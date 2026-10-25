"""List user_box_points keys for one floor."""
import json
import sys

d = json.load(open(sys.argv[1]))
for k in ("top|flat", "top|P:pitch+3.2"):
    u = d["user_box_points"][k]
    print(k, list(u.keys()))
    for kk in list(u.keys())[:12]:
        print("  ", kk, u[kk].get("s_motor_mm"), u[kk].get("s_max_mm@c50"))
