"""Re-judge stored study-1 results (``s9_soil_slope.py`` JSON) with the corrected settle check.

The first settle check compared the pad penetration at the settle INSTANT with the table gap
targets, which are 5 s means (dynamics-expert 2026-10-28): the crawler still rocks after the
settle, so the instant differs from the mean by the rocking phase (rigid rotation plus a common
heave; remainder <= 0.011 mm). Corrected check (no rerun, stored values only):
  gap       pen_mean_i = pen_inst_i + (y_i d_phi - x_i d_theta), d = settle-instant attitude
            minus the window-mean attitude (floor axes, the attitude check window),
            |pen_mean + gap_target| <= 1 mm per pad
  attitude  window-mean attitude minus target_q_floor per axis within
            max(0.005 deg, |table residual of that axis| + 0.002 deg)
Verdict: the stored row verdict (``verdict_rows``) unless the corrected check fails
("settle_check_fail"); runs with ``case.mass_scale`` != 1.0 only record the check and keep
``verdict_rows`` (spec 422.2, ``s9_soil_slope._final_verdict``). The first check is kept as
``settle.check_v1``.

Two input formats:
  ``results``  s9_soil_slope.py output; re-judged with the stored settle data as above.
  ``records``  s9_slope_fix_candidates.py ``run`` output. Records keep no settle data, so the
               settle v2 result of each case comes from a re-judged ``results`` file (--baseline;
               the settle precedes the controller, so it is the same for every candidate):
                 baseline settle v2 fails      -> settle_check_fail                  (direct)
                 record not settle_check_fail  -> stored verdict                     (direct)
                 command hash == baseline hash -> baseline ``verdict_rows``          (baseline_rows)
                 otherwise rebuilt from ``soil_stop`` / ``failed_rows`` / ``warnings`` (rebuilt),
                   in the ``s9_soil_slope.classify`` order:
                   soil-guard stop -> stroke_limited_stop (or fail), stroke FAULT -> fail,
                   guard warning -> stroke_limited_pass when no FAULT and P3-1 / P3-3 / P3-4
                   pass (also with no failed row, spec 398.1 SL-1; lifted legs are not
                   recorded) else stroke_limited_fail, then no failed row -> pass, else fail
               Records whose id is not in the baseline keep their verdict (direct). Each output
               record carries ``verdict``, ``verdict_before_settle_v2``, ``passed`` and
               ``settle_v2_source``; the input ``summary`` / ``comparison`` blocks (pre-v2
               verdicts) are not copied, ``counts`` gives the before / after tallies.

Usage (project root): python -I s9_settle_rejudge.py <json> [<json> ...]
                      [--table JSON] [--baseline JSON] [--suffix _rejudged] [--out-dir DIR]
Writes <stem><suffix>.json next to each input (or into --out-dir); ``results`` inputs also get the
case / k* CSV tables (s9_soil_slope ``write_outputs``). Units: mm, deg; pad x, y in m.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import s9_soil_slope as ss  # noqa: E402  (summary / CSV writers only, nothing is run)

DEFAULT_TABLE = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
DEFAULT_BASELINE = (ROOT / "06_analysis" / "02_control" / "s9" / "rev80"
                    / "s9_soil_slope_settle_rejudged.json")
SCRIPT = "04_scripts/03_control/s9/s9_settle_rejudge.py"
GAP_TOL_MM = 1.0
ATTITUDE_TOL_MIN_DEG = 0.005
ATTITUDE_RESIDUAL_MARGIN_DEG = 0.002
RESIDUAL_KEYS = ("residual_roll_deg", "residual_pitch_deg")
CHECK_VERSION = "v2: window-mean pen (rotation-corrected), residual-aware attitude tolerance"

# ``records`` inputs (s9_slope_fix_candidates.py run): where the settle v2 verdict came from
SOURCE_DIRECT = "direct"
SOURCE_BASELINE_ROWS = "baseline_rows"
SOURCE_REBUILT = "rebuilt"
PASSED_VERDICTS = (ss.VERDICT_PASS, ss.VERDICT_STROKE_LIMITED_PASS)
FAULT_WARNING_PREFIX = "FAULT"  # s9_soil_slope._has_fault: any event named FAULT*
RECORDS_RULE = (
    "settle v2 from the baseline (re-judged results file) per case id. Baseline settle v2 fail -> "
    "settle_check_fail (direct); record not settle_check_fail -> stored verdict (direct); hash == "
    "baseline hash -> baseline verdict_rows (baseline_rows); else rebuilt from soil_stop + "
    "failed_rows + warnings in s9_soil_slope.classify order (soil stop -> stroke_limited_stop / "
    "fail, stroke FAULT -> fail, guard warning -> stroke_limited_pass when no FAULT and "
    "P3-1/P3-3/P3-4 pass (lifted legs not recorded) else stroke_limited_fail, then no failed "
    "rows -> pass, else fail)")


def window_mean_penetration_mm(pen_inst_mm, q_inst_deg, q_mean_deg, pad_xy_m) -> list[float]:
    """Pad penetration at the window-mean attitude: the instant value moved by the rigid rotation
    d = instant - mean (floor axes; point displacement y d_phi - x d_theta, mm)."""
    d_phi = math.radians(q_inst_deg[0] - q_mean_deg[0])
    d_theta = math.radians(q_inst_deg[1] - q_mean_deg[1])
    return [pen + (y * d_phi - x * d_theta) * 1e3
            for pen, (x, y) in zip(pen_inst_mm, pad_xy_m, strict=True)]


def attitude_tolerances_deg(table_row: dict) -> list[float]:
    """Per-axis (roll, pitch) tolerance: the table row's own residual plus a margin, at least
    0.005 deg."""
    return [max(ATTITUDE_TOL_MIN_DEG, abs(float(table_row.get(key, 0.0)))
                + ATTITUDE_RESIDUAL_MARGIN_DEG) for key in RESIDUAL_KEYS]


def corrected_check(result: dict, table_row: dict, pad_xy_m) -> dict | None:
    """Corrected settle check of one stored result (None when the run had no table check)."""
    settle = result.get("settle") or {}
    first = settle.get("check_v1", settle.get("check"))
    if first is None:
        return None
    gap_target = result["case"]["settle_table"]["gap_target_mm"]
    pen_mean = window_mean_penetration_mm(settle["pen_mm"], settle["q_floor_deg"],
                                          first["q_floor_mean_deg"], pad_xy_m)
    gap_error = [p + g for p, g in zip(pen_mean, gap_target, strict=True)]
    tolerances = attitude_tolerances_deg(table_row)
    att_error = first["attitude_error_deg"]
    is_gap_ok = all(abs(e) <= GAP_TOL_MM for e in gap_error)
    is_attitude_ok = all(abs(e) <= tol for e, tol in zip(att_error, tolerances, strict=True))
    return {"ok": is_gap_ok and is_attitude_ok, "gap_ok": is_gap_ok,
            "attitude_ok": is_attitude_ok, "pen_plus_gap_mm": gap_error,
            "pen_plus_gap_instant_mm": first["pen_plus_gap_mm"],
            "attitude_error_deg": att_error, "attitude_tol_deg": tolerances,
            "window_end_s": first.get("window_end_s"),
            "q_floor_mean_deg": first["q_floor_mean_deg"], "version": CHECK_VERSION}


def rejudge_result(result: dict, rows: dict, pad_xy_m) -> dict:
    """Stored result with the corrected check and verdict (input left unchanged)."""
    if "error" in result or result["case"].get("settle_table_status") != "applied":
        return result
    row = rows[result["case"]["harness_settle_key"]]
    check = corrected_check(result, row, pad_xy_m)
    if check is None:
        return result
    settle = dict(result["settle"])
    settle["check_v1"] = settle.get("check_v1", settle["check"])
    settle["check"] = check
    # same rule as the run itself (spec 422.2): a scaled-mass run only records the check
    mass_scale = result["case"].get("mass_scale", 1.0)
    verdict = ss._final_verdict(result["verdict_rows"], check, mass_scale)  # noqa: SLF001
    return {**result, "settle": settle, "verdict_before_settle_v2": result["verdict"],
            "verdict": verdict}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _has_warning(warnings: list[str], prefixes: str | tuple[str, ...]) -> bool:
    return any(warning.startswith(prefixes) for warning in warnings)


def _record_has_fault(record: dict) -> bool:
    """``s9_soil_slope._has_fault`` on a record: FAULT final phase or any FAULT event.

    The ``fault_ready`` row is not used here: it also fails on a run without READY."""
    return (record.get("final_phase") in ss.FAULT_PHASES
            or _has_warning(record["warnings"], FAULT_WARNING_PREFIX))


def _is_record_stroke_limited_pass(record: dict) -> bool:
    """``s9_soil_slope.is_stroke_limited_pass`` on a record.

    The lifted-leg test reads the record's SL-1 ``lifted_legs`` (written by
    ``s9_slope_fix_candidates`` since 2026-10-30). An older record without the key skips that
    test, as before: there a guarded run with a lifted leg and P3-1 / P3-3 / P3-4 passing is a
    stroke limited pass here and a stroke limited fail in ``classify``."""
    failed_required_rows = set(record["failed_rows"]) & set(ss.STROKE_LIMITED_REQUIRED_ROWS)
    has_lifted_leg = bool(record.get("lifted_legs"))
    return not _record_has_fault(record) and not failed_required_rows and not has_lifted_leg


def rebuild_row_verdict(record: dict) -> str:
    """Row verdict of a ``records`` entry from its failed rows, warnings and soil stop.

    Same order as ``s9_soil_slope.classify``: the soil-guard stop (spec 427.9) first, then a
    stroke FAULT fails, then the stroke guard warning gives the stroke limited class (spec 398.1
    SL-1: also with no failed row), and only then no failed row passes."""
    soil_stop = record.get("soil_stop")
    if soil_stop is not None:
        return ss.VERDICT_STROKE_LIMITED_STOP if soil_stop["pass"] else ss.VERDICT_FAIL
    warnings = record["warnings"]
    if _has_warning(warnings, ss.STROKE_FAULT_EVENTS):
        return ss.VERDICT_FAIL
    if _has_warning(warnings, ss.STROKE_GUARD_WARNING):
        if _is_record_stroke_limited_pass(record):
            return ss.VERDICT_STROKE_LIMITED_PASS
        return ss.VERDICT_STROKE_LIMITED_FAIL
    # without the guard every judged row counts; a FAULT already fails the fault_ready row
    if record["failed_rows"] or _record_has_fault(record):
        return ss.VERDICT_FAIL
    return ss.VERDICT_PASS


def _is_baseline_settle_ok(baseline_result: dict) -> bool:
    check = (baseline_result.get("settle") or {}).get("check")
    return check is None or bool(check["ok"])


def record_settle_v2_verdict(record: dict, baseline_by_id: dict[str, dict]) -> tuple[str, str]:
    """Settle v2 verdict of one ``records`` entry and its source (see the module docstring).

    Args:
        record: One entry of a s9_slope_fix_candidates.py ``records`` list.
        baseline_by_id: Re-judged ``results`` entries of s9_soil_slope.py keyed by case id.

    Returns:
        (verdict, source), source one of ``SOURCE_DIRECT``, ``SOURCE_BASELINE_ROWS``,
        ``SOURCE_REBUILT``.
    """
    baseline_result = baseline_by_id.get(record["id"])
    if baseline_result is None:
        return record["verdict"], SOURCE_DIRECT
    if not _is_baseline_settle_ok(baseline_result):
        return ss.VERDICT_SETTLE_CHECK_FAIL, SOURCE_DIRECT
    if record["verdict"] != ss.VERDICT_SETTLE_CHECK_FAIL:
        return record["verdict"], SOURCE_DIRECT
    baseline_hash = (baseline_result.get("run") or {}).get("commands_sha256")
    baseline_rows_verdict = baseline_result.get("verdict_rows")
    if record["hash"] == baseline_hash and baseline_rows_verdict is not None:
        return baseline_rows_verdict, SOURCE_BASELINE_ROWS
    return rebuild_row_verdict(record), SOURCE_REBUILT


def rejudge_record(record: dict, baseline_by_id: dict[str, dict]) -> dict:
    """``records`` entry with the settle v2 verdict (input left unchanged)."""
    verdict, source = record_settle_v2_verdict(record, baseline_by_id)
    return {**record, "verdict_before_settle_v2": record["verdict"], "verdict": verdict,
            "passed": verdict in PASSED_VERDICTS, "settle_v2_source": source}


def load_baseline(baseline_path: Path) -> dict[str, dict]:
    """Re-judged ``results`` of the baseline file keyed by case id.

    Raises:
        ValueError: The file is not a settle v2 re-judged ``results`` file.
    """
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    is_rejudged = "settle_rejudge" in payload.get("meta", {})
    if "results" not in payload or not is_rejudged:
        raise ValueError(f"{baseline_path}: baseline must be a settle v2 re-judged results file "
                         "(s9_settle_rejudge.py output)")
    return {result["id"]: result for result in payload["results"]}


def _output_path(path: Path, suffix: str, out_dir: Path | None) -> Path:
    folder = path.parent if out_dir is None else out_dir
    return folder / (path.stem + suffix + ".json")


def _rejudge_results_payload(payload: dict, path: Path, table_path: Path,
                             out_path: Path) -> dict:
    table = json.loads(table_path.read_text(encoding="utf-8"))
    rows, pad_xy = table["hook_harness"], table["pad_xy_m"]
    results = [rejudge_result(r, rows, pad_xy) for r in payload["results"]]
    meta = {**payload["meta"], "settle_rejudge": {
        "script": SCRIPT, "from": str(path),
        "from_sha256": _sha256(path), "table": str(table_path), "table_sha256": _sha256(table_path),
        "check": CHECK_VERSION}}
    summary = ss.write_outputs(out_path, results, meta)
    return {"out": out_path, "counts": summary["counts"],
            "before": dict(Counter(r.get("verdict") for r in payload["results"])),
            "results": results}


def _rejudge_records_payload(payload: dict, path: Path, baseline_path: Path,
                             out_path: Path) -> dict:
    baseline_by_id = load_baseline(baseline_path)
    records = [rejudge_record(record, baseline_by_id) for record in payload["records"]]
    counts = {
        "before": dict(Counter(record["verdict"] for record in payload["records"])),
        "after": dict(Counter(record["verdict"] for record in records)),
        "settle_v2_source": dict(Counter(record["settle_v2_source"] for record in records)),
    }
    meta = {**payload["meta"], "settle_rejudge": {
        "script": SCRIPT, "from": str(path), "from_sha256": _sha256(path),
        "baseline": str(baseline_path), "baseline_sha256": _sha256(baseline_path),
        "check": CHECK_VERSION, "rule": RECORDS_RULE}}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"meta": meta, "counts": counts, "records": records},
                                   indent=1, default=str), encoding="utf-8")
    return {"out": out_path, "counts": counts["after"], "before": counts["before"],
            "sources": counts["settle_v2_source"], "records": records}


def rejudge_file(path: Path, table_path: Path, suffix: str, *,
                 baseline_path: Path = DEFAULT_BASELINE, out_dir: Path | None = None) -> dict:
    """Re-judge one ``results`` or ``records`` JSON file and write <stem><suffix>.json.

    Args:
        path: Input JSON (s9_soil_slope.py ``results`` or s9_slope_fix_candidates.py
            ``records``).
        table_path: Settle table (``hook_harness``, ``pad_xy_m``), used by ``results`` inputs.
        suffix: Appended to the input stem for the output name.
        baseline_path: Re-judged ``results`` file, used by ``records`` inputs.
        out_dir: Output folder; None writes next to the input.

    Returns:
        Report with the output path, before / after verdict counts and the re-judged entries
        (``results`` or ``records``).

    Raises:
        ValueError: The input has neither a ``results`` nor a ``records`` list.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    out_path = _output_path(path, suffix, out_dir)
    if "results" in payload:
        return _rejudge_results_payload(payload, path, table_path, out_path)
    if "records" in payload:
        return _rejudge_records_payload(payload, path, baseline_path, out_path)
    raise ValueError(f"{path}: expected a 'results' (s9_soil_slope.py) or 'records' "
                     "(s9_slope_fix_candidates.py run) list")


