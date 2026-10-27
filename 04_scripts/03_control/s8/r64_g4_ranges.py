"""Ranges of one variant of r64_g4_closed_loop.py over the runs with a target (FAULT time after t_f, travel,
duration, faulty-leg max force, G4-6 change, longest healthy dip, last-2 s mean / peak-to-peak).

Usage: python -I r64_g4_ranges.py <json> <variant>
"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
var = sys.argv[2]
rows = []
for r in d["runs"]:
    v = r["variants"].get(var)
    if not v or not (v["meta_run"] or {}).get("targets"):
        continue
    j = v["judge"]
    t = v["meta_run"]["targets"][0]
    rows.append({
        "case": r["case"], "off": r["offset_s"], "fault_minus_tf": round(j["t_fault_rel_s"] - j["t_f_rel_s"], 2),
        "travel_mm": round((t["travel_m"] or 0) * 1e3, 1), "dur_s": t["duration_s"] and round(t["duration_s"], 1),
        "outcome": t["outcome"], "cues": t["cues"], "faulty_max_kN": j["G4_5_faulty_max_kN"],
        "head_bar": j["G4_5_max_head_bar"], "g46": j["G4_6_mean_change_deg"],
        "dip_s": j["G4_5_healthy_longest_low_s"], "min": j["G4_4_min_kN"], "m05": j["G4_4_mean05_min_kN"],
        "last_mean": j["last2s_mean_kN"], "last_ptp": j["last2s_ptp_kN"]})
for x in rows:
    print(json.dumps(x, ensure_ascii=True))
for k in ("fault_minus_tf", "travel_mm", "dur_s", "faulty_max_kN", "head_bar", "g46"):
    vals = [x[k] for x in rows if x[k] is not None]
    print(k, min(vals), max(vals))
