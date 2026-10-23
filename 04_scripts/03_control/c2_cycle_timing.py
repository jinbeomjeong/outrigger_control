"""Computation time of one C2 control period (R7 now, R8 estimate) on a single CPU core.

``00_docs/04_control/s6_control_spec.md`` revision 26 (99.5, U-R8-2): the 10 Hz design R8 needs
the sample -> compute -> valve output chain inside one 100 ms period (d = 0). This script
measures how much of that period the controller computation takes.

Two steps, so that the timing needs neither numba nor Chrono:

``record``
    Runs C2 (R7, ``03_src/outrigger_sim/control/c2.py``, imported read-only) in closed loop on
    the reduced 6-DoF plant (``04_scripts/01_dynamics/run_control_comparison.py``, numba) for
    representative cases and stores every period's ``Measurements`` and command in an npz.
``measure``
    Replays the stored inputs through fresh controllers on one pinned logical CPU and times
    ``C2Controller.update`` per period. The replay is checked to reproduce the recorded commands
    bit for bit, so it is the closed-loop state flow. R8 is not in the code yet; its extra work
    per 10 Hz period (multi-rate attitude filter: 9 more IMU samples, R-1 stop predictor, R-2
    touch window, sample confirmation counters, end-approach slow-down, per-period increment
    limit; logic of the control harness ``run_c2_r8_10hz_check.py``) is emulated with the same numpy
    building blocks and timed together with the R7 update.

Run (project root, Chrono-dev; E-core 27 while the P-cores are busy):
    python.exe -I 04_scripts/03_control/c2_cycle_timing.py record
    python.exe -I 04_scripts/03_control/c2_cycle_timing.py measure --cpu 27 --label ecore27

On another computer only ``measure`` is needed (numpy, PyYAML, ``03_src`` and the npz).
Results merge into ``06_analysis/02_control/c2_cycle_timing.json`` under ``--label``.
"""

from __future__ import annotations

import argparse
import cProfile
import ctypes
import gc
import json
import math
import os
import platform
import pstats
import subprocess
import sys
import time
import tracemalloc
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# One BLAS thread: the controller's matrices are 4x4, and extra threads on one pinned core only
# compete with the measured thread.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
REDUCED_MODEL_DIR = PROJECT_ROOT / "04_scripts" / "01_dynamics"
sys.path.insert(0, str(SOURCE_DIR))

import numpy as np  # noqa: E402

from outrigger_sim.control.c2 import (  # noqa: E402
    C2Config,
    C2Controller,
    C2Phase,
    TargetSettings,
)
from outrigger_sim.control.target import CrawlerSettleMap, SlopeLimitMode  # noqa: E402
from outrigger_sim.params import LEG_ORDER, load_params  # noqa: E402
from outrigger_sim.sensors.attitude import AttitudeEstimator, CascadedLowPass  # noqa: E402
from outrigger_sim.signals import LEG_COUNT, Measurements  # noqa: E402

ANALYSIS_DIR = PROJECT_ROOT / "06_analysis" / "02_control"
INPUTS_PATH = ANALYSIS_DIR / "c2_cycle_timing_inputs.npz"
RESULTS_PATH = ANALYSIS_DIR / "c2_cycle_timing.json"

R7_PERIOD_S = 0.02
R8_PERIOD_S = 0.1
RUN_LIMIT_S = 200.0
HOLD_AFTER_READY_S = 5.0
ROD_PRESSURE_PA = 2e5  # constant rod-side reading, so the R6-P net-force path runs
OIL_TEMPERATURE_C = 40.0  # so the E-5 oil temperature watch runs
SINK_LEG = LEG_ORDER.index("RR")
SINK_DEPTH_M = 0.0115  # c2_design 8.2 settling case: RR floor 11.5 mm in 2 s after READY
SINK_RAMP_S = 2.0
SINK_DELAY_AFTER_READY_S = 2.0

# R8 (spec 99.3 / 101): IMU 100 Hz multi-rate filter, 2 stages tau 0.8 s; R-1 3-sample rate,
# (1 + d) periods ahead; R-2 window 40 mm at 0.5 v_max; increments 0.25 / 0.1 v_max per period;
# end approach within 15 mm at 0.25 v_max; confirmation ABOVE 3, BELOW 2, P5 2, guard 1.
R8_IMU_SAMPLES_PER_PERIOD = 10
R8_IMU_PERIOD_S = R8_PERIOD_S / R8_IMU_SAMPLES_PER_PERIOD
R8_ATTITUDE_TIME_CONSTANT_S = 0.8
R8_ATTITUDE_STAGE_COUNT = 2
R8_COMPLETION_TIME_CONSTANT_S = 1.0
R8_STOP_PREDICTOR_SAMPLES = 4  # 3 rates
R8_OUTPUT_DELAY_PERIODS = 0
R8_TOUCH_WINDOW_M = 0.04
R8_TOUCH_WINDOW_SPEED_FRACTION = 0.5
R8_GUARD_INCREMENT_FRACTION = 0.25
R8_OTHER_INCREMENT_FRACTION = 0.1
R8_END_MARGIN_M = 0.010  # end margin below the stroke sensor end (CLAUDE.md: 0.6848 m)
R8_END_APPROACH_M = 0.015
R8_END_APPROACH_SPEED_FRACTION = 0.25
R8_CONFIRM_SAMPLES = (3, 2, 2, 1)  # ABOVE, BELOW, P5 re-level, guard

