"""Rev. 64 P-S8-23 (d): record replay of the D1 / D1'' diagnosis with the settings before and after rev. 64.

The controller's two-pressure monitor (``TwoPressureMonitor``, diagnosis ON, built as ``C2Controller`` builds it)
is run offline on each recorded 10 Hz run (record ``meas.*``, r8_series ``phase`` / ``issued_u`` / ``leg_band_N`` /
IMU partial means) three ways; the inputs are identical, only the settings and the crawler-lifted input differ:

  A  old   ``with_10hz_d1`` two-pressure settings with ``imu_mass_before_ready=None``,
           ``crawler_recontact_watch=False`` (= test_r5_fallback_replay._preset_before_rev64), crawler-lifted input =
           the phase rule (CRAWLER_LIFTED_PHASES of the phase before the read)
  B  new   ``with_10hz_d1`` (YAML mass before READY, re-contact watch on), crawler-lifted input = LOC (the run's
           ``crawler_liftoff_confirmed`` / ``INFO_SOIL_STATE_RESTORED`` event, from the row after it) and not the
           watch's suspicion; a run without a LOC event uses the phase rule as the LOC proxy (ASSUMPTION: a new run
           confirms the lift-off at its first lifted phase, and a branch from an old pickle restores it)
  C  new without LOC   as B, but a run without a LOC event never gets one (old-pickle branch not restored:
           D1' throughout); only for runs without a LOC event

Per run: first head FAULT (time, leg), event counts by kind (``FAULT_HEAD_PRESSURE``, ``WARN_ROD_PRESSURE_FALLBACK``,
``INFO_PRESSURE_STEP:<side>:<reason>``, ``INFO_D1_IMU_MASS_SOURCE``, ``WARN_CRAWLER_RECONTACT_SUSPECTED``) and the
recorded controller events of the same kinds (fidelity of A for old runs, of B for runs made with rev. 64).
A run with an injected head fault and ``head_fault_delivered.npz`` (C-S8-71; same rows and times as the record) is
replayed on the delivered head reading ``meas.head_pressure_delivered`` (record ``meas.head_pressure`` is the reading
before the injection).
Not replayed: the controller's reaction (FAULT stops nothing here; FAULT_REGROUND's held reading is not applied, so
for runs with an injected head fault only the events up to the first FAULT compare), the R-5 fallback ratio
choice (forces only), the probe's seal friction sum (0: the re-contact threshold takes its 30 kN floor, the most
sensitive value). The zero offsets apply from the row after each INFO_PRESSURE_ZERO_CALIBRATED event (result meta).

Usage (dynamics-dev): python -I r64_d1_replay.py <project_root> <out_json> <workers> <batch_dir> [...]
Deterministic, read only.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]).resolve()
for _p in (ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import r64_common as rc  # noqa: E402

LOC_EVENTS = ("crawler_liftoff_confirmed", "INFO_SOIL_STATE_RESTORED")
KINDS = ("FAULT_HEAD_PRESSURE", "WARN_ROD_PRESSURE_FALLBACK", "INFO_PRESSURE_STEP", "INFO_D1_IMU_MASS_SOURCE",
         "WARN_CRAWLER_RECONTACT_SUSPECTED", "INFO_CRAWLER_RECONTACT_CLEARED", "WARN_D1_IMU_GYRO_MISSING")


def kind_of(name: str) -> str | None:
    for k in KINDS:
        if name.startswith(k):
            if k == "INFO_PRESSURE_STEP":
                parts = name.split(":")
                return ":".join([k] + parts[2:4])  # side, reason
            if k == "INFO_D1_IMU_MASS_SOURCE":
                return name
            return k
    return None


def _objects():
    from outrigger_sim.contact_episode import _calibration_rows, _zero_calibration
    from outrigger_sim.control.c2 import CRAWLER_LIFTED_PHASES, C2Config, C2Geometry
    from outrigger_sim.control.two_pressure import TwoPressureMonitor
    from outrigger_sim.params import load_params
    geometry = C2Geometry.from_params(load_params())
    new = C2Config().with_10hz_d1()
    tp_old = replace(new.two_pressure, imu_mass_before_ready=None, crawler_recontact_watch=False)
    if hasattr(tp_old, "suspend_steps_after_head_fault"):  # P-S8-25 (rev. 65): not in the settings before rev. 64
        tp_old = replace(tp_old, suspend_steps_after_head_fault=False)
    old = replace(new, two_pressure=tp_old)
    lifted = {str(p) for p in CRAWLER_LIFTED_PHASES}
    return geometry, old, new, lifted, TwoPressureMonitor, _calibration_rows, _zero_calibration


def make_monitor(TwoPressureMonitor, geometry, config):
    return TwoPressureMonitor(
        geometry.head_area_m2, geometry.annulus_area_m2, geometry.max_speed_m_s, geometry.F_min_N,
        config.period_s, config.load_estimate, config.two_pressure, geometry.rod_weight_N,
        stroke_max_m=geometry.stroke_max_m,
        retract_lock_rod_pressure_Pa=geometry.rod_lock_pressure_after_retract_Pa,
        counterbalance_lag_tau_s=geometry.counterbalance_lag_tau_s,
        body_mass_kg=geometry.superstructure_mass_kg,
        imu_lever_arm_m=geometry.imu_lever_arm_m,
    )


def replay_one(objs, data, config, rule):
    geometry, _, _, lifted_phases, TM, _, _ = objs
    mon = make_monitor(TM, geometry, config)
    t, head, rod, stroke, phase, acting, band, fz, gyro, offsets, cal_rows, loc_row = data
    out_events = []
    first_fault = None
    for row in range(t.size):
        mon.set_zero_offsets_N(np.where(cal_rows <= row, offsets, 0.0))
        prev = phase[row - 1] if row > 0 else phase[0]
        if rule == "phase":
            is_lifted = prev in lifted_phases
        else:
            has_loc = loc_row is not None and row > loc_row
            is_lifted = has_loc and not mon.is_crawler_recontact_suspected
        mon.read(float(t[row]), head[row], rod[row], acting[row], prev == "ready", band[row],
                 stroke_m=stroke[row], imu_specific_force_z_m_s2=None if fz is None else float(fz[row]),
                 is_crawler_lifted=bool(is_lifted), imu_gyro_rad_s=None if gyro is None else gyro[row],
                 r5_fallback_ratios=None, seal_friction_sum_N=0.0)
        for name, _ in mon.pop_events():
            out_events.append((float(t[row]), name))
            if first_fault is None and name.startswith("FAULT_HEAD_PRESSURE"):
                first_fault = (float(t[row]), name.split(":")[1])
    return out_events, first_fault


def load_case(case: Path, objs):
    *_, _calibration_rows, _zero_calibration = objs
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    r8p = case / "r8_series.npz"
    if not r8p.exists():
        return None, "no r8_series"
    r8 = np.load(r8p, allow_pickle=True)
    t = np.asarray(rec["t"], float)
    if t.size < 3 or abs(float(np.median(np.diff(t))) - 0.1) > 1e-6:
        return None, "not 10 Hz"
    if "meas.rod_pressure" not in rec.files or not np.all(np.isfinite(r8["t"])) or r8["t"].size != t.size:
        return None, "no rod / time mismatch"
    phase = np.array([str(p).split(".")[-1].lower() for p in r8["phase"]])
    issued = np.asarray(r8["issued_u"], float)
    acting = np.vstack([np.zeros((1, 4)), issued[:-1]])
    band = np.asarray(r8["leg_band_N"], float)
    band = np.vstack([band[:1], band[:-1]])
    fz = np.asarray(r8["imu_samples"][:, -1, 2], float) if "imu_samples" in r8.files else None
    gyro = np.asarray(r8["imu_gyro_samples"][:, -2:, :], float) if "imu_gyro_samples" in r8.files else None
    result = rc.load_json(case / "result.json") or {}
    events = rc.events(case, result)
    offsets, _ = _zero_calibration(result)
    cal_rows = _calibration_rows(events, t, 0.1)
    loc_times = [tt for tt, n in events if n.startswith(LOC_EVENTS)]
    loc_row = None
    if loc_times:
        loc_row = int(np.argmin(np.abs(t - min(loc_times))))
    head = np.asarray(rec["meas.head_pressure"], float)
    delivered = case / "head_fault_delivered.npz"  # C-S8-71: head reading after the fault injection
    if delivered.exists():
        dz = np.load(delivered, allow_pickle=False)
        if "t" in dz.files and not np.array_equal(np.asarray(dz["t"], float), t):
            return None, "head_fault_delivered t differs from record t"
        head = np.asarray(dz["meas.head_pressure_delivered"], float)
    rod = np.asarray(rec["meas.rod_pressure"], float)
    stroke = np.asarray(rec["meas.stroke"], float)
    data = (t, head, rod, stroke, phase, acting, band, fz, gyro, offsets, cal_rows, loc_row)
    recorded = [(tt, n) for tt, n in events if kind_of(n)]
    return (data, recorded, loc_row is not None), None


def summarize(evs, until=None):
    c = Counter()
    for tt, n in evs:
        if until is not None and tt > until + 1e-9:
            continue
        k = kind_of(n)
        if k:
            c[k] += 1
    return dict(c)


def run_case(case_str):
    case = Path(case_str)
    objs = _objects()
    try:
        loaded, why = load_case(case, objs)
    except Exception as exc:  # noqa: BLE001 - recorded per case
        return {"case": case_str, "skip": f"load error {type(exc).__name__}: {exc}"}
    if loaded is None:
        return {"case": case_str, "skip": why}
    data, recorded, has_loc = loaded
    _, old, new, *_ = objs
    out = {"case": case_str, "has_loc": has_loc, "n_rows": int(data[0].size)}
    ev_a, ff_a = replay_one(objs, data, old, "phase")
    ev_b, ff_b = replay_one(objs, data, new, "loc" if has_loc else "phase")
    out["A"] = {"first_fault": ff_a, "counts": summarize(ev_a)}
    out["B"] = {"first_fault": ff_b, "counts": summarize(ev_b)}
    if not has_loc:
        ev_c, ff_c = replay_one(objs, data, new, "loc")
        out["C"] = {"first_fault": ff_c, "counts": summarize(ev_c)}
    rec_fault = next(((tt, n.split(":")[1]) for tt, n in recorded if n.startswith("FAULT_HEAD_PRESSURE")), None)
    out["recorded"] = {"first_fault": rec_fault, "counts": summarize(recorded)}
    if rec_fault is not None:  # fidelity up to the recorded first FAULT (the controller reacted after it)
        out["until_recorded_fault"] = {"A": summarize(ev_a, rec_fault[0]), "B": summarize(ev_b, rec_fault[0]),
                                       "recorded": summarize(recorded, rec_fault[0])}
    # step reasons changed A -> B, listed by time
    sa = {(round(tt, 2), n) for tt, n in ev_a if n.startswith(("INFO_PRESSURE_STEP", "FAULT_HEAD"))}
    sb = {(round(tt, 2), n) for tt, n in ev_b if n.startswith(("INFO_PRESSURE_STEP", "FAULT_HEAD"))}
    out["A_only"] = sorted(sa - sb)[:20]
    out["B_only"] = sorted(sb - sa)[:20]
    return out


def main():
    out = Path(sys.argv[2])
    workers = int(sys.argv[3])
    cases = [str(c) for c in rc.case_dirs(sys.argv[4:])]
    t0 = time.perf_counter()
    with Pool(workers) as pool:
        res = pool.map(run_case, cases, chunksize=4)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r64_d1_replay.py",
                                        "spec": "rev. 64 P-S8-23 (d)", "roots": sys.argv[4:],
                                        "wall_s": round(time.perf_counter() - t0, 1)},
                               "runs": res}, indent=1, default=float), encoding="utf-8")
    print("done", len(res), "cases", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
