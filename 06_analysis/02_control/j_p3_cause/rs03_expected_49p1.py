"""Expected values of the J-P3 remedy at the R12 RR 49.1 s read (read only, repo code imported).

Path A: repo functions (ExtendStartTracker, flow_limited_rod_pressure, CheckOpenDelay).
Path B: closed-form hand formulas for the same quantities (line fill volume, C_r, relief rate).

Units: SI internally, printed in bar / ms / cm3. Gauge pressures. Leg RR (index 3).
All inputs not taken from the records are ASSUMPTIONS stated in the printout.
"""
import json
import math
import sys

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")

from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    BoundGeometry, ExtendStartBound, ExtendStartTracker)
from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit, CheckDelayInputs, CheckOpenDelay)
from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    RodPressureFlowLaw, flow_limited_rod_pressure)
from outrigger_sim.hydraulics.v5_options import CheckDelaySetting  # noqa: E402

BAR = 1e5
A_H = np.array([1.327e-2, 1.327e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
LEG = 3
V_MAX = 20.924e-3
TAU_V = 0.1
S = 0.395
S_MAX = 0.70
U_PREV = 0.0749e-3      # acting command of the 49.0 s period (T4h, cause report 2.2)
U_EXT = 4.71e-3         # acting command of the 49.1 s period
P_LOCKED_49 = 53.9e5    # physical locked rod pressure at 49.0 s (hydraulics_review 4, VB)
P_HEAD_49 = 35.2e5      # head pressure at 49.0 s from F 16.8 kN and p_r 53 bar (ASSUMPTION)
BOUND4_49 = 70.0e5      # ④ at 49.0 s, M 13 bar + 1.355 (77.3 - 35.2) bar (ASSUMPTION)


def tracker_relief(start_Pa, gate_open_substep):
    """Path A: one 0.1 s period of the ③ tracker from start_Pa, relief counted only from
    sub-step gate_open_substep on (emulating the rev-5 line-fill gate)."""
    geometry = BoundGeometry(tuple(A_H), tuple(A_ANN), S_MAX, V_MAX, TAU_V)
    tracker = ExtendStartTracker(ExtendStartBound(), geometry, np.full(4, start_Pa))
    tracker.valve_m_s[:] = U_PREV
    command = np.zeros(4)
    command[LEG] = U_EXT
    compliance = [tracker.compliance_m3_Pa(i, S) for i in range(4)]
    for k in range(100):
        is_end = np.zeros(4, bool)
        if k < gate_open_substep:
            is_end[LEG] = True  # no relief counted (same branch as the stroke-end rule)
        tracker._substep(command, command < 0.0, is_end, compliance)
    return tracker.pressure_Pa[LEG], compliance[LEG]


def plant_relief(start_Pa, open_s, step_s=5e-4):
    """Path A: plant M2 r5 relief of the moving rod pressure after release at open_s inside
    the period (nominal plant C_r, target 5 bar ASSUMPTION, valve lag from U_PREV)."""
    beta, l0 = 1.0e9, 0.05
    e_op = 0.3909
    k_h = beta * A_H[LEG] / (l0 + e_op)
    k_r = beta * A_ANN[LEG] / (l0 + S_MAX - e_op)
    c_r = RodPressureFlowLaw().rod_compliance_m3_Pa(A_ANN[LEG], k_h, k_r)
    p = start_Pa
    valve = U_PREV
    t = 0.0
    keep = math.exp(-step_s / TAU_V)
    while t < 0.1 - 1e-12:
        valve = U_EXT + (valve - U_EXT) * keep
        t += step_s
        if t > open_s:
            p = flow_limited_rod_pressure(p, 5.0e5, valve, step_s, 0.05, c_r, A_H[LEG],
                                          A_ANN[LEG], False)
    return p, c_r


def m1c_open_time(p_head_Pa, p_rod_Pa, kind="VN"):
    """Path A: first opening of the head check (extension) with M1c, chunk 1 ms, valve lag."""
    circuit = CheckDelayCircuit(A_H.copy(), A_ANN.copy(), S_MAX, 0.05, 0.05, 1.0e9, 2.0e5,
                                V_MAX, 10.0e5)
    model = CheckOpenDelay(CheckDelaySetting(kind=kind), circuit)
    valve = U_PREV
    keep = math.exp(-1e-3 / TAU_V)
    rod_open = None
    for k in range(400):
        start = valve
        valve = U_EXT + (valve - U_EXT) * keep
        mean = U_EXT + (start - U_EXT) * (TAU_V / 1e-3) * (1 - keep)
        u = np.zeros(4)
        u[LEG] = mean
        inputs = CheckDelayInputs(k * 1e-3, 1e-3, u, np.full(4, p_head_Pa),
                                  np.full(4, p_rod_Pa), np.ones(4, bool), np.zeros(4),
                                  np.zeros(4), np.full(4, S))
        out = model.filter(inputs)
        if rod_open is None and model.rod_released[LEG]:
            rod_open = (k + 1) * 1e-3
        if model.is_open[LEG]:
            return rod_open, (k + 1) * 1e-3
    return rod_open, None


def hand_fill_time(volume_m3, area_m2, speed_factor=1.0):
    """Path B: t with area * k * U_EXT * (t - tau (1 - exp(-t/tau))) + start term = volume."""
    lo, hi = 0.0, 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        x = U_EXT * (mid - TAU_V * (1 - math.exp(-mid / TAU_V))) \
            + U_PREV * TAU_V * (1 - math.exp(-mid / TAU_V))
        if area_m2 * speed_factor * x < volume_m3:
            lo = mid
        else:
            hi = mid
    return hi


def main():
    out = {"assumptions": {"P_locked_49_bar": P_LOCKED_49 / BAR, "p_head_49_bar": P_HEAD_49 / BAR,
                           "bound4_49_bar": BOUND4_49 / BAR, "u_prev_mm_s": U_PREV * 1e3,
                           "u_ext_mm_s": U_EXT * 1e3}}
    out["u_hold_mm_s"] = 0.01 * V_MAX * 1e3
    rod_open, head_open = m1c_open_time(P_HEAD_49, P_LOCKED_49)
    out["m1c_VN_rod_check_open_ms"] = None if rod_open is None else rod_open * 1e3
    out["m1c_VN_head_check_open_ms"] = None if head_open is None else head_open * 1e3
    rod_open_bl, head_open_bl = m1c_open_time(P_HEAD_49, P_LOCKED_49, "BL")
    out["m1c_BL_head_check_open_ms"] = None if head_open_bl is None else head_open_bl * 1e3
    v_line, beta_h = 285e-6, 0.5e9
    need_head = v_line / beta_h * (P_HEAD_49 + 3e5 - 2e5)
    out["hand_head_fill_cm3"] = need_head * 1e6
    out["hand_head_open_ms_k1"] = hand_fill_time(need_head, A_H[LEG], 1.0) * 1e3
    need_head_ub = v_line / beta_h * (P_HEAD_49 + 5e5 + 3e5 - 2e5)
    out["hand_tracker_gate_open_ms_k0p8_eh5"] = hand_fill_time(need_head_ub, A_H[LEG], 0.8) * 1e3
    for gate_ms in (0, int(round(out["hand_tracker_gate_open_ms_k0p8_eh5"])), 100):
        p_bound, c_bar = tracker_relief(BOUND4_49, gate_ms)
        out[f"tracker_p_hat_49p1_bar_gate{gate_ms}ms"] = p_bound / BAR
    out["tracker_C_r_bar_m3_Pa"] = c_bar
    open_s = (head_open or 0.067)
    p_plant, c_r = plant_relief(P_LOCKED_49, open_s)
    out["plant_C_r_m3_Pa"] = c_r
    out["plant_p_tr_49p1_bar_open_at_m1c_head"] = p_plant / BAR
    p_plant67, _ = plant_relief(P_LOCKED_49, 0.067)
    out["plant_p_tr_49p1_bar_open_67ms"] = p_plant67 / BAR
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
