"""S6 verification-range extension by the crawler compliance (dynamics_model.md 3.13, rev. 24).

Background (user decision 2026-10-21): the S6 stage-2 Chrono snapshots (crawler Coulomb bushings, Q12) show that a
floor slope of 3.5 deg nose down puts the body on the crawler at 3.73-3.82 deg and a 5.5 deg roll at 5.53-5.56 deg,
so the C2 verification mode (5.5 / 3.5 deg on the crawler attitude) rejects the floors it is meant to cover. The
verification range is to be widened by the crawler compliance (crawler attitude basis); the operating limits
(4.4 / 3.2 deg) stay.

Stages (each rewrites only its own key of the output JSON):
  crawler   A  Chrono snapshots (07_results/S6/snapshots_20261021_195044): end value, last-window mean, decaying-sine
               fit of the residual sway, normal-force difference vs the analytic start decomposed as a rigid motion.
            B  Independent quasi-static crawler-on-slope model (this file, numpy): 24 unilateral normal springs
               (layout D, gaps), in-plane gravity carried by the stuck crawler bushings (equal share over the active
               spheres = rigid in-plane translation, equal kt), force point at the sphere centre (Chrono L1) or at the
               floor contact point (reduced plant); mass with the rods retracted (Chrono start) or at e_op (plant).
            C  Reduced time-domain plant (run_mast_flex_c2_check.FlexPlant, import only) settled on the crawler with
               crawler tangential kt = kn (all earlier reduced runs) and kt = 0.402 kn (Chrono Q12) x 0.3 / 1 / 3.
            D  Compliance map floor -> crawler attitude on the floor diamond and on-axis, three auger levels, and the
               floor image of the proposed verification boundary.
  envelope  Quasi-static levelling end state (run_target_envelope.point, import only) at the floor images of the
            proposed boundary: stroke headroom (50 mm crawler clearance), F_min, swivel, rod bending pair, pad slip;
            rule A interplay (accepted target set near the boundary, physical feasibility of the accepted targets).
  td_main / td_robust / td_kt / td_ext
            Closed loop C2 R1 (run_pad_tangential_check.run_one, import only) at the floor images of the proposed
            boundary: rigid + three flexible masts, seeds, beta 0.69 / 1.6 GPa, extra delay 0, crawler kt variants,
            secant pad kt.
  report    Tables (printed) from the JSON.

Run (project root, dynamics-dev, each stage < 10 min with 12 workers):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s6_slope_boundary_check.py --stage crawler
  ... --stage envelope | td_main | td_robust | td_kt | td_ext | report
Output: 06_analysis/00_dynamics/s6_slope_boundary_check.json
Conventions: body x forward, y left, z up; roll + = left side up, pitch + = nose down; attitudes ZYX (yaw, pitch,
roll) intrinsic, degrees in outputs. Floor plane z = -tan(theta_g) x + tan(phi_g) y (run_control_comparison.Plant).
Gravity g from the YAML (9.80665 m/s^2, -z world).
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
sys.path.insert(0, str(HERE.parent / "03_control"))
sys.path.insert(0, str(HERE.parent / "00_cad"))
import dyn_model as dm  # noqa: E402
import run_pad_tangential_check as rpt  # noqa: E402  (imports rmf -> patches rcc.Plant in this process)
import run_mast_flex_c2_check as rmf  # noqa: E402
import run_control_comparison as rcc  # noqa: E402

ROOT = dm.PROJECT_ROOT
OUT_JSON = ROOT / "06_analysis" / "00_dynamics" / "s6_slope_boundary_check.json"
SNAP_DIR = ROOT / "07_results" / "S6" / "snapshots_20261021_195044"
LEGS = dm.LEG_NAMES
DEG = math.pi / 180.0
F_MIN = float(dm.load_params()["control"]["F_min_cylinder_N"])  # YAML (rev. 30; was the literal 9452.55)
GUARD = F_MIN + 5e3
WORKERS = 12

# Chrono Q12 crawler bushing (snapshot meta 'crawler_bushing'), ASSUMPTION of cad: kt = (kt/kn)_pad mean x kn_sphere
KT_REL_CHRONO = 0.4021968558889507
SPHERE_R = 0.05                     # YAML contact.crawler.sphere_layout.sphere_radius_m

# Proposed verification boundary (crawler attitude basis, offset form, see stage crawler D):
#   |phi_c| / PHI_V + |theta_c - THETA0| / THETA_V(sign, level) <= 1
THETA0 = 0.17                       # flat-floor settle pitch on the crawler (0.1718-0.1737 deg, Chrono), rounded down
PHI_V = 5.6
THETA_V = {"top": (3.70, 3.60), "middle": (3.65, 3.60), "bottom": (3.62, 3.60)}   # (nose down +, nose up -)
SNAP_FLOORS = {"flat": (0.0, 0.0), "fdown3.5": (0.0, 3.5), "fup3.5": (0.0, -3.5), "roll5.5": (5.5, 0.0),
               "diag3": (2.1213203435596424, 2.1213203435596424), "roll3": (3.0, 0.0)}


# ================================================================================================ geometry helpers
def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def floor_rot(roll_deg, pitch_deg):
    """Floor frame as run_control_comparison.Plant: R e_z = n, yaw 0, R = Ry(th) Rx(phi)."""
    n = rpt.floor_normal(roll_deg, pitch_deg)
    phi = math.asin(-n[1]); th = math.atan2(n[0], n[2])
    return _ry(th) @ _rx(phi), n


def rp_of(R):
    """(roll, pitch) deg of a body rotation, ZYX."""
    return math.degrees(math.atan2(R[2, 1], R[2, 2])), math.degrees(-math.asin(max(-1.0, min(1.0, R[2, 0]))))


_P = {}


def P():
    if not _P:
        p = dm.load_params(); geo = dm.geometry_from_params(p)
        cxy, kcr, ccr = dm.crawler_points(p)
        gap = dm.crawler_gaps(p)
        _P.update(p=p, geo=geo, cxy=cxy, kcr=kcr, ccr=ccr, gap=gap,
                  e_op=geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"])
    return _P


# ================================================================================================ B quasi-static model
CRAWLER_MASS = 11271.0              # CAD crawler compound (REXOME25 model), cad_review.md
CRAWLER_COM = np.array([0.0, 0.0, -0.55])   # ASSUMPTION: undercarriage CoM (body), only for the +-10 % mass case


def crawler_static(level, roll_g, pitch_g, point="centre", rods="retracted", tangential=True, kn_scale=1.0,
                   crawler_mass_frac=0.0, pad_F=None):
    """Settled crawler pose on a sloped floor (independent implementation, floor frame).

    Unknowns z0 (body origin height above the floor plane, floor axes), roll, pitch of the body relative to the floor.
    Normal force per sphere k max(delta, 0), delta = -(sphere bottom height); the in-plane gravity -m g_xy (floor axes)
    is shared equally by the active spheres (stuck bushings, rigid in-plane translation, equal kt; distribution does
    not change the roll/pitch moments because all force points are at one height) and acts at the sphere centre
    (point='centre', Chrono L1) or at the contact point on the floor ('floor', reduced plant). Moments about the CoM.
    """
    c = P(); p = c["p"]; geo = c["geo"]
    ext = np.zeros(4) if rods == "retracted" else np.full(4, c["e_op"])
    body = dm.body_with_rods(p, geo, level, ext)
    m = body.mass; com = body.com
    if crawler_mass_frac:
        dmass = crawler_mass_frac * CRAWLER_MASS
        com = (m * com + dmass * CRAWLER_COM) / (m + dmass); m = m + dmass
    padF = np.zeros(4) if pad_F is None else np.asarray(pad_F, float)
    pad_xy = geo.pad_xy
    Rf, n = floor_rot(roll_g, pitch_g)
    gf = Rf.T @ np.array([0.0, 0.0, -geo.g])            # gravity in floor axes
    k = c["kcr"] * kn_scale
    pts = np.column_stack([c["cxy"], geo.crawler_bottom_z + c["gap"]])   # sphere bottoms (body), gaps included
    h_pt = SPHERE_R if point == "centre" else 0.0

    def state(q):
        z0, ph, th = q
        R = _ry(th) @ _rx(ph)
        O = np.array([0.0, 0.0, z0])
        w = O + pts @ R.T
        delta = -w[:, 2]
        act = delta > 0
        N = k * np.maximum(delta, 0.0)
        cw = O + R @ com
        nact = max(int(act.sum()), 1)
        T = -m * gf[:2] / nact if tangential else np.zeros(2)
        rN = w - cw                                       # normal force at the contact point (same line as centre)
        rT = w + R @ np.array([0, 0, h_pt]) - cw          # tangential force point
        M = np.zeros(3)
        for i in np.where(act)[0]:
            M += np.cross(rN[i], [0, 0, N[i]]) + np.cross(rT[i], [T[0], T[1], 0.0])
        for i in range(4):                                # pad loads along the floor normal (touchdown)
            if padF[i]:
                rp_ = O + R @ np.array([pad_xy[i, 0], pad_xy[i, 1], 0.0]) - cw
                M += np.cross(rp_, [0, 0, padF[i]])
        r = np.array([N.sum() + padF.sum() + m * gf[2], M[0], M[1]])
        return r, N, act, R

    q = np.array([-geo.crawler_bottom_z - m * geo.g / k[:12].sum(), 0.0, 0.0])
    for _ in range(100):
        r, N, act, R = state(q)
        if np.max(np.abs(r)) < 1e-6:
            break
        J = np.zeros((3, 3))
        for j, h in enumerate((1e-7, 1e-8, 1e-8)):
            dq = np.zeros(3); dq[j] = h
            J[:, j] = (state(q + dq)[0] - state(q - dq)[0]) / (2 * h)
        q = q - np.linalg.solve(J, r)
    else:
        raise RuntimeError("crawler_static did not converge")
    r, N, act, R = state(q)
    roll_b, pitch_b = rp_of(Rf @ R)
    return {"body_deg": [roll_b, pitch_b], "rel_deg": [math.degrees(q[1]), math.degrees(q[2])],
            "N": N, "active": act, "res": float(np.max(np.abs(r))), "z0": float(q[0])}


def floor_of_body(level, target, point="centre", rods="retracted"):
    """Floor (roll, pitch) whose settled crawler attitude equals target (deg); fixed-point + secant (2-D Newton)."""
    tg = np.asarray(target, float)
    x = tg - np.array([0.0, THETA0])
    for _ in range(30):
        b = np.array(crawler_static(level, x[0], x[1], point, rods)["body_deg"])
        r = b - tg
        if np.max(np.abs(r)) < 1e-7:
            break
        J = np.zeros((2, 2))
        for j in range(2):
            dx = np.zeros(2); dx[j] = 1e-4
            J[:, j] = (np.array(crawler_static(level, *(x + dx), point, rods)["body_deg"]) - b) / 1e-4
        x = x - np.linalg.solve(J, r)
    return x


def boundary_body_points(level):
    """Proposed boundary (offset form) sampled like rpt.diamond_points: vertices + (+,+-) s 0.25/0.5/0.75 + (-,+-) 0.5."""
    Tp, Tm = THETA_V[level]
    pts = [("pitch+", 0.0, THETA0 + Tp), ("pitch-", 0.0, THETA0 - Tm), ("roll+", PHI_V, THETA0),
           ("roll-", -PHI_V, THETA0)]
    for s in (0.25, 0.5, 0.75):
        pts.append((f"r+p+{s:g}", s * PHI_V, THETA0 + (1 - s) * Tp))
        pts.append((f"r+p-{s:g}", s * PHI_V, THETA0 - (1 - s) * Tm))
    pts.append(("r-p+0.5", -0.5 * PHI_V, THETA0 + 0.5 * Tp))
    pts.append(("r-p-0.5", -0.5 * PHI_V, THETA0 - 0.5 * Tm))
    return pts


# ================================================================================================ A Chrono snapshots
def snapshot_analysis():
    from scipy.optimize import curve_fit
    out = {}
    c = P()
    for d in sorted(SNAP_DIR.iterdir()):
        if not d.is_dir():
            continue
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        z = np.load(d / "series.npz")
        t = z["t"]; rp = z["roll_pitch_deg"]
        lv, fl = res["level"], res["floor"]
        o = {"level": lv, "floor": fl, "floor_deg": res["floor_slope_deg"],
             "chrono_end_deg": res["chrono_end"]["body_roll_pitch_deg"],
             "cad_analytic_deg": res["analytic"]["body_roll_pitch_deg"]}
        w = t >= t[-1] - 20.0
        o["mean_last20s_deg"] = rp[w].mean(axis=0).tolist()
        o["span_last5s_deg"] = np.ptp(rp[t >= t[-1] - 5.0], axis=0).tolist()
        # decaying-sine fit of the pitch (and roll) after the 3 s gravity ramp + 2 s
        fits = {}
        for j, nm in ((0, "roll"), (1, "pitch")):
            sel = t >= 5.0
            tt = t[sel] - 5.0; yy = rp[sel, j]
            y0 = yy[-int(len(yy) * 0.3):].mean()
            yd = yy - y0
            # frequency guess from zero crossings
            zc = np.where(np.diff(np.sign(yd)) != 0)[0]
            f0 = (len(zc) / 2) / (tt[zc[-1]] - tt[zc[0]]) if len(zc) > 4 else 1.0
            A0 = np.max(np.abs(yd[: max(10, len(yd) // 10)]))

            def fn(tt_, c_, A, s, f, ph):
                return c_ + A * np.exp(-s * tt_) * np.cos(2 * np.pi * f * tt_ + ph)
            try:
                pp, _ = curve_fit(fn, tt, yy, p0=[y0, A0, 0.05, f0, 0.0], maxfev=40000)
                if pp[1] < 0:
                    pp[1] = -pp[1]; pp[4] += np.pi
                f = abs(pp[3]); zeta = pp[2] / math.hypot(pp[2], 2 * np.pi * f)
                resid = float(np.sqrt(np.mean((fn(tt, *pp) - yy) ** 2)))
                fits[nm] = {"mean_deg": float(pp[0]), "amp_t5_deg": float(pp[1]), "sigma_1_s": float(pp[2]),
                            "f_Hz": float(f), "zeta": float(zeta),
                            "amp_end_deg": float(pp[1] * math.exp(-pp[2] * tt[-1])), "rms_resid_deg": resid,
                            "zero_cross_f_guess_Hz": float(f0)}
            except RuntimeError as e:
                fits[nm] = {"error": repr(e)}
        o["fit"] = fits
        # normal-force difference Chrono - analytic decomposed as a rigid rotation (plane fit over active spheres)
        dN = np.array(res["sphere_normal_minus_analytic_N"])
        Nch = np.array(res["chrono_end"]["sphere_normal_N"])
        act = Nch > 0
        # Chrono sphere order: per track (left, right) 6 rollers then 6 end shoes (track-major, from the snapshot
        # loads); x / y from the YAML layout
        lay = c["p"]["contact"]["crawler"]["sphere_layout"]
        xs = [float(x) for x in lay["roller_x_m"]] + [float(x) for x in lay["end_shoe_x_m"]]
        yt = float(lay["track_centre_y_m"])
        xy = np.array([[x, s * yt] for s in (1.0, -1.0) for x in xs])
        A = np.column_stack([np.ones(act.sum()), xy[act, 0], xy[act, 1]])
        coef, *_ = np.linalg.lstsq(A, dN[act], rcond=None)
        kn = float(c["kcr"][0])
        o["dN_max_abs_N"] = float(np.max(np.abs(dN)))
        o["dN_plane_fit"] = {"heave_mm": float(coef[0] / kn * 1e3),
                             "pitch_deg_from_x_slope": float(math.degrees(coef[1] / kn)),
                             "roll_deg_from_y_slope": float(math.degrees(coef[2] / kn)),
                             "rms_resid_N": float(np.sqrt(np.mean((A @ coef - dN[act]) ** 2)))}
        o["chrono_minus_analytic_deg"] = (np.array(o["chrono_end_deg"]) - o["cad_analytic_deg"]).tolist()
        cb = res.get("crawler_bushing", {})
        o["yield_steps_after_ramp_total"] = int(np.sum(cb.get("yield_steps_after_ramp", [0])))
        o["yield_steps_last10s_total"] = int(np.sum(cb.get("yield_steps_last10s", [0])))
        o["contact_events"] = len(cb.get("events", []))
        o["last_event_t_s"] = float(cb["events"][-1][0]) if cb.get("events") else None
        o["slip_total_mm_max"] = float(np.max(cb.get("slip_total_mm", [0.0])))
        out[d.name] = o
    return out


# ================================================================================================ C reduced plant settle
def plant_settle(level, roll_g, pitch_g, kt_rel=1.0, t_avg=20.0):
    rmf.CONFIG.clear()
    pl = rmf.FlexPlant(level, roll_g, pitch_g)
    pl.ktcr = pl.kcr * kt_rel
    pl.ctcr = pl.ccr * math.sqrt(kt_rel)
    pl.step(np.zeros(4), int(round(rcc.SETTLE_ON_CRAWLER_S / pl.dt)))
    att0 = np.degrees(pl.attitude())
    n = int(round(t_avg / 0.05))
    A = np.empty((n, 2))
    for i in range(n):
        pl.step(np.zeros(4), int(round(0.05 / pl.dt)))
        A[i] = np.degrees(pl.attitude())
    return {"after_settle_deg": att0.tolist(), "mean_next20s_deg": A.mean(axis=0).tolist(),
            "span_next20s_deg": np.ptp(A, axis=0).tolist()}


def _settle_job(a):
    return a, plant_settle(*a)


# ================================================================================================ stage crawler
def stage_crawler():
    out = {"meta": {"theta0_deg": THETA0, "phi_v_deg": PHI_V, "theta_v_deg": THETA_V, "kt_rel_chrono": KT_REL_CHRONO}}
    t0 = time.perf_counter()
    snaps = snapshot_analysis()
    out["A_snapshots"] = snaps
    # B: quasi-static model at the snapshot floors, four variants
    B = {}
    for name, o in snaps.items():
        lv = o["level"]; rg, pg = o["floor_deg"]
        row = {}
        for pt_ in ("centre", "floor"):
            for rods in ("retracted", "e_op"):
                r = crawler_static(lv, rg, pg, pt_, rods)
                row[f"{pt_}|{rods}"] = r["body_deg"]
        rn = crawler_static(lv, rg, pg, "centre", "retracted", tangential=False)
        row["normal_only"] = rn["body_deg"]
        r = crawler_static(lv, rg, pg, "centre", "retracted")
        row["vs_cad_analytic_deg"] = (np.array(r["body_deg"]) - o["cad_analytic_deg"]).tolist()
        row["vs_chrono_mean_deg"] = (np.array(r["body_deg"]) - o["mean_last20s_deg"]).tolist()
        row["active_spheres"] = int(r["active"].sum())
        row["kn_x3_body_deg"] = crawler_static(lv, rg, pg, "centre", "retracted", kn_scale=3.0)["body_deg"]
        B[name] = row
    out["B_static_at_snapshots"] = B
    # C: reduced plant settle at the snapshot floors, crawler kt variants
    jobs = []
    for name, o in snaps.items():
        lv = o["level"]; rg, pg = o["floor_deg"]
        for ktr in (1.0, KT_REL_CHRONO, 0.3 * KT_REL_CHRONO, 3.0 * KT_REL_CHRONO):
            jobs.append((lv, rg, pg, ktr))
    _settle_job(jobs[0])            # numba compile in the main process
    from multiprocessing import Pool
    with Pool(WORKERS) as pool:
        res = pool.map(_settle_job, jobs, chunksize=1)
    C = {}
    for (lv, rg, pg, ktr), r in res:
        C[f"{lv}|{rg:.4f}|{pg:.4f}|kt{ktr:.4f}"] = r
    out["C_plant_settle"] = C
    # D: compliance map (B model, centre, retracted = Chrono L1 formulation), three levels
    D = {}
    for lv in dm.LEVELS:
        axis = {}
        for ang in (-3.7, -3.5, -3.2, -2.0, -1.0, 0.0, 1.0, 2.0, 3.2, 3.5, 3.6, 3.7):
            axis[f"pitch{ang:+g}"] = crawler_static(lv, 0.0, ang)["body_deg"]
        for ang in (1.0, 3.0, 4.4, 5.5, 5.6, 5.7):
            axis[f"roll{ang:+g}"] = crawler_static(lv, ang, 0.0)["body_deg"]
            axis[f"roll{-ang:+g}"] = crawler_static(lv, -ang, 0.0)["body_deg"]
        diam = {}
        for tag, r_, p_ in rpt.diamond_points(5.5, 3.5, "V") + rpt.diamond_points(4.4, 3.2, "P"):
            b = crawler_static(lv, r_, p_)["body_deg"]
            Tp, Tm = THETA_V[lv]
            dth = b[1] - THETA0
            u_off = abs(b[0]) / PHI_V + abs(dth) / (Tp if dth >= 0 else Tm)
            diam[tag] = {"floor": [r_, p_], "body": b,
                         "usage_offset_form": u_off,
                         "usage_plain_5.5_3.5": abs(b[0]) / 5.5 + abs(b[1]) / 3.5,
                         "usage_plain_5.6_3.85": abs(b[0]) / 5.6 + abs(b[1]) / 3.85,
                         "usage_operating_4.4_3.2": abs(b[0]) / 4.4 + abs(b[1]) / 3.2}
        img = {}
        for tag, br, bp in boundary_body_points(lv):
            fl = floor_of_body(lv, (br, bp))
            img[tag] = {"body": [br, bp], "floor": fl.tolist()}
        # operating-mode check on the crawler attitude: floor image of the 4.4 / 3.2 plain diamond (vertices)
        op = {}
        for tag, br, bp in (("pitch+", 0.0, 3.2), ("pitch-", 0.0, -3.2)):
            op[tag] = floor_of_body(lv, (br, bp)).tolist()
        # roll vertex of the plain operating diamond with the settle pitch: solve floor roll at body usage 1
        lo, hi = 3.0, 4.4
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            b = crawler_static(lv, mid, 0.0)["body_deg"]
            if abs(b[0]) / 4.4 + abs(b[1]) / 3.2 > 1.0:
                hi = mid
            else:
                lo = mid
        op["roll+_floor_at_usage1"] = lo
        D[lv] = {"axis_body_deg": axis, "diamond": diam, "boundary_floor_image": img, "operating_plain_floor": op}
    out["D_compliance"] = D
    out["wall_s"] = round(time.perf_counter() - t0, 1)
    return out


# ================================================================================================ stage envelope
def _env_job(a):
    import run_target_envelope as rte
    lv, rg, pg, rt, pt_ = a
    return a, rte.point(lv, rg, pg, rt, pt_)


def env_summary(pt_):
    import run_target_envelope as rte
    c = rte.ctx()
    return {"stroke_headroom_mm_50": (c.stroke - pt_["s_max_at_clr"]["50"]) * 1e3,
            "stroke_low_mm_50": pt_["s_min_at_clr"]["50"] * 1e3,
            "F_cyl_min_kN": min(pt_["F_cyl_min_N"], pt_["F_cyl_min_yaml_N"]) / 1e3,
            "F_cyl_max_kN": pt_["F_cyl_max_N"] / 1e3, "swivel_deg": pt_["beta_deg"],
            "rod_SF_min": pt_["rod_SF_min"], "util_ext_max": pt_["util_ext_max"], "util_yaml_max": pt_["util_yaml_max"],
            "L_ext_max_kN": max(pt_["L_ext_N"]) / 1e3, "L_yaml_max_kN": max(pt_["L_yaml_N"]) / 1e3,
            "feasible_50_10mm_guard_rod": rte.feasible(pt_, 50, 0.010, True, True),
            "feasible_50_0mm": rte.feasible(pt_, 50, 0.0, False, False)}


def stage_envelope(d):
    img = d["crawler"]["D_compliance"]
    jobs = []
    floors = {}
    for lv in dm.LEVELS:
        for tag, v in img[lv]["boundary_floor_image"].items():
            floors[f"{lv}|N:{tag}"] = (lv, *v["floor"])
        for tag, r_, p_ in rpt.diamond_points(5.5, 3.5, "V"):
            floors[f"{lv}|{tag}"] = (lv, r_, p_)
        for tag in ("pitch+", "pitch-"):     # floor images of the operating plain diamond (crawler attitude basis)
            floors[f"{lv}|OP:{tag}"] = (lv, *img[lv]["operating_plain_floor"][tag])
        floors[f"{lv}|OP:roll+"] = (lv, img[lv]["operating_plain_floor"]["roll+_floor_at_usage1"], 0.0)
        # uniform alternative Theta_v+ = 3.70 deg at every level (floor image of body (0, THETA0 + 3.70))
        floors[f"{lv}|U3.70:pitch+"] = (lv, *floor_of_body(lv, (0.0, THETA0 + 3.70)).tolist())
        floors[f"{lv}|plain3.85:pitch+"] = (lv, *floor_of_body(lv, (0.0, 3.85)).tolist())
        floors[f"{lv}|V:pitch+3.6"] = (lv, 0.0, 3.6)
        floors[f"{lv}|V:pitch-3.6"] = (lv, 0.0, -3.6)
    for k, (lv, rg, pg) in floors.items():
        jobs.append((lv, rg, pg, 0.0, 0.0))
    # rule A interplay: target grid inside the absolute diamond / axis caps, for a few boundary floors (top)
    tg_floors = ["top|N:pitch+", "top|N:pitch-", "top|N:roll+", "top|N:r+p+0.5", "top|N:r+p-0.5",
                 "bottom|N:pitch+", "bottom|N:roll+"]
    grid = [(round(r_, 2), round(p_, 2)) for r_ in np.arange(-4.0, 4.0 + 1e-9, 0.2)
            for p_ in np.arange(-3.0, 3.0 + 1e-9, 0.2)
            if abs(r_) / 4.4 + abs(p_) / 3.2 <= 1 + 1e-9]
    for k in tg_floors:
        lv, rg, pg = floors[k]
        for r_, p_ in grid:
            if (r_, p_) == (0.0, 0.0):
                continue
            # only targets the proposed relative rule could accept (others are skipped as rejected anyway)
            jobs.append((lv, rg, pg, r_, p_))
    from multiprocessing import Pool
    t0 = time.perf_counter()
    with Pool(WORKERS) as pool:
        res = pool.map(_env_job, jobs, chunksize=4)
    R = {a: r for a, r in res}
    out = {"floors": {}, "rule_A": {}}
    for k, (lv, rg, pg) in floors.items():
        out["floors"][k] = {"floor_deg": [rg, pg], **env_summary(R[(lv, rg, pg, 0.0, 0.0)])}
    snaps = d["crawler"]
    for k in tg_floors:
        lv, rg, pg = floors[k]
        tag = k.split("|N:")[1]
        body = img[lv]["boundary_floor_image"][tag]["body"]
        Tp, Tm = THETA_V[lv]
        acc_true = []; acc_off = []; acc_plain = []
        for r_, p_ in grid:
            pt_ = R.get((lv, rg, pg, r_, p_)) if (r_, p_) != (0.0, 0.0) else R[(lv, rg, pg, 0.0, 0.0)]
            ok = env_summary(pt_)["feasible_50_10mm_guard_rod"][0]
            # relative rule with the true floor and verification spans 5.5 / 3.5 (rule A as written, floor known)
            ut = abs(r_ - rg) / 5.5 + abs(p_ - pg) / 3.5
            # proposed offset form on the crawler attitude (floor estimate = body - (0, THETA0))
            dth = p_ - (body[1] - THETA0)
            uo = abs(r_ - body[0]) / PHI_V + abs(dth) / (Tm if dth >= 0 else Tp)
            # current code form on the crawler attitude, spans 5.6 / 3.85 (plain, no offset)
            up = abs(r_ - body[0]) / 5.6 + abs(p_ - body[1]) / 3.85
            for lst, u in ((acc_true, ut), (acc_off, uo), (acc_plain, up)):
                if u <= 1 + 1e-9:
                    lst.append({"t": [r_, p_], "feasible": ok})
        out["rule_A"][k] = {
            "floor_deg": [rg, pg], "body_deg": body, "grid_points": len(grid),
            **{nm: {"accepted": len(lst), "accepted_infeasible": sum(1 for e in lst if not e["feasible"]),
                    "max_abs_target_deg": [max((abs(e["t"][0]) for e in lst), default=None),
                                           max((abs(e["t"][1]) for e in lst), default=None)],
                    "infeasible": [e["t"] for e in lst if not e["feasible"]][:20]}
               for nm, lst in (("true_floor_5.5_3.5", acc_true), ("offset_form", acc_off),
                               ("plain_5.6_3.85", acc_plain))}}
    out["wall_s"] = round(time.perf_counter() - t0, 1)
    del snaps
    return out


# ================================================================================================ time domain
class KPlant(rpt.TPlant):
    """TPlant + crawler tangential override (RCFG['ktcr_rel_kn']: kt = s kn, ct = c_n sqrt(s); Chrono Q12 rule)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        s = rpt.RCFG.get("ktcr_rel_kn")
        self.ktcr_rel = None
        if s is not None:
            s = float(s)
            self.ktcr = self.kcr * s
            self.ctcr = self.ccr * math.sqrt(s)
            self.ktcr_rel = s


