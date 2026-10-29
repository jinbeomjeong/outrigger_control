"""Spec rev. 79 draft (study 2, spec 394): sensor error models with the new rules P-S8-28 / 29 / 30
on the reduced G6 / G8 harnesses (design: control-expert 2026-10-28, H-1 .. H-5, levels L0 .. L4).

Harnesses (imported, not changed; patched per job in the worker, restored afterwards):
  * G6: ``r72_g6_screen.job`` (s9 soil harness, one weak pad; project C2 preset);
  * G8: ``r69_g8_screen.job`` (r51 / r67 loop, one pad floor moved; project C2 preset);
  * ref: the G6 path with a pad type and a floor slope injected into the s9 case.
Adapter (this file):
  H-1 every control period, after the harness has stepped the plant: the ideal measurements of the
      harness go through ``SensorSuite`` (``LegSensorModel`` head / rod / stroke at the 10 Hz
      instant, WIKA A-10 grade, NAMUR range, chain resolution, stroke noise 0.1 mm; ``ImuModel`` on
      every 10 ms IMU sample, gyro included). Rod channel for G6: ``r64.with_two_pressures``
      (p_r = p_r0 - Gr / A_ann from the RodSidePlant state, p_h = (F_net + p_r A_ann) / A_p).
      The C2 target ``gyro_noise_std_rad_s`` is set from the IMU grade
      (as run_S9.level_sensor_setup).
  H-2 CHECK on (2 s, B1' extension up to 10 s) and the airborne round-trip zero calibration on;
      target acceptance and REANCHOR stay off (preset). The run limit grows by
      ``CHECK_RUN_EXTENSION_S`` on every CHECK level (L1 and above alike).
  H-3 10 Hz truth log (true leg force at the instant and its 1 ms period minimum, motor stroke,
      crawler load); the per-run truth summary is computed in the worker (``summarise_run``).
  H-4 seed = 20261028 + 100000 g + 1000 s + k (g set group, s seed index, k case index in its
      group): the same s gives the same noise draws on every grade (paired comparison).
  H-5 L0 = the harness channels (G6 head only, G8 head + rod), ideal sensors, CHECK off: the
      command hashes must equal the rev. 76 baseline (``r79_sensor_judge.py identity``).
Levels: L0 harness path, L1 ideal + two channels + CHECK (path reference), L2 normal + zero
  calibration + IMU normal_zeroed (5 seeds), L3 / L4 conservative / old_worst (3 seeds), options
  L2nocal (normal, CHECK on, no zero calibration) and L2imuideal (IMU grade ideal).
Sets: g6 (116 = r72 all + rigid_all), g6core (48), g6rear (32), g8 (50), ref (21), all (187),
  core (119 = g6core + g8 + ref), identity (20: every 9th G6 key + every 8th G8 key).
Options (control-expert 2026-10-28): L2imuideal on g6rear x seeds 0..4 (160), L2nocal on
  g6core x seeds 0..2 (144, fault-stress record, no acceptance).

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r79_sensor_screen.py <project_root> <out_json> [workers]
  python -I r79_sensor_screen.py <project_root> --list
Env: R79_LEVELS (comma, default L1), R79_SET (default identity), R79_SEEDS (comma list of seed
  indices; default per level 0..n-1), R79_FILTER (substrings, any match keeps a job),
  R79_AFFINITY (hex mask on the parent, inherited by the workers), R79_TRACE=1 (keep the 10 Hz
  truth log in the record; the G6 recontact intervals ``r79.recontact_events`` of spec 407.2 are
  kept without it), R79_ROD_MODEL = dyn_map (default) | harness | extend_vent
  (``ROD_MODELS``; the last two for comparison), R79_CANDIDATE (spec 424.5: comma list of
  ``s9_slope_fix_candidates.py`` candidates, e.g. ``current,D1,D2+D3``; every job runs once per
  candidate, key ``cand=<name>#<key>``, record ``candidate`` / ``candidate_record``).
"""

from __future__ import annotations

