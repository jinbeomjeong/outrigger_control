"""R3c vs R3d comparison of the path 1 Chrono outputs (rules rev22 R22-3, original 9.2 K-10;
python-expert 2026-11-15, draft for run_path1_r3d.ps1).

* ``judge_<B>.json`` (chrono_rows_judge, C-1 .. C-8): K-10 form without ``tool``, ``rules``,
  ``seals`` and the ``disclosure`` block (R22-3 keys of path 1).
* ``bundle_<B>.json`` (chrono_bundle_grade, C-1 .. C-3): K-10 form without ``tool``, ``rules``,
  ``seals``, the pairing record ``t45_pairing_R22_1``, the name record ``runner_name_map_R23_1``
  (rev23 R23-3) and ``inputs.rows_judge.path`` / ``inputs.rows_judge.sha256``;
  ``inputs.rows_judge_tool`` and ``inputs.runner_judge_dir`` stay.
K-10: grades, booleans, lists, counts and classes equal; numbers within 1e-9 * max(1, |a|, |b|).
A bundle output missing on either side is S-15 (R22-3 1).

Usage: python -I -B compare_r3c.py <R3c folder> <R3d folder> <out.json>
Exit codes: 0 all equal, 1 a difference or a missing output.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

JUDGE_BUNDLES = ("C1", "C2", "C3", "C4", "C5", "C6C7", "OC5PROBE", "OC5")
GRADE_BUNDLES = ("C1", "C2", "C3")
JUDGE_IGNORED = {("tool",), ("rules",), ("seals",), ("disclosure",)}
BUNDLE_IGNORED = {("tool",), ("rules",), ("seals",), ("t45_pairing_R22_1",),
                  ("runner_name_map_R23_1",),
                  ("inputs", "rows_judge", "path"), ("inputs", "rows_judge", "sha256")}
REL_TOL = 1e-9
MAX_LISTED = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare(a, b, path: tuple, ignored: set, out: list[str]) -> None:
    """K-10: append the dotted paths where ``a`` and ``b`` differ (``ignored`` key paths out)."""
    if len(out) >= MAX_LISTED or path in ignored:
        return
    name = ".".join(str(p) for p in path) or "(top)"
    if is_number(a) and is_number(b):
        if math.isfinite(a) and math.isfinite(b):
            if abs(a - b) > REL_TOL * max(1.0, abs(a), abs(b)):
                out.append(f"{name}: {a} != {b}")
        elif a != b:
            out.append(f"{name}: {a} != {b}")
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            sub = (*path, key)
            if sub in ignored:
                continue
            if key not in a or key not in b:
                out.append(f"{name}.{key}: present only in {'R3c' if key in a else 'R3d'}")
                continue
            compare(a[key], b[key], sub, ignored, out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{name}: list length {len(a)} != {len(b)}")
            return
        for index, (x, y) in enumerate(zip(a, b, strict=True)):
            compare(x, y, (*path, index), ignored, out)
        return
    if a != b:
        out.append(f"{name}: {str(a)[:80]!r} != {str(b)[:80]!r}")


def compare_files(old: Path, new: Path, ignored: set) -> dict:
    if not old.is_file() or not new.is_file():
        return {"present": {"R3c": old.is_file(), "R3d": new.is_file()}, "k10_equal": False,
                "stop": "S-15: output missing on one side (rev22 R22-3 1)"}
    diffs: list[str] = []
    compare(json.loads(old.read_text(encoding="utf-8")),
            json.loads(new.read_text(encoding="utf-8")), (), ignored, diffs)
    return {"r3c_sha256": sha256(old), "r3d_sha256": sha256(new), "k10_equal": not diffs,
            "differences": diffs}


def main() -> int:
    r3c, r3d, out_path = map(Path, sys.argv[1:4])
    report = {"rule": "rev22 R22-3, original 9.2 K-10 (rel 1e-9)",
              "judge_ignored": sorted(".".join(p) for p in JUDGE_IGNORED),
              "bundle_ignored": sorted(".".join(p) for p in BUNDLE_IGNORED),
              "judge": {b: compare_files(r3c / f"judge_{b}.json", r3d / f"judge_{b}.json",
                                         JUDGE_IGNORED) for b in JUDGE_BUNDLES},
              "bundle": {b: compare_files(r3c / f"bundle_{b}.json", r3d / f"bundle_{b}.json",
                                          BUNDLE_IGNORED) for b in GRADE_BUNDLES}}
    equal = all(v["k10_equal"] for part in ("judge", "bundle") for v in report[part].values())
    report["all_equal"] = equal
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({"all_equal": equal,
                      "judge": {k: v["k10_equal"] for k, v in report["judge"].items()},
                      "bundle": {k: v["k10_equal"] for k, v in report["bundle"].items()}}))
    return 0 if equal else 1


if __name__ == "__main__":
    sys.exit(main())
