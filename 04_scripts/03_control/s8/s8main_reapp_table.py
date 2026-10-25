"""Rev. 51: 10 Hz controller table around a re-approach sequence (ML78 tail).

Usage: python -I s8main_reapp_table.py <case_dir> <t0_rel_s> <t1_rel_s>
Per controller period (engine time - event): phase, per leg F_lower (kN), true F_cyl 1 ms
minimum of the past period (kN), airborne fraction of the past period, and command
components (mm/s): twist, reapproach, guard, attitude, heave, issued.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
case = Path(sys.argv[1])
t0, t1 = float(sys.argv[2]), float(sys.argv[3])
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
t_ev = float(res["event_t_s"])
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
tr = r8["t"] - t_ev
tp = pads["t"] - t_ev
F = pads["F_cyl"] / 1e3
air = pads["airborne"].astype(float)
f = lambda a: " ".join(f"{x:+5.1f}" for x in a)
print(" t_rel phase | F_lower kN               | Fmin_true(prev T) kN     | air frac  | twist         | reapp         | guard         | att           | heave | issued")
for k in np.flatnonzero((tr >= t0) & (tr <= t1)):
    m = (tp > tr[k] - 0.1) & (tp <= tr[k])
    fmin = F[m].min(axis=0)
    af = air[m].mean(axis=0)
    print(f" {tr[k]:5.2f} {str(r8['phase'][k])[:5]:5s} | {f(r8['F_lower_N'][k]/1e3)} | {f(fmin)} | {' '.join(f'{x:.1f}' for x in af)} | "
          f"{f(1e3*r8['cmp_twist_u'][k])} | {f(1e3*r8['cmp_reapproach_u'][k])} | {f(1e3*r8['cmp_guard_u'][k])} | {f(1e3*r8['cmp_attitude_u'][k])} | {1e3*r8['cmp_heave_u'][k][0]:+4.1f} | {f(1e3*r8['issued_u'][k])}")
