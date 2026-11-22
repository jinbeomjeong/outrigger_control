"""Summaries of the IMU attitude-only study outputs (read only): pair categories, absolute M1..M8 per arm and
level (and group), worse reasons, probe abstain causes, D1' faults. Usage: python -I -B analyse.py <runs dir> <out>"""
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

d = Path(sys.argv[1])
runs = json.load(open(d / "imuatt_metrics_runs.json", encoding="utf-8"))
pairs = list(csv.DictReader(open(d / "imuatt_pairs.csv", encoding="utf-8")))


def fl(x):
    return None if x in (None, "") else float(x)


def dist(vals):
    v = [x for x in vals if x is not None and math.isfinite(x)]
    if not v:
        return None
    a = np.array(v)
    return {"n": len(v), "min": round(float(a.min()), 4), "med": round(float(np.median(a)), 4),
            "p90": round(float(np.quantile(a, 0.9)), 4), "max": round(float(a.max()), 4)}


out = {"pairs": {}, "pairs_group": {}, "abs": {}, "abs_group": {}, "worse_reasons": {}, "abstain": {},
       "worst_cases": {}}
# --- pair categories
by = defaultdict(list)
byg = defaultdict(list)
for p in pairs:
    by[(p["arm"], p["level"])].append(p)
    byg[(p["arm"], p["level"], p["group"])].append(p)


def pair_cell(cell):
    c = Counter(p["category"] for p in cell)
    return {"n": len(cell), "worse": c["worse"], "equal": c["equal"], "better": c["better"],
            "d_M1": dist([fl(p["d_M1_deg"]) for p in cell]), "d_M2": dist([fl(p["d_M2_s"]) for p in cell]),
            "d_M3": dist([fl(p["d_M3_kN"]) for p in cell]),
            "risky": sum(int(p["risky_misjudged"]) for p in cell),
            "d_events": dist([fl(p["d_events"]) for p in cell])}


for k, cell in sorted(by.items()):
    out["pairs"]["|".join(k)] = pair_cell(cell)
    out["worse_reasons"]["|".join(k)] = dict(Counter(r for p in cell if p["category"] == "worse"
                                                     for r in p["reasons"].split("+")))
    better = Counter(r for p in cell if p["category"] == "better" for r in p["reasons"].split("+"))
    out["worse_reasons"]["|".join(k) + "|better"] = dict(better)
for k, cell in sorted(byg.items()):
    out["pairs_group"]["|".join(k)] = pair_cell(cell)

# --- absolute metrics
ab = defaultdict(list)
abg = defaultdict(list)
for r in runs:
    m = r["run_metrics"]
    ab[(r["arm"], r["level"])].append(m)
    abg[(r["arm"], r["level"], r["group"])].append(m)


def abs_cell(ms):
    g = lambda k: [m.get(k) for m in ms]  # noqa: E731
    causes = Counter()
    for m in ms:
        causes.update(m.get("M4_abstain_causes") or {})
    step = Counter()
    for m in ms:
        step.update(m.get("M6_d1_step_reasons") or {})
    return {
        "n": len(ms),
        "M1": dist(g("M1_deg")), "M1_fail_0p2": sum(1 for m in ms if m.get("M1_within_0p2") is False),
        "M2": dist(g("M2_s")), "t_ready": dist(g("t_ready_s")), "check_s": dist(g("check_duration_s")),
        "M3": dist(g("M3_kN")), "M3_below_Fmin_runs": sum(1 for m in ms if (m.get("M3_below_F_min") or 0) > 0),
        "M3_below_Fmin5_runs": sum(1 for m in ms if (m.get("M3_below_F_min_plus_5kN") or 0) > 0),
        "M4_abstain_rate": dist(g("M4_attitude_abstain_rate")), "M4_causes": dict(causes),
        "M4_risky": sum(m["M4_risky_misjudged"] for m in ms), "M4_safe": sum(m["M4_safe_misjudged"] for m in ms),
        "M4_probe_time": dist(g("M4_probe_time_s")), "M4_rounds": dist(g("M4_rounds")),
        "M4_unresolved": sum(m["M4_probe_unresolved"] for m in ms), "M4_regrounds": sum(m["M4_regrounds"] for m in ms),
        "M4_probe_att_change": dist(g("M4_probe_attitude_change_deg")),
        "M5_fault_events": sum(m["M5_fault_events"] for m in ms),
        "M5_fault_runs": sum(1 for m in ms if m["M5_fault_events"] > 0),
        "M5_fault_reground": sum(m["M5_fault_reground_entries"] for m in ms),
        "M5_soil_stops": sum(m["M5_soil_stops"] for m in ms), "M5_idle": sum(m["M5_idle_entries"] for m in ms),
        "M5_no_ready": sum(1 for m in ms if m["M5_no_ready"]),
        "M5_final_phase": dict(Counter(m["M5_final_phase"] for m in ms)),
        "M6_head_faults": sum(m["M6_head_faults"] for m in ms),
        "M6_head_fault_runs": sum(1 for m in ms if m["M6_head_faults"] > 0),
        "M6_fallback": sum(m["M6_fallback_starts"] for m in ms),
        "M6_imu_missing": sum(m["M6_imu_input_missing"] for m in ms), "M6_steps": dict(step),
        "M7_rev": dist(g("M7_command_reversals")), "M7_done_to_level": dist(g("M7_done_to_level")),
        "M7_relevels": dist(g("M7_relevels_30s")), "M7_cross": dist(g("M7_completion_crossings")),
        "M8_gate": dist(g("M8_gate_open_fraction_ready")), "M8_support": sum(m["M8_support_events"] for m in ms),
        "M8_dsb75_holds": sum(m["M8_dsb75_holds"] for m in ms), "M8_loc": sum(m["M8_loc"] for m in ms),
        "M8_revokes": sum((m.get("M8_loc_revokes") or 0) for m in ms),
        "gyro_bias": dict(Counter(m.get("gyro_bias_outcome") for m in ms)),
    }


