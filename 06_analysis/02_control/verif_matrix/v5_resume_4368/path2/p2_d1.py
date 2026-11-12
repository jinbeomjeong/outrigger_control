"""Path-2 recount of H-1 (D-1 harness) and re-selection H-2, 436.8 v5 resume.

Rules: ``d1_selection_rules.md`` (sha256 51dea528...) + ``d1_selection_rules_rev1.md`` (eb730bdd...), with the
436.8 rules (9019b405...) / rev1 (d9094fda...) that make them the H-1 / H-2 rules (436.8 5.1, 7.1). Author:
dynamics-expert (path 2); 436.8 rev3 (dad8dfa6...) R3-A1 (G-3 exception = ASSUMED_BOUNDARY tag), R3-A2 (three
layers: re-judge, re-aggregate d1.verdict, re-select), R3-A3 (READY origin and t_READY cross-check). Written from the rule sentences and the jsonl records only; the path-1 tools
(run_v5 judgement block, d1_select.py, resume4368_judge.py) were not opened (436.8 9.2).

What it does (rule section in brackets):
  * gates G-1 (run errors 0, counts 420 / 424 / 24 runs, 105 / 106 / 6 combinations), G-2 (section-3 fields
    on every run), G-3 (judge row VB fail with the same-key V0 pass; S2 fup-rec excepted), G-4 (VB J-P3 has
    no setting defect and no H-7)  [10]
  * margins m_F, m_T, m_a, m_s and m  [4.1]; candidate grade / m  [4.2]; ranking and ties  [4.3]
  * S1 C2-03 / C2-07 roll sign  [5], S2 S-01 / S-02 soft slope with the fup-rec rule  [6],
    S3 D1-PSC triggers T1..T3  [7], baseline-failure second row  [4.3]
  * crawler x3 transfer rule 1 / 2 / 3 on the H-R-0 2x2, for m and for each term  [8]
  * path-2 cross-check of the recorded run verdict where the sealed text defines the item from recorded
    harness values (H-R: D8 F after lift-off, end attitude, READY, moving <= 180 bar, FAULT 0); the READY
    limit is recomputed from rev1 1 (spec 421.1 wording)  [11, rev1 1]

The per-run grade used for ranking is the section-3 input ``d1.verdict`` (the rules define the selection on
that field). The cross-check reports every run where a recounted item contradicts it (two-path grade
difference candidate, 436.8 S-13).

Exit codes: 0 selection done, 1 a gate stop (G-1 / G-3 / G-4) or a cross-check difference, 2 missing input
(G-2) or a rules sha mismatch, 3 tool error. Last stdout line: JSON summary with out_sha256.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import functools
import importlib.util
import json
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p2_4368_core", _HERE / "p2_4368.py")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

TOOL_NAME = "p2_d1.py"
TOOL_VERSION = "1"
D1_RULES = {
    "06_analysis/02_control/verif_matrix/d1_selection_rules.md":
        "51dea528e57fa0c4378cda110addb73da20339535e16189452af2d06b60736e9",
    "06_analysis/02_control/verif_matrix/d1_selection_rules_rev1.md":
        "eb730bddae35e76bc2569503605dea714b066fa42de7bc7b98efdde3edb3e868",
}

F_MIN = core.F_MIN_N
S_END = 0.6848              # 1: stroke end
ATT_LIM = 0.2               # 4.1
MOVING_BAR = 180.0          # 11 D8.P
TIE_M = 1e-3                # 4.3 / 13
TIE_F_N = 1.0
TIE_S_M = 1e-4
T3_F = 1.1 * F_MIN          # 7 T3 / 13 (10.36 kN)
T3_A = 0.15
T3_S = 0.6428
GRADE_ORDER = {"fail": 0, "allowed_stop": 1, "pass": 2}
JUDGE_GROUPS = {"H-R-0", "H-R-A", "H-S-0", "H-S-1", "H-S-A", "H-S-C"}
FIELDS = ("key", "verdict", "fail_items", "F_judged_min_N", "F_first_level_min_N", "t_ready_s",
          "t_ready_limit_s", "att_judged_deg", "stroke_max_m", "imu_R_c", "dsb75_events", "j_p3")
G1_COUNTS = {"H-R": (105, 420), "H-S": (106, 424), "H-S-C-g": (6, 24)}
J_P3_OK = {"pass", "no_rod_reading", "not_applicable"}   # 3: pass / H-7 / no_rod_reading / setting defect
LEVEL_TAG = {"top": "T", "middle": "M", "bottom": "B"}
S1_CELLS = {"C2-03": "middle", "C2-07": "bottom"}
S1_SIGNS = {"roll+op": "D1C2_{lv}_roll4.4_Fs4", "roll-op": "D1C2_{lv}_rollm4.4_Fs4"}
S2_CELLS = {"S-01": "middle", "S-02": "bottom"}
S2_SLOPES = {"diag-rec": "D1S_J1_B_{lv}_Fs4_r1p925_p1p4", "roll-rec": "D1S_J1_B_{lv}_Fs4_rm2p64_p0",
             "fup-rec": "D1S_J1_B_{lv}_Fs4_r0_pm2p8"}
S3_PROFILES = [("FL", "c-slow"), ("FL", "c-mid"), ("FL", "c-edge"), ("FL", "c-fast"), ("RL", "c-mid")]
R8_CELLS = [("top", "flat"), ("top", "diag-op"), ("bottom", "flat"), ("bottom", "diag-op")]
ASSUMED_BOUNDARY = "ASSUMED_BOUNDARY"   # rev3 R3-A1: the G-3 exception = rows carrying this tag
SLS_ALLOWED = {"H-R-A", "H-S-0", "H-S-1", "H-S-A"}   # 11: rows whose definition allows stroke_limited_stop
ORIGIN_MAX_S = 0.1                      # rev3 R3-A3: the first phase (CHECK) starts within one period
PHASE_START_PATHS = ("values.times.t_check_start_s", "values.phases", "phases", "values.phase_starts_s",
                     "phase_starts_s")


# ----------------------------------------------------------------- run normalisation
def ready_limit_path2(job_d1):
    """rev1 1: slope 120 s; H-R flat 90 s; H-S flat + pad B + uniform J1 / J2 / S1 100 s, other flat 90 s."""
    flat = job_d1.get("roll_deg") == 0.0 and job_d1.get("pitch_deg") == 0.0
    if not flat:
        return 120.0
    if job_d1["group"].startswith("H-R"):
        return 90.0
    uniform = job_d1.get("base") in ("J1", "J2", "S1") and job_d1.get("patch_leg") in (None, "")
    return 100.0 if uniform else 90.0


def norm_run(rec):
    j = rec["job"]
    jd = j["d1"]
    d = rec.get("d1") or {}
    run = {"row": jd["key"], "group": jd["group"], "level": jd["level"], "slope": jd["slope_name"],
           "base": jd.get("base"), "K": jd.get("crawler_k_scale"), "sink": jd.get("sink"),
           "patch_leg": jd.get("patch_leg"), "tags": jd.get("tags") or [], "setting": j.get("setting"),
           "eps": j.get("eps"), "d1": d, "values": rec.get("values") or {}, "final_phase": rec.get("final_phase"),
           "error": rec.get("error"), "raw": {k: rec[k] for k in ("values", "phases", "phase_starts_s") if k in rec}}
    run["T_lim_p2"] = ready_limit_path2(jd)
    run["missing"] = [f for f in FIELDS if f not in d]
    return run


def margins(run):
    """4.1 margins from the section-3 fields; T_lim from the path-2 READY limit (rev1 1)."""
    d = run["d1"]
    F, t, a, s = d.get("F_judged_min_N"), d.get("t_ready_s"), d.get("att_judged_deg"), d.get("stroke_max_m")
    T = run["T_lim_p2"]
    mF = None if F is None else (F - F_MIN) / F_MIN
    mT = None if (t is None or run["group"] == "H-S-C") else (T - t) / T
    ma = None if a is None else (ATT_LIM - a) / ATT_LIM
    ms = None if s is None else (S_END - s) / S_END
    terms = {"m_F": mF, "m_T": mT, "m_a": ma, "m_s": ms}
    present = [v for v in terms.values() if v is not None]
    m = min(present) if present else None
    return m, terms


# ----------------------------------------------------------------- path-2 cross-check of the run verdict
def crosscheck(run):
    """Items the sealed text defines from recorded harness values (11 H-R D8.P)."""
    if run["group"] not in ("H-R-0", "H-R-A"):
        return None
    v = run["values"]
    out = {}
    fl = core.dig(v, "forces.after_liftoff.min_kN", None)
    out["D8_F_after_liftoff"] = None if fl is None else bool(core.t_ge(fl * 1e3, F_MIN))
    ea = core.dig(v, "attitude.end_abs_deg", None)
    if isinstance(ea, dict) and ea.get("roll") is not None and ea.get("pitch") is not None:
        out["D8_end_attitude"] = not core.t_gt(max(abs(ea["roll"]), abs(ea["pitch"])), ATT_LIM)
    else:
        out["D8_end_attitude"] = None
    tr = core.dig(v, "times.t_first_ready_s")       # None = no READY (a real value), MISSING = no key
    out["READY"] = None if tr is core.MISSING else (tr is not None and not core.t_gt(tr, run["T_lim_p2"]))
    mb = core.dig(v, "pressure.max_moving_bar", None)
    out["moving_180bar"] = None if mb is None else not core.t_gt(mb, MOVING_BAR)
    fe = core.dig(v, "events.fault_events", None)
    out["FAULT0"] = None if not isinstance(fe, list) else len(fe) == 0
    rec_items = run["d1"].get("items") or {}
    diffs = [k for k, x in out.items() if x is not None and k in rec_items and bool(rec_items[k]) != x]
    fj = run["d1"].get("F_judged_min_N")
    if fl is not None and fj is not None and abs(fl * 1e3 - fj) > 1.0:   # values are kN rounded to 0.1 N
        diffs.append("F_judged_min_N vs forces.after_liftoff")
    # a recounted failing item with a recorded 'pass' verdict is a grade difference
    grade_conflict = run["d1"].get("verdict") == "pass" and any(x is False for x in out.values())
    return {"items": out, "item_diffs": diffs, "grade_conflict": grade_conflict}


def reaggregate(run):
    """rev3 R3-A2 layer 2: rebuild ``d1.verdict`` from the recorded item results with the allowed_stop rule
    (3, 54) and the demotion rules (11: 377 / 424.11.2). A false item missing from ``fail_items`` must carry a
    recorded demotion (a field whose name contains "demot"); otherwise the line is undecidable."""
    d = run["d1"]
    items = d.get("items") if isinstance(d.get("items"), dict) else None
    fails = d.get("fail_items")
    if items is None or not isinstance(fails, list):
        return {"status": "inputs missing"}
    false_items = {k for k, v in items.items() if v is False}
    demoted = false_items - set(fails)
    demot_fields = [k for k in list(d) + list(items) if "demot" in str(k).lower()]
    if demoted and not demot_fields:
        return {"status": "false item without fail_items entry or demotion record", "items": sorted(demoted)}
    cls = d.get("harness_class")
    if cls == "stroke_limited_stop" and run["group"] in SLS_ALLOWED:
        rebuilt = "allowed_stop"     # 3, 54: that termination on a row that allows it (fail items = record)
    elif fails:
        rebuilt = "fail"
    else:
        rebuilt = "pass"
    if rebuilt != d.get("verdict"):
        return {"status": "rebuilt verdict differs", "rebuilt": rebuilt, "recorded": d.get("verdict")}
    return {"status": "same", "rebuilt": rebuilt, "demoted": sorted(demoted)}


def phase_start(rec):
    """Earliest phase start time from the line's phase record (several accepted shapes); None if absent."""
    for p in PHASE_START_PATHS:
        v = core.dig(rec, p, None)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        starts = []
        if isinstance(v, dict):
            starts = [core.num(x) for x in v.values()]
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, (list, tuple)) and len(x) >= 2:
                    starts.append(core.num(x[1]) if core.num(x[1]) is not None else core.num(x[0]))
                elif isinstance(x, dict):
                    starts.append(core.num(x.get("t_start_s", x.get("t_s"))))
        starts = [s for s in starts if s is not None]
        if starts:
            return min(starts)
    return None


