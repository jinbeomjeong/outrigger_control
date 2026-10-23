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
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER, Params, ParamsError
from outrigger_sim.sensors.pressure_error import (
    CHAIN_RESOLUTION_PA,
    SENSOR_SIDES,
    SIGNAL_CURRENT_RANGE_MA,
    PressureErrorGrade,
    PressureErrorTerms,
    draw_unit_terms,
    error_terms_from_unit,
    saturate_at_signal_range,
    terms_to_meta,
    wika_noise_std_Pa,
)
from outrigger_sim.signals import LEG_COUNT, Measurements

DEFAULT_PRESSURE_ERROR_GRADE = PressureErrorGrade.NORMAL
"""U70 / 76.1: the simulation default grade (:func:`wika_a10_leg_sensor_config`)."""
NONLINEARITY_SHAPE = "bfsl_parabola"
HEAD_SIDE = 0
ROD_SIDE = 1

REDUCED_MODEL_PRESSURE_NOISE_FORCE_N = 300.0
"""ASSUMPTION (reduced model ``CA['pressure_noise_N']``): 1-sigma pressure noise as force."""
REDUCED_MODEL_STROKE_NOISE_M = 1e-4
"""ASSUMPTION (reduced model ``CA['stroke_noise_m']``): 1-sigma stroke noise."""

LOCKED_PRESSURE_LIMIT_KEY = "actuator.locked_pressure_limit_Pa"
BORE_DIAMETER_KEY = "actuator.bore_diameter_m"
ANNULUS_AREA_KEY = "actuator.annulus_area_m2"
LEG_HEAD_AREA_KEY = "legs.{leg}.cylinder.head_area_m2"
LEG_ANNULUS_AREA_KEY = "legs.{leg}.cylinder.annulus_area_m2"
LEG_BORE_DIAMETER_KEY = "legs.{leg}.cylinder.bore_diameter_m"
LEG_ROD_DIAMETER_KEY = "legs.{leg}.cylinder.rod_diameter_m"
"""P-15 (spec 61.3, 64.2): per-leg cylinder keys of the regenerated YAML (dynamics 5.11.10
order 2, ``legs.<leg>.cylinder.*``): an area key wins over the diameters. Without them every
leg takes the common ``actuator.*`` values (bit for bit the R5 areas), so the controller stays
consistent with the engine that synthesises ``p_h = F / A_p`` from the same YAML."""

REXOME35_HEAD_AREA_M2 = (1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3)
REXOME35_ANNULUS_AREA_M2 = (3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3)
"""Spec 64.2 per-leg areas of the REXOME35 drawing (front ø130/ø110, rear ø110/ø90), for the
runs whose YAML / engine already use them (``dataclasses.replace`` of ``C2Geometry``)."""

PRESSURE_SENSOR_NOISE_STD_PA = 0.3e5
"""P-16 (spec 61.3, rod_side_pressure.md 7.3): 1-sigma noise of one pressure sensor, given as
a pressure (0.3 bar, ASSUMPTION until the sensor data sheet, Q-R1)."""


def head_area_m2(bore_diameter_m: float) -> float:
    """Piston (head side) area ``pi / 4 d^2`` (m^2)."""
    return math.pi / 4.0 * bore_diameter_m**2


def head_area_from_params(params: Params) -> float:
    """Head area from YAML ``actuator.bore_diameter_m``."""
    return head_area_m2(float(params.get(BORE_DIAMETER_KEY)))


def _optional(params: Params, key: str) -> float | None:
    try:
        return float(params.get(key))
    except ParamsError:
        return None


def leg_head_areas_from_params(params: Params) -> NDArray[np.float64]:
    """Head area per leg (4,), LEG_ORDER: ``legs.<leg>.cylinder.*`` or the common bore."""
    common = head_area_from_params(params)
    areas = []
    for leg in LEG_ORDER:
        area = _optional(params, LEG_HEAD_AREA_KEY.format(leg=leg))
        bore = _optional(params, LEG_BORE_DIAMETER_KEY.format(leg=leg))
        if area is None:
            area = common if bore is None else head_area_m2(bore)
        areas.append(area)
    return np.array(areas)


