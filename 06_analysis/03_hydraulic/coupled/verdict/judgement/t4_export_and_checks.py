"""T-4 phase of each observed set, run map of the structures, V-tables summary, Julia export.

Writes t4_set_map.json, v_checks.json, t4_export.json. Run with dynamics-dev, -I -B.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
V = HERE.parent
COUP = V.parent
SPEC = importlib.util.spec_from_file_location("t4_linear", HERE / "t4_linear.py")
T = importlib.util.module_from_spec(SPEC)
sys.modules["t4_linear"] = T
SPEC.loader.exec_module(T)
R, cl, dm = T.R, T.cl, T.dm

d = json.loads((V / "verdict_pairs.json").read_text(encoding="utf-8"))
res = json.loads((HERE / "t4_results.json").read_text(encoding="utf-8"))
summ = json.loads((HERE / "t4_summary.json").read_text(encoding="utf-8"))

# which phase each observed set's runs >= 1 s sit in
phase_rows = []
for p in d["pairs"]:
    j = json.loads((V / f"{p['run_id']}.json").read_text(encoding="utf-8"))
    v = j["values"]
    te = v["times"]["t_touch_end_s"]
    for name, s in v["T4_inputs"]["sets"].items():
        t = s["operating_point"]["t_s"]
        phase_rows.append({"run": p["run_id"], "set": name, "longest_s": s["longest_s"], "runs_ge_1s": s["runs_ge_1s"], "t_op_s": t,
                           "t_touch_end_s": te, "phase_op": "touch" if t <= te else "after_touch",
                           "p_max_bar": max(s["operating_point"]["p_load_Pa"].values()) / 1e5,
                           "p_P_bar": s["operating_point"]["p_P_Pa"] / 1e5, "law": v["T4_inputs"]["valve_constants"]["law"]})
four = [r for r in phase_rows if r["set"] == "FL+FR+RL+RR"]
others = [r for r in phase_rows if r["set"] != "FL+FR+RL+RR"]
sets_summary = {
    "four_leg": {"n": len(four), "all_runs_ge_1s_is_1": all(r["runs_ge_1s"] == 1 for r in four),
                 "all_touch": all(r["phase_op"] == "touch" for r in four), "p_load_max_bar": max(r["p_max_bar"] for r in four)},
    "others": {"n": len(others), "sets": sorted({r["set"] for r in others}), "all_after_touch": all(r["phase_op"] != "touch" for r in others),
               "p_load_range_bar": [min(r["p_max_bar"] for r in others), max(r["p_max_bar"] for r in others)]},
}
# structure -> runs, verdict
map_rows = []
for n, s in enumerate(res["sets"]):
    key = f"set{n}_{s['set']}"
    x = summ[key]
    map_rows.append({"key": key, "set": s["set"], "law": s["law"], "n_runs": len(s["runs"]), "runs": s["runs"], "t_op_s": s["op_t_s"],
                     "Ms_max": x["Ms_max"], "plant": x["plant"], "ch": x["ch"], "rho_excl": x["rho"], "rho_plant": x["rho_plant"],
                     "growth_1_s": np.log(max(x["rho"], 1e-9)) / 0.1,
                     "fail": x["Ms_max"] > 1.5 or x["rho"] >= 1.0})
(HERE / "t4_set_map.json").write_text(json.dumps({"phase": phase_rows, "summary": sets_summary, "structures": map_rows}, indent=1), encoding="utf-8")
print(json.dumps(sets_summary, indent=0))
for m in map_rows:
    print(m["key"], "n", m["n_runs"], "t", m["t_op_s"], "Ms", round(m["Ms_max"], 3), m["ch"], m["plant"], "rho", round(m["rho_excl"], 5), "growth", round(m["growth_1_s"], 3), "FAIL" if m["fail"] else "ok", m["runs"][:6])
rows = res["rows"]
fails = {}
for r in rows:
    if r["struct"].startswith("set") and "RL" in r["struct"]:
        fails.setdefault(r["struct"], [0, 0, 0])
        fails[r["struct"]][0] += r["rho_excl"] >= 1.0
        fails[r["struct"]][1] += max(r[c]["Ms"] for c in T.JUDGED) > 1.5
        fails[r["struct"]][2] += 1
print("4-leg count rho>=1, Ms>1.5, of", fails)
for s in ("single_RL", "single_RR"):
    fr = [r for r in rows if r["struct"] == s]
    print(s, "plants Ms>1.5", sum(max(r[c]["Ms"] for c in T.JUDGED) > 1.5 for r in fr), "of", len(fr))

# V tables
checks = {}
off = d["off_identity"]
checks["V5"] = {"n_off": len(off), "same": sum(1 for x in off if x["is_same"] is True), "no_stored": [x["case_id"] for x in off if x["is_same"] is None],
                "different": [x["case_id"] for x in off if x["is_same"] is False]}
b2 = json.loads((COUP / "v2b_summary.json").read_text(encoding="utf-8"))
br = b2["rows"]
checks["V2b"] = {"n": len(br), "balance_max": max(r["balance_after_20ms_cm3"] for r in br),
                 "balance_1ms_output_max": max(r["balance_after_20ms_1ms_output_cm3"] for r in br),
                 "excess_mean_max": max(r["excess_mean_steady"] for r in br),
                 "speed_err_max": max(r["speed_error_rel_vmax"] for r in br if r.get("speed_error_rel_vmax") is not None),
                 "limits": b2["meta"]["limits"], "keys": [k for k in br[0]],
                 "excess_volume_max_cm3": max(r["excess_volume_all_cm3"] for r in br)}
with open(COUP / "v3_table.csv", newline="", encoding="utf-8") as f:
    v3 = list(csv.DictReader(f))
grid = [r for r in v3 if r["on_grid"] == "True"]
checks["V3"] = {"n_grid": len(grid), "pass": sum(r["pass"] == "True" for r in grid), "max_dr": max(float(r["max_abs_dr"]) for r in grid),
                "off_grid_fail": [r["name"] for r in v3 if r["on_grid"] != "True" and r["pass"] != "True"],
                "same_sets": sum(r["same_rev3_equal_sets"] == "True" for r in grid)}
conv = json.loads((COUP / "converge_summary.json").read_text(encoding="utf-8"))
checks["V4_dt"] = {"n": len(conv), "not_match": {k: (v["verdict"], v.get("worst"), v.get("worst_change")) for k, v in conv.items() if v["verdict"] != "match"},
                   "worst_change": max(v.get("worst_change", 0) for v in conv.values())}
with open(COUP / "e4_table.csv", newline="", encoding="utf-8") as f:
    e4 = list(csv.DictReader(f))
checks["E4_record"] = {"n": len(e4), "flag_orig": sum(r["flag_orig"] == "True" for r in e4), "flag_rev3": sum(r["flag_rev3"] == "True" for r in e4),
                       "swaps_rev3_max": max(int(r["swaps_rev3"]) for r in e4)}
(HERE / "v_checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
print(json.dumps(checks, indent=0))

# Julia export: nominal + single RL/RR/FL + worst FL+FR + the four-leg worst Ms and worst rho, on their worst plants
items = R.catalogue_ext()
by_tag = {R.tag(R.make_plant(it)): it for it in items}
cc = cl.nominal_controller_constants()
set_def = {f"set{n}_{s['set']}": s for n, s in enumerate(res["sets"])}
worst_four_ms = max((m for m in map_rows if m["set"] == "FL+FR+RL+RR"), key=lambda m: m["Ms_max"])
worst_four_rho = max((m for m in map_rows if m["set"] == "FL+FR+RL+RR"), key=lambda m: m["rho_excl"])
worst_pair = max((m for m in map_rows if m["set"] == "FL+FR"), key=lambda m: m["Ms_max"])
cases = [("nominal", summ["nominal"]["plant"], None), ("nominal", summ["nominal"]["rho_plant"], None),
         ("single_RL", summ["single_RL"]["plant"], "s2"), ("single_RR", summ["single_RR"]["plant"], "s3"), ("single_FL", summ["single_FL"]["plant"], "s0"),
         (worst_pair["key"], worst_pair["plant"], worst_pair["key"]), (worst_pair["key"], worst_pair["rho_plant"], worst_pair["key"]),
         (worst_four_ms["key"], worst_four_ms["plant"], worst_four_ms["key"]), (worst_four_rho["key"], worst_four_rho["rho_plant"], worst_four_rho["key"]),
         (worst_four_ms["key"], worst_four_ms["rho_plant"], worst_four_ms["key"])]
out = []
for name, tag, ref in cases:
    lp = R.make_plant(by_tag[tag])
    if ref is None:
        Mu, Mf = np.eye(4), np.zeros((4, 4))
    elif ref.startswith("s") and ref[1:].isdigit():
        Mu, Mf = T.single_leg_structure(int(ref[1:]))
    else:
        Mu, Mf = np.array(set_def[ref]["Mu"]), np.array(set_def[ref]["Mf"])
    r = T.eval_loop(T.apply_structure(lp, Mu, Mf), n_grid=20000)
    out.append({"struct": name, "plant": tag, "A": lp.A.tolist(), "B": lp.B.tolist(), "C": lp.C.tolist(), "D": lp.D.tolist(),
                "i_pa": lp.idx("phi_acc") + 1, "i_ta": lp.idx("theta_acc") + 1, "i_clr": lp.idx("clr") + 1,
                "iP": [lp.idx(f"P_{nm}") + 1 for nm in dm.LEG_NAMES], "Amat": cc["A"].tolist(), "n": cc["n"].tolist(), "k_nom": cc["k_nom"],
                "Mu": Mu.tolist(), "Mf": Mf.tolist(),
                "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in T.CFG.__dict__.items()},
                "python": {c: r[c]["Ms"] for c in R.CH} | {"rho_excl": r["rho_excl"], "rho_all": r["rho_all"]}})
(HERE / "t4_export.json").write_text(json.dumps(out), encoding="utf-8")
print("export", len(out), [(o["struct"], o["plant"]) for o in out])
