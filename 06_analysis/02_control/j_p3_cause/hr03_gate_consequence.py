"""Consequence of an early R5-4 gate opening (read only; uses hr02_gate_check functions).

Extension: for every grid case where the bound counts relief before the plant releases
(e_h 5 bar), the gap p_hat + delta_m - p_tr at the next three reads is compared with the same case
opened at the plant release ("ideal"). The cost is the change of the minimum gap; a case is a
J-P3a risk only if the early gap is < 0 while the ideal one is >= 0.
Retract: break-down of the early cases of hr02 by speed, reading error, hump and rod pressure.
"""
import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hr02_gate_check as g  # noqa: E402

from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    RodPressureFlowLaw, flow_limited_rod_pressure)

BAR = 1e5
OUT = Path(__file__).with_suffix(".json")
BIG = np.iinfo(np.int64).max


def gaps(leg, u_prev, u_ext, h, r, p_hat0, k_plant, k_bound):
    a_h, a_ann = g.A_H[leg], g.A_ANN[leg]
    k_h = g.BETA * a_h / (g.L0 + g.E_OP[leg])
    k_r = g.BETA * a_ann / (g.L0 + g.S_MAX - g.E_OP[leg])
    c_pl = RodPressureFlowLaw.rod_compliance_m3_Pa(a_ann, k_h, k_r)
    tk_h = 0.69e9 * a_h / (0.08 + 0.395)
    tk_r = 0.69e9 * a_ann / (0.10 + g.S_MAX - 0.395)
    c_tr = 1.40 * RodPressureFlowLaw.rod_compliance_m3_Pa(a_ann, tk_h, tk_r)
    force = h * a_h - r * a_ann
    p_star = max(5e5, -force / a_ann)
    means = g.valve_means(u_prev, u_ext)
    p_tr, p_hat = r, p_hat0
    out = []
    for k in range(300):
        if k >= k_plant:
            for _ in range(2):
                p_tr = flow_limited_rod_pressure(p_tr, p_star, means[k], 5e-4, 0.05, c_pl,
                                                 a_h, a_ann, False)
        if k > k_bound:
            p_hat = flow_limited_rod_pressure(p_hat, 5e5, g.KAPPA * max(means[k], 0.0), g.DT,
                                              0.05, c_tr, a_h, a_ann, False)
        if (k + 1) % 100 == 0:
            out.append((p_hat + 0.5e5 - p_tr) / BAR)
    return out


