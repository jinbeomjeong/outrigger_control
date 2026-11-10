"""Path-2 independent recount for V5-LAS-K1-REM (rules las_k1_rules_adopt2.md, section 9.2).

Independence contract (rules 9.2):
  * Reads only result.json / batch.json (+ controller_commands.npz for the
    pair-divergence record) and the rules file. Does not open or import the
    path-1 judge tool or any project module.
  * Source order differs from path 1:
      - LOC    : controller_meta.soil.t_loc_s and the order-gate decisions first,
                 LOC events (crawler_liftoff_confirmed) only for cross-checks.
      - t_S    : controller_meta.soil.mode_starts first, then events
                 soil_mode_start.
      - revoke : events INFO_LOC_REVOKED first, then controller_meta.loc_revoke.
  * Integer periods n = round(t / 0.1) (Python builtin, half-to-even).

User decisions taken before results (2026-11-09, rem_prelaunch_audit.md):
  * Fourth F path class FORCED_REVOKED_NO_REEVAL (revokes >= 1 and no R4
    evaluated decision after them). F classes are info only.
  * K-7: a gate-on row that ends in FAULT before the pair L1 -> K-7 None ->
    condition 3 false -> 'partial pass' (rules 4.2 example), not stop.
  * K-8 (a)/(c): a LOC before the first soil-mode start -> stop (wording).

Output grade is provisional; K-10 (path 1 vs path 2) is decided outside.
Exit codes: 0 pass (provisional), 1 fail / undecidable / partial pass,
2 stop, 3 tool error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import sys
import traceback

TOOL_NAME = "recount_rem.py"
TOOL_VERSION = "1"
RULES_SHA_EXPECTED = "fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8"
DLL_SHA_EXPECTED = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"
PERIOD_S = 0.1
THIN_MARGIN_PERIODS = 12
SCM_THREADS = 4
PLANNED_POOL = "pcore"  # user decision 1: P only (rules 2.1 literal)

TAG_VB = "final_C4G2_P3_LAS"
TAG_V0 = "final_C4G2_LAS"

# rules 2.2 / 2.3 row table
RULE_ROWS = {
    "R1": dict(case="REM_J2_B_top_Fs4_VB_gateoff", soil="J2", level="top", mass=1.0, v5="VB", gate="off", forced="off", role="judge"),
    "R2": dict(case="REM_J2_B_middle_Fs4_VB_gateoff", soil="J2", level="middle", mass=1.0, v5="VB", gate="off", forced="off", role="judge"),
    "R3": dict(case="REM_J2_B_bottom_Fs4_VB_gateoff", soil="J2", level="bottom", mass=1.0, v5="VB", gate="off", forced="off", role="judge"),
    "R4": dict(case="REM_J2_B_top_Fs4_m1p1_VB_gateoff", soil="J2", level="top", mass=1.1, v5="VB", gate="off", forced="off", role="judge"),
    "R5": dict(case="REM_J2_B_top_Fs4_m1p1_V0_gateoff", soil="J2", level="top", mass=1.1, v5="V0", gate="off", forced="off", role="judge"),
    "R6": dict(case="REM_J1_B_top_Fs4_m1p1_VB_gateoff", soil="J1", level="top", mass=1.1, v5="VB", gate="off", forced="off", role="judge"),
    "R7": dict(case="REM_J2_B_top_Fs4_VB_gateon", soil="J2", level="top", mass=1.0, v5="VB", gate="on", forced="off", role="judge"),
    "R8": dict(case="REM_J2_B_top_Fs4_m1p1_VB_gateon", soil="J2", level="top", mass=1.1, v5="VB", gate="on", forced="off", role="judge"),
    "F1": dict(case="REM_J2_B_top_Fs4_VB_gateon_forced1", soil="J2", level="top", mass=1.0, v5="VB", gate="on", forced="first", role="diag"),
    "F2": dict(case="REM_J2_B_top_Fs4_m1p1_VB_gateon_forced1", soil="J2", level="top", mass=1.1, v5="VB", gate="on", forced="first", role="diag"),
}
GATEOFF_KEYS = ["R1", "R2", "R3", "R4", "R5", "R6"]
GATEON_KEYS = ["R7", "R8"]
JUDGE_KEYS = GATEOFF_KEYS + GATEON_KEYS
DIAG_KEYS = ["F1", "F2"]
GATE_PAIRS = [("R1", "R7"), ("R4", "R8")]          # (gateoff, gateon)
FORCED_ARGV_PAIRS = [("R7", "F1"), ("R8", "F2")]   # argv differs by --k1-forced-block only
F_L1_PAIR = {"F1": "R1", "F2": "R4"}               # rules 2.3 FORCED_PAIR_L1
POOL_SETS = [("R1", "R7", "F1"), ("R4", "R8", "F2")]
FIXED_ARGS = dict(pad_variant="dwg_rear250", fs_kN=4.0, seed=20261026, pressure_grade="normal",
                  imu_grade="ideal", duration=120.0, floor_roll=0.0, floor_pitch=0.0, soil_patch=None)
PER_ROW_ARGV_OPTS = {"--soil", "--level", "--mass-scale", "--k1-order-gate", "--k1-forced-block",
                     "--expect-controller", "--case", "--out-root"}
# v5 hydraulic options seen in the stored S-Ch VB argv (schema reference only)
V5_ARGV_OPTS = {"--flow-eta-v", "--flow-dp-comp-bar", "--flow-dp-unload-bar", "--flow-width-bar",
                "--flow-law", "--valve-tau-s", "--rod-release-force", "--lock-overlap-ratio",
                "--lock-closing-delay-s", "--lock-window-follows-plant", "--extend-start-tracked"}
# rules 1.1 old-controller values (n_R = old first R4 LOC period, n_S)
OLD_CTRL = {"R1": (451, 332), "R2": (451, 332), "R3": (451, 332), "R7": (451, 332),
            "R4": (553, 333), "R5": (553, 333), "R8": (553, 333), "R6": (492, 333),
            "F1": (451, 332), "F2": (553, 333)}
# rules 1.3 harness first-LOC dP (x1.0 flat), comparison record only
HARNESS_DP = {"R1": (92, 93, "J2 T x1.0"), "R2": (94, 94, "J2 M x1.0"), "R3": (94, 95, "J2 B x1.0"),
              "R6": (36, 38, "J1 T x1.0 (R6 is x1.1)")}

EV_LOC = "crawler_liftoff_confirmed"
EV_SOIL_START = "soil_mode_start"
EV_REVOKED = "INFO_LOC_REVOKED"
EV_E3C10 = "INFO_LOC_CLEARANCE_MARGIN"
EV_FLAT = "INFO_LOC_FLAT_SOIL_MARGIN"
EV_FLAT_SKIP = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"


# ----------------------------------------------------------------------------- helpers

def per(t):
    """Integer control period n = round(t / 0.1) (builtin round, half-to-even)."""
    if t is None:
        return None
    return round(t / PERIOD_S)


def base_name(name):
    return str(name).split(":", 1)[0]


def suffix(name):
    parts = str(name).split(":", 1)
    return parts[1] if len(parts) > 1 else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dig(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def is_error_obj(x):
    return isinstance(x, dict) and "error" in x


def same_float(a, b):
    """Exact equality incl. None; floats must be the identical value."""
    if a is None or b is None:
        return a is None and b is None
    return type(a) in (int, float) and type(b) in (int, float) and float(a) == float(b) and \
        not (isinstance(a, float) and math.isnan(a))


class Check:
    """One K check: ok True / False / None (not evaluable) + details."""

    def __init__(self, key, scope):
        self.key = key
        self.scope = scope
        self.items = []

    def add(self, row, name, ok, got=None, want=None):
        self.items.append(dict(row=row, item=name, ok=ok, got=got, want=want))

    @staticmethod
    def _keys(row):
        return [] if row is None else str(row).split("/")

    def _judge_items(self):
        """Items that decide stop: global (row None) or rows made of judge keys only."""
        out = []
        for i in self.items:
            ks = self._keys(i["row"])
            if not ks or not any(x in DIAG_KEYS for x in ks):
                out.append(i)
        return out

    def diag_items(self, f):
        return [i for i in self.items if f in self._keys(i["row"])]

    @staticmethod
    def _fold(items):
        vals = [i["ok"] for i in items]
        if any(v is False for v in vals):
            return False
        if not any(v is True for v in vals):
            return None
        return True

    @property
    def ok(self):
        return self._fold(self._judge_items())

    def failures(self):
        return [i for i in self.items if i["ok"] is False]

    def as_dict(self):
        return dict(ok=self.ok, scope=self.scope, n_items=len(self.items),
                    failures_judge_scope=[i for i in self._judge_items() if i["ok"] is False],
                    failures_all=self.failures(), items=self.items)


# ----------------------------------------------------------------------------- loading

def load_batch(batch_dir):
    bpath = os.path.join(batch_dir, "batch.json")
    with open(bpath, encoding="utf-8") as f:
        batch = json.load(f)
    return bpath, batch


def map_entries(batch, k5):
    """rem_key -> last batch entry (rerun replaces the original, rules 7)."""
    out = {}
    counts = {}
    for e in batch.get("cases", []) or []:
        case = e.get("case")
        key_by_case = next((k for k, v in RULE_ROWS.items() if v["case"] == case), None)
        key = e.get("rem_key") or key_by_case
        if key is None:
            k5.add(case, "case_not_in_rules_table", False, got=case)
            continue
        if key_by_case is not None and e.get("rem_key") is not None and key_by_case != e.get("rem_key"):
            k5.add(key, "rem_key_vs_case_name", False, got=[e.get("rem_key"), case], want=key_by_case)
        counts[key] = counts.get(key, 0) + 1
        out[key] = e
    return out, counts


def load_result(batch_dir, entry):
    case = entry.get("case")
    path = os.path.join(batch_dir, case, "result.json")
    if not os.path.isfile(path):
        return path, None, "result.json missing"
    try:
        with open(path, encoding="utf-8") as f:
            return path, json.load(f), None
    except Exception as exc:  # partial record
        return path, None, f"result.json unreadable: {exc!r}"


# ----------------------------------------------------------------------------- per-row recount

def missing_reasons(entry, res, load_err):
    """rules 7 / K-9: reasons that make a row MISSING (empty list = present)."""
    reasons = []
    if entry is None:
        return ["no batch entry"]
    if entry.get("rc") != 0:
        reasons.append(f"rc={entry.get('rc')!r}")
    if load_err:
        reasons.append(load_err)
        return reasons
    cm = res.get("controller_meta")
    if not isinstance(cm, dict) or is_error_obj(cm):
        reasons.append("controller_meta error/absent")
    else:
        soil = cm.get("soil")
        if not isinstance(soil, dict) or is_error_obj(soil):
            reasons.append("controller_meta.soil error/absent")
        elif soil.get("restored_from") is not None:
            reasons.append(f"soil.restored_from={soil.get('restored_from')!r}")
    ev = res.get("events")
    if not isinstance(ev, list):
        reasons.append("events error/absent")
    if isinstance(res.get("c2_soil"), dict) and res["c2_soil"].get("restored_from") is not None:
        reasons.append(f"c2_soil.restored_from={res['c2_soil'].get('restored_from')!r}")
    return reasons


def recount_row(key, res):
    """Decision table, L1, status and record fields for one present row."""
    cm = res["controller_meta"]
    soil = cm["soil"]
    scm = cm.get("slope_clearance_margin") or {}
    og = scm.get("order_gate")
    events = [e for e in res.get("events", []) if isinstance(e, dict)]
    ev = [(per(e.get("t_s")), e.get("t_s"), str(e.get("name"))) for e in events]

    def ev_periods(base, suf=None):
        return [n for (n, _t, nm) in ev if base_name(nm) == base and (suf is None or suffix(nm) == suf)]

    # --- soil-mode starts: meta first, events second
    ms_meta = soil.get("mode_starts")
    ms_events = [(n, t) for (n, t, nm) in ev if base_name(nm) == EV_SOIL_START]
    if isinstance(ms_meta, list):
        starts = [dict(t_s=m.get("t_s"), n=per(m.get("t_s")), source=m.get("source")) for m in ms_meta]
        starts_source = "controller_meta.soil.mode_starts"
    else:
        starts = [dict(t_s=t, n=n, source=None) for (n, t) in ms_events]
        starts_source = "events soil_mode_start (mode_starts absent)"
    starts.sort(key=lambda s: (s["n"] if s["n"] is not None else -1))
    starts_cross = sorted(s["n"] for s in starts) == sorted(n for (n, _t) in ms_events)

    # --- revokes: events first, meta second
    rv_events = sorted((n, t) for (n, t, nm) in ev if base_name(nm) == EV_REVOKED)
    lr = cm.get("loc_revoke") or {}
    rv_meta = [(per(t), t) for t in (lr.get("t_revoke_s") or [])]
    revokes = [n for (n, _t) in rv_events] if rv_events or not rv_meta else [n for (n, _t) in rv_meta]
    revokes_source = "events INFO_LOC_REVOKED" if (rv_events or not rv_meta) else "controller_meta.loc_revoke (no events)"
    revokes = sorted(revokes)

    # --- LOCs: meta (decisions + soil.t_loc_s) first, events for cross-check
    decisions_raw = None if not isinstance(og, dict) else og.get("decisions")
    has_decisions_key = isinstance(decisions_raw, list)
    decisions_raw = sorted(decisions_raw or [], key=lambda d: (d.get("t_loc_s") is None, d.get("t_loc_s") or 0.0))
    loc_meta_periods = sorted({per(d.get("t_loc_s")) for d in decisions_raw if d.get("t_loc_s") is not None}
                              | ({per(soil.get("t_loc_s"))} if soil.get("t_loc_s") is not None else set()))
    loc_ev_periods = sorted(ev_periods(EV_LOC))
    e3c10_periods = sorted(set(ev_periods(EV_E3C10)))
    e3c10_locs = [n for n in loc_ev_periods if n in e3c10_periods]

    applied_ev = {}
    skipped_ev = {}
    for (n, _t, nm) in ev:
        if base_name(nm) == EV_FLAT:
            applied_ev[n] = applied_ev.get(n, 0) + 1
        elif base_name(nm) == EV_FLAT_SKIP and suffix(nm) == "order":
            skipped_ev[n] = skipped_ev.get(n, 0) + 1
    skipped_any = sum(1 for (_n, _t, nm) in ev if base_name(nm) == EV_FLAT_SKIP)

    table = []
    for i, d in enumerate(decisions_raw):
        t_loc = d.get("t_loc_s")
        n_loc = per(t_loc)
        t_P = d.get("t_P_s")
        t_S = d.get("t_S_s")
        n_P = per(t_P)
        n_S = per(t_S)
        dP = (n_P - n_S) if (n_P is not None and n_S is not None) else None
        prior = [r for r in revokes if n_loc is not None and r < n_loc]
        post_revoke = bool(prior)
        last_rv = max(prior) if prior else None
        restart_n = None
        if last_rv is not None:
            cand = [s["n"] for s in starts if s["n"] is not None and s["n"] >= last_rv]
            restart_n = min(cand) if cand else None
        struct_zero = bool(post_revoke and n_S is not None and restart_n is not None
                           and n_S == restart_n and n_P == n_S)
        rec_match = (d.get("n_P") == n_P and d.get("n_S") == n_S and d.get("dP") == dP)
        table.append(dict(
            i=i, t_loc_s=t_loc, n_loc=n_loc, t_P_s=t_P, t_S_s=t_S, n_P=n_P, n_S=n_S, dP=dP,
            rec_n_P=d.get("n_P"), rec_n_S=d.get("n_S"), rec_dP=d.get("dP"), rec_match=rec_match,
            r4=bool(d.get("r4_due_without_gate")), would_block=bool(d.get("would_block")),
            applied=bool(d.get("applied")), post_revoke=post_revoke, last_revoke_n=last_rv,
            restart_n=restart_n, struct_zero=struct_zero,
            ev_applied=applied_ev.get(n_loc, 0), ev_skipped_order=skipped_ev.get(n_loc, 0)))

    r4 = [x for x in table if x["r4"]]
    L1 = r4[0] if r4 else None
    if L1 is None:
        status = "NO_R4"
    elif L1["post_revoke"] and L1["struct_zero"]:
        status = "LATE_STRUCT"
    elif L1["dP"] is not None and L1["t_P_s"] is not None and L1["t_S_s"] is not None and L1["dP"] > 0:
        status = "POS"
    else:
        status = "NONPOS"
    l1_tuple = None if L1 is None else dict(n_loc=L1["n_loc"], n_P=L1["n_P"], n_S=L1["n_S"], dP=L1["dP"],
                                            t_P_s=L1["t_P_s"], t_S_s=L1["t_S_s"])
    first_loc_meta = loc_meta_periods[0] if loc_meta_periods else None
    first_loc = first_loc_meta if first_loc_meta is not None else (loc_ev_periods[0] if loc_ev_periods else None)

    faults = [(n, nm) for (n, _t, nm) in ev if base_name(nm).startswith("FAULT_")]
    warns = sorted({nm for (_n, _t, nm) in ev if base_name(nm).startswith("WARN_")})
    phases = res.get("phases") or []
    first_done = next((p.get("t_s") for p in phases if p.get("phase") == "done"), None)
    first_ready = next((p.get("t_s") for p in phases if p.get("phase") == "ready"), None)
    final_phase = phases[-1].get("phase") if phases else None
    smax = dig(res, "p3b", "P3-5_clearance_stroke", "s_motor_max_m")
    gap = dig(res, "p3b_ext", "crawler_gap") or {}

    return dict(
        status=status, L1=l1_tuple, L1_index=None if L1 is None else L1["i"],
        L1_post_revoke=None if L1 is None else L1["post_revoke"],
        L1_loc_minus_P=None if (L1 is None or L1["n_P"] is None) else L1["n_loc"] - L1["n_P"],
        decisions=table, has_decisions_key=has_decisions_key, n_decisions=len(table), n_r4=len(r4),
        order_gate_enabled=None if not isinstance(og, dict) else og.get("enabled"),
        mode_starts=starts, mode_starts_source=starts_source, mode_starts_events_match=starts_cross,
        revokes_n=revokes, revokes_source=revokes_source,
        revokes_events_n=[n for (n, _t) in rv_events], revokes_meta_n=sorted(n for (n, _t) in rv_meta),
        revokes_meta_count=lr.get("revokes"),
        loc_meta_periods=loc_meta_periods, loc_event_periods=loc_ev_periods,
        soil_t_loc_n=per(soil.get("t_loc_s")),
        soil_t_loc_is_last_event_loc=(per(soil.get("t_loc_s")) == loc_ev_periods[-1]) if (loc_ev_periods and soil.get("t_loc_s") is not None) else None,
        first_loc_n=first_loc, e3c10_loc_periods=e3c10_locs, n_e3c10_loc=len(e3c10_locs),
        applied_event_periods=applied_ev, skipped_order_event_periods=skipped_ev, skipped_any_count=skipped_any,
        faults=faults, warn_names=warns, first_done_t_s=first_done, first_ready_t_s=first_ready,
        final_phase=final_phase, s_motor_max_m=(max(smax) if isinstance(smax, list) and smax else None),
        crawler_gap_end_grid_m=gap.get("grid_end_m"), crawler_gap_end_all_m=gap.get("end_m"),
    )


# ----------------------------------------------------------------------------- argv helpers

def strip_argv(argv, opts):
    out = []
    skip = False
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


def argv_value(argv, opt):
    for i, tok in enumerate(argv):
        if tok == opt and i + 1 < len(argv):
            return argv[i + 1]
        if tok.startswith(opt + "="):
            return tok.split("=", 1)[1]
    return None


def argv_options(argv):
    return {t for t in argv if t.startswith("--")}


# ----------------------------------------------------------------------------- main recount

def recount(batch_dir, rules_path):
    files_read = {}
    rules_sha = sha256_file(rules_path)
    files_read[os.path.abspath(rules_path)] = rules_sha
    k = {kk: Check(kk, sc) for kk, sc in [
        ("K-0", "partial: rules sha vs .sha256 file and expected constant (tool/audit sha chain is path-1/judgement doc)"),
        ("K-1", "partial: git_at_start.head equal over rows, dirty empty, batch code_at_launch head equal (prelaunch/postrun HEAD not available to path 2)"),
        ("K-2", "partial: recorded c2/zero_calibration sha equal batch vs result and over rows; F module sha consistency (file-vs-blob is path 1)"),
        ("K-3", "full from records"), ("K-4", "full from records"), ("K-5", "full from records"),
        ("K-6", "full from records"), ("K-7", "full"), ("K-8", "full"),
        ("K-9", "MISSING assignment by rules 7 (always consistent in path 2 by construction)"),
    ]}

    # K-0
    sha_file = os.path.splitext(rules_path)[0] + ".sha256"
    rec = None
    if os.path.isfile(sha_file):
        with open(sha_file, encoding="utf-8") as f:
            txt = f.read().strip()
        rec = txt.split()[0] if txt else None
        files_read[os.path.abspath(sha_file)] = sha256_file(sha_file)
    k["K-0"].add(None, "rules_sha_eq_sha256_file", rec == rules_sha, got=rules_sha, want=rec)
    k["K-0"].add(None, "rules_sha_eq_expected", rules_sha == RULES_SHA_EXPECTED, got=rules_sha, want=RULES_SHA_EXPECTED)

    bpath, batch = load_batch(batch_dir)
    files_read[os.path.abspath(bpath)] = sha256_file(bpath)
    entries, counts = map_entries(batch, k["K-5"])

    rows = {}
    res_by = {}
    for key in JUDGE_KEYS + DIAG_KEYS:
        spec = RULE_ROWS[key]
        entry = entries.get(key)
        row = dict(rem_key=key, case=spec["case"], role=spec["role"], gate=spec["gate"], forced=spec["forced"],
                   entries_in_batch=counts.get(key, 0),
                   rerun_of=None if entry is None else entry.get("rerun_of"))
        if entry is None:
            row.update(status="MISSING", missing_reasons=["no batch entry"])
            rows[key] = row
            continue
        rpath, res, err = load_result(batch_dir, entry)
        if res is not None:
            files_read[os.path.abspath(rpath)] = sha256_file(rpath)
        reasons = missing_reasons(entry, res, err)
        if reasons:
            row.update(status="MISSING", missing_reasons=reasons)
            rows[key] = row
            k["K-9"].add(key, "missing_assigned", True, got=reasons)
            continue
        k["K-9"].add(key, "present", True)
        try:
            row.update(recount_row(key, res))
        except Exception as exc:
            # a broken record inside a present row: treat as K-6/K-8 failure, not silently missing
            row.update(status="RECOUNT_ERROR", error=repr(exc))
            k["K-8"].add(key, "recount_error", False, got=repr(exc))
        row["missing_reasons"] = []
        rows[key] = row
        res_by[key] = (entry, res)

    present = [kk for kk in res_by]

    # ---------------- K-1 / K-2 (partial)
    heads = {}
    for kk in present:
        entry, res = res_by[kk]
        g = dig(res, "code_state", "git_at_start") or {}
        heads[kk] = g.get("head")
        k["K-1"].add(kk, "dirty_empty", g.get("dirty") == [], got=g.get("dirty"), want=[])
        bh = dig(entry, "code_at_launch", "git", "head")
        k["K-1"].add(kk, "batch_head_eq_result_head", bh == g.get("head"), got=g.get("head"), want=bh)
        bd = dig(entry, "code_at_launch", "git", "dirty")
        k["K-1"].add(kk, "batch_dirty_empty", bd == [], got=bd, want=[])
    uh = sorted({heads[x] for x in heads if x in JUDGE_KEYS}, key=str)
    k["K-1"].add(None, "single_head_judge_rows", len(uh) == 1 and uh[0] is not None, got=uh)
    for f in DIAG_KEYS:
        if f in heads:
            k["K-1"].add(f, "head_eq_judge_rows", len(uh) == 1 and heads[f] == uh[0], got=heads[f], want=uh)

    c2sha = {}
    for kk in present:
        entry, res = res_by[kk]
        fa = dig(res, "code_state", "files_at_start") or {}
        rs = {v.get("path"): v.get("sha256") for v in fa.values() if isinstance(v, dict) and "path" in v}
        bs = dig(entry, "code_at_launch", "files") or {}
        for p in ("03_src/outrigger_sim/control/c2.py", "03_src/outrigger_sim/control/zero_calibration.py"):
            k["K-2"].add(kk, f"sha_batch_eq_result:{p}", bs.get(p) is not None and bs.get(p) == rs.get(p),
                         got=rs.get(p), want=bs.get(p))
        c2sha[kk] = rs.get("03_src/outrigger_sim/control/c2.py")
    uc = sorted({c2sha[x] for x in c2sha if x in JUDGE_KEYS}, key=str)
    k["K-2"].add(None, "single_c2_sha_judge_rows", len(uc) == 1 and uc[0] is not None, got=uc)
    fsha = {}
    for f in DIAG_KEYS:
        if f in c2sha:
            k["K-2"].add(f, "c2_sha_eq_judge_rows", len(uc) == 1 and c2sha[f] == uc[0], got=c2sha[f], want=uc)
            fb_meta = dig(res_by[f][1], "controller_meta", "k1_forced_block", "module_sha256")
            fb_setup = dig(res_by[f][1], "c2_setup", "k1_forced_block", "module_sha256")
            k["K-2"].add(f, "forced_module_sha_meta_eq_setup", fb_meta is not None and fb_meta == fb_setup,
                         got=fb_meta, want=fb_setup)
            fsha[f] = fb_meta
    if len(fsha) == 2:
        k["K-2"].add("F1/F2", "forced_module_sha_equal", fsha["F1"] == fsha["F2"], got=fsha)

    # ---------------- K-3
    k["K-3"].add(None, "batch_mixed_hull_mode_false", batch.get("mixed_hull_mode") is False, got=batch.get("mixed_hull_mode"))
    for kk in present:
        entry, res = res_by[kk]
        hh = res.get("hull_hook") or {}
        k["K-3"].add(kk, "mode_fast", hh.get("mode") == "fast", got=hh.get("mode"))
        k["K-3"].add(kk, "requested_fast", hh.get("requested") == "fast", got=hh.get("requested"))
        k["K-3"].add(kk, "fallback_none", hh.get("fallback_reason") is None, got=hh.get("fallback_reason"))
        k["K-3"].add(kk, "dll_sha", hh.get("dll_sha256") == DLL_SHA_EXPECTED, got=hh.get("dll_sha256"))
        he = entry.get("hull_hook_effective")
        if he is not None:
            k["K-3"].add(kk, "batch_hull_effective_fast", he.get("mode") == "fast" and he.get("fallback_reason") is None, got=he)

    # ---------------- K-4
    pool_kind = {}
    for kk in present:
        entry, res = res_by[kk]
        args = res.get("args") or {}
        pl = res.get("placement") or {}
        nt_meta = dig(res, "meta", "num_threads_chrono")
        k["K-4"].add(kk, "threads_4", args.get("threads") == SCM_THREADS and nt_meta == SCM_THREADS
                     and res.get("num_threads_chrono", SCM_THREADS) == SCM_THREADS,
                     got=[args.get("threads"), nt_meta, res.get("num_threads_chrono")], want=SCM_THREADS)
        k["K-4"].add(kk, "omp_passive", entry.get("omp_wait_policy") == "PASSIVE" and pl.get("omp_wait_policy") == "PASSIVE",
                     got=[entry.get("omp_wait_policy"), pl.get("omp_wait_policy")])
        k["K-4"].add(kk, "placement_eq_plan", pl.get("mode") == entry.get("planned_pool") == entry.get("pool") == PLANNED_POOL,
                     got=[pl.get("mode"), entry.get("planned_pool"), entry.get("pool")], want=PLANNED_POOL)
        k["K-4"].add(kk, "affinity_ok", pl.get("affinity_ok") is True, got=pl.get("affinity_ok"))
        k["K-4"].add(kk, "power_throttling_off_ok", pl.get("power_throttling_off_ok") is True, got=pl.get("power_throttling_off_ok"))
        pool_kind[kk] = pl.get("mode")
    for ps in POOL_SETS:
        judge_part = [x for x in ps if x in JUDGE_KEYS and x in pool_kind]
        k["K-4"].add("/".join(judge_part), "pair_same_pool", len({pool_kind[x] for x in judge_part}) <= 1,
                     got=[pool_kind[x] for x in judge_part])
        for f in ps:
            if f in DIAG_KEYS and f in pool_kind:
                ref = [pool_kind[x] for x in judge_part]
                k["K-4"].add(f, "diag_same_pool_as_pair", all(v == pool_kind[f] for v in ref), got=pool_kind[f], want=ref)

    # ---------------- K-5 (args from result + argv from batch)
    argvs = {kk: list(entries[kk].get("argv") or []) for kk in entries}
    for kk in JUDGE_KEYS + DIAG_KEYS:
        spec = RULE_ROWS[kk]
        if kk in argvs:
            av = argvs[kk]
            k["K-5"].add(kk, "argv_soil", argv_value(av, "--soil") == spec["soil"], got=argv_value(av, "--soil"), want=spec["soil"])
            k["K-5"].add(kk, "argv_level", argv_value(av, "--level") == spec["level"], got=argv_value(av, "--level"), want=spec["level"])
            ms = argv_value(av, "--mass-scale")
            k["K-5"].add(kk, "argv_mass_scale", (float(ms) if ms is not None else 1.0) == spec["mass"], got=ms, want=spec["mass"])
            k["K-5"].add(kk, "argv_gate", argv_value(av, "--k1-order-gate") == spec["gate"], got=argv_value(av, "--k1-order-gate"), want=spec["gate"])
            fb = argv_value(av, "--k1-forced-block")
            k["K-5"].add(kk, "argv_forced", (fb or "off") == spec["forced"], got=fb, want=spec["forced"])
            tag = TAG_V0 if spec["v5"] == "V0" else TAG_VB
            k["K-5"].add(kk, "argv_expect_controller", argv_value(av, "--expect-controller") == tag,
                         got=argv_value(av, "--expect-controller"), want=tag)
            has_v5 = sorted(argv_options(av) & V5_ARGV_OPTS)
            if spec["v5"] == "V0":
                k["K-5"].add(kk, "v0_no_v5_options", has_v5 == [], got=has_v5, want=[])
        if kk in res_by:
            args = res_by[kk][1].get("args") or {}
            k["K-5"].add(kk, "args_soil", args.get("soil") == spec["soil"], got=args.get("soil"), want=spec["soil"])
            k["K-5"].add(kk, "args_level", args.get("level") == spec["level"], got=args.get("level"), want=spec["level"])
            k["K-5"].add(kk, "args_mass_scale", args.get("mass_scale") == spec["mass"], got=args.get("mass_scale"), want=spec["mass"])
            k["K-5"].add(kk, "args_gate", args.get("k1_order_gate") == spec["gate"], got=args.get("k1_order_gate"), want=spec["gate"])
            if "k1_forced_block" in args or spec["forced"] != "off":
                k["K-5"].add(kk, "args_forced", args.get("k1_forced_block") == spec["forced"], got=args.get("k1_forced_block"), want=spec["forced"])
            tag = TAG_V0 if spec["v5"] == "V0" else TAG_VB
            k["K-5"].add(kk, "args_expect_controller", args.get("expect_controller") == tag, got=args.get("expect_controller"), want=tag)
            k["K-5"].add(kk, "args_case", args.get("case") == spec["case"], got=args.get("case"), want=spec["case"])
            for fk, fv in FIXED_ARGS.items():
                k["K-5"].add(kk, f"args_{fk}", args.get(fk) == fv, got=args.get(fk), want=fv)
    # common argv (all VB rows equal after stripping per-row options)
    vb = [x for x in JUDGE_KEYS + DIAG_KEYS if x in argvs and RULE_ROWS[x]["v5"] == "VB"]
    if vb:
        ref = strip_argv(argvs[vb[0]], PER_ROW_ARGV_OPTS)
        for x in vb[1:]:
            k["K-5"].add(x, f"argv_common_eq_{vb[0]}", strip_argv(argvs[x], PER_ROW_ARGV_OPTS) == ref)
    if "R5" in argvs and "R4" in argvs:
        a4 = strip_argv(argvs["R4"], PER_ROW_ARGV_OPTS)
        a5 = strip_argv(argvs["R5"], PER_ROW_ARGV_OPTS)
        extra5 = sorted(argv_options(a5) - argv_options(a4))
        only4 = sorted(argv_options(a4) - argv_options(a5))
        k["K-5"].add("R5", "v0_argv_is_vb_minus_v5", extra5 == [] and set(only4) <= V5_ARGV_OPTS,
                     got=dict(extra_in_R5=extra5, only_in_R4=only4))
        # remove v5 options with their values / flags for a token-level comparison
        k["K-5"].add("R5", "v0_argv_rest_eq_R4", _strip_v5(argvs["R4"]) == _strip_v5(argvs["R5"]))
    for off, on in GATE_PAIRS:
        if off in argvs and on in argvs:
            k["K-5"].add(f"{off}/{on}", "pair_argv_diff_gate_only",
                         strip_argv(argvs[off], {"--k1-order-gate", "--case", "--out-root"}) ==
                         strip_argv(argvs[on], {"--k1-order-gate", "--case", "--out-root"}))
    for on, f in FORCED_ARGV_PAIRS:
        if on in argvs and f in argvs:
            k["K-5"].add(f"{on}/{f}", "pair_argv_diff_forced_only",
                         strip_argv(argvs[on], {"--k1-forced-block", "--case", "--out-root"}) ==
                         strip_argv(argvs[f], {"--k1-forced-block", "--case", "--out-root"}))

    # ---------------- K-6
    for kk in present:
        entry, res = res_by[kk]
        spec = RULE_ROWS[kk]
        row = rows[kk]
        c2s = res.get("c2_setup") or {}
        ec = c2s.get("expect_controller") or {}
        tag = TAG_V0 if spec["v5"] == "V0" else TAG_VB
        sink = k["K-6"]
        sink.add(kk, "expect_controller_ok", ec.get("ok") is True and ec.get("name") == tag, got=[ec.get("ok"), ec.get("name")], want=tag)
        sink.add(kk, "c2_setup_gate", c2s.get("k1_order_gate") == spec["gate"], got=c2s.get("k1_order_gate"), want=spec["gate"])
        og = dig(res, "controller_meta", "slope_clearance_margin", "order_gate")
        sink.add(kk, "order_gate_decisions_key", isinstance(og, dict) and isinstance(og.get("decisions"), list))
        sink.add(kk, "order_gate_enabled", isinstance(og, dict) and og.get("enabled") is (spec["gate"] == "on"),
                 got=None if not isinstance(og, dict) else og.get("enabled"), want=spec["gate"] == "on")
        lrs = dig(res, "controller_meta", "loc_revoke", "settings") or {}
        sink.add(kk, "keep_slope_margin_on_revoke", lrs.get("keep_slope_margin_on_revoke") is True, got=lrs.get("keep_slope_margin_on_revoke"))
        sink.add(kk, "max_revokes_2", lrs.get("max_revokes") == 2, got=lrs.get("max_revokes"))
        ps = lrs.get("period_s", dig(res, "controller_meta", "period_s"))
        sink.add(kk, "period_0p1", ps == PERIOD_S, got=ps)
        fbs = c2s.get("k1_forced_block")
        fb_req = fbs.get("requested") if isinstance(fbs, dict) else fbs
        fb_cls = fbs.get("class") if isinstance(fbs, dict) else None
        if spec["role"] == "judge":
            sink.add(kk, "no_meta_k1_forced_block", "k1_forced_block" not in (res.get("controller_meta") or {}))
            sink.add(kk, "c2_setup_forced_off", fb_req == "off", got=fb_req, want="off")
            sink.add(kk, "controller_class_C2Controller", fb_cls is not None and str(fb_cls).split(".")[-1] == "C2Controller",
                     got=fb_cls)
            if spec["gate"] == "off" and row.get("status") not in ("MISSING", "RECOUNT_ERROR"):
                sink.add(kk, "gateoff_r4_le_1", row["n_r4"] <= 1, got=row["n_r4"], want="<=1")
                sink.add(kk, "gateoff_skipped_order_0", sum(row["skipped_order_event_periods"].values()) == 0,
                         got=row["skipped_order_event_periods"])

    # ---------------- K-8 (all present rows; judge rows decide stop, F rows info)
    k8_info = Check("K-8", "F rows (info)")
    for kk in present:
        row = rows[kk]
        if row.get("status") == "RECOUNT_ERROR":
            continue
        sink = k["K-8"] if RULE_ROWS[kk]["role"] == "judge" else k8_info
        starts = row["mode_starts"]
        first_start = starts[0]["n"] if starts else None
        loc_after = [n for n in row["loc_event_periods"] if first_start is not None and n > first_start]
        non_e3 = [n for n in loc_after if n not in row["e3c10_loc_periods"]]
        sink.add(kk, "a_decisions_eq_nonE3c10_locs_after_soil_start", row["n_decisions"] == len(non_e3),
                 got=row["n_decisions"], want=len(non_e3))
        pre_soil = [n for n in row["loc_event_periods"] if first_start is None or n <= first_start]
        if any(d["n_loc"] in pre_soil for d in row["decisions"]):
            sink.add(kk, "a_decision_before_soil_mode_start", False, got=pre_soil)
        for d in row["decisions"]:
            sink.add(kk, f"b_decision{d['i']}_at_loc_event", d["n_loc"] in row["loc_event_periods"], got=d["n_loc"])
            prior = [s for s in starts if s["n"] is not None and s["n"] < d["n_loc"]]
            want = prior[-1]["t_s"] if prior else "<no start before LOC>"
            sink.add(kk, f"c_decision{d['i']}_t_S_eq_last_prior_start",
                     bool(prior) and same_float(d["t_S_s"], prior[-1]["t_s"]), got=d["t_S_s"], want=want)
        sink.add(kk, "d_revoke_meta_eq_events",
                 row["revokes_events_n"] == row["revokes_meta_n"] and
                 (row["revokes_meta_count"] is None or row["revokes_meta_count"] == len(row["revokes_events_n"])),
                 got=dict(events=row["revokes_events_n"], meta=row["revokes_meta_n"], meta_count=row["revokes_meta_count"]))
        exp_app = {}
        exp_skip = {}
        for d in row["decisions"]:
            if d["applied"]:
                exp_app[d["n_loc"]] = exp_app.get(d["n_loc"], 0) + 1
            if d["would_block"] and not d["applied"]:
                exp_skip[d["n_loc"]] = exp_skip.get(d["n_loc"], 0) + 1
        sink.add(kk, "e_applied_events", exp_app == row["applied_event_periods"],
                 got=row["applied_event_periods"], want=exp_app)
        sink.add(kk, "e_skipped_order_events", exp_skip == row["skipped_order_event_periods"],
                 got=row["skipped_order_event_periods"], want=exp_skip)
        sink.add(kk, "e_skipped_other_suffix_0", row["skipped_any_count"] == sum(row["skipped_order_event_periods"].values()),
                 got=row["skipped_any_count"])
        if RULE_ROWS[kk]["gate"] == "on" and RULE_ROWS[kk]["role"] == "judge" and row["L1"] is not None:
            l1 = row["decisions"][row["L1_index"]]
            if l1["applied"]:
                later_r4 = [d for d in row["decisions"] if d["r4"] and d["i"] > l1["i"]]
                sink.add(kk, "f_after_applied_L1_no_r4", later_r4 == [], got=[d["n_loc"] for d in later_r4])
                sink.add(kk, "f_after_applied_L1_no_skipped_order", sum(row["skipped_order_event_periods"].values()) == 0,
                         got=row["skipped_order_event_periods"])

    # ---------------- statuses, SHADOW, pairs
    for kk in rows:
        r = rows[kk]
        if r.get("status") in ("MISSING", "RECOUNT_ERROR"):
            continue
        r["shadow_reloc"] = [dict(n_loc=d["n_loc"], dP=d["dP"], struct_zero=d["struct_zero"])
                             for d in r["decisions"] if d["post_revoke"] and not d["r4"]]
        L1i = r["L1_index"]
        r["revokes_after_L1"] = [] if L1i is None else [n for n in r["revokes_n"] if n > r["L1"]["n_loc"]]
        r4s = [d for d in r["decisions"] if d["r4"]]
        if not r4s:
            path = "NO_R4"
        elif r4s[0]["applied"]:
            path = "APPLIED_AT_L1"
        elif any(d["applied"] for d in r4s[1:]):
            path = "R4_APPLIED_LATE"
        else:
            path = "R4_NEVER"
        r["r4_path"] = path
        r["r4_sequence"] = [dict(n_loc=d["n_loc"], dP=d["dP"], applied=d["applied"], would_block=d["would_block"],
                                 struct_zero=d["struct_zero"], post_revoke=d["post_revoke"]) for d in r4s]
        if kk in OLD_CTRL and r["L1"] is not None:
            on, os_ = OLD_CTRL[kk]
            r["old_ctrl_shift"] = dict(d_n_loc=r["L1"]["n_loc"] - on, d_n_S=None if r["L1"]["n_S"] is None else r["L1"]["n_S"] - os_)
        else:
            r["old_ctrl_shift"] = None

    pairs = {}
    for off, on in GATE_PAIRS:
        ro, rn = rows[off], rows[on]
        p = dict(gateoff=off, gateon=on, k7=None, k7_reason=None, cond3=None, cond3_reason=None)
        bad = {"MISSING", "RECOUNT_ERROR"}
        if ro["status"] in bad or rn["status"] in bad:
            p["k7"] = None
            p["k7_reason"] = "row missing"
            p["cond3"] = False
            p["cond3_reason"] = "row missing (rules 7: cond 3 false)"
        else:
            if ro["L1"] is not None and rn["L1"] is not None:
                eq = all(same_float(ro["L1"][f], rn["L1"][f]) for f in ("n_loc", "n_P", "n_S", "dP", "t_P_s", "t_S_s"))
                p["k7"] = eq
                p["k7_reason"] = "L1 tuple equal" if eq else "L1 tuple differs"
                p["L1_off"] = ro["L1"]
                p["L1_on"] = rn["L1"]
            elif ro["L1"] is None and rn["L1"] is None:
                eq = ro["first_loc_n"] == rn["first_loc_n"]
                p["k7"] = eq
                p["k7_reason"] = f"both NO_R4, first LOC {ro['first_loc_n']} vs {rn['first_loc_n']}"
            elif ro["L1"] is not None and rn["L1"] is None:
                nL = ro["L1"]["n_loc"]
                fault_before = [f for f in rn["faults"] if f[0] is not None and f[0] <= nL]
                if fault_before:
                    p["k7"] = None
                    p["k7_reason"] = f"gate-on row ended in FAULT before pair L1 (user decision 2): {fault_before[:3]}"
                else:
                    p["k7"] = False
                    p["k7_reason"] = "gate-on has no R4 decision, no FAULT before pair L1"
            else:
                p["k7"] = False
                p["k7_reason"] = "gate-on has L1, gate-off has none"
            if p["k7"] is not None:
                k["K-7"].add(f"{off}/{on}", "pair_L1", p["k7"], got=p["k7_reason"])
            # condition 3
            if p["k7"] is None:
                p["cond3"] = False
                p["cond3_reason"] = "K-7 None (gate-on FAULT before L1) -> cond 3 false"
            elif p["k7"] is False:
                p["cond3"] = False
                p["cond3_reason"] = "K-7 false (stop)"
            elif ro["status"] != "POS":
                p["cond3"] = True
                p["cond3_reason"] = f"gateoff {ro['status']}: cond 3 not checked for this pair"
            else:
                l1n = rn["decisions"][rn["L1_index"]]
                later_r4 = [d for d in rn["decisions"] if d["r4"] and d["i"] > l1n["i"]]
                ok = (l1n["applied"] and l1n["ev_applied"] >= 1 and later_r4 == []
                      and sum(rn["skipped_order_event_periods"].values()) == 0)
                p["cond3"] = bool(ok)
                p["cond3_reason"] = ("gate-on L1 applied, event present, no later R4 / SKIPPED:order" if ok else
                                     f"gate-on L1 applied={l1n['applied']} ev={l1n['ev_applied']} later_r4={len(later_r4)} "
                                     f"skipped={rn['skipped_order_event_periods']}")
        p["gateon_path"] = rn.get("r4_path")
        p["gateon_r4_sequence"] = rn.get("r4_sequence")
        p["cmd"] = cmd_compare(batch_dir, RULE_ROWS[off]["case"], RULE_ROWS[on]["case"], files_read)
        pairs[on] = p

    # ---------------- F rows (info)
    diag = {}
    for f in DIAG_KEYS:
        r = rows[f]
        d = dict(rem_key=f, status=r["status"], valid=None, invalid_reasons=[], path_class=None)
        if r["status"] in ("MISSING", "RECOUNT_ERROR"):
            d["valid"] = None
            d["note"] = "no information (rules 7)"
            diag[f] = d
            continue
        entry, res = res_by[f]
        inv = []
        # F-only identity: K-1..K-5 items of this row + 2.3 items
        for kk in ("K-1", "K-2", "K-3", "K-4", "K-5"):
            for it in k[kk].failures():
                if it["row"] is not None and f in str(it["row"]).split("/"):
                    inv.append(f"{kk}:{it['item']}")
        kfb = dig(res, "controller_meta", "k1_forced_block") or {}
        c2fb = dig(res, "c2_setup", "k1_forced_block") or {}
        if not isinstance(c2fb, dict):
            c2fb = {"requested": c2fb}
        if kfb.get("mode") != "first":
            inv.append("meta.mode != first")
        if c2fb.get("requested") != "first":
            inv.append("c2_setup.requested != first")
        if kfb.get("class") is None or kfb.get("class") != c2fb.get("class"):
            inv.append("class mismatch meta vs c2_setup")
        if kfb.get("module_sha256") is None or kfb.get("module_sha256") != c2fb.get("module_sha256"):
            inv.append("module_sha256 mismatch meta vs c2_setup")
        if r.get("order_gate_enabled") is not True:
            inv.append("order_gate.enabled not true")
        calls = kfb.get("calls") or []
        n_forced = sum(1 for c in calls if isinstance(c, dict) and c.get("forced") is True)
        if n_forced != 1:
            inv.append(f"forced calls = {n_forced}")
        d["module_sha256"] = kfb.get("module_sha256")
        d["invalid_reasons"] = inv
        d["valid"] = not inv
        d["L1"] = r["L1"]
        d["forced_n_loc"] = kfb.get("forced_n_loc")
        d["forced_t_loc_n"] = per(kfb.get("forced_t_loc_s"))
        d["natural_blocked"] = kfb.get("natural_blocked")
        d["forced_record_dP"] = kfb.get("dP")
        d["FORCED_AT_L1"] = (r["L1"] is not None and kfb.get("forced_n_loc") == r["L1"]["n_loc"]
                             and per(kfb.get("forced_t_loc_s")) == r["L1"]["n_loc"])
        pr = rows[F_L1_PAIR[f]]
        if r["L1"] is not None and pr.get("L1") is not None:
            d["FORCED_PAIR_L1"] = all(same_float(r["L1"][x], pr["L1"][x]) for x in ("n_loc", "n_P", "n_S", "dP", "t_P_s", "t_S_s"))
        else:
            d["FORCED_PAIR_L1"] = None
        d["pair_row"] = F_L1_PAIR[f]
        if r["L1"] is None:
            d["path_class"] = None
            d["path_note"] = "no R4-evaluated LOC"
        else:
            nL = r["L1"]["n_loc"]
            rv_after = [n for n in r["revokes_n"] if n > nL]
            reeval = [x for x in r["decisions"] if x["r4"] and x["n_loc"] > nL
                      and any(nL < n < x["n_loc"] for n in rv_after)]
            r4_after_no_rv = [x["n_loc"] for x in r["decisions"] if x["r4"] and x["n_loc"] > nL and x not in reeval]
            if not rv_after:
                cls = "FORCED_NO_REVOKE"
            elif not reeval:
                cls = "FORCED_REVOKED_NO_REEVAL"
            elif any(x["applied"] for x in reeval):
                cls = "FORCED_R4_LATE"
            else:
                cls = "FORCED_R4_NEVER"
            d["path_class"] = cls
            d["revokes_after_L1"] = rv_after
            d["reeval"] = [dict(n_loc=x["n_loc"], dP=x["dP"], struct_zero=x["struct_zero"], applied=x["applied"],
                                would_block=x["would_block"]) for x in reeval]
            late = [x for x in reeval if x["applied"]]
            d["late_applied"] = None if not late else dict(n_loc=late[0]["n_loc"], dP=late[0]["dP"])
            d["r4_after_L1_without_revoke"] = r4_after_no_rv
            d["any_applied_decision"] = any(x["applied"] for x in r["decisions"])
        d["row_end"] = dict(s_motor_max_m=r["s_motor_max_m"], crawler_gap_end_grid_m=r["crawler_gap_end_grid_m"],
                            crawler_gap_end_all_m=r["crawler_gap_end_all_m"], first_done_t_s=r["first_done_t_s"],
                            first_ready_t_s=r["first_ready_t_s"], final_phase=r["final_phase"],
                            faults=[nm for (_n, nm) in r["faults"]], warns=r["warn_names"])
        diag[f] = d

    # ---------------- flags
    flags = {}
    pos_rows = [x for x in GATEOFF_KEYS if rows[x]["status"] == "POS"]
    flags["THIN_MARGIN"] = [x for x in pos_rows if rows[x]["L1"]["dP"] <= THIN_MARGIN_PERIODS]
    flags["LATE_R4"] = [x for x in pos_rows if rows[x]["L1_post_revoke"]]
    sh = []
    for x in GATEOFF_KEYS:
        for s in rows[x].get("shadow_reloc") or []:
            sh.append(dict(row=x, **s))
    flags["SHADOW_RELOC"] = dict(count=len(sh), struct_zero=sum(1 for s in sh if s["struct_zero"]),
                                 zero_ratio=(sum(1 for s in sh if s["struct_zero"]) / len(sh)) if sh else None,
                                 items=sh)
    flags["PAIR_DIVERGE"] = [dict(pair=f"{p['gateoff']}/{on}", first_diff_n=p["cmd"].get("first_diff_n"))
                             for on, p in pairs.items()
                             if rows[p["gateoff"]]["status"] == "POS" and p["cmd"].get("sha_equal") is False]
    flags["GATEON_PATH"] = {on: rows[on].get("r4_path") for on in GATEON_KEYS}
    flags["OLD_CTRL_SHIFT"] = {x: rows[x].get("old_ctrl_shift") for x in JUDGE_KEYS if rows[x].get("old_ctrl_shift") is not None}
    flag_counts = dict(
        THIN_MARGIN=len(flags["THIN_MARGIN"]), LATE_R4=len(flags["LATE_R4"]),
        SHADOW_RELOC=flags["SHADOW_RELOC"]["count"], SHADOW_RELOC_struct_zero=flags["SHADOW_RELOC"]["struct_zero"],
        PAIR_DIVERGE=len(flags["PAIR_DIVERGE"]),
        GATEON_PATH=sum(1 for v in flags["GATEON_PATH"].values() if v in ("R4_APPLIED_LATE", "R4_NEVER")),
        OLD_CTRL_SHIFT=len(flags["OLD_CTRL_SHIFT"]))
    harness = {}
    for x, (lo, hi, lab) in HARNESS_DP.items():
        L = rows[x].get("L1")
        harness[x] = dict(harness_range=[lo, hi], harness_key=lab, chrono_dP=None if not L else L["dP"],
                          diff_to_range=None if not L or L["dP"] is None else (0 if lo <= L["dP"] <= hi else (L["dP"] - hi if L["dP"] > hi else L["dP"] - lo)))

    # ---------------- conditions and grade
    st = {x: rows[x]["status"] for x in GATEOFF_KEYS}
    st = {x: ("MISSING" if v == "RECOUNT_ERROR" else v) for x, v in st.items()}
    n_pos = sum(1 for v in st.values() if v == "POS")
    cond1 = (all(v in ("POS", "NO_R4") for v in st.values()) and n_pos >= 4
             and any(st[x] == "POS" for x in ("R4", "R5")))
    cond3 = all(pairs[on]["cond3"] is True for on in GATEON_KEYS)
    k_judge = {kk: c.as_dict() for kk, c in k.items()}
    stop_keys = [kk for kk, c in k.items() if c.ok is False]
    reasons = []
    if stop_keys:
        grade = "stop"
        reasons = [f"{kk} false" for kk in stop_keys]
    elif any(v in ("NONPOS", "LATE_STRUCT") for v in st.values()):
        grade = "미달"
        reasons = sorted({"MEASURED_NONPOS" if v == "NONPOS" else "STRUCT_ZERO" for v in st.values() if v in ("NONPOS", "LATE_STRUCT")})
        reasons += [f"{x}:{v}" for x, v in st.items() if v in ("NONPOS", "LATE_STRUCT")]
    elif any(v == "MISSING" for v in st.values()) or n_pos < 4 or all(st[x] == "NO_R4" for x in ("R4", "R5")):
        grade = "판정 불가"
        if any(v == "MISSING" for v in st.values()):
            reasons.append("MISSING: " + ",".join(x for x, v in st.items() if v == "MISSING"))
        if n_pos < 4:
            reasons.append(f"POS {n_pos} < 4")
        if all(st[x] == "NO_R4" for x in ("R4", "R5")):
            reasons.append("R4 and R5 both NO_R4")
    elif cond1 and not cond3:
        grade = "부분 통과"
        reasons = [f"cond3 false at {on}: {pairs[on]['cond3_reason']}" for on in GATEON_KEYS if pairs[on]["cond3"] is not True]
    else:
        grade = "통과"
        reasons = ["cond1, cond2 (known rows), cond3 true"]
    conditions = {"1_MUST": cond1, "1_status": st, "1_pos_count": n_pos,
                  "2_PATCH": "adopt cond 2 carried over (known S-Ch rows, dP -20), not recounted here",
                  "3_PAIR": {on: dict(cond3=pairs[on]["cond3"], reason=pairs[on]["cond3_reason"]) for on in GATEON_KEYS}}

    predictions = make_predictions(rows, pairs, diag, flags, grade)

    out = dict(
        tool=TOOL_NAME, tool_version=TOOL_VERSION, path=2, provisional=True,
        note="path-2 recount; grade is provisional; K-10 is decided in the judgement document",
        k10=None, rules_path=os.path.abspath(rules_path), rules_sha256=rules_sha,
        batch=os.path.abspath(batch_dir), batch_name=batch.get("batch"),
        taken_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        files_read_sha256=files_read,
        k_checks=k_judge, k8_diag_info=k8_info.as_dict(), stop_keys=stop_keys,
        rows=rows, pairs=pairs, diag=diag, flags=flags, flag_counts=flag_counts, harness_compare=harness,
        conditions=conditions, grade_provisional=grade, grade_reasons=reasons, predictions=predictions,
        k10_compare=k10_view(rows, pairs, diag, flag_counts, grade),
    )
    return out


def _strip_v5(argv):
    """Remove v5 options; flags (no value) and value options alike (value = next token not starting with --)."""
    out = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in V5_ARGV_OPTS:
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                i += 2
            else:
                i += 1
            continue
        out.append(tok)
        i += 1
    return strip_argv(out, PER_ROW_ARGV_OPTS)


def cmd_compare(batch_dir, case_a, case_b, files_read):
    pa = os.path.join(batch_dir, case_a, "controller_commands.npz")
    pb = os.path.join(batch_dir, case_b, "controller_commands.npz")
    if not (os.path.isfile(pa) and os.path.isfile(pb)):
        return dict(sha_equal=None, note="controller_commands.npz missing")
    sa, sb = sha256_file(pa), sha256_file(pb)
    files_read[os.path.abspath(pa)] = sa
    files_read[os.path.abspath(pb)] = sb
    out = dict(sha_a=sa, sha_b=sb, sha_equal=(sa == sb), first_diff_n=None)
    if sa != sb:
        try:
            import numpy as np  # only for the first-difference period
            with np.load(pa, allow_pickle=False) as za, np.load(pb, allow_pickle=False) as zb:
                ta, tb = za["t_s"], zb["t_s"]
                ua, ub = za["issued_u_m_s"], zb["issued_u_m_s"]
                m = min(len(ta), len(tb))
                idx = None
                for i in range(m):
                    if ta[i] != tb[i] or not np.array_equal(ua[i], ub[i]):
                        idx = i
                        break
                if idx is None and len(ta) != len(tb):
                    idx = m
                if idx is not None:
                    t_at = ta[idx] if idx < len(ta) else tb[idx]
                    out["first_diff_n"] = per(float(t_at))
                out["first_diff_index"] = idx
        except Exception as exc:
            out["first_diff_error"] = repr(exc)
    return out


def make_predictions(rows, pairs, diag, flags, grade):
    def dp(x):
        L = rows[x].get("L1")
        return None if not L else L["dP"]

    def inr(v, lo, hi):
        return None if v is None else (lo <= v <= hi)

    p = {}
    p["P-1"] = dict(values={x: dp(x) for x in ("R1", "R2", "R3")},
                    inside=all(inr(dp(x), 60, 140) for x in ("R1", "R2", "R3")) if all(dp(x) is not None for x in ("R1", "R2", "R3")) else None)
    n4 = rows["R4"].get("L1")
    n5 = rows["R5"].get("L1")
    p["P-2"] = dict(values={x: dp(x) for x in ("R4", "R5")},
                    inside=(inr(dp("R4"), 120, 240) and inr(dp("R5"), 120, 240) and abs(n4["n_loc"] - n5["n_loc"]) <= 20) if (n4 and n5 and dp("R4") is not None and dp("R5") is not None) else None)
    p["P-3"] = dict(value=dp("R6"), inside=inr(dp("R6"), 90, 180))
    p["P-4"] = dict(statuses={x: rows[x]["status"] for x in GATEOFF_KEYS}, inside=all(rows[x]["status"] == "POS" for x in GATEOFF_KEYS))
    nrv = sum(1 for x in GATEOFF_KEYS if rows[x].get("revokes_after_L1"))
    p["P-5"] = dict(rows_with_revoke_after_L1=nrv, inside=4 <= nrv <= 6)
    zr = flags["SHADOW_RELOC"]["zero_ratio"]
    p["P-6"] = dict(zero_ratio=zr, inside=None if zr is None else zr >= 0.7)
    p["P-7"] = dict(inside=(rows["R4"]["status"] == "POS" and rows["R5"]["status"] == "POS" and abs(dp("R4") - dp("R5")) <= 30)
                    if (dp("R4") is not None and dp("R5") is not None) else None)
    p["P-8"] = dict(inside=all(rows[on].get("r4_path") == "APPLIED_AT_L1" and pairs[on]["cmd"].get("sha_equal") is True for on in GATEON_KEYS),
                    paths={on: rows[on].get("r4_path") for on in GATEON_KEYS},
                    cmd_sha_equal={on: pairs[on]["cmd"].get("sha_equal") for on in GATEON_KEYS})
    p["P-9"] = dict(count=len(flags["THIN_MARGIN"]), inside=len(flags["THIN_MARGIN"]) == 0)
    p["P-10"] = dict(grade=grade, inside=grade == "통과")
    p["P-11"] = dict(inside=all(diag[f].get("FORCED_AT_L1") is True and diag[f].get("FORCED_PAIR_L1") is True for f in DIAG_KEYS),
                     classes={f: diag[f].get("path_class") for f in DIAG_KEYS})
    return p


def k10_view(rows, pairs, diag, flag_counts, grade):
    """Compact view of exactly the K-10 comparison items (rules 9.2)."""
    rv = {}
    for x in JUDGE_KEYS + DIAG_KEYS:
        r = rows[x]
        rv[x] = dict(status=r["status"], L1=r.get("L1"),
                     decisions=[dict(n_loc=d["n_loc"], n_P=d["n_P"], n_S=d["n_S"], dP=d["dP"], r4=d["r4"],
                                     would_block=d["would_block"], applied=d["applied"], post_revoke=d["post_revoke"],
                                     restart_n=d["restart_n"], struct_zero=d["struct_zero"]) for d in r.get("decisions") or []])
    return dict(
        rows=rv,
        pairs={on: dict(k7=p["k7"], cond3=p["cond3"], gateon_path=p["gateon_path"]) for on, p in pairs.items()},
        flag_counts=flag_counts, grade_provisional=grade,
        f_path_class={f: diag[f].get("path_class") for f in DIAG_KEYS},
        f_path_class_note="F classes are info only; a K-10 mismatch here = info-only invalid (user decision 3)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="V5-LAS-K1-REM path-2 independent recount (rules 9.2)")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        out = recount(a.batch, a.rules)
        out["tool_sha256"] = sha256_file(os.path.abspath(__file__))
    except Exception as exc:
        err = dict(tool=TOOL_NAME, path=2, error=repr(exc), traceback=traceback.format_exc())
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(err, f, ensure_ascii=False, indent=1)
        print("PROVISIONAL path-2 recount: TOOL ERROR " + repr(exc))
        print(json.dumps(dict(status="error", grade_provisional=None)))
        return 3
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    g = out["grade_provisional"]
    print(f"PROVISIONAL path-2 recount (K-10 decided outside): grade={g.encode('ascii', 'backslashreplace').decode()}")
    print(json.dumps(dict(status="ok", grade_provisional=g, stop_keys=out["stop_keys"],
                          statuses={x: out["rows"][x]["status"] for x in JUDGE_KEYS + DIAG_KEYS},
                          out=os.path.abspath(a.out)), ensure_ascii=True))
    return {"통과": 0, "미달": 1, "판정 불가": 1, "부분 통과": 1, "stop": 2}.get(g, 3)


if __name__ == "__main__":
    sys.exit(main())
