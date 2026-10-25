"""H-S8-1: print one leg of one S8 case around a window (1 ms record decimated), read only.

Usage: python -I h_s8_1_probe.py <case_dir> <leg 0-3> <t0> <t1> [step_s]
Columns: t, phase(10 Hz), u_cmd, ds_motor/dt, N, F_cyl, F_p, f_seal, p_h, p_r [bar g], s_motor.
"""
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
leg = int(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
step = float(sys.argv[5]) if len(sys.argv) > 5 else 0.1
with np.load(case / "pads.npz", allow_pickle=True) as z:
    d = {k: z[k] for k in ("t", "N", "F_cyl", "F_pressure", "f_seal", "head_pressure",
                           "rod_pressure", "s_motor")}
with np.load(case / "r8_series.npz", allow_pickle=True) as z:
    t10, ph10, u10 = z["t"], z["phase"], z["computed_u"]
t = d["t"]
v = np.zeros_like(d["s_motor"])
v[1:] = np.diff(d["s_motor"], axis=0) / np.diff(t)[:, None]
m = (t >= t0) & (t <= t1)
print(f"max p_r in window {d['rod_pressure'][m, leg].max()/1e5:.2f} bar at "
      f"t {t[m][np.argmax(d['rod_pressure'][m, leg])]:.3f}; whole run max "
      f"{d['rod_pressure'][:, leg].max()/1e5:.2f} at {t[np.argmax(d['rod_pressure'][:, leg])]:.3f}")
last = -1e9
for k in np.flatnonzero(m):
    if t[k] - last < step - 1e-9:
        continue
    last = t[k]
    j = max(np.searchsorted(t10, t[k], side="right") - 1, 0)
    print(f"{t[k]:8.3f} {ph10[j]:10s} u {1e3*u10[j, leg]:+6.2f} v {1e3*v[k, leg]:+7.3f} "
          f"N {d['N'][k, leg]/1e3:7.2f} F {d['F_cyl'][k, leg]/1e3:7.2f} Fp {d['F_pressure'][k, leg]/1e3:7.2f} "
          f"f {d['f_seal'][k, leg]/1e3:+5.2f} ph {d['head_pressure'][k, leg]/1e5:7.2f} "
          f"pr {d['rod_pressure'][k, leg]/1e5:7.2f} s {1e3*d['s_motor'][k, leg]:8.3f}")
