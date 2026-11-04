"""Final verdict values of the coupled soil rows (criteria rev. 6, 7.1, 7.2, 7.3, 9.1): limit on vs stored off.

Reads the run folders only and never writes into them (run_S9.rejudge_case with write=False, same judge code on
both sides). Writes soil_tables.json next to this file. Limits come from the criteria.

Run: conda run -n dynamics-dev python -I judge_soil.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
S9 = ROOT / "07_results/S9"
ON = S9 / "batch_COUPLED_eta085_20261104_142213"
REP = S9 / "batch_FINAL-REP_20261030_223359"
REPX = S9 / "batch_FINAL-REP-X_20261031_020716"
CASES = {
    "S8": ("S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0", REP),
    "S6": ("P3b_J2_B_top_Fs4_m1p1_t180", REPX),
    "S1": ("P3b_J1_B_top_Fs4", REP),
}
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
V_MAX = 20.9243016e-3
F_MIN = 9.41458911
F_SPEC = F_MIN + 5.0
GUARD_MM = 682.8
SIDE_KEYS = ("args", "plant_s8", "c2_setup", "sensors", "controller_meta", "c2_timing", "settle_reference",
             "gravity_schedule", "mass_scale")
sys.path[:0] = [str(ROOT / "04_scripts/02_chrono"), str(ROOT / "04_scripts/03_control/s8"), str(ROOT / "03_src")]


def walk_diff(a, b, path="", out=None, limit=40):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            walk_diff(a.get(k), b.get(k), f"{path}.{k}", out, limit)
    elif a != b and len(out) < limit:
        out.append([path, str(a)[:100], str(b)[:100]])
    return out


def phases_of(res):
    return [(float(p["t_s"]), str(p["phase"]).lower()) for p in res["phases"]]


def events_of(res):
    return [(float(e["t_s"]), str(e["name"])) for e in res["events"]]


def first_diff_row(a, b):
    n = min(len(a), len(b))
    x, y = a[:n], b[:n]
    same = (x == y) | (np.isnan(x) & np.isnan(y))
    same = same.reshape(n, -1).all(axis=1)
    return None if same.all() else int(np.argmin(same))


def load(case_dir: Path) -> dict:
    res = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    with np.load(case_dir / "step_series.npz", allow_pickle=False) as z:
        st = {k: np.asarray(z[k]) for k in z.files}
    with np.load(case_dir / "completion_series.npz", allow_pickle=False) as z:
        comp = {k: np.asarray(z[k]) for k in z.files}
    with np.load(case_dir / "controller_commands.npz", allow_pickle=False) as z:
        cmd = {k: np.asarray(z[k]) for k in z.files}
    with np.load(case_dir / "record" / "record.npz", allow_pickle=False) as z:
        rec = {k: np.asarray(z[k]) for k in ("t", "F_cyl", "stroke_true", "meas.stroke", "s_ref", "s_motor", "u_applied")}
    return {"dir": case_dir, "res": res, "st": st, "comp": comp, "cmd": cmd, "rec": rec}


def side_values(run: dict, rj: dict, pm) -> dict:
    """Judged and recorded values of one run. Times are loop relative unless named *_abs."""
    res, st, comp, rec = run["res"], run["st"], run["comp"], run["rec"]
    t0 = float(res["t_loop_start_s"])
    b = rj["p3b"]
    c = b["checks"]
    ph = phases_of(res)
    ev = events_of(res)
    ready = [t - t0 for t, n in ph if n == "ready"]
    done = [t - t0 for t, n in ph if n == "done"]
    probe = [t - t0 for t, n in ph if n == "probe"]
    level = [t - t0 for t, n in ph if n == "level"]
    fault = [t - t0 for t, n in ph if n == "fault"]
    t_touch_end = level[0] if level else None
    dep = b.get("departure") or {}
    t_dep_abs = dep.get("t_departure_s")
    F = st["F_cyl_N"] / 1e3
    t = st["t_s"]
    k_dep = None if t_dep_abs is None else int(np.searchsorted(t, t_dep_abs))
    D = F @ N
    out = {"t_loop_start_abs": t0, "t_end_abs": float(t[-1]), "phases": [[round(x - t0, 3), n] for x, n in ph],
           "final_phase": ph[-1][1], "ready_s": ready, "done_s": done, "probe_s": probe, "fault_s": fault,
           "touch_end_s": t_touch_end, "checks": {k: v for k, v in c.items() if not isinstance(v, (dict, list)) or k in ("P3-1_flags", "P3-4_window_s")},
           "P3-6": b.get("P3-6_ready"), "unchanged_blocks_equal": rj["unchanged_blocks_equal"], "params_file_match": rj["params_file_match"]}
    F_after = b["P3-3_leg_force"]["F_min_after_N"]
    out["P3-3_F_min_after_kN"] = [x / 1e3 for x in F_after]
    if k_dep is not None:
        a = F[k_dep:]
        i, j = np.unravel_index(int(np.argmin(a)), a.shape)
        out["F_min_after_departure_kN"] = float(a[i, j])
        out["F_min_leg"] = LEGS[j]
        out["F_min_t_s"] = float(t[k_dep + i] - t0)
        out["F_min_after_dep_s"] = float(t[k_dep + i] - t_dep_abs)
        out["D_at_F_min_kN"] = float(D[k_dep + i])
        out["F_min_twist_removed_kN"] = float(a[i, j] - N[j] * D[k_dep + i])
        k8 = int(np.searchsorted(t, t_dep_abs + 8.0))
        w = a[: k8 - k_dep]
        out["F_min_first8_kN"] = float(w.min())
        out["F_min_first8_leg"] = LEGS[int(np.unravel_index(int(np.argmin(w)), w.shape)[1])]
        mw = 1000
        mean1 = np.column_stack([np.convolve(w[:, q], np.ones(mw) / mw, "valid") for q in range(4)])
        out["mean1s_min_first8_kN"] = float(mean1.min())
        out["D_peak_abs_after_dep_kN"] = float(np.abs(D[k_dep:]).max())
        out["D_lift_kN"] = float(F[k_dep:k_dep + 400].mean(axis=0) @ N)
    if done:
        k = int(np.searchsorted(t, done[0] + t0))
        out["D_at_first_done_kN"] = float(D[k])
    if t_touch_end is not None:
        k = int(np.searchsorted(t, t_touch_end + t0))
        out["D_te_kN"] = float(F[max(k - 200, 0):k].mean(axis=0) @ N)
        out["s_motor_te_mm"] = (st["s_motor_m"][k] * 1e3).round(4).tolist()
        out["tau_te_mm"] = float(N @ (st["s_motor_m"][k] * 1e3))
        Fr = F[:k]
        first = [int(np.argmax(Fr[:, q] > Fr[int(np.searchsorted(t, t0)), q] + 3.0)) for q in range(4)]
        out["t_contact_rel_te_s"] = [round(float(t[q] - (t_touch_end + t0)), 3) for q in first]
        out["s_contact_mm"] = [round(float(st["s_motor_m"][first[q], q] * 1e3), 3) for q in range(4)]
    out["t_departure_s"] = None if t_dep_abs is None else t_dep_abs - t0
    out["crawler_at_end_kN"] = float(st["scm_crawler_normal_N"][-1] / 1e3)
    att = b.get("P3-4_attitude") or {}
    out["P3-4"] = {k: att.get(k) for k in ("p34_absmax_deg", "p34_absmax_overall_deg", "p34_window_length_s", "window_short",
                                           "creep_vibration_suspect", "sensor_allowance_left_deg", "end_mean_roll_pitch_deg")}
    clr = b.get("P3-5_clearance_stroke") or {}
    out["P3-5"] = {k: clr.get(k) for k in ("rut_clearance_min_after_first_ready_m", "s_motor_max_m", "s_motor_limit_m", "rut_clearance_at_loc_m")}
    loc = b.get("P3-2_loc") or {}
    out["P3-2"] = {k: loc.get(k) for k in loc if not isinstance(loc.get(k), (dict, list))}
    out["P3-7_rise_kN"] = (c.get("P3-7_rise_min_loaded_N") or 0.0) / 1e3
    out["P3-8"] = b.get("P3-8_counts")
    rr = rec["meas.stroke"] * 1e3
    out["stroke_reading_max_mm"] = rr.max(axis=0).round(3).tolist()
    out["guard_margin_mm"] = GUARD_MM - float(rr.max())
    out["stroke_true_max_mm"] = (rec["stroke_true"].max(axis=0) * 1e3).round(3).tolist()
    roll, pitch = st["roll_pitch_deg"][:, 0], st["roll_pitch_deg"][:, 1]
    out["end_roll_pitch_deg"] = [float(roll[-1000:].mean()), float(pitch[-1000:].mean())]
    if k_dep is not None:
        out["att_max_after_dep_deg"] = float(np.abs(st["roll_pitch_deg"][k_dep:]).max())
    names = [n.split(":")[0] for _, n in ev]
    out["event_list"] = [[round(x - t0, 2), n] for x, n in ev]
    out["counts"] = {k: names.count(k) for k in sorted(set(names))}
    out["saturation_step_count"] = (res.get("monitor") or {}).get("saturation_step_count")
    out["moving_pressure"] = pm
    soil = res.get("c2_soil") or {}
    out["soil"] = {k: soil.get(k) for k in ("loc", "soil_mode", "t_loc_s", "t_P_s", "push_m", "W_ratio", "loc_revokes", "clearance_at_P_m", "clearance_at_loc_m")}
    ext = b.get("reapproach_limit_FLAG")
    out["reapproach_limit_flag"] = ext
    u = run["cmd"]["issued_u_m_s"]
    out["command_peak_mm_s"] = float(np.abs(u).max() * 1e3)
    out["command_over_vmax_periods"] = int((np.abs(u) > V_MAX * (1 + 1e-9)).any(axis=1).sum())
    return out


def stop_block(run: dict, rj: dict) -> dict:
    """SA-4 values of a safe stop run (spec 427 SA-4, 430.4.1)."""
    res, st = run["res"], run["st"]
    t0 = float(res["t_loop_start_s"])
    ev = events_of(res)
    stop = next(((x, n) for x, n in ev if n.startswith("FAULT_")), None)
    if stop is None:
        return {"stopped": False}
    t = st["t_s"]
    k = int(np.searchsorted(t, stop[0]))
    F = st["F_cyl_N"] / 1e3
    W = rj["p3b"]["weight_N"] / 1e3
    cr = st["scm_crawler_normal_N"] / 1e3
    pads = st["scm_pad_normal_N"] / 1e3
    ps = phases_of(res)
    return {"stopped": True, "t_stop_s": stop[0] - t0, "event": stop[1],
            "all_events_FAULT_WARN": [[round(x - t0, 2), n] for x, n in ev if n.startswith(("FAULT", "WARN"))],
            "FAULT_STROKE_END": sum(n.startswith("FAULT_STROKE_END") for _, n in ev),
            "F_min_after_stop_kN": F[k:].min(axis=0).round(3).tolist(), "F_min_after_stop_all_kN": float(F[k:].min()),
            "pad_normal_min_after_stop_kN": float(pads[k:].min()),
            "crawler_at_stop_kN": float(cr[k]), "crawler_max_after_stop_kN": float(cr[k:].max()), "crawler_end_kN": float(cr[-1]),
            "crawler_limit_stop_plus_0p01W_kN": float(cr[k] + 0.01 * W), "weight_kN": W,
            "crawler_0p01W_kN": 0.01 * W,
            "ready_count": sum(n == "ready" for _, n in ps),
            "end_roll_pitch_deg": st["roll_pitch_deg"][-1000:].mean(axis=0).round(4).tolist(),
            "F_at_stop_kN": F[k].round(3).tolist()}


def flow_block(run: dict) -> dict:
    fl = run["res"].get("flow_limit")
    if not fl:
        return {"present": False}
    su = fl["summary"]
    out = {"present": True, "setting": fl.get("setting"), "enabled": fl.get("enabled"),
           "short_s": su["short_s"], "by_phase": {k: v["short_s"] for k, v in su["by_phase"].items() if v["short_s"] > 0},
           "deficit_by_phase_L_min": {k: v.get("max_deficit_L_min") for k, v in su["by_phase"].items() if v["short_s"] > 0},
           "max_deficit_L_min": su["max_deficit_L_min"],
           "min_r_by_phase": {leg: v["min_r_by_phase"] for leg, v in su["speed_ratio"].items()},
           "long93_s": {leg: v["longest_below_0p93_s"] for leg, v in su["speed_ratio"].items()},
           "tracking_mm": su["tracking"], "limited_sets": su["limited_sets"], "swaps": su["residual_groups"],
           "steps": su["steps"], "over_supply": su["max_sum_Q_over_supply_minus_1"]}
    return out


def flow_recompute(run: dict) -> dict:
    """Second path for E-1 and E-2 from the raw flow series (1 ms rows)."""
    res = run["res"]
    t0 = float(res["t_loop_start_s"])
    with np.load(run["dir"] / "flow_series.npz", allow_pickle=True) as z:
        rows, cols = z["rows"], [str(c) for c in z["columns"]]
        supply = float(z["supply_m3_s"])
    idx = {c: i for i, c in enumerate(cols)}
    t = rows[:, idx["t"]]
    dt = float(np.median(np.diff(t)))
    t_rel = t - t0 if t[0] > 1.0 else t
    limited = rows[:, idx["limited_mask"]].astype(int)
    u = rows[:, [idx[f"u_{leg}"] for leg in LEGS]]
    v = rows[:, [idx[f"v_{leg}"] for leg in LEGS]]
    qd = rows[:, idx["Q_dem"]]
    short = qd > supply * (1 + 1e-6)
    n = int(round(1.0 / dt))
    ker = np.ones(n) / n
    r_min, below = {}, {}
    for i, leg in enumerate(LEGS):
        ub = np.convolve(u[:, i], ker, mode="valid")
        vb = np.convolve(v[:, i], ker, mode="valid")
        ok = np.abs(ub) >= 0.1 * V_MAX
        r = np.full_like(ub, np.nan)
        r[ok] = vb[ok] / ub[ok]
        r_min[leg] = float(np.nanmin(r)) if ok.any() else None
        low = np.nan_to_num(r, nan=1.0) < 0.93
        edges = np.diff(np.concatenate(([0], low.astype(int), [0])))
        spans = np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)
        below[leg] = float(spans.max() * dt) if spans.size else 0.0
    edges = np.diff(np.concatenate(([0], (limited > 0).astype(int), [0])))
    runs = [(float(t_rel[a]), float(t_rel[b - 1])) for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]
    deficit = np.abs(u - v)
    e3 = np.abs(np.cumsum((u - v) * dt, axis=0)) * 1e3
    return {"cols": cols, "dt_s": dt, "t_first_rel_s": float(t_rel[0]), "t_last_rel_s": float(t_rel[-1]),
            "supply_L_min": supply * 6e4, "short_s": float(short.sum() * dt), "limited_s": float((limited > 0).sum() * dt),
            "max_deficit_L_min": float((qd - supply).max() * 6e4), "r_min": r_min, "below93_s": below,
            "first_limited_rel_s": runs[0][0] if runs else None,
            "last_limited_rel_s": runs[-1][1] if runs else None, "n_limited_runs": len(runs),
            "runs_ge_0p5s": [[round(a, 3), round(b, 3)] for a, b in runs if b - a >= 0.5],
            "max_u_minus_v_mm_s": float(deficit.max() * 1e3), "max_abs_integral_mm": e3.max(axis=0).round(3).tolist(),
            "max_between_legs_mm": float(np.ptp(np.cumsum((u - v) * dt, axis=0) * 1e3, axis=1).max())}


def prefix_identity(on: dict, off: dict, first_limited_rel: float | None) -> dict:
    """V-5: the runs must be bit identical until the limit first acts."""
    t0 = float(on["res"]["t_loop_start_s"])
    out = {}
    for name, a, b, ta in (("commands", on["cmd"]["issued_u_m_s"], off["cmd"]["issued_u_m_s"], on["cmd"]["t_s"]),
                           ("F_cyl", on["st"]["F_cyl_N"], off["st"]["F_cyl_N"], on["st"]["t_s"]),
                           ("s_motor", on["st"]["s_motor_m"], off["st"]["s_motor_m"], on["st"]["t_s"]),
                           ("crawler", on["st"]["scm_crawler_normal_N"], off["st"]["scm_crawler_normal_N"], on["st"]["t_s"])):
        d = first_diff_row(a, b)
        out[name] = {"first_diff_rel_s": None if d is None else float(ta[d] - t0)}
    out["first_limited_rel_s"] = first_limited_rel
    return out


def main() -> None:
    import paper_max_pressure_table as pmt
    import run_S9

    out = {"criteria_sha256": "1d743eab34d5091757b5e021bc1722f56fbedea9b0bc7ff2b4ca5ea0774fd0de", "rows": {}}
    for cid, (case, off_batch) in CASES.items():
        d_on, d_off = ON / case, off_batch / case
        on, off = load(d_on), load(d_off)
        rj_on = run_S9.rejudge_case(d_on, write=False)
        rj_off = run_S9.rejudge_case(d_off, write=False)
        stored = json.loads((d_off / "result_rejudge_rev60.json").read_text(encoding="utf-8"))
        same_stored = json.dumps(rj_off["p3b"], sort_keys=True, default=str) == json.dumps(stored["p3b"], sort_keys=True, default=str)
        diff_stored = walk_diff(rj_off["p3b"].get("checks"), stored["p3b"].get("checks"))
        vals_on = side_values(on, rj_on, None)
        vals_off = side_values(off, rj_off, None)
        for key, side, values in (("on", d_on, vals_on), ("off", d_off, vals_off)):
            peak = pmt.record_moving_peak(side)
            cur = peak["current"]
            values["moving_pressure"] = {"max_bar": cur["max_bar"], "leg": cur.get("leg"), "t_s": cur.get("t_s"),
                                         "head_max_bar": peak["measured_head_pressure_current_mask_max_bar"],
                                         "any_state_bar": peak["max_any_state_bar"]}
        fr = flow_recompute(on)
        settings = {k: walk_diff(on["res"].get(k), off["res"].get(k)) for k in SIDE_KEYS}
        code_diff = walk_diff(on["res"].get("code_state"), off["res"].get("code_state"))
        out["rows"][cid] = {
            "case": case, "on_dir": str(d_on), "off_dir": str(d_off),
            "on": vals_on, "off": vals_off,
            "off_rejudge_equals_stored_p3b": same_stored, "off_rejudge_checks_diff": diff_stored,
            "flow": flow_block(on), "flow_recomputed": fr,
            "V5": prefix_identity(on, off, fr["first_limited_rel_s"]),
            "settings_diff": settings, "code_state_diff": code_diff,
            "params_sha": [(on["res"].get("meta") or {}).get("params_sha256"), (off["res"].get("meta") or {}).get("params_sha256")],
            "stop_on": stop_block(on, rj_on), "stop_off": stop_block(off, rj_off),
        }
        print(cid, "done", flush=True)
    (HERE / "soil_tables.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