def td_one(case):
    rpt.TPlant = KPlant                     # re-assert in this (possibly spawned) process before every run
    case = dict(case); case["keep_series"] = True
    out = rpt.run_one(case)
    pl = rmf.LAST.get("plant")
    if "error" not in out:
        if not isinstance(pl, KPlant) or pl.case_id != case["id"]:
            raise RuntimeError("KPlant identity check failed")
        want = case.get("rcfg", {}).get("ktcr_rel_kn")
        if (want is None) != (pl.ktcr_rel is None) or (want is not None and abs(pl.ktcr_rel - want) > 1e-12):
            raise RuntimeError("crawler kt override mismatch")
        S = out["_series"]["S"]
        smot = np.asarray(S["x"]) + np.asarray(S["Ftrue"]) / pl.ko[None, :]
        out["s_motor_max_mm"] = (smot.max(axis=0) * 1e3).round(2).tolist()
        out["s_motor_min_mm"] = (smot.min(axis=0) * 1e3).round(2).tolist()
        out["sref_end_mm"] = (pl.sref * 1e3).round(2).tolist()
        out["ktcr_rel"] = pl.ktcr_rel
        t = np.asarray(S["t"])
        out["att_start_deg"] = [float(np.degrees(S["phi"][0])), float(np.degrees(S["theta"][0]))]
        out["clr_min_after_lift_mm"] = None
        if out.get("t_crawler_liftoff_s") is not None:
            post = t >= out["t_crawler_liftoff_s"] + 1.0
            if post.any():
                out["clr_min_after_lift_mm"] = round(float(np.min(np.asarray(S["clr"])[post])) * 1e3, 2)
    out.pop("_series", None)
    return out


