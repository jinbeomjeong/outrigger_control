"""S6 branch A runs (Chrono infrastructure): V11b, V17 path, sensor truth, V13, 60 s smoke,
force-saturation regression.

``00_docs/03_chrono/chrono_build_plan.md`` S6; checks in ``outrigger_sim.verify.s6``.
Usage (Chrono-dev python, from any folder)::

    python -I -X utf8 -u run_S6.py run     [--jobs 6] [--only CASE ...]  # batch + summary
    python -I -X utf8 -u run_S6.py summary                               # rebuild the summary
    python -I -X utf8 -u run_S6.py list
    python -I -X utf8 -u run_S6.py snaps2 [--jobs 7] [--only NAME ...]   # stage-2 snapshots
    python -I -X utf8 -u run_S6.py plan2 [--set SET ...]                 # stage-2 matrix plan
    python -I -X utf8 -u run_S6.py run2 --go [--jobs 7] [--only CASE ...] # stage 2 (s6_stage2)
    python -I -X utf8 -u run_S6.py run2 --go --set RE1 RE1c [--jobs 7]   # re-run sets only

``--set`` (plan2 / run2): restrict the stage-2 matrix to the re-run sets of
``s6_stage2.RERUN_SETS`` (``RE1``, ``RE2``, ``RE1b``, ``RE1c``, ``RE3`` = all 38 stage-2
cases, ``RE3new`` = the five rev. 7 cases, ``B1`` = the top nose-down B1′ cases; several
allowed, union of their case ids); without it the full matrix is used. ``check2``: R5 GE1′
name preflight (``run2`` runs it first unless ``--no-ge1-check``).

Cases (L1, YAML ``simulation.L1.dt_s`` unless the id says otherwise):

* ``truth_static``: superstructure fixed at a tilted pose (roll 2 deg, pitch -1.5 deg, yaw
  10 deg) high above the floor, legs hanging on their motors; closed loop (runner + hold
  controller + ideal sensors) 0.2 s for the IMU point C1 and a far point (2.0, -1.0, 3.0) m,
  both IMU truth methods -> sensor truth (f = R^T (0, 0, g), omega = 0, p A = F, strokes).
* ``v11b_<leg>_dt<dt>``: single-leg model (``chrono.single_leg``), extend into the 210 bar
  head limit, retract into the pull limit, extend again (schedule :data:`V11B_SCHEDULE`).
* ``v17_<level>``: restore ``07_results/states/S1_L1_<level>`` into the actuated model,
  closed loop with the hold controller, ideal sensors, 10 s; locked pressure report with and
  without the locked mask, per-step maxima, sensor truth on the settled state, V13.
* ``smoke60_top``: same start (top), 60 s closed-loop smoke test (V13, record kept).
* ``regress_lift_<on|off>``: S3 V4 lift (top, layout D, ``S2b_crawler_top``, general dt, no
  transition window) with the force saturation on / off; the summary compares the sampled
  states bit for bit (runs that never reach the limits must be identical).

Outputs: ``07_results/S6/batch_<stamp>/<case>/`` (case.json, case.log, result.json,
series.npz, Record directories), ``07_results/S6/index.json``, ``07_results/S6/batches.json``;
summary ``06_analysis/01_chrono/16_S6/verify_S6_L1_infra.json`` and figures
``verify_S6_L1_infra_v11b.png``, ``verify_S6_L1_infra_smoke.png``.
Units SI; angles in deg where named ``*_deg``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S6"
INDEX = RESULTS / "index.json"
STATES = ROOT / "07_results" / "states"
sys.path.insert(0, str(HERE))
import l1r_variant as _l1rv  # noqa: E402

STATES = _l1rv.tagged(STATES)
"""Bundle B (L1-R on): ``07_results/states_L1R`` (stage-2 crawler snapshots built with L1-R;
the settlement cases use them too since 2026-10-22; the older ``*_L1Roff`` twins there were
their L1-R-off start states)."""
ANALYSIS_DIR = ROOT / "06_analysis" / "01_chrono" / "16_S6"
SUMMARY = ANALYSIS_DIR / "verify_S6_L1_infra.json"
FIG_V11B = ANALYSIS_DIR / "verify_S6_L1_infra_v11b.png"
FIG_SMOKE = ANALYSIS_DIR / "verify_S6_L1_infra_smoke.png"
MAX_WORKERS = 7
"""P-cores used (i7-14700: 8 P-cores, 7 for cases)."""
DEFAULT_JOBS = 6
CASE_TIMEOUT_S = 1500.0
LEVELS = ("top", "middle", "bottom")
V17_DURATION_S = 10.0
SMOKE_DURATION_S = 60.0
TRUTH_DURATION_S = 0.2
TRUTH_POSE_DEG = (2.0, -1.5, 10.0)
"""roll, pitch, yaw of the fixed-body sensor-truth case (ZYX, body -> world)."""
TRUTH_FAR_POINT_M = (2.0, -1.0, 3.0)
V11B_SCHEDULE = ((0.0, 0.0), (0.1, 1.0), (3.0, -1.0), (5.5, 1.0))
"""(t, speed / v_max) of the single-leg V11b run, end :data:`V11B_END_S`."""
V11B_END_S = 6.0
REGRESS_SAMPLE_S = 1.0e-3
F_MIN_KEY = "control.F_min_cylinder_N"
"""YAML F_min (10 % of the mean leg load, cylinder-force basis; 9,414.59 N on the REXOME35 YAML,
CLAUDE.md 2026-10-22). Read per run so that the info flag follows the YAML (was 9,453.0 N)."""
LEGS = ("FL", "FR", "RL", "RR")
CODE_FILES = (
    "04_scripts/02_chrono/run_S6.py",
    "03_src/outrigger_sim/runner.py",
    "03_src/outrigger_sim/chrono/actuators.py",
    "03_src/outrigger_sim/chrono/model.py",
    "03_src/outrigger_sim/chrono/truth.py",
    "03_src/outrigger_sim/chrono/l1_engine.py",
    "03_src/outrigger_sim/chrono/single_leg.py",
    "03_src/outrigger_sim/verify/s6.py",
    "03_src/outrigger_sim/chrono/ground_bushing.py",
    "03_src/outrigger_sim/chrono/ground_settlement.py",
    "03_src/outrigger_sim/chrono/pad_record.py",
    "04_scripts/02_chrono/s6_stage2.py",
)


def _plain(value):
    import numpy as np

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _rel(path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


# --- case table -----------------------------------------------------------------------------


def case_ids() -> list[str]:
    return (
        ["smoke60_top", "regress_lift_on", "regress_lift_off"]
        + [f"v17_{lv}" for lv in LEVELS]
        + ["v11b_FL_dt1e-5", "v11b_RL_dt1e-5", "v11b_FL_dt2e-4", "v11b_RL_dt2e-4",
           "truth_static"]
    )


def case_settings(case_id: str) -> dict:
    from outrigger_sim.params import load_params

    dt_gen = float(load_params(level="top").simulation.L1.dt_s)
    if case_id == "truth_static":
        return {"kind": "truth", "level": "top", "dt": dt_gen}
    if case_id.startswith("v11b_"):
        _, leg, dts = case_id.split("_")
        dt = float(dts.removeprefix("dt"))
        return {"kind": "v11b", "leg": leg, "dt": dt, "level": "top"}
    if case_id.startswith("v17_"):
        level = case_id.removeprefix("v17_")
        if level not in LEVELS:
            raise SystemExit(f"unknown case {case_id!r}")
        return {"kind": "hold", "level": level, "dt": dt_gen, "duration_s": V17_DURATION_S,
                "start": f"snapshot S1_L1_{level}"}
    if case_id == "smoke60_top":
        return {"kind": "hold", "level": "top", "dt": dt_gen, "duration_s": SMOKE_DURATION_S,
                "start": "snapshot S1_L1_top", "grade": "ideal"}
    if case_id.startswith("regress_lift_"):
        flag = case_id.removeprefix("regress_lift_")
        if flag not in ("on", "off"):
            raise SystemExit(f"unknown case {case_id!r}")
        return {"kind": "regress", "level": "top", "dt": dt_gen, "force_saturation": flag == "on"}
    raise SystemExit(f"unknown case {case_id!r}")


# --- helpers --------------------------------------------------------------------------------


PDELTA_JSON = ROOT / "06_analysis" / "00_dynamics" / "s1_pdelta_check.json"
"""dyn independent nonlinear (P-delta) statics per level, V17 reference (U3 = a)."""


def _reference_sha256():
    from outrigger_sim.verify.reference import load_references

    shas = dict(load_references().sha256_by_file())
    shas[PDELTA_JSON.name] = hashlib.sha256(PDELTA_JSON.read_bytes()).hexdigest()
    return shas


def _run_meta(params, engine_meta, scenario, settings, sensors=None, extra=None):
    from outrigger_sim.record import make_run_meta

    return make_run_meta(params, engine_meta, scenario=scenario, scenario_settings=settings,
                         sensors=sensors, reference_sha256=_reference_sha256(),
                         extra=extra or {})


def _ideal_suite(grade=None, mount=None):
    """Sensor suite with error-free leg sensors; IMU = the named grade, or error-free
    (``ImuErrorConfig()``, no bias, no noise) when ``grade`` is None. Note: grade "ideal"
    of plan S6 has no zero error but 15 ug/rtHz noise."""
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M, ImuErrorConfig, imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite

    imu = ImuErrorConfig() if grade is None else imu_config_for_grade(grade)
    return SensorSuite(imu, LegSensorConfig(), seed=20261021,
                       imu_mount_point_body_m=IMU_MOUNT_C1_BODY_M if mount is None else mount)


def _restored_actuated(params, refs, level, dt):
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose

    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt, actuator=True)
    snap = f"S1_L1_{level}"
    t0 = model.restore(load_snapshot(snap, params_sha256=params.sha256, directory=STATES))
    return model, t0, {"kind": f"snapshot {snap}", "t_s": t0, "params_sha256": params.sha256}


def _record_arrays(record):
    return {k: __import__("numpy").asarray(v) for k, v in record.arrays.items()}


# --- jobs -----------------------------------------------------------------------------------


def job_truth(case, case_dir):
    """Fixed tilted superstructure: sensor truth at C1 and a far point, both IMU methods."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.l1_engine import L1Engine
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.chrono.truth import IMU_METHODS
    from outrigger_sim.control.hold import HoldController
    from outrigger_sim.frames import quat_from_euler_zyx
    from outrigger_sim.params import load_params
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.s6 import sensor_truth_checks

    s = dict(case.settings)
    params = load_params(level=s["level"])
    roll, pitch, yaw = (math.radians(a) for a in TRUTH_POSE_DEG)
    quat = tuple(float(c) for c in quat_from_euler_zyx(yaw, pitch, roll))
    pose = BodyPose((0.3, -0.2, params.ground.crawler_bottom_z_m + 4.0), quat)
    variants = []
    checks = []
    meta = None
    for point_name, point in (("C1", IMU_MOUNT_C1_BODY_M), ("far", TRUTH_FAR_POINT_M)):
        for method in IMU_METHODS:
            model = L1Model(params, pose=pose, extensions_m=operating_extensions_m(params),
                            crawler=False, attach_bushings=False, actuator=True,
                            dt_s=float(s["dt"]))
            model.superstructure.SetFixed(True)
            engine = L1Engine(model, imu_mount_point_body_m=point, imu_method=method)
            suite = _ideal_suite(mount=point)
            run_meta = _run_meta(params, engine.meta(), f"S6_{case.case_id}", s,
                                 sensors=suite.setup())
            res = run_closed_loop(engine, HoldController(), suite, TRUTH_DURATION_S,
                                  run_meta=run_meta)
            arr = _record_arrays(res.record)
            tag = f"{point_name}_{method}"
            c = sensor_truth_checks(arr, gravity_m_s2=params.meta.gravity_m_s2,
                                    head_area_m2=engine.sensor_truth.head_area_m2,
                                    k_oil_N_m=engine.sensor_truth.k_oil_N_m, case=tag,
                                    stroke_m=params.actuator.stroke_m)
            checks += c
            variants.append({"point": point_name, "point_body_m": list(point), "method": method,
                             "f_mean_m_s2": arr["meas.specific_force"].mean(axis=0),
                             "F_cyl_mean_N": arr["F_cyl"].mean(axis=0),
                             "n_samples": int(arr["t"].shape[0]),
                             "monitor": engine.step_monitor()})
            meta = run_meta
            engine.close()
    g = params.meta.gravity_m_s2
    from outrigger_sim.frames import quat_to_matrix

    expected = quat_to_matrix(np.asarray(quat)).T @ np.array([0.0, 0.0, g])
    summary = {"case": case.case_id, "settings": s, "pose_deg": TRUTH_POSE_DEG,
               "quat_wxyz": quat, "expected_f_m_s2": expected, "variants": variants,
               "checks": summary_table(checks), "all_passed": all_passed(checks)}
    return CaseResult(summary=_plain(summary), run_meta=meta)


