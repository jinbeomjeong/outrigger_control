"""C-S8-75 bundle C judgement (spec rev. 68 358.6): S9 SCM J1 B top F_s 0 / 4 with P-S8-27.

Pass rule (358.6 row C): every P3 judgement row of spec 284 with the rev. 60 corrected definitions
passes (P3-1, P3-2, P3-3, P3-4, P3-5, P3-8). P3-6, P3-7, P3-9, the pre-lift-off dip (J1 note 3),
W-61 and the 10 s re-approach limit are records / FLAGs (284, 306), never a failure. P3-10 and RE1c
are not part of bundle C. A row that cannot be evaluated (P3-1 window incomplete, P3-4 window short
or no READY) makes the case "not judgeable", not "fail".

Two paths per case (spec 307 style; both read the same raw series, so this checks the extraction,
not the plant):

- path 1 = the runner's ``p3b`` block. A finished case of the old runner (before C-S9-60) uses its
  ``result_rejudge_rev60.json`` when that was made from the same ``result.json`` (SHA-256, as
  ``s9_batch_summary._p3b_of_case``). In addition ``run_S9.rejudge_case(write=False)`` recomputes
  the whole block with the current code (nothing is written into the case folder) and every block
  is compared with the stored one (``path1_recompute_equal``).
- path 2 = this script's own recomputation from ``step_series.npz`` (1 ms), ``record/record.npz``
  (10 Hz), the 10 Hz ``s9_rows``, ``phases`` and ``events``; the S-1 window replay of P3-7 uses
  ``04_scripts/03_control/s9/p3b/p3b_collect.reconstruct_s1`` (control's rev. 60 replica, same
  sample, lag 0).

Observation items for P-S8-26 / P-S8-27 (records): controller identity (``runner_meta.controller.r8``
``touch_free_air_cap_excess_N``, ``touch_hold_dip_samples``), ``INFO_TOUCH_FREE_AIR_CAPPED`` /
``INFO_TOUCH_DIP_HELD`` events, TOUCH span, per leg the start of the final zero-command run inside
TOUCH (proxy of the latch / candidate start; 10 Hz ``issued_u_m_s``), motor stroke gained in TOUCH,
first pad contact, attitude in TOUCH, READY / DONE / PROBE, end phase, end attitude, minimum forces,
LOC / departure, and the time of the first issued-command difference against the reference batch.

The reference batch (default ``batch_P3b_20261026_122444``, old controller) is comparison only
(358.6: the controller differs a lot, judgement is absolute).

Conventions: absolute simulation time [s] (closed loop starts at 8.0 s), forces N (printed kN),
lengths m (printed mm), angles deg (pitch > 0 nose down), true attitude = body quaternion, target 0.
Discrete controller 10 Hz (T = 0.1 s), output delay d = 1, ZOH; negative feedback.

Usage (repository root, one line; Chrono-dev or dynamics-dev):
  python -I 04_scripts/03_control/s8/r68_c75c_j1_judge.py [--batch DIR] [--ref DIR]
      [--cases ID ...] [--out JSON] [--allow-incomplete]
Without ``--allow-incomplete`` the batch must hold END for every case and "# batch P3b finished".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9" / "p3b"))
sys.path.insert(0, str(ROOT / "03_src"))

import p3b_collect  # noqa: E402  (control rev. 60 S-1 replica)
import run_S9  # noqa: E402  (runner p3b code, for the path-1 recomputation)

DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261027_174330"
DEFAULT_REF = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
DEFAULT_CASES = ("P3b_J1_B_top_Fs0", "P3b_J1_B_top_Fs4")
DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s8" / "rev68" / "c75c_j1_judgement.json"
LEGS = ("FL", "FR", "RL", "RR")

# spec 284 / rev. 60 criteria (units SI)
DEP_FRACTION = 0.01  # crawler normal < 0.01 W held 0.1 s = departure (P3a-2)
DEP_HOLD_S = 0.1
READY_WINDOW_S = 10.0  # P3-1
CREEP_LIMIT_M_S = 1.0e-4  # 0.1 mm/s, two-sided, 0.2 s backward rate
P34_LIMIT_DEG = 0.2
P34_MIN_WINDOW_S = 5.0
RUT_MIN_M = 0.025  # P3-5 (ASSUMPTION U-S9-C3)
P32_TAIL_S = 1.0  # P3-2 T_lim tail share (ASSUMPTION, spec 308)
P37_RISE_MIN_N = 4000.0
P37_LOADED_FRACTION = 0.01  # of W_ref
P3_8_KINDS = ("leg_reapproach_start", "relevel_predicted", "probe_aborted_low_load")
JUDGED_ROWS = ("P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-8")
CAP_EXPECTED_N = [8000.0, 8000.0, 6666.4, 6666.4]  # P-S8-26 R8 preset
DIP_EXPECTED = 2  # P-S8-27 R8 preset
TOL = {"time_s": 1e-6, "force_N": 1e-6, "angle_deg": 1e-9, "length_m": 1e-12, "rise_N": 0.01}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _plain(x: Any) -> Any:
    return json.loads(json.dumps(x, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))


def _canon(x: Any) -> str:
    return json.dumps(_plain(x), sort_keys=True, ensure_ascii=False)


def batch_status(batch: Path, cases: tuple[str, ...]) -> dict[str, Any]:
    """END lines and the finish marker of ``progress.log``; result files per case."""
    log = batch / "progress.log"
    txt = log.read_text("utf-8", errors="replace") if log.exists() else ""
    ends = {c: any(ln.startswith(f"END {c} ") for ln in txt.splitlines()) for c in cases}
    end_lines = [ln for ln in txt.splitlines() if ln.startswith("END ")]
    files = {c: {n: (batch / c / n).exists() for n in ("result.json", "step_series.npz", "record/record.npz",
                                                        "controller_commands.npz")} for c in cases}
    return {"batch": batch.as_posix(), "progress_log": log.exists(), "finished_marker": "# batch P3b finished" in txt,
            "end": ends, "end_lines": end_lines, "files": files,
            "complete": bool("# batch P3b finished" in txt and all(ends.values())
                             and all(all(v.values()) for v in files.values()))}


def path1_p3b(case: Path, r: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stored p3b (rev. 60 definitions) and its source, plus the current-code recomputation check."""
    rj = case / run_S9.REJUDGE_FILE
    if "criteria_rev" in (r["p3b"].get("checks") or {}):
        stored, src = r["p3b"], "result.json (runner with rev. 60 definitions)"
    elif rj.exists():
        o = json.loads(rj.read_text("utf-8"))
        if (o.get("inputs_sha256") or {}).get("result.json") != _sha(case / "result.json"):
            raise RuntimeError(f"{rj}: made from another result.json")
        stored, src = o["p3b"], run_S9.REJUDGE_FILE
    else:
        stored, src = None, "none (old runner, no re-judgement file)"
    rec = run_S9.rejudge_case(case, write=False)  # never writes into the case folder
    new = rec["p3b"]
    info: dict[str, Any] = {"source": src, "params_file_match": rec["params_file_match"],
                            "unchanged_blocks_equal_vs_result_json": rec["unchanged_blocks_equal"],
                            "unchanged_block_diffs": rec["unchanged_block_diffs"]}
    if stored is None:
        stored, info["source"] = new, "run_S9.rejudge_case(write=False) (no stored rev. 60 block)"
    diffs = sorted(k for k in set(stored) | set(new) if _canon(stored.get(k)) != _canon(new.get(k)))
    info["path1_recompute_equal"] = not diffs
    info["path1_recompute_diff_blocks"] = diffs
    return stored, info


