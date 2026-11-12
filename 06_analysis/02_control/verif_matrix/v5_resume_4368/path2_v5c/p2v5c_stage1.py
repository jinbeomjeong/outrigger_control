"""436.8 path 2: v5-criteria grade recount of the stage-1 harness bundles H-10 and H-9 (main part).

Inputs (436.8 rules 4.3, rev1 RV1-2 / RV1-3.3 / RV1-4): ``resume_k1/h10_reuse_rerun.jsonl`` (440 lines:
main VB 100 + LS1~LS4 288, U-9 VB 28, item8 VB 6 + V0 6, overlap VB 4 + V0 4 + V3 4) and
``resume_k1/h9_stage1.jsonl`` (908 lines: main V0~V8 / L1 / L2 812 + pressure_only 96), optionally the
T4h folder of the VB / LS lines (rev9 3.1 rod reading) and ``h10_overlap_t_a.json`` (RV1-4, record).

Rules applied (v5 criteria original + revisions 1~12b read through the 436.8 rules; rule -> function):
  v5 3 J1~J11, rev2 2.1 (J9 post-lift), rev8 3.2 / rev9 3 (J-P3)  -> ``p2_v5j.judge_pair`` (imported)
  v5 2 P-6 (L1 / L2 hash), P-7 (L1 != V0)                            -> ``check_p6_p7``
  v5 4 / 11 H-4 (limit cycle VB or L1)                               -> ``bundle_h10`` / ``bundle_h9``
  v5 6 S8 F-5 clause and its stops (H-5)                             -> ``f5_clause``
  v5 8 VB x L1 table                                                 -> ``l1_table``
  v5 8 LS L-a..L-e (H-6)                                             -> ``ls_conditions``
  v5 11 H-2 (VB J fail), H-3 (R12 V0 pass count), H-7, H-8 (S7), H-9 -> ``bundle_h10``
  v5 13.1 item 8 order (H-11)                                        -> ``item8_order``
  v5 13.3 overlap record (FLAG_overlap)                              -> ``overlap_record``
  v5 13.4 pressure_only record (unit_status)                        -> ``pressure_only_record``
  rev4 #4 / rev5 #1 / rev6 #9 m2_law key (flow_limited_r5)           -> ``m2_law_check``
  rev1 RV1-2 / RV1-12 line counts (S-15)                             -> ``split_lines``
U-9 VB (28 lines of H-10) is graded by ``p2_v5j.py u9`` (dynamics-expert); this tool only counts them.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402

TOOL_NAME = "p2v5c_stage1.py"
TOOL_VERSION = "1"

M2_ON = {"V1", "V3", "VB", "V4", "V5", "V6", "V7", "V8", "LS1", "LS2", "LS3", "LS4"}   # v5 8
M2_LAW = "flow_limited_r5"                                                         # rev6 #9
FLOW_ON = {"V2", "V3", "VB", "V4", "V5", "V6", "V7", "V8", "LS1", "LS2", "LS3", "LS4"}  # v5 6
FLOW_OFF = {"V0", "V1", "L1"}                                                      # v5 6
LS_SETTINGS = ("LS1", "LS2", "LS3", "LS4")
H9_MAIN_COUNTS = {"V0": 100, "V1": 72, "V2": 72, "V3": 72, "V4": 100, "V5": 100, "V6": 72, "V7": 72,
                  "V8": 72, "L1": 72, "L2": 8}                                      # v5 0 / 8, 436.8 5.1
H10_MAIN_COUNTS = {"VB": 100, "LS1": 72, "LS2": 72, "LS3": 72, "LS4": 72}           # RV1-2
PRESSURE_ONLY_COUNTS = {"V0": 32, "V4": 32, "V5": 32}                              # v5 13.4
ITEM8_COUNTS = {"VB": 6, "V0": 6}                                                  # v5 13.1
OVERLAP_COUNTS = {"V0": 4, "V3": 4, "VB": 4}                                       # v5 13.3
U9_VB_COUNT = 28
H10_TOTAL, H9_TOTAL = 440, 908                                                     # RV1-12
ITEM8_ROWS = (("R6", "top"), ("R8", "middle"), ("R9", "bottom"))                    # v5 13.1
ITEM8_NEW_EPS = (0.001, 0.003)
F5_MARGIN_STOP_KN, F5_MAX_AFTER_STOP_KN = -6.92, 14.21                             # v5 6 (user values)
LD_FORCE_KN, LD_READY_S = 1.0, 1.0                                                 # v5 8 L-d (assumption)
LA_ITEMS = ("J1", "J2", "J4", "J6", "J7")                                          # v5 8 L-a
J_FAIL_ITEMS = ("J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "J10")


def setting(ln):
    return (ln.get("job") or {}).get("setting")


def kind_of(ln):
    job = ln.get("job") or {}
    if "timing" in job:
        return "overlap"
    if "contact" in job:
        return "pressure_only"
    if job.get("u9_metrics"):
        return "u9"
    if job.get("case") in ("R6", "R8", "R9") and any(
            abs(float(job.get("eps", 0.0)) - e) < 1e-12 for e in ITEM8_NEW_EPS):
        return "item8"
    return "main"


def split_lines(h9, h10, fnd):
    """S-15 counts (436.8 5.1, RV1-2, RV1-12) and duplicate keys."""
    parts = {"h9": {}, "h10": {}}
    for name, lines in (("h9", h9), ("h10", h10)):
        for ln in lines:
            parts[name].setdefault(kind_of(ln), []).append(ln)
    counts = {n: {k: _count(v) for k, v in p.items()} for n, p in parts.items()}
    want = {("h9", "main"): H9_MAIN_COUNTS, ("h9", "pressure_only"): PRESSURE_ONLY_COUNTS,
            ("h10", "main"): H10_MAIN_COUNTS, ("h10", "item8"): ITEM8_COUNTS,
            ("h10", "overlap"): OVERLAP_COUNTS}
    for (f, k), w in want.items():
        got = counts[f].get(k, {})
        if got != w:
            fnd.stop("S-15", f"{f}:{k}", f"line counts {got} != {w}")
    if counts["h10"].get("u9", {}) != {"VB": U9_VB_COUNT}:
        fnd.stop("S-15", "h10:u9", f"U-9 VB lines {counts['h10'].get('u9')} != {U9_VB_COUNT}")
    extra = {f: sorted(set(p) - {"main", "pressure_only"} if f == "h9" else set(p) - {"main", "item8",
                                                                                     "overlap", "u9"})
             for f, p in parts.items()}
    for f, ks in extra.items():
        if ks:
            fnd.stop("S-15", f, f"unexpected line kinds {ks}")
    if len(h9) != H9_TOTAL or len(h10) != H10_TOTAL:
        fnd.stop("S-15", "files", f"h9 {len(h9)} / h10 {len(h10)} != {H9_TOTAL} / {H10_TOTAL}")
    return parts, counts


def _count(lines):
    out = {}
    for ln in lines:
        out[setting(ln)] = out.get(setting(ln), 0) + 1
    return out


def index_by_pair(v5j, lines, where, fnd):
    idx = {}
    for ln in lines:
        k = v5j.pair_key(ln["job"])
        if k in idx:
            fnd.stop("S-15", where, f"duplicate pair key {k}")
        idx[k] = ln
    return idx


def m2_law_check(lines, core, fnd, where):
    """rev6 #9: M2-on lines carry m2_law flow_limited_r5, M2-off lines none (else rerun -> undecidable)."""
    bad = []
    for ln in lines:
        s = setting(ln)
        law = core.dig(ln, "hydraulic_options.m2_law", None)
        if (s in M2_ON and law != M2_LAW) or (s not in M2_ON and law is not None):
            bad.append({"job": ln.get("job"), "m2_law": law})
    for b in bad:
        fnd.undec(where, f"m2_law key {b['m2_law']!r} on {b['job']} (rev6 #9: rerun)")
    return {"checked": len(lines), "bad": len(bad)}


