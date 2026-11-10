"""Ideal-sensor diagnosis stage 1: path-2 independent re-count (plan section 8.8).

Written by control-expert. This script does NOT import any project module and does
NOT read the path-1 output. It re-derives, from the raw result files only:

  * row counts per bundle / variant / set and key coverage against the keys file
  * gates G-1 .. G-4 (stored reference hashes looked up in the original stored files)
  * metrics M-1 .. M-12 (pairs = same bundle, key, K1 arm, LAS candidate; SHD vs variant)
  * H-F detection metrics
  * truth value of every pre-registered direction prediction (plan 7.2), split into
    sub-items; the split and the reading of vague wording are listed in the output

There is no verdict grade (diagnosis only, plan 8.8).

Usage (dynamics-dev, read only):
  python -I ideal_stage1_path2.py --ideal-dir <v5/las/ideal> --stored-v5 <main v5 dir>
         --r64 <rev64/r64_g4_closed_loop.json> --out <path2.json>
"""
import argparse
import collections
import hashlib
import json
import math
import os
import statistics
import sys

F_MIN_KN = 9.415
STROKE_GUARD_MM = 682.8
FALSE_SOIL_DT_S = 0.05
TS = 0.1
VARIANTS = ("SHD", "IGA", "IGB", "IZ", "S4")
EXPECTED_KEYS_SHA = "fa313763afda066929317fdc32a58996eaf58601bc364869f6c2c41a689d8766"
P0_UNION_SETS = ("A_P0", "A_boundary_P0", "B", "C", "E", "F")
PRESSURE_NAMES = ("FAULT_HEAD_PRESSURE", "WARN_ROD_PRESSURE_FALLBACK", "INFO_PRESSURE_STEP",
                  "WARN_CRAWLER_RECONTACT_SUSPECTED", "INFO_ROD_PRESSURE_FAULT_REASON", "check_draining")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def list_sha(ids):
    return hashlib.sha256(("\n".join(sorted(ids)) + "\n").encode("utf-8")).hexdigest()


