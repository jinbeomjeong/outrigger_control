"""Read hopsan-mcp results_full.csv (row format) of LockedCyl and compute 10 Hz secant ratios.

R_model = (V_1 / A_1) / (V_2 / A_2) = capacitance ratio (equal beta).  Windows n = 1 and 3
periods of 0.1 s, every 1 ms phase offset (all sampling phases), after the load step.
Usage: python -I hopsan_secant.py <results_full.csv>
"""
import csv
import sys

import numpy as np

rows = {}
with open(sys.argv[1], newline="", encoding="utf-8") as f:
    for r in csv.reader(f):
        rows[r[0]] = np.array([float(x) for x in r[3:]])
t = rows["Time"]
ph = rows["OrfH#P1#Pressure"]
pr = rows["OrfR#P1#Pressure"]
A1, A2, V1, V2 = 0.013273229, 0.00376991118, 0.0094107, 0.00034306
r_model = (A2 / V2) / (A1 / V1)
print("R_model", round(r_model, 4))
dt = t[1] - t[0]
step = int(round(0.1 / dt))
for n in (1, 3):
    vals, exc = [], []
    for k in range(step * n, t.size):
        if t[k - step * n] < 0.5:
            continue
        dh = ph[k - step * n] - ph[k]
        dr = pr[k] - pr[k - step * n]
        if abs(dh) >= 1e5:
            vals.append((dr / dh) / r_model)
            exc.append(A2 * (dr - r_model * dh))
    v = np.array(vals)
    print(f"n={n}: windows {v.size}, R_sec/R_model min {v.min():.5f} max {v.max():.5f}, "
          f"max |force excess| {np.abs(exc).max():.2f} N")
