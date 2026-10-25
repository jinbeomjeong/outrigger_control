"""Prescribed ground settlement under named pads of the L2b-NSC model (S8, C-S8-3).

``00_docs/04_control/s6_control_spec.md`` rev. 39 202 / 209.1 C-S8-3: the L2b runner refused
floor events ("floor events need settlement patches (L1 only)"). This module gives the L2b
model the same kinematic floor patch as the L1 model (``chrono/ground_settlement``):

* per settling leg one **patch body** (mass ``contact.rigid_floor.ground_body_mass_kg`` = 1e9 kg,
  same pose as the floor body, collision family :data:`FAMILY_PATCH`) carrying an NSC box whose
  top face is the floor surface around that pad (half size :data:`PATCH_HALF_SIZE_M`, ASSUMPTION:
  larger than any pad slide of a run), same NSC friction as the floor plate;
* the leg's rod stops colliding with the floor plate (``DisallowCollisionsWith(FAMILY_FLOOR)``;
  Bullet needs both masks to allow a pair, so the plate under the pad is no longer seen) and
  touches its patch only; the patch does not collide with the superstructure (crawler spheres);
* the patch is driven along the floor normal by the L1 class
  :class:`~outrigger_sim.chrono.ground_settlement.GroundSettlement` (``ChLinkMotorLinearPosition``
  to the floor, ``z(t) = -depth Poly345((t - t0) / ramp)``, position / velocity / acceleration
  continuous, so the NSC contact sees the true patch velocity).

Attach right after building the model and before the first step (adding bodies later would
change the solver's item order):  ``patches = attach_ground_patches(model, ("RR",))``.

Snapshot: :func:`attach_ground_patches` also wraps ``model.snapshot`` / ``model.restore`` so the
patch bodies are part of the body list and the ``ground_settlement`` part (schedule) is stored.
A snapshot of a model with patches only restores into a model with the same patches.

Diagnostic caveat (as L1): ``ProbeState.penetration_m`` measures against the fixed floor plane.

Units SI; world Z-up.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pychrono as ch

from outrigger_sim.chrono.contact import FAMILY_FLOOR, FAMILY_SUPERSTRUCTURE
from outrigger_sim.chrono.ground_settlement import PART_PREFIX, GroundSettlement
from outrigger_sim.chrono.probes import chvec
from outrigger_sim.chrono.snapshot import capture_snapshot, engine_info, restore_snapshot
from outrigger_sim.chrono.system import ChronoModel, floor_material_values, make_nsc_material
from outrigger_sim.engine import Snapshot
from outrigger_sim.params import LEG_ORDER
from outrigger_sim.signals import Command

FAMILY_PATCH = 3
"""Collision family of the settling patch bodies (families 0-2 are floor, superstructure, rod)."""
PATCH_HALF_SIZE_M = (0.6, 0.6, 0.05)
"""ASSUMPTION: half size of the patch box (x, y in the floor plane, thickness); the pad sphere
contact point stays within a few cm of its start in every S6 / S7 run."""


class L2bGroundPatches:
    """Patch bodies + :class:`GroundSettlement` of the settling legs of one L2b model."""

    def __init__(self, model: Any, legs: Sequence[str]) -> None:
        names = tuple(legs)
        if not names or len(set(names)) != len(names) or any(n not in LEG_ORDER for n in names):
            raise ValueError(f"legs must be distinct LEG_ORDER names, got {names}")
        if float(model.system.GetChTime()) != 0.0:
            raise ValueError("attach the ground patches before the first step")
        self.model = model
        self.leg_names = names
        params = model.params
        floor = model.floor
        mass = float(params.contact.rigid_floor.ground_body_mass_kg)
        mu = floor_material_values(params, ChronoModel.L2B_NSC)["friction"]
        hx, hy, hz = PATCH_HALF_SIZE_M
        q_floor = floor.GetRot()
        p_floor = floor.GetPos()
        bodies = []
        self.patch_centres_floor_m: dict[str, list[float]] = {}
        for name in names:
            i = LEG_ORDER.index(name)
            rod = model.legs[i]
            c_world = rod.TransformPointLocalToParent(model.sphere_centres_local_ch[i])
            local = floor.TransformPointParentToLocal(c_world)  # floor frame (Z = normal)
            centre = np.array([local.x, local.y, model.floor_z_m - hz])
            body = ch.ChBody()
            body.SetName(f"pad_patch_{name}")
            body.SetMass(mass)
            body.SetInertiaXX(ch.ChVector3d(mass, mass, mass))
            body.SetPos(ch.ChVector3d(p_floor.x, p_floor.y, p_floor.z))
            body.SetRot(ch.ChQuaterniond(q_floor.e0, q_floor.e1, q_floor.e2, q_floor.e3))
            body.EnableCollision(True)
            body.AddCollisionShape(
                ch.ChCollisionShapeBox(make_nsc_material(mu), 2.0 * hx, 2.0 * hy, 2.0 * hz),
                ch.ChFramed(chvec(centre), ch.QUNIT))
            cm = body.GetCollisionModel()
            cm.SetFamily(FAMILY_PATCH)
            cm.DisallowCollisionsWith(FAMILY_SUPERSTRUCTURE)
            cm.DisallowCollisionsWith(FAMILY_PATCH)
            cm.DisallowCollisionsWith(FAMILY_FLOOR)  # the box sits inside the floor plate
            model.system.Add(body)
            rod.GetCollisionModel().DisallowCollisionsWith(FAMILY_FLOOR)
            bodies.append(body)
            self.patch_centres_floor_m[name] = centre.tolist()
        self.bodies = tuple(bodies)
        self.settlement = GroundSettlement(model.system, floor, names, bodies)
        self.friction = mu

    # --- schedule --------------------------------------------------------------------------

    def schedule(self, t_start_s: float, depth_m: float, ramp_s: float, *,
                 dt_s: float | None = None) -> None:
        self.settlement.schedule(t_start_s, depth_m, ramp_s, dt_s=dt_s)

    @property
    def is_scheduled(self) -> bool:
        return self.settlement.is_scheduled

    def displacement_m(self, t_s: float | None = None) -> float:
        return self.settlement.displacement_m(t_s)

    def meta(self) -> dict[str, Any]:
        return {**self.settlement.meta(), "engine": "L2b_NSC", "family_patch": FAMILY_PATCH,
                "patch_half_size_m": list(PATCH_HALF_SIZE_M),
                "patch_centres_floor_frame_m": self.patch_centres_floor_m,
                "friction": self.friction,
                "rule": "rod of a settling leg collides with its patch only (floor masked); "
                        "patch box top = floor surface; 1e9 kg patch on a position motor "
                        "(chrono/ground_settlement)"}


def attach_ground_patches(model: Any, legs: Sequence[str]) -> L2bGroundPatches:
    """Build the patches on ``model`` (an ``L2bModel`` before its first step) and wrap its
    snapshot / restore so the patch bodies and the schedule travel with a snapshot."""
    patches = L2bGroundPatches(model, legs)
    model.ground_patches = patches

    def snapshot(held_command: Command | None = None) -> Snapshot:
        from outrigger_sim.chrono.l2b_model import ACTUATOR_PART, BUSHING_PART

        t = float(model.system.GetChTime())
        if held_command is None:
            held_command = Command(t_s=t, leg_speed_m_s=model.actuator.reference.command_m_s)
        return capture_snapshot(
            model.system, engine=engine_info(ChronoModel.L2B_NSC.value),
            params_sha256=model.params.sha256, held_command=held_command,
            bodies=(*model.bodies, *patches.bodies), motors=model.motors,
            s_ref_m=model.actuator.reference.s_ref_m,
            parts={ACTUATOR_PART: model.actuator, BUSHING_PART: model.bushings,
                   PART_PREFIX: patches.settlement})

    def restore(snap: Snapshot) -> float:
        from outrigger_sim.chrono.l2b_model import ACTUATOR_PART, BUSHING_PART

        restored = restore_snapshot(
            snap, model.system, engine=engine_info(ChronoModel.L2B_NSC.value),
            params_sha256=model.params.sha256, bodies=(*model.bodies, *patches.bodies),
            motors=model.motors,
            parts={ACTUATOR_PART: model.actuator, BUSHING_PART: model.bushings,
                   PART_PREFIX: patches.settlement})
        model.actuator.set_command(restored.held_command.leg_speed_m_s)
        return restored.time_s

    model.snapshot = snapshot
    model.restore = restore
    return patches


__all__ = ["FAMILY_PATCH", "PATCH_HALF_SIZE_M", "L2bGroundPatches", "attach_ground_patches"]