def ready_check(run):
    """rev3 R3-A3: t_READY = values.times.t_first_ready_s (closed-loop origin), origin = first phase start
    <= 0.1 s, and d1.t_ready_s equal within the 7.6 tolerance."""
    tr = core.dig(run["values"], "times.t_first_ready_s")
    if tr is core.MISSING:
        return {"status": "values.times.t_first_ready_s missing"}
    t0 = phase_start(run["raw"])
    if t0 is None:
        return {"status": "phase record missing (origin not checkable)"}
    if core.t_gt(t0, ORIGIN_MAX_S):
        return {"status": f"first phase starts at {t0} s > 0.1 s"}
    dr = run["d1"].get("t_ready_s")
    if (tr is None) != (dr is None) or (tr is not None and abs(tr - dr) > core.EPS_THR):
        return {"status": "d1.t_ready_s differs from t_READY", "t_ready": tr, "d1_t_ready_s": dr}
    return {"status": "ok"}


# ----------------------------------------------------------------- candidates and ranking (4.2, 4.3)
def candidate(name, runs):
    if not runs:
        return {"name": name, "runs": 0, "grade": None, "m": None}
    scored = []
    for r in runs:
        m, terms = margins(r)
        scored.append((r, m, terms))
    grade = min((r["d1"]["verdict"] for r, _, _ in scored), key=lambda g: GRADE_ORDER[g])
    ms = [x for x in scored if x[1] is not None]
    best = min(ms, key=lambda x: x[1]) if ms else scored[0]
    r0 = best[0]
    return {"name": name, "runs": len(runs), "grade": grade, "m": best[1],
            "tie_F_first_level_min_N": r0["d1"].get("F_first_level_min_N"),
            "tie_stroke_max_m": r0["d1"].get("stroke_max_m"), "tie_eps": r0["eps"],
            "min_run": {"row": r0["row"], "setting": r0["setting"], "eps": r0["eps"], "terms": best[2]},
            "run_values": [{"row": r["row"], "K": r["K"], "eps": r["eps"], "grade": r["d1"]["verdict"], "m": m,
                            "terms": t} for r, m, t in scored],
            "fail_runs": [r for r, _, _ in scored if r["d1"]["verdict"] == "fail"]}


