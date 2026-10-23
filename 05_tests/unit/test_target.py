"""Target acceptance A0-A4 and the reference ramp (control/target.py, s6_control_spec.md 2.3-2.4).

Boundary cases of the spec's test list (2.9, first and fifth rows); the C2 integration is in
``test_c2_target.py``.
"""

from __future__ import annotations

import math

import pytest

from outrigger_sim.control.target import (
    AttitudeTarget,
    SlopeLimitMode,
    TargetAcceptance,
    TargetCode,
    TargetLimits,
    check_target,
    diamond_usage,
    floor_usage,
    ramp_reference,
    relative_usage,
)

OPERATING = TargetLimits.for_mode(SlopeLimitMode.OPERATING)
VERIFICATION = TargetLimits.for_mode(SlopeLimitMode.VERIFICATION)
PERIOD_S = 0.02


def _floor(roll_deg: float, pitch_deg: float) -> tuple[float, float]:
    return math.radians(roll_deg), math.radians(pitch_deg)


def _code(roll_deg, pitch_deg, floor=(0.0, 0.0), limits=OPERATING) -> TargetCode:
    target = AttitudeTarget.from_degrees(roll_deg, pitch_deg)
    return check_target(target, _floor(*floor), limits).code


@pytest.mark.parametrize(
    ("target_deg", "floor_deg", "limits", "code"),
    [
        ((2.2, 1.6), (0.0, 0.0), OPERATING, TargetCode.ACCEPTED),  # on the absolute diamond
        ((2.21, 1.6), (0.0, 0.0), OPERATING, TargetCode.REJ_TARGET_ABS),
        ((0.0, 3.01), (0.0, 0.0), OPERATING, TargetCode.REJ_TARGET_AXIS_CAP),
        ((4.0, 0.5), (0.0, 0.0), OPERATING, TargetCode.REJ_TARGET_ABS),
        ((0.0, 0.1), (0.0, -3.2), OPERATING, TargetCode.REJ_TARGET_REL),
        ((0.0, 0.0), (0.0, -3.5), VERIFICATION, TargetCode.ACCEPTED),
        ((0.0, 0.0), (0.0, -3.5), OPERATING, TargetCode.REJ_SLOPE_D8),
        ((0.0, 3.0), (0.0, 3.3), OPERATING, TargetCode.REJ_SLOPE_D8),  # relative 0.3 deg only
    ],
)
def test_spec_boundary_cases(target_deg, floor_deg, limits, code) -> None:
    assert _code(*target_deg, floor=floor_deg, limits=limits) is code


def test_checks_run_in_order_and_report_the_first_failure() -> None:
    nan_target = AttitudeTarget(math.nan, 0.0)
    assert check_target(nan_target, _floor(0, 4), OPERATING).code is TargetCode.REJ_TARGET_INVALID
    # Floor outside D8 and target beyond the cap: A1 comes first.
    assert _code(0.0, 5.0, floor=(0.0, 3.5)) is TargetCode.REJ_SLOPE_D8
    # Cap and absolute diamond both broken: A2 comes first.
    assert _code(4.5, 3.0) is TargetCode.REJ_TARGET_AXIS_CAP


def test_verification_mode_changes_only_the_relative_half_spans() -> None:
    assert VERIFICATION.relative_roll_span_rad == pytest.approx(math.radians(5.5))
    assert VERIFICATION.relative_pitch_span_rad == pytest.approx(math.radians(3.5))
    assert VERIFICATION.absolute_pitch_span_rad == OPERATING.absolute_pitch_span_rad
    assert VERIFICATION.max_roll_rad == OPERATING.max_roll_rad


def test_rejected_target_has_no_accepted_value() -> None:
    check = check_target(AttitudeTarget.from_degrees(4.0, 3.0), (0.0, 0.0), OPERATING)
    assert check.accepted is None and not check.is_accepted
    assert check.to_meta()["code"] == "REJ_TARGET_ABS"


