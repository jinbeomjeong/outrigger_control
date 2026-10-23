"""Static error model of the WIKA A-10 pressure transmitters (spec 71, E-1 / E-2, U70 / U72).

``00_docs/04_control/s6_control_spec.md`` sections 71 and 76.1; sensor data
``08_test_data/datasheets/WIKA_A-10_pressure_sensor_summary.md`` (0-400 bar, 4-20 mA,
standard accuracy class). Each of the eight sensors (4 legs x head / rod side) draws its error
terms once per run:

    p_meas = p + o + g p + A (x - x^2 - 1/6) / (1/6) + e_rep + n(t),    x = p / 400 bar

* ``o``: zero error + drift (+ the temperature zero error of the conservative / old-worst
  grades), a run constant; ``g``: span (gain) error; ``A``: amplitude of the BFSL-shaped
  parabola (zero mean over the span); ``e_rep``: non-repeatability, a run constant.
* The noise ``n(t)`` is not drawn here: :class:`~outrigger_sim.sensors.hydraulic.LegSensorModel`
  keeps its noise streams and scales them by ``pressure_noise_std_Pa``.
* The normal grade clips the non-temperature sum at the data-sheet maximum measuring error
  (+-4 bar); the other grades are not clipped.
* Output chain (E-2): the reading becomes a 4-20 mA current that saturates at the NAMUR NE 43
  measuring range (3.8 / 20.5 mA = -5 / 412.5 bar) and is read back with the 0.025 bar
  resolution of the measured chain.

Every bound here is a data-sheet value or an ASSUMPTION of spec 71; units Pa.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER

BAR_PA = 1e5
SENSOR_SPAN_PA = 400.0 * BAR_PA
"""Measuring range 0-400 bar (gauge)."""
CURRENT_ZERO_MA = 4.0
CURRENT_SPAN_MA = 16.0
SIGNAL_CURRENT_RANGE_MA = (3.8, 20.5)
"""NAMUR NE 43 measuring signal range; outside it the controller sees a fault (D1, U72)."""
CHAIN_RESOLUTION_PA = 0.025 * BAR_PA
"""Resolution of the measured chain (16,000 counts over 400 bar, single-sensor test)."""

SENSOR_SIDES = ("head", "rod")
ERROR_TERM_COUNT = 7
"""Unit uniforms drawn per sensor (fixed, whatever the grade, so every grade sees the same
draws): zero, drift, temperature zero, span, temperature span, nonlinearity, repeatability."""


class PressureErrorGrade(StrEnum):
    """Error grade of the pressure sensors (spec 71, U70)."""

    LEGACY = "legacy"
    """No static error; only the configured noise and resolution (the R6-P model)."""
    NORMAL = "normal"
    """Data-sheet standard class at the calibration temperature; simulation default (76.1)."""
    CONSERVATIVE = "conservative"
    """Normal plus the typical temperature error (+-4 bar zero, +-0.5 % span)."""
    OLD_WORST = "old_worst"
    """Normal plus the old data-sheet maximum temperature error (+-10 bar, +-1 % span)."""


@dataclass(frozen=True)
class PressureErrorBounds:
    """Half-widths of the uniform error terms of one grade (spec 71 table)."""

    zero_offset_Pa: float
    drift_offset_Pa: float
    temperature_offset_Pa: float
    span_gain: float
    """Relative span error (0.005 = 0.5 %)."""
    temperature_span_gain: float
    nonlinearity_Pa: float
    nonrepeatability_Pa: float
    nontemperature_clip_Pa: float | None
    """Clip of the non-temperature sum (normal grade: the +-4 bar maximum measuring error)."""
    noise_std_Pa: float
    """Noise of the grade (spec 71); used by :func:`wika_noise_std_Pa`, not drawn here."""


_NORMAL_BOUNDS = PressureErrorBounds(
    zero_offset_Pa=1.2 * BAR_PA,
    drift_offset_Pa=0.4 * BAR_PA,
    temperature_offset_Pa=0.0,
    span_gain=0.005,
    temperature_span_gain=0.0,
    nonlinearity_Pa=2.0 * BAR_PA,
    nonrepeatability_Pa=0.4 * BAR_PA,
    nontemperature_clip_Pa=4.0 * BAR_PA,
    noise_std_Pa=0.20 * BAR_PA,
)

PRESSURE_ERROR_BOUNDS: dict[PressureErrorGrade, PressureErrorBounds] = {
    PressureErrorGrade.LEGACY: PressureErrorBounds(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, 0.0),
    PressureErrorGrade.NORMAL: _NORMAL_BOUNDS,
    PressureErrorGrade.CONSERVATIVE: PressureErrorBounds(
        zero_offset_Pa=1.2 * BAR_PA,
        drift_offset_Pa=0.4 * BAR_PA,
        temperature_offset_Pa=4.0 * BAR_PA,
        span_gain=0.005,
        temperature_span_gain=0.005,
        nonlinearity_Pa=2.0 * BAR_PA,
        nonrepeatability_Pa=0.4 * BAR_PA,
        nontemperature_clip_Pa=None,
        noise_std_Pa=0.20 * BAR_PA,
    ),
    PressureErrorGrade.OLD_WORST: PressureErrorBounds(
        zero_offset_Pa=1.2 * BAR_PA,
        drift_offset_Pa=0.4 * BAR_PA,
        temperature_offset_Pa=10.0 * BAR_PA,
        span_gain=0.005,
        temperature_span_gain=0.010,
        nonlinearity_Pa=2.0 * BAR_PA,
        nonrepeatability_Pa=0.4 * BAR_PA,
        nontemperature_clip_Pa=None,
        noise_std_Pa=0.27 * BAR_PA,
    ),
}


def wika_noise_std_Pa(grade: PressureErrorGrade | str) -> float:
    """1-sigma noise of the grade (0.20 bar; old worst 0.27 bar = the 0.8 bar spec as 3 sigma)."""
    return PRESSURE_ERROR_BOUNDS[PressureErrorGrade(grade)].noise_std_Pa


@dataclass(frozen=True, eq=False)
class PressureErrorTerms:
    """Drawn error terms; every array has the same shape (one entry per sensor).

    ``offset_Pa`` = zero + drift + repeatability (non-temperature constants), ``gain`` and
    ``nonlinearity_Pa`` the other non-temperature terms; the temperature terms are separate
    because only the non-temperature sum is clipped.
    """

    offset_Pa: NDArray[np.float64]
    gain: NDArray[np.float64]
    nonlinearity_Pa: NDArray[np.float64]
    temperature_offset_Pa: NDArray[np.float64]
    temperature_gain: NDArray[np.float64]
    nontemperature_clip_Pa: float | None

    def error_Pa(self, pressure_Pa: ArrayLike) -> NDArray[np.float64]:
        """Static error at the true pressure ``pressure_Pa`` (broadcast with the terms)."""
        pressure = np.asarray(pressure_Pa, dtype=float)
        span_fraction = pressure / SENSOR_SPAN_PA
        parabola = (span_fraction - span_fraction**2 - 1.0 / 6.0) / (1.0 / 6.0)
        nontemperature = self.offset_Pa + self.gain * pressure + self.nonlinearity_Pa * parabola
        if self.nontemperature_clip_Pa is not None:
            clip = self.nontemperature_clip_Pa
            nontemperature = np.clip(nontemperature, -clip, clip)
        return nontemperature + self.temperature_offset_Pa + self.temperature_gain * pressure


def draw_unit_terms(rng: np.random.Generator, sensor_shape: tuple[int, ...]) -> NDArray:
    """Uniform draws in [-1, 1), shape ``sensor_shape + (ERROR_TERM_COUNT,)``."""
    return rng.uniform(-1.0, 1.0, (*sensor_shape, ERROR_TERM_COUNT))


def error_terms_from_unit(
    unit_terms: ArrayLike, grade: PressureErrorGrade | str
) -> PressureErrorTerms:
    """Scale unit draws (last axis = the 7 terms of :data:`ERROR_TERM_COUNT`) to a grade."""
    unit = np.asarray(unit_terms, dtype=float)
    bounds = PRESSURE_ERROR_BOUNDS[PressureErrorGrade(grade)]
    zero, drift, temperature_zero, span, temperature_span, nonlinearity, repeat = np.moveaxis(
        unit, -1, 0
    )
    return PressureErrorTerms(
        offset_Pa=(
            zero * bounds.zero_offset_Pa
            + drift * bounds.drift_offset_Pa
            + repeat * bounds.nonrepeatability_Pa
        ),
        gain=span * bounds.span_gain,
        nonlinearity_Pa=nonlinearity * bounds.nonlinearity_Pa,
        temperature_offset_Pa=temperature_zero * bounds.temperature_offset_Pa,
        temperature_gain=temperature_span * bounds.temperature_span_gain,
        nontemperature_clip_Pa=bounds.nontemperature_clip_Pa,
    )


def terms_to_meta(terms: PressureErrorTerms) -> dict[str, Any]:
    """Per-sensor terms of a (2, 4) draw (head / rod x LEG_ORDER) for the run meta."""
    meta: dict[str, Any] = {}
    for side_index, side in enumerate(SENSOR_SIDES):
        for leg_index, leg in enumerate(LEG_ORDER):
            meta[f"{side}:{leg}"] = {
                "offset_Pa": float(terms.offset_Pa[side_index, leg_index]),
                "gain": float(terms.gain[side_index, leg_index]),
                "nonlinearity_Pa": float(terms.nonlinearity_Pa[side_index, leg_index]),
                "temperature_offset_Pa": float(
                    terms.temperature_offset_Pa[side_index, leg_index]
                ),
                "temperature_gain": float(terms.temperature_gain[side_index, leg_index]),
            }
    return meta


def pressure_to_current_mA(pressure_Pa: ArrayLike) -> NDArray[np.float64]:
    """Transmitter current of a reading (4 mA at 0, 20 mA at 400 bar, not saturated)."""
    return CURRENT_ZERO_MA + CURRENT_SPAN_MA * np.asarray(pressure_Pa, dtype=float) / SENSOR_SPAN_PA


def current_to_pressure_Pa(current_mA: ArrayLike) -> NDArray[np.float64]:
    """Raw pressure read back from a current (inverse of :func:`pressure_to_current_mA`)."""
    current = np.asarray(current_mA, dtype=float)
    return (current - CURRENT_ZERO_MA) / CURRENT_SPAN_MA * SENSOR_SPAN_PA


def saturate_at_signal_range(
    pressure_Pa: NDArray[np.float64], current_range_mA: tuple[float, float]
) -> NDArray[np.float64]:
    """Reading after the transmitter output saturates at ``current_range_mA``."""
    low, high = (float(value) for value in current_to_pressure_Pa(current_range_mA))
    return np.clip(pressure_Pa, low, high)
