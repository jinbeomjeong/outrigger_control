"""H-S8-2: 1 ms trace of one leg (s_ref, pressures, forces) with the locked-law prediction.

Usage: python -I h_s8_2_trace.py <case_dir> <leg 0-3> <t0> <t1> [every_ms] [t_anchor]
The prediction p_r0 + R(s_anchor) (p_h0 - p_h) uses the anchor sample at t_anchor (default t0)
and R = (L0h + s) / (L0r + 0.7 - s) with the run's dead lengths.
"""
import json
import sys
from pathlib import Path

import numpy as np

BAR = 1e5
case = Path(sys.argv[1])
leg = int(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
every = int(sys.argv[5]) if len(sys.argv) > 5 else 20
ta = float(sys.argv[6]) if len(sys.argv) > 6 else t0
meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
rs = meta["run"]["engine"]["actuator"]["rod_side"]
l0r, l0h = rs["rod_dead_length_m"][leg], rs["head_dead_length_m"]
with np.load(case / "pads.npz", allow_pickle=True) as z:
    t = z["t"]
    sm, ph, pr = z["s_motor"][:, leg], z["head_pressure"][:, leg], z["rod_pressure"][:, leg]
    fp, fc, air = z["F_pressure"][:, leg], z["F_cyl"][:, leg], z["airborne"][:, leg]
    n = z["N"][:, leg]
ja = int(np.searchsorted(t, ta - 1e-9))
R = (l0h + sm[ja]) / (l0r + 0.7 - sm[ja])
print(f"{case.name} leg {leg} L0r {l0r} L0h {l0h} anchor t {t[ja]:.3f} s {sm[ja]:.5f} R {R:.4f}"
      f" p_h0 {ph[ja]/BAR:.2f} p_r0 {pr[ja]/BAR:.2f}")
print("   t      s_ref[mm]  ds/dt[mm/s]  p_h    p_r    pred_r   F_p[kN]  F_cyl  N_pad  air")
idx = np.flatnonzero((t >= t0) & (t <= t1))[::every]
for j in idx:
    v = (sm[j] - sm[j - 1]) / (t[j] - t[j - 1]) if j else 0.0
    pred = max(-0.91 * BAR, pr[ja] + R * (ph[ja] - ph[j]))
    print(f" {t[j]:7.3f} {1e3*sm[j]:9.3f} {1e3*v:+10.5f} {ph[j]/BAR:7.2f} {pr[j]/BAR:7.2f} {pred/BAR:7.2f}"
          f" {fp[j]/1e3:8.2f} {fc[j]/1e3:7.2f} {n[j]/1e3:7.2f} {int(air[j])}")
