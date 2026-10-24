"""S7 checklist item: L1 (L1-R) versus L2b-NSC comparison table.

Reads only existing results (no Chrono run, no new physics):
  - reference.json (L1R_rod_side_reference_rev32, L2b_NSC_reference_rev33, slope_V12)
  - L2b Chrono judgement 06_analysis/01_chrono/17_S7/verify_S7_L2b.json (dynamics_model.md 5.22)
  - L1 Chrono judgements 11_S1 (statics), 12_S2 (V12), 14_S4 verify_L1R_V7_V5 (V7a L1-R LOCK),
    16_S6 verify_S6_L1_infra (V11b), 01_cost/step_cost_S0, 17_S7/step_cost_S7
  - L1 values that exist only as dynamics judgements in dynamics_model.md (5.12.12 supplement 8,
    5.17.5) are copied with their section as source (HARD-CODED, marked "doc").

Writes 06_analysis/01_chrono/17_S7/S7_L1_vs_L2b.json and S7_L1_vs_L2b.png.
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s7_l1_vs_l2b_table.py
Frame: world z up, gravity -z 9.80665 m/s^2; forces on the pad/rod from the floor; legs FL, FR, RL, RR.
"""

# ruff: noqa: E501  (long descriptive JSON keys)
import hashlib
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
OUT_JSON = P("06_analysis", "01_chrono", "17_S7", "S7_L1_vs_L2b.json")
OUT_PNG = P("06_analysis", "01_chrono", "17_S7", "S7_L1_vs_L2b.png")
LEVELS = ("top", "middle", "bottom")
LEGS = ("FL", "FR", "RL", "RR")


def load(*parts):
    path = P(*parts)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return data, sha


def key(d, prefix):
    """Return d[k] for the unique key k starting with prefix."""
    hits = [k for k in d if k.startswith(prefix)]
    if len(hits) != 1:
        raise KeyError(f"{prefix!r}: {hits}")
    return d[hits[0]]


def rel(a, b):
    return (np.asarray(a, float) - np.asarray(b, float)) / np.abs(np.asarray(b, float))


def r(x, n=4):
    return np.round(np.asarray(x, float), n).tolist()


ref, sha_ref = load("06_analysis", "00_dynamics", "reference.json")
v7, sha_v7 = load("06_analysis", "01_chrono", "17_S7", "verify_S7_L2b.json")
s1, sha_s1 = load("06_analysis", "01_chrono", "11_S1", "verify_S1_L1.json")
s2a, sha_s2a = load("06_analysis", "01_chrono", "12_S2", "verify_S2a_L1.json")
l1r, sha_l1r = load("06_analysis", "01_chrono", "14_S4", "verify_L1R_V7_V5.json")
s6, sha_s6 = load("06_analysis", "01_chrono", "16_S6", "verify_S6_L1_infra.json")
c0, sha_c0 = load("06_analysis", "01_chrono", "01_cost", "step_cost_S0.json")
c7, sha_c7 = load("06_analysis", "01_chrono", "17_S7", "step_cost_S7.json")

R1 = ref["L1R_rod_side_reference_rev32"]
R2 = ref["L2b_NSC_reference_rev33"]
num = v7["numbers"]
F_MIN = R2["levels"]["top"]["F_min_cylinder_N"]
GUARD = F_MIN + 5000.0
W4 = R2["levels"]["top"]["W_total_N"] / 4.0

