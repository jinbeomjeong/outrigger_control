"""Spec rev. 75 draft: judgement of the G6 Chrono (S9 SCM, soil patch under one pad) runs.

Per case (result.json p3b / p3b_ext of run_S9.py):
  G6-1 = P3-1 (crawler zero READY..+10 s, no re-contact; U-S9-G6d (a): a re-contact recorded in
  p3b.P3-1_crawler.recontact_events (or result_rejudge_U-S9-G6d.json) with pass = true is a FLAG), G6-2 = P3-2 within (LOC before first DONE, not loaded,
  LOC - departure <= limit), G6-3 = P3-3 within (true F_cyl >= F_min after the departure), G6-4 = P3-4 within_0p2,
  G6-5 = P3-5 (rut clearance from the first READY >= 25 mm, stroke <= 684.8 mm), G6-6 = no FAULT and READY reached,
  G6-7 = P3-8 (no re-approach / P5 / probe abort before the LOC) with the decision-2 / U-S9-G6c FLAG rules
  (pre-LOC re-approach: started leg true minimum >= F_min -> P3-8_demoted; < F_min with G6-3 passed and no FAULT ->
  P3-8_preloc_loss), READY <= 120 s after the loop start (P-S8-29 acceptance), P3-6 / P3-7 / P3-9 recorded.
Records: P-S8-28/29/30 event counts, LOC - departure, completion blocking shares, virgin-branch flag, pad sinkage,
settle reference (must equal the P3b reference of the same base: dynamics), and an optional comparison with a
reference run (P3b case): commands (10 Hz issued u) max difference, 1 ms truth max differences (F_cyl, attitude,
z_origin, crawler normal) over the common time, phase times.

READY-less runs (counterfactual noTR, 2026-10-28): G6-4, G6-5, G6-6 and READY <= 120 s are
"not judgeable" (listed in not_judgeable_gates) and counted as failed, so a --expect case
classifies them as expected failures; G6-1 uses the crawler normal maximum from the departure
confirmation to the end (= 0 N) in place of the READY .. READY + 10 s window (crawler_zero_rule).

Record rows, not gates (G6P, cad-expert / control-expert 2026-10-28):
  relax_settings = the P-S8-29 relaxation settings (c2_setup.twist_relax of the G6P runs,
    else the controller record twist_relax) with n_relaxed_done and last_D_N;
  after_ready (READY reached) = D_raw at DONE / READY, |D| max and end after READY
    (completion_series, 10 Hz) and the per-leg true F_cyl minimum after READY (step_series,
    1 kHz) against F_min of the YAML;
  end_of_run = last phase, end D_raw, log-linear decay rate of |D| in LEVEL from LOC + 10 s on,
    soft-pad end sinkage and its last 0.2 s rate, last 10 s per-leg F_cyl minimum;
  expected_fail = a counterfactual case's expected failing gates (--expect), kept out of the
    overall pass count (summary).
Record-row times are relative to the loop start (npz t_s is absolute: t_rel = t_s - t_loop_start_s).

Usage: python -I r76_g6_chrono_judge.py <out_json> <case dir> [<case dir> ...]
       [--ref <case>=<ref dir> ...] [--expect <case>=<gate>,<gate> ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

READY_MAX_S = 120.0
PARAMS_YAML = Path(__file__).resolve().parents[3] / "02_params" / "rexome33.yaml"
LEG_NAMES = ("FL", "FR", "RL", "RR")
SAMPLE_TIME_TOL_S = 1e-9
DECAY_START_AFTER_LOC_S = 10.0
DECAY_MIN_ABS_D_N = 1000.0
END_WINDOW_S = 10.0
TWIST_RELAX_EVENT = "INFO_TWIST_UNSETTLED"
RUT_CLEARANCE_MIN_M = 0.025
# Gates whose window starts at READY: without READY they are "not judgeable" and count as failed.
READY_DEPENDENT_GATES = ("G6-4_att", "G6-5_rut_stroke", "G6-6_fault_ready", "READY_le_120s")
CRAWLER_ZERO_READY_RULE = "P3-1_crawler.crawler_zero (READY .. READY + 10 s)"
CRAWLER_ZERO_NO_READY_RULE = (
    "no READY: departure.crawler_normal_max_after_confirm_N == 0 (departure confirmation .. end)")


def load(d):
    return json.loads((Path(d) / "result.json").read_text(encoding="utf-8"))


def load_f_min_N(params_path: Path = PARAMS_YAML) -> float:
    """F_min [N] of the single parameter source (``control.F_min_cylinder_N``)."""
    params = yaml.safe_load(params_path.read_text(encoding="utf-8"))
    return float(params["control"]["F_min_cylinder_N"])


def _round_or_none(value: float | None, digits: int) -> float | None:
    return None if value is None else round(float(value), digits)


def _kN(value_N: float | None) -> float | None:
    return None if value_N is None else round(float(value_N) / 1e3, 3)


def _first_index_at_or_after(times_s: np.ndarray, t_s: float) -> int | None:
    index = int(np.searchsorted(times_s, t_s - SAMPLE_TIME_TOL_S))
    return index if index < len(times_s) else None


def _last_finite(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    return float(finite[-1]) if finite.size else None


def _value_at(times_s: np.ndarray, values: np.ndarray, t_s: float | None) -> float | None:
    """Value of the first sample at or after ``t_s`` (the sample the controller acted on)."""
    if t_s is None:
        return None
    index = _first_index_at_or_after(times_s, t_s)
    return None if index is None else float(values[index])


def _relax_record(result: dict[str, Any]) -> dict[str, Any]:
    """P-S8-29 relaxation provenance: settings (G6P: c2_setup.twist_relax, older runs: the
    controller record) and the controller's relaxed-DONE count and last relaxed |D|."""
    setup = (result.get("c2_setup") or {}).get("twist_relax")
    controller = (result.get("controller_meta") or {}).get("twist_relax") or {}
    source = setup if setup is not None else controller
    n_events = sum(1 for e in result.get("events") or [] if e["name"].startswith(TWIST_RELAX_EVENT))
    return {
        "source": "c2_setup.twist_relax" if setup is not None else "controller_meta.twist_relax",
        "mode": source.get("mode"), "overrides": source.get("overrides"),
        "settings": source.get("settings"),
        "n_relaxed_done": controller.get("n_relaxed_done"),
        "n_info_twist_unsettled_events": n_events,
        "last_D_N": controller.get("last_D_N"),
    }


