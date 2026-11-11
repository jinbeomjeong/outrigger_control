"""Path-2 independent recount, harness bundles of las_p5r4_k1_rules.md (+ rev1).

Rules: 06_analysis/02_control/verif_matrix/las_p5r4_k1_rules.md (sha256 5ee2bac0...) and the
record-only addendum las_p5r4_k1_rules_rev1.md, the reading-rule addendum las_p5r4_k1_rules_rev2.md
(RV2-1..RV2-14) and las_p5r4_k1_rules_rev3.md (RV3-1 threshold tolerance 1e-9, RV3-6 time-window bounds in
integer periods, RV3-5 identity). Author: control-expert (path 2).

Independence contract (rules 10.2):
  * Reads only the run jsonl files, the stored baseline jsonl files named in rules appendix A
    (+ the stored P5 pair files of las_revA_targeted_rules_rev2 R2-5), the rules files and their
    .sha256 files. Does not open or import the path-1 judge tools or any project module.
  * Source choices that differ from a straightforward reading are deliberate (rules 10.2):
      - LOC / L1   : k1.decisions first (sorted by t_loc_s); event names only for cross-checks.
      - READY      : values.times.t_first_ready_s (d1.t_ready_s is recorded as a cross-check).
      - event names: keys of event_names, name = split(":", 1)[0], exact match.
  * Integer periods n = round(t / 0.1) (Python builtin round).
  * Priority (rules 16.6) on every layer: stop > undecidable > fail > pass.
  * Error lines (key "error") are counted before judging and listed in full; no list in the
    output is truncated.

Exit codes: 0 pass (provisional), 1 fail or undecidable, 2 stop, 3 tool error.
Grade is provisional; K-10 (path 1 vs path 2) is decided outside this tool.
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

TOOL_NAME = "p5k_recount.py"
TOOL_VERSION = "1"

RULES_SHA = "5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979"
RULES_REV1_SHA = "f39846d6067a7bd409b4ac930d73ebde58a721728ec7d93703ff4627bf21e4b6"
RULES_REV2_SHA = "e0a7d1e56b57df5336fc2fd40835624d93585fb224063f6c8068c2b1ba7b10fc"
RULES_REV3_SHA = "5798dd320cdaad5e76b5b287c7496a84a23684f2b4e09557b07a71d95ede2a0b"
K1_TOKEN_JOB_KEYS = {"k1", "k1_candidate", "k1_order_gate", "las_off"}   # rev2 RV2-14

PERIOD_S = 0.1
F_MIN_N = 9414.589
F_LINE_N = 10414.589            # C-1 / C-F (F_min + 1 kN)
F_LINE_KN = 10.414589           # rev3 T-15 FLAG band upper end (kN field)
G1_KN = 10.400                  # G-1 / G-1H / G-1Q
G2P_KN = 11.414589              # G-2' (F_min + 2 kN)
CS_LIMIT_M = 0.001              # C-S
R1_MEDIAN_S = 1.0
R2_MAX_S = 5.0
C4_RATIO = 0.8
S8_MAX_EXCEPTIONS = 5
S8_MAX_DT_S = 15.0
THIN_MARGIN_PERIODS = 12
M2_P5_MAX_RANGE_KN = 1.1049128292761132
EMPTY_SHA = hashlib.sha256(b"").hexdigest()

TAG_VB = "final_C4G2_P3_LAS_K1"
TAG_V0 = "final_C4G2_LAS_K1"
FORBIDDEN_TAGS = {"final_C4G2_K1", "final_C4G2_P3_K1", "final_C4G2_LAS", "final_C4G2_P3_LAS",
                  "final_C4G2", "final_C4G2_P3"}

# b0 (rules 2, revA 1.2 "remaining values b0") and P5r4 settings
B0_SETTINGS = dict(enable=True, sum_on_fraction_W=0.6, light_leg_fraction_of_F_min=3.5,
                   slow_mean_fraction=0.16, sum_off_fraction_W=0.85, off_periods=5, max_s=1.5,
                   rho_on=0.18, require_soil_response=True, min_active_periods=0, end_ramp_periods=0)
P5R4_SETTINGS = dict(B0_SETTINGS, light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)
N_R = 4

ARM_LABEL = {"ref": "P0", "cand": "P5r4"}

BUNDLES = ["Z-0", "Z-A", "Z-T", "Z-S", "Z-C", "Z-X"]
BUNDLE_ARMS = {"Z-0": ("ref",), "Z-A": ("cand",), "Z-T": ("ref", "cand"), "Z-S": ("ref", "cand"),
               "Z-C": ("ref", "cand"), "Z-X": ("ref",)}

# rules appendix A
BASE_FILES = {
    "revA_R0": ("las/revA2/revA_R0.jsonl", "04cadd3cdd63372518ee8fcf3620bfef43695f08583a99b7458a0c53b7f777f3"),
    "revA_R0A": ("las/revA2/revA_R0A.jsonl", "28df99076cc309718e9dcfc270fed5d390a111f5ace8ce77ddbc3a3c8b0f14f8"),
    "revA_RQ": ("las/revA2/revA_RQ.jsonl", "93ced32cedb57888c37ea06dfbbe966c12c35d858f5b92a543e816f86cf953ca"),
    "revA_RT": ("las/revA2/revA_RT.jsonl", "c72f7e0882c50d86e565366866526ed55073d8bfef5c9f959b82c0e2885afd54"),
    "las_T1": ("las/las_T1.jsonl", "3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b"),
    "las_T2": ("las/las_T2.jsonl", "2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb"),
    "revA_RS": ("las/revA2/revA_RS.jsonl", "7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d"),
    "k1_YS": ("las/k1/k1_YS.jsonl", "a31153a64ed9cbdf7410082e8dbda81b79e6d607c0a238d510ac34c0c9333ac6"),
    "s2d_SC": ("soil_defer/s2d_SC.jsonl", "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa"),
    "k1_YP": ("las/k1/k1_YP.jsonl", "0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3"),
    "revA_RX": ("las/revA2/revA_RX.jsonl", "04f7a4dcf435b66934a811af6cee4cb5fa657f8e897f4a503321dd126f4b0d78"),
    # stored P5 pairs for K-A1..K-A4 and M-1..M-3 (las_revA_targeted_rules_rev2 R2-5 / H-10)
    "rev_RG": ("las/rev/rev_RG.jsonl", "7e8c3b4173f1fc682e665ad173589dbbe335ba914a06d5ef2984c5807bb8cca6"),
    "revA_RH": ("las/revA/revA_RH.jsonl", "f934cbd945353fe236e5313ed5b0b147c39a7e30f6b1b02cfc5557739422b0c9"),
}
LIST_SHA = {
    "Z-0": "4d1591ba30b686bb6484072c1e63df51130791c2d0cee7106d9ae7d1bc4b6c9e",
    "Z-A": "14f89f1f9209114d7e5a2c84f5b45a7d6c650e44ac3de41dd4c93c8733451577",
    "Z-T": "4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933",
    "Z-S": "19c78b49197ac53da5ae50808555c5879aabc90765589ea220830d5588a23950",
    "Z-C": "fe6c9c46f2c799ee440d8a2a5d99d88099c51586297afd01d7201a52d26389d9",
    "Y-Pa": "dc1e65d49bc0ea34fd04fdb7ba4eeceb7fc576ee15de9658dbe26927598b753b",
    "Z-C-out": "f20bb9e0b1b570660fd15c2a33a2abd66308efce10e1aeb3185cc178956edea7",
}

# fields each criterion reads (rules 5.0: absent field -> that pair is undecidable for it)
CRIT_FIELDS = {
    "C-2": dict(all=["commands_sha256", "final_phase", "event_names", "values.times.t_first_ready_s"],
                d1=["d1", "d1.items", "d1.verdict", "d1.fail_items"]),
    "P3": dict(all=[], d1=["d1.items"]),
    "C-F": dict(all=[], d1=["d1.F_judged_min_N"]),
    "C-S": dict(all=[], d1=["d1.stroke_max_m"]),
    "CK-1": dict(all=["k1.decisions"], d1=[]),
    "R-1/R-2": dict(all=["commands_sha256", "values.times.t_first_ready_s"], d1=[]),
    "PAIR_DIVERGE": dict(all=["commands_sha256", "las.start_t_s"], d1=[]),
}
USES_ANCHOR = ("1", "2", "1+2")

EV_LOC = "crawler_liftoff_confirmed"
EV_BIAS = "INFO_CLEARANCE_BIAS"
EV_ANCHOR = "INFO_LOC_CLEARANCE_ANCHOR"
EV_FLAT = "INFO_LOC_FLAT_SOIL_MARGIN"
EV_FLAT_SKIP = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED"
RAMP_END_REASONS = {"done", "loc", "phase", "soil", "reapproach", "zone"}
SAFE_END_REASONS = {"loc", "phase", "soil", "reapproach", "zone"}

PRIORITY = {"stop": 4, "undecidable": 3, "incomplete": 3, "fail": 2, "pass": 1}


# ----------------------------------------------------------------------------- helpers

def per(t):
    if t is None:
        return None
    return round(t / PERIOD_S)


def base_name(name):
    return str(name).split(":", 1)[0]


def name_suffix(name):
    parts = str(name).split(":", 1)
    return parts[1] if len(parts) > 1 else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def list_sha(keys):
    return hashlib.sha256("".join(k + "\n" for k in sorted(keys)).encode("utf-8")).hexdigest()


MISSING = object()


def dig(d, path, default=MISSING):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def val(d, path):
    """Value or None when absent."""
    v = dig(d, path)
    return None if v is MISSING else v


def has(d, path):
    return dig(d, path) is not MISSING


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not (isinstance(x, float) and math.isnan(x))


# ----------------------------------------------------------------------------- rev3 RV3-1 / RV3-6
EPS_THR = 1e-9
"""rev3 RV3-1: threshold-comparison tolerance (absolute, in the unit of the compared field)."""


def t_ge(x, L):
    """x >= L with RV3-1: x >= L - 1e-9."""
    return x >= L - EPS_THR


def t_gt(x, L):
    """x > L with RV3-1: x > L + 1e-9."""
    return x > L + EPS_THR


def t_le(x, L):
    """x <= L with RV3-1: x <= L + 1e-9."""
    return x <= L + EPS_THR


def t_lt(x, L):
    """x < L with RV3-1: x < L - 1e-9."""
    return x < L - EPS_THR


def t_in(x, a, b):
    """closed interval [a, b] with RV3-1: a - 1e-9 <= x <= b + 1e-9."""
    return a - EPS_THR <= x <= b + EPS_THR


def combine(statuses):
    """Rules 16.6 on a list of statuses (not_run / None ignored)."""
    best = None
    for s in statuses:
        if s not in PRIORITY:
            continue
        if best is None or PRIORITY[s] > PRIORITY[best]:
            best = s
    if best == "incomplete":
        best = "undecidable"
    return best


def read_jsonl(path):
    lines = []
    with open(path, encoding="utf-8") as f:
        for i, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            obj["__lineno__"] = i
            lines.append(obj)
    return lines


def find_strings(obj, key_filter=None):
    """All string values in a nested object (optionally only under keys containing key_filter)."""
    out = []

    def walk(o, under):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, under or (key_filter is None) or (key_filter in str(k).lower()))
        elif isinstance(o, list):
            for v in o:
                walk(v, under)
        elif isinstance(o, str) and under:
            out.append(o)

    walk(obj, key_filter is None)
    return out


def find_key(obj, key):
    """All values stored under a dict key named `key` anywhere in obj."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key:
                    out.append(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return out


def line_key(line):
    return val(line, "rev.key")


def line_arm(line):
    lc = line.get("las_candidate")
    if lc is None:
        lc = val(line, "las.candidate")
    for arm, label in ARM_LABEL.items():
        if lc == label:
            return arm
    return None


def setting_of(line):
    s = val(line, "job.setting")
    if s in ("VB", "V0"):
        return s
    k = line_key(line) or ""
    toks = k.split("|")
    for t in toks:
        if t in ("VB", "V0"):
            return t
    return None


def group_token(key):
    toks = (key or "").split("|")
    return toks[1] if len(toks) > 1 else None


def event_base_counts(line):
    en = line.get("event_names")
    if not isinstance(en, dict):
        return None
    out = {}
    for k, v in en.items():
        b = base_name(k)
        out[b] = out.get(b, 0) + (v if isinstance(v, int) and not isinstance(v, bool) else 1)
    return out


def fault_warn_names(line):
    c = event_base_counts(line)
    if c is None:
        return None
    return sorted(n for n in c if n.startswith("FAULT") or n.startswith("WARN"))


def decisions_of(line):
    d = val(line, "k1.decisions")
    if not isinstance(d, list):
        return None
    return sorted([x for x in d if isinstance(x, dict)],
                  key=lambda x: (x.get("t_loc_s") is None, x.get("t_loc_s") or 0.0))


def decision_dP(dec):
    nP, nS = per(dec.get("t_P_s")), per(dec.get("t_S_s"))
    return None if (nP is None or nS is None) else nP - nS


def l1_of(decs):
    if decs is None:
        return None
    r4 = [d for d in decs if d.get("r4_due_without_gate") is True]
    return r4[0] if r4 else None


def l1_tuple(dec):
    if dec is None:
        return None
    return dict(n_loc=per(dec.get("t_loc_s")), n_P=per(dec.get("t_P_s")), n_S=per(dec.get("t_S_s")),
                dP=decision_dP(dec), applied=dec.get("applied") is True, t_loc_s=dec.get("t_loc_s"),
                t_P_s=dec.get("t_P_s"), t_S_s=dec.get("t_S_s"))


# ----------------------------------------------------------------------------- rev1 anchor record

def anchor_record_harness(line):
    """las_p5r4_k1_rules_rev1 RV1-1 / RV1-5 record for one harness line."""
    missing = []
    counts = event_base_counts(line)
    if counts is None:
        missing.append("event_names")
        path = None
        n_loc = None
    else:
        p1 = counts.get(EV_BIAS, 0) > 0
        p2 = counts.get(EV_ANCHOR, 0) > 0
        path = "1+2" if (p1 and p2) else ("1" if p1 else ("2" if p2 else "3"))
        n_loc = counts.get(EV_LOC, 0)
    tl_first = val(line, "values.events.t_loc_first_s")
    tl_last = val(line, "values.events.t_loc_last_s")
    if not has(line, "values.events.t_loc_first_s"):
        missing.append("values.events.t_loc_first_s")
    sm = val(line, "anchor.soil_meta")
    if not isinstance(sm, dict):
        missing.append("anchor.soil_meta")
        sm = {}
    tp_last = sm.get("t_P_s")
    calls = val(line, "anchor.loc_calls")
    calls_src = "anchor.loc_calls"
    if not isinstance(calls, list):
        calls = val(line, "k1.loc_calls")
        calls_src = "k1.loc_calls"
        if not isinstance(calls, list):
            calls = None
            calls_src = None
            missing.append("anchor.loc_calls")
    tp_first = None
    tp_first_src = None
    first_call = None
    if calls:
        first_call = calls[0] if isinstance(calls[0], dict) else None
        if first_call is not None and first_call.get("t_P_s") is not None:
            tp_first = first_call.get("t_P_s")
            tp_first_src = calls_src + "[0].t_P_s"
    if tp_first is None and n_loc == 1 and tp_last is not None:
        tp_first = tp_last
        tp_first_src = "single LOC: anchor.soil_meta.t_P_s"
    raw = sm.get("bias_corner_raw_m")
    app = sm.get("bias_corner_m")
    agree = None
    if path is not None and isinstance(sm, dict) and "loc_anchor_applied" in sm:
        nonzero = isinstance(app, list) and any(num(x) and x != 0.0 for x in app)
        agree = ((path in ("2", "1+2")) == (sm.get("loc_anchor_applied") is True)) and \
                ((path == "3") or nonzero)
    return dict(path=path, n_loc=n_loc, t_L_first_s=tl_first, t_L_last_s=tl_last,
                n_L_first=per(tl_first), n_L_last=per(tl_last),
                t_P_first_s=tp_first, t_P_first_source=tp_first_src, n_P_first=per(tp_first),
                t_P_last_s=tp_last, n_P_last=per(tp_last),
                bias_corner_raw_m=raw, bias_corner_m=app, loc_anchor_bias_mm=sm.get("loc_anchor_bias_mm"),
                corner_order=sm.get("corner_order"),
                first_loc_bias_corner_raw_m=None if first_call is None or calls_src != "anchor.loc_calls" else first_call.get("bias_corner_raw_m"),
                first_loc_bias_corner_m=None if first_call is None or calls_src != "anchor.loc_calls" else first_call.get("bias_corner_m"),
                anchor_meta_agree=agree, missing=missing)


def anchor_shift(ra, ca):
    """RV1-2 FLAG ANCHOR_SAMPLE_SHIFT: True / False / None (+ reason)."""
    pr, pc = ra.get("path"), ca.get("path")
    uses = (pr in USES_ANCHOR) or (pc in USES_ANCHOR)
    if (pr is None or pc is None) and not uses:
        return None, "ANCHOR_RECORD_MISSING:path"
    if not uses:
        return False, "both arms path 3"
    compared = []
    differ = False
    for slot in ("n_P_first", "n_P_last"):
        a, b = ra.get(slot), ca.get(slot)
        if a is not None and b is not None:
            compared.append(slot)
            if a != b:
                differ = True
    if not compared:
        return None, "ANCHOR_RECORD_MISSING:t_P"
    return differ, "compared " + ",".join(compared)


def anchor_pair_record(ra, ca):
    flag, reason = anchor_shift(ra, ca)

    def d(slot):
        a, b = ra.get(slot), ca.get(slot)
        return None if (a is None or b is None) else b - a

    return dict(flag=flag, reason=reason, ref=ra, cand=ca, d_n_P_first=d("n_P_first"),
                d_n_P_last=d("n_P_last"), d_n_L_first=d("n_L_first"), d_n_L_last=d("n_L_last"))


# ----------------------------------------------------------------------------- pair criteria

def items_of(line):
    it = val(line, "d1.items")
    return it if isinstance(it, dict) else None


def pair_kind(ref, cand):
    if has(ref, "job.case") or has(cand, "job.case"):
        return "verdict"
    return "d1"


def eval_pair(ref, cand, bundle):
    """C-2, P3, C-F, C-S, CK-1, hash / divergence, READY and records for one pair."""
    kind = pair_kind(ref, cand)
    und = {c: [] for c in CRIT_FIELDS}   # undecidable reasons per criterion (rules 5.0, R1-3)
    out = dict(kind=kind)

    # ---- required fields per criterion
    for crit, spec in CRIT_FIELDS.items():
        fields = list(spec["all"]) + (list(spec["d1"]) if kind == "d1" else [])
        for side, line in (("ref", ref), ("cand", cand)):
            for p in fields:
                if not has(line, p):
                    und[crit].append(f"{side}:missing:{p}")

    h_ref, h_cand = ref.get("commands_sha256"), cand.get("commands_sha256")
    hash_equal = (h_ref is not None and h_ref == h_cand)
    out["hash_equal"] = hash_equal
    cand_started = val(cand, "las.start_t_s") is not None
    out["cand_las_started"] = cand_started
    out["ref_las_started"] = val(ref, "las.start_t_s") is not None
    # rules 3: premise = cand LAS-b not started
    out["PAIR_DIVERGE"] = bool(has(cand, "las.start_t_s") and not cand_started and h_ref is not None
                               and h_cand is not None and not hash_equal)
    out["PAIR_CMD_DIFF"] = bool(cand_started and h_ref is not None and h_cand is not None and not hash_equal)

    # ---- C-2 (rules 6.2 = K1 rev1 R1-2, las_rev 5.2 / rev1 R1-1..R1-3)
    c2 = []
    items_only_ref, items_only_cand = [], []
    p3, p3_base_false = [], []
    if kind == "d1" and items_of(ref) is not None and items_of(cand) is not None:
        vr, vc = val(ref, "d1.verdict"), val(cand, "d1.verdict")
        if vr in ("pass", "allowed_stop") and vc not in ("pass", "allowed_stop"):
            c2.append(f"a:verdict:{vr}->{vc}")
        ir, ic = items_of(ref), items_of(cand)
        items_only_ref = sorted(set(ir) - set(ic))
        items_only_cand = sorted(set(ic) - set(ir))
        for k in sorted(set(ir) | set(ic)):
            a, b = ir.get(k), ic.get(k)
            if (a is True and b is not True) or (a is None and b is False):
                c2.append(f"a:item:{k}:{a}->{b}")
            if k.startswith("P3-1") or k.startswith("P3-5"):
                if (a is True and b is not True) or (a is None and b is False):
                    p3.append(f"{k}:{a}->{b}")
                elif a is False:
                    p3_base_false.append(k)
        fr = val(ref, "d1.fail_items") or []
        fc = val(cand, "d1.fail_items") or []
        new_fail = sorted(set(fc) - set(fr))
        if new_fail:
            c2.append("a:new_fail_items:" + ",".join(new_fail))
        if hash_equal and ir != ic:
            und["C-2"].append("R1-3:hash_equal_but_d1.items_differ")
            und["P3"].append("R1-3:hash_equal_but_d1.items_differ")
    fpr, fpc = ref.get("final_phase"), cand.get("final_phase")
    if fpr == "ready" and fpc != "ready":
        c2.append(f"b:final_phase:ready->{fpc}")
    tr, tc = val(ref, "values.times.t_first_ready_s"), val(cand, "values.times.t_first_ready_s")
    if tr is not None and tc is None:
        c2.append("b:ready_time_lost")
    nr, nc = fault_warn_names(ref), fault_warn_names(cand)
    if nr is not None and nc is not None:
        new = sorted(set(nc) - set(nr))
        if new:
            c2.append("c:new_events:" + ",".join(new))
    out.update(c2_violations=c2, items_only_ref=items_only_ref, items_only_cand=items_only_cand,
               p3_violations=p3, p3_baseline_false=p3_base_false)

    # ---- C-F, C-S (D-1 pairs)
    out["cf"] = None
    out["cs"] = None
    if kind == "d1":
        Fr, Fc = val(ref, "d1.F_judged_min_N"), val(cand, "d1.F_judged_min_N")
        # rev2 RV2-2: ref None -> out of scope (ref_none); cand None with ref in scope -> violation
        if num(Fr) and t_ge(Fr, F_LINE_N):
            out["cf"] = dict(in_scope=True, ref_N=Fr, cand_N=Fc, violation=not (num(Fc) and t_ge(Fc, F_LINE_N)),
                             ref_none=False)
        else:
            out["cf"] = dict(in_scope=False, ref_N=Fr, cand_N=Fc, violation=False, ref_none=not num(Fr))
        sr, sc = val(ref, "d1.stroke_max_m"), val(cand, "d1.stroke_max_m")
        if num(sr) and num(sc):
            out["cs"] = dict(ref_m=sr, cand_m=sc, delta_m=sc - sr, violation=t_gt(sc - sr, CS_LIMIT_M), ref_none=False)
        elif not num(sc) and num(sr):
            out["cs"] = dict(ref_m=sr, cand_m=sc, delta_m=None, violation=True, ref_none=False)
        else:
            # ref None (cand value or None): out of scope, recorded as ref_none (RV2-2 2)
            out["cs"] = dict(ref_m=sr, cand_m=sc, delta_m=None, violation=False, ref_none=True)

    # ---- CK-1
    dr, dc = decisions_of(ref), decisions_of(cand)
    ck = None
    if dr is not None and dc is not None:
        L1r, L1c = l1_of(dr), l1_of(dc)
        ref_any = any(d.get("r4_due_without_gate") is True and d.get("applied") is True for d in dr)
        cand_any = any(d.get("r4_due_without_gate") is True and d.get("applied") is True for d in dc)
        lost = (L1r is not None and L1r.get("applied") is True and not cand_any)
        gained = (cand_any and not ref_any)
        cls = "R4_LOST" if lost else ("R4_GAINED" if gained else
                                     ("KEPT" if (ref_any and cand_any) else "NONE"))
        ck = dict(cls=cls, violation=lost, ref_L1=l1_tuple(L1r), cand_L1=l1_tuple(L1c),
                  THIN_MARGIN=(L1c is not None and decision_dP(L1c) is not None and decision_dP(L1c) <= THIN_MARGIN_PERIODS))
    out["ck1"] = ck

    # ---- READY
    dt = (tc - tr) if (num(tr) and num(tc)) else None
    out["ready"] = dict(ref_s=tr, cand_s=tc, dt_s=dt,
                        d1_ref_s=val(ref, "d1.t_ready_s"), d1_cand_s=val(cand, "d1.t_ready_s"),
                        source_agree=(val(ref, "d1.t_ready_s") == tr and val(cand, "d1.t_ready_s") == tc)
                        if kind == "d1" else None)

    # ---- records (6.4)
    def las_rec(line):
        return dict(start_t_s=val(line, "las.start_t_s"), end_t_s=val(line, "las.end_t_s"),
                    end_reason=val(line, "las.end_reason"), active_periods=val(line, "las.active_periods"),
                    lambda0=val(line, "las.ramp.start_factor"), ramp_end_reason=val(line, "las.ramp.end_reason"),
                    ramp_periods_applied=val(line, "las.ramp.periods_applied"))
    out["record"] = dict(
        las_ref=las_rec(ref), las_cand=las_rec(cand),
        t_loc_first_s=[val(ref, "values.events.t_loc_first_s"), val(cand, "values.events.t_loc_first_s")],
        F_after_liftoff=[val(ref, "values.forces.after_liftoff"), val(cand, "values.forces.after_liftoff")],
        F_judged_min_N=[val(ref, "d1.F_judged_min_N"), val(cand, "d1.F_judged_min_N")],
        stroke_max_m=[val(ref, "d1.stroke_max_m"), val(cand, "d1.stroke_max_m")],
    )
    out["anchor"] = anchor_pair_record(anchor_record_harness(ref), anchor_record_harness(cand))
    out["undecidable_reasons"] = {c: v for c, v in und.items() if v}
    return out


# ----------------------------------------------------------------------------- bundle loading

def group_lines(lines, arms, keyfun):
    """-> (groups {(arm,key): [line]}, error_lines, stray)"""
    groups, errors, stray = {}, [], []
    for ln in lines:
        if "error" in ln:
            errors.append(dict(lineno=ln.get("__lineno__"), key=line_key(ln), label=val(ln, "rev.label"),
                               error=str(ln.get("error"))[:2000], attempt=val(ln, "rev.attempt")))
            continue
        arm = line_arm(ln)
        if arm not in arms:
            stray.append(dict(lineno=ln.get("__lineno__"), key=line_key(ln), arm_field=ln.get("las_candidate")))
            continue
        groups.setdefault((arm, keyfun(ln)), []).append(ln)
    return groups, errors, stray


def za_key(line):
    return (line_key(line), val(line, "rev.label"))


# ----------------------------------------------------------------------------- K checks per line

def k_line_checks(line, arm, sink, row_id):
    """K-0 (line part), K-3, K-4, K-5 items for one line. sink: dict K-name -> list of items."""
    def add(k, item, ok, got=None, want=None):
        sink.setdefault(k, []).append(dict(row=row_id, item=item, ok=ok, got=got, want=want))

    rules_strings = set(find_strings(line, "rules"))
    if rules_strings:
        add("K-0", "line_records_rules_sha", RULES_SHA in rules_strings, got=None, want=RULES_SHA)
        add("K-0", "line_records_rules_rev1_sha", RULES_REV1_SHA in rules_strings, got=None, want=RULES_REV1_SHA)
    else:
        add("K-0", "line_records_rules_sha", None, got="no rules sha field found")
    st = setting_of(line)
    want_tag = TAG_VB if st == "VB" else (TAG_V0 if st == "V0" else None)
    tag = line.get("controller_tag")
    add("K-3", "controller_tag_exact", want_tag is not None and tag == want_tag, got=tag, want=want_tag)
    add("K-3", "no_TCL_or_old_tag", isinstance(tag, str) and "_TCL" not in tag and tag not in FORBIDDEN_TAGS, got=tag)
    # K-4
    k1en = val(line, "k1.enabled")
    add("K-4", "k1.enabled_true", k1en is True, got=k1en)
    gates = [g for g in find_key(line, "flat_soil_margin_order_gate") if isinstance(g, bool)]
    add("K-4", "flat_soil_margin_order_gate_true", (all(gates) if gates else None), got=gates or "absent")
    tcl = [t for t in find_key(line, "touch_creep_latch") if isinstance(t, dict)]
    if tcl:
        add("K-4", "touch_creep_latch_off", all(t.get("enable") is False for t in tcl), got=[t.get("enable") for t in tcl])
    else:
        add("K-4", "touch_creep_latch_off", None, got="absent")
    job = line.get("job") if isinstance(line.get("job"), dict) else {}
    jk = sorted(k for k in job if k in K1_TOKEN_JOB_KEYS)
    add("K-4", "no_k1_or_las_off_token_in_job", jk == [], got=jk)
    # K-5
    s = val(line, "las.settings")
    want = B0_SETTINGS if arm == "ref" else P5R4_SETTINGS
    if isinstance(s, dict):
        bad = {k: (s.get(k), v) for k, v in want.items() if s.get(k) != v}
        add("K-5", "las.settings_eq_" + ARM_LABEL[arm], bad == {}, got=bad or None)
    else:
        add("K-5", "las.settings_present", False, got="absent")
    a1, a2 = line.get("las_candidate"), val(line, "las.candidate")
    if a1 is not None and a2 is not None:
        add("K-5", "las_candidate_eq_las.candidate", a1 == a2, got=[a1, a2])


def identity_of(line):
    for p in ("rev.identity", "identity", "p5k.identity", "k1.identity"):
        v = val(line, p)
        if isinstance(v, dict) and "git_head" in v:
            return p, v
    return None, None


# ----------------------------------------------------------------------------- Z-A

def za_criteria(cand_lines, p5_pairs, sink_k):
    """6.1 for the 102 Z-A lines: G-1/G-1H/G-1Q, G-2', G-3, G-4 (K-A1..K-A6, K-A8) + records."""
    res = dict(G1={}, G2p=None, G3={}, KA={}, records={})
    sub = {"LT": [], "LH": [], "LQ": []}
    for (key, label), ln in cand_lines.items():
        kind = None
        for t in ("LT", "LH", "LQ"):
            if label and f"-{t}-" in label:
                kind = t
        if kind:
            sub[kind].append(((key, label), ln))
    g2p_fail, between = [], []
    for kind, items in sub.items():
        fails = []
        for (key, label), ln in items:
            frl, fj = val(ln, "diag.summary.F_RL_kN"), val(ln, "diag.summary.F_judged_min_kN")
            ok = num(frl) and num(fj) and t_ge(frl, G1_KN) and t_ge(fj, G1_KN)
            if not ok:
                fails.append(dict(key=key, label=label, F_RL_kN=frl, F_judged_min_kN=fj))
            ok2 = num(frl) and num(fj) and t_ge(frl, G2P_KN) and t_ge(fj, G2P_KN)
            if not ok2:
                g2p_fail.append(dict(key=key, label=label, F_RL_kN=frl, F_judged_min_kN=fj))
            for fname, v in (("F_RL_kN", frl), ("F_judged_min_kN", fj)):
                # rev3 T-15: 10.400 <= v < 10.414589 kN, each value counted separately
                if num(v) and t_ge(v, G1_KN) and t_lt(v, F_LINE_KN):
                    between.append(dict(key=key, label=label, field=fname, value_kN=v))
        res["G1"][kind] = dict(n=len(items), violations=fails, ok=(fails == []))
    res["G2p"] = dict(n=sum(len(v) for v in sub.values()), violations=g2p_fail, ok=(g2p_fail == []))
    res["records"]["between_10p400_and_10p4146"] = between
    # G-3 per sub-bundle (lines present / error 0 checked by caller), level budget, gate_consistent
    for kind, items in sub.items():
        bad = []
        for (key, label), ln in items:
            lb = val(ln, "diag.touch_budget.level_budget_periods")
            gc = val(ln, "diag.summary.gate_consistent")
            if lb != 0 or gc is not True:
                bad.append(dict(key=key, label=label, level_budget_periods=lb, gate_consistent=gc))
        res["G3"][kind] = dict(n=len(items), bad=bad, ok=(bad == []))
    # K-A5 / K-A6 / K-A8 (all 102), K-A1..K-A4 (LT/LH vs stored P5)
    ka = {f"K-A{i}": [] for i in (1, 2, 3, 4, 5, 6, 8)}
    for (key, label), ln in cand_lines.items():
        rid = f"{key}#{label}"
        er = val(ln, "las.end_reason")
        sf = val(ln, "las.ramp.start_factor")
        pa = val(ln, "las.ramp.periods_applied")
        rer = val(ln, "las.ramp.end_reason")
        p5 = p5_pairs.get((key, label.replace("P5r4-", "P5-", 1) if label else None))
        if er in ("sum", "time") and num(sf) and t_lt(sf, 1.0):
            ok = (rer in RAMP_END_REASONS and num(pa) and pa <= N_R and (rer != "done" or pa == N_R))
            if p5 is not None:
                ok = ok and (ln.get("commands_sha256") != p5.get("commands_sha256"))
            ka["K-A5"].append(dict(row=rid, ok=bool(ok), got=dict(end_reason=er, start_factor=sf, ramp_end=rer,
                                                                  periods_applied=pa, p5_pair=p5 is not None)))
        else:
            ka["K-A6"].append(dict(row=rid, ok=(pa == 0), got=dict(end_reason=er, start_factor=sf, periods_applied=pa)))
        s = val(ln, "las.settings") or {}
        ka["K-A8"].append(dict(row=rid, ok=(s.get("light_leg_fraction_of_F_min") == 4.5 and s.get("min_active_periods") == 0
                                            and s.get("end_ramp_periods") == N_R),
                               got=[s.get("light_leg_fraction_of_F_min"), s.get("min_active_periods"), s.get("end_ramp_periods")]))
        if label and ("-LT-" in label or "-LH-" in label):
            if p5 is None:
                ka["K-A1"].append(dict(row=rid, ok=None, got="no stored P5 pair"))
                continue
            f1 = ("las.start_t_s", "las.end_t_s", "las.end_reason", "las.active_periods", "las.scaled_periods", "las.start_leg")
            bad = [f for f in f1 if val(ln, f) != val(p5, f)]
            ka["K-A1"].append(dict(row=rid, ok=bad == [], got=bad))
            te = val(ln, "las.end_t_s")
            per_c = {per(p.get("t_s")): p.get("cmd_mm_s") for p in (val(ln, "diag.periods") or []) if isinstance(p, dict)}
            per_p = {per(p.get("t_s")): p.get("cmd_mm_s") for p in (val(p5, "diag.periods") or []) if isinstance(p, dict)}
            bad2 = []
            if num(te):
                for p in (val(ln, "diag.periods") or []):
                    t = p.get("t_s")
                    if num(t) and per(t) < per(te):   # rev3 W-1
                        n = per(t)
                        if n not in per_p or per_p[n] != per_c.get(n):
                            bad2.append(n)
            ka["K-A2"].append(dict(row=rid, ok=(bad2 == [] and num(te)), got=bad2 if num(te) else "end_t_s not numeric"))
            ka["K-A3"].append(dict(row=rid, ok=val(ln, "diag.summary.t_lift_s") == val(p5, "diag.summary.t_lift_s"),
                                   got=[val(ln, "diag.summary.t_lift_s"), val(p5, "diag.summary.t_lift_s")]))
            fw_c = val(ln, "diag.force_window.rows") or []
            fw_p = val(p5, "diag.force_window.rows") or []
            rows_p = {r[0]: r for r in fw_p if isinstance(r, list) and r}
            bad4 = []
            if num(te):
                L_end = te + 0.1   # rev3 T-19: float window end computed first
                for r in fw_c:
                    if isinstance(r, list) and r and r[0] in rows_p and num(r[0]) and t_lt(r[0], L_end):
                        if r != rows_p[r[0]]:
                            bad4.append(r[0])
            ka["K-A4"].append(dict(row=rid, ok=(bad4 == [] and num(te)), got=bad4))
    res["KA"] = {k: dict(n=len(v), failures=[x for x in v if x["ok"] is False],
                         not_evaluable=[x for x in v if x["ok"] is None], ok=all(x["ok"] is not False for x in v))
                 for k, v in ka.items()}
    # records: G-2 R_c (j <= 3 integer, R-G), G-2H (j in 0..3.5 step .5), 16-point union, Q-1..Q-5, M-1..M-3
    cells = {}
    for (key, label), ln in cand_lines.items():
        cen = val(ln, "diag.touch_budget.centre")
        j = val(ln, "diag.touch_budget.j")
        frl = val(ln, "diag.summary.F_RL_kN")
        cells.setdefault((setting_of(ln), cen), []).append((j, frl, ln, label, key))

    def rng(vals):
        vals = [v for v in vals if num(v)]
        return (max(vals) - min(vals)) if vals else None

    g2 = {}
    for (st, cen), pts in sorted(cells.items(), key=lambda kv: str(kv[0])):
        # grid-point selection j <= 3 / j <= 3.5 (not in the RV3-1.2 table; RV3-1.2 last sentence: same form)
        rg = [f for (j, f, _l, lab, _k) in pts if lab and "-LT-" in lab and num(j) and t_le(j, 3)]
        rh = [f for (j, f, _l, lab, _k) in pts if lab and ("-LT-" in lab or "-LH-" in lab) and num(j) and t_le(j, 3.5)]
        allp = [f for (j, f, _l, _lab, _k) in pts]
        rc, ruc = rng(rg), rng(rh)
        g2[f"{st}|{cen}"] = dict(R_c=rc, R_union_c=ruc, range_16=rng(allp), n_points=len(pts),
                                 G2_le_0p5=None if rc is None else t_le(rc, 0.500),
                                 G2H_le_0p5=None if ruc is None else t_le(ruc, 0.500))
    res["records"]["G2_ranges"] = g2
    # Q-1..Q-5 (rev2 R2-3.1, rev3 RQ3-1) on the LQ lines
    q = dict(VB1=[], VB094=[], four=[], low=[], high=[], outside=[], late_min=[])
    lq_all = []
    for (st, cen), pts in cells.items():
        for (j, frl, ln, lab, key) in pts:
            if not (lab and "-LQ-" in lab):
                continue
            lq_all.append(frl)
            gap = None
            t_min, t_end = val(ln, "diag.summary.t_RL_min_s"), val(ln, "las.end_t_s")
            if num(t_min) and num(t_end):
                gap = t_min - (t_end + 0.1)
            rec = dict(label=lab, key=key, F_RL_kN=frl, gap_s=gap)
            if st == "VB" and str(cen) == "1":
                q["VB1"].append(rec)
            elif st == "VB" and str(cen) == "0.94":
                q["VB094"].append(rec)
            else:
                q["four"].append(rec)
                if num(frl) and t_in(frl, 12.2, 13.5) and gap is not None and t_le(gap, 0.05):
                    q["low"].append(rec)
                elif num(frl) and t_in(frl, 14.0, 16.0):
                    q["high"].append(rec)
                else:
                    q["outside"].append(rec)
            if gap is not None and t_gt(gap, 0.05):
                q["late_min"].append(rec)
    qres = dict(
        Q1=(all(num(r["F_RL_kN"]) and t_in(r["F_RL_kN"], 14.13, 14.17) for r in q["VB1"]) and
            all(num(r["F_RL_kN"]) and t_in(r["F_RL_kN"], 14.61, 14.64) for r in q["VB094"])) if (q["VB1"] or q["VB094"]) else None,
        Q2=(q["outside"] == []) if q["four"] else None,
        Q3=(6 <= len(q["low"]) <= 20) if q["four"] else None,
        Q4=all(num(r["F_RL_kN"]) and t_ge(r["F_RL_kN"], 14.0) for r in q["late_min"]) if lq_all else None,
        Q5=(t_in(min(v for v in lq_all if num(v)), 12.2, 12.7) and all(num(v) and t_ge(v, 12.0) for v in lq_all)) if any(num(v) for v in lq_all) else None,
        detail=q)
    res["records"]["Q"] = qres
    # M-1..M-3 vs stored P5 (R-G + R-H 54 pairs)
    dF = []
    m3 = []
    branch_a = {("V0", "0.94", 1), ("V0", "0.94", 3), ("V0", "1", 0), ("V0", "1", 2), ("V0", "1", 4), ("V0", "nom", 3)}
    for (key, label), ln in cand_lines.items():
        if not (label and ("-LT-" in label or "-LH-" in label)):
            continue
        p5 = p5_pairs.get((key, label.replace("P5r4-", "P5-", 1)))
        if p5 is None:
            continue
        a, b = val(ln, "diag.summary.F_RL_kN"), val(p5, "diag.summary.F_RL_kN")
        if num(a) and num(b):
            dF.append(a - b)
            if "-LT-" in label and (setting_of(ln), str(val(ln, "diag.touch_budget.centre")), val(ln, "diag.touch_budget.j")) in branch_a:
                m3.append(a - b)
    max_rc = max([v["R_c"] for v in g2.values() if num(v["R_c"])], default=None)
    res["records"]["M"] = dict(n_pairs=len(dF), M1_median_dF=(statistics.median(dF) if dF else None),
                               M1=t_gt(statistics.median(dF), 0.0) if dF else None,
                               M2_max_R_c=max_rc, M2=t_lt(max_rc, M2_P5_MAX_RANGE_KN) if num(max_rc) else None,
                               M3_dF=m3, M3=(sum(1 for x in m3 if t_gt(x, 0.0)) >= 4) if len(m3) == 6 else None)
    return res


# ----------------------------------------------------------------------------- main recount

def load_baselines(v5_dir, k, files_read):
    base = {}
    for name, (rel, want) in BASE_FILES.items():
        path = os.path.join(v5_dir, *rel.split("/"))
        if not os.path.isfile(path):
            base[name] = None
            k.setdefault("K-9", []).append(dict(row=name, item="baseline_file_present", ok=False, got=path))
            continue
        got = sha256_file(path)
        files_read[os.path.abspath(path)] = got
        k.setdefault("K-9", []).append(dict(row=name, item="baseline_file_sha", ok=(got == want), got=got, want=want))
        base[name] = read_jsonl(path)
    return base


def by_key(lines, keyfun, pred=lambda ln: True):
    out = {}
    for ln in lines or []:
        if "error" in ln or not pred(ln):
            continue
        out.setdefault(keyfun(ln), []).append(ln)
    return out


def find_bundle_file(run_dir, bundle, explicit):
    if bundle in explicit:
        return explicit[bundle]
    cands = []
    for nm in (f"p5k_{bundle}.jsonl", f"p5k_{bundle.replace('-', '')}.jsonl", f"p5k_{bundle.replace('-', '_')}.jsonl"):
        p = os.path.join(run_dir, nm)
        if os.path.isfile(p) and p not in cands:
            cands.append(p)
    if len(cands) > 1:
        raise RuntimeError(f"bundle {bundle}: more than one file {cands}")
    return cands[0] if cands else None


def recount(run_dir, v5_dir, rules_path, rules_rev1_path, rules_rev2_path, rules_rev3_path, explicit=None, gs_dir=None):
    explicit = explicit or {}
    files_read = {}
    K = {}

    def kadd(kname, row, item, ok, got=None, want=None):
        K.setdefault(kname, []).append(dict(row=row, item=item, ok=ok, got=got, want=want))

    # ---- K-0 rules
    for path, want, label in ((rules_path, RULES_SHA, "rules"), (rules_rev1_path, RULES_REV1_SHA, "rules_rev1"),
                              (rules_rev2_path, RULES_REV2_SHA, "rules_rev2"),
                              (rules_rev3_path, RULES_REV3_SHA, "rules_rev3")):
        got = sha256_file(path) if path and os.path.isfile(path) else None
        if got:
            files_read[os.path.abspath(path)] = got
        rec = None
        sp = os.path.splitext(path)[0] + ".sha256" if path else None
        if sp and os.path.isfile(sp):
            files_read[os.path.abspath(sp)] = sha256_file(sp)
            with open(sp, encoding="utf-8") as f:
                txt = f.read().strip()
            rec = txt.split()[0] if txt else None
        kadd("K-0", None, f"{label}_sha_eq_sha256_file", got is not None and got == rec, got=got, want=rec)
        kadd("K-0", None, f"{label}_sha_eq_constant", got == want, got=got, want=want)

    base = load_baselines(v5_dir, K, files_read)

    def blines(name):
        return base.get(name) or []

    # ---- key lists (K-9, appendix A)
    lists = {}
    z0_keys = sorted({line_key(l) for l in blines("revA_R0") if "error" not in l})
    lists["Z-0"] = z0_keys
    za_keyset = sorted({za_key(l) for l in blines("revA_R0A") + blines("revA_RQ") if "error" not in l}, key=str)
    lists["Z-A"] = za_keyset
    zt_keys = sorted({line_key(l) for l in blines("revA_RT") if "error" not in l})
    lists["Z-T"] = zt_keys
    zs_keys = sorted({line_key(l) for l in blines("revA_RS") if "error" not in l})
    lists["Z-S"] = zs_keys
    zc_keys = sorted({line_key(l) for l in blines("s2d_SC") if "error" not in l})
    lists["Z-C"] = zc_keys
    for b, keys in (("Z-0", z0_keys), ("Z-T", zt_keys), ("Z-S", zs_keys), ("Z-C", zc_keys)):
        kadd("K-9", b, "key_list_sha", list_sha(keys) == LIST_SHA[b], got=list_sha(keys), want=LIST_SHA[b])
    za_unique = sorted({k for (k, _l) in za_keyset})
    kadd("K-9", "Z-A", "key_list_sha", list_sha(za_unique) == LIST_SHA["Z-A"], got=list_sha(za_unique), want=LIST_SHA["Z-A"])
    za_label_sha = list_sha([f"{k}\t{l}" for (k, l) in za_keyset])
    # Z-T ref baseline (las_T1 b0 + las_T2), keyed by las.key
    lt_lines = [l for l in blines("las_T1") if val(l, "las.candidate") == "b0"] + blines("las_T2")
    L_by = by_key(lt_lines, lambda l: val(l, "las.key"))
    kadd("K-9", "Z-T-ref-base", "las.key_list_eq_Z-T", list_sha(L_by.keys()) == LIST_SHA["Z-T"], got=list_sha(L_by.keys()))
    t1_keys = sorted({val(l, "las.key") for l in blines("las_T1") if val(l, "las.candidate") == "b0"})
    # Z-C ref baseline: Y-Pa (K1on, P0, no error) else s2d_SC
    ypa = by_key(blines("k1_YP"), line_key, lambda l: val(l, "k1.sub_bundle") == "Y-Pa" and
                 val(l, "las.candidate") == "P0" and val(l, "k1.k1_candidate") == "K1on")
    kadd("K-9", "Y-Pa", "key_list_sha", list_sha(ypa.keys()) == LIST_SHA["Y-Pa"], got=list_sha(ypa.keys()))
    yp_errors = [dict(lineno=l.get("__lineno__"), key=line_key(l)) for l in blines("k1_YP") if "error" in l]
    for kk, ls in ypa.items():
        if len(ls) != 1:
            kadd("K-9", f"Y-Pa:{kk}", "exactly_one_normal_line", False, got=len(ls))
    rs_keys = set(zs_keys)
    zc_out = sorted(set(zc_keys) - rs_keys)
    kadd("K-9", "Z-C-out", "key_list_sha", list_sha(zc_out) == LIST_SHA["Z-C-out"], got=list_sha(zc_out))

    expect_hash = {
        ("Z-0", "ref"): {k: ls[0].get("commands_sha256") for k, ls in by_key(blines("revA_R0"), line_key).items()},
        ("Z-A", "cand"): {k: ls[0].get("commands_sha256") for k, ls in by_key(blines("revA_R0A") + blines("revA_RQ"), za_key).items()},
        ("Z-T", "ref"): {k: ls[0].get("commands_sha256") for k, ls in L_by.items()},
        ("Z-T", "cand"): {k: ls[0].get("commands_sha256") for k, ls in by_key(blines("revA_RT"), line_key).items()},
        ("Z-S", "ref"): {k: ls[0].get("commands_sha256") for k, ls in by_key(blines("k1_YS"), line_key, lambda l: val(l, "k1.sub_bundle") == "Y-Sa").items()},
        ("Z-S", "cand"): {k: ls[0].get("commands_sha256") for k, ls in by_key(blines("k1_YS"), line_key, lambda l: val(l, "k1.sub_bundle") == "Y-Sb").items()},
    }
    sc_by = by_key(blines("s2d_SC"), line_key)
    zc_ref = {}
    zc_ref_src = {}
    for kk in zc_keys:
        if kk in ypa and len(ypa[kk]) == 1:
            zc_ref[kk] = ypa[kk][0].get("commands_sha256")
            zc_ref_src[kk] = "k1_YP Y-Pa"
        elif kk in sc_by:
            zc_ref[kk] = sc_by[kk][0].get("commands_sha256")
            zc_ref_src[kk] = "s2d_SC"
    expect_hash[("Z-C", "ref")] = zc_ref
    for kk in ("Z-S",):
        for arm in ("ref", "cand"):
            kadd("K-9", f"{kk}-{arm}-base", "baseline_key_list_eq", list_sha(expect_hash[(kk, arm)].keys()) == LIST_SHA[kk])

    p5_pairs = {}
    for l in blines("rev_RG") + blines("revA_RH"):
        if "error" in l:
            continue
        lab = val(l, "rev.label") or ""
        if lab.startswith("P5-LT-") or lab.startswith("P5-LH-"):
            p5_pairs[(line_key(l), lab)] = l

    # ---- bundles
    bundles = {}
    lines_by_bundle = {}
    error_lines = {}
    for b in BUNDLES:
        path = find_bundle_file(run_dir, b, explicit) if run_dir else explicit.get(b)
        if path is None:
            bundles[b] = dict(status=None, file=None, present=False)
            continue
        files_read[os.path.abspath(path)] = sha256_file(path)
        lines = read_jsonl(path)
        keyfun = za_key if b == "Z-A" else line_key
        groups, errs, stray = group_lines(lines, BUNDLE_ARMS[b], keyfun)
        error_lines[b] = errs
        lines_by_bundle[b] = groups
        bundles[b] = dict(file=path, present=True, n_lines=len(lines), n_error_lines=len(errs),
                          error_lines=errs, stray_lines=stray)

    for b in BUNDLES:
        bd = bundles[b]
        if not bd["present"]:
            continue
        groups = lines_by_bundle[b]
        kl = lists.get(b)
        stop_r, und_r, fail_r = [], [], []
        if bd["stray_lines"]:
            stop_r.append(f"K-9: {len(bd['stray_lines'])} lines with an arm outside {BUNDLE_ARMS[b]}")
        dup = {f"{a}|{k}": len(v) for (a, k), v in groups.items() if len(v) > 1}
        if dup:
            stop_r.append(f"K-9 duplicate lines: {dup}")
        if b == "Z-X":
            allowed = set(zt_keys) | set(zs_keys) | set(zc_keys)
            outside = sorted(str(k) for (a, k) in groups if k not in allowed)
            missing_keys = []
        else:
            allowed = set(kl)
            outside = sorted(str(k) for (a, k) in groups if k not in allowed)
            missing_keys = sorted(f"{a}|{k}" for a in BUNDLE_ARMS[b] for k in kl if (a, k) not in groups)
        if outside:
            stop_r.append(f"K-9 keys outside list: {outside}")
        bd["missing_keys"] = missing_keys
        # rev2 RV2-8: errors_total = every error line (first attempts included); errors_left = (arm, key) without
        # any normal line (list bundles: the incomplete keys; Z-X: error-line keys with no normal line)
        bd["errors_total"] = bd["n_error_lines"]
        if b == "Z-X":
            err_keys = {e["key"] for e in bd["error_lines"]}
            bd["errors_left"] = sum(1 for k in err_keys if ("ref", k) not in groups)
        else:
            bd["errors_left"] = len(missing_keys)
        if missing_keys:
            und_r.append(f"incomplete: {len(missing_keys)} (arm,key) without a normal line")
        bd["key_list_sha_Z-A_labels"] = za_label_sha if b == "Z-A" else None
        # ---- per-line K checks, identity
        kl_items = {}
        heads = {}
        for (arm, key), ls in groups.items():
            for ln in ls:
                rid = f"{b}|{arm}|{key}"
                k_line_checks(ln, arm, kl_items, rid)
                p, ident = identity_of(ln)
                heads.setdefault(arm, set()).add(None if ident is None else ident.get("git_head"))
                if ident is None:
                    kl_items.setdefault("K-1", []).append(dict(row=rid, item="identity_present", ok=None, got="no identity block"))
                else:
                    kl_items.setdefault("K-1", []).append(dict(row=rid, item="code_diff_sha256_empty",
                                                               ok=ident.get("code_diff_sha256") == EMPTY_SHA,
                                                               got=ident.get("code_diff_sha256")))
        for arm, hs in heads.items():
            kl_items.setdefault("K-1", []).append(dict(row=f"{b}|{arm}", item="single_git_head", ok=(len(hs) == 1 and None not in hs),
                                                       got=sorted(map(str, hs))))
        bd["k_items"] = kl_items
        if b in ("Z-0", "Z-A", "Z-X"):
            bd["anchor_records"] = {f"{a}|{k if b != 'Z-A' else k[0] + '#' + str(k[1])}": anchor_record_harness(ls[0])
                                    for (a, k), ls in groups.items() if len(ls) == 1}
        for kname, items in kl_items.items():
            for it in items:
                if it["ok"] is False:
                    stop_r.append(f"{kname}:{it['item']}:{it['row']}")
        # ---- bit predictions
        bt = []
        for arm in BUNDLE_ARMS[b]:
            exp = expect_hash.get((b, arm))
            if exp is None:
                continue
            for (a, key), ls in groups.items():
                if a != arm or len(ls) != 1:
                    continue
                want = exp.get(key)
                got = ls[0].get("commands_sha256")
                bt.append(dict(arm=arm, key=key if b != "Z-A" else f"{key[0]}#{key[1]}", ok=(want is not None and got == want),
                               got=got, want=want))
        bd["bit_prediction"] = dict(n=len(bt), n_equal=sum(1 for x in bt if x["ok"]),
                                    mismatches=[x for x in bt if not x["ok"]])
        if bd["bit_prediction"]["mismatches"]:
            stop_r.append(f"bit prediction mismatch: {len(bd['bit_prediction']['mismatches'])}")
        bd["stop_reasons"], bd["undecidable_reasons"], bd["fail_reasons"] = stop_r, und_r, fail_r

    # ---- Z-A criteria
    if bundles["Z-A"]["present"]:
        bd = bundles["Z-A"]
        cand_lines = {k: ls[0] for (a, k), ls in lines_by_bundle["Z-A"].items() if a == "cand" and len(ls) == 1}
        za = za_criteria(cand_lines, p5_pairs, K)
        bd["criteria"] = za
        for kind, g in za["G1"].items():
            if not g["ok"]:
                bd["fail_reasons"].append(f"G-1{kind}: {len(g['violations'])}")
        if not za["G2p"]["ok"]:
            bd["fail_reasons"].append(f"G-2': {len(za['G2p']['violations'])}")
        for kind, g in za["G3"].items():
            if not g["ok"]:
                bd["undecidable_reasons"].append(f"G-3 {kind}: {len(g['bad'])}")
        if bd["n_error_lines"]:
            bd["undecidable_reasons"].append(f"G-3: error lines {bd['n_error_lines']}")
        for kname in ("K-A5", "K-A6", "K-A8", "K-A1", "K-A2", "K-A3", "K-A4"):
            if not za["KA"][kname]["ok"]:
                bd["stop_reasons"].append(f"{kname}: {len(za['KA'][kname]['failures'])}")

    # ---- Z-0 has no criteria beyond BT-0 and K
    # ---- pair bundles
    zx_ref = {}
    if bundles["Z-X"]["present"]:
        zx_ref = {k: ls[0] for (a, k), ls in lines_by_bundle["Z-X"].items() if a == "ref" and len(ls) == 1}
    ref_hash_any = {}
    for b in ("Z-T", "Z-S", "Z-C"):
        if bundles[b]["present"]:
            for (a, k), ls in lines_by_bundle[b].items():
                if a == "ref" and len(ls) == 1:
                    ref_hash_any.setdefault(k, []).append((b, ls[0].get("commands_sha256")))
    if bundles["Z-X"]["present"]:
        # rev2 RV2-6: Z-X ref hash = the new ref hash of every bundle the key belongs to (Z-C overlaps Z-S on 19 keys)
        bx = []
        for k, ln in zx_ref.items():
            srcs = ref_hash_any.get(k) or []
            bx.append(dict(key=k, ok=(bool(srcs) and all(ln.get("commands_sha256") == h for (_b, h) in srcs)),
                           got=ln.get("commands_sha256"), want=[h for (_b, h) in srcs],
                           ref_bundles=[b for (b, _h) in srcs]))
        bundles["Z-X"]["bit_prediction"] = dict(n=len(bx), n_equal=sum(1 for x in bx if x["ok"]),
                                                mismatches=[x for x in bx if not x["ok"]], rule="BT-X")
        if bundles["Z-X"]["bit_prediction"]["mismatches"]:
            bundles["Z-X"]["stop_reasons"].append("BT-X mismatch")

    criteria_per_bundle = {}
    zx_candidates = []   # rev2 RV2-6: hash changed and READY dt > +1.0 s, over Z-T, Z-S, Z-C
    for b in ("Z-T", "Z-S", "Z-C"):
        bd = bundles[b]
        if not bd["present"]:
            continue
        groups = lines_by_bundle[b]
        pairs = {}
        for k in lists[b]:
            r, c = groups.get(("ref", k)), groups.get(("cand", k))
            if r and c and len(r) == 1 and len(c) == 1:
                pairs[k] = eval_pair(r[0], c[0], b)
        bd["pairs"] = pairs
        crit = {}

        def und_for(cname):
            return {k: p["undecidable_reasons"][cname] for k, p in pairs.items()
                    if cname in p["undecidable_reasons"]}

        def cstat(viol, und):
            if und:
                return "undecidable"
            return "fail" if viol else "pass"
        # C-2
        c2_list = {k: p["c2_violations"] for k, p in pairs.items() if p["c2_violations"]}
        u = und_for("C-2")
        crit["C-2"] = dict(status=cstat(c2_list, u), violations=c2_list, undecidable=u, n_pairs=len(pairs),
                           items_only={k: dict(ref=p["items_only_ref"], cand=p["items_only_cand"]) for k, p in pairs.items()
                                       if p["items_only_ref"] or p["items_only_cand"]})
        p3_list = {k: p["p3_violations"] for k, p in pairs.items() if p["p3_violations"]}
        u = und_for("P3")
        crit["P3"] = dict(status=cstat(p3_list, u), violations=p3_list, undecidable=u,
                          P3_baseline_false={k: p["p3_baseline_false"] for k, p in pairs.items() if p["p3_baseline_false"]},
                          n_not_applicable=sum(1 for p in pairs.values()
                                               if not p["p3_violations"] and not p["p3_baseline_false"]))
        cf_list = {k: p["cf"] for k, p in pairs.items() if p["cf"] and p["cf"]["violation"]}
        u = und_for("C-F")
        crit["C-F"] = dict(status=cstat(cf_list, u), violations=cf_list, undecidable=u,
                           n_in_scope=sum(1 for p in pairs.values() if p["cf"] and p["cf"]["in_scope"]),
                           ref_none=sorted(k for k, p in pairs.items() if p["cf"] and p["cf"].get("ref_none")))
        cs_vals = {k: p["cs"] for k, p in pairs.items() if p["cs"] is not None}
        cs_viol = {k: v for k, v in cs_vals.items() if v["violation"]}
        deltas = [v["delta_m"] for v in cs_vals.values() if num(v["delta_m"])]
        u = und_for("C-S")
        crit["C-S"] = dict(status=cstat(cs_viol, u), violations=cs_viol, undecidable=u, n=len(cs_vals),
                           ref_none=sorted(k for k, v in cs_vals.items() if v.get("ref_none")),
                           max_delta_m=max(deltas) if deltas else None, min_delta_m=min(deltas) if deltas else None)
        ck_viol = {k: p["ck1"] for k, p in pairs.items() if p["ck1"] and p["ck1"]["violation"]}
        u = und_for("CK-1")
        crit["CK-1"] = dict(status=cstat(ck_viol, u), violations=ck_viol, undecidable=u,
                            classes={cl: sorted(k for k, p in pairs.items() if p["ck1"] and p["ck1"]["cls"] == cl)
                                     for cl in ("R4_LOST", "R4_GAINED", "KEPT", "NONE")})
        u = und_for("PAIR_DIVERGE")
        if u:
            bd["undecidable_reasons"].append(f"PAIR_DIVERGE premise fields missing: {sorted(u)}")
        if b == "Z-T":
            c1 = {}
            c1_und = []
            for k in t1_keys:
                p = pairs.get(k)
                cl = groups.get(("cand", k))
                if p is None or not cl or not has(cl[0], "d1.F_judged_min_N"):
                    c1_und.append(k)
                    continue
                Fc = p["record"]["F_judged_min_N"][1]
                if not (num(Fc) and t_ge(Fc, F_LINE_N)):
                    c1[k] = Fc
            crit["C-1"] = dict(status="undecidable" if (c1_und or len(t1_keys) != 8) else ("fail" if c1 else "pass"),
                               violations=c1, keys=t1_keys, missing=c1_und)
            hr0 = [k for k in lists[b] if group_token(k) == "H-R-0"]
            a3 = {k: [pairs[k]["hash_equal"]] for k in hr0 if k in pairs and not pairs[k]["hash_equal"]}
            crit["A-3"] = dict(status="undecidable" if (len(hr0) != 48 or any(k not in pairs for k in hr0)) else ("fail" if a3 else "pass"),
                               n_keys=len(hr0), violations=sorted(a3))
        # R-1 / R-2 with C-4 exception
        changed = {k: p for k, p in pairs.items() if not p["hash_equal"]}
        pop, exc, no_ready = {}, {}, []
        exc_detail = {}
        for k, p in changed.items():
            dt = p["ready"]["dt_s"]
            if dt is None:
                no_ready.append(k)
                continue
            is_exc = False
            det = None
            if t_gt(dt, R1_MEDIAN_S):   # rev3 T-7
                zx_candidates.append(dict(bundle=b, key=k, dt_s=dt))
                det = c4_exception(groups[("cand", k)][0], zx_ref.get(k), groups[("ref", k)][0], dt)
                is_exc = det["exception"]
                exc_detail[k] = det
            if is_exc:
                exc[k] = dt
            else:
                pop[k] = dt
        r_und = und_for("R-1/R-2")
        if r_und:
            r_status = "undecidable"
            r_note = "fields missing"
        elif not changed:
            r_status = "pass"
            r_note = f"hash identical {len(pairs)}/{len(pairs)}"
        elif not pop:
            r_status = "undecidable"
            r_note = "changed pairs exist but population empty"
        else:
            med, mx = statistics.median(pop.values()), max(pop.values())
            r_status = "pass" if (t_le(med, R1_MEDIAN_S) and t_le(mx, R2_MAX_S)) else "fail"
            r_note = None
        vals = list(pop.values())
        crit["R-1/R-2"] = dict(status=r_status, judged=(b in ("Z-T", "Z-C")), note=r_note,
                               n_changed=len(changed), n_population=len(pop), population=pop,
                               exceptions=exc, exception_detail=exc_detail, changed_without_ready=sorted(no_ready),
                               median_s=statistics.median(vals) if vals else None, max_s=max(vals) if vals else None,
                               min_s=min(vals) if vals else None,
                               S8_ask=(len(exc) > S8_MAX_EXCEPTIONS or any(t_gt(v, S8_MAX_DT_S) for v in exc.values())))
        if b == "Z-S":
            crit["R-1/R-2"]["status_record_only"] = crit["R-1/R-2"]["status"]
            crit["R-1/R-2"]["status"] = None
        # PAIR_DIVERGE / PAIR_CMD_DIFF / K-A7, K-A8 (K-5 above)
        div = sorted(k for k, p in pairs.items() if p["PAIR_DIVERGE"])
        crit["PAIR_DIVERGE"] = dict(keys=div, n=len(div))
        crit["PAIR_CMD_DIFF"] = dict(keys=sorted(k for k, p in pairs.items() if p["PAIR_CMD_DIFF"]),
                                     n=sum(1 for p in pairs.values() if p["PAIR_CMD_DIFF"]))
        if div:
            bd["stop_reasons"].append(f"PAIR_DIVERGE: {div}")
        crit["S5_c2_pairs_ge_5"] = len(c2_list) >= 5
        # flags / records
        flags = dict(
            R4_GAINED=crit["CK-1"]["classes"]["R4_GAINED"],
            THIN_MARGIN=sorted(k for k, p in pairs.items() if p["ck1"] and p["ck1"]["THIN_MARGIN"]),
            ANCHOR_SAMPLE_SHIFT=sorted(k for k, p in pairs.items() if p["anchor"]["flag"] is True),
            ANCHOR_RECORD_MISSING=sorted(k for k, p in pairs.items() if p["anchor"]["flag"] is None),
            ready_source_disagree=sorted(k for k, p in pairs.items() if p["ready"]["source_agree"] is False),
        )
        viol_keys = set(cs_viol) | set(p3_list)
        flags["anchor_effect_possible"] = sorted(k for k in viol_keys if pairs[k]["anchor"]["flag"] is True)
        flags["anchor_effect_unknown"] = sorted(k for k in viol_keys if pairs[k]["anchor"]["flag"] is None)
        crit["flags"] = flags
        if b == "Z-C":
            ins = set(zs_keys)
            def split(dct):
                return dict(in_sample=sorted(k for k in dct if k in ins), out_of_sample=sorted(k for k in dct if k not in ins))
            crit["sample_split"] = {name: split(crit[name]["violations"]) for name in ("C-2", "P3", "C-F", "C-S", "CK-1")}
            crit["sample_split"]["n_in"] = sum(1 for k in pairs if k in ins)
            crit["sample_split"]["n_out"] = sum(1 for k in pairs if k not in ins)
        for name in ("C-2", "P3", "C-F", "C-S", "CK-1", "C-1", "A-3", "R-1/R-2"):
            if name not in crit or crit[name]["status"] is None:
                continue
            st = crit[name]["status"]
            if st == "fail":
                bd["fail_reasons"].append(name)
            elif st == "undecidable":
                bd["undecidable_reasons"].append(name)
        criteria_per_bundle[b] = crit
        bd["criteria"] = crit

    # ---- G-S same-key hash check (16.2)
    if gs_dir:
        gs = {}
        for b in BUNDLES:
            path = find_bundle_file(gs_dir, b, {})
            if not path or not bundles[b]["present"]:
                continue
            files_read[os.path.abspath(path)] = sha256_file(path)
            keyfun = za_key if b == "Z-A" else line_key
            g, errs, _s = group_lines(read_jsonl(path), BUNDLE_ARMS[b], keyfun)
            res = []
            for (a, k), ls in g.items():
                main = lines_by_bundle[b].get((a, k))
                if main and len(main) == 1 and len(ls) == 1:
                    res.append(dict(arm=a, key=str(k), same=(ls[0].get("commands_sha256") == main[0].get("commands_sha256"))))
            gs[b] = dict(n=len(res), differ=[r for r in res if not r["same"]], error_lines=len(errs))
            if gs[b]["differ"]:
                bundles[b]["stop_reasons"].append("G-S same-key hash differs")
        bundles["_G-S"] = gs

    # ---- statuses (8.1 + 16.6)
    order_prev_fail = False
    for b in BUNDLES:
        bd = bundles[b]
        if not bd["present"]:
            if b == "Z-X":
                bd["status"] = "not_run"
            else:
                bd["status"] = "not_run" if order_prev_fail else "incomplete"
            continue
        st = "pass"
        if bd["fail_reasons"]:
            st = "fail"
        if bd["undecidable_reasons"]:
            st = "undecidable"
        if bd["stop_reasons"]:
            st = "stop"
        bd["status"] = st
        if st == "fail":
            order_prev_fail = True
    harness_status = combine([bundles[b]["status"] for b in BUNDLES])
    global_k = {kname: dict(items=items, ok=all(i["ok"] is not False for i in items)) for kname, items in K.items()}
    if any(not v["ok"] for v in global_k.values()):
        harness_status = "stop"

    out = dict(
        tool=TOOL_NAME, tool_version=TOOL_VERSION, tool_sha256=sha256_file(os.path.abspath(__file__)),
        taken_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        rules_sha256=RULES_SHA, rules_rev1_sha256=RULES_REV1_SHA,
        grade_provisional=harness_status, k10=None,
        global_k=global_k,
        error_lines_total=sum(len(v) for v in error_lines.values()),
        error_lines_by_bundle={b: len(v) for b, v in error_lines.items()},
        errors_total=sum(bundles[b].get("errors_total", 0) for b in BUNDLES),
        errors_left=sum(bundles[b].get("errors_left", 0) for b in BUNDLES),
        errors_by_bundle={b: dict(errors_total=bundles[b].get("errors_total"), errors_left=bundles[b].get("errors_left"))
                          for b in BUNDLES},
        zx_candidates=dict(keys=zx_candidates, n_unique_keys=len({c["key"] for c in zx_candidates}),
                           ask_more_than_10=len({c["key"] for c in zx_candidates}) > 10),
        rules_rev2_sha256=RULES_REV2_SHA, rules_rev3_sha256=RULES_REV3_SHA,
        bundles={b: {kk: vv for kk, vv in bundles[b].items()} for b in bundles},
        lists=dict(Z_A_label_list_sha=za_label_sha, Z_C_out_of_sample_n=len(zc_out), Y_P_error_lines=yp_errors,
                   Z_C_ref_source_counts={s: sum(1 for v in zc_ref_src.values() if v == s) for s in set(zc_ref_src.values())}),
        files_read_sha256=files_read,
        truncated=False,
    )
    return out


def c4_exception(cand, zx, ref_new, dt):
    """las_rev_targeted_rules 6 + revA 6 (ramp end condition)."""
    det = dict(exception=False, dt_s=dt, reason=None)
    if zx is None:
        det["reason"] = "no Z-X ref line"
        return det
    if zx.get("commands_sha256") != ref_new.get("commands_sha256"):
        det["reason"] = "Z-X hash != ref hash"
        return det
    dcc, dcr = cand.get("done_clock"), zx.get("done_clock")
    if not isinstance(dcc, dict) or not isinstance(dcr, dict):
        det["reason"] = "done_clock missing"
        return det
    lc, lr = dcc.get("loss_s"), dcr.get("loss_s")
    if not (num(lc) and num(lr)):
        det["reason"] = "loss_s not numeric"
        return det
    E = lc - lr
    det.update(loss_cand_s=lc, loss_ref_s=lr, E_s=E, E_over_dt=E / dt)
    if not t_ge(E, C4_RATIO * dt):   # rev3 T-8 (threshold computed first)
        det["reason"] = "E < 0.8 dt"
        return det
    starts = dcc.get("clock_starts_s") or []
    resets = [r for r in (dcc.get("resets") or []) if isinstance(r, dict)]
    if starts:
        c1, cm = starts[0], starts[-1]
        in_l = [r for r in resets if num(r.get("t_s")) and per(c1) <= per(r["t_s"]) <= per(cm)]   # rev3 W-3
    else:
        in_l = []
    te = val(cand, "las.ramp.end_t_s")
    if te is None:
        te = val(cand, "las.end_t_s")
    if te is None:
        det["reason"] = "LAS-b / ramp end time missing"
        return det
    late = all(per(r["t_s"]) > per(te) for r in in_l)
    det.update(resets_in_loss=in_l, end_t_s=te)
    if not late:
        det["reason"] = "a reset is not after the LAS-b / ramp end"
        return det
    det["exception"] = True
    det["reason"] = "exception"
    return det


EXIT = {"pass": 0, "fail": 1, "undecidable": 1, "stop": 2}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", help="folder with p5k_<bundle>.jsonl")
    ap.add_argument("--bundle", action="append", default=[], help="explicit BUNDLE=path (e.g. Z-0=path)")
    ap.add_argument("--v5-dir", required=True, help="06_analysis/03_hydraulic/coupled/v5 (baselines)")
    ap.add_argument("--rules", required=True)
    ap.add_argument("--rules-rev1", required=True)
    ap.add_argument("--rules-rev2", required=True)
    ap.add_argument("--rules-rev3", required=True)
    ap.add_argument("--gs-dir", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        explicit = {}
        for s in a.bundle:
            k, v = s.split("=", 1)
            explicit[k] = v
        res = recount(a.run_dir, a.v5_dir, a.rules, a.rules_rev1, a.rules_rev2, a.rules_rev3, explicit, a.gs_dir)
    except Exception:
        traceback.print_exc()
        print(json.dumps(dict(status="tool_error")))
        return 3
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, sort_keys=True, default=str)
    g = res["grade_provisional"]
    print("PROVISIONAL grade (K-10 decided outside):", g)
    print(json.dumps(dict(status=g, errors_total=res["errors_total"], errors_left=res["errors_left"],
                          bundles={b: res["bundles"][b].get("status") for b in BUNDLES}, out=a.out)))
    return EXIT.get(g, 1)


if __name__ == "__main__":
    sys.exit(main())
