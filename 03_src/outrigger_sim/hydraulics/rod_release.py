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

Revision 4 (``flow_limited_r4``, user decision 2026-11-07, hydraulics-expert P-1): the base L1-R
release decay ``G_r exp(-(t - t_rel) / tau)`` already moves the share of the rod pressure that
built up while the leg was locked (``p_r0 - p_r,rel``, about 1.06 mm on a lifted leg). M2 moves
only the change from the lock anchor ``p_r0`` to ``p*``, so it reads the pressure plus the part of
that share the base decay still carries (:func:`compensated_rod_pressure_Pa`)::

    Delta = p_r0 - p_r,rel = G_r(t_rel) / A_ann    set at the release, cleared at the lock
    w^k   = exp(-(t_k - t_rel) / tau)               the base release decay weight
    p_hat^k = p_r^k + Delta w^k
    d s_ref^k = A_ann (p_hat^(k-1) - p_hat^k) / k_h,   p_hat before the release step = start + Delta

``p_r`` itself (the reading, the lag start ``p_r,rel`` or the M1c seed) is unchanged; with a seed
``Delta`` stays as it is (spec P-1). The move over a whole release is ``A_ann (p_r0 - p*) / k_h``.

Revision 5 (``flow_limited_r5``, user decision 2026-11-07, plan B): the lock anchor after an
extension keeps the rod pressure the moving lag had not yet relieved::

    p_r0 = max(min(p_tr, p_ext + max(p_tr - p*, 0)), p_floor)    extension lock, M2 on only
    p_tr = moving rod pressure of the last step,  p* = moving target of the extension

The upper cap ``p_tr`` (hydraulics-expert 2026-11-07) keeps the anchor at or below the tracked
pressure when ``p_ext > p*``. A finished (or hanging) extension has ``p_tr = p*`` and keeps
``p_r0 = min(p*, p_ext)``, which is ``p_ext`` in the YAML conditions (``p* > p_ext``). Retract locks
keep ``p_ret``. The anchor is set by the plant laws (L2b ``l2b_rod_side``, harness
``harness_hydraulics``); this module carries the name of the law and its snapshot marker
(:data:`LAW_REVISION_KEY`).

Revision 6 (``flow_limited_r6``, 436.9 P3 ``rod_flow_cap_all``, harness only; hydraulics-expert
``hydraulics_remedy_review.md`` 1): the r5 lag-only branches get a flow cap too
(:func:`flow_limited_rod_pressure_r6`); r5 stays as it is.

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
"""Previous compensated pressure ``p_hat^(k-1)`` (revision 4)."""
SHIFT_TOTAL_KEY = "m2_shift_total_m"
CLIPPED_STEPS_KEY = "m2_clipped_steps"
RELEASE_DROP_KEY = "m2_release_drop_Pa"
"""Optional snapshot keys (written only with the option on)."""
LAW_REVISION_KEY = "m2_law_revision"
"""Snapshot marker of the M2 law (a snapshot payload holds numbers only, so the revision number
stands for :data:`FLOW_LIMITED_LAW`). Snapshots before revision 5 have no marker."""

FLOW_LIMITED_LAW = "flow_limited_r5"
"""Name of the M2 law in the meta and the definition digests (M2 on only): revision 3 pressure
lag, revision 4 release-decay compensation and the revision 5 extension lock anchor."""
LAW_REVISION = 5
"""Revision number of :data:`FLOW_LIMITED_LAW` (snapshot marker)."""
FLOW_LIMITED_R6_LAW = "flow_limited_r6"
"""436.9 plant option P3 (``rod_flow_cap_all``, ``jp3_remedy_spec.md`` 3): the r5 law with a flow
cap on all four branches (:func:`flow_limited_rod_pressure_r6`). Harness only."""
STORED_LAWS = ("flow_limited_r3", "flow_limited_r4", FLOW_LIMITED_LAW, FLOW_LIMITED_R6_LAW)
"""M2 law names stored results may carry; only :data:`RERUNNABLE_LAWS` can be rerun."""
RERUNNABLE_LAWS = (FLOW_LIMITED_LAW, FLOW_LIMITED_R6_LAW)
"""Laws this code runs: r5 (M2 on) and r6 (M2 with ``rod_flow_cap_all``)."""
_M2_STATE_KEYS = (PREVIOUS_PRESSURE_KEY, SHIFT_TOTAL_KEY, CLIPPED_STEPS_KEY, RELEASE_DROP_KEY)
METER_OUT_RATIO = 1.0
"""``b_T``: meter-out (A -> T) over meter-in (P -> A) opening at the same spool stroke
(ASSUMPTION)."""
SPOOL_REFERENCE_DROP_PA = 10.0e5
"""``dp_c``: spool drop at which the opening passes ``A_h |u|`` (compensator drop, ASSUMPTION)."""
TANK_PRESSURE_PA = 2.0e5
"""``p_T``: return line pressure, gauge (ASSUMPTION)."""

