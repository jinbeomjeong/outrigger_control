"""Compact view of the S8 ML main report (06_analysis/02_control/s8/s8_ml_main_report.json) for the rev. 52 verdict.
Prints settings, seeds, shares and, per model, the E1..E7 rows (truncated). Read only.
Usage: python -I r52_ml_report_view.py <project_root>
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(sys.argv[1]) / "06_analysis" / "02_control" / "s8" / "s8_ml_main_report.json"
d = json.loads(p.read_text(encoding="utf-8"))


def short(x, n=600):
    s = json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + " ..."


for k in ("spec", "seeds", "settings", "shares", "tags", "release_step_effect", "lightgbm_preset", "compared_runs"):
    print("##", k, short(d.get(k), 900))
models = d["models"]
print("## models", list(models) if isinstance(models, dict) else type(models))
for name, m in (models.items() if isinstance(models, dict) else enumerate(models)):
    print("====", name, list(m) if isinstance(m, dict) else "")
    if isinstance(m, dict):
        for k, v in m.items():
            print("  -", k, short(v, 700))
print("## train_report", short(d.get("train_report"), 1500))
for name, m in models.items():
    for rows in ("verdict_rows", "judged_rows"):
        print("####", name, rows)
        for r in m[rows]:
            print("   ", r["item"], "|", r["kind"], "|", r["passed"], "|", short(r["value"], 400))
    for sname, s in m["sets"].items():
        if isinstance(s, dict) and "ML" in s:
            print("   set", sname, "ML", short(s["ML"], 300), "J_C", short(s.get("J_C"), 200))
