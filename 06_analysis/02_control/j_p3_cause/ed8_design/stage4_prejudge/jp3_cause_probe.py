"""Cause probe of "J-P3 0 judged rows" on the edition 8 lines (state only).

``j_p3_inputs.REV5_JUDGED_SETTINGS`` (the hold revision rows J-P3 judges) holds the edition
5 / 6 / 7 names only. In this process only (no file is changed) the edition 8 judged names
``run_v5.ED8_JUDGED_SETTINGS`` are added, and ``jp3_ed8_judge.jp3_of`` is run again on the
``impl_cases`` lines. Only the judged-row bucket and the setting-defect / not-judgeable texts
are written; the failure list and the J-P3 status are not.

Run with dynamics-dev ``python.exe -I -B`` from the judge worktree root:
  python -I -B <this file> <judge root> <stage root> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

JUDGE_ROOT, STAGE_ROOT, OUT = (Path(arg) for arg in sys.argv[1:4])
sys.path.insert(0, str(JUDGE_ROOT / "04_scripts" / "04_hydraulic" / "coupled"))

import j_p3_inputs  # noqa: E402
import jp3_ed7_judge as ed7  # noqa: E402
import jp3_ed8_judge as ed8  # noqa: E402
import run_v5  # noqa: E402


def state(rows, folders) -> dict:
    jp3 = ed8.jp3_of(rows, folders)
    count = jp3["J-P3_judged_rows"]
    bucket = "0" if count == 0 else ("equal to 10" if count == ed8.CASE_ROWS else "other")
    return {"judged_rows": bucket, "setting_defects": jp3["basis"]["setting_defects"],
            "not_judgeable": jp3["basis"]["not_judgeable"]}


def main() -> int:
    path = STAGE_ROOT / "impl_cases_a1" / "ed8_cases.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    folders = tuple(ed7.t4h_folders_of(path, rows))
    report = {"ed8_names_in_REV5_JUDGED_SETTINGS": sorted(
        set(run_v5.ED8_JUDGED_SETTINGS) & set(j_p3_inputs.REV5_JUDGED_SETTINGS)),
        "line_settings": sorted({row["job"]["setting"] for row in rows}),
        "as_is": state(rows, folders)}
    saved = j_p3_inputs.REV5_JUDGED_SETTINGS
    j_p3_inputs.REV5_JUDGED_SETTINGS = (*saved, *run_v5.ED8_JUDGED_SETTINGS)
    try:
        report["with_ed8_names_in_memory"] = state(rows, folders)
    finally:
        j_p3_inputs.REV5_JUDGED_SETTINGS = saved
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": "written", "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