# --- P3 (flow_limited_r6), hydraulics_remedy_review.md 1 / 5 (hydraulics-expert 2026-11-16) ------
R6_LAW_REVISION = 6
"""Snapshot marker of :data:`FLOW_LIMITED_R6_LAW` (review 1.5: a r5 snapshot never continues r6)."""
RETRACT_DRAIN_MIN_DROP_PA = 0.5e5
"""Guard of branch (c): ``p_bA - p_T`` below this raises (review 1.5, no silent clip)."""
R6_RULE = ("r5 branches (a) retract rise and (b) extend relief unchanged; (c) retract relief "
           "p >= p - A_ann |u| (sqrt((p_h - p_T)+ / (p_bA - p_T)) - 1)+ dt / C_r, "
           "p_h = (F + A_ann p) / A_h, A->T calibrated on p_bA (b_T,ret = sqrt(dp_c / "
           "(p_bA - p_T)) = 1.826); (d) extend rise p <= max(p + A_ann |u| dt / C_r, lag to "
           "p_F = -F / A_ann when p_F > p)")
"""Meta rule of the r6 branches (review 1.1)."""


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


def flow_limited_rod_pressure_r6(
    previous_Pa: float,
    target_Pa: float,
    speed_m_s: float,
    step_s: float,
    lag_s: float,
    compliance_m3_Pa: float,
    head_area_m2: float,
    annulus_area_m2: float,
    is_retract: bool,
    cylinder_force_N: float,
    head_back_retract_Pa: float,
    *,
    meter_out_ratio: float = METER_OUT_RATIO,
    spool_reference_drop_Pa: float = SPOOL_REFERENCE_DROP_PA,
    tank_pressure_Pa: float = TANK_PRESSURE_PA,
) -> float:
    """Moving rod pressure after one step of the r6 law (P3, ``rod_flow_cap_all``;
    ``hydraulics_remedy_review.md`` 1.1, reference ``hr01_p3_flow_law.r6``)::

        (a) retract, p* > p:  r5 (meter-in fill cap)
        (b) extend,  p* < p:  r5 (meter-out drain cap)
        (c) retract, p* < p:  max(lag, p - A_ann |u| f dt / C_r),
                              f = (sqrt((p_h - p_T)+ / (p_bA - p_T)) - 1)+
                              p_h = (F + A_ann p) / A_h      (fixed-load two-chamber balance)
        (d) extend,  p* > p:  min(lag, max(p + A_ann |u| dt / C_r, lag_F)),
                              lag_F = the lag towards p_F = -F / A_ann if p_F > p, else -inf
                              (a tension load pulls the rod side up; no valve flow limits it)

    A cap never passes the lagged value, so the step stays increasing in ``p^(k-1)`` (the ③
    bound argument; review 1.3: smallest slope 0.980).

    Args:
        previous_Pa .. is_retract: As :func:`flow_limited_rod_pressure`.
        cylinder_force_N: Net cylinder force ``F`` of the step.
        head_back_retract_Pa: ``p_bA`` (``RodChamberLegParams.p_head_back_retract_Pa``).

    Returns:
        ``p_r^k`` [Pa gauge].

    Raises:
        ValueError: Branch (c) with ``p_bA - p_T`` below :data:`RETRACT_DRAIN_MIN_DROP_PA`.
    """
    if (is_retract and target_Pa >= previous_Pa) or (not is_retract
                                                     and target_Pa <= previous_Pa):
        return flow_limited_rod_pressure(
            previous_Pa, target_Pa, speed_m_s, step_s, lag_s, compliance_m3_Pa, head_area_m2,
            annulus_area_m2, is_retract, meter_out_ratio=meter_out_ratio,
            spool_reference_drop_Pa=spool_reference_drop_Pa, tank_pressure_Pa=tank_pressure_Pa)
    keep = math.exp(-step_s / lag_s) if lag_s > 0.0 else 0.0
    lagged_Pa = target_Pa + (previous_Pa - target_Pa) * keep
    speed = abs(speed_m_s)
    if is_retract:  # (c)
        drain_drop_Pa = head_back_retract_Pa - tank_pressure_Pa
        if drain_drop_Pa < RETRACT_DRAIN_MIN_DROP_PA:
            raise ValueError(f"p_bA - p_T = {drain_drop_Pa} Pa < {RETRACT_DRAIN_MIN_DROP_PA} Pa "
                             "(flow_limited_r6 branch (c))")
        head_Pa = (cylinder_force_N + annulus_area_m2 * previous_Pa) / head_area_m2
        factor = max(math.sqrt(max(head_Pa - tank_pressure_Pa, 0.0) / drain_drop_Pa) - 1.0, 0.0)
        return max(lagged_Pa, previous_Pa - annulus_area_m2 * speed * factor * step_s
                   / compliance_m3_Pa)
    tension_Pa = -cylinder_force_N / annulus_area_m2  # (d)
    lag_tension_Pa = (tension_Pa + (previous_Pa - tension_Pa) * keep if tension_Pa > previous_Pa
                      else -math.inf)
    return min(lagged_Pa, max(previous_Pa + annulus_area_m2 * speed * step_s / compliance_m3_Pa,
                              lag_tension_Pa))


