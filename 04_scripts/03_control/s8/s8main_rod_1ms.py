"""Rev. 51: 1 ms truth of one leg (rod / head pressure, F_cyl, N, airborne, seal state, piston
and motor strokes, u_applied hold) between t0 and t1, printed every <step> ms.

Usage: python -I s8main_rod_1ms.py <case_dir> <leg> <t0_s> <t1_s> [step_ms]
"""
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
case = Path(sys.argv[1])
L = LEGS.index(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
step = int(sys.argv[5]) if len(sys.argv) > 5 else 5
p = np.load(case / "pads.npz", allow_pickle=True)
rec = np.load(case / "record" / "record.npz", allow_pickle=True)
tp = p["t"]
idx = np.flatnonzero((tp >= t0) & (tp <= t1))[::step]
j = np.clip(np.searchsorted(rec["t"], tp[idx], side="right") - 1, 0, len(rec["t"]) - 1)
print("   t      rod   head  F_cyl kN  N kN   air stuck f_seal kN  s_piston mm  s_link mm  s_motor mm  cb_y  u_applied(10Hz)")
for i, jj in zip(idx, j):
    print(f" {tp[i]:.3f} {p['rod_pressure'][i, L]/1e5:6.1f} {p['head_pressure'][i, L]/1e5:6.1f} {p['F_cyl'][i, L]/1e3:8.2f} {p['N'][i, L]/1e3:6.2f} {int(p['airborne'][i, L])} "
          f"{int(p['seal_stuck'][i, L])} {p['f_seal'][i, L]/1e3:7.2f} {1e3*p['s_piston'][i, L]:10.3f} {1e3*p['s_link'][i, L]:10.3f} {1e3*p['s_motor'][i, L]:10.3f} {p['cb_y'][i, L]:.2f} {rec['u_applied'][jj][L]:+.2e}")