def f5_clause(ln, core):
    """v5 6: clause = crawler load after stop <= load at stop + 0.01 W (record values)."""
    sc = ln.get("soil_stop_crawler")
    if not isinstance(sc, dict):
        return {"status": "missing"}
    at, thr, mx = (core.num(sc.get(k)) for k in ("at_stop_kN", "threshold_kN", "max_after_stop_kN"))
    if at is None or thr is None:
        return {"status": "missing", "record": sc}
    margin = None if mx is None else at + thr - mx
    ok = True if mx is None else not core.t_gt(mx, at + thr)
    return {"status": "ok" if ok else "clause_fail", "at_stop_kN": at, "threshold_kN": thr,
            "max_after_stop_kN": mx, "margin_kN_p2": margin,
            "margin_at_stop_kN_recorded": sc.get("margin_at_stop_kN"),
            "max_before_1s_kN": sc.get("max_before_1s_kN"), "near_stop_pm0p1s_kN": sc.get("near_stop_pm0p1s_kN")}


T_S = 0.1   # 436.8 2: compare times as n = round(t / T_s)
LIFT_AFTER_STOP_PATHS = ("soil_stop_crawler.pad_lift_after_stop_ms", "soil_stop_crawler.lift_ms_after_stop",
                         "values.lift_after_stop_ms")   # rev3 Q-S6 "정지 뒤 부상 0": record name not known yet


