import json, collections
from pathlib import Path
d = json.loads(Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85\fin_x426_C.json").read_text(encoding="utf-8"))
rs = d["results"]
print(collections.Counter((r["pad"], r["level"], r["fs_kN"]) for r in rs))
B = [r for r in rs if r["pad"] in ("B", "dwg_rear250")]
print("B n", len(B), "pass", collections.Counter(r["pass"] for r in B))
print("B gates fail", collections.Counter(k for r in B for k, v in (r["gates"] or {}).items() if v is False))
print("B flags", collections.Counter(f for r in B for f in r["flags"]))
soft = [r for r in B if r["weak_leg"]]
print("B soft n", len(soft), "READY", min(r["t_ready_s"] for r in soft if r["t_ready_s"]), max(r["t_ready_s"] for r in soft if r["t_ready_s"]))
mf = [r["min_true_Fcyl_after_off_kN"] for r in B if r["min_true_Fcyl_after_off_kN"] is not None]
print("B minF", min(mf), "att", max(abs(x) if not isinstance(x, list) else max(map(abs, x)) for x in (r["att_end_deg"] for r in B)))
print("B crawler after ready", max(r["crawler_N_max_after_ready"] or 0 for r in B))
print("by variant", collections.Counter((r["level"], r["fs_kN"], bool(r["weak_leg"])) for r in B))
print("flags rows", [(r["key"], r["flags"]) for r in B if r["flags"]])
print("ex", rs[0]["key"], rs[0]["pad"], rs[0]["gates"])