def cmp_candidates(a, b):
    ga, gb = GRADE_ORDER[a["grade"]], GRADE_ORDER[b["grade"]]
    if ga != gb:
        return -1 if ga < gb else 1
    if abs(a["m"] - b["m"]) >= TIE_M:
        return -1 if a["m"] < b["m"] else 1
    fa, fb = a["tie_F_first_level_min_N"], b["tie_F_first_level_min_N"]
    if fa is not None and fb is not None and abs(fa - fb) >= TIE_F_N:
        return -1 if fa < fb else 1
    sa, sb = a["tie_stroke_max_m"], b["tie_stroke_max_m"]
    if sa is not None and sb is not None and abs(sa - sb) >= TIE_S_M:
        return -1 if sa > sb else 1
    ea, eb = a["tie_eps"] == 0.0, b["tie_eps"] == 0.0
    if ea != eb:
        return -1 if ea else 1
    return -1 if a["name"] < b["name"] else (1 if a["name"] > b["name"] else 0)


def rank(cands):
    return sorted(cands, key=functools.cmp_to_key(cmp_candidates))


def v0_twin_fails(cand, by_key):
    """4.3 baseline failure: every VB 'fail' run of the candidate has a same-key V0 run that is 'fail' too."""
    fr = cand.get("fail_runs") or []
    if cand["grade"] != "fail" or not fr:
        return False
    for r in fr:
        tw = by_key.get((r["row"], "V0", r["eps"]))
        if tw is None or tw["d1"].get("verdict") != "fail":
            return False
    return True


