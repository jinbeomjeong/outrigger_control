"""Static settle scenario on four pads: analytic start, settle and still windows (S1).

``00_docs/03_chrono/chrono_build_plan.md`` section 2 (initial-condition rules 1-3) and S1;
``dynamics_model.md`` 4.5 item 1. Engine independent: this module computes the start pose
and the time windows; the engine (``chrono/model``) places the bodies and runs the steps.

Analytic start (rule 1, ``AnalyticStart.ON_PADS``): the body pose comes from the V2
penetration and V3 attitude reference values of the level
(``reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels /
<level> / static_penetration_or_compression_mm`` and ``.../ static_attitude_deg (roll,
pitch)``):

* attitude = ZYX (yaw 0, pitch, roll) from the V3 values;
* height: the zero pose has the pads just touching at the operating extensions (body
  origin at :func:`outrigger_sim.geometry.pads_touching_origin_z_m`); the origin height is
  set so that the mean of the exact sphere penetrations ``r - (z_centre - z_floor)`` of the
  rotated body equals the mean of the V2 values. The four individual penetrations then
  differ from V2 only by the rounding of the reference values and second-order rotation
  terms (reported as ``penetration_residual_mm``).

The ground bushings are created at this pose with zero tangential force, which is the exact
equilibrium of the tangential direction (no horizontal load on a level floor). Because the
start uses the values that V2 / V3 judge, the judgement is made after the settle window
(risk 3: staying at the start values is the equilibrium check), and one run without the
analytic start (zero pose, settle >= ``simulation.settle_on_pads_min_s``) cross-checks it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import quat_from_euler_zyx, quat_to_matrix
from outrigger_sim.geometry import pad_sphere_centre_body_m, pads_touching_origin_z_m
from outrigger_sim.params import Params
from outrigger_sim.verify.reference import (
    L1_STATIC_ATTITUDE_DEG,
    L1_STATIC_PENETRATION_MM,
    References,
)

SETTLE_S = 10.0
"""Plan section 2 rule 1: settle after the analytic start before the judgement window."""
STILL_S = 5.0
"""``dynamics_model.md`` 4.5 item 1 / V13: still window (drift, force variation)."""


def cross_settle_s(params: Params) -> float:
    """Settle length without the analytic start: ``simulation.settle_on_pads_min_s`` rounded
    up to whole seconds (52.86 -> 53 s, plan S1 / rule 2)."""
    return float(math.ceil(params.simulation.settle_on_pads_min_s))


@dataclass(frozen=True)
class StaticStartPose:
    """Analytic static start on four pads."""

    origin_m: tuple[float, float, float]
    quat_wxyz: tuple[float, float, float, float]
    roll_deg: float
    pitch_deg: float
    zero_pose_origin_z_m: float
    u_z_m: float
    """Origin height relative to the zero pose (negative = sunk)."""
    penetration_ref_mm: tuple[float, ...]
    penetration_start_mm: tuple[float, ...]
    penetration_residual_mm: tuple[float, ...]
    ref_keys: tuple[str, ...]


def analytic_static_pose(
    params: Params,
    refs: References,
    extensions_m: Sequence[float],
    *,
    floor_z_m: float | None = None,
) -> StaticStartPose:
    """Body pose of the analytic static solution of ``params.level`` (rule 1).

    Raises:
        ValueError: The legs do not touch at one height at ``extensions_m``.
    """
    level = params.level.value
    pen_ref_mm = np.asarray(refs.get(L1_STATIC_PENETRATION_MM, level=level), dtype=float)
    roll_deg, pitch_deg = (float(v) for v in refs.get(L1_STATIC_ATTITUDE_DEG, level=level))
    floor = params.ground.crawler_bottom_z_m if floor_z_m is None else float(floor_z_m)
    heights = pads_touching_origin_z_m(params, extensions_m, floor)
    if float(np.ptp(heights)) > 1e-9:
        raise ValueError(f"pads do not touch at one height: {heights}")
    z0 = float(heights.mean())
    quat = quat_from_euler_zyx(0.0, math.radians(pitch_deg), math.radians(roll_deg))
    rot = quat_to_matrix(quat)
    radii = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    centres_rot_z = np.array(
        [
            (rot @ pad_sphere_centre_body_m(params, i, float(extensions_m[i])))[2]
            for i in range(len(params.legs))
        ]
    )
    # penetration_i = r_i - (origin_z + centre_rot_z_i - floor); match the mean
    pen_ref_m = pen_ref_mm * 1e-3
    origin_z = float(np.mean(radii - pen_ref_m - centres_rot_z + floor))
    pen_start_m = radii - (origin_z + centres_rot_z - floor)
    return StaticStartPose(
        origin_m=(0.0, 0.0, origin_z),
        quat_wxyz=tuple(float(c) for c in quat),  # type: ignore[arg-type]
        roll_deg=roll_deg,
        pitch_deg=pitch_deg,
        zero_pose_origin_z_m=z0,
        u_z_m=origin_z - z0,
        penetration_ref_mm=tuple(float(v) for v in pen_ref_mm),
        penetration_start_mm=tuple(float(v) for v in pen_start_m * 1e3),
        penetration_residual_mm=tuple(float(v) for v in (pen_start_m - pen_ref_m) * 1e3),
        ref_keys=(
            L1_STATIC_PENETRATION_MM.resolve(level=level).notation(),
            L1_STATIC_ATTITUDE_DEG.resolve(level=level).notation(),
        ),
    )


def linear_static_solution(
    params: Params, kn_N_m: Sequence[float]
) -> dict[str, NDArray[np.float64] | float]:
    """Independent cross-check: 3-DoF linear statics with the given pad stiffnesses.

    ``dynamics_model.md`` 3.1: ``A = [1, y_i, -x_i]``, ``A^T K A q = -w`` with
    ``w = [W, W y_c, -W x_c]`` for the superstructure weight at its centre of mass; the rod
    weights act straight at the pads. Penetration ``delta = -(A q)``; contact force
    ``k delta`` + nothing else (rod weight enters ``q`` through the pad term below).

    Returns:
        ``q`` = (u_z [m], roll [rad], pitch [rad]), ``penetration_m``, ``contact_N``,
        ``cylinder_N`` (contact minus rod weight).
    """
    g = params.meta.gravity_m_s2
    props = params.superstructure.mass_properties
    xy = np.array([leg.pad_bottom_center_retracted_m[:2] for leg in params.legs], dtype=float)
    k = np.asarray(kn_N_m, dtype=float)
    a = np.column_stack([np.ones(len(k)), xy[:, 1], -xy[:, 0]])
    w_sup = props.mass_kg * g
    xc, yc = props.com_m[0], props.com_m[1]
    rods = np.array([leg.moving_part.mass_kg * g for leg in params.legs])
    # generalised load (down positive on u_z equals -z): weight of superstructure and rods
    load = np.array([w_sup, w_sup * yc, -w_sup * xc]) + a.T @ rods
    q = -np.linalg.solve(a.T @ (k[:, None] * a), load)
    penetration = -(a @ q)
    contact = k * penetration
    return {
        "q": q,
        "penetration_m": penetration,
        "contact_N": contact,
        "cylinder_N": contact - rods,
        "total_weight_N": float(w_sup + rods.sum()),
    }
