"""436.8 path 2: v5-criteria recount of the noise bundles H-6 (dg3 v4_on) and H-8 (noise VB / V0, seedext).

436.8 rev3 R3-E3 (Q-E3 = A) sets three layers; this tool does both kinds and lists them in TABLE_REAGG:

* recomputed from the record (``recomputed``): level counts and S1-front-excluded n (rev3 #1~#3, 423.1),
  one-sided Clopper-Pearson upper bounds by two roots (v5 10, rev3), L1 gate counts (false LOC,
  unmatched, errors, setting mismatch; v5 10), dg3 135-key substitution and hash record (rev8 #6,
  RV1-3.2), seedext seeds 0~4 hash (rev6 9, H-15), the time / load conditions of 419.8 for S-4 late LOC,
  J-P3 (rev8 3.2 / rev9 3.2 via ``p2_v5j.jp3``), J9 post-lift clip and H-7 n_late_fallback.
* re-aggregated from the recorded r79 gate results (``reaggregated``): per line the S-1~S-6 booleans of
  the r79 judge are the input (``--gates LABEL=<json>``); the grading rules are applied here
  independently: 13.2 / 419.8 (``S4_late_loc`` FLAG), 423.1 (S-4 recontact: only a new ``strict_fail``
  fails; G6-1 threshold chatter = FLAG), then the L2 fail count / CP grade, L3 record, seedext record.

Commands hash: top-level ``commands_sha256`` only (R3-E4); missing = ``기록 불완전`` (record, no stop).
The gate file layout is an input contract of this tool (README): ``{key: {"S-1": bool, ..., "S-6": bool,
"s4_reasons": [...]}}``, ``{key: {"gates": {...}, "s4_reasons": [...]}}``, or ``{"results": [{"key": ...,
...}]}``. ``s4_reasons`` items: ``time_clause`` (LOC - departure > T_lim), ``recontact_strict_new``,
``recontact_chatter``; any other text counts as a real S-4 fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402

TOOL_NAME = "p2v5c_noise.py"
TOOL_VERSION = "2"
LEVEL_COUNTS = {"L1": 167, "L2": 835, "L3": 501}      # rev3 #1
H6_COUNTS = {"L2": 1, "L3": 134}                      # rev8 #6
SEEDEXT_KEYS, SEEDEXT_SEEDS, SEEDEXT_CHECK = 2, 25, 5  # rev6 9 (seeds 0~4 checked)
M2_LAW = "flow_limited_r5"
S1_FRONT = ("S1@FL", "S1@FR")                          # 423.1 / v5 10 "S1 전방 제외"
CP_LIMIT = 0.03                                        # v5 10 L2
GATES = ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6")
T_LIM_S = 0.010 / (0.25 * 0.0209243016) + 1.0          # spec 11980: 2.91165 s
FALSE_LOC_W = 0.01                                      # 419.8 cond. 3 / P3-2 load clause
FISHER_P = 0.05                                         # rev6 9


def load(path):
    d = json.loads(Path(path).read_text("utf-8"))
    return d, {r.get("key"): r for r in d.get("results") or []}


def h(rec):
    """R3-E4: top-level ``commands_sha256`` only."""
    v = rec.get("commands_sha256") if isinstance(rec, dict) else None
    return v if isinstance(v, str) else None


def levels(recs):
    out = {}
    for r in recs.values():
        out[r.get("level")] = out.get(r.get("level"), 0) + 1
    return out


def s1_front(rec):
    return any(s in str(rec.get("inner", "")) for s in S1_FRONT)


def load_gates(path):
    d = json.loads(Path(path).read_text("utf-8"))
    if isinstance(d, dict) and isinstance(d.get("results"), list):
        d = {r.get("key"): r for r in d["results"]}
    elif isinstance(d, list):
        d = {r.get("key"): r for r in d}
    out = {}
    for k, e in d.items():
        g = e.get("gates") if isinstance(e.get("gates"), dict) else e
        out[k] = {"gates": {x: g.get(x) for x in GATES}, "s4_reasons": e.get("s4_reasons")}
    return out


# ----------------------------------------------------------------- 419.8 recompute (S-4 late LOC)
def late_loc_conditions(rec, core):
    """419.8 / 419.8.1 conditions 1~5 from the r79 record (None = record missing)."""
    r = rec.get("r79") or {}
    ev = [(float(e[0]), e[1]) for e in rec.get("events") or []
          if isinstance(e, (list, tuple)) and len(e) == 2 and isinstance(e[1], str)]
    t_off, t_loc = core.num(r.get("t_off_s")), core.num(r.get("t_loc_s"))
    if t_off is None or t_loc is None or not ev:
        return {"c1": None, "c2": None, "c3": None, "c4": None, "c5": None, "why": "t_off / t_loc / events missing"}
    # reapproach intervals: leg_reapproach_start:<leg> .. first contact / no-contact of that leg
    ivs = []
    for t, n in sorted(ev):
        if n.startswith("leg_reapproach_start:"):
            leg = n.split(":", 1)[1]
            end = next((t2 for t2, n2 in sorted(ev) if t2 >= t and (n2 == f"leg_reapproach_contact:{leg}"
                        or n2 == f"WARN_LEG_REAPPROACH_NO_CONTACT:{leg}")), None)
            ivs.append((t, end))
    over = [iv for iv in ivs if iv[0] <= t_loc + 1e-9 and (iv[1] is None or iv[1] >= t_off - 1e-9)]
    restart = [t for t, n in ev if n.startswith("INFO_LOC_WINDOW_RESTART")]
    c1 = any(any(a - 1e-9 <= t <= (b if b is not None else t_loc) + 1e-9 for t in restart) for a, b in over)
    if not over or any(b is None for _, b in over):
        c2 = False
    else:
        c2 = not core.t_gt(t_loc - max(t_off, max(b for _, b in over)), T_LIM_S)
    w = core.num(r.get("crawler_at_loc_over_W"))
    c3 = None if w is None else core.t_lt(w, FALSE_LOC_W)
    mf = core.num(r.get("min_true_F_after_off_kN"))
    faults = [n for _, n in ev if n.startswith("FAULT")]
    c4 = None if mf is None else (core.t_ge(mf, core.F_MIN_N / 1000.0) and not faults)
    done = [t for t, n in ev if n in ("first_done", "done", "phase:done", "DONE")]
    c5 = None if not done else t_loc < min(done)
    return {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "t_off_s": t_off, "t_loc_s": t_loc,
            "late_loc_s": t_loc - t_off}


def line_grade(key, rec, gates, core):
    """Re-aggregated line grade (pass / flag / fail / undecidable) and the flags."""
    if gates is None:
        return "undecidable", ["no gate record"], None
    g, reasons = gates["gates"], gates.get("s4_reasons")
    if any(not isinstance(g.get(x), bool) for x in GATES):
        return "undecidable", ["gate missing"], None
    flags, fail = [], [x for x in GATES if g[x] is False and x != "S-4"]
    cond = None
    if g["S-4"] is False:
        rs = set(reasons or [])
        if not rs:
            fail.append("S-4 (reason not recorded)")
        else:
            real = rs - {"time_clause", "recontact_chatter"}
            if "recontact_chatter" in rs:
                flags.append("S4_threshold_chatter")      # 423.1 / 423.3
            if "time_clause" in rs:
                cond = late_loc_conditions(rec, core)
                vals = [cond[c] for c in ("c1", "c2", "c3", "c4", "c5")]
                if all(v is True for v in vals):
                    flags.append("S4_late_loc")            # 13.2 / 419.8
                elif None in vals and False not in vals:
                    return "undecidable", ["419.8 record missing"], cond
                else:
                    fail.append("S-4 time clause (419.8 not met)")
            if real:
                fail.append(f"S-4 {sorted(real)}")
    if fail:
        return "fail", fail, cond
    return ("flag" if flags else "pass"), flags, cond


def run_checks(name, recs, core, v5j, is_p3, vb, fnd):
    jp = {}
    for k, r in recs.items():
        where = f"{name}|{k}"
        if vb:
            res, why = v5j.jp3(r, is_p3, True)   # R3-C8: two-pressure screen = rod reading
            jp[res] = jp.get(res, 0) + 1
            if res == "not_applicable_tag":
                fnd.undec(where, "J-P3 not applied (tag not ③ on)")
            elif res == "H-7":
                fnd.stop("H-7", where, f"J-P3 {why}")
            elif res == "setting_defect":
                fnd.stop("J-P3-defect", where, why)
        hr = r.get("hydraulics_record") or {}
        post = hr.get("m2_clipped_steps_post_lift")
        law = (r.get("hydraulic_options") or {}).get("m2_law")
        if vb:
            if law != M2_LAW:
                fnd.undec(where, f"m2_law {law!r} (rev6 #9)")
            if isinstance(post, list) and sum(post) > 0:
                fnd.stop("H-9", where, f"m2_clipped_steps_post_lift {post}")
        elif law is not None:
            fnd.undec(where, f"V0 run with m2_law {law!r}")
        nlf = core.dig(r, "lock_window_alignment.n_late_fallback", None)
        if isinstance(nlf, int) and nlf > 0:
            fnd.stop("H-7", where, f"n_late_fallback {nlf}")
    return jp


def cp_pair(k, n):
    return {"k": k, "n": n, "upper_beta": cm.cp_upper_beta(k, n), "upper_root": cm.cp_upper_root(k, n),
            "max_fail_at_3pct": cm.cp_max_fail(n)}


def l1_gate(meta, recs, expect_setting, core):
    """v5 10 L1 gate counts (recomputed). false LOC = r79.crawler_at_loc_over_W >= 0.01 (419.8 cond. 3)."""
    l1 = {(r.get("harness"), r.get("case_index"), r.get("inner")) for r in recs.values() if r.get("level") == "L1"}
    false_loc = [k for k, r in recs.items() if r.get("level") == "L1"
                 and core.num((r.get("r79") or {}).get("crawler_at_loc_over_W")) is not None
                 and not core.t_lt(core.num(r["r79"]["crawler_at_loc_over_W"]), FALSE_LOC_W)]
    unmatched = [k for k, r in recs.items() if r.get("level") in ("L2", "L3")
                 and (r.get("harness"), r.get("case_index"), r.get("inner")) not in l1]
    errors = (meta.get("n_errors") if isinstance(meta.get("n_errors"), int) else 0) + \
        sum(1 for r in recs.values() if r.get("error"))
    mismatch = [k for k, r in recs.items() if r.get("v5_setting") != expect_setting]
    return {"false_loc": len(false_loc), "unmatched": len(unmatched), "errors": errors,
            "setting_mismatch": len(mismatch), "false_loc_keys": false_loc, "unmatched_keys": unmatched[:50],
            "mismatch_keys": mismatch[:50]}


def seedext(name, se, noise, core, fnd):
    seeds = {}
    for r in se.values():
        seeds.setdefault(r.get("inner"), set()).add(r.get("seed_index"))
    ok_shape = len(seeds) == SEEDEXT_KEYS and all(v == set(range(SEEDEXT_SEEDS)) for v in seeds.values())
    if not ok_shape or len(se) != SEEDEXT_KEYS * SEEDEXT_SEEDS:
        fnd.stop("S-15", name, f"seedext shape {({k: len(v) for k, v in seeds.items()})}")
    chk = []
    for k, r in se.items():
        if isinstance(r.get("seed_index"), int) and r["seed_index"] < SEEDEXT_CHECK:
            n = noise.get(k)
            ha, hb = h(r), (None if n is None else h(n))
            chk.append({"key": k, "noise_found": n is not None, "same_hash": n is not None and ha is not None
                        and ha == hb, "hash_missing": ha is None or hb is None})
            if n is None:
                fnd.stop("S-15", f"{name}|{k}", "seed 0~4 key has no noise line")
            elif ha is not None and hb is not None and ha != hb:
                fnd.stop("H-15", f"{name}|{k}", "seed 0~4 hash differs from the noise line (rev6 9)")
    miss = sum(c["hash_missing"] for c in chk)
    return {"runs": len(se), "inners": {k: len(v) for k, v in seeds.items()}, "seed0_4_checked": len(chk),
            "seed0_4_same": sum(1 for c in chk if c["same_hash"]), "hash_missing": miss,
            "record_status": "기록 불완전" if miss else "complete", "detail": chk}


def grade_set(recs, gates, core):
    out = {}
    for k, r in recs.items():
        gr, why, cond = line_grade(k, r, None if gates is None else gates.get(k), core)
        out[k] = {"grade": gr, "why": why, "late_loc": cond}
    return out


def cmd_noise(args, repo, v5j, core):
    is_p3, mod = core.load_is_extend_start(repo)
    fnd = core.Findings()
    d_vb, vb = load(args.noise_vb)
    d_v0, v0 = load(args.noise_v0)
    d_h6, h6 = load(args.h6)
    gates = {lab: load_gates(p) for lab, p in (x.split("=", 1) for x in (args.gates or []))}
    reagg_items = []
    lv_vb, lv_v0, lv_h6 = levels(vb), levels(v0), levels(h6)
    if lv_vb != LEVEL_COUNTS or lv_v0 != LEVEL_COUNTS:
        fnd.stop("S-15", "noise", f"levels VB {lv_vb} V0 {lv_v0} != {LEVEL_COUNTS}")
    if set(vb) != set(v0):
        fnd.stop("S-15", "noise", f"VB / V0 key sets differ ({len(set(vb) ^ set(v0))})")
    if lv_h6 != H6_COUNTS:
        fnd.stop("S-15", "H-6", f"levels {lv_h6} != {H6_COUNTS}")
    if not set(h6) <= set(vb):
        fnd.stop("S-15", "H-6", f"{len(set(h6) - set(vb))} dg3 keys not in the noise VB keys")
    sub = [{"key": k, "same_hash": h(r) is not None and h(r) == h(vb.get(k, {})),
            "hash_missing": h(r) is None or h(vb.get(k, {})) is None} for k, r in h6.items()]
    jp = {"noise_VB": run_checks("noise_VB", vb, core, v5j, is_p3, True, fnd),
          "H-6": run_checks("H-6", h6, core, v5j, is_p3, True, fnd)}
    run_checks("noise_V0", v0, core, v5j, is_p3, False, fnd)
    l1g = l1_gate(d_vb.get("meta") or {}, vb, "VB", core)
    if l1g["false_loc"] or l1g["unmatched"] or l1g["errors"] or l1g["setting_mismatch"]:
        fnd.stop("H-10", "L1 gate", f"false LOC {l1g['false_loc']} unmatched {l1g['unmatched']} "
                                    f"errors {l1g['errors']} mismatch {l1g['setting_mismatch']}")
        fnd.fail("L1 gate", "v5 10 L1 gate violated")
    # re-aggregated line grades; the 135 dg3 keys replace the VB lines (rev8 #6)
    g_vb = grade_set(vb, gates.get("noise_VB"), core)
    g_h6 = grade_set(h6, gates.get("H-6"), core)
    g_v0 = grade_set(v0, gates.get("noise_V0"), core)
    eff = {k: (g_h6[k] if k in g_h6 else g) for k, g in g_vb.items()}
    for lab, gs in (("noise_VB", g_vb), ("H-6", g_h6), ("noise_V0", g_v0)):
        if lab not in gates:
            fnd.undec(lab, "r79 gate record not given (--gates)")
        reagg_items.append({"bundle": "H-6" if lab == "H-6" else "H-8", "set": lab,
                            "item": "r79 S-1~S-6 line grade (13.2 / 419.8 / 423.1)", "lines": len(gs),
                            "undecidable": sum(1 for g in gs.values() if g["grade"] == "undecidable")})
    res = {}
    for lev in ("L2", "L3"):
        keys = [k for k, r in vb.items() if r.get("level") == lev and not s1_front(r)]
        und = [k for k in keys if eff[k]["grade"] == "undecidable"]
        kf = sum(1 for k in keys if eff[k]["grade"] == "fail")
        res[lev] = {**cp_pair(kf, len(keys)), "flags": sum(1 for k in keys if eff[k]["grade"] == "flag"),
                    "undecidable": len(und),
                    "fallback_rows": sum(1 for k in keys if vb[k].get("rod_fallback_reasons")),
                    "pass_to_fail_vs_V0": [k for k in keys if eff[k]["grade"] == "fail"
                                           and g_v0.get(k, {}).get("grade") in ("pass", "flag")]}
        if und:
            fnd.undec(lev, f"{len(und)} undecidable line grades")
    l2 = res["L2"]
    if l2["undecidable"] == 0:
        l2["grade"] = "pass" if l2["upper_beta"] <= CP_LIMIT + 1e-12 and l2["upper_root"] <= CP_LIMIT + 1e-12 else "fail"
        if l2["grade"] == "fail":
            fnd.fail("L2", f"CP {l2['upper_beta']:.4f} > 3 %")
            fnd.stop("H-10", "L2", "L2 CP > 3 %")
    res["L3"]["grade"] = "record"
    se = {}
    if args.seedext_vb:
        _, sv = load(args.seedext_vb)
        jp["seedext_VB"] = run_checks("seedext_VB", sv, core, v5j, is_p3, True, fnd)
        se["VB"] = seedext("seedext_VB", sv, vb, core, fnd)
        se["VB"]["grades"] = grade_set(sv, gates.get("seedext_VB"), core)
    if args.seedext_v0:
        _, s0 = load(args.seedext_v0)
        run_checks("seedext_V0", s0, core, v5j, is_p3, False, fnd)
        se["V0"] = seedext("seedext_V0", s0, v0, core, fnd)
        se["V0"]["grades"] = grade_set(s0, gates.get("seedext_V0"), core)
    if "VB" in se and "V0" in se:
        se["record"] = seedext_record(se, core)
        reagg_items.append({"bundle": "H-8", "set": "seedext", "item": "r79 line grade -> k/25, CP, Fisher",
                            "lines": se["VB"]["runs"] + se["V0"]["runs"]})
    h6_grade = "stop" if any(s["where"].startswith("H-6|") for s in fnd.stops) else (
        "undecidable" if any(g["grade"] == "undecidable" for g in g_h6.values()) else "pass")
    body = {"inputs": {k: [p, cm.sha256_file(p)] for k, p in (("noise_vb", args.noise_vb),
                                                              ("noise_v0", args.noise_v0), ("h6", args.h6),
                                                              ("seedext_vb", args.seedext_vb),
                                                              ("seedext_v0", args.seedext_v0)) if p},
            "gate_inputs": {x.split("=", 1)[0]: [x.split("=", 1)[1], cm.sha256_file(x.split("=", 1)[1])]
                            for x in (args.gates or [])},
            "v5_options": mod,
            "recomputed": {"levels": {"VB": lv_vb, "V0": lv_v0, "H-6": lv_h6}, "L1_gate": l1g,
                           "H-6_substitution": {"keys": len(sub),
                                                "same_hash_as_H8_VB": sum(1 for s in sub if s["same_hash"]),
                                                "hash_missing": sum(1 for s in sub if s["hash_missing"]),
                                                "record_status": "기록 불완전" if any(s["hash_missing"] for s in sub)
                                                else "complete",
                                                "different": [s["key"] for s in sub
                                                              if not s["same_hash"] and not s["hash_missing"]]},
                           "J-P3": jp},
            "reaggregated": {"L2": l2, "L3": res["L3"], "seedext": se,
                             "line_grades": {"noise_VB_effective": eff, "H-6": g_h6, "noise_V0": g_v0}},
            "TABLE_REAGG": reagg_items,
            "H-6_grade": h6_grade, **fnd.as_dict()}
    st = fnd.status()
    lab = {"pass": "통과", "fail": "미달", "undecidable": "판정 불가", "stop": "멈춤"}
    body["grades_436_8"] = {"H-6": lab[h6_grade], "H-8": lab[st]}
    body["stop_codes"] = fnd.as_dict()["stop_codes"]
    return body, st


def seedext_record(se, core):
    """rev6 9 record: k/25 per key and setting, CP (two roots), Fisher one-sided (VB > V0)."""
    from scipy.stats import fisher_exact  # noqa: PLC0415
    out = {}
    inners = sorted(set(se["VB"]["inners"]) | set(se["V0"]["inners"]))
    for inner in inners:
        row = {}
        for s in ("VB", "V0"):
            gs = [g for k, g in se[s]["grades"].items() if k.endswith("|" + inner)]
            row[s] = {"k": sum(1 for g in gs if g["grade"] == "fail"), "n": len(gs),
                      "undecidable": sum(1 for g in gs if g["grade"] == "undecidable")}
            row[s].update(cp_pair(row[s]["k"], max(row[s]["n"], 1)))
        kv, k0, n = row["VB"]["k"], row["V0"]["k"], SEEDEXT_SEEDS
        p = float(fisher_exact([[kv, n - kv], [k0, n - k0]], alternative="greater")[1])
        row["fisher_p"] = p
        row["phrase"] = ("VB 체계적 악화 의심(하네스)" if p < FISHER_P and kv > k0 else "시드 산포와 구분되지 않음")
        out[inner] = row
    return out


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    cm.add_common_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("noise")
    n.add_argument("--noise-vb", required=True, help="resume_k1/h8_noise_VB.json")
    n.add_argument("--noise-v0", required=True, help="resume_k1/h8_noise_V0.json")
    n.add_argument("--h6", required=True, help="resume_k1/h6_dg3_v4on.json")
    n.add_argument("--seedext-vb", default=None, help="resume_k1/h8_seedext_VB.json")
    n.add_argument("--seedext-v0", default=None, help="resume_k1/h8_seedext_V0.json")
    n.add_argument("--gates", action="append", default=None,
                   help="LABEL=<r79 gate record json>, LABEL in noise_VB, noise_V0, H-6, seedext_VB, seedext_V0")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"noise": cmd_noise})


if __name__ == "__main__":
    sys.exit(main())
