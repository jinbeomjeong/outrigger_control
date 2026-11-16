"""Path-2 R4 tool for the 436.8 rev16 rows: H-11 G-3 gate, C-9~C-11 records, RD-13 item lists.

Rules: the 436.8 R4 common block (sha256 e451f067..., RD-0~RD-13) and the rule bullets handed to path 2-dyn
(rev16 R16-8 = P2-16~P2-25, R16-11 / R16-11b = P2-30~P2-43, rev16:350 output place = P2-44; rules rev25
c0b778fd...). Author: dynamics-expert (third path-2 author, a new agent run without the earlier authors' context,
written only from the R4 handoff for path 2-dyn). Path-1 tools and outputs were not opened (436.8 9.2, RD-6).

Sub-commands:
  g3     H-11 (rev16 R16-8): the 8 key pairs of the option-free runs against their comparison outputs (same
         field hash), count check (exactly one line per key on each side), commit identity of every H-11 run
         (``<stem>.identity.json`` start / end records: ``git.head`` = R2 and clean, else S-12). G-3 true / false;
         false -> marker ``G-3(H-11) 거짓`` and the RD-7 list (script, key, field, hashes, line counts); H-3 / H-4
         are then not judged (rev16:142).
  c16    C-9 / C-10 / C-11 records (R16-11 record items, R16-11b 1 identity, R16-11b 2 row-folder files): record
         bundles, ``기록 완료`` / ``기록 불완전`` (never a grade). C-9 P-18 premise (rev16:254). R4 supplement 1
         (sha 8736f68d...) / 2 (a9a15a13...): identity files ``<OUT>\\_identity\\<short>_pre|post.json`` (``dry_`` not
         read), rc = ``exit=`` of the first line of ``<OUT>\\_runners\\logs_*\\<short>_run.done`` (2-4), C-10 G6 from
         the ``p3b`` P3 values (2-5), C-11 at the first LOC and, with a revoke, also at the final LOC (2-6).
  items  RD-13 item lists of the bundles the path-2 tools judge or record (item, rule clause, kind); one JSON file,
         per-bundle sha256 of the canonical list.

Exit codes: 0 nothing stopped / incomplete; 1 a record incomplete or an undecidable item; 2 a stop (S-*, G-3 false)
or a rules sha mismatch / not the M4 checkout (S-12); 3 tool error. Last stdout line: JSON summary with
``out_sha256``. Only the stdlib and numpy (npz) are used.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import re
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p2_4368_core", _HERE / "p2_4368.py")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

TOOL_NAME = "p2_x16.py"
TOOL_VERSION = "1"
LEGS = ("FL", "FR", "RL", "RR")

# ----------------------------------------------------------------- H-11 (rev16 R16-8, P2-16~P2-25)
G3_MARKER = "G-3(H-11) 거짓"
# (script, key, option-free output in <OUT>/H-11, comparison output, container, hash field, controller filter)
# comparison output: "las_k1:<name>" = v5_rerun/las_k1/<name> (H-3 V0 output of R2), "h11:<name>" = <OUT>/H-11/<name>
G3_PAIRS = (
    ("s9_slope_fix_candidates.py", "base|G1|B|top|Fs0", "u3_p3b_none.json", "las_k1:u3_p3b_V0.json", "records",
     "hash", None),
    ("s9_slope_fix_candidates.py", "slope|edge|top|4.0|ref|none|0|proj", "u3_g8_none.json", "las_k1:u3_g8_V0.json",
     "records", "hash", None),
    ("r72_g6_screen.py", "g6|G1+J1@FL|top|Fs8", "u3_C_none.json", "las_k1:u3_C_V0.json", "results",
     "commands_sha256", None),
    ("r72_g6_screen.py", "g6r|rigid+J1@FL|top|Fs8", "u3_C_none.json", "las_k1:u3_C_V0.json", "results",
     "commands_sha256", None),
    ("s9_soil_slope.py", "H8|rigid|B|top|flat", "u3_D_none.json", "las_k1:u3_D_V0.json", "results",
     "run.commands_sha256", None),
    ("s9_soil_slope.py", "H8|G1|B|top|flat|FL:g20", "u3_D_none.json", "las_k1:u3_D_V0.json", "results",
     "run.commands_sha256", None),
    ("b5_baseline_compare.py", "A1-rigid", "u6_b5_A1_none.json", "h11:u6_b5_A1_V0.json", "records",
     "commands_sha256", "C2"),
    ("b5_baseline_compare.py", "A1-J1", "u6_b5_A1_none.json", "h11:u6_b5_A1_V0.json", "records",
     "commands_sha256", "C2"),
)
KEY_FIELDS = ("id", "key", "case")       # the line identifier of the three output forms


def _item_key(r):
    for f in KEY_FIELDS:
        v = r.get(f)
        if isinstance(v, str) and v:
            return v
    return None


def lines_for(path, container, key, controller):
    """Items of ``container`` whose identifier equals ``key`` (and ``controller`` when given)."""
    data = json.loads(Path(path).read_text("utf-8"))
    items = data.get(container) if isinstance(data.get(container), list) else []
    return [r for r in items if isinstance(r, dict) and _item_key(r) == key
            and (controller is None or r.get("controller") == controller)]


def identity_records(path):
    """start / end records of a ``resume_k1_identity`` sidecar (dict or list of dicts)."""
    data = json.loads(Path(path).read_text("utf-8"))
    out = {}
    for m in ("start", "end"):
        v = data.get(m)
        recs = [v] if isinstance(v, dict) else (v if isinstance(v, list) else [])
        out[m] = [r for r in recs if isinstance(r, dict)]
    return out


def h11_identity(path, r2):
    """rev16:143 (P2-24): every start / end record ``git.head`` = R2 and the tree clean; else S-12."""
    if not Path(path).is_file():
        return {"file": str(path), "ok": False, "why": "identity sidecar missing"}
    recs = identity_records(path)
    out = {"file": str(path), "sha256": core.sha256_file(path), "n_start": len(recs["start"]),
           "n_end": len(recs["end"]), "ok": True, "why": None}
    if not recs["start"] or not recs["end"]:
        out.update(ok=False, why="start or end record missing")
        return out
    for m in ("start", "end"):
        for r in recs[m]:
            head = core.dig(r, "git.head", None)
            clean = core.dig(r, "git.is_clean", None)
            porcelain = core.dig(r, "git.status_porcelain", None)
            if not (isinstance(head, str) and head.lower() == r2):
                out.update(ok=False, why=f"{m} git.head {head!r} != R2")
                return out
            if clean is not True or (isinstance(porcelain, str) and porcelain.strip()):
                out.update(ok=False, why=f"{m} tree not clean")
                return out
    return out


def cmd_g3(args, repo):
    fnd = core.Findings()
    h11 = Path(args.h11_dir)
    lk = Path(args.las_k1_dir) if args.las_k1_dir else repo / "06_analysis/02_control/v5_rerun/las_k1"
    pairs, false_rows = [], []
    for script, key, none_name, cmp_ref, cont, field, ctrl in G3_PAIRS:
        where = f"{script}:{key}"
        p_none = h11 / none_name
        ref_dir, ref_name = cmp_ref.split(":", 1)
        p_cmp = (lk if ref_dir == "las_k1" else h11) / ref_name
        row = {"script": script, "key": key, "field": field, "none_file": core.rel_posix(p_none, repo),
               "compare_file": core.rel_posix(p_cmp, repo), "none_hash": None, "compare_hash": None,
               "none_lines": None, "compare_lines": None, "equal": False}
        if not p_none.is_file() or not p_cmp.is_file():
            row["why"] = "output file missing"
        else:
            ln = lines_for(p_none, cont, key, ctrl)
            lc = lines_for(p_cmp, cont, key, ctrl)
            row["none_lines"], row["compare_lines"] = len(ln), len(lc)
            if len(ln) == 1:
                row["none_hash"] = core.dig(ln[0], field, None)
            if len(lc) == 1:
                row["compare_hash"] = core.dig(lc[0], field, None)
            # P2-22 count check: exactly one line on each side; P2-23: the field hashes are equal
            row["equal"] = (len(ln) == 1 and len(lc) == 1 and isinstance(row["none_hash"], str)
                            and row["none_hash"] == row["compare_hash"])
            if not row["equal"]:
                row["why"] = ("count check false" if not (len(ln) == 1 and len(lc) == 1)
                              else "hash field missing or different")
        pairs.append(row)
        if not row["equal"]:
            false_rows.append({"script": script, "key": key, "field": field, "none_hash": row["none_hash"],
                               "compare_hash": row["compare_hash"], "none_lines": row["none_lines"],
                               "compare_lines": row["compare_lines"]})
            fnd.stop(G3_MARKER, where, row.get("why"))
    # P2-24 commit identity of every H-11 run (option-free and the b5 V0 arm)
    ident = {}
    names = sorted({p[2] for p in G3_PAIRS} | {p[3].split(":", 1)[1] for p in G3_PAIRS if p[3].startswith("h11:")})
    for nm in names:
        side = h11 / (Path(nm).stem + ".identity.json")
        ident[nm] = h11_identity(side, core.R2_COMMIT)
        if not ident[nm]["ok"]:
            fnd.stop("S-12", nm, f"H-11 run identity: {ident[nm]['why']} (rev16:143)")
    g3 = not false_rows
    out = {"G-3": g3, "marker": None if g3 else G3_MARKER, "n_pairs": len(pairs), "pairs": pairs,
           "G-3_false_list": {"columns": ["script", "key", "field", "none_hash", "compare_hash", "none_lines",
                                          "compare_lines"], "rows": false_rows},
           "identity": ident, "r2_commit": core.R2_COMMIT,
           "consequence": None if g3 else "H-3 / H-4 not judged, stop and ask (rev16:142)"}
    out.update(fnd.as_dict())
    return out, fnd.status()


# ----------------------------------------------------------------- C-9 ~ C-11 (rev16 R16-11, R16-11b)
DLL_SHA = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"   # rev16:280 (P2-42)
FORBIDDEN_ENV = ("OUTRIGGER_LOC_SHADOW", "OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED", "OUTRIGGER_HULL_HOOK_DLL",
                 "OUTRIGGER_HULL_HOOK", "MIXED_HULL_MODE")
THREADS = 4
# bundle, row name (P2-32), --duration, identity file stem (pre / post), patch leg (C-10)
C16_ROWS = (
    ("C-9", "R4368X_G1_B_top_Fs4_V0_gateon", 120.0, "C9on", None),
    ("C-9", "R4368X_G1_B_top_Fs4_V0_gateoff", 120.0, "C9off", None),
    ("C-10", "R4368X_rigidS1FL_B_top_Fs4_V0", 160.0, "C10FLV0", "FL"),
    ("C-10", "R4368X_rigidS1FL_B_top_Fs4_VB", 160.0, "C10FLVB", "FL"),
    ("C-10", "R4368X_rigidS1FR_B_top_Fs4_V0", 160.0, "C10FRV0", "FR"),
    ("C-10", "R4368X_rigidS1FR_B_top_Fs4_VB", 160.0, "C10FRVB", "FR"),
    ("C-11", "R4368X_J2_B_top_Fs0_L2_V0", 120.0, "C11V0", None),
    ("C-11", "R4368X_J2_B_top_Fs0_L2_VB", 120.0, "C11VB", None),
)
ROW_FILES = ("result.json", "controller_commands.npz", "step_series.npz", "r8_series.npz",
             "completion_series.npz", "record/record.npz", "record/meta.json")   # rev16:288 (P2-43)
P3_CHECKS = ("P3-1_crawler_zero_after_ready", "P3-1_recontact_pass", "P3-2_within", "P3-3_within",
             "P3-4_within_0p2", "P3-5_within", "P3-6_within", "P3-7_within", "P3-8_within", "P3-9_flags")
# identity files <OUT>\_identity\<short>_pre.json / _post.json (R4 supplement 1-2; the `dry_` files are not read).
# Key names from the files (opened under the supplement): top-level head, tracked_status (git status --porcelain
# --untracked-files=no lines), forbidden_env (name -> value, null = absent), case; pre: env, dll_sha256;
# post: reflog_n5, reflog_new_since_pre. Their meaning is R16-11b 1 (rev16:280~287).
DONE_RE = re.compile(r"(?:^|\s)exit=(-?\d+)(?:\s|$)")


def done_rc(runners_dir, short):
    """R4 supplement 2-4: rc = N of ``exit=N`` on the first line of ``<runners>/logs_*/<short>_run.done``.
    Returns (rc or None, why, file)."""
    hits = sorted(Path(runners_dir).glob(f"logs_*/{short}_run.done")) if runners_dir else []
    if len(hits) != 1:
        return None, f"{len(hits)} {short}_run.done files (exactly one required)", None
    with open(hits[0], encoding="utf-8", errors="replace") as f:
        first = f.readline()
    m = DONE_RE.search(first.strip())
    if not m:
        return None, "no exit= on the first line of the .done file", str(hits[0])
    return int(m.group(1)), None, str(hits[0])


def row_identity(res, pre, post, row=None):
    """rev16:280~287 (P2-42) identity of one row: result.json fields + start / end identity files.
    Returns (dict, stops[(code, why)], incomplete[why])."""
    stops, inc = [], []
    out = {"result": {}, "pre": None, "post": None}
    gas = core.dig(res, "code_state.git_at_start.head", None)
    out["result"]["git_at_start"] = gas
    if not (isinstance(gas, str) and gas.lower() == core.R2_COMMIT):
        stops.append(("S-12", f"result.json code_state.git_at_start.head {gas!r} != R2"))
    nt = res.get("num_threads_chrono")
    out["result"]["num_threads_chrono"] = nt
    if nt != THREADS:
        stops.append(("S-4", f"num_threads_chrono {nt!r} != 4"))
    owp = core.dig(res, "placement.omp_wait_policy", None)
    out["result"]["omp_wait_policy"] = owp
    if owp != "PASSIVE":
        stops.append(("S-4", f"placement.omp_wait_policy {owp!r} != PASSIVE"))
    out["result"]["affinity_mask_process"] = core.dig(res, "placement.affinity_mask_process", None)
    out["result"]["placement_requested"] = core.dig(res, "placement.requested", None)
    hh = {k: core.dig(res, "hull_hook." + k, None) for k in ("mode", "dll_sha_validated", "dll_sha256",
                                                               "fallback_reason")}
    out["result"]["hull_hook"] = hh
    if hh["mode"] != "fast" or hh["dll_sha_validated"] is not True or hh["dll_sha256"] != DLL_SHA:
        stops.append(("S-4", f"hull_hook {hh}"))
    for name, d in (("pre", pre), ("post", post)):
        if d is None:
            inc.append(f"identity file {name} missing")
            continue
        keys = ("case", "head", "tracked_status", "forbidden_env") + \
            (("env", "dll_sha256") if name == "pre" else ("reflog_n5", "reflog_new_since_pre"))
        rec = {k: d.get(k) for k in keys}
        out[name] = rec
        missing = [k for k in keys if k not in d]
        if missing:
            inc.append(f"identity {name}: keys {missing} missing")
        if rec["case"] != row:
            inc.append(f"identity {name}: case {rec['case']!r} != row {row!r}")
        if not (isinstance(rec["head"], str) and rec["head"].lower() == core.R2_COMMIT):
            stops.append(("S-12", f"identity {name}: HEAD {rec['head']!r} != R2"))
        if not (isinstance(rec["tracked_status"], list) and not rec["tracked_status"]):
            stops.append(("S-12", f"identity {name}: git status --porcelain --untracked-files=no not empty"))
        fb = rec["forbidden_env"]
        if not isinstance(fb, dict) or any(fb.get(e, "absent-key") is not None for e in FORBIDDEN_ENV):
            stops.append(("S-4", f"identity {name}: forbidden env present or not recorded {fb!r}"))
        if name == "pre":
            if rec["dll_sha256"] != DLL_SHA:
                stops.append(("S-4", "identity pre: DLL sha256 differs"))
            if not isinstance(rec["env"], dict) or rec["env"].get("OMP_WAIT_POLICY") != "PASSIVE":
                stops.append(("S-4", "identity pre: start env OMP_WAIT_POLICY != PASSIVE"))
        else:
            if not (isinstance(rec["reflog_new_since_pre"], list) and not rec["reflog_new_since_pre"]):
                stops.append(("S-12", "identity post: new reflog entries since the start (rev16:280)"))
    if pre is not None and post is not None and pre.get("head") != post.get("head"):
        stops.append(("S-12", "identity: end HEAD != start HEAD"))
    return out, stops, inc


def _load_json(p):
    return json.loads(Path(p).read_text("utf-8")) if Path(p).is_file() else None


def row_common(folder, duration):
    """Files, rc-independent items shared by the three bundles."""
    import numpy as np   # noqa: PLC0415
    files = {}
    for f in ROW_FILES:
        p = folder / f
        files[f] = core.sha256_file(p) if p.is_file() else None
    res = _load_json(folder / "result.json") or {}
    st = None
    last_t = None
    if (folder / "step_series.npz").is_file():
        with np.load(folder / "step_series.npz", allow_pickle=False) as z:
            st = {k: np.asarray(z[k]) for k in ("t_s", "s_motor_m", "scm_crawler_normal_N", "pad_sinkage_geometric_m")
                  if k in z.files}
        if "t_s" in st and st["t_s"].size:
            last_t = float(st["t_s"][-1])
    p3 = core.dig(res, "p3b.checks", {}) or {}
    items = {
        "first_ready_s": core.dig(res, "p3b.P3-5_clearance_stroke.t_first_ready_s", None),
        "last_sample_t_s": last_t,
        "max_stroke_mm": (float(st["s_motor_m"].max()) * 1000.0 if st is not None and "s_motor_m" in st
                          and st["s_motor_m"].size else None),
        "P3": {k: p3.get(k) for k in P3_CHECKS},
        "duration_s": core.dig(res, "args.duration", None),
        "duration_expected_s": duration,
    }
    return res, st, files, items


def c9_items(res, st):
    og = core.dig(res, "controller_meta.slope_clearance_margin.order_gate", None)
    return {"decisions": og.get("decisions") if isinstance(og, dict) else None,
            "soil_mode_start_t_s": core.dig(res, "p3b.P3-2_loc.soil_mode_start_t_s", None),
            "loc_t_s": core.dig(res, "p3b.P3-2_loc.t_loc_s", None),
            "loc_first_t_s": core.dig(res, "p3b.P3-2_loc.t_loc_first_s", None),
            "loc_final_t_s": core.dig(res, "p3b.P3-2_loc.t_loc_final_s", None),
            "end_rut_gap_mm": (None if core.num(core.dig(res, "p3b.P3-5_clearance_stroke.rut_clearance_end_m", None))
                               is None else core.num(core.dig(res, "p3b.P3-5_clearance_stroke.rut_clearance_end_m",
                                                              None)) * 1000.0)}


NO_READY = "해당 없음(READY 없음)"
READY_LIMIT_S = 120.0
FAULT_PHASES = ("fault", "fault_reground")


def g6_from_p3b(res):
    """R4 supplement 2-5 (rev25 CD-8 9 / CD-11 G6 table): C-10 G6 values from the row's ``p3b`` P3 values.
    G6-1 = P3-1 (crawler zero READY ~ READY + 10 s and the re-contact check), G6-2 = P3-2, G6-3 = P3-3, G6-4 = P3-4,
    G6-5 = P3-5, G6-7 = P3-8; G6-6 = no FAULT and READY reached; READY_le_120s = first READY after the loop start
    <= 120 s (1e-9). Without READY: G6-4 / G6-5 = "해당 없음(READY 없음)", G6-6 / READY_le_120s = "미달"; G6-1 keeps
    the recorded P3-1 value (CD-5 P3-1 row: not handed, the recorded value is written)."""
    ck = core.dig(res, "p3b.checks", {}) or {}
    t_ready = core.num(core.dig(res, "p3b.P3-6_ready.t_ready_after_loop_start_s", None))
    ready = t_ready is not None
    ev = res.get("events") if isinstance(res.get("events"), list) else []
    fault_ev = [e.get("name") for e in ev if isinstance(e, dict) and str(e.get("name", "")).startswith("FAULT")]
    ph = [p.get("phase") for p in res.get("phases") or [] if isinstance(p, dict)]
    no_fault = not fault_ev and not any(p in FAULT_PHASES for p in ph)
    p31 = (None if ck.get("P3-1_crawler_zero_after_ready") is None or ck.get("P3-1_recontact_pass") is None
           else bool(ck["P3-1_crawler_zero_after_ready"] and ck["P3-1_recontact_pass"]))
    g6 = {"G6-1": p31, "G6-2": ck.get("P3-2_within"), "G6-3": ck.get("P3-3_within"),
          "G6-4": ck.get("P3-4_within_0p2") if ready else NO_READY,
          "G6-5": ck.get("P3-5_within") if ready else NO_READY,
          "G6-6": (no_fault and ready) if ready else "미달",
          "G6-7": ck.get("P3-8_within"),
          "READY_le_120s": (not core.t_gt(t_ready, READY_LIMIT_S)) if ready else "미달"}
    return g6, {"P3-2_verdict": ck.get("P3-2_verdict"), "fault_events": fault_ev, "t_ready_after_loop_start_s": t_ready}


def c10_items(res, st, folder, patch_leg):
    g6, g6src = g6_from_p3b(res)
    rec = {"G6": g6, "G6_source": g6src, "G6_rule": "R4 supplement 2-5 (rev25 CD-11 G6 table, p3b P3 values)",
           "P3-3": core.dig(res, "p3b.checks.P3-3_within", None),
           "end_phase": None, "patch_leg": patch_leg, "patch_leg_sinkage_mm": None}
    ph = res.get("phases")
    if isinstance(ph, list) and ph and isinstance(ph[-1], dict):
        rec["end_phase"] = ph[-1].get("phase")
    if st is not None and "pad_sinkage_geometric_m" in st and patch_leg in LEGS and st["pad_sinkage_geometric_m"].size:
        rec["patch_leg_sinkage_mm"] = float(st["pad_sinkage_geometric_m"][-1, LEGS.index(patch_leg)]) * 1000.0
    w = core.num(core.dig(res, "p3b.weight_N", None))
    sp = folder / "step_series.npz"
    if w is not None and sp.is_file():
        fr = core.series_force_recount(sp, w)       # 1 ms true F_cyl, original 7.4 definition (R2-5 / R2-6)
        rec["force"] = {k: fr.get(k) for k in ("t_departure_s", "legs", "window_truncated_at_run_end", "dt_s")}
    else:
        rec["force"] = None
    return rec


def loc_period(st, t_loc, w):
    """Spec 419.8.1 condition 3: max crawler SCM normal over the 1 ms samples in (t_LOC - 0.1 s, t_LOC] and the t_LOC
    sample; / W and above / below 0.01 W (W = ``p3b.weight_N``, the departure threshold weight). ``p3b`` times and
    ``step_series.npz`` ``t_s`` are the same absolute time base (R4 supplement 2-6)."""
    out = {"t_loc_s": t_loc, "crawler_max_N": None, "crawler_max_over_W": None, "above_0p01W": None}
    if st is None or t_loc is None or "scm_crawler_normal_N" not in st:
        return out
    t, cr = st["t_s"], st["scm_crawler_normal_N"]
    m = (t > t_loc - 0.1 - 1e-9) & (t <= t_loc + 1e-9)
    if m.any():
        mx = float(cr[m].max())
        out["crawler_max_N"] = mx
        if w:
            out["crawler_max_over_W"] = mx / w
            out["above_0p01W"] = bool(mx >= 0.01 * w - core.EPS_THR)
    return out


def c11_items(res, st):
    """R16-11 3 record items; t_LOC = the first LOC, and with a revoke (final LOC differs) the same three values at
    the final LOC too (R4 supplement 2-6)."""
    w = core.num(core.dig(res, "p3b.weight_N", None))
    t_first = core.num(core.dig(res, "p3b.P3-2_loc.t_loc_first_s", None))
    t_final = core.num(core.dig(res, "p3b.P3-2_loc.t_loc_final_s", None))
    rv = core.dig(res, "p3b.P3-2_loc.loc_revokes", None)
    first = loc_period(st, t_first, w)
    rec = {"loc_first_t_s": t_first, "loc_final_t_s": t_final, "weight_N": w,
           "loc_revokes": len(rv) if isinstance(rv, list) else None,
           "loc_period_crawler_max_N": first["crawler_max_N"],
           "loc_period_crawler_max_over_W": first["crawler_max_over_W"], "above_0p01W": first["above_0p01W"],
           "final_loc_period": None}
    if t_first is not None and t_final is not None and not core.same_value(t_first, t_final):
        rec["final_loc_period"] = loc_period(st, t_final, w)
    return rec


def cmd_c16(args, repo):
    fnd = core.Findings()
    out_root = Path(args.out_root)
    idd = Path(args.identity_dir) if args.identity_dir else out_root / "_identity"
    runners = Path(args.runners_dir) if args.runners_dir else out_root / "_runners"
    bundles = {}
    rows = {}
    for bundle, name, dur, idstem, patch in C16_ROWS:
        folder = out_root / bundle / name
        where = f"{bundle}:{name}"
        b = bundles.setdefault(bundle, {"rows": [], "incomplete": [], "status": "기록 완료"})
        b["rows"].append(name)
        if not (folder / "result.json").is_file():
            b["incomplete"].append({"row": name, "why": "result.json missing"})
            rows[name] = {"bundle": bundle, "folder": str(folder), "present": False}
            continue
        res, st, files, items = row_common(folder, dur)
        pre = _load_json(idd / f"{idstem}_pre.json") if idd else None
        post = _load_json(idd / f"{idstem}_post.json") if idd else None
        ident, stops, inc = row_identity(res, pre, post, row=name)
        for code, why in stops:
            fnd.stop(code, where, why)
        miss_files = [f for f, h in files.items() if h is None]
        if miss_files:
            inc.append(f"row files missing {miss_files} (rev16:288)")
        if core.dig(res, "args.flow_eta_v", None) is not None and not (folder / "flow_series.npz").is_file():
            inc.append("flow_series.npz missing on a VB row (--flow-eta-v given, rev16:288)")
        rc, rc_why, rc_file = done_rc(runners, idstem)      # R4 supplement 2-4
        items["rc"] = rc
        items["rc_source"] = rc_file
        if rc is None:
            inc.append(f"rc: {rc_why}")
        if bundle == "C-9":
            items.update(c9_items(res, st))
        elif bundle == "C-10":
            items.update(c10_items(res, st, folder, patch))
        else:
            items.update(c11_items(res, st))
        items["controller_commands_sha256"] = files.get("controller_commands.npz")
        for w in inc:
            b["incomplete"].append({"row": name, "why": w})
        rows[name] = {"bundle": bundle, "folder": core.rel_posix(folder, repo), "present": True, "files": files,
                      "identity": ident, "items": items}
    # C-9 pair: commands sha equal? and the P-18 premise (rev16:254)
    on, off = rows.get("R4368X_G1_B_top_Fs4_V0_gateon"), rows.get("R4368X_G1_B_top_Fs4_V0_gateoff")
    p18 = {"premise": None, "why": [], "commands_equal": None}
    if on and off and on.get("present") and off.get("present"):
        p18["commands_equal"] = (on["items"]["controller_commands_sha256"] is not None
                                 and on["items"]["controller_commands_sha256"] == off["items"]["controller_commands_sha256"])
        for r in (on, off):
            it = r["items"]
            if it.get("rc") != 0:
                p18["why"].append(f"rc {it.get('rc')!r}")
            lt, d = core.num(it.get("last_sample_t_s")), core.num(it.get("duration_s"))
            if lt is None or d is None or core.t_lt(lt, d - 0.1):
                p18["why"].append(f"last sample {lt} < duration - 0.1 s")
            if it.get("first_ready_s") is None:
                p18["why"].append("no first READY")
            if r["identity"]["result"].get("num_threads_chrono") != THREADS:
                p18["why"].append("threads != 4")
            if r["identity"]["result"].get("placement_requested") != "pcore":
                p18["why"].append(f"placement.requested {r['identity']['result'].get('placement_requested')!r} != pcore")
        p18["premise"] = not p18["why"]
        if not p18["premise"]:
            bundles["C-9"]["incomplete"].append({"row": "C-9 pair", "why": "P-18 premise false: " + "; ".join(p18["why"])})
    else:
        p18["why"].append("a C-9 arm is missing")
    for b in bundles.values():
        b["status"] = "기록 불완전" if b["incomplete"] else "기록 완료"
        for x in b["incomplete"]:
            fnd.undec(x["row"], x["why"])
    out = {"out_root": str(out_root), "identity_dir": None if idd is None else str(idd), "bundles": bundles,
           "rows": rows, "C-9_P-18": p18,
           "note": "record bundles (rev16:55): no grade; 기록 불완전 when a record item or an identity file is missing"}
    out.update(fnd.as_dict())
    return out, fnd.status()


# ----------------------------------------------------------------- RD-13 item lists
G, R, K = "등급 항목", "기록", "관문"
_LAYER = [  # p2_4368.py harness (436.8 layer), every harness bundle
    ("태그(4.1 표, is_extend_start_tag)", "원판 4.1", K),
    ("4.2 금지 토큰·기록 확인", "원판 4.2", K),
    ("7.2 K1 분류(미작동·LAS-b 작동·K1 막힘·둘 다)", "원판 7.2", R),
    ("7.2 기록 모순(would_block ∧ ¬r4_due, applied ∧ ¬r4_due, _SKIPPED:order 수)", "rev2 R2-1", K),
    ("멈춤 S-6 목록(균일 연약 계열 K1 막힘)", "원판 8.2 S-6", K),
    ("계열 판정(강체·패치·처방 침하·균일 연약)", "rev1 RV1-6", R),
    ("LAS-b start_s 읽기", "rev2 R2-2", R),
    ("결측 = 판정 불가", "원판 9.3", R),
    ("묶음 줄 수 S-15", "rev1 RV1-12", K),
    ("RD-9 ③ 켬 줄 수", "원판 4.1", K),
]
_RD8 = [("RD-8 J-P3 입력 형식(breach_reads 4정수, 기록 pass 빈 통과)", "rev4 R4-A2", K)]
_KS = [("키 원본 해시 대조(미작동 확인, 기록)", "rev16:87", R)]
RD13_ITEMS = {
    "H-1": _LAYER + _RD8 + [
        ("P-1·P-2 비트 앵커 대조(anchors)", "rev1 RV1-5", K),
        ("D-1 관문 G-1~G-4(p2_d1)", "d1_selection_rules 10", K),
        ("H-R 다섯 항목 재판정(p2_d1)", "d1_selection_rules 11", G),
        ("d1.verdict 재집계(p2_d1)", "rev3 R3-A2", G),
        ("READY 원점(p2_d1)", "rev4 R4-C1", R),
        ("강등 항목 집합(p2_d1)", "rev4 R4-C3", G),
        ("G6-7 세 분기(p2_d1)", "rev6 R6-C3", G),
    ],
    "H-2": [("D-1 선별(후보 등급·여유 m·순위, S1~S3, 크롤러 ×3)(p2_d1)", "d1_selection_rules 4", G),
            ("C-2 행 수(p2_d1)", "rev1 RV1-10 g", K)],
    "H-3": _LAYER + _RD8 + [
        ("U-3 G-1 실행 오류·키 수", "u3 원판 7", K),
        ("U-3 G-2 meta·태그", "u3 rev2 #4", K),
        ("U-3 G-4 J-P3 선택(파일 설정)", "u3 rev2 #5", K),
        ("U-3 G-6 g8 VB 대체 사건 목록", "u3 rev1 #5", K),
        ("U-3 G-5 VB 고유 실패 목록", "u3 원판 5.1", K),
        ("U-3 등급 이동 4×4·묶음 문구", "u3 원판 5.1", G),
        ("정착 v2 재계산(축별)", "rev16:194", G),
        ("r72 계열 등급(g6·연구 C)", "rev16:194", G),
        ("r72 G6-2 LOC 취소 강등(G6-2_late_loc_revoked, 조건 1~6, 424.11.2 강등)", "rev3 R3-G12", G),
        ("D-1 재사용", "rev3 R3-B3", R),
    ],
    "H-4": _LAYER + _RD8 + [
        ("U-6 G-1 사례 수", "u3 원판 7", K),
        ("U-6 G-2 태그(③는 C2만)", "u3 rev2 #4", K),
        ("U-6 제어기별 표", "u3 원판 5.2", R),
        ("IND_LAS 관문·해시 동일", "rev3 R3-B5", R),
        ("u6 키 계열(안쪽 키 = src의 지면 토큰)", "rev16:197", R),
    ],
    "H-5": _LAYER + [
        ("U-9 키·태그", "u9_targeted_rules_rev1 2", K),
        ("U-9 H0", "u9_targeted_rules_rev1 4", K),
        ("T1 J1~J10(η_v 0.85)", "v5_criteria 3", G),
        ("J11 대체 다리 n_late", "rev16:102", G),
        ("J-P3(RD-8 형식)", "rev3 R3-C8", G),
        ("T3·T4·4.1 분류(η_v 0.80)", "rev3 R3-C2", R),
    ],
    "H-6": _LAYER + _KS, "H-7": _LAYER + _KS, "H-8": _LAYER + _KS, "H-9": _LAYER + _KS, "H-10": _LAYER,
    "H-11": [("G-3 8쌍 해시 같음", "rev16:142", K), ("수 검사(키마다 1줄)", "rev16:141", K),
             ("커밋 정체성(R2, clean)", "rev16:143", K), ("G-3 거짓 짝 목록", "rev16:142", K)],
    "C-9": [("두 팔 decisions(dP)·토양 모드 시작·LOC 시각", "rev16:250", R),
            ("두 팔 controller_commands.npz sha 같음", "rev16:250", R),
            ("최대 행정·끝 rut 틈·P3-1~P3-9·첫 READY·rc·마지막 표본 시각", "rev16:250", R),
            ("P-18 읽기 전제", "rev16:254", R), ("정체성(시작·끝 파일, result.json)", "rev16:280", K)],
    "C-10": [("다리별 F^a_min·F^t_min·시각, F<F_min·F<F_min+2kN 시간(1 ms)", "rev16:257", R),
             ("G6-1~G6-7·READY_le_120s(p3b P3 값으로 갈음, G6-6 따로)", "rev25:99", R),
             ("P3-3·끝 단계·최대 행정·패치 다리 침하·rc(.done exit=)·마지막 표본 시각", "rev16:257", R),
             ("정체성(시작·끝 파일, result.json)", "rev16:280", K)],
    "C-11": [("첫 LOC·LOC 주기 1 ms 크롤러 법선 최대와 /W·0.01 W 위아래·LOC 취소 수", "rev16:264", R),
             ("LOC 취소가 있으면 최종 LOC 기준 같은 세 값", "rev16:264", R),
             ("첫 READY·rc·마지막 표본 시각", "rev16:264", R), ("정체성(시작·끝 파일, result.json)", "rev16:280", K)],
    "J_P": [("행 집합(두 batch.json cases, 12 고정)", "원판 7.3", K), ("사건 기록 꼴(C2Event 문자열)", "원판 7.3", K),
            ("R4c30 적용 수(기본 이름)·토양 모드 시작 수", "원판 7.3", R),
            ("그림자 줄 수·조건 1", "원판 7.3", K), ("조건 2·재사용 참거짓", "원판 7.3", R)],
}


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def rd13_lists():
    lists = {b: [{"item": i, "clause": c, "kind": k} for i, c, k in items] for b, items in RD13_ITEMS.items()}
    return lists, {b: canonical_sha(v) for b, v in lists.items()}


def cmd_items(args, repo):
    lists, shas = rd13_lists()
    return {"columns": ["item", "clause", "kind"], "kinds": [G, R, K], "lists": lists, "list_sha256": shas,
            "sha_rule": "sha256 of json.dumps(list, ensure_ascii=False, sort_keys=True, separators=(',', ':')) UTF-8",
            "note": "path-2 item names; clauses of earlier sheets not handed over are copied from the tool comments / "
                    "README (RD-13, decision 117 2)"}, "pass"


# ----------------------------------------------------------------- main
CMDS = {"g3": cmd_g3, "c16": cmd_c16, "items": cmd_items}


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None, help="repository root (default: 5 levels above this file)")
    ap.add_argument("--out", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    head_help = "full 40-hex M4 commit; the judging checkout HEAD must equal it, else S-12 (R4 RD-1 5)"
    g = sub.add_parser("g3")
    g.add_argument("--h11-dir", required=True, help="<OUT>\\H-11")
    g.add_argument("--las-k1-dir", default=None, help="v5_rerun/las_k1 (default: under --repo)")
    g.add_argument("--expect-head", required=True, help=head_help)
    c = sub.add_parser("c16")
    c.add_argument("--out-root", required=True, help="<OUT> (rev16:350)")
    c.add_argument("--identity-dir", default=None,
                   help="folder of the <short>_pre.json / _post.json identity files (default <OUT>\\_identity)")
    c.add_argument("--runners-dir", default=None,
                   help="folder holding logs_*\\<short>_run.done (rc, supplement 2-4; default <OUT>\\_runners)")
    c.add_argument("--expect-head", required=True, help=head_help)
    sub.add_parser("items")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    repo = Path(args.repo) if args.repo else _HERE.parents[4]
    tool_sha = core.sha256_file(Path(__file__))
    summary = {"tool": TOOL_NAME, "version": TOOL_VERSION, "tool_sha256": tool_sha, "cmd": args.cmd,
               "core_sha256": core.sha256_file(_HERE / "p2_4368.py")}
    try:
        seals = core.check_seals(repo)
        hc = core.head_check(repo, args.expect_head) if args.cmd in ("g3", "c16") else None
        if not seals["ok"]:
            report, status = {"seals": seals, "stop_codes": ["S-1"]}, "stop"
        elif hc is not None and not hc["ok"]:
            report, status = {"head_check": hc, "stop_codes": ["S-12"]}, "stop"
        else:
            body, status = CMDS[args.cmd](args, repo)
            report = {"seals": {"ok": True, "r4_rev13_25_sha256": {Path(r).stem: w for r, w, _ in core.R4_SEALS_EXTRA},
                                "r4_common_block_sha256": core.R4_BLOCK_SHA,
                                "eol_only": seals.get("eol_only", [])}, **body}
            if hc is not None:
                report["head_check"] = hc
        report.update(tool=TOOL_NAME, version=TOOL_VERSION, tool_sha256=tool_sha, cmd=args.cmd,
                      argv=sys.argv[1:] if argv is None else list(argv),
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"), status=status)
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = core.sha256_file(args.out)
        code = core.EXIT[status]
        summary.update(status=status, exit=code, out=args.out, out_sha256=out_sha,
                       stop_codes=report.get("stop_codes", []))
        if args.cmd == "items":
            summary["list_sha256"] = report.get("list_sha256")
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(status="tool_error", exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
