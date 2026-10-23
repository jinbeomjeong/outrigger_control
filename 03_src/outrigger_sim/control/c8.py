"""C8 levelling controller (alternative, two-phase, extend-only): skeleton on the C2 boundary.

``00_docs/04_control/control_candidates_comparison.md`` 7.2 (alternative 1) and the reduced
model ``04_scripts/01_dynamics/run_control_comparison.py`` class ``C8``. The sequence is

    TOUCH -> ATTITUDE -> LIFT -> REGROUND -> TRIM -> DONE -> READY,

* ATTITUDE: highest-leg reference, every lower leg extends in proportion to its height deficit
  (synchronised, same arrival time) until the slow-filtered tilt is within 0.05 deg,
* LIFT: all legs at ``v_max`` until the stroke-based crawler clearance reaches its target,
* REGROUND: a leg whose load estimate is below ``1.5 F_min`` extends at 0.2 ``v_max``,
* TRIM: highest-leg reference at 0.25 ``v_max`` (with a 0.02 deg dead band) plus re-grounding,
  DONE after 1 s inside 0.03 deg with every leg loaded; READY re-trims on a 0.07 deg trigger.

This is a skeleton: it follows the same :class:`~outrigger_sim.control.protocol.Controller`
contract as C2 (``Measurements`` in, ``Command`` out, 20 ms) so the runner can swap the two,
and reuses C2's geometry, filters and output ramp. Not yet in it (SPEC POINT, control-expert):
the R1 touch confirmation, the combined contact judge with the probe (the comparison requires
it for C8: pressure-only re-grounding misses lifted legs under seal friction, 5.3), the target
acceptance of ``control/target.py`` (C8 levels to level only), the stroke-end fault of C2 (the
legs are only clipped at the stroke ends) and a tuned gain set; the values are the
reduced-model assumptions (``CA`` there) and have not been re-verified in this package.

Units SI (m, rad, N, s); per-leg arrays follow ``LEG_ORDER`` (FL, FR, RL, RR).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.control.c2 import C2Geometry, scale_to_speed_limit
from outrigger_sim.params import Params
from outrigger_sim.sensors.attitude import AttitudeEstimator, CascadedLowPass
from outrigger_sim.sensors.rod_side import ForceEstimate, cylinder_force_from_pressures
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S, LEG_COUNT, Command, Measurements

C8_CONTROLLER_NAME = "C8"
DESIGN_SOURCE = "00_docs/04_control/control_candidates_comparison.md 7.2 (skeleton)"

# The highest-leg reference ignores height deficits below this (reduced model value).
MIN_HEIGHT_DEFICIT_M = 2e-4


class C8Phase(StrEnum):
    """Controller phase."""

    TOUCH = "touch"
    ATTITUDE = "attitude"
    LIFT = "lift"
    REGROUND = "reground"
    TRIM = "trim"
    DONE = "done"
    READY = "ready"


@dataclass(frozen=True)
class C8Settings:
    """Reduced-model assumptions of C8 (``run_control_comparison.CA``), not re-tuned."""

    touch_load_factor: float = 1.5
    reground_load_factor: float = 1.5
    """A leg below ``factor x F_min`` is re-grounded."""
    reground_speed_fraction: float = 0.2
    fine_gain_1_s: float = 0.5
    """Proportional gain on the height deficit (m/s per m)."""
    trim_speed_fraction: float = 0.25
    attitude_phase_done_rad: float = math.radians(0.05)
    trim_deadband_rad: float = math.radians(0.02)
    done_attitude_rad: float = math.radians(0.03)
    done_hold_s: float = 1.0
    relevel_attitude_rad: float = math.radians(0.07)
    clearance_target_m: float = 0.05
    stroke_end_clip_margin_m: float = 1e-4
    completion_time_constant_s: float = 1.0
    output_ramp_time_s: float | None = 0.1
    period_s: float = DEFAULT_CONTROL_PERIOD_S
    load_estimate: ForceEstimate = ForceEstimate.HEAD_ONLY
    """R6-P P-8 (option): ``two_sensor`` reads the net force when a rod-side pressure is
    measured; the default keeps the C8 head-only reading."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "load_estimate", ForceEstimate(self.load_estimate))
        if not self.period_s > 0.0:
            raise ValueError(f"period_s must be > 0, got {self.period_s!r}")