import ctypes
import json
import math
import os
import sys
import time
import types
from dataclasses import dataclass, field, replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for _path in (ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "s8",
              ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.sensors.hydraulic import (  # noqa: E402
    LegSensorConfig,
    wika_a10_leg_sensor_config,
)
from outrigger_sim.sensors.imu import ImuErrorConfig, imu_config_for_grade  # noqa: E402
from outrigger_sim.sensors.suite import SensorSuite  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
IMU_SAMPLE_S = 0.01
SEED_BASE = 20261028
SEED_GROUP_STRIDE = 100_000
SEED_INDEX_STRIDE = 1_000
CHECK_TIME_S = 2.0
"""``TargetSettings().check_time_s`` (the Chrono preset value)."""
CHECK_RUN_EXTENSION_S = 10.0
"""Extra run time on CHECK levels = ``TargetSettings.check_max_s`` (normal grade B1' window)."""
TWIST_WINDOW_S = 5.0
"""P-S8-29 V2b non-rising window (spec 386)."""
GROUP_INDEX = {"g6": 0, "g8": 1, "ref": 2}
G8_SLOPE_GAPS_MM = (140.0, 170.0, 200.0, 230.0)
G8_FLAT_RAISED_MM = (200.0, 290.0, 320.0)
G8_FLAT_LOWERED_MM = (150.0,)
G6_CORE_WEAK = ("J1", "J2")
G6_CORE_LEGS = ("RL", "RR")
G6_CORE_BASES = ("G1", "rigid")
REF_SOILS = ("G1", "J1", "J2", "S1")
REF_PADS = ("A", "B")
IDENTITY_G6_STEP = 9
"""Odd step: the G6 list alternates F_s 0 / 4, so the subset holds both (13 keys)."""
IDENTITY_G8_STEP = 8


# --------------------------------------------------------------------------------------- levels
@dataclass(frozen=True)
class SensorLevel:
    """Sensor grades and controller start of one study level.

    ``pressure_grade`` / ``imu_grade`` ``None`` = error-free sensors (``LegSensorConfig()``,
    ``ImuErrorConfig()``); otherwise the WIKA A-10 grade / the IMU grade name.
    """

    name: str
    pressure_grade: str | None
    imu_grade: str | None
    adds_rod_channel: bool
    check_enabled: bool
    zero_calibration: bool
    imu_rate_gyro: bool
    """Gyro of every IMU sample delivered and averaged (Chrono SensorSuite path); False = the
    harness end-of-period rate (L0)."""
    default_seeds: int


LEVELS = {
    "L0": SensorLevel("L0", None, None, False, False, False, False, 1),
    "L1": SensorLevel("L1", None, None, True, True, True, True, 1),
    "L2": SensorLevel("L2", "normal", "normal_zeroed", True, True, True, True, 5),
    "L3": SensorLevel("L3", "conservative", "normal_zeroed", True, True, True, True, 3),
    "L4": SensorLevel("L4", "old_worst", "normal_zeroed", True, True, True, True, 3),
    "L2nocal": SensorLevel("L2nocal", "normal", "normal_zeroed", True, True, False, True, 3),
    "L2imuideal": SensorLevel("L2imuideal", "normal", "ideal", True, True, True, True, 5),
}


ROD_MODELS = ("dyn_map", "harness", "extend_vent")
"""Rod reading of the L1+ levels (default ``dyn_map``, the other two kept for comparison):
``dyn_map`` = the dynamics-expert mapping of the RodSidePlant state (``DynMapRodModel``);
``harness`` = ``r64.with_two_pressures`` (p_r = p_r0 - Gr / A_ann; after a retraction lock
p_r0 = p_r0_after_retract, about 31-35 bar, which an extending leg keeps while it moves);
``extend_vent`` = the same, but a released extending leg reads p_r0_after_extend (2 bar). All three
keep the net force F_net."""
DEFAULT_ROD_MODEL = "dyn_map"
ROD_LAG_S = 0.05
"""tau_v of the moving rod pressure (rod_side_pressure.md 7.3, ``RodSideParams``)."""
SYNTH_STROKE_MAX_M = 0.70
SYNTH_HEAD_DEAD_LENGTH_M = 0.05
"""Geometry of the ``RodSideSynth`` cross-check only (YAML stroke, L_0h lower value)."""


class DynMapRodModel:
    """``dyn_map`` rod-side reading from the harness RodSidePlant state (dynamics-expert rule,
    2026-10-28; sources rod_side_pressure.md 7.3 / 14.7, 03_src rod_chamber / l2b_rod_side).

    * locked leg (``plant.locked``): ``p_r = max(p_floor, p_r0 - (Gr - Gr_lock) / A_ann)``,
      ``p_floor`` = 0.1 bar abs - 1 atm; p_r0 = the plant's lock pressure (2 bar g after an
      extension, the YAML constant ``p_r0_after_retract`` after a retraction: the harness keeps
      that constant, recorded as such);
    * moving leg: from the value at the release, an exact first-order step per 1 ms chunk
      (tau_v 0.05 s) towards the 7.4 / 14.7 target of ``RodSideSynth.moving_target_Pa``
      (extend: flow-dependent back pressure, at least -F / A_ann; retract: POC-A meter-in,
      at most the relief), F = F_net, u = the applied valve speed;
    * head: ``p_h = (F_net + p_r A_ann) / A_p`` clipped at the floor, then p_r re-solved.

    A ``RodSideSynth`` runs beside it on the same signals at the control instants; the largest
    |delta p_r| is recorded (``meta``).
    """

    def __init__(self) -> None:
        self.rod_Pa: np.ndarray | None = None
        self.was_locked: np.ndarray | None = None
        self._targets = None
        self._synth = None
        self.max_delta_vs_synth_Pa = {"locked": 0.0, "moving": 0.0}

    def _setup(self, plant) -> None:
        from outrigger_sim.params import load_params
        from outrigger_sim.sensors.hydraulic import leg_head_areas_from_params
        from outrigger_sim.sensors.rod_side import RodSideParams, RodSideSynth

        params = load_params()
        synth_params = RodSideParams.from_params(params, rod_pressure_lag_s=ROD_LAG_S)
        head_area = leg_head_areas_from_params(params)
        annulus = np.asarray(plant.A_ann, float)
        self._targets = RodSideSynth(synth_params, head_area, annulus, SYNTH_STROKE_MAX_M,
                                     SYNTH_HEAD_DEAD_LENGTH_M, IMU_SAMPLE_S)
        self._synth = RodSideSynth(synth_params, head_area, annulus, SYNTH_STROKE_MAX_M,
                                   SYNTH_HEAD_DEAD_LENGTH_M, 0.1)
        self.floor_Pa = synth_params.floor_gauge_Pa

    def locked_value_Pa(self, plant) -> np.ndarray:
        drop = (np.asarray(plant.Gr, float) - np.asarray(plant.Gr_lock, float)) / plant.A_ann
        return np.maximum(self.floor_Pa, np.asarray(plant.p_r0, float) - drop)

    def step_chunk(self, plant, valve, chunk_s: float) -> None:
        """Advance the moving-leg lag over one 1 ms chunk (after the plant step)."""
        if not getattr(plant, "armed", False):
            return
        if self._targets is None:
            self._setup(plant)
        from outrigger_sim.sensors.rod_side import LegMode

        locked = np.asarray(plant.locked, bool)
        if self.rod_Pa is None:
            self.rod_Pa = self.locked_value_Pa(plant)
            self.was_locked = np.ones(4, bool)
        speed = np.asarray(valve, float)
        self.last_speed = speed.copy()
        mode = np.where(locked, LegMode.LOCKED,
                        np.where(np.asarray(plant.last_dir, float) > 0.0, LegMode.EXTEND,
                                 LegMode.RETRACT))
        target = self._targets.moving_target_Pa(np.asarray(plant.pressure(), float), mode,
                                                np.abs(speed))
        decay = math.exp(-chunk_s / ROD_LAG_S)
        moving = np.where(np.isnan(target), self.rod_Pa,
                          target + (self.rod_Pa - target) * decay)
        self.rod_Pa = np.where(locked, self.locked_value_Pa(plant), moving)
        self.was_locked = locked

    def __call__(self, plant, ideal, head_area):
        if self.rod_Pa is None:
            self.step_chunk(plant, np.zeros(4), 0.0)
        net = np.asarray(plant.pressure(), float)
        annulus = np.asarray(plant.A_ann, float)
        head = (net + self.rod_Pa * annulus) / head_area
        clipped = head < self.floor_Pa
        head = np.where(clipped, self.floor_Pa, head)
        self.rod_Pa = np.where(clipped, (head * head_area - net) / annulus, self.rod_Pa)
        self._cross_check(plant, net)
        return replace(ideal, head_pressure_Pa=head, rod_pressure_Pa=self.rod_Pa.copy())

    def _cross_check(self, plant, net) -> None:
        speed = np.where(np.asarray(plant.locked, bool), 0.0,
                         getattr(self, "last_speed", np.zeros(4)))
        _, synth_rod = self._synth.update(net, speed, np.asarray(plant.x, float))
        key = "locked" if bool(np.all(plant.locked)) else "moving"
        delta = float(np.max(np.abs(synth_rod - self.rod_Pa)))
        self.max_delta_vs_synth_Pa[key] = max(self.max_delta_vs_synth_Pa[key], delta)

    def meta(self) -> dict:
        return {"model": "dyn_map", "tau_v_s": ROD_LAG_S,
                "p_r0_after_retract": "YAML constant (harness RodSidePlant lock), not tracked",
                "max_abs_delta_p_r_vs_RodSideSynth_bar": {
                    k: round(v / 1e5, 3) for k, v in self.max_delta_vs_synth_Pa.items()}}


def split_extend_vent(plant, ideal, head_area):
    """ASSUMPTION (option ``extend_vent``, hydraulics to confirm): a released leg whose last
    command extended reads the after-extension lock pressure on the rod side; the head reading
    keeps the harness net force, p_h = (F_net + p_r A_ann) / A_p."""
    extending = ~np.asarray(plant.locked, bool) & (np.asarray(plant.last_dir, float) > 0.0)
    harness_p_r = np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / plant.A_ann
    p_r = np.where(extending, np.asarray(plant.p_ext, float), harness_p_r)
    p_h = (plant.pressure() + p_r * plant.A_ann) / head_area
    return replace(ideal, head_pressure_Pa=p_h, rod_pressure_Pa=p_r)


def rod_split_function(rod_model: str):
    """Fresh rod-reading function of a run (``dyn_map`` keeps state, one object per run)."""
    if rod_model not in ROD_MODELS:
        raise ValueError(f"rod model must be one of {ROD_MODELS}: {rod_model!r}")
    if rod_model == "dyn_map":
        return DynMapRodModel()
    if rod_model == "extend_vent":
        return split_extend_vent
    import r64_g4_closed_loop as r64

    return r64.with_two_pressures


def case_seed(group: int, seed_index: int, case_index: int) -> int:
    """H-4 noise seed; independent of the level, so the same ``seed_index`` pairs the grades."""
    return SEED_BASE + SEED_GROUP_STRIDE * group + SEED_INDEX_STRIDE * seed_index + case_index


def level_config(config, level: SensorLevel):
    """C2 config of a level: CHECK and zero calibration (H-2) and the gyro noise of the grade."""
    if not level.check_enabled:
        return config
    from outrigger_sim.control.zero_calibration import ZeroCalibrationMode

    target = replace(config.target, check_time_s=CHECK_TIME_S)
    if level.imu_grade is not None:
        gyro_sigma = imu_config_for_grade(level.imu_grade, sample_period_s=config.period_s)
        target = replace(target, gyro_noise_std_rad_s=float(gyro_sigma.gyro_noise_std_rad_s))
    mode = (ZeroCalibrationMode.AIRBORNE_ROUNDTRIP if level.zero_calibration
            else ZeroCalibrationMode.OFF)
    zero_calibration = replace(config.zero_calibration, mode=mode)
    return replace(config, target=target, zero_calibration=zero_calibration)


# --------------------------------------------------------------------------------------- sensors
class SensorAdapter:
    """Ideal harness measurements -> delivered measurements of one level (H-1).

    Args:
        level: Study level.
        seed: Noise seed of the run (``case_seed``).
        split_pressures: ``(plant, m, head_area) -> m`` with head and rod readings
            (``rod_split_function``); used on the levels with a rod channel when the harness
            gives head only, or always when ``always_split`` (a non-harness rod model).
        always_split: Replace a rod reading the harness already gives (G8 path).
    """

    def __init__(self, level: SensorLevel, seed: int, split_pressures=None,
                 always_split: bool = False) -> None:
        self.level = level
        self.always_split = always_split
        if level.imu_grade is None:
            imu_config = ImuErrorConfig(sample_period_s=IMU_SAMPLE_S)
        else:
            imu_config = imu_config_for_grade(level.imu_grade, sample_period_s=IMU_SAMPLE_S)
        if level.pressure_grade is None:
            leg_config = LegSensorConfig()
        else:
            leg_config = wika_a10_leg_sensor_config(level.pressure_grade)
        self.suite = SensorSuite(imu_config, leg_config, seed)
        self.split_pressures = split_pressures

    def deliver(self, ideal, plant, head_area, gyro_samples, sample_times):
        """Delivered measurements for one control period.

        Args:
            ideal: Harness measurements (IMU samples = 10 ms mean specific forces).
            plant: Harness plant (rod-side state for the rod channel).
            head_area: Head areas of the controller geometry.
            gyro_samples: True angular rate at the end of every IMU sample, (n, 3).
            sample_times: Plant time at the end of every IMU sample, (n,).
        """
        needs_split = ideal.rod_pressure_Pa is None or self.always_split
        if self.level.adds_rod_channel and needs_split:
            ideal = self.split_pressures(plant, ideal, head_area)
        forces = np.asarray(ideal.imu_specific_force_samples_m_s2, float)
        if len(gyro_samples) != len(forces):
            raise RuntimeError(f"{len(gyro_samples)} gyro samples for {len(forces)} IMU samples")
        if self.level.imu_rate_gyro:
            samples = types.SimpleNamespace(
                sample_t_s=np.asarray(sample_times, float),
                sample_specific_force_m_s2=forces,
                sample_angular_rate_rad_s=np.asarray(gyro_samples, float))
            return self.suite.apply(ideal, samples)
        return self._deliver_with_end_rate(ideal, forces, sample_times)

    def _deliver_with_end_rate(self, ideal, forces, sample_times):
        """L0: the harness angular rate (end of the period) and no gyro samples."""
        delivered = np.empty_like(forces)
        for i, force in enumerate(forces):
            reading = self.suite.imu.measure(float(sample_times[i]), force,
                                             ideal.angular_rate_rad_s)
            delivered[i] = reading.specific_force_m_s2
        legs = self.suite.legs.measure(ideal.head_pressure_Pa, ideal.stroke_m,
                                       ideal.stroke_corrected_m, ideal.rod_pressure_Pa,
                                       t_s=ideal.t_s)
        return replace(ideal, specific_force_m_s2=delivered.mean(axis=0),
                       imu_specific_force_samples_m_s2=delivered,
                       head_pressure_Pa=legs.head_pressure_Pa, stroke_m=legs.stroke_m,
                       stroke_corrected_m=legs.stroke_corrected_m,
                       rod_pressure_Pa=legs.rod_pressure_Pa)


# --------------------------------------------------------------------------------------- truth log
class ChunkProbe:
    """Wraps the harness ``_lagged_step`` (1 ms chunk): gyro at every IMU sample end, and the
    period minimum of the true leg force (contact - rod weight) and maximum of the crawler load."""

    def __init__(self, lagged_step, chunks_per_sample: int, chunk_hook=None) -> None:
        self.lagged_step = lagged_step
        self.chunks_per_sample = chunks_per_sample
        self.chunk_hook = chunk_hook
        """``(plant, valve, chunk_s)`` after every chunk (the ``dyn_map`` rod lag)."""
        self.reset_period()

    def reset_period(self) -> None:
        self.chunk_count = 0
        self.gyro_samples: list[np.ndarray] = []
        self.sample_times: list[float] = []
        self.force_min = np.full(4, np.inf)
        self.crawler_max = 0.0

    def __call__(self, plant, cmd, valve, lag_steps):
        acc = self.lagged_step(plant, cmd, valve, lag_steps)
        if self.chunk_hook is not None:
            self.chunk_hook(plant, valve, lag_steps * plant.dt)
        self.chunk_count += 1
        self.force_min = np.minimum(self.force_min, np.asarray(acc[11:15], float) - plant.Wr)
        self.crawler_max = max(self.crawler_max, float(acc[15]))
        if self.chunk_count % self.chunks_per_sample == 0:
            self.gyro_samples.append(np.asarray(plant.w, float).copy())
            self.sample_times.append(float(plant.t))
        return acc


@dataclass
class TruthLog:
    """H-3: 10 Hz truth at every controller measurement (phase = the one in effect)."""

    t_s: list[float] = field(default_factory=list)
    phase: list[str] = field(default_factory=list)
    stroke_m: list[np.ndarray] = field(default_factory=list)
    force_N: list[np.ndarray] = field(default_factory=list)
    force_min_N: list[np.ndarray] = field(default_factory=list)
    crawler_max_N: list[float] = field(default_factory=list)

    def append(self, plant, phase: str, probe: ChunkProbe) -> None:
        self.t_s.append(float(plant.t))
        self.phase.append(phase)
        self.stroke_m.append(np.asarray(plant.sref, float).copy())
        self.force_N.append(np.asarray(plant.true_cyl_force(), float).copy())
        self.force_min_N.append(probe.force_min.copy())
        self.crawler_max_N.append(probe.crawler_max)

    def arrays(self) -> dict[str, np.ndarray]:
        return {"t_s": np.asarray(self.t_s), "phase": np.asarray(self.phase),
                "stroke_m": np.asarray(self.stroke_m).reshape(-1, 4),
                "force_N": np.asarray(self.force_N).reshape(-1, 4),
                "force_min_N": np.asarray(self.force_min_N).reshape(-1, 4),
                "crawler_max_N": np.asarray(self.crawler_max_N)}


@dataclass
class ActiveRun:
    """State of the run in this worker (the harness patches read it)."""

    level: SensorLevel
    adapter: SensorAdapter
    probe: ChunkProbe | None = None
    truth: TruthLog = field(default_factory=TruthLog)
    ctrl: object | None = None
    plant: object | None = None

    def after_period(self, plant, ideal, head_area):
        """Truth row, then the delivered measurements (called before the controller update)."""
        self.plant = plant
        phase = "none" if self.ctrl is None else str(self.ctrl.phase)
        self.truth.append(plant, phase, self.probe)
        delivered = self.adapter.deliver(ideal, plant, head_area, self.probe.gyro_samples,
                                         self.probe.sample_times)
        self.probe.reset_period()
        return delivered


_ACTIVE: ActiveRun | None = None


# --------------------------------------------------------------------------------------- summary
def twist_load_N(forces: np.ndarray, twist_vector: np.ndarray) -> np.ndarray:
    """Twist load D = n^T F per row, n = the controller's unit twist vector (the quantity of the
    P-S8-29 15 kN limit; about half of (F_FL + F_RR) - (F_FR + F_RL))."""
    return np.atleast_2d(forces) @ np.asarray(twist_vector, float)


def largest_rise(values: np.ndarray) -> float:
    """Largest rise of a series above its running minimum (0 for a non-rising series)."""
    if len(values) == 0:
        return 0.0
    return float(np.max(values - np.minimum.accumulate(values)))


def _row_at(t_s: np.ndarray, t: float) -> int:
    return int(np.argmin(np.abs(t_s - t)))


def _event_times(events, prefix: str) -> list[tuple[float, str]]:
    return [(float(t), name) for t, name in events if name.split(":")[0] == prefix]


def _departure(t_s, crawler, t_after: float):
    """First crawler-free row after ``t_after`` and the crawler re-contacts after it."""
    free = np.flatnonzero((crawler <= 0.0) & (t_s >= t_after - 1e-9))
    if free.size == 0:
        return None, 0
    first = int(free[0])
    loaded = crawler[first:] > 0.0
    onsets = int(np.sum(loaded[1:] & ~loaded[:-1]))
    return first, onsets


def _done_to_ready_rows(truth, t_e: float) -> np.ndarray:
    """Rows from a relaxed DONE at ``t_e`` up to the next READY row (or the run end)."""
    t_s = truth["t_s"]
    after = t_s >= t_e - 1e-9
    ready_after = np.flatnonzero(after & (truth["phase"] == "ready"))
    t_end = t_s[ready_after[0]] if ready_after.size else t_s[-1]
    return after & (t_s <= t_end + 1e-9)


def summarise_twist_relax(truth, events, f_min_N: float, twist_vector) -> list[dict]:
    """S-3 truth at every ``INFO_TWIST_UNSETTLED:<D kN>``: the controller's D (event value),
    the true D = n^T F_true and the read error |D_meas - D_true|, the smallest true force at
    the event and from the event to READY, and the 5 s window rise of the true |D|."""
    t_s = truth["t_s"]
    true_twist = twist_load_N(truth["force_N"], twist_vector)
    abs_twist = np.abs(true_twist)
    rows = []
    for t_e, name in _event_times(events, "INFO_TWIST_UNSETTLED"):
        i = _row_at(t_s, t_e)
        window = (t_s >= t_e - TWIST_WINDOW_S - 1e-9) & (t_s <= t_e + 1e-9)
        d_meas_kN = float(name.split(":")[1])
        d_true_kN = float(true_twist[i]) / 1e3
        min_to_ready = float(truth["force_min_N"][_done_to_ready_rows(truth, t_e)].min())
        rows.append({"t_s": round(t_e, 2), "event": name,
                     "D_meas_kN": d_meas_kN, "D_true_kN": round(d_true_kN, 3),
                     "D_read_error_kN": round(abs(d_meas_kN - d_true_kN), 3),
                     "true_abs_D_kN": round(float(abs_twist[i]) / 1e3, 3),
                     "true_min_F_kN": round(float(truth["force_min_N"][i].min()) / 1e3, 3),
                     "true_below_F_min": bool(truth["force_min_N"][i].min() < f_min_N),
                     "true_min_F_to_ready_kN": round(min_to_ready / 1e3, 3),
                     "true_below_F_min_to_ready": bool(min_to_ready < f_min_N),
                     "window_rise_kN": round(largest_rise(abs_twist[window]) / 1e3, 3),
                     "window_end_minus_start_kN": round(float(
                         abs_twist[window][-1] - abs_twist[window][0]) / 1e3, 3)
                     if window.any() else None})
    return rows


def summarise_lift_pauses(truth, events, f_min_N: float) -> list[dict]:
    """S-4 truth at every ``INFO_LIFT_PAUSED:<leg>``: true sample drop and true value."""
    t_s = truth["t_s"]
    forces = truth["force_N"]
    rows = []
    for t_e, name in _event_times(events, "INFO_LIFT_PAUSED"):
        leg = LEGS.index(name.split(":")[1])
        i = _row_at(t_s, t_e)
        drop = float(forces[i - 1, leg] - forces[i, leg]) if i > 0 else math.nan
        rows.append({"t_s": round(t_e, 2), "leg": LEGS[leg],
                     "true_drop_kN": round(drop / 1e3, 3),
                     "true_F_kN": round(float(forces[i, leg]) / 1e3, 3),
                     "true_F_over_F_min": round(float(forces[i, leg]) / f_min_N, 3)})
    return rows


def summarise_run(truth, events, f_min_N: float, weight_N: float, twist_vector) -> dict:
    """Per-run truth summary (H-3) for the S-1 .. S-6 judge; ``events`` = (t_s, name) pairs."""
    t_s = truth["t_s"]
    crawler = truth["crawler_max_N"]
    not_check = np.flatnonzero(truth["phase"] != "check")
    t_check_end = float(t_s[not_check[0]]) if not_check.size else None
    first_free, recontacts = _departure(t_s, crawler, t_check_end or 0.0)
    t_off = None if first_free is None else float(t_s[first_free])
    loc = _event_times(events, "crawler_liftoff_confirmed")
    t_loc = loc[0][0] if loc else None
    crawler_at_loc = None if t_loc is None else float(crawler[_row_at(t_s, t_loc)])
    min_after_off = (None if first_free is None
                     else float(truth["force_min_N"][first_free:].min()))
    guard = [(round(t, 2), n) for t, n in events
             if n.split(":")[0] in ("WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT",
                                    "FAULT_STROKE_END")]
    return {
        "t_check_end_s": t_check_end, "t_off_s": t_off, "t_loc_s": t_loc,
        "loc_minus_off_s": None if t_loc is None or t_off is None else round(t_loc - t_off, 2),
        "n_recontact_after_off": recontacts,
        "crawler_at_loc_N": crawler_at_loc,
        "crawler_at_loc_over_W": None if crawler_at_loc is None else crawler_at_loc / weight_N,
        "min_true_F_after_off_kN": None if min_after_off is None else min_after_off / 1e3,
        "max_true_stroke_mm": float(truth["stroke_m"].max()) * 1e3,
        "guard_events": guard,
        "n_stroke_end_fault": sum(1 for _, n in guard if n.startswith("FAULT_STROKE_END")),
        "anchor_applied": any(n.startswith("INFO_LOC_CLEARANCE_ANCHOR") for _, n in events),
        "twist_relax": summarise_twist_relax(truth, events, f_min_N, twist_vector),
        "n_done_entries": int(np.sum((truth["phase"][1:] == "done")
                                     & (truth["phase"][:-1] != "done"))),
        "lift_pauses": summarise_lift_pauses(truth, events, f_min_N),
        "warn_fault": sorted({n.split(":")[0] for _, n in events
                              if n.startswith(("WARN", "FAULT"))}),
        "rod_fallback": [(round(t, 2), n.split(":")[1])
                         for t, n in _event_times(events, "WARN_ROD_PRESSURE_FALLBACK")],
        "F_min_kN": f_min_N / 1e3, "W_N": weight_N,
    }


def zero_calibration_outcome(meta: dict) -> dict:
    """Per-leg CHECK zero calibration result (as run_S9.zero_calibration_outcome)."""
    zc = (meta or {}).get("zero_calibration") or {}
    legs = ((zc.get("result") or {}).get("legs")) or {}
    rows = {leg: {"status": (legs.get(leg) or {}).get("status"),
                  "reason": (legs.get(leg) or {}).get("reason")} for leg in LEGS}
    return {"is_active": zc.get("is_active"), "legs": rows,
            "all_calibrated": all(r["status"] == "calibrated" for r in rows.values()),
            "offsets_N": zc.get("offsets_N")}


# --------------------------------------------------------------------------------------- case sets
@dataclass(frozen=True)
class CaseSpec:
    """One harness case: ``harness`` g6 / g8 / ref, the harness key, its seed group and index."""

    harness: str
    inner: str
    index: int

    @property
    def key(self) -> str:
        return f"{self.harness}|{self.inner}"

    @property
    def group(self) -> int:
        return GROUP_INDEX[self.harness]


def g6_keys() -> list[str]:
    """G6 116 = r72 ``all`` (64) + ``rigid_all`` (52), the rev. 76 baseline order."""
    import r72_g6_screen as g6

    return g6.all_jobs("all") + g6.all_jobs("rigid_all")


def is_g6_rear(inner: str) -> bool:
    """The 32 rear cases: J1 / J2 @ RL / RR x top / bottom x F_s 0 / 4 on G1 and rigid."""
    tag, soil, _, _ = inner.split("|")
    if tag == "ref":
        return False
    base, rest = soil.split("+")
    weak, leg = rest.split("@")
    return weak in G6_CORE_WEAK and leg in G6_CORE_LEGS and base in G6_CORE_BASES


def is_g6_core(inner: str) -> bool:
    """G6 core 48 (control-expert 2026-10-28): the 32 rear cases, rigid + S1 front (C) (8) and
    the uniform G1 / rigid refs x top / bottom x F_s 0 / 4 (8, pairs complete)."""
    tag, soil, _, _ = inner.split("|")
    if tag == "ref":
        return soil in G6_CORE_BASES
    if is_g6_rear(inner):
        return True
    base, rest = soil.split("+")
    weak, leg = rest.split("@")
    return base == "rigid" and weak == "S1" and leg in ("FL", "FR")


def g8_keys() -> list[str]:
    """G8 partial 50 (r69 key format, top, F_s 4)."""
    keys = []
    for floor in ("edge", "rpB"):
        keys.append(f"slope|{floor}|top|4.0|ref|none|0")
        for leg in LEGS:
            keys += [f"slope|{floor}|top|4.0|{leg}|raised|{g}" for g in G8_SLOPE_GAPS_MM]
    for leg in LEGS:
        keys += [f"main|flat|top|4.0|{leg}|raised|{g}" for g in G8_FLAT_RAISED_MM]
        keys += [f"main|flat|top|4.0|{leg}|lowered|{d}" for d in G8_FLAT_LOWERED_MM]
    return keys


def ref_keys() -> list[str]:
    """Reference 21: rigid on the 13 s9 slopes + uniform soil x pad A / B, top, F_s 4."""
    import s9_runs

    keys = [f"rigid|B|{roll:g},{pitch:g}" for roll, pitch in s9_runs.SLOPES]
    keys += [f"{soil}|{pad}|0,0" for soil in REF_SOILS for pad in REF_PADS]
    return keys


def cases_for_set(name: str) -> list[CaseSpec]:
    g6 = [CaseSpec("g6", k, i) for i, k in enumerate(g6_keys())]
    g8 = [CaseSpec("g8", k, i) for i, k in enumerate(g8_keys())]
    ref = [CaseSpec("ref", k, i) for i, k in enumerate(ref_keys())]
    g6core = [c for c in g6 if is_g6_core(c.inner)]
    g6rear = [c for c in g6 if is_g6_rear(c.inner)]
    sets = {"g6": g6, "g6core": g6core, "g6rear": g6rear, "g8": g8, "ref": ref,
            "all": g6 + g8 + ref,
            "core": g6core + g8 + ref,
            "identity": g6[::IDENTITY_G6_STEP] + g8[::IDENTITY_G8_STEP]}
    return sets[name]


def job_keys(set_name: str, level_names: list[str], seeds: list[int] | None) -> list[str]:
    jobs = []
    for level_name in level_names:
        level_seeds = seeds if seeds is not None else range(LEVELS[level_name].default_seeds)
        for seed_index in level_seeds:
            jobs += [f"{level_name}|s{seed_index}|{c.harness}|{c.index}|{c.inner}"
                     for c in cases_for_set(set_name)]
    return jobs


CANDIDATE_ENV = "R79_CANDIDATE"
"""Spec 424.5: comma list of ``s9_slope_fix_candidates.py`` candidates (tokens joined by "+",
"current" = the project controller as it is) applied to every job of the run."""
CANDIDATE_KEY_PREFIX = "cand="
CANDIDATE_KEY_SEPARATOR = "#"


def candidate_names() -> list[str]:
    return [name for name in os.environ.get(CANDIDATE_ENV, "").split(",") if name]


def split_candidate(key: str) -> tuple[str | None, str]:
    """(candidate, key without it) of ``cand=<name>#<key>``; (None, key) for a plain key."""
    if not key.startswith(CANDIDATE_KEY_PREFIX):
        return None, key
    candidate, _, plain = key[len(CANDIDATE_KEY_PREFIX):].partition(CANDIDATE_KEY_SEPARATOR)
    return candidate, plain


def parse_job_key(key: str) -> tuple[SensorLevel, int, CaseSpec]:
    _, key = split_candidate(key)
    level_name, seed_tag, harness, index, inner = key.split("|", 4)
    return LEVELS[level_name], int(seed_tag[1:]), CaseSpec(harness, inner, int(index))


# --------------------------------------------------------------------------------------- jobs
class _Patches:
    """Set module attributes for one job and put the originals back afterwards."""

    def __init__(self) -> None:
        self._saved: list[tuple[object, str, object]] = []

    def set(self, module, name: str, value) -> None:
        self._saved.append((module, name, getattr(module, name)))
        setattr(module, name, value)

    def restore(self) -> None:
        for module, name, value in reversed(self._saved):
            setattr(module, name, value)
        self._saved.clear()


def _rebuild_controller(cl, c2, ctrl, level: SensorLevel):
    if not level.check_enabled:
        return ctrl
    rebuilt = c2.C2Controller.from_params(cl.PARAMS, level_config(ctrl.config, level))
    rebuilt.reset()
    return rebuilt


def _install_probe(patches: _Patches, cl, run: ActiveRun) -> ChunkProbe:
    hook = None
    if run.level.adds_rod_channel:
        hook = getattr(run.adapter.split_pressures, "step_chunk", None)
    probe = ChunkProbe(cl._lagged_step, round(cl.IMU_SAMPLE_S / cl.LAG_CHUNK_S), hook)
    patches.set(cl, "_lagged_step", probe)
    return probe


def _run_g6_family(case: CaseSpec, run: ActiveRun, patches: _Patches) -> tuple[dict, object]:
    """G6 / ref case through ``r72_g6_screen.job`` with the adapter patches."""
    import r72_g6_screen as g6
    import s9_soil_closed_loop as sl

    cl, c2, _ = sl._imports()
    run.probe = _install_probe(patches, cl, run)
    s9_period = g6._ORIG_CONTROL_PERIOD
    make_preset = g6.make_controller_preset

    def period(cl_, measurements, plant, cmd, valve, ha, period_s, rec, sens=None):
        ideal = s9_period(cl_, measurements, plant, cmd, valve, ha, period_s, rec, sens)
        return run.after_period(plant, ideal, ha)

    def make_controller(cl_, c2_, variant):
        ctrl = _rebuild_controller(cl_, c2_, make_preset(cl_, c2_, variant), run.level)
        g6._CAP["ctrl"] = ctrl
        run.ctrl = ctrl
        return ctrl

    patches.set(g6, "_ORIG_CONTROL_PERIOD", period)
    patches.set(g6, "make_controller_preset", make_controller)
    if run.level.check_enabled:
        patches.set(sl, "RUN_LIMIT_S", sl.RUN_LIMIT_S + CHECK_RUN_EXTENSION_S)
    inner = case.inner
    if case.harness == "ref":
        soil, pad, slope = case.inner.split("|")
        roll, pitch = (float(v) for v in slope.split(","))
        inner = f"ref|{soil}|top|Fs4"
        run_case = sl.run_case

        def run_case_with_extras(case_dict):
            return run_case({**case_dict, "pad": pad, "slope": (roll, pitch)})

        patches.set(sl, "run_case", run_case_with_extras)
    rec = g6.job(inner)
    return rec, g6._CAP.get("plant")


def _run_g8(case: CaseSpec, run: ActiveRun, patches: _Patches) -> tuple[dict, object]:
    """G8 case through ``r69_g8_screen.job`` with the adapter patches."""
    import r51_reapp_closed_loop as r51
    import r64_g4_closed_loop as r64
    import r67_g1_screen as r67
    import r69_g8_screen as g8

    cl, _, _ = r51._imports()
    run.probe = _install_probe(patches, cl, run)
    make_base = g8.make_base_g8

    def step_period(cl_, meas, plant, ctrl, cmd, valve, ha, floor_fn=None, rec=None):
        ideal = r64.with_two_pressures(plant, r51.control_period(
            cl_, meas, plant, cmd, valve, ha, ctrl.period_s, floor_fn, rec), ha)
        delivered = run.after_period(plant, ideal, ha)
        return np.array(ctrl.update(delivered).leg_speed_m_s)

    def make(cl_, c2_, level, fs_kN, floor, leg, gap_spec):
        plant, ctrl, info, node_d0 = make_base(cl_, c2_, level, fs_kN, floor, leg, gap_spec)
        ctrl = _rebuild_controller(cl_, c2_, ctrl, run.level)
        run.ctrl, run.plant = ctrl, plant
        return plant, ctrl, info, node_d0

    patches.set(r67, "step_period", step_period)
    patches.set(g8, "make_base_g8", make)
    if run.level.check_enabled:
        patches.set(r51, "BASE_LIMIT_S", r51.BASE_LIMIT_S + CHECK_RUN_EXTENSION_S)
    rec = g8.job(case.inner)
    return rec, run.plant


def _place_worker() -> None:
    import r51_reapp_closed_loop as r51

    r51.place_worker()


def run_job(key: str) -> dict:
    """One study run; the harness record is kept under ``base``, the truth summary under ``r79``."""
    global _ACTIVE
    candidate, _ = split_candidate(key)
    level, seed_index, case = parse_job_key(key)
    seed = case_seed(case.group, seed_index, case.index)
    rod_model = os.environ.get("R79_ROD_MODEL", DEFAULT_ROD_MODEL)
    out = {"key": key, "level": level.name, "seed_index": seed_index, "seed": seed,
           "harness": case.harness, "inner": case.inner, "case_index": case.index,
           "rod_model": rod_model, "candidate": candidate or "current"}
    t_wall = time.perf_counter()
    _place_worker()
    adapter = SensorAdapter(level, seed, rod_split_function(rod_model),
                            always_split=rod_model != "harness")
    run = ActiveRun(level, adapter)
    _ACTIVE = run
    patches = _Patches()
    restore_candidate = lambda: None  # noqa: E731
    try:
        restore_candidate = _install_r79_candidate(candidate)
        runner = _run_g8 if case.harness == "g8" else _run_g6_family
        base, plant = runner(case, run, patches)
    except Exception as exc:  # keep the batch going; the error is reported
        import traceback
        out.update(error=f"{type(exc).__name__}: {exc}", trace=traceback.format_exc()[-3000:])
        return out
    finally:
        patches.restore()
        restore_candidate()
        _ACTIVE = None
    out["base"] = base
    if "error" in base or run.ctrl is None or plant is None:
        out["error"] = base.get("error", "no controller / plant captured")
        return out
    out.update(_run_summary(run, plant))
    out["r79"]["recontact_events"] = recontact_summary(base)
    if candidate not in (None, "current"):  # spec 424.5: the candidate's own record
        controller = run.ctrl
        fix = getattr(controller, "fix", None)
        out["candidate_record"] = None if fix is None else _candidate_record(fix)
    out["wall_s"] = round(time.perf_counter() - t_wall, 1)
    return out


RECONTACT_EVENT_KEYS = ("t_start_s", "t_end_s", "duration_s", "max_normal_N", "max_over_W",
                        "ended_before_loc", "class")


def recontact_summary(base: dict) -> dict | None:
    """Spec 407.2 (2): U-S9-G6d recontact intervals of a G6 run (r72 ``crawler_recontact``, the
    run_S9 ``recontact_events`` on the 1 ms crawler force), kept without ``R79_TRACE``; None for
    a harness record without them (G8)."""
    record = base.get("crawler_recontact")
    if record is None:
        return None
    events = record["recontact_events"]
    return {"t_departure_confirmed_s": record["departure"].get("t_confirmed_s"),
            "pass": events["pass"], "flags": events["flags"],
            "events": [{key: event[key] for key in RECONTACT_EVENT_KEYS}
                       for event in events["events"]]}


def _run_summary(run: ActiveRun, plant) -> dict:
    ctrl = run.ctrl
    truth = run.truth.arrays()
    events = [(float(e.t_s), e.name) for e in ctrl.events]
    summary = summarise_run(truth, events, float(ctrl.geometry.F_min_N), float(plant.m * plant.g),
                            ctrl.geometry.twist_vector)
    soil = ctrl._soil_state()
    c_min = getattr(soil, "clearance_at_plateau_start_m", None)
    summary["c_min_tP_mm"] = None if c_min is None else round(float(c_min) * 1e3, 2)
    out = {"r79": summary, "zero_calibration": zero_calibration_outcome(ctrl.meta()),
           "sensors": run.adapter.suite.setup().config,
           "events": [(round(t, 2), n) for t, n in events
                      if not n.startswith(("INFO_PRESSURE", "shadow"))][:200]}
    rod_meta = getattr(run.adapter.split_pressures, "meta", None)
    if run.level.adds_rod_channel and callable(rod_meta):
        out["rod_model_meta"] = rod_meta()
    if os.environ.get("R79_TRACE") == "1":
        out["truth"] = {k: (v.tolist() if v.dtype != object else list(v))
                        for k, v in truth.items()}
    return out


# --------------------------------------------------------------------------------------- main
def set_parent_placement() -> None:
    mask = os.environ.get("R79_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def selected_jobs() -> list[str]:
    levels = os.environ.get("R79_LEVELS", "L1").split(",")
    seeds_env = os.environ.get("R79_SEEDS")
    seeds = None if not seeds_env else [int(s) for s in seeds_env.split(",")]
    jobs = job_keys(os.environ.get("R79_SET", "identity"), levels, seeds)
    filt = os.environ.get("R79_FILTER")
    if filt:
        jobs = [j for j in jobs if any(f in j for f in filt.split(","))]
    candidates = candidate_names()
    if candidates:
        jobs = [f"{CANDIDATE_KEY_PREFIX}{name}{CANDIDATE_KEY_SEPARATOR}{job}"
                for name in candidates for job in jobs]
    return jobs


def _candidate_record(fix) -> dict:
    """Spec 424.5: the wrapper counters of one candidate run (424.4.1 D1 / D2 / D3 included)."""
    import s9_slope_fix_candidates as fx

    return {"l1_revokes": fix.l1_revokes, "l2_confirms": fix.l2_confirms,
            "l2_rejects": fix.l2_rejects, "l4_reused": list(fix.l4_reused),
            "lw_clears": fix.lw_clears, **fx.qc_record(fix)}


def _install_r79_candidate(candidate: str | None):
    """Spec 424.5: swap ``c2.C2Controller`` for the wrapper candidate class (every harness
    builds through the module attribute); returns a function that puts the original back.
    None / "current": nothing is installed (the stored r79 path, bit for bit)."""
    if candidate is None or candidate == "current":
        return lambda: None
    import s9_slope_fix_candidates as fx

    c2, _ = fx._install_candidate(candidate, {})
    original = fx._RUNNING["original_class"]

    def restore() -> None:
        c2.C2Controller = original

    return restore


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    jobs = selected_jobs()
    if sys.argv[2] == "--list":
        print("\n".join(jobs))
        print(len(jobs), "jobs")
        return
    set_parent_placement()
    out_path = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        results = pool.map(run_job, jobs, chunksize=1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"script": "04_scripts/03_control/s8/r79_sensor_screen.py",
            "spec": "rev. 79 draft (study 2: sensor errors + P-S8-28 / 29 / 30)",
            "levels": os.environ.get("R79_LEVELS", "L1"), "set": os.environ.get("R79_SET",
                                                                                 "identity"),
            "seeds": os.environ.get("R79_SEEDS"), "filter": os.environ.get("R79_FILTER"),
            "candidates": candidate_names() or None,
            "affinity": os.environ.get("R79_AFFINITY"), "workers": workers,
            "rod_model": os.environ.get("R79_ROD_MODEL", DEFAULT_ROD_MODEL),
            "wall_s": round(time.perf_counter() - t0, 1), "n_jobs": len(jobs)}
    out_path.write_text(json.dumps({"meta": meta, "results": results}, indent=1, default=float),
                        encoding="utf-8")
    print("done", meta["wall_s"], "s ->", out_path)
    for r in results:
        if "error" in r:
            print(r["key"], "ERROR", r["error"])
            continue
        print(r["key"], "pass", r["base"].get("pass"), "zero_cal",
              r["zero_calibration"]["all_calibrated"], "ready",
              r["base"].get("t_ready_s", r["base"].get("t_ready")), "wall", r["wall_s"])


if __name__ == "__main__":
    main()