def _events(ln):
    ev = ln.get("events")
    if not isinstance(ev, list):
        return None
    return [(float(e[0]), e[1]) for e in ev if isinstance(e, (list, tuple)) and len(e) == 2
            and isinstance(e[1], str) and isinstance(e[0], (int, float))]


def sa4_rest(ln, core):
    """rev3 R3-E5 Q-S6: the SA-4 items other than the F-5 clause (True / False / None = no record)."""
    ev = _events(ln)
    out = {}
    if ev is None:
        out["same_cycle_warn_fault_soil"] = None
    else:
        w = {round(t / T_S) for t, n in ev if n.startswith("WARN_LIFT_STROKE_LIMITED:")}
        f = {round(t / T_S) for t, n in ev if n.startswith("FAULT_LIFT_STROKE_LIMIT:soil")}
        out["same_cycle_warn_fault_soil"] = bool(w & f)
    names = [n for _, n in (ev or [])] + [s for s in (core.dig(ln, "values.events.fault_events", None) or [])
                                          if isinstance(s, str)]
    out["fault_stroke_end_0"] = None if ev is None else not any(n.startswith("FAULT_STROKE_END") for n in names)
    tr = core.dig(ln, "values.times.t_first_ready_s", core.MISSING)
    out["ready_0"] = None if tr is core.MISSING else tr is None
    stop_t = core.num(core.dig(ln, "soil_stop_crawler.stop_t_s", None))
    mn = core.num(core.dig(ln, "values.forces.after_liftoff.min_kN", None))
    mt = core.num(core.dig(ln, "values.forces.after_liftoff.t_s", None))
    fmin = core.F_MIN_N / 1000.0
    if mn is not None and core.t_ge(mn, fmin):
        out["after_stop_Fmin"] = True          # after-liftoff minimum covers the post-stop part
    elif mn is not None and mt is not None and stop_t is not None and mt >= stop_t:
        out["after_stop_Fmin"] = False
    else:
        out["after_stop_Fmin"] = None
    lift = None
    for p in LIFT_AFTER_STOP_PATHS:
        v = core.num(core.dig(ln, p, None))
        if v is not None:
            lift = v == 0
            break
    out["lift_after_stop_0"] = lift
    mp = core.num(core.dig(ln, "values.pressure.max_moving_bar", None))
    out["moving_le_180"] = None if mp is None else not core.t_gt(mp, 180.0)
    sat = core.dig(ln, "values.pressure.saturation_leg_chunks", None)
    out["saturation_block_0"] = None if not isinstance(sat, int) else sat == 0
    return out


def fl_guard_cycle(ln):
    """rev3 Q-S7: cycle of the first WARN_LIFT_STROKE_LIMITED: event whose leg list holds FL."""
    ev = _events(ln)
    if ev is None:
        return "no_events"
    for t, n in sorted(ev):
        if n.startswith("WARN_LIFT_STROKE_LIMITED:") and "FL" in n.split(":", 1)[1].replace(",", " ").replace("+", " ").split():
            return round(t / T_S)
    return None


def judge_all(v5j, core, lines, v0_idx, nrev, is_p3, t4h_root, where):
    """judge_pair for every line; returns {pair_key: (items, findings)}."""
    out = {}
    for ln in lines:
        pk = v5j.pair_key(ln["job"])
        v0 = v0_idx.get(pk)
        if v0 is None:
            f = core.Findings()
            f.undec(where, f"no V0 partner for {pk}")
            out[(setting(ln), pk)] = ({}, f)
            continue
        rod = v5j.rod_reading_from_t4h(ln, t4h_root) if t4h_root else None
        items, f = v5j.judge_pair(ln, v0, nrev.get(v5j.row_key(ln["job"])), is_p3, rod)
        if setting(ln) in ("VB",) + LS_SETTINGS and items.get("J-P3", {}).get("result") == "not_applicable_tag":
            f.undec(where, f"J-P3 not applied on {setting(ln)} line (tag not ③ on): {pk}")
        out[(setting(ln), pk)] = (items, f)
    return out


