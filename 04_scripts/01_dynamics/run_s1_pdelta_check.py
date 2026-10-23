"""Independent nonlinear static check of the S1 L1 equilibrium (6-DoF rigid body).

Usage (project root, dynamics-dev): conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s1_pdelta_check.py
Writes 06_analysis/00_dynamics/s1_pdelta_check.json. dynamics_model.md 5.2 (rev. 11).

Model (independent of the project code; inputs read from the YAML only):
- One rigid body = superstructure (level com/mass) + 4 leg moving parts at e_op.
- Pad = sphere (radius r = swivel height) centred at the ball centre, flat floor z_f.
  Normal force kn_i * penetration, vertical, at the world point under the sphere centre.
- Tangential bushing kt_i anchored at the body-fixed point that coincides with the contact
  point at the start pose (analytic linear pose), force in the floor plane only.
- Gravity -9.80665 z (world). Rotation R = Rz(yaw) Ry(pitch) Rx(roll).
Outputs per level: contact force, cylinder force, penetration, roll/pitch, compared with
the linear 3-DoF solution (same kn) and the Chrono S1 values.

The Chrono S1 values are the still-window means of ``07_results/S1/<level>/result.json``
(``contact_force_mean_N``, ``roll_mean_deg``, ``pitch_mean_deg``). They are marked stale
(``<level>.chrono_source.stale``) when the record's ``params_file_sha256`` (``meta.json``)
is not the sha256 of the current YAML file or the files cannot be read; unreadable values give
null Chrono comparisons. The output carries ``params_file_sha256`` of the YAML it solved.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import fsolve

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
PARAMS_PATH = Path(ROOT) / "02_params" / "rexome33.yaml"
PARAMS_FILE_SHA256 = hashlib.sha256(PARAMS_PATH.read_bytes()).hexdigest()
S1_RESULTS = Path(ROOT) / "07_results" / "S1"
P = yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))
G = P["meta"]["gravity_m_s2"] if "gravity_m_s2" in P["meta"] else 9.80665
LEGS = ["FL", "FR", "RL", "RR"]
L1 = P["contact"]["rigid_floor"]["L1"]
kn = np.array([L1["kn_per_pad_N_m"][k] for k in LEGS])
kt = np.array([L1["kt_per_pad_N_m"][k] for k in LEGS])
eop = np.array([L1["derivation"]["operating_extension_m"][k] for k in LEGS])
zf = P["ground"]["crawler_bottom_z_m"]
legs = P["legs"]
r = np.array([legs[k]["pad"]["swivel_center_above_pad_bottom_m"] for k in LEGS])
padb = np.array([legs[k]["pad_bottom_center_retracted_m"] for k in LEGS], float)
padb[:, 2] -= eop
centre_b = padb + np.c_[np.zeros(4), np.zeros(4), r]
mmov = np.array([legs[k]["moving_part"]["mass_kg"] for k in LEGS])
cmov = np.array([legs[k]["moving_part"]["com_retracted_m"] for k in LEGS], float)
cmov[:, 2] -= eop

def load_chrono_s1(level):
    """Chrono S1 still-window means of one level and their source record.

    Returns ``(contact_N, (roll_deg, pitch_deg))`` or ``None`` when the result cannot be read,
    and the source description with the ``stale`` flag (module docstring).
    """
    result_path = S1_RESULTS / level / "result.json"
    source = {"path": f"07_results/S1/{level}/result.json"}
    try:
        window = json.loads(result_path.read_text(encoding="utf-8"))["still_window"]
        contact_N = [float(f) for f in window["contact_force_mean_N"]]
        attitude_deg = (float(window["roll_mean_deg"]), float(window["pitch_mean_deg"]))
    except (OSError, KeyError, TypeError, ValueError) as err:
        source.update(stale=True, reason=f"result unreadable: {err!r}")
        print(f"WARNING Chrono S1 {level}: {source['reason']}", flush=True)
        return None, source
    try:
        meta = json.loads(result_path.with_name("meta.json").read_text(encoding="utf-8"))
        record_sha256 = meta["run"]["params_file_sha256"]
    except (OSError, KeyError, TypeError, ValueError):
        record_sha256 = None
    source["params_file_sha256"] = record_sha256
    source["stale"] = record_sha256 != PARAMS_FILE_SHA256
    if source["stale"]:
        source["reason"] = "S1 record params_file_sha256 differs from the current YAML (or missing)"
        print(f"WARNING Chrono S1 {level}: stale ({source['reason']})", flush=True)
    return (contact_N, attitude_deg), source


def rot(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def linear3(ms, cs):
    """dynamics_model.md 3.1 linear 3-DoF (fixed moment arms), z0 = pads touching."""
    m = ms + mmov.sum()
    c = (ms * cs + (mmov[:, None] * cmov).sum(0)) / m
    W = m * G
    x, y = centre_b[:, 0], centre_b[:, 1]
    A = np.c_[np.ones(4), y, -x]
    K = np.diag(kn)
    w = np.array([W, W * c[1], -W * c[0]])
    # compression c_i = -(A q)_i with q = (u_z, roll, pitch); F = K c; equilibrium A^T F = w
    q = np.linalg.solve(A.T @ K @ A, -w)
    F = -K @ A @ q
    return F, q, W, c


def solve(level, kt_scale=1.0, start=None):
    lv = P["superstructure"]["auger_levels"][level]
    ms, cs = lv["mass_kg"], np.array(lv["com_m"])
    F_lin, q_lin, W, c = linear3(ms, cs)
    z0 = zf - padb[0, 2]  # origin z with pads just touching (level)
    # start pose = analytic linear pose (bushing anchors set here)
    if start is None:
        start = np.array([0, 0, z0 + q_lin[0], q_lin[1], q_lin[2], 0.0])
    R0 = rot(start[3], start[4], start[5])
    # body-fixed point: centre_b + R0^T(0,0,-r)
    contact_b = centre_b + (R0.T @ np.array([0, 0, -1.0]))[None, :] * r[:, None]
    anchor = start[:3] + contact_b @ R0.T
    comw_b = c

    def forces(s):
        R = rot(s[3], s[4], s[5])
        o = s[:3]
        cw = o + centre_b @ R.T
        pen = r - (cw[:, 2] - zf)
        Fn = kn * np.maximum(pen, 0)
        pw = o + contact_b @ R.T
        dt = (pw - anchor)[:, :2]
        Ft = -kt_scale * kt[:, None] * dt
        return cw, pen, Fn, Ft, R

    def resid(s):
        cw, pen, Fn, Ft, R = forces(s)
        o = s[:3]
        gpos = o + R @ comw_b
        f = np.zeros(3)
        mo = np.zeros(3)
        for i in range(4):
            Fi = np.array([Ft[i, 0], Ft[i, 1], Fn[i]])
            pi = np.array([cw[i, 0], cw[i, 1], zf])  # contact point on the floor under the centre
            f += Fi
            mo += np.cross(pi - o, Fi)
        Fg = np.array([0, 0, -W])
        f += Fg
        mo += np.cross(gpos - o, Fg)
        return np.r_[f / W, mo / W]

    s = fsolve(resid, start, xtol=1e-15)
    cw, pen, Fn, Ft, R = forces(s)
    # cylinder force: contact force along the leg axis minus moving part weight along the axis
    axis = R @ np.array([0, 0, 1.0])
    Fcyl = np.array([np.dot([Ft[i, 0], Ft[i, 1], Fn[i]], axis) for i in range(4)]) - mmov * G * axis[2]
    return dict(Fn=Fn, Ft=Ft, pen_mm=pen * 1e3, roll_deg=np.degrees(s[3]), pitch_deg=np.degrees(s[4]),
                Fcyl=Fcyl, F_lin=F_lin, q_lin=q_lin, W=W, com=c, res=np.abs(resid(s)).max(),
                Fcyl_lin=F_lin - mmov * G, z_cg_above_centres=c[2] - centre_b[:, 2].mean())


out = {"params_file_sha256": PARAMS_FILE_SHA256}
for lev in ["top", "middle", "bottom"]:
    a = solve(lev)
    b = solve(lev, kt_scale=0.0 + 1e-9)
    chrono, chrono_source = load_chrono_s1(lev)
    chrono_contact = None if chrono is None else np.array(chrono[0])
    xc = a["com"][0]
    th = np.radians(a["pitch_deg"])
    h = a["z_cg_above_centres"]
    row = {
        "W_N": a["W"], "com_m": a["com"].tolist(), "h_cg_above_ball_m": h,
        "linear_contact_N": a["F_lin"].tolist(),
        "nonlinear_contact_N": a["Fn"].tolist(),
        "nonlinear_minus_linear_N": (a["Fn"] - a["F_lin"]).tolist(),
        "chrono_minus_nonlinear_N": None if chrono is None else (chrono_contact - a["Fn"]).tolist(),
        "chrono_minus_linear_N": None if chrono is None else (chrono_contact - a["F_lin"]).tolist(),
        "nonlinear_kt0_contact_N": b["Fn"].tolist(),
        "nonlinear_cyl_N": a["Fcyl"].tolist(),
        "nonlinear_pen_mm": a["pen_mm"].tolist(),
        "nonlinear_roll_pitch_deg": [a["roll_deg"], a["pitch_deg"]],
        "chrono_roll_pitch_deg": None if chrono is None else list(chrono[1]),
        "chrono_source": chrono_source,
        "linear_roll_pitch_deg": np.degrees(a["q_lin"][1:]).tolist(),
        "tangential_N": a["Ft"].tolist(),
        "pdelta_shift_m": h * th,
        "resid": a["res"],
    }
    out[lev] = row
    print(lev, json.dumps({k: (np.round(v, 4).tolist() if isinstance(v, (list, np.ndarray)) else v)
                           for k, v in row.items()}))
OUT = sys.argv[2] if len(sys.argv) > 2 else ROOT + "/06_analysis/00_dynamics/s1_pdelta_check.json"
json.dump(out, open(OUT, "w"), indent=1, default=float)
