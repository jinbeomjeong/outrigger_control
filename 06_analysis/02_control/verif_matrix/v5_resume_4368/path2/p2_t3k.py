"""Path-2 recount of H-0 T-3K (436.8 stage 0): R-0 K-2, R-0K K-1K / K-2K, T-3K K-1 / K-3 / K-4 / K-5 / K-6 / K-7.

Rules: ``las_targeted_rules.md`` (00b48fd8...) and its addenda rev1, rev2, rev3 (+ key list rev3_keys), rev4,
rev4a, rev4b, rev4c, rev5 (+ R-0K key list) - eleven sealed files (rev5 1 #5), read through the 436.8 rules
(5.1 H-0 "rev5 그대로", S-14) and rev3 (dad8dfa6...) R3-D1 (dg3 key / folder from the record), R3-D2 (R-0 V0
tag absent or null), R3-D3 (K-0 from .identity.json; H-T3-0 pre-run gate not two-path), R3-D4 (1e-9 tolerance); rev4 (7ea87a30...) R4-C4 superseded by rev6 (809e5639...) R6-C2 (K-0 from run_identity git / threads / rules_seals and the
outputs' own line identity); rev7 (e81f7d31...) R7-3b (line identity names: header ``header.identity``, lines
``t3.identity`` with ``git_head`` / ``sha256`` (six tool files) / ``c2_sha256`` / ``threads`` / ``workers`` /
``affinity`` and the mirrors ``t3.commit`` / ``t3.workers`` / ``t3.affinity_hex``; a format difference is S-11)
and R7-1c (a line with ``t3.las`` = ``t3.gate`` = ``"off"`` and no tag key reads ``final_C4G2`` for key presence
and version only; K-2 / H-T3-3 keep the recorded key, R3-D2). Author: dynamics-expert (path 2, second author). Path-1 tools (``las_judge``,
``las_h7``, ``las_t3*`` judging parts) and their outputs were not opened (436.8 9.2).

Definitions used (rule sentences; the line fields are the stored ``v5/d1.jsonl`` names):
  active      rev3 3: an ``INFO_LIFTOFF_SLOW`` start event (not ``_END``) in the line's events
              (``event_names`` count, else ``events`` [t, name])
  would_block rev5 2.1: ``slope_clearance_margin.order_gate.decisions[*].would_block``; ``would_block_any``
  B(k)        rev5 3.1: R-0K line for the 45 R-0K keys, else the rev3 key-list values (checked against
              ``v5/d1.jsonl`` when given, rev4a 1); dg3: key-list ``shadow_commands_sha256_all_folders``
  K-6a~e      rev3 3 table with rev4a 1-2 (``G6-2_loc``; item absent in the baseline = not applicable;
              baseline true + new None = violation)

Stops (rev5 4 order, S-11 of rev7 after H-T3-0): H-T3-0 -> S-11 -> H-T3-3 -> H-T3-2 -> H-T3-1 -> H-T3-1K ->
H-T3-1Q -> H-T3-4 -> H-T3-5 -> H-T3-6.
Exit codes (rev3 / rev5): 0 pass, 1 a criteria fail (H-T3-1K, H-T3-5, H-T3-6 class), 2 a stop without
judgement (H-T3-0, S-11, H-T3-1, H-T3-1Q, H-T3-2, H-T3-3, H-T3-4) or a rules sha mismatch, 3 tool error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p2_4368_core", _HERE / "p2_4368.py")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

TOOL_NAME = "p2_t3k.py"
TOOL_VERSION = "1"
_VM = "06_analysis/02_control/verif_matrix/"
LAS_RULES = {  # the eleven sealed files of rev5 1 #5 (436.8 appendix A gives the same sha for the rule texts)
    _VM + "las_targeted_rules.md": "00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40",
    _VM + "las_targeted_rules_rev1.md": "0d5f59f8e4a09448b93e0cde42adb7d23c2f99f6b365809876efaa6212d27625",
    _VM + "las_targeted_rules_rev2.md": "6be736cb98cea34e4a606606b4009668bbc1470c8a7db23b6a119ef033c97960",
    _VM + "las_targeted_rules_rev3.md": "956f65c74e36eb8fe921dc6399b0d5f2f04099b7852380362351f658c9791cd1",
    _VM + "las_targeted_rules_rev3_keys.json": "3602438d047b6a35829bda013921972411d10b0906153eba8bdc9760e7888553",
    _VM + "las_targeted_rules_rev4.md": "05fbde22009c10b74ddf0df071452a99631bb319c2f482df83be59adfad1de6d",
    _VM + "las_targeted_rules_rev4a.md": "3cbbfb5d8afda9075bf9631accf1b8bee4c1ee02edafa34a7869091175a73b15",
    _VM + "las_targeted_rules_rev4b.md": "add921e4978ef16abcc22dfc88dc25e51a770dc98d2d540526f48cf6ea7a6f3f",
    _VM + "las_targeted_rules_rev4c.md": "7e45993f667382f56aeb1b72bb5e7023ecfe3048a3723ac050cefc3b2a721417",
    _VM + "las_targeted_rules_rev5.md": "879d0e4d715b2e9f4e51257863fc259ccfe48105ca019299547d58dca24949b2",
}
R0K_KEYS_REL = _VM + "las_targeted_rules_rev5_r0k_keys.json"   # sha in its .sha256 (rev5 header: two lines)
R0K_LIST_SHA = "9399c4922828973fe5129c6c5964dc2cf6c53137a8858d1f92e69f9c85452e3c"  # rev5 2.3
REV3_KEYS_REL = _VM + "las_targeted_rules_rev3_keys.json"
D1_SHA = "9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f"

EV_LAS = "INFO_LIFTOFF_SLOW"
EV_FLAT = "INFO_LOC_FLAT_SOIL_MARGIN"
TAGS = {"R-0": {"V0": None, "VB": "final_C4G2_P3"},
        "R-0K": {"V0": "final_C4G2_K1", "VB": "final_C4G2_P3_K1"},
        "T-3K": {"V0": "final_C4G2_LAS_K1", "VB": "final_C4G2_P3_LAS_K1"}}
COUNTS = {"R-0": 7, "R-0K": 45, "T-3a": 228, "T-3b": 4, "T-3c": 76}
READY_ADD_S = 5.0    # K-6d (C5)
STROKE_ADD_M = 0.001  # K-6e (C5)
FLAT_SOIL_MARGIN_M = 0.03
LAS_B0 = core.LAS_PRESET    # b0 = preset values (spec 436 settings table)


def sha_lf(path):
    b = Path(path).read_bytes()
    return hashlib.sha256(b).hexdigest(), hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def check_las_seals(repo):
    """Eleven sealed files (rev5 1 #5). The rev3 key list and the R-0K list are data; LF normalisation per
    436.8 R2-9 is allowed for files that are not '-text' protected (recorded as eol_only)."""
    out, ok = {}, True
    want = dict(LAS_RULES)
    seal = repo / (R0K_KEYS_REL.rsplit(".", 1)[0].replace("_r0k_keys", "") + ".sha256")
    r0k_want = None
    if seal.is_file():
        for line in seal.read_text("utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].endswith("las_targeted_rules_rev5_r0k_keys.json"):
                r0k_want = parts[0].lower()
    want[R0K_KEYS_REL] = r0k_want
    for rel, w in want.items():
        p = repo / rel
        if not p.is_file() or w is None:
            out[rel] = {"ok": False, "why": "missing file or seal value"}
            ok = False
            continue
        raw, lf = sha_lf(p)
        item = {"sha256": raw, "want": w, "ok": raw == w}
        if raw != w and lf == w:
            item.update(ok=True, eol_only=True, sha256_lf=lf, note="CRLF 변환만 다름")
        out[rel] = item
        ok &= item["ok"]
    return ok, out


# ----------------------------------------------------------------- line access
def line_tag(ln):
    """The recorded tag (None if the key is absent or null). K-2 / H-T3-3 use this value (rev3 R3-D2)."""
    v, _ = core.first_path(ln, core.TAG_PATHS)
    return None if v is core.MISSING else v


ALL_OFF_TAG = "final_C4G2"    # rev7 R7-1c: LAS-b and K1 gate off preset


def read_tag(ln):
    """rev7 R7-1c reading for key presence and version (4.1) only: the recorded tag if there is one, else
    ``final_C4G2`` on a line with ``t3.las`` = ``t3.gate`` = ``"off"`` (not a missing key), else None
    (missing key, S-11). (tag, source)."""
    t = line_tag(ln)
    if t is not None:
        return t, "record"
    if core.dig(ln, "t3.las", None) == "off" and core.dig(ln, "t3.gate", None) == "off":
        return ALL_OFF_TAG, "R7-1c all-off"
    return None, "missing"


# version each bundle line must read as (4.1 one version per bundle; R-0 V0 by R7-1c)
VERSION_READ = {"R-0": {"V0": ALL_OFF_TAG, "VB": "final_C4G2_P3"},
                "R-0K": {"V0": "final_C4G2_K1", "VB": "final_C4G2_P3_K1"},
                "T-3K": {"V0": "final_C4G2_LAS_K1", "VB": "final_C4G2_P3_LAS_K1"}}


def event_names(ln):
    """Dict name -> count from ``event_names``; else counted from ``events`` [[t, name], ...]; None if neither."""
    en = ln.get("event_names")
    if isinstance(en, dict):
        return en
    ev = ln.get("events")
    if isinstance(ev, list):
        d = {}
        for e in ev:
            name = e[1] if isinstance(e, (list, tuple)) and len(e) == 2 else (e.get("name") if isinstance(e, dict) else None)
            if isinstance(name, str):
                d[name] = d.get(name, 0) + 1
        return d
    return None


def count_base(names, base):
    if names is None:
        return None
    return sum(int(c) for n, c in names.items() if isinstance(n, str) and n.split(":", 1)[0] == base)


def is_active(ln):
    return count_base(event_names(ln), EV_LAS) or 0


def fault_set(names):
    return None if names is None else {n for n in names if isinstance(n, str) and n.startswith("FAULT")}


def decisions_of(ln):
    v, _ = core.first_path(ln, ("resume_k1.slope_clearance_margin.order_gate.decisions",
                                "controller_meta.slope_clearance_margin.order_gate.decisions",
                                "slope_clearance_margin.order_gate.decisions"))
    return None if v is core.MISSING else v


def would_block_any(ln):
    d = decisions_of(ln)
    if not isinstance(d, list):
        return None
    return any(isinstance(x, dict) and x.get("would_block") is True for x in d)


def d1_block(ln):
    return ln.get("d1") if isinstance(ln.get("d1"), dict) else {}


def d1_key(ln):
    k = d1_block(ln).get("key")
    if isinstance(k, str):
        return k
    job = ln.get("job") or {}
    rk = core.dig(job, "d1.key", None)
    if isinstance(rk, str):
        eps = job.get("eps", 0.0)
        e = "0" if not eps else repr(float(eps))
        return f"{rk}|{job.get('setting')}|e{e}"
    return None


def baseline_of_line(ln):
    """B(k) values from a line (R-0K line or a stored d1.jsonl line)."""
    b = d1_block(ln)
    items = b.get("items") if isinstance(b.get("items"), dict) else {}
    return {"commands_sha256": ln.get("commands_sha256"), "verdict": b.get("verdict"),
            "fail_items": b.get("fail_items"), "P3-2": items.get("P3-2", core.MISSING),
            "G6-2_loc": items.get("G6-2_loc", core.MISSING), "t_ready_s": core.num(b.get("t_ready_s")),
            "stroke_max_m": core.num(b.get("stroke_max_m")), "faults": fault_set(event_names(ln))}


def baseline_of_keylist(e):
    """B(k) from a rev3 key-list entry (its G6-2 field is void, rev4a 1: G6-2_loc comes from d1.jsonl)."""
    return {"commands_sha256": e.get("commands_sha256"), "verdict": e.get("verdict"), "fail_items": e.get("fail_items"),
            "P3-2": e["P3-2"] if e.get("P3-2") is not None else core.MISSING, "G6-2_loc": core.MISSING,
            "t_ready_s": core.num(e.get("t_ready_s")), "stroke_max_m": core.num(e.get("stroke_max_m")),
            "faults": set(e["fault_names"]) if isinstance(e.get("fault_names"), list) else None}


# ----------------------------------------------------------------- K-6
def k6(new, base):
    """K-6a~e violations of one active D-1 line against B(k) (rev3 3, rev4a 2). [] = pass."""
    v = []
    nv, bv = new["verdict"], base["verdict"]
    if bv in ("pass", "allowed_stop") and nv == "fail":
        v.append(("K-6a", f"{bv} -> fail"))
    elif bv == "fail":
        nf, bf = new.get("fail_items"), base.get("fail_items")
        if not isinstance(nf, list) or not isinstance(bf, list) or not set(nf) <= set(bf):
            v.append(("K-6a", f"fail_items {nf} not within {bf}"))
    elif nv is None or bv is None:
        v.append(("K-6a", f"verdict missing (new {nv!r}, base {bv!r})"))
    for item in ("P3-2", "G6-2_loc"):
        b = base[item]
        if b is core.MISSING:
            continue                     # baseline has no item: not applicable (rev4a 2)
        if b is True and new[item] is not True:
            v.append(("K-6b", f"{item} true -> {new[item] if new[item] is not core.MISSING else None!r}"))
    nfz, bfz = new.get("faults"), base.get("faults")
    if nfz is None or bfz is None:
        v.append(("K-6c", "event_names missing"))
    elif not nfz <= bfz:
        v.append(("K-6c", f"new FAULT {sorted(nfz - bfz)}"))
    rb, rn = base["t_ready_s"], new["t_ready_s"]
    if rb is not None and rn is None:
        v.append(("K-6d", "READY lost"))
    elif rb is not None and rn is not None and core.t_gt(rn - rb, READY_ADD_S):
        v.append(("K-6d", f"READY +{rn - rb:.3f} s"))
    sb, sn = base["stroke_max_m"], new["stroke_max_m"]
    if sb is None or sn is None:
        v.append(("K-6e", "stroke_max_m missing"))
    elif core.t_gt(sn - sb, STROKE_ADD_M):
        v.append(("K-6e", f"stroke +{(sn - sb) * 1000:.3f} mm"))
    return v


def config_check(ln, bundle):
    """rev5 2.2: LAS-b state (b0 values for T-3K, off for R-0 / R-0K), gate value, R4c30 enable / 0.03 m."""
    rk = ln.get("resume_k1") if isinstance(ln.get("resume_k1"), dict) else None
    if rk is None:
        return ["resume_k1 block missing (config not checkable)"]
    bad = []
    las = rk.get("liftoff_approach_slow")
    st = las.get("settings") if isinstance(las, dict) else None
    if bundle == "T-3K":
        if not isinstance(st, dict):
            bad.append("LAS-b settings missing")
        else:
            for k, want in LAS_B0.items():
                if not core.same_value(st.get(k), want):
                    bad.append(f"LAS-b {k} {st.get(k)!r} != {want!r}")
    else:
        if isinstance(st, dict) and st.get("enable") is not False:
            bad.append(f"LAS-b enable {st.get('enable')!r} (off expected)")
    gate_on = bundle != "R-0"
    if rk.get("k1_order_gate_effective") is not gate_on:
        bad.append(f"k1_order_gate_effective {rk.get('k1_order_gate_effective')!r} (want {gate_on})")
    scm = rk.get("slope_clearance_margin") if isinstance(rk.get("slope_clearance_margin"), dict) else {}
    s = scm.get("settings") if isinstance(scm.get("settings"), dict) else scm
    if s.get("enable") is not True:
        bad.append(f"slope_clearance_margin.enable {s.get('enable')!r}")
    if not core.same_value(s.get("flat_soil_margin_m"), FLAT_SOIL_MARGIN_M):
        bad.append(f"flat_soil_margin_m {s.get('flat_soil_margin_m')!r}")
    if s.get("flat_soil_margin_order_gate") is not gate_on and "flat_soil_margin_order_gate" in s:
        bad.append(f"flat_soil_margin_order_gate {s.get('flat_soil_margin_order_gate')!r}")
    return bad


def tag_presence(ln, bundle, setting, fnd, where, tally):
    """rev7 R7-1c key presence and version reading of one line. A missing key on a line that is not all-off
    is S-11. The read version is compared with VERSION_READ (a mismatch there is already an H-T3-3 of
    ``tag_ok`` on the recorded value, so only recorded here)."""
    t, src = read_tag(ln)
    tally[src] = tally.get(src, 0) + 1
    if t is None:
        fnd.stop("S-11", where, "controller_tag missing on a line that is not t3.las = t3.gate = off (R7-1c)")
    elif t != VERSION_READ[bundle][setting]:
        tally.setdefault("version_differs", []).append(where)
    return t, src


def tag_ok(tag, bundle, setting, is_p3):
    want = TAGS[bundle][setting]
    if isinstance(tag, str) and "_FB" in tag:
        return False, "_FB tag"
    if bundle == "T-3K" and isinstance(tag, str) and tag.endswith("_LAS"):
        return False, "_LAS without _K1 (H-T3-3)"
    if tag != want:
        return False, f"tag {tag!r} != {want!r}"
    if is_p3 is not None and isinstance(tag, str) and is_p3(tag) != (setting == "VB"):
        return False, f"is_extend_start_tag({tag}) wrong for {setting}"
    return True, None


# ----------------------------------------------------------------- dg3 lines
CAND_PREFIX = "cand=current#"
EXT_RULE_PATHS = ("two_pressure.extend_start_rule", "controller_settings.two_pressure.extend_start_rule",
                  "preset_settings.two_pressure.extend_start_rule", "resume_k1.two_pressure.extend_start_rule",
                  "controller_meta.two_pressure.settings.extend_start_rule")


def norm_dg3_key(k):
    """rev3 R3-D1: keys with and without the ``cand=current#`` prefix are the same key."""
    return k[len(CAND_PREFIX):] if isinstance(k, str) and k.startswith(CAND_PREFIX) else k


def dig_dotted(d, path):
    """Nested lookup that also accepts a dict key containing dots (e.g. ``preset_settings["two_pressure.x"]``)."""
    if not isinstance(d, dict):
        return core.MISSING
    if path in d:
        return d[path]
    head, _, rest = path.partition(".")
    while rest:
        if head in d:
            v = dig_dotted(d[head], rest)
            if v is not core.MISSING:
                return v
        h2, _, rest = rest.partition(".")
        head = f"{head}.{h2}"
    return d.get(head, core.MISSING)


def dg3_folder(rec):
    """rev3 R3-D1: the folder from the recorded controller setting: tracked_bound -> v4_on, else off.
    None if the setting is not recorded (S-11 / H-T3-3)."""
    for p in EXT_RULE_PATHS:
        v = dig_dotted(rec, p)
        if isinstance(v, str):
            return "v4_on" if v == "tracked_bound" else "off"
    return None


def dg3_records(path, folder=None):
    """(folder, key, rec) from a dg3 output: jsonl lines or a JSON with ``results[]`` / ``records[]``.
    The folder is read from the record (R3-D1); a folder given on the command line is only cross-checked."""
    p = Path(path)
    if p.suffix == ".jsonl":
        recs = core.read_jsonl(p)
    else:
        data = json.loads(p.read_text("utf-8"))
        recs = data.get("results") or data.get("records") or []
    for r in recs:
        k = norm_dg3_key(r.get("key") or r.get("id"))
        got = dg3_folder(r)
        if folder is not None and got is not None and got != folder:
            r = dict(r, _folder_conflict=f"recorded {got} vs given {folder}")
        yield got, k, r


def dg3_hash(r):
    v, _ = core.first_path(r, core.HASH_PATHS)
    return None if v is core.MISSING else v


THREAD_ENV = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS")
# rev7 R7-3b: line / header identity of las_T3_*.jsonl (first line ``header``, then ``t3`` per line)
LINE_IDENTITY_KEYS = ("git_head", "sha256", "c2_sha256", "threads", "workers", "affinity")
IDENTITY_TOOL_FILES = ("las_t3.py", "las_t3_dg3.py", "las_h7.py", "las_judge.py", "las_targeted.py",
                       "las_t3_presets.py")
IDENTITY_THREAD_KEYS = THREAD_ENV + ("MKL_THREADING_LAYER",)
SHADOW_ENV = core.SHADOW_ENV
_HEX = set("0123456789abcdef")


def _is_hex(v, n):
    return isinstance(v, str) and len(v) == n and set(v) <= _HEX


def is_header(rec):
    """rev7 R7-3b: the first line of a las_T3 output is the ``header`` record (no line body)."""
    return isinstance(rec.get("header"), dict) and not isinstance(rec.get("t3"), dict) and "d1" not in rec


def identity_problems(ident, t3=None):
    """rev7 R7-3b formats of one ``identity`` block (+ the ``t3`` mirror fields of a line). [] = matches."""
    p = []
    if not isinstance(ident, dict):
        return ["identity block missing"]
    if not _is_hex(ident.get("git_head"), 40):
        p.append("git_head: 40 hex")
    sh = ident.get("sha256")
    if not (isinstance(sh, dict) and set(sh) == set(IDENTITY_TOOL_FILES) and all(_is_hex(v, 64) for v in sh.values())):
        p.append(f"sha256: dict of the six files {IDENTITY_TOOL_FILES} -> 64 hex")
    if not _is_hex(ident.get("c2_sha256"), 64):
        p.append("c2_sha256: 64 hex")
    th = ident.get("threads")
    if not (isinstance(th, dict) and set(th) == set(IDENTITY_THREAD_KEYS)
            and all(v is None or isinstance(v, str) for v in th.values())):
        p.append(f"threads: dict {IDENTITY_THREAD_KEYS} -> str or null")
    if isinstance(ident.get("workers"), bool) or not isinstance(ident.get("workers"), int):
        p.append("workers: int")
    if "affinity" not in ident or not (ident["affinity"] is None or isinstance(ident["affinity"], str)):
        p.append("affinity: str or null")
    if t3 is not None:
        if t3.get("commit") != ident.get("git_head"):
            p.append("t3.commit != identity.git_head")
        if t3.get("workers") != ident.get("workers") or isinstance(t3.get("workers"), bool):
            p.append("t3.workers != identity.workers")
        if "affinity_hex" not in t3 or t3.get("affinity_hex") != ident.get("affinity"):
            p.append("t3.affinity_hex != identity.affinity")
    return p


def identity_of(path):
    """The run's ``.identity.json`` (run_identity ``start`` / ``end`` records). (dict or None, file)."""
    p = Path(path)
    for c in (Path(str(p) + ".identity.json"), p.with_suffix(".identity.json")):
        if c.is_file():
            return json.loads(c.read_text("utf-8")), str(c)
    return None, None


def line_identity(rec):
    """rev7 R7-3b identity of one record: ``header.identity`` for the header, ``t3.identity`` for a line.
    (identity dict of LINE_IDENTITY_KEYS or None, format problems)."""
    if is_header(rec):
        ident, t3 = rec["header"].get("identity"), None
    elif isinstance(rec.get("t3"), dict):
        ident, t3 = rec["t3"].get("identity"), rec["t3"]
    else:
        return None, ["no header.identity / t3.identity"]
    prob = identity_problems(ident, t3)
    if not isinstance(ident, dict):
        return None, prob
    return {k: ident.get(k) for k in LINE_IDENTITY_KEYS}, prob


def output_identity(path):
    """(identity common to the header and every line, or None; S-11 format problems; H-T3-3 problem or None)
    of one jsonl output (rev6 R6-C2 condition read through the rev7 R7-3b names)."""
    recs = core.read_jsonl(path)
    fmt = []
    if not recs or not is_header(recs[0]):
        fmt.append("first line is not the header record (R7-3b)")
    ids = []
    for i, r in enumerate(recs):
        if i > 0 and is_header(r):
            fmt.append(f"line {i + 1}: a second header record")
        lid, prob = line_identity(r)
        if prob:
            fmt.append(f"line {i + 1}: {prob[:3]}")
        if lid is not None:
            ids.append(lid)
    if not ids:
        return None, fmt, None
    first = json.dumps(ids[0], sort_keys=True, default=str)
    if any(json.dumps(x, sort_keys=True, default=str) != first for x in ids[1:]):
        return ids[0], fmt, "header / line identities differ inside the output"
    return ids[0], fmt, None


def identity_check(paths, fnd, repo=None, git_at_start=None, allowed_dirty=(), steps=()):
    """K-0 with the rev6 R6-C2 table: .identity.json start / end git.head (= git_at_start), git.is_clean or
    status_porcelain within the audit allowance, threads (four = 1, MKL_THREADING_LAYER = TBB), rules_seals
    all ok; controller / tool sha from the outputs' own line / header identity (same in every line and in the
    three outputs); OUTRIGGER_LOC_SHADOW by the RV1-9 method (step files given with --steps)."""
    got, line_ids = {}, {}
    for name, p in paths.items():
        row = {"checks": {}}
        got[name] = row
        ck = row["checks"]

        def need(label, ok, why=""):
            ck[label] = ok
            if ok is None:
                fnd.undec(f"K-0:{name}", f"{label}: source missing (R6-C2)")
            elif ok is False:
                fnd.stop("H-T3-3", f"K-0:{name}", f"{label}: {why}")

        ident, used = identity_of(p)
        row["file"] = used
        s = ident.get("start") if isinstance(ident, dict) else None
        e = ident.get("end") if isinstance(ident, dict) else None
        if not isinstance(s, dict) or not isinstance(e, dict):
            need("identity_file", None)
        else:
            h0, h1 = core.dig(s, "git.head", None), core.dig(e, "git.head", None)
            need("head", None if h0 is None or h1 is None else (h0 == h1 and (git_at_start is None or
                 str(h0).startswith(git_at_start) or str(git_at_start).startswith(str(h0)))),
                 f"{h0} / {h1} / git_at_start {git_at_start}")
            if git_at_start is None:
                ck["head_vs_git_at_start"] = "not checked (--git-at-start not given)"
            if core.dig(s, "git.is_clean", None) is True:
                ck["tree"] = True
            elif isinstance(core.dig(s, "git.status_porcelain", None), str):
                dirty = [ln[3:].strip() for ln in s["git"]["status_porcelain"].splitlines() if ln.strip()]
                extra = [x for x in dirty if x not in allowed_dirty]
                ck["tree"] = not extra
                if extra:
                    fnd.undec(f"K-0:{name}", f"dirty files not in the pre-run audit allowance: {extra[:5]}")
            else:
                need("tree", None)
            th = s.get("threads")
            need("threads", None if not isinstance(th, dict) else
                 (all(str(th.get(k)) == "1" for k in THREAD_ENV) and th.get("MKL_THREADING_LAYER") == "TBB"),
                 {k: (th or {}).get(k) for k in THREAD_ENV + ("MKL_THREADING_LAYER",)})
            seals = s.get("rules_seals")
            if isinstance(seals, dict):
                vals = list(seals.values())
            else:
                vals = seals if isinstance(seals, list) else None
            need("rules_seals", None if not vals else all(
                (v.get("ok") is True) if isinstance(v, dict) else (v is True) for v in vals), "a rules seal not ok")
        lid, fmt, prob = output_identity(p)
        if fmt:
            ck["line_identity_format"] = False
            row["line_identity_format_problems"] = fmt[:20]
            fnd.stop("S-11", f"K-0:{name}", f"line / header identity differs from the rev7 R7-3b table: {fmt[:3]}")
        else:
            ck["line_identity_format"] = True
        if lid is None:
            need("line_identity", None)
        elif prob:
            need("line_identity", False, prob)
        else:
            ck["line_identity"] = True
            line_ids[name] = lid
    if len(line_ids) >= 2:
        vals = {json.dumps(v, sort_keys=True, default=str) for v in line_ids.values()}
        got["line_identity_same_across_outputs"] = len(vals) == 1
        if len(vals) > 1:
            fnd.stop("H-T3-3", "K-0", "controller / tool line identity differs between R-0 / R-0K / T-3K")
    if steps:
        hit = [sp for sp in steps if SHADOW_ENV in Path(sp).read_text("utf-8")]
        got["loc_shadow_env"] = {"step_files": list(steps), "files_with_name": hit}
        if hit:
            fnd.stop("H-T3-3", "K-0", f"{SHADOW_ENV} in step files {hit} (436.8 4.2)")
    else:
        got["loc_shadow_env"] = "판정 불가: step files not given (RV1-9 method)"
        fnd.undec("K-0", f"{SHADOW_ENV}: step files not given (--steps, RV1-9)")
    return got


# ----------------------------------------------------------------- main recount
def recount(repo, r0_lines, r0k_lines, t3_lines, dg3_r0, dg3_t3, d1_lines, is_p3):
    fnd = core.Findings()
    keys = json.loads((repo / REV3_KEYS_REL).read_text("utf-8"))
    r0k_list = json.loads((repo / R0K_KEYS_REL).read_text("utf-8"))
    r0k = {e["key"]: e for e in r0k_list["R-0K"]}
    lst = "".join(k + "\n" for k in sorted(r0k)).encode("utf-8")
    if hashlib.sha256(lst).hexdigest() != R0K_LIST_SHA or len(r0k) != COUNTS["R-0K"]:
        fnd.stop("H-T3-0", "R-0K key list", "list sha256 / count differs from rev5 2.3")
    kl = {}
    for b in ("T-3a", "T-3c"):
        for e in keys[b]:
            kl[e["key"]] = dict(e, bundle=b)
    t3b = {(e["folder"], norm_dg3_key(e["key"])): e for e in keys["T-3b"]}
    g1_uniform = {k for k, e in kl.items() if e["bundle"] == "T-3a" and e.get("base") == "G1"}
    # rev4a 1: key-list baseline fields = d1.jsonl values (H-T3-3)
    d1_idx = {}
    for ln in d1_lines or []:
        k = d1_key(ln)
        if k:
            d1_idx[k] = ln
    base_check = {"checked": 0, "differ": []}
    if d1_lines:
        for k, e in kl.items():
            ln = d1_idx.get(k)
            if ln is None:
                base_check["differ"].append({"key": k, "why": "absent in d1.jsonl"})
                continue
            b = baseline_of_line(ln)
            base_check["checked"] += 1
            for f, kv in (("commands_sha256", e.get("commands_sha256")), ("verdict", e.get("verdict")),
                          ("fail_items", e.get("fail_items")), ("t_ready_s", core.num(e.get("t_ready_s"))),
                          ("stroke_max_m", core.num(e.get("stroke_max_m")))):
                if not core.same_value(b[f], kv) and b[f] != kv:
                    base_check["differ"].append({"key": k, "field": f})
            p32 = b["P3-2"] if b["P3-2"] is not core.MISSING else None
            if p32 != e.get("P3-2"):
                base_check["differ"].append({"key": k, "field": "P3-2"})
            if sorted(b["faults"] or []) != sorted(e.get("fault_names") or []):
                base_check["differ"].append({"key": k, "field": "fault_names"})
        for d in base_check["differ"]:
            fnd.stop("H-T3-3", f"baseline {d['key']}", f"key list vs d1.jsonl: {d.get('field', d.get('why'))}")
    tag_tally = {}
    out = {"baseline_check_rev4a": base_check, "R7-1c_tag_reading": tag_tally}

    def index(lines, bundle):
        idx = {}
        for ln in lines:
            if is_header(ln):        # rev7 R7-3b: the header record carries no line body
                continue
            k = d1_key(ln)
            if "error" in ln:
                fnd.stop("H-T3-2", f"{bundle}:{k}", "error line left (after the one retry)")
                continue
            if k in idx:
                fnd.stop("H-T3-3", f"{bundle}:{k}", "duplicate key")
            idx[k] = ln
        return idx

    # rev3 R3-D1: the dg3 folder must come from the record (and agree with a folder given on the CLI)
    for f_, k_, r_ in list(dg3_r0) + list(dg3_t3):
        if f_ is None:
            fnd.stop("H-T3-3", f"dg3:{k_}", "two_pressure.extend_start_rule not recorded: folder unknown (R3-D1, S-11)")
        if isinstance(r_, dict) and r_.get("_folder_conflict"):
            fnd.stop("H-T3-3", f"dg3:{k_}", r_["_folder_conflict"])
    # ---- R-0 (rev3 K-2; 5 D-1 + 2 dg3)
    r0_idx = index(r0_lines, "R-0")
    r0_want = set(keys["R-0"]["d1"])
    r0_rep = []
    if set(r0_idx) != r0_want:
        fnd.stop("H-T3-3", "R-0", f"D-1 key set differs ({len(r0_idx)} vs 5)")
    for k in sorted(r0_want & set(r0_idx)):
        ln, setting = r0_idx[k], k.split("|")[-2]
        base = baseline_of_line(d1_idx[k]) if k in d1_idx else None
        bh = base["commands_sha256"] if base else (kl.get(k) or {}).get("commands_sha256") or r0k.get(k, {}).get("stored_commands_sha256")
        tr, tsrc = tag_presence(ln, "R-0", setting, fnd, f"R-0:{k}", tag_tally.setdefault("R-0", {}))
        ok_t, why = tag_ok(line_tag(ln), "R-0", setting, is_p3)
        act = is_active(ln)
        same = ln.get("commands_sha256") == bh
        r0_rep.append({"key": k, "hash_same": same, "tag_ok": ok_t, "active": act, "tag_read": tr,
                       "tag_read_source": tsrc})
        if not ok_t:
            fnd.stop("H-T3-3", f"R-0:{k}", why)
        if not same or act:
            fnd.stop("H-T3-1", f"R-0:{k}", f"K-2: hash same {same}, active {act}")
    dg3_want = {(x[0], norm_dg3_key(x[1])) for x in keys["R-0"]["dg3"]}
    dg3_got = {(f, norm_dg3_key(k)): r for f, k, r in dg3_r0}
    if set(dg3_got) != dg3_want:
        fnd.stop("H-T3-3", "R-0 dg3", f"dg3 key set {sorted(dg3_got)} != {sorted(dg3_want)}")
    for fk in sorted(dg3_want & set(dg3_got)):
        r = dg3_got[fk]
        e = t3b.get(fk) or {}
        want = (e.get("shadow_commands_sha256_all_folders") or [None])[0]
        same = dg3_hash(r) == want
        act = is_active(r)
        r0_rep.append({"key": list(fk), "hash_same": same, "active": act})
        if not same or act:
            fnd.stop("H-T3-1", f"R-0 dg3:{fk}", f"K-2: hash same {same}, active {act}")
    out["R-0"] = r0_rep

    # ---- R-0K (rev5 3.2)
    r0k_idx = index(r0k_lines, "R-0K")
    r0k_rep = []
    if set(r0k_idx) != set(r0k):
        fnd.stop("H-T3-3", "R-0K", f"K-1K key set differs ({len(r0k_idx)} vs 45)")
    for k in sorted(set(r0k) & set(r0k_idx)):
        ln, e = r0k_idx[k], r0k[k]
        tag_presence(ln, "R-0K", e["setting"], fnd, f"R-0K:{k}", tag_tally.setdefault("R-0K", {}))
        ok_t, why = tag_ok(line_tag(ln), "R-0K", e["setting"], is_p3)
        act, wb = is_active(ln), would_block_any(ln)
        cfg = config_check(ln, "R-0K")
        same = ln.get("commands_sha256") == e.get("stored_commands_sha256")
        row = {"key": k, "class": e["class"], "would_block_any": wb, "hash_same_stored": same, "active": act,
               "tag_ok": ok_t, "config": cfg}
        r0k_rep.append(row)
        if not ok_t or act or cfg:
            fnd.stop("H-T3-3", f"R-0K:{k}", f"K-2K (i): tag {why}, active {act}, config {cfg}")
        if wb is None:
            fnd.undec(f"R-0K:{k}", "order_gate decisions missing (9.3)")
            continue
        if wb is False and not same:
            fnd.stop("H-T3-1K", f"R-0K:{k}", "K-2K (ii): would_block_any false but hash != stored")
        if e["class"] == "r0_no_r4" and (wb or not same):
            fnd.stop("H-T3-1K", f"R-0K:{k}", f"K-2K (iii): would_block_any {wb}, hash same {same}")
        if e["class"] == "uniform_r4" and wb:
            fnd.stop("H-T3-1Q", f"R-0K:{k}", "K-2K (iv): gate blocked on a uniform soft-ground key (ask)")
    out["R-0K"] = r0k_rep

    # ---- T-3K
    t3_idx = index(t3_lines, "T-3K")
    rep = {"T-3a": 0, "T-3c": 0, "rows": [], "active_rows": [], "K-6_violations": []}
    if set(t3_idx) != set(kl):
        fnd.stop("H-T3-3", "T-3K", f"K-1 key set differs ({len(t3_idx)} vs {len(kl)}: "
                                   f"missing {len(set(kl) - set(t3_idx))}, extra {len(set(t3_idx) - set(kl))})")
    for k in sorted(set(kl) & set(t3_idx)):
        ln, e = t3_idx[k], kl[k]
        rep[e["bundle"]] += 1
        tag_presence(ln, "T-3K", e["setting"], fnd, f"T-3K:{k}", tag_tally.setdefault("T-3K", {}))
        ok_t, why = tag_ok(line_tag(ln), "T-3K", e["setting"], is_p3)
        cfg = config_check(ln, "T-3K")
        if not ok_t or cfg:
            fnd.stop("H-T3-3", f"T-3K:{k}", f"K-3: tag {why}, config {cfg}")
        if k in r0k:
            bl = r0k_idx.get(k)
            if bl is None:
                fnd.undec(f"T-3K:{k}", "R-0K baseline line missing")
                continue
            base, src = baseline_of_line(bl), "R-0K"
        else:
            base = baseline_of_line(d1_idx[k]) if k in d1_idx else baseline_of_keylist(e)
            src = "d1.jsonl" if k in d1_idx else "key list"
        new = baseline_of_line(ln)
        act, wb = is_active(ln), would_block_any(ln)
        same = new["commands_sha256"] == base["commands_sha256"]
        row = {"key": k, "bundle": e["bundle"], "active": act, "would_block_any": wb, "hash_same_B": same,
               "baseline_source": src}
        rep["rows"].append(row)
        if k in g1_uniform:
            if act:
                fnd.stop("H-T3-4", f"T-3K:{k}", "K-4: LAS-b active on a G1 uniform row (ask)")
            elif not same:
                fnd.fail(f"T-3K:{k}", "H-T3-5 (K-4 hash, rev4a 3): inactive G1 uniform row, hash != B(k)")
                fnd.stop("H-T3-5", f"T-3K:{k}", "K-5 hash")
        if not act:
            if not same and k not in g1_uniform:
                fnd.stop("H-T3-5", f"T-3K:{k}", "K-5: inactive line, hash != B(k)")
            if k not in r0k and wb is not False:
                if wb is None:
                    fnd.undec(f"T-3K:{k}", "order_gate decisions missing (9.3)")
                else:
                    fnd.stop("H-T3-5", f"T-3K:{k}", "K-5 (G-c): inactive non-R-0K line with would_block_any")
            continue
        vio = k6(new, base)
        dec = decisions_of(ln) or []
        first = next((x for x in dec if isinstance(x, dict)), None)
        bdec = decisions_of(r0k_idx[k]) if k in r0k_idx else None
        rep["active_rows"].append({
            "key": k, "K-6": vio, "would_block_any": wb,
            "applied": sum(1 for x in dec if isinstance(x, dict) and x.get("applied") is True),
            "first_dP_periods": (first.get("n_P") - first.get("n_S")) if first and isinstance(first.get("n_P"), int)
            and isinstance(first.get("n_S"), int) else None,
            "baseline_source": src,
            "decision_set_differs": None if bdec is None else (
                sorted(str(x.get("n_P")) for x in bdec if isinstance(x, dict) and x.get("would_block"))
                != sorted(str(x.get("n_P")) for x in dec if isinstance(x, dict) and x.get("would_block"))),
            "las": core.dig(ln, "resume_k1.liftoff_approach_slow", None)})
        if vio:
            rep["K-6_violations"].append({"key": k, "violations": vio})
            fnd.fail(f"T-3K:{k}", f"H-T3-6: {vio}")
            fnd.stop("H-T3-6", f"T-3K:{k}", f"K-6 {vio} (ask)")
    # T-3b dg3 (K-4 only)
    dg3_t3 = {(f, norm_dg3_key(k)): r for f, k, r in dg3_t3}
    if set(dg3_t3) != set(t3b):
        fnd.stop("H-T3-3", "T-3b", f"dg3 key set {len(dg3_t3)} vs 4")
    t3b_rep = []
    for fk in sorted(set(dg3_t3) & set(t3b)):
        r, e = dg3_t3[fk], t3b[fk]
        want = (e.get("shadow_commands_sha256_all_folders") or [None])[0]
        act, same = is_active(r), dg3_hash(r) == want
        t3b_rep.append({"key": list(fk), "active": act, "hash_same": same})
        if act:
            fnd.stop("H-T3-4", f"T-3b:{fk}", "K-4: LAS-b active on dg3 G1 uniform (ask)")
        elif not same:
            fnd.stop("H-T3-5", f"T-3b:{fk}", "K-4/K-5: inactive dg3 line, hash differs")
    rep["T-3b"] = t3b_rep
    rep["counts"] = {"T-3a": rep["T-3a"], "T-3b": len(t3b_rep), "T-3c": rep["T-3c"],
                     "active": len(rep["active_rows"]), "K-4_rows": len(g1_uniform & set(t3_idx)) + len(t3b_rep)}
    out["T-3K"] = rep
    return out, fnd


# S-11 (rev7 R7-1c missing tag key, R7-3b identity format) is a record defect: listed right after H-T3-0
ORDER = ["H-T3-0", "S-11", "H-T3-3", "H-T3-2", "H-T3-1", "H-T3-1K", "H-T3-1Q", "H-T3-4", "H-T3-5", "H-T3-6"]
EXIT_OF = {"H-T3-0": 2, "S-11": 2, "H-T3-3": 2, "H-T3-2": 2, "H-T3-1": 2, "H-T3-1K": 1, "H-T3-1Q": 2, "H-T3-4": 2,
           "H-T3-5": 1, "H-T3-6": 2}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--r0", required=True, help="t3_k1/las_T3_R0.jsonl")
    ap.add_argument("--r0k", required=True, help="t3_k1/las_T3_R0K.jsonl")
    ap.add_argument("--t3", required=True, help="t3_k1/las_T3.jsonl")
    ap.add_argument("--dg3-r0", action="append", default=[], help="FOLDER=path of the R-0 dg3 output(s)")
    ap.add_argument("--dg3-t3", action="append", default=[], help="FOLDER=path of the T-3b dg3 output(s)")
    ap.add_argument("--d1", default=None, help="stored v5/d1.jsonl (rev4a 1 baseline check, G6-2_loc / FAULT)")
    ap.add_argument("--git-at-start", default=None, help="git_at_start commit for the K-0 head / c2.py check (R4-C4)")
    ap.add_argument("--allowed-dirty", action="append", default=[], help="file allowed dirty by the pre-run audit")
    ap.add_argument("--steps", action="append", default=[], help="step file(s) steps_*.json for the RV1-9 env check")
    args = ap.parse_args(argv)
    repo = Path(args.repo) if args.repo else _HERE.parents[4]
    tool_sha = core.sha256_file(Path(__file__))
    summary = {"tool": TOOL_NAME, "version": TOOL_VERSION, "tool_sha256": tool_sha,
               "core_sha256": core.sha256_file(_HERE / "p2_4368.py")}
    try:
        seals = core.check_seals(repo)
        ok_las, las = check_las_seals(repo)
        if not seals["ok"] or not ok_las:
            report, code = {"seals": seals, "las_rules": las, "stop_codes": ["S-1", "H-T3-0"]}, 2
        else:
            is_p3, mod = core.load_is_extend_start(repo)
            d1 = core.read_jsonl(args.d1) if args.d1 else None
            if d1 is not None and core.sha256_file(args.d1) != D1_SHA:
                raise ValueError("d1.jsonl sha256 differs from the key list baseline")

            def dg3(items):
                res = []
                for a in items:
                    f, sep, p = a.partition("=")
                    if not sep or f not in ("off", "v4_on"):
                        f, p = None, a
                    res.extend(dg3_records(p, f))
                return res

            body, f = recount(repo, core.read_jsonl(args.r0), core.read_jsonl(args.r0k), core.read_jsonl(args.t3),
                              dg3(args.dg3_r0), dg3(args.dg3_t3), d1, is_p3)
            body["K-0"] = identity_check({"R-0": args.r0, "R-0K": args.r0k, "T-3K": args.t3}, f, repo,
                                         args.git_at_start, tuple(args.allowed_dirty), tuple(args.steps))
            body["H-T3-0_pre_run"] = "실행 전 관문: 두 경로 대상 아님(R3-D3). 실행 전 감사·경로 1 기록 경로를 판정서에 적는다"
            codes = sorted({s["code"] for s in f.stops}, key=lambda c: ORDER.index(c) if c in ORDER else 99)
            first = codes[0] if codes else None
            code = EXIT_OF.get(first, 2) if first else (1 if (f.fails or f.undecidable) else 0)
            status = "통과" if code == 0 and not f.undecidable else ("판정 불가" if f.undecidable and not codes else
                                                                    ("멈춤" if code == 2 else "미달"))
            report = {"las_rules": las, "v5_options": mod, "seals_eol_only": seals.get("eol_only", []),
                      "H-0": {**body, **f.as_dict(), "first_stop": first, "stop_order": codes,
                              "status_4368": status, "S-14": "본 묶음 시작 가능" if status == "통과" else "S-14 멈춤"},
                      "inputs": {n: [p, core.sha256_file(p)] for n, p in (("r0", args.r0), ("r0k", args.r0k), ("t3", args.t3))},
                      "stop_codes": codes}
        report.update(tool=TOOL_NAME, version=TOOL_VERSION, tool_sha256=tool_sha,
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"))
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = core.sha256_file(args.out)
        summary.update(exit=code, out=args.out, out_sha256=out_sha, stop_codes=report.get("stop_codes", []))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