def td_points(d):
    img = d["crawler"]["D_compliance"]
    pts = {}
    for lv in dm.LEVELS:
        for tag, v in img[lv]["boundary_floor_image"].items():
            pts[(lv, tag)] = tuple(v["floor"])
    return pts


def mkc(cid, lv, ang, mast="rigid", gainset=rpt.R1, seed=12345, **kw):
    c = rpt.mk(cid, "s6b", lv, f"N:{cid}", mast, gainset, seed=seed)
    c["angles"] = (float(ang[0]), float(ang[1]))
    for k, v in kw.items():
        if k == "rcfg_extra":
            c["rcfg"].update(v)
        else:
            c[k] = v
    return c


def td_cases(stage, d):
    pts = td_points(d)
    C = []
    if stage == "td_main":
        for (lv, tag), ang in pts.items():
            for mast in rpt.MASTS:
                C.append(mkc(f"main|{lv}|{mast}|{tag}", lv, ang, mast))
    elif stage == "td_robust":
        for (lv, tag), ang in pts.items():
            if lv != "top":
                continue
            for mast in rpt.MASTS:
                for s in (1, 2):
                    C.append(mkc(f"seed|{lv}|{mast}|{tag}|{s}", lv, ang, mast, seed=12345 + s))
                for s in range(3):
                    C.append(mkc(f"d0|{lv}|{mast}|{tag}|{s}", lv, ang, mast, rpt.R1 + "_d0", seed=12345 + s))
                for b in (0.69e9, 1.6e9):
                    C.append(mkc(f"beta|{lv}|{mast}|{tag}|{b:g}", lv, ang, mast, beta=b))
        for (lv, tag), ang in pts.items():
            if lv == "top" or tag not in ("pitch+", "pitch-", "roll+", "r+p+0.5"):
                continue
            for mast in rpt.MASTS:
                for b in (0.69e9, 1.6e9):
                    C.append(mkc(f"beta|{lv}|{mast}|{tag}|{b:g}", lv, ang, mast, beta=b))
                C.append(mkc(f"d0|{lv}|{mast}|{tag}|0", lv, ang, mast, rpt.R1 + "_d0"))
    elif stage == "td_kt":
        for (lv, tag), ang in pts.items():
            if tag not in ("pitch+", "pitch-", "roll+", "r+p+0.5", "r+p+0.25"):
                continue
            masts = ("rigid", "stiff") if lv == "top" else ("rigid",)
            for mast in masts:
                for s in (KT_REL_CHRONO, 0.3 * KT_REL_CHRONO, 3.0 * KT_REL_CHRONO):
                    C.append(mkc(f"kt|{lv}|{mast}|{tag}|{s:.4f}", lv, ang, mast, rcfg_extra={"ktcr_rel_kn": s}))
                    if lv == "top":
                        C.append(mkc(f"ktd0|{lv}|{mast}|{tag}|{s:.4f}", lv, ang, mast, rpt.R1 + "_d0",
                                     rcfg_extra={"ktcr_rel_kn": s}))
    elif stage == "td_ext":
        for (lv, tag), ang in pts.items():
            for mast in ("rigid", "stiff"):
                c = mkc(f"ext|{lv}|{mast}|{tag}", lv, ang, mast)
                lev = rpt_kin_ext(lv, ang)
                c["rcfg"]["kt_per_pad"] = rpt.kt_of_ext(lev).tolist(); c["kt_mode"] = "ext"
                C.append(c)
    else:
        raise ValueError(stage)
    return C