def _first_run(mask: np.ndarray, n: int) -> int | None:
    """Index of the first sample of the first run of >= n True samples."""
    if mask.size < n:
        return None
    run = np.convolve(mask.astype(int), np.ones(n, int), "valid")
    k = np.nonzero(run == n)[0]
    return int(k[0]) if k.size else None


def path2(case: Path, r: dict[str, Any], v_max: float) -> dict[str, Any]:
    """Independent recomputation of the P3 rows (judged and recorded)."""
    ss = np.load(case / "step_series.npz")
    rec = np.load(case / "record" / "record.npz")
    t = ss["t_s"]
    cn = ss["scm_crawler_normal_N"]
    f = ss["F_cyl_N"]
    rp = ss["roll_pitch_deg"]
    w = float(r["p3b"]["weight_N"])
    f_min = float(r["p3b"]["F_min_N"])
    phases = r["phases"]
    events = r["events"]
    soil = r.get("c2_soil") or {}
    dt = float(np.median(np.diff(t)))
    n_hold = int(round(DEP_HOLD_S / dt))
    i0 = _first_run(cn < DEP_FRACTION * w, n_hold)
    t_dep = None if i0 is None else float(t[i0])
    out: dict[str, Any] = {"t_departure_s": t_dep}
    ready_entries = [p["t_s"] for k, p in enumerate(phases)
                     if p["phase"] == "ready" and (k == 0 or phases[k - 1]["phase"] != "ready")]
    dones = [p["t_s"] for p in phases if p["phase"] == "done"]
    # P3-1
    if ready_entries:
        tr = ready_entries[0]
        m = (t >= tr - 1e-9) & (t <= tr + READY_WINDOW_S + 1e-9)
        complete = bool(t[-1] >= tr + READY_WINDOW_S - 1e-9)
        cmax = float(cn[m].max())
    else:
        complete, cmax = False, None
    recontact = None
    if i0 is not None:
        kc = i0 + n_hold - 1
        back = np.nonzero(cn[kc:] >= DEP_FRACTION * w)[0]
        recontact = float(t[kc + back[0]]) if back.size else None
    out["P3-1"] = {"window_complete": complete, "crawler_max_N": cmax, "recontact_t_s": recontact,
                   "pass": None if not complete else bool(cmax is not None and cmax <= 0.0 and recontact is None)}
    # P3-2
    t_loc = next((e["t_s"] for e in events if e["name"] == "crawler_liftoff_confirmed"), None)
    st = soil.get("settings") or {}
    t_lim = float(st["plateau_window_m"]) / (float(st["push_speed_fraction"]) * v_max) + P32_TAIL_S if st else None
    p32: dict[str, Any] = {"t_loc_s": t_loc, "T_lim_s": t_lim}
    if t_loc is None or t_dep is None or t_lim is None:
        p32["pass"] = False if t_loc is None else None
    else:
        k = min(int(np.searchsorted(t, t_loc - 1e-9)), len(t) - 1)
        d = t_loc - t_dep
        before_done = not dones or t_loc <= dones[0] + 1e-9
        p32.update(loc_minus_departure_s=d, crawler_at_loc_N=float(cn[k]), loc_before_first_done=before_done)
        p32["pass"] = bool(before_done and cn[k] < DEP_FRACTION * w and 0.0 <= d <= t_lim + 1e-9)
    out["P3-2"] = p32
    # P3-3
    if t_dep is not None:
        a = t >= t_dep - 1e-9
        mins = f[a].min(axis=0)
        out["P3-3"] = {"F_min_after_N": mins.tolist(), "min_N": float(mins.min()), "min_leg": LEGS[int(mins.argmin())],
                       "min_over_F_min": float(mins.min() / f_min), "pass": bool(mins.min() >= f_min)}
    else:
        out["P3-3"] = {"pass": False, "reason": "no departure"}
    # P3-4
    rate = np.abs(ss["sinkage_rate_0p2s_m_s"])
    valid = np.all(np.isfinite(rate), axis=1)
    if t_dep is not None and ready_entries:
        after = (t >= t_dep - 1e-12) & valid
        ok = after & np.all(rate < CREEP_LIMIT_M_S, axis=1)
        bad = np.nonzero(after & ~ok)[0]
        if ok[-1]:
            t_creep = float(t[np.nonzero(ok)[0][0]]) if not bad.size else float(t[bad[-1] + 1])
        else:
            t_creep = None
        if t_creep is None:
            out["P3-4"] = {"pass": None, "reason": "no two-sided creep stop (creep_vibration_suspect)"}
        else:
            t0w = max(t_creep, ready_entries[-1])
            m = t >= t0w - 1e-9
            absmax = float(np.abs(rp[m]).max())
            length = float(t[-1] - t0w)
            out["P3-4"] = {"t_creep_two_sided_s": t_creep, "window_s": [t0w, float(t[-1])], "window_length_s": length,
                           "absmax_deg": absmax, "absmax_roll_pitch_deg": np.abs(rp[m]).max(axis=0).tolist(),
                           "end_1s_mean_roll_pitch_deg": rp[t >= t[-1] - 1.0 - 1e-9].mean(axis=0).tolist(),
                           "pass": None if length < P34_MIN_WINDOW_S - 1e-9 else bool(absmax <= P34_LIMIT_DEG)}
    else:
        out["P3-4"] = {"pass": None, "reason": "no departure or no READY"}
    # P3-5
    rows = r["s9_rows"]
    rt = np.array([row["t_s"] for row in rows])
    rut = np.array([np.nan if row["rut_clearance_m"] is None else row["rut_clearance_m"] for row in rows])
    s_lim = float(r["p3b"]["P3-5_clearance_stroke"]["s_motor_limit_m"])
    s_max = float(ss["s_motor_m"].max())
    if ready_entries:
        sel = (rt >= ready_entries[0] - 1e-9) & np.isfinite(rut)
        kmin = int(np.nonzero(sel)[0][np.argmin(rut[sel])])
        out["P3-5"] = {"rut_min_after_first_ready_m": float(rut[kmin]), "t_at_min_s": float(rt[kmin]),
                       "s_motor_max_m": s_max, "s_motor_limit_m": s_lim,
                       "pass": bool(rut[kmin] >= RUT_MIN_M and s_max <= s_lim)}
    else:
        out["P3-5"] = {"pass": None, "reason": "no READY", "s_motor_max_m": s_max}
    # P3-8
    lim = math.inf if t_loc is None else t_loc
    early = [e for e in events if e["name"].split(":")[0] in P3_8_KINDS and e["t_s"] < lim]
    out["P3-8"] = {"events_before_loc": early, "pass": not early}
    # P3-6 (record)
    t0 = float(r["t_loop_start_s"])
    out["P3-6"] = {"ready_after_loop_start_s": None if not ready_entries else ready_entries[0] - t0,
                   "within_90s_record": bool(ready_entries and ready_entries[0] - t0 <= 90.0 + 1e-9)}
    # P3-7 (record; rev. 60 loaded window > 0.01 W_ref), S-1 replay lag 0 / shift 0 (spec 307)
    w_ref = soil.get("W_ref_N")
    if soil.get("loc") and w_ref is not None:
        hp, rpz = rec["meas.head_pressure"], rec["meas.rod_pressure"]
        a_p = np.array([math.pi / 4 * 0.13**2] * 2 + [math.pi / 4 * 0.11**2] * 2)  # m^2, REXOME35 drawing
        a_ann = a_p - np.array([math.pi / 4 * 0.11**2] * 2 + [math.pi / 4 * 0.09**2] * 2)
        load = (hp * a_p - rpz * a_ann).sum(axis=1)

        def crawler_at(tq: float) -> float:
            return float(cn[min(int(np.searchsorted(t, tq - 1e-9)), len(t) - 1)])

        tp, tl, wins = p3b_collect.reconstruct_s1(rec["t"], rec["u_applied"], rec["meas.stroke"], load, phases,
                                                  float(w_ref), crawler_at, 0.0)
        thr = P37_LOADED_FRACTION * float(w_ref)
        loaded = [wn for wn in wins if crawler_at(wn[0]) > thr]
        rise_min = min((wn[1] for wn in loaded), default=None)
        gate = (tp is not None and tl is not None and abs(tp - soil["t_P_s"]) <= 1e-6
                and abs(tl - soil["t_loc_s"]) <= 1e-6)
        out["P3-7"] = {"reconstruct_ok": bool(gate), "t_P_rec_s": tp, "t_loc_rec_s": tl, "n_windows": len(wins),
                       "n_loaded_windows": len(loaded), "rise_min_loaded_N": rise_min,
                       "within_record": None if not gate else bool(rise_min is None or rise_min >= P37_RISE_MIN_N)}
    else:
        out["P3-7"] = {"reconstruct_ok": False, "reason": "no LOC / W_ref"}
    out["_series"] = {"t": t, "cn": cn, "f": f, "rp": rp, "s_motor": ss["s_motor_m"], "pad_n": ss["scm_pad_normal_N"]}
    return out