def job_v11b(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.single_leg import SingleLegModel, run_schedule
    from outrigger_sim.params import load_params
    from outrigger_sim.record import make_run_meta
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.s6 import (
        V11B_INERTIA_FACTOR,
        v11b_analysis,
        v11b_checks,
        v17_checks,
        v17_reports,
    )

    s = dict(case.settings)
    params = load_params(level=s["level"])
    model = SingleLegModel(params, s["leg"], dt_s=float(s["dt"]))
    v = params.actuator.max_speed_m_s
    schedule = [(t, f * v) for t, f in V11B_SCHEDULE]
    t0 = time.perf_counter()
    a = run_schedule(model, schedule, V11B_END_S)
    wall = time.perf_counter() - t0
    f_ext, f_ret = model.actuator.force_limits_N
    g = params.meta.gravity_m_s2
    ana = v11b_analysis(a, f_ext_N=f_ext, f_ret_N=f_ret, v_max_m_s=v,
                        rod_mass_kg=model.rod_mass_kg, gravity_m_s2=g,
                        spring_c_N_s_m=model.spring_c_N_s_m, spring_k_N_m=model.spring_k_N_m)
    t_sat = model.actuator.saturation_stop_s
    inertia_limit = V11B_INERTIA_FACTOR * model.rod_mass_kg * v / t_sat
    checks = v11b_checks(ana, f_ext_N=f_ext, f_ret_N=f_ret, ramp_s=model.actuator.ramp_s,
                         dt_s=model.dt_s, case=case.case_id, inertia_limit_N=inertia_limit)
    from outrigger_sim.params import LEG_ORDER
    from outrigger_sim.sensors.hydraulic import leg_head_areas_from_params

    # per-leg area (legs.<leg>.cylinder.*, REXOME35); the common bore without those keys
    head_area = float(leg_head_areas_from_params(params)[LEG_ORDER.index(model.leg)])
    p = (a["F_cyl"] / head_area)[:, None].repeat(4, axis=1)
    masks = v17_reports(a["t"], p, float(params.get("actuator.locked_pressure_limit_Pa")),
                        a["u_cmd"][:, None].repeat(4, axis=1),
                        a["u_applied"][:, None].repeat(4, axis=1))
    checks += [c for c in v17_checks(masks, level=case.case_id, ref_max_Pa=None, tol_Pa=0.0,
                                     relief_Pa=float(params.get("actuator.relief_pressure_moving_Pa")))
               if c.id.endswith(("not_exceeded", "moving_relief"))]
    np.savez_compressed(Path(case_dir) / "series.npz", **a)
    expected_creep = model.spring_c_N_s_m * v / model.spring_k_N_m
    summary = {
        "case": case.case_id, "settings": s, "schedule_m_s": schedule, "end_s": V11B_END_S,
        "model": model.meta(), "analysis": ana, "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "expected_creep_c_v_over_k_m": expected_creep,
        "expected_inertial_dip_m_v_over_dt_N": model.rod_mass_kg * v / model.dt_s,
        "saturation_law": {"law": "C (dyn rev. 23)", "t_sat_s": t_sat,
                           "inertia_limit_N": inertia_limit,
                           "saturation_start_count": model.actuator.saturation_start_count,
                           "saturation_step_count": model.actuator.saturation_step_count},
        "mask_comparison_single_leg": {"note": "leg index 0 repeated x4 (single leg)",
                                       "all_samples_max_Pa": masks["all_samples"]["max_pressure_Pa"],
                                       "locked_only_max_Pa": None if masks["locked_only"] is None
                                       else masks["locked_only"]["max_pressure_Pa"],
                                       "moving_max_Pa": masks["moving_max_Pa"],
                                       "locked_fraction": masks["locked_fraction_per_leg"]["FL"]},
        "timing": {"wall_s": wall, "steps": len(a["t"]), "us_per_step": wall / len(a["t"]) * 1e6},
    }
    meta = make_run_meta(params, model.meta(), scenario=f"S6_{case.case_id}",
                         scenario_settings=s, reference_sha256=_reference_sha256())
    return CaseResult(summary=_plain(summary), run_meta=meta)


def job_hold(case, case_dir):
    """Restore S1 state (actuated), hold controller closed loop: V17 path, truth, V13."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.l1_engine import L1Engine
    from outrigger_sim.control.hold import HoldController
    from outrigger_sim.frames import roll_pitch_from_quat
    from outrigger_sim.params import load_params
    from outrigger_sim.record import save_record
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.reference import (
        HYDRAULIC_MAX_STATIC_HEAD_PRESSURE_PA,
        TOTAL_WEIGHT_INCL_RODS_N,
        load_references,
    )
    from outrigger_sim.verify.s6 import (
        V17_TOL_W4_FRACTION,
        imu_static_residual,
        sensor_truth_checks,
        v13_checks,
        v17_checks,
        v17_pdelta_checks,
        v17_reports,
    )

    s = dict(case.settings)
    level = s["level"]
    params = load_params(level=level)
    refs = load_references()
    model, t0, start = _restored_actuated(params, refs, level, float(s["dt"]))
    engine = L1Engine(model)
    suite = _ideal_suite(s.get("grade"))
    controller = HoldController()
    run_meta = _run_meta(params, engine.meta(), f"S6_{case.case_id}", {**s, "start": start},
                         sensors=suite.setup())
    res = run_closed_loop(engine, controller, suite, float(s["duration_s"]), run_meta=run_meta)
    record = res.record
    save_record(record, Path(case_dir) / "record")
    arr = _record_arrays(record)
    monitor = engine.step_monitor()
    head_area = engine.sensor_truth.head_area_m2
    limit = float(params.get("actuator.locked_pressure_limit_Pa"))
    p_true = arr["F_cyl"] / head_area
    rep_true = v17_reports(arr["t"], p_true, limit, arr["u_cmd"], arr["u_applied"])
    rep_meas = v17_reports(arr["t"], arr["meas.head_pressure"], limit, arr["u_cmd"],
                           arr["u_applied"])
    weight = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N))
    tol_pa = V17_TOL_W4_FRACTION * weight / 4.0 / head_area
    # per leg (FL, FR, RL, RR) since the REXOME35 cylinders (info only, see U3 below)
    ref_max = ([float(x) for x in refs.get(HYDRAULIC_MAX_STATIC_HEAD_PRESSURE_PA)] if level == "top" else None)
    # U3 = (a): judged against the P-delta solution; the linear maximum is info (no ref_max)
    checks = v17_checks(rep_true, level=level, ref_max_Pa=None, tol_Pa=tol_pa,
                        step_max_force_N=monitor["cylinder_force_max_N"],
                        head_area_m2=head_area,
                        relief_Pa=float(params.get("actuator.relief_pressure_moving_Pa")))
    pd = json.loads(PDELTA_JSON.read_text(encoding="utf-8"))[level]
    pd_cyl = np.asarray(pd["nonlinear_cyl_N"], dtype=float)
    lin_cyl = pd_cyl - np.asarray(pd["nonlinear_minus_linear_N"], dtype=float)
    checks += v17_pdelta_checks(level=level, settled_max_cyl_N=monitor["cylinder_force_max_N"],
                                pdelta_cyl_N=pd_cyl, linear_cyl_N=lin_cyl, w4_N=weight / 4.0)
    checks += sensor_truth_checks(arr, gravity_m_s2=params.meta.gravity_m_s2,
                                  head_area_m2=head_area, k_oil_N_m=engine.sensor_truth.k_oil_N_m,
                                  case=case.case_id, imu_static=False,
                                  stroke_m=params.actuator.stroke_m)
    checks += v13_checks(arr, monitor, case.case_id)
    rp = np.degrees(np.array([roll_pitch_from_quat(q) for q in arr["body_quat_wxyz"]]))
    f_cyl = arr["F_cyl"]
    fmin = float(params.get(F_MIN_KEY))
    np.savez_compressed(Path(case_dir) / "series.npz", t=arr["t"] - t0, roll_pitch_deg=rp,
                        F_cyl=f_cyl, head_pressure=arr["meas.head_pressure"],
                        specific_force=arr["meas.specific_force"],
                        angular_rate=arr["meas.angular_rate"],
                        stroke=arr["meas.stroke"], stroke_corrected=arr["meas.stroke_corrected"],
                        F_contact_n=arr["F_contact_n"])
    summary = {
        "case": case.case_id, "settings": s, "start": start, "dt_s": engine.dt_s,
        "v17": {"true_pressure": rep_true, "meas_pressure_ideal": rep_meas,
                "tol_Pa": tol_pa, "tol_basis": "0.1 % W/4 / A_head, W = statics "
                "total_weight_incl_rods_N (S1 V1 tolerance, proposal)",
                "ref_max_static_head_pressure_Pa": ref_max,
                "step_monitor_max_pressure_Pa": (np.asarray(monitor["cylinder_force_max_N"])
                                                 / head_area).tolist()},
        "imu_residual_settled": imu_static_residual(arr, params.meta.gravity_m_s2),
        "stroke_motor_minus_true_mm": ((arr["meas.stroke"] - arr["meas.stroke_corrected"])
                                       .mean(axis=0) * 1e3).tolist(),
        "attitude": {"roll_mean_deg": float(rp[:, 0].mean()), "pitch_mean_deg": float(rp[:, 1].mean()),
                     "roll_span_deg": float(np.ptp(rp[:, 0])), "pitch_span_deg": float(np.ptp(rp[:, 1])),
                     "drift_roll_deg": float(rp[-1, 0] - rp[0, 0]),
                     "drift_pitch_deg": float(rp[-1, 1] - rp[0, 1])},
        "cylinder_force": {"min_N": f_cyl.min(axis=0).tolist(), "max_N": f_cyl.max(axis=0).tolist(),
                           "mean_N": f_cyl.mean(axis=0).tolist(), "f_min_N": fmin,
                           "all_above_f_min": bool(np.all(f_cyl >= fmin))},
        "monitor": monitor, "checks": summary_table(checks), "all_passed": all_passed(checks),
        "runner": {"n_steps": res.n_steps, "n_control": res.n_control,
                   "steps_per_period": res.steps_per_period, "wall_s": res.wall_s,
                   "us_per_step": res.wall_s / res.n_steps * 1e6,
                   "commands_all_zero": bool(np.all(res.command_m_s == 0.0)),
                   "meta": res.meta},
        "record_dir": "record", "record_samples": int(arr["t"].shape[0]),
    }
    engine.close()
    return CaseResult(summary=_plain(summary), run_meta=run_meta)


def job_regress(case, case_dir):
    """S3 V4 lift with the force saturation on / off; sampled state for the bitwise compare."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.chrono.runs import run_windowed
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.crawler_settle import crawler_static_pose
    from outrigger_sim.scenarios.lift import lift_plan
    from outrigger_sim.verify.reference import (
        L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
        LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
        load_references,
    )

    s = dict(case.settings)
    params = load_params(level=s["level"])
    refs = load_references()
    touch_ref = [float(v) for v in refs.get(LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D)]
    f1 = float(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level=s["level"])[0])
    plan = lift_plan(params, reference_touch_eq_s=touch_ref, first_rocking_Hz=f1)
    pose = crawler_static_pose(params)
    model = L1Model(params, pose=BodyPose(pose.origin_m, pose.quat_wxyz),
                    extensions_m=(0.0, 0.0, 0.0, 0.0), attach_bushings=False, actuator=True,
                    dt_s=float(s["dt"]), force_saturation=bool(s["force_saturation"]))
    snap = load_snapshot("S2b_crawler_top", params_sha256=params.sha256, directory=STATES)
    model.restore(snap)
    model.actuator.set_soft_limits(hi_m=plan.e_op_m)
    rows = {k: [] for k in ("t", "origin", "quat", "vel", "omega", "Fcyl", "s_motor", "N",
                            "anchor", "s_ref", "u_applied")}

    def sample(probe):
        rows["t"].append(probe.t_s)
        rows["origin"].append(probe.body_pos_m)
        rows["quat"].append(probe.body_quat_wxyz)
        rows["vel"].append(probe.body_vel_m_s)
        rows["omega"].append(probe.body_omega_rad_s)
        rows["Fcyl"].append(probe.motor_force_N)
        rows["s_motor"].append(probe.motor_pos_m)
        rows["N"].append(probe.pad_normal_force_N)
        rows["anchor"].append(probe.bushing_anchor_world_m)
        rows["s_ref"].append(model.actuator.acting_s_ref_m)
        rows["u_applied"].append(model.actuator.acting_u_m_s)

    t0 = time.perf_counter()
    run = run_windowed(model, plan.end_s, plan.schedule(), windows=[], base_dt_s=float(s["dt"]),
                       sample_s=REGRESS_SAMPLE_S, on_sample=sample)
    wall = time.perf_counter() - t0
    arrays = {k: np.asarray(v, dtype=float) for k, v in rows.items()}
    np.savez_compressed(Path(case_dir) / "series.npz", **arrays)
    digest = hashlib.sha256()
    for k in sorted(arrays):
        digest.update(k.encode())
        digest.update(np.ascontiguousarray(arrays[k]).tobytes())
    summary = {
        "case": case.case_id, "settings": s, "plan_end_s": plan.end_s,
        "samples": int(arrays["t"].shape[0]), "series_sha256": digest.hexdigest(),
        "max_motor_force_N": run.max_motor_force_N, "max_motor_force_t_s": run.max_motor_force_t_s,
        "events": len(run.events),
        "saturation_step_count": model.actuator.saturation_step_count.tolist(),
        "force_limits_N": model.actuator.force_limits_N,
        "timing": {"wall_s": wall, "steps": run.steps, "us_per_step": wall / run.steps * 1e6},
    }
    return CaseResult(summary=_plain(summary), run_meta=_run_meta(params, model.meta(),
                      f"S6_{case.case_id}", s))


