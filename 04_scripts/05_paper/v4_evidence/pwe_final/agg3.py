"""Aggregate final-controller harness results, part 3 (read-only)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9")
R = ROOT / "rev85"
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
P = L(R / "finB2_p0.json")["records"]
R2p = {r["id"]: r for r in L(ROOT / "rev83" / "R2DS_p3b.json")["records"]}
p3b = [r for r in P if r["suite"] == "p3b"]
ch = Counter(); allc = Counter()
dready = defaultdict(list); datt = defaultdict(list); drut = defaultdict(list)
for r in p3b:
    s = r["id"].split("|")[1]; pad = r["id"].split("|")[2]
    allc[(s, pad)] += 1
    o = R2p[r["id"]]
    if o["hash"] != r["hash"]:
        ch[(s, pad)] += 1
        dready[s].append(r["t_ready_s"] - o["t_ready_s"])
        datt[s].append(max(abs(x) for x in r["att_end_deg"]) - max(abs(x) for x in o["att_end_deg"]))
        drut[s].append(r["rut_ready_mm"] - o["rut_ready_mm"])
print("p3b changed by soil/pad", dict(ch), "of", dict(allc))
for s in dready:
    print("  ", s, "dREADY %.1f..%.1f" % (min(dready[s]), max(dready[s])), "datt %.4f..%.4f" % (min(datt[s]), max(datt[s])), "drut %.1f..%.1f" % (min(drut[s]), max(drut[s])))
# p3b summary per soil/pad (soil only) for table 12b
agg = defaultdict(list)
for r in p3b:
    s, pad = r["id"].split("|")[1], r["id"].split("|")[2]
    agg[(s, pad)].append(r)
print("p3b per soil/pad: n, READY range, att max, minF min, rut_ready min, max stroke")
for k, rr in sorted(agg.items()):
    print("  ", k, len(rr), "%.1f-%.1f" % (min(r["t_ready_s"] for r in rr), max(r["t_ready_s"] for r in rr)),
          "%.4f" % max(max(abs(x) for x in r["att_end_deg"]) for r in rr), "%.2f" % min(r["min_force_kN"] for r in rr),
          "%.1f" % min(r["rut_ready_mm"] for r in rr), "%.1f" % max(r["max_stroke_mm"] for r in rr),
          Counter(r["verdict"] for r in rr))
# R2DS p3b soil att for comparison
for k in [("J1", "B"), ("J2", "B")]:
    rr = [o for o in R2p.values() if o["id"].split("|")[1] == k[0] and o["id"].split("|")[2] == k[1]]
    print("  R2DS", k, "att max %.4f READY %.1f-%.1f rut min %.1f" % (max(max(abs(x) for x in r["att_end_deg"]) for r in rr), min(r["t_ready_s"] for r in rr), max(r["t_ready_s"] for r in rr), min(r["rut_ready_mm"] for r in rr)))
# v3s changes
R2v = L(ROOT / "rev83" / "R2_v3s.json")
rv = {r["id"]: r for r in (R2v.get("records") or [])}
v3 = [r for r in P if r["suite"] == "v3s"]
print("v3s hash same", sum(1 for r in v3 if rv.get(r["id"], {}).get("hash") == r["hash"]), "/", len(v3), "ids eg", [r["id"] for r in v3][:3])
print("v3s changed ids", [r["id"] for r in v3 if rv.get(r["id"], {}).get("hash") != r["hash"]][:40])
# g6 rigid-based hash diffs
g6 = [r for r in P if r["suite"] == "g6"]
R2g = {r["id"]: r for r in L(ROOT / "rev83" / "R2DS_g6.json")["records"]}
cc = Counter()
for r in g6:
    base = r["id"].split("|")[1].split("+")[0] if "+" in r["id"].split("|")[1] else r["id"].split("|")[1]
    cc[(base, R2g[r["id"]]["hash"] == r["hash"])] += 1
print("g6 base/same", dict(cc))
# g6 flags detail
print("g6 FLAG preloc fail list:")
for r in g6:
    if r["verdict"] == "fail":
        print("   ", r["id"], r["failed_rows"])
# x426b
X = L(R / "finB2_x426b_rejudged.json")
print("x426b counts", X["counts"])
var = defaultdict(Counter)
for r in X["records"]:
    t = r["id"].split("|")
    tag = "m1.1" if "m1.1" in r["id"] else ("Fs0" if "Fs0" in r["id"] else ("Fs8" if "Fs8" in r["id"] else ("mid" if "middle" in r["id"] else "?")))
    var[tag][r["verdict"]] += 1
for k, c in var.items():
    print("  ", k, dict(c))
print("x426b crawler after ready max", max((r.get("crawler_N_max_after_ready") or 0) for r in X["records"]))
for r in X["records"]:
    if "m1.1" in r["id"]:
        print("   m1.1", r["id"], r["verdict"], r["failed_rows"], None if r["t_ready_s"] is None else round(r["t_ready_s"], 1))
# old x426b
for f in ("x426_B_Fs0_rejudged.json", "x426_B_Fs8_rejudged.json", "x426_B_mid_rejudged.json", "x426_B_m1p1_rejudged.json"):
    try:
        d = L(R / f)
        recs = d.get("records") or d.get("results") or []
        print("old", f, Counter(r.get("verdict") for r in recs))
    except Exception as e:
        print("old", f, "ERR", e)
