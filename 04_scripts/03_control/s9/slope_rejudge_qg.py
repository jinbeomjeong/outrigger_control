"""Spec 423.3 / 423.4 (decision Q-G) on a stored ``s9_soil_slope.py`` result (e.g. the H6 run
``rev82/r82_mass_scale.json``): re-judge P3-1 with the threshold-chatter class, no harness run.

Per result: the stored P3-1 ``recontact_events`` are re-classified
(``late_loc_rule.reclassify_recontacts``: t_LOC of the P3-2 row, the events' ``limit_N``, READY
of the P3-6 row); P3-1 = ``late_loc_rule.crawler_gate`` (crawler 0 after READY, no strict
recontact) and READY reached; the verdict is recomputed by ``s9_soil_slope.rejudge_stored``.
Results without the recorded events keep their stored P3-1 row.

Usage (project root, any env with numpy):
  python -I 04_scripts/03_control/s9/slope_rejudge_qg.py <result_json> <out_json>
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import late_loc_rule  # noqa: E402
import s9_soil_slope as slope  # noqa: E402

P31_ROW = "P3-1"


def rejudged_p31_row(row: dict, t_loc_s: float | None, t_ready_s: float | None) -> dict:
    """The P3-1 row with the 423.3 classes (unchanged without recorded events)."""
    events = row.get("recontact_events")
    if events is None:
        return row
    reclassified = late_loc_rule.reclassify_recontacts(events, t_loc_s, events["limit_N"],
                                                       t_ready_s)
    is_crawler_ok, flags = late_loc_rule.crawler_gate(
        row.get("crawler_N_max_after_ready") == 0.0, {"recontact_events": reclassified},
        row.get("n_recontact"))
    is_pass = bool(is_crawler_ok and t_ready_s is not None)
    return {**row, "pass": is_pass, "flag": bool(is_pass and flags),
            "flag_name": flags[0] if is_pass and flags else None,
            "flag_names": flags if is_pass else [], "recontact_events": reclassified}


def rejudge_result(result: dict) -> tuple[dict, dict]:
    """(re-judged result, before / after record) of one stored result."""
    if "error" in result or "rows" not in result:
        return result, {"id": result.get("id"), "skipped": result.get("error", "no rows")}
    rows = result["rows"]
    before_p31 = rows[P31_ROW]
    after_p31 = rejudged_p31_row(before_p31, rows["P3-2"].get("t_loc_s"),
                                 rows["P3-6"].get("t_ready_s"))
    updated = copy.deepcopy(result)
    updated["rows"][P31_ROW] = after_p31
    rejudged = slope.rejudge_stored(updated)
    rejudged["failed_rows"] = sorted(k for k, v in rejudged["rows"].items()
                                     if v.get("pass") is False)

    def classes(row: dict) -> list[str] | None:
        events = row.get("recontact_events")
        return None if events is None else [e["class"] for e in events["events"]]

    return rejudged, {
        "id": result["id"],
        "p3_1_classes_before": classes(before_p31), "p3_1_classes_after": classes(after_p31),
        "p3_1_pass_before": before_p31.get("pass"), "p3_1_pass_after": after_p31.get("pass"),
        "p3_1_flags_after": after_p31.get("flag_names", []),
        "failed_rows_before": result.get("failed_rows"),
        "failed_rows_after": rejudged["failed_rows"],
        "verdict_before": result.get("verdict"), "verdict_after": rejudged["verdict"]}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    in_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    data = json.loads(in_path.read_text(encoding="utf-8"))
    pairs = [rejudge_result(result) for result in data["results"]]
    cases = [record for _, record in pairs]
    judged = [record for record in cases if "skipped" not in record]
    summary = {
        "results": len(cases),
        "verdict_before": dict(Counter(r["verdict_before"] for r in judged)),
        "verdict_after": dict(Counter(r["verdict_after"] for r in judged)),
        "p3_1_failed_before": sum(r["p3_1_pass_before"] is False for r in judged),
        "p3_1_failed_after": sum(r["p3_1_pass_after"] is False for r in judged),
        "changed": [r["id"] for r in judged
                    if r["verdict_before"] != r["verdict_after"]
                    or r["p3_1_pass_before"] != r["p3_1_pass_after"]],
    }
    meta = {"script": "04_scripts/03_control/s9/slope_rejudge_qg.py",
            "rule": "spec 423.3 (Q-G): threshold chatter after the LOC = FLAG "
                    "P3-1_threshold_chatter; verdict by s9_soil_slope.rejudge_stored",
            "functions": ["late_loc_rule.reclassify_recontacts", "late_loc_rule.crawler_gate",
                          "s9_soil_slope.rejudge_stored"],
            "chatter_constants": {"after_loc_s": late_loc_rule.CHATTER_AFTER_LOC_S,
                                  "max_duration_s": late_loc_rule.CHATTER_MAX_DURATION_S,
                                  "max_over_threshold": late_loc_rule.CHATTER_MAX_OVER_THRESHOLD},
            "input": {"path": str(in_path),
                      "sha256": hashlib.sha256(in_path.read_bytes()).hexdigest()},
            "commands": "unchanged (judgement only, no harness run)"}
    out_path.write_text(json.dumps({"meta": meta, "summary": summary, "cases": cases,
                                    "results": [result for result, _ in pairs]},
                                   indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
