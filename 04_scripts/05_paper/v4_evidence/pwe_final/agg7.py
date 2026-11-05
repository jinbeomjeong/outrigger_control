"""Part 7: study A metrics, p3b per auger level, x426b x1.1 pairs, g6 READY change (read-only)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
W = Path(r"C:\workspace\outrigger_control")
R = W / "06_analysis/02_control/s9/rev85"
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
A = L(R / "finB2_A.json")["results"]
agg = defaultdict(lambda: {"minW": [], "lift": [], "pw": [], "pm": [], "crawl": [], "n": 0, "ok": 0})
for job in A:
    if job["readings"] != "two":
        continue
    for run in job["runs"]:
        a = agg[job["soil"]]
        a["n"] += 1; a["ok"] += bool(run["pass"])
        m = run.get("min_F_after_W_kN") or {}
        if isinstance(m, dict) and m: a["minW"].append(min(m.values()))
        lifts = run.get("lifts") or {}
        if isinstance(lifts, dict):
            vals = [v if isinstance(v, (int, float)) else (v.get("total_s") if isinstance(v, dict) else None) for v in lifts.values()]
            vals = [v for v in vals if v is not None]
            if vals: a["lift"].append(max(vals))
        p = run.get("pressure") or {}
        def mx(v):
            if isinstance(v, dict):
                v = [x for x in v.values() if isinstance(x, (int, float))]
                return max(v) if v else None
            return v
        if mx(p.get("window_max_bar")) is not None: a["pw"].append(mx(p["window_max_bar"]))
        if mx(p.get("moving_outside_max_bar")) is not None: a["pm"].append(mx(p["moving_outside_max_bar"]))
        c = run.get("crawler") or {}
        a["crawl"].append(c)
for s, a in agg.items():
    print("A", s, a["n"], a["ok"], "minW %.2f" % min(a["minW"]) if a["minW"] else None, "lift max", max(a["lift"]) if a["lift"] else None,
          "pw max", max(a["pw"]) if a["pw"] else None, "pm max", max(a["pm"]) if a["pm"] else None)
print("A lifts sample", json.dumps(A[0]["runs"][2].get("lifts"))[:300], "crawler sample", json.dumps(A[0]["runs"][2].get("crawler"))[:300])
P = [r for r in L(R / "finB2_p0.json")["records"] if r["suite"] == "p3b"]
print("p3b per level (Fs4):")
for soil in ("G1", "J1", "J2", "S1"):
    for pad in ("A", "B"):
        out = []
        for lvl in ("top", "middle", "bottom"):
            r = [x for x in P if x["id"] == f"base|{soil}|{pad}|{lvl}|Fs4"][0]
            out.append("%s:%.4f/%.1f/%.2f/%.1f" % (lvl[0], max(abs(v) for v in r["att_end_deg"]), r["t_ready_s"], r["min_force_kN"], r["rut_ready_mm"]))
        print("  ", soil, pad, " ".join(out))
    for pad in ("A", "B"):
        out = []
        for fs in ("Fs0", "Fs4", "Fs8"):
            r = [x for x in P if x["id"] == f"base|{soil}|{pad}|top|{fs}"][0]
            out.append("%s:%.4f/%.1f/%.2f" % (fs, max(abs(v) for v in r["att_end_deg"]), r["t_ready_s"], r["min_force_kN"]))
        print("   Fs", soil, pad, " ".join(out))
H = {r["id"]: r for r in L(R / "finB2_harness_rejudged.json")["records"]}
X = L(R / "finB2_x426b.json")["records"]
pair = Counter()
for r in X:
    if "m1.1" in r["id"]:
        base = r["id"].replace("|m1.1", "")
        b = H.get(base)
        pair[(b["verdict"] if b else None, r["verdict"])] += 1
print("x1.0 -> x1.1 (slope pairs):", dict(pair))
for tag in ("Fs0", "Fs8"):
    pc = Counter()
    for r in X:
        if r["id"].endswith("|" + tag):
            b = H.get(r["id"].replace("|" + tag, ""))
            pc[(b["verdict"] if b else None, r["verdict"])] += 1
    print(tag, dict(pc))
pc = Counter()
for r in X:
    if "|middle|" in r["id"]:
        b = H.get(r["id"].replace("|middle|", "|top|"))
        pc[(b["verdict"] if b else None, r["verdict"])] += 1
print("mid", dict(pc))
# g6 READY change vs R2DS
g6 = [r for r in L(R / "finB2_p0.json")["records"] if r["suite"] == "g6"]
R2 = {r["id"]: r for r in L(W / "06_analysis/02_control/s9/rev83/R2DS_g6.json")["records"]}
d = [r["t_ready_s"] - R2[r["id"]]["t_ready_s"] for r in g6 if r["hash"] != R2[r["id"]]["hash"] and r["t_ready_s"] and R2[r["id"]]["t_ready_s"]]
print("g6 dREADY changed", len(d), round(min(d), 1), round(max(d), 1))