def _per_leg_minimum(times_s: np.ndarray, forces_N: np.ndarray, t_loop_start_s: float,
                     f_min_N: float) -> dict[str, dict[str, float]]:
    """Per-leg minimum of the true cylinder force over the given samples, with its loop time."""
    out = {}
    for leg_index, leg in enumerate(LEG_NAMES):
        sample = int(np.argmin(forces_N[:, leg_index]))
        minimum_N = float(forces_N[sample, leg_index])
        out[leg] = {"min_kN": _kN(minimum_N),
                    "t_rel_s": round(float(times_s[sample]) - t_loop_start_s, 3),
                    "ratio_to_F_min": round(minimum_N / f_min_N, 3)}
    return out


def _last_done_before(phases: list[dict[str, Any]], t_ready_abs_s: float) -> float | None:
    done_times = [ph["t_s"] for ph in phases
                  if ph["phase"] == "done" and ph["t_s"] <= t_ready_abs_s + SAMPLE_TIME_TOL_S]
    return done_times[-1] if done_times else None


def _after_ready_record(result: dict[str, Any], completion: Any, steps: Any,
                        f_min_N: float) -> dict[str, Any] | None:
    """Twist and leg loads after the first READY (None when READY was not reached)."""
    t_loop_start_s = result["p3b"]["t_loop_start_s"]
    t_ready_rel_s = result["p3b"]["P3-6_ready"]["t_ready_after_loop_start_s"]
    if t_ready_rel_s is None:
        return None
    t_ready_abs_s = t_loop_start_s + t_ready_rel_s
    t_done_abs_s = _last_done_before(result.get("phases") or [], t_ready_abs_s)
    d_times_s, d_raw_N = completion["t_s"], completion["D_raw_N"]
    d_after = d_raw_N[d_times_s >= t_ready_abs_s - SAMPLE_TIME_TOL_S]
    finite_after = d_after[np.isfinite(d_after)]
    absmax_after_N = float(np.max(np.abs(finite_after))) if finite_after.size else None
    step_mask = steps["t_s"] >= t_ready_abs_s - SAMPLE_TIME_TOL_S
    leg_minimum = _per_leg_minimum(steps["t_s"][step_mask], steps["F_cyl_N"][step_mask],
                                   t_loop_start_s, f_min_N)
    return {
        "t_ready_abs_s": t_ready_abs_s,
        "t_done_rel_s": None if t_done_abs_s is None else round(t_done_abs_s - t_loop_start_s, 3),
        "D_at_done_kN": _kN(_value_at(d_times_s, d_raw_N, t_done_abs_s)),
        "D_at_ready_kN": _kN(_value_at(d_times_s, d_raw_N, t_ready_abs_s)),
        "D_absmax_after_ready_kN": _kN(absmax_after_N),
        "D_end_kN": _kN(_last_finite(d_after)),
        "n_D_samples_after_ready": int(d_after.size),
        "window_after_ready_s": round(float(steps["t_s"][-1]) - t_ready_abs_s, 3),
        "F_cyl_min_after_ready": leg_minimum,
        "F_min_kN": _kN(f_min_N),
    }


