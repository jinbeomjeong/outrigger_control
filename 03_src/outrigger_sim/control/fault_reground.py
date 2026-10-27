"""FAULT_REGROUND of C2: re-ground the lifted legs after a head-sensor fault, then FAULT.

Spec ``00_docs/04_control/s6_control_spec.md`` revision 64 section 323 (P-S8-24, user decision
U-S8-68 of 2026-10-27). A head-pressure fault (D1) used to stop every leg at once (FAULT). A leg
that the diagonal rocking had lifted at that moment then stayed in the air. With
:class:`FaultRegroundSettings` ``enable`` the controller instead:

1. stops every leg for one period (as FAULT does) and picks the re-ground targets from the
   0.3 s before the fault: a healthy-sensor leg whose lower load estimate was below 0 N on the
   last two samples, and the faulty leg itself when the Newton estimate, its rod-side rise or
   the four-pad plane residual says it carries little load (323.3);
2. extends the targets one at a time (healthy legs first, lowest load first) at a slow speed
   with the other legs locked, until contact (323.4) or a travel / time limit (323.5);
3. goes to FAULT when the targets are done, after 15 s, or at once on one of the abort
   conditions of 323.6.

Spec revision 65 section 332 (P-S8-25) corrects the design; each correction is a settings key
whose class default keeps the revision-64 behaviour and the R8 preset turns on:

* ``attitude_abort`` off: abort 2 (raw IMU attitude) is gone, the run records the largest
  change of the levelling (filtered) attitude instead (332.1);
* ``contact_rule = "all_legs_hold"``: contact needs the target's own level and the other legs
  carrying load; the leg stops while that holds and is confirmed after
  ``hold_confirm_samples`` (1.0 s) in a row (332.2);
* ``own_pre_fault_cue``: faulty-leg cue (d), its own lower estimate below 0 N on the two samples
  before the fault sample (332.3);
* ``plane_gap_scaled``: cue (c) and the gap estimate use ``g_i = Delta r_i / (I - P)_ii`` above
  5 mm instead of the raw residual above 1.4 mm (332.3, 329 ④).

Spec revision 70 section 369.4 (P-S8-28, U-S8-79) adds a second entry: a stroke-end FAULT in
LEVEL (``FAULT_STROKE_END`` or ``FAULT_LIFT_STROKE_LIMIT``) re-grounds the healthy legs that
read lifted, with no faulty sensor, each with ``stroke_end_travel_m`` of travel
(``stroke_end_entry``, off by default). The run record keeps its ``trigger``.

This module holds the settings, the run record and the pure judgements; the controller
(``control/c2.py``) feeds them. Units SI (m, s, N, Pa); legs follow ``LEG_ORDER``.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.params import LEG_ORDER

START_EVENT = "fault_reground_start"
"""``fault_reground_start:<legs>`` (legs comma separated, in re-ground order)."""
CONTACT_EVENT = "fault_reground_contact"
"""``fault_reground_contact:<leg>``."""
LIMIT_EVENT = "WARN_FAULT_REGROUND_LIMIT"
"""``WARN_FAULT_REGROUND_LIMIT:<leg>:<travel|time>``."""
END_EVENT = "fault_reground_end"
"""``fault_reground_end:<n_contact>/<n>``."""
ABORT_EVENT = "WARN_FAULT_REGROUND_ABORT"
"""``WARN_FAULT_REGROUND_ABORT:<end_reason>`` on an abort or the total time (spec rev. 65 329 ⑧);
``done`` and ``no_target`` raise none."""

# Spec 323.5 (ASSUMPTION values of 327.3)
SPEED_FRACTION_HEALTHY = 0.25
"""Healthy-sensor leg: the leg-mode re-approach speed (P-R8-12), 5.23 mm/s."""
SPEED_FRACTION_FAULTY = 0.15
"""Faulty-sensor leg (load unknown): 3.14 mm/s."""
MAX_TRAVEL_M = 0.030
TRAVEL_GAP_MARGIN_M = 0.005
"""Travel limit ``min(gap + 5 mm, 30 mm)``; 30 mm without a gap estimate."""
MAX_LEG_DURATION_S = 8.0
MAX_TOTAL_DURATION_S = 15.0
# Spec 323.3 / 323.4 / 323.6
TARGET_WINDOW_S = 0.3
"""The target cues look at this window before (and including) the fault sample."""
HEALTHY_LIFTED_LEVEL_N = 0.0
HEALTHY_LIFTED_SAMPLES = 2
"""Healthy leg: lower load estimate below 0 N on two samples (as the RT strong check, 228.3)."""
FAULTY_ROD_RISE_FRACTION = 0.5
"""Faulty leg cue (b): rod-side rise of at least ``0.5 R_lb(s) p_h,lock``."""
PLANE_RESIDUAL_THRESHOLD_M = 1.4e-3
"""Faulty leg cue (c) and the gap estimate: four-pad plane residual change (the G2 level)."""
PLANE_GAP_THRESHOLD_M = 5.0e-3
"""Spec rev. 65 332.3: the same cue on the scaled gap ``Delta r_i / (I - P)_ii`` (the G1-L
level; the 1.4 mm above was the G2 residual level carried over by mistake)."""
HOLD_CONFIRM_SAMPLES = 10
"""Spec rev. 65 332.2: 1.0 s, longer than the harness teeter (about 0.75 s) and the Chrono
rocking (1.24-2.9 Hz)."""
CONTACT_MARGIN_N = 5000.0
HEALTHY_CONTACT_SAMPLES = 3
FAULTY_CONTACT_SAMPLES = 2
FAULTY_CONTACT_WINDOW_S = 0.2
"""Faulty leg: the other legs' sum is averaged over this window (at the start and now)."""
PROTECT_SAMPLES = 5
"""Abort 1 (spec rev. 64 323.9 ④): 0.5 s in a row below ``F_min`` (the U57 adjacent lift-off
allowance; a passive rocking dip is shorter)."""
ATTITUDE_ABORT_RAD = math.radians(0.5)
ATTITUDE_WINDOW_S = 0.5
"""Abort 2 (323.9 ④): 0.5 s mean raw attitude against the mean of ``[t_f - 0.5, t_f]`` (one to
1.5 periods of the 1.24-2.9 Hz rocking)."""
STROKE_END_ABORT_MARGIN_M = 0.010
"""Abort 5: the moving leg reaches ``s_soft - 10 mm (end margin) - 10 mm``."""
# R_lb(s): the low end of the lock-law ratio band (spec rev. 49 219, H-S8-2 10.2 opposite end)
RATIO_LOWER_HEAD_DEAD_M = 0.05
RATIO_LOWER_ROD_DEAD_M = 0.10
RATIO_LOWER_KAPPA = 1.10


