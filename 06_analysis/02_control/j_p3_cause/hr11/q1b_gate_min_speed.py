"""Smallest steady retract speed at which the R5-4 tracker gate can open (VN drain balance at
level 1: kappa_x U > K_n g(U) sqrt(p_open - p_T) / A_ann, g = (1 - U / (c_v v_max))+), and the
same for the P1 plant (kappa 1, plant need inputs, p_r trapped or 2 bar). Read only."""
import math
import sys

import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, r"C:\workspace\z4369-jp3\03_src")
from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    LineFillGateBound, LineFillGateParams)
from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402

V_MAX = 0.0209243016
A_H = [0.013273229] * 2 + [math.pi / 4 * 0.11**2] * 2
A_ANN = [0.00376991118] * 2 + [math.pi / 4 * (0.11**2 - 0.09**2)] * 2
GATE = LineFillGateBound(LineFillGateParams(), A_H, A_ANN, 0.70, V_MAX)
CFG = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6, beta_hose_Pa=0.5e9,
                    psi=3.5, p_crack_Pa=3e5)
K_N = [0.05 * a * V_MAX / math.sqrt(10e5) for a in A_H]


def u_min(leg, rise, kappa):
    f = lambda u: kappa * u - K_N[leg] * max(1 - u / (0.02 * V_MAX), 0.0) * math.sqrt(rise) / A_ANN[leg]  # noqa: E731
    return brentq(f, 1e-9, 0.02 * V_MAX)


for leg, name in ((0, "front"), (2, "rear")):
    for p_h in (20e5, 35e5, 60e5, 120e5):
        _, p_open = GATE.retract_need_m(leg, p_h + 9e5, 0.395)
        ug = u_min(leg, max(p_open - 2e5, 0.0), 0.8)
        out = []
        for p_r in (2e5, 60e5):
            r = retract_dead(CFG, p_h, p_r, 0.0, 0.395, 0.0, A_H[leg], A_ANN[leg], 0.70, 0.05, 0.05,
                             1e9, 2e5)
            out.append(round(u_min(leg, max(r["p_open"] - 2e5, 0.0), 1.0) * 1e3, 4))
        print(name, f"p_h {p_h / 1e5:g} bar: gate opens only above U = {ug * 1e3:.4f} mm/s "
              f"({ug / (0.01 * V_MAX):.2f} u_hold); plant (p_r 2 / 60 bar) above {out} mm/s")
