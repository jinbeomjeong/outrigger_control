"""Spec rev. 79 draft (study 2): H-5 identity check and the S-1 .. S-6 judgement of the
``r79_sensor_screen.py`` runs (design: control-expert 2026-10-28, proposed thresholds).

identity  L0 command hashes against the rev. 76 baseline (G6 116: r76_g6_Pb.json, G8:
          r76_g8_ft_Pb / r76_g8_sw_Pb.json; the project C2 since f062051 has the Pb rise
          tolerance 0.6 kN built in).
judge     every run of a sensor level (L2, L3, ...) against the L1 run of the same case (path
          reference: ideal sensors, two pressure channels, CHECK + zero calibration):
  S-1 harness verdict (G6: r72 gates with the pre-LOC FLAG rules; G8: r69 pass): L1 pass ->
      level fail counts.
  S-2 P-S8-28: misfire = a guard event that L1 has not, while the true maximum motor stroke stays
      below 680.8 mm, or the anchor decision differs from L1 with |delta c_min(t_P)| > 5 mm;
      miss = true maximum stroke > 684.8 mm without a guard event; FAULT_STROKE_END 0.
  S-3 P-S8-29 (control-expert 2026-10-28, new against L1): fail = (1) from a relaxed DONE to
      READY a true leg force < F_min, or (2) true |D| - 15 kN > the run's own read error
      |D_meas - D_true| + 0.1 kN at an event that L1 has not (no L1 relax within +-5 s, times
      counted from the CHECK end); true |D| > 15 kN inside the band = FLAG S3_true_over_band;
      miss (design, kept) = L1 relaxed but the level has no READY or READY > 30 s later.
      Recorded: the design's absolute misfire (true |D| > 15 kN, < F_min, 5 s rise > 1.0 kN).
  S-4 P-S8-30 (new against L1): fail = a pause with no L1 pause of the same leg within +-1 s
      (CHECK-end relative) whose started leg has a true sample drop < 1 kN AND true force
      >= 3.5 F_min; the absolute condition with an L1 counterpart = baseline record; miss
      (design) = L1 paused, the level did not, and after the departure the true minimum
      < F_min or > 5 kN below L1; gate LOC - departure <= 2.9 s and no re-contact (new vs L1).
  S-5 LOC (new against L1): fail = L1 < 0.01 W but the level >= 0.01 W crawler true load (period
      maximum) at the LOC, or more than 0.01 W above L1; L1 >= 0.01 W = S5_baseline record.
  S-6 FAULT names that L1 has not: 0; new WARN names recorded.
Rates: failures / runs with the one-sided Clopper-Pearson 95 % upper bound
(``scipy.stats.beta.ppf(0.95, k + 1, n - k)``, spec 9966 convention).

Usage (any env with numpy + scipy):
  python -I r79_sensor_judge.py identity <run_json> [<run_json> ...]
  python -I r79_sensor_judge.py judge <out_json> <run_json> [<run_json> ...]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[3]
BASELINE_DIR = ROOT / "06_analysis" / "02_control" / "s8" / "rev76"
BASELINE_FILES = ("r76_g6_Pb.json", "r76_g8_ft_Pb.json", "r76_g8_sw_Pb.json")
BASELINE_VARIANT = "Pb"

GUARD_UNNEEDED_STROKE_MM = 680.8
GUARD_NEEDED_STROKE_MM = 684.8
ANCHOR_C_MIN_TOL_MM = 5.0
TWIST_RELAX_MAX_KN = 15.0
TWIST_RISE_MAX_KN = 1.0
READY_DELAY_MAX_S = 30.0
PAUSE_MIN_DROP_KN = 1.0
PAUSE_MAX_F_OVER_F_MIN = 3.5
PAUSE_MISS_MARGIN_KN = 5.0
LOC_DELAY_MAX_S = 2.9
FALSE_LOC_FRACTION_OF_W = 0.01
TWIST_BAND_MARGIN_KN = 0.1
RELAX_MATCH_S = 5.0
PAUSE_MATCH_S = 1.0
GUARD_WARNINGS = ("WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT")
CONFIDENCE = 0.95
REFERENCE_LEVEL = "L1"
NOT_JUDGED_LEVELS = ("L0", "L1")


def clopper_pearson_upper(failures: int, runs: int) -> float | None:
    """One-sided Clopper-Pearson upper bound of a failure rate (None for no runs)."""
    if runs == 0:
        return None
    if failures >= runs:
        return 1.0
    return float(beta.ppf(CONFIDENCE, failures + 1, runs - failures))


def _load_results(paths) -> list[dict]:
    results = []
    for path in paths:
        results += json.loads(Path(path).read_text(encoding="utf-8"))["results"]
    return results


def _command_hash(base: dict) -> str | None:
    return base.get("commands_sha256") or base.get("cmd_sha256")


# --------------------------------------------------------------------------------------- identity
def load_baseline_hashes(baseline_dir: Path = BASELINE_DIR) -> dict[str, tuple[str, bool]]:
    """``"<harness>|<inner>"`` -> (command hash, harness pass) of the rev. 76 baseline."""
    hashes = {}
    for name in BASELINE_FILES:
        data = json.loads((baseline_dir / name).read_text(encoding="utf-8"))
        for rec in data["results"]:
            harness, rest = rec["key"].split("|", 1)
            inner = rest.rsplit("|", 1)[0]
            if rec["key"].endswith(f"|{BASELINE_VARIANT}"):
                hashes[f"{harness}|{inner}"] = (_command_hash(rec), bool(rec.get("pass")))
    return hashes


def identity_rows(results: list[dict], baseline: dict[str, tuple[str, bool]]) -> list[dict]:
    rows = []
    for r in results:
        if r.get("level") != "L0":
            continue
        ref = baseline.get(f"{r['harness']}|{r['inner']}")
        run_hash = None if "error" in r else _command_hash(r["base"])
        rows.append({"key": r["key"], "run_hash": run_hash,
                     "baseline_hash": None if ref is None else ref[0],
                     "identical": ref is not None and run_hash == ref[0],
                     "pass_same": ref is not None and "error" not in r
                     and bool(r["base"].get("pass")) == ref[1],
                     "error": r.get("error"), "wall_s": r.get("wall_s")})
    return rows


# --------------------------------------------------------------------------------------- judge rows
def harness_verdict(base: dict) -> bool:
    """Harness pass with the G6 pre-LOC FLAG rules of r72_judge.py (decision 2 / U-S9-G6c):
    G6-7 counts as passed when every pre-LOC started leg kept its true minimum >= F_min, or when
    it did not but G6-3 holds and the run has no FAULT. G8 records keep their own ``pass``."""
    gates = base.get("gates")
    if not gates or "G6-7_preloc" not in gates:
        return bool(base.get("pass"))
    gates = dict(gates)
    no_fault = base.get("final_phase") not in ("fault", "fault_reground")
    if not gates["G6-7_preloc"]:
        flag_ok = base.get("preloc_flag_ok")
        if flag_ok is True or (flag_ok is False and gates.get("G6-3_Fmin") and no_fault):
            gates["G6-7_preloc"] = True
    return all(gates.values())


def _ready_time(rec: dict) -> float | None:
    base = rec["base"]
    return base.get("t_ready_s", base.get("t_ready"))


def judge_s2(run: dict, ref: dict) -> dict:
    s, s_ref = run["r79"], ref["r79"]
    guards = {n.split(":")[0] for _, n in s["guard_events"]} & set(GUARD_WARNINGS)
    guards_ref = {n.split(":")[0] for _, n in s_ref["guard_events"]} & set(GUARD_WARNINGS)
    new_guard = bool(guards - guards_ref)
    c_min, c_min_ref = s.get("c_min_tP_mm"), s_ref.get("c_min_tP_mm")
    anchor_differs = s["anchor_applied"] != s_ref["anchor_applied"]
    c_min_shift = (None if c_min is None or c_min_ref is None else abs(c_min - c_min_ref))
    misfire = ((new_guard and s["max_true_stroke_mm"] < GUARD_UNNEEDED_STROKE_MM)
               or (anchor_differs and c_min_shift is not None
                   and c_min_shift > ANCHOR_C_MIN_TOL_MM))
    miss = s["max_true_stroke_mm"] > GUARD_NEEDED_STROKE_MM and not guards
    return {"misfire": misfire, "miss": miss, "stroke_end_fault": s["n_stroke_end_fault"] > 0,
            "ok": not (misfire or miss or s["n_stroke_end_fault"] > 0),
            "new_guard": new_guard, "anchor_differs": anchor_differs,
            "c_min_shift_mm": c_min_shift, "max_true_stroke_mm": s["max_true_stroke_mm"]}


def bad_relaxations(summary: dict) -> list[dict]:
    """S-3 misfire events of one run (true values outside the relaxed-DONE premises)."""
    return [e for e in summary["twist_relax"]
            if e["true_abs_D_kN"] > TWIST_RELAX_MAX_KN or e["true_below_F_min"]
            or e["window_rise_kN"] > TWIST_RISE_MAX_KN]


def bad_pauses(summary: dict) -> list[dict]:
    """S-4 misfire events of one run (the started leg was not really falling / low)."""
    return [p for p in summary["lift_pauses"]
            if p["true_drop_kN"] < PAUSE_MIN_DROP_KN
            or p["true_F_over_F_min"] >= PAUSE_MAX_F_OVER_F_MIN]


def _relative_s(summary: dict, t_s: float) -> float:
    """Event time from the CHECK end (the CHECK length differs between the levels)."""
    return t_s - (summary.get("t_check_end_s") or 0.0)


def _has_counterpart(summary: dict, ref_summary: dict, event: dict, key: str, tol_s: float,
                     leg: str | None = None) -> bool:
    t_rel = _relative_s(summary, event["t_s"])
    for other in ref_summary[key]:
        if leg is not None and other["leg"] != leg:
            continue
        if abs(_relative_s(ref_summary, other["t_s"]) - t_rel) <= tol_s + 1e-9:
            return True
    return False


def _twist_over_band_kN(event: dict) -> float:
    """True |D| above 15 kN beyond the run's own read error band (> 0 = outside)."""
    return (event["true_abs_D_kN"] - TWIST_RELAX_MAX_KN
            - (event["D_read_error_kN"] + TWIST_BAND_MARGIN_KN))


