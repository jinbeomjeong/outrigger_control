"""Read the Chrono state once per step and copy it (R9); true-state extraction.

``00_docs/03_chrono/chrono_build_plan.md`` 3.1 (``chrono/probes``), 3.2 (frame convention of
``TruthState``), R9; ``dynamics_model.md`` 4.6 ruling 2, step 1 (state copy).

:func:`read_probe` is the only place where the L1 model reads Chrono values for recording
and verification. Every value is copied into Python floats / numpy arrays at once, so no
SWIG reference (``GetPos()`` returns one) outlives the call. It must run **before** the
ground-bushing hook of the same step, so that the bushing anchors and contact flags it
stores are the ones that acted during the step just taken (the hook changes them for the
next step; one-step lag, R15).

Conventions of the copied state (all SI, world frame Z-up):

* ``body_*``: the machine body frame (origin = CAD origin, :mod:`outrigger_sim.chrono.bodies`)
  - Chrono's superstructure frame is the centre of mass, so the origin position and velocity
  are transformed here (plan 3.2).
* ``motor_force_N``: ``ChLinkMotorLinearPosition.GetMotorForce()`` with the link Z axis on body
  -z (R4); positive pushes the pad down (checked 2026-10-20: locked leg on a floor gives
  ``+(contact - rod weight)``). For the L1 position motor this is the cylinder force
  ``F_cyl`` (pressure x bore area) of ``dynamics_model.md`` 1.1.
* ``pad_contact_world_N``: ``ChBody.GetContactForce()`` of each leg moving part, world axes
  (checked 2026-10-20 with a body rotated 30 deg; the pad sphere is the only contact shape
  of the rod body).
* ``stroke_true_m``: actual stroke = motor position minus the compression of the locked oil
  column ``F_cyl / k_oil`` (``contact.rigid_floor.L1.derivation.k_oil_N_m``, head side only;
  the rod side is the separate ``actuator.rod_side`` spring of L1-R). In L1 the oil
  compliance is lumped into the pad contact stiffness, so the rigid motor position is the commanded (locked) stroke and the
  piston sits ``F_cyl / k_oil`` (about 5 mm at the operating point) shorter (signals
  ``TruthState.stroke_true_m``, user decision 2026-10-20). Rod, frame and slab compliance do
  not change the stroke.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.signals import TruthState


def _v(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


@dataclass(frozen=True, eq=False)
class ProbeState:
    """Copied Chrono state after one step (before the ground-bushing hook of that step)."""

    t_s: float
    body_pos_m: NDArray[np.float64]
    body_quat_wxyz: NDArray[np.float64]
    body_vel_m_s: NDArray[np.float64]
    body_omega_rad_s: NDArray[np.float64]
    cog_pos_m: NDArray[np.float64]
    motor_pos_m: NDArray[np.float64]
    motor_force_N: NDArray[np.float64]
    pad_contact_world_N: NDArray[np.float64]
    """(4, 3)."""
    pad_sphere_centre_world_m: NDArray[np.float64]
    """(4, 3)."""
    pad_sphere_radius_m: NDArray[np.float64]
    leg_offset_in_body_m: NDArray[np.float64]
    """(4, 3) leg COG in superstructure body coordinates minus its nominal position at the
    motor's set extension (prismatic guide + motor constraint violation)."""
    crawler_contact_world_N: NDArray[np.float64]
    floor_normal_world: NDArray[np.float64]
    floor_point_world_m: NDArray[np.float64]
    bushing_in_contact: NDArray[np.bool_]
    bushing_anchor_world_m: NDArray[np.float64]
    """(4, 3), NaN rows without a bushing (anchors that acted during the step)."""
    bushing_force_world_N: NDArray[np.float64]
    """(4, 3) bushing force on the pad (last load evaluation = end of the step)."""
    n_contacts: int

    @property
    def pad_normal_force_N(self) -> NDArray[np.float64]:
        """Signed contact force along the floor normal per pad (N, up +)."""
        return self.pad_contact_world_N @ self.floor_normal_world

    @property
    def penetration_m(self) -> NDArray[np.float64]:
        """Geometric pad sphere penetration ``r - n . (c - p0)`` (positive = overlap)."""
        heights = (self.pad_sphere_centre_world_m - self.floor_point_world_m) @ (
            self.floor_normal_world
        )
        return self.pad_sphere_radius_m - heights


