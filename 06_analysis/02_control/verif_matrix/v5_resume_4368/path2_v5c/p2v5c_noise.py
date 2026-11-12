"""436.8 path 2: v5-criteria recount of the noise bundles H-6 (dg3 v4_on) and H-8 (noise VB / V0, seedext).

Layers (436.8 rev3 R3-E3, rev4 R4-A2 option c, R4-B2/B3/B6):

* recomputed from the run records (``recomputed``): level counts and S1-front-excluded n (rev3 #1~#3,
  423.1), one-sided Clopper-Pearson upper bounds by two roots (v5 10, rev3), the four L1 gate counts
  (R4-B3), dg3 135-key substitution and hash record (rev8 #6, RV1-3.2, R3-E4 top-level hash), seedext
  seeds 0~4 hash (rev6 9, H-15), the time / load conditions of 419.8 for an S-4 time-clause failure
  (first DONE = ``base.t_done_s`` checked against ``base.phase_path``, R4-B2), J-P3 / J9 / H-7.
* item values from the rule-designated judge, run by this path itself (R4-A2 c):
  ``04_scripts/03_control/s8/r79_sensor_judge.py judge|judge-merged <out> ... --s4-late-loc``. The tool
  file must have 0 commits in ``f46b5ab..GIT_AT_START`` (condition 1, else S-11); its outputs go to
  ``--judge-dir`` (this path's folder); path-1 outputs are not read (condition 3).
* re-aggregated here (``reaggregated``, condition 4): from the per-run item rows S-1..S-6 the line grade
  is rebuilt with 13.2 / 419.8 (``S4_late_loc``) and 423.1 independently of the judge's own ``pass``
  and tables; then L2 fail count / CP grade (H-10), L3 record, seedext k/25 / CP / Fisher phrase,
  H-6 grade (R4-B6). Every item that is re-aggregated (not recomputed) is listed in ``TABLE_REAGG``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402

TOOL_NAME = "p2v5c_noise.py"
TOOL_VERSION = "3"
JUDGE_REL = "04_scripts/03_control/s8/r79_sensor_judge.py"
SEAL_BASE = "f46b5ab"                                   # R4-A2 condition 1
RELATED_MODULES = ("04_scripts/03_control/s9/late_loc_rule.py",          # imported by the judge
                   "04_scripts/03_control/s8/r79_sensor_screen.py",       # R5-E examples
                   "04_scripts/03_control/s9/s9_slope_fix_candidates.py",
                   "04_scripts/03_control/s8/r79_L3L4_final.py")          # H-8 runner (cf88ea8, R5-E)
LATE_LOC_OPTION = "--s4-late-loc"                       # v5 13.2 / R4-A2 table
LEVEL_COUNTS = {"L1": 167, "L2": 835, "L3": 501}        # rev3 #1
H6_COUNTS = {"L2": 1, "L3": 134}                        # rev8 #6
SEEDEXT_KEYS, SEEDEXT_SEEDS, SEEDEXT_CHECK = 2, 25, 5   # rev6 9 (seeds 0~4 checked)
M2_LAW = "flow_limited_r5"
S1_FRONT = ("S1@FL", "S1@FR")                            # 423.1 / v5 10 "S1 전방 제외"
CP_LIMIT = 0.03                                          # v5 10 L2
GATES = ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6")
T_LIM_S = 0.010 / (0.25 * 0.0209243016) + 1.0            # spec 11980: 2.91165 s
FALSE_LOC_W = 0.01                                        # R4-B3 / 419.8 cond. 3
FISHER_P = 0.05                                           # rev6 9


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


def fault_names(rec):
    """FAULT names of a run (':' segments without numeric ones, rev3 R3-C6)."""
    out = set()
    for e in rec.get("events") or []:
        if isinstance(e, (list, tuple)) and len(e) == 2 and isinstance(e[1], str) and e[1].startswith("FAULT"):
            segs = []
            for s in e[1].split(":"):
                try:
                    float(s)
                except ValueError:
                    segs.append(s)
            out.add(":".join(segs))
    return out


# ----------------------------------------------------------------- judge (R4-A2 c)
def run_judge(repo, judge_dir, name, args_in, merged=None):
    """Run r79_sensor_judge (this path's own output); returns (output path, record)."""
    out = Path(judge_dir) / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    script = Path(repo) / JUDGE_REL
    cmd = [sys.executable, "-I", "-B", str(script)]
    cmd += (["judge-merged", str(out), merged] if merged else ["judge", str(out)]) + list(args_in) + [LATE_LOC_OPTION]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, stdin=subprocess.DEVNULL)
    rec = {"cmd": cmd[1:], "returncode": p.returncode, "stdout_tail": p.stdout[-600:], "stderr_tail": p.stderr[-600:],
           "out": str(out), "out_sha256": cm.sha256_file(out) if out.is_file() else None}
    return out, rec