def judge_s3(run: dict, ref: dict) -> dict:
    """control-expert rule (failure new against L1); the design's absolute misfire recorded."""
    s, s_ref = run["r79"], ref["r79"]
    low_to_ready = [e for e in s["twist_relax"] if e.get("true_below_F_min_to_ready")]
    over_band, in_band = [], []
    for e in s["twist_relax"]:
        if e["true_abs_D_kN"] <= TWIST_RELAX_MAX_KN:
            continue
        outside = _twist_over_band_kN(e) > 0.0
        if outside and not _has_counterpart(s, s_ref, e, "twist_relax", RELAX_MATCH_S):
            over_band.append(e)
        else:
            in_band.append(e)
    ready, ready_ref = _ready_time(run), _ready_time(ref)
    delay = None if ready is None or ready_ref is None else ready - ready_ref
    miss = bool(s_ref["twist_relax"]) and (
        ready is None or (delay is not None and delay > READY_DELAY_MAX_S))
    fail = bool(low_to_ready or over_band) or miss
    return {"ok": not fail, "fail_low_to_ready": bool(low_to_ready),
            "fail_over_band_new": bool(over_band), "miss": miss,
            "flags": ["S3_true_over_band"] if in_band else [],
            "absolute_misfire": bool(bad_relaxations(s)),
            "absolute_misfire_L1": bool(bad_relaxations(s_ref)),
            "n_relax": len(s["twist_relax"]), "n_done_entries": s["n_done_entries"],
            "ready_delay_vs_L1_s": delay,
            "events": [{k: e.get(k) for k in ("t_s", "D_meas_kN", "D_true_kN", "D_read_error_kN",
                                              "true_abs_D_kN", "true_min_F_to_ready_kN",
                                              "window_rise_kN")} for e in s["twist_relax"][:6]]}


