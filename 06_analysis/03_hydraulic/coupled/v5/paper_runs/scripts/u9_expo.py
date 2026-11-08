"""Exposure table (T2) per key and setting from u9_judge.json."""
import json
import sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text("utf-8"))
for k in d["keys"]:
    for st in ("VB0.85", "VB0.8"):
        x = k[st]
        u = x["U9"]
        lc = u["level_count_s"]
        r = x["E2_level_min_r"]
        print(f"{k['case']} {k['eps']} {st}: level k1..4 {lc['1']} {lc['2']} {lc['3']} {lc['4']} | ge3 {u['longest_ge3_s']} eq4 {u['longest_eq4_s']} "
              f"n {u['ge3_runs_count']} | E1 lvl short {x['E1_level_short_s']} | r FL {r.get('FL')} FR {r.get('FR')} RL {r.get('RL')} RR {r.get('RR')} "
              f"| E4 sat {x['E4']['saturated_s']} | E5 back {x['E5'].get('back_in_band_after_saturation_s')} int {x['E5'].get('max_abs_integral_rad_s')} "
              f"| rate {u['level_sat_rate_max_deg_s']} | J {len(x['J_fails'])}")
