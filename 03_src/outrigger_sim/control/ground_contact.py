"""Physics-based combined ground-contact judge and the leg probe (engine independent).

CLAUDE.md '접지 판정' (2026-10-20): the absolute pressure can miss a lifted leg because of the
seal friction ``|f| <= F_s`` (at F_s 12 kN a lifting leg still reads 10.9 kN > F_min), so the
contact of a leg is judged from three physical cues together:

1. **Friction band.** The reading is ``P = F - f`` (cylinder-force basis), so the true force
   lies in ``[P - F_band, P + F_band]`` (:func:`load_bounds_N`, :func:`classify_load`). A leg is
   surely loaded when the lower bound reaches F_min, surely below it when the upper bound does
   not; in between only a probe decides (``00_docs/04_control/c2_design.md`` 10.2, 14.5 5).
2. **Incremental stiffness.** Extending a grounded leg by ``dx`` raises its force by about
   ``S_ii dx`` (``S`` = load sensitivity of the four-leg support); a lifted leg moves freely
   (design 14.6: grounded when ``dP / dx > 0.3 S_ii``).
3. **Attitude response against the kinematics.** Extending a grounded leg tilts the body by
   ``J_i ds`` (:func:`attitude_sensitivity_rad_m`); a lifted leg leaves the attitude unchanged.
   With equal pad stiffness ``J`` is the roll and pitch rows of ``A^+`` (FL: 0.0118 deg/mm,
   ``00_docs/04_control/control_candidates_comparison.md`` 5.4). The attitude change is the
   gyro rate integrated over the probe (``rate_attitude_rad``), not the accelerometer tilt:
   at the IMU point C1 the apparent tilt of the rocking is 0.3-0.5 deg during a probe (reduced
   model), an order of magnitude above the response.

Why both cues: with one leg lifted the other three carry the machine statically determinate,
so extending any of them only tilts the body and its force hardly rises. The stiffness cue then
calls all four legs ungrounded; only the attitude response tells the lifted leg apart (seen on
the reduced plant, ``05_tests/unit/test_c2_closed_loop.py``).

The probe (:class:`ProbeRound`, design 14.6 and decision D4: once after every completed
levelling and again only after a trigger) moves one leg at a time ``+depth`` (2 mm at
0.25 v_max), holds, ``-depth``, holds, and turns the four readings into a
:class:`ProbeResult` (:func:`evaluate_probe`). The extend / retract midpoint cancels the seal
friction (load estimate), half the gap estimates ``F_s`` (D5: R5 sets ``F_band`` from the first
round, :class:`SealBandRule`, and only widens it afterwards). The
attitude change of each probe is kept within ``attitude_limit_rad`` (D4: +-0.1 deg; the probe
stops extending early if the filtered attitude moves further).

Verdict (``00_docs/04_control/s6_control_spec.md`` 10.1, decision P1): with
``ProbeSettings.use_combined_verdict`` (default on) a leg is grounded when any cue shows contact
(band ABOVE, stiffness above its fraction of ``S_ii``, or an attitude response above
``attitude_agreement_ratio``) and lifted when none does; ``False`` gives the stiffness-only
verdict of design 14.6 (the R2 regression traces). Band ABOVE cannot come from a lifted leg
while ``F_band >= F_s`` (D5). The band cue matters for the legs of a three-leg support that
carry 150-200 kN: they may not be able to extend at all (210 bar cut-off) and then show neither
stiffness nor attitude response. The risky misjudgement (a lifted leg called grounded) of the
attitude cue is set by the gyro: spec 10.3 requires ARW <= 0.15 deg/sqrt(h) and bias instability
<= 10 deg/h (U8), and C2 removes the gyro bias measured in CHECK.

Units SI (m, rad, N, s); per-leg arrays follow ``LEG_ORDER`` (FL, FR, RL, RR).
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import Enum, StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.signals import LEG_COUNT

# --- settings and results ------------------------------------------------------------------


class LoadBand(StrEnum):
    """Where the true cylinder force can lie relative to F_min, given the friction band."""

    ABOVE = "above"
    """Lower bound ``P - F_band >= F_min``: loaded whatever the seal friction."""
    AMBIGUOUS = "ambiguous"
    """F_min inside the band: only a probe decides."""
    BELOW = "below"
    """Upper bound ``P + F_band < F_min``: unloaded or lifted whatever the seal friction."""


class RegroundRule(StrEnum):
    """Which leg a probe round re-grounds (spec 21.2 Q2)."""

    LOAD_FIRST = "load_first"
    """R4.1: the lowest midpoint load estimate below F_min + guard margin first, whatever the
    verdict; then the verdict rule; ``probe_unresolved`` only without such a leg."""
    VERDICT = "verdict"
    """R4: judged ungrounded legs first (smallest reading), ``probe_unresolved`` when all four
    are judged ungrounded."""


class StiffnessWindow(StrEnum):
    """Which part of a move the incremental stiffness is measured on (spec 27, K1)."""

    SECOND_HALF = "second_half"
    """R4.1: from the reading at half the travel to the reading after the hold (the seal
    friction has settled its direction)."""
    FULL = "full"
    """R2-R4: from the round-start reading to the reading after the hold."""


class SealBandRule(StrEnum):
    """How a probe round sets the friction band ``F_band`` (decision D5, spec 22.4)."""

    MEASURED_FIRST = "measured_first"
    """R5 (H5a): the first round of the run replaces the start value by the measured band
    ``max(seal_band_min_N, F_s estimate + margin)``; later rounds only widen it."""
    WIDEN_ONLY = "widen_only"
    """R2-R4.1: every round only widens the band from its start value (13 kN)."""


class ProbeSequence(StrEnum):
    """Order of the moves of one leg's probe (spec 63.3, U62)."""

    EXTEND_RETRACT_TAIL = "extend_retract_tail"
    """Spec rev. 11 option (U62 first form): +d -> hold (reading E) -> -(d + tail) -> hold
    (reading R) -> +tail -> settle. Rev. 12 (U67) moved the tail to one four-leg heave before
    READY (control/c2.py), so this stays an option only."""
    EXTEND_RETRACT = "extend_retract"
    """+d -> hold (E) -> -d -> hold (R): R2-R6 (spec 65.1 keeps it)."""


