"""Rod-side pressure review for the outrigger leg cylinders (hydraulics-expert, 2026-10-22).

Short steady-state / quasi-static calculations only. All pressures in this script are GAUGE
unless named *_abs. SI units internally; printed in bar / kN.
Run: conda run -n hydraulics-dev python -I rod_side_calc.py <out.json>

Archived 2026-10-25 from the 2026-10-22 session scratchpad (hyd-run/rod_side). Values use the
OLD common cylinder dimensions (bore 115 / rod 110, stroke 680) of rod_side_pressure.md 0-11;
REXOME35 values are in rod_side_rexome35.py. Only change on archiving: output path is argv[1]
(was: next to this script).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import fluids
import numpy as np
import pint
from scipy.optimize import brentq

ureg = pint.UnitRegistry()
BAR = ureg("1 bar").to("Pa").magnitude  # 1e5 Pa
P_ATM = 1.01325e5  # Pa abs

# --- project values (02_params/rexome33.yaml, CLAUDE.md) ---------------------------------
D_BORE = 0.115
D_ROD = 0.110
A_P = math.pi / 4 * D_BORE**2  # head area
A_ANN = math.pi / 4 * (D_BORE**2 - D_ROD**2)  # annulus area
PHI = A_P / A_ANN
S_MAX = 0.68
L0 = 0.05  # dead length head side (ASSUMPTION, YAML); same used for rod side (ASSUMPTION)
BETA = 1.0e9  # user decision
M_ROD = 106.783666
G = 9.80665
MG = M_ROD * G
F_MIN = 9453.0
E_OP = {"front": 0.4015, "rear": 0.3915}  # back-solved from k_oil / k_ann in dynamics_model 2.3
V_MAX = 0.68 / 30.0
P_RELIEF = 210 * BAR

# --- assumptions (not in the source) ------------------------------------------------------
RHO = 870.0  # kg/m3, ISO VG 46 class at ~40 degC (ASSUMPTION)
NU = 46e-6  # m2/s at 40 degC (ASSUMPTION)
SIGMA_P = 0.3 * BAR  # 1-sigma pressure reading per sensor (task statement, ~0.3 kN/A_p)


def k_head(e: float) -> float:
    return BETA * A_P / (L0 + e)


def k_rod(e: float) -> float:
    return BETA * A_ANN / (S_MAX - e + L0)


# ---------------------------------------------------------------------------------------
# 1) Locked chamber with entrained free air: volume-pressure law
# ---------------------------------------------------------------------------------------
def rod_pressure_locked(dv_compress: float, v0: float, p0: float, x_air_atm: float,
                        n_poly: float = 1.0, p_floor_abs: float = 0.1e5) -> float:
    """Gauge pressure of a trapped chamber after its volume shrinks by dv_compress (m3, <0 grows).

    Liquid: linear bulk modulus BETA. Free air: x_air_atm = gas volume fraction at 1 atm abs,
    polytropic n_poly. Below p_floor_abs (gas release / vapour) the pressure is clamped.
    """
    p0_abs = p0 + P_ATM
    v_gas_atm = x_air_atm * v0  # gas volume referred to 1 atm (fraction of chamber volume)
    v_gas0 = v_gas_atm * (P_ATM / p0_abs) ** (1 / n_poly)
    v_liq0 = v0 - v_gas0

    def residual(p_abs: float) -> float:
        v_liq = v_liq0 * (1 - (p_abs - p0_abs) / BETA)
        v_gas = v_gas_atm * (P_ATM / p_abs) ** (1 / n_poly) if v_gas_atm > 0 else 0.0
        return (v_liq + v_gas) - (v0 - dv_compress)

    if residual(p_floor_abs) < 0:  # chamber grew more than the floor allows -> released gas
        return p_floor_abs - P_ATM
    p_abs = brentq(residual, p_floor_abs, 2000e5)
    return p_abs - P_ATM


def unload_to_liftoff(f0: float, e: float, p_r0: float, x_air: float, f_s: float = 0.0) -> dict:
    """Locked leg unloaded from cylinder force f0 until the pad force is 0 (F_cyl = -m g).

    Friction: stuck until the oil-force change reaches 2 f_s from the end of loading (the
    worst case for the reading: friction last acted against loading, so it holds +f_s on
    the way down) -> the oil carries only (f0 + mg - f_s) of the unloading. Here we model the
    simple case 'friction initially 0 (mid-band) and holds up to f_s', i.e. the oil force at
    lift-off is -mg + f_s (cylinder force by oil) and the pad force is 0.
    """
    p_h0 = (f0 + p_r0 * A_ANN) / A_P
    l_h, l_r = L0 + e, S_MAX - e + L0
    v_r0 = A_ANN * l_r
    f_oil_target = -MG + f_s  # oil force when the pad just reaches 0 (friction at +f_s)

    def oil_force(ds: float) -> tuple[float, float, float]:
        p_h = p_h0 - BETA * ds / l_h  # head decompresses (high pressure, liquid only)
        p_r = rod_pressure_locked(A_ANN * ds, v_r0, p_r0, x_air)
        return p_h * A_P - p_r * A_ANN, p_h, p_r

    ds = brentq(lambda d: oil_force(d)[0] - f_oil_target, 0.0, 0.05)
    f, p_h, p_r = oil_force(ds)
    return {
        "F0_kN": f0 / 1e3, "x_air_atm": x_air, "F_s_kN": f_s / 1e3,
        "piston_out_mm": ds * 1e3, "p_h_bar": p_h / BAR, "p_r_bar": p_r / BAR,
        "head_only_reading_kN": p_h * A_P / 1e3, "two_sensor_reading_kN": f / 1e3,
        "true_cyl_force_kN": -MG / 1e3,
        "head_only_minus_Fmin_kN": (p_h * A_P - F_MIN) / 1e3,
    }


def load_until_floor(e: float, p_r0: float, x_air: float) -> dict:
    """Locked leg loaded further: force increase until the rod chamber reaches the floor."""
    l_h, l_r = L0 + e, S_MAX - e + L0
    v_r0 = A_ANN * l_r
    floor = 0.1e5 - P_ATM

    def p_r_of(ds_in: float) -> float:
        return rod_pressure_locked(-A_ANN * ds_in, v_r0, p_r0, x_air)

    ds = brentq(lambda d: p_r_of(d) - (floor + 1.0), 0.0, 0.3)
    df = BETA * ds / l_h * A_P + (p_r0 - floor) * A_ANN
    return {"x_air_atm": x_air, "piston_in_mm": ds * 1e3, "dF_to_floor_kN": df / 1e3,
            "rod_force_released_kN": (p_r0 - floor) * A_ANN / 1e3}


# ---------------------------------------------------------------------------------------
# 2) Moving states
# ---------------------------------------------------------------------------------------
def retract_pressures(f_cyl: float, psi: float, p_back_a: float, p_crack: float = 2 * BAR
                      ) -> tuple[float, float]:
    """Retraction, meter-in limited (pilot-threshold regime, lower bound of p_r).

    f_cyl = p_h A_p - p_r A_ann (+ = pushes pad down). Head flows out through the head POC
    (internal drain, opens at p_r >= p_A + (p_h - p_A)/psi + p_crack) and the A->T notch with
    line pressure p_A >= p_back_a. Returns (p_h, p_r) gauge.
    """
    p_h_pilot = (f_cyl / A_ANN + p_crack + p_back_a - p_back_a / psi) / (PHI - 1 / psi)
    p_h = max(p_back_a, p_h_pilot)
    p_r = (p_h * A_P - f_cyl) / A_ANN
    return p_h, p_r


def hose_dp(q_lpm: float, d_in: float = 9.5e-3, length: float = 4.0) -> float:
    """Straight-hose pressure drop (Pa) with fluids (Darcy, smooth)."""
    q = q_lpm / 60000
    v = q / (math.pi / 4 * d_in**2)
    re = v * d_in / NU
    fd = fluids.friction_factor(Re=re, eD=0.0)
    return fd * length / d_in * RHO * v**2 / 2


def main() -> None:
    out: dict = {"inputs": {
        "A_p_m2": A_P, "A_ann_m2": A_ANN, "phi": PHI, "mg_N": MG, "beta_Pa": BETA,
        "L0_m": L0, "e_op_m": E_OP, "sigma_p_bar": SIGMA_P / BAR}}

    # flows
    q_head = V_MAX * A_P * 60000
    q_rod = V_MAX * A_ANN * 60000
    out["flows_lpm_per_leg"] = {"head": q_head, "rod": q_rod}
    out["hose_dp_bar_4m_3_8in"] = {"head_14lpm": hose_dp(q_head) / BAR,
                                   "rod_1.2lpm": hose_dp(q_rod) / BAR}

    # stiffness split
    out["stiffness"] = {}
    for side, e in E_OP.items():
        kh, kr = k_head(e), k_rod(e)
        out["stiffness"][side] = {
            "k_head": kh, "k_rod": kr, "r=k_r/(k_h+k_r)": kr / (kh + kr),
            "dp_r/dp_h (locked, beta const)": -(BETA / (S_MAX - e + L0)) / (BETA / (L0 + e)),
            "L_h_m": L0 + e, "L_r_m": S_MAX - e + L0}

    # locked unloading to lift-off
    rows = []
    for f0 in (20e3, 60e3, 100e3, 140e3):
        for x_air in (0.0, 0.001, 0.01):
            for f_s in (0.0, 5e3, 12e3):
                if f_s > f0:
                    continue
                rows.append(unload_to_liftoff(f0, E_OP["front"], 3 * BAR, x_air, f_s))
    out["locked_unload_to_liftoff_front_pr0_3bar"] = rows

    # head-only reading at lift-off vs F0 (beta const, F_s 0): find F0 where it reaches F_min
    def ho_minus_fmin(f0: float) -> float:
        return unload_to_liftoff(f0, E_OP["front"], 3 * BAR, 0.0)["head_only_minus_Fmin_kN"]
    out["F0_where_head_only_liftoff_reading_eq_Fmin_kN"] = {
        "x_air_0": brentq(ho_minus_fmin, 1e3, 300e3) / 1e3}
    for x_air in (0.001, 0.01):
        def g(f0: float, xa: float = x_air) -> float:
            return unload_to_liftoff(f0, E_OP["front"], 3 * BAR, xa)["head_only_minus_Fmin_kN"]
        out["F0_where_head_only_liftoff_reading_eq_Fmin_kN"][f"x_air_{x_air}"] = (
            brentq(g, 1e3, 400e3) / 1e3)

    # locked loading: how fast the rod side empties
    out["locked_load_to_floor_front"] = [
        load_until_floor(E_OP["front"], p0, xa) for p0 in (3 * BAR, 30 * BAR)
        for xa in (0.0, 0.001, 0.01)]

    # retraction, grounded and airborne
    ret = []
    for f_cyl in (100e3, 60e3, 20e3, -MG):
        for psi in (3.0, 4.0, 6.0):
            for pba in (3 * BAR, 8 * BAR, 15 * BAR):
                p_h, p_r = retract_pressures(f_cyl, psi, pba)
                ret.append({"F_cyl_kN": f_cyl / 1e3, "psi": psi, "p_backA_bar": pba / BAR,
                            "p_h_bar": p_h / BAR, "p_r_bar": p_r / BAR,
                            "head_only_err_kN": p_r * A_ANN / 1e3})
    out["retract_meter_in_limited"] = ret

    # airborne retraction needs: p_r = (mg + F_s + p_backA A_p)/A_ann
    air = []
    for f_s in (0.0, 2e3, 5e3, 12e3):
        for pba in (3 * BAR, 8 * BAR, 15 * BAR):
            p_r = (MG + f_s + pba * A_P) / A_ANN
            air.append({"F_s_kN": f_s / 1e3, "p_backA_bar": pba / BAR, "p_r_bar": p_r / BAR,
                        "exceeds_210bar": p_r > P_RELIEF,
                        "head_only_reading_kN": pba * A_P / 1e3,
                        "true_F_cyl_kN": (pba * A_P - p_r * A_ANN) / 1e3})
    out["retract_airborne"] = air
    out["retract_airborne_Fs_limit_kN"] = {
        f"p_backA_{b}bar": (P_RELIEF * A_ANN - MG - b * BAR * A_P) / 1e3 for b in (3, 8, 15)}

    # extension
    out["extend"] = {
        "p_r_range_bar": [1, 8],
        "head_only_err_kN": [1 * BAR * A_ANN / 1e3, 8 * BAR * A_ANN / 1e3],
        "airborne_hold_weight_p_r_bar (F_s=0)": MG / A_ANN / BAR}

    # noise
    s_head = SIGMA_P * A_P
    s_two = math.hypot(SIGMA_P * A_P, SIGMA_P * A_ANN)
    out["noise"] = {"head_only_sigma_kN": s_head / 1e3, "two_sensor_sigma_kN": s_two / 1e3,
                    "increase_pct": (s_two / s_head - 1) * 100,
                    "rod_sigma_1bar_two_sensor_kN": math.hypot(SIGMA_P * A_P, BAR * A_ANN) / 1e3,
                    "rod_offset_0.5bar_kN": 0.5 * BAR * A_ANN / 1e3,
                    "head_offset_0.5bar_kN": 0.5 * BAR * A_P / 1e3}

    # probe (C2): +2 mm / -2 mm, head-only bias on F_s and midpoint
    probe = []
    for p_r_ext, p_r_ret in ((3 * BAR, 30 * BAR), (3 * BAR, 40 * BAR), (3 * BAR, 20 * BAR)):
        probe.append({"p_r_ext_bar": p_r_ext / BAR, "p_r_ret_bar": p_r_ret / BAR,
                      "F_s_hat_bias_kN": -(p_r_ret - p_r_ext) * A_ANN / 2 / 1e3,
                      "midpoint_bias_kN": (p_r_ret + p_r_ext) * A_ANN / 2 / 1e3})
    out["probe_head_only_bias"] = probe

    # sensitivity: rod-side dead length (block passage volume / A_ann), beta const, F_s 0
    sens = []
    for side, f0 in (("front", 118e3), ("rear", 72e3), ("front", 100e3)):
        e = E_OP[side]
        kh = k_head(e)
        for l0r in (0.05, 0.2, 0.6):
            kr = BETA * A_ANN / (S_MAX - e + l0r)
            r = kr / (kh + kr)
            p_r0 = 3 * BAR
            ho = -MG + p_r0 * A_ANN + r * (f0 + MG)
            sens.append({"side": side, "F0_kN": f0 / 1e3, "L0_rod_m": l0r, "r": r,
                         "p_r_liftoff_bar": (p_r0 * A_ANN + r * (f0 + MG)) / A_ANN / BAR,
                         "head_only_liftoff_reading_kN": ho / 1e3})
    out["liftoff_sensitivity_rod_dead_length"] = sens

    # thermal: trapped rod chamber, grounded leg (incremental support stiffness S_FL 4.77e6 N/m,
    # actuator_L2_feasibility.md), oil volumetric expansion alpha (ASSUMPTION 6.5e-4 1/K net)
    alpha = 6.5e-4
    s_leg = 4.77e6
    e = E_OP["front"]
    kh = k_head(e)
    l_r = S_MAX - e + L0
    dp_per_k = alpha / (1 / BETA + A_ANN / (l_r * (kh + s_leg)))
    dx_per_k = dp_per_k * A_ANN / (kh + s_leg)
    out["thermal_rod_chamber_front"] = {
        "alpha_1_K": alpha, "S_leg_N_m": s_leg,
        "dp_r_bar_per_K": dp_per_k / BAR,
        "dF_cyl_true_kN_per_K": -s_leg * dx_per_k / 1e3,
        "head_only_reading_change_kN_per_K": kh * dx_per_k / 1e3,
        "head_only_error_growth_kN_per_K": dp_per_k * A_ANN / 1e3,
        "cooling_K_to_reach_floor_from_3bar": (3 * BAR + 0.9 * BAR) / dp_per_k}

    # locked lift-off visibility by pressure alone: largest F_s for which the reading at
    # lift-off is below F_min - 3 sigma (F_s held fully, beta const, p_r0 3 bar, L0_rod 0.05)
    vis = {}
    s3 = 3 * math.hypot(SIGMA_P * A_P, SIGMA_P * A_ANN)
    for side, f0 in (("front", 118e3), ("rear", 72e3)):
        e = E_OP[side]
        kh, kr = k_head(e), k_rod(e)
        r = kr / (kh + kr)
        rhs_ho = F_MIN - 3 * SIGMA_P * A_P + MG - 3 * BAR * A_ANN - r * (f0 + MG)
        vis[side] = {"F0_kN": f0 / 1e3, "r": r,
                     "head_only_Fs_max_kN": max(rhs_ho / (1 - r), float("nan")) / 1e3
                     if rhs_ho > 0 else None,
                     "two_sensor_Fs_max_kN": (F_MIN + MG - s3) / 1e3}
    out["locked_liftoff_visibility"] = vis
    # rod side reaches 350 bar on locked unloading from F0 (beta const, L0_rod 0.05, p_r0 3 bar)
    out["F0_for_rod_350bar_on_liftoff_kN"] = {
        side: ((350 - 3) * BAR * A_ANN / (k_rod(e) / (k_head(e) + k_rod(e))) - MG) / 1e3
        for side, e in E_OP.items()}

    path = Path(sys.argv[1])
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