TIMED_REPETITIONS = 5
QUANTILES = {"median": 0.5, "p95": 0.95, "p99": 0.99}
TAIL_LIMITS_MS = (2, 5, 10, 50)
PROFILE_TOP_COUNT = 15
IMPORT_PROBE_COUNT = 3
ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
HIGH_PRIORITY_CLASS = 0x00000080
PRIORITY_CLASSES = {"normal": None, "above_normal": ABOVE_NORMAL_PRIORITY_CLASS,
                    "high": HIGH_PRIORITY_CLASS}
PROCESS_POWER_THROTTLING = 4  # PROCESS_INFORMATION_CLASS ProcessPowerThrottling


# --- cases ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One closed-loop case of the reduced plant (top auger, ideal sensors)."""

    name: str
    pitch_deg: float = 0.0
    is_verification: bool = False
    """Verification mode with the top crawler settle map (accepts nose-down 3.5 deg)."""
    pad_friction_mode: int = 0
    """Reduced plant pad friction (1 = Chrono-type; the REANCHOR closed-loop tests use 1)."""
    sinks_after_ready: bool = False
    """RR floor sinks 11.5 mm after READY: READY -> LEVEL (guard) -> PROBE -> READY again."""


SCENARIOS = (
    Scenario("nose_down_3p5_reanchor", pitch_deg=3.5, is_verification=True, pad_friction_mode=1),
    Scenario("flat"),
    Scenario("flat_sink_relevel", sinks_after_ready=True),
)


