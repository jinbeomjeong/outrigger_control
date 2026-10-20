"""Rigid bodies of the L1 model: superstructure and the four leg moving parts.

``00_docs/03_chrono/chrono_build_plan.md`` S1 (``chrono/bodies``); ``dynamics_model.md`` 2.1.

* Superstructure: one rigid body with ``superstructure.auger_levels.<level>`` mass, centre of
  mass and the **full** inertia tensor about the centre of mass in body axes (YAML, case C;
  crawler and leg barrels included, leg moving parts excluded).
* Leg moving part (rod + piston + pad): ``legs.<leg>.moving_part`` mass, centre of mass in
  the retracted state (``com_retracted_m`` in the YAML, ``MassProperties.com_m`` in
  :mod:`outrigger_sim.params`) and inertia; at extension ``e`` it sits ``e`` lower along the
  body -z axis (``actuator.extension_direction``).

Body frames: Chrono ``ChBody`` frames are centre-of-mass frames whose axes are the body axes
(x forward, y left, z up; R3). The machine pose is given as the pose of the **body frame**
(origin = CAD origin, :data:`outrigger_sim.frames.BODY_ORIGIN_IN_CAD_MM`): a world position
of the origin and a wxyz quaternion world <- body. Positions in body coordinates (YAML) map
to world as ``origin + R p``. The ChBody inertia setters take the tensor in body axes:
``SetInertiaXX(Ixx, Iyy, Izz)`` and ``SetInertiaXY(Ixy, Ixz, Iyz)`` with the off-diagonal
entries of the tensor itself (YAML convention: off-diagonal = -integral(x y dm), the same
sign convention Chrono uses for its inertia matrix).

Units SI. Every Chrono value read here is copied (R9).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.frames import quat_to_matrix
from outrigger_sim.geometry import leg_com_body_m
from outrigger_sim.params import MassProperties, Params

SUPERSTRUCTURE_NAME = "superstructure"


def leg_body_name(leg: str) -> str:
    """Chrono body name of a leg moving part (``leg_FL`` ...)."""
    return f"leg_{leg}"


@dataclass(frozen=True)
class BodyPose:
    """Pose of the machine body frame: origin (CAD origin) in world and world <- body quat."""

    origin_m: tuple[float, float, float]
    quat_wxyz: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)

    @property
    def rotation(self) -> NDArray[np.float64]:
        return quat_to_matrix(np.asarray(self.quat_wxyz, dtype=float))

    def to_world(self, point_body: ArrayLike) -> NDArray[np.float64]:
        """World position of a point given in body coordinates."""
        return np.asarray(self.origin_m, dtype=float) + self.rotation @ np.asarray(
            point_body, dtype=float
        )

    def chrono_quat(self) -> ch.ChQuaterniond:
        w, x, y, z = (float(c) for c in self.quat_wxyz)
        return ch.ChQuaterniond(w, x, y, z)


def _chvec(a: ArrayLike) -> ch.ChVector3d:
    x, y, z = (float(c) for c in np.asarray(a, dtype=float).reshape(3))
    return ch.ChVector3d(x, y, z)


def _rigid_body(
    name: str, props: MassProperties, com_body_m: ArrayLike, pose: BodyPose
) -> ch.ChBody:
    inertia = np.asarray(props.inertia_kg_m2, dtype=float)
    body = ch.ChBody()
    body.SetName(name)
    body.SetMass(float(props.mass_kg))
    body.SetInertiaXX(ch.ChVector3d(inertia[0, 0], inertia[1, 1], inertia[2, 2]))
    body.SetInertiaXY(ch.ChVector3d(inertia[0, 1], inertia[0, 2], inertia[1, 2]))
    body.SetPos(_chvec(pose.to_world(com_body_m)))
    body.SetRot(pose.chrono_quat())
    return body


def make_superstructure(params: Params, pose: BodyPose) -> ch.ChBody:
    """Superstructure body of the selected auger level (``params.level``), not yet added."""
    props = params.superstructure.mass_properties
    return _rigid_body(SUPERSTRUCTURE_NAME, props, props.com_m, pose)


def make_leg_moving_parts(
    params: Params, extensions_m: Sequence[float], pose: BodyPose
) -> list[ch.ChBody]:
    """Four leg moving parts (LEG_ORDER) at the given extensions, not yet added."""
    return [
        _rigid_body(
            leg_body_name(leg.name),
            leg.moving_part,
            leg_com_body_m(params, i, float(extensions_m[i])),
            pose,
        )
        for i, leg in enumerate(params.legs)
    ]


@dataclass(frozen=True)
class ChronoMassProperties:
    """Mass properties read back from a Chrono body (V0), body axes, about the COG."""

    mass_kg: float
    com_world_m: NDArray[np.float64]
    inertia_kg_m2: NDArray[np.float64]


def read_mass_properties(body: ch.ChBody) -> ChronoMassProperties:
    """Mass, COG world position and the 3x3 inertia tensor as Chrono holds them."""
    xx = body.GetInertiaXX()
    xy = body.GetInertiaXY()
    inertia = np.array([[xx.x, xy.x, xy.y], [xy.x, xx.y, xy.z], [xy.y, xy.z, xx.z]], dtype=float)
    p = body.GetPos()
    return ChronoMassProperties(
        mass_kg=float(body.GetMass()),
        com_world_m=np.array([p.x, p.y, p.z], dtype=float),
        inertia_kg_m2=inertia,
    )
