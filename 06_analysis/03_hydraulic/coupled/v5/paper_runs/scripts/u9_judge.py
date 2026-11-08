"""U-9 targeted harness judgement by the sealed rules u9_targeted_rules_rev1.md (SHA-256 644005b7...).

Reads u9_targeted.jsonl, p3_hash.jsonl, main.jsonl and the T4h replay output (argv[1]);
writes the per-key values and the verdict to argv[2]. J items reuse J_fails / metrics of
ctrl_v5s1/judge_stage1_r5.py (stage 1 judge code, same criteria).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ctrl_v5s1"))
import judge_stage1_r5 as js  # noqa: E402

V5 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5")
t4h_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

T3A, T3B, T3C = 0.10, 0.05, 0.10
T4_FLOOR, T4_ADD = 20.0, 5.0
AB_EDGE = 0.5
H0_KEYS = {("S2", 0.002), ("S3", 0.0), ("R3", 0.0), ("S5", 0.0)}


def load(name):
    return [json.loads(l) for l in (V5 / name).read_text("utf-8").splitlines() if l.strip()]


def setting_of(rec):
    j = rec["job"]
    return j["setting"] if j["setting"] == "V0" else f"VB{j.get('eta_v', 0.85):g}"


recs = load("u9_targeted.jsonl")
p3 = load("p3_hash.jsonl")
main = load("main.jsonl")
t4h = json.loads(t4h_path.read_text("utf-8"))

out = {"rules": "u9_targeted_rules_rev1.md 644005b706ba46ce...", "n_runs": len(recs),
       "errors": sum("error" in r for r in recs)}

# ---- H0
def eps(rec):
    return float(rec["job"].get("eps", 0.0))


p3_by = defaultdict(list)
for r in p3:
    j = r.get("job", {})
    p3_by[(j.get("case"), float(j.get("eps", 0.0)), j.get("setting"))].append(r.get("commands_sha256"))
main_by = defaultdict(list)
for r in main:
    j = r["job"]
    if j.get("offset_s") is None and not j.get("twin") and j.get("decision") != "reanchor_on":
        main_by[(j["case"], float(j.get("eps", 0.0)), j["setting"])].append(r["commands_sha256"])
h0 = []
for r in recs:
    st = setting_of(r)
    key = (r["job"]["case"], eps(r))
    entry = {"case": key[0], "eps": key[1], "setting": st, "sha": r["commands_sha256"][:16]}
    if st == "VB0.85":
        if key in H0_KEYS:
            ref = p3_by.get((key[0], key[1], "VB"), [])
            entry.update(kind="H0-1 p3_hash", ref=[x[:16] for x in ref], equal=r["commands_sha256"] in ref and len(ref) > 0)
        else:
            ref = main_by.get((key[0], key[1], "VB"), [])
            entry.update(kind="H0-2 main VB (record)", ref=[x[:16] for x in ref], equal=r["commands_sha256"] in ref)
    elif st == "V0":
        ref = main_by.get((key[0], key[1], "V0"), [])
        entry.update(kind="V0 vs main V0 (record)", ref=[x[:16] for x in ref], equal=r["commands_sha256"] in ref)
    else:
        entry.update(kind="eta 0.80 (no reference)")
    h0.append(entry)
out["H0"] = h0
out["H0_1_pass"] = all(e["equal"] for e in h0 if e.get("kind") == "H0-1 p3_hash")
out["H0_1_count"] = sum(e.get("kind") == "H0-1 p3_hash" for e in h0)
out["p3_hash_keys"] = sorted({f"{k[0]}|{k[1]}|{k[2]}" for k in p3_by})[:80]

# ---- metrics and J items
rows = {}
for r in recs:
    m = js.metrics(r)
    m["setting"] = setting_of(r)
    rows[(r["job"]["case"], eps(r), m["setting"])] = (m, r)
v0_groups = defaultdict(list)
for (case, e, st), (m, r) in rows.items():
    if st == "V0":
        v0_groups[case].append(m)
nrev_max = {c: max(m["n_rev"] for m in ms) for c, ms in v0_groups.items()}

# J-P3 from the T4h replay (criteria rev. 9)
jp3 = t4h.get("J-P3")
jp3_by_file = {}
for row in t4h.get("rows", []):
    jp3_by_file[row["file"]] = {k: row.get(k) for k in row if "p3" in k.lower() or "rod" in k.lower() or "breach" in k.lower()}
out["J_P3"] = jp3
out["T4h"] = {"runs": t4h.get("runs"), "runs_over": t4h.get("runs_over"),
              "max_excess_N": max((x["max_excess_N"] for x in t4h["rows"] if x.get("max_excess_N") is not None), default=None),
              "tail_max_excess_N": max((x["unlocked_tail_max_excess_N"] for x in t4h["rows"]
                                        if x.get("unlocked_tail_max_excess_N") is not None), default=None)}

keys = sorted({(c, e) for (c, e, st) in rows})
per_key = []
for case, e in keys:
    b = rows[(case, e, "V0")][0]
    k = {"case": case, "eps": e}
    for st in ("V0", "VB0.85", "VB0.8"):
        m, r = rows[(case, e, st)]
        v = r["values"]
        u9 = v.get("U9") or {}
        e1 = (v.get("E1") or {}).get("level", {})
        e2 = v.get("E2") or {}
        e5 = v.get("E5") or {}
        lvl_r = {leg: (x.get("min_r_by_phase") or {}).get("level") for leg, x in e2.items()}
        k[st] = {
            "final": m["final"], "class": m["class"], "t_ready": m["t_ready"], "F_after": m["F_after"],
            "att_last5": m["att_last5"], "att_max_after_liftoff": v["attitude"]["max_abs_after_liftoff_deg"],
            "n_rev": m["n_rev"], "bad": m["bad"], "p_move": m["p_move"],
            "supply_L_min": v.get("supply_L_min"),
            "U9": {kk: u9.get(kk) for kk in ("level_count_s", "post_touch_count_s", "longest_ge3_s", "longest_eq4_s",
                                              "ge3_runs_count", "level_sat_rate_max_deg_s")},
            "ge3_runs": u9.get("ge3_runs") or [],
            "E1_level_short_s": e1.get("short_s"), "E2_level_min_r": lvl_r,
            "E4": {kk: (v.get("E4") or {}).get(kk) for kk in ("group_time_s", "saturated_s")},
            "E5": e5, "sha": r["commands_sha256"][:16],
        }
        if st != "V0":
            k[st]["J_fails"] = js.J_fails(b, m, v0_groups[case], nrev_max[case])
    # T3 / T4 on eta 0.80 (baseline eta 0.85 for T3c / T4)
    lo, hi = k["VB0.8"], k["VB0.85"]
    t3a = [max(abs(x) for x in g["max_abs_delta_deg"].values()) if isinstance(g["max_abs_delta_deg"], dict)
           else max(abs(x) for x in g["max_abs_delta_deg"]) for g in lo["ge3_runs"]]

    def axes(val):
        """Roll and pitch only (the filtered dicts also carry the sample time t_s)."""
        return [val["roll"], val["pitch"]] if isinstance(val, dict) else list(val)

    t3b_ok = True
    t3b_detail = []
    for g in lo["ge3_runs"]:
        s0, s1 = axes(g["filtered_start_deg"]), axes(g["filtered_end_deg"])
        ok = all(abs(b1) <= abs(a0) + T3B for a0, b1 in zip(s0, s1))
        t3b_ok &= ok
        t3b_detail.append({"t_start_s": g["t_start_s"], "start": s0, "end": s1, "ok": ok})
    t3c_val = lo["att_max_after_liftoff"] - hi["att_max_after_liftoff"]
    b_lo = lo["E5"].get("back_in_band_after_saturation_s")
    b_hi = hi["E5"].get("back_in_band_after_saturation_s")
    t4_lim = max(T4_FLOOR, (b_hi if b_hi is not None else 0.0) + T4_ADD)
    k["T3a"] = {"max_delta_deg": max(t3a) if t3a else None, "pass": all(x <= T3A for x in t3a)}
    k["T3b"] = {"pass": t3b_ok, "runs": t3b_detail}
    k["T3c"] = {"delta_deg": t3c_val, "pass": t3c_val <= T3C}
    k["T4"] = {"value_s": b_lo, "limit_s": t4_lim, "baseline_s": b_hi, "pass": b_lo is not None and b_lo <= t4_lim,
               "flag_integral_limit": (lo["E5"].get("max_abs_integral_rad_s") or 0) >= (lo["E5"].get("integral_limit_rad_s") or 0.02)}
    k["T5_ready_delta_s"] = None if lo["t_ready"] is None or hi["t_ready"] is None else lo["t_ready"] - hi["t_ready"]
    k["T1"] = {"VB0.85_fail": bool(hi["J_fails"]), "VB0.8_fail": bool(lo["J_fails"]),
               "saturation_caused": (not hi["J_fails"]) and bool(lo["J_fails"])}
    per_key.append(k)
out["keys"] = per_key

# ---- classification
any_sat_fail = any(k["T1"]["saturation_caused"] for k in per_key)
any_t3t4_fail = any(not (k["T3a"]["pass"] and k["T3b"]["pass"] and k["T4"]["pass"]) for k in per_key)
any_t3c_fail = any(not k["T3c"]["pass"] for k in per_key)
non_sat_fail = [f"{k['case']}|{k['eps']}" for k in per_key if k["T1"]["VB0.85_fail"]]
longest = max((k["VB0.8"]["U9"]["longest_ge3_s"] or 0.0) for k in per_key)
longest4 = max((k["VB0.8"]["U9"]["longest_eq4_s"] or 0.0) for k in per_key)
if any_sat_fail or any_t3t4_fail or any_t3c_fail:
    cls = "C"
elif longest >= AB_EDGE:
    cls = "A"
else:
    cls = "B"
out["classification"] = {"class": cls, "saturation_caused_T1_fail": any_sat_fail, "T3ab_T4_fail": any_t3t4_fail,
                         "T3c_fail": any_t3c_fail, "D_rows_VB0.85_fail": non_sat_fail,
                         "longest_ge3_s_eta080": longest, "longest_eq4_s_eta080": longest4}
# values for the fixed sentence
all_ge3 = [g for k in per_key for g in k["VB0.8"]["ge3_runs"]]
out["sentence_values"] = {
    "x_longest_ge3_s": longest, "y_longest_eq4_s": longest4,
    "z_max_delta_deg": max((k["T3a"]["max_delta_deg"] or 0.0) for k in per_key),
    "w_back_in_band_max_s": max((k["T4"]["value_s"] or 0.0) for k in per_key),
    "r_min_front_level_eta080": min(min(v for leg, v in k["VB0.8"]["E2_level_min_r"].items() if v is not None and leg in ("FL", "FR"))
                                    for k in per_key if any(v is not None for v in k["VB0.8"]["E2_level_min_r"].values())),
    "n_ge3_runs_eta080": len(all_ge3),
    "eta085_longest_ge3_s": max((k["VB0.85"]["U9"]["longest_ge3_s"] or 0.0) for k in per_key),
    "eta085_longest_eq4_s": max((k["VB0.85"]["U9"]["longest_eq4_s"] or 0.0) for k in per_key),
    "eta085_max_delta_deg": max((max(g["max_abs_delta_deg"]["roll"], g["max_abs_delta_deg"]["pitch"])
                                 for k in per_key for g in k["VB0.85"]["ge3_runs"]), default=None),
    "n_ge3_runs_eta085": sum(len(k["VB0.85"]["ge3_runs"]) for k in per_key),
    "T4_flag_integral_keys": [f"{k['case']}|{k['eps']}" for k in per_key if k["T4"]["flag_integral_limit"]]}
out_path.write_text(json.dumps(out, indent=1, default=str), "utf-8")
print(json.dumps({"H0_1_pass": out["H0_1_pass"], "H0_1_count": out["H0_1_count"], "class": out["classification"],
                  "sentence": out["sentence_values"], "J-P3": jp3 and jp3.get("status")}, indent=1))