def scenario_config(scenario: Scenario, command_ramp_s: float) -> C2Config:
    """Decided R7 defaults (as the closed-loop tests build them) for ``scenario``."""
    ramp_s = command_ramp_s if command_ramp_s > 0.0 else None
    if not scenario.is_verification:
        return C2Config(output_ramp_time_s=ramp_s)
    target = TargetSettings(
        slope_limit_mode=SlopeLimitMode.VERIFICATION,
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    return C2Config(target=target, output_ramp_time_s=ramp_s)


def new_controller(scenario: Scenario) -> C2Controller:
    params = load_params()
    config = scenario_config(scenario, params.actuator.command_ramp_s)
    return C2Controller.from_params(params, config)


# --- record (closed loop, numba plant) -------------------------------------------------------


@dataclass
class Recording:
    """Per-period controller inputs and outputs of one closed-loop run."""

    t_s: list[float] = field(default_factory=list)
    specific_force_m_s2: list[np.ndarray] = field(default_factory=list)
    angular_rate_rad_s: list[np.ndarray] = field(default_factory=list)
    head_pressure_Pa: list[np.ndarray] = field(default_factory=list)
    rod_pressure_Pa: list[np.ndarray] = field(default_factory=list)
    stroke_m: list[np.ndarray] = field(default_factory=list)
    stroke_corrected_m: list[np.ndarray] = field(default_factory=list)
    command_m_s: list[np.ndarray] = field(default_factory=list)
    phase_before: list[str] = field(default_factory=list)

    def append(self, measurements: Measurements, command: np.ndarray, phase: C2Phase) -> None:
        self.t_s.append(measurements.t_s)
        self.specific_force_m_s2.append(np.array(measurements.specific_force_m_s2))
        self.angular_rate_rad_s.append(np.array(measurements.angular_rate_rad_s))
        self.head_pressure_Pa.append(np.array(measurements.head_pressure_Pa))
        self.rod_pressure_Pa.append(np.array(measurements.rod_pressure_Pa))
        self.stroke_m.append(np.array(measurements.stroke_m))
        self.stroke_corrected_m.append(np.array(measurements.stroke_corrected_m))
        self.command_m_s.append(command)
        self.phase_before.append(str(phase))

    def arrays(self, prefix: str) -> dict[str, np.ndarray]:
        return {f"{prefix}/{name}": np.array(values) for name, values in vars(self).items()}


def plant_measurements(plant, accumulated, controller: C2Controller, n_sub: int) -> Measurements:
    """Ideal sensors of the last period; head pressure includes the rod-side force."""
    geometry = controller.geometry
    rod_Pa = np.full(LEG_COUNT, ROD_PRESSURE_PA)
    head_Pa = (plant.pressure() + rod_Pa * geometry.annulus_area_m2) / geometry.head_area_m2
    return Measurements(
        t_s=plant.t,
        specific_force_m_s2=accumulated[0:3] / n_sub,
        angular_rate_rad_s=plant.w.copy(),
        head_pressure_Pa=head_Pa,
        stroke_m=plant.sref.copy(),
        stroke_corrected_m=plant.x.copy(),
        rod_pressure_Pa=rod_Pa,
        oil_temperature_C=OIL_TEMPERATURE_C,
    )


class _ReadyHoldClock:
    """Tells when READY has held long enough; with a sink, only after the re-level."""

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.ready_held_s = 0.0
        self.first_ready_t_s: float | None = None
        self.has_relevelled = False

    def floor_sink_m(self, t_s: float) -> float:
        if not self.scenario.sinks_after_ready or self.first_ready_t_s is None:
            return 0.0
        elapsed_s = t_s - self.first_ready_t_s - SINK_DELAY_AFTER_READY_S
        return SINK_DEPTH_M * min(1.0, max(0.0, elapsed_s / SINK_RAMP_S))

    def is_done(self, phase: C2Phase, t_s: float, period_s: float) -> bool:
        if phase is C2Phase.READY and self.first_ready_t_s is None:
            self.first_ready_t_s = t_s
        self.has_relevelled |= self.first_ready_t_s is not None and phase is C2Phase.LEVEL
        self.ready_held_s = self.ready_held_s + period_s if phase is C2Phase.READY else 0.0
        needs_relevel = self.scenario.sinks_after_ready and not self.has_relevelled
        return self.ready_held_s >= HOLD_AFTER_READY_S and not needs_relevel


def record_scenario(scenario: Scenario, reduced_model) -> Recording:
    """Closed loop until READY has held 5 s (after the re-level for the sink case)."""
    reduced_model.PAD_FRICTION_MODE = scenario.pad_friction_mode  # read at plant construction
    plant = reduced_model.Plant("top", 0.0, scenario.pitch_deg)
    plant.step(np.zeros(4), int(round(reduced_model.SETTLE_ON_CRAWLER_S / reduced_model.DT)))
    plant.t = 0.0
    controller = new_controller(scenario)
    clock = _ReadyHoldClock(scenario)
    recording = Recording()
    command = np.zeros(LEG_COUNT)
    while plant.t < RUN_LIMIT_S:
        plant.goff[SINK_LEG] = clock.floor_sink_m(plant.t)
        accumulated = plant.step(command, reduced_model.N_SUB)
        measurements = plant_measurements(plant, accumulated, controller, reduced_model.N_SUB)
        phase_before = controller.phase
        command = np.array(controller.update(measurements).leg_speed_m_s)
        recording.append(measurements, command, phase_before)
        if clock.is_done(controller.phase, plant.t, reduced_model.T_CTRL):
            break
    if controller.phase is not C2Phase.READY:
        raise RuntimeError(f"{scenario.name}: ended in {controller.phase} at {plant.t:.1f} s")
    return recording


def record(_arguments: argparse.Namespace) -> None:
    pin_to_cpus(efficiency_class=0)  # every E-core: the P-cores may carry a Chrono batch
    sys.path.insert(0, str(REDUCED_MODEL_DIR))
    import run_control_comparison as reduced_model  # noqa: PLC0415 - numba, record step only

    if not math.isclose(reduced_model.T_CTRL, R7_PERIOD_S):
        raise RuntimeError(f"reduced model T_CTRL {reduced_model.T_CTRL} != {R7_PERIOD_S}")
    arrays: dict[str, np.ndarray] = {}
    for scenario in SCENARIOS:
        recording = record_scenario(scenario, reduced_model)
        phases = sorted(set(recording.phase_before))
        print(f"{scenario.name}: {len(recording.t_s)} periods, phases {phases}", flush=True)
        arrays.update(recording.arrays(scenario.name))
    INPUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(INPUTS_PATH, **arrays)
    print(f"wrote {INPUTS_PATH}")


# --- CPU placement ----------------------------------------------------------------------------


class _PowerThrottlingState(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - ctypes layout
        ("Version", ctypes.c_ulong),
        ("ControlMask", ctypes.c_ulong),
        ("StateMask", ctypes.c_ulong),
    ]


def _efficiency_classes() -> dict[int, int]:
    from outrigger_sim.hostcpu import cpu_sets  # noqa: PLC0415 - Windows only

    return {cpu["logical"]: cpu["efficiency_class"] for cpu in cpu_sets() if cpu["group"] == 0}


def pin_to_cpus(
    cpus: list[int] | None = None, efficiency_class: int | None = None, priority: str = "normal"
) -> dict[str, object]:
    """Pin this process (and its children) to ``cpus`` or to one efficiency class.

    EcoQoS throttling is switched off for this process (``hostcpu.place_process`` does the
    same for the runner); ``priority`` sets this process's priority class. No system setting.
    """
    classes = _efficiency_classes()
    if cpus is None:
        cpus = [cpu for cpu, cls in classes.items() if cls == efficiency_class]
    mask = sum(1 << cpu for cpu in cpus)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    process = ctypes.c_void_p(kernel32.GetCurrentProcess())
    kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    is_pinned = bool(kernel32.SetProcessAffinityMask(process, mask))
    state = _PowerThrottlingState(1, 0x1, 0x0)  # EXECUTION_SPEED controlled, throttling off
    kernel32.SetProcessInformation.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong
    ]
    is_unthrottled = bool(
        kernel32.SetProcessInformation(
            process, PROCESS_POWER_THROTTLING, ctypes.byref(state), ctypes.sizeof(state)
        )
    )
    priority_class = PRIORITY_CLASSES[priority]
    is_priority_set = priority_class is None or bool(
        kernel32.SetPriorityClass(process, priority_class)
    )
    return {
        "logical_cpus": cpus,
        "affinity_mask_hex": f"0x{mask:08X}",
        "efficiency_classes": sorted({classes[cpu] for cpu in cpus}),
        "affinity_ok": is_pinned,
        "ecoqos_off_ok": is_unthrottled,
        "priority": priority,
        "priority_ok": is_priority_set,
    }


