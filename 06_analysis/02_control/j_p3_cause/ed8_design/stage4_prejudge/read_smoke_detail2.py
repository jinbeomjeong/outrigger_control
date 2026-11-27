"""Detail 2 of the read smoke (state only): the fixed reason texts of the L-c not-judgeable
items and the item names of the C-S not-judgeable units (by setting), to tell a smoke
artifact (a line without a stored V0 line of its job) from a reading defect.

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
import jp3_j9main_judge as base  # noqa: E402
import judge_stage1_4368 as path1  # noqa: E402
import run_v5  # noqa: E402

V0_MAIN = MAIN / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
LC_REASONS = ("no V0 n_rev maximum of the group", "n_rev None")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def main() -> int:
    t8_path = STAGE_ROOT / "impl_t8_a1" / "ed8_t8.jsonl"
    cases_path = STAGE_ROOT / "impl_cases_a1" / "ed8_cases.jsonl"
    t8, cases = read_jsonl(t8_path), read_jsonl(cases_path)
    rows = t8 + cases
    folders = tuple(ed7.t4h_folders_of(t8_path, t8)) + tuple(ed7.t4h_folders_of(cases_path,
                                                                                 cases))
    v0_by_job = ed8.v0_rows_by_job(V0_MAIN)
    v0_unique = {}
    for row in rows:
        found = v0_by_job.get(keys.plain_job_key(row["job"]))
        if found is not None:
            v0_unique[keys.plain_job_key(found["job"])] = found
    v0_metrics = [ed7.metric_of(row, folders, ed8.V0_LABEL) for row in v0_unique.values()]
    cj = [ed7.metric_of(dict(row), folders, ed8.CJ_LABEL[row["job"]["setting"]])
          for row in rows if row["job"]["setting"] in ed8.CJ_LABEL]
    lc = base.limit_cycle_suspects(path1._by_setting(cj + v0_metrics))
    report = {"L-c not-judgeable reasons": dict(Counter(
        item["detail"] if item["detail"] in LC_REASONS else "other"
        for item in lc["not_judgeable"]))}
    own = [ed7.metric_of(dict(row), folders, row["job"]["setting"]) for row in rows]
    settings = (*run_v5.ED8_SENSITIVITY_SETTINGS, *run_v5.ED8_SENSITIVITY_RECORD_SETTINGS)
    judged = ed7.unit_table(own, v0_metrics, settings)
    verdicts = ed7.unit_verdicts(own, judged)
    names = Counter()
    for (setting, _, _), verdict in verdicts.items():
        if verdict["verdict"] == ed7.VERDICT_MISSING:
            for text in verdict["not_judgeable_items"]:
                name = "no V0 line" if text.startswith("no V0 line") else text.split(" ", 1)[0]
                names[f"{setting} {name}"] += 1
    report["C-S not-judgeable unit item names (setting item)"] = dict(names)
    report["sensitivity settings named by run_v5"] = list(settings)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": "written", "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