def _log_linear_decay(result: dict[str, Any], completion: Any) -> dict[str, Any]:
    """Least-squares fit ln|D| = a - lambda t over the LEVEL samples from LOC + 10 s on with
    |D| >= 1 kN; lambda > 0 = |D| decays."""
    t_loc_s = result["p3b"]["P3-2_loc"].get("t_loc_s")
    record: dict[str, Any] = {
        "lambda_per_s": None, "n_samples": 0, "t_rel_range_s": None,
        "rule": "LEVEL, t >= t_LOC + 10 s, |D_raw| >= 1 kN, ln|D| least squares",
    }
    if t_loc_s is None:
        return record
    times_s, d_raw_N = completion["t_s"], completion["D_raw_N"]
    abs_d_N = np.abs(d_raw_N)
    mask = ((completion["phase"] == "level") & (times_s >= t_loc_s + DECAY_START_AFTER_LOC_S)
            & np.isfinite(abs_d_N) & (abs_d_N >= DECAY_MIN_ABS_D_N))
    record["n_samples"] = int(mask.sum())
    if record["n_samples"] < 2:
        return record
    slope, _ = np.polyfit(times_s[mask], np.log(abs_d_N[mask]), 1)
    t_loop_start_s = result["p3b"]["t_loop_start_s"]
    record["lambda_per_s"] = float(-slope)
    record["t_rel_range_s"] = [round(float(times_s[mask][0]) - t_loop_start_s, 3),
                               round(float(times_s[mask][-1]) - t_loop_start_s, 3)]
    return record


def _soft_leg(result: dict[str, Any]) -> str | None:
    soft = ((result.get("p3b_ext") or {}).get("pad_sinkage") or {}).get("soft_leg")
    if soft is None and isinstance((result.get("args") or {}).get("soil_patch"), str):
        soft = result["args"]["soil_patch"].split(":", 1)[0]  # args form "RR:J1"
    return soft if soft in LEG_NAMES else None


