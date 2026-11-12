"""Path-2 recount of H-0 T-3K (436.8 stage 0): R-0 K-2, R-0K K-1K / K-2K, T-3K K-1 / K-3 / K-4 / K-5 / K-6 / K-7.

Rules: ``las_targeted_rules.md`` (00b48fd8...) and its addenda rev1, rev2, rev3 (+ key list rev3_keys), rev4,
rev4a, rev4b, rev4c, rev5 (+ R-0K key list) - eleven sealed files (rev5 1 #5), read through the 436.8 rules
(5.1 H-0 "rev5 그대로", S-14). Author: dynamics-expert (path 2, second author). Path-1 tools (``las_judge``,
``las_h7``, ``las_t3*`` judging parts) and their outputs were not opened (436.8 9.2).

Definitions used (rule sentences; the line fields are the stored ``v5/d1.jsonl`` names):
  active      rev3 3: an ``INFO_LIFTOFF_SLOW`` start event (not ``_END``) in the line's events
              (``event_names`` count, else ``events`` [t, name])
  would_block rev5 2.1: ``slope_clearance_margin.order_gate.decisions[*].would_block``; ``would_block_any``
  B(k)        rev5 3.1: R-0K line for the 45 R-0K keys, else the rev3 key-list values (checked against
              ``v5/d1.jsonl`` when given, rev4a 1); dg3: key-list ``shadow_commands_sha256_all_folders``
  K-6a~e      rev3 3 table with rev4a 1-2 (``G6-2_loc``; item absent in the baseline = not applicable;
              baseline true + new None = violation)

Stops (rev5 4 order): H-T3-0 -> H-T3-3 -> H-T3-2 -> H-T3-1 -> H-T3-1K -> H-T3-1Q -> H-T3-4 -> H-T3-5 -> H-T3-6.
Exit codes (rev3 / rev5): 0 pass, 1 a criteria fail (H-T3-1K, H-T3-5, H-T3-6 class), 2 a stop without
judgement (H-T3-0, H-T3-1, H-T3-1Q, H-T3-2, H-T3-3, H-T3-4) or a rules sha mismatch, 3 tool error.
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
    v, _ = core.first_path(ln, core.TAG_PATHS)
    return None if v is core.MISSING else v


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
def dg3_records(path, folder):
    """(folder, key, rec) from a dg3 output: jsonl lines or a JSON with ``results[]`` / ``records[]``."""
    p = Path(path)
    if p.suffix == ".jsonl":
        recs = core.read_jsonl(p)
    else:
        data = json.loads(p.read_text("utf-8"))
        recs = data.get("results") or data.get("records") or []
    for r in recs:
        k = r.get("key") or r.get("id")
        if isinstance(r.get("cand"), str) and isinstance(k, str) and not k.startswith("cand="):
            k = f"cand={r['cand']}#{k}"
        yield folder, k, r


def dg3_hash(r):
    v, _ = core.first_path(r, core.HASH_PATHS)
    return None if v is core.MISSING else v


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
    t3b = {(e["folder"], e["key"]): e for e in keys["T-3b"]}
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
    out = {"baseline_check_rev4a": base_check}

    def index(lines, bundle):
        idx = {}
        for ln in lines:
            k = d1_key(ln)
            if "error" in ln:
                fnd.stop("H-T3-2", f"{bundle}:{k}", "error line left (after the one retry)")
                continue
            if k in idx:
                fnd.stop("H-T3-3", f"{bundle}:{k}", "duplicate key")
            idx[k] = ln
        return idx

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
        ok_t, why = tag_ok(line_tag(ln), "R-0", setting, is_p3)
        act = is_active(ln)
        same = ln.get("commands_sha256") == bh
        r0_rep.append({"key": k, "hash_same": same, "tag_ok": ok_t, "active": act})
        if not ok_t:
            fnd.stop("H-T3-3", f"R-0:{k}", why)
        if not same or act:
            fnd.stop("H-T3-1", f"R-0:{k}", f"K-2: hash same {same}, active {act}")
    dg3_want = {tuple(x) for x in keys["R-0"]["dg3"]}
    dg3_got = {(f, k): r for f, k, r in dg3_r0}
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
    dg3_t3 = {(f, k): r for f, k, r in dg3_t3}
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


ORDER = ["H-T3-0", "H-T3-3", "H-T3-2", "H-T3-1", "H-T3-1K", "H-T3-1Q", "H-T3-4", "H-T3-5", "H-T3-6"]
EXIT_OF = {"H-T3-0": 2, "H-T3-3": 2, "H-T3-2": 2, "H-T3-1": 2, "H-T3-1K": 1, "H-T3-1Q": 2, "H-T3-4": 2,
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
                    f, p = a.split("=", 1)
                    res.extend(dg3_records(p, f))
                return res

            body, f = recount(repo, core.read_jsonl(args.r0), core.read_jsonl(args.r0k), core.read_jsonl(args.t3),
                              dg3(args.dg3_r0), dg3(args.dg3_t3), d1, is_p3)
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
