"""Two-sensor net force sum around TOUCH end / READY / re-READY (D5 load-sum check)."""
import json
import sys

import numpy as np

# migrated 2026-10-25 from session scratchpad a06eea4a ctrl-run; repository-relative
BASE = (__import__("pathlib").Path(__file__).resolve().parents[3] / "07_results" / "S6").as_posix() + "/"
case_dir = BASE + sys.argv[1]
times = [float(x) for x in sys.argv[2].split(",")]
z = np.load(case_dir + "/record/record.npz")
t = z["t"]
d_f, r_f, d_r, r_r = 0.130, 0.110, 0.110, 0.090
Ap = np.array([np.pi / 4 * d_f**2] * 2 + [np.pi / 4 * d_r**2] * 2)
Aa = np.array([np.pi / 4 * (d_f**2 - r_f**2)] * 2 + [np.pi / 4 * (d_r**2 - r_r**2)] * 2)
ph = z["meas.head_pressure"]
pr = z["meas.rod_pressure"]
net = ph * Ap - pr * Aa
print("t range", t[0], t[-1], "dt", t[1] - t[0])
for tq in times:
    i = int(np.argmin(abs(t - tq)))
    print(f"t={t[i]:8.2f} net[kN]={np.round(net[i]/1e3,2)} sum={net[i].sum()/1e3:8.2f} "
          f"Fcyl_sum={z['F_cyl'][i].sum()/1e3:8.2f} crawler_Fz={z['F_crawler'][i][2]/1e3:8.2f}")
