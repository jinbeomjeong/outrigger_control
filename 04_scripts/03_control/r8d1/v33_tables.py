"""Compact per-case tables of selected verify_S6C rows."""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
rows = d["rows"]
pats = sys.argv[2:]


def fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, list):
        return "[" + ", ".join(fmt(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {fmt(x)}" for k, x in v.items()) + "}"
    return str(v)


for p in pats:
    print("=====", p)
    for r in rows:
        if p in r["item"]:
            print(f"{r['case'][:42]:42s} | {r['item'][:50]:50s} | {fmt(r['value'])[:110]} | lim {fmt(r['limit'])[:30]} | {r['passed']} | {r['note'][:120]}")