def test_projection_starts_from_the_current_target() -> None:
    current = AttitudeTarget.from_degrees(0.0, 2.0)
    requested = AttitudeTarget.from_degrees(0.0, 3.5)  # beyond the 3 deg cap
    check = check_target(requested, (0.0, 0.0), OPERATING, TargetAcceptance.PROJECT, current)
    assert check.code is TargetCode.REJ_TARGET_AXIS_CAP and check.is_projected
    assert check.accepted is not None
    assert math.degrees(check.accepted.pitch_rad) == pytest.approx(3.0, abs=1e-6)
    usage = diamond_usage(
        check.accepted.roll_rad,
        check.accepted.pitch_rad,
        OPERATING.absolute_roll_span_rad,
        OPERATING.absolute_pitch_span_rad,
    )
    assert usage <= 1.0


def test_projection_never_overrides_the_d8_floor() -> None:
    check = check_target(AttitudeTarget(), _floor(0, 3.4), OPERATING, TargetAcceptance.PROJECT)
    assert check.code is TargetCode.REJ_SLOPE_D8 and check.accepted is None


def test_off_accepts_everything() -> None:
    check = check_target(AttitudeTarget(), _floor(0, 3.7), OPERATING, TargetAcceptance.OFF)
    assert check.code is TargetCode.ACCEPTED and check.accepted == AttitudeTarget()


# --- reference ramp (R1) ----------------------------------------------------------------------


def test_ramp_keeps_the_rate_diamond_and_arrives_on_time() -> None:
    """0 -> (2.2, 1.6) deg: |d_phi| / 0.4 + |d_theta| / 0.25 <= T per period, 11.9 s +- T."""
    reference, target = AttitudeTarget(), AttitudeTarget.from_degrees(2.2, 1.6)
    periods = 0
    while reference != target and periods < 2000:
        previous, reference = reference, ramp_reference(reference, target, PERIOD_S)
        roll_step_deg = abs(math.degrees(reference.roll_rad - previous.roll_rad))
        pitch_step_deg = abs(math.degrees(reference.pitch_rad - previous.pitch_rad))
        assert roll_step_deg / 0.4 + pitch_step_deg / 0.25 <= PERIOD_S * (1 + 1e-9)
        periods += 1
    assert periods * PERIOD_S == pytest.approx(2.2 / 0.4 + 1.6 / 0.25, abs=PERIOD_S)


def test_ramp_lands_exactly_on_the_target() -> None:
    target = AttitudeTarget.from_degrees(0.0, 0.001)
    assert ramp_reference(AttitudeTarget(), target, PERIOD_S) == target


def test_invalid_limits_are_rejected() -> None:
    with pytest.raises(ValueError):
        TargetLimits(max_roll_rad=0.0)
    with pytest.raises(ValueError):
        TargetLimits(relative_pitch_span_nose_up_rad=0.0)


# --- nose-up half-span (spec revision 20 86.3, R7) --------------------------------------------

INTERIM_B = TargetLimits.interim_b()
# 86.3 (d): one 1e-9 rad step past a half-span changes the usage by ~1.8e-8, beyond eps_u 1e-9.
BOUNDARY_STEP_RAD = 1e-9
USAGE_GRID_DEG = [-3.6, -3.2, -3.15, -1.0, -0.0, 0.0, 0.4, 3.1, 3.15, 3.2, 3.6]


def test_interim_b_preset_sets_only_the_nose_up_span() -> None:
    """Provisional B: 3.1 deg on the nose-up side, everything else the operating limits."""
    assert INTERIM_B.relative_pitch_span_nose_up_rad == math.radians(3.1)
    assert OPERATING.relative_pitch_span_nose_up_rad is None
    assert INTERIM_B == TargetLimits(relative_pitch_span_nose_up_rad=math.radians(3.1))
    assert TargetLimits.for_mode(SlopeLimitMode.OPERATING) == TargetLimits()


def test_default_nose_up_span_is_bit_identical_to_the_symmetric_one() -> None:
    """86.3 (a): ``None`` and an explicit 3.2 deg give the same usages bit for bit."""
    explicit = TargetLimits(relative_pitch_span_nose_up_rad=OPERATING.relative_pitch_span_rad)
    for floor_pitch_deg in USAGE_GRID_DEG:
        floor = _floor(1.3, floor_pitch_deg)
        assert floor_usage(floor, OPERATING) == floor_usage(floor, explicit)
        for target_pitch_deg in USAGE_GRID_DEG:
            target = AttitudeTarget.from_degrees(-0.7, target_pitch_deg)
            assert relative_usage(target, floor, OPERATING) == relative_usage(
                target, floor, explicit
            )


