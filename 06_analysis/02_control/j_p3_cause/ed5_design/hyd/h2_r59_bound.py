"""H-2: R5-9 retract relief bound against the P3 plant law r6 (c)/(a), single leg (read only).

Plant (harness P3): from the witness instant the leg is released and retracts at the valve speed
U (steady), M2 law ``flow_limited_rod_pressure_r6`` with the plant C_r (frozen e_op), tau 0.05 s,
dt 5e-4 s, target p*_ret(F(t)) of ``RodChamberLegParams``; F(t) = F0 + ripple.
Tracker R5-9 (1 ms sub-steps, from the same instant, p_hat(0) = p_tr(0), the least value A1 allows):
    p_hat <- max(p_hat - A_ann kappa_x U f_lb dt / (h C_r(s)),
                 p*_ub + (p_hat - p*_ub) exp(-dt / tau),
                 13 bar + p_h_ub / 3)
    f_lb  = (sqrt((p_h_lb - p_T)+ / (p_bA - p_T)) - 1)+,  p_h_lb = min(read_k-1, read_k) - e_h
    p_h_ub = max(read_k-1, read_k) + e_h,  F_ub = p_h_ub A_h - p_floor A_ann,  p*_ub = p*(F_ub)
    read = plant head (F + A_ann p_tr) / A_h + err (err fixed per case), e_h 9 bar
Checks: min over time of p_hat - p_tr (must be >= 0), first-period relief bound, time to floor,
remaining over p_hat - p_tr after 1 / 2 / 5 s, against A2 (p_hat held at p0).
"""
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode  # noqa: E402
from outrigger_sim.hydraulics.rod_release import flow_limited_rod_pressure_r6  # noqa: E402

OUT = Path(__file__).with_suffix(".json")
BAR = 1e5
P_T, P_BA, P_FLOOR = 2e5, 5e5, 0.1e5 - 1.01325e5
E_H, B_READ = 9e5, 4.62e5
KAPPA, HOSE, BETA_B, L0H_B, L0R_B, S_MAX = 0.8, 1.40, 0.69e9, 0.08, 0.10, 0.70
TAU = 0.05
LEGS = {
    "front": dict(A_h=1.3273e-2, A_ann=3.7699e-3, kh=2.9424e7, kr=1.0805e7, C_r=1.7983e-12),
    "rear": dict(A_h=9.5033e-3, A_ann=3.1416e-3, kh=2.1554e7, kr=8.7485e6, C_r=1.5860e-12),
}


def tracker_C(leg, s):
    A_h, A_ann = leg["A_h"], leg["A_ann"]
    kh = BETA_B * A_h / (L0H_B + s)
    kr = BETA_B * A_ann / (L0R_B + S_MAX - s)
    return HOSE * A_ann**2 * (1 / kh + 1 / kr)


def f_of(p_h):
    return max(math.sqrt(max(p_h - P_T, 0.0) / (P_BA - P_T)) - 1.0, 0.0)