class RegroundCue(StrEnum):
    """Why a leg is a re-ground target (spec 323.3)."""

    LOWER_BOUND = "lower_bound"
    """Healthy sensor: lower load estimate below 0 N on the last two samples."""
    NEWTON = "newton"
    """Faulty sensor (a): ``M_eff f_z - sum_(i != j) F_i < F_min`` over the window."""
    ROD_RISE = "rod_rise"
    """Faulty sensor (b): the locked rod side rose by at least ``0.5 R_lb(s) p_h,lock``."""
    PLANE = "plane"
    """Faulty sensor (c): the four-pad plane residual sees the leg more than 1.4 mm up (or the
    scaled gap more than 5 mm, ``plane_gap_scaled``)."""
    OWN_PRE_FAULT = "own_pre_fault"
    """Faulty sensor (d), spec rev. 65 332.3: its own lower load estimate below 0 N on the two
    samples before the fault sample (the readings before the jump are valid)."""


class ContactRule(StrEnum):
    """How a re-grounded leg's contact is judged (``FaultRegroundSettings.contact_rule``)."""

    TARGET_ONLY = "target_only"
    """Spec rev. 64 323.4: the target's own level on 3 (healthy) / 2 (faulty) samples."""
    ALL_LEGS_HOLD = "all_legs_hold"
    """Spec rev. 65 332.2: the target's own level, every other healthy leg at ``F_min`` and a
    faulty non-target leg's Newton estimate at ``F_min``; the leg stops while that holds and
    the contact is confirmed after ``hold_confirm_samples`` in a row."""


class TargetOutcome(StrEnum):
    CONTACT = "contact"
    TRAVEL = "travel"
    TIME = "time"
    ABORTED = "aborted"
    """The run ended (abort or total time) while this leg moved."""


class RegroundTrigger(StrEnum):
    """What started the FAULT_REGROUND (meta ``trigger``)."""

    HEAD_FAULT = "head_fault"
    """A head-sensor fault (spec rev. 64 323.2)."""
    STROKE_END = "stroke_end"
    """A stroke-end FAULT in LEVEL (spec rev. 70 369.4, U-S8-79)."""


