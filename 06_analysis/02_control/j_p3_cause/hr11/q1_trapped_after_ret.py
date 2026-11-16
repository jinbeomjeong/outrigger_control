"""Q1 (counterexample 11b): trapped rod pressure left by P3 (c) when a short retraction whose
tracker gate opened is followed by HOLD / relock (read only).

Single leg, fixed net force F, locked with a trapped rod pressure p_r0 above the plant retract
target p*_ret(F). Acting command -U for N periods of 0.1 s (read-aligned, d = 1 already applied),
then 0 (HOLD). Valve: first-order lag tau_v 0.1 s, 1 ms chunk means (the M1c / gate input).

Plant (P1 + P3, as the harness):
  * M1c retract line fill x (kappa 1, VN drain below c_v v_max), need = retract_dead at the plant
    inputs (beta 1 GPa, L0 0.05 m, true p_h, p_r0, seal band, void 0); release at x >= need;
  * seed max(p_rod, p_r0) (= p_r0 for a trapped lock), then flow_limited_rod_pressure_r6 (worktree)
    with p*_ret(F) of RodChamberLegParams, 5e-4 s inner steps, speed = valve speed.
Tracker gate: worktree LineFillGateBound (kappa_x 0.8, e_h 9 bar, need_ub at decision 147 inputs),
head reading = truth + read error (0 or -4.62 bar), reset on HOLD.
For each case the smallest N whose gate opens inside the RET is taken (the shortest 11b RET,
largest trapped excess). Reported at the HOLD reads after the RET:
  excess = p_tr - max(13 bar + p_h / 3, p_ret)      (the new stretch's retract candidate; p_ret is
           taken as the retract model itself, its plant value is lower than the model here)
  plan A margin = (p_hat + delta_m) - p_tr with p_hat >= p_r0 (exit seed max(p_hat, ④), ④ >= p_r0
           when J-P3b holds; p_hat not lowered in RET).
Units SI inside; printed bar (gauge), kN, mm/s, ms. Valve values are ASSUMPTIONS.
"""
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\z4369-jp3\03_src")
from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    LineFillGateBound, LineFillGateParams)
from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode  # noqa: E402
from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    RodPressureFlowLaw, flow_limited_rod_pressure_r6)

BAR = 1e5
OUT = Path(__file__).with_name(Path(__file__).stem + (sys.argv[3] if len(sys.argv) > 3 else "") + ".json")
V_MAX = 0.0209243016
U_HOLD = 0.01 * V_MAX
S_MAX, BETA, L0 = 0.70, 1.0e9, 0.05
P_T, P_BA = 2e5, 5e5
TAU, TAU_V = 0.05, 0.1
DT_CHUNK, DT_IN = 1e-3, 5e-4
T_PER = 0.1
DELTA_M = 0.5e5
C_V, F_N, DP_COMP = 0.02, 0.05, 10e5
CFG = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6, beta_hose_Pa=0.5e9,
                    psi=3.5, p_crack_Pa=3e5)
LEGS = {"front": dict(idx=0, A_h=0.013273229, A_ann=0.00376991118, e_op=0.4011),
        "rear": dict(idx=2, A_h=math.pi / 4 * 0.11**2, A_ann=math.pi / 4 * (0.11**2 - 0.09**2),
                     e_op=0.3909)}
E_READ = 4.0e5 + 3 * 0.2e5 + 0.025e5


def leg_consts(name):
    g = dict(LEGS[name])
    k_h = BETA * g["A_h"] / (L0 + g["e_op"])
    k_r = BETA * g["A_ann"] / (L0 + S_MAX - g["e_op"])
    g["C_r"] = RodPressureFlowLaw.rod_compliance_m3_Pa(g["A_ann"], k_h, k_r)
    g["params"] = RodChamberLegParams(head_area_m2=g["A_h"], annulus_area_m2=g["A_ann"],
                                      head_stiffness_N_m=k_h, rod_stiffness_N_m=k_r,
                                      outer_stiffness_N_m=math.inf, rod_weight_N=0.0)
    g["K_n"] = F_N * g["A_h"] * V_MAX / math.sqrt(DP_COMP)
    return g


GATE = LineFillGateBound(LineFillGateParams(), [LEGS["front"]["A_h"]] * 2 + [LEGS["rear"]["A_h"]] * 2,
                         [LEGS["front"]["A_ann"]] * 2 + [LEGS["rear"]["A_ann"]] * 2, S_MAX, V_MAX)


def valve_chunks(u_act, n_chunks):
    """Chunk-mean valve speed of a first-order lag on the per-period acting command."""
    out = np.empty(n_chunks)
    v = 0.0
    a = math.exp(-DT_CHUNK / TAU_V)
    for k in range(n_chunks):
        target = u_act[min(int(k * DT_CHUNK / T_PER + 1e-9), len(u_act) - 1)]
        v_new = target + (v - target) * a
        # exact mean of the exponential over the chunk
        out[k] = target + (v - target) * TAU_V / DT_CHUNK * (1 - a)
        v = v_new
    return out


