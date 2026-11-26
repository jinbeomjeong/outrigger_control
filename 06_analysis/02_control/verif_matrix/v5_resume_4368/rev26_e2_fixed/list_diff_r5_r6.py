"""rev26 erratum 2 disclosure check: compare the r5 and r6 application lists of the ORIGINAL output.

Reads only the two list files (token paths and categories, no output values). Expected: the r6 list equals the
sealed r5 list except the ``rules`` name and exactly one added row
``harness_path2/p2v5c_merge.json : [["parts", "[]", "sha256"], "I"]`` (no removed row, no category change, the
``c`` group and the scope keys unchanged). On a mismatch the differing rows (token paths and categories) are printed,
at most 20 per side.

Usage (python-dev): python -I -B -X utf8 list_diff_r5_r6.py <r5 list.json> <r6 list.json> [--out <result.json>]
Exit 0 as expected, 1 mismatch, 2 input error. Last stdout line is one JSON object; ``--out`` also writes it (UTF-8,
LF, indented) for the record.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

EXPECT_FILE = "harness_path2/p2v5c_merge.json"
EXPECT_ROW = (("parts", "[]", "sha256"), "I")
SCOPE_KEYS = ("scope_d_skipped_files", "scope_d_skipped_subtrees", "scope_c_files")
LIMIT = 20


def rows(doc, group):
    return {f: {(tuple(p), c) for p, c in v} for f, v in doc[group].items()}


def flat(per_file):
    return sorted([f, list(p), c] for f, s in per_file.items() for p, c in s)


def main() -> int:
    argv = sys.argv[1:]
    out_file = None
    if len(argv) == 4 and argv[2] == "--out":
        out_file, argv = Path(argv[3]), argv[:2]
    if len(argv) != 2:
        print(json.dumps({"status": "input_error", "detail": "usage: <r5 list> <r6 list> [--out <file>]"}))
        return 2
    try:
        paths = [Path(a) for a in argv]
        raw = [p.read_bytes() for p in paths]
        old, new = (json.loads(b.decode("utf-8")) for b in raw)
        ro = {g: rows(old, g) for g in ("d", "c")}
        rn = {g: rows(new, g) for g in ("d", "c")}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "input_error", "detail": type(exc).__name__}))
        return 2
    added, removed = {}, {}
    for f in sorted(set(ro["d"]) | set(rn["d"])):
        a = rn["d"].get(f, set()) - ro["d"].get(f, set())
        r = ro["d"].get(f, set()) - rn["d"].get(f, set())
        if a:
            added[f] = a
        if r:
            removed[f] = r
    checks = {
        "rules_names": old.get("rules") == "excl_fields_r5" and new.get("rules") == "excl_fields_r6",
        "scope_keys_equal": all(old.get(k) == new.get(k) for k in SCOPE_KEYS),
        "d_file_set_equal": set(ro["d"]) == set(rn["d"]),
        "c_equal": ro["c"] == rn["c"],
        "d_added_is_expected_row_only": added == {EXPECT_FILE: {EXPECT_ROW}},
        "d_removed_none": not removed,
    }
    ok = all(checks.values())
    out = {
        "status": "ok" if ok else "mismatch",
        "sha256": {"r5_list": hashlib.sha256(raw[0]).hexdigest(), "r6_list": hashlib.sha256(raw[1]).hexdigest()},
        "checks": checks,
        "d_files": [len(ro["d"]), len(rn["d"])],
        "d_entries": [sum(map(len, ro["d"].values())), sum(map(len, rn["d"].values()))],
        "d_by_cat_r5": dict(sorted(Counter(c for s in ro["d"].values() for _, c in s).items())),
        "d_by_cat_r6": dict(sorted(Counter(c for s in rn["d"].values() for _, c in s).items())),
        "c_entries": [sum(map(len, ro["c"].values())), sum(map(len, rn["c"].values()))],
        "added": flat(added)[:LIMIT],
        "removed": flat(removed)[:LIMIT],
    }
    if out_file is not None:
        out_file.write_bytes((json.dumps(out, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(out, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
