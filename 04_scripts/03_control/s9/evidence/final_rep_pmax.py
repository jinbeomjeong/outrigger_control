"""Max moving pressure (spec 412 / paper_max_pressure_table.record_moving_peak: F_cyl / A_p per leg, 10 Hz Record,
mask |u_applied| > 1e-6 m/s, judge limit 180 bar) of FINAL-REP Chrono cases.

Usage: python -I final_rep_pmax.py <repo root> <out json> <case dir> [<case dir> ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))
import paper_max_pressure_table as pmt  # noqa: E402

out = {"definition": "spec 412: max over legs and moving samples (|u_applied| > 1e-6 m/s) of F_cyl / A_p, "
                     "10 Hz Record; judge limit 180 bar; ratio to 210 bar = F / extension force limit",
       "script": "04_scripts/03_control/s9/evidence/final_rep_pmax.py (uses "
                 "04_scripts/03_control/s8/paper_max_pressure_table.record_moving_peak)",
       "cases": {}}
for c in sys.argv[3:]:
    p = Path(c)
    peak = pmt.record_moving_peak(p)
    cur = peak["current"]
    out["cases"][p.name] = {"folder": p.as_posix(), "max_moving_pressure_bar": cur["max_bar"],
                            "peak_leg": cur.get("leg"), "t_s": cur.get("t_s"),
                            "measured_head_max_bar": peak["measured_head_pressure_current_mask_max_bar"],
                            "max_any_state_bar": peak["max_any_state_bar"]} | pmt._ratios(cur["max_bar"], cur.get("leg"))
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
for k, v in out["cases"].items():
    print(k, round(v["max_moving_pressure_bar"], 2), v["peak_leg"], round(v["t_s"], 1),
          "ratio180", round(v["ratio_to_judge_180"], 3))
