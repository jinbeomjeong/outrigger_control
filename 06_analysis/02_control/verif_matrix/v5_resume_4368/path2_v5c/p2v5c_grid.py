"""436.8 path 2: v5-criteria grade recount of the H-9 grid part (768 VB runs, r67 / r69 screens).

Inputs: ``resume_k1/h9_grid/grid_{r67_main,r67_top,r69_bottom,r69_top}.json`` (rev1 RV1-3.3), the V0 pair
of 436.8 rev3 R3-E1 (stored V0 + same-commit 8-job sample, or the new ``resume_k1/h9_grid_v0/``) and, when
needed, ``resume_k1/h9_family_F.jsonl`` (R3-E2).

Rules (rule -> function):
  spec 342.3 row gates (r67 screen, one row per event), recomputed from the run record fields
                                                           -> ``gates_p2`` (compared with the recorded gates)
  rev3 R3-E1 V0 pair (8-job sample hash, else V0 768)      -> ``sample_jobs``, ``v0_pair``
  v5 10 grid row: pass -> fail 0 against V0, FAULT 0        -> ``cmd_grid``
  rev5 #5 / 5.1 / 5.2 with rev3 R3-E2: family F (keys screen|top|0.0|ready|FR/FL, event FS24); a
      transition made only by Fmin_after_W / U57_outside goes to R-1..R-4 on the 64 conditional runs
      (pass: excluded from H-10, fail: H-10 stop)            -> ``family_f_rule``
  rev8 3.2 / rev9 3.2 J-P3 on every VB run (two-pressure event path: rod reading assumed)
                                                           -> ``p2_v5j.jp3`` (imported)
  rev2 2.1 / rev6 J9 (post-lift M2 clip) on every VB run   -> ``cmd_grid``
  v5 8 window rule / H-7: n_late_fallback > 0              -> ``cmd_grid``
  436.8 rev1 RV1-12 S-15 count (192 runs per file, 768)    -> ``cmd_grid``
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402

TOOL_NAME = "p2v5c_grid.py"
TOOL_VERSION = "1"
STEMS = ("grid_r67_main", "grid_r67_top", "grid_r69_bottom", "grid_r69_top")
RUNS_PER_FILE = 192
FAST_EVENTS = {"RE1bF", "FS24"}
SLOW_EVENTS = {"G4"}
PAIR_UNION_S, LAST_TOUCH_S = 1.8, 3.0         # 342.3 U-S8-32
ADJ_SUM_S, ADJ_GAP_MM = 0.5, 2.0              # 342.3 U57
END_ATT_DEG = 0.2                             # 342.3 end attitude
MAX_BUNDLES = 1                               # 342.3 recurrence (+20 J bundles <= 1)
FAMILY_F_KEYS = {"screen|top|0.0|ready|FR", "screen|top|0.0|ready|FL"}   # rev5 5.1
FAMILY_F_EVENT = "FS24"
FAMILY_F_GATES = {"Fmin_after_W", "U57_outside"}
M2_LAW = "flow_limited_r5"


def gates_p2(run, core):
    """spec 342.3 gates from the run record; None where a field is missing."""
    fmin_kn = core.F_MIN_N / 1000.0
    num = core.num

    def le(v, x):
        v = num(v)
        return None if v is None else not core.t_gt(v, x)

    def min_ge(d):
        if not isinstance(d, dict) or not d or any(num(v) is None for v in d.values()):
            return None
        return core.t_ge(min(num(v) for v in d.values()), fmin_kn)

    fp, fe = run.get("fault_periods"), run.get("fault_events")
    fault0 = None if not isinstance(fp, int) or not isinstance(fe, list) else (fp == 0 and not fe)
    att = run.get("att_end_deg")
    if isinstance(att, list) and att and all(num(a) is not None for a in att):
        end_att = run.get("final_phase") == "ready" and not core.t_gt(max(abs(num(a)) for a in att), END_ATT_DEG)
    else:
        end_att = None
    nb = (run.get("twist") or {}).get("n_bundles")
    recurrence = None if not isinstance(nb, int) else nb <= MAX_BUNDLES
    g = {"fault0": fault0, "end_att": end_att, "recurrence": recurrence}
    ev = run.get("event")
    if ev in FAST_EVENTS:
        out = run.get("adj_lift_outside_W_s")
        g.update(U832_pair_union=le(run.get("pair_union_s"), PAIR_UNION_S),
                 U832_last_touch=le(run.get("pair_last_touch_s"), LAST_TOUCH_S),
                 U57_sum=le(run.get("adj_lift_sum_W_s"), ADJ_SUM_S),
                 U57_gap=le(run.get("adj_max_gap_W_mm"), ADJ_GAP_MM),
                 U57_outside=None if num(out) is None else num(out) == 0.0,
                 Fmin_after_W=min_ge(run.get("min_F_after_W_kN")))
    elif ev in SLOW_EVENTS:
        lifts = run.get("lifts")
        g.update(no_lift=None if not isinstance(lifts, dict) else not lifts,
                 Fmin_after_event=min_ge(run.get("min_F_after_event_kN")))
    else:
        g["event_unknown"] = None
    return g


def run_pass(g):
    return None if any(v is None for v in g.values()) else all(g.values())


def runs_of(doc):
    for r in doc.get("results") or []:
        for run in r.get("runs") or []:
            yield r, run


def run_key(stem, r, run):
    return f"{stem}|{r.get('key')}|{run.get('event')}|{run.get('offset_s')}"


F_PHASES = 16                                   # rev5 5.2: 0, 0.00625, ..., 0.09375 s
F_M, F_M_SUM = 4, 6                             # rev5 5.2 R-1 / R-2


def sample_jobs(stored):
    """rev3 R3-E1 + rev4 R4-B4: per file the first and the last ``results[]`` item; one job = one item,
    all its runs (matched by stem, key, event, offset_s). Returns {job: {run_key: hash}}."""
    out = {}
    for stem, path in stored.items():
        res = json.loads(Path(path).read_text("utf-8")).get("results") or []
        for r in (res[:1] + res[-1:]) if res else []:
            out[f"{stem}|{r.get('key')}"] = {run_key(stem, r, run): run.get("commands_sha256")
                                            for run in r.get("runs") or []}
    return out


def v0_pair(args, fnd):
    """rev3 R3-E1: stored V0 grid is the pair only if the same-commit 8-job sample hashes all match;
    otherwise the new V0 768 (resume_k1/h9_grid_v0/) is the pair."""
    stored = dict(x.split("=", 1) for x in (args.v0_stored or []))
    new = dict(x.split("=", 1) for x in (args.v0_new or []))
    rec = {"stored": stored, "new": new, "sample": None, "pair": None}
    if stored and args.v0_sample:
        want = sample_jobs(stored)
        got = {}
        for x in args.v0_sample:
            stem, path = x.split("=", 1)
            for r, run in runs_of(json.loads(Path(path).read_text("utf-8"))):
                got[run_key(stem, r, run)] = run.get("commands_sha256")
        cmp_ = []
        for job, runs in sorted(want.items()):
            diff = [k for k, hh in runs.items() if not (isinstance(hh, str) and got.get(k) == hh)]
            cmp_.append({"job": job, "runs": len(runs), "runs_differing": diff, "same": bool(runs) and not diff})
        rec["sample"] = {"jobs": len(cmp_), "same": sum(c["same"] for c in cmp_), "detail": cmp_}
        if len(cmp_) != 8:
            fnd.stop("S-15", "V0 sample", f"{len(cmp_)} sample jobs != 8")
    if new:
        rec["pair"] = "new"
        if set(new) != set(STEMS):
            fnd.stop("S-15", "V0 new", f"stems {sorted(new)}")
        if rec["sample"] and rec["sample"]["same"] == 8:
            fnd.note("V0 pair", "sample hashes all equal but the new V0 768 was given: new V0 used (record)")
        return new, rec
    if rec["sample"] is None:
        fnd.undec("V0 pair", "R3-E1: V0 8-job sample (and stored V0) not given")
        return {}, rec
    if rec["sample"]["same"] == 8:
        rec["pair"] = "stored (old V0 controller, sample hashes equal)"
        return stored, rec
    fnd.undec("V0 pair", "R3-E1: sample hash differs -> V0 768 (resume_k1/h9_grid_v0/) required")
    return {}, rec


def family_f_rule(path, core, fnd):
    """rev5 5.2 R-1..R-4 on the 64 conditional runs (rev3 R3-E2)."""
    lines = core.read_jsonl(path)
    runs, other_events = {}, 0
    for ln in lines:   # rev4 R4-B5: one line = one runner run; only event FS24 is judged and counted
        run = ln.get("run") if isinstance(ln.get("run"), dict) else ln
        s = ln.get("setting") or ln.get("v5_setting") or (ln.get("job") or {}).get("setting")
        key = ln.get("key") or (ln.get("job") or {}).get("key")
        off = run.get("offset_s", ln.get("offset_s"))
        if (run.get("event") or ln.get("event")) != FAMILY_F_EVENT:
            other_events += 1
            continue
        runs[(key, s, round(float(off), 6) if off is not None else None)] = run
    out = {"lines": len(lines), "runs": len(runs), "non_FS24_lines_excluded": other_events}
    if len(runs) != 2 * 2 * F_PHASES or {k[0] for k in runs} != FAMILY_F_KEYS or {k[1] for k in runs} != {"V0", "VB"}:
        fnd.stop("S-15", "family_F", f"runs {len(runs)} keys {sorted({str(k[0]) for k in runs})}")
        out["result"] = "undecidable"
        return out
    k = {}
    r3, r4 = [], []
    used_recorded = 0

    def gates_of(run):
        nonlocal used_recorded
        g = gates_p2(run, core)
        rec = run.get("gates") if isinstance(run.get("gates"), dict) else {}
        if any(v is None for v in g.values()) and rec and all(isinstance(rec.get(x), bool) for x in g):
            used_recorded += 1   # R4-B5 line holds the recorded gates; raw fields absent -> recorded gates
            return {x: rec[x] for x in g}
        return g

    for (key, s, off), run in runs.items():
        g = gates_of(run)
        if any(v is None for v in g.values()):
            fnd.undec(f"family_F|{key}|{s}|{off}", "gate field missing")
        bad = any(g.get(x) is False for x in FAMILY_F_GATES)
        k[(key, s)] = k.get((key, s), 0) + bad
        if s == "VB":
            if g.get("fault0") is not True or run.get("final_phase") != "ready":
                r3.append([key, off])
            v0g = gates_of(runs.get((key, "V0", off), {}))
            others = [x for x, v in g.items() if x not in FAMILY_F_GATES and v is False and v0g.get(x) is not False]
            if others:
                r4.append([key, off, others])
    r1 = {key: k.get((key, "VB"), 0) <= k.get((key, "V0"), 0) + F_M for key in FAMILY_F_KEYS}
    tv = sum(k.get((key, "VB"), 0) for key in FAMILY_F_KEYS)
    t0 = sum(k.get((key, "V0"), 0) for key in FAMILY_F_KEYS)
    r2 = tv <= t0 + F_M_SUM
    ok = all(r1.values()) and r2 and not r3 and not r4
    out.update(k={f"{a}|{b}": v for (a, b), v in sorted(k.items())}, R1=r1, R2={"VB": tv, "V0": t0, "ok": r2},
               R3=r3, R4=r4, recorded_gates_used=used_recorded, result="pass" if ok else "fail")
    return out


def cmd_grid(args, repo, v5j, core):
    is_p3, mod = core.load_is_extend_start(repo)
    fnd = core.Findings()
    vb_files = dict(x.split("=", 1) for x in args.vb)
    v0_files, pair_rec = v0_pair(args, fnd)
    if set(vb_files) != set(STEMS):
        fnd.stop("S-15", "files", f"VB stems {sorted(vb_files)} != {list(STEMS)}")
    v0_runs, v0_meta = {}, {}
    for stem, path in v0_files.items():
        d = json.loads(Path(path).read_text("utf-8"))
        v0_meta[stem] = {"path": path, "sha256": cm.sha256_file(path),
                         "v5_setting": (d.get("meta") or {}).get("v5_setting"),
                         "tags": sorted({str(v5j.tag_of(run)) for _, run in runs_of(d)})}
        for r, run in runs_of(d):
            g = gates_p2(run, core)
            v0_runs[run_key(stem, r, run)] = {"pass_p2": run_pass(g), "pass_rec": run.get("pass"),
                                              "gates_p2": g}
    out_files, rows = {}, []
    trans_all, trans_nonF, fault_runs, gate_diff = [], [], [], []
    fam_F = []
    # rev11 R11-2 / rev12 R12-1: T4h search places of the VB grid files (input error = S-11, exit 2)
    places, perr = v5j.t4h_places(list(vb_files.values()), getattr(args, "t4h_root", None))
    if places is None:
        body, st = cm.t4h_input_error(perr)
        body["not_judged"] = ["H-9 grid"]
        return body, st
    t4h_log = {}
    for stem, path in vb_files.items():
        d = json.loads(Path(path).read_text("utf-8"))
        meta = d.get("meta") or {}
        n = 0
        tags = {}
        for r, run in runs_of(d):
            n += 1
            k = run_key(stem, r, run)
            g = gates_p2(run, core)
            rec_g = run.get("gates") or {}
            p = run_pass(g)
            if p is None:
                fnd.undec(k, f"gate field missing {[x for x, v in g.items() if v is None]}")
            diff = sorted(x for x in g if x in rec_g and g[x] is not None and rec_g[x] != g[x])
            if diff or (p is not None and run.get("pass") is not None and p != run.get("pass")):
                gate_diff.append({"run": k, "gates": diff, "pass_p2": p, "pass_rec": run.get("pass")})
            if g.get("fault0") is False:
                fault_runs.append(k)
                fnd.fail(k, "FAULT in a VB grid run (v5 10: FAULT 0)")
            t = str(v5j.tag_of(run))
            tags[t] = tags.get(t, 0) + 1
            v0 = v0_runs.get(k)
            row = {"run": k, "pass_p2": p, "v0_pass_p2": None if v0 is None else v0["pass_p2"]}
            in_F = r.get("key") in FAMILY_F_KEYS and run.get("event") == FAMILY_F_EVENT
            if v0 is None:
                if v0_files:
                    fnd.undec(k, "no V0 run with the same key / event / offset")
            elif v0["pass_p2"] is True and p is False:
                failed = sorted(x for x, v in g.items() if v is False)
                trans_all.append({"run": k, "failed_gates": failed})
                v0f = sorted(x for x, v in v0["gates_p2"].items() if v is False)
                if in_F and set(failed) <= FAMILY_F_GATES:
                    fam_F.append({"run": k, "failed_gates": failed, "v0_failed": v0f})
                else:
                    trans_nonF.append({"run": k, "failed_gates": failed})
                    fnd.fail(k, f"grid pass -> fail {failed}")
            if in_F:
                row["family_F"] = True
            rows.append(row)
            # J-P3 (configuration: two-pressure event path = rod reading, rev9 3.2 #4); rev12 R12-1: a
            # recorded t4h_file is read first (found 0 or 2+ = S-2, J-P3 not judged)
            rod, ok = cm.jp3_rod_input(fnd, k, run, places[str(path)], v5j, True, t4h_log)
            res, why = v5j.jp3(run, is_p3, rod) if ok else ("t4h_unresolved", "R12-1 S-2")
            if not ok:
                pass
            elif cm.jp3_tag_scope(fnd, k, res, "VB"):   # rev8 R8-2: not applicable + S-2
                pass
            elif res == "H-7":
                fnd.stop("H-7", k, f"J-P3 {why}")
            elif res == "setting_defect":
                fnd.stop("J-P3-defect", k, why)
            hr = run.get("hydraulics_record") or r.get("hydraulics_record") or {}
            post = hr.get("m2_clipped_steps_post_lift")
            if isinstance(post, list) and sum(post) > 0:
                fnd.stop("H-9", k, f"m2_clipped_steps_post_lift {post}")
            elif not isinstance(post, list):
                fnd.undec(k, "m2_clipped_steps_post_lift missing")
            law = (run.get("hydraulic_options") or r.get("hydraulic_options") or {}).get("m2_law")
            if law != M2_LAW:
                fnd.undec(k, f"m2_law {law!r} (rev6 #9: rerun)")
            nlf = core.dig(run, "lock_window_alignment.n_late_fallback", None)
            if isinstance(nlf, int) and nlf > 0:
                fnd.stop("H-7", k, f"n_late_fallback {nlf}")
        if n != RUNS_PER_FILE:
            fnd.stop("S-15", stem, f"runs {n} != {RUNS_PER_FILE}")
        out_files[stem] = {"path": path, "sha256": cm.sha256_file(path), "runs": n, "tags": tags,
                           "meta_spec": meta.get("spec"), "meta_script": meta.get("script"),
                           "v5_setting": meta.get("v5_setting")}
    fam_rule = None
    if fam_F:   # rev3 R3-E2 (Q-E2 = A): conditional 64 runs judged by rev5 5.2 R-1..R-4
        if not args.family_f:
            fnd.undec("family_F", f"{len(fam_F)} family-F transitions: resume_k1/h9_family_F.jsonl (64 runs) needed")
        else:
            fam_rule = family_f_rule(args.family_f, core, fnd)
            fam_rule["input"] = [args.family_f, cm.sha256_file(args.family_f)]
            if fam_rule["result"] == "fail":
                fnd.stop("H-10", "family_F", "rev5 5.2 R-1..R-4 failed")
    if trans_nonF:
        fnd.stop("H-10", "grid", f"pass -> fail {len(trans_nonF)} (outside family F)")
    body = {"inputs": {"vb": out_files, "v0": v0_meta}, "v5_options": mod, "v0_pair": pair_rec,
            "R11-2_t4h": {"search_dirs": {k: [str(d) for d in v] for k, v in places.items()}, "lookup": t4h_log},
            "grid": {"runs": len(rows), "pass_p2": sum(1 for x in rows if x["pass_p2"] is True),
                     "fail_p2": sum(1 for x in rows if x["pass_p2"] is False),
                     "pass_to_fail_all": trans_all, "pass_to_fail_outside_F": trans_nonF,
                     "family_F": fam_F,
                     "family_F_rule": fam_rule if fam_F else "not applicable (no family-F-only transition)",
                     "fault_runs": fault_runs,
                     "recorded_gate_differences": gate_diff, **fnd.as_dict()},
            "per_run": rows}
    st = fnd.status()
    body["grades_436_8"] = {"H-9_grid": {"pass": "통과", "fail": "미달", "undecidable": "판정 불가",
                                          "stop": "멈춤"}[st]}
    body["stop_codes"] = fnd.as_dict()["stop_codes"]
    return body, st


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    cm.add_common_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid")
    g.add_argument("--vb", action="append", required=True, help="<stem>=<resume_k1/h9_grid/<stem>.json>")
    g.add_argument("--v0-stored", action="append", default=None,
                   help="<stem>=<stored V0 grid json> (acceptance/c4g2_only/grid, R3-E1)")
    g.add_argument("--v0-sample", action="append", default=None,
                   help="<stem>=<same-commit V0 8-job sample json> (R3-E1)")
    g.add_argument("--v0-new", action="append", default=None,
                   help="<stem>=<resume_k1/h9_grid_v0/<stem>.json> (R3-E1, when the sample differs)")
    g.add_argument("--family-f", default=None, help="resume_k1/h9_family_F.jsonl (R3-E2, 64 runs)")
    g.add_argument("--t4h-root", action="append", default=None,
                   help="T4h folder (rev12 R12-1 / rev11 R11-2): only when no --vb file has a convention "
                        "folder <stem>_t4h/ or t4h/, at most one")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"grid": cmd_grid})


if __name__ == "__main__":
    sys.exit(main())
