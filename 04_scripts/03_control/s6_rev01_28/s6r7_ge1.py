"""S6 rev. 7: re-process GE1 shadow series of batch stage2_20261021_232845.

Two paths:
  (1) controller sensor path: ge1_timeseries.csv (d_i, r from C2 R4.1 support_geometry)
  (2) truth path: pads.npz contact_point_world (Chrono pad contact points, world frame)

Outputs JSON to ctrl-run/s6r7_ge1_out.json.
"""
import glob
import json
import math
import os

import numpy as np
import pandas as pd

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
B = str(REPO / r"07_results\S6\stage2_20261021_232845")
OUT = os.path.join(str(OUT_DIR), "s6r7_ge1_out.json")
LEGS = ["FL", "FR", "RL", "RR"]
T_CTRL = 0.02
ARW = {"ideal": 0.0, "good_zeroed": 0.15, "normal_zeroed": 0.30, "normal_zeroed_repeatability": 0.30}
BIAS_DEG_H = {"ideal": 0.0, "good_zeroed": 5.0, "normal_zeroed": 20.0, "normal_zeroed_repeatability": 20.0}


def sigma_sample_deg_s(grade):
    """Per-axis std of one 20 ms gyro sample, density*sqrt(1/(2T)) (imu.py convention)."""
    n = ARW.get(grade, 0.0) / 60.0  # deg/s/sqrt(Hz)
    return n * math.sqrt(1.0 / (2.0 * T_CTRL))


def run_hold(mask, n_hold):
    """True where mask has been True for at least n_hold consecutive samples (inclusive)."""
    out = np.zeros_like(mask)
    c = 0
    for k, m in enumerate(mask):
        c = c + 1 if m else 0
        out[k] = c >= n_hold
    return out


def window_mean(x, n):
    """Trailing moving mean over n samples (NaN for first n-1)."""
    c = np.cumsum(np.insert(x, 0, 0.0, axis=0), axis=0)
    m = (c[n:] - c[:-n]) / n
    pad = np.full((n - 1,) + x.shape[1:], np.nan)
    return np.concatenate([pad, m], axis=0)


def lsq_plane_residual(z, xy):
    """4-point plane fit residuals (z = a + b x + c y)."""
    A = np.column_stack([np.ones(4), xy[:, 0], xy[:, 1]])
    coef, *_ = np.linalg.lstsq(A, z, rcond=None)
    return z - A @ coef


def median_others(h):
    """d_i = h_i - median_{j != i} h_j along last axis (4 legs)."""
    out = np.empty_like(h)
    for i in range(4):
        others = np.delete(h, i, axis=-1)
        out[..., i] = h[..., i] - np.median(others, axis=-1)
    return out


