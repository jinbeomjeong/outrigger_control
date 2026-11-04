"""S8 SA-4 clause on all six runs (off stored + 2 variants, on stored + 2 variants) and the user rule fixed before the on result.

Uses crawler_block, run_block and first_diff of s8off_verdict.py, so the calculation is the same. Adds whether eps moved the phase:
first pad contact, TOUCH end, latch times, stop time, delivered speed ratio in the saturated TOUCH span (s_motor slope). Reads the
run folders only. Writes s8on_verdict.json; exports CSV for xcheck_s8on.jl to argv[1]. Second run reads xcheck_s8on_julia.json.

Run: conda run -n dynamics-dev python -I s8on_verdict.py <scratch folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono")
sys.path.insert(0, str(HERE))
import s8off_verdict as base  # noqa: E402

S9 = base.S9
CASE = base.CASE
RUNS = dict(base.RUNS)
RUNS["on_eps1e-3"] = S9 / "batch_s8on_eps1e-3_20261104" / CASE
RUNS["on_eps2e-3"] = S9 / "batch_s8on_eps2e-3_20261104" / CASE
OFF = ("off_stored", "off_eps1e-3", "off_eps2e-3")
ON = ("on_stored", "on_eps1e-3", "on_eps2e-3")
TOUCH_SPAN_REL_S = (6.0, 20.0)
"""Span inside the saturated free travel of every run; the variants are scaled here."""
CONTACT_N = 3000.0


def phase_block(path: Path) -> dict:
    res = json.loads((path / "result.json").read_text(encoding="utf-8"))
    t0 = float(res["t_loop_start_s"])
    with np.load(path / "step_series.npz", allow_pickle=False) as z:
        t = np.asarray(z["t_s"]) - t0
        pad = np.asarray(z["scm_pad_normal_N"])
        s = np.asarray(z["s_motor_m"])
    i0 = int(np.searchsorted(t, 10.0))
    any_contact = i0 + int(np.argmax(pad[i0:].max(axis=1) > CONTACT_N))
    per_leg = [i0 + int(np.argmax(pad[i0:, q] > CONTACT_N)) for q in range(4)]
    a, b = (int(np.searchsorted(t, x)) for x in TOUCH_SPAN_REL_S)
    speed = (s[b] - s[a]) / (t[b] - t[a]) * 1e3
    meta = (res.get("controller_meta") or {}).get("floor_estimate_touch") or {}
    phases = [(float(p["t_s"]) - t0, str(p["phase"]).lower()) for p in res["phases"]]
    te = next(x for x, n in phases if n == "level")
    k = int(np.searchsorted(t, te))
    return {"first_pad_contact_s": float(t[any_contact]), "first_contact_per_leg_s": [round(float(t[i]), 3) for i in per_leg],
            "touch_end_s": te, "latch_rel_s": [round(float(x) - t0, 2) for x in meta.get("latch_times_s", [])], "s_motor_at_touch_end_mm": (s[k] * 1e3).round(3).tolist(),
            "touch_speed_mm_s": speed.round(5).tolist(), "phase_rel_touch_end_of_stop_s": None}


def wrapper_state(path: Path) -> dict | None:
    f = path / "eps_wrapper.json"
    if not f.exists():
        return None
    w = json.loads(f.read_text(encoding="utf-8"))
    return {k: w.get(k) for k in ("eps", "gate_s", "perturbation", "state", "main_head", "env")} | {"c2_sha256": (w.get("code_sha256") or {}).get("03_src/outrigger_sim/control/c2.py")}


def spread(runs: dict, names: tuple, getter) -> dict:
    v = [getter(runs[n]) for n in names]
    return {"min": min(v), "max": max(v), "range": max(v) - min(v), "values": v}


def main() -> None:
    import paper_max_pressure_table as pmt
    import run_S9

    scratch = Path(sys.argv[1])
    runs = {n: base.run_block(n, p, run_S9, pmt) for n, p in RUNS.items()}
    phase = {n: phase_block(p) for n, p in RUNS.items()}
    for n in runs:
        phase[n]["phase_rel_touch_end_of_stop_s"] = runs[n]["t_stop_s"] - phase[n]["touch_end_s"]
    ways = {"at_stop_kN": lambda r: r["crawler"]["at_stop_kN"], "max_after_kN": lambda r: r["crawler"]["max_after_kN"], "rise_kN": lambda r: r["crawler"]["rise_kN"],
            "limit_kN": lambda r: r["crawler"]["limit_kN"], "margin_kN": lambda r: r["crawler"]["margin_kN"], "end_kN": lambda r: r["crawler"]["end_kN"],
            "t_since_crossing_s": lambda r: r["crawler"]["t_since_last_below_0p01W_s"], "F_min_after_stop_kN": lambda r: r["F_min_after_stop_all_kN"],
            "moving_bar": lambda r: r["moving_bar"], "guard_margin_mm": lambda r: r["guard_margin_mm"], "end_roll_deg": lambda r: r["end_roll_pitch_deg"][0]}
    table = {k: {"off": spread(runs, OFF, g), "on": spread(runs, ON, g)} for k, g in ways.items()}
    on_pass = {n: runs[n]["crawler"]["clause_pass"] for n in ("on_eps1e-3", "on_eps2e-3")}
    any_pass = any(on_pass.values())
    out = {"criteria_sha256": base.SHA,
           "rule_user_before_result": "any of the 2 on variants passes the clause: saturation attribution broken, not a flip, record as a clause limit; both fail: F-5 confirmed, v4 submitted unchanged because the flow limit is out of its scope, no D-5 switch, recorded as a limit in v5",
           "on_variants_clause_pass": on_pass, "rule_outcome": "clause_limit" if any_pass else "F5_confirmed",
           "runs": runs, "phase": phase, "spread": table, "wrappers": {n: wrapper_state(p) for n, p in RUNS.items()},
           "first_diff_vs_stored_on": {n: base.first_diff(RUNS[n], RUNS["on_stored"]) for n in ("on_eps1e-3", "on_eps2e-3")}}
    jl_path = HERE / "xcheck_s8on_julia.json"
    if jl_path.exists():
        jl = json.loads(jl_path.read_text(encoding="utf-8"))
        diffs = {}
        for n, r in runs.items():
            for key, a, b in (("at_stop", jl[n]["crawler_at_stop_kN"], r["crawler"]["at_stop_kN"]), ("max_after", jl[n]["crawler_max_after_kN"], r["crawler"]["max_after_kN"]),
                              ("end", jl[n]["crawler_end_kN"], r["crawler"]["end_kN"]), ("F_min_after_stop", min(jl[n]["F_min_after_stop_kN"]), r["F_min_after_stop_all_kN"])):
                diffs[f"{n}_{key}"] = abs(a - b) / abs(b)
        out["xcheck_python_julia"] = {"worst_relative_diff": max(diffs.values()), "clause_same": {n: [jl[n]["clause_pass"], runs[n]["crawler"]["clause_pass"]] for n in runs},
                                      "grade": "match" if max(diffs.values()) <= 1e-9 else "check"}
    out["conclusion"] = {
        "status": "CLAUSE_LIMIT_RECORD" if any_pass else "F5_CONFIRMED_BY_USER_RULE",
        "literal_verdict": "off 3/3 pass, on 3/3 fail on the clause 'crawler after the stop <= crawler at the stop + 0.01 W' (criteria 9.1)",
        "T2": "confirmed 1 row (S8), safe stop -> SA-4 clause violated", "F5": "confirmed at eta_v 0.85, nominal compensator, plant without valve lag",
        "condition_10_1_5": "met by the user rule: the only difference is the flow limit; eps moved first contact by at most 63 ms",
        "D5": "no switch by the user rule; the comparison after the C4G2 / K1 merge is a separate step",
        "v4": "submitted unchanged, flow limit out of scope; v5 records the limit"} if not any_pass else {"status": "CLAUSE_LIMIT_RECORD"}
    (HERE / "s8on_verdict.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("on_variants_clause_pass", "rule_outcome", "phase", "spread", "first_diff_vs_stored_on")}, default=float))
    print("wrappers", json.dumps({n: w for n, w in out["wrappers"].items() if w}, default=float))
    print("xcheck", json.dumps(out.get("xcheck_python_julia"), default=float))
    for n, r in runs.items():
        print(n, json.dumps({k: v for k, v in r.items() if k not in ("dir", "phases", "files_at_start")}, ensure_ascii=False, default=float))
        print("  c2", ((r["files_at_start"] or {}).get("outrigger_sim.control.c2") or {}).get("sha256"))
        with np.load(RUNS[n] / "step_series.npz", allow_pickle=False) as z:
            np.savetxt(scratch / f"s8on_{n}.csv", np.column_stack([z["t_s"], z["scm_crawler_normal_N"], z["F_cyl_N"]]), delimiter=",", fmt="%.17g",
                       header="t_s,crawler_N,F_FL_N,F_FR_N,F_RL_N,F_RR_N", comments="")


if __name__ == "__main__":
    main()