out = {
    "meta": {
        "purpose": "chrono_build_plan.md S7 checklist 'L1 vs L2b-NSC comparison table'; dynamics_model.md 5.23",
        "script": "04_scripts/01_dynamics/s7_l1_vs_l2b_table.py",
        "no_new_simulation": True,
        "frame": "world z up, gravity -z 9.80665 m/s^2; pad/rod force from floor; legs FL, FR, RL, RR",
        "models": {
            "L1": "SMC, rigid position motor + Hooke pad (k_n = k2 head-only lumped with rod/frame/concrete) "
            "+ ground bushing (k_t, Coulomb return map, 1-step lag) + L1-R rod-side one-sided spring "
            "(lock state machine, e_op fixed); dt 2e-4 s",
            "L2b": "NSC (PSOR 50), force motor with explicit axial law k2(s)/k1(s_lock) + rod-side state machine, "
            "explicit 2-axis lateral spring k_t barrel-rod (horizontal), rigid NSC contact (stick native); dt 1e-4 s",
        },
        "F_min_N": F_MIN,
        "guard_F_min_plus_5kN_N": GUARD,
        "W_over_4_N": W4,
        "inputs_sha256": {
            "reference.json": sha_ref,
            "verify_S7_L2b.json": sha_v7,
            "verify_S1_L1.json": sha_s1,
            "verify_S2a_L1.json": sha_s2a,
            "verify_L1R_V7_V5.json": sha_l1r,
            "verify_S6_L1_infra.json": sha_s6,
            "step_cost_S0.json": sha_c0,
            "step_cost_S7.json": sha_c7,
        },
        "doc_values": "values tagged 'doc' are copied from dynamics_model.md judgements (sections named in 'source')",
    }
}

# ---------------------------------------------------------------- A. statics (V1-V3), three auger levels
A = {}
for lv in LEVELS:
    ref_c = R2["levels"][lv]["contact_force_N (V1)"]
    ref_cyl = R2["levels"][lv]["cylinder_force_N"]
    sw = s1["cases"][lv]["still_window"]
    st = num[f"settle_{lv}"]
    A[lv] = {
        "reference_contact_N (L1 = L2b, same rigid-body statics)": r(ref_c, 1),
        "reference_cylinder_N": r(ref_cyl, 1),
        "L1_chrono_contact_N": r(sw["contact_force_mean_N"], 1),
        "L2b_chrono_contact_N (0.1 s window)": r(st["pad_normal_mean_N"], 1),
        "L1_chrono_cylinder_N": r(sw["cylinder_force_mean_N"], 1),
        "L2b_chrono_cylinder_N": r(st["cylinder_force_mean_N"], 1),
        "L2b_minus_L1_cylinder_N": r(
            np.subtract(st["cylinder_force_mean_N"], sw["cylinder_force_mean_N"]), 1
        ),
        "L1_attitude_deg (roll, pitch)": r([sw["roll_mean_deg"], sw["pitch_mean_deg"]], 6),
        "L2b_attitude_deg (roll, pitch)": r(st["roll_pitch_mean_deg"], 6),
        "L1_cylinder_window_span_N": r(sw["contact_force_span_N"], 1),
        "L2b_cylinder_step_std_N": r(st["cylinder_force_step_std_N"], 1),
        "L2b_contact_step_std_N": r(st["pad_normal_step_std_N"], 0),
    }
out["A_statics_V1_V3"] = A

# ---------------------------------------------------------------- B. modes 1-6 (LOCK)
B = {}
for lv in LEVELS:
    r1 = R1["modes_V7a"][lv]["LOCK"]
    r2 = R2["levels"][lv]["modes"]["LOCK"]
    jm = l1r["records"]["V7a"][lv]["judged_modes"]
    c2 = v7["modal"][f"V7_{lv}"]["judged"]
    f1c = [m["f_Hz"] for m in jm]
    z1c = [m["zeta"] for m in jm]
    f2c = [m["f_Hz"] for m in c2]
    z2c = [m["zeta"] for m in c2]
    f1r = key(r1, "f_damped_Hz")
    f2r = key(r2, "f_damped_Hz")
    B[lv] = {
        "L1R_ref_f_damped_Hz": f1r,
        "L1R_ref_zeta": r1["zeta"],
        "L2b_ref_f_damped_Hz": f2r,
        "L2b_ref_zeta": key(r2, "zeta"),
        "L1_chrono_f_Hz (V7a, L1-R LOCK)": r(f1c, 4),
        "L1_chrono_zeta (minus r omega dt/2)": r(z1c, 5),
        "L2b_chrono_f_Hz": r(f2c, 4),
        "L2b_chrono_zeta (no correction)": r(z2c, 5),
        "L2b_over_L1_ref_f_minus_1": r(rel(f2r, f1r), 4),
        "L2b_over_L1_chrono_f_minus_1": r(rel(f2c, f1c), 4),
        "L2b_over_L1_chrono_zeta_minus_1": r(rel(z2c, z1c), 3),
    }