def select_cell(cands, by_key):
    order = rank([c for c in cands if c["grade"] is not None])
    chosen = [order[0]["name"]] if order else []
    baseline = bool(order) and v0_twin_fails(order[0], by_key)
    if baseline and len(order) > 1:
        chosen.append(order[1]["name"])
    return chosen, baseline, [c["name"] for c in order]


def strip(c):
    return {k: v for k, v in c.items() if k != "fail_runs"}


# ----------------------------------------------------------------- crawler x3 rule (8)
def rule8(runs):
    out = {}
    for lv, slope in R8_CELLS:
        cell = {}
        mh = {}
        for P in ("V0", "VB"):
            for k in (1.0, 3.0):
                rs = [r for r in runs if r["group"] == "H-R-0" and r["level"] == lv and r["slope"] == slope
                      and r["setting"] == P and r["K"] == k]
                mh[(P, k)] = {r["eps"]: margins(r) for r in rs}
        res = {}
        for term in ("m", "m_F", "m_T", "m_a", "m_s"):
            def val(P, k, e):
                x = mh[(P, k)].get(e)
                if x is None:
                    return None
                return x[0] if term == "m" else x[1][term]
            ok = all(val(P, k, e) is not None for P in ("V0", "VB") for k in (1.0, 3.0) for e in (0.0, 2e-3))
            if not ok:
                res[term] = {"rule": None, "why": "missing run or term"}
                continue
            bar = {(P, k): 0.5 * (val(P, k, 0.0) + val(P, k, 2e-3)) for P in ("V0", "VB") for k in (1.0, 3.0)}
            sig = max(abs(val(P, k, 0.0) - val(P, k, 2e-3)) for P in ("V0", "VB") for k in (1.0, 3.0))
            res[term] = rule8_decide(bar, sig)
        cell.update(res)
        out[f"{LEVEL_TAG[lv]}|{slope}"] = cell
    return out


