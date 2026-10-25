"""H-S8-4: 1 ms trace of one leg around a locked lift-off (pads.npz) plus the 10 Hz valve rows.

Usage: h_s8_4_trace.py <episode_dir> <leg 0..3> <t_centre_s> [half_window_s] [stride_ms]
"""

import json
import sys
from pathlib import Path

import numpy as np

ep = Path(sys.argv[1])
leg = int(sys.argv[2])
tc = float(sys.argv[3])
hw = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
stride = int(sys.argv[5]) if len(sys.argv) > 5 else 1

z = np.load(ep / "pads.npz", allow_pickle=True)
t = z["t"]
sel = np.flatnonzero((t >= tc - hw) & (t <= tc + hw))[::stride]
cols = ["F_cyl", "F_pressure", "f_seal", "seal_stuck", "head_pressure", "rod_pressure",
        "s_motor", "s_link", "s_piston", "N", "airborne", "F_seal_limit"]
print("t_s      " + " ".join(f"{c:>12s}" for c in cols))
for i in sel:
    vals = []
    for c in cols:
        v = z[c][i, leg]
        if c in ("head_pressure", "rod_pressure"):
            vals.append(f"{v / 1e5:12.3f}")
        elif c in ("s_motor", "s_link", "s_piston"):
            vals.append(f"{v * 1e3:12.5f}")
        elif c in ("F_cyl", "F_pressure", "f_seal", "N", "F_seal_limit"):
            vals.append(f"{v / 1e3:12.4f}")
        else:
            vals.append(f"{int(v):12d}")
    print(f"{t[i]:.4f} " + " ".join(vals))

r8 = np.load(ep / "r8_series.npz", allow_pickle=True)
rec = np.load(ep / "record" / "record.npz", allow_pickle=True)
tt = r8["t"]
k = np.flatnonzero(np.abs(tt - tc) <= max(hw, 0.25))
print("\n10 Hz rows: t, issued_u, valve_u, amp_u, rec.u_cmd, rec.u_applied, s_ref[mm], meas p_h, p_r")
for j in k:
    print(f"{tt[j]:.3f} {r8['issued_u'][j, leg]: .3e} {r8['valve_u'][j, leg]: .3e} "
          f"{r8['amp_u'][j, leg]: .3e} {rec['u_cmd'][j, leg]: .3e} {rec['u_applied'][j, leg]: .3e} "
          f"{rec['s_ref'][j, leg] * 1e3:.5f} {rec['meas.head_pressure'][j, leg] / 1e5:.2f} "
          f"{rec['meas.rod_pressure'][j, leg] / 1e5:.2f}")
meta = json.loads(str(z["meta_json"]))
print("\nmeta keys:", list(meta)[:40])
print({k2: meta[k2] for k2 in list(meta)[:40] if not isinstance(meta[k2], (dict, list))})