out["B_modes_LOCK"] = B

# ---------------------------------------------------------------- C. V4 touch-down
V4n = R2["V4_NSC"]
C = {
    "L2b_ref_dynamic_touch_s (rigid crawler limit)": key(V4n["L2b_dynamic"], "touch_s"),
    "L1_ref_rigid_crawler_touch_s (= lift_V4 D rigid dynamic_events_s)": key(
        V4n, "L1_basis_replica_touch_s"
    ),
    "L2b_minus_L1_ref_s (rigid crawler)": key(V4n, "L2b_minus_L1_basis_s"),
    "L2b_chrono_touch_s": r(num["V4"]["touch_eq_s"], 4),
    "L2b_chrono_minus_ref_s": r(
        np.subtract(num["V4"]["touch_eq_s"], key(V4n["L2b_dynamic"], "touch_s")), 4
    ),
    "L2b_crawler": "rigid NSC spheres (no crawler compliance)",
    "L1_chrono_touch_s (crawler x1 compliant, D, doc)": [16.287, 16.287, 16.441, 16.441],
    "L1_ref_touch_s (crawler x1 compliant, doc)": [16.295, 16.294, 16.432, 16.432],
    "L1_chrono_touch_s (crawler x3, doc)": [16.525, 16.525, 16.418, 16.418],
    "source_L1": "dynamics_model.md 5.12.12 supplement 8 (S3 v4_D batches 20261022_052232 / 053640)",
    "first_touch": {
        "L1 crawler x1": "front pair",
        "L1 crawler x3": "rear pair",
        "rigid crawler (L1 ref, L2b)": "rear pair",
    },
    "note": "order depends on crawler stiffness (CLAUDE.md: V4 judged per leg vs same-layout reference, not by order)",
}
out["C_V4_touch"] = C

# ---------------------------------------------------------------- D. single-leg sensitivity, F_min, lift-off (V5, V6, V14)
qs = R1["V5_V6_quasi_static"]["top"]
qs_l1r = key(qs, "L1R")
qs_ho = key(qs, "head_only")
thr = key(R2["levels"]["top"], "single_leg_thresholds_mm")
D = {
    "V5_FL+1mm_dF_N": {
        "L1R_ref_quasi_static": qs_l1r["FL +1 mm"]["dF_N"],
        "L1R_dynamic_replica (doc 5.17.5)": [5887.8, -5913.0, -6582.9, 6608.1],
        "head_only_ref": qs_ho["FL +1 mm"]["dF_N"],
        "L1_chrono (L1-R, module normal force, doc 5.17.5)": [5877.5, -5917.0, -6581.0, 6598.6],
        "L2b_chrono (law output)": r(num["V5_FL_p1mm"]["dF_N"], 1),
    },
    "V6": {},
    "V14_RL+": {},
}
D["V5_FL+1mm_dF_N"]["L2b_minus_L1_chrono_rel"] = r(
    rel(
        D["V5_FL+1mm_dF_N"]["L2b_chrono (law output)"],
        D["V5_FL+1mm_dF_N"]["L1_chrono (L1-R, module normal force, doc 5.17.5)"],
    ),
    4,
)
v6_l1_chrono = {"FL+": (9.900, 11.51), "FL-": (10.07, 11.76)}  # doc 5.17.5 (S3 L1-R, converted)
v6_l2b_chrono = {"FL+": "V6_FLp", "RL+": "V6_RLp", "RL-": "V6_RLm"}
for case in ("FL+", "FL-", "RL+", "RL-"):
    t = thr.get(case)
    row = {}
    if t is not None:
        row["head_only_ref_mm (F_min, lift)"] = [
            t["head_only"]["F_min_mm"]["value"],
            t["head_only"]["liftoff_mm"]["value"],
        ]
        row["L1R_ref_mm (F_min, lift)"] = [
            t["L1R_after_extend"]["F_min_mm"]["value"],
            t["L1R_after_extend"]["liftoff_mm"]["value"],
        ]
        row["leg"] = t["L1R_after_extend"]["F_min_mm"]["leg"]
    if case in v6_l1_chrono:
        row["L1_chrono_mm (doc 5.17.5)"] = list(v6_l1_chrono[case])
    if case in v6_l2b_chrono:
        n = num[v6_l2b_chrono[case]]
        row["L2b_chrono_mm"] = r([n["f_min_mm"], n["liftoff_mm"]], 3)
    if "L1_chrono_mm (doc 5.17.5)" in row and "L2b_chrono_mm" in row:
        row["L2b_minus_L1_chrono_mm"] = r(
            np.subtract(row["L2b_chrono_mm"], row["L1_chrono_mm (doc 5.17.5)"]), 3
        )
    if "L1R_ref_mm (F_min, lift)" in row and "L2b_chrono_mm" in row:
        row["L2b_chrono_vs_L1R_ref_rel"] = r(
            rel(row["L2b_chrono_mm"], row["L1R_ref_mm (F_min, lift)"]), 4
        )
    D["V6"][case] = row

