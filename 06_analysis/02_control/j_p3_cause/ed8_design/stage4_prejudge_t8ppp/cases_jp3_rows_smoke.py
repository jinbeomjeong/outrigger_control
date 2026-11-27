"""Value-free smoke at T8''' (D-1): the J-P3 judged row count of the P8-2 cases lines.

Prints one JSON line with counts and structural reasons only: never a J-P3 status, a breach
count, a failure text, the ③ rev 7 condition or any line value. Everything the judge modules
print while reading is captured and only its line count is reported.

Exit 0: judged rows 10, runs expected 10, no rule-missing / unjudged-setting / key rows, the
C8 tuples restored. Exit 1: a count differs. Exit 2: argument or input error. Exit 3: error.

Usage (from the judge worktree root, dynamics-dev or the env the judge runs in):
  python -I -B cases_jp3_rows_smoke.py --judge-root JUDGE_ROOT --rows CASES_JSONL
  python -I -B cases_jp3_rows_smoke.py --judge-root JUDGE_ROOT --dry   (no rows: import check)
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

EXPECTED_JUDGED = 10
COUNT_KEYS = ("runs_expected", "rule_missing_runs", "test_only_setting_runs",
              "l1_reference_runs", "revision_key_missing_runs", "revision_key_mismatch_runs",
              "rev7_unjudged_setting_runs", "rev6_unjudged_setting_runs",
              "rev5_unjudged_setting_runs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-root", type=Path, required=True)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    root = args.judge_root.resolve()
    if args.dry == (args.rows is not None):
        print(json.dumps({"status": "input_error", "reason": "give --rows or --dry"}))
        return 2
    if args.rows is not None and not args.rows.is_file():
        print(json.dumps({"status": "input_error", "reason": "--rows is not a file"}))
        return 2
    for path in (root / "04_scripts" / "04_hydraulic" / "coupled", root / "03_src"):
        sys.path.insert(0, str(path))
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        import j_p3_inputs
        import jp3_ed7_judge as ed7
        import jp3_ed8_gate_judge as gate
        import jp3_ed8_judge as ed8

        saved = (j_p3_inputs.REV5_JUDGED_SETTINGS, j_p3_inputs.P3_OFF_SETTINGS)
        rows = [] if args.dry else gate.read_rows(args.rows)
        good = [row for row in rows if "error" not in row]
        folders = () if args.dry else tuple(ed7.t4h_folders_of(args.rows, good))
        report = ed8.jp3_of(good, folders)  # the T8''' wrapper itself (J-P3 + ③ condition)
        _, jp3_defects, jp3_unjudged = ed7.jp3_basis(report["J-P3"], None)  # failures unused
        restored = (j_p3_inputs.REV5_JUDGED_SETTINGS is saved[0]
                    and j_p3_inputs.P3_OFF_SETTINGS is saved[1])
        modules = {name: getattr(module, "__file__", None) for name, module in (
            ("j_p3_inputs", j_p3_inputs), ("jp3_ed7_judge", ed7), ("jp3_ed8_gate_judge", gate),
            ("jp3_ed8_judge", ed8))}
    jp3 = report["J-P3"]
    counts = {key: jp3.get(key) for key in COUNT_KEYS if key in jp3}
    outside = sorted(name for name, file in modules.items()
                     if file is None or not Path(file).resolve().is_relative_to(root))
    out = {"rows": len(rows), "error_rows": len(rows) - len(good),
           "lines_by_setting": dict(sorted(Counter(
               str((row.get("job") or {}).get("setting")) for row in good).items())),
           "judged_rows": report["J-P3_judged_rows"],
           "judged_settings_record": report.get("J-P3_judged_settings"),
           "hold_revision_blocks": sorted(key for key in jp3 if key in ("rev5", "rev6", "rev7")),
           "counts": counts,
           "jp3_setting_defect_texts": jp3_defects,
           "jp3_not_judgeable_texts": jp3_unjudged,
           "tuples_restored": restored, "modules_outside_judge_root": outside,
           "captured_output_lines": len(captured.getvalue().splitlines())}
    if args.dry:
        out["status"] = "dry"
        print(json.dumps(out, ensure_ascii=False))
        return 0 if restored and not outside else 1
    ok = (out["judged_rows"] == EXPECTED_JUDGED and counts.get("runs_expected") == EXPECTED_JUDGED
          and not any(counts.get(key) for key in COUNT_KEYS if key != "runs_expected")
          and not jp3_defects and not jp3_unjudged and restored and not outside
          and out["error_rows"] == 0)
    out["status"] = "ok" if ok else "count_mismatch"
    print(json.dumps(out, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - the type only, never a message with values
        print(json.dumps({"status": "error", "type": type(exc).__name__}))
        sys.exit(3)