def rule8_decide(bar, sig):
    d0 = bar[("V0", 3.0)] - bar[("V0", 1.0)]
    db = bar[("VB", 3.0)] - bar[("VB", 1.0)]
    i = db - d0
    r = {"mbar": {f"{P},{int(k)}": v for (P, k), v in bar.items()}, "Delta_V0": d0, "Delta_VB": db, "I": i,
         "sigma_j": sig}
    if db != 0 and d0 != 0 and (db > 0) == (d0 > 0) and abs(i) <= 0.5 * max(abs(db), abs(d0)) + core.EPS_THR:
        r.update(rule=1, text="transfer", offset=bar[("VB", 3.0)] - bar[("V0", 3.0)])
    elif abs(db) < sig and abs(d0) < sig:
        r.update(rule=2, text="crawler stiffness no effect")
    else:
        r.update(rule=3, text="VB crawler sensitivity undetermined")
    return r


# ----------------------------------------------------------------- S3 (7)
def s3(runs):
    rows = []
    trig = {}
    for leg, prof in S3_PROFILES:
        rs = [r for r in runs if r["group"] == "H-S-C" and r["base"] == "J1" and r["level"] == "top"
              and r["slope"] == "flat" and r["setting"] == "VB" and isinstance(r["sink"], dict)
              and r["sink"].get("name") == prof and r["sink"].get("leg") == leg]
        holds = [sum(1 for e in (r["d1"].get("dsb75_events") or []) if e.get("name") == "INFO_DIFF_SINK_HOLD")
                 for r in rs]
        t1 = any(r["d1"]["verdict"] == "fail" for r in rs)
        if prof == "c-slow":
            t2 = any(h >= 1 for h in holds)
        elif prof in ("c-mid", "c-fast"):
            t2 = len(rs) > 0 and all(h == 0 for h in holds)
        else:
            t2 = False
        t3 = any((r["d1"].get("F_judged_min_N") is not None and core.t_lt(r["d1"]["F_judged_min_N"], T3_F))
                 or (r["d1"].get("att_judged_deg") is not None and core.t_gt(r["d1"]["att_judged_deg"], T3_A))
                 or (r["d1"].get("stroke_max_m") is not None and core.t_gt(r["d1"]["stroke_max_m"], T3_S))
                 for r in rs)
        tag = prof.replace("-", "")
        name = f"D1PSC_J1_B_top_Fs4_{leg}_{tag}"
        trig[name] = {"runs": len(rs), "T1": t1, "T2": t2, "T3": t3, "holds": holds,
                      "F_min_N": min((r["d1"].get("F_judged_min_N") for r in rs if r["d1"].get("F_judged_min_N") is not None), default=None),
                      "a_max_deg": max((r["d1"].get("att_judged_deg") for r in rs if r["d1"].get("att_judged_deg") is not None), default=None),
                      "s_max_m": max((r["d1"].get("stroke_max_m") for r in rs if r["d1"].get("stroke_max_m") is not None), default=None)}
        if len(rs) != 2:
            trig[name]["note"] = f"{len(rs)} runs (2 expected)"
        if t1 or t2 or t3:
            rows.append(name)
            base = f"D1PSC_J1_B_top_Fs4_sp{leg}J1_base"
            if base not in rows:
                rows.append(base)
    return {"triggers": trig, "rows": rows, "omitted": not rows}


