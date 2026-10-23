"""Rod-side pressure parameters with the REXOME35 cylinder drawing (hydraulics-expert, 2026-10-22).

Supplement to 00_docs/02_hydraulic/rod_side_pressure.md (section 12):
  P   rod-side model parameters per leg type (front / rear): chamber stiffness split r,
      locked dp_r/dp_h, moving-state rod pressures, head-only bias, lift-off readings,
      two-sensor visibility limit, thermal rate
  H-1 dynamic load surge during slow retraction (S6 RE3 FR 260.8 kN, RL 182.8 kN):
      head / rod / A-line pressure in the meter-in (pilot-check throttling) and the
      meter-out (pilot check fully open) regime, transient stall instead of overrun
  H-2 'locked at the dynamic peak, then unloaded to lift-off' rod pressure, incl. the
      lock-state history (extend / retract pilot threshold / meter-out), free gas and the
      rod-side floor (cavitation, gas release) after an overload of a locked leg

All pressures GAUGE unless *_abs. SI inside; printed in bar / kN / mm.
Quasi-static, lumped chambers, constant beta (+ optional free gas). No line dynamics.
Run: conda run -n hydraulics-dev python -I rod_side_rexome35.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scipy.optimize import brentq

BAR = 1.0e5
P_ATM = 1.01325e5
G = 9.80665

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "06_analysis" / "03_hydraulic"

# REXOME35-9206 Rev.0 drawing (user decision 2026-10-22); bore/rod from H9/f8 fits
LEGS = {
    "front": {"bore": 0.130, "rod": 0.110, "e_op": 0.4015, "F_static": 118.25e3, "F_peak": [260.8e3, 265.6e3]},
    "rear": {"bore": 0.110, "rod": 0.090, "e_op": 0.3915, "F_static": 72.8e3, "F_peak": [182.8e3]},
}
S_MAX = 0.700  # drawing stroke
L0_HEAD = 0.05  # ASSUMPTION (YAML oil_dead_length_m); sensitivity 0.02 / 0.2
L0_ROD = 0.05  # ASSUMPTION (block passage volume / A_ann); sensitivity 0.02 / 0.2 / 0.6
BETA = 1.0e9  # user decision
M_ROD = 106.784  # REXOME33 CAD moving mass (before the dimension change)
MG = M_ROD * G
F_MIN = 9452.5
P_RELIEF = 210 * BAR
P_LOCK_LIMIT = 350 * BAR
P_FLOOR_ABS = 0.1e5  # ASSUMPTION: cavitation / gas-release floor
# valve assumptions (rod_side_pressure.md 7.3)
PSI = 3.5
P_CR = 3 * BAR
P_BA = 5 * BAR
P_BB = 5 * BAR
P_R0_EXT = 2 * BAR
# B line between MCV and the rod-side POC (outside the locked volume): 3/8" hose, 4 m (ASSUMPTION)
V_HOSE_B = math.pi / 4 * 9.5e-3**2 * 4.0
S_LEG_SUPPORT = 4.77e6  # incremental support stiffness used in rod_side_pressure.md 3.2 (thermal)
ALPHA_OIL = 6.5e-4  # ASSUMPTION net volumetric expansion, 1/K
AIR_SOL_BUNSEN = 0.09  # ASSUMPTION: dissolved air volume fraction at 1 atm (mineral oil, typical)


def geom(leg: str, e: float | None = None, l0h: float = L0_HEAD, l0r: float = L0_ROD) -> dict:
    c = LEGS[leg]
    a_p = math.pi / 4 * c["bore"] ** 2
    a_ann = math.pi / 4 * (c["bore"] ** 2 - c["rod"] ** 2)
    e = c["e_op"] if e is None else e
    l_h, l_r = l0h + e, S_MAX - e + l0r
    k_h, k_r = BETA * a_p / l_h, BETA * a_ann / l_r
    return {"A_p": a_p, "A_ann": a_ann, "phi": a_p / a_ann, "e": e, "L_h": l_h, "L_r": l_r,
            "k_h": k_h, "k_r": k_r, "r": k_r / (k_h + k_r), "V_r": a_ann * l_r, "V_h": a_p * l_h}


# ----------------------------------------------------------------------------- locked chamber
def p_locked(dv_compress: float, v0: float, p0: float, x_air_atm: float, n_poly: float = 1.0) -> float:
    """Gauge pressure of a trapped chamber after its volume shrinks by dv_compress (m3; < 0 grows)."""
    p0_abs = p0 + P_ATM
    v_gas_atm = x_air_atm * v0
    v_gas0 = v_gas_atm * (P_ATM / p0_abs) ** (1 / n_poly)
    v_liq0 = v0 - v_gas0

    def res(p_abs: float) -> float:
        v_liq = v_liq0 * (1 - (p_abs - p0_abs) / BETA)
        v_gas = v_gas_atm * (P_ATM / p_abs) ** (1 / n_poly) if v_gas_atm > 0 else 0.0
        return (v_liq + v_gas) - (v0 - dv_compress)

    if res(P_FLOOR_ABS) < 0:
        return P_FLOOR_ABS - P_ATM
    return brentq(res, P_FLOOR_ABS, 20000e5) - P_ATM


def unload_to_liftoff(leg: str, f0: float, p_r0: float, x_air: float = 0.0, f_s: float = 0.0,
                      **gkw) -> dict:
    """Locked at cylinder force f0 (rod pressure p_r0), unloaded until the pad force is 0.

    Friction holds +f_s at lift-off (oil force -mg + f_s); f_s = 0 is the worst case for p_r.
    """
    g = geom(leg, **gkw)
    p_h0 = (f0 + p_r0 * g["A_ann"]) / g["A_p"]
    target = -MG + f_s

    def oil(ds: float) -> tuple[float, float, float]:
        p_h = p_h0 - BETA * ds / g["L_h"]
        p_r = p_locked(g["A_ann"] * ds, g["V_r"], p_r0, x_air)
        return p_h * g["A_p"] - p_r * g["A_ann"], p_h, p_r

    ds = brentq(lambda d: oil(d)[0] - target, 0.0, 0.05)
    f, p_h, p_r = oil(ds)
    return {"leg": leg, "F0_kN": f0 / 1e3, "p_r0_bar": p_r0 / BAR, "x_air": x_air, "F_s_kN": f_s / 1e3,
            "p_h0_bar": p_h0 / BAR, "piston_out_mm": ds * 1e3, "p_h_bar": p_h / BAR, "p_r_bar": p_r / BAR,
            "head_only_reading_kN": p_h * g["A_p"] / 1e3, "two_sensor_kN": f / 1e3,
            "margin_to_350_pct": (1 - p_r / P_LOCK_LIMIT) * 100}


def load_until_floor(leg: str, p_r0: float, x_air: float = 0.0) -> dict:
    """Locked leg loaded above its lock load: force increase until the rod side reaches the floor."""
    g = geom(leg)
    floor = P_FLOOR_ABS - P_ATM

    def p_r_of(ds_in: float) -> float:
        return p_locked(-g["A_ann"] * ds_in, g["V_r"], p_r0, x_air)

    ds = brentq(lambda d: p_r_of(d) - (floor + 1.0), 0.0, 0.3)
    df = BETA * ds / g["L_h"] * g["A_p"] + (p_r0 - floor) * g["A_ann"]
    return {"leg": leg, "p_r0_bar": p_r0 / BAR, "x_air": x_air, "piston_in_mm": ds * 1e3,
            "dF_to_floor_kN": df / 1e3}


def overload_void(leg: str, f_lock: float, f_peak: float, p_r0: float) -> dict:
    """Locked at f_lock, loaded to f_peak: rod side at the floor, void volume, released gas bound."""
    g = geom(leg)
    fl = load_until_floor(leg, p_r0)
    df_rest = max(0.0, f_peak - f_lock - fl["dF_to_floor_kN"] * 1e3)
    ds_after = df_rest / g["k_h"]  # head chamber only once the rod side is at the floor
    ds_total = fl["piston_in_mm"] * 1e-3 + ds_after
    void = g["A_ann"] * ds_after  # m3 opened at the floor pressure
    # upper bound of released gas: the void fills with gas at P_FLOOR_ABS; referred to 1 atm
    gas_atm = void * P_FLOOR_ABS / P_ATM
    # dissolved-air reservoir in the rod chamber (equilibrium bound, not kinetics)
    dissolved_atm = AIR_SOL_BUNSEN * g["V_r"] * (1 - P_FLOOR_ABS / (p_r0 + P_ATM))
    x_air_after = min(gas_atm, dissolved_atm) / g["V_r"]
    return {"leg": leg, "F_lock_kN": f_lock / 1e3, "F_peak_kN": f_peak / 1e3, "p_r0_bar": p_r0 / BAR,
            "dF_to_floor_kN": fl["dF_to_floor_kN"], "piston_in_total_mm": ds_total * 1e3,
            "void_cc": void * 1e6, "gas_bound_cc_at_1atm": gas_atm * 1e6,
            "dissolved_air_reservoir_cc_at_1atm": dissolved_atm * 1e6, "x_air_after_bound": x_air_after,
            "stiffness_locked_both_N_m": g["k_h"] + g["k_r"], "stiffness_rod_at_floor_N_m": g["k_h"],
            "stiffness_drop_pct": g["k_r"] / (g["k_h"] + g["k_r"]) * 100}


# ----------------------------------------------------------------------------- moving states
def retract_meter_in(leg: str, f_cyl: float, psi: float = PSI, p_ba: float = P_BA, p_cr: float = P_CR) -> dict:
    """Retraction with the head POC throttling (pilot threshold, lower bound of p_r)."""
    g = geom(leg)
    p_h = (f_cyl / g["A_ann"] + p_cr + p_ba * (1 - 1 / psi)) / (g["phi"] - 1 / psi)
    p_h = max(p_ba, p_h)
    p_r = (p_h * g["A_p"] - f_cyl) / g["A_ann"]
    return {"F_cyl_kN": f_cyl / 1e3, "psi": psi, "p_bA_bar": p_ba / BAR, "p_h_bar": p_h / BAR,
            "p_r_bar": p_r / BAR, "F_over_Ap_bar": f_cyl / g["A_p"] / BAR,
            "head_only_bias_kN": p_r * g["A_ann"] / 1e3, "A_line_bar": p_ba / BAR}


def retract_meter_out_bound(leg: str, f_cyl: float) -> dict:
    """POC fully open, meter-out notch limits: rod side may rise to the relief (upper bound)."""
    g = geom(leg)
    p_h = (f_cyl + P_RELIEF * g["A_ann"]) / g["A_p"]
    return {"F_cyl_kN": f_cyl / 1e3, "p_r_bar": P_RELIEF / BAR, "p_h_bar": p_h / BAR,
            "A_line_bar_upper": p_h / BAR}


def stall_from_surge(leg: str, f_before: float, f_peak: float, v_cmd: float = 5e-3) -> dict:
    """Meter-in retraction: a load surge raises the pilot threshold; the pump must first compress the
    rod side + B line to the new threshold at the meter-in flow -> the piston stalls (no overrun)."""
    g = geom(leg)
    a = retract_meter_in(leg, f_before)
    b = retract_meter_in(leg, f_peak)
    dp = (b["p_r_bar"] - a["p_r_bar"]) * BAR
    dv = (g["V_r"] + V_HOSE_B) * dp / BETA
    q = g["A_ann"] * v_cmd
    return {"leg": leg, "p_r_before_bar": a["p_r_bar"], "p_r_peak_bar": b["p_r_bar"],
            "dV_to_recompress_cc": dv * 1e6, "meter_in_flow_L_min": q * 6e4,
            "stall_time_s": dv / q, "lost_stroke_mm": dv / g["A_ann"] * 1e3}


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out: dict = {"assumptions": {"S_MAX_m": S_MAX, "L0_head_m": L0_HEAD, "L0_rod_m": L0_ROD, "beta_Pa": BETA,
                                 "m_rod_kg": M_ROD, "psi": PSI, "p_cr_bar": P_CR / BAR, "p_bA_bar": P_BA / BAR,
                                 "p_bB_bar": P_BB / BAR, "p_r0_ext_bar": P_R0_EXT / BAR,
                                 "floor_bar_abs": P_FLOOR_ABS / BAR, "V_hose_B_L": V_HOSE_B * 1e3,
                                 "e_op_m": {k: v["e_op"] for k, v in LEGS.items()}}}
    # ---- P: parameters
    par = {}
    for leg in LEGS:
        g = geom(leg)
        sig_f = {s: math.hypot(s * BAR * g["A_p"], s * BAR * g["A_ann"]) for s in (0.3, 0.07)}
        p = {
            **{k: g[k] for k in ("A_p", "A_ann", "phi", "L_h", "L_r", "k_h", "k_r", "r", "V_r", "V_h")},
            "L_r_over_L_h": g["L_r"] / g["L_h"],
            "dp_r_dp_h_locked": -g["L_h"] / g["L_r"],
            "dp_r_bar_per_100kN_unload": g["r"] * 1e5 / g["A_ann"] / BAR,
            "weight_hold_p_r_bar": MG / g["A_ann"] / BAR,
            "extend_p_r_airborne_bar": max(P_BB, MG / g["A_ann"]) / BAR,
            "head_only_bias_per_bar_N": BAR * g["A_ann"],
            "sigma_F_two_sensor_kN": {str(s): v / 1e3 for s, v in sig_f.items()},
            "two_sensor_static_liftoff_Fs_max_kN": {str(s): (F_MIN + MG - 3 * v) / 1e3 for s, v in sig_f.items()},
            "F0_for_rod_350bar_liftoff_kN": ((P_LOCK_LIMIT - P_R0_EXT) * g["A_ann"] / g["r"] - MG) / 1e3,
            "F_head_350bar_kN": P_LOCK_LIMIT * g["A_p"] / 1e3,
            "F_retract_210bar_kN": P_RELIEF * g["A_ann"] / 1e3,
            "F_extend_210bar_kN": P_RELIEF * g["A_p"] / 1e3,
            "dF_locked_load_to_floor_kN_pr0_2bar": load_until_floor(leg, P_R0_EXT)["dF_to_floor_kN"],
        }
        # thermal (trapped rod chamber, grounded)
        dp_k = ALPHA_OIL / (1 / BETA + g["A_ann"] / (g["L_r"] * (g["k_h"] + S_LEG_SUPPORT)))
        dx_k = dp_k * g["A_ann"] / (g["k_h"] + S_LEG_SUPPORT)
        p["thermal"] = {"dp_r_bar_per_K": dp_k / BAR, "dF_true_kN_per_K": -S_LEG_SUPPORT * dx_k / 1e3,
                        "head_only_error_kN_per_K": dp_k * g["A_ann"] / 1e3,
                        "cool_K_to_floor_from_2bar": (P_R0_EXT - (P_FLOOR_ABS - P_ATM)) / dp_k}
        # retraction (grounded) pilot threshold table and airborne retraction
        p["retract_grounded"] = [retract_meter_in(leg, f, psi, pba)
                                 for f in (20e3, 60e3, 100e3, LEGS[leg]["F_static"])
                                 for psi in (3.0, 3.5, 6.0) for pba in (3 * BAR, 5 * BAR, 15 * BAR)]
        p["retract_airborne"] = [{"F_s_kN": fs / 1e3, "p_bA_bar": pba / BAR,
                                  "p_r_bar": (MG + fs + pba * g["A_p"]) / g["A_ann"] / BAR,
                                  "head_only_reading_kN": pba * g["A_p"] / 1e3,
                                  "two_sensor_kN": -(MG + fs) / 1e3}
                                 for fs in (0.0, 3.7e3, 12e3) for pba in (3 * BAR, 5 * BAR, 15 * BAR)]
        p["retract_airborne_Fs_limit_kN"] = {f"p_bA_{b}": (P_RELIEF * g["A_ann"] - MG - b * BAR * g["A_p"]) / 1e3
                                             for b in (3, 5, 15, 48)}
        # static lift-off from the static locked load (after extension, p_r0 2 bar)
        p["liftoff_static"] = [unload_to_liftoff(leg, LEGS[leg]["F_static"], P_R0_EXT, xa)
                               for xa in (0.0, 0.001, 0.01)]
        # locked after a grounded retraction (probe end): p_r0 = pilot threshold
        thr = retract_meter_in(leg, LEGS[leg]["F_static"])
        p["locked_after_retract"] = {"p_r0_bar": thr["p_r_bar"], "head_only_bias_kN": thr["head_only_bias_kN"],
                                     "liftoff": unload_to_liftoff(leg, LEGS[leg]["F_static"], thr["p_r_bar"] * BAR)}
        # sensitivity to dead lengths and e_op
        sens = []
        for l0r in (0.02, 0.05, 0.2, 0.6):
            for de in (-0.02, 0.0, 0.02):
                gg = geom(leg, e=LEGS[leg]["e_op"] + de, l0r=l0r)
                sens.append({"L0_rod_m": l0r, "e_m": gg["e"], "r": gg["r"],
                             "dp_r_bar_per_100kN": gg["r"] * 1e5 / gg["A_ann"] / BAR,
                             "dp_r_dp_h": -gg["L_h"] / gg["L_r"]})
        p["sensitivity_r"] = sens
        par[leg] = p
    out["parameters"] = par

    # ---- H-1
    h1 = {}
    cases = {"front": (116.3e3, 260.8e3), "rear": (72.8e3, 182.8e3)}
    for leg, (f0, fpk) in cases.items():
        g = geom(leg)
        h1[leg] = {"F_before_kN": f0 / 1e3, "F_peak_kN": fpk / 1e3, "F_peak_over_Ap_bar": fpk / g["A_p"] / BAR,
                   "meter_in_before": retract_meter_in(leg, f0), "meter_in_peak": retract_meter_in(leg, fpk),
                   "meter_in_peak_psi3": retract_meter_in(leg, fpk, psi=3.0),
                   "meter_in_peak_psi6": retract_meter_in(leg, fpk, psi=6.0),
                   "meter_out_peak_bound": retract_meter_out_bound(leg, fpk),
                   "stall": stall_from_surge(leg, f0, fpk),
                   "F_for_head_210bar_meter_in_kN": brentq(
                       lambda f, lg=leg: retract_meter_in(lg, f)["p_h_bar"] - 210.0, 1e3, 600e3) / 1e3,
                   "F_for_head_350bar_meter_in_kN": brentq(
                       lambda f, lg=leg: retract_meter_in(lg, f)["p_h_bar"] - 350.0, 1e3, 900e3) / 1e3}
        # old YAML dimensions for comparison (F/A_p)
        h1[leg]["F_peak_over_Ap_old_yaml_bar"] = fpk / (math.pi / 4 * 0.115**2) / BAR
    out["H1"] = h1

    # ---- H-2
    h2 = []
    for leg in LEGS:
        for fpk in LEGS[leg]["F_peak"]:
            thr = retract_meter_in(leg, fpk)["p_r_bar"] * BAR
            for label, pr0 in (("a_extend_lock_pr0_2", P_R0_EXT), ("a_extend_lock_pr0_5", P_BB),
                               ("b_retract_meter_in_threshold", thr), ("b_retract_meter_out_210", P_RELIEF)):
                for xa in (0.0, 0.0014, 0.01):
                    for fs in (0.0, 3.7e3):
                        r = unload_to_liftoff(leg, fpk, pr0, xa, fs)
                        r["case"] = label
                        h2.append(r)
    out["H2_lock_at_peak_then_liftoff"] = h2
    # F0 at which the lift-off rod pressure reaches 350 bar for each lock state (F_s 0, no gas)
    lim = {}
    for leg in LEGS:
        lim[leg] = {}
        for label in ("a_extend_lock_pr0_2", "b_retract_meter_in_threshold", "b_retract_meter_out_210"):
            def fun(f0, lg=leg, lb=label):
                if lb == "a_extend_lock_pr0_2":
                    pr0 = P_R0_EXT
                elif lb == "b_retract_meter_in_threshold":
                    pr0 = retract_meter_in(lg, f0)["p_r_bar"] * BAR
                else:
                    pr0 = P_RELIEF
                return unload_to_liftoff(lg, f0, pr0)["p_r_bar"] - 350.0
            lim[leg][label] = brentq(fun, 20e3, 1.0e6) / 1e3
    out["H2_F0_for_rod_350bar_kN"] = lim
    # thermal headroom for the worst H-2 case
    # overload of a locked leg: static lock -> dynamic peak -> back
    out["H2_overload_floor"] = [overload_void("front", 116.3e3, 260.8e3, P_R0_EXT),
                                overload_void("front", 116.3e3, 265.6e3, P_R0_EXT),
                                overload_void("rear", 72.8e3, 182.8e3, P_R0_EXT),
                                overload_void("front", 116.3e3, 265.6e3,
                                              retract_meter_in("front", 116.3e3)["p_r_bar"] * BAR)]
    # lift-off after the overload (gas bound from the void) vs without
    out["H2_liftoff_after_overload"] = []
    for ov in out["H2_overload_floor"]:
        leg = ov["leg"]
        for xa in (0.0, ov["x_air_after_bound"]):
            r = unload_to_liftoff(leg, ov["F_lock_kN"] * 1e3, ov["p_r0_bar"] * BAR, xa)
            r["after_overload_to_kN"] = ov["F_peak_kN"]
            out["H2_liftoff_after_overload"].append(r)

    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "rod_side_rexome35.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    # console summary
    for leg, p in par.items():
        print(leg, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in p.items()
                    if not isinstance(v, (list, dict))})
        print("  thermal", p["thermal"])
        print("  sigmaF / Fs_max", p["sigma_F_two_sensor_kN"], p["two_sensor_static_liftoff_Fs_max_kN"])
        print("  liftoff_static", [(round(r["p_r_bar"], 1), round(r["head_only_reading_kN"], 2), r["x_air"])
                                   for r in p["liftoff_static"]])
        print("  locked_after_retract", round(p["locked_after_retract"]["p_r0_bar"], 1),
              round(p["locked_after_retract"]["head_only_bias_kN"], 2),
              round(p["locked_after_retract"]["liftoff"]["p_r_bar"], 1),
              round(p["locked_after_retract"]["liftoff"]["head_only_reading_kN"], 2))
        print("  retract airborne", [(r["F_s_kN"], r["p_bA_bar"], round(r["p_r_bar"], 1))
                                     for r in p["retract_airborne"]])
        print("  retract airborne Fs limit", p["retract_airborne_Fs_limit_kN"])
        print("  retract grounded psi3.5 pbA5", [(r["F_cyl_kN"], round(r["p_h_bar"], 1), round(r["p_r_bar"], 1),
                                                 round(r["head_only_bias_kN"], 2))
                                                for r in p["retract_grounded"] if r["psi"] == 3.5 and r["p_bA_bar"] == 5])
        print("  retract grounded range p_r", min(r["p_r_bar"] for r in p["retract_grounded"]),
              max(r["p_r_bar"] for r in p["retract_grounded"]))
        print("  sens r", [(s["L0_rod_m"], round(s["e_m"], 4), round(s["r"], 3), round(s["dp_r_bar_per_100kN"], 1))
                           for s in p["sensitivity_r"]])
    print(json.dumps(out["H1"], indent=1))
    for r in h2:
        if r["F_s_kN"] == 0:
            print(f"H2 {r['leg']} F0 {r['F0_kN']:.1f} {r['case']:30s} x_air {r['x_air']:.4f} p_r0 {r['p_r0_bar']:6.1f}"
                  f" -> p_r {r['p_r_bar']:6.1f} (p_h {r['p_h_bar']:5.1f}, out {r['piston_out_mm']:.2f} mm,"
                  f" head-only {r['head_only_reading_kN']:.1f} kN)")
    for r in h2:
        if r["F_s_kN"] > 0 and r["x_air"] == 0:
            print(f"H2 Fs3.7 {r['leg']} F0 {r['F0_kN']:.1f} {r['case']:30s} -> p_r {r['p_r_bar']:6.1f}")
    print("F0 for 350", out["H2_F0_for_rod_350bar_kN"])
    print(json.dumps(out["H2_overload_floor"], indent=1))
    for r in out["H2_liftoff_after_overload"]:
        print(f"after overload {r['leg']} lock {r['F0_kN']:.1f} p_r0 {r['p_r0_bar']:.1f} x_air {r['x_air']:.5f}"
              f" -> p_r {r['p_r_bar']:.1f}")


if __name__ == "__main__":
    main()
