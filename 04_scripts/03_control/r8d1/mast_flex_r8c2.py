"""G5 re-judgement of the equivalent flexible mast with the project R8 C2 (dynamics_model.md 3.9.7).

``04_scripts/01_dynamics/run_mast_flex_c2_check.py`` (rmf) judged the one-mode-per-direction
equivalent flexible mast with the R7 it3 copy of C2 (50 Hz, ``run_c2_timedomain.C2D``); its JSON
``mast_flex_c2_check.json`` stays the R7 record. This driver runs the project controller
:class:`outrigger_sim.control.c2.C2Controller` with :meth:`C2Config.with_10hz_d1` on the same
plant (rmf ``FlexPlant``), so every final-preset function (LAS-b, C4G2, P-S8-30, R-2, sample
confirmation, S_ii normalisation) is in the loop. rmf is used as a plant / equivalent-mast
library only and is not modified in behaviour.

Loop (as ``c2py_r8d1_closed_loop.run_imu_100hz_flat``, generalised to slope, mast and beta): one
control period of 0.1 s = ten 10 ms IMU samples, each of ten 1 ms chunks (2 physics steps of
5e-4 s) with the exact mean of the first-order valve lag tau_v (ASSUMPTION 0.1 s, spec 138 C-1).
At the period end the controller reads the head pressure ``F / A_p`` (net-force basis, no
rod-side sensor), the motor and the corrected stroke and the gyro; its command is output one
period later (``d = 1`` inside the controller). The record grid is 20 ms (``rcc.T_CTRL``) so that
``rcc.metrics`` counts its sample times and moving averages as for R7.

Departures from the full preset: zero calibration OFF, target check OFF, REANCHOR OFF in the
matrix (group ``reanchor_on`` with the preset H4), no rod-side L1-R law, one leg damping value;
ideal sensors except the seed axis of ``robust`` (R7 noise sizes, ASSUMPTION).

Conventions: body x forward, y left, z up; pitch > 0 nose down; leg order FL, FR, RL, RR; SI.

Run (project root, dynamics-dev, E-cores 16..27 at below-normal priority are set by the script):
  conda run -n dynamics-dev python -I -B 04_scripts/03_control/r8d1/mast_flex_r8c2.py --stage smoke
  conda run -n dynamics-dev python -I -B 04_scripts/03_control/r8d1/mast_flex_r8c2.py --stage main
  conda run -n dynamics-dev python -I -B 04_scripts/03_control/r8d1/mast_flex_r8c2.py --stage robust
Writes 06_analysis/00_dynamics/mast_flex_c2_check_r8.json (``robust`` adds to it) and
mast_flex_c2_check_r8_{timeseries,slope_map,robust}.png.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import subprocess
import sys
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field, replace
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
sys.path.insert(0, str(PROJECT_ROOT / "04_scripts" / "01_dynamics"))
sys.path.insert(0, str(HERE.parent))
import dyn_model as dm  # noqa: E402
import run_control_comparison as rcc  # noqa: E402
import run_mast_bending_check as mbc  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.control.c2 import (  # noqa: E402
    C2Config,
    C2Controller,
    C2Phase,
    ContactJudge,
    ReanchorSettings,
    TargetSettings,
)
from outrigger_sim.control.target import TargetAcceptance  # noqa: E402
from outrigger_sim.control.zero_calibration import ZeroCalibrationMode  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.signals import Measurements  # noqa: E402

LOG = logging.getLogger("mast_flex_r8c2")

OUT_JSON = rmf.OUT_DIR / "mast_flex_c2_check_r8.json"
FIG_STEM = "mast_flex_c2_check_r8"
R7_JSON = rmf.OUT_JSON
C2PY_SCRIPT = HERE / "c2py_r8d1_closed_loop.py"

VALVE_LAG_S = 0.1
"""ASSUMPTION (spec 138 C-1): first-order valve lag on the issued leg speed."""
LAG_CHUNK_S = 0.001
RECORD_GRID_S = 0.02
"""Record grid = ``rcc.T_CTRL``: ``rcc.metrics`` counts samples x 0.02 s and averages 50 of them."""
GAINSET_NAME = "R8_C2_with_10hz_d1"
CTRL_LABEL = "R8 C2 (10 Hz, d 1, tau_v 0.1 s)"
TIMESERIES_XLIM_S = (15, 70)

MASTS = ("rigid", *rmf.FLEX)
SERIES_SLOPES = ("diag3", "pitch+3.7")
KEY_SLOPES = ("pitch+3.5", "pitch+3.7", "diag2.8", "diag3", "diag3.2", "roll+5.7")
MAST_ZETAS = (0.012, 0.023)
LEG_DAMPING_SCALE = 1.0 / 3.0
LEG_DAMPING_SLOPES = ("flat", "roll+3", "diag3", "pitch+3.7")
SEAL_FRICTION_N = (4e3, 8e3)
"""ASSUMPTION: the CLAUDE.md seal-friction sensitivity 4 / 8 kN, the same on every leg."""
SEAL_FRICTION_SLOPES = ("flat", "diag3", "pitch+3.7")
REANCHOR_SLOPES = ("pitch+2.5", "pitch+3", "pitch+3.3", "pitch+3.5", "pitch+3.7")

ROBUST_BETAS_PA = (0.69e9, 1.6e9)
ROBUST_TAU_V_S = (0.05, 0.15)
ROBUST_SEEDS = (12345, 12346, 12347)
ROBUST_AXIS_BY_GROUP = {"robust_beta": "beta", "robust_tau_v": "tau_v", "robust_seed": "seed"}

SMOKE_HOLD_S = 5.0
"""Smoke and convergence runs stop at READY + 5 s (the c2py flat run)."""
SMOKE_CASES = (("flat", "rigid"), ("diag3", "rigid"), ("diag3", "lower"), ("pitch+3.7", "stiff"))
SMOKE_EXPECTED = {
    # (slope, mast): touch s, crawler lift-off s, READY s, min true force kN (100 ms samples),
    # mast alpha max (LAT, FA) deg, steady |attitude| deg (spec table 5, control-expert)
    ("flat", "rigid"): (19.9, 21.0, 39.1, 58.29, None, 0.0107),
    ("diag3", "rigid"): (20.3, 21.3, 54.2, 46.58, None, 0.0153),
    ("diag3", "lower"): (20.3, 21.2, 54.1, 54.11, (0.125, 0.064), 0.0165),
    ("pitch+3.7", "stiff"): (20.5, 21.5, 56.1, 50.76, (0.001, 0.035), 0.0157),
}
CONVERGENCE_DT_S = 2.5e-4
CONVERGENCE_MIN_FORCE_TOL_KN = 0.05
CONVERGENCE_READY_TOL_S = 0.2

T1_LIMIT_S = 120.0
T1_HOLD_S = 5.0

DEPARTURES = (
    "zero calibration OFF (no CHECK round trip)",
    "target check OFF (TargetAcceptance.OFF, check_time 0)",
    "REANCHOR OFF in the matrix and sensitivities (group reanchor_on: preset H4 on)",
    "no rod-side sensor and no L1-R rod-side law (head reading = net force / A_p)",
    "single leg damping value (LOCK reference)",
    "valve: exact first-order lag tau_v on the issued command (no extra ramp)",
)
EXTRA_RUN_KEYS = (
    "tau_v_s",
    "reanchor",
    "phase_final",
    "fault_names",
    "warn_names",
    "event_counts",
    "commands_sha256",
    "controller_revision",
    "dt_s",
    "min_true_cyl_force_period_kN",
    "max_abs_attitude_after_ready_period_deg",
    "peak_leg_speed_mm_s",
)


@dataclass(frozen=True)
class RunCase:
    """One closed-loop run of the R8 C2 on the flexible-mast plant."""

    level: str
    slope: str
    mast: str
    group: str
    mast_eq: dict | None
    zeta_mast: float | None = None
    beta_Pa: float = 1.0e9
    seal_friction_N: float = 0.0
    leg_damping_scale: float = 1.0
    tau_v_s: float = VALVE_LAG_S
    seed: int | None = None
    reanchor: bool = False
    limit_s: float = rcc.T_MAX
    hold_s: float = rcc.T_HOLD
    dt_s: float = rcc.DT
    keep_series: bool = False

    @property
    def slope_deg(self) -> tuple[float, float]:
        """Floor (roll, pitch) in degrees."""
        return rmf.SLOPE_ANG[self.slope]


@dataclass
class MetricsRecord:
    """The controller attributes ``rcc.metrics`` reads, filled from the R8 run."""

    c: Any
    t_touch: float | None = None
    t_done: float | None = None
    t_ready_first: float | None = None
    fault: bool = False
    probe_time: float = 0.0
    probe_rounds: int = 0
    events: list[str] = field(default_factory=list)
    probe_log: list = field(default_factory=list)


class SensorNoise:
    """Robust seed axis: R7 sensor sizes (``rcc.CA``) on the R8 samples (ASSUMPTION)."""

    def __init__(self, seed: int, g: float) -> None:
        imu = rcc.CA["imu_nominal"]
        self.rng = np.random.default_rng(seed)
        self.imu_bias = np.array([*imu["bias_mg"], 0.0]) * 1e-3 * g
        self.imu_sigma = (
            imu["noise_ug_rtHz"] * 1e-6 * g * math.sqrt(1.0 / (2.0 * c2.R8_IMU_SAMPLE_PERIOD_S))
        )
        self.pressure_sigma_N = float(rcc.CA["pressure_noise_N"])
        self.stroke_sigma_m = float(rcc.CA["stroke_noise_m"])

    def imu_sample(self, specific_force: np.ndarray) -> np.ndarray:
        return specific_force + self.imu_bias + self.rng.normal(0.0, self.imu_sigma, 3)

    def force(self, force_N: np.ndarray) -> np.ndarray:
        return force_N + self.rng.normal(0.0, self.pressure_sigma_N, 4)

    def stroke(self) -> np.ndarray:
        """One stroke-sensor error per leg; the corrected stroke carries the same error."""
        return self.rng.normal(0.0, self.stroke_sigma_m, 4)


@dataclass
class SeriesRecorder:
    """20 ms record grid (the ``c2t.run_case`` series keys) and the run totals."""

    series: dict[str, list] = field(
        default_factory=lambda: {
            key: []
            for key in (
                "t",
                "phi",
                "theta",
                "phi_m",
                "theta_m",
                "P",
                "Ftrue",
                "x",
                "u",
                "crawler_N",
                "clr",
                "Pmax",
                "Pmin",
                "alpha",
            )
        }
    )
    saturation_steps: np.ndarray = field(default_factory=lambda: np.zeros(4))
    stroke_limit_steps: np.ndarray = field(default_factory=lambda: np.zeros(4))
    _pressure_max: np.ndarray = field(default_factory=lambda: np.full(4, -1e12))
    _pressure_min: np.ndarray = field(default_factory=lambda: np.full(4, 1e12))
    _speed_sum: np.ndarray = field(default_factory=lambda: np.zeros(4))
    _chunks: int = 0

    def add_chunk(self, accumulated: np.ndarray, mean_speed: np.ndarray) -> None:
        self._pressure_max = np.maximum(self._pressure_max, accumulated[16:20])
        self._pressure_min = np.minimum(self._pressure_min, accumulated[20:24])
        self.saturation_steps += accumulated[3:7]
        self.stroke_limit_steps += accumulated[7:11]
        self._speed_sum += mean_speed
        self._chunks += 1

    def record(self, plant: rmf.FlexPlant, controller: C2Controller, crawler_N: float) -> None:
        phi, theta = plant.attitude()
        phi_m, theta_m = controller.filtered_attitude_rad
        values = {
            "t": plant.t,
            "phi": phi,
            "theta": theta,
            "phi_m": phi_m,
            "theta_m": theta_m,
            "P": plant.pressure().copy(),
            "Ftrue": plant.true_cyl_force().copy(),
            "x": plant.x.copy(),
            "u": self._speed_sum / self._chunks,
            "crawler_N": crawler_N,
            "clr": plant.crawler_clearance(),
            "Pmax": self._pressure_max.copy(),
            "Pmin": self._pressure_min.copy(),
            "alpha": plant.al.copy(),
        }
        for key, value in values.items():
            self.series[key].append(value)
        self._pressure_max = np.full(4, -1e12)
        self._pressure_min = np.full(4, 1e12)
        self._speed_sum = np.zeros(4)
        self._chunks = 0

    def arrays(self) -> dict[str, np.ndarray]:
        return {key: np.array(values) for key, values in self.series.items()}


# --- configuration -----------------------------------------------------------------------------


def r8_config(reanchor: bool) -> C2Config:
    """``with_10hz_d1`` with the driver departures; ``reanchor`` False = the c2py flat preset."""
    base = C2Config(
        contact=ContactJudge.COMBINED,
        output_ramp_time_s=None,
        reanchor=ReanchorSettings(enable=reanchor),
        target=TargetSettings(check_time_s=0.0, acceptance=TargetAcceptance.OFF),
    )
    config = base.with_10hz_d1()
    zero_calibration = replace(config.zero_calibration, mode=ZeroCalibrationMode.OFF)
    return replace(config, zero_calibration=zero_calibration)


def preset_constants(config: C2Config) -> dict[str, Any]:
    """The preset values the judgement rests on, read from the config (meta and T3)."""
    gains = config.gains
    return {
        "period_s": config.period_s,
        "imu_sample_period_s": config.r8.imu_sample_period_s,
        "output_delay_periods": config.r8.output_delay_periods,
        "attitude_kp_1_s": gains.attitude_kp_1_s,
        "attitude_ki_1_s2": gains.attitude_ki_1_s2,
        "twist_ktw_1_s": gains.twist_ktw_1_s,
        "guard_kg_1_s": gains.guard_kg_1_s,
        "attitude_time_constant_s": config.filters.attitude_time_constant_s,
        "attitude_stage_count": config.filters.attitude_stage_count,
        "twist_load_time_constant_s": config.filters.twist_load_time_constant_s,
        "increment_fraction_per_period": config.r8.increment_limit.fraction_per_period,
        "valve_lag_s": VALVE_LAG_S,
    }


def _assert_preset_matches_module_constants(config: C2Config) -> None:
    """The driver copies no controller value: it checks the config against the c2.py constants."""
    values = preset_constants(config)
    expected = {
        "period_s": c2.R8_PERIOD_S,
        "imu_sample_period_s": c2.R8_IMU_SAMPLE_PERIOD_S,
        "output_delay_periods": c2.R8_D1_SETTINGS.output_delay_periods,
        **c2.R8_D1_C2_GAINS,
        "attitude_time_constant_s": c2.R8_D1_ATTITUDE_TIME_CONSTANT_S,
        "twist_load_time_constant_s": c2.R8_D1_TWIST_LOAD_TIME_CONSTANT_S,
        "increment_fraction_per_period": c2.R8_D1_SETTINGS.increment_limit.fraction_per_period,
    }
    for key, value in expected.items():
        if values[key] != value:
            raise AssertionError(f"preset {key} = {values[key]!r}, c2.py constant {value!r}")
    if not math.isclose(RECORD_GRID_S, rcc.T_CTRL):
        raise AssertionError("the record grid must equal rcc.T_CTRL (metrics sample length)")


def check_plant_flex(plant: rmf.FlexPlant, mast_eq: dict | None) -> int:
    """The plant flex flag must follow the case: 0 without a mast model, 1 with one."""
    expected = 0 if mast_eq is None else 1
    if int(plant.flex) != expected:
        raise RuntimeError(f"plant flex {plant.flex} does not match the case (expected {expected})")
    return expected


# --- one run -----------------------------------------------------------------------------------


def _lagged_step(
    plant: rmf.FlexPlant, command: np.ndarray, valve: np.ndarray, steps: int, tau_v_s: float
) -> tuple[np.ndarray, np.ndarray]:
    """Exact mean of the first-order valve lag over the chunk (``c2py._lagged_step``)."""
    duration_s = steps * plant.dt
    decay = math.exp(-duration_s / tau_v_s)
    mean_speed = command + (valve - command) * (tau_v_s / duration_s) * (1.0 - decay)
    valve[:] = command + (valve - command) * decay
    return plant.step(mean_speed, steps), mean_speed


def _control_period(
    plant: rmf.FlexPlant,
    controller: C2Controller,
    command: np.ndarray,
    valve: np.ndarray,
    case: RunCase,
    recorder: SeriesRecorder,
    noise: SensorNoise | None,
) -> tuple[Measurements, float]:
    """One control period of 10 ms IMU samples; measurements and crawler force at its end."""
    lag_steps = round(LAG_CHUNK_S / plant.dt)
    imu_sample_s = controller.config.r8.imu_sample_period_s
    chunks_per_sample = round(imu_sample_s / LAG_CHUNK_S)
    samples_per_period = round(controller.period_s / imu_sample_s)
    samples_per_record = round(RECORD_GRID_S / imu_sample_s)
    imu_samples = []
    for sample in range(samples_per_period):
        force_sum = np.zeros(3)
        for _ in range(chunks_per_sample):
            accumulated, mean_speed = _lagged_step(plant, command, valve, lag_steps, case.tau_v_s)
            force_sum += accumulated[0:3]
            recorder.add_chunk(accumulated, mean_speed)
        specific_force = force_sum / (lag_steps * chunks_per_sample)
        imu_samples.append(specific_force if noise is None else noise.imu_sample(specific_force))
        if (sample + 1) % samples_per_record == 0:
            recorder.record(plant, controller, float(accumulated[15]))
    force_N = plant.pressure()
    stroke_error = np.zeros(4)
    if noise is not None:
        force_N = noise.force(force_N)
        stroke_error = noise.stroke()
    measurements = Measurements(
        t_s=plant.t,
        specific_force_m_s2=np.mean(imu_samples, axis=0),
        angular_rate_rad_s=np.asarray(plant.w, dtype=float),
        head_pressure_Pa=force_N / controller.geometry.head_area_m2,
        stroke_m=np.asarray(plant.sref, dtype=float) + stroke_error,
        stroke_corrected_m=np.asarray(plant.x, dtype=float) + stroke_error,
        imu_specific_force_samples_m_s2=np.array(imu_samples),
    )
    return measurements, float(accumulated[15])


def _build_plant(case: RunCase) -> rmf.FlexPlant:
    roll_deg, pitch_deg = case.slope_deg
    rmf.CONFIG.clear()
    rmf.CONFIG.update({"mast_eq": case.mast_eq, "record": False})
    plant = rmf.FlexPlant(
        case.level, roll_deg, pitch_deg, beta=case.beta_Pa, Fs=case.seal_friction_N, dt=case.dt_s
    )
    if case.leg_damping_scale != 1.0:
        plant.cn *= case.leg_damping_scale
        plant.ct *= case.leg_damping_scale
    check_plant_flex(plant, case.mast_eq)
    plant.step(np.zeros(4), int(round(rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    return plant


def _metrics_context(plant: rmf.FlexPlant, controller: C2Controller, level: str) -> rcc.Ctx:
    """``rcc.Ctx`` of the R7 metrics; its F_min (YAML-checked inside) must be the controller's."""
    W_nom = dm.body_from_params(dm.load_params(), level).mass * plant.g
    context = rcc.Ctx(plant.geo, W_nom, float(np.mean(rcc.Plant.k_nom_cache())))
    if not math.isclose(context.F_min, controller.geometry.F_min_N, rel_tol=1e-9):
        raise AssertionError(
            f"metrics F_min {context.F_min} N != controller F_min {controller.geometry.F_min_N} N"
        )
    return context


