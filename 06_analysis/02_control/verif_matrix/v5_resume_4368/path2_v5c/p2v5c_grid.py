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
  436.8 rev1 RV1-12 S-15 count (192 runs per file, 768)    -> ``cmd_grid``
R4 (436.8 R4 common block sha256 e451f067..., supplement 2-2; 2-terra author, a new agent run without the earlier
authors' context): every one of the 768 runs (``results[i].runs[j]``) is a row of RD-7. J-P3 = ``p2_v5j.jp3(run,
is_p3, rod, tag=<run tag, else results[i] tag>)``; an RD-8 input-format defect or an RD-7 3 top-level mismatch is
J-P3 undecidable (never a pass, ``common.jp3_apply``). J11 = ``p2_v5j.j11_item(run, setting=results[i].v5_setting,
setting_required=True)`` (supplement 3-6: ``results[i].v5_setting`` only, missing = J11 undecidable; RD-10 block
missing = undecidable on VB); the old ``lock_window_alignment.n_late_fallback`` stop is replaced by
it (rev16:102 ``n_late_fallback_by_leg`` of the actual fallback legs). Output ``R4``: RD-7 J-P3 / J11 rows
(RD-7 3 columns and order), RD-8 / RD-9 / RD-10 counts of the grid part; ``RD-13`` the H-9 item list.
R4 supplement 4 (user decisions 127 / 128): ``--family-f`` (original ``resume_k1/h9_family_F.jsonl``) is required
and R-1..R-4 are always computed from its 64 lines (``family_f_rule``: fields ``key``, ``setting``, ``offset_s``,
``event``, ``gates``, ``fault_events``, ``final_phase``, ``controller_tag``; pairs by (key, offset_s); form = S-15;
plate by ``setting`` + tag = S-11 / S-2). Family F rows = the two keys' FS24 runs of ``grid_r67_main`` /
``grid_r67_top`` only, 12 (else S-15). Applied only when one of them has a two-gate-only pass -> fail: pass = those
two-gate failures leave the v5 H-10 count, fail / undecidable = v5 stop H-10; else a record. Supplement 4-4: the
four stored V0 grids (``<stem>.json``) and ``h9_family_F.jsonl`` must exist (``input_files_check``, S-15).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2v5c_common as cm  # noqa: E402

TOOL_NAME = "p2v5c_grid.py"
TOOL_VERSION = "3"
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
F_STEMS = ("grid_r67_main", "grid_r67_top")      # rev5 5.1: the family F rows overlap in these two files
F_ROWS = 12                                        # supplement 4-5: 2 phases x 2 keys + 4 phases x 2 keys
FAMILY_F_NAME = "h9_family_F.jsonl"                # supplement 4-2 / 4-5: the original judgement input
M2_LAW = "flow_limited_r5"


def input_files_check(args, fnd):
    """Supplement 4-4 (this folder's part): the stored V0 grids (``--v0-stored``, one per stem, file name
    ``<stem>.json``, never ``*_off.json``) and ``--family-f`` = ``h9_family_F.jsonl`` must exist; a missing file or
    another name = S-15 (the bundle stops)."""
    out = {"v0_stored": {}, "family_f": None, "ok": True}
    stored = dict(x.split("=", 1) for x in (args.v0_stored or []))
    for stem in STEMS:
        p = stored.get(stem)
        ok = p is not None and Path(p).is_file() and Path(p).name == f"{stem}.json"
        out["v0_stored"][stem] = {"path": p, "ok": ok}
        if not ok:
            fnd.stop("S-15", f"v0_stored|{stem}", f"supplement 4-4: stored V0 grid {p!r} missing or not {stem}.json")
    extra = sorted(set(stored) - set(STEMS))
    if extra:
        fnd.stop("S-15", "v0_stored", f"supplement 4-4: unexpected stems {extra}")
    ff = getattr(args, "family_f", None)
    ok = isinstance(ff, str) and Path(ff).is_file() and Path(ff).name == FAMILY_F_NAME
    out["family_f"] = {"path": ff, "ok": ok}
    if not ok:
        fnd.stop("S-15", "family_F input", f"supplement 4-4: {ff!r} missing or not {FAMILY_F_NAME}")
    out["ok"] = not extra and ok and all(v["ok"] for v in out["v0_stored"].values())
    return out


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


