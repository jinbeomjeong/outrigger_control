"""P7-7 window: T4h reads of the FL first probe round (Mslow c2, M c2) and the hand need of
``check_open_delay.retract_dead`` (formula copied, unchanged) from the read inputs.

Usage: python -I -B s09_p77.py <t4h dir>
"""
import math
import sys
from pathlib import Path

import numpy as np

T4H = Path(sys.argv[1])
A_H = 0.013273229        # front head area (T4h meta valve_constants)
A_ANN = 0.00376991118    # front annulus
S_MAX, L0, P_T = 0.70, 0.05, 2e5
V_LINE, BETA_HOSE, PSI, P_CR = 285e-6, 0.5e9, 3.5, 3e5
SETS = {"Mslow": dict(beta=0.69e9, s_l=1.5, s_d=1.5), "M": dict(beta=1.0e9, s_l=1.0, s_d=1.0)}


def retract_dead(p_h, p_r, band, s, void, beta, s_l, s_d):
    """check_open_delay.retract_dead (VN: rod_forward, delta = p_crack) with the P1 patch
    split volumes (v_line * s_l, L0 * s_d, beta of P1, volume_scale 1)."""
    v_line = V_LINE * s_l
    l0r = l0h = L0 * s_d
    p_h = max(p_h, 0.0)
    delta = P_CR
    drive = p_h + P_CR - P_T
    p_free = max(drive / PSI, 0.0)
    if A_ANN * (p_free - delta - p_r) > band:
        p_b = (drive - (A_ANN * (delta + p_r) + band) / A_H) / (PSI - A_ANN / A_H)
    else:
        p_b = p_free
    p_rod = max(p_b - delta, p_r)
    dp_h = max(A_ANN * (p_rod - p_r) - band, 0.0) / A_H
    v_head = A_H * (l0h + s)
    v_rod = A_ANN * (l0r + S_MAX - s)
    volume = (v_line * max(p_b - P_T, 0.0) / BETA_HOSE + v_rod * (p_rod - p_r) / beta
              + A_ANN * v_head * dp_h / (beta * A_H))
    parts = {"line": v_line * max(p_b - P_T, 0.0) / BETA_HOSE / A_ANN,
             "rod": v_rod * (p_rod - p_r) / beta / A_ANN,
             "head": v_head * dp_h / (beta * A_H)}
    return volume / A_ANN + void, p_b, p_rod, parts


for plant, name in (("Mslow", "R12_top-FR-Fs0-o0.0_P7-Mslow-c2.npz"),
                    ("M", "R12_top-FR-Fs0-o0.0_P7-M-c2.npz")):
    with np.load(T4H / name, allow_pickle=False) as d:
        t = d["t_s"]
        sel = np.flatnonzero((t >= 31.8) & (t <= 34.0))
        print(f"== {plant} {name} FL")
        print("  t   lk dir cmd_mm_s valve_mm_s x_mm need_mm drain_mm_s head_bar rod_bar stroke_mm band_N | hand_need(void0) p_b p_rod parts")
        for k in sel:
            ph, pr = float(d["head_pressure_Pa"][k, 0]), float(d["rod_pressure_Pa"][k, 0])
            s, band = float(d["motor_stroke_m"][k, 0]), float(d["seal_band_N"][k, 0])
            need_h, p_b, p_rod, parts = retract_dead(ph, pr, band, s, 0.0, **SETS[plant])
            print(f"  {t[k]:6.2f} {int(d['locked'][k, 0])} {int(d['p1_line_dir'][k, 0]):2d} "
                  f"{d['command_m_s'][k, 0] * 1e3:7.3f} {d['p1_valve_speed_m_s'][k, 0] * 1e3:7.3f} "
                  f"{d['p1_x_m'][k, 0] * 1e3:7.4f} {d['p1_need_m'][k, 0] * 1e3:7.4f} "
                  f"{d['p1_drain_m_s'][k, 0] * 1e3:7.4f} {ph / 1e5:8.3f} {pr / 1e5:7.3f} "
                  f"{s * 1e3:8.3f} {band:7.1f} | {need_h * 1e3:7.4f} {p_b / 1e5:7.3f} "
                  f"{p_rod / 1e5:7.3f} " + " ".join(f"{k2}={v * 1e3:.4f}" for k2, v in parts.items()))
