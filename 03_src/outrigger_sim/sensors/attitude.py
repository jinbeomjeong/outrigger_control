"""Attitude signal: tilt from the accelerometer and the 2nd-order low-pass (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` S6 (py) and CLAUDE.md '자세 신호 필터' (user decision
2026-10-20): **two identical first-order stages of tau 0.5 s** (about 0.32 Hz) at the control
period (20 ms). A single first-order stage leaves 0.023 deg of rocking ripple
(``00_docs/05_sensors/imu_cabin_and_accuracy_review.md`` 2.3, filter F2).

Discretisation, kept by user decision 2026-10-20 (2) because the expected values of the
closed-loop checks come from the reduced model that uses it (the gain near the corner differs
from the exact form by about 2 %); same as ``04_scripts/01_dynamics/run_control_comparison.py``
``Ctx.filt``. Every stage is

    y[k] = y[k-1] + a (x[k] - y[k-1]),   a = T / tau

i.e. Euler integration of ``tau dy/dt = x - y`` with the input of the current sample, a
discrete pole at ``z = 1 - a`` (0.96 for T 20 ms, tau 0.5 s; the exact zero-order-hold pole
``exp(-T / tau)`` would be 0.9608). All stages start at the first input, so there is no start
transient. ``a`` must lie in (0, 1] (no overshoot, stable).

Tilt: roll and pitch from the specific force with
:func:`outrigger_sim.frames.roll_pitch_from_specific_force` (exact, no small-angle
approximation; valid at rest, any acceleration of the sensor point reads as tilt). The angles,
not the specific force, are filtered, as in the reduced model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.frames import roll_pitch_from_specific_force
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S

ATTITUDE_FILTER_TIME_CONSTANT_S = 0.5
"""Per-stage time constant of the attitude low-pass (user decision 2026-10-20)."""
ATTITUDE_FILTER_STAGE_COUNT = 2
"""Number of first-order stages (2nd-order filter, user decision 2026-10-20)."""


class CascadedLowPass:
    """``stage_count`` identical first-order low-pass stages (discretisation: module docstring).

    Filters a scalar or an array; every element is an independent channel.

    Args:
        time_constant_s: Time constant ``tau`` of each stage (s).
        stage_count: Number of stages (>= 1).
        sample_period_s: Sample period ``T`` (s).

    Raises:
        ValueError: ``T / tau`` outside (0, 1] or ``stage_count`` < 1.
    """

    def __init__(
        self,
        time_constant_s: float = ATTITUDE_FILTER_TIME_CONSTANT_S,
        stage_count: int = ATTITUDE_FILTER_STAGE_COUNT,
        sample_period_s: float = DEFAULT_CONTROL_PERIOD_S,
    ) -> None:
        if stage_count < 1:
            raise ValueError(f"stage_count must be >= 1, got {stage_count}")
        gain = sample_period_s / time_constant_s
        if not (math.isfinite(gain) and 0.0 < gain <= 1.0):
            raise ValueError(f"sample_period_s / time_constant_s must be in (0, 1], got {gain!r}")
        self.time_constant_s = float(time_constant_s)
        self.stage_count = int(stage_count)
        self.sample_period_s = float(sample_period_s)
        self.gain = gain
        self._stages: list[NDArray[np.float64]] | None = None

    @property
    def pole(self) -> float:
        """Discrete pole of each stage, ``1 - T / tau``."""
        return 1.0 - self.gain

    def reset(self) -> None:
        """Forget the state; the next input initialises every stage again."""
        self._stages = None

    def update(self, value: ArrayLike) -> NDArray[np.float64]:
        """Filter one sample and return the output of the last stage (a new array)."""
        sample = np.array(value, dtype=np.float64, copy=True)
        if self._stages is None:
            self._stages = [sample.copy() for _ in range(self.stage_count)]
            return sample
        stage_input = sample
        for stage in self._stages:
            stage += self.gain * (stage_input - stage)
            stage_input = stage
        return stage_input.copy()


@dataclass(frozen=True)
class AttitudeEstimate:
    """Tilt from one accelerometer sample, raw and low-passed (rad)."""

    t_s: float
    roll_raw_rad: float
    pitch_raw_rad: float
    roll_rad: float
    pitch_rad: float


class AttitudeEstimator:
    """Roll and pitch from the specific force at rest, then the attitude low-pass.

    Args:
        low_pass: Filter for the (roll, pitch) pair; default = decided 2nd-order filter.
    """

    def __init__(self, low_pass: CascadedLowPass | None = None) -> None:
        self.low_pass = low_pass if low_pass is not None else CascadedLowPass()

    def reset(self) -> None:
        """Forget the filter state."""
        self.low_pass.reset()

    def update(self, t_s: float, specific_force_m_s2: ArrayLike) -> AttitudeEstimate:
        """Estimate the attitude from one sample (sensor = body axes)."""
        roll, pitch = roll_pitch_from_specific_force(specific_force_m_s2)
        filtered_roll, filtered_pitch = self.low_pass.update([roll, pitch])
        return AttitudeEstimate(
            t_s=float(t_s),
            roll_raw_rad=float(roll),
            pitch_raw_rad=float(pitch),
            roll_rad=float(filtered_roll),
            pitch_rad=float(filtered_pitch),
        )