# --- measure: inputs, R8 emulation ------------------------------------------------------------


def load_columns(scenario: Scenario) -> dict[str, np.ndarray]:
    prefix = f"{scenario.name}/"
    with np.load(INPUTS_PATH, allow_pickle=False) as stored:
        return {key.removeprefix(prefix): stored[key] for key in stored.files
                if key.startswith(prefix)}


def build_measurements(columns: dict[str, np.ndarray]) -> list[Measurements]:
    return [
        Measurements(
            t_s=float(columns["t_s"][i]),
            specific_force_m_s2=columns["specific_force_m_s2"][i],
            angular_rate_rad_s=columns["angular_rate_rad_s"][i],
            head_pressure_Pa=columns["head_pressure_Pa"][i],
            stroke_m=columns["stroke_m"][i],
            stroke_corrected_m=columns["stroke_corrected_m"][i],
            rod_pressure_Pa=columns["rod_pressure_Pa"][i],
            oil_temperature_C=OIL_TEMPERATURE_C,
        )
        for i in range(len(columns["t_s"]))
    ]


def load_inputs(scenario: Scenario) -> tuple[list[Measurements], np.ndarray, list[str]]:
    """Stored measurements (as objects), recorded commands and phases before each update."""
    columns = load_columns(scenario)
    phases = [str(phase) for phase in columns["phase_before"]]
    return build_measurements(columns), columns["command_m_s"], phases