def leg_annulus_areas_from_params(params: Params) -> NDArray[np.float64]:
    """Annulus (rod side) area per leg (4,): ``pi / 4 (bore^2 - rod^2)`` from the per-leg
    diameters when both are given, else the common ``actuator.annulus_area_m2``."""
    common = float(params.get(ANNULUS_AREA_KEY))
    areas = []
    for leg in LEG_ORDER:
        area = _optional(params, LEG_ANNULUS_AREA_KEY.format(leg=leg))
        bore = _optional(params, LEG_BORE_DIAMETER_KEY.format(leg=leg))
        rod = _optional(params, LEG_ROD_DIAMETER_KEY.format(leg=leg))
        if area is not None:
            areas.append(area)
        elif bore is None or rod is None:
            areas.append(common)
        else:
            areas.append(math.pi / 4.0 * (bore**2 - rod**2))
    return np.array(areas)


def locked_pressure_limit_from_params(params: Params) -> float:
    """Locked-state pressure limit (Pa), YAML ``actuator.locked_pressure_limit_Pa``."""
    return float(params.get(LOCKED_PRESSURE_LIMIT_KEY))


# --- virtual sensors -----------------------------------------------------------------------


ZERO_PER_LEG = (0.0,) * LEG_COUNT


def _four_floats(value: float | ArrayLike, name: str) -> tuple[float, ...]:
    values = np.broadcast_to(np.asarray(value, dtype=float), (LEG_COUNT,))
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name}: expected finite values, got {value!r}")
    return tuple(float(item) for item in values)


@dataclass(frozen=True)
class LegSensorConfig:
    """Noise (1 sigma) and resolution of the per-leg pressure and stroke sensors; 0 = ideal.

    ``pressure_noise_std_Pa`` is one value for every leg or four values (LEG_ORDER, P-16: a
    noise defined as a force differs per leg once the head areas differ). The rod-side
    fields act only when the engine gives a rod-side pressure.

    Static pressure errors (spec 71, E-1 / E-2) are off by default (``legacy`` grade, no
    current chain, no offsets), which is the R6-P sensor bit for bit;
    :func:`wika_a10_leg_sensor_config` gives the simulation default (normal grade).
    """

    pressure_noise_std_Pa: float | tuple[float, ...] = 0.0
    pressure_resolution_Pa: float = 0.0
    stroke_noise_std_m: float = 0.0
    stroke_resolution_m: float = 0.0
    rod_pressure_noise_std_Pa: float = 0.0
    rod_pressure_resolution_Pa: float = 0.0
    pressure_error_grade: PressureErrorGrade = PressureErrorGrade.LEGACY
    """E-1: grade of the per-run static error terms of the eight pressure sensors."""
    current_range_mA: tuple[float, float] | None = None
    """E-2: the readings go through the 4-20 mA chain and saturate at this current range
    (NAMUR 3.8 / 20.5 mA); ``None`` = no current chain."""
    head_offset_Pa: tuple[float, ...] = ZERO_PER_LEG
    """Deterministic extra zero offset per head sensor (worst-sign cases PS-4 / PS-7, tests)."""
    rod_offset_Pa: tuple[float, ...] = ZERO_PER_LEG
    head_zero_drift_Pa_per_s: tuple[float, ...] = ZERO_PER_LEG
    """Linear zero drift per head sensor from ``zero_drift_start_s`` (temperature case PS-5)."""
    zero_drift_start_s: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.pressure_noise_std_Pa, list | tuple | np.ndarray):
            values = tuple(float(value) for value in self.pressure_noise_std_Pa)
            if len(values) != LEG_COUNT:
                raise ValueError(f"pressure_noise_std_Pa: expected 1 or {LEG_COUNT} values")
            object.__setattr__(self, "pressure_noise_std_Pa", values)
        for name, value in self._noise_meta().items():
            for item in value if isinstance(value, list) else [value]:
                if not math.isfinite(item) or item < 0.0:
                    raise ValueError(f"{name}: expected finite values >= 0, got {value!r}")
        object.__setattr__(
            self, "pressure_error_grade", PressureErrorGrade(self.pressure_error_grade)
        )
        for name in ("head_offset_Pa", "rod_offset_Pa", "head_zero_drift_Pa_per_s"):
            object.__setattr__(self, name, _four_floats(getattr(self, name), name))
        if self.current_range_mA is not None:
            low, high = (float(value) for value in self.current_range_mA)
            if not low < high:
                raise ValueError(f"current_range_mA: expected (low, high), got {low, high}")
            object.__setattr__(self, "current_range_mA", (low, high))

    @property
    def has_static_error(self) -> bool:
        """Whether any E-1 / E-2 term acts (``False`` = the R6-P sensor)."""
        return (
            self.pressure_error_grade is not PressureErrorGrade.LEGACY
            or self.current_range_mA is not None
            or any(self.head_offset_Pa)
            or any(self.rod_offset_Pa)
            or any(self.head_zero_drift_Pa_per_s)
        )

    def _noise_meta(self) -> dict[str, Any]:
        noise = self.pressure_noise_std_Pa
        return {
            "pressure_noise_std_Pa": list(noise) if isinstance(noise, tuple) else noise,
            "pressure_resolution_Pa": self.pressure_resolution_Pa,
            "stroke_noise_std_m": self.stroke_noise_std_m,
            "stroke_resolution_m": self.stroke_resolution_m,
            "rod_pressure_noise_std_Pa": self.rod_pressure_noise_std_Pa,
            "rod_pressure_resolution_Pa": self.rod_pressure_resolution_Pa,
        }

    def to_meta(self) -> dict[str, Any]:
        """JSON-ready settings for the run meta (the R6-P keys only while no static error
        acts, so the meta of a legacy run is unchanged)."""
        meta = self._noise_meta()
        if not self.has_static_error:
            return meta
        return {
            **meta,
            "pressure_error_grade": str(self.pressure_error_grade),
            "nonlinearity_shape": NONLINEARITY_SHAPE,
            "current_range_mA": (
                None if self.current_range_mA is None else list(self.current_range_mA)
            ),
            "head_offset_Pa": list(self.head_offset_Pa),
            "rod_offset_Pa": list(self.rod_offset_Pa),
            "head_zero_drift_Pa_per_s": list(self.head_zero_drift_Pa_per_s),
            "zero_drift_start_s": self.zero_drift_start_s,
        }

    @property
    def pressure_noise_per_leg_Pa(self) -> NDArray[np.float64] | float:
        noise = self.pressure_noise_std_Pa
        return np.array(noise) if isinstance(noise, tuple) else noise