def job_stage2_case(case, case_dir):
    """Batch job of stage 2 (module level for spawn): s6_stage2.job_stage2."""
    from outrigger_sim.batch import CaseResult

    sys.path.insert(0, str(HERE))
    import s6_stage2

    summary, run_meta = s6_stage2.job_stage2(case.case_id, Path(case_dir), STATES)
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    return CaseResult(summary=_plain(summary), run_meta=run_meta)


def job_stage2_snapshot(case, case_dir):
    """Batch job: one settled crawler snapshot of stage 2 (s6_stage2.job_snapshot)."""
    from outrigger_sim.batch import CaseResult

    sys.path.insert(0, str(HERE))
    import s6_stage2

    s = case.settings
    summary = s6_stage2.job_snapshot(s["level"], s["floor"], Path(case_dir), STATES,
                                     off=bool(s.get("off", False)))
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    return CaseResult(summary=_plain(summary), run_meta=None)


def stage2_snapshots(jobs, only=None):
    """Build the 14 settled crawler snapshots of stage 2 (07_results/states/S6_crawler_*)."""
    from outrigger_sim.batch import Case, run_cases

    sys.path.insert(0, str(HERE))
    import s6_stage2

    triples = [(lv, f, False) for lv, f in s6_stage2.SNAPSHOTS]
    if _l1rv.is_on():  # bundle B: L1-R-off twins (none since settlement supports L1-R)
        triples += [(lv, f, True) for lv, f in s6_stage2.OFF_SNAPSHOTS]
    triples = [(lv, f, off) for lv, f, off in triples
               if not only or s6_stage2.snapshot_name(lv, f, off=off) in only]
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"snapshots{_l1rv.suffix()}_{stamp}"
    cases = [Case(s6_stage2.snapshot_name(lv, f, off=off), {"level": lv, "floor": f, "off": off})
             for lv, f, off in triples]
    report = run_cases(cases, job_stage2_snapshot, out, max_workers=jobs, placement="pcore",
                       timeout_s=1200.0)
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += "\n" + (o.error or "")[-2000:]
        print(msg, flush=True)
    print(f"-> {_rel(out)}")
    return report


