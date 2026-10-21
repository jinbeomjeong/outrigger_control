"""Independent checks for the C7/C8 crawler-contact judgements before S9 (dynamics_model.md 3.11, rev. 20).

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_crawler_contact_check.py
Writes 06_analysis/00_dynamics/crawler_contact_check.json (about 1-3 min).

Part A - rigid floor, layout D end-roller load point and track phase (judgement 1).
    Variants of the 24-sphere crawler layout (YAML contact.crawler.sphere_layout = D):
      D    YAML as is (reference)
      J    end-roller springs moved to the nearest track joint of the CAD track phase
           (x -0.8763 / +0.8617 m, crawler_ground_sheet.json rollers.roller_to_shoe_left), end shoes as D
      H    track phase shifted by half a pitch (86.6 mm): end rollers sit on flat shoes (load under the roller
           axis, as D) and the raised end shoes move half a pitch outwards with the same gaps (ASSUMPTION:
           free span shape fixed relative to the hinge joint)
      each also with kn_total x3 (YAML kn_total_sensitivity_range_N_m).
    For each: exact-geometry static settle on the crawler (legs at 0, P-delta), 6-DoF crawler modes about it
    (world-axis inertia, same model as run_s2b_crawler_check part B), settle length ln(100) tau_max,
    V4 damped vertical 3-DoF touch / crawler-off times (copy of run_reference.dynamic_touch, step start as
    the V4 reference), post-touch F_min margin and peak pad force, and the nose-down slope that unloads
    the rear roller row (linear statics, CoM lever, crawler tangential held).
Part B - SCM crawler contact shape (judgement 2). A node-wise Bekker (SCM-type) static model of the rigid
    machine on the crawler: soil nodes on a square grid (spacing h, offset o) under the active domain of
    crawler_ground_sheet.json; vertical ray from each node hits the lowest crawler shape surface; sinkage
    s = max(0, -(z0 + h_b(x, y) + y phi - x theta)) (small angles, body = world xy); pressure
    p = (k_c / b + k_phi) s^n with b = 2 A / perimeter of the connected contact patch (Chrono SCM convention,
    to be confirmed in the Chrono source); equilibrium of vertical force and roll/pitch moments.
    Shapes: SPH (the 24 r 0.05 m spheres of D), A (one block-bottom box per shoe, 16 per track),
    B (one flat box per track + 6 end-shoe boxes), C (envelope: one flat box + one inclined ramp box per
    end through the end-shoe gaps). Soils: illustrative Bekker sets (ASSUMPTION, not project soil).
    Grid convergence 40 / 20 / 10 / 5 mm and grid-offset scatter at 20 mm. Validation: shape B flat part on a
    linear Winkler soil vs the closed-form rigid-strip solution.
Inputs: 02_params/rexome33.yaml, 06_analysis/00_dynamics/reference.json,
    01_cad/06_brep/derived/crawler/crawler_ground_sheet.json, crawler_contact_parts.csv (read only). Units SI.
Frames: body axes x forward, y left, z up (CLAUDE.md); pitch > 0 = nose down, roll > 0 = left side up;
    gravity (0, 0, -g) with g from YAML meta.gravity_m_s2.
"""
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve, least_squares

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

T0 = time.perf_counter()
P = dm.load_params(ROOT / "02_params" / "rexome33.yaml")
REF = json.load(open(ROOT / "06_analysis/00_dynamics/reference.json", encoding="utf-8"))
SHEET = json.load(open(ROOT / "01_cad/06_brep/derived/crawler/crawler_ground_sheet.json", encoding="utf-8"))
G = float(P["meta"]["gravity_m_s2"])
LEGS = dm.LEG_NAMES
ZF = float(P["ground"]["crawler_bottom_z_m"])
CR = P["contact"]["crawler"]
LAY = CR["sphere_layout"]
RAD = float(LAY["sphere_radius_m"])
YT = float(LAY["track_centre_y_m"])
KN_SPH = float(CR["kn_per_sphere_N_m"])
N_ROLL = 2 * len(LAY["roller_x_m"])
C_SPH = float(CR["damping_total_N_s_m"]) / N_ROLL
FMIN = float(P["control"]["F_min_cylinder_N"]) if "control" in P and "F_min_cylinder_N" in P["control"] else None
PITCH = float(SHEET["shoe_geometry"]["pitch_mm"]) * 1e-3
HALF = PITCH / 2


def find_fmin(p):
    """F_min_cylinder_N wherever it sits in the YAML (top-level block name not fixed here)."""
    for v in p.values():
        if isinstance(v, dict):
            if "F_min_cylinder_N" in v:
                return float(v["F_min_cylinder_N"])
            r = find_fmin(v)
            if r is not None:
                return r
    return None


FMIN = FMIN or find_fmin(P)