class R8Additions:
    """Per-period work R8 adds to the R7 update (estimate; ``run_c2_r8_10hz_check.py``).

    Every rule runs in every period (worst case); in R8 R-1 runs only in a REANCHOR move and
    R-2 only in TOUCH. The values do not steer the replayed controller.
    """

    def __init__(self, controller: C2Controller) -> None:
        geometry = controller.geometry
        self.head_area_m2 = geometry.head_area_m2
        self.annulus_area_m2 = geometry.annulus_area_m2
        self.max_speed_m_s = geometry.max_speed_m_s
        self.guard_level_N = geometry.F_min_N + controller.config.thresholds.guard_margin_N
        self.stroke_soft_end_m = geometry.stroke_measurable_max_m - R8_END_MARGIN_M
        self.touch_extension_m = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m
        self.attitude = AttitudeEstimator(
            CascadedLowPass(R8_ATTITUDE_TIME_CONSTANT_S, R8_ATTITUDE_STAGE_COUNT, R8_IMU_PERIOD_S)
        )
        self.completion = CascadedLowPass(R8_COMPLETION_TIME_CONSTANT_S, 1, R8_IMU_PERIOD_S)
        self.rate_attitude_rad = (0.0, 0.0)
        self.reanchor_history: list[float] = []
        self.touch_seen = np.zeros(LEG_COUNT, dtype=bool)
        self.confirm_counts = np.zeros((len(R8_CONFIRM_SAMPLES), LEG_COUNT), dtype=int)
        self.confirm_needed = np.array(R8_CONFIRM_SAMPLES)[:, None]
        self.previous_output_m_s = np.zeros(LEG_COUNT)

    def filter_extra_imu_samples(self, measurements: Measurements) -> None:
        """The 9 IMU samples of a 10 Hz period that R7 does not filter (multi-rate filter)."""
        roll_rate, pitch_rate = (float(rate) for rate in measurements.angular_rate_rad_s[:2])
        for _ in range(R8_IMU_SAMPLES_PER_PERIOD - 1):
            estimate = self.attitude.update(measurements.t_s, measurements.specific_force_m_s2)
            self.completion.update([estimate.roll_rad, estimate.pitch_rad])
            roll, pitch = self.rate_attitude_rad
            self.rate_attitude_rad = (
                roll + roll_rate * R8_IMU_PERIOD_S,
                pitch + pitch_rate * R8_IMU_PERIOD_S,
            )

    def adjust_command(self, measurements: Measurements, command_m_s: np.ndarray) -> np.ndarray:
        force_N = (
            np.asarray(measurements.head_pressure_Pa) * self.head_area_m2
            - np.asarray(measurements.rod_pressure_Pa) * self.annulus_area_m2
        )
        self._predict_reanchor_stop(force_N)
        command = self._touch_window(np.asarray(measurements.stroke_m), force_N, command_m_s)
        self._confirm_samples(force_N)
        command = self._slow_down_near_end(np.asarray(measurements.stroke_m), command)
        return self._limit_increment(command, force_N)

    def _predict_reanchor_stop(self, force_N: np.ndarray) -> bool:
        """R-1: ``P_hat = P - r_hat T (1 + d)`` with the mean unloading rate of 3 samples."""
        target_leg = SINK_LEG
        self.reanchor_history.append(float(force_N[target_leg]))
        self.reanchor_history = self.reanchor_history[-R8_STOP_PREDICTOR_SAMPLES:]
        predicted_N = force_N.copy()
        history = self.reanchor_history
        if len(history) >= 2:
            rate_N = (history[0] - history[-1]) / (len(history) - 1)
            predicted_N[target_leg] -= max(rate_N, 0.0) * (1 + R8_OUTPUT_DELAY_PERIODS)
        return bool(predicted_N[target_leg] <= self.guard_level_N)

    def _touch_window(
        self, stroke_m: np.ndarray, force_N: np.ndarray, command_m_s: np.ndarray
    ) -> np.ndarray:
        """R-2: 0.5 v_max inside 40 mm of the flat-floor touch extension."""
        self.touch_seen |= force_N >= self.guard_level_N
        is_in_window = stroke_m >= self.touch_extension_m - R8_TOUCH_WINDOW_M
        window_speed = np.where(
            is_in_window, R8_TOUCH_WINDOW_SPEED_FRACTION * self.max_speed_m_s, self.max_speed_m_s
        )
        approach_speed = np.where(self.touch_seen, 0.25 * self.max_speed_m_s, window_speed)
        return np.minimum(command_m_s, approach_speed)

    def _confirm_samples(self, force_N: np.ndarray) -> np.ndarray:
        """Consecutive-sample rules ABOVE 3, BELOW 2, P5 2, guard 1 (spec 99.3)."""
        conditions = np.stack([
            force_N >= self.guard_level_N,
            force_N < self.guard_level_N,
            force_N < self.guard_level_N + 2500.0,
            force_N < self.guard_level_N,
        ])
        self.confirm_counts = np.where(conditions, self.confirm_counts + 1, 0)
        return self.confirm_counts >= self.confirm_needed

    def _slow_down_near_end(self, stroke_m: np.ndarray, command_m_s: np.ndarray) -> np.ndarray:
        is_near_end = stroke_m >= self.stroke_soft_end_m - R8_END_APPROACH_M
        slow_m_s = R8_END_APPROACH_SPEED_FRACTION * self.max_speed_m_s
        return np.where(is_near_end & (command_m_s > slow_m_s), slow_m_s, command_m_s)

    def _limit_increment(self, command_m_s: np.ndarray, force_N: np.ndarray) -> np.ndarray:
        """Per-period increment: 0.25 v_max for load recovery (guard), 0.1 v_max otherwise."""
        is_recovering = (force_N < self.guard_level_N) & (command_m_s > self.previous_output_m_s)
        limit_m_s = self.max_speed_m_s * np.where(
            is_recovering, R8_GUARD_INCREMENT_FRACTION, R8_OTHER_INCREMENT_FRACTION
        )
        step_m_s = np.clip(command_m_s - self.previous_output_m_s, -limit_m_s, limit_m_s)
        self.previous_output_m_s = self.previous_output_m_s + step_m_s
        return self.previous_output_m_s


# --- measure: timing passes -------------------------------------------------------------------


@dataclass
class PassSamples:
    """Per-period times (ns) of one pass type, with the phase before each update."""

    phases: list[str] = field(default_factory=list)
    period_keys: list[int] = field(default_factory=list)
    """Same key for the same stored period in every repetition (best-of-repetitions)."""
    update_ns: list[int] = field(default_factory=list)
    imu_extra_ns: list[int] = field(default_factory=list)
    additions_ns: list[int] = field(default_factory=list)
    had_gc: list[bool] = field(default_factory=list)