def main():
    res = {}
    p_h0s = np.array([5, 10, 20, 35, 50, 77, 100, 150, 200]) * BAR
    p_r0s = np.array([g.P_FLOOR / BAR, 0, 2, 5, 13, 30, 54, 80]) * BAR
    amps = np.array([0.0, 1.0, 3.0]) * BAR
    early = Counter()
    worst_cost = 0.0
    risk = []
    worst_rows = []
    for e_h in (5e5, 8.5e5):
        early = Counter()
        n_early = 0
        worst_cost = 0.0
        risk = []
        for leg, u_prev, u_ext in itertools.product(("front", "rear"),
                                                    (0.0, 0.5 * g.U_HOLD, -0.5 * g.U_HOLD),
                                                    g.U_EXT):
            p_a = g.ext_line(leg, u_prev, u_ext)
            p_a_hat = g.ext_line(leg, u_prev, u_ext, kappa=g.KAPPA, reset=True)
            ph, pr, am = (a.ravel() for a in np.meshgrid(p_h0s, p_r0s, amps, indexing="ij"))
            k_plant, _ = g.plant_ext_open(leg, p_a, ph, pr, am)
            for ci, es, dh in itertools.product(range(ph.size), (-g.E_READ, 0.0, g.E_READ),
                                                (0.0, 10e5)):
                h, r, a = ph[ci], pr[ci], am[ci]
                p_hat = max(r + dh, g.P_FLOOR)
                thr = max(h + es + e_h + g.P_CR, g.P_T + (p_hat + g.P_CR - g.P_T) / g.PSI)
                k_b = int(g.bound_ext_open(p_a_hat, np.array([thr]))[0])
                k_p = int(k_plant[ci])
                if k_p == BIG or k_b + 1 >= k_p:
                    continue
                n_early += 1
                early[(round(r / BAR, 2), round(a / BAR, 1), round(es / BAR, 2))] += 1
                ge = gaps(leg, u_prev, u_ext, h, r, p_hat, k_p, k_b)
                gi = gaps(leg, u_prev, u_ext, h, r, p_hat, k_p, k_p - 1)
                cost = min(ge) - min(gi)
                worst_cost = min(worst_cost, cost)
                if min(ge) < 0.0 <= min(gi):
                    risk.append({"leg": leg, "u_ext_mm_s": u_ext * 1e3, "p_h": h / BAR,
                                 "p_r": r / BAR, "amp": a / BAR, "err": es / BAR})
                if e_h == 5e5 and len(worst_rows) < 2000:
                    worst_rows.append({"leg": leg, "u_prev_mm_s": u_prev * 1e3,
                                       "u_ext_mm_s": u_ext * 1e3, "p_h": h / BAR,
                                       "p_r": r / BAR, "amp": a / BAR, "err": es / BAR,
                                       "dhat": dh / BAR, "lead_ms": (k_b + 1 - k_p),
                                       "gap_early": ge, "gap_ideal": gi, "cost": cost})
        res[f"ext_e_h_{e_h / BAR:g}"] = {
            "early_cases": n_early,
            "by_p_r_amp_err": {f"p_r {k[0]} amp {k[1]} err {k[2]}": v
                               for k, v in sorted(early.items())},
            "worst_min_gap_change_bar": worst_cost, "new_negative_gap_cases": len(risk),
            "risk_cases": risk[:20]}
    worst_rows.sort(key=lambda r: r["cost"])
    res["ext_worst_cost_rows_e_h5"] = worst_rows[:10]
    # ---- retract early break-down (same grid as hr02)
    rows = Counter()
    for leg in ("front", "rear"):
        a_h, a_ann = g.A_H[leg], g.A_ANN[leg]
        ph, pr, bd, am = (a.ravel() for a in np.meshgrid(
            np.array([5, 20, 50, 77, 100, 150, 200]) * BAR,
            np.array([2, 5, 13, 30, 54]) * BAR, np.array([0, 4, 8, 16]) * 1e3,
            np.array([0.0, 3.0]) * BAR, indexing="ij"))
        t = (np.arange(g.N) + 1) * g.DT
        bump = np.sin(np.pi * ((t % g.T_PER) / g.T_PER))
        for u_prev, u_ret, es in itertools.product((0.0, -0.5 * g.U_HOLD),
                                                   (1.01 * g.U_HOLD, 0.5e-3, 1e-3, 4.71e-3,
                                                    g.V_MAX), (-g.E_READ, 0.0)):
            means = g.valve_means(u_prev, -u_ret)

            def plant_need(k, ph=ph, pr=pr, bd=bd, am=am, a_h=a_h, a_ann=a_ann, leg=leg):
                h = ph + am * bump[k]
                r = np.maximum(pr - g.ratio(leg) * am * bump[k], g.P_FLOOR)
                return g.need_vec(h, r, bd, 0.395, 0.0, a_h, a_ann, g.BETA, g.L0, g.L0)
            x0 = np.zeros_like(ph)
            if u_prev < -g.EPS:
                k_n = g.F_N * g.k_land(leg)
                for _ in range(1000):
                    need, rise = plant_need(0)
                    gg = max(1 - abs(u_prev) / (g.C_V * g.V_MAX), 0.0)
                    level = np.minimum(x0 / np.where(need > 0, need, 1.0), 1.0)
                    x0 = np.maximum(x0 + (abs(u_prev) - k_n * gg * np.sqrt(rise * level)
                                          / a_ann) * g.DT, 0.0)
            k_pl = g.ret_open(leg, plant_need, means, 1.0, x0)
            for name, band_ub, e_h in (("spec_Fband8_eh5", 8e3, 5e5), ("Fband0_eh5", 0.0, 5e5),
                                       ("Fband0_eh8.5", 0.0, 8.5e5)):
                need_ub, rise_ub = g.need_vec(ph + es + e_h, np.full_like(pr, g.P_T),
                                              np.full_like(bd, band_ub), 0.395, 0.0, a_h,
                                              a_ann, 0.69e9, 0.10, 0.08)
                k_b = g.ret_open(leg, lambda k, n=need_ub, ru=rise_ub: (n, ru), means, g.KAPPA,
                                 np.zeros_like(ph))
                bad = np.where(k_pl == BIG, k_b < BIG, (k_b < BIG) & (k_b + 1 < k_pl))
                for i in np.flatnonzero(bad):
                    rows[(name, leg, round(u_prev * 1e3, 3), round(u_ret * 1e3, 3),
                          round(es / BAR, 2), round(am[i] / BAR), round(pr[i] / BAR),
                          "plant_never" if k_pl[i] == BIG else "plant_later")] += 1
    agg = {}
    for (name, leg, up, ur, es, amp, prr, kind), v in rows.items():
        key = f"{name} | u_prev {up} | u_ret {ur} | err {es} | amp {amp} | {kind}"
        agg[key] = agg.get(key, 0) + v
    res["ret_early_breakdown"] = dict(sorted(agg.items()))
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "ext_worst_cost_rows_e_h5"},
                     indent=1, default=float))
    print(json.dumps(res["ext_worst_cost_rows_e_h5"][:5], indent=1, default=float))


if __name__ == "__main__":
    main()