def read_probe(model: Any) -> ProbeState:
    """Copy the state of an :class:`outrigger_sim.chrono.model.L1Model` (R9).

    Reads only; call it before ``GroundBushingCoulomb.after_step`` of the same step.
    """
    sup = model.superstructure
    origin_local = model.origin_in_cog_frame_ch
    origin = sup.TransformPointLocalToParent(origin_local)
    vel = sup.PointSpeedLocalToParent(origin_local)
    q = sup.GetRot()
    omega = sup.GetAngVelParent()
    cog = sup.GetPos()
    legs = model.legs
    motors = model.motors
    centres = np.array(
        [
            _v(leg.TransformPointLocalToParent(c))
            for leg, c in zip(legs, model.sphere_centres_local_ch, strict=True)
        ]
    )
    offsets = np.empty((len(legs), 3))
    for i, leg in enumerate(legs):
        # COG-frame coordinates of the superstructure + its COM = body coordinates
        local = _v(sup.TransformPointParentToLocal(leg.GetPos())) + model.sup_com_body_m
        offsets[i] = local - model.leg_com_body_nominal_m(i)
    gb = model.bushing
    return ProbeState(
        t_s=float(model.system.GetChTime()),
        body_pos_m=_v(origin),
        body_quat_wxyz=np.array([q.e0, q.e1, q.e2, q.e3], dtype=float),
        body_vel_m_s=_v(vel),
        body_omega_rad_s=_v(omega),
        cog_pos_m=_v(cog),
        motor_pos_m=np.array([m.GetMotorPos() for m in motors], dtype=float),
        motor_force_N=np.array([m.GetMotorForce() for m in motors], dtype=float),
        pad_contact_world_N=np.array([_v(leg.GetContactForce()) for leg in legs]),
        pad_sphere_centre_world_m=centres,
        pad_sphere_radius_m=np.array(model.sphere_radii_m, dtype=float),
        leg_offset_in_body_m=offsets,
        crawler_contact_world_N=_v(sup.GetContactForce()),
        floor_normal_world=gb.normal_world(),
        floor_point_world_m=np.array(model.floor_point_world_m, dtype=float),
        bushing_in_contact=gb.in_contact,
        bushing_anchor_world_m=gb.anchors_world_m(),
        bushing_force_world_N=gb.tangential_force_world_N(),
        n_contacts=int(model.system.GetNumContacts()),
    )


def truth_state(
    state: ProbeState,
    *,
    s_ref_m: Sequence[float],
    u_applied_m_s: Sequence[float],
    k_oil_N_m: Sequence[float],
) -> TruthState:
    """Engine-independent :class:`TruthState` from a probe copy (plan 3.2 conventions)."""
    n = state.floor_normal_world
    tangential = state.bushing_force_world_N - np.outer(state.bushing_force_world_N @ n, n)
    f_cyl = state.motor_force_N
    stroke_true = state.motor_pos_m - f_cyl / np.asarray(k_oil_N_m, dtype=float)
    return TruthState(
        t_s=state.t_s,
        body_pos_m=state.body_pos_m,
        body_quat_wxyz=state.body_quat_wxyz,
        body_vel_m_s=state.body_vel_m_s,
        body_omega_rad_s=state.body_omega_rad_s,
        s_motor_m=state.motor_pos_m,
        s_ref_m=np.asarray(s_ref_m, dtype=float),
        u_applied_m_s=np.asarray(u_applied_m_s, dtype=float),
        F_cyl_N=f_cyl,
        F_contact_n_N=state.pad_normal_force_N,
        F_contact_t_N=tangential[:, :2],
        is_pad_in_contact=state.bushing_in_contact,
        F_crawler_N=state.crawler_contact_world_N,
        bushing_anchor_m=state.bushing_anchor_world_m,
        stroke_true_m=stroke_true,
    )


def chvec(values: Sequence[float]) -> ch.ChVector3d:
    """ChVector3d from three floats (helper for the model's cached local points)."""
    x, y, z = (float(c) for c in values)
    return ch.ChVector3d(x, y, z)
