"""R3d vs R3f comparison of the path 1 Chrono outputs (rules rev24 R24-3 re-judgement 2 as kept by
rev25 R25-3, original 9.2 K-10; python-expert 2026-11-16, draft for run_path1_r3f.ps1; the R3e
draft with the rev25 categories added; "R3e" below means the run being compared, now R3f).

* Left out (as before): ``tool``, ``rules``, ``seals``, ``disclosure`` (judge), the pairing record
  ``t45_pairing_R22_1``, the name record ``runner_name_map_R23_1`` and ``inputs.rows_judge.path``
  / ``.sha256`` (bundle).
* Left out (rules rev24 CD-10 run identity, CD-7 reason text): the keys of :data:`REASON_KEYS` at
  any depth and the ``reasons_CD_7`` block. Run identity of path 1 = ``inputs.rows_judge.path``
  (output folder) and ``disclosure`` (checkout); neither output records a run time.
* A remaining difference is allowed when its key path is under a pattern of :data:`ALLOWED` (the
  pre-registered key list ``allowed_keys_path1.md``); any other difference fails.
* Always fails, allowed or not: a different C-1 / C-2 / C-3 bundle grade (``bundle_grade.grade``,
  ``status``, ``grade_without_stop``) or row grade (``rows[].grade``).
* An R3d output missing in R3e is S-15; ``bundle_C4.json`` is new in R3e (listed, not compared).
K-10: grades, booleans, lists, counts and classes equal; numbers within 1e-9 * max(1, |a|, |b|).

Usage: python -I -B compare_r3d.py <R3d folder> <R3e folder> <out.json>
Exit codes: 0 no failing difference, 1 a failing difference or a missing output.
"""

import fnmatch
import hashlib
import json
import math
import sys
from pathlib import Path

JUDGE_BUNDLES = ("C1", "C2", "C3", "C4", "C5", "C6C7", "OC5PROBE", "OC5")
GRADE_BUNDLES = ("C1", "C2", "C3", "C5", "C6C7", "OC5")
"""Bundle outputs R3d wrote (all compared)."""
NEW_BUNDLES = ("C4",)
"""Bundle outputs new in R3e (rules rev24 CD-9): listed, not compared (R24-3 re-judgement 3)."""
GRADE_GUARDED = ("C1", "C2", "C3")
JUDGE_IGNORED = {("tool",), ("rules",), ("seals",), ("disclosure",)}
BUNDLE_IGNORED = {("tool",), ("rules",), ("seals",), ("t45_pairing_R22_1",),
                  ("runner_name_map_R23_1",), ("reasons_CD_7",),
                  ("inputs", "rows_judge", "path"), ("inputs", "rows_judge", "sha256")}
REASON_KEYS = ("reason", "override_reason", "grade_reason", "record_reason",
               "reason_not_judgeable", "gate_reasons_CD_5", "condition_note")
"""Rules rev24 CD-7 reason text keys (CD-10: left out of K-10 at any depth)."""
ALLOWED = {
    # CD-3 event rows (C-5 whole bundle) and the event test record of every L2b row
    "judge_C5.json": ["rows.#.items.moving_pressure_D-32*", "rows.#.items.ready_D-27_D-28.*"],
    "judge_C1.json": ["rows.#.items.moving_pressure_D-32.event_test_CD_3*"],
    "judge_C2.json": ["rows.#.items.moving_pressure_D-32.event_test_CD_3*",
                      "rows.#.items.ready_D-27_D-28.P3-6",
                      "rows.#.items.ready_D-27_D-28.ready_reached"],
    # C-5 whole bundle (rules rev24 R24-3 re-judgement 2)
    "bundle_C5.json": ["*"],
    # CD-2 re-computed item values, CD-5 READY missing items, CD-11 item list (C-1 .. C-3)
    "bundle_C1.json": ["item_list_CD_11*", "rows.#.overrides.#*", "rows.#.runner_items.#*"],
    # rev25 R25-3: CD-4 P3-6 role / limit and CD-11 P3-9 record move items between items and
    # record_items (C-2 PS-c base row, 427.9 rows); CD-5 P3-6 lines of the recorded rows
    "bundle_C2.json": ["item_list_CD_11*", "rows.#.overrides.#*", "rows.#.runner_items.#*",
                       "rows.#.items", "rows.#.items.#*", "rows.#.record_items",
                       "rows.#.record_items.#*"],
    "bundle_C3.json": ["item_list_CD_11*"],
    # CD-8 C-8 record values, record status and the new rows-judge input
    "bundle_OC5.json": ["rows.#.record_values_CD_8*", "rows.#.complete", "rows.#.missing_inputs*",
                        "rows.#.inputs_sha256*", "record_status", "inputs.rows_judge",
                        "inputs.rows_judge_tool"],
}
"""Pre-registered allowed difference keys (``allowed_keys_path1.md``); ``#`` = any list index,
fnmatch patterns on the dotted path."""
REL_TOL = 1e-9
MAX_LISTED = 200


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def dotted(path: tuple) -> str:
    return ".".join("#" if isinstance(p, int) else str(p) for p in path) or "(top)"


