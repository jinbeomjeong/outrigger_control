"""List top-level and grid keys of target_envelope.json."""
import json
import sys

d = json.load(open(sys.argv[1]))
print(list(d.keys()))
for k, v in d.items():
    if isinstance(v, dict):
        print(k, list(v.keys())[:40])
g = d.get("grids") or d.get("grid") or {}
if isinstance(g, dict):
    for k, v in list(g.items())[:2]:
        print("GRID", k, type(v).__name__)
        if isinstance(v, dict):
            for kk, vv in v.items():
                print("   ", kk, type(vv).__name__, len(vv) if hasattr(vv, "__len__") else vv)
s = d["summary"]
print(list(s.keys()))
for k in s:
    if "rule" in k or "accept" in k:
        print(k, json.dumps(s[k])[:2000])
