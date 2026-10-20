"""IMU truth at the mounting point and IMU error model (engine independent, no pychrono).

``00_docs/03_chrono/chrono_build_plan.md`` S6 (py: IMU error model, sensor grades) and 3.3;
values from ``00_docs/05_sensors/imu_cabin_and_accuracy_review.md`` 4.1 and 10.

Mounting (CLAUDE.md 'IMU 장착 위치', user decision 2026-10-20): candidate **C1**, upper frame
under the cab, body point :data:`IMU_MOUNT_C1_BODY_M` = (0.31, 0.88, 0.040) m. Sensor axes
are the body axes (no misalignment); the mounting error is a separate 0.02 deg budget item
added at judgement time (plan S6 controller check 2), not part of this model.

Error pipeline of :meth:`ImuModel.measure` (one call per sample, default 20 ms):

1. true specific force and angular rate in sensor axes, **averaged over the control period**
   (user decision 2026-10-20 (1): :class:`outrigger_sim.sensors.averaging.ControlPeriodAverager`
   on every physics step, same as the reduced model the noise model and grades come from);
2. ``+ bias`` (constant vector);
3. ``+ white noise`` with ``sigma = density * sqrt(1 / (2 T))``, ``T`` = sample period. This
   is the noise of a ``T``-long average and matches the reduced model
   (``04_scripts/01_dynamics/run_control_comparison.py`` ``Sensors``), which feeds the
   specific force averaged over the control period;
4. quantisation to the resolution (0 = off);
5. ``- zero offset`` (software correction from the field zero calibration,
   :func:`field_zero_offset`);
6. delay by ``delay_samples`` whole samples.

Field zero (user decision 2026-10-20 (3)): a grade's zero error *is* the residual after the
mandatory field zero, so a run uses the grade bias as is and no calibration procedure is
simulated. :func:`field_zero_offset` stays as a tool for studies of the procedure only.

Random numbers: six normal draws per sample (accelerometer x, y, z, then gyro x, y, z) even
when a density is 0, so two models with the same seed see the same noise sequence whatever
their grade (common random numbers when comparing grades).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.frames import quat_conjugate, rotate_vector
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S

Vector3 = tuple[float, float, float]

STANDARD_GRAVITY_M_S2 = 9.80665

IMU_MOUNT_C1_BODY_M: Vector3 = (0.31, 0.88, 0.040)
"""Decided IMU point C1 (user decision 2026-10-20; ``00_docs/00_cad/cad_origin_mass_imu.md``
4): BASE DECK left pontoon, top face of the 15 mm cross plate, body axes (m)."""

MICRO_G_PER_G = 1e6
MILLI_G_PER_G = 1e3

# Noise draws per sample: accelerometer xyz then gyro xyz (see module docstring).
_AXIS_COUNT = 3


# --- truth at the mounting point ----------------------------------------------------------


def specific_force_at_point(
    body_quat_wxyz: ArrayLike,
    origin_accel_world_m_s2: ArrayLike,
    omega_world_rad_s: ArrayLike,
    alpha_world_rad_s2: ArrayLike,
    point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
) -> NDArray[np.float64]:
    """True specific force at a body point in body axes (rigid-body kinematics).

    ``f = R^T (a_P + g z_hat)`` with ``a_P = a_O + alpha x r + omega x (omega x r)`` and
    ``r = R p`` (world gravity ``-g z_hat``). About ``(0, 0, +g)`` for a level body at rest.

    Args:
        body_quat_wxyz: Body orientation, world <- body.
        origin_accel_world_m_s2: Acceleration of the body-frame origin, world axes.
        omega_world_rad_s: Body angular velocity, world axes.
        alpha_world_rad_s2: Body angular acceleration, world axes.
        point_body_m: Sensor point in body axes (m); default C1.
        gravity_m_s2: Magnitude of gravity.

    Returns:
        Specific force in body axes (m/s^2), shape (3,).
    """
    lever_world = rotate_vector(body_quat_wxyz, np.asarray(point_body_m, dtype=float))
    omega = np.asarray(omega_world_rad_s, dtype=float)
    point_accel = (
        np.asarray(origin_accel_world_m_s2, dtype=float)
        + np.cross(np.asarray(alpha_world_rad_s2, dtype=float), lever_world)
        + np.cross(omega, np.cross(omega, lever_world))
    )
    specific_force_world = point_accel + np.array([0.0, 0.0, gravity_m_s2])
    return rotate_vector(quat_conjugate(body_quat_wxyz), specific_force_world)


def angular_rate_in_body(body_quat_wxyz: ArrayLike, omega_world_rad_s: ArrayLike) -> NDArray:
    """Gyro truth: body angular velocity (world axes, as in ``TruthState``) in body axes."""
    return rotate_vector(quat_conjugate(body_quat_wxyz), omega_world_rad_s)


# --- sensor grades -----------------------------------------------------------------------


class ImuGradeName(StrEnum):
    """The five sensor grades of plan S6 (``imu_cabin_and_accuracy_review.md`` 4.1)."""

    IDEAL = "ideal"
    GOOD_ZEROED = "good_zeroed"
    NORMAL_ZEROED = "normal_zeroed"
    NORMAL_ZEROED_REPEATABILITY = "normal_zeroed_repeatability"
    NORMAL_AS_SHIPPED = "normal_as_shipped"


@dataclass(frozen=True)
class ImuGrade:
    """Accelerometer error level of one sensor grade.

    Attributes:
        name: Grade identifier.
        zero_error_deg: Residual zero (tilt) error per tilt axis, applied with the same sign
            on x and y (the reduced model's convention).
        noise_density_ug_rtHz: Accelerometer white-noise density (micro-g per root hertz).
        basis: Where the numbers come from.
    """

    name: ImuGradeName
    zero_error_deg: float
    noise_density_ug_rtHz: float
    basis: str

    @property
    def zero_error_mg(self) -> float:
        """Zero error as an accelerometer bias in milli-g (``sin(angle) x 1000``)."""
        return math.sin(math.radians(self.zero_error_deg)) * MILLI_G_PER_G


_GRADE_SOURCE = (
    "00_docs/05_sensors/imu_cabin_and_accuracy_review.md 4.1; same values as "
    "04_scripts/01_dynamics/run_imu_accuracy_review.py GRADES"
)

IMU_GRADES: MappingProxyType[ImuGradeName, ImuGrade] = MappingProxyType(
    {
        ImuGradeName.IDEAL: ImuGrade(
            ImuGradeName.IDEAL, 0.0, 15.0, f"baseline, no zero error; {_GRADE_SOURCE}"
        ),
        ImuGradeName.GOOD_ZEROED: ImuGrade(
            ImuGradeName.GOOD_ZEROED,
            0.046,
            15.0,
            f"excellent class after field zero (ifm JN2101 B 0.046 deg); {_GRADE_SOURCE}",
        ),
        ImuGradeName.NORMAL_ZEROED: ImuGrade(
            ImuGradeName.NORMAL_ZEROED,
            0.072,
            82.0,
            f"normal class after field zero (SICK TMM88D-MJI B 0.072 deg); {_GRADE_SOURCE}",
        ),
        ImuGradeName.NORMAL_ZEROED_REPEATABILITY: ImuGrade(
            ImuGradeName.NORMAL_ZEROED_REPEATABILITY,
            0.122,
            82.0,
            f"normal after field zero + power-on repeatability 0.05 deg (linear sum); "
            f"{_GRADE_SOURCE}",
        ),
        ImuGradeName.NORMAL_AS_SHIPPED: ImuGrade(
            ImuGradeName.NORMAL_AS_SHIPPED,
            0.17,
            82.0,
            f"normal class as shipped, no field zero (TMM88D-MJI A 0.17 deg); reference only, "
            f"the field zero is mandatory; {_GRADE_SOURCE}",
        ),
    }
)
"""Grade name -> values. Gyro errors are not graded (no source values; the controller C2
uses the accelerometer tilt only)."""


# --- error configuration -------------------------------------------------------------------


def _vector3(value: ArrayLike, name: str) -> Vector3:
    array = np.asarray(value, dtype=float)
    if array.shape != (_AXIS_COUNT,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name}: expected 3 finite numbers, got {value!r}")
    return (float(array[0]), float(array[1]), float(array[2]))


def _non_negative(value: float, name: str) -> float:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name}: expected a finite value >= 0, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class ImuErrorConfig:
    """Error parameters of one IMU; all SI, sensor (= body) axes.

    Attributes:
        accel_bias_m_s2: Constant accelerometer bias.
        accel_noise_density_m_s2_rtHz: Accelerometer white-noise density.
        accel_resolution_m_s2: Accelerometer quantisation step, 0 = no quantisation.
        gyro_bias_rad_s: Constant gyro bias.
        gyro_noise_density_rad_s_rtHz: Gyro white-noise density.
        gyro_resolution_rad_s: Gyro quantisation step, 0 = no quantisation.
        zero_offset_m_s2: Field zero correction subtracted from the accelerometer reading
            (:func:`field_zero_offset`).
        delay_samples: Output delay in whole samples.
        sample_period_s: Sample period ``T`` (default = control period 20 ms).
        grade: Grade name the values came from, or ``None`` for custom values (meta only).
    """

    accel_bias_m_s2: Vector3 = (0.0, 0.0, 0.0)
    accel_noise_density_m_s2_rtHz: float = 0.0
    accel_resolution_m_s2: float = 0.0
    gyro_bias_rad_s: Vector3 = (0.0, 0.0, 0.0)
    gyro_noise_density_rad_s_rtHz: float = 0.0
    gyro_resolution_rad_s: float = 0.0
    zero_offset_m_s2: Vector3 = (0.0, 0.0, 0.0)
    delay_samples: int = 0
    sample_period_s: float = DEFAULT_CONTROL_PERIOD_S
    grade: str | None = None

    def __post_init__(self) -> None:
        for name in ("accel_bias_m_s2", "gyro_bias_rad_s", "zero_offset_m_s2"):
            object.__setattr__(self, name, _vector3(getattr(self, name), name))
        for name in (
            "accel_noise_density_m_s2_rtHz",
            "accel_resolution_m_s2",
            "gyro_noise_density_rad_s_rtHz",
            "gyro_resolution_rad_s",
        ):
            object.__setattr__(self, name, _non_negative(getattr(self, name), name))
        if isinstance(self.delay_samples, bool) or not isinstance(self.delay_samples, int):
            raise ValueError(f"delay_samples: expected an int, got {self.delay_samples!r}")
        if self.delay_samples < 0:
            raise ValueError(f"delay_samples: expected >= 0, got {self.delay_samples}")
        if not math.isfinite(self.sample_period_s) or self.sample_period_s <= 0.0:
            raise ValueError(f"sample_period_s: expected > 0, got {self.sample_period_s!r}")

    @property
    def accel_noise_std_m_s2(self) -> float:
        """Standard deviation of one accelerometer sample, ``density sqrt(1 / (2 T))``."""
        return self.accel_noise_density_m_s2_rtHz * math.sqrt(1.0 / (2.0 * self.sample_period_s))

    @property
    def gyro_noise_std_rad_s(self) -> float:
        """Standard deviation of one gyro sample, ``density sqrt(1 / (2 T))``."""
        return self.gyro_noise_density_rad_s_rtHz * math.sqrt(1.0 / (2.0 * self.sample_period_s))

    def to_meta(self) -> dict[str, Any]:
        """JSON-ready settings for the run meta (``record.SensorSetup.config``)."""
        return {
            "grade": self.grade,
            "accel_bias_m_s2": list(self.accel_bias_m_s2),
            "accel_noise_density_m_s2_rtHz": self.accel_noise_density_m_s2_rtHz,
            "accel_resolution_m_s2": self.accel_resolution_m_s2,
            "gyro_bias_rad_s": list(self.gyro_bias_rad_s),
            "gyro_noise_density_rad_s_rtHz": self.gyro_noise_density_rad_s_rtHz,
            "gyro_resolution_rad_s": self.gyro_resolution_rad_s,
            "zero_offset_m_s2": list(self.zero_offset_m_s2),
            "delay_samples": self.delay_samples,
            "sample_period_s": self.sample_period_s,
        }


def imu_config_for_grade(
    grade_name: ImuGradeName | str,
    *,
    delay_samples: int = 0,
    sample_period_s: float = DEFAULT_CONTROL_PERIOD_S,
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
) -> ImuErrorConfig:
    """Error configuration of a plan S6 sensor grade.

    The zero error becomes an accelerometer bias of ``sin(angle) g`` on x and y with the same
    (positive) sign and none on z, exactly as in the reduced model. A positive y bias reads as
    positive roll, a positive x bias as negative (nose-up) pitch. Gyro errors are zero.
    Quantisation is off (no source value).
    """
    grade = IMU_GRADES[ImuGradeName(grade_name)]
    bias_m_s2 = grade.zero_error_mg / MILLI_G_PER_G * gravity_m_s2
    noise_density = grade.noise_density_ug_rtHz / MICRO_G_PER_G * gravity_m_s2
    return ImuErrorConfig(
        accel_bias_m_s2=(bias_m_s2, bias_m_s2, 0.0),
        accel_noise_density_m_s2_rtHz=noise_density,
        delay_samples=delay_samples,
        sample_period_s=sample_period_s,
        grade=grade.name.value,
    )


def field_zero_offset(
    mean_specific_force_m_s2: ArrayLike,
    *,
    reference_roll_rad: float = 0.0,
    reference_pitch_rad: float = 0.0,
    current_offset_m_s2: ArrayLike = (0.0, 0.0, 0.0),
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
) -> NDArray[np.float64]:
    """Zero offset from a field zero calibration at rest (mandatory procedure, CLAUDE.md).

    The machine stands still at an attitude known from a reference instrument; the mean of
    the delivered readings is compared with the specific force that attitude should give,
    ``g (-sin pitch, sin roll cos pitch, cos roll cos pitch)``.

    The grade values of :data:`IMU_GRADES` marked "after field zero" are already the
    residual errors *after* this procedure (temperature drift, repeatability), so do not
    calibrate a grade configuration again in simulation; this function models the procedure
    itself (for example a raw bias with an imperfect reference attitude).

    Args:
        mean_specific_force_m_s2: Mean delivered accelerometer reading at rest.
        reference_roll_rad: Roll of the reference attitude.
        reference_pitch_rad: Pitch of the reference attitude.
        current_offset_m_s2: Offset already applied to the readings that were averaged.
        gravity_m_s2: Magnitude of gravity.

    Returns:
        Total offset to put in :attr:`ImuErrorConfig.zero_offset_m_s2`.
    """
    expected = gravity_m_s2 * np.array(
        [
            -math.sin(reference_pitch_rad),
            math.sin(reference_roll_rad) * math.cos(reference_pitch_rad),
            math.cos(reference_roll_rad) * math.cos(reference_pitch_rad),
        ]
    )
    mean = np.asarray(_vector3(mean_specific_force_m_s2, "mean_specific_force_m_s2"))
    current = np.asarray(_vector3(current_offset_m_s2, "current_offset_m_s2"))
    return current + mean - expected


# --- model -------------------------------------------------------------------------------


@dataclass(frozen=True, eq=False)
class ImuReading:
    """One IMU output sample (sensor axes); arrays are read-only copies."""

    t_s: float
    specific_force_m_s2: NDArray[np.float64]
    angular_rate_rad_s: NDArray[np.float64]


def _quantize(values: NDArray[np.float64], resolution: float) -> NDArray[np.float64]:
    if resolution == 0.0:
        return values
    return np.round(values / resolution) * resolution


def _read_only_copy(values: NDArray[np.float64]) -> NDArray[np.float64]:
    copied = np.array(values, dtype=np.float64, copy=True)
    copied.setflags(write=False)
    return copied


@dataclass
class _DelayLine:
    """Fixed delay in samples; before it fills, the first sample stands for the past."""

    delay_samples: int
    _samples: deque[tuple[NDArray[np.float64], NDArray[np.float64]]] = field(default_factory=deque)

    def push(
        self, sample: tuple[NDArray[np.float64], NDArray[np.float64]]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        if not self._samples:
            # The sensor ran before the first sample; assume it saw the same value.
            self._samples.extend([sample] * self.delay_samples)
        self._samples.append(sample)
        return self._samples.popleft()

    def clear(self) -> None:
        self._samples.clear()


class ImuModel:
    """IMU error model: true specific force and angular rate -> delivered readings.

    Args:
        config: Error parameters.
        seed: Noise seed (int or ``numpy.random.SeedSequence``); ``None`` draws fresh
            entropy, which :attr:`seed_entropy` exposes so the run can still be repeated.
    """

    def __init__(
        self, config: ImuErrorConfig, seed: int | np.random.SeedSequence | None = None
    ) -> None:
        self.config = config
        self._seed_sequence = (
            seed if isinstance(seed, np.random.SeedSequence) else np.random.SeedSequence(seed)
        )
        self._rng = np.random.default_rng(self._seed_sequence)
        self._delay_line = _DelayLine(config.delay_samples)

    @property
    def seed_entropy(self) -> int | tuple[int, ...] | None:
        """Entropy of the noise seed; ``ImuModel(config, seed_entropy)`` repeats the noise.

        For a spawned ``SeedSequence`` the spawn key is needed as well; keep the parent seed.
        """
        return self._seed_sequence.entropy  # type: ignore[return-value]

    def reset(self) -> None:
        """Restart the noise sequence from the seed and empty the delay line."""
        self._rng = np.random.default_rng(self._seed_sequence)
        self._delay_line.clear()

    def measure(
        self, t_s: float, specific_force_m_s2: ArrayLike, angular_rate_rad_s: ArrayLike
    ) -> ImuReading:
        """Delivered reading at ``t_s`` for the given true values (module pipeline 1-6).

        Args:
            t_s: Sample time (s); the delayed output carries this time stamp.
            specific_force_m_s2: True specific force at the sensor, sensor axes. Pass the
                average over the sample period to match the noise model.
            angular_rate_rad_s: True angular rate, sensor axes.
        """
        config = self.config
        accel_noise = self._rng.normal(0.0, 1.0, _AXIS_COUNT) * config.accel_noise_std_m_s2
        gyro_noise = self._rng.normal(0.0, 1.0, _AXIS_COUNT) * config.gyro_noise_std_rad_s
        accel = np.asarray(_vector3(specific_force_m_s2, "specific_force_m_s2"))
        rate = np.asarray(_vector3(angular_rate_rad_s, "angular_rate_rad_s"))
        accel = _quantize(
            accel + config.accel_bias_m_s2 + accel_noise, config.accel_resolution_m_s2
        )
        rate = _quantize(rate + config.gyro_bias_rad_s + gyro_noise, config.gyro_resolution_rad_s)
        accel = accel - config.zero_offset_m_s2
        delayed_accel, delayed_rate = self._delay_line.push((accel, rate))
        return ImuReading(
            t_s=float(t_s),
            specific_force_m_s2=_read_only_copy(delayed_accel),
            angular_rate_rad_s=_read_only_copy(delayed_rate),
        )
