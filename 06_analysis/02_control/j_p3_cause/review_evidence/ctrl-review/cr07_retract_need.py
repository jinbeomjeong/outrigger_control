"""Retract need of the tracker gate (need_ub) vs head, from the implementation (read only).

Usage: python -I -B cr07_retract_need.py <worktree>
Prints need_ub [mm] for RR and FL at head readings 30..150 bar (+ e_h inside the gate call is
NOT added here: the argument is p_h_ub itself), stroke 0.395 m. Also the commanded retract
travel 41.5-42.3 s of VBH RR (sum |u| T, kappa 0.8) for comparison.
"""

import sys

import numpy as np

sys.path.insert(0, sys.argv[1] + r"\03_src")

from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    LineFillGateBound, LineFillGateParams)

A_H = [1.327e-2, 1.327e-2, 9.503e-3, 9.503e-3]
A_ANN = [3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3]
gate = LineFillGateBound(LineFillGateParams(), A_H, A_ANN, 0.70, 20.924e-3)
for leg, name in ((0, "FL"), (3, "RR")):
    for head_bar in (30, 50, 77, 86, 95, 104, 120, 150):
        need_m, p_open = gate.retract_need_m(leg, head_bar * 1e5, 0.395)
        print(f"{name} p_h_ub {head_bar:4d} bar need_ub {need_m * 1e3:6.3f} mm "
              f"open {p_open / 1e5:6.2f} bar")
u_mm_s = np.array([0.6944, 1.6865, 2.6786, 3.4921, 3.5714, 3.3929, 2.4802, 1.4881, 0.4960])
print("VBH RR 41.5-42.3 s: sum|u|T =", round(float(u_mm_s.sum() * 0.1), 3),
      "mm, x0.8 =", round(float(u_mm_s.sum() * 0.1 * 0.8), 3), "mm (valve lag ignored)")
