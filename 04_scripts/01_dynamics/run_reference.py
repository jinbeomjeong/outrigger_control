"""Compute the analytic reference values for the Chrono outrigger model (00_docs/01_dynamics/dynamics_model.md).

Run (dynamics-dev, activated):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_reference.py

Writes 06_analysis/00_dynamics/reference.json and prints a summary. Deterministic (no random numbers).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json"
DEG = 180.0 / math.pi
KC_RIGID = 1e13  # N/m, stands in for the rigid NSC contact (L2b-NSC); rod-on-floor mode ~ 50 kHz, removed from the tables
V12_L2B_OLD_KEY = "L2b_NSC_rev4_kt_in_floor_plane (superseded 2026-10-24, record)"


def r(x, n=6):
    """Round floats / arrays for JSON."""
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    return x


def sympy_hessian_check(body, pad_pts, kv, kh, F0, g):
    """Independent path: exact potential with a full ZYX rotation matrix, Hessian at q=0 (sympy)."""
    # Lazy import: importers of run_reference must also load in envs without sympy.
    import sympy as sp

    ux, uy, uz, ph, th, ps = sp.symbols("ux uy uz phi theta psi", real=True)
    Rx = sp.Matrix([[1, 0, 0], [0, sp.cos(ph), -sp.sin(ph)], [0, sp.sin(ph), sp.cos(ph)]])
    Ry = sp.Matrix([[sp.cos(th), 0, sp.sin(th)], [0, 1, 0], [-sp.sin(th), 0, sp.cos(th)]])
    Rz = sp.Matrix([[sp.cos(ps), -sp.sin(ps), 0], [sp.sin(ps), sp.cos(ps), 0], [0, 0, 1]])
    R = Rz * Ry * Rx
    u = sp.Matrix([ux, uy, uz])
    V = body.mass * g * uz
    for i in range(4):
        d = sp.Matrix([sp.Float(v, 17) for v in (pad_pts[i] - body.com)])
        D = u + (R - sp.eye(3)) * d
        c0 = F0[i] / kv[i]
        V += sp.Rational(1, 2) * kv[i] * (c0 - D[2]) ** 2 + sp.Rational(1, 2) * kh[i] * (D[0] ** 2 + D[1] ** 2)
    qs = [ux, uy, uz, ph, th, ps]
    grad = [sp.diff(V, a).subs({s: 0 for s in qs}) for a in qs]
    H = sp.hessian(V, qs).subs({s: 0 for s in qs})
    return np.array(grad, float), np.array(H, float)


def lift_reference(p, geo, e_op, k_L1, kt_L1, tests):
    """V4 reference (rev. 5): machine resting on a compliant crawler (kn_total, sphere layout), all legs extend from 0 at
    v_max (t = 0 = motor start), each leg stops with a step at its own e_op. Quasi-static active-set statics over the
    whole sequence (pads + crawler spheres, unilateral, vertical 3-DoF), crawler-on-floor modes for the settle length,
    and a linear 6-DoF L1 simulation of the residual vibration after the step stops.
    """
    from scipy.integrate import solve_ivp

    g, xy, v = geo.g, geo.pad_xy, geo.v_max
    touch = geo.touch_extension
    bw = dm.body_with_rods(p, geo, "top", e_op)   # rod x,y do not change with the extension
    W, cg = bw.mass * g, bw.com[:2]
    kn_tot = float(p["contact"]["crawler"]["kn_total_N_m"])
    c_tot = dm.crawler_damping_total(kn_tot, bw.mass)
    m_b = dm.body_from_params(p, "top").mass
    out = {
        "procedure": ("t < 0: machine settled on the crawler, legs fully retracted (initialise at the settled pose below). "
                      "t = 0: all four motors start at +v_max. Each leg stops with a velocity step at its own e_op "
                      "(rear first). Quasi-static statics (rate effects neglected), body rigid, crawler spheres and "
                      "pads unilateral vertical springs (pads: L1 kn)."),
        "time_origin": "t = 0 at motor start (not at simulation start)",
        "crawler_contact_assumptions": {
            "kn_total_N_m": kn_tot,
            "damping_ratio_heave (ASSUMPTION)": dm.CRAWLER_DEFAULTS["damping_ratio_heave"],
            "damping_total_N_s_m": r(c_tot),
            "mass_for_damping_kg (superstructure + 4 rods)": r(bw.mass),
            "gn_input_rule": "gn = (damping_total / n_spheres) / m_eff, m_eff = superstructure body mass (crawler spheres are on that body; rods are separate bodies)",
            "superstructure_body_mass_kg": r(m_b),
            "tangential": "SMC kt = gt = mu = 0 (no crawler tangential force in L1; horizontal drift before pad touch not judged; no lift on a sloped floor with this model)",
        },
    }
    sph_r = dm.CRAWLER_DEFAULTS["sphere_radius_m"]
    # layout D (YAML contact.crawler.sphere_layout, dynamics_model.md 3.8) + sensitivities: name -> (xy, k, gap, c each)
    xy_d, k_d, _ = dm.crawler_points(p); gap_d = dm.crawler_gaps(p); n_rol = int((gap_d <= 0).sum())
    s3 = dm.crawler_kn_scales(p)[-1]   # kn_total x3 (user decision 2026-10-20), dashpot x sqrt(3) (same heave zeta)
    layouts = {
        V4_LAYOUT_D: (xy_d, k_d, gap_d, c_tot / n_rol),
        V4_LAYOUT_D_K3: (xy_d, k_d * s3, gap_d, c_tot * math.sqrt(s3) / n_rol),
        V4_LAYOUT_ROLLERS_ONLY: (xy_d[:n_rol], k_d[:n_rol], gap_d[:n_rol], c_tot / n_rol),
        V4_LAYOUT_D_RIGID: (xy_d, k_d * RIGID_CRAWLER_SCALE, gap_d, c_tot * math.sqrt(RIGID_CRAWLER_SCALE) / n_rol),
    }
    out["crawler_contact_assumptions"]["layout_D"] = {
        "kn_per_sphere_N_m": r(k_d[0]), "c_per_sphere_N_s_m": r(c_tot / n_rol), "kn_total_sensitivity_scale": r(s3),
        "n_spheres (rollers gap 0, end shoes gapped)": [n_rol, len(xy_d) - n_rol]}
    A_pad = dm.support_matrix(xy)
    t_stop = e_op / v
    t_end = float(t_stop.max())
    lay_out = {}
    lay_events = {}
    for name, (pts, kc, gap, c_each) in layouts.items():
        A_cr = dm.support_matrix(pts)
        F_cr0, q0, act0 = dm.static_unilateral(pts, kc, -gap, W, cg)
        gap0 = touch + A_pad @ q0
        t_touch_kin = gap0 / v

        allxy = np.vstack([xy, pts]); allk = np.concatenate([k_L1, kc])

        def state(t):
            e = np.minimum(v * t, e_op)
            delta = np.concatenate([e - touch, -gap])
            F, q, act = dm.static_unilateral(allxy, allk, delta, W, cg)
            return F, q, act

        # event search: coarse grid, then bisection on the active-set flags
        tg = np.arange(0.0, t_end + 1e-9, 1e-3)
        flags = []
        for t in tg:
            _, _, act = state(t)
            flags.append(np.concatenate([act[:4], [act[4:].any()]]))
        flags = np.array(flags)
        ev = {}
        for col, lab in [(0, "FL"), (1, "FR"), (2, "RL"), (3, "RR"), (4, "crawler")]:
            ch = np.where(flags[1:, col] != flags[:-1, col])[0]
            if not len(ch):
                continue
            lo, hi = tg[ch[0]], tg[ch[0] + 1]
            f_lo = flags[ch[0], col]
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                _, _, a = state(mid)
                fm = a[col] if col < 4 else a[4:].any()
                lo, hi = (mid, hi) if fm == f_lo else (lo, mid)
            ev[lab] = 0.5 * (lo + hi)
        F_end, q_end, act_end = state(t_end); L1top = tests["L1_rigid_motor_lumped_contact"]["levels"]["top"]
        first = min(("FL", "FR", "RL", "RR"), key=lambda n: ev.get(n, np.inf))
        ent = {
            "n_spheres": len(pts), "n_floor_contact_spheres (gap 0)": int((gap <= 0).sum()),
            "track_centre_y_m": r(float(np.abs(pts[:, 1]).max())), "kn_per_sphere_N_m": r(float(kc[0])),
            "c_per_sphere_N_s_m": r(c_each),
            "settled_on_crawler (legs at 0)": {
                "q_about_origin (uz_mm, roll_deg, pitch_deg)": r([q0[0] * 1e3, np.degrees(q0[1]), np.degrees(q0[2])], 5),
                "crawler_sphere_forces_N": r(F_cr0, 5),
                "end_shoe_spheres_in_contact": int((act0 & (gap > 0)).sum()),
                "pad_gap_at_e0_mm": r(gap0 * 1e3, 5),
            },
            "pad_touch_time_kinematic_from_settled_pose_s": r(t_touch_kin, 5),
            "quasi_static_events_s": {
                "first_touch_leg": first,
                "first_touch_s": r(ev[first], 5),
                "touch_s (FL, FR, RL, RR)": r([ev.get(n, float("nan")) for n in dm.LEG_NAMES], 5),
                "crawler_fully_off_s": r(ev.get("crawler", float("nan")), 5),
                "leg_stop_s (FL, FR, RL, RR)": r(t_stop, 5),
            },
            "end_state (after the last stop)": {
                "pad_contact_force_N": r(F_end[:4]),
                "attitude_deg (roll, pitch)": r(np.degrees(q_end[1:]), 4),
                "crawler_min_clearance_mm": r(float((A_cr @ q_end + gap).min()) * 1e3, 5),
                "max_abs_diff_vs_V1_contact_force_N": r(float(np.abs(F_end[:4] - np.array(L1top["contact_force_N"])).max()), 3),
                "crawler_active_at_end": bool(act_end[4:].any()),
            },
        }
        lay_out[name] = ent
        lay_events[name] = (ev, pts, kc, q0, F_cr0, act0, c_each)
    out["layouts"] = lay_out
    out["rigid_crawler_reference_old (operating_point.time_to_touch_s)"] = r(touch / v, 5)

    # crawler-on-floor modes (legs retracted, crawler tangential stiffness 0, active springs only) -> settle length
    b0 = dm.body_with_rods(p, geo, "top", np.zeros(4)); M = dm.mass_6dof(b0); ev = lay_events[V4_LAYOUT_D][0]
    for name, key in ((V4_LAYOUT_D, V4_MODES_D), (V4_LAYOUT_D_K3, V4_MODES_D_K3)):
        _, pts, kc, _, F_cr0, act0, c_each = lay_events[name]
        pts3 = np.column_stack([pts[act0], np.full(int(act0.sum()), geo.crawler_bottom_z)])
        K = _stiff_n(b0, pts3, kc[act0], F_cr0[act0])
        C = np.zeros((6, 6))
        for j in range(len(pts3)):
            _, _, az = dm.a_vec(pts3[j] - b0.com)
            C += c_each * np.outer(az, az)
        fd, zd = dm.complex_modes(M, K, C)
        keep = fd > 0.05
        tau = 1.0 / (zd[keep] * 2 * np.pi * fd[keep])
        out[key] = {
            "f_Hz": r(fd[keep], 4), "zeta": r(zd[keep], 4), "tau_s": r(tau, 4), "active_spheres": int(act0.sum()),
            "note": "surge, sway, yaw have zero stiffness (no crawler tangential force) and are omitted; active springs only",
            "settle_length_s (ln(100) x max tau)": r(float(np.log(100) * tau.max()), 4),
        }

    # residual vibration after the step stops: linear 6-DoF L1 about the e_op equilibrium (top), crawler off
    cfg = tests["L1_rigid_motor_lumped_contact"]
    cn = np.array(cfg["c_pad_N_s_m"]); ct = np.array(cfg["c_tan_N_s_m"])
    pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
    Fc, _, _ = dm.static_loads(k_L1, xy, W, cg)
    K6 = dm.stiffness_6dof(bw, pad_pts, k_L1, kt_L1, Fc); M6 = dm.mass_6dof(bw)
    C6 = np.zeros((6, 6)); AZ = []
    for i in range(4):
        ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
        C6 += cn[i] * np.outer(az, az) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay)); AZ.append(az)
    AZ = np.array(AZ)
    t_s = float(ev["crawler"]) + 0.05

    def u(t):
        return np.minimum(v * t, e_op) - e_op, np.where(v * t < e_op, v, 0.0)

    def rhs(t, y):
        uu, ud = u(t)
        Q = AZ.T @ (k_L1 * uu + cn * ud)
        return np.concatenate([y[6:], np.linalg.solve(M6, Q - K6 @ y[:6] - C6 @ y[6:])])

    uu0, ud0 = u(t_s)
    y0 = np.concatenate([np.linalg.solve(K6, AZ.T @ (k_L1 * uu0)), np.linalg.solve(K6, AZ.T @ (k_L1 * ud0))])
    # integrate piecewise (input kinks at the stops)
    seg = [t_s] + sorted(set(float(x) for x in t_stop)) + [t_end + 20.0]
    T, Y = [], []
    y = y0
    for a, b_ in zip(seg[:-1], seg[1:]):
        sol = solve_ivp(rhs, (a, b_), y, method="DOP853", rtol=1e-10, atol=1e-13, max_step=2e-3, dense_output=False)
        T.append(sol.t); Y.append(sol.y); y = sol.y[:, -1]
    T = np.concatenate(T); Y = np.concatenate(Y, axis=1)
    rp = np.degrees(Y[3:5])
    f1 = cfg["levels"]["top"]["f_damped_Hz"][0]

    def amp(t_from):
        m = (T >= t_end + t_from) & (T <= t_end + t_from + 1.0 / f1)
        return r(np.abs(rp[:, m]).max(axis=1), 4)

    out["residual_after_last_stop_linear_L1 (deg, max |dev| over one 1st-rocking period)"] = {
        "model": "linear 6-DoF L1 (top) with reference damping, motor = pad-spring base displacement; start quasi-static 0.05 s after crawler off",
        "integrator": "solve_ivp DOP853 rtol 1e-10 atol 1e-13, piecewise at the stops",
        "t_last_stop_s": r(t_end, 5),
        "roll_pitch_at_0s": amp(0.0), "roll_pitch_at_5s": amp(5.0), "roll_pitch_at_10s": amp(10.0), "roll_pitch_at_15s": amp(15.0), "last_time_above_0.001deg_after_last_stop_s": r(float(T[np.abs(rp).max(axis=0) > 1e-3].max()) - t_end, 4),
    }
    return out


def _stiff_n(body, pts3, k, F0):
    """stiffness_6dof for any number of vertical-only spring points (kh = 0)."""
    K = np.zeros((6, 6))
    for i in range(len(pts3)):
        d = pts3[i] - body.com
        _, _, az = dm.a_vec(d)
        K += k[i] * np.outer(az, az)
        K[3:, 3:] -= F0[i] * dm._hz(d)
    return K


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    g = geo.g
    A_ = dm.ASSUMPTIONS
    res = {"meta": {
        "script": "04_scripts/01_dynamics/run_reference.py",
        "params": "02_params/rexome33.yaml",
        "frame": "body: x forward, y left, z up; level body = world axes; origin = CAD origin",
        "gravity_m_s2": [0.0, 0.0, -g],
        "angles": "roll phi about +x, pitch theta about +y (small angles); reported in deg where *_deg",
        "leg_order": list(dm.LEG_NAMES),
        "assumptions": A_,
    }}

    # ------------------------------------------------------------ operating point
    touch = geo.touch_extension
    e_op = touch + A_["crawler_clearance_m"]
    res["operating_point"] = {
        "touch_extension_m": r(touch), "levelled_extension_m": r(e_op),
        "remaining_stroke_m": r(geo.stroke - e_op),
        "time_to_touch_s": r(touch / geo.v_max),
    }

    # ------------------------------------------------------------ stiffness table
    wc = dm.k_concrete_westergaard()
    kc_nom = wc["k_slab_N_m"]
    ko = dm.k_oil(e_op)
    kr = dm.k_rod()
    kf = A_["frame_bracket_stiffness_N_m"]
    ko_eff = dm.series(ko, kr, kf)  # everything between body and pad bottom (axial)
    kv_H = dm.series(ko_eff, kc_nom)
    kh_guided = dm.k_leg_lateral_legs(geo, e_op, True)
    kh_free = dm.k_leg_lateral_legs(geo, e_op, False)
    res["stiffness"] = {
        "piston_area_m2": r(dm.piston_area()),
        "k_oil_N_m": r(ko), "k_oil_at_e0_N_m": r(dm.k_oil(0.0)), "k_oil_at_stroke_N_m": r(dm.k_oil(geo.stroke)),
        "k_rod_N_m": r(kr), "k_frame_N_m": kf,
        "k_axial_leg_N_m (oil+rod+frame)": r(ko_eff),
        "concrete_westergaard": {k: r(v) for k, v in wc.items()},
        "k_vertical_physical_N_m (leg+concrete)": r(kv_H),
        "k_lateral_leg_rigid_pad_N_m": r(kh_guided),
        "k_lateral_leg_swivel_pad_N_m": r(kh_free),
    }

    # ------------------------------------------------------------ statics
    xy = geo.pad_xy
    st = {}
    for lvl in dm.LEVELS:
        b = dm.body_from_params(p, lvl)
        F, q, act = dm.static_loads(np.ones(4), xy, b.mass * g, b.com[:2])
        yaml_F = np.array([p["superstructure"]["auger_levels"][lvl]["static_leg_loads_N"][n] for n in dm.LEG_NAMES])
        st[lvl] = {"equal_k_superstructure_only_N": r(F), "yaml_N": r(yaml_F),
                   "max_rel_diff_vs_yaml": r(np.max(np.abs(F - yaml_F) / yaml_F))}
    b_top = dm.body_from_params(p, "top")
    W_b = b_top.mass * g
    bw = dm.body_with_rods(p, geo, "top", e_op)
    W_tot = bw.mass * g
    F_eq, _, _ = dm.static_loads(np.ones(4), xy, W_b, b_top.com[:2])
    st["contact_force_incl_rods_N"] = r(F_eq + geo.rod_mass * g)
    st["total_weight_incl_rods_N"] = r(W_tot)
    # stiffness variations (superstructure weight, contact forces = these + rod weight)
    cases = {
        "equal": np.ones(4),
        "front_2x_stiffer": np.array([2, 2, 1, 1.0]),
        "rear_2x_stiffer": np.array([1, 1, 2, 2.0]),
        "FL_half": np.array([0.5, 1, 1, 1.0]),
        "RL_half": np.array([1, 1, 0.5, 1.0]),
        "FL_and_RR_half (diagonal)": np.array([0.5, 1, 1, 0.5]),
        "oil_column_by_extension (roll 2deg slope, physical model)": None,
    }
    var = {}
    for name, kk in cases.items():
        if kk is None:
            # left legs longer than right by track*tan(2deg): oil stiffness differs per leg
            ext = e_op + np.array([1, 0, 1, 0]) * np.abs(xy[:, 1]).sum() / 2 * math.tan(math.radians(2))
            kk = dm.series(dm.series(dm.k_oil(ext), kr, kf), kc_nom)
            var[name] = {"extension_m": r(ext), "k_N_m": r(kk)}
        F, _, _ = dm.static_loads(kk, xy, W_b, b_top.com[:2])
        var.setdefault(name, {})
        var[name].update({"k_rel": r(kk / kk.max()), "F_N": r(F), "change_vs_equal_N": r(F - F_eq)})
    st["stiffness_variation"] = var

    # sensitivity to extension error (twist)
    sens = {}
    n_tw = dm.twist_vector(xy)
    for name, k_leg in {
        "R_chrono_rigid_motor (k=k_concrete_slab)": np.full(4, kc_nom),
        "H_physical (oil+rod+frame+concrete)": kv_H,
        "R_rigid_halfspace (k=k_concrete_halfspace)": np.full(4, wc["k_halfspace_N_m"]),
    }.items():
        S = dm.load_sensitivity(k_leg, xy)
        Q = dm.attitude_sensitivity(k_leg, xy)
        lift = {}
        for i, nm in enumerate(dm.LEG_NAMES):
            # smallest +/- extension error on leg i that unloads some leg
            best = None
            for sgn in (+1, -1):
                col = S[:, i] * sgn
                with np.errstate(divide="ignore"):
                    dd = np.where(col < 0, -F_eq / col, np.inf)
                j = int(np.argmin(dd))
                cand = (sgn * dd[j], dm.LEG_NAMES[j])
                if best is None or abs(cand[0]) < abs(best[0]):
                    best = cand
            lift[nm] = {"delta_mm": r(best[0] * 1e3, 4), "unloaded_leg": best[1]}
        sens[name] = {
            "k_leg_N_m": r(k_leg),
            "dF_per_mm_N (rows=load leg, cols=extended leg)": r(S * 1e-3),
            "dq_per_mm (rows=uz_mm, roll_deg, pitch_deg; cols=leg)": r(np.vstack([Q[0], Q[1] * DEG * 1e-3, Q[2] * DEG * 1e-3])),
            "smallest_extension_error_to_unload_a_leg": lift,
            "twist_stiffness_N_per_m (load change along twist per twist extension)": r(float(n_tw @ S @ n_tw)),
        }
    st["extension_error_sensitivity"] = sens
    st["twist_vector"] = r(n_tw)
    res["statics"] = st

    # ------------------------------------------------------------ kinematics
    A = dm.support_matrix(xy)
    J = np.linalg.pinv(A)  # equal stiffness: q = J e  ([uz, phi, theta] per extension)
    kin = {"A (pad dz = A [uz, phi, theta])": r(A),
           "J=pinv(A) (rows uz, phi, theta per m extension)": r(J),
           "roll_deg_per_mm_extension": r(J[1] * DEG * 1e-3),
           "pitch_deg_per_mm_extension": r(J[2] * DEG * 1e-3),
           "note": "extension e pushes the pad down so the body point rises by e: A q = e (rigid floor, all pads in contact)"}
    # extension needed for 0.1 deg / 1 deg
    y_span_f = xy[0, 1] - xy[1, 1]; y_span_r = xy[2, 1] - xy[3, 1]; x_span = xy[0, 0] - xy[2, 0]
    kin["extension_diff_for_0.1deg_mm"] = {
        "roll_front_pair": r(y_span_f * math.tan(math.radians(0.1)) * 1e3),
        "roll_rear_pair": r(y_span_r * math.tan(math.radians(0.1)) * 1e3),
        "pitch": r(x_span * math.tan(math.radians(0.1)) * 1e3)}
    kin["time_for_0.1deg_at_vmax_s"] = {k: r(v * 1e-3 / geo.v_max) for k, v in kin["extension_diff_for_0.1deg_mm"].items()}

    def levelled_extension(slope_roll_deg, slope_pitch_deg, clearance):
        """Ground plane z = z0 + sx x + sy y (sx = -tan(pitch), sy = tan(roll) for a ground that,
        if the machine sat on it, would give body roll/pitch of the given sign). Body level.
        Choose body height so that min crawler clearance = clearance; returns e (4,)."""
        sx = -math.tan(math.radians(slope_pitch_deg)); sy = math.tan(math.radians(slope_roll_deg))
        (x0, x1), (y0, y1) = geo.crawler_xy_box
        corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
        # body height H (shift of body z): crawler bottom at z_cb + H >= ground + clearance at corners
        H = np.max(sx * corners[:, 0] + sy * corners[:, 1]) + clearance - geo.crawler_bottom_z
        zg_pad = sx * xy[:, 0] + sy * xy[:, 1]
        return geo.pad_z_retracted + H - zg_pad

    ex = {}
    for (ro, pi) in [(0, 0), (1, 0), (0, 1), (2, 0), (0, 2), (1, 1), (-2, 1.5)]:
        e = levelled_extension(ro, pi, A_["crawler_clearance_m"])
        ex[f"ground roll {ro} deg, pitch {pi} deg"] = {"extension_m": r(e, 4),
                                                       "feasible": bool(e.min() >= 0 and e.max() <= geo.stroke)}
    kin["levelling_examples (crawler clearance 50 mm, crawler box corners)"] = ex

    def max_slope(direction_deg, clearance):
        lo, hi = 0.0, 20.0
        for _ in range(60):
            mid = (lo + hi) / 2
            ro = mid * math.sin(math.radians(direction_deg)); pi = mid * math.cos(math.radians(direction_deg))
            e = levelled_extension(ro, pi, clearance)
            ok = e.min() >= 0 and e.max() <= geo.stroke
            lo, hi = (mid, hi) if ok else (lo, mid)
        return lo

    kin["max_levellable_ground_slope_deg"] = {
        f"clearance_{int(c*1000)}mm": {
            "pitch(+/-)": r([max_slope(0, c), max_slope(180, c)], 4),
            "roll(+/-)": r([max_slope(90, c), max_slope(270, c)], 4),
            "diagonal_45deg": r(max_slope(45, c), 4)} for c in (0.0, 0.05)}
    kin["note_slope"] = ("crawler treated as a rigid box x[-1.840,1.844] y[-1.366,1.366] at z=-1.0509 (bbox of the crawler "
                         "assembly in 01_cad/01_parts/parts_classified.csv); the crawler hangs from the body, so clearance is checked at its corners")
    res["kinematics"] = kin

    # ------------------------------------------------------------ modal analysis
    modal_out = {}
    sympy_check = None
    for lvl in dm.LEVELS:
        b = dm.body_from_params(p, lvl)
        bw = dm.body_with_rods(p, geo, lvl, e_op)
        pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
        h_cg = float(bw.com[2] - pad_pts[:, 2].mean())
        lv = {"cg_height_above_floor_m": r(h_cg)}
        Fc, _, _ = dm.static_loads(np.ones(4), xy, bw.mass * g, bw.com[:2])
        rigid_cases = {
            "R1_chrono_baseline (kv=kh=k_slab, rigid motors)": (np.full(4, kc_nom), np.full(4, kc_nom)),
            "R2 (kv=k_slab, kh=leg bending rigid pad)": (np.full(4, kc_nom), kh_guided),
            "R3_rigid_halfspace (kv=kh=k_halfspace)": (np.full(4, wc["k_halfspace_N_m"]), np.full(4, wc["k_halfspace_N_m"])),
        }
        for name, (kv, kh) in rigid_cases.items():
            K = dm.stiffness_6dof(bw, pad_pts, kv, kh, Fc)
            M = dm.mass_6dof(bw)
            w2, f, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
            lv[name] = {"f_Hz": r(f, 5), "omega_rad_s": r(np.sqrt(w2), 5), "mode_content": cls,
                        "orthogonality_err": r(orth, 3),
                        "geometric_stiffness_roll_Nm_rad": r(-bw.mass * g * h_cg)}
            if sympy_check is None and name.startswith("R1"):
                grad, Hs = sympy_hessian_check(bw, pad_pts, kv, kh, Fc, g)
                sympy_check = {"level": lvl, "case": name,
                               "max_abs_gradient_at_q0 (N, Nm)": r(np.abs(grad).max(), 3),
                               "max_rel_diff_hessian": r(np.abs(Hs - K).max() / np.abs(K).max(), 3)}
        # physical estimate, 10-DoF
        flex = {
            "H1_physical_nominal (rigid pad)": dict(ko=ko_eff, kc=np.full(4, kc_nom), kh=dm.series(kh_guided, kc_nom)),
            "H2_swivel_pad": dict(ko=ko_eff, kc=np.full(4, kc_nom), kh=dm.series(kh_free, kc_nom)),
            "H3_beta_0.69GPa": dict(ko=dm.series(dm.k_oil(e_op, beta=0.69e9), kr, kf), kc=np.full(4, kc_nom), kh=dm.series(kh_guided, kc_nom)),
            "H4_beta_1.6GPa": dict(ko=dm.series(dm.k_oil(e_op, beta=1.6e9), kr, kf), kc=np.full(4, kc_nom), kh=dm.series(kh_guided, kc_nom)),
            "H5_kc_1e8": dict(ko=ko_eff, kc=np.full(4, 1e8), kh=dm.series(kh_guided, 1e8)),
            "H6_kc_halfspace": dict(ko=ko_eff, kc=np.full(4, wc["k_halfspace_N_m"]), kh=dm.series(kh_guided, wc["k_halfspace_N_m"])),
        }
        for name, kw in flex.items():
            M, K, C, labels, Fcont = dm.model_10dof(b, geo, e_op, **kw)
            w2, f, Phi, cls, orth = dm.modal(M, K, labels)
            lv[name] = {"f_Hz": r(f, 5), "mode_content": cls, "orthogonality_err": r(orth, 3)}
        # damping proposal: per-pad vertical dashpot that gives zeta_target in heave of R1
        kv = np.full(4, kc_nom)
        K = dm.stiffness_6dof(bw, pad_pts, kv, kv, Fc); M = dm.mass_6dof(bw)
        w2, f, Phi, cls, _ = dm.modal(M, K, dm.DOF6)
        zt = A_["modal_damping_ratio_body"]
        i_heave = [j for j, c in enumerate(cls) if max(c, key=c.get) == "heave z"][0]
        c_pad = 2 * zt * math.sqrt(kc_nom * bw.mass / 4)
        Cm = np.zeros((6, 6))
        for i in range(4):
            ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
            Cm += c_pad * (np.outer(az, az) + np.outer(ax, ax) + np.outer(ay, ay))
        fd, zd = dm.complex_modes(M, K, Cm)
        lv["R1_damped (c_pad vertical=tangential)"] = {"c_pad_N_s_m": r(c_pad), "f_Hz": r(fd, 5), "zeta": r(zd, 4),
                                                       "heave_mode_index": i_heave}
        modal_out[lvl] = lv
    res["modal"] = modal_out
    res["modal"]["sympy_hessian_check"] = sympy_check

    # time step recommendation
    def dt_rec(fmax, ppc=50):
        T = 1 / fmax
        for dt in (1e-3, 5e-4, 2e-4, 1e-4, 5e-5, 2e-5, 1e-5):
            if dt <= T / ppc:
                return dt
        return 1e-5

    # rod local mode when the rod is a separate body between oil spring and contact
    f_rod_local = math.sqrt((ko_eff.mean() + kc_nom) / geo.rod_mass.mean()) / (2 * math.pi)
    f_rod_local_rigid = math.sqrt((ko_eff.mean() + wc["k_halfspace_N_m"]) / geo.rod_mass.mean()) / (2 * math.pi)
    fmax_R1 = max(max(modal_out[l]["R1_chrono_baseline (kv=kh=k_slab, rigid motors)"]["f_Hz"]) for l in dm.LEVELS)
    fmax_R3 = max(max(modal_out[l]["R3_rigid_halfspace (kv=kh=k_halfspace)"]["f_Hz"]) for l in dm.LEVELS)
    res["time_step"] = {
        "rule": "dt <= T_min / 50 (accuracy, >= 50 steps per period of the highest retained mode); stability of explicit contact needs dt < 2/omega_max",
        "R1_fmax_Hz": r(fmax_R1), "R1_dt_s": dt_rec(fmax_R1), "R1_stability_limit_s": r(2 / (2 * math.pi * fmax_R1)),
        "R3_fmax_Hz": r(fmax_R3), "R3_dt_s": dt_rec(fmax_R3),
        "H_rod_local_mode_Hz (slab)": r(f_rod_local), "H_dt_s": dt_rec(f_rod_local),
        "H_rod_local_mode_Hz (halfspace)": r(f_rod_local_rigid), "H_halfspace_dt_s": dt_rec(f_rod_local_rigid),
    }

    # ------------------------------------------------------------ references for the Chrono tests
    # three candidate Chrono configurations (00_docs/01_dynamics/dynamics_model.md 3.3)
    zt = A_["modal_damping_ratio_body"]
    m_rod = float(geo.rod_mass.mean())
    k_L1 = kv_H  # lumped: rigid motor, contact stiffness = series(oil, rod, frame, concrete)
    kt_L1 = dm.series(kh_free, kc_nom)  # lumped lateral: swivel leg bending in series with concrete kt
    c_o = 2 * zt * np.sqrt(ko_eff * W_tot / g / 4)        # oil-column damper (heave ~ zeta)
    c_o_moving = 2 * A_["leg_damping_ratio_moving"] * np.sqrt(ko_eff * W_tot / g / 4)  # valve open (L2, L2b moving)
    # contact damper: total damping on the rod local mode (oil + contact dashpots act in parallel on the rod)
    # set to zeta_rod = 0.3 -> c_c = 2*0.3*sqrt((ko+kc) m_rod) - c_o  (numerical hygiene for the 286 Hz mode)
    zeta_rod = 0.3
    c_c = 2 * zeta_rod * np.sqrt((ko_eff + kc_nom) * m_rod) - c_o
    configs = {
        "R1_rigid_motor_concrete (informational, excluded from load evaluation)": dict(kv=np.full(4, kc_nom), kh=np.full(4, kc_nom),
                                        c_pad=np.full(4, 2 * zt * math.sqrt(kc_nom * W_tot / g / 4))),
        # L1 (TEMPORARY DEFAULT, user decision 2026-10-19): rigid motor; contact kn = series(oil, rod, frame, concrete),
        # contact kt = series(swivel-leg lateral bending, concrete kt); one contact sphere per pad at the ball
        "L1_rigid_motor_lumped_contact": dict(kv=k_L1, kh=kt_L1, c_pad=2 * zt * np.sqrt(l1_damping_stiffness(p, geo, e_op, k_L1) * W_tot / g / 4),
                                              c_tan=2 * zt * np.sqrt(kt_L1 * W_tot / g / 4)),
        # L2 (default, CLAUDE.md 2026-10-19): rigid prismatic guide -> lateral stiffness = contact kt only
        "L2_force_motor_oil_spring": dict(kv=kv_H, kh=np.full(4, kc_nom), c_o=c_o, c_c=c_c),
        # L2b (option): L2 + lateral leg compliance (swivel pad -> fixed-free bending, in series with contact kt)
        "L2b_force_motor_oil_spring_lateral_bushing": dict(kv=kv_H, kh=dm.series(kh_free, kc_nom), c_o=c_o, c_c=c_c),
        # L2b-NSC (rev. 4, operating plan B): ChSystemNSC rigid contact (stick exact). Concrete compliance is folded into
        # the axial force law (oil + rod + frame + concrete) and the concrete tangential compliance into the lateral
        # bushing, so the bushing equals the L1 kt. Rigid contact is represented by a very stiff kc without dashpot.
        "L2b_NSC_force_motor_axial_spring_lateral_bushing": dict(kv=kv_H, kh=kt_L1, c_o=c_o, c_c=np.zeros(4),
                                                                 ko=kv_H, kc=np.full(4, KC_RIGID)),
    }
    tests = {}
    for name, cfg in configs.items():
        kv = cfg["kv"]
        lvl_out = {}
        for lvl in dm.LEVELS:
            b = dm.body_from_params(p, lvl)
            bw = dm.body_with_rods(p, geo, lvl, e_op)
            # contact forces incl. rods; attitude from the superstructure problem (rod weight acts below the spring
            # in L2, and at the pad axis in R1/L1 -> both add m_rod g to each pad without moment about the pads)
            if name.startswith("L2"):
                Fb, qb, _ = dm.static_loads(kv, xy, b.mass * g, b.com[:2])
            else:
                Fb, qb, _ = dm.static_loads(kv, xy, bw.mass * g, bw.com[:2])
                Fb = Fb - geo.rod_mass * g
            Fc = Fb + geo.rod_mass * g
            S = dm.load_sensitivity(kv, xy)
            Q = dm.attitude_sensitivity(kv, xy)
            thr = {}
            thr_min = {}
            F_min = A_["F_min_fraction_of_mean_leg_load"] * b.mass * g / 4  # cylinder-force basis
            for i, nm in enumerate(dm.LEG_NAMES):
                for sgn, lab in ((1, "+"), (-1, "-")):
                    col = S[:, i] * sgn
                    with np.errstate(divide="ignore"):
                        dd = np.where(col < 0, -Fc / col, np.inf)
                        dm_ = np.where(col < 0, -(Fb - F_min) / col, np.inf)
                    j = int(np.argmin(dd))
                    thr[f"{nm}{lab}"] = {"delta_mm": r(dd[j] * 1e3, 4), "unloaded_leg": dm.LEG_NAMES[j]}
                    j = int(np.argmin(dm_))
                    thr_min[f"{nm}{lab}"] = {"delta_mm": r(dm_[j] * 1e3, 4), "leg_at_F_min": dm.LEG_NAMES[j]}
            if name.startswith("L2"):
                M, K, C, labels, _ = dm.model_10dof(b, geo, e_op, ko=cfg.get("ko", ko_eff), kc=cfg.get("kc", np.full(4, kc_nom)),
                                                    kh=cfg["kh"],
                                                    co=cfg["c_o"], cc=cfg["c_c"], ch=2 * zt * np.sqrt(cfg["kh"] * W_tot / g / 4))
                _, f_und, Phi, mcls, _ = dm.modal(M, K, labels)
                fd, zd = dm.complex_modes(M, K, C)
                ref_pt, coords = b.com, labels
            else:
                pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
                K = dm.stiffness_6dof(bw, pad_pts, kv, cfg["kh"], Fc)
                M = dm.mass_6dof(bw)
                Cm = np.zeros((6, 6))
                for i in range(4):
                    ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
                    ct = cfg.get("c_tan", cfg["c_pad"])
                    Cm += cfg["c_pad"][i] * np.outer(az, az) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay))
                _, f_und, Phi, mcls, _ = dm.modal(M, K, dm.DOF6)
                fd, zd = dm.complex_modes(M, K, Cm)
                ref_pt, coords = bw.com, list(dm.DOF6)
            lvl_out[lvl] = {
                "contact_force_N": r(Fc), "static_penetration_or_compression_mm": r(Fb / kv * 1e3 + geo.rod_mass * g / kv * 1e3 * (not name.startswith("L2"))),
                "static_attitude_deg (roll, pitch)": r(np.degrees(qb[1:]), 4),
                "dF_per_mm_FL_N": r(S[:, 0] * 1e-3), "droll_dpitch_per_mm_FL_deg": r(np.degrees(Q[1:, 0]) * 1e-3),
                "cylinder_force_N": r(Fb),
                "F_min_cylinder_N": r(F_min),
                "liftoff_threshold_single_leg (contact force 0)": thr,
                "F_min_threshold_single_leg (cylinder force = F_min)": thr_min,
                "f_undamped_Hz": r(f_und, 5), "mode_content": mcls, "f_damped_Hz": r(fd, 5), "zeta": r(zd, 3)}
            # rev. 5: mass-normalised undamped mode shapes of the 6 rigid-body modes for modal projection (V7)
            Ph = Phi[:, :6].copy()
            for jm in range(6):
                imax = int(np.argmax(np.abs(Ph[:6, jm])))
                if Ph[imax, jm] < 0:
                    Ph[:, jm] *= -1.0
            lvl_out[lvl]["mode_shapes_rev5"] = {
                "coordinates": coords,
                "reference_point_m (rotations about it, translations of it; body axes, level body = world)": r(ref_pt),
                "reference_point_meaning": ("CoM of superstructure + 4 rods at e_op (rods rigid with the body)"
                                            if coords == list(dm.DOF6) else
                                            "CoM of the superstructure alone; rod rows = absolute vertical rod displacement (up +)"),
                "units": "translations m, rotations rad (small angles), per sqrt(kg)",
                "Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)": r(Ph, 12),
                "mass_matrix (same coordinates)": r(M, 12),
                "projection": "eta = Phi^T M q (q = measured displacement from the static equilibrium); sign: largest body component of each column positive",
            }
        tests[name] = {"k_vertical_N_m": r(kv), "k_horizontal_N_m": r(cfg["kh"]),
                       **({"c_pad_N_s_m": r(cfg["c_pad"]), "c_tan_N_s_m": r(cfg.get("c_tan", cfg["c_pad"]))} if "c_pad" in cfg else {"c_oil_N_s_m": r(c_o), "c_oil_moving_N_s_m": r(c_o_moving), "c_contact_N_s_m": r(cfg["c_c"]),
                          "c_tangential_N_s_m": r(2 * zt * np.sqrt(cfg["kh"] * W_tot / g / 4))}),
                       "levels": lvl_out}
    res["chrono_test_references"] = tests

    # L1 time-step bound from numerical damping of EULER_IMPLICIT_LINEARIZED: zeta_num ~ omega dt / 2 <= 0.1 zeta_1
    L1_top = tests["L1_rigid_motor_lumped_contact"]["levels"]["top"]
    f1, z1 = L1_top["f_damped_Hz"][0], L1_top["zeta"][0]
    res["time_step"]["L1_numerical_damping_bound_s (omega1 dt/2 <= 0.1 zeta1, top)"] = r(0.2 * z1 / (2 * math.pi * f1), 4)
    # L2b-NSC: the rod is held by the rigid contact; if it separates, the rod rides on the axial spring alone
    res["time_step"]["L2b_NSC_rod_on_axial_spring_Hz (contact open)"] = r(math.sqrt(kv_H.mean() / m_rod) / (2 * math.pi), 4)
    res["time_step"]["L2b_NSC_dt_s"] = dt_rec(math.sqrt(kv_H.mean() / m_rod) / (2 * math.pi))
    N_top = tests["L2b_NSC_force_motor_axial_spring_lateral_bushing"]["levels"]["top"]  # same rocking rule as L1 (user decision 2026-10-20)
    res["time_step"]["L2b_NSC_numerical_damping_bound_s (omega1 dt/2 <= 0.1 zeta1, top)"] = r(0.2 * N_top["zeta"][0] / (2 * math.pi * N_top["f_damped_Hz"][0]), 4)

    # ------------------------------------------------------------ hydraulic circuit (00_docs/02_hydraulic/hydraulic_circuit.md, rev. 4)
    # double-acting cylinder, dual pilot-operated check valve on the cylinder: both chambers locked.
    # Rod-side (annulus) oil column acts in parallel with the head-side column while its pressure stays above ~0
    # (one-sided: it stiffens when the leg unloads / piston moves down, cavitates toward 0 when the leg loads).
    A_head = dm.piston_area()
    A_ann = math.pi / 4 * (dm.cylinder_value("bore_diameter_m") ** 2 - dm.cylinder_value("rod_diameter_m") ** 2)  # per leg (rev. 30)
    beta = A_["oil_bulk_modulus_eff_Pa"]
    L0 = A_["oil_dead_length_m"]
    L_rod_side = geo.stroke - e_op + L0
    k_rod_side = beta * A_ann / L_rod_side
    p_max = 210e5
    res["hydraulic_circuit"] = {
        "annulus_area_m2": r(A_ann), "head_area_m2": r(A_head),
        "rod_side_column_length_m (stroke - e_op + L0)": r(L_rod_side, 4),
        "k_rod_side_N_m": r(k_rod_side), "k_rod_side_over_k_oil_head": r(k_rod_side / ko, 4),
        "kv_with_rod_side_over_kv": r(dm.series(dm.series(ko + k_rod_side, kr, kf), kc_nom) / kv_H, 4),
        "max_pressure_Pa": p_max, "max_head_force_N": r(p_max * A_head), "max_rod_side_force_N": r(p_max * A_ann),
        "max_static_head_pressure_Pa": r(float(tests["L1_rigid_motor_lumped_contact"]["levels"]["top"]["cylinder_force_N"][0]) / A_head if np.ndim(A_head) == 0 else np.asarray(tests["L1_rigid_motor_lumped_contact"]["levels"]["top"]["cylinder_force_N"], float) / A_head),
        "flow_4_legs_at_vmax_L_min": r((4 * geo.v_max * A_head if np.ndim(A_head) == 0 else geo.v_max * float(np.sum(A_head))) * 6e4, 4), "pump_flow_L_min": 60.2,
    }

    # ------------------------------------------------------------ V12: sloped floor, levelled body, swivel pads
    b = dm.body_from_params(p, "top")
    slope = {"procedure": "pads placed on the floor with zero spring force at the levelled extension, then gravity (linear statics)",
             "contact_point": "sphere of radius = ball height (ASSUMPTION 0.06 m) centred at the ball; force through the ball centre"}
    # self-check: level floor must reproduce the vertical-spring static solution
    chk = dm.static_slope_10dof(b, geo, e_op, ko_eff, kc_nom, kc_nom)
    F_ref, _, _ = dm.static_loads(kv_H, xy, b.mass * g, b.com[:2])
    slope["self_check_level_max_abs_diff_N"] = r(np.abs(chk["F_cyl"] - F_ref).max(), 3)
    for ro, pi in [(0, 2), (2, 0), (-2, 1.5)]:
        ext = levelled_extension(ro, pi, A_["crawler_clearance_m"])
        ko_s = dm.series(dm.k_oil(ext), kr, kf)
        entry = {"extension_m": r(ext, 4)}
        for name, (ko_c, kn_c, kt_c) in {
            "L2": (ko_s, kc_nom, kc_nom),
            "L2b": (ko_s, kc_nom, dm.series(dm.k_leg_lateral_legs(geo, ext, False), kc_nom)),
            "L1": (np.full(4, 1e14), k_L1, kt_L1),
            # rev. 35 (user decision 2026-10-24, dynamics_model.md 5.22.3): S7 Chrono topology (kt barrel-rod
            # horizontal, NSC stick rigid), axial force law incl. concrete, constant bushing = L1 kt (YAML value)
            "L2b_NSC": (dm.series(ko_s, kc_nom), np.full(4, KC_RIGID), kt_L1),
            # rev. 4 value kept as a record: kt in the floor plane, rods laterally rigid (superseded for V12)
            V12_L2B_OLD_KEY: (dm.series(ko_s, kc_nom), np.full(4, KC_RIGID), kt_L1),
        }.items():
            if name == "L2b_NSC":
                sr = dm.static_slope_l2b_chrono_topology(b, geo, ext, ko_c, kt_c, slope_pitch_deg=pi,
                                                         slope_roll_deg=ro, kc_rigid=KC_RIGID)
            else:
                sr = dm.static_slope_10dof(b, geo, ext, ko_c, kn_c, kt_c, slope_pitch_deg=pi, slope_roll_deg=ro)
            kv_s = dm.series(ko_c, kn_c)
            F_ideal, _, _ = dm.static_loads(kv_s, xy, b.mass * g, b.com[:2])
            entry[name] = {"contact_vertical_N": r(sr["R"][:, 2]), "contact_horizontal_xy_N": r(sr["R"][:, :2]),
                           "cylinder_force_N": r(sr["F_cyl"]), "friction_utilisation_T_over_N": r(sr["mu_used"], 4),
                           "cylinder_force_if_no_horizontal_reaction_N": r(F_ideal),
                           "attitude_change_deg (roll, pitch)": r(np.degrees(sr["q"][3:5]), 4)}
        entry["L2b_NSC"]["model"] = ("rev. 35: dyn_model.static_slope_l2b_chrono_topology (S7 topology: kt barrel-rod "
                                     "horizontal, NSC stick rigid, rod rotation = body, linear, no P-delta)")
        slope[f"ground roll {ro} deg, pitch {pi} deg"] = entry
    res["slope_V12"] = slope

    # ------------------------------------------------------------ L1 sensitivity to the oil bulk modulus assumption
    sensb = {}
    b = dm.body_from_params(p, "top")
    bw = dm.body_with_rods(p, geo, "top", e_op)
    pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
    F_min = A_["F_min_fraction_of_mean_leg_load"] * b.mass * g / 4
    for beta in (A_['oil_bulk_modulus_range_Pa'][0], A_['oil_bulk_modulus_eff_Pa'], A_['oil_bulk_modulus_range_Pa'][1]):
        kL = dm.series(dm.series(dm.k_oil(e_op, beta=beta), kr, kf), kc_nom)
        Fb, qb, _ = dm.static_loads(kL, xy, bw.mass * g, bw.com[:2]); Fb = Fb - geo.rod_mass * g
        S = dm.load_sensitivity(kL, xy)
        Fc = Fb + geo.rod_mass * g
        with np.errstate(divide="ignore"):
            col = S[:, 0]
            lift = np.min(np.where(col < 0, -Fc / col, np.inf)); fm = np.min(np.where(col < 0, -(Fb - F_min) / col, np.inf))
        K = dm.stiffness_6dof(bw, pad_pts, kL, kt_L1, Fc)
        f = dm.modal(dm.mass_6dof(bw), K, dm.DOF6)[1]
        sensb[f"beta_{beta:.1e}"] = {"k_L1_N_m": r(kL), "contact_force_N": r(Fc), "penetration_mm": r(Fc / kL * 1e3),
                                     "static_pitch_deg": r(np.degrees(qb[2]), 4),
                                     "dF_per_mm_FL_N": r(S[:, 0] * 1e-3), "FL+_liftoff_mm": r(lift * 1e3, 4),
                                     "FL+_F_min_mm": r(fm * 1e3, 4), "f_Hz_top": r(f, 4)}
    res["L1_beta_sensitivity_top"] = sensb

    # ------------------------------------------------------------ stability
    stab_all = {}
    for swv in (True, False):
      poly = dm.support_polygon(geo, swivel=swv)
      stab = {"support_polygon_xy_m": r(poly, 5)}
      for lvl in dm.LEVELS:
          bw = dm.body_with_rods(p, geo, lvl, e_op)
          h = float(bw.com[2] - (geo.pad_z_retracted - e_op).mean())
          em = dm.edge_margins(poly, bw.com[:2])
          # keep the 4 long edges (front, rear, left, right) by inward normal direction
          named = {}
          for dist, a, b_, nin in em:
              ang = math.degrees(math.atan2(nin[1], nin[0]))
              key = {0: "rear edge (tip backward)", 180: "front edge (tip forward)",
                     90: "right edge (tip right)", -90: "left edge (tip left)"}
              for target, nm in key.items():
                  if abs(((ang - target + 180) % 360) - 180) < 20:
                      if nm not in named or dist < named[nm]["margin_m"]:
                          named[nm] = {"margin_m": r(dist, 5), "tip_angle_deg": r(math.degrees(math.atan2(dist, h)), 4)}
          min_d = min(d for d, *_ in em)
          # lift-off tilt: tilt gravity by alpha towards azimuth beta (body level), equal-stiffness loads
          lift = {}
          tip_ray = {}
          fmin_tilt = {}
          for beta in range(0, 360, 45):
              def min_load(alpha_deg):
                  al = math.radians(alpha_deg)
                  shift = h * math.tan(al) * np.array([math.cos(math.radians(beta)), math.sin(math.radians(beta))])
                  F, _, _ = dm.static_loads(kv_H, xy, bw.mass * g * math.cos(al), bw.com[:2] + shift, max_iter=1)
                  return F.min()
              lo, hi = 0.0, 45.0
              for _ in range(60):
                  mid = (lo + hi) / 2
                  lo, hi = (mid, hi) if min_load(mid) > 0 else (lo, mid)
              lift[f"azimuth_{beta}deg"] = r(lo, 4) if lo < 44.99 else "> 45"
              F_min_c = A_["F_min_fraction_of_mean_leg_load"] * b_top.mass * g / 4 + geo.rod_mass.mean() * g  # contact basis
              lo2, hi2 = 0.0, 45.0
              for _ in range(60):
                  mid = (lo2 + hi2) / 2
                  lo2, hi2 = (mid, hi2) if min_load(mid) > F_min_c else (lo2, mid)
              fmin_tilt[f"azimuth_{beta}deg"] = r(lo2, 4) if lo2 < 44.99 else "> 45"
              # rigid tip-over along the same azimuth: ray from the CoM projection to the polygon boundary
              u = np.array([math.cos(math.radians(beta)), math.sin(math.radians(beta))])
              ray = min(((a - bw.com[:2]) @ (-nin)) / (u @ (-nin)) for _, a, _, nin in em if u @ (-nin) > 1e-12)
              tip_ray[f"azimuth_{beta}deg"] = r(math.degrees(math.atan2(ray, h)), 4)
          stab[lvl] = {"cg_xy_m": r(bw.com[:2]), "cg_height_above_floor_m": r(h, 5), "edges": named,
                       "min_margin_m": r(min_d, 5), "min_tip_angle_deg": r(math.degrees(math.atan2(min_d, h)), 4),
                       "first_leg_liftoff_tilt_deg (azimuth 0 = gravity tilted toward +x i.e. nose-down slope)": lift,
                       "first_leg_F_min_tilt_deg (same azimuths)": fmin_tilt,
                       "tip_over_tilt_deg (same azimuths, rigid, CoM projection leaves the support polygon)": tip_ray}
      stab_all["swivel_pad_centres (default)" if swv else "rigid_pad_octagon_hull (comparison)"] = stab
    res["stability"] = stab_all

    # ------------------------------------------------------------ rev. 5: V4 lift with a compliant crawler
    res["lift_V4_compliant_crawler"] = add_dynamic_touch(lift_reference(p, geo, e_op, k_L1, kt_L1, tests), p, geo, e_op, k_L1, tests)
    add_ball_centre_bushing(res, p, geo, e_op, k_L1, kt_L1)   # rev. 13 (plan A): new keys only, nothing else changes

    res["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False)[:200000])
    print("written", OUT)


# reference.json lift_V4_compliant_crawler keys of the crawler layout D (dynamics_model.md 3.8, decided 2026-10-20).
# Defined here (not at the top) to keep the line numbers cited by 04_scripts/00_cad/export_params.py LINE_REFS.
V4_LAYOUT_D = "D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)"
V4_LAYOUT_D_K3 = "D kn_total x3 (sensitivity, YAML contact.crawler.kn_total_sensitivity_range_N_m)"
V4_LAYOUT_ROLLERS_ONLY = "sensitivity D without the end shoes (rollers only)"
V4_MODES_D = "crawler_on_floor_modes (layout D, legs at 0)"
V4_MODES_D_K3 = "crawler_on_floor_modes (layout D kn_total x3, legs at 0)"
V4_LAYOUT_D_RIGID = "D rigid crawler limit (kn_total x1e3, L2b-NSC V4)"
RIGID_CRAWLER_SCALE = 1.0e3   # crawler kn_total x1e3 stands in for the rigid NSC crawler contact (L2b-NSC V4)

# ------------------------------------------------------------ V4 dynamic touch times (user decision 2026-10-20)
# V4 is judged against the touch times of the damped vertical 3-DoF model below; the quasi-static times
# (quasi_static_events_s) stay in reference.json as a reference. Defined after main() so that the line numbers cited
# by 04_scripts/00_cad/export_params.py LINE_REFS do not move.
V4_DYN_KEY = "dynamic_events_s"
V4_DYN_T_BEFORE_S = 0.3        # integration starts this long before the earliest kinematic pad touch (body at rest)
V4_DYN_T_AFTER_S = 1.0         # ... and ends this long after the later of the last quasi-static touch / crawler off
V4_DYN_SOLVER = {"method": "DOP853", "rtol": 1e-9, "atol": 1e-12, "max_step_s": 1e-3}
V4_DYN_CHECK_MAX_STEP_S = 5e-4
V4_DYN_CHECK_METHOD = "Radau"
V4_DYN_TOL_S = 0.05            # V4 acceptance band per leg (chrono_build_plan.md V4), for the sensitivity margin only


def dynamic_touch(p, geo, e_op, k_pad, c_pad, xy_cr, k_cr, gap_cr, c_cr, t_from, t_to,
                  method="DOP853", max_step=1e-3, rtol=1e-9, atol=1e-12):
    """Damped vertical 3-DoF (uz, roll, pitch about the body-frame origin) through the V4 lift.

    Same model as run_leg_extension_loads.dynamic_check: M = m a a^T + blockdiag(0, I_xy), a = [1, cg_y, -cg_x],
    I_xy = roll/pitch block of the inertia about the CoM of superstructure (top) + 4 rods at e = 0 (rod x,y fixed);
    unilateral spring-dampers F = max(0, k c + c_d c_dot) for c > 0 (pads and crawler spheres), gravity on the CoM.
    Legs e(t) = min(v t, e_op) (V4 schedule, t = 0 = motor start). Start at t_from in the static pose on the crawler
    with zero velocity (exact: nothing moves the body before the first pad touch). Events: pad compression c_i = 0
    (touch / loss) and max over crawler spheres c_j = 0 (crawler fully off / re-contact), located by solve_ivp.
    """
    from scipy.integrate import solve_ivp

    g, v, touch, xy = geo.g, geo.v_max, geo.touch_extension, geo.pad_xy
    b0 = dm.body_with_rods(p, geo, "top", np.zeros(4))
    W, cg = b0.mass * g, b0.com[:2]
    a = np.array([1.0, cg[1], -cg[0]])
    M = b0.mass * np.outer(a, a)
    M[1:, 1:] += b0.inertia[:2, :2]
    xy_all = np.vstack([xy, xy_cr])
    A = dm.support_matrix(xy_all)
    k = np.concatenate([k_pad, k_cr])
    cd = np.concatenate([c_pad, c_cr])
    w = np.array([W, W * cg[1], -W * cg[0]])
    n_cr = len(xy_cr)

    def comp(t, y):
        e = np.minimum(v * t, e_op)
        ed = np.where(v * t < e_op, v, 0.0)
        c = np.concatenate([e - touch, -gap_cr]) - A @ y[:3]
        cdot = np.concatenate([ed, np.zeros(n_cr)]) - A @ y[3:]
        return c, cdot

    def rhs(t, y):
        c, cdot = comp(t, y)
        F = np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)
        return np.concatenate([y[3:], np.linalg.solve(M, A.T @ F - w)])

    evs = [(lambda t, y, i=i: comp(t, y)[0][i]) for i in range(4)] + [lambda t, y: comp(t, y)[0][4:].max()]
    _, q0, _ = dm.static_unilateral(xy_cr, k_cr, -gap_cr, W, cg)
    y0 = np.concatenate([q0, np.zeros(3)])
    c0, _ = comp(t_from, y0)
    if (c0[:4] >= 0).any():
        raise RuntimeError("a pad already touches at the start of the dynamic window")
    t_wall = time.perf_counter()
    sol = solve_ivp(rhs, (t_from, t_to), y0, method=method, rtol=rtol, atol=atol, max_step=max_step, events=evs)
    t_wall = time.perf_counter() - t_wall
    if sol.status != 0:
        raise RuntimeError(f"dynamic V4 integration failed: {sol.message}")
    touch_s, losses = [], []
    for i in range(4):
        te, ye = sol.t_events[i], sol.y_events[i]
        up = [t for t, y in zip(te, ye, strict=True) if comp(t, y)[1][i] > 0]
        down = [t for t, y in zip(te, ye, strict=True) if comp(t, y)[1][i] < 0]
        touch_s.append(up[0] if up else float("nan"))
        losses.append(len([t for t in down if up and t > up[0]]))
    te, ye = sol.t_events[4], sol.y_events[4]
    off = [t for t, y in zip(te, ye, strict=True) if comp(t, y)[1][4:][np.argmax(comp(t, y)[0][4:])] < 0]
    on = [t for t, y in zip(te, ye, strict=True) if off and t > off[0]]
    return {"touch_s": np.array(touch_s), "crawler_off_s": off[0] if off else float("nan"),
            "pad_contact_losses": losses, "crawler_events_after_off": len(on),
            "nfev": int(sol.nfev), "wall_s": t_wall}


def add_dynamic_touch(lift, p, geo, e_op, k_L1, tests):
    """Add dynamic_events_s (V4 basis, user decision 2026-10-20) to every lift_V4_compliant_crawler layout, plus the
    leg / crawler damping sensitivity. Uses the same layouts and dashpots as lift_reference; nothing else changes."""
    cfg = tests["L1_rigid_motor_lumped_contact"]
    c_pad = np.array(cfg["c_pad_N_s_m"], float)
    L1y = p["contact"]["rigid_floor"]["L1"]
    c_yaml = np.array([float(L1y["cn_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES])
    if np.abs(c_pad - c_yaml).max() > 1e-5 * c_yaml.max():
        raise RuntimeError(f"pad dashpots differ: reference {c_pad} vs YAML {c_yaml}")
    zeta_leg = float(L1y["derivation"]["damping_ratio"])
    zeta_cr = float(dm.CRAWLER_DEFAULTS["damping_ratio_heave"])
    v = geo.v_max
    t_stop = e_op / v
    # same layouts as lift_reference (kept in step: the per-sphere stiffness/dashpot are checked against its output)
    bw = dm.body_with_rods(p, geo, "top", e_op)
    c_tot = dm.crawler_damping_total(float(p["contact"]["crawler"]["kn_total_N_m"]), bw.mass)
    xy_d, k_d, _ = dm.crawler_points(p); gap_d = dm.crawler_gaps(p); n_rol = int((gap_d <= 0).sum())
    s3 = dm.crawler_kn_scales(p)[-1]
    layouts = {
        V4_LAYOUT_D: (xy_d, k_d, gap_d, c_tot / n_rol),
        V4_LAYOUT_D_K3: (xy_d, k_d * s3, gap_d, c_tot * math.sqrt(s3) / n_rol),
        V4_LAYOUT_ROLLERS_ONLY: (xy_d[:n_rol], k_d[:n_rol], gap_d[:n_rol], c_tot / n_rol),
        V4_LAYOUT_D_RIGID: (xy_d, k_d * RIGID_CRAWLER_SCALE, gap_d, c_tot * math.sqrt(RIGID_CRAWLER_SCALE) / n_rol),
    }
    sens = {}
    for name, (pts, kc, gap, c_each) in layouts.items():
        ent = lift["layouts"][name]
        if abs(ent["kn_per_sphere_N_m"] - r(float(kc[0]))) > 0 or abs(ent["c_per_sphere_N_s_m"] - r(c_each)) > 0:
            raise RuntimeError(f"layout {name!r} out of step with lift_reference")
        qs = ent["quasi_static_events_s"]
        t_kin = np.array(ent["pad_touch_time_kinematic_from_settled_pose_s"])
        t_from = float(np.floor((t_kin.min() - V4_DYN_T_BEFORE_S) * 1e3) / 1e3)
        t_to = float(np.ceil((max(max(qs["touch_s (FL, FR, RL, RR)"]), qs["crawler_fully_off_s"]) + V4_DYN_T_AFTER_S) * 1e3) / 1e3)
        cc = np.full(len(pts), c_each)

        def run(c_p=c_pad, c_c=cc, pts=pts, kc=kc, gap=gap, window=(t_from, t_to), **kw):
            o = dict(method=V4_DYN_SOLVER["method"], max_step=V4_DYN_SOLVER["max_step_s"],
                     rtol=V4_DYN_SOLVER["rtol"], atol=V4_DYN_SOLVER["atol"])
            o.update(kw)
            return dynamic_touch(p, geo, e_op, k_L1, c_p, pts, kc, gap, c_c, *window, **o)

        d = run()
        d_h = run(max_step=V4_DYN_CHECK_MAX_STEP_S)
        d_r = run(method=V4_DYN_CHECK_METHOD)
        conv_h = float(np.abs(d["touch_s"] - d_h["touch_s"]).max())
        conv_r = float(np.abs(d["touch_s"] - d_r["touch_s"]).max())
        first = dm.LEG_NAMES[int(np.argmin(d["touch_s"]))]
        dyn = {
            "first_touch_leg": first,
            "first_touch_s": r(float(d["touch_s"].min()), 5),
            "touch_s (FL, FR, RL, RR)": r(d["touch_s"], 5),
            "crawler_fully_off_s": r(d["crawler_off_s"], 5),
            "leg_stop_s (FL, FR, RL, RR)": r(t_stop, 5),
            "minus_quasi_static_touch_s (FL, FR, RL, RR)": r(d["touch_s"] - np.array(qs["touch_s (FL, FR, RL, RR)"]), 3),
            "pad_contact_losses_after_touch (FL, FR, RL, RR)": d["pad_contact_losses"],
            "crawler_contact_events_after_fully_off": d["crawler_events_after_off"],
            "meta": {
                "basis": "V4 judgement basis (user decision 2026-10-20): per-leg touch time within +-0.05 s of touch_s; "
                         "quasi_static_events_s kept as a reference only",
                "model": " ".join(dynamic_touch.__doc__.split("\n\n")[1].split()),
                "touch_definition": "first time the pad compression c_i = e_i - touch_extension_i - (A q)_i turns positive "
                                    "(spring-damper force > 0 from that instant)",
                "damping (ASSUMPTION)": {
                    "leg_axial_zeta (heave basis, YAML contact.rigid_floor.L1.derivation.damping_ratio)": zeta_leg,
                    "pad_dashpot_N_s_m (FL, FR, RL, RR) (YAML cn_per_pad_N_s_m)": r(c_pad),
                    "crawler_heave_zeta (dyn_model.CRAWLER_DEFAULTS)": zeta_cr,
                    "crawler_dashpot_per_sphere_N_s_m": r(c_each),
                },
                "integrator": {"method": V4_DYN_SOLVER["method"], "rtol": V4_DYN_SOLVER["rtol"],
                               "atol": V4_DYN_SOLVER["atol"], "max_step_s": V4_DYN_SOLVER["max_step_s"],
                               "events": "solve_ivp root finding on the pad and crawler compressions",
                               "nfev": d["nfev"]},
                "window_s": [t_from, t_to],
                "initial_condition": "static pose on the crawler (legs in the air), body velocity 0",
                "max_abs_touch_diff_vs_max_step_5e-4_s": r(conv_h, 3),
                "max_abs_touch_diff_vs_Radau_s": r(conv_r, 3),
            },
        }
        # insert right after the quasi-static block (other keys unchanged, order kept)
        new = {}
        for key, val in ent.items():
            new[key] = val
            if key == "quasi_static_events_s":
                new[V4_DYN_KEY] = dyn
        lift["layouts"][name] = new

        # damping sensitivity (leg zeta range of the YAML, crawler zeta range of CRAWLER_DEFAULTS)
        cases = {}
        for z in dm.ASSUMPTIONS["leg_damping_ratio_range"]:
            dz = run(c_p=c_pad * (float(z) / zeta_leg))
            cases[f"leg_zeta_{float(z):g}"] = dz
        for z in dm.CRAWLER_DEFAULTS["damping_ratio_heave_range"]:
            dz = run(c_c=cc * (float(z) / zeta_cr))
            cases[f"crawler_zeta_{float(z):g}"] = dz
        if name == V4_LAYOUT_D_RIGID:
            dz = run(c_c=cc * (1.0 / zeta_cr))
            cases["crawler_zeta_1 (near-plastic, NSC-like no rebound)"] = dz
        sens[name] = {
            "nominal touch_s (FL, FR, RL, RR)": r(d["touch_s"], 5),
            **{cn: {"touch_s (FL, FR, RL, RR)": r(dz["touch_s"], 5),
                    "shift_vs_nominal_s (FL, FR, RL, RR)": r(dz["touch_s"] - d["touch_s"], 3),
                    "max_abs_shift_s": r(float(np.abs(dz["touch_s"] - d["touch_s"]).max()), 3),
                    "within_V4_band_0.05_s": bool(np.abs(dz["touch_s"] - d["touch_s"]).max() <= V4_DYN_TOL_S),
                    "first_touch_leg": dm.LEG_NAMES[int(np.argmin(dz["touch_s"]))],
                    "pad_contact_losses_after_touch (FL, FR, RL, RR)": dz["pad_contact_losses"]}
               for cn, dz in cases.items()},
        }
    lift["V4_judgement_basis"] = (f"layouts/<layout>/{V4_DYN_KEY}/touch_s (FL, FR, RL, RR), tolerance +-{V4_DYN_TOL_S} s "
                                  "per leg (user decision 2026-10-20); quasi_static_events_s = reference only")
    lift["dynamic_touch_damping_sensitivity"] = {
        "description": ("dynamic_events_s repeated with the pad dashpots scaled to the leg zeta (heave basis, crawler "
                        "unchanged) and with the crawler dashpots scaled to the crawler zeta (pads unchanged); "
                        "same integrator and window as dynamic_events_s"),
        "nominal": {"leg_zeta": zeta_leg, "crawler_zeta": zeta_cr},
        "layouts": sens,
    }
    return lift


# ------------------------------------------------------------ rev. 13: L1 ground bushing at the ball centre (plan A)
# User decision 2026-10-20 (dynamics_model.md 5.3 ruling 4, rev. 13): the L1 ground bushing (tangential spring k_t
# and dashpot c_t) acts at the swivel ball centre (pad bottom + swivel_center_above_pad_bottom_m), not at the sphere
# contact point. Keys are only added; the rev. 5 L1 values (springs at the pad bottom) stay as history. Defined
# after main() so that the line numbers cited by 04_scripts/00_cad/export_params.py LINE_REFS do not move.
V7_BALL_KEY = "V7_ball_centre_bushing_rev13"
V12_EXACT_KEY = "extension_exact_m"
BETA_BALL_KEY = "f_Hz_top_ball_centre_rev13"
V12_SPHERE_KEY = "extension_sphere_touch_m"
V12_PLAN_A_KEY = "L1_plan_A_expected_chrono_minus_reference_rev13"
V7_DT_ZETA_NUM_S = (1e-4, 2e-4)   # general-run dt and the conditional 2e-4 s (dynamics_model.md 4.3)
V7_NORMAL_BAND = 0.10             # diagnosis 1: identified zeta within +-10 % of the reference (rev. 7 supplement)
V7_BUSHING_MISSING_ZETA3 = 0.005  # diagnosis 5: zeta_3 at or below this = bushing damping missing (rev. 7 value)
V12_NEWTON_TOL = 1e-13            # max |residual| / W of the slope statics (/ (W x gravity scale) < this / scale)
V12_NEWTON_MAX_ITER = 30
V12_LINEAR_EPS = 1e-4             # gravity scales eps, 2 eps of the "linear" solve; Richardson 2 F(eps)/eps - F(2eps)/(2eps)


def _l1_matrices(bw, xy, z_v, z_h, kv, kh, cn, ct, F0):
    """L1 6-DoF stiffness / damping about the CoM of bw (q = [ux, uy, uz, phi, theta, psi], small angles).

    Vertical spring kv + dashpot cn and the preload F0 (geometric term) at (x_i, y_i, z_v_i); tangential spring kh +
    dashpot ct (x and y) at (x_i, y_i, z_h_i). z_v = z_h = pad bottom reproduces dm.stiffness_6dof (rev. 5).
    Returns K, C_n, C_t, K_bushing (tangential spring part of K).
    """
    K = np.zeros((6, 6)); Kb = np.zeros((6, 6)); Cn = np.zeros((6, 6)); Ct = np.zeros((6, 6))
    for i in range(4):
        dv = np.array([xy[i, 0], xy[i, 1], z_v[i]]) - bw.com
        dh = np.array([xy[i, 0], xy[i, 1], z_h[i]]) - bw.com
        _, _, az = dm.a_vec(dv)
        ax, ay, _ = dm.a_vec(dh)
        Kh = kh[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        K += kv[i] * np.outer(az, az) + Kh
        K[3:, 3:] -= F0[i] * dm._hz(dv)
        Kb += Kh
        Cn += cn[i] * np.outer(az, az)
        Ct += ct[i] * (np.outer(ax, ax) + np.outer(ay, ay))
    return K, Cn, Ct, Kb


def _ball_heights(p):
    hb = np.array([float(p["legs"][n]["pad"]["swivel_center_above_pad_bottom_m"]) for n in dm.LEG_NAMES])
    if np.abs(hb - dm.ASSUMPTIONS["swivel_ball_height_above_pad_bottom_m"]).max() > 0:
        raise RuntimeError(f"ball height YAML {hb} differs from dyn_model ASSUMPTIONS")
    return hb


def _v7_ball_centre(p, geo, e_op, k_L1, kt_L1, tests):
    """V7 reference with the tangential spring / dashpot at the ball centre (rev. 13), all auger levels.

    Normal (SMC) force: the pad sphere is centred at the ball, so the normal force passes through the ball centre and
    the compression is the ball-centre drop -> vertical spring and its preload also at the ball centre. The variant
    'tangential only at the ball' isolates the bushing move. The damping values are the rev. 7 L1 values (unchanged).
    """
    import run_v7_diagnostic as v7d

    g, xy = geo.g, geo.pad_xy
    hb = _ball_heights(p)
    zt = dm.ASSUMPTIONS["modal_damping_ratio_body"]
    W_tot = dm.body_with_rods(p, geo, "top", e_op).mass * g
    cn = 2 * zt * np.sqrt(l1_damping_stiffness(p, geo, e_op, k_L1) * W_tot / g / 4)  # LOCK basis if the YAML says so (rev. 30)
    ct = 2 * zt * np.sqrt(kt_L1 * W_tot / g / 4)
    cfg = tests["L1_rigid_motor_lumped_contact"]
    if r(cn) != cfg["c_pad_N_s_m"] or r(ct) != cfg["c_tan_N_s_m"]:
        raise RuntimeError("L1 dashpots out of step with chrono_test_references")
    m_moving = float(p["legs"]["FL"]["moving_part"]["mass_kg"])
    m_eff_1kg = m_moving * 1.0 / (m_moving + 1.0)
    cases = {   # same multipliers (s_n, s_t) as run_v7_diagnostic.py
        "nominal": (1.0, 1.0),
        "c_t x2 (bushing input = c_t, R7 violation)": (1.0, 2.0),
        "c_n x2": (2.0, 1.0),
        "c_t x0.5": (1.0, 0.5),
        "c_t = 0 (bushing damping missing)": (1.0, 0.0),
        "c_n x0.0093 (floor body 1 kg)": (m_eff_1kg / m_moving, 1.0),
        "c_n -> 0 and c_t x2 (both errors)": (m_eff_1kg / m_moving, 2.0),
        "c_n x106.8 (g_n entered as c_n, unit error)": (m_moving, 1.0),
    }
    z_pad = geo.pad_z_retracted - e_op
    z_ball = z_pad + hb
    variants = {"rev5": (z_pad, z_pad), "tangential_only_at_ball": (z_pad, z_ball), "ball": (z_ball, z_ball)}

    def thresholds(z, zc):
        lo1, hi1 = (1 - V7_NORMAL_BAND) * z[0], (1 + V7_NORMAL_BAND) * z[0]
        lo2, hi2 = (1 - V7_NORMAL_BAND) * z[1], (1 + V7_NORMAL_BAND) * z[1]
        t2 = 0.5 * lo1
        t3 = 0.5 * (hi1 + zc["c_n x2"][0])
        t4 = 0.5 * (hi2 + (1 - V7_NORMAL_BAND) * zc["c_t x2 (bushing input = c_t, R7 violation)"][1])
        t5 = 0.5 * (z[2] + zc["c_t x2 (bushing input = c_t, R7 violation)"][2])
        return {"1_normal_zeta1_band": [lo1, hi1], "1_normal_zeta2_band": [lo2, hi2],
                "2_gn_or_floor_mass_error_zeta1_max": t2, "3_vertical_damping_excess_zeta1_min": t3,
                "4_ct_x2_suspect_zeta2_min (with zeta1_max(2) < zeta1 < zeta1_min(3))": t4,
                "5_ct_x2_confirmed_zeta3_min": t5, "5_bushing_damping_missing_zeta3_max": V7_BUSHING_MISSING_ZETA3}

    out = {}
    for lvl in dm.LEVELS:
        bw = dm.body_with_rods(p, geo, lvl, e_op)
        Fc, _, _ = dm.static_loads(k_L1, xy, bw.mass * g, bw.com[:2])
        M = dm.mass_6dof(bw)
        old = cfg["levels"][lvl]
        var = {}
        for vname, (zv, zh) in variants.items():
            K, Cn, Ct, Kb = _l1_matrices(bw, xy, zv, zh, k_L1, kt_L1, cn, ct, Fc)
            w2, f_und, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
            fd, zd = dm.complex_modes(M, K, Cn + Ct)
            var[vname] = dict(K=K, Cn=Cn, Ct=Ct, Kb=Kb, w2=w2, f=f_und, Phi=Phi, cls=cls, orth=orth, fd=fd, zd=zd)
        v5 = var["rev5"]
        if (r(v5["f"], 5) != old["f_undamped_Hz"] or r(v5["fd"], 5) != old["f_damped_Hz"]
                or r(v5["zd"], 3) != old["zeta"]):
            raise RuntimeError(f"{lvl}: rev. 5 L1 modal values not reproduced")
        vb = var["ball"]
        Ph = vb["Phi"][:, :6].copy()
        for jm in range(6):
            imax = int(np.argmax(np.abs(Ph[:6, jm])))
            if Ph[imax, jm] < 0:
                Ph[:, jm] *= -1.0
        om = np.sqrt(vb["w2"][:6])
        share = np.array([vb["Phi"][:, j] @ vb["Kb"] @ vb["Phi"][:, j] / vb["w2"][j] for j in range(6)])
        share5 = np.array([v5["Phi"][:, j] @ v5["Kb"] @ v5["Phi"][:, j] / v5["w2"][j] for j in range(6)])
        # diagnosis cases (mode tracking by MAC, as run_v7_diagnostic.py)
        zc, zc5 = {}, {}
        for cname, (sn, st) in cases.items():
            zc[cname] = v7d.tracked_modes(M, vb["K"], sn * vb["Cn"] + st * vb["Ct"])["zeta"]
            zc5[cname] = v7d.tracked_modes(M, v5["K"], sn * v5["Cn"] + st * v5["Ct"])["zeta"]
        nom = v7d.tracked_modes(M, vb["K"], vb["Cn"] + vb["Ct"])
        if np.abs(nom["zeta"] - vb["zd"][:6]).max() > 1e-12:
            raise RuntimeError(f"{lvl}: tracked and sorted complex modes differ")
        split = v7d.first_order_split(nom["Phi"], {"normal c_n": vb["Cn"], "tangential c_t": vb["Ct"]},
                                      nom["f_undamped_Hz"])
        Kn0 = vb["K"] - vb["Kb"]
        f_nobush = np.sqrt(np.clip(np.linalg.eigvals(np.linalg.solve(M, Kn0)).real, 0, None))
        f_nobush = np.sort(f_nobush)[-3:] / (2 * np.pi)
        thr, thr5 = thresholds(vb["zd"], zc), thresholds(v5["zd"], zc5)
        sep = {
            "2: floor-mass and unit errors below zeta1_max(2)": bool(
                zc["c_n x0.0093 (floor body 1 kg)"][0] < thr["2_gn_or_floor_mass_error_zeta1_max"]
                and zc["c_n -> 0 and c_t x2 (both errors)"][0] < thr["2_gn_or_floor_mass_error_zeta1_max"]),
            "3: c_n x2 above zeta1_min(3) > band(1)": bool(
                zc["c_n x2"][0] > thr["3_vertical_damping_excess_zeta1_min"] > thr["1_normal_zeta1_band"][1]),
            "4: c_t x2 zeta1 between (2) and (3), its zeta2 x0.9 above zeta2_min(4) > band(1)": bool(
                thr["2_gn_or_floor_mass_error_zeta1_max"] < zc["c_t x2 (bushing input = c_t, R7 violation)"][0]
                < thr["3_vertical_damping_excess_zeta1_min"]
                and (1 - V7_NORMAL_BAND) * zc["c_t x2 (bushing input = c_t, R7 violation)"][1]
                > thr["4_ct_x2_suspect_zeta2_min (with zeta1_max(2) < zeta1 < zeta1_min(3))"]
                > thr["1_normal_zeta2_band"][1]),
            "5: c_t x2 zeta3 above, c_t = 0 zeta3 below, nominal x0.9 above the missing threshold": bool(
                zc["c_t x2 (bushing input = c_t, R7 violation)"][2] > thr["5_ct_x2_confirmed_zeta3_min"]
                and zc["c_t = 0 (bushing damping missing)"][2] < V7_BUSHING_MISSING_ZETA3
                < (1 - V7_NORMAL_BAND) * vb["zd"][2]),
        }
        out[lvl] = {
            "model": ("L1 6-DoF (superstructure + 4 rods rigid with the body), pad sphere centred at the ball: vertical "
                      "spring k_n, dashpot c_n and preload (geometric term) at the ball centre, tangential spring k_t and "
                      "dashpot c_t (ground bushing, plan A) at the ball centre. k, c = rev. 7 L1 values (unchanged)"),
            "ball_centre_z_m (FL, FR, RL, RR) (pad bottom + swivel_center_above_pad_bottom_m)": r(z_ball),
            "f_undamped_Hz": r(vb["f"], 5), "mode_content": vb["cls"], "f_damped_Hz": r(vb["fd"], 5),
            "zeta": r(vb["zd"], 3), "zeta_4sig": r(vb["zd"], 4),
            "orthogonality_err": r(vb["orth"], 3),
            "change_vs_rev5 (springs at the pad bottom)": {
                "f_undamped_rel": r(vb["f"] / v5["f"] - 1, 3), "zeta_rel": r(vb["zd"] / v5["zd"] - 1, 3),
                "tangential_only_at_ball_f_undamped_rel": r(var["tangential_only_at_ball"]["f"] / v5["f"] - 1, 3),
                "tangential_only_at_ball_zeta_rel": r(var["tangential_only_at_ball"]["zd"] / v5["zd"] - 1, 3),
            },
            "mode_shapes": {
                "coordinates": list(dm.DOF6),
                "reference_point_m (rotations about it, translations of it; body axes, level body = world)": r(bw.com),
                "reference_point_meaning": "CoM of superstructure + 4 rods at e_op (rods rigid with the body)",
                "units": "translations m, rotations rad (small angles), per sqrt(kg)",
                "Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)": r(Ph, 12),
                "mass_matrix (same coordinates)": r(M, 12),
                "projection": "eta = Phi^T M q (q = measured displacement from the static equilibrium); sign: largest body component of each column positive",
            },
            "implicit_strain_energy_share r (bushing)": r(share, 4),
            "implicit_strain_energy_share r (bushing), rev5": r(share5, 4),
            "zeta_num_r_omega_dt_half": {f"{dt:g}": r(share * om * dt / 2, 3) for dt in V7_DT_ZETA_NUM_S},
            "f_undamped_Hz_without_bushing (3 non-zero modes, position independent)": r(f_nobush, 4),
            "V7_diagnostic": {
                "usage": ("subtract zeta_num (r omega dt / 2 at the run dt, or the V8(a) measurement) from the identified "
                          "zeta, then apply 1-5 (dynamics_model.md 5 V7 row); S2a judges the top level. Rules 2-4 "
                          "were set for the top level; where separation_checks is false (middle, bottom) confirm "
                          "with 5 (3rd mode)"),
                "zeta_cases": {k: r(v, 4) for k, v in zc.items()},
                "first_order_split_nominal": {k: r(v, 4) for k, v in split.items()},
                "tangential_share_nominal": r(split["tangential c_t"] / (split["tangential c_t"] + split["normal c_n"]), 4),
                "thresholds": {k: r(v, 4) for k, v in thr.items()},
                "threshold_rules": {
                    "1": "nominal zeta x (1 -+ 0.10)",
                    "2": "0.5 x lower bound of the zeta1 band (rev. 7 value 0.0035 = 0.5 x 0.0070)",
                    "3": "midpoint of the zeta1 band upper bound and zeta1 of c_n x2 (rev. 7: 0.0115)",
                    "4": "midpoint of the zeta2 band upper bound and 0.9 x zeta2 of c_t x2 (rev. 7 printed 0.0165, "
                         "set by hand inside the same gap; the rule gives the rev5 value below)",
                    "5": "c_t x2: midpoint of nominal zeta3 and zeta3 of c_t x2 (rev. 7: 0.056); missing: fixed 0.005",
                },
                "thresholds_same_rules_on_rev5": {k: r(v, 4) for k, v in thr5.items()},
                "separation_checks": sep,
            },
        }
    return out


def _levelled_extension_rev13(geo, slope_roll_deg, slope_pitch_deg, clearance):
    """Copy of main().levelled_extension (nested there): level body, floor z = sx x + sy y - H, pad bottoms on it."""
    sx = -math.tan(math.radians(slope_pitch_deg)); sy = math.tan(math.radians(slope_roll_deg))
    (x0, x1), (y0, y1) = geo.crawler_xy_box
    corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
    H = np.max(sx * corners[:, 0] + sy * corners[:, 1]) + clearance - geo.crawler_bottom_z
    zg_pad = sx * geo.pad_xy[:, 0] + sy * geo.pad_xy[:, 1]
    return geo.pad_z_retracted + H - zg_pad


def _rot_zyx(phi, theta, psi):
    cr, sr, cp, sp, cy, sy = math.cos(phi), math.sin(phi), math.cos(theta), math.sin(theta), math.cos(psi), math.sin(psi)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _slope_rigid_statics(p, geo, ext_pad, ext_sph, nrm, kn, kt, bushing_at_ball, gscale=1.0, s0=None):
    """Nonlinear statics of the L1 Chrono pad model on a tilted rigid plane (top level), body start level at the
    origin. Rigid body = superstructure + 4 rods at ext_sph (rigid motor). Sphere radius h_b centred at the ball;
    the floor plane holds the pad bottoms at ext_pad, so the spheres touch it exactly with ext_sph. Normal force
    k_n x penetration along n through the ball centre; bushing k_t in the plane between a body-fixed point (ball centre,
    or the start contact point if bushing_at_ball is False) and its start position (stick). Gravity -g z (x gscale).

    s0: start of the solve (default 0). Returns contact reactions R (4,3) floor -> pad [N], cylinder force [N],
    attitude [rad], in-plane bushing disp [m], solution s, max residual.
    """
    g, xy = geo.g, geo.pad_xy
    hb = _ball_heights(p)
    bw = dm.body_with_rods(p, geo, "top", ext_sph)
    W = bw.mass * g * gscale
    p0 = np.array([xy[0, 0], xy[0, 1], geo.pad_z_retracted[0] - ext_pad[0]])
    c_b = np.column_stack([xy, geo.pad_z_retracted - ext_sph + hb])
    a_b = c_b if bushing_at_ball else c_b - hb[:, None] * nrm[None, :]
    Pt = np.eye(3) - np.outer(nrm, nrm)

    def forces(s):
        R = _rot_zyx(*s[3:])
        cw = s[:3] + c_b @ R.T
        pa = s[:3] + a_b @ R.T
        pen = hb - (cw - p0) @ nrm
        Fn = kn * np.maximum(pen, 0.0)
        Ft = -kt[:, None] * ((pa - a_b) @ Pt.T)
        return R, cw, pa, Fn, Ft

    def resid(s):
        R, cw, pa, Fn, Ft = forces(s)
        f = (Fn[:, None] * nrm[None, :] + Ft).sum(0) + np.array([0.0, 0.0, -W])
        mo = np.cross(cw - s[:3], Fn[:, None] * nrm[None, :]).sum(0) + np.cross(pa - s[:3], Ft).sum(0)
        mo += np.cross(R @ bw.com, np.array([0.0, 0.0, -W]))
        return np.r_[f, mo] / (bw.mass * g * gscale)

    # Newton with a central-difference Jacobian of fixed absolute step (positions are ~1 m, the solution ~1e-3 m or,
    # at a small gravity scale, ~1e-7 m: a relative step as in fsolve would drown in round-off)
    s = np.zeros(6) if s0 is None else np.asarray(s0, float).copy()
    h = 1e-7
    for _ in range(V12_NEWTON_MAX_ITER):
        f0 = resid(s)
        if np.abs(f0).max() < V12_NEWTON_TOL / gscale:   # round-off floor ~ 1e-14 / gscale
            break
        J = np.column_stack([(resid(s + h * e) - resid(s - h * e)) / (2 * h) for e in np.eye(6)])
        s = s - np.linalg.solve(J, f0)
    else:
        raise RuntimeError(f"slope statics did not converge (residual {np.abs(resid(s)).max():.1e})")
    R, cw, pa, Fn, Ft = forces(s)
    Rf = Fn[:, None] * nrm[None, :] + Ft
    axis = R @ np.array([0.0, 0.0, 1.0])
    F_cyl = Rf @ axis - geo.rod_mass * g * gscale * axis[2]
    d = np.linalg.norm((pa - a_b) @ Pt.T, axis=1)
    return {"R": Rf, "F_cyl": F_cyl, "att": s[3:], "bush": d, "s": s, "resid": float(np.abs(resid(s)).max())}


def _v12_plan_a(res, p, geo, e_op, k_L1, kt_L1):
    """Adds to every slope_V12 case: the unrounded extensions and the expected Chrono - reference difference
    after plan A (P-delta only). The reference itself (static_slope_10dof) already acts through the ball centre."""
    A_ = dm.ASSUMPTIONS
    hb = _ball_heights(p)
    b = dm.body_from_params(p, "top")
    eps = V12_LINEAR_EPS
    for ro, pi in [(0, 2), (2, 0), (-2, 1.5)]:
        key = f"ground roll {ro} deg, pitch {pi} deg"
        ent = res["slope_V12"][key]
        ext = _levelled_extension_rev13(geo, ro, pi, A_["crawler_clearance_m"])
        if r(ext, 4) != ent["extension_m"]:
            raise RuntimeError(f"{key}: levelled extension out of step with slope_V12")
        sr = dm.static_slope_10dof(b, geo, ext, np.full(4, 1e14), k_L1, kt_L1, slope_pitch_deg=pi, slope_roll_deg=ro)
        if r(sr["R"][:, 2]) != ent["L1"]["contact_vertical_N"] or r(sr["F_cyl"]) != ent["L1"]["cylinder_force_N"]:
            raise RuntimeError(f"{key}: L1 slope reference not reproduced")
        nrm = sr["normal"]
        ext_sph = ext - hb * (1.0 / nrm[2] - 1.0)
        ent[V12_EXACT_KEY] = [float(x) for x in ext]
        ent[V12_SPHERE_KEY] = [float(x) for x in ext_sph]
        res_v = {}
        for nm, at_ball in (("ball", True), ("contact", False)):
            nl = _slope_rigid_statics(p, geo, ext, ext_sph, nrm, k_L1, kt_L1, at_ball)
            l1 = _slope_rigid_statics(p, geo, ext, ext_sph, nrm, k_L1, kt_L1, at_ball, gscale=eps, s0=nl["s"] * eps)
            l2 = _slope_rigid_statics(p, geo, ext, ext_sph, nrm, k_L1, kt_L1, at_ball, gscale=2 * eps, s0=nl["s"] * 2 * eps)
            li = {k: 2 * l1[k] / eps - l2[k] / (2 * eps) for k in ("R", "F_cyl", "att", "bush")}
            li["resid"] = max(l1["resid"], l2["resid"])
            res_v[nm] = (nl, li)   # linearisation about the unloaded start (quadratic term removed)
        nlb, lib = res_v["ball"]
        nlc, lic = res_v["contact"]
        R_ref, F_ref = sr["R"], sr["F_cyl"]
        att_ref = sr["q"][3:5]
        T_ref = np.linalg.norm(R_ref - np.outer(R_ref @ nrm, nrm), axis=1)
        ent[V12_PLAN_A_KEY] = {
            "model": " ".join(_slope_rigid_statics.__doc__.split("\n\n")[0].split()),
            "plan": ("plan A (user decision 2026-10-20): bushing at the ball centre -> the whole floor reaction passes "
                     "through the swivel centre as in the reference static_slope_10dof; the remaining Chrono - reference "
                     "difference is the geometric nonlinearity (P-delta) only"),
            "extension_used": f"{V12_SPHERE_KEY} (spheres touch the plane at the level start pose)",
            "reference_unchanged_check (linear ball model - reference)": {
                "contact_vertical_N": r(lib["R"][:, 2] - R_ref[:, 2], 3),
                "contact_horizontal_xy_N": r(lib["R"][:, :2] - R_ref[:, :2], 3),
                "cylinder_force_N": r(lib["F_cyl"] - F_ref, 3),
                "attitude_deg (roll, pitch)": r(np.degrees(lib["att"][:2] - att_ref), 3),
            },
            "expected_chrono_minus_reference": {
                "contact_vertical_N": r(nlb["R"][:, 2] - R_ref[:, 2], 4),
                "contact_horizontal_xy_N": r(nlb["R"][:, :2] - R_ref[:, :2], 4),
                "cylinder_force_N": r(nlb["F_cyl"] - F_ref, 4),
                "in_plane_force_N": r(np.linalg.norm(nlb["R"] - np.outer(nlb["R"] @ nrm, nrm), axis=1) - T_ref, 4),
                "attitude_deg (roll, pitch)": r(np.degrees(nlb["att"][:2] - att_ref), 4),
            },
            "P_delta_nonlinear_minus_linear_vertical_N": r(nlb["R"][:, 2] - lib["R"][:, 2], 4),
            "expected_bushing_in_plane_displacement_mm": r(nlb["bush"] * 1e3, 5),
            "expected_attitude_deg (roll, pitch)": r(np.degrees(nlb["att"][:2]), 5),
            "rev12_contact_point_bushing (S2a run before plan A)": {
                "chrono_model_minus_reference_vertical_N": r(nlc["R"][:, 2] - R_ref[:, 2], 4),
                "sphere_lever_part_vertical_N (contact - ball, nonlinear)": r(nlc["R"][:, 2] - nlb["R"][:, 2], 4),
            },
            "solver": (f"Newton (central-difference Jacobian, step 1e-7) on the 6 equilibrium equations / (W x gravity scale), max residual nonlinear "
                       f"{max(nlb['resid'], nlc['resid']):.1e}, linear {max(lib['resid'], lic['resid']):.1e}; "
                       f"linear = Richardson extrapolation of gravity x {eps:g} and x {2 * eps:g} to the tangent"),
        }


def add_ball_centre_bushing(res, p, geo, e_op, k_L1, kt_L1):
    """rev. 13 keys (plan A): V7 L1 reference with the bushing at the ball centre (per level, under the L1 level
    head), and per V12 case the unrounded extensions and the expected Chrono - reference difference."""
    tests = res["chrono_test_references"]
    v7 = _v7_ball_centre(p, geo, e_op, k_L1, kt_L1, tests)
    for lvl in dm.LEVELS:
        tests["L1_rigid_motor_lumped_contact"]["levels"][lvl][V7_BALL_KEY] = v7[lvl]
    _v12_plan_a(res, p, geo, e_op, k_L1, kt_L1)
    _beta_ball_centre(res, p, geo, e_op, kt_L1)


def _beta_ball_centre(res, p, geo, e_op, kt_L1):
    """L1 beta sensitivity: undamped frequencies (top) with both pad springs at the ball centre (rev. 13), next to
    f_Hz_top (rev. 5, springs at the pad bottom). Same k_L1(beta) as main(); the rev. 5 values are reproduced first."""
    A_ = dm.ASSUMPTIONS
    g, xy = geo.g, geo.pad_xy
    kc_nom = dm.k_concrete_westergaard()["k_slab_N_m"]
    kr, kf = dm.k_rod(), A_["frame_bracket_stiffness_N_m"]
    bw = dm.body_with_rods(p, geo, "top", e_op)
    z_pad = geo.pad_z_retracted - e_op
    z_ball = z_pad + _ball_heights(p)
    zero = np.zeros(4)
    for beta in (A_["oil_bulk_modulus_range_Pa"][0], A_["oil_bulk_modulus_eff_Pa"], A_["oil_bulk_modulus_range_Pa"][1]):
        ent = res["L1_beta_sensitivity_top"][f"beta_{beta:.1e}"]
        kL = dm.series(dm.series(dm.k_oil(e_op, beta=beta), kr, kf), kc_nom)
        Fc, _, _ = dm.static_loads(kL, xy, bw.mass * g, bw.com[:2])
        f = {}
        for name, z in (("pad", z_pad), ("ball", z_ball)):
            K = _l1_matrices(bw, xy, z, z, kL, kt_L1, zero, zero, Fc)[0]
            f[name] = dm.modal(dm.mass_6dof(bw), K, dm.DOF6)[1]
        if r(f["pad"], 4) != ent["f_Hz_top"]:
            raise RuntimeError(f"beta {beta:.1e}: f_Hz_top not reproduced")
        ent[BETA_BALL_KEY] = r(f["ball"], 4)


def l1_damping_stiffness(p, geo, e_op, k_L1):
    """Stiffness on which the L1 pad dashpot c = 2 zeta sqrt(k m/4) is set (rev. 30, dynamics_model.md 5.12.8 Q-D3).

    YAML contact.rigid_floor.L1.derivation.damping_basis 'LOCK' (L1-R): k_lock = series(k_oil + k_rod_side, k_rod,
    k_frame, k_concrete), k_rod_side = beta A_ann / (stroke - e_op + L0) computed here and checked against the YAML
    derivation.k_rod_side_N_m (rel 1e-6). Any other value or no key (YAML before L1-R): k_L1 itself (bit-identical).
    """
    d = p["contact"]["rigid_floor"]["L1"]["derivation"]
    if d.get("damping_basis", "HEAD") != "LOCK":
        return k_L1
    A_ = dm.ASSUMPTIONS
    beta = float(p["actuator"].get("oil_bulk_modulus_eff_Pa", A_["oil_bulk_modulus_eff_Pa"]))
    L0 = float(p["actuator"].get("oil_dead_length_m", A_["oil_dead_length_m"]))
    k_rs = beta * np.broadcast_to(dm.annulus_area(), (4,)) / (geo.stroke - np.asarray(e_op, float) + L0)
    k_rs_yaml = np.array([float(d["k_rod_side_N_m"][n]) for n in dm.LEG_NAMES])
    if np.max(np.abs(k_rs / k_rs_yaml - 1.0)) > 1e-6:
        raise RuntimeError(f"rod-side stiffness {k_rs} differs from the YAML derivation {k_rs_yaml}")
    kc = dm.k_concrete_westergaard()["k_slab_N_m"]
    return dm.series(dm.series(dm.k_oil(e_op) + k_rs, dm.k_rod(), A_["frame_bracket_stiffness_N_m"]), kc)


def l1r_cli(argv=None):
    """Options of the L1-R reference block (dynamics_model.md rev. 32, 5.14); no option = main() unchanged.

    --l1r-out PATH  write only the L1-R block (l1r_reference.build_block) to PATH, series to PATH .npz;
                    reference.json is read for the cross-checks and not written
    --with-l1r      run main() (writes reference.json as before), then add the block under l1r_reference.L1R_KEY
    """
    import argparse

    ap = argparse.ArgumentParser(description=l1r_cli.__doc__.split("\n")[0])
    ap.add_argument("--l1r-out", type=Path, default=None)
    ap.add_argument("--with-l1r", action="store_true")
    a = ap.parse_args(argv)
    if a.l1r_out is None and not a.with_l1r:
        main()
        return
    import l1r_reference as l1r

    if a.with_l1r:
        main()
    with open(OUT, encoding="utf-8") as f:
        res = json.load(f)
    out_path = a.l1r_out if a.l1r_out is not None else OUT.with_name(OUT.stem + "_L1R_series.json")
    block = l1r.build_block(ref_res=res, npz_out=out_path.with_suffix(".npz"))
    if a.with_l1r:
        res[l1r.L1R_KEY] = block
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
        print("added", l1r.L1R_KEY, "to", OUT)
    if a.l1r_out is not None:
        a.l1r_out.parent.mkdir(parents=True, exist_ok=True)
        with open(a.l1r_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump({l1r.L1R_KEY: block}, f, indent=1, ensure_ascii=False)
        print("written", a.l1r_out)


def cli(argv=None):
    """Options of the reference blocks; no option = main() unchanged (dynamics_model.md rev. 33, 5.20).

    --l1r-out PATH / --with-l1r   L1-R block (rev. 32), as l1r_cli
    --l2b-out PATH                write only the L2b-NSC block (l2b_reference.build_block) to PATH; reference.json is
                                  read (cross-checks) and not written
    --with-l2b                    run main() and the L1-R block (implies --with-l1r, so reference.json keeps it), then
                                  add the L2b-NSC block under l2b_reference.L2B_KEY
    """
    import argparse

    ap = argparse.ArgumentParser(description=cli.__doc__.split("\n")[0])
    ap.add_argument("--l1r-out", type=Path, default=None)
    ap.add_argument("--with-l1r", action="store_true")
    ap.add_argument("--l2b-out", type=Path, default=None)
    ap.add_argument("--with-l2b", action="store_true")
    a = ap.parse_args(argv)
    l1r_args = (["--with-l1r"] if (a.with_l1r or a.with_l2b) else []) + \
        (["--l1r-out", str(a.l1r_out)] if a.l1r_out is not None else [])
    if a.l2b_out is None and not a.with_l2b:
        l1r_cli(l1r_args)
        return
    import l2b_reference as l2b

    if a.with_l2b or l1r_args:
        l1r_cli(l1r_args)
    with open(OUT, encoding="utf-8") as f:
        res = json.load(f)
    block = l2b.build_block(ref_res=res)
    if a.with_l2b:
        res[l2b.L2B_KEY] = block
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
        print("added", l2b.L2B_KEY, "to", OUT)
    if a.l2b_out is not None:
        a.l2b_out.parent.mkdir(parents=True, exist_ok=True)
        with open(a.l2b_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump({l2b.L2B_KEY: block}, f, indent=1, ensure_ascii=False)
        print("written", a.l2b_out)


if __name__ == "__main__":
    cli()
