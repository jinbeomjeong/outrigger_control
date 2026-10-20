"""Cylinder pressure and stroke sensors, and the 350 bar locked-pressure indicator.

Engine independent part of ``00_docs/03_chrono/chrono_build_plan.md`` S6 (pressure and stroke
virtual sensors, 350 bar indicator / V17 path). The engine supplies the true head pressure
``p = F_cyl / A_head`` and the strokes; this module adds noise and resolution.

* Pressure: the sensor sits in the lock valve block and keeps reading the trapped pressure
  while locked (YAML ``sensors.cylinder_pressure.location``). Readings are not clipped at 0.
* Stroke: one sensor per cylinder. When the engine also gives the oil-compression corrected
  stroke (L1), both readouts get the **same** noise sample because they stand for one sensor.
* Noise defaults are zero (ideal). :func:`reduced_model_leg_sensor_config` gives the values of
  the reduced model (``04_scripts/01_dynamics/run_control_comparison.py``: pressure noise
  0.3 kN of cylinder force, stroke noise 0.1 mm), both assumptions; no resolution is known.
* 350 bar: CLAUDE.md '압력 한계' - locked state maximum 350 bar
  (YAML ``actuator.locked_pressure_limit_Pa``). :func:`locked_pressure_report` reports the
  maximum, the time and leg, and whether and when the limit was exceeded (plan V17).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.signals import LEG_COUNT

REDUCED_MODEL_PRESSURE_NOISE_FORCE_N = 300.0
"""ASSUMPTION (reduced model ``CA['pressure_noise_N']``): 1-sigma pressure noise as force."""
REDUCED_MODEL_STROKE_NOISE_M = 1e-4
"""ASSUMPTION (reduced model ``CA['stroke_noise_m']``): 1-sigma stroke noise."""

LOCKED_PRESSURE_LIMIT_KEY = "actuator.locked_pressure_limit_Pa"
BORE_DIAMETER_KEY = "actuator.bore_diameter_m"


def head_area_m2(bore_diameter_m: float) -> float:
    """Piston (head side) area ``pi / 4 d^2`` (m^2)."""
    return math.pi / 4.0 * bore_diameter_m**2


def head_area_from_params(params: Params) -> float:
    """Head area from YAML ``actuator.bore_diameter_m``."""
    return head_area_m2(float(params.get(BORE_DIAMETER_KEY)))


def locked_pressure_limit_from_params(params: Params) -> float:
    """Locked-state pressure limit (Pa), YAML ``actuator.locked_pressure_limit_Pa``."""
    return float(params.get(LOCKED_PRESSURE_LIMIT_KEY))


# --- virtual sensors -----------------------------------------------------------------------


@dataclass(frozen=True)
class LegSensorConfig:
    """Noise (1 sigma) and resolution of the per-leg pressure and stroke sensors; 0 = ideal."""

    pressure_noise_std_Pa: float = 0.0
    pressure_resolution_Pa: float = 0.0
    stroke_noise_std_m: float = 0.0
    stroke_resolution_m: float = 0.0

    def __post_init__(self) -> None:
        for name, value in self.to_meta().items():
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name}: expected a finite value >= 0, got {value!r}")

    def to_meta(self) -> dict[str, Any]:
        """JSON-ready settings for the run meta."""
        return {
            "pressure_noise_std_Pa": self.pressure_noise_std_Pa,
            "pressure_resolution_Pa": self.pressure_resolution_Pa,
            "stroke_noise_std_m": self.stroke_noise_std_m,
            "stroke_resolution_m": self.stroke_resolution_m,
        }


def reduced_model_leg_sensor_config(head_area: float) -> LegSensorConfig:
    """Noise levels of the reduced model (assumptions), pressure noise as ``0.3 kN / A_head``."""
    return LegSensorConfig(
        pressure_noise_std_Pa=REDUCED_MODEL_PRESSURE_NOISE_FORCE_N / head_area,
        stroke_noise_std_m=REDUCED_MODEL_STROKE_NOISE_M,
    )


@dataclass(frozen=True, eq=False)
class LegSensorReading:
    """Delivered pressure and stroke readings, shape (4,) each, LEG_ORDER."""

    head_pressure_Pa: NDArray[np.float64]
    stroke_m: NDArray[np.float64]
    stroke_corrected_m: NDArray[np.float64] | None


def _per_leg(values: ArrayLike, name: str) -> NDArray[np.float64]:
    array = np.array(values, dtype=np.float64, copy=True)
    if array.shape != (LEG_COUNT,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name}: expected {LEG_COUNT} finite values, got {values!r}")
    return array


def _quantize(values: NDArray[np.float64], resolution: float) -> NDArray[np.float64]:
    if resolution == 0.0:
        return values
    return np.round(values / resolution) * resolution


class LegSensorModel:
    """Pressure and stroke sensors of the four legs.

    Random numbers: 8 normal draws per sample (4 pressure, then 4 stroke), whatever the
    configured noise, so the sequence depends on the seed only.

    Args:
        config: Noise and resolution.
        seed: Noise seed (int or ``numpy.random.SeedSequence``); ``None`` = fresh entropy.
    """

    def __init__(
        self, config: LegSensorConfig, seed: int | np.random.SeedSequence | None = None
    ) -> None:
        self.config = config
        self._seed_sequence = (
            seed if isinstance(seed, np.random.SeedSequence) else np.random.SeedSequence(seed)
        )
        self._rng = np.random.default_rng(self._seed_sequence)

    def reset(self) -> None:
        """Restart the noise sequence from the seed."""
        self._rng = np.random.default_rng(self._seed_sequence)

    def measure(
        self,
        head_pressure_Pa: ArrayLike,
        stroke_m: ArrayLike,
        stroke_corrected_m: ArrayLike | None = None,
    ) -> LegSensorReading:
        """Delivered readings for the true head pressures and strokes."""
        config = self.config
        pressure_noise = self._rng.normal(0.0, 1.0, LEG_COUNT) * config.pressure_noise_std_Pa
        stroke_noise = self._rng.normal(0.0, 1.0, LEG_COUNT) * config.stroke_noise_std_m
        pressure = _per_leg(head_pressure_Pa, "head_pressure_Pa") + pressure_noise
        stroke = _per_leg(stroke_m, "stroke_m") + stroke_noise
        corrected = None
        if stroke_corrected_m is not None:
            corrected = _per_leg(stroke_corrected_m, "stroke_corrected_m") + stroke_noise
            corrected = _quantize(corrected, config.stroke_resolution_m)
        return LegSensorReading(
            head_pressure_Pa=_quantize(pressure, config.pressure_resolution_Pa),
            stroke_m=_quantize(stroke, config.stroke_resolution_m),
            stroke_corrected_m=corrected,
        )


# --- 350 bar indicator -------------------------------------------------------------------


@dataclass(frozen=True)
class LockedPressureReport:
    """Locked-pressure indicator over a run (plan V17 path); pressures in Pa, times in s.

    Attributes:
        limit_Pa: Limit compared against (exceeded when the pressure is strictly above it).
        max_pressure_Pa: Highest considered pressure over all legs.
        max_leg: LEG_ORDER index of that maximum.
        max_t_s: Time of that maximum (first occurrence).
        max_per_leg_Pa: Highest considered pressure of each leg (NaN if none considered).
        exceed_sample_count_per_leg: Considered samples above the limit, per leg.
        first_exceed_t_s: First time any leg is above the limit, ``None`` if never.
        first_exceed_leg: Leg of that first exceedance (lowest index if several).
    """

    limit_Pa: float
    max_pressure_Pa: float
    max_leg: int
    max_t_s: float
    max_per_leg_Pa: tuple[float, ...]
    exceed_sample_count_per_leg: tuple[int, ...]
    first_exceed_t_s: float | None
    first_exceed_leg: int | None

    @property
    def is_exceeded(self) -> bool:
        """Whether any considered sample is above the limit."""
        return self.first_exceed_t_s is not None

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready summary with leg names (NaN per-leg maxima become ``None``)."""
        first_leg = self.first_exceed_leg
        return {
            "limit_Pa": self.limit_Pa,
            "max_pressure_Pa": self.max_pressure_Pa,
            "max_leg": LEG_ORDER[self.max_leg],
            "max_t_s": self.max_t_s,
            "max_per_leg_Pa": {
                leg: (None if math.isnan(value) else value)
                for leg, value in zip(LEG_ORDER, self.max_per_leg_Pa, strict=True)
            },
            "exceed_sample_count_per_leg": dict(
                zip(LEG_ORDER, self.exceed_sample_count_per_leg, strict=True)
            ),
            "is_exceeded": self.is_exceeded,
            "first_exceed_t_s": self.first_exceed_t_s,
            "first_exceed_leg": None if first_leg is None else LEG_ORDER[first_leg],
        }


