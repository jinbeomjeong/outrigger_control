"""Recursive upper bound of the rod pressure after an extension (option ``tracked_bound``).

``06_analysis/03_hydraulic/coupled/v5/p3_extend_start_spec.md`` 3 / 4 (control-expert, plan D-p),
with the hydraulics-expert review of 2026-11-07 (``p3_review.md``): B hose factor on ``C_r`` and
no counted relief while the pump saturates or the stroke is at its end.

The controller runs the plant's own pure function
(:func:`outrigger_sim.hydraulics.rod_release.flow_limited_rod_pressure`) on conservative inputs
in 1 ms sub-steps per leg::

    valve      u_v <- u + (u_v - u) exp(-dt / tau_v)              (acting command u)
    speed      u_lb = kappa_x max(mean u_v over the sub-step, 0),
               0 if u_v <= 0, if the acting command is 0 (|u| <= eps) and u_v < delta_ol v_max
               (the plant's tail cut; v2, spec 3 (i)), if the pump demand
               sum A_h |u_v| (extend) + A_ann |u_v| (retract) > eta_v Q_pump with per leg the
               larger |u_v| of the sub-step start and end, if the stroke reading >= the end
               margin, or (revision 3) if the head reading of the period or of the previous
               one is >= p_sat 200 bar or NaN (relief stop: valve open, no flow)
    pressure   p <- flow_limited_rod_pressure(p, p_bB, u_lb, dt, tau, h C_r(s), ...)
    retract    p <- max(p, p_ret, retract moving model)   (no sub-steps)
    C_r(s)     A_ann^2 (1/k_r + 1/k_h), k_h = beta A_h / (L0h + s),
               k_r = beta A_ann / (L0r + s_max - s), times the hose factor h

The relief speed is the exact sub-step mean of the valve, not its end value: with v2 a ramp
from rest counts from the first sub-step, and the end value over the whole sub-step relieved up to
210 Pa more than the plant there (T-P3-3, seed 20261107, plant step 1e-4 s).

Records kept by the plant adapters (harness ``harness_hydraulics``, L2b actuator; record only):

* ``hydraulics_record.extend_bound_check`` (:class:`ExtendBoundCheck`, the judged record,
  ``tension_premise.md`` 5.4): per leg ``reads``, ``breach_reads``, ``margin_used_reads``,
  ``min_gap_bar``, ``min_gap_t_s``, ``min_gap_state``, ``first_breach_t_s``,
  ``retract_reads``, ``retract_breach_reads``; ``null`` = option off. Rule of a ③-on run:
  ``sum(breach_reads) == 0`` passes, ``sum(margin_used_reads) > 0`` is a FLAG.
* ``hydraulics_record.tension_truth`` (:class:`TensionTruthCounter`): premise ① diagnostic
  (``substeps``, ``substeps_over_margin``, ``active_substeps``, ``min_p_tr_minus_p_star_bar``).

The step is increasing in ``p``, decreasing in the speed and increasing in ``C_r``, so a lower
speed and a larger compliance from an equal or higher start bound the plant from above (spec 3).
Every parameter is an ASSUMPTION (hydraulics-expert review); units SI, gauge pressures.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw, flow_limited_rod_pressure

BAR_PA = 1.0e5
LEG_COUNT = 4

EXTEND_START_REVISION = 3
"""Revision of the bound rule in the meta (v2: overlap cut with a zero command only, sub-step
mean valve, start / end saturation test; spec 3 and its v2 review. 3: no relief counted in a
period whose head reading or the previous one is at the relief stop, spec 10). A
``tracked_bound`` meta of another revision, or without one (v1), is refused
(:func:`check_extend_start_meta`)."""
TRACKED_BOUND_RULE = "tracked_bound"

BOUND_BULK_MODULUS_PA = 0.69e9
BOUND_HEAD_DEAD_LENGTH_M = 0.08
BOUND_ROD_DEAD_LENGTH_M = 0.10
"""Sensitivity ends of the oil columns (spec 3: a larger ``C_r`` relieves slower)."""
BOUND_HOSE_FACTOR = 1.40
"""``1 + h_B``: B hose volume on ``C_r`` (hydraulics-expert review 2026-11-07, item 1)."""
BOUND_SPEED_FACTOR = 0.8
"""``kappa_x``: delivered speed lower bound over the valve estimate (flow share, ``b_T``)."""
BOUND_OVERLAP_CUT_RATIO = 0.05
"""``delta_ol,max``: with a zero acting command, below this valve fraction of ``v_max`` no relief
is counted (LS2 end). A small non-zero command flows in the plant (spec L-6) and counts
``kappa_x u_v`` (v2, user decision 2026-11-07; v1 cut every command below it)."""
ZERO_COMMAND_M_S = 1.0e-6
"""``eps`` of a zero acting command: the plant cuts the tail at ``|u| <= eps`` (L2b
``LOCK_EPS_M_S``, the harness ``install_overlap_cut``), so the bound treats it as zero too."""
BOUND_LAG_S = 0.05
BOUND_BACK_PRESSURE_PA = 5.0 * BAR_PA
"""``p_bB``: extension target of the plant (its ASSUMPTION)."""
BOUND_MARGIN_PA = 0.5 * BAR_PA
"""``delta_m``: sub-step and reading-delay margin added to the bound."""
BOUND_SUBSTEP_S = 1.0e-3
BOUND_PUMP_FLOW_M3_S = 60.2e-3 / 60.0
"""``Q_pump`` 60.2 L/min (YAML ``actuator`` pump)."""
BOUND_VOLUMETRIC_EFFICIENCY = 0.85
"""``eta_v`` of the saturation test; the lower end of the plant values (VB 0.85, nominal 0.95)
counts saturation earlier (ASSUMPTION)."""
BOUND_STROKE_END_M = 0.6848
"""End-margin stroke: at or beyond it the end braking may slow the leg (no relief counted)."""
BOUND_SATURATION_STOP_HEAD_PA = 200.0e5
"""``p_sat`` (spec 10, revision 3): a head reading at or above it (or NaN) in the period or the
previous one means the leg may stand at the relief stop (210 bar) with its valve open, so no
relief is counted. ASSUMPTION: relief 210 bar minus a 10 bar reading allowance (at least twice
the normal-grade +-4 bar)."""


@dataclass(frozen=True)
class ExtendStartBound:
    """Conservative parameters of the bound (spec 3 table, review 2026-11-07; ASSUMPTIONS).

    Attributes:
        bulk_modulus_Pa: ``beta`` of ``C_r``.
        head_dead_length_m: ``L0h``.
        rod_dead_length_m: ``L0r``.
        hose_factor: ``1 + h_B`` on ``C_r``.
        speed_factor: ``kappa_x``.
        overlap_cut_ratio: ``delta_ol,max`` (fraction of ``v_max``).
        lag_s: ``tau`` of the pressure lag.
        back_pressure_Pa: ``p_bB``.
        margin_Pa: ``delta_m``.
        substep_s: Sub-step ``dt``.
        pump_flow_m3_s: ``Q_pump``.
        volumetric_efficiency: ``eta_v`` of the saturation test.
        stroke_end_m: End-margin stroke.
        saturation_stop_head_Pa: ``p_sat`` of the relief-stop test.
        revision: Rule revision (only :data:`EXTEND_START_REVISION` runs in this code).
    """

    bulk_modulus_Pa: float = BOUND_BULK_MODULUS_PA
    head_dead_length_m: float = BOUND_HEAD_DEAD_LENGTH_M
    rod_dead_length_m: float = BOUND_ROD_DEAD_LENGTH_M
    hose_factor: float = BOUND_HOSE_FACTOR
    speed_factor: float = BOUND_SPEED_FACTOR
    overlap_cut_ratio: float = BOUND_OVERLAP_CUT_RATIO
    lag_s: float = BOUND_LAG_S
    back_pressure_Pa: float = BOUND_BACK_PRESSURE_PA
    margin_Pa: float = BOUND_MARGIN_PA
    substep_s: float = BOUND_SUBSTEP_S
    pump_flow_m3_s: float = BOUND_PUMP_FLOW_M3_S
    volumetric_efficiency: float = BOUND_VOLUMETRIC_EFFICIENCY
    stroke_end_m: float = BOUND_STROKE_END_M
    saturation_stop_head_Pa: float = BOUND_SATURATION_STOP_HEAD_PA
    revision: int = EXTEND_START_REVISION

    def __post_init__(self) -> None:
        if self.revision != EXTEND_START_REVISION:
            raise ValueError(f"extend start bound revision {self.revision!r}: this code runs "
                             f"revision {EXTEND_START_REVISION} only")
        positive = ("bulk_modulus_Pa", "hose_factor", "substep_s", "pump_flow_m3_s",
                    "volumetric_efficiency")
        for name in positive:
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{name} must be a finite value > 0, got {value!r}")
        if not 0.0 <= self.speed_factor <= 1.0:
            raise ValueError(f"speed_factor must be in [0, 1], got {self.speed_factor!r}")
        if not (self.lag_s >= 0.0 and self.margin_Pa >= 0.0):
            raise ValueError("lag_s and margin_Pa must be >= 0")

    def to_meta(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class BoundGeometry:
    """Per-leg cylinder data of the bound (from the monitor).

    Attributes:
        head_area_m2: ``A_h`` per leg.
        annulus_area_m2: ``A_ann`` per leg.
        stroke_max_m: ``s_max``.
        max_speed_m_s: ``v_max``.
        valve_tau_s: ``tau_v`` of the controller's valve model.
    """

    head_area_m2: tuple[float, ...]
    annulus_area_m2: tuple[float, ...]
    stroke_max_m: float
    max_speed_m_s: float
    valve_tau_s: float


class ExtendStartTracker:
    """State ``(p, u_v)`` per leg and the period update (module docstring).

    Args:
        bound: The conservative parameters.
        geometry: Cylinder data.
        start_Pa: Initial ``p`` per leg (``p_ret``: the history is unknown, spec 3).
    """

    def __init__(self, bound: ExtendStartBound, geometry: BoundGeometry,
                 start_Pa: ArrayLike) -> None:
        self.bound = bound
        self.geometry = geometry
        self.pressure_Pa = np.array(start_Pa, dtype=float).reshape(LEG_COUNT)
        self.valve_m_s = np.zeros(LEG_COUNT)
        self.saturated_substeps = 0
        self.saturation_stop_periods = np.zeros(LEG_COUNT, dtype=np.int64)
        """Periods per leg without counted relief for a relief stop (revision 3, spec 10)."""
        self.previous_head_Pa: NDArray[np.float64] | None = None
        self._law = RodPressureFlowLaw()

    def bound_Pa(self, leg: int) -> float:
        """``p + delta_m``: the bound the start value and the moving estimate take."""
        return float(self.pressure_Pa[leg]) + self.bound.margin_Pa

    def compliance_m3_Pa(self, leg: int, stroke_m: float) -> float:
        """``h C_r(s)``; an unknown stroke takes ``s = 0`` (largest ``C_r``: ``A_h > A_ann``)."""
        bound, geometry = self.bound, self.geometry
        stroke = stroke_m if math.isfinite(stroke_m) else 0.0
        stroke = min(max(stroke, 0.0), geometry.stroke_max_m)
        head_area, annulus = geometry.head_area_m2[leg], geometry.annulus_area_m2[leg]
        head_stiffness = bound.bulk_modulus_Pa * head_area / (bound.head_dead_length_m + stroke)
        rod_stiffness = bound.bulk_modulus_Pa * annulus / (
            bound.rod_dead_length_m + geometry.stroke_max_m - stroke)
        return bound.hose_factor * self._law.rod_compliance_m3_Pa(annulus, head_stiffness,
                                                                  rod_stiffness)

    def advance(self, command_m_s: ArrayLike, stroke_m: ArrayLike,
                retract_floor_Pa: ArrayLike, period_s: float,
                head_Pa: ArrayLike | None = None) -> None:
        """One controller period with the acting command ``command_m_s``.

        Args:
            command_m_s: Acting command per leg (the output of the previous period).
            stroke_m: Stroke reading per leg (NaN = unknown).
            retract_floor_Pa: ``max(p_ret, retract moving model)`` per leg.
            period_s: Controller period ``T``.
            head_Pa: Head pressure reading per leg of this period (the relief-stop test with
                the previous one, revision 3); None = no reading given (no stop counted).
        """
        command = np.asarray(command_m_s, dtype=float)
        stroke = np.asarray(stroke_m, dtype=float)
        is_retracting = command < 0.0
        self.pressure_Pa = np.where(
            is_retracting, np.maximum(self.pressure_Pa, np.asarray(retract_floor_Pa, float)),
            self.pressure_Pa)
        compliance = [self.compliance_m3_Pa(leg, float(stroke[leg])) for leg in range(LEG_COUNT)]
        is_stopped = self._relief_stop(head_Pa)
        self.saturation_stop_periods += is_stopped & ~is_retracting
        is_at_end = np.isfinite(stroke) & (stroke >= self.bound.stroke_end_m)
        for _ in range(round(period_s / self.bound.substep_s)):
            self._substep(command, is_retracting, is_at_end | is_stopped, compliance)

    def _relief_stop(self, head_Pa: ArrayLike | None) -> NDArray[np.bool_]:
        """Spec 10 #1, #3: head reading of this period or the previous one at or above
        ``p_sat``, or NaN (a stop that starts inside the period shows in one of the two)."""
        if head_Pa is None:
            return np.zeros(LEG_COUNT, dtype=bool)
        head = np.asarray(head_Pa, dtype=float).reshape(LEG_COUNT)
        previous = self.previous_head_Pa
        self.previous_head_Pa = head.copy()
        readings = [head] if previous is None else [head, previous]
        is_stopped = np.zeros(LEG_COUNT, dtype=bool)
        for reading in readings:
            with np.errstate(invalid="ignore"):
                is_stopped |= ~(reading < self.bound.saturation_stop_head_Pa)
        return is_stopped

    def _substep(self, command, is_retracting, is_at_end, compliance) -> None:
        bound, geometry = self.bound, self.geometry
        step_s = bound.substep_s
        start_valve_m_s = self.valve_m_s
        mean_valve_m_s = self._advance_valve(command, step_s)
        demand_m3_s = self._pump_demand_m3_s(start_valve_m_s, self.valve_m_s)
        is_saturated = demand_m3_s > bound.volumetric_efficiency * bound.pump_flow_m3_s
        self.saturated_substeps += int(is_saturated)
        cut_m_s = bound.overlap_cut_ratio * geometry.max_speed_m_s
        for leg in range(LEG_COUNT):
            if is_retracting[leg]:
                continue
            valve = float(self.valve_m_s[leg])
            # The plant closes the tail only with a zero acting command (spec L-6); a valve
            # still negative after a retract fills, so it never counts relief.
            is_tail_cut = abs(command[leg]) <= ZERO_COMMAND_M_S and valve < cut_m_s
            counts_relief = (valve > 0.0 and not is_tail_cut and not is_saturated
                             and not is_at_end[leg])
            mean_speed_m_s = max(float(mean_valve_m_s[leg]), 0.0)
            speed_m_s = bound.speed_factor * mean_speed_m_s if counts_relief else 0.0
            self.pressure_Pa[leg] = flow_limited_rod_pressure(
                float(self.pressure_Pa[leg]), bound.back_pressure_Pa, speed_m_s, step_s,
                bound.lag_s, compliance[leg], geometry.head_area_m2[leg],
                geometry.annulus_area_m2[leg], False)

    def _advance_valve(self, command: NDArray[np.float64], step_s: float
                       ) -> NDArray[np.float64]:
        """Move ``u_v`` to the end of the sub-step; return its exact mean over the sub-step."""
        tau_s = self.geometry.valve_tau_s
        start_m_s = self.valve_m_s
        if tau_s <= 0.0:
            self.valve_m_s = np.array(command, dtype=float)
            return self.valve_m_s.copy()
        keep = math.exp(-step_s / tau_s)
        self.valve_m_s = command + (start_m_s - command) * keep
        return command + (start_m_s - command) * (tau_s / step_s) * (1.0 - keep)

    def _pump_demand_m3_s(self, start_valve_m_s: NDArray[np.float64],
                          end_valve_m_s: NDArray[np.float64]) -> float:
        """``sum A |u_v|`` with per leg the larger demand of the sub-step start and end: on a
        falling valve the end value alone misses a saturation early in the sub-step (spec 3
        (ii), v2 review)."""
        return float(np.sum(np.maximum(self._leg_demand_m3_s(start_valve_m_s),
                                       self._leg_demand_m3_s(end_valve_m_s))))

    def _leg_demand_m3_s(self, valve_m_s: NDArray[np.float64]) -> NDArray[np.float64]:
        head = np.asarray(self.geometry.head_area_m2)
        annulus = np.asarray(self.geometry.annulus_area_m2)
        return np.where(valve_m_s > 0.0, head * valve_m_s, -annulus * valve_m_s)

    def record(self) -> dict[str, object]:
        return {"extend_bound_Pa": self.pressure_Pa.tolist(),
                "valve_estimate_m_s": self.valve_m_s.tolist(),
                "saturated_substeps": self.saturated_substeps,
                "saturation_stop_periods": self.saturation_stop_periods.tolist()}


TENSION_READ_SIGMA_PA = 0.20e5
"""ASSUMPTION: white noise of one pressure reading, normal grade (``pressure_error`` table, spec
71); the static errors are removed by the zero offsets, not by this margin."""
TENSION_READ_K = 3.0
"""ASSUMPTION: the read margin is ``k sigma_F``, ``sigma_F = sigma sqrt(A_h^2 + A_ann^2)``
(hydraulics-expert ``tension_premise.md`` 4, S-1)."""
TENSION_RULE = "zero_corrected_3sigma"
"""``review_record.tension_rule``; a record without it is the raw-reading count of 83e8a36 and
earlier (judged invalid)."""


class PremiseRecord:
    """Review records of the bound's premises, kept with the ③ option on or off (criteria
    rev. 6 14.5, hydraulics-expert ③ review 2026-11-07; user decision 2026-11-07). Records only:
    nothing here feeds a command. The premise itself is judged on the plant truth
    (:class:`TensionTruthCounter`); these are the controller's readings, kept for the machine.

    * ``tension_substeps``: 1 ms sub-steps of an extending, zero-calibrated leg whose net force
      reading (zero offset removed) pulls beyond ``p_bB A_ann`` plus the read margin
      ``k sigma_F`` (front 828 N, rear 600 N); ``tension_substeps_uncalibrated`` the same for a
      leg without a zero offset (its static sensor error is still in the reading).
    * ``d2_violation_start_ratio``: stroke rate over the acting command at each D2 violation
      start (priority saturation shows as 1-2 % ``v_max`` delivered; ``None`` = no rate).

    Args:
        head_area_m2: ``A_h`` per leg.
        annulus_area_m2: ``A_ann`` per leg.
    """

    def __init__(self, head_area_m2: ArrayLike, annulus_area_m2: ArrayLike) -> None:
        head = np.asarray(head_area_m2, dtype=float).reshape(LEG_COUNT)
        annulus = np.asarray(annulus_area_m2, dtype=float).reshape(LEG_COUNT)
        self.tension_read_margin_N = (TENSION_READ_K * TENSION_READ_SIGMA_PA
                                      * np.sqrt(head**2 + annulus**2))
        self.tension_threshold_N = BOUND_BACK_PRESSURE_PA * annulus + self.tension_read_margin_N
        self.tension_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        self.tension_substeps_uncalibrated = np.zeros(LEG_COUNT, dtype=np.int64)
        self.d2_start_ratios: list[list[float | None]] = [[] for _ in range(LEG_COUNT)]

    def count_tension(self, command_m_s: ArrayLike, net_force_N: ArrayLike,
                      is_calibrated: ArrayLike, period_s: float) -> None:
        """One controller period: the net force reading holds over its 1 ms sub-steps.

        Args:
            command_m_s: Acting command per leg.
            net_force_N: ``p_h A_h - p_r A_ann - c_i`` per leg (``c_i`` 0 if not calibrated).
            is_calibrated: The leg has a zero offset.
            period_s: Controller period.
        """
        is_pulled = ((np.asarray(command_m_s, float) > 0.0)
                     & (np.asarray(net_force_N, float) < -self.tension_threshold_N))
        calibrated = np.asarray(is_calibrated, bool)
        substeps = round(period_s / BOUND_SUBSTEP_S)
        self.tension_substeps += substeps * (is_pulled & calibrated)
        self.tension_substeps_uncalibrated += substeps * (is_pulled & ~calibrated)

    def add_d2_start(self, leg: int, stroke_rate_m_s: float | None,
                     command_m_s: float) -> None:
        is_known = stroke_rate_m_s is not None and math.isfinite(stroke_rate_m_s)
        self.d2_start_ratios[leg].append(
            float(stroke_rate_m_s) / command_m_s if is_known else None)

    def to_meta(self) -> dict[str, object]:
        return {"tension_rule": TENSION_RULE,
                "tension_substeps": self.tension_substeps.tolist(),
                "tension_substeps_uncalibrated": self.tension_substeps_uncalibrated.tolist(),
                "tension_threshold_N": self.tension_threshold_N.tolist(),
                "tension_read_margin_N": self.tension_read_margin_N.tolist(),
                "d2_violation_start_ratio": [list(ratios) for ratios in self.d2_start_ratios]}


TENSION_TRUTH_RULE = ("plant p* > p_bB on an unlocked leg with valve > 0, per 1 ms; "
                      "diagnostic; judged by extend_bound_check")


class TensionTruthCounter:
    """Plant truth of premise ① (``tension_premise.md`` 4, S-2), a **diagnostic** record since
    5.4: the bound is judged by :class:`ExtendBoundCheck`. Time an extending leg spends with the
    plant's extend target ``p*`` above ``p_bB``, kept by the plant adapters (harness, L2b) and
    recorded as ``hydraulics_record.tension_truth``. ``active_substeps`` = the part where ``p*``
    is also above the plant rod pressure ``p_tr`` (the target holds the plant up: the case that
    can break the bound; a break-away after a retract lock relieves from above, 5.2). Records
    only.

    The adapters add every plant step (1 ms harness chunk, L2b step); the counts are the summed
    time in 1 ms sub-steps.
    """

    def __init__(self) -> None:
        self.seconds = np.zeros(LEG_COUNT)
        self.seconds_over_margin = np.zeros(LEG_COUNT)
        self.seconds_active = np.zeros(LEG_COUNT)
        self.max_excess_Pa = np.zeros(LEG_COUNT)
        self.min_plant_minus_target_Pa = np.full(LEG_COUNT, np.inf)
        self.first_t_s: list[float | None] = [None] * LEG_COUNT

    def add(self, is_extending: ArrayLike, target_Pa: ArrayLike, duration_s: float,
            t_s: float, plant_rod_Pa: ArrayLike | None = None) -> None:
        """One plant step.

        Args:
            is_extending: Unlocked leg with a valve speed > 0 in this step.
            target_Pa: Plant extend target ``p*`` per leg (gauge; NaN = not extending).
            duration_s: Step length.
            t_s: Plant time at the step end.
            plant_rod_Pa: Plant rod pressure ``p_tr`` per leg (None = not known: no
                ``active_substeps``).
        """
        extending = np.asarray(is_extending, bool)
        if not extending.any():
            return
        target = np.asarray(target_Pa, float)
        with np.errstate(invalid="ignore"):
            excess_Pa = np.where(extending, target - BOUND_BACK_PRESSURE_PA, -np.inf)
        over = excess_Pa > 0.0
        if not over.any():
            return
        self.seconds += duration_s * over
        self.seconds_over_margin += duration_s * (excess_Pa > BOUND_MARGIN_PA)
        self.max_excess_Pa = np.where(over, np.maximum(self.max_excess_Pa, excess_Pa),
                                      self.max_excess_Pa)
        if plant_rod_Pa is not None:
            plant_minus_target_Pa = np.asarray(plant_rod_Pa, float) - target
            with np.errstate(invalid="ignore"):
                self.seconds_active += duration_s * (over & (plant_minus_target_Pa < 0.0))
                self.min_plant_minus_target_Pa = np.where(
                    over, np.fmin(self.min_plant_minus_target_Pa, plant_minus_target_Pa),
                    self.min_plant_minus_target_Pa)
        for leg in np.flatnonzero(over):
            if self.first_t_s[leg] is None:
                self.first_t_s[leg] = round(float(t_s), 6)

    def record(self) -> dict[str, object]:
        known = np.isfinite(self.min_plant_minus_target_Pa)
        return {"rule": TENSION_TRUTH_RULE,
                "substeps": _substeps(self.seconds),
                "substeps_over_margin": _substeps(self.seconds_over_margin),
                "active_substeps": _substeps(self.seconds_active),
                "max_excess_bar": (self.max_excess_Pa / BAR_PA).tolist(),
                "min_p_tr_minus_p_star_bar": [
                    float(value) / BAR_PA if is_known else None
                    for value, is_known in zip(self.min_plant_minus_target_Pa, known,
                                               strict=True)],
                "first_t_s": list(self.first_t_s),
                "back_pressure_bar": BOUND_BACK_PRESSURE_PA / BAR_PA,
                "margin_bar": BOUND_MARGIN_PA / BAR_PA}


def _substeps(seconds: NDArray[np.float64]) -> list[int]:
    return [round(value / BOUND_SUBSTEP_S) for value in seconds.tolist()]


EXTEND_BOUND_CHECK_RULE = (
    "③ judged here (tension_premise.md 5.4): at every controller read, plant rod pressure p_tr "
    "against the bound p_hat + delta_m of that read, on moving legs and on legs locked after an "
    "extension; breach_reads = p_tr > p_hat + delta_m (judged: the sum must be 0), "
    "margin_used_reads = p_tr > p_hat (FLAG), both beyond a 1 Pa rounding allowance; "
    "retracting legs are counted apart (premise ④); null record = option off")


BOUND_CHECK_TOLERANCE_PA = 1.0
"""Rounding allowance of :class:`ExtendBoundCheck`: in a steady extension the plant lag and the
bound's ``p_hat`` both converge to ``p_bB`` and differ by float rounding only (ASSUMPTION,
1 Pa = 1e-5 bar, far below any physical margin)."""


class ExtendBoundState(StrEnum):
    """Leg state of one bound comparison (``min_gap_state``)."""

    EXTEND_MOVING = "ext_moving"
    EXTEND_LOCKED = "ext_locked"
    RETRACT = "retract"


class ExtendBoundCheck:
    """The ③ bound against the plant at the controller reads (``tension_premise.md`` 5.5),
    kept by the plant adapters as ``hydraulics_record.extend_bound_check``. Records only.

    Judged legs: moving while extending (``ext_moving``) and locked after an extension
    (``ext_locked``). A retracting leg (``retract``, the bound is the retract floor there,
    premise ④) has its own counts. A leg locked after a retraction is not compared.
    """

    def __init__(self) -> None:
        self.reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.locked_breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        """The part of ``breach_reads`` on legs locked after an extension (their rod pressure
        follows the locked law after the lock, not the relief the bound tracks)."""
        self.margin_used_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.retract_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.retract_breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.min_gap_Pa = np.full(LEG_COUNT, np.inf)
        self.min_gap_t_s: list[float | None] = [None] * LEG_COUNT
        self.min_gap_state: list[str | None] = [None] * LEG_COUNT
        self.first_breach_t_s: list[float | None] = [None] * LEG_COUNT

    def add(self, t_s: float, bound_Pa: ArrayLike, plant_rod_Pa: ArrayLike,
            states: list[ExtendBoundState | None]) -> None:
        """One controller read.

        Args:
            t_s: Read time.
            bound_Pa: The controller's ``p_hat + delta_m`` per leg.
            plant_rod_Pa: Plant rod pressure ``p_tr`` per leg at the read.
            states: Leg state per leg; None = not compared (locked after a retraction).
        """
        bound = np.asarray(bound_Pa, float)
        plant = np.asarray(plant_rod_Pa, float)
        for leg, state in enumerate(states):
            if state is None or not math.isfinite(plant[leg]):
                continue
            gap_Pa = float(bound[leg] - plant[leg])
            is_breach = gap_Pa < -BOUND_CHECK_TOLERANCE_PA
            if state is ExtendBoundState.RETRACT:
                self.retract_reads[leg] += 1
                self.retract_breach_reads[leg] += int(is_breach)
                continue
            self.reads[leg] += 1
            self.breach_reads[leg] += int(is_breach)
            if state is ExtendBoundState.EXTEND_LOCKED:
                self.locked_breach_reads[leg] += int(is_breach)
            self.margin_used_reads[leg] += int(gap_Pa < BOUND_MARGIN_PA - BOUND_CHECK_TOLERANCE_PA)
            if is_breach and self.first_breach_t_s[leg] is None:
                self.first_breach_t_s[leg] = round(float(t_s), 6)
            if gap_Pa < self.min_gap_Pa[leg]:
                self.min_gap_Pa[leg] = gap_Pa
                self.min_gap_t_s[leg] = round(float(t_s), 6)
                self.min_gap_state[leg] = state.value

    def record(self) -> dict[str, object]:
        return {"rule": EXTEND_BOUND_CHECK_RULE,
                "reads": self.reads.tolist(),
                "breach_reads": self.breach_reads.tolist(),
                "locked_breach_reads": self.locked_breach_reads.tolist(),
                "margin_used_reads": self.margin_used_reads.tolist(),
                "min_gap_bar": [float(value) / BAR_PA if math.isfinite(value) else None
                                for value in self.min_gap_Pa],
                "min_gap_t_s": list(self.min_gap_t_s),
                "min_gap_state": list(self.min_gap_state),
                "first_breach_t_s": list(self.first_breach_t_s),
                "retract_reads": self.retract_reads.tolist(),
                "retract_breach_reads": self.retract_breach_reads.tolist()}


def extend_bound_states(is_locked: ArrayLike, last_direction: ArrayLike
                        ) -> list[ExtendBoundState | None]:
    """Leg states of :class:`ExtendBoundCheck` from the plant lock state and the sign of its
    last moving direction (> 0 extension)."""
    states: list[ExtendBoundState | None] = []
    for locked, direction in zip(np.asarray(is_locked, bool), np.asarray(last_direction, float),
                                 strict=True):
        if direction > 0.0:
            states.append(ExtendBoundState.EXTEND_LOCKED if locked
                          else ExtendBoundState.EXTEND_MOVING)
        elif locked:
            states.append(None)
        else:
            states.append(ExtendBoundState.RETRACT)
    return states


def check_extend_start_meta(settings_meta: Mapping[str, Any]) -> None:
    """Refuse a stored two-pressure settings meta of an older ``tracked_bound`` rule.

    Args:
        settings_meta: ``TwoPressureSettings.to_meta()`` of a stored run.

    Raises:
        ValueError: The rule is ``tracked_bound`` and its bound has no ``revision`` (v1) or
            another revision than :data:`EXTEND_START_REVISION`.
    """
    if settings_meta.get("extend_start_rule") != TRACKED_BOUND_RULE:
        return
    revision = (settings_meta.get("extend_start_bound") or {}).get("revision")
    if revision != EXTEND_START_REVISION:
        label = "v1 (no revision)" if revision is None else f"revision {revision!r}"
        raise ValueError(f"stored tracked_bound meta is {label}; this code runs revision "
                         f"{EXTEND_START_REVISION}")


def initial_pressure_Pa(retract_floor_Pa: ArrayLike) -> NDArray[np.float64]:
    """Spec 3: the start ``p`` is ``p_ret`` per leg (history unknown, conservative)."""
    return np.array(retract_floor_Pa, dtype=float).reshape(LEG_COUNT)


__all__ = ["EXTEND_START_REVISION", "BoundGeometry", "ExtendStartBound", "ExtendStartTracker",
           "ExtendBoundCheck", "ExtendBoundState", "PremiseRecord", "TensionTruthCounter",
           "check_extend_start_meta", "extend_bound_states", "initial_pressure_Pa"]
