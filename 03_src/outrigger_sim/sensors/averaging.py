"""Control-period average of the IMU truth (engine independent).

User decision 2026-10-20: the IMU input of :class:`outrigger_sim.sensors.imu.ImuModel` is the
true specific force and angular rate **averaged over the control period** (20 ms), as in the
reduced model (``04_scripts/01_dynamics/run_control_comparison.py`` sums the physics steps of
one period). The noise model ``sigma = density sqrt(1 / (2 T))`` is the noise of such a
``T``-long average, and the average suppresses content near and above the 50 Hz sample rate
(local vibration, aliasing) while passing the 1.8-3.9 Hz rocking almost unchanged (gain
about 0.99); the attitude low-pass removes the rocking. The runner feeds every physics step
here (connecting it is the runner's job, Chrono side).

Averaging rule: each step sample ``x_i`` at time ``t_i`` stands for the interval
``(t_{i-1}, t_i]`` (the value at the end of the step), and the average is weighted by the
interval lengths, so a period with mixed step sizes (``dt_transition_s`` windows) is still a
time average. A period ``(t_start, t_start + T]`` closes with the first sample at or after
its end (within ``1e-9 T`` for floating-point step sums); that sample belongs wholly to the
closing period, and the next period starts at its time. With steps that divide ``T``
(1e-4 and 1e-5 s into 20 ms) no step straddles a boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S

# Relative tolerance on the period end, for times built from repeated additions of dt.
_BOUNDARY_TOLERANCE = 1e-9
_AXIS_COUNT = 3


@dataclass(frozen=True, eq=False)
class PeriodAverage:
    """Time average of one control period (sensor axes); arrays are read-only.

    Attributes:
        t_s: End time of the period (the control sample time).
        specific_force_m_s2: Average true specific force, shape (3,).
        angular_rate_rad_s: Average true angular rate, shape (3,).
        sample_count: Number of step samples in the period.
    """

    t_s: float
    specific_force_m_s2: NDArray[np.float64]
    angular_rate_rad_s: NDArray[np.float64]
    sample_count: int


def _vector3(value: ArrayLike, name: str) -> NDArray[np.float64]:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (_AXIS_COUNT,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name}: expected 3 finite numbers, got {value!r}")
    return array


def _read_only(array: NDArray[np.float64]) -> NDArray[np.float64]:
    array.setflags(write=False)
    return array


class ControlPeriodAverager:
    """Collects step samples and returns the average when a control period ends.

    Args:
        period_s: Control period ``T`` (s).
        start_t_s: Start of the first period (s), normally the run start time.
    """

    def __init__(self, period_s: float = DEFAULT_CONTROL_PERIOD_S, start_t_s: float = 0.0) -> None:
        if not (math.isfinite(period_s) and period_s > 0.0):
            raise ValueError(f"period_s must be > 0, got {period_s!r}")
        self.period_s = float(period_s)
        self.reset(start_t_s)

    def reset(self, start_t_s: float) -> None:
        """Drop the collected samples and start the first period at ``start_t_s``."""
        self._period_start_s = float(start_t_s)
        self._last_t_s = float(start_t_s)
        self._force_integral = np.zeros(_AXIS_COUNT)
        self._rate_integral = np.zeros(_AXIS_COUNT)
        self._sample_count = 0

    @property
    def period_end_s(self) -> float:
        """End time of the period being collected."""
        return self._period_start_s + self.period_s

    def add(
        self, t_s: float, specific_force_m_s2: ArrayLike, angular_rate_rad_s: ArrayLike
    ) -> PeriodAverage | None:
        """Add the true values at the end of one physics step.

        Returns:
            The period average when this sample closes the period, else ``None``.

        Raises:
            ValueError: Time not after the previous sample, or bad vectors.
        """
        if not t_s > self._last_t_s:
            raise ValueError(f"t_s {t_s!r} is not after the previous sample {self._last_t_s!r}")
        force = _vector3(specific_force_m_s2, "specific_force_m_s2")
        rate = _vector3(angular_rate_rad_s, "angular_rate_rad_s")
        weight_s = t_s - self._last_t_s
        self._force_integral += weight_s * force
        self._rate_integral += weight_s * rate
        self._sample_count += 1
        self._last_t_s = float(t_s)
        if t_s < self.period_end_s - _BOUNDARY_TOLERANCE * self.period_s:
            return None
        return self._close_period()

    def _close_period(self) -> PeriodAverage:
        duration_s = self._last_t_s - self._period_start_s
        average = PeriodAverage(
            t_s=self._last_t_s,
            specific_force_m_s2=_read_only(self._force_integral / duration_s),
            angular_rate_rad_s=_read_only(self._rate_integral / duration_s),
            sample_count=self._sample_count,
        )
        self.reset(self._last_t_s)
        return average