class ProbeSensitivity(StrEnum):
    """``S_ii`` of the midpoint and seal-friction corrections (spec 63.2, U63)."""

    MEASURED_IF_GROUNDED = "measured_if_grounded"
    """R6: the given correction value (C1, 'other legs locked after an extension'), replaced
    by the measured secant (K1 second half) when the stiffness cue says grounded."""
    NOMINAL = "nominal"
    """R2-R5: the nominal ``S_ii`` of the load sensitivity."""


class ProbeProfile(StrEnum):
    """Speed profile of one probe move."""

    RECT = "rect"
    """Constant ``speed_fraction`` x ``v_max`` (revisions R2 / R3)."""
    TRAPEZOID = "trapezoid"
    """Plateau ``depth / D``, linear ramps ``tau`` (spec 16.1: residual rocking ratio <= 0.05
    from 1.70 to 2.95 Hz)."""


@dataclass(frozen=True)
class ProbeSettings:
    """Probe of the combined contact judge (design 14.6, reduced model values).

    The first nine fields are the decided design; the ``attitude_*`` fields and
    ``use_combined_verdict`` belong to the combined verdict of this module (SPEC POINT).
    """

    speed_fraction: float = 0.25
    """Probe speed as a fraction of the maximum leg speed."""
    depth_m: float = 2e-3
    hold_s: float = 0.4
    min_travel_m: float = 2e-4
    """Below this extension travel the incremental stiffness is not evaluated."""
    grounded_stiffness_ratio: float = 0.3
    """Grounded when the incremental stiffness exceeds this fraction of ``S_ii``."""
    max_rounds: int = 3
    """Probe rounds per run that may still re-ground a leg."""
    reground_load_margin_N: float = 15e3
    """A re-grounded leg is extended to ``F_min + margin``."""
    reground_min_load_step_N: float = 5e3
    seal_band_margin_N: float = 1e3
    """``F_band <- max(F_band, F_s estimate + margin)`` (decision D5)."""
    seal_band_rule: SealBandRule = SealBandRule.MEASURED_FIRST
    """Spec 22.4 (U25 = c): ``measured_first`` (R5) or ``widen_only`` (R2-R4.1)."""
    seal_band_min_N: float = 1e3
    """Lower bound of the band measured by the first round (spec 22.4, H5a)."""
    attitude_window_s: float = 0.3
    """The rate-integrated attitude is averaged over this window before and after each
    extension (the last 0.3 s of the 0.4 s hold; ASSUMPTION)."""
    attitude_agreement_ratio: float = 0.5
    """The attitude response says 'grounded' above this fraction of the kinematic one
    (ASSUMPTION, kept by spec 10.2 P2; S6 item 7 records the ratios: grounded 0.7-1.5, lifted
    |ratio| <= 0.3 expected)."""
    attitude_limit_rad: float = math.radians(0.08)
    """The extension stops early once the 2nd-order filtered roll or pitch has moved this far
    from the round start: D4 allows +-0.1 deg, 0.02 deg are left for the filter lag
    (ASSUMPTION)."""
    use_combined_verdict: bool = True
    """Grounded when any cue shows contact: band, stiffness, attitude (spec 10.1 P1, default
    on; ``False`` = stiffness only, the design 14.6 verdict of the R2 regression traces)."""
    profile: ProbeProfile = ProbeProfile.TRAPEZOID
    """Speed profile of each move (spec 18.1 P1, U16): trapezoid by default; ``rect`` is the
    rectangular ``speed_fraction`` move of revisions R2 / R3 (their regression traces)."""
    move_duration_s: float = 0.56
    """Trapezoid: plateau length ``D`` (plateau speed ``depth / D``); the top-level rocking
    period 1 / 1.78 Hz (ASSUMPTION)."""
    ramp_s: float = 0.36
    """Trapezoid: linear ramp ``tau``; the bottom-level rocking period 1 / 2.84 Hz
    (ASSUMPTION). A move lasts ``D + tau``."""
    attitude_ripple_ratio: float | None = 0.15
    """Spec 21.2 Q1 (U24' = a): the attitude cue abstains when, in either window, the
    detrended peak-to-peak of the rate-integrated attitude projected on ``J_i`` exceeds this
    fraction of the expected response ``|J_i| |ds|`` (ASSUMPTION). ``None`` = no gate (R4)."""
    attitude_drift_ratio: float | None = 0.25
    """Spec 21.2 Q1b: it also abstains when the window trend times the window spacing exceeds
    this fraction of the expected response (ASSUMPTION). ``None`` = no gate (R4)."""
    reground_rule: RegroundRule = RegroundRule.LOAD_FIRST
    """Spec 21.2 Q2: ``load_first`` (R4.1) or ``verdict`` (R4)."""
    stiffness_window: StiffnessWindow = StiffnessWindow.SECOND_HALF
    """Spec 29 K1 (U29): ``second_half`` (R4.1) or ``full`` (R2-R4)."""
    stroke_guard_margin_m: float | None = 5e-3
    """Spec 20.4 P6 (U23): a leg with ``s + depth > s_max - margin`` is probed retract first,
    a leg with ``s > s_max - margin`` is skipped (``probe_skipped:stroke_margin``); ASSUMPTION
    5 mm. ``None`` turns the guard off (R2 / R3 regression)."""
    sequence: ProbeSequence = ProbeSequence.EXTEND_RETRACT
    """Move order (trapezoid profile; the tail option only for a leg probed extend first)."""
    tail_m: float = 3e-4
    """Tail option: length (rev. 11 0.3 mm, ASSUMPTION)."""
    tail_speed_fraction: float = 0.1
    """Tail option: speed / v_max (ASSUMPTION)."""
    tail_settle_s: float = 0.2
    """Tail option: standstill after the tail before the next leg (ASSUMPTION)."""
    sensitivity: ProbeSensitivity = ProbeSensitivity.NOMINAL
    """U63 (spec 63.2): ``S_ii`` of the corrections."""

    def __post_init__(self) -> None:
        if not 0.0 < self.speed_fraction <= 1.0:
            raise ValueError(f"speed_fraction must be in (0, 1], got {self.speed_fraction!r}")
        if not (self.depth_m > 0.0 and self.hold_s >= 0.0 and self.attitude_window_s > 0.0):
            raise ValueError("depth_m and attitude_window_s must be > 0, hold_s >= 0")
        object.__setattr__(self, "profile", ProbeProfile(self.profile))
        object.__setattr__(self, "reground_rule", RegroundRule(self.reground_rule))
        object.__setattr__(self, "stiffness_window", StiffnessWindow(self.stiffness_window))
        object.__setattr__(self, "seal_band_rule", SealBandRule(self.seal_band_rule))
        object.__setattr__(self, "sequence", ProbeSequence(self.sequence))
        object.__setattr__(self, "sensitivity", ProbeSensitivity(self.sensitivity))
        if self.tail_m < 0.0 or not 0.0 < self.tail_speed_fraction <= 1.0:
            raise ValueError("tail_m must be >= 0 and tail_speed_fraction in (0, 1]")
        if not 0.0 < self.ramp_s <= self.move_duration_s:
            raise ValueError("trapezoid: 0 < ramp_s <= move_duration_s required")


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of probing one leg (+depth, hold, -depth, hold).

    Attributes:
        leg_index: Leg (LEG_ORDER index).
        load_estimate_N: Extend/retract midpoint corrected by ``S_ii dx / 2``.
        seal_friction_estimate_N: Half the extend/retract reading gap after the stiffness part.
        incremental_stiffness_N_m: ``dP / dx`` of the extension (NaN if the leg barely moved).
        is_grounded: The verdict (stiffness; any cue with ``use_combined_verdict``).
        is_grounded_by_stiffness: Incremental stiffness above the grounded fraction of ``S_ii``.
        load_band: Friction-band verdict of the round-start reading (``None`` if not given).
        attitude_change_rad: Measured (roll, pitch) change over the extension, or ``None``
            without enough IMU samples.
        predicted_attitude_change_rad: ``J_i`` times the motor-stroke travel of the extension.
        attitude_response_ratio: Measured change projected on ``J_i`` / predicted change
            (about 1 grounded, 0 lifted; NaN when the leg did not move or no attitude).
        is_attitude_consistent: Whether the attitude cue agrees with the stiffness verdict
            (``None`` when the ratio is NaN).
        is_attitude_limited: The extension was stopped early by the attitude limit.
        is_reversed: Probed retract first (stroke guard P6).
        is_skipped: Not probed (stroke guard P6); the verdict is the friction band or the
            previous round's verdict, the estimates are the start reading / NaN.
    """

    leg_index: int
    load_estimate_N: float
    seal_friction_estimate_N: float
    incremental_stiffness_N_m: float
    is_grounded: bool
    is_grounded_by_stiffness: bool | None = None
    load_band: LoadBand | None = None
    attitude_change_rad: tuple[float, float] | None = None
    predicted_attitude_change_rad: tuple[float, float] | None = None
    attitude_response_ratio: float = math.nan
    is_attitude_consistent: bool | None = None
    is_attitude_limited: bool = False
    is_reversed: bool = False
    is_skipped: bool = False
    is_attitude_rippled: bool = False
    """Q1: the attitude cue abstained (window ripple or drift above its gate)."""
    attitude_ripple_ratio: float = math.nan
    """Q1: largest detrended window peak-to-peak / expected response (report)."""
    attitude_drift_ratio: float = math.nan
    """Q1b: largest window trend x window spacing / expected response (report)."""
    t_move_start_s: float = math.nan
    """J-0 (spec 59.1): time of the first move's first period (NaN for a skipped leg)."""
    t_first_hold_end_s: float = math.nan
    """J-0: time of the reading at the end of the hold after the first move."""
    t_second_hold_end_s: float = math.nan
    """J-0: time of the reading at the end of the hold after the second move."""


