"""Independent reference times for T-JR-03 (tracker gate, R12 RR) and T-JR-06 (P1 plant, FL).

Path B1: continuous ODE of the line fill with the VN neutral drain (scipy solve_ivp, event),
         exact first-order valve lag  u_v(t) = u1 + (u0 - u1) exp(-t / tau).
Path B2: the same ODE stepped with 1 ms sub-steps and the exact mean valve over the sub-step
         (the discretisation the tracker uses), opening reported at the sub-step end.
Path B0: drain-free closed form (the spec 2.4 hand value).
No repo code is imported. SI units, gauge pressures; printed in ms / bar / cm3.

Line fill (spec 2.4):  dx/dt = k max(u_v, 0) - K_n g sqrt(max(p_A - p_T, 0)) / A_h,
  p_A = p_T + x A_h beta / V,  g = (1 - |u_v| / (c_v v_max))^+,  K_n = f_n A_h v_max / sqrt(dp_c)
Open: p_A >= p_open (head check; the psi p_B help is left out: later opening).
ASSUMPTIONS: values of spec 2.4 table (V 285 cm3, beta 0.5 GPa, p_cr 3 bar, p_T 2 bar,
f_n 0.05, c_v 0.02, dp_c 10 bar, v_max 20.924 mm/s, tau 0.1 s).
"""

import json
import math
import sys

from scipy.integrate import solve_ivp

BAR = 1e5
V_LINE, BETA, P_CR, P_T = 285e-6, 0.5e9, 3e5, 2e5
F_N, C_V, DP_C, V_MAX, TAU = 0.05, 0.02, 10e5, 20.924e-3, 0.1
A_H = {"front": 1.327e-2, "rear": 9.503e-3}


def valve(t, u0, u1):
    return u1 + (u0 - u1) * math.exp(-t / TAU)


def mean_valve(t0, dt, u0, u1):
    a = (u0 - u1) * TAU / dt * (math.exp(-t0 / TAU) - math.exp(-(t0 + dt) / TAU))
    return u1 + a


def rhs(t, x, area, k, u0, u1, drain):
    u = valve(t, u0, u1)
    k_n = F_N * area * V_MAX / math.sqrt(DP_C)
    g = max(1.0 - abs(u) / (C_V * V_MAX), 0.0)
    p_a = P_T + x[0] * area * BETA / V_LINE
    d = k_n * g * math.sqrt(max(p_a - P_T, 0.0)) / area if drain else 0.0
    rate = k * max(u, 0.0) - d
    if x[0] <= 0.0 and rate < 0.0:
        rate = 0.0
    return [rate]


def open_time_ode(area, k, u0, u1, p_open, drain=True):
    x_need = (p_open - P_T) * V_LINE / (BETA * area)
    event = lambda t, x, *a: x[0] - x_need  # noqa: E731
    event.terminal, event.direction = True, 1
    sol = solve_ivp(rhs, (0.0, 2.0), [0.0], args=(area, k, u0, u1, drain), events=event,
                    max_step=1e-4, rtol=1e-10, atol=1e-14)
    return float(sol.t_events[0][0]), x_need


def open_time_substep(area, k, u0, u1, p_open, dt=1e-3, drain=True):
    k_n = F_N * area * V_MAX / math.sqrt(DP_C)
    x, t = 0.0, 0.0
    for n in range(4000):
        u = mean_valve(t, dt, u0, u1)
        g = max(1.0 - abs(u) / (C_V * V_MAX), 0.0)
        p_a = P_T + x * area * BETA / V_LINE
        d = k_n * g * math.sqrt(max(p_a - P_T, 0.0)) / area if drain else 0.0
        x = max(x + (k * max(u, 0.0) - d) * dt, 0.0)
        t = (n + 1) * dt
        if P_T + x * area * BETA / V_LINE >= p_open:
            return t
    return math.nan


def main():
    out = {}
    # T-JR-03: R12 RR, tracker gate (kappa 0.8, e_h 9 bar), head 35.2 bar, valve 0.0749 -> 4.71
    p_open = 35.2 * BAR + 9 * BAR + P_CR
    t_ode, x_need = open_time_ode(A_H["rear"], 0.8, 0.0749e-3, 4.71e-3, p_open)
    t_ode0, _ = open_time_ode(A_H["rear"], 0.8, 0.0749e-3, 4.71e-3, p_open, drain=False)
    out["T_JR_03"] = {
        "need_cm3": x_need * A_H["rear"] * 1e6,
        "B0_drain_free_ms": t_ode0 * 1e3,
        "B1_ode_with_drain_ms": t_ode * 1e3,
        "B2_substep_1ms_with_drain_ms": open_time_substep(
            A_H["rear"], 0.8, 0.0749e-3, 4.71e-3, p_open) * 1e3,
        "B2_substep_1ms_drain_free_ms": open_time_substep(
            A_H["rear"], 0.8, 0.0749e-3, 4.71e-3, p_open, drain=False) * 1e3,
    }
    # T-JR-06: P1 plant (kappa 1), lifted FL head ~87 bar, valve from rest to 4.71 mm/s
    for head_bar in (35.2, 87.0):
        p_open = head_bar * BAR + P_CR
        t1, x1 = open_time_ode(A_H["front"], 1.0, 0.0, 4.71e-3, p_open)
        t0, _ = open_time_ode(A_H["front"], 1.0, 0.0, 4.71e-3, p_open, drain=False)
        out[f"T_JR_06_front_head_{head_bar:g}bar"] = {
            "need_cm3": x1 * A_H["front"] * 1e6, "drain_free_ms": t0 * 1e3,
            "with_drain_no_psi_ms": t1 * 1e3}
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