@dataclass
class _LoopState:
    """Phase times and per-period quantities of the running loop."""

    phase_before: C2Phase | None = None
    t_touch: float | None = None
    t_done: float | None = None
    t_ready: float | None = None
    t_fault: float | None = None
    t_liftoff: float | None = None
    min_force_after_liftoff_N: float = math.inf
    attitude_after_ready_deg: list = field(default_factory=list)
    guard_periods: int = 0

    def note(self, controller: C2Controller, plant: rmf.FlexPlant, crawler_N: float) -> None:
        phase = controller.phase
        t = plant.t
        if (
            self.phase_before is C2Phase.TOUCH
            and phase is not C2Phase.TOUCH
            and self.t_touch is None
        ):
            self.t_touch = t
        if phase is C2Phase.DONE and self.t_done is None:
            self.t_done = t
        if phase is C2Phase.READY and self.t_ready is None:
            self.t_ready = t
        if phase is C2Phase.FAULT and self.t_fault is None:
            self.t_fault = t
        if self.t_liftoff is None and crawler_N == 0.0 and phase is C2Phase.LEVEL:
            self.t_liftoff = t
        if self.t_liftoff is not None:
            self.min_force_after_liftoff_N = min(
                self.min_force_after_liftoff_N, float(plant.true_cyl_force().min())
            )
        if self.t_ready is not None:
            self.attitude_after_ready_deg.append(np.degrees(plant.attitude()))
        if np.any(controller.command_components_m_s.get("guard", np.zeros(4)) != 0.0):
            self.guard_periods += 1
        self.phase_before = phase

    def is_finished(self, t: float, hold_s: float) -> bool:
        ends = [start + hold_s for start in (self.t_ready, self.t_fault) if start is not None]
        return bool(ends) and t >= min(ends)


