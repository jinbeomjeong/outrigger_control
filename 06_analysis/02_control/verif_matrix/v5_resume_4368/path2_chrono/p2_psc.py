"""C-2 PS-c rows: spec 426.3 study A rows E-1..E-7 on one Chrono SCM row (rev4 R4-A2, rev18 R18-3 1).

- E-1..E-6 are recomputed from the raw record (R4-A2 option b): `soil_event_series.npz` 1 ms rows (pad contact
  normal, F_cyl, valve output, gap, true roll / pitch, crawler normal), `result.json` `phases` / `events` /
  `s9_rows` / `soil_event.spec` / `soil_event.driver` / `soil_event.event_reached`, `step_series.npz`
  `s_motor_m`. The runner's `soil_event.judgement` block is never read.
- E-7 comes from the path 2 run of the designated tool (`p2_e7.py`, R4-A2 option c); path 2 applies the
  grade itself (bundles <= 1).
- Any item that cannot be computed is `indeterminate`, so the row is 판정 불가 (R18-3: no empty item passes).

Branch of 426.3 read on the Chrono row: from t_ev - 0.5 s; it ends at the first control instant
t >= t_ev + max(12 s, ramp + 3 s) with READY held >= 3 s since the first READY instant after t_ev, else at
t_ev + 60 s. The items use the rows of [t_ev - 0.5, branch end]; times below are relative to t_ev.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import p2_core as C
import p2_rules as R

E_KEYS = ("E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7")


def _ind(reason, **kw):
    return {"verdict": "indeterminate", "reason": reason, **kw}


def load_event(row) -> tuple[dict | None, str | None]:
    """Event description and the 1 ms rows. Returns (event, None) or (None, reason)."""
    se = row.result.get("soil_event")
    p = row.folder / "soil_event_series.npz"
    if not isinstance(se, dict):
        return None, "no soil_event block in result.json (row without a soil event, e.g. a PS-c base run)"
    if not p.exists():
        return None, "soil_event_series.npz missing"
    spec, drv = se.get("spec") or {}, se.get("driver") or {}
    if se.get("event_reached") is not True:
        return None, f"soil_event.event_reached = {se.get('event_reached')!r}"
    try:
        t_ev = float(drv["t_ev_s"])
        depth, ramp = float(spec["depth_m"]), float(spec["ramp_s"])
        leg = str(spec["leg"])
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"soil_event spec / driver key missing: {exc!r}"
    if leg not in R.LEGS:
        return None, f"event leg {leg!r}"
    z = np.load(p)
    cols = [str(c) for c in z["columns"]] if "columns" in z.files else None
    if cols != list(R.E_ROW_COLUMNS) or "rows" not in z.files:
        return None, f"soil_event_series columns {cols} != {list(R.E_ROW_COLUMNS)}"
    rows = np.asarray(z["rows"], float)
    if rows.ndim != 2 or rows.shape[1] != len(R.E_ROW_COLUMNS) or len(rows) < 2:
        return None, f"soil_event_series rows shape {rows.shape}"
    t = rows[:, 0]
    dt = np.diff(t)
    if np.any(np.abs(dt - 1e-3) > R.LAW_LOCK_DT_TOL_S):
        return None, "soil_event_series time column not 1 ms"
    if abs(t[0] - (t_ev - R.E_PRE_S)) > 1.5e-3:
        return None, f"series start {t[0]} != t_ev - 0.5 s ({t_ev - R.E_PRE_S})"
    eid = str(spec.get("event_id"))
    speed = "slow" if eid in R.E_SLOW_EVENTS else ("fast" if eid in R.E_FAST_EVENTS else None)
    if speed is None:
        return None, f"event id {eid!r} not in 426.3 (slow {R.E_SLOW_EVENTS}, fast {R.E_FAST_EVENTS})"
    return {"event_id": eid, "speed": speed, "leg": leg, "t_ev_s": t_ev, "depth_m": depth, "ramp_s": ramp,
            "rows": rows, "series_end_s": float(t[-1])}, None


def branch_end(row, ev) -> dict:
    """426.3 branch end on the 10 Hz control instants (see module docstring)."""
    t_ev = ev["t_ev_s"]
    min_after = max(R.E_MIN_AFTER_S, ev["ramp_s"] + R.E_SLOW_TAIL_S)
    tk = row.t10[(row.t10 > t_ev + R.CMP_TOL) & (row.t10 < t_ev + R.E_MAX_AFTER_S + R.CMP_TOL)]
    ph = C.phase_at(row, tk) if tk.size else np.array([])
    ready_since = None
    for t, p in zip(tk, ph):
        if p != "ready":
            ready_since = None
            continue
        if ready_since is None:
            ready_since = float(t)
        if t >= t_ev + min_after - R.CMP_TOL and t - ready_since >= R.E_READY_HOLD_S - R.CMP_TOL:
            return {"t_end_s": float(t), "reason": "ready_held", "min_after_s": min_after}
    return {"t_end_s": t_ev + R.E_MAX_AFTER_S, "reason": "max_60s", "min_after_s": min_after}


def _runs(mask):
    return C.runs_of(np.asarray(mask, bool))


def _lift_stats(lifted_col, t_rel):
    """Lift sum [s] (samples x 1 ms) and last touch-down [s after the event] of one leg after the event."""
    runs = _runs(lifted_col)
    n = int(np.asarray(lifted_col, bool).sum())
    if not runs:
        return {"sum_s": 0.0, "n_runs": 0, "last_touch_s": 0.0, "lifted_at_end": False}
    i0, i1 = runs[-1]
    at_end = i1 == len(t_rel) - 1
    return {"sum_s": n * 1e-3, "n_runs": len(runs), "first_s": float(t_rel[runs[0][0]]),
            "last_touch_s": None if at_end else float(t_rel[i1 + 1]), "lifted_at_end": bool(at_end)}


def e_items(row, params, e7=None) -> tuple[dict, list]:
    """Items E-1..E-7 (+ records) of one PS-c row and the judged keys."""
    ev, why = load_event(row)
    if ev is None:
        items = {k: _ind(why, clause="426.3 / rev4 R4-A2") for k in E_KEYS}
        return items, list(E_KEYS)
    be = branch_end(row, ev)
    t_ev, rows = ev["t_ev_s"], ev["rows"]
    t_end = be["t_end_s"]
    truncated = ev["series_end_s"] < t_end - R.CMP_TOL
    sel = rows[:, 0] <= t_end + R.CMP_TOL
    rw = rows[sel]
    t_rel = rw[:, 0] - t_ev
    contact, F, valve, gap = rw[:, 1:5], rw[:, 5:9], rw[:, 9:13], rw[:, 13:17]
    att, cr = rw[:, 17:19], rw[:, 19]
    after = t_rel >= -R.CMP_TOL
    lifted = (contact <= R.CMP_TOL) & after[:, None]          # Q-14: pad normal <= 0 (7.6 tolerance)
    fast = ev["speed"] == "fast"
    li = R.LEGS.index(ev["leg"])
    pair = [ev["leg"], R.E_DIAG[ev["leg"]]]
    adj = [g for g in R.LEGS if g not in pair]
    per_leg = {g: _lift_stats(lifted[:, R.LEGS.index(g)], t_rel) for g in R.LEGS}
    base = {"event": {k: ev[k] for k in ("event_id", "speed", "leg", "t_ev_s", "depth_m", "ramp_s")},
            "branch": dict(be, rows=int(sel.sum()), truncated_by_run_end=bool(truncated))}
    items = {"E_branch": dict(base, verdict="record", clause="426.3 branch (path 2 reading on the Chrono row)")}

    # E-1
    if fast:
        pl = {g: per_leg[g] for g in pair}
        sum_ok = all(R.le(v["sum_s"], R.E1_LIFT_SUM_S) for v in pl.values())
        touch_ok = all(v["last_touch_s"] is not None and R.le(v["last_touch_s"], R.E1_LAST_TOUCH_S)
                       for v in pl.values())
        union = _runs(lifted[:, [R.LEGS.index(g) for g in pair]].any(axis=1))
        items["E-1"] = {"clause": "426.3 E-1 fast: event leg + diagonal, per leg lift sum <= 1.8 s, last touch-down "
                                  "<= event + 3.0 s (pair union recorded)", "pair": pair, "per_leg": pl,
                        "pair_union_s": sum(b - a + 1 for a, b in union) * 1e-3,
                        "verdict": "pass" if (sum_ok and touch_ok) else "fail"}
    else:
        items["E-1"] = {"clause": "426.3 E-1 slow: no lift on any leg after the event",
                        "lift_samples_per_leg": lifted.sum(axis=0).astype(int).tolist(),
                        "verdict": "fail" if lifted.any() else "pass"}

    # window W (fast) / event window (slow)
    if fast:
        lt = [per_leg[g]["last_touch_s"] for g in pair if per_leg[g]["n_runs"]]
        if any(x is None for x in lt):
            w_end = None
        else:
            w_end = min((max(lt) if lt else 0.0) + R.E2_T3_S, R.E2_W_CAP_S)
    else:
        w_end = ev["ramp_s"] + R.E_SLOW_TAIL_S
    items["E_branch"]["window_end_s"] = w_end

    # E-2
    if not fast:
        items["E-2"] = {"clause": "426.3 E-2 (U57) fast events only", "verdict": "not_applicable"}
    elif w_end is None:
        items["E-2"] = _ind("pair leg lifted to the branch end: W not defined", clause="426.3 E-2")
    else:
        ia = [R.LEGS.index(g) for g in adj]
        inW = after & (t_rel <= w_end + R.CMP_TOL)
        outW = t_rel > w_end + R.CMP_TOL
        la = lifted[:, ia]
        s_in = float((la & inW[:, None]).sum() * 1e-3)
        g_in = float(gap[:, ia][la & inW[:, None]].max()) if (la & inW[:, None]).any() else 0.0
        s_out = float((la & outW[:, None]).sum() * 1e-3)
        g_out = float(gap[:, ia][la & outW[:, None]].max()) if (la & outW[:, None]).any() else 0.0
        fs_N = 1000.0 * float(row.result.get("fs_kN") if row.result.get("fs_kN") is not None
                              else (row.result.get("args") or {}).get("fs_kN"))
        ok_in = R.le(s_in, R.E2_SUM_S) and R.le(g_in, R.E2_GAP_M)
        lowf = (R.lt(fs_N, R.E2_LOWF_FS_N) and s_out > 0.0 and R.le(s_out, R.E2_LOWF_SUM_S)
                and R.le(g_out, R.E2_LOWF_GAP_M))
        v = "fail" if not ok_in else ("pass" if s_out == 0.0 else ("flag" if lowf else "fail"))
        items["E-2"] = {"clause": "426.3 E-2 (U57) adjacent legs: W = [0, min(pair last touch-down + 0.82, 5) s], "
                                  "lift sum in W <= 0.5 s, gap <= 2 mm, outside W lift 0 (U-S8-75 F_s < 2 kN FLAG)",
                        "adjacent": adj, "W_end_s": w_end, "lift_sum_in_W_s": s_in, "gap_max_in_W_m": g_in,
                        "lift_sum_outside_W_s": s_out, "gap_max_outside_W_m": g_out, "front_Fs_N": fs_N,
                        "flags": ["U-S8-75 low friction exception"] if v == "flag" else [], "verdict": v}

    # E-3
    if w_end is None:
        items["E-3"] = _ind("W not defined", clause="426.3 E-3")
    else:
        post = (t_rel > w_end + R.CMP_TOL) if fast else after
        if not post.any():
            items["E-3"] = _ind("no 1 ms row in the E-3 window", clause="426.3 E-3")
        else:
            mins = F[post].min(axis=0)
            items["E-3"] = {"clause": "426.3 E-3: four legs 1 ms actual F_cyl >= F_min after W (fast) / after the "
                                      "event (slow) to the end", "min_N": mins.tolist(), "F_min_N": params["F_min_N"],
                            "verdict": "pass" if R.ge(float(mins.min()), params["F_min_N"]) else "fail"}

    # E-4
    if w_end is None:
        items["E-4"] = _ind("event window not defined", clause="426.3 E-4")
    else:
        A = np.array(params["head_area_m2"])
        p_bar = F / A[None, :] / 1e5
        inw = after & (t_rel <= w_end + R.CMP_TOL)
        outw = after & (t_rel > w_end + R.CMP_TOL)
        mov = np.abs(valve) > R.E4_MOVING_EPS_M_S
        ext = valve > R.E4_MOVING_EPS_M_S
        wmax = p_bar[inw].max(axis=0).tolist() if inw.any() else None
        mo = outw[:, None] & mov
        mmax = float(p_bar[mo].max()) if mo.any() else None
        sat = int((outw[:, None] & ext & (p_bar >= R.SATURATION_BAR - R.CMP_TOL)).sum())
        ok = (wmax is not None and all(R.le(x, R.E4_WINDOW_BAR) for x in wmax)
              and (mmax is None or R.le(mmax, R.E4_MOVING_BAR)) and sat == 0)
        items["E-4"] = {"clause": "426.3 E-4: in the event window F_cyl/A_p <= 350 bar per leg; outside it moving "
                                  "samples (|u| > 1e-6 m/s) <= 180 bar and saturation 0 (extending, >= 210 bar)",
                        "window_end_s": w_end, "window_max_bar": wmax, "moving_outside_max_bar": mmax,
                        "saturation_outside_ms": sat,
                        "verdict": "indeterminate" if wmax is None else ("pass" if ok else "fail")}
        if wmax is None:
            items["E-4"]["reason"] = "no row in the event window"

    # E-5
    ph_end = str(C.phase_at(row, np.array([t_end]))[0])
    tail = rw[:, 0] >= t_end - R.E5_END_MEAN_S - R.CMP_TOL
    m_att = np.abs(att[tail].mean(axis=0)) if tail.any() else None
    fevs = [n for t, n in row.events if n.startswith("FAULT") and t <= t_end + R.CMP_TOL]
    fph = [n for t, n in row.phases if n in R.FAULT_PHASES and t <= t_end + R.CMP_TOL]
    smask = row.tF <= t_end + R.CMP_TOL
    smax = float(row.s_motor[smask].max()) if smask.any() else None
    e5 = {"clause": "426.3 E-5: ends in READY, last 1 s mean |roll|, |pitch| <= 0.2 deg, FAULT 0, run maximum "
                    "stroke <= 684.8 mm (start .. branch end)", "phase_at_end": ph_end,
          "end_mean_abs_deg": None if m_att is None else m_att.tolist(), "fault_events": fevs,
          "fault_phases": fph, "stroke_max_m": smax}
    if truncated:
        e5.update(verdict="indeterminate", reason="run ended before the 426.3 branch end")
    elif m_att is None or smax is None:
        e5.update(verdict="indeterminate", reason="no rows for the end state")
    else:
        ok = (ph_end == "ready" and all(R.le(float(x), R.ATT_LIMIT_DEG) for x in m_att) and not fevs and not fph
              and R.le(smax, R.E5_STROKE_M))
        e5["verdict"] = "pass" if ok else "fail"
    items["E-5"] = e5

    # E-6
    loaded = after & np.array([R.gt(float(x), 0.0) for x in cr])
    if w_end is None:
        items["E-6"] = _ind("W not defined", clause="426.3 E-6")
    else:
        in_ms = int((loaded & (t_rel <= w_end + R.CMP_TOL)).sum()) if fast else 0
        out_ms = int((loaded & (t_rel > w_end + R.CMP_TOL)).sum()) if fast else int(loaded.sum())
        end_load = float(cr[-1])
        rut = [(t, c) for t, c in row.rut if c is not None and t <= t_end + R.CMP_TOL]
        clear = float(rut[-1][1]) if rut else None
        e6 = {"clause": "426.3 E-6 (confirmed 2026-10-30): recontact in W of a fast event FLAG; outside W / after a "
                        "slow event 0; end crawler load 0 and all-node clearance >= 25 mm (0 < c < 25 mm FLAG)",
              "contact_in_W_ms": in_ms, "contact_outside_ms": out_ms, "end_load_N": end_load,
              "end_clearance_m": clear, "end_clearance_t_s": rut[-1][0] if rut else None, "flags": []}
        if truncated or clear is None:
            e6.update(verdict="indeterminate", reason="run ended before the branch end" if truncated
                      else "no s9_rows rut_clearance_m up to the branch end")
        elif out_ms > 0 or R.gt(end_load, 0.0) or R.le(clear, 0.0):
            e6["verdict"] = "fail"
        else:
            if in_ms > 0:
                e6["flags"].append("E-6_event_transient_recontact")
            if R.lt(clear, R.E6_CLEAR_M):
                e6["flags"].append("E-6_post_event_clearance")
            e6["verdict"] = "flag" if e6["flags"] else "pass"
        items["E-6"] = e6

    # E-7 (tool output, option c)
    items["E-7"] = e7_item(row, e7)
    # records (d1 11 "DSb75 기록", 426.3 기록)
    items["E_records"] = {"verdict": "record",
                          "diff_sink_events": [n for t, n in row.events if n.startswith("INFO_DIFF_SINK")],
                          "loc_revokes_after_event": sum(1 for t, n in row.events
                                                         if n.startswith(R.EVENT_LOC_REVOKED) and t >= t_ev)}
    keys = [k for k in E_KEYS if items[k]["verdict"] != "not_applicable"]
    return items, keys


def e7_item(row, doc) -> dict:
    """E-7 from the path 2 run of the designated tool (`p2_e7.py` output); grade by path 2: bundles <= 1."""
    out = {"clause": "426.3 E-7 (248.3): twist-work bundles > +20 J <= 1; tool run by path 2 (rev4 R4-A2 c)",
           "layer": "tool-run (rev4 R4-A2 c)"}
    if doc is None:
        return dict(out, **_ind("E-7 tool output not given (--aux e7=<e7_path2.json>)"))
    gate = doc.get("tool_gate") or {}
    if not gate.get("ok"):
        return dict(out, **_ind("E-7 tool gate failed (rev4 R4-A2 condition 1)"),
                    stop="S-11 (rev4 R4-A2 condition 1: E-7 tool gate)")
    rec = (doc.get("rows") or {}).get(row_key(row.folder))
    if not isinstance(rec, dict):
        return dict(out, **_ind("row not in the E-7 tool output"))
    if rec.get("error"):
        return dict(out, **_ind(f"E-7 tool error: {rec['error']}"))
    tw = rec.get("twist") or {}
    nb = tw.get("n_bundles")
    if not isinstance(nb, int):
        return dict(out, **_ind("twist.n_bundles missing in the tool output"))
    return dict(out, n_bundles=nb, bundles=tw.get("bundles"), bins_J=tw.get("bins_J"),
                verdict="pass" if nb <= R.E7_MAX_BUNDLES else "fail")


def row_key(folder) -> str:
    return str(Path(folder).resolve()).lower()


def load_e7(path) -> dict | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))
