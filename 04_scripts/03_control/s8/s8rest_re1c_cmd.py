"""RE1c: controller command chain (computed / raw / issued / valve) per leg around the event.

Usage: python -I s8rest_re1c_cmd.py <case_dir> [t0] [t1]
"""
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 58.0
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
t = r8["t"]
sel = np.flatnonzero((t >= t0) & (t <= t1))
print("t      phase     | computed_u | raw_u | issued_u | valve_u  [mm/s]  FL FR RL RR | reapproach cmp")
for k in sel[::2]:
    f = lambda key: " ".join(f"{1e3 * v:+5.2f}" for v in r8[key][k])
    print(f"{t[k]:6.2f} {r8['phase'][k]:9s} | {f('computed_u')} | {f('raw_u')} | {f('issued_u')} | {f('valve_u')}"
          f" | {f('cmp_reapproach_u')} | {r8['limit_flags'][k][:60]}")
