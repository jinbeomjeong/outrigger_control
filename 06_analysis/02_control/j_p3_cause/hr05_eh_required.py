"""Required e_h for strict bound-after-plant ordering at a 3.6 bar intra-period head rise
(3.4 kN heave ringing on the rear head, two_pressure.load_reference_mean_s note), normal-grade
worst reading error, extension and retract (read only; uses hr02_gate_check functions).
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hr02_gate_check as g  # noqa: E402

BAR = 1e5
BIG = np.iinfo(np.int64).max
OUT = Path(__file__).with_suffix(".json")


def main():
    res = {}
    e_hs = np.arange(0.0, 14.01, 0.5) * BAR
    p_h0s = np.array([5, 10, 20, 35, 50, 77, 100, 150, 200]) * BAR
    p_r0s = np.array([g.P_FLOOR / BAR, 0, 1, 2, 5, 13, 30, 54, 80]) * BAR
    for amp_bar in (3.6, 5.0):
        need_max = 0.0
        for leg, u_prev, u_ext in itertools.product(("front", "rear"),
                                                    (0.0, 0.5 * g.U_HOLD, -0.5 * g.U_HOLD),
                                                    g.U_EXT):
            p_a = g.ext_line(leg, u_prev, u_ext)
            p_a_hat = g.ext_line(leg, u_prev, u_ext, kappa=g.KAPPA, reset=True)
            ph, pr = (a.ravel() for a in np.meshgrid(p_h0s, p_r0s, indexing="ij"))
            k_p, _ = g.plant_ext_open(leg, p_a, ph, pr, np.full_like(ph, amp_bar * BAR))
            for i in range(ph.size):
                for e_h in e_hs:
                    thr = max(ph[i] - g.E_READ + e_h + g.P_CR,
                              g.P_T + (max(pr[i], g.P_FLOOR) + g.P_CR - g.P_T) / g.PSI)
                    k_b = int(g.bound_ext_open(p_a_hat, np.array([thr]))[0])
                    ok = (k_p[i] == BIG and k_b == BIG) or (k_p[i] != BIG and
                                                            (k_b == BIG or k_b + 1 >= k_p[i]))
                    if ok:
                        need_max = max(need_max, e_h / BAR)
                        break
                else:
                    need_max = float("inf")
        res[f"ext_required_e_h_bar_amp{amp_bar:g}"] = need_max
        # retract early count at e_h 9 bar, F_band 0, p_r_lb = p_floor
        early = 0
        cases = 0
        for leg in ("front", "rear"):
            a_h, a_ann = g.A_H[leg], g.A_ANN[leg]
            ph, pr, bd = (a.ravel() for a in np.meshgrid(
                np.array([5, 20, 50, 77, 100, 150, 200]) * BAR,
                np.array([2, 5, 13, 30, 54]) * BAR, np.array([0, 4, 8, 16]) * 1e3,
                indexing="ij"))
            t = (np.arange(g.N) + 1) * g.DT
            bump = np.sin(np.pi * ((t % g.T_PER) / g.T_PER))
            for u_ret in (1.01 * g.U_HOLD, 0.5e-3, 1e-3, 4.71e-3, g.V_MAX):
                means = g.valve_means(0.0, -u_ret)

                def plant_need(k, ph=ph, pr=pr, bd=bd, a_h=a_h, a_ann=a_ann, leg=leg):
                    h = ph + amp_bar * BAR * bump[k]
                    r = np.maximum(pr - g.ratio(leg) * amp_bar * BAR * bump[k], g.P_FLOOR)
                    return g.need_vec(h, r, bd, 0.395, 0.0, a_h, a_ann, g.BETA, g.L0, g.L0)
                k_pl = g.ret_open(leg, plant_need, means, 1.0, np.zeros_like(ph))
                need_ub, rise_ub = g.need_vec(ph - g.E_READ + 9e5, np.full_like(pr, g.P_FLOOR),
                                              np.zeros_like(bd), 0.395, 0.0, a_h, a_ann,
                                              0.69e9, 0.10, 0.08)
                k_b = g.ret_open(leg, lambda k, n=need_ub, ru=rise_ub: (n, ru), means, g.KAPPA,
                                 np.zeros_like(ph))
                bad = np.where(k_pl == BIG, k_b < BIG, (k_b < BIG) & (k_b + 1 < k_pl))
                early += int(bad.sum())
                cases += int(bad.size)
        res[f"ret_early_e_h9_Fband0_floor_amp{amp_bar:g}"] = {"early": early, "cases": cases}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
