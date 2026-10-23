"""Roll / pitch target acceptance A0-A4 and the target reference ramp (engine independent).

Specification ``00_docs/04_control/s6_control_spec.md`` section 2 (control-expert, adopted by
the user on 2026-10-21: U1 reject, U4 ramp 0.4 / 0.25 deg/s) and its revision 2 sections 12-13
(R3.1: floor estimate for the verification mode, U10 (a), U11 epsilon_u 0.01, U12 operating
mode unchanged), from CLAUDE.md '미정 사항' (provisional axis caps pitch +-3 deg, roll +-4 deg)
and ``00_docs/01_dynamics/dynamics_model.md`` 3.12.6 (rule A), 3.13 (crawler compliance).

A target is judged in this order, the first failed check gives the code:

* A0 finite angles (``REJ_TARGET_INVALID``),
* A1 D8 floor: ``|phi_g^| / Phi_r + |theta_g^| / Theta_r <= 1 + eps_u`` (``REJ_SLOPE_D8``),
* A2 axis caps ``|phi_t| <= 4 deg``, ``|theta_t| <= 3 deg`` (``REJ_TARGET_AXIS_CAP``),
* A3 absolute diamond ``|phi_t| / 4.4 + |theta_t| / 3.2 <= 1`` (``REJ_TARGET_ABS``),
* A4 relative diamond ``|phi_t - phi_g^| / Phi_r + |theta_t - theta_g^| / Theta_r <= 1 + eps_u``
  (``REJ_TARGET_REL``).

Spec revision 20 86.3 (R7): ``Theta_r`` of A1 and A4 may differ on the nose-up side
(:attr:`TargetLimits.relative_pitch_span_nose_up_rad`, default ``None`` = symmetric). The side
is the sign of the relative pitch term ``theta_t - theta_g^`` of rule A (> 0 = the floor is
nose up of the target), the same quantity as the REANCHOR direction rule
(``theta_anchor - theta_t ~ -(theta_t - theta_g)``); A1 judges the floor against a level
target, so its nose-up side is ``theta_g^ < 0``. The absolute diamond A3 stays symmetric (a
nose-up target on a flat floor loads the machine like a nose-down floor).
:meth:`TargetLimits.interim_b` is the operating preset of the provisional nose-up 3.1 deg.

``(phi_g^, theta_g^)`` is the floor attitude estimated from the attitude measured on the
crawler in CHECK, ``(phi_c, theta_c)``, with a :class:`CrawlerSettleMap` (spec 13.1):
``phi_g^ = phi_c / (1 + k_phi)`` and ``theta_g^ = (theta_c - theta_0) / (1 + k_dn)`` nose down
of the flat settle pitch ``theta_0`` (``k_up`` nose up). The crawler sinks into its rollers more
at the front, so the body on the crawler tilts more than the floor (top level: +0.17 deg on a
flat floor, +0.32 deg nose down at 3.5 deg). **The operating mode uses the identity map** (the
measured attitude, as before, spec U12) and ``eps_u`` 1e-9; the verification mode (5.5 / 3.5 deg,
simulation checks only) uses the map fitted to the Chrono crawler model of its auger level and
``eps_u`` 0.01. A2 and A3 look at the target only and keep the 1e-9 tolerance in both modes.
A5 (stroke prediction, READY only) needs the strokes and lives in ``c2.py``.

A rejected target is refused by default (U1). :attr:`TargetAcceptance.PROJECT` (option) accepts
the point where the segment from the current target to the requested one leaves the accepted
set; :attr:`TargetAcceptance.OFF` accepts everything and is meant only for replaying
reduced-model traces beyond the limits (the regression tests).

Angles in rad (roll about x, left up +; pitch about y, nose down +, as the IMU reports them).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

# Spec 2.3: comparisons with a relative 1e-9 so that boundary points are accepted.
LIMIT_TOLERANCE = 1e-9

# Spec 13.1 U11: usage tolerance of A1 / A4 in the verification mode, the settle residual of the
# 1 s CHECK mean (Chrono 5 s spread 0.017 deg); ASSUMPTION.
VERIFICATION_USAGE_TOLERANCE = 0.01

# Bisection steps of the projection; 2^-60 of the segment is far below the IMU resolution.
PROJECTION_BISECTION_STEPS = 60

# Spec 2.4 R1 (U4): reference ramp rates.
ROLL_RAMP_RATE_RAD_S = math.radians(0.4)
PITCH_RAMP_RATE_RAD_S = math.radians(0.25)

# Spec revision 20 86.3: provisional nose-up half-span B (user decision 2026-10-22, "C first,
# provisional B"); back to 3.2 deg under dynamics_model.md 5.13.5 supplements 4 and 5.
INTERIM_B_NOSE_UP_PITCH_SPAN_RAD = math.radians(3.1)


class TargetAcceptance(StrEnum):
    """What happens to a target outside the accepted set."""

    REJECT = "reject"
    """Refuse it with its code (U1, default)."""
    PROJECT = "project"
    """Accept the projection toward the current target, event ``WARN_TARGET_PROJECTED``."""
    OFF = "off"
    """Accept everything (trace replays beyond the limits only)."""


class SlopeLimitMode(StrEnum):
    """Half-spans of the D8 / relative diamond (spec 2.3)."""

    OPERATING = "operating"
    """(4.4, 3.2) deg, the operating limit (CLAUDE.md '경사 운용 한계')."""
    VERIFICATION = "verification"
    """(5.5, 3.5) deg on the floor, the D8 verification range (simulation checks only)."""


class TargetCode(StrEnum):
    """Result codes of a target request (spec 2.3)."""

    ACCEPTED = "ACCEPTED"
    PENDING_CHECK = "PENDING_CHECK"
    """Request in IDLE: judged at the end of the restarted CHECK."""
    REJ_TARGET_INVALID = "REJ_TARGET_INVALID"
    REJ_SLOPE_D8 = "REJ_SLOPE_D8"
    REJ_TARGET_AXIS_CAP = "REJ_TARGET_AXIS_CAP"
    REJ_TARGET_ABS = "REJ_TARGET_ABS"
    REJ_TARGET_REL = "REJ_TARGET_REL"
    REJ_TARGET_STROKE = "REJ_TARGET_STROKE"
    REJ_BUSY = "REJ_BUSY"

    @property
    def is_rejection(self) -> bool:
        return self.startswith("REJ_")


@dataclass(frozen=True)
class AttitudeTarget:
    """Body roll and pitch target (rad); A0 checks that both are finite."""

    roll_rad: float = 0.0
    pitch_rad: float = 0.0

    @classmethod
    def from_degrees(cls, roll_deg: float, pitch_deg: float) -> AttitudeTarget:
        """Target given in degrees."""
        return cls(math.radians(roll_deg), math.radians(pitch_deg))

    @property
    def is_finite(self) -> bool:
        return math.isfinite(self.roll_rad) and math.isfinite(self.pitch_rad)

    def toward(self, other: AttitudeTarget, fraction: float) -> AttitudeTarget:
        """The point ``fraction`` of the way from this target to ``other``."""
        return AttitudeTarget(
            self.roll_rad + fraction * (other.roll_rad - self.roll_rad),
            self.pitch_rad + fraction * (other.pitch_rad - self.pitch_rad),
        )


# --- crawler settle map (spec 13.1, X1) ----------------------------------------------------

# Spec 13.1 table, fitted per auger level to the four Chrono vertices (flat, +-3.5 deg pitch,
# roll 5.5 deg): (theta_0 deg, k_dn, k_up, k_phi). Chrono stage-2 snapshots 20261021_195044,
# crawler layout D, normal stiffness 1e8 N/m, Q12 bushing k_t / k_n 0.40, mass case C;
# ASSUMPTION, refit when the snapshots are rebuilt (spec 13.3 K6).
_SETTLE_MAP_COEFFICIENTS = {
    "top": (0.17366, 0.04298, 0.02478, 0.01007),
    "middle": (0.17272, 0.02711, 0.01927, 0.00772),
    "bottom": (0.17180, 0.01742, 0.01381, 0.00539),
}
SETTLE_MAP_SOURCE = "Chrono stage-2 snapshots 20261021_195044, ASSUMPTION (s6_control_spec 13.1)"


@dataclass(frozen=True)
class CrawlerSettleMap:
    """Attitude on the crawler <-> floor attitude (spec 13.1); the identity in operation.

    Attributes:
        theta0_rad: Settle pitch on a flat floor (nose down +).
        k_dn: Extra tilt ratio on a nose-down floor (``theta_c >= theta_0``).
        k_up: Extra tilt ratio on a nose-up floor.
        k_phi: Extra tilt ratio of roll.
    """

    theta0_rad: float = 0.0
    k_dn: float = 0.0
    k_up: float = 0.0
    k_phi: float = 0.0

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value!r}")
        for name in ("k_dn", "k_up", "k_phi"):
            if not 1.0 + getattr(self, name) > 0.0:
                raise ValueError(f"1 + {name} must be > 0, got {getattr(self, name)!r}")

    @classmethod
    def identity(cls) -> CrawlerSettleMap:
        """No crawler compliance: the floor estimate is the measured attitude."""
        return cls()

    @classmethod
    def for_level(cls, level: str) -> CrawlerSettleMap:
        """Map of an auger level, ``top`` / ``middle`` / ``bottom`` (spec 13.1 table)."""
        try:
            theta0_deg, k_dn, k_up, k_phi = _SETTLE_MAP_COEFFICIENTS[str(level)]
        except KeyError:
            levels = sorted(_SETTLE_MAP_COEFFICIENTS)
            raise ValueError(f"level must be one of {levels}, got {level!r}") from None
        return cls(math.radians(theta0_deg), k_dn, k_up, k_phi)

    @property
    def is_identity(self) -> bool:
        return self == CrawlerSettleMap.identity()

    def floor_from_crawler(self, crawler_attitude_rad: tuple[float, float]) -> tuple[float, float]:
        """``(phi_g^, theta_g^)`` from the attitude measured on the crawler."""
        roll, pitch = crawler_attitude_rad
        pitch_ratio = self.k_dn if pitch >= self.theta0_rad else self.k_up
        return roll / (1.0 + self.k_phi), (pitch - self.theta0_rad) / (1.0 + pitch_ratio)

    def crawler_from_floor(self, floor_attitude_rad: tuple[float, float]) -> tuple[float, float]:
        """Inverse of :meth:`floor_from_crawler` (tests and case setup)."""
        roll, pitch = floor_attitude_rad
        pitch_ratio = self.k_dn if pitch >= 0.0 else self.k_up
        return roll * (1.0 + self.k_phi), self.theta0_rad + pitch * (1.0 + pitch_ratio)

    def to_meta(self) -> dict[str, float]:
        """Fields in degrees (theta_0) and ratios, JSON-ready."""
        return {
            "theta0_deg": math.degrees(self.theta0_rad),
            "k_dn": self.k_dn,
            "k_up": self.k_up,
            "k_phi": self.k_phi,
        }


@dataclass(frozen=True)
class TargetLimits:
    """Axis caps, diamond half-spans (rad) and the A1 / A4 usage tolerance.

    Attributes:
        max_roll_rad: Axis cap ``C_phi`` (4 deg).
        max_pitch_rad: Axis cap ``C_theta`` (3 deg).
        absolute_roll_span_rad: ``Phi_a`` (4.4 deg, fixed).
        absolute_pitch_span_rad: ``Theta_a`` (3.2 deg, fixed).
        relative_roll_span_rad: ``Phi_r`` of the D8 and relative diamonds.
        relative_pitch_span_rad: ``Theta_r`` of the D8 and relative diamonds.
        usage_tolerance: ``eps_u`` of A1 and A4 (A2 and A3 keep 1e-9).
        relative_pitch_span_nose_up_rad: ``Theta_r`` on the relative nose-up side
            (``theta_t - theta_g^ > 0``) of the D8 and relative diamonds; ``None`` =
            ``relative_pitch_span_rad`` (spec revision 20 86.3).
    """

    max_roll_rad: float = math.radians(4.0)
    max_pitch_rad: float = math.radians(3.0)
    absolute_roll_span_rad: float = math.radians(4.4)
    absolute_pitch_span_rad: float = math.radians(3.2)
    relative_roll_span_rad: float = math.radians(4.4)
    relative_pitch_span_rad: float = math.radians(3.2)
    usage_tolerance: float = LIMIT_TOLERANCE
    relative_pitch_span_nose_up_rad: float | None = None

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if value is None and name == "relative_pitch_span_nose_up_rad":
                continue
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{name} must be finite and > 0, got {value!r}")

    def relative_pitch_span_for(self, relative_pitch_rad: float) -> float:
        """``Theta_r`` for a relative pitch ``theta_t - theta_g^`` (> 0 = nose-up side)."""
        nose_up_span = self.relative_pitch_span_nose_up_rad
        if relative_pitch_rad > 0.0 and nose_up_span is not None:
            return nose_up_span
        return self.relative_pitch_span_rad

    @classmethod
    def interim_b(cls) -> TargetLimits:
        """Operating limits with the provisional nose-up half-span B, 3.1 deg.

        Provisional B (user decision 2026-10-22, "C first, provisional B"): the relative
        nose-up side of A1 / A4 uses 3.1 deg, the nose-down side and the absolute diamond keep
        3.2 deg. The return to 3.2 deg follows ``dynamics_model.md`` 5.13.5 supplements 4 and
        5. While B holds, operation uses this preset, not the default (``None`` = 3.2 deg).
        """
        return cls(relative_pitch_span_nose_up_rad=INTERIM_B_NOSE_UP_PITCH_SPAN_RAD)

    @classmethod
    def for_mode(cls, mode: SlopeLimitMode) -> TargetLimits:
        """Limits of the operating or the verification mode."""
        if SlopeLimitMode(mode) is SlopeLimitMode.VERIFICATION:
            return cls(
                relative_roll_span_rad=math.radians(5.5),
                relative_pitch_span_rad=math.radians(3.5),
                usage_tolerance=VERIFICATION_USAGE_TOLERANCE,
            )
        return cls()


@dataclass(frozen=True)
class TargetCheck:
    """Outcome of one target request.

    Attributes:
        requested: The target asked for.
        accepted: The target to use (requested or projected), ``None`` when not accepted.
        code: ``ACCEPTED``, ``PENDING_CHECK`` or the first failed check.
        crawler_attitude_rad: ``(phi_c, theta_c)`` measured in CHECK, ``None`` if not known.
        floor_estimate_rad: ``(phi_g^, theta_g^)`` used by A1 / A4, ``None`` if not known.
        floor_usage: A1 usage of the floor estimate (``None`` if not known).
    """

    requested: AttitudeTarget
    accepted: AttitudeTarget | None
    code: TargetCode
    crawler_attitude_rad: tuple[float, float] | None = None
    floor_estimate_rad: tuple[float, float] | None = None
    floor_usage: float | None = None

    @property
    def is_accepted(self) -> bool:
        return self.accepted is not None

    @property
    def is_projected(self) -> bool:
        return self.accepted is not None and self.accepted != self.requested

    def to_meta(self) -> dict[str, object]:
        """JSON-serialisable summary for the run meta."""

        def as_list(pair: tuple[float, float] | None) -> list[float] | None:
            return None if pair is None else list(pair)

        accepted = self.accepted
        return {
            "requested_rad": [self.requested.roll_rad, self.requested.pitch_rad],
            "accepted_rad": None if accepted is None else [accepted.roll_rad, accepted.pitch_rad],
            "code": str(self.code),
            "crawler_attitude_rad": as_list(self.crawler_attitude_rad),
            "floor_estimate_rad": as_list(self.floor_estimate_rad),
            "floor_usage": self.floor_usage,
        }


# --- checks --------------------------------------------------------------------------------


def diamond_usage(
    roll_rad: float, pitch_rad: float, roll_span_rad: float, pitch_span_rad: float
) -> float:
    """``|roll| / roll_span + |pitch| / pitch_span``: at most 1 inside the diamond."""
    return abs(roll_rad) / roll_span_rad + abs(pitch_rad) / pitch_span_rad


def _is_within(value: float, limit: float) -> bool:
    return value <= limit * (1.0 + LIMIT_TOLERANCE)


def _relative_tilt_usage(
    relative_roll_rad: float, relative_pitch_rad: float, limits: TargetLimits
) -> float:
    """Usage of a target-minus-floor tilt in the relative diamond (A1 / A4)."""
    return diamond_usage(
        relative_roll_rad,
        relative_pitch_rad,
        limits.relative_roll_span_rad,
        limits.relative_pitch_span_for(relative_pitch_rad),
    )


def floor_usage(floor_attitude_rad: tuple[float, float], limits: TargetLimits) -> float:
    """A1 usage of a floor attitude (D8 diamond with the relative half-spans).

    The floor is judged against a level target, so the relative pitch is ``-theta_g^`` and a
    nose-up floor (``theta_g^ < 0``) uses the nose-up half-span.
    """
    roll, pitch = floor_attitude_rad
    return _relative_tilt_usage(-roll, -pitch, limits)


def relative_usage(
    target: AttitudeTarget, floor_attitude_rad: tuple[float, float], limits: TargetLimits
) -> float:
    """A4 usage: the target tilt relative to the floor, ``(phi_t - phi_g^, theta_t - theta_g^)``."""
    floor_roll, floor_pitch = floor_attitude_rad
    return _relative_tilt_usage(
        target.roll_rad - floor_roll, target.pitch_rad - floor_pitch, limits
    )


def is_floor_inside_d8(
    crawler_attitude_rad: tuple[float, float],
    limits: TargetLimits,
    settle_map: CrawlerSettleMap | None = None,
) -> bool:
    """A1: the floor estimate from the attitude on the crawler inside the D8 diamond."""
    floor = (settle_map or CrawlerSettleMap.identity()).floor_from_crawler(crawler_attitude_rad)
    return floor_usage(floor, limits) <= 1.0 + limits.usage_tolerance


def first_target_failure(
    target: AttitudeTarget,
    crawler_attitude_rad: tuple[float, float],
    limits: TargetLimits,
    settle_map: CrawlerSettleMap | None = None,
) -> TargetCode | None:
    """A0-A4 in order; the first failed check's code, ``None`` when all pass."""
    if not target.is_finite:
        return TargetCode.REJ_TARGET_INVALID
    floor = (settle_map or CrawlerSettleMap.identity()).floor_from_crawler(crawler_attitude_rad)
    if not floor_usage(floor, limits) <= 1.0 + limits.usage_tolerance:
        return TargetCode.REJ_SLOPE_D8
    is_capped = _is_within(abs(target.roll_rad), limits.max_roll_rad) and _is_within(
        abs(target.pitch_rad), limits.max_pitch_rad
    )
    if not is_capped:
        return TargetCode.REJ_TARGET_AXIS_CAP
    absolute = diamond_usage(
        target.roll_rad,
        target.pitch_rad,
        limits.absolute_roll_span_rad,
        limits.absolute_pitch_span_rad,
    )
    if not _is_within(absolute, 1.0):
        return TargetCode.REJ_TARGET_ABS
    if not relative_usage(target, floor, limits) <= 1.0 + limits.usage_tolerance:
        return TargetCode.REJ_TARGET_REL
    return None


