"""H-S8-2: per-sample 10 Hz view of the fallback estimates of one leg.

Usage: python -I h_s8_2_stretch.py <case_dir> <leg 0-3> <t0> <t1>
Columns: applied command, measured head / rod / stroke, true head / rod (1 ms record at the
sample), the current estimate (two_pressure.py as of 2026-10-25) and the P-S8-13 estimate
(h_s8_2_lock_ratio.window_estimate), and their lower-bound errors F_lower - F_true [kN]
(truth head, no lift-off cap). Positive error = optimistic.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h_s8_2_lock_ratio as h  # noqa: E402

case = h.load_case(Path(sys.argv[1]))
leg = int(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
r8, rec, p = case["r8"], case["rec"], case["pads"]
t = r8["t"]
n = t.size
ir = np.clip(np.searchsorted(rec["t"], t - 1e-9), 0, rec["t"].size - 1)
ip = np.clip(np.searchsorted(p["t"], t - 1e-9), 0, p["t"].size - 1)
cmd = np.r_[0.0, r8["issued_u"][:-1, leg]]
hm, rm_, st = rec["meas.head_pressure"][ir, leg], rec["meas.rod_pressure"][ir, leg], rec["meas.stroke"][ir, leg]
ph, pr, fp = p["head_pressure"][ip, leg], p["rod_pressure"][ip, leg], p["F_pressure"][ip, leg]
est_cur = np.zeros(n)
est_prop = np.zeros(n)
k = 0
last_cur, last_sign, last_u = 0.0, 1.0, 0.0
while k < n:
    if cmd[k] != 0.0:
        last_sign, last_u = float(np.sign(cmd[k])), float(cmd[k])
        last_cur = h.model_moving(case, last_sign, hm[k], leg, current=True)
        est_cur[k] = last_cur
        est_prop[k] = h.model_moving(case, last_sign, hm[k], leg)
        k += 1
        continue
    k0 = k
    while k < n and cmd[k] == 0.0:
        k += 1
    idx = np.arange(k0, k)
    w_s = h.lock_window_s(last_u, case["tau_v"])
    in_w = t[idx] < t[k0] + w_s - 1e-9
    in_w[0] = True
    est_cur[idx] = last_cur + h.R_FB[leg] * np.maximum(hm[k0] - hm[idx], 0.0)
    est_prop[idx] = h.window_estimate(case, last_sign, hm[idx], st[idx], in_w, leg)
B = h.BAR
print(" t      cmd[mm/s]  h_meas  r_meas  s_meas   h_true  r_true | est_cur  est_prop | err_cur err_prop [kN]")
for k in np.flatnonzero((t >= t0) & (t <= t1)):
    ec = ph[k] * h.A_P[leg] - est_cur[k] * h.A_R[leg] - fp[k]
    ep = ph[k] * h.A_P[leg] - est_prop[k] * h.A_R[leg] - fp[k]
    print(f" {t[k]:6.2f} {1e3*cmd[k]:+8.3f} {hm[k]/B:7.2f} {rm_[k]/B:7.2f} {1e3*st[k]:8.2f}"
          f" {ph[k]/B:7.2f} {pr[k]/B:7.2f} | {est_cur[k]/B:7.2f} {est_prop[k]/B:8.2f} |"
          f" {ec/1e3:+7.2f} {ep/1e3:+7.2f}")