def compare(a, b, path: tuple, ignored: set, out: list[tuple[str, str]]) -> None:
    """K-10: append (pattern path, text) where ``a`` and ``b`` differ (ignored keys out)."""
    if len(out) >= MAX_LISTED or path in ignored or (path and path[-1] in REASON_KEYS):
        return
    name = dotted(path)
    if is_number(a) and is_number(b):
        if math.isfinite(a) and math.isfinite(b):
            if abs(a - b) > REL_TOL * max(1.0, abs(a), abs(b)):
                out.append((name, f"{a} != {b}"))
        elif a != b:
            out.append((name, f"{a} != {b}"))
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            sub = (*path, key)
            if sub in ignored or key in REASON_KEYS:
                continue
            if key not in a or key not in b:
                out.append((dotted(sub), f"present only in {'R3d' if key in a else 'R3e'}"))
                continue
            compare(a[key], b[key], sub, ignored, out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((name, f"list length {len(a)} != {len(b)}"))
            return
        for index, (x, y) in enumerate(zip(a, b, strict=True)):
            compare(x, y, (*path, index), ignored, out)
        return
    if a != b:
        out.append((name, f"{str(a)[:60]!r} != {str(b)[:60]!r}"))


def is_allowed(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def grade_differences(old: dict, new: dict) -> list[str]:
    """C-1 .. C-3 bundle and row grades that differ (a stop whatever the allowed list says)."""
    found = []
    for key in ("grade", "status", "grade_without_stop"):
        if (old.get("bundle_grade") or {}).get(key) != (new.get("bundle_grade") or {}).get(key):
            found.append(f"bundle_grade.{key}")
    old_rows = {r.get("case"): r.get("grade") for r in old.get("rows") or []}
    new_rows = {r.get("case"): r.get("grade") for r in new.get("rows") or []}
    found += [f"rows[{case}].grade" for case in sorted(set(old_rows) | set(new_rows))
              if old_rows.get(case) != new_rows.get(case)]
    return found


def compare_files(old: Path, new: Path, ignored: set, *, guarded: bool) -> dict:
    if not old.is_file() or not new.is_file():
        return {"present": {"R3d": old.is_file(), "R3e": new.is_file()}, "ok": False,
                "stop": "S-15: output missing on one side (rev24 R24-3 re-judgement 3)"}
    a = json.loads(old.read_text(encoding="utf-8"))
    b = json.loads(new.read_text(encoding="utf-8"))
    diffs: list[tuple[str, str]] = []
    compare(a, b, (), ignored, diffs)
    patterns = ALLOWED.get(new.name, [])
    allowed = [{"key": k, "diff": t} for k, t in diffs if is_allowed(k, patterns)]
    failing = [{"key": k, "diff": t} for k, t in diffs if not is_allowed(k, patterns)]
    grades = grade_differences(a, b) if guarded else []
    return {"r3d_sha256": sha256(old), "r3e_sha256": sha256(new),
            "allowed_differences": allowed, "failing_differences": failing,
            "grade_differences": grades, "truncated": len(diffs) >= MAX_LISTED,
            "ok": not failing and not grades and len(diffs) < MAX_LISTED}


def main() -> int:
    r3d, r3e, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    report = {"rules": "rev24 R24-3 re-judgement 2 / 3, original 9.2 K-10, CD-10, CD-7",
              "judge_ignored": sorted(".".join(p) for p in JUDGE_IGNORED),
              "bundle_ignored": sorted(".".join(p) for p in BUNDLE_IGNORED),
              "reason_keys": list(REASON_KEYS), "allowed": ALLOWED,
              "judge": {b: compare_files(r3d / f"judge_{b}.json", r3e / f"judge_{b}.json",
                                         JUDGE_IGNORED, guarded=False) for b in JUDGE_BUNDLES},
              "bundle": {b: compare_files(r3d / f"bundle_{b}.json", r3e / f"bundle_{b}.json",
                                          BUNDLE_IGNORED, guarded=b in GRADE_GUARDED)
                         for b in GRADE_BUNDLES},
              "new_in_r3e": {b: (r3e / f"bundle_{b}.json").is_file() for b in NEW_BUNDLES}}
    ok = all(v["ok"] for part in ("judge", "bundle") for v in report[part].values())
    report["all_ok"] = ok
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({"all_ok": ok,
                      "judge": {k: v["ok"] for k, v in report["judge"].items()},
                      "bundle": {k: v["ok"] for k, v in report["bundle"].items()},
                      "new_in_r3e": report["new_in_r3e"]}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