def _overshoot_deg(series: dict[str, np.ndarray], t_liftoff: float | None) -> list[float] | None:
    """True-attitude overshoot past zero after crawler lift-off (``c2t.run_case``)."""
    if t_liftoff is None:
        return None
    attitude = np.degrees(np.column_stack([series["phi"], series["theta"]]))
    after = attitude[series["t"] >= t_liftoff]
    start = after[0]
    overshoot = []
    for axis in range(2):
        if abs(start[axis]) > 0.2:
            overshoot.append(
                round(float(max(0.0, np.max(-np.sign(start[axis]) * after[:, axis]))), 4)
            )
        else:
            overshoot.append(0.0)
    return overshoot


def _event_summary(controller: C2Controller) -> dict[str, Any]:
    names = [event.name for event in controller.events]
    return {
        "event_names": names,
        "fault_names": sorted({name for name in names if name.startswith("FAULT")}),
        "warn_names": sorted({name for name in names if name.startswith("WARN")}),
        "event_counts": dict(Counter(name.split(":")[0] for name in names)),
    }


def run_one(case: RunCase) -> dict[str, Any]:
    """Run one case; the R7 metrics (``rcc.metrics`` + ``rmf.extra_metrics``) and the R8 record."""
    started = time.perf_counter()
    plant = _build_plant(case)
    controller = C2Controller.from_params(load_params(), r8_config(case.reanchor))
    _assert_preset_matches_module_constants(controller.config)
    context = _metrics_context(plant, controller, case.level)
    noise = None if case.seed is None else SensorNoise(case.seed, plant.g)
    recorder = SeriesRecorder()
    loop = _LoopState()
    command = np.zeros(4)
    valve = np.zeros(4)
    commands = []
    while plant.t < case.limit_s:
        measurements, crawler_N = _control_period(
            plant, controller, command, valve, case, recorder, noise
        )
        command = np.array(controller.update(measurements).leg_speed_m_s)
        commands.append(command)
        loop.note(controller, plant, crawler_N)
        if loop.is_finished(plant.t, case.hold_s):
            break
    series = recorder.arrays()
    events = _event_summary(controller)
    record = MetricsRecord(
        c=context,
        t_touch=loop.t_touch,
        t_done=loop.t_done,
        t_ready_first=loop.t_ready,
        fault=loop.t_fault is not None,
        probe_rounds=len(controller.probe_history),
        events=events["event_names"][:12],
    )
    result = rcc.metrics(
        series,
        record,
        plant,
        loop.t_liftoff,
        recorder.saturation_steps,
        recorder.stroke_limit_steps,
    )
    result.update(rmf.extra_metrics(series, result, plant))
    result["fails"] = [*result["fails"], *(f"fault:{name}" for name in events["fault_names"])]
    result.update(_run_record(case, controller, plant, loop, events, commands, series))
    result["wall_s"] = round(time.perf_counter() - started, 1)
    if case.keep_series:
        result["_series"] = {key: series[key].tolist() for key in series}
    return result