def run_case(g, force, p_r0, speed, band, read_err, n_ret, n_hold=8, stop_on_gate=False):
    leg = g["idx"]
    a_h, a_ann = g["A_h"], g["A_ann"]
    p_h0 = (force + a_ann * p_r0) / a_h
    n_per = n_ret + n_hold
    u_act = [-speed] * n_ret + [0.0] * n_hold
    n_chunks = int(round(n_per * T_PER / DT_CHUNK))
    uv = valve_chunks(u_act, n_chunks)
    res_pl = retract_dead(CFG, p_h0, p_r0, band, g["e_op"], 0.0, a_h, a_ann, S_MAX, L0, L0, BETA,
                          P_T)
    need_pl, rise_pl = res_pl["need"], max(res_pl["p_open"] - P_T, 0.0)
    x = 0.0
    released = False
    t_rel = None
    p = p_r0
    GATE.reset(leg)
    t_gate = None
    head_ub = p_h0 + read_err + LineFillGateParams().head_reading_margin_Pa
    p_star = g["params"].moving_target_rod_pressure_Pa(RodChamberMode.RET, force)
    reads = []
    for k in range(n_chunks):
        t = (k + 1) * DT_CHUNK
        per = int(k * DT_CHUNK / T_PER + 1e-9)
        s = -uv[k]
        if not released:
            gfac = max(1.0 - abs(s) / (C_V * V_MAX), 0.0)
            level = min(x / need_pl, 1.0) if need_pl > 0 else 0.0
            drain = g["K_n"] * gfac * math.sqrt(rise_pl * level) / a_ann
            x = max(x + (max(s, 0.0) - drain) * DT_CHUNK, 0.0)
            if x >= need_pl and s > 1e-6:
                released, t_rel = True, t
                p = max(res_pl["p_rod"], p_r0)
        else:
            for _ in range(2):
                p = flow_limited_rod_pressure_r6(p, p_star, max(s, 0.0), DT_IN, TAU, g["C_r"],
                                                 a_h, a_ann, True, force, P_BA)
        if per < n_ret:
            if GATE.advance_substep(leg, uv[k], DT_CHUNK, head_ub, p_r0, g["e_op"], -1) \
                    and t_gate is None:
                t_gate = t
                if stop_on_gate:
                    break
        elif per == n_ret and t_gate is not None and not reads:
            pass
        if abs((t / T_PER) - round(t / T_PER)) < 1e-9 and round(t / T_PER) > n_ret:
            p_h = (force + a_ann * p) / a_h
            model = 13e5 + p_h / 3.0
            reads.append({"t_s": round(t, 3), "p_tr_bar": p / BAR, "p_h_bar": p_h / BAR,
                          "model_bar": model / BAR, "excess_bar": (p - model) / BAR,
                          "excess_kN": (p - model) * a_ann / 1e3,
                          "planA_margin_bar": (p_r0 + DELTA_M - p) / BAR,
                          "valve_mm_s": float(-uv[k]) * 1e3})
    return {"t_plant_release_ms": None if t_rel is None else round(t_rel * 1e3, 1),
            "t_gate_open_ms": None if t_gate is None else round(t_gate * 1e3, 1),
            "need_plant_mm": need_pl * 1e3, "p_h0_bar": p_h0 / BAR, "p_star_bar": p_star / BAR,
            "reads": reads}


N_RET_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def shortest_case(g, force, p_r0, speed, band, err):
    """Smallest N whose gate opens inside the RET: one long run finds the gate time, a second
    run with N = ceil(t_gate / T_per) gives the reads."""
    probe = run_case(g, force, p_r0, speed, band, err, N_RET_MAX, n_hold=1, stop_on_gate=True)
    if probe["t_gate_open_ms"] is None:
        return None, None
    n_ret = max(1, math.ceil(probe["t_gate_open_ms"] / 1e3 / T_PER - 1e-9))
    case = run_case(g, force, p_r0, speed, band, err, n_ret)
    if case["t_gate_open_ms"] is None:  # gate time on a chunk edge
        n_ret += 1
        case = run_case(g, force, p_r0, speed, band, err, n_ret)
    return n_ret, case


def decay_time(g, force, p_r0, speed):
    """Time at constant speed for P3 (c) to bring p_r0 down to the retract model (after release)."""
    a_h, a_ann = g["A_h"], g["A_ann"]
    p_star = g["params"].moving_target_rod_pressure_Pa(RodChamberMode.RET, force)
    p, t = p_r0, 0.0
    while t < 30.0:
        p_h = (force + a_ann * p) / a_h
        if p <= 13e5 + p_h / 3.0:
            return t
        p = flow_limited_rod_pressure_r6(p, p_star, speed, DT_IN, TAU, g["C_r"], a_h, a_ann, True,
                                         force, P_BA)
        t += DT_IN
    return math.inf