def reduced_model_leg_sensor_config(head_area: float | ArrayLike) -> LegSensorConfig:
    """Noise levels of the reduced model (assumptions), pressure noise as ``0.3 kN / A_head``.

    ``head_area``: one area (R5) or four per-leg areas; equal areas give the scalar R5 setting
    bit for bit, different ones a per-leg noise (P-15 / P-16).
    """
    areas = np.atleast_1d(np.asarray(head_area, dtype=float))
    if areas.size == 1 or np.all(areas == areas[0]):
        noise: float | tuple[float, ...] = REDUCED_MODEL_PRESSURE_NOISE_FORCE_N / float(areas[0])
    else:
        noise = tuple(float(REDUCED_MODEL_PRESSURE_NOISE_FORCE_N / area) for area in areas)
    return LegSensorConfig(
        pressure_noise_std_Pa=noise, stroke_noise_std_m=REDUCED_MODEL_STROKE_NOISE_M
    )


def pressure_spec_leg_sensor_config(
    pressure_noise_std_Pa: float = PRESSURE_SENSOR_NOISE_STD_PA,
    rod_pressure_noise_std_Pa: float = PRESSURE_SENSOR_NOISE_STD_PA,
    stroke_noise_std_m: float = REDUCED_MODEL_STROKE_NOISE_M,
) -> LegSensorConfig:
    """P-16: sensors specified as pressures (0.3 bar head and rod side, ASSUMPTION); the
    force noise then follows each leg's area."""
    return LegSensorConfig(
        pressure_noise_std_Pa=pressure_noise_std_Pa,
        stroke_noise_std_m=stroke_noise_std_m,
        rod_pressure_noise_std_Pa=rod_pressure_noise_std_Pa,
    )


def wika_a10_leg_sensor_config(
    grade: PressureErrorGrade | str = DEFAULT_PRESSURE_ERROR_GRADE,
    stroke_noise_std_m: float = REDUCED_MODEL_STROKE_NOISE_M,
    **overrides: Any,
) -> LegSensorConfig:
    """E-1 / E-2 (spec 71, 76.1): WIKA A-10 head and rod sensors of the given grade.

    Grade noise on both sides (0.20 bar, old worst 0.27 bar), the 0.025 bar chain resolution
    and the 3.8-20.5 mA current range; ``legacy`` keeps the 0.3 bar noise-only model of
    :func:`pressure_spec_leg_sensor_config`. ``overrides`` replace single fields (offsets,
    drift).
    """
    grade = PressureErrorGrade(grade)
    if grade is PressureErrorGrade.LEGACY:
        return replace(pressure_spec_leg_sensor_config(stroke_noise_std_m=stroke_noise_std_m),
                       **overrides)
    noise = wika_noise_std_Pa(grade)
    config = LegSensorConfig(
        pressure_noise_std_Pa=noise,
        pressure_resolution_Pa=CHAIN_RESOLUTION_PA,
        stroke_noise_std_m=stroke_noise_std_m,
        rod_pressure_noise_std_Pa=noise,
        rod_pressure_resolution_Pa=CHAIN_RESOLUTION_PA,
        pressure_error_grade=grade,
        current_range_mA=SIGNAL_CURRENT_RANGE_MA,
    )
    return replace(config, **overrides)


