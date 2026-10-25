"""CB D2 false fallback: rod / head pressure and command of one leg during LEVEL extension.

Prints the 10 Hz controller command (computed_u) and the 1 ms pad record pressures at the
sample times, plus the counterbalance state (cb_y, cb_delta) if recorded.
Usage: python -I s8cb_d2.py <case_dir> <leg 0-3> <t0> <t1>
"""
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
leg = int(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
t, tp = r8["t"], pads["t"]
idx = np.clip(np.searchsorted(tp, t), 0, len(tp) - 1)  # exact alignment (rev. 47 217.6)
print(" t      phase     u_comp[mm/s] u_valve  p_h[bar] p_r[bar]  F[kN]  cb_y   cb_delta[mm]  s_motor[mm]")
for k in np.flatnonzero((t >= t0) & (t <= t1)):
    j = idx[k]
    print(f" {t[k]:6.2f} {r8['phase'][k]:9s} {1e3*r8['computed_u'][k, leg]:+7.2f} {1e3*r8['valve_u'][k, leg]:+7.2f}"
          f" {pads['head_pressure'][j, leg]/1e5:8.1f} {pads['rod_pressure'][j, leg]/1e5:8.1f}"
          f" {pads['F_cyl'][j, leg]/1e3:7.2f} {pads['cb_y'][j, leg]:6.3f} {1e3*pads['cb_delta'][j, leg]:8.3f}"
          f" {1e3*pads['s_motor'][j, leg]:9.2f}")