def line_failed(items, names=J_FAIL_ITEMS):
    return sorted(n for n in names if items.get(n, {}).get("result") == "fail")


def ls_conditions(judged, vb_lines, v5j, core, fnd):
    """v5 8 L-a..L-e (violation of a, b, c, e = H-6 stop; d = record)."""
    vb = {v5j.pair_key(ln["job"]): ln for ln in vb_lines}
    vb_ok = {pk: not line_failed(judged[("VB", pk)][0]) and not judged[("VB", pk)][1].undecidable
             for pk in vb if ("VB", pk) in judged}
    out = {}
    for s in LS_SETTINGS:
        rec = {"L-a": [], "L-b": [], "L-c": [], "L-e": [], "L-d_large": [], "lines": 0}
        for (st, pk), (items, f) in judged.items():
            if st != s:
                continue
            rec["lines"] += 1
            if vb_ok.get(pk):
                bad = line_failed(items, LA_ITEMS)
                if bad:
                    rec["L-a"].append([pk, bad])
            for j in ("J3", "J5"):
                if items.get(j, {}).get("result") in ("fail", "baseline_fail"):
                    rec["L-b"].append([pk, j])
            if items.get("J8", {}).get("result") == "fail":
                rec["L-c"].append(pk)
            if items.get("J11", {}).get("result") == "stop":
                rec["L-e"].append(pk)
        rec["L-d_large"] = ld_large(s, judged, vb, v5j, core)
        for c in ("L-a", "L-b", "L-c", "L-e"):
            for x in rec[c]:
                fnd.stop("H-6", f"{s}:{c}", json.dumps(x, ensure_ascii=False)[:300])
        out[s] = {k: (len(v) if isinstance(v, list) else v) for k, v in rec.items()} | {"detail": rec}
    return out


_LINE_CACHE = {}   # (setting, pair key) -> line, filled by cmd_stage1


def ld_large(s, judged, vb, v5j, core):
    """v5 8 L-d with rev3 Q-S9: per row (all phases) and metric (min force kN, first READY s),
    E_r = median(LS) - median(VB), S_r = ptp(VB phases) (m1_criteria 5). '감도 큼' (record) when
    |E_r| >= limit and the effect is distinguished (|E_r| > S_r and all pair differences share a sign)."""
    rows = {}
    for (st, pk), _ in judged.items():
        if st != s or pk not in vb:
            continue
        a, b = v5j.j_values(vb[pk]), v5j.j_values(_LINE_CACHE[(s, pk)])
        rk = v5j.row_key(vb[pk]["job"])
        for m, lim in (("minF", LD_FORCE_KN), ("t_ready", LD_READY_S)):
            if a[m] is not None and b[m] is not None:
                rows.setdefault((rk, m, lim), []).append((a[m], b[m]))
    out = []
    for (rk, m, lim), pairs in rows.items():
        base = [p[0] for p in pairs]
        e = statistics.median(p[1] for p in pairs) - statistics.median(base)
        sr = max(base) - min(base)
        d = [p[1] - p[0] for p in pairs]
        same_sign = all(x > 0 for x in d) or all(x < 0 for x in d)
        distinguished = abs(e) > sr and same_sign
        if core.t_ge(abs(e), lim) and distinguished:
            out.append({"row": rk, "metric": m, "E_r": e, "S_r": sr, "phases": len(pairs),
                        "weak": len(pairs) <= 2})
    return out


def l1_table(judged, fnd):
    """v5 8: VB x L1 per row (VB fail & L1 pass / fail = stop; VB pass & L1 fail = record)."""
    rows = {}
    for (s, pk), (items, f) in judged.items():
        if s in ("VB", "L1"):
            rows.setdefault(pk, {})[s] = "fail" if line_failed(items) else (
                "undecidable" if f.undecidable else "pass")
    tab = {"pass/pass": 0, "pass/fail": 0, "fail/pass": 0, "fail/fail": 0, "incomplete": 0}
    for pk, r in rows.items():
        if "VB" not in r or "L1" not in r or "undecidable" in r.values():
            if "VB" in r and "L1" in r:
                tab["incomplete"] += 1
            continue
        key = f"{r['VB']}/{r['L1']}"
        tab[key] += 1
        if r["VB"] == "fail":
            fnd.stop("L1-table", pk, f"VB {r['VB']} / L1 {r['L1']} (v5 8: stop)")
    return tab


