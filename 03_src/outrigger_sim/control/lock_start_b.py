"""Edition 6 lock-start compensation (A) and event response order (B) of the C2 controller.

``06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v6.md`` 3 (draft, not sealed) with the
reviews the user adopted on 2026-11-23: stats (``ed6_design/stats_v6/stats_v6_summary.md``:
E3 stall witness, dead-beat fill command, thresholds) and hydraulics
(``ed6_design/hydraulics_v6/h6_review_report.md``, which wins where the two overlap: look-ahead
fill, the two-chamber void, the robust lower-bound set recomputed every period, the rod-pressure
witness, extension off, the A(i) ramp). Three components, each off unless named in
:attr:`LockStartBSettings.components`:

=======  ==========================================  ========================================
name     rule                                        where it acts (``C2Controller``)
=======  ==========================================  ========================================
``A_i``  3.1 adaptive LEVEL dead-band compensation:  output stage, after the phase command
         a leg commanded one way that does not       (every LEVEL period) and before the
         move gets a rising command floor            stroke-end slowdown and the increment
                                                     limit
``A_ii`` 3.2 lock-start fill: a leg leaving its      same stage (every phase but FAULT,
         lock gets the dead-beat fill command,       FAULT_REGROUND and IDLE); retraction
         planned so that the commanded travel,       only by default (extension is an
         its ramp-down included, lands on the        option)
         dead-stroke lower bound
``B``    3.3 event response order after an R-5       LEVEL step, after the re-approach
         ``relevel_predicted:<leg>``: B1 no          speeds and before the pre-LOC pause,
         retraction of that leg and of every leg     LAS-b and the stroke-budget guard; B2
         with a low re-approach count; B2 (option,   in the re-approach start count
         off by default) fewer start samples
=======  ==========================================  ========================================

A only raises the magnitude of a command that already points that way (``|u| > u_hold``), so
the stroke-end clipping, the crawler-zone rule and a stopped leg keep their zero; the
stroke-end slowdown, the increment limit (0.25 ``v_max`` per period both ways, user decision
Q6-6) and the FAULT stop come after it. Legs the crawler-zone rule or the stroke-end clipping
changed in this period, every leg in a period the stroke-budget guard acted, and an extending
leg the raised speed would bring into the guard's look-ahead keep their command (spec 3.1
priority).

Stall witness of A(i) (stats E3): the mean of the last three stroke reads minus the mean of
the first three reads of the stretch. The A(ii) motion witnesses use single reads (spec 3.2,
hydraulics 3).

Edition 7 (``jp3_remedy_spec_v7.md`` 3.1) adds ``A_ib``, the second trigger path of A(i): a
LEVEL leg whose acting command stays inside the dead band (``0 < |u| <= u_hold``, one sign,
``N_blind`` periods) without moving (E3 from read ``k_s + 2`` less than ``s_still``), while the
completion condition 3 is open, gets a floor ``u_hold + Delta u_step`` rising by
``Delta u_step`` per period to ``u_cap`` (A(i) values), whatever ``|u|`` is; a predictive load
protection holds a shot back and a reversal latch switches the leg off. Its fields (``ib_*``)
stay at their defaults and out of the meta while ``A_ib`` is off, so an edition 6 run is
unchanged (P7-0).

Every threshold is a field of :class:`LockStartBSettings` (defaults: the adopted review
values). Off (``components`` empty), no line of this module runs in the controller (P6-0).

Units SI: speeds m/s, strokes m, pressures gauge Pa, forces N. Leg order FL, FR, RL, RR.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead
from outrigger_sim.params import LEG_ORDER

LEG_COUNT = 4
WITNESS_READS = 3
"""E3: reads averaged at each end of an A(i) stall displacement."""
TIME_MATCH_TOLERANCE_S = 1.0e-6
"""A trace row belongs to a read time when the two differ by less than this."""
PLAN_TOLERANCE_M = 1.0e-12
ROD_FLOOR_PA = 0.1e5 - 1.01325e5
"""0.1 bar abs as gauge: the lowest rod pressure (the L1-R / M2 floor)."""
NO_LEG = -1
CAP_EVENT = "INFO_LSB_CAP"
"""Spec 3.1: an A(i) floor that stayed at ``u_cap`` for ``N_cap`` periods ends with this event
(``INFO_LSB_CAP:<leg>``)."""
TRACE_ARRAY_PREFIX = "lsb_"
"""T4h array names of the per-read record (``lsb_<field>``)."""


class LsbComponent(StrEnum):
    """The edition 6 components (spec 3, names of the ``lsb_components`` meta) and the
    edition 7 blind-band fill ``A_ib``."""

    DEADBAND = "A_i"
    """3.1 adaptive LEVEL dead-band compensation."""
    BLIND_FILL = "A_ib"
    """Edition 7 (``jp3_remedy_spec_v7.md`` 3.1): the second trigger path of A(i) for a leg
    commanded inside the dead band (``0 < |u| <= u_hold``) that does not move."""
    FILL_FLOOR = "A_ii"
    """3.2 lock-start fill (dead-beat command)."""
    EVENT_BLOCK = "B1"
    """3.3 B1: no retraction of the predicted leg (and the low-count legs) after R-5."""
    PRE_TWIST = "B3"
    """3.3 B3 (spec revision 1): the R-5 pre-twist toward the predicted leg."""


EVENT_COMPONENTS = (LsbComponent.EVENT_BLOCK, LsbComponent.PRE_TWIST)
"""The B components (spec 3.3 "B" = B1 + B3; B2 is an option of these)."""
EVENT_ALIAS = "B"
"""Input alias of :data:`EVENT_COMPONENTS` (``components=("B",)`` = B1 + B3)."""


COMPONENT_ORDER = tuple(LsbComponent)
"""Canonical order of :attr:`LockStartBSettings.components` (A_i, A_ib, A_ii, B1, B3)."""

BLIND_LATCH_EVENT = "INFO_LSB_BLIND_LATCH"
"""Edition 7 3.1: more than ``ib_latch_reversals`` opposite-sign A(i)-b triggers of one leg in
one LEVEL stretch switch A(i)-b off for that leg (``INFO_LSB_BLIND_LATCH:<leg>``)."""
BLIND_PROTECT_EVENT = "INFO_LSB_BLIND_PROTECT"
"""Edition 7 3.1: the predictive load protection held a trigger back (once per stretch)."""


class BlindCondition(StrEnum):
    """Edition 7 3.1 condition 3 of the A(i)-b trigger (probe arms 2 .. 4)."""

    WITH_TWIST = "with_twist"
    """(다), the sealed draft: attitude or clearance condition open, or ``|D|`` above the
    relax limit."""
    ATTITUDE_CLEARANCE = "attitude_clearance"
    """(나): attitude or clearance condition open."""
    LEVEL_INCOMPLETE = "level_incomplete"
    """First draft: the period's LEVEL completion test (twist included) failed."""


class BlindEnd(StrEnum):
    """Why an A(i)-b floor ended (edition 7 3.1 record values)."""

    MOVED = "moved"
    SIGN = "sign"
    ZERO = "zero"
    PHASE = "phase"
    CAP = "cap"


ED7_FIELD_PREFIX = "ib_"
"""Fields of the edition 7 A(i)-b; a run without ``A_ib`` keeps them at their defaults and
leaves them out of :meth:`LockStartBSettings.to_meta` (edition 6 metas unchanged, P7-0)."""


@dataclass(frozen=True)
class CompletionFlags:
    """The LEVEL completion tests of one period (``C2Controller._update_completion``), the
    inputs of condition 3 of A(i)-b."""

    is_on_target: bool
    is_clearance_done: bool
    is_complete: bool
    """The period's completion test with its twist condition (before the hold time)."""


class A1End(StrEnum):
    """Why an A(i) floor ended (spec 3.1)."""

    MOVED = "moved"
    SIGN = "sign"
    HOLD = "hold"
    PHASE = "phase"
    CAP = "cap"


class A2End(StrEnum):
    """Why an A(ii) fill ended (spec 3.2, hydraulics 3)."""

    FILLED = "filled"
    MOVED = "moved"
    ROD_WITNESS = "rod_witness"
    HOLD_TIMEOUT = "hold_timeout"
    SIGN = "sign"
    HOLD = "hold"
    FAULT = "fault"


class BEnd(StrEnum):
    """Why a B1 episode ended (spec 3.3)."""

    LOAD = "load"
    CONTACT = "contact"
    PHASE = "phase"
    REPLACED = "replaced"


class B3End(StrEnum):
    """Why a B3 pre-twist ended (spec revision 4 3.3 record values ``handover``,
    ``resolved``, ``travel_cap``, ``protect``, ``phase``; two more for edge cases)."""

    HANDOVER = "handover"
    """The formal re-approach of the predicted leg started (it takes over the same rate)."""
    RESOLVED = "resolved"
    """The leg read at least P5 without falling for ``b3_end_periods`` periods (stats s30)."""
    TRAVEL_CAP = "travel_cap"
    """The commanded twist travel limit (or the period limit ``b3_max_periods``)."""
    PHASE = "phase"
    PROTECT = "protect"
    """A leg the pre-twist unloads read below the B3 protection level (dynamics review); the
    pre-twist does not start again in this LEVEL stretch (the formal re-approach rules keep
    the leg)."""
    OTHER_REAPPROACH = "other_reapproach"
    """Another leg's re-approach started (single-leg rule; beyond the spec values)."""
    REPLACED = "replaced"
    """A new R-5 prediction (beyond the spec values)."""


