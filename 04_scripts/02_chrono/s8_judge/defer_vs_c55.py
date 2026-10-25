"""Compare the judge rev. 56 deferred windows / reference columns with the control
``c55_defer.json`` (read only): window minimum (next + 0.3 or defer + T_o + 0.3 end), the
0..4 s leg statistics (run, ref).

Moved from the cad scratchpad (``cad-run55/defer_vs_c55.py``, 2026-10-25); the control JSON and
the judge output folder are arguments now. Copies: ``verify_S8ML_A_new56.json`` and
``verify_S8C_D_new56.json`` in ``07_results/S8/archive/18_S8_extra/rejudge/rev56/`` (local only,
gitignored; pass this folder as ``--new``), ``c55_defer.json`` in
``06_analysis/01_chrono/18_S8/rejudge/rev56/inputs_logs/``.

usage::

    python -I -X utf8 defer_vs_c55.py --c55 <c55_defer.json> --new <dir with *_new56.json>
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--c55", type=Path, required=True, help="control c55_defer.json")
ap.add_argument("--new", type=Path, required=True, help="folder with the rev. 56 judge outputs")
a = ap.parse_args()
c55 = json.loads(a.c55.read_text(encoding="utf-8"))
per = {}
for f in ("verify_S8ML_A_new56.json", "verify_S8C_D_new56.json"):
    doc = json.loads((a.new / f).read_text(encoding="utf-8"))
    (row,) = [r for r in doc["rows"] if r["item"].startswith("C-S8-41 RT deferral")]
    per.update(row["per_run"])
bad = n = 0
for c, v in c55.items():
    wins = per[c]
    for d in v["deferrals"]:
        w = next(x for x in wins if x["leg"] == d["leg"] and d["deferred_s"] in
                 [round(s, 2) for s in x["deferred_s"]])
        end = "next+0.3" if "next+0.3" in d["windows"] else "defer+T_o+0.3"
        cw = d["windows"][end]
        ok_end = abs(cw["end"] - w["window_s"][1]) < 2e-3
        ok_min = abs(cw["A"]["min"] - w["min_kN"]) < 1e-3
        ctx = v["ctx_0_3s"][d["leg"]]
        ok_run = all(abs(ctx["A"][p] - w["leg_0_4s"][q]) < 1e-3 for p, q in
                     (("min", "min_kN"), ("below_Fmin_s", "below_F_min_s"), ("air_s", "air_s")))
        ok_ref = all(abs(ctx["ref"][p] - w["ref_0_4s"][q]) < 1e-3 for p, q in
                     (("min", "min_kN"), ("below_Fmin_s", "below_F_min_s"), ("air_s", "air_s")))
        n += 1
        bad += not (ok_end and ok_min and ok_run and ok_ref)
        print(f"{c} {d['leg']} {d['deferred_s']}: end {cw['end']} / {w['window_s'][1]} "
              f"min {cw['A']['min']} / {w['min_kN']} | run0-4 {ok_run} ref0-4 {ok_ref}"
              f"{'' if ok_end and ok_min else '  <-- DIFF'}")
print("deferrals compared:", n, "differences:", bad)