def check_p6_p7(main_lines, v5j, fnd):
    by = {}
    for ln in main_lines:
        by.setdefault(setting(ln), {})[v5j.pair_key(ln["job"])] = ln.get("commands_sha256")
    l1, l2, v0 = by.get("L1", {}), by.get("L2", {}), by.get("V0", {})
    p6 = {"compared": 0, "differ": []}
    for pk, h in l2.items():
        p6["compared"] += 1
        if pk not in l1 or l1[pk] != h or not isinstance(h, str):
            p6["differ"].append(pk)
    if p6["compared"] != 8 or p6["differ"]:
        fnd.stop("P-6", "L2", f"compared {p6['compared']} differ {len(p6['differ'])}")
    same = sorted(pk for pk, h in l1.items() if v0.get(pk) == h)
    p7 = {"L1_lines": len(l1), "L1_equal_V0": len(same), "equal_keys": same}
    if l1 and len(same) == len(l1):
        fnd.stop("P-7", "L1", "every L1 hash equals its V0 hash (LC did not act)")
    return {"P-6": {"compared": p6["compared"], "differ": len(p6["differ"]), "keys": p6["differ"]}, "P-7": p7}


def item8_order(main_lines, item8_lines, core, fnd):
    """v5 13.1. Metric: after-liftoff 1 ms minimum (values.forces.after_liftoff.min_kN), 4 phases."""
    out = {}
    for s in ("V0", "VB"):
        stats = {}
        for case, level in ITEM8_ROWS:
            vals = {}
            for ln in main_lines + item8_lines:
                job = ln["job"]
                if job.get("case") == case and setting(ln) == s:
                    vals[round(float(job.get("eps", 0.0)), 6)] = core.num(core.dig(ln, "values.forces.after_liftoff.min_kN", None))
            ok = sorted(vals) == [0.0, 0.001, 0.002, 0.003] and all(v is not None for v in vals.values())
            stats[level] = {"case": case, "values": vals, "complete": ok,
                            "median": statistics.median(vals.values()) if ok else None,
                            "range": [min(vals.values()), max(vals.values())] if ok else None}
        if not all(v["complete"] for v in stats.values()):
            out[s] = {"rows": stats, "result": "undecidable"}
            fnd.undec(f"item8:{s}", "4 phases x 3 rows not complete")
            continue
        pairs = (("top", "middle"), ("middle", "bottom"))
        rel = []
        for lo, hi in pairs:
            a, b = stats[lo], stats[hi]
            overlap = not (core.t_lt(a["range"][1], b["range"][0]) or core.t_lt(b["range"][1], a["range"][0]))
            if core.t_lt(a["median"], b["median"]) and not overlap:
                rel.append("kept")
            elif core.t_gt(a["median"], b["median"]) and not overlap:
                rel.append("reversed")
            else:
                rel.append("undetermined")
        # rev3 R3-E5 Q-S5: "reversed" only when fully reversed (m_top > m_mid > m_bottom, no overlap)
        res = "order_kept" if rel == ["kept", "kept"] else ("reversed" if rel == ["reversed", "reversed"]
                                                            else "undetermined")
        out[s] = {"rows": stats, "pairs": rel, "result": res}
    if out.get("VB", {}).get("result") == "reversed" and out.get("V0", {}).get("result") == "order_kept":
        out["grade"] = "fail"
        fnd.stop("H-11", "item8", "VB order reversed while V0 keeps the order")
        fnd.fail("item8", "13.1 reversed")
    else:
        out["grade"] = "flag" if out.get("VB", {}).get("result") == "undetermined" else (
            "undecidable" if out.get("VB", {}).get("result") == "undecidable" else "pass")
    return out


