"""Independent recomputation of the D1'' ratio (C-S8-32) on the MLJ runs.

For every 10 Hz head-pressure step |dp_h| > 100 bar after the first LEVEL entry (crawler
lift-off side), r_k = sum_i F_hat_i - M_eff [f_z - (alpha x r_C1)_z], ratio = |r_k - r_{k-1}| /
(|dp_h| A_p). f_z = last 10 ms partial mean (imu_samples[k, -1, 2]); alpha = (gyro[k, -1] -
gyro[k, -2]) / 0.01 s; (alpha x r)_z = alpha_x r_y - alpha_y r_x with r_C1 = (-0.150, 0.881)
m (spec 219.2 table, top level ASSUMPTION for all levels); M_eff = median sum F_hat / f_z over
the last READY stay (>= 3 samples, last 60 s) before the step. Judge time base.
"""
import json
import sys
from pathlib import Path

import numpy as np

A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
R_X, R_Y = -0.150, 0.881
LEGS = ("FL", "FR", "RL", "RR")

for arg in sys.argv[1:]:
    d = Path(arg)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    T0 = float(res["settings"]["start_t_s"])
    r8 = np.load(d / "r8_series.npz", allow_pickle=True)
    rec = np.load(d / "record" / "record.npz", allow_pickle=True)
    t = r8["t"] - T0
    ph = r8["phase"].astype(str)
    fz = r8["imu_samples"][:, -1, 2]
    g = r8["imu_gyro_samples"]
    alpha = (g[:, -1, :] - g[:, -2, :]) / 0.01
    lever = alpha[:, 0] * R_Y - alpha[:, 1] * R_X
    Fs = np.nansum(r8["F_hat_N"], axis=1)
    hp = rec["meas.head_pressure"]
    t_lo = next(float(a) for a, b in res["phases"] if b == "level")
    ready = ph == "ready"
    out = []
    for k in range(1, len(t)):
        if t[k] < t_lo:
            continue
        dp = hp[k] - hp[k - 1]
        for j in range(4):
            if abs(dp[j]) <= 100e5:
                continue
            prior = np.flatnonzero(ready[:k] & (t[:k] >= t[k] - 60.0))
            if len(prior) < 3:
                continue
            # last contiguous READY stay
            last = prior[-1]
            stay = [last]
            for i in prior[::-1][1:]:
                if i == stay[-1] - 1:
                    stay.append(i)
                else:
                    break
            if len(stay) < 3:
                stay = list(prior)
            m_eff = float(np.median(Fs[stay] / fz[stay]))
            J = abs(dp[j]) * A_P[j]
            r_c = Fs - m_eff * (fz - lever)
            r_u = Fs - m_eff * fz
            out.append((t[k], LEGS[j], dp[j] / 1e5, abs(r_c[k] - r_c[k - 1]) / J,
                        abs(r_u[k] - r_u[k - 1]) / J, m_eff))
    print(d.name, "steps > 100 bar:", len(out))
    for o in out:
        print(f"  t={o[0]:.2f} {o[1]} dp={o[2]:+.1f} bar ratio corrected {o[3]:.3f} uncorrected {o[4]:.3f} M_eff {o[5]:.0f} kg")
