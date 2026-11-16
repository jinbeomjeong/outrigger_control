"""436.8 path 2: v5-criteria grade recount of the stage-1 harness bundles H-10 and H-9 (main part).

Inputs (436.8 rules 4.3, rev1 RV1-2 / RV1-3.3 / RV1-4): ``resume_k1/h10_reuse_rerun.jsonl`` (440 lines:
main VB 100 + LS1~LS4 288, U-9 VB 28, item8 VB 6 + V0 6, overlap VB 4 + V0 4 + V3 4) and
``resume_k1/h9_stage1.jsonl`` (908 lines: main V0~V8 / L1 / L2 812 + pressure_only 96), optionally the
T4h folder of the VB / LS lines (rev9 3.1 rod reading) and ``h10_overlap_t_a.json`` (RV1-4, record).
436.8 rev11 R11-2: the T4h of an H-10 line (main, item8, overlap; all from the ``--h10`` file) is looked
up only in the runner convention folders of ``--h10`` (``<stem>_t4h/``, ``t4h/`` next to it); one
``--t4h-root`` only when neither exists (given anyway, or two or more = input error: S-11, exit 2, the
bundles are not judged); a recorded ``t4h_file`` found 0 or 2+ times = S-2. A line without ``t4h_file``
keeps the configuration reading (rev3 R3-C8). Search: ``p2_v5j.t4h_places`` / ``rod_reading_lookup``.
436.8 rev12 R12-1 (Q-R12-1 = A): on such an S-2 line the J-P3 is not judged (``common.strip_jp3``): the
configuration reading does not stand in; a ``t4h_file`` value that is not a file name is also S-2.

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

R4 (436.8 R4 common block sha256 e451f067..., supplement 2-1 / 2-2; 2-terra author, a new agent run without the
earlier authors' context): every line of ``h9_stage1.jsonl`` (bundle H-9: main + pressure_only) and of
``h10_reuse_rerun.jsonl`` (bundle H-10, U-9 VB lines included) is a row of the RD-7 scan (``rd_scan``, position
``line N`` = physical line number): J-P3 rows of the 3-on lines (row tag, ``p2_v5j.jp3``; RD-8 format defect =
undecidable, never a pass), J11 rows by ``p2_v5j.j11_item`` (stop settings VB / LS1~LS4, item8 and overlap VB;
records V0~V8, L1, L2, pressure_only; rev16:102~103, RD-10), RD-9 3-on counts (H-10 0 = S-8; H-9 0 = S-8 on the
sum with the grid part, ``merge``). The old V0 ``n_late_fallback`` H-7 stop is removed (the V0 J11 is a record).
H-9 3-on lines read a recorded T4h only from the convention folders of ``--h9`` (R12-1). ``merge`` collates the
noise / stage1 / grid outputs into one RD-7 / RD-8 / RD-9 / RD-10 / RD-13 file.
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
TOOL_VERSION = "2"

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
LIFT_AFTER_STOP_PATH = "values.sa4.lift_after_stop_ms"   # rev4 R4-B1 (rev3 Q-S6 "정지 뒤 부상 0")
AFTER_STOP_FMIN_PATH = "values.sa4.F_min_after_stop_N"   # rev6 R6-C1 / F-9


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
    # rev6 R6-C1 1: F-9 values.sa4.F_min_after_stop_N (per leg, N); without it the after-liftoff
    # minimum >= F_min is a sufficient condition, else undecidable
    f9 = core.dig(ln, AFTER_STOP_FMIN_PATH, None)
    if isinstance(f9, list) and len(f9) == 4 and all(core.num(x) is not None for x in f9):
        out["after_stop_Fmin"] = core.t_ge(min(core.num(x) for x in f9), core.F_MIN_N)
        out["after_stop_Fmin_source"] = "F-9"
    else:
        mn = core.num(core.dig(ln, "values.forces.after_liftoff.min_kN", None))
        out["after_stop_Fmin"] = True if (mn is not None and core.t_ge(mn, core.F_MIN_N / 1000.0)) else None
        out["after_stop_Fmin_source"] = "after_liftoff (sufficient)"
    lv = core.dig(ln, LIFT_AFTER_STOP_PATH, None)   # rev4 R4-B1: per-leg ms (FL, FR, RL, RR)
    if isinstance(lv, list) and len(lv) == 4 and all(core.num(x) is not None for x in lv):
        out["lift_after_stop_0"] = all(core.num(x) == 0 for x in lv)
    else:
        out["lift_after_stop_0"] = None
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


def is_p3_line(v5j, is_p3, ln):
    """3 on by the row tag only (original 4.1, rev8 R8-2)."""
    t = v5j.tag_of(ln)
    return is_p3 is not None and isinstance(t, str) and bool(is_p3(t))


def judge_all(v5j, core, lines, v0_idx, nrev, is_p3, t4h_dirs, where, t4h_log=None, by_id=None, p3_only=False):
    """judge_pair for every line; returns {pair_key: (items, findings)}. ``t4h_dirs`` = the rev11 R11-2
    search folders of the result file (None: no T4h reading, configuration only); ``t4h_log`` counts the
    lookup status (``ok``, ``no_t4h_file``, ``not_found``, ``several``). R4: ``by_id`` receives
    {id(line): items} of the lines judged with a V0 partner (the RD-7 scan reuses their J-P3 / J11);
    ``p3_only``: the T4h lookup only on lines whose tag is 3 on (H-9 main / pressure_only lines)."""
    out = {}
    for ln in lines:
        pk = v5j.pair_key(ln["job"])
        v0 = v0_idx.get(pk)
        if v0 is None:
            f = core.Findings()
            f.undec(where, f"no V0 partner for {pk}")
            out[(setting(ln), pk)] = ({}, f)
            continue
        f_t4h, rod, ok = core.Findings(), None, True
        if t4h_dirs is not None and (not p3_only or is_p3_line(v5j, is_p3, ln)):
            # rev11 R11-2 3 / rev12 R12-1: recorded t4h_file found 0 or 2+ = S-2
            rod, ok = cm.jp3_rod_input(f_t4h, f"{where}|{pk}", ln, t4h_dirs, v5j, None,
                                       t4h_log if t4h_log is not None else {})
        items, f = v5j.judge_pair(ln, v0, nrev.get(v5j.row_key(ln["job"])), is_p3, rod)
        if not ok:
            cm.strip_jp3(items, f)
        for s in f_t4h.stops:
            f.stop(s["code"], s["where"], s["why"])
        if setting(ln) in ("VB",) + LS_SETTINGS:   # rev8 R8-2: non-3 tag = J-P3 not applicable + S-2
            cm.jp3_tag_scope(f, f"{where}|{pk}", items.get("J-P3", {}).get("result"), setting(ln))
        out[(setting(ln), pk)] = (items, f)
        if by_id is not None:
            by_id[id(ln)] = items
    return out


def rd_scan(v5j, core, is_p3, rd, bundle, rfile, lines, nums, judged_by_id, dirs, fx, t4h_log):
    """R4 RD-7 / RD-8 / RD-9 / RD-10 over every line of one result file of ``bundle`` (position ``line N``, key
    ``job.case``, setting ``job.setting``, RD-7 3). Lines judged by ``judge_pair`` reuse its J-P3 / J11 items;
    the other lines (V0 partners, pressure_only, U-9 VB of H-10, lines without a V0 partner) get J-P3 (3-on tag or
    a 3-on setting VB / LS) and J11 here, with their findings on ``fx``."""
    for ln, n in zip(lines, nums):
        pos = f"line {n}"
        key = core.dig(ln, "job.case", None)
        key = key if isinstance(key, str) else None
        st = setting(ln) if isinstance(setting(ln), str) else None
        p3 = is_p3_line(v5j, is_p3, ln)
        rd.line(bundle, p3)
        items = judged_by_id.get(id(ln))
        if items:
            res, why = (items.get("J-P3") or {}).get("result"), (items.get("J-P3") or {}).get("why")
            j11 = items.get("J11")
        else:
            where = f"{bundle}|{rfile}|{pos}"
            res = why = None
            if p3 or st in ("VB",) + LS_SETTINGS:
                rod, ok = cm.jp3_rod_input(fx, where, ln, dirs, v5j, None, t4h_log)
                res, why = v5j.jp3(ln, is_p3, rod) if ok else ("t4h_unresolved", "R12-1 S-2")
                if ok:
                    cm.jp3_apply(fx, where, res, why, st if st in ("VB",) + LS_SETTINGS else None)
            j11 = v5j.j11_item(ln)
            v5j.apply_j11(j11, where, fx)
        if res is not None:
            rd.jp3_result(bundle, res, why)
        if res == "H-7":
            rd.jp3 += cm.jp3_rows(bundle, rfile, pos, ln, key, st, core)
        if isinstance(j11, dict):
            rd.j11_result(bundle, j11)
            rd.j11 += cm.j11_rows(bundle, rfile, pos, j11, key, st)


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
    # rev11 R11-2 1 / 2: search folders of the --h10 file (input error = S-11, bundles not judged)
    places, perr = v5j.t4h_places([args.h10], args.t4h_root)
    if places is None:
        body, st = cm.t4h_input_error(perr)
        body.update(inputs={"h9": args.h9, "h10": args.h10, "t4h_root": args.t4h_root},
                    not_judged=["H-10", "H-9_stage1"], grades_436_8={"H-10": "멈춤", "H-9_stage1": "멈춤"})
        return body, st
    t4h_dirs = places[str(args.h10)]
    t4h_log, t4h_log9 = {}, {}
    # R4: H-9 main / pressure_only lines whose tag is 3 on read a recorded T4h only from the runner convention
    # folders of --h9 (rev12 R12-1 for every T4h read; --t4h-root belongs to --h10)
    dirs9 = v5j.t4h_convention_dirs(args.h9)
    h9, nums9 = cm.read_jsonl_numbered(args.h9)      # RD-7 3: physical line numbers
    h10, nums10 = cm.read_jsonl_numbered(args.h10)
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
    # R4 (rev16:103 = P2-14, RD-10): the J11 of V0 lines is a record (the old V0 n_late_fallback H-7 stop is
    # removed); every line's J11 is ``p2_v5j.j11_item`` (in judge_pair, or in rd_scan below)
    by_id = {}
    j9 = judge_all(v5j, core, [x for x in main9 if setting(x) != "V0"], v0_idx, nrev, is_p3, dirs9, "h9",
                   t4h_log9, by_id, p3_only=True)
    j10 = judge_all(v5j, core, main10 + [x for x in it8 if setting(x) != "V0"], v0_idx, nrev, is_p3,
                    t4h_dirs, "h10", t4h_log, by_id)
    ov_idx = index_by_pair(v5j, v0_ov, "overlap V0", f10)
    jov = judge_all(v5j, core, [x for x in ov if setting(x) != "V0"], ov_idx, nrev, is_p3, t4h_dirs, "ov",
                    t4h_log, by_id)
    # R4 RD-7 / RD-8 / RD-9 / RD-10 over every line of the two result files (H-9 main + pressure_only, H-10)
    rd = cm.RdCounter(core.bundle_key)   # supplement 3-5: bundle order by p2_4368.bundle_key
    rd_scan(v5j, core, is_p3, rd, "H-9", cm.rel_file(args.h9, repo), h9, nums9, by_id, dirs9, f9, t4h_log9)
    rd_scan(v5j, core, is_p3, rd, "H-10", cm.rel_file(args.h10, repo), h10, nums10, by_id, t4h_dirs, f10, t4h_log)
    if rd.p3.get("H-10", 0) == 0:   # RD-9: H-10 has VB (3-on) lines by definition; 0 = S-8
        f10.stop("S-8", "H-10|RD-9", "no 3-on line in H-10 (original 8.2 S-8, R4 RD-9)")
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
        for u in f.undecidable:   # R4 RD-8: a 3-on line's J-P3 undecidable stays undecidable on H-9
            if str(u["why"]).startswith("J-P3"):
                f9.undec(f"{s}|{u['where']}"[:200], u["why"])
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
        "R11-2_t4h": {"search_dirs": [str(d) for d in t4h_dirs], "lookup": t4h_log,
                      "h9_search_dirs": [str(d) for d in dirs9], "h9_lookup": t4h_log9},
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
        # R4: RD-7 J-P3 / J11 rows of H-9 (main + pressure_only part; the grid part is in the grid output and the
        # two are merged by ``merge``) and H-10, RD-8 / RD-9 / RD-10 counts (H-9 S-8 on the sum in ``merge``), RD-13
        "R4": rd.as_dict(["H-9", "H-10"]),
        "RD-13": {b: cm.rd13_lists()[b] for b in ("H-9", "H-10")},
    }
    g = {"H-10": f10.status(), "H-9_stage1": f9.status()}
    body["grades_436_8"] = {k: {"pass": "통과", "fail": "미달", "undecidable": "판정 불가", "stop": "멈춤"}[v]
                            for k, v in g.items()}
    body["stop_codes"] = sorted(set(f10.as_dict()["stop_codes"]) | set(f9.as_dict()["stop_codes"]))
    status = "stop" if "stop" in g.values() else ("undecidable" if "undecidable" in g.values() else (
        "fail" if "fail" in g.values() else "pass"))
    return body, status


MERGE_TOOLS = {"p2v5c_noise.py": ("H-6", "H-8"), "p2v5c_stage1.py": ("H-9", "H-10"), "p2v5c_grid.py": ("H-9",)}


def cmd_merge(args, repo, v5j, core):
    """R4 RD-7 / RD-9 / RD-8 / RD-10 / RD-13 of this folder in one file: the three finished tool outputs
    (noise, stage1, grid) of the same checkout are collated. H-9 = stage1 rows (main + pressure_only) + grid rows,
    re-sorted by RD-7 3; RD-9 S-8 on each bundle count (H-9 on the sum). Nothing is re-judged here.
    Input checks (else not merged): one output of each tool (S-11), each with an ``R4`` block (S-11), its
    ``tool_sha256`` / ``common_sha256`` equal to the files of this checkout (S-11) and its HEAD equal to this
    run's HEAD (S-12)."""
    fnd = core.Findings()
    here = Path(__file__).resolve().parent
    parts, by_tool = [], {}
    for p in args.part:
        d = json.loads(Path(p).read_text("utf-8"))
        t = d.get("tool")
        rec = {"path": p, "sha256": cm.sha256_file(p), "tool": t, "status": d.get("status"),
               "stop_codes": d.get("stop_codes"), "tool_sha256": d.get("tool_sha256"),
               "head": (d.get("head_check") or {}).get("head")}
        parts.append(rec)
        if t not in MERGE_TOOLS or t in by_tool:
            fnd.stop("S-11", p, f"tool {t!r}: one output of each of {sorted(MERGE_TOOLS)} is needed")
            continue
        by_tool[t] = d
        if not isinstance(d.get("R4"), dict):
            fnd.stop("S-11", p, f"no R4 block (status {d.get('status')}, stop codes {d.get('stop_codes')})")
        if d.get("tool_sha256") != cm.sha256_file(here / t) or d.get("common_sha256") != cm.sha256_file(here / "p2v5c_common.py"):
            fnd.stop("S-11", p, "tool / common sha256 differ from the files of this checkout")
        if rec["head"] != args.expect_head.lower():
            fnd.stop("S-12", p, f"output HEAD {rec['head']} != {args.expect_head}")
    if set(by_tool) != set(MERGE_TOOLS):
        fnd.stop("S-11", "parts", f"missing outputs {sorted(set(MERGE_TOOLS) - set(by_tool))}")
    if fnd.stops:
        return {"parts": parts, "not_merged": True, **fnd.as_dict()}, "stop"
    bundles = cm.RD7_BUNDLES
    lists = {"J-P3": {b: [] for b in bundles}, "J11": {b: [] for b in bundles}}
    rd9 = {b: {"p3_on": 0, "scanned": 0} for b in bundles}
    rd8 = {b: {"format": 0, "top_level_mismatch": 0} for b in bundles}
    rd10 = {b: {"undecidable": 0, "input_missing": 0} for b in bundles}
    for t, d in by_tool.items():
        r4 = d["R4"]
        for b in MERGE_TOOLS[t]:
            for li in ("J-P3", "J11"):
                lists[li][b] += r4["RD-7"][li].get(b, [])
            for k in ("p3_on", "scanned"):
                rd9[b][k] += r4["RD-9"][b][k]
            for k in ("format", "top_level_mismatch"):
                rd8[b][k] += r4["RD-8"][b][k]
            for k in ("undecidable", "input_missing"):
                rd10[b][k] += r4["RD-10"][b][k]
        for b, item in (d.get("RD-13") or {}).items():
            if item.get("sha256") != cm.rd13_lists()[b]["sha256"]:
                fnd.stop("S-11", t, f"RD-13 list of {b} differs from this checkout")
    out_lists = {li: {b: cm.rd7_sort(v, core.bundle_key) for b, v in per.items()} for li, per in lists.items()}
    for b in bundles:
        if rd9[b]["p3_on"] == 0:
            fnd.stop("S-8", f"{b}|RD-9", "no 3-on line / run in the bundle (original 8.2 S-8, R4 RD-9)")
    markers = {b: cm.rd7_markers(out_lists["J-P3"][b], out_lists["J11"][b]) for b in bundles}
    for b, ms in markers.items():
        for m in ms:
            fnd.stop(m.replace("멈춤 ", ""), f"{b}|RD-7", f"{m}: see the RD-7 list of {b}")
    rd13 = cm.rd13_lists()
    body = {"parts": parts, "bundles": list(bundles),
            "RD-7": out_lists,
            "RD-7_sha256": {li: {b: cm.canon_sha(v) for b, v in per.items()} for li, per in out_lists.items()},
            "markers": markers, "RD-8": rd8, "RD-9": rd9, "RD-10": rd10,
            "RD-13": rd13, "RD-13_sha256": {b: v["sha256"] for b, v in rd13.items()},
            **fnd.as_dict()}
    return body, fnd.status()


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    cm.add_common_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mg = sub.add_parser("merge", help="R4 RD-7 / RD-9 / RD-8 / RD-10 / RD-13 of the noise, stage1 and grid outputs")
    mg.add_argument("--part", action="append", required=True,
                    help="finished output JSON of p2v5c_noise.py noise / p2v5c_stage1.py stage1 / p2v5c_grid.py grid")
    s = sub.add_parser("stage1")
    s.add_argument("--h9", required=True, help="resume_k1/h9_stage1.jsonl")
    s.add_argument("--h10", required=True, help="resume_k1/h10_reuse_rerun.jsonl")
    s.add_argument("--t4h-root", action="append", default=None,
                   help="T4h folder of the H-10 lines (rev9 3.1). 436.8 rev11 R11-2: the convention folders "
                        "<h10 stem>_t4h/ and t4h/ next to --h10 are used; another folder only when none "
                        "exists, at most one (else input error, S-11, exit 2)")
    s.add_argument("--overlap-ta", default=None, help="resume_k1/h10_overlap_t_a.json (record)")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser,
                       {"stage1": cmd_stage1, "merge": cmd_merge})


if __name__ == "__main__":
    sys.exit(main())
