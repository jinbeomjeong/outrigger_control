"""P8-14 selection on raw/runs.jsonl of p814_rerun.py (rule fixed before the run, applied as
written; spec v8 draft 12 P8-14):

  candidate (L1, L2) eligible when
  (1) G1 R12_bottom-FR-Fs4-o0.075-RE1bF-ready: every gate passes and READY is back
      (t_ready_back_s finite, final phase ready);
  (2) the edition 5 deadlock keys (P814_VBK_KEYS): stall signature (spec v7 6.2 fixed reading,
      jp3_ed7_rules.is_stall_signature_ed7 on the T4h phase / t_s / motor_stroke_m) false;
  (3) the other keys: against B no new failed gate, no new J7 item, no READY lost, no new FAULT;
  (4) every LEVEL ended by a waiver (L2) or after a rise-opened shot (L1): |D| <= 15 kN at DONE.
  Both eligible: fewer keys with commands_sha256 different from B; tie -> L2.

Outputs: p814_selection.json, p814_metrics.csv, p814_analyze_out.txt
Usage: conda run -n dynamics-dev python -I -B p814_analyze.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
sys.path.insert(0, str(WT / "04_scripts" / "04_hydraulic" / "coupled"))
import jp3_ed7_rules as rules  # noqa: E402

D_LIMIT_N = 15000.0
DONE_HOLD_S = 1.0


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


rr = _load("p814_rerun", HERE / "p814_rerun.py")
an = _load("p89_analyze", rr.P89_DIR / "p89_analyze.py")


def jkey(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in ("mask", "t4h_dir")},
                      sort_keys=True)


def stall_of(rec: dict) -> dict:
    job = rec["p814_job"]
    if "r79_key" in job:
        folder = RAW / f"t4h_r79_{job['setting'].replace('-', '_')}"
        t_ev = None
    else:
        folder = RAW / "t4h"
        t_ev = rec.get("t_event_s")
    name = rec.get("t4h_file")
    if not name or not (folder / name).exists():
        return {"stall": None, "why": "no T4h"}
    with np.load(folder / name, allow_pickle=False) as z:
        t = np.asarray(z["t_s"], float)
        ph = [str(p).lower() for p in np.asarray(z["phase"]).astype(str)]
        s = np.asarray(z["motor_stroke_m"], float)
    stall = rules.is_stall_signature_ed7(ph, t, s, t_ev)
    win = t >= t[-1] - rules.STALL_WINDOW_S - rules.STALL_WINDOW_TOLERANCE_S
    spans = (s[win].max(axis=0) - s[win].min(axis=0)) * 1e3
    return {"stall": bool(stall), "last_phase": ph[-1], "t_end": round(float(t[-1]), 2),
            "spans_mm": [round(float(x), 3) for x in spans]}


def fault_of(rec: dict) -> bool:
    eo = rec.get("event_output") or {}
    base = rec.get("base") or {}
    phase = str(rec.get("final_phase") or base.get("final_phase") or "")
    events = [str(n) for _, n in (rec.get("events") or [])]
    return (phase.startswith("fault") or bool(eo.get("fault_periods"))
            or any(n.startswith("FAULT") for n in events)
            or bool(base.get("fault")))


def row_of(rec: dict) -> dict:
    job = rec["p814_job"]
    log = json.loads((RAW / "logs" / f"{rec['p814']['stem']}_p814.json").read_text("utf-8"))["p814"]
    if "r79_key" in job:
        base = rec.get("base") or {}
        gates = base.get("gates") or {}
        t_ready = base.get("t_ready_s", base.get("t_ready"))
        final_phase = base.get("final_phase")
        ready = t_ready is not None
        t_ev = None
        j7, capped = set(), False
    else:
        eo = rec.get("event_output") or {}
        gates = eo.get("gates") or {}
        t_ready = eo.get("t_ready_back_s") if rec.get("t_event_s") is not None else (
            (rec.get("values") or {}).get("times") or {}).get("t_first_ready_s")
        final_phase = rec.get("final_phase")
        ready = an.ready_reached(rec)
        t_ev = rec.get("t_event_s")
        j7, capped = an.j7_set(rec)
    rel = (lambda t: round(t - t_ev, 2)) if t_ev is not None else (lambda t: round(t, 2))
    rise_t = {round(x["t"], 6) for x in log["rise_open"]}
    shots_open = [x for x in log["shots"] if round(x["t"], 6) in rise_t]
    dones = log["level_done"]
    acted_dones = []
    for d in dones:
        by_waiver = any(d["t"] - DONE_HOLD_S - 0.25 <= w["t"] <= d["t"] + 1e-9
                        for w in log["waivers"])
        prev = [x["t"] for x in dones if x["t"] < d["t"]]
        seg0 = max(prev) if prev else -math.inf
        by_shot = any(seg0 < s["t"] <= d["t"] for s in shots_open)
        if by_waiver or by_shot:
            acted_dones.append({"t_rel": rel(d["t"]), "path": d["path"],
                                "absD_kN": round(abs(d["D_N"]) / 1e3, 3),
                                "by": "waiver" if by_waiver else "rise_shot"})
    return {"sha": rec.get("commands_sha256"), "gates": gates,
            "gates_failed": sorted(g for g, ok in gates.items() if not ok),
            "t_ready": t_ready, "final_phase": final_phase, "ready": ready,
            "fault": fault_of(rec), "j7": sorted(j7), "capped": capped,
            "stall": stall_of(rec),
            "n_rise_open": len(log["rise_open"]),
            "rise_open_rel": [(rel(x["t"]), round(x["absD_N"] / 1e3, 2), round(x["rise_N"] / 1e3, 2))
                              for x in log["rise_open"]][:40],
            "shots_in_open": [(rel(x["t"]), x["leg"], x["sign"]) for x in shots_open],
            "n_shots": len(log["shots"]),
            "n_waivers": len(log["waivers"]),
            "waivers_rel": [(rel(x["t"]), round(x["absD_N"] / 1e3, 2), round(x["rise_N"] / 1e3, 2),
                             x["legs"]) for x in log["waivers"]][:40],
            "level_done_rel": [(rel(d["t"]), d["path"], round(d["D_N"] / 1e3, 2)) for d in dones],
            "acted_dones": acted_dones, "wall_s": rec.get("wall_s")}


def main() -> int:
    recs = [json.loads(x) for x in (RAW / "runs.jsonl").read_text("utf-8").splitlines()]
    by = {}
    errors = []
    for r in recs:
        if "error" in r:
            errors.append({"job": r.get("p814_job"), "error": str(r["error"])[:300]})
            continue
        by[jkey(r["p814_job"])] = r
    table, lines = {}, []
    for group, label, key in rr.KEYS:
        for arm in rr.ARMS:
            r = by.get(jkey(rr.job_of(key, arm)))
            table[(label, arm)] = None if r is None else row_of(r)
    repro = by.get(jkey({"r79_key": rr.VBK0_REPRO[0], "setting": "VBK0"}))
    repro_out = None if repro is None else {
        "stored": rr.VBK0_REPRO[1][:12], "now": (repro.get("commands_sha256") or "")[:12],
        "equal": repro.get("commands_sha256") == rr.VBK0_REPRO[1],
        "stall": stall_of(repro)}
    sel = {}
    for cand in ("L1", "L2"):
        missing = [(lab, a) for (lab, a), v in table.items() if v is None and a in ("B", cand)]
        g1 = table.get(("bottom-FR-Fs4-RE1bF-ready-o0.075", cand))
        c1 = (g1 is not None and not g1["gates_failed"] and g1["t_ready"] is not None
              and g1["final_phase"] == "ready")
        c2 = {}
        for group, label, _ in rr.KEYS:
            if group == "da":
                v = table.get((label, cand))
                c2[label] = None if v is None else (v["stall"]["stall"] is False)
        c3 = {}
        for group, label, _ in rr.KEYS:
            if group in ("ga", "da"):
                continue
            b, c = table.get((label, "B")), table.get((label, cand))
            if b is None or c is None:
                c3[label] = {"not_judgeable": True}
                continue
            item = {"new_failed_gates": sorted(g for g, ok in c["gates"].items()
                                               if not ok and b["gates"].get(g, True)),
                    "new_j7": sorted(set(c["j7"]) - set(b["j7"])),
                    "ready_lost": b["ready"] and not c["ready"],
                    "new_fault": c["fault"] and not b["fault"],
                    "capped": b["capped"] or c["capped"]}
            if any(item.values()):
                c3[label] = item
        c4 = []
        for (label, arm), v in table.items():
            if arm == cand and v is not None:
                c4 += [dict(d, key=label) for d in v["acted_dones"] if d["absD_kN"] > D_LIMIT_N / 1e3]
        n_diff = sum(1 for _, label, _ in rr.KEYS
                     if table.get((label, cand)) and table.get((label, "B"))
                     and table[(label, cand)]["sha"] != table[(label, "B")]["sha"])
        eligible = (not missing and c1 and all(v is True for v in c2.values()) and not c3
                    and not c4)
        sel[cand] = {"missing": missing, "cond1_G1": c1, "cond2_stall_false": c2,
                     "cond2": all(v is True for v in c2.values()), "cond3_failures": c3,
                     "cond3": not c3, "cond4_over_limit": c4, "cond4": not c4,
                     "eligible": eligible, "n_keys_commands_differ_from_B": n_diff}
    if sel["L1"]["eligible"] and sel["L2"]["eligible"]:
        choice = "L1" if sel["L1"]["n_keys_commands_differ_from_B"] < \
            sel["L2"]["n_keys_commands_differ_from_B"] else "L2"
    elif sel["L1"]["eligible"]:
        choice = "L1"
    elif sel["L2"]["eligible"]:
        choice = "L2"
    else:
        choice = None
    result = {"rule": "spec v8 draft 12 P8-14 (fixed before the run, applied as written)",
              "selection": sel, "choice": choice, "vbk0_repro": repro_out, "errors": errors,
              "n_records": len(recs)}
    (HERE / "p814_selection.json").write_text(
        json.dumps({"result": result, "lines": {f"{k[0]}|{k[1]}": v for k, v in table.items()}},
                   indent=1, default=str), "utf-8")
    cols = ["group", "key", "arm", "sha", "gates_failed", "t_ready", "final_phase", "ready",
            "fault", "j7", "stall", "n_rise_open", "shots_in_open", "n_waivers", "waivers_rel",
            "level_done_rel", "acted_dones", "n_shots", "wall_s"]
    with (HERE / "p814_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for group, label, _ in rr.KEYS:
            for arm in rr.ARMS:
                v = table.get((label, arm))
                if v is None:
                    w.writerow([group, label, arm] + ["MISSING"] * (len(cols) - 3))
                    continue
                v = dict(v, group=group, key=label, arm=arm)
                w.writerow([json.dumps(v[c], default=str) if isinstance(v[c], (list, dict))
                            else v[c] for c in cols])
    out = [json.dumps(result, default=str)]
    for group, label, _ in rr.KEYS:
        for arm in rr.ARMS:
            v = table.get((label, arm))
            if v is None:
                out.append(f"{group:3s} {label:40s} {arm:2s} MISSING")
                continue
            out.append(f"{group:3s} {label:40s} {arm:2s} {str(v['sha'])[:8]} fail={v['gates_failed']} "
                       f"tR={v['t_ready']} ph={v['final_phase']} fault={v['fault']} "
                       f"stall={v['stall'].get('stall')} rise_open={v['n_rise_open']} "
                       f"shots_open={v['shots_in_open']} waivers={v['n_waivers']} "
                       f"wv={v['waivers_rel'][:3]} done={v['level_done_rel'][:4]} "
                       f"acted={v['acted_dones']} j7={v['j7']}")
    text = "\n".join(out)
    (HERE / "p814_analyze_out.txt").write_text(text, "utf-8")
    print(text.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
