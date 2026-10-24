"""Summarize verify_S6C.json: counts, failures, item list."""
import json, sys, collections
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
rows = d["rows"]
print("meta keys", list(d["meta"].keys()))
print("metrics n", len(d["metrics"]), json.dumps(d["metrics"][0], ensure_ascii=False)[:1500])
print(collections.Counter((r["kind"], r["passed"]) for r in rows))
print("== failures")
for r in rows:
    if r["passed"] is False:
        print(json.dumps(r, ensure_ascii=False)[:700])
print("== None judged/function")
for r in rows:
    if r["passed"] is None and r["kind"] in ("function", "judged"):
        print(json.dumps(r, ensure_ascii=False)[:500])
print("== items")
items = collections.Counter(r["item"] for r in rows)
for k, v in items.items():
    print(v, k)