class GcWatch:
    """Counts garbage collections, so a slow period can be attributed to one."""

    def __init__(self) -> None:
        self.collections = 0

    def __call__(self, phase: str, _info: dict) -> None:
        if phase == "start":
            self.collections += 1

    def __enter__(self) -> GcWatch:
        gc.callbacks.append(self)
        return self

    def __exit__(self, *_exc: object) -> None:
        gc.callbacks.remove(self)


@contextmanager
def gc_mode(is_gc_enabled: bool) -> Iterator[None]:
    """Collect, then run the block with the garbage collector on or off."""
    gc.collect()
    if is_gc_enabled:
        gc.enable()
    else:
        gc.disable()
    try:
        yield
    finally:
        gc.enable()


def replay(
    scenario: Scenario,
    inputs: list[Measurements],
    recorded_commands: np.ndarray,
    samples: PassSamples,
    *,
    emulates_r8: bool,
    gc_watch: GcWatch,
    key_offset: int = 0,
) -> None:
    """One pass through the stored inputs with a fresh controller, timing every period."""
    controller = new_controller(scenario)
    additions = R8Additions(controller) if emulates_r8 else None
    clock = time.perf_counter_ns
    for index, measurements in enumerate(inputs):
        phase = str(controller.phase)
        collections_before = gc_watch.collections
        start = clock()
        command = controller.update(measurements)
        after_update = clock()
        after_imu = after_update
        if additions is not None:
            additions.filter_extra_imu_samples(measurements)
            after_imu = clock()
            additions.adjust_command(measurements, np.asarray(command.leg_speed_m_s))
        end = clock()
        if not np.array_equal(command.leg_speed_m_s, recorded_commands[index]):
            raise RuntimeError(f"{scenario.name}: replay differs from the recording at {index}")
        samples.phases.append(phase)
        samples.period_keys.append(key_offset + index)
        samples.update_ns.append(after_update - start)
        samples.imu_extra_ns.append(after_imu - after_update)
        samples.additions_ns.append(end - after_imu)
        samples.had_gc.append(gc_watch.collections != collections_before)


def _quantile_table(values_us: np.ndarray) -> dict[str, float]:
    table = {"count": int(values_us.size), "mean_us": round(float(values_us.mean()), 2)}
    for name, quantile in QUANTILES.items():
        table[f"{name}_us"] = round(float(np.quantile(values_us, quantile)), 2)
    table["max_us"] = round(float(values_us.max()), 2)
    return table


def _best_of_repetitions(
    total_us: np.ndarray, period_keys: np.ndarray, phases: np.ndarray
) -> dict[str, float]:
    """Slowest period after taking each stored period's fastest repetition, per phase.

    A delay that recurs in every repetition of a period is computation; one that does not is
    the operating system (preemption, interrupts) or a garbage collection.
    """
    order = np.argsort(period_keys, kind="stable")
    sorted_keys = period_keys[order]
    starts = np.flatnonzero(np.r_[True, sorted_keys[1:] != sorted_keys[:-1]])
    best_us = np.minimum.reduceat(total_us[order], starts)
    best_phases = phases[order][starts]
    table = {"all": round(float(best_us.max()), 2)}
    for phase in sorted(set(best_phases)):
        table[str(phase)] = round(float(best_us[best_phases == phase].max()), 2)
    return table


def _tail_counts(total_us: np.ndarray) -> dict[str, int]:
    return {f"over_{limit_ms}ms": int((total_us > limit_ms * 1e3).sum())
            for limit_ms in TAIL_LIMITS_MS}


def summarise(samples: PassSamples, budget_s: float, segments: tuple[str, ...]) -> dict:
    """Quantiles per phase of the sum of ``segments`` (ns lists of ``samples``) in microseconds."""
    total_us = sum(np.array(getattr(samples, name), dtype=float) for name in segments) / 1e3
    phases = np.array(samples.phases)
    had_gc = np.array(samples.had_gc)
    per_phase = {"all": _quantile_table(total_us)}
    for phase in C2Phase:
        selected = phases == str(phase)
        if selected.any():
            per_phase[str(phase)] = _quantile_table(total_us[selected])
    worst_us = float(total_us.max())
    best_of_repetitions = _best_of_repetitions(
        total_us, np.array(samples.period_keys), phases
    )
    return {
        "segments": list(segments),
        "per_phase": per_phase,
        "max_of_best_repetition_us": best_of_repetitions,
        "tail_counts": _tail_counts(total_us),
        "periods_with_gc": int(had_gc.sum()),
        "max_with_gc_us": round(float(total_us[had_gc].max()), 2) if had_gc.any() else None,
        "max_without_gc_us": round(float(total_us[~had_gc].max()), 2),
        "budget_ms": budget_s * 1e3,
        "worst_fraction_of_budget": round(worst_us * 1e-6 / budget_s, 5),
        "p99_fraction_of_budget": round(per_phase["all"]["p99_us"] * 1e-6 / budget_s, 5),
        "headroom_factor_worst": round(budget_s / (worst_us * 1e-6), 1),
        "best_repetition_fraction_of_budget": round(
            best_of_repetitions["all"] * 1e-6 / budget_s, 5
        ),
    }


