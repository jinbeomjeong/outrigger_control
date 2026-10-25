"""Spec rev. 44 (question a): where the F1 (R43-1) excess of p1 S_top_rpB_wika_Fs8 sits.

F1 row: |F_hat_cal - F| <= F_s,leg + 0.6 kN + 0.025 |F| (phases other than CHECK), F = true rod
force at the control instant (pads F_cyl, nearest 1 ms row), F_s,leg = F_s (front) / 0.8333 F_s
(rear). Reading: F_nominal_N if recorded, else F_lower_N (the p1 records have no nominal).
Prints the worst samples with phase, leg, F, reading, seal friction f and the excess for the
constant 0.6 and 0.85 kN; also the near-F_min (-5..+10 kN) share |F_hat_cal - F + f|.
Usage: python -I s8p1r_f1.py <case dir> <F_s kN>
"""
import sys, os
import numpy as np

D, FS = sys.argv[1], float(sys.argv[2]) * 1e3
r8 = np.load(os.path.join(D, "r8_series.npz"))
pads = np.load(os.path.join(D, "pads.npz"))
reading = r8["F_nominal_N"] if "F_nominal_N" in r8.files else r8["F_lower_N"]
src = "F_nominal_N" if "F_nominal_N" in r8.files else "F_lower_N"
t8, ph = r8["t"], r8["phase"]
tp = pads["t"]
idx = np.clip(np.searchsorted(tp, t8), 0, tp.size - 1)
F = pads["F_cyl"][idx]
f = pads["f_seal"][idx]
fs_leg = np.array([FS, FS, 0.8333 * FS, 0.8333 * FS])
mask = ph != "check"
rows = []
for k in np.flatnonzero(mask):
    for leg in range(4):
        e = abs(reading[k, leg] - F[k, leg])
        rows.append((e - fs_leg[leg] - 600 - 0.025 * abs(F[k, leg]), e - fs_leg[leg] - 850 - 0.025 * abs(F[k, leg]),
                     t8[k], str(ph[k]), leg, F[k, leg], reading[k, leg], f[k, leg]))
rows.sort(reverse=True)
print("reading", src, "samples", len(rows))
for r in rows[:6]:
    print(f"  excess0.6 {r[0] / 1e3:+.3f} excess0.85 {r[1] / 1e3:+.3f} kN t {r[2]:.1f} {r[3]} leg {r[4]} F {r[5] / 1e3:.2f} "
          f"read {r[6] / 1e3:.2f} f {r[7] / 1e3:+.2f}")
near = [(abs(reading[k, l] - F[k, l] + f[k, l]), str(ph[k]), l, F[k, l]) for k in np.flatnonzero(mask) for l in range(4)
        if -5e3 <= F[k, l] <= 10e3]
near.sort(reverse=True)
print("near F_min share max", [(round(a / 1e3, 3), p, l, round(b / 1e3, 2)) for a, p, l, b in near[:5]])
