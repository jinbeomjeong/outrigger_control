"""S8 SA-4 clause on the two flow-off runs meant to hit the 16.9 s stop cycle (eps 0.5e-3, 0.75e-3), next to all earlier runs.

Same calculation as s8off_verdict.py and s8on_verdict.py (run_block, phase_block). Adds the crawler oscillation state before the stop
(peak timing, phase at the stop, amplitude), the stop cycle against the clause margin, and the flow deficit. Does not change the F-5
record (user decision). Reads the run folders only. Writes s8off169_verdict.json; exports CSV for xcheck_s8off169.jl to argv[1].
A second run reads xcheck_s8off169_julia.json.

Run: conda run -n dynamics-dev python -I -B s8off169_verdict.py <scratch folder>
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

HERE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono")
sys.path.insert(0, str(HERE))
import s8eta_verdict as eta  # noqa: E402
import s8off_verdict as base  # noqa: E402
import s8on_verdict as prev  # noqa: E402

S9 = base.S9
CASE = base.CASE
RUNS = dict(eta.RUNS)
RUNS["off_eps0p50e-3"] = S9 / "batch_s8off169_e0p50e-3_20261105" / CASE
RUNS["off_eps0p75e-3"] = S9 / "batch_s8off169_e0p75e-3_20261105" / CASE
NEW = ("off_eps0p50e-3", "off_eps0p75e-3")
ORDER = ("off_stored", "off_eps0p50e-3", "off_eps0p75e-3", "off_eps1e-3", "off_eps2e-3", "on_stored", "on_eps1e-3", "on_eps2e-3", "on_eta0.90", "on_eta0.925")
SMOOTH_N = 20
"""Same 20 ms moving mean as crawler_block."""
PHASE_16P9_S = 0.585
"""Below the smallest stop - peak time of the 16.9 s rows, so every run has a sample there before its stop."""
SLOW_U_MM_S = 0.30 * 20.924


def oscillation_block(path: Path, t_stop: float) -> dict:
    """Crawler oscillation before the stop: extrema of the 20 ms mean, phase of the stop sample inside the last cycle."""
    with np.load(path / "step_series.npz", allow_pickle=False) as z:
        t = np.asarray(z["t_s"])
        c = np.asarray(z["scm_crawler_normal_N"]) / 1e3
    smooth = np.convolve(c, np.ones(SMOOTH_N) / SMOOTH_N, "same")
    k = int(np.searchsorted(t, t_stop))
    sel = np.flatnonzero((t >= t_stop - 6.0) & (t < t_stop))
    pk, _ = find_peaks(smooth[sel], prominence=1.0, distance=150)
    tr, _ = find_peaks(-smooth[sel], prominence=1.0, distance=150)
    tp, tt = t[sel][pk], t[sel][tr]
    phase = None
    if tp.size >= 2:
        period = float(np.diff(tp[-3:]).mean())
        phase = float((t_stop - tp[-1]) / period)
    win = (t >= t_stop - 4.0) & (t < t_stop)
    # first extremum after the stop, how the load leaves the stop sample
    after = np.flatnonzero((t >= t_stop) & (t < t_stop + 4.0))
    pk_after, _ = find_peaks(smooth[after], prominence=1.0, distance=150)
    tr_after, _ = find_peaks(-smooth[after], prominence=1.0, distance=150)
    return {"peak_t_rel_stop_s": (tp - t_stop).round(3).tolist(), "peak_kN": smooth[sel][pk].round(3).tolist(),
            "trough_t_rel_stop_s": (tt - t_stop).round(3).tolist(), "trough_kN": smooth[sel][tr].round(3).tolist(),
            "last_peak_before_stop_s": None if not tp.size else float(t_stop - tp[-1]), "last_trough_before_stop_s": None if not tt.size else float(t_stop - tt[-1]),
            "cycle_phase_since_last_peak": phase, "mean_4s_before_kN": float(c[win].mean()), "ptp_4s_before_kN": float(np.ptp(c[win])),
            "max_4s_before_kN": float(c[win].max()), "min_4s_before_kN": float(c[win].min()), "c_stop_kN": float(c[k]),
            "peaks_after_rel_stop_s": (t[after][pk_after] - t_stop).round(3).tolist(), "peaks_after_kN": smooth[after][pk_after].round(3).tolist(),
            "troughs_after_rel_stop_s": (t[after][tr_after] - t_stop).round(3).tolist(), "troughs_after_kN": smooth[after][tr_after].round(3).tolist()}


def aligned_rms(path_a: Path, path_b: Path, t_a: float, t_b: float, lo: float, hi: float) -> dict:
    """RMS difference of the crawler load, the two series aligned on the given times."""
    out = {}
    with np.load(path_a / "step_series.npz", allow_pickle=False) as a, np.load(path_b / "step_series.npz", allow_pickle=False) as b:
        ta, ca, tb, cb = np.asarray(a["t_s"]), np.asarray(a["scm_crawler_normal_N"]) / 1e3, np.asarray(b["t_s"]), np.asarray(b["scm_crawler_normal_N"]) / 1e3
    grid = np.arange(lo, hi, 1e-3)
    x, y = np.interp(grid + t_a, ta, ca), np.interp(grid + t_b, tb, cb)
    out["rms_kN"] = float(np.sqrt(np.mean((x - y) ** 2)))
    out["max_abs_kN"] = float(np.abs(x - y).max())
    return out


def stop_cycle_block(path: Path, res: dict, t_stop: float, te_abs: float) -> dict:
    """Where the stop falls relative to the large crawler peak before it, and the stroke that decides the stop period.

    The peak is the raw maximum in the 1.5 s before the stop. Slow start = first command in the 3 s before the stop with the FR
    command at or below 0.30 v_max. Reads step_series, controller_commands and the event list only.
    """
    with np.load(path / "step_series.npz", allow_pickle=False) as z:
        t, c, s = np.asarray(z["t_s"]), np.asarray(z["scm_crawler_normal_N"]) / 1e3, np.asarray(z["s_motor_m"]) * 1e3
        sink, rp, zo = np.asarray(z["pad_sinkage_geometric_m"]) * 1e3, np.asarray(z["roll_pitch_deg"]), np.asarray(z["z_origin_m"]) * 1e3
    k = int(np.searchsorted(t, t_stop))
    ke = int(np.searchsorted(t, te_abs))
    sel = np.flatnonzero((t >= t_stop - 1.5) & (t < t_stop))
    ip = int(sel[int(np.argmax(c[sel]))])
    tp = float(t[ip])
    at = {f"{o:.3f}": (float(c[int(np.searchsorted(t, tp + o))]) if tp + o < t_stop else None) for o in (0.40, 0.50, 0.55, PHASE_16P9_S, 0.65, 0.70, 0.75)}
    second = (t >= tp + 0.6) & (t < t_stop)
    with np.load(path / "controller_commands.npz", allow_pickle=False) as z:
        tc, u = np.asarray(z["t_s"]), np.asarray(z["issued_u_m_s"]) * 1e3
    win = np.flatnonzero((tc >= t_stop - 3.0) & (tc < t_stop) & (u[:, 1] <= SLOW_U_MM_S))
    t_slow = float(tc[win[0]]) if win.size else None
    twist = float(s[ip, 0] - s[ip, 1] - s[ip, 2] + s[ip, 3])
    return {"peak_kN": float(c[ip]), "peak_after_touch_end_s": tp - te_abs, "delta_stop_minus_peak_s": t_stop - tp, "crawler_after_peak_kN": at,
            "max_between_peak_plus_0p6_and_stop_kN": None if not second.any() else float(c[second].max()),
            "slow_start_before_stop_s": None if t_slow is None else t_stop - t_slow, "slow_periods": None if t_slow is None else int(round((t_stop - t_slow) / 0.1)),
            "u_FR_last_before_stop_mm_s": float(u[int(np.searchsorted(tc, t_stop)) - 1, 1]),
            "s_FR_touch_end_mm": float(s[ke, 1]), "s_FR_peak_mm": float(s[ip, 1]), "s_FR_stop_mm": float(s[k, 1]), "s_mean_stop_mm": float(s[k].mean()),
            "s_FR_gain_touch_end_to_peak_mm": float(s[ip, 1] - s[ke, 1]), "s_FR_peak_to_stop_mm": float(s[k, 1] - s[ip, 1]), "s_mean_gain_touch_end_to_peak_mm": float(s[ip].mean() - s[ke].mean()),
            "twist_s_at_peak_mm": twist, "sink_FR_peak_mm": float(sink[ip, 1]), "sink_at_peak_mm": sink[ip].round(3).tolist(), "roll_peak_deg": float(rp[ip, 0]), "z_origin_peak_mm": float(zo[ip]),
            "t_peak_abs_s": tp, "t_stop_abs_s": t_stop,
            "info_events_3s_before_stop": [[round(float(e["t_s"]) - t_stop, 2), str(e["name"])] for e in res["events"] if t_stop - 3.0 <= float(e["t_s"]) <= t_stop + 0.2]}


def peak_aligned_rms(names: tuple, blocks: dict) -> dict:
    """RMS of the crawler difference on [-1.0, +PHASE_16P9_S] s around each run's own peak, flow on and off pairs apart."""
    grid = np.arange(-1.0, PHASE_16P9_S, 1e-3)
    traces = {}
    for n in names:
        with np.load(RUNS[n] / "step_series.npz", allow_pickle=False) as z:
            traces[n] = np.interp(grid + blocks[n]["t_peak_abs_s"], np.asarray(z["t_s"]), np.asarray(z["scm_crawler_normal_N"]) / 1e3)
    pairs = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            kind = "on_on" if a.startswith("on") and b.startswith("on") else ("off_off" if a.startswith("off") and b.startswith("off") else "on_off")
            pairs.setdefault(kind, []).append(float(np.sqrt(np.mean((traces[a] - traces[b]) ** 2))))
    without = [n for n in names if n != "off_eps0p75e-3"]
    pairs_wo = {}
    for i, a in enumerate(without):
        for b in without[i + 1:]:
            kind = "on_on" if a.startswith("on") and b.startswith("on") else ("off_off" if a.startswith("off") and b.startswith("off") else "on_off")
            pairs_wo.setdefault(kind, []).append(float(np.sqrt(np.mean((traces[a] - traces[b]) ** 2))))
    fmt = lambda p: {k: {"n": len(v), "min_kN": min(v), "median_kN": float(np.median(v)), "max_kN": max(v)} for k, v in p.items()}
    return {"window_rel_peak_s": [-1.0, PHASE_16P9_S], "all": fmt(pairs), "without_off_eps0p75e-3": fmt(pairs_wo)}


