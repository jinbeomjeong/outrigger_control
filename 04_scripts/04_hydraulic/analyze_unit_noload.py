"""Analysis of the outrigger single-cylinder bench test with the pad unloaded (airborne).

Data: 08_test_data/2026-10-22_outrigger_unit_noload/sample.csv (user supplied, read only).
Columns: clock (mm:ss.f), elapsed s, pressure1_bar, pressure2_bar, length_mm.
Test set-up (user, 2026-10-22): hydraulic power pack connected directly to the cylinder,
on/off valve operation (the real machine uses a proportional pressure-compensated valve bank).

What the script does
  1. sampling statistics (period, jitter, gaps, timestamp quantum)
  2. sensor characteristics at rest (zero offset, noise sigma, resolution / quantum)
  3. velocity from the length signal (local linear fit) and phase segmentation
  4. steady-state pressures of every motion phase (offset corrected, gauge)
  5. area ratio phi = A_head / A_annulus from several independent routes
  6. seal friction F_s = (F_ext - F_ret) / 2 and weight check W = -(F_ext + F_ret) / 2
  7. transitions: valve-on -> motion delay, pressure settling, stall pressure rise,
     relief level, overshoot, lumped beta_eff / L_eff from the stall rise
  8. locked leak-down after the valve is switched off (exponential fit)
  9. figures (PNG) and a JSON summary

Sign convention: x = length_mm (stroke, + = extension, 0 = fully retracted). The rod points
down (pad below), so the rod weight assists extension. F_cyl = p_h A_p - p_r A_ann (+ pushes
the pad down). Airborne quasi-static balance: extend  F_cyl + W = +F_s,
                                             retract F_cyl + W = -F_s.
All pressures in the outputs are gauge [bar g] after the zero-offset correction unless the key
says "raw".

Run:
  conda run -n hydraulics-dev python -I analyze_unit_noload.py [--csv PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import curve_fit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "08_test_data" / "2026-10-22_outrigger_unit_noload" / "sample.csv"
DEFAULT_OUT = ROOT / "06_analysis" / "03_hydraulic" / "unit_noload"

BAR = 1.0e5  # Pa per bar
G = 9.80665

# Cylinder dimensions: manufacturing drawing REXOME35-9206 Rev.0 (user decision 2026-10-22,
# 08_test_data/datasheets/cylinder_{front,rear}_extract.md; bore/rod read from H9/f8 fits)
CYLINDERS = {
    "front": {"bore_m": 0.130, "rod_m": 0.110},
    "rear": {"bore_m": 0.110, "rod_m": 0.090},
}
for _c in CYLINDERS.values():
    _c["A_p"] = math.pi / 4 * _c["bore_m"] ** 2
    _c["A_ann"] = math.pi / 4 * (_c["bore_m"] ** 2 - _c["rod_m"] ** 2)
    _c["phi"] = _c["A_p"] / _c["A_ann"]
A_P_F = CYLINDERS["front"]["A_p"]  # 1.3273e-2 m^2 (default case; the data point to the front cylinder)
# Superseded REXOME33 CAD/YAML values (bore 115 / rod 110): only for the consistency check
PHI_OLD = (0.115**2) / (0.115**2 - 0.110**2)  # 11.76
M_ROD_KG = 106.784  # moving mass from the REXOME33 CAD (before the dimension change), not in the drawing
W_ROD_N = M_ROD_KG * G  # 1.047 kN
V_MAX_SPEC_MM_S = 680.0 / 30.0  # 22.67 mm/s (CLAUDE.md, 680 mm / 30 s)
STROKE_SPEC_MM = 700.0  # drawing "Stoke 700"
L0_DEAD_M = 0.05  # ASSUMPTION: dead length of the head chamber (YAML oil_dead_length_m)
SEED = 20261022

# Analysis settings
V_HALF_WINDOW_S = 0.5  # local linear fit half window for the velocity
V_MOVE_MM_S = 1.0  # |v| above this = moving
X_STEADY_RANGE_MM = (100.0, 600.0)  # steady window for force balance (away from cushions)


# ----------------------------------------------------------------------------- loading
def load(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if df.shape[1] != 5:
        raise ValueError(f"expected 5 columns, got {df.shape[1]}")
    df.columns = ["clock", "t", "p1", "p2", "x"]
    for c in ("t", "p1", "p2", "x"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    mm, ss = zip(*(s.split(":") for s in df["clock"].astype(str)))
    df["clock_s"] = np.array(mm, dtype=float) * 60.0 + np.array(ss, dtype=float)
    return df.reset_index(drop=True)


def local_velocity(t: np.ndarray, x: np.ndarray, half: float) -> np.ndarray:
    """Slope of a local least-squares line over [t - half, t + half] (units of x per s)."""
    v = np.full_like(x, np.nan, dtype=float)
    j0 = 0
    j1 = 0
    n = len(t)
    for i in range(n):
        while t[j0] < t[i] - half:
            j0 += 1
        while j1 < n and t[j1] <= t[i] + half:
            j1 += 1
        tt = t[j0:j1]
        if len(tt) >= 3:
            v[i] = np.polyfit(tt - t[i], x[j0:j1], 1)[0]
    return v


def quantum(values: np.ndarray) -> dict:
    """Estimate the reading quantum: smallest common step of the distinct values."""
    u = np.unique(np.round(values, 6))
    d = np.diff(u)
    d = d[d > 1e-9]
    q0 = float(np.median(d[d < 1.5 * d.min()]))
    k = (u - u[0]) / q0
    resid = float(np.max(np.abs(k - np.round(k))))
    return {"quantum": q0, "n_distinct": int(len(u)), "max_residual_counts": resid}


# ----------------------------------------------------------------------------- segmentation
def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def segment(df: pd.DataFrame) -> list[dict]:
    t, x, v = df.t.values, df.x.values, df.v.values
    moving = np.abs(v) > V_MOVE_MM_S
    segs = []
    # moving runs
    mv = [r for r in runs(moving) if t[r[1]] - t[r[0]] >= 0.3]
    # build an ordered list: stationary between moving runs
    edges = []
    prev = 0
    for a, b in mv:
        if a > prev:
            edges.append(("still", prev, a - 1))
        edges.append(("move", a, b))
        prev = b + 1
    if prev < len(t):
        edges.append(("still", prev, len(t) - 1))
    for kind, a, b in edges:
        s = {"kind": kind, "i0": int(a), "i1": int(b), "t0": float(t[a]), "t1": float(t[b]),
             "x0": float(x[a]), "x1": float(x[b])}
        if kind == "move":
            vm = float(np.median(v[a:b + 1]))
            s["dir"] = "extend" if vm > 0 else "retract"
            s["v_peak_mm_s"] = float(np.max(np.abs(v[a:b + 1])))
            if s["v_peak_mm_s"] >= 80:
                s["label"] = s["dir"] + "_jump"
            elif t[b] - t[a] >= 10.0:
                s["label"] = s["dir"]  # main stroke phase
            else:
                s["label"] = s["dir"] + "_short"
        else:
            xm = float(np.median(x[a:b + 1]))
            s["x_med"] = xm
            s["label"] = ("ext_end" if xm > 690 else "ret_end" if xm < 1.0 else "rest")
        segs.append(s)
    # number labels
    count: dict[str, int] = {}
    short = {"extend": "E", "retract": "R"}
    for s in segs:
        count[s["label"]] = count.get(s["label"], 0) + 1
        if s["label"] in short:
            s["name"] = f"{short[s['label']]}{count[s['label']]}"
        else:
            s["name"] = f"{s['label']}#{count[s['label']]}"
    return segs


# ----------------------------------------------------------------------------- analysis pieces
def sampling_stats(df: pd.DataFrame) -> dict:
    dt = np.diff(df.t.values)
    tick = 1.0 / 64.0
    ticks = dt / tick
    dclk = np.diff(df.clock_s.values)
    return {
        "n_rows": int(len(df)), "t_start_s": float(df.t.iloc[0]), "t_end_s": float(df.t.iloc[-1]),
        "dt_mean_s": float(dt.mean()), "dt_median_s": float(np.median(dt)),
        "dt_std_s": float(dt.std()), "dt_min_s": float(dt.min()), "dt_max_s": float(dt.max()),
        "dt_p05_p95_s": [float(np.percentile(dt, 5)), float(np.percentile(dt, 95))],
        "rate_effective_Hz": float((len(df) - 1) / (df.t.iloc[-1] - df.t.iloc[0])),
        "n_gaps_gt_0p2s": int(np.sum(dt > 0.2)), "n_gaps_gt_0p5s": int(np.sum(dt > 0.5)),
        "gaps_gt_0p5s": [[float(df.t.iloc[i]), float(dt[i])] for i in np.where(dt > 0.5)[0]],
        "fraction_dt_multiple_of_15p625ms": float(np.mean(np.abs(ticks - np.round(ticks)) < 0.12)),
        "clock_minus_elapsed_s": [float(np.min(df.clock_s - df.t)), float(np.max(df.clock_s - df.t))],
        "clock_dt_unique_s": sorted({round(float(d), 3) for d in dclk})[:10],
    }


def stationary_stats(df: pd.DataFrame, a: int, b: int) -> dict:
    s = df.iloc[a:b + 1]
    tt = s.t.values - s.t.values[0]
    out = {"t0": float(s.t.iloc[0]), "t1": float(s.t.iloc[-1]), "n": int(len(s))}
    for c in ("p1", "p2", "x"):
        y = s[c].values
        p = np.polyfit(tt, y, 1)
        r = y - np.polyval(p, tt)
        d = np.diff(y)
        out[c] = {"mean": float(y.mean()), "std": float(y.std(ddof=1)),
                  "std_detrended": float(r.std(ddof=1)), "trend_per_s": float(p[0]),
                  "min": float(y.min()), "max": float(y.max()),
                  "std_diff_over_sqrt2": float(d.std(ddof=1) / math.sqrt(2))}
    return out


def steady_window(df: pd.DataFrame, seg: dict) -> pd.DataFrame:
    s = df.iloc[seg["i0"]:seg["i1"] + 1]
    lo, hi = X_STEADY_RANGE_MM
    return s[(s.x >= lo) & (s.x <= hi)]


def ols(xv: np.ndarray, yv: np.ndarray, rng: np.random.Generator, nboot: int = 2000) -> dict:
    p = np.polyfit(xv, yv, 1)
    n = len(xv)
    boots = []
    for _ in range(nboot):
        k = rng.integers(0, n, n)
        if np.ptp(xv[k]) > 0:
            boots.append(np.polyfit(xv[k], yv[k], 1)[0])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    r = yv - np.polyval(p, xv)
    return {"slope": float(p[0]), "intercept": float(p[1]), "slope_ci95": [float(lo), float(hi)],
            "n": int(n), "x_range": [float(xv.min()), float(xv.max())],
            "resid_std": float(r.std(ddof=2))}


def forces(ph_bar: np.ndarray, pr_bar: np.ndarray, phi: float, a_p: float = A_P_F) -> np.ndarray:
    """F_cyl [N] for head area a_p and area ratio phi."""
    return (ph_bar - pr_bar / phi) * BAR * a_p


def first_index(cond: np.ndarray, start: int = 0) -> int | None:
    idx = np.where(cond[start:])[0]
    return int(idx[0] + start) if len(idx) else None


def transition_start(df: pd.DataFrame, seg: dict, v_ss: float) -> dict:
    """Valve-on -> motion for a motion segment (on/off valve step)."""
    t, x, p1, p2, v = (df[c].values for c in ("t", "x", "p1", "p2", "v"))
    i_m = seg["i0"]
    # motion onset: first sample where x leaves the pre-start median by > 0.5 mm
    pre = np.where((t >= t[i_m] - 3.0) & (t < t[i_m] - 1.5))[0]
    if len(pre) < 3:
        pre = np.arange(max(0, i_m - 15), max(1, i_m - 5))
    x_base = np.median(x[pre])
    p1_base, p2_base = np.median(p1[pre]), np.median(p2[pre])
    j0 = pre[-1]
    i_x = first_index(np.abs(x - x_base) > 0.5, j0)
    i_p = first_index((np.abs(p1 - p1_base) > 1.0) | (np.abs(p2 - p2_base) > 1.0), j0)
    i_v90 = first_index(np.abs(v) >= 0.9 * abs(v_ss), i_x if i_x is not None else j0)
    out = {"t_pressure_change": float(t[i_p]) if i_p is not None else None,
           "t_motion": float(t[i_x]) if i_x is not None else None,
           "t_v90": float(t[i_v90]) if i_v90 is not None else None,
           "p1_before": float(p1_base), "p2_before": float(p2_base)}
    if i_p is not None and i_x is not None:
        out["delay_pressure_to_motion_s"] = float(t[i_x] - t[i_p])
    if i_x is not None and i_v90 is not None:
        out["motion_to_v90_s"] = float(t[i_v90] - t[i_x])
    # pressures settle: steady values = median over 2..4 s after motion onset
    if i_x is not None:
        w = (t >= t[i_x] + 2.0) & (t <= t[i_x] + 4.0)
        for c, arr, base in (("p1", p1, p1_base), ("p2", p2, p2_base)):
            ss = float(np.median(arr[w]))
            win = np.where((t >= t[i_p] if i_p is not None else t >= t[i_x]) & (t <= t[i_x] + 2.0))[0]
            seg_arr = arr[win]
            if len(seg_arr) == 0:
                out[c] = {"steady": ss, "step": float(ss - base), "note": "pressure change after motion window"}
                continue
            if ss > base:
                extreme = float(seg_arr.max())
                over = extreme - ss
                under = ss - float(seg_arr[np.argmax(seg_arr >= ss - 0.05 * (ss - base)):].min()) \
                    if np.any(seg_arr >= ss - 0.05 * (ss - base)) else float("nan")
            else:
                extreme = float(seg_arr.min())
                over = ss - extreme
                under = float("nan")
            step = ss - base
            k63 = first_index(np.abs(arr - base) >= 0.632 * abs(step), win[0]) if abs(step) > 1 else None
            out[c] = {"steady": ss, "step": float(step), "extreme_in_2s": extreme,
                      "overshoot_bar": float(over),
                      "overshoot_pct_of_step": float(100 * over / abs(step)) if abs(step) > 1 else None,
                      "t63_from_pressure_change_s": float(t[k63] - t[i_p]) if (k63 is not None and i_p is not None) else None,
                      "undershoot_after_reaching_bar": under}
    return out


def transition_stop(df: pd.DataFrame, seg: dict, nxt: dict | None, v_ss: float) -> dict:
    """End-of-stroke stall: pressure rise to the relief level."""
    t, x, p1, p2 = (df[c].values for c in ("t", "x", "p1", "p2"))
    i_e = seg["i1"]
    dirn = seg["dir"]
    pc = p1 if dirn == "extend" else p2  # pressurised side at the stall
    po = p2 if dirn == "extend" else p1
    t_end_seg = nxt["t1"] if nxt is not None else t[-1]
    w = np.where((t >= t[i_e] - 3.0) & (t <= min(t[i_e] + 6.0, t_end_seg)))[0]
    tw, pw = t[w], pc[w]
    settled_mask = (tw >= t[i_e] + 2.0) & (tw <= t[i_e] + 4.0)
    p_settled = float(np.median(pw[settled_mask])) if settled_mask.any() else float("nan")
    # start of the steep rise: last sample before stall where pc is within 3 bar of its moving level
    moving_level = float(np.median(pc[(t >= t[i_e] - 3.0) & (t <= t[i_e] - 1.0)]))
    k_hi = int(np.argmax(pw))
    p_peak = float(pw[k_hi])
    rise = p_settled - moving_level
    k10 = int(np.argmax(pw >= moving_level + 0.1 * rise))
    k90 = int(np.argmax(pw >= moving_level + 0.9 * rise))
    # steepest slope over 3 consecutive samples between 15 % and 85 % of the rise
    sl = []
    for k in range(len(pw) - 2):
        if moving_level + 0.15 * rise <= pw[k] and pw[k + 2] <= moving_level + 0.85 * rise:
            sl.append((pw[k + 2] - pw[k]) / (tw[k + 2] - tw[k]))
    slope = float(max(sl)) if sl else float("nan")
    # fit over the 15..85 % band
    band = (pw >= moving_level + 0.15 * rise) & (pw <= moving_level + 0.85 * rise)
    fit_slope = float(np.polyfit(tw[band], pw[band], 1)[0]) if band.sum() >= 2 else float("nan")
    x_stop_idx = first_index(np.abs(x - x[i_e + 3 if i_e + 3 < len(x) else i_e]) < 0.5, i_e - 10)
    out = {"side": "head(p1)" if dirn == "extend" else "rod(p2)",
           "t_stall_motion_end": float(t[i_e]), "level_moving_bar": moving_level,
           "settled_2_4s_bar": p_settled, "peak_bar": p_peak,
           "overshoot_bar": float(p_peak - p_settled),
           "rise_10_90_s": float(tw[k90] - tw[k10]),
           "slope_max_3pt_bar_s": slope, "slope_fit_15_85_bar_s": fit_slope,
           "n_samples_in_15_85_band": int(band.sum()),
           "other_side_moving_bar": float(np.median(po[(t >= t[i_e] - 3.0) & (t <= t[i_e] - 1.0)])),
           "other_side_peak_before_stall_bar": float(np.max(po[(t >= t[i_e] - 1.5) & (t <= t[i_e] + 0.3)])),
           "v_before_stall_mm_s": float(v_ss)}
    if x_stop_idx is not None:
        out["t_x_stop"] = float(t[x_stop_idx])
    # lumped stiffness of the pressurised volume: dp/dt = beta * v / L_eff (A cancels)
    for key, s_ in (("max3pt", slope), ("fit", fit_slope)):
        if np.isfinite(s_) and abs(v_ss) > 0:
            beta_over_L = s_ * BAR / (abs(v_ss) * 1e-3)  # Pa/m
            out[f"beta_over_Leff_Pa_per_m_{key}"] = float(beta_over_L)
            if dirn == "extend":
                l_eff = STROKE_MEAS_MM[0] * 1e-3 + L0_DEAD_M
                out[f"beta_eff_GPa_if_chamber_only_{key}"] = float(beta_over_L * l_eff / 1e9)
                out["L_eff_chamber_only_m"] = l_eff
    return out


STROKE_MEAS_MM = [695.0]  # replaced at run time by the measured full stroke


def stick_slip(df: pd.DataFrame, seg: dict, t_max: float) -> dict:
    """Stick-slip events in a motion segment: runs of samples with dx < 0.3 mm followed by a lunge."""
    w = df.iloc[seg["i0"]:seg["i1"] + 1]
    w = w[w.t <= t_max]
    t, x, p1 = w.t.values, w.x.values, w.p1.values
    dx = np.diff(x)
    stuck = dx < 0.3
    events = []
    for a, b in runs(stuck):
        dur = t[b + 1] - t[a]
        if dur < 0.25:
            continue
        # lunge after the stick: samples until dx falls below 0.3 again
        k = b + 1
        x0 = x[b + 1]
        while k < len(dx) and dx[k] >= 0.3:
            k += 1
        events.append({"t_stick_start": float(t[a]), "stick_s": float(dur), "x_stick_mm": float(x0),
                       "slip_mm": float(x[k] - x0), "slip_s": float(t[k] - t[b + 1]),
                       "p1_raw_rise_during_stick": float(p1[a:b + 2].max() - p1[a]),
                       "gap_inside": bool(np.any(np.diff(t[a:k + 1]) > 0.5))})
    clean = [e for e in events if not e["gap_inside"]]
    starts = np.array([e["t_stick_start"] for e in events])
    return {"n_events": len(events), "events": events,
            "mean_period_s": float(np.mean(np.diff(starts))) if len(starts) > 2 else None,
            "median_stick_s": float(np.median([e["stick_s"] for e in clean])) if clean else None,
            "median_slip_mm": float(np.median([e["slip_mm"] for e in clean])) if clean else None,
            "median_p1_rise_bar": float(np.median([e["p1_raw_rise_during_stick"] for e in clean])) if clean else None,
            "last_event_x_mm": float(events[-1]["x_stick_mm"]) if events else None}


def leak_fit(df: pd.DataFrame, seg: dict) -> dict | None:
    """Locked leak-down at the retracted end after the valve is switched off."""
    t, p1, p2 = df.t.values, df.p1.values, df.p2.values
    a, b = seg["i0"], seg["i1"]
    t0 = t[a]
    base_mask = (t >= t0 + 1.5) & (t <= t0 + 3.0) & (np.arange(len(t)) <= b)
    if base_mask.sum() < 5:
        return None
    base = float(np.median(p1[base_mask]))
    sm = pd.Series(p1).rolling(5, center=True, min_periods=1).median().values
    idx = np.arange(a, b + 1)
    above = sm[idx] > base + 0.3
    # onset: last index from which p1 stays above base + 0.3 until the end of the segment
    if not above[-1]:
        return {"onset": None, "note": "no head-pressure rise in this segment"}
    k = len(above) - 1
    while k > 0 and above[k - 1]:
        k -= 1
    # back off to where the smoothed signal was still at the base level
    k_on = k
    while k_on > 0 and sm[idx[k_on]] > base + 0.05:
        k_on -= 1
    i_on = int(idx[k_on])
    out = {"t_onset": float(t[i_on]), "p1_base_raw": base, "t_end": float(t[b]),
           "duration_s": float(t[b] - t[i_on])}
    tt = t[i_on:b + 1] - t[i_on]
    out["p1_rise_bar"] = float(p1[b] - p1[i_on])
    out["p2_change_bar"] = float(p2[b] - p2[i_on])
    # the head rise is S-shaped (slow start ~2 s); fit the exponential tail from onset + 3 s
    i_fit = int(np.searchsorted(t, t[i_on] + 3.0))
    out["t_fit_start"] = float(t[i_fit]) if i_fit <= b else None
    i_on = min(i_fit, b)
    tt = t[i_on:b + 1] - t[i_on]
    if tt[-1] > 5.0:
        def expo(tau_t, p_inf, tau, p0):
            return p_inf - (p_inf - p0) * np.exp(-tau_t / tau)

        try:
            # allow a dead time: fit from the onset with a small delay parameter absorbed in p0
            popt, pcov = curve_fit(expo, tt, p1[i_on:b + 1], p0=[p1[b] + 2, 5.0, p1[i_on]], maxfev=20000)
            perr = np.sqrt(np.diag(pcov))
            out["p1_fit"] = {"p_inf_raw": float(popt[0]), "tau_s": float(popt[1]), "p0_raw": float(popt[2]),
                             "p_inf_sigma": float(perr[0]), "tau_sigma": float(perr[1]),
                             "rms_resid": float(np.std(p1[i_on:b + 1] - expo(tt, *popt)))}
            popt2, pcov2 = curve_fit(expo, tt, p2[i_on:b + 1], p0=[p2[b] - 2, 5.0, p2[i_on]], maxfev=20000)
            perr2 = np.sqrt(np.diag(pcov2))
            out["p2_fit"] = {"p_inf_raw": float(popt2[0]), "tau_s": float(popt2[1]), "p0_raw": float(popt2[2]),
                             "p_inf_sigma": float(perr2[0]), "tau_sigma": float(perr2[1]),
                             "rms_resid": float(np.std(p2[i_on:b + 1] - expo(tt, *popt2)))}
        except RuntimeError as exc:  # pragma: no cover - fit failure is reported, not raised
            out["fit_error"] = str(exc)
        # local ratio dp1/dp2 in 2 s blocks
        blocks = []
        tb = t[i_on]
        while tb + 2.0 <= t[b]:
            m0 = np.argmin(np.abs(t - tb))
            m1 = np.argmin(np.abs(t - (tb + 2.0)))
            d1 = p1[m1] - p1[m0]
            d2 = p2[m1] - p2[m0]
            blocks.append({"t": float(tb), "dp1": float(d1), "dp2": float(d2),
                           "ratio_dp1_dp2": float(d1 / d2) if abs(d2) > 0.05 else None})
            tb += 2.0
        out["blocks_2s"] = blocks
    return out


# ----------------------------------------------------------------------------- plotting
COL_H = "#1f5fa8"   # head / p1
COL_R = "#c0392b"   # rod / p2
COL_X = "#2c3e50"
SHADE = {"extend": "#d6eaf8", "retract": "#fadbd8", "ext_end": "#e8e8e8", "ret_end": "#e8e8e8",
         "rest": "#ffffff", "extend_jump": "#f9e79f", "retract_jump": "#f9e79f"}


def shade(ax, segs):
    for s in segs:
        ax.axvspan(s["t0"], s["t1"], color=SHADE.get(s["label"], "#ffffff"), lw=0, zorder=0)


def fig_overview(df, segs, off1, off2, path):
    fig, axs = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    ax = axs[0]
    shade(ax, segs)
    ax.plot(df.t, df.p1 - off1, color=COL_H, lw=1.0, label="p1 = head (offset corrected)")
    ax.plot(df.t, df.p2 - off2, color=COL_R, lw=1.0, label="p2 = rod (offset corrected)")
    ax.set_ylabel("pressure [bar g]")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    for s in segs:
        if s["kind"] == "move" or s["t1"] - s["t0"] > 4:
            ax.text(0.5 * (s["t0"] + s["t1"]), 205, s["name"], ha="center", va="bottom", fontsize=6.5,
                    rotation=90)
    ax.set_ylim(-10, 240)
    ax = axs[1]
    shade(ax, segs)
    ax.plot(df.t, df.x, color=COL_X, lw=1.0)
    ax.set_ylabel("length_mm (stroke) [mm]")
    ax.grid(alpha=0.3)
    ax = axs[2]
    shade(ax, segs)
    ax.plot(df.t, df.v, color=COL_X, lw=1.0, label="v (local fit ±0.5 s)")
    for k in (1, -1):
        ax.axhline(k * V_MAX_SPEC_MM_S, color="#7f8c8d", ls="--", lw=0.8)
    ax.text(df.t.iloc[0] + 1, V_MAX_SPEC_MM_S + 1, "±v_max 22.67 mm/s (spec)", fontsize=7, color="#7f8c8d")
    ax.set_ylim(-60, 60)
    ax.set_ylabel("velocity [mm/s]")
    ax.set_xlabel("elapsed time [s]")
    ax.grid(alpha=0.3)
    ax.text(df.t.iloc[0] + 1, -55, "start jump before E1 (peak > 200 mm/s) clipped", fontsize=7)
    fig.suptitle("Outrigger unit test, pad unloaded (power pack direct, on/off valve) - overview")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_phase_plane(df, segs, off1, off2, a_p, phi_bounds, path):
    fig, ax = plt.subplots(figsize=(8, 6.5))
    styles = {"extend": ("o", COL_H), "retract": ("s", COL_R)}
    for s in segs:
        if s["kind"] != "move" or s["label"] not in styles:
            continue
        w = df.iloc[s["i0"]:s["i1"] + 1]
        w = w[(w.x > 20) & (w.x < 692)]
        mk, col = styles[s["label"]]
        ax.scatter(w.p1 - off1, w.p2 - off2, s=7, marker=mk, alpha=0.5,
                   color=col if s["name"] in ("E2", "R1") else None, label=s["name"])
    ph = np.linspace(-2, 60, 50)
    wb = W_ROD_N / a_p / BAR
    for phi, ls, lab in ((CYLINDERS["front"]["phi"], "-", f"front drawing phi {CYLINDERS['front']['phi']:.2f}, F_s=0"),
                         (CYLINDERS["rear"]["phi"], "-.", f"rear drawing phi {CYLINDERS['rear']['phi']:.2f}, F_s=0"),
                         (PHI_OLD, ":", f"superseded REXOME33 phi {PHI_OLD:.2f}, F_s=0")):
        ax.plot(ph, phi * (ph + wb), color="k", ls=ls, lw=1, label=lab)
    for phi in phi_bounds:
        ax.plot(ph, phi * (ph + wb), color="#7f8c8d", ls="--", lw=0.8)
    ax.text(2, 215, f"dashed: phi band {phi_bounds[0]:.2f}..{phi_bounds[1]:.2f} from F_s >= 0 "
            "(W = 1.047 kN, front A_p)", fontsize=7, color="#7f8c8d")
    ax.set_xlim(-3, 60)
    ax.set_ylim(-5, 230)
    ax.set_xlabel("p1 head [bar g]")
    ax.set_ylabel("p2 rod [bar g]")
    ax.set_title("Head vs rod pressure while moving (x 20..692 mm).\n"
                 "Line p_r = phi (p_h + W/A_p): zero friction; extend lies below, retract above")
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_transitions(df, windows, off1, off2, path):
    n = len(windows)
    fig, axs = plt.subplots(n, 1, figsize=(11, 2.4 * n))
    for ax, (title, a, b) in zip(np.atleast_1d(axs), windows):
        w = df[(df.t >= a) & (df.t <= b)]
        ax.plot(w.t, w.p1 - off1, "o-", ms=2.5, lw=0.9, color=COL_H, label="p1 head")
        ax.plot(w.t, w.p2 - off2, "s-", ms=2.5, lw=0.9, color=COL_R, label="p2 rod")
        ax.set_ylabel("bar g")
        ax.grid(alpha=0.3)
        ax2 = ax.twinx()
        ax2.plot(w.t, w.x, "^-", ms=2.5, lw=0.8, color=COL_X, label="x")
        ax2.set_ylabel("x [mm]")
        ax.set_title(title, fontsize=9)
        if ax is np.atleast_1d(axs)[0]:
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="center left")
    np.atleast_1d(axs)[-1].set_xlabel("elapsed time [s] (markers = samples, ~10 Hz)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_sensor(df, rest, path, off1, off2):
    s = df[(df.t >= rest["t0"]) & (df.t <= rest["t1"])]
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, c, col, lab in ((axs[0], "p1", COL_H, "p1 raw [bar]"), (axs[1], "p2", COL_R, "p2 raw [bar]"),
                            (axs[2], "x", COL_X, "length raw [mm]")):
        vals = s[c].values
        q = 0.025 if c != "x" else 0.04375
        bins = np.arange(vals.min() - q / 2, vals.max() + q, q)
        ax.hist(vals, bins=bins, color=col, alpha=0.8)
        ax.set_xlabel(lab)
        ax.set_title(f"mean {vals.mean():.3f}, sigma {vals.std(ddof=1):.3f}", fontsize=9)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("count")
    fig.suptitle(f"Rest at x = 5.8 mm, t {rest['t0']:.1f}-{rest['t1']:.1f} s (both chambers at 0 bar g assumed)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_friction(phis, table, path):
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(phis, [r["F_s_roundtrip_kN"] for r in table], color=COL_X, label="F_s = (F_ext - F_ret)/2 (E2 vs R1+R2)")
    ax.plot(phis, [r["W_est_kN"] for r in table], color="#27ae60", label="W_est = -(F_ext + F_ret)/2")
    ax.plot(phis, [r["F_s_E2_with_W_kN"] for r in table], color=COL_H, ls="--", lw=0.9,
            label="F_s extend only (W = 1.047 kN)")
    ax.plot(phis, [r["F_s_R_with_W_kN"] for r in table], color=COL_R, ls="--", lw=0.9,
            label="F_s retract only (W = 1.047 kN)")
    ax.axhline(W_ROD_N / 1e3, color="#27ae60", ls=":", lw=1, label="m_rod g = 1.047 kN (REXOME33 CAD)")
    ax.axhline(0, color="k", lw=0.6)
    for k, ls in (("front", "-"), ("rear", "-.")):
        ax.axvline(CYLINDERS[k]["phi"], color="#7f8c8d", ls=ls, lw=0.8)
        ax.text(CYLINDERS[k]["phi"] + 0.01, -4.5, k, fontsize=7, color="#7f8c8d")
    ax.set_ylim(-5, 9)
    ax.set_xlabel("area ratio phi = A_p / A_ann (A_p = front drawing, bore 130 mm)")
    ax.set_ylabel("kN")
    ax.set_title("Seal friction and weight from the airborne round trip vs assumed phi")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    df = load(args.csv)
    df["v"] = local_velocity(df.t.values, df.x.values, V_HALF_WINDOW_S)
    res: dict = {"input_csv": str(args.csv), "seed": SEED,
                 "conventions": {"p1": "head (inferred)", "p2": "rod (inferred)",
                                 "x": "stroke from fully retracted (inferred)",
                                 "pressure": "bar g after zero-offset correction unless *_raw"}}
    res["sampling"] = sampling_stats(df)
    res["quantum"] = {c: quantum(df[c].values) for c in ("p1", "p2", "x")}

    segs = segment(df)
    res["segments"] = [{k: v for k, v in s.items()} for s in segs]

    # ---- sensor characteristics at rest (first stationary segment)
    rest = next(s for s in segs if s["label"] == "rest")
    rest_stats = stationary_stats(df, rest["i0"], rest["i1"])
    off1 = rest_stats["p1"]["mean"]
    off2 = rest_stats["p2"]["mean"]
    res["sensor_rest"] = rest_stats
    res["offset_bar"] = {"p1": off1, "p2": off2}
    # noise in other stationary states
    other = {}
    for s in segs:
        if s["kind"] == "still" and s["t1"] - s["t0"] > 2.0:
            a = int(np.searchsorted(df.t.values, s["t0"] + 1.5))
            b = s["i1"]
            if b - a > 10:
                other[s["name"]] = stationary_stats(df, a, b)
    res["sensor_stationary_states"] = other
    # full stroke
    ext_ends = [s for s in segs if s["label"] == "ext_end"]
    ret_ends = [s for s in segs if s["label"] == "ret_end"]
    x_full = float(np.median(np.concatenate([df.x.values[s["i0"]:s["i1"] + 1] for s in ext_ends])))
    x_zero = float(np.median(np.concatenate([df.x.values[s["i0"]:s["i1"] + 1] for s in ret_ends])))
    STROKE_MEAS_MM[0] = x_full - x_zero
    res["stroke"] = {"x_at_full_extension_mm": x_full, "x_at_full_retraction_mm": x_zero,
                     "stroke_measured_mm": x_full - x_zero, "stroke_spec_mm": STROKE_SPEC_MM,
                     "ratio": (x_full - x_zero) / STROKE_SPEC_MM}

    # ---- motion phases
    phases = {}
    for s in segs:
        if s["kind"] != "move":
            continue
        w = df.iloc[s["i0"]:s["i1"] + 1]
        st = steady_window(df, s)
        info = {"t0": s["t0"], "t1": s["t1"], "x0": s["x0"], "x1": s["x1"],
                "duration_s": s["t1"] - s["t0"], "v_peak_mm_s": s["v_peak_mm_s"]}
        if len(st) > 5:
            vfit = np.polyfit(st.t, st.x, 1)[0]
            info.update({
                "steady_n": int(len(st)), "steady_t": [float(st.t.iloc[0]), float(st.t.iloc[-1])],
                "v_mean_mm_s": float(vfit), "v_local_std_mm_s": float(st.v.std(ddof=1)),
                "v_over_vmax": float(abs(vfit) / V_MAX_SPEC_MM_S),
                "p_h_mean": float((st.p1 - off1).mean()), "p_h_std": float(st.p1.std(ddof=1)),
                "p_h_range": [float((st.p1 - off1).min()), float((st.p1 - off1).max())],
                "p_r_mean": float((st.p2 - off2).mean()), "p_r_std": float(st.p2.std(ddof=1)),
                "p_r_range": [float((st.p2 - off2).min()), float((st.p2 - off2).max())],
                "F_cyl_kN": {k: float(forces((st.p1 - off1).values, (st.p2 - off2).values,
                                             c["phi"], c["A_p"]).mean() / 1e3)
                             for k, c in CYLINDERS.items()},
                "F_cyl_superseded_phi11p76_Ap_front_kN": float(forces((st.p1 - off1).values,
                                                                      (st.p2 - off2).values, PHI_OLD).mean() / 1e3),
                "Q_head_L_min": {k: float(c["A_p"] * abs(vfit) * 1e-3 * 6e4) for k, c in CYLINDERS.items()},
                "Q_rod_L_min": {k: float(c["A_ann"] * abs(vfit) * 1e-3 * 6e4) for k, c in CYLINDERS.items()},
            })
        # full-phase pressure range (incl. cushion), x > 20 mm
        ww = w[(w.x > 20) & (w.x < 693)]
        if len(ww):
            info["full_p_h_range"] = [float((ww.p1 - off1).min()), float((ww.p1 - off1).max())]
            info["full_p_r_range"] = [float((ww.p2 - off2).min()), float((ww.p2 - off2).max())]
        phases[s["name"]] = info
    res["phases"] = phases

    # ---- area ratio phi
    ph = {}
    e2 = next(s for s in segs if s["name"] == "E2")
    e1 = next(s for s in segs if s["name"] == "E1")
    rr = [s for s in segs if s["label"] == "retract"]
    st_e2 = steady_window(df, e2)
    st_e1 = steady_window(df, e1)
    st_r = pd.concat([steady_window(df, s) for s in rr])
    # M1: slope of p_r vs p_h inside a phase (friction and weight assumed constant)
    ph["M1_slope_E2_steady"] = ols((st_e2.p1 - off1).values, (st_e2.p2 - off2).values, rng)
    ph["M1_slope_E1_steady"] = ols((st_e1.p1 - off1).values, (st_e1.p2 - off2).values, rng)
    for s in (e1, e2):
        w = df.iloc[s["i0"]:s["i1"] + 1]
        w = w[(w.x > 660) & (w.x < 693.5)]
        if len(w) > 4:
            ph[f"M1_slope_{s['name']}_end_cushion_x660_693"] = ols((w.p1 - off1).values, (w.p2 - off2).values, rng)
    ph["M1_slope_R_steady"] = ols((st_r.p1 - off1).values, (st_r.p2 - off2).values, rng)
    # M2: self-calibration with the rod weight W (symmetric friction):
    #     -(F_E + F_R)/2 = W  ->  phi = (p_rE + p_rR) / (p_hE + p_hR + 2 W / A_p)
    phE = float((st_e2.p1 - off1).mean())
    prE = float((st_e2.p2 - off2).mean())
    phR = float((st_r.p1 - off1).mean())
    prR = float((st_r.p2 - off2).mean())
    st_e = pd.concat([st_e1, st_e2])
    ph["means_for_M2"] = {"p_h_E2": phE, "p_r_E2": prE, "p_h_R": phR, "p_r_R": prR}
    ph["M2_weight_selfcal"] = {}
    ph["M3_bounds_Fs_nonneg"] = {}
    for k, c in CYLINDERS.items():
        wb = W_ROD_N / c["A_p"] / BAR
        ph["M2_weight_selfcal"][k] = {
            "W_over_Ap_bar": wb, "phi": (prE + prR) / (phE + phR + 2 * wb),
            "phi_if_W_zero": (prE + prR) / (phE + phR),
            "phi_if_W_doubled": (prE + prR) / (phE + phR + 4 * wb),
            "phi_if_rod_up": (prE + prR) / (phE + phR - 2 * wb)}
        # M3: bounds from F_s >= 0 sample by sample (extension below the line, retraction above)
        re_ = (st_e.p2 - off2).values / ((st_e.p1 - off1).values + wb)
        rr_ = (st_r.p2 - off2).values / ((st_r.p1 - off1).values + wb)
        lo = float(np.percentile(re_, 99))
        hi = float(np.percentile(rr_, 1))
        ph["M3_bounds_Fs_nonneg"][k] = {"phi_min_from_E_p99": lo, "phi_min_from_E_max": float(re_.max()),
                                        "phi_max_from_R_p01": hi, "phi_max_from_R_min": float(rr_.min()),
                                        "drawing_phi": c["phi"],
                                        "drawing_phi_inside": bool(lo <= c["phi"] <= hi)}
    # M5: flow continuity, fixed pump flow: A_ann v_R <= A_p v_E  ->  phi >= v_R / v_E
    vE = phases["E2"]["v_mean_mm_s"]
    vR = np.mean([abs(phases[s["name"]]["v_mean_mm_s"]) for s in rr])
    ph["M5_flow_bound"] = {"phi_min": float(vR / vE), "v_E2_mm_s": vE, "v_R_mean_mm_s": float(vR),
                           "note": "valid if the pump flow is the same and fully used in extension"}
    res["phi"] = ph

    def fs_at(phi: float, a_p: float) -> dict:
        fE = forces((st_e2.p1 - off1).values, (st_e2.p2 - off2).values, phi, a_p).mean()
        fR = forces((st_r.p1 - off1).values, (st_r.p2 - off2).values, phi, a_p).mean()
        fE1 = forces((st_e1.p1 - off1).values, (st_e1.p2 - off2).values, phi, a_p).mean()
        return {"phi": float(phi), "A_p_m2": a_p, "F_ext_E2_kN": fE / 1e3, "F_ret_R_kN": fR / 1e3,
                "F_s_roundtrip_kN": (fE - fR) / 2e3, "W_est_kN": -(fE + fR) / 2e3,
                "F_s_E2_with_W_kN": (fE + W_ROD_N) / 1e3, "F_s_R_with_W_kN": (-fR - W_ROD_N) / 1e3,
                "F_s_E1_lowp_with_W_kN": (fE1 + W_ROD_N) / 1e3,
                "F_s_E1_lowp_with_West_kN": (fE1 - (fE + fR) / 2) / 1e3}

    # friction / weight for the two drawing cases (primary: the case consistent with the data)
    cases = {k: fs_at(c["phi"], c["A_p"]) for k, c in CYLINDERS.items()}
    cases["superseded_rexome33"] = fs_at(PHI_OLD, math.pi / 4 * 0.115**2)
    for k in CYLINDERS:
        m3 = ph["M3_bounds_Fs_nonneg"][k]
        cases[k]["phi_band"] = [m3["phi_min_from_E_p99"], m3["phi_max_from_R_p01"]]
        cases[k]["at_phi_band_lo"] = fs_at(m3["phi_min_from_E_p99"], CYLINDERS[k]["A_p"])
        cases[k]["at_phi_band_hi"] = fs_at(m3["phi_max_from_R_p01"], CYLINDERS[k]["A_p"])
        cases[k]["at_phi_M2"] = fs_at(ph["M2_weight_selfcal"][k]["phi"], CYLINDERS[k]["A_p"])
    res["friction_cases"] = cases
    primary = "front" if ph["M3_bounds_Fs_nonneg"]["front"]["drawing_phi_inside"] else "rear"
    res["cylinder_judgement"] = {"primary": primary,
                                 "front_inside_band": ph["M3_bounds_Fs_nonneg"]["front"]["drawing_phi_inside"],
                                 "rear_inside_band": ph["M3_bounds_Fs_nonneg"]["rear"]["drawing_phi_inside"]}
    A_p_best = CYLINDERS[primary]["A_p"]
    phi_best = CYLINDERS[primary]["phi"]
    phi_lo = ph["M3_bounds_Fs_nonneg"][primary]["phi_min_from_E_p99"]
    phi_hi = ph["M3_bounds_Fs_nonneg"][primary]["phi_max_from_R_p01"]
    phis = np.round(np.arange(2.9, 4.01, 0.05), 3)
    table = [fs_at(float(p), A_p_best) for p in phis]
    res["friction_vs_phi_primary_Ap"] = table
    nE, nR = len(st_e2), len(st_r)
    sp = rest_stats["p1"]["std"]
    res["friction_cases"]["F_s_noise_sigma_kN"] = float(
        0.5 * A_p_best * BAR * sp * math.sqrt(1 / nE + 1 / nR) * math.sqrt(1 + 1 / phi_best**2) / 1e3)
    fE_s = forces((st_e2.p1 - off1).values, (st_e2.p2 - off2).values, phi_best, A_p_best) + W_ROD_N
    res["friction_cases"]["E2_Fs_vs_v_corr"] = float(np.corrcoef(st_e2.v.values, fE_s)[0, 1])
    res["friction_cases"]["E2_Fs_vs_x_slope_kN_per_100mm"] = float(
        np.polyfit(st_e2.x.values, fE_s, 1)[0] * 100 / 1e3)
    res["friction_cases"]["E2_Fs_std_kN"] = float(np.std(fE_s) / 1e3)
    fR_s = -forces((st_r.p1 - off1).values, (st_r.p2 - off2).values, phi_best, A_p_best) - W_ROD_N
    res["friction_cases"]["R_Fs_std_kN"] = float(np.std(fR_s) / 1e3)

    # ---- transitions
    tr = {}
    for k, s in enumerate(segs):
        if s["kind"] != "move" or s["label"] not in ("extend", "retract"):
            continue
        v_ss = phases[s["name"]].get("v_mean_mm_s", np.nan)
        tr[s["name"] + "_start"] = transition_start(df, s, v_ss)
        nxt = segs[k + 1] if k + 1 < len(segs) else None
        if nxt is not None and nxt["label"] in ("ext_end", "ret_end"):
            tr[s["name"] + "_stop"] = transition_stop(df, s, nxt, v_ss)
    # pilot-check unlocking at retraction start: rod pressure when the head starts to fall
    unlock = []
    for s in rr:
        t, p1, p2 = df.t.values, df.p1.values - off1, df.p2.values - off2
        a = int(np.searchsorted(t, s["t0"] - 3.0))
        b = s["i0"] + 5
        h0 = float(np.median(p1[a:a + 8]))
        k = first_index(p1 < h0 - 3.0, a)
        if k is not None and k <= b:
            unlock.append({"segment": s["name"], "t_head_release": float(t[k]),
                           "p_h_before": h0, "p_r_last_before_release": float(p2[k - 1]),
                           "p_r_at_release_sample": float(p2[k]),
                           "psi_estimate_range": [h0 / max(p2[k], 1e-3), h0 / max(p2[k - 1], 1e-3)],
                           "t_rod_rise_start": tr[s["name"] + "_start"]["t_pressure_change"]})
    res["poc_unlock_at_retract_start"] = unlock
    res["transitions"] = tr

    # ---- relief level
    rel = {"head_stall_settled_raw": [], "rod_stall_settled_raw": [], "rod_stall_peak_raw": []}
    for name, d in tr.items():
        if name.endswith("_stop"):
            if d["side"].startswith("head"):
                rel["head_stall_settled_raw"].append(d["settled_2_4s_bar"])
            else:
                rel["rod_stall_settled_raw"].append(d["settled_2_4s_bar"])
                rel["rod_stall_peak_raw"].append(d["peak_bar"])
    rel["head_relief_gauge_bar"] = float(np.mean(rel["head_stall_settled_raw"]) - off1)
    rel["rod_relief_gauge_bar"] = float(np.mean(rel["rod_stall_settled_raw"]) - off2)
    res["relief"] = rel

    # ---- locked leak-down
    leaks = {}
    for s in ret_ends:
        lf = leak_fit(df, s)
        if lf is not None:
            if "p1_fit" in lf:
                p1i = lf["p1_fit"]["p_inf_raw"] - off1
                p2i = lf["p2_fit"]["p_inf_raw"] - off2
                lf["asymptote_gauge"] = {"p_h": p1i, "p_r": p2i, "ratio_pr_ph": p2i / p1i,
                                         "phi_lower_bound_if_floating": p2i / (p1i + W_ROD_N / A_p_best / BAR)}
            leaks[s["name"]] = lf
    res["locked_leak"] = leaks
    last = df.iloc[-5:]
    res["last_rows"] = {"p1_raw": float(last.p1.mean()), "p2_raw": float(last.p2.mean()),
                        "p_h": float(last.p1.mean() - off1), "p_r": float(last.p2.mean() - off2),
                        "x": float(last.x.mean())}

    # ---- stick-slip in the low-pressure extension E1
    res["stick_slip_E1"] = stick_slip(df, e1, t_max=e1["t0"] + 20.0)

    # ---- length sensor vs datasheet (GEFRAN WRP-A, analog, 16 bit, noise < 5 mVpp on 10 V)
    fs_mm = 700.0  # inferred model: next catalogue stroke >= measured 694.8 mm; quantum 700/16000
    q = res["quantum"]["x"]["quantum"]
    res["length_sensor"] = {
        "FS_model_mm_inferred": fs_mm, "quantum_mm": q, "FS_over_quantum_counts": fs_mm / q,
        "datasheet_16bit_step_mm": fs_mm / 65536,
        "datasheet_noise_pp_mm": 5e-3 / 10.0 * fs_mm,
        "datasheet_noise_sigma_mm_pp_over_6": 5e-3 / 10.0 * fs_mm / 6,
        "quantisation_sigma_mm": q / math.sqrt(12),
        "rest_sigma_mm": rest_stats["x"]["std"],
        "rest_sigma_white_mm": rest_stats["x"]["std_diff_over_sqrt2"],
        "analog_sigma_excl_quantisation_mm": math.sqrt(max(0.0, rest_stats["x"]["std"]**2 - q**2 / 12)),
        "linearity_mm": max(0.0002 * fs_mm, 0.060),
        "temp_coeff_mm_per_K": 0.0001 * fs_mm,
        "pressure_quantum_bar": res["quantum"]["p1"]["quantum"],
        "pressure_FS_if_16000_counts_bar": res["quantum"]["p1"]["quantum"] * 16000,
    }

    # ---- E1 start jump
    jumps = [s for s in segs if s["label"].endswith("_jump")]
    res["jumps"] = []
    for s in jumps:
        w = df.iloc[max(0, s["i0"] - 5):s["i1"] + 6]
        res["jumps"].append({"name": s["name"], "t0": s["t0"], "t1": s["t1"], "x0": s["x0"], "x1": s["x1"],
                             "v_peak_mm_s": s["v_peak_mm_s"],
                             "v_peak_raw_diff_mm_s": float(np.max(np.diff(w.x.values) / np.diff(w.t.values))),
                             "p_h_range": [float((w.p1 - off1).min()), float((w.p1 - off1).max())],
                             "p_r_range": [float((w.p2 - off2).min()), float((w.p2 - off2).max())],
                             "head_volume_L_if_CAD_bore": float(A_P_F * (s["x1"] - s["x0"]) * 1e-3 * 1e3)})

    # ---- figures
    fig_overview(df, segs, off1, off2, args.out / "unit_noload_overview.png")
    fig_phase_plane(df, segs, off1, off2, A_p_best, (phi_lo, phi_hi), args.out / "unit_noload_ph_pr_plane.png")
    windows = [("before E1: start jump 6 -> 84 mm", 501.0, 506.0),
               ("E1 low-pressure extension: stick-slip", 506.0, 516.0),
               ("E1 end: rod-end cushion, head stall to relief", 533.0, 539.0),
               ("R1 start: head held until rod pressure ~46 bar (POC-A pilot)", 546.5, 549.5),
               ("R1 end: rod stall to relief", 562.5, 566.5),
               ("H2 valve off -> E2 start (POC-B pilot from head)", 568.5, 573.0),
               ("E2 end: cushion (rod 190 bar) and head stall", 603.5, 607.5),
               ("R2 end / valve off / locked leak-down", 631.5, 656.5)]
    fig_transitions(df, windows, off1, off2, args.out / "unit_noload_transitions.png")
    fig_sensor(df, rest, args.out / "unit_noload_sensor_rest.png", off1, off2)
    fig_friction([r["phi"] for r in table], table, args.out / "unit_noload_friction_vs_phi.png")

    with open(args.out / "unit_noload_analysis.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)

    # ---- console summary
    print("segments:")
    for s in segs:
        print(f"  {s['name']:14s} {s['t0']:8.2f}-{s['t1']:8.2f}  x {s['x0']:7.2f}->{s['x1']:7.2f}")
    print("offset", off1, off2)
    print(json.dumps({k: res[k] for k in ("stick_slip_E1", "length_sensor")}, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("sampling", "quantum", "stroke", "phases", "phi",
                                          "friction_cases", "cylinder_judgement", "relief", "poc_unlock_at_retract_start",
                                          "last_rows", "jumps")}, indent=1, default=float))
    print(json.dumps(res["transitions"], indent=1, default=float))
    print(json.dumps(res["locked_leak"], indent=1, default=float))
    print(json.dumps({k: {c: {kk: round(vv, 4) for kk, vv in d[c].items()} for c in ("p1", "p2", "x")}
                      for k, d in {"rest": rest_stats, **other}.items()}, indent=1))
    print("friction table (phi, F_s, W_est, Fs_E2, Fs_R, Fs_E1):")
    for r in table:
        print(f"  {r['phi']:6.2f} {r['F_s_roundtrip_kN']:7.3f} {r['W_est_kN']:7.3f} {r['F_s_E2_with_W_kN']:7.3f}"
              f" {r['F_s_R_with_W_kN']:7.3f} {r['F_s_E1_lowp_with_W_kN']:7.3f}")


if __name__ == "__main__":
    main()
