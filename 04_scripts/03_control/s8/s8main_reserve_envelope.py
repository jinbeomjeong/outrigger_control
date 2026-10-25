"""Rev. 51: stroke reserve at the event vs the operating diamond |phi|/4.4 + |theta|/3.2 (floor).

Usage: python -I s8main_reserve_envelope.py <stroke_scan_json>
Reserve = soft end - 1 mm - stroke reading at the event (min over legs) [mm]. Prints the
minimum reserve inside / outside the operating diamond and the three FAULT bases' indices, and
the deepest settle a leg could take before the stroke-end test with the observed heave rise
(~6-7 mm, ASSUMPTION from ML28_ep5).
"""
import json
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
rows = json.load(open(sys.argv[1], encoding="utf-8"))["rows"]
inside, outside = [], []
for r in rows:
    phi, th = r["floor_deg"]
    op = abs(phi) / 4.4 + abs(th) / 3.2
    ver = abs(phi) / 5.5 + abs(th) / 3.5
    res = min(r["reserve_at_event_mm"])
    (inside if op <= 1.0 else outside).append((res, r["case"], op, ver, r["fault_t_s"] is not None))
for name, g in (("inside operating diamond", inside), ("outside (verification only)", outside)):
    g.sort()
    bases = {c.split("_")[0] for _, c, *_ in g}
    print(f"{name}: episodes {len(g)} (bases {len(bases)}), min reserve {g[0][0]:.1f} mm ({g[0][1]}, op {g[0][2]:.2f}), p05 {np.percentile([x[0] for x in g],5):.1f} mm, FAULT {sum(x[4] for x in g)}")
    for x in g[:6]:
        print(f"    {x[1]}: reserve {x[0]:.1f} mm, op index {x[2]:.2f}, verification index {x[3]:.2f}, fault {x[4]}")