def rpt_kin_ext(lv, ang):
    return rpt.kin_internal(lv, float(ang[0]), float(ang[1]), "ext")["levelled_ext_m"]


def run_td(stage, d):
    cases = td_cases(stage, d)
    t0 = time.perf_counter()
    r0 = td_one(cases[0])                 # numba compile in the main process first
    from multiprocessing import Pool
    with Pool(WORKERS) as pool:
        rest = pool.map(td_one, cases[1:], chunksize=1)
    runs = [r0] + rest
    errs = [r for r in runs if "error" in r]
    return {"n": len(runs), "errors": len(errs), "error_samples": errs[:3], "wall_s": round(time.perf_counter() - t0, 1),
            "runs": runs}


# ================================================================================================ (A) budget, (B) touch
def compliance(level, rg, pg, **kw):
    b = crawler_static(level, rg, pg, **kw)["body_deg"]
    return [b[0] - rg, b[1] - pg]


def stage_budget():
    """Method (A) error budget: compliance Delta = crawler attitude - floor, nominal and variants (static model B;
    crawler kt enters only through the reduced plant settle, stage crawler C)."""
    out = {}
    floors = {"flat": (0, 0), "fdown3.2": (0, 3.2), "fdown3.5": (0, 3.5), "fup3.2": (0, -3.2), "fup3.5": (0, -3.5),
              "roll4.4": (4.4, 0), "roll5.5": (5.5, 0), "diag3": (2.1213, 2.1213), "r+p-0.5": (2.75, -1.75)}
    for lv in dm.LEVELS:
        row = {}
        for nm, (rg, pg) in floors.items():
            row[nm] = {"nominal": compliance(lv, rg, pg),
                       "kn_x3": compliance(lv, rg, pg, kn_scale=3.0),
                       "crawler_mass_+10%": compliance(lv, rg, pg, crawler_mass_frac=0.10),
                       "crawler_mass_-10%": compliance(lv, rg, pg, crawler_mass_frac=-0.10),
                       "floor_point": compliance(lv, rg, pg, point="floor"),
                       "rods_e_op": compliance(lv, rg, pg, rods="e_op")}
        out[lv] = row
    return out