def run_case(name, F0_N, p0_Pa, U, err_Pa, ripple_N=0.0, ripple_hz=5.0, s=0.40, t_end=6.0):
    leg = LEGS[name]
    params = RodChamberLegParams(head_area_m2=leg["A_h"], annulus_area_m2=leg["A_ann"],
                                 head_stiffness_N_m=leg["kh"], rod_stiffness_N_m=leg["kr"],
                                 outer_stiffness_N_m=1e12, rod_weight_N=0.0)
    A_h, A_ann = leg["A_h"], leg["A_ann"]
    Cbar = tracker_C(leg, s)

    def F_at(t):
        return F0_N + ripple_N * math.sin(2 * math.pi * ripple_hz * t)

    def target(F):
        return params.moving_target_rod_pressure_Pa(RodChamberMode.RET, F)

    if p0_Pa <= target(F0_N) + 1e3:
        return None
    dt_p, dt_t, T = 5e-4, 1e-3, 0.1
    p = p0_Pa
    p_hat = p0_Pa
    t = 0.0
    read_prev = (F_at(0) + A_ann * p) / A_h + err_Pa
    min_margin = math.inf
    out = {"first_period_drop_bar": None}
    hist = {}
    t_floor = None
    n_periods = int(round(t_end / T))
    p_hat_start_period = p_hat
    for k in range(n_periods):
        # plant over the period (needs the end reading for the tracker; the tracker advances after)
        p_start = p
        traj = []
        for j in range(int(round(T / dt_p))):
            F = F_at(t + j * dt_p)
            p = flow_limited_rod_pressure_r6(p, target(F), U, dt_p, TAU, leg["C_r"], A_h, A_ann,
                                             True, F, P_BA)
            traj.append(p)
        t_next = t + T
        read_now = (F_at(t_next) + A_ann * p) / A_h + err_Pa
        ph_lb = min(read_prev, read_now) - E_H
        ph_ub = max(read_prev, read_now) + E_H
        F_ub = ph_ub * A_h - P_FLOOR * A_ann
        pstar_ub = target(F_ub)
        floor = 13e5 + ph_ub / 3.0
        f_lb = f_of(ph_lb)
        p_hat_start_period = p_hat
        traj_hat = []
        for j in range(int(round(T / dt_t))):
            p_hat = max(p_hat - A_ann * KAPPA * U * f_lb * dt_t / Cbar,
                        pstar_ub + (p_hat - pstar_ub) * math.exp(-dt_t / TAU), floor)
            traj_hat.append(p_hat)
        # margin at the common instants (every ms boundary; the monitor uses p_hat at reads only)
        ratio = int(round(dt_t / dt_p))
        for jt, ph in enumerate(traj_hat):
            pv = traj[(jt + 1) * ratio - 1]
            min_margin = min(min_margin, ph - pv)
        if k == 0:
            out["first_period_drop_bar"] = (p_hat_start_period - p_hat) / BAR
            out["first_period_plant_drop_bar"] = (p_start - p) / BAR
            out["f_lb_first"] = f_lb
        if t_floor is None and p_hat <= floor + 1.0:
            t_floor = t_next
        for tt in (1.0, 2.0, 5.0):
            if abs(t_next - tt) < 1e-9:
                hist[tt] = {"over_bar": (p_hat - p) / BAR, "over_A2_bar": (p0_Pa - p) / BAR,
                            "p_hat_bar": p_hat / BAR, "p_tr_bar": p / BAR}
        read_prev = read_now
        t = t_next
    out.update(min_margin_bar=min_margin / BAR, t_floor_s=t_floor, at=hist,
               pstar0_bar=target(F0_N) / BAR, Cbar_over_Cr=Cbar / leg["C_r"])
    return out


def main():
    rows = []
    worst = None
    for name, F_kN, p0_bar, U_mm, err_bar, rip in itertools.product(
            LEGS, (5, 15, 30, 50, 100, 150), (30, 60, 100), (0.3, 0.5, 1.0, 2.0, 4.71, 20.92),
            (-4.62, 0.0, 4.62), (0.0, 3.4e3)):
        r = run_case(name, F_kN * 1e3, p0_bar * BAR, U_mm * 1e-3, err_bar * BAR, ripple_N=rip)
        if r is None:
            continue
        r.update(leg=name, F_kN=F_kN, p0_bar=p0_bar, U_mm_s=U_mm, err_bar=err_bar, ripple_N=rip)
        rows.append(r)
        if worst is None or r["min_margin_bar"] < worst["min_margin_bar"]:
            worst = r
    summary = {"cases": len(rows), "min_margin_bar": worst["min_margin_bar"], "worst_case": worst}
    # table: err 0, no ripple, U 1 and 4.71 mm/s
    table = [
        {k: r[k] for k in ("leg", "F_kN", "p0_bar", "U_mm_s", "first_period_drop_bar",
                           "first_period_plant_drop_bar", "f_lb_first", "t_floor_s", "pstar0_bar")}
        | {"over_1s_bar": r["at"].get(1.0, {}).get("over_bar"),
           "over_2s_bar": r["at"].get(2.0, {}).get("over_bar"),
           "over_A2_1s_bar": r["at"].get(1.0, {}).get("over_A2_bar"),
           "over_A2_2s_bar": r["at"].get(2.0, {}).get("over_A2_bar")}
        for r in rows if r["err_bar"] == 0.0 and r["ripple_N"] == 0.0 and r["p0_bar"] == 60
        and r["U_mm_s"] in (0.5, 1.0, 4.71)]
    summary["table_p0_60"] = table
    neg = [r for r in rows if r["min_margin_bar"] < 0]
    summary["negative_margin_cases"] = len(neg)
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8",
                   newline="\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