def judge_s4(run: dict, ref: dict) -> dict:
    """control-expert rule (failure new against L1); the design's absolute misfire recorded."""
    s, s_ref = run["r79"], ref["r79"]
    bad = bad_pauses(s)
    new_bad, baseline = [], []
    for p in s["lift_pauses"]:
        both = (p["true_drop_kN"] < PAUSE_MIN_DROP_KN
                and p["true_F_over_F_min"] >= PAUSE_MAX_F_OVER_F_MIN)
        matched = _has_counterpart(s, s_ref, p, "lift_pauses", PAUSE_MATCH_S, leg=p["leg"])
        if both and not matched:
            new_bad.append(p)
        elif p in bad and matched:
            baseline.append(p)
    minimum, minimum_ref = s["min_true_F_after_off_kN"], s_ref["min_true_F_after_off_kN"]
    paused_ref, paused = bool(s_ref["lift_pauses"]), bool(s["lift_pauses"])
    low = minimum is not None and (
        minimum < s["F_min_kN"]
        or (minimum_ref is not None and minimum < minimum_ref - PAUSE_MISS_MARGIN_KN))
    miss = paused_ref and not paused and low
    loc_ok = s["loc_minus_off_s"] is not None and s["loc_minus_off_s"] <= LOC_DELAY_MAX_S
    loc_ok_ref = (s_ref["loc_minus_off_s"] is not None
                  and s_ref["loc_minus_off_s"] <= LOC_DELAY_MAX_S)
    recontact_new = s["n_recontact_after_off"] > 0 and s_ref["n_recontact_after_off"] == 0
    gate_fail = (loc_ok_ref and not loc_ok) or recontact_new
    return {"ok": not (new_bad or miss or gate_fail), "fail_misfire_new": bool(new_bad),
            "miss": miss, "gate_fail": gate_fail,
            "flags": ["S4_baseline"] if baseline else [],
            "absolute_misfire": bool(bad), "absolute_misfire_L1": bool(bad_pauses(s_ref)),
            "n_pauses": len(s["lift_pauses"]), "loc_minus_off_s": s["loc_minus_off_s"],
            "n_recontact_after_off": s["n_recontact_after_off"],
            "misfire_events": (new_bad or bad)[:5]}


