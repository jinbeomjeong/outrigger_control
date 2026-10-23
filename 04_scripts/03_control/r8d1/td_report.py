import json, sys
f = sys.argv[1]
d = json.load(open(f))
for k, v in d["summary"].items():
    print(k, {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()})
print("wall", d["wall_s"])
