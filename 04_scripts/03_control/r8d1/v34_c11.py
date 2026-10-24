"""rerun33: per-case judged-row summary (pass counts) and the key minimum-force rows."""
import json
import sys
from collections import defaultdict
from pathlib import Path

v = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = v["rows"]
by = defaultdict(lambda: [0, 0, 0])
for r in rows:
    p = r.get("passed")
    by[r["case"]][0 if p is True else 1 if p is False else 2] += 1
for c, n in sorted(by.items()):
    print(f"{c:45s} True {n[0]:3d} False {n[1]:2d} None {n[2]:3d}")
keys = ("min", "REANCHOR", "F_min", "6 ", "D8", "attitude", "pressure", "bar", "re-READY", "R-5", "C-5", "saturation")
print()
for r in rows:
    if not (str(r["case"]).startswith(tuple(sys.argv[2:])) if len(sys.argv) > 2 else True):
        continue
    item = r["item"]
    if any(k in item for k in keys):
        val = json.dumps(r.get("value"), default=str)
        print(f"{r['case'][:40]:40s} | {item[:70]:70s} | {val[:110]} | {json.dumps(r.get('limit'), default=str)[:40]} | {r.get('passed')}")