def timing_passes(all_inputs: dict[str, tuple]) -> dict[str, dict]:
    """R7 and R8-emulated passes, GC on and off, ``TIMED_REPETITIONS`` each after a warm-up."""
    results = {}
    for emulates_r8 in (False, True):
        for is_gc_enabled in (True, False):
            samples = PassSamples()
            key_offset = 0
            with GcWatch() as watch:
                for scenario in SCENARIOS:
                    inputs, commands, _ = all_inputs[scenario.name]
                    replay(scenario, inputs, commands, PassSamples(), emulates_r8=emulates_r8,
                           gc_watch=watch)  # warm-up pass, not counted
                    for _ in range(TIMED_REPETITIONS):
                        with gc_mode(is_gc_enabled):
                            replay(scenario, inputs, commands, samples, emulates_r8=emulates_r8,
                                   gc_watch=watch, key_offset=key_offset)
                    key_offset += len(inputs)
            name = f"{'r8_emulated' if emulates_r8 else 'r7'}_gc_{'on' if is_gc_enabled else 'off'}"
            if emulates_r8:
                results[name] = {
                    "all_in_one_period": summarise(
                        samples, R8_PERIOD_S, ("update_ns", "imu_extra_ns", "additions_ns")
                    ),
                    "critical_path_imu_outside": summarise(
                        samples, R8_PERIOD_S, ("update_ns", "additions_ns")
                    ),
                    "imu_extra_only": summarise(samples, R8_PERIOD_S, ("imu_extra_ns",)),
                    "additions_only": summarise(samples, R8_PERIOD_S, ("additions_ns",)),
                }
            else:
                results[name] = summarise(samples, R7_PERIOD_S, ("update_ns",))
            print(f"{name}: done", flush=True)
    return results


# --- measure: first call, allocation, profile -------------------------------------------------


def import_cost_ms() -> list[dict[str, float]]:
    """``import numpy`` and ``import outrigger_sim.control.c2`` in fresh child processes."""
    probe = (
        "import sys, time; sys.path.insert(0, sys.argv[1]); t0 = time.perf_counter(); "
        "import numpy; t1 = time.perf_counter(); import outrigger_sim.control.c2; "
        "t2 = time.perf_counter(); print((t1 - t0) * 1e3, (t2 - t1) * 1e3)"
    )
    results = []
    for _ in range(IMPORT_PROBE_COUNT):
        output = subprocess.run(
            [sys.executable, "-I", "-c", probe, str(SOURCE_DIR)],
            capture_output=True, text=True, check=True,
        ).stdout.split()
        results.append({"numpy_ms": round(float(output[0]), 1),
                        "c2_package_ms": round(float(output[1]), 1)})
    return results


def first_call_costs(scenario: Scenario, inputs: list[Measurements]) -> dict[str, float]:
    """Parameter load, controller construction and the first two updates (cold, in ms)."""
    clock = time.perf_counter
    start = clock()
    params = load_params()
    loaded = clock()
    controller = C2Controller.from_params(
        params, scenario_config(scenario, params.actuator.command_ramp_s)
    )
    built = clock()
    controller.update(inputs[0])
    first = clock()
    controller.update(inputs[1])
    second = clock()
    return {
        "load_params_ms": round((loaded - start) * 1e3, 2),
        "construct_controller_ms": round((built - loaded) * 1e3, 2),
        "first_update_ms": round((first - built) * 1e3, 3),
        "second_update_ms": round((second - first) * 1e3, 3),
    }


def first_pass_phase_max_us(scenario: Scenario, inputs, commands) -> dict[str, float]:
    """Slowest period per phase of the very first pass (first use of each code path)."""
    samples = PassSamples()
    with GcWatch() as watch:
        replay(scenario, inputs, commands, samples, emulates_r8=False, gc_watch=watch)
    phases = np.array(samples.phases)
    times_us = np.array(samples.update_ns) / 1e3
    return {phase: round(float(times_us[phases == phase].max()), 1)
            for phase in sorted(set(samples.phases))}


def allocation_per_period(scenario: Scenario, inputs: list[Measurements]) -> dict[str, dict]:
    """tracemalloc peak above the start of each update (bytes), per phase."""
    controller = new_controller(scenario)
    peaks: dict[str, list[int]] = {}
    tracemalloc.start()
    for measurements in inputs:
        phase = str(controller.phase)
        current_before, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        controller.update(measurements)
        _, peak = tracemalloc.get_traced_memory()
        peaks.setdefault(phase, []).append(peak - current_before)
    tracemalloc.stop()
    return {phase: {"median_bytes": int(np.median(values)), "max_bytes": int(max(values))}
            for phase, values in peaks.items()}