def stage2_plan(sets=None):
    """Write and print the stage-2 matrix plan (no simulation); ``sets`` restricts it."""
    sys.path.insert(0, str(HERE))
    import s6_stage2

    ids = None if not sets else {c for name in sets for c in s6_stage2.RERUN_SETS[name]}
    doc = s6_stage2.plan_document(STATES, ids=ids)
    doc["sets"] = sets or "full matrix"
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "stage2_plan.json"
    path.write_text(json.dumps(_plain(doc), indent=1, ensure_ascii=False), encoding="utf-8")
    for r in doc["cases"]:
        print(f"{r['case_id']:34s} {r['duration_s']:6.1f} s sim  ~{r['wall_estimate_s']:6.1f} s wall"
              f"  {r['blocked'] or 'runnable'}")
    print(json.dumps(doc["counts"]), json.dumps(doc["wall_estimate"]))
    print(f"plan -> {_rel(path)}")
    return doc


def stage2_check():
    """R5 GE1′ name preflight (no physics): prints and returns ``s6_stage2.ge1_r5_preflight``."""
    sys.path.insert(0, str(HERE))
    import s6_stage2

    pre = s6_stage2.ge1_r5_preflight()
    pre["c2_config"] = s6_stage2.default_c2_meta()  # spec 86.6: revision + REANCHOR direction
    pre["nose_up_h4_cases"] = s6_stage2.plan_document(STATES)["nose_up_h4_cases"]
    print(json.dumps(pre, indent=1))
    return pre


