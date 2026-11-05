"""Look at the stored acceptance rows: which fields exist, whether retrigger deferrals are recorded, split c4g2 rows against the both rows (hash and values). Read-only."""
import json
from pathlib import Path

ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")


def partial(p):
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[r.get("key")] = r
    return out


l12 = partial(ACC / "noise/r79_L1L2.json.partial.jsonl")
k0 = next(iter(l12))
r0 = l12[k0]
print("noise key", k0)
print("noise fields", {k: type(v).__name__ for k, v in r0.items()})
print(json.dumps(r0, default=str)[:1500])
c = partial(ACC / "split/r79_c4g2.json.partial.jsonl")
print("split keys", list(c))
for k, r in c.items():
    b = l12.get(k)
    print(k, "in both", b is not None)
    if b:
        print("  shared diff", [f for f in r if f in b and r[f] != b[f] and f not in ("wall_s", "pid")][:15])
g = json.loads((ACC / "grid/grid_r69_top.json").read_text(encoding="utf-8"))
print("grid top keys", list(g) if isinstance(g, dict) else len(g))
res = g.get("results") or g.get("rows") or g
print(type(res).__name__, len(res))
x = res[0] if isinstance(res, list) else next(iter(res.values()))
print("grid job fields", {k: type(v).__name__ for k, v in x.items()})
run = (x.get("runs") or x.get("events") or [None])[0]
if run:
    print("grid run fields", {k: type(v).__name__ for k, v in run.items()})
    print(json.dumps(run, default=str)[:1200])
print("key", x.get("key"), json.dumps(g.get("meta"), default=str)[:600])