def runs_indexed(doc):
    """(i, j, results[i], results[i].runs[j]) in file order (R4 RD-7 3 position ``results[i].runs[j]``)."""
    for i, r in enumerate(doc.get("results") or []):
        for j, run in enumerate(r.get("runs") or []):
            yield i, j, r, run


def run_tag_view(v5j, r, run):
    """rev8 R8-1 ("top-level controller_tag", user decision 19): a grid run carries no tag; its job record
    ``results[i]`` holds the run's controller tag. The run's own tag wins; the run is not changed (a shallow
    copy gets ``controller_tag``). Neither = no tag (J-P3 not applicable + S-2 on a VB run, R8-2)."""
    if v5j.tag_of(run) is not None:
        return run
    t = v5j.tag_of(r)
    return run if t is None else {**run, "controller_tag": t}


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


def _f_num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def family_f_rule(path, core, fnd, v5j):
    """R4 supplement 4-5 (user decision 127): v5 criteria revision 5 5.2 R-1..R-4 on the original
    ``resume_k1/h9_family_F.jsonl`` (64 lines, rev3 R3-E2, rev4 R4-B5), always computed.

    Read per line: ``key``, ``setting``, ``offset_s``, ``event``, ``gates`` (gate -> bool, True = pass),
    ``fault_events`` (list), ``final_phase`` (str), ``controller_tag``. Form: 64 lines, ``event`` all FS24, the
    2 keys x 16 ``offset_s`` x V0 / VB cells one line each, else S-15 (result undecidable). Plate by ``setting``
    and tag check (supplement 4-3: S-11 / S-2). k = phases with ``gates.Fmin_after_W`` or ``gates.U57_outside``
    False per key and setting. R-1 k_VB <= k_V0 + 4 per key; R-2 sums, m_sum 6; R-3 every VB line
    ``fault_events`` == [] and ``final_phase`` == ready; R-4 per VB line, gates outside the two that are False in VB
    and True in the V0 line of the same (key, offset_s) = 0 (a gate name on one side only = that line undecidable).
    A missing field / wrong type = that item undecidable (9.3); the result is then ``undecidable``, never pass.
    Only the S-15 / S-11 / S-2 stops go to ``fnd``; the R-1..R-4 values are a record until ``cmd_grid`` applies
    them."""
    lines, nums = cm.read_jsonl_numbered(path)
    out = {"input": [str(path), cm.sha256_file(path)], "lines": len(lines)}
    cells, form = {}, []
    for ln, n in zip(lines, nums):
        where = f"family_F|line {n}"
        cm.plate_check(fnd, where, ln.get("setting"), v5j.tag_of(ln), field="setting")   # supplement 4-3
        if ln.get("event") != FAMILY_F_EVENT:
            form.append(f"line {n}: event {ln.get('event')!r}")
        cells.setdefault((ln.get("key"), ln.get("setting"), _f_num(ln.get("offset_s"))), []).append(ln)
    offs = sorted({c[2] for c in cells if c[2] is not None})
    want = {(k, s, o) for k in FAMILY_F_KEYS for s in ("V0", "VB") for o in offs}
    if len(lines) != 2 * 2 * F_PHASES:
        form.append(f"{len(lines)} lines != 64")
    if len(offs) != F_PHASES:
        form.append(f"{len(offs)} offset_s values != 16")
    if set(cells) != want:
        form.append(f"cells {len(set(cells) ^ want)} differ from 2 keys x 16 offsets x V0 / VB")
    dup = [list(c) for c, v in cells.items() if len(v) != 1]
    if dup:
        form.append(f"{len(dup)} cells with more than one line")
    out["form"] = {"ok": not form, "problems": form}
    if form:
        fnd.stop("S-15", "family_F", f"supplement 4-5 / R4-B5 form: {form[:5]}")
        out["result"] = "undecidable"
        return out
    one = {c: v[0] for c, v in cells.items()}
    undec = []

    def gate(ln, name):
        g = ln.get("gates")
        v = g.get(name) if isinstance(g, dict) else None
        return v if isinstance(v, bool) else None

    k = {}
    for (key, s, off), ln in sorted(one.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        a, b = gate(ln, "Fmin_after_W"), gate(ln, "U57_outside")
        if a is None or b is None:   # this key / setting k is undecidable (9.3)
            undec.append({"item": "k", "key": key, "setting": s, "offset_s": off, "why": "gate missing / not bool"})
            k[(key, s)] = None
        elif not ((key, s) in k and k[(key, s)] is None):
            k[(key, s)] = k.get((key, s), 0) + (a is False or b is False)
    r1 = {}
    for key in sorted(FAMILY_F_KEYS):
        kv, k0 = k.get((key, "VB")), k.get((key, "V0"))
        r1[key] = None if kv is None or k0 is None else kv <= k0 + F_M
    kvs = [k.get((key, "VB")) for key in FAMILY_F_KEYS]
    k0s = [k.get((key, "V0")) for key in FAMILY_F_KEYS]
    tv = None if None in kvs else sum(kvs)
    t0 = None if None in k0s else sum(k0s)
    r2 = None if tv is None or t0 is None else tv <= t0 + F_M_SUM
    r3_v, r3_u, r4_v, r4_u = [], [], [], []
    for (key, s, off), ln in sorted(one.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        if s != "VB":
            continue
        fe, fp = ln.get("fault_events"), ln.get("final_phase")
        if not isinstance(fe, list) or not isinstance(fp, str):
            r3_u.append([key, off])
        elif fe or fp != "ready":
            r3_v.append([key, off, len(fe), fp])
        g1, g0 = ln.get("gates"), one[(key, "V0", off)].get("gates")
        if not isinstance(g1, dict) or not isinstance(g0, dict):
            r4_u.append([key, off, "gates missing"])
            continue
        n1, n0 = set(g1) - FAMILY_F_GATES, set(g0) - FAMILY_F_GATES
        if n1 != n0 or any(not isinstance(g1[x], bool) or not isinstance(g0[x], bool) for x in n1):
            r4_u.append([key, off, "gate names differ or not bool"])
            continue
        new = sorted(x for x in n1 if g1[x] is False and g0[x] is True)
        if new:
            r4_v.append([key, off, new])
    r3 = None if r3_u else not r3_v
    r4 = None if r4_u else not r4_v
    conds = list(r1.values()) + [r2, r3, r4]
    result = "undecidable" if (undec or None in conds) else ("pass" if all(conds) else "fail")
    out.update(k={f"{a}|{b}": v for (a, b), v in sorted(k.items())}, R1=r1,
               R2={"VB": tv, "V0": t0, "ok": r2}, R3={"ok": r3, "violations": r3_v, "undecidable": r3_u},
               R4={"ok": r4, "violations": r4_v, "undecidable": r4_u}, undecidable=undec, result=result)
    return out


def cmd_grid(args, repo, v5j, core):
    is_p3, mod = core.load_is_extend_start(repo)
    fnd = core.Findings()
    vb_files = dict(x.split("=", 1) for x in args.vb)
    inputs_44 = input_files_check(args, fnd)          # supplement 4-4 (S-15)
    v0_files, pair_rec = v0_pair(args, fnd)
    if set(vb_files) != set(STEMS):
        fnd.stop("S-15", "files", f"VB stems {sorted(vb_files)} != {list(STEMS)}")
    v0_runs, v0_meta = {}, {}
    for stem, path in v0_files.items():
        d = json.loads(Path(path).read_text("utf-8"))
        v0_meta[stem] = {"path": path, "sha256": cm.sha256_file(path),
                         "v5_setting": (d.get("meta") or {}).get("v5_setting"),
                         "tags": sorted({str(v5j.tag_of(run_tag_view(v5j, r, run))) for r, run in runs_of(d)})}
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
    rd = cm.RdCounter(core.bundle_key)   # R4 RD-7 / RD-8 / RD-9 / RD-10 (bundle H-9, grid part; supplement 2-2)
    n_F = 0
    for stem, path in vb_files.items():
        d = json.loads(Path(path).read_text("utf-8"))
        meta = d.get("meta") or {}
        rfile = cm.rel_file(path, repo)
        n = 0
        tags = {}
        for i, j, r, run in runs_indexed(d):
            n += 1
            k = run_key(stem, r, run)
            pos = f"results[{i}].runs[{j}]"                   # RD-7 3 position
            rkey = r.get("key") if isinstance(r.get("key"), str) else None             # RD-7 3: results[i].key
            rset = r.get("v5_setting") if isinstance(r.get("v5_setting"), str) else None   # results[i].v5_setting
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
            run_t = run_tag_view(v5j, r, run)   # rev8 R8-1: tag from the job record when the run has none
            t = str(v5j.tag_of(run_t))
            tags[t] = tags.get(t, 0) + 1
            v0 = v0_runs.get(k)
            row = {"run": k, "pass_p2": p, "v0_pass_p2": None if v0 is None else v0["pass_p2"]}
            # family F rows (v5 revision 5 5.1, supplement 4-5): the two keys' FS24 runs of grid_r67_main / _top
            in_F = stem in F_STEMS and r.get("key") in FAMILY_F_KEYS and run.get("event") == FAMILY_F_EVENT
            n_F += in_F
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
            # R4: jp3 gets the tag of the run view (run tag, else results[i] tag; supplement 2-2); RD-8 format
            # defects and RD-7 3 top-level mismatches stay undecidable (cm.jp3_apply), never a pass.
            tag = v5j.tag_of(run_t)
            rd.line("H-9", is_p3 is not None and isinstance(tag, str) and bool(is_p3(tag)))   # RD-9
            rod, ok = cm.jp3_rod_input(fnd, k, run, places[str(path)], v5j, True, t4h_log)
            res, why = v5j.jp3(run, is_p3, rod, tag=tag) if ok else ("t4h_unresolved", "R12-1 S-2")
            if ok:
                rd.jp3_result("H-9", res, why)
                cm.jp3_apply(fnd, k, res, why, "VB")   # rev8 R8-2: non-3 tag = not applicable + S-2
                if res == "H-7":
                    rd.jp3 += cm.jp3_rows("H-9", rfile, pos, run, rkey, rset, core)
            # J11 (RD-10, rev16:102~103, supplement 2-2 / 3-6): per run, setting = results[i].v5_setting only
            # (no file-meta fallback); missing = J11 undecidable (p2_v5j.j11_item setting_required=True)
            item = v5j.j11_item(run, setting=rset, setting_required=True)
            v5j.apply_j11(item, k, fnd)
            rd.j11 += cm.j11_rows("H-9", rfile, pos, item, rkey, rset)
            rd.j11_result("H-9", item)
            hr = run.get("hydraulics_record") or r.get("hydraulics_record") or {}
            post = hr.get("m2_clipped_steps_post_lift")
            if isinstance(post, list) and sum(post) > 0:
                fnd.stop("H-9", k, f"m2_clipped_steps_post_lift {post}")
            elif not isinstance(post, list):
                fnd.undec(k, "m2_clipped_steps_post_lift missing")
            law = (run.get("hydraulic_options") or r.get("hydraulic_options") or {}).get("m2_law")
            if law != M2_LAW:
                fnd.undec(k, f"m2_law {law!r} (rev6 #9: rerun)")
        if n != RUNS_PER_FILE:
            fnd.stop("S-15", stem, f"runs {n} != {RUNS_PER_FILE}")
        out_files[stem] = {"path": path, "sha256": cm.sha256_file(path), "runs": n, "tags": tags,
                           "meta_spec": meta.get("spec"), "meta_script": meta.get("script"),
                           "v5_setting": meta.get("v5_setting")}
    # supplement 4-5: the family F rows must be 12 (grid_r67_main 2 phases + grid_r67_top 4 phases, x 2 keys)
    if n_F != F_ROWS:
        fnd.stop("S-15", "family_F rows", f"{n_F} family F rows in the VB grid != {F_ROWS} (supplement 4-5: ask)")
    # R-1..R-4 always computed (supplement 4-5); applied only when a family-F row has a two-gate-only transition
    fam_rule = (family_f_rule(args.family_f, core, fnd, v5j) if Path(args.family_f).is_file()
                else {"input": [args.family_f, None], "result": "undecidable", "why": "file missing (4-4 S-15)"})
    applicable = bool(fam_F)
    if not applicable:
        fam_rule["application"] = "record (no two-gate-only pass -> fail in the 12 family F rows)"
    elif fam_rule["result"] == "pass":
        fam_rule["application"] = (f"R-1..R-4 pass: the two-gate failures of {len(fam_F)} family F rows are taken "
                                   "out of the v5 H-10 count (other gates stay per row)")
    else:
        fam_rule["application"] = f"R-1..R-4 {fam_rule['result']}: v5 criteria stop H-10 (ask)"
        fnd.stop("H-10", "family_F", f"rev5 5.2 R-1..R-4 {fam_rule['result']} with {len(fam_F)} family F transitions")
    if trans_nonF:
        fnd.stop("H-10", "grid", f"pass -> fail {len(trans_nonF)} (outside family F)")
    body = {"inputs": {"vb": out_files, "v0": v0_meta, "supplement_4-4": inputs_44}, "v5_options": mod,
            "v0_pair": pair_rec,
            "R11-2_t4h": {"search_dirs": {k: [str(d) for d in v] for k, v in places.items()}, "lookup": t4h_log},
            "grid": {"runs": len(rows), "pass_p2": sum(1 for x in rows if x["pass_p2"] is True),
                     "fail_p2": sum(1 for x in rows if x["pass_p2"] is False),
                     "pass_to_fail_all": trans_all, "pass_to_fail_outside_F": trans_nonF,
                     "family_F": fam_F, "family_F_rows": n_F, "family_F_applicable": applicable,
                     "family_F_rule": fam_rule,
                     "fault_runs": fault_runs,
                     "recorded_gate_differences": gate_diff, **fnd.as_dict()},
            "per_run": rows,
            # R4: RD-7 J-P3 / J11 rows of the grid part of H-9 (merged with the stage1 H-9 rows by ``stage1 merge``),
            # RD-8 / RD-9 / RD-10 counts of the grid part (RD-9 S-8 is decided on the H-9 sum in ``merge``), RD-13
            "R4": rd.as_dict(["H-9"]), "RD-13": {"H-9": cm.rd13_lists()["H-9"]}}
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
                   help="<stem>=<stored V0 grid json> (touch_phase/acceptance/c4g2_only/grid/<stem>.json, R3-E1); "
                        "all four are required (supplement 4-4, else S-15)")
    g.add_argument("--v0-sample", action="append", default=None,
                   help="<stem>=<same-commit V0 8-job sample json> (R3-E1)")
    g.add_argument("--v0-new", action="append", default=None,
                   help="<stem>=<resume_k1/h9_grid_v0/<stem>.json> (R3-E1, when the sample differs)")
    g.add_argument("--family-f", required=True,
                   help="resume_k1/h9_family_F.jsonl (required, supplement 4-4 / 4-5: R-1..R-4 always computed; "
                        "missing or another name = S-15)")
    g.add_argument("--t4h-root", action="append", default=None,
                   help="T4h folder (rev12 R12-1 / rev11 R11-2): only when no --vb file has a convention "
                        "folder <stem>_t4h/ or t4h/, at most one")
    return ap


def main(argv=None):
    return cm.run_main(TOOL_NAME, TOOL_VERSION, Path(__file__), argv, build_parser, {"grid": cmd_grid})


if __name__ == "__main__":
    sys.exit(main())
