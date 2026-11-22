"""436.9 edition 5 P5-1 (``jp3_remedy_spec_v5.md`` 5, 4.5 T8): command hashes of the rows that
stages (1) .. (6) run again, this edition against the edition 4a run commit ``78fd5d2d``.

Rule: a row pair (the same job in both runs) without ``WARN_ROD_PRESSURE_FALLBACK`` on either
side has the same ``commands_sha256``; a row of a setting with ③ off or ③ revision 4
(:data:`ALWAYS_EQUAL_SETTINGS`: VBJ0, VB, VBK0) has it whatever the fallbacks. A pair with a
fallback on a ③ rev 6 row is recorded only (its commands may differ by design).

Rows are paired by job identity: the r79 ``key`` without its ``cand=...#`` prefix, else the
run_v5 ``job`` without the run-time keys (``mask``, ``t4h_dir``), with the setting. The
fallback is read from the full event list of the row's T4h record when ``--old-t4h`` /
``--new-t4h`` name the folders (``meta_json.events``), else from the row: r79 lines
``r79.rod_fallback`` and ``rod_fallback_reasons``, run_v5 rows ``events`` (cut at
:data:`ROW_EVENT_CAP`: a row at the cap without a T4h record is not judgeable).

Usage (any env with numpy, project root; read only):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_p51_compare.py --old <78fd5d2d rows>
      --new <edition 5 rows> [--old-t4h <folder>] [--new-t4h <folder>] --out <report.json>
(one pair of row files per call; a run file is JSON ``{"results": [...]}``, a JSON list or
JSON lines.)

======  =================  ==================================================================
exit    status             meaning
======  =================  ==================================================================
0       ``pass``           every judged pair has the same hash (at least one judged pair)
1       ``differ``         a judged pair differs: stop (P5-1), also with the problems below
                           (kept in ``problems``, erratum 2 2-10)
2       ``not_judgeable``  no differing pair and: a row of one side only, a repeated job, a
                           row without a 64-hex
                           hash, an event list at the cap, no judged pair, an existing --out
3       ``error``          a tool error (unreadable file, broken JSON)
======  =================  ==================================================================

The stdout's last line is JSON with ``status``, the counts and the report path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
ALWAYS_EQUAL_SETTINGS = ("VBJ0", "VB", "VBK0", "LSJ4_X11")
"""③ off (VBJ0, VBK0), ③ revision 4 (VB) or the X11 arm on ③ revision 5 (erratum 1 1: its
rev 5 path is unchanged, so its hash equals the 78fd5d2d X11 line): equal whatever the
fallbacks (P5-1)."""
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")
SETTING_OF_PREVIOUS_EDITION = {"VBG6": "VBG5"}
"""Case D: edition 5 runs it as VBG6 (③ rev 6), edition 4a ran the same job as VBG5
(``jp3_case_replay.CASE_D_PREVIOUS_SETTING``); erratum 1 2: the pair's hashes are equal when
neither side has a fallback (T8 under the name map), else a record."""
ROW_EVENT_CAP = 400
"""``verdict_runs._finish`` keeps the first 400 events of a run_v5 row."""
HASH = re.compile(r"^[0-9a-f]{64}$")
EXIT_PASS, EXIT_DIFFER, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3


def read_rows(path: Path) -> list[dict]:
    """A run file: one JSON document (``{"results": [...]}`` or a list), else JSON lines."""
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(document, dict):  # a run file, or a JSON lines file of one row
        return document["results"] if "results" in document else [document]
    return document


def identity(row: dict) -> str:
    """The pairing key of a row (r79 key without the candidate prefix, or the run_v5 job; a
    setting of :data:`SETTING_OF_PREVIOUS_EDITION` takes its edition 4a name)."""
    if isinstance(row.get("key"), str):
        key = row["key"]
        return "r79:" + (key.split("#", 1)[1] if "#" in key else key)
    job = {name: value for name, value in (row.get("job") or {}).items()
           if name not in RUNTIME_JOB_KEYS}
    if job.get("setting") in SETTING_OF_PREVIOUS_EDITION:
        job["setting"] = SETTING_OF_PREVIOUS_EDITION[job["setting"]]
    return "job:" + json.dumps(job, sort_keys=True)


def setting_of(row: dict) -> str | None:
    return row.get("v5_setting") or (row.get("job") or {}).get("setting")


def t4h_events(row: dict, folder: Path | None) -> list | None:
    """The full event list of the row's T4h record (None: no folder or no record)."""
    name = row.get("t4h_file")
    if folder is None or not name or not (folder / name).is_file():
        return None
    with np.load(folder / name, allow_pickle=False) as data:
        return json.loads(str(data["meta_json"])).get("events")