@dataclass(frozen=True, eq=False)
class LegSensorReading:
    """Delivered pressure and stroke readings, shape (4,) each, LEG_ORDER."""

    head_pressure_Pa: NDArray[np.float64]
    stroke_m: NDArray[np.float64]
    stroke_corrected_m: NDArray[np.float64] | None
    rod_pressure_Pa: NDArray[np.float64] | None = None


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
    configured noise, so the sequence depends on the seed only. The rod-side noise (P-7) comes
    from a separate child stream (``SeedSequence.spawn``), so the head and stroke sequences
    stay those of R5 bit for bit whether or not a rod-side pressure is measured. The static
    error terms of the eight pressure sensors (E-1) come from a second child, drawn once at
    construction (7 uniforms per sensor whatever the grade), so they leave both noise
    streams unchanged and the same seed gives the same terms.

    Args:
        config: Noise, resolution and static errors.
        seed: Noise seed (int or ``numpy.random.SeedSequence``); ``None`` = fresh entropy.
    """

    def __init__(
        self, config: LegSensorConfig, seed: int | np.random.SeedSequence | None = None
    ) -> None:
        self.config = config
        self._seed_sequence = (
            seed if isinstance(seed, np.random.SeedSequence) else np.random.SeedSequence(seed)
        )
        # The spawn key of the child differs from the parent's, so the parent stream is the
        # same as before the rod-side sensor existed.
        (self._rod_seed_sequence,) = self._seed_sequence.spawn(1)
        (error_seed_sequence,) = self._seed_sequence.spawn(1)
        unit_terms = draw_unit_terms(
            np.random.default_rng(error_seed_sequence), (len(SENSOR_SIDES), LEG_COUNT)
        )
        self.error_terms: PressureErrorTerms = error_terms_from_unit(
            unit_terms, config.pressure_error_grade
        )
        """Static terms, shape (2, 4): head / rod side x LEG_ORDER."""
        self.reset()

    def reset(self) -> None:
        """Restart the noise sequences from the seed (the static error terms stay)."""
        self._rng = np.random.default_rng(self._seed_sequence)
        self._rod_rng = np.random.default_rng(self._rod_seed_sequence)

    def error_meta(self) -> dict[str, Any] | None:
        """Drawn static terms per sensor for the run meta (``None`` for the R6-P sensor)."""
        if not self.config.has_static_error:
            return None
        return terms_to_meta(self.error_terms)

    def measure(
        self,
        head_pressure_Pa: ArrayLike,
        stroke_m: ArrayLike,
        stroke_corrected_m: ArrayLike | None = None,
        rod_pressure_Pa: ArrayLike | None = None,
        t_s: float = 0.0,
    ) -> LegSensorReading:
        """Delivered readings for the true head (and rod-side) pressures and strokes.

        ``t_s`` only drives the optional linear zero drift.
        """
        config = self.config
        pressure_noise = self._rng.normal(0.0, 1.0, LEG_COUNT) * config.pressure_noise_per_leg_Pa
        stroke_noise = self._rng.normal(0.0, 1.0, LEG_COUNT) * config.stroke_noise_std_m
        true_head = _per_leg(head_pressure_Pa, "head_pressure_Pa")
        pressure = true_head + pressure_noise
        if config.has_static_error:
            pressure = self._with_static_error(pressure, true_head, HEAD_SIDE, t_s)
        stroke = _per_leg(stroke_m, "stroke_m") + stroke_noise
        corrected = None
        if stroke_corrected_m is not None:
            corrected = _per_leg(stroke_corrected_m, "stroke_corrected_m") + stroke_noise
            corrected = _quantize(corrected, config.stroke_resolution_m)
        rod = None
        if rod_pressure_Pa is not None:
            rod_noise = self._rod_rng.normal(0.0, 1.0, LEG_COUNT) * config.rod_pressure_noise_std_Pa
            true_rod = _per_leg(rod_pressure_Pa, "rod_pressure_Pa")
            rod = true_rod + rod_noise
            if config.has_static_error:
                rod = self._with_static_error(rod, true_rod, ROD_SIDE, t_s)
            rod = _quantize(rod, config.rod_pressure_resolution_Pa)
        return LegSensorReading(
            head_pressure_Pa=_quantize(pressure, config.pressure_resolution_Pa),
            stroke_m=_quantize(stroke, config.stroke_resolution_m),
            stroke_corrected_m=corrected,
            rod_pressure_Pa=rod,
        )

    def _with_static_error(
        self,
        noisy_Pa: NDArray[np.float64],
        true_Pa: NDArray[np.float64],
        side: int,
        t_s: float,
    ) -> NDArray[np.float64]:
        """E-1 terms, the extra offset and drift, then the E-2 current saturation."""
        config = self.config
        terms = self.error_terms
        side_terms = PressureErrorTerms(
            offset_Pa=terms.offset_Pa[side],
            gain=terms.gain[side],
            nonlinearity_Pa=terms.nonlinearity_Pa[side],
            temperature_offset_Pa=terms.temperature_offset_Pa[side],
            temperature_gain=terms.temperature_gain[side],
            nontemperature_clip_Pa=terms.nontemperature_clip_Pa,
        )
        reading = noisy_Pa + side_terms.error_Pa(true_Pa)
        if side == HEAD_SIDE:
            drift_time_s = max(0.0, t_s - config.zero_drift_start_s)
            reading = reading + np.array(config.head_offset_Pa)
            reading = reading + np.array(config.head_zero_drift_Pa_per_s) * drift_time_s
        else:
            reading = reading + np.array(config.rod_offset_Pa)
        if config.current_range_mA is not None:
            reading = saturate_at_signal_range(reading, config.current_range_mA)
        return reading


class RodSensorFault(StrEnum):
    """Rod-side sensor faults injected by :class:`FaultyRodSensor` (P-4 / P-7 tests)."""

    STUCK = "stuck"
    """The reading freezes at ``value_Pa``."""
    OFFSET = "offset"
    """``value_Pa`` is added to the reading."""
    DROPOUT = "dropout"
    """The reading is NaN."""


@dataclass(frozen=True)
class FaultyRodSensor:
    """Test wrapper: a rod-side fault on one leg from ``t_start_s`` on.

    Apply it to the delivered :class:`~outrigger_sim.signals.Measurements` (``apply``); the
    other legs and every other field pass unchanged.
    """

    leg: int
    fault: RodSensorFault
    value_Pa: float = 0.0
    t_start_s: float = 0.0

    def apply(self, measurements: Measurements) -> Measurements:
        rod = measurements.rod_pressure_Pa
        if rod is None or measurements.t_s < self.t_start_s:
            return measurements
        faulty = np.array(rod, dtype=float)
        if self.fault is RodSensorFault.STUCK:
            faulty[self.leg] = self.value_Pa
        elif self.fault is RodSensorFault.OFFSET:
            faulty[self.leg] += self.value_Pa
        else:
            faulty[self.leg] = math.nan
        return replace(measurements, rod_pressure_Pa=faulty)


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


def two_sided_locked_pressure_report(
    t_s: ArrayLike,
    head_pressure_Pa: ArrayLike,
    limit_Pa: float,
    *,
    rod_pressure_Pa: ArrayLike | None = None,
    rod_limit_Pa: float | None = None,
    is_locked: ArrayLike | None = None,
) -> dict[str, LockedPressureReport | None]:
    """Head and rod-side locked-pressure reports (P-13, U46: the rod side has no relief).

    ``rod_limit_Pa`` defaults to ``limit_Pa`` (ASSUMPTION 350 bar, manufacturer to confirm).
    Rows with a NaN rod reading (dropout) are left out of the rod report.

    Returns:
        ``{"head": report, "rod": report or None}`` (no rod-side pressure given -> ``None``).
    """
    head = locked_pressure_report(t_s, head_pressure_Pa, limit_Pa, is_locked=is_locked)
    if rod_pressure_Pa is None:
        return {"head": head, "rod": None}
    rod = np.asarray(rod_pressure_Pa, dtype=np.float64)
    considered = np.isfinite(rod)
    if is_locked is not None:
        considered &= np.asarray(is_locked, dtype=bool)
    rod_report = locked_pressure_report(
        t_s,
        np.where(considered, rod, 0.0),
        limit_Pa if rod_limit_Pa is None else rod_limit_Pa,
        is_locked=considered,
    )
    return {"head": head, "rod": rod_report}