def stage_touch_static():
    """Body attitude change on the crawler when pads take load (redistribution), static model."""
    out = {}
    F1 = 1.5 * F_MIN
    for lv in dm.LEVELS:
        for nm, (rg, pg) in (("flat", (0, 0)), ("fdown3.5", (0, 3.5)), ("fup3.5", (0, -3.5)), ("roll5.5", (5.5, 0))):
            b0 = np.array(crawler_static(lv, rg, pg)["body_deg"])
            row = {"base_deg": b0.tolist()}
            for i, leg in enumerate(LEGS):
                F = np.zeros(4); F[i] = F1
                row[f"one_{leg}_dAtt_deg"] = (np.array(crawler_static(lv, rg, pg, pad_F=F)["body_deg"]) - b0).tolist()
            for k_, F in (("all4_at_1.5Fmin", np.full(4, F1)), ("all4_at_30kN", np.full(4, 30e3))):
                try:
                    row[f"{k_}_dAtt_deg"] = (np.array(crawler_static(lv, rg, pg, pad_F=F)["body_deg"]) - b0).tolist()
                except RuntimeError:
                    row[f"{k_}_dAtt_deg"] = [float("nan"), float("nan")]   # active-set cycling (Newton)
            out[f"{lv}|{nm}"] = row
    return out


