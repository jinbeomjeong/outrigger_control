"""Ideal-sensor stage 1: compare path-2 (ideal_stage1_path2.py) with the path-1 judge output.

Written by control-expert. Reads the raw jsonl again through path 2's own ``row_facts``
(no project module, no path-1 code) and compares every per-pair field and set total that
path 1 publishes, with tolerance 1e-9 (plan 8.8). Also compares gates and predictions.

Usage (dynamics-dev, read only):
  python -I ideal_stage1_path2_compare.py --ideal-dir <v5/las/ideal> --path1 <path1.json>
         --path2 <path2.json> --out <compare.json>
"""
import argparse
import collections
import importlib.util
import json
import os
import statistics
import sys

TOL = 1e-9
F_MIN_KN = 9.415
GUARD_MM = 682.8
VARS = ("SHD", "IGA", "IGB", "IZ", "S4")


def load_path2_module():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("p2", os.path.join(here, "ideal_stage1_path2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def num_eq(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))
    return a == b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ideal-dir", required=True)
    ap.add_argument("--path1", required=True)
    ap.add_argument("--path2", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    p2 = load_path2_module()
    P1 = json.load(open(a.path1, encoding="utf-8"))
    P2 = json.load(open(a.path2, encoding="utf-8"))
    out = {"script_sha256": p2.sha_file(os.path.abspath(__file__)),
           "path1_sha256": p2.sha_file(a.path1), "path2_sha256": p2.sha_file(a.path2)}

    bmap = {"I0": "I-0", "I1": "I-1", "I1k": "I-1k", "I1p": "I-1p"}
    facts, raw_phase = {}, {}
    for b in ("I1", "I1k", "I1p"):
        for v in VARS:
            p = os.path.join(a.ideal_dir, f"ideal_{b}_{v}.jsonl")
            if not os.path.exists(p):
                continue
            for r in p2.read_jsonl(p):
                f = p2.row_facts(r)
                k = (bmap[b], v, f["k1_arm"], f["key"])
                facts[k] = f
                raw_phase[k] = (r.get("final_phase"), r.get("harness_class"))

    # ---------------------------------------------------------------- per-pair fields
    def side(f):
        m10 = {"loc": (f["m10_loc_c_mm"], f["m10_loc_ccorr_mm"]), "ready": (f["m10_ready_c_mm"], f["m10_ready_ccorr_mm"])}
        return {
            "M-1": f["verdict"], "M-2": f["t_ready"], "s_max_mm": f["smax_mm"], "M-4_mm": GUARD_MM - f["smax_mm"],
            "M-5_kN": (f["min_after_lift_kN"] - F_MIN_KN) if f["min_after_lift_kN"] is not None else None,
            "M-6.P3-1": f["items"].get("P3-1"), "M-6.P3-5": f["items"].get("P3-5"),
            "M-7_s": f["loc_minus_lift"], "M-8.false_loc": f["false_loc"], "M-8.false_soil_mode": f["false_soil"],
            "M-8.false_soil_mode_ideal": f["flag_false_soil"], "M-8.soil_mode_started": f["soil_mode_started"],
            "M-9.revokes": f["revoked"], "M-9.f2": f["f2"], "M-10.loc.c": m10["loc"][0], "M-10.loc.ccorr": m10["loc"][1],
            "M-10.ready.c": m10["ready"][0], "M-10.ready.ccorr": m10["ready"][1],
            "M-12.roll": f["end_abs_deg"].get("roll"), "M-12.pitch": f["end_abs_deg"].get("pitch"),
            "sgs_stop": bool(f["sgs_stop"]), "commands_sha256": f["hash"], "r4_decisions": f["n_ogd"],
        }

    def p1side(s):
        m10 = s.get("M-10") or {}
        loc, rdy = m10.get("loc") or {}, m10.get("ready") or {}
        return {
            "M-1": s.get("M-1"), "M-2": s.get("M-2"), "s_max_mm": s.get("s_max_mm"), "M-4_mm": s.get("M-4_mm"),
            "M-5_kN": s.get("M-5_kN"), "M-6.P3-1": (s.get("M-6") or {}).get("P3-1"), "M-6.P3-5": (s.get("M-6") or {}).get("P3-5"),
            "M-7_s": s.get("M-7_s"), "M-8.false_loc": (s.get("M-8") or {}).get("false_loc"),
            "M-8.false_soil_mode": (s.get("M-8") or {}).get("false_soil_mode"),
            "M-8.false_soil_mode_ideal": (s.get("M-8") or {}).get("false_soil_mode_ideal"),
            "M-8.soil_mode_started": (s.get("M-8") or {}).get("soil_mode_started"),
            "M-9.revokes": (s.get("M-9") or {}).get("revokes"), "M-9.f2": (s.get("M-9") or {}).get("f2"),
            "M-10.loc.c": loc.get("c_minus_g_mm"), "M-10.loc.ccorr": loc.get("c_corr_minus_g_mm"),
            "M-10.ready.c": rdy.get("c_minus_g_mm"), "M-10.ready.ccorr": rdy.get("c_corr_minus_g_mm"),
            "M-12.roll": (s.get("M-12_deg") or [None, None])[0], "M-12.pitch": (s.get("M-12_deg") or [None, None])[1],
            "sgs_stop": s.get("sgs_stop"), "commands_sha256": s.get("commands_sha256"), "r4_decisions": s.get("r4_decisions"),
        }

    field_stats = collections.defaultdict(lambda: {"compared": 0, "equal": 0, "examples": []})
    m1_pattern = collections.Counter()
    missing = []
    maxdiff = collections.defaultdict(float)
    for pk, pr in P1["pairs"].items():
        bundle, var, arm, key = pk.split("|", 3)
        fv = facts.get((bundle, var, arm, key))
        fs = facts.get((bundle, "SHD", arm, key))
        if fv is None or fs is None:
            missing.append(pk)
            continue
        for role, mine_f, theirs in (("shd", fs, pr["shd"]), ("variant", fv, pr["variant"])):
            mine, th = side(mine_f), p1side(theirs)
            for fld in mine:
                st = field_stats[fld]
                st["compared"] += 1
                x, y = mine[fld], th[fld]
                if fld.startswith("M-6") or fld == "M-8.soil_mode_started":
                    ok = bool(x) == bool(y)  # missing item == false
                else:
                    ok = num_eq(x, y)
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
                    maxdiff[fld] = max(maxdiff[fld], abs(x - y))
                if ok:
                    st["equal"] += 1
                elif len(st["examples"]) < 4:
                    st["examples"].append([pk, role, x, y])
                if fld == "M-1" and not ok:
                    m1_pattern[(x, y, raw_phase[(bundle, var if role == 'variant' else 'SHD', arm, key)])] += 1
        # pair-level
        for fld, mine_v, th_v in (
                ("verdict_transition", f"{fs['verdict']}->{fv['verdict']}", pr.get("verdict_transition")),
                ("hash_equal", fs["hash"] == fv["hash"], pr.get("hash_equal")),
                ("dt_ready_s", (fv["t_ready"] - fs["t_ready"]) if (fv["t_ready"] is not None and fs["t_ready"] is not None) else None, pr.get("dt_ready_s")),
                ("ds_max_mm", fv["smax_mm"] - fs["smax_mm"], pr.get("ds_max_mm")),
                ("dF_kN", (fv["min_after_lift_kN"] - fs["min_after_lift_kN"]), pr.get("dF_kN"))):
            st = field_stats["pair." + fld]
            st["compared"] += 1
            if num_eq(mine_v, th_v):
                st["equal"] += 1
            elif len(st["examples"]) < 4:
                st["examples"].append([pk, mine_v, th_v])
    out["pairs"] = {"path1_pairs": len(P1["pairs"]), "missing_in_path2": missing,
                    "fields": {k: v for k, v in sorted(field_stats.items())},
                    "max_abs_diff_numeric": dict(maxdiff),
                    "M-1_mismatch_pattern(path2, path1, raw(final_phase, harness_class))": {str(k): n for k, n in m1_pattern.items()}}

    # ---------------------------------------------------------------- set totals
    st_cmp = {}
    for sk, t1 in P1["set_totals"].items():
        bundle, var, arm, sname = sk.split("|")
        pp = [(facts[(bundle, "SHD", arm, k)], f) for (b, v, ar, k), f in facts.items()
              if b == bundle and v == var and ar == arm and f["ideal_set"] == sname]
        mine = {
            "pairs": len(pp), "hash_equal": sum(1 for s, f in pp if s["hash"] == f["hash"]),
            "median_dt_ready_s": p2.med([f["t_ready"] - s["t_ready"] for s, f in pp if f["t_ready"] is not None and s["t_ready"] is not None]),
            "median_ds_max_mm": p2.med([f["smax_mm"] - s["smax_mm"] for s, f in pp]),
            "sgs_stops": {"shd": sum(1 for s, _ in pp if s["sgs_stop"]), "variant": sum(1 for _, f in pp if f["sgs_stop"])},
            "false_loc": {"shd": sum(s["false_loc"] for s, _ in pp), "variant": sum(f["false_loc"] for _, f in pp)},
            "false_soil_mode": {"shd": sum(s["false_soil"] for s, _ in pp), "variant": sum(f["false_soil"] for _, f in pp)},
            "median_M7_s": {"shd": p2.med([s["loc_minus_lift"] for s, _ in pp]), "variant": p2.med([f["loc_minus_lift"] for _, f in pp])},
            "revokes": {"shd": sum(s["revoked"] for s, _ in pp), "variant": sum(f["revoked"] for _, f in pp)},
            "f2": {"shd": sum(s["f2"] for s, _ in pp), "variant": sum(f["f2"] for _, f in pp)},
            "verdict_transitions": dict(collections.Counter(f"{s['verdict']}->{f['verdict']}" for s, f in pp)),
        }
        diffs = []
        for fld, mv in mine.items():
            tv = t1.get(fld)
            if isinstance(mv, dict) and isinstance(tv, dict) and fld != "verdict_transitions":
                ok = all(num_eq(mv.get(x), tv.get(x)) for x in set(mv) | set(tv))
            else:
                ok = num_eq(mv, tv) if fld != "verdict_transitions" else mv == tv
            if not ok:
                diffs.append([fld, mv, tv])
        st_cmp[sk] = diffs
    out["set_totals"] = {"groups": len(st_cmp), "groups_all_equal": sum(1 for d in st_cmp.values() if not d),
                         "field_mismatch_count": dict(collections.Counter(d[0] for ds in st_cmp.values() for d in ds)),
                         "non_M1_mismatches": {k: [d for d in v if d[0] != "verdict_transitions"] for k, v in st_cmp.items()
                                               if any(d[0] != "verdict_transitions" for d in v)}}

    # ---------------------------------------------------------------- gates
    g1 = P1["gates"]
    out["gates"] = {
        "G-1": {"path1": g1["G-1"], "path2": [P2["G1"]["same"], P2["G1"]["rows"]],
                "equal": g1["G-1"]["match_stored"] == P2["G1"]["same"] and g1["G-1"]["shd_lines"] == P2["G1"]["rows"]},
        "G-2": {"path1": g1["G-2"], "path2": [P2["G2"]["same"], P2["G2"]["pairs"]],
                "equal": g1["G-2"]["hash_equal"] == P2["G2"]["same"] and g1["G-2"]["pairs"] == P2["G2"]["pairs"]},
        "G-3": {"path1": g1["G-3"], "path2": [P2["G3"]["same"], P2["G3"]["pairs"]],
                "equal": g1["G-3"]["hash_equal"] == P2["G3"]["same"] and g1["G-3"]["pairs"] == P2["G3"]["pairs"]},
        "G-4ii": {"path1": g1["G-4"]["ii"], "path2": [P2["G4_ii"]["same"], P2["G4_ii"]["rows"]],
                  "equal": g1["G-4"]["ii"]["same"] == P2["G4_ii"]["same"] and g1["G-4"]["ii"]["rows"] == P2["G4_ii"]["rows"]},
        "G-4i": {"path1": g1["G-4"]["i"], "path2": [P2["G4_i"]["same"], P2["G4_i"]["rows"]],
                 "equal": g1["G-4"]["i"]["same"] == P2["G4_i"]["same"] and g1["G-4"]["i"]["rows"] == P2["G4_i"]["rows"]},
    }

    # ---------------------------------------------------------------- predictions: map path-2 sub-items to path-1 items
    pm = {
        "P-A1 IGA/IGB": ["P-A1/IGA", "P-A1/IGB"], "P-A1 IZ": ["P-A1/IZ"], "P-A2": ["P-A2"], "P-A3": ["P-A3"],
        "P-A4": ["P-A4/IGA", "P-A4/IGB", "P-A4/IZ", "P-A4/SHD"],
        "P-B1": ["P-B1/IGA/false_loc", "P-B1/IGA/window", "P-B1/IGB/false_loc", "P-B1/IGB/window"],
        "P-B2": ["P-B2/IGA/roll_P3-1", "P-B2/IGA/diag_stop", "P-B2/IGB/roll_P3-1", "P-B2/IGB/diag_stop"],
        "P-B3": ["P-B3"], "P-C1 IGA": ["P-C1/IGA/smax", "P-C1/IGA/sgs"], "P-C1 IZ": ["P-C1/IZ/smax", "P-C1/IZ/sgs"],
        "P-C2": ["P-C2/IGB/smax", "P-C2/IGB/sgs", "P-C2/IGB/J2fdown"], "P-L1 IGA": ["P-L1/IGA"], "P-L1 IGB": ["P-L1/IGB"],
        "P-L2 IGA": ["P-L2/IGA"], "P-L2 IGB": ["P-L2/IGB"], "P-E1 IGA": ["P-E1/IGA"], "P-E1 IGB": ["P-E1/IGB"],
        "P-E1 IZ": ["P-E1/IZ"], "P-F1": ["P-F1"], "P-S1": ["P-S1/hash", "P-S1/verdict", "P-S1/lowerbound_jitter"],
        "P-S2": ["P-S2/step", "P-S2/rod_fallback"], "P-S3": ["P-S3/head_fault", "P-S3/residual"],
        "P-H1": ["P-H1/phi50", "P-H1/phi_le20", "P-H1/phi90"], "P-H2": ["P-H2/all_caught", "P-H2/late_ge67"],
        "P-H3": ["P-H3/late_or_never", "P-H3/G4-4_worse"],
    }
    rows = []
    for p in P1["predictions"]:
        subs = pm.get(p["id"], [])
        sv = [P2["predictions"][s]["truth"] for s in subs if s in P2["predictions"]]
        decided = [x for x in sv if x is not None]
        agg = (all(decided) if decided else None)
        rows.append({"id": p["id"], "path1": p["holds"], "path2_subitems": dict(zip(subs, sv)), "path2_and_of_decided": agg,
                     "equal": agg == p["holds"]})
    out["predictions"] = rows
    out["predictions_equal"] = sum(1 for r in rows if r["equal"])
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({"status": "ok", "pairs_missing": len(missing),
                      "fields_not_all_equal": {k: [v["equal"], v["compared"]] for k, v in field_stats.items() if v["equal"] != v["compared"]},
                      "set_groups_equal": out["set_totals"]["groups_all_equal"], "gates_equal": {k: v["equal"] for k, v in out["gates"].items()},
                      "predictions_equal": [out["predictions_equal"], len(rows)]}, default=str))


if __name__ == "__main__":
    sys.exit(main())
