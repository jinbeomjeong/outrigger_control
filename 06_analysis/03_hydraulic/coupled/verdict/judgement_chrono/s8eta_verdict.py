"""S8 SA-4 clause at eta_v 0.90 and 0.925 next to the off and eta_v 0.85 runs; flow audit items and the expected values.

Same calculation as s8on_verdict.py (run_block, phase_block). Adds the flow summary (limit time, deficit integral at the end, audit
items). The eps variants' flow_series hold values before the scaling, so their deficit integral leaves out the eps part. Reads the run
folders only. Writes s8eta_verdict.json; exports CSV for xcheck_s8eta.jl to argv[1]. Second run reads xcheck_s8eta_julia.json.

Run: conda run -n dynamics-dev python -I s8eta_verdict.py <scratch folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono")
sys.path.insert(0, str(HERE))
import s8off_verdict as base  # noqa: E402
import s8on_verdict as prev  # noqa: E402

S9 = base.S9
CASE = base.CASE
RUNS = dict(prev.RUNS)
RUNS["on_eta0.90"] = S9 / "batch_s8_eta090_20261105" / CASE
RUNS["on_eta0.925"] = S9 / "batch_s8_eta0925_20261105" / CASE
LEGS = ("FL", "FR", "RL", "RR")
OFF = ("off_stored", "off_eps1e-3", "off_eps2e-3")
ON85 = ("on_stored", "on_eps1e-3", "on_eps2e-3")
NEW = ("on_eta0.90", "on_eta0.925")
EXPECTED_0P90 = {"supply_L_min": 54.18, "front_rear_mm_s": [19.78, 19.88], "short_s": 15.2, "first_limited_abs_s": 13.22, "last_limited_abs_s": 28.4,
                 "max_deficit_L_min": 3.01, "deficit_end_mm": 16.0, "solved_steps": 152000, "touch_end_abs_s": [32.4, 32.5], "loc_abs_s": 41.6, "fault_abs_s": 49.4,
                 "r_range": [0.945, 0.950], "by_phase": "touch only", "audit_mismatches": 0, "demand_met_but_limited": 0, "over_supply": 0.0}


def flow_block(path: Path) -> dict | None:
    res = json.loads((path / "result.json").read_text(encoding="utf-8"))
    fl = res.get("flow_limit")
    if not fl:
        return None
    su = fl["summary"]
    t0 = float(res["t_loop_start_s"])
    with np.load(path / "flow_series.npz", allow_pickle=True) as z:
        rows, cols = z["rows"], [str(c) for c in z["columns"]]
        supply = float(z["supply_m3_s"])
    idx = {c: i for i, c in enumerate(cols)}
    t = rows[:, idx["t"]]
    limited = rows[:, idx["limited_mask"]].astype(int) > 0
    dt = float(np.median(np.diff(t)))
    edges = np.diff(np.concatenate(([0], limited.astype(int), [0])))
    spans = [[round(float(t[a]), 3), round(float(t[b - 1]), 3)] for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]
    k0, k1 = (int(np.searchsorted(t, x)) for x in (15.0, 27.0))  # absolute time, inside the limit span of every eta_v
    v = rows[k0:k1, [idx[f"v_{leg}"] for leg in LEGS]].mean(axis=0) * 1e3
    q = rows[:, idx["Q_sum"]] if "Q_sum" in idx else None
    return {"eta_v": fl["setting"]["eta_v"], "supply_L_min": supply * 6e4, "short_s": su["short_s"], "limited_s_recomputed": float(limited.sum() * dt),
            "by_phase": {k: x["short_s"] for k, x in su["by_phase"].items() if x["short_s"] > 0}, "max_deficit_L_min": su["max_deficit_L_min"],
            "deficit_end_mm": dict(zip(LEGS, (rows[-1, [idx[f"deficit_integral_{leg}"] for leg in LEGS]] * 1e3).round(3).tolist(), strict=True)),
            "tracking": su["tracking"], "limited_sets": su["limited_sets"], "limited_spans_ge_0p5s_abs": [s for s in spans if s[1] - s[0] >= 0.5], "n_limited_spans": len(spans),
            "first_limited_abs_s": spans[0][0] if spans else None, "last_limited_abs_s": spans[-1][1] if spans else None,
            "delivered_15_27s_abs_mm_s": v.round(4).tolist(), "t0": t0,
            "min_r_by_phase": {leg: x["min_r_by_phase"] for leg, x in su["speed_ratio"].items()}, "long93_s": {leg: x["longest_below_0p93_s"] for leg, x in su["speed_ratio"].items()},
            "disjoint_swaps": su["residual_groups"]["disjoint_swaps"],
            "audit_mismatches": su["steps"]["audit_mismatches"], "demand_met_but_limited": su["steps"]["demand_met_but_limited"], "solved_steps": su["steps"]["solved"],
            "max_sum_Q_over_supply_minus_1": su["max_sum_Q_over_supply_minus_1"], "Q_sum_over_supply_max_recomputed": None if q is None else float(q.max() / supply - 1.0)}


def main() -> None:
    import paper_max_pressure_table as pmt
    import run_S9

    scratch = Path(sys.argv[1])
    runs = {n: base.run_block(n, p, run_S9, pmt) for n, p in RUNS.items()}
    phase = {n: prev.phase_block(p) for n, p in RUNS.items()}
    flow = {n: flow_block(p) for n, p in RUNS.items()}
    results = {n: json.loads((p / "result.json").read_text(encoding="utf-8")) for n, p in RUNS.items()}
    loc = {n: [round(float(e["t_s"]), 2) for e in r["events"] if e["name"] == "crawler_liftoff_confirmed"] for n, r in results.items()}
    args_diff = {n: base_diff(results["on_stored"]["args"], results[n]["args"]) for n in NEW}
    ranges = {}
    for key, getter in (("at_stop_kN", lambda r: r["crawler"]["at_stop_kN"]), ("max_after_kN", lambda r: r["crawler"]["max_after_kN"]), ("rise_kN", lambda r: r["crawler"]["rise_kN"]),
                        ("margin_kN", lambda r: r["crawler"]["margin_kN"]), ("end_kN", lambda r: r["crawler"]["end_kN"]), ("F_min_after_stop_kN", lambda r: r["F_min_after_stop_all_kN"]),
                        ("moving_bar", lambda r: r["moving_bar"]), ("guard_margin_mm", lambda r: r["guard_margin_mm"])):
        off = [getter(runs[n]) for n in OFF]
        on = [getter(runs[n]) for n in ON85]
        ranges[key] = {"off": [min(off), max(off)], "on_0p85": [min(on), max(on)]}
        for n in NEW:
            v = getter(runs[n])
            ranges[key][n] = {"value": v, "in_off": min(off) <= v <= max(off), "in_on_0p85": min(on) <= v <= max(on)}
    for n in phase:
        phase[n]["stop_minus_touch_end_s"] = round(runs[n]["t_stop_s"] - phase[n]["touch_end_s"], 2)
    stored_series = [runs[n]["crawler"]["max_after_kN"] for n in ("on_stored", "on_eta0.90", "on_eta0.925", "off_stored")]
    diffs = np.diff(stored_series)
    out = {"criteria_sha256": base.SHA,
           "rule": "does not change the F-5 confirmation; records the efficiency boundary only; one run per efficiency cannot separate the phase scatter",
           "clause_pass": {n: runs[n]["crawler"]["clause_pass"] for n in RUNS}, "runs": runs, "phase": phase, "flow": flow, "loc_abs_s": loc, "args_diff_vs_on_stored": args_diff, "ranges": ranges,
           "max_after_by_eta": {"eta": [0.85, 0.90, 0.925, "0.95 = off, no Chrono at 0.95"], "stored_phase_only_kN": stored_series, "monotone_decreasing_stored_phase": bool((diffs <= 0).all()),
                                "on_0p85_all_kN": [runs[n]["crawler"]["max_after_kN"] for n in ON85]},
           "eta_0p95": "no Chrono run: four-leg v_max demand equals the supply, offline limit time 0, recorded as equal to off",
           "expected_eta_0p90": EXPECTED_0P90, "expected_eta_0p925": None}
    jl_path = HERE / "xcheck_s8eta_julia.json"
    if jl_path.exists():
        jl = json.loads(jl_path.read_text(encoding="utf-8"))
        d = {}
        for n in NEW:
            r = runs[n]
            for key, a, b in (("at_stop", jl[n]["crawler_at_stop_kN"], r["crawler"]["at_stop_kN"]), ("max_after", jl[n]["crawler_max_after_kN"], r["crawler"]["max_after_kN"]),
                              ("end", jl[n]["crawler_end_kN"], r["crawler"]["end_kN"]), ("F_min_after_stop", min(jl[n]["F_min_after_stop_kN"]), r["F_min_after_stop_all_kN"])):
                d[f"{n}_{key}"] = abs(a - b) / abs(b)
        out["xcheck_python_julia"] = {"worst_relative_diff": max(d.values()), "clause_same": {n: [jl[n]["clause_pass"], runs[n]["crawler"]["clause_pass"]] for n in NEW}, "grade": "match" if max(d.values()) <= 1e-9 else "check"}
    (HERE / "s8eta_verdict.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("clause_pass", "loc_abs_s", "args_diff_vs_on_stored", "ranges", "max_after_by_eta")}, default=float))
    print("xcheck", json.dumps(out.get("xcheck_python_julia"), default=float))
    for n in NEW + ("on_stored",):
        print(n, "flow", json.dumps(flow[n], default=float))
    for n in RUNS:
        r = runs[n]
        c = r["crawler"]
        print(n, json.dumps({"stop": r["t_stop_s"], "ref": c["at_stop_kN"], "slope": c["slope_at_stop_kN_s"], "since": c["t_since_last_below_0p01W_s"], "lim": c["limit_kN"], "max": c["max_after_kN"], "tmax": c["max_after_t_after_stop_s"], "margin": c["margin_kN"], "end": c["end_kN"],
                             "pass": c["clause_pass"], "legs": r["F_min_after_stop_kN"], "bar": r["moving_bar"], "guard": r["guard_margin_mm"], "ev": r["events_fault_warn"], "FSE": r["FAULT_STROKE_END"], "ready": r["ready_count"], "sat": r["saturation"], "roll": r["end_roll_pitch_deg"], "last_zero": c["last_zero_before_stop_s"],
                             "max1s": c["max_1s_before_kN"], "phase": phase[n]}, default=float))
    for n in NEW:
        with np.load(RUNS[n] / "step_series.npz", allow_pickle=False) as z:
            np.savetxt(scratch / f"s8eta_{n}.csv", np.column_stack([z["t_s"], z["scm_crawler_normal_N"], z["F_cyl_N"]]), delimiter=",", fmt="%.17g",
                       header="t_s,crawler_N,F_FL_N,F_FR_N,F_RL_N,F_RR_N", comments="")


def base_diff(a: dict, b: dict) -> dict:
    return {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


if __name__ == "__main__":
    main()
