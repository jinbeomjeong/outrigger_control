"""B5 wide (baseline comparison) with the final controller: validity, patch check, judgement, change vs the previous run.

Inputs (all JSON, no simulation):
  new   rev84/fin2_b5_wide_official.json  (final controller C2 = R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30)
  old   rev84/b5_wide_official.json       (previous official B5 run, R7-era C2) and
        rev84/b5_wide_A/B1/B2.json        (previous lite run used by the paper, merged)
  main  rev84/b5_main.json                (16 table cases, previous run)
  wrap  rev85/finB2_harness.json, rev85/finB2_p0.json (final wrapper runs, command hashes)
  ref   rev83/R2DS_g6.json                (G6 reference for the soft-patch check)
Output: rev85/evidence/b5_final_compare.json (+ printed digest, ASCII).
Usage (dynamics-dev): python -I b5_final_compare.py <project root> <out json>
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
S9 = ROOT / "06_analysis" / "02_control" / "s9"
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
from b5_baseline_compare import CASES, CASE_DISPLAY_NAMES  # noqa: E402
from b5_baseline_table import backfill_gates, cells  # noqa: E402

CTRL = ("C2", "ABL", "IND")
STOP = "stroke_limited_stop"
EXPECTED_SETTINGS = {
    "C2": {"soil_stop": True, "soil_stop_scope": "any_loc", "flat_soil_margin_m": 0.03},
    "ABL": {"soil_stop": False, "flat_soil_margin_m": 0.0},
    "IND": {"soil_stop": None, "soil_stop_scope": None, "flat_soil_margin_m": None},
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def by_key(records):
    out = {}
    for r in records:
        backfill_gates(r)
        out[(r["case"], r["controller"])] = r
    return out


def median(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 2) if values else None


new_doc = load(S9 / "rev84" / "fin2_b5_wide_official.json")
new = by_key(new_doc["records"])
old = by_key(load(S9 / "rev84" / "b5_wide_official.json")["records"])
old_lite = {}
for name in ("b5_wide_A.json", "b5_wide_B1.json", "b5_wide_B2.json"):
    old_lite.update(by_key(load(S9 / "rev84" / name)["records"]))
main_old = by_key(load(S9 / "rev84" / "b5_main.json")["records"])
cases = sorted({c for c, _ in new})

# ---------------------------------------------------------------- A. validity
records = new_doc["records"]
pairs = Counter((r["case"], r["controller"]) for r in records)
g_rows = [r for r in records if r["case"].startswith("G|")]
g1_weak = [r for r in g_rows if r["src"].split("|")[1].startswith("G1+")]
settings = new_doc["meta"]["controller_settings"]
settings_ok = {c: all(settings[c].get(k) == v for k, v in EXPECTED_SETTINGS[c].items()) for c in CTRL}
rec_settings_ok = all(all(r["controller_settings"].get(k) == v for k, v in EXPECTED_SETTINGS[r["controller"]].items())
                      for r in records)
text = (S9 / "rev84" / "fin2_b5_wide_official.json").read_text(encoding="utf-8")
validity = {
    "records": len(records), "meta_jobs": new_doc["meta"]["jobs"],
    "cases": len(cases), "slope_cases": sum(c.startswith("S|") for c in cases),
    "g6_cases": sum(c.startswith("G|") for c in cases),
    "per_controller": dict(Counter(r["controller"] for r in records)),
    "duplicate_pairs": sum(1 for v in pairs.values() if v > 1),
    "missing_pairs": [(c, k) for c in cases for k in CTRL if (c, k) not in pairs],
    "error_records": sum("error" in r for r in records),
    "text_WeakPatchMissing": text.count("WeakPatchMissing"),
    "g6_rows": len(g_rows),
    "g1_weak_rows": len(g1_weak),
    "g1_weak_soil_model": dict(Counter(r.get("soil_model") for r in g1_weak)),
    "g1_weak_r72_path": dict(Counter(r.get("r72_path") for r in g1_weak)),
    "g6_soil_model_all": dict(Counter(str(r.get("soil_model")) for r in g_rows)),
    "g6_soil_model_none_srcs": sorted({r["src"] for r in g_rows if r.get("soil_model") is None}),
    "meta_r72_path_env": new_doc["meta"].get("r72_path_env"),
    "meta_controller_settings": settings, "meta_settings_ok": settings_ok,
    "record_settings_ok": rec_settings_ok,
    "settle_table_sha256": new_doc["meta"]["settle_table_sha256"],
    "wall_s": new_doc["meta"]["wall_s"], "workers": new_doc["meta"]["workers"],
}

# ---------------------------------------------------------------- B. hash identity
wrap = {}
for name in ("finB2_harness.json", "finB2_p0.json"):
    for r in load(S9 / "rev85" / name)["records"]:
        wrap[r["id"]] = r
hash_vs_wrap = Counter()
hash_vs_wrap_diff = []
for c in cases:
    r = new[(c, "C2")]
    w = wrap.get(r["src"])
    if w is None:
        hash_vs_wrap["no_wrapper_row"] += 1
        continue
    same = w.get("hash") == r["commands_sha256"]
    hash_vs_wrap["same" if same else "diff"] += 1
    if not same:
        hash_vs_wrap_diff.append(c)
hash_old_new = {k: Counter() for k in CTRL}
c2_hash_changed = []
for c in cases:
    for k in CTRL:
        same = old[(c, k)]["commands_sha256"] == new[(c, k)]["commands_sha256"]
        hash_old_new[k]["same" if same else "diff"] += 1
        if k == "C2" and not same:
            c2_hash_changed.append(c)
lite_vs_official_old = sum(old[(c, k)]["commands_sha256"] == old_lite[(c, k)]["commands_sha256"]
                           for c in cases for k in CTRL)

# ---------------------------------------------------------------- C. soft-patch check
ref = {r["id"]: r for r in load(S9 / "rev83" / "R2DS_g6.json")["records"]}


def patch_groups(store, ctrl):
    g = defaultdict(list)
    for c in cases:
        if not c.startswith("G|"):
            continue
        r = store[(c, ctrl)]
        soil = r["src"].split("|")[1]
        if "+" not in soil:
            continue
        base, rest = soil.split("+", 1)
        g[f"{base}+{rest.split('@')[0]}"].append(r)
    return {k: {"n": len(v), "ready_med_s": median(x["t_ready_s"] for x in v),
                "stroke_med_mm": median(x["max_motor_stroke_mm"] for x in v)} for k, v in sorted(g.items())}


ref_groups = defaultdict(list)
for i, r in ref.items():
    soil = i.split("|")[1]
    if "+" in soil:
        base, rest = soil.split("+", 1)
        ref_groups[f"{base}+{rest.split('@')[0]}"].append(r)
patch = {
    "new_C2": patch_groups(new, "C2"), "new_ABL": patch_groups(new, "ABL"), "new_IND": patch_groups(new, "IND"),
    "old_C2": patch_groups(old, "C2"), "old_IND": patch_groups(old, "IND"),
    "R2DS_g6": {k: {"n": len(v), "ready_med_s": median(x["t_ready_s"] for x in v),
                    "stroke_med_mm": median(x["max_stroke_mm"] for x in v)} for k, v in sorted(ref_groups.items())},
}

# ---------------------------------------------------------------- D. summary per controller


def classify(r):
    if r["controller"] == "C2" and r.get("official_verdict") == STOP:
        return "stop"
    return "pass" if r["lite_pass"] else "fail"


def summarize(store, subset=None):
    out = {}
    for k in CTRL:
        rs = [store[(c, k)] for c in cases if subset is None or c.startswith(subset)]
        cls = Counter(classify(r) for r in rs)
        gates = Counter(g for r in rs for g, ok in r["lite_gates"].items() if not ok)
        gates_nonstop = Counter(g for r in rs if classify(r) == "fail" for g, ok in r["lite_gates"].items() if not ok)
        out[k] = {
            "runs": len(rs), "lite_pass": cls["pass"], "safe_stop": cls["stop"] if k == "C2" else None,
            "fail_other": cls["fail"], "gate_failures": dict(gates), "gate_failures_excl_stop": dict(gates_nonstop),
            "crawler_liftoff_fail": sum(r["crawler_liftoff_fail"] for r in rs),
            "crawler_recontact_runs": sum(bool(r["n_crawler_recontact"]) for r in rs),
            "false_loc_runs": sum(bool(r["false_loc"]) for r in rs),
            "fault": sum(r["fault"] for r in rs),
            "ready_median_lite_pass_s": median(r["t_ready_s"] for r in rs if r["lite_pass"]),
            "official_verdict": dict(Counter(r.get("official_verdict") for r in rs)),
        }
    return out


summary = {"wide_293": summarize(new), "slope_177": summarize(new, "S|"), "g6_116": summarize(new, "G|"),
           "old_official_293": summarize(old), "old_lite_293": summarize(old_lite)}

# ---------------------------------------------------------------- E. C2 transitions old (lite) -> new
def change_cause(o, n):
    """Cause of a C2 change old -> new (commands differ unless 'same commands')."""
    if o["commands_sha256"] == n["commands_sha256"]:
        return "same commands"
    if n.get("official_verdict") == STOP:
        return "SGS stop (stroke_limited_stop)"
    if "FAULT_LIFT_STROKE_LIMIT" in n["warnings"]:
        return "stroke guard FAULT judged fail (F_min / attitude lost before the stop)"
    return "R4c30 (flat-soil LOC clearance target +30 mm)"


trans = Counter()
trans_cases = defaultdict(list)
cause = {}
for c in cases:
    cause[c] = change_cause(old_lite[(c, "C2")], new[(c, "C2")])
for c in cases:
    o, n = old_lite[(c, "C2")], new[(c, "C2")]
    key = f"{'pass' if o['lite_pass'] else 'fail'}->{classify(n)}"
    trans[key] += 1
    hash_changed = o["commands_sha256"] != n["commands_sha256"]
    if key != "pass->pass" or hash_changed:
        why = change_cause(o, n)
        trans_cases[key].append({
            "case": c, "cause": why,
            "old": {"lite": o["lite_pass"], "verdict": old[(c, "C2")].get("official_verdict"),
                    "failed_gates": [g for g, ok in o["lite_gates"].items() if not ok],
                    "t_ready_s": o["t_ready_s"], "crawler_fail": o["crawler_liftoff_fail"],
                    "rut_mm": o["rut_all_ready_mm"], "stroke_mm": o["max_motor_stroke_mm"]},
            "new": {"lite": n["lite_pass"], "verdict": n.get("official_verdict"),
                    "failed_gates": [g for g, ok in n["lite_gates"].items() if not ok],
                    "t_ready_s": n["t_ready_s"], "crawler_fail": n["crawler_liftoff_fail"],
                    "rut_mm": n["rut_all_ready_mm"], "stroke_mm": n["max_motor_stroke_mm"],
                    "warnings": n["warnings"], "final_phase": n["final_phase"]}})
hash_change_by_cause = Counter(cause[c] for c in c2_hash_changed)
r4_like = [c for c in c2_hash_changed if cause[c].startswith("R4c30")]
lite_vs_official_c2 = Counter(f"lite {classify(new[(c, 'C2')])} / official {new[(c, 'C2')].get('official_verdict')}"
                              for c in cases)
r4_rut = [{"case": c, "old_rut": old_lite[(c, "C2")]["rut_all_ready_mm"], "new_rut": new[(c, "C2")]["rut_all_ready_mm"],
           "old_ready": old_lite[(c, "C2")]["t_ready_s"], "new_ready": new[(c, "C2")]["t_ready_s"],
           "old_lite": old_lite[(c, "C2")]["lite_pass"], "new_lite": new[(c, "C2")]["lite_pass"]} for c in r4_like]

# C2 vs IND cross table (new)
cross = Counter(f"C2 {classify(new[(c, 'C2')])} / IND {classify(new[(c, 'IND')])}" for c in cases)
cross_old = Counter(f"C2 {'pass' if old_lite[(c, 'C2')]['lite_pass'] else 'fail'} / IND "
                    f"{'pass' if old_lite[(c, 'IND')]['lite_pass'] else 'fail'}" for c in cases)
c2_fail_new = [{"case": c, "gates": [g for g, ok in new[(c, "C2")]["lite_gates"].items() if not ok],
                "verdict": new[(c, "C2")].get("official_verdict"), "IND": classify(new[(c, "IND")]),
                "warnings": new[(c, "C2")]["warnings"], "final_phase": new[(c, "C2")]["final_phase"]}
               for c in cases if classify(new[(c, "C2")]) == "fail"]

# ---------------------------------------------------------------- F. 16 table cases
CELL_FIELDS = ("att_end_absmax_deg", "t_ready_s", "min_Fcyl_after_off_kN", "below_Fmin_after_off_s",
               "rut_all_ready_mm", "crawler_liftoff_fail", "crawler_N_at_ready", "p_max_move_bar", "commands_sha256")
table = {}
for case, spec in CASES.items():
    prefix = "S|" if spec["harness"] == "slope" else "G|"
    plain = not any(k in spec for k in ("fs_kN", "event", "hold_s"))
    wid = prefix + spec["src"]
    row = {"display": CASE_DISPLAY_NAMES[case], "src": spec["src"], "wide_id": wid if plain else None}
    if plain and (wid, "C2") in new:
        same_old = {k: all(main_old[(case, k)].get(f) == old[(wid, k)].get(f) for f in CELL_FIELDS) for k in CTRL}
        row["old_main_equals_old_wide"] = same_old
        row["c2_hash_changed"] = new[(wid, "C2")]["commands_sha256"] != old[(wid, "C2")]["commands_sha256"]
        recs = {k: new[(wid, k)] for k in CTRL}
        row["cells_new"] = cells(recs)
        row["c2_new"] = {f: recs["C2"].get(f) for f in CELL_FIELDS if f != "commands_sha256"}
        row["c2_new"].update({"min_Fcyl_after_event_kN": recs["C2"].get("min_Fcyl_after_event_kN"),
                              "lite_pass": recs["C2"]["lite_pass"], "verdict": recs["C2"].get("official_verdict")})
        row["source"] = "fin2 wide (same src, harness defaults)"
    else:
        recs = {k: main_old[(case, k)] for k in CTRL}
        row["cells_old_main"] = cells(recs)
        row["source"] = "not in wide set (F_s override / event): old b5_main only, needs final rerun"
    row["cells_old_main_all"] = cells({k: main_old[(case, k)] for k in CTRL})
    table[case] = row
rigid_flat = "S|H5|rigid|B|top|flat"
table_note = {"rigid_flat_c2_hash_same_old_new": new[(rigid_flat, "C2")]["commands_sha256"]
              == old[(rigid_flat, "C2")]["commands_sha256"]}

result = {"validity": validity,
          "hash": {"c2_new_vs_finB2_wrapper": dict(hash_vs_wrap), "c2_new_vs_finB2_diff": hash_vs_wrap_diff,
                   "old_vs_new": {k: dict(v) for k, v in hash_old_new.items()},
                   "old_official_vs_old_lite_same_pairs": lite_vs_official_old,
                   "c2_hash_changed_n": len(c2_hash_changed), "c2_hash_change_cause": dict(hash_change_by_cause)},
          "patch_check": patch, "summary": summary,
          "c2_transitions_old_lite_to_new": dict(trans), "c2_transition_cases": trans_cases,
          "r4_like_hash_changes": r4_rut,
          "r4_rut_delta_mm": {"n": len(r4_rut), "min": min(x["new_rut"] - x["old_rut"] for x in r4_rut if x["new_rut"] is not None),
                              "median": median([x["new_rut"] - x["old_rut"] for x in r4_rut if x["new_rut"] is not None]),
                              "max": max(x["new_rut"] - x["old_rut"] for x in r4_rut if x["new_rut"] is not None)},
          "r4_ready_delta_s": {"median": median([x["new_ready"] - x["old_ready"] for x in r4_rut if x["new_ready"] is not None]),
                               "min": min(x["new_ready"] - x["old_ready"] for x in r4_rut if x["new_ready"] is not None),
                               "max": max(x["new_ready"] - x["old_ready"] for x in r4_rut if x["new_ready"] is not None)},
          "r4_lite_change": dict(Counter(f"{x['old_lite']}->{x['new_lite']}" for x in r4_rut)),
          "c2_lite_vs_official_new": dict(lite_vs_official_c2),
          "cross_C2_IND_new": dict(cross), "cross_C2_IND_old": dict(cross_old), "c2_fail_new": c2_fail_new,
          "table16": table, "table_note": table_note}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
digest = {k: result[k] for k in ("hash", "c2_transitions_old_lite_to_new", "cross_C2_IND_new", "cross_C2_IND_old",
                                 "r4_rut_delta_mm", "r4_ready_delta_s", "r4_lite_change", "c2_lite_vs_official_new")}
print(json.dumps(digest, indent=1, ensure_ascii=True, default=str))
print(json.dumps(result["summary"], ensure_ascii=True))
print(json.dumps(patch, ensure_ascii=True))
