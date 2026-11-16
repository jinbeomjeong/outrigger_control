"""Can the RR micro commands (48.6..49.0 s) open a pilot check?  Line-fill check, RR leg.

Independent of the harness code. Blocked-centre line (BL, no neutral bleed = fastest opening):
  valve u_v: first-order lag tau_v 0.1 s of the acting command (10 Hz, d = 1)
  delivered q = A u_v with an optional overlap cut |u_v| <= u_ol -> 0 (no deadband compensation);
  with compensation (spec 2.5 L-6 ASSUMPTION) no cut.
  line: dp_line/dt = q beta_hose / V_line (A line for extension, B line for retraction), from p_T.
Openings (M1c formulas, check_open_delay.py, VN p_ref = p_T):
  extension, rod check (piloted by A):  p_T + psi (p_A - p_T) - p_r - p_cr > 0
  extension, head check (free flow):    p_A + psi p_B - p_h - p_cr > 0, p_B = p_T
  retraction, head check (piloted by B): p_T + psi (p_B - p_T) - p_h - p_cr > 0
  retraction, rod check (free flow):    p_B - p_r - p_cr > 0
Trapped RR pressures (physical counterfactual, c01): p_r 48.5 -> 53.9 bar, p_h 39.9 -> 35.5 bar
(48.8 -> 49.0 s, VB); 48.6 s: p_r 39.3, p_h 47.4 bar.
All valve/line values are the M1c ASSUMPTIONS (V_line 285 cm3, beta_hose 0.5 GPa, psi 3.5,
p_cr 3 bar, p_T 2 bar). Usage: python -I -B c02_line_fill.py <out_json>
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1"
           r"\h10_reuse_rerun_t4h\R12_bottom-FL-Fs4-o0.0_VB.npz")
A_H = math.pi / 4 * 0.110 ** 2
A_ANN = math.pi / 4 * (0.110 ** 2 - 0.090 ** 2)
V_LINE, BETA_HOSE, PSI, P_CR, P_T = 285e-6, 0.5e9, 3.5, 3e5, 2e5
V_MAX = 0.020924
TAU_V = 0.1
DT = 1e-4


def p_trapped(t):
    """Physical trapped RR pressures (piecewise linear through the c01 VB values)."""
    ts = [48.6, 48.7, 48.8, 48.9, 49.0, 49.2]
    pr = [39.31, 42.04, 48.49, 52.88, 53.92, 53.92]
    ph = [47.38, 45.15, 39.90, 36.33, 35.48, 35.48]
    return np.interp(t, ts, pr) * 1e5, np.interp(t, ts, ph) * 1e5


def run(overlap_ratio, t_end=49.3):
    z = np.load(T4H, allow_pickle=True)
    t10 = z["t_s"]
    out = z["command_m_s"][:, 3]
    u_ol = overlap_ratio * V_MAX
    t, uv = 48.6, 0.0
    pA = pB = P_T
    first = {}
    vol = {"A": 0.0, "B": 0.0}
    while t < t_end:
        k = int(np.searchsorted(t10, t + 1e-9)) - 1   # read at or before t
        u_act = float(out[k])  # output of read k acts on (t_k, t_k + T] (d = 1)
        uv += (u_act - uv) * (1 - math.exp(-DT / TAU_V))
        q_speed = 0.0 if abs(uv) <= u_ol else uv
        if q_speed > 0:
            dV = A_H * q_speed * DT
            vol["A"] += dV
            pA += dV * BETA_HOSE / V_LINE
        elif q_speed < 0:
            dV = A_ANN * (-q_speed) * DT
            vol["B"] += dV
            pB += dV * BETA_HOSE / V_LINE
        pr, ph = p_trapped(t)
        checks = {
            "ext_rod_check": P_T + PSI * (pA - P_T) - pr - P_CR > 0,
            "ext_head_check": pA + PSI * pB - ph - P_CR > 0,
            "ret_head_check": P_T + PSI * (pB - P_T) - ph - P_CR > 0,
            "ret_rod_check": pB - pr - P_CR > 0,
        }
        for name, ok in checks.items():
            if ok and name not in first:
                first[name] = round(t, 4)
        if abs(t - 49.0) < DT / 2:
            first["volume_A_at_49.0_cm3"] = vol["A"] * 1e6
            first["p_A_at_49.0_bar"] = pA / 1e5
        t += DT
    need_rod_A = ((48.49e5 + P_CR - P_T) / PSI) * V_LINE / BETA_HOSE  # volume to vent rod @48.8
    return {"overlap_ratio": overlap_ratio, "u_ol_mm_s": u_ol * 1e3, "first_open_s": first,
            "line_volume_cm3": {k: v * 1e6 for k, v in vol.items()},
            "p_A_end_bar": pA / 1e5, "p_B_end_bar": pB / 1e5,
            "vol_to_open_rod_check_ext_cm3": need_rod_A * 1e6}


def main():
    res = [run(r) for r in (0.0, 0.01, 0.02, 0.05)]
    # one-period opening speed: u such that A u T fills the line to the rod-check pilot pressure
    one = {}
    for pr_bar in (2.0, 13.0, 30.6, 54.0):
        dp = (pr_bar * 1e5 + P_CR - P_T) / PSI
        one[f"p_r {pr_bar} bar"] = {"ext_rod_check_u_mm_s": dp * V_LINE / BETA_HOSE / (A_H * 0.1) * 1e3}
    for ph_bar in (35.5, 47.4, 77.0):
        dp_ret = (ph_bar * 1e5 + P_CR - P_T) / PSI
        one[f"p_h {ph_bar} bar"] = {
            "ret_head_check_u_mm_s": dp_ret * V_LINE / BETA_HOSE / (A_ANN * 0.1) * 1e3,
            "ext_head_check_u_mm_s": max(ph_bar * 1e5 + P_CR - PSI * P_T - P_T, 0) * V_LINE
            / BETA_HOSE / (A_H * 0.1) * 1e3}
    out = {"runs": res, "one_period_opening_speed": one}
    for r in res:
        print(json.dumps(r))
    print(json.dumps(one, indent=1))
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
