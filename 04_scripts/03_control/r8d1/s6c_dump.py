"""Dump verify_S6C.json rows: failing rows, judged rows, kinds, per-item summary."""
import json
import sys
from collections import Counter, defaultdict

path = sys.argv[1]
d = json.load(open(path, encoding="utf-8"))
rows = d["rows"]
print("meta", d["meta"])
print("kinds", Counter(r.get("kind") for r in rows))
print("passed by kind", Counter((r.get("kind"), r.get("passed")) for r in rows))
items = defaultdict(list)
for r in rows:
    items[r["item"]].append(r)
print("\n== items ==")
for k, v in items.items():
    c = Counter(r.get("passed") for r in v)
    print(f"{k!r:60s} n={len(v):3d} {dict(c)} kind={Counter(r.get('kind') for r in v).most_common(1)[0][0]}")


def fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, list):
        return "[" + ",".join(fmt(x) for x in v) + "]"
    return str(v)


print("\n== FALSE rows ==")
for r in rows:
    if r.get("passed") is False:
        print(f"{r['case']:42s} | {r['item']:40s} | {fmt(r['value'])} | lim {fmt(r['limit'])} | {r.get('kind')} | {r.get('note','')}")
print("\n== None rows (non-report) ==")
for r in rows:
    if r.get("passed") is None and r.get("kind") not in ("report", "info"):
        print(f"{r['case']:42s} | {r['item']:40s} | {fmt(r['value'])} | lim {fmt(r['limit'])} | {r.get('kind')} | {r.get('note','')}")
