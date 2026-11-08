"""Open-loop SCM lift: VB / V0 / v4-stored three-way comparison (paper v5 2.8, v4 2.7 table 7).

Reads result.json + series.npz (+ flow_series.npz) of each run; recomputes the v4 table 7 items from the
series with one definition for all runs, and compares with the stored p3a block.
Output: JSON to argv[1].
"""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {
    ("J1", "VB"): R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_J1_B_VB",
    ("J1", "V0"): R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
    ("J1", "v4"): R / "batch_P3a_20261026_092653/P3a_J1_B",
    ("G1", "VB"): R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_G1_B_VB",
    ("G1", "V0"): R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_G1_B_V0",
    ("G1", "v4"): R / "batch_P3a_20261026_092653/P3a_G1_B",
}
BATCH = {"VB": R / "batch_V5-OPENLOOP-VB_20261108_112044/batch.json",
         "V0": R / "batch_V5-OPENLOOP-V0_20261108_123517/batch.json",
         "v4": R / "batch_P3a_20261026_092653/batch.json"}
F_MIN = 9414.58911
T_LIFT = 8.0
# pad bottom centres (YAML legs.*.pad_bottom_center_retracted_m), x, y [m]
PAD_XY = np.array([[2.2938, 1.3238], [2.2938, -1.3238], [-2.556, 1.1679], [-2.556, -1.2429]])


def first_run(t, mask, hold):
    """First index k where mask stays true for hold seconds."""
    n = len(t)
    k = 0
    while k < n:
        if mask[k]:
            j = k
            while j < n and mask[j]:
                j += 1
            if t[j - 1] - t[k] >= hold - 1e-9:
                return k
            k = j
        else:
            k += 1
    return None


def plane_fit(h):
    """Fit z = a + b x + c y over 4 pads; return roll, pitch [deg] (roll>0 left up, pitch>0 nose down)."""
    A = np.c_[np.ones(4), PAD_XY]
    coef, *_ = np.linalg.lstsq(A, h.T, rcond=None)
    b, c = coef[1], coef[2]
    roll = np.degrees(np.arctan(c))  # left (y+) higher -> roll +
    pitch = np.degrees(np.arctan(-b))  # front lower (b>0 means front higher) -> pitch +
    return roll, pitch


