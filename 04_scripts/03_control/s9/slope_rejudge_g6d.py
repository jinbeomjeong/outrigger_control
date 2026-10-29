"""Spec 420.2b (U-S9-G6d (가)) on study 1: re-judge the P3-1 crawler row of a stored wrapper
slope run (``s9_slope_fix_candidates.py run --suite slope``) without re-running the harness.

Per record: P3-1 = crawler load 0 after READY (``crawler_N_max_after_ready``), READY reached
(``t_ready_s``) and no ``strict_fail`` recontact (``late_loc_rule.crawler_gate`` on the record's
``metrics.crawler_recontact``, the run_S9 ``recontact_events`` classes on the 1 ms crawler
force); ``transient_flag`` passes with ``P3-1_transient_recontact``.

Verdict after (``s9_soil_slope.classify`` on the stored failed rows):
  * unjudged runs (``settle_check_fail``, error) stay as they are;
  * plain class: ``pass`` when no row fails, else ``fail``;
  * stroke-limited class: ``stroke_limited_fail`` while P3-1 / P3-3 / P3-4 or ``fault_ready``
    fail; otherwise ``undetermined`` (the lifted-leg condition is not in the wrapper record).

Usage (project root, any env with numpy):
  python -I 04_scripts/03_control/s9/slope_rejudge_g6d.py <run_json> <out_json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import late_loc_rule  # noqa: E402

P31_ROW = "P3-1"
UNJUDGED_VERDICTS = ("settle_check_fail", "error")
STROKE_LIMITED_BLOCKING_ROWS = ("P3-1", "P3-3", "P3-4", "fault_ready")
"""``is_stroke_limited_pass``: required rows plus FAULT 0 (``fault_ready`` covers it)."""


def _classes(recontact: dict | None) -> list[str] | None:
    if recontact is None:
        return None
    return [event["class"] for event in recontact["recontact_events"]["events"]]


def _verdict_after(verdict_before: str, failed_after: list[str]) -> str:
    if verdict_before in UNJUDGED_VERDICTS:
        return verdict_before
    if verdict_before.startswith("stroke_limited"):
        if any(row in failed_after for row in STROKE_LIMITED_BLOCKING_ROWS):
            return "stroke_limited_fail"
        return verdict_before if verdict_before == "stroke_limited_pass" else "undetermined"
    return "pass" if not failed_after else "fail"


def rejudge_record(record: dict) -> dict:
    """Before / after of one stored slope record (failed rows, flags, verdict, classes)."""
    recontact = (record.get("metrics") or {}).get("crawler_recontact")
    failed_before = list(record.get("failed_rows") or [])
    flags_before = list(record.get("flags") or [])
    is_crawler_ok, crawler_flags = late_loc_rule.crawler_gate(
        record.get("crawler_N_max_after_ready") == 0.0, recontact,
        legacy_recontact_count=0 if P31_ROW not in failed_before else 1)
    is_pass = bool(is_crawler_ok and record.get("t_ready_s") is not None)
    failed_after = [row for row in failed_before if row != P31_ROW]
    if not is_pass:
        failed_after.insert(0, P31_ROW)
    flags = crawler_flags if is_pass else []
    flags_after = flags_before + [flag for flag in flags if flag not in flags_before]
    return {"id": record["id"], "hash": record.get("hash"),
            "recontact_classes": _classes(recontact),
            "crawler_N_max_after_ready": record.get("crawler_N_max_after_ready"),
            "t_ready_s": record.get("t_ready_s"),
            "failed_rows_before": failed_before, "failed_rows_after": sorted(failed_after),
            "flags_before": flags_before, "flags_after": flags_after,
            "verdict_before": record.get("verdict"),
            "verdict_after": _verdict_after(record.get("verdict") or "error", failed_after)}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    run_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    records = [r for r in json.loads(run_path.read_text(encoding="utf-8"))["records"]
               if r.get("suite", "slope") == "slope" and "error" not in r]
    rows = [rejudge_record(record) for record in records]
    changed = [row for row in rows if sorted(row["failed_rows_before"]) != row["failed_rows_after"]
               or row["flags_before"] != row["flags_after"]
               or row["verdict_before"] != row["verdict_after"]]
    judged = [row for row in rows if row["verdict_before"] not in UNJUDGED_VERDICTS]
    summary = {
        "records": len(rows),
        "p3_1_failed_before": sum(P31_ROW in row["failed_rows_before"] for row in rows),
        "p3_1_failed_after": sum(P31_ROW in row["failed_rows_after"] for row in rows),
        "p3_1_failed_before_judged": sum(P31_ROW in row["failed_rows_before"] for row in judged),
        "p3_1_failed_after_judged": sum(P31_ROW in row["failed_rows_after"] for row in judged),
        "with_transient_flag": sum("transient_flag" in (row["recontact_classes"] or [])
                                   for row in rows),
        "with_strict_fail": sum("strict_fail" in (row["recontact_classes"] or []) for row in rows),
        "without_recontact_record": sum(row["recontact_classes"] is None for row in rows),
        "verdict_changes": [[row["id"], row["verdict_before"], row["verdict_after"]]
                            for row in rows if row["verdict_before"] != row["verdict_after"]],
        "changed_records": len(changed),
    }
    meta = {"script": "04_scripts/03_control/s9/slope_rejudge_g6d.py",
            "rule": "spec 420.2b, U-S9-G6d (가): P3-1 = crawler 0 after READY, READY reached and "
                    "no strict_fail recontact; transient_flag -> FLAG P3-1_transient_recontact",
            "function": "late_loc_rule.crawler_gate",
            "recontact_source": "metrics.crawler_recontact of each run record (run_S9 "
                                "recontact_events on the 1 ms crawler force)",
            "input": {"path": str(run_path),
                      "sha256": hashlib.sha256(run_path.read_bytes()).hexdigest()},
            "commands": "unchanged (judgement only, no harness run)"}
    out_path.write_text(json.dumps({"meta": meta, "summary": summary, "changed": changed,
                                    "records": rows}, indent=1), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "verdict_changes"}))
    for item in summary["verdict_changes"]:
        print("verdict", item)


if __name__ == "__main__":
    main()
