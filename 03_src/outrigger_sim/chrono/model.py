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
  created now (t = 0) with zero tangential force (plan section 2 rule 1).

Hook order after every step: see :meth:`L1Model.after_step`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

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
    add_floor_patches,
    crawler_layout,
    crawler_material_values,
    floor_patches,
    pad_material_values,
    report_contacts,
    set_family,
    shape_materials,
)
from outrigger_sim.chrono.ground_bushing import (
    DEFAULT_FORCE_POINT,
    BushingEvent,
    GroundBushingCoulomb,
)
from outrigger_sim.chrono.probes import ProbeState, chvec, read_probe, truth_state
from outrigger_sim.chrono.snapshot import capture_snapshot, engine_info, restore_snapshot
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
    ) -> None:
        self.params = params
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
        self.patches = floor_patches(params, self.crawler_layout)
        add_floor_patches(self.floor, self.patches, self.floor_z_m)

        # superstructure (+ crawler spheres)
        sup = make_superstructure(params, self.pose)
        com_body = np.asarray(params.superstructure.mass_properties.com_m, dtype=float)
        if self.crawler_layout is not None:
            sup.EnableCollision(True)
            material = crawler_material_values(params).make()
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
                ch.ChCollisionShapeSphere(pad_material_values(params, i).make(), radius),
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
            motor.SetMotionFunction(ch.ChFunctionConst(ext[i]))
            self.system.Add(motor)
            motors.append(motor)
            centres_local.append(centre_local)
            radii.append(radius)
        self.legs: tuple[ch.ChBody, ...] = tuple(legs)
        self.motors: tuple[ch.ChLinkMotorLinearPosition, ...] = tuple(motors)
        self.sphere_centres_local_m = tuple(np.asarray(c) for c in centres_local)
        self.sphere_centres_local_ch = tuple(chvec(c) for c in centres_local)
        self.sphere_radii_m = tuple(radii)

        # ground bushing (L1 tangential model)
        self.bushing = GroundBushingCoulomb.from_params(
            params,
            self.system,
            self.floor,
            legs,
            centres_local,
            dt_s=self.dt_s,
            force_point=bushing_force_point,
        )
        if attach_bushings:
            self.bushing.attach()

        k_oil = params.get(K_OIL_KEY)
        self.k_oil_N_m = tuple(float(k_oil[name]) for name in LEG_ORDER)
        self.s_ref_m = np.array(ext, dtype=float)  # locked L1 actuator: s_ref = extension
        self.u_applied_m_s = np.zeros(len(LEG_ORDER))
        self.actuator_hooks: list[StepHook] = []
        self.load_hooks: list[StepHook] = []
        self.record_hooks: list[RecordHook] = []

    # --- geometry helpers --------------------------------------------------------------

    def leg_com_body_nominal_m(self, leg_index: int) -> NDArray[np.float64]:
        """Leg COG in body coordinates at the motor's set extension (constraint check)."""
        return leg_com_body_m(self.params, leg_index, float(self.s_ref_m[leg_index]))

    @property
    def bodies(self) -> tuple[ch.ChBody, ...]:
        """Non-fixed bodies in snapshot order: superstructure, legs FL, FR, RL, RR."""
        return (self.superstructure, *self.legs)

    @property
    def body_names(self) -> tuple[str, ...]:
        return tuple(str(b.GetName()) for b in self.bodies)

    # --- stepping ------------------------------------------------------------------------

    def step(self, *, capture: bool = False) -> StepResult:
        """One ``DoStepDynamics(dt_s)`` followed by :meth:`after_step`."""
        self.system.DoStepDynamics(self.dt_s)
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
           the record need the current contact state.
        3. **Actuators** (:attr:`actuator_hooks`): cylinder force, per-step saturation,
           ``s_ref`` integration and motor-function update for the next step. S1: none
           (locked legs, ``s_ref`` = extension).
        4. **External loads** (:attr:`load_hooks`): empty the accumulator and add this step's
           value once (D2 etc.). S1: none.
        5. **Record** (:attr:`record_hooks`): the step-n copy of 1, i.e. the state at
           ``t_n`` together with the inputs that acted during step n.

        Every input set in 2-4 acts from step n+1 (one-step lag, R15; record meta
        ``input_lag_steps: 1``), except right after a bushing is created or removed, when
        Chrono's full Update at the next step start uses it at once (``ground_bushing``).
        """
        probe = read_probe(self) if (capture or self.record_hooks) else None
        events = self.bushing.after_step(dt_s)
        for hook in self.actuator_hooks:
            hook(self, dt_s)
        for hook in self.load_hooks:
            hook(self, dt_s)
        if probe is not None:
            for record in self.record_hooks:
                record(self, probe)
        return StepResult(events, probe)

    def probe(self) -> ProbeState:
        """Copy of the current state (between steps: anchors are those set for the next
        step if the hook already ran)."""
        return read_probe(self)

    def truth(self, probe: ProbeState) -> TruthState:
        """:class:`TruthState` of a probe copy (``stroke_true_m`` = motor - F_cyl / k_oil)."""
        return truth_state(
            probe, s_ref_m=self.s_ref_m, u_applied_m_s=self.u_applied_m_s, k_oil_N_m=self.k_oil_N_m
        )

    # --- snapshot (R16) ------------------------------------------------------------------

    def snapshot(self, held_command: Command | None = None) -> Snapshot:
        """R16 snapshot: bodies, motors, ``s_ref``, ground-bushing state, time, Params.sha256."""
        command = held_command or Command(
            t_s=float(self.system.GetChTime()), leg_speed_m_s=np.zeros(len(LEG_ORDER))
        )
        return capture_snapshot(
            self.system,
            engine=engine_info(ChronoModel.L1.value),
            params_sha256=self.params.sha256,
            held_command=command,
            bodies=self.bodies,
            motors=self.motors,
            s_ref_m=self.s_ref_m,
            parts={GROUND_BUSHING_PART: self.bushing},
        )

    def restore(self, snapshot: Snapshot) -> float:
        """Restore a snapshot of the same model (built with ``attach_bushings=False`` or not;
        existing bushings are replaced). Returns the restored time [s].

        Raises:
            SnapshotMismatchError / ValueError: see :func:`restore_snapshot`.
        """
        restored = restore_snapshot(
            snapshot,
            self.system,
            engine=engine_info(ChronoModel.L1.value),
            params_sha256=self.params.sha256,
            bodies=self.bodies,
            motors=self.motors,
            parts={GROUND_BUSHING_PART: self.bushing},
        )
        if restored.s_ref_m is not None and not np.array_equal(restored.s_ref_m, self.s_ref_m):
            raise ValueError(
                f"snapshot s_ref {restored.s_ref_m} differs from the locked extensions "
                f"{self.s_ref_m} of this S1 model"
            )
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
            leg_lock="ChLinkMotorLinearPosition, ChFunctionConst(extension), guide PRISMATIC",
            ground_bushing_force_point=self.bushing.force_point,
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
                    for patch, shape in zip(self.patches, floor_shapes, strict=True)
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
