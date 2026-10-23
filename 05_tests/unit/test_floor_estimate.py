"""Floor estimate of revision R3.1: crawler settle map (A) and the shadow plane estimate (B).

``00_docs/04_control/s6_control_spec.md`` revision 2: 13.2 (X1-X8) and 14.6 (X9, X10), test
list of 13.2. The operating-mode / target-0 regression against the R2 traces is
``test_c2.py``; the H4 check on the reduced plant is ``test_c2_closed_loop.py``.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    ContactJudge,
    FloorPlaneEstimator,
    TargetSettings,
)
from outrigger_sim.control.target import (
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
    TargetCode,
    TargetLimits,
    check_target,
    floor_usage,
    relative_usage,
)
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

LEVELS = ("top", "middle", "bottom")
VERIFICATION = TargetLimits.for_mode(SlopeLimitMode.VERIFICATION)
OPERATING = TargetLimits.for_mode(SlopeLimitMode.OPERATING)
GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.02

# Spec 12.2: settled attitude on the crawler (roll, pitch) deg, Chrono stage-2 snapshots, by
# level and floor. The spec counts 14 snapshots; its table lists these 13 values.
SNAPSHOTS_DEG = {
    ("top", "flat"): (0.000, 0.174),
    ("top", "nose_down_3.5"): (0.000, 3.824),
    ("top", "nose_up_3.5"): (0.000, -3.413),
    ("top", "roll_5.5"): (5.555, 0.180),
    ("top", "diagonal_3"): (2.147, 2.362),
    ("middle", "flat"): (0.000, 0.173),
    ("middle", "nose_down_3.5"): (0.000, 3.768),
    ("middle", "nose_up_3.5"): (0.000, -3.395),
    ("middle", "roll_5.5"): (5.543, 0.176),
    ("bottom", "flat"): (0.000, 0.172),
    ("bottom", "nose_down_3.5"): (0.000, 3.733),
    ("bottom", "nose_up_3.5"): (0.000, -3.377),
    ("bottom", "roll_5.5"): (5.530, 0.171),
}
REJECTED_WITHOUT_MAP = {"nose_down_3.5", "roll_5.5", "diagonal_3"}


def _rad(pair_deg: tuple[float, float]) -> tuple[float, float]:
    return math.radians(pair_deg[0]), math.radians(pair_deg[1])


# --- CrawlerSettleMap (X1) --------------------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_settle_map_round_trip_and_continuity(level) -> None:
    settle_map = CrawlerSettleMap.for_level(level)
    for roll_deg in np.linspace(-6.0, 6.0, 13):
        for pitch_deg in np.linspace(-4.0, 4.0, 17):
            measured = _rad((roll_deg, pitch_deg))
            back = settle_map.crawler_from_floor(settle_map.floor_from_crawler(measured))
            np.testing.assert_allclose(back, measured, rtol=0, atol=1e-12)
    at_theta0 = settle_map.floor_from_crawler((0.0, settle_map.theta0_rad))
    assert at_theta0 == (0.0, 0.0)
    just_below = settle_map.floor_from_crawler((0.0, settle_map.theta0_rad - 1e-12))
    assert abs(just_below[1]) < 1e-11


def test_identity_map_and_invalid_coefficients() -> None:
    identity = CrawlerSettleMap.identity()
    assert identity.is_identity
    assert identity.floor_from_crawler((0.01, -0.02)) == (0.01, -0.02)
    with pytest.raises(ValueError):
        CrawlerSettleMap(k_dn=-1.0)
    with pytest.raises(ValueError):
        CrawlerSettleMap.for_level("upper")
    top = CrawlerSettleMap.for_level("top")
    assert math.degrees(top.theta0_rad) == pytest.approx(0.17366)
    assert (top.k_dn, top.k_up, top.k_phi) == (0.04298, 0.02478, 0.01007)
    json.dumps(top.to_meta())


# --- A1 / A4 with the map (X2, X3) --------------------------------------------------------------


@pytest.mark.parametrize(("level", "floor"), list(SNAPSHOTS_DEG))
def test_snapshots_accepted_with_the_level_map(level, floor) -> None:
    measured = _rad(SNAPSHOTS_DEG[(level, floor)])
    settle_map = CrawlerSettleMap.for_level(level)
    check = check_target(AttitudeTarget(), measured, VERIFICATION, settle_map=settle_map)
    assert check.code is TargetCode.ACCEPTED
    # The vertex snapshots define the map, so they return to usage 1.000 (+0.0017 for the
    # roll snapshot's 0.006 deg pitch share, spec 13.1); the spec 12.3 column quotes 0.990.
    assert check.floor_usage <= 1.0 + VERIFICATION.usage_tolerance
    without_map = check_target(AttitudeTarget(), measured, VERIFICATION).code
    expected = TargetCode.REJ_SLOPE_D8 if floor in REJECTED_WITHOUT_MAP else TargetCode.ACCEPTED
    assert without_map is expected


def test_seven_snapshots_are_rejected_without_the_map() -> None:
    codes = [
        check_target(AttitudeTarget(), _rad(attitude), VERIFICATION).code
        for attitude in SNAPSHOTS_DEG.values()
    ]
    assert codes.count(TargetCode.REJ_SLOPE_D8) == 7


@pytest.mark.parametrize("level", LEVELS)
def test_vertices_come_back_on_the_boundary(level) -> None:
    settle_map = CrawlerSettleMap.for_level(level)
    for floor_deg in ((0.0, 3.5), (0.0, -3.5), (5.5, 0.0)):
        measured = settle_map.crawler_from_floor(_rad(floor_deg))
        floor = settle_map.floor_from_crawler(measured)
        assert floor_usage(floor, VERIFICATION) == pytest.approx(1.0, abs=1e-12)
    beyond = settle_map.crawler_from_floor(_rad((0.0, 3.5 * 1.01 + 0.01)))
    check = check_target(AttitudeTarget(), beyond, VERIFICATION, settle_map=settle_map)
    assert check.code is TargetCode.REJ_SLOPE_D8


def test_nose_up_side_is_not_widened() -> None:
    """Top map: measured -3.85 deg is a -3.93 deg floor; the measured boundary is -3.449 deg.

    The spec quotes -3.45 deg as accepted; with eps_u 0.01 it lies 0.001 deg beyond the
    boundary (usage 1.0103), so -3.44 deg is the accepted case here.
    """
    top = CrawlerSettleMap.for_level("top")

    def code(pitch_deg: float) -> TargetCode:
        measured = _rad((0.0, pitch_deg))
        return check_target(AttitudeTarget(), measured, VERIFICATION, settle_map=top).code

    floor_pitch = math.degrees(top.floor_from_crawler(_rad((0.0, -3.85)))[1])
    assert floor_pitch == pytest.approx(-3.926, abs=1e-3)
    assert code(-3.85) is TargetCode.REJ_SLOPE_D8
    assert code(-3.47) is TargetCode.REJ_SLOPE_D8
    assert code(-3.44) is TargetCode.ACCEPTED


def test_relative_diamond_uses_the_floor_estimate() -> None:
    """A4 on the floor: on a flat floor (measured theta_0), target -3 deg uses 3.0 / 3.5."""
    top = CrawlerSettleMap.for_level("top")
    measured = top.crawler_from_floor((0.0, 0.0))
    assert math.degrees(measured[1]) == pytest.approx(0.17366)
    target = AttitudeTarget.from_degrees(0.0, -3.0)
    floor = top.floor_from_crawler(measured)
    assert relative_usage(target, floor, VERIFICATION) == pytest.approx(3.0 / 3.5, abs=1e-12)
    assert relative_usage(target, measured, VERIFICATION) == pytest.approx(0.907, abs=1e-3)
    level = AttitudeTarget()
    assert relative_usage(level, floor, VERIFICATION) == floor_usage(floor, VERIFICATION)


@pytest.mark.parametrize(
    ("target_deg", "code"),
    [((2.21, 1.6), TargetCode.REJ_TARGET_ABS), ((0.0, 3.01), TargetCode.REJ_TARGET_AXIS_CAP)],
)
def test_a2_a3_keep_their_tolerance_in_the_verification_mode(target_deg, code) -> None:
    top = CrawlerSettleMap.for_level("top")
    measured = top.crawler_from_floor((0.0, 0.0))
    check = check_target(
        AttitudeTarget.from_degrees(*target_deg), measured, VERIFICATION, settle_map=top
    )
    assert check.code is code


def test_usage_tolerance_per_mode() -> None:
    assert VERIFICATION.usage_tolerance == 0.01
    assert OPERATING.usage_tolerance == 1e-9


# --- TargetSettings and the C2 wiring (X5, X6) --------------------------------------------------


def test_operating_mode_refuses_a_settle_map() -> None:
    with pytest.raises(ValueError, match="crawler_settle_map"):
        TargetSettings(crawler_settle_map=CrawlerSettleMap.for_level("top"))
    TargetSettings(crawler_settle_map=CrawlerSettleMap.identity())
    assert TargetSettings().settle_map.is_identity


def _specific_force(roll_rad: float, pitch_rad: float) -> np.ndarray:
    up_in_body = [
        -math.sin(pitch_rad),
        math.sin(roll_rad) * math.cos(pitch_rad),
        math.cos(roll_rad) * math.cos(pitch_rad),
    ]
    return GRAVITY_M_S2 * np.array(up_in_body)


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def _run_check(geometry: C2Geometry, measured_rad, target_settings: TargetSettings):
    config = C2Config(
        target=target_settings, contact=ContactJudge.PRESSURE, output_ramp_time_s=None
    )
    controller = C2Controller(geometry, config)
    strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05
    t_s = 0.0
    while controller.phase is C2Phase.CHECK and t_s < 5.0:
        t_s += PERIOD_S
        controller.update(
            Measurements(
                t_s=t_s,
                specific_force_m_s2=_specific_force(*measured_rad),
                angular_rate_rad_s=np.zeros(3),
                head_pressure_Pa=np.full(4, 80e3) / geometry.head_area_m2,
                stroke_m=strokes,
                stroke_corrected_m=strokes,
            )
        )
    return controller


def test_c2_check_uses_the_map_in_the_verification_mode(geometry) -> None:
    measured = _rad(SNAPSHOTS_DEG[("top", "nose_down_3.5")])
    verification = TargetSettings(
        slope_limit_mode=SlopeLimitMode.VERIFICATION,
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    accepted = _run_check(geometry, measured, verification)
    assert accepted.phase is C2Phase.TOUCH
    meta = accepted.meta()
    json.dumps(meta)
    assert meta["revision"] == "R7"
    floor_pitch = math.degrees(meta["target"]["floor_estimate_rad"][1])
    assert floor_pitch == pytest.approx((3.824 - 0.17366) / 1.04298, abs=1e-6)
    assert meta["target"]["crawler_settle_map"]["k_dn"] == 0.04298
    unmapped = TargetSettings(slope_limit_mode=SlopeLimitMode.VERIFICATION)
    assert _run_check(geometry, measured, unmapped).phase is C2Phase.IDLE


# --- shadow floor plane (X9, X10) ---------------------------------------------------------------


def _rotation(roll_rad: float, pitch_rad: float) -> np.ndarray:
    """Level <- body, R_y(theta) R_x(phi) (independent of the code under test)."""
    roll = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(roll_rad), -math.sin(roll_rad)],
            [0.0, math.sin(roll_rad), math.cos(roll_rad)],
        ]
    )
    pitch = np.array(
        [
            [math.cos(pitch_rad), 0.0, math.sin(pitch_rad)],
            [0.0, 1.0, 0.0],
            [-math.sin(pitch_rad), 0.0, math.cos(pitch_rad)],
        ]
    )
    return pitch @ roll


def _extensions_to_floor(
    geometry: C2Geometry,
    floor_rad: tuple[float, float],
    body_attitudes_rad: list[tuple[float, float]],
    floor_height_m: float = -1.6,
) -> np.ndarray:
    """Leg extensions that put each pad bottom on the floor plane at its body attitude."""
    floor_normal = _rotation(*floor_rad) @ np.array([0.0, 0.0, 1.0])
    extensions = np.zeros(4)
    for leg, attitude in enumerate(body_attitudes_rad):
        rotation = _rotation(*attitude)
        pad = np.array([*geometry.pad_xy_m[leg], geometry.pad_bottom_z_retracted_m[leg]])
        leg_axis = rotation @ np.array([0.0, 0.0, 1.0])
        extensions[leg] = (floor_normal @ (rotation @ pad) - floor_height_m) / (
            floor_normal @ leg_axis
        )
    return extensions


def test_plane_estimate_recovers_the_floor(geometry) -> None:
    """Each leg latched at its own body attitude: the floor comes back to 1e-9 deg."""
    floor = _rad((1.2, -2.1))
    attitudes = [_rad((0.5, 0.8)), _rad((0.52, 0.75)), _rad((0.47, 0.83)), _rad((0.5, 0.9))]
    extensions = _extensions_to_floor(geometry, floor, attitudes)
    estimator = FloorPlaneEstimator(geometry)
    assert estimator.estimate(VERIFICATION) is None
    for leg, (extension, attitude) in enumerate(zip(extensions, attitudes, strict=True)):
        estimator.record_latch(leg, 10.0 + leg, float(extension), attitude)
    estimate = estimator.estimate(VERIFICATION)
    np.testing.assert_allclose(np.degrees(estimate.floor_rad), np.degrees(floor), atol=1e-9)
    assert estimate.residual_m < 1e-12
    assert estimate.latch_times_s == (10.0, 11.0, 12.0, 13.0)
    assert estimate.floor_usage == pytest.approx(floor_usage(floor, VERIFICATION))


def test_plane_residual_of_one_raised_leg(geometry) -> None:
    """One leg 3 mm longer: residual = 3 mm |n_i| max |n_j| (about 3/4 of it, spec X10)."""
    level = [(0.0, 0.0)] * 4
    extensions = _extensions_to_floor(geometry, (0.0, 0.0), level)
    extensions[0] += 3e-3
    estimator = FloorPlaneEstimator(geometry)
    for leg, extension in enumerate(extensions):
        estimator.record_latch(leg, 0.0, float(extension), (0.0, 0.0))
    twist = geometry.twist_vector
    expected = 3e-3 * abs(twist[0]) * np.max(np.abs(twist))
    estimate = estimator.estimate(VERIFICATION)
    assert estimate.residual_m == pytest.approx(expected, rel=1e-9)
    assert estimate.residual_m == pytest.approx(0.75e-3, abs=0.01e-3)


def test_c2_records_the_shadow_estimate_at_touch_end(geometry) -> None:
    """Level body, operating strokes (pads coplanar on a level floor): floor (0, 0), event."""
    controller = _run_check(geometry, (0.0, 0.0), TargetSettings(check_time_s=0.0))
    strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05
    t_s = 1.0
    while controller.phase is C2Phase.TOUCH and t_s < 5.0:
        t_s += PERIOD_S
        controller.update(
            Measurements(
                t_s=t_s,
                specific_force_m_s2=_specific_force(0.0, 0.0),
                angular_rate_rad_s=np.zeros(3),
                head_pressure_Pa=np.full(4, 80e3) / geometry.head_area_m2,
                stroke_m=strokes,
                stroke_corrected_m=strokes,
            )
        )
    assert controller.phase is C2Phase.LEVEL
    shadow = controller.meta()["floor_estimate_touch"]
    np.testing.assert_allclose(shadow["floor_rad"], 0.0, atol=1e-12)
    assert shadow["residual_m"] < 1e-12
    assert "floor_estimate_touch" in [event.name for event in controller.events]