def _print_record_changes(report: dict) -> None:
    print(report["out"], "before", report["before"], "after", report["counts"],
          "source", report["sources"])
    transitions = Counter((record["verdict_before_settle_v2"], record["verdict"])
                          for record in report["records"]
                          if record["verdict_before_settle_v2"] != record["verdict"])
    for (before, after), count in sorted(transitions.items()):
        print(f"  {before} -> {after}: {count}")


def _print_changes(report: dict) -> None:
    if "records" in report:
        _print_record_changes(report)
        return
    print(report["out"], "before", report["before"], "after", report["counts"])
    for result in report["results"]:
        before = result.get("verdict_before_settle_v2")
        is_changed = before is not None and result["verdict"] != before
        if not (is_changed or before == ss.VERDICT_SETTLE_CHECK_FAIL):
            continue
        check = result["settle"]["check"]
        print(f"  {result['id']}: {before} -> {result['verdict']} | gap(mean) "
              f"{[round(v, 3) for v in check['pen_plus_gap_mm']]} (instant "
              f"{[round(v, 3) for v in check['pen_plus_gap_instant_mm']]}) | att err "
              f"{[round(v, 4) for v in check['attitude_error_deg']]} tol "
              f"{[round(v, 4) for v in check['attitude_tol_deg']]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-judge study-1 results, corrected settle check")
    parser.add_argument("results", nargs="+", type=Path,
                        help="s9_soil_slope 'results' or s9_slope_fix_candidates 'records' JSON")
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE,
                        help="re-judged results file giving the settle v2 of 'records' inputs")
    parser.add_argument("--suffix", default="_rejudged")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="output folder (default: next to each input)")
    args = parser.parse_args()
    for path in args.results:
        _print_changes(rejudge_file(path, args.table, args.suffix,
                                    baseline_path=args.baseline, out_dir=args.out_dir))


if __name__ == "__main__":
    main()
