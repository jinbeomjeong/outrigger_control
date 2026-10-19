"""IMU in the cabin + attitude accuracy target +/-0.1 deg vs +/-0.2 deg review (docs/imu_cabin_and_accuracy_review.md).

Parts
  1. Cabin geometry from cad/parts_classified.csv (operator cab = 'BUMA CE 3D 20230425' sub-assembly: CABIN-2 glass,
     slide windows, frame parts, Shrinkwrap_11). Body frame: x fwd, y left, z up, m; CAD map x = Z_cad, y = X_cad,
     z = Y_cad (CLAUDE.md). Proposed mount point on the cab floor + uncertainty box.
  2. Apparent tilt of an accelerometer-only tilt sensor in the L1 rocking modes (reference.json mode_shapes_rev5,
     reference point = composite CoM incl. rods). Small-angle specific-force model:
         f_b = R^T (a + g z_hat)  ->  phi_m = phi + a_y / g,  theta_m = theta - a_x / g
     with a = -omega^2 d, d = u + rot x rho (rho = IMU point - mode reference point). For pure rotation about a point
     a height r above the IMU this reduces to phi_m = phi (1 - r omega^2 / g).
  3. Filter requirement (rocking ripple at the completion filter) and loop phase margin for the attitude PI.
  4. Error budget for +/-0.1 / +/-0.2 deg and sensor classification (values from docs/attitude_sensor_survey.md).
  5. Closed-loop runs of C2 and C8 of run_control_comparison.py (imported, its result files are NOT written) with the
     IMU at the cab point, sensor grades (zeroed in the field), dead band 0.03 / 0.06 deg, auger top/middle/bottom.

Gravity g = -9.80665 z_hat m/s^2 (world). Roll phi about x, pitch theta about y (theta > 0 nose down), ZYX Euler.

Run: conda run -n dynamics-dev python -I scripts/dynamics/run_imu_accuracy_review.py [--no-sim]
Writes analysis/dynamics/imu_accuracy_review.json only.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_control_comparison as rcc  # noqa: E402  (imports dyn_model; no file is written on import)

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "analysis" / "dynamics" / "imu_accuracy_review.json"
G = 9.80665
DEG = math.pi / 180
LEVELS = ("top", "middle", "bottom")

# ---------------------------------------------------------------------------- ASSUMPTIONS (this review)
RA = {
    "cab_floor_above_lowest_cab_frame_m": 0.025,   # ASSUMPTION: floor plate / bracket above the lowest cab frame edge
    "imu_cab_point_m": [0.20, 0.88, 0.30],         # proposed: cab floor, footprint centre (rounded), see part 1
    "imu_cab_box_m": {"x": [-0.60, 0.90], "y": [0.50, 1.25], "z": [0.24, 0.45]},   # mount-position uncertainty
    "imu_old_point_m": [0.45, 0.0, 0.30],          # run_control_comparison.py assumption (deck, ~1.9 m below top CoM)
    # true rocking (1 s moving average removed) in the 5 s before completion, max over the closed-loop runs below
    "rocking_true_amp_deg": {"top": 0.031, "middle": 0.021, "bottom": 0.016},
    "ripple_limit_deg": 0.005,                     # allowed rocking ripple at the completion filter (half of 0.01 line)
    "loop": {"Kp_1_s": 0.4, "Ki_1_s2": 0.02, "T_ctrl_s": 0.02},
    # error-budget lines other than the sensor zero error [deg]
    "budget_noise_rocking_deg": 0.01,
    "budget_mount_deck_deg": 0.01,                 # field-zero reference + deck bracket (IMU on the deck frame)
    "budget_mount_cab_deg": 0.03,                  # ASSUMPTION: field-zero ref 0.01 + cab mount static change 0.02
    "temperature_span_K": 45.0,                    # 25 degC zero -> -20 degC (survey convention)
}

# Sensor grades for the closed-loop runs: per-axis bias (same sign on x and y) and noise density.
GRADES = {
    "ideal":        {"bias_deg": 0.0,   "noise_ug_rtHz": 15.0, "note": "no zero error (isolates rocking/filter/dead band)"},
    "good_B":       {"bias_deg": 0.046, "noise_ug_rtHz": 15.0, "note": "excellent class after field zero (JN2101 B 0.046 deg)"},
    "normal_B":     {"bias_deg": 0.072, "noise_ug_rtHz": 82.0, "note": "normal class after field zero (TMM88D-MJI B 0.072 deg)"},
    "normal_B_rep": {"bias_deg": 0.122, "noise_ug_rtHz": 82.0, "note": "normal B + power-on repeatability 0.05 deg (linear)"},
    "normal_A":     {"bias_deg": 0.17,  "noise_ug_rtHz": 82.0, "note": "normal class as shipped (TMM88D-MJI A 0.17 deg)"},
}

# Sensor zero-error figures from docs/attitude_sensor_survey.md (A = as shipped, B = after field zero) [deg].
# None = not given in the survey table. Class values ('normal'/'low') are the survey's 3-level representative values.
SENSORS = [
    {"name": "ifm JN2101", "A": 0.056, "B": 0.046, "src": "survey table"},
    {"name": "Level Dev. SOLAR-2 (compensated)", "A": 0.037, "B": 0.020, "src": "survey table (-10..60 degC)"},
    {"name": "AdvNav Motus", "A": 0.05, "B": None, "src": "survey table (conditions unknown)"},
    {"name": "Epson M-A370", "A": None, "B": 0.035, "src": "survey table"},
    {"name": "ADI ADIS16575", "A": 0.097, "B": 0.017, "src": "survey table, 1 sigma; B excludes 1.4 mg power-on rep."},
    {"name": "TE DPG +/-10 deg", "A": 0.15, "B": 0.05, "src": "survey table"},
    {"name": "SICK TMM88D-MJI090A", "A": 0.17, "B": 0.072, "src": "survey table"},
    {"name": "SBG Ellipse-A", "A": 0.10, "B": None, "src": "survey text (roll/pitch 0.1 deg; statistic not stated)"},
    {"name": "POSITAL ACS-080 (normal class)", "A": 0.1 + 0.0016 * 45 + 0.05, "B": 0.0016 * 45 + 0.05,
     "src": "no item values in survey; 'normal' class: 0.1 + TC 0.0016..0.004 x 45 K + rep 0.05",
     "A_hi": 0.1 + 0.004 * 45 + 0.05, "B_hi": 0.004 * 45 + 0.05},
    {"name": "Murata SCL3300 raw", "A": 1.0, "B": None, "src": "survey table"},
]

# ---------------------------------------------------------------------------- part 1: cab geometry


def cab_geometry():
    import pandas as pd
    d = pd.read_csv(ROOT / "cad" / "parts_classified.csv", encoding="utf-8-sig")
    top = d["instance_path"].str.split(" / ").str[1]
    bx = lambda df: {  # noqa: E731  body-frame bbox [m]
        "x": [round(float(df["bbox_min_z_mm"].min()) / 1e3, 3), round(float(df["bbox_max_z_mm"].max()) / 1e3, 3)],
        "y": [round(float(df["bbox_min_x_mm"].min()) / 1e3, 3), round(float(df["bbox_max_x_mm"].max()) / 1e3, 3)],
        "z": [round(float(df["bbox_min_y_mm"].min()) / 1e3, 3), round(float(df["bbox_max_y_mm"].max()) / 1e3, 3)]}
    cab = d[top.str.startswith("BUMA CE 3D 20230425")]
    shrink = cab[cab["instance_path"].str.contains("Shrinkwrap")]
    glass = cab[cab["instance_path"].str.contains("CABIN")]
    frame = cab[~cab["instance_path"].str.contains("CABIN|Shrinkwrap", regex=True)]
    housing = d[top.str.startswith("CABIN HOUSING")]
    deck = d[top.str.startswith("BASE DECK")]
    out = {"operator_cab_all_parts": bx(cab), "n_parts": int(len(cab)),
           "cab_shrinkwrap_11": bx(shrink), "cab_glass_and_windows": bx(glass), "cab_frame_parts": bx(frame),
           "cab_mass_step_kg": round(float(cab["mass_step_kg"].sum()), 1),
           "CABIN_HOUSING_R1 (rear housing, cooler covers; not the operator cab)": bx(housing),
           "BASE_DECK": bx(deck)}
    z_floor = frame["bbox_min_y_mm"].min() / 1e3 + RA["cab_floor_above_lowest_cab_frame_m"]
    c = out["operator_cab_all_parts"]
    out["proposed_point_derivation"] = {
        "x_centre": round((c["x"][0] + c["x"][1]) / 2, 3), "y_centre": round((c["y"][0] + c["y"][1]) / 2, 3),
        "z_floor_estimate": round(float(z_floor), 3),
        "rule": "footprint centre of the operator cab bbox; z = lowest cab frame edge + 0.025 m (ASSUMPTION)"}
    return out


# ---------------------------------------------------------------------------- part 2: rocking apparent tilt


def load_modes():
    r = json.load(open(ROOT / "analysis" / "dynamics" / "reference.json", encoding="utf-8"))
    L = r["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"]
    out = {}
    for lv in LEVELS:
        ms = L[lv]["mode_shapes_rev5"]
        refk = [k for k in ms if k.startswith("reference_point_m")][0]
        Phi = np.array(ms["Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)"])
        M = np.array(ms["mass_matrix (same coordinates)"])
        out[lv] = {"ref": np.array(ms[refk]), "Phi": Phi, "M": M, "f": np.array(L[lv]["f_undamped_Hz"][:6]),
                   "zeta": L[lv]["zeta"][:6]}
    return out


def apparent_tilt(phi_col, omega, rho):
    """Apparent (accelerometer) tilt of one mode at a point rho from the mode reference point. Returns true (phi,
    theta), apparent (phi_m, theta_m), vertical acceleration per unit modal amplitude."""
    u, rot = phi_col[:3], phi_col[3:]
    d = u + np.cross(rot, rho)
    a = -omega ** 2 * d
    true = rot[:2]
    app = np.array([rot[0] + a[1] / G, rot[1] - a[0] / G])
    return true, app, a[2]


def rocking_gains(modes, points):
    res = {}
    for lv in LEVELS:
        md = modes[lv]
        # orthogonality check of the stored shapes (12-digit JSON)
        orth = float(np.abs(md["Phi"].T @ md["M"] @ md["Phi"] - np.eye(6)).max())
        res[lv] = {"orthogonality_max_err": orth, "ref_point_m": md["ref"].round(4).tolist(),
                   "f_Hz": md["f"].round(3).tolist(), "points": {}}
        for pname, p in points.items():
            rho = np.asarray(p) - md["ref"]
            rows = []
            for j in range(2):          # 1st (roll-sway) and 2nd (pitch-surge) rocking
                om = 2 * math.pi * md["f"][j]
                tr, ap, az = apparent_tilt(md["Phi"][:, j], om, rho)
                k = int(np.argmax(np.abs(tr)))          # dominant tilt axis of the mode
                gsig = ap[k] / tr[k]
                r_eff = (1 - gsig) * G / om ** 2        # equivalent height of the rotation centre above the IMU
                rows.append({"mode": j + 1, "f_Hz": round(float(md["f"][j]), 3),
                             "axis": ["roll", "pitch"][k],
                             "gain_dominant_signed": round(float(gsig), 2),
                             "gain_norm": round(float(np.linalg.norm(ap) / np.linalg.norm(tr)), 2),
                             "cross_axis_app_over_true_dominant": round(float(ap[1 - k] / tr[k]), 3),
                             "r_eff_m": round(float(r_eff), 3),
                             "vertical_acc_over_true_tilt_m_s2_per_rad": round(float(az / tr[k]), 2)})
            # simple formula with pure rotation about the reference point (CoM): 1 - r w^2/g, r = z_ref - z_imu
            r_simple = float(md["ref"][2] - p[2])
            for row in rows:
                om = 2 * math.pi * row["f_Hz"]
                row["gain_simple_rotation_about_CoM"] = round(1 - r_simple * om ** 2 / G, 2)
            res[lv]["points"][pname] = {"point_m": [round(float(v), 3) for v in p],
                                        "height_below_ref_m": round(r_simple, 3), "modes": rows}
    return res


def verify_gain_timedomain(points, level="top"):
    """Independent path: nonlinear 6-DoF plant of run_control_comparison (free vibration from initial body rates),
    IMU tilt from the averaged specific force (20 ms) vs true attitude. Gain = FFT amplitude ratio at each peak."""
    out = {}
    dm = rcc.dm
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    for pname, pt in points.items():
        rcc.CA["imu_point_body_m"] = list(pt)
        pl = rcc.Plant(level, init_ext=e_op)
        pl.step(np.zeros(4), int(40 / rcc.DT))
        pl.w[:] = [2e-4, 2e-4, 0.0]
        nsub = int(round(rcc.T_CTRL / rcc.DT))
        tru, app = [], []
        for _ in range(int(30 / rcc.T_CTRL)):
            a = pl.step(np.zeros(4), nsub)
            fb = a[0:3] / nsub
            app.append([math.atan2(fb[1], fb[2]), math.atan2(-fb[0], math.hypot(fb[1], fb[2]))])
            tru.append(pl.attitude())
        tru = np.array(tru); app = np.array(app)
        tru -= tru.mean(axis=0); app -= app.mean(axis=0)
        fs = 1 / rcc.T_CTRL
        win = np.hanning(len(tru))[:, None]
        n = 16 * len(tru)
        T = np.fft.rfft(tru * win, n=n, axis=0); A = np.fft.rfft(app * win, n=n, axis=0)
        fr = np.fft.rfftfreq(n, 1 / fs)
        rows = []
        for ax, (lo, hi) in ((0, (1.0, 2.4)), (1, (2.4, 4.0))):   # roll near mode 1, pitch near mode 2 (top)
            sel = (fr > lo) & (fr < hi)
            k = np.where(sel)[0][np.argmax(np.abs(T[sel, ax]))]
            g = A[k, ax] / T[k, ax]
            rows.append({"axis": ["roll", "pitch"][ax], "f_peak_Hz": round(float(fr[k]), 3),
                         "gain_signed_real": round(float(g.real), 2), "gain_imag": round(float(g.imag), 2)})
        out[pname] = rows
    rcc.CA["imu_point_body_m"] = [0.45, 0.0, 0.30]
    return out


def box_extremes(modes, box):
    """Min/max |gain| over the 8 corners of the mount-position uncertainty box."""
    out = {}
    corners = [(x, y, z) for x in box["x"] for y in box["y"] for z in box["z"]]
    for lv in LEVELS:
        md = modes[lv]
        out[lv] = {}
        for j in range(2):
            om = 2 * math.pi * md["f"][j]
            g = []
            for c in corners:
                tr, ap, _ = apparent_tilt(md["Phi"][:, j], om, np.array(c) - md["ref"])
                g.append(float(np.linalg.norm(ap) / np.linalg.norm(tr)))
            out[lv][f"mode{j + 1}"] = [round(min(g), 2), round(max(g), 2)]
    return out


# ---------------------------------------------------------------------------- part 3: filters and loop margin


def filters_and_loop(gains):
    """gains: {level: [(f_Hz, |gain|) for modes 1, 2]} at the cab point. Ripple = A_true * gain * |H|, A_true from
    the closed-loop runs (max true rocking in the 5 s before completion). Loop: PI (Kp, Ki) / s * H_loop * delay."""
    import control as ct
    s = ct.tf("s")
    lp = RA["loop"]
    pade = ct.tf(*ct.pade(lp["T_ctrl_s"] * 1.5, 3))     # ZOH half-sample + 20 ms average ~ 1.5 T delay
    one = ct.tf([1], [1])
    wc = 2 * math.pi * 0.15
    bw2 = wc ** 2 / (s ** 2 + math.sqrt(2) * wc * s + wc ** 2)
    tcf = 1 / (2 * math.pi * 0.05)
    # name: (accelerometer path seen by the control loop, completion filter, filter inside the attitude loop)
    opts = {
        "F0 current: 1st tau 0.5 s + completion 1st tau 1.0 s": (1 / (0.5 * s + 1), 1 / (1.0 * s + 1), 1 / (0.5 * s + 1)),
        "F2: 2 x 1st tau 0.5 s + completion 1st tau 1.0 s": ((1 / (0.5 * s + 1)) ** 2, 1 / (1.0 * s + 1), (1 / (0.5 * s + 1)) ** 2),
        "F3: 1st tau 1.0 s + completion 1st tau 1.0 s": (1 / (1.0 * s + 1), 1 / (1.0 * s + 1), 1 / (1.0 * s + 1)),
        "F1: 2nd Butterworth 0.15 Hz + completion 1st tau 1.0 s": (bw2, 1 / (1.0 * s + 1), bw2),
        "F4: gyro complementary 0.05 Hz (accel path 1st tau 3.2 s) + completion 1st tau 1.0 s":
            (1 / (tcf * s + 1), 1 / (1.0 * s + 1), one),
    }
    res = {"A_true_deg": RA["rocking_true_amp_deg"], "ripple_limit_deg": RA["ripple_limit_deg"], "options": {}}
    for name, (Ha, Hd, Hl) in opts.items():
        worst = {"control": 0.0, "completion": 0.0, "where": None}
        for lv, rows in gains.items():
            for j, (f, g) in enumerate(rows):
                w = 2 * math.pi * f
                avg = abs(math.sin(w * lp["T_ctrl_s"] / 2) / (w * lp["T_ctrl_s"] / 2))
                rc = RA["rocking_true_amp_deg"][lv] * g * avg * float(abs(ct.evalfr(Ha, 1j * w)))
                rd = rc * float(abs(ct.evalfr(Hd, 1j * w)))
                if rd > worst["completion"]:
                    worst = {"control": round(rc, 4), "completion": round(rd, 5), "where": f"{lv} mode {j + 1} {f} Hz"}
        C = lp["Kp_1_s"] + lp["Ki_1_s2"] / s
        L = C / s * Hl * pade
        gm, pm, wg, wp = ct.margin(L)
        cl = ct.feedback(L, 1)
        tt = np.linspace(0, 60, 6001)
        _, y = ct.step_response(cl, tt)
        idx = np.where(np.abs(1 - y) > 0.05)[0]
        ts = float(tt[idx[-1] + 1]) if len(idx) and idx[-1] + 1 < len(tt) else float("nan")
        ww = np.array([0.01, 0.0101])
        ph = np.unwrap(np.angle([ct.evalfr(Hl, 1j * x) for x in ww]))
        res["options"][name] = {
            "worst_ripple_control_deg": worst["control"], "worst_ripple_completion_deg": worst["completion"],
            "worst_at": worst["where"], "meets_ripple_limit": bool(worst["completion"] <= RA["ripple_limit_deg"]),
            "loop_filter_group_delay_s": round(float(-(ph[1] - ph[0]) / (ww[1] - ww[0])), 3),
            "phase_margin_deg": round(float(pm), 1), "crossover_rad_s": round(float(wp), 3),
            "gain_margin": round(float(gm), 1) if np.isfinite(gm) else None, "linear_5pct_settling_s": round(ts, 1)}
    return res


# ---------------------------------------------------------------------------- part 4: budget


def budget():
    out = {"rows": [], "sensor_classification": {}}
    cases = [("deck (old assumption)", 0.1, 0.03, RA["budget_mount_deck_deg"]),
             ("cab", 0.1, 0.03, RA["budget_mount_cab_deg"]),
             ("deck (old assumption)", 0.2, 0.03, RA["budget_mount_deck_deg"]),
             ("cab", 0.2, 0.03, RA["budget_mount_cab_deg"]),
             ("cab", 0.2, 0.06, RA["budget_mount_cab_deg"])]
    for pos, tgt, db, mnt in cases:
        allow = tgt - db - RA["budget_noise_rocking_deg"] - mnt
        mg = math.sin(allow * DEG) * 1e3
        rss = math.sqrt(max(0.0, (tgt - db) ** 2 - RA["budget_noise_rocking_deg"] ** 2 - mnt ** 2))
        key = f"{pos} target {tgt} db {db}"
        out["rows"].append({"case": key, "target_deg": tgt, "deadband_deg": db,
                            "noise_rocking_deg": RA["budget_noise_rocking_deg"], "mount_deg": mnt,
                            "sensor_zero_allow_deg": round(allow, 3), "sensor_zero_allow_mg": round(mg, 2),
                            "sensor_zero_allow_rss_deg": round(rss, 3)})
        cls = {}
        for s in SENSORS:
            a, b = s["A"], s["B"]
            cls[s["name"]] = {"A": None if a is None else round(a, 3), "B": None if b is None else round(b, 3),
                              "A_pass": None if a is None else bool(a <= allow + 1e-9),
                              "B_pass": None if b is None else bool(b <= allow + 1e-9)}
            if "A_hi" in s:
                cls[s["name"]]["A_pass_worst_TC"] = bool(s["A_hi"] <= allow)
                cls[s["name"]]["B_pass_worst_TC"] = bool(s["B_hi"] <= allow)
        out["sensor_classification"][key] = cls
    return out


# ---------------------------------------------------------------------------- part 5: closed-loop runs


def _worker(kw):
    """Run one case of run_control_comparison with overridden assumptions (spawned processes re-import rcc)."""
    kw = dict(kw)
    ov = kw.pop("ov")
    meta = kw.pop("meta")
    rcc.CA.update(ov)
    t0 = time.perf_counter()
    try:
        r = rcc.run_case(keep_series=True, **kw)
    except Exception as e:      # keep the sweep going
        return {**meta, "error": repr(e)}
    S = r.pop("_series")
    t = S["t"]
    att = np.degrees(np.abs(np.column_stack([S["phi"], S["theta"]]))).max(axis=1)
    attm = np.degrees(np.abs(np.column_stack([S["phi_m"], S["theta_m"]]))).max(axis=1)
    out = dict(meta)
    tt = r.get("t_touch_s"); trd = r.get("t_ready_s")
    out["t_lev_s"] = None if (tt is None or trd is None) else round(trd - tt, 2)
    out["t_done_after_touch_s"] = None if (tt is None or r.get("t_done_s") is None) else round(r["t_done_s"] - tt, 2)
    for lim in (0.1, 0.2):     # first time the TRUE attitude stays within the limit until the end (after touchdown)
        if tt is None:
            out[f"t_in_{lim}_s"] = None
            continue
        bad = np.where((t >= tt) & (att > lim))[0]
        idx = bad[-1] + 1 if len(bad) else int(np.argmax(t >= tt))
        out[f"t_in_{lim}_s"] = round(float(t[idx]) - tt, 2) if idx < len(t) else None
    out["ss_true_deg"] = r.get("ss_true_att_deg_maxabs")
    out["ss_true_mean_deg"] = r.get("ss_true_att_deg_mean")
    out["ss_meas_mean_deg"] = r.get("ss_meas_att_deg_mean")
    fin = t >= t[-1] - 5.0
    out["meas_ripple_pp_deg"] = round(float(np.ptp(attm[fin])), 4)
    td = r.get("t_done_s")
    if td is not None and tt is not None:
        w = (t >= max(tt, td - 5.0)) & (t <= td)
        a2 = np.degrees(np.column_stack([S["phi"], S["theta"]]))
        hp = a2 - rcc._movavg(a2, 50)
        out["pre_done_true_rocking_deg"] = round(float(np.abs(hp[w]).max()), 4)
        am = np.degrees(np.column_stack([S["phi_m"], S["theta_m"]]))
        out["pre_done_ctrl_filtered_ripple_deg"] = round(float(np.abs(am[w] - rcc._movavg(am, 50)[w]).max()), 4)
    out["rocking_peak_deg"] = r.get("rocking_peak_deg")
    out["min_true_kN"] = r.get("min_true_cyl_force_kN")
    out["max_bar"] = r.get("max_pressure_bar")
    other = [f for f in r.get("fails", []) if f != rcc.ss_fail_label()]   # target 0.1 deg set in ov (legacy study basis)
    out["other_fails"] = other
    ss = out["ss_true_deg"]
    out["pass_0.1"] = bool(not other and ss is not None and ss <= 0.1)
    out["pass_0.2"] = bool(not other and ss is not None and ss <= 0.2)
    out["n_relevel"] = sum(1 for e in r.get("events", []) if str(e[1]).startswith("relevel"))
    out["wall_s"] = round(time.perf_counter() - t0, 1)
    return out


def sim_cases():
    slopes = [("flat", 0, 0), ("pitch+3", 0, 3), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213)]
    cases = []
    for cand in ("C2", "C8"):
        for lv in LEVELS:
            for tag, ro, pi in slopes:
                for pt_name, pt in (("cab", RA["imu_cab_point_m"]), ("old", RA["imu_old_point_m"])):
                    for gname, gr in GRADES.items():
                        for db in (0.03, 0.06):
                            if pt_name == "old" and (db != 0.03 or gname not in ("ideal", "good_B", "normal_B")):
                                continue
                            bmg = math.sin(gr["bias_deg"] * DEG) * 1e3
                            variants = [("F0", 0.5, 1.0)]
                            if pt_name == "cab" and gname == "normal_B" and db == 0.03:
                                variants += [("F3_ctrl_tau1.0", 1.0, 1.0), ("Fd_done_tau2.0", 0.5, 2.0)]
                            for fname, tau_c, tau_d in variants:
                                # every key is set on every task: worker processes keep CA between tasks
                                ov = {"imu_point_body_m": list(pt), "done_att_deg": db, "relevel_att_deg": db + 0.04,
                                      "trim_deadband_deg": round(db * 2 / 3, 4), "imu_lpf_tau_s": tau_c, "imu_lpf_order": 1,
                                      "accuracy_target_deg": 0.1,   # study basis (rcc defaults changed 2026-10-20)
                                      "done_filter_tau_s": tau_d,
                                      "imu_custom": {"bias_mg": [bmg, bmg], "noise_ug_rtHz": gr["noise_ug_rtHz"]}}
                                meta = {"cand": cand, "level": lv, "slope": tag, "point": pt_name, "grade": gname,
                                        "db_deg": db, "filt": fname}
                                cases.append({"cand": cand, "level": lv, "roll": ro, "pitch": pi, "imu": "custom",
                                              "ov": ov, "meta": meta})
    return cases


def summarise_sim(runs):
    out = {}
    keyf = lambda r: (r["cand"], r["point"], r["grade"], r["db_deg"], r["filt"])  # noqa: E731
    groups = {}
    for r in runs:
        if "error" in r:
            continue
        groups.setdefault(keyf(r), []).append(r)
    for k, rs in sorted(groups.items()):
        tl = [r["t_lev_s"] for r in rs if r["t_lev_s"] is not None]
        out["|".join(map(str, k))] = {
            "n": len(rs), "pass_0.1": sum(r["pass_0.1"] for r in rs), "pass_0.2": sum(r["pass_0.2"] for r in rs),
            "ss_true_max_deg": max(r["ss_true_deg"] or 9 for r in rs),
            "t_lev_median_s": round(float(np.median(tl)), 1) if tl else None,
            "t_lev_max_s": round(float(np.max(tl)), 1) if tl else None,
            "rocking_peak_max_deg": max(r["rocking_peak_deg"] or 0 for r in rs),
            "meas_ripple_pp_max_deg": max(r["meas_ripple_pp_deg"] for r in rs),
            "pre_done_true_rocking_max_deg": max(r.get("pre_done_true_rocking_deg", 0) for r in rs),
            "pre_done_ctrl_filtered_ripple_max_deg": max(r.get("pre_done_ctrl_filtered_ripple_deg", 0) for r in rs),
            "relevels": sum(r["n_relevel"] for r in rs),
            "other_fails": sorted({f"{r['level']}:{r['slope']}:{'/'.join(r['other_fails'])}" for r in rs
                                   if r["other_fails"]})}
    return out


def time_saving(runs):
    """Paired levelling-time difference db 0.06 - db 0.03 at the cab point (same cand, level, slope, grade)."""
    idx = {}
    for r in runs:
        if r.get("point") == "cab" and r.get("filt") == "F0" and "error" not in r:
            idx[(r["cand"], r["level"], r["slope"], r["grade"], r["db_deg"])] = r
    out = {}
    for cand in ("C2", "C8"):
        d = []
        for (c, lv, sl, gr, db), r in idx.items():
            if c == cand and db == 0.03:
                r2 = idx.get((c, lv, sl, gr, 0.06))
                if r2 and r["t_lev_s"] is not None and r2["t_lev_s"] is not None:
                    d.append(r2["t_lev_s"] - r["t_lev_s"])
        out[cand] = {"n": len(d), "median_s": round(float(np.median(d)), 2) if d else None,
                     "min_s": round(float(np.min(d)), 2) if d else None, "max_s": round(float(np.max(d)), 2) if d else None}
    return out


# ---------------------------------------------------------------------------- main


def main():
    t0 = time.perf_counter()
    res = {"meta": {"script": "scripts/dynamics/run_imu_accuracy_review.py", "assumptions": RA, "grades": GRADES,
                    "frames": "body x fwd, y left, z up (m); roll about x, pitch about y (theta>0 nose down); "
                              "gravity (0,0,-9.80665) m/s^2; mode shapes: reference.json L1 mode_shapes_rev5",
                    "apparent_tilt": "phi_m = phi + a_y/g, theta_m = theta - a_x/g, a = -w^2 (u + rot x rho)",
                    "sim_base": "run_control_comparison.run_case (imported; its JSON/PNG are not written)"}}
    res["cab"] = cab_geometry()
    modes = load_modes()
    pts = {"cab": RA["imu_cab_point_m"], "old_deck": RA["imu_old_point_m"],
           "cab_seat_height": [RA["imu_cab_point_m"][0], RA["imu_cab_point_m"][1], 0.80],
           "cab_roof": [RA["imu_cab_point_m"][0], RA["imu_cab_point_m"][1], 1.90]}
    res["rocking"] = rocking_gains(modes, pts)
    res["rocking_box"] = box_extremes(modes, RA["imu_cab_box_m"])
    res["rocking_timedomain_check_top"] = verify_gain_timedomain({"cab": pts["cab"], "old_deck": pts["old_deck"],
                                                                  "cab_roof": pts["cab_roof"]})
    print(json.dumps(res["rocking_timedomain_check_top"]))
    gains = {lv: [(m["f_Hz"], m["gain_norm"]) for m in res["rocking"][lv]["points"]["cab"]["modes"]] for lv in LEVELS}
    res["filters"] = filters_and_loop(gains)
    res["budget"] = budget()
    print(json.dumps({k: res[k] for k in ("cab", "rocking_box", "filters")}, indent=1, ensure_ascii=False))
    for lv in LEVELS:
        for pn, pv in res["rocking"][lv]["points"].items():
            print(lv, pn, [(m["mode"], m["f_Hz"], m["gain_dominant_signed"], m["gain_norm"], m["r_eff_m"],
                            m["gain_simple_rotation_about_CoM"]) for m in pv["modes"]])
    print(json.dumps(res["budget"]["rows"], indent=1))
    if "--no-sim" not in sys.argv:
        from multiprocessing import Pool
        cases = sim_cases()
        _worker(dict(cases[0]))                     # numba cache
        with Pool(min(20, os.cpu_count() or 4)) as pool:
            runs = pool.map(_worker, cases, chunksize=1)
        res["sim_summary"] = summarise_sim(runs)
        res["sim_deadband_time_saving_cab"] = time_saving(runs)
        keep = ("cand", "level", "slope", "point", "grade", "db_deg", "filt", "t_lev_s", "t_in_0.1_s", "t_in_0.2_s",
                "ss_true_deg", "pass_0.1", "pass_0.2", "min_true_kN", "rocking_peak_deg", "pre_done_true_rocking_deg",
                "other_fails", "error")
        res["sim_runs_fields"] = keep
        res["sim_runs"] = [[r.get(k) for k in keep] for r in runs]
        print(json.dumps(res["sim_summary"], indent=1))
        print(json.dumps(res["sim_deadband_time_saving_cab"]))
        errs = [r for r in runs if "error" in r]
        print("errors:", len(errs), errs[:2])
    res["meta"]["wall_s"] = round(time.perf_counter() - t0, 1)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, separators=(",", ":"), default=float, ensure_ascii=False)
    print("wrote", OUT_JSON, res["meta"]["wall_s"], "s")


if __name__ == "__main__":
    main()
