"""Summarise rerun33 verify_S6C.json: failed rows, item-3 lift rows, C11 rows, min-force rows."""
import json
import sys
from pathlib import Path

v = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("top keys", list(v)[:20])
rows = v.get("rows") or v.get("table") or []
if not rows:
    for k, val in v.items():
        if isinstance(val, list) and val and isinstance(val[0], dict) and "item" in val[0]:
            rows = val
            print("rows key", k)
            break
print("n rows", len(rows), "row keys", list(rows[0]))
pat = sys.argv[2:] or []
for r in rows:
    item = str(r.get("item"))
    if r.get("passed") is False or any(p in item for p in pat):
        val = json.dumps(r.get("value"), default=str)
        print(f"{r.get('case')} | {item} | {val[:300]} | lim {json.dumps(r.get('limit'), default=str)[:120]} | "
              f"{r.get('passed')} | {r.get('c11_role', '')} | {str(r.get('note', ''))[:400]}")
