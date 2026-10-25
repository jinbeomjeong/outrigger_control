"""Summarise c36_work_def.py output: over-limit sets per definition, split by affected set."""
import json
import sys

rows = json.loads(open(sys.argv[1], encoding="utf-8").read())
aff = set(json.loads(open(sys.argv[2], encoding="utf-8").read())["affected"])
pp = {"ML78_ep0", "ML78_ep1", "ML78_ep3", "ML00_ep5", "ML21_ep1", "ML90_ep1"}
rows = [r for r in rows if "error" not in r and r.get("orig_max_after") is not None]
print("n", len(rows))
keys = ["orig_max_after", "osc1_max_after", "osc1.5_max_after", "osc2_max_after",
        "osc1.5_net_after", "osc1.5_net2s_max", "starts_after_1.5", "osc_D_pp_kN_after"]
print(f"{'case':<10} {'grp':<4} {'kind':<7} leg depth ramp | orig osc1 osc1.5 osc2 net1.5 net2s late Dpp | starts")
sel = [r for r in rows if r["orig_max_after"] > 20 or r["case"] in aff or r["case"] == "ML24_ep7"]
sel.sort(key=lambda r: -r["orig_max_after"])
for r in sel:
    g = ("PP" if r["case"] in pp else "AFF") if r["case"] in aff else "-"
    v = " ".join(f"{r[k]:6.1f}" if isinstance(r[k], float) else f"{r[k]!s:>6}" for k in keys)
    st = " ".join(f"{s[1]}{s[0]:.1f}" for s in r["reapp_starts"][:10])
    print(f"{r['case']:<10} {g:<4} {r['kind']:<7} {r['leg']!s:<3} {r['depth_mm'] or 0:5.1f} "
          f"{r['ramp_s'] or 0:5.2f} | {v} | {st}")
# distribution of the oscillatory metric among non-affected runs
for k in ("orig_max_after", "osc1.5_max_after", "osc1.5_net2s_max", "osc1_max_after", "osc2_max_after"):
    na = sorted((r[k], r["case"]) for r in rows if r["case"] not in aff)
    a = sorted((r[k], r["case"]) for r in rows if r["case"] in aff)
    print(k, "non-aff top5", [(round(x, 1), c) for x, c in na[-5:]],
          "| aff top8", [(round(x, 1), c) for x, c in a[-8:]])
    for lim in (10, 15, 20, 30):
        print(f"   >{lim}: non-aff {sum(x > lim for x, _ in na)}, aff {sum(x > lim for x, _ in a)}")
