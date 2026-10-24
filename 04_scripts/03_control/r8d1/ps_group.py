"""Group the base-variant probe stiffness ratios by beta / F_s / slope / level.

Input: 06_analysis/02_control/r8_10hz/d1/ps_all.json (spec rev. 31 144.1).
"""
import json
import sys
from collections import defaultdict

import numpy as np

NOM = (5.83e6, 5.83e6, 6.98e6, 6.98e6)
rows = [r for r in json.load(open(sys.argv[1])) if r["case"]["variant"] == "base"]
for name in ("beta", "fs", "level"):
    g = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for p in r["probes"]:
            if p["grounded_stiff"]:
                g[r["case"][name]][("F" if p["leg"] < 2 else "R")].append(p["half"] / NOM[p["leg"]])
    print(name)
    for k in sorted(g):
        print("  ", k, {fr: f"{np.min(v):.2f}/{np.median(v):.2f}/{np.max(v):.2f}" for fr, v in g[k].items()})
g = defaultdict(list)
for r in rows:
    c = r["case"]
    g[(c["beta"], c["fs"])].append(r["scale"])
print("scale by (beta, fs):", {k: (round(min(v), 2), round(max(v), 2)) for k, v in g.items()})
for r in rows:
    c = r["case"]
    if c["fs"] == 0 and c["roll"] == 0 and c["pitch"] == 0:
        print(c["level"], c["beta"], [round(p["half"] / NOM[p["leg"]], 2) for p in r["probes"]],
              [round(p["full"] / NOM[p["leg"]], 2) for p in r["probes"]], [round(p["travel_mm"], 2) for p in r["probes"]])