def touch_one(case):
    """Closed loop to READY; method (B) floor estimate from the four touch strokes."""
    rpt.TPlant = KPlant
    case = dict(case); case["keep_series"] = True
    out = rpt.run_one(case)
    pl = rmf.LAST.get("plant")
    if "error" in out:
        return out
    if not isinstance(pl, KPlant) or pl.case_id != case["id"]:
        raise RuntimeError("KPlant identity check failed")
    S = out.pop("_series")["S"]
    t = np.asarray(S["t"]); P = np.asarray(S["P"]); x = np.asarray(S["x"]); Ft = np.asarray(S["Ftrue"])
    phi = np.asarray(S["phi"]); th = np.asarray(S["theta"])
    Cc = P >= 1.5 * F_MIN
    lat = []
    for i in range(4):
        j = None; start = None
        for k in range(len(t)):
            if Cc[k, i]:
                start = k if start is None else start
                if t[k] - t[start] >= 0.5 - 1e-9:
                    j = k; break
            else:
                start = None
        lat.append((start, j))
    if any(j is None for _, j in lat):
        return {**{k: out.get(k) for k in ("id", "fails")}, "touch_error": "latch not found"}
    pad_rel = pl.pad_rel                                  # pad bottom (retracted) relative to com, body
    ks = pl.ks
    rg, pg = case["angles"]
    n_true = rpt.floor_normal(rg, pg)

    def att_R(k):
        """True body attitude (yaw neglected) at control sample k (the IMU-ideal attitude)."""
        return _rzyx(0.0, th[k], phi[k])

    def fit(points):
        A = np.column_stack([points[:, 0], points[:, 1], np.ones(4)])
        c_, *_ = np.linalg.lstsq(A, points[:, 2], rcond=None)   # z = a x + b y + c
        nn = np.array([-c_[0], -c_[1], 1.0]); return nn / np.linalg.norm(nn)

    def floor_angles(nw):
        # inverse of rpt.floor_normal: n = (tan th, -tan ph, 1)/|.| -> th = atan(nx/nz), ph = atan(-ny/nz)
        return [math.degrees(math.atan(-nw[1] / nw[2])), math.degrees(math.atan(nw[0] / nw[2]))]

    res = {}
    kL = [j for _, j in lat]; kC = [s for s, _ in lat]
    klast = max(kL)
    for var in ("piston_latch", "piston_cand", "motor_latch", "piston_latch_pen_corr"):
        kk = kC if var == "piston_cand" else kL
        pts_b = []
        for i in range(4):
            k = kk[i]
            s = x[k, i]
            if var == "motor_latch":
                s = s + Ft[k, i] / pl.ko[i]
            z = pad_rel[i, 2] - s
            if var == "piston_latch_pen_corr":
                z = z + (Ft[k, i] + pl.Wr[i]) / ks[i]
            pts_b.append([pad_rel[i, 0], pad_rel[i, 1], z])
        pts_b = np.array(pts_b)
        # (raw) all points in the body frame of the last latch, (corr) each point rotated by its own attitude
        nb = fit(pts_b)
        e_raw = np.array(floor_angles(att_R(klast) @ nb)) - [rg, pg]
        pts_w = np.array([att_R(kk[i]) @ pts_b[i] for i in range(4)])
        e_cor = np.array(floor_angles(fit(pts_w))) - [rg, pg]
        res[var] = {"err_raw_deg": e_raw.tolist(), "err_att_corrected_deg": e_cor.tolist()}
    a_first = np.degrees([phi[min(kC)], th[min(kC)]]); a_last = np.degrees([phi[klast], th[klast]])
    a0 = np.degrees([phi[0], th[0]])
    return {"id": case["id"], "level": case["level"], "angles": case["angles"], "fails": out.get("fails"),
            "min_true_cyl_force_kN": out.get("min_true_cyl_force_kN"),
            "t_cand_s": [round(float(t[k]), 3) for k in kC], "t_latch_s": [round(float(t[k]), 3) for k in kL],
            "F_at_latch_kN": [round(float(Ft[kL[i], i]) / 1e3, 2) for i in range(4)],
            "att_start_deg": a0.tolist(), "att_first_cand_deg": a_first.tolist(), "att_last_latch_deg": a_last.tolist(),
            "dAtt_first_to_last_deg": (a_last - a_first).tolist(), "dAtt_start_to_last_deg": (a_last - a0).tolist(),
            "B": res, "true_floor_deg": [rg, pg], "n_true": n_true.tolist()}


