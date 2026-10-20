"""Coordinate frames, wxyz quaternions and ZYX Euler angles (engine independent).

Conventions (CLAUDE.md '좌표계와 명명', ``00_docs/01_dynamics/dynamics_model.md`` 1.1,
``00_docs/03_chrono/chrono_build_plan.md`` R10):

* Body frame: x forward, y left, z up, right-handed. Roll ``phi`` is about x, pitch
  ``theta`` about y, yaw ``psi`` about z. ``theta > 0`` is nose-down, ``phi > 0`` lifts the
  left side.
* Quaternions are **wxyz** (scalar first), like Chrono ``ChQuaternion(e0, e1, e2, e3)``.
  SciPy ``Rotation.as_quat()`` is xyzw by default; this module never uses SciPy so the two
  orders cannot mix. A quaternion ``q`` maps body coordinates to world coordinates:
  ``v_world = rotate_vector(q, v_body)``.
* Euler angles are ZYX intrinsic (= XYZ extrinsic): ``R = Rz(yaw) @ Ry(pitch) @ Rx(roll)``.
  Roll and pitch depend only on the third row of ``R`` (world up seen from the body), so they
  are independent of yaw.
* Gimbal lock: when ``cos(pitch) < GIMBAL_LOCK_COS_THRESHOLD`` roll and yaw are not unique.
  Roll is then reported as 0 and the whole rotation about the vertical goes into yaw. The
  levelling range (a few degrees) is far from this.

All quaternion and angle functions accept a single value or arrays with leading batch
dimensions (``(..., 4)`` quaternions, ``(..., 3)`` vectors, ``(..., 3, 3)`` matrices).

CAD <-> body: the CAD model is Y-up in millimetres. The rotation comes from the YAML
(``meta.frame.rotation_body_from_cad``, read with :func:`outrigger_sim.params.load_params`);
the body-frame origin is :data:`BODY_ORIGIN_IN_CAD_MM`, the only place where it is defined.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import Params

# Body-frame origin expressed in CAD coordinates (CAD axes, mm). CLAUDE.md: the body origin
# is undecided and stays at the CAD origin. Change it here only; every CAD <-> body point
# conversion goes through CadBodyTransform.
BODY_ORIGIN_IN_CAD_MM: tuple[float, float, float] = (0.0, 0.0, 0.0)

CAD_LENGTH_UNIT = "mm"
MM_PER_M = 1000.0

QUATERNION_IDENTITY_WXYZ: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)

# Below this norm a quaternion carries no usable orientation.
QUATERNION_NORM_MIN = 1e-12

# |cos(pitch)| below this is treated as gimbal lock (|pitch| within about 5.7e-5 deg of 90).
# Above it atan2(R21, R22) keeps full precision for roll.
GIMBAL_LOCK_COS_THRESHOLD = 1e-6

# Orthonormality tolerance for rotation matrices given as input (YAML values are exact).
ROTATION_MATRIX_TOLERANCE = 1e-9

FloatArray = NDArray[np.float64]


# --- input checks ------------------------------------------------------------------------


def _as_vectors(values: ArrayLike, length: int, name: str) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 0 or array.shape[-1] != length:
        raise ValueError(f"{name}: expected shape (..., {length}), got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name}: contains NaN or infinity")
    return array


def _as_rotation_matrices(rotation: ArrayLike) -> FloatArray:
    matrices = np.asarray(rotation, dtype=np.float64)
    if matrices.ndim < 2 or matrices.shape[-2:] != (3, 3):
        raise ValueError(f"rotation: expected shape (..., 3, 3), got {matrices.shape}")
    if not np.all(np.isfinite(matrices)):
        raise ValueError("rotation: contains NaN or infinity")
    gram = matrices @ np.swapaxes(matrices, -1, -2)
    is_orthonormal = np.allclose(gram, np.eye(3), atol=ROTATION_MATRIX_TOLERANCE, rtol=0.0)
    if not is_orthonormal or np.any(np.linalg.det(matrices) <= 0.0):
        raise ValueError("rotation: not a proper rotation matrix (orthonormal, det +1)")
    return matrices


# --- quaternion algebra (wxyz) -----------------------------------------------------------


def normalize_quat(quat_wxyz: ArrayLike) -> FloatArray:
    """Return the unit quaternion with the same orientation.

    Args:
        quat_wxyz: Quaternion(s), shape ``(..., 4)``, scalar first.

    Returns:
        Unit quaternion(s) of the same shape. The sign is kept (``q`` and ``-q`` are the
        same orientation; see :func:`canonical_quat`).

    Raises:
        ValueError: Wrong shape, non-finite value, or norm below :data:`QUATERNION_NORM_MIN`.
    """
    quat = _as_vectors(quat_wxyz, 4, "quat_wxyz")
    norm = np.linalg.norm(quat, axis=-1, keepdims=True)
    if np.any(norm < QUATERNION_NORM_MIN):
        raise ValueError(f"quat_wxyz: norm below {QUATERNION_NORM_MIN}, no orientation")
    return quat / norm


def canonical_quat(quat_wxyz: ArrayLike) -> FloatArray:
    """Return one representative of ``+-q``: normalized, first non-zero component positive.

    That is ``w > 0``, or for an exact half turn (``w == 0``) the first non-zero of x, y, z.
    """
    quat = normalize_quat(quat_wxyz)
    first_nonzero_index = np.argmax(quat != 0.0, axis=-1)[..., np.newaxis]
    leading = np.take_along_axis(quat, first_nonzero_index, axis=-1)
    return quat * np.where(leading < 0.0, -1.0, 1.0)


def quat_conjugate(quat_wxyz: ArrayLike) -> FloatArray:
    """Return ``(w, -x, -y, -z)``; for a unit quaternion this is the inverse rotation."""
    quat = _as_vectors(quat_wxyz, 4, "quat_wxyz")
    return quat * np.array([1.0, -1.0, -1.0, -1.0])


def quat_multiply(left_wxyz: ArrayLike, right_wxyz: ArrayLike) -> FloatArray:
    """Hamilton product ``left * right``: apply ``right`` first, then ``left``.

    ``quat_to_matrix(left * right) == quat_to_matrix(left) @ quat_to_matrix(right)``.
    """
    left = _as_vectors(left_wxyz, 4, "left_wxyz")
    right = _as_vectors(right_wxyz, 4, "right_wxyz")
    w1, x1, y1, z1 = np.moveaxis(left, -1, 0)
    w2, x2, y2, z2 = np.moveaxis(right, -1, 0)
    return np.stack(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        axis=-1,
    )


def quat_to_matrix(quat_wxyz: ArrayLike) -> FloatArray:
    """Rotation matrix ``R`` with ``v_world = R @ v_body``; the input is normalized first."""
    w, x, y, z = np.moveaxis(normalize_quat(quat_wxyz), -1, 0)
    rows = [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z), 2.0 * (x * z + w * y)],
        [2.0 * (x * y + w * z), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - w * x)],
        [2.0 * (x * z - w * y), 2.0 * (y * z + w * x), 1.0 - 2.0 * (x * x + y * y)],
    ]
    return np.stack([np.stack(row, axis=-1) for row in rows], axis=-2)


def _matrix_to_quat_single(matrix: FloatArray) -> FloatArray:
    """Shepperd's method: divide by the largest of 4w^2, 4x^2, 4y^2, 4z^2 for accuracy."""
    m = matrix
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    largest = int(np.argmax([trace, m[0, 0], m[1, 1], m[2, 2]]))
    if largest == 0:
        s = 2.0 * math.sqrt(1.0 + trace)
        quat = [0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s]
    elif largest == 1:
        s = 2.0 * math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        quat = [(m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s]
    elif largest == 2:
        s = 2.0 * math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        quat = [(m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s]
    else:
        s = 2.0 * math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        quat = [(m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s]
    return np.array(quat)


def matrix_to_quat(rotation: ArrayLike) -> FloatArray:
    """Quaternion (wxyz, ``w >= 0``) of a rotation matrix.

    Raises:
        ValueError: The input is not a proper rotation matrix within
            :data:`ROTATION_MATRIX_TOLERANCE`.
    """
    matrices = _as_rotation_matrices(rotation)
    flat = matrices.reshape(-1, 3, 3)
    quats = np.array([_matrix_to_quat_single(matrix) for matrix in flat])
    return canonical_quat(quats.reshape((*matrices.shape[:-2], 4)))


def rotate_vector(quat_wxyz: ArrayLike, vector: ArrayLike) -> FloatArray:
    """Rotate ``vector`` by ``quat_wxyz`` (body -> world for a body orientation).

    For the inverse (world -> body) pass :func:`quat_conjugate` of the quaternion.
    """
    rotation = quat_to_matrix(quat_wxyz)
    vectors = _as_vectors(vector, 3, "vector")
    return np.einsum("...ij,...j->...i", rotation, vectors)


# --- ZYX Euler angles and tilt -----------------------------------------------------------


def _axis_angle_quat(axis_index: int, angle_rad: FloatArray) -> FloatArray:
    half = 0.5 * angle_rad
    quat = np.zeros((*np.shape(half), 4))
    quat[..., 0] = np.cos(half)
    quat[..., 1 + axis_index] = np.sin(half)
    return quat


def quat_from_euler_zyx(
    yaw_rad: ArrayLike, pitch_rad: ArrayLike, roll_rad: ArrayLike
) -> FloatArray:
    """Quaternion (wxyz) of ``Rz(yaw) @ Ry(pitch) @ Rx(roll)`` (ZYX intrinsic).

    The arguments broadcast against each other; the result has shape ``(..., 4)``.
    """
    yaw, pitch, roll = np.broadcast_arrays(
        np.asarray(yaw_rad, dtype=np.float64),
        np.asarray(pitch_rad, dtype=np.float64),
        np.asarray(roll_rad, dtype=np.float64),
    )
    yaw_quat = _axis_angle_quat(2, yaw)
    pitch_quat = _axis_angle_quat(1, pitch)
    roll_quat = _axis_angle_quat(0, roll)
    return quat_multiply(yaw_quat, quat_multiply(pitch_quat, roll_quat))


def _tilt_from_up_vector(up_in_body: FloatArray) -> tuple[FloatArray, FloatArray, NDArray]:
    """Roll, pitch and gimbal-lock flag from world up seen in body axes.

    ``up_in_body`` is proportional to ``(-sin pitch, sin roll cos pitch, cos roll cos pitch)``
    (the third row of ``R``); any positive length works.
    """
    up_x, up_y, up_z = np.moveaxis(up_in_body, -1, 0)
    cos_pitch_scaled = np.hypot(up_y, up_z)
    pitch = np.arctan2(-up_x, cos_pitch_scaled)
    length = np.linalg.norm(up_in_body, axis=-1)
    is_gimbal_lock = cos_pitch_scaled < GIMBAL_LOCK_COS_THRESHOLD * length
    roll = np.where(is_gimbal_lock, 0.0, np.arctan2(up_y, up_z))
    return roll, pitch, is_gimbal_lock


def euler_zyx_from_quat(quat_wxyz: ArrayLike) -> tuple[FloatArray, FloatArray, FloatArray]:
    """ZYX intrinsic angles ``(yaw, pitch, roll)`` in rad of a quaternion.

    Ranges: yaw and roll in ``[-pi, pi]``, pitch in ``[-pi/2, pi/2]``. ``-pi`` and ``pi`` are
    the same angle and rounding can give either, so compare angles modulo ``2 pi``
    (e.g. ``math.remainder(a - b, 2 * math.pi)``). Near gimbal lock
    (``cos(pitch) < GIMBAL_LOCK_COS_THRESHOLD``) roll is 0 and yaw carries the rotation about
    the vertical, so ``quat_from_euler_zyx(*result)`` is still the same orientation.
    """
    rotation = quat_to_matrix(quat_wxyz)
    roll, pitch, is_gimbal_lock = _tilt_from_up_vector(rotation[..., 2, :])
    yaw_regular = np.arctan2(rotation[..., 1, 0], rotation[..., 0, 0])
    # In gimbal lock R01 = -sin(yaw -+ roll), R11 = cos(yaw -+ roll) for pitch = +-90 deg;
    # with roll reported as 0 the combined angle is the yaw.
    yaw_locked = np.arctan2(-rotation[..., 0, 1], rotation[..., 1, 1])
    yaw = np.where(is_gimbal_lock, yaw_locked, yaw_regular)
    return yaw, pitch, roll


def roll_pitch_from_quat(quat_wxyz: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Roll and pitch (rad, ZYX intrinsic) of a body orientation; independent of yaw.

    Same values as the last two of :func:`euler_zyx_from_quat` (roll 0 in gimbal lock).
    """
    rotation = quat_to_matrix(quat_wxyz)
    roll, pitch, _ = _tilt_from_up_vector(rotation[..., 2, :])
    return roll, pitch


def roll_pitch_from_specific_force(specific_force_body: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Roll and pitch (rad) from an accelerometer specific force in body axes (exact, no
    small-angle approximation).

    At rest the specific force is ``f = R^T (a + g z_hat) = g * (world up in body axes)``.
    Any acceleration of the sensor point appears as tilt error; filtering is the sensor
    model's job, not this function's.

    Raises:
        ValueError: Wrong shape, non-finite value or zero vector.
    """
    force = _as_vectors(specific_force_body, 3, "specific_force_body")
    if np.any(np.linalg.norm(force, axis=-1) == 0.0):
        raise ValueError("specific_force_body: zero vector has no direction")
    roll, pitch, _ = _tilt_from_up_vector(force)
    return roll, pitch


# --- CAD <-> body ------------------------------------------------------------------------


def _read_only(array: FloatArray) -> FloatArray:
    array.setflags(write=False)
    return array


@dataclass(frozen=True, eq=False)
class CadBodyTransform:
    """Rigid transform between CAD coordinates (Y-up, mm) and body coordinates (SI).

    ``p_body_m = R @ (p_cad_mm - body_origin_in_cad_mm) / 1000`` with
    ``R = rotation_body_from_cad``. Directions (unit vectors, forces) only rotate.
    Build it with :meth:`from_params` so the rotation comes from the YAML.
    """

    rotation_body_from_cad: FloatArray
    """3x3, read-only."""
    body_origin_in_cad_mm: FloatArray
    """Body-frame origin in CAD coordinates (mm), read-only."""

    def __post_init__(self) -> None:
        rotation = _as_rotation_matrices(self.rotation_body_from_cad)
        if rotation.shape != (3, 3):
            raise ValueError(f"rotation_body_from_cad: expected (3, 3), got {rotation.shape}")
        origin = _as_vectors(self.body_origin_in_cad_mm, 3, "body_origin_in_cad_mm")
        if origin.shape != (3,):
            raise ValueError(f"body_origin_in_cad_mm: expected (3,), got {origin.shape}")
        object.__setattr__(self, "rotation_body_from_cad", _read_only(rotation.copy()))
        object.__setattr__(self, "body_origin_in_cad_mm", _read_only(origin.copy()))

    @classmethod
    def from_params(
        cls,
        params: Params,
        body_origin_in_cad_mm: ArrayLike = BODY_ORIGIN_IN_CAD_MM,
    ) -> CadBodyTransform:
        """Use ``meta.frame.rotation_body_from_cad`` from loaded parameters.

        Args:
            params: Loaded parameters (:func:`outrigger_sim.params.load_params`).
            body_origin_in_cad_mm: Body origin in CAD coordinates; keep the default
                :data:`BODY_ORIGIN_IN_CAD_MM` outside tests.

        Raises:
            ValueError: ``meta.frame.cad_length_unit`` is not ``"mm"`` or the rotation is
                not a proper rotation matrix.
        """
        cad_unit = params.get("meta.frame.cad_length_unit")
        if cad_unit != CAD_LENGTH_UNIT:
            raise ValueError(
                f"meta.frame.cad_length_unit: expected {CAD_LENGTH_UNIT!r}, got {cad_unit!r}"
            )
        return cls(
            rotation_body_from_cad=np.array(params.meta.frame.rotation_body_from_cad),
            body_origin_in_cad_mm=np.asarray(body_origin_in_cad_mm, dtype=np.float64),
        )

    @property
    def quat_body_from_cad_wxyz(self) -> FloatArray:
        """Orientation of the CAD axes in the body frame as a wxyz quaternion."""
        return matrix_to_quat(self.rotation_body_from_cad)

    def point_cad_mm_to_body_m(self, point_cad_mm: ArrayLike) -> FloatArray:
        """CAD point(s) in mm, shape ``(..., 3)``, to body coordinates in m."""
        points = _as_vectors(point_cad_mm, 3, "point_cad_mm")
        return (points - self.body_origin_in_cad_mm) @ self.rotation_body_from_cad.T / MM_PER_M

    def point_body_m_to_cad_mm(self, point_body_m: ArrayLike) -> FloatArray:
        """Body point(s) in m, shape ``(..., 3)``, to CAD coordinates in mm."""
        points = _as_vectors(point_body_m, 3, "point_body_m")
        return points * MM_PER_M @ self.rotation_body_from_cad + self.body_origin_in_cad_mm

    def direction_cad_to_body(self, direction_cad: ArrayLike) -> FloatArray:
        """Rotate direction(s) from CAD axes to body axes; no offset, no unit change."""
        directions = _as_vectors(direction_cad, 3, "direction_cad")
        return directions @ self.rotation_body_from_cad.T

    def direction_body_to_cad(self, direction_body: ArrayLike) -> FloatArray:
        """Rotate direction(s) from body axes to CAD axes; no offset, no unit change."""
        directions = _as_vectors(direction_body, 3, "direction_body")
        return directions @ self.rotation_body_from_cad
