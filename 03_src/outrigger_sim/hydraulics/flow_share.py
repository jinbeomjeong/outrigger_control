"""Quasi-static flow sharing of the four legs on one fixed pump (engine independent, no pychrono).

Option of the leg plants, **off by default** (criteria
``00_docs/02_hydraulic/hydraulic_coupling_criteria.md`` 9 step 1; D-5 not switched, S8 F-5
(decision_log 2026-11-05), the switch stays for reproducing v4). Given the speed each valve
section asks for and
the cylinder forces, it returns the leg speeds the shared pump can deliver.

Laws (``00_docs/02_hydraulic/hydraulic_coupling.md`` 3)::

    section       Q_i = K_i sqrt(y_i), K_i = A_i |u_i| / sqrt(dp_c), so v_i = u_i sqrt(y_i / dp_c)
    priority      y_i = smin(dp_c, y_open(p_P - p_L,i)): pre-compensator of the drawing
    proportional  y_i = smin(dp_c, p_P - LS): common drop, flow sharing (Q-M5 contrast)
    y_open(D)     = D X^2 / (X^2 + K_i^2): compensator fully open in series with the spool
    gallery       sum Q_i(p_P) + Q_byp(p_P) = Q_sup, Q_byp opens at p_P = LS + dp_ls

With ``Q_dem <= Q_sup (1 + 1e-6)`` and a sufficient load-sense margin the result equals the request
bit for bit (criteria V-1, V-2).

Plant integration (dynamics-expert conditions, the reason for the shape of
:class:`PumpFlowLimiter`):

1. Call it per plant chunk (the harness uses 1 ms), not at the 10 Hz controller rate: the valve lag
   and the pressures move inside a controller period.
2. ``cylinder_force_N`` is the current force of the chunk including the seal friction the head
   pressure has to overcome, not a value frozen at the start slope. The rod pressure of an extending
   leg is the meter-out value computed here.
3. ``speed_request_m_s`` is the speed after the valve lag, the opening that draws the flow.

Pressures GAUGE [Pa], flows m^3/s, speeds m/s, extension positive; arrays in ``LEG_ORDER``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..params import LEG_ORDER, Params

SUPPLY_REL_TOL = 1.0e-6
"""Criteria V-1, V-2: a demand inside this relative tolerance of the supply counts as met."""

HOPSAN_VALVE_NOMINAL_DROP_PA = 7.0e6
"""Nominal pressure drop of the Hopsan pressure valve; the valve constants below refer to it."""

BISECTION_STEPS = 60
GALLERY_UPPER_BOUND_MARGIN_PA = 1.0e5
GALLERY_UPPER_BOUND_STEP_PA = 50.0e5
GALLERY_UPPER_BOUND_LIMIT_PA = 1.0e9
FULL_DROP_REL_TOL = 1.0e-12
"""A section within this of its full spool drop gets exactly its request."""


class FlowShareLaw(StrEnum):
    """How the sections divide a short supply (criteria 8.3; Q-M5 is unanswered)."""

    PRIORITY = "priority"
    PROPORTIONAL = "proportional"


@dataclass(frozen=True)
class FlowCircuit:
    """Known circuit values, normally from the YAML (:func:`flow_circuit_from_params`)."""

    head_area_m2: NDArray[np.float64]
    annulus_area_m2: NDArray[np.float64]
    pump_flow_m3_s: float
    """Drawing flow before the volumetric efficiency."""
    max_speed_m_s: float
    relief_pressure_Pa: float


@dataclass(frozen=True)
class FlowShareAssumptions:
    """Values the YAML does not hold; all ASSUMPTION (criteria 8.2, 8.3; Q-M1, Q-M2, Q-M4, Q-M5).

    The defaults are the nominal values of ``04_scripts/04_hydraulic/coupled/params.py``.

    Attributes:
        eta_v: Pump volumetric efficiency; no default, the level is the choice of each run.
        is_enabled: False = the legs get their request (default, D-5 not switched, S8 F-5
            (decision_log 2026-11-05)).
        compensator_drop_Pa: Section compensator drop dp_c.
        unloading_drop_Pa: Inlet compensator standby drop dp_ls.
        smoothing_width_Pa: Width of the C1 compensator transition; 0 = sharp minimum.
        law: Division of a short supply.
        tank_pressure_Pa: T line back pressure, independent of the flow.
        pilot_pressure_Pa: Rod pressure of a retracting leg (PO check pilot threshold).
        back_land_ratio: B->T land area / P->A land area of the spool.
        compensator_open_coefficient: Compensator fully open, Q = X sqrt(dp) [m^3/s/sqrt(Pa)].
        unloading_spring_coefficient: Inlet compensator spring characteristic Cs.
        unloading_flow_force_coefficient: Inlet compensator flow-force characteristic Cf.
        unloading_open_coefficient: Inlet compensator fully open, Q = X sqrt(dp).
    """

    eta_v: float
    is_enabled: bool = False
    compensator_drop_Pa: float = 10.0e5
    unloading_drop_Pa: float = 20.0e5
    smoothing_width_Pa: float = 1.0e5
    law: FlowShareLaw = FlowShareLaw.PRIORITY
    tank_pressure_Pa: float = 2.0e5
    pilot_pressure_Pa: float = 35.0e5
    back_land_ratio: float = 1.0
    compensator_open_coefficient: float = 1.667e-3 / math.sqrt(HOPSAN_VALVE_NOMINAL_DROP_PA)
    unloading_spring_coefficient: float = math.sqrt(HOPSAN_VALVE_NOMINAL_DROP_PA) / 2.6e-8
    unloading_flow_force_coefficient: float = 1.0 / (
        1.9e-8 * math.sqrt(HOPSAN_VALVE_NOMINAL_DROP_PA)
    )
    unloading_open_coefficient: float = 3.0e-3 / math.sqrt(HOPSAN_VALVE_NOMINAL_DROP_PA)


@dataclass(frozen=True)
class FlowShareResult:
    """Solved operating point of one chunk."""

    speed_m_s: NDArray[np.float64]
    """Delivered leg speeds."""
    flow_m3_s: NDArray[np.float64]
    """Flow from the gallery per leg."""
    gallery_pressure_Pa: float
    bypass_flow_m3_s: float
    load_sense_Pa: float
    spool_drop_Pa: NDArray[np.float64]
    is_limited: NDArray[np.bool_]
    """True where the leg gets less than its request."""
    demand_m3_s: float


def flow_circuit_from_params(params: Params) -> FlowCircuit:
    """The known circuit values of loaded parameters (``02_params/rexome33.yaml``)."""
    return FlowCircuit(
        head_area_m2=_cylinder_areas(params, "head_area_m2"),
        annulus_area_m2=_cylinder_areas(params, "annulus_area_m2"),
        pump_flow_m3_s=float(params.get("actuator.pump_flow_m3_s")),
        max_speed_m_s=float(params.get("actuator.max_speed_m_s")),
        relief_pressure_Pa=float(params.get("actuator.relief_pressure_moving_Pa")),
    )


def _cylinder_areas(params: Params, key: str) -> NDArray[np.float64]:
    return np.array([params.get(f"legs.{leg}.cylinder.{key}") for leg in LEG_ORDER], dtype=float)


def soft_min(
    first: NDArray[np.float64] | float, second: NDArray[np.float64] | float, width: float
) -> NDArray[np.float64]:
    """C1 soft minimum, exactly ``min`` when ``|first - second| >= width``; ``width`` 0 is sharp."""
    minimum = np.minimum(first, second)
    if width <= 0.0:
        return minimum
    gap = np.maximum(width - np.abs(first - second), 0.0)
    return minimum - gap**2 / (4.0 * width)


def _section_spool_drop_Pa(
    spool_coefficient: NDArray[np.float64],
    available_drop_Pa: NDArray[np.float64],
    assumptions: FlowShareAssumptions,
) -> NDArray[np.float64]:
    positive_drop = np.maximum(available_drop_Pa, 0.0)
    if assumptions.law == FlowShareLaw.PROPORTIONAL:
        # flow sharing: the same spool drop on every section
        section_limit = positive_drop
    else:
        open_coefficient_sq = assumptions.compensator_open_coefficient**2
        section_limit = (
            positive_drop * open_coefficient_sq / (open_coefficient_sq + spool_coefficient**2)
        )
    limited = soft_min(
        assumptions.compensator_drop_Pa, section_limit, assumptions.smoothing_width_Pa
    )
    return np.maximum(limited, 0.0)


def _bypass_flow_m3_s(
    gallery_Pa: float, load_sense_Pa: float, assumptions: FlowShareAssumptions
) -> float:
    drop_to_tank = max(gallery_Pa - assumptions.tank_pressure_Pa, 0.0)
    opening = (gallery_Pa - assumptions.unloading_drop_Pa - load_sense_Pa) / (
        assumptions.unloading_spring_coefficient
        + assumptions.unloading_flow_force_coefficient * drop_to_tank
    )
    limited_opening = min(max(opening, 0.0), assumptions.unloading_open_coefficient)
    return limited_opening * math.sqrt(drop_to_tank)


def _load_sense_Pa(
    load_pressure_Pa: NDArray[np.float64],
    is_active: NDArray[np.bool_],
    circuit: FlowCircuit,
    assumptions: FlowShareAssumptions,
) -> float:
    tank = assumptions.tank_pressure_Pa
    highest_load = float(load_pressure_Pa[is_active].max()) if is_active.any() else tank
    return min(max(tank, highest_load), circuit.relief_pressure_Pa)


def _solve_gallery_pressure_Pa(
    spool_coefficient: NDArray[np.float64],
    load_pressure_Pa: NDArray[np.float64],
    load_sense_Pa: float,
    supply_m3_s: float,
    assumptions: FlowShareAssumptions,
) -> float:
    """Bisection on the gallery balance sum Q_i(p_P) + Q_byp(p_P) = Q_sup (module docstring)."""

    def excess_flow_m3_s(gallery_Pa: float) -> float:
        drop = _available_drop_Pa(gallery_Pa, load_pressure_Pa, load_sense_Pa, assumptions)
        spool_drop = _section_spool_drop_Pa(spool_coefficient, drop, assumptions)
        section_flow = float((spool_coefficient * np.sqrt(spool_drop)).sum())
        bypass_flow = _bypass_flow_m3_s(gallery_Pa, load_sense_Pa, assumptions)
        return section_flow + bypass_flow - supply_m3_s

    lower = assumptions.tank_pressure_Pa
    upper = load_sense_Pa + assumptions.unloading_drop_Pa + GALLERY_UPPER_BOUND_MARGIN_PA
    while excess_flow_m3_s(upper) < 0.0 and upper < GALLERY_UPPER_BOUND_LIMIT_PA:
        upper = upper + GALLERY_UPPER_BOUND_STEP_PA
    for _ in range(BISECTION_STEPS):
        middle = 0.5 * (lower + upper)
        if excess_flow_m3_s(middle) > 0.0:
            upper = middle
        else:
            lower = middle
    return 0.5 * (lower + upper)


def _available_drop_Pa(
    gallery_Pa: float,
    load_pressure_Pa: NDArray[np.float64],
    load_sense_Pa: float,
    assumptions: FlowShareAssumptions,
) -> NDArray[np.float64]:
    if assumptions.law == FlowShareLaw.PROPORTIONAL:
        return np.full(load_pressure_Pa.shape, gallery_Pa - load_sense_Pa)
    return gallery_Pa - load_pressure_Pa


def share_flow(
    speed_request_m_s: ArrayLike,
    load_pressure_Pa: ArrayLike,
    circuit: FlowCircuit,
    assumptions: FlowShareAssumptions,
) -> FlowShareResult:
    """Solve the leg speeds for one chunk (module docstring).

    Args:
        speed_request_m_s: Requested leg speeds.
        load_pressure_Pa: Load pressure per leg (:meth:`PumpFlowLimiter.load_pressures_Pa`).
        circuit: Known circuit values.
        assumptions: Supply level and compensator values.

    Returns:
        The operating point. With ``assumptions.is_enabled`` False the speeds are the request.
    """
    request = np.asarray(speed_request_m_s, dtype=float)
    load = np.asarray(load_pressure_Pa, dtype=float)
    area = np.where(request < 0, circuit.annulus_area_m2, circuit.head_area_m2)
    is_active = request != 0
    requested_flow = area * np.abs(request)
    demand = float(requested_flow.sum())
    load_sense = _load_sense_Pa(load, is_active, circuit, assumptions)
    full_drop = assumptions.compensator_drop_Pa

    if not assumptions.is_enabled:
        return FlowShareResult(
            speed_m_s=request.copy(),
            flow_m3_s=requested_flow,
            gallery_pressure_Pa=load_sense + assumptions.unloading_drop_Pa,
            bypass_flow_m3_s=0.0,
            load_sense_Pa=load_sense,
            spool_drop_Pa=np.full(request.shape, full_drop),
            is_limited=np.zeros(request.shape, dtype=bool),
            demand_m3_s=demand,
        )

    supply = circuit.pump_flow_m3_s * assumptions.eta_v
    if demand <= supply * (1.0 + SUPPLY_REL_TOL):
        supply = max(supply, demand)  # inside the supply tolerance the demand counts as met
    spool_coefficient = requested_flow / math.sqrt(full_drop)
    gallery = _solve_gallery_pressure_Pa(spool_coefficient, load, load_sense, supply, assumptions)
    available = _available_drop_Pa(gallery, load, load_sense, assumptions)
    spool_drop = _section_spool_drop_Pa(spool_coefficient, available, assumptions)
    has_full_drop = spool_drop >= full_drop * (1.0 - FULL_DROP_REL_TOL)
    return FlowShareResult(
        speed_m_s=np.where(has_full_drop, request, request * np.sqrt(spool_drop / full_drop)),
        flow_m3_s=np.where(
            has_full_drop, requested_flow, spool_coefficient * np.sqrt(spool_drop)
        ),
        gallery_pressure_Pa=gallery,
        bypass_flow_m3_s=_bypass_flow_m3_s(gallery, load_sense, assumptions),
        load_sense_Pa=load_sense,
        spool_drop_Pa=spool_drop,
        is_limited=is_active & ~has_full_drop,
        demand_m3_s=demand,
    )


class PumpFlowLimiter:
    """Delivered leg speeds per plant chunk: the entry point for a plant (module docstring)."""

    def __init__(self, circuit: FlowCircuit, assumptions: FlowShareAssumptions) -> None:
        self.circuit = circuit
        self.assumptions = assumptions
        self.supply_m3_s = circuit.pump_flow_m3_s * assumptions.eta_v
        # the land opens with the request, so the drop does not depend on the speed
        full_opening_coefficient = (
            circuit.head_area_m2
            * circuit.max_speed_m_s
            / math.sqrt(assumptions.compensator_drop_Pa)
        )
        back_land_coefficient = (
            full_opening_coefficient / circuit.max_speed_m_s * assumptions.back_land_ratio
        )
        self._meter_out_drop_Pa = (circuit.annulus_area_m2 / back_land_coefficient) ** 2

    def demand_m3_s(self, speed_request_m_s: NDArray[np.float64]) -> float:
        """Requested flow summed over the legs (head side extending, annulus retracting)."""
        area = np.where(
            speed_request_m_s < 0, self.circuit.annulus_area_m2, self.circuit.head_area_m2
        )
        return float((area * np.abs(speed_request_m_s)).sum())

    def load_pressures_Pa(
        self, speed_request_m_s: NDArray[np.float64], cylinder_force_N: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Load pressure p_L per leg of the chunk.

        Extending ``(F + A_r p_r) / A_h`` with the meter-out rod pressure, retracting the pilot
        threshold (``hydraulic_coupling.md`` 3, 6).
        """
        tank = self.assumptions.tank_pressure_Pa
        pilot = self.assumptions.pilot_pressure_Pa
        rod_pressure = np.where(
            speed_request_m_s > 0,
            tank + self._meter_out_drop_Pa,
            np.where(speed_request_m_s < 0, pilot, tank),
        )
        head_pressure = (
            cylinder_force_N + self.circuit.annulus_area_m2 * rod_pressure
        ) / self.circuit.head_area_m2
        return np.where(speed_request_m_s < 0, rod_pressure, head_pressure)

    def is_demand_met_with_margin(
        self, speed_request_m_s: NDArray[np.float64], load_pressure_Pa: NDArray[np.float64]
    ) -> bool:
        """True when :meth:`solve` is certain to return the request, without solving.

        The flow fits and at the standby gallery pressure every active section keeps its full
        spool drop. This is the cheap path for the chunks below saturation.
        """
        assumptions = self.assumptions
        is_active = speed_request_m_s != 0
        if not is_active.any():
            return True
        area = np.where(
            speed_request_m_s < 0, self.circuit.annulus_area_m2, self.circuit.head_area_m2
        )
        flow = area * np.abs(speed_request_m_s)
        if float(flow.sum()) > self.supply_m3_s * (1.0 + SUPPLY_REL_TOL):
            return False
        load_sense = _load_sense_Pa(load_pressure_Pa, is_active, self.circuit, assumptions)
        margin = load_sense + assumptions.unloading_drop_Pa - load_pressure_Pa
        needed = assumptions.compensator_drop_Pa + assumptions.smoothing_width_Pa
        if assumptions.law == FlowShareLaw.PROPORTIONAL:
            return bool(np.all(margin[is_active] >= needed))
        spool_coefficient_sq = flow**2 / assumptions.compensator_drop_Pa
        needed_per_leg = needed * (
            1.0 + spool_coefficient_sq / assumptions.compensator_open_coefficient**2
        )
        return bool(np.all(margin[is_active] >= needed_per_leg[is_active]))

    def solve(
        self, speed_request_m_s: NDArray[np.float64], load_pressure_Pa: NDArray[np.float64]
    ) -> FlowShareResult:
        """The full operating point of one chunk (:func:`share_flow`)."""
        return share_flow(speed_request_m_s, load_pressure_Pa, self.circuit, self.assumptions)

    def delivered_speeds_m_s(
        self, speed_request_m_s: ArrayLike, cylinder_force_N: ArrayLike
    ) -> NDArray[np.float64]:
        """Leg speeds of one plant chunk; the request itself when the option is off.

        Args:
            speed_request_m_s: Speed after the valve lag.
            cylinder_force_N: Current force the head pressure works against, seal friction
                included (module docstring, conditions 1 to 3).
        """
        request = np.array(speed_request_m_s, dtype=float)
        if not self.assumptions.is_enabled:
            return request
        load = self.load_pressures_Pa(request, np.asarray(cylinder_force_N, dtype=float))
        if self.is_demand_met_with_margin(request, load):
            return request
        return self.solve(request, load).speed_m_s