v14map = {
    "level": "V14_flat_RL",
    "max pitch+": "V14_pitchp_RL",
    "max roll+": "V14_rollp_RL",
    "max diag 45": "V14_diag_RL",
}
ctrl_rows = []
for case, nk in v14map.items():
    c = R2["V14"]["cases"][case]
    rl = c["RL+"]
    l1 = rl["L1R_after_extend"]
    ho = rl["head_only"]
    n = num[nk]
    fmin_ref = l1["F_min_threshold_mm"]["value"]
    lift_ref = l1["liftoff_threshold_mm"]["value"]
    fmin_c = n["thresholds"]["f_min_mm"]
    lift_c = n["thresholds"]["liftoff_mm"]
    sec_ref = key(l1, "dF_cyl_secant_+1mm_N")[2]
    sec_c = n["secant_N"][2]
    # Force-equivalent of the threshold shift at the F_min leg (RR): RR force falls from its settled
    # value to F_min over the threshold travel; mean slope x shift.
    j = LEGS.index(l1["F_min_threshold_mm"]["leg"])
    F0 = key(c, "F_cyl_place_and_settle_N")[j] if "F_cyl_place_and_settle_N" in c else None
    if F0 is None:  # level case: use statics
        F0 = R2["levels"]["top"]["cylinder_force_N"][j]
    slope = (F0 - F_MIN) / fmin_ref  # N/mm, mean over the travel (L1-R reference)
    dF_eq = slope * (fmin_c - fmin_ref)
    row = {
        "ground_roll_pitch_deg": c.get("ground_roll_pitch_deg", [0.0, 0.0]),
        "head_only_ref (secant RL N, F_min mm, lift mm)": [
            key(ho, "dF_cyl_secant_+1mm_N")[2],
            ho["F_min_threshold_mm"]["value"],
            ho["liftoff_threshold_mm"]["value"],
        ],
        "L1R_ref (secant RL N, F_min mm, lift mm)": [sec_ref, fmin_ref, lift_ref],
        "L2b_chrono (secant RL N, F_min mm, lift mm)": r([sec_c, fmin_c, lift_c], 3),
        "L2b_chrono_vs_L1R_ref_rel": r(
            rel([sec_c, fmin_c, lift_c], [sec_ref, fmin_ref, lift_ref]), 4
        ),
        "L1R_vs_head_only_rel (F_min)": round(
            fmin_ref / ho["F_min_threshold_mm"]["value"] - 1.0, 4
        ),
        "F_min_leg": l1["F_min_threshold_mm"]["leg"],
        "F_min_leg_settled_cylinder_N": round(F0, 1),
        "mean_force_slope_N_per_mm (L1R ref)": round(slope, 1),
        "force_equivalent_of_threshold_shift_N": round(dF_eq, 1),
        "share_of_5kN_guard_margin": round(dF_eq / 5000.0, 3),
        "L1_chrono": "not run (V14 is an S7 case; L1 basis = L1-R reference, same constitutive law as L1 Chrono S3/S6)",
    }
    D["V14_RL+"][case] = row
    ctrl_rows.append((case, fmin_ref, fmin_c, dF_eq))