class RegroundEnd(StrEnum):
    """Why FAULT_REGROUND ended (meta ``end_reason``)."""

    NO_TARGET = "no_target"
    """No leg qualified: FAULT on the fault sample, as without FAULT_REGROUND (G4-7)."""
    DONE = "done"
    TOTAL_TIME = "total_time"
    PROTECTED_LEG_LOW = "protected_leg_low"
    """Abort 1: a healthy leg (neither faulty nor a target) read below ``F_min`` for 0.5 s."""
    ATTITUDE = "attitude"
    """Abort 2 (``attitude_abort`` only): the 0.5 s mean raw roll or pitch moved more than
    0.5 deg from its mean over the 0.5 s up to the fault sample."""
    NEW_HEAD_FAULT = "new_head_fault"
    """Abort 3: another leg's head sensor faulted."""
    PRESSURE_WARNING = "pressure_warning"
    """Abort 4: a rod side or a healthy head above the 345 bar warning."""
    STROKE_END = "stroke_end"
    """Abort 5: the moving leg entered the stroke-end zone."""

    @property
    def is_abort(self) -> bool:
        """An abort or the total time (``WARN_FAULT_REGROUND_ABORT``), not a regular end."""
        return self not in (RegroundEnd.NO_TARGET, RegroundEnd.DONE)


