"""Pad-area variant check (cad 330 all legs vs drawing rear 250): reduced models only, no Chrono.

00_docs/01_dynamics/dynamics_model.md 5.30 (rev. 44). Output 06_analysis/00_dynamics/pad_variant_check.json.
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_pad_variant_check.py   (~3 s)

Variants
  A  = all four pads CAD REXOME33 octagon 330 x 330, chamfer 30 (0.1071 m^2)
  B  = front 330 (CAD = drawing), rear REXOME35 drawing 250 x 250, chamfer 30 (ASSUMPTION) (0.0607 m^2)
Units SI, body frame x fwd, y left, z up, pitch > 0 = nose down, g = 9.80665 m/s^2 along -z.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

OUT = ROOT / "06_analysis" / "00_dynamics" / "pad_variant_check.json"
p = dm.load_params()
geo = dm.geometry_from_params(p)
g = geo.g
L1 = p["contact"]["rigid_floor"]["L1"]
der = L1["derivation"]
LEGS = dm.LEG_NAMES


def octagon(side, ch):
    area = side**2 - 2 * ch**2
    perim = 4 * (side - 2 * ch) + 4 * ch * math.sqrt(2)
    return {"side_m": side, "chamfer_m": ch, "area_m2": area, "perimeter_m": perim,
            "b_scm_m": 2 * area / perim, "a_eq_m": math.sqrt(area / math.pi), "B_sq_m": math.sqrt(area)}


PAD = {"330": octagon(0.330, 0.030), "250": octagon(0.250, 0.030), "250c25": octagon(0.250, 0.025)}
VARIANTS = {"A": ["330", "330", "330", "330"], "B": ["330", "330", "250", "250"]}
res = {"pad_geometry": PAD}

# ---------------- 1. Westergaard interior load with finite contact radius -----------------
E, nu, h, ks = (dm.ASSUMPTIONS[k] for k in ("concrete_E_Pa", "concrete_nu", "slab_thickness_m", "subgrade_modulus_N_m3"))
D = E * h**3 / (12 * (1 - nu**2))
l = (D / ks) ** 0.25
k0 = 8 * ks * l**2
EULER = 0.5772156649


def k_wg(a):
    """Westergaard interior deflection with circular load radius a (1926, small-a expansion)."""
    corr = 1 + (1 / (2 * math.pi)) * (math.log(a / (2 * l)) + EULER - 1.25) * (a / l) ** 2
    return k0 / corr


wg = {"D_Nm": D, "l_m": l, "k_slab_point_N_m": k0, "yaml_k_N_m": p["contact"]["rigid_floor"]["concrete"]["k_N_m"]}
for key, pg in PAD.items():
    wg[key] = {"k_finite_N_m": k_wg(pg["a_eq_m"]), "rel_to_point": k_wg(pg["a_eq_m"]) / k0 - 1,
               "k_halfspace_N_m": 2 * pg["a_eq_m"] * E / (1 - nu**2)}
res["westergaard"] = wg

# ---------------- 2. series stiffness per leg -------------------------------------------
k_ax = np.array([der["k_axial_leg_N_m"][n] for n in LEGS])
k_oil = np.array([der["k_oil_N_m"][n] for n in LEGS])
k_rs = np.array([der["k_rod_side_N_m"][n] for n in LEGS])
k_rod = np.array([der["k_rod_N_m"][n] for n in LEGS])
k_fr = dm.ASSUMPTIONS["frame_bracket_stiffness_N_m"]
kn_yaml = np.array([L1["kn_per_pad_N_m"][n] for n in LEGS])
klock_yaml = np.array([der["k_lock_N_m"][n] for n in LEGS])
kt_yaml = np.array([L1["kt_per_pad_N_m"][n] for n in LEGS])
kh_sw = np.array([der["k_lateral_leg_swivel_N_m"][n] for n in LEGS])
chk = {"kn_rebuild_rel": float(np.max(np.abs(dm.series(k_ax, k0) / kn_yaml - 1))),
       "klock_rebuild_rel": float(np.max(np.abs(dm.series(k_oil + k_rs, k_rod, k_fr, k0) / klock_yaml - 1)))}


def stiff(kc):
    return {"kn": dm.series(k_ax, kc), "klock": dm.series(k_oil + k_rs, k_rod, k_fr, kc), "kt": dm.series(kh_sw, kc)}


base = stiff(np.full(4, k0))
var_k = {}
for v, types in VARIANTS.items():
    kc = np.array([k_wg(PAD[t]["a_eq_m"]) for t in types])
    s = stiff(kc)
    var_k[v] = s
    res.setdefault("stiffness", {})[v] = {
        "kc_N_m": kc.tolist(),
        **{f"{q}_rel_to_yaml": (s[q] / base[q] - 1).tolist() for q in s}}
res["stiffness"]["B_vs_A_rel"] = {q: (var_k["B"][q] / var_k["A"][q] - 1).tolist() for q in base}
res["stiffness"]["rebuild_check"] = chk

# ---------------- 3. statics, load sensitivity, F_min margin, modes ------------------------
e_op = np.array([der["operating_extension_m"][n] for n in LEGS])
F_min = p["control"]["F_min_cylinder_N"]
rod_w = geo.rod_mass * g
DM_REAR_A = 0.0464 * 0.025 * 7850.0  # ASSUMPTION: plate area difference x 25 mm x 7850, ribs not scaled


def body_variant(level, extra_rear_mass):
    g2 = dm.geometry_from_params(p)
    if extra_rear_mass:
        for i in (2, 3):
            m0 = g2.rod_mass[i]
            cpad = np.array([g2.pad_xy[i][0], g2.pad_xy[i][1], g2.pad_z_retracted[i] + 0.0125])
            g2.rod_com_retracted[i] = (m0 * g2.rod_com_retracted[i] + extra_rear_mass * cpad) / (m0 + extra_rear_mass)
            g2.rod_mass[i] = m0 + extra_rear_mass
    return g2, dm.body_with_rods(p, g2, level, e_op)


def analyse(k_v, k_h, extra_rear_mass, level="top"):
    g2, b = body_variant(level, extra_rear_mass)
    W = b.mass * g
    F, q, act = dm.static_loads(k_v, g2.pad_xy, W, b.com[:2])
    S = dm.load_sensitivity(k_v, g2.pad_xy)
    F_cyl = F - g2.rod_mass * g
    mm_to_Fmin = (F_cyl - F_min) / np.abs(np.diag(S)) * 1e3  # single-leg retract error [mm]
    pts = np.column_stack([g2.pad_xy, g2.pad_z_retracted - e_op + 0.06])  # ball centres
    K = dm.stiffness_6dof(b, pts, k_v, k_h, F)
    M = dm.mass_6dof(b)
    w2, f, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
    return {"F_contact_N": F.tolist(), "F_cyl_N": F_cyl.tolist(), "sum_F_N": float(F.sum()), "W_N": W,
            "dF_ddelta_diag_N_per_mm": (np.diag(S) / 1e3).tolist(), "mm_to_Fmin_single_leg": mm_to_Fmin.tolist(),
            "f_Hz": f.tolist(), "mode_class": cls, "orth": orth, "mass_kg": b.mass}


stat = {}
stat["yaml"] = analyse(kn_yaml, kt_yaml, 0.0)
stat["yaml_lock"] = analyse(klock_yaml, kt_yaml, 0.0)
stat["A_kc_only"] = analyse(var_k["A"]["kn"], var_k["A"]["kt"], 0.0)
stat["A_kc_mass"] = analyse(var_k["A"]["kn"], var_k["A"]["kt"], DM_REAR_A)
stat["B_kc"] = analyse(var_k["B"]["kn"], var_k["B"]["kt"], 0.0)
for lvl in ("middle", "bottom"):
    stat[f"yaml_{lvl}"] = analyse(kn_yaml, kt_yaml, 0.0, lvl)
    stat[f"A_kc_mass_{lvl}"] = analyse(var_k["A"]["kn"], var_k["A"]["kt"], DM_REAR_A, lvl)
    stat[f"B_kc_{lvl}"] = analyse(var_k["B"]["kn"], var_k["B"]["kt"], 0.0, lvl)
res["statics_modes"] = stat


def diff(a, b, key):
    return (np.array(stat[a][key]) - np.array(stat[b][key])).tolist()


res["diff"] = {
    "A_minus_B_F_contact_N_top": diff("A_kc_mass", "B_kc", "F_contact_N"),
    "A_minus_B_F_cyl_N_top": diff("A_kc_mass", "B_kc", "F_cyl_N"),
    "A_over_B_f_rel_top": (np.array(stat["A_kc_mass"]["f_Hz"]) / np.array(stat["B_kc"]["f_Hz"]) - 1).tolist(),
    "B_over_yaml_f_rel_top": (np.array(stat["B_kc"]["f_Hz"]) / np.array(stat["yaml"]["f_Hz"]) - 1).tolist(),
    "A_minus_B_mm_to_Fmin_top": diff("A_kc_mass", "B_kc", "mm_to_Fmin_single_leg"),
    "A_over_B_f_rel_bottom": (np.array(stat["A_kc_mass_bottom"]["f_Hz"]) / np.array(stat["B_kc_bottom"]["f_Hz"]) - 1).tolist(),
}

# rod-local quantities (rear)
m_rear_B = geo.rod_mass[2]
m_rear_A = m_rear_B + DM_REAR_A
c_rear = L1["cn_per_pad_N_s_m"]["RL"]
res["rear_rod"] = {
    "dm_rear_A_kg": DM_REAR_A, "m_B": m_rear_B, "m_A": m_rear_A,
    "gn_B_1_s": c_rear / m_rear_B, "gn_A_1_s_same_c": c_rear / m_rear_A,
    "f_rod_axial_open_B_Hz": math.sqrt(k_ax[2] / m_rear_B) / (2 * math.pi),
    "f_rod_axial_open_A_Hz": math.sqrt(k_ax[2] / m_rear_A) / (2 * math.pi),
    "dt_rule_a_B_s": 1 / (math.sqrt(k_ax[2] / m_rear_B) / (2 * math.pi)) / 50,
    "dt_rule_a_A_s": 1 / (math.sqrt(k_ax[2] / m_rear_A) / (2 * math.pi)) / 50,
    "rod_on_contact_B_Hz": math.sqrt((kn_yaml[2]) / m_rear_B) / (2 * math.pi),
    "rod_on_contact_A_Hz": math.sqrt((kn_yaml[2]) / m_rear_A) / (2 * math.pi),
    "F_min_contact_basis_change_N": DM_REAR_A * g,
}

# support polygon (rigid pad hull, swivel=False reference only)
def rear_edge_margin(types):
    pts = []
    for i, t in enumerate(types):
        poly = np.array(p["legs"][LEGS[i]]["pad"]["polygon_xy_m"])
        s = PAD[t]["side_m"] / PAD["330"]["side_m"]
        pts.append(geo.pad_xy[i] + poly * s)
    pts = np.vstack(pts)
    return float(pts[:, 0].min())


res["support_polygon_rigid_hull_rear_x_m"] = {"A": rear_edge_margin(VARIANTS["A"]), "B": rear_edge_margin(VARIANTS["B"]),
                                              "pad_centre_rear_x_m": float(geo.pad_xy[2][0])}

# ---------------- 4. soil (example Bekker values, NOT project soil) ----------------------
# Wong, Theory of Ground Vehicles, Table 2.3; kc [N/m^(n+1)], kphi [N/m^(n+2)], c [Pa], phi [deg]
SOILS = {
    "dry_sand": dict(n=1.1, kc=0.99e3, kphi=1528.43e3, c=1.04e3, phi=28.0),
    "LETE_sand": dict(n=0.79, kc=102e3, kphi=5301e3, c=1.3e3, phi=31.1),
    "clayey_soil": dict(n=0.5, kc=13.19e3, kphi=692.15e3, c=4.14e3, phi=13.0),
    "heavy_clay_25": dict(n=0.13, kc=12.70e3, kphi=1555.95e3, c=68.95e3, phi=34.0),
}
CRAWLER_C = {"dry_sand": (-0.1197, 4.66), "LETE_sand": (-0.0120, 0.70), "clayey_soil": (-0.0544, 3.54), "heavy_clay_25": (0.0, 0.005)}
K_EL = 2.0e8      # ASSUMPTION: SCM elastic K [Pa/m] (S0 demo level, dynamics_model.md 3.11.3)
GAMMA = 18e3      # ASSUMPTION: soil unit weight [N/m^3]
F_pad = np.array(stat["B_kc"]["F_contact_N"])  # levelled static contact forces (top) [N]
x_front, x_rear = geo.pad_xy[:2, 0].mean(), geo.pad_xy[2:, 0].mean()
Lx = x_front - x_rear


def bearing(c, phi_deg, B):
    ph = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(ph)) * math.tan(math.pi / 4 + ph / 2) ** 2
    Nc = (Nq - 1) / math.tan(ph)
    Ng = 2 * (Nq + 1) * math.tan(ph)
    sc, sg = 1 + Nq / Nc, 0.6  # square footing (De Beer / Vesic)
    return c * Nc * sc + 0.5 * GAMMA * B * Ng * sg  # surface footing, q = 0


soil_out = {}
for sname, s in SOILS.items():
    row = {}
    for v, types in VARIANTS.items():
        z, kb, kel, p_pad, qult = [], [], [], [], []
        for i, t in enumerate(types):
            pg = PAD[t]
            pr = F_pad[i] / pg["area_m2"]
            zz = (pr / (s["kc"] / pg["b_scm_m"] + s["kphi"])) ** (1 / s["n"])
            z.append(zz); p_pad.append(pr)
            kb.append(s["n"] * F_pad[i] / zz)          # loading-branch tangent dF/dz
            kel.append(K_EL * pg["area_m2"])            # unloading branch
            qult.append(bearing(s["c"], s["phi"], pg["B_sq_m"]))
        z, kb, kel = np.array(z), np.array(kb), np.array(kel)
        k_load = dm.series(klock_yaml, kb)
        k_unl = dm.series(klock_yaml, kel)
        out = {"p_pad_kPa": (np.array(p_pad) / 1e3).tolist(), "z_pad_m": z.tolist(),
               "k_bekker_tangent_N_m": kb.tolist(), "k_elastic_KA_N_m": kel.tolist(),
               "k_leg_loading_N_m": k_load.tolist(), "k_leg_unloading_N_m": k_unl.tolist(),
               "q_ult_surface_kPa": (np.array(qult) / 1e3).tolist(),
               "p_over_qult": (np.array(p_pad) / np.array(qult)).tolist(),
               "pitch_from_pad_sink_deg": -math.degrees(math.atan((z[2:].mean() - z[:2].mean()) / Lx)),
               "extra_stroke_rear_m": float(z[2:].mean()), "extra_stroke_front_m": float(z[:2].mean())}
        for br, kk in (("loading", k_load), ("unloading", k_unl)):
            S = dm.load_sensitivity(kk, geo.pad_xy)
            Fc = F_pad - geo.rod_mass * g
            out[f"mm_to_Fmin_{br}"] = ((Fc - F_min) / np.abs(np.diag(S)) * 1e3).tolist()
            out[f"dF_ddelta_diag_{br}_N_per_mm"] = (np.diag(S) / 1e3).tolist()
            Q = dm.attitude_sensitivity(kk, geo.pad_xy)
            out[f"pitch_per_mm_rear_leg_{br}_deg"] = float(np.degrees(Q[2, 2]) * 1e-3)
        row[v] = out
    row["crawler_C_z0_m_pitch_deg"] = CRAWLER_C[sname]
    row["B_over_A_rear_z"] = row["B"]["z_pad_m"][2] / row["A"]["z_pad_m"][2]
    soil_out[sname] = row
res["soil"] = {"Lx_m": Lx, "K_elastic_Pa_m": K_EL, "gamma_N_m3": GAMMA, "soils": soil_out}

# SCM pad-soil local mode and explicit damping limit (pad body on K A; R = 7e5 Pa s/m ASSUMPTION, 3.11.3)
R_SOIL = 7.0e5
m_pad = {"front330": p["legs"]["FL"]["pad_body"]["mass_kg"], "rear250": p["legs"]["RL"]["pad_body"]["mass_kg"],
         "rear330": p["legs"]["RL"]["pad_body"]["mass_kg"] + DM_REAR_A}
A_pad = {"front330": PAD["330"]["area_m2"], "rear250": PAD["250"]["area_m2"], "rear330": PAD["330"]["area_m2"]}
res["scm_pad_local"] = {k: {"m_kg": m_pad[k], "KA_N_m": K_EL * A_pad[k],
                            "f_Hz": math.sqrt(K_EL * A_pad[k] / m_pad[k]) / (2 * math.pi),
                            "RA_N_s_m": R_SOIL * A_pad[k], "dt_explicit_2m_over_c_s": 2 * m_pad[k] / (R_SOIL * A_pad[k])}
                        for k in m_pad}
# rough slab punching shear (ASSUMPTION: d = 0.16 m effective depth, control perimeter at d/2 of the equivalent square)
d_eff = 0.16
res["slab_punching_rough"] = {}
for leg_i, t in ((0, "330"), (2, "330"), (2, "250")):
    u = 4 * PAD[t]["B_sq_m"] + math.pi * d_eff
    res["slab_punching_rough"][f"{LEGS[leg_i]}_{t}"] = {"F_N": float(F_pad[leg_i]), "u_m": u,
                                                       "v_MPa": float(F_pad[leg_i]) / (u * d_eff) / 1e6}

# stroke budget at the rigid-floor operating point
res["stroke_budget_m"] = {"stroke": p["actuator"]["stroke_m"], "operating_extension": e_op.tolist(),
                          "remaining_rigid_floor": (p["actuator"]["stroke_m"] - e_op).tolist(),
                          "end_margin_ref": 0.6848}

OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")


def fmt(a, n=4):
    return [round(float(x), n) for x in a]


print("pad", {k: (round(v["area_m2"], 5), round(v["b_scm_m"], 4), round(v["a_eq_m"], 4)) for k, v in PAD.items()})
print("WG l", round(l, 4), "k0", f"{k0:.4e}", {k: round(wg[k]["rel_to_point"], 5) for k in PAD})
print("rebuild", chk)
for q in ("kn", "klock", "kt"):
    print(q, "A rel", fmt(res["stiffness"]["A"][f"{q}_rel_to_yaml"], 6), "B rel", fmt(res["stiffness"]["B"][f"{q}_rel_to_yaml"], 6),
          "B/A", fmt(res["stiffness"]["B_vs_A_rel"][q], 6))
for k in ("yaml", "A_kc_mass", "B_kc"):
    s = stat[k]
    print(k, "F", fmt(np.array(s["F_contact_N"]) / 1e3, 3), "mmFmin", fmt(s["mm_to_Fmin_single_leg"], 2), "f", fmt(s["f_Hz"], 3))
print("diff", {k: fmt(v, 5) for k, v in res["diff"].items()})
print("rear_rod", {k: round(v, 6) for k, v in res["rear_rod"].items()})
print("hull rear x", res["support_polygon_rigid_hull_rear_x_m"])
for sname, row in soil_out.items():
    for v in ("A", "B"):
        o = row[v]
        print(sname, v, "p", fmt(o["p_pad_kPa"], 0), "z", fmt(o["z_pad_m"], 4), "kb", fmt(np.array(o["k_bekker_tangent_N_m"]) / 1e6, 2),
              "kel", fmt(np.array(o["k_elastic_KA_N_m"]) / 1e6, 2), "p/qult", fmt(o["p_over_qult"], 2),
              "pitch", round(o["pitch_from_pad_sink_deg"], 3), "mmFmin L/U", fmt(o["mm_to_Fmin_loading"], 2), fmt(o["mm_to_Fmin_unloading"], 2),
              "pitch/mm rear L/U", round(o["pitch_per_mm_rear_leg_loading_deg"], 5), round(o["pitch_per_mm_rear_leg_unloading_deg"], 5))
    print(sname, "B/A rear z", round(row["B_over_A_rear_z"], 3), "crawler", row["crawler_C_z0_m_pitch_deg"])
print("Lx", Lx, "budget", res["stroke_budget_m"])
print("scm_pad_local", {k: {kk: round(vv, 6) for kk, vv in v.items()} for k, v in res["scm_pad_local"].items()})
print("punching", res["slab_punching_rough"])