# ====================================================================== Part A
R2S = SHEET["rollers"]["roller_to_shoe_left"]
J_REAR = float(R2S[0]["nearest_joint_x_m"])   # -0.8763
J_FRONT = float(R2S[-1]["nearest_joint_x_m"])  # +0.8617
RX = [float(x) for x in LAY["roller_x_m"]]
EX = [float(x) for x in LAY["end_shoe_x_m"]]
EG = [float(g) for g in LAY["end_shoe_gap_m"]]


def variant(name):
    rx, ex, eg = list(RX), list(EX), list(EG)
    if name == "J":
        rx[0], rx[-1] = J_REAR, J_FRONT
    elif name == "H":
        ex = [x - HALF if x < 0 else x + HALF for x in ex]
    elif name != "D":
        raise ValueError(name)
    return rx, ex, eg


def layout_arrays(rx, ex, eg, kn_scale=1.0):
    """dyn_model.crawler_points order: rollers L, rollers R, end shoes L, end shoes R."""
    xy = np.array([[x, s * YT] for xs in (rx, ex) for s in (1.0, -1.0) for x in xs])
    gap = np.concatenate([np.zeros(2 * len(rx)), eg, eg])
    k = np.full(len(xy), KN_SPH * kn_scale)
    c = np.full(len(xy), C_SPH * math.sqrt(kn_scale))
    centres = np.column_stack([xy, ZF + gap + RAD])
    return xy, gap, k, c, centres


def composite(level):
    L = P["superstructure"]["auger_levels"][level]
    parts = [(float(L["mass_kg"]), np.array(L["com_m"], float), np.array(L["inertia_kg_m2"], float))]
    for n in LEGS:
        mp = P["legs"][n]["moving_part"]
        parts.append((float(mp["mass_kg"]), np.array(mp["com_retracted_m"], float), np.array(mp["inertia_kg_m2"], float)))
    m, c, inertia = dm.combine_bodies(parts)
    return m, c, inertia, float(L["mass_kg"])


def rot(roll, pitch):
    cr, sr, cp, sp = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    return ry @ rx


def skew(w):
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])


def expm_so3(w):
    th = np.linalg.norm(w)
    if th < 1e-300:
        return np.eye(3)
    k = skew(w / th)
    return np.eye(3) + math.sin(th) * k + (1 - math.cos(th)) * k @ k


def static_exact(level, centres, kn):
    m, c, _, _ = composite(level)
    W = m * G

    def resid(s):
        z0, ro, pi = s
        R = rot(ro, pi)
        cw = np.array([0, 0, z0]) + centres @ R.T
        pen = RAD - (cw[:, 2] - ZF)
        F = kn * np.maximum(pen, 0.0)
        g = np.array([0, 0, z0]) + R @ c
        mx = np.sum(F * (cw[:, 1] - g[1]))
        my = -np.sum(F * (cw[:, 0] - g[0]))
        return np.array([(F.sum() - W) / W, mx / W, my / W]), F, pen, cw, g

    s = fsolve(lambda s: resid(s)[0], [-W / (12 * kn.mean()), 0.0, 0.0], xtol=1e-14)
    r, F, pen, cw, g = resid(s)
    return dict(q=s, F=F, pen=pen, cw=cw, g=g, W=W, m=m, com=c, resid=float(np.abs(r).max()))


def modes(level, st, centres, kn, cdash):
    """6-DoF crawler modes about the exact pose (world-axis inertia, geometric lever at the sphere centre)."""
    m, c, Ib, _ = composite(level)
    z0, ro, pi = st["q"]
    R0 = rot(ro, pi)
    g0 = np.array([0, 0, z0]) + R0 @ c
    act = st["F"] > 0

    def wrench(x):
        R = expm_so3(x[3:]) @ R0
        g = g0 + x[:3]
        cw = g + (centres - c) @ R.T
        pen = RAD - (cw[:, 2] - ZF)
        F = kn * np.maximum(pen, 0.0) * act
        f = np.array([0, 0, F.sum() - m * G])
        mo = np.sum(np.cross(cw - g, np.column_stack([np.zeros_like(F), np.zeros_like(F), F])), axis=0)
        return np.concatenate([f, mo])

    h = np.array([1e-7] * 3 + [1e-8] * 3)
    K = np.zeros((6, 6))
    for j in range(6):
        dx = np.zeros(6)
        dx[j] = h[j]
        K[:, j] = -(wrench(dx) - wrench(-dx)) / (2 * h[j])
    K = 0.5 * (K + K.T)
    M = np.zeros((6, 6))
    M[:3, :3] = m * np.eye(3)
    M[3:, 3:] = R0 @ Ib @ R0.T
    C = np.zeros((6, 6))
    cw0 = g0 + (centres - c) @ R0.T
    for i in np.flatnonzero(act):
        a = np.concatenate([[0, 0, 1], np.cross(cw0[i] - g0, [0, 0, 1])])
        C += cdash[i] * np.outer(a, a)
    A = np.block([[np.zeros((6, 6)), np.eye(6)], [-np.linalg.solve(M, K), -np.linalg.solve(M, C)]])
    lam = np.linalg.eigvals(A)
    lam = lam[lam.imag > 2 * np.pi * 0.05]
    lam = lam[np.argsort(np.abs(lam))]
    fn = np.abs(lam) / (2 * np.pi)
    zeta = -lam.real / np.abs(lam)
    tau = 1.0 / (zeta * 2 * np.pi * fn)
    return dict(f_n_Hz=fn.tolist(), zeta=zeta.tolist(), tau_s=tau.tolist(),
                settle_ln100_tau_max_s=float(math.log(100) * tau.max()), n_active=int(act.sum()))