class C8Controller:
    """C8 skeleton (module docstring).

    Args:
        geometry: Machine quantities (:meth:`C2Geometry.from_params`).
        settings: Thresholds and gains; ``None`` = reduced-model values.
    """

    def __init__(self, geometry: C2Geometry, settings: C8Settings | None = None) -> None:
        self.geometry = geometry
        self.settings = settings if settings is not None else C8Settings()
        period_s = self.settings.period_s
        self._attitude = AttitudeEstimator(CascadedLowPass(sample_period_s=period_s))
        self._completion_filter = CascadedLowPass(
            self.settings.completion_time_constant_s, 1, period_s
        )
        self.reset()

    @classmethod
    def from_params(cls, params: Params, settings: C8Settings | None = None) -> C8Controller:
        """Controller for the machine described by ``params``."""
        return cls(C2Geometry.from_params(params), settings)

    # --- Controller protocol ---

    @property
    def period_s(self) -> float:
        """Control period (s)."""
        return self.settings.period_s

    def reset(self) -> None:
        """Clear filters, phase and bookkeeping."""
        self._attitude.reset()
        self._completion_filter.reset()
        self.phase = C8Phase.TOUCH
        self._touched = np.zeros(LEG_COUNT, dtype=bool)
        self._roll_rad = self._pitch_rad = 0.0
        self._slow_roll_rad = self._slow_pitch_rad = 0.0
        self._complete_since_s: float | None = None
        self._previous_output = np.zeros(LEG_COUNT)

    def update(self, measurements: Measurements) -> Command:
        """Leg speed command for the next period."""
        force, _ = cylinder_force_from_pressures(
            measurements.head_pressure_Pa,
            measurements.rod_pressure_Pa,
            self.geometry.head_area_m2,
            self.geometry.annulus_area_m2,
            self.settings.load_estimate,
        )
        rod_stroke = self._rod_stroke(measurements, force)
        self._update_filters(measurements)
        leg_speeds = self._phase_command(measurements.t_s, force, rod_stroke)
        leg_speeds = self._clip_at_stroke_ends(np.asarray(measurements.stroke_m), leg_speeds)
        return Command(t_s=measurements.t_s, leg_speed_m_s=self._apply_output_ramp(leg_speeds))

    def meta(self) -> dict[str, Any]:
        """Name and settings (JSON-serialisable, new dict per call)."""
        return {
            "controller": C8_CONTROLLER_NAME,
            "design": DESIGN_SOURCE,
            "is_skeleton": True,
            "period_s": self.settings.period_s,
            "settings": {
                **asdict(self.settings), "load_estimate": str(self.settings.load_estimate)
            },
        }

    # --- signals ---

    def _rod_stroke(self, measurements: Measurements, force_N: NDArray[np.float64]) -> NDArray:
        if measurements.stroke_corrected_m is not None:
            return np.array(measurements.stroke_corrected_m)
        motor = np.array(measurements.stroke_m)
        return motor - force_N / self.geometry.oil_stiffness_N_m(motor)

    def _update_filters(self, measurements: Measurements) -> None:
        estimate = self._attitude.update(measurements.t_s, measurements.specific_force_m_s2)
        self._roll_rad, self._pitch_rad = estimate.roll_rad, estimate.pitch_rad
        slow = self._completion_filter.update([estimate.roll_rad, estimate.pitch_rad])
        self._slow_roll_rad, self._slow_pitch_rad = float(slow[0]), float(slow[1])

    def _is_attitude_within(self, limit_rad: float) -> bool:
        return abs(self._slow_roll_rad) < limit_rad and abs(self._slow_pitch_rad) < limit_rad

    def _leg_heights_m(self) -> NDArray[np.float64]:
        """Pad heights of the tilted body relative to level: ``phi y - theta x``."""
        pad_xy = self.geometry.pad_xy_m
        return self._roll_rad * pad_xy[:, 1] - self._pitch_rad * pad_xy[:, 0]

    def _height_deficits_m(self) -> NDArray[np.float64]:
        """Extension that brings each leg up to the highest one."""
        heights = self._leg_heights_m()
        return heights.max() - heights

    # --- phases ---

    def _phase_command(
        self, t_s: float, force_N: NDArray[np.float64], rod_stroke_m: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        if self.phase is C8Phase.TOUCH:
            return self._touch(force_N)
        if self.phase in (C8Phase.DONE, C8Phase.READY):
            if not self._is_attitude_within(self.settings.relevel_attitude_rad):
                self.phase = C8Phase.TRIM
                self._complete_since_s = None
            else:
                self.phase = C8Phase.READY
                return np.zeros(LEG_COUNT)
        if self.phase is C8Phase.ATTITUDE:
            return self._attitude_phase()
        if self.phase is C8Phase.LIFT:
            return self._lift(rod_stroke_m)
        if self.phase is C8Phase.REGROUND:
            return self._reground_phase(force_N)
        return self._trim(t_s, force_N)

    def _touch(self, force_N: NDArray[np.float64]) -> NDArray[np.float64]:
        """Pressure-only touchdown (no R1 hold yet, SPEC POINT)."""
        touch_level = self.settings.touch_load_factor * self.geometry.F_min_N
        self._touched |= force_N >= touch_level
        if self._touched.all():
            self.phase = C8Phase.ATTITUDE
        return np.where(self._touched, 0.0, self.geometry.max_speed_m_s)

    def _attitude_phase(self) -> NDArray[np.float64]:
        settings = self.settings
        if self._is_attitude_within(settings.attitude_phase_done_rad):
            self.phase = C8Phase.LIFT
        leg_speeds = settings.fine_gain_1_s * self._height_deficits_m()
        return scale_to_speed_limit(leg_speeds, self.geometry.max_speed_m_s)

    def _lift(self, rod_stroke_m: NDArray[np.float64]) -> NDArray[np.float64]:
        clearance = self.geometry.clearance_estimate_m(rod_stroke_m)
        if clearance >= self.settings.clearance_target_m:
            self.phase = C8Phase.REGROUND
            return np.zeros(LEG_COUNT)
        return np.full(LEG_COUNT, self.geometry.max_speed_m_s)

    def _reground_speeds(self, force_N: NDArray[np.float64]) -> NDArray[np.float64]:
        settings = self.settings
        is_light = force_N < settings.reground_load_factor * self.geometry.F_min_N
        speed = settings.reground_speed_fraction * self.geometry.max_speed_m_s
        return np.where(is_light, speed, 0.0)

    def _reground_phase(self, force_N: NDArray[np.float64]) -> NDArray[np.float64]:
        leg_speeds = self._reground_speeds(force_N)
        if not leg_speeds.any():
            self.phase = C8Phase.TRIM
        return leg_speeds

    def _trim(self, t_s: float, force_N: NDArray[np.float64]) -> NDArray[np.float64]:
        settings = self.settings
        trim_speeds = np.zeros(LEG_COUNT)
        if not self._is_attitude_within(settings.trim_deadband_rad):
            deficits = self._height_deficits_m()
            trim_speed_limit = settings.trim_speed_fraction * self.geometry.max_speed_m_s
            trim_speeds = np.minimum(settings.fine_gain_1_s * deficits, trim_speed_limit)
            trim_speeds[deficits < MIN_HEIGHT_DEFICIT_M] = 0.0
        reground_speeds = self._reground_speeds(force_N)
        is_complete = self._is_attitude_within(settings.done_attitude_rad)
        self._update_completion(t_s, is_complete and not reground_speeds.any())
        return np.maximum(trim_speeds, reground_speeds)

    def _update_completion(self, t_s: float, is_complete_now: bool) -> None:
        if not is_complete_now:
            self._complete_since_s = None
            return
        if self._complete_since_s is None:
            self._complete_since_s = t_s
        elif t_s - self._complete_since_s >= self.settings.done_hold_s:
            self.phase = C8Phase.DONE

    # --- output ---

    def _clip_at_stroke_ends(
        self, motor_stroke_m: NDArray[np.float64], leg_speeds: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        margin = self.settings.stroke_end_clip_margin_m
        clipped = leg_speeds.copy()
        clipped[(motor_stroke_m >= self.geometry.stroke_max_m - margin) & (clipped > 0)] = 0.0
        clipped[(motor_stroke_m <= margin) & (clipped < 0)] = 0.0
        return clipped

    def _apply_output_ramp(self, leg_speeds: NDArray[np.float64]) -> NDArray[np.float64]:
        ramp_time_s = self.settings.output_ramp_time_s
        if ramp_time_s is None:
            output = leg_speeds.copy()
        else:
            max_step = self.geometry.max_speed_m_s * self.settings.period_s / ramp_time_s
            step = np.clip(leg_speeds - self._previous_output, -max_step, max_step)
            output = self._previous_output + step
        self._previous_output = output
        return output
