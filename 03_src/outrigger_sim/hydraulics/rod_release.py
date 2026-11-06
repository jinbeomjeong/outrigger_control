"""M2: rod pressure of a moving leg shifts the oil reference (engine independent, no pychrono).

``00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`` 2.3 (rule of ``pressure_review_report.md`` 12.4).
At the same net force a rod pressure ``p_r`` compresses the head oil column by another
``A_ann p_r / k_h``, so a moving leg's ``s_ref`` moves by that amount when ``p_r`` changes::

    d s_ref^k = A_ann (p_r^(k-1) - p_r^k) / k_h   moving legs, 0 on locked legs
    force change at a fixed body = (k_2 / k_h) A_ann d p_r

Both directions (decision D-4). **Off by default**: nothing here runs without the option. The rod
pressure is a model value of the plant law, not a measured one: ``p_bB`` 5 bar, ``tau`` 0.05 s and
``p_r0`` are ASSUMPTIONS (spec 2.3).

The shift is clipped to the travel range: a reference outside it would be clipped back by the next
speed reference step, which turns the difference into a large speed. Clipped steps are counted.

Moving rod pressure, revision 3 (``flow_limited_r3``, user decision 2026-11-06, P-A without the B
hose): the first-order lag towards ``p*`` may not change the pressure faster than the valve flow
fills or drains the rod chamber (:func:`flow_limited_rod_pressure`)::

    p_lag = p* + (p_r^(k-1) - p*) exp(-dt / tau)
    retract, p* > p_r^(k-1):  p_r^k = min(p_lag, p_r^(k-1) + Q_in dt / C_r),  Q_in = A_ann |u|
    extend,  p* < p_r^(k-1):  p_r^k = max(p_lag, p_r^(k-1) - Q_out dt / C_r),
                              Q_out = b_T A_h |u| sqrt(max(p_r^(k-1) - p_T, 0) / dp_c)
    otherwise                 p_r^k = p_lag
    C_r = A_ann^2 (1 / k_r + 1 / k_h)   (B hose not included: ASSUMPTION)

``b_T``, ``dp_c`` and ``p_T`` are ASSUMPTIONS (the values of ``coupled/params.py`` and of the flow
share model). ``u = 0`` holds the pressure on the filled side.

Units SI; gauge pressures; arrays per leg.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np
from numpy.typing import ArrayLike, NDArray

PREVIOUS_PRESSURE_KEY = "m2_p_prev_Pa"
SHIFT_TOTAL_KEY = "m2_shift_total_m"
CLIPPED_STEPS_KEY = "m2_clipped_steps"
"""Optional snapshot keys (written only with the option on)."""

FLOW_LIMITED_LAW = "flow_limited_r3"
"""Name of the moving rod-pressure law in the meta and the definition digests (M2 on only)."""
METER_OUT_RATIO = 1.0
"""``b_T``: meter-out (A -> T) over meter-in (P -> A) opening at the same spool stroke
(ASSUMPTION)."""
SPOOL_REFERENCE_DROP_PA = 10.0e5
"""``dp_c``: spool drop at which the opening passes ``A_h |u|`` (compensator drop, ASSUMPTION)."""
TANK_PRESSURE_PA = 2.0e5
"""``p_T``: return line pressure, gauge (ASSUMPTION)."""


def flow_limited_rod_pressure(
    previous_Pa: float,
    target_Pa: float,
    speed_m_s: float,
    step_s: float,
    lag_s: float,
    compliance_m3_Pa: float,
    head_area_m2: float,
    annulus_area_m2: float,
    is_retract: bool,
    *,
    meter_out_ratio: float = METER_OUT_RATIO,
    spool_reference_drop_Pa: float = SPOOL_REFERENCE_DROP_PA,
    tank_pressure_Pa: float = TANK_PRESSURE_PA,
) -> float:
    """Moving rod pressure after one step of the revision 3 law (module docstring).

    The flow cap is explicit on the previous pressure and never passes the lagged value.

    Args:
        previous_Pa: ``p_r^(k-1)``.
        target_Pa: ``p*`` of the moving direction.
        speed_m_s: Delivered leg speed ``u`` of this step (its magnitude is used).
        step_s: ``dt``.
        lag_s: ``tau``; 0 jumps to the target as the plain lag does.
        compliance_m3_Pa: ``C_r`` (:meth:`RodPressureFlowLaw.rod_compliance_m3_Pa`).
        head_area_m2: ``A_h``.
        annulus_area_m2: ``A_ann``.
        is_retract: The leg moves in its retract direction (meter-in on the rod side).

    Returns:
        ``p_r^k`` [Pa gauge].
    """
    keep = math.exp(-step_s / lag_s) if lag_s > 0.0 else 0.0
    lagged_Pa = target_Pa + (previous_Pa - target_Pa) * keep
    if is_retract and target_Pa > previous_Pa:
        fill_m3_s = annulus_area_m2 * abs(speed_m_s)
        return min(lagged_Pa, previous_Pa + fill_m3_s * step_s / compliance_m3_Pa)
    if not is_retract and target_Pa < previous_Pa:
        orifice_drop_Pa = max(previous_Pa - tank_pressure_Pa, 0.0)
        drain_m3_s = (meter_out_ratio * head_area_m2 * abs(speed_m_s)
                      * math.sqrt(orifice_drop_Pa / spool_reference_drop_Pa))
        return max(lagged_Pa, previous_Pa - drain_m3_s * step_s / compliance_m3_Pa)
    return lagged_Pa


@dataclass(frozen=True)
class RodPressureFlowLaw:
    """Constants of the revision 3 law; the harness and the L2b law call the same function.

    Attributes:
        meter_out_ratio: ``b_T``.
        spool_reference_drop_Pa: ``dp_c``.
        tank_pressure_Pa: ``p_T``.
    """

    meter_out_ratio: float = METER_OUT_RATIO
    spool_reference_drop_Pa: float = SPOOL_REFERENCE_DROP_PA
    tank_pressure_Pa: float = TANK_PRESSURE_PA
    name: ClassVar[str] = FLOW_LIMITED_LAW

    @staticmethod
    def rod_compliance_m3_Pa(annulus_area_m2: float, head_stiffness_N_m: float,
                             rod_stiffness_N_m: float) -> float:
        """``C_r = A_ann^2 (1 / k_r + 1 / k_h)``: rod-chamber oil per pressure change, the head
        column included (B hose not included, ASSUMPTION)."""
        return annulus_area_m2**2 * (1.0 / rod_stiffness_N_m + 1.0 / head_stiffness_N_m)

    def rod_pressure_Pa(self, previous_Pa: float, target_Pa: float, speed_m_s: float,
                        step_s: float, lag_s: float, compliance_m3_Pa: float,
                        head_area_m2: float, annulus_area_m2: float, is_retract: bool) -> float:
        """:func:`flow_limited_rod_pressure` with these constants."""
        return flow_limited_rod_pressure(
            previous_Pa, target_Pa, speed_m_s, step_s, lag_s, compliance_m3_Pa, head_area_m2,
            annulus_area_m2, is_retract, meter_out_ratio=self.meter_out_ratio,
            spool_reference_drop_Pa=self.spool_reference_drop_Pa,
            tank_pressure_Pa=self.tank_pressure_Pa)

    def meta(self) -> dict[str, Any]:
        return {"law": self.name,
                "rule": "moving p_r: lag to p* capped by the valve flow; retract meter-in "
                        "A_ann |u|, extend meter-out b_T A_h |u| sqrt((p_r - p_T) / dp_c); "
                        "C_r = A_ann^2 (1/k_r + 1/k_h), B hose not included",
                "meter_out_ratio": self.meter_out_ratio,
                "spool_reference_drop_Pa": self.spool_reference_drop_Pa,
                "tank_pressure_Pa": self.tank_pressure_Pa,
                "status": "ASSUMPTION b_T, dp_c, p_T (coupled/params.py values)"}


class RodReleaseShift:
    """Reference shift per step and its record (module docstring).

    Args:
        annulus_area_m2: ``A_ann`` per leg.
    """

    def __init__(self, annulus_area_m2: ArrayLike) -> None:
        self._annulus_area_m2 = np.array(annulus_area_m2, dtype=float).reshape(-1)
        leg_count = self._annulus_area_m2.size
        self._previous_pressure_Pa: NDArray[np.float64] | None = None
        self._shift_total_m = np.zeros(leg_count)
        self._clipped_steps = np.zeros(leg_count, dtype=np.int64)
        self._clip_times_s: list[list[float]] = [[] for _ in range(leg_count)]

    @property
    def shift_total_m(self) -> NDArray[np.float64]:
        """Accumulated shift per leg: it moves the stroke reading too (spec 2.3)."""
        return self._shift_total_m.copy()

    @property
    def clipped_steps(self) -> NDArray[np.int64]:
        return self._clipped_steps.copy()

    @property
    def clip_times_s(self) -> list[list[float]]:
        """Per leg the step times of the clipped steps that were given a ``t_s`` (v5 criteria
        rev. 2 2.1: split before / after the first lift-off). Not part of the snapshot."""
        return [list(times) for times in self._clip_times_s]

    def forget_pressure(self) -> None:
        """The next call starts from its own pressure (rod law disarmed: no pressure exists)."""
        self._previous_pressure_Pa = None

    def seed_pressure(self, leg: int, pressure_Pa: float) -> None:
        """Previous pressure of ``leg``: M1c has already moved the reference to this pressure."""
        if self._previous_pressure_Pa is not None:
            self._previous_pressure_Pa[leg] = pressure_Pa

    def shift_m(self, rod_pressure_Pa: ArrayLike, head_stiffness_N_m: ArrayLike,
                is_moving: ArrayLike, room_down_m: ArrayLike, room_up_m: ArrayLike,
                *, t_s: float | None = None) -> NDArray[np.float64]:
        """Advance one step; the amount to add to ``s_ref`` per leg [m].

        Args:
            rod_pressure_Pa: ``p_r`` of this step (before any pressure split floor).
            head_stiffness_N_m: ``k_h`` per leg.
            is_moving: False on locked legs.
            room_down_m: Allowed shift towards the lower limit, ``<= 0``.
            room_up_m: Allowed shift towards the upper limit, ``>= 0``.
            t_s: Step time; a clipped leg records it (:attr:`clip_times_s`). None = no time.
        """
        pressure_Pa = np.array(rod_pressure_Pa, dtype=float)
        previous_Pa = (pressure_Pa if self._previous_pressure_Pa is None
                       else self._previous_pressure_Pa)
        wanted_m = np.where(is_moving, self._annulus_area_m2 * (previous_Pa - pressure_Pa)
                            / np.asarray(head_stiffness_N_m, dtype=float), 0.0)
        shift_m = np.clip(wanted_m, room_down_m, room_up_m)
        is_clipped = shift_m != wanted_m
        self._clipped_steps += is_clipped
        if t_s is not None:
            for leg in np.flatnonzero(is_clipped):
                self._clip_times_s[leg].append(float(t_s))
        self._shift_total_m += shift_m
        self._previous_pressure_Pa = pressure_Pa
        return shift_m

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        arrays: dict[str, NDArray[Any]] = {SHIFT_TOTAL_KEY: self._shift_total_m.copy(),
                                           CLIPPED_STEPS_KEY: self._clipped_steps.copy()}
        if self._previous_pressure_Pa is not None:
            arrays[PREVIOUS_PRESSURE_KEY] = self._previous_pressure_Pa.copy()
        return arrays

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """A snapshot without the keys continues from the current pressure with a zero record.
        The clip times are not in the snapshot: they restart empty."""
        leg_count = self._annulus_area_m2.size
        self._clip_times_s = [[] for _ in range(leg_count)]
        self._previous_pressure_Pa = None
        if PREVIOUS_PRESSURE_KEY in arrays:
            self._previous_pressure_Pa = np.array(arrays[PREVIOUS_PRESSURE_KEY], dtype=float)
        self._shift_total_m = np.array(arrays.get(SHIFT_TOTAL_KEY, np.zeros(leg_count)),
                                       dtype=float)
        self._clipped_steps = np.array(arrays.get(CLIPPED_STEPS_KEY, np.zeros(leg_count)),
                                       dtype=np.int64)

    def record(self) -> dict[str, Any]:
        """Per-leg totals for the run summary."""
        return {"m2_shift_total_mm": (self._shift_total_m * 1e3).tolist(),
                "m2_clipped_steps": self._clipped_steps.tolist()}


__all__ = ["CLIPPED_STEPS_KEY", "FLOW_LIMITED_LAW", "METER_OUT_RATIO", "PREVIOUS_PRESSURE_KEY",
           "SHIFT_TOTAL_KEY", "SPOOL_REFERENCE_DROP_PA", "TANK_PRESSURE_PA", "RodPressureFlowLaw",
           "RodReleaseShift", "flow_limited_rod_pressure"]
