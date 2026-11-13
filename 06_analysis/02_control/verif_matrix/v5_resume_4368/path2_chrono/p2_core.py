"""Path 2 core: load one Chrono row from raw files and recompute judgement quantities.

Inputs are raw records only (time series, phases, events, settings, argv). The judgement
blocks written by the row judges (SCM `p3b` / `p3b_ext` except the two keys named by the
rules, L2b / L1-R `acceptance` / `h4` / `c2` / `stroke` / `s8_end`) are never read.

Verdict words used per item:
  pass / fail / flag (counts as pass, d1 rules 3) / hold (R40-2) / indeterminate / na / record
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import p2_rules as R

EVENT_RE = re.compile(r"C2Event\(t_s=([-+0-9.eE]+), name='(.*)'\)$")


class InputError(Exception):
    """Missing or inconsistent input (exit 2)."""


# ----------------------------------------------------------------------------- params
def load_params(repo: Path) -> dict:
    import yaml  # PyYAML (dynamics-dev)
    y = yaml.safe_load((repo / R.REPO_MARKER).read_text(encoding="utf-8"))
    areas = [float(y["legs"][leg]["cylinder"]["head_area_m2"]) for leg in R.LEGS]
    return {
        "F_min_N": float(y["control"]["F_min_cylinder_N"]),
        "v_max_m_s": float(y["actuator"]["max_speed_m_s"]),
        "head_area_m2": areas,
    }


# ----------------------------------------------------------------------------- row data
@dataclass
class Row:
    case: str
    engine: str                      # scm / l2b / l1r
    folder: Path
    t_offset: float                  # add to phase / event times to get absolute time
    loop_start: float                # absolute
    t_end: float                     # absolute, last 1 ms sample
    tF: np.ndarray                   # 1 ms time
    F: np.ndarray                    # (n,4) 1 ms true F_cyl (min over the 1 ms interval when recorded)
    F_inst: np.ndarray               # (n,4) 1 ms true F_cyl (sample)
    s_motor: np.ndarray              # (n,4) on tF
    t_att: np.ndarray
    att: np.ndarray                  # (m,2) roll, pitch [deg], gravity-based body attitude
    t_cr: np.ndarray | None
    cr: np.ndarray | None            # crawler normal [N]
    cr_basis: str
    t_pad: np.ndarray | None
    pad_n: np.ndarray | None         # (k,4) pad normal [N]
    t_sink: np.ndarray | None
    sink: np.ndarray | None          # (k,4) pad sinkage [m] (SCM)
    law_locked: np.ndarray | None    # (n,4) int8 on tF (SCM step_series / L2b pads, rev8 R8-3a, rev9 R9-2); None if absent or malformed
    t10: np.ndarray                  # 10 Hz control instants
    issued: np.ndarray               # (p,4) issued command [m/s]
    phases: list                     # [(t_abs, name)]
    events: list                     # [(t_abs, name)]
    floor_label: str
    flat: bool
    target_deg: tuple
    weight_N: float | None
    rut: list                        # [(t_abs, clearance m or None)] (SCM s9_rows)
    result: dict = field(repr=False, default_factory=dict)
    argv: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    law_locked_source: str | None = None          # "step_series.npz law_locked" / "pads.npz law_locked"
    law_locked_problems: list = field(default_factory=list)   # rev9 R9-2 format problems (non-empty = malformed)
    law_locked_pattern: dict | None = None        # rev9 R9-3 -1 pattern (None if the key is absent)


def law_locked_pattern(arr) -> dict:
    """rev9 R9-3 -1 pattern of a [N, 4] `law_locked`.

    allowed: `none` (no -1) or `before_first_arming` (-1 from the first sample, all four legs leave
    -1 at the same sample, no -1 afterwards; read as locked, rev6 6). Format errors (R9-5):
    `after_arming` (-1 after any leg showed 0 or 1), `whole_run` (every sample of every leg -1),
    `per_leg_mismatch` (legs leave -1 at different samples)."""
    a = np.asarray(arr)
    out = {"patterns": [], "first_armed_index_per_leg": None, "unarmed_prefix_samples": 0,
           "after_arming_samples_per_leg": None, "ok": False}
    if a.ndim != 2 or a.shape[1] != 4 or a.shape[0] == 0:
        out["patterns"] = ["not_evaluated"]
        return out
    neg = a == -1
    if not neg.any():
        out.update(patterns=["none"], first_armed_index_per_leg=[0, 0, 0, 0],
                   after_arming_samples_per_leg=[0, 0, 0, 0], ok=True)
        return out
    if neg.all():
        out.update(patterns=["whole_run"], unarmed_prefix_samples=int(a.shape[0]))
        return out
    armed = ~neg
    first = [int(np.argmax(armed[:, j])) if armed[:, j].any() else None for j in range(4)]
    k_any = min(f for f in first if f is not None)   # first sample where any leg is armed
    after = (neg & (np.arange(a.shape[0])[:, None] >= k_any)).sum(axis=0).astype(int).tolist()
    pats = []
    if len(set(first)) != 1:
        pats.append("per_leg_mismatch")
    if sum(after) > 0:
        pats.append("after_arming")
    if not pats:
        pats = ["before_first_arming"] if k_any > 0 else ["none"]
    out.update(patterns=pats, first_armed_index_per_leg=first, unarmed_prefix_samples=int(k_any),
               after_arming_samples_per_leg=after, ok=pats in (["none"], ["before_first_arming"]))
    return out


def law_locked_check(arr, t) -> list:
    """rev9 R9-2 format check of `law_locked` (both engines alike). `t` is the same file's time
    column (None = absent). Returns problems as strings starting with the item code
    (`R9-2.1` .. `R9-2.6`, R.LAW_LOCK_ITEMS); empty = well formed. Item 6 is the R9-3 -1 pattern."""
    probs = []
    arr = np.asarray(arr)
    if t is None:
        probs.append("R9-2.1: time column absent")
    else:
        t = np.asarray(t, float)
    if arr.ndim != 2 or arr.shape[1] != 4:
        probs.append(f"R9-2.2: shape {list(arr.shape)} != [N, 4]")
    elif t is not None and arr.shape[0] != len(t):
        probs.append(f"R9-2.2: rows {arr.shape[0]} != time column rows {len(t)}")
    if arr.dtype != np.int8:
        probs.append(f"R9-2.3: dtype {arr.dtype} != int8")
    if arr.size:
        bad = sorted(set(np.unique(arr).tolist()) - set(R.LAW_LOCK_VALUES))
        if bad:
            probs.append(f"R9-2.4: values {bad[:5]} outside {list(R.LAW_LOCK_VALUES)}")
    if t is not None and len(t) > 1:
        d = np.diff(t)
        dev = np.abs(d - R.LAW_LOCK_DT_S)
        n_bad = int(np.sum(~(dev <= R.LAW_LOCK_DT_TOL_S)))
        if n_bad:
            probs.append(f"R9-2.5: {n_bad} steps with |dt - 1 ms| > 1e-6 s (max {float(np.nanmax(dev)):.3e} s)")
    pat = law_locked_pattern(arr)
    if not pat["ok"] and pat["patterns"] != ["not_evaluated"]:
        probs.append("R9-2.6: -1 pattern " + "+".join(pat["patterns"]) + " (R9-3)")
    return probs


def law_locked_codes(problems) -> list:
    """Item codes (R.LAW_LOCK_ITEMS) of a problem list."""
    return sorted({p.split(":", 1)[0] for p in problems})


def _law_locked_from(npz, tkey, src):
    """Returns (array or None, problems, pattern). Key absent -> (None, [], None)."""
    if "law_locked" not in npz.files:
        return None, [], None
    arr = np.asarray(npz["law_locked"])
    t = npz[tkey] if tkey in npz.files else None
    probs = law_locked_check(arr, t)
    return (None if probs else arr), probs, law_locked_pattern(arr)


def law_lock_view(ll: np.ndarray):
    """rev6 6 / rev9 R9-3 reading of the plant lock state: 1 = locked, 0 = moving, -1 before the
    first arming = locked (only well-formed arrays reach here, so no -1 after arming). Returns
    (locked bool (n,4), samples per leg with -1 after the leg's first armed sample, always 0 here)."""
    ll = np.asarray(ll).astype(int)
    armed = ll != -1
    seen = np.maximum.accumulate(armed, axis=0)
    locked = (ll == 1) | (~seen)
    after = ((ll == -1) & seen).sum(axis=0).astype(int).tolist()
    return locked, after


# ----------------------------------------------------------------------------- tag (rules 4.1 / 6)
_V5O = {}


def _repo_of_tool() -> Path:
    here = Path(__file__).resolve().parent
    for p in [here] + list(here.parents):
        if (p / R.REPO_MARKER).exists():
            return p
    raise InputError("repository root not found (v5_options)")


def v5_options():
    """`03_src/outrigger_sim/hydraulics/v5_options.py` of this checkout (rules 4.1: the ③ reading
    of a tag is `is_extend_start_tag` only; the module is controller option code, not a path 1 tool)."""
    if "mod" not in _V5O:
        import importlib
        import sys
        src = _repo_of_tool() / "03_src"
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        mod = importlib.import_module("outrigger_sim.hydraulics.v5_options")
        f = Path(mod.__file__).resolve()
        if src.resolve() not in f.parents:
            raise InputError(f"v5_options imported from {f}, not from {src}")
        _V5O["mod"] = mod
    return _V5O["mod"]


def is_extend_start_tag(tag) -> bool:
    return bool(v5_options().is_extend_start_tag(tag))


def row_tag(row) -> dict:
    """Rules 4.1 / 6 / rev1 RV1-10 a: a Chrono row's tag is the argv `--expect-controller` value and
    the run's expect check must be true (SCM `c2_setup.expect_controller`, L2b / L1-R
    `expect_controller`). A recorded `name` different from the argv value also leaves the tag
    unestablished."""
    argv = row.argv
    tag = None
    if "--expect-controller" in argv:
        i = argv.index("--expect-controller")
        tag = argv[i + 1] if i + 1 < len(argv) else None
    if row.engine == "scm":
        ec = (row.result.get("c2_setup") or {}).get("expect_controller") or {}
    else:
        ec = row.result.get("expect_controller") or {}
    name = ec.get("name")
    est = tag is not None and ec.get("ok") is True and (name is None or name == tag)
    return {"tag": tag, "expect_ok": ec.get("ok"), "expect_name": name, "established": est}


def _quat_rp(q):
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    r20 = 2 * (x * z - w * y)
    r21 = 2 * (y * z + w * x)
    r22 = 1 - 2 * (x * x + y * y)
    return np.stack([np.degrees(np.arctan2(r21, r22)),
                     np.degrees(np.arcsin(np.clip(-r20, -1.0, 1.0)))], axis=-1)


def _events_from_json_list(lst, offset):
    out = []
    for e in lst or []:
        if isinstance(e, dict):
            out.append((float(e["t_s"]) + offset, str(e["name"])))
        elif isinstance(e, str):
            m = EVENT_RE.match(e.strip())
            if not m:
                raise InputError(f"unparsed event string: {e[:80]}")
            out.append((float(m.group(1)) + offset, m.group(2)))
        else:
            raise InputError(f"unknown event entry type {type(e).__name__}")
    out.sort(key=lambda x: x[0])
    return out


def _phases(lst, offset):
    out = []
    for p in lst or []:
        if isinstance(p, dict):
            out.append((float(p["t_s"]) + offset, str(p["phase"])))
        else:
            out.append((float(p[0]) + offset, str(p[1])))
    out.sort(key=lambda x: x[0])
    return out


def _floor_flat_from_label(label: str) -> bool:
    return label.strip().lower() == "flat"


def load_row(folder: Path, engine: str, argv=None) -> Row:
    folder = Path(folder)
    res_p = folder / "result.json"
    if not res_p.exists():
        raise InputError(f"no result.json in {folder}")
    res = json.loads(res_p.read_text(encoding="utf-8"))
    r8 = np.load(folder / "r8_series.npz")
    t10 = np.asarray(r8["t"], float)
    issued = np.asarray(r8["issued_u"], float)
    notes = []
    if engine == "scm":
        z = np.load(folder / "step_series.npz")
        tF = np.asarray(z["t_s"], float)
        F_inst = np.asarray(z["F_cyl_N"], float)
        F = F_inst
        s_motor = np.asarray(z["s_motor_m"], float)
        att = np.asarray(z["roll_pitch_deg"], float)
        t_att = tF
        cr = np.asarray(z["scm_crawler_normal_N"], float)
        t_cr = tF
        cr_basis = "1ms"
        pad_n = np.asarray(z["scm_pad_normal_N"], float)
        t_pad = tF
        sink = np.asarray(z["pad_sinkage_geometric_m"], float)
        t_sink = tF
        # rev8 R8-3 / R8-3a: SCM J11 plant lock state = step_series.npz law_locked on t_s (1 ms)
        law_locked, ll_probs, ll_pat = _law_locked_from(z, "t_s", "step_series.npz")
        ll_src = "step_series.npz law_locked" if "law_locked" in z.files else None
        offset = 0.0
        loop_start = float(res["t_loop_start_s"])
        phases = _phases(res.get("phases"), offset)
        events = _events_from_json_list(res.get("events"), offset)
        a = res.get("args", {})
        fr, fp = float(a.get("floor_roll") or 0.0), float(a.get("floor_pitch") or 0.0)
        flat = (fr == 0.0 and fp == 0.0)
        floor_label = f"roll {fr} pitch {fp}"
        target = (0.0, 0.0)
        # W: rev2 R2-5 names `p3b.weight_N` (the only key read from the p3b block)
        wN = (res.get("p3b") or {}).get("weight_N")
        w2 = ((res.get("mass_scale") or {}).get("judgement_weights") or {}).get("weight_N")
        if wN is None:
            raise InputError("p3b.weight_N missing (rev2 R2-5 W)")
        if w2 is not None and abs(float(w2) - float(wN)) > 1e-6:
            notes.append(f"p3b.weight_N {wN} != mass_scale.judgement_weights.weight_N {w2}")
        weight = float(wN)
        rut = [(float(r["t_s"]), r.get("rut_clearance_m")) for r in res.get("s9_rows") or []]
    else:
        pads = np.load(folder / "pads.npz")
        tF = np.asarray(pads["t"], float)
        F_inst = np.asarray(pads["F_cyl"], float)
        if "F_cyl_min_interval" in pads.files:
            F = np.asarray(pads["F_cyl_min_interval"], float)
            if "airborne" in pads.files and "F_cyl_mean_20ms" in pads.files:
                # rev6 R6-B2: S8-A2 judged force (airborne samples use the 20 ms mean)
                air = np.asarray(pads["airborne"], bool)
                F = np.where(air, np.asarray(pads["F_cyl_mean_20ms"], float), F)
                notes.append(f"S8-A2 airborne samples per leg: {air.sum(axis=0).astype(int).tolist()}")
        else:
            F = F_inst
            notes.append("F_cyl_min_interval absent: 1 ms sample used")
        s_motor = np.asarray(pads["s_motor"], float)
        rec = np.load(folder / "record" / "record.npz")
        if "body_quat_wxyz" in pads.files:
            att = _quat_rp(np.asarray(pads["body_quat_wxyz"], float))
            t_att = tF
        else:
            att = _quat_rp(np.asarray(rec["body_quat_wxyz"], float))
            t_att = np.asarray(rec["t"], float)
            notes.append("attitude from record.npz (10 Hz)")
        if "crawler_normal_N" in pads.files:
            cr = np.asarray(pads["crawler_normal_N"], float)
            t_cr = tF
            cr_basis = "1ms"
        else:
            cr = np.asarray(rec["F_crawler"], float)[:, 2]
            t_cr = np.asarray(rec["t"], float)
            cr_basis = "bracket_10Hz"
        pad_n = np.asarray(pads["N"], float) if "N" in pads.files else None
        t_pad = tF if pad_n is not None else None
        sink = None
        t_sink = None
        # rev8 R8-3a (rev4 R4-A2, rev6 R6-B7): L2b plant lock state = pads.npz law_locked on t (1 ms)
        law_locked, ll_probs, ll_pat = _law_locked_from(pads, "t", "pads.npz")
        ll_src = "pads.npz law_locked" if "law_locked" in pads.files else None
        st = res.get("settings", {})
        offset = float(st["start_t_s"])
        loop_start = offset
        phases = _phases(res.get("phases"), offset)
        ev_p = folder / "controller_events.json"
        # rev6 R6-1: controller_events.json is absolute Chrono time; phases are relative (+ start_t_s)
        events = _events_from_json_list(json.loads(ev_p.read_text(encoding="utf-8")) if ev_p.exists() else [], 0.0)
        floor_label = str(st.get("floor"))
        flat = _floor_flat_from_label(floor_label)
        tg = st.get("target_deg") or [0.0, 0.0]
        target = (float(tg[0]), float(tg[1]))
        weight = None
        rut = []
    # consistency check of the time base: the 10 Hz phase at the first 'touch' entry
    if "phase" in r8.files and phases:
        ph10 = [str(x) for x in r8["phase"]]
        for tp, name in phases[:3]:
            k = int(np.argmin(np.abs(t10 - tp)))
            if abs(t10[k] - tp) < 1e-6 and ph10[k] != name:
                raise InputError(f"time-base check failed: phase {name} at {tp} vs r8 {ph10[k]}")
    return Row(case=str(res.get("case") or folder.name), engine=engine, folder=folder, t_offset=offset,
               loop_start=loop_start, t_end=float(tF[-1]), tF=tF, F=F, F_inst=F_inst, s_motor=s_motor,
               t_att=t_att, att=att, t_cr=t_cr, cr=cr, cr_basis=cr_basis, t_pad=t_pad, pad_n=pad_n,
               t_sink=t_sink, sink=sink, law_locked=law_locked, t10=t10, issued=issued, phases=phases,
               events=events, floor_label=floor_label, flat=flat, target_deg=target, weight_N=weight,
               rut=rut, result=res, argv=list(argv or []), notes=notes,
               law_locked_source=ll_src, law_locked_problems=ll_probs, law_locked_pattern=ll_pat)


# ----------------------------------------------------------------------------- helpers
def dt_of(t):
    return float(np.median(np.diff(t))) if len(t) > 1 else 0.0


def first_phase_time(row: Row, name: str):
    for t, n in row.phases:
        if n == name:
            return t
    return None


def last_phase_time(row: Row, name: str):
    out = None
    for t, n in row.phases:
        if n == name:
            out = t
    return out


def phase_at(row: Row, t_query: np.ndarray) -> np.ndarray:
    tp = np.array([p[0] for p in row.phases])
    names = np.array([p[1] for p in row.phases] + ["<before>"])
    idx = np.searchsorted(tp, t_query, side="right") - 1
    idx = np.where(idx < 0, len(row.phases), idx)
    return names[idx]


def events_named(row: Row, prefix: str):
    return [(t, n) for t, n in row.events if n == prefix or n.startswith(prefix + ":")]


def leg_of(name: str):
    if ":" in name:
        s = name.split(":", 1)[1]
        for leg in R.LEGS:
            if s == leg or s.startswith(leg):
                return leg
    return None


def fault_present(row: Row, exclude_prefix=None):
    evs = [(t, n) for t, n in row.events if n.startswith("FAULT")]
    if exclude_prefix:
        evs = [(t, n) for t, n in evs if not n.startswith(exclude_prefix)]
    ph = [(t, n) for t, n in row.phases if n in R.FAULT_PHASES]
    return {"fault_events": [n for _, n in evs], "fault_phases": [n for _, n in ph],
            "any": bool(evs or ph)}


def runs_of(mask: np.ndarray):
    """[(i0, i1)] inclusive index runs where mask is True."""
    if mask.size == 0:
        return []
    m = mask.astype(np.int8)
    d = np.diff(np.concatenate([[0], m, [0]]))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    return list(zip(starts.tolist(), ends.tolist()))


def applied_moving(row: Row, t_query: np.ndarray) -> np.ndarray:
    """(n,4) bool: applied command |u| > 1e-6 m/s. The command issued at control instant
    t_k drives (t_k, t_{k+1}] (runner meta zero_order_hold; rev6 4.1 d = 1)."""
    k = np.searchsorted(row.t10, t_query, side="left") - 1
    ok = k >= 0
    u = np.zeros((len(t_query), 4))
    u[ok] = row.issued[k[ok]]
    return np.abs(u) > R.MOVING_U_EPS


# ----------------------------------------------------------------------------- times
def t_departure(row: Row):
    """P3-2 / rev2 R2-5: first sample of the first run with crawler normal < 0.01 W lasting
    >= 0.1 s (after loop start). Returns None if no such run or no 1 ms crawler / W."""
    if row.cr is None or row.weight_N is None:
        return None
    thr = R.W_FRACTION * row.weight_N
    sel = row.t_cr >= row.loop_start
    t = row.t_cr[sel]
    v = row.cr[sel]
    dt = dt_of(t)
    for i0, i1 in runs_of(np.array([R.lt(x, thr) for x in v])):
        if (i1 - i0 + 1) * dt >= R.DEPART_HOLD_S - R.CMP_TOL:
            return float(t[i0])
    return None


def t_lift(row: Row):
    """rev6 5: first 1 ms sample with phase not idle/check/touch and crawler normal <= 0.
    10 Hz fallback (rev6 R6-B1, L1-R): the first 10 Hz record row t_b with that condition;
    t_a (last > 0 row before it) is kept in `t_lift_bracket`."""
    return t_lift_bracket(row)[:2]


def t_lift_bracket(row: Row):
    if row.cr is None:
        return None, None, None
    ph = phase_at(row, row.t_cr)
    ok = ~np.isin(ph, list(R.TLIFT_SKIP_PHASES) + ["<before>"])
    le0 = np.array([R.le(x, 0.0) for x in row.cr])
    idx = np.where(ok & le0)[0]
    if idx.size == 0:
        return None, row.cr_basis, None
    i = int(idx[0])
    if row.cr_basis == "1ms":
        return float(row.t_cr[i]), "1ms", None
    t_a = float(row.t_cr[i - 1]) if i > 0 else None
    return float(row.t_cr[i]), "bracket_10Hz", t_a


def t_lift_sus(row: Row):
    """rev6 5: crawler <= 0.01 W held to the end of the run (start time). Record."""
    if row.cr is None or row.weight_N is None:
        return None
    thr = R.W_FRACTION * row.weight_N
    bad = np.where(np.array([R.gt(x, thr) for x in row.cr]))[0]
    if bad.size == 0:
        return float(row.t_cr[0])
    j = int(bad[-1]) + 1
    return float(row.t_cr[j]) if j < len(row.t_cr) else None


def loc_times(row: Row):
    locs = [t for t, _ in events_named(row, R.EVENT_LOC)]
    revs = [t for t, _ in events_named(row, R.EVENT_LOC_REVOKED)]
    final = None
    for t in locs:
        if not any(r >= t - R.CMP_TOL for r in revs):
            final = t
    # final = last LOC not followed by a revoke (424.8.1); revokes at the same instant revoke it
    return {"locs": locs, "revokes": revs, "first": locs[0] if locs else None, "final": final}


# ----------------------------------------------------------------------------- items
def min_force_after(row: Row, t0, t1=None, F_min=None):
    """Per-leg min of 1 ms true F_cyl over [t0, t1] (t1 = end). Also time below F_min and
    below F_min + 2 kN (count x dt, rev2 R2-5)."""
    if t0 is None:
        return None
    truncated = t1 is not None and t1 > row.t_end + R.CMP_TOL
    t1 = row.t_end if t1 is None else min(t1, row.t_end)
    sel = (row.tF >= t0 - R.CMP_TOL) & (row.tF <= t1 + R.CMP_TOL)
    if not sel.any():
        return None
    F = row.F[sel]
    tt = row.tF[sel]
    dt = dt_of(row.tF)
    mins = F.min(axis=0)
    arg = F.argmin(axis=0)
    out = {"t0": t0, "t1": t1, "truncated_at_run_end": bool(truncated),
           "min_N": mins.tolist(), "min_t_s": [float(tt[a]) for a in arg],
           "min_all_N": float(mins.min()), "min_leg": R.LEGS[int(mins.argmin())]}
    if F_min is not None:
        below = np.vectorize(lambda x: R.lt(x, F_min))(F)
        below2 = np.vectorize(lambda x: R.lt(x, F_min + R.FMIN_PLUS_N))(F)
        out["t_below_Fmin_s"] = (below.sum(axis=0) * dt).tolist()
        out["t_below_Fmin_plus2k_s"] = (below2.sum(axis=0) * dt).tolist()
        out["t_below_Fmin_max_s"] = float(max(out["t_below_Fmin_s"]))
        out["t_below_Fmin_plus2k_max_s"] = float(max(out["t_below_Fmin_plus2k_s"]))
    return out


def recontacts(row: Row, t_D):
    """Crawler >= 0.01 W runs after t_D (U-S9-G6d counting rule, 393)."""
    if t_D is None or row.cr is None or row.weight_N is None:
        return []
    thr = R.W_FRACTION * row.weight_N
    sel = row.t_cr >= t_D
    t = row.t_cr[sel]
    v = row.cr[sel]
    dt = dt_of(row.t_cr)
    out = []
    for i0, i1 in runs_of(np.array([R.ge(x, thr) for x in v])):
        out.append({"start_s": float(t[i0]), "end_s": float(t[i1]),
                    "duration_s": float(t[i1] - t[i0] + dt), "max_N": float(v[i0:i1 + 1].max())})
    return out


def classify_recontact(ev, t_loc_fin, t_ready, W):
    """U-S9-G6d (가) before the final LOC, 423.3 Q-G after it, strict after READY."""
    thr = R.W_FRACTION * W
    s, e, d, mx = ev["start_s"], ev["end_s"], ev["duration_s"], ev["max_N"]
    if t_ready is not None and s >= t_ready - R.CMP_TOL:
        return "strict_fail"
    if t_loc_fin is None:
        return "strict_fail"
    if s <= t_loc_fin + R.CMP_TOL:
        if R.le(d, R.TRANSIENT_MAX_S) and R.lt(e, t_loc_fin) and R.le(mx, R.TRANSIENT_MAX_W * W):
            return "transient_flag"
        return "strict_fail"
    if R.le(s, t_loc_fin + R.CHATTER_AFTER_LOC_S) and R.le(d, R.CHATTER_MAX_S) and R.le(mx, R.CHATTER_MAX_OVER * thr):
        return "threshold_chatter"
    return "strict_fail"


def p3_1(row: Row, t_D, locs):
    t_R = first_phase_time(row, "ready")
    out = {"clause": "spec 284 P3-1 + U-S9-G6d (393) + 423.3 Q-G + 424.8.1 (final LOC)"}
    evs = recontacts(row, t_D)
    for ev in evs:
        ev["class"] = classify_recontact(ev, locs["final"], t_R, row.weight_N)
    out["recontacts"] = evs
    strict = [e for e in evs if e["class"] == "strict_fail"]
    flags = sorted({"P3-1_transient_recontact" if e["class"] == "transient_flag" else "P3-1_threshold_chatter"
                    for e in evs if e["class"] != "strict_fail"})
    out["flags"] = flags
    if t_R is None:
        out.update(window_complete=False, verdict="indeterminate", reason="no READY (284.1)")
        return out
    w1 = t_R + R.READY_WINDOW_S
    complete = w1 <= row.t_end + R.CMP_TOL
    sel = (row.t_cr >= t_R - R.CMP_TOL) & (row.t_cr <= w1 + R.CMP_TOL)
    wmax = float(row.cr[sel].max()) if sel.any() else None
    out.update(t_ready_s=t_R, window_complete=bool(complete), ready_window_crawler_max_N=wmax)
    if strict or (wmax is not None and R.gt(wmax, 0.0)):
        out["verdict"] = "fail"
    elif not complete:
        out["verdict"] = "indeterminate"
        out["reason"] = "window_complete false (284.1)"
    else:
        out["verdict"] = "flag" if flags else "pass"
    return out


def reapproach_intervals(row: Row):
    """419.8.1: from leg_reapproach_start:<leg> to that leg's next contact / no-contact."""
    out = []
    starts = events_named(row, R.EVENT_REAPPROACH_START)
    ends = events_named(row, R.EVENT_REAPPROACH_CONTACT) + events_named(row, R.EVENT_REAPPROACH_NO_CONTACT)
    for ts, n in starts:
        leg = leg_of(n)
        te = None
        for t2, n2 in sorted(ends):
            if t2 >= ts - R.CMP_TOL and leg_of(n2) == leg:
                te = t2
                break
        out.append({"leg": leg, "start_s": ts, "end_s": te})
    return out


def p3_2(row: Row, t_D, locs, p33_pass, fault_any, params):
    T_lim = R.P32_WINDOW_M / (R.P32_SPEED_FRACTION * params["v_max_m_s"]) + R.P32_SLACK_S
    out = {"clause": "spec 284 P3-2 (U-S9P-13) + 419.8 / 419.8.1 + 424.8.1", "T_lim_s": T_lim,
           "T_lim_rule_text_s": R.P32_RULE_VALUE_S}
    t_loc = locs["final"]
    t_done = first_phase_time(row, "done")
    out.update(t_D_s=t_D, t_loc_final_s=t_loc, t_first_done_s=t_done, locs_s=locs["locs"], revokes_s=locs["revokes"])
    if t_loc is None:
        out.update(verdict="fail", reason="no confirmed LOC")
        return out
    order = (t_done is None) or (t_loc < t_done - R.CMP_TOL)
    thr = R.W_FRACTION * row.weight_N
    sel = (row.t_cr > t_loc - R.LOC_CYCLE_S + R.CMP_TOL) & (row.t_cr <= t_loc + R.CMP_TOL)
    cyc_max = float(row.cr[sel].max()) if sel.any() else None
    loaded_ok = cyc_max is not None and R.lt(cyc_max, thr)
    out.update(order_ok=order, loc_cycle_crawler_max_N=cyc_max, loaded_ok=loaded_ok)
    # rev3 R3-G10 Q-17: revoked LOCs under load are recorded only
    rev_loaded = []
    for tl in locs["locs"]:
        if tl == t_loc:
            continue
        s2 = (row.t_cr > tl - R.LOC_CYCLE_S + R.CMP_TOL) & (row.t_cr <= tl + R.CMP_TOL)
        if s2.any() and not R.lt(float(row.cr[s2].max()), thr):
            rev_loaded.append(tl)
    out["revoked_loc_under_load_record_s"] = rev_loaded
    if t_D is None:
        out.update(verdict="indeterminate", reason="t_D undefined")
        return out
    delay = t_loc - t_D
    time_ok = R.le(delay, T_lim)
    out.update(loc_minus_departure_s=delay, time_ok=time_ok)
    if not order or not loaded_ok:
        out["verdict"] = "fail"
        return out
    if time_ok:
        out["verdict"] = "pass"
        return out
    # 419.8 late LOC after reapproach
    iv = [i for i in reapproach_intervals(row)
          if i["start_s"] <= t_loc + R.CMP_TOL and (i["end_s"] is None or i["end_s"] >= t_D - R.CMP_TOL)]
    restarts = events_named(row, R.EVENT_LOC_WINDOW_RESTART)
    c1 = any(any(i["start_s"] - R.CMP_TOL <= t <= (i["end_s"] if i["end_s"] is not None else row.t_end) + R.CMP_TOL
                 for t, _ in restarts) for i in iv)
    c2_ends = [i["end_s"] for i in iv]
    t_re_end = None if (not iv or any(e is None for e in c2_ends)) else max(c2_ends)
    revs = [t for t in locs["revokes"] if t_D - R.CMP_TOL <= t <= t_loc + R.CMP_TOL]
    r1 = bool(revs)
    t_rev = max(revs) if revs else None
    c4 = bool(p33_pass) and not fault_any
    ref = [t_D]
    if c1 and t_re_end is not None:
        ref.append(t_re_end)
    if r1:
        ref.append(t_rev)
    c2 = R.le(t_loc - max(ref), T_lim)
    late = {"c1_window_restart": c1, "t_reapproach_end_s": t_re_end,
            "c2_delay_ok": bool(c2 and c1 and t_re_end is not None), "c3_not_false_loc": loaded_ok,
            "c4_load_fault": c4, "c5_order": order}
    # rev3 R3-G12: condition 6 (spec 424.9 decision 1): t_LOC_fin - t_off <= (1 + n_revoke) T_lim
    c6 = R.le(t_loc - t_D, (1 + len(revs)) * T_lim)
    rev = {"c1_revoke": r1, "t_revoke_last_s": t_rev, "c2_delay_ok": bool(c2 and r1),
           "c3": loaded_ok, "c4": c4, "c5": order, "c6_total_delay_ok": c6, "n_revoke": len(revs)}
    out["late_loc_reapproach"] = late
    out["late_loc_revoked"] = rev
    flags = []
    if all([late["c1_window_restart"], late["c2_delay_ok"], loaded_ok, c4, order]):
        flags.append("P3-2_late_loc_reapproach")
    if all([rev["c1_revoke"], rev["c2_delay_ok"], loaded_ok, c4, order, c6]):
        flags.append("P3-2_late_loc_revoked")
    out["flags"] = flags
    out["verdict"] = "flag" if flags else "fail"
    return out


def p3_3(row: Row, t_D, params):
    m = min_force_after(row, t_D, None, params["F_min_N"])
    out = {"clause": "spec 284 P3-3 (true F_cyl after departure >= F_min)"}
    if m is None:
        out.update(verdict="indeterminate", reason="t_D undefined")
        return out
    out.update(m)
    out["verdict"] = "pass" if R.ge(m["min_all_N"], params["F_min_N"]) else "fail"
    return out


def creep_stop_times(row: Row):
    """433.6 (v5): backward sinkage rate over 1.0 s; two-sided stop |v| < 0.1 mm/s on all pads.
    Returns (t_final_two_sided, t_final_signed)."""
    if row.sink is None:
        return None, None
    t = row.t_sink
    dt = dt_of(t)
    n = int(round(R.CREEP_RATE_WINDOW_S / dt))
    if len(t) <= n:
        return None, None
    v = (row.sink[n:] - row.sink[:-n]) / (t[n:] - t[:-n])[:, None]
    tv = t[n:]
    two = np.all(np.abs(v) < R.CREEP_STOP_M_S - R.CMP_TOL, axis=1)
    signed = np.all(v < R.CREEP_STOP_M_S - R.CMP_TOL, axis=1)

    def final_start(mask):
        if not mask[-1]:
            return None
        bad = np.where(~mask)[0]
        return float(tv[0]) if bad.size == 0 else float(tv[bad[-1] + 1])
    return final_start(two), final_start(signed)


def p3_4(row: Row):
    out = {"clause": "spec 284 P3-4 + 284.1 window + 433.6 (1.0 s rate, window_short FLAG)"}
    t_lr = last_phase_time(row, "ready")
    t2, ts = creep_stop_times(row)
    out.update(t_final_two_sided_s=t2, t_final_signed_s=ts, t_last_ready_s=t_lr)
    if t_lr is None:
        out.update(verdict="indeterminate", reason="no READY")
        return out
    flags = []
    base = t2
    if base is None:
        base = ts
        flags.append("creep_vibration_suspect")
        if base is None:
            out.update(verdict="indeterminate", reason="no creep stop (two-sided nor signed)", flags=flags)
            return out
    w0 = max(base, t_lr)
    length = row.t_end - w0
    sel = row.t_att >= w0 - R.CMP_TOL
    val = float(np.max(np.abs(row.att[sel] - np.array(row.target_deg)))) if sel.any() else None
    out.update(window_s=[w0, row.t_end], window_length_s=length, absmax_deg=val)
    if val is None:
        out.update(verdict="indeterminate", reason="empty window", flags=flags)
        return out
    within = R.le(val, R.ATT_LIMIT_DEG)
    out["absmax_within_0p2_record"] = within
    if not R.ge(length, R.P34_WINDOW_MIN_S):
        flags.append("window_short")
        # rev3 R3-G7: FLAG; item tally counts it as FLAG (not pass), row grade does not count it as fail
        out.update(flags=flags, verdict="flag", item_tally="flag_not_pass",
                   reason="window_short (433.6); value in absmax_within_0p2_record")
        return out
    out["flags"] = flags
    if not within:
        out["verdict"] = "fail"
    elif "creep_vibration_suspect" in flags:
        out["verdict"] = "flag"
    else:
        out["verdict"] = "pass"
    return out


def p3_5(row: Row):
    out = {"clause": "spec 284 P3-5 (U-S9P-14): rut clearance first READY..end >= 25 mm; motor stroke <= 0.6848 m"}
    t_R = first_phase_time(row, "ready")
    smax = float(row.s_motor.max())
    out.update(stroke_max_m=smax, stroke_max_leg=R.LEGS[int(row.s_motor.max(axis=0).argmax())],
               stroke_ok=R.le(smax, R.STROKE_END_M))
    vals = [c for t, c in row.rut if t_R is not None and t >= t_R - R.CMP_TOL and c is not None]
    out["clearance_min_m"] = float(min(vals)) if vals else None
    out["clearance_samples"] = len(vals)
    if t_R is None or not vals:
        out["clearance_ok"] = None
        out["verdict"] = "fail" if not out["stroke_ok"] else "indeterminate"
        out["reason"] = "no READY or no rut_clearance_m sample after READY"
        return out
    out["clearance_ok"] = R.ge(out["clearance_min_m"], R.CLEARANCE_MIN_M)
    out["verdict"] = "pass" if (out["clearance_ok"] and out["stroke_ok"]) else "fail"
    return out


def ready_item(row: Row, limit_s, clause, judged=True):
    t_R = first_phase_time(row, "ready")
    rel = None if t_R is None else t_R - row.loop_start
    v = "indeterminate" if rel is None else ("pass" if R.le(rel, limit_s) else "fail")
    if t_R is None:
        v = "fail" if judged else "record"
    return {"clause": clause, "t_ready_rel_s": rel, "limit_s": limit_s, "judged": judged,
            "verdict": v if judged else "record", "within": None if rel is None else R.le(rel, limit_s)}


def soil_mode_time(row: Row):
    c = row.result.get("c2_soil") or {}
    ts = c.get("soil_mode_t_s")
    starts = c.get("mode_starts") or []
    cand = []
    if ts is not None:
        cand.append(float(ts) + row.t_offset)
    for s in starts:
        if isinstance(s, dict):
            for k in ("t_s", "t"):
                if s.get(k) is not None:
                    cand.append(float(s[k]) + row.t_offset)
                    break
        elif isinstance(s, (int, float)):
            cand.append(float(s) + row.t_offset)
    return min(cand) if cand else None


def p3_8(row: Row, locs, params, fault_any, demote: bool, p33_pass=None):
    out = {"clause": "spec 284 P3-8 (before soil mode / LOC) + 377 demotion and U-S9-G6c "
                     "P3-8_preloc_loss (G6 rows, rev6 R6-C3); 377 window LOC = first LOC (rev6 R6-B3)"}
    t_soil = soil_mode_time(row)
    cands = [x for x in (locs["first"], t_soil) if x is not None]
    cut = min(cands) if cands else None
    out.update(cutoff_s=cut, t_soil_mode_s=t_soil, t_first_loc_s=locs["first"])
    evs = []
    for pre in R.EVENT_P38:
        evs += [(t, n) for t, n in events_named(row, pre) if cut is None or t < cut - R.CMP_TOL]
    evs.sort()
    out["events"] = [{"t_s": t, "name": n} for t, n in evs]
    if not evs:
        out["verdict"] = "pass"
        return out
    if not demote:
        out["verdict"] = "fail"
        return out
    demoted = []
    for t, n in evs:
        if not n.startswith(R.EVENT_REAPPROACH_START):
            demoted.append({"event": n, "demoted": False, "reason": "not a reapproach"})
            continue
        leg = leg_of(n)
        if leg is None or locs["first"] is None:
            demoted.append({"event": n, "demoted": False, "reason": "no leg or no LOC"})
            continue
        m = min_force_after(row, t, locs["first"] + 1.0)
        mn = m["min_N"][R.LEGS.index(leg)] if m else None
        a = mn is not None and R.ge(mn, params["F_min_N"]) and not fault_any  # rev3 R3-G8
        rec = {"event": n, "leg_min_N": mn, "preloc_flag_ok": a}
        # rev6 R6-B3 record: would the final-LOC window give another 377 result?
        if locs["final"] is not None and locs["final"] != locs["first"]:
            m2 = min_force_after(row, t, locs["final"] + 1.0)
            mn2 = m2["min_N"][R.LEGS.index(leg)] if m2 else None
            rec["final_loc_window_preloc_ok_record"] = mn2 is not None and R.ge(mn2, params["F_min_N"]) and not fault_any
        if a:
            rec.update(demoted=True, flag="P3-8_demoted", rule="377")
        elif p33_pass and not fault_any:
            rec.update(demoted=True, flag="P3-8_preloc_loss", rule="U-S9-G6c")
        elif p33_pass is None:
            rec.update(demoted=None, reason="G6-3 (P3-3) result missing")
        else:
            rec["demoted"] = False
        demoted.append(rec)
    out["demotion"] = demoted
    if any(d.get("demoted") is None and "reason" in d and d["reason"].startswith("G6-3") for d in demoted):
        out["verdict"] = "indeterminate"
    elif all(d.get("demoted") for d in demoted):
        out["verdict"] = "flag"
        out["flags"] = sorted({d["flag"] for d in demoted})
    else:
        out["verdict"] = "fail"
    return out


def p3_9(row: Row, params):
    out = {"clause": "spec 284 P3-9 (record): RT deferrals", "verdict": "record"}
    d = events_named(row, R.EVENT_DEFERRED)
    out["deferrals"] = len(d)
    rows = []
    starts = sorted(t for t, _ in events_named(row, R.EVENT_REAPPROACH_START))
    for t, n in d:
        leg = leg_of(n)
        nxt = [s for s in starts if s > t]
        t1 = (nxt[0] + 0.3) if nxt else row.t_end
        m = min_force_after(row, t, t1)
        rows.append({"t_s": t, "leg": leg, "min_N": None if (m is None or leg is None) else m["min_N"][R.LEGS.index(leg)]})
    out["rows"] = rows
    return out


def leg_lift(row: Row, t0):
    """Pad normal <= 0 after t0 (SCM pad normal / L2b 20 ms N). Definition chosen here."""
    if row.pad_n is None or t0 is None:
        return None
    sel = row.t_pad >= t0
    le0 = np.vectorize(lambda x: R.le(x, 0.0))(row.pad_n[sel])
    return {"t0": t0, "samples_per_leg": le0.sum(axis=0).astype(int).tolist(), "any": bool(le0.any())}


def pressure_item(row: Row, params, t_window=None):
    """Head-equivalent pressure F_cyl / A_p (spec J-5) in bar on the control-period rows of
    record/record.npz (rev6 R6-B5): moving = |u_applied| > 1e-9 (rev3 Q-13) <= 180 bar, all rows
    <= 350 bar (d1 11 D8.P). Peaks between control instants are not seen (disclosed limit)."""
    A = np.array(params["head_area_m2"])
    rp = row.folder / "record" / "record.npz"
    if not rp.exists():
        return {"clause": "rev6 R6-B5", "verdict": "indeterminate", "reason": "record/record.npz missing"}
    rec = np.load(rp)
    tr = np.asarray(rec["t"], float)
    p_bar = np.asarray(rec["F_cyl"], float) / A[None, :] / 1e5
    mov = np.abs(np.asarray(rec["u_applied"], float)) > R.MOVING_U_EPS
    if t_window is not None:
        sel = (tr >= t_window[0]) & (tr <= t_window[1])
        p_bar = p_bar[sel]
        mov = mov[sel]
    mmax = float(np.max(np.where(mov, p_bar, -np.inf))) if mov.any() else None
    amax = float(p_bar.max())
    out = {"clause": "d1 11 D8.P: moving <= 180 bar, locked <= 350 bar (head equivalent F_cyl/A_p)",
           "moving_max_bar": mmax, "all_max_bar": amax,
           "moving_ok": True if mmax is None else R.le(mmax, R.MOVING_BAR),
           "all_ok": R.le(amax, R.LOCKED_BAR)}
    out["verdict"] = "pass" if (out["moving_ok"] and out["all_ok"]) else "fail"
    return out


def d8_force(row: Row, params, rigid_nsc_hold: bool):
    tl, basis = t_lift(row)
    out = {"clause": "d1 11 D8.P / spec 3 item 3: after crawler lift-off all 1 ms F_cyl >= F_min; "
                     "R40-2 hold for rigid NSC crawler", "t_lift_s": tl, "t_lift_basis": basis}
    m = min_force_after(row, tl, None, params["F_min_N"])
    if m is None:
        out.update(verdict="indeterminate", reason="no crawler lift-off")
        return out
    out.update(m)
    ok = R.ge(m["min_all_N"], params["F_min_N"])
    out["verdict"] = "pass" if ok else "fail"
    if not ok and rigid_nsc_hold:
        t_min = min(m["min_t_s"][i] for i in range(4) if m["min_N"][i] == m["min_all_N"])
        in8 = t_min <= tl + R.HOLD_WINDOW_S + R.CMP_TOL
        sel = (row.tF >= tl) & (row.tF <= tl + R.HOLD_WINDOW_S)
        dt = dt_of(row.tF)
        n = max(1, int(round(R.HOLD_SLOW_MEAN_S / dt)))
        k = np.ones(n) / n
        # rev6 R6-B2: slow component = 1 s centred mean of the same judged force
        slow = np.stack([np.convolve(row.F[:, j], k, mode="same") for j in range(4)], axis=1)
        smin = float(slow[sel].min()) if sel.any() else None
        out["hold_check"] = {"min_in_8s": in8, "slow_min_N": smin}
        thr = params["F_min_N"] + R.HOLD_SLOW_MARGIN_N
        out["hold_check"]["slow_threshold_N"] = thr
        if in8 and smin is not None and R.ge(smin, thr):
            out["verdict"] = "hold"
            out["stop"] = "R40-2 hold: resolve with the d1 rules 8 L1 pair (spec 7155) or ask (rev3 R3-G6)"
    return out


def d8_end_attitude(row: Row):
    out = {"clause": "spec 3 item 2: last 5 s (after first READY, standstill) max |att - target| + 0.02 <= 0.2"}
    t_R = first_phase_time(row, "ready")
    w0 = row.t_end - R.D8_LAST_WINDOW_S
    if t_R is None or t_R > w0 + R.CMP_TOL:
        out.update(verdict="indeterminate", reason="first READY not before the last 5 s")
        return out
    phs = set(phase_at(row, row.t10[(row.t10 >= w0) & (row.t10 <= row.t_end)]).tolist())
    out["phases_in_window"] = sorted(phs)
    sel = row.t_att >= w0 - R.CMP_TOL
    val = float(np.max(np.abs(row.att[sel] - np.array(row.target_deg))))
    out.update(window_s=[w0, row.t_end], absmax_deg=val, with_mount_deg=val + R.D8_MOUNT_DEG)
    if phs != {"ready"}:
        out.update(verdict="indeterminate", reason="last 5 s not all in READY")
        return out
    out["verdict"] = "pass" if R.le(val + R.D8_MOUNT_DEG, R.ATT_LIMIT_DEG) else "fail"
    return out


def stroke_guard_class(row: Row):
    w = events_named(row, R.EVENT_STROKE_LIMITED)
    f = events_named(row, R.EVENT_STROKE_STOP)
    return {"warn_lift_stroke_limited": len(w), "fault_lift_stroke_limit": [n for _, n in f],
            "fault_stroke_end": len(events_named(row, "FAULT_STROKE_END"))}


def stop_classification(row: Row, t_D, params):
    """427.12.5 SA-4 / 427.12.1 1: soil stroke-guard stop (FAULT_LIFT_STROKE_LIMIT:soil)."""
    f = [(t, n) for t, n in events_named(row, R.EVENT_STROKE_STOP) if n.endswith(":soil")]
    if not f:
        return None
    t_stop = f[0][0]
    thr = R.W_FRACTION * row.weight_N
    k = int(np.searchsorted(row.t_cr, t_stop))
    k = min(k, len(row.cr) - 1)
    cr_stop = float(row.cr[k])
    after = row.cr[row.t_cr >= t_stop]
    m = min_force_after(row, t_stop, None)
    other_faults = [n for n in fault_present(row, exclude_prefix=R.EVENT_STROKE_STOP)["fault_events"]]
    lift = leg_lift(row, t_stop)   # rev6 R6-B9 / rev4 R4-B1: pad normal <= 0 from the stop to the end
    press = pressure_item(row, params)
    conds = {
        "ready_none": first_phase_time(row, "ready") is None,
        "no_fault_stroke_end": not events_named(row, "FAULT_STROKE_END"),
        "no_other_fault": not other_faults,
        "min_after_stop_ge_Fmin": m is not None and R.ge(m["min_all_N"], params["F_min_N"]),
        "crawler_no_increase": bool(np.all([R.le(x, cr_stop + thr) for x in after])),
        "no_leg_lift": lift is not None and not lift["any"],
        "moving_le_180bar": press["moving_ok"],
    }
    departed = t_D is not None and t_D <= t_stop + R.CMP_TOL
    loaded = R.gt(cr_stop, thr)
    cls = "stroke_limited_stop" if (all(conds.values()) and departed and not loaded) else "fail"
    return {"clause": "spec 427.12.5 SA-4, 427.12.1 1", "t_stop_s": t_stop, "crawler_at_stop_N": cr_stop,
            "departed": departed, "stop_with_crawler_loaded": loaded, "conditions": conds, "class": cls}


def rc_from_record(row: Row):
    """rules 2 R_c from the recorded crawler attitude (9.1 C-8 row): p3b_ext.start_condition.crawler_attitude_deg."""
    sc = ((row.result.get("p3b_ext") or {}).get("start_condition") or {})
    a = sc.get("crawler_attitude_deg")
    if a is None:
        return None
    phi, th = float(a[0]), float(a[1])
    return {"crawler_attitude_deg": [phi, th], "R_c": abs(phi) / R.RC_PHI_DEG + abs(th) / R.RC_THETA_DEG}


def k1_classification(row: Row, las_off: bool = False):
    """rules 7.2 + rev2 R2-1 / R2-2 (Chrono: controller_meta)."""
    cm = row.result.get("controller_meta")
    out = {"clause": "rules 7.2, rev2 R2-1 / R2-2"}
    if cm is None:
        out.update(cls="indeterminate", reason="controller_meta missing")
        return out
    las = cm.get("liftoff_approach_slow")
    if las_off:
        las_state = "las_none"
    elif las is None:
        out.update(cls="indeterminate", reason="liftoff_approach_slow block missing (9.3)")
        return out
    elif "start_s" not in las or las.get("start_s") is None:
        las_state = "not_started"
    else:
        las_state = "started"
    scm = cm.get("slope_clearance_margin") or {}
    dec = ((scm.get("order_gate") or {}).get("decisions"))
    if dec is None:
        out.update(cls="indeterminate", reason="order_gate.decisions missing")
        return out
    conflict = [d for d in dec if (d.get("would_block") and not d.get("r4_due_without_gate"))
                or (d.get("applied") and not d.get("r4_due_without_gate"))
                or (d.get("applied") and d.get("would_block"))]
    blocks = [d for d in dec if d.get("would_block") and d.get("r4_due_without_gate")]
    skipped = len(events_named(row, "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"))
    out.update(las_state=las_state, n_decisions=len(dec), n_blocks=len(blocks), n_conflicts=len(conflict),
               n_skipped_order_events=skipped)
    if conflict:
        out.update(cls="indeterminate", stop="S-5", reason="record conflict (R2-1)")
        return out
    if blocks and skipped != len(blocks):
        out.update(cls="indeterminate", stop="S-5", reason="_SKIPPED:order count != blocks")
        return out
    started = las_state == "started"
    if las_state == "las_none":
        out["cls"] = "las_none_k1_block" if blocks else "las_none_inactive"
    elif started and blocks:
        out["cls"] = "both"
    elif started:
        out["cls"] = "las_active"
    elif blocks:
        out["cls"] = "k1_block"
    else:
        out["cls"] = "inactive"
    return out


# ----------------------------------------------------------------------------- re-aggregation
# rev3 R3-G1 (Q-C1 = A): monitor / event-logic items are re-aggregated from the per-item record in
# result.json; path 2 applies the grade rules itself. Not an independent recomputation (disclosed).
REAGG_ALIASES = {
    "T4-0": ("T4-0", "T4_0", "t4_0"), "T4": ("T4", "t4"), "T5": ("T5", "t5"),
    "J11_window": ("J11", "j11"), "J-P3": ("J-P3", "J_P3", "jp3", "j_p3"), "D2": ("D2", "d2"),
    **{f"E-{k}": (f"E-{k}", f"E{k}", f"E_{k}") for k in range(1, 8)},
}
PASS_WORDS = {"pass", "passed", "ok", "true", "통과", "일치", "match"}
FAIL_WORDS = {"fail", "failed", "false", "실패", "불일치", "미달", "mismatch"}


def _find_key(o, names, path="", depth=0):
    if depth > 8 or not isinstance(o, dict):
        return None
    for k, v in o.items():
        if k in names:
            return f"{path}.{k}" if path else k, v
    for k, v in o.items():
        if isinstance(v, dict):
            hit = _find_key(v, names, f"{path}.{k}" if path else k, depth + 1)
            if hit:
                return hit
    return None


def _verdict_of(v):
    if isinstance(v, bool):
        return "pass" if v else "fail"
    if isinstance(v, str):
        s = v.strip().lower()
        if s.startswith("flag"):
            return "flag"
        if s in PASS_WORDS:
            return "pass"
        if s in FAIL_WORDS:
            return "fail"
        return None
    if isinstance(v, dict):
        for k in ("verdict", "status", "result", "passed", "ok", "pass"):
            if k in v and v[k] is not None:
                r = _verdict_of(v[k])
                if r:
                    return r
    return None


def reagg_item(row: Row, item: str) -> dict:
    hit = _find_key(row.result, set(REAGG_ALIASES[item]))
    out = {"layer": "re-aggregated (rev3 R3-G1)", "item": item}
    if hit is None:
        out.update(verdict="indeterminate", source=None, reason="per-item record not found in result.json")
        return out
    path, v = hit
    vv = _verdict_of(v)
    out.update(source=path, recorded_verdict=vv)
    out["verdict"] = vv if vv in ("pass", "fail", "flag") else "indeterminate"
    if out["verdict"] == "indeterminate":
        out["reason"] = "recorded value not readable as pass / fail / flag"
    return out


def extend_start_rule(row: Row):
    """rev8 R8-2: the running controller's ③ rule = `controller_meta.two_pressure.settings.extend_start_rule`
    (None when the key is absent)."""
    tp = (row.result.get("controller_meta") or {}).get("two_pressure") or {}
    return (tp.get("settings") or {}).get("extend_start_rule")


def reagg_table(rows: list) -> list:
    """TABLE_REAGG (rev3 R3-G1): per re-aggregated item, rows, sources and verdict counts."""
    tab = {}
    for r in rows:
        for k, it in r["items"].items():
            if isinstance(it, dict) and str(it.get("layer", "")).startswith("re-aggregated"):
                e = tab.setdefault(k, {"item": k, "rows": 0, "sources": set(), "verdicts": {}})
                e["rows"] += 1
                if it.get("source"):
                    e["sources"].add(it["source"])
                e["verdicts"][it["verdict"]] = e["verdicts"].get(it["verdict"], 0) + 1
    return [{**e, "sources": sorted(e["sources"])} for e in tab.values()]


def row_status(items: dict, judged_keys) -> str:
    """rules 8.1 per row: indeterminate > fail > pass (flag / allowed counts as pass)."""
    vs = [items[k]["verdict"] for k in judged_keys if k in items]
    if any(v in ("indeterminate", "hold") for v in vs):
        return "판정 불가"
    if any(v == "fail" for v in vs):
        return "미달"
    return "통과"


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return str(o)
    if isinstance(o, Path):
        return str(o)
    return o