@dataclass(frozen=True, eq=False)
class ProbeReading:
    """What one probe period needs from the controller's readings.

    Attributes:
        t_s: Measurement time (s).
        cylinder_force_N: Pressure reading as cylinder force (4,).
        rod_stroke_m: Rod position ``stroke_corrected_m`` (4,): incremental stiffness.
        motor_stroke_m: ``stroke_m`` (4,): travel for the kinematic attitude response.
        rate_attitude_rad: Gyro roll / pitch rate integrated up to this sample (rad); only its
            changes over a probe are used.
        filtered_attitude_rad: 2nd-order filtered (roll, pitch): attitude limit.
    """

    t_s: float
    cylinder_force_N: NDArray[np.float64]
    rod_stroke_m: NDArray[np.float64]
    motor_stroke_m: NDArray[np.float64]
    rate_attitude_rad: tuple[float, float]
    filtered_attitude_rad: tuple[float, float]


@dataclass(frozen=True)
class ProbeSample:
    """Readings of one leg's probe that :func:`evaluate_probe` turns into a result.

    ``extended_*`` are taken at the end of the hold after the upward move and ``retracted_*``
    after the downward move, whatever their order. ``attitude_extended_rad`` is the attitude
    after the *first* move (the extension, or the retraction when ``is_reversed``).
    """

    leg_index: int
    start_force_N: float
    start_rod_stroke_m: float
    start_motor_stroke_m: float
    extended_force_N: float
    extended_rod_stroke_m: float
    extended_motor_stroke_m: float
    retracted_force_N: float
    retracted_rod_stroke_m: float
    attitude_before_rad: tuple[float, float] | None = None
    attitude_extended_rad: tuple[float, float] | None = None
    is_attitude_limited: bool = False
    start_load_band: LoadBand | None = None
    is_reversed: bool = False
    """P6: retract first, then extend back to the start."""
    retracted_motor_stroke_m: float = math.nan
    """Motor stroke after the retraction (the first move's travel when ``is_reversed``)."""
    first_move_mid_force_N: float = math.nan
    """K1: reading at half the first move's travel (NaN = not taken)."""
    first_move_mid_rod_stroke_m: float = math.nan
    attitude_window_before_rad: tuple[tuple[float, float], ...] = ()
    """Q1: rate-integrated attitude samples of the window before the first move."""
    attitude_window_after_rad: tuple[tuple[float, float], ...] = ()
    """Q1: samples of the window at the end of the first move's hold."""
    window_spacing_s: float = math.nan
    """Q1b: time between the two window centres."""
    window_period_s: float = 0.02
    """Sample period of the attitude windows (the control period)."""


# --- physics pieces ------------------------------------------------------------------------


