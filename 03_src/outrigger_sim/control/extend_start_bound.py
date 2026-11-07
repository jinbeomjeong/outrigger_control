"""Recursive upper bound of the rod pressure after an extension (option ``tracked_bound``).

``06_analysis/03_hydraulic/coupled/v5/p3_extend_start_spec.md`` 3 / 4 (control-expert, plan D-p),
with the hydraulics-expert review of 2026-11-07 (``p3_review.md``): B hose factor on ``C_r`` and
no counted relief while the pump saturates or the stroke is at its end.

The controller runs the plant's own pure function
(:func:`outrigger_sim.hydraulics.rod_release.flow_limited_rod_pressure`) on conservative inputs
in 1 ms sub-steps per leg::

    valve      u_v <- u + (u_v - u) exp(-dt / tau_v)              (acting command u)
    speed      u_lb = kappa_x u_v,  0 if u_v < delta_ol v_max, the pump demand
               sum A_h |u_v| (extend) + A_ann |u_v| (retract) > eta_v Q_pump, or the stroke
               reading >= the end margin
    pressure   p <- flow_limited_rod_pressure(p, p_bB, u_lb, dt, tau, h C_r(s), ...)
    retract    p <- max(p, p_ret, retract moving model)   (no sub-steps)
    C_r(s)     A_ann^2 (1/k_r + 1/k_h), k_h = beta A_h / (L0h + s),
               k_r = beta A_ann / (L0r + s_max - s), times the hose factor h

The step is increasing in ``p``, decreasing in the speed and increasing in ``C_r``, so a lower
speed and a larger compliance from an equal or higher start bound the plant from above (spec 3).
Every parameter is an ASSUMPTION (hydraulics-expert review); units SI, gauge pressures.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw, flow_limited_rod_pressure

BAR_PA = 1.0e5
LEG_COUNT = 4

BOUND_BULK_MODULUS_PA = 0.69e9
BOUND_HEAD_DEAD_LENGTH_M = 0.08
BOUND_ROD_DEAD_LENGTH_M = 0.10
"""Sensitivity ends of the oil columns (spec 3: a larger ``C_r`` relieves slower)."""
BOUND_HOSE_FACTOR = 1.40
"""``1 + h_B``: B hose volume on ``C_r`` (hydraulics-expert review 2026-11-07, item 1)."""
BOUND_SPEED_FACTOR = 0.8
"""``kappa_x``: delivered speed lower bound over the valve estimate (flow share, ``b_T``)."""
BOUND_OVERLAP_CUT_RATIO = 0.05
"""``delta_ol,max``: below this valve fraction of ``v_max`` no relief is counted (LS2 end)."""
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

    def __post_init__(self) -> None:
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

    def to_meta(self) -> dict[str, float]:
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
        self.tension_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        """Sub-steps of an extending leg whose force read a pull beyond ``p_bB A_ann`` (the
        plant target then exceeds ``p_bB``: a premise of the bound, review item ①)."""
        self.saturated_substeps = 0
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

    def advance(self, command_m_s: ArrayLike, stroke_m: ArrayLike, force_N: ArrayLike,
                retract_floor_Pa: ArrayLike, period_s: float) -> None:
        """One controller period with the acting command ``command_m_s``.

        Args:
            command_m_s: Acting command per leg (the output of the previous period).
            stroke_m: Stroke reading per leg (NaN = unknown).
            force_N: Cylinder force reading per leg (the tension record).
            retract_floor_Pa: ``max(p_ret, retract moving model)`` per leg.
            period_s: Controller period ``T``.
        """
        command = np.asarray(command_m_s, dtype=float)
        stroke = np.asarray(stroke_m, dtype=float)
        is_retracting = command < 0.0
        self.pressure_Pa = np.where(
            is_retracting, np.maximum(self.pressure_Pa, np.asarray(retract_floor_Pa, float)),
            self.pressure_Pa)
        compliance = [self.compliance_m3_Pa(leg, float(stroke[leg])) for leg in range(LEG_COUNT)]
        is_at_end = np.isfinite(stroke) & (stroke >= self.bound.stroke_end_m)
        is_pulled = (command > 0.0) & (np.asarray(force_N, float)
                                       < -self.bound.back_pressure_Pa
                                       * np.asarray(self.geometry.annulus_area_m2))
        for _ in range(round(period_s / self.bound.substep_s)):
            self._substep(command, is_retracting, is_at_end, compliance)
            self.tension_substeps += is_pulled

    def _substep(self, command, is_retracting, is_at_end, compliance) -> None:
        bound, geometry = self.bound, self.geometry
        step_s = bound.substep_s
        keep = math.exp(-step_s / geometry.valve_tau_s) if geometry.valve_tau_s > 0.0 else 0.0
        self.valve_m_s = command + (self.valve_m_s - command) * keep
        is_saturated = self._pump_demand_m3_s() > (bound.volumetric_efficiency
                                                   * bound.pump_flow_m3_s)
        self.saturated_substeps += int(is_saturated)
        cut_m_s = bound.overlap_cut_ratio * geometry.max_speed_m_s
        for leg in range(LEG_COUNT):
            if is_retracting[leg]:
                continue
            valve = float(self.valve_m_s[leg])
            counts_relief = valve >= cut_m_s and not is_saturated and not is_at_end[leg]
            speed_m_s = bound.speed_factor * valve if counts_relief else 0.0
            self.pressure_Pa[leg] = flow_limited_rod_pressure(
                float(self.pressure_Pa[leg]), bound.back_pressure_Pa, speed_m_s, step_s,
                bound.lag_s, compliance[leg], geometry.head_area_m2[leg],
                geometry.annulus_area_m2[leg], False)

    def _pump_demand_m3_s(self) -> float:
        valve = self.valve_m_s
        head = np.asarray(self.geometry.head_area_m2)
        annulus = np.asarray(self.geometry.annulus_area_m2)
        return float(np.sum(np.where(valve > 0.0, head * valve, -annulus * valve)))

    def record(self) -> dict[str, object]:
        return {"extend_bound_Pa": self.pressure_Pa.tolist(),
                "valve_estimate_m_s": self.valve_m_s.tolist(),
                "tension_substeps": self.tension_substeps.tolist(),
                "saturated_substeps": self.saturated_substeps}


def initial_pressure_Pa(retract_floor_Pa: ArrayLike) -> NDArray[np.float64]:
    """Spec 3: the start ``p`` is ``p_ret`` per leg (history unknown, conservative)."""
    return np.array(retract_floor_Pa, dtype=float).reshape(LEG_COUNT)


__all__ = ["BoundGeometry", "ExtendStartBound", "ExtendStartTracker", "initial_pressure_Pa"]
