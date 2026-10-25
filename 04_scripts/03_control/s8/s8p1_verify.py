"""List failing rows of verify_S8C.json and show the row schema."""
import sys, json
v = json.load(open(sys.argv[1], encoding="utf-8"))
print("top keys:", list(v.keys()))
rows = v["rows"]
print("n rows", len(rows), "row keys:", list(rows[0].keys()))
mode = sys.argv[2] if len(sys.argv) > 2 else "fail"
for r in rows:
    p = r.get("passed")
    if mode == "fail" and p is False:
        s = json.dumps({k: r[k] for k in r if k not in ("detail",)}, ensure_ascii=False)
        print(s[:600])
    elif mode not in ("fail",) and mode in json.dumps(r, ensure_ascii=False):
        print(json.dumps(r, ensure_ascii=False)[:1500])
for k in v:
    if k != "rows":
        print(k, json.dumps(v[k], ensure_ascii=False)[:3000])
