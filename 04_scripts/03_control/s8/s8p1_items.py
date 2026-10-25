"""Unique items of verify_S8C.json with counts; optional item-substring table across cases."""
import sys, json, collections
v = json.load(open(sys.argv[1], encoding="utf-8"))
rows = v["rows"]
if len(sys.argv) == 2:
    c = collections.Counter((r["item"], r["kind"]) for r in rows)
    f = collections.Counter((r["item"], r["kind"]) for r in rows if r["passed"] is False)
    for (it, k), n in sorted(c.items()):
        print(f"{n:3d} fail {f.get((it, k), 0):2d}  [{k}] {it}")
else:
    pat = sys.argv[2]
    for r in rows:
        if pat in r["item"]:
            val = r["value"]
            s = json.dumps(val, ensure_ascii=False)
            print(f"{r['case']:26s} {str(r['passed']):5s} {s[:160]} | {str(r.get('note'))[:140]}")
