"""Aggregate final-controller harness results, part 4 (read-only)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9")
R = ROOT / "rev85"
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
X = L(R / "finB2_x426b_rejudged.json")
print("settle_rejudge meta", json.dumps(X["meta"].get("settle_rejudge"), ensure_ascii=False)[:900])
for r in X["records"]:
    if "m1.1" in r["id"]:
        ss = r.get("soil_stop") or {}
        print(r["id"], "before:", r.get("verdict_before_settle_v2"), "src:", r.get("settle_v2_source"), "stop:", ss.get("pass") if ss else None, ss.get("stop_with_crawler_loaded") if ss else None, "crawlerAfterReady", r.get("crawler_N_max_after_ready"))
Xr = L(R / "finB2_x426b.json")
print("raw x426b verdicts", Counter(r["verdict"] for r in Xr["records"]))
print("raw m1.1", Counter(r["verdict"] for r in Xr["records"] if "m1.1" in r["id"]))
for r in Xr["records"]:
    if "m1.1" in r["id"]:
        print("   raw", r["id"], r["verdict"], r["failed_rows"])
# C
C = L(R / "fin_x426_C.json")["results"]
print("C n", len(C), Counter(r["pass"] for r in C))
print("C keys", list(C[0].keys()))
fl = Counter(); [fl.update(r.get("flags") or []) for r in C]
print("C flags", dict(fl))
for r in C:
    if not r["pass"]:
        print("  C fail", r["key"], {k: v for k, v in r["gates"].items() if v is not True})
print("C crawler after ready max", max((r.get("crawler_N_max_after_ready") or 0) for r in C))
# compare C to old
Co = {r["key"]: r for r in L(R / "x426_C.json")["results"]}
for r in C:
    o = Co.get(r["key"])
    if o and (o.get("t_ready_s") != r.get("t_ready_s")):
        pass
dif = [(r["key"], round(Co[r["key"]]["t_ready_s"] or -1, 1), round(r["t_ready_s"] or -1, 1)) for r in C if r["key"] in Co and abs((Co[r["key"]]["t_ready_s"] or 0) - (r["t_ready_s"] or 0)) > 0.05]
print("C ready changed", len(dif), dif[:60])
for key in ("g6|G1+J2@RR|top|Fs4|PA", "g6|G1+S1@RR|top|Fs4|PA", "g6r|rigid+J2@RR|top|Fs4|PA"):
    r = [x for x in C if x["key"] == key]
    if r: print("  C", key, round(r[0]["t_ready_s"], 1))
# D
D = L(R / "fin_x426_D.json")
print("D summary", D["summary"])
ct = D["cases_table"]
print("D verdicts", Counter(c["verdict"] for c in ct))
Do = {c["id"]: c for c in L(R / "x426_D.json")["cases_table"]}
for c in ct:
    o = Do.get(c["id"])
    print("  D", c["id"], c["verdict"], round(c["t_ready_s"] or -1, 1), "old", round(o["t_ready_s"] or -1, 1) if o else None, "stroke %.1f" % c["max_stroke_mm"], "rut %.1f" % (c["rut_ready_mm"] or -1), "end %.1f" % (c.get("rut_end_mm") or -1))
# A
A = L(R / "finB2_A.json")["results"]
print("A runs keys", list(A[0]["runs"][0].keys()))