def _run_record(case, controller, plant, loop, events, commands, series) -> dict[str, Any]:
    """Case keys, R8 controller record and the period-sample extras of one run."""
    attitude = loop.attitude_after_ready_deg
    return {
        "slope": case.slope,
        "level": case.level,
        "mast": case.mast,
        "group": case.group,
        "gainset": GAINSET_NAME,
        "contact": str(ContactJudge.COMBINED),
        "variant": "",
        "zeta_mast": case.zeta_mast,
        "seed": case.seed,
        "beta_GPa": case.beta_Pa / 1e9,
        "Fs_kN": case.seal_friction_N / 1e3,
        "damping_scale": case.leg_damping_scale,
        "tau_v_s": case.tau_v_s,
        "reanchor": case.reanchor,
        "dt_s": case.dt_s,
        "plant_flex": int(plant.flex),
        "controller_revision": controller.meta()["revision"],
        "phase_final": str(controller.phase),
        "fault_names": events["fault_names"],
        "warn_names": events["warn_names"],
        "event_counts": events["event_counts"],
        "commands_sha256": hashlib.sha256(np.array(commands).tobytes()).hexdigest(),
        "guard_active_s": round(loop.guard_periods * controller.period_s, 2),
        "overshoot_true_deg": _overshoot_deg(series, loop.t_liftoff),
        "peak_leg_speed_mm_s": round(float(np.abs(series["u"]).max()) * 1e3, 2),
        "min_true_cyl_force_period_kN": None
        if loop.t_liftoff is None
        else round(loop.min_force_after_liftoff_N / 1e3, 2),
        "max_abs_attitude_after_ready_period_deg": round(float(np.abs(attitude).max()), 4)
        if attitude
        else None,
    }


