"""Rev. 51: rod-pressure D1 fallback in ML88_ep0 (RR 63.3 s) - commands vs plant lock state.

Usage: python -I s8main_rod_fb.py <case_dir> <leg> <t0_s> <t1_s>
Prints per 10 Hz sample the controller issued / valve / applied command of the leg (exact
values, m/s), and 1 ms truth between samples: rod / head pressure range, u_applied range,
airborne fraction, seal_stuck, s_motor change.
"""
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
case = Path(sys.argv[1])
L = LEGS.index(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
rec = np.load(case / "record" / "record.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
t = r8["t"]
tp = pads["t"]
for k in np.flatnonzero((t >= t0) & (t <= t1)):
    print(f"{t[k]:.2f}: issued {r8['issued_u'][k][L]:+.3e} valve {r8['valve_u'][k][L]:+.3e} amp {r8['amp_u'][k][L]:+.3e} | rec u_cmd {rec['u_cmd'][k][L]:+.3e} u_applied {rec['u_applied'][k][L]:+.3e}"
          f" | meas head {rec['meas.head_pressure'][k][L]/1e5:6.1f} rod {rec['meas.rod_pressure'][k][L]/1e5:6.1f} bar")
    m = (tp > t[k]) & (tp <= t[k] + 0.1)
    if m.any():
        rp = pads["rod_pressure"][m, L] / 1e5
        hp = pads["head_pressure"][m, L] / 1e5
        sm = pads["s_motor"][m, L]
        print(f"      next 0.1 s truth: rod {rp[0]:6.1f}->{rp[-1]:6.1f} (min {rp.min():.1f} max {rp.max():.1f}), head {hp[0]:6.1f}->{hp[-1]:6.1f}, air {pads['airborne'][m, L].mean():.2f}, "
              f"seal_stuck {pads['seal_stuck'][m, L].mean():.2f}, ds_motor {1e3*(sm[-1]-sm[0]):+.3f} mm")
