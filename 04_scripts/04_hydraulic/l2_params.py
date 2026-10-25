"""Parameters of the L2 hydraulic leg model (spec 00_docs/02_hydraulic/l2_hydraulic_model_spec.md, 2 and 7).

HISTORICAL BASIS (pinned 2026-10-25, YAML regen bundle H-1 / user decision D7):
this is the "REXOME33 old-dimension L2 reference response history" path. It reads the frozen
history YAML 02_params/history/rexome33_2026-10-22_before_rexome35.yaml (read only), NOT the current
02_params/rexome33.yaml. Geometry (common bore/rod 115/110 mm, stroke 0.68 m), v_max, damping
(actuator.L2.oil_damping*), loads and F_min all come from that one file, so the L2 spec first
edition (2026-10-21) is reproduced bit for bit and old areas are no longer mixed with REXOME35
per-leg damping. The current YAML no longer carries the common cylinder keys. A per-leg REXOME35
re-run would be option (b) of D7 (re-run and re-judge the L2 spec), not done here.

Adds the hydraulic ASSUMPTIONs that the YAML does not carry. Every derived number is computed with
pint units and written to 06_analysis/03_hydraulic/l2_params.json with its source / ASSUMPTION tag.
Importers (linearize.py, run_l2_reference.py, hopsan_single_leg.py) get the same basis via build().

Run (conda hydraulics-dev):  python -I 04_scripts/04_hydraulic/l2_params.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# Pinned history YAML (D7): do not point this at the current 02_params/rexome33.yaml.
YAML_REL = "02_params/history/rexome33_2026-10-22_before_rexome35.yaml"
YAML_PATH = ROOT / YAML_REL
BASIS_NOTE = ("L2 reference basis = REXOME33 old dimensions (history, pinned 2026-10-25 D7): "
              f"{YAML_REL}; common bore/rod 115/110 mm, stroke 0.68 m; NOT the current REXOME35 per-leg YAML")
OUT_DIR = ROOT / "06_analysis" / "03_hydraulic"
sys.path.insert(0, str(HERE))

import l2_cylinder as lc  # noqa: E402

G = 9.80665


def load_yaml() -> dict:
    """Frozen history YAML (see module docstring). Every read of this L2 path goes through here."""
    with open(YAML_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def print_basis() -> None:
    print(f"[basis] {BASIS_NOTE}")


def series(*k: float) -> float:
    return 1.0 / sum(1.0 / x for x in k)


# ---------------------------------------------------------------------------------------------
# ASSUMPTIONS that are new in this spec (not in the YAML); value, sensitivity, reason
# ---------------------------------------------------------------------------------------------
ASSUMPTIONS = {
    "oil_grade": ("ISO VG 46 mineral (HM/HV)", None, "typical mobile hydraulics; manufacturer Q-H1"),
    "oil_temperature_C": (50.0, [20.0, 80.0], "operating range; beta and viscosity depend on it"),
    "oil_density_kg_m3": (860.0, [850.0, 875.0], "VG46 at 40-50 C"),
    "oil_kinematic_viscosity_mm2_s": (32.0, [15.0, 100.0], "VG46 at 50 C (46 at 40 C)"),
    "beta_liquid_lumped_Pa": (1.0e9, [0.69e9, 1.6e9],
                              "user decision 2026-10-19 (YAML actuator.oil_bulk_modulus_eff_Pa)"),
    "air_fraction_at_1bar": (0.0, [0.0, 0.005, 0.02],
                             "baseline constant beta; sensitivity for low-pressure chambers"),
    "air_polytropic_n": (1.0, [1.0, 1.4], "isothermal slow / adiabatic fast"),
    "dead_length_head_m": (0.05, [0.0, 0.15], "YAML actuator.oil_dead_length_m"),
    "dead_length_rod_m": (0.05, [0.0, 0.15],
                          "same as head (annulus port + block); dynamics_model.md 2.3 used 0.68 - e + L0"),
    "p_rod_locked_gauge_Pa": (2.0e5, [0.0, 10.0e5], "rod side trapped at tank/return back-pressure after extension"),
    "p_cav_abs_Pa": (0.0, None, "vapour pressure of mineral oil is < 1 kPa; Hopsan clamps at 0 Pa abs"),
    "valve_ramp_time_s": (0.1, [0.05, 0.3], "user brief: command ramp 0.1 s (0 -> v_max)"),
    "compensator_dp_Pa": (10.0e5, [7.0e5, 15.0e5], "section compensator margin (not needed by Level 1)"),
    "rod_line_dp_at_vmax_Pa": (5.0e5, [2.0e5, 10.0e5],
                               "rod side -> tank pressure drop at A_B v_max (meter-out edge + POC + hose)"),
    "relief_override_Pa_at_qmax": (10.0e5, [5.0e5, 20.0e5], "210 bar relief: overpressure at full section flow"),
    "relief_tau_s": (0.01, [0.005, 0.03], "relief spool time constant"),
    "poc_pilot_ratio": (3.5, [2.0, 6.0], "dual POC typical 3:1-4:1; Hopsan default 3.5"),
    "poc_crack_Pa": (3.0e5, [1.0e5, 5.0e5], "POC check spring"),
    "poc_hysteresis_Pa": (2.0e5, [0.0, 5.0e5], "pilot close/open difference"),
    "cb_setting_gauge_Pa": (350.0e5, None, "manufacturer: counterbalance limits the locked pressure to 350 bar"),
    "cb_pilot_ratio": (4.0, [3.0, 8.0], "typical counterbalance 3:1-8:1"),
    "cb_override_Pa_at_20Lmin": (20.0e5, [10.0e5, 40.0e5], "relief-function override"),
    "cb_hysteresis_Pa": (5.0e5, [0.0, 10.0e5], "Hopsan default p_h"),
    "cb_tau_s": (0.01, [0.005, 0.05], "spool time constant"),
    "cb_neutral_vents_lines": (True, None,
                               "CB circuits need A,B -> T neutral; with A,B blocked the CB relieves into a "
                               "closed hose (Q-H4)"),
    "seal_friction_Fs_N": (0.0, [0.0, 2.0e3, 5.0e3, 12.0e3], "V15 set (user decision); value unknown (Q-H5)"),
    "seal_friction_Fc_over_Fs": (1.0, [0.6, 1.0], "1.0 = V15 Coulomb mode; Stribeck option 0.7"),
    "seal_friction_v_stribeck_m_s": (0.005, [0.001, 0.02], "LuGre Stribeck velocity"),
    "seal_friction_sigma0_N_m": (1.0e10, [2.0e8, 1.0e10],
                                 "merged (L2b-NSC) form: 1e10 = near-rigid stick (V15); a separate rod body "
                                 "(L2, airborne rod) needs 2e8 with sigma1 1.3e5 N s/m (spec 3.4)"),
    "leak_internal_m3_s_Pa": (0.0, [0.0, 2.6e-16], "test limit 0.5 mL/min at 315 bar"),
    "leak_poc_seat_m3_s_Pa": (0.0, [0.0, 3.6e-16], "5 drops/min (0.05 mL) at 115 bar"),
    "hose_volume_line_A_m3": (0.0, [0.0, 3.5e-4], "3/8 in hose 5 m (length unknown, Q-H3); only joins while moving"),
    "hose_bulk_modulus_Pa": (0.6e9, [0.3e9, 1.0e9], "2-wire hose, with oil"),
    "end_stop_k_N_m": (1.0e9, None, "penalty stiffness of the stroke end stops"),
}


def build(beta: float = 1.0e9, F_s: float = 0.0, air: float = 0.0, leg: str = "FL",
          hopsan_force_convention: bool = False, with_relief: bool = True,
          with_cb: bool = False, k_series: float = math.inf, c_scale: float = 1.0,
          extra_head_volume: float = 0.0, fc_ratio: float = 1.0, sigma0: float | None = None,
          sigma1: float = 0.0, cb_q_override: float | None = None, cb_tau: float | None = None,
          cb_q_nom: float = 1.0e-3) -> tuple[lc.CylinderParams, dict]:
    """CylinderParams for one leg + scenario constants (dict, SI).

    cb_q_override: counterbalance flow at the assumed override (default 20 L/min at 20 bar);
    cb_q_nom: flow-coefficient cap of the CB law (q_nom at p_nom 70 bar; 1e-3 m^3/s = 60 L/min).
    """
    y = load_yaml()
    act = y["actuator"]
    D, d = float(act["bore_diameter_m"]), float(act["rod_diameter_m"])
    A_A = math.pi / 4 * D ** 2
    A_B = math.pi / 4 * (D ** 2 - d ** 2)
    stroke = float(act["stroke_m"])
    L0A = float(act["oil_dead_length_m"])
    L0B = ASSUMPTIONS["dead_length_rod_m"][0]
    geo = lc.Geometry(A_A, A_B, stroke, A_A * L0A, A_B * L0B)
    fluid = lc.Fluid(beta_L_Pa=beta, air_fraction=air, p_atm_Pa=1.0e5, p_cav_abs_Pa=0.0,
                     polytropic_n=ASSUMPTIONS["air_polytropic_n"][0])
    fric = lc.Friction(F_s_N=F_s, F_c_N=F_s * fc_ratio,
                       v_stribeck_m_s=ASSUMPTIONS["seal_friction_v_stribeck_m_s"][0],
                       sigma0_N_m=sigma0 or ASSUMPTIONS["seal_friction_sigma0_N_m"][0],
                       sigma1_N_s_m=sigma1)
    # damping placement: the YAML dashpot acts on the whole axial spring k_ax (dynamics_model.md 2.3,
    # zeta set on the heave mode); here it sits across the oil column only, in series with
    # k_g = rod (+) frame (+) concrete. Same modal damping needs c_h = c_ax (1 + k_oil/k_g)^2 (spec 3.5).
    cr0 = y["contact"]["rigid_floor"]
    k_g0 = series(float(cr0["L1"]["derivation"]["k_rod_N_m"]), float(act["frame_stiffness_N_m"]),
                  float(cr0["concrete"]["k_N_m"]))
    k_oil_op = beta * A_A / (L0A + float(cr0["L1"]["derivation"]["operating_extension_m"][leg]))
    placement = (1.0 + k_oil_op / k_g0) ** 2
    c_lock = float(act["L2"]["oil_damping_N_s_m"][leg]) * c_scale * placement
    c_move = float(act["L2"]["oil_damping_moving_N_s_m"][leg]) * c_scale * placement
    v_max = float(act["max_speed_m_s"])
    q_max = A_A * v_max
    # relief 210 bar: Hopsan-law parameters giving the assumed override at q_max
    p_rel = float(act["relief_pressure_moving_Pa"])
    relief = None
    if with_relief:
        dp_ov = ASSUMPTIONS["relief_override_Pa_at_qmax"][0]
        k_cf = valve_kcf(q_max, dp_ov, p_rel + dp_ov)
        relief = lc.PressureValve(p_set_gauge_Pa=p_rel, pilot_ratio=0.0, hysteresis_Pa=0.0,
                                  tau_s=ASSUMPTIONS["relief_tau_s"][0], k_cs=1.0e-6, k_cf=k_cf,
                                  q_nom_m3_s=1.0e-3, p_nom_Pa=7.0e6)
    cb = None
    if with_cb:
        p_cb = float(act["locked_pressure_limit_Pa"])
        dp_ov = ASSUMPTIONS["cb_override_Pa_at_20Lmin"][0]
        k_cf = valve_kcf(cb_q_override or 20.0e-3 / 60.0, dp_ov, p_cb + dp_ov)
        cb = lc.PressureValve(p_set_gauge_Pa=p_cb, pilot_ratio=ASSUMPTIONS["cb_pilot_ratio"][0],
                              hysteresis_Pa=ASSUMPTIONS["cb_hysteresis_Pa"][0],
                              tau_s=cb_tau or ASSUMPTIONS["cb_tau_s"][0], k_cs=1.0e-6, k_cf=k_cf,
                              q_nom_m3_s=cb_q_nom, p_nom_Pa=7.0e6)
    prm = lc.CylinderParams(
        geometry=geo, fluid=fluid, friction=fric,
        c_h_locked_N_s_m=c_lock, c_h_moving_N_s_m=c_move,
        relief=relief, counterbalance=cb, k_series_N_m=k_series,
        p_force_ref_abs_Pa=0.0 if hopsan_force_convention else None,
        end_stop_k_N_m=ASSUMPTIONS["end_stop_k_N_m"][0],
        moving_extra_volume_head_m3=extra_head_volume,
    )
    cr = y["contact"]["rigid_floor"]
    k_rod = float(cr["L1"]["derivation"]["k_rod_N_m"])
    k_frame = float(act["frame_stiffness_N_m"])
    k_conc = float(cr["concrete"]["k_N_m"])
    F0 = float(y["superstructure"]["auger_levels"]["top"]["static_leg_loads_N"][leg])
    e_op = float(cr["L1"]["derivation"]["operating_extension_m"][leg])
    m_r = float(y["legs"][leg]["moving_part"]["mass_kg"])
    dp_rod = ASSUMPTIONS["rod_line_dp_at_vmax_Pa"][0]
    consts = {
        "leg": leg, "A_A": A_A, "A_B": A_B, "stroke": stroke, "s0": e_op, "F0": F0,
        "M_eq": F0 / G, "m_r": m_r, "g": G,
        "k_rod": k_rod, "k_frame": k_frame, "k_concrete": k_conc,
        "k_g": series(k_rod, k_frame, k_conc),
        "v_max": v_max, "q_max": q_max,
        "rod_valve_Ks": A_B * v_max / math.sqrt(dp_rod),
        "p_rod0_g": ASSUMPTIONS["p_rod_locked_gauge_Pa"][0],
        "p_relief_g": p_rel, "p_locked_limit_g": float(act["locked_pressure_limit_Pa"]),
        "F_relief": p_rel * A_A, "F_locked_limit": float(act["locked_pressure_limit_Pa"]) * A_A,
        "c_h_locked": c_lock, "c_h_moving": c_move, "c_h_placement_factor": placement,
        "c_ax_yaml_locked": float(act["L2"]["oil_damping_N_s_m"][leg]),
        "F_min_cyl": float(y["control"]["F_min_cylinder_N"]),
    }
    return prm, consts


def valve_kcf(q: float, dp_over: float, dp_total: float, p_nom: float = 7.0e6, k_cs: float = 1.0e-6) -> float:
    """k_cf of the Hopsan pressure-valve law that passes q at overpressure dp_over (total drop dp_total)."""
    c_s = math.sqrt(p_nom) / k_cs
    b = dp_over * math.sqrt(dp_total) / q
    c_f = (b - c_s) / dp_total
    return 1.0 / (c_f * math.sqrt(p_nom))


def unit_table() -> dict:
    """Derived values with pint (SI internally, practical units in brackets)."""
    import pint

    ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity
    prm, c = build()
    g = prm.geometry
    A_A = Q_(c["A_A"], "m**2")
    A_B = Q_(c["A_B"], "m**2")
    beta = Q_(prm.fluid.beta_L_Pa, "Pa")
    V_A = Q_(g.dead_volume_head_m3 + c["A_A"] * c["s0"], "m**3")
    V_B = Q_(g.dead_volume_rod_m3 + c["A_B"] * (c["stroke"] - c["s0"]), "m**3")
    k_A = (beta * A_A ** 2 / V_A).to("N/m")
    k_B = (beta * A_B ** 2 / V_B).to("N/m")
    k_g = Q_(c["k_g"], "N/m")
    k_ax = 1 / (1 / k_A + 1 / k_g)
    M = Q_(c["M_eq"], "kg")
    w = (k_ax / M) ** 0.5
    q_max = Q_(c["q_max"], "m**3/s")
    rows = {
        "A_A": (A_A.to("m**2").m, "m^2", A_A.to("cm**2").m, "cm^2"),
        "A_B": (A_B.to("m**2").m, "m^2", A_B.to("cm**2").m, "cm^2"),
        "area_ratio_phi": ((A_A / A_B).to("").m, "-", None, None),
        "V_A_at_e_op": (V_A.m, "m^3", V_A.to("L").m, "L"),
        "V_B_at_e_op": (V_B.m, "m^3", V_B.to("L").m, "L"),
        "k_oil_head_e_op": (k_A.m, "N/m", k_A.to("kN/mm").m, "kN/mm"),
        "k_oil_rod_side_e_op_if_pressurised": (k_B.m, "N/m", k_B.to("kN/mm").m, "kN/mm"),
        "k_g_rod_frame_concrete": (k_g.m, "N/m", k_g.to("kN/mm").m, "kN/mm"),
        "k_axial_series": (k_ax.to("N/m").m, "N/m", k_ax.to("kN/mm").m, "kN/mm"),
        "M_eq_FL": (M.m, "kg", M.to("t").m, "t"),
        "f_heave_single_leg": ((w / (2 * math.pi)).to("1/s").m, "Hz", None, None),
        "q_max": (q_max.m, "m^3/s", q_max.to("L/min").m, "L/min"),
        "p_static_head_gauge": (c["F0"] / c["A_A"], "Pa", c["F0"] / c["A_A"] / 1e5, "bar(g)"),
        "F_relief_210bar": (c["F_relief"], "N", c["F_relief"] / 1e3, "kN"),
        "F_locked_350bar": (c["F_locked_limit"], "N", c["F_locked_limit"] / 1e3, "kN"),
        "rod_valve_Ks": (c["rod_valve_Ks"], "m^3/s/sqrt(Pa)", None, None),
    }
    # flow coefficient conversions for the rod-side path (Ks -> CdA, Kv, Cv)
    rho = ASSUMPTIONS["oil_density_kg_m3"][0]
    cda = c["rod_valve_Ks"] / math.sqrt(2.0 / rho)
    # Kv (water-equivalent, IEC 60534): Q[m^3/h] = Kv sqrt(dp[bar] / SG)  ->  Kv = Ks_oil sqrt(SG) in h/bar units
    kv = c["rod_valve_Ks"] * 3600.0 * math.sqrt(1.0e5) * math.sqrt(rho / 1000.0)
    cv = 1.156 * kv
    rows["rod_path_CdA"] = (cda, "m^2", cda * 1e6, "mm^2")
    rows["rod_path_Kv_water_equiv"] = (kv, "m^3/h/sqrt(bar)", cv, "Cv US gpm/sqrt(psi)")
    return {k: {"si": v[0], "si_unit": v[1], "practical": v[2], "practical_unit": v[3]}
            for k, v in rows.items()}


def main() -> None:
    print_basis()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prm, c = build()
    out = {
        "meta": {"script": "04_scripts/04_hydraulic/l2_params.py", "yaml": YAML_REL, "basis": BASIS_NOTE,
                 "env": "conda hydraulics-dev", "pressure_convention": "absolute inside, gauge in reports",
                 "date": "2026-10-20"},
        "scenario_constants_FL": c,
        "derived_units": unit_table(),
        "assumptions": {k: {"value": v[0], "sensitivity": v[1], "basis": v[2]} for k, v in ASSUMPTIONS.items()},
        "relief_valve_law": prm.relief.__dict__ if prm.relief else None,
        "counterbalance_law": build(with_cb=True)[0].counterbalance.__dict__,
    }
    path = OUT_DIR / "l2_params.json"
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"wrote {path}")
    for k, v in out["derived_units"].items():
        print(f"  {k:38s} {v['si']:.6g} {v['si_unit']}  ({v['practical']} {v['practical_unit']})")


if __name__ == "__main__":
    main()