def release_weight(elapsed_s: float, decay_s: float) -> float:
    """``w = exp(-max(t - t_rel, 0) / tau)``: the share of ``G_r(t_rel)`` the base release decay
    still carries (``RodSidePlant`` on the harness; L2b reads ``RodChamberLeg.release_decay``).

    Args:
        elapsed_s: ``t - t_rel``; not finite (no release yet) gives 0.
        decay_s: ``tau`` of the base release decay; 0 gives 0 (the decay is cut in one step).
    """
    if not math.isfinite(elapsed_s) or decay_s == 0.0:
        return 0.0
    return math.exp(-max(elapsed_s, 0.0) / decay_s)


def compensated_rod_pressure_Pa(pressure_Pa: ArrayLike, release_drop_Pa: ArrayLike,
                                weight: ArrayLike) -> NDArray[np.float64]:
    """``p_hat = p_r + Delta w`` per leg: the pressure M2 moves ``s_ref`` by (revision 4).

    Args:
        pressure_Pa: ``p_r`` (the revision 3 lag on moving legs).
        release_drop_Pa: ``Delta = p_r0 - p_r,rel`` of the last release, 0 on locked legs.
        weight: ``w`` of :func:`release_weight`.
    """
    return (np.asarray(pressure_Pa, dtype=float)
            + np.asarray(release_drop_Pa, dtype=float) * np.asarray(weight, dtype=float))


@dataclass(frozen=True)
class ReleaseStart:
    """A leg that left its lock in this step (L2b: ``L2bRodSide.releases_of_last_call``).

    Attributes:
        start_pressure_Pa: Start of the moving pressure lag (``p_r,rel`` or the M1c seed).
        drop_Pa: ``Delta = p_r0 - p_r,rel`` at the release instant (not changed by a seed).
    """

    start_pressure_Pa: float
    drop_Pa: float


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
                        "C_r = A_ann^2 (1/k_r + 1/k_h), B hose not included; "
                        "M2 reads p_hat = p_r + Delta w, Delta = p_r0 - p_r,rel at the release, "
                        "w = base release decay (revision 4); extension lock anchor "
                        "p_r0 = max(min(p_tr, p_ext + max(p_tr - p*, 0)), p_floor), p_tr = "
                        "moving rod "
                        "pressure before the lock, p* = extension target; retract lock "
                        "keeps p_ret (revision 5)",
                "meter_out_ratio": self.meter_out_ratio,
                "spool_reference_drop_Pa": self.spool_reference_drop_Pa,
                "tank_pressure_Pa": self.tank_pressure_Pa,
                "status": "ASSUMPTION b_T, dp_c, p_T (coupled/params.py values)"}