def run_stage2(ids, jobs, go, ge1_check=True):
    """Run stage-2 cases (only with --go; blocked cases are refused; the R5 GE1′ names are
    checked first unless ``ge1_check`` is False)."""
    from outrigger_sim.batch import Case, run_cases

    sys.path.insert(0, str(HERE))
    import s6_stage2

    if not go:
        raise SystemExit("stage 2 waits for the dyn rulings and the coordinator's go: add --go")
    if ge1_check:
        pre = s6_stage2.ge1_r5_preflight()
        if not pre["ok"]:
            raise SystemExit(
                f"C2 {pre['revision']} lacks the R5 GE1' names {sorted(pre['missing'])} "
                "(s6_stage2.GE1_R5_REQUIRED, spec rev. 7 42.1/42.2): fix the names to the R5 "
                "delivery or pass --no-ge1-check")
    # spec 86.6 / dynamics return condition 1: stage 2 runs the default C2 configuration
    # (REANCHOR nose_down_only); the revision is read from control.c2, never hard-coded
    c2_meta = s6_stage2.default_c2_meta()
    if c2_meta.get("reanchor_direction") != "nose_down_only":
        raise SystemExit(f"default C2 REANCHOR direction is {c2_meta.get('reanchor_direction')!r}, "
                         "spec 86.6 expects 'nose_down_only' (C2Config default)")
    print(f"C2 {c2_meta['c2_revision']}, REANCHOR direction {c2_meta['reanchor_direction']}",
          flush=True)
    table = {c.case_id: c for c in s6_stage2.all_cases()}
    ids = ids or [c for c, v in table.items() if v.blocked_in(STATES) is None]
    bad = [c for c in ids if c not in table or table[c].blocked_in(STATES)]
    if bad:
        raise SystemExit(f"unknown or blocked stage-2 cases: {bad}")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    import l1r_variant

    batch_dir = RESULTS / f"stage2{l1r_variant.suffix()}_{stamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "batch_meta.json").write_text(json.dumps({
        "c2": c2_meta, "l1r": l1r_variant.meta(),
        "settlement_cases_l1r_off": [],  # settlement + L1-R supported (2026-10-22)
        "nose_up_h4_cases": [c for c in ids if s6_stage2.expected_reanchor(
            table[c], c2_meta["reanchor_direction"])["expected"] == "reanchor_skipped:nose_up"],
        "note": "spec 86.6: nose-up H4 cases stay in the matrix and run nose_down_only; expected "
                "reanchor_skipped:nose_up once, REANCHOR rows not applicable (nose_up)"},
        indent=1), encoding="utf-8")
    report = run_cases([Case(c, {"kind": "stage2"}) for c in ids], job_stage2_case, batch_dir,
                       max_workers=jobs, placement="pcore", timeout_s=s6_stage2.CASE_TIMEOUT_S)
    for o in report.outcomes:
        print(f"{o.case_id}: {o.status} {o.wall_s:.1f}s", flush=True)
    return report


