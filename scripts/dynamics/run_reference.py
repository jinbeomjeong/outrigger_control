"""Compute the analytic reference values for the Chrono outrigger model (docs/dynamics_model.md).

Run (dynamics-dev, activated):
    conda run -n dynamics-dev python -I scripts/dynamics/run_reference.py

Writes analysis/dynamics/reference.json and prints a summary. Deterministic (no random numbers).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

OUT = dm.PROJECT_ROOT / "analysis" / "dynamics" / "reference.json"
DEG = 180.0 / math.pi
KC_RIGID = 1e13  # N/m, stands in for the rigid NSC contact (L2b-NSC); rod-on-floor mode ~ 50 kHz, removed from the tables


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


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    g = geo.g
    A_ = dm.ASSUMPTIONS
    res = {"meta": {
        "script": "scripts/dynamics/run_reference.py",
        "params": "params/rexome33.yaml",
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
                         "assembly in cad/parts_classified.csv); the crawler hangs from the body, so clearance is checked at its corners")
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
    # three candidate Chrono configurations (docs/dynamics_model.md 3.3)
    zt = A_["modal_damping_ratio_body"]
    m_rod = float(geo.rod_mass.mean())
    k_L1 = kv_H  # lumped: rigid motor, contact stiffness = series(oil, rod, frame, concrete)
    kt_L1 = dm.series(kh_free, kc_nom)  # lumped lateral: swivel leg bending in series with concrete kt
    c_o = 2 * zt * np.sqrt(ko_eff * W_tot / g / 4)        # oil-column damper (heave ~ zeta)
    # contact damper: total damping on the rod local mode (oil + contact dashpots act in parallel on the rod)
    # set to zeta_rod = 0.3 -> c_c = 2*0.3*sqrt((ko+kc) m_rod) - c_o  (numerical hygiene for the 286 Hz mode)
    zeta_rod = 0.3
    c_c = 2 * zeta_rod * np.sqrt((ko_eff + kc_nom) * m_rod) - c_o
    configs = {
        "R1_rigid_motor_concrete (informational, excluded from load evaluation)": dict(kv=np.full(4, kc_nom), kh=np.full(4, kc_nom),
                                        c_pad=np.full(4, 2 * zt * math.sqrt(kc_nom * W_tot / g / 4))),
        # L1 (TEMPORARY DEFAULT, user decision 2026-10-19): rigid motor; contact kn = series(oil, rod, frame, concrete),
        # contact kt = series(swivel-leg lateral bending, concrete kt); one contact sphere per pad at the ball
        "L1_rigid_motor_lumped_contact": dict(kv=k_L1, kh=kt_L1, c_pad=2 * zt * np.sqrt(k_L1 * W_tot / g / 4),
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
                _, f_und, _, mcls, _ = dm.modal(M, K, labels)
                fd, zd = dm.complex_modes(M, K, C)
            else:
                pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
                K = dm.stiffness_6dof(bw, pad_pts, kv, cfg["kh"], Fc)
                M = dm.mass_6dof(bw)
                Cm = np.zeros((6, 6))
                for i in range(4):
                    ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
                    ct = cfg.get("c_tan", cfg["c_pad"])
                    Cm += cfg["c_pad"][i] * np.outer(az, az) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay))
                _, f_und, _, mcls, _ = dm.modal(M, K, dm.DOF6)
                fd, zd = dm.complex_modes(M, K, Cm)
            lvl_out[lvl] = {
                "contact_force_N": r(Fc), "static_penetration_or_compression_mm": r(Fb / kv * 1e3 + geo.rod_mass * g / kv * 1e3 * (not name.startswith("L2"))),
                "static_attitude_deg (roll, pitch)": r(np.degrees(qb[1:]), 4),
                "dF_per_mm_FL_N": r(S[:, 0] * 1e-3), "droll_dpitch_per_mm_FL_deg": r(np.degrees(Q[1:, 0]) * 1e-3),
                "cylinder_force_N": r(Fb),
                "F_min_cylinder_N": r(F_min),
                "liftoff_threshold_single_leg (contact force 0)": thr,
                "F_min_threshold_single_leg (cylinder force = F_min)": thr_min,
                "f_undamped_Hz": r(f_und, 5), "mode_content": mcls, "f_damped_Hz": r(fd, 5), "zeta": r(zd, 3)}
        tests[name] = {"k_vertical_N_m": r(kv), "k_horizontal_N_m": r(cfg["kh"]),
                       **({"c_pad_N_s_m": r(cfg["c_pad"]), "c_tan_N_s_m": r(cfg.get("c_tan", cfg["c_pad"]))} if "c_pad" in cfg else {"c_oil_N_s_m": r(c_o), "c_contact_N_s_m": r(cfg["c_c"]),
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

    # ------------------------------------------------------------ hydraulic circuit (docs/hydraulic_circuit.md, rev. 4)
    # double-acting cylinder, dual pilot-operated check valve on the cylinder: both chambers locked.
    # Rod-side (annulus) oil column acts in parallel with the head-side column while its pressure stays above ~0
    # (one-sided: it stiffens when the leg unloads / piston moves down, cavitates toward 0 when the leg loads).
    A_head = dm.piston_area()
    A_ann = math.pi / 4 * (A_["bore_diameter_m"] ** 2 - A_["rod_diameter_m"] ** 2)
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
        "max_static_head_pressure_Pa": r(float(tests["L1_rigid_motor_lumped_contact"]["levels"]["top"]["cylinder_force_N"][0]) / A_head),
        "flow_4_legs_at_vmax_L_min": r(4 * geo.v_max * A_head * 6e4, 4), "pump_flow_L_min": 60.2,
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
            # rev. 4: NSC rigid contact (stick), axial force law incl. concrete, constant bushing = L1 kt (YAML value)
            "L2b_NSC": (dm.series(ko_s, kc_nom), np.full(4, KC_RIGID), kt_L1),
        }.items():
            sr = dm.static_slope_10dof(b, geo, ext, ko_c, kn_c, kt_c, slope_pitch_deg=pi, slope_roll_deg=ro)
            kv_s = dm.series(ko_c, kn_c)
            F_ideal, _, _ = dm.static_loads(kv_s, xy, b.mass * g, b.com[:2])
            entry[name] = {"contact_vertical_N": r(sr["R"][:, 2]), "contact_horizontal_xy_N": r(sr["R"][:, :2]),
                           "cylinder_force_N": r(sr["F_cyl"]), "friction_utilisation_T_over_N": r(sr["mu_used"], 4),
                           "cylinder_force_if_no_horizontal_reaction_N": r(F_ideal),
                           "attitude_change_deg (roll, pitch)": r(np.degrees(sr["q"][3:5]), 4)}
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
    res["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False)[:200000])
    print("written", OUT)


if __name__ == "__main__":
    main()