@dataclass(frozen=True)
class FaultRegroundSettings:
    """Spec 323.5 / 323.6 keys and the rev. 65 332.5 keys (P-S8-25).

    ``enable`` is off by default; :meth:`C2Config.with_10hz_d1` turns it on together with the
    rev. 65 values. The rev. 65 keys default to the rev. 64 behaviour except
    ``attitude_abort``, which is off (spec 332.5: switched off instead of removed). All are
    plain class-level defaults, so configs unpickled from older code read them.
    """

    enable: bool = False
    speed_fraction_healthy: float = SPEED_FRACTION_HEALTHY
    speed_fraction_faulty: float = SPEED_FRACTION_FAULTY
    max_travel_m: float = MAX_TRAVEL_M
    travel_gap_margin_m: float = TRAVEL_GAP_MARGIN_M
    max_leg_duration_s: float = MAX_LEG_DURATION_S
    max_total_duration_s: float = MAX_TOTAL_DURATION_S
    target_window_s: float = TARGET_WINDOW_S
    healthy_lifted_level_N: float = HEALTHY_LIFTED_LEVEL_N
    healthy_lifted_samples: int = HEALTHY_LIFTED_SAMPLES
    faulty_rod_rise_fraction: float = FAULTY_ROD_RISE_FRACTION
    plane_residual_threshold_m: float = PLANE_RESIDUAL_THRESHOLD_M
    contact_margin_N: float = CONTACT_MARGIN_N
    healthy_contact_samples: int = HEALTHY_CONTACT_SAMPLES
    faulty_contact_samples: int = FAULTY_CONTACT_SAMPLES
    faulty_contact_window_s: float = FAULTY_CONTACT_WINDOW_S
    protect_samples: int = PROTECT_SAMPLES
    attitude_abort_rad: float = ATTITUDE_ABORT_RAD
    attitude_window_s: float = ATTITUDE_WINDOW_S
    stroke_end_abort_margin_m: float = STROKE_END_ABORT_MARGIN_M
    # spec rev. 65 332.5 (P-S8-25, values ASSUMPTION)
    attitude_abort: bool = False
    """Abort 2 on the raw IMU attitude (332.1: off; True = the rev. 64 rule)."""
    contact_rule: ContactRule = ContactRule.TARGET_ONLY
    hold_confirm_samples: int = HOLD_CONFIRM_SAMPLES
    """``all_legs_hold``: samples in a row that confirm the contact."""
    own_pre_fault_cue: bool = False
    """Faulty-leg cue (d) of 332.3."""
    plane_gap_scaled: bool = False
    """Cue (c) and the gap estimate on ``Delta r_i / (I - P)_ii`` above
    ``plane_gap_threshold_m`` (332.3)."""
    plane_gap_threshold_m: float = PLANE_GAP_THRESHOLD_M
    # spec rev. 70 369.4 (P-S8-28, U-S8-79)
    stroke_end_entry: bool = False
    """A stroke-end FAULT in LEVEL re-grounds the lifted healthy legs first."""
    stroke_end_travel_m: float = MAX_TRAVEL_M
    """Travel limit of every target of a stroke-end run (the plane-gap estimate reads a
    non-planar floor as too small a gap, spec rev. 70 367 R / R30)."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "contact_rule", ContactRule(self.contact_rule))
        for name in ("speed_fraction_healthy", "speed_fraction_faulty"):
            if not 0.0 < getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in (0, 1], got {getattr(self, name)!r}")
        for name in ("max_travel_m", "max_leg_duration_s", "max_total_duration_s",
                     "target_window_s", "faulty_contact_window_s", "attitude_abort_rad",
                     "attitude_window_s", "stroke_end_travel_m"):
            if not getattr(self, name) > 0.0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)!r}")
        for name in ("travel_gap_margin_m", "plane_residual_threshold_m", "contact_margin_N",
                     "faulty_rod_rise_fraction", "stroke_end_abort_margin_m",
                     "plane_gap_threshold_m"):
            if not getattr(self, name) >= 0.0:
                raise ValueError(f"{name} must be >= 0, got {getattr(self, name)!r}")
        for name in ("healthy_lifted_samples", "healthy_contact_samples",
                     "faulty_contact_samples", "protect_samples", "hold_confirm_samples"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be an int >= 1, got {value!r}")

    def travel_limit_m(self, gap_m: float | None) -> float:
        """323.5 ``min(gap + 5 mm, 30 mm)``; 30 mm without a gap estimate."""
        if gap_m is None:
            return self.max_travel_m
        return min(gap_m + self.travel_gap_margin_m, self.max_travel_m)

    def speed_fraction(self, is_faulty: bool) -> float:
        return self.speed_fraction_faulty if is_faulty else self.speed_fraction_healthy

    def contact_samples(self, is_faulty: bool) -> int:
        """Samples in a row that end a target with contact."""
        if self.contact_rule is ContactRule.ALL_LEGS_HOLD:
            return self.hold_confirm_samples
        return self.faulty_contact_samples if is_faulty else self.healthy_contact_samples

    @property
    def plane_cue_threshold_m(self) -> float:
        """Level of cue (c) and of the gap estimate, on the value :attr:`plane_gap_scaled`
        selects (scaled gap or raw residual change)."""
        if self.plane_gap_scaled:
            return self.plane_gap_threshold_m
        return self.plane_residual_threshold_m

    def to_meta(self) -> dict[str, Any]:
        meta = {name: getattr(self, name) for name in self.__dataclass_fields__}
        meta["contact_rule"] = str(self.contact_rule)
        return meta


@dataclass(frozen=True)
class RegroundSample:
    """One period of the readings FAULT_REGROUND looks back on (kept only when enabled)."""

    t_s: float
    load_reading_N: NDArray[np.float64]
    """Nominal cylinder-force readings (net force, zero offsets removed)."""
    load_estimate_N: NDArray[np.float64]
    """Lower load estimates (lower reading minus the band)."""
    rod_pressure_Pa: NDArray[np.float64] | None
    motor_stroke_m: NDArray[np.float64]
    imu_f_z_m_s2: float | None
    """D1'' ``f_z`` of the monitor (lever term removed)."""


def window_samples(
    history: deque[RegroundSample], window_s: float, period_s: float
) -> list[RegroundSample]:
    """The newest ``round(window_s / period_s)`` samples (at least one), oldest first."""
    count = max(1, round(window_s / period_s))
    return list(history)[-count:]


def pre_fault_load_estimates_N(
    history: deque[RegroundSample], leg: int, count: int
) -> list[float]:
    """Cue (d): the leg's lower load estimates on the ``count`` samples before the newest one
    (the fault sample), oldest first; fewer when the history is shorter."""
    before_fault = list(history)[-count - 1:-1]
    return [float(sample.load_estimate_N[leg]) for sample in before_fault]


def other_legs_mean_sum_N(samples: list[RegroundSample], leg: int) -> float:
    """Mean over ``samples`` of ``sum_(i != leg) F_i`` (nominal readings)."""
    sums = [float(np.sum(np.delete(sample.load_reading_N, leg))) for sample in samples]
    return float(np.mean(sums))


def newton_leg_load_N(samples: list[RegroundSample], leg: int, mass_kg: float) -> float | None:
    """323.3 (a) ``M_eff mean(f_z) - mean(sum_(i != j) F_i)``; ``None`` without every ``f_z``."""
    f_z = [sample.imu_f_z_m_s2 for sample in samples]
    if any(value is None or not math.isfinite(value) for value in f_z):
        return None
    return mass_kg * float(np.mean(f_z)) - other_legs_mean_sum_N(samples, leg)


def ratio_lower_bound(stroke_m: float, stroke_max_m: float) -> float:
    """``R_lb(s) = (L_0h,min + s) / (L_0r,max + s_max - s) / kappa`` (the low end of the lock
    law band, spec rev. 49 219; ``s`` cut to ``[0, s_max]``)."""
    stroke = min(max(stroke_m, 0.0), stroke_max_m)
    head_column_m = RATIO_LOWER_HEAD_DEAD_M + stroke
    rod_column_m = RATIO_LOWER_ROD_DEAD_M + stroke_max_m - stroke
    return head_column_m / rod_column_m / RATIO_LOWER_KAPPA


@dataclass
class RegroundTarget:
    """One leg of the run and how its re-ground went."""

    leg: int
    is_faulty: bool
    cues: tuple[str, ...]
    gap_m: float | None
    """Plane-residual gap estimate (only when the residual sees the leg up), else ``None``."""
    max_travel_m: float
    start_s: float | None = None
    start_motor_stroke_m: float | None = None
    start_other_sum_N: float | None = None
    """Faulty leg: mean other-leg sum over the contact window at the start (323.4)."""
    contact_samples_seen: int = 0
    hold_count: int = 0
    """``all_legs_hold``: stops before the confirmation (each new run of the contact
    condition counts once; spec rev. 65 333 G4-8)."""
    end_s: float | None = None
    travel_m: float | None = None
    outcome: TargetOutcome | None = None

    def to_meta(self) -> dict[str, Any]:
        duration_s = None
        if self.start_s is not None and self.end_s is not None:
            duration_s = self.end_s - self.start_s
        return {
            "leg": LEG_ORDER[self.leg],
            "sensor": "faulty" if self.is_faulty else "healthy",
            "cues": list(self.cues),
            "gap_m": self.gap_m,
            "max_travel_m": self.max_travel_m,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "duration_s": duration_s,
            "travel_m": self.travel_m,
            "outcome": None if self.outcome is None else str(self.outcome),
            "hold_count": self.hold_count,
        }


@dataclass
class FaultRegroundRun:
    """State and record of one FAULT_REGROUND (meta ``fault_reground.run``)."""

    fault_s: float
    fault_legs: tuple[int, ...]
    targets: list[RegroundTarget]
    protected_legs: tuple[int, ...]
    """Healthy legs that are no target (abort 1, spec 323.9 ④)."""
    faulty_cue_values: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Per faulty leg the values behind its three cues (meta, also when it is no target)."""
    fault_attitude_rad: tuple[float, float] | None = None
    """Mean raw (roll, pitch) over ``attitude_window_s`` up to the fault sample (abort 2)."""
    fault_filtered_attitude_rad: tuple[float, float] | None = None
    """Levelling (filtered) (roll, pitch) on the fault sample (spec rev. 65 332.1 record)."""
    max_filtered_attitude_change_rad: float = 0.0
    """Largest ``max(|d roll|, |d pitch|)`` of the filtered attitude against the fault sample,
    over the run up to its end (record only)."""
    active_index: int | None = None
    next_index: int = 0
    protect_low_counts: dict[int, int] = field(default_factory=dict)
    end_s: float | None = None
    end_reason: RegroundEnd | None = None
    trigger: RegroundTrigger = RegroundTrigger.HEAD_FAULT
    """A class-level default, so runs pickled before spec rev. 70 read ``head_fault``."""

    @property
    def active_target(self) -> RegroundTarget | None:
        return None if self.active_index is None else self.targets[self.active_index]

    @property
    def contact_count(self) -> int:
        return sum(target.outcome is TargetOutcome.CONTACT for target in self.targets)

    def to_meta(self) -> dict[str, Any]:
        return {
            "fault_s": self.fault_s,
            "fault_legs": [LEG_ORDER[leg] for leg in self.fault_legs],
            "targets": [target.to_meta() for target in self.targets],
            "faulty_cue_values": {leg: dict(values)
                                  for leg, values in self.faulty_cue_values.items()},
            "protected_legs": [LEG_ORDER[leg] for leg in self.protected_legs],
            "fault_attitude_rad": (
                None if self.fault_attitude_rad is None else list(self.fault_attitude_rad)
            ),
            "max_filtered_attitude_change_rad": self.max_filtered_attitude_change_rad,
            "end_s": self.end_s,
            "end_reason": None if self.end_reason is None else str(self.end_reason),
            "contact_count": self.contact_count,
            "trigger": str(self.trigger),
        }