def overlap_record(judged_ov, ov_lines, v5j, core, ta_path):
    rows = []
    for ln in ov_lines:
        s = setting(ln)
        if s == "V0":
            continue
        items, f = judged_ov[(s, v5j.pair_key(ln["job"]))]
        of = ln.get("overlap_found")
        exists = None
        if isinstance(of, dict):
            # v5 13.3: Q_dem > Q_sup time in the event window [ms] (record field ``over_ms``)
            ms = core.num(of.get("over_ms"))
            exists = (ms > 0) if ms is not None else None
        changed = any(items.get(j, {}).get("v0") != items.get(j, {}).get("set") for j in ("J1", "J2"))
        rows.append({"setting": s, "job": ln["job"], "overlap_found": of, "overlap_exists": exists,
                     "J1J2_changed": changed, "FLAG_overlap": bool(exists) and changed,
                     "items": {k: v.get("result") for k, v in items.items()}})
    ta = None
    if ta_path:
        ta = {"path": ta_path, "sha256": cm.sha256_file(ta_path),
              "content": json.loads(Path(ta_path).read_text("utf-8"))}
    return {"rows": rows, "t_a_reference": ta, "grade": "record"}


def pressure_only_record(lines):
    us = {}
    for ln in lines:
        us[str(ln.get("unit_status"))] = us.get(str(ln.get("unit_status")), 0) + 1
    return {"lines": len(lines), "unit_status": us,
            "ok": us == {"below_criteria_reference_only": len(lines)}, "grade": "record"}


def summarize(judged, settings):
    tab = {}
    for (s, pk), (items, f) in judged.items():
        if s not in settings:
            continue
        t = tab.setdefault(s, {"lines": 0, "fail_lines": 0, "undecidable_lines": 0, "stop_lines": 0,
                               "items": {}})
        t["lines"] += 1
        t["fail_lines"] += bool(line_failed(items))
        t["undecidable_lines"] += bool(f.undecidable)
        t["stop_lines"] += bool(f.stops)
        for n, v in items.items():
            r = v.get("result")
            t["items"].setdefault(n, {}).setdefault(r, 0)
            t["items"][n][r] += 1
    return tab


def merge(fnd, f, prefix=""):
    for s in f.stops:
        fnd.stop(s["code"], prefix + str(s["where"])[:200], s["why"])
    for u in f.undecidable:
        fnd.undec(prefix + str(u["where"])[:200], u["why"])
    for x in f.fails:
        fnd.fail(prefix + str(x["where"])[:200], x["why"])