def job(case, case_dir):
    """Batch job (module level for spawn): dispatch on ``case.settings['kind']``."""
    fn = {"truth": job_truth, "v11b": job_v11b, "hold": job_hold,
          "regress": job_regress}[case.settings["kind"]]
    out = fn(case, Path(case_dir))
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(dict(out.summary)), indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# --- batch ----------------------------------------------------------------------------------


def run_batch(ids, jobs):
    from outrigger_sim.batch import Case, run_cases

    if not 1 <= jobs <= MAX_WORKERS:
        raise SystemExit(f"--jobs must be 1..{MAX_WORKERS}")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / f"batch_{stamp}"
    order = [c for c in case_ids() if c in ids] + [c for c in ids if c not in case_ids()]
    cases = [Case(c, case_settings(c)) for c in order]
    t0 = time.perf_counter()
    report = run_cases(cases, job, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CASE_TIMEOUT_S)
    wall = time.perf_counter() - t0
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += f"\n{(o.error or '')[-2500:]}"
        print(msg, flush=True)
    print(f"batch wall {wall:.1f} s, jobs {jobs} -> {_rel(batch_dir)}", flush=True)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    for o in report.outcomes:
        if o.status == "ok":
            index[o.case_id] = _rel(batch_dir / o.case_id)
    RESULTS.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    log = RESULTS / "batches.json"
    hist = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    hist.append({"batch": _rel(batch_dir), "cases": order, "jobs": jobs, "wall_s": wall,
                 "placement": "pcore (EcoQoS off), outrigger_sim.hostcpu.place_process",
                 "env_threads": {k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS",
                                                                "MKL_NUM_THREADS")},
                 "note": "wall times of concurrent cases are not unit costs",
                 "case_wall_s": {o.case_id: o.wall_s for o in report.outcomes},
                 "status": {o.case_id: o.status for o in report.outcomes}})
    log.write_text(json.dumps(hist, indent=1), encoding="utf-8")
    return report


