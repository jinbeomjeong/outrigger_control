"""R5-9 lag term at light / tension loads: p*_ret(F) is not monotone in F (head clipped at p_bA
below F_c = A_ann (p_bA (phi - 1) - p_cr)), so p*_ub = p*(F_ub) alone may fall below the plant
target. Compare p*_ub = p*(F_ub) (form A, H-2 draft) with max(p*(F_lb), p*(F_ub)) (form B),
F_lb = p_h_lb A_h - p_hat A_ann, against the r6 plant; single leg, fixed F, steady U."""
import itertools
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode  # noqa: E402
from outrigger_sim.hydraulics.rod_release import flow_limited_rod_pressure_r6  # noqa: E402

BAR = 1e5
P_T, P_BA, P_FLOOR, P_CR = 2e5, 5e5, 0.1e5 - 1.01325e5, 3e5
E_H, KAPPA, HOSE, BETA_B, L0H_B, L0R_B, S_MAX, TAU = 9e5, 0.8, 1.40, 0.69e9, 0.08, 0.10, 0.70, 0.05
LEGS = {"front": dict(A_h=1.3273e-2, A_ann=3.7699e-3, kh=2.9424e7, kr=1.0805e7, C_r=1.7983e-12),
        "rear": dict(A_h=9.5033e-3, A_ann=3.1416e-3, kh=2.1554e7, kr=8.7485e6, C_r=1.5860e-12)}


def run(name, F, p0, U, err, form, s=0.40, t_end=3.0):
    leg = LEGS[name]
    A_h, A_ann = leg["A_h"], leg["A_ann"]
    par = RodChamberLegParams(head_area_m2=A_h, annulus_area_m2=A_ann, head_stiffness_N_m=leg["kh"],
                              rod_stiffness_N_m=leg["kr"], outer_stiffness_N_m=1e12, rod_weight_N=0.0)
    tgt = lambda f: par.moving_target_rod_pressure_Pa(RodChamberMode.RET, f)  # noqa: E731
    kh = BETA_B * A_h / (L0H_B + s)
    kr = BETA_B * A_ann / (L0R_B + S_MAX - s)
    Cbar = HOSE * A_ann**2 * (1 / kh + 1 / kr)
    p = p_hat = p0
    read_prev = (F + A_ann * p) / A_h + err
    worst = math.inf
    for _ in range(int(round(t_end / 0.1))):
        traj = []
        for _ in range(200):
            p = flow_limited_rod_pressure_r6(p, tgt(F), U, 5e-4, TAU, leg["C_r"], A_h, A_ann, True, F, P_BA)
            traj.append(p)
        read = (F + A_ann * p) / A_h + err
        lo, hi = min(read_prev, read) - E_H, max(read_prev, read) + E_H
        f_lb = max(math.sqrt(max(lo - P_T, 0) / (P_BA - P_T)) - 1, 0)
        ps_hi = tgt(hi * A_h - P_FLOOR * A_ann)
        ps_ub = ps_hi if form == "A" else max(ps_hi, tgt(lo * A_h - p_hat * A_ann))
        floor = 13e5 + hi / 3
        for j in range(100):
            p_hat = max(p_hat - A_ann * KAPPA * U * f_lb * 1e-3 / Cbar,
                        ps_ub + (p_hat - ps_ub) * math.exp(-1e-3 / TAU), floor)
            worst = min(worst, p_hat - traj[2 * j + 1])
        read_prev = read
    return worst / BAR


rows = []
for name, F_kN, p0_bar, U_mm, err_bar in itertools.product(
        LEGS, (-30, -10, -5, -1, 0, 2, 3.5, 5), (60, 120, 180), (0.5, 4.71, 20.92), (-4.62, 0, 4.62)):
    F, p0 = F_kN * 1e3, p0_bar * BAR
    leg = LEGS[name]
    par = RodChamberLegParams(head_area_m2=leg["A_h"], annulus_area_m2=leg["A_ann"],
                              head_stiffness_N_m=leg["kh"], rod_stiffness_N_m=leg["kr"],
                              outer_stiffness_N_m=1e12, rod_weight_N=0.0)
    if p0 <= par.moving_target_rod_pressure_Pa(RodChamberMode.RET, F) + 1e3:
        continue
    rows.append({"leg": name, "F_kN": F_kN, "p0_bar": p0_bar, "U_mm_s": U_mm, "err_bar": err_bar,
                 "min_margin_A_bar": run(name, F, p0, U_mm * 1e-3, err_bar * BAR, "A"),
                 "min_margin_B_bar": run(name, F, p0, U_mm * 1e-3, err_bar * BAR, "B")})
summary = {"cases": len(rows),
           "A_negative": sum(r["min_margin_A_bar"] < 0 for r in rows),
           "A_min_bar": min(r["min_margin_A_bar"] for r in rows),
           "A_worst": min(rows, key=lambda r: r["min_margin_A_bar"]),
           "B_negative": sum(r["min_margin_B_bar"] < 0 for r in rows),
           "B_min_bar": min(r["min_margin_B_bar"] for r in rows)}
out = Path(__file__).with_suffix(".json")
out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(summary, indent=1))