# ----------------------------------------------------------------- main recount
def recount(runs, errors):
    fnd = core.Findings()
    by_key = {(r["row"], r["setting"], r["eps"]): r for r in runs}
    # G-1
    if errors:
        fnd.stop("G-1", "runs", f"{errors} run(s) with error")
    fam = {"H-R": [r for r in runs if r["group"].startswith("H-R")],
           "H-S": [r for r in runs if r["group"].startswith("H-S") and r["group"] != "H-S-C-g"],
           "H-S-C-g": [r for r in runs if r["group"] == "H-S-C-g"]}
    g1 = {}
    for f, (nc, nr) in G1_COUNTS.items():
        combos = {(r["row"]) for r in fam[f]}
        g1[f] = {"runs": len(fam[f]), "combos": len(combos), "want": [nc, nr]}
        if len(fam[f]) != nr or len(combos) != nc:
            fnd.stop("G-1", f, f"{len(combos)} combinations / {len(fam[f])} runs, rules say {nc} / {nr}")
    # G-2
    miss = [(r["row"], r["setting"], r["eps"], r["missing"]) for r in runs if r["missing"]]
    if miss:
        fnd.stop("G-2", "fields", f"{len(miss)} run(s) lack section-3 fields, e.g. {miss[:3]}")
        return {"gates": {"G-1": g1, "G-2": len(miss)}, **fnd.as_dict()}, 2
    # G-3
    g3 = []
    for r in runs:
        if r["group"] in JUDGE_GROUPS and r["setting"] == "VB" and r["d1"]["verdict"] == "fail":
            tw = by_key.get((r["row"], "V0", r["eps"]))
            if tw is not None and tw["d1"]["verdict"] == "pass":
                # 10 G-3 "exception: 6 fup-rec" read as every fup-rec row (ASSUMED_BOUNDARY, 11) - confirm
                exc = ASSUMED_BOUNDARY in r["tags"]                      # rev3 R3-A1
                g3.append({"row": r["row"], "eps": r["eps"], "exception_fup_rec": exc})
                if exc:
                    fnd.note(r["row"], "가정 경계 미성립 (G-3 예외, R3-A1): 앞들림 경계 재결정을 사용자에게 묻는다")
                if not exc:
                    fnd.stop("G-3", r["row"], f"VB fail, same-key V0 pass (eps {r['eps']})")
    # G-4
    g4 = [(r["row"], r["eps"], r["d1"]["j_p3"]) for r in runs if r["setting"] == "VB" and r["d1"]["j_p3"] not in J_P3_OK]
    for x in g4:
        fnd.stop("G-4", x[0], f"J-P3 = {x[2]!r} (eps {x[1]})")
    # S1
    s1 = {}
    for cell, lv in S1_CELLS.items():
        cands = []
        for slope, tmpl in S1_SIGNS.items():
            rs = [r for r in runs if r["group"] == "H-R-0" and r["level"] == lv and r["slope"] == slope and r["setting"] == "VB"]
            if len(rs) != 4:
                fnd.undec(cell, f"{slope}: {len(rs)} VB runs (4 expected)")
            cands.append(candidate(tmpl.format(lv=lv), rs))
        chosen, baseline, order = select_cell(cands, by_key)
        s1[cell] = {"chosen": chosen, "baseline_failure": baseline, "order": order, "candidates": [strip(c) for c in cands]}
    # S2
    s2 = {}
    for cell, lv in S2_CELLS.items():
        cands = []
        fup_excluded = False
        for slope, tmpl in S2_SLOPES.items():
            rs = [r for r in runs if r["group"] == "H-S-0" and r["base"] == "J1" and r["level"] == lv and r["slope"] == slope
                  and r["setting"] == "VB"]
            if len(rs) != 2:
                fnd.undec(cell, f"{slope}: {len(rs)} VB runs (2 expected)")
            c = candidate(tmpl.format(lv=lv), rs)
            if slope == "fup-rec" and c["grade"] == "fail":
                fup_excluded = True
                fnd.note(cell, "fup-rec harness fail: assumed boundary not met, ask the user (6)")
                c["excluded"] = "assumed boundary not met"
                s2.setdefault("_excluded", []).append(c["name"])
                cands.append(c)
                continue
            cands.append(c)
        chosen, baseline, order = select_cell([c for c in cands if not c.get("excluded")], by_key)
        s2[cell] = {"chosen": chosen, "baseline_failure": baseline, "order": order, "fup_rec_excluded": fup_excluded,
                    "candidates": [strip(c) for c in cands]}
    s2.pop("_excluded", None)
    # S3, rule 8
    s3r = s3(runs)
    r8 = rule8(runs)
    # rev3 R3-A1: the tag defines the exception; record where tag and (H-S-0, fup-rec) disagree
    tag_mismatch = sorted({r["row"] for r in runs
                           if (ASSUMED_BOUNDARY in r["tags"]) != (r["group"] == "H-S-0" and r["slope"] == "fup-rec")})
    if tag_mismatch:
        fnd.note("R3-A1", f"ASSUMED_BOUNDARY tag vs H-S-0 fup-rec differ on {len(tag_mismatch)} row(s)")
    # rev3 R3-A2 layer 2 (re-aggregation of d1.verdict) and R3-A3 (READY origin, t_READY cross-check)
    reagg, ready_x = [], []
    for r in runs:
        where = f"{r['row']}|{r['setting']}|{r['eps']}"
        ra = reaggregate(r)
        if ra["status"] != "same":
            reagg.append({"row": r["row"], "setting": r["setting"], "eps": r["eps"], **ra})
            fnd.undec(where, f"R3-A2 re-aggregation: {ra['status']} (S-13)")
        rx = ready_check(r)
        if rx["status"] != "ok":
            ready_x.append({"row": r["row"], "setting": r["setting"], "eps": r["eps"], **rx})
            fnd.undec(where, f"R3-A3 READY: {rx['status']}")
    # cross-check
    cc = []
    for r in runs:
        x = crosscheck(r)
        if x and (x["item_diffs"] or x["grade_conflict"]):
            cc.append({"row": r["row"], "setting": r["setting"], "eps": r["eps"], **x})
    if cc:
        fnd.fail("crosscheck", f"{len(cc)} run(s): recounted item differs from the recorded run verdict / items")
    lim = [(r["row"], r["setting"], r["eps"], r["d1"].get("t_ready_limit_s"), r["T_lim_p2"]) for r in runs
           if r["d1"].get("t_ready_limit_s") is not None and not core.same_value(r["d1"]["t_ready_limit_s"], r["T_lim_p2"])]
    if lim:
        fnd.fail("ready_limit", f"{len(lim)} run(s): recorded t_ready_limit_s differs from rev1 1, e.g. {lim[:3]}")
    tallies = {}
    for r in runs:
        k = f"{r['group']}|{r['setting']}"
        tallies.setdefault(k, {}).setdefault(r["d1"]["verdict"], 0)
        tallies[k][r["d1"]["verdict"]] += 1
    c2_rows = sorted({n for c in s1.values() for n in c["chosen"]} | {n for c in s2.values() for n in c["chosen"]})
    out = {"gates": {"G-1": g1, "G-2": 0, "G-3": g3, "G-4": g4}, "tallies": tallies, "S1": s1, "S2": s2, "S3": s3r,
           "rule8": r8, "crosscheck_differences": cc[:200], "n_crosscheck_differences": len(cc),
           "ready_limit_differences": lim[:200],
           "R3-A2": {"rejudged_items": ["D8_F_after_liftoff", "D8_end_attitude", "READY", "moving_180bar", "FAULT0"],
                     "reaggregated_only": "d1.items / d1.fail_items (H-S P3, G6, E; H-R locked_350bar, G6)",
                     "n_rejudge_differences": len(cc), "n_reaggregation_differences": len(reagg),
                     "reaggregation_differences": reagg[:200]},
           "R3-A3": {"n_ready_undecidable": len(ready_x), "examples": ready_x[:50]},
           "R3-A1_tag_mismatch_rows": tag_mismatch[:50],
           "C2_selected_rows": {"S1_S2": c2_rows, "PS-c": s3r["rows"],
                                "n_rows_selected": len(c2_rows) + len(s3r["rows"]),
                                "n_psc_rows": len(s3r["rows"])},
           **fnd.as_dict()}
    gate_stop = any(s["code"] in ("G-1", "G-3", "G-4") for s in fnd.stops)
    return out, (1 if (gate_stop or fnd.fails or fnd.undecidable) else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--h1", required=True, help="h1_d1.jsonl (868 runs)")
    args = ap.parse_args(argv)
    repo = Path(args.repo) if args.repo else _HERE.parents[4]
    tool_sha = core.sha256_file(Path(__file__))
    summary = {"tool": TOOL_NAME, "version": TOOL_VERSION, "tool_sha256": tool_sha,
               "core_sha256": core.sha256_file(_HERE / "p2_4368.py")}
    try:
        seals = core.check_seals(repo)
        d1s = {rel: core.sha256_file(repo / rel) if (repo / rel).is_file() else None for rel in D1_RULES}
        d1_ok = all(d1s[rel] == want for rel, want in D1_RULES.items())
        if not seals["ok"] or not d1_ok:
            report, code = {"seals": seals, "d1_rules": d1s, "status": "stop", "stop_codes": ["S-1"]}, 2
        else:
            runs, errors = [], 0
            for rec in core.read_jsonl(args.h1):
                if "error" in rec:
                    errors += 1
                    continue
                runs.append(norm_run(rec))
            report, code = recount(runs, errors)
            report["input"] = {"h1": str(args.h1), "sha256": core.sha256_file(args.h1), "runs": len(runs),
                               "errors": errors}
            report["d1_rules"] = d1s
        report.update(tool=TOOL_NAME, version=TOOL_VERSION, tool_sha256=tool_sha,
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"))
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = core.sha256_file(args.out)
        summary.update(exit=code, out=args.out, out_sha256=out_sha, stop_codes=report.get("stop_codes", []),
                       c2_rows=report.get("C2_selected_rows"))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