res = {}
for cdir in sorted(glob.glob(B + r"\*\\")):
    case = os.path.basename(os.path.normpath(cdir))
    rj = json.load(open(cdir + "result.json", encoding="utf-8"))
    st = rj["settings"]
    grade = st["grade"]
    t0 = rj["runner"]["start_t_s"]
    df = pd.read_csv(cdir + "ge1_timeseries.csv")
    t = df["t_s"].to_numpy()
    d = df[[f"d_{l}_mm" for l in LEGS]].to_numpy(float)
    r = df["r_mm"].to_numpy(float)
    u = df[[f"u_{l}_m_s" for l in LEGS]].to_numpy(float)
    con = df[[f"contact_{l}" for l in LEGS]].to_numpy(bool)
    ph = df["phase"].to_numpy(str)
    grms = df["gyro_rms_0p5s_deg_s"].to_numpy(float)
    stat_cur = df["stationary"].to_numpy(bool)
    valid = np.isfinite(d).all(axis=1)

    # per-axis gyro from record.npz (bias-removed with the controller CHECK estimate)
    z = np.load(cdir + r"record\record.npz", allow_pickle=False)
    w = np.degrees(z["meas.angular_rate"][:, :2])  # deg/s, roll p, pitch q (body)
    tz = z["t"] - t0
    b_est = np.degrees(np.array(rj["controller_meta"]["target"]["gyro_bias_rad_s"][:2], float)) \
        if rj["controller_meta"]["target"].get("gyro_bias_rad_s") is not None else np.zeros(2)
    wc = w - b_est
    assert len(tz) == len(t), (case, len(tz), len(t))
    sig = sigma_sample_deg_s(grade)
    n05 = int(round(0.5 / T_CTRL))
    n10 = int(round(1.0 / T_CTRL))
    rms_axis = np.sqrt(window_mean(wc ** 2, n05))           # per-axis 0.5 s RMS, bias removed
    rms_axis_comp = np.sqrt(np.clip(rms_axis ** 2 - sig ** 2, 0.0, None))  # noise-compensated
    mean_axis_1s = np.abs(window_mean(wc, n10))              # |1 s mean| per axis, bias removed
    rms_mag_raw = np.sqrt(window_mean((w ** 2).sum(axis=1), n05))  # as exporter (no bias removal)

    phase_ok = np.isin(ph, ["done", "probe", "ready"])
    cmd0 = run_hold(np.all(u == 0.0, axis=1), n10)
    gates = {
        "current(R4.1 export)": stat_cur,
        "cmd_only": phase_ok & cmd0,
        "proposed": phase_ok & cmd0 & run_hold(
            (rms_axis_comp.max(axis=1) <= 0.02) & (mean_axis_1s.max(axis=1) <= 0.01), n05),
    }
    ev_rel = None
    if st.get("event") in ("settle_RR_30", "retract_RR_25", "settle_RR"):
        ev_rel = 42.02 if st.get("event") != "settle_RR" else None
    out = {"grade": grade, "floor": st["floor"], "event": st.get("event"), "sigma_axis_deg_s": sig,
           "check_bias_deg_h": (b_est * 3600).tolist(), "configured_bias_deg_h": BIAS_DEG_H.get(grade),
           "seed": rj["runner"].get("sensor_seed"), "gates": {}}
    for gname, g in gates.items():
        g = g & valid
        sel_pre = g if ev_rel is None else g & (t < ev_rel)
        dd = np.where(con, np.abs(d), np.nan)[sel_pre]
        out["gates"][gname] = {
            "n": int(sel_pre.sum()),
            "grounded_d_maxabs_mm": float(np.nanmax(dd)) if dd.size and np.isfinite(dd).any() else None,
            "r_maxabs_mm": float(np.nanmax(np.abs(r[sel_pre]))) if sel_pre.any() else None,
        }
    # gyro statistics in READY with cmd0
    sel = (ph == "ready") & cmd0 & (t < (ev_rel if ev_rel else 1e9))
    if sel.any():
        out["ready_gyro"] = {
            "n": int(sel.sum()),
            "rms_mag_raw_min_deg_s": float(np.nanmin(rms_mag_raw[sel])),
            "rms_mag_raw_median_deg_s": float(np.nanmedian(rms_mag_raw[sel])),
            "rms_axis_comp_p95_deg_s": np.nanpercentile(rms_axis_comp[sel], 95, axis=0).tolist(),
            "mean1s_axis_p95_deg_s": np.nanpercentile(mean_axis_1s[sel], 95, axis=0).tolist(),
            "std_axis_deg_s": np.nanstd(wc[sel], axis=0).tolist(),
        }
    # level-phase false flag check with proposed gate (G1 |d|>5 while gate open)
    gp = gates["proposed"] & valid
    flag_any = (np.abs(np.where(con, d, 0.0)) > 5.0).any(axis=1) | (np.abs(r) > 1.4)
    pre = gp if ev_rel is None else gp & (t < ev_rel)
    out["proposed_gate_flag_samples_pre_event"] = int((flag_any & pre).sum())

    if case.startswith("RE1"):
        ev = ev_rel
        phases = rj["phases"]
        left_ready = next(p[0] for p in phases if p[0] > ev and p[1] != "ready")
        rr = d[:, 3]
        k_any = np.where((t >= ev) & (rr < -5.0) & valid)[0] if "settle" in st["event"] else \
            np.where((t >= ev) & (rr > 5.0) & valid)[0]
        k_st = [k for k in k_any if gates["proposed"][k]]
        ev_out = {"event_rel_s": ev, "left_ready_rel_s": left_ready,
                  "RR_cross_any_dt_s": float(t[k_any[0]] - ev) if len(k_any) else None,
                  "RR_cross_gate_dt_s": float(t[k_st[0]] - ev) if k_st else None,
                  "RR_d_at_cross_mm": float(rr[k_any[0]]) if len(k_any) else None}
        win = (t >= ev) & (t < left_ready) & valid
        ev_out["others_maxabs_d_event_to_leftready_mm"] = np.nanmax(np.abs(d[win][:, :3]), axis=0).tolist() if win.any() else None
        ev_out["RR_min_max_d_event_to_leftready_mm"] = [float(np.nanmin(rr[win])), float(np.nanmax(rr[win]))] if win.any() else None
        ev_out["r_event_to_leftready_mm"] = [float(np.nanmin(r[win])), float(np.nanmax(r[win]))] if win.any() else None
        # re-READY reference: sensor-path delta definition d_delta = d(t) - d(t_ref) if median rank stable
        ref_abs = rj["controller_meta"]["support_geometry"]["reference_t_s"]
        ref_rel = ref_abs - t0
        kref = int(np.argmin(np.abs(t - ref_rel)))
        post = (t > ref_rel) & valid
        ev_out["ref_rel_s"] = ref_rel
        ev_out["d_at_ref_mm"] = d[kref].tolist()
        ev_out["r_at_ref_mm"] = float(r[kref])
        if post.any():
            ev_out["post_ref_d_raw_maxabs_mm"] = np.nanmax(np.abs(d[post]), axis=0).tolist()
            ev_out["post_ref_d_delta_maxabs_mm"] = np.nanmax(np.abs(d[post] - d[kref]), axis=0).tolist()
            ev_out["post_ref_r_delta_maxabs_mm"] = float(np.nanmax(np.abs(r[post] - r[kref])))
        # truth path from pads.npz
        p = np.load(cdir + "pads.npz", allow_pickle=False)
        tp = p["t"] - t0
        cp = p["contact_point_world"]  # (n,4,3)
        bc = p["ball_centre_world"]
        Np = p["N"]
        # use ball centre (always defined) for heights; contact point for check
        h = bc[:, :, 2] * 1e3
        xy = bc[:, :, :2]
        kpre = int(np.argmin(np.abs(tp - (ev - 0.5))))
        kend = len(tp) - 1
        kr = int(np.argmin(np.abs(tp - ref_rel)))
        ev_out["truth_ball_z_change_pre_to_end_mm"] = (h[kend] - h[kpre]).tolist()
        ev_out["truth_N_end_kN"] = (Np[kend] / 1e3).tolist()
        # current definition on truth: n0 = LS normal at ref, d = n0.p - median others
        def ls_normal(pts):
            A = np.column_stack([np.ones(4), pts[:, 0], pts[:, 1]])
            c, *_ = np.linalg.lstsq(A, pts[:, 2], rcond=None)
            n = np.array([-c[1], -c[2], 1.0])
            return n / np.linalg.norm(n)
        pts_ref = bc[kr] * 1e3
        n0 = ls_normal(pts_ref)
        hh_end = bc[kend] * 1e3 @ n0
        hh_ref = pts_ref @ n0
        ev_out["truth_current_def_d_end_mm"] = median_others(hh_end[None, :])[0].tolist()
        ev_out["truth_current_def_d_ref_mm"] = median_others(hh_ref[None, :])[0].tolist()
        ev_out["truth_delta_def_d_end_mm"] = median_others((hh_end - hh_ref)[None, :])[0].tolist()
        ev_out["truth_planar_residual_end_mm"] = lsq_plane_residual(h[kend], xy[kend]).tolist()
        # delta definition vs pre-event reference (first READY), during event window
        kr0 = int(np.argmin(np.abs(tp - (ev - 0.5))))
        n00 = ls_normal(bc[kr0] * 1e3)
        hh0 = bc[kr0] * 1e3 @ n00
        sel_p = (tp >= ev) & (tp < left_ready)
        if sel_p.any():
            hd = (bc[sel_p] * 1e3) @ n00 - hh0
            dd = median_others(hd)
            ev_out["truth_delta_def_event_window_maxabs_mm"] = np.max(np.abs(dd), axis=0).tolist()
            ev_out["truth_RR_delta_end_of_window_mm"] = float(dd[-1, 3])
        out["event_case"] = ev_out
    res[case] = out

json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1)
for c, o in res.items():
    g = o["gates"]
    print(f"{c:46s} {o['grade']:28s} cur n={g['current(R4.1 export)']['n']:5d} "
          f"d={g['current(R4.1 export)']['grounded_d_maxabs_mm']} | cmd n={g['cmd_only']['n']:5d} "
          f"d={g['cmd_only']['grounded_d_maxabs_mm']:.3f} r={g['cmd_only']['r_maxabs_mm']:.3f} | "
          f"prop n={g['proposed']['n']:5d} d={g['proposed']['grounded_d_maxabs_mm']} "
          f"r={g['proposed']['r_maxabs_mm']} flags={o['proposed_gate_flag_samples_pre_event']}")
print(OUT)