def observations(case: Path, r: dict[str, Any], p1: dict[str, Any], p2: dict[str, Any]) -> dict[str, Any]:
    """P-S8-26 / P-S8-27 observation items (records)."""
    s = p2["_series"]
    t, rp, sm = s["t"], s["rp"], s["s_motor"]
    phases = r["phases"]
    t0 = float(r["t_loop_start_s"])
    r8 = ((r.get("runner_meta") or {}).get("controller") or {}).get("r8") or {}
    cap = r8.get("touch_free_air_cap_excess_N")
    dip = r8.get("touch_hold_dip_samples")
    ident = {"touch_free_air_cap_excess_N": cap, "touch_hold_dip_samples": dip,
             "is_P_S8_26": cap is not None and np.allclose(cap, CAP_EXPECTED_N),
             "is_P_S8_27": dip == DIP_EXPECTED,
             "touch_hold_s": ((r.get("runner_meta") or {}).get("controller") or {}).get("thresholds", {}).get(
                 "touch_hold_s")}
    k_t = next((k for k, p in enumerate(phases) if p["phase"] == "touch"), None)
    t_ts = None if k_t is None else phases[k_t]["t_s"]
    t_te = None if k_t is None or k_t + 1 >= len(phases) else phases[k_t + 1]["t_s"]
    ev = r["events"]

    def evs(prefix: str) -> list[dict[str, Any]]:
        return [{"t_s": e["t_s"], "name": e["name"], "t_rel_touch_s": None if t_ts is None else e["t_s"] - t_ts}
                for e in ev if e["name"].startswith(prefix)]

    cmd = np.load(case / "controller_commands.npz")
    ct, cu = cmd["t_s"], cmd["issued_u_m_s"]
    stop = {}
    gain = {}
    if t_ts is not None and t_te is not None:
        m = (ct >= t_ts - 1e-9) & (ct < t_te - 1e-9)
        idx = np.nonzero(m)[0]
        for j, lg in enumerate(LEGS):
            z = np.abs(cu[idx, j]) <= 1e-12
            if z.size and z[-1]:
                nz = np.nonzero(~z)[0]
                k = idx[nz[-1] + 1] if nz.size else idx[0]
                stop[lg] = float(ct[k] - t_ts)
            else:
                stop[lg] = None
        ka = min(int(np.searchsorted(t, t_ts - 1e-9)), len(t) - 1)
        kb = min(int(np.searchsorted(t, t_te - 1e-9)), len(t) - 1)
        gain = {lg: float((sm[kb, j] - sm[ka, j]) * 1e3) for j, lg in enumerate(LEGS)}
        mt = (t >= t_ts - 1e-9) & (t <= t_te + 1e-9)
        rock = np.abs(rp[mt]).max(axis=0).tolist()
    else:
        rock = None
    pad_first = {}
    for j, lg in enumerate(LEGS):
        k = np.nonzero((t >= t0 - 1e-9) & (s["pad_n"][:, j] > 0.0))[0]
        pad_first[lg] = None if not k.size else float(t[k[0]])
    ready_entries = [p["t_s"] for k, p in enumerate(phases)
                     if p["phase"] == "ready" and (k == 0 or phases[k - 1]["phase"] != "ready")]
    p33 = p1["P3-3_leg_force"]
    p34 = p1["P3-4_attitude"]
    pre = p1["pre_liftoff_min_F_cyl"]["legs"]
    return {
        "controller_identity": ident,
        "INFO_TOUCH_FREE_AIR_CAPPED": evs("INFO_TOUCH_FREE_AIR_CAPPED"),
        "INFO_TOUCH_DIP_HELD": evs("INFO_TOUCH_DIP_HELD"),
        "touch_span_s": [t_ts, t_te], "touch_length_s": None if t_ts is None or t_te is None else t_te - t_ts,
        "touch_final_zero_command_start_rel_s": stop,
        "touch_stroke_gain_mm": gain, "touch_absmax_roll_pitch_deg": rock,
        "pad_first_contact_t_s": pad_first,
        "ready_entries_s": ready_entries,
        "ready_first_after_loop_start_s": None if not ready_entries else ready_entries[0] - t0,
        "n_done": sum(p["phase"] == "done" for p in phases), "n_probe": sum(p["phase"] == "probe" for p in phases),
        "end_phase": phases[-1]["phase"] if phases else None,
        "ready_at_end": p34.get("ready_at_end"),
        "phases": [[p["t_s"], p["phase"]] for p in phases],
        "end_attitude": {"p34_absmax_deg": p34.get("p34_absmax_overall_deg"),
                         "end_mean_roll_pitch_deg": p34.get("end_mean_roll_pitch_deg"),
                         "within_deadband_0p03_record": p34.get("within_deadband_0p03_record"),
                         "budget_residual_le_0p04_record": p34.get("budget_residual_le_0p04"),
                         "sensor_allowance_left_deg": p34.get("sensor_allowance_left_deg"),
                         "post_liftoff_absmax_deg": p34.get("post_liftoff_absmax_deg")},
        "F_min_after_departure_N": p33.get("F_min_after_N"),
        "F_min_after_departure_min_N": None if not p33.get("F_min_after_N") else min(p33["F_min_after_N"]),
        "F_min_transient_min_N": None if not p33.get("F_min_transient_N") else min(p33["F_min_transient_N"]),
        "F_min_late_min_N": None if not p33.get("F_min_late_N") else min(p33["F_min_late_N"]),
        "pre_liftoff_min_N": {row["leg"]: row["F_min_N"] for row in pre},
        "pre_liftoff_flag": p1["pre_liftoff_min_F_cyl"]["any_flag"],
        "t_departure_s": p1["departure"].get("t_departure_s"), "t_loc_s": p1["P3-2_loc"].get("t_loc_s"),
        "loc_minus_departure_s": p1["P3-2_loc"].get("loc_minus_departure_s"),
        "soil_mode_start_s": p1["P3-2_loc"].get("soil_mode_start_t_s"),
        "bias_corner_mm": [None if b is None else b * 1e3 for b in ((r.get("c2_soil") or {}).get("bias_corner_m") or [])],
        "P3-7_rise_min_loaded_N": p1["P3-7_plateau"].get("rise_min_loaded_N"),
        "rut_min_after_first_ready_m": p1["P3-5_clearance_stroke"].get("rut_clearance_min_after_first_ready_m"),
        "s_motor_max_m": max(p1["P3-5_clearance_stroke"]["s_motor_max_m"]),
        "probe_sinkage_mm": [[round(x * 1e3, 3) for x in pi["d_sinkage_m"]]
                             for pi in p1["P3-5_clearance_stroke"].get("probe_sinkage", [])],
        "warn_fault_events": [e for e in ev if e["name"].startswith(("WARN", "FAULT"))],
        "event_kinds": sorted({e["name"].split(":")[0] for e in ev}),
        "W61_warnings": len(p1["W61_watch"]["warnings"]), "reapproach_limit_fired": p1["reapproach_limit"]["fired"],
        "P3-9_windows": len(p1["P3-9_deferred"]["windows"]),
        "wall_s": r.get("wall_s"), "us_per_step": r.get("us_per_step"),
    }