def _run_safely(case: RunCase) -> dict[str, Any]:
    """Pool worker: one failed run is recorded with its traceback, the batch goes on."""
    try:
        return run_one(case)
    except Exception as error:  # noqa: BLE001  (recorded per run, never silent)
        LOG.exception("run failed: %s", case)
        return {
            "slope": case.slope,
            "level": case.level,
            "mast": case.mast,
            "group": case.group,
            "gainset": GAINSET_NAME,
            "seed": case.seed,
            "tau_v_s": case.tau_v_s,
            "beta_GPa": case.beta_Pa / 1e9,
            "error": repr(error),
            "tb": traceback.format_exc()[-800:],
        }


def compact(result: dict[str, Any]) -> dict[str, Any]:
    """rmf ``KEEP`` keys plus the R8 keys; the series stay out of the JSON."""
    if result.get("t_ready_s") is not None and result.get("t_touch_s") is not None:
        result["t_level_after_touch_s"] = round(result["t_ready_s"] - result["t_touch_s"], 2)
    keys = (*rmf.KEEP, *EXTRA_RUN_KEYS)
    return {key: result[key] for key in keys if key in result and result[key] is not None}


# --- case lists --------------------------------------------------------------------------------


def _case(
    eqs, level: str, slope: str, mast: str, group: str, zeta: float | None = None, **overrides: Any
) -> RunCase:
    mast_eq = rmf.eq_case(eqs, level, mast, None if zeta is None else (zeta, zeta))
    if mast == "rigid":
        zeta_mast = None
    else:
        zeta_mast = rmf.ZETA_NOM if zeta is None else zeta
    return RunCase(
        level=level,
        slope=slope,
        mast=mast,
        group=group,
        mast_eq=mast_eq,
        zeta_mast=zeta_mast,
        **overrides,
    )


def matrix_cases(eqs) -> list[RunCase]:
    """Top: rigid + three supports; middle / bottom: three supports; 23 slopes each."""
    cases = []
    for level in dm.LEVELS:
        masts = MASTS if level == "top" else rmf.FLEX
        for mast in masts:
            for slope, _, _ in rmf.SLOPES:
                keep = level == "top" and slope in SERIES_SLOPES
                cases.append(_case(eqs, level, slope, mast, "matrix", keep_series=keep))
    return cases


def sensitivity_cases(eqs) -> list[RunCase]:
    """Top, upper / lower supports: mast zeta, leg damping 1/3 and seal friction."""
    cases = []
    for mast in ("upper", "lower"):
        for zeta in MAST_ZETAS:
            cases += [
                _case(eqs, "top", slope, mast, f"zeta{zeta}", zeta=zeta) for slope in KEY_SLOPES
            ]
        cases += [
            _case(eqs, "top", slope, mast, "leg_damp_1/3", leg_damping_scale=LEG_DAMPING_SCALE)
            for slope in LEG_DAMPING_SLOPES
        ]
        for friction_N in SEAL_FRICTION_N:
            group = f"seal{friction_N / 1e3:g}"
            cases += [
                _case(eqs, "top", slope, mast, group, seal_friction_N=friction_N)
                for slope in SEAL_FRICTION_SLOPES
            ]
    return cases


def reanchor_cases(eqs) -> list[RunCase]:
    return [
        _case(eqs, "top", slope, mast, "reanchor_on", reanchor=True)
        for slope in REANCHOR_SLOPES
        for mast in MASTS
    ]


def convergence_cases(eqs) -> list[RunCase]:
    """The smoke cases at the plant dt and at half of it (1 ms chunks either way)."""
    cases = []
    for dt_s in (rcc.DT, CONVERGENCE_DT_S):
        for slope, mast in SMOKE_CASES:
            cases.append(
                _case(eqs, "top", slope, mast, "convergence", hold_s=SMOKE_HOLD_S, dt_s=dt_s)
            )
    return cases


def robust_cases(eqs) -> list[RunCase]:
    """ROBUST_TOP / ROBUST_LOW x four masts: beta, tau_v (ideal sensors) and noise seeds."""
    cases = []
    for level, slopes in (
        ("top", rmf.ROBUST_TOP),
        ("middle", rmf.ROBUST_LOW),
        ("bottom", rmf.ROBUST_LOW),
    ):
        for mast in MASTS:
            for slope in slopes:
                cases += [
                    _case(eqs, level, slope, mast, "robust_beta", beta_Pa=beta)
                    for beta in ROBUST_BETAS_PA
                ]
                cases += [
                    _case(eqs, level, slope, mast, "robust_tau_v", tau_v_s=tau)
                    for tau in ROBUST_TAU_V_S
                ]
                cases += [
                    _case(eqs, level, slope, mast, "robust_seed", seed=seed)
                    for seed in ROBUST_SEEDS
                ]
    return cases


# --- batch ---------------------------------------------------------------------------------------


def set_ecore_affinity() -> list[int] | str:
    """E-cores 16..27 (mask 0x0FFF0000), below-normal priority, inherited by the pool."""
    return rmf.c2t.set_affinity()


def run_batch(cases: list[RunCase], workers: int, label: str) -> list[dict[str, Any]]:
    """Run the cases in a pool; progress every 25 runs (the main / robust batches are long)."""
    started = time.perf_counter()
    results = []
    with Pool(workers) as pool:
        for index, result in enumerate(pool.imap(_run_safely, cases, chunksize=1), start=1):
            results.append(result)
            if index % 25 == 0 or index == len(cases):
                LOG.info(
                    "%s: %d / %d runs, %.0f s",
                    label,
                    index,
                    len(cases),
                    time.perf_counter() - started,
                )
    return results


