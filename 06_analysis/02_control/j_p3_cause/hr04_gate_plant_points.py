"""P1 CheckOpenGate review points (read only; uses hr02_gate_check functions).

1. HOLD premise: steady line pressure of the VN line at a micro command (fill = neutral bleed) and
   the head / rod pressures below which the plant would still release under |u| <= u_hold.
2. Rod check first (M1c E2 left out): time from the rod check release to the head check opening
   and the equalised B pressure the gate plant does not apply to the rod chamber in between.
Units SI inside; printed bar / ms; gauge pressures.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hr02_gate_check as g  # noqa: E402

BAR = 1e5
OUT = Path(__file__).with_suffix(".json")


def steady_line_pressure(u):
    """VN line with a steady micro command: |u| = f_n g v_max sqrt((p_A - p_T) / dp_c)."""
    gate = max(1 - u / (g.C_V * g.V_MAX), 0.0)
    if gate == 0.0:
        return math.inf
    return g.P_T + g.DP_C * (u / (g.F_N * gate * g.V_MAX)) ** 2


def main():
    res = {"hold": [], "rod_first": []}
    for frac in (1e-4, 1e-3, 0.0036, 0.005, 0.01, 0.015, 0.02):
        u = frac * g.V_MAX
        p_a = steady_line_pressure(u)
        rod_release_below = g.P_T + g.PSI * (p_a - g.P_T) - g.P_CR
        # head check with p_B = min(equalised, p_r) <= p_r: best case p_r at the rod release limit
        p_b = max(min(rod_release_below, rod_release_below), g.P_FLOOR)
        head_release_below = p_a + g.PSI * p_b - g.P_CR
        res["hold"].append({"u_frac_vmax": frac, "u_mm_s": u * 1e3,
                            "p_A_ss_bar": p_a / BAR if math.isfinite(p_a) else None,
                            "rod_check_opens_if_p_r_below_bar":
                                rod_release_below / BAR if math.isfinite(p_a) else None,
                            "head_check_opens_if_p_h_below_bar_at_best_p_r":
                                head_release_below / BAR if math.isfinite(p_a) else None})
    for leg in ("front", "rear"):
        for u_ext in (1e-3, 4.71e-3, g.V_MAX):
            p_a = g.ext_line(leg, 0.0, u_ext)
            ph, pr = (a.ravel() for a in np.meshgrid(np.array([20, 35, 77, 150]) * BAR,
                                                     np.array([2, 13, 30, 54]) * BAR,
                                                     indexing="ij"))
            k_head, k_rod = g.plant_ext_open(leg, p_a, ph, pr, np.zeros_like(ph))
            c_r = g.A_ANN[leg] * (g.L0 + g.S_MAX - 0.395) / g.BETA
            c_l = g.V_LINE / g.BETA_H
            for h, r, kh, kr in zip(ph, pr, k_head, k_rod):
                p_b_after = (c_r * r + c_l * g.P_T) / (c_r + c_l)
                res["rod_first"].append({
                    "leg": leg, "u_mm_s": u_ext * 1e3, "p_h_bar": h / BAR, "p_r_bar": r / BAR,
                    "rod_release_ms": int(kr) + 1, "head_open_ms": int(kh) + 1,
                    "rod_first_window_ms": int(kh) - int(kr),
                    "p_B_equalised_bar": p_b_after / BAR,
                    "rod_drop_not_applied_bar": (r - p_b_after) / BAR})
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["hold"], indent=1))
    worst = sorted(res["rod_first"], key=lambda x: -x["rod_first_window_ms"])[:8]
    print(json.dumps(worst, indent=1))
    r12 = [x for x in res["rod_first"] if x["leg"] == "rear" and x["p_h_bar"] == 35
           and x["p_r_bar"] == 54]
    print(json.dumps(r12, indent=1))


if __name__ == "__main__":
    main()
