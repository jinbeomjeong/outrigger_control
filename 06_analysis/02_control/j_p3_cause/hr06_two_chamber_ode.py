"""Independent check of the P3 branch (c) rate: two-chamber cylinder ODE (read only).

States s, v, p_h, p_r of one rear (RR) cylinder retracting against a constant net load F
(piston + rod mass 107 kg, heavy viscous damping so the piston follows quasi-statically):

    m dv/dt = p_h A_h - p_r A_ann - F - c v
    V_h / beta dp_h/dt = -A_h v - Q_AT,   Q_AT = K_AT sqrt((p_h - p_T)+),  K_AT = A_h |u| / sqrt(p_bA - p_T)
    V_r / beta dp_r/dt =  A_ann v + A_ann |u|                              (meter-in, compensated)

The quasi-static rod pressure rate is compared with branch (c) of hr01:
    dp_r/dt = -A_ann |u| (sqrt((p_h - p_T) / (p_bA - p_T)) - 1) / C_r,  C_r = A_ann^2 (1/k_r + 1/k_h)
Path B (this file, scipy Radau) vs path A (closed form). Gauge pressures; SI; printed bar/s.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

OUT = Path(__file__).with_suffix(".json")
BAR = 1e5
A_H = math.pi / 4 * 0.11**2
A_ANN = math.pi / 4 * (0.11**2 - 0.09**2)
BETA, L0, S_MAX, E_OP = 1.0e9, 0.05, 0.70, 0.3909
P_T, P_BA = 2e5, 5e5
M_ROD = 107.0


def main():
    res = []
    k_h = BETA * A_H / (L0 + E_OP)
    k_r = BETA * A_ANN / (L0 + S_MAX - E_OP)
    c_r = A_ANN**2 * (1 / k_r + 1 / k_h)
    c_damp = 2.0 * math.sqrt((k_h + k_r) * M_ROD) * 0.7   # zeta 0.7: ringing gone in ~8 ms
    for f_kN, p_r0_bar, u in ((22.0, 50.0, 1e-3), (10.0, 50.0, 1e-3), (50.0, 54.0, 4.71e-3),
                              (0.0, 40.0, 4.71e-3)):
        force = f_kN * 1e3
        k_at = A_H * u / math.sqrt(P_BA - P_T)

        def rhs(_t, y, force=force, k_at=k_at, u=u):
            s, v, p_h, p_r = y
            v_h = A_H * (L0 + s)
            v_r = A_ANN * (L0 + S_MAX - s)
            q_at = k_at * math.sqrt(max(p_h - P_T, 0.0))
            return [v, (p_h * A_H - p_r * A_ANN - force - c_damp * v) / M_ROD,
                    BETA / v_h * (-A_H * v - q_at), BETA / v_r * (A_ANN * v + A_ANN * u)]

        p_r0 = p_r0_bar * BAR
        p_h0 = (force + p_r0 * A_ANN) / A_H
        sol = solve_ivp(rhs, (0.0, 0.2), [E_OP, -u, p_h0, p_r0], method="Radau",
                        rtol=1e-9, atol=[1e-12, 1e-12, 1.0, 1.0], dense_output=True,
                        max_step=1e-4)
        rows = []
        for t in (0.03, 0.06, 0.1):
            s, v, p_h, p_r = sol.sol(t)
            dp = (sol.sol(t + 5e-3)[3] - sol.sol(t - 5e-3)[3]) / 1e-2   # 10 ms mean rate
            p_h_qs = (force + p_r * A_ANN) / A_H
            closed = -A_ANN * u * max(math.sqrt(max(p_h_qs - P_T, 0) / (P_BA - P_T)) - 1, 0) / c_r
            rows.append({"t_s": t, "p_r_bar": p_r / BAR, "p_h_bar": p_h / BAR,
                         "p_h_quasi_static_bar": p_h_qs / BAR, "damper_force_N": c_damp * v,
                         "ode_rate_bar_s": dp / BAR, "closed_rate_bar_s": closed / BAR,
                         "rel_diff": (dp - closed) / closed if closed != 0 else None})
        res.append({"F_kN": f_kN, "p_r0_bar": p_r0_bar, "u_mm_s": u * 1e3, "rows": rows,
                    "c_damp_N_s_m": c_damp})
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
