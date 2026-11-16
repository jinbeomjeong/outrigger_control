"""P3 (rod_flow_cap_all, M2 law flow_limited_r6): coefficients and checks (read only).

Reference implementation of the two new branches of the revision 6 moving rod pressure law as
the hydraulics review fixes them (hydraulics_remedy_review.md 1), checked against the stored
revision 5 function (repo, imported, not modified):

    (a) retract, p* > p : min(lag, p + A_ann |u| dt / C_r)                          r5
    (b) extend,  p* < p : max(lag, p - b_T A_h |u| sqrt((p - p_T)+ / dp_c) dt / C_r)  r5
    (c) retract, p* < p : max(lag, p - A_ann |u| (sqrt((p_h - p_T)+ / (p_bA - p_T)) - 1)+ dt / C_r)
                          p_h = (F + A_ann p) / A_h                                    new
    (d) extend,  p* > p : min(lag, max(p + A_ann |u| dt / C_r, lag_F))                new
                          lag_F = lag towards p_F = -F / A_ann if p_F > p, else -inf

Path B (hand): closed forms of the fixed-force two-chamber balance (rates, time constants,
stall pressures). Units SI inside, printed bar / ms / mm/s; pressures gauge. Leg 0 = FL (front),
leg 3 = RR (rear). Every valve value is an ASSUMPTION of the plant (rod_release, rod_chamber).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")

from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode  # noqa: E402
from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    METER_OUT_RATIO, SPOOL_REFERENCE_DROP_PA, TANK_PRESSURE_PA, RodPressureFlowLaw,
    flow_limited_rod_pressure)

BAR = 1e5
OUT = Path(__file__).with_suffix(".json")
V_MAX = 0.0209243016
STROKE = 0.70
BETA = 1.0e9
L0H = L0R = 0.05
DT = 5.0e-4          # harness inner step
TAU = 0.05           # plant lag
P_T = TANK_PRESSURE_PA
DP_C = SPOOL_REFERENCE_DROP_PA
B_T = METER_OUT_RATIO
V_HOSE, BETA_HOSE = 285e-6, 0.5e9
LEGS = {
    "front": dict(A_h=0.013273229, A_ann=0.00376991118, e_op=0.4011, m_rod=106.783666),
    "rear": dict(A_h=math.pi / 4 * 0.11**2, A_ann=math.pi / 4 * (0.11**2 - 0.09**2),
                 e_op=0.3909, m_rod=None),
}


def leg_consts(name):
    g = LEGS[name]
    k_h = BETA * g["A_h"] / (L0H + g["e_op"])
    k_r = BETA * g["A_ann"] / (L0R + STROKE - g["e_op"])
    c_r = RodPressureFlowLaw.rod_compliance_m3_Pa(g["A_ann"], k_h, k_r)
    params = RodChamberLegParams(head_area_m2=g["A_h"], annulus_area_m2=g["A_ann"],
                                 head_stiffness_N_m=k_h, rod_stiffness_N_m=k_r,
                                 outer_stiffness_N_m=math.inf, rod_weight_N=0.0)
    return dict(g, k_h=k_h, k_r=k_r, C_r=c_r, phi=g["A_h"] / g["A_ann"], params=params)


def r6(prev, target, speed, dt, lag, c_r, a_h, a_ann, is_retract, force, p_ba,
       p_t=P_T, dp_c=DP_C, b_t=B_T):
    """Reference revision 6 step (branches (a)-(d) of the module docstring)."""
    keep = math.exp(-dt / lag) if lag > 0.0 else 0.0
    lagged = target + (prev - target) * keep
    s = abs(speed)
    if is_retract and target > prev:                         # (a) r5
        return min(lagged, prev + a_ann * s * dt / c_r)
    if not is_retract and target < prev:                     # (b) r5
        drop = max(prev - p_t, 0.0)
        return max(lagged, prev - b_t * a_h * s * math.sqrt(drop / dp_c) * dt / c_r)
    if is_retract and target < prev:                         # (c) new
        if p_ba - p_t < 0.5 * BAR:
            raise ValueError("p_bA - p_T must be >= 0.5 bar")
        head = (force + a_ann * prev) / a_h
        factor = max(math.sqrt(max(head - p_t, 0.0) / (p_ba - p_t)) - 1.0, 0.0)
        return max(lagged, prev - a_ann * s * factor * dt / c_r)
    if not is_retract and target > prev:                     # (d) new
        p_force = -force / a_ann
        lag_force = (p_force + (prev - p_force) * keep) if p_force > prev else -math.inf
        return min(lagged, max(prev + a_ann * s * dt / c_r, lag_force))
    return lagged


def r6_bt(prev, target, speed, dt, lag, c_r, a_h, a_ann, force):
    """Sensitivity of branch (c): A->T land = b_T K_spool (b_T 1, dp_c 10 bar) instead of the
    p_bA calibration (the form quoted in hydraulics_review 7 P3)."""
    keep = math.exp(-dt / lag)
    lagged = target + (prev - target) * keep
    head = (force + a_ann * prev) / a_h
    factor = max(B_T * math.sqrt(max(head - P_T, 0.0) / DP_C) - 1.0, 0.0)
    return max(lagged, prev - a_ann * abs(speed) * factor * dt / c_r)


def target(leg, mode, force):
    return leg["params"].moving_target_rod_pressure_Pa(mode, force)


def run(leg, p0, force, speed, t_end, law, mode):
    p = p0
    tgt = target(leg, mode, force)
    out = []
    for k in range(int(round(t_end / DT))):
        if law == "r5":
            p = flow_limited_rod_pressure(p, tgt, speed, DT, TAU, leg["C_r"], leg["A_h"],
                                          leg["A_ann"], mode is RodChamberMode.RET)
        elif law == "r6":
            p = r6(p, tgt, speed, DT, TAU, leg["C_r"], leg["A_h"], leg["A_ann"],
                   mode is RodChamberMode.RET, force, leg["params"].p_head_back_retract_Pa)
        else:
            p = r6_bt(p, tgt, speed, DT, TAU, leg["C_r"], leg["A_h"], leg["A_ann"], force)
        out.append(p)
    return np.array(out), tgt


def main():
    res = {"constants": {}, "micro": {}, "vmax_vs_r5": {}, "monotone": {}, "steady": {},
           "examples": {}, "bt_sensitivity": {}, "extend_drain_physics": {}, "light_leg": {}}
    for name in LEGS:
        leg = leg_consts(name)
        p_ba = leg["params"].p_head_back_retract_Pa
        res["constants"][name] = {
            "A_h_m2": leg["A_h"], "A_ann_m2": leg["A_ann"], "phi": leg["phi"],
            "k_h_N_m": leg["k_h"], "k_r_N_m": leg["k_r"], "C_r_m3_Pa": leg["C_r"],
            "C_r_plus_hose_m3_Pa": leg["C_r"] + V_HOSE / BETA_HOSE,
            "unit_rate_vmax_bar_s": leg["A_ann"] * V_MAX / leg["C_r"] / BAR,
            "p_bA_bar": p_ba / BAR, "b_T_ret_equiv": math.sqrt(DP_C / (p_ba - P_T)),
            "tau_cap_at_vmax_s": 2 * leg["phi"] * (p_ba - P_T) * leg["C_r"]
            / (leg["A_ann"] * V_MAX),
        }
        # 1) micro command: 1 um/s x 0.1 s, worst head 210 bar (c) and start 2 bar (d)
        worst = {}
        for label, mode, p0, force in (
                ("c_ret_depress_p_h_210", RodChamberMode.RET, 80e5,
                 210e5 * leg["A_h"] - 80e5 * leg["A_ann"]),
                ("d_ext_press_from_2bar", RodChamberMode.EXT, 2e5, 10e3)):
            p, tgt = run(leg, p0, force, 1e-6, 0.1, "r6", mode)
            p5, _ = run(leg, p0, force, 1e-6, 0.1, "r5", mode)
            worst[label] = {"dp_r6_bar": (p[-1] - p0) / BAR, "dp_r5_bar": (p5[-1] - p0) / BAR,
                            "target_bar": tgt / BAR}
        res["micro"][name] = worst
        # 2) v_max: r6 vs r5 over a grid of lock pressures and forces (retract (c), extend (d))
        grid = []
        for f_kN in (-1.0, 0.0, 2.0, 5.0, 10.0, 25.0, 50.0, 80.0):
            for p0_bar in (2.0, 5.0, 13.0, 30.0, 54.0, 80.0):
                for mode in (RodChamberMode.RET, RodChamberMode.EXT):
                    for speed in (V_MAX, 0.225 * V_MAX, 0.05 * V_MAX):
                        p6, tgt = run(leg, p0_bar * BAR, f_kN * 1e3, speed, 0.3, "r6", mode)
                        p5, _ = run(leg, p0_bar * BAR, f_kN * 1e3, speed, 0.3, "r5", mode)
                        diff = np.abs(p6 - p5)
                        grid.append({"F_kN": f_kN, "p0_bar": p0_bar, "mode": mode.name,
                                     "speed_frac": speed / V_MAX, "target_bar": tgt / BAR,
                                     "max_abs_diff_bar": float(diff.max() / BAR),
                                     "diff_at_0p1s_bar": float((p6[199] - p5[199]) / BAR),
                                     "r6_0p3s_bar": float(p6[-1] / BAR),
                                     "r5_0p3s_bar": float(p5[-1] / BAR)})
        res["vmax_vs_r5"][name] = {
            "rows": grid,
            "max_diff_vmax_bar": max(r["max_abs_diff_bar"] for r in grid if r["speed_frac"] == 1.0),
            "max_diff_vmax_ret_loaded_bar": max(
                r["max_abs_diff_bar"] for r in grid
                if r["speed_frac"] == 1.0 and r["mode"] == "RET" and r["F_kN"] >= 10.0),
            "max_diff_vmax_ext_bar": max(r["max_abs_diff_bar"] for r in grid
                                         if r["speed_frac"] == 1.0 and r["mode"] == "EXT"),
        }
        # 3) one-step monotonicity in p (dt 5e-4 and 1e-3), both new branches, v_max
        viol = 0
        worst_slope = math.inf
        for dt in (5e-4, 1e-3):
            for f_kN in (-5.0, 0.0, 5.0, 25.0, 80.0):
                for mode in (RodChamberMode.RET, RodChamberMode.EXT):
                    tgt = target(leg, mode, f_kN * 1e3)
                    ps = np.linspace(-0.9e5, 250e5, 25001)
                    ys = np.array([r6(pp, tgt, V_MAX, dt, TAU, leg["C_r"], leg["A_h"],
                                      leg["A_ann"], mode is RodChamberMode.RET, f_kN * 1e3,
                                      p_ba) for pp in ps])
                    slope = np.diff(ys) / np.diff(ps)
                    viol += int((slope < -1e-12).sum())
                    worst_slope = min(worst_slope, float(slope.min()))
        res["monotone"][name] = {"violations": viol, "min_slope": worst_slope}
        # 4) steady state = p* (no stall) from above, 3 s, 0.05 v_max
        stall = []
        for f_kN in (-1.0, 0.0, 1.0, 3.0, 8.0, 25.0, 80.0):
            p, tgt = run(leg, 80e5, f_kN * 1e3, 0.05 * V_MAX, 3.0, "r6", RodChamberMode.RET)
            pb, _ = run(leg, 80e5, f_kN * 1e3, 0.05 * V_MAX, 3.0, "bt", RodChamberMode.RET)
            stall.append({"F_kN": f_kN, "target_bar": tgt / BAR, "r6_end_bar": p[-1] / BAR,
                          "bt1_end_bar": pb[-1] / BAR})
        res["steady"][name] = stall
        # 5) examples: spec 2.5 claim (1 mm/s retract from 50 bar), R12-like F 22 kN
        ex = {}
        for f_kN in (10.0, 22.0, 50.0):
            p6, tgt = run(leg, 50e5, f_kN * 1e3, 1e-3, 2.0, "r6", RodChamberMode.RET)
            pb, _ = run(leg, 50e5, f_kN * 1e3, 1e-3, 2.0, "bt", RodChamberMode.RET)
            p5, _ = run(leg, 50e5, f_kN * 1e3, 1e-3, 2.0, "r5", RodChamberMode.RET)

            def t_to(arr, level):
                idx = np.flatnonzero(arr <= level)
                return None if idx.size == 0 else float((idx[0] + 1) * DT)
            ex[f"F{f_kN:g}kN"] = {
                "target_bar": tgt / BAR,
                "initial_rate_r6_bar_s": float((50e5 - p6[0]) / DT / BAR),
                "initial_rate_bt1_bar_s": float((50e5 - pb[0]) / DT / BAR),
                "t_to_30bar_r6_s": t_to(p6, 30e5), "t_to_30bar_bt1_s": t_to(pb, 30e5),
                "t_to_30bar_r5_s": t_to(p5, 30e5),
                "p_at_1s_r6_bar": float(p6[1999] / BAR), "p_at_1s_bt1_bar": float(pb[1999] / BAR)}
        res["examples"][name] = ex
        # 6) extension drain: r5 gross (plant) vs fixed-force net physics vs tracker (kappa 0.8,
        #    hose 1.4, beta 0.69, L0 0.08/0.10), start 54 bar, 4.71 mm/s step through tau_v 0.1
        tr_kh = 0.69e9 * leg["A_h"] / (0.08 + 0.3950)
        tr_kr = 0.69e9 * leg["A_ann"] / (0.10 + STROKE - 0.3950)
        c_tr = 1.40 * RodPressureFlowLaw.rod_compliance_m3_Pa(leg["A_ann"], tr_kh, tr_kr)
        rows = []
        for u_ext in (4.71e-3, V_MAX):
            p_pl = p_net = p_nh = p_tr = 54e5
            valve = 0.0749e-3
            worst_tr = math.inf
            worst_net_minus_plant = -math.inf
            for k in range(int(0.4 / DT)):
                valve = u_ext + (valve - u_ext) * math.exp(-DT / 0.1)
                p_pl = flow_limited_rod_pressure(p_pl, 5e5, valve, DT, TAU, leg["C_r"],
                                                 leg["A_h"], leg["A_ann"], False)
                p_tr = flow_limited_rod_pressure(p_tr, 5e5, 0.8 * valve, DT, TAU, c_tr,
                                                 leg["A_h"], leg["A_ann"], False)
                for which in ("net", "nh"):
                    c_phys = leg["C_r"] + (V_HOSE / BETA_HOSE if which == "net" else 0.0)
                    pp = p_net if which == "net" else p_nh
                    lagged = 5e5 + (pp - 5e5) * math.exp(-DT / TAU)
                    q = (B_T * leg["A_h"] * valve * math.sqrt(max(pp - P_T, 0) / DP_C)
                         - leg["A_ann"] * valve)
                    pp = max(lagged, pp - max(q, 0.0) * DT / c_phys)
                    if which == "net":
                        p_net = pp
                    else:
                        p_nh = pp
                worst_tr = min(worst_tr, p_tr - p_net)
                worst_net_minus_plant = max(worst_net_minus_plant, p_nh - p_pl)
            rows.append({"u_ext_mm_s": u_ext * 1e3, "C_tracker": c_tr,
                         "min_tracker_minus_physics_with_hose_bar": worst_tr / BAR,
                         "max_physics_nohose_minus_plant_r5_bar": worst_net_minus_plant / BAR})
        res["extend_drain_physics"][name] = rows
        # 7) light legs: retract target vs the monitor retract moving model 13 + p_h / 3
        light = []
        for f_kN in (-2.0, -1.0, 0.0, 0.5, 1.0, 2.0, 4.0):
            tgt = target(leg, RodChamberMode.RET, f_kN * 1e3)
            head = (f_kN * 1e3 + tgt * leg["A_ann"]) / leg["A_h"]
            model = 15e5 + (head - 15e5) / 3.0 + 3e5
            light.append({"F_kN": f_kN, "p_star_ret_bar": tgt / BAR, "p_h_bar": head / BAR,
                          "monitor_model_bar": model / BAR, "excess_bar": (tgt - model) / BAR})
        res["light_leg"][name] = light
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    brief = {n: {"constants": res["constants"][n], "micro": res["micro"][n],
                 "vmax": {k: v for k, v in res["vmax_vs_r5"][n].items() if k != "rows"},
                 "monotone": res["monotone"][n], "steady": res["steady"][n],
                 "examples": res["examples"][n], "drain": res["extend_drain_physics"][n],
                 "light": res["light_leg"][n]} for n in LEGS}
    print(json.dumps(brief, indent=1))


if __name__ == "__main__":
    main()
