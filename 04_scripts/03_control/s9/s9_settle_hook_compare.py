"""Compare two runs of the S9 reduced harness case by case: settle hook "harness" vs "p0" (or a
fresh run vs a stored reference for the identity check).

Accepted result files (the format is detected per file):
  g6     r72 / r74 / r76 screen JSON (``results`` with ``key`` / ``gates``); cases are matched by
         the r72 key (the variant suffix ``|proj`` / ``|Pb`` is dropped)
  s9     ``s9_soil_closed_loop.run_batch`` JSON (``runs`` with ``id``; s9_runs, s9_project_check)
  slope  ``s9_soil_slope.py`` JSON (``results`` with ``verdict`` / ``rows``)
Metrics per case: judgement rows (failed set, pass), command SHA-256, READY time, min true F_cyl
after the crawler lift-off, end attitude, rut clearance at READY / end, max motor stroke,
c_min(t_P), S-3 corner bias applied (INFO_CLEARANCE_BIAS) and LOC anchor, LOC minus lift-off, relaxed-DONE |D|,
INFO_TOUCH_DIP_HELD / INFO_LIFT_PAUSED counts, settle check (hook, attitude / gap errors).
Units: s, kN, deg, mm. Pure JSON post-processing (no harness import).

Usage: python -I s9_settle_hook_compare.py <base_json> <new_json> <out_json> [--focus SUBSTR,...]
  (several base / new files: join them with ';', e.g. "soil.json;sensor.json")
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ATTITUDE_TOL_DEG = 0.2
RUT_MIN_MM = 25.0
STROKE_OK_MM = 684.8
LOC_DELAY_MAX_S = 2.9
S3_EVENT = "INFO_CLEARANCE_BIAS"
ANCHOR_EVENT = "INFO_LOC_CLEARANCE_ANCHOR"
TOUCH_DIP_EVENT = "INFO_TOUCH_DIP_HELD"
LIFT_PAUSED_EVENT = "INFO_LIFT_PAUSED"
TWIST_RELAX_EVENT = "INFO_TWIST_UNSETTLED"
LOC_EVENT = "crawler_liftoff_confirmed"
DELTA_KEYS = (
    "t_ready_s",
    "min_Fcyl_after_off_kN",
    "att_end_roll_deg",
    "att_end_pitch_deg",
    "rut_ready_mm",
    "rut_end_mm",
    "max_stroke_mm",
    "c_min_tP_mm",
    "loc_delay_s",
)
COUNT_KEYS = (TOUCH_DIP_EVENT, LIFT_PAUSED_EVENT, S3_EVENT, ANCHOR_EVENT, TWIST_RELAX_EVENT)


# ------------------------------------------------------------------------------ normalising
def _event_names(entries) -> list[str]:
    """Event names of "<t> <name>" strings (s9 events, r72 events_head)."""
    return [entry.split(" ", 1)[1] for entry in entries or [] if " " in entry]


def _event_time(entries, prefix: str) -> float | None:
    for entry in entries or []:
        t_s, _, name = entry.partition(" ")
        if name.startswith(prefix):
            return float(t_s)
    return None


def _count(names: list[str], event: str) -> int:
    return sum(1 for name in names if name.split(":")[0] == event)


def _relax_values_kN(names: list[str]) -> list[float]:
    return [float(n.split(":")[1]) for n in names if n.startswith(TWIST_RELAX_EVENT + ":")]


def _settle_fields(settle: dict | None) -> dict:
    settle = settle or {}
    return {
        "settle_hook": settle.get("hook"),
        "settle_att_floor_deg": settle.get("att_floor_deg"),
        "settle_gap_mm": settle.get("gap_mm"),
        "settle_att_error_deg": settle.get("att_error_deg"),
        "settle_gap_error_mm": settle.get("gap_error_mm"),
    }


def _from_g6(rec: dict) -> dict:
    names = _event_names(rec.get("events_head"))
    counts = rec.get("info_counts")
    if (
        counts is None
    ):  # older screens: only the first 40 events are stored (counts are lower bounds)
        counts = {event: _count(names, event) for event in COUNT_KEYS}
    relax = rec.get("twist_unsettled_D_kN")
    if relax is None:
        relax = _relax_values_kN(names)
    att = rec.get("att_end_deg") or [math.nan, math.nan]
    return {
        "id": rec.get("inner_key") or rec["key"].rsplit("|", 1)[0],
        "sha": rec.get("commands_sha256"),
        "pass": rec.get("pass"),
        "failed": sorted(k for k, v in (rec.get("gates") or {}).items() if not v),
        "t_ready_s": rec.get("t_ready_s"),
        "min_Fcyl_after_off_kN": rec.get("min_true_Fcyl_after_off_kN"),
        "att_end_roll_deg": att[0],
        "att_end_pitch_deg": att[1],
        "rut_ready_mm": rec.get("rut_clear_ready_mm"),
        "rut_end_mm": rec.get("rut_clear_end_mm"),
        "max_stroke_mm": rec.get("max_motor_stroke_mm"),
        "c_min_tP_mm": rec.get("c_min_tP_mm"),
        "loc_delay_s": rec.get("loc_delay_s"),
        "s3_applied": counts.get(S3_EVENT, 0) > 0,
        "anchor_applied": bool(rec.get("anchor_applied")),
        "relax_D_kN": relax,
        "counts": dict(counts),
        "counts_exact": rec.get("info_counts") is not None,
        **_settle_fields(rec.get("settle")),
        "error": rec.get("error"),
    }


def _s9_gates(run: dict, t_loc: float | None) -> dict:
    """P3-type gates of an s9 run_case record (as the G6 screen rows)."""
    att = run.get("att_end_deg") or [math.nan, math.nan]
    t_off, t_done = run.get("t_crawler_off_first_s"), run.get("t_done_s")
    margin = run.get("min_margin_after_off_kN")
    return {
        "crawler": run.get("crawler_N_max_after_ready") == 0.0
        and run.get("n_crawler_recontact", 1) == 0,
        "loc": t_loc is not None
        and t_off is not None
        and (t_done is None or t_loc <= t_done + 1e-9)
        and t_loc - t_off <= LOC_DELAY_MAX_S + 1e-9,
        "Fmin": margin is not None and margin >= 0.0,
        "att": all(abs(a) <= ATTITUDE_TOL_DEG for a in att),
        "rut_stroke": (run.get("clear_true_ready_mm") or -1.0) >= RUT_MIN_MM
        and run.get("max_motor_stroke_mm", math.inf) <= STROKE_OK_MM,
        "fault_ready": run.get("final_phase") not in ("fault", "fault_reground")
        and run.get("t_ready_s") is not None,
    }


def _from_s9(run: dict) -> dict:
    if "error" in run:
        return {"id": run["id"], "error": run["error"]}
    names = _event_names(run.get("events"))
    t_loc = _event_time(run.get("events"), LOC_EVENT)
    t_off = run.get("t_crawler_off_first_s")
    gates = _s9_gates(run, t_loc)
    att = run.get("att_end_deg") or [math.nan, math.nan]
    meta = run.get("soil_rule_meta") or {}
    return {
        "id": run["id"],
        "sha": run.get("commands_sha256"),
        "pass": all(gates.values()),
        "failed": sorted(k for k, v in gates.items() if not v),
        "t_ready_s": run.get("t_ready_s"),
        "min_Fcyl_after_off_kN": run.get("min_true_Fcyl_after_off_kN"),
        "att_end_roll_deg": att[0],
        "att_end_pitch_deg": att[1],
        "rut_ready_mm": run.get("clear_true_ready_mm"),
        "rut_end_mm": None,
        "max_stroke_mm": run.get("max_motor_stroke_mm"),
        "c_min_tP_mm": None,
        "loc_delay_s": None if t_loc is None or t_off is None else t_loc - t_off,
        "s3_applied": _count(names, S3_EVENT) > 0,
        "anchor_applied": _count(names, ANCHOR_EVENT) > 0,
        "relax_D_kN": _relax_values_kN(names),
        "counts": {event: _count(names, event) for event in COUNT_KEYS},
        "counts_exact": True,
        "t_P_s": meta.get("t_P_s"),
        **_settle_fields(run.get("settle")),
        "error": None,
    }


def _from_slope(res: dict) -> dict:
    if "error" in res:
        return {"id": res["id"], "error": res["error"]}
    run, rows = res["run"], res["rows"]
    names = [name for _, name in res.get("events", [])]
    att = run.get("att_end_deg") or [math.nan, math.nan]
    check = (res.get("settle") or {}).get("check") or {}
    return {
        "id": res["id"],
        "sha": run.get("commands_sha256"),
        "pass": res["verdict"],
        "failed": list(res.get("failed_rows", [])),
        "t_ready_s": run.get("t_ready_s"),
        "min_Fcyl_after_off_kN": run.get("min_true_Fcyl_after_off_kN"),
        "att_end_roll_deg": att[0],
        "att_end_pitch_deg": att[1],
        "rut_ready_mm": run.get("clear_true_ready_mm"),
        "rut_end_mm": res.get("rut_end_mm"),
        "max_stroke_mm": run.get("max_motor_stroke_mm"),
        "c_min_tP_mm": rows["SL-3"].get("c_min_tP_mm"),
        "loc_delay_s": rows["P3-2"].get("loc_delay_s"),
        "s3_applied": _count(names, S3_EVENT) > 0,
        "anchor_applied": bool(rows["SL-3"].get("anchor_applied")),
        "relax_D_kN": _relax_values_kN(names),
        "counts": {event: _count(names, event) for event in COUNT_KEYS},
        "counts_exact": True,
        "settle_hook": (res.get("case") or {}).get("settle_table_status"),
        "settle_att_error_deg": check.get("attitude_error_deg"),
        "settle_gap_error_mm": check.get("pen_plus_gap_mm"),
        "error": None,
    }


def load_records(paths: str) -> dict[str, dict]:
    """Normalised records of one or more result files (';' separated), keyed by case id."""
    records: dict[str, dict] = {}
    for path in (Path(p) for p in paths.split(";") if p):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "runs" in payload:
            items = [_from_s9(run) for run in payload["runs"]]
        elif payload.get("results") and "rows" in next(
            (r for r in payload["results"] if "error" not in r), {}
        ):
            items = [_from_slope(res) for res in payload["results"]]
        else:
            items = [_from_g6(rec) for rec in payload["results"]]
        for item in items:
            records[item["id"]] = item
    return records


# ------------------------------------------------------------------------------ comparing
def _delta(new, base):
    if new is None or base is None:
        return None
    return new - base


def compare_case(base: dict, new: dict, c_min_bias_threshold_mm: float = 20.0) -> dict:
    """Differences of one case (new minus base)."""
    if base.get("error") or new.get("error"):
        return {"id": new["id"], "error": {"base": base.get("error"), "new": new.get("error")}}
    deltas = {key: _delta(new.get(key), base.get(key)) for key in DELTA_KEYS}
    c_base, c_new = base.get("c_min_tP_mm"), new.get("c_min_tP_mm")
    return {
        "id": new["id"],
        "sha_equal": base.get("sha") == new.get("sha"),
        "pass_base": base.get("pass"),
        "pass_new": new.get("pass"),
        "row_change": sorted(set(base.get("failed", [])) ^ set(new.get("failed", []))),
        "failed_base": base.get("failed"),
        "failed_new": new.get("failed"),
        "delta": deltas,
        "s3_flip": base.get("s3_applied") != new.get("s3_applied"),
        "s3_base": base.get("s3_applied"),
        "s3_new": new.get("s3_applied"),
        "anchor_flip": base.get("anchor_applied") != new.get("anchor_applied"),
        "c_min_crosses_20mm": None
        if c_base is None or c_new is None
        else (c_base > c_min_bias_threshold_mm) != (c_new > c_min_bias_threshold_mm),
        "c_min_tP_mm": [c_base, c_new],
        "relax_D_kN": [base.get("relax_D_kN"), new.get("relax_D_kN")],
        "counts": {
            event: [base["counts"].get(event, 0), new["counts"].get(event, 0)]
            for event in COUNT_KEYS
        },
        "counts_exact": bool(base.get("counts_exact") and new.get("counts_exact")),
        "settle_new": {
            k: new.get(k) for k in ("settle_hook", "settle_att_error_deg", "settle_gap_error_mm")
        },
        "settle_base": {
            k: base.get(k) for k in ("settle_hook", "settle_att_floor_deg", "settle_gap_mm")
        },
    }


def _stats(values: list[float]) -> dict | None:
    finite = [v for v in values if v is not None and math.isfinite(v)]
    if not finite:
        return None
    return {
        "n": len(finite),
        "min": min(finite),
        "median": statistics.median(finite),
        "max": max(finite),
        "max_abs": max(abs(v) for v in finite),
    }


def _settle_extremes(cases: list[dict]) -> dict:
    att = [
        abs(v) for c in cases for v in (c.get("settle_new", {}).get("settle_att_error_deg") or [])
    ]
    gap = [
        abs(v) for c in cases for v in (c.get("settle_new", {}).get("settle_gap_error_mm") or [])
    ]
    return {
        "att_error_max_abs_deg": max(att, default=None),
        "gap_error_max_abs_mm": max(gap, default=None),
        "n_cases_with_check": sum(
            1 for c in cases if c.get("settle_new", {}).get("settle_att_error_deg")
        ),
    }


def summarize(cases: list[dict], missing: dict) -> dict:
    ok = [c for c in cases if "error" not in c]
    count_totals = {
        event: [sum(c["counts"][event][0] for c in ok), sum(c["counts"][event][1] for c in ok)]
        for event in COUNT_KEYS
    }
    return {
        "n_compared": len(cases),
        "n_errors": len(cases) - len(ok),
        "missing": missing,
        "sha_equal": sum(1 for c in ok if c["sha_equal"]),
        "pass_flips": [c["id"] for c in ok if c["pass_base"] != c["pass_new"]],
        "row_changes": {c["id"]: c["row_change"] for c in ok if c["row_change"]},
        "delta_stats": {key: _stats([c["delta"][key] for c in ok]) for key in DELTA_KEYS},
        "s3_flips": [c["id"] for c in ok if c["s3_flip"]],
        "anchor_flips": [c["id"] for c in ok if c["anchor_flip"]],
        "c_min_20mm_crossings": [c["id"] for c in ok if c["c_min_crosses_20mm"]],
        "event_totals_base_new": count_totals,
        "counts_exact": all(c["counts_exact"] for c in ok),
        "settle_check_new": _settle_extremes(ok),
    }


def compare(base: dict[str, dict], new: dict[str, dict], focus: list[str]) -> dict:
    common = [key for key in new if key in base]
    cases = [compare_case(base[key], new[key]) for key in common]
    missing = {"only_base": sorted(set(base) - set(new)), "only_new": sorted(set(new) - set(base))}
    summary = summarize(cases, missing)
    summary["focus"] = [c for c in cases if any(f in c["id"] for f in focus)]
    return {"summary": summary, "cases": cases}


def _print_summary(summary: dict) -> None:
    print(
        f"compared {summary['n_compared']} (errors {summary['n_errors']}), "
        f"SHA equal {summary['sha_equal']}, only base {len(summary['missing']['only_base'])}, "
        f"only new {len(summary['missing']['only_new'])}"
    )
    print("pass flips:", summary["pass_flips"] or "-")
    print("row changes:", summary["row_changes"] or "-")
    print(
        "S-3 flips:",
        summary["s3_flips"] or "-",
        "| anchor flips:",
        summary["anchor_flips"] or "-",
        "| c_min 20 mm crossings:",
        summary["c_min_20mm_crossings"] or "-",
    )
    for key, stats in summary["delta_stats"].items():
        if stats:
            median, low, high = stats["median"], stats["min"], stats["max"]
            print(f"  d{key}: median {median:+.3f}, min {low:+.3f}, max {high:+.3f}")
    print(
        "events base/new:",
        summary["event_totals_base_new"],
        "exact" if summary["counts_exact"] else "(base counts from the first 40 events only)",
    )
    print("settle check (new):", summary["settle_check_new"])
    for case in summary["focus"]:
        print(
            "focus",
            case["id"],
            "S-3",
            case.get("s3_base"),
            "->",
            case.get("s3_new"),
            "c_min",
            case.get("c_min_tP_mm"),
            "rows",
            case.get("row_change"),
            "d",
            case.get("delta"),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="S9 settle hook: case-by-case comparison")
    parser.add_argument("base", help="reference / p0 result JSON (';' joins several)")
    parser.add_argument("new", help="new / harness result JSON (';' joins several)")
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--focus",
        default="G1+J2@FL|top,G1+J2@FR|top",
        help="comma list of case-id substrings printed in full",
    )
    args = parser.parse_args()
    result = compare(
        load_records(args.base), load_records(args.new), [f for f in args.focus.split(",") if f]
    )
    result["meta"] = {
        "script": "04_scripts/03_control/s9/s9_settle_hook_compare.py",
        "base": args.base,
        "new": args.new,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    _print_summary(result["summary"])


if __name__ == "__main__":
    main()