def load_bounds_N(
    cylinder_force_N: ArrayLike, seal_band_N: float
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Bounds ``(P - F_band, P + F_band)`` of the true cylinder force for readings ``P``."""
    reading = np.asarray(cylinder_force_N, dtype=float)
    return reading - seal_band_N, reading + seal_band_N


def classify_load(
    cylinder_force_N: ArrayLike, seal_band_N: float, F_min_N: float
) -> list[LoadBand]:
    """Friction-band verdict per leg (cue 1 of the module docstring)."""
    lower, upper = load_bounds_N(cylinder_force_N, seal_band_N)
    bands = []
    for low, high in zip(lower, upper, strict=True):
        if low >= F_min_N:
            bands.append(LoadBand.ABOVE)
        elif high < F_min_N:
            bands.append(LoadBand.BELOW)
        else:
            bands.append(LoadBand.AMBIGUOUS)
    return bands


def attitude_sensitivity_rad_m(
    support_matrix: ArrayLike, pad_stiffness_N_m: ArrayLike
) -> NDArray[np.float64]:
    """``J`` (4, 2): body (roll, pitch) change per metre of extension of each leg alone.

    All four legs grounded, leg ``i`` extended by ``ds`` at its motor (L1 position motor; the
    oil column and the pad act as the series spring ``k_i``): the rigid-body displacement
    ``q = [z, phi, theta]`` balances ``A^T K (ds e_i - A q) = 0``, so
    ``q = (A^T K A)^-1 A^T K e_i ds``. With equal ``k_i`` this is ``A^+ e_i ds``.
    """
    support = np.asarray(support_matrix, dtype=float)
    stiffness = np.diag(np.asarray(pad_stiffness_N_m, dtype=float))
    weighted = support.T @ stiffness
    rigid_body_per_leg = np.linalg.solve(weighted @ support, weighted)  # (3, 4)
    return rigid_body_per_leg[1:3].T.copy()


def _attitude_response_ratio(
    change_rad: NDArray[np.float64], kinematic_rad_m: NDArray[np.float64], travel_m: float
) -> float:
    """Measured change projected on ``J_i``, divided by the predicted ``|J_i| travel``."""
    norm_squared = float(kinematic_rad_m @ kinematic_rad_m)
    if travel_m == 0.0 or norm_squared == 0.0:
        return math.nan
    return float(change_rad @ kinematic_rad_m) / (norm_squared * travel_m)


def evaluate_probe(
    sample: ProbeSample,
    load_sensitivity_N_m: float,
    attitude_sensitivity_rad_m: ArrayLike,
    settings: ProbeSettings,
    correction_sensitivity_N_m: float | None = None,
) -> ProbeResult:
    """Combined verdict of one leg's probe.

    Args:
        sample: Readings at the round start, after the extension hold and after the retraction
            hold, and the window-averaged rate-integrated attitude before and after the
            extension.
        load_sensitivity_N_m: ``S_ii`` of the four-leg support with the nominal pad stiffness.
        attitude_sensitivity_rad_m: Row ``J_i`` (roll, pitch per metre) of
            :func:`attitude_sensitivity_rad_m`.
        settings: Probe settings.
        correction_sensitivity_N_m: U63: ``S_ii`` of the midpoint / seal-friction corrections
            (``None`` = ``load_sensitivity_N_m``); the grounded threshold keeps
            ``load_sensitivity_N_m``.

    Returns:
        Load and seal-friction estimates, incremental stiffness and the verdicts.
    """
    stiffness_cue = _stiffness_cue(
        sample, load_sensitivity_N_m, settings, correction_sensitivity_N_m
    )
    change, predicted, ratio = _attitude_cue(
        sample, attitude_sensitivity_rad_m, stiffness_cue.has_moved
    )
    ripple_ratio, drift_ratio = _attitude_window_quality(sample, attitude_sensitivity_rad_m)
    is_rippled = _exceeds(ripple_ratio, settings.attitude_ripple_ratio) or _exceeds(
        drift_ratio, settings.attitude_drift_ratio
    )
    shows_attitude_response = (
        not is_rippled and math.isfinite(ratio) and ratio >= settings.attitude_agreement_ratio
    )
    is_consistent = None
    if math.isfinite(ratio) and not is_rippled:
        is_consistent = shows_attitude_response == stiffness_cue.is_grounded

    is_grounded = stiffness_cue.is_grounded
    if settings.use_combined_verdict:
        is_loaded = sample.start_load_band is LoadBand.ABOVE
        is_grounded = is_loaded or stiffness_cue.is_grounded or shows_attitude_response
    return ProbeResult(
        leg_index=sample.leg_index,
        load_estimate_N=stiffness_cue.load_estimate_N,
        seal_friction_estimate_N=stiffness_cue.seal_friction_estimate_N,
        incremental_stiffness_N_m=stiffness_cue.incremental_stiffness_N_m,
        is_grounded=is_grounded,
        is_grounded_by_stiffness=stiffness_cue.is_grounded,
        load_band=sample.start_load_band,
        attitude_change_rad=change,
        predicted_attitude_change_rad=predicted,
        attitude_response_ratio=ratio,
        is_attitude_consistent=is_consistent,
        is_attitude_limited=sample.is_attitude_limited,
        is_reversed=sample.is_reversed,
        is_attitude_rippled=is_rippled,
        attitude_ripple_ratio=ripple_ratio,
        attitude_drift_ratio=drift_ratio,
    )


def _exceeds(value: float, gate: float | None) -> bool:
    return gate is not None and math.isfinite(value) and value > gate


def _window_ripple_and_trend(
    samples: tuple[tuple[float, float], ...], direction: NDArray[np.float64], period_s: float
) -> tuple[float, float]:
    """Detrended peak-to-peak and trend (rad/s) of the samples projected on ``direction``."""
    projected = np.array(samples, dtype=float) @ direction
    times = np.arange(len(projected)) * period_s
    slope, intercept = np.polyfit(times, projected, 1)
    residual = projected - (slope * times + intercept)
    return float(np.ptp(residual)), float(slope)


def _attitude_window_quality(
    sample: ProbeSample, attitude_sensitivity_rad_m: ArrayLike
) -> tuple[float, float]:
    """Q1 / Q1b (spec 21.2): window ripple and drift over the expected response ``|J_i| |ds|``.

    Both windows' rate-integrated attitude is projected on the unit ``J_i``; the larger
    detrended peak-to-peak and the larger trend x window spacing are returned as fractions of
    the expected response (NaN when the windows or the travel are missing).
    """
    kinematic = np.asarray(attitude_sensitivity_rad_m, dtype=float)
    norm = float(np.linalg.norm(kinematic))
    first_move_stroke = (
        sample.retracted_motor_stroke_m if sample.is_reversed else sample.extended_motor_stroke_m
    )
    expected = norm * abs(first_move_stroke - sample.start_motor_stroke_m)
    windows = (sample.attitude_window_before_rad, sample.attitude_window_after_rad)
    if not (math.isfinite(expected) and expected > 0.0) or any(len(w) < 3 for w in windows):
        return math.nan, math.nan
    direction = kinematic / norm
    ripple, drift = 0.0, 0.0
    for window in windows:
        peak_to_peak, slope = _window_ripple_and_trend(window, direction, sample.window_period_s)
        ripple = max(ripple, peak_to_peak)
        drift = max(drift, abs(slope) * sample.window_spacing_s)
    return ripple / expected, drift / expected


@dataclass(frozen=True)
class _StiffnessCue:
    has_moved: bool
    incremental_stiffness_N_m: float
    is_grounded: bool
    load_estimate_N: float
    seal_friction_estimate_N: float


def _stiffness_cue(
    sample: ProbeSample,
    load_sensitivity_N_m: float,
    settings: ProbeSettings,
    correction_sensitivity_N_m: float | None = None,
) -> _StiffnessCue:
    """Incremental stiffness, load and seal friction from the readings (design 14.6).

    Retract first (P6): the stiffness is ``dP / dx`` of the retraction (both negative, so the
    sign is the same) and the readings straddle the start from below, so the midpoint
    correction changes sign.
    """
    sensitivity = load_sensitivity_N_m
    if sample.is_reversed:
        travel = sample.retracted_rod_stroke_m - sample.start_rod_stroke_m
        force_rise = sample.retracted_force_N - sample.start_force_N
        first_force, first_rod = sample.retracted_force_N, sample.retracted_rod_stroke_m
    else:
        travel = sample.extended_rod_stroke_m - sample.start_rod_stroke_m
        force_rise = sample.extended_force_N - sample.start_force_N
        first_force, first_rod = sample.extended_force_N, sample.extended_rod_stroke_m
    has_moved = abs(travel) > settings.min_travel_m
    is_second_half = settings.stiffness_window is StiffnessWindow.SECOND_HALF
    if is_second_half and math.isfinite(sample.first_move_mid_rod_stroke_m):
        # K1 (spec 27): by half the travel the seal friction has turned to the move direction.
        travel = first_rod - sample.first_move_mid_rod_stroke_m
        force_rise = first_force - sample.first_move_mid_force_N
        has_moved = has_moved and travel != 0.0
    stiffness = force_rise / travel if has_moved else math.nan
    is_grounded = has_moved and stiffness > settings.grounded_stiffness_ratio * sensitivity
    correction = _correction_sensitivity(
        sensitivity, correction_sensitivity_N_m, settings, bool(is_grounded), stiffness
    )
    stroke_gap = sample.extended_rod_stroke_m - sample.retracted_rod_stroke_m
    extended, retracted = sample.extended_force_N, sample.retracted_force_N
    # The extend / retract midpoint cancels the seal friction (+F_s then -F_s).
    if sample.is_reversed:
        load = 0.5 * (extended + retracted) + 0.5 * correction * stroke_gap
    else:
        load = 0.5 * (extended + retracted) - 0.5 * correction * stroke_gap
    seal_friction = 0.5 * (extended - retracted - correction * stroke_gap)
    return _StiffnessCue(has_moved, stiffness, bool(is_grounded), load, seal_friction)


def _correction_sensitivity(
    nominal: float,
    given: float | None,
    settings: ProbeSettings,
    is_grounded: bool,
    stiffness: float,
) -> float:
    """U63: ``S_ii`` of the corrections (the nominal one for the R2-R5 settings)."""
    correction = nominal if given is None else given
    is_measured = settings.sensitivity is ProbeSensitivity.MEASURED_IF_GROUNDED
    if is_measured and is_grounded and math.isfinite(stiffness):
        return stiffness
    return correction


def _attitude_cue(
    sample: ProbeSample, attitude_sensitivity_rad_m: ArrayLike, has_moved: bool
) -> tuple[tuple[float, float] | None, tuple[float, float], float]:
    """Measured change, predicted change ``J_i ds`` and their ratio (NaN if not available)."""
    kinematic = np.asarray(attitude_sensitivity_rad_m, dtype=float)
    first_move_stroke = (
        sample.retracted_motor_stroke_m if sample.is_reversed else sample.extended_motor_stroke_m
    )
    motor_travel = first_move_stroke - sample.start_motor_stroke_m
    predicted = (float(kinematic[0] * motor_travel), float(kinematic[1] * motor_travel))
    if sample.attitude_before_rad is None or sample.attitude_extended_rad is None:
        return None, predicted, math.nan
    change = np.subtract(sample.attitude_extended_rad, sample.attitude_before_rad)
    ratio = _attitude_response_ratio(change, kinematic, motor_travel) if has_moved else math.nan
    return (float(change[0]), float(change[1])), predicted, ratio


# --- probe sequencer -----------------------------------------------------------------------

# A stage ends once its hold has lasted this long after the last move command (float sample
# times may miss the hold by rounding, as the touch hold of c2.py).
HOLD_SLACK_S = 1e-9


def trapezoid_speeds(
    depth_m: float, plateau_s: float, ramp_s: float, period_s: float
) -> NDArray[np.float64]:
    """Per-period speeds of a trapezoidal move of ``depth_m`` (spec 18.1 P1).

    The continuous profile rises linearly over ``ramp_s`` to ``depth / plateau_s``, holds, and
    falls over ``ramp_s`` (total ``plateau_s + ramp_s``, area ``depth``). Each period commands
    the mean speed of its interval (zero-order hold), and the last period closes the depth
    exactly.
    """
    plateau_speed = depth_m / plateau_s
    total_s = plateau_s + ramp_s

    def position(t_s: float) -> float:
        if t_s <= 0.0:
            return 0.0
        if t_s <= ramp_s:
            return plateau_speed * t_s * t_s / (2.0 * ramp_s)
        if t_s <= plateau_s:
            return plateau_speed * (t_s - 0.5 * ramp_s)
        if t_s <= total_s:
            remaining_s = total_s - t_s
            return depth_m - plateau_speed * remaining_s * remaining_s / (2.0 * ramp_s)
        return depth_m

    period_count = math.ceil(total_s / period_s - 1e-9)
    speeds = np.array(
        [
            (position((k + 1) * period_s) - position(k * period_s)) / period_s
            for k in range(period_count)
        ]
    )
    speeds[-1] = (depth_m - period_s * float(np.sum(speeds[:-1]))) / period_s
    return speeds


class _Stage(Enum):
    FIRST_MOVE = "first_move"
    SECOND_MOVE = "second_move"
    TAIL = "tail"
    """U62: +tail and the settle after the R reading (the result is already taken)."""


@dataclass
class _LegRecord:
    """Readings and move bookkeeping while one leg is probed."""

    attitude_before_rad: tuple[float, float] | None
    extend_move_s: float
    """Rect: duration of the first move; shortened when the attitude limit stops it."""
    first_sign: float = 1.0
    """+1 extend first (normal), -1 retract first (stroke guard P6)."""
    is_attitude_limited: bool = False
    first_force_N: float = math.nan
    first_rod_stroke_m: float = math.nan
    first_motor_stroke_m: float = math.nan
    attitude_after_first_rad: tuple[float, float] | None = None
    mid_force_N: float = math.nan
    """K1: reading at half the first move's commanded travel."""
    mid_rod_stroke_m: float = math.nan
    window_before_rad: tuple[tuple[float, float], ...] = ()
    """Q1: window samples before the first move (copied when the record is made)."""
    window_after_rad: tuple[tuple[float, float], ...] = ()
    start_t_s: float = math.nan
    first_end_t_s: float = math.nan
    planned_speeds: list[float] = field(default_factory=list)
    """Trapezoid: speeds (magnitudes) still to command in this move."""
    sent_speeds: list[float] = field(default_factory=list)
    """Trapezoid: speeds commanded in the first move (the second move plays them back)."""
    last_command_t_s: float | None = None
    pending_result: ProbeResult | None = None
    """U62: the result taken at the R reading, stored while the tail runs."""


@dataclass
class _Window:
    """Rolling attitude window (the mean of the last ``size`` samples)."""

    size: int
    samples: deque[tuple[float, float]] = field(default_factory=deque)

    def add(self, attitude_rad: tuple[float, float]) -> None:
        self.samples.append(attitude_rad)
        while len(self.samples) > self.size:
            self.samples.popleft()

    def mean(self) -> tuple[float, float] | None:
        if len(self.samples) < self.size:
            return None
        roll, pitch = np.mean(np.array(self.samples), axis=0)
        return float(roll), float(pitch)


class ProbeRound:
    """One probe round: every leg in LEG_ORDER +depth, hold, -depth, hold (design 14.6).

    Call :meth:`step` once per control period, starting with the period that creates the
    round; it returns the leg speeds of that period. After the last leg :attr:`is_finished` is
    true and :attr:`results` holds one :class:`ProbeResult` per leg.

    Profiles (``ProbeSettings.profile``):

    * ``rect`` (R2 / R3): constant speed ``speed_fraction v_max`` for ``depth / speed``. The
      first leg moves from the period that creates the round, every later stage from the
      period after its switching period, so FL extends one period more than it retracts
      (0.11 mm per round, about 0.0013 deg). KNOWN DEVIATION (spec 10.4, P4): kept so that the
      reduced-model reference and the R2 traces stay valid.
    * ``trapezoid`` (R4 default, spec 16.1 P1): :func:`trapezoid_speeds`; the second move plays
      the first move's commands back in reverse, so every leg returns exactly to its start.
      The attitude limit replaces the rest of the first move by a linear ramp down over
      ``ramp_s``.

    Stroke guard (spec 20.4 P6): a leg whose motor stroke plus ``depth`` would pass
    ``stroke_max - margin`` is probed retract first; a leg already past it is skipped
    (:attr:`skipped_legs`) and keeps the friction-band / previous verdict.

    Args:
        start: Reading of the period that starts the round (also its first :meth:`step`).
        settings: Probe settings.
        max_speed_m_s: ``v_max``.
        period_s: Control period (s).
        load_sensitivity_diag_N_m: ``S_ii`` per leg (4,).
        attitude_sensitivity_rad_m: ``J`` (4, 2) of :func:`attitude_sensitivity_rad_m`.
        recent_rate_attitude_rad: Rate-integrated (roll, pitch) samples before the round,
            oldest first (the attitude baseline of the first leg).
        load_band_limits_N: ``(F_band, F_min)`` for the friction-band cue of the round-start
            readings, or ``None`` to leave it out.
        stroke_max_m: ``s_max`` of the stroke guard (``inf`` = no guard).
        previous_results: Results of the previous round, by leg (verdict of a skipped leg).
        correction_sensitivity_N_m: U63 ``S_ii`` of the midpoint / seal-friction corrections
            per leg (4,); ``None`` = ``load_sensitivity_diag_N_m``.
        retract_first_legs: Legs probed retract first whenever their stroke allows it (R6-P
            P-9: a rod-side fallback leg ends its probe extending, so its rod side stays at
            the return back pressure, spec 53.3).
    """

    def __init__(
        self,
        start: ProbeReading,
        settings: ProbeSettings,
        max_speed_m_s: float,
        period_s: float,
        load_sensitivity_diag_N_m: ArrayLike,
        attitude_sensitivity_rad_m: ArrayLike,
        recent_rate_attitude_rad: Iterable[tuple[float, float]] = (),
        load_band_limits_N: tuple[float, float] | None = None,
        stroke_max_m: float = math.inf,
        previous_results: Iterable[ProbeResult] = (),
        retract_first_legs: Iterable[int] = (),
        correction_sensitivity_N_m: ArrayLike | None = None,
    ) -> None:
        self.settings = settings
        self._retract_first_legs = frozenset(int(leg) for leg in retract_first_legs)
        self._correction_sensitivity = (
            None
            if correction_sensitivity_N_m is None
            else np.asarray(correction_sensitivity_N_m, dtype=float)
        )
        self.speed_m_s = settings.speed_fraction * max_speed_m_s
        self.max_speed_m_s = max_speed_m_s
        self.period_s = period_s
        self.stroke_max_m = stroke_max_m
        self._load_sensitivity = np.asarray(load_sensitivity_diag_N_m, dtype=float)
        self._attitude_sensitivity = np.asarray(attitude_sensitivity_rad_m, dtype=float)
        self._start_force = start.cylinder_force_N.copy()
        self._start_rod_stroke = start.rod_stroke_m.copy()
        self._start_motor_stroke = start.motor_stroke_m.copy()
        self._start_attitude = start.filtered_attitude_rad
        self._start_load_bands: list[LoadBand] | None = None
        if load_band_limits_N is not None:
            seal_band_N, F_min_N = load_band_limits_N
            self._start_load_bands = classify_load(start.cylinder_force_N, seal_band_N, F_min_N)
        self._previous = {result.leg_index: result for result in previous_results}
        self._trapezoid = trapezoid_speeds(
            settings.depth_m, settings.move_duration_s, settings.ramp_s, period_s
        )
        self._stage_start_s = start.t_s
        self._window = _Window(max(1, round(settings.attitude_window_s / period_s)))
        for attitude in recent_rate_attitude_rad:
            self._window.add(attitude)
        self.leg = 0
        self._stage = _Stage.FIRST_MOVE
        self._record: _LegRecord | None = None
        self.results: list[ProbeResult] = []
        self.skipped_legs: list[int] = []

    @property
    def is_finished(self) -> bool:
        return self.leg == LEG_COUNT

    @property
    def nominal_move_s(self) -> float:
        """Rect: duration of a full ``depth`` move at the probe speed."""
        return self.settings.depth_m / self.speed_m_s

    @property
    def is_trapezoid(self) -> bool:
        return self.settings.profile is ProbeProfile.TRAPEZOID

    def step(self, reading: ProbeReading) -> NDArray[np.float64]:
        """Leg speeds for this period; collects the readings at the end of each hold."""
        leg_speeds = np.zeros(LEG_COUNT)
        if self.is_finished:
            return leg_speeds
        if self._record is None:
            first_sign = self._first_move_sign(reading)
            if first_sign is None:
                self._skip_leg(reading)
                return leg_speeds
            self._record = _LegRecord(self._window.mean(), self.nominal_move_s, first_sign)
            self._record.window_before_rad = tuple(self._window.samples)
            self._record.start_t_s = reading.t_s
            if self.is_trapezoid:
                self._record.planned_speeds = self._trapezoid.tolist()
        self._window.add(reading.rate_attitude_rad)
        if self.is_trapezoid:
            return self._step_trapezoid(self._record, reading, leg_speeds)
        return self._step_rect(self._record, reading, leg_speeds)

    # --- stroke guard (P6) ---

    def _first_move_sign(self, reading: ProbeReading) -> float | None:
        """+1 normal, -1 retract first, ``None`` skip (spec 20.4 P6)."""
        margin = self.settings.stroke_guard_margin_m
        stroke = float(reading.motor_stroke_m[self.leg])
        if self.leg in self._retract_first_legs and stroke >= self.settings.depth_m:
            return -1.0
        if margin is None:
            return 1.0
        stroke_limit = self.stroke_max_m - margin
        if stroke + self.settings.depth_m <= stroke_limit:
            return 1.0
        if stroke <= stroke_limit:
            return -1.0
        return None

    def _skip_leg(self, reading: ProbeReading) -> None:
        leg = self.leg
        band = None if self._start_load_bands is None else self._start_load_bands[leg]
        previous = self._previous.get(leg)
        previous_verdict = previous.is_grounded if previous is not None else False
        self.results.append(
            ProbeResult(
                leg_index=leg,
                load_estimate_N=float(self._start_force[leg]),
                seal_friction_estimate_N=0.0,
                incremental_stiffness_N_m=math.nan,
                is_grounded=band is LoadBand.ABOVE or previous_verdict,
                is_grounded_by_stiffness=(
                    None if previous is None else previous.is_grounded_by_stiffness
                ),
                load_band=band,
                is_skipped=True,
            )
        )
        self.skipped_legs.append(leg)
        self._stage_start_s = reading.t_s
        self.leg += 1

    # --- rect profile (R2 / R3 timing) ---

    def _step_rect(
        self, record: _LegRecord, reading: ProbeReading, leg_speeds: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        elapsed_s = reading.t_s - self._stage_start_s
        is_first_move = self._stage is _Stage.FIRST_MOVE
        move_s = record.extend_move_s
        if elapsed_s < move_s and is_first_move and self._exceeds_attitude_limit(reading):
            # Half a period below the elapsed time: the second move then runs exactly as many
            # periods as the first did.
            record.extend_move_s = move_s = elapsed_s - 0.5 * self.period_s
            record.is_attitude_limited = True
        is_halfway = elapsed_s >= 0.5 * move_s
        if is_first_move and is_halfway and not math.isfinite(record.mid_rod_stroke_m):
            self._record_mid_reading(record, reading)
        if elapsed_s < move_s:
            sign = record.first_sign if is_first_move else -record.first_sign
            leg_speeds[self.leg] = sign * self.speed_m_s
            return leg_speeds
        if elapsed_s < move_s + self.settings.hold_s:
            return leg_speeds
        self._end_stage(record, reading)
        self._stage_start_s = reading.t_s
        return leg_speeds

    # --- trapezoid profile (R4) ---

    def _step_trapezoid(
        self, record: _LegRecord, reading: ProbeReading, leg_speeds: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        is_first_move = self._stage is _Stage.FIRST_MOVE
        if record.planned_speeds:
            if is_first_move and not record.is_attitude_limited:
                if self._exceeds_attitude_limit(reading):
                    record.planned_speeds = self._ramp_down(record)
                    record.is_attitude_limited = True
            half_periods = len(self._trapezoid) // 2
            if is_first_move and len(record.sent_speeds) == half_periods:
                self._record_mid_reading(record, reading)
            if record.planned_speeds:
                speed = record.planned_speeds.pop(0)
                if is_first_move:
                    record.sent_speeds.append(speed)
                sign = record.first_sign if is_first_move else -record.first_sign
                leg_speeds[self.leg] = sign * speed
                record.last_command_t_s = reading.t_s
                return leg_speeds
        last_command_s = record.last_command_t_s
        if last_command_s is None:
            last_command_s = reading.t_s - self.period_s  # limited before the first command
        since_motion_s = reading.t_s - last_command_s - self.period_s
        is_tail = self._stage is _Stage.TAIL
        hold_s = self.settings.tail_settle_s if is_tail else self.settings.hold_s
        if since_motion_s < hold_s - HOLD_SLACK_S:
            return leg_speeds
        if is_first_move:
            record.planned_speeds = list(reversed(record.sent_speeds))
            if self._has_tail(record):  # U62: retract the tail further, extend it back later
                record.planned_speeds += self._tail_speeds()
            record.last_command_t_s = None
        elif self._stage is _Stage.TAIL:
            self._finish_leg(record)
            return leg_speeds
        self._end_stage(record, reading)
        return leg_speeds

    def _has_tail(self, record: _LegRecord) -> bool:
        settings = self.settings
        is_tail_sequence = settings.sequence is ProbeSequence.EXTEND_RETRACT_TAIL
        return is_tail_sequence and settings.tail_m > 0.0 and record.first_sign > 0.0

    def _tail_speeds(self) -> list[float]:
        """Per-period speeds of the ``tail_m`` move at ``tail_speed_fraction v_max``."""
        settings = self.settings
        tail_speed = settings.tail_speed_fraction * self.max_speed_m_s
        periods = max(1, math.ceil(settings.tail_m / (tail_speed * self.period_s) - 1e-9))
        return [settings.tail_m / (periods * self.period_s)] * periods

    def _ramp_down(self, record: _LegRecord) -> list[float]:
        """Speeds that bring the last commanded speed linearly to zero over ``ramp_s``."""
        last_speed = record.sent_speeds[-1] if record.sent_speeds else 0.0
        steps = max(1, round(self.settings.ramp_s / self.period_s))
        return [last_speed * (1.0 - j / steps) for j in range(1, steps)]

    # --- shared ---

    def _record_mid_reading(self, record: _LegRecord, reading: ProbeReading) -> None:
        """K1: reading at half the first move's commanded travel."""
        record.mid_force_N = float(reading.cylinder_force_N[self.leg])
        record.mid_rod_stroke_m = float(reading.rod_stroke_m[self.leg])

    def _exceeds_attitude_limit(self, reading: ProbeReading) -> bool:
        roll, pitch = reading.filtered_attitude_rad
        start_roll, start_pitch = self._start_attitude
        excursion = max(abs(roll - start_roll), abs(pitch - start_pitch))
        return excursion > self.settings.attitude_limit_rad

    def _end_stage(self, record: _LegRecord, reading: ProbeReading) -> None:
        leg = self.leg
        if self._stage is _Stage.FIRST_MOVE:
            record.first_force_N = float(reading.cylinder_force_N[leg])
            record.first_rod_stroke_m = float(reading.rod_stroke_m[leg])
            record.first_motor_stroke_m = float(reading.motor_stroke_m[leg])
            record.attitude_after_first_rad = self._window.mean()
            record.window_after_rad = tuple(self._window.samples)
            record.first_end_t_s = reading.t_s
            self._stage = _Stage.SECOND_MOVE
            return
        result = self._evaluate(record, reading)
        if self.is_trapezoid and self._has_tail(record):
            # U62: +tail, then settle (the hold rule of the stages), then the next leg.
            record.pending_result = result
            record.planned_speeds = self._tail_speeds()
            record.first_sign = -1.0  # the TAIL stage commands -first_sign = +1
            record.last_command_t_s = None
            self._stage = _Stage.TAIL
            return
        self.results.append(result)
        self._record = None
        self._stage = _Stage.FIRST_MOVE
        self.leg += 1

    def _finish_leg(self, record: _LegRecord) -> None:
        assert record.pending_result is not None
        self.results.append(record.pending_result)
        self._record = None
        self._stage = _Stage.FIRST_MOVE
        self.leg += 1

    def _evaluate(self, record: _LegRecord, reading: ProbeReading) -> ProbeResult:
        leg = self.leg
        second_force = float(reading.cylinder_force_N[leg])
        second_rod_stroke = float(reading.rod_stroke_m[leg])
        is_reversed = record.first_sign < 0.0
        if is_reversed:
            extended = (second_force, second_rod_stroke, float(reading.motor_stroke_m[leg]))
            retracted = (record.first_force_N, record.first_rod_stroke_m)
            retracted_motor = record.first_motor_stroke_m
        else:
            extended = (
                record.first_force_N,
                record.first_rod_stroke_m,
                record.first_motor_stroke_m,
            )
            retracted = (second_force, second_rod_stroke)
            retracted_motor = float(reading.motor_stroke_m[leg])
        sample = ProbeSample(
            leg_index=leg,
            start_force_N=float(self._start_force[leg]),
            start_rod_stroke_m=float(self._start_rod_stroke[leg]),
            start_motor_stroke_m=float(self._start_motor_stroke[leg]),
            extended_force_N=extended[0],
            extended_rod_stroke_m=extended[1],
            extended_motor_stroke_m=extended[2],
            retracted_force_N=retracted[0],
            retracted_rod_stroke_m=retracted[1],
            attitude_before_rad=record.attitude_before_rad,
            attitude_extended_rad=record.attitude_after_first_rad,
            is_attitude_limited=record.is_attitude_limited,
            start_load_band=None if self._start_load_bands is None else self._start_load_bands[leg],
            is_reversed=is_reversed,
            retracted_motor_stroke_m=retracted_motor,
            first_move_mid_force_N=record.mid_force_N,
            first_move_mid_rod_stroke_m=record.mid_rod_stroke_m,
            attitude_window_before_rad=record.window_before_rad,
            attitude_window_after_rad=record.window_after_rad,
            # The before window ends one period before the first move, the after window at
            # the end of its hold.
            window_spacing_s=record.first_end_t_s - record.start_t_s + self.period_s,
            window_period_s=self.period_s,
        )
        corrections = self._correction_sensitivity
        correction = None if corrections is None else float(corrections[leg])
        result = evaluate_probe(
            sample,
            float(self._load_sensitivity[leg]),
            self._attitude_sensitivity[leg],
            self.settings,
            correction,
        )
        # J-0: the probe timing per leg, so that the S6 judge can take the truth of this leg's
        # own probe interval (spec 55.1); the verdict and the commands do not use it.
        return replace(
            result,
            t_move_start_s=float(record.start_t_s),
            t_first_hold_end_s=float(record.first_end_t_s),
            t_second_hold_end_s=float(reading.t_s),
        )
