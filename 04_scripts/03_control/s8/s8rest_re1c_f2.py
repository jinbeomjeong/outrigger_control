"""RE1c F2 failure: which leg / when F_lower_est exceeds the true rod force, and why.

Reads one case folder (r8_series.npz, pads.npz) and prints per leg:
  - F_lower_est - F, (F_nominal - F_band) - F, (F_hat - F_band) - F at the 10 Hz samples
  - rod / head pressures and issued command of the worst leg around the first violation.
Truth F is the 1 ms rod axial force F_cyl taken at the record time nearest to each sample.
Usage: python -I s8rest_re1c_f2.py <case_dir>
"""
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
case = Path(sys.argv[1])
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
t = r8["t"]
tp = pads["t"]
print(f"r8 t {t[0]:.3f}..{t[-1]:.3f}  pads t {tp[0]:.4f}..{tp[-1]:.4f}")
# r8 t is controller time; try both offsets and pick the one that matches the readings best
F_cyl = pads["F_cyl"]
f_seal = pads["f_seal"]
best = None
for off in (0.0, 3.0):
    idx = np.clip(np.searchsorted(tp, t + off), 0, len(tp) - 1)  # exact alignment (rev. 47 217.6)
    ideal = F_cyl[idx] - f_seal[idx]
    err = np.nanmedian(np.abs(r8["F_hat_N"] - ideal))
    print(f"offset {off}: median |F_hat - (F - f)| = {err:.1f} N")
    if best is None or err < best[0]:
        best = (err, off, idx)
_, off, idx = best
F = F_cyl[idx]
band = r8["leg_band_N"]
d_est = r8["F_lower_est_N"] - F
d_nom = r8["F_nominal_N"] - band - F
d_hat = r8["F_hat_N"] - band - F
d_rdl = r8["F_lower_N"] - F
for i, leg in enumerate(LEGS):
    bad = d_est[:, i] > 0
    first = t[bad][0] if bad.any() else None
    print(f"{leg}: max(F_lower_est-F) {d_est[:, i].max()/1e3:+.2f} kN  n>0 {bad.sum()}  first {first}"
          f" | max(F_nom-band-F) {d_nom[:, i].max()/1e3:+.2f} | max(F_hat-band-F) {d_hat[:, i].max()/1e3:+.2f}"
          f" | max(F_lower_reading-F) {d_rdl[:, i].max()/1e3:+.2f}")
worst = int(np.argmax(d_est.max(axis=0)))
bad = np.flatnonzero(d_est[:, worst] > 0)
if bad.size:
    k0 = bad[0]
    print(f"worst leg {LEGS[worst]}; samples around first violation (t controller s):")
    print(" t      phase     u_issued[mm/s]  p_h[bar] p_r[bar]  F[kN]  F_hat F_nom F_low_rd F_low_est band")
    for k in range(max(0, k0 - 25), min(len(t), k0 + 10)):
        j = idx[k]
        print(f" {t[k]:6.2f} {r8['phase'][k]:9s} {1e3*r8['issued_u'][k, worst]:+7.2f}"
              f" {pads['head_pressure'][j, worst]/1e5:8.1f} {pads['rod_pressure'][j, worst]/1e5:8.1f}"
              f" {F[k, worst]/1e3:7.2f} {r8['F_hat_N'][k, worst]/1e3:6.2f} {r8['F_nominal_N'][k, worst]/1e3:6.2f}"
              f" {r8['F_lower_N'][k, worst]/1e3:7.2f} {r8['F_lower_est_N'][k, worst]/1e3:7.2f} {band[k, worst]/1e3:5.2f}")
    # RR forced retraction window and other legs' commands
    print("issued_u all legs [mm/s] at 50..56 s:")
    for k in np.flatnonzero((t >= 50.0) & (t <= 56.0))[::3]:
        print(f"  {t[k]:6.2f} {r8['phase'][k]:9s} " + " ".join(f"{1e3*v:+6.2f}" for v in r8["issued_u"][k])
              + " | p_r " + " ".join(f"{pads['rod_pressure'][idx[k], i]/1e5:6.1f}" for i in range(4))
              + " | F " + " ".join(f"{F[k, i]/1e3:6.1f}" for i in range(4)))