def exact_label_test(values_on: list, values_off: list) -> dict:
    """All C(10,5) on/off labellings: share with a mean difference at least as large (two sided). Runs are not independent draws."""
    x = np.array(list(values_on) + list(values_off), dtype=float)
    d0 = abs(np.mean(values_on) - np.mean(values_off))
    count = total = 0
    for pick in combinations(range(x.size), len(values_on)):
        mask = np.zeros(x.size, bool)
        mask[list(pick)] = True
        total += 1
        count += abs(x[mask].mean() - x[~mask].mean()) >= d0 - 1e-12
    return {"mean_on": float(np.mean(values_on)), "mean_off": float(np.mean(values_off)), "share_as_extreme": count / total, "n_labellings": total}


def main() -> None:
    import paper_max_pressure_table as pmt
    import run_S9

    scratch = Path(sys.argv[1])
    runs = {n: base.run_block(n, p, run_S9, pmt) for n, p in RUNS.items()}
    phase = {n: prev.phase_block(p) for n, p in RUNS.items()}
    flow = {n: eta.flow_block(p) for n, p in RUNS.items()}
    results = {n: json.loads((p / "result.json").read_text(encoding="utf-8")) for n, p in RUNS.items()}
    wrappers = {n: prev.wrapper_state(p) for n, p in RUNS.items()}
    osc = {}
    for n, p in RUNS.items():
        t0 = float(results[n]["t_loop_start_s"])
        osc[n] = oscillation_block(p, runs[n]["t_stop_s"] + t0)
        phase[n]["stop_minus_touch_end_s"] = round(runs[n]["t_stop_s"] - phase[n]["touch_end_s"], 2)
        phase[n]["stop_minus_first_contact_s"] = round(runs[n]["t_stop_s"] - phase[n]["first_pad_contact_s"], 3)
    loc = {n: [round(float(e["t_s"]) - float(r["t_loop_start_s"]), 2) for e in r["events"] if e["name"] == "crawler_liftoff_confirmed"] for n, r in results.items()}

    table = []
    for n in ORDER:
        r, c, ph, fl = runs[n], runs[n]["crawler"], phase[n], flow[n]
        table.append({"run": n, "flow": "on" if fl else "off", "eta_v": None if not fl else fl["eta_v"], "t_stop_s": round(r["t_stop_s"], 2), "touch_end_s": ph["touch_end_s"],
                      "stop_minus_touch_end_s": ph["stop_minus_touch_end_s"], "first_pad_contact_s": ph["first_pad_contact_s"], "stop_minus_first_contact_s": ph["stop_minus_first_contact_s"],
                      "at_stop_kN": c["at_stop_kN"], "slope_kN_s": c["slope_at_stop_kN_s"], "since_crossing_ms": None if c["t_since_last_below_0p01W_s"] is None else c["t_since_last_below_0p01W_s"] * 1e3, "limit_kN": c["limit_kN"],
                      "max_after_kN": c["max_after_kN"], "tmax_after_s": c["max_after_t_after_stop_s"], "rise_kN": c["rise_kN"], "margin_kN": c["margin_kN"], "end_kN": c["end_kN"], "clause_pass": c["clause_pass"],
                      "F_min_legs_kN": r["F_min_after_stop_kN"], "F_min_kN": r["F_min_after_stop_all_kN"], "moving_bar": r["moving_bar"], "guard_margin_mm": r["guard_margin_mm"], "end_roll_deg": r["end_roll_pitch_deg"][0],
                      "ready": r["ready_count"], "FAULT_STROKE_END": r["FAULT_STROKE_END"], "saturation": r["saturation"], "first_fault": r["events_fault_warn"][-1][1] if r["events_fault_warn"] else None,
                      "deficit_front_mm": None if not fl else fl["deficit_end_mm"]["FL"], "deficit_rear_mm": None if not fl else fl["deficit_end_mm"]["RL"],
                      "cycle_phase": osc[n]["cycle_phase_since_last_peak"], "last_peak_before_stop_s": osc[n]["last_peak_before_stop_s"], "last_trough_before_stop_s": osc[n]["last_trough_before_stop_s"]})

    at = np.array([x["at_stop_kN"] for x in table])
    mx = np.array([x["max_after_kN"] for x in table])
    rise = np.array([x["rise_kN"] for x in table])
    is_on = np.array([x["flow"] == "on" for x in table])
    corr = {"at_stop_vs_max_after_all": float(np.corrcoef(at, mx)[0, 1]), "at_stop_vs_rise_all": float(np.corrcoef(at, rise)[0, 1]),
            "at_stop_vs_max_after_off": float(np.corrcoef(at[~is_on], mx[~is_on])[0, 1]), "at_stop_vs_max_after_on": float(np.corrcoef(at[is_on], mx[is_on])[0, 1])}
    fit = np.polyfit(at, mx, 1)
    groups = {}
    for x in table:
        groups.setdefault(f"{x['stop_minus_touch_end_s']:.1f}", {"on": [], "off": []})[x["flow"]].append({"run": x["run"], "margin_kN": x["margin_kN"], "pass": x["clause_pass"], "at_stop_kN": x["at_stop_kN"], "max_after_kN": x["max_after_kN"]})
    pairs = {}
    for a, b in (("off_eps0p50e-3", "on_eps1e-3"), ("off_eps0p75e-3", "on_eps1e-3"), ("off_stored", "on_stored"), ("off_eps0p50e-3", "off_eps0p75e-3")):
        ta, tb = runs[a]["t_stop_s"] + float(results[a]["t_loop_start_s"]), runs[b]["t_stop_s"] + float(results[b]["t_loop_start_s"])
        pairs[f"{a}__{b}"] = {"before_stop_4s": aligned_rms(RUNS[a], RUNS[b], ta, tb, -4.0, 0.0), "after_stop_4s": aligned_rms(RUNS[a], RUNS[b], ta, tb, 0.0, 4.0)}

    cycle = {}
    for n in ORDER:
        t0 = float(results[n]["t_loop_start_s"])
        cycle[n] = stop_cycle_block(RUNS[n], results[n], runs[n]["t_stop_s"] + t0, phase[n]["touch_end_s"] + t0)
    off_names = [n for n in ORDER if n.startswith("off")]
    on_names = [n for n in ORDER if n.startswith("on")]
    margins = np.array([runs[n]["crawler"]["margin_kN"] for n in ORDER])
    deltas = np.array([cycle[n]["delta_stop_minus_peak_s"] for n in ORDER])
    ranks = lambda v: np.argsort(np.argsort(v)).astype(float)
    labels = {key: exact_label_test([g(n) for n in on_names], [g(n) for n in off_names]) for key, g in (
        ("stop_minus_touch_end_s", lambda n: phase[n]["stop_minus_touch_end_s"]), ("delta_stop_minus_peak_s", lambda n: cycle[n]["delta_stop_minus_peak_s"]),
        ("s_FR_peak_mm", lambda n: cycle[n]["s_FR_peak_mm"]), ("s_FR_gain_touch_end_to_peak_mm", lambda n: cycle[n]["s_FR_gain_touch_end_to_peak_mm"]), ("s_FR_touch_end_mm", lambda n: cycle[n]["s_FR_touch_end_mm"]),
        ("margin_kN", lambda n: runs[n]["crawler"]["margin_kN"]))}
    # implied clause terms if an off run had stopped at the 16.9 s phase: reference measured in the off runs, peak only from runs still lifting there
    implied = {}
    still_lifting = [n for n in off_names if cycle[n]["delta_stop_minus_peak_s"] >= 0.80]
    for n in off_names:
        ref = cycle[n]["crawler_after_peak_kN"][f"{PHASE_16P9_S:.3f}"]
        implied[n] = {"reference_kN": ref, "limit_kN": ref + base.MARGIN_KN, "second_peak_while_lifting_kN": cycle[n]["max_between_peak_plus_0p6_and_stop_kN"] if n in still_lifting else None}
        if n in still_lifting:
            implied[n]["limit_minus_second_peak_kN"] = implied[n]["limit_kN"] - implied[n]["second_peak_while_lifting_kN"]
    code_same = {}
    prior_wrap = json.loads((RUNS["off_eps1e-3"] / "eps_wrapper.json").read_text(encoding="utf-8"))
    for n in NEW:
        w = json.loads((RUNS[n] / "eps_wrapper.json").read_text(encoding="utf-8"))
        code_same[n] = {"same_wrapper_sha": w["wrapper_sha256"] == prior_wrap["wrapper_sha256"], "files_different_from_off_eps1e-3": [f for f, v in w["code_sha256"].items() if prior_wrap["code_sha256"].get(f) != v]}

    out = {"criteria_sha256": base.SHA, "rule": "F-5 record stays by user decision; this result does not change it",
           "stop_cycle_16p9_reached": {n: bool(abs(phase[n]["stop_minus_touch_end_s"] - 16.9) < 0.05) for n in NEW},
           "stop_cycle": cycle, "peak_aligned_rms_before_stop": peak_aligned_rms(ORDER, cycle), "label_tests_not_independent_runs": labels, "implied_off_at_16p9_phase_not_a_run": implied,
           "delta_vs_margin": {"pearson": float(np.corrcoef(deltas, margins)[0, 1]), "spearman": float(np.corrcoef(ranks(deltas), ranks(margins))[0, 1])},
           "code_vs_off_eps1e-3": code_same,
           "clause_pass": {n: runs[n]["crawler"]["clause_pass"] for n in ORDER}, "table": table, "groups_by_stop_cycle": groups, "oscillation": osc, "phase": phase, "loc_rel_s": loc,
           "correlation_n10": corr, "fit_max_after_vs_at_stop_n10": {"slope": float(fit[0]), "intercept_kN": float(fit[1])}, "aligned_stop_pairs": pairs,
           "wrappers": {n: wrappers[n] for n in NEW}, "first_diff_vs_stored_off": {n: base.first_diff(RUNS[n], RUNS["off_stored"]) for n in NEW},
           "first_diff_between_new": base.first_diff(RUNS[NEW[0]], RUNS[NEW[1]]),
           "args_diff_vs_off_stored": {n: eta.base_diff(results["off_stored"]["args"], results[n]["args"]) for n in NEW},
           "flow_limit_absent": {n: flow[n] is None for n in NEW}, "runs": runs, "flow": flow}
    jl_path = HERE / "xcheck_s8off169_julia.json"
    if jl_path.exists():
        jl = json.loads(jl_path.read_text(encoding="utf-8"))
        d = {}
        for n in NEW:
            r = runs[n]
            for key, a, b in (("at_stop", jl[n]["crawler_at_stop_kN"], r["crawler"]["at_stop_kN"]), ("max_after", jl[n]["crawler_max_after_kN"], r["crawler"]["max_after_kN"]),
                              ("end", jl[n]["crawler_end_kN"], r["crawler"]["end_kN"]), ("F_min_after_stop", min(jl[n]["F_min_after_stop_kN"]), r["F_min_after_stop_all_kN"]),
                              ("t_stop", jl[n]["t_stop_abs_s"], r["t_stop_s"] + float(results[n]["t_loop_start_s"]))):
                d[f"{n}_{key}"] = abs(a - b) / abs(b)
        for n in ORDER:
            d[f"{n}_delta"] = abs(jl[n]["delta_stop_minus_peak_s"] - cycle[n]["delta_stop_minus_peak_s"]) / cycle[n]["delta_stop_minus_peak_s"]
            d[f"{n}_peak"] = abs(jl[n]["peak_kN"] - cycle[n]["peak_kN"]) / cycle[n]["peak_kN"]
            d[f"{n}_ref0585"] = abs(jl[n]["crawler_peak_plus_0p585_kN"] - cycle[n]["crawler_after_peak_kN"][f"{PHASE_16P9_S:.3f}"]) / cycle[n]["crawler_after_peak_kN"][f"{PHASE_16P9_S:.3f}"]
        out["xcheck_python_julia"] = {"worst_relative_diff": max(d.values()), "worst_key": max(d, key=d.get), "clause_same": {n: [jl[n]["clause_pass"], runs[n]["crawler"]["clause_pass"]] for n in ORDER}, "grade": "match" if max(d.values()) <= 1e-9 else "check"}
    (HERE / "s8off169_verdict.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")

    for x in table:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()}, default=float))
    print("groups", json.dumps(groups, default=float))
    print("corr", json.dumps(corr), "fit", fit.tolist())
    print("pairs", json.dumps(pairs))
    for n in ORDER:
        print(n, "osc", json.dumps(osc[n]))
        print(n, "extra", json.dumps({"loc": loc[n], "events": runs[n]["events_fault_warn"], "max1s": runs[n]["crawler"]["max_1s_before_kN"], "min1s": runs[n]["crawler"]["min_1s_before_kN"], "last_zero": runs[n]["crawler"]["last_zero_before_stop_s"], "patches": runs[n]["crawler"]["patches_min_1s_before"],
                                       "P3_2": runs[n]["P3_2_s"], "P3_1": runs[n]["P3_1_recontact_pass"], "blocks_eq": runs[n]["rejudge_blocks_equal"], "params": runs[n]["params_match"], "git": runs[n]["code_git"], "speed": phase[n]["touch_speed_mm_s"], "latch": phase[n]["latch_rel_s"]}, default=float))
    print("wrappers", json.dumps(out["wrappers"], default=float))
    print("first_diff", json.dumps(out["first_diff_vs_stored_off"]), json.dumps(out["first_diff_between_new"]))
    print("args_diff", json.dumps(out["args_diff_vs_off_stored"], default=str))
    print("xcheck", json.dumps(out.get("xcheck_python_julia"), default=float))
    print("CYCLE")
    for n in ORDER:
        print(n, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in cycle[n].items()}, default=float))
    print("rms", json.dumps(out["peak_aligned_rms_before_stop"]))
    print("labels", json.dumps(labels))
    print("implied", json.dumps(implied))
    print("delta_margin", json.dumps(out["delta_vs_margin"]), "code", json.dumps(code_same), "reached", json.dumps(out["stop_cycle_16p9_reached"]))
    for n in ORDER:
        with np.load(RUNS[n] / "step_series.npz", allow_pickle=False) as z:
            np.savetxt(scratch / f"s8off169_{n}.csv", np.column_stack([z["t_s"], z["scm_crawler_normal_N"], z["F_cyl_N"]]), delimiter=",", fmt="%.17g",
                       header="t_s,crawler_N,F_FL_N,F_FR_N,F_RL_N,F_RR_N", comments="")


if __name__ == "__main__":
    main()
