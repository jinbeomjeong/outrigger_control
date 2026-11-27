"""Compare two junit files: per-test status changes (no values, names only)."""
import sys
import xml.etree.ElementTree as ET


def statuses(path):
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = f"{case.get('classname')}::{case.get('name')}"
        kind = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                kind = child.tag
        out[key] = kind
    return out


a, b = statuses(sys.argv[1]), statuses(sys.argv[2])
only_a = sorted(set(a) - set(b))
only_b = sorted(set(b) - set(a))
changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
print(f"A {len(a)}  B {len(b)}  only_A {len(only_a)}  only_B {len(only_b)}  changed {len(changed)}")
for k in changed:
    print(f"  {a[k]} -> {b[k]}  {k}")
for k in only_b:
    print(f"  new in B: {b[k]}  {k}")
for k in only_a:
    print(f"  only in A: {a[k]}  {k}")
