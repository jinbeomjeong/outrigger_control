"""Spec 420.2b (U-S9-G6d (가)): re-judge the G6-1 crawler row of a stored wrapper g6 run
(``s9_slope_fix_candidates.py run --suite g6``) without re-running the harness.

Per record: G6-1 = READY crawler load 0 (``metrics.ready_crawler_max_kN``, the wrapper's READY
log) and no ``strict_fail`` recontact (``late_loc_rule.crawler_gate`` on the record's own
``metrics.crawler_recontact``, the run_S9 ``recontact_events`` classes on the 1 ms crawler
force); a ``transient_flag`` recontact passes with ``P3-1_transient_recontact``. Records whose
id and command hash are also in the cross-check file (e.g. ``fix_g6_LW_recontact.json``) must
carry the same recontact classes there.

Usage (project root, any env with numpy):
  python -I 04_scripts/03_control/s9/g6_rejudge_g6d.py <run_json> <cross_check_json> <out_json>
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

G61_ROW = "G6-1_crawler"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _classes(recontact: dict | None) -> list[str] | None:
    if recontact is None:
        return None
    return [event["class"] for event in recontact["recontact_events"]["events"]]


def _cross_check_classes(path: Path) -> dict[tuple[str, str], list[str] | None]:
    """(id, command hash) -> recontact classes of the cross-check file."""
    records = json.loads(path.read_text(encoding="utf-8"))["records"]
    return {(r["id"], r.get("hash")): _classes((r.get("metrics") or {}).get("crawler_recontact"))
            for r in records if "error" not in r}


def rejudge_record(record: dict, cross_check: dict) -> dict:
    """Before / after of one stored g6 record (failed rows, flags, recontact classes)."""
    metrics = record.get("metrics") or {}
    recontact = metrics.get("crawler_recontact")
    failed_before = list(record.get("failed_rows") or [])
    flags_before = list(record.get("flags") or [])
    passes, crawler_flags = late_loc_rule.crawler_gate(
        metrics.get("ready_crawler_max_kN") == 0.0, recontact,
        legacy_recontact_count=0 if G61_ROW not in failed_before else 1)
    failed_after = [row for row in failed_before if row != G61_ROW]
    if not passes:
        failed_after.insert(0, G61_ROW)
    flags_after = flags_before + [flag for flag in crawler_flags if flag not in flags_before]
    classes = _classes(recontact)
    key = (record["id"], record.get("hash"))
    return {"id": record["id"], "candidate": record.get("candidate"), "hash": record.get("hash"),
            "recontact_classes": classes,
            "cross_check_classes": cross_check.get(key, "not in cross-check file"),
            "cross_check_agrees": key not in cross_check or cross_check[key] == classes,
            "failed_rows_before": failed_before, "failed_rows_after": failed_after,
            "flags_before": flags_before, "flags_after": flags_after,
            "verdict_before": record.get("verdict"),
            "verdict_after": "pass" if not failed_after else "fail"}


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    run_path, cross_path, out_path = (Path(arg) for arg in sys.argv[1:])
    cross_check = _cross_check_classes(cross_path)
    records = [r for r in json.loads(run_path.read_text(encoding="utf-8"))["records"]
               if r.get("suite", "g6") == "g6" and "error" not in r]
    rows = [rejudge_record(record, cross_check) for record in records]
    changed = [row for row in rows if row["failed_rows_before"] != row["failed_rows_after"]
               or row["flags_before"] != row["flags_after"]]
    summary = {
        "records": len(rows),
        "g6_1_failed_before": sum(G61_ROW in row["failed_rows_before"] for row in rows),
        "g6_1_failed_after": sum(G61_ROW in row["failed_rows_after"] for row in rows),
        "with_transient_flag": sum("transient_flag" in (row["recontact_classes"] or [])
                                   for row in rows),
        "with_strict_fail": sum("strict_fail" in (row["recontact_classes"] or []) for row in rows),
        "without_recontact_record": sum(row["recontact_classes"] is None for row in rows),
        "cross_checked": sum(row["cross_check_classes"] != "not in cross-check file"
                             for row in rows),
        "cross_check_disagreements": sum(not row["cross_check_agrees"] for row in rows),
        "changed_records": len(changed),
    }
    meta = {"script": "04_scripts/03_control/s9/g6_rejudge_g6d.py",
            "rule": "spec 420.2b, U-S9-G6d (가): G6-1 = READY crawler 0 and no strict_fail "
                    "recontact; transient_flag -> FLAG P3-1_transient_recontact",
            "function": "late_loc_rule.crawler_gate",
            "recontact_source": "metrics.crawler_recontact of each run record (run_S9 "
                                "recontact_events on the 1 ms crawler force); cross-checked "
                                "against the same id + hash in the cross-check file",
            "ready_crawler_source": "metrics.ready_crawler_max_kN",
            "input": {"path": str(run_path), "sha256": _sha256(run_path)},
            "cross_check": {"path": str(cross_path), "sha256": _sha256(cross_path)},
            "commands": "unchanged (judgement only, no harness run)"}
    out_path.write_text(json.dumps({"meta": meta, "summary": summary, "changed": changed,
                                    "records": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