# --- summary --------------------------------------------------------------------------------


def _load_results():
    if not INDEX.exists():
        return {}
    out = {}
    for cid, rel in json.loads(INDEX.read_text(encoding="utf-8")).items():
        p = ROOT / rel / "result.json"
        if p.exists():
            out[cid] = json.loads(p.read_text(encoding="utf-8"))
            out[cid]["_dir"] = rel
    return out


def code_sha256() -> dict[str, str]:
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}


def regression_section(res):
    import numpy as np

    on, off = res.get("regress_lift_on"), res.get("regress_lift_off")
    if on is None or off is None:
        return {"available": False}
    a = np.load(ROOT / on["_dir"] / "series.npz")
    b = np.load(ROOT / off["_dir"] / "series.npz")
    fields = {k: bool(np.array_equal(a[k], b[k], equal_nan=True)) for k in a.files}
    return {
        "available": True,
        "scenario": "S3 V4 lift (top, layout D, S2b_crawler_top, general dt, no window)",
        "samples": on["samples"], "sample_s": REGRESS_SAMPLE_S,
        "sha256_on": on["series_sha256"], "sha256_off": off["series_sha256"],
        "bit_identical": on["series_sha256"] == off["series_sha256"] and all(fields.values()),
        "fields_equal": fields,
        "saturation_steps_on": on["saturation_step_count"],
        "max_motor_force_on_N": on["max_motor_force_N"],
        "max_motor_force_off_N": off["max_motor_force_N"],
        "dirs": [on["_dir"], off["_dir"]],
    }


def summarize():
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.reference import load_references

    res = _load_results()
    params = load_params(level="top")
    checks = []
    for cid in case_ids():
        r = res.get(cid)
        if r is None or "checks" not in r:
            continue
        for c in r["checks"]:
            checks.append({**c, "case": cid})
    reg = regression_section(res)
    if reg.get("available"):
        checks.append({"id": "S6.regression.bit_identical", "item": "force saturation on/off, "
                       "lift run never saturated: sampled states bit-identical", "value":
                       reg["bit_identical"], "ref": True, "passed": bool(reg["bit_identical"])
                       and not any(reg["saturation_steps_on"]), "case": "regress_lift_*"})
    n_fail = sum(1 for c in checks if not c["passed"])
    doc = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": "S6 branch A (Chrono infrastructure): V11b, V17 path, sensor truth, V13, "
                     "60 s closed-loop smoke, force-saturation regression",
            "script": "04_scripts/02_chrono/run_S6.py",
            "checks_module": "outrigger_sim.verify.s6",
            "judgement": "cad-expert pre-check; physical judgement by dynamics-expert",
            "dt_yaml_s": float(params.simulation.L1.dt_s),
            "params_file_sha256": params.file_sha256,
            "reference_sha256": load_references().sha256_by_file(),
            "code_sha256": code_sha256(),
            "code_sha256_note": "sha256 of the listed files when this summary was written; "
                                "the case results come from the batches in 'batches' (stage-1 "
                                "code unchanged since batch_20261021_194136 except stage-2 "
                                "files s6_stage2.py / run_S6.py stage-2 actions, which the "
                                "stage-1 cases do not use)",
            "batches": json.loads((RESULTS / "batches.json").read_text(encoding="utf-8"))
            if (RESULTS / "batches.json").exists() else [],
        },
        # Information only (not read by any check); judged tolerances (0.04 mm, 1 %,
        # 1.5 m_rod v/t_sat) live in outrigger_sim.verify.s6 and are unchanged.
        "v11b_expected_ranges": {
            "source": "dynamics_model.md 5.12.12 supplement 8 (REXOME35, per leg; replica law C "
                      "lag 1 − v_max dt ± 1 um)",
            "creep_from_first_saturation_mm": {
                "FL": {"dt_2e-4": {"extend": [0.0210, 0.0230], "retract": [0.0193, 0.0213]},
                       "dt_1e-5": {"extend": [0.0266, 0.0286], "retract": [0.0265, 0.0285]}},
                "RL": {"dt_2e-4": {"extend": [0.0253, 0.0273], "retract": [0.0272, 0.0292]},
                       "dt_1e-5": {"extend": [0.0312, 0.0332], "retract": [0.0313, 0.0333]}},
            },
            "judged_tolerance_mm": 0.04,
            "peak_over_limit": {leg: {"extend": "<= 1.001", "retract": "<= 1.003"}
                                for leg in ("FL", "RL")},
            "reading_inertia_kN": {"FL": [1.10, 1.16], "RL": [0.75, 0.80]},
            "settled_window_motion_um": {"FL": "<= 2", "RL": "<= 2"},
            "settled_mean_force_over_limit": {"FL": "1.000 +- 0.002", "RL": "1.000 +- 0.002"},
        },
        "counts": {"checks": len(checks), "failed": n_fail},
        "checks": checks,
        "v11b": {cid: {k: res[cid][k] for k in ("analysis", "expected_creep_c_v_over_k_m",
                                                  "expected_inertial_dip_m_v_over_dt_N",
                                                  "mask_comparison_single_leg", "model",
                                                  "timing", "_dir")}
                 for cid in case_ids() if cid.startswith("v11b_") and cid in res},
        "v17": {cid: {k: res[cid][k] for k in ("v17", "imu_residual_settled", "attitude",
                                                 "cylinder_force", "monitor",
                                                 "stroke_motor_minus_true_mm", "_dir")}
                for cid in case_ids() if cid.startswith(("v17_", "smoke")) and cid in res},
        "runner": {cid: res[cid]["runner"] for cid in res if "runner" in res[cid]},
        "truth_static": res.get("truth_static"),
        "regression": reg,
    }
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(_plain(doc), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"summary -> {_rel(SUMMARY)}: {len(checks)} checks, {n_fail} failed", flush=True)
    for c in checks:
        if not c["passed"]:
            print(f"  FAIL {c['id']} [{c.get('case')}]: {c.get('value')}", flush=True)
    _figures(res)