# ---- V4 vertical damped 3-DoF (copy of run_reference.dynamic_touch / run_s2b_crawler_check.run3)
geo = dm.geometry_from_params(P)
v = geo.v_max
L1y = P["contact"]["rigid_floor"]["L1"]
e_op = np.array([float(L1y["derivation"]["operating_extension_m"][n]) for n in LEGS])
k_pad = np.array([float(L1y["kn_per_pad_N_m"][n]) for n in LEGS])
c_pad = np.array(REF["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["c_pad_N_s_m"], float)
touch = np.asarray(geo.touch_extension, float)
rod_w = np.array([float(P["legs"][n]["moving_part"]["mass_kg"]) for n in LEGS]) * G


def sched_step(t):
    e = np.minimum(v * t, e_op)
    ed = np.where(v * t < e_op, v, 0.0)
    return e, ed


def run3(xy_cr, gap_cr, k_cr, c_cr, t_from=14.5, t_to=None, max_step=1e-3):
    t_to = float(e_op.max() / v + 3.0) if t_to is None else t_to
    b0 = dm.body_with_rods(P, geo, "top", np.zeros(4))
    W, cg = b0.mass * G, b0.com[:2]
    a = np.array([1.0, cg[1], -cg[0]])
    M = b0.mass * np.outer(a, a)
    M[1:, 1:] += b0.inertia[:2, :2]
    A = dm.support_matrix(np.vstack([geo.pad_xy, xy_cr]))
    k = np.concatenate([k_pad, k_cr])
    cd = np.concatenate([c_pad, c_cr])
    w = np.array([W, W * cg[1], -W * cg[0]])
    n_cr = len(xy_cr)

    def comp(t, y):
        e, ed = sched_step(t)
        c = np.concatenate([e - touch, -gap_cr]) - A @ y[:3]
        cdot = np.concatenate([ed, np.zeros(n_cr)]) - A @ y[3:]
        return c, cdot

    def force(t, y):
        c, cdot = comp(t, y)
        return np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)

    def rhs(t, y):
        return np.concatenate([y[3:], np.linalg.solve(M, A.T @ force(t, y) - w)])

    evs = [(lambda t, y, i=i: comp(t, y)[0][i]) for i in range(4)] + [lambda t, y: comp(t, y)[0][4:].max()]
    _, q0, _ = dm.static_unilateral(xy_cr, k_cr, -gap_cr, W, cg)
    sol = solve_ivp(rhs, (t_from, t_to), np.concatenate([q0, np.zeros(3)]), method="DOP853", rtol=1e-9,
                    atol=1e-12, max_step=max_step, events=evs, dense_output=True)
    touch_s = []
    for i in range(4):
        up = [t for t, y in zip(sol.t_events[i], sol.y_events[i]) if comp(t, y)[1][i] > 0]
        touch_s.append(up[0] if up else math.nan)
    off = [t for t, y in zip(sol.t_events[4], sol.y_events[4])
           if comp(t, y)[1][4:][np.argmax(comp(t, y)[0][4:])] < 0]
    tt = np.arange(t_from, t_to, 1e-3)
    Fp = np.array([force(t, sol.sol(t))[:4] for t in tt])
    Fc = Fp - rod_w
    margin = []
    for i in range(4):
        idx = np.flatnonzero(Fc[:, i] >= FMIN)
        margin.append(float(Fc[idx[0]:, i].min() - FMIN) if len(idx) else math.nan)
    losses = []
    for i in range(4):
        dn = [t for t, y in zip(sol.t_events[i], sol.y_events[i]) if comp(t, y)[1][i] < 0 and t > touch_s[i]]
        losses.append(len(dn))
    return dict(touch_s=touch_s, crawler_off_s=off[0] if off else math.nan, initial_q=q0.tolist(),
                peak_pad_N=Fp.max(axis=0).tolist(), Fmin_margin_after_reach_N=margin,
                Fmin_margin_min_N=float(np.nanmin(margin)), pad_contact_losses=losses, nfev=int(sol.nfev))


def rear_row_unload_slope_deg(xy_cr, gap_cr, k_cr):
    """Nose-down slope at which the rear roller row force reaches 0 (linear statics, CoM lever h tan(alpha))."""
    m, c, _, _ = composite("top")
    W = m * G
    h = c[2] - ZF
    rear = np.isclose(xy_cr[:, 0], xy_cr[:, 0][gap_cr == 0].min()) & (gap_cr == 0)

    def f_rear(alpha_deg):
        cgx = c[0] + h * math.tan(math.radians(alpha_deg))
        try:
            F, _, _ = dm.static_unilateral(xy_cr, k_cr, -gap_cr, W * math.cos(math.radians(alpha_deg)), np.array([cgx, c[1]]))
        except RuntimeError:  # active set cycling far beyond the rear-unload point
            return -1.0
        return float(F[rear].sum())

    lo, hi = -3.0, 4.0
    if f_rear(lo) <= 0:
        return lo
    if f_rear(hi) > 0:
        return hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f_rear(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def sum_x2(rx):
    x = np.asarray(rx)
    return float(np.sum(x ** 2)), float(np.sum((x - x.mean()) ** 2))


partA = {"meta": {
    "variants": {
        "D": "YAML layout D (reference)",
        "J": f"end-roller springs at the nearest joint of the CAD track phase: rear {J_REAR}, front {J_FRONT} m; end shoes as D",
        "H": f"track phase + half pitch ({HALF:.4f} m): end rollers on flat shoes (load at the roller axis); raised end shoes "
             "moved half a pitch outwards, same gaps (ASSUMPTION: free-span shape fixed relative to the hinge joint)"},
    "kn_per_sphere_N_m": KN_SPH, "c_per_sphere_N_s_m": C_SPH, "x3": "kn x3, dashpot x sqrt(3) (same heave zeta)",
    "V4_model": "vertical damped 3-DoF, step start/stop (V4 reference convention), DOP853 rtol 1e-9 atol 1e-12 max_step 1 ms",
    "F_min_cylinder_N": FMIN,
    "pitch_sign": "pitch > 0 = nose down"}}
for name in ("D", "J", "H"):
    rx, ex, eg = variant(name)
    for scale in (1.0, 3.0):
        key = name if scale == 1.0 else name + " x3"
        xy, gap, k, c, centres = layout_arrays(rx, ex, eg, scale)
        st = static_exact("top", centres, k)
        mo = modes("top", st, centres, k, c)
        act = st["F"] > 0
        F = st["F"]
        n_r = len(rx)
        Fl_roll = F[:n_r]
        Fl_end = F[2 * n_r:2 * n_r + len(ex)]
        row = {
            "roller_x_m": rx, "end_shoe_x_m": ex, "end_shoe_gap_m": eg,
            "sum_x2_rollers_about_0_m2": sum_x2(rx)[0], "sum_x2_rollers_about_centroid_m2": sum_x2(rx)[1],
            "settle_exact": {"u_z_mm": st["q"][0] * 1e3, "roll_deg": math.degrees(st["q"][1]),
                             "pitch_deg": math.degrees(st["q"][2]), "active": int(act.sum()), "resid_rel_W": st["resid"],
                             "left_roller_forces_N": Fl_roll.tolist(), "left_end_shoe_forces_N": Fl_end.tolist(),
                             "front_cluster_share_of_track": float((Fl_roll[-1] + Fl_end[len(ex) // 2:].sum()) / (Fl_roll.sum() + Fl_end.sum()))},
            "k_pitch_active_heave_condensed_N_m_rad": None,
            "modes": mo,
            "V4": run3(xy, gap, k, c),
            "rear_row_unload_nose_down_slope_deg": rear_row_unload_slope_deg(xy, gap, k),
        }
        xs = st["cw"][act, 0] - st["g"][0]
        row["k_pitch_active_heave_condensed_N_m_rad"] = float(np.sum(k[act] * xs ** 2) - np.sum(k[act] * xs) ** 2 / k[act].sum())
        partA[key] = row
        print("A", key, "pitch", round(row["settle_exact"]["pitch_deg"], 5), "f", np.round(mo["f_n_Hz"][:3], 4),
              "settle", round(mo["settle_ln100_tau_max_s"], 2), "touch", np.round(row["V4"]["touch_s"], 4),
              "off", round(row["V4"]["crawler_off_s"], 4), "Fmin margin", round(row["V4"]["Fmin_margin_min_N"], 1), flush=True)

refD = REF["lift_V4_compliant_crawler"]["layouts"]["D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)"]["dynamic_events_s"]
refD3 = REF["lift_V4_compliant_crawler"]["layouts"]["D kn_total x3 (sensitivity, YAML contact.crawler.kn_total_sensitivity_range_N_m)"]["dynamic_events_s"]
partA["validation"] = {
    "D_touch_minus_reference_s": (np.array(partA["D"]["V4"]["touch_s"]) - np.array(refD["touch_s (FL, FR, RL, RR)"])).tolist(),
    "D_crawler_off_minus_reference_s": partA["D"]["V4"]["crawler_off_s"] - refD["crawler_fully_off_s"],
    "Dx3_touch_minus_reference_s": (np.array(partA["D x3"]["V4"]["touch_s"]) - np.array(refD3["touch_s (FL, FR, RL, RR)"])).tolist(),
    "D_settle_pitch_vs_s2b_exact_deg (s2b_crawler_check top exact 0.173661 with float32 kn)": partA["D"]["settle_exact"]["pitch_deg"] - 0.173661,
    "D_modes_vs_s2b_world_axis_Hz (1.32691 / 3.05532 / 8.73106)": (np.array(partA["D"]["modes"]["f_n_Hz"][:3]) - np.array([1.32691, 3.05532, 8.73106])).tolist(),
}
for name in ("J", "H"):
    for suf in ("", " x3"):
        a, d = partA[name + suf], partA["D" + suf]
        partA[name + suf]["minus_D" + suf.replace(" ", "_")] = {
            "touch_s": (np.array(a["V4"]["touch_s"]) - np.array(d["V4"]["touch_s"])).tolist(),
            "crawler_off_s": a["V4"]["crawler_off_s"] - d["V4"]["crawler_off_s"],
            "f_n_rel": (np.array(a["modes"]["f_n_Hz"][:3]) / np.array(d["modes"]["f_n_Hz"][:3]) - 1).tolist(),
            "settle_pitch_deg": a["settle_exact"]["pitch_deg"] - d["settle_exact"]["pitch_deg"],
            "settle_u_z_mm": a["settle_exact"]["u_z_mm"] - d["settle_exact"]["u_z_mm"],
            "k_pitch_rel": a["k_pitch_active_heave_condensed_N_m_rad"] / d["k_pitch_active_heave_condensed_N_m_rad"] - 1,
            "settle_length_s": a["modes"]["settle_ln100_tau_max_s"] - d["modes"]["settle_ln100_tau_max_s"],
            "peak_pad_N": (np.array(a["V4"]["peak_pad_N"]) - np.array(d["V4"]["peak_pad_N"])).tolist(),
            "Fmin_margin_min_N": a["V4"]["Fmin_margin_min_N"] - d["V4"]["Fmin_margin_min_N"],
        }
partA["x3_minus_D_touch_s (stiffness sensitivity spread, for scale)"] = (
    np.array(partA["D x3"]["V4"]["touch_s"]) - np.array(partA["D"]["V4"]["touch_s"])).tolist()

# ====================================================================== Part B
# soil sets: ASSUMPTION, illustrative Bekker values (Wong, Theory of Ground Vehicles, Bekker table order), SI units
SOILS = {
    "dry_sand_LLL": dict(n=1.1, kc=0.99e3, kphi=1528.43e3),
    "LETE_sand": dict(n=0.79, kc=102e3, kphi=5301e3),
    "clayey_soil_Thailand_38pct": dict(n=0.5, kc=13.19e3, kphi=692.15e3),
    "heavy_clay_25pct (S0 benchmark soil)": dict(n=0.13, kc=12.70e3, kphi=1555.95e3),
}
SG = SHEET["shoe_geometry"]
BLK_X = float(SG["block_bottom_plane_mm (x, y)"][0]) * 1e-3     # 0.0881
BLK_Y0, BLK_Y1 = SHEET["rectangles_body_m"]["left"]["block_bottom_flat"]["y_m"]   # 0.80038, 1.28961
FLAT_X0, FLAT_X1 = SHEET["rectangles_body_m"]["left"]["block_bottom_flat"]["x_m"]  # -0.83037, 0.81686
DOM = SHEET["scm_active_domain"]["variants"]["full (10 flat + 6 end shoes per track)"]["boxes"]["left"]
DOM_X, DOM_Y = DOM["x_m"], DOM["y_m"]
flat_st = []
with open(ROOT / "01_cad/06_brep/derived/crawler/crawler_contact_parts.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["kind"] == "flat_shoe" and r["side"] == "L":
            flat_st.append(float(r["station_x_body_m"]))
flat_st = sorted(flat_st)
end_st = [float(e["station_x_body_m"]) for e in SHEET["end_shoes_left"]]
end_gap = [float(e["gap_mm"]) * 1e-3 for e in SHEET["end_shoes_left"]]
# straight free span through the three end-shoe (station, gap) points of each end: gap = s (|x| - x0)
fr = np.polyfit([x for x in end_st if x > 0], [g for x, g in zip(end_st, end_gap) if x > 0], 1)
re = np.polyfit([-x for x in end_st if x < 0], [g for x, g in zip(end_st, end_gap) if x < 0], 1)
RAMP = {"front": dict(slope=float(fr[0]), x0=float(-fr[1] / fr[0])), "rear": dict(slope=float(re[0]), x0=float(-re[1] / re[0]))}


def shape_prims(shape):
    """Primitives of the left track (right = mirror in y). Heights relative to the block-bottom plane
    (ASSUMPTION: the 4 mm pads are pressed in; on soil the block bottom is the bearing face).
    box: (x0, x1, y0, y1, h_at_xref, xref, slope_dh_dx); sphere: (xc, yc, gap, r)."""
    boxes, spheres = [], []
    if shape == "SPH":
        for x in RX:
            spheres.append((x, YT, 0.0, RAD))
        for x, g in zip(EX, EG):
            spheres.append((x, YT, g, RAD))
    if shape in ("A", "B"):
        for x, g, sgn in [(x, g, 1 if x > 0 else -1) for x, g in zip(end_st, end_gap)]:
            r = RAMP["front"] if sgn > 0 else RAMP["rear"]
            # block-bottom box at the end-shoe station, tilted with the free span (dh/dx = sgn * slope)
            boxes.append((x - BLK_X / 2, x + BLK_X / 2, BLK_Y0, BLK_Y1, g, x, sgn * r["slope"]))
    if shape == "A":
        for x in flat_st:
            boxes.append((x - BLK_X / 2, x + BLK_X / 2, BLK_Y0, BLK_Y1, 0.0, x, 0.0))
    if shape == "B":
        boxes.append((FLAT_X0, FLAT_X1, BLK_Y0, BLK_Y1, 0.0, 0.0, 0.0))
    if shape == "C":
        xr0, xf0 = -RAMP["rear"]["x0"], RAMP["front"]["x0"]
        boxes.append((xr0, xf0, BLK_Y0, BLK_Y1, 0.0, 0.0, 0.0))
        boxes.append((xf0, max(end_st) + BLK_X / 2, BLK_Y0, BLK_Y1, 0.0, xf0, RAMP["front"]["slope"]))
        boxes.append((min(end_st) - BLK_X / 2, xr0, BLK_Y0, BLK_Y1, 0.0, xr0, -RAMP["rear"]["slope"]))
    return boxes, spheres


def grid(h, ox=0.0, oy=0.0):
    xs = np.arange(DOM_X[0] + ox, DOM_X[1], h)
    ys = np.arange(DOM_Y[0] + oy, DOM_Y[1], h)
    return xs, ys


def bottom_height(shape, xs, ys):
    """Lowest shape surface above each node (left track grid), nan where no shape."""
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    hb = np.full(X.shape, np.inf)
    boxes, spheres = shape_prims(shape)
    for (x0, x1, y0, y1, h0, xr, s) in boxes:
        m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
        hb = np.where(m, np.minimum(hb, h0 + s * (X - xr)), hb)
    for (xc, yc, gp, r) in spheres:
        rho2 = (X - xc) ** 2 + (Y - yc) ** 2
        m = rho2 < r * r
        hb = np.where(m, np.minimum(hb, gp + r - np.sqrt(np.maximum(r * r - rho2, 0.0))), hb)
    return X, Y, hb


m_all, c_all, _, _ = composite("top")
W_ALL = m_all * G
XG, YG = c_all[0], c_all[1]
FOUR = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)


def scm_eval(q, track_data, soil, h):
    """Vertical force and moments about the origin from both tracks; also per-node diagnostics."""
    z0, ph, th = q
    Fz = Mx = My = 0.0
    diag = []
    for (X, Y, hb, sgn) in track_data:
        Yw = sgn * Y
        zb = z0 + hb + Yw * ph - X * th
        s = np.where(np.isfinite(hb), np.maximum(-zb, 0.0), 0.0)
        con = s > 0
        lab, nlab = ndimage.label(con, structure=FOUR)
        b = np.zeros_like(s)
        if nlab:
            area = ndimage.sum(con, lab, index=np.arange(1, nlab + 1)) * h * h
            # perimeter: contact-node edges facing a non-contact node (4-neighbour, padded border = no contact)
            pad = np.pad(con, 1)
            edges = (pad[1:-1, 1:-1] & ~pad[:-2, 1:-1]).astype(int) + (pad[1:-1, 1:-1] & ~pad[2:, 1:-1]) + \
                    (pad[1:-1, 1:-1] & ~pad[1:-1, :-2]) + (pad[1:-1, 1:-1] & ~pad[1:-1, 2:])
            per = ndimage.sum(edges, lab, index=np.arange(1, nlab + 1)) * h
            bp = 2 * area / np.maximum(per, 1e-12)
            b = np.where(con, bp[np.maximum(lab - 1, 0)], 0.0)
        p = np.where(con, (soil["kc"] / np.where(con, b, 1.0) + soil["kphi"]) * s ** soil["n"], 0.0)
        f = p * h * h
        Fz += f.sum()
        Mx += (f * Yw).sum()
        My += (f * X).sum()
        diag.append(dict(s=s, p=p, con=con, nlab=nlab, b=b, X=X))
    return np.array([Fz, Mx, My]), diag


def scm_solve(shape, soil, h, ox=0.0, oy=0.0, q0=None):
    xs, ys = grid(h, ox, oy)
    X, Y, hb = bottom_height(shape, xs, ys - YT + YT)  # left-track body y
    track_data = [(X, Y, hb, 1.0), (X, Y, hb, -1.0)]   # right track = mirror (y -> -y)
    target = np.array([W_ALL, W_ALL * YG, W_ALL * XG])

    def res(q):
        f, _ = scm_eval(q, track_data, soil, h)
        return (f - target) / W_ALL

    if q0 is None:
        q0 = [-0.3 if shape == "SPH" else -0.02, 0.0, 0.0]
    sol = least_squares(res, q0, x_scale=[0.01, 0.001, 0.001], diff_step=1e-6, xtol=1e-12, ftol=1e-12, gtol=1e-12,
                        max_nfev=400)
    f, diag = scm_eval(sol.x, track_data, soil, h)
    d = diag[0]
    s, p, con = d["s"], d["p"], d["con"]
    xcon = d["X"][con]
    lab_b = d["b"][con]
    # tangent heave stiffness of the loading (Bekker) branch, both tracks: sum dp/ds dA
    kt = 0.0
    for dd in diag:
        ss, pp = dd["s"], dd["p"]
        kt += float(np.sum(np.where(ss > 0, soil["n"] * pp / np.maximum(ss, 1e-12), 0.0)) * h * h)
    area = float(sum(dd["con"].sum() for dd in diag) * h * h)
    return dict(z0_mm=sol.x[0] * 1e3, roll_deg=math.degrees(sol.x[1]), pitch_deg=math.degrees(sol.x[2]),
                resid_rel=float(np.abs(sol.fun).max()), nfev=int(sol.nfev),
                max_sinkage_mm=float(s.max() * 1e3), max_p_kPa=float(p.max() * 1e-3),
                contact_nodes_left=int(con.sum()), contact_area_both_m2=area,
                contact_x_left_m=[float(xcon.min()), float(xcon.max())] if con.any() else None,
                patches_left=int(d["nlab"]), b_range_m=[float(lab_b.min()), float(lab_b.max())] if con.any() else None,
                k_tangent_loading_N_m=kt, q=sol.x.tolist())


partB = {"meta": {
    "model": "node-wise Bekker (SCM-type) statics, rigid machine (superstructure top + 4 rods at e = 0) on the crawler, "
             "small angles, b = 2 A / perimeter per connected contact patch (4-neighbour), no elastic K, no bulldozing, "
             "no lateral interaction between nodes",
    "weight_N": W_ALL, "com_xy_m": [XG, YG],
    "soils (ASSUMPTION, illustrative Bekker sets; n, kc N/m^(n+1), kphi N/m^(n+2))": SOILS,
    "shapes": {"SPH": "24 spheres r 0.05 m of layout D (YAML)",
               "A": "16 block-bottom boxes per track (10 flat shoes at crawler_contact_parts.csv stations, 6 end shoes "
                    "at their gaps, tilted with the free span), 88.1 x 489.2 mm",
               "B": "1 flat block-bottom box per track (x -0.830 ... +0.817, 0.489 m wide) + the 6 end-shoe boxes of A",
               "C": "envelope: 1 flat box per track between the free-span hinge points + 1 inclined ramp box per end through "
                    "the end-shoe gaps (continuous bottom profile, one patch)"},
    "ramp_free_span_fit": RAMP,
    "reference_plane": "block bottom (pad tips +4 mm); the 4 mm pads are taken as pressed in (ASSUMPTION)",
    "active_domain_left_m": {"x": DOM_X, "y": DOM_Y}}}

# validation: shape B flat box only on a linear Winkler soil (n = 1, kc = 0) vs closed form
kw = 5e7
soil_w = dict(n=1.0, kc=0.0, kphi=kw)


def winkler_closed_form():
    """Rigid strip pair on Winkler soil, pitch only (roll handled by symmetry, small y_g ignored for the strip length)."""
    L = FLAT_X1 - FLAT_X0
    B = (BLK_Y1 - BLK_Y0) * 2
    xc = 0.5 * (FLAT_X0 + FLAT_X1)
    e = XG - xc
    Pt = W_ALL
    if abs(e) <= L / 6:
        return dict(p_max_kPa=Pt / (B * L) * (1 + 6 * abs(e) / L) * 1e-3, contact_length_m=L)
    Lc = 3 * (L / 2 - abs(e))
    return dict(p_max_kPa=2 * Pt / (3 * B * (L / 2 - abs(e))) * 1e-3, contact_length_m=Lc)


_orig_prims = shape_prims


def prims_flat_B(shape):
    if shape == "Bflat":
        return [(FLAT_X0, FLAT_X1, BLK_Y0, BLK_Y1, 0.0, 0.0, 0.0)], []
    return _orig_prims(shape)


shape_prims = prims_flat_B  # noqa: F811  (adds the validation shape)
val = {}
for h in (0.02, 0.01, 0.005):
    r = scm_solve("Bflat", soil_w, h)
    val[f"{h * 1e3:.0f}mm"] = {k: r[k] for k in ("max_p_kPa", "contact_x_left_m", "pitch_deg", "z0_mm", "resid_rel")}
cf = winkler_closed_form()
val["closed_form"] = cf
val["5mm_contact_length_m"] = val["5mm"]["contact_x_left_m"][1] - val["5mm"]["contact_x_left_m"][0]
val["5mm_rel_diff_p_max"] = val["5mm"]["max_p_kPa"] / cf["p_max_kPa"] - 1
val["note"] = f"Winkler k = {kw:g} Pa/m, block-bottom width x 2 tracks, flat length {FLAT_X1 - FLAT_X0:.4f} m; roll ignored in the closed form"
partB["validation_winkler"] = val
print("B validation", json.dumps(val, default=float)[:400], flush=True)

res = {}
for shape in ("SPH", "A", "B", "C"):
    res[shape] = {}
    for sname, soil in SOILS.items():
        rr = {}
        q0 = None
        for h in (0.04, 0.02, 0.01, 0.005):
            r = scm_solve(shape, soil, h, q0=q0)
            q0 = r["q"]
            rr[f"h_{h * 1e3:.0f}mm"] = r
        offs = []
        for o in (0.25, 0.5, 0.75):
            r = scm_solve(shape, soil, 0.02, ox=o * 0.02, oy=o * 0.02, q0=rr["h_20mm"]["q"])
            offs.append(r)
        rr["h_20mm_offsets_0.25_0.5_0.75"] = offs
        fine = rr["h_5mm"]
        for hk in ("h_40mm", "h_20mm", "h_10mm"):
            c = rr[hk]
            c["minus_5mm"] = {"z0_mm": c["z0_mm"] - fine["z0_mm"], "pitch_deg": c["pitch_deg"] - fine["pitch_deg"],
                              "max_p_rel": c["max_p_kPa"] / fine["max_p_kPa"] - 1}
        g20 = [rr["h_20mm"]] + offs
        rr["h_20mm_offset_scatter"] = {"z0_mm": [min(x["z0_mm"] for x in g20), max(x["z0_mm"] for x in g20)],
                                       "pitch_deg": [min(x["pitch_deg"] for x in g20), max(x["pitch_deg"] for x in g20)],
                                       "max_p_kPa": [min(x["max_p_kPa"] for x in g20), max(x["max_p_kPa"] for x in g20)]}
        res[shape][sname] = rr
        print("B", shape, sname, "z0 mm 40/20/10/5", [round(rr[k]["z0_mm"], 2) for k in ("h_40mm", "h_20mm", "h_10mm", "h_5mm")],
              "pitch", [round(rr[k]["pitch_deg"], 4) for k in ("h_40mm", "h_20mm", "h_10mm", "h_5mm")],
              "pmax kPa", [round(rr[k]["max_p_kPa"]) for k in ("h_40mm", "h_20mm", "h_10mm", "h_5mm")],
              "offs z0", [round(v, 2) for v in rr["h_20mm_offset_scatter"]["z0_mm"]], flush=True)
partB["results"] = res

# crawler-soil heave damping: SCM damping_R per unit area for zeta 0.2 (YAML damping_ratio_heave_soil)
zeta_soil = float(CR["damping_ratio_heave_soil"])
Kel = 2e8  # ASSUMPTION: Chrono SCM elastic K of the S0 benchmark (demo order), Pa/m
ex_damp = {}
for sname in SOILS:
    r = res["C"][sname]["h_20mm"]
    A = r["contact_area_both_m2"]
    k_el = Kel * A
    R = 2 * zeta_soil * math.sqrt(k_el * m_all) / A
    ex_damp[sname] = {"contact_area_m2": A, "k_elastic_N_m (K x A)": k_el, "f_heave_elastic_Hz": math.sqrt(k_el / m_all) / (2 * math.pi),
                      "R_for_zeta_Pa_s_m": R, "k_tangent_loading_N_m": r["k_tangent_loading_N_m"],
                      "zeta_on_loading_branch_with_that_R": R * A / (2 * math.sqrt(r["k_tangent_loading_N_m"] * m_all)),
                      "zeta_with_S0_benchmark_R_3e4": 3e4 * A / (2 * math.sqrt(k_el * m_all))}
partB["soil_damping_R_example"] = {"zeta_target (YAML damping_ratio_heave_soil)": zeta_soil, "elastic_K_Pa_m (ASSUMPTION)": Kel,
                                   "rule": "R = 2 zeta sqrt(K m / A_c) (per-area dashpot of SCM, heave of the machine on the crawler, elastic branch)",
                                   "shape": "C, 20 mm grid", "by_soil": ex_damp}

out = {"meta": {"script": "04_scripts/01_dynamics/run_crawler_contact_check.py", "doc": "dynamics_model.md 3.11 (rev. 20)",
                "gravity_world_m_s2": [0, 0, -G], "frames": "body x forward, y left, z up; pitch > 0 nose down; roll > 0 left up",
                "inputs": ["02_params/rexome33.yaml", "06_analysis/00_dynamics/reference.json",
                           "01_cad/06_brep/derived/crawler/crawler_ground_sheet.json", "01_cad/06_brep/derived/crawler/crawler_contact_parts.csv"]},
       "partA_end_roller_and_phase": partA, "partB_scm_shape": partB}
out["meta"]["runtime_s"] = time.perf_counter() - T0
dst = ROOT / "06_analysis/00_dynamics/crawler_contact_check.json"
json.dump(out, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
print(json.dumps(partA["validation"], default=float))
print("runtime", out["meta"]["runtime_s"])