out["D_V5_V6_V14"] = D

# ---------------------------------------------------------------- E. V12 slope statics
E = {}
v12map = {
    "ground roll 0 deg, pitch 2 deg": ("v12_pitch2", "V12_0"),
    "ground roll 2 deg, pitch 0 deg": ("v12_roll2", "V12_1"),
    "ground roll -2 deg, pitch 1.5 deg": ("v12_rollm2_pitch1.5", "V12_2"),
}
for case, (k1, k2) in v12map.items():
    sv = ref["slope_V12"][case]
    w1 = np.asarray(s2a["v12"][k1]["window"]["reaction_world_mean_N"], float)
    w2 = np.asarray(num[k2]["mean_last_s"]["pad_contact_world_N"], float)
    E[case] = {
        "L1_ref_vertical_N": sv["L1"]["contact_vertical_N"],
        "L2b_ref_vertical_N (Chrono topology, rev 35)": sv["L2b_NSC"]["contact_vertical_N"],
        "L1_chrono_vertical_N": r(w1[:, 2], 1),
        "L2b_chrono_vertical_N": r(w2[:, 2], 1),
        "L2b_minus_L1_chrono_vertical_N": r(w2[:, 2] - w1[:, 2], 1),
        "L2b_minus_L1_ref_vertical_N": r(
            np.subtract(sv["L2b_NSC"]["contact_vertical_N"], sv["L1"]["contact_vertical_N"]), 1
        ),
        "L1_chrono_horizontal_xy_N": r(w1[:, :2], 1),
        "L2b_chrono_horizontal_xy_N": r(w2[:, :2], 1),
        "L1_ref_horizontal_xy_N": sv["L1"]["contact_horizontal_xy_N"],
        "L2b_ref_horizontal_xy_N": sv["L2b_NSC"]["contact_horizontal_xy_N"],
        "L1_floor_plane_tangential_N (bushing load, not rod bending)": r(
            s2a["v12"][k1]["window"]["tangential_mean_N"], 1
        ),
        "L2b_lateral_spring_force_N (barrel-rod, rod bending)": r(
            num[k2]["mean_last_s"]["lateral_force_N"], 1
        ),
    }
    # Twist-mode share of the reference-model difference (n from CLAUDE.md C2, |n| = 1).
    dref = np.subtract(sv["L2b_NSC"]["contact_vertical_N"], sv["L1"]["contact_vertical_N"])
    n_tw = np.array([0.476, -0.476, -0.523, 0.523])
    n_tw = n_tw / np.linalg.norm(n_tw)
    t = float(n_tw @ dref)
    E[case]["ref_difference_twist_component_N (n^T dF, n unit)"] = round(t, 1)
    E[case]["ref_difference_non_twist_residual_N"] = r(dref - t * n_tw, 1)
    E[case]["ref_difference_twist_share_of_norm"] = round(abs(t) / float(np.linalg.norm(dref)), 3)
    # Split of the reference cylinder-force difference (L2b_NSC - L1) with the existing keys
    # 'cylinder_force_if_no_horizontal_reaction_N' of each model:
    #   axial-stiffness part   = noH(L2b) - noH(L1)          (k(e_i) per leg vs fixed k at e_op)
    #   horizontal-path part   = [L2b - noH(L2b)] - [L1 - noH(L1)]  (k_t topology, N sin(alpha) path)
    cyl1 = np.asarray(sv["L1"]["cylinder_force_N"], float)
    cyl2 = np.asarray(sv["L2b_NSC"]["cylinder_force_N"], float)
    nh1 = np.asarray(sv["L1"]["cylinder_force_if_no_horizontal_reaction_N"], float)
    nh2 = np.asarray(sv["L2b_NSC"]["cylinder_force_if_no_horizontal_reaction_N"], float)
    E[case]["ref_cyl_diff_L2b_minus_L1_N"] = r(cyl2 - cyl1, 1)
    E[case]["ref_cyl_diff_axial_k_of_e_part_N"] = r(nh2 - nh1, 1)
    E[case]["ref_cyl_diff_horizontal_path_part_N"] = r((cyl2 - nh2) - (cyl1 - nh1), 1)
    E[case]["ref_cyl_diff_axial_part_twist_N (n^T, n unit)"] = round(float(n_tw @ (nh2 - nh1)), 1)
    E[case]["ref_cyl_diff_horizontal_part_twist_N (n^T, n unit)"] = round(
        float(n_tw @ ((cyl2 - nh2) - (cyl1 - nh1))), 1
    )
    E[case]["extension_m"] = sv["extension_m"]