def judge_runs(path):
    d = json.loads(Path(path).read_text("utf-8"))
    return d, {r.get("key"): r for r in d.get("runs") or []}


# ----------------------------------------------------------------- 419.8 recompute (S-4 late LOC)
def late_loc_conditions(rec, core, fnd=None):
    """419.8 / 419.8.1 conditions 1~5 from the r79 record (None = record missing)."""
    r = rec.get("r79") or {}
    base = rec.get("base") or {}
    ev = sorted((float(e[0]), e[1]) for e in rec.get("events") or []
                if isinstance(e, (list, tuple)) and len(e) == 2 and isinstance(e[1], str))
    t_off, t_loc = core.num(r.get("t_off_s")), core.num(r.get("t_loc_s"))
    if t_off is None or t_loc is None or not ev:
        return {"c1": None, "c2": None, "c3": None, "c4": None, "c5": None, "why": "t_off / t_loc / events missing"}
    ivs = []
    for t, n in ev:
        if n.startswith("leg_reapproach_start:"):
            leg = n.split(":", 1)[1]
            end = next((t2 for t2, n2 in ev if t2 >= t and n2 in (f"leg_reapproach_contact:{leg}",
                                                                  f"WARN_LEG_REAPPROACH_NO_CONTACT:{leg}")), None)
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
    c4 = None if mf is None else (core.t_ge(mf, core.F_MIN_N / 1000.0) and not fault_names(rec))
    # R4-B2: first DONE = base.t_done_s (None = no DONE), checked against base.phase_path
    if "t_done_s" not in base:
        c5, pp_ok = None, None
    else:
        td = core.num(base.get("t_done_s"))
        pp = base.get("phase_path")
        first = next((core.num(x[0]) for x in pp if isinstance(x, (list, tuple)) and len(x) == 2
                      and x[1] == "done"), None) if isinstance(pp, list) else "missing"
        pp_ok = None if first == "missing" else ((first is None and td is None) or
                                                 (first is not None and td is not None and abs(first - td) <= 1e-6))
        if pp_ok is False and fnd is not None:
            fnd.stop("S-11", str(rec.get("key")), f"base.t_done_s {td} is not the first done of phase_path ({first})")
        t_fin = core.num(base.get("t_loc_final_s"))
        t_fin = t_loc if t_fin is None else t_fin
        c5 = td is None or t_fin < td
    return {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "t_off_s": t_off, "t_loc_s": t_loc,
            "late_loc_s": t_loc - t_off, "phase_path_ok": pp_ok}


