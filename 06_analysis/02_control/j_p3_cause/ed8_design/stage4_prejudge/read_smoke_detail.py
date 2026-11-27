"""Detail of the read smoke (state only): the reason texts of the setting-defect and
not-judgeable lists of J-P3 / ③ rev 7 condition, and the item names (first token) of the
not-judgeable unit items. Failure lists, statuses that can mean a failure, values and
per-line results are never written.

Run with dynamics-dev ``python.exe -I -B`` from the judge worktree root:
  python -I -B <this file> <judge root> <stage root> <out.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

JUDGE_ROOT, STAGE_ROOT, OUT = (Path(arg) for arg in sys.argv[1:4])
MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(JUDGE_ROOT / "04_scripts" / "04_hydraulic" / "coupled"))

import ed8_key_lists as keys  # noqa: E402
import jp3_ed7_judge as ed7  # noqa: E402
import jp3_ed8_judge as ed8  # noqa: E402

V0_MAIN = MAIN / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def judged_rows_bucket(count: int, expected: int | None) -> str:
    if count == 0:
        return "0"
    if expected is not None:
        return "equal to expected" if count == expected else "other than expected"
    return "> 0"


def jp3_state(rows: list[dict], folders, expected: int | None) -> dict:
    jp3 = ed8.jp3_of(rows, folders)
    return {"lines": len(rows),
            "judged_rows": judged_rows_bucket(jp3["J-P3_judged_rows"], expected),
            "setting_defects": jp3["basis"]["setting_defects"],
            "not_judgeable": jp3["basis"]["not_judgeable"]}


def item_names(texts) -> list[str]:
    return [str(text).split(" ", 1)[0] for text in texts]


def main() -> int:
    t8_path = STAGE_ROOT / "impl_t8_a1" / "ed8_t8.jsonl"
    cases_path = STAGE_ROOT / "impl_cases_a1" / "ed8_cases.jsonl"
    t8 = read_jsonl(t8_path)
    cases = read_jsonl(cases_path)
    t8_folders = tuple(ed7.t4h_folders_of(t8_path, t8))
    case_folders = tuple(ed7.t4h_folders_of(cases_path, cases))
    report: dict = {"note": "reason texts of defect / not-judgeable lists only"}

    report["jp3 impl_cases (as judge_cases)"] = jp3_state(cases, case_folders, ed8.CASE_ROWS)
    for setting in ("VBN", "VBN0"):
        part = [row for row in t8 if row["job"]["setting"] == setting]
        report[f"jp3 impl_t8 {setting}"] = jp3_state(part, t8_folders, None)
        events = [row for row in part if not row.get("head_only_declared")]
        report[f"jp3 impl_t8 {setting} not head-only"] = jp3_state(events, t8_folders, None)

    # not-judgeable unit items of the C-J reading (item names only)
    folders = t8_folders + case_folders
    rows = t8 + cases
    v0_by_job = ed8.v0_rows_by_job(V0_MAIN)
    v0_lines = {keys.plain_job_key(row["job"]): v0_by_job.get(keys.plain_job_key(row["job"]))
                for row in rows}
    report["lines without a V0 main line (by setting)"] = dict(Counter(
        row["job"]["setting"] for row in rows
        if v0_lines[keys.plain_job_key(row["job"])] is None))
    v0_metrics = [ed7.metric_of(row, folders, ed8.V0_LABEL)
                  for row in v0_lines.values() if row is not None]
    vb = [ed7.metric_of(dict(row), folders, ed8.TREATMENT_LABEL) for row in rows
          if row["job"]["setting"] == "VBN"]
    verdicts = ed8.unit_item_verdicts(vb, v0_metrics)
    names = Counter()
    for unit in verdicts["units"].values():
        names.update(item_names(unit["not_judgeable_items"]))
    report["C-J unit not-judgeable item names"] = dict(names)

    # LS against VB (C-J (ii)): the not-judgeable item names
    import jp3_ed6_judge as ed6
    import jp3_j9main_judge as base
    import judge_stage1_4368 as path1

    cj = [ed7.metric_of(dict(row), folders, ed8.CJ_LABEL[row["job"]["setting"]])
          for row in rows if row["job"]["setting"] in ed8.CJ_LABEL]
    rows_by = path1._by_setting(cj + v0_metrics)
    j_vs_v0 = base._full_items(rows_by, (ed8.TREATMENT_LABEL,), ed8.V0_LABEL)
    ls_vs_vb = base._full_items(rows_by, path1.LS_SETTINGS, ed8.TREATMENT_LABEL)
    ed7.replace_j7(ls_vs_vb, rows_by, ed8.TREATMENT_LABEL)
    ed6.apply_reading_1(ls_vs_vb, rows_by, ed8.TREATMENT_LABEL)
    ed7.replace_j7(j_vs_v0, rows_by, ed8.V0_LABEL)
    ed6.apply_reading_1(j_vs_v0, rows_by, ed8.V0_LABEL)
    groups = ed7._j9main_items(j_vs_v0, ls_vs_vb, rows_by)
    report["C-J (ii) LS not-judgeable items (setting, item)"] = dict(Counter(
        f"{item.get('setting')} {item.get('item')}" for item in groups["not_judgeable_items"]
        if item.get("setting") in path1.LS_SETTINGS))
    report["C-J (ii) LS no_reference (setting count)"] = {
        setting: len(ls_vs_vb[setting]["no_reference"]) for setting in ls_vs_vb}

    OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": "written", "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
