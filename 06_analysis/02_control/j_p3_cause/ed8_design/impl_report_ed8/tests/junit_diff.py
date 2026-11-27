"""Compare two junit files: failures, skips and test ids."""
import sys
import xml.etree.ElementTree as ET


def states(path):
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        tid = f"{case.get('classname')}::{case.get('name')}"
        state = "pass"
        for child in case:
            if child.tag in ("failure", "error"):
                state = "fail"
            elif child.tag == "skipped":
                state = "skip:" + (child.get("message") or "")[:90]
        out[tid] = state
    return out


base, new = states(sys.argv[1]), states(sys.argv[2])
print("base", len(base), "new", len(new))
for tid in sorted(set(base) | set(new)):
    a, b = base.get(tid, "absent"), new.get(tid, "absent")
    if a == b:
        continue
    if a.startswith("skip") and b.startswith("skip"):
        continue
    if b == "absent" or (a == "absent" and b == "pass"):
        continue
    print(f"{a[:40]:<40} -> {b[:60]:<60} {tid}")