def is_false_loc(run: dict) -> bool:
    ratio = run["r79"]["crawler_at_loc_over_W"]
    return ratio is not None and ratio >= FALSE_LOC_FRACTION_OF_W


def judge_s5(run: dict, ref: dict) -> dict:
    """control-expert rule: fail when the LOC crawler load turns >= 0.01 W against an L1 below
    it, or rises more than 0.01 W above L1; L1 already >= 0.01 W = S5_baseline record."""
    ratio = run["r79"]["crawler_at_loc_over_W"]
    ratio_ref = ref["r79"]["crawler_at_loc_over_W"]
    false_loc, false_loc_ref = is_false_loc(run), is_false_loc(ref)
    rise = None if ratio is None or ratio_ref is None else ratio - ratio_ref
    fail = (false_loc and not false_loc_ref) or (
        rise is not None and rise > FALSE_LOC_FRACTION_OF_W)
    return {"ok": not fail, "false_loc": false_loc, "false_loc_L1": false_loc_ref,
            "flags": ["S5_baseline"] if false_loc_ref else [],
            "crawler_at_loc_over_W": ratio, "crawler_at_loc_over_W_L1": ratio_ref,
            "rise_over_W": rise}


def judge_s6(run: dict, ref: dict) -> dict:
    names, names_ref = set(run["r79"]["warn_fault"]), set(ref["r79"]["warn_fault"])
    new = sorted(names - names_ref)
    new_fault = [n for n in new if n.startswith("FAULT")]
    return {"new_fault": new_fault, "new_warn": [n for n in new if n.startswith("WARN")],
            "ok": not new_fault}


