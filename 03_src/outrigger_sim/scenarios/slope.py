"""Sloped-floor statics (V12): tilted floor, levelled body, pads placed with zero force, g ramp.

``00_docs/03_chrono/chrono_build_plan.md`` S2a (``scenarios/slope``); ``dynamics_model.md`` 3.6
(procedure), 5 V12, 5.2 ruling 2 (S2a implication). Engine independent: this module computes
the floor plane, the start pose, the leg extensions and the gravity ramp; the engine
(``chrono/model``, ``chrono/runs``) rotates the floor body and runs the steps.

Procedure (3.6): the body is level at the levelling extensions of the case, the pads touch
the sloped floor with zero force (no tangential history), the ground bushings are created at
t = 0 with zero deformation, then gravity is ramped from 0 to g. The run is never started from
the level S1 snapshot or from a drop (5.2 ruling 2: the drop leaves +-4-5 kN of tangential
preload that would hide the +-0.75-0.80 kN V12 horizontal forces).

Floor plane of a case (``04_scripts/01_dynamics/run_reference.py`` ``levelled_extension`` and
``dyn_model.static_slope_10dof``): ``z = z_floor + sx x + sy y`` with
``sx = -tan(pitch)``, ``sy = tan(roll)``, i.e. a ground that would give the machine a body roll
/ pitch of the named sign if it sat on it (pitch + = nose down: the floor falls towards +x).
Unit normal ``n = (-sx, -sy, 1) / |.|``. The plane passes through the world point
``(0, 0, ground.crawler_bottom_z_m)``; the floor body is rotated about that point so that its
local z axis is ``n`` and its local x axis is the projection of world x onto the plane.

Leg extensions: the reference extensions (``reference.json / slope_V12 / <case> /
extension_m``) are rounded to 0.1 mm, so with them the four pad spheres cannot all touch the
plane at once (plan S2a risk: the rounding moves the loads by up to 0.26 kN, the size of
the horizontal tolerance). :func:`slope_start` therefore uses the exact plane-touching set
closest to the reference (same body height offset, mean difference 0) and reports the
difference from the rounded values. Units SI, world frame Z-up.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import matrix_to_quat
from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m
from outrigger_sim.params import Params
from outrigger_sim.verify.reference import SLOPE_V12_EXTENSION_M, References

RAMP_S = 3.0
"""Gravity ramp length (plan S2a V12: 2-5 s, default 3 s; >= 4 x the 0.56 s first period)."""
SETTLE_AFTER_RAMP_S = 53.0
"""Settle after the ramp: ceil(``simulation.settle_on_pads_min_s`` 52.86 s) (user decision
2026-10-20); :func:`settle_after_ramp_s` reads the YAML value."""
MEAN_WINDOW_S = 3.0
"""V12: the judged values are the means over the last 3 s."""
STILL_WINDOW_S = 5.0
"""V13: still window of ``dynamics_model.md`` 4.5 item 1 (drift, force variation), the last 5 s
of the run; it starts after ``RAMP_S + SETTLE_AFTER_RAMP_S - 2 s``, i.e. it ends with the
3 s mean window."""

_CASE_PATTERN = re.compile(
    r"^ground roll (?P<roll>-?\d+(?:\.\d+)?) deg, pitch (?P<pitch>-?\d+(?:\.\d+)?) deg$"
)


def settle_after_ramp_s(params: Params) -> float:
    """``ceil(simulation.settle_on_pads_min_s)`` (52.86 -> 53 s)."""
    return float(math.ceil(params.simulation.settle_on_pads_min_s))


def parse_case(case: str) -> tuple[float, float]:
    """``"ground roll -2 deg, pitch 1.5 deg"`` -> ``(roll_deg, pitch_deg)``.

    Raises:
        ValueError: The text is not a slope case name.
    """
    match = _CASE_PATTERN.match(case)
    if match is None:
        raise ValueError(f"not a slope case name: {case!r}")
    return float(match["roll"]), float(match["pitch"])


def floor_normal(roll_deg: float, pitch_deg: float) -> NDArray[np.float64]:
    """Unit floor normal ``(-sx, -sy, 1)/|.|`` with ``sx = -tan(pitch)``, ``sy = tan(roll)``."""
    sx = -math.tan(math.radians(pitch_deg))
    sy = math.tan(math.radians(roll_deg))
    n = np.array([-sx, -sy, 1.0])
    return n / np.linalg.norm(n)


def floor_rotation(normal: Sequence[float]) -> NDArray[np.float64]:
    """3x3 rotation world <- floor: columns x (world x projected on the plane), y = z x x, z = n."""
    z = np.asarray(normal, dtype=float)
    z = z / np.linalg.norm(z)
    x = np.array([1.0, 0.0, 0.0]) - z[0] * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.column_stack((x, y, z))


def gravity_ramp(t_s: float, ramp_s: float = RAMP_S) -> float:
    """Gravity scale in [0, 1]: half-cosine ``(1 - cos(pi t / T)) / 2`` for ``0 <= t <= T``.

    C1-smooth at both ends (no acceleration jump at the start or the end of the ramp), so the
    ramp excites the 1.8 Hz rocking less than a linear ramp of the same length.
    """
    if t_s <= 0.0:
        return 0.0
    if t_s >= ramp_s:
        return 1.0
    return 0.5 * (1.0 - math.cos(math.pi * t_s / ramp_s))


@dataclass(frozen=True)
class SlopeStart:
    """Start of one V12 case (all SI, world frame)."""

    case: str
    roll_deg: float
    pitch_deg: float
    normal_world: tuple[float, float, float]
    floor_quat_wxyz: tuple[float, float, float, float]
    """World <- floor rotation of the floor body."""
    floor_pos_m: tuple[float, float, float]
    """Floor body frame origin so that ``(0, 0, z_floor)`` stays on the surface."""
    floor_point_world_m: tuple[float, float, float]
    body_origin_m: tuple[float, float, float]
    """Level body (identity rotation): origin position."""
    extensions_m: tuple[float, ...]
    """Exact plane-touching extensions (LEG_ORDER) used by the run."""
    extensions_ref_m: tuple[float, ...]
    """``reference.json / slope_V12 / <case> / extension_m`` (rounded to 0.1 mm)."""
    extension_minus_ref_mm: tuple[float, ...]
    sphere_gap_m: tuple[float, ...]
    """Signed distance sphere surface - plane at the start (0 up to rounding)."""
    ref_key: str


def slope_start(params: Params, refs: References, case: str) -> SlopeStart:
    """Floor pose, level body pose and extensions of a V12 case.

    The pads touch the plane exactly: ``n . (o + c_i(e_i) - p0) = r_i`` with the sphere centre
    ``c_i(e) = c_i(0) + e d`` (``d`` = extension direction). The body origin height is chosen
    so that the mean of ``e_i - e_ref,i`` is 0.
    """
    roll_deg, pitch_deg = parse_case(case)
    n = floor_normal(roll_deg, pitch_deg)
    rot = floor_rotation(n)
    z_floor = float(params.ground.crawler_bottom_z_m)
    p0 = np.array([0.0, 0.0, z_floor])
    floor_pos = p0 - rot @ p0
    e_ref = np.asarray(refs.get(SLOPE_V12_EXTENSION_M, case=case), dtype=float)
    d = extension_direction(params)
    nd = float(n @ d)
    radii = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    c0 = np.array([pad_sphere_centre_body_m(params, i, 0.0) for i in range(len(params.legs))])
    # e_i = (r_i - n.(c0_i - p0) - n_z z_o) / (n.d); pick z_o so that mean(e - e_ref) = 0
    base = radii - (c0 - p0) @ n
    z_o = float(np.mean(base - e_ref * nd) / n[2])
    ext = (base - n[2] * z_o) / nd
    origin = np.array([0.0, 0.0, z_o])
    centres = origin + c0 + ext[:, None] * d
    gap = (centres - p0) @ n - radii
    quat = matrix_to_quat(rot)
    return SlopeStart(
        case=case,
        roll_deg=roll_deg,
        pitch_deg=pitch_deg,
        normal_world=tuple(float(v) for v in n),  # type: ignore[arg-type]
        floor_quat_wxyz=tuple(float(v) for v in quat),  # type: ignore[arg-type]
        floor_pos_m=tuple(float(v) for v in floor_pos),  # type: ignore[arg-type]
        floor_point_world_m=(0.0, 0.0, z_floor),
        body_origin_m=(0.0, 0.0, z_o),
        extensions_m=tuple(float(v) for v in ext),
        extensions_ref_m=tuple(float(v) for v in e_ref),
        extension_minus_ref_mm=tuple(float(v) for v in (ext - e_ref) * 1e3),
        sphere_gap_m=tuple(float(v) for v in gap),
        ref_key=SLOPE_V12_EXTENSION_M.resolve(case=case).notation(),
    )


def reference_reaction_world_N(
    vertical_N: Sequence[float], horizontal_xy_N: Sequence[Sequence[float]]
) -> NDArray[np.float64]:
    """(4, 3) floor -> rod reaction in world axes from the ``slope_V12 / <case> / L1`` arrays
    (``contact_horizontal_xy_N`` = R[:, :2], ``contact_vertical_N`` = R[:, 2])."""
    xy = np.asarray(horizontal_xy_N, dtype=float)
    z = np.asarray(vertical_N, dtype=float)
    return np.column_stack((xy, z))


def split_normal_tangential(
    reaction_world_N: NDArray[np.float64], normal: Sequence[float]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Normal component ``N = R . n`` and in-plane magnitude ``|R - N n|`` per row."""
    n = np.asarray(normal, dtype=float)
    r = np.asarray(reaction_world_N, dtype=float)
    normal_part = r @ n
    tangential = np.linalg.norm(r - np.outer(normal_part, n), axis=1)
    return normal_part, tangential