def locked_pressure_report(
    t_s: ArrayLike,
    head_pressure_Pa: ArrayLike,
    limit_Pa: float,
    *,
    is_locked: ArrayLike | None = None,
) -> LockedPressureReport:
    """Maximum head pressure and 350 bar exceedance over a run.

    Args:
        t_s: Sample times, shape (n,).
        head_pressure_Pa: Head pressure per sample and leg, shape (n, 4). True values
            (``F_cyl / A_head``) or sensor readings, as the caller decides.
        limit_Pa: Locked-state limit, normally :func:`locked_pressure_limit_from_params`.
        is_locked: Optional bool mask, shape (n, 4): only samples where the leg is locked
            (not moving) are considered, since the limit applies to the locked state.
            ``None`` considers every sample.

    Raises:
        ValueError: Wrong shapes, non-finite pressures, or no sample considered.
    """
    times = np.asarray(t_s, dtype=np.float64)
    pressures = np.asarray(head_pressure_Pa, dtype=np.float64)
    if times.ndim != 1 or pressures.shape != (times.size, LEG_COUNT):
        raise ValueError(
            f"expected t_s (n,) and head_pressure_Pa (n, {LEG_COUNT}), "
            f"got {times.shape} and {pressures.shape}"
        )
    if not np.all(np.isfinite(pressures)):
        raise ValueError("head_pressure_Pa contains NaN or infinity")
    considered = np.ones(pressures.shape, dtype=bool)
    if is_locked is not None:
        considered = np.asarray(is_locked, dtype=bool)
        if considered.shape != pressures.shape:
            raise ValueError(f"is_locked: expected shape {pressures.shape}, got {considered.shape}")
    if not considered.any():
        raise ValueError("no sample is considered (is_locked is all False or the run is empty)")

    masked = np.where(considered, pressures, -np.inf)
    sample_index, max_leg = np.unravel_index(int(np.argmax(masked)), masked.shape)
    max_per_leg = np.where(considered.any(axis=0), masked.max(axis=0), np.nan)
    is_above = masked > limit_Pa
    first_exceed_t_s = None
    first_exceed_leg = None
    if is_above.any():
        first_sample = int(np.argmax(is_above.any(axis=1)))
        first_exceed_t_s = float(times[first_sample])
        first_exceed_leg = int(np.argmax(is_above[first_sample]))
    return LockedPressureReport(
        limit_Pa=float(limit_Pa),
        max_pressure_Pa=float(masked[sample_index, max_leg]),
        max_leg=int(max_leg),
        max_t_s=float(times[sample_index]),
        max_per_leg_Pa=tuple(float(value) for value in max_per_leg),
        exceed_sample_count_per_leg=tuple(int(count) for count in is_above.sum(axis=0)),
        first_exceed_t_s=first_exceed_t_s,
        first_exceed_leg=first_exceed_leg,
    )