def load_equivalent_masts():
    """Calibration (new T_rel) and the equivalent-mast parameters of every level and support."""
    params = dm.load_params()
    geometry = dm.geometry_from_params(params)
    reference = json.loads(mbc.REF_JSON.read_text(encoding="utf-8"))
    return rmf.calibration(params, geometry, reference, mbc.load_mast(), rmf.load_boom())


def kernel_linearisation(eqs) -> dict[str, Any]:
    """Linearised kernel vs the 8-DoF linear equivalent (the rmf ``main`` block, unchanged)."""
    linearisation = {}
    for level in ("top", "bottom"):
        basis = rmf.cl_basis(level)
        f6, z6 = rmf.complex_modes(basis["M6"], basis["K6"], basis["C6"], 6)
        fj6, zj6 = rmf.plant_jacobian(level, None)
        entry = {
            "rigid": {
                "linear_f_Hz": f6.tolist(),
                "kernel_f_Hz": fj6[:6].tolist(),
                "linear_zeta": z6.tolist(),
                "kernel_zeta": zj6[:6].tolist(),
            }
        }
        for support in rmf.SUPPORTS:
            eq = rmf.public(eqs[(level, support)])
            M8, K8, C8 = rmf.eq_linear(basis, eq)
            f8, z8 = rmf.complex_modes(M8, K8, C8, 8)
            fj, zj = rmf.plant_jacobian(level, eq)
            entry[support] = {
                "linear_f_Hz": f8.tolist(),
                "kernel_f_Hz": fj[:8].tolist(),
                "linear_zeta": z8.tolist(),
                "kernel_zeta": zj[:8].tolist(),
                "max_rel_f_diff": float(np.max(np.abs(fj[:8] / f8 - 1))),
            }
        entry["rigid"]["max_rel_f_diff"] = float(np.max(np.abs(fj6[:6] / f6 - 1)))
        linearisation[level] = entry
    return linearisation


def c2py_reference_sha() -> str:
    """``imu_100hz.commands_sha256`` of ``c2py_r8d1_closed_loop.py`` in its own process (it
    patches the harness, so it is never imported here)."""
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]); "
        "import c2py_r8d1_closed_loop as loop; "
        "print(json.dumps(loop.run_imu_100hz_flat()['commands_sha256']))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, str(HERE)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def t1_case() -> RunCase:
    """T1: top, level floor, rigid mast, ideal sensors, tau_v 0.1 s, 120 s limit, READY + 5 s."""
    return RunCase(
        level="top",
        slope="flat",
        mast="rigid",
        group="t1",
        mast_eq=None,
        limit_s=T1_LIMIT_S,
        hold_s=T1_HOLD_S,
    )


def t1_bit_regression() -> dict[str, Any]:
    driver_sha = run_one(t1_case())["commands_sha256"]
    reference_sha = c2py_reference_sha()
    return {
        "driver_commands_sha256": driver_sha,
        "c2py_commands_sha256": reference_sha,
        "is_bit_identical": driver_sha == reference_sha,
    }


def convergence_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Half-dt vs plant dt on the smoke cases: min true force and READY time."""
    by_key = {(r["slope"], r["mast"], r.get("dt_s")): r for r in results}
    rows = {}
    for slope, mast in SMOKE_CASES:
        coarse = by_key[(slope, mast, rcc.DT)]
        fine = by_key[(slope, mast, CONVERGENCE_DT_S)]
        force_diff = _abs_diff(
            coarse.get("min_true_cyl_force_kN"), fine.get("min_true_cyl_force_kN")
        )
        ready_diff = _abs_diff(coarse.get("t_ready_s"), fine.get("t_ready_s"))
        rows[f"{slope}:{mast}"] = {
            "min_force_kN (dt, dt/2)": [
                coarse.get("min_true_cyl_force_kN"),
                fine.get("min_true_cyl_force_kN"),
            ],
            "t_ready_s (dt, dt/2)": [coarse.get("t_ready_s"), fine.get("t_ready_s")],
            "min_force_abs_diff_kN": force_diff,
            "t_ready_abs_diff_s": ready_diff,
            "passes": force_diff is not None
            and ready_diff is not None
            and force_diff <= CONVERGENCE_MIN_FORCE_TOL_KN
            and ready_diff <= CONVERGENCE_READY_TOL_S,
        }
    return {
        "dt_s": [rcc.DT, CONVERGENCE_DT_S],
        "chunk_s": LAG_CHUNK_S,
        "tolerances": {
            "min_force_kN": CONVERGENCE_MIN_FORCE_TOL_KN,
            "t_ready_s": CONVERGENCE_READY_TOL_S,
        },
        "cases": rows,
        "passes": all(row["passes"] for row in rows.values()),
    }


def _abs_diff(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else round(abs(a - b), 4)


def smoke_table(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Smoke runs (READY + 5 s, plant dt) next to the spec 5 expectations."""
    table = {}
    for r in results:
        if r.get("dt_s") != rcc.DT:
            continue
        expected = SMOKE_EXPECTED[(r["slope"], r["mast"])]
        table[f"{r['slope']}:{r['mast']}"] = {
            "expected (touch, liftoff, ready, min_kN, alpha_deg, ss_deg)": list(expected),
            "got": [
                r.get("t_touch_s"),
                r.get("t_crawler_liftoff_s"),
                r.get("t_ready_s"),
                r.get("min_true_cyl_force_period_kN"),
                r.get("mast_alpha_maxabs_deg (LAT x, FA y)"),
                r.get("max_abs_attitude_after_ready_period_deg"),
            ],
            "min_true_cyl_force_20ms_kN": r.get("min_true_cyl_force_kN"),
            "grid_min_le_period_min": _is_le(
                r.get("min_true_cyl_force_kN"), r.get("min_true_cyl_force_period_kN")
            ),
        }
    return table


def _is_le(a: float | None, b: float | None) -> bool | None:
    return None if a is None or b is None else a <= b


def _numeric_diff(new: Any, old: Any, path: str, out: dict[str, Any]) -> int:
    """Differences of the numeric leaves present in both trees; returns the compared count."""
    if isinstance(new, dict) and isinstance(old, dict):
        return sum(_numeric_diff(new[k], old[k], f"{path}/{k}", out) for k in new if k in old)
    if isinstance(new, list) and isinstance(old, list) and len(new) == len(old):
        pairs = enumerate(zip(new, old, strict=True))
        return sum(_numeric_diff(a, b, f"{path}[{i}]", out) for i, (a, b) in pairs)
    is_number = isinstance(new, int | float) and isinstance(old, int | float)
    if not is_number or isinstance(new, bool) or isinstance(old, bool):
        return 0
    if new != old:
        out[path] = {"r7": old, "r8_run": new, "diff": new - old}
    return 1


