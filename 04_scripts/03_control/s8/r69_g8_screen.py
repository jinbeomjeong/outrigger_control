"""Spec rev. 69 draft (coverage gap G8 + G5 remainder): reduced closed-loop screen of a non-planar start - the floor
under ONE pad raised (early grounding) or lowered (late grounding) - with the seal friction F_s as a second axis.

Harness: the rev. 67 PS-7 path (``r67_g1_screen.run_base``; plant / loop of r51_reapp_closed_loop: reduced 6-DoF
FlexPlant, L1-R rod-side law armed after the crawler settle, Coulomb seal friction per leg (rear 0.833 x), valve
first-order lag 0.1 s in 1 ms chunks, leg damping locked / moving, IMU 10 ms samples, head / rod readings from the net
oil force). Controller: the project C2 R8 preset (``preset_config(COMBINED)`` = ``with_10hz_d1`` minus zero
calibration / REANCHOR / target check), 03_src read only, no subclass. Ideal sensors. Deterministic.

Non-planar start: after the crawler settle (all pads in the air, zero stroke), the floor offset ``goff`` of one pad
is moved so that the pad gap at zero stroke becomes ``g_start`` (raised floor: g_start < g_0, about 341 mm front /
346 mm rear; lowered floor: g_start = g_0 + d). Crawler floor unchanged. Then t = 0, arm(), controller from CHECK
to READY + 5 s. The gaps are chosen around the TOUCH mechanisms of the R8 preset:
  free-air median of the first 5 s of moving samples (v_max 20.924 mm/s -> contact before about 52 mm of travel
  pollutes the median, before about 105 mm the window still holds grounded samples), the R-2 touch window
  (0.5 v_max over the last 40 mm before the level-floor touch extension: a pad raised by > 40 mm lands at v_max),
  lowered floor (the leg extends past the nominal extension at 0.5 v_max, more stroke).
Grid (mode "main"): g_start = 5, 20, 35, 50, 55, 80, 100, 110, 200, 290, 320 mm and g_0 + 20, 60, 150 mm
  x leg FL / FR / RL / RR x auger top / bottom x F_s 0 / 4 / 8 kN (front value, rear 0.833 x)  + ref (no change).
Mode "slope": floor edge (roll 2.2, pitch 1.6 deg, on the operating start rule) / rpB (2.7355, 1.7592 deg,
  verification range) x g_start 20 / 55 / 140 / 170 / 200 / 230 / 290 mm x 4 legs x top x F_s 4 + ref per floor
  (the 140..230 mm steps resolve the stroke-budget boundary seen in the smoke run: edge floor, FL raised 320 mm
  -> FR at the stroke end -> FAULT with RL lifted; FL raised 140 mm -> READY with FR 8 mm from the end margin).

Judgement per run (1 ms plant record; F = true cylinder force, contact = pad contact force, lift = contact <= 0):
  D8 (spec 92 / 345.2): min 1 ms F after the crawler lift-off >= F_min + 5 kN, no pad lift after the crawler
     lift-off, final attitude (mean of the last 1 s, true deck) |roll|, |pitch| <= 0.2 deg, READY reached;
  FAULT 0; stroke at READY <= end margin 0.6848 m on every leg;
  TOUCH FLAGs (345.2, generalised to the non-planar leg "k"): T-3' stroke of leg k from its first physical contact
     (pad contact > 0 held 0.1 s) to its latch > 40 mm, T-4 max |roll| or |pitch| change from the TOUCH start
     > 1.0 deg (equal to 345.2 on a level floor), T-2' latch of
     leg k later than 3.0 s after its first contact (C-S8-75 row), pumping: work of leg k's valve on the detrended
     pad load (1 s centred mean removed) in TOUCH after contact > +50 J (ASSUMPTION; c72 pumping cases +354..+477 J);
  Chrono escalation marks (harness under-predicts Chrono, rev. 68 351.1: +5..10 mm, +0.10..0.18 deg; harness
     post-lift-off minimum within +-10 kN, 358.7): T-3' > 20 mm, T-4 > 0.6 deg, D8 minimum < F_min + 15 kN.
  Records: timeline, latch time per leg (rel. TOUCH start), first contact of leg k, TOUCH length, capped / dip-held
     legs, crawler minimum in TOUCH, detrended half peak-to-peak per 2 s of leg k, warnings, command SHA-256,
     crawler clearance at the end: true (lowest gap of all crawler nodes above the base floor; the rev. 69 batch
     JSON still holds the first definition, see ``crawler_clearance``) and the controller's
     stroke-plane estimate (``geometry.clearance_corners_m``; it assumes coplanar pad floors, so a pad floor
     raised by h reads about 3h/4 too little clearance at the near corner -> over-lift; escalation only for
     under-lift true < estimate - 20 mm). Gate ``crawler_clear``: true clearance > 0 and crawler load 0 at the end.

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r69_g8_screen.py <project_root> <out_json> [workers]
  python -I r69_g8_screen.py <project_root> --list            (job keys, one per line)
Env: R69_MODE = main | slope | all (default all); R69_FILTER = comma list of substrings (a job is kept if any
  matches); R69_SLICE = "a:b" fraction of the sorted list; R69_AFFINITY = hex mask set on the parent (inherited).
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
_HERE = ROOT / "04_scripts" / "03_control" / "s8"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import numpy as np  # noqa: E402

import r51_reapp_closed_loop as r51  # noqa: E402
import r67_g1_screen as r67  # noqa: E402

LEGS = r67.LEGS
F_MIN_N = r67.F_MIN_N
STROKE_END_OK_M = 0.6848
GAPS_RAISED_MM = (5.0, 20.0, 35.0, 50.0, 55.0, 80.0, 100.0, 110.0, 200.0, 290.0, 320.0)
GAPS_LOWERED_MM = (20.0, 60.0, 150.0)
"""Lowered floor: g_start = g_0 + value."""
LEVELS = ("top", "bottom")
FS_KN = (0.0, 4.0, 8.0)
FLOORS = {"flat": (0.0, 0.0), "edge": (2.2, 1.6), "rpB": (2.7355, 1.7592)}
"""edge = on the operating start rule |roll|/4.4 + |pitch|/3.2 = 1 (dynamics 3.9.7), same signs as rpB;
rpB = verification-range floor of the S6/S8 matrices (rule value 1.17, outside the operating start envelope)."""
SLOPE_GAPS_MM = (20.0, 55.0, 140.0, 170.0, 200.0, 230.0, 290.0)
CONTACT_HOLD_S = 0.1
FLAG = {"T3_mm": 40.0, "T4_deg": 1.0, "T2_s": 3.0, "pump_J": 50.0}
ESCALATE = {"T3_mm": 20.0, "T4_deg": 0.6, "D8_margin_kN": 15.0, "clearance_err_mm": 20.0}


def set_parent_placement() -> None:
    mask = os.environ.get("R69_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def make_base_g8(cl, c2, level, fs_kN, floor, leg, gap_spec):
    """Settled plant with one pad floor moved; ``gap_spec`` = ("raised", g_start_mm) | ("lowered", d_mm) | None."""
    base = r51._reg_base("b", level, floor, fs_kN, [])
    plant = r51.make_plant(cl, base)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    gaps0 = r51.pad_gaps(cl, plant)
    info = {"g0_mm": (gaps0 * 1e3).round(3).tolist()}
    node_d0 = crawler_node_heights(cl, plant)
    if leg is not None:
        kind, val = gap_spec
        target = val * 1e-3 if kind == "raised" else float(gaps0[leg]) + val * 1e-3
        goff = np.array(plant.goff, float)
        for _ in range(3):  # gap is linear in goff (/ a_n); a few passes absorb a_n
            err = float(r51.pad_gaps(cl, plant)[leg]) - target
            R = cl.rcc._R(plant.q)
            a_n = float(plant.nrm @ R[:, 2])
            goff[leg] -= err * a_n
            plant.goff = goff.copy()
        info.update(leg=LEGS[leg], kind=kind, value_mm=val, g_start_mm=round(float(r51.pad_gaps(cl, plant)[leg]) * 1e3, 3),
                    goff_mm=(np.asarray(plant.goff, float) * 1e3).round(3).tolist())
    plant.t = 0.0
    plant.arm()
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    ctrl = c2.C2Controller.from_params(cl.PARAMS, cfg)
    ctrl.reset()
    return plant, ctrl, info, node_d0


def crawler_node_heights(cl, plant):
    """Crawler contact node heights along the floor normal [m] (as s9_soil_closed_loop.crawler_node_heights)."""
    R = cl.rcc._R(plant.q)
    return np.array([float(plant.nrm @ (plant.r + R @ c)) for c in plant.cr_rel])


def crawler_clearance(cl, plant, ctrl, node_d0):
    """True crawler clearance = lowest gap of ALL crawler nodes above the base floor plane n.p = 0, and the
    controller's stroke-plane estimate [mm].

    Rev. 69 correction (after the 432-job screen): the first version took the rise of the settle-contact nodes
    only; the 24 nodes sit at different heights (settle -6..+24 mm) and only 1-2 touch at the settle, so that
    value read +6 mm too much on a level floor and +56 / +163 mm on the edge / rpB slopes (uphill nodes missed).
    ``node_d0`` is kept for the call signature (unused)."""
    del node_d0
    d = crawler_node_heights(cl, plant)
    true_m = float(np.min(d))
    est_m = float(np.min(ctrl.geometry.clearance_corners_m(np.asarray(plant.x, float))))
    return round(true_m * 1e3, 1), round(est_m * 1e3, 1)


def detrended_bins(t, N_kN, valve_m_s):
    n = 1001
    if N_kN.size < n + 200:
        return None
    x = N_kN - np.convolve(N_kN, np.ones(n) / n, mode="same")
    work_J = float((x[n // 2: -(n // 2)] * 1e3 * valve_m_s[n // 2: -(n // 2)]).sum() * 1e-3)
    x[: n // 2] = np.nan
    x[-(n // 2):] = np.nan
    amps = []
    for a in np.arange(0.0, t[-1] - t[0], 2.0):
        w = (t - t[0] >= a) & (t - t[0] < a + 2.0) & np.isfinite(x)
        if w.sum() > 100:
            amps.append(round(float((np.nanmax(x[w]) - np.nanmin(x[w])) / 2), 1))
    return {"half_pp_detrended_per_2s_kN": amps, "work_on_detrended_load_J": round(work_J, 1)}


def job(key):
    mode, floor_id, level, fs, leg_name, kind, val = key.split("|")
    fs = float(fs)
    leg = None if leg_name == "ref" else LEGS.index(leg_name)
    gap_spec = None if leg is None else (kind, float(val))
    r51.place_worker()
    cl, c2, Meas = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    t_wall = time.perf_counter()
    plant, ctrl, info, node_d0 = make_base_g8(cl, c2, level, fs, FLOORS[floor_id], leg, gap_spec)
    rec, crawler, log = [], [], []
    tl = r67.run_base(cl, c2, Meas, plant, ctrl, rec=rec, crawler=crawler, log=log)
    rec = np.array(rec)
    t = rec[:, 0]
    contact, F, valve, att = rec[:, 1:5], rec[:, 5:9], rec[:, 9:13], rec[:, 17:19]
    res = {"key": key, "floor": floor_id, "level": level, "fs_kN": fs, "leg": leg_name, "info": info,
           "timeline": tl["timeline"], "t_lift": tl["t_lift"], "t_loc": tl["t_loc"], "t_ready": tl["t_ready"]}
    res["cmd_sha256"] = hashlib.sha256(np.array([q[3] for q in log]).tobytes()).hexdigest()[:16]
    tt = np.array([q[0] for q in log])
    is_touch = np.array([q[1] == "touch" for q in log])
    flags, esc = [], []
    if is_touch.any():
        k0, k1 = int(np.flatnonzero(is_touch)[0]), int(np.flatnonzero(is_touch)[-1])
        latched = np.array([q[7] for q in log])
        lat_abs = [float(tt[np.flatnonzero(latched[:, i])[0]]) if latched[:, i].any() else None for i in range(4)]
        atts = np.array([q[4] for q in log])[is_touch]
        datt = np.abs(atts - atts[0]).max(axis=0)
        touch = {"start_s": round(float(tt[k0]), 2), "duration_s": round(float(tt[k1] - tt[k0]), 2),
                 "latch_rel_s": {LEGS[i]: None if lat_abs[i] is None else round(lat_abs[i] - float(tt[k0]), 2)
                                 for i in range(4)},
                 "max_abs_att_deg": np.abs(atts).max(axis=0).round(3).tolist(),
                 "max_abs_att_change_deg": datt.round(3).tolist(),
                 "min_crawler_kN": round(min(q[5] for q, m in zip(log, is_touch) if m) / 1e3, 1)}
        # T-4 on the change from the TOUCH start (equal to 345.2 on a level floor; a sloped floor starts tilted)
        if datt.max() > FLAG["T4_deg"]:
            flags.append("T4")
        if datt.max() > ESCALATE["T4_deg"]:
            esc.append("T4")
        if leg is not None:
            # first physical contact of leg k held CONTACT_HOLD_S
            c_on = contact[:, leg] > 0.0
            n_hold = int(round(CONTACT_HOLD_S / 1e-3))
            run = np.convolve(c_on.astype(int), np.ones(n_hold, int), "valid")
            idx = np.flatnonzero(run == n_hold)
            t_c = float(t[idx[0]]) if idx.size else None
            touch["first_contact_s"] = None if t_c is None else round(t_c, 3)
            touch["first_contact_phase"] = None if t_c is None else next(
                (q[1] for q in log if q[0] >= t_c - 1e-9), None)
            s_at = lambda ts: float(np.interp(ts, tt, np.array([q[2][leg] for q in log])))  # noqa: E731
            if t_c is not None and lat_abs[leg] is not None:
                t3 = (s_at(lat_abs[leg]) - s_at(max(t_c, float(tt[0])))) * 1e3
                touch["post_contact_stroke_mm"] = round(t3, 1)
                touch["latch_after_contact_s"] = round(lat_abs[leg] - t_c, 2)
                if t3 > FLAG["T3_mm"]:
                    flags.append("T3")
                if t3 > ESCALATE["T3_mm"]:
                    esc.append("T3")
                if lat_abs[leg] - t_c > FLAG["T2_s"]:
                    flags.append("T2")
                m = (t >= t_c) & (t <= float(tt[k1]))
                osc = detrended_bins(t[m], contact[m, leg] / 1e3, valve[m, leg])
                touch["leg_oscillation"] = osc
                if osc is not None and osc["work_on_detrended_load_J"] > FLAG["pump_J"]:
                    flags.append("pump")
            touch["stroke_at_latch_mm"] = None if lat_abs[leg] is None else round(s_at(lat_abs[leg]) * 1e3, 1)
        res["touch"] = touch
    st = ctrl._state
    res["capped_legs"] = sorted(LEGS[i] for i in getattr(st, "free_air_capped_legs", set()))
    if tl["t_lift"] is not None:
        w = t >= tl["t_lift"]
        mins = F[w].min(axis=0)
        lifts = {LEGS[i]: round(float((w & (contact[:, i] <= 0)).sum() * 1e-3), 3) for i in range(4)}
        att_end = att[t >= t[-1] - 1.0].mean(axis=0)
        g = {"Fmin_plus5": bool(mins.min() >= F_MIN_N + 5e3), "no_lift": all(v == 0 for v in lifts.values()),
             "end_att": bool(np.all(np.abs(att_end) <= 0.2)), "ready": tl["t_ready"] is not None}
        res.update({"min_F_after_liftoff_kN": {LEGS[i]: round(float(mins[i]) / 1e3, 2) for i in range(4)},
                    "lift_after_liftoff_s": lifts, "att_end_deg": [round(float(a), 4) for a in att_end]})
        if float(mins.min()) < F_MIN_N + ESCALATE["D8_margin_kN"] * 1e3:
            esc.append("D8_margin")
    else:
        g = {"Fmin_plus5": False, "no_lift": False, "end_att": False, "ready": tl["t_ready"] is not None}
    phases = [q[1] for q in log]
    g["fault0"] = not any(p in ("fault", "fault_reground") for p in phases)
    stroke_end = np.asarray(plant.sref, float)
    # spec rev. 72 (366 correction): the stroke gate is the run maximum (10 Hz log of the motor stroke reference,
    # resolution <= v_max T_s); the end value stays as a record
    stroke_run_max = np.max(np.array([q[2] for q in log] + [stroke_end]), axis=0)
    g["stroke_end"] = bool(np.all(stroke_run_max <= STROKE_END_OK_M))
    res["stroke_end_mm"] = (stroke_end * 1e3).round(2).tolist()
    res["stroke_max_run_mm"] = (stroke_run_max * 1e3).round(2).tolist()
    res["stroke_end_value_ok"] = bool(np.all(stroke_end <= STROKE_END_OK_M))
    c_true, c_est = crawler_clearance(cl, plant, ctrl, node_d0)
    res["crawler_clearance_end_mm"] = {"true": c_true, "controller_estimate": c_est,
                                       "target": round(ctrl.config.thresholds.clearance_target_m * 1e3, 1)}
    res["crawler_clearance_end_mm"]["true_minus_estimate"] = round(c_true - c_est, 1)
    g["crawler_clear"] = bool(c_true > 0.0 and float(plant.acc[15]) == 0.0)
    if c_true < c_est - ESCALATE["clearance_err_mm"]:  # under-lift only; over-lift is the known plane-fit bias
        esc.append("clearance_underlift")
    res["gates"] = g
    res["flags"] = flags
    res["escalate"] = sorted(set(esc))
    res["pass"] = bool(all(g.values()) and not flags)
    res["final_phase"] = phases[-1] if phases else None
    res["events"] = [(round(e.t_s, 2), e.name) for e in ctrl.events
                     if not e.name.startswith(("INFO_PRESSURE", "shadow", "leg_reapproach", "relevel_predicted"))][:60]
    res["wall_s"] = round(time.perf_counter() - t_wall, 1)
    return res


def run_job(key):
    try:
        return job(key)
    except Exception as exc:  # keep the batch going; the error is reported
        import traceback
        return {"key": key, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}


def all_jobs(mode):
    jobs = []
    if mode in ("main", "all"):
        for lv in LEVELS:
            for fs in FS_KN:
                jobs.append(f"main|flat|{lv}|{fs}|ref|none|0")
                for lg in LEGS:
                    jobs += [f"main|flat|{lv}|{fs}|{lg}|raised|{g}" for g in GAPS_RAISED_MM]
                    jobs += [f"main|flat|{lv}|{fs}|{lg}|lowered|{d}" for d in GAPS_LOWERED_MM]
    if mode in ("slope", "all"):
        for fl in ("edge", "rpB"):
            jobs.append(f"slope|{fl}|top|4.0|ref|none|0")
            for lg in LEGS:
                jobs += [f"slope|{fl}|top|4.0|{lg}|raised|{g}" for g in SLOPE_GAPS_MM]
    return jobs


def main():
    if len(sys.argv) > 2 and sys.argv[2] == "--list":
        for j in all_jobs(os.environ.get("R69_MODE", "all")):
            print(j)
        return
    set_parent_placement()
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    jobs = all_jobs(os.environ.get("R69_MODE", "all"))
    filt = os.environ.get("R69_FILTER")
    if filt:
        jobs = [j for j in jobs if any(f in j for f in filt.split(","))]
    sl = os.environ.get("R69_SLICE")
    if sl:
        a, b = (float(x) for x in sl.split(":"))
        n = len(jobs)
        jobs = [jobs[k] for k in range(n) if a <= (k + 0.5) / n < b]
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        res = pool.map(run_job, jobs, chunksize=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r69_g8_screen.py",
                                        "spec": "rev. 69 draft (G8 non-planar start + G5 remainder)",
                                        "wall_s": round(time.perf_counter() - t0, 1), "workers": workers,
                                        "affinity": os.environ.get("R69_AFFINITY"), "filter": filt, "slice": sl,
                                        "n_jobs": len(jobs)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
