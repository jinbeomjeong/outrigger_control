"""Crawler contact layout check: former YAML layout A (2 x 9 over the bbox) vs CAD-measured layouts (D chosen 2026-10-20).

Decision support only. Does NOT change the YAML, export_params.py or the reference outputs
(reference.json, leg_extension_loads.json). Writes 06_analysis/00_dynamics/crawler_layout_check.json.

Inputs
  * 02_params/rexome33.yaml (current layout, stiffness, damping, legs, mass case C, auger level top)
  * 01_cad/06_brep/derived/crawler/{crawler_summary.json, crawler_wheels.csv, crawler_grouser_tips.csv,
    crawler_solids.csv} (B-rep measurements of the drawn undercarriage; REXOME25 model per the STEP file)

Layouts (vertical unilateral point springs on a rigid level floor, total stiffness kept = kn_total unless noted,
total dashpot = 2 zeta sqrt(kn_total m) with zeta = contact.crawler.damping_ratio_heave):
  A  former YAML layout (rev. 5, replaced by D on 2026-10-20): 2 x 9, x evenly over the bbox [-1.840, 1.844], y +/-1.066
  B  proposed: lower track rollers, 2 x 6, x = roller axes (-0.884 ... +0.901, pitch 357 mm), y +/-1.045
  C  bound: flat shoes, 2 x 10, x = grouser pad centres on the floor (-0.786 ... +0.773, pitch 173.2 mm), y +/-1.045
  D  sensitivity: B + raised shoes beyond the end rollers as gapped unilateral springs (gap = lowest point of the
     shoe above the floor from CAD, k per point = B value) -> upper bound of end engagement
  E  sensitivity: B with kn_total x 3 (stiffer track / slab), dashpot rescaled to keep zeta
  F  sensitivity: D with kn_total x 3

Model per layout (same family as run_reference.lift_reference and run_leg_extension_loads):
  1. settled pose on the crawler (legs at 0): dyn_model.static_unilateral
  2. crawler-on-floor modes: linear 6-DoF about the settled pose with the ACTIVE springs only (vertical springs,
     geometric preload term), damped eigenvalues -> f, zeta, tau, settle length ln(100) max tau
  3. nonlinear settle check: damped vertical 3-DoF (uz, roll, pitch) released at rest from zero spring compression
  4. V4 quasi-static events (e_i = min(v t, e_op_i)): touch times, first touch leg, crawler fully off, end state
  5. V4 residual after the last stop (linear 6-DoF L1, as run_reference.lift_reference)
  6. full-stroke damped 3-DoF transition (as run_leg_extension_loads.dynamic_check, with gapped springs)
  7. stability on the crawler (legs retracted) on a slope: end lift / track lift angle, model tip angle
  8. levelling range with the CAD lower envelope (solid bboxes) vs the bbox corners (run_reference 3.3)

Conventions: body frame x forward, y left, z up (CLAUDE.md); g = -9.80665 z_hat m/s^2 (YAML meta.gravity_m_s2);
pitch theta > 0 = nose down, roll phi > 0 = left side up; q = [uz, phi, theta] about the body-frame origin.
CAD axes: body x = +Z_cad, y = +X_cad, z = +Y_cad (mm -> m).

Run (dynamics-dev, activated):
    C:\\ProgramData\\miniforge3\\Scripts\\conda.exe run -n dynamics-dev python -I \\
        04_scripts/01_dynamics/run_crawler_layout_check.py
Deterministic (no random numbers).
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402
import run_leg_extension_loads as lel  # noqa: E402
import run_reference as rref  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "crawler_layout_check.json"
REF_JSON = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json"
LEL_JSON = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "leg_extension_loads.json"
CR_DIR = dm.PROJECT_ROOT / "01_cad" / "06_brep" / "derived" / "crawler"
MM = 1e-3
LN100 = math.log(100.0)
r = lel.r
# former YAML layout A (rev. 5): 2 x 9 spheres evenly over the crawler bbox x, track centre +/-1.066 m (assumed 0.6 m shoe)
LEGACY_A_NX = 9
LEGACY_A_X_RANGE_M = (-1.840, 1.844)
LEGACY_A_TRACK_Y_M = 1.066


# ---------------------------------------------------------------------------------------------
# CAD measurements
# ---------------------------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_cad() -> dict:
    summ = json.loads((CR_DIR / "crawler_summary.json").read_text(encoding="utf-8"))
    ground_y = float(summ["ground_y_mm"])
    wheels = read_csv(CR_DIR / "crawler_wheels.csv")
    rollers = sorted((float(w["axis_x_body_m"]), float(w["axis_y_body_m"])) for w in wheels
                     if w["role"].startswith("track roller"))
    ends = {w["side"] + ("_rear" if float(w["axis_x_body_m"]) < 0 else "_front"):
            {"axis_x_m": float(w["axis_x_body_m"]), "wheel_bottom_above_floor_mm": float(w["bottom_height_mm"]),
             "role": w["role"]} for w in wheels if w["role"].startswith("end wheel")}
    # grouser pads: 4 small downward planes per shoe (area 2108.5 mm^2); lowest point height per shoe station
    tips = [t for t in read_csv(CR_DIR / "crawler_grouser_tips.csv") if abs(float(t["area_mm2"]) - 2108.515681) < 1.0]
    st: dict[tuple, float] = {}
    for t in tips:
        key = (t["side"], round(float(t["centroid_z_mm"]), 1))
        h = float(t["bbox_min_y_mm"]) - ground_y
        st[key] = min(st.get(key, np.inf), h)
    shoes = sorted((z * MM, (1.0 if s == "left" else -1.0), h * MM) for (s, z), h in st.items())
    roller_bottom_above_floor = None
    for w in wheels:
        if w["role"].startswith("track roller"):
            roller_bottom_above_floor = float(w["bottom_height_mm"]) * MM
            break
    return {"summary": summ, "rollers": rollers, "shoes": shoes, "end_wheels": ends,
            "track_centre_y_m": float(summ["track_centre_half_spacing_mm"]) * MM,
            "roller_bottom_above_floor_m": roller_bottom_above_floor}


def lower_envelope(cell: float = 0.01) -> dict:
    """Lowest point of the crawler on an (x, y) grid from the solid bboxes (conservative: solid fills its bbox)."""
    rows = read_csv(CR_DIR / "crawler_solids.csv")
    ground_y = json.loads((CR_DIR / "crawler_summary.json").read_text(encoding="utf-8"))["ground_y_mm"]
    xs = np.arange(-1.86, 1.86 + 1e-9, cell); ys = np.arange(-1.38, 1.38 + 1e-9, cell)
    zlow = np.full((len(xs), len(ys)), np.inf)
    for s in rows:
        x0, x1 = float(s["bbox_min_z_mm"]) * MM, float(s["bbox_max_z_mm"]) * MM   # body x = Z_cad
        y0, y1 = float(s["bbox_min_x_mm"]) * MM, float(s["bbox_max_x_mm"]) * MM   # body y = X_cad
        h = (float(s["bbox_min_y_mm"]) - ground_y) * MM
        ix = (xs >= x0 - cell / 2) & (xs <= x1 + cell / 2)
        iy = (ys >= y0 - cell / 2) & (ys <= y1 + cell / 2)
        if ix.any() and iy.any():
            sub = zlow[np.ix_(ix, iy)]
            zlow[np.ix_(ix, iy)] = np.minimum(sub, h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    m = np.isfinite(zlow)
    return {"x": X[m], "y": Y[m], "h": zlow[m]}


# ---------------------------------------------------------------------------------------------
# Layouts
# ---------------------------------------------------------------------------------------------
def build_layouts(p: dict, cad: dict, m_damp: float) -> dict:
    cr = p["contact"]["crawler"]
    kn_tot = float(cr["kn_total_N_m"])
    zeta = float(cr["damping_ratio_heave"])
    yt = cad["track_centre_y_m"]
    out = {}

    def entry(name, xy, gap, k_each, kn_total_nominal, note):
        xy = np.asarray(xy, float); gap = np.asarray(gap, float)
        n_nom = int((gap <= 0).sum())
        c_tot = dm.crawler_damping_total(kn_total_nominal, m_damp, zeta)
        out[name] = {"xy": xy, "gap": gap, "k": np.full(len(xy), k_each), "c": np.full(len(xy), c_tot / n_nom),
                     "kn_total_floor_contact_N_m": kn_total_nominal, "damping_total_N_s_m": c_tot, "note": note}

    # layout A = the former YAML layout (rev. 5, before the 2026-10-20 decision); dm.crawler_points is layout D now
    xy_a = np.array([[x, s * LEGACY_A_TRACK_Y_M] for s in (1.0, -1.0) for x in np.linspace(*LEGACY_A_X_RANGE_M, LEGACY_A_NX)])
    entry("A_current_2x9_bbox", xy_a, np.zeros(len(xy_a)), kn_tot / len(xy_a), kn_tot,
          "YAML contact.crawler.sphere_layout: x evenly over the crawler bbox, y +/-1.066 (assumed 0.6 m shoe)")
    rx = np.array([x for x, y in cad["rollers"] if y > 0])
    xy_b = np.array([[x, s * yt] for s in (1.0, -1.0) for x in rx])
    entry("B_rollers_2x6", xy_b, np.zeros(len(xy_b)), kn_tot / len(xy_b), kn_tot,
          "lower track roller axes from crawler_wheels.csv, y = track centre +/-1.045 (crawler_summary.json)")
    flat = [(x, s) for x, s, h in cad["shoes"] if h < 1e-6]
    xy_c = np.array([[x, s * yt] for x, s in flat])
    entry("C_flat_shoes_2x10", xy_c, np.zeros(len(xy_c)), kn_tot / len(xy_c), kn_tot,
          "grouser pad centres touching the floor (lowest point 0 mm), pitch 173.2 mm")
    raised = [(x, s, h) for x, s, h in cad["shoes"] if h > 1e-6]
    xy_d = np.vstack([xy_b, [[x, s * yt] for x, s, _ in raised]])
    gap_d = np.concatenate([np.zeros(len(xy_b)), [h for _, _, h in raised]])
    entry("D_rollers_plus_gapped_end_shoes", xy_d, gap_d, kn_tot / len(xy_b), kn_tot,
          "B + raised shoes beyond the end rollers (gap = CAD lowest point, k per point = B value): end engagement upper bound")
    entry("E_rollers_2x6_k_x3", xy_b, np.zeros(len(xy_b)), 3 * kn_tot / len(xy_b), 3 * kn_tot,
          "B with kn_total x 3 (stiffer track/slab), dashpot rescaled to the same heave zeta")
    entry("F_D_with_k_x3", xy_d, gap_d, 3 * kn_tot / len(xy_b), 3 * kn_tot,
          "D with kn_total x 3 (stiffer track/slab), dashpot rescaled to the same heave zeta")
    return out


# ---------------------------------------------------------------------------------------------
# Lift model with arbitrary crawler points (gaps allowed)
# ---------------------------------------------------------------------------------------------
class LayoutLiftModel(lel.LiftModel):
    def __init__(self, p, lay):
        super().__init__(p)
        self.cr_xy = lay["xy"]; self.cr_k = lay["k"]; self.cr_c = lay["c"]; self.cr_gap = lay["gap"]
        self.xy_all = np.vstack([self.geo.pad_xy, self.cr_xy])
        self.k_all = np.concatenate([self.k_pad, self.cr_k])
        self.A_cr = dm.support_matrix(self.cr_xy)
        self.A_all = dm.support_matrix(self.xy_all)

    def delta(self, e):
        return np.concatenate([np.broadcast_to(np.asarray(e, float), (4,)) - self.touch, -self.cr_gap])

    def solve(self, e):
        e = np.broadcast_to(np.asarray(e, float), (4,))
        d = self.delta(e)
        F, q, act = dm.static_unilateral(self.xy_all, self.k_all, d, self.W_tot, self.cg)
        gap_all = -(d - self.A_all @ q)
        return {"e": e.copy(), "q": q, "F_pad": F[:4], "F_cyl": F[:4] - self.W_rod, "F_cr": F[4:],
                "F_cr_tot": float(F[4:].sum()), "pad_contact": act[:4].copy(), "crawler_contact": bool(act[4:].any()),
                "gap_all": gap_all, "active_all": act.copy(), "F_all": F,
                "crawler_clearance": float((self.A_cr @ q + self.cr_gap).min())}


def settled(model: LayoutLiftModel) -> dict:
    """Legs at 0: only the crawler springs can act (pads are 340 mm above the floor)."""
    F, q, act = dm.static_unilateral(model.cr_xy, model.cr_k, -model.cr_gap, model.W_tot, model.cg)
    xy = model.cr_xy
    xs = np.unique(np.round(xy[model.cr_gap <= 0, 0], 4))   # rows of the floor-contact (gap 0) points
    rear = np.isclose(xy[:, 0], xs.min(), atol=1e-4); front = np.isclose(xy[:, 0], xs.max(), atol=1e-4)
    # kern check per track for the springs on the floor (gap 0): eccentricity of the resultant vs the kern
    base = model.cr_gap <= 0
    xb = xy[base, 0]; xc = xb.mean()
    kern = float(((xb - xc) ** 2).sum() / (len(xb) * (xc - xb.min())))
    return {"F": F, "q": q, "active": act,
            "out": {"q_about_origin (uz_mm, roll_deg, pitch_deg)": r([q[0] * 1e3, math.degrees(q[1]), math.degrees(q[2])], 5),
                    "active_points": int(act.sum()), "n_points": int(len(act)),
                    "station_force_N (left track, rear -> front)": r(F[(xy[:, 1] > 0)][np.argsort(xy[xy[:, 1] > 0, 0])], 5),
                    "rear_row_force_N": r(float(F[rear].sum()), 5), "front_row_force_N": r(float(F[front].sum()), 5),
                    "gapped_points_in_contact": int((act & ~base).sum()),
                    "gapped_points_force_N": r(float(F[~base].sum()), 5),
                    "eccentricity_of_resultant_from_floor_spring_centroid_m": r(float(model.cg[0] - xc), 4),
                    "kern_half_length_rear_side_m (rear row unloads beyond this)": r(kern, 4),
                    "pad_gap_at_e0_mm": r((model.touch + model.A_pad @ q) * 1e3, 5)}}


def crawler_modes(model: LayoutLiftModel, s: dict, p: dict, level: str = "top") -> dict:
    b0 = dm.body_with_rods(p, model.geo, level, np.zeros(4))
    act = s["active"]
    pts3 = np.column_stack([model.cr_xy[act], np.full(int(act.sum()), model.geo.crawler_bottom_z)])
    K = np.zeros((6, 6)); C = np.zeros((6, 6))
    for j, (pt, k, c, F0) in enumerate(zip(pts3, model.cr_k[act], model.cr_c[act], s["F"][act])):
        d = pt - b0.com
        _, _, az = dm.a_vec(d)
        K += k * np.outer(az, az); C += c * np.outer(az, az)
        K[3:, 3:] -= F0 * dm._hz(d)
    M = dm.mass_6dof(b0)
    # undamped modes on the stiff subspace (heave, roll, pitch): surge/sway/yaw have no stiffness
    w2, f_u, Phi, cls, orth = dm.modal(M, K + 1e-9 * np.eye(6), list(dm.DOF6))
    fd, zd = dm.complex_modes(M, K, C)
    keep = fd > 0.05
    tau = 1.0 / (zd[keep] * 2 * np.pi * fd[keep])
    ku = f_u > 0.05
    return {"f_Hz": r(fd[keep], 4), "zeta": r(zd[keep], 4), "tau_s": r(tau, 4),
            "mode_shapes_undamped (KE fraction)": [c for c, k in zip(cls, ku) if k],
            "settle_length_s (ln(100) x max tau)": r(float(LN100 * tau.max()), 4),
            "mass_orthogonality_max": r(float(orth), 3)}


def free_settle(model: LayoutLiftModel, s: dict, t_end: float = 80.0) -> dict:
    """Nonlinear damped vertical 3-DoF (crawler springs only), released at rest with zero spring compression."""
    bw = model.bw
    a = np.array([1.0, bw.com[1], -bw.com[0]])
    M = bw.mass * np.outer(a, a); M[1:, 1:] += bw.inertia[:2, :2]
    A = model.A_cr; k = model.cr_k; cd = model.cr_c; dlt = -model.cr_gap
    w = np.array([model.W_tot, model.W_tot * model.cg[1], -model.W_tot * model.cg[0]])

    def rhs(t, y):
        q, qd = y[:3], y[3:]
        c = dlt - A @ q; cdot = -A @ qd
        F = np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)
        return np.concatenate([qd, np.linalg.solve(M, A.T @ F - w)])

    tt = np.arange(0.0, t_end + 1e-12, 2e-3)
    sol = solve_ivp(rhs, (0, t_end), np.zeros(6), method="DOP853", rtol=1e-9, atol=1e-12, max_step=2e-3, t_eval=tt)
    dev = np.abs(sol.y[:3] - s["q"][:, None])
    d0 = dev[:, 0]
    out = {"solver": {"method": "DOP853", "rtol": 1e-9, "atol": 1e-12, "max_step_s": 2e-3, "status": int(sol.status),
                      "nfev": int(sol.nfev)},
           "initial_deviation (uz_mm, roll_deg, pitch_deg)": r([d0[0] * 1e3, math.degrees(d0[1]), math.degrees(d0[2])], 4)}
    for j, nm in ((0, "uz"), (2, "pitch")):
        big = np.where(dev[j] > 0.01 * d0[j])[0]
        out[f"t_last_above_1pct_of_initial_{nm}_s"] = r(float(sol.t[big[-1]]) if len(big) else 0.0, 4)
    out["end_minus_static (uz_mm, pitch_deg)"] = r([(sol.y[0, -1] - s["q"][0]) * 1e3, math.degrees(sol.y[2, -1] - s["q"][2])], 3)
    return out


def residual_after_stop(p, model: LayoutLiftModel, t_crawler_off: float, e_op: np.ndarray, f1: float) -> dict:
    """Copy of run_reference.lift_reference residual block (linear 6-DoF L1, top) with the given crawler-off time."""
    geo = model.geo; xy = geo.pad_xy; v = geo.v_max
    L1 = p["contact"]["rigid_floor"]["L1"]
    k_L1 = np.array([float(L1["kn_per_pad_N_m"][n]) for n in dm.LEG_NAMES])
    kt_L1 = np.array([float(L1["kt_per_pad_N_m"][n]) for n in dm.LEG_NAMES])
    cn = np.array([float(L1["cn_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES])
    ct = np.array([float(L1["ct_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES])
    bw = dm.body_with_rods(p, geo, "top", e_op)
    W, cg = bw.mass * geo.g, bw.com[:2]
    pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
    Fc, _, _ = dm.static_loads(k_L1, xy, W, cg)
    K6 = dm.stiffness_6dof(bw, pad_pts, k_L1, kt_L1, Fc); M6 = dm.mass_6dof(bw)
    C6 = np.zeros((6, 6)); AZ = []
    for i in range(4):
        ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
        C6 += cn[i] * np.outer(az, az) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay)); AZ.append(az)
    AZ = np.array(AZ)
    t_stop = e_op / v; t_end = float(t_stop.max())
    t_s = float(t_crawler_off) + 0.05

    def u(t):
        return np.minimum(v * t, e_op) - e_op, np.where(v * t < e_op, v, 0.0)

    def rhs(t, y):
        uu, ud = u(t)
        Q = AZ.T @ (k_L1 * uu + cn * ud)
        return np.concatenate([y[6:], np.linalg.solve(M6, Q - K6 @ y[:6] - C6 @ y[6:])])

    uu0, ud0 = u(t_s)
    y = np.concatenate([np.linalg.solve(K6, AZ.T @ (k_L1 * uu0)), np.linalg.solve(K6, AZ.T @ (k_L1 * ud0))])
    seg = [t_s] + sorted(set(float(x) for x in t_stop if x > t_s)) + [t_end + 20.0]
    T, Y = [], []
    for a_, b_ in zip(seg[:-1], seg[1:]):
        sol = solve_ivp(rhs, (a_, b_), y, method="DOP853", rtol=1e-10, atol=1e-13, max_step=2e-3)
        T.append(sol.t); Y.append(sol.y); y = sol.y[:, -1]
    T = np.concatenate(T); Y = np.concatenate(Y, axis=1)
    rp = np.degrees(Y[3:5])

    def amp(t_from):
        m = (T >= t_end + t_from) & (T <= t_end + t_from + 1.0 / f1)
        return r(np.abs(rp[:, m]).max(axis=1), 4)

    return {"start_s": r(t_s, 6), "roll_pitch_at_0s": amp(0.0), "roll_pitch_at_10s": amp(10.0),
            "roll_pitch_at_15s": amp(15.0),
            "last_time_above_0.001deg_after_last_stop_s": r(float(T[np.abs(rp).max(axis=0) > 1e-3].max()) - t_end, 4)}


def dynamic_transition(model: LayoutLiftModel, t0: float, t1: float, schedule, max_step=1e-3):
    """run_leg_extension_loads.dynamic_check with gapped crawler springs (same equations otherwise)."""
    bw = model.bw
    a = np.array([1.0, bw.com[1], -bw.com[0]])
    M = bw.mass * np.outer(a, a); M[1:, 1:] += bw.inertia[:2, :2]
    A = model.A_all; k = model.k_all
    cd = np.concatenate([model.c_pad, model.cr_c])
    w = np.array([model.W_tot, model.W_tot * model.cg[1], -model.W_tot * model.cg[0]])
    v = model.v; ncr = len(model.cr_xy)

    def forces(t, q, qd):
        e = schedule(t)
        ed = np.full(4, v if v * t < model.stroke else 0.0)
        d = model.delta(e); dd = np.concatenate([ed, np.zeros(ncr)])
        c = d - A @ q; cdot = dd - A @ qd
        return np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)

    def rhs(t, y):
        return np.concatenate([y[3:], np.linalg.solve(M, A.T @ forces(t, y[:3], y[3:]) - w)])

    s0 = model.solve(schedule(t0))
    tt = np.round(np.arange(t0, t1 + 1e-12, 1e-3), 6)
    tw = time.perf_counter()
    sol = solve_ivp(rhs, (t0, t1), np.concatenate([s0["q"], np.zeros(3)]), method="DOP853", rtol=1e-9, atol=1e-12,
                    max_step=max_step, t_eval=tt)
    tw = time.perf_counter() - tw
    F = np.array([forces(t, sol.y[:3, j], sol.y[3:, j]) for j, t in enumerate(sol.t)])
    F_qs = np.array([model.solve(schedule(t))["F_all"] for t in sol.t])
    per = {}
    for i, n in enumerate(dm.LEG_NAMES):
        touched = np.where(F[:, i] > 0)[0]
        k0 = touched[0]
        loss = (F[k0:, i] <= 0) & (F_qs[k0:, i] > 0)
        reach = np.where(F[k0:, i] - model.W_rod[i] >= model.F_min_cyl)[0]
        after = F[k0 + reach[0]:, i] - model.W_rod[i] if len(reach) else np.array([np.nan])
        per[n] = {"first_touch_dyn_s": r(float(sol.t[k0]), 6), "peak_pad_force_N": r(float(F[:, i].max()), 6),
                  "peak_at_s": r(float(sol.t[int(np.argmax(F[:, i]))]), 6),
                  "contact_lost_samples_after_touch": int(loss.sum()),
                  "cyl_force_min_after_first_reaching_F_min_N": r(float(after.min()), 6)}
    dpad = np.abs(F[:, :4] - F_qs[:, :4])
    fmin_after = [per[n]["cyl_force_min_after_first_reaching_F_min_N"] for n in dm.LEG_NAMES]
    return {"window_s": [r(t0, 6), t1], "solver": {"method": "DOP853", "rtol": 1e-9, "atol": 1e-12, "max_step_s": max_step,
                                                     "status": int(sol.status), "nfev": int(sol.nfev), "wall_s": round(tw, 2)},
            "per_leg": per,
            "max_peak_pad_force_N": r(float(F[:, :4].max()), 6),
            "max_peak_cylinder_force_N": r(float(max(F[:, i].max() - model.W_rod[i] for i in range(4))), 6),
            "max_abs_diff_vs_quasi_static_N": r(float(dpad.max()), 5),
            "max_abs_diff_at_s": r(float(sol.t[int(np.argmax(dpad.max(1)))]), 6),
            "F_min_margin_N (min cyl force after first reaching F_min - F_min)": r(min(fmin_after) - model.F_min_cyl, 4),
            "contact_lost_samples_after_touch": int(sum(per[n]["contact_lost_samples_after_touch"] for n in dm.LEG_NAMES)),
            "_F": F}


def slope_stability(p, model: LayoutLiftModel, level: str, cad: dict) -> dict:
    """Machine on its crawler (legs retracted) on a rigid slope. Gravity tilted by alpha toward azimuth az
    (az 0 = toward +x = nose-down slope). Linear springs, small displacements: resultant shifts by h tan(alpha)."""
    geo = model.geo
    b0 = dm.body_with_rods(p, geo, level, np.zeros(4))
    h = float(b0.com[2] - geo.crawler_bottom_z)
    W = b0.mass * geo.g
    xy = model.cr_xy; base = model.cr_gap <= 0
    xs = xy[base, 0]; ys = xy[base, 1]
    res = {"com_height_above_floor_m": r(h, 5), "com_xy_m": r(b0.com[:2], 5)}

    def row_force(alpha_deg, az_deg, sel):
        """Sum of the spring forces of the selected points; 0 if the springs cannot hold the body (tip)."""
        t = math.tan(math.radians(alpha_deg))
        cg = b0.com[:2] + h * t * np.array([math.cos(math.radians(az_deg)), math.sin(math.radians(az_deg))])
        try:
            F, _, _ = dm.static_unilateral(xy, model.cr_k, -model.cr_gap, W * math.cos(math.radians(alpha_deg)), cg)
        except RuntimeError:
            return 0.0
        return float(F[sel].sum())

    rear = np.isclose(xy[:, 0], xs.min(), atol=1e-4) & base
    front = np.isclose(xy[:, 0], xs.max(), atol=1e-4) & base
    left = xy[:, 1] > 0; right = ~left

    def crossing(fun, lo, hi):
        """fun(lo) > 0, fun(hi) <= 0 -> boundary by bisection (deg)."""
        if fun(lo) <= 0:
            return float("nan")
        if fun(hi) > 0:
            return float("inf")
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if fun(mid) > 1e-6 else (lo, mid)
        return 0.5 * (lo + hi)

    def signed(a):  # signed pitch slope: a > 0 nose-down (gravity toward +x, az 0), a < 0 nose-up (az 180)
        return abs(a), (0.0 if a >= 0 else 180.0)

    g_rear = lambda a: row_force(*signed(a), rear)      # noqa: E731
    g_front = lambda a: row_force(*signed(-a), front)   # noqa: E731  (argument = nose-up angle)
    a_rear = crossing(g_rear, 0.0, 30.0) if g_rear(0.0) > 1e-6 else crossing(g_rear, -5.0, 0.0)
    a_front = crossing(g_front, 0.0, 30.0) if g_front(0.0) > 1e-6 else -crossing(g_front, -30.0, 0.0)
    a_left = crossing(lambda a: row_force(a, 270.0, left), 0.0, 45.0)
    a_right = crossing(lambda a: row_force(a, 90.0, right), 0.0, 45.0)
    xmax = float(xs.max()); xmin = float(xs.min()); ymax = float(ys.max())
    shoe_edge = float(cad["summary"]["ground_patches_by_band"]["1mm"]["left"]["x_range_mm"][1]) * MM
    res.update({
        "rear_row_unloads_at_pitch_slope_deg (+ nose-down; - = already unloaded on level ground, nose-up slope that reloads it)": r(a_rear, 4),
        "front_row_unloads_at_nose_up_slope_deg": r(a_front, 4),
        "one_track_fully_unloaded_roll_slope_deg (left track, right track)": r([a_left, a_right], 4),
        "model_tip_angle_deg (resultant reaches the outermost spring line): forward, backward, roll": r([
            math.degrees(math.atan2(xmax - b0.com[0], h)), math.degrees(math.atan2(b0.com[0] - xmin, h)),
            math.degrees(math.atan2(ymax - abs(b0.com[1]), h))], 4),
        "physical_roll_tip_angle_deg (shoe outer edge |y| = %.3f m)" % shoe_edge: r(
            math.degrees(math.atan2(shoe_edge - abs(b0.com[1]), h)), 4),
        "tip_angle_incl_raised_points_deg (forward, backward; = model tip if no gapped points)": r([
            math.degrees(math.atan2(float(xy[:, 0].max()) - b0.com[0], h)),
            math.degrees(math.atan2(b0.com[0] - float(xy[:, 0].min()), h))], 4),
        "tip_angle_about_end_wheel_axes_deg (front x %.3f, rear x %.3f; track under the wheels 30-43 mm up)" % (
            cad["end_wheels"]["left_front"]["axis_x_m"], cad["end_wheels"]["left_rear"]["axis_x_m"]): r([
            math.degrees(math.atan2(cad["end_wheels"]["left_front"]["axis_x_m"] - b0.com[0], h)),
            math.degrees(math.atan2(b0.com[0] - cad["end_wheels"]["left_rear"]["axis_x_m"], h))], 4),
    })
    return res


def levelling_range(geo, xy_pads, pad_z, stroke, pts_xy, pts_h, clearance) -> dict:
    """run_reference.levelled_extension with an arbitrary set of crawler low points (x, y, height above floor)."""
    def levelled(ro, pi):
        sx = -math.tan(math.radians(pi)); sy = math.tan(math.radians(ro))
        H = np.max(sx * pts_xy[:, 0] + sy * pts_xy[:, 1] - pts_h) + clearance - geo.crawler_bottom_z
        return pad_z + H - (sx * xy_pads[:, 0] + sy * xy_pads[:, 1])

    def max_slope(direc):
        lo, hi = 0.0, 20.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            e = levelled(mid * math.sin(math.radians(direc)), mid * math.cos(math.radians(direc)))
            lo, hi = (mid, hi) if (e.min() >= 0 and e.max() <= stroke) else (lo, mid)
        return lo

    return {"pitch(+/-)": r([max_slope(0), max_slope(180)], 4), "roll(+/-)": r([max_slope(90), max_slope(270)], 4),
            "diagonal_45deg": r(max_slope(45), 4)}


# ---------------------------------------------------------------------------------------------
def main():
    t_start = time.perf_counter()
    p = dm.load_params()
    cad = load_cad()
    ref = json.loads(REF_JSON.read_text(encoding="utf-8"))
    lel_ref = json.loads(LEL_JSON.read_text(encoding="utf-8"))
    f1 = float(ref["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"]["top"]["f_damped_Hz"][0])
    base = lel.LiftModel(p)
    geo = base.geo; v = base.v
    e_op = np.array([float(p["contact"]["rigid_floor"]["L1"]["derivation"]["operating_extension_m"][n]) for n in dm.LEG_NAMES])
    layouts = build_layouts(p, cad, base.bw.mass)

    res = {"meta": {
        "script": "04_scripts/01_dynamics/run_crawler_layout_check.py",
        "params": "02_params/rexome33.yaml (not modified)",
        "cad": "01_cad/06_brep/derived/crawler (REXOME25 undercarriage drawn in the STEP)",
        "frame": "body: x forward, y left, z up; origin = CAD origin; floor z = ground.crawler_bottom_z_m",
        "gravity_m_s2": [0.0, 0.0, -geo.g],
        "signs": "pitch > 0 nose-down, roll > 0 left up; q about the body-frame origin",
        "level": "auger top (mass case C) unless noted; legs = superstructure + 4 moving parts",
        "assumptions": {
            "kn_total_N_m (A-D)": float(p["contact"]["crawler"]["kn_total_N_m"]),
            "crawler_heave_zeta": float(p["contact"]["crawler"]["damping_ratio_heave"]),
            "equal stiffness per point, vertical only (SMC kt = 0), rigid level floor, rigid body": True,
            "dashpot total": "2 zeta sqrt(kn_total m), m = superstructure top + 4 moving parts, split equally over the floor-contact points",
        }},
        "cad_measurements": {
            "track_centre_y_m": r(cad["track_centre_y_m"], 6),
            "roller_axes_x_m (left)": r([x for x, y in cad["rollers"] if y > 0], 6),
            "roller_bottom_above_floor_m (link + shoe height under a roller)": r(cad["roller_bottom_above_floor_m"], 5),
            "shoe_stations (x_m, lowest point above floor mm), left": [[r(x, 5), r(h * 1e3, 4)] for x, s, h in cad["shoes"] if s > 0],
            "end_wheels": cad["end_wheels"],
        }}

    out_lay = {}
    lay_models = {}
    for name, lay in layouts.items():
        tw = time.perf_counter()
        m = LayoutLiftModel(p, lay)
        lay_models[name] = m
        s = settled(m)
        ent = {"note": lay["note"], "n_points": len(lay["xy"]),
               "x_floor_contact_range_m": r([float(lay["xy"][lay["gap"] <= 0, 0].min()), float(lay["xy"][lay["gap"] <= 0, 0].max())], 5),
               "track_centre_y_m": r(float(np.abs(lay["xy"][:, 1]).max()), 5),
               "k_per_point_N_m": r(float(lay["k"][0]), 6), "c_per_point_N_s_m": r(float(lay["c"][0]), 6),
               "damping_total_N_s_m": r(lay["damping_total_N_s_m"], 6),
               "gn_per_point_1_s (c / superstructure body mass)": r(float(lay["c"][0]) / base.body.mass, 6),
               "pitch_stiffness_about_spring_centroid_N_m_rad": r(float(
                   (lay["k"][lay["gap"] <= 0] * (lay["xy"][lay["gap"] <= 0, 0] - lay["xy"][lay["gap"] <= 0, 0].mean()) ** 2).sum()), 5),
               "settled_on_crawler (legs at 0)": s["out"]}
        ent["crawler_on_floor_modes (active springs, top)"] = crawler_modes(m, s, p, "top")
        ent["crawler_on_floor_modes_other_levels"] = {lv: {k_: v_ for k_, v_ in crawler_modes(m, s, p, lv).items()
                                                            if k_ in ("f_Hz", "zeta", "settle_length_s (ln(100) x max tau)")}
                                                       for lv in ("middle", "bottom")}
        ent["nonlinear_free_settle_from_zero_compression"] = free_settle(m, s)

        # V4 quasi-static events
        sched_v4 = lambda t: np.minimum(v * t, e_op)  # noqa: E731
        ev = lel.events(m, sched_v4, float((e_op / v).max()))
        touch = [ev[f"touch_{n}"] for n in dm.LEG_NAMES]
        first = dm.LEG_NAMES[int(np.argmin(touch))]
        s_end = m.solve(e_op)
        gap0 = m.touch + m.A_pad @ s["q"]
        ent["V4_quasi_static"] = {
            "touch_s (FL, FR, RL, RR)": r(touch, 6), "first_touch_leg": first, "first_touch_s": r(min(touch), 6),
            "front_minus_rear_touch_s": r(0.5 * (touch[0] + touch[1]) - 0.5 * (touch[2] + touch[3]), 4),
            "touch_kinematic_from_settled_pose_s": r(gap0 / v, 6),
            "crawler_fully_off_s": r(ev["crawler_off"], 6),
            "all_cyl_ge_F_min_s": r(ev["all_cyl_ge_F_min"], 6),
            "end_pad_force_N": r(s_end["F_pad"], 7), "end_attitude_deg (roll, pitch)": r(np.degrees(s_end["q"][1:]), 5),
            "end_crawler_min_clearance_mm": r(s_end["crawler_clearance"] * 1e3, 6),
        }
        ent["V4_residual_linear_L1_after_last_stop (deg, roll/pitch)"] = residual_after_stop(p, m, ev["crawler_off"], e_op, f1)

        # full-stroke damped transition
        sched_full = lambda t: np.full(4, min(v * t, m.stroke))  # noqa: E731
        ev_full = lel.events(m, sched_full, 17.0)
        t0 = math.floor(min(14.5, min(ev_full[f"touch_{n}"] for n in dm.LEG_NAMES) - 0.5) * 10) / 10
        dyn = dynamic_transition(m, t0, 20.0, sched_full)
        dyn.pop("_F")
        if name.startswith(("B_", "D_")):
            d2 = dynamic_transition(m, t0, 20.0, sched_full, max_step=5e-4)
            dyn["max_step_convergence: max peak diff vs max_step 5e-4 [N]"] = r(abs(d2["max_peak_pad_force_N"] - dyn["max_peak_pad_force_N"]), 3)
            d2.pop("_F")
        dyn["quasi_static_events_full_stroke_s"] = {"touch (FL, FR, RL, RR)": r([ev_full[f"touch_{n}"] for n in dm.LEG_NAMES], 6),
                                                    "crawler_off": r(ev_full["crawler_off"], 6)}
        ent["full_stroke_damped_3dof"] = dyn
        ent["slope_stability_on_crawler (legs retracted)"] = {lv: slope_stability(p, m, lv, cad) for lv in dm.LEVELS}
        ent["wall_s"] = round(time.perf_counter() - tw, 1)
        out_lay[name] = ent
        print(name, "done", ent["wall_s"], "s", flush=True)
    res["layouts"] = out_lay

    # ------------------------------------------------------------ validation: D reproduces the reference outputs
    # (before 2026-10-20 this block compared layout A with the then-default 2x9 entries; the stored
    # crawler_layout_check.json still holds that A comparison; D uses CAD-exact positions here, YAML-rounded there)
    A = out_lay["D_rollers_plus_gapped_end_shoes"]
    v4ref = ref["lift_V4_compliant_crawler"]["layouts"][rref.V4_LAYOUT_D]
    mref = ref["lift_V4_compliant_crawler"][rref.V4_MODES_D]
    resref = ref["lift_V4_compliant_crawler"]["residual_after_last_stop_linear_L1 (deg, max |dev| over one 1st-rocking period)"]
    dref = lel_ref["validation"]["quasi_static_check (damped 3-DoF)"]
    res["validation_D_vs_reference"] = {
        "settled q (uz_mm, roll_deg, pitch_deg) this / reference.json": [A["settled_on_crawler (legs at 0)"]["q_about_origin (uz_mm, roll_deg, pitch_deg)"],
                                                                         v4ref["settled_on_crawler (legs at 0)"]["q_about_origin (uz_mm, roll_deg, pitch_deg)"]],
        "modes f_Hz this / reference": [A["crawler_on_floor_modes (active springs, top)"]["f_Hz"], mref["f_Hz"]],
        "modes zeta this / reference": [A["crawler_on_floor_modes (active springs, top)"]["zeta"], mref["zeta"]],
        "settle_length_s this / reference": [A["crawler_on_floor_modes (active springs, top)"]["settle_length_s (ln(100) x max tau)"],
                                             mref["settle_length_s (ln(100) x max tau)"]],
        "touch_s this / reference": [A["V4_quasi_static"]["touch_s (FL, FR, RL, RR)"], v4ref["quasi_static_events_s"]["touch_s (FL, FR, RL, RR)"]],
        "crawler_off_s this / reference": [A["V4_quasi_static"]["crawler_fully_off_s"], v4ref["quasi_static_events_s"]["crawler_fully_off_s"]],
        "residual 10 s / 15 s this / reference": [[A["V4_residual_linear_L1_after_last_stop (deg, roll/pitch)"]["roll_pitch_at_10s"],
                                                   A["V4_residual_linear_L1_after_last_stop (deg, roll/pitch)"]["roll_pitch_at_15s"]],
                                                  [resref["roll_pitch_at_10s"], resref["roll_pitch_at_15s"]]],
        "full-stroke dynamic peak pad force N (FL) this / leg_extension_loads.json": [
            A["full_stroke_damped_3dof"]["per_leg"]["FL"]["peak_pad_force_N"], dref["per_leg"]["FL"]["peak_pad_force_N"]],
        "full-stroke F_min margin N this / leg_extension_loads.json": [
            A["full_stroke_damped_3dof"]["F_min_margin_N (min cyl force after first reaching F_min - F_min)"],
            r(min(dref["per_leg"][n]["cyl_force_min_after_first_reaching_F_min_N"] for n in dm.LEG_NAMES) - base.F_min_cyl, 4)],
    }

    # ------------------------------------------------------------ levelling range: bbox corners vs CAD lower envelope
    env = lower_envelope()
    box = np.array([[x, y] for x in geo.crawler_xy_box[0] for y in geo.crawler_xy_box[1]])
    stroke = geo.stroke
    lv = {}
    for c in (0.0, 0.05):
        lv[f"clearance_{int(c * 1000)}mm"] = {
            "bbox_corners_at_floor (current, run_reference 3.3)": levelling_range(geo, geo.pad_xy, geo.pad_z_retracted, stroke, box, np.zeros(4), c),
            "CAD_lower_envelope (solid bboxes, 10 mm grid)": levelling_range(geo, geo.pad_xy, geo.pad_z_retracted, stroke,
                                                                             np.column_stack([env["x"], env["y"]]), env["h"], c)}
    lv["envelope_note"] = ("lowest point per 10 mm (x, y) cell over the crawler solids' bboxes (conservative: each solid fills "
                           "its bbox); the raised track ends and the idler/sprocket wraps replace the floor-level bbox corners")
    lv["envelope_lowest_height_at_x_mm"] = {f"{xq:+.2f}": r(float(env["h"][np.abs(env["x"] - xq) < 0.006].min()) * 1e3, 4)
                                            for xq in (-1.84, -1.70, -1.55, -1.40, -1.20, -1.00, -0.90, 0.90, 1.00, 1.20, 1.40, 1.55, 1.70, 1.82)}
    res["levelling_range_crawler_clearance"] = lv
    res["meta"]["runtime_s"] = round(time.perf_counter() - t_start, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps(res["validation_D_vs_reference"], indent=1))
    print("written", OUT, res["meta"]["runtime_s"], "s")


if __name__ == "__main__":
    main()