def _rzyx(psi, th, ph):
    cz, sz = math.cos(psi), math.sin(psi)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ _ry(th) @ _rx(ph)


def touch_cases():
    C = []
    fl = {"top": ("flat", "fdown3.5", "fup3.5", "roll5.5", "diag3"), "middle": ("fdown3.5", "fup3.5", "roll5.5"),
          "bottom": ("fdown3.5", "fup3.5", "roll5.5")}
    for lv, names in fl.items():
        for nm in names:
            ang = SNAP_FLOORS[nm]
            for mast in ("rigid", "stiff"):
                for seed in (12345, 12346):
                    for ktr in (None, KT_REL_CHRONO):
                        c = mkc(f"touch|{lv}|{nm}|{mast}|{seed}|{ktr}", lv, ang, mast, seed=seed)
                        if ktr is not None:
                            c["rcfg"]["ktcr_rel_kn"] = ktr
                        C.append(c)
    return C


def stage_touch():
    cases = touch_cases()
    t0 = time.perf_counter()
    r0 = touch_one(cases[0])
    from multiprocessing import Pool
    with Pool(WORKERS) as pool:
        rest = pool.map(touch_one, cases[1:], chunksize=1)
    return {"static": stage_touch_static(), "runs": [r0] + rest, "wall_s": round(time.perf_counter() - t0, 1)}


# ================================================================================================ report
def _passes(r):
    f = r.get("fails") or []
    mn = r.get("min_true_cyl_force_kN")
    return mn is not None and mn >= GUARD / 1e3 and not f