def line_grade(rec, row, core, fnd=None):
    """Re-aggregated line grade from the judge item rows (pass / flag / fail / undecidable)."""
    if not isinstance(row, dict) or not isinstance(row.get("rows"), dict):
        return "undecidable", ["no judge row"], None
    rows = row["rows"]
    if any(not isinstance(rows.get(g), dict) or not isinstance(rows[g].get("ok"), bool) for g in GATES):
        return "undecidable", ["judge item missing"], None
    fail, flags, cond = [], [], None
    for g in ("S-1", "S-2", "S-3", "S-5", "S-6"):
        if rows[g]["ok"] is False:
            fail.append(g)
    s4 = rows["S-4"]
    if s4.get("fail_misfire_new") is True:
        fail.append("S-4 misfire new")
    if s4.get("miss") is True:
        fail.append("S-4 miss")
    if s4.get("recontact_new") is True:            # 423.1: only a new strict_fail recontact counts
        fail.append("S-4 recontact new")
    lmo = core.num(s4.get("loc_minus_off_s"))
    if lmo is not None and core.t_gt(lmo, T_LIM_S):   # 13.2: time clause -> 419.8
        cond = late_loc_conditions(rec, core, fnd)
        vals = [cond[c] for c in ("c1", "c2", "c3", "c4", "c5")]
        if all(v is True for v in vals):
            flags.append("S4_late_loc")
        elif False in vals:
            fail.append("S-4 time clause (419.8 not met)")
        else:
            return "undecidable", ["419.8 record missing"], cond
    mine_s4_fail = any(x.startswith("S-4") for x in fail)
    if s4["ok"] is False and not mine_s4_fail and "S4_late_loc" not in flags:
        # rev5 R5-C2: an S-4 failure explained neither by 13.2 nor by the judge's existing S-4 FLAG tags
        # (e.g. S4_baseline) is a fail; with such a tag it is that FLAG
        tags = [t for t in (s4.get("flags") or []) if isinstance(t, str) and t.startswith("S4_")]
        if tags:
            flags.extend(tags)
        else:
            fail.append("S-4 unexplained (R5-C2)")
    if fail:
        return "fail", fail, cond
    return ("flag" if flags else "pass"), flags, cond


def grade_set(recs, jruns, core, fnd):
    out = {}
    for k, r in recs.items():
        if r.get("level") == "L1":
            continue
        gr, why, cond = line_grade(r, jruns.get(k), core, fnd)
        jp = (jruns.get(k) or {}).get("pass")
        out[k] = {"grade": gr, "why": why, "late_loc": cond, "judge_pass": jp,
                  "differs_from_judge_pass": isinstance(jp, bool) and gr in ("pass", "flag", "fail")
                  and jp != (gr != "fail")}
    return out


# ----------------------------------------------------------------- checks
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
    """R4-B3 four counts (3rd-stage judgement definition), counted from the run records."""
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


def l1_gate_judge(jd):
    """The same four counts from the judge output (R4-B3 second column)."""
    ref = jd.get("reference") or []
    fl = sum(int(r.get("false_loc") or 0) for r in ref if isinstance(r, dict))
    sm = jd.get("settings_mismatch")
    return {"false_loc": fl, "unmatched": len(jd.get("unmatched") or []), "errors": len(jd.get("errors") or []),
            "setting_mismatch": (len(sm) if isinstance(sm, list) else sm) if sm is not None else None}


def seedext(name, se, noise, fnd):
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


def seedext_record(grades_vb, grades_v0):
    """rev6 9 record: k/25 per inner and setting, CP (two roots), Fisher one-sided (VB > V0)."""
    from scipy.stats import fisher_exact  # noqa: PLC0415
    out = {}
    inners = sorted({k.split("|", 4)[-1] for k in list(grades_vb) + list(grades_v0)})
    for inner in inners:
        row = {}
        for s, gs in (("VB", grades_vb), ("V0", grades_v0)):
            sel = [g for k, g in gs.items() if k.endswith("|" + inner)]
            row[s] = {"k": sum(1 for g in sel if g["grade"] == "fail"), "n": len(sel),
                      "undecidable": sum(1 for g in sel if g["grade"] == "undecidable")}
            row[s].update(cp_pair(row[s]["k"], max(row[s]["n"], 1)))
        kv, k0, n = row["VB"]["k"], row["V0"]["k"], SEEDEXT_SEEDS
        p = float(fisher_exact([[kv, n - kv], [k0, n - k0]], alternative="greater")[1])
        row["fisher_p"] = p
        row["phrase"] = "VB 체계적 악화 의심(하네스)" if p < FISHER_P and kv > k0 else "시드 산포와 구분되지 않음"
        out[inner] = row
    return out