@pytest.mark.parametrize(
    ("floor_pitch_deg", "b_code", "default_code"),
    [
        (-3.15, TargetCode.REJ_SLOPE_D8, TargetCode.ACCEPTED),  # floor nose up
        (3.15, TargetCode.ACCEPTED, TargetCode.ACCEPTED),  # floor nose down
    ],
    ids=["floor-nose-up", "floor-nose-down"],
)
def test_interim_b_d8_start_check(floor_pitch_deg, b_code, default_code) -> None:
    """86.3 (b): level target, floor -3.15 deg is rejected by B only; +3.15 deg passes both."""
    floor = (0.0, floor_pitch_deg)
    assert _code(0.0, 0.0, floor=floor, limits=INTERIM_B) is b_code
    assert _code(0.0, 0.0, floor=floor, limits=OPERATING) is default_code


@pytest.mark.parametrize(
    ("target_pitch_deg", "b_code"),
    [
        (2.15, TargetCode.REJ_TARGET_REL),  # theta_t - theta_g = +3.15: nose-up side
        (-2.0, TargetCode.ACCEPTED),  # -1.0: nose-down side
    ],
    ids=["relative-nose-up-3.15", "relative-nose-down-1.0"],
)
def test_interim_b_relative_diamond(target_pitch_deg, b_code) -> None:
    """86.3 (c): floor -1 deg; the side is the sign of theta_t - theta_g (rule A), so +2.15 deg
    is rejected by B and accepted by the default."""
    floor = (0.0, -1.0)
    assert _code(0.0, target_pitch_deg, floor=floor, limits=INTERIM_B) is b_code
    assert _code(0.0, target_pitch_deg, floor=floor, limits=OPERATING) is TargetCode.ACCEPTED


def test_interim_b_usage_denominators() -> None:
    """86.3 (d): nose-up side denominator 3.1 deg, nose-down side 3.2 deg (boundary +-1e-9)."""
    nose_up_span = math.radians(3.1)
    nose_down_span = math.radians(3.2)
    target = AttitudeTarget()
    assert floor_usage((0.0, -nose_up_span), INTERIM_B) == pytest.approx(1.0, abs=1e-15)
    assert floor_usage((0.0, nose_down_span), INTERIM_B) == pytest.approx(1.0, abs=1e-15)
    nose_up_target = AttitudeTarget(0.0, nose_up_span)  # relative +3.1 on a level floor
    assert relative_usage(nose_up_target, (0.0, 0.0), INTERIM_B) == pytest.approx(1.0, abs=1e-15)
    cases = [
        (-(nose_up_span - BOUNDARY_STEP_RAD), True),
        (-(nose_up_span + BOUNDARY_STEP_RAD), False),
        (nose_up_span + BOUNDARY_STEP_RAD, True),  # nose-down floor: 3.2 deg applies
        (nose_down_span - BOUNDARY_STEP_RAD, True),
        (nose_down_span + BOUNDARY_STEP_RAD, False),
    ]
    for floor_pitch_rad, is_accepted in cases:
        check = check_target(target, (0.0, floor_pitch_rad), INTERIM_B)
        assert check.is_accepted is is_accepted, math.degrees(floor_pitch_rad)


@pytest.mark.parametrize("pitch_sign", [1.0, -1.0], ids=["nose-down", "nose-up"])
def test_interim_b_keeps_the_absolute_diamond_symmetric(pitch_sign) -> None:
    """86.3: A3 stays |phi_t| / 4.4 + |theta_t| / 3.2 for both target signs (floor roll 2.2 deg
    so that the relative tilt is pitch only and A4 passes)."""
    floor = (2.2, 0.0)
    assert _code(2.2, pitch_sign * 1.6, floor=floor, limits=INTERIM_B) is TargetCode.ACCEPTED
    rejected = _code(2.2, pitch_sign * 1.61, floor=floor, limits=INTERIM_B)
    assert rejected is TargetCode.REJ_TARGET_ABS
