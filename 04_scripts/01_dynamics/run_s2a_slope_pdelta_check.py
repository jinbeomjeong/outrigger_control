"""Independent nonlinear static check of the S2a V12 sloped-floor equilibrium (6-DoF rigid body).

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s2a_slope_pdelta_check.py
Writes 06_analysis/00_dynamics/s2a_slope_pdelta_check.json. dynamics_model.md 5.3 (rev. 12),
5.5 (rev. 14: Chrono bushing at the ball centre since option A -> compare with the "ball" variant).

Extension of run_s1_pdelta_check.py to a tilted floor plane. Inputs: the YAML only, plus the
three floor planes (point + unit normal) and the level-body start height of the Chrono runs
(07_results/S2a/<case>/result.json "start"), which are set-up data, not results.

Model (independent of the project code):
- One rigid body = superstructure (top level) + 4 leg moving parts at the levelled extension
  (rigid L1 motor, the moving part is rigidly attached to the body).
- Pad = sphere (radius r = swivel height) centred at the ball centre. Floor = plane through
  p0 with unit normal n. Normal force kn * penetration along n (linear Hooke, as the L1 SMC).
- Tangential bushing kt in the floor plane between the body-fixed point that coincides with the
  sphere contact point at the start pose and the floor anchor at that point (stick, no slip).
- Gravity (0, 0, -9.80665) m/s^2 world. Rotation R = Rz(yaw) Ry(pitch) Rx(roll).
- Extensions: level body, every sphere exactly touching the plane (computed here, compared with
  the Chrono start extensions).
Variants per case:
- nonlinear: full equilibrium (geometry updated).
- linear: same model, gravity scaled by eps = 1e-7 and forces rescaled by 1/eps, i.e. the
  linearisation about the unloaded start pose (= dyn_model.static_slope_10dof, L1 column).
- "ball" variant: the bushing (tangential force) at the ball centre instead of the sphere contact
  point, so the whole floor reaction passes through the swivel centre (real swivel pad). Its
  linearisation reproduces the reference (static_slope_10dof); the Chrono sphere-pad model
  carries the extra moment r x T about each ball ("sphere lever").
"""
import json
import sys

import numpy as np
import yaml
from scipy.optimize import fsolve

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
P = yaml.safe_load(open(ROOT + "/02_params/rexome33.yaml", encoding="utf-8"))
G = 9.80665
LEGS = ["FL", "FR", "RL", "RR"]
L1 = P["contact"]["rigid_floor"]["L1"]
kn = np.array([L1["kn_per_pad_N_m"][k] for k in LEGS])
kt = np.array([L1["bushing_stiffness_per_pad_N_m"][k] for k in LEGS])
legs = P["legs"]
r = np.array([legs[k]["pad"]["swivel_center_above_pad_bottom_m"] for k in LEGS])
padb_ret = np.array([legs[k]["pad_bottom_center_retracted_m"] for k in LEGS], float)
mmov = np.array([legs[k]["moving_part"]["mass_kg"] for k in LEGS])
cmov_ret = np.array([legs[k]["moving_part"]["com_retracted_m"] for k in LEGS], float)
lv = P["superstructure"]["auger_levels"]["top"]
ms, cs = lv["mass_kg"], np.array(lv["com_m"], float)
REF = json.load(open(ROOT + "/06_analysis/00_dynamics/reference.json", encoding="utf-8"))["slope_V12"]
_VER_ALL = json.load(open(ROOT + "/06_analysis/01_chrono/verify_S2a_L1.json", encoding="utf-8"))
VER = _VER_ALL["v12"]
VER_FP = _VER_ALL["meta"].get("ground_bushing_force_point", ["contact_point"])

CASES = {"v12_pitch2": (0.0, 2.0), "v12_roll2": (2.0, 0.0), "v12_rollm2_pitch1.5": (-2.0, 1.5)}