def read_jsonl(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def q(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "min": min(xs), "p10": q(xs, 0.1), "median": med(xs), "p90": q(xs, 0.9), "max": max(xs),
            "mean": sum(xs) / len(xs)}


# ----------------------------------------------------------------------------- row extraction

def strip_legs(name):
    parts = name.split(":")
    return ":".join(p for p in parts if p not in ("FL", "FR", "RL", "RR"))


def row_facts(r):
    d1 = r["d1"]
    v = r["values"]
    ev = v["events"]
    idl = r.get("ideal") or {}
    per = idl.get("periods") or {}
    t_lift = v["forces"]["t_lift_s"]
    t_loc = ev.get("t_loc_first_s")
    sms = idl.get("soil_mode_starts") or []
    t_S = sms[0]["t_s"] if sms else None
    ogd = idl.get("order_gate_decisions") or []
    fault_names = collections.Counter(strip_legs(x) for x in ev.get("fault_events") or [])
    en = r.get("event_names") or {}
    ev_list = collections.Counter(strip_legs(e[1]) for e in (r.get("events") or []))
    al = v["forces"].get("after_liftoff") or {}
    f = {
        "key": d1["key"],
        "group": d1["group"],
        "row_key": d1["row_key"],
        "setting": d1["setting"],
        "verdict": d1["verdict"],
        "fail_items": d1.get("fail_items") or [],
        "items": d1.get("items") or {},
        "t_ready": d1.get("t_ready_s"),
        "smax_mm": d1["stroke_max_m"] * 1000.0 if d1.get("stroke_max_m") is not None else None,
        "hash": r["commands_sha256"],
        "tag": r.get("controller_tag"),
        "t_lift": t_lift,
        "t_loc": t_loc,
        "t_S": t_S,
        "soil_mode_started": ev.get("soil_mode_started"),
        "loc_minus_lift": (t_loc - t_lift) if (t_loc is not None and t_lift is not None) else None,
        "false_loc": (t_loc is not None and t_lift is not None and t_loc < t_lift),
        "false_soil": (t_S is not None and t_lift is not None and t_S > t_lift + FALSE_SOIL_DT_S),
        "flag_false_loc": idl.get("false_loc"),
        "flag_false_soil": idl.get("false_soil_mode"),
        "n_ogd": len(ogd),
        "f2": bool(ogd) and bool(ogd[0].get("would_block")) and not idl.get("flat_soil_margin_applied"),
        "r4c30_applied": idl.get("flat_soil_margin_applied"),
        "e3c10_applied": idl.get("slope_margin_applied"),
        "revoked": int(en.get("INFO_LOC_REVOKED", 0)),
        "revokes_list": len(idl.get("loc_revokes") or []),
        "fault_names": dict(fault_names),
        "sgs_stop": sum(c for n, c in fault_names.items() if n.startswith("FAULT_LIFT_STROKE_LIMIT")),
        "min_after_lift_kN": al.get("min_kN"),
        "end_abs_deg": v["attitude"].get("end_abs_deg") or {},
        "event_names": dict(en),
        "events_list": dict(ev_list),
        "ideal_set": idl.get("set"),
        "bundle": idl.get("bundle"),
        "variant": idl.get("variant"),
        "k1_arm": idl.get("k1_arm"),
        "las": idl.get("las_candidate"),
        "base_tag": idl.get("base_tag"),
        "in_row_stored_hash": idl.get("stored_commands_sha256"),
        "disabled_margins": idl.get("disabled_margins"),
        "k1_gate_eff": idl.get("k1_order_gate_effective"),
    }
    # M-10 clearance error at LOC and at READY (c_min - g_box_min, g_min = min of g_box)
    ts = per.get("t_s") or []

    def at(t):
        if t is None or not ts:
            return None
        n = round(t / TS)
        best = None
        for i, tt in enumerate(ts):
            if round(tt / TS) == n:
                best = i
        return best

    def err(i, cname):
        if i is None:
            return None
        c = per.get(cname, [None] * len(ts))[i]
        gb = per.get("g_box", [None] * len(ts))[i]
        if c is None or gb is None:
            return None
        return (c - min(gb)) * 1000.0

    iL, iR = at(t_loc), at(f["t_ready"])
    f["m10_loc_c_mm"] = err(iL, "c_min")
    f["m10_loc_ccorr_mm"] = err(iL, "c_corr_min")
    f["m10_ready_c_mm"] = err(iR, "c_min")
    f["m10_ready_ccorr_mm"] = err(iR, "c_corr_min")
    # g_min consistency check (g_min == min(g_box))
    gm, gb = per.get("g_min") or [], per.get("g_box") or []
    f["gmin_box_maxdiff"] = max((abs(a - min(b)) for a, b in zip(gm, gb) if a is not None and b), default=0.0)
    # S4 alignment residual records: max |period-to-period change|
    for nm in ("r_bar_aligned", "r_inst"):
        xs = per.get(nm) or []
        ds = [abs(b - a) for a, b in zip(xs, xs[1:]) if a is not None and b is not None]
        f["max_d_" + nm] = max(ds) if ds else None
        f["std_d_" + nm] = statistics.pstdev([b - a for a, b in zip(xs, xs[1:]) if a is not None and b is not None]) if len(ds) > 1 else None
    return f


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ideal-dir", required=True)
    ap.add_argument("--stored-v5", required=True)
    ap.add_argument("--r64", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = a.ideal_dir
    out = {"schema": "ideal-stage1-path2/1", "script_sha256": sha_file(os.path.abspath(__file__)), "inputs": {}}

    # keys
    kp = os.path.join(D, "ideal_stage1_keys.json")
    out["inputs"]["ideal_stage1_keys.json"] = sha_file(kp)
    K = json.load(open(kp, encoding="utf-8"))
    sets = {n: list(s["keys"]) for n, s in K["sets"].items()}
    key_checks = {"file_sha_ok": out["inputs"]["ideal_stage1_keys.json"] == EXPECTED_KEYS_SHA}
    for n, s in K["sets"].items():
        key_checks[n] = {"n": len(s["keys"]), "n_ok": len(s["keys"]) == s["n"], "sha_ok": list_sha(s["keys"]) == s["sha256"]}
    union = []
    for n in P0_UNION_SETS:
        union += sets[n]
    key_checks["P0_union_n"] = len(set(union))
    key_checks["P0_union_disjoint"] = len(union) == len(set(union))
    if "P0_union" in K["sets"]:
        pass
    out["key_checks"] = key_checks
    set_of = {}
    for n in P0_UNION_SETS:
        for k in sets[n]:
            set_of[k] = n

    # ideal rows
    files = {}
    rows = []
    for b in ("I0", "I1", "I1k", "I1p"):
        for v in VARIANTS:
            p = os.path.join(D, f"ideal_{b}_{v}.jsonl")
            if not os.path.exists(p):
                continue
            files[os.path.basename(p)] = sha_file(p)
            for r in read_jsonl(p):
                f = row_facts(r)
                f["file_bundle"] = b
                f["file_variant"] = v
                rows.append(f)
    out["inputs"].update(files)
    cnt = collections.Counter((f["file_bundle"], f["file_variant"]) for f in rows)
    out["counts"] = {f"{b}/{v}": n for (b, v), n in sorted(cnt.items())}
    out["counts_total_jsonl"] = len(rows)

    # integrity of labels
    integ = collections.Counter()
    for f in rows:
        if f["variant"] != f["file_variant"]:
            integ["variant_mismatch"] += 1
        if not (f["tag"] or "").endswith("_IDEAL-" + f["file_variant"]):
            integ["tag_suffix_bad"] += 1
        if f["tag"] != f"{f['base_tag']}_IDEAL-{f['file_variant']}":
            integ["tag_not_base_plus_variant"] += 1
        exp_set = set_of.get(f["key"]) if f["las"] == "P0" else ("A_P5r4" if f["key"] in sets["A_P5r4"] else None)
        if f["file_bundle"] == "I1p":
            exp_set = "A_P5r4"
        if f["ideal_set"] != exp_set:
            integ["set_label_mismatch"] += 1
        if f["gmin_box_maxdiff"] > 1e-12:
            integ["g_min_ne_min_g_box"] += 1
        if f["k1_gate_eff"] != (f["k1_arm"] == "on"):
            integ["k1_gate_effective_mismatch"] += 1
        if f["revoked"] != f["revokes_list"]:
            integ["revoke_count_mismatch_event_vs_list"] += 1
        if f["flag_false_loc"] != f["false_loc"]:
            integ["false_loc_flag_ne_time_rule"] += 1
        if f["flag_false_soil"] != f["false_soil"]:
            integ["false_soil_flag_ne_time_rule"] += 1
    out["label_integrity"] = dict(integ)

    # coverage: I-1 each variant must be exactly the P0 union
    cov = {}
    for v in VARIANTS:
        ks = [f["key"] for f in rows if f["file_bundle"] == "I1" and f["file_variant"] == v]
        cov[f"I1/{v}"] = {"n": len(ks), "unique": len(set(ks)), "equals_P0_union": set(ks) == set(union)}
    i0 = [f["key"] for f in rows if f["file_bundle"] == "I0"]
    exp_i0 = sets["A_P0"] + sets["A_boundary_P0"] + sets["F"][:4] + sets["E"][:4]
    cov["I0"] = {"n": len(i0), "equals_plan_selection": sorted(i0) == sorted(exp_i0)}
    for b, exp in (("I1k", sets["A_P0"] + sets["A_boundary_P0"]), ("I1p", sets["A_P5r4"])):
        for v in ("SHD", "IGA", "IGB", "IZ"):
            ks = [(f["key"], f["k1_arm"]) for f in rows if f["file_bundle"] == b and f["file_variant"] == v]
            arms = sorted(set(x[1] for x in ks))
            cov[f"{b}/{v}"] = {"n": len(ks), "keys_ok": set(x[0] for x in ks) == set(exp), "arms": arms}
    out["coverage"] = cov

    # bundle totals vs registered document
    hf = json.load(open(os.path.join(D, "ideal_HF.json"), encoding="utf-8"))
    out["inputs"]["ideal_HF.json"] = sha_file(os.path.join(D, "ideal_HF.json"))
    n_hf = len(hf["rows"])
    tot = {"I-0": cov["I0"]["n"], "I-1": sum(cov[f"I1/{v}"]["n"] for v in VARIANTS),
           "I-1k": sum(cov[f"I1k/{v}"]["n"] for v in ("SHD", "IGA", "IGB", "IZ")),
           "I-1p": sum(cov[f"I1p/{v}"]["n"] for v in ("SHD", "IGA", "IGB", "IZ")), "H-F": n_hf}
    tot["sum"] = sum(tot.values())
    tot["plan_table_says"] = {"subtotal": 859, "total": 873, "text": "859 + I-0 14 = 873"}
    tot["plan_rows_sum"] = 14 + 805 + 24 + 16 + 144
    out["bundle_totals"] = tot

    # ------------------------------------------------------------------ G-1 stored references
    V5 = a.stored_v5
    ref = {}

    def index(path, pred):
        out["inputs"][os.path.relpath(path, V5)] = sha_file(path)
        idx = collections.defaultdict(set)
        for r in read_jsonl(path):
            d1 = r.get("d1")
            if not d1 or not d1.get("key"):
                continue
            if pred(r):
                idx[d1["key"]].add(r["commands_sha256"])
        return idx

    lab = lambda L: (lambda r: (r.get("rev") or {}).get("label") == L)
    ref["Y-Pa"] = index(os.path.join(V5, "las", "k1", "k1_YP.jsonl"), lab("P0-K1on"))
    ref["Y-Sb"] = index(os.path.join(V5, "las", "k1", "k1_YS.jsonl"), lab("P5r4-K1on"))
    ref["Y-0b"] = index(os.path.join(V5, "las", "k1", "k1_Y0.jsonl"), lab("P5r4-K1off"))
    ref["S-C"] = index(os.path.join(V5, "soil_defer", "s2d_SC.jsonl"), lambda r: (r.get("las") or {}).get("candidate") == "P0")
    t1 = index(os.path.join(V5, "las", "las_T1.jsonl"), lambda r: (r.get("las") or {}).get("candidate") == "b0")
    t2 = index(os.path.join(V5, "las", "las_T2.jsonl"), lambda r: (r.get("las") or {}).get("candidate") == "b0")
    lasT = collections.defaultdict(set)
    for idx in (t1, t2):
        for k, s in idx.items():
            lasT[k] |= s
    ref["las_T"] = lasT
    ambiguous = {n: sum(1 for s in idx.values() if len(s) > 1) for n, idx in ref.items()}

    def ref_name(f):
        if f["las"] == "P5r4":
            return "Y-Sb" if f["k1_arm"] == "on" else "Y-0b"
        if f["k1_arm"] == "off":
            return "S-C"
        s = set_of.get(f["key"])
        if s == "A_P0":
            return "Y-Pa"
        if s == "F":
            return "las_T"
        return "S-C"

    g1 = {"rows": 0, "same": 0, "missing_ref": [], "diff": [], "in_row_ref_disagrees": 0, "by_ref": collections.Counter(),
          "ambiguous_ref_keys": ambiguous}
    for f in rows:
        if f["file_variant"] != "SHD":
            continue
        g1["rows"] += 1
        rn = ref_name(f)
        hs = ref[rn].get(f["key"])
        g1["by_ref"][rn] += 1
        if not hs:
            g1["missing_ref"].append([f["file_bundle"], f["key"], f["k1_arm"], rn])
            continue
        if f["in_row_stored_hash"] not in hs:
            g1["in_row_ref_disagrees"] += 1
        if f["hash"] in hs:
            g1["same"] += 1
        else:
            g1["diff"].append([f["file_bundle"], f["key"], f["k1_arm"], f["las"], rn])
    g1["by_ref"] = dict(g1["by_ref"])
    out["G1"] = g1

    # ------------------------------------------------------------------ pairing
    def pk(f):
        return (f["file_bundle"], f["key"], f["k1_arm"], f["las"])

    by = {v: {pk(f): f for f in rows if f["file_variant"] == v} for v in VARIANTS}
    for v in VARIANTS:
        n = sum(1 for f in rows if f["file_variant"] == v)
        if n != len(by[v]):
            out.setdefault("pairing_errors", []).append(f"duplicate pair key in {v}")

    # ------------------------------------------------------------------ G-2: IZ vs SHD on F (I-1)
    g2 = {"pairs": 0, "same": 0, "diff_keys": [], "by_group": {}}
    gg = collections.defaultdict(lambda: [0, 0])
    for k in sets["F"]:
        s, z = by["SHD"].get(("I1", k, "on", "P0")), by["IZ"].get(("I1", k, "on", "P0"))
        if not s or not z:
            continue
        g2["pairs"] += 1
        gg[s["group"]][0] += 1
        if s["hash"] == z["hash"]:
            g2["same"] += 1
            gg[s["group"]][1] += 1
        else:
            g2["diff_keys"].append(k)
    g2["by_group"] = {g: {"pairs": p, "same": n} for g, (p, n) in gg.items()}
    # what changed in the differing rigid pairs
    dd = []
    for k in g2["diff_keys"]:
        s, z = by["SHD"][("I1", k, "on", "P0")], by["IZ"][("I1", k, "on", "P0")]
        dd.append({"key": k, "verdict": [s["verdict"], z["verdict"]], "t_ready": [s["t_ready"], z["t_ready"]],
                   "smax_mm": [s["smax_mm"], z["smax_mm"]], "t_loc": [s["t_loc"], z["t_loc"]],
                   "events_only_in_IZ": sorted(set(z["event_names"]) - set(s["event_names"])),
                   "events_only_in_SHD": sorted(set(s["event_names"]) - set(z["event_names"]))})
    g2["diff_detail"] = dd
    # also all rigid rows (soil-free groups H-R-*) in I-1
    out["G2"] = g2

    # ------------------------------------------------------------------ G-3: IGA vs IGB on A_P0 + boundary
    g3 = {"pairs": 0, "same": 0, "diff": []}
    for b, arm in (("I1", "on"), ("I1k", "off")):
        for k in sets["A_P0"] + sets["A_boundary_P0"]:
            x, y = by["IGA"].get((b, k, arm, "P0")), by["IGB"].get((b, k, arm, "P0"))
            if not x or not y:
                continue
            g3["pairs"] += 1
            if x["hash"] == y["hash"]:
                g3["same"] += 1
            else:
                g3["diff"].append([b, k])
    out["G3"] = g3

    # ------------------------------------------------------------------ G-4
    def same_tuple(a_, b_):
        def eq(u, w):
            if isinstance(u, float) or isinstance(w, float):
                return u is not None and w is not None and abs(u - w) <= 1e-9
            if isinstance(u, list) and isinstance(w, list):
                return sorted(u) == sorted(w)
            return u == w
        return all(eq(a_.get(k), b_.get(k)) for k in set(a_) | set(b_))

    g4ii = {"rows": 0, "same": 0, "diff": []}
    for r in hf["rows"]:
        if r["arm"] != "base":
            continue
        g4ii["rows"] += 1
        o, c = r["g4_ii"]["old"], r["g4_ii"]["chunk"]
        if same_tuple(o, c):
            g4ii["same"] += 1
        else:
            g4ii["diff"].append([r["case"], r["phase_ms"], r["jump_bar"]])
        if bool(r["g4_ii"]["same"]) != same_tuple(o, c):
            g4ii.setdefault("flag_disagrees", 0)
            g4ii["flag_disagrees"] = g4ii.get("flag_disagrees", 0) + 1
    out["G4_ii"] = g4ii

    old = json.load(open(os.path.join(D, "ideal_HF_g4_old.json"), encoding="utf-8"))
    out["inputs"]["ideal_HF_g4_old.json"] = sha_file(os.path.join(D, "ideal_HF_g4_old.json"))
    st = json.load(open(a.r64, encoding="utf-8"))
    out["inputs"]["r64_g4_closed_loop.json"] = sha_file(a.r64)
    st_py = {(s["case"], round(s["off"], 4)): s for s in st["summary"] if s["var"] == "py"}
    g4i = {"rows": 0, "same": 0, "stored_copy_ok": 0, "diff_fields": collections.Counter(), "rows_detail": []}
    for c in old["comparison"]:
        g4i["rows"] += 1
        s = st_py.get((c["case"], round(c["offset_s"], 4)))
        if s is None:
            g4i["rows_detail"].append({"case": c["case"], "off": c["offset_s"], "error": "no stored row"})
            continue
        stored = {"t_f": s["t_f"], "fault": s["fault"], "targets": s["targets"]}
        if same_tuple(stored, c["stored"]):
            g4i["stored_copy_ok"] += 1
        new = c["new"]
        dfs = [k for k in ("t_f", "fault", "targets") if not same_tuple({k: new.get(k)}, {k: stored.get(k)})]
        for k in dfs:
            g4i["diff_fields"][k] += 1
        if not dfs:
            g4i["same"] += 1
        g4i["rows_detail"].append({"case": c["case"], "off": c["offset_s"], "new": new, "stored": stored,
                                   "stored_end": s.get("end"), "diff_fields": dfs})
    g4i["diff_fields"] = dict(g4i["diff_fields"])
    out["G4_i"] = g4i

    # ------------------------------------------------------------------ metrics per variant (paired with SHD)
    def pairs(v, bundle=None, setnames=None, arm=None):
        res = []
        for k_, f in by[v].items():
            b, key, k1a, las = k_
            if bundle and b not in bundle:
                continue
            if arm and k1a != arm:
                continue
            sname = f["ideal_set"]
            if setnames and sname not in setnames:
                continue
            s = by["SHD"].get(k_)
            if s is None:
                continue
            res.append((s, f))
        return res

    def metric_block(pp):
        m = {"pairs": len(pp)}
        m["M1_transitions"] = dict(collections.Counter(f"{s['verdict']}->{f['verdict']}" for s, f in pp))
        m["M1_changed"] = sum(1 for s, f in pp if s["verdict"] != f["verdict"])
        m["hash_same"] = sum(1 for s, f in pp if s["hash"] == f["hash"])
        dr = [f["t_ready"] - s["t_ready"] for s, f in pp if s["t_ready"] is not None and f["t_ready"] is not None]
        m["M2_dt_ready_s"] = summ(dr)
        m["M2_ready_lost"] = sum(1 for s, f in pp if s["t_ready"] is not None and f["t_ready"] is None)
        m["M2_ready_gained"] = sum(1 for s, f in pp if s["t_ready"] is None and f["t_ready"] is not None)
        m["M2_abs_le_2s"] = sum(1 for x in dr if abs(x) <= 2.0)
        fn_s, fn_v = collections.Counter(), collections.Counter()
        for s, f in pp:
            fn_s.update(s["fault_names"])
            fn_v.update(f["fault_names"])
        m["M3_fault_names"] = {"SHD": dict(fn_s), "var": dict(fn_v)}
        m["M3_sgs_rows"] = {"SHD": sum(1 for s, _ in pp if s["sgs_stop"]), "var": sum(1 for _, f in pp if f["sgs_stop"])}
        m["M3_allowed_stop_rows"] = {"SHD": sum(1 for s, _ in pp if s["verdict"] == "allowed_stop"),
                                     "var": sum(1 for _, f in pp if f["verdict"] == "allowed_stop")}
        m["M4_margin_mm"] = {"SHD": summ([STROKE_GUARD_MM - s["smax_mm"] for s, _ in pp]),
                             "var": summ([STROKE_GUARD_MM - f["smax_mm"] for _, f in pp])}
        m["M4_dsmax_mm"] = summ([f["smax_mm"] - s["smax_mm"] for s, f in pp])
        m["M5_min_minus_Fmin_kN"] = {"SHD": summ([s["min_after_lift_kN"] - F_MIN_KN for s, _ in pp if s["min_after_lift_kN"] is not None]),
                                     "var": summ([f["min_after_lift_kN"] - F_MIN_KN for _, f in pp if f["min_after_lift_kN"] is not None])}
        m["M5_delta_kN"] = summ([f["min_after_lift_kN"] - s["min_after_lift_kN"] for s, f in pp
                                 if f["min_after_lift_kN"] is not None and s["min_after_lift_kN"] is not None])
        for it in ("P3-1", "P3-5"):
            m["M6_" + it] = {"SHD_true": sum(1 for s, _ in pp if s["items"].get(it)),
                             "var_true": sum(1 for _, f in pp if f["items"].get(it)),
                             "false_to_true": sum(1 for s, f in pp if not s["items"].get(it) and f["items"].get(it)),
                             "true_to_false": sum(1 for s, f in pp if s["items"].get(it) and not f["items"].get(it))}
        m["M7_loc_minus_lift_s"] = {"SHD": summ([s["loc_minus_lift"] for s, _ in pp]),
                                    "var": summ([f["loc_minus_lift"] for _, f in pp])}
        m["M8"] = {"false_loc": {"SHD": sum(s["false_loc"] for s, _ in pp), "var": sum(f["false_loc"] for _, f in pp)},
                   "false_soil": {"SHD": sum(s["false_soil"] for s, _ in pp), "var": sum(f["false_soil"] for _, f in pp)},
                   "soil_mode": {"SHD": sum(1 for s, _ in pp if s["t_S"] is not None),
                                 "var": sum(1 for _, f in pp if f["t_S"] is not None)}}
        m["M9"] = {"revoked_events": {"SHD": sum(s["revoked"] for s, _ in pp), "var": sum(f["revoked"] for _, f in pp)},
                   "revoked_rows": {"SHD": sum(1 for s, _ in pp if s["revoked"]), "var": sum(1 for _, f in pp if f["revoked"])},
                   "F2_rows": {"SHD": sum(s["f2"] for s, _ in pp), "var": sum(f["f2"] for _, f in pp)},
                   "R4c30_applied_rows": {"SHD": sum(1 for s, _ in pp if s["r4c30_applied"]),
                                          "var": sum(1 for _, f in pp if f["r4c30_applied"])},
                   "E3c10_applied_rows": {"SHD": sum(1 for s, _ in pp if s["e3c10_applied"]),
                                          "var": sum(1 for _, f in pp if f["e3c10_applied"])},
                   "order_gate_rows": {"SHD": sum(1 for s, _ in pp if s["n_ogd"]), "var": sum(1 for _, f in pp if f["n_ogd"])}}
        m["M10_SHD_mm"] = {k: summ([s[k] for s, _ in pp]) for k in
                           ("m10_loc_c_mm", "m10_loc_ccorr_mm", "m10_ready_c_mm", "m10_ready_ccorr_mm")}
        pc_s, pc_v = collections.Counter(), collections.Counter()
        for s, f in pp:
            for nm in PRESSURE_NAMES:
                pc_s[nm] += sum(c for n, c in s["events_list"].items() if n.startswith(nm)) or \
                    sum(1 for n in s["event_names"] if n.startswith(nm))
                pc_v[nm] += sum(c for n, c in f["events_list"].items() if n.startswith(nm)) or \
                    sum(1 for n in f["event_names"] if n.startswith(nm))
        m["M11_pressure_events"] = {"SHD": dict(pc_s), "var": dict(pc_v),
                                    "rows_SHD": {nm: sum(1 for s, _ in pp if any(n.startswith(nm) for n in s["event_names"])) for nm in PRESSURE_NAMES},
                                    "rows_var": {nm: sum(1 for _, f in pp if any(n.startswith(nm) for n in f["event_names"])) for nm in PRESSURE_NAMES}}
        m["M12_end_deg"] = {"SHD_roll": summ([s["end_abs_deg"].get("roll") for s, _ in pp]),
                            "SHD_pitch": summ([s["end_abs_deg"].get("pitch") for s, _ in pp]),
                            "var_roll": summ([f["end_abs_deg"].get("roll") for _, f in pp]),
                            "var_pitch": summ([f["end_abs_deg"].get("pitch") for _, f in pp]),
                            "var_gt_0p03_rows": sum(1 for _, f in pp if max(f["end_abs_deg"].get("roll") or 0, f["end_abs_deg"].get("pitch") or 0) > 0.03),
                            "SHD_gt_0p03_rows": sum(1 for s, _ in pp if max(s["end_abs_deg"].get("roll") or 0, s["end_abs_deg"].get("pitch") or 0) > 0.03)}
        m["changed_verdict_rows"] = [{"key": f["key"], "arm": f["k1_arm"], "las": f["las"], "set": f["ideal_set"],
                                      "SHD": s["verdict"], "var": f["verdict"], "var_fail_items": f["fail_items"],
                                      "SHD_fail_items": s["fail_items"], "dsmax_mm": f["smax_mm"] - s["smax_mm"],
                                      "fault_var": f["fault_names"], "t_ready": [s["t_ready"], f["t_ready"]]}
                                     for s, f in pp if s["verdict"] != f["verdict"]]
        return m

    metrics = {}
    setlist = list(P0_UNION_SETS)
    for v in VARIANTS:
        if v == "SHD":
            continue
        metrics[v] = {"I1_all": metric_block(pairs(v, bundle=("I1",)))}
        for sname in setlist:
            metrics[v]["I1_" + sname] = metric_block(pairs(v, bundle=("I1",), setnames=(sname,)))
        if v != "S4":
            metrics[v]["I1k_all"] = metric_block(pairs(v, bundle=("I1k",)))
            metrics[v]["I1p_on"] = metric_block(pairs(v, bundle=("I1p",), arm="on"))
            metrics[v]["I1p_off"] = metric_block(pairs(v, bundle=("I1p",), arm="off"))
    # SHD-only descriptive (I-1)
    shd1 = [f for k_, f in by["SHD"].items() if k_[0] == "I1"]
    metrics["SHD_I1"] = {"rows": len(shd1),
                         "verdicts": dict(collections.Counter(f["verdict"] for f in shd1)),
                         "false_loc": sum(f["false_loc"] for f in shd1), "false_soil": sum(f["false_soil"] for f in shd1),
                         "M7": summ([f["loc_minus_lift"] for f in shd1]),
                         "M10": {k: summ([f[k] for f in shd1]) for k in ("m10_loc_c_mm", "m10_ready_c_mm")}}
    out["metrics"] = metrics

    # K1 off vs on per variant (P-A4)
    a4 = {}
    for v in ("SHD", "IGA", "IGB", "IZ"):
        n = same = 0
        for k in sets["A_P0"] + sets["A_boundary_P0"]:
            x, y = by[v].get(("I1", k, "on", "P0")), by[v].get(("I1k", k, "off", "P0"))
            if x and y:
                n += 1
                same += x["hash"] == y["hash"]
        a4[v] = {"pairs": n, "same": same}
    p5 = {}
    for v in ("SHD", "IGA", "IGB", "IZ"):
        n = same = 0
        for k in sets["A_P5r4"]:
            x, y = by[v].get(("I1p", k, "on", "P5r4")), by[v].get(("I1p", k, "off", "P5r4"))
            if x and y:
                n += 1
                same += x["hash"] == y["hash"]
        p5[v] = {"pairs": n, "same": same}
    out["k1_off_vs_on"] = {"P0_A": a4, "P5r4": p5}

    # per-key detail for small sets
    detail = {}
    for sname in ("A_P0", "A_boundary_P0", "B"):
        rowsd = []
        for k in sets[sname]:
            ent = {"key": k}
            for v in ("SHD", "IGA", "IGB", "IZ", "S4"):
                f = by[v].get(("I1", k, "on", "P0"))
                if f:
                    ent[v] = {"verdict": f["verdict"], "smax_mm": f["smax_mm"], "t_ready": f["t_ready"], "t_S": f["t_S"],
                              "t_loc": f["t_loc"], "t_lift": f["t_lift"], "false_loc": f["false_loc"],
                              "false_soil": f["false_soil"], "P3-1": f["items"].get("P3-1"), "n_ogd": f["n_ogd"],
                              "faults": f["fault_names"], "revoked": f["revoked"], "hash": f["hash"][:12]}
            rowsd.append(ent)
        detail[sname] = rowsd
    out["detail"] = detail

    # ------------------------------------------------------------------ H-F
    hrows = hf["rows"]
    base = {(r["case"], r["phase_ms"], r["jump_bar"]): r for r in hrows if r["arm"] == "base"}
    hfm = {}
    for arm in ("base", "S4"):
        for J in (150.0, 250.0):
            for ph in (1, 20, 33, 50, 67, 90):
                rs = [r for r in hrows if r["arm"] == arm and float(r["jump_bar"]) == J and r["phase_ms"] == ph]
                ent = {"n": len(rs), "missed": sum(1 for r in rs if r["missed"] or r.get("head_fault_period") is None),
                       "delay_vs_arm": dict(collections.Counter(str(r.get("delay_periods")) for r in rs)),
                       "reasons": dict(collections.Counter(strip_legs(x) for r in rs for x in r.get("fault_reasons") or [])),
                       "G4_4_false": sum(1 for r in rs if not (r.get("judge") or {}).get("G4_4"))}
                dvb = []
                for r in rs:
                    b_ = base[(r["case"], r["phase_ms"], r["jump_bar"])]
                    if r.get("head_fault_period") is not None and b_.get("head_fault_period") is not None:
                        dvb.append(r["head_fault_period"] - b_["head_fault_period"])
                    else:
                        dvb.append(None)
                ent["delay_vs_base"] = dict(collections.Counter(str(x) for x in dvb))
                hfm[f"{arm}|J{int(J)}|phi{ph}"] = ent
    # G4-x changes S4 vs base
    g4chg = collections.Counter()
    g44 = []
    for r in hrows:
        if r["arm"] != "S4":
            continue
        b_ = base[(r["case"], r["phase_ms"], r["jump_bar"])]
        for g in ("G4_1", "G4_2", "G4_3", "G4_4", "G4_4_mean05", "G4_5", "G4_6"):
            if (r.get("judge") or {}).get(g) != (b_.get("judge") or {}).get(g):
                g4chg[g] += 1
        fm_s = (r.get("judge") or {}).get("final_min_kN_all")
        fm_b = (b_.get("judge") or {}).get("final_min_kN_all")
        if fm_s is not None and fm_b is not None:
            g44.append(fm_s - fm_b)
    hfm["S4_vs_base_G4_changes"] = dict(g4chg)
    hfm["S4_minus_base_final_min_kN"] = summ(g44)
    hfm["base_missed_total"] = sum(1 for r in hrows if r["arm"] == "base" and r["missed"])
    hfm["S4_missed_total"] = sum(1 for r in hrows if r["arm"] == "S4" and r["missed"])
    hfm["S4_missed_rows"] = [[r["case"], r["phase_ms"], r["jump_bar"], r.get("t_head_fault_rel_s"), (r.get("judge") or {}).get("G4_4"),
                              r.get("fault_reasons")] for r in hrows if r["arm"] == "S4" and r["missed"]]
    out["HF"] = hfm

    # ------------------------------------------------------------------ predictions (plan 7.2)
    P = {}
    M = metrics

    def put(pid, truth, value, note=""):
        P[pid] = {"truth": truth, "value": value, "reading": note}

    A = sets["A_P0"]
    for v in ("IGA", "IGB"):
        ok = [(by[v][("I1", k, "on", "P0")]["t_S"] is None and by[v][("I1", k, "on", "P0")]["n_ogd"] == 0) for k in A]
        put(f"P-A1/{v}", all(ok), f"{sum(ok)}/5 no soil mode and no order-gate decision")
    fs = [by["IZ"][("I1", k, "on", "P0")]["false_soil"] for k in A]
    put("P-A1/IZ", (5 - sum(fs)) >= 3, f"false soil mode removed in {5 - sum(fs)}/5 (SHD false soil {sum(by['SHD'][('I1', k, 'on', 'P0')]['false_soil'] for k in A)}/5)")
    same = sum(by["IGA"][("I1", k, "on", "P0")]["hash"] == by["IGB"][("I1", k, "on", "P0")]["hash"] for k in A)
    put("P-A2", same == 5, f"IGA==IGB hash {same}/5 (A_P0, K1 on)")
    ds = [by["IGA"][("I1", k, "on", "P0")]["smax_mm"] - by["SHD"][("I1", k, "on", "P0")]["smax_mm"] for k in A]
    put("P-A3", all(0.0 <= x <= 15.0 for x in ds), {"dsmax_mm": ds, "median": med(ds)},
        "truth = every pair in [0, +15] mm; 'median about +9 mm' reported, not scored")
    for v in ("IGA", "IGB", "IZ"):
        put(f"P-A4/{v}", a4[v]["same"] == a4[v]["pairs"] and a4[v]["pairs"] == 6, f"K1 off==on hash {a4[v]['same']}/{a4[v]['pairs']}")
    sc_ok = sum(1 for f in rows if f["file_bundle"] == "I1k" and f["file_variant"] == "SHD" and f["hash"] in ref["S-C"].get(f["key"], set()))
    put("P-A4/SHD", sc_ok == 6, f"SHD K1-off == S-C hash {sc_ok}/6")
    Bk = sets["B"]
    for v in ("IGA", "IGB"):
        fl = [by[v][("I1", k, "on", "P0")]["false_loc"] for k in Bk]
        lm = [by[v][("I1", k, "on", "P0")]["loc_minus_lift"] for k in Bk]
        put(f"P-B1/{v}/false_loc", sum(fl) == 0, f"false LOC {sum(fl)}/8")
        put(f"P-B1/{v}/window", all(x is not None and 0.1 - 1e-9 <= x <= 0.3 + 1e-9 for x in lm),
            {"loc_minus_lift_s": lm})
        roll = [k for k in Bk if "|J2|" in k and "roll+rec" in k]
        rec = sum(1 for k in roll if not by["SHD"][("I1", k, "on", "P0")]["items"].get("P3-1") and by[v][("I1", k, "on", "P0")]["items"].get("P3-1"))
        diag = [k for k in Bk if "|J2|" in k and "diag-rec" in k]
        st_ = sum(1 for k in diag if by[v][("I1", k, "on", "P0")]["verdict"] == "allowed_stop")
        put(f"P-B2/{v}/roll_P3-1", rec >= 2, f"P3-1 recovered {rec}/{len(roll)} (J2 roll+rec)")
        put(f"P-B2/{v}/diag_stop", st_ >= 1, f"allowed_stop remaining {st_}/{len(diag)} (J2 diag-rec)",
            "'diag-rec 2 rows' read as the two J2 T diag-rec keys")
    fl = sum(by["IZ"][("I1", k, "on", "P0")]["false_loc"] for k in Bk)
    put("P-B3", fl == 8, f"IZ false LOC {fl}/8")
    Ck = sets["C"]

    def cset(v):
        d = [by[v][("I1", k, "on", "P0")]["smax_mm"] - by["SHD"][("I1", k, "on", "P0")]["smax_mm"] for k in Ck]
        sg_s = sum(1 for k in Ck if by["SHD"][("I1", k, "on", "P0")]["sgs_stop"])
        sg_v = sum(1 for k in Ck if by[v][("I1", k, "on", "P0")]["sgs_stop"])
        return d, sg_s, sg_v

    for v in ("IGA", "IZ"):
        d, a_, b_ = cset(v)
        put(f"P-C1/{v}/smax", 3.0 <= med(d) <= 12.0, {"median_dsmax_mm": med(d), "p10": q(d, .1), "p90": q(d, .9)})
        put(f"P-C1/{v}/sgs", b_ >= a_, f"SGS stop rows SHD {a_} -> {v} {b_}")
    d, a_, b_ = cset("IGB")
    put("P-C2/IGB/smax", -25.0 <= med(d) <= -10.0, {"median_dsmax_mm": med(d), "p10": q(d, .1), "p90": q(d, .9)})
    put("P-C2/IGB/sgs", b_ <= a_, f"SGS stop rows SHD {a_} -> IGB {b_}")
    fd = [k for k in Ck if "|J2|" in k and "fdown" in k]
    gone = sum(1 for k in fd if by["SHD"][("I1", k, "on", "P0")]["sgs_stop"] and not by["IGB"][("I1", k, "on", "P0")]["sgs_stop"])
    put("P-C2/IGB/J2fdown", gone >= 3, f"J2 fdown keys {len(fd)}: SGS stop removed {gone}; SHD stops {sum(1 for k in fd if by['SHD'][('I1', k, 'on', 'P0')]['sgs_stop'])}")
    for v in ("IGA", "IGB"):
        m7 = M[v]["I1_all"]["M7_loc_minus_lift_s"]
        put(f"P-L1/{v}", m7["var"]["median"] is not None and m7["var"]["median"] <= 0.3,
            {"SHD_median": m7["SHD"]["median"], "var_median": m7["var"]["median"]}, "'all' = I-1 161 pairs (K1 on, P0)")
        m9 = M[v]["I1_all"]["M9"]
        put(f"P-L2/{v}", m9["revoked_events"]["var"] <= m9["revoked_events"]["SHD"] and m9["F2_rows"]["var"] <= m9["F2_rows"]["SHD"],
            {"revoked": m9["revoked_events"], "F2": m9["F2_rows"]}, "F2 = first order-gate decision would_block and R4c30 never applied")
    for v in ("IGA", "IGB", "IZ"):
        pp = pairs(v, bundle=("I1",), setnames=("E", "F"))
        newfail = sum(1 for s, f in pp if s["verdict"] != "fail" and f["verdict"] == "fail")
        both = [(s, f) for s, f in pp if s["t_ready"] is not None and f["t_ready"] is not None]
        le2 = sum(1 for s, f in both if abs(f["t_ready"] - s["t_ready"]) <= 2.0)
        put(f"P-E1/{v}", newfail <= 1 and le2 >= 0.9 * len(pp),
            {"pairs": len(pp), "new_fail": newfail, "abs_dready_le_2s": le2, "both_ready": len(both)},
            "|dREADY| share uses all 80 pairs as denominator")
    put("P-F1", g2["same"] == g2["pairs"] == 40, f"IZ==SHD hash {g2['same']}/{g2['pairs']}")
    m = M["S4"]["I1_all"]
    put("P-S1/hash", (m["pairs"] - m["hash_same"]) >= 150, f"hash changed {m['pairs'] - m['hash_same']}/{m['pairs']}")
    put("P-S1/verdict", m["M1_changed"] <= 3, f"verdict changed {m['M1_changed']}/{m['pairs']}")
    put("P-S1/lowerbound_jitter", None, "not recorded (no per-period lower-bound estimate in records)")
    ps = m["M11_pressure_events"]
    put("P-S2/step", None if ps["SHD"].get("INFO_PRESSURE_STEP", 0) == 0 else ps["var"].get("INFO_PRESSURE_STEP", 0) < ps["SHD"].get("INFO_PRESSURE_STEP", 0),
        f"INFO_PRESSURE_STEP SHD {ps['SHD'].get('INFO_PRESSURE_STEP', 0)} -> S4 {ps['var'].get('INFO_PRESSURE_STEP', 0)}",
        "undecidable when SHD count is 0 (cannot decrease)")
    put("P-S2/rod_fallback", ps["var"].get("WARN_ROD_PRESSURE_FALLBACK", 0) >= ps["SHD"].get("WARN_ROD_PRESSURE_FALLBACK", 0),
        f"WARN_ROD_PRESSURE_FALLBACK SHD {ps['SHD'].get('WARN_ROD_PRESSURE_FALLBACK', 0)} -> S4 {ps['var'].get('WARN_ROD_PRESSURE_FALLBACK', 0)} (events), rows {ps['rows_SHD'].get('WARN_ROD_PRESSURE_FALLBACK')} -> {ps['rows_var'].get('WARN_ROD_PRESSURE_FALLBACK')}")
    put("P-S3/head_fault", ps["var"].get("FAULT_HEAD_PRESSURE", 0) >= 1,
        f"FAULT_HEAD_PRESSURE in S4 rows: {ps['var'].get('FAULT_HEAD_PRESSURE', 0)}", "'can occur in >= 1 row' scored as occurred")
    s4rows = [f for k_, f in by["S4"].items() if k_[0] == "I1"]
    rb = [f["max_d_r_bar_aligned"] for f in s4rows if f["max_d_r_bar_aligned"] is not None]
    ri = [f["max_d_r_inst"] for f in s4rows if f["max_d_r_inst"] is not None]
    smaller = sum(1 for f in s4rows if f["max_d_r_bar_aligned"] is not None and f["max_d_r_inst"] is not None
                  and f["max_d_r_bar_aligned"] < f["max_d_r_inst"])
    put("P-S3/residual", smaller == len(s4rows) if s4rows else None,
        {"rows_rbar_smaller": smaller, "rows": len(s4rows), "median_max_d_rbar_N": med(rb), "median_max_d_rinst_N": med(ri)},
        "proxy: max |period-to-period change| of r_bar_aligned vs r_inst per S4 row (normalisation by |dp_h| A_p not recorded)")
    H = hfm
    put("P-H1/phi50", H["S4|J150|phi50"]["missed"] == 6, f"S4 J150 phi50 missed {H['S4|J150|phi50']['missed']}/6")
    e1 = H["S4|J150|phi1"]["delay_vs_base"]
    e20 = H["S4|J150|phi20"]["delay_vs_base"]
    put("P-H1/phi_le20", e1 == {"0": 6} and e20 == {"0": 6}, {"phi1": e1, "phi20": e20})
    put("P-H1/phi90", H["S4|J150|phi90"]["delay_vs_base"] == {"1": 6}, {"phi90": H["S4|J150|phi90"]["delay_vs_base"]})
    put("P-H2/all_caught", sum(H[f"S4|J250|phi{p}"]["missed"] for p in (1, 20, 33, 50, 67, 90)) == 0,
        f"S4 J250 missed {sum(H[f'S4|J250|phi{p}']['missed'] for p in (1, 20, 33, 50, 67, 90))}/36")
    put("P-H2/late_ge67", all(H[f"S4|J250|phi{p}"]["delay_vs_base"] == {"1": 6} for p in (67, 90)),
        {p: H[f"S4|J250|phi{p}"]["delay_vs_base"] for p in (67, 90)})
    # rev2 of this script (after run 1): P-H3 split; a missed row has no FAULT entry, so the
    # G4 judge is not evaluated (judge 'error: no fault entry') and G4-4 is undecidable.
    missed_rows = H["S4_missed_rows"]
    put("P-H3/late_or_never", None if not missed_rows else all(x[3] is None for x in missed_rows) or None,
        {"missed": len(missed_rows), "missed_with_no_head_fault_at_all": sum(1 for x in missed_rows if x[3] is None)},
        "truth = every missed row has no FAULT_HEAD_PRESSURE until the run end (the 'never' branch)")
    put("P-H3/G4-4_worse", None if all(x[4] is None for x in missed_rows) else any(x[4] is False for x in missed_rows),
        {"G4_4_values_on_missed_rows": sorted(set(str(x[4]) for x in missed_rows))},
        "undecidable when missed rows have no G4 evaluation (no fault entry)")
    out["predictions"] = P
    out["prediction_counts"] = {"true": sum(1 for p in P.values() if p["truth"] is True),
                                "false": sum(1 for p in P.values() if p["truth"] is False),
                                "undecided": sum(1 for p in P.values() if p["truth"] is None), "items": len(P)}

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({"status": "ok", "rows": len(rows), "G1": [g1["same"], g1["rows"]], "G2": [g2["same"], g2["pairs"]],
                      "G3": [g3["same"], g3["pairs"]], "G4_ii": [g4ii["same"], g4ii["rows"]], "G4_i": [g4i["same"], g4i["rows"]],
                      "pred": out["prediction_counts"]}))


if __name__ == "__main__":
    sys.exit(main())
