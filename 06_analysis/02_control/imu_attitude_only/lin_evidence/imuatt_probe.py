"""Analytic side calculations (continuous approximations, no closed loop):

1. Rocking ripple of the controller attitude filter output and of the completion filter, per sensor model,
   from the modal apparent-tilt amplification G (imu_cabin_and_accuracy_review.md 2.2) and the assumed true
   rocking amplitudes of 2.3 (top 0.031, middle 0.021, bottom 0.016 deg).
2. Probe attitude cue (ground_contact.py window difference, spec 10.3): 1-sigma noise of the difference of two
   0.3 s window means 0.76 s apart, for the current rate integral and for the AHRS output, normal / good grade;
   apparent-rocking ripple ratio of the inclinometer and AHRS outputs during a probe (0.3-0.5 deg apparent at C1,
   reduced model, ground_contact.py docstring) against the Q1 gate 0.15 x 0.0236 deg.
3. Quantisation: worst error of the window-mean difference with LSB q without dither.
Usage: python -I -B imuatt_probe.py <out.json>
"""
import json
import math
import sys

import numpy as np

DEG = math.pi / 180
MODES = {"top": [(1.784, 26.8), (2.984, 130.5)], "middle": [(2.309, 50.7), (3.509, 231.7)],
         "bottom": [(2.857, 87.4), (3.928, 361.3)]}
AMP = {"top": 0.031, "middle": 0.021, "bottom": 0.016}  # deg, assumed true rocking (2.3)


def lp(s, tau, n):
    return 1.0 / (1.0 + tau * s) ** n


def h_acc_B(s, fc):
    wc = 2 * math.pi * fc
    kP, kI = 2 * wc, wc * wc
    return (kP * s + kI) / (s * s + kP * s + kI)


def sensor_gain(kind, s, G, par):
    """Sensor output per unit true rocking attitude at that mode (accelerometer tilt = G x attitude)."""
    if kind == "S0":
        return G
    if kind == "A":
        return G * lp(s, 1 / (2 * math.pi * par), 2) * np.exp(-0.02 * s)
    if kind == "B":
        return (1 + (G - 1) * h_acc_B(s, par)) * np.exp(-0.01 * s)
    raise ValueError(kind)


SENSORS = {"S0": ("S0", None), "A_f1.0": ("A", 1.0), "A_f0.5": ("A", 0.5), "A_f0.3": ("A", 0.3),
           "B_c0.05": ("B", 0.05), "B_c0.1": ("B", 0.1), "B_c0.02": ("B", 0.02)}
ripple = {}
for name, (kind, par) in SENSORS.items():
    for tau_f in (0.8, 0.4):
        worst_ctrl = worst_comp = 0.0
        where = None
        for lvl, modes in MODES.items():
            for f, G in modes:
                s = 2j * math.pi * f
                y = AMP[lvl] * abs(sensor_gain(kind, s, G, par)) * abs(lp(s, tau_f, 2))
                yc = y * abs(lp(s, 1.0, 1))
                if y > worst_ctrl:
                    worst_ctrl, worst_comp, where = y, yc, f"{lvl} {f} Hz"
        ripple[f"{name}_tf{tau_f}"] = {"ctrl_ripple_deg": worst_ctrl, "completion_ripple_deg": worst_comp,
                                       "worst_mode": where}

# --- probe cue noise (window difference) -----------------------------------------------------------------
TAU_W, DT_C = 0.3, 0.760
f = np.logspace(-5, 2.5, 400000)
w = 2 * np.pi * f
s = 1j * w
win = np.sinc(f * TAU_W) * (np.exp(1j * w * DT_C) - 1)  # mean over 0.3 s, difference 0.76 s apart
GRADES = {"good": (0.15, 15.0), "normal": (0.30, 82.0)}  # ARW deg/sqrt(h), accel density ug/sqrt(Hz)
cue = {}
for g, (arw, acc_ug) in GRADES.items():
    d_rate = arw / 60.0 * DEG                 # rad/s/sqrt(Hz) one-sided -> two-sided below via factor
    s_rate = d_rate ** 2                      # one-sided PSD of rate noise [rad^2/s^2/Hz]
    s_tilt = (acc_ug * 1e-6) ** 2             # tilt PSD [rad^2/Hz] (small angle, 1 g)
    # current: integral of the rate, 1/s
    var_cur = np.trapezoid(s_rate * np.abs(win / s) ** 2, f)
    for fc in (0.02, 0.05, 0.1):
        wc = 2 * math.pi * fc
        kP, kI = 2 * wc, wc * wc
        den = s * s + kP * s + kI
        g_gyro = s / den                      # rate noise -> attitude
        g_acc = (kP * s + kI) / den           # tilt noise -> attitude
        var_B = np.trapezoid((s_rate * np.abs(g_gyro) ** 2 + s_tilt * np.abs(g_acc) ** 2) * np.abs(win) ** 2, f)
        cue[f"{g}_B_c{fc}"] = math.sqrt(var_B) / DEG
    cue[f"{g}_current"] = math.sqrt(var_cur) / DEG
    cue[f"{g}_current_formula"] = arw / 60.0 * math.sqrt(DT_C - TAU_W / 3)  # spec 10.3 (deg)
RESP = 0.0118 * 2  # deg, FL 2 mm
cue_z = {k: 0.5 * RESP / v for k, v in cue.items()}

# --- apparent rocking ripple ratio during a probe (Q1 gate 0.15) --------------------------------------
APP = (0.3, 0.5)  # deg apparent at C1 during a probe (reduced model)
probe_ripple = {}
for name, (kind, par) in SENSORS.items():
    rows = {}
    for f_r, G in MODES["top"]:
        s_r = 2j * math.pi * f_r
        true_amp = [a / G for a in APP]
        out_amp = [t * abs(sensor_gain(kind, s_r, G, par)) for t in true_amp]
        rows[f"{f_r}Hz"] = {"out_amp_deg": out_amp, "ptp_ratio_to_response": [2 * a / RESP for a in out_amp]}
    probe_ripple[name] = rows
probe_ripple["note"] = "S0 row = accelerometer tilt (the cue uses the gyro integral instead: true rocking only)"

# --- quantisation ---------------------------------------------------------------------------------------
quant = {f"lsb_{q}": {"window_diff_worst_deg": q, "ratio_error_worst": q / RESP, "q_over_gate": q / (0.5 * RESP),
                      "single_step_ripple_ratio": q / RESP}
         for q in (0.01, 0.005, 0.001, 0.0005)}

json.dump({"ripple": ripple, "cue_sigma_deg": cue, "cue_z": cue_z, "probe_ripple": probe_ripple,
           "quantisation": quant, "response_deg": RESP}, open(sys.argv[1], "w"), indent=1)
for k, v in ripple.items():
    print("ripple", k, {a: (round(b, 5) if isinstance(b, float) else b) for a, b in v.items()})
for k, v in cue.items():
    print("cue", k, round(v, 5), "z", round(cue_z[k], 2))
for k, v in probe_ripple.items():
    print("probe", k, v)
