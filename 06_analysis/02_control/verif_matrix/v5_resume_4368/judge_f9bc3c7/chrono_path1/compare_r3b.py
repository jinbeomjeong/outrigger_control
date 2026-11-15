"""R3b vs R3c comparison of the path 1 ``chrono_rows_judge`` outputs (rules rev21 R21-4, original 9.2
K-10; python-expert 2026-11-15).

K-10 form over every row key, with the D-29 keys (``D8_t_lift_s_D-29_D-30``, ``D8_t_lift_basis``,
``D8_t_lift_sus_R21_1``, ``C1_R40``, ``D8_no_pad_lift_Q-14``) left out **only** on the rows whose R3c
``D8_t_lift_basis`` is ``1ms_sus`` (1 ms L2b rows, the D-29 change of R21-1). L1-R rows and V0 bracket
rows keep these keys in the comparison; ``D8_t_lift_sus_R21_1`` is new in R3c and is reported as
"R3c only" on such rows instead of a difference. Texts that differ by construction (tool / rules
strings, the seal block, the disclosure block) are left out everywhere.

Usage: python -I -B compare_r3b.py <R3b folder> <R3c folder> <out.json>
Exit codes: 0 all equal, 1 a difference.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

BUNDLES = ("C1", "C2", "C3", "C4", "C5", "C6C7", "OC5PROBE", "OC5")
IGNORED_KEYS = {"tool", "rules", "seals", "disclosure"}
D29_KEYS = ("D8_t_lift_s_D-29_D-30", "D8_t_lift_basis", "D8_t_lift_sus_R21_1", "C1_R40",
            "D8_no_pad_lift_Q-14")
NEW_IN_R3C = "D8_t_lift_sus_R21_1"
SUS_BASIS = "1ms_sus"
REL_TOL = 1e-9
MAX_LISTED = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare(a, b, path: str, out: list[str]) -> None:
    """K-10: append the paths where ``a`` and ``b`` differ."""
    if len(out) >= MAX_LISTED:
        return
    if is_number(a) and is_number(b):
        if math.isfinite(a) and math.isfinite(b):
            if abs(a - b) > REL_TOL * max(1.0, abs(a), abs(b)):
                out.append(f"{path}: {a} != {b}")
        elif a != b:
            out.append(f"{path}: {a} != {b}")
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key in IGNORED_KEYS:
                continue
            if key not in a or key not in b:
                out.append(f"{path}.{key}: present only in {'R3b' if key in a else 'R3c'}")
                continue
            compare(a[key], b[key], f"{path}.{key}", out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list length {len(a)} != {len(b)}")
            return
        for index, (x, y) in enumerate(zip(a, b, strict=True)):
            compare(x, y, f"{path}[{index}]", out)
        return
    if a != b:
        out.append(f"{path}: {str(a)[:80]!r} != {str(b)[:80]!r}")


def strip_row(row: dict, keys: tuple[str, ...]) -> dict:
    items = {k: v for k, v in (row.get("items") or {}).items() if k not in keys}
    return {**row, "items": items}


def compare_rows(rows_b: list, rows_c: list, bundle: str) -> tuple[list[str], dict]:
    diffs: list[str] = []
    excluded, kept, new_only = [], [], []
    if len(rows_b) != len(rows_c):
        return [f"{bundle}.rows: length {len(rows_b)} != {len(rows_c)}"], {}
    for rb, rc in zip(rows_b, rows_c, strict=True):
        case = rc.get("case")
        if rb.get("case") != case:
            diffs.append(f"{bundle}.rows: case order {rb.get('case')} != {case}")
            continue
        basis = (rc.get("items") or {}).get("D8_t_lift_basis")
        if basis == SUS_BASIS:
            excluded.append(case)
            compare(strip_row(rb, D29_KEYS), strip_row(rc, D29_KEYS), f"{bundle}.{case}", diffs)
            continue
        if NEW_IN_R3C in (rc.get("items") or {}):
            new_only.append(case)
        kept.append(case)
        compare(strip_row(rb, (NEW_IN_R3C,)), strip_row(rc, (NEW_IN_R3C,)), f"{bundle}.{case}",
                diffs)
    return diffs, {"d29_keys_excluded_rows": excluded, "d29_keys_compared_rows": kept,
                   "r3c_only_key_rows": new_only}


def main() -> int:
    r3b, r3c, out_path = map(Path, sys.argv[1:4])
    report: dict = {"rule": "rev21 R21-4, original 9.2 K-10 (rel 1e-9); D-29 keys left out on "
                            "1ms_sus rows only", "bundles": {}}
    equal = True
    for bundle in BUNDLES:
        name = f"judge_{bundle}.json"
        a = json.loads((r3b / name).read_text(encoding="utf-8"))
        b = json.loads((r3c / name).read_text(encoding="utf-8"))
        diffs, scope = compare_rows(a.get("rows") or [], b.get("rows") or [], bundle)
        rest_a = {k: v for k, v in a.items() if k != "rows"}
        rest_b = {k: v for k, v in b.items() if k != "rows"}
        compare(rest_a, rest_b, f"{bundle}(top)", diffs)
        report["bundles"][bundle] = {"r3b_sha256": sha256(r3b / name),
                                     "r3c_sha256": sha256(r3c / name), "k10_equal": not diffs,
                                     **scope, "differences": diffs}
        equal &= not diffs
    report["all_equal"] = equal
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({"all_equal": equal,
                      "bundles": {k: v["k10_equal"] for k, v in report["bundles"].items()}}))
    return 0 if equal else 1


if __name__ == "__main__":
    sys.exit(main())