def _end_of_run_record(result: dict[str, Any], completion: Any, steps: Any,
                       f_min_N: float) -> dict[str, Any]:
    """State at the end of the run (the READY-less counterfactual ends here)."""
    t_loop_start_s = result["p3b"]["t_loop_start_s"]
    phases = result.get("phases") or []
    soft = _soft_leg(result)
    soft_record = None
    if soft is not None:
        leg_index = LEG_NAMES.index(soft)
        sinkage_end_m = float(steps["pad_sinkage_geometric_m"][-1, leg_index])
        sinkage_rate_m_s = float(steps["sinkage_rate_0p2s_m_s"][-1, leg_index])
        soft_record = {"leg": soft, "sinkage_end_mm": round(sinkage_end_m * 1e3, 3),
                       "sinkage_rate_last_0p2s_mm_s": round(sinkage_rate_m_s * 1e3, 5)}
    step_times_s = steps["t_s"]
    end_mask = step_times_s >= step_times_s[-1] - END_WINDOW_S
    return {
        "last_phase": phases[-1]["phase"] if phases else None,
        "last_phase_t_rel_s": round(phases[-1]["t_s"] - t_loop_start_s, 3) if phases else None,
        "t_end_rel_s": round(float(step_times_s[-1]) - t_loop_start_s, 3),
        "D_end_kN": _kN(_last_finite(completion["D_raw_N"])),
        "D_level_decay": _log_linear_decay(result, completion),
        "soft_pad": soft_record,
        "F_cyl_min_last_10s": _per_leg_minimum(step_times_s[end_mask], steps["F_cyl_N"][end_mask],
                                               t_loop_start_s, f_min_N),
    }


def record_rows(d: str | Path, result: dict[str, Any], f_min_N: float) -> dict[str, Any]:
    """G6P record rows (no gates) of one case directory.

    Args:
        d: Case directory with ``completion_series.npz`` and ``step_series.npz``.
        result: Its parsed ``result.json``.
        f_min_N: F_min [N] (YAML ``control.F_min_cylinder_N``).

    Returns:
        ``relax_settings``, ``after_ready`` (None without READY) and ``end_of_run``.
    """
    with np.load(Path(d) / "completion_series.npz", allow_pickle=False) as completion_file, \
            np.load(Path(d) / "step_series.npz", allow_pickle=False) as step_file:
        completion = {k: completion_file[k] for k in ("t_s", "D_raw_N", "phase")}
        steps = {k: step_file[k] for k in ("t_s", "F_cyl_N", "pad_sinkage_geometric_m",
                                           "sinkage_rate_0p2s_m_s")}
    return {
        "relax_settings": _relax_record(result),
        "after_ready": _after_ready_record(result, completion, steps, f_min_N),
        "end_of_run": _end_of_run_record(result, completion, steps, f_min_N),
    }


def expected_fail_record(gates: dict[str, bool], expected: list[str]) -> dict[str, Any]:
    """Compare a counterfactual case's gates with its expected failures (record only)."""
    failed = [name for name, ok in gates.items() if not ok]
    return {
        "expected_gates": list(expected),
        "failed_as_expected": [name for name in expected if name in failed],
        "expected_but_passed": [name for name in expected if name not in failed],
        "unexpected_failures": [name for name in failed if name not in expected],
        "as_expected": set(failed) == set(expected),
    }