def calibration_vs_r7(calibration: dict[str, Any], r7: dict[str, Any]) -> dict[str, Any]:
    diffs: dict[str, Any] = {}
    compared = _numeric_diff(calibration, r7.get("calibration", {}), "", diffs)
    return {"compared_leaves": compared, "changed_leaves": len(diffs), "changes": diffs}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() or f"unknown ({completed.stderr.strip()})"


def build_meta(cores) -> dict[str, Any]:
    config = r8_config(False)
    controller = C2Controller.from_params(load_params(), config)
    return {
        "script": "04_scripts/03_control/r8d1/mast_flex_r8c2.py",
        "doc": "00_docs/01_dynamics/dynamics_model.md 3.9.7 / 5.13.2 (R8 re-judgement)",
        "argv": sys.argv[1:],
        "affinity": cores,
        "git_head": _git_head(),
        "c2_py_sha256": _sha256(PROJECT_ROOT / "03_src/outrigger_sim/control/c2.py"),
        "controller_revision": controller.meta()["revision"],
        "preset": "C2Config.with_10hz_d1() (defaults), contact combined, zero calibration OFF, "
        "target check OFF, REANCHOR OFF (group reanchor_on: on)",
        "preset_constants": preset_constants(config),
        "departures": list(DEPARTURES),
        "gainset": GAINSET_NAME,
        "T_ctrl_s": config.period_s,
        "imu_sample_s": config.r8.imu_sample_period_s,
        "tau_v_s": VALVE_LAG_S,
        "record_grid_s": RECORD_GRID_S,
        "lag_chunk_s": LAG_CHUNK_S,
        "dt_s": rcc.DT,
        "F_min_kN": rmf.F_MIN_KN,
        "frame": "body x fwd, y left, z up; gravity -9.80665 z_hat; pitch > 0 nose down; "
        "roll > 0 left up",
        "assumptions": {
            "tau_v_s": "0.1 s first-order valve lag (spec 138 C-1), sensitivity 0.05 / 0.15",
            "robust_noise": "R7 sizes rcc.CA: IMU bias [0.5, -0.5] mg, 100 ug/rtHz per 10 ms "
            "sample, pressure 300 N, stroke 0.1 mm (both strokes), default_rng(seed)",
            "seal_friction": "sensitivity 4 / 8 kN on every leg (rmf FlexPlant scalar Fs)",
            "matrix_reanchor": "OFF (group reanchor_on with the preset H4)",
            "equivalent_mast": "rmf equivalent mast, unchanged (see the R7 JSON meta)",
        },
        "r7_reference": {
            "path": str(R7_JSON.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": _sha256(R7_JSON),
        },
    }


def _series_for_figures(results: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict]:
    return {
        (r["level"], r["slope"], r["mast"]): r.pop("_series") for r in results if "_series" in r
    }


def _matrix_figures(series, runs) -> list[Path]:
    """rmf ``figures`` with the R8 label; its R7 cause panel is not part of this study."""
    paths = rmf.figures(series, runs, FIG_STEM, ctrl_label=CTRL_LABEL, xlim=TIMESERIES_XLIM_S)
    kept = []
    for path in paths:
        if path.name.endswith("_cause.png"):
            path.unlink()
        else:
            kept.append(path)
    return kept


def _relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def main_stage(workers: int, cores) -> None:
    started = time.perf_counter()
    calibration, eqs = load_equivalent_masts()
    r7 = json.loads(R7_JSON.read_text(encoding="utf-8"))
    calibration_rounded = mbc.r(calibration)
    verification = {
        "t1_bit_regression": t1_bit_regression(),
        "frozen_kernel_identity": rmf.verify_frozen_identity(),
        "kernel_linearisation_vs_linear_equivalent": kernel_linearisation(eqs),
    }
    LOG.info("calibration + verification %.0f s", time.perf_counter() - started)
    cases = (
        matrix_cases(eqs) + sensitivity_cases(eqs) + reanchor_cases(eqs) + convergence_cases(eqs)
    )
    raw = run_batch(cases, workers, "main")
    series = _series_for_figures(raw)
    convergence = [r for r in raw if r.get("group") == "convergence"]
    verification["convergence_half_dt"] = convergence_summary(convergence)
    verification["smoke"] = smoke_table(convergence)
    runs = [compact(r) for r in raw]
    verification["runs"] = {
        "count": len(runs),
        "errors": sum("error" in r for r in runs),
        "plant_flex_mismatch": _plant_flex_mismatches(runs),
    }
    summary, slope_limits = rmf.summarise(runs)
    figures = _matrix_figures(series, runs)
    meta = build_meta(cores)
    meta["figures"] = [_relative(path) for path in figures]
    meta["wall_s"] = round(time.perf_counter() - started, 1)
    result = {
        "meta": meta,
        "calibration": calibration_rounded,
        "calibration_vs_r7": calibration_vs_r7(calibration_rounded, r7),
        "verification": mbc.r(verification),
        "summary": summary,
        "slope_limits": slope_limits,
        "reanchor_on": [r for r in runs if r["group"] == "reanchor_on"],
        "runs": runs,
    }
    OUT_JSON.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    LOG.info("wrote %s (%.0f s)", OUT_JSON, meta["wall_s"])


def _plant_flex_mismatches(runs: list[dict[str, Any]]) -> int:
    return sum(1 for r in runs if "plant_flex" in r and r["plant_flex"] != (r["mast"] != "rigid"))


def robust_envelope(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Worst minimum force, fail count and runs per ``level:mast:slope`` and robust axis."""
    envelope: dict[str, Any] = {}
    for r in runs:
        axis = ROBUST_AXIS_BY_GROUP.get(r.get("group"))
        if axis is None:
            continue
        entry = envelope.setdefault(
            f"{r['level']}:{r['mast']}:{r['slope']}",
            {
                **{
                    name: {"min_kN": None, "fails": 0, "runs": 0}
                    for name in ROBUST_AXIS_BY_GROUP.values()
                },
                "t_level_max_s": 0.0,
                "ss_max_deg": 0.0,
                "max_bar": 0.0,
                "fail_kinds": [],
            },
        )
        cell = entry[axis]
        force = r.get("min_true_cyl_force_kN")
        if force is not None:
            cell["min_kN"] = force if cell["min_kN"] is None else min(cell["min_kN"], force)
        cell["runs"] += 1
        if r.get("fails") or "error" in r:
            cell["fails"] += 1
            kinds = set(r.get("fails", [])) | ({"error"} if "error" in r else set())
            entry["fail_kinds"] = sorted(set(entry["fail_kinds"]) | kinds)
        entry["t_level_max_s"] = max(
            entry["t_level_max_s"], r.get("t_level_after_touch_s", 0.0) or 0.0
        )
        entry["ss_max_deg"] = max(entry["ss_max_deg"], r.get("ss_true_att_deg_maxabs", 0.0) or 0.0)
        entry["max_bar"] = max(entry["max_bar"], r.get("max_pressure_bar", 0.0) or 0.0)
    return envelope


def robust_figure(envelope: dict[str, Any]) -> Path:
    """Top: worst minimum true force per robust axis (rows) and slope direction (columns)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colours = {"rigid": "#7f7f7f", "stiff": "#2ca02c", "upper": "#1f77b4", "lower": "#d62728"}
    directions = [
        ("pitch+ (front low)", "pitch+"),
        ("pitch- (front high)", "pitch-"),
        ("roll+ (left high)", "roll+"),
        ("diag (roll+, pitch+)", "diag"),
    ]
    axis_titles = {
        "beta": "beta 0.69 / 1.6 GPa",
        "tau_v": "tau_v 0.05 / 0.15 s",
        "seed": "sensor noise seeds 12345..12347",
    }
    fig, ax = plt.subplots(3, 4, figsize=(15, 10), sharey=True)
    for column, (direction_name, prefix) in enumerate(directions):
        for row, axis in enumerate(axis_titles):
            panel = ax[row, column]
            for mast in MASTS:
                _plot_robust_line(panel, envelope, mast, prefix, axis, colours[mast])
            panel.axhline(rmf.F_MIN_KN, color="k", ls=":", lw=0.8)
            panel.axhline(rmf.F_MIN_KN + rmf.D8_FORCE_MARGIN_KN, color="k", ls="--", lw=0.6)
            panel.set_title(f"top, {direction_name}, {axis_titles[axis]}", fontsize=8)
            panel.grid(alpha=0.3)
            if column == 0:
                panel.set_ylabel("worst min true force [kN]")
            if row == 2:
                panel.set_xlabel("ground slope magnitude [deg]")
    ax[0, 0].legend(fontsize=8)
    fig.suptitle(
        f"{CTRL_LABEL}: worst minimum true cylinder force after crawler lift-off; x = a run "
        "failed; dotted F_min, dashed F_min + 5 kN",
        fontsize=10,
    )
    fig.tight_layout()
    path = rmf.OUT_DIR / f"{FIG_STEM}_robust.png"
    fig.savefig(path, dpi=90)
    plt.close(fig)
    return path


def _plot_robust_line(panel, envelope, mast: str, prefix: str, axis: str, colour: str) -> None:
    points = []
    for slope in rmf.ROBUST_TOP:
        key = f"top:{mast}:{slope}"
        if slope.startswith(prefix) and key in envelope:
            cell = envelope[key][axis]
            force = -2.0 if cell["min_kN"] is None else max(-2.0, cell["min_kN"])
            points.append((math.hypot(*rmf.SLOPE_ANG[slope]), force, cell["fails"]))
    if not points:
        return
    points.sort()
    panel.plot(
        [p[0] for p in points], [p[1] for p in points], "o-", color=colour, ms=3, lw=1, label=mast
    )
    for magnitude, force, fails in points:
        if fails:
            panel.plot(magnitude, force, "x", color=colour, ms=9, mew=2)


def robust_stage(workers: int, cores) -> None:
    started = time.perf_counter()
    _, eqs = load_equivalent_masts()
    cases = robust_cases(eqs)
    runs = [compact(r) for r in run_batch(cases, workers, "robust")]
    envelope = robust_envelope(runs)
    result = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    figure = _relative(robust_figure(envelope))
    if figure not in result["meta"]["figures"]:
        result["meta"]["figures"].append(figure)
    result["robustness"] = {
        "meta": {
            "argv": sys.argv[1:],
            "affinity": cores,
            "seeds": list(ROBUST_SEEDS),
            "betas_GPa": [b / 1e9 for b in ROBUST_BETAS_PA],
            "tau_v_s": list(ROBUST_TAU_V_S),
            "top_slopes": list(rmf.ROBUST_TOP),
            "middle_bottom_slopes": list(rmf.ROBUST_LOW),
            "wall_s": round(time.perf_counter() - started, 1),
            "note": "beta / tau_v rows: ideal sensors; seed rows: R7 noise sizes, beta 1.0 GPa,"
            " tau_v 0.1 s",
            "errors": sum("error" in r for r in runs),
            "plant_flex_mismatch": _plant_flex_mismatches(runs),
        },
        "envelope": envelope,
        "runs": runs,
    }
    OUT_JSON.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    LOG.info("robust: %d runs, %.0f s", len(runs), time.perf_counter() - started)


def smoke_stage(workers: int, out_path: Path | None) -> None:
    """The four smoke cases only (READY + 5 s), printed next to the spec 5 table."""
    _, eqs = load_equivalent_masts()
    cases = [c for c in convergence_cases(eqs) if c.dt_s == rcc.DT]
    table = smoke_table(run_batch(cases, min(workers, len(cases)), "smoke"))
    text = json.dumps(table, indent=1, default=float)
    print(text)
    if out_path is not None:
        out_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=("smoke", "main", "robust"), default="main")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--out", type=Path, help="smoke: also write the table here")
    parser.add_argument("--log", type=Path, help="progress log file (in addition to stderr)")
    args = parser.parse_args()
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.log is not None:
        handlers.append(logging.FileHandler(args.log, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=handlers)
    cores = set_ecore_affinity()
    LOG.info("stage %s, affinity %s", args.stage, cores)
    if args.stage == "smoke":
        smoke_stage(args.workers, args.out)
    elif args.stage == "main":
        main_stage(args.workers, cores)
    else:
        robust_stage(args.workers, cores)


if __name__ == "__main__":
    main()
