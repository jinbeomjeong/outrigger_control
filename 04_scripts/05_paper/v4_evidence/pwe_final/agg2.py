"""Aggregate final-controller harness results, part 2 (read-only)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9")
R = ROOT / "rev85"
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))

H = L(R / "finB2_harness_rejudged.json")
fin = {r["id"]: r for r in H["records"]}
R2 = L(ROOT / "rev83" / "R2DS_slope_rejudged.json")
print("R2DS counts", R2["counts"])
r2 = {r["id"]: r for r in R2["records"]}
tr = Counter()
for i, r in fin.items():
    if r["suite"] != "slope":
        continue
    tr[(r2[i]["verdict"], r["verdict"])] += 1
print("transitions R2DS->final:")
for k, v in sorted(tr.items()):
    print("  ", k, v)
# changed non-guard
for i, r in fin.items():
    if r["suite"] == "slope" and r2[i]["verdict"] in ("pass",) and r["verdict"] != "pass":
        print("  pass->", r["verdict"], i, r["failed_rows"])
    if r["suite"] == "slope" and r2[i]["verdict"] == "fail" and r["verdict"] == "pass":
        print("  fail->pass", i)
# stop: crawler loaded at stop?
st = [r for r in fin.values() if r["verdict"] == "stroke_limited_stop"]
print("stops", len(st), "loaded", sum(1 for r in st if (r.get("soil_stop") or {}).get("stop_with_crawler_loaded")))
mp = [((r.get("soil_stop") or {}).get("moving_pressure") or {}).get("max_moving_bar") for r in st]
print("stop moving bar max", max(x for x in mp if x is not None))
mf = [(r.get("soil_stop") or {}).get("min_true_Fcyl_after_off_kN") for r in st]
print("stop min_true_Fcyl_after_off_kN min", min(x for x in mf if x is not None))
# fail soil_stop True: loaded?
for r in fin.values():
    if r["suite"] == "slope" and r["verdict"] == "fail" and r.get("soil_stop"):
        ss = r["soil_stop"]
        print("  failstop", r["id"], ss.get("stop_with_crawler_loaded"), round(ss.get("min_true_Fcyl_at_stop_kN") or -1, 1), ss.get("stop_event"), {k: v for k, v in ss.get("conditions", {}).items() if not v})

# pass-class per direction, attitude & minF
def parse(i):
    p = i.split("|"); d = p[4]; k = None
    if "@k" in d: d, k = d.split("@k")
    return p[0], p[1], p[2], p[3], d, k
def dgroup(d):
    if d == "flat": return "flat"
    if d.startswith("nose_down"): return "nose_down"
    if d == "nose_up": return "nose_up"
    if d.startswith("roll"): return "roll"
    return "edge"
dd = defaultdict(Counter)
for r in fin.values():
    if r["suite"] != "slope": continue
    g, s, p, l, d, k = parse(r["id"])
    dd[d][r["verdict"]] += 1
print("by exact direction:")
for d, c in sorted(dd.items()):
    print("  ", d, dict(c), sum(c.values()))

# p0
P = L(R / "finB2_p0.json")["records"]
for suite in ("g6", "g8", "p3b", "v3s"):
    rr = [r for r in P if r["suite"] == suite]
    fl = Counter(); [fl.update(r.get("flags") or []) for r in rr]
    frw = Counter(); [frw.update(r.get("failed_rows") or []) for r in rr]
    print(suite, len(rr), Counter(r["verdict"] for r in rr), "flags", dict(fl), "failed_rows", dict(frw))
g6 = [r for r in P if r["suite"] == "g6"]
soft = [r for r in g6 if "@" in r["id"]]
print("g6 soft n", len(soft), "READY %.1f-%.1f" % (min(r["t_ready_s"] for r in soft if r["t_ready_s"]), max(r["t_ready_s"] for r in soft if r["t_ready_s"])),
      "minF %.2f" % min(r["min_force_kN"] for r in soft if r["min_force_kN"] is not None),
      "att %.4f" % max(max(abs(x) for x in r["att_end_deg"]) for r in soft if r["att_end_deg"]))
print("g6 crawler after ready", max((r.get("crawler_N_max_after_ready") or 0) for r in g6))
R2g6 = L(ROOT / "rev83" / "R2DS_g6.json")
r2g6 = {r["id"]: r for r in R2g6["records"]}
diff = [(r["id"], r2g6[r["id"]]["hash"] == r["hash"]) for r in g6 if r["id"] in r2g6]
print("g6 hash same as R2DS:", sum(1 for _, s in diff if s), "/", len(diff))
for i, s in diff:
    if not s:
        print("   g6 hash diff", i, r2g6[i]["verdict"], "->", [r for r in g6 if r["id"] == i][0]["verdict"], round(r2g6[i]["t_ready_s"] or -1, 1), "->", round([r for r in g6 if r["id"] == i][0]["t_ready_s"] or -1, 1))
g8 = [r for r in P if r["suite"] == "g8"]
print("g8 maxstroke %.2f att %.4f minF %.2f" % (max(r["max_stroke_mm"] for r in g8), max(max(abs(x) for x in r["att_end_deg"]) for r in g8 if r["att_end_deg"]), min(r["min_force_kN"] for r in g8 if r["min_force_kN"] is not None)))
R2g8 = L(ROOT / "rev83" / "R2_g8.json")
recs8 = R2g8.get("records") or R2g8.get("results")
h8 = {r["id"]: r.get("hash") for r in recs8}
print("g8 hash same:", sum(1 for r in g8 if h8.get(r["id"]) == r["hash"]), "/", len(g8))
p3b = {r["id"]: r for r in P if r["suite"] == "p3b"}
for k in ("base|J1|B|top|Fs4", "base|J2|B|top|Fs4", "base|J2|B|middle|Fs4", "base|G1|B|top|Fs4", "base|G1|A|top|Fs4", "base|J1|A|top|Fs4", "base|J2|A|top|Fs4", "base|S1|A|top|Fs4", "base|S1|B|top|Fs4", "base|J1|B|top|Fs0", "base|J1|B|top|Fs8", "base|J2|B|bottom|Fs4"):
    r = p3b.get(k)
    if r:
        m = r["metrics"]
        print("  p3b", k, r["verdict"], round(r["t_ready_s"], 1), round(r["min_force_kN"], 2), [round(x, 4) for x in r["att_end_deg"]], round(r["rut_ready_mm"], 1), round(r["max_stroke_mm"], 1), "e3", m.get("e3_applied"))
print("p3b ids sample", list(p3b)[:5], len(p3b))
# p3b hash vs R2DS
R2p = L(ROOT / "rev83" / "R2DS_p3b.json")
rp = {r["id"]: r for r in (R2p.get("records") or [])}
same = sum(1 for i, r in p3b.items() if rp.get(i, {}).get("hash") == r["hash"])
print("p3b hash same as R2DS", same, "/", len(p3b))
chg = Counter()
for i, r in p3b.items():
    if rp.get(i, {}).get("hash") != r["hash"]:
        chg[(rp.get(i, {}).get("verdict"), r["verdict"])] += 1
print("p3b changed transitions", dict(chg))
v3 = [r for r in P if r["suite"] == "v3s"]
print("p3b soil counts:", Counter(i.split("|")[1] for i in p3b))