def parse_expect(argument: str) -> tuple[str, list[str]]:
    """``<case>=<gate>,<gate>`` of ``--expect``."""
    case, _, gates = argument.partition("=")
    gate_names = [g.strip() for g in gates.split(",") if g.strip()]
    if not case or not gate_names:
        raise SystemExit(f"--expect needs <case>=<gate>[,<gate>...], got {argument!r}")
    return case, gate_names


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Overall pass count without the expected-fail (counterfactual) cases, listed apart."""
    regular = [j for j in cases if "expected_fail" not in j]
    counterfactual = [j for j in cases if "expected_fail" in j]
    as_expected = {j["case"]: j["expected_fail"]["as_expected"] for j in counterfactual}
    return {
        "n_regular": len(regular), "n_regular_pass": sum(1 for j in regular if j["pass"]),
        "regular_all_pass": all(j["pass"] for j in regular),
        "expected_fail_cases": as_expected,
    }


def crawler_zero_record(p3b: dict[str, Any]) -> tuple[bool, str]:
    """Crawler-zero part of G6-1 and the rule it came from.

    With READY the runner's ``P3-1_crawler.crawler_zero`` (READY .. READY + 10 s) is used.
    Without READY that window does not exist, so the zero is taken over the whole run after the
    departure confirmation (``departure.crawler_normal_max_after_confirm_N == 0``), a superset of
    the READY window (same rule as the r77 scratchpad wrapper, 2026-10-28).

    Raises:
        KeyError: READY was reached but the runner record has no ``crawler_zero``.
    """
    crawler = p3b["P3-1_crawler"]
    if "crawler_zero" in crawler:
        return bool(crawler["crawler_zero"]), CRAWLER_ZERO_READY_RULE
    if p3b["P3-6_ready"]["t_ready_after_loop_start_s"] is not None:
        raise KeyError("P3-1_crawler.crawler_zero missing although READY was reached")
    departure = p3b["departure"]
    is_zero = bool(departure.get("departed")
                   and departure.get("crawler_normal_max_after_confirm_N") == 0.0)
    return is_zero, CRAWLER_ZERO_NO_READY_RULE


def rut_stroke_ok(clearance_stroke: dict[str, Any]) -> bool:
    """G6-5: rut clearance from the first READY >= 25 mm and stroke within (False without READY)."""
    rut_min_m = clearance_stroke["rut_clearance_min_after_first_ready_m"]
    if rut_min_m is None:
        return False
    return bool(rut_min_m >= RUT_CLEARANCE_MIN_M and clearance_stroke["stroke_within"])


def not_judgeable_gates(t_ready_rel_s: float | None) -> list[str]:
    """Gates that need a READY entry; without READY they are failed as 'not judgeable'."""
    return [] if t_ready_rel_s is not None else list(READY_DEPENDENT_GATES)


def judge(d, f_min_N: float | None = None):
    r = load(d)
    p, x = r["p3b"], r.get("p3b_ext") or {}
    t0 = p["t_loop_start_s"]
    phases = [ph["phase"] for ph in r.get("phases") or []]
    names = [e["name"] for e in r.get("events") or []]
    fault = any(ph in ("fault", "fault_reground") for ph in phases) or any(n.startswith("FAULT") for n in names)
    ready = p["P3-6_ready"]["t_ready_after_loop_start_s"]
    p38 = p["P3-8_false_triggers"]
    p31 = p["P3-1_crawler"]
    rce = p31.get("recontact_events")
    rejudge = Path(d) / "result_rejudge_U-S9-G6d.json"
    if rce is None and rejudge.exists():
        rce = json.loads(rejudge.read_text(encoding="utf-8"))["p3b"]["P3-1_crawler"].get("recontact_events")
    flags = []
    if p31["recontact_count"] == 0:
        recontact_ok = True
    elif rce is not None:
        # U-S9-G6d (a), 2026-10-28: transient re-contact (<= 0.5 s, ended before the LOC, <= 0.15 W) -> FLAG
        recontact_ok = bool(rce.get("pass"))
        flags += list(rce.get("flags") or [])
    else:
        recontact_ok = False
    crawler_zero, crawler_zero_rule = crawler_zero_record(p)
    not_judgeable = not_judgeable_gates(ready)
    rut_min_m = p["P3-5_clearance_stroke"]["rut_clearance_min_after_first_ready_m"]
    g = {
        "G6-1_crawler": bool(crawler_zero and recontact_ok),
        "G6-2_loc": bool(p["P3-2_loc"]["within"]),
        "G6-3_Fmin": bool(p["P3-3_leg_force"]["within"]),
        "G6-4_att": bool(ready is not None and p["P3-4_attitude"]["within_0p2"]),
        "G6-5_rut_stroke": rut_stroke_ok(p["P3-5_clearance_stroke"]),
        "G6-6_fault_ready": bool(not fault and ready is not None),
        "G6-7_preloc": bool(p38["within"]),
        "READY_le_120s": bool(ready is not None and ready <= READY_MAX_S),
    }
    if not g["G6-7_preloc"]:
        # decision 2 / U-S9-G6c: needs the started leg's true minimum; the runner record lists the events only
        flags.append("P3-8_needs_leg_minimum")
    res = {
        "case": Path(d).name, "gates": g, "pass": all(g.values()), "flags": flags,
        "not_judgeable_gates": not_judgeable, "crawler_zero_rule": crawler_zero_rule,
        "recontact_events": rce,
        "t_ready_rel_s": ready, "loc_minus_departure_s": p["P3-2_loc"]["loc_minus_departure_s"],
        "loc_limit_s": p["P3-2_loc"]["limit_s"],
        "F_min_after_departure_kN": [round(v / 1e3, 2) for v in p["P3-3_leg_force"]["F_min_after_N"]],
        "attitude_p34_absmax_deg": p["P3-4_attitude"]["p34_absmax_overall_deg"],
        "end_mean_roll_pitch_deg": p["P3-4_attitude"]["end_mean_roll_pitch_deg"],
        "rut_min_after_ready_mm": None if rut_min_m is None else round(rut_min_m * 1e3, 2),
        "s_motor_max_mm": [round(v * 1e3, 2) for v in p["P3-5_clearance_stroke"]["s_motor_max_m"]],
        "P3-6": p["P3-6_ready"].get("within"), "P3-7": p.get("P3-7_plateau", {}).get("within"),
        "P3-9_flag": p.get("P3-9_deferred", {}).get("flag"),
        "pre_liftoff_flag": p.get("pre_liftoff_min_F_cyl", {}).get("any_flag"),
        "p38_counts": p38.get("counts"),
        "event_counts": x.get("event_counts"), "pause_times_rel_s": (x.get("event_times_rel_s") or {}).get(
            "INFO_LIFT_PAUSED"),
        "c_min_at_P_mm": None if x.get("c_min_at_P_m") is None else round(x["c_min_at_P_m"] * 1e3, 2),
        "loc_anchor_applied": x.get("loc_anchor_applied"),
        "completion": x.get("completion"), "pad_sinkage": x.get("pad_sinkage"),
        "virgin_branch_any": (x.get("virgin_branch") or {}).get("any_in_window"),
        "settle_reference": {k: r["settle_reference"][k] for k in ("roll_pitch_deg", "z_origin_m")},
        "phases_rel_s": [(round(ph["t_s"] - t0, 2), ph["phase"]) for ph in r.get("phases") or []],
        "events": [(round(e["t_s"] - t0, 2), e["name"]) for e in r.get("events") or []
                   if not e["name"].startswith("INFO_PRESSURE_ZERO")],
    }
    res.update(record_rows(d, r, load_f_min_N() if f_min_N is None else f_min_N))
    return res, r


def compare(d, ref):
    a, b = Path(d), Path(ref)
    ca, cb = np.load(a / "controller_commands.npz"), np.load(b / "controller_commands.npz")
    n = min(len(ca["t_s"]), len(cb["t_s"]))
    du = float(np.max(np.abs(ca["issued_u_m_s"][:n] - cb["issued_u_m_s"][:n])))
    first = np.flatnonzero(np.any(np.abs(ca["issued_u_m_s"][:n] - cb["issued_u_m_s"][:n]) > 1e-12, axis=1))
    sa, sb = np.load(a / "step_series.npz"), np.load(b / "step_series.npz")
    m = min(len(sa["t_s"]), len(sb["t_s"]))
    out = {"ref": b.name, "n_periods": int(n), "commands_max_abs_diff_m_s": du,
           "commands_first_diff_t_s": None if not first.size else float(ca["t_s"][first[0]]),
           "truth_max_abs_diff": {}}
    for k in ("F_cyl_N", "roll_pitch_deg", "z_origin_m", "scm_crawler_normal_N", "s_motor_m"):
        out["truth_max_abs_diff"][k] = float(np.max(np.abs(sa[k][:m] - sb[k][:m])))
    return out


def main():
    out = Path(sys.argv[1])
    cases, refs, expects = [], {}, {}
    it = iter(sys.argv[2:])
    for a in it:
        if a == "--ref":
            k, v = next(it).split("=", 1)
            refs[k] = v
        elif a == "--expect":
            k, gates = parse_expect(next(it))
            expects[k] = gates
        else:
            cases.append(a)
    unknown_cases = set(expects) - {Path(d).name for d in cases}
    if unknown_cases:
        raise SystemExit(f"--expect names cases not given: {sorted(unknown_cases)}")
    f_min_N = load_f_min_N()
    res = {"script": "04_scripts/03_control/s8/r76_g6_chrono_judge.py", "cases": []}
    for d in cases:
        j, r = judge(d, f_min_N)
        name = Path(d).name
        if name in expects:
            unknown_gates = set(expects[name]) - set(j["gates"])
            if unknown_gates:
                raise SystemExit(f"--expect {name}: unknown gates {sorted(unknown_gates)}")
            j["expected_fail"] = expected_fail_record(j["gates"], expects[name])
        if name in refs:
            j["vs_reference"] = compare(d, refs[name])
            rr = load(refs[name])
            j["vs_reference"]["ref_settle_reference"] = {k: rr["settle_reference"][k] for k in ("roll_pitch_deg",
                                                                                              "z_origin_m")}
            j["vs_reference"]["ref_phases"] = [(round(ph["t_s"] - rr["p3b"]["t_loop_start_s"], 2), ph["phase"])
                                               for ph in rr.get("phases") or []]
        res["cases"].append(j)
    res["summary"] = summarize(res["cases"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for j in res["cases"]:
        verdict = j["pass"]
        if "expected_fail" in j:
            verdict = f"expected fail (as expected: {j['expected_fail']['as_expected']})"
        print(j["case"], "pass", verdict, {k: v for k, v in j["gates"].items() if not v}, "READY",
              j["t_ready_rel_s"], "LOC-dep", _round_or_none(j["loc_minus_departure_s"], 3), "Fmin",
              j["F_min_after_departure_kN"], "att", _round_or_none(j["attitude_p34_absmax_deg"], 4),
              "rut", j["rut_min_after_ready_mm"], "events", j["event_counts"])
        if j["not_judgeable_gates"]:
            print("   not judgeable (no READY, counted as failed):", j["not_judgeable_gates"],
                  "G6-1 rule:", j["crawler_zero_rule"])
        print("   settle", j["settle_reference"], "phases", j["phases_rel_s"])
        _print_record_rows(j)
        if "vs_reference" in j:
            v = j["vs_reference"]
            print("   vs", v["ref"], "du_max", v["commands_max_abs_diff_m_s"], "first diff t", v["commands_first_diff_t_s"],
                  "truth", {k: round(x, 6) for k, x in v["truth_max_abs_diff"].items()}, "ref settle",
                  v["ref_settle_reference"])
    summary = res["summary"]
    print("summary: regular", summary["n_regular_pass"], "/", summary["n_regular"],
          "pass; expected fail", summary["expected_fail_cases"])


def _print_record_rows(j: dict[str, Any]) -> None:
    relax = j["relax_settings"]
    settings = relax["settings"] or {}
    print("   relax", relax["mode"], "enable", settings.get("enable"),
          "rise_tol_N", settings.get("rise_tol_N"), "n_relaxed_done", relax["n_relaxed_done"],
          "last_D_kN", _kN(relax["last_D_N"]))
    after = j["after_ready"]
    if after is not None:
        print("   after READY: D done", after["D_at_done_kN"], "ready", after["D_at_ready_kN"],
              "|D| max", after["D_absmax_after_ready_kN"], "end", after["D_end_kN"],
              "F_cyl min kN", {leg: v["min_kN"] for leg, v in after["F_cyl_min_after_ready"].items()})
    end = j["end_of_run"]
    decay = end["D_level_decay"]
    print("   end: phase", end["last_phase"], "D_end", end["D_end_kN"],
          "lambda", _round_or_none(decay["lambda_per_s"], 5), "n", decay["n_samples"],
          "soft", end["soft_pad"], "F_cyl min last 10 s kN",
          {leg: v["min_kN"] for leg, v in end["F_cyl_min_last_10s"].items()})


if __name__ == "__main__":
    main()
