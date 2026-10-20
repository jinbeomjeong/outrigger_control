"""Unit tests for frames: wxyz quaternions, ZYX Euler angles, CAD <-> body (plan R10)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st
from scipy.spatial.transform import Rotation

from outrigger_sim import frames
from outrigger_sim.frames import (
    BODY_ORIGIN_IN_CAD_MM,
    QUATERNION_IDENTITY_WXYZ,
    CadBodyTransform,
    canonical_quat,
    euler_zyx_from_quat,
    matrix_to_quat,
    normalize_quat,
    quat_conjugate,
    quat_from_euler_zyx,
    quat_multiply,
    quat_to_matrix,
    roll_pitch_from_quat,
    roll_pitch_from_specific_force,
    rotate_vector,
)
from outrigger_sim.params import Params, load_params

# CLAUDE.md '좌표계와 명명': rotation (body <- CAD), x = +Z_cad, y = +X_cad, z = +Y_cad.
CLAUDE_MD_ROTATION_BODY_FROM_CAD = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]
GRAVITY_M_S2 = 9.80665
HALF_PI = 0.5 * math.pi

# database=None: no .hypothesis/ example database is left in the project.
PROPERTY_SETTINGS = settings(max_examples=50, deadline=None, database=None)
ANGLE = st.floats(min_value=-math.pi, max_value=math.pi, allow_nan=False)
# Pitch kept 1e-3 rad away from +-90 deg so the Euler round trip is unique.
REGULAR_PITCH = st.floats(min_value=-HALF_PI + 1e-3, max_value=HALF_PI - 1e-3)
QUAT_COMPONENT = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)
RANDOM_QUAT = st.tuples(QUAT_COMPONENT, QUAT_COMPONENT, QUAT_COMPONENT, QUAT_COMPONENT).filter(
    lambda q: math.hypot(*q) > 1e-3
)


@pytest.fixture(scope="module")
def params(params_path: Path) -> Params:
    return load_params(params_path)


def _same_orientation(quat_a: np.ndarray, quat_b: np.ndarray, atol: float = 1e-12) -> bool:
    """``q`` and ``-q`` are the same orientation: compare |<a, b>| with 1."""
    dot = np.sum(normalize_quat(quat_a) * normalize_quat(quat_b), axis=-1)
    return bool(np.all(np.abs(dot) >= 1.0 - atol))


def test_canonical_quat_is_unique_for_half_turns() -> None:
    np.testing.assert_array_equal(canonical_quat([0.0, 0.0, 0.0, -1.0]), [0, 0, 0, 1])
    np.testing.assert_array_equal(canonical_quat([-0.5, 0.5, 0.5, 0.5]), [0.5, -0.5, -0.5, -0.5])


# --- quaternion algebra ------------------------------------------------------------------


def test_normalize_gives_unit_norm_and_keeps_direction() -> None:
    quat = normalize_quat([2.0, 0.0, 0.0, -2.0])
    assert np.linalg.norm(quat) == pytest.approx(1.0, abs=1e-15)
    np.testing.assert_allclose(quat, [math.sqrt(0.5), 0.0, 0.0, -math.sqrt(0.5)])


@pytest.mark.parametrize("bad", [[0.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [math.nan, 0, 0, 1]])
def test_normalize_rejects_degenerate_input(bad: list[float]) -> None:
    with pytest.raises(ValueError, match="quat_wxyz"):
        normalize_quat(bad)


def test_identity_does_not_rotate() -> None:
    vector = np.array([0.3, -1.2, 4.0])
    np.testing.assert_array_equal(rotate_vector(QUATERNION_IDENTITY_WXYZ, vector), vector)


@PROPERTY_SETTINGS
@given(a=RANDOM_QUAT, b=RANDOM_QUAT, c=RANDOM_QUAT)
def test_product_is_associative_and_matches_matrix_product(a, b, c) -> None:
    left_first = quat_multiply(quat_multiply(a, b), c)
    right_first = quat_multiply(a, quat_multiply(b, c))
    np.testing.assert_allclose(left_first, right_first, atol=1e-12)
    product_matrix = quat_to_matrix(quat_multiply(a, b))
    np.testing.assert_allclose(product_matrix, quat_to_matrix(a) @ quat_to_matrix(b), atol=1e-12)


@PROPERTY_SETTINGS
@given(quat=RANDOM_QUAT)
def test_conjugate_is_the_inverse_rotation(quat) -> None:
    unit = normalize_quat(quat)
    product = quat_multiply(unit, quat_conjugate(unit))
    np.testing.assert_allclose(product, QUATERNION_IDENTITY_WXYZ, atol=1e-12)


@PROPERTY_SETTINGS
@given(quat=RANDOM_QUAT)
def test_matrix_round_trip(quat) -> None:
    matrix = quat_to_matrix(quat)
    np.testing.assert_allclose(matrix @ matrix.T, np.eye(3), atol=1e-12)
    assert np.linalg.det(matrix) == pytest.approx(1.0, abs=1e-12)
    recovered = matrix_to_quat(matrix)
    assert recovered[0] >= 0.0
    assert _same_orientation(recovered, normalize_quat(quat))


@pytest.mark.parametrize(
    ("axis", "vector", "expected"),
    [
        # roll +90 deg about x: left (+y) goes up (+z), matches "phi > 0 lifts the left side".
        ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        # pitch +90 deg about y: forward (+x) goes down (-z), "theta > 0 is nose-down".
        ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
        # yaw +90 deg about z: forward (+x) turns left (+y).
        ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    ],
)
def test_known_90_degree_rotations(axis, vector, expected) -> None:
    half = math.radians(45.0)
    quat = [math.cos(half), *(math.sin(half) * np.array(axis))]
    np.testing.assert_allclose(rotate_vector(quat, vector), expected, atol=1e-15)


def test_matrix_to_quat_rejects_non_rotations() -> None:
    with pytest.raises(ValueError, match="proper rotation"):
        matrix_to_quat(np.diag([1.0, 1.0, -1.0]))  # reflection
    with pytest.raises(ValueError, match="proper rotation"):
        matrix_to_quat(2.0 * np.eye(3))


@pytest.mark.parametrize("angle_deg", [180.0, -179.999, 90.0])
@pytest.mark.parametrize("axis", [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)])
def test_matrix_to_quat_handles_every_shepperd_branch(axis, angle_deg) -> None:
    unit_axis = np.array(axis) / np.linalg.norm(axis)
    half = math.radians(angle_deg) / 2.0
    quat = np.array([math.cos(half), *(math.sin(half) * unit_axis)])
    assert _same_orientation(matrix_to_quat(quat_to_matrix(quat)), quat)


def test_functions_accept_batches() -> None:
    yaw = np.array([0.0, 0.1, -0.2])
    pitch = np.array([0.05, -0.3, 0.4])
    roll = np.array([-0.02, 0.2, 1.0])
    quats = quat_from_euler_zyx(yaw, pitch, roll)
    assert quats.shape == (3, 4)
    assert quat_to_matrix(quats).shape == (3, 3, 3)
    assert matrix_to_quat(quat_to_matrix(quats)).shape == (3, 4)
    recovered = euler_zyx_from_quat(quats)
    np.testing.assert_allclose(np.stack(recovered), np.stack([yaw, pitch, roll]), atol=1e-12)


# --- wxyz vs SciPy xyzw ------------------------------------------------------------------


@PROPERTY_SETTINGS
@given(yaw=ANGLE, pitch=REGULAR_PITCH, roll=ANGLE)
def test_euler_zyx_matches_scipy_intrinsic_zyx(yaw, pitch, roll) -> None:
    scipy_rotation = Rotation.from_euler("ZYX", [yaw, pitch, roll])  # uppercase = intrinsic
    scipy_xyzw = scipy_rotation.as_quat()  # SciPy default order: scalar LAST
    ours_wxyz = quat_from_euler_zyx(yaw, pitch, roll)
    assert _same_orientation(ours_wxyz, np.roll(scipy_xyzw, 1))
    np.testing.assert_allclose(quat_to_matrix(ours_wxyz), scipy_rotation.as_matrix(), atol=1e-12)


def test_reading_scipy_xyzw_as_wxyz_is_a_different_rotation() -> None:
    """The R10 trap: xyzw passed where wxyz is expected silently gives a wrong rotation."""
    scipy_xyzw = Rotation.from_euler("x", 30.0, degrees=True).as_quat()
    misread = quat_to_matrix(scipy_xyzw)
    correct = quat_to_matrix(np.roll(scipy_xyzw, 1))
    assert not np.allclose(misread, correct, atol=1e-3)
    roll, pitch = roll_pitch_from_quat(np.roll(scipy_xyzw, 1))
    assert math.degrees(roll) == pytest.approx(30.0, abs=1e-12)
    assert pitch == pytest.approx(0.0, abs=1e-15)


# --- ZYX Euler angles and tilt -----------------------------------------------------------


@PROPERTY_SETTINGS
@given(yaw=ANGLE, pitch=REGULAR_PITCH, roll=ANGLE)
# Roll at the atan2 branch cut: R21 is ~1e-17 with a rounding-dependent sign, so one call
# returns -pi and the other +pi for the same orientation (flaky failure seen 2026-10-20).
@example(yaw=2.0, pitch=1.5, roll=-math.pi)
@example(yaw=-1.0, pitch=1.5, roll=-3.1415926535897927)
def test_euler_round_trip_and_roll_pitch_are_yaw_independent(yaw, pitch, roll) -> None:
    quat = quat_from_euler_zyx(yaw, pitch, roll)
    recovered_yaw, recovered_pitch, recovered_roll = euler_zyx_from_quat(quat)
    assert recovered_pitch == pytest.approx(pitch, abs=1e-9)
    assert math.remainder(recovered_roll - roll, 2 * math.pi) == pytest.approx(0.0, abs=1e-9)
    assert math.remainder(recovered_yaw - yaw, 2 * math.pi) == pytest.approx(0.0, abs=1e-9)
    roll_only, pitch_only = roll_pitch_from_quat(quat_from_euler_zyx(0.0, pitch, roll))
    # Angles are compared modulo 2 pi: +pi and -pi are the same roll.
    roll_difference = math.remainder(roll_only - recovered_roll, 2 * math.pi)
    assert roll_difference == pytest.approx(0.0, abs=1e-9)
    assert pitch_only == pytest.approx(recovered_pitch, abs=1e-9)


def test_small_tilt_signs() -> None:
    roll, pitch = roll_pitch_from_quat(quat_from_euler_zyx(0.7, math.radians(2), math.radians(-1)))
    assert math.degrees(roll) == pytest.approx(-1.0, abs=1e-12)
    assert math.degrees(pitch) == pytest.approx(2.0, abs=1e-12)


@pytest.mark.parametrize("pitch_sign", [1.0, -1.0])
@pytest.mark.parametrize("offset_rad", [0.0, 1e-9, 1e-7])
def test_gimbal_lock_gives_zero_roll_and_the_same_orientation(pitch_sign, offset_rad) -> None:
    pitch = pitch_sign * (HALF_PI - offset_rad)
    quat = quat_from_euler_zyx(0.4, pitch, -0.3)
    yaw_out, pitch_out, roll_out = euler_zyx_from_quat(quat)
    assert roll_out == 0.0
    assert pitch_out == pytest.approx(pitch, abs=1e-6)
    rebuilt = quat_from_euler_zyx(yaw_out, pitch_out, roll_out)
    assert _same_orientation(rebuilt, quat)
    assert roll_pitch_from_quat(quat)[0] == 0.0


def test_just_outside_gimbal_lock_keeps_roll() -> None:
    quat = quat_from_euler_zyx(0.4, HALF_PI - 1e-4, -0.3)
    yaw_out, pitch_out, roll_out = euler_zyx_from_quat(quat)
    assert roll_out == pytest.approx(-0.3, abs=1e-8)
    assert _same_orientation(quat_from_euler_zyx(yaw_out, pitch_out, roll_out), quat)


@PROPERTY_SETTINGS
@given(yaw=ANGLE, pitch=REGULAR_PITCH, roll=ANGLE)
def test_tilt_from_specific_force_at_rest_is_exact(yaw, pitch, roll) -> None:
    quat = quat_from_euler_zyx(yaw, pitch, roll)
    # At rest the accelerometer measures R^T (0, 0, +g).
    specific_force_body = rotate_vector(quat_conjugate(quat), [0.0, 0.0, GRAVITY_M_S2])
    roll_from_force, pitch_from_force = roll_pitch_from_specific_force(specific_force_body)
    assert pitch_from_force == pytest.approx(pitch, abs=1e-9)
    assert math.remainder(roll_from_force - roll, 2 * math.pi) == pytest.approx(0.0, abs=1e-9)


def test_tilt_from_zero_specific_force_raises() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        roll_pitch_from_specific_force([0.0, 0.0, 0.0])


# --- CAD <-> body ------------------------------------------------------------------------


def test_yaml_rotation_equals_claude_md(params: Params) -> None:
    transform = CadBodyTransform.from_params(params)
    np.testing.assert_array_equal(
        transform.rotation_body_from_cad, CLAUDE_MD_ROTATION_BODY_FROM_CAD
    )
    assert params.get("meta.frame.cad_length_unit") == "mm"


def test_cad_axes_map_as_documented(params: Params) -> None:
    transform = CadBodyTransform.from_params(params)
    cad_x, cad_y, cad_z = np.eye(3)
    np.testing.assert_array_equal(transform.direction_cad_to_body(cad_z), [1, 0, 0])
    np.testing.assert_array_equal(transform.direction_cad_to_body(cad_x), [0, 1, 0])
    np.testing.assert_array_equal(transform.direction_cad_to_body(cad_y), [0, 0, 1])


def test_default_body_origin_is_the_cad_origin(params: Params) -> None:
    assert BODY_ORIGIN_IN_CAD_MM == (0.0, 0.0, 0.0)
    transform = CadBodyTransform.from_params(params)
    np.testing.assert_array_equal(transform.point_cad_mm_to_body_m([0.0, 0.0, 0.0]), [0, 0, 0])
    # 1000 mm along +Y_cad (CAD up) is 1 m along body +z.
    np.testing.assert_array_equal(transform.point_cad_mm_to_body_m([0, 1000, 0]), [0, 0, 1])


@PROPERTY_SETTINGS
@given(
    point=st.tuples(*[st.floats(min_value=-2e4, max_value=2e4)] * 3),
    origin=st.tuples(*[st.floats(min_value=-5e3, max_value=5e3)] * 3),
)
def test_point_round_trip_with_origin_offset(params: Params, point, origin) -> None:
    transform = CadBodyTransform.from_params(params, body_origin_in_cad_mm=origin)
    body_m = transform.point_cad_mm_to_body_m(point)
    np.testing.assert_allclose(transform.point_body_m_to_cad_mm(body_m), point, atol=1e-9)
    # The offset point itself is the body origin.
    np.testing.assert_allclose(transform.point_cad_mm_to_body_m(origin), [0, 0, 0], atol=1e-12)


def test_origin_offset_shifts_points_but_not_directions(params: Params) -> None:
    origin_cad_mm = (100.0, 200.0, 300.0)  # CAD x, y, z = body y, z, x
    shifted = CadBodyTransform.from_params(params, body_origin_in_cad_mm=origin_cad_mm)
    unshifted = CadBodyTransform.from_params(params)
    point_cad_mm = np.array([1000.0, 2000.0, 3000.0])
    difference = unshifted.point_cad_mm_to_body_m(point_cad_mm) - shifted.point_cad_mm_to_body_m(
        point_cad_mm
    )
    np.testing.assert_allclose(difference, [0.3, 0.1, 0.2], atol=1e-15)
    np.testing.assert_array_equal(
        shifted.direction_cad_to_body(point_cad_mm), unshifted.direction_cad_to_body(point_cad_mm)
    )


def test_batched_points_and_quaternion_of_the_cad_axes(params: Params) -> None:
    transform = CadBodyTransform.from_params(params)
    points = np.arange(12.0).reshape(4, 3)
    assert transform.point_cad_mm_to_body_m(points).shape == (4, 3)
    np.testing.assert_allclose(
        quat_to_matrix(transform.quat_body_from_cad_wxyz), CLAUDE_MD_ROTATION_BODY_FROM_CAD
    )
    np.testing.assert_allclose(
        transform.direction_body_to_cad(transform.direction_cad_to_body(points)), points
    )


def test_transform_is_read_only(params: Params) -> None:
    transform = CadBodyTransform.from_params(params)
    with pytest.raises(ValueError, match="read-only"):
        transform.rotation_body_from_cad[0, 0] = 1.0
    with pytest.raises(AttributeError):
        transform.body_origin_in_cad_mm = np.ones(3)  # type: ignore[misc]


def test_wrong_cad_unit_is_rejected(params_path: Path) -> None:
    variant = load_params(params_path, overrides={"meta.frame.cad_length_unit": "inch"})
    with pytest.raises(ValueError, match="cad_length_unit"):
        CadBodyTransform.from_params(variant)


def test_module_has_no_engine_dependency() -> None:
    source = Path(frames.__file__).read_text(encoding="utf-8")
    for forbidden in ("import pychrono", "from pychrono", "import scipy", "from scipy"):
        assert forbidden not in source
