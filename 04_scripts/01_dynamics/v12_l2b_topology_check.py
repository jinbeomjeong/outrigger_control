"""V12 L2b-NSC horizontal reactions: reference topology vs Chrono topology (independent check).

Reference (run_reference slope_V12 / L2b_NSC, dyn_model.static_slope_10dof): rods laterally rigid
with the body, lateral spring kt between contact point and floor in the floor plane.
Chrono (S7 L2bModel): lateral spring kt between barrel (body point at the ball centre) and rod,
body-horizontal axes; NSC contact rigid in all directions (stick); rod rotation = body rotation.
Both linear, no P-delta. Prints world horizontal contact reactions (floor -> rod) per leg.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

KC_RIGID = 1e13
p = dm.load_params()
geo = dm.geometry_from_params(p)
A_ = dm.ASSUMPTIONS
g = geo.g
touch = geo.touch_extension
e_op = touch + A_["crawler_clearance_m"]
kc_nom = dm.k_concrete_westergaard()["k_slab_N_m"]
kr = dm.k_rod()
kf = A_["frame_bracket_stiffness_N_m"]
kh_free = dm.k_leg_lateral_legs(geo, e_op, False)
kt_L1 = dm.series(kh_free, kc_nom)
b = dm.body_from_params(p, "top")
xy = geo.pad_xy
hb = A_["swivel_ball_height_above_pad_bottom_m"]


def levelled_extension(ro, pi, clearance):
    """Same as ``run_reference.main.levelled_extension`` (copied: it is a closure there)."""
    sx = -math.tan(math.radians(pi))
    sy = math.tan(math.radians(ro))
    (x0, x1), (y0, y1) = geo.crawler_xy_box
    corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
    H = np.max(sx * corners[:, 0] + sy * corners[:, 1]) + clearance - geo.crawler_bottom_z
    return geo.pad_z_retracted + H - (sx * xy[:, 0] + sy * xy[:, 1])


def chrono_topology(ext, ko, kt, pi, ro):
    """18-DoF linear statics (body 6 about the CoM + rod ball translation x, y, z per leg).

    Independent copy kept on purpose: the rev. 35 reference uses dm.static_slope_l2b_chrono_topology;
    this script checks that function against this copy (``shared_function_max_abs_diff_N``)."""
    sx = -math.tan(math.radians(pi))
    sy = math.tan(math.radians(ro))
    nrm = np.array([-sx, -sy, 1.0])
    nrm /= np.linalg.norm(nrm)
    n = 6 + 12
    K = np.zeros((n, n))
    f = np.zeros(n)
    f[2] = -b.mass * g
    rows = []
    for i in range(4):
        r0 = 6 + 3 * i
        f[r0 + 2] = -geo.rod_mass[i] * g
        d_att = np.array([*xy[i], geo.attach_z[i]]) - b.com
        d_ball = np.array([*xy[i], geo.pad_z_retracted[i] - ext[i] + hb]) - b.com
        _, _, az_att = dm.a_vec(d_att)
        ax_b, ay_b, _ = dm.a_vec(d_ball)
        bb = np.zeros(n)
        bb[:6] = az_att
        bb[r0 + 2] = -1.0
        K += ko[i] * np.outer(bb, bb)
        for a, k in ((ax_b, 0), (ay_b, 1)):  # lateral spring barrel (body) - rod, body x / y
            e = np.zeros(n)
            e[:6] = a
            e[r0 + k] = -1.0
            K += kt[i] * np.outer(e, e)
        # contact point = rod ball + theta x (-hb n) (rod turns with the body), rigid stick
        G = np.zeros((3, n))
        G[:, r0:r0 + 3] = np.eye(3)
        # d/dtheta of (theta x v) = -skew(v), v = -hb n
        v = -hb * nrm
        skew_v = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        G[:, 3:6] = -skew_v
        K += KC_RIGID * G.T @ G
        rows.append(G)
    q = np.linalg.solve(K, f)
    R = np.array([-KC_RIGID * (G @ q) for G in rows])
    return R, q


out = {}
run = Path(sys.argv[1]) if len(sys.argv) > 1 else None
for idx, (ro, pi) in enumerate([(0, 2), (2, 0), (-2, 1.5)]):
    ext = levelled_extension(ro, pi, A_["crawler_clearance_m"])
    ko_s = dm.series(dm.k_oil(ext), kr, kf)
    ko = dm.series(ko_s, kc_nom)
    ref = dm.static_slope_10dof(b, geo, ext, ko, np.full(4, KC_RIGID), kt_L1, slope_pitch_deg=pi,
                                slope_roll_deg=ro)
    R, q = chrono_topology(ext, ko, kt_L1, pi, ro)
    sh = dm.static_slope_l2b_chrono_topology(b, geo, ext, ko, kt_L1, slope_pitch_deg=pi,
                                             slope_roll_deg=ro, kc_rigid=KC_RIGID)
    d_shared = float(np.abs(sh["R"] - R).max())
    if d_shared > 1e-3:
        raise RuntimeError(f"shared function differs from the independent copy: {d_shared} N")
    name = f"ground roll {ro} deg, pitch {pi} deg"
    row = {"ref_topology_horizontal_N": np.round(ref["R"][:, :2], 1).tolist(),
           "ref_topology_vertical_N": np.round(ref["R"][:, 2], 1).tolist(),
           "chrono_topology_horizontal_N": np.round(R[:, :2], 1).tolist(),
           "chrono_topology_vertical_N": np.round(R[:, 2], 1).tolist(),
           "chrono_topology_attitude_deg": np.round(np.degrees(q[3:5]), 5).tolist(),
           "shared_function_max_abs_diff_N": d_shared}
    if run is not None and (run / f"V12_{idx}" / "result.json").exists():
        rr = json.loads((run / f"V12_{idx}" / "result.json").read_text())
        contact = np.array(rr["mean_last_s"]["pad_contact_world_N"])
        row["chrono_run_horizontal_N"] = np.round(contact[:, :2], 1).tolist()
        row["chrono_run_vertical_N"] = np.round(contact[:, 2], 1).tolist()
        row["chrono_run_attitude_deg"] = np.round(rr["mean_last_s"]["roll_pitch_deg"], 5).tolist()
    out[name] = row
text = json.dumps(out, indent=1)
print(text)
(ROOT / "06_analysis" / "00_dynamics" / "v12_l2b_topology_check.json").write_text(
    text + chr(10), encoding="utf-8")
