"""Synthetic episodes in the episode schema, for an end-to-end smoke run of the ML pipeline.

NOT a plant model and not training data: the controller is frozen in READY, the load
redistribution of a sinking pad is a fixed pattern and the seal friction is a rigid Coulomb
element on the reading (stuck until ``|f| = F_s``, spec 199). The numbers only have the right
sizes (front / rear loads, F_min, rod weights, friction 0-8 kN) so that every class occurs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import LEG_COUNT, NO_CALIBRATION_SUFFIX, Episode
from outrigger_sim.control.c2 import C2Config
from outrigger_sim.control.contact_replay import replay_meta_from_config

PERIOD_S = 0.1
F_MIN_N = 9414.59
ROD_WEIGHT_N = np.array([1047.2, 1047.2, 717.7, 717.7])
HEAD_AREA_M2 = np.array([0.013273, 0.013273, 0.0095033, 0.0095033])
ANNULUS_AREA_M2 = np.array([0.0037699, 0.0037699, 0.0031416, 0.0031416])
STATIC_LOAD_N = np.array([118.1e3, 118.1e3, 72.1e3, 72.1e3])
LEG_STIFFNESS_N_M = 4.77e6
"""Load lost per metre of pad sink (rod_side_pressure.md 5: S_ii)."""
OIL_STIFFNESS_N_M = 3.0e7
READING_NOISE_N = 300.0
PROBE_END_S = 17.0
READY_S = 17.1
LIFT_S = 5.0
EVENT_KINDS = ("hold", "slow_sink", "fast_sink", "drop")
LEVELS = ("top", "middle", "bottom")


@dataclass(frozen=True)
class SyntheticCase:
    base_id: str
    episode_id: str
    level: str
    seal_friction_N: NDArray[np.float64]
    event: str
    event_leg: int
    sink_m: float
    ramp_s: float
    floor_roll_deg: float
    seed: int


def _redistribution(leg: int) -> NDArray[np.float64]:
    """Load change pattern of a sinking pad: it and its diagonal lose, the others gain."""
    pattern = np.ones(LEG_COUNT)
    pattern[leg] = -1.0
    pattern[LEG_COUNT - 1 - leg] = -1.0
    return pattern


def _true_forces(case: SyntheticCase, t_s: NDArray[np.float64]) -> NDArray[np.float64]:
    rng = np.random.default_rng(case.seed)
    base = STATIC_LOAD_N * (1.0 + 0.05 * rng.standard_normal(LEG_COUNT))
    forces = np.repeat(base[None, :], t_s.size, axis=0)
    if case.event != "hold":
        start_s = READY_S + 5.0
        progress = np.clip((t_s - start_s) / case.ramp_s, 0.0, 1.0)
        drop = LEG_STIFFNESS_N_M * case.sink_m * progress
        forces = forces + drop[:, None] * _redistribution(case.event_leg)[None, :]
    rocking = 400.0 * np.sin(2 * np.pi * 1.9 * t_s)[:, None]
    return np.maximum(forces + rocking, -ROD_WEIGHT_N[None, :])


def _seal_readings(forces: NDArray[np.float64], friction_N: NDArray[np.float64]):
    """Oil force P = F - f with a rigid Coulomb element (stuck until |f| = F_s)."""
    oil = np.empty_like(forces)
    state = np.zeros(LEG_COUNT)
    for row in range(forces.shape[0]):
        if row:
            state = np.clip(state + forces[row] - forces[row - 1], -friction_N, friction_N)
        oil[row] = forces[row] - state
    return oil


def synthetic_episode(case: SyntheticCase, duration_s: float = 45.0) -> Episode:
    """One synthetic episode (module docstring)."""
    rng = np.random.default_rng(case.seed + 1)
    count = int(round(duration_s / PERIOD_S))
    t_s = (np.arange(count) + 1) * PERIOD_S
    fine_t = np.arange(1, count * 10 + 1) * (PERIOD_S / 10)
    fine_forces = _true_forces(case, fine_t)
    windows = fine_forces.reshape(count, 10, LEG_COUNT)
    true_force = windows[:, -1, :]
    oil = _seal_readings(true_force, case.seal_friction_N)
    reading = oil + READING_NOISE_N * rng.standard_normal(oil.shape)
    phase = np.where(t_s < 3.0, "touch", np.where(t_s < 15.0, "level", np.where(
        t_s < PROBE_END_S + 1e-9, "probe", "ready"))).astype("U16")
    band = np.where(t_s[:, None] <= PROBE_END_S + 1e-9, 13e3,
                    case.seal_friction_N.max() + 3e3) * np.ones((1, LEG_COUNT))
    motor = 0.25 + true_force / OIL_STIFFNESS_N_M
    probe_end_row = int(round(PROBE_END_S / PERIOD_S)) - 1
    after_probe = np.arange(count) >= probe_end_row
    probe_grounded = np.where(after_probe[:, None], 1.0, np.nan) * np.ones((1, LEG_COUNT))
    specific_force = np.array([0.0, 0.0, 9.81]) + 0.002 * rng.standard_normal((count, 3))
    arrays = {
        "t_s": t_s,
        "phase": phase,
        "head_pressure_Pa": (reading + 2e5 * ANNULUS_AREA_M2) / HEAD_AREA_M2,
        "rod_pressure_Pa": np.full((count, LEG_COUNT), 2e5),
        "net_force_N": reading,
        "lower_reading_N": reading,
        "seal_band_N": band,
        "motor_stroke_m": motor,
        "stroke_corrected_m": motor - reading / OIL_STIFFNESS_N_M,
        "command_m_s": np.zeros((count, LEG_COUNT)),
        "specific_force_m_s2": specific_force,
        "angular_rate_rad_s": 1e-4 * rng.standard_normal((count, 3)),
        "imu_specific_force_samples_m_s2": specific_force[:, None, :]
        + 0.01 * rng.standard_normal((count, 10, 3)),
        "is_lifted": t_s >= LIFT_S,
        "touched": np.repeat((t_s >= 3.0)[:, None], LEG_COUNT, axis=1),
        "probed_leg": np.where(phase == "probe", 0, -1),
        "ge2_lift_mark": np.zeros((count, LEG_COUNT), dtype=bool),
        "ge2_trigger_mark": np.zeros((count, LEG_COUNT), dtype=bool),
        "probe_round_end": np.arange(count) == probe_end_row,
        "probe_is_grounded": probe_grounded,
        "probe_load_estimate_N": np.where(after_probe[:, None], reading[probe_end_row], np.nan),
        "probe_stiffness_ratio": probe_grounded * 1.2,
        "probe_attitude_ratio": probe_grounded,
        "probe_age_s": np.where(after_probe[:, None], t_s[:, None] - PROBE_END_S, np.nan)
        * np.ones((1, LEG_COUNT)),
        "true_force_N": true_force,
        "true_force_min_N": windows.min(axis=1),
        "true_force_mean_N": windows.mean(axis=1),
    }
    meta = {
        "source": "synthetic (outrigger_sim.ml.synthetic)",
        "case_id": case.episode_id,
        "base_id": case.base_id,
        "episode_id": case.episode_id,
        "engine": "synthetic",
        "period_s": PERIOD_S,
        "F_min_N": F_MIN_N,
        "rod_weight_N": ROD_WEIGHT_N.tolist(),
        "zero_offset_N": [0.0] * LEG_COUNT,
        "seal_friction_N": case.seal_friction_N.tolist(),
        "initial_seal_state_N": [0.0] * LEG_COUNT,
        "level": case.level,
        "floor_roll_deg": case.floor_roll_deg,
        # Readings carry no sensor error and no zero offset, so there is nothing to calibrate.
        "sensor_grade": "ideal",
        "zero_calibration": False,
        "sensor_condition": f"ideal{NO_CALIBRATION_SUFFIX}",
        "event": {"kind": case.event, "leg": case.event_leg, "sink_m": case.sink_m,
                  "ramp_s": case.ramp_s},
        "seed": case.seed,
        "controller": replay_meta_from_config(C2Config().with_10hz_d1()),
        "reconstructed": [],
    }
    return Episode(arrays, meta)


def synthetic_cases(base_count: int, episodes_per_base: int, seed: int) -> list[SyntheticCase]:
    """Bases with random level, friction (rear 0.833 x front, 205.3 / U-S8-H1) and floor roll;
    episodes with random event kind, leg, sink depth and ramp."""
    rng = np.random.default_rng(seed)
    cases = []
    for base in range(base_count):
        front_N = float(rng.uniform(0.0, 8e3))
        friction = np.array([front_N, front_N, 0.833 * front_N, 0.833 * front_N])
        level = LEVELS[base % len(LEVELS)]
        roll = float(rng.uniform(-5.5, 5.5))
        for episode in range(episodes_per_base):
            kind = str(rng.choice(EVENT_KINDS, p=[0.2, 0.4, 0.2, 0.2]))
            ramp = {"hold": 1.0, "slow_sink": 20.0, "fast_sink": 2.0, "drop": 0.05}[kind]
            cases.append(SyntheticCase(
                base_id=f"SYN{base:02d}", episode_id=f"SYN{base:02d}_ep{episode}",
                level=level, seal_friction_N=friction, event=kind,
                event_leg=int(rng.integers(LEG_COUNT)), sink_m=float(rng.uniform(0.002, 0.030)),
                ramp_s=ramp, floor_roll_deg=roll, seed=int(rng.integers(1, 2**31 - 1)),
            ))
    return cases