@dataclass(frozen=True)
class LockStartBSettings:
    """Edition 6 settings; the class default (no component) is off.

    The spec 3 placeholders are fields with the adopted review values (user decisions
    2026-11-23); every field can be changed per run (``HydraulicOptions.lsb_parameters``).
    The A(ii) lower-bound values are the hydraulics "robust" set.
    """

    components: tuple[str, ...] = ()
    """Components on, in :data:`COMPONENT_ORDER`; empty = off."""
    hold_speed_ratio: float = 0.01
    """``u_hold / v_max`` (spec conventions: 0.209243 mm/s)."""
    # --- A(i), spec 3.1 (stats trigger, hydraulics ramp) ---
    a1_trigger_periods: int = 10
    """``N_trig``: periods of one acting direction before a trigger."""
    a1_trigger_travel_m: float = 0.5e-3
    """``D_trig``: commanded travel ``sum |u| T`` of the stretch."""
    a1_motion_ratio: float = 0.25
    """``eta``: the stretch moved (E3) less than this share of its commanded travel."""
    a1_witness_m: float = 0.4e-3
    """``s_w,A`` (E3): travel in the commanded direction that ends the floor."""
    a1_step_m_s: float = 0.2e-3
    """``Delta u_step`` per period (hydraulics 5)."""
    a1_cap_m_s: float = 1.05e-3
    """``u_cap`` (hydraulics 5: 0.05 ``v_max``, 1.25 times the release threshold limit)."""
    a1_cap_periods: int = 50
    """``N_cap``: periods at ``u_cap`` before the floor ends with the event (user decision
    2026-11-23: 50; hydraulics 5 asked for at least 40)."""
    # --- A(ii), spec 3.2 ---
    a2_extend: bool = False
    """Fill an extension start too (hydraulics 2: off, an option)."""
    a2_lock_periods: int = 2
    """``N_lock``: previous acting commands all at or below ``u_hold``."""
    a2_fill_factor: float = 1.0
    """``kappa_fill`` (hydraulics 1: 1.0 with the robust set)."""
    a2_fill_speed_ratio: float = 1.0
    """Largest fill command over ``v_max`` (the plan never commands more)."""
    a2_hold_after_fill_s: float | None = None
    """Probe variant (hydraulics 4): once the plan comes down to one increment, hold one
    increment as a speed floor until a motion witness, for at most this long; None = off."""
    a2_psi: float = 6.0
    a2_bulk_modulus_Pa: float = 1.6e9
    """Cylinder oil bulk modulus of the dead-stroke formula (lower-bound side)."""
    a2_line_volume_m3: float = 0.5 * 285e-6
    a2_hose_bulk_modulus_Pa: float = 1.0e9
    a2_crack_Pa: float = 1.0e5
    a2_tank_Pa: float = 2.0e5
    """Tank back pressure (harness ``params.p_T``, 2 bar)."""
    a2_rod_dead_length_m: float = 0.02
    a2_head_dead_length_m: float = 0.05
    a2_friction_band_N: tuple[float, ...] = (16.0e3, 16.0e3, 13.328e3, 13.328e3)
    """Seal friction band per leg: 2 ``F_s,max`` (8 kN front, x 0.833 rear)."""
    a2_reading_margin_Pa: float = 4.0e5
    """Pressure reading margin: the bound reads ``p_h - e`` and ``p_r + e``."""
    a2_void_estimate: bool = True
    """Add the two-chamber void ``max(0, ((L_0h + s_0)(p_h - p_h0) + (L_0r + s_max - s_0)
    (p_r - p_r0)) / beta)`` from the lock anchor read (hydraulics 1)."""
    a2_void_head_bulk_modulus_Pa: float = 1.6e9
    a2_void_rod_bulk_modulus_Pa: float = 0.69e9
    a2_retract_witness_m: float = 1.0e-3
    """Retract stroke witness (single reads)."""
    a2_rod_witness_min_Pa: float = 3.0e5
    a2_rod_witness_ratio: float = 0.5
    """Rod witness ``p_r(k) - min p_r >= max(min, ratio (p_open,lb - p_r(k_s)))``."""
    a2_extend_witness_m: float = 1.0e-3
    """``s_w,ext`` (single reads, hydraulics 3)."""
    a2_on_fallback_legs: bool = False
    """Spec 3.2 (proposed off): a rod-side fallback leg takes no fill."""
    # --- B, spec 3.3 (stats) ---
    b1_exit_margin_N: float = 2.0e3
    """``m_B``: B1 ends once the predicted leg reads ``F_min`` plus this."""
    b1_exit_samples: int = 3
    """``N_B``: consecutive samples at the exit level."""
    b2_required_samples: int | None = None
    """B2 ``required_samples`` of the predicted leg; None = unchanged (stats Q-G: B2 off). The
    R8 preset re-approach starts on one low sample already (``LiftedReapproachSettings.samples``
    = 1), so 1 here changes nothing in the preset."""
    b3_end_periods: int = 2
    """``N_B3`` (stats s30, user decision 2026-11-23): the leg's lower load estimate at or
    above P5 and not below the previous period's, this many LEVEL periods in a row, ends the
    pre-twist (the R-5 prediction itself is computed in READY / PROBE only)."""
    b3_travel_cap_fraction: float = 0.065
    """Limit of the pre-twist's commanded twist travel of the leg (``|n_j tau_dot| T`` summed,
    not the measured stroke; dynamics review) as a multiple of the re-approach
    ``max_travel_m`` (stats s30: 0.065, about 2.6 mm). A period that would pass it ends the
    pre-twist first."""
    b3_max_periods: int | None = None
    """Option (dynamics review): the pre-twist ends after this many periods; None = off."""
    b3_protect_margin_N: float = 35.0e3
    """B3 protection (dynamics review): the pre-twist ends (``protect``) once a touched leg it
    unloads (``sign(n_i) != sign(n_j)``) reads below ``F_min`` plus this (about 44 kN). The
    re-approach keeps its own ``protect_margin_N``."""
    b3_protect_predictive: bool = False
    """Option: protect by ``F_lo - 2 dF >= F_min + b3_predictive_margin_N`` instead, with
    ``dF = k_tw |n_p| (n^T u) T`` the load the next period's pre-twist takes off leg p."""
    b3_predictive_margin_N: float = 5.0e3
    b3_twist_stiffness_N_m: float = 21.7e6
    """``k_tw`` of the predictive protection (dynamics review, harness value)."""
    # --- A(i)-b, edition 7 spec 3.1 (ramp values shared with A(i): a1_step / cap / witness) ---
    ib_blind_periods: int = 25
    """``N_blind``: periods of one acting sign with ``0 < |u| <= u_hold`` before a trigger."""
    ib_still_m: float = 0.1e-3
    """``s_still``: the stretch moved (E3, along its sign) less than this."""
    ib_reference_skip_reads: int = 2
    """The still reference is the mean of reads ``k_s + skip`` .. ``k_s + skip + 2`` (stats
    S1-2: the ``d`` = 1 tail of the command before stays out of the reference)."""
    ib_condition: str = BlindCondition.WITH_TWIST.value
    """Condition 3 (:class:`BlindCondition`; probe arms 3 and 4 take the other two)."""
    ib_twist_limit_N: float | None = None
    """``|D|`` limit of condition (다); None = the controller's relax ``max_twist_N``."""
    ib_latch_reversals: int = 2
    """More opposite-sign triggers than this in one LEVEL stretch latch the leg off."""
    ib_protect: bool = True
    """Predictive load protection (dynamics d7 2.5-5)."""
    ib_protect_travel_m: float = 0.85e-3
    """``Delta e_max``: the largest single shot."""
    ib_protect_stiffness_N_m: float = 41.0e6
    """``k_1`` (covers beta 1.6)."""
    ib_protect_margin_N: float = 5.0e3
    """A shot needs ``min_j(F_lo,j + k_1 n_i n_j sigma Delta e_max) >= F_min`` plus this."""
    ib_record_after_s: float = 1.0
    """Record only: ``Delta D`` / ``Delta F`` of a shot are taken this long after its end."""

    def __post_init__(self) -> None:
        names: list[str] = []
        for name in self.components:
            names += ([str(c) for c in EVENT_COMPONENTS] if name == EVENT_ALIAS else [name])
        components = tuple(str(LsbComponent(name)) for name in names)
        if len(set(components)) != len(components):
            raise ValueError(f"components repeat a name: {self.components!r}")
        ordered = tuple(str(name) for name in COMPONENT_ORDER if name in components)
        object.__setattr__(self, "components", ordered)
        bands = tuple(float(value) for value in self.a2_friction_band_N)
        if len(bands) != LEG_COUNT or min(bands) < 0.0:
            raise ValueError(f"a2_friction_band_N: {LEG_COUNT} values >= 0, got {bands!r}")
        object.__setattr__(self, "a2_friction_band_N", bands)
        _check_positive_ints(self, ("a1_trigger_periods", "a1_cap_periods", "a2_lock_periods",
                                    "b1_exit_samples", "b3_end_periods"))
        for name in ("b2_required_samples", "b3_max_periods"):
            if getattr(self, name) is not None:
                _check_positive_ints(self, (name,))
        _check_positive(self, (
            "hold_speed_ratio", "a1_trigger_travel_m", "a1_motion_ratio", "a1_witness_m",
            "a1_step_m_s", "a1_cap_m_s", "a2_fill_speed_ratio", "a2_psi", "a2_bulk_modulus_Pa",
            "a2_line_volume_m3", "a2_hose_bulk_modulus_Pa", "a2_void_head_bulk_modulus_Pa",
            "a2_void_rod_bulk_modulus_Pa", "a2_retract_witness_m", "a2_rod_witness_min_Pa",
            "a2_rod_witness_ratio", "a2_extend_witness_m", "b3_travel_cap_fraction",
            "b3_twist_stiffness_N_m"))
        _check_non_negative(self, ("a2_crack_Pa", "a2_tank_Pa", "a2_rod_dead_length_m",
                                   "a2_head_dead_length_m", "a2_reading_margin_Pa",
                                   "b1_exit_margin_N", "b3_protect_margin_N",
                                   "b3_predictive_margin_N"))
        if not 0.0 < self.a2_fill_factor <= 1.0:
            raise ValueError(f"a2_fill_factor must be in (0, 1], got {self.a2_fill_factor!r}")
        if self.a2_fill_speed_ratio > 1.0:
            raise ValueError("a2_fill_speed_ratio above 1 would command more than v_max")
        if self.a2_hold_after_fill_s is not None and not self.a2_hold_after_fill_s > 0.0:
            raise ValueError("a2_hold_after_fill_s must be > 0 or None")
        for name in ("a2_extend", "a2_void_estimate", "a2_on_fallback_legs",
                     "b3_protect_predictive", "ib_protect"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a bool")
        self._check_blind_fields()

    def _check_blind_fields(self) -> None:
        """Edition 7 fields: valid values, and none changed while ``A_ib`` is off."""
        object.__setattr__(self, "ib_condition", BlindCondition(self.ib_condition).value)
        _check_positive_ints(self, ("ib_latch_reversals",))
        minimum_periods = self.ib_reference_skip_reads + WITNESS_READS
        if (isinstance(self.ib_blind_periods, bool) or not isinstance(self.ib_blind_periods, int)
                or self.ib_blind_periods < minimum_periods):
            raise ValueError(f"ib_blind_periods must be an int >= {minimum_periods}")
        if (isinstance(self.ib_reference_skip_reads, bool)
                or not isinstance(self.ib_reference_skip_reads, int)
                or self.ib_reference_skip_reads < 0):
            raise ValueError("ib_reference_skip_reads must be an int >= 0")
        _check_positive(self, ("ib_still_m", "ib_protect_travel_m", "ib_protect_stiffness_N_m",
                               "ib_record_after_s"))
        _check_non_negative(self, ("ib_protect_margin_N",))
        if self.ib_twist_limit_N is not None and not self.ib_twist_limit_N > 0.0:
            raise ValueError("ib_twist_limit_N must be > 0 or None")
        if self.has(LsbComponent.BLIND_FILL):
            return
        defaults = LockStartBSettings.__dataclass_fields__
        changed = [name for name in blind_field_names()
                   if getattr(self, name) != defaults[name].default]
        if changed:
            raise ValueError(f"{changed} are A(i)-b fields: they need the A_ib component")

    @property
    def is_enabled(self) -> bool:
        return bool(self.components)

    def has(self, component: LsbComponent) -> bool:
        return str(component) in self.components

    @property
    def has_event_rules(self) -> bool:
        """A B component is on (the R-5 prediction starts an episode)."""
        return any(self.has(component) for component in EVENT_COMPONENTS)

    def to_meta(self) -> dict[str, Any]:
        """The fields; without ``A_ib`` the edition 7 fields are left out, so an edition 6
        meta (and its identity check) stays as it was (P7-0)."""
        values = asdict(self)
        values["components"] = list(self.components)
        values["a2_friction_band_N"] = list(self.a2_friction_band_N)
        if not self.has(LsbComponent.BLIND_FILL):
            for name in blind_field_names():
                del values[name]
        return values


def blind_field_names() -> tuple[str, ...]:
    """The edition 7 A(i)-b fields (:data:`ED7_FIELD_PREFIX`)."""
    return tuple(item.name for item in fields(LockStartBSettings)
                 if item.name.startswith(ED7_FIELD_PREFIX))


def parameter_names() -> tuple[str, ...]:
    """The fields a run may set besides ``components`` (``HydraulicOptions.lsb_parameters``)."""
    return tuple(item.name for item in fields(LockStartBSettings) if item.name != "components")


def _check_positive_ints(settings: LockStartBSettings, names: tuple[str, ...]) -> None:
    for name in names:
        value = getattr(settings, name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be an int >= 1, got {value!r}")


def _check_positive(settings: LockStartBSettings, names: tuple[str, ...]) -> None:
    for name in names:
        if not getattr(settings, name) > 0.0:
            raise ValueError(f"{name} must be > 0, got {getattr(settings, name)!r}")


def _check_non_negative(settings: LockStartBSettings, names: tuple[str, ...]) -> None:
    for name in names:
        if not getattr(settings, name) >= 0.0:
            raise ValueError(f"{name} must be >= 0, got {getattr(settings, name)!r}")


@dataclass(frozen=True)
class CylinderGeometry:
    """The controller values the rules need (per leg where an array)."""

    head_area_m2: NDArray[np.float64]
    annulus_area_m2: NDArray[np.float64]
    stroke_max_m: float
    max_speed_m_s: float
    period_s: float
    increment_limit_m_s: float | None = None
    """The controller's increment limit per period (None: no limit); the fill plan keeps it."""


@dataclass(frozen=True)
class LockAnchor:
    """The read at which a leg's lock estimate began (the void's ``0`` subscript)."""

    head_Pa: float
    rod_Pa: float
    stroke_m: float


def void_estimate_m(settings: LockStartBSettings, geometry: CylinderGeometry, anchor: LockAnchor,
                    head_Pa: float, rod_Pa: float) -> float:
    """Hydraulics 1: oil the rod side did not get since the anchor - the piston travel the head
    saw minus the part the rod decompression absorbed (head term at the upper ``beta``, rod
    term at the lower one, both conservative)."""
    head_term = ((settings.a2_head_dead_length_m + anchor.stroke_m) * (head_Pa - anchor.head_Pa)
                 / settings.a2_void_head_bulk_modulus_Pa)
    rod_length_m = settings.a2_rod_dead_length_m + geometry.stroke_max_m - anchor.stroke_m
    rod_term = rod_length_m * (rod_Pa - anchor.rod_Pa) / settings.a2_void_rod_bulk_modulus_Pa
    return max(0.0, float(head_term + rod_term))


def retract_fill_bound(settings: LockStartBSettings, geometry: CylinderGeometry, leg: int,
                       head_Pa: float, rod_Pa: float, stroke_m: float,
                       void_m: float) -> tuple[float, float]:
    """Spec 3.2 retract ``(x_lb, p_open,lb)``: ``kappa_fill`` times the hydraulics dead-stroke
    formula (``check_open_delay.retract_dead``, VN circuit) on the robust lower-bound set,
    with the reading margin (``p_h - e``, ``p_r + e`` above the floor) and the void."""
    config = RetractConfig(rod_forward=True, volume_scale=1.0,
                           v_line_m3=settings.a2_line_volume_m3,
                           beta_hose_Pa=settings.a2_hose_bulk_modulus_Pa, psi=settings.a2_psi,
                           p_crack_Pa=settings.a2_crack_Pa)
    margin_Pa = settings.a2_reading_margin_Pa
    values = retract_dead(config, head_Pa - margin_Pa, max(rod_Pa + margin_Pa, ROD_FLOOR_PA),
                          settings.a2_friction_band_N[leg], stroke_m, void_m,
                          float(geometry.head_area_m2[leg]), float(geometry.annulus_area_m2[leg]),
                          geometry.stroke_max_m, settings.a2_rod_dead_length_m,
                          settings.a2_head_dead_length_m, settings.a2_bulk_modulus_Pa,
                          settings.a2_tank_Pa)
    return settings.a2_fill_factor * max(float(values["need"]), 0.0), float(values["p_open"])


def extend_fill_bound_m(settings: LockStartBSettings, geometry: CylinderGeometry, leg: int,
                        head_Pa: float, rod_Pa: float) -> float:
    """Hydraulics 2 extend ``x_lb``: the line charged to ``p_A,lb = max(p_T + (p_r - e + p_cr -
    p_T) / psi, p_h - e + p_cr - psi (p_r + e))``, in stroke units of the head area."""
    margin_Pa, tank_Pa, crack_Pa = (settings.a2_reading_margin_Pa, settings.a2_tank_Pa,
                                    settings.a2_crack_Pa)
    psi = settings.a2_psi
    rod_release_Pa = tank_Pa + (rod_Pa - margin_Pa + crack_Pa - tank_Pa) / psi
    head_open_Pa = head_Pa - margin_Pa + crack_Pa - psi * (rod_Pa + margin_Pa)
    line_Pa = max(rod_release_Pa, head_open_Pa) - tank_Pa
    line_m = (max(line_Pa, 0.0) * settings.a2_line_volume_m3
              / (float(geometry.head_area_m2[leg]) * settings.a2_hose_bulk_modulus_Pa))
    return settings.a2_fill_factor * line_m


def stopping_travel_m(speed_m_s: float, step_m_s: float | None, period_s: float) -> float:
    """Least travel after a period at ``speed`` when every later period may lower the speed by
    at most ``step`` (the periods ``speed - step``, ``speed - 2 step``, ... above 0): the
    ramp-down the symmetric increment limit forces (hydraulics: the look-ahead)."""
    if step_m_s is None or not math.isfinite(step_m_s):
        return 0.0
    whole_steps = math.ceil(speed_m_s / step_m_s - 1e-12) - 1
    if whole_steps <= 0:
        return 0.0
    return period_s * (whole_steps * speed_m_s - step_m_s * whole_steps * (whole_steps + 1) / 2)


def deadbeat_fill_speed(remaining_m: float, previous_m_s: float, cap_m_s: float,
                        step_m_s: float | None, period_s: float) -> float:
    """Stats Q-B dead-beat command (``s20_aii_b.delivered`` "deadbeat"): the largest speed
    ``c <= previous + step`` (and the cap) with ``c T + stopping_travel(c) <= remaining``, so
    the commanded travel, its ramp-down included, lands on the bound.

    ``previous_m_s`` is the last output along the fill direction (negative when it points the
    other way). Returns 0 when nothing remains.
    """
    if remaining_m <= PLAN_TOLERANCE_M:
        return 0.0
    upper = cap_m_s if step_m_s is None else min(cap_m_s, previous_m_s + step_m_s)
    upper = max(upper, 0.0)

    def travel(speed: float) -> float:
        return speed * period_s + stopping_travel_m(speed, step_m_s, period_s)

    if travel(upper) <= remaining_m + PLAN_TOLERANCE_M:
        return upper
    low, high = 0.0, upper
    for _ in range(80):  # travel() is increasing in the speed
        middle = 0.5 * (low + high)
        if travel(middle) <= remaining_m:
            low = middle
        else:
            high = middle
    return low


def _e3_displacement(reads: list[float], sign: int) -> float:
    """E3 displacement along ``sign`` (NaN before the third read)."""
    if len(reads) < WITNESS_READS:
        return float("nan")
    first = sum(reads[:WITNESS_READS]) / WITNESS_READS
    last = sum(reads[-WITNESS_READS:]) / WITNESS_READS
    return sign * (last - first)


# ------------------------------------------------------------------------------ run state
@dataclass
class _DeadbandLeg:
    """A(i) state of one leg: the acting stretch and the floor."""

    stretch_sign: int = 0
    stretch_periods: int = 0
    stretch_travel_m: float = 0.0
    """``D_cmd``: commanded travel of the stretch."""
    stretch_reads: list[float] = field(default_factory=list)
    """Stroke reads from the read before the stretch's first acting period on (E3)."""
    is_floor_on: bool = False
    floor_sign: int = 0
    floor_m_s: float = 0.0
    floor_reads: list[float] = field(default_factory=list)
    """Stroke reads from the trigger on (E3 witness)."""
    cap_periods: int = 0


@dataclass
class _FillLeg:
    """A(ii) state of one leg: the fill episode."""

    is_on: bool = False
    sign: int = 0
    anchor: LockAnchor | None = None
    lower_bound_m: float = 0.0
    commanded_m: float = 0.0
    start_stroke_m: float = float("nan")
    start_rod_Pa: float = float("nan")
    rod_min_Pa: float = float("nan")
    rod_witness_Pa: float = float("inf")
    planned_m_s: float = 0.0
    hold_start_s: float | None = None
    periods: int = 0


@dataclass
class _EventOrder:
    """B episode (one predicted leg at a time)."""

    leg: int = NO_LEG
    start_s: float = float("nan")
    exit_count: int = 0


@dataclass
class _PreTwist:
    """B3 pre-twist (one predicted leg at a time)."""

    leg: int = NO_LEG
    start_s: float = float("nan")
    release_count: int = 0
    periods: int = 0
    commanded_m: float = 0.0
    """Commanded twist travel of the leg so far."""


@dataclass
class _LegCounts:
    """Record counters of one leg (spec 3.1 .. 3.3 "기록")."""

    a1_triggers: int = 0
    a1_cap_reached: int = 0
    a1_trigger_periods: list[int] = field(default_factory=list)
    a1_end: Counter = field(default_factory=Counter)
    a1_raised_periods: int = 0
    a2_floors: int = 0
    a2_start_bounds_m: list[float] = field(default_factory=list)
    a2_end: Counter = field(default_factory=Counter)
    a2_end_periods: list[int] = field(default_factory=list)
    a2_raised_periods: int = 0
    a2_hold_periods: int = 0
    b1_blocked_periods: int = 0
    b2_early_starts: list[float] = field(default_factory=list)
    b3_periods: int = 0

    def to_meta(self) -> dict[str, Any]:
        return {"a1_triggers": self.a1_triggers, "a1_cap_reached": self.a1_cap_reached,
                "a1_trigger_periods": list(self.a1_trigger_periods),
                "a1_end": dict(self.a1_end), "a1_raised_periods": self.a1_raised_periods,
                "a2_floors": self.a2_floors,
                "a2_start_bounds_m": [round(value, 9) for value in self.a2_start_bounds_m],
                "a2_end": dict(self.a2_end), "a2_end_periods": list(self.a2_end_periods),
                "a2_raised_periods": self.a2_raised_periods,
                "a2_hold_periods": self.a2_hold_periods,
                "b1_blocked_periods": self.b1_blocked_periods,
                "b2_early_starts_s": list(self.b2_early_starts),
                "b3_periods": self.b3_periods}


TRACE_FLOAT_FIELDS = ("input_m_s", "output_m_s", "a1_floor_m_s", "a2_lower_bound_m",
                      "a2_planned_m_s", "a2_commanded_m")
TRACE_FLAG_FIELDS = ("a1_on", "a2_on", "b1_blocked", "protected")
TRACE_PERIOD_FLAGS = ("g2_split",)
"""Per-read flags (one value per read): ``g2_split`` = the G2 vector ramp acted in a period
with a leg the A rules raised (spec revision 5)."""


@dataclass(frozen=True)
class FloorInputs:
    """What the output-stage rules read in one period (``C2Controller`` supplies it)."""

    t_s: float
    is_level: bool
    is_fill_phase: bool
    """A(ii) may act (every phase but FAULT, FAULT_REGROUND and IDLE)."""
    is_fault: bool
    requested_m_s: NDArray[np.float64]
    """The command of this period before the rules."""
    acting_m_s: NDArray[np.float64]
    """The command acting on the legs now (the controller's applied output of the last
    update)."""
    previous_output_m_s: NDArray[np.float64]
    """The controller output of the last update (after the increment limit, before the delay)."""
    stroke_m: NDArray[np.float64]
    """``stroke_m`` (oil coordinate)."""
    head_Pa: NDArray[np.float64]
    rod_Pa: NDArray[np.float64] | None
    protected: NDArray[np.bool_]
    """Legs whose command the rules must not raise in this period (priority rules)."""
    fallback_legs: frozenset[int]
    # Edition 7 A(i)-b inputs (read only when ``A_ib`` is on; the defaults keep every caller
    # of edition 6 valid).
    completion: CompletionFlags | None = None
    """This period's LEVEL completion tests; None = not evaluated (condition 3 open)."""
    twist_load_N: float = math.nan
    """``D = n^T F`` of the completion test (raw reading)."""
    twist_limit_N: float = math.nan
    """The relax ``max_twist_N`` of the controller (condition (다) limit by default)."""
    lower_load_N: NDArray[np.float64] | None = None
    """``F_lo``: the lower load estimate B3 protection uses (``_load_estimate_N``)."""
    force_N: NDArray[np.float64] | None = None
    """The cylinder force reading (record of the shot's ``Delta F`` only)."""
    F_min_N: float = math.nan
    twist_vector: NDArray[np.float64] | None = None


@dataclass
class _BlindLeg:
    """Edition 7 A(i)-b state of one leg: the dead-band stretch, the floor and the latch."""

    stretch_sign: int = 0
    stretch_periods: int = 0
    stretch_reads: list[float] = field(default_factory=list)
    """Stroke reads from the stretch's first period on (index 0 = ``k_s``)."""
    is_protect_noted: bool = False
    """The protection event of this stretch is out already."""
    is_floor_on: bool = False
    floor_sign: int = 0
    floor_m_s: float = 0.0
    floor_reads: list[float] = field(default_factory=list)
    cap_periods: int = 0
    last_trigger_sign: int = 0
    reversals: int = 0
    is_latched: bool = False


@dataclass
class _BlindShot:
    """Record of one A(i)-b shot: ``Delta D`` and ``Delta F`` from the period before the
    trigger to ``ib_record_after_s`` after its end."""

    leg: int
    sign: int
    start_t_s: float
    twist_before_N: float
    force_before_N: list[float]
    end_t_s: float | None = None
    end: str | None = None
    twist_after_N: float | None = None
    force_after_N: list[float] | None = None

    def to_meta(self) -> dict[str, Any]:
        delta_D = (None if self.twist_after_N is None or not math.isfinite(self.twist_before_N)
                   else self.twist_after_N - self.twist_before_N)
        delta_F = (None if self.force_after_N is None
                   else [after - before for after, before
                         in zip(self.force_after_N, self.force_before_N, strict=True)])
        grew = (None if delta_D is None
                else abs(self.twist_after_N) > abs(self.twist_before_N))
        return {"leg": LEG_ORDER[self.leg], "sign": self.sign, "start_t_s": self.start_t_s,
                "end_t_s": self.end_t_s, "end": self.end,
                "twist_before_N": self.twist_before_N, "twist_after_N": self.twist_after_N,
                "delta_D_N": delta_D, "delta_F_N": delta_F, "twist_grew": grew}


@dataclass
class _BlindCounts:
    """Edition 7 record counters of one leg (spec 3.1 "기록")."""

    triggers: int = 0
    trigger_periods: list[int] = field(default_factory=list)
    end: Counter = field(default_factory=Counter)
    latches: int = 0
    reversals: int = 0
    protect_blocked_periods: int = 0
    raised_periods: int = 0

    def to_meta(self) -> dict[str, Any]:
        return {"triggers": self.triggers, "trigger_periods": list(self.trigger_periods),
                "end": dict(self.end), "latches": self.latches, "n_rev": self.reversals,
                "protect_blocked_periods": self.protect_blocked_periods,
                "raised_periods": self.raised_periods}


class LockStartB:
    """Run state, rules and record of one controller run (:class:`LockStartBSettings` on).

    Args:
        settings: The run's settings (at least one component).
        geometry: Cylinder values of the controller.
    """

    def __init__(self, settings: LockStartBSettings, geometry: CylinderGeometry) -> None:
        if not settings.is_enabled:
            raise ValueError("LockStartB needs at least one component")
        self.settings = settings
        self.geometry = geometry
        self.hold_m_s = settings.hold_speed_ratio * geometry.max_speed_m_s
        self._deadband = [_DeadbandLeg() for _ in range(LEG_COUNT)]
        self._fill = [_FillLeg() for _ in range(LEG_COUNT)]
        self._acting_history: list[NDArray[np.float64]] = []
        self._anchors: list[LockAnchor | None] = [None] * LEG_COUNT
        """Read at which each leg's present lock estimate began."""
        self._last_stroke_m: NDArray[np.float64] | None = None
        self.last_raised = np.zeros(LEG_COUNT, bool)
        """Legs this period's rules raised (the controller's vector-ramp exclusion)."""
        self.last_input_m_s = np.zeros(LEG_COUNT)
        """The command of this period before the rules."""
        self.event_order = _EventOrder()
        self.counts = [_LegCounts() for _ in range(LEG_COUNT)]
        self.b_episodes: list[dict[str, Any]] = []
        self.pre_twist = _PreTwist()
        self.b3_episodes: list[dict[str, Any]] = []
        self.protect_blocked_legs: set[int] = set()
        self.g2_split_periods = 0
        self.events: list[tuple[float, str]] = []
        """Events of the last :meth:`apply_floors` (the controller adds them to its log)."""
        self._trace_t_s: list[float] = []
        self._trace_rows: list[dict[str, NDArray[Any]]] = []
        self._pending_b1_blocked = np.zeros(LEG_COUNT, bool)
        # edition 7 A(i)-b (inert without the component)
        self._blind = [_BlindLeg() for _ in range(LEG_COUNT)]
        self.blind_counts = [_BlindCounts() for _ in range(LEG_COUNT)]
        self.blind_shots: list[_BlindShot] = []
        self.blind_four_leg_triggers = 0
        """Periods in which all four legs triggered with the twist sign pattern (``+-sign n``)."""
        self._last_twist_N = math.nan
        self._last_force_N: list[float] = [math.nan] * LEG_COUNT

    # --------------------------------------------------------------- output-stage rules
    def apply_floors(self, inputs: FloorInputs) -> NDArray[np.float64]:
        """The command of this period with the A(i) floor and the A(ii) fill (spec 3.1, 3.2)."""
        self.events = []
        requested = np.asarray(inputs.requested_m_s, float)
        self._remember_acting(inputs)
        floors = np.zeros(LEG_COUNT)
        if self.settings.has(LsbComponent.DEADBAND):
            floors = np.maximum(floors, self._deadband_floors(inputs, requested))
        if self.settings.has(LsbComponent.FILL_FLOOR):
            floors = np.maximum(floors, self._fill_speeds(inputs, requested))
        output = requested.copy()
        is_raised = ((floors > np.abs(requested)) & (np.abs(requested) > self.hold_m_s)
                     & ~inputs.protected)
        output[is_raised] = np.sign(requested[is_raised]) * floors[is_raised]
        if self.settings.has(LsbComponent.BLIND_FILL):
            is_raised = is_raised | self._apply_blind_floors(inputs, requested, output)
        self._count_raised(is_raised)
        self.last_raised = is_raised.copy()
        self.last_input_m_s = requested.copy()
        self._last_stroke_m = np.asarray(inputs.stroke_m, float).copy()
        self._record_trace(inputs, requested, output)
        return output

    def after_output(self, output_m_s: NDArray[np.float64]) -> None:
        """Count the commanded fill of this period's output (after the increment limit)."""
        period_s = self.geometry.period_s
        for fill, speed in zip(self._fill, np.asarray(output_m_s, float), strict=True):
            if fill.is_on and np.sign(speed) == fill.sign:
                fill.commanded_m += abs(float(speed)) * period_s
        if self._trace_rows:
            self._trace_rows[-1]["a2_commanded_m"] = np.array(
                [fill.commanded_m if fill.is_on else np.nan for fill in self._fill])

    def note_g2_split(self, is_split: bool) -> None:
        """G2 acted in this period while an A rule had raised a leg (record only)."""
        if not is_split:
            return
        self.g2_split_periods += 1
        if self._trace_rows:
            self._trace_rows[-1]["g2_split"] = np.array(True)

    def _remember_acting(self, inputs: FloorInputs) -> None:
        """Acting history (``N_lock``) and the lock anchors (the read a lock estimate began)."""
        acting = np.asarray(inputs.acting_m_s, float)
        previous = self._acting_history[-1] if self._acting_history else None
        for leg in range(LEG_COUNT):
            is_held = abs(float(acting[leg])) <= self.hold_m_s
            was_held = previous is not None and abs(float(previous[leg])) <= self.hold_m_s
            if not is_held:
                self._anchors[leg] = None
            elif not was_held or self._anchors[leg] is None:
                self._anchors[leg] = self._anchor_of(inputs, leg)
        self._acting_history.append(acting.copy())
        del self._acting_history[:-self.settings.a2_lock_periods]

    @staticmethod
    def _anchor_of(inputs: FloorInputs, leg: int) -> LockAnchor:
        rod_Pa = np.nan if inputs.rod_Pa is None else float(inputs.rod_Pa[leg])
        return LockAnchor(head_Pa=float(inputs.head_Pa[leg]), rod_Pa=rod_Pa,
                          stroke_m=float(inputs.stroke_m[leg]))

    def _count_raised(self, is_raised: NDArray[np.bool_]) -> None:
        for leg in np.flatnonzero(is_raised):
            if self._deadband[leg].is_floor_on:
                self.counts[leg].a1_raised_periods += 1
            if self._fill[leg].is_on:
                self.counts[leg].a2_raised_periods += 1
            if self._blind[leg].is_floor_on:
                self.blind_counts[leg].raised_periods += 1

    # A(i) ---------------------------------------------------------------------------
    def _deadband_floors(self, inputs: FloorInputs,
                         requested: NDArray[np.float64]) -> NDArray[np.float64]:
        floors = np.zeros(LEG_COUNT)
        for leg, state in enumerate(self._deadband):
            if not inputs.is_level:
                self._end_deadband(leg, A1End.PHASE)
                self._reset_stretch(state)
                continue
            if self._blind[leg].is_floor_on:
                # Edition 7 3.1: one leg never builds both stretches at once.
                self._reset_stretch(state)
                continue
            self._update_stretch(state, leg, inputs)
            if state.is_floor_on:
                state.floor_reads.append(float(inputs.stroke_m[leg]))
                floors[leg] = self._next_deadband_floor(state, leg, inputs, requested[leg])
            elif self._is_stall(state):
                self._start_deadband(state, leg, float(inputs.stroke_m[leg]),
                                     abs(float(requested[leg])))
                floors[leg] = state.floor_m_s
        return floors

    def _update_stretch(self, state: _DeadbandLeg, leg: int, inputs: FloorInputs) -> None:
        """Spec 3.1 (1)-(2): one sign of the acting command above ``u_hold``."""
        acting = float(inputs.acting_m_s[leg])
        sign = int(np.sign(acting)) if abs(acting) > self.hold_m_s else 0
        if sign == 0:
            self._reset_stretch(state)
            return
        if sign != state.stretch_sign:
            state.stretch_sign = sign
            state.stretch_periods = 0
            state.stretch_travel_m = 0.0
            # The acting command moved the leg since the last read: start from that read.
            start = self._last_stroke_m
            state.stretch_reads = [] if start is None else [float(start[leg])]
        state.stretch_periods += 1
        state.stretch_travel_m += abs(acting) * self.geometry.period_s
        state.stretch_reads.append(float(inputs.stroke_m[leg]))

    @staticmethod
    def _reset_stretch(state: _DeadbandLeg) -> None:
        state.stretch_sign = 0
        state.stretch_periods = 0
        state.stretch_travel_m = 0.0
        state.stretch_reads = []

    def _is_stall(self, state: _DeadbandLeg) -> bool:
        """Spec 3.1 (3): the stretch moved (E3) less than ``eta D_cmd`` over ``N_trig``."""
        settings = self.settings
        if state.stretch_sign == 0 or state.stretch_periods < settings.a1_trigger_periods:
            return False
        if state.stretch_travel_m < settings.a1_trigger_travel_m:
            return False
        motion_m = _e3_displacement(state.stretch_reads, state.stretch_sign)
        return motion_m < settings.a1_motion_ratio * state.stretch_travel_m

    def _start_deadband(self, state: _DeadbandLeg, leg: int, stroke_m: float,
                        requested_m_s: float) -> None:
        state.is_floor_on = True
        state.floor_sign = state.stretch_sign
        # Hydraulics 5: the staircase starts at max(|u|, u_hold).
        state.floor_m_s = max(requested_m_s, self.hold_m_s)
        state.cap_periods = 0
        state.floor_reads = [stroke_m]
        counts = self.counts[leg]
        counts.a1_triggers += 1
        counts.a1_trigger_periods.append(state.stretch_periods)

    def _next_deadband_floor(self, state: _DeadbandLeg, leg: int, inputs: FloorInputs,
                             requested_m_s: float) -> float:
        end = self._deadband_end_reason(state, leg, inputs, requested_m_s)
        if end is not None:
            self._end_deadband(leg, end)
            return 0.0
        settings = self.settings
        state.floor_m_s = min(state.floor_m_s + settings.a1_step_m_s, settings.a1_cap_m_s)
        if state.floor_m_s >= settings.a1_cap_m_s:
            state.cap_periods += 1
        return state.floor_m_s

    def _deadband_end_reason(self, state: _DeadbandLeg, leg: int, inputs: FloorInputs,
                             requested_m_s: float) -> A1End | None:
        sign = int(np.sign(requested_m_s))
        if _e3_displacement(state.floor_reads, state.floor_sign) >= self.settings.a1_witness_m:
            return A1End.MOVED
        if sign != state.floor_sign and abs(requested_m_s) > self.hold_m_s:
            return A1End.SIGN
        if abs(requested_m_s) <= self.hold_m_s:
            return A1End.HOLD
        if state.cap_periods >= self.settings.a1_cap_periods:
            self.counts[leg].a1_cap_reached += 1
            self.events.append((inputs.t_s, f"{CAP_EVENT}:{LEG_ORDER[leg]}"))
            return A1End.CAP
        return None

    def _end_deadband(self, leg: int, reason: A1End) -> None:
        state = self._deadband[leg]
        if not state.is_floor_on:
            return
        state.is_floor_on = False
        state.floor_m_s = 0.0
        state.cap_periods = 0
        state.floor_reads = []
        self.counts[leg].a1_end[str(reason)] += 1
        # A new stretch must build up again before the next trigger.
        self._reset_stretch(state)

    # A(i)-b, edition 7 ------------------------------------------------------------------
    def _apply_blind_floors(self, inputs: FloorInputs, requested: NDArray[np.float64],
                            output: NDArray[np.float64]) -> NDArray[np.bool_]:
        """Edition 7 3.1 on ``output`` in place; the legs it raised. The floor is applied
        whatever ``|requested|`` is (implementation note (가): the request is inside the dead
        band), never on a protected leg."""
        floors, signs = self._blind_floors(inputs, requested)
        is_raised = (floors > np.abs(output)) & ~inputs.protected
        output[is_raised] = signs[is_raised] * floors[is_raised]
        self._note_shot_after(inputs)
        return is_raised

    def _blind_floors(self, inputs: FloorInputs, requested: NDArray[np.float64]
                      ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        floors, signs = np.zeros(LEG_COUNT), np.zeros(LEG_COUNT)
        if not inputs.is_level:
            for leg in range(LEG_COUNT):
                self._end_blind(leg, BlindEnd.PHASE, inputs.t_s)
                self._blind[leg] = _BlindLeg()  # the latch and the reversals end with LEVEL
            return floors, signs
        triggered = []
        for leg, state in enumerate(self._blind):
            if state.is_floor_on:
                floors[leg] = self._next_blind_floor(state, leg, inputs, float(requested[leg]))
                signs[leg] = state.floor_sign
                continue
            self._update_blind_stretch(state, inputs, leg)
            if not self._is_blind_trigger(state, leg, inputs):
                continue
            if not self._is_shot_safe(leg, state.stretch_sign, inputs):
                self._note_protect(state, leg, inputs.t_s)
                continue
            if self._latches_on_trigger(state, leg, inputs.t_s):
                continue
            self._start_blind(state, leg, inputs)
            triggered.append((leg, state.floor_sign))
            floors[leg], signs[leg] = state.floor_m_s, state.floor_sign
        self._count_four_leg_trigger(triggered, inputs)
        return floors, signs

    def _update_blind_stretch(self, state: _BlindLeg, inputs: FloorInputs, leg: int) -> None:
        """Condition 1: one sign of the acting command with ``0 < |u| <= u_hold``; a zero, a
        sign change or ``|u| > u_hold`` clears it."""
        acting = float(inputs.acting_m_s[leg])
        if acting == 0.0 or abs(acting) > self.hold_m_s or state.is_latched:
            self._reset_blind_stretch(state)
            return
        sign = int(np.sign(acting))
        if sign != state.stretch_sign:
            self._reset_blind_stretch(state)
            state.stretch_sign = sign
        state.stretch_periods += 1
        state.stretch_reads.append(float(inputs.stroke_m[leg]))

    @staticmethod
    def _reset_blind_stretch(state: _BlindLeg) -> None:
        state.stretch_sign = 0
        state.stretch_periods = 0
        state.stretch_reads = []
        state.is_protect_noted = False

    def _is_blind_trigger(self, state: _BlindLeg, leg: int, inputs: FloorInputs) -> bool:
        """Conditions 1 .. 3 of spec 3.1 (an A(i) floor on the leg or a protected leg waits)."""
        settings = self.settings
        if state.stretch_sign == 0 or state.stretch_periods < settings.ib_blind_periods:
            return False
        if self._deadband[leg].is_floor_on or bool(inputs.protected[leg]):
            return False
        return (self._blind_still_m(state) < settings.ib_still_m
                and self._is_completion_open(inputs))

    def _blind_still_m(self, state: _BlindLeg) -> float:
        """Condition 2: ``Delta s`` along the stretch sign, the mean of the last three reads
        minus the mean of reads ``k_s + skip`` .. ``k_s + skip + 2`` (no sliding window)."""
        skip = self.settings.ib_reference_skip_reads
        reads = state.stretch_reads
        reference = sum(reads[skip:skip + WITNESS_READS]) / WITNESS_READS
        latest = sum(reads[-WITNESS_READS:]) / WITNESS_READS
        return state.stretch_sign * (latest - reference)

    def _is_completion_open(self, inputs: FloorInputs) -> bool:
        """Condition 3 (:class:`BlindCondition`); a period without completion flags counts as
        open (its LEVEL completion was not evaluated)."""
        flags = inputs.completion
        if flags is None:
            return True
        condition = BlindCondition(self.settings.ib_condition)
        if condition is BlindCondition.LEVEL_INCOMPLETE:
            return not flags.is_complete
        is_attitude_clearance_open = not (flags.is_on_target and flags.is_clearance_done)
        if condition is BlindCondition.ATTITUDE_CLEARANCE:
            return is_attitude_clearance_open
        limit_N = self.settings.ib_twist_limit_N
        if limit_N is None:
            limit_N = inputs.twist_limit_N
        is_twist_open = math.isfinite(inputs.twist_load_N) and abs(inputs.twist_load_N) > limit_N
        return is_attitude_clearance_open or is_twist_open

    def _is_shot_safe(self, leg: int, sign: int, inputs: FloorInputs) -> bool:
        """Predictive protection: ``min_j(F_lo,j + k_1 n_i n_j sigma Delta e_max) >= F_min +
        margin``; missing or non-finite inputs hold the shot back."""
        settings = self.settings
        if not settings.ib_protect:
            return True
        loads, twist = inputs.lower_load_N, inputs.twist_vector
        if loads is None or twist is None or not math.isfinite(inputs.F_min_N):
            return False
        loads = np.asarray(loads, float)
        twist = np.asarray(twist, float)
        if not np.all(np.isfinite(loads)):
            return False
        step_N = (settings.ib_protect_stiffness_N_m * twist[leg] * twist * sign
                  * settings.ib_protect_travel_m)
        predicted_N = loads + step_N
        return bool(np.min(predicted_N) >= inputs.F_min_N + settings.ib_protect_margin_N)

    def _note_protect(self, state: _BlindLeg, leg: int, t_s: float) -> None:
        self.blind_counts[leg].protect_blocked_periods += 1
        if not state.is_protect_noted:
            state.is_protect_noted = True
            self.events.append((t_s, f"{BLIND_PROTECT_EVENT}:{LEG_ORDER[leg]}"))

    def _latches_on_trigger(self, state: _BlindLeg, leg: int, t_s: float) -> bool:
        """Count an opposite-sign trigger; more than ``ib_latch_reversals`` of them latch the
        leg off for the rest of the LEVEL stretch (that trigger does not fire)."""
        sign = state.stretch_sign
        if state.last_trigger_sign not in (0, sign):
            state.reversals += 1
            self.blind_counts[leg].reversals += 1
        state.last_trigger_sign = sign
        if state.reversals <= self.settings.ib_latch_reversals:
            return False
        state.is_latched = True
        self.blind_counts[leg].latches += 1
        self.events.append((t_s, f"{BLIND_LATCH_EVENT}:{LEG_ORDER[leg]}"))
        self._reset_blind_stretch(state)
        return True

    def _start_blind(self, state: _BlindLeg, leg: int, inputs: FloorInputs) -> None:
        """Implementation note (다): the trigger period commands ``u_hold + Delta u_step``."""
        settings = self.settings
        counts = self.blind_counts[leg]
        counts.triggers += 1
        counts.trigger_periods.append(state.stretch_periods)
        state.is_floor_on = True
        state.floor_sign = state.stretch_sign
        state.floor_m_s = min(self.hold_m_s + settings.a1_step_m_s, settings.a1_cap_m_s)
        state.floor_reads = [float(inputs.stroke_m[leg])]
        state.cap_periods = 0
        self.blind_shots.append(_BlindShot(leg=leg, sign=state.floor_sign,
                                           start_t_s=float(inputs.t_s),
                                           twist_before_N=self._last_twist_N,
                                           force_before_N=list(self._last_force_N)))
        self._reset_blind_stretch(state)

    def _next_blind_floor(self, state: _BlindLeg, leg: int, inputs: FloorInputs,
                          requested_m_s: float) -> float:
        state.floor_reads.append(float(inputs.stroke_m[leg]))
        end = self._blind_end_reason(state, leg, inputs, requested_m_s)
        if end is not None:
            self._end_blind(leg, end, inputs.t_s)
            return 0.0
        settings = self.settings
        state.floor_m_s = min(state.floor_m_s + settings.a1_step_m_s, settings.a1_cap_m_s)
        if state.floor_m_s >= settings.a1_cap_m_s:
            state.cap_periods += 1
        return state.floor_m_s

    def _blind_end_reason(self, state: _BlindLeg, leg: int, inputs: FloorInputs,
                          requested_m_s: float) -> BlindEnd | None:
        """Spec 3.1 end: motion witness, sign change, a zero request, the cap time (implementation
        note (나): no ``u_hold`` end)."""
        if _e3_displacement(state.floor_reads, state.floor_sign) >= self.settings.a1_witness_m:
            return BlindEnd.MOVED
        if requested_m_s == 0.0:
            return BlindEnd.ZERO
        if int(np.sign(requested_m_s)) != state.floor_sign:
            return BlindEnd.SIGN
        if state.cap_periods >= self.settings.a1_cap_periods:
            self.events.append((inputs.t_s, f"{CAP_EVENT}:{LEG_ORDER[leg]}"))
            return BlindEnd.CAP
        return None

    def _end_blind(self, leg: int, reason: BlindEnd, t_s: float) -> None:
        state = self._blind[leg]
        if not state.is_floor_on:
            return
        state.is_floor_on = False
        state.floor_m_s = 0.0
        state.cap_periods = 0
        state.floor_reads = []
        self.blind_counts[leg].end[str(reason)] += 1
        for shot in reversed(self.blind_shots):
            if shot.leg == leg and shot.end_t_s is None:
                shot.end_t_s, shot.end = float(t_s), str(reason)
                break
        self._reset_blind_stretch(state)

    def _count_four_leg_trigger(self, triggered: list[tuple[int, int]],
                                inputs: FloorInputs) -> None:
        if len(triggered) != LEG_COUNT or inputs.twist_vector is None:
            return
        pattern = np.array([sign for _, sign in sorted(triggered)])
        twist_signs = np.sign(np.asarray(inputs.twist_vector, float))
        if np.array_equal(pattern, twist_signs) or np.array_equal(pattern, -twist_signs):
            self.blind_four_leg_triggers += 1

    def _note_shot_after(self, inputs: FloorInputs) -> None:
        """Record only: the twist and forces of this period (the "before" of a later trigger)
        and the "after" of the shots that ended ``ib_record_after_s`` ago."""
        force = (None if inputs.force_N is None
                 else [float(value) for value in np.asarray(inputs.force_N, float)])
        delay_s = self.settings.ib_record_after_s
        for shot in self.blind_shots:
            if shot.end_t_s is None or shot.twist_after_N is not None:
                continue
            if inputs.t_s >= shot.end_t_s + delay_s - TIME_MATCH_TOLERANCE_S:
                shot.twist_after_N = float(inputs.twist_load_N)
                shot.force_after_N = force
        self._last_twist_N = float(inputs.twist_load_N)
        self._last_force_N = force if force is not None else [math.nan] * LEG_COUNT

    def blind_record(self) -> dict[str, Any]:
        """The ``blind`` block of the ``lsb_record`` (edition 7 3.1 "기록"; record only)."""
        shots = [shot.to_meta() for shot in self.blind_shots]
        return {"legs": {LEG_ORDER[leg]: counts.to_meta()
                         for leg, counts in enumerate(self.blind_counts)},
                "shots": shots,
                "shots_twist_grew": sum(bool(shot["twist_grew"]) for shot in shots),
                "four_leg_twist_triggers": self.blind_four_leg_triggers}

    # A(ii) --------------------------------------------------------------------------
    def _fill_speeds(self, inputs: FloorInputs,
                     requested: NDArray[np.float64]) -> NDArray[np.float64]:
        speeds = np.zeros(LEG_COUNT)
        for leg in range(LEG_COUNT):
            requested_m_s = float(requested[leg])
            if self._fill[leg].is_on:
                self._update_fill(leg, inputs, requested_m_s)
            if not self._fill[leg].is_on and self._is_fill_start(leg, inputs, requested_m_s):
                self._start_fill(leg, inputs, requested_m_s)
            fill = self._fill[leg]
            if fill.is_on:
                fill.periods += 1
                speeds[leg] = self._fill_command(fill, leg, inputs, requested_m_s)
        return speeds

    def _update_fill(self, leg: int, inputs: FloorInputs, requested_m_s: float) -> None:
        """This period's bound (recomputed every period, hydraulics 1) and the end checks."""
        fill = self._fill[leg]
        rod_Pa = np.nan if inputs.rod_Pa is None else float(inputs.rod_Pa[leg])
        if np.isfinite(rod_Pa):
            fill.rod_min_Pa = min(fill.rod_min_Pa, rod_Pa)
        bound = self._lower_bound(leg, inputs, fill.sign, fill.anchor)
        if bound is not None:
            fill.lower_bound_m = bound[0]
        end = self._fill_end_reason(fill, leg, inputs, requested_m_s, rod_Pa)
        if end is not None:
            self._end_fill(leg, end)

    def _fill_command(self, fill: _FillLeg, leg: int, inputs: FloorInputs,
                      requested_m_s: float) -> float:
        """The dead-beat command, or with the hold variant one increment once the plan comes
        down to it (until a witness or the hold time)."""
        geometry = self.geometry
        cap_m_s = self.settings.a2_fill_speed_ratio * geometry.max_speed_m_s
        previous_along_m_s = fill.sign * float(inputs.previous_output_m_s[leg])
        planned = deadbeat_fill_speed(fill.lower_bound_m - fill.commanded_m, previous_along_m_s,
                                      cap_m_s, geometry.increment_limit_m_s, geometry.period_s)
        hold_speed = min(cap_m_s, geometry.increment_limit_m_s or cap_m_s)
        if self.settings.a2_hold_after_fill_s is not None and (
                fill.hold_start_s is not None or planned <= max(abs(requested_m_s), hold_speed)):
            if fill.hold_start_s is None:
                fill.hold_start_s = float(inputs.t_s)
            self.counts[leg].a2_hold_periods += 1
            planned = max(planned, hold_speed)
        fill.planned_m_s = planned
        return planned

    def _lower_bound(self, leg: int, inputs: FloorInputs, sign: int,
                     anchor: LockAnchor | None) -> tuple[float, float] | None:
        """``(x_lb, p_open,lb)`` from this period's reads; None without the reads it needs."""
        head_Pa = float(inputs.head_Pa[leg])
        rod_Pa = np.nan if inputs.rod_Pa is None else float(inputs.rod_Pa[leg])
        if not (np.isfinite(head_Pa) and np.isfinite(rod_Pa)):
            return None
        if sign > 0:
            return extend_fill_bound_m(self.settings, self.geometry, leg, head_Pa, rod_Pa), np.nan
        void_m = 0.0
        if self.settings.a2_void_estimate and anchor is not None and np.isfinite(anchor.rod_Pa):
            void_m = void_estimate_m(self.settings, self.geometry, anchor, head_Pa, rod_Pa)
        return retract_fill_bound(self.settings, self.geometry, leg, head_Pa, rod_Pa,
                                  float(inputs.stroke_m[leg]), void_m)

    def _is_lock_estimated(self, leg: int) -> bool:
        """Spec 3.2: the last ``N_lock`` acting commands were all at or below ``u_hold``."""
        history = self._acting_history
        if len(history) < self.settings.a2_lock_periods:
            return False
        return all(abs(float(acting[leg])) <= self.hold_m_s for acting in history)

    def _is_fill_start(self, leg: int, inputs: FloorInputs, requested_m_s: float) -> bool:
        if not inputs.is_fill_phase or abs(requested_m_s) <= self.hold_m_s:
            return False
        if requested_m_s > 0.0 and not self.settings.a2_extend:
            return False
        if leg in inputs.fallback_legs and not self.settings.a2_on_fallback_legs:
            return False
        previous = float(inputs.previous_output_m_s[leg])
        is_reversal = np.sign(previous) == -np.sign(requested_m_s) and previous != 0.0
        return is_reversal or self._is_lock_estimated(leg)

    def _start_fill(self, leg: int, inputs: FloorInputs, requested_m_s: float) -> None:
        sign = int(np.sign(requested_m_s))
        anchor = self._anchors[leg] if self._is_lock_estimated(leg) else None
        bound = self._lower_bound(leg, inputs, sign, anchor)
        if bound is None or not bound[0] > 0.0:
            return
        lower_bound_m, open_Pa = bound
        rod_Pa = float(inputs.rod_Pa[leg])  # finite: the bound needed it
        rod_witness_Pa = max(self.settings.a2_rod_witness_min_Pa,
                             self.settings.a2_rod_witness_ratio * (open_Pa - rod_Pa))
        self._fill[leg] = _FillLeg(
            is_on=True, sign=sign, anchor=anchor, lower_bound_m=lower_bound_m,
            start_stroke_m=float(inputs.stroke_m[leg]), start_rod_Pa=rod_Pa, rod_min_Pa=rod_Pa,
            rod_witness_Pa=rod_witness_Pa if sign < 0 else float("inf"))
        counts = self.counts[leg]
        counts.a2_floors += 1
        counts.a2_start_bounds_m.append(lower_bound_m)

    def _fill_end_reason(self, fill: _FillLeg, leg: int, inputs: FloorInputs,
                         requested_m_s: float, rod_Pa: float) -> A2End | None:
        settings = self.settings
        if inputs.is_fault or not inputs.is_fill_phase:
            return A2End.FAULT
        moved_m = fill.sign * (float(inputs.stroke_m[leg]) - fill.start_stroke_m)
        witness_m = (settings.a2_retract_witness_m if fill.sign < 0
                     else settings.a2_extend_witness_m)
        if moved_m >= witness_m:
            return A2End.MOVED
        if np.isfinite(rod_Pa) and rod_Pa - fill.rod_min_Pa >= fill.rod_witness_Pa:
            return A2End.ROD_WITNESS
        if fill.hold_start_s is not None:
            if inputs.t_s - fill.hold_start_s >= settings.a2_hold_after_fill_s - 1e-9:
                return A2End.HOLD_TIMEOUT
        elif fill.commanded_m >= fill.lower_bound_m - PLAN_TOLERANCE_M:
            return A2End.FILLED
        if abs(requested_m_s) <= self.hold_m_s:
            return A2End.HOLD
        if int(np.sign(requested_m_s)) != fill.sign:
            return A2End.SIGN
        return None

    def _end_fill(self, leg: int, reason: A2End) -> None:
        fill = self._fill[leg]
        counts = self.counts[leg]
        counts.a2_end[str(reason)] += 1
        counts.a2_end_periods.append(fill.periods)
        self._fill[leg] = _FillLeg()

    # B -------------------------------------------------------------------------------
    @property
    def event_leg(self) -> int | None:
        """The predicted leg of the active B episode (None without one)."""
        return None if self.event_order.leg == NO_LEG else self.event_order.leg

    def start_event_order(self, leg: int, t_s: float) -> None:
        """An R-5 ``relevel_predicted:<leg>`` re-level (spec 3.3); a running episode ends."""
        if self.event_leg is not None:
            self.end_event_order(t_s, BEnd.REPLACED)
        self.event_order = _EventOrder(leg=int(leg), start_s=float(t_s))

    def end_event_order(self, t_s: float, reason: BEnd) -> None:
        leg = self.event_leg
        if leg is None:
            return
        self.b_episodes.append({"leg": LEG_ORDER[leg], "start_s": self.event_order.start_s,
                                "end_s": float(t_s), "end": str(reason)})
        self.event_order = _EventOrder()

    def update_event_exit(self, t_s: float, load_N: float, exit_level_N: float) -> None:
        """B1 end on ``N_B`` samples of the predicted leg at ``F_min`` + ``m_B``."""
        if self.event_leg is None:
            return
        order = self.event_order
        order.exit_count = order.exit_count + 1 if load_N >= exit_level_N else 0
        if order.exit_count >= self.settings.b1_exit_samples:
            self.end_event_order(t_s, BEnd.LOAD)

    def blocked_retract_speeds(self, leg_speeds: NDArray[np.float64],
                               low_counts: NDArray[np.int64]) -> NDArray[np.float64]:
        """B1: no retraction of the predicted leg and of a leg with a low re-approach count."""
        leg = self.event_leg
        if leg is None:
            return leg_speeds
        blocked = np.asarray(low_counts) > 0
        blocked[leg] = True
        is_cut = blocked & (leg_speeds < 0.0)
        self._pending_b1_blocked = self._pending_b1_blocked | is_cut
        for cut_leg in np.flatnonzero(is_cut):
            self.counts[cut_leg].b1_blocked_periods += 1
        return np.where(blocked, np.maximum(leg_speeds, 0.0), leg_speeds)

    def required_samples(self, leg: int, default_samples: int) -> int:
        """B2 (option): the start sample count of the predicted leg; unchanged by default."""
        samples = self.settings.b2_required_samples
        if samples is None or self.event_leg != leg:
            return default_samples
        return min(default_samples, samples)

    def note_early_start(self, leg: int, t_s: float) -> None:
        self.counts[leg].b2_early_starts.append(float(t_s))

    # B3 ------------------------------------------------------------------------------
    @property
    def pre_twist_leg(self) -> int | None:
        """The leg of the active B3 pre-twist (None without one)."""
        return None if self.pre_twist.leg == NO_LEG else self.pre_twist.leg

    def start_pre_twist(self, leg: int, t_s: float) -> None:
        """Spec revision 1 3.3 B3: an R-5 ``relevel_predicted:<leg>`` starts the pre-twist
        (not on a leg whose pre-twist ended on ``protect`` in this LEVEL stretch)."""
        if int(leg) in self.protect_blocked_legs:
            return
        if self.pre_twist_leg is not None:
            self.end_pre_twist(t_s, B3End.REPLACED)
        self.pre_twist = _PreTwist(leg=int(leg), start_s=float(t_s))

    def update_pre_twist(self, t_s: float, is_released: bool) -> None:
        """One LEVEL period of the pre-twist before its rate: the release count (ends it on
        ``N_B3`` released periods in a row) and the period limit."""
        twist = self.pre_twist
        if self.pre_twist_leg is None:
            return
        twist.release_count = twist.release_count + 1 if is_released else 0
        max_periods = self.settings.b3_max_periods
        if twist.release_count >= self.settings.b3_end_periods:
            self.end_pre_twist(t_s, B3End.RESOLVED)
        elif max_periods is not None and twist.periods >= max_periods:
            self.end_pre_twist(t_s, B3End.TRAVEL_CAP)

    def command_pre_twist(self, t_s: float, travel_m: float, max_travel_m: float) -> bool:
        """This period's commanded twist travel of the leg: counted, or (when it would pass
        the travel limit) the pre-twist ends first (``cap``). True = the period runs."""
        twist = self.pre_twist
        limit_m = self.settings.b3_travel_cap_fraction * max_travel_m
        if twist.commanded_m + abs(float(travel_m)) > limit_m + 1e-12:
            self.end_pre_twist(t_s, B3End.TRAVEL_CAP)
            return False
        twist.commanded_m += abs(float(travel_m))
        twist.periods += 1
        return True

    def end_pre_twist(self, t_s: float, reason: B3End) -> None:
        leg = self.pre_twist_leg
        if leg is None:
            return
        twist = self.pre_twist
        self.b3_episodes.append({"leg": LEG_ORDER[leg], "start_s": twist.start_s,
                                 "end_s": float(t_s), "end": str(reason),
                                 "periods": twist.periods,
                                 "commanded_travel_m": round(twist.commanded_m, 9)})
        self.counts[leg].b3_periods += twist.periods
        if reason is B3End.PROTECT:
            self.protect_blocked_legs.add(leg)
        self.pre_twist = _PreTwist()

    def clear_protect_block(self) -> None:
        """Outside LEVEL: a later R-5 prediction may start a pre-twist on any leg again."""
        self.protect_blocked_legs.clear()

    # record ------------------------------------------------------------------------
    def _record_trace(self, inputs: FloorInputs, requested: NDArray[np.float64],
                      output: NDArray[np.float64]) -> None:
        self._trace_t_s.append(float(inputs.t_s))
        self._trace_rows.append({
            "input_m_s": requested.copy(), "output_m_s": output.copy(),
            "a1_floor_m_s": np.array([state.floor_m_s if state.is_floor_on else np.nan
                                      for state in self._deadband]),
            "a2_lower_bound_m": np.array([fill.lower_bound_m if fill.is_on else np.nan
                                          for fill in self._fill]),
            "a2_planned_m_s": np.array([fill.planned_m_s if fill.is_on else np.nan
                                        for fill in self._fill]),
            "a2_commanded_m": np.full(LEG_COUNT, np.nan),
            "a1_on": np.array([state.is_floor_on for state in self._deadband]),
            "a2_on": np.array([fill.is_on for fill in self._fill]),
            "b1_blocked": self._pending_b1_blocked.copy(),
            "protected": np.asarray(inputs.protected, bool).copy(),
            "event_leg": np.array(NO_LEG if self.event_leg is None else self.event_leg,
                                  np.int8),
            "pre_twist_leg": np.array(
                NO_LEG if self.pre_twist_leg is None else self.pre_twist_leg, np.int8),
            "g2_split": np.array(False)})
        if self.settings.has(LsbComponent.BLIND_FILL):
            self._trace_rows[-1].update({
                "ib_floor_m_s": np.array([state.floor_m_s if state.is_floor_on else np.nan
                                          for state in self._blind]),
                "ib_on": np.array([state.is_floor_on for state in self._blind]),
                "ib_stretch_periods": np.array([state.stretch_periods for state in self._blind],
                                               np.int32)})
        self._pending_b1_blocked = np.zeros(LEG_COUNT, bool)

    def trace_arrays_at(self, t_s: NDArray[np.float64]) -> dict[str, NDArray[Any]]:
        """``lsb_*`` T4h arrays on the reads ``t_s`` (row k = the update at ``t_s[k]``);
        ``lsb_read_found`` marks the reads with a row."""
        t_s = np.asarray(t_s, float)
        shape = (len(t_s), LEG_COUNT)
        arrays: dict[str, NDArray[Any]] = {name: np.full(shape, np.nan)
                                           for name in TRACE_FLOAT_FIELDS}
        arrays.update({name: np.zeros(shape, bool) for name in TRACE_FLAG_FIELDS})
        arrays["event_leg"] = np.full(len(t_s), NO_LEG, np.int8)
        arrays["pre_twist_leg"] = np.full(len(t_s), NO_LEG, np.int8)
        arrays.update({name: np.zeros(len(t_s), bool) for name in TRACE_PERIOD_FLAGS})
        if self.settings.has(LsbComponent.BLIND_FILL):  # edition 7 arrays only with A_ib
            arrays["ib_floor_m_s"] = np.full(shape, np.nan)
            arrays["ib_on"] = np.zeros(shape, bool)
            arrays["ib_stretch_periods"] = np.zeros(shape, np.int32)
        found = np.zeros(len(t_s), bool)
        logged_t = np.asarray(self._trace_t_s, float)
        for k, read_t in enumerate(t_s):
            matches = np.flatnonzero(np.abs(logged_t - read_t) <= TIME_MATCH_TOLERANCE_S)
            if not len(matches):
                continue
            found[k] = True
            for name, values in self._trace_rows[int(matches[-1])].items():
                arrays[name][k] = values
        out = {TRACE_ARRAY_PREFIX + name: values for name, values in arrays.items()}
        out[TRACE_ARRAY_PREFIX + "read_found"] = found
        return out

    def record(self) -> dict[str, Any]:
        """The ``lsb_record`` of the run (spec 3.1 .. 3.3 "기록"; record only); with ``A_ib``
        also its ``blind`` block (edition 7 3.1)."""
        record = self._edition_6_record()
        if self.settings.has(LsbComponent.BLIND_FILL):
            record["blind"] = self.blind_record()
        return record

    def _edition_6_record(self) -> dict[str, Any]:
        return {"components": list(self.settings.components),
                "settings": self.settings.to_meta(),
                "legs": {LEG_ORDER[leg]: counts.to_meta()
                         for leg, counts in enumerate(self.counts)},
                "b_episodes": [dict(episode) for episode in self.b_episodes],
                "b_active_leg": None if self.event_leg is None else LEG_ORDER[self.event_leg],
                "b3_episodes": [dict(episode) for episode in self.b3_episodes],
                "b3_active_leg": (None if self.pre_twist_leg is None
                                  else LEG_ORDER[self.pre_twist_leg]),
                "g2_split_periods": self.g2_split_periods,
                "trace_reads": len(self._trace_t_s)}


__all__ = [
    "BLIND_LATCH_EVENT",
    "BLIND_PROTECT_EVENT",
    "CAP_EVENT",
    "COMPONENT_ORDER",
    "TRACE_ARRAY_PREFIX",
    "A1End",
    "A2End",
    "B3End",
    "BEnd",
    "BlindCondition",
    "BlindEnd",
    "CompletionFlags",
    "blind_field_names",
    "EVENT_COMPONENTS",
    "CylinderGeometry",
    "FloorInputs",
    "LockAnchor",
    "LockStartB",
    "LockStartBSettings",
    "LsbComponent",
    "deadbeat_fill_speed",
    "extend_fill_bound_m",
    "parameter_names",
    "retract_fill_bound",
    "stopping_travel_m",
    "void_estimate_m",
]