def compare_paths(p1: dict[str, Any], p2: dict[str, Any]) -> dict[str, Any]:
    """Path 1 vs path 2 differences of the judged quantities."""
    c = p1["checks"]
    d: dict[str, Any] = {}

    def diff(name: str, a: Any, b: Any, tol: float) -> None:
        if a is None or b is None:
            d[name] = {"p1": a, "p2": b, "abs_diff": None, "ok": a is None and b is None}
        else:
            e = abs(float(a) - float(b))
            d[name] = {"p1": a, "p2": b, "abs_diff": e, "ok": e <= tol}

    diff("t_departure_s", p1["departure"].get("t_departure_s"), p2["t_departure_s"], TOL["time_s"])
    diff("P3-1_crawler_max_N", p1["P3-1_crawler"].get("crawler_normal_max_N"), p2["P3-1"]["crawler_max_N"], 0.0)
    diff("P3-2_loc_minus_departure_s", p1["P3-2_loc"].get("loc_minus_departure_s"),
         p2["P3-2"].get("loc_minus_departure_s"), TOL["time_s"])
    diff("P3-2_T_lim_s", p1["P3-2_loc"].get("limit_s"), p2["P3-2"].get("T_lim_s"), 1e-9)
    diff("P3-3_min_N", min(p1["P3-3_leg_force"].get("F_min_after_N") or [math.nan]), p2["P3-3"].get("min_N"),
         TOL["force_N"])
    diff("P3-4_absmax_deg", c.get("P3-4_absmax_deg"), p2["P3-4"].get("absmax_deg"), TOL["angle_deg"])
    diff("P3-4_creep_two_sided_s", p1["P3-4_attitude"].get("t_creep_stop_final_two_sided_s"),
         p2["P3-4"].get("t_creep_two_sided_s"), TOL["time_s"])
    diff("P3-5_rut_min_after_first_ready_m", c.get("P3-5_rut_clearance_min_after_first_ready_m"),
         p2["P3-5"].get("rut_min_after_first_ready_m"), TOL["length_m"])
    diff("P3-7_rise_min_loaded_N", c.get("P3-7_rise_min_loaded_N"), p2["P3-7"].get("rise_min_loaded_N"), TOL["rise_N"])
    verdict_p1 = {"P3-1": c.get("P3-1_crawler_zero_after_ready") and c.get("P3-1_recontact") is None,
                  "P3-2": c.get("P3-2_within"), "P3-3": c.get("P3-3_within"), "P3-4": c.get("P3-4_within_0p2"),
                  "P3-5": c.get("P3-5_within"), "P3-8": c.get("P3-8_within")}
    verdict_p2 = {k: p2[k]["pass"] for k in JUDGED_ROWS}
    return {"values": d, "values_all_ok": all(v["ok"] for v in d.values()),
            "verdict_p1": verdict_p1, "verdict_p2": verdict_p2, "verdicts_equal": verdict_p1 == verdict_p2}