def judge_run(run: dict, ref: dict) -> dict:
    verdict, verdict_ref = harness_verdict(run["base"]), harness_verdict(ref["base"])
    rows = {"S-1": {"ok": not (verdict_ref and not verdict), "L1_pass": verdict_ref,
                    "pass": verdict},
            "S-2": judge_s2(run, ref), "S-3": judge_s3(run, ref), "S-4": judge_s4(run, ref),
            "S-5": judge_s5(run, ref), "S-6": judge_s6(run, ref)}
    ready, ready_ref = _ready_time(run), _ready_time(ref)
    return {"key": run["key"], "level": run["level"], "seed_index": run["seed_index"],
            "harness": run["harness"], "inner": run["inner"], "rows": rows,
            "pass": all(row["ok"] for row in rows.values()),
            "zero_cal_all": run.get("zero_calibration", {}).get("all_calibrated"),
            "ready_delay_vs_L1_s": None if ready is None or ready_ref is None
            else round(ready - ready_ref, 1),
            "rod_fallback_legs": len({leg for _, leg in run["r79"].get("rod_fallback", [])})}


def case_group(harness: str, inner: str) -> str:
    return {"g6": "G6", "g8": "G8", "ref": "ref"}[harness]


def aggregate(judged: list[dict]) -> list[dict]:
    """Failure counts and upper bounds per (level, group) and per (level, all)."""
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in judged:
        buckets[(row["level"], case_group(row["harness"], row["inner"]))].append(row)
        buckets[(row["level"], "all")].append(row)
    table = []
    for (level, group), rows in sorted(buckets.items()):
        entry = {"level": level, "group": group, "runs": len(rows)}
        for name in ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6"):
            failures = sum(1 for r in rows if not r["rows"][name]["ok"])
            entry[name] = {"fail": failures,
                           "upper_95": clopper_pearson_upper(failures, len(rows))}
        failures = sum(1 for r in rows if not r["pass"])
        entry["any"] = {"fail": failures, "upper_95": clopper_pearson_upper(failures, len(rows))}
        entry["zero_cal_failed_runs"] = sum(1 for r in rows if r["zero_cal_all"] is False)
        entry["ready_late_30s_runs"] = sum(
            1 for r in rows if r["ready_delay_vs_L1_s"] is not None
            and r["ready_delay_vs_L1_s"] > READY_DELAY_MAX_S)
        entry["rod_fallback_runs"] = sum(1 for r in rows if r["rod_fallback_legs"] > 0)
        # the design's absolute counts (record only; the failures above are new against L1)
        entry["absolute"] = {
            "S-3_misfire": sum(1 for r in rows if r["rows"]["S-3"]["absolute_misfire"]),
            "S-4_misfire": sum(1 for r in rows if r["rows"]["S-4"]["absolute_misfire"]),
            "S-5_false_loc": sum(1 for r in rows if r["rows"]["S-5"]["false_loc"])}
        entry["flags"] = {
            flag: sum(1 for r in rows if flag in r["rows"][name].get("flags", []))
            for name, flag in (("S-3", "S3_true_over_band"), ("S-4", "S4_baseline"),
                               ("S-5", "S5_baseline"))}
        table.append(entry)
    return table


