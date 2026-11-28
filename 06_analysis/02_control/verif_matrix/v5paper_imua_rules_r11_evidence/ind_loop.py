"""Small-signal attitude loop of the IND (C8 skeleton) harness: full IMU vs A-type options.

Assumption (not from the code): attitude loop = fine gain K / s (leg geometry cancels),
continuous approximation of the 10 Hz loop: output delay d = 1 (0.1 s) + ZOH 0.05 s.
Two independent paths inside Python: (1) dense frequency sweep with exact delays,
(2) ct.margin on a rational model with 6th-order Pade delays.
"""
import json
import sys

import control as ct
import numpy as np

K = 0.5                 # c8.C8Settings.fine_gain_1_s [1/s]
TAU = 0.8               # IND_ATTITUDE_TIME_CONSTANT_S [s], 2 stages
T_LOOP = 0.1 + 0.05     # output delay d = 1 plus ZOH half period [s]
T_INC = 0.02            # inclinometer output delay [s] (rules draft 1, assumption)
F_BESSEL = 1.0          # inclinometer 2nd-order Bessel cut-off [Hz]

s = ct.tf("s")
lpf = 1 / (TAU * s + 1) ** 2
# 2nd-order Bessel, -3 dB at F_BESSEL: normalised 3/(p^2+3p+3), -3 dB at 1.3617 rad/s
a = 2 * np.pi * F_BESSEL / 1.36165
bessel = 3 / ((s / a) ** 2 + 3 * (s / a) + 3)

cases = {
    "full_imu (tilt -> LPF)": (lpf, T_LOOP),
    "A-type kept LPF (incl -> LPF)": (bessel * lpf, T_LOOP + T_INC),
    "A-type LPF bypassed (incl only)": (bessel, T_LOOP + T_INC),
}
w = np.logspace(-3, 2, 400_001)
out = {"assumptions": {"K_1_s": K, "tau_s": TAU, "stages": 2, "T_loop_s": T_LOOP,
                       "T_inclinometer_s": T_INC, "bessel_hz": F_BESSEL,
                       "bessel_dc_group_delay_s": 1 / a,
                       "feedback": "negative, L = K/s * F(s) * exp(-sT)"}}
for name, (filt, delay) in cases.items():
    base = K / s * filt
    resp = base(1j * w) * np.exp(-1j * w * delay)
    mag = np.abs(resp)
    ph = np.unwrap(np.angle(resp))
    i = np.where(np.diff(np.sign(mag - 1.0)))[0]
    wgc = float(w[i[0]]) if len(i) else float("nan")
    pm = float(180 + np.degrees(np.interp(wgc, w, ph)))
    j = np.where(np.diff(np.sign(ph + np.pi)))[0]
    wpc = float(w[j[0]]) if len(j) else float("nan")
    gm = float(1 / np.interp(wpc, w, mag)) if len(j) else float("inf")
    S = 1 / np.abs(1 + resp)
    num, den = ct.pade(delay, 6)
    lr = base * ct.tf(num, den)
    gm2, pm2, wcg2, wcp2 = ct.margin(lr)
    cl = ct.feedback(lr, 1)
    out[name] = {
        "sweep": {"wgc_rad_s": wgc, "pm_deg": pm, "wpc_rad_s": wpc, "gm_abs": gm,
                  "gm_db": 20 * np.log10(gm), "Ms": float(S.max()),
                  "delay_margin_s": float(np.radians(pm) / wgc)},
        "ct_margin_pade6": {"gm_abs": float(gm2), "pm_deg": float(pm2),
                            "w_phase_cross_rad_s": float(wcg2),
                            "w_gain_cross_rad_s": float(wcp2)},
        "cl_poles_max_real": float(np.max(np.real(cl.poles()))),
    }
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
