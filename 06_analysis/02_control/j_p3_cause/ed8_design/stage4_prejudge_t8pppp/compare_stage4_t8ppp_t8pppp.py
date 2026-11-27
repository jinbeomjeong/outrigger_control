"""Stage 4 after-compare (control_p80p85.md 5 "메인 순서" 5; decision D-2): the seven gates
other than p80 judged at T8'''' (judge_7ea78232) against T8''' (judge_2263b246).

Reads only the judge output JSON files of the two folders (never a run line). Prints, per gate,
the two statuses, booleans (status, status_basis, count fields, whole report without
``judge_code``) and the NAMES of the report fields that differ; never a field value, a list
entry or a hash. The judge identity of the new folder (head 7ea78232, clean) is checked for all
eight files, p80 included (identity only).

Usage (python-dev): python.exe -I -B compare_stage4_t8ppp_t8pppp.py OLD_FOLDER NEW_FOLDER
  OLD_FOLDER = j9_runs/56849248/judge_2263b246, NEW_FOLDER = j9_runs/56849248/judge_7ea78232
Exit: 0 every gate the same / 1 a difference or an identity problem / 2 an input error.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GATES = ("p816", "p85", "p88", "p815", "t8", "cases", "l1ref")
OLD_HEAD = "2263b2461238da7f93eda147838c01c847315561"
NEW_HEAD = "7ea782323c427917709ecbb365a58044449beac2"
NOT_COMPARED = ("judge_code",)
MISSING = object()


def load(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path.name}: not a JSON object")
    return document


def count_fields(report: dict) -> dict:
    """Top-level numbers and booleans, and the length of every top-level list."""
    counts = {}
    for key, value in report.items():
        if key in NOT_COMPARED:
            continue
        if isinstance(value, (bool, int, float)) or value is None:
            counts[key] = value
        elif isinstance(value, list):
            counts[f"len({key})"] = len(value)
    for key, value in (report.get("status_basis") or {}).items():
        counts[f"len(status_basis.{key})"] = len(value) if isinstance(value, list) else value
    return counts


def identity_ok(report: dict, head: str) -> bool:
    code = report.get("judge_code") or {}
    return code.get("head") == head and code.get("is_clean") is True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"status": "input_error", "reason": "two folders expected"}))
        return 2
    old_dir, new_dir = Path(argv[0]), Path(argv[1])
    try:
        old = {gate: load(old_dir / f"{gate}.json") for gate in GATES}
        new = {gate: load(new_dir / f"{gate}.json") for gate in GATES}
        new_p80 = load(new_dir / "p80.json")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return 2
    rows, all_same = [], True
    identity = {"p80": identity_ok(new_p80, NEW_HEAD)}
    for gate in GATES:
        a, b = old[gate], new[gate]
        fields = sorted((set(a) | set(b)) - set(NOT_COMPARED))
        differing = [key for key in fields if a.get(key, MISSING) != b.get(key, MISSING)]
        ca, cb = count_fields(a), count_fields(b)
        row = {"gate": gate, "status_old": a.get("status"), "status_new": b.get("status"),
               "status_same": a.get("status") == b.get("status"),
               "status_basis_same": a.get("status_basis") == b.get("status_basis"),
               "count_fields_same": ca == cb,
               "count_fields_differing": sorted(k for k in set(ca) | set(cb)
                                                if ca.get(k, MISSING) != cb.get(k, MISSING)),
               "whole_same": not differing, "fields_differing": differing,
               "old_identity_ok": identity_ok(a, OLD_HEAD)}
        identity[gate] = identity_ok(b, NEW_HEAD)
        all_same &= row["status_same"] and row["status_basis_same"] and row["count_fields_same"] \
            and row["whole_same"] and row["old_identity_ok"]
        rows.append(row)
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    all_same &= all(identity.values())
    summary = {"status": "same" if all_same else "differs", "new_identity_ok": identity}
    print(json.dumps(summary))
    return 0 if all_same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
