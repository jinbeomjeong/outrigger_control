"""Rev. 55 (262.1 items without a judge row): PROBE -> LEVEL returns and re-READY vs 768.

Usage: python -I c55_avail.py <episodes dir> [<ref episodes dir>] [--ids a,b,...] [--out file.json]
Definitions (spec rev. 55 266.4):
- probe_return: after the event, a 10 Hz phase change 'probe' -> 'level' (r8_series.npz phase),
  counted per run; the controller events 'probe_aborted_low_load:<leg>' are listed as the cause.
- re_ready: first 'ready' sample after a 'done' sample after the event (event-relative s);
  None = not reached inside the record (episode end, 28 s).
- verdict: probe_return_runs <= the reference on the same ids (0 for the 17); median of
  (re_ready - ref) over runs reaching it in both <= +0.1 s (one control period); a run
  reaching it only in the reference fails when it has a probe return or a rod fallback,
  otherwise it is a DONE-tail record (spec 257.2).
"""
import json
import os
import re
import sys
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s8" / "rev53_56" / "rev55"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ---
REF768 = str(REPO / r"07_results\S8\ml_main_20261025_090131\episodes")
IDS17 = ("ML00_ep5,ML10_ep0,ML21_ep1,ML24_ep6,ML25_ep7,ML33_ep4,ML34_ep7,ML39_ep5,ML42_ep6,"
         "ML51_ep4,ML54_ep0,ML59_ep7,ML71_ep6,ML81_ep5,ML87_ep1,ML87_ep5,ML89_ep0").split(",")
PAT = re.compile(r"t_s=([-0-9.e]+), name='([^']+)'")
TOL_S = 0.1


def run(path):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = float(r["event_t_s"])
    s = np.load(os.path.join(path, "r8_series.npz"), allow_pickle=True)
    t, ph = s["t"] - te, [str(x) for x in s["phase"]]
    ret, rr, seen_done = [], None, False
    for i in range(1, len(t)):
        if t[i] < 0:
            continue
        if ph[i - 1] == "probe" and ph[i] == "level":
            ret.append(round(float(t[i]), 1))
        if ph[i] == "done":
            seen_done = True
        if rr is None and seen_done and ph[i] == "ready":
            rr = round(float(t[i]), 1)
    aborts, fb = [], []
    for e in json.load(open(os.path.join(path, "controller_events.json"), encoding="utf-8")):
        m = PAT.search(e)
        if not m or float(m.group(1)) < te - 1e-6:
            continue
        if m.group(2).startswith("probe_aborted"):
            aborts.append([round(float(m.group(1)) - te, 1), m.group(2)])
        if m.group(2).startswith("WARN_ROD_PRESSURE_FALLBACK"):
            fb.append([round(float(m.group(1)) - te, 1), m.group(2)])
    return {"probe_returns_s": ret, "probe_aborts": aborts, "rod_fallback": fb, "re_ready_s": rr,
            "t_end_s": round(float(t[-1]), 1)}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opts = dict(zip(argv[::1], argv[1::1]))
    batch = args[0]
    ref = args[1] if len(args) > 1 and not args[1].startswith("--") and os.path.isdir(args[1]) else REF768
    ids = opts.get("--ids").split(",") if "--ids" in opts else IDS17
    out = {"batch": batch, "ref": ref, "ids": ids, "runs": {}}
    deltas, only_ref, only_new = [], [], []
    for c in ids:
        a, b = run(os.path.join(batch, c)), run(os.path.join(ref, c))
        out["runs"][c] = {"new": a, "ref": b}
        if a["re_ready_s"] is not None and b["re_ready_s"] is not None:
            deltas.append((c, round(a["re_ready_s"] - b["re_ready_s"], 1)))
        elif b["re_ready_s"] is not None:
            only_ref.append(c)
        elif a["re_ready_s"] is not None:
            only_new.append(c)
    d = np.array([x for _, x in deltas]) if deltas else np.array([np.nan])
    pr_new = sorted(c for c in ids if out["runs"][c]["new"]["probe_returns_s"])
    pr_ref = sorted(c for c in ids if out["runs"][c]["ref"]["probe_returns_s"])
    s = {"probe_return_runs_new": pr_new, "probe_return_runs_ref": pr_ref,
         "re_ready_both": len(deltas), "median_delta_s": float(np.median(d)),
         "later_runs": [c for c, x in deltas if x > TOL_S], "worst": max(deltas, key=lambda z: z[1]) if deltas else None,
         "reached_only_in_ref": only_ref, "reached_only_in_new": only_new}
    # runs reaching re-READY only in the reference: a failure when the new run has a probe
    # return or a rod fallback (availability defect), else a DONE-tail record (spec 257.2)
    bad_only_ref = [c for c in only_ref if out["runs"][c]["new"]["probe_returns_s"]
                    or out["runs"][c]["new"]["rod_fallback"]]
    s["reached_only_in_ref_with_probe_return_or_fallback"] = bad_only_ref
    s["reached_only_in_ref_done_tail_record"] = [c for c in only_ref if c not in bad_only_ref]
    s["passed"] = bool(len(pr_new) <= len(pr_ref) and s["median_delta_s"] <= TOL_S
                       and not bad_only_ref)
    out["summary"] = s
    dst = opts.get("--out") or os.path.join(str(OUT_DIR), "c55_avail.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    for c in ids:
        a, b = out["runs"][c]["new"], out["runs"][c]["ref"]
        print(f"{c}: probe->level new {a['probe_returns_s']} ref {b['probe_returns_s']} | "
              f"re-READY new {a['re_ready_s']} ref {b['re_ready_s']}")
    print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
