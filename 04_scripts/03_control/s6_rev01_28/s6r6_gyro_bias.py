"""S6 spec revision 6: CHECK gyro-bias estimate on a settling machine (reduced plant, ideal gyro, true bias 0).

Settled plant as 05_tests/unit/test_c2_closed_loop.settled_plant (65.5 s on the crawler, u = 0) for floors flat /
nose-down 3.5 / nose-up 3.5 / roll 5.5 at the top level, then CHECK windows of 2 / 4 s. Estimators of the gyro bias:
  naive    : mean of the body rate over the window (R4.1 P3)
  motion   : (integral of the rate - (accelerometer tilt at the end - at the start)) / window, the end tilts are the
             means of the accelerometer tilt over 0.5 s (motion seen by both sensors cancels)
Also the accelerometer-tilt change over the window (stationarity indicator) and the rate RMS.
Run: conda run -n dynamics-dev python -I s6r6_gyro_bias.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "05_tests" / "unit"))
import test_c2_closed_loop as T  # noqa: E402

rcc = T.reduced_model


def tilt(f):
    return np.array([math.atan2(f[1], f[2]), math.atan2(-f[0], math.hypot(f[1], f[2]))])


def main():
    out = {}
    for name, (r, p) in {"flat": (0, 0), "fdown3.5": (0, 3.5), "fup3.5": (0, -3.5), "roll5.5": (5.5, 0)}.items():
        pl = T.settled_plant(r, p)
        n = rcc.N_SUB
        w, a = [], []
        for _ in range(int(round(4.0 / rcc.T_CTRL))):
            acc = pl.step(np.zeros(4), n)
            w.append(pl.w[:2].copy())                      # body rate (end of period), roll / pitch axes
            a.append(tilt(acc[0:3] / n))
        w = np.array(w); a = np.array(a)
        res = {}
        for T_w in (2.0, 4.0):
            k = int(round(T_w / rcc.T_CTRL)); m = int(round(0.5 / rcc.T_CTRL))
            ww, aa = w[:k], a[:k]
            naive = ww.mean(axis=0)
            dacc = aa[-m:].mean(axis=0) - aa[:m].mean(axis=0)
            span = (k - m) * rcc.T_CTRL                     # distance between the two 0.5 s window centres
            integ = ww[m // 2:k - m // 2].sum(axis=0) * rcc.T_CTRL
            motion = (integ - dacc) / span
            res[f"{T_w:g}s"] = {"naive_rad_s": naive.tolist(), "motion_rad_s": motion.tolist(),
                                "naive_deg_h": np.degrees(naive * 3600).round(1).tolist(),
                                "motion_deg_h": np.degrees(motion * 3600).round(1).tolist(),
                                "acc_tilt_change_deg": np.degrees(dacc).round(5).tolist(),
                                "rate_rms_deg_s": np.degrees(np.sqrt((ww ** 2).mean(axis=0))).round(5).tolist()}
        out[name] = res
        print(name, json.dumps(res))
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
