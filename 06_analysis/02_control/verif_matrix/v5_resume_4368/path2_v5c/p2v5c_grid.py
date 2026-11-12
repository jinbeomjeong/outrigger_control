"""436.8 path 2: v5-criteria grade recount of the H-9 grid part (768 VB runs, r67 / r69 screens).

Inputs: ``resume_k1/h9_grid/grid_{r67_main,r67_top,r69_bottom,r69_top}.json`` (rev1 RV1-3.3) and the V0 grid
files that form the pair (``--v0 <stem>=<file>``; which V0 is the 436.8 pair is open, see README Q-G1).

Rules (rule -> function):
  spec 342.3 row gates (r67 screen, one row per event), recomputed from the run record fields
                                                           -> ``gates_p2`` (compared with the recorded gates)
  v5 10 grid row: pass -> fail 0 against V0, FAULT 0        -> ``cmd_grid``
  rev5 #5 / 5.1: family F (keys screen|top|0.0|ready|FR/FL, event FS24) - only the gates Fmin_after_W
      and U57_outside go to the 16-phase rule of rev5 5.2, which needs 32 VB + 32 V0 phase runs that are
      not part of 436.8; reported separately (``family_F``), not decided here
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


def cmd_grid(args, repo, v5j, core):
    is_p3, mod = core.load_is_extend_start(repo)
    fnd = core.Findings()
    vb_files = dict(x.split("=", 1) for x in args.vb)
    v0_files = dict(x.split("=", 1) for x in (args.v0 or []))
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
            # J-P3 (rod reading assumed: two-pressure event path, rev9 3.2 #4)
            res, why = v5j.jp3(run, is_p3, True)
            if res == "not_applicable_tag":
                fnd.undec(k, "J-P3 not applied (tag not ③ on)")
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
    if not v0_files:
        fnd.undec("pair", "no V0 grid given: pass -> fail cannot be counted (v5 10)")
    if fam_F:
        fnd.undec("family_F", f"{len(fam_F)} family-F transitions need the rev5 5.2 phase rule (not in 436.8)")
    if trans_nonF:
        fnd.stop("H-10", "grid", f"pass -> fail {len(trans_nonF)} (outside family F)")
    body = {"inputs": {"vb": out_files, "v0": v0_meta}, "v5_options": mod,
            "grid": {"runs": len(rows), "pass_p2": sum(1 for x in rows if x["pass_p2"] is True),
                     "fail_p2": sum(1 for x in rows if x["pass_p2"] is False),
                     "pass_to_fail_all": trans_all, "pass_to_fail_outside_F": trans_nonF,
                     "family_F": fam_F, "fault_runs": fault_runs,
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
    g.add_argument("--v0", action="append", default=None, help="<stem>=<V0 grid json> (pair, README Q-G1)")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"grid": cmd_grid})


if __name__ == "__main__":
    sys.exit(main())
