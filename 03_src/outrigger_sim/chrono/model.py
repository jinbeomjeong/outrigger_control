"""L1 Chrono model: superstructure + four locked legs + pad / crawler contact + ground bushing.

``00_docs/03_chrono/chrono_build_plan.md`` S1 (and 3.1 ``chrono/model``); ``dynamics_model.md``
2.1, 4.1, 4.2, 4.6. The S1 model holds every leg at a fixed extension with a
``ChLinkMotorLinearPosition`` whose motion function is a constant (the locked L1 actuator:
default guide PRISMATIC, motor position = extension). Later stages replace the constant by
the actuator model (S2b) without changing the bodies, contacts or the hook order.

Build (:class:`L1Model`):

* ``make_system`` (R1 gravity, R2 Bullet, R6 floor 1e9 kg fixed, R11 integrator and solver,
  time step from the YAML ``simulation.L1.dt_s`` unless given), floor without the default
  plate;
* floor patches: one per leg with that leg's pad material, two crawler strips with the
  crawler material (R13, ``chrono/contact``);
* superstructure body of ``params.level`` (``chrono/bodies``) carrying the 24 crawler spheres
  of layout D (optional, default on);
* four leg moving parts, each with one pad sphere (radius = swivel-centre height) at the
  swivel centre;
* collision families (R14): floor 0, superstructure 1, rods 2; rods do not collide with 1;
* motors: ``Initialize(leg, superstructure, False, frame_leg, frame_body)`` with both frames
  on the leg axis, rotated by pi about x so that the link Z axis is body -z (R4); the leg
  frame sits ``e`` below the body frame, so ``GetMotorPos() = e`` after the first Update;
* ``GroundBushingCoulomb`` (L1 tangential model, R7, R15; tangential force at the ball
  centre by default, ``bushing_force_point``); with ``attach_bushings`` the bushings are
  created now (t = 0) with zero tangential force (plan section 2 rule 1);
* S2b: with ``actuator=True`` the motor functions are ramps (``ChFunctionRamp``) driven by
  :class:`~outrigger_sim.chrono.actuators.L1SpeedActuator` (rate-limited speed reference
  integrated in the actuator hook, plan rev. 8 + command ramp, user decision 2026-10-20).
  Without it the legs stay locked at ``extensions_m`` (S1, S2a).

Hook order after every step: see :meth:`L1Model.after_step`.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.actuators import PART_PREFIX as ACTUATOR_PART
from outrigger_sim.chrono.actuators import (
    L1SpeedActuator,
    make_motion_function,
)
from outrigger_sim.chrono.bodies import (
    BodyPose,
    make_leg_moving_parts,
    make_superstructure,
    read_mass_properties,
)
from outrigger_sim.chrono.contact import (
    FAMILY_FLOOR,
    FAMILY_ROD,
    FAMILY_SUPERSTRUCTURE,
    ContactReport,
    CrawlerSphereLayout,
    SphereContactReport,
    add_floor_patches,
    crawler_layout,
    crawler_material_values,
    floor_patches,
    pad_material_values,
    report_contacts,
    report_sphere_contacts,
    set_family,
    shape_materials,
)
from outrigger_sim.chrono.crawler_bushing import PART_PREFIX as CRAWLER_BUSHING_PART
from outrigger_sim.chrono.crawler_bushing import make_crawler_bushing
from outrigger_sim.chrono.ground_bushing import (
    DEFAULT_FORCE_POINT,
    BushingEvent,
    GroundBushingCoulomb,
)
from outrigger_sim.chrono.ground_settlement import PART_PREFIX as SETTLEMENT_PART
from outrigger_sim.chrono.ground_settlement import GroundSettlement
from outrigger_sim.chrono.probes import ProbeState, chvec, read_probe, truth_state
from outrigger_sim.chrono.rod_chamber_link import PART_PREFIX as ROD_CHAMBER_PART
from outrigger_sim.chrono.rod_chamber_link import (
    L1RodChamber,
    mechanics_from_params,
)
from outrigger_sim.hydraulics.rod_chamber import RodSideMechanics
from outrigger_sim.chrono.snapshot import (
    S_REF_KEY,
    capture_snapshot,
    engine_info,
    restore_snapshot,
)
from outrigger_sim.chrono.system import ChronoModel, StepPurpose, make_system
from outrigger_sim.engine import Snapshot
from outrigger_sim.frames import roll_pitch_from_quat
from outrigger_sim.geometry import (
    leg_com_body_m,
    pad_sphere_centre_body_m,
    pads_touching_origin_z_m,
)
from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.signals import Command, TruthState
from outrigger_sim.verify.s1 import StillWindowStats

GROUND_BUSHING_PART = "ground_bushing"
K_OIL_KEY = "contact.rigid_floor.L1.derivation.k_oil_N_m"

StepHook = Callable[["L1Model", float], None]
"""Actuator / external-load hook: ``hook(model, dt_s)``; must only set inputs for the next step."""
RecordHook = Callable[["L1Model", ProbeState], None]
"""Record hook: receives the state copy of the step (taken before the ground-bushing hook)."""


def operating_extensions_m(params: Params) -> tuple[float, ...]:
    """``contact.rigid_floor.L1.derivation.operating_extension_m`` in LEG_ORDER."""
    ext = params.contact.rigid_floor.L1.operating_extension_m
    return tuple(float(ext[i]) for i in range(len(LEG_ORDER)))


def zero_pose(params: Params, extensions_m: Sequence[float]) -> BodyPose:
    """Level pose with the pads just touching the floor (zero compression).

    Raises:
        ValueError: The four legs do not touch at the same body height (more than 1e-9 m
            apart), i.e. the extensions are not a level-touch set.
    """
    heights = pads_touching_origin_z_m(params, extensions_m)
    if float(np.ptp(heights)) > 1e-9:
        raise ValueError(f"pads do not touch at one height for {extensions_m}: {heights}")
    return BodyPose((0.0, 0.0, float(heights.mean())))


class _ActuatorPart:
    """Snapshot part adapter: actuator state + whether the next step starts with a full
    Update (``not IsUpdated()`` at capture time)."""

    def __init__(self, actuator: L1SpeedActuator, system: ch.ChSystem) -> None:
        self._actuator = actuator
        self._system = system

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        return self._actuator.state_arrays(next_step_full_update=not self._system.IsUpdated())

    def restore_state(self, arrays: Any) -> None:  # pragma: no cover - capture only
        self._actuator.restore_state(arrays)


@dataclass(frozen=True)
class StepResult:
    """What :meth:`L1Model.step` returns."""

    events: list[BushingEvent]
    probe: ProbeState | None


class L1Model:
    """S1 L1 model (legs locked at fixed extensions).

    Args:
        params: Parameters (auger level = ``params.level``).
        pose: Body-frame pose at t = 0; default :func:`zero_pose` (pads just touching).
        extensions_m: Leg extensions (LEG_ORDER); default the operating extensions.
        crawler: Add the 24 crawler spheres and crawler floor strips.
        attach_bushings: Create the ground bushings now (zero tangential force).
        dt_s: Time step; default from the YAML (``purpose``).
        purpose: ``"general"`` (``simulation.L1.dt_s``), ``"reference"``, ``"transition"``.
        solver, lock_sparsity_pattern: Passed to :func:`make_system`.
        floor_pose: Pose of the fixed floor body (default: identity, level floor). A tilted
            floor (S2a V12, ``scenarios/slope``) must keep the world point
            ``(0, 0, ground.crawler_bottom_z_m)`` on its surface (probe convention); it is
            set before the bushings are created.
        bushing_force_point: Ground-bushing force point (``ground_bushing.FORCE_POINTS``);
            default ball centre (user decision 2026-10-20, ``dynamics_model.md`` 5.3 ruling
            4 option A). ``"contact_point"`` reproduces the model before that decision.
        actuator: Drive the legs with :class:`L1SpeedActuator` (S2b); False = locked legs.
        actuator_ramp_s: 0 -> v_max time of the command acceleration limit (None = YAML
            ``actuator.command_ramp_s``; 0 = speed steps, only for the inertial-spike
            comparison).
        settlement_legs: Legs whose pad patch sits on a separately driven patch body for a
            prescribed ground settlement (S6 G4, ``chrono/ground_settlement``; default none =
            the S1-S6 model unchanged).
        crawler_bushings: Circular-Coulomb anchor bushings under the crawler spheres (Q12,
            ``chrono/crawler_bushing``; default off = the S1-S6 model unchanged).
        crawler_bushing_kt_scale: Sensitivity factor on the assumed crawler tangential
            stiffness (0.3 / 1 / 3).
        attach_crawler_bushings: Create crawler bushings now (zero tangential force, initial
            hold until loaded): True = the roller spheres, a list = those sphere indices (the
            loaded set of an analytic start); the others get theirs on touch (R15).
        force_saturation: With the actuator, cut the leg speed every step at the 210 bar
            force limits (S6, ``chrono/actuators`` force saturation; default on). Runs that
            never reach the limits are bit-identical to ``False``.
        rod_side_mechanics: L1-R mechanics override (``"off"`` / ``"one_sided_parallel"``;
            None = YAML ``actuator.rod_side.mechanics``, off when absent). Not part of
            ``Params.sha256``; snapshots carry the flag and refuse a mismatch.
        head_only_dashpot: Pad dashpot ``gn_per_pad_head_only_1_s`` (regression of the
            pre-L1-R head-only model) instead of ``gn_per_pad_1_s`` (LOCK basis, default).
    """

    def __init__(
        self,
        params: Params,
        *,
        pose: BodyPose | None = None,
        extensions_m: Sequence[float] | None = None,
        crawler: bool = True,
        attach_bushings: bool = True,
        dt_s: float | None = None,
        purpose: StepPurpose | str = StepPurpose.GENERAL,
        solver: str | None = None,
        lock_sparsity_pattern: bool | None = None,
        floor_pose: BodyPose | None = None,
        bushing_force_point: str = DEFAULT_FORCE_POINT,
        actuator: bool = False,
        actuator_ramp_s: float | None = None,
        force_saturation: bool = True,
        settlement_legs: Sequence[str] = (),
        crawler_bushings: bool = False,
        crawler_bushing_kt_scale: float = 1.0,
        attach_crawler_bushings: bool | Sequence[int] = True,
        rod_side_mechanics: str | None = None,
        head_only_dashpot: bool = False,
    ) -> None:
        self.params = params
        self.head_only_dashpot = bool(head_only_dashpot)
        self.last_probe: ProbeState | None = None
        """State copy of the last step (step 1 of :meth:`after_step`; None when the step was
        not captured). Read by hooks that need the step-n state after the bushing hook."""
        ext = (
            operating_extensions_m(params)
            if extensions_m is None
            else tuple(float(e) for e in extensions_m)
        )
        if len(ext) != len(LEG_ORDER):
            raise ValueError(f"need {len(LEG_ORDER)} extensions, got {ext}")
        self.extensions_m = ext
        self.pose = zero_pose(params, ext) if pose is None else pose
        bundle = make_system(
            params,
            ChronoModel.L1,
            purpose=purpose if dt_s is None else StepPurpose.GENERAL,
            dt=dt_s,
            solver=solver,
            lock_sparsity_pattern=lock_sparsity_pattern,
            floor_plate=False,
        )
        self.bundle = bundle
        self.system: ch.ChSystem = bundle.system
        self.floor: ch.ChBody = bundle.floor
        self.dt_s = bundle.dt_s
        self.floor_z_m = params.ground.crawler_bottom_z_m
        self.floor_point_world_m = (0.0, 0.0, self.floor_z_m)
        self.floor_pose = floor_pose
        if floor_pose is not None:
            fp = floor_pose
            self.floor.SetPos(chvec(fp.origin_m))
            self.floor.SetRot(fp.chrono_quat())
            on_plane = fp.rotation.T @ (np.asarray(self.floor_point_world_m) - fp.origin_m)
            if abs(on_plane[2] - self.floor_z_m) > 1e-12:
                raise ValueError(
                    f"floor pose moves (0, 0, {self.floor_z_m}) off the floor surface "
                    f"(local z {on_plane[2]!r})"
                )

        # floor patches (R13) and crawler layout
        self.crawler_layout: CrawlerSphereLayout | None = (
            crawler_layout(params) if crawler else None
        )
        self.patches = floor_patches(params, self.crawler_layout, head_only_dashpot)
        settle = tuple(settlement_legs)
        unknown = [n for n in settle if n not in LEG_ORDER]
        if unknown or len(set(settle)) != len(settle):
            raise ValueError(f"settlement_legs must be distinct LEG_ORDER names, got {settle}")
        moving_names = {f"pad_{n}" for n in settle}
        self.floor_body_patches = tuple(p for p in self.patches if p.name not in moving_names)
        """Patches on the fixed floor body (all of them without settlement legs)."""
        add_floor_patches(self.floor, self.floor_body_patches, self.floor_z_m)
        patch_bodies: dict[str, ch.ChBody] = {}
        for name in settle:
            body = ch.ChBody()
            body.SetName(f"pad_patch_{name}")
            mass = float(params.get("contact.rigid_floor.ground_body_mass_kg"))
            body.SetMass(mass)
            body.SetInertiaXX(ch.ChVector3d(mass, mass, mass))
            fpos, frot = self.floor.GetPos(), self.floor.GetRot()
            body.SetPos(ch.ChVector3d(fpos.x, fpos.y, fpos.z))
            body.SetRot(ch.ChQuaterniond(frot.e0, frot.e1, frot.e2, frot.e3))
            add_floor_patches(
                body, [p for p in self.patches if p.name == f"pad_{name}"], self.floor_z_m
            )
            self.system.Add(body)
            patch_bodies[name] = body
        self.settlement: GroundSettlement | None = None
        if settle:
            self.settlement = GroundSettlement(
                self.system, self.floor, settle, [patch_bodies[n] for n in settle]
            )

        # superstructure (+ crawler spheres)
        sup = make_superstructure(params, self.pose)
        com_body = np.asarray(params.superstructure.mass_properties.com_m, dtype=float)
        self.crawler_centres_local_m: NDArray[np.float64] = np.zeros((0, 3))
        if self.crawler_layout is not None:
            sup.EnableCollision(True)
            material = crawler_material_values(params).make()
            self.crawler_centres_local_m = (
                self.crawler_layout.centres_body_m(self.floor_z_m) - com_body
            )
            for centre in self.crawler_layout.centres_body_m(self.floor_z_m):
                sup.AddCollisionShape(
                    ch.ChCollisionShapeSphere(material, self.crawler_layout.sphere_radius_m),
                    ch.ChFramed(chvec(centre - com_body), ch.QUNIT),
                )
            set_family(sup, FAMILY_SUPERSTRUCTURE)
        self.system.Add(sup)
        self.superstructure = sup
        self.sup_com_body_m = com_body
        self.origin_in_cog_frame_ch = chvec(-com_body)

        # legs, pad spheres, locked position motors
        legs = make_leg_moving_parts(params, ext, self.pose)
        motors = []
        functions = []
        centres_local = []
        radii = []
        rot_link = ch.QuatFromAngleX(np.pi)  # link Z = body -z (R4)
        q_pose = self.pose.chrono_quat()
        q_link = q_pose * rot_link
        for i, (leg, body) in enumerate(zip(params.legs, legs, strict=True)):
            radius = leg.pad.swivel_center_above_pad_bottom_m
            centre_local = pad_sphere_centre_body_m(params, i, ext[i]) - leg_com_body_m(
                params, i, ext[i]
            )
            body.EnableCollision(True)
            body.AddCollisionShape(
                ch.ChCollisionShapeSphere(
                    pad_material_values(params, i, head_only_dashpot).make(), radius
                ),
                ch.ChFramed(chvec(centre_local), ch.QUNIT),
            )
            set_family(body, FAMILY_ROD, no_collision_with=(FAMILY_SUPERSTRUCTURE,))
            self.system.Add(body)
            attachment = np.asarray(leg.attachment_point_m, dtype=float)
            direction = np.asarray(params.actuator.extension_direction, dtype=float)
            frame_body = ch.ChFramed(chvec(self.pose.to_world(attachment)), q_link)
            frame_leg = ch.ChFramed(
                chvec(self.pose.to_world(attachment + ext[i] * direction)), q_link
            )
            motor = ch.ChLinkMotorLinearPosition()
            motor.SetName(f"motor_{leg.name}")
            motor.Initialize(body, sup, False, frame_leg, frame_body)
            function = make_motion_function(ext[i]) if actuator else ch.ChFunctionConst(ext[i])
            motor.SetMotionFunction(function)
            self.system.Add(motor)
            motors.append(motor)
            functions.append(function)
            centres_local.append(centre_local)
            radii.append(radius)
        self.legs: tuple[ch.ChBody, ...] = tuple(legs)
        self.motors: tuple[ch.ChLinkMotorLinearPosition, ...] = tuple(motors)
        self.motor_functions: tuple[ch.ChFunction, ...] = tuple(functions)
        self.sphere_centres_local_m = tuple(np.asarray(c) for c in centres_local)
        self.sphere_centres_local_ch = tuple(chvec(c) for c in centres_local)
        self.sphere_radii_m = tuple(radii)

        # ground bushing (L1 tangential model); with L1-R mechanics on, its normal force is the
        # rod-chamber machine's total normal force (Q-D2, chrono/rod_chamber_link); off: the
        # Chrono contact force, as before
        self.rod_chamber: L1RodChamber | None = None
        l1r_on = (
            mechanics_from_params(params, rod_side_mechanics)
            is RodSideMechanics.ONE_SIDED_PARALLEL
        )
        self.bushing = GroundBushingCoulomb.from_params(
            params,
            self.system,
            self.floor,
            legs,
            centres_local,
            dt_s=self.dt_s,
            force_point=bushing_force_point,
            leg_floors=None
            if not settle
            else [patch_bodies.get(name, self.floor) for name in LEG_ORDER],
            normal_force_source=self._bushing_normal_source if l1r_on else None,
        )
        if attach_bushings:
            self.bushing.attach()
        self.crawler_bushing: GroundBushingCoulomb | None = None
        self.crawler_bushing_values = None
        if crawler_bushings:
            if self.crawler_layout is None:
                raise ValueError("crawler_bushings needs crawler=True")
            self.crawler_bushing, self.crawler_normals, self.crawler_bushing_values = (
                make_crawler_bushing(
                    params, self.system, self.floor, sup, self.crawler_centres_local_m,
                    self.crawler_layout.sphere_radius_m, dt_s=self.dt_s,
                    kt_scale=crawler_bushing_kt_scale, normal_fn=self.bushing.normal_world,
                )
            )
            if attach_crawler_bushings is True:
                spheres = [int(i) for i in np.flatnonzero(self.crawler_layout.is_roller)]
            elif attach_crawler_bushings is False:
                spheres = []
            else:
                spheres = [int(i) for i in attach_crawler_bushings]
            if spheres:
                self.crawler_bushing.attach(spheres, hold_until_loaded=True)

        k_oil = params.get(K_OIL_KEY)
        self.k_oil_N_m = tuple(float(k_oil[name]) for name in LEG_ORDER)
        self._locked_s_ref_m = np.array(ext, dtype=float)  # locked legs: s_ref = extension
        self.actuator_hooks: list[StepHook] = []
        self.load_hooks: list[StepHook] = []
        self.record_hooks: list[RecordHook] = []
        self.actuator: L1SpeedActuator | None = None
        if actuator:
            self.actuator = L1SpeedActuator.from_params(
                params,
                self.motors,
                self.motor_functions,
                ext,
                ramp_s=actuator_ramp_s,
                force_saturation=force_saturation,
            )
            self.actuator_hooks.append(self.actuator.hook)
        # L1-R rod-side chamber (dynamics_model.md 5.12, chrono/rod_chamber_link): stepped in
        # after_step 2b every step (also with mechanics off: same-step sensor truth)
        self.rod_chamber = L1RodChamber(self, rod_side_mechanics)

    def _bushing_normal_source(self) -> list[float] | None:
        """Ground-bushing normal force with L1-R mechanics on (None: the contact force)."""
        return None if self.rod_chamber is None else self.rod_chamber.bushing_normal_force_N()

    # --- actuator state views ------------------------------------------------------------

    @property
    def s_ref_m(self) -> NDArray[np.float64]:
        """Motor target enforced during the step just taken (locked legs: the extensions).

        With the actuator this is :attr:`L1SpeedActuator.acting_s_ref_m` (the hook-set value
        acts one step later, ``chrono/actuators`` timing); Record ``s_ref``.
        """
        if self.actuator is None:
            return self._locked_s_ref_m.copy()
        return self.actuator.acting_s_ref_m

    @property
    def u_applied_m_s(self) -> NDArray[np.float64]:
        """Applied (saturated, rate-limited) speed behind :attr:`s_ref_m`; 0 when locked."""
        if self.actuator is None:
            return np.zeros(len(LEG_ORDER))
        return self.actuator.acting_u_m_s

    def set_command(self, leg_speed_m_s: Sequence[float] | NDArray[np.float64]) -> None:
        """Hold a leg speed command (m/s, LEG_ORDER); used by the next actuator hook.

        Raises:
            RuntimeError: The model was built without the actuator (legs locked).
        """
        if self.actuator is None:
            raise RuntimeError("model built without the actuator (actuator=False)")
        self.actuator.set_command(leg_speed_m_s)

    # --- geometry helpers --------------------------------------------------------------

    def leg_com_body_nominal_m(self, leg_index: int) -> NDArray[np.float64]:
        """Leg COG in body coordinates at the motor target that acted during the last step
        (constraint check, V13)."""
        target = self._locked_s_ref_m if self.actuator is None else self.actuator.acting_s_ref_m
        return leg_com_body_m(self.params, leg_index, float(target[leg_index]))

    @property
    def bodies(self) -> tuple[ch.ChBody, ...]:
        """Non-fixed bodies in snapshot order: superstructure, legs FL, FR, RL, RR."""
        return (self.superstructure, *self.legs)

    @property
    def body_names(self) -> tuple[str, ...]:
        return tuple(str(b.GetName()) for b in self.bodies)

    # --- stepping ------------------------------------------------------------------------

    def set_dt(self, dt_s: float) -> None:
        """Change the time step between two steps (S3 transition windows).

        Updates the model, the ground bushing (lift-off step count) and the pending actuator
        segment (:meth:`L1SpeedActuator.retime`; change ``dt`` while the applied speeds are
        constant, ``chrono/actuators`` module docstring). The integrator, solver and sparsity
        pattern do not depend on ``dt``.
        """
        dt = float(dt_s)
        if not (dt > 0.0 and np.isfinite(dt)):
            raise ValueError(f"dt must be positive: {dt_s!r}")
        if dt == self.dt_s:
            return
        self.dt_s = dt
        self.bushing.dt_s = dt
        if self.crawler_bushing is not None:
            self.crawler_bushing.dt_s = dt
        if self.actuator is not None:
            self.actuator.retime(float(self.system.GetChTime()), dt)

    def step(self, *, capture: bool = False) -> StepResult:
        """One ``DoStepDynamics(dt_s)`` followed by :meth:`after_step`.

        With the actuator, the actuator is told before the step whether it starts with a full
        Update (``not IsUpdated()``), the step time and ``dt_s`` (hook guard: raises
        :class:`~outrigger_sim.chrono.actuators.ActuatorHookMissedError` when a moving ramp
        segment was not set by the hook for this step, ``dynamics_model.md`` 5.6 ruling 1
        condition 1), and after it that the end-of-step Update read the current targets
        (``chrono/actuators`` timing).
        """
        act = self.actuator
        if act is not None:
            # hook guard: a moving ramp segment must have been set by the hook for this step
            act.on_step_start(
                not self.system.IsUpdated(), float(self.system.GetChTime()), self.dt_s
            )
        self.system.DoStepDynamics(self.dt_s)
        if act is not None:
            act.on_step_end()
        return self.after_step(self.dt_s, capture=capture)

    def after_step(self, dt_s: float, *, capture: bool = False) -> StepResult:
        """Post-step hooks in the fixed order of plan 3.1 / ``dynamics_model.md`` 4.6 ruling 2.

        1. **State copy** (``chrono/probes``, R9): when ``capture`` is true or a record hook
           is registered, the step-n state is read once and copied
           (:func:`~outrigger_sim.chrono.probes.read_probe`): bodies, motors, contact forces,
           and the ground-bushing anchors / contact flags that acted during step n. Later
           steps of this hook use this copy; the ground bushing reads the same post-step
           Chrono values itself (nothing changes the Chrono state between 1 and 2).
        2. **Ground bushing R15** (:meth:`GroundBushingCoulomb.after_step`): lift-off /
           re-touch, return mapping, damping switch. First, because the actuator guards and
           the record need the current contact state. With L1-R mechanics on its normal force
           is the rod-chamber machine's total ``N`` of the previous machine step (Q-D2).
        2b. **L1-R machine** (:meth:`L1RodChamber.step`, ``chrono/rod_chamber_link``): state
           machine, extra pad force and same-step sensor truth from ``t``, ``dt``, the acting
           applied speed, the pad deflection, ``GetMotorPos`` and ``GetMotorForce``. None of
           these is changed by 3, so this equals a call after the actuator hook, and the
           closed-loop callback at the head of 3 reads the output of this step.
        3. **Actuators** (:attr:`actuator_hooks`): cylinder force, per-step saturation,
           ``s_ref`` integration and motor-function update for the next step. S1: none
           (locked legs, ``s_ref`` = extension). S2b: :meth:`L1SpeedActuator.hook`.
        4. **External loads**: the L1-R extra pad force (:meth:`L1RodChamber.apply_force`,
           own accumulator per leg, emptied and set once; nothing with mechanics off), then
           :attr:`load_hooks`: empty the accumulator and add this step's value once (D2
           etc.). S1: none.
        5. **Record** (:attr:`record_hooks`): the step-n copy of 1, i.e. the state at
           ``t_n`` together with the inputs that acted during step n.

        Every input set in 2-4 acts from step n+1 (one-step lag, R15; record meta
        ``input_lag_steps: 1``), except right after a bushing is created or removed, when
        Chrono's full Update at the next step start uses it at once (``ground_bushing``).
        """
        rod = self.rod_chamber
        if rod is not None:
            rod.on_step_end()  # the step's end Update loaded the accumulator content
        probe = read_probe(self) if (capture or self.record_hooks) else None
        self.last_probe = probe
        events = self.bushing.after_step(dt_s)
        if self.crawler_bushing is not None:
            self.crawler_bushing.after_step(dt_s)
        if rod is not None:
            rod.step(dt_s)
        for hook in self.actuator_hooks:
            hook(self, dt_s)
        if rod is not None:
            rod.apply_force()
        for hook in self.load_hooks:
            hook(self, dt_s)
        if probe is not None:
            for record in self.record_hooks:
                record(self, probe)
        return StepResult(events, probe)

    def crawler_sphere_contacts(self) -> SphereContactReport:
        """Per-sphere crawler contact forces (layout order) of the last step."""
        return report_sphere_contacts(
            self.system, self.superstructure, self.crawler_centres_local_m
        )

    def probe(self) -> ProbeState:
        """Copy of the current state (between steps: anchors are those set for the next
        step if the hook already ran)."""
        return read_probe(self)

    def truth(self, probe: ProbeState) -> TruthState:
        """:class:`TruthState` of a probe copy (``stroke_true_m`` = motor - F_cyl / k_oil).

        With L1-R mechanics on and the machine output of the probe's step available,
        ``stroke_true_m`` and ``F_contact_n_N`` are the machine's ``stroke_true_m`` and total
        ``normal_force_N`` of that step (Q-D2, Q-D4); mechanics off: unchanged.
        """
        state = truth_state(
            probe, s_ref_m=self.s_ref_m, u_applied_m_s=self.u_applied_m_s, k_oil_N_m=self.k_oil_N_m
        )
        rod = self.rod_chamber
        if rod is None or not rod.enabled:
            return state
        out = rod.output_at(probe.t_s)
        if out is None:
            return state
        return dataclasses.replace(
            state,
            stroke_true_m=np.array(out.stroke_true_m, dtype=float),
            F_contact_n_N=np.array(out.normal_force_N, dtype=float),
        )

    # --- snapshot (R16) ------------------------------------------------------------------

    def snapshot(self, held_command: Command | None = None) -> Snapshot:
        """R16 snapshot: bodies, motors, ``s_ref``, ground-bushing state, time, Params.sha256.

        With the actuator, ``actuator.s_ref_m`` is the integrated reference (post-hook) and
        the ``l1_actuator.*`` part carries the limiter and lag state; the held command
        defaults to the actuator's command.
        """
        t_now = float(self.system.GetChTime())
        if held_command is None:
            speeds = (
                np.zeros(len(LEG_ORDER)) if self.actuator is None else self.actuator.command_m_s
            )
            held_command = Command(t_s=t_now, leg_speed_m_s=speeds)
        parts: dict[str, Any] = {GROUND_BUSHING_PART: self.bushing}
        if self.settlement is not None:
            parts[SETTLEMENT_PART] = self.settlement
        if self.crawler_bushing is not None:
            parts[CRAWLER_BUSHING_PART] = self.crawler_bushing
        s_ref = self._locked_s_ref_m
        if self.actuator is not None:
            parts[ACTUATOR_PART] = _ActuatorPart(self.actuator, self.system)
            s_ref = self.actuator.s_ref_m
        if self.rod_chamber is not None:
            parts[ROD_CHAMBER_PART] = self.rod_chamber
        return capture_snapshot(
            self.system,
            engine=engine_info(ChronoModel.L1.value),
            params_sha256=self.params.sha256,
            held_command=held_command,
            bodies=self.bodies,
            motors=self.motors,
            s_ref_m=s_ref,
            parts=parts,
        )

    def restore(self, snapshot: Snapshot) -> float:
        """Restore a snapshot of the same model (built with ``attach_bushings=False`` or not;
        existing bushings are replaced). Returns the restored time [s].

        Locked model: the snapshot ``s_ref`` must equal the locked extensions. Actuator
        model: a snapshot with actuator state continues exactly (held command included); one
        without it (S1 / S2a locked-leg states) starts the actuator at rest at the snapshot
        ``s_ref`` with a zero command.

        Raises:
            SnapshotMismatchError / ValueError: see :func:`restore_snapshot`.
        """
        parts: dict[str, Any] = {GROUND_BUSHING_PART: self.bushing}
        act = self.actuator
        has_actuator_state = any(k.startswith(f"{ACTUATOR_PART}.") for k in snapshot.payload)
        if self.settlement is not None and any(
            k.startswith(f"{SETTLEMENT_PART}.") for k in snapshot.payload
        ):
            parts[SETTLEMENT_PART] = self.settlement
        if self.crawler_bushing is not None and any(
            k.startswith(f"{CRAWLER_BUSHING_PART}.") for k in snapshot.payload
        ):
            parts[CRAWLER_BUSHING_PART] = self.crawler_bushing
        if act is not None:
            if has_actuator_state:
                parts[ACTUATOR_PART] = act
            elif S_REF_KEY in snapshot.payload:
                act.reset_to(snapshot.payload[S_REF_KEY])  # targets before the restore Update
        rod = self.rod_chamber
        if rod is not None:
            if any(k.startswith(f"{ROD_CHAMBER_PART}.") for k in snapshot.payload):
                parts[ROD_CHAMBER_PART] = rod
            else:
                # older snapshot (Q-D6): module default "locked after an extension at the
                # current force and deflection" on the next standstill step; meta flag
                rod.restore_default()
        restored = restore_snapshot(
            snapshot,
            self.system,
            engine=engine_info(ChronoModel.L1.value),
            params_sha256=self.params.sha256,
            bodies=self.bodies,
            motors=self.motors,
            parts=parts,
        )
        if self.settlement is not None:
            self.settlement.sync()
        if act is None:
            if restored.s_ref_m is not None and not np.array_equal(
                restored.s_ref_m, self._locked_s_ref_m
            ):
                raise ValueError(
                    f"snapshot s_ref {restored.s_ref_m} differs from the locked extensions "
                    f"{self._locked_s_ref_m} of this locked-leg model"
                )
        else:
            act.set_command(restored.held_command.leg_speed_m_s)
            # the snapshot was captured after the hook of its step (R16); a model built with
            # another dt re-integrates the pending segment for its own step length
            act.mark_hooked(restored.time_s, self.dt_s)
            if has_actuator_state and act.is_moving_segment:
                act.retime_if_needed(restored.time_s, self.dt_s)
        return restored.time_s

    # --- metadata and V0 inventory -----------------------------------------------------------

    def meta(self) -> dict[str, Any]:
        """Engine meta for ``record.make_run_meta`` (JSON-ready)."""
        meta = self.bundle.meta()
        meta.update(
            engine_version=engine_info(ChronoModel.L1.value).version,
            auger_level=self.params.level.value,
            extensions_m=list(self.extensions_m),
            initial_pose={
                "origin_m": list(self.pose.origin_m),
                "quat_wxyz": list(self.pose.quat_wxyz),
            },
            crawler_spheres=0 if self.crawler_layout is None else self.crawler_layout.n_points,
            floor_patches=[p.name for p in self.patches],
            collision_families={
                "floor": FAMILY_FLOOR,
                "superstructure": FAMILY_SUPERSTRUCTURE,
                "rod": FAMILY_ROD,
                "disabled_pairs": ["rod-superstructure (incl. crawler)"],
            },
            floor_pose=None
            if self.floor_pose is None
            else {
                "origin_m": list(self.floor_pose.origin_m),
                "quat_wxyz": list(self.floor_pose.quat_wxyz),
            },
            leg_lock="ChLinkMotorLinearPosition, ChFunctionConst(extension), guide PRISMATIC"
            if self.actuator is None
            else (
                "ChLinkMotorLinearPosition, guide PRISMATIC, ChFunctionRamp s(t_n) + u (t - t_n) "
                "from L1SpeedActuator (saturation, stroke-end braking, rate limit, s_ref "
                "integration in the actuator hook)"
            ),
            actuator=None
            if self.actuator is None
            else {
                "class": "L1SpeedActuator",
                "max_speed_m_s": self.actuator.max_speed_m_s,
                "ramp_s": self.actuator.ramp_s,
                "ramp_source": (
                    "YAML actuator.command_ramp_s (ASSUMPTION, user decision 2026-10-20)"
                    if self.actuator.ramp_s == self.params.actuator.command_ramp_s
                    else "override (constructor actuator_ramp_s)"
                ),
                "accel_limit_m_s2": None
                if self.actuator.ramp_s == 0.0
                else self.actuator.accel_limit_m_s2,
                "stroke_range_m": self.actuator.stroke_range_m.tolist(),
                "force_saturation_N": None
                if self.actuator.force_limits_N is None
                else {
                    "extend": self.actuator.force_limits_N[0],
                    "retract": self.actuator.force_limits_N[1],
                    "rule": "every step in the actuator hook: F_cyl >= extend and u > 0 -> u = 0; "
                    "F_cyl <= -retract and u < 0 -> u = 0 (YAML actuator.max_force_*_N, 210 bar)",
                },
            },
            ground_bushing_force_point=self.bushing.force_point,
            ground_settlement=None if self.settlement is None else self.settlement.meta(),
            crawler_bushings=None
            if self.crawler_bushing_values is None
            else self.crawler_bushing_values.meta(),
            rod_chamber=None if self.rod_chamber is None else self.rod_chamber.meta(),
            input_lag_steps=1,
        )
        return meta

    def v0_inventory(self) -> dict[str, Any]:
        """Values as Chrono holds them, for the V0 comparison with the YAML.

        Call before the first step (the body COG is compared with the build pose). Runs one
        ``system.Update()`` so that the motor positions are evaluated (a fresh system is
        flagged "not updated", so the first step runs a full Update anyway; this call does
        not change the trajectory).
        """
        self.system.Update()
        rot = self.pose.rotation
        origin = np.asarray(self.pose.origin_m, dtype=float)

        def body_entry(body: ch.ChBody) -> dict[str, Any]:
            props = read_mass_properties(body)
            return {
                "name": str(body.GetName()),
                "mass_kg": props.mass_kg,
                "com_body_m": (rot.T @ (props.com_world_m - origin)).tolist(),
                "inertia_kg_m2": props.inertia_kg_m2.tolist(),
                "collision": shape_materials(body) if body.GetCollisionModel() else [],
                "family": int(body.GetCollisionModel().GetFamily())
                if body.GetCollisionModel()
                else None,
            }

        floor_model = self.floor.GetCollisionModel()
        bushings = []
        for leg in self.bushing._legs:  # noqa: SLF001 - read the Chrono inputs directly
            if leg.bushing is None:
                bushings.append(None)
                continue
            k = leg.bushing.GetStiffness()
            c = leg.bushing.GetDamping()
            bushings.append(
                {"stiffness_N_m": [k.x, k.y, k.z], "damping_input_N_s_m": [c.x, c.y, c.z]}
            )
        g = self.system.GetGravitationalAcceleration()
        sup_model = self.superstructure.GetCollisionModel()
        rod_models = [leg.GetCollisionModel() for leg in self.legs]
        floor_shapes = shape_materials(self.floor)
        collision_type = self.system.GetCollisionSystem().GetType()
        return {
            "extensions_m": list(self.extensions_m),
            "rod_side_mechanics": None
            if self.rod_chamber is None
            else str(self.rod_chamber.mechanics),
            "head_only_dashpot": self.head_only_dashpot,
            "gravity_m_s2": [g.x, g.y, g.z],
            "collision_system_name": "BULLET"
            if collision_type == ch.ChCollisionSystem.Type_BULLET
            else str(collision_type),
            "floor": {
                "mass_kg": float(self.floor.GetMass()),
                "fixed": bool(self.floor.IsFixed()),
                "family": int(floor_model.GetFamily()),
                "patches": [p.name for p in self.patches],
                "collision_named": [
                    {"name": patch.name, **shape}
                    for patch, shape in zip(self.floor_body_patches, floor_shapes, strict=True)
                ],
            },
            "superstructure": body_entry(self.superstructure),
            "legs": [body_entry(b) for b in self.legs],
            "motor_pos_m": [float(m.GetMotorPos()) for m in self.motors],
            # guide PRISMATIC (Chrono default) + motor = 6 bilateral constraints per link
            "motor_constraints": [int(m.GetNumConstraintsBilateral()) for m in self.motors],
            "bushings": bushings,
            "collides": {
                "rod_with_superstructure": [
                    bool(m.CollidesWith(FAMILY_SUPERSTRUCTURE)) for m in rod_models
                ],
                "rod_with_floor": [bool(m.CollidesWith(FAMILY_FLOOR)) for m in rod_models],
                "superstructure_with_rod": bool(sup_model.CollidesWith(FAMILY_ROD))
                if sup_model
                else None,
                "superstructure_with_floor": bool(sup_model.CollidesWith(FAMILY_FLOOR))
                if sup_model
                else None,
            },
            "crawler_layout": None
            if self.crawler_layout is None
            else {
                "n_points": self.crawler_layout.n_points,
                "n_roller": int(self.crawler_layout.is_roller.sum()),
                "centres_body_m": self.crawler_layout.centres_body_m(self.floor_z_m).tolist(),
            },
        }


# --- static settle run (S1) --------------------------------------------------------------


@dataclass
class SettleRun:
    """Result of :func:`run_settle`."""

    stats: StillWindowStats
    events: list[BushingEvent]
    steps: int
    wall_s: float
    t_s: list[float]
    """Sample times (coarse before the window, fine inside)."""
    pad_normal_N: list[NDArray[np.float64]]
    roll_pitch_deg: list[tuple[float, float]]
    end_probe: ProbeState
    end_contacts: ContactReport


def run_settle(
    model: L1Model,
    settle_s: float,
    still_s: float,
    *,
    coarse_sample_s: float = 1.0e-2,
    fine_sample_s: float = 1.0e-3,
    on_sample: Callable[[ProbeState], None] | None = None,
) -> SettleRun:
    """Step ``settle_s + still_s`` from the current state and collect the still-window stats.

    Samples (state copies, R9) every ``coarse_sample_s`` during the settle and every
    ``fine_sample_s`` in the still window; ``on_sample`` receives each copy (e.g. to
    append to a Recorder). No sample at the start: Chrono computes contact forces inside a
    step, so before the first step they read 0. In the still window the contacts are counted
    per body with ``ReportContactCallback`` (V13 "one contact per leg").
    """
    dt = model.dt_s
    n_settle = round(settle_s / dt)
    n_still = round(still_s / dt)
    coarse = max(1, round(coarse_sample_s / dt))
    fine = max(1, round(fine_sample_s / dt))
    names = model.body_names
    window: dict[str, list[Any]] = {
        k: [] for k in ("t", "N", "Fcyl", "pen", "roll", "pitch", "off", "nc", "cb")
    }
    t_list: list[float] = []
    n_list: list[NDArray[np.float64]] = []
    rp_list: list[tuple[float, float]] = []

    def sample(probe: ProbeState, in_window: bool) -> None:
        if on_sample is not None:
            on_sample(probe)
        roll, pitch = roll_pitch_from_quat(probe.body_quat_wxyz)
        roll_deg, pitch_deg = float(np.degrees(roll)), float(np.degrees(pitch))
        t_list.append(probe.t_s)
        n_list.append(probe.pad_normal_force_N)
        rp_list.append((roll_deg, pitch_deg))
        if in_window:
            report = report_contacts(model.system, names)
            window["t"].append(probe.t_s)
            window["N"].append(probe.pad_normal_force_N)
            window["Fcyl"].append(probe.motor_force_N)
            window["pen"].append(probe.penetration_m * 1e3)
            window["roll"].append(roll_deg)
            window["pitch"].append(pitch_deg)
            window["off"].append(float(np.abs(probe.leg_offset_in_body_m).max()))
            window["nc"].append(probe.n_contacts)
            window["cb"].append(report.count[1:].copy())

    events: list[BushingEvent] = []
    t0 = time.perf_counter()
    for k in range(1, n_settle + n_still + 1):
        in_window = k > n_settle
        result = model.step(capture=(k % (fine if in_window else coarse) == 0))
        events.extend(result.events)
        if result.probe is not None:
            sample(result.probe, in_window)
    wall = time.perf_counter() - t0
    w = {k: np.asarray(v) for k, v in window.items()}
    if w["t"].size == 0:
        raise ValueError("still window has no samples")
    stats = StillWindowStats(
        t_start_s=float(w["t"][0]),
        t_end_s=float(w["t"][-1]),
        n_samples=int(w["t"].size),
        contact_force_mean_N=w["N"].mean(axis=0),
        contact_force_span_N=np.ptp(w["N"], axis=0),
        cylinder_force_mean_N=w["Fcyl"].mean(axis=0),
        penetration_mean_mm=w["pen"].mean(axis=0),
        roll_mean_deg=float(w["roll"].mean()),
        pitch_mean_deg=float(w["pitch"].mean()),
        roll_span_deg=float(np.ptp(w["roll"])),
        pitch_span_deg=float(np.ptp(w["pitch"])),
        motor_violation_max_m=float(w["off"].max()),
        contacts_per_leg_min=w["cb"].min(axis=0),
        contacts_per_leg_max=w["cb"].max(axis=0),
        system_contacts_range=(int(w["nc"].min()), int(w["nc"].max())),
        any_nan=bool(
            any(not np.all(np.isfinite(w[k])) for k in ("N", "Fcyl", "pen", "roll", "pitch"))
        ),
    )
    return SettleRun(
        stats=stats,
        events=events,
        steps=n_settle + n_still,
        wall_s=wall,
        t_s=t_list,
        pad_normal_N=n_list,
        roll_pitch_deg=rp_list,
        end_probe=model.probe(),
        end_contacts=report_contacts(model.system, names),
    )