def analyse(path):
    res = json.loads((path / "result.json").read_text("utf-8"))
    z = np.load(path / "series.npz")
    t = z["t_s"]
    fc = z["F_cyl_N"]
    sink = z["pad_sinkage_geometric_m"]
    rp = z["roll_pitch_deg"]
    sm = z["s_motor_m"]
    cr = z["scm_crawler_normal_N"]
    W = res["p3a"]["weight_N"]
    lift = t > T_LIFT + 1e-9
    i0 = int(np.argmax(lift)) - 1
    k = first_run(t[lift], cr[lift] < 0.01 * W, 0.1)
    klo = int(np.nonzero(lift)[0][k])
    tlo = float(t[klo])
    # before lift-off min F_cyl (from first > 1.4 F_min to departure), per leg
    pre = []
    for i in range(4):
        idx = np.nonzero(lift & (fc[:, i] > 1.4 * F_MIN))[0]
        if not idx.size or idx[0] >= klo:
            pre.append(None)
            continue
        seg = fc[idx[0]:klo + 1, i]
        j = int(np.argmin(seg))
        pre.append({"F_min_N": float(seg[j]), "t_s": float(t[idx[0] + j])})
    # creep stop: all pads 1 s sinkage rate < 0.1 mm/s after departure
    dt = float(np.median(np.diff(t)))
    w = int(round(1.0 / dt))
    rate = np.full_like(sink, np.nan)
    rate[w:] = (sink[w:] - sink[:-w]) / 1.0
    after = t >= tlo
    ok = np.all(rate < 1e-4, axis=1) & after
    kc = np.nonzero(ok)[0]
    creep_first = float(t[kc[0]] - tlo) if kc.size else None
    # final: last time it becomes and stays true
    creep_final = None
    if kc.size and ok[-1]:
        j = len(ok) - 1
        while j > 0 and ok[j - 1]:
            j -= 1
        creep_final = float(t[j] - tlo)
    end_rate_mm_s = (rate[-1] * 1e3).tolist()
    # attitude
    ref = rp[i0]
    d_end = (rp[-1] - ref).tolist()
    d_lo = (rp[klo] - ref).tolist()
    # roll rate over last 1 s and last 3 s (deg/s)
    def slope(win):
        m = t >= t[-1] - win
        return np.polyfit(t[m], rp[m, 0], 1)[0], np.polyfit(t[m], rp[m, 1], 1)[0]
    rr1 = slope(1.0)
    rr3 = slope(3.0)
    # roll second derivative (quadratic fit over last 4 s) -> acceleration indicator
    m4 = t >= t[-1] - 4.0
    q = np.polyfit(t[m4] - t[-1], rp[m4, 0], 2)
    # geometric decomposition (support height h_i = s_motor_i - sink_i relative to settle)
    h_s = sm - sm[i0]
    h_k = -(sink - sink[i0])
    r_s, p_s = plane_fit((h_s[-1])[None, :])
    r_k, p_k = plane_fit((h_k[-1])[None, :])
    r_t, p_t = plane_fit((h_s[-1] + h_k[-1])[None, :])
    peaks = fc[lift].max(axis=0)
    lim = np.array(res["p3a"]["limits"]["F_extend_limit_N"])
    out = {
        "t_liftoff_s": tlo, "t_liftoff_after_start_s": tlo - T_LIFT,
        "s_motor_at_liftoff_mm": (sm[klo] * 1e3).tolist(),
        "pad_N_at_liftoff_kN": (z["scm_pad_normal_N"][klo] / 1e3).tolist(),
        "sink_at_liftoff_mm": (sink[klo] * 1e3).tolist(),
        "sink_end_mm": (sink[-1] * 1e3).tolist(),
        "creep_after_liftoff_mm": ((sink[-1] - sink[klo]) * 1e3).tolist(),
        "pre_liftoff_min_F_kN": [None if p is None else p["F_min_N"] / 1e3 for p in pre],
        "pre_liftoff_min_t_s": [None if p is None else p["t_s"] for p in pre],
        "creep_stop_first_s": creep_first, "creep_stop_final_s": creep_final,
        "sink_rate_end_mm_s": end_rate_mm_s,
        "d_roll_pitch_liftoff_deg": d_lo, "d_roll_pitch_end_deg": d_end,
        "roll_rate_last1s_deg_s": rr1[0], "roll_rate_last3s_deg_s": rr3[0],
        "pitch_rate_last1s_deg_s": rr1[1],
        "roll_quad_last4s": {"a2_deg_s2": q[0], "a1_deg_s": q[1]},
        "roll_pp_last1s_deg": float(np.ptp(rp[t >= t[-1] - 1.0, 0])),
        "decomp_end_deg": {"stroke_roll": float(r_s[0]), "stroke_pitch": float(p_s[0]),
                           "sink_roll": float(r_k[0]), "sink_pitch": float(p_k[0]),
                           "sum_roll": float(r_t[0]), "sum_pitch": float(p_t[0])},
        "s_motor_end_mm": (sm[-1] * 1e3).tolist(), "s_motor_max_mm": float(sm.max() * 1e3),
        "stroke_margin_mm": float((0.6848 - sm.max()) * 1e3),
        "F_peak_kN": (peaks / 1e3).tolist(), "F_peak_ratio_max": float((peaks / lim).max()),
        "F_end_kN": (fc[-1] / 1e3).tolist(),
        "pad_N_end_kN": (z["scm_pad_normal_N"][-1] / 1e3).tolist(),
        "stored_p3a_checks": res["p3a"]["checks"],
        "stored_liftoff_s": res["p3a"]["P3a-2_liftoff"]["t_liftoff_s"],
        "stored_before_liftoff": res["p3a"]["P3a-9_min_cylinder_force"].get("before_liftoff"),
        "stored_creep_stop": res["p3a"].get("creep_stop"),
        "us_per_step": res.get("us_per_step"), "wall_s": res.get("wall_s"),
    }
    fl = res.get("flow_limit")
    if fl:
        s = fl["summary"]
        out["flow"] = {"supply_L_min": fl["supply_L_min"], "short_s": s["short_s"], "limited_s": s["limited_s"],
                       "max_deficit_L_min": s["max_deficit_L_min"],
                       "deficit_integral_end_mm": s["deficit_integral_end_mm"],
                       "speed_ratio": s["speed_ratio"], "tracking": s["tracking"],
                       "limited_sets": s["limited_sets"],
                       "max_sum_Q_over_supply_minus_1": s["max_sum_Q_over_supply_minus_1"],
                       "audit_mismatches": s["steps"]["audit_mismatches"]}
    hr = res.get("hydraulics_record")
    if hr:
        out["m2"] = {"law": hr["m2_law"]["law"], "shift_total_mm": hr["m2_shift_total_mm"],
                     "clipped_steps": hr["m2_clipped_steps"], "clip_times_s": hr["m2_clip_times_s"],
                     "tension_truth": hr["tension_truth"], "extend_bound_check": hr["extend_bound_check"],
                     "n_releases": len(hr.get("m2_releases", []))}
        out["v5_controller_options"] = res["v5_hydraulics"]["controller_options"]
        out["v5_records"] = res["v5_hydraulics"]["records"]
    return out, z


def series_diff(za, zb):
    d = {}
    for k in za.files:
        if k in zb.files and za[k].shape == zb[k].shape and za[k].dtype.kind == "f":
            a, b = za[k], zb[k]
            d[k] = float(np.nanmax(np.abs(a - b))) if a.size else 0.0
            if not np.array_equal(a, b, equal_nan=True):
                d[k + "_identical"] = False
    return d


out = {"runs": {}, "rc": {}, "v0_vs_v4_series_maxabs": {}}
zs = {}
for key, p in RUNS.items():
    o, z = analyse(p)
    out["runs"][f"{key[0]}_{key[1]}"] = o
    zs[key] = z
for s, p in BATCH.items():
    b = json.loads(p.read_text("utf-8"))
    out["rc"][s] = {c["case"]: {"rc": c.get("rc"), "wall_s": c.get("wall_s")} for c in b["cases"]}
for soil in ("J1", "G1"):
    out["v0_vs_v4_series_maxabs"][soil] = series_diff(zs[(soil, "V0")], zs[(soil, "v4")])
# flow series columns for reference
fz = np.load(RUNS[("J1", "VB")] / "flow_series.npz")
out["flow_series_columns"] = [str(c) for c in fz["columns"]]
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
print("ok")