def rot(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def build(case):
    st = VER[case]["start"]
    n = np.array(st["normal_world"], float)
    n /= np.linalg.norm(n)
    p0 = np.array(st["floor_point_world_m"], float)
    o0 = np.array(st["body_origin_m"], float)
    # level body, sphere centre c = o0 + padb_ret - e z + r z ; touch: n.(c - p0) = r
    base = o0 + padb_ret + np.c_[np.zeros(4), np.zeros(4), r]
    e = ((base - p0) @ n - r) / n[2]
    centre_b = padb_ret - np.c_[np.zeros(4), np.zeros(4), e] + np.c_[np.zeros(4), np.zeros(4), r]
    cmov = cmov_ret - np.c_[np.zeros(4), np.zeros(4), e]
    m = ms + mmov.sum()
    com = (ms * cs + (mmov[:, None] * cmov).sum(0)) / m
    contact_b = centre_b - r[:, None] * n[None, :]  # body-fixed point at the start contact (R0 = I)
    anchor = o0 + contact_b
    Pt = np.eye(3) - np.outer(n, n)
    return dict(n=n, p0=p0, o0=o0, e=e, centre_b=centre_b, contact_b=contact_b, anchor=anchor,
                Pt=Pt, m=m, com=com, W=m * G)


def solve(M, gscale=1.0, kt_scale=1.0):
    n, p0, Pt = M["n"], M["p0"], M["Pt"]
    W = M["W"] * gscale

    def forces(s):
        R = rot(s[3], s[4], s[5])
        o = s[:3]
        cw = o + M["centre_b"] @ R.T
        pen = r - (cw - p0) @ n
        Fn = kn * np.maximum(pen, 0.0)
        pa = o + M["contact_b"] @ R.T
        Ft = -(kt_scale * kt)[:, None] * ((pa - M["anchor"]) @ Pt.T)
        Rf = Fn[:, None] * n[None, :] + Ft
        return cw, pa, pen, Rf, R

    def resid(s):
        cw, pa, pen, Rf, R = forces(s)
        o = s[:3]
        gpos = o + R @ M["com"]
        f = Rf.sum(0) + np.array([0, 0, -W])
        mo = np.zeros(3)
        for i in range(4):
            # normal force through the ball centre; tangential at the bushing point (frame A)
            Fn_i = (Rf[i] @ n) * n
            mo += np.cross(cw[i] - n * r[i] - o, Fn_i) + np.cross(pa[i] - o, Rf[i] - Fn_i)
        mo += np.cross(gpos - o, np.array([0, 0, -W]))
        return np.r_[f, mo] / M["W"]

    s0 = np.r_[M["o0"], 0, 0, 0]
    s = fsolve(resid, s0, xtol=1e-14)
    s = fsolve(resid, s, xtol=1e-15)
    cw, pa, pen, Rf, R = forces(s)
    axis = R @ np.array([0, 0, 1.0])
    Fcyl = Rf @ axis - mmov * G * gscale * axis[2]
    dt = (pa - M["anchor"]) @ Pt.T
    return dict(s=s, R=Rf, Fcyl=Fcyl, pen=pen, roll=np.degrees(s[3]), pitch=np.degrees(s[4]),
                yaw=np.degrees(s[5]), bush=np.linalg.norm(dt, axis=1), res=float(np.abs(resid(s)).max()),
                N=Rf @ n, T=np.linalg.norm(Rf - np.outer(Rf @ n, n), axis=1))


out = {"meta": {"script": "04_scripts/01_dynamics/run_s2a_slope_pdelta_check.py",
                "model": "6-DoF rigid body, sphere pads on a tilted plane, Hooke normal kn, stick bushing kt in the plane",
                "gravity_m_s2": [0, 0, -G], "frames": "world, Z up; roll/pitch ZYX (deg)",
                "level": "top", "inputs": "YAML + floor plane and start height of the Chrono runs",
                "chrono_ground_bushing_force_point": VER_FP}}
for case, (ro, pi) in CASES.items():
    M = build(case)
    nl = solve(M)
    eps = 1e-7
    li = solve(M, gscale=eps)
    lin_R = li["R"] / eps
    lin_cyl = li["Fcyl"] / eps
    lin_att = np.degrees(li["s"][3:5]) / eps
    w = VER[case]["window"]
    ch_R = np.array(w["reaction_world_mean_N"])
    ch_cyl = np.array(w["motor_force_mean_N"])
    key = f"ground roll {ro:g} deg, pitch {pi:g} deg"
    ref = REF[key]["L1"]
    ref_z = np.array(ref["contact_vertical_N"])
    ref_xy = np.array(ref["contact_horizontal_xy_N"])
    # P-delta estimate: body rotation (nonlinear pose) moves the CoM relative to the ball centres
    # variant "ball": bushing (tangential force) applied at the ball centre instead of the sphere
    # contact point, i.e. the whole floor reaction passes through the swivel centre (real swivel pad)
    Mb = dict(M, contact_b=M["centre_b"], anchor=M["o0"] + M["centre_b"])
    nlb = solve(Mb)
    lib = solve(Mb, gscale=eps)
    lin_b_R = lib["R"] / eps
    row = {
        "case": key,
        "ball_variant_linear_minus_reference_vertical_N": (lin_b_R[:, 2] - ref_z).tolist(),
        "ball_variant_linear_minus_reference_horizontal_N": (lin_b_R[:, :2] - ref_xy).tolist(),
        "ball_variant_nonlinear_minus_linear_vertical_N": (nlb["R"][:, 2] - lin_b_R[:, 2]).tolist(),
        "contact_minus_ball_nonlinear_vertical_N": (nl["R"][:, 2] - nlb["R"][:, 2]).tolist(),
        "sphere_lever_moment_estimate_N_m": float(np.sum(r * nl["T"])),
        "chrono_minus_ball_nonlinear_vertical_N": (ch_R[:, 2] - nlb["R"][:, 2]).tolist(),
        # rev. 14: Chrono runs since option A apply the bushing at the ball centre -> "ball" variant
        "chrono_force_point": VER_FP,
        "chrono_minus_ball_nonlinear_horizontal_N": (ch_R[:, :2] - nlb["R"][:, :2]).tolist(),
        "chrono_minus_ball_nonlinear_cyl_N": (ch_cyl - nlb["Fcyl"]).tolist(),
        "chrono_minus_ball_nonlinear_bushing_disp_mm":
            ((np.array(w["bushing_disp_mean_m"]) - nlb["bush"]) * 1e3).tolist(),
        "ball_nonlinear_vertical_N": nlb["R"][:, 2].tolist(),
        "ball_nonlinear_horizontal_N": nlb["R"][:, :2].tolist(),
        "ball_nonlinear_cyl_N": nlb["Fcyl"].tolist(),
        "ball_nonlinear_bushing_disp_mm": (nlb["bush"] * 1e3).tolist(),
        "ball_nonlinear_inplane_force_N": nlb["T"].tolist(),
        "ball_nonlinear_attitude_deg": [nlb["roll"], nlb["pitch"], nlb["yaw"]],
        "ball_nonlinear_minus_reference_vertical_N": (nlb["R"][:, 2] - ref_z).tolist(),
        "ball_resid": nlb["res"],
        "extension_here_m": M["e"].tolist(),
        "extension_chrono_start_m": VER[case]["start"]["extensions_m"],
        "extension_here_minus_chrono_mm": ((M["e"] - np.array(VER[case]["start"]["extensions_m"])) * 1e3).tolist(),
        "extension_reference_rounded_m": REF[key]["extension_m"],
        "W_N": M["W"],
        "com_world_start_m": (M["o0"] + M["com"]).tolist(),
        "linear_vertical_N": lin_R[:, 2].tolist(),
        "linear_minus_reference_vertical_N": (lin_R[:, 2] - ref_z).tolist(),
        "linear_minus_reference_horizontal_N": (lin_R[:, :2] - ref_xy).tolist(),
        "linear_attitude_deg": lin_att.tolist(),
        "nonlinear_vertical_N": nl["R"][:, 2].tolist(),
        "nonlinear_horizontal_N": nl["R"][:, :2].tolist(),
        "nonlinear_cyl_N": nl["Fcyl"].tolist(),
        "nonlinear_attitude_deg": [nl["roll"], nl["pitch"], nl["yaw"]],
        "nonlinear_bushing_disp_mm": (nl["bush"] * 1e3).tolist(),
        "nonlinear_inplane_force_N": nl["T"].tolist(),
        "nonlinear_minus_linear_vertical_N": (nl["R"][:, 2] - lin_R[:, 2]).tolist(),
        "chrono_minus_reference_vertical_N": (ch_R[:, 2] - ref_z).tolist(),
        "chrono_minus_nonlinear_vertical_N": (ch_R[:, 2] - nl["R"][:, 2]).tolist(),
        "chrono_minus_nonlinear_horizontal_N": (ch_R[:, :2] - nl["R"][:, :2]).tolist(),
        "chrono_minus_nonlinear_cyl_N": (ch_cyl - nl["Fcyl"]).tolist(),
        "chrono_minus_nonlinear_bushing_disp_mm": (np.array(w["bushing_disp_mean_m"]) * 1e3 - nl["bush"] * 1e3).tolist(),
        "chrono_attitude_deg": [w["roll_mean_deg"], w["pitch_mean_deg"]],
        "displacement_body_origin_mm": ((nl["s"][:3] - M["o0"]) * 1e3).tolist(),
        "resid": nl["res"],
    }
    out[case] = row
    print(case)
    for k in ["ball_variant_linear_minus_reference_vertical_N", "ball_variant_linear_minus_reference_horizontal_N",
              "ball_variant_nonlinear_minus_linear_vertical_N", "contact_minus_ball_nonlinear_vertical_N",
              "sphere_lever_moment_estimate_N_m", "chrono_minus_ball_nonlinear_vertical_N",
              "chrono_minus_ball_nonlinear_horizontal_N", "chrono_minus_ball_nonlinear_cyl_N",
              "chrono_minus_ball_nonlinear_bushing_disp_mm", "ball_nonlinear_minus_reference_vertical_N",
              "ball_nonlinear_attitude_deg", "ball_resid",
              "extension_here_minus_chrono_mm", "linear_minus_reference_vertical_N", "linear_minus_reference_horizontal_N",
              "nonlinear_minus_linear_vertical_N", "chrono_minus_reference_vertical_N",
              "chrono_minus_nonlinear_vertical_N", "chrono_minus_nonlinear_horizontal_N", "chrono_minus_nonlinear_cyl_N",
              "nonlinear_bushing_disp_mm", "chrono_minus_nonlinear_bushing_disp_mm", "nonlinear_inplane_force_N",
              "nonlinear_attitude_deg", "chrono_attitude_deg", "linear_attitude_deg", "displacement_body_origin_mm", "resid"]:
        print("  ", k, np.round(np.array(row[k], float), 4).tolist())

OUT = sys.argv[2] if len(sys.argv) > 2 else ROOT + "/06_analysis/00_dynamics/s2a_slope_pdelta_check.json"
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, default=float)
print("written", OUT)
