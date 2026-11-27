"""Compare test_ed8_* statuses between two junit files (names and statuses only).

Usage: python -I -B junit_ed8_compare.py A.xml B.xml
Prints counts per file, then any changed / missing test_ed8_* cases. Exit 0 same, 1 differs.
"""
import sys
import xml.etree.ElementTree as ET


def statuses(path):
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        cls = case.get("classname") or ""
        if ".test_ed8_" not in "." + cls:
            continue
        kind = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                kind = child.tag
        out[f"{cls.split('.')[-1]}::{case.get('name')}"] = kind
    return out


def tally(d):
    t = {}
    for v in d.values():
        t[v] = t.get(v, 0) + 1
    return t


a, b = statuses(sys.argv[1]), statuses(sys.argv[2])
changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
print(f"A test_ed8_* {len(a)} {tally(a)}")
print(f"B test_ed8_* {len(b)} {tally(b)}")
print(f"changed {len(changed)} only_A {len(only_a)} only_B {len(only_b)}")
for k in changed:
    print(f"  {a[k]} -> {b[k]}  {k}")
for k in only_a:
    print(f"  only in A: {k}")
for k in only_b:
    print(f"  only in B: {k}")
sys.exit(0 if not (changed or only_a or only_b) else 1)
