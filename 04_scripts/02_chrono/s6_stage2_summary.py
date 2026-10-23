"""S6 stage-2 summary: pre-judgement of checks 1-8, T, R; shadow floor table; figures.

Usage (Chrono-dev python)::

    python -I -X utf8 s6_stage2_summary.py <batch dir> [<override batch dir> ...] [--tag NAME]
        [--jobs N] [--placement os|ecore|pcore]

* ``<batch dir>``: stage-2 batch (``07_results/S6/stage2_<stamp>``).
* ``<override batch dir>`` (optional, any number, applied in order): case directories of a
  later batch replace the case directories of the same name. When the merged cases carry
  different C2 revisions (``result.json`` ``controller_meta.revision``) the meta says
  ``mixed_revisions: true`` with the revision per batch and a warning, and the item 8 rows
  (level trends across cases) are set to ``passed`` None: not used for the judgement.
* ``--tag NAME`` or ``--tag=NAME``: output name suffix.
* ``--jobs N`` (default 1 = serial): per-case ``case_metrics`` / ``probe_metrics`` in N worker
  processes; loading, judgement, b1, figures and JSON stay in the main process, so the
  output does not depend on N (meta ``processing`` records N, the placement and the wall time).
* ``--placement MODE`` (with ``--jobs`` > 1; default ``os`` = no pinning): ``ecore`` pins the
  process and its workers to the E cores (i7-14700: logical 16-27, mask 0x0FFF0000), keeping
  the P cores for pytest / Chrono; ``pcore`` the P cores (``outrigger_sim.hostcpu``). Workers
  get ``OPENBLAS_NUM_THREADS=1`` unless it is set. Example (RE3b, 38 cases, 8 E-core
  workers: about 20 s)::

      s6_stage2_summary.py <batch> <override> --tag re3b --jobs 8 --placement ecore

Outputs (``06_analysis/01_chrono/16_S6/``): ``verify_S6_L1_closed_loop[_<tag>].json`` and
``verify_S6_L1_closed_loop[_<tag>]_{forces,attitude,shadow}.png`` (no tag: no suffix).
Row counts: ``failed_rows`` = ``passed`` False; ``not_judged_rows`` = ``passed`` None (reports,
info rows of RE1c, rows whose value could not be measured, item 8 under mixed revisions).
Checks in ``outrigger_sim.verify.s6_control``; judgement by control-expert / dynamics-expert.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "16_S6"
OUT = OUT_DIR / "verify_S6_L1_closed_loop.json"
TAG = ""
"""Output name suffix (``--tag=re`` -> ``verify_S6_L1_closed_loop_re.json``, figures likewise)."""
REDUCED = ROOT / "06_analysis" / "02_control" / "c2_revision_verify.json"
REDUCED_SLOPE = {"flat": "flat", "diag3": "diag3", "roll3": "roll+3"}
REANCHOR_REF = ROOT / "06_analysis" / "02_control" / "c2_reanchor.json"
"""Reduced model with H4 per level and slope (``verify`` runs): item 8 time trend (J4)."""
REANCHOR_SLOPE = {"flat": "flat", "roll5.5": "roll+5.5", "fdown3.5": "pitch+3.5",
                  "fup3.5": "pitch-3.5"}


def _plain(v):
    import numpy as np

    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, np.ndarray):
        return _plain(v.tolist())
    if isinstance(v, np.generic):
        return _plain(v.item())
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


MIXED_NOTE = "리비전 혼합 — 판정에 쓰지 않음"
"""Note of rows not used for the judgement because the merged cases mix C2 revisions."""


def _revision(case) -> str:
    """C2 revision of a case (``result.json`` ``controller_meta.revision``)."""
    res = case["result"]
    rev = (res.get("controller_meta") or {}).get("revision")
    if rev is None:
        rev = ((res.get("runner") or {}).get("controller") or {}).get("revision")
    return str(rev) if rev is not None else "unknown"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def reduced_refs(params):
    """Item 1 references (``verify.s6_control.reduced_reference``) of the G1 floors."""
    from outrigger_sim.verify.s6_control import reduced_reference

    data = json.loads(REDUCED.read_text(encoding="utf-8"))
    out = {}
    for floor, slope in REDUCED_SLOPE.items():
        runs = [r for r in data["runs"] if r["gainset"] == "R:BS_hold" and r["group"] == "base"
                and r["level"] == "top" and r["slope"] == slope and r["contact"] == "pressure"
                and r["mast"] == "rigid" and r["Fs_kN"] == 0.0 and r["imu"] == "nominal"]
        if runs:
            out[floor] = {**reduced_reference(runs[0], params),
                          "source": f"{REDUCED.name} runs: R:BS_hold base top {slope} pressure",
                          "note": "reduced model R1 + delay 1 step (spec item 1)"}
    return out


def reduced_level_times():
    """Item 8 time trend (J4): reduced touch -> READY per floor and level, H4 variant, rigid
    mast, group ``base`` at every level (``c2_reanchor.json`` ``verify`` runs)."""
    data = json.loads(REANCHOR_REF.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float]] = {}
    for floor, slope in REANCHOR_SLOPE.items():
        for lv in ("top", "middle", "bottom"):
            runs = [r for r in data["verify"]["runs"] if r.get("level") == lv
                    and r.get("slope") == slope and r.get("variant") == "H4"
                    and r.get("mast") == "rigid" and r.get("group") == "base"
                    and r.get("t_ready_s") is not None]
            if runs:  # same group at every level (base: no probe); only differences are used
                out.setdefault(floor, {})[lv] = runs[0]["t_ready_s"] - runs[0]["t_touch_s"]
    return out


def _ge1_summary(case_dir: Path, t_from: float | None):
    """GE1 series (``ge1_series.json``: (t, phase, SupportGeometry)) after ``t_from``, split into
    the stationary phases (done, probe, ready) and the moving ones (level, reanchor): d_i
    (``heights_above_others_m``) minimum / maximum per leg [mm], |r| (``nonplanarity_m``)
    maximum [mm]. LEVEL values carry the attitude-filter lag (python-expert, known limit)."""
    import numpy as np

    f = case_dir / "ge1_series.json"
    if not f.exists():
        return {"available": False}
    rows = json.loads(f.read_text(encoding="utf-8"))
    out: dict = {"available": True, "n": len(rows)}
    groups = {"stationary": ("done", "probe", "ready"), "moving": ("level", "reanchor")}
    for name, phases in groups.items():
        sel = [v for t, ph, v in rows if isinstance(v, dict) and ph in phases
               and (t_from is None or t >= t_from)]
        # R5 (spec rev. 7 37.3) d^Delta when present, else the R4.1 d (older batches)
        from s6_ge1_export import K_D

        key = (K_D
               if any(K_D in v for v in sel)
               else "heights_above_others_m")
        out.setdefault("d_key", key)
        d = np.array([v[key] for v in sel if v.get(key) is not None], dtype=float)
        r = np.array([v["nonplanarity_m"] for v in sel if v.get("nonplanarity_m") is not None],
                     dtype=float)
        blk = {"n": len(sel)}
        if d.size:
            blk["d_min_mm"] = (d.min(axis=0) * 1e3).tolist()
            blk["d_max_mm"] = (d.max(axis=0) * 1e3).tolist()
        if r.size:
            blk["r_maxabs_mm"] = float(np.max(np.abs(r))) * 1e3
        out[name] = blk
    return out


def event_case_blocks(cases, metrics):
    """RE1b (RR ground 30 mm) and RE1c (RR forced retract 25 mm) blocks (spec 23, 30)."""
    import numpy as np

    out = {}
    for cid, case in cases.items():
        m = metrics[cid]
        if not cid.startswith(("RE1b", "RE1c")):
            continue
        tm = m["times_s"]
        res = case["result"]
        t_ev = res.get("event_t_s")
        if t_ev is None:  # batches before RE3: event at READY + 5 s
            t_ev = None if tm["ready"] is None else tm["ready"] + 5.0
        blk: dict = {"event_start_s": t_ev, "event_definition": res.get("event_definition"),
                     "final_phase": m["final_phase"], "fine_dt": res.get("fine_dt"),
                     "dt_segments": (res.get("runner") or {}).get("dt_segments"),
                     "grade": res["settings"].get("grade")}
        pads = case["pads"]
        if pads is not None and t_ev is not None and np.any(pads["t"] - tm["t0"] >= t_ev):
            tp = pads["t"] - tm["t0"]
            after = tp >= t_ev
            n_rr = pads["N"][after, 3]
            blk["RR_lifted"] = bool(np.any(n_rr <= 0.0))
            blk["RR_lifted_fraction"] = float(np.mean(n_rr <= 0.0))
            ta = tp[after]
            lifted = n_rr <= 0.0
            if lifted.any():
                dt_rec = np.diff(ta, append=ta[-1])
                blk["RR_lifted_total_s"] = float(np.sum(dt_rec[lifted]))
                blk["RR_first_liftoff_after_event_s"] = float(ta[np.argmax(lifted)] - t_ev)
                last = np.flatnonzero(lifted)[-1]
                blk["RR_last_recontact_after_event_s"] = (
                    float(ta[last + 1] - t_ev) if last + 1 < len(ta) else None)
            blk["pad_N_min_after_event_kN"] = (pads["N"][after].min(axis=0) / 1e3).tolist()
            blk["cyl_min_after_event_kN"] = (
                pads["F_cyl_min_interval"][after].min(axis=0) / 1e3).tolist()
            end = tp >= tm["end"] - 1.0
            blk["final_pad_N_min_kN"] = float(pads["N"][end].min()) / 1e3
            blk["final_cyl_kN"] = (pads["F_cyl"][end].mean(axis=0) / 1e3).tolist()
        phases = [(float(t), ph) for t, ph in case["result"]["phases"]]
        if t_ev is not None:
            left = [t for t, ph in phases if t > t_ev and ph != "ready"]
            re_ready = next((t for t, ph in phases if left and t > left[0] and ph == "ready"), None)
            blk["left_ready_s"] = left[0] if left else None
            blk["re_ready_after_event_s"] = None if re_ready is None else re_ready - t_ev
        if cid.startswith("RE1b"):
            t_rr = blk.get("re_ready_after_event_s")
            ok_time = t_rr is not None and t_rr <= 60.0
            blk["pass_re_ready_60s"] = ok_time
            blk["pass_final_contact"] = blk.get("final_pad_N_min_kN", 0.0) > 0.0
            final = np.asarray(blk.get("final_cyl_kN", [0]))
            from outrigger_sim.verify.s6_control import D8_MARGIN_N, F_MIN_N

            f_min_kN = float(m.get("F_min_N", F_MIN_N)) / 1e3  # the run's YAML F_min (rev. 13)
            blk["pass_final_force"] = bool(np.all(final >= f_min_kN + D8_MARGIN_N / 1e3))
        blk["probe_after_event"] = [r for rnd in case["probes"] for r in rnd
                                    if isinstance(r, dict)] if case["probes"] else []
        blk["ge1"] = _ge1_summary(case["dir"], t_ev)
        if res["settings"].get("event") == "drop_RR_30_probe":
            blk["probe_relevel_check"] = probe_relevel_check(case, t_ev)
        out[cid] = blk
    return out


def probe_relevel_check(case, t_ev):
    """RE1b-P (spec rev. 7 41.2, s6_stage2.RE1BP_RELEVEL_CHECK): does the probe round that holds
    the drop run to its end, or does a PROBE -> LEVEL re-level cut it?

    From the phase list: the PROBE interval containing ``t_ev`` and the phase after it; the
    probe rounds in ``probe_history.json`` (a round cut by a re-level is not stored); the
    completion-filter attitude deviation proxy = 2nd-order filtered IMU tilt (Record) change
    from its value at ``t_ev`` (relevel_attitude_rad 0.07 deg in R4.1)."""
    import numpy as np

    from outrigger_sim.verify.s6_control import _filter_tilt_deg

    if t_ev is None:
        return {"status": "no event"}
    phases = [(float(t), p) for t, p in case["result"]["phases"]]
    nxt = [*phases[1:], (math.inf, "end")]
    window = next(((a, b[0], b[1]) for (a, p), b in zip(phases, nxt, strict=True)
                   if p == "probe" and a <= t_ev < b[0]), None)
    rec = case["rec"]
    t = rec["t"] - float(case["result"]["settings"]["start_t_s"])
    filt = _filter_tilt_deg(rec)
    k = int(np.searchsorted(t, t_ev))
    end = window[1] if window else t_ev + 15.0
    sel = (t >= t_ev) & (t <= end)
    dev = float(np.max(np.abs(filt[sel] - filt[min(k, len(t) - 1)]))) if sel.any() else None
    rounds = len(case["probes"])
    after = window[2] if window else None
    intervals = case["result"].get("probe_intervals")
    hit = None if intervals is None else next(
        (iv for iv in intervals if iv["t_start_s"] <= t_ev
         and (iv.get("t_end_s") is None or t_ev < iv["t_end_s"])), None)
    return {
        "probe_interval_at_drop": hit,
        "probe_interrupted": None if hit is None else hit.get("interrupted_by_relevel"),
        "probe_intervals_interrupted": None if intervals is None
        else [iv for iv in intervals if iv.get("interrupted_by_relevel")],
        "probe_window_s": None if window is None else [window[0], window[1]],
        "phase_after_probe": after,
        "probe_rounds_stored": rounds,
        "filtered_tilt_change_max_deg": dev,
        "relevel_attitude_limit_deg": 0.07,
        "probe_ran_through": None if window is None else after in ("ready", "level", "probe")
        and dev is not None and dev < 0.07,
        "note": "phase_after_probe 'level' with a stored round = Q2 re-ground or round end; "
                "'level' with no new round = cut by a re-level (check controller events)",
    }


B1_SEEDS = (12345, 12346, 12347)
"""Independent seeds of the normal grade (spec rev. 7 41.3 supplement): ``normal_zeroed`` only;
``normal_zeroed_repeatability`` (seed 12345, the same noise sequence) is the zero-offset paired
comparison and is not counted."""
B1_WINDOW_S = {"ideal": 2.0, "good": 2.5, "normal": 10.0}
"""Expected CHECK length per grade family (spec 39 T_b: ideal 2 s, good >= 2.5 s, normal 10 s)."""
B1_BIAS_TOL_DEG_H = {"good": 6.0, "normal": 12.0}
"""Per-axis |estimate - configured| (spec 41.3 supplement: normal 3 x 4 deg/h, good 6 deg/h)."""
B1_PERIOD_S = 0.02
B1_CHECK_MAX_DEFAULT_S = 10.0
"""``TargetSettings.check_max_s`` default, used when a case meta lacks the setting."""
B1_EVENTS = ("WARN_GYRO_BIAS_SKIPPED", "WARN_GYRO_BIAS_IMPLAUSIBLE")
"""B1′ event names (spec 32.2 / 42.1 names)."""
B1_META_PARENT = "target"
B1_META_ESTIMATE = "gyro_bias_rad_s"
B1_META_BLOCK, B1_META_WINDOW = "gyro_bias", "window_s"
B1_META_RESULT, B1_META_RMS = "result", "motion_rms_rad_s"
"""Controller-meta names the block needs (C2 R5 final, python-expert 2026-10-22), all under
``controller_meta[target]``: ``gyro_bias_rad_s`` = (roll, pitch) bias removed or None,
``gyro_bias[window_s]`` = T_b, ``gyro_bias[result]`` = GyroBiasEstimate meta (outcome,
window_s, check_duration_s, estimate_rad_s, motion_rms_rad_s = noise-corrected RMS of the last
window per axis (required when the bias is None), is_accepted). A missing name raises
:class:`B1MetaError`."""
B1_OUTCOME_SKIPPED_MOTION = "skipped_motion"
"""``GyroBiasOutcome.SKIPPED_MOTION`` (``control/standstill.py``): the only outcome the logic
check of the None seeds applies to (``rejected_implausible`` excluded)."""
B1_META_OMEGA_TH = "motion_limit_rad_s"
"""B1′ rate threshold omega_th(T_b) the controller judged the last-window RMS against
(``target.gyro_bias.result.motion_limit_rad_s``, C2 R5 final; the planned value of the run
setting is ``target.gyro_bias.motion_limit_rad_s``, recorded too). Without it (no CHECK result)
the threshold is computed from T_b (:func:`omega_th_deg_s`). ``motion_rms_rad_s`` = noise-
corrected deviation RMS of the last window."""


def omega_th_deg_s(t_b_s: float) -> float:
    """B1′ motion threshold omega_th(T_b) = min(0.01 sqrt(T_b / 2), 0.02) deg/s (spec rev. 8
    44.2, user decision U41-a)."""
    return min(0.01 * math.sqrt(t_b_s / 2.0), 0.02)
B1_UNCONFIRMED_NOTE = "B1′ 경사 효과 미확인 (보통 3시드 모두 편향 None, 명세 41.3 2026-10-22 보완)"


class B1MetaError(KeyError):
    """An R5 case lacks a B1′ controller-meta name (:data:`B1_META_ESTIMATE` ...)."""


def _grade_family(grade: str) -> str:
    return grade.split("_", 1)[0]


def _is_r5(res) -> bool:
    rev = str((res.get("controller_meta") or {}).get("revision") or "")
    return rev.startswith("R") and rev[1:2].isdigit() and int(rev[1:2]) >= 5


def _b1_meta_error(res, missing, present):
    return B1MetaError(f"{res['case']}: controller_meta lacks the B1' names {missing} (present: "
                       f"{sorted(present)}); match B1_META_* in s6_stage2_summary.py to "
                       "python-expert's R5 names")


def b1_entry(case, verdict_7b: bool | None = None) -> dict:
    """One B1′ record (spec rev. 7 41.3 supplements) from a stage-2 case; ``verdict_7b`` =
    ``probe_metrics(case)['verdict_match']`` (7b, probe verdict = truth)."""
    import numpy as np

    from outrigger_sim.sensors.imu import imu_config_for_grade

    res = case["result"]
    s = res["settings"]
    grade = s["grade"]
    entry = {"grade": grade, "family": _grade_family(grade), "seed": s.get("seed", 12345),
             "revision": (res.get("controller_meta") or {}).get("revision"),
             "independent_seed": grade == "normal_zeroed" and s.get("seed", 12345) in B1_SEEDS,
             "role": "zero-offset paired comparison (not a seed)"
             if grade.endswith("_repeatability") else "B1' sample",
             "verdict_7b": verdict_7b}
    if not _is_r5(res):
        entry["status"] = "C2 before R5: B1' not in the controller, not judged"
        return entry
    if B1_META_PARENT not in res["controller_meta"]:
        raise _b1_meta_error(res, [B1_META_PARENT], res["controller_meta"])
    meta = res["controller_meta"][B1_META_PARENT]
    missing = [n for n in (B1_META_ESTIMATE, B1_META_BLOCK) if n not in meta]
    if not missing and B1_META_WINDOW not in (meta[B1_META_BLOCK] or {}):
        missing.append(f"{B1_META_BLOCK}.{B1_META_WINDOW}")
    if missing:
        raise _b1_meta_error(res, missing, meta)
    est = meta[B1_META_ESTIMATE]
    result = meta[B1_META_BLOCK].get(B1_META_RESULT) or {}
    rms = result.get(B1_META_RMS)
    if est is None and rms is None:
        raise _b1_meta_error(res, [f"{B1_META_BLOCK}.{B1_META_RESULT}.{B1_META_RMS}"],
                             list(meta[B1_META_BLOCK]) + [f"result.{k}" for k in result])
    phases = [(float(t), p) for t, p in res["phases"]]
    t_start = phases[0][0] if phases and phases[0][1] == "check" else None
    t_end = next((t for t, p in phases if p != "check"), None)
    length = None if t_start is None or t_end is None else t_end - t_start
    t_b = float(meta[B1_META_BLOCK][B1_META_WINDOW])
    check_time = float(s.get("check_time_s", 2.0))
    if length is None:
        reason = None
    elif length > max(t_b, check_time) + B1_PERIOD_S + 1e-6:
        reason = "motion condition (longer than T_b)"
    elif t_b > check_time + 1e-6:
        reason = "T_b (grade window)"
    else:
        reason = "not extended"
    cfg_rad = np.asarray(imu_config_for_grade(grade).gyro_bias_rad_s, dtype=float)[:2]
    cfg = np.degrees(cfg_rad) * 3600
    names = [str(e) for e in case["events"]]
    events = {n: any(n in e for e in names) for n in B1_EVENTS}
    legs = [r for rnd in case["probes"] for r in rnd if isinstance(r, dict)]
    drift = [r.get("attitude_drift_ratio") for r in legs]
    drift = [float(d) for d in drift if d is not None and np.isfinite(d)]
    entry.update({
        "check_length_s": length, "T_b_s": t_b, "extension_reason": reason,
        "check_time_s": check_time,
        "check_max_s": (meta[B1_META_BLOCK].get("settings") or {}).get("check_max_s"),
        "bias_outcome": result.get("outcome"),
        "bias_is_accepted": result.get("is_accepted"),
        "check_duration_controller_s": result.get("check_duration_s"),
        "bias_window_estimate_deg_h": None if result.get("estimate_rad_s") is None
        else (np.degrees(result["estimate_rad_s"]) * 3600).tolist(),
        "bias_estimate_deg_h": None if est is None else (np.degrees(est) * 3600).tolist(),
        "bias_configured_deg_h": cfg.tolist(),
        "bias_error_deg_h": None if est is None
        else (np.degrees(np.asarray(est, dtype=float)) * 3600 - cfg).tolist(),
        "bias_removed": est is not None,
        "last_window_rms_deg_s": None if rms is None else np.degrees(np.asarray(rms)).tolist(),
        "omega_th_deg_s": float(np.degrees(result[B1_META_OMEGA_TH]))
        if result.get(B1_META_OMEGA_TH) is not None else omega_th_deg_s(t_b),
        "omega_th_source": f"meta result.{B1_META_OMEGA_TH}"
        if result.get(B1_META_OMEGA_TH) is not None else "computed from T_b (spec rev. 8 44.2)",
        "omega_th_setting_deg_s": None if meta[B1_META_BLOCK].get(B1_META_OMEGA_TH) is None
        else float(np.degrees(meta[B1_META_BLOCK][B1_META_OMEGA_TH])),
        "omega_th_computed_deg_s": omega_th_deg_s(t_b),
        "events": events,
        "probe_legs": len(legs),
        "q1_abstentions": sum(bool(r.get("is_attitude_rippled")) for r in legs),
        "q1_drift_ratio_max": max(drift) if drift else None,
        "q1_drift_ratio_per_leg": drift,
    })
    return entry


def check_length_verdict(e: dict) -> tuple[bool | None, str]:
    """U55 / J-3 (spec 55.3): CHECK length judged by its reason code.

    Returns (passed, note).

    * ``T_b`` (or not extended): length = ``max(T_b, check_time)`` within one period;
    * motion condition (longer than that): ``length <= check_max_s`` and the reason must be
      evidenced: ``skipped_motion`` with the last-window RMS above ``omega_th`` (the logic
      check), or an accepted / rejected estimate whose window became quiet before
      ``check_max_s``. A longer CHECK without that evidence (e.g. ``skipped_motion`` with a
      quiet last window) fails: no blanket ">= 2 s" relaxation.
    """
    length = e["check_length_s"]
    if length is None:
        return None, "no CHECK"
    slack = B1_PERIOD_S + 1e-6
    expected = max(e["T_b_s"], e.get("check_time_s", 2.0))
    if length <= expected + slack:
        return abs(length - expected) <= slack, f"reason T_b: length = {expected:g} s"
    check_max = e.get("check_max_s")
    if check_max is None:
        check_max = B1_CHECK_MAX_DEFAULT_S
    if length > check_max + slack:
        return False, f"longer than check_max_s {check_max} s"
    outcome = e.get("bias_outcome")
    if outcome == B1_OUTCOME_SKIPPED_MOTION:
        rms = e["last_window_rms_deg_s"]
        moving = rms is not None and max(rms) > e["omega_th_deg_s"]
        reached_max = length >= check_max - slack
        ok = moving and reached_max and e["events"]["WARN_GYRO_BIAS_SKIPPED"]
        return ok, (f"reason motion: T_b < length <= {check_max:g} s, bias None + "
                    f"WARN_GYRO_BIAS_SKIPPED, last-window RMS > omega_th: {ok}")
    if outcome is not None:  # the window became quiet during the extension
        return True, f"reason motion: quiet window found at {length:.2f} s ({outcome})"
    return False, "longer than T_b without a bias outcome (no reason code)"


def b1_rows(entries: dict) -> list[dict]:
    """B1′ judgement rows (spec rev. 7 41.3 supplements) from :func:`b1_entry` records.

    A case whose bias is None (not removed) is held out of the bias-error row (``passed`` None,
    only ``WARN_GYRO_BIAS_SKIPPED`` reported); instead (1) its last-window noise-corrected RMS
    must exceed 0.01 deg/s on some axis (else a logic defect: failed), (3) its 7b verdict is
    shown. (2) All three independent normal seeds None -> a held row with
    :data:`B1_UNCONFIRMED_NOTE`."""
    rows = []
    for cid, e in entries.items():
        if "check_length_s" not in e:
            continue
        fam, length = e["family"], e["check_length_s"]
        want = B1_WINDOW_S.get(fam)
        ok, note = check_length_verdict(e)
        rows.append({"item": "B1' CHECK length", "case": cid, "value": length,
                     "limit": want, "passed": ok,
                     "note": f"{note}; reason {e['extension_reason']}"})
        tol = B1_BIAS_TOL_DEG_H.get(fam)
        counted = fam == "good" or e["independent_seed"]
        if tol is not None and counted:
            # U55 holds the bias accuracy of a motion-skipped CHECK (bias None, below); an
            # estimate accepted from a quiet window after the extension is still judged.
            if e["bias_error_deg_h"] is None:
                rows.append({"item": "B1' bias error per axis", "case": cid, "value": None,
                             "limit": tol, "passed": None,
                             "note": "bias None: held out of the error check; "
                                     "WARN_GYRO_BIAS_SKIPPED "
                                     f"{e['events']['WARN_GYRO_BIAS_SKIPPED']}"})
            else:
                err = [abs(v) for v in e["bias_error_deg_h"]]
                rows.append({"item": "B1' bias error per axis", "case": cid, "value": err,
                             "limit": tol, "passed": max(err) <= tol, "note": ""})
        if e.get("bias_outcome") == B1_OUTCOME_SKIPPED_MOTION:
            # the motion-condition logic check only: an implausible (rejected) estimate is
            # not a motion skip
            rms = e["last_window_rms_deg_s"]
            limit = e["omega_th_deg_s"]
            low = rms is not None and max(rms) <= limit
            rows.append({"item": "B1' None with last-window RMS (logic check)", "case": cid,
                         "value": rms, "limit": f"> omega_th(T_b) {limit:.4f} deg/s on some axis",
                         "passed": not low,
                         "note": "RMS within the estimation condition but bias None: logic defect"
                         if low else "bias None explained by motion above the condition"})
            rows.append({"item": "B1' None seed 7b verdict = truth (shown)", "case": cid,
                         "value": e.get("verdict_7b"), "limit": True, "passed": None,
                         "note": "7b is judged in the main rows"})
        rows.append({"item": "B1' Q1 abstentions (report)", "case": cid,
                     "value": [e["q1_abstentions"], e["probe_legs"]], "limit": None,
                     "passed": None, "note": f"drift ratio max {e['q1_drift_ratio_max']}"})
    judged = {cid: e for cid, e in entries.items() if "check_length_s" in e}
    seeds = sorted(e["seed"] for e in judged.values() if e["independent_seed"])
    if judged:
        rows.append({"item": "B1' independent normal seeds", "case": "normal_zeroed",
                     "value": seeds, "limit": list(B1_SEEDS),
                     "passed": seeds == list(B1_SEEDS),
                     "note": "normal_zeroed_repeatability (seed 12345) not counted"})
        normal = [e for e in judged.values() if e["independent_seed"]]
        if len(normal) == len(B1_SEEDS) and all(not e["bias_removed"] for e in normal):
            rows.append({"item": "B1' slope effect", "case": "normal_zeroed",
                         "value": "all seeds bias None", "limit": None, "passed": None,
                         "note": B1_UNCONFIRMED_NOTE})
    return rows


def _runs(mask):
    """(start, stop) index pairs of the True runs of a boolean array."""
    import numpy as np

    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1), strict=True))


def band_decomposition(case, head_area_m2) -> dict:
    """Per-leg measured friction band and its split (control spec rev. 8 44.3, U42-a).

    For every probe round and leg: the controller's ``seal_friction_estimate_N`` (half the
    extend / retract reading gap after the stiffness part, ``probe_history.json``) and, from the
    Record (20 ms, Record ``u_cmd`` = the applied command), the two hold windows of that leg's
    probe: hold A = every-leg-zero samples after its extension, hold B = after its retraction.
    Split (ASSUMPTION, cad definition): **static reading-noise share** = half the gap of the
    reading error ``(p_meas A_head - F_true)`` means between A and B (the part of the measured
    half gap that the pressure noise makes; no stiffness term, it cancels in the error); **moving
    share** = controller estimate - static share (what the probe motion / dynamic pressure
    leaves; L1 has no seal friction, F_s = 0). Also the per-reading noise sigma of the holds.
    """
    import numpy as np

    rec = case["rec"]
    u = np.asarray(rec["u_cmd"])
    f_true = np.asarray(rec["F_cyl"])
    f_meas = np.asarray(rec["meas.head_pressure"]) * head_area_m2
    err = f_meas - f_true
    tm = _times_rel(case)
    t = rec["t"] - tm
    windows = [(float(a), float(b)) for a, b in _probe_windows(case)]
    still = np.all(u == 0.0, axis=1)
    out_rounds = []
    for k, (a, b) in enumerate(windows):
        sel = (t >= a) & (t <= b)
        legs = []
        for leg in range(4):
            ext = sel & (u[:, leg] > 0.0)
            ret = sel & (u[:, leg] < 0.0)
            if not ext.any() or not ret.any():
                continue
            i_ext_end = int(np.flatnonzero(ext)[-1])
            i_ret_start = int(np.flatnonzero(ret)[0])
            i_ret_end = int(np.flatnonzero(ret)[-1])
            hold_a = np.zeros_like(still)
            hold_a[i_ext_end + 1:i_ret_start] = True
            hold_a &= still & sel
            after = np.zeros_like(still)
            after[i_ret_end + 1:] = True
            runs = _runs(after & still & sel)
            hold_b = np.zeros_like(still)
            if runs:
                hold_b[runs[0][0]:runs[0][1]] = True
            if not hold_a.any() or not hold_b.any():
                continue
            static = 0.5 * abs(float(err[hold_a, leg].mean() - err[hold_b, leg].mean()))
            sigma = float(np.std(np.concatenate([err[hold_a, leg], err[hold_b, leg]])))
            legs.append({"leg": LEGS_SUMMARY[leg], "hold_samples": [int(hold_a.sum()),
                                                                   int(hold_b.sum())],
                         "static_noise_share_kN": static / 1e3,
                         "reading_sigma_kN": sigma / 1e3, "leg_index": leg})
        rnd = case["probes"][k] if k < len(case["probes"]) else []
        est = {int(r["leg_index"]): float(r["seal_friction_estimate_N"])
               for r in rnd if isinstance(r, dict) and r.get("seal_friction_estimate_N")
               is not None and np.isfinite(r["seal_friction_estimate_N"])}
        for x in legs:
            e = est.get(x.pop("leg_index"))
            x["controller_estimate_kN"] = None if e is None else e / 1e3
            x["moving_share_kN"] = None if e is None else e / 1e3 - x["static_noise_share_kN"]
        out_rounds.append({"window_s": [a, b], "legs": legs})
    cm = case["result"].get("controller_meta") or {}
    return {"rounds": out_rounds,
            "seal_band_end_kN": None if cm.get("seal_band_N") is None
            else cm["seal_band_N"] / 1e3,
            "seal_band_initial_kN": None if cm.get("initial_seal_band_N") is None
            else cm["initial_seal_band_N"] / 1e3,
            "definition": "static share = half gap of reading-error means of the two holds; "
                          "moving share = controller estimate - static share (ASSUMPTION)"}


LEGS_SUMMARY = ("FL", "FR", "RL", "RR")


def _times_rel(case) -> float:
    return float(case["result"]["settings"]["start_t_s"])


def _probe_windows(case):
    phases = [(float(t), p) for t, p in case["result"]["phases"]]
    t_end = float(case["rec"]["t"][-1]) - _times_rel(case)
    nxt = [*phases[1:], (t_end, "end")]
    return [(a, b[0]) for (a, p), b in zip(phases, nxt, strict=True) if p == "probe"]


def b1_block(cases, probes=None):
    """B1′ check of the top nose-down 3.5 deg cases (``s6_stage2.RERUN_SETS['B1']``, spec rev. 7
    35, 39, 41.3 supplements): per-case records and judgement rows; ``probes`` =
    ``probe_metrics`` by case (7b of the None seeds)."""
    import s6_stage2

    probes = probes or {}
    entries = {cid: b1_entry(cases[cid], (probes.get(cid) or {}).get("verdict_match"))
               for cid in s6_stage2.RERUN_SETS["B1"] if cid in cases}
    return {"cases": entries, "rows": b1_rows(entries)}


NOT_APPLICABLE_NOSE_UP = "not applicable (nose_up)"
LEVEL_END_WINDOW_S = 0.5
"""Mean window before the levelling-end instants (pad record 1 ms)."""


def _h4_not_applicable(h4) -> bool:
    return bool(h4) and str(h4.get("status") or "") == NOT_APPLICABLE_NOSE_UP


def levelling_end_forces(case, tp, pads) -> dict:
    """Per-leg pad floor-plane force T and leg-normal force L [kN] at the levelling end (spec 86.6
    / dynamics return condition 2): at the first LEVEL -> DONE transition and at the first READY,
    each as the sample at the instant and the mean of the LEVEL_END_WINDOW_S before it."""
    import numpy as np

    phases = [(float(t), p) for t, p in case["result"]["phases"]]
    marks = {}
    for (_t, p), (t2, p2) in zip(phases[:-1], phases[1:], strict=True):
        if p == "level" and p2 == "done" and "first_done" not in marks:
            marks["first_done"] = t2
    t_ready = next((t for t, p in phases if p == "ready"), None)
    if t_ready is not None:
        marks["first_ready"] = t_ready
    out = {"legs": list(LEGS_SUMMARY), "window_s": LEVEL_END_WINDOW_S}
    for name, t_mark in marks.items():
        i = int(np.clip(np.searchsorted(tp, t_mark), 0, len(tp) - 1))
        win = (tp >= t_mark - LEVEL_END_WINDOW_S) & (tp <= t_mark)
        out[name] = {"t_s": t_mark,
                     "T_kN": (pads["T"][i] / 1e3).tolist(), "L_kN": (pads["L"][i] / 1e3).tolist(),
                     "T_mean_kN": (pads["T"][win].mean(axis=0) / 1e3).tolist() if win.any() else None,
                     "L_mean_kN": (pads["L"][win].mean(axis=0) / 1e3).tolist() if win.any() else None,
                     "N_kN": (pads["N"][i] / 1e3).tolist()}
    return out


def nose_up_rows(metrics, slope_r) -> list[dict]:
    """Spec 86.6 rows of the nose-up H4 cases (added next to the judge rows): the expected skip
    (judged) and the REANCHOR rows shown as "not applicable (nose_up)" (not counted)."""
    rows = []
    for cid in sorted(metrics):
        h4 = metrics[cid].get("h4") or {}
        exp = h4.get("expected") or {}
        if exp.get("expected") != "reanchor_skipped:nose_up":
            continue
        met = h4.get("expectation_met")
        rows.append({"item": "R REANCHOR expected skip (nose_up)", "case": cid,
                     "value": {"outcome": h4.get("outcome"),
                               "n_reanchor_skipped_nose_up": h4.get("n_reanchor_skipped_nose_up"),
                               "n_reanchor_started": h4.get("n_reanchor_started")},
                     "limit": "reanchor_skipped:nose_up once, no reanchor_started",
                     "passed": None if met is None else bool(met),
                     "note": "spec 86.6 (direction nose_down_only)", "kind": "function"})
        for item in ("R attitude change during REANCHOR", "R H4 (REANCHOR outcome)",
                     "16.5 T3 REANCHOR breakdown"):
            rows.append({"item": item, "case": cid, "value": NOT_APPLICABLE_NOSE_UP, "limit": None,
                         "passed": None, "note": "spec 86.6: not counted", "kind": "n/a"})
        le = (slope_r.get(cid) or {}).get("levelling_end")
        if le:
            rows.append({"item": "R levelling-end pad force per leg (report)", "case": cid,
                         "value": {k: le[k] for k in ("first_done", "first_ready") if k in le},
                         "limit": "return condition 2: <= reduced envelope x 1.05 (dynamics)",
                         "passed": None, "note": "spec 86.6 / dynamics 5.13.5 supplement 4; "
                         "T = floor-plane, L = leg-normal [kN], legs FL FR RL RR",
                         "kind": "report"})
    for key, entry in slope_r.items():
        if key.startswith("H4_reduction_") and isinstance(entry, dict) \
                and entry.get("status") == NOT_APPLICABLE_NOSE_UP:
            rows.append({"item": "R H4 reduction (L basis)", "case": key[len("H4_reduction_"):],
                         "value": NOT_APPLICABLE_NOSE_UP, "limit": None, "passed": None,
                         "note": "spec 86.6: not counted", "kind": "n/a"})
    return rows


def h4_and_friction(cases, metrics):
    """R: pad floor-plane force T and leg-normal force L at the end, rear slip, H4 reduction."""
    import numpy as np

    out = {}
    for cid, case in cases.items():
        pads = case["pads"]
        m = metrics[cid]
        if pads is None or m["floor"] not in ("fdown3.5", "fup3.5", "roll5.5"):
            continue
        tp = pads["t"] - m["times_s"]["t0"]
        end = tp >= m["times_s"]["end"] - 1.0
        slip = np.linalg.norm(pads["slip_total"], axis=2)  # (n, 4) cumulative
        t_touch = m["times_s"]["touch"] or 0.0
        i0 = int(np.searchsorted(tp, t_touch))
        out[cid] = {
            "T_end_kN": (pads["T"][end].mean(axis=0) / 1e3).tolist(),
            "L_end_kN": (pads["L"][end].mean(axis=0) / 1e3).tolist(),
            "utilisation_end": np.nanmean(pads["utilisation"][end], axis=0).tolist(),
            "slip_after_touch_mm": ((slip[-1] - slip[i0]) * 1e3).tolist(),
            "rear_slip_gt_0p1mm": bool(np.any((slip[-1] - slip[i0])[2:] > 1e-4)),
            "h4": m.get("h4"), "stroke": m.get("stroke"),
            "levelling_end": levelling_end_forces(case, tp, pads),
        }
    for floor in ("fdown3.5", "fup3.5"):
        on, off = out.get(f"G6_top_{floor}_H4on"), out.get(f"G6_top_{floor}_H4off")
        if on and _h4_not_applicable(on.get("h4")):
            # spec 86.6: nose-up H4 skipped under nose_down_only, H4 on = H4 off by design
            out[f"H4_reduction_{floor}"] = {"reduction": None, "status": "not applicable (nose_up)",
                                            "rear_L_on_kN": np.asarray(on["L_end_kN"])[2:].max(),
                                            "rear_L_off_kN": None if not off
                                            else np.asarray(off["L_end_kN"])[2:].max()}
            continue
        if on and off:
            l_on = np.asarray(on["L_end_kN"])[2:].max()
            l_off = np.asarray(off["L_end_kN"])[2:].max()
            out[f"H4_reduction_{floor}"] = {"rear_L_on_kN": l_on, "rear_L_off_kN": l_off,
                                            "reduction": 1.0 - l_on / l_off if l_off else None,
                                            "reduced_model_expectation": "-54 % (36.5 -> 16.8 kN)"}
    return out


def figures(metrics, shadow):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    ids = [m["case"] for m in metrics]
    y = np.arange(len(ids))
    fmin = [m.get("min_cyl_after_liftoff_kN") or 0.0 for m in metrics]
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(y, fmin, color="#1f5aa6")
    f_min_kN = float(metrics[0].get("F_min_N", 9453.0)) / 1e3 if metrics else 9.453
    ax.axvline(f_min_kN, color="#b03a2e", ls="--", lw=1, label=f"F_min {f_min_kN:.3f} kN")
    ax.axvline(f_min_kN + 5.0, color="#d68910", ls=":", lw=1, label="F_min + 5 kN (D8)")
    ax.set_yticks(y, ids, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("minimum true cylinder force after crawler lift-off, every step [kN]")
    ax.legend(fontsize=8)
    ax.set_title("S6 stage 2: item 3 F_min (1 ms record)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"verify_S6_L1_closed_loop{TAG}_forces.png", dpi=130)
    plt.close(fig)
    att = [(m.get("att_err_last5_maxabs_deg") or 0.0) + 0.02 for m in metrics]
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(y, att, color="#1f5aa6")
    ax.axvline(0.2, color="#b03a2e", ls="--", lw=1, label="0.2 deg")
    ax.set_yticks(y, ids, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("last 5 s max |true attitude - target| + mount share 0.02 [deg]")
    ax.legend(fontsize=8)
    ax.set_title("S6 stage 2: item 2 accuracy")
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"verify_S6_L1_closed_loop{TAG}_attitude.png", dpi=130)
    plt.close(fig)
    if shadow:
        fig, ax = plt.subplots(figsize=(8, 6))
        names = list(shadow)
        d = np.array([shadow[k]["shadow_minus_true_deg"] for k in names])
        yy = np.arange(len(names))
        ax.barh(yy - 0.2, d[:, 0], height=0.4, label="roll", color="#1f5aa6")
        ax.barh(yy + 0.2, d[:, 1], height=0.4, label="pitch", color="#d68910")
        ax.axvline(0.02, color="#888888", ls=":", lw=1)
        ax.axvline(-0.02, color="#888888", ls=":", lw=1)
        ax.set_yticks(yy, names, fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("(B) shadow floor estimate at TOUCH end - true floor slope [deg]")
        ax.legend(fontsize=8)
        ax.set_title("S6 stage 2: X9 shadow floor estimate (expected <= 0.02 deg, ideal IMU)")
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"verify_S6_L1_closed_loop{TAG}_shadow.png", dpi=130)
        plt.close(fig)


_WORKER_PARAMS: dict = {}
"""Per worker process: ``load_params`` result per level (:func:`_case_metrics_job`)."""


def _case_metrics_job(job: tuple[str, object]) -> tuple[str, dict, dict]:
    """Pool job: (case dir, reduced reference or None) -> (case dir, case_metrics,
    probe_metrics), the same calls as the serial path of :func:`main`."""
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.s6_control import case_metrics, load_case, probe_metrics

    case_dir, red = job
    case = load_case(Path(case_dir))
    lv = case["result"]["settings"]["level"]
    if lv not in _WORKER_PARAMS:
        _WORKER_PARAMS[lv] = load_params(level=lv)
    return case_dir, case_metrics(case, _WORKER_PARAMS[lv], red), probe_metrics(case)


def _parallel_metrics(jobs_list: list[tuple[str, object]], jobs: int,
                      placement: str) -> dict[str, tuple[dict, dict]]:
    """``case_metrics`` / ``probe_metrics`` of every job in ``jobs`` worker processes.

    ``placement`` (``os`` / ``ecore`` / ``pcore``, :func:`outrigger_sim.hostcpu.place_process`)
    is applied to this process before the pool starts, so the workers inherit the affinity.
    ``OPENBLAS_NUM_THREADS`` is set to 1 for the workers unless already set (small dense
    algebra under a restricted affinity otherwise oversubscribes)."""
    import os
    from concurrent.futures import ProcessPoolExecutor

    from outrigger_sim.hostcpu import place_process

    PLACEMENT.update(place_process(placement))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    out: dict = {}
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for case_dir, m, p in ex.map(_case_metrics_job, jobs_list):
            out[case_dir] = (m, p)
    return out


PLACEMENT: dict = {}
"""What :func:`_parallel_metrics` did for the CPU placement (written to the meta)."""


def main(batch_dir: Path, *overrides: Path, jobs: int = 1, placement: str = "os"):
    """Summary of batch_dir; case directories in overrides (later batches) replace
    those of the same name. ``jobs`` > 1 computes the per-case metrics in that many worker
    processes (``placement`` as :func:`_parallel_metrics`); the result does not depend on it."""
    import time

    from outrigger_sim.params import load_params
    from outrigger_sim.sensors.hydraulic import leg_head_areas_from_params
    from outrigger_sim.verify.s6_control import case_metrics, judge, load_case, probe_metrics

    t_start = time.perf_counter()
    params = {lv: load_params(level=lv) for lv in ("top", "middle", "bottom")}
    reduced = reduced_refs(params["top"])
    cases, metrics, probes, failed = {}, {}, {}, []
    dirs = {d.name: d for d in sorted(batch_dir.iterdir()) if d.is_dir()}
    for extra in overrides:
        dirs.update({d.name: d for d in sorted(extra.iterdir()) if d.is_dir()})
    pooled: dict = {}
    if jobs > 1:
        job_list = []
        for _name, d in sorted(dirs.items()):
            if (d / "result.json").exists():
                res = json.loads((d / "result.json").read_text(encoding="utf-8"))
                red = (reduced.get(res["settings"]["floor"]) if res["case"].startswith("G1")
                       else None)
                job_list.append((str(d), red))
        pooled = _parallel_metrics(job_list, jobs, placement)
    for _name, d in sorted(dirs.items()):
        if not (d / "result.json").exists():
            failed.append({"case": d.name, "case_json": (d / "case.json").read_text(
                encoding="utf-8")[-2000:] if (d / "case.json").exists() else None})
            continue
        case = load_case(d)
        cid = case["result"]["case"]
        lv = case["result"]["settings"]["level"]
        red = reduced.get(case["result"]["settings"]["floor"]) if cid.startswith("G1") else None
        cases[cid] = case
        if pooled:
            metrics[cid], probes[cid] = pooled[str(d)]
        else:
            metrics[cid] = case_metrics(case, params[lv], red)
            probes[cid] = probe_metrics(case)
    order = sorted(metrics)
    mlist = [metrics[c] for c in order]
    slope_r = h4_and_friction(cases, metrics)
    level_times = reduced_level_times()
    rows = judge(mlist, probes, reduced_level_times=level_times, slope_r=slope_r)
    rows += nose_up_rows(metrics, slope_r)  # spec 86.6
    batch_revisions = {}
    for b in (batch_dir, *overrides):
        own = sorted({_revision({"result": json.loads((d / "result.json").read_text(
            encoding="utf-8"))}) for d in b.iterdir() if (d / "result.json").exists()})
        used = sorted(cid for cid in cases if cases[cid]["dir"].parent == b)
        batch_revisions[_rel(b)] = {"revisions": own, "cases_used": len(used)}
    case_revision = {cid: _revision(cases[cid]) for cid in order}
    mixed = len(set(case_revision.values())) > 1
    for r in rows:
        if r["passed"] is False and r["value"] is None:  # measurement interrupted
            r["passed_raw"] = False
            r["passed"] = None
            r["note"] = "value not measured (run ended first): not judged; " + r["note"]
        if mixed and str(r["item"]).startswith("8"):
            r["passed_raw"] = r["passed"]
            r["passed"] = None
            r["note"] = f"{MIXED_NOTE}; " + r["note"]
    shadow = {cid: {k: metrics[cid].get(k) for k in ("floor_true_deg", "shadow_floor_deg",
                                                      "shadow_minus_true_deg",
                                                      "shadow_residual_mm", "shadow_floor_usage")}
              for cid in order if metrics[cid].get("shadow_minus_true_deg") is not None}
    lists = {
        "not_ready": [c for c in order if metrics[c]["final_phase"] != "ready"],
        "idle": [c for c in order if any(p == "idle" for _, p in metrics[c]["phases"])],
        "fault": [c for c in order if any(p == "fault" for _, p in metrics[c]["phases"])],
        "rejected_codes": {c: metrics[c]["target_code"] for c in order
                           if metrics[c]["target_code"] and "REJ" in str(metrics[c]["target_code"])},
        "failed_processes": failed,
    }
    b1 = b1_block(cases, probes)
    doc = {
        "meta": {"generated": _dt.datetime.now().isoformat(timespec="seconds"),
                 "stage": "S6 stage 2 C2 closed loop (control spec 3, 4; criteria rev. 2 K1-K8, "
                          "rev. 3 J1-J7 / I1-I8, rev. 4-5 RE1b / RE1c (spec 23, 30), rev. 6 GE1 "
                          f"32-33; C2 revision(s) {', '.join(sorted(set(case_revision.values())))})",
                 "batch": _rel(batch_dir),
                 "override_batches": [_rel(p) for p in overrides],
                 "mixed_revisions": mixed,
                 "c2_revision_by_batch": batch_revisions,
                 "c2_revision_by_case": case_revision,
                 "revision_warning": (f"{MIXED_NOTE}: cases of C2 "
                                      f"{', '.join(sorted(set(case_revision.values())))} are "
                                      "merged; per-case rows hold for their own revision, rows "
                                      "comparing cases (item 8) are passed None"
                                      if mixed else None),
                 "checks_module": "outrigger_sim.verify.s6_control",
                 "processing": {"jobs": jobs, "placement": dict(PLACEMENT) if jobs > 1
                                else {"mode": "serial (no placement)"},
                                "wall_s_before_output": time.perf_counter() - t_start},
                 "judgement": "cad-expert pre-check; control-expert / dynamics-expert judge",
                 "reduced_reference": {"file": REDUCED.name, "sha256": hashlib.sha256(
                     REDUCED.read_bytes()).hexdigest(),
                                       "level_times_file": REANCHOR_REF.name,
                                       "level_times_sha256": hashlib.sha256(
                                           REANCHOR_REF.read_bytes()).hexdigest()},
                 "conventions": {"delay": "ZOH + 1 control period", "imu_method": "chrono_point",
                                 "mount_share_deg": 0.02, "last_window_s": 5.0}},
        "counts": {"cases": len(order), "rows": len(rows),
                   "failed_rows": sum(1 for r in rows if r["passed"] is False),
                   "not_judged_rows": sum(1 for r in rows if r["passed"] is None),
                   "b1_failed_rows": sum(1 for r in b1["rows"] if r["passed"] is False)},
        "lists": lists, "rows": rows,
        "note_items_6_T": "item 6 and T are judged rows (I1); per-case details in cases.<id>."
                          "item6 / cases.<id>.target_T",
        "slope_R": slope_r, "reduced_level_times": level_times,
        "event_cases_RE1b_RE1c": event_case_blocks(cases, metrics),
        "b1_check": b1,
        "band_decomposition_U42": {
            cid: band_decomposition(
                cases[cid], leg_head_areas_from_params(params[metrics[cid]["level"]])
            )
            for cid in order if cases[cid]["probes"]},
        "shadow_floor_B": shadow, "reduced_G1": reduced, "probes_item7": probes,
        "cases": metrics,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(_plain(doc), indent=1, ensure_ascii=False), encoding="utf-8")
    figures(mlist, shadow)
    print(f"-> {_rel(OUT)}: {doc['counts']}")
    for r in rows:
        if r["passed"] is False:
            print("FAIL", r["item"], r["case"], r["value"], r["limit"], r["note"])


PLACEMENTS = ("os", "ecore", "pcore")
"""``--placement`` values (:func:`outrigger_sim.hostcpu.place_process` modes)."""


def _parse_args(argv: list[str]) -> tuple[list[str], str, int, str]:
    """Positional batch directories, the tag (``--tag NAME`` / ``--tag=NAME``), the worker
    count (``--jobs N``, default 1 = serial) and the placement (``--placement MODE``, default
    ``os``; only used with ``--jobs`` > 1)."""
    positional, tag, jobs, placement, i = [], "", 1, "os", 0
    values: dict[str, str] = {}
    while i < len(argv):
        a = argv[i]
        name, eq, val = a.partition("=")
        if name in ("--tag", "--jobs", "--placement"):
            if not eq:
                if i + 1 >= len(argv):
                    raise SystemExit(f"{name} needs a value")
                val = argv[i + 1]
                i += 1
            values[name] = val
        elif a.startswith("--"):
            raise SystemExit(f"unknown option {a}")
        else:
            positional.append(a)
        i += 1
    tag = values.get("--tag", tag)
    if "--jobs" in values:
        try:
            jobs = int(values["--jobs"])
        except ValueError:
            raise SystemExit(f"--jobs needs an integer, got {values['--jobs']!r}") from None
        if jobs < 1:
            raise SystemExit("--jobs must be >= 1")
    placement = values.get("--placement", placement)
    if placement not in PLACEMENTS:
        raise SystemExit(f"--placement must be one of {PLACEMENTS}, got {placement!r}")
    if not positional:
        raise SystemExit(__doc__)
    return positional, tag, jobs, placement


if __name__ == "__main__":
    args, tag, n_jobs, where = _parse_args(sys.argv[1:])
    if tag:
        TAG = "_" + tag
        OUT = OUT_DIR / f"verify_S6_L1_closed_loop{TAG}.json"
    main(*(Path(a).resolve() for a in args), jobs=n_jobs, placement=where)
