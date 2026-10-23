"""Gyro error on the probe attitude cue: Monte Carlo of the window-mean difference of the rate-integrated
attitude (c2.py / ground_contact.py: 0.3 s window means before and after the extension, T = 20 ms samples =
period-averaged rate). Probe: 2 mm at 0.25 v_max (0.353 s) + 0.4 s hold; the 'before' window is the last 0.3 s
before the move starts. Analytic cross-check: Var = d^2 * (dt_c - tau/3) for two non-overlapping box windows of
length tau whose centres are dt_c apart (integrated white noise = random walk).
Units: deg, s. Seed 20261021.
Run: conda run -n dynamics-dev python -I s6_gyro_probe_noise.py
"""
import math

import numpy as np

T = 0.02
v = 0.25 * 0.68 / 30.0
move = 2e-3 / v
hold = 0.4
tau = 0.3
n_w = round(tau / T)
n_move = math.ceil(move / T)
n_hold = round(hold / T)
n_pre = n_w
N = n_pre + n_move + n_hold
rng = np.random.default_rng(20261021)
M = 200_000
resp = 0.0118 * 2.0          # FL J * 2 mm [deg], ground_contact.py docstring
thr = 0.5 * resp
out = []
for arw_deg_rth in (0.15, 0.3, 0.5, 1.0):
    d = arw_deg_rth / 60.0                     # deg/sqrt(s)
    rate = rng.normal(0.0, d / math.sqrt(T), size=(M, N))   # period-averaged white rate
    ang = np.cumsum(rate, axis=1) * T
    pre = ang[:, n_pre - n_w:n_pre].mean(axis=1)
    post = ang[:, N - n_w:N].mean(axis=1)
    diff = post - pre
    sd = float(diff.std())
    dt_c = (N - n_w / 2) * T - (n_pre - n_w / 2) * T
    sd_an = d * math.sqrt(dt_c - tau / 3)
    z = thr / sd
    p = math.erfc(z / math.sqrt(2)) / 2
    out.append((arw_deg_rth, sd, sd_an, z, p))
    print(f"ARW {arw_deg_rth:4.2f} deg/rt-h: sd {sd:.5f} deg (analytic {sd_an:.5f}), threshold {thr:.4f} deg, "
          f"z {z:.2f}, one-sided error prob {p:.2e}")
dt_c = (N - n_w / 2) * T - (n_pre - n_w / 2) * T
print(f"window centre separation {dt_c:.3f} s, response {resp:.4f} deg")
for bias_deg_h in (5, 12, 20, 50):
    b = bias_deg_h / 3600.0
    print(f"uncorrected bias {bias_deg_h:3d} deg/h -> {b * dt_c:.4f} deg ({b * dt_c / resp * 100:.1f} % of response)")