def report(d):
    cr = d.get("crawler", {})
    if cr:
        print("== A snapshots: chrono end / mean20 / cad analytic / fit (pitch f, zeta, amp_end) ==")
        for k, o in cr["A_snapshots"].items():
            fp = o["fit"].get("pitch", {}); fr = o["fit"].get("roll", {})
            print(f"{k:32s} end {o['chrono_end_deg'][0]:8.4f} {o['chrono_end_deg'][1]:8.4f} | mean {o['mean_last20s_deg'][0]:8.4f}"
                  f" {o['mean_last20s_deg'][1]:8.4f} | cad {o['cad_analytic_deg'][0]:8.4f} {o['cad_analytic_deg'][1]:8.4f}"
                  f" | span5 {o['span_last5s_deg'][1]:.4f} | p f {fp.get('f_Hz', 0):.3f} z {fp.get('zeta', 0):.4f}"
                  f" a_end {fp.get('amp_end_deg', 0):.4f} | r f {fr.get('f_Hz', 0):.3f} z {fr.get('zeta', 0):.4f}"
                  f" | dN {o['dN_max_abs_N']:.0f} fit dth {o['dN_plane_fit']['pitch_deg_from_x_slope']:.5f}"
                  f" | ev {o['contact_events']} last {o['last_event_t_s']}")
        print("== B static vs snapshots ==")
        for k, o in cr["B_static_at_snapshots"].items():
            print(f"{k:32s} centre|ret {o['centre|retracted'][0]:8.4f} {o['centre|retracted'][1]:8.4f}"
                  f" floor|eop {o['floor|e_op'][0]:8.4f} {o['floor|e_op'][1]:8.4f} vs cad {o['vs_cad_analytic_deg'][1]:+.5f}"
                  f" vs chrono mean {o['vs_chrono_mean_deg'][0]:+.5f} {o['vs_chrono_mean_deg'][1]:+.5f} kn x3 {o['kn_x3_body_deg'][1]:.4f}")
        print("== C plant settle ==")
        for k, o in cr["C_plant_settle"].items():
            print(f"{k:40s} {o['mean_next20s_deg'][0]:8.4f} {o['mean_next20s_deg'][1]:8.4f} span {o['span_next20s_deg'][1]:.4f}")
        print("== D boundary floor image ==")
        for lv, o in cr["D_compliance"].items():
            for tag, v in o["boundary_floor_image"].items():
                print(f"{lv:7s} {tag:10s} body {v['body'][0]:7.3f} {v['body'][1]:7.3f} floor {v['floor'][0]:7.4f} {v['floor'][1]:7.4f}")
            print(lv, "operating plain diamond floor image", o["operating_plain_floor"])
            worst = max(o["diamond"].items(), key=lambda kv: kv[1]["usage_offset_form"] if kv[0].startswith("V") else 0)
            print(lv, "max offset-form usage on V floor diamond:", worst[0], round(worst[1]["usage_offset_form"], 4))
            for tg, v in o["diamond"].items():
                if tg.startswith("V"):
                    print(f"   {tg:14s} body {v['body'][0]:7.4f} {v['body'][1]:7.4f} off {v['usage_offset_form']:.4f}"
                          f" plain55 {v['usage_plain_5.5_3.5']:.4f} plain5.6/3.85 {v['usage_plain_5.6_3.85']:.4f}")
    bd = d.get("budget")
    if bd:
        print("== (A) budget: compliance [roll, pitch] deg ==")
        for lv, row in bd.items():
            for nm, v in row.items():
                print(f"{lv:7s} {nm:9s} " + " ".join(f"{k}={v[k][0]:+.4f},{v[k][1]:+.4f}" for k in v))
    tc = d.get("touch")
    if tc:
        print("== touch static: dAtt on crawler ==")
        for k, v in tc["static"].items():
            print(k, {kk: [round(x, 4) for x in vv] for kk, vv in v.items()})
        print("== touch runs (B) ==")
        for r in tc["runs"]:
            if "B" not in r:
                print(r.get("id"), r.get("touch_error"), r.get("error")); continue
            b = r["B"]
            print(f"{r['id']:52s} F@latch {r['F_at_latch_kN']} dAtt f->l {np.round(r['dAtt_first_to_last_deg'], 4)}"
                  f" s->l {np.round(r['dAtt_start_to_last_deg'], 4)} | raw {np.round(b['piston_latch']['err_raw_deg'], 4)}"
                  f" cor {np.round(b['piston_latch']['err_att_corrected_deg'], 4)}"
                  f" motor {np.round(b['motor_latch']['err_att_corrected_deg'], 4)}"
                  f" pen {np.round(b['piston_latch_pen_corr']['err_att_corrected_deg'], 4)}"
                  f" cand {np.round(b['piston_cand']['err_att_corrected_deg'], 4)}")
    env = d.get("envelope")
    if env:
        print("== envelope (levelling to 0) ==")
        for k, o in env["floors"].items():
            print(f"{k:22s} floor {o['floor_deg'][0]:7.4f} {o['floor_deg'][1]:7.4f} head {o['stroke_headroom_mm_50']:6.1f} mm"
                  f" low {o['stroke_low_mm_50']:6.1f} Fmin {o['F_cyl_min_kN']:6.1f} sw {o['swivel_deg']:.2f}"
                  f" SF ext/C45 {o['rod_SF_min']['ext_C45']:.3f} yaml/20MnV6 {o['rod_SF_min']['yaml_20MnV6']:.3f}"
                  f" yaml/C45 {o['rod_SF_min']['yaml_C45']:.3f} util e/y {o['util_ext_max']:.2f}/{o['util_yaml_max']:.2f}"
                  f" L e/y {o['L_ext_max_kN']:.1f}/{o['L_yaml_max_kN']:.1f} ok {o['feasible_50_10mm_guard_rod']}")
        print("== rule A ==")
        for k, o in env["rule_A"].items():
            print(k, o["floor_deg"], o["body_deg"], {nm: (o[nm]["accepted"], o[nm]["accepted_infeasible"],
                                                         o[nm]["max_abs_target_deg"])
                                                    for nm in ("true_floor_5.5_3.5", "offset_form", "plain_5.6_3.85")})
    for st in ("td_main", "td_robust", "td_kt", "td_ext"):
        o = d.get(st)
        if not o:
            continue
        runs = o["runs"]
        print(f"== {st}: n {o['n']} errors {o['errors']} wall {o['wall_s']} s ==")
        fails = [r for r in runs if not _passes(r)]
        print("  not passing:", [(r["id"], r.get("min_true_cyl_force_kN"), r.get("fails")) for r in fails][:30])
        mins = sorted(runs, key=lambda r: r.get("min_true_cyl_force_kN") or 1e9)[:8]
        print("  lowest:", [(r["id"], r.get("min_true_cyl_force_kN"), r.get("min_true_leg")) for r in mins])
        smax = max(runs, key=lambda r: max(r.get("s_motor_max_mm") or [0]))
        print("  max motor stroke:", smax["id"], smax.get("s_motor_max_mm"))
        clr = [r.get("clr_min_after_lift_mm") for r in runs if r.get("clr_min_after_lift_mm") is not None]
        print("  min clearance after lift +1 s [mm]:", min(clr) if clr else None)
        print("  max ss att err:", max((r.get("ss_true_att_deg_maxabs") or 0) for r in runs))
        print("  max pressure bar:", max((r.get("max_pressure_bar") or 0) for r in runs))
        tg = [(r["id"], max(r["tang"].get("dyn_max_kN", [0]))) for r in runs if "tang" in r]
        print("  max pad tangential dyn:", max(tg, key=lambda x: x[1]) if tg else None)
        ut = []
        for r in runs:
            if "tang" in r and "ready" in r["tang"]:
                ut.append((r["id"], max(r["tang"]["ready"]["util"])))
        print("  max util at ready:", max(ut, key=lambda x: x[1]) if ut else None)


# ================================================================================================ main
def load():
    return json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}


def save(d):
    OUT_JSON.write_text(json.dumps(d, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)),
                        encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["crawler", "budget", "touch", "envelope", "td_main", "td_robust", "td_kt", "td_ext", "report"])
    a = ap.parse_args()
    d = load()
    if a.stage == "crawler":
        d["crawler"] = stage_crawler()
    elif a.stage == "budget":
        d["budget"] = stage_budget()
    elif a.stage == "touch":
        d["touch"] = stage_touch()
    elif a.stage == "envelope":
        d["envelope"] = stage_envelope(d)
    elif a.stage.startswith("td_"):
        d[a.stage] = run_td(a.stage, d)
    if a.stage != "report":
        d.setdefault("meta", {})["script"] = "04_scripts/01_dynamics/run_s6_slope_boundary_check.py"
        save(d)
    report(d)


if __name__ == "__main__":
    main()
