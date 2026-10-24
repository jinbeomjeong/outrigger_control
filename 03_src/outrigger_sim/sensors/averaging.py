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

IMU-rate samples (R8, ``s6_control_spec.md`` 148 R-1): with ``sample_period_s`` (e.g. 10 ms
in a 100 ms control period) the averager also closes sub-periods of that length with the same
rule (step-length weighted box average, a sample at or after the sub-period end closes it) and
the period average carries them, oldest first, the last one ending at the period end. The
period mean itself is computed exactly as without sub-periods (bit-identical). Without
``sample_period_s`` (or when it equals the period) nothing changes.
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
        sample_t_s: End times of the IMU-rate sub-periods, shape (n,), or None.
        sample_specific_force_m_s2: Sub-period mean specific force, shape (n, 3), or None.
        sample_angular_rate_rad_s: Sub-period mean angular rate, shape (n, 3), or None.
    """

    t_s: float
    specific_force_m_s2: NDArray[np.float64]
    angular_rate_rad_s: NDArray[np.float64]
    sample_count: int
    sample_t_s: NDArray[np.float64] | None = None
    sample_specific_force_m_s2: NDArray[np.float64] | None = None
    sample_angular_rate_rad_s: NDArray[np.float64] | None = None


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
        sample_period_s: IMU-rate sub-period (module docstring); None or equal to the period =
            no sub-periods. The period must be an integer multiple of it.
    """

    def __init__(
        self,
        period_s: float = DEFAULT_CONTROL_PERIOD_S,
        start_t_s: float = 0.0,
        sample_period_s: float | None = None,
    ) -> None:
        if not (math.isfinite(period_s) and period_s > 0.0):
            raise ValueError(f"period_s must be > 0, got {period_s!r}")
        self.period_s = float(period_s)
        self.samples_per_period = 1
        self.sample_period_s: float | None = None
        if sample_period_s is not None:
            if not (math.isfinite(sample_period_s) and sample_period_s > 0.0):
                raise ValueError(f"sample_period_s must be > 0, got {sample_period_s!r}")
            ratio = self.period_s / float(sample_period_s)
            n = round(ratio)
            if n < 1 or abs(ratio - n) > _BOUNDARY_TOLERANCE * ratio:
                raise ValueError(
                    f"period {period_s!r} s is not a multiple of the sample period "
                    f"{sample_period_s!r} s"
                )
            if n > 1:
                self.samples_per_period = n
                self.sample_period_s = float(sample_period_s)
        self.reset(start_t_s)

    def reset(self, start_t_s: float) -> None:
        """Drop the collected samples and start the first period at ``start_t_s``."""
        self._period_start_s = float(start_t_s)
        self._last_t_s = float(start_t_s)
        self._force_integral = np.zeros(_AXIS_COUNT)
        self._rate_integral = np.zeros(_AXIS_COUNT)
        self._sample_count = 0
        self._reset_sub(float(start_t_s))
        self._sub_t: list[float] = []
        self._sub_force: list[NDArray[np.float64]] = []
        self._sub_rate: list[NDArray[np.float64]] = []

    def _reset_sub(self, start_t_s: float) -> None:
        self._sub_start_s = start_t_s
        self._sub_force_integral = np.zeros(_AXIS_COUNT)
        self._sub_rate_integral = np.zeros(_AXIS_COUNT)

    def _sub_end_s(self) -> float:
        """End of the sub-period being collected, on the grid of the period start."""
        assert self.sample_period_s is not None
        return self._period_start_s + (len(self._sub_t) + 1) * self.sample_period_s

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
        closes_period = not t_s < self.period_end_s - _BOUNDARY_TOLERANCE * self.period_s
        if self.sample_period_s is not None:
            self._sub_force_integral += weight_s * force
            self._sub_rate_integral += weight_s * rate
            sub_end = self._sub_end_s()
            if closes_period or not t_s < sub_end - _BOUNDARY_TOLERANCE * self.sample_period_s:
                sub_duration = self._last_t_s - self._sub_start_s
                self._sub_t.append(self._last_t_s)
                self._sub_force.append(self._sub_force_integral / sub_duration)
                self._sub_rate.append(self._sub_rate_integral / sub_duration)
                self._reset_sub(self._last_t_s)
        if not closes_period:
            return None
        return self._close_period()

    def _close_period(self) -> PeriodAverage:
        duration_s = self._last_t_s - self._period_start_s
        samples: dict[str, NDArray[np.float64]] = {}
        if self.sample_period_s is not None:
            if len(self._sub_t) != self.samples_per_period:
                raise ValueError(
                    f"period ending at {self._last_t_s!r} s has {len(self._sub_t)} IMU samples, "
                    f"expected {self.samples_per_period} (steps must divide the sample period)"
                )
            samples = {
                "sample_t_s": _read_only(np.array(self._sub_t, dtype=np.float64)),
                "sample_specific_force_m_s2": _read_only(np.array(self._sub_force)),
                "sample_angular_rate_rad_s": _read_only(np.array(self._sub_rate)),
            }
        average = PeriodAverage(
            t_s=self._last_t_s,
            specific_force_m_s2=_read_only(self._force_integral / duration_s),
            angular_rate_rad_s=_read_only(self._rate_integral / duration_s),
            sample_count=self._sample_count,
            **samples,
        )
        self.reset(self._last_t_s)
        return average