out["E_V12_slope"] = E

# ---------------------------------------------------------------- F. V11b saturation
F = {"L1": {}, "L2b": {}}
for name, case in s6["v11b"].items():
    ph = [p for p in case["analysis"]["phases"] if p.get("saturated")]
    F["L1"][name] = {
        "dt_s": case["model"]["dt_s"],
        "per_phase (direction, F_first_sat N, peak/limit, creep_from_first mm, settled_mean/limit)": [
            [
                p["direction"],
                round(p["force_at_first_saturation_N"], 1),
                round(p["force_peak_over_limit"], 5),
                round(p["creep_from_first_m"] * 1e3, 4),
                round(p["settled_mean_force_over_limit"], 6),
            ]
            for p in ph
        ],
        "reading_inertia_max_N": round(case["analysis"]["reading_inertia_max_N"], 1),
        "creep_c_v_over_k_mm": round(case["analysis"]["creep_reference_c_v_over_k_m"] * 1e3, 4),
    }
lim = {"FL_ext": 278738.0, "FL_ret": 79168.1, "RL_ext": 199570.0, "RL_ret": 65973.4}
for k, L in lim.items():
    n = num[f"V11b_{k}"]
    F["L2b"][k] = {
        "F_first_sat_N": round(n["f_sat_N"], 1),
        "peak_over_limit": round(abs(n["f_max_abs_after_N"]) / L, 5),
        "s_ref_creep_after_mm": round(n["s_ref_travel_after_m"] * 1e3, 4),
        "settled_over_limit": round(abs(n["f_settled_N"]) / L, 5),
    }
F["L2b_creep_prediction_mm (c_mov v_max / k2(e_op))"] = {
    "front": round(100206.0 * 0.0209243 / 2.59057e7 * 1e3, 4),
    "rear": round(86949.0 * 0.0209243 / 1.95046e7 * 1e3, 4),
}
F["physical_relief_piston_creep_mm (s6_check_rexome35 C, record)"] = 0.00184
F["note"] = (
    "both models settle on the 210 bar limit (law C re-arms); creep = damping-force loss / k "
    "(L1 c_n LOCK 34.4 kN s/m, L2b c_mov 100.2 kN s/m); L1 reading has the rigid-motor inertia pulse "
    "m_rod v / t_sat, L2b law output has none"
)
out["F_V11b_saturation"] = F

# ---------------------------------------------------------------- G. cost
hop = [x for x in c0["hook_optimization"]["runs"] if x["variant"] == "after"]
l1_us = float(np.median([x["plain_wall_us_per_step"] for x in hop]))
l2b_us = float(np.median([x["us_per_step"] for x in c7["rows"]]))
G = {
    "L1_pads_us_per_step (dt 1e-4, hook-optimised S0, before L1-R, P-core, alone)": round(l1_us, 1),
    "L1_crawler_us_per_step (S0)": round(
        c0["cases"][1]["plain_wall_us_per_step"] if isinstance(c0["cases"], list) else 71.0, 1
    ),
    "L2b_us_per_step (step_cost_S7, P-core, alone, incl. law + bushing + rod-side)": round(
        l2b_us, 1
    ),
    "L2b_us_per_step_with_capture": round(
        float(np.median([x["us_per_step_with_capture"] for x in c7["rows"]])), 1
    ),
    "recommended_dt_s": {"L1": 2e-4, "L2b": 1e-4, "reference/transition": 1e-5},
    "wall_s_per_sim_s (general dt)": {
        "L1": round(l1_us * 1e-6 / 2e-4, 3),
        "L2b": round(l2b_us * 1e-6 / 1e-4, 3),
    },
    "wall_s_per_sim_s (1e-5 s)": {
        "L1": round(l1_us * 1e-6 / 1e-5, 2),
        "L2b": round(l2b_us * 1e-6 / 1e-5, 2),
    },
    "L2b_over_L1_general": round((l2b_us / 1e-4) / (l1_us / 2e-4), 2),
    "L2b_batch_check (V14_flat_RL, 4 workers)": "264.2 s / 1,061,290 steps = 249 us/step",
    "note": "L1-R hook cost not measured separately (assumed small vs bushing hook); step cost nearly dt-independent (S0 ratio 1.03)",
}
out["G_cost"] = G

