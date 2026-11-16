"""Expected values of T-JR-04 case (11b) (read only, no repo import).

Worst case the comparison principle allows: the P3 plant leaves its lock at the very sub-step the
tracker gate opens, so the trapped rod pressure is whole at the gate opening. Then a short RET
at s, then a hold (zero flow). P3 branch (c) only (the lag target assumed below: ASSUMPTION):
  p^k = p^{k-1} - A_ann s [sqrt((p_h^{k-1} - p_T)^+ / (p_bA - p_T)) - 1]^+ dt / C_r,
  p_h^{k-1} = (F + A_ann p^{k-1}) / A_h.
Rear leg, F fixed. Bounds: revision 5 ed. 3 hold bound = retract model 13 + p_h/3 bar (window
candidate after a retraction); ed. 4 R5-7 adds p_hat + delta_m with p_hat >= the seeded ④.
Units SI inside, bar / kN printed.
"""

import json
import math
import sys

BAR = 1e5
A_H, A_ANN = 9.503e-3, 3.142e-3
C_R = 1.586e-12
P_T, P_BA = 2e5, 5e5
DT = 5e-4


def run(p0_bar, force_kN, speed_mm_s, ret_s):
    p = p0_bar * BAR
    f = force_kN * 1e3
    s = speed_mm_s * 1e-3
    for _ in range(round(ret_s / DT)):
        p_h = (f + A_ANN * p) / A_H
        factor = max(math.sqrt(max(p_h - P_T, 0.0) / (P_BA - P_T)) - 1.0, 0.0)
        p -= A_ANN * s * factor * DT / C_R
    p_h = (f + A_ANN * p) / A_H
    model = 13e5 + p_h / 3.0
    return {"p0_bar": p0_bar, "F_kN": force_kN, "s_mm_s": speed_mm_s, "ret_s": ret_s,
            "p_tr_at_hold_bar": p / BAR, "p_h_at_hold_bar": p_h / BAR,
            "ed3_hold_bound_bar": model / BAR, "ed3_gap_bar": (model - p) / BAR,
            "ed4_bound_floor_bar": p0_bar + 0.5, "ed4_gap_floor_bar": p0_bar + 0.5 - p / BAR,
            "ed3_F_lb_kN": (p_h * A_H - model * A_ANN) / 1e3}


rows = [run(59.9, 14.8, 0.3, t) for t in (0.1, 0.2, 0.5)]
rows += [run(59.9, 14.8, 1.0, t) for t in (0.1, 0.2)]
rows += [run(60.0, 5.0, 0.3, 0.2)]
json.dump(rows, sys.stdout, indent=1)