def _figures(res):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from outrigger_sim.params import load_params

    from outrigger_sim.chrono.actuators import leg_force_limits_N

    params = load_params(level="top")
    ext_all, ret_all = leg_force_limits_N(params)  # per leg (legs.<leg>.cylinder.*), LEG_ORDER
    f_ext, f_ret = ext_all[0], ret_all[0]  # the V11b figure case is leg FL
    cid = "v11b_FL_dt2e-4"
    if cid in res:
        a = np.load(ROOT / res[cid]["_dir"] / "series.npz")
        fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
        ax[0].plot(a["t"], a["F_cyl"] / 1e3, lw=0.8, color="#1f5aa6", label="F_cyl")
        ax[0].axhline(f_ext / 1e3, color="#b03a2e", lw=0.8, ls="--",
                      label=f"+{f_ext / 1e3:.1f} kN (210 bar)")
        ax[0].axhline(-f_ret / 1e3, color="#7d3c98", lw=0.8, ls="--",
                      label=f"-{f_ret / 1e3:.1f} kN (210 bar)")
        ax[0].set_ylabel("cylinder force [kN]")
        ax[0].legend(loc="upper right", fontsize=8)
        ax[1].plot(a["t"], (a["s_motor"] - a["s_motor"][0]) * 1e3, lw=0.8, color="#1f5aa6")
        ax[1].set_ylabel("stroke change [mm]")
        ax[2].plot(a["t"], a["u_cmd"] * 1e3, lw=0.8, color="#888888", label="u_cmd")
        ax[2].plot(a["t"], a["u_applied"] * 1e3, lw=0.8, color="#1f5aa6", label="u_applied")
        ax[2].set_ylabel("leg speed [mm/s]")
        ax[2].set_xlabel("time [s]")
        ax[2].legend(loc="upper right", fontsize=8)
        fig.suptitle("S6 V11b single leg FL, dt 2e-4 s: 210 bar force saturation per step")
        fig.tight_layout()
        fig.savefig(FIG_V11B, dpi=130)
        plt.close(fig)
    cid = "smoke60_top"
    if cid in res:
        a = np.load(ROOT / res[cid]["_dir"] / "series.npz")
        fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
        rp = a["roll_pitch_deg"]
        ax[0].plot(a["t"], (rp[:, 0] - rp[0, 0]) * 1e6, lw=0.8, label="roll - roll(0)")
        ax[0].plot(a["t"], (rp[:, 1] - rp[0, 1]) * 1e6, lw=0.8, label="pitch - pitch(0)")
        ax[0].set_ylabel("attitude change [udeg]")
        ax[0].legend(fontsize=8)
        p = a["head_pressure"] / 1e5
        for i, leg in enumerate(LEGS):
            ax[1].plot(a["t"], p[:, i], lw=0.8, label=leg)
        ax[1].set_ylabel("head pressure [bar]")
        ax[1].legend(fontsize=8, ncol=4)
        f = a["specific_force"]
        ax[2].plot(a["t"], (f[:, 2] - f[:, 2].mean()) * 1e3, lw=0.6, label="f_z - mean")
        ax[2].plot(a["t"], (f[:, 0] - f[:, 0].mean()) * 1e3, lw=0.6, label="f_x - mean")
        ax[2].set_ylabel("IMU specific force [mm/s^2]")
        ax[2].set_xlabel("time since start [s]")
        ax[2].legend(fontsize=8)
        fig.suptitle("S6 closed-loop smoke 60 s, top, hold controller, IMU ideal (C1)")
        fig.tight_layout()
        fig.savefig(FIG_SMOKE, dpi=130)
        plt.close(fig)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("run", "summary", "list", "plan2", "run2", "snaps2",
                                       "check2"))
    ap.add_argument("--go", action="store_true", help="run2 only: really run stage 2")
    ap.add_argument("--no-ge1-check", action="store_true",
                    help="run2: skip the R5 GE1' name preflight (s6_stage2.ge1_r5_preflight)")
    ap.add_argument("--set", nargs="*", dest="sets",
                    help="run2 / plan2: re-run sets of s6_stage2.RERUN_SETS (RE1 RE2 RE1b RE1c "
                         "RE3 RE3new B1)")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    if args.action == "list":
        print("\n".join(case_ids()))
        return
    if args.action == "summary":
        summarize()
        return
    if args.action == "snaps2":
        stage2_snapshots(min(args.jobs, MAX_WORKERS), args.only)
        return
    if args.action == "check2":
        stage2_check()
        return
    if args.action == "plan2":
        stage2_plan(args.sets)
        return
    if args.action == "run2":
        ids = args.only
        if args.sets:
            sys.path.insert(0, str(HERE))
            import s6_stage2

            ids = sorted({c for name in args.sets for c in s6_stage2.RERUN_SETS[name]})
        run_stage2(ids, min(args.jobs, MAX_WORKERS), args.go, ge1_check=not args.no_ge1_check)
        return
    ids = args.only or case_ids()
    for c in ids:
        case_settings(c)
    run_batch(ids, args.jobs)
    summarize()


if __name__ == "__main__":
    main(sys.argv[1:])