# ---------------------------------------------------------------- H. control impact summary
H = {
    "V14_threshold_shift_force_equivalent_N": {c: round(d, 1) for c, _, _, d in ctrl_rows},
    "max_share_of_5kN_margin": round(max(abs(d) for *_, d in ctrl_rows) / 5000.0, 3),
    "sign": "L2b reaches F_min later (less sensitive) than L1-R reference -> L1-R/L1 conservative",
    "V12_vertical_L2b_minus_L1_chrono_max_abs_N": round(
        max(max(abs(x) for x in e["L2b_minus_L1_chrono_vertical_N"]) for e in E.values()), 1
    ),
    "flat_static_L2b_minus_L1_cylinder_max_abs_N": round(
        max(max(abs(x) for x in a["L2b_minus_L1_cylinder_N"]) for a in A.values()), 1
    ),
    "V12_ref_axial_k_of_e_part_max_abs_per_leg_N": round(
        max(max(abs(x) for x in e["ref_cyl_diff_axial_k_of_e_part_N"]) for e in E.values()), 1
    ),
    "V12_ref_horizontal_path_part_max_abs_per_leg_N": round(
        max(max(abs(x) for x in e["ref_cyl_diff_horizontal_path_part_N"]) for e in E.values()), 1
    ),
    "V12_note": (
        "the axial part is pure twist (n^T share ~1.0) = per-leg k(e_i) (L2b) vs fixed k(e_op) (L1 Chrono law); "
        "C2 twist loop (n^T P -> 0, pressure feedback) sets this component in closed loop; "
        "locked-state load paths (D2, H4 P_stop, probe S_ii) keep it"
    ),
    "L1_fixed_k_vs_k_of_e_at_stroke_end": {
        "front k2(0.6948)/k2(e_op)": round(1.647 / 2.591, 3),
        "rear k2(0.6948)/k2(e_op)": round(1.201 / 1.950, 3),
        "front k2(touch)/k2(e_op)": round(2.871 / 2.591, 3),
        "rear k2(touch)/k2(e_op)": round(2.174 / 1.950, 3),
        "source": "reference.json L2b_NSC_reference_rev33 leg_parameters k_of_s_table (dynamics_model.md 5.20.3)",
    },
    "D2_static_roll_4p4_first_event_kN (doc 5.21.2)": {
        "L1-R fixed k": [574.0, 574.0],
        "L2b k(e_i)": [418.4, 412.3],
        "note": "roll +4.4 / -4.4; L1-R non-conservative by -28 %",
    },
}
out["H_control_impact"] = H

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- figure
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
m = np.arange(1, 7)
for lv, mk in zip(LEVELS, ("o", "s", "^"), strict=True):
    ax[0].plot(
        m, 100 * np.asarray(B[lv]["L2b_over_L1_chrono_f_minus_1"]), mk + "-", label=f"{lv} Chrono"
    )
    ax[0].plot(
        m,
        100 * np.asarray(B[lv]["L2b_over_L1_ref_f_minus_1"]),
        mk + ":",
        color="grey",
        label=f"{lv} reference",
    )