def cmd_stage1(args, repo, v5j, core):
    h9 = core.read_jsonl(args.h9)
    h10 = core.read_jsonl(args.h10)
    is_p3, mod = core.load_is_extend_start(repo)
    f10, f9 = core.Findings(), core.Findings()
    parts, counts = split_lines(h9, h10, f10)
    for s in f10.stops:
        f9.stop(s["code"], s["where"], s["why"])
    main9, main10 = parts["h9"].get("main", []), parts["h10"].get("main", [])
    po = parts["h9"].get("pressure_only", [])
    it8, ov = parts["h10"].get("item8", []), parts["h10"].get("overlap", [])
    v0_main = [x for x in main9 if setting(x) == "V0"]
    v0_it8 = [x for x in it8 if setting(x) == "V0"]
    v0_ov = [x for x in ov if setting(x) == "V0"]
    v0_idx = index_by_pair(v5j, v0_main + v0_it8, "V0", f9)
    nrev = v5j.nrev_max_by_row(v0_main + v0_it8)
    for ln in main9 + main10 + it8 + ov:
        _LINE_CACHE[(setting(ln), v5j.pair_key(ln["job"]))] = ln
    # V0 lines: J11 stop (n_late counted on every row, v5 8 window rule) and J9 not applicable
    for ln in v0_main + v0_it8 + v0_ov:
        nlf = core.dig(ln, "lock_window_alignment.n_late_fallback", None)
        if isinstance(nlf, int) and nlf > 0:
            f9.stop("H-7", v5j.pair_key(ln["job"]), f"V0 n_late_fallback {nlf}")
    j9 = judge_all(v5j, core, [x for x in main9 if setting(x) != "V0"], v0_idx, nrev, is_p3, None, "h9")
    j10 = judge_all(v5j, core, main10 + [x for x in it8 if setting(x) != "V0"], v0_idx, nrev, is_p3,
                    args.t4h_root, "h10")
    ov_idx = index_by_pair(v5j, v0_ov, "overlap V0", f10)
    jov = judge_all(v5j, core, [x for x in ov if setting(x) != "V0"], ov_idx, nrev, is_p3, args.t4h_root, "ov")
    # S8 F-5 and the rest of SA-4 (v5 6, rev3 R3-E5 Q-S6) - decided first because an F-5 record
    # line does not count its clause fail as a new fail
    f5, f5_record = [], set()
    for ln in main9 + main10:
        if (ln.get("job") or {}).get("case") != "S8":
            continue
        s, pk = setting(ln), v5j.pair_key(ln["job"])
        c = f5_clause(ln, core)
        rest = sa4_rest(ln, core)
        c.update(setting=s, job=ln["job"], sa4_rest=rest)
        f5.append(c)
        fx = f9 if s not in ("VB",) + LS_SETTINGS else f10
        vals = list(rest.values())
        if False in vals:
            c["result"] = "fail (SA-4 rest)"
            if fx is f10:
                fx.fail(f"{s}|{pk}", f"SA-4 item false {[k for k, v in rest.items() if v is False]}")
                if s == "VB":
                    fx.stop("H-2", pk, "VB SA-4 fail")
            else:
                fx.note(f"{s}|{pk}", "SA-4 item false (no grade for this setting)")
        elif None in vals:
            c["result"] = "undecidable (SA-4 record missing)"
            if fx is f10:
                fx.undec(f"{s}|{pk}", f"SA-4 record missing {[k for k, v in rest.items() if v is None]}")
        elif c["status"] == "clause_fail":
            if s in FLOW_ON:
                c["result"] = "F-5 record"
                f5_record.add((s, pk))
            elif s in FLOW_OFF:
                c["result"] = "stop H-5"
                fx.stop("H-5", s, "F-5 clause fail on a flow-off setting")
        elif c["status"] == "missing":
            c["result"] = "undecidable (clause record missing)"
            if fx is f10:
                fx.undec(f"{s}|{pk}", "soil_stop_crawler missing")
        else:
            c["result"] = "pass"
        if s == "VB" and c.get("margin_kN_p2") is not None and core.t_lt(c["margin_kN_p2"], F5_MARGIN_STOP_KN):
            f10.stop("H-5", "VB S8", f"clause margin {c['margin_kN_p2']} < {F5_MARGIN_STOP_KN}")
        if s == "VB" and c.get("max_after_stop_kN") is not None and core.t_gt(c["max_after_stop_kN"], F5_MAX_AFTER_STOP_KN):
            f10.stop("H-5", "VB S8", f"max after stop {c['max_after_stop_kN']} > {F5_MAX_AFTER_STOP_KN}")
    for (s, pk), (items, f) in j10.items():
        if (s, pk) in f5_record:   # v5 6: flow-on clause-only fail = F-5 record, not a new fail
            f.fails = [x for x in f.fails if not str(x.get("why", "")).startswith("J1")]
            if items.get("J1", {}).get("result") == "fail":
                items["J1"]["result"] = "F-5 record"
        merge(f10, f, f"{s}|")
        if s == "VB":
            bad = line_failed(items)
            if bad:
                f10.stop("H-2", pk, f"VB J fail {bad}")
            if items.get("J8", {}).get("result") == "fail":
                f10.stop("H-4", pk, "VB limit cycle")
    for (s, pk), (items, f) in j9.items():
        # H-9 main settings other than L1 have no grade (v5 8); only stop conditions are carried
        for st in f.stops:
            f9.stop(st["code"], f"{s}|{st['where']}"[:200], st["why"])
        if s == "L1" and items.get("J8", {}).get("result") == "fail":
            f9.stop("H-4", pk, "L1 limit cycle")
        if s in ("L1", "L2", "V1", "V2", "V3") and f.undecidable:
            for u in f.undecidable:
                f9.note(f"{s}|{u['where']}"[:200], u["why"])
    for (s, pk), (items, f) in jov.items():
        for st in f.stops:
            f10.stop(st["code"], f"overlap|{st['where']}"[:200], st["why"])
    # H-3: R12 V0 pass count (main, 4 phases)
    r12 = {s: sum(1 for ln in (v0_main if s == "V0" else [x for x in main10 if setting(x) == "VB"])
                  if ln["job"].get("case") == "R12" and core.dig(ln, "event_output.pass", None) is True)
           for s in ("V0", "VB")}
    if r12["VB"] < r12["V0"]:
        f10.stop("H-3", "R12", f"VB event passes {r12['VB']} < V0 {r12['V0']}")
    # H-8: S7 class and guard time
    s7 = []
    for ln in [x for x in main10 if setting(x) == "VB" and x["job"].get("case") == "S7"]:
        v0 = v0_idx.get(v5j.pair_key(ln["job"]))
        if v0 is None:
            continue
        g0, g1 = fl_guard_cycle(v0), fl_guard_cycle(ln)
        rec = {"job": ln["job"], "class_v0": v0.get("harness_class"), "class_vb": ln.get("harness_class"),
               "fl_guard_cycle_v0": g0, "fl_guard_cycle_vb": g1}
        s7.append(rec)
        if rec["class_v0"] != rec["class_vb"]:
            f10.stop("H-8", "S7", f"class {rec['class_v0']} -> {rec['class_vb']}")
        if g0 == "no_events" or g1 == "no_events":
            f10.undec("S7", "events list missing (H-8 FL guard time, rev3 Q-S7)")
        elif g0 != g1:
            f10.stop("H-8", "S7", f"FL guard cycle {g0} -> {g1}")
    ls = ls_conditions(j10, [x for x in main10 if setting(x) == "VB"], v5j, core, f10)
    l1t = l1_table({**j9, **{k: v for k, v in j10.items() if k[0] == "VB"}}, f10)
    p67 = check_p6_p7(main9, v5j, f9)
    m2_10 = m2_law_check(main10 + it8 + ov, core, f10, "h10")
    m2_9 = m2_law_check(main9 + po, core, f9, "h9")
    i8 = item8_order([x for x in main9 + main10 if setting(x) in ("V0", "VB")], it8, core, f10)
    ovr = overlap_record(jov, ov, v5j, core, args.overlap_ta)
    por = pressure_only_record(po)
    if not por["ok"]:
        f9.note("pressure_only", f"unit_status {por['unit_status']}")
    body = {
        "inputs": {"h9": [args.h9, cm.sha256_file(args.h9)], "h10": [args.h10, cm.sha256_file(args.h10)],
                   "t4h_root": args.t4h_root, "overlap_ta": args.overlap_ta},
        "v5_options": mod, "counts": counts,
        "H-10": {"VB_and_LS": summarize(j10, {"VB"} | set(LS_SETTINGS)), "LS_conditions": ls,
                 "R12_event_passes": r12, "S7": s7, "item8_13_1": i8, "overlap_13_3": ovr,
                 "U9_VB": {"lines": counts["h10"].get("u9"), "grade": "by p2_v5j.py u9 (not here)"},
                 "m2_law": m2_10, **f10.as_dict()},
        "H-9_stage1": {"settings": summarize(j9, set(H9_MAIN_COUNTS) - {"V0"}), "VB_x_L1": l1t,
                       "P-6_P-7": p67, "pressure_only_13_4": por, "m2_law": m2_9, **f9.as_dict()},
        "S8_F5": f5,
        "per_line": {f"{s}|{pk}": {n: v.get("result") for n, v in items.items()}
                     for (s, pk), (items, f) in {**j9, **j10, **jov}.items()},
    }
    g = {"H-10": f10.status(), "H-9_stage1": f9.status()}
    body["grades_436_8"] = {k: {"pass": "통과", "fail": "미달", "undecidable": "판정 불가", "stop": "멈춤"}[v]
                            for k, v in g.items()}
    body["stop_codes"] = sorted(set(f10.as_dict()["stop_codes"]) | set(f9.as_dict()["stop_codes"]))
    status = "stop" if "stop" in g.values() else ("undecidable" if "undecidable" in g.values() else (
        "fail" if "fail" in g.values() else "pass"))
    return body, status


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    cm.add_common_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage1")
    s.add_argument("--h9", required=True, help="resume_k1/h9_stage1.jsonl")
    s.add_argument("--h10", required=True, help="resume_k1/h10_reuse_rerun.jsonl")
    s.add_argument("--t4h-root", default=None, help="T4h folder of the H-10 VB / LS lines (rev9 3.1)")
    s.add_argument("--overlap-ta", default=None, help="resume_k1/h10_overlap_t_a.json (record)")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"stage1": cmd_stage1})


if __name__ == "__main__":
    sys.exit(main())
