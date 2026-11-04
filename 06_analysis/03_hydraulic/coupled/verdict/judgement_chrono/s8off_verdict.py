"""S8 SA-4 clause on the flow-off phase variants (user rule fixed before the result), next to the stored off and on runs.

Same calculation as s8_stop_detail.py and x6_stop_check.py: crawler at the stop sample, maximum after it, limit = stop value
+ 0.01 W. Adds the stop state, the moving pressure (paper_max_pressure_table.record_moving_peak), the P3 checks through
run_S9.rejudge_case(write=False), the wrapper state, the first difference against the stored off run and the crawler
oscillation before the stop. Reads the run folders only. Writes s8off_verdict.json; exports CSV for xcheck_s8off.jl to argv[1].

Run: conda run -n dynamics-dev python -I s8off_verdict.py <scratch folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

ROOT =Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
S9 = ROOT / "07_results/S9"
CASE = "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
RUNS = {"off_stored": S9 / "batch_FINAL-REP_20261030_223359" / CASE,
        "off_eps1e-3": S9 / "batch_s8off_eps1e-3_20261104" / CASE,
        "off_eps2e-3": S9 / "batch_s8off_eps2e-3_20261104" / CASE,
        "on_stored": S9 / "batch_COUPLED_eta085_20261104_142213" / CASE}
OFF_RUNS = ("off_stored", "off_eps1e-3", "off_eps2e-3")
WEIGHT_KN = 380.11291206408396
MARGIN_KN = 0.01 * WEIGHT_KN
F_MIN_KN = 9.41458911
SHA = "1d743eab34d5091757b5e021bc1722f56fbedea9b0bc7ff2b4ca5ea0774fd0de"
sys.path[:0] = [str(ROOT / "04_scripts/02_chrono"), str(ROOT / "04_scripts/03_control/s8"), str(ROOT / "03_src")]


def crawler_block(t, c, t_stop, patches) -> dict:
    k = int(np.searchsorted(t, t_stop))
    i_max = k + int(np.argmax(c[k:]))
    below = np.flatnonzero(c[:k] < MARGIN_KN)
    last_below = int(below[-1]) if below.size else None
    zero = np.flatnonzero(c[:k] <= 0.0)
    pre = (t >= t_stop - 6.0) & (t < t_stop)
    x = c[pre] - c[pre].mean()
    w = np.hanning(x.size)
    spec = np.abs(np.fft.rfft(x * w))
    freq = np.fft.rfftfreq(x.size, 1e-3)
    band = (freq >= 0.5) & (freq <= 5.0)
    f_peak = float(freq[band][np.argmax(spec[band])])
    post = (t >= t_stop) & (t < t_stop + 6.0)
    y = c[post] - c[post].mean()
    spec_y = np.abs(np.fft.rfft(y * np.hanning(y.size)))
    freq_y = np.fft.rfftfreq(y.size, 1e-3)
    band_y = (freq_y >= 0.5) & (freq_y <= 5.0)
    win = (t >= t_stop - 1.0) & (t < t_stop)
    smooth = np.convolve(c, np.ones(20) / 20, "same")
    intervals = {}
    for label, lo, hi in (("before_stop_4s", t_stop - 4.0, t_stop), ("after_stop_4s", t_stop, t_stop + 4.0)):
        sel = np.flatnonzero((t >= lo) & (t < hi))
        peaks, _ = find_peaks(smooth[sel], prominence=1.0, distance=150)
        times = t[sel][peaks]
        intervals[label] = {"peak_t_rel_stop_s": (times - t_stop).round(3).tolist(), "freq_from_mean_interval_Hz": None if times.size < 2 else float(1.0 / np.diff(times).mean())}
    k_cross = None if last_below is None else last_below + 1
    fixed_delay = {}
    if k_cross is not None:
        for delay_ms in (15, 46, 63):
            ref = float(c[k_cross + delay_ms - 1])
            fixed_delay[str(delay_ms)] = {"ref_kN": ref, "same_max_after_passes": bool(c[k:].max() <= ref + MARGIN_KN)}
    refs = {"mean_0p2s_before": float(c[k - 200:k].mean()), "mean_1s_before": float(c[k - 1000:k].mean()),
            "median_1s_before": float(np.median(c[k - 1000:k]))}
    return {"at_stop_kN": float(c[k]), "max_after_kN": float(c[k:].max()), "max_after_t_after_stop_s": float(t[i_max] - t_stop),
            "limit_kN": float(c[k] + MARGIN_KN), "margin_kN": float(c[k] + MARGIN_KN - c[k:].max()),
            "clause_pass": bool(c[k:].max() <= c[k] + MARGIN_KN), "rise_kN": float(c[k:].max() - c[k]), "end_kN": float(c[-1]),
            "t_since_last_below_0p01W_s": None if last_below is None else float(t_stop - t[last_below]),
            "min_1s_before_kN": float(c[k - 1000:k].min()), "max_1s_before_kN": float(c[k - 1000:k].max()),
            "last_zero_before_stop_s": None if not zero.size else float(t_stop - t[zero[-1]]),
            "patches_min_1s_before": int(patches[k - 1000:k].min()),
            "slope_at_stop_kN_s": float((c[k + 10] - c[k - 10]) / (t[k + 10] - t[k - 10])),
            "peak_freq_6s_before_Hz": f_peak, "peak_freq_6s_after_Hz": float(freq_y[band_y][np.argmax(spec_y[band_y])]),
            "crawler_peaks": intervals, "analysis_reference_at_fixed_delay_after_0p01W_crossing": fixed_delay,
            "other_references": {n: {"ref_kN": v, "passes": bool(c[k:].max() <= v + MARGIN_KN)} for n, v in refs.items()},
            "trace_rel_stop_kN": {str(g): float(c[int(np.searchsorted(t, t_stop + g))]) for g in (-0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 20.0)},
            "win_ptp_1s_before_kN": float(np.ptp(c[win]))}


def run_block(name: str, path: Path, run_s9, pmt) -> dict:
    res = json.loads((path / "result.json").read_text(encoding="utf-8"))
    t0 = float(res["t_loop_start_s"])
    with np.load(path / "step_series.npz", allow_pickle=False) as z:
        t = np.asarray(z["t_s"])
        c = np.asarray(z["scm_crawler_normal_N"]) / 1e3
        F = np.asarray(z["F_cyl_N"]) / 1e3
        rp = np.asarray(z["roll_pitch_deg"])
        patches = np.asarray(z["scm_crawler_patches"])
        pad = np.asarray(z["scm_pad_normal_N"]) / 1e3
    events = [(float(e["t_s"]), str(e["name"])) for e in res["events"]]
    t_stop = next(x for x, n in events if n.startswith("FAULT_LIFT_STROKE_LIMIT"))
    k = int(np.searchsorted(t, t_stop))
    phases = [(float(p["t_s"]) - t0, str(p["phase"]).lower()) for p in res["phases"]]
    rj = run_s9.rejudge_case(path, write=False)
    chk = rj["p3b"]["checks"]
    peak = pmt.record_moving_peak(path)
    cur = peak["current"]
    with np.load(path / "record" / "record.npz", allow_pickle=False) as z:
        reading = np.asarray(z["meas.stroke"]) * 1e3
    return {"dir": str(path), "t_stop_s": t_stop - t0, "events_fault_warn": [[round(x - t0, 2), n] for x, n in events if n.startswith(("FAULT", "WARN"))],
            "FAULT_STROKE_END": sum(n.startswith("FAULT_STROKE_END") for _, n in events), "ready_count": sum(n == "ready" for _, n in phases),
            "final_phase": phases[-1][1], "phases": [[round(x, 2), n] for x, n in phases],
            "touch_end_s": next(x for x, n in phases if n == "level"),
            "crawler": crawler_block(t, c, t_stop, patches), "F_at_stop_kN": F[k].round(3).tolist(),
            "F_min_after_stop_kN": F[k:].min(axis=0).round(3).tolist(), "F_min_after_stop_all_kN": float(F[k:].min()),
            "F_end_kN": F[-1].round(3).tolist(), "F_min_clause_pass": bool(F[k:].min() >= F_MIN_KN), "pad_min_after_stop_kN": float(pad[k:].min()),
            "moving_bar": cur["max_bar"], "moving_leg": cur.get("leg"), "saturation": (res.get("monitor") or {}).get("saturation_step_count"),
            "end_roll_pitch_deg": rp[-1000:].mean(axis=0).round(4).tolist(), "stroke_reading_max_mm": reading.max(axis=0).round(3).tolist(),
            "guard_margin_mm": 682.8 - float(reading.max()),
            "P3_2_s": chk["P3-2_loc_minus_departure_s"], "P3_1_recontact_pass": chk["P3-1_recontact_pass"],
            "rejudge_blocks_equal": rj["unchanged_blocks_equal"], "params_match": rj["params_file_match"],
            "has_flow_limit": bool(res.get("flow_limit")), "flow_args": {k2: v for k2, v in (res.get("args") or {}).items() if k2.startswith("flow_") and v is not None},
            "code_git": (res.get("code_state") or {}).get("git_at_start", {}).get("head"), "files_at_start": (res.get("code_state") or {}).get("files_at_start")}


def first_diff(path_a: Path, path_b: Path) -> dict:
    t0 = json.loads((path_a / "result.json").read_text(encoding="utf-8"))["t_loop_start_s"]
    out = {}
    with np.load(path_a / "step_series.npz", allow_pickle=False) as a, np.load(path_b / "step_series.npz", allow_pickle=False) as b:
        for key in ("F_cyl_N", "s_motor_m", "scm_crawler_normal_N"):
            same = (a[key] == b[key]).reshape(len(a[key]), -1).all(axis=1)
            out[key] = None if same.all() else float(a["t_s"][int(np.argmin(same))] - t0)
    with np.load(path_a / "controller_commands.npz", allow_pickle=False) as a, np.load(path_b / "controller_commands.npz", allow_pickle=False) as b:
        same = (a["issued_u_m_s"] == b["issued_u_m_s"]).all(axis=1)
        out["issued_u"] = None if same.all() else float(a["t_s"][int(np.argmin(same))] - t0)
    return out


def main() -> None:
    import paper_max_pressure_table as pmt
    import run_S9

    scratch = Path(sys.argv[1])
    runs = {name: run_block(name, path, run_S9, pmt) for name, path in RUNS.items()}
    wrappers = {name: json.loads((RUNS[name] / "eps_wrapper.json").read_text(encoding="utf-8")) for name in ("off_eps1e-3", "off_eps2e-3")}
    variants_pass = [runs[n]["crawler"]["clause_pass"] for n in ("off_eps1e-3", "off_eps2e-3")]
    spread = {}
    for key in ("at_stop_kN", "max_after_kN", "end_kN", "limit_kN", "rise_kN", "t_since_last_below_0p01W_s"):
        v = [runs[n]["crawler"][key] for n in OFF_RUNS]
        spread[key] = {"min": min(v), "max": max(v), "range": max(v) - min(v), "on": runs["on_stored"]["crawler"][key]}
    for key in ("F_min_after_stop_all_kN", "moving_bar", "t_stop_s", "guard_margin_mm"):
        v = [runs[n][key] for n in OFF_RUNS]
        spread[key] = {"min": min(v), "max": max(v), "range": max(v) - min(v), "on": runs["on_stored"][key]}
    rule = ("one_off_variant_fails_clause_limit" if not all(variants_pass) else "both_pass_run_on_variants")
    out = {"criteria_sha256": SHA, "rule_user_before_result": "any of the 2 off variants fails the clause: saturation attribution broken, not a flip, record as a clause limit; both pass: 2 on variants with the same wrapper",
           "variants_clause_pass": dict(zip(("off_eps1e-3", "off_eps2e-3"), variants_pass, strict=True)), "rule_outcome": rule,
           "runs": runs, "spread_off_3_runs": spread,
           "wrapper_state": {n: {"eps": w["eps"], "gate_s": w["gate_s"], "state": w["state"], "env": w["env"]} for n, w in wrappers.items()},
           "first_diff_vs_stored_off": {n: first_diff(RUNS[n], RUNS["off_stored"]) for n in ("off_eps1e-3", "off_eps2e-3")}}
    jl_path = HERE / "xcheck_s8off_julia.json"
    if jl_path.exists():
        jl = json.loads(jl_path.read_text(encoding="utf-8"))
        diffs = {}
        for n, r in runs.items():
            for key, a, b in (("at_stop", jl[n]["crawler_at_stop_kN"], r["crawler"]["at_stop_kN"]), ("max_after", jl[n]["crawler_max_after_kN"], r["crawler"]["max_after_kN"]),
                              ("end", jl[n]["crawler_end_kN"], r["crawler"]["end_kN"]), ("F_min_after_stop", min(jl[n]["F_min_after_stop_kN"]), r["F_min_after_stop_all_kN"])):
                diffs[f"{n}_{key}"] = abs(a - b) / abs(b)
        out["xcheck_python_julia"] = {"worst_relative_diff": max(diffs.values()), "clause_same": {n: [jl[n]["clause_pass"], runs[n]["crawler"]["clause_pass"]] for n in runs},
                                      "t_stop_abs_s_julia": {n: jl[n]["t_stop_abs_s"] for n in runs}, "grade": "match" if max(diffs.values()) <= 1e-9 else "check"}
    out["conclusion"] = {
        "status": "HOLD_ON_VARIANTS" if all(variants_pass) else "CLAUSE_LIMIT_RECORD",
        "literal_verdict_unchanged": "stored on run fails the clause as written (10.43 > 8.95 kN); the sealed criteria are not changed",
        "T2": "candidate stays open", "F5": "candidate stays open", "condition_10_1_5": "off variants do not break the attribution; not proven either, off samples did not reach the on sampling phase",
        "D5_auto_switch": {"no_failure_in_10_rows": False, "reason": "S8 candidate open"},
        "next_by_user_rule": "2 on variants with the same wrapper; the wrapper refuses a flow-on run as written"}
    (HERE / "s8off_verdict.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({"rule": out["rule_outcome"], "xcheck": out.get("xcheck_python_julia")}, indent=0, default=float))
    for n, r in runs.items():
        print(n, json.dumps({k: r["crawler"][k] for k in ("crawler_peaks", "analysis_reference_at_fixed_delay_after_0p01W_crossing", "t_since_last_below_0p01W_s")}, default=float))
        with np.load(RUNS[n] / "step_series.npz", allow_pickle=False) as z:
            np.savetxt(scratch / f"s8off_{n}.csv", np.column_stack([z["t_s"], z["scm_crawler_normal_N"], z["F_cyl_N"]]), delimiter=",", fmt="%.17g",
                       header="t_s,crawler_N,F_FL_N,F_FR_N,F_RL_N,F_RR_N", comments="")


if __name__ == "__main__":
    main()
