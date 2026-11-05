"""Aggregate final-controller harness results (read-only)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
L = lambda n: json.loads((R / n).read_text(encoding="utf-8"))

H = L("finB2_harness_rejudged.json")
recs = H["records"]
slope = [r for r in recs if r["suite"] == "slope"]
h6 = [r for r in recs if r["suite"] == "h6"]
print("slope", len(slope), Counter(r["verdict"] for r in slope))
print("h6", len(h6), Counter(r["verdict"] for r in h6))

# metric keys
print("metrics keys:", sorted(slope[0]["metrics"].keys()))
st = [r for r in slope if r["verdict"] == "stroke_limited_stop"]
print("soil_stop example:", json.dumps(st[0]["soil_stop"], ensure_ascii=False)[:600])

def parse(i):
    p = i.split("|")
    grp, soil, pad, lvl, d = p[0], p[1], p[2], p[3], p[4]
    k = None
    if "@k" in d:
        d, k = d.split("@k"); k = float(k)
    return grp, soil, pad, lvl, d, k

def dgroup(d):
    if d == "flat": return "flat"
    if d.startswith("nose_down"): return "nose_down"
    if d == "nose_up": return "nose_up"
    if d.startswith("roll"): return "roll"
    return "edge"

by_soil = defaultdict(Counter); by_dir = defaultdict(Counter); by_pad = defaultdict(Counter)
for r in slope:
    g, s, p, l, d, k = parse(r["id"])
    by_soil[s][r["verdict"]] += 1
    by_dir[dgroup(d)][r["verdict"]] += 1
    by_pad[(s, p)][r["verdict"]] += 1
print("by soil:"); [print(" ", s, dict(c), sum(c.values())) for s, c in sorted(by_soil.items())]
print("by dir:"); [print(" ", s, dict(c), sum(c.values())) for s, c in sorted(by_dir.items())]
print("by soil/pad:"); [print(" ", s, dict(c), sum(c.values())) for s, c in sorted(by_pad.items())]
fr = Counter()
for r in slope:
    if r["verdict"] == "fail":
        fr.update(r["failed_rows"])
print("fail rows:", dict(fr))
print("fail ids:")
for r in slope:
    if r["verdict"] == "fail":
        print("  ", r["id"], r["failed_rows"], "phase", r["final_phase"], "soil_stop", bool(r.get("soil_stop")))

def att(r):
    a = r.get("att_end_deg") or [None, None]
    return max(abs(x) for x in a if x is not None) if a and a[0] is not None else None
ps = [r for r in slope if r["verdict"] == "pass"]
print("pass: att max %.4f, minF min %.2f, ready max %.1f" % (max(att(r) for r in ps), min(r["min_force_kN"] for r in ps), max(r["t_ready_s"] for r in ps if r["t_ready_s"])))
print("pass READY>120:", [(r["id"], round(r["t_ready_s"], 1)) for r in ps if r["t_ready_s"] and r["t_ready_s"] > 120])
print("stop: maxstroke %.1f-%.1f, minF min %s" % (min(r["max_stroke_mm"] for r in st), max(r["max_stroke_mm"] for r in st), min((r["min_force_kN"] for r in st if r["min_force_kN"] is not None), default=None)))
print("crawler after ready max (all slope):", max((r.get("crawler_N_max_after_ready") or 0) for r in slope))
print("soil-wise rigid/G1 any non pass:", [(r["id"], r["verdict"]) for r in slope if parse(r["id"])[1] in ("rigid", "G1") and r["verdict"] != "pass"])
# J1 boundary
print("J1 rows:")
for r in slope:
    g, s, p, l, d, k = parse(r["id"])
    if s == "J1" and l == "top" and (k is not None or g == "H1"):
        print("  ", r["id"], r["verdict"], round(r["t_ready_s"] or -1, 1), round(r["max_stroke_mm"], 1))
# stop counts by soil
print("h6 rows:")
for r in h6:
    print("  ", r["id"], r["verdict"], r["failed_rows"], None if r["t_ready_s"] is None else round(r["t_ready_s"], 1), round(r["max_stroke_mm"], 1), r.get("final_phase"), (r.get("warnings") or [])[:3])

# R2DS comparison for slope verdicts
R2 = json.loads(Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev83\R2DS_slope_rejudged.json").read_text(encoding="utf-8"))
k2 = list(R2.keys()); print("R2DS keys", k2[:6])