def gc_collections_per_1000_periods(scenario: Scenario, inputs: list[Measurements]) -> dict:
    controller = new_controller(scenario)
    gc.collect()
    before = [stats["collections"] for stats in gc.get_stats()]
    for measurements in inputs:
        controller.update(measurements)
    after = [stats["collections"] for stats in gc.get_stats()]
    scale = 1000.0 / len(inputs)
    return {f"gen{generation}": round((end - start) * scale, 2)
            for generation, (start, end) in enumerate(zip(before, after, strict=True))}


def profile_update(scenario: Scenario, inputs: list[Measurements]) -> dict[str, list[dict]]:
    """cProfile of one pass: top functions by own time and by cumulative time (per period)."""
    controller = new_controller(scenario)
    profiler = cProfile.Profile()
    profiler.enable()
    for measurements in inputs:
        controller.update(measurements)
    profiler.disable()
    stats = pstats.Stats(profiler)
    period_count = len(inputs)

    def top(sort_index: int) -> list[dict]:
        rows = sorted(stats.stats.items(), key=lambda item: -item[1][sort_index])
        table = []
        for (file_name, line, function), (_, calls, own_s, cumulative_s, _) in rows:
            if len(table) == PROFILE_TOP_COUNT:
                break
            table.append({
                "function": f"{Path(file_name).name}:{line}({function})",
                "calls_per_period": round(calls / period_count, 2),
                "own_us_per_period": round(own_s / period_count * 1e6, 2),
                "cumulative_us_per_period": round(cumulative_s / period_count * 1e6, 2),
            })
        return table

    return {"by_own_time": top(2), "by_cumulative_time": top(3)}


def measurement_build_us(scenario: Scenario) -> float:
    """Mean cost of building one ``Measurements`` (part of a real period: IO -> object)."""
    columns = load_columns(scenario)
    start = time.perf_counter()
    inputs = build_measurements(columns)
    return round((time.perf_counter() - start) / len(inputs) * 1e6, 2)


def environment(placement: dict[str, object]) -> dict[str, object]:
    return {
        "date": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "numpy": np.__version__,
        "processor": platform.processor(),
        "machine": platform.node(),
        "placement": placement,
        "controller_revision": "R7 (03_src/outrigger_sim/control/c2.py, C2_REVISION)",
        "timed_repetitions": TIMED_REPETITIONS,
    }


def measure(arguments: argparse.Namespace) -> None:
    placement = pin_to_cpus(cpus=[arguments.cpu], priority=arguments.priority)
    print(f"placement {placement}", flush=True)
    all_inputs = {scenario.name: load_inputs(scenario) for scenario in SCENARIOS}
    reference = SCENARIOS[0]
    reference_inputs = all_inputs[reference.name][0]
    result = {
        "environment": environment(placement),
        "cases": {name: {"periods": len(inputs), "phases": sorted(set(phases))}
                  for name, (inputs, _, phases) in all_inputs.items()},
        "import_cost": import_cost_ms(),
        "first_call": first_call_costs(reference, reference_inputs),
        "first_pass_phase_max_us": first_pass_phase_max_us(
            reference, *all_inputs[reference.name][:2]
        ),
        "measurement_build_us": measurement_build_us(reference),
        "timing": timing_passes(all_inputs),
        "allocation_per_period": allocation_per_period(reference, reference_inputs),
        "gc_collections_per_1000_periods": gc_collections_per_1000_periods(
            reference, reference_inputs
        ),
    }
    if arguments.profile:
        result["profile"] = profile_update(reference, reference_inputs)
    merged = {}
    if RESULTS_PATH.exists():
        merged = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    merged.setdefault("runs", {})[arguments.label] = result
    merged["about"] = __doc__.split("\n\n", 1)[0]
    RESULTS_PATH.write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {RESULTS_PATH} [{arguments.label}]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("record", help="closed-loop runs -> stored inputs (numba plant)")
    measure_parser = commands.add_parser("measure", help="time the replay on one CPU")
    measure_parser.add_argument("--cpu", type=int, required=True, help="logical CPU to pin to")
    measure_parser.add_argument("--label", required=True, help="result key, e.g. ecore27")
    measure_parser.add_argument("--priority", choices=sorted(PRIORITY_CLASSES), default="normal")
    measure_parser.add_argument("--profile", action="store_true", help="add a cProfile table")
    arguments = parser.parse_args()
    actions: dict[str, Callable[[argparse.Namespace], None]] = {
        "record": record, "measure": measure,
    }
    actions[arguments.command](arguments)


if __name__ == "__main__":
    main()