@dataclass(frozen=True)
class RodPressureFlowLawR6(RodPressureFlowLaw):
    """P3 law ``flow_limited_r6`` (:func:`flow_limited_rod_pressure_r6`); the harness picks it
    with ``rod_flow_cap_all``. The r5 class and its function stay as they are (the ③ tracker
    and the plants without P3 call them)."""

    name: ClassVar[str] = FLOW_LIMITED_R6_LAW
    law_revision: ClassVar[int] = R6_LAW_REVISION

    def rod_pressure_with_force_Pa(self, previous_Pa: float, target_Pa: float,
                                   speed_m_s: float, step_s: float, lag_s: float,
                                   compliance_m3_Pa: float, head_area_m2: float,
                                   annulus_area_m2: float, is_retract: bool,
                                   cylinder_force_N: float,
                                   head_back_retract_Pa: float) -> float:
        """:func:`flow_limited_rod_pressure_r6` with these constants."""
        return flow_limited_rod_pressure_r6(
            previous_Pa, target_Pa, speed_m_s, step_s, lag_s, compliance_m3_Pa, head_area_m2,
            annulus_area_m2, is_retract, cylinder_force_N, head_back_retract_Pa,
            meter_out_ratio=self.meter_out_ratio,
            spool_reference_drop_Pa=self.spool_reference_drop_Pa,
            tank_pressure_Pa=self.tank_pressure_Pa)

    def meta(self) -> dict[str, Any]:
        return {**super().meta(), "law": self.name, "rule_r6": R6_RULE,
                "b_T_ret_equivalent": "sqrt(dp_c / (p_bA - p_T)) = 1.826 at p_bA 5 bar",
                "status": "ASSUMPTION b_T, dp_c, p_T, p_bA (hydraulics_remedy_review.md 1, 5)"}


def _check_law_revision(arrays: Mapping[str, NDArray[Any]],
                        expected: int = LAW_REVISION) -> None:
    """Refuse M2 state of another law revision; a snapshot without M2 keys passes."""
    if not any(key in arrays for key in _M2_STATE_KEYS):
        return
    if LAW_REVISION_KEY not in arrays:
        raise ValueError(f"snapshot M2 state has no law marker (revision 4 or older), "
                         f"this code runs revision {expected}")
    stored = np.asarray(arrays[LAW_REVISION_KEY]).reshape(-1)
    if stored.size != 1 or int(stored[0]) != expected:
        raise ValueError(f"snapshot M2 law revision {stored.tolist()} is not {expected}")