def judge_case(case: Path, v_max: float) -> dict[str, Any]:
    r = json.loads((case / "result.json").read_text("utf-8"))
    p1, info = path1_p3b(case, r)
    p2 = path2(case, r, v_max)
    obs = observations(case, r, p1, p2)
    cmp_ = compare_paths(p1, p2)
    c = p1["checks"]
    p31 = p1["P3-1_crawler"]
    rows = {
        "P3-1": {"criterion": "SCM crawler normal = 0 N over READY .. READY + 10 s; no recontact (>= 0.01 W) after the "
                              "first departure", "kind": "judged",
                 "value": {"crawler_max_N": p31.get("crawler_normal_max_N"), "recontact_t_s": c.get("P3-1_recontact"),
                           "window_complete": p31.get("window_complete")},
                 "pass": None if not p31.get("window_complete") else cmp_["verdict_p1"]["P3-1"]},
        "P3-2": {"criterion": "LOC before the first DONE; crawler < 0.01 W at the LOC; 0 <= t_LOC - t_D <= T_lim = "
                              "10 mm / (0.25 v_max) + 1.0 s = 2.91165 s (rev. 60, U-S9P-13)", "kind": "judged",
                 "value": {"loc_minus_departure_s": c.get("P3-2_loc_minus_departure_s"), "T_lim_s": c.get("P3-2_limit_s"),
                           "within_2s_record": c.get("P3-2_within_2s_record")},
                 "pass": c.get("P3-2_within")},
        "P3-3": {"criterion": "true F_cyl min after the departure >= F_min 9.415 kN (all legs)", "kind": "judged",
                 "value": {"min_N": obs["F_min_after_departure_min_N"]}, "pass": c.get("P3-3_within")},
        "P3-4": {"criterion": "max |roll|, |pitch| (true, absolute) <= 0.2 deg on [max(two-sided creep stop, last "
                              "READY entry), end], window >= 5 s (main judgement)", "kind": "judged",
                 "value": {"absmax_deg": c.get("P3-4_absmax_deg"), "window_s": c.get("P3-4_window_s"),
                           "flags": c.get("P3-4_flags")},
                 "pass": None if c.get("P3-4_window_short") else c.get("P3-4_within_0p2")},
        "P3-5": {"criterion": "rut clearance min from the first READY to the end >= 25 mm (ASSUMPTION U-S9-C3), "
                              "s_motor <= 0.6848 m (rev. 60, U-S9P-14)", "kind": "judged",
                 "value": {"rut_min_m": c.get("P3-5_rut_clearance_min_after_first_ready_m"),
                           "s_motor_max_m": obs["s_motor_max_m"]}, "pass": c.get("P3-5_within")},
        "P3-8": {"criterion": "0 re-approach starts / relevel_predicted (P5) / probe_aborted_low_load before the LOC",
                 "kind": "judged", "value": p1["P3-8_false_triggers"]["counts"], "pass": c.get("P3-8_within")},
        "P3-6": {"criterion": "READY <= 90 s after the loop start (ASSUMPTION, record)", "kind": "record",
                 "value": p1["P3-6_ready"]["t_ready_after_loop_start_s"], "within": c.get("P3-6_within")},
        "P3-7": {"criterion": "S-1 rise >= 4 kN on windows with end crawler > 0.01 W_ref (record, rev. 60)",
                 "kind": "record", "value": c.get("P3-7_rise_min_loaded_N"), "within": c.get("P3-7_within"),
                 "reconstruct_ok": c.get("P3-7_reconstruct_ok")},
        "P3-9": {"criterion": "RT deferral windows, FLAG when the deferred leg < F_min (record)", "kind": "record",
                 "value": obs["P3-9_windows"], "flags": c.get("P3-9_flags")},
        "J1-③ pre-lift-off dip": {"criterion": "min F_cyl after first > 1.4 F_min up to the departure; < F_min = FLAG",
                                  "kind": "record", "value": obs["pre_liftoff_min_N"], "flag": obs["pre_liftoff_flag"]},
        "reapproach 10 s limit": {"criterion": "firing = FLAG (record)", "kind": "record",
                                  "value": obs["reapproach_limit_fired"]},
        "W-61": {"criterion": "warnings (record)", "kind": "record", "value": obs["W61_warnings"]},
    }
    judged = [rows[k]["pass"] for k in JUDGED_ROWS]
    if any(v is False for v in judged):
        verdict = "fail"
    elif any(v is None for v in judged):
        verdict = "not_judgeable"
    else:
        verdict = "pass"
    flags = [k for k, v in (("P3-6", rows["P3-6"]["within"] is False), ("P3-7", rows["P3-7"]["within"] is False),
                            ("P3-9", bool(rows["P3-9"]["flags"])), ("pre_liftoff", obs["pre_liftoff_flag"]),
                            ("reapproach_limit", bool(obs["reapproach_limit_fired"])), ("W-61", bool(obs["W61_warnings"])),
                            ("P3-4_creep_vibration_suspect", bool(c.get("P3-4_creep_vibration_suspect"))),
                            ("WARN/FAULT events", bool(obs["warn_fault_events"]))) if v]
    p2.pop("_series")
    return {"case": case.name, "verdict": verdict, "rows": rows, "flags_records": flags, "path1": info,
            "path_compare": cmp_, "path2": p2, "observations": obs,
            "inputs_sha256": {n: _sha(case / n) for n in ("result.json", "step_series.npz", "record/record.npz",
                                                         "controller_commands.npz")}}