def cmd_noise(args, repo, v5j, core):
    is_p3, mod = core.load_is_extend_start(repo)
    fnd = core.Findings()
    judge_dir = Path(args.judge_dir)
    # R4-A2 condition 1: judge tool unchanged since the 436.8 seal
    head = args.git_at_start or cm.git_head(repo)
    commits = cm.git_commits_since(repo, SEAL_BASE, head, JUDGE_REL) if head else None
    jtool = {"path": JUDGE_REL, "sha256": cm.sha256_file(Path(repo) / JUDGE_REL), "git_at_start": head,
             "commits_since_f46b5ab": commits,
             # rev5 R5-E: modules the judge imports / works with - record git diff --stat (judgement
             # whether a change is record-only goes to the judgement document; not condition 1)
             "related_modules_diff_stat": {m: (cm.git_diff_stat(repo, SEAL_BASE, head, m) if head else None)
                                           for m in RELATED_MODULES}}
    if commits is None or commits:
        fnd.stop("S-11", "judge tool", f"git log {SEAL_BASE}..{head} -- {JUDGE_REL}: {commits}")
        return {"judge_tool": jtool, **fnd.as_dict(), "stop_codes": ["S-11"]}, "stop"
    d_vb, vb = load(args.noise_vb)
    d_v0, v0 = load(args.noise_v0)
    d_h6, h6 = load(args.h6)
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
    # judge runs (own outputs): VB with the dg3 keys merged (rev8 #6), V0 as is
    jrec = {}
    p_vb, jrec["VB_with_H6"] = run_judge(repo, judge_dir, "judge_VB_with_H6", [args.noise_vb], merged=args.h6)
    p_v0, jrec["V0"] = run_judge(repo, judge_dir, "judge_V0", [args.noise_v0])
    for name, rec in jrec.items():
        if rec["returncode"] != 0 or rec["out_sha256"] is None:
            fnd.stop("S-11", f"judge {name}", f"returncode {rec['returncode']}: {rec['stderr_tail'][-200:]}")
    if fnd.stops and any(s["code"] == "S-11" for s in fnd.stops):
        return {"judge_tool": jtool, "judge_runs": jrec, **fnd.as_dict(),
                "stop_codes": fnd.as_dict()["stop_codes"]}, "stop"
    jd_vb, jr_vb = judge_runs(p_vb)
    jd_v0, jr_v0 = judge_runs(p_v0)
    eff_recs = {**vb, **h6}   # the run records the merged judge saw
    g_vb = grade_set(eff_recs, jr_vb, core, fnd)
    g_v0 = grade_set(v0, jr_v0, core, fnd)
    # L1 gate (VB): own counts vs judge counts (R4-B3)
    l1_own = l1_gate(d_vb.get("meta") or {}, vb, "VB", core)
    l1_j = l1_gate_judge(jd_vb)
    l1_cmp = {k: l1_own[k] == l1_j[k] for k in ("false_loc", "unmatched", "errors", "setting_mismatch")
              if l1_j[k] is not None}
    l1_no_ref = [k for k in ("false_loc", "unmatched", "errors", "setting_mismatch") if l1_j[k] is None]
    # rev5 R5-C1: a count the judge does not output is "대조 대상 없음" (path-2 count is the value)
    if not all(l1_cmp.values()):
        fnd.undec("L1 gate", f"own vs judge counts differ {l1_cmp} (R4-B3: S-13)")
        fnd.stop("S-13", "L1 gate", "path-2 count differs from the judge count")
    if any(l1_own[k] for k in ("false_loc", "unmatched", "errors", "setting_mismatch")):
        fnd.fail("L1 gate", "v5 10 L1 gate violated")
        fnd.stop("H-10", "L1 gate", f"{ {k: l1_own[k] for k in ('false_loc', 'unmatched', 'errors', 'setting_mismatch')} }")
    res = {}
    for lev in ("L2", "L3"):
        keys = [k for k, r in vb.items() if r.get("level") == lev and not s1_front(r)]
        und = [k for k in keys if g_vb[k]["grade"] == "undecidable"]
        kf = sum(1 for k in keys if g_vb[k]["grade"] == "fail")
        res[lev] = {**cp_pair(kf, len(keys)), "flags": sum(1 for k in keys if g_vb[k]["grade"] == "flag"),
                    "undecidable": len(und),
                    "fallback_rows": sum(1 for k in keys if eff_recs[k].get("rod_fallback_reasons")),
                    "n_late_by_row": {k: core.dig(eff_recs[k], "lock_window_alignment.n_late", None)
                                      for k in keys if eff_recs[k].get("rod_fallback_reasons")},
                    "pass_to_fail_vs_V0": [k for k in keys if g_vb[k]["grade"] == "fail"
                                           and g_v0.get(k, {}).get("grade") in ("pass", "flag")]}
        if und:
            fnd.undec(lev, f"{len(und)} undecidable line grades")
    l2 = res["L2"]
    if l2["undecidable"] == 0:
        ok = l2["upper_beta"] <= CP_LIMIT + 1e-12 and l2["upper_root"] <= CP_LIMIT + 1e-12
        l2["grade"] = "pass" if ok else "fail"
        if not ok:
            fnd.fail("L2", f"CP {l2['upper_beta']:.4f} > 3 %")
            fnd.stop("H-10", "L2", "L2 CP > 3 %")
    res["L3"]["grade"] = "record"
    # H-6 grade (R4-B6)
    h6f = core.Findings()
    l1_by_case = {(r.get("harness"), r.get("case_index"), r.get("inner")): r for r in vb.values()
                  if r.get("level") == "L1"}
    new_fault = {}
    for k, r in h6.items():
        l1r = l1_by_case.get((r.get("harness"), r.get("case_index"), r.get("inner")))
        nf = sorted(fault_names(r) - (fault_names(l1r) if l1r else set()))
        if nf:
            new_fault[k] = nf
        if l1r is None:
            h6f.undec(k, "no L1 run of the same case (S-6 reference)")
    for s in fnd.stops:
        if str(s["where"]).startswith("H-6|"):
            h6f.stop(s["code"], s["where"], s["why"])
    for u in fnd.undecidable:
        if str(u["where"]).startswith("H-6|"):
            h6f.undec(u["where"], u["why"])
    if new_fault:
        h6f.fail("H-6", f"new FAULT names vs L1 in {len(new_fault)} runs (R4-B6 3)")
    if any(g_vb[k]["grade"] == "undecidable" for k in h6):
        h6f.undec("H-6", "undecidable line grade")
    h6_l3_fail = sum(1 for k, r in h6.items() if r.get("level") == "L3" and g_vb[k]["grade"] == "fail")
    se = {}
    if args.seedext_vb and args.seedext_v0:
        sv_doc, sv = load(args.seedext_vb)
        s0_doc, s0 = load(args.seedext_v0)
        jp["seedext_VB"] = run_checks("seedext_VB", sv, core, v5j, is_p3, True, fnd)
        run_checks("seedext_V0", s0, core, v5j, is_p3, False, fnd)
        se["VB"] = seedext("seedext_VB", sv, vb, fnd)
        se["V0"] = seedext("seedext_V0", s0, v0, fnd)
        gs = {}
        # rev5 R5-C3: the judge gets the seedext file and the same-setting noise file (its L1 lines)
        for s, recs, se_path, noise_path in (("VB", sv, args.seedext_vb, args.noise_vb),
                                             ("V0", s0, args.seedext_v0, args.noise_v0)):
            pj, jrec[f"seedext_{s}"] = run_judge(repo, judge_dir, f"judge_seedext_{s}", [se_path, noise_path])
            if jrec[f"seedext_{s}"]["returncode"] != 0:
                fnd.stop("S-11", f"judge seedext {s}", jrec[f"seedext_{s}"]["stderr_tail"][-200:])
                continue
            gs[s] = grade_set(recs, judge_runs(pj)[1], core, fnd)
        if len(gs) == 2:
            se["record"] = seedext_record(gs["VB"], gs["V0"])
    reagg = [{"bundle": b, "set": s, "item": f"{g} (judge item row)", "source": "r79_sensor_judge --s4-late-loc",
              "lines": n} for b, s, n in (("H-8", "noise_VB+H-6", len(g_vb)), ("H-8", "noise_V0", len(g_v0)))
             for g in GATES]
    reagg.append({"bundle": "H-6", "set": "H-6 (in noise_VB+H-6)", "item": "S-1~S-6 line grade",
                  "source": "same judge run", "lines": len(h6)})
    if se.get("record"):
        reagg.append({"bundle": "H-8", "set": "seedext", "item": "S-1~S-6 line grade",
                      "source": "r79_sensor_judge --s4-late-loc", "lines": se["VB"]["runs"] + se["V0"]["runs"]})
    lab = {"pass": "통과", "fail": "미달", "undecidable": "판정 불가", "stop": "멈춤"}
    body = {"inputs": {k: [p, cm.sha256_file(p)] for k, p in (("noise_vb", args.noise_vb),
                                                              ("noise_v0", args.noise_v0), ("h6", args.h6),
                                                              ("seedext_vb", args.seedext_vb),
                                                              ("seedext_v0", args.seedext_v0)) if p},
            "judge_tool": jtool, "judge_runs": jrec, "v5_options": mod,
            "recomputed": {"levels": {"VB": lv_vb, "V0": lv_v0, "H-6": lv_h6},
                           "L1_gate": {"path2": l1_own, "judge": l1_j, "same": l1_cmp,
                                       "대조 대상 없음": l1_no_ref},
                           "H-6_substitution": {"keys": len(sub),
                                                "same_hash_as_H8_VB": sum(1 for s in sub if s["same_hash"]),
                                                "hash_missing": sum(1 for s in sub if s["hash_missing"]),
                                                "record_status": "기록 불완전" if any(s["hash_missing"] for s in sub)
                                                else "complete",
                                                "different": [s["key"] for s in sub
                                                              if not s["same_hash"] and not s["hash_missing"]]},
                           "J-P3": jp},
            "reaggregated": {"L2": l2, "L3": res["L3"], "seedext": se,
                             "judge_pass_differs": sum(1 for g in list(g_vb.values()) + list(g_v0.values())
                                                       if g["differs_from_judge_pass"]),
                             "line_grades": {"noise_VB_with_H6": g_vb, "noise_V0": g_v0}},
            "H-6": {"grade": lab[h6f.status()], "new_fault": new_fault, "L3_fail_record": h6_l3_fail,
                    **h6f.as_dict()},
            "TABLE_REAGG": reagg, **fnd.as_dict()}
    st = fnd.status()
    body["grades_436_8"] = {"H-6": lab[h6f.status()], "H-8": lab[st]}
    body["stop_codes"] = sorted(set(fnd.as_dict()["stop_codes"]) | set(h6f.as_dict()["stop_codes"]))
    worst = max((st, h6f.status()), key=lambda s: {"pass": 0, "fail": 1, "undecidable": 2, "stop": 3}[s])
    return body, worst


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
    n.add_argument("--judge-dir", required=True, help="this path's folder for the r79 judge outputs (R4-A2 c 3)")
    n.add_argument("--git-at-start", default=None, help="GIT_AT_START of 436.8 (default: repo HEAD)")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"noise": cmd_noise})


if __name__ == "__main__":
    sys.exit(main())
