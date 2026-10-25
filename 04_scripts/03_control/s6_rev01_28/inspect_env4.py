"""Print C7 / C8 checks and the worst accepted points of rule A from target_envelope.json."""
import json
import sys

import numpy as np

d = json.load(open(sys.argv[1]))
print(json.dumps(d["checks"]["C7_flat_target_vs_slope_levelled"], indent=0))
print(json.dumps(d["checks"]["C8_friction_decomposition"], indent=0))
print(d["meta"]["conventions"])
roll = np.array(d["meta"]["grid_roll_deg"])
pitch = np.array(d["meta"]["grid_pitch_deg"])
R, P = np.meshgrid(roll, pitch)  # maps are (pitch, roll)
print("map shape", np.array(d["maps"]["top|flat"]["s_max_c50_m"]).shape)
worst = []
for key, m in d["maps"].items():
    lvl, floor = key.split("|")
    sm = np.array(m["s_max_c50_m"])
    s20 = np.array(m["s_max_c20_m"])
    s0 = np.array(m["s_max_c0_m"])
    # floor attitude from summary key
    print(key, "floor slope?", d["summary"][key].get("floor_roll_pitch_deg"), list(d["summary"][key].keys())[:3])
    break
print(json.dumps(d["user_box_points"]["top|flat"])[:500])
print(json.dumps(d["summary"]["top|P:pitch+3.2"]["base_c50"], indent=0)[:1500])