class RodReleaseShift:
    """Reference shift per step and its record (module docstring).

    Args:
        annulus_area_m2: ``A_ann`` per leg.
        law_revision: Snapshot marker of the moving law (:data:`LAW_REVISION`, or
            :data:`R6_LAW_REVISION` with P3).
    """

    _law_revision: int = LAW_REVISION
    """Class default for objects pickled before the marker became per instance."""

    def __init__(self, annulus_area_m2: ArrayLike, law_revision: int = LAW_REVISION) -> None:
        self._law_revision = int(law_revision)
        self._annulus_area_m2 = np.array(annulus_area_m2, dtype=float).reshape(-1)
        leg_count = self._annulus_area_m2.size
        self._previous_pressure_Pa: NDArray[np.float64] | None = None
        """``p_hat^(k-1)`` per leg (None: the next call starts from its own pressure)."""
        self._release_drop_Pa = np.zeros(leg_count)
        """``Delta`` of the last release per leg; 0 while locked."""
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

    @property
    def release_drop_Pa(self) -> NDArray[np.float64]:
        """``Delta`` per leg (0 while locked)."""
        return self._release_drop_Pa.copy()

    def forget_pressure(self) -> None:
        """The next call starts from its own pressure (rod law disarmed: no pressure exists)."""
        self._previous_pressure_Pa = None
        self._release_drop_Pa[:] = 0.0

    def release(self, leg: int, start: ReleaseStart) -> None:
        """``leg`` leaves its lock in this step: set ``Delta`` and ``p_hat`` before the step.

        ``p_hat^(k-1) = start + Delta`` (``p_r0`` without an M1c seed): the move of the whole
        release is then ``A_ann (p_hat^(k-1) - p*) / k_h``. Call before :meth:`shift_m` of the
        release step.
        """
        self._release_drop_Pa[leg] = start.drop_Pa
        if self._previous_pressure_Pa is not None:
            self._previous_pressure_Pa[leg] = start.start_pressure_Pa + start.drop_Pa

    def shift_m(self, rod_pressure_Pa: ArrayLike, head_stiffness_N_m: ArrayLike,
                is_moving: ArrayLike, room_down_m: ArrayLike, room_up_m: ArrayLike,
                *, release_weight: ArrayLike | None = None,
                t_s: float | None = None) -> NDArray[np.float64]:
        """Advance one step; the amount to add to ``s_ref`` per leg [m].

        A locked leg does not shift and its ``Delta`` is cleared (the lock ends the release).

        Args:
            rod_pressure_Pa: ``p_r`` of this step (before any pressure split floor).
            head_stiffness_N_m: ``k_h`` per leg.
            is_moving: False on locked legs.
            room_down_m: Allowed shift towards the lower limit, ``<= 0``.
            room_up_m: Allowed shift towards the upper limit, ``>= 0``.
            release_weight: ``w`` per leg (:func:`release_weight`); None only while no leg has
                a ``Delta``.
            t_s: Step time; a clipped leg records it (:attr:`clip_times_s`). None = no time.

        Raises:
            ValueError: A leg has a ``Delta`` and no ``release_weight`` was given.
        """
        self._release_drop_Pa[~np.asarray(is_moving, dtype=bool)] = 0.0
        if release_weight is None:
            if np.any(self._release_drop_Pa != 0.0):
                raise ValueError("a released leg needs the release weight w (revision 4)")
            release_weight = np.zeros_like(self._release_drop_Pa)
        pressure_Pa = compensated_rod_pressure_Pa(rod_pressure_Pa, self._release_drop_Pa,
                                                  release_weight)
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
                                           CLIPPED_STEPS_KEY: self._clipped_steps.copy(),
                                           RELEASE_DROP_KEY: self._release_drop_Pa.copy(),
                                           LAW_REVISION_KEY: np.array([self._law_revision])}
        if self._previous_pressure_Pa is not None:
            arrays[PREVIOUS_PRESSURE_KEY] = self._previous_pressure_Pa.copy()
        return arrays

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """A snapshot without the keys continues from the current pressure with a zero record.
        The clip times are not in the snapshot: they restart empty.

        Raises:
            ValueError: The snapshot has M2 keys of another law revision (a snapshot without
                the marker is revision 4 or older).
        """
        _check_law_revision(arrays, self._law_revision)
        leg_count = self._annulus_area_m2.size
        self._clip_times_s = [[] for _ in range(leg_count)]
        self._previous_pressure_Pa = None
        if PREVIOUS_PRESSURE_KEY in arrays:
            self._previous_pressure_Pa = np.array(arrays[PREVIOUS_PRESSURE_KEY], dtype=float)
        self._shift_total_m = np.array(arrays.get(SHIFT_TOTAL_KEY, np.zeros(leg_count)),
                                       dtype=float)
        self._clipped_steps = np.array(arrays.get(CLIPPED_STEPS_KEY, np.zeros(leg_count)),
                                       dtype=np.int64)
        self._release_drop_Pa = np.array(arrays.get(RELEASE_DROP_KEY, np.zeros(leg_count)),
                                         dtype=float)

    def record(self) -> dict[str, Any]:
        """Per-leg totals for the run summary."""
        return {"m2_shift_total_mm": (self._shift_total_m * 1e3).tolist(),
                "m2_clipped_steps": self._clipped_steps.tolist()}


__all__ = ["CLIPPED_STEPS_KEY", "FLOW_LIMITED_LAW", "FLOW_LIMITED_R6_LAW", "LAW_REVISION",
           "LAW_REVISION_KEY", "METER_OUT_RATIO", "PREVIOUS_PRESSURE_KEY", "RELEASE_DROP_KEY",
           "R6_LAW_REVISION", "RERUNNABLE_LAWS", "RETRACT_DRAIN_MIN_DROP_PA", "SHIFT_TOTAL_KEY",
           "STORED_LAWS", "SPOOL_REFERENCE_DROP_PA",
           "TANK_PRESSURE_PA", "ReleaseStart", "RodPressureFlowLaw", "RodPressureFlowLawR6",
           "RodReleaseShift", "compensated_rod_pressure_Pa", "flow_limited_rod_pressure",
           "flow_limited_rod_pressure_r6", "release_weight"]
