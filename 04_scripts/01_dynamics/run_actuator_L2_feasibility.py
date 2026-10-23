"""L1 vs L2 actuator model feasibility numbers (00_docs/01_dynamics/actuator_L2_feasibility.md).

Read-only use of dyn_model.py and 02_params/rexome33.yaml. Writes 06_analysis/00_dynamics/actuator_L2_feasibility.json.

Sections
  A  extension dependence of the oil column: static loads / sensitivity / F_min threshold / modes,
     L1 (contact kn fixed at the operating extension) vs L2b (k_oil(e) per leg) over levelling cases
  B  cylinder-force (pressure) frequency response to a leg reference step, L1 (6-DoF) vs L2b (10-DoF)
  C  seal friction (Coulomb, stick/slip) in parallel with the oil column: quasi-static incremental
     model, true leg load vs pressure reading, F_min thresholds, hysteresis
  D  leakage (pilot check valve / internal) -> sink rate, load and attitude drift
  E  barrel expansion and rod-side (annulus) chamber -> effect on the effective column stiffness
  F  Chrono SMC tangential model falls back to OneStep (ChSystemSMC.h:94): modes without a tangential
     spring, creep estimate; rod local mode with a rigid (NSC) contact for L2b

Conventions as dyn_model.py: body x fwd, y left, z up; g = -9.80665 z; leg order FL FR RL RR;
cylinder force F_cyl = pressure x bore area (compression +), F_min on this basis.
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

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "actuator_L2_feasibility.json"


def r(x, n=5):
    if isinstance(x, dict):
        return {k: r(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    g = geo.g
    A_ = dm.ASSUMPTIONS
    xy = geo.pad_xy
    zt = A_["modal_damping_ratio_body"]
    e_op = geo.touch_extension + A_["crawler_clearance_m"]
    kc = dm.k_concrete_westergaard()["k_slab_N_m"]
    kr = dm.k_rod()
    kf = A_["frame_bracket_stiffness_N_m"]
    b_top = dm.body_from_params(p, "top")
    W_b = b_top.mass * g
    F_min = A_["F_min_fraction_of_mean_leg_load"] * W_b / 4

    def ko_eff(ext, beta=None):
        return dm.series(dm.k_oil(ext, beta=beta), kr, kf)

    def kv_of(ext, beta=None):
        return dm.series(ko_eff(ext, beta), kc)

    kv_L1 = kv_of(e_op)                                       # L1 contact kn (fixed)
    kt_L1 = dm.series(dm.k_leg_lateral_legs(geo, e_op, False), kc)

    def levelled_extension(slope_roll_deg, slope_pitch_deg, clearance=A_["crawler_clearance_m"]):
        # copy of run_reference.levelled_extension (nested function there)
        sx = -math.tan(math.radians(slope_pitch_deg)); sy = math.tan(math.radians(slope_roll_deg))
        (x0, x1), (y0, y1) = geo.crawler_xy_box
        corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
        H = np.max(sx * corners[:, 0] + sy * corners[:, 1]) + clearance - geo.crawler_bottom_z
        return geo.pad_z_retracted + H - (sx * xy[:, 0] + sy * xy[:, 1])

    def max_slope(direction_deg):
        lo, hi = 0.0, 20.0
        for _ in range(60):
            mid = (lo + hi) / 2
            e = levelled_extension(mid * math.sin(math.radians(direction_deg)), mid * math.cos(math.radians(direction_deg)))
            lo, hi = (mid, hi) if (e.min() >= 0 and e.max() <= geo.stroke) else (lo, mid)
        return lo

    res = {"meta": {"script": "04_scripts/01_dynamics/run_actuator_L2_feasibility.py", "params": "02_params/rexome33.yaml",
                    "frame": "body x fwd, y left, z up; g = -9.80665 z", "leg_order": list(dm.LEG_NAMES),
                    "force_basis": "cylinder force = pressure x bore area (compression +); contact = cylinder + rod weight",
                    "level": "top unless stated", "F_min_cylinder_N": F_min}}

    # ------------------------------------------------------------------ A: extension dependence
    cases = {"level": (0, 0), "roll 2": (2, 0), "pitch 2": (0, 2), "roll -2 pitch 1.5": (-2, 1.5)}
    for name, d in (("max pitch+", 0), ("max pitch-", 180), ("max roll+", 90), ("max diag 45", 45)):
        s = max_slope(d) * 0.999
        cases[name] = (s * math.sin(math.radians(d)), s * math.cos(math.radians(d)))

    def modes_L1(ext, kv):
        bw = dm.body_with_rods(p, geo, "top", ext)
        pad_pts = np.column_stack([xy, geo.pad_z_retracted - ext])
        Fb, _, _ = dm.static_loads(kv, xy, bw.mass * g, bw.com[:2])
        K = dm.stiffness_6dof(bw, pad_pts, kv, kt_L1, Fb)
        return dm.modal(dm.mass_6dof(bw), K, dm.DOF6)[1]

    def modes_L2b(ext, beta=None):
        kh = dm.series(dm.k_leg_lateral_legs(geo, ext, False), kc)
        M, K, C, lab, _ = dm.model_10dof(b_top, geo, ext, ko_eff(ext, beta), np.full(4, kc), kh)
        return dm.modal(M, K, lab)[1]

    def thresholds(k):
        Fb, _, _ = dm.static_loads(k, xy, W_b, b_top.com[:2])
        S = dm.load_sensitivity(k, xy)
        col = S[:, 0]
        with np.errstate(divide="ignore"):
            fm = np.where(col < 0, -(Fb - F_min) / col, np.inf)
        return Fb, S, float(fm.min())

    secA = {}
    for name, (ro, pi) in cases.items():
        ext = levelled_extension(ro, pi)
        kv2 = kv_of(ext)
        F1, S1, th1 = thresholds(kv_L1)
        F2, S2, th2 = thresholds(kv2)
        f1 = modes_L1(ext, kv_L1)
        f1u = modes_L1(ext, kv2)
        f2 = modes_L2b(ext)
        secA[name] = {
            "ground_roll_pitch_deg": [ro, pi], "extension_m": ext,
            "k_oil_eff_rel_to_L1": ko_eff(ext) / ko_eff(e_op),
            "kv_L2_N_m": kv2,
            "F_cyl_place_and_settle_L1_N": F1, "F_cyl_place_and_settle_L2_N": F2,
            "F_diff_L2_minus_L1_N": F2 - F1,
            "S_diag_L1_kN_per_mm": np.diag(S1) * 1e-6, "S_diag_L2_kN_per_mm": np.diag(S2) * 1e-6,
            "S_max_rel_diff": float(np.abs(S2 - S1).max() / np.abs(S1).max()),
            "FLplus_F_min_threshold_mm_L1": th1 * 1e3, "FLplus_F_min_threshold_mm_L2": th2 * 1e3,
            "f_Hz_L1_fixed_kn": f1, "f_Hz_L1_kn_updated_to_extension": f1u, "f_Hz_L2b_rigid_body_modes": f2[:6],
            "rocking1_2_rel_diff_L2b_vs_L1": (f2[:2] - f1[:2]) / f1[:2],
            "rocking1_2_rel_diff_L2b_vs_L1u": (f2[:2] - f1u[:2]) / f1u[:2],
        }
    # beta range for comparison (L1 at e_op)
    secA["_beta_range_for_comparison"] = {
        f"beta_{b:.2e}": {"S_FL_kN_per_mm": thresholds(kv_of(e_op, b))[1][0, 0] * 1e-6,
                          "FLplus_F_min_mm": thresholds(kv_of(e_op, b))[2] * 1e3} for b in (0.69e9, 1.0e9, 1.6e9)}
    # rev. 5 (V14 redefinition): at max pitch+ FL/FR sit at the stroke end, so an FL+ single-leg test is impossible.
    # Single-leg sensitivity / F_min / lift-off for every leg and direction on the slope itself, L2b-NSC statics
    # (static_slope_10dof: axial k_oil(e) + rod + frame + concrete, rigid NSC contact 1e13, lateral bushing kt_L1),
    # with the stroke room of the tested leg. V14 uses RL+ in all three cases (room everywhere).
    v14 = {"method": ("L2b-NSC linear statics on the sloped floor (place and settle at the levelled extension), "
                      "then +/-1 mm of reference extension on one leg (oil-spring prestrain); thresholds by linear "
                      "extrapolation (exact for the linear model up to the first event). Cylinder-force basis for "
                      "F_min, pad normal contact force 0 for lift-off."),
           "V14_test_leg": "RL+", "cases": {}}
    hb_n = len(dm.LEG_NAMES)
    for name in ("level", "max pitch+", "max roll+", "max diag 45", "max pitch-"):
        ro, pi = cases[name]
        ext = levelled_extension(ro, pi)
        ko_s = dm.series(ko_eff(ext), kc)
        base = dm.static_slope_10dof(b_top, geo, ext, ko_s, np.full(4, 1e13), kt_L1, slope_pitch_deg=pi, slope_roll_deg=ro)
        tests_ = {}
        for i, nm in enumerate(dm.LEG_NAMES):
            for sgn, lab in ((1, "+"), (-1, "-")):
                dl = np.zeros(hb_n); dl[i] = sgn * 1e-3
                pert = dm.static_slope_10dof(b_top, geo, ext, ko_s, np.full(4, 1e13), kt_L1, slope_pitch_deg=pi,
                                             slope_roll_deg=ro, delta=dl)
                dF = pert["F_cyl"] - base["F_cyl"]; dN = pert["N"] - base["N"]
                with np.errstate(divide="ignore", invalid="ignore"):
                    t_min = np.where(dF < 0, (base["F_cyl"] - F_min) / -dF, np.inf)
                    t_lift = np.where(dN < 0, base["N"] / -dN, np.inf)
                jm, jl = int(np.argmin(t_min)), int(np.argmin(t_lift))
                room = (geo.stroke - ext[i]) if sgn > 0 else ext[i]
                tests_[nm + lab] = {
                    "S_own_kN_per_mm": float(dF[i] * 1e-3 * sgn), "dF_cyl_per_mm_N": dF * sgn,
                    "F_min_threshold_mm": float(t_min[jm]), "leg_at_F_min": dm.LEG_NAMES[jm],
                    "liftoff_threshold_mm": float(t_lift[jl]), "liftoff_leg": dm.LEG_NAMES[jl],
                    "stroke_room_mm": float(room * 1e3),
                    "feasible (room >= liftoff + 1 mm)": bool(room * 1e3 >= t_lift[jl] + 1.0)}
        v14["cases"][name] = {"ground_roll_pitch_deg": [ro, pi], "extension_m": ext,
                              "F_cyl_place_and_settle_N": base["F_cyl"], "N_contact_normal_N": base["N"],
                              "single_leg": tests_,
                              "f_Hz_L2b_rigid_body_modes": secA[name]["f_Hz_L2b_rigid_body_modes"]}
    secA["V14_rev5"] = v14
    res["A_extension_dependence"] = secA

    # ------------------------------------------------------------------ B: pressure FRF
    bw = dm.body_with_rods(p, geo, "top", e_op)
    W_tot = bw.mass * g
    pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
    Fc0, _, _ = dm.static_loads(kv_L1, xy, W_tot, bw.com[:2])
    K6 = dm.stiffness_6dof(bw, pad_pts, kv_L1, kt_L1, Fc0)
    M6 = dm.mass_6dof(bw)
    cn = 2 * zt * np.sqrt(kv_L1 * W_tot / g / 4); ct = 2 * zt * np.sqrt(kt_L1 * W_tot / g / 4)
    C6 = np.zeros((6, 6)); AZ = []
    for i in range(4):
        ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
        C6 += cn[i] * np.outer(az, az) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay)); AZ.append(az)
    AZ = np.array(AZ)
    # L2b 10-DoF with the reference damping
    ko0 = ko_eff(e_op)
    kh2 = dm.series(dm.k_leg_lateral_legs(geo, e_op, False), kc)
    c_o = 2 * zt * np.sqrt(ko0 * W_tot / g / 4)
    m_rod = float(geo.rod_mass.mean())
    c_c = 2 * 0.3 * np.sqrt((ko0 + kc) * m_rod) - c_o
    c_h = 2 * zt * np.sqrt(kh2 * W_tot / g / 4)
    M10, K10, C10, _, _ = dm.model_10dof(b_top, geo, e_op, ko0, np.full(4, kc), kh2, c_o, c_c, c_h)
    B10 = []
    for i in range(4):
        d_att = np.array([*xy[i], geo.attach_z[i]]) - b_top.com
        bb = np.zeros(10); bb[:6] = dm.a_vec(d_att)[2]; bb[6 + i] = -1.0
        B10.append(bb)
    B10 = np.array(B10)

    def H_L1(s, j=0):
        """F_cyl (4,) per unit reference extension of leg j, L1 (rigid motor = contact spring base)."""
        z = kv_L1[j] + cn[j] * s
        q = np.linalg.solve(M6 * s**2 + C6 * s + K6, AZ[j] * z)
        dlt = np.zeros(4); dlt[j] = 1.0
        Fc = (kv_L1 + cn * s) * (dlt - AZ @ q)
        return Fc - geo.rod_mass * s**2 * (AZ @ q)   # motor reaction = contact - rod inertia (rod rigid with body)

    def H_L2(s, j=0):
        z = ko0[j] + c_o[j] * s
        q = np.linalg.solve(M10 * s**2 + C10 * s + K10, B10[j] * z)
        dlt = np.zeros(4); dlt[j] = 1.0
        return (ko0 + c_o * s) * (dlt - B10 @ q)

    freqs = [0.0, 0.05, 0.2, 0.5, 1.0, 1.78, 2.0, 3.0, 5.0, 10.0]
    frf = {}
    for f in freqs:
        s = 2j * math.pi * f
        h1 = H_L1(s); h2 = H_L2(s)
        frf[f"{f} Hz"] = {"L1_kN_per_mm_abs": np.abs(h1) * 1e-6, "L2b_kN_per_mm_abs": np.abs(h2) * 1e-6,
                          "rel_diff_abs": (np.abs(h2) - np.abs(h1)) / np.abs(h1),
                          "phase_diff_deg": np.degrees(np.angle(h2 / h1))}
    res["B_pressure_frf_FL_reference_input"] = {
        "input": "FL reference extension (L1: motor position, L2b: s_ref = oil volume / bore area), sinusoid",
        "output": "cylinder force of FL, FR, RL, RR [kN/mm]", "frf": frf}

    # ------------------------------------------------------------------ C: seal friction (quasi-static)
    ko_op = dm.k_oil(e_op)
    k_s = np.broadcast_to(np.asarray(dm.series(kr, kf, kc), float), (4,)).copy()  # per leg (rev. 30); leg stiffness with the oil column locked by stick friction
    kv = dm.series(ko_op, kr, kf, kc)     # slipping: oil column in series
    A = dm.support_matrix(xy)

    def friction_run(Fs, d_max=0.016, dd=2e-6, back=True, stop_at_liftoff=False):
        F0, _, _ = dm.static_loads(kv, xy, W_b, b_top.com[:2])
        F = F0.copy(); f = np.zeros(4)               # f: friction force on the rod, outward +
        stick = np.ones(4, bool); sgn = np.zeros(4)  # sgn: sign of f while slipping
        path = list(np.arange(dd, d_max + dd / 2, dd))
        if back:
            path += list(np.arange(d_max - dd, -dd / 2, -dd))
        prev = 0.0
        hist = []
        for d in path:
            dsig = np.zeros(4); dsig[0] = d - prev; prev = d
            st = stick.copy(); sg = sgn.copy()
            for _ in range(20):
                k = np.where(st, k_s, kv)
                dl = np.where(st, 0.0, dsig)
                Kd = np.diag(k)
                dq = np.linalg.solve(A.T @ Kd @ A, A.T @ Kd @ dl)
                dF = k * (dl - A @ dq)
                dFoil = np.where(st, ko_op * dsig, dF)
                fn = np.where(st, f + dF - dFoil, sg * Fs)
                dx = np.where(st, 0.0, dsig - dFoil / ko_op)
                ch = False
                for i in range(4):
                    if st[i] and abs(fn[i]) > Fs:
                        st[i] = False; sg[i] = np.sign(fn[i]); ch = True
                    elif (not st[i]) and dx[i] * sg[i] > 0:   # moving in the direction friction pushes -> stick
                        st[i] = True; ch = True
                if not ch:
                    break
            F = F + dF; f = fn; stick = st; sgn = sg
            hist.append((d, F.copy(), (F - f).copy()))
            if stop_at_liftoff and (F + geo.rod_mass * g).min() <= 0.0:
                break   # first pad contact force reaches 0 (unilateral contact): the linear 4-leg model ends here
        D = np.array([h[0] for h in hist]); Ft = np.array([h[1] for h in hist]); P = np.array([h[2] for h in hist])
        if stop_at_liftoff:
            Fc = Ft + geo.rod_mass * g                  # pad contact force
            j = int(np.argmin(Fc[-1])); lifted = bool(Fc[-1, j] <= 0.0)
            if lifted:   # linear interpolation between the last two increments
                d_lift = float(np.interp(0.0, [Fc[-1, j], Fc[-2, j]], [D[-1], D[-2]]))
            P_lift = P[-1, j]

            def first_u(arr, thr):
                idx = np.where(arr.min(axis=1) <= thr)[0]
                return float(D[idx[0]] * 1e3) if len(idx) else None

            return {"F_s_N": Fs,
                    "FLplus_true_min_load_at_F_min_mm": first_u(Ft, F_min),
                    "FLplus_pressure_min_at_F_min_mm (null = pad lifts off first)": first_u(P, F_min),
                    "FLplus_liftoff_mm (pad contact force 0)": d_lift * 1e3 if lifted else None,
                    "liftoff_leg": dm.LEG_NAMES[j] if lifted else None,
                    "pressure_reading_of_lifting_leg_at_liftoff_N (cylinder-force basis)": float(P_lift),
                    "pressure_minus_F_min_at_liftoff_N": float(P_lift - F_min)}

        n_up = int(round(d_max / dd))
        up = slice(0, n_up)

        def first(arr, thr):
            idx = np.where(arr[up].min(axis=1) <= thr)[0]
            return float(D[idx[0]] * 1e3) if len(idx) else None

        out = {"F_s_N": Fs,
               "FLplus_true_min_load_at_F_min_mm": first(Ft, F_min),
               "FLplus_pressure_min_at_F_min_mm": first(P, F_min),
               "max_abs_pressure_minus_true_N": float(np.abs(P - Ft).max()),
               "RL_load_change_at_1mm_true_N": float(np.interp(1e-3, D[up], Ft[up, 2]) - F0[2]),
               "RL_load_change_at_1mm_pressure_N": float(np.interp(1e-3, D[up], P[up, 2]) - F0[2]),
               "FL_pressure_minus_true_while_extending_N": float((P - Ft)[n_up // 2, 0])}
        if back:
            out["residual_true_load_change_after_return_N"] = Ft[-1] - F0
            out["residual_pressure_change_after_return_N"] = P[-1] - F0
        return out

    rated = {"rated_pressure_20.6MPa_x_bore_area_N": 20.6e6 * dm.piston_area(), "max_static_leg_load_N": 118254.6}
    secC = {"model": ("massless rod; oil spring k_oil(e_op) in parallel with a Coulomb friction element |f|<=F_s "
                      "(static = kinetic), in series with rod+frame+concrete k_s; stick legs: oil locked. Initial "
                      "friction state f = 0 (ASSUMPTION; the real state after levelling is history dependent). "
                      "FL reference extended 0 -> 16 mm -> 0 quasi-statically, other legs locked (s_ref const)."),
            "k_s_N_m (stick)": k_s, "kv_N_m (slip)": kv, "rated_basis": rated, "runs": {}}
    for Fs in (0.0, 1e3, 2e3, 5e3, 1.2e4, 2.14e4):
        secC["runs"][f"F_s {Fs/1e3:g} kN"] = friction_run(Fs)
    # rev. 5 (V15 redefinition): the runs above are bilateral and cross the lift-off threshold (14.08 mm at F_s 0) on
    # the way to 16 mm, so they cannot be compared with a unilateral Chrono contact. V15 now uses
    #   (a) up-sweep 0 -> lift-off, unilateral: stops at the first pad contact force 0
    #   (b) round trip 0 -> 10 mm -> 0: below every F_min / lift-off threshold, so the linear model is exact there
    v15 = {"note": ("rev. 5 V15 reference. (a) unilateral up-sweep, FL s_ref from 0 until the first pad contact force "
                    "reaches 0 (contact force = cylinder-basis load + rod weight); (b) round trip 0 -> 10 mm -> 0, no "
                    "pad reaches F_min or lift-off, so the bilateral model is valid. Same friction model and initial "
                    "f = 0 (ASSUMPTION) as 'runs'."),
           "a_upsweep_unilateral": {}, "b_roundtrip_10mm": {}}
    for Fs in (0.0, 2e3, 5e3, 1.2e4):
        lab = f"F_s {Fs/1e3:g} kN"
        v15["a_upsweep_unilateral"][lab] = friction_run(Fs, d_max=0.02, back=False, stop_at_liftoff=True)
        rt = friction_run(Fs, d_max=0.010)
        v15["b_roundtrip_10mm"][lab] = {k: rt[k] for k in ("F_s_N", "residual_true_load_change_after_return_N",
                                                          "residual_pressure_change_after_return_N",
                                                          "RL_load_change_at_1mm_true_N", "RL_load_change_at_1mm_pressure_N")}
        rt_min = friction_run(Fs, d_max=0.010, back=False)
        v15["b_roundtrip_10mm"][lab]["F_min_reached_on_the_way (true, pressure)"] = [
            rt_min["FLplus_true_min_load_at_F_min_mm"], rt_min["FLplus_pressure_min_at_F_min_mm"]]
    secC["V15_rev5"] = v15
    # small-amplitude rocking if all legs stick (oil column bypassed)
    bw = dm.body_with_rods(p, geo, "top", e_op)
    Fc0, _, _ = dm.static_loads(k_s, xy, bw.mass * g, bw.com[:2])
    f_stick = dm.modal(dm.mass_6dof(bw), dm.stiffness_6dof(bw, pad_pts, k_s, kt_L1, Fc0), dm.DOF6)[1]
    secC["f_Hz_all_legs_stuck_small_amplitude"] = f_stick
    secC["f_Hz_L1_reference"] = modes_L1(e_op, kv_L1)
    res["C_seal_friction"] = secC

    # ------------------------------------------------------------------ D: leakage
    drop_mL = 0.05  # ASSUMPTION: 1 drop = 0.05 mL
    Ap = dm.piston_area(0)  # FL (the leaking leg) head area (rev. 30, per leg); = the common area for the old YAML
    S = dm.load_sensitivity(kv_L1, xy); Q = dm.attitude_sensitivity(kv_L1, xy)
    leak = {}
    for name, Qml_min in (("check valve 1 drop/min", 1 * drop_mL), ("check valve 5 drops/min", 5 * drop_mL),
                          ("internal 0.5 mL/min (1.5x pressure test limit)", 0.5)):
        v = Qml_min * 1e-6 / 60 / Ap  # m/s sink of one leg
        ent = {"Q_mL_per_min": Qml_min, "sink_mm_per_min": v * 6e4, "sink_mm_per_h": v * 3.6e6}
        for T, lab in ((60, "60 s"), (600, "10 min"), (3600, "1 h")):
            dl = np.zeros(4); dl[0] = -v * T  # FL leaks
            ent[f"FL leaks {lab}: dF_cyl_N"] = S @ dl
            ent[f"FL leaks {lab}: droll_dpitch_deg"] = np.degrees((Q @ dl)[1:])
        leak[name] = ent
    res["D_leakage"] = {"drop_volume_mL (ASSUMPTION)": drop_mL, "cases": leak,
                        "note": "linear, L1 stiffness, one leg leaking, others locked, no control"}

    # ------------------------------------------------------------------ E: barrel expansion, annulus chamber
    E = A_["steel_E_Pa"]; nu = 0.3
    _cd = [dm.cylinder_dims(i) for i in range(4)]  # per leg (rev. 30): scalars while all legs share the cylinder
    Do, Di, Dr = _cd[0] if all(c == _cd[0] for c in _cd) else tuple(np.array(v) for v in zip(*_cd))
    c_tube = 2 / E * ((Do**2 + Di**2) / (Do**2 - Di**2) + nu)   # dV/V/dp of a thick-walled closed tube (Lame, radial only)
    K_tube = 1 / c_tube
    secE = {"K_tube_equivalent_Pa": K_tube,
            "beta_eff_with_tube": {f"oil {bo/1e9:g} GPa": 1 / (1 / bo + c_tube) for bo in (1.3e9, 1.58e9, 1.75e9)},
            "tube_share_of_column_compliance_at_oil_1.3GPa": c_tube / (1 / 1.3e9 + c_tube)}
    A_ann = math.pi / 4 * (Di**2 - Dr**2)
    L_ann = geo.stroke - e_op + A_["oil_dead_length_m"]   # ASSUMPTION: rod-side column length incl. same dead length
    k_ann = A_["oil_bulk_modulus_eff_Pa"] * A_ann / L_ann
    secE["annulus_area_m2"] = A_ann
    secE["annulus_area_over_bore_area"] = A_ann / dm.piston_area()   # per leg (rev. 30)
    secE["k_annulus_locked_N_m (upper bound, rod side locked and pressurised)"] = k_ann
    secE["k_annulus_over_k_cap"] = k_ann / ko_op
    res["E_column_details"] = secE

    # ------------------------------------------------------------------ F: OneStep tangential model
    bw = dm.body_with_rods(p, geo, "top", e_op)
    Fc0, _, _ = dm.static_loads(kv_L1, xy, bw.mass * g, bw.com[:2])
    f_no_kt = dm.modal(dm.mass_6dof(bw), dm.stiffness_6dof(bw, pad_pts, kv_L1, np.zeros(4), Fc0), dm.DOF6)
    secF = {"L1_f_Hz_with_kt": modes_L1(e_op, kv_L1), "L1_f_Hz_kt_zero": f_no_kt[1], "L1_kt_zero_mode_content": f_no_kt[3]}
    # OneStep-like: no tangential stiffness, tangential viscous c = kt dt + ct (ASSUMPTION on the OneStep formula)
    K0 = dm.stiffness_6dof(bw, pad_pts, kv_L1, np.zeros(4), Fc0)
    C0 = np.zeros((6, 6))
    for i in range(4):
        ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
        C0 += cn[i] * np.outer(az, az) + (kt_L1[i] * 2e-4 + ct[i]) * (np.outer(ax, ax) + np.outer(ay, ay))
    fd0, zd0 = dm.complex_modes(dm.mass_6dof(bw), K0, C0)
    fdr, zdr = dm.complex_modes(dm.mass_6dof(bw), dm.stiffness_6dof(bw, pad_pts, kv_L1, kt_L1, Fc0), C6)
    secF["L1_damped_with_kt (reference)"] = {"f_Hz": fdr, "zeta": zdr}
    secF["L1_damped_onestep_like (kt 0, c_t = kt dt + ct, dt 2e-4)"] = {"f_Hz": fd0, "zeta": zd0}
    # creep of the whole machine down a 2 deg slope if the tangential contact force is velocity based only:
    # sum_i (kt_i dt + ct_i) v = W_tot sin(alpha)  (ASSUMPTION: OneStep delta_t = v_t dt; Chrono source not
    # installed, headers only). The slip-velocity threshold (no tangential force below it) is ignored here.
    creep = {}
    W_slope = W_tot * math.sin(math.radians(2.0))
    for lab, kt, ctan, dt in (("L1 (kt_L1, ct_L1, dt 2e-4)", kt_L1, ct, 2e-4),
                              ("L2/L2b (contact kt = concrete, ct = 2 zeta sqrt(kc m/4), dt 5e-5)", np.full(4, kc),
                               np.full(4, 2 * zt * math.sqrt(kc * W_tot / g / 4)), 5e-5)):
        c_eq = float(np.sum(kt * dt + ctan))
        v = W_slope / c_eq
        creep[lab] = {"W_sin_alpha_N": W_slope, "sum_c_equiv_N_s_m": c_eq, "creep_m_s": v, "time_to_0.1mm_s": 1e-4 / v}
    secF["creep_if_velocity_based_tangential"] = creep
    # rod local mode: L2b with a rigid (NSC) contact = rod mass on the oil spring only
    f_rod_rigid = np.sqrt(ko_op / geo.rod_mass) / (2 * math.pi)
    f_rod_slab = np.sqrt((ko_eff(e_op) + kc) / geo.rod_mass) / (2 * math.pi)
    secF["rod_local_mode_Hz_slab_contact"] = f_rod_slab
    secF["rod_local_mode_Hz_rigid_NSC_contact"] = f_rod_rigid
    secF["rod_local_mode_Hz_rigid_contact_full_stroke"] = np.sqrt(dm.k_oil(0.0) / geo.rod_mass) / (2 * math.pi)
    # L2b on a rigid (NSC) floor: modes with kc -> very stiff in series (contact compliance moved into the oil spring)
    kv_nsc = dm.series(ko_eff(e_op), kc)  # keep the concrete compliance by lumping it into the axial spring
    M, K, _, lab, _ = dm.model_10dof(b_top, geo, e_op, kv_nsc, np.full(4, 1e12), dm.series(dm.k_leg_lateral_legs(geo, e_op, False), kc))
    fm = dm.modal(M, K, lab)[1]
    secF["L2b_NSC_equivalent_f_Hz (contact 1e12, concrete lumped into the axial spring)"] = fm[:6]
    secF["L2b_NSC_rod_mode_Hz (oil+rod+frame+concrete series, rigid floor)"] = np.sqrt(kv_nsc / geo.rod_mass) / (2 * math.pi)
    res["F_onestep_and_nsc"] = secF

    res["meta"]["runtime_s"] = time.perf_counter() - t0
    OUT.write_text(json.dumps(r(res), indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, f"{res['meta']['runtime_s']:.2f} s")


if __name__ == "__main__":
    main()