def _project(
    anchor: AttitudeTarget,
    requested: AttitudeTarget,
    crawler_attitude_rad: tuple[float, float],
    limits: TargetLimits,
    settle_map: CrawlerSettleMap,
) -> AttitudeTarget:
    """Point where the segment anchor -> requested leaves the accepted set (anchor accepted).

    The accepted set (A2-A4) is convex, so the accepted part of the segment is one interval
    starting at the anchor and bisection finds its end.
    """
    inside, outside = 0.0, 1.0
    for _ in range(PROJECTION_BISECTION_STEPS):
        middle = 0.5 * (inside + outside)
        candidate = anchor.toward(requested, middle)
        if first_target_failure(candidate, crawler_attitude_rad, limits, settle_map) is None:
            inside = middle
        else:
            outside = middle
    return anchor.toward(requested, inside)


def check_target(
    requested: AttitudeTarget,
    crawler_attitude_rad: tuple[float, float],
    limits: TargetLimits,
    acceptance: TargetAcceptance = TargetAcceptance.REJECT,
    current: AttitudeTarget | None = None,
    settle_map: CrawlerSettleMap | None = None,
) -> TargetCheck:
    """Judge a requested target with A0-A4.

    Args:
        requested: Target asked for.
        crawler_attitude_rad: ``(phi_c, theta_c)`` of the CHECK phase.
        limits: Caps, half-spans and tolerance (:meth:`TargetLimits.for_mode`).
        acceptance: Reaction to a failed check (module docstring).
        current: The target in force (READY change); the projection starts from it, from
            level when ``None``.
        settle_map: Crawler settle map for the floor estimate; ``None`` = identity.

    Returns:
        The check. A0 and A1 failures are never projected.
    """
    settle_map = settle_map or CrawlerSettleMap.identity()
    floor = settle_map.floor_from_crawler(crawler_attitude_rad)
    context = {
        "crawler_attitude_rad": crawler_attitude_rad,
        "floor_estimate_rad": floor,
        "floor_usage": floor_usage(floor, limits),
    }
    failure = first_target_failure(requested, crawler_attitude_rad, limits, settle_map)
    if failure is None or acceptance is TargetAcceptance.OFF:
        return TargetCheck(requested, requested, TargetCode.ACCEPTED, **context)
    is_projectable = failure not in (TargetCode.REJ_TARGET_INVALID, TargetCode.REJ_SLOPE_D8)
    if acceptance is TargetAcceptance.REJECT or not is_projectable:
        return TargetCheck(requested, None, failure, **context)
    anchor = current if current is not None else AttitudeTarget()
    projected = _project(anchor, requested, crawler_attitude_rad, limits, settle_map)
    return TargetCheck(requested, projected, failure, **context)


# --- reference ramp ------------------------------------------------------------------------


def ramp_reference(
    reference: AttitudeTarget,
    target: AttitudeTarget,
    period_s: float,
    roll_rate_rad_s: float = ROLL_RAMP_RATE_RAD_S,
    pitch_rate_rad_s: float = PITCH_RAMP_RATE_RAD_S,
) -> AttitudeTarget:
    """One period of the reference ramp (spec 2.4 R1).

    ``lambda = min(1, T / (|d_phi| / r_phi + |d_theta| / r_theta))``, the reference moves by
    ``lambda`` of the remaining difference, so ``|phi_r_dot| / r_phi + |theta_r_dot| / r_theta
    <= 1`` and the last period lands exactly on the target.
    """
    remaining_s = (
        abs(target.roll_rad - reference.roll_rad) / roll_rate_rad_s
        + abs(target.pitch_rad - reference.pitch_rad) / pitch_rate_rad_s
    )
    if remaining_s <= period_s:
        return target
    return reference.toward(target, period_s / remaining_s)