def has_fallback(row: dict, folder: Path | None) -> bool | None:
    """Whether the run had a rod fallback (None: cannot tell, event list at the cap)."""
    events = t4h_events(row, folder)
    if events is not None:
        return any(str(event[1]).startswith(FALLBACK_EVENT) for event in events)
    r79 = row.get("r79")
    if isinstance(r79, dict) and "rod_fallback" in r79:
        return bool(r79["rod_fallback"]) or bool(row.get("rod_fallback_reasons"))
    events = row.get("events") or []
    if len(events) >= ROW_EVENT_CAP:
        return None
    return any(str(event[1]).startswith(FALLBACK_EVENT) for event in events)


def by_identity(rows: list[dict], label: str, problems: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for row in rows:
        key = identity(row)
        if key in found:
            problems.append(f"{label}: repeated job {key[:80]}")
        found[key] = row
    return found


def compare(old_rows: list[dict], new_rows: list[dict], old_t4h: Path | None,
            new_t4h: Path | None) -> dict:
    """The P5-1 report (module docstring rule)."""
    problems: list[str] = []
    old, new = by_identity(old_rows, "old", problems), by_identity(new_rows, "new", problems)
    one_sided = sorted(set(old) ^ set(new))
    problems += [f"one side only: {key[:80]}" for key in one_sided]
    judged, recorded, differing = [], [], []
    for key in sorted(set(old) & set(new)):
        before, after = old[key], new[key]
        hashes = (before.get("commands_sha256"), after.get("commands_sha256"))
        if not all(isinstance(value, str) and HASH.match(value) for value in hashes):
            problems.append(f"no 64-hex commands_sha256: {key[:80]}")
            continue
        setting = setting_of(after)
        fallbacks = (has_fallback(before, old_t4h), has_fallback(after, new_t4h))
        is_always = setting in ALWAYS_EQUAL_SETTINGS
        if not is_always and None in fallbacks:
            problems.append(f"event list at the cap without a T4h record: {key[:80]}")
            continue
        pair = {"job": key, "setting": setting, "fallback": list(fallbacks),
                "equal": hashes[0] == hashes[1]}
        if is_always or not any(fallbacks):
            judged.append(pair)
            if not pair["equal"]:
                differing.append(pair)
        else:
            recorded.append(pair)
    if not judged:
        problems.append("no judged pair")
    # erratum 2 2-10: a differing judged pair is a failure whatever the problems (all kept)
    status = "differ" if differing else ("not_judgeable" if problems else "pass")
    return {"rule": "jp3_remedy_spec_v5.md P5-1", "status": status,
            "pairs": len(set(old) & set(new)), "judged_pairs": len(judged),
            "differing_pairs": len(differing), "fallback_pairs_recorded": len(recorded),
            "problems": problems, "differing": differing, "recorded": recorded}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--old-t4h", type=Path, default=None)
    parser.add_argument("--new-t4h", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_judgeable", "reason": "--out exists"}))
        return EXIT_NOT_JUDGEABLE
    try:
        report = compare(read_rows(args.old), read_rows(args.new), args.old_t4h, args.new_t4h)
        report["inputs"] = {name: {"path": str(path),
                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                            for name, path in (("old", args.old), ("new", args.new))}
    except Exception as exc:  # a tool error, never a verdict
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps({"status": report["status"], "judged_pairs": report["judged_pairs"],
                      "differing_pairs": report["differing_pairs"],
                      "problems": len(report["problems"]), "out": str(args.out)}))
    return {"pass": EXIT_PASS, "differ": EXIT_DIFFER}.get(report["status"], EXIT_NOT_JUDGEABLE)


if __name__ == "__main__":
    sys.exit(main())