for k, ms in sorted(ab.items()):
    out["abs"]["|".join(k)] = abs_cell(ms)
for k, ms in sorted(abg.items()):
    out["abs_group"]["|".join(k)] = abs_cell(ms)

# --- worst d_M2 / d_M1 cases per arm (L2)
for arm in sorted({p["arm"] for p in pairs}):
    cell = [p for p in pairs if p["arm"] == arm]
    m2 = sorted((p for p in cell if fl(p["d_M2_s"]) is not None), key=lambda p: -fl(p["d_M2_s"]))[:3]
    m1 = sorted((p for p in cell if fl(p["d_M1_deg"]) is not None), key=lambda p: -fl(p["d_M1_deg"]))[:3]
    m3 = sorted((p for p in cell if fl(p["d_M3_kN"]) is not None), key=lambda p: fl(p["d_M3_kN"]))[:3]
    ev = [p for p in cell if fl(p["d_events"]) and fl(p["d_events"]) > 0][:5]
    out["worst_cases"][arm] = {
        "d_M2": [(p["level"], p["seed_index"], p["case_id"], fl(p["d_M2_s"])) for p in m2],
        "d_M1": [(p["level"], p["seed_index"], p["case_id"], fl(p["d_M1_deg"])) for p in m1],
        "d_M3": [(p["level"], p["seed_index"], p["case_id"], fl(p["d_M3_kN"])) for p in m3],
        "d_events_pos": [(p["level"], p["seed_index"], p["case_id"], fl(p["d_events"])) for p in ev],
        "n_events_pos": sum(1 for p in cell if fl(p["d_events"]) and fl(p["d_events"]) > 0),
        "n_events_neg": sum(1 for p in cell if fl(p["d_events"]) and fl(p["d_events"]) < 0)}
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# --- compact print
print("== pairs (arm|level): n worse/equal/better | dM1 med/max | dM2 med/p90/max | dM3 min/med | risky | worse reasons")
for k, c in out["pairs"].items():
    m1, m2, m3 = c["d_M1"], c["d_M2"], c["d_M3"]
    print(k, c["n"], c["worse"], c["equal"], c["better"], "|",
          m1 and (m1["med"], m1["max"]), "|", m2 and (m2["med"], m2["p90"], m2["max"]), "|",
          m3 and (m3["min"], m3["med"]), "|", c["risky"], "|", out["worse_reasons"][k],
          "better:", out["worse_reasons"][k + "|better"])
print("== abs (arm|level)")
for k, c in out["abs"].items():
    print(k, "M1", c["M1"] and (c["M1"]["med"], c["M1"]["max"]), "fail", c["M1_fail_0p2"],
          "M2", c["M2"] and (c["M2"]["med"], c["M2"]["max"]), "chk", c["check_s"] and c["check_s"]["med"],
          "M3", c["M3"] and (c["M3"]["min"], c["M3"]["med"]), "<Fmin", c["M3_below_Fmin_runs"],
          "<Fmin+5", c["M3_below_Fmin5_runs"],
          "abst", c["M4_abstain_rate"] and (c["M4_abstain_rate"]["med"], c["M4_abstain_rate"]["max"]),
          "causes", c["M4_causes"], "risky", c["M4_risky"], "safe", c["M4_safe"],
          "ptime", c["M4_probe_time"] and c["M4_probe_time"]["med"], "unres", c["M4_unresolved"],
          "regr", c["M4_regrounds"], "patt", c["M4_probe_att_change"] and c["M4_probe_att_change"]["max"])
    print("   ", "FAULTev", c["M5_fault_events"], "FAULTruns", c["M5_fault_runs"], "FR", c["M5_fault_reground"],
          "soil", c["M5_soil_stops"], "idle", c["M5_idle"], "noREADY", c["M5_no_ready"], "final", c["M5_final_phase"],
          "head", c["M6_head_faults"], "headruns", c["M6_head_fault_runs"], "fb", c["M6_fallback"],
          "imumiss", c["M6_imu_missing"], "steps", c["M6_steps"])
    print("   ", "M7rev", c["M7_rev"] and (c["M7_rev"]["med"], c["M7_rev"]["max"]),
          "d2l", c["M7_done_to_level"] and c["M7_done_to_level"]["max"],
          "relev", c["M7_relevels"] and (c["M7_relevels"]["med"], c["M7_relevels"]["max"]),
          "cross", c["M7_cross"] and (c["M7_cross"]["med"], c["M7_cross"]["max"]),
          "gate", c["M8_gate"] and c["M8_gate"]["med"], "supp", c["M8_support"], "dsb", c["M8_dsb75_holds"],
          "loc", c["M8_loc"], "rev", c["M8_revokes"], "B1", c["gyro_bias"])
print("== worst cases")
for arm, w in out["worst_cases"].items():
    print(arm, json.dumps(w))
