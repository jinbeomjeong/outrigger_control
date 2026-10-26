"""S7 control ③ preparation: R8 C2 (10 Hz, d = 1) closed loop on the L2b-NSC Chrono model.

``00_docs/03_chrono/chrono_build_plan.md`` S7 "제어 ③ 준비"; ``dynamics_model.md`` 5.23.4 (L2b
judges control ③, L1 bundle-C twins give the D8 minimum-force pair difference), 5.22.3 (NSC
read-out); controller and R8 settings as bundle C (``run_S6C.py``, ``s6_control_spec.md`` rev.
30-36). Judge module ``outrigger_sim.verify.s7_control``.

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py list --set ctrl3
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py plan --set ctrl3
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py check --set ctrl3 [--jobs 7]  # 0.3 s
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py check --set ctrl3 --duration 16 \
        --only L2b_...   # CHECK decision codes (C-R17)
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py run --set ctrl3 --approved [--jobs 7]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py judge --batch 07_results/S7/ctrl3_<stamp>
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py run --set ctrl3_rerun --approved --jobs 2
    python -I -X utf8 -u 04_scripts/02_chrono/run_S7C.py judge \
        --batch 07_results/S7/ctrl3_rerun_<stamp> [--pair-batch 07_results/S7/ctrl3_20261024_154939]

``run`` refuses without ``--approved`` (the user confirms the main run separately).
``ctrl3_rerun`` (U-S7-2, spec rev. 37 192): the L2b fup3.5 / roll5.5 cases with the identity
map; their L1 twins are those of :data:`CTRL3_PAIR_BATCH` (``s7c.pair_batch``, judged with
``--pair-batch`` or that setting).

L2b-NSC cases (engine ``L2b_NSC``):

* plant ``load_params(level, model="L2b_NSC")`` at the YAML values (beta 1.0 GPa, REXOME35 legs,
  rod-side law on, PSOR 50, dt 1e-4 s); controller ``C2Controller.from_params(load_params(level),
  run_S6C.controller_config(...))`` = the bundle-C controller at beta 1.0 (C-R11: nominal pad
  stiffness and ``k_oil(e)`` from the YAML), ``C2Config().with_10hz_d1()``, runner
  ``command_delay_periods`` 0 (``d`` = 1 inside the controller, R-4 guard);
* start: rigid NSC crawler on the case floor. The floor body and the machine body get the same
  rotation ``floor_rotation(floor_normal(roll, pitch))`` about ``(0, 0, crawler_bottom_z)``, so
  the zero-pose crawler spheres touch the plane; legs hang at extension 0 (``start="hanging"``).
  Settle :data:`CRAWLER_SETTLE_S` (ASSUMPTION; rigid crawler, no crawler rocking mode) with
  zero command, then the controller starts (the settle is recorded in ``result.json / l2b_start``).
  The crawler settle map of the controller is the **identity** (C-R17, U-S7-1, spec rev. 37
  191.4 (a)): the NSC crawler is rigid, so its physical map is the identity; the L1 map would
  read the floor 0.17-0.32 deg wrong (191.2, the ctrl3_20261024_154939 fup3.5 / roll5.5 false
  rejections). The L1 twins keep the 13.1 map. :func:`controller_settle_map` is the one rule
  (also for the S8 L2b runs); the map is recorded in ``acceptance.controller_settle_map`` and
  ``settings.s7c.controller_settle_map``. Everything else of the controller is the L1 twin's;
* valve: ``tau_v`` 0.1 s on the speed reference (``SpeedReference.configure_valve``: amplifier
  ramp none, command acceleration limit off, end cushion kept), i.e. on the flow that integrates
  into ``s_ref`` and drives the dashpot (module docstring of ``outrigger_sim.actuation``);
* sensors: IMU 100 Hz samples (``imu_config_for_grade(grade, sample_period_s=0.01)``, 10 ms box
  means, ``Measurements.imu_specific_force_samples_m_s2``), head / rod pressure and stroke 10 Hz
  instantaneous at the control instants (``L2bEngine.ideal_measurements``: ``p_h = (F + p_r
  A_ann) / A_p``, ``p_r``, ``stroke_m = s_ref``, ``stroke_corrected_m`` = piston ``s + F /
  k_out``), ideal leg sensors except the PS2 case (WIKA old_worst, calibration off);
* records: ``record/`` (10 Hz), ``pads.npz`` (``chrono/l2b_pad_record``: 1 ms, loads from the
  force-law output with the every-step minimum, contact force as a 20 ms centred mean),
  ``r8_series.npz``, events, probe history.

L1 twin cases (engine ``L1R``): ``run_S6C.job_bundle_c`` unchanged (L1-R, settled crawler
snapshots of ``07_results/states_L1R``), beta 1.0, same scenario; they exist because the bundle-C
batches have no beta 1.0 run of those D8 floors (H4V has one, used as a regression reference).

Outputs ``07_results/S7/ctrl3[_check]_<stamp>/<case>/``. Units SI.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
import warnings
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import run_S6C as s6c  # noqa: E402  (sets OUTRIGGER_ROD_SIDE_MECHANICS for the L1 twins)

st = s6c.st
RESULTS = ROOT / "07_results" / "S7"
MAX_WORKERS = 7
CHECK_DURATION_S = 0.3
CASE_TIMEOUT_S = 3600.0
CHECK_TIMEOUT_S = 900.0
CRAWLER_SETTLE_S = 3.0
"""ASSUMPTION: settle of the rigid NSC crawler with hanging legs before the controller starts
(no crawler compliance; the hanging rods ring on the lateral bushings, about 78 Hz)."""
SMOKE_READY_EXTRA_S = 52.0
"""Smoke case: added to the stage-2 flat length so that READY is held >= 60 s (stage-2 READY
window 10 s + R8 8 s + CHECK extension 8 s - margin)."""
PAD_RECORD_S = 1.0e-3
L2B_US_PER_STEP_7W = 300.0
"""Wall estimate of an L2b closed-loop step with 7 workers: ctrl3 check 2026-10-24 measured
261-291 us/step (runner, chrono_point IMU, pad record, contact window included; 4-7 workers),
rounded up."""
L1_WALL_S_PER_S = 3.5
"""L1 twin wall per simulated second, 7 workers: bundle-C rerun34 H4V 306 s for 93 s (3.3 s/s,
658 us/step at 2e-4 s) and the ctrl3 check 641-804 us/step, rounded up."""
H4V_L1_REFERENCE = ("07_results/S6/bundleC_rerun34_L1R_20261024_141040", "C1_H4V_top_fdown3.5")
CTRL3_PAIR_BATCH = "07_results/S7/ctrl3_20261024_154939"
"""U-S7-2 (spec rev. 37 192): the ctrl3 batch whose L1 twins pair the ``ctrl3_rerun`` cases."""
RERUN_TAGS = ("D8_top_fup3.5_b1.0", "D8_top_roll5.5_b1.0")
"""Spec rev. 37 192: the L2b cases re-run with the identity settle map."""
SETTLE_MAP_BY_ENGINE = {"L2b_NSC": "identity", "L1R": "level"}
"""C-R17 / U-S7-1 (spec rev. 37 191.4 (a)): controller crawler settle map per engine.
``identity`` = rigid crawler (physical map), ``level`` = ``CrawlerSettleMap.for_level`` (13.1,
the L1-R flexible crawler; set by ``run_S6C.controller_config``)."""


def controller_settle_map(engine: str, level: str):
    """(kind, ``CrawlerSettleMap``) the controller of ``engine`` uses (:data:`SETTLE_MAP_BY_
    ENGINE`)."""
    from outrigger_sim.control.target import CrawlerSettleMap

    kind = SETTLE_MAP_BY_ENGINE[engine]
    if kind == "identity":
        return kind, CrawlerSettleMap.identity()
    return kind, CrawlerSettleMap.for_level(level)


def apply_settle_map(config, engine: str, level: str):
    """``config`` with the target's ``crawler_settle_map`` set by :func:`controller_settle_map`
    (``None`` for the identity, the controller default); returns (config, meta)."""
    kind, smap = controller_settle_map(engine, level)
    target = replace(config.target, crawler_settle_map=None if smap.is_identity else smap)
    meta = {"kind": kind, "engine": engine, "coefficients": smap.to_meta(),
            "rule": "C-R17 / U-S7-1 (s6_control_spec rev. 37 191.4 (a))"}
    return replace(config, target=target), meta


@dataclass(frozen=True)
class Ctrl3Case:
    """One control ③ case: a bundle-C case definition run on ``engine``."""

    case_id: str
    engine: str  # "L2b_NSC" | "L1R"
    base: s6c.BundleCCase
    pair_l1: str | None = None
    external_l1: tuple[str, str] | None = None
    smoke: bool = False
    role: str = "pair"
    notes: tuple[str, ...] = field(default_factory=tuple)
    pair_batch: str | None = None
    """Batch directory (project-relative) holding ``pair_l1`` when this batch does not."""

    @property
    def duration_s(self) -> float:
        return self.base.duration_s

    def wall_estimate_s(self) -> float:
        if self.engine == "L1R":
            return 20.0 + L1_WALL_S_PER_S * self.duration_s
        steps = (self.duration_s + CRAWLER_SETTLE_S) / 1.0e-4
        return 20.0 + steps * L2B_US_PER_STEP_7W * 1e-6

    def to_meta(self) -> dict[str, Any]:
        return {"case_id": self.case_id, "engine": self.engine, "pair_l1": self.pair_l1,
                "external_l1": None if self.external_l1 is None else list(self.external_l1),
                "pair_batch": self.pair_batch,
                "controller_settle_map": SETTLE_MAP_BY_ENGINE[self.engine],
                "smoke": self.smoke, "role": self.role, "notes": list(self.notes),
                "duration_s": self.duration_s, "base": self.base.to_meta()}


def _bc(cid: str, sc: st.Stage2Case, **kw) -> s6c.BundleCCase:
    # config "C-1": the bundle-C base configuration (judge adds the C-8 rows as in bundle C)
    return s6c.BundleCCase(cid, "C-1", replace(sc, case_id=cid), **kw)


def ctrl3_cases() -> list[Ctrl3Case]:
    """Control ③ preparation set (dynamics 5.23.4; coordinator 2026-10-24): smoke + D8 boundary
    pairs + PS2 sensitivity, each on L2b with an L1 twin."""
    flat = s6c._sc("SMOKE", "G2", "top", "flat", extra=SMOKE_READY_EXTRA_S,
                   items=("2", "3", "4", "5", "7", "8"))
    ps2 = s6c._sc("PS2", "PS", "top", "fdown3.5", items=("PS",), pressure_grade="old_worst",
                  zero_calibration=False)
    defs = [
        ("smoke_top_flat", flat, {}, True, "smoke: levelling -> READY, >= 60 s stable"),
        ("D8_top_rpB_b1.0", s6c._d8("top", "rpB"), {}, False, "D8 diamond boundary twin"),
        ("D8_top_roll5.5_b1.0", s6c._d8("top", "roll5.5"), {}, False, "D8 roll 5.5 deg"),
        ("D8_top_fup3.5_b1.0", s6c._d8("top", "fup3.5"), {}, False,
         "D8 nose up 3.5 deg (H4 skipped nose up)"),
        ("H4V_top_fdown3.5", s6c._sc("H4V", "G2-R", "top", "fdown3.5",
                                     items=("R", "2", "3", "8")), {}, False,
         "H4 nose down 3.5 deg (REANCHOR)"),
        ("PS2_fdown3.5_old_worst_nocal", ps2, {"sensor_model": True}, False,
         "PS2 old_worst + no calibration (dynamics 5.23.3: judge on L2b)"),
    ]
    out = []
    for tag, sc, kw, smoke, note in defs:
        l1_id, l2_id = f"L1_{tag}", f"L2b_{tag}"
        ext = H4V_L1_REFERENCE if tag == "H4V_top_fdown3.5" else None
        out.append(Ctrl3Case(l2_id, "L2b_NSC", _bc(l2_id, sc, **kw), pair_l1=l1_id,
                             external_l1=ext, smoke=smoke, notes=(note,)))
        out.append(Ctrl3Case(l1_id, "L1R", _bc(l1_id, sc, **kw), smoke=smoke, role="twin",
                             notes=(note, "L1-R twin (bundle-C job, beta 1.0)")))
    ids = [c.case_id for c in out]
    if len(set(ids)) != len(ids):
        raise RuntimeError("duplicate ctrl3 case id")
    return out


def ctrl3_rerun_cases() -> list[Ctrl3Case]:
    """U-S7-2 (spec rev. 37 192): the two L2b cases that ended in an A1 false rejection under the
    L1 settle map, re-run with the identity map; L1 twins from :data:`CTRL3_PAIR_BATCH`."""
    base = {c.case_id: c for c in ctrl3_cases()}
    out = []
    for tag in RERUN_TAGS:
        c = base[f"L2b_{tag}"]
        out.append(replace(c, pair_batch=CTRL3_PAIR_BATCH,
                           notes=(*c.notes, "rerun U-S7-2: identity settle map (C-R17)")))
    return out


CASE_SETS = {"ctrl3": ctrl3_cases, "ctrl3_rerun": ctrl3_rerun_cases}


def case_table(case_set: str | None = None) -> dict[str, Ctrl3Case]:
    """Cases by id of ``case_set`` (all sets when None; a later set wins on a shared id)."""
    sets = CASE_SETS.values() if case_set is None else (CASE_SETS[case_set],)
    return {c.case_id: c for make in sets for c in make()}


# --- L2b job ------------------------------------------------------------------------------------


def l2b_crawler_start(params, floor: str):
    """(body pose, floor pose, floor normal) of the rigid crawler start (module docstring)."""
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.frames import matrix_to_quat
    from outrigger_sim.scenarios.slope import floor_normal, floor_rotation

    roll, pitch = st.FLOORS[floor]
    n = floor_normal(roll, pitch)
    rot = floor_rotation(n)
    p0 = np.array([0.0, 0.0, float(params.ground.crawler_bottom_z_m)])
    origin = tuple(float(v) for v in p0 - rot @ p0)
    quat = tuple(float(v) for v in matrix_to_quat(rot))
    return BodyPose(origin, quat), BodyPose(origin, quat), n


def settle_l2b(model, seconds: float) -> dict[str, Any]:
    """Step with zero command; returns the end state (last 0.1 s window means)."""
    import numpy as np

    from outrigger_sim.chrono.l2b_model import read_l2b_probe
    from outrigger_sim.frames import roll_pitch_from_quat

    n = round(seconds / model.dt_s)
    win = round(0.1 / model.dt_s)
    crawler, rp, speed, omega = [], [], [], []
    wall0 = time.perf_counter()
    for k in range(n):
        model.step()
        if k >= n - win:
            p = read_l2b_probe(model)
            crawler.append(float(p.crawler_contact_world_N @ p.floor_normal_world))
            rp.append(np.degrees(roll_pitch_from_quat(p.body_quat_wxyz)))
            speed.append(float(np.linalg.norm(p.body_vel_m_s)))
            omega.append(float(np.linalg.norm(p.body_omega_rad_s)))
    g = model.params.meta.gravity_m_s2
    w = (model.params.superstructure.mass_properties.mass_kg
         + sum(leg.moving_part.mass_kg for leg in model.params.legs)) * g
    normal = model.floor_normal_world()
    return {"settle_s": n * model.dt_s, "steps": n, "wall_s": time.perf_counter() - wall0,
            "crawler_normal_mean_N": float(np.mean(crawler)) if crawler else None,
            "weight_along_normal_N": float(w * normal[2]),
            "rods_on_crawler_note": "rod weights hang on the superstructure (legs in the air)",
            "body_roll_pitch_deg_mean": np.mean(rp, axis=0).tolist() if rp else None,
            "max_speed_m_s": max(speed) if speed else None,
            "max_omega_rad_s": max(omega) if omega else None,
            "window_s": win * model.dt_s}


S8_SEAL_PAD_FIELDS = ("F_pressure", "F_pressure_min_interval", "F_pressure_max_interval",
                      "f_seal", "seal_stuck", "s_piston", "F_seal_limit")
"""Fields the S8 recorder (``chrono/l2b_pad_record_s8.py``) adds to ``pads.npz`` on the
friction path; the S7 recorder (``l2b_pad_record.py``) already has ``head_pressure`` /
``rod_pressure`` (1 ms) and has no seal element to record."""


def l2b_pads_seal_fields_meta(params, model) -> dict[str, Any]:
    """C-2 (control 2026-10-26, before V-4 (1)): the S7 L2b ``pads.npz`` keeps the S7 fields.
    The S8 seal fields are recorded only on the friction path (F_s > 0 or counterbalance),
    which this runner does not build (``job_l2b`` refuses parameter overrides, YAML
    ``actuator.seal_friction.level_N`` = 0); the meta states why they are absent. A friction
    path here raises (the S8 runner records it)."""
    sf = getattr(getattr(params, "l2b", None), "seal_friction", None)
    level_N = 0.0 if sf is None else float(sf.level_N)
    friction_path = bool(getattr(model.actuator, "friction_path", False))
    if friction_path:
        raise RuntimeError("run_S7C L2b: friction path (F_s > 0 / CB) built; the S7 pad recorder "
                           "has no seal fields - use run_S8C (l2b_pad_record_s8)")
    return {"added": False, "fields_s8": list(S8_SEAL_PAD_FIELDS), "F_s_front_N": level_N,
            "friction_path": friction_path,
            "pressure_fields_present": ["head_pressure", "rod_pressure", "F_cyl"],
            "reason": "F_s = 0 (YAML actuator.seal_friction.level_N, no override in run_S7C): "
                      "no seal friction element, so F_pressure = F_cyl and f_seal = 0; nothing "
                      "to add (C-2, control 2026-10-26)"}


def job_l2b(case: Ctrl3Case, case_dir: Path, *, duration_s: float | None = None):
    """Run one L2b-NSC case. Returns (summary, run_meta)."""
    import numpy as np

    from outrigger_sim.chrono.l2b_engine import L2bEngine
    from outrigger_sim.chrono.l2b_model import L2bModel
    from outrigger_sim.chrono.l2b_pad_record import L2bPadRecorder
    from outrigger_sim.control.c2 import C2Controller, C2Phase
    from outrigger_sim.params import load_params
    from outrigger_sim.record import make_run_meta, save_record
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s6_bundle_c import classify_warning

    bcase = case.base
    sc = bcase.scenario
    if sc.event is not None:
        raise ValueError(f"{case.case_id}: floor events need settlement patches (L1 only)")
    if bcase.beta_GPa != 1.0 or bcase.L0r_m is not None or bcase.front_frame_stiffness_N_m:
        raise ValueError(f"{case.case_id}: L2b overrides are not implemented (YAML plant only)")
    params = load_params(level=sc.level, model="L2b_NSC")
    params_ctrl = load_params(level=sc.level)  # C-R11: controller at the YAML beta 1.0
    pose, floor_pose, normal = l2b_crawler_start(params, sc.floor)
    model = L2bModel(params, pose=pose, extensions_m=(0.0,) * 4, start="hanging", crawler=True,
                     floor_pose=floor_pose)
    model.actuator.configure_valve(tau_s=bcase.tau_v_s, amp_ramp=bcase.amp_ramp,
                                   amp_ramp_s=s6c.AMP_RAMP_S)
    start = settle_l2b(model, CRAWLER_SETTLE_S)
    t0 = float(model.system.GetChTime())
    engine = L2bEngine(model, imu_method="chrono_point")
    leg_sensors = st.leg_sensor_config_for(sc, t0) if bcase.sensor_model else LegSensorConfig()
    suite = SensorSuite(imu_config_for_grade(sc.grade, sample_period_s=s6c.IMU_SAMPLE_PERIOD_S),
                        leg_sensors, seed=sc.seed)
    config, settle_meta = apply_settle_map(s6c.controller_config(params_ctrl, bcase),
                                           case.engine, sc.level)
    # U-S8-61 (spec 304 1): L2b-NSC keeps the preset R-5 fallback ratio (column_nominal)
    from outrigger_sim.chrono.fallback_ratio import with_engine_fallback_ratio

    config, fallback_ratio_meta = with_engine_fallback_ratio(config, case.engine)
    c2 = C2Controller.from_params(params_ctrl, config)
    pads = L2bPadRecorder(engine, every_steps=max(1, round(PAD_RECORD_S / model.dt_s)))
    sat_rec = s6c.SaturationRecorder(model, t0)
    series = s6c.R8Series(model, c2)
    phases: list[tuple[float, str]] = []
    probe_intervals: list[dict[str, Any]] = []
    probe_margins: list[dict[str, Any]] = []
    stroke_hi = float(params.legs[0].extension_range_m[1])
    state = {"ready_t": None, "probe_t": None}

    def observe(meas, command):
        series(meas, command)
        ph = c2.phase
        n_rounds = len(c2.probe_history)
        if not phases or phases[-1][1] != ph.value:
            if phases and phases[-1][1] == "probe" and probe_intervals:
                iv = probe_intervals[-1]
                iv.update(t_end_s=meas.t_s - t0, next_phase=ph.value,
                          rounds_completed=n_rounds - iv["rounds_at_start"])
                iv["interrupted_by_relevel"] = ph.value == "level" and iv["rounds_completed"] == 0
            if ph.value == "probe":
                probe_intervals.append({"t_start_s": meas.t_s - t0, "rounds_at_start": n_rounds})
                s_ref = model.actuator.reference.s_ref_m
                probe_margins.append({"t_s": meas.t_s - t0,
                                      "margin_m": [stroke_hi - float(v) for v in s_ref],
                                      "stroke_meas_m": [float(v) for v in meas.stroke_m]})
            phases.append((meas.t_s - t0, ph.value))
        if ph is C2Phase.READY and state["ready_t"] is None:
            state["ready_t"] = meas.t_s
        if ph is C2Phase.PROBE and state["probe_t"] is None:
            state["probe_t"] = meas.t_s

    c2_meta = st.c2_config_meta(config)
    expect = st.expected_reanchor(sc, c2_meta["reanchor_direction"])
    bundle = {**bcase.to_meta(), "param_overrides": {}, "controller_param_overrides": {},
              "controller_params_beta_GPa": s6c.CONTROLLER_BETA_GPA,
              "fallback_ratio": fallback_ratio_meta,
              "pads_seal_fields": l2b_pads_seal_fields_meta(params, model),
              "valve": model.actuator.valve_meta(),
              "imu_sample_period_s": s6c.IMU_SAMPLE_PERIOD_S,
              "leg_sensors": "WIKA error model" if bcase.sensor_model
              else "ideal (LegSensorConfig())",
              "c2_implementation": s6c.c2_implementation_status(c2),
              "controller_timing": c2.meta().get("timing"),
              "gyro_noise_std_rad_s_passed": config.target.gyro_noise_std_rad_s,
              "params_sha256": params.sha256, "params_sha256_controller": params_ctrl.sha256,
              "saturation_stop_s": model.actuator.saturation_stop_s}
    settings = {**asdict(sc), "snapshot": None, "start_t_s": t0, **c2_meta,
                "reanchor_expected": expect, "bundle_c": bundle,
                "s7c": {**case.to_meta(), "engine": "L2b_NSC",
                        "controller_settle_map_meta": settle_meta},
                "l2b_start": {"floor_normal_world": normal.tolist(),
                              "floor_pose": asdict(floor_pose), "body_pose": asdict(pose),
                              "extensions_m": list(model.extensions_m), "settle": start,
                              "crawler": "rigid NSC spheres (layout D), mu "
                                         f"{params.l2b.rigid_floor.crawler_friction}"},
                "leg_sensors": leg_sensors.to_meta(), "controller_config": str(config),
                "gyro_bias_removal": "CHECK standstill" if sc.check_time_s > 0.0 else "none"}
    run_meta = make_run_meta(params, engine.meta(), scenario=f"S7C_{case.case_id}",
                             scenario_settings=settings, sensors=suite.setup(),
                             reference_sha256=load_references().sha256_by_file())
    wall0 = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        res = run_closed_loop(engine, c2, suite, duration_s or case.duration_s,
                              run_meta=run_meta, on_control=observe, command_delay_periods=0,
                              command_offset_s=bcase.command_offset_s,
                              step_hook=st._chain_hooks(pads, sat_rec),
                              placement=st.run_placement())
    wall = time.perf_counter() - wall0
    observed = []
    for w in caught:
        cls = classify_warning(str(w.message), w.category.__name__, bcase.beta_GPa)
        cls.update(filename=Path(str(w.filename)).name, lineno=w.lineno)
        observed.append(cls)
    bundle["warnings"] = observed
    bundle["warnings_unexpected_count"] = sum(1 for w in observed if not w["expected"])
    bundle["saturation_steps"] = sat_rec.meta()
    save_record(res.record, case_dir / "record")
    pads.save(case_dir / "pads.npz")
    series_info = series.save(case_dir / s6c.R8_SERIES_NAME)
    events = [str(e) for e in c2.events]
    probes = [[asdict(r) if hasattr(r, "__dataclass_fields__") else str(r) for r in rnd]
              for rnd in c2.probe_history]
    (case_dir / "probe_history.json").write_text(json.dumps(probes, indent=1, default=str),
                                                 "utf-8")
    (case_dir / "controller_events.json").write_text(json.dumps(events, indent=1), "utf-8")
    arr = res.record.arrays
    s_motor = np.asarray(arr["s_motor"])
    reanchor = c2.reanchor_outcome
    ctl_meta = c2.meta()
    p_floor = np.asarray(model.floor_point_world_m, dtype=float)
    acceptance = {
        "target_code": None if c2.target_code is None else str(c2.target_code),
        "crawler_attitude_deg": None if c2.crawler_attitude_rad is None
        else [math.degrees(a) for a in c2.crawler_attitude_rad],
        "target_checks": [str(c) for c in c2.target_checks],
        "last_check": (ctl_meta.get("target", {}).get("checks") or [None])[-1],
        "floor_estimate_rad": ctl_meta.get("target", {}).get("floor_estimate_rad"),
        "floor_estimate_touch": ctl_meta.get("floor_estimate_touch"),
        "floor_true_deg": st.FLOORS[sc.floor],
        "slope_limit_mode": "verification",
        "controller_settle_map": settle_meta,
        "controller_settle_map_in_meta": ctl_meta.get("target", {}).get("crawler_settle_map"),
        "settle_map_note": f"controller settle map {settle_meta['kind']} on the rigid NSC "
                           "crawler (C-R17 / U-S7-1, module docstring)",
    }
    summary = {
        "case": case.case_id, "settings": settings, "phases": phases,
        "events_count": len(events), "acceptance": acceptance,
        "h4": {"enabled": sc.h4, "outcome": None if reanchor is None else str(reanchor),
               "expected": expect, "direction": ctl_meta.get("reanchor_direction"),
               "n_reanchor_skipped_nose_up": sum(1 for e in events
                                                 if "reanchor_skipped:nose_up" in e),
               "n_reanchor_started": sum(1 for e in events if "reanchor_started" in e)},
        "c2": c2_meta,
        "stroke": {"max_m": s_motor.max(axis=0), "min_m": s_motor.min(axis=0),
                   "margin_to_end_m": stroke_hi - s_motor.max(axis=0),
                   "coordinate": "s_ref (L2b; = L1 motor position)"},
        "controller_meta": ctl_meta,
        "probe_start_stroke_margin": probe_margins,
        "probe_events": [e for e in events if "probe" in e],
        "probe_skipped": [e for e in events if "probe_skipped" in e],
        "floor_plane": {"normal_world": normal.tolist(), "offset_m": float(normal @ p_floor)},
        "ready_t_s": None if state["ready_t"] is None else state["ready_t"] - t0,
        "probe_intervals": probe_intervals,
        "first_probe_t_s": None if state["probe_t"] is None else state["probe_t"] - t0,
        "event_t_s": None, "fine_dt": None, "seed": sc.seed, "target_request": None,
        "r8_series": series_info,
        "pad_record": pads.meta(),
        "piston_monitor": model.actuator.piston_monitor(),
        "rod_side_lock_table": None if model.actuator.rod_side is None
        else model.actuator.rod_side.lock_table(),
        "monitor": engine.step_monitor(),
        "runner": {**res.meta, "wall_s": wall, "n_steps": res.n_steps,
                   "n_control": res.n_control,
                   "us_per_step": wall / max(res.n_steps, 1) * 1e6},
    }
    engine.close()
    return summary, run_meta


# --- batch ---------------------------------------------------------------------------------------


def job_case(case, case_dir):
    """Batch job (module level for spawn)."""
    from outrigger_sim.batch import CaseResult

    s = case.settings
    c = case_table(s.get("case_set"))[case.case_id]
    d = Path(case_dir)
    if c.engine == "L2b_NSC":
        summary, run_meta = job_l2b(c, d, duration_s=s.get("duration_s"))
    else:
        summary, run_meta = s6c.job_bundle_c(c.base, d, duration_s=s.get("duration_s"))
        summary["settings"]["s7c"] = {**c.to_meta(), "engine": "L1R",
                                      "controller_settle_map_meta": {
                                          "kind": SETTLE_MAP_BY_ENGINE["L1R"],
                                          "engine": "L1R",
                                          "note": "run_S6C.controller_config (13.1 map)"}}
    (d / "result.json").write_text(json.dumps(s6c._plain(summary), indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    return CaseResult(summary=s6c._plain({k: summary[k] for k in ("case", "phases", "runner")}),
                      run_meta=run_meta)


def plan(case_set: str, ids=None) -> dict[str, Any]:
    cases = [c for c in CASE_SETS[case_set]() if ids is None or c.case_id in ids]
    rows = [{"case_id": c.case_id, "engine": c.engine, "duration_s": c.duration_s,
             "wall_estimate_s": c.wall_estimate_s(), "pair_l1": c.pair_l1,
             "blocked": c.base.blocked_in(s6c.STATES) if c.engine == "L1R" else None}
            for c in cases]
    walls = [r["wall_estimate_s"] for r in rows]
    return {"cases": rows, "count": len(rows), "serial_wall_s": sum(walls),
            "makespan_7_s": st.lpt_makespan_s(sorted(walls, reverse=True), MAX_WORKERS),
            "basis": f"L2b {L2B_US_PER_STEP_7W:g} us/step (dt 1e-4 s, 7 workers, ASSUMPTION) "
                     f"+ crawler settle {CRAWLER_SETTLE_S:g} s; L1 {L1_WALL_S_PER_S:g} s/s"}


def run_batch(ids, jobs: int, *, check: bool, case_set: str, check_duration_s: float):
    from outrigger_sim.batch import Case, run_cases

    table = case_table(case_set)
    bad = [c for c in ids if c not in table]
    if bad:
        raise SystemExit(f"unknown cases: {bad}")
    blocked = [c for c in ids if table[c].engine == "L1R" and table[c].base.blocked_in(s6c.STATES)]
    if blocked:
        raise SystemExit(f"L1 twins without a start snapshot: {blocked}")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / (f"{case_set}_check_{stamp}" if check else f"{case_set}_{stamp}")
    batch_dir.mkdir(parents=True, exist_ok=True)
    meta = {"mode": "check" if check else "run", "case_set": case_set, "cases": ids,
            "jobs": jobs, "check_duration_s": check_duration_s if check else None,
            "c2_readiness": s6c.rerun34_readiness(),
            "controller_settle_map": {c: SETTLE_MAP_BY_ENGINE[table[c].engine] for c in ids},
            "settle_map_rule": "C-R17 / U-S7-1 (s6_control_spec rev. 37 191.4 (a))",
            "pair_batch": {c: table[c].pair_batch for c in ids if table[c].pair_batch},
            "env": {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS",
                                                    "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
            "plan": plan(case_set, set(ids))}
    (batch_dir / "batch_meta.json").write_text(json.dumps(s6c._plain(meta), indent=1), "utf-8")
    order = sorted(ids, key=lambda c: -table[c].wall_estimate_s())
    cases = [Case(c, {"duration_s": check_duration_s if check else None, "case_set": case_set})
             for c in order]
    t0 = time.perf_counter()
    report = run_cases(cases, job_case, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CHECK_TIMEOUT_S if check else CASE_TIMEOUT_S)
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += "\n" + (o.error or "")[-2500:]
        print(msg, flush=True)
    print(f"batch wall {time.perf_counter() - t0:.1f} s, jobs {jobs} -> {batch_dir}", flush=True)
    return report, batch_dir


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("list", "plan", "check", "run", "judge"))
    ap.add_argument("--set", dest="case_set", choices=tuple(CASE_SETS), default="ctrl3")
    ap.add_argument("--jobs", type=int, default=MAX_WORKERS)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--duration", type=float, default=CHECK_DURATION_S)
    ap.add_argument("--batch")
    ap.add_argument("--out")
    ap.add_argument("--pair-batch", dest="pair_batch",
                    help="judge: batch holding the L1 twins (default: s7c.pair_batch)")
    ap.add_argument("--allow-env-override", action="store_true",
                    help="run / check: start even with OUTRIGGER_L1_FALLBACK_RATIO_SOURCE set "
                         "(B(iii) comparison batch; the L1 twins take the override)")
    args = ap.parse_args(argv)
    jobs = max(1, min(args.jobs, MAX_WORKERS))
    if args.action in ("run", "check"):
        from outrigger_sim.chrono.fallback_ratio import refuse_env_override

        refuse_env_override(args.allow_env_override, f"run_S7C {args.action}")
    if args.action == "list":
        for c in CASE_SETS[args.case_set]():
            print(f"{c.case_id:36s} {c.engine:8s} {c.duration_s:6.1f} s  "
                  f"~{c.wall_estimate_s():6.0f} s wall  pair {c.pair_l1 or '-'}")
        return
    if args.action == "plan":
        doc = plan(args.case_set, set(args.only) if args.only else None)
        print(json.dumps(s6c._plain(doc), indent=1))
        return
    if args.action == "judge":
        from outrigger_sim.verify.s7_control import judge_batch

        print("->", judge_batch(Path(args.batch), None if not args.out else Path(args.out),
                                pair_batch=None if not args.pair_batch else Path(args.pair_batch)))
        return
    ids = args.only or [c.case_id for c in CASE_SETS[args.case_set]()]
    if args.action == "check":
        run_batch(ids, jobs, check=True, case_set=args.case_set, check_duration_s=args.duration)
        return
    if not args.approved:
        raise SystemExit("control ③ main run needs the user's confirmation: add --approved")
    run_batch(ids, jobs, check=False, case_set=args.case_set, check_duration_s=0.0)


if __name__ == "__main__":
    main(sys.argv[1:])
