"""Q3: the retract need of spec 2.4 (0.92 -> 1.24 mm) against the implemented need_ub (read only).

Chain from the plant nominal input set (hydraulics_remedy_review 3.3 'point_loaded': beta 1 GPa,
L0r = L0h = 0.05 m, p_r = p_T, stroke 0.395 m) to the gate input set of decision 147
(p_h + e_h, p_r = floor, F_band 0, beta 0.69 GPa, L0r 0.10 m, L0h 0.08 m), one input at a time,
with the worktree ``retract_dead`` and ``LineFillGateBound.retract_need_m``.
Times: fill from a valve at rest to a 4.71 mm/s retract step (first-order valve lag tau_v 0.1 s,
vent closed above c_v v_max so no VN drain), plant kappa 1, gate kappa_x 0.8.
Units SI inside; printed bar (gauge), mm, ms. Valve values are ASSUMPTIONS.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, r"C:\workspace\z4369-jp3\03_src")
from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    LineFillGateBound, LineFillGateParams)
from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402

BAR = 1e5
P_T = 2e5
P_FLOOR = 0.1e5 - 1.01325e5
S_MAX = 0.70
V_MAX = 0.0209243016
TAU_V = 0.1
A_H = {"front": 0.013273229, "rear": math.pi / 4 * 0.11**2}
A_ANN = {"front": 0.00376991118, "rear": math.pi / 4 * (0.11**2 - 0.09**2)}
CFG = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6, beta_hose_Pa=0.5e9,
                    psi=3.5, p_crack_Pa=3e5)
OUT = Path(__file__).with_suffix(".json")


def need(leg, p_h, p_r, band, s, beta, l0r, l0h):
    return retract_dead(CFG, p_h, p_r, band, s, 0.0, A_H[leg], A_ANN[leg], S_MAX, l0r, l0h,
                        beta, P_T)["need"]


def fill_time(need_m, speed, kappa):
    """t with kappa*U*(t - tau(1-exp(-t/tau))) = need (no drain: |u_v| > c_v v_max)."""
    f = lambda t: kappa * speed * (t - TAU_V * (1 - math.exp(-t / TAU_V))) - need_m  # noqa: E731
    return brentq(f, 1e-9, 50.0)


def main():
    res = {}
    gate = LineFillGateBound(LineFillGateParams(), [A_H["front"]] * 2 + [A_H["rear"]] * 2,
                             [A_ANN["front"]] * 2 + [A_ANN["rear"]] * 2, S_MAX, V_MAX)
    for leg, idx in (("front", 0), ("rear", 2)):
        p_h = 77e5
        for s in (0.0, 0.35, 0.395):
            chain = []
            steps = [("plant nominal, F_band 8 kN (spec 'before')", p_h, P_T, 8e3, 1.0e9, .05, .05),
                     ("F_band 0 (spec 'after' 1.24)", p_h, P_T, 0.0, 1.0e9, .05, .05),
                     ("+ p_r floor", p_h, P_FLOOR, 0.0, 1.0e9, .05, .05),
                     ("+ beta 0.69 GPa", p_h, P_FLOOR, 0.0, 0.69e9, .05, .05),
                     ("+ L0r 0.10 m", p_h, P_FLOOR, 0.0, 0.69e9, .10, .05),
                     ("+ L0h 0.08 m (= need_ub at p_h_ub 77)", p_h, P_FLOOR, 0.0, 0.69e9, .10, .08),
                     ("+ e_h 9 bar (= need_ub at reading 77)", p_h + 9e5, P_FLOOR, 0.0, 0.69e9,
                      .10, .08)]
            for name, ph, pr, bd, be, l0r, l0h in steps:
                n = need(leg, ph, pr, bd, s, be, l0r, l0h)
                chain.append({"step": name, "need_mm": round(n * 1e3, 4)})
            impl77 = gate.retract_need_m(idx, 77e5, s)[0]
            impl86 = gate.retract_need_m(idx, 86e5, s)[0]
            res[f"{leg}:s{s:g}"] = {"chain": chain,
                                    "impl_need_ub_mm_p_h_ub77": round(impl77 * 1e3, 4),
                                    "impl_need_ub_mm_p_h_ub86": round(impl86 * 1e3, 4)}
        # timing at 4.71 mm/s, s = 0.395: plant (kappa 1, its own need) vs gate (kappa 0.8)
        s = 0.395
        U = 4.71e-3
        t_rows = {}
        for band_pl in (0.0, 4e3, 8e3):
            n_pl = need(leg, p_h, P_T, band_pl, s, 1.0e9, .05, .05)
            t_rows[f"plant_band{band_pl / 1e3:g}kN"] = {
                "need_mm": round(n_pl * 1e3, 4), "t_ms": round(fill_time(n_pl, U, 1.0) * 1e3, 1)}
        for name, n in (("spec_v1_gate(band8,p_T,beta.69,L0 .10/.08,e_h5)",
                         need(leg, p_h + 5e5, P_T, 8e3, s, 0.69e9, .10, .08)),
                        ("spec_text_1.24_as_gate", need(leg, p_h, P_T, 0.0, s, 1.0e9, .05, .05)),
                        ("impl_gate(e_h9)", gate.retract_need_m(idx, p_h + 9e5, s)[0])):
            t_rows[name] = {"need_mm": round(n * 1e3, 4),
                            "t_ms_kappa0.8": round(fill_time(n, U, 0.8) * 1e3, 1)}
        res[f"{leg}:timing_4.71mm_s"] = t_rows
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
