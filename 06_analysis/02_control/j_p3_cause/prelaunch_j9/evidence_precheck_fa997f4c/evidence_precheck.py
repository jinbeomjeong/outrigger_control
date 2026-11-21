"""Erratum 1 9 precheck of the J-P3 judged-setting lines of an attempt's steps 4a / 4b.

Reads per line only: ``job`` (identifier), the line's ``head_only_declared``, the T4h meta key
``head_only_declared`` and ``hydraulics_record.rod_reading_truth_calls`` (1) /
``two_pressure_reads`` (2). It prints counts and the identifiers (job, setting) of lines that
break the rule, with the rule part broken; it never prints a value.

Rule (addendum 4a-7 erratum 1 9): an event-path line 1 = 2 > 0, a declared head-only line
1 = 2 = 0, a missing or non-integer key = a defect. Declared: T4h meta, else the line, else
the steady path of its ``verdict_cases`` case (4a-7 1.1); undecided = event path (erratum 3).

Usage: python -I -B evidence_precheck.py <attempt root> <worktree> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np

JUDGED_SETTINGS = ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")
EVIDENCE_KEYS = ("rod_reading_truth_calls", "two_pressure_reads")
HEAD_ONLY_KEY = "head_only_declared"
STEP_FILES = {"cases": ("j9_cases.jsonl", "cd.jsonl"), "casef": ("j9_case_f.jsonl",)}


def step_folder(root: Path, step: str) -> Path:
    marker = json.loads((root / f"{step}.done").read_text(encoding="utf-8"))
    return root / Path(marker["folder"]).name


def t4h_declaration(rows_file: Path, line: dict):
    name = line.get("t4h_file")
    if not name:
        return None
    npz = rows_file.with_name(f"{rows_file.stem}_t4h") / Path(name).name
    if not npz.is_file():
        return None
    with np.load(npz, allow_pickle=False) as data:
        if "meta_json" not in data.files:
            return None
        return json.loads(str(data["meta_json"])).get(HEAD_ONLY_KEY)


def declaration(rows_file: Path, line: dict, verdict_cases) -> tuple[bool, str]:
    meta_value = t4h_declaration(rows_file, line)
    if meta_value is not None:
        return bool(meta_value), "t4h_meta"
    if line.get(HEAD_ONLY_KEY) is not None:
        return bool(line[HEAD_ONLY_KEY]), "line"
    case = verdict_cases.CASES.get((line.get("job") or {}).get("case"))
    if case is not None:
        return case.path == verdict_cases.PATH_STEADY, "case_table"
    return False, "undecided_event"


def broken_part(record: dict, is_declared: bool) -> str | None:
    """The rule part the line breaks (None = sound); no value goes into the text."""
    values = [record.get(key) for key in EVIDENCE_KEYS]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return "evidence key missing or not an integer"
    truth, reads = values
    if is_declared:
        return None if truth == 0 and reads == 0 else "declared line: 1 = 2 = 0 not met"
    return None if reads > 0 and truth == reads else "event line: 1 = 2 > 0 not met"


def main() -> int:
    root, worktree, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    for path in (worktree / "04_scripts" / "04_hydraulic" / "coupled", worktree / "03_src"):
        sys.path.insert(0, str(path))
    import verdict_cases

    report = {"root": str(root), "files": {}}
    for step, names in STEP_FILES.items():
        folder = step_folder(root, step)
        for name in names:
            rows_file = folder / name
            lines = [json.loads(text) for text in rows_file.read_text(encoding="utf-8").splitlines()
                     if text]
            entry = {"lines": len(lines), "judged_lines": 0, "sound": 0, "broken": [],
                     "error_lines": 0, "declared": 0, "basis": {}}
            for line in lines:
                setting = (line.get("job") or {}).get("setting")
                if setting not in JUDGED_SETTINGS:
                    continue
                entry["judged_lines"] += 1
                if "error" in line:
                    entry["error_lines"] += 1
                    entry["broken"].append({"job": line.get("job"), "part": "error line"})
                    continue
                is_declared, basis = declaration(rows_file, line, verdict_cases)
                entry["declared"] += int(is_declared)
                entry["basis"][basis] = entry["basis"].get(basis, 0) + 1
                part = broken_part(line.get("hydraulics_record") or {}, is_declared)
                if part is None:
                    entry["sound"] += 1
                else:
                    entry["broken"].append({"job": line.get("job"), "part": part})
            report["files"][f"{folder.name}/{name}"] = entry
    total_broken = sum(len(entry["broken"]) for entry in report["files"].values())
    total_judged = sum(entry["judged_lines"] for entry in report["files"].values())
    report.update(judged_lines=total_judged, broken_lines=total_broken)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    status = "pass" if total_judged > 0 and total_broken == 0 else (
        "not_judgeable" if total_judged == 0 else "broken")
    print(json.dumps({"status": status, "judged_lines": total_judged,
                      "broken_lines": total_broken, "out": str(out)}))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
