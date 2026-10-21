"""Roll / pitch target reachability envelope of the levelled deck (dynamics_model.md 3.12, rev. 21).

Question (user decision 2026-10-21): provisional target range pitch +/-3 deg, roll +/-6 deg (from a flat-floor
geometric estimate). Is a target attitude (phi_t, theta_t) of the deck reachable and safe on a flat floor and on
slopes inside the D8 range, for the three auger levels?

Definition: target (phi_t, theta_t) is REACHABLE when the deck can sit in static equilibrium at that attitude with
  * every leg stroke 0 <= s <= stroke_m (motor position = C2 stroke-end coordinate; margin variants 0 / 10 mm),
  * the lowest crawler point at least c_req above the floor (c_req 0 / 20 / 50 mm; C2 heave target is 50 mm,
    clearance measured like C2 = min normal distance of the 4 crawler-box corners; the physical track points
    (roller stations, raised end shoes, shoe edges) are reported as a second measure),
  * every cylinder force F_min <= F_cyl <= 218 kN (guard variant F_min + 5 kN), twist target n^T F_cyl = 0 (C2 D6),
  * every swivel tilt (angle between leg axis and floor normal) <= swivel_tilt_range_deg,
  * no pad lift-off (normal contact force > 0).
Separate indicators: pad slip (|T| > mu N, mu 0.5), rod bending margin (00_docs/00_cad/leg_rod_lateral_check.md
model, imported), allowed twist interval.

Model (quasi-static, exact rotations; independent of Chrono and of the reduced time-domain plant):
  * Floor plane n . x = 0, n = floor_normal(phi_g, theta_g) (project convention of run_control_comparison.Plant:
    plane z = -tan(theta_g) x + tan(phi_g) y). Target attitude R_t = Rz(psi) Ry(theta_t) Rx(phi_t) (ZYX, intrinsic
    yaw-pitch-roll; psi is a free equilibrium DOF, ~0). roll > 0 left side up, pitch > 0 nose down.
  * Pads touch down while the machine stands settled on the crawler (body parallel to the floor x crawler settle
    rotation, dyn_model.static_unilateral, layout D) and stick there (anchor = pad-bottom contact point).
  * Deck at the target: body position O = (X, Y, Z); Z from the clearance rule (lowest box corner at c_req, C2 heave
    loop), X, Y, psi free. Rod tip (ball centre) is held at anchor + h_b n: the rod deflects laterally
    delta_i (perpendicular to the leg axis a = R e_z) and the geometric extension is e_i = -(v_i . a).
    Ground force on the moving part i: R_i = F_ax,i a + k_t,i delta_i (k_t = series(swivel cantilever bending,
    concrete tangential); 'yaml' = YAML L1 kt_per_pad (upper bound), 'ext' = secant k_t(e) (best estimate)).
  * Unknowns X, Y, psi, F_ax(4): force (3) + moment (3) equilibrium of body + moving parts (gravity at the combined
    CoM with the rods at their extension) + twist condition n_tw^T F_cyl = tau (tau = 0 nominal).
    F_cyl = F_ax - m_rod g (e_z,world . a) (cylinder force = pressure reading basis, CLAUDE.md F_min).
  * Coulomb: N_i = n . R_i, T_i = R_i - N_i n; |T_i| > mu N_i -> anchor return mapping (pad slips to the cap).
  * Stroke: s_motor = e + F_ax / series(k_oil(e), k_rod, k_frame, k_concrete) (L1 motor coordinate, includes oil
    compression; C2 stroke-end rule uses it); s_piston = e + F_ax / series(k_rod, k_frame, k_concrete) recorded.
  * Twist interval: at the solved kinematics, N + t w (w = normal-force null vector of the 3 normal equilibrium
    equations) keeps equilibrium; interval of n_tw^T F_cyl with all F_cyl in [F_lo, 218 kN].
  * Acceptance rules (RULES / rule_check): relative diamond on (target - floor attitude) and optional absolute
    diamond; counts accepted-but-infeasible grid points per criterion set (dynamics_model.md 3.12.6).
  * Checks C1-C8 (stage 'checks'): YAML static loads, pad_tangential_check kin, dynamics 3.3 limits, twist interval
    re-solve, rod-margin interpolation, flat-target vs slope equivalence, friction decomposition (Chrono L1 normal
    along the floor normal vs the reduced plant's axial normal).

Run (project root):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_target_envelope.py            (all, ~3-6 min)
  ... run_target_envelope.py --stage report                                                     (figure from JSON)
Outputs: 06_analysis/00_dynamics/target_envelope.json, target_envelope.png
Units: SI internally; deg / mm / kN only in outputs.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "00_cad"))
import dyn_model as dm  # noqa: E402
import leg_rod_lateral_check as lrc  # noqa: E402  (pure numpy / scipy; beam model of the rod check)

ROOT = dm.PROJECT_ROOT
OUT_DIR = ROOT / "06_analysis" / "00_dynamics"
OUT_JSON = OUT_DIR / "target_envelope.json"
OUT_PNG = OUT_DIR / "target_envelope.png"
PTC_JSON = OUT_DIR / "pad_tangential_check.json"
LEGS = dm.LEG_NAMES
DEG = math.pi / 180.0

# ---------------------------------------------------------------------------------------------------- assumptions
ASSUMPTIONS = {
    "stroke_margin_variants_m": [0.0, 0.010],   # ASSUMPTION: 10 mm headroom for twist trim, probe (+2 mm),
                                                # re-anchoring (<= 2.9 mm), F_s hysteresis; C2 clips at s_max - 0.1 mm
    "clearance_variants_m": [0.0, 0.020, 0.050],  # task: 0 / 20 / 50 mm (C2 heave target 50 mm = YAML)
    "F_guard_margin_N": 5000.0,                 # C2 guard threshold F_min + 5 kN (variant)
    "force_upper_N": None,                      # filled: actuator.max_force_extend_N (210 bar, moving)
    "touchdown_pose": "settled on the crawler (layout D, dyn_model.static_unilateral), pads stick at first touch",
    "tangential_compliance": "rod lateral (perpendicular to the leg axis) k_t = series(swivel cantilever, concrete); "
                             "'yaml' = L1 kt_per_pad (upper bound), 'ext' = secant k_t(e) (best estimate)",
    "friction_mu": None,                        # filled: contact.rigid_floor.friction (static = kinetic)
    "rod_check_criterion": "SF_rod_yield >= 1.5 with (secant k_t, C45 305 MPa) and (YAML k_t, 20MnV6 450 MPa), "
                           "same pair as the D8 provisional limit decision (leg_rod_lateral_check.md 1.3)",
    "quasi_static": "no dynamic overshoot (levelling dynamic max is +1.6 kN over the end value, 3.10.5)",
    "no_reanchoring": "values are levelling-end values without the H4 re-anchoring action",
    "rigid_mast_rigid_body": True,
}

GRID_ROLL = np.round(np.arange(-8.0, 8.0 + 1e-9, 0.25), 4)
GRID_PITCH = np.round(np.arange(-5.0, 5.0 + 1e-9, 0.25), 4)
USER_BOX = {"roll_deg": 6.0, "pitch_deg": 3.0}


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def floor_normal(roll_deg, pitch_deg):
    """run_control_comparison.Plant convention: plane z = sx x + sy y, sx = -tan(pitch), sy = tan(roll)."""
    sx = -math.tan(math.radians(pitch_deg)); sy = math.tan(math.radians(roll_deg))
    n = np.array([-sx, -sy, 1.0])
    return n / np.linalg.norm(n)


def att_rot(roll_deg, pitch_deg, psi=0.0):
    return _rz(psi) @ _ry(math.radians(pitch_deg)) @ _rx(math.radians(roll_deg))


# ---------------------------------------------------------------------------------------------------- context
class Ctx:
    def __init__(self):
        p = dm.load_params()
        self.p = p
        geo = dm.geometry_from_params(p)
        self.geo = geo
        self.g = geo.g
        self.hb = float(p["legs"]["FL"]["pad"]["swivel_center_above_pad_bottom_m"])
        self.swivel_max = float(p["legs"]["FL"]["pad"]["swivel_tilt_range_deg"])
        self.stroke = float(p["actuator"]["stroke_m"])
        self.F_up = float(p["actuator"]["max_force_extend_N"])
        self.F_min = float(p["control"]["F_min_cylinder_N"])
        self.mu = float(p["contact"]["rigid_floor"]["friction"])
        ASSUMPTIONS["force_upper_N"] = self.F_up
        ASSUMPTIONS["friction_mu"] = self.mu
        self.kc = float(p["contact"]["rigid_floor"]["concrete"]["k_N_m"])
        self.k_frame = float(p["actuator"]["frame_stiffness_N_m"])
        self.k_rod = dm.k_rod()
        L1 = p["contact"]["rigid_floor"]["L1"]
        self.kt_yaml = np.array([L1["kt_per_pad_N_m"][n] for n in LEGS], float)
        self.b0 = np.column_stack([geo.pad_xy, geo.pad_z_retracted])          # pad bottom, retracted, body
        self.a0 = self.b0 + np.array([0.0, 0.0, self.hb])                      # ball centre, retracted, body
        (x0, x1), (y0, y1) = geo.crawler_xy_box
        zc = geo.crawler_bottom_z
        self.box = np.array([[x, y, zc] for x in (x0, x1) for y in (y0, y1)])
        lay = p["contact"]["crawler"]["sphere_layout"]
        yt = float(lay["track_centre_y_m"])
        import json as _j
        cs = _j.load(open(ROOT / "01_cad" / "06_brep" / "derived" / "crawler" / "crawler_summary.json", encoding="utf-8"))
        self.shoe_w = float(cs["comparison_with_previous_review"]["now_shoe_ground_width_m"])  # 0.422 m (B-rep)
        xs = [(float(x), 0.0) for x in lay["roller_x_m"]] + list(zip(map(float, lay["end_shoe_x_m"]),
                                                                    map(float, lay["end_shoe_gap_m"])))
        pts = []
        for x, gap in xs:
            for yc in (yt, -yt):
                for dy in (-self.shoe_w / 2, self.shoe_w / 2):
                    pts.append([x, yc + dy, zc + gap])
        self.phys = np.array(pts)
        self.tw = dm.twist_vector(geo.pad_xy)
        self.m_rod = geo.rod_mass.copy()
        # bodies
        self.body = {lv: dm.body_from_params(p, lv) for lv in dm.LEVELS}
        self.static_yaml = {lv: np.array([p["superstructure"]["auger_levels"][lv]["static_leg_loads_N"][n] for n in LEGS])
                            for lv in dm.LEVELS}
        # interpolation tables in the extension (secant k_t, rod beam data)
        self.e_tab = np.linspace(0.0, 0.75, 151)
        self.klat_tab = np.array([dm.k_leg_lateral_legs(geo, e, guided_tip=False) for e in self.e_tab])   # (151,4)
        self.rodg = lrc.leg_geometry(p)
        rows = []
        for e in self.e_tab:
            r = []
            for leg in LEGS:
                c = lrc.leg_case(self.rodg[leg], p, float(e), 1.0, 0.0, "swivel", 305e6)
                r.append([c["lever_gland_centre_m"], c["tip_deflection_m"], c["imperfection_m"], c["P_euler_sway_N"]])
            rows.append(r)
        self.rod_tab = np.array(rows)   # (151, 4, 4): a_c, flex [m/N], e0, P_E
        D = float(p["actuator"]["rod_diameter_m"])
        self.A_r, _, self.Z_r = lrc.sec_rod(D)
        self.rod_sy = lrc.ASSUMPTIONS["rod_yield_Pa"]

    # -------- stiffness helpers
    def kt_ext(self, e):
        kl = np.array([np.interp(e[i], self.e_tab, self.klat_tab[:, i]) for i in range(4)])
        return dm.series(kl, self.kc)

    def k_ax_motor(self, e):
        return dm.series(dm.k_oil(e), self.k_rod, self.k_frame, self.kc)

    def k_ax_piston(self, e):
        return dm.series(self.k_rod, self.k_frame, self.kc) * np.ones(4)

    def rod_SF(self, e, F, P, sy):
        """leg_rod_lateral_check.leg_case SF_rod_yield from interpolated beam data (affine in F at fixed P, e)."""
        out = np.zeros(4)
        for i in range(4):
            a_c, flex, e0, PE = (np.interp(e[i], self.e_tab, self.rod_tab[:, i, j]) for j in range(4))
            AF = 1.0 / (1.0 - P[i] / PE)
            M = (abs(F[i]) * a_c + P[i] * (abs(F[i]) * flex + e0)) * AF
            out[i] = sy / (P[i] / self.A_r + M / self.Z_r)
        return out

    # -------- touchdown anchors
    def touch(self, level, roll_g, pitch_g, settle=True):
        geo = self.geo
        n = floor_normal(roll_g, pitch_g)
        phi = math.asin(-n[1]); th = math.atan2(n[0], n[2])
        R = _ry(th) @ _rx(phi)
        qs = np.zeros(3)
        if settle:
            e_op = geo.touch_extension + 0.05
            body = dm.body_with_rods(self.p, geo, level, e_op)
            cxy, kcr, _ = dm.crawler_points(self.p)
            cgap = dm.crawler_gaps(self.p)
            _, qs, _ = dm.static_unilateral(cxy, kcr, -cgap, body.mass * geo.g, body.com[:2])
            R = R @ (_ry(qs[2]) @ _rx(qs[1]))
        O = n * (-geo.crawler_bottom_z + qs[0])
        ez = R[:, 2]
        e_t = np.array([n @ (O + R @ self.b0[i]) / (n @ ez) for i in range(4)])
        anc = np.array([O + R @ (self.b0[i] - np.array([0, 0, e_t[i]])) for i in range(4)])
        return n, anc, O, e_t, qs


C = None


def ctx() -> Ctx:
    global C
    if C is None:
        C = Ctx()
    return C


# ---------------------------------------------------------------------------------------------------- solver
def _kin(c: Ctx, n, Rt, anc, clr, X, Y, psi):
    R = _rz(psi) @ Rt
    a = R[:, 2]
    minc = np.min((R @ c.box.T).T @ n)
    Z = (clr - minc - n[0] * X - n[1] * Y) / n[2]
    O = np.array([X, Y, Z])
    b = anc + c.hb * n                                   # ball centres (held by the stuck pads)
    v = b - O - (R @ c.a0.T).T
    e = -(v @ a)
    d = v + e[:, None] * a[None, :]                      # lateral rod deflection (perp. to a)
    return R, a, O, b, e, d


def solve(c: Ctx, level, n, Rt, anc, clr, kt, tau=0.0, z0=None, tol=1e-7, maxit=30):
    body = c.body[level]
    M = body.mass + c.m_rod.sum()
    W = M * c.g
    ezw = np.array([0.0, 0.0, 1.0])
    rodc0 = c.geo.rod_com_retracted

    def resid(z, need=False):
        X, Y, psi = z[:3]; F = z[3:]
        R, a, O, b, e, d = _kin(c, n, Rt, anc, clr, X, Y, psi)
        L = kt[:, None] * d
        Rf = F[:, None] * a[None, :] + L
        com_b = (body.mass * body.com + (c.m_rod[:, None] * (rodc0 - np.outer(e, [0, 0, 1]))).sum(0)) / M
        cw = O + R @ com_b
        fr = Rf.sum(0) - W * ezw
        mr = np.cross(b - cw, Rf).sum(0)
        Fcyl = F - c.m_rod * c.g * (a @ ezw)
        tr = c.tw @ Fcyl - tau
        r = np.concatenate([fr / 1e4, mr / 1e4, [tr / 1e4]])
        if need:
            return r, dict(R=R, a=a, O=O, b=b, e=e, d=d, L=L, Rf=Rf, cw=cw, Fcyl=Fcyl)
        return r

    if z0 is None:
        z0 = np.concatenate([anc.mean(0)[:2] * 0 + _guess_xy(c, n, Rt, anc, clr), [0.0], np.full(4, W / 4)])
    z = z0.astype(float).copy()
    for it in range(maxit):
        r = resid(z)
        if np.max(np.abs(r)) < tol:
            break
        J = np.zeros((7, 7))
        for j in range(7):
            h = 1e-7 if j < 3 else 1.0
            zp = z.copy(); zp[j] += h
            J[:, j] = (resid(zp) - r) / h
        z = z - np.linalg.solve(J, r)
    r, s = resid(z, True)
    s["z"] = z; s["res_max_N"] = float(np.max(np.abs(r)) * 1e4); s["iters"] = it
    return s


def _guess_xy(c: Ctx, n, Rt, anc, clr):
    """In-plane position that puts the rigid ball positions on average over the anchors (psi 0)."""
    X = Y = 0.0
    for _ in range(3):
        R, a, O, b, e, d = _kin(c, n, Rt, anc, clr, X, Y, 0.0)
        mean_d = d.mean(0)
        X += mean_d[0]; Y += mean_d[1]
    return np.array([X, Y])


def evaluate(level, roll_g, pitch_g, roll_t, pitch_t, clr=0.05, kt_mode="ext", cap=True, settle=True, tau=0.0,
             detail=False):
    c = ctx()
    n, anc0, O_t, e_t, qs = c.touch(level, roll_g, pitch_g, settle)
    Rt = att_rot(roll_t, pitch_t)
    anc = anc0.copy()
    kt = c.kt_yaml.copy()
    s = solve(c, level, n, Rt, anc, clr, kt, tau)
    if kt_mode == "ext":
        for _ in range(3):
            kt = c.kt_ext(s["e"])
            s = solve(c, level, n, Rt, anc, clr, kt, tau, z0=s["z"])
    stick = s
    slip = np.zeros(4, bool)
    nit = 0
    if cap:
        for nit in range(200):
            Nn = s["Rf"] @ n
            T = s["Rf"] - np.outer(Nn, n)
            Tm = np.linalg.norm(T, axis=1)
            over = Tm > c.mu * np.maximum(Nn, 0.0) * (1 + 1e-9) + 1e-6
            if not over.any():
                break
            slip |= over
            for i in np.where(over)[0]:
                Tc = T[i] * (c.mu * max(Nn[i], 0.0) / Tm[i])
                anc[i] = anc[i] + (Tc - T[i]) / kt[i]
            s = solve(c, level, n, Rt, anc, clr, kt, tau, z0=s["z"])
            if kt_mode == "ext":
                kt = c.kt_ext(s["e"])
    R, a = s["R"], s["a"]
    Rf = s["Rf"]
    Nn = Rf @ n
    T = Rf - np.outer(Nn, n)
    F_ax = s["z"][3:]
    Lb = (R.T @ s["L"].T).T                                  # rod lateral in body axes
    e = s["e"]
    s_motor = e + F_ax / c.k_ax_motor(e)
    s_pist = e + F_ax / c.k_ax_piston(e)
    beta = np.degrees(math.acos(min(1.0, float(a @ n)))) * np.ones(4)
    clr_box = float(np.min((R @ c.box.T).T @ n + s["O"] @ n))
    clr_phys = float(np.min((R @ c.phys.T).T @ n + s["O"] @ n))
    Fcyl = s["Fcyl"]
    # twist interval: normal null vector w (sum w = 0, in-plane moments of w n zero)
    bt = s["b"] - s["cw"]
    A3 = np.vstack([np.ones(4), np.cross(bt, n).T])            # 4 x 4 rows (1 + 3 moment comps, 1 is ~0)
    _, _, vt = np.linalg.svd(A3)
    w = vt[-1]
    dF = w * (n @ a)                                         # change of the axial component per unit t
    lo_t, hi_t = -np.inf, np.inf
    out_tw = {}
    for name, Flo in (("Fmin", c.F_min), ("guard", c.F_min + ASSUMPTIONS["F_guard_margin_N"])):
        lo_t, hi_t = -np.inf, np.inf
        for i in range(4):
            if abs(dF[i]) < 1e-12:
                continue
            t1 = (Flo - Fcyl[i]) / dF[i]; t2 = (c.F_up - Fcyl[i]) / dF[i]
            lo_t = max(lo_t, min(t1, t2)); hi_t = min(hi_t, max(t1, t2))
        dtw = c.tw @ dF
        out_tw[name] = sorted([float(lo_t * dtw), float(hi_t * dtw)]) if lo_t <= hi_t else None
    res = {
        "e_m": e, "s_motor_m": s_motor, "s_piston_m": s_pist, "F_cyl_N": Fcyl, "F_ax_N": F_ax, "N_N": Nn,
        "T_N": np.linalg.norm(T, axis=1), "L_N": np.linalg.norm(Lb[:, :2], axis=1), "L_body": Lb,
        "util": np.linalg.norm(T, axis=1) / np.maximum(c.mu * Nn, 1e-9), "slip": slip,
        "stick_L_N": np.linalg.norm((stick["R"].T @ stick["L"].T).T[:, :2], axis=1),
        "beta_deg": beta, "clr_box_m": clr_box, "clr_phys_m": clr_phys, "twist_interval_N": out_tw,
        "res_max_N": s["res_max_N"], "cap_iter": nit, "kt": kt, "yaw_deg": float(s["z"][2] / DEG),
        "twist_N": float(c.tw @ Fcyl), "a_z": float(a[2]), "n_z": float(n[2]),
    }
    if detail:
        res.update(anchors=anc, anchors0=anc0, n=n, R=R, O=s["O"], touch_ext=e_t, settle=qs)
    return res


def rod_margins(c: Ctx, r_yaml, r_ext):
    """SF_rod_yield per leg: (secant, C45), (YAML, 20MnV6), (secant, 20MnV6), (YAML, C45)."""
    sy = c.rod_sy
    out = {}
    for tag, r in (("ext", r_ext), ("yaml", r_yaml)):
        for mat, key in (("C45", "C45_normalised"), ("20MnV6", "20MnV6")):
            out[f"{tag}_{mat}"] = c.rod_SF(r["e_m"], r["L_N"], r["F_ax_N"], sy[key])
    return out


# ---------------------------------------------------------------------------------------------------- grid
CONSTRAINT_ORDER = ["swivel", "stroke_hi", "stroke_lo", "F_min", "F_up", "liftoff"]


def point(level, rg, pg, rt, pt):
    """All quantities for one (floor, target) pair. Returns compact dict of per-constraint margins."""
    c = ctx()
    out = {}
    rr = {}
    for km in ("ext", "yaml"):
        rr[km] = evaluate(level, rg, pg, rt, pt, clr=0.05, kt_mode=km)
    r = rr["ext"]
    # geometry for other clearance targets: the extensions shift by (c - 0.05) / cos(beta) (heave along n)
    shift = r["a_z"] / r["n_z"]                      # de / d(clearance) for a heave along body-frame z
    rm = rod_margins(c, rr["yaml"], rr["ext"])
    out["beta_deg"] = float(r["beta_deg"][0])
    out["s_motor_m"] = r["s_motor_m"].tolist()
    out["s_max_at_clr"] = {f"{int(cl*1000)}": float(np.max(r["s_motor_m"]) + (cl - 0.05) * shift)
                           for cl in ASSUMPTIONS["clearance_variants_m"]}
    out["s_min_at_clr"] = {f"{int(cl*1000)}": float(np.min(r["s_motor_m"]) + (cl - 0.05) * shift)
                           for cl in ASSUMPTIONS["clearance_variants_m"]}
    out["F_cyl_min_N"] = float(np.min(r["F_cyl_N"])); out["F_cyl_max_N"] = float(np.max(r["F_cyl_N"]))
    out["F_cyl_N"] = r["F_cyl_N"].tolist()
    out["N_min_N"] = float(np.min(r["N_N"]))
    out["clr_phys_minus_box_m"] = r["clr_phys_m"] - r["clr_box_m"]
    out["L_ext_N"] = r["L_N"].tolist(); out["L_yaml_N"] = rr["yaml"]["L_N"].tolist()
    out["util_ext_max"] = float(np.max(r["util"])); out["util_yaml_max"] = float(np.max(rr["yaml"]["util"]))
    out["slip_ext"] = bool(r["slip"].any()); out["slip_yaml"] = bool(rr["yaml"]["slip"].any())
    out["stick_yaml_N"] = rr["yaml"]["stick_L_N"].tolist()
    out["rod_SF"] = {k: v.tolist() for k, v in rm.items()}
    out["rod_SF_min"] = {k: float(np.min(v)) for k, v in rm.items()}
    out["twist_interval_N"] = r["twist_interval_N"]
    out["res_max_N"] = max(r["res_max_N"], rr["yaml"]["res_max_N"])
    out["F_cyl_min_yaml_N"] = float(np.min(rr["yaml"]["F_cyl_N"]))
    return out


def feasible(pt, clr_mm=50, margin=0.0, guard=False, rod=False):
    """Return (ok, first violated constraint name)."""
    c = ctx()
    viol = []
    if pt["beta_deg"] > c.swivel_max:
        viol.append("swivel")
    if pt["s_max_at_clr"][str(clr_mm)] > c.stroke - margin:
        viol.append("stroke_hi")
    if pt["s_min_at_clr"][str(clr_mm)] < 0.0 + margin:
        viol.append("stroke_lo")
    Flo = c.F_min + (ASSUMPTIONS["F_guard_margin_N"] if guard else 0.0)
    if min(pt["F_cyl_min_N"], pt["F_cyl_min_yaml_N"]) < Flo:
        viol.append("F_min")
    if pt["F_cyl_max_N"] > c.F_up:
        viol.append("F_up")
    if pt["N_min_N"] <= 0:
        viol.append("liftoff")
    if rod:
        if pt["rod_SF_min"]["ext_C45"] < 1.5 or pt["rod_SF_min"]["yaml_20MnV6"] < 1.5:
            viol.append("rod")
    return (len(viol) == 0), viol


def run_grid(level, rg, pg, rolls=GRID_ROLL, pitches=GRID_PITCH):
    pts = {}
    for pt_ in pitches:
        for rt in rolls:
            pts[f"{rt:+.2f},{pt_:+.2f}"] = point(level, rg, pg, float(rt), float(pt_))
    return pts


def summarize(pts, rolls=GRID_ROLL, pitches=GRID_PITCH):
    """Feasibility maps and axis extents for several criteria sets."""
    crit = {
        "base_c50": dict(clr_mm=50),
        "guard_c50": dict(clr_mm=50, guard=True),
        "guard_c50_m10": dict(clr_mm=50, guard=True, margin=0.010),
        "guard_c20_m10": dict(clr_mm=20, guard=True, margin=0.010),
        "guard_c0_m10": dict(clr_mm=0, guard=True, margin=0.010),
        "rec_c50_m10_rod": dict(clr_mm=50, guard=True, margin=0.010, rod=True),
        "rec_c20_m10_rod": dict(clr_mm=20, guard=True, margin=0.010, rod=True),
        "base_c50_rod": dict(clr_mm=50, rod=True),
    }
    out = {}
    for cname, kw in crit.items():
        okmap = np.zeros((len(pitches), len(rolls)), bool)
        first = np.empty((len(pitches), len(rolls)), object)
        for i, p_ in enumerate(pitches):
            for j, r_ in enumerate(rolls):
                ok, v = feasible(pts[f"{r_:+.2f},{p_:+.2f}"], **kw)
                okmap[i, j] = ok
                first[i, j] = "+".join(v) if v else ""
        # axis extents
        i0 = int(np.argmin(np.abs(pitches))); j0 = int(np.argmin(np.abs(rolls)))
        def ext(arr, vals, k0):
            if not arr[k0]:
                return [None, None]
            lo = k0
            while lo - 1 >= 0 and arr[lo - 1]:
                lo -= 1
            hi = k0
            while hi + 1 < len(arr) and arr[hi + 1]:
                hi += 1
            return [float(vals[lo]), float(vals[hi])]
        # user box check
        inbox = [(i, j) for i, p_ in enumerate(pitches) for j, r_ in enumerate(rolls)
                 if abs(p_) <= USER_BOX["pitch_deg"] + 1e-9 and abs(r_) <= USER_BOX["roll_deg"] + 1e-9]
        fails = [(float(rolls[j]), float(pitches[i]), first[i, j]) for i, j in inbox if not okmap[i, j]]
        reasons = {}
        for _, _, f in fails:
            for k in f.split("+"):
                reasons[k] = reasons.get(k, 0) + 1
        # largest symmetric box (Phi, Theta) fully feasible: for each Theta the max Phi
        pareto = _pareto(okmap)
        corners = {}
        for sr in (1, -1):
            for sp in (1, -1):
                key = f"{sr*USER_BOX['roll_deg']:+.2f},{sp*USER_BOX['pitch_deg']:+.2f}"
                i = int(np.argmin(np.abs(pitches - sp * USER_BOX["pitch_deg"])))
                j = int(np.argmin(np.abs(rolls - sr * USER_BOX["roll_deg"])))
                corners[key] = first[i, j] or "ok"
        out[cname] = {
            "criteria": kw, "ok": okmap.astype(int).tolist(),
            "roll_extent_at_pitch0_deg": ext(okmap[i0, :], rolls, j0),
            "pitch_extent_at_roll0_deg": ext(okmap[:, j0], pitches, i0),
            "user_box_all_ok": len(fails) == 0, "user_box_fail_count": len(fails), "user_box_points": len(inbox),
            "user_box_fail_reasons": reasons, "user_box_corners": corners,
            "max_symmetric_box_Phi_for_Theta": pareto,
        }
    return out


# ---------------------------------------------------------------------------------------------------- checks
def stage_checks():
    c = ctx()
    out = {}
    # C1: flat floor, level target, no settle: F_cyl = YAML equal-stiffness static loads (n^T F = 0 equivalence)
    d = {}
    for lv in dm.LEVELS:
        r = evaluate(lv, 0, 0, 0, 0, kt_mode="yaml", settle=False)
        rel = np.max(np.abs(r["F_cyl_N"] - c.static_yaml[lv]) / c.static_yaml[lv])
        d[lv] = {"F_cyl_kN": (r["F_cyl_N"] / 1e3).round(4).tolist(), "yaml_kN": (c.static_yaml[lv] / 1e3).round(4).tolist(),
                 "rel_max": float(rel), "e_m": r["e_m"].round(6).tolist(), "L_kN_max": float(r["L_N"].max() / 1e3),
                 "res_N": r["res_max_N"]}
    out["C1_level_loads_vs_yaml"] = d
    # C2: levelled extension (target 0) on slopes vs pad_tangential_check kin (5-digit) and dynamics 3.3 table
    ptc = json.load(open(PTC_JSON, encoding="utf-8"))["kin"]
    d = {}
    for key in ("top|V:pitch+3.5", "top|V:pitch-3.5", "top|V:roll+5.5", "top|V:roll-5.5", "top|V:r+p+0.5",
                "top|P:pitch+3.2", "top|P:roll+4.4"):
        tag = key.split("|")[1].split(":")[1]
        rg, pg = _slope_of_tag(key)
        r_y = evaluate("top", rg, pg, 0, 0, kt_mode="yaml", cap=False)
        r_e = evaluate("top", rg, pg, 0, 0, kt_mode="ext", cap=False)
        r_yc = evaluate("top", rg, pg, 0, 0, kt_mode="yaml", cap=True)
        ref = ptc[key]
        d[key] = {"slope_roll_pitch_deg": [rg, pg],
                  "e_geom_m": r_y["e_m"].round(5).tolist(), "ref_levelled_ext_m": ref["yaml"]["levelled_ext_m"],
                  "de_max_mm": float(np.max(np.abs(r_y["e_m"] - np.array(ref["yaml"]["levelled_ext_m"]))) * 1e3),
                  "stick_yaml_kN": (r_y["L_N"] / 1e3).round(2).tolist(), "ref_stick_yaml_kN": ref["yaml"]["stick_kN"],
                  "stick_ext_kN": (r_e["L_N"] / 1e3).round(2).tolist(), "ref_stick_ext_kN": ref["ext"]["stick_kN"],
                  "capped_yaml_kN": (r_yc["L_N"] / 1e3).round(2).tolist(), "ref_capped_yaml_kN": ref["yaml"]["capped_kN"],
                  "slip_yaml": r_yc["slip"].tolist()}
        for a_, b_ in (("stick_yaml_kN", "ref_stick_yaml_kN"), ("stick_ext_kN", "ref_stick_ext_kN"),
                       ("capped_yaml_kN", "ref_capped_yaml_kN")):
            A = np.array(d[key][a_]); B = np.array(d[key][b_])
            d[key][f"{a_}_diff_over_max"] = float(np.max(np.abs(A - B)) / max(np.max(B), 1e-9))
    out["C2_slope_levelling_vs_pad_tangential_kin"] = d
    # C3: geometric levelling limits (no compression, box corners) vs dynamics_model.md 3.3 table
    d = {}
    for clr, ref in ((0.0, {"pitch+": 4.55, "pitch-": 4.41, "roll": 6.97, "diag": 3.90}),
                     (0.05, {"pitch+": 3.86, "pitch-": 3.76, "roll": 5.92, "diag": 3.31})):
        res = {}
        for name, dirv in (("pitch+", (0, 1)), ("pitch-", (0, -1)), ("roll", (1, 0)), ("roll-", (-1, 0)),
                           ("diag", (1 / math.sqrt(2), 1 / math.sqrt(2)))):
            lo, hi = 0.0, 10.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                r = evaluate("top", dirv[0] * mid, dirv[1] * mid, 0, 0, clr=clr, kt_mode="yaml", cap=False, settle=False)
                if np.max(r["e_m"]) <= c.stroke and np.min(r["e_m"]) >= 0:
                    lo = mid
                else:
                    hi = mid
            res[name] = round(lo, 3)
        d[f"clearance_{int(clr*1000)}mm"] = {"this": res, "dynamics_3.3": ref}
    out["C3_geometric_slope_limits_vs_3.3"] = d
    # C4: twist interval end re-solved with the full solver (tau = interval end) gives F_cyl min = bound
    r0 = evaluate("top", 0, 0, 3.0, 2.0, kt_mode="ext", cap=False)
    lo, hi = r0["twist_interval_N"]["Fmin"]
    r1 = evaluate("top", 0, 0, 3.0, 2.0, kt_mode="ext", cap=False, tau=lo)
    r2 = evaluate("top", 0, 0, 3.0, 2.0, kt_mode="ext", cap=False, tau=hi)
    out["C4_twist_interval_resolve"] = {
        "interval_kN": [lo / 1e3, hi / 1e3],
        "F_cyl_at_lo_kN": (r1["F_cyl_N"] / 1e3).round(4).tolist(), "F_cyl_at_hi_kN": (r2["F_cyl_N"] / 1e3).round(4).tolist(),
        "bound_error_N": float(min(abs(np.min(r1["F_cyl_N"]) - c.F_min), abs(np.max(r1["F_cyl_N"]) - c.F_up)) +
                               min(abs(np.min(r2["F_cyl_N"]) - c.F_min), abs(np.max(r2["F_cyl_N"]) - c.F_up)))}
    # C5: rod margin interpolation vs direct leg_case (leg_rod_lateral_check.md 5.1: secant FL e 0.654, 26.6 kN, 119 kN -> 1.48)
    e = np.array([0.654, 0.660, 0.347, 0.3472]); F = np.array([26.6e3, 54.4e3, 36.9e3, 36.3e3]); P = np.array([119e3, 120e3, 74e3, 72e3])
    interp = c.rod_SF(e, F, P, 305e6)
    direct = np.array([lrc.leg_case(c.rodg[LEGS[i]], c.p, float(e[i]), float(F[i]), float(P[i]), "swivel", 305e6)["SF_rod_yield"]
                       for i in range(4)])
    out["C5_rod_SF_interp_vs_direct"] = {"interp": interp.round(4).tolist(), "direct": direct.round(4).tolist(),
                                         "rel_max": float(np.max(np.abs(interp / direct - 1))),
                                         "doc_5.1_FL_secant_C45": 1.48}
    # C6: equilibrium residual and twist definition (twist vector)
    out["C6_twist_vector"] = c.tw.round(4).tolist()
    # C7: flat-floor target = slope levelling equivalence (relative rotation): target pitch -3.5 on flat vs slope +3.5 levelled
    a = evaluate("top", 0, 0, 0, -3.5, kt_mode="ext", cap=False, settle=False)
    b = evaluate("top", 0, 3.5, 0, 0, kt_mode="ext", cap=False, settle=False)
    out["C7_flat_target_vs_slope_levelled"] = {
        "flat_target_pitch-3.5": {"e_mm": (a["e_m"] * 1e3).round(2).tolist(), "L_kN": (a["L_N"] / 1e3).round(2).tolist(),
                                  "F_cyl_kN": (a["F_cyl_N"] / 1e3).round(2).tolist()},
        "slope_pitch+3.5_level": {"e_mm": (b["e_m"] * 1e3).round(2).tolist(), "L_kN": (b["L_N"] / 1e3).round(2).tolist(),
                                  "F_cyl_kN": (b["F_cyl_N"] / 1e3).round(2).tolist()}}
    # C8: pad friction demand, Chrono L1 decomposition (N = R.n, T = R - N n) vs the reduced plant
    #     (run_control_comparison: normal force along the leg axis, cap applies to the bushing force only)
    d = {}
    for tag, (rg, pg) in (("slope_pitch+3.5", (0.0, 3.5)), ("slope_pitch-3.5", (0.0, -3.5)), ("slope_roll+5.5", (5.5, 0.0))):
        r = evaluate("top", rg, pg, 0, 0, kt_mode="yaml", cap=False, detail=True)
        n = r["n"]; a = r["R"][:, 2]
        Rf = r["F_ax_N"][:, None] * a[None, :] + (r["R"] @ r["L_body"].T).T
        N = Rf @ n; T = np.linalg.norm(Rf - np.outer(N, n), axis=1)
        N2 = r["F_ax_N"] * (a @ n); T2 = r["L_N"]
        d[tag] = {"chrono_style_T_over_muN": (T / (c.mu * N)).round(3).tolist(),
                  "reduced_plant_style_T_over_muN": (T2 / (c.mu * N2)).round(3).tolist(),
                  "T_kN": (T / 1e3).round(2).tolist(), "L_kN": (T2 / 1e3).round(2).tolist()}
    out["C8_friction_decomposition"] = d
    return out


def _slope_of_tag(key):
    tag = key.split("|")[1]
    rng, s = tag.split(":")
    Phi, Theta = (5.5, 3.5) if rng == "V" else (4.4, 3.2)
    if s.startswith("pitch"):
        return 0.0, float(s[5:])
    if s.startswith("roll"):
        return float(s[4:]), 0.0
    # r+p+0.5 style: quadrant signs and fraction s of the diamond (roll = s Phi, pitch = (1-s) Theta)
    sr = 1 if s[1] == "+" else -1
    sp = 1 if s[3] == "+" else -1
    f = float(s[4:])
    return sr * f * Phi, sp * (1 - f) * Theta


# ---------------------------------------------------------------------------------------------------- main
FLOORS = {
    "flat": (0.0, 0.0),
    "P:pitch+3.2": (0.0, 3.2), "P:pitch-3.2": (0.0, -3.2), "P:roll+4.4": (4.4, 0.0), "P:roll-4.4": (-4.4, 0.0),
    "P:diag++": (2.2, 1.6), "P:diag+-": (2.2, -1.6), "P:diag-+": (-2.2, 1.6), "P:diag--": (-2.2, -1.6),
    "V:pitch+3.5": (0.0, 3.5), "V:pitch-3.5": (0.0, -3.5), "V:roll+5.5": (5.5, 0.0), "V:roll-5.5": (-5.5, 0.0),
}


WORKERS = 10


def _grid_job(job):
    lv, fk = job
    rg, pg = FLOORS[fk]
    return f"{lv}|{fk}", run_grid(lv, rg, pg)


def stage_main():
    t0 = time.time()
    out = {"meta": {"script": "04_scripts/01_dynamics/run_target_envelope.py", "assumptions": ASSUMPTIONS,
                    "grid_roll_deg": GRID_ROLL.tolist(), "grid_pitch_deg": GRID_PITCH.tolist(), "user_box": USER_BOX,
                    "conventions": "body x fwd, y left, z up; target R = Ry(theta) Rx(phi) (ZYX, yaw free); roll > 0 "
                                   "left up, pitch > 0 nose down; floor slope (phi_g, theta_g) = plane z = -tan(theta_g) x "
                                   "+ tan(phi_g) y (attitude on the crawler); forces kN, strokes m (motor coordinate)",
                    "F_min_N": ctx().F_min, "F_up_N": ctx().F_up, "stroke_m": ctx().stroke,
                    "swivel_max_deg": ctx().swivel_max}}
    out["checks"] = stage_checks()
    print(f"checks done {time.time()-t0:.1f} s", flush=True)
    jobs = [(lv, "flat") for lv in dm.LEVELS] + [("top", fk) for fk in FLOORS if fk != "flat"]
    jobs += [(lv, fk) for lv in ("middle", "bottom") for fk in ("P:pitch+3.2", "P:pitch-3.2", "P:roll+4.4", "P:roll-4.4")]
    import multiprocessing as mp
    grids = {}
    with mp.get_context("spawn").Pool(min(WORKERS, len(jobs))) as pool:
        for key, pts in pool.imap_unordered(_grid_job, jobs):
            grids[key] = pts
            print(f"{key} {time.time()-t0:.1f} s", flush=True)
    grids = {f"{lv}|{fk}": grids[f"{lv}|{fk}"] for lv, fk in jobs}
    out["summary"] = {k: summarize(v) for k, v in grids.items()}
    # intersection over the operating diamond (top + middle/bottom vertices) and over the verification vertices
    def inter(keys, cname):
        ok = None
        for k in keys:
            m = np.array(out["summary"][k][cname]["ok"], bool)
            ok = m if ok is None else (ok & m)
        return ok
    inter_sets = {
        "operating_P_all": [k for k in out["summary"] if "|P:" in k or k.endswith("|flat")],
        "verification_V_top": [k for k in out["summary"] if k.startswith("top|V:") or k == "top|flat"],
        "flat_all_levels": [f"{lv}|flat" for lv in dm.LEVELS],
    }
    out["intersection"] = {}
    for iname, keys in inter_sets.items():
        out["intersection"][iname] = {"floors": keys}
        for cname in out["summary"]["top|flat"]:
            ok = inter(keys, cname)
            out["intersection"][iname][cname] = _box_stats(ok)
    # compact per-point tables at the user-box corners / edges for the report
    out["user_box_points"] = {}
    for k, g in grids.items():
        tab = {}
        for key in ("+6.00,+3.00", "+6.00,-3.00", "-6.00,+3.00", "-6.00,-3.00", "+6.00,+0.00", "-6.00,+0.00",
                    "+0.00,+3.00", "+0.00,-3.00", "+0.00,+0.00"):
            ptd = g[key]
            tab[key] = {"s_max_mm@c50": round(ptd["s_max_at_clr"]["50"] * 1e3, 1),
                        "s_max_mm@c20": round(ptd["s_max_at_clr"]["20"] * 1e3, 1),
                        "s_max_mm@c0": round(ptd["s_max_at_clr"]["0"] * 1e3, 1),
                        "s_min_mm@c50": round(ptd["s_min_at_clr"]["50"] * 1e3, 1),
                        "F_cyl_kN": [round(x / 1e3, 1) for x in ptd["F_cyl_N"]],
                        "beta_deg": round(ptd["beta_deg"], 2),
                        "L_ext_kN": [round(x / 1e3, 1) for x in ptd["L_ext_N"]],
                        "L_yaml_kN": [round(x / 1e3, 1) for x in ptd["L_yaml_N"]],
                        "slip_yaml": ptd["slip_yaml"], "util_yaml_max": round(ptd["util_yaml_max"], 3),
                        "rod_SF_min": {kk: round(v, 2) for kk, v in ptd["rod_SF_min"].items()},
                        "twist_interval_guard_kN": None if ptd["twist_interval_N"]["guard"] is None else
                        [round(x / 1e3, 1) for x in ptd["twist_interval_N"]["guard"]],
                        "clr_phys_minus_box_mm": round(ptd["clr_phys_minus_box_m"] * 1e3, 1)}
            tab[key]["s_motor_mm"] = [round(x * 1e3, 1) for x in ptd["s_motor_m"]]
        out["user_box_points"][k] = tab
    out["max_residual_N"] = max(p_["res_max_N"] for g in grids.values() for p_ in g.values())
    out["meta"]["runtime_s"] = time.time() - t0
    # store compact maps for the figure (first-violation codes for 'base_c50' and rod indicator)
    out["maps"] = {}
    for k, g in grids.items():
        smax50 = np.array([[g[f"{r:+.2f},{p:+.2f}"]["s_max_at_clr"]["50"] for r in GRID_ROLL] for p in GRID_PITCH])
        smax20 = np.array([[g[f"{r:+.2f},{p:+.2f}"]["s_max_at_clr"]["20"] for r in GRID_ROLL] for p in GRID_PITCH])
        smax0 = np.array([[g[f"{r:+.2f},{p:+.2f}"]["s_max_at_clr"]["0"] for r in GRID_ROLL] for p in GRID_PITCH])
        fmin = np.array([[min(g[f"{r:+.2f},{p:+.2f}"]["F_cyl_min_N"], g[f"{r:+.2f},{p:+.2f}"]["F_cyl_min_yaml_N"])
                          for r in GRID_ROLL] for p in GRID_PITCH])
        beta = np.array([[g[f"{r:+.2f},{p:+.2f}"]["beta_deg"] for r in GRID_ROLL] for p in GRID_PITCH])
        rodE = np.array([[g[f"{r:+.2f},{p:+.2f}"]["rod_SF_min"]["ext_C45"] for r in GRID_ROLL] for p in GRID_PITCH])
        rodY = np.array([[g[f"{r:+.2f},{p:+.2f}"]["rod_SF_min"]["yaml_20MnV6"] for r in GRID_ROLL] for p in GRID_PITCH])
        rodYC = np.array([[g[f"{r:+.2f},{p:+.2f}"]["rod_SF_min"]["yaml_C45"] for r in GRID_ROLL] for p in GRID_PITCH])
        fmax = np.array([[g[f"{r:+.2f},{p:+.2f}"]["F_cyl_max_N"] for r in GRID_ROLL] for p in GRID_PITCH])
        uE = np.array([[g[f"{r:+.2f},{p:+.2f}"]["util_ext_max"] for r in GRID_ROLL] for p in GRID_PITCH])
        uY = np.array([[g[f"{r:+.2f},{p:+.2f}"]["util_yaml_max"] for r in GRID_ROLL] for p in GRID_PITCH])
        twl = np.array([[np.nan if g[f"{r:+.2f},{p:+.2f}"]["twist_interval_N"]["guard"] is None else
                         min(-g[f"{r:+.2f},{p:+.2f}"]["twist_interval_N"]["guard"][0],
                             g[f"{r:+.2f},{p:+.2f}"]["twist_interval_N"]["guard"][1]) for r in GRID_ROLL] for p in GRID_PITCH])
        out["maps"][k] = {"util_ext": uE.round(4).tolist(), "util_yaml": uY.round(4).tolist(),
                          "twist_half_width_guard_N": np.nan_to_num(twl, nan=-1.0).round(0).tolist(),"s_max_c50_m": smax50.round(5).tolist(), "s_max_c20_m": smax20.round(5).tolist(),
                          "s_max_c0_m": smax0.round(5).tolist(), "F_cyl_min_N": fmin.round(1).tolist(),
                          "F_cyl_max_N": fmax.round(1).tolist(), "beta_deg": beta.round(4).tolist(),
                          "rod_SF_ext_C45": rodE.round(4).tolist(), "rod_SF_yaml_20MnV6": rodY.round(4).tolist(),
                          "rod_SF_yaml_C45": rodYC.round(4).tolist()}
    out["rules"] = rule_check(out)
    return out


RULES = {
    # name: (relative diamond (Phi, Theta+, Theta-) on target - floor attitude, absolute diamond (Phi, Theta) or None)
    "R_geom_c50_m10": ((5.5, 3.5, 3.5), None),          # stroke / clearance / F guard only (no rod criterion)
    "R_geom_c50_m0": ((5.79, 3.70, 3.75), None),        # fitted c50 stroke boundary on the flat floor, no margin
    "R_rec_rel44_32_abs44_32": ((4.4, 3.2, 3.2), (4.4, 3.2)),   # recommended (rod criterion of the D8 decision)
    "R_rel44_32_only": ((4.4, 3.2, 3.2), None),
    "R_rel55_35_abs44_32": ((5.5, 3.5, 3.5), (4.4, 3.2)),
}


def rule_mask(rg, pg, rel, ab, rolls=GRID_ROLL, pitches=GRID_PITCH):
    RR, PP = np.meshgrid(rolls, pitches)
    dr, dp = RR - rg, PP - pg
    T = np.where(dp >= 0, rel[1], rel[2])
    m = np.abs(dr) / rel[0] + np.abs(dp) / T <= 1 + 1e-9
    if ab is not None:
        m &= np.abs(RR) / ab[0] + np.abs(PP) / ab[1] <= 1 + 1e-9
    return m


def rule_check(out):
    """Accepted-but-infeasible count of each candidate acceptance rule on every computed floor / level."""
    res = {"note": "relative diamond |phi_t-phi_g|/Phi + |theta_t-theta_g|/Theta(sign) <= 1 and optional absolute "
                   "diamond |phi_t|/Phi_a + |theta_t|/Theta_a <= 1; grid 0.25 deg"}
    for rn, (rel, ab) in RULES.items():
        d = {"relative": rel, "absolute": ab}
        for cname in ("base_c50", "guard_c50_m10", "rec_c50_m10_rod"):
            acc = bad = 0
            where = []
            for key, summ in out["summary"].items():
                rg, pg = FLOORS[key.split("|", 1)[1]]
                m = rule_mask(rg, pg, rel, ab)
                ok = np.array(summ[cname]["ok"], bool)
                acc += int(m.sum()); b = m & ~ok; bad += int(b.sum())
                if b.any():
                    i, j = np.argwhere(b)[0]
                    where.append([key, int(b.sum()), float(GRID_ROLL[j]), float(GRID_PITCH[i])])
            d[cname] = {"accepted": acc, "accepted_infeasible": bad, "first_cases": where[:6]}
        # worst indicators inside the accepted set
        uY = uE = 0.0; rodE = rodY = 99.0; fmin = 1e9; smax = 0.0
        for key, m_ in out["maps"].items():
            rg, pg = FLOORS[key.split("|", 1)[1]]
            m = rule_mask(rg, pg, rel, ab)
            if not m.any():
                continue
            uY = max(uY, float(np.array(m_["util_yaml"])[m].max())); uE = max(uE, float(np.array(m_["util_ext"])[m].max()))
            rodE = min(rodE, float(np.array(m_["rod_SF_ext_C45"])[m].min()))
            rodY = min(rodY, float(np.array(m_["rod_SF_yaml_20MnV6"])[m].min()))
            fmin = min(fmin, float(np.array(m_["F_cyl_min_N"])[m].min())); smax = max(smax, float(np.array(m_["s_max_c50_m"])[m].max()))
        d["worst_in_accepted"] = {"util_yaml_max": uY, "util_ext_max": uE, "rod_SF_ext_C45_min": rodE,
                                  "rod_SF_yaml_20MnV6_min": rodY, "F_cyl_min_kN": fmin / 1e3, "s_max_c50_mm": smax * 1e3}
        res[rn] = d
    return res


def _pareto(ok):
    """For each symmetric pitch half-range Theta, the largest symmetric roll half-range Phi with every grid point of
    the box |pitch| <= Theta, |roll| <= Phi feasible (None if even Phi = 0 fails)."""
    aP, aR = np.abs(GRID_PITCH), np.abs(GRID_ROLL)
    out = []
    for th in np.arange(0.0, 5.0 + 1e-9, 0.25):
        best = None
        for ph in np.arange(0.0, 8.0 + 1e-9, 0.25):
            m = (aP <= th + 1e-9)[:, None] & (aR <= ph + 1e-9)[None, :]
            if ok[m].all():
                best = float(ph)
            else:
                break
        out.append([float(th), best])
    return out


def _box_stats(ok):
    rolls, pitches = GRID_ROLL, GRID_PITCH
    i0 = int(np.argmin(np.abs(pitches))); j0 = int(np.argmin(np.abs(rolls)))
    inbox = [(i, j) for i, p_ in enumerate(pitches) for j, r_ in enumerate(rolls)
             if abs(p_) <= USER_BOX["pitch_deg"] + 1e-9 and abs(r_) <= USER_BOX["roll_deg"] + 1e-9]
    pareto = _pareto(ok)
    row = ok[i0, :]; col = ok[:, j0]
    return {"ok": ok.astype(int).tolist(), "user_box_all_ok": bool(all(ok[i, j] for i, j in inbox)),
            "user_box_fail_count": int(sum(not ok[i, j] for i, j in inbox)),
            "roll_ok_at_pitch0": [float(rolls[j]) for j in range(len(rolls)) if row[j]][:1] +
                                 [float(rolls[j]) for j in range(len(rolls)) if row[j]][-1:],
            "pitch_ok_at_roll0": [float(pitches[i]) for i in range(len(pitches)) if col[i]][:1] +
                                 [float(pitches[i]) for i in range(len(pitches)) if col[i]][-1:],
            "max_symmetric_box_Phi_for_Theta": pareto}


# ---------------------------------------------------------------------------------------------------- figure
def figure(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch, Rectangle
    for fam in ("Malgun Gothic",):
        matplotlib.rcParams["font.family"] = fam
    matplotlib.rcParams["axes.unicode_minus"] = False
    R, P = np.array(d["meta"]["grid_roll_deg"]), np.array(d["meta"]["grid_pitch_deg"])
    Fmin = d["meta"]["F_min_N"]; Fup = d["meta"]["F_up_N"]; smax = d["meta"]["stroke_m"]; bmax = d["meta"]["swivel_max_deg"]
    panels = [("top|flat", "평지, 상단"), ("middle|flat", "평지, 중단"), ("bottom|flat", "평지, 하단"),
              ("top|P:pitch+3.2", "앞내림 3.2°, 상단"), ("top|P:pitch-3.2", "앞들림 3.2°, 상단"),
              ("top|P:roll+4.4", "좌측 높음 roll +4.4°, 상단"), ("top|P:roll-4.4", "roll -4.4°, 상단"),
              ("top|P:diag++", "대각 (+2.2°, +1.6°), 상단"), ("top|V:pitch+3.5", "앞내림 3.5° (검증), 상단")]
    # codes: 0 ok, 1 rod only (indicator), 2 stroke c50, 3 F_min(+5), 4 swivel, 5 F_up
    cmap = ListedColormap(["#d9f0d3", "#fdd49e", "#9ecae1", "#fb6a4a", "#9e9ac8", "#636363"])
    fig, axs = plt.subplots(3, 3, figsize=(16.5, 13.5), sharex=True, sharey=True)
    for ax, (k, title) in zip(axs.ravel(), panels):
        m = d["maps"][k]
        s50 = np.array(m["s_max_c50_m"]); s20 = np.array(m["s_max_c20_m"]); s0 = np.array(m["s_max_c0_m"])
        fmn = np.array(m["F_cyl_min_N"]); fmx = np.array(m["F_cyl_max_N"]); be = np.array(m["beta_deg"])
        rodE = np.array(m["rod_SF_ext_C45"]); rodY = np.array(m["rod_SF_yaml_20MnV6"])
        code = np.zeros_like(s50, int)
        rodbad = (rodE < 1.5) | (rodY < 1.5)
        code[rodbad] = 1
        code[s50 > smax] = 2
        code[fmn < Fmin + 5000] = 3
        code[be > bmax] = 4
        code[fmx > Fup] = 5
        ax.pcolormesh(R, P, code, cmap=cmap, vmin=-0.5, vmax=5.5, shading="nearest")
        ax.contour(R, P, s50 - smax, [0], colors="#08519c", linewidths=1.6)
        ax.contour(R, P, s20 - smax, [0], colors="#08519c", linewidths=1.0, linestyles="--")
        ax.contour(R, P, s0 - smax, [0], colors="#08519c", linewidths=1.0, linestyles=":")
        ax.contour(R, P, s50 - (smax - 0.010), [0], colors="#6baed6", linewidths=0.9)
        ax.contour(R, P, rodE, [1.5], colors="#d94801", linewidths=1.3)
        ax.contour(R, P, rodY, [1.5], colors="#d94801", linewidths=1.0, linestyles="--")
        ax.contour(R, P, fmn - Fmin, [0], colors="#a50f15", linewidths=1.3)
        ax.add_patch(Rectangle((-6, -3), 12, 6, fill=False, ec="k", lw=2.0))
        fk = k.split("|", 1)[1]
        rg, pg = FLOORS[fk]
        for rn, col, ls in (("R_rec_rel44_32_abs44_32", "#006d2c", "-"), ("R_geom_c50_m10", "#54278f", "--")):
            rel, ab = RULES[rn]
            fr, fp = np.linspace(R[0], R[-1], 801), np.linspace(P[0], P[-1], 501)
            ax.contour(fr, fp, rule_mask(rg, pg, rel, ab, fr, fp).astype(float), [0.5], colors=col, linewidths=2.0,
                       linestyles=ls)
        ax.axhline(0, color="grey", lw=0.5); ax.axvline(0, color="grey", lw=0.5)
        ax.set_title(title, fontsize=11)
        ax.grid(alpha=0.25)
    for ax in axs[-1]:
        ax.set_xlabel("목표 roll φ_t [deg] (+ = 좌측 위)")
    for ax in axs[:, 0]:
        ax.set_ylabel("목표 pitch θ_t [deg] (+ = 앞내림)")
    handles = [Patch(fc="#d9f0d3", label="도달 가능(크롤러 50 mm, s ≤ 680 mm, F ≥ F_min+5 kN, 스위블, 218 kN) + 로드 1.5 충족"),
               Patch(fc="#fdd49e", label="도달 가능, 로드 굽힘 여유 < 1.5 (할선·C45 또는 YAML·20MnV6)"),
               Patch(fc="#9ecae1", label="불가: 스트로크 끝(크롤러 여유 50 mm)"),
               Patch(fc="#fb6a4a", label="불가: F_cyl < F_min + 5 kN"),
               Patch(fc="#9e9ac8", label="불가: 스위블 > 10°"),
               Patch(fc="#636363", label="불가: F_cyl > 218 kN"),
               plt.Line2D([], [], color="#08519c", lw=1.6, label="스트로크 680 mm 경계: 실선 50 / 파선 20 / 점선 0 mm 여유"),
               plt.Line2D([], [], color="#6baed6", lw=0.9, label="스트로크 670 mm(마진 10 mm, 50 mm 여유)"),
               plt.Line2D([], [], color="#d94801", lw=1.3, label="로드 여유 1.5: 실선 할선·C45 / 파선 YAML·20MnV6"),
               plt.Line2D([], [], color="#a50f15", lw=1.3, label="F_cyl = F_min (9.45 kN)"),
               Patch(fc="none", ec="k", lw=2, label="사용자 잠정 범위 roll ±6°, pitch ±3°"),
               plt.Line2D([], [], color="#006d2c", lw=2, label="권고 규칙: |Δφ|/4.4+|Δθ|/3.2 ≤ 1 그리고 |φ_t|/4.4+|θ_t|/3.2 ≤ 1 (Δ = 목표 - 지면)"),
               plt.Line2D([], [], color="#54278f", lw=2, ls="--", label="기하 규칙(로드 제외): |Δφ|/5.5+|Δθ|/3.5 ≤ 1")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("데크 roll·pitch 목표 도달 포락선 (준정적, 비틀림 n^T P = 0, 고착 패드, 재설정 동작 없음)", fontsize=13)
    fig.tight_layout(rect=(0, 0.10, 1, 0.97))
    fig.savefig(OUT_PNG, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "checks", "report"])
    a = ap.parse_args()
    if a.stage == "checks":
        print(json.dumps(stage_checks(), indent=1, default=float))
        return
    if a.stage == "all":
        d = stage_main()
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=0, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o))
    d = json.load(open(OUT_JSON, encoding="utf-8"))
    figure(d)
    print("wrote", OUT_JSON, OUT_PNG)


if __name__ == "__main__":
    main()