ax[0].axhspan(-3, 3, color="0.92", zorder=0)
ax[0].set_xlabel("mode (LOCK)")
ax[0].set_ylabel("f(L2b) / f(L1-R) - 1 [%]")
ax[0].set_title("Modes 1-6: L2b vs L1-R")
ax[0].legend(fontsize=7, ncol=2)
cases = list(v14map)
x = np.arange(len(cases))
ho = [D["V14_RL+"][c]["head_only_ref (secant RL N, F_min mm, lift mm)"][1] for c in cases]
l1 = [D["V14_RL+"][c]["L1R_ref (secant RL N, F_min mm, lift mm)"][1] for c in cases]
l2 = [D["V14_RL+"][c]["L2b_chrono (secant RL N, F_min mm, lift mm)"][1] for c in cases]
ax[1].bar(x - 0.27, ho, 0.27, label="head only (no rod side)", color="0.75")
ax[1].bar(x, l1, 0.27, label="L1-R reference (k(e_i) per leg)")
ax[1].bar(x + 0.27, l2, 0.27, label="L2b Chrono")
ax[1].set_xticks(x, ["flat", "pitch+4.06", "roll+6.23", "diag 3.48"])
ax[1].set_ylabel("RL+ travel to F_min at RR [mm]")
ax[1].set_title("V14 F_min threshold")
ax[1].legend(fontsize=7)
eq = [D["V14_RL+"][c]["force_equivalent_of_threshold_shift_N"] / 1e3 for c in cases]
ax[2].bar(x, eq, 0.5, color="C1")
ax[2].axhline(5.0, color="k", lw=0.8, ls="--")
ax[2].text(-0.3, 4.7, "guard margin F_min + 5 kN", fontsize=8, va="top")
ax[2].set_xticks(x, ["flat", "pitch+4.06", "roll+6.23", "diag 3.48"])
ax[2].set_ylabel("force equivalent of L2b - L1-R threshold shift [kN]")
ax[2].set_title("Model difference vs 5 kN guard margin")
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=130)

print(json.dumps(H, indent=1))
print(json.dumps(G, indent=1))
for lv in LEVELS:
    print(
        lv,
        B[lv]["L2b_over_L1_chrono_f_minus_1"],
        B[lv]["L2b_over_L1_chrono_zeta_minus_1"],
        B[lv]["L2b_over_L1_ref_f_minus_1"],
    )
for lv in LEVELS:
    print(
        lv,
        A[lv]["L2b_minus_L1_cylinder_N"],
        A[lv]["L1_attitude_deg (roll, pitch)"],
        A[lv]["L2b_attitude_deg (roll, pitch)"],
    )
for c, e in E.items():
    print(
        c,
        e["L2b_minus_L1_chrono_vertical_N"],
        e["L2b_minus_L1_ref_vertical_N"],
        e["L1_chrono_horizontal_xy_N"],
        e["L2b_chrono_horizontal_xy_N"],
    )
    print(
        "   split",
        e["extension_m"],
        e["ref_cyl_diff_L2b_minus_L1_N"],
        e["ref_cyl_diff_axial_k_of_e_part_N"],
        e["ref_cyl_diff_horizontal_path_part_N"],
        e["ref_cyl_diff_axial_part_twist_N (n^T, n unit)"],
        e["ref_cyl_diff_horizontal_part_twist_N (n^T, n unit)"],
    )
    print(
        "   twist",
        e["ref_difference_twist_component_N (n^T dF, n unit)"],
        e["ref_difference_twist_share_of_norm"],
        e["ref_difference_non_twist_residual_N"],
        e["L1_floor_plane_tangential_N (bushing load, not rod bending)"],
        e["L2b_lateral_spring_force_N (barrel-rod, rod bending)"],
    )
print(json.dumps(D["V6"], indent=0))
for c, d in D["V14_RL+"].items():
    print(
        c,
        d["L1R_ref (secant RL N, F_min mm, lift mm)"],
        d["L2b_chrono (secant RL N, F_min mm, lift mm)"],
        d["L2b_chrono_vs_L1R_ref_rel"],
        d["F_min_leg_settled_cylinder_N"],
        d["force_equivalent_of_threshold_shift_N"],
    )
print(json.dumps(F, indent=0))
print(D["V5_FL+1mm_dF_N"]["L2b_minus_L1_chrono_rel"])