def delta(new: dict[str, Any], ref: dict[str, Any], new_dir: Path, ref_dir: Path) -> dict[str, Any]:
    """New minus reference (comparison only)."""
    on, orf = new["observations"], ref["observations"]

    def sub(a: Any, b: Any) -> Any:
        return None if a is None or b is None else a - b

    a = np.load(new_dir / "controller_commands.npz")
    b = np.load(ref_dir / "controller_commands.npz")
    n = min(len(a["t_s"]), len(b["t_s"]))
    idx = np.nonzero(np.any(a["issued_u_m_s"][:n] != b["issued_u_m_s"][:n], axis=1))[0]
    differing: dict[str, list[str]] = {}
    for f in ("step_series.npz", "record/record.npz"):
        za, zb = np.load(new_dir / f), np.load(ref_dir / f)
        differing[f] = [k for k in za.files if k not in zb.files or za[k].shape != zb[k].shape
                        or not np.array_equal(za[k], zb[k], equal_nan=True)]
    rn = json.loads((new_dir / "result.json").read_text("utf-8"))["events"]
    rr = json.loads((ref_dir / "result.json").read_text("utf-8"))["events"]
    ev_new_only = [e for e in rn if e not in rr]
    ev_ref_only = [e for e in rr if e not in rn]
    return {"series_arrays_differing_nan_aware": differing, "events_new_only": ev_new_only,
            "events_ref_only": ev_ref_only, "touch_length_s": sub(on["touch_length_s"], orf["touch_length_s"]),
            "ready_first_after_loop_start_s": sub(on["ready_first_after_loop_start_s"],
                                                  orf["ready_first_after_loop_start_s"]),
            "p34_absmax_deg": sub(on["end_attitude"]["p34_absmax_deg"], orf["end_attitude"]["p34_absmax_deg"]),
            "F_min_after_departure_min_kN": sub(on["F_min_after_departure_min_N"], orf["F_min_after_departure_min_N"])
            / 1e3 if on["F_min_after_departure_min_N"] is not None and orf["F_min_after_departure_min_N"] is not None
            else None,
            "loc_minus_departure_s": sub(on["loc_minus_departure_s"], orf["loc_minus_departure_s"]),
            "n_probe": on["n_probe"] - orf["n_probe"],
            "end_phase": [orf["end_phase"], on["end_phase"]],
            "first_issued_command_diff_t_s": float(a["t_s"][idx[0]]) if idx.size else None,
            "issued_commands_identical": bool(not idx.size and len(a["t_s"]) == len(b["t_s"]))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    ap.add_argument("--ref", type=Path, default=DEFAULT_REF)
    ap.add_argument("--cases", nargs="+", default=list(DEFAULT_CASES))
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="judge the finished cases only; missing ones are reported as pending")
    args = ap.parse_args()
    cases = tuple(args.cases)
    from outrigger_sim.params import load_params

    params = load_params()
    v_max = float(params.get("actuator.max_speed_m_s"))
    st_new = batch_status(args.batch, cases)
    if not st_new["complete"] and not args.allow_incomplete:
        raise SystemExit(f"batch not finished: {json.dumps(st_new['end'])}, marker {st_new['finished_marker']} "
                         "(use --allow-incomplete to judge what exists)")
    out: dict[str, Any] = {
        "rule": "spec rev. 68 358.6 bundle C: all P3 judgement rows of spec 284 (rev. 60 corrected) pass; records/FLAGs "
                "do not fail; reference batch is comparison only",
        "generator": "04_scripts/03_control/s8/r68_c75c_j1_judge.py", "batch_status": st_new,
        "reference_status": batch_status(args.ref, cases), "params_file_sha256": params.file_sha256,
        "v_max_m_s": v_max, "cases": {}}
    for c in cases:
        row: dict[str, Any] = {}
        new_dir, ref_dir = args.batch / c, args.ref / c
        if (new_dir / "result.json").exists():
            row["new"] = judge_case(new_dir, v_max)
        else:
            row["new"] = {"verdict": "pending", "reason": "no result.json yet"}
        if (ref_dir / "result.json").exists():
            row["reference"] = judge_case(ref_dir, v_max)
        if "rows" in row["new"] and "reference" in row:
            row["delta_new_minus_ref"] = delta(row["new"], row["reference"], new_dir, ref_dir)
        out["cases"][c] = row
        for tag in ("new", "reference"):
            j = row.get(tag)
            if not j or "rows" not in j:
                print(f"{c} [{tag}] {j.get('verdict') if j else None}")
                continue
            o = j["observations"]
            print(f"{c} [{tag}] verdict {j['verdict']} | " + " ".join(
                f"{k}={j['rows'][k]['pass']}" for k in JUDGED_ROWS)
                + f" | paths equal {j['path_compare']['values_all_ok']}/{j['path_compare']['verdicts_equal']}"
                + f" | p1 recompute equal {j['path1']['path1_recompute_equal']} ({j['path1']['source']})")
            print(f"   P3-4 {j['rows']['P3-4']['value']['absmax_deg']:.4f} deg | P3-3 min "
                  f"{o['F_min_after_departure_min_N'] / 1e3:.2f} kN | READY {o['ready_first_after_loop_start_s']} s | "
                  f"TOUCH {o['touch_length_s']} s | CAPPED {len(o['INFO_TOUCH_FREE_AIR_CAPPED'])} DIP "
                  f"{len(o['INFO_TOUCH_DIP_HELD'])} | end {o['end_phase']} | probes {o['n_probe']} | "
                  f"identity cap {o['controller_identity']['is_P_S8_26']} dip {o['controller_identity']['is_P_S8_27']}"
                  f" | flags {j['flags_records']}")
        if "delta_new_minus_ref" in row:
            print("   delta new-ref:", json.dumps(row["delta_new_minus_ref"]))
    verdicts = [row["new"]["verdict"] for row in out["cases"].values()]
    out["bundle_C_verdict"] = ("pass" if all(v == "pass" for v in verdicts) else
                               "fail" if any(v == "fail" for v in verdicts) else
                               "pending" if any(v == "pending" for v in verdicts) else "not_judgeable")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(_plain(out), indent=1, ensure_ascii=False), "utf-8")
    print("bundle C verdict:", out["bundle_C_verdict"])
    print(args.out)


if __name__ == "__main__":
    main()
