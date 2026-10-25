"""H-S8-1: CB extend formula (spec 4.3) against the recorded rod pressure in a time window.

Recorded 1 ms truth (pads.npz) of one leg; formula with the recorded pressure force F_p
(nominal CB: p_set 330 bar g, psi 4, p_back 2 bar g) and with the 50 ms first-order lag of the
L1-R machine (rod_chamber._relax_tracked_pressure), restarted at the window start.
Usage: python -I h_s8_1_window.py <case_dir> <leg 0-3> <t0> <t1>
"""
import math
import sys
from pathlib import Path

import numpy as np

A_P = (0.013273229, 0.013273229, 0.009503317777, 0.009503317777)
A_R = (0.00376991118, 0.00376991118, 0.003141592654, 0.003141592654)
P_SET, PSI, P_BACK, TAU = 330e5, 4.0, 2e5, 0.05

case = Path(sys.argv[1])
leg = int(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
with np.load(case / "pads.npz", allow_pickle=True) as z:
    t, fp, pr, ph = z["t"], z["F_pressure"][:, leg], z["rod_pressure"][:, leg], z["head_pressure"][:, leg]
    fs = z["f_seal"][:, leg]
a_p, a_r = A_P[leg], A_R[leg]
tgt = np.maximum(P_BACK, (P_SET * a_p - PSI * fp) / (a_p + PSI * a_r))
m = np.flatnonzero((t >= t0) & (t <= t1))
y = pr[m[0]]
lag = np.empty(m.size)
keep = math.exp(-float(np.median(np.diff(t))) / TAU)
for n, k in enumerate(m):
    if n:
        y = tgt[k - 1] + (y - tgt[k - 1]) * keep
    lag[n] = y
ident = pr[m] - np.maximum(P_BACK, P_SET - PSI * ph[m])
print(f"{case.name} leg {leg} t {t0}-{t1} s, n {m.size}")
print(f"  F_p          {fp[m].min()/1e3:8.2f} .. {fp[m].max()/1e3:8.2f} kN   f_seal {fs[m].min()/1e3:+.2f} .. {fs[m].max()/1e3:+.2f} kN")
print(f"  p_r recorded {pr[m].min()/1e5:8.2f} .. {pr[m].max()/1e5:8.2f} bar g")
print(f"  formula      {tgt[m].min()/1e5:8.2f} .. {tgt[m].max()/1e5:8.2f} bar g (instantaneous)")
print(f"  formula+lag  {lag.min()/1e5:8.2f} .. {lag.max()/1e5:8.2f} bar g, max |rec - lag| {np.max(np.abs(pr[m]-lag))/1e5:.3f} bar,"
      f" mean {np.mean(pr[m]-lag)/1e5:+.3f}")
print(f"  identity p_r - max(p_back, p_set - psi p_h): {ident.min()/1e5:+.2f} .. {ident.max()/1e5:+.2f} bar")
print(f"  p_h recorded {ph[m].min()/1e5:8.2f} .. {ph[m].max()/1e5:8.2f} bar g")
