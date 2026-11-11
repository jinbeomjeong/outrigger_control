"""Path-2 independent recount, Chrono batch V5-LAS-P5R4-K1 of las_p5r4_k1_rules.md (+ rev1).

Rules: las_p5r4_k1_rules.md (sha256 5ee2bac0...) 4.3 / 4.4 BT-C / 5.2 / 6.3 / 9 / 10 / 16, and the
record-only addendum las_p5r4_k1_rules_rev1.md. Author: control-expert (path 2).

Independence contract (rules 10.2):
  * Reads only batch.json, <case>/result.json, <case>/controller_commands.npz of the batch, the two
    REM reference npz files of BT-C, and the rules files. Does not open or import the path-1 judge
    tools or any project module.
  * Sources: LOC from controller_meta.slope_clearance_margin.order_gate.decisions first (events
    for cross-checks); t_S from controller_meta.soil.mode_starts, then events soil_mode_start;
    event names split(":", 1)[0] exact match; READY from p3b.P3-6_ready.
  * Command content hash: sha256 over, for name in (t_s, issued_u_m_s): name, dtype.str, shape,
    C-order bytes. C3 / REM R8 use the rows with t_s <= 128 s (rules 4.4 BT-C).
  * Priority (rules 16.6): stop > undecidable > fail > pass. rc != 0 rows counted and listed.

Exit codes: 0 pass (provisional), 1 fail or undecidable, 2 stop, 3 tool error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import statistics
import sys
import traceback

TOOL_NAME = "p5k_chrono_recount.py"
TOOL_VERSION = "1"
RULES_SHA = "5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979"
RULES_REV1_SHA = "f39846d6067a7bd409b4ac930d73ebde58a721728ec7d93703ff4627bf21e4b6"
DLL_SHA = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"
PERIOD_S = 0.1
SCM_THREADS = 4
F_LINE_N = 10414.589
G2P_N = 11414.589
CS_LIMIT_M = 0.001
R_MEDIAN_S = 1.0
R_MAX_S = 5.0
THIN_MARGIN_PERIODS = 12
HARNESS_B0_A_KN = 11.377  # las_chrono_rows header, rules 6.4
BTC_CUT_S = 128.0
TAG_VB = "final_C4G2_P3_LAS_K1"
TAG_V0 = "final_C4G2_LAS_K1"
REM_R7 = ("REM_J2_B_top_Fs4_VB_gateon", "ebf86d1d40af464e2e4e23d4ea79ad56721829e65d70cb4efb1d2cc072e4b559")
REM_R8 = ("REM_J2_B_top_Fs4_m1p1_VB_gateon", "97aace614a534a6aa95f67857947dcd541f9ecca1e9974eb5105fc017bf7c8aa")

B0 = dict(enable=True, sum_on_fraction_W=0.6, light_leg_fraction_of_F_min=3.5, slow_mean_fraction=0.16,
          sum_off_fraction_W=0.85, off_periods=5, max_s=1.5, rho_on=0.18, require_soil_response=True,
          min_active_periods=0, end_ramp_periods=0)
P5R4 = dict(B0, light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)
ARM_LABEL = {"ref": "P0", "cand": "P5r4"}

# rules 4.3 (12 rows)
ROWS = {
    "A1": dict(arm="ref", group="A", v5="VB", kc=1.0, mass=1.0, duration=160.0),
    "A2": dict(arm="cand", group="A", v5="VB", kc=1.0, mass=1.0, duration=160.0),
    "A3": dict(arm="ref", group="A", v5="VB", kc=3.0, mass=1.0, duration=160.0),
    "A4": dict(arm="cand", group="A", v5="VB", kc=3.0, mass=1.0, duration=160.0),
    "A5": dict(arm="ref", group="A", v5="V0", kc=1.0, mass=1.0, duration=160.0),
    "A6": dict(arm="cand", group="A", v5="V0", kc=1.0, mass=1.0, duration=160.0),
    "B1": dict(arm="ref", group="B", v5="VB", kc=None, mass=1.0, duration=200.0),
    "B2": dict(arm="cand", group="B", v5="VB", kc=None, mass=1.0, duration=200.0),
    "C1": dict(arm="ref", group="C", v5="VB", kc=None, mass=1.0, duration=120.0),
    "C2": dict(arm="cand", group="C", v5="VB", kc=None, mass=1.0, duration=120.0),
    "C3": dict(arm="ref", group="C", v5="VB", kc=None, mass=1.1, duration=180.0),
    "C4": dict(arm="cand", group="C", v5="VB", kc=None, mass=1.1, duration=180.0),
}
PAIRS = [("A1", "A2"), ("A3", "A4"), ("A5", "A6"), ("B1", "B2"), ("C1", "C2"), ("C3", "C4")]
FIXED_ARGS = dict(pad_variant="dwg_rear250", fs_kN=4.0, seed=20261026, pressure_grade="normal",
                  imu_grade="ideal", level="top", threads=SCM_THREADS)
I_KEYS = ["P3-1_recontact_pass", "P3-1_crawler_zero_after_ready", "P3-2_within", "P3-3_within",
          "P3-4_within_0p2", "P3-5_within", "P3-6_within", "P3-7_within", "P3-8_within"]
PAIR_ARGV_FREE = {"--las-candidate", "--case", "--out-root"}
FORBIDDEN_OPTS = {"--k1-order-gate", "--k1-forced-block", "--las-off"}

EV_LOC = "crawler_liftoff_confirmed"
EV_SOIL_START = "soil_mode_start"
EV_REVOKED = "INFO_LOC_REVOKED"
EV_E3C10 = "INFO_LOC_CLEARANCE_MARGIN"
EV_FLAT = "INFO_LOC_FLAT_SOIL_MARGIN"
EV_FLAT_SKIP = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"
EV_BIAS = "INFO_CLEARANCE_BIAS"
EV_ANCHOR = "INFO_LOC_CLEARANCE_ANCHOR"
USES_ANCHOR = ("1", "2", "1+2")
PRIORITY = {"stop": 4, "undecidable": 3, "fail": 2, "pass": 1}


def per(t):
    return None if t is None else round(t / PERIOD_S)


def base_name(n):
    return str(n).split(":", 1)[0]


def suffix(n):
    p = str(n).split(":", 1)
    return p[1] if len(p) > 1 else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


MISSING = object()


def dig(d, path, default=None):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def has(d, path):
    return dig(d, path, MISSING) is not MISSING


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not (isinstance(x, float) and math.isnan(x))


def combine(statuses):
    best = None
    for s in statuses:
        if s in PRIORITY and (best is None or PRIORITY[s] > PRIORITY[best]):
            best = s
    return best


def same_float(a, b):
    if a is None or b is None:
        return a is None and b is None
    return num(a) and num(b) and float(a) == float(b)


def argv_value(argv, opt):
    for i, tok in enumerate(argv):
        if tok == opt and i + 1 < len(argv):
            return argv[i + 1]
        if tok.startswith(opt + "="):
            return tok.split("=", 1)[1]
    return None


def strip_argv(argv, opts):
    out, skip = [], False
    for tok in argv:
        if skip:
            skip = False
            continue
        if tok in opts:
            skip = True
            continue
        if any(tok.startswith(o + "=") for o in opts):
            continue
        out.append(tok)
    return out


def command_content_hash(npz_path, cut_s=None):
    """sha256 over (name, dtype.str, shape, bytes) of t_s and issued_u_m_s (optionally t_s <= cut)."""
    import numpy as np  # dynamics-dev; only used to read the npz arrays
    with np.load(npz_path, allow_pickle=False) as z:
        t = np.asarray(z["t_s"])
        u = np.asarray(z["issued_u_m_s"])
    if cut_s is not None:
        m = t <= cut_s
        t, u = t[m], u[m]
    h = hashlib.sha256()
    n_rows = int(t.shape[0]) if t.ndim else 0
    for name, a in (("t_s", t), ("issued_u_m_s", u)):
        a = np.ascontiguousarray(a)
        h.update(name.encode())
        h.update(a.dtype.str.encode())
        h.update(repr(tuple(a.shape)).encode())
        h.update(a.tobytes())
    return h.hexdigest(), n_rows


# ----------------------------------------------------------------------------- per row

def missing_reasons(entry, res, err):
    if entry is None:
        return ["no batch entry"]
    r = []
    if entry.get("rc") != 0:
        r.append(f"rc={entry.get('rc')!r}")
    if err:
        r.append(err)
        return r
    cm = res.get("controller_meta")
    if not isinstance(cm, dict) or "error" in cm:
        r.append("controller_meta error/absent")
    else:
        soil = cm.get("soil")
        if not isinstance(soil, dict) or "error" in soil:
            r.append("controller_meta.soil error/absent")
        elif soil.get("restored_from") is not None:
            r.append(f"soil.restored_from={soil.get('restored_from')!r}")
    if not isinstance(res.get("events"), list):
        r.append("events error/absent")
    if res.get("restored_from") is not None:
        r.append(f"restored_from={res.get('restored_from')!r}")
    return r


def recount_row(res):
    cm = res["controller_meta"]
    soil = cm["soil"]
    og = dig(cm, "slope_clearance_margin.order_gate")
    ev = [(per(e.get("t_s")), e.get("t_s"), str(e.get("name"))) for e in res.get("events", []) if isinstance(e, dict)]
    names = {}
    for (_n, _t, nm) in ev:
        names[base_name(nm)] = names.get(base_name(nm), 0) + 1
    ms_meta = soil.get("mode_starts")
    ms_ev = [(n, t) for (n, t, nm) in ev if base_name(nm) == EV_SOIL_START]
    if isinstance(ms_meta, list):
        starts = sorted([dict(t_s=m.get("t_s"), n=per(m.get("t_s"))) for m in ms_meta], key=lambda s: s["n"] if s["n"] is not None else -1)
        starts_source = "controller_meta.soil.mode_starts"
    else:
        starts = sorted([dict(t_s=t, n=n) for (n, t) in ms_ev], key=lambda s: s["n"])
        starts_source = "events soil_mode_start"
    decs_raw = og.get("decisions") if isinstance(og, dict) else None
    has_dec = isinstance(decs_raw, list)
    decs = sorted([d for d in (decs_raw or []) if isinstance(d, dict)],
                  key=lambda d: (d.get("t_loc_s") is None, d.get("t_loc_s") or 0.0))
    table = []
    for i, d in enumerate(decs):
        nP, nS = per(d.get("t_P_s")), per(d.get("t_S_s"))
        table.append(dict(i=i, n_loc=per(d.get("t_loc_s")), t_loc_s=d.get("t_loc_s"), t_P_s=d.get("t_P_s"),
                          t_S_s=d.get("t_S_s"), n_P=nP, n_S=nS,
                          dP=(nP - nS) if (nP is not None and nS is not None) else None,
                          r4=d.get("r4_due_without_gate") is True, applied=d.get("applied") is True,
                          would_block=d.get("would_block") is True, rec_dP=d.get("dP")))
    r4 = [x for x in table if x["r4"]]
    L1 = r4[0] if r4 else None
    loc_ev = sorted(n for (n, _t, nm) in ev if base_name(nm) == EV_LOC)
    loc_ev_t = sorted(t for (_n, t, nm) in ev if base_name(nm) == EV_LOC and t is not None)
    e3 = sorted({n for (n, _t, nm) in ev if base_name(nm) == EV_E3C10})
    applied_ev, skipped_ev = {}, {}
    for (n, _t, nm) in ev:
        if base_name(nm) == EV_FLAT:
            applied_ev[n] = applied_ev.get(n, 0) + 1
        elif base_name(nm) == EV_FLAT_SKIP and suffix(nm) == "order":
            skipped_ev[n] = skipped_ev.get(n, 0) + 1
    skipped_any = sum(1 for (_n, _t, nm) in ev if base_name(nm) == EV_FLAT_SKIP)
    rv_ev = sorted(n for (n, _t, nm) in ev if base_name(nm) == EV_REVOKED)
    rv_meta = sorted(per(t) for t in (dig(cm, "loc_revoke.t_revoke_s") or []))
    las = cm.get("liftoff_approach_slow") or {}
    p3b = res.get("p3b") or {}
    checks = p3b.get("checks") if isinstance(p3b.get("checks"), dict) else {}
    fa = dig(p3b, "P3-3_leg_force.F_min_after_N")
    ft = dig(p3b, "P3-3_leg_force.F_min_transient_N")
    sm = dig(p3b, "P3-5_clearance_stroke.s_motor_max_m")

    def agg(x, f):
        if isinstance(x, list):
            xs = [v for v in x if num(v)]
            return f(xs) if xs and len(xs) == len(x) else None
        return x if num(x) else None

    phases = res.get("phases") or []
    final_phase = phases[-1].get("phase") if phases and isinstance(phases[-1], dict) else None
    # rev1 anchor record
    p1, p2 = names.get(EV_BIAS, 0) > 0, names.get(EV_ANCHOR, 0) > 0
    path = "1+2" if (p1 and p2) else ("1" if p1 else ("2" if p2 else "3"))
    tp_last = soil.get("t_P_s")
    first_loc_n = loc_ev[0] if loc_ev else None
    tp_first, tp_first_src = None, None
    if first_loc_n is not None:
        hit = [x for x in table if x["n_loc"] == first_loc_n]
        if hit:
            tp_first, tp_first_src = hit[0]["t_P_s"], "order_gate.decisions at first LOC"
    if tp_first is None and len(loc_ev) == 1 and tp_last is not None:
        tp_first, tp_first_src = tp_last, "single LOC: controller_meta.soil.t_P_s"
    app = soil.get("bias_corner_m")
    nonzero = isinstance(app, list) and any(num(v) and v != 0.0 for v in app)
    anchor = dict(path=path, n_loc=len(loc_ev), t_L_first_s=loc_ev_t[0] if loc_ev_t else None,
                  t_L_last_s=loc_ev_t[-1] if loc_ev_t else None, n_L_first=first_loc_n,
                  n_L_last=loc_ev[-1] if loc_ev else None, t_P_first_s=tp_first, t_P_first_source=tp_first_src,
                  n_P_first=per(tp_first), t_P_last_s=tp_last, n_P_last=per(tp_last),
                  t_loc_meta_s=soil.get("t_loc_s"), bias_corner_raw_m=soil.get("bias_corner_raw_m"),
                  bias_corner_m=app, loc_anchor_bias_mm=soil.get("loc_anchor_bias_mm"),
                  corner_order=soil.get("corner_order"),
                  anchor_meta_agree=(((path in ("2", "1+2")) == (soil.get("loc_anchor_applied") is True))
                                     and (path == "3" or nonzero)),
                  missing=[k for k in ("t_P_s", "bias_corner_raw_m", "bias_corner_m") if k not in soil])
    # cross-check (record only) against the run_S9 per-LOC record loc_corrections.locs[] (cad-expert ff07ac9)
    lc = res.get("loc_corrections")
    lc_locs = lc.get("locs") if isinstance(lc, dict) else None
    if isinstance(lc_locs, list):
        pset = sorted({str(e.get("path")) for e in lc_locs if isinstance(e, dict)})
        lc_path = ("1+2" if {"1", "2"} <= set(pset) else ("1" if "1" in pset else ("2" if "2" in pset else "3")))
        n_ps = [e.get("n_P") for e in lc_locs if isinstance(e, dict)]
        anchor["loc_corrections"] = dict(
            path=lc_path, n_locs=len(lc_locs), n_P_first=n_ps[0] if n_ps else None, n_P_last=n_ps[-1] if n_ps else None,
            agree=dict(path=(lc_path == path), n_loc=(len(lc_locs) == len(loc_ev)),
                       n_P_last=(not n_ps or n_ps[-1] == per(tp_last)),
                       n_P_first=(tp_first is None or not n_ps or n_ps[0] == per(tp_first))))
    else:
        anchor["loc_corrections"] = None
    # crawler departure (rules 10.1: a row that ends before the lift is judged, not missing)
    dep = dig(res, "p3b.departure.departed", MISSING)
    has_fa = has(res, "p3b.P3-3_leg_force.F_min_after_N")
    has_ft = has(res, "p3b.P3-3_leg_force.F_min_transient_N")
    if has_fa and has_ft:
        f_state = "present"
    elif (not has_fa) and (not has_ft) and dep is False:
        f_state = "no_departure"
    else:
        f_state = "missing"
    return dict(
        decisions=table, has_decisions_key=has_dec, L1=L1, n_r4=len(r4),
        any_r4_applied=any(x["r4"] and x["applied"] for x in table),
        order_gate_enabled=None if not isinstance(og, dict) else og.get("enabled"),
        gate_setting=dig(cm, "slope_clearance_margin.settings.flat_soil_margin_order_gate"),
        mode_starts=starts, mode_starts_source=starts_source, loc_event_periods=loc_ev, e3c10_periods=e3,
        applied_event_periods=applied_ev, skipped_order_event_periods=skipped_ev, skipped_any=skipped_any,
        revokes_events=rv_ev, revokes_meta=rv_meta, revokes_meta_count=dig(cm, "loc_revoke.revokes"),
        las=dict(start_s=las.get("start_s"), end_s=las.get("end_s"), end_reason=las.get("end_reason"),
                 active_periods=las.get("active_periods"), ramp=las.get("ramp"), settings=las.get("settings")),
        checks={k: checks.get(k, MISSING) for k in I_KEYS},
        late_loc=dict(reapproach=checks.get("P3-2_late_loc_reapproach"), revoked=checks.get("P3-2_late_loc_revoked")),
        window_short=checks.get("P3-4_window_short"),
        F_after_N=agg(fa, min), F_tr_N=agg(ft, min), s_max_m=agg(sm, max),
        F_state=f_state, departed=None if dep is MISSING else dep,
        has_s=has(res, "p3b.P3-5_clearance_stroke.s_motor_max_m"),
        has_ready=has(res, "p3b.P3-6_ready.t_ready_after_loop_start_s"),
        t_ready=dig(res, "p3b.P3-6_ready.t_ready_after_loop_start_s"),
        final_phase=final_phase, has_phases=isinstance(res.get("phases"), list),
        fault_warn=sorted(n for n in names if n.startswith("FAULT") or n.startswith("WARN")),
        anchor=anchor,
    )


# ----------------------------------------------------------------------------- recount

def recount(batch_dir, rules_path, rules_rev1_path, rem_batch_dir):
    files_read = {}
    K = {f"K-{i}": [] for i in range(10)}

    def kadd(k, row, item, ok, got=None, want=None):
        K[k].append(dict(row=row, item=item, ok=ok, got=got, want=want))

    for path, want, label in ((rules_path, RULES_SHA, "rules"), (rules_rev1_path, RULES_REV1_SHA, "rules_rev1")):
        got = sha256_file(path) if os.path.isfile(path) else None
        if got:
            files_read[os.path.abspath(path)] = got
        sp = os.path.splitext(path)[0] + ".sha256"
        rec = None
        if os.path.isfile(sp):
            files_read[os.path.abspath(sp)] = sha256_file(sp)
            with open(sp, encoding="utf-8") as f:
                t = f.read().strip()
            rec = t.split()[0] if t else None
        kadd("K-0", None, f"{label}_sha_eq_sha256_file", got is not None and got == rec, got=got, want=rec)
        kadd("K-0", None, f"{label}_sha_eq_constant", got == want, got=got, want=want)

    bpath = os.path.join(batch_dir, "batch.json")
    with open(bpath, encoding="utf-8") as f:
        batch = json.load(f)
    files_read[os.path.abspath(bpath)] = sha256_file(bpath)
    entries, counts, error_rows = {}, {}, []
    for e in batch.get("cases") or []:
        pid = e.get("p5k_id")
        if pid not in ROWS:
            kadd("K-9", e.get("case"), "row_in_rules_table", False, got=pid)
            continue
        counts[pid] = counts.get(pid, 0) + 1
        entries[pid] = e  # rerun (rerun_of) replaces the first entry, rules 10.1
        if e.get("rc") != 0:
            error_rows.append(dict(p5k_id=pid, case=e.get("case"), rc=e.get("rc"), rerun_of=e.get("rerun_of")))

    rows, res_by = {}, {}
    for pid, spec in ROWS.items():
        e = entries.get(pid)
        row = dict(p5k_id=pid, arm=spec["arm"], entries_in_batch=counts.get(pid, 0),
                   case=None if e is None else e.get("case"), rerun_of=None if e is None else e.get("rerun_of"))
        res, err = None, None
        if e is not None:
            rp = os.path.join(batch_dir, str(e.get("case")), "result.json")
            if os.path.isfile(rp):
                try:
                    with open(rp, encoding="utf-8") as f:
                        res = json.load(f)
                    files_read[os.path.abspath(rp)] = sha256_file(rp)
                except Exception as exc:
                    err = f"result.json unreadable: {exc!r}"
            else:
                err = "result.json missing"
        reasons = missing_reasons(e, res, err)
        if reasons:
            row.update(status="MISSING", missing_reasons=reasons)
            kadd("K-9", pid, "missing_assigned", True, got=reasons)
        else:
            try:
                row.update(recount_row(res))
                row["status"] = "PRESENT"
                res_by[pid] = (e, res)
            except Exception as exc:
                row.update(status="RECOUNT_ERROR", error=repr(exc))
                kadd("K-8", pid, "recount_error", False, got=repr(exc))
            npz = os.path.join(batch_dir, str(e.get("case")), "controller_commands.npz")
            if os.path.isfile(npz):
                files_read[os.path.abspath(npz)] = sha256_file(npz)
                row["cmd_hash"], row["cmd_rows"] = command_content_hash(npz)
                if pid == "C3":
                    row["cmd_hash_cut128"], row["cmd_rows_cut128"] = command_content_hash(npz, BTC_CUT_S)
            else:
                row["cmd_hash"] = None
                kadd("K-9", pid, "controller_commands.npz_present", False)
        rows[pid] = row

    present = list(res_by)
    # ---- K-1 / K-2
    heads = {}
    for pid in present:
        e, res = res_by[pid]
        g = dig(res, "code_state.git_at_start") or {}
        heads[pid] = g.get("head")
        kadd("K-1", pid, "dirty_empty", g.get("dirty") == [], got=g.get("dirty"))
        bh = dig(e, "code_at_launch.git.head")
        if bh is not None:
            kadd("K-1", pid, "batch_head_eq_result_head", bh == g.get("head"), got=g.get("head"), want=bh)
    uh = sorted({str(h) for h in heads.values()})
    kadd("K-1", None, "single_head", len(uh) == 1 and uh[0] != "None", got=uh)
    c2s = {}
    for pid in present:
        e, res = res_by[pid]
        fa = dig(res, "code_state.files_at_start") or {}
        rs = {v.get("path"): v.get("sha256") for v in fa.values() if isinstance(v, dict) and "path" in v}
        bs = dig(e, "code_at_launch.files") or {}
        for p, s in bs.items():
            if p in rs:
                kadd("K-2", pid, f"sha_batch_eq_result:{p}", s == rs[p], got=rs[p], want=s)
        c2s[pid] = rs.get("03_src/outrigger_sim/control/c2.py")
    uc = sorted({str(v) for v in c2s.values()})
    kadd("K-2", None, "single_c2_sha", len(uc) == 1 and uc[0] != "None", got=uc)
    # rules 5.2 code files (run_S9 code_files_at_start: worktree_sha256 / head_blob_sha256 per file, head)
    cfa = {pid: res_by[pid][1].get("code_files_at_start") for pid in present}
    have = {pid: v for pid, v in cfa.items() if isinstance(v, dict)}
    if have:
        for pid in present:
            if pid not in have:
                kadd("K-2", pid, "code_files_at_start_present", False)
                continue
            gh = dig(res_by[pid][1], "code_state.git_at_start.head")
            kadd("K-2", pid, "code_files_at_start.head_eq_git_at_start", have[pid].get("head") == gh,
                 got=have[pid].get("head"), want=gh)
        files = sorted({f for v in have.values() for f in (v.get("files") or {})})
        for f in files:
            for fld in ("worktree_sha256", "head_blob_sha256"):
                vals = sorted({str(dig(v, "files", {}).get(f, {}).get(fld)) for v in have.values()})
                kadd("K-2", f, f"{fld}_single_over_rows", len(vals) == 1 and vals[0] != "None", got=vals)
    else:
        kadd("K-2", None, "code_files_at_start_present", None, got="absent in every row")
    # ---- K-3 tag, K-4 gate / latch / forced, K-5 LAS-b settings, K-6 run conditions
    kadd("K-6", None, "batch_mixed_hull_mode_false", batch.get("mixed_hull_mode") is False, got=batch.get("mixed_hull_mode"))
    pool = {}
    for pid in present:
        e, res = res_by[pid]
        spec = ROWS[pid]
        tag = TAG_V0 if spec["v5"] == "V0" else TAG_VB
        ec = dig(res, "c2_setup.expect_controller") or {}
        kadd("K-3", pid, "expect_controller_ok", ec.get("ok") is True and ec.get("name") == tag, got=[ec.get("ok"), ec.get("name")], want=tag)
        at = dig(res, "args.expect_controller")
        kadd("K-3", pid, "args_expect_controller", at == tag, got=at, want=tag)
        kadd("K-3", pid, "no_TCL", isinstance(at, str) and "_TCL" not in at, got=at)
        r = rows[pid]
        kadd("K-4", pid, "flat_soil_margin_order_gate_true", r["gate_setting"] is True, got=r["gate_setting"])
        kadd("K-4", pid, "order_gate_enabled_true", r["order_gate_enabled"] is True, got=r["order_gate_enabled"])
        kadd("K-4", pid, "decisions_key", r["has_decisions_key"] is True)
        kadd("K-4", pid, "c2_setup.k1_order_gate_preset", dig(res, "c2_setup.k1_order_gate") == "preset",
             got=dig(res, "c2_setup.k1_order_gate"))
        tcl = dig(res, "controller_meta.touch_creep_latch")
        if isinstance(tcl, dict):
            en = tcl.get("enable", dig(tcl, "settings.enable"))
            kadd("K-4", pid, "touch_creep_latch_off", en is False, got=en)
        else:
            kadd("K-4", pid, "touch_creep_latch_off", None, got="absent")
        fb = dig(res, "c2_setup.k1_forced_block")
        fbr = fb.get("requested") if isinstance(fb, dict) else fb
        kadd("K-4", pid, "k1_forced_block_off", fbr == "off", got=fbr)
        cls = fb.get("class") if isinstance(fb, dict) else None
        if cls is not None:
            kadd("K-4", pid, "controller_class_C2Controller", str(cls).split(".")[-1] == "C2Controller", got=cls)
        kadd("K-4", pid, "no_meta_k1_forced_block", "k1_forced_block" not in (res.get("controller_meta") or {}))
        want = B0 if spec["arm"] == "ref" else P5R4
        s = r["las"]["settings"] or {}
        bad = {k: (s.get(k), v) for k, v in want.items() if s.get(k) != v}
        kadd("K-5", pid, "las_settings_eq_" + ARM_LABEL[spec["arm"]], bad == {}, got=bad or None)
        lc = dig(res, "c2_setup.las_candidate")
        req = lc.get("requested") if isinstance(lc, dict) else lc
        kadd("K-5", pid, "c2_setup.las_candidate.requested", req == ARM_LABEL[spec["arm"]], got=req)
        if isinstance(lc, dict) and isinstance(lc.get("settings"), dict):
            kadd("K-5", pid, "c2_setup_settings_eq_meta", lc["settings"] == s)
        bl = e.get("las_candidate")
        if bl is not None:
            kadd("K-5", pid, "batch_las_candidate", bl == ARM_LABEL[spec["arm"]], got=bl)
        args = res.get("args") or {}
        pl = res.get("placement") or {}
        nt = res.get("num_threads_chrono", dig(res, "meta.num_threads_chrono"))
        kadd("K-6", pid, "threads_4", args.get("threads") == SCM_THREADS and nt == SCM_THREADS, got=[args.get("threads"), nt])
        kadd("K-6", pid, "omp_passive", e.get("omp_wait_policy") == "PASSIVE" and pl.get("omp_wait_policy") == "PASSIVE",
             got=[e.get("omp_wait_policy"), pl.get("omp_wait_policy")])
        hh = res.get("hull_hook") or {}
        kadd("K-6", pid, "hull_fast", hh.get("mode") == "fast" and hh.get("requested") == "fast", got=[hh.get("mode"), hh.get("requested")])
        kadd("K-6", pid, "hull_fallback_none", hh.get("fallback_reason") is None, got=hh.get("fallback_reason"))
        kadd("K-6", pid, "dll_sha", hh.get("dll_sha256") == DLL_SHA, got=hh.get("dll_sha256"))
        he = e.get("hull_hook_effective")
        if isinstance(he, dict):
            kadd("K-6", pid, "batch_hull_effective_fast", he.get("mode") == "fast" and he.get("fallback_reason") is None, got=he)
        kadd("K-6", pid, "placement_eq_plan", pl.get("mode") is not None and pl.get("mode") == e.get("planned_pool")
             and (e.get("pool") is None or e.get("pool") == e.get("planned_pool")),
             got=[pl.get("mode"), e.get("planned_pool"), e.get("pool")])
        kadd("K-6", pid, "affinity_ok", pl.get("affinity_ok") is True, got=pl.get("affinity_ok"))
        kadd("K-6", pid, "power_throttling_off_ok", pl.get("power_throttling_off_ok") is True, got=pl.get("power_throttling_off_ok"))
        pool[pid] = pl.get("mode")
        # K-7 per row
        for fk, fv in FIXED_ARGS.items():
            kadd("K-7", pid, f"args_{fk}", args.get(fk) == fv, got=args.get(fk), want=fv)
        kadd("K-7", pid, "args_duration", args.get("duration") == spec["duration"], got=args.get("duration"), want=spec["duration"])
        kadd("K-7", pid, "args_mass_scale", (args.get("mass_scale") if args.get("mass_scale") is not None else 1.0) == spec["mass"],
             got=args.get("mass_scale"), want=spec["mass"])
    for a, b in PAIRS:
        if a in pool and b in pool:
            kadd("K-6", f"{a}/{b}", "pair_same_pool", pool[a] == pool[b], got=[pool[a], pool[b]])
    # ---- K-7 argv
    argvs = {pid: list(entries[pid].get("argv") or []) for pid in entries}
    for pid, av in argvs.items():
        spec = ROWS[pid]
        opts = {t.split("=", 1)[0] for t in av if t.startswith("--")}
        kadd("K-7", pid, "no_forbidden_options", not (opts & FORBIDDEN_OPTS), got=sorted(opts & FORBIDDEN_OPTS))
        kadd("K-7", pid, "argv_las_candidate", argv_value(av, "--las-candidate") == ARM_LABEL[spec["arm"]],
             got=argv_value(av, "--las-candidate"))
        tag = TAG_V0 if spec["v5"] == "V0" else TAG_VB
        kadd("K-7", pid, "argv_expect_controller", argv_value(av, "--expect-controller") == tag, got=argv_value(av, "--expect-controller"))
        if spec["group"] == "A":
            kadd("K-7", pid, "argv_rigid_base", "--rigid-base" in opts)
            kc = argv_value(av, "--crawler-kn-scale")
            kadd("K-7", pid, "argv_crawler_kn_scale", (float(kc) if kc is not None else 1.0) == spec["kc"], got=kc, want=spec["kc"])
        else:
            kadd("K-7", pid, "argv_no_rigid_base", "--rigid-base" not in opts and "--crawler-kn-scale" not in opts)
        if spec["group"] == "B":
            kadd("K-7", pid, "argv_soil_patch", "--soil-patch" in opts)
        ms = argv_value(av, "--mass-scale")
        kadd("K-7", pid, "argv_mass_scale", (float(ms) if ms is not None else 1.0) == spec["mass"], got=ms)
    for a, b in PAIRS:
        if a in argvs and b in argvs:
            kadd("K-7", f"{a}/{b}", "pair_argv_diff_las_candidate_only",
                 strip_argv(argvs[a], PAIR_ARGV_FREE) == strip_argv(argvs[b], PAIR_ARGV_FREE))
    # ---- K-8 (adopt2 K-8 (a)..(e))
    for pid in present:
        r = rows[pid]
        if r.get("status") != "PRESENT":
            continue
        starts = r["mode_starts"]
        fs = starts[0]["n"] if starts else None
        loc_after = [n for n in r["loc_event_periods"] if fs is not None and n > fs]
        non_e3 = [n for n in loc_after if n not in r["e3c10_periods"]]
        kadd("K-8", pid, "a_decisions_eq_nonE3c10_locs_after_soil_start", len(r["decisions"]) == len(non_e3),
             got=len(r["decisions"]), want=len(non_e3))
        for d in r["decisions"]:
            kadd("K-8", pid, f"b_decision{d['i']}_at_loc_event", d["n_loc"] in r["loc_event_periods"], got=d["n_loc"])
            prior = [s for s in starts if s["n"] is not None and d["n_loc"] is not None and s["n"] < d["n_loc"]]
            kadd("K-8", pid, f"c_decision{d['i']}_t_S_eq_last_prior_start", bool(prior) and same_float(d["t_S_s"], prior[-1]["t_s"]),
                 got=d["t_S_s"], want=prior[-1]["t_s"] if prior else None)
            if d["rec_dP"] != d["dP"]:
                # record only (not an adopt2 K-8 item): recorded dP differs from round(t_P/0.1) - round(t_S/0.1)
                r.setdefault("recorded_dP_mismatch", []).append(dict(i=d["i"], recorded=d["rec_dP"], recount=d["dP"]))
        kadd("K-8", pid, "d_revoke_meta_eq_events", r["revokes_events"] == r["revokes_meta"] and
             (r["revokes_meta_count"] is None or r["revokes_meta_count"] == len(r["revokes_events"])),
             got=dict(events=r["revokes_events"], meta=r["revokes_meta"], count=r["revokes_meta_count"]))
        ea, es = {}, {}
        for d in r["decisions"]:
            if d["applied"]:
                ea[d["n_loc"]] = ea.get(d["n_loc"], 0) + 1
            if d["would_block"] and not d["applied"]:
                es[d["n_loc"]] = es.get(d["n_loc"], 0) + 1
        kadd("K-8", pid, "e_applied_events", ea == r["applied_event_periods"], got=r["applied_event_periods"], want=ea)
        kadd("K-8", pid, "e_skipped_order_events", es == r["skipped_order_event_periods"], got=r["skipped_order_event_periods"], want=es)
        kadd("K-8", pid, "e_skipped_other_suffix_0", r["skipped_any"] == sum(r["skipped_order_event_periods"].values()), got=r["skipped_any"])

    # ---- BT-C
    btc = dict(C1=None, C3=None)
    if rem_batch_dir:
        for pid, (case, want_sha) in (("C1", REM_R7), ("C3", REM_R8)):
            p = os.path.join(rem_batch_dir, case, "controller_commands.npz")
            if not os.path.isfile(p):
                btc[pid] = dict(ok=False, reason="REM npz missing", path=p)
                continue
            fs = sha256_file(p)
            files_read[os.path.abspath(p)] = fs
            if fs != want_sha:
                btc[pid] = dict(ok=False, reason="REM npz file sha differs", got=fs, want=want_sha)
                continue
            ref_hash, n = command_content_hash(p, BTC_CUT_S if pid == "C3" else None)
            row = rows.get(pid) or {}
            got = row.get("cmd_hash_cut128") if pid == "C3" else row.get("cmd_hash")
            btc[pid] = dict(ok=(got is not None and got == ref_hash), got=got, want=ref_hash, rem_rows=n,
                            row_rows=row.get("cmd_rows_cut128") if pid == "C3" else row.get("cmd_rows"))
    else:
        btc = dict(C1=dict(ok=None, reason="no --rem-batch"), C3=dict(ok=None, reason="no --rem-batch"))

    # ---- pairs (6.3)
    pairs = {}
    obs_A = []
    for a, b in PAIRS:
        ra, rb = rows[a], rows[b]
        p = dict(ref=a, cand=b, undecidable=[], undecidable_by={}, violations={})
        if ra.get("status") != "PRESENT" or rb.get("status") != "PRESENT":
            p["undecidable"].append("row missing (rules 10.1)")
            pairs[f"{a}/{b}"] = p
            continue
        miss_I = [k for k in I_KEYS for r in (ra, rb) if r["checks"].get(k) is MISSING]
        if miss_I:
            p["undecidable"].append(f"I keys missing: {sorted(set(miss_I))}")
        if not (ra["has_phases"] and rb["has_phases"] and ra["has_ready"] and rb["has_ready"]):
            p["undecidable"].append("phases / P3-6_ready missing")
        cc2 = []
        late_flag = []
        for k in I_KEYS:
            va, vb = ra["checks"].get(k), rb["checks"].get(k)
            if va is MISSING or vb is MISSING:
                continue
            if va is True and vb is not True:
                if k == "P3-2_within" and (rb["late_loc"]["reapproach"] is True or rb["late_loc"]["revoked"] is True):
                    late_flag.append(k)
                else:
                    cc2.append(f"a:{k}:{va}->{vb}")
        if ra["final_phase"] == "ready" and rb["final_phase"] != "ready":
            cc2.append(f"b:final_phase:ready->{rb['final_phase']}")
        if ra["t_ready"] is not None and rb["t_ready"] is None:
            cc2.append("b:first_ready_lost")
        new = sorted(set(rb["fault_warn"]) - set(ra["fault_warn"]))
        if new:
            cc2.append("c:new_events:" + ",".join(new))
        p["violations"]["CC-2"] = cc2
        p["LATE_LOC_P32"] = late_flag
        # CC-F
        # F keys: "missing" (absent with departure true / departure key absent) -> CC-F, G-2'C undecidable;
        # "no_departure" (absent, p3b.departure.departed false) -> judged, no value (rules 10.1: not missing)
        p["F_state"] = [ra["F_state"], rb["F_state"]]
        und_F = [f"{s}:P3-3 force keys missing" for s, r in (("ref", ra), ("cand", rb)) if r["F_state"] == "missing"]
        for cname in ("CC-F", "G-2'C"):
            if und_F:
                p["undecidable_by"].setdefault(cname, []).extend(und_F)
        fr, fc = ra["F_after_N"], rb["F_after_N"]
        p["CC-F"] = dict(in_scope=num(fr) and fr >= F_LINE_N, ref_N=fr, cand_N=fc,
                         ref_no_departure=ra["F_state"] == "no_departure", cand_no_departure=rb["F_state"] == "no_departure")
        p["violations"]["CC-F"] = (["cand below line" if num(fc) else "cand no value (no departure)"]
                                   if (p["CC-F"]["in_scope"] and not (num(fc) and fc >= F_LINE_N)) else [])
        # G-2'C on A pairs
        if a.startswith("A"):
            ok = num(fc) and fc >= G2P_N and num(rb["F_tr_N"]) and rb["F_tr_N"] >= G2P_N
            p["G-2'C"] = dict(cand_after_N=fc, cand_transient_N=rb["F_tr_N"], ok=bool(ok),
                              cand_no_departure=rb["F_state"] == "no_departure")
            p["violations"]["G-2'C"] = [] if ok else (["cand below 11414.589 N"] if rb["F_state"] != "no_departure"
                                                      else ["cand no value (no departure)"])
            p["record_A"] = dict(d_F_after_N=(fc - fr) if (num(fc) and num(fr)) else None,
                                 cand_minus_harness_b0_kN=(fc / 1000.0 - HARNESS_B0_A_KN) if num(fc) else None,
                                 ref_minus_harness_b0_kN=(fr / 1000.0 - HARNESS_B0_A_KN) if num(fr) else None)
            started = rb["las"]["start_s"] is not None
            ramp = rb["las"]["ramp"] or {}
            obs_A.append(dict(pair=f"{a}/{b}", started=started,
                              ramp_periods_applied=ramp.get("periods_applied"),
                              observed=bool(started and num(ramp.get("periods_applied")) and ramp.get("periods_applied") >= 1)))
        # CC-S
        if not (ra["has_s"] and rb["has_s"]) or not (num(ra["s_max_m"]) and num(rb["s_max_m"])):
            p["undecidable_by"].setdefault("CC-S", []).append("s_motor_max_m missing")
            p["CC-S"] = None
            p["violations"]["CC-S"] = []
        else:
            dlt = rb["s_max_m"] - ra["s_max_m"]
            p["CC-S"] = dict(ref_m=ra["s_max_m"], cand_m=rb["s_max_m"], delta_m=dlt)
            p["violations"]["CC-S"] = ["delta > 0.001 m"] if dlt > CS_LIMIT_M else []
        # CK-1C (B, C)
        lost = gained = False
        if a[0] in "BC":
            lost = ra["L1"] is not None and ra["L1"]["applied"] and not rb["any_r4_applied"]
            p["violations"]["CK-1C"] = ["R4_LOST"] if lost else []
        gained = rb["any_r4_applied"] and not ra["any_r4_applied"]
        p["CK"] = dict(cls="R4_LOST" if lost else ("R4_GAINED" if gained else ("KEPT" if (ra["any_r4_applied"] and rb["any_r4_applied"]) else "NONE")),
                       ref_L1=ra["L1"], cand_L1=rb["L1"])
        p["THIN_MARGIN"] = rb["L1"] is not None and rb["L1"]["dP"] is not None and rb["L1"]["dP"] <= THIN_MARGIN_PERIODS
        # hash, divergence
        h_eq = ra.get("cmd_hash") is not None and ra.get("cmd_hash") == rb.get("cmd_hash")
        cand_started = rb["las"]["start_s"] is not None
        p["hash_equal"] = h_eq
        p["cand_las_started"] = cand_started
        p["PAIR_DIVERGE"] = bool((not cand_started) and ra.get("cmd_hash") and rb.get("cmd_hash") and not h_eq)
        p["PAIR_CMD_DIFF"] = bool(cand_started and ra.get("cmd_hash") and rb.get("cmd_hash") and not h_eq)
        if a[0] in "BC" and not cand_started:
            p["note"] = "P5r4 not acting, not P5r4 evidence"
        # READY
        p["ready"] = dict(ref_s=ra["t_ready"], cand_s=rb["t_ready"],
                          dt_s=(rb["t_ready"] - ra["t_ready"]) if (num(ra["t_ready"]) and num(rb["t_ready"])) else None)
        # rev1 anchor
        an_a, an_b = ra["anchor"], rb["anchor"]
        uses = an_a["path"] in USES_ANCHOR or an_b["path"] in USES_ANCHOR
        if not uses:
            flag, why = False, "both arms path 3"
        else:
            cmp_ = [s for s in ("n_P_first", "n_P_last") if an_a.get(s) is not None and an_b.get(s) is not None]
            if not cmp_:
                flag, why = None, "ANCHOR_RECORD_MISSING:t_P"
            else:
                flag = any(an_a[s] != an_b[s] for s in cmp_)
                why = "compared " + ",".join(cmp_)

        def dd(s):
            return None if (an_a.get(s) is None or an_b.get(s) is None) else an_b[s] - an_a[s]
        p["anchor"] = dict(flag=flag, reason=why, ref=an_a, cand=an_b, d_n_P_first=dd("n_P_first"),
                           d_n_P_last=dd("n_P_last"), d_n_L_first=dd("n_L_first"), d_n_L_last=dd("n_L_last"))
        p["record"] = dict(las_ref=ra["las"], las_cand=rb["las"], window_short=[ra["window_short"], rb["window_short"]],
                           F_after_N=[fr, fc], F_tr_N=[ra["F_tr_N"], rb["F_tr_N"]], s_max_m=[ra["s_max_m"], rb["s_max_m"]],
                           mode_starts=[ra["mode_starts"], rb["mode_starts"]])
        pairs[f"{a}/{b}"] = p

    # ---- criteria statuses
    def crit_status(name, scope):
        und = [k for k in scope if pairs[k]["undecidable"] or pairs[k].get("undecidable_by", {}).get(name)]
        viol = {k: pairs[k]["violations"].get(name) for k in scope if pairs[k]["violations"].get(name)}
        return dict(status="undecidable" if und else ("fail" if viol else "pass"), violations=viol, undecidable=und)

    all_p = [f"{a}/{b}" for a, b in PAIRS]
    A_p = [k for k in all_p if k.startswith("A")]
    BC_p = [k for k in all_p if k[0] in "BC"]
    crit = {
        "CC-2": crit_status("CC-2", all_p), "CC-F": crit_status("CC-F", all_p), "G-2'C": crit_status("G-2'C", A_p),
        "CC-S": crit_status("CC-S", all_p), "CK-1C": crit_status("CK-1C", BC_p),
    }
    changed = [k for k in all_p if pairs[k].get("hash_equal") is False and not pairs[k]["undecidable"]]
    popv = {k: pairs[k]["ready"]["dt_s"] for k in changed if pairs[k]["ready"]["dt_s"] is not None}
    und_r = [k for k in all_p if pairs[k]["undecidable"]]
    if und_r:
        st = "undecidable"
    elif not changed:
        st = "pass"
    elif not popv:
        st = "undecidable"
    else:
        st = "pass" if (statistics.median(popv.values()) <= R_MEDIAN_S and max(popv.values()) <= R_MAX_S) else "fail"
    crit["CC-R"] = dict(status=st, changed=changed, population=popv,
                        median_s=statistics.median(popv.values()) if popv else None,
                        max_s=max(popv.values()) if popv else None, undecidable=und_r)
    obs_ok = any(o["observed"] for o in obs_A)
    observation = dict(A_pairs=obs_A, ok=obs_ok, reason=None if obs_ok else "NO_P5R4_OBSERVATION")
    divergence = sorted(k for k in all_p if pairs[k].get("PAIR_DIVERGE"))
    flags = dict(
        R4_GAINED=sorted(k for k in all_p if pairs[k].get("CK", {}).get("cls") == "R4_GAINED"),
        LATE_LOC_P32=sorted(k for k in all_p if pairs[k].get("LATE_LOC_P32")),
        THIN_MARGIN=sorted(k for k in all_p if pairs[k].get("THIN_MARGIN")),
        PAIR_CMD_DIFF=sorted(k for k in all_p if pairs[k].get("PAIR_CMD_DIFF")),
        ANCHOR_SAMPLE_SHIFT=sorted(k for k in all_p if pairs[k].get("anchor", {}).get("flag") is True),
        ANCHOR_RECORD_MISSING=sorted(k for k in all_p if "anchor" in pairs[k] and pairs[k]["anchor"]["flag"] is None),
        P3_4_window_short=sorted(k for k in all_p if any(x is True for x in pairs[k].get("record", {}).get("window_short", []))),
    )
    viol_anchor = set(crit["CC-S"]["violations"]) | {k for k in all_p if any(v.startswith("a:") for v in pairs[k]["violations"].get("CC-2", []))}
    flags["anchor_effect_possible"] = sorted(k for k in viol_anchor if pairs[k].get("anchor", {}).get("flag") is True)
    flags["anchor_effect_unknown"] = sorted(k for k in viol_anchor if pairs[k].get("anchor", {}).get("flag") is None)

    k_ok = {k: all(i["ok"] is not False for i in v) for k, v in K.items()}
    stop_r = [f"{k} false" for k, ok in k_ok.items() if not ok]
    for pid in ("C1", "C3"):
        if btc[pid] and btc[pid].get("ok") is False:
            stop_r.append(f"BT-C {pid} mismatch")
    if divergence:
        stop_r.append(f"PAIR_DIVERGE {divergence}")
    und_reasons = [f"{n} undecidable" for n, c in crit.items() if c["status"] == "undecidable"]
    if not obs_ok:
        und_reasons.append("NO_P5R4_OBSERVATION")
    for pid in ("C1", "C3"):
        if btc[pid] and btc[pid].get("ok") is None:
            und_reasons.append(f"BT-C {pid} not evaluated")
    fail_reasons = [f"{n} violated" for n, c in crit.items() if c["status"] == "fail"]
    status = "stop" if stop_r else ("undecidable" if und_reasons else ("fail" if fail_reasons else "pass"))
    return dict(
        tool=TOOL_NAME, tool_version=TOOL_VERSION, tool_sha256=sha256_file(os.path.abspath(__file__)),
        taken_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(), rules_sha256=RULES_SHA,
        rules_rev1_sha256=RULES_REV1_SHA, grade_provisional=status, k10=None,
        stop_reasons=stop_r, undecidable_reasons=und_reasons, fail_reasons=fail_reasons,
        error_rows=error_rows, n_error_rows=len(error_rows),
        k_checks={k: dict(ok=k_ok[k], items=v) for k, v in K.items()},
        bt_c=btc, rows=rows, pairs=pairs, criteria=crit, observation=observation, flags=flags,
        files_read_sha256=files_read, truncated=False)


EXIT = {"pass": 0, "fail": 1, "undecidable": 1, "stop": 2}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch", required=True)
    ap.add_argument("--rem-batch", default=None, help="07_results/S9/batch_V5-LAS-K1-REM_20261109_235554")
    ap.add_argument("--rules", required=True)
    ap.add_argument("--rules-rev1", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        res = recount(a.batch, a.rules, a.rules_rev1, a.rem_batch)
    except Exception:
        traceback.print_exc()
        print(json.dumps(dict(status="tool_error")))
        return 3
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, sort_keys=True, default=lambda o: None if o is MISSING else str(o))
    g = res["grade_provisional"]
    print("PROVISIONAL grade (K-10 decided outside):", g)
    print(json.dumps(dict(status=g, n_error_rows=res["n_error_rows"], out=a.out)))
    return EXIT.get(g, 1)


if __name__ == "__main__":
    sys.exit(main())
