"""Part 6: Chrono P3b G1 rows, rep-case harness values, E1 per-variable aggregates (read-only)."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
W = Path(r"C:\workspace\outrigger_control")
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
S = L(W / "06_analysis/01_chrono/19_S9/s9_P3b_summary.json")
rows = S["rows"]
print("row keys", list(next(iter(rows.values())).keys()))
vk = S.get("values_only")
print("values_only type", type(vk).__name__, (list(vk.keys())[:3] if isinstance(vk, dict) else None))
first = next(iter(vk.values())) if isinstance(vk, dict) else None
print("values_only sample", json.dumps(first, ensure_ascii=False)[:1200])
for k in sorted(rows):
    if "_G1_" in k:
        c = rows[k]["checks"]
        print(k, "att", round(c.get("P3-4_absmax_deg") or -1, 4), "P3-6", {kk: v for kk, v in c.items() if kk.startswith("P3-6") or kk.startswith("P3-3") or kk.startswith("P3-5")})
# rep-case final harness
R = W / "06_analysis/02_control/s9/rev85"
H = {r["id"]: r for r in L(R / "finB2_harness_rejudged.json")["records"]}
H9 = {r["id"]: r for r in L(R / "finB2_h9.json")["records"]}
P = {r["id"]: r for r in L(R / "finB2_p0.json")["records"]}
def show(src, i):
    r = src[i]
    ss = r.get("soil_stop") or {}
    print("REP", i, r["verdict"], "READY", None if r["t_ready_s"] is None else round(r["t_ready_s"], 1), "minF", None if r["min_force_kN"] is None else round(r["min_force_kN"], 2),
          "rut", None if r.get("rut_ready_mm") is None else round(r["rut_ready_mm"], 1), "stroke", round(r["max_stroke_mm"], 1),
          "att", [round(x, 4) for x in r["att_end_deg"]] if r.get("att_end_deg") else None,
          "stop", ss.get("stop_event"), ss.get("min_true_Fcyl_after_off_kN"), (ss.get("moving_pressure") or {}).get("max_moving_bar"), ss.get("stop_with_crawler_loaded"),
          "revokes", r["metrics"].get("l1_revokes"), "ds", r["metrics"].get("ds_events"))
for i in ("H3|J1|B|top|roll_pos@k0.875", "H6|J1|B|top|flat|m1.1", "H6|J2|B|top|flat|m1.1", "H6|J1|B|top|flat|m1.2", "H6|J1|B|top|flat", "H6|J2|B|top|flat"):
    show(H, i)
show(H9, "H9|J1|B|top|roll_neg@k0.65")
for i in ("base|J1|B|top|Fs4", "base|J2|B|top|Fs4", "base|J2|B|middle|Fs4"):
    show(P, i)
# rigid slope hashes vs R2DS
R2 = {r["id"]: r for r in L(W / "06_analysis/02_control/s9/rev83/R2DS_slope_rejudged.json")["records"]}
rig = [i for i in H if "|rigid|" in i and H[i]["suite"] == "slope"]
print("rigid slope same hash", sum(1 for i in rig if R2[i]["hash"] == H[i]["hash"]), "/", len(rig))
g1 = [i for i in H if "|G1|" in i and H[i]["suite"] == "slope"]
print("G1 slope same hash", sum(1 for i in g1 if R2[i]["hash"] == H[i]["hash"]), "/", len(g1))
print("all slope same hash", sum(1 for i in R2 if R2[i]["hash"] == H[i]["hash"]), "/", len(R2))
# E1 per variable
Pp = L(R / "harness_chrono_pairs.json")
agg = defaultdict(lambda: {"n": 0, "same": 0, "dr": [], "dg": [], "side": defaultdict(int)})
for p in Pp["pairs"]:
    v = p["variable"].split(" ")[0] + " " + p["variable"].split(" ")[1]
    a = agg[v]
    a["n"] += 1; a["same"] += p["delta"].get("verdict_same", 0)
    if p["delta"].get("d_ready_s") is not None: a["dr"].append(p["delta"]["d_ready_s"])
    if p["delta"].get("d_gap_ready_mm") is not None: a["dg"].append(p["delta"]["d_gap_ready_mm"])
    a["side"][p["side"]] += 1
for v, a in sorted(agg.items()):
    rr = "%.1f~%.1f" % (min(a["dr"]), max(a["dr"])) if a["dr"] else "-"
    gg = "%.1f~%.1f" % (min(a["dg"]), max(a["dg"])) if a["dg"] else "-"
    print("E1", v, a["n"], a["same"], rr, gg, dict(a["side"]))
alld = [p["delta"]["d_gap_ready_mm"] for p in Pp["pairs"] if p["delta"].get("d_gap_ready_mm") is not None]
print("gap n", len(alld), min(alld), max(alld), sum(alld) / len(alld))
# C preloc
C = L(R / "fin_x426_C.json")["results"]
for r in C:
    if not r["pass"]:
        print("Cpre", r["key"], r.get("preloc_flag_ok"), json.dumps(r.get("preloc_starts"), ensure_ascii=False)[:300])
