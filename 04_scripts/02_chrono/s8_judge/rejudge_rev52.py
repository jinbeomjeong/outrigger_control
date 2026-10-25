"""C-S8-37 re-judgement (no Chrono): run the judge of ``<project_root>/03_src`` on a recorded
batch into ``<out_dir>`` and compare with the batch's existing verify file.

Moved from the cad scratchpad (``cad-run/rejudge_rev52.py``, 2026-10-25). Run on 2026-10-25 with
the rev. 52 judge; outputs ``summary_<target>.json`` are kept in
``06_analysis/01_chrono/18_S8/rejudge/rev52/``. Of that run's verify files only the ml768 one is
kept, in ``07_results/S8/archive/rejudge_ml768/rev52/`` (local only, gitignored); the others are
row-identical to ``07_results/S8/archive/18_S8_extra/rejudge/rev54/*_base52.json``.

usage (Chrono-dev python)::

    python -I -X utf8 rejudge_rev52.py <project_root> <target> <out_dir>

target: p1r | rest | mlj | ml768. Sources are read only.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "03_src"))
TARGET, OUT = sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
S8 = ROOT / "07_results" / "S8"

from outrigger_sim.verify import s8_control as v  # noqa: E402

BATCHES = {
    "p1r": (S8 / "p1r_20261024_222013", dict(ref_batch=S8 / "p1_20261024_204911",
                                             lookup_batches=[S8 / "p1_20261024_204911",
                                                             S8 / "rest_20261024_233615"])),
    "rest": (S8 / "rest_20261024_233615", dict(ref_batch=S8 / "p1r_20261024_222013",
                                               lookup_batches=[S8 / "p1r_20261024_222013"])),
    "mlj": (S8 / "ml_main_20261025_090131" / "judged",
            dict(lookup_batches=[S8 / "p1r_20261024_222013"])),
}


def failed(doc):
    return sorted({(r["item"], str(r["case"])) for r in doc["rows"] if r["passed"] is False})


def item9_cmp(doc):
    out = {}
    for cid, sm in (doc.get("s8_metrics") or {}).items():
        rep = ((sm.get("item9") or {}).get("replay") or {})
        if "J_C" not in rep:
            continue
        row = {}
        for name in ("J_P", "J_C"):
            row[name] = {k: {"M1": (src.get(name) or {}).get("score", {}).get("M1_missed"),
                             "M1p": (src.get(name) or {}).get("score", {}).get("M1p_late"),
                             "M4_kN": None if (src.get(name) or {}).get("score", {}).get(
                                 "M4_max_N") is None else round(
                                 src[name]["score"]["M4_max_N"] / 1e3, 3)}
                         for k, src in (("corrected", rep), ("raw", rep.get("raw") or {}),
                                        ("upper", rep.get("upper_sensitivity") or {}))}
        row["stats"] = rep.get("reading_stats")
        out[cid] = row
    return out


t0 = time.perf_counter()
if TARGET in BATCHES:
    batch, kw = BATCHES[TARGET]
    old = json.loads((batch / "verify_S8C.json").read_text(encoding="utf-8"))
    p = v.judge_batch(batch, OUT / f"verify_S8C_{TARGET}_rev52.json", **kw)
    new = json.loads(p.read_text(encoding="utf-8"))
    fo, fn = failed(old), failed(new)
    i9 = item9_cmp(new)
    diff_cases = {c: r for c, r in i9.items()
                  if any(r[n]["corrected"]["M1"] != r[n]["raw"]["M1"]
                         or r[n]["corrected"]["M1p"] != r[n]["raw"]["M1p"]
                         for n in ("J_P", "J_C"))}
    rows_new = [r for r in new["rows"] if r["item"].startswith(("C-S8-3", "I1 "))]
    summary = {"target": TARGET, "batch": str(batch), "wall_s": time.perf_counter() - t0,
               "old_failed": fo, "new_failed": fn,
               "only_old": sorted(set(fo) - set(fn)), "only_new": sorted(set(fn) - set(fo)),
               "rows_old": len(old["rows"]), "rows_new": len(new["rows"]),
               "item9_cases": len(i9), "item9_raw_vs_corrected_differs": diff_cases,
               "new_rows": [{k: r.get(k) for k in ("item", "case", "value", "limit", "passed",
                                                    "kind", "note")} for r in rows_new]}
else:
    batch = S8 / "ml_main_20261025_090131"
    old = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
    p = v.judge_ml_batch(batch, OUT / "verify_S8ML_ml768_rev52.json")
    new = json.loads(p.read_text(encoding="utf-8"))
    fo, fn = failed(old), failed(new)
    rows_new = [r for r in new["rows"] if r["item"].startswith("C-S8-3")]
    rt = {c: m.get("rt") for c, m in new["ml_metrics"].items() if m.get("rt")}
    summary = {"target": TARGET, "batch": str(batch), "wall_s": time.perf_counter() - t0,
               "old_failed": fo, "new_failed": fn,
               "only_old": sorted(set(fo) - set(fn)), "only_new": sorted(set(fn) - set(fo)),
               "rows_old": len(old["rows"]), "rows_new": len(new["rows"]),
               "new_rows": [{k: r.get(k) for k in ("item", "case", "value", "limit", "passed",
                                                    "kind")} for r in rows_new],
               "work_ml24_ep7": (rt.get("ML24_ep7") or {}).get("work"),
               "work_ml78_ep0": (rt.get("ML78_ep0") or {}).get("work")}
(OUT / f"summary_{TARGET}.json").write_text(json.dumps(summary, indent=1, default=str),
                                            encoding="utf-8")
print(json.dumps({k: summary[k] for k in ("target", "wall_s", "only_old", "only_new")},
                 indent=1, default=str))
print("new failed:", len(fn), "old failed:", len(fo))