def reference_table(results: list[dict]) -> list[dict]:
    """L1 (path reference) per group: harness verdict, false LOC, zero calibration, rod
    fallback, so a level row can be read against what the reference itself does."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        if r.get("level") == REFERENCE_LEVEL and "error" not in r:
            buckets[case_group(r["harness"], r["inner"])].append(r)
            buckets["all"].append(r)
    return [{"group": group, "runs": len(rows),
             "harness_pass": sum(harness_verdict(r["base"]) for r in rows),
             "false_loc": sum(is_false_loc(r) for r in rows),
             "zero_cal_failed": sum(1 for r in rows
                                    if not r["zero_calibration"]["all_calibrated"]),
             "rod_fallback_runs": sum(1 for r in rows if r["r79"].get("rod_fallback"))}
            for group, rows in sorted(buckets.items())]


def _pair_key(run: dict) -> tuple[str, str, str]:
    """A level run pairs with the L1 run of the same case and the same rod reading model."""
    return run["harness"], run["inner"], run.get("rod_model", "harness")


def judge_results(results: list[dict]) -> dict:
    references = {_pair_key(r): r for r in results
                  if r.get("level") == REFERENCE_LEVEL and "error" not in r}
    judged, unmatched, errors = [], [], []
    for r in results:
        if r.get("level") in NOT_JUDGED_LEVELS:
            continue
        if "error" in r:
            errors.append({"key": r["key"], "error": r["error"]})
            continue
        ref = references.get(_pair_key(r))
        if ref is None:
            unmatched.append(r["key"])
            continue
        judged.append(judge_run(r, ref))
    return {"table": aggregate(judged), "reference": reference_table(results), "runs": judged,
            "unmatched": unmatched, "errors": errors}


def summary_lines(report: dict) -> list[str]:
    """Markdown tables: failures (upper bound) per level and group, then the L1 reference."""
    head = ("| level | group | runs | S-1 | S-2 | S-3 | S-4 | S-5 | S-6 | any | 0-cal fail "
            "| READY +30 s | rod fallback | absolute S-3 / S-4 / S-5 | FLAG S3 band / S4 base "
            "/ S5 base |")
    lines = [head, "|" + "---|" * 15]
    for e in report["table"]:
        cells = [f"{e[n]['fail']} ({100 * e[n]['upper_95']:.1f} %)"
                 for n in ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6", "any")]
        absolute, flags = e["absolute"], e["flags"]
        lines.append(f"| {e['level']} | {e['group']} | {e['runs']} | " + " | ".join(cells)
                     + f" | {e['zero_cal_failed_runs']} | {e['ready_late_30s_runs']} "
                       f"| {e['rod_fallback_runs']} | {absolute['S-3_misfire']} / "
                       f"{absolute['S-4_misfire']} / {absolute['S-5_false_loc']} "
                       f"| {flags['S3_true_over_band']} / {flags['S4_baseline']} / "
                       f"{flags['S5_baseline']} |")
    lines += ["", "| L1 group | runs | harness pass | false LOC | 0-cal fail | rod fallback |",
              "|" + "---|" * 6]
    for e in report["reference"]:
        lines.append(f"| {e['group']} | {e['runs']} | {e['harness_pass']} | {e['false_loc']} "
                     f"| {e['zero_cal_failed']} | {e['rod_fallback_runs']} |")
    return lines


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("identity", "judge"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "identity":
        rows = identity_rows(_load_results(sys.argv[2:]), load_baseline_hashes())
        for row in rows:
            print(row["key"], "identical" if row["identical"] else "DIFFERENT",
                  "pass_same" if row["pass_same"] else "PASS_DIFFERS", row["wall_s"],
                  row["error"] or "")
        print(sum(r["identical"] for r in rows), "/", len(rows), "identical")
        return
    out_path = Path(sys.argv[2])
    report = judge_results(_load_results(sys.argv[3:]))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print("\n".join(summary_lines(report)))
    print("unmatched", len(report["unmatched"]), "errors", len(report["errors"]), "->", out_path)


if __name__ == "__main__":
    main()