def main():
    rows = []
    speeds = (tuple(float(v) * 1e-3 for v in sys.argv[2].split(",")) if len(sys.argv) > 2
              else (1.2 * U_HOLD, 0.3e-3, 0.5e-3, 1.0e-3, 2.0e-3, 4.71e-3, V_MAX))
    for name in ("front", "rear"):
        g = leg_consts(name)
        for force, p_r0, speed, band, err in itertools.product(
                (2e3, 5e3, 10e3, 15e3, 25e3, 50e3), np.array([30, 45, 60, 80, 120]) * BAR,
                speeds, (0.0, 4e3), (0.0, -E_READ)):
            p_h0 = (force + g["A_ann"] * p_r0) / g["A_h"]
            p_star = g["params"].moving_target_rod_pressure_Pa(RodChamberMode.RET, force)
            if p_h0 > 210e5 or p_r0 <= p_star or p_r0 <= 13e5 + p_h0 / 3:
                continue
            n_ret, case = shortest_case(g, force, p_r0, speed, band, err)
            if case is None:
                continue
            first = case["reads"][0]
            worst_read = max(case["reads"], key=lambda r: r["excess_bar"])
            rows.append({"leg": name, "F_kN": force / 1e3, "p_r0_bar": p_r0 / BAR,
                         "p_h0_bar": round(case["p_h0_bar"], 2), "U_mm_s": round(speed * 1e3, 4),
                         "band_kN": band / 1e3, "read_err_bar": err / BAR, "n_ret": n_ret,
                         "t_plant_release_ms": case["t_plant_release_ms"],
                         "t_gate_open_ms": case["t_gate_open_ms"],
                         "window_ms": case["t_gate_open_ms"] - case["t_plant_release_ms"],
                         "start_excess_bar": (p_r0 - 13e5 - p_h0 / 3) / BAR,
                         "first_hold": first, "worst_hold_read": worst_read,
                         "min_planA_margin_bar": min(r["planA_margin_bar"] for r in case["reads"]),
                         "decay_to_model_s": decay_time(g, force, p_r0, speed)})
    # VBJ RR 49.0 s example of the control review (F 14.8 kN, p_r 59.9 bar)
    g = leg_consts("rear")
    example = {}
    for speed in (0.3e-3, 0.42e-3, 1.0e-3, 4.71e-3):
        n_ret, case = shortest_case(g, 14.8e3, 59.9e5, speed, 4e3 * 0.833, 0.0)
        if case is None:
            continue
        example[f"U{speed * 1e3:g}"] = {"n_ret": n_ret, "t_plant_release_ms":
                                        case["t_plant_release_ms"],
                                        "t_gate_open_ms": case["t_gate_open_ms"],
                                        "reads": case["reads"][:4],
                                        "decay_to_model_s": decay_time(g, 14.8e3, 59.9e5, speed)}
    summary = {
        "cases": len(rows),
        "max_first_hold_excess_bar": max(r["first_hold"]["excess_bar"] for r in rows),
        "max_any_hold_excess_bar": max(r["worst_hold_read"]["excess_bar"] for r in rows),
        "max_any_hold_excess_kN": max(r["worst_hold_read"]["excess_kN"] for r in rows),
        "min_planA_margin_bar": min(r["min_planA_margin_bar"] for r in rows),
        "share_first_hold_excess_ge_0.5_start": float(np.mean(
            [r["first_hold"]["excess_bar"] >= 0.5 * r["start_excess_bar"] for r in rows])),
        "min_retained_fraction_first_hold": min(
            r["first_hold"]["excess_bar"] / r["start_excess_bar"] for r in rows),
        "by_speed": {}}
    for speed in speeds:
        sel = [r for r in rows if abs(r["U_mm_s"] - round(speed * 1e3, 4)) < 1e-9]
        if not sel:
            continue
        summary["by_speed"][f"{speed * 1e3:.4g}"] = {
            "n": len(sel),
            "retained_fraction_first_hold_min": min(
                r["first_hold"]["excess_bar"] / r["start_excess_bar"] for r in sel),
            "retained_fraction_first_hold_max": max(
                r["first_hold"]["excess_bar"] / r["start_excess_bar"] for r in sel),
            "window_ms_min": min(r["window_ms"] for r in sel),
            "window_ms_max": max(r["window_ms"] for r in sel),
            "n_ret_max": max(r["n_ret"] for r in sel),
            "max_first_hold_excess_kN": max(r["first_hold"]["excess_kN"] for r in sel),
            "decay_to_model_s_range": [min(r["decay_to_model_s"] for r in sel),
                                       max(r["decay_to_model_s"] for r in sel)]}
    worst = sorted(rows, key=lambda r: -r["worst_hold_read"]["excess_kN"])[:6]
    OUT.write_text(json.dumps({"summary": summary, "example_VBJ_RR": example, "worst": worst,
                               "rows": rows}, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"summary": summary, "example_VBJ_RR": example}, indent=1, default=float))
    for r in worst:
        print({k: r[k] for k in ("leg", "F_kN", "p_r0_bar", "p_h0_bar", "U_mm_s", "band_kN",
                                 "read_err_bar", "n_ret", "window_ms", "start_excess_bar")},
              round(r["worst_hold_read"]["excess_bar"], 2), round(r["worst_hold_read"]["excess_kN"], 2))


if __name__ == "__main__":
    main()
