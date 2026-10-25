"""L2b-NSC Chrono model: superstructure + four force-law legs + lateral bushings + NSC contact.

``00_docs/03_chrono/chrono_build_plan.md`` S7; ``dynamics_model.md`` 2.3 (L2b-NSC row), 4.2, rev. 33
5.20. Same bodies, pose convention, crawler layout D and hook order as
:class:`outrigger_sim.chrono.model.L1Model`; what differs:

* ``ChSystemNSC`` from ``make_system(params, "L2b_NSC")`` (PSOR 50, R1 gravity, R2 Bullet) with
  the default floor plate (NSC, ``mu = contact.rigid_floor.L2b_NSC.friction``); the floor body
  can be tilted (``floor_pose``, V12 / V14). Bodies are built right after ``make_system``
  (``ChSystemNSC()`` sets the process-wide collision envelope, 5.20.9).
* Pads: one NSC sphere per leg (radius = swivel-centre height, at the swivel centre, ``mu``
  = the floor value); crawler: the 24 spheres of layout D on the superstructure, NSC ``mu =
  contact.crawler.friction`` (rigid crawler, no damping). Collision families as L1 (R14).
* Legs: ``ChLinkMotorLinearForce`` (link Z = body -z, R4; guide x, y free) driven by
  :class:`~outrigger_sim.chrono.l2b_actuator.L2bForceActuator` (explicit force law with the
  rev. 33 dashpots and the rod-side law), lateral leg compliance =
  :class:`~outrigger_sim.chrono.lateral_bushing.LateralBushings` at the ball centre.
* No ground bushing: the tangential pad load is NSC friction (stick exact).

Starts (``start``):

* ``"static"``: pads just touching at ``extensions_m`` (default the L1 operating extensions,
  level body at the zero pose, rigid contact). The cylinder forces are the planar-compatible
  static solution of the superstructure weight on the four axial springs ``k_ax(e_i)``
  (:func:`static_cylinder_forces_N`; rod weights go straight to the floor), ``s_ref = e +
  F / k_ax``, the first step's force = ``F``. This is the rev. 33 V1-V3 rule (5.20.4: place the
  analytic static solution and lock there, ``dc = 0``).
* ``"hanging"``: legs in the air (e.g. on the crawler with legs retracted, or superstructure
  fixed for V11): each rod hangs on its spring, ``F = -m_rod g_axis``.
* an explicit force array.

Step order (``dynamics_model.md`` 4.6 ruling 2, as L1): hook guards -> ``DoStepDynamics`` ->
``on_step_end`` -> state copy (``capture`` / record hooks) -> lateral-bushing hook ->
:attr:`L2bModel.actuator_hooks` (closed-loop callback first when an engine is attached, then
the force-law hook) -> :attr:`L2bModel.load_hooks` -> record hooks. Every hook value acts in
the next step (explicit, ``input_lag_steps`` 1).

Pad normal force (plan S7 risk 5): ``ChBody.GetContactForce()`` of each rod (NSC contact
container ``ComputeContactForces`` / ``GetContactableForce``, ``ChContactContainerNSC.cpp:176,
182``) is the state copy's ``pad_contact_world_N``; :func:`pad_force_crosscheck` compares it with
``ReportAllContacts`` per rod, with the rod's axial balance (``F + m g`` along the floor normal
at rest) and with the total weight (V1 cross-check path).

Units SI, world Z-up; per-leg arrays in LEG_ORDER.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

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
    CrawlerSphereLayout,
    crawler_layout,
    report_contacts,
    report_sphere_contacts,
    set_family,
    shape_materials,
)
from outrigger_sim.chrono.l2b_actuator import L2bForceActuator, make_force_motor
from outrigger_sim.chrono.lateral_bushing import LateralBushings, lateral_bushing_values
from outrigger_sim.chrono.model import operating_extensions_m, zero_pose
from outrigger_sim.chrono.probes import ProbeState, chvec, truth_state
from outrigger_sim.chrono.snapshot import capture_snapshot, engine_info, restore_snapshot
from outrigger_sim.chrono.system import (
    ChronoModel,
    StepPurpose,
    floor_material_values,
    gravity_vector,
    make_nsc_material,
    make_system,
)
from outrigger_sim.engine import Snapshot
from outrigger_sim.geometry import leg_com_body_m, pad_sphere_centre_body_m
from outrigger_sim.params import LEG_ORDER, Params, axial_stiffness_N_m
from outrigger_sim.signals import Command, TruthState

ACTUATOR_PART = "l2b_actuator"
BUSHING_PART = "lateral_bushing"

StepHook = Callable[["L2bModel", float], None]
RecordHook = Callable[["L2bModel", ProbeState], None]


# --- static start -------------------------------------------------------------------------


def axial_stiffness_at_N_m(params: Params, extensions_m: Sequence[float]) -> NDArray[np.float64]:
    """``k_ax(e_i)`` per leg (force-law spring incl. the concrete) [N/m]."""
    a = params.l2b.actuator
    return np.array(
        [
            axial_stiffness_N_m(
                float(extensions_m[i]),
                bulk_modulus_Pa=a.oil_bulk_modulus_eff_Pa,
                head_area_m2=a.head_area_m2[i],
                dead_length_m=a.oil_dead_length_m,
                k_rod_N_m=a.k_rod_N_m[i],
                k_frame_N_m=a.frame_stiffness_N_m,
                k_concrete_N_m=a.k_concrete_N_m,
            )
            for i in range(len(LEG_ORDER))
        ]
    )


def static_cylinder_forces_N(params: Params, k_N_m: ArrayLike) -> NDArray[np.float64]:
    """Planar-compatible static cylinder forces of the level superstructure on the four axial
    springs (``A = [1, y_i, -x_i]`` at the leg axes, ``A^T K A q = [W, W y_c, -W x_c]``,
    ``F = K A q``; rod weights act on the floor directly). [N], + = pushes the pad down."""
    g = params.meta.gravity_m_s2
    props = params.superstructure.mass_properties
    xy = np.array([leg.attachment_point_m[:2] for leg in params.legs], dtype=float)
    k = np.asarray(k_N_m, dtype=float)
    a = np.column_stack([np.ones(len(k)), xy[:, 1], -xy[:, 0]])
    w = props.mass_kg * g
    load = np.array([w, w * props.com_m[1], -w * props.com_m[0]])
    q = np.linalg.solve(a.T @ (k[:, None] * a), load)
    return k * (a @ q)


def touching_pose(
    params: Params, link_extensions_m: Sequence[float], *, tol_m: float = 1.0e-12
) -> BodyPose:
    """Body pose (height, roll, pitch; yaw 0) where the four pad spheres at the given link
    extensions touch the level floor ``ground.crawler_bottom_z_m`` (Gauss-Newton least
    squares). With planar-compatible compressions (:func:`static_cylinder_forces_N`) the four
    conditions are consistent; the residual is checked against 1e-9 m."""
    from outrigger_sim.frames import quat_from_euler_zyx, quat_to_matrix

    floor = float(params.ground.crawler_bottom_z_m)
    radii = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    centres = np.array([pad_sphere_centre_body_m(params, i, float(link_extensions_m[i]))
                        for i in range(len(params.legs))])
    q = np.array([float(np.mean(floor + radii - centres[:, 2])), 0.0, 0.0])  # z, roll, pitch

    def residual(x):
        rot = quat_to_matrix(quat_from_euler_zyx(0.0, x[2], x[1]))
        return (centres @ rot.T)[:, 2] + x[0] - floor - radii

    for _ in range(20):
        r = residual(q)
        jac = np.empty((len(r), 3))
        for j in range(3):
            dq = np.zeros(3)
            dq[j] = 1.0e-7
            jac[:, j] = (residual(q + dq) - r) / 1.0e-7
        step = np.linalg.lstsq(jac, -r, rcond=None)[0]
        q = q + step
        if np.abs(step).max() < tol_m:
            break
    if np.abs(residual(q)).max() > 1.0e-9:
        raise ValueError(f"pads cannot all touch: residual {residual(q)}")
    quat = quat_from_euler_zyx(0.0, q[2], q[1])
    return BodyPose((0.0, 0.0, float(q[0])), tuple(float(c) for c in quat))


# --- state copy ---------------------------------------------------------------------------


def _v(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


def read_l2b_probe(model: L2bModel) -> ProbeState:
    """State copy of an :class:`L2bModel` in the L1 :class:`ProbeState` layout.

    ``motor_force_N`` = force-law value that acted in the step (cylinder force);
    ``bushing_force_world_N`` = the pad contact force (its tangential part is the NSC friction,
    ``truth_state`` takes it); ``bushing_anchor_world_m`` NaN (no ground bushing);
    ``leg_offset_in_body_m`` = rod COG minus its axis position at the actual motor position
    (lateral bushing deflection, guide x, y free)."""
    sup = model.superstructure
    origin_local = model.origin_in_cog_frame_ch
    origin = sup.TransformPointLocalToParent(origin_local)
    vel = sup.PointSpeedLocalToParent(origin_local)
    q = sup.GetRot()
    legs = model.legs
    motor_pos = np.array([m.GetMotorPos() for m in model.motors], dtype=float)
    centres = np.array(
        [_v(leg.TransformPointLocalToParent(c))
         for leg, c in zip(legs, model.sphere_centres_local_ch, strict=True)]
    )
    offsets = np.empty((len(legs), 3))
    for i, leg in enumerate(legs):
        local = _v(sup.TransformPointParentToLocal(leg.GetPos())) + model.sup_com_body_m
        offsets[i] = local - leg_com_body_m(model.params, i, float(motor_pos[i]))
    contact = np.array([_v(leg.GetContactForce()) for leg in legs])
    normal = model.floor_normal_world()
    return ProbeState(
        t_s=float(model.system.GetChTime()),
        body_pos_m=_v(origin),
        body_quat_wxyz=np.array([q.e0, q.e1, q.e2, q.e3], dtype=float),
        body_vel_m_s=_v(vel),
        body_omega_rad_s=_v(sup.GetAngVelParent()),
        cog_pos_m=_v(sup.GetPos()),
        motor_pos_m=motor_pos,
        motor_force_N=model.actuator.acting_force_N,
        pad_contact_world_N=contact,
        pad_sphere_centre_world_m=centres,
        pad_sphere_radius_m=np.array(model.sphere_radii_m, dtype=float),
        leg_offset_in_body_m=offsets,
        crawler_contact_world_N=_v(sup.GetContactForce()),
        floor_normal_world=normal,
        floor_point_world_m=np.array(model.floor_point_world_m, dtype=float),
        bushing_in_contact=(contact @ normal) > 0.0,
        bushing_anchor_world_m=np.full((len(legs), 3), np.nan),
        bushing_force_world_N=contact,
        n_contacts=int(model.system.GetNumContacts()),
    )


@dataclass(frozen=True)
class L2bStepResult:
    probe: ProbeState | None


CRAWLER_CHECK_PASSED = False
"""S8-L4 check of the compliant NSC crawler (U-S8-L3 option 1) on 2026-10-24: FAILED. In pychrono
10.0.0 NSC ``SetCompliance`` does not act as a contact spring (PSOR, APGD and BB): a body on
compliant spheres sinks at a steady speed of about ``compliance F / h`` and falls through the floor
at 1.2e-7 m/N (z -9 m after 3 s). Results on the L2b crawler stay "rigid crawler upper bound"
(S8-L5)."""

CRAWLER_CHECK_NOTE = ("S8-L4 failed 2026-10-24: NSC compliance creeps (no restoring spring) in "
                      "pychrono 10.0.0; crawler contact stays rigid NSC, S8-L5 tag applies")


class L2bModel:
    """L2b-NSC four-leg model (module docstring).

    Args:
        params: Loaded with ``model="L2b_NSC"`` (auger level = ``params.level``).
        pose: Body pose at t = 0; default the zero pose of ``extensions_m`` (pads touching).
        extensions_m: Leg extensions (link displacements) at t = 0; default the L1 operating
            extensions.
        start: ``"static"``, ``"hanging"`` or a per-leg start force [N] (module docstring).
        crawler: Add the 24 crawler spheres.
        dt_s, purpose: Time step (default ``simulation.L2b_NSC.dt_s``).
        floor_pose: Pose of the fixed floor body (tilted floor); the world point
            ``(0, 0, ground.crawler_bottom_z_m)`` must stay on its surface.
        damping: ``"rev33"`` (default) or ``"yaml_pre_rev33"`` (``L2bForceActuator.from_params``).
        rod_side: Rod-side law on/off (None = ``params.l2b.rod_side.mechanics``).
        rod_side_armed: Start with the rod-side law armed (False: arm later, V12 rule).
        force_saturation: Per-leg 210 bar limits (law C).
        actuator_ramp_s: Command ramp override.
        lateral_damping_scale: Factor on the lateral bushing dashpot (V8(a): 0).
        crawler_contact: ``"rigid"`` (S7), ``"compliant"`` (U-S8-L3 option 1: NSC
            ``SetCompliance`` / ``SetDampingF`` of ``contact.crawler.L2b_NSC`` on the crawler
            spheres, ``SetDampingF`` also on the floor material because NSC combines dampingf by
            min; the pads keep compliance 0, so their contacts are unchanged) or None = the YAML
            ``contact.crawler.L2b_NSC.model`` (rigid when the block is absent).
    """

    def __init__(
        self,
        params: Params,
        *,
        pose: BodyPose | None = None,
        extensions_m: Sequence[float] | None = None,
        start: str | Sequence[float] = "static",
        crawler: bool = True,
        dt_s: float | None = None,
        purpose: StepPurpose | str = StepPurpose.GENERAL,
        floor_pose: BodyPose | None = None,
        damping: str = "rev33",
        rod_side: bool | None = None,
        rod_side_armed: bool = True,
        force_saturation: bool = True,
        actuator_ramp_s: float | None = None,
        lateral_damping_scale: float = 1.0,
        crawler_contact: str | None = None,
    ) -> None:
        if params.l2b is None:
            raise ValueError('params must be loaded with model="L2b_NSC"')
        self.params = params
        ext = (
            operating_extensions_m(params)
            if extensions_m is None
            else tuple(float(e) for e in extensions_m)
        )
        if len(ext) != len(LEG_ORDER):
            raise ValueError(f"need {len(LEG_ORDER)} extensions, got {ext}")
        # Column convention (dyn rev. 33 supplement 1, 5.20.2): ``extensions_m`` are the start
        # references s_ref (oil-column extensions, = the reference solutions' placement
        # extensions); the rod bodies sit at the link extension s = s_ref - F / k_ax(s_ref).
        s_ref0 = np.array(ext, dtype=float)
        k0 = axial_stiffness_at_N_m(params, s_ref0)
        if isinstance(start, str):
            if start == "static":
                f0 = static_cylinder_forces_N(params, k0)
            elif start == "hanging":
                rot = (BodyPose((0.0, 0.0, 0.0)) if pose is None else pose).rotation
                axis = rot @ np.asarray(params.actuator.extension_direction, dtype=float)
                g_axis = float(np.asarray(gravity_vector(params)) @ axis)
                f0 = -np.array([leg.moving_part.mass_kg for leg in params.legs]) * g_axis
            else:
                raise ValueError(f"unknown start {start!r}")
        else:
            f0 = np.array(start, dtype=float).reshape(len(LEG_ORDER))
        for i, leg in enumerate(params.legs):
            lo, hi = leg.extension_range_m
            if not lo <= s_ref0[i] <= hi:
                raise ValueError(f"{leg.name}: start reference {s_ref0[i]} m outside the stroke")
        link_ext = tuple(float(v) for v in s_ref0 - f0 / k0)
        self.start_s_ref_m = tuple(float(v) for v in s_ref0)
        self.extensions_m = link_ext
        """Link (rod-body) extensions at t = 0."""
        if pose is None:
            pose = (
                zero_pose(params, link_ext)
                if float(np.ptp(f0 / k0)) == 0.0
                else touching_pose(params, link_ext)
            )
        self.pose = pose
        ext = link_ext
        bundle = make_system(
            params,
            ChronoModel.L2B_NSC,
            purpose=purpose if dt_s is None else StepPurpose.GENERAL,
            dt=dt_s,
            floor_plate=True,
        )
        self.bundle = bundle
        self.system: ch.ChSystem = bundle.system
        self.floor: ch.ChBody = bundle.floor
        self.dt_s = bundle.dt_s
        self.floor_z_m = params.ground.crawler_bottom_z_m
        self.floor_point_world_m = (0.0, 0.0, self.floor_z_m)
        self.floor_pose = floor_pose
        if floor_pose is not None:
            self.floor.SetPos(chvec(floor_pose.origin_m))
            self.floor.SetRot(floor_pose.chrono_quat())
            on_plane = floor_pose.rotation.T @ (
                np.asarray(self.floor_point_world_m) - floor_pose.origin_m
            )
            if abs(on_plane[2] - self.floor_z_m) > 1e-12:
                raise ValueError("floor pose moves (0, 0, floor_z) off the floor surface")
        set_family(self.floor, FAMILY_FLOOR)
        friction = floor_material_values(params, ChronoModel.L2B_NSC)["friction"]

        # superstructure + crawler spheres (rigid NSC)
        sup = make_superstructure(params, self.pose)
        com_body = np.asarray(params.superstructure.mass_properties.com_m, dtype=float)
        self.crawler_layout: CrawlerSphereLayout | None = (
            crawler_layout(params) if crawler else None
        )
        self.crawler_centres_local_m: NDArray[np.float64] = np.zeros((0, 3))
        cc = params.l2b.crawler_contact
        mode = (cc.model if cc is not None else "rigid") if crawler_contact is None else crawler_contact
        if mode not in ("rigid", "compliant"):
            raise ValueError(f"unknown crawler_contact {crawler_contact!r}")
        if mode == "compliant" and cc is None:
            raise ValueError("compliant crawler needs contact.crawler.L2b_NSC in the YAML")
        if mode == "compliant" and not CRAWLER_CHECK_PASSED:
            import warnings

            warnings.warn("compliant NSC crawler: " + CRAWLER_CHECK_NOTE, RuntimeWarning, stacklevel=2)
        self.crawler_check_passed = CRAWLER_CHECK_PASSED
        self.crawler_contact = {"model": mode, "check_passed": CRAWLER_CHECK_PASSED,
                                "check_note": CRAWLER_CHECK_NOTE, "source": "argument" if crawler_contact else (
            "YAML contact.crawler.L2b_NSC.model" if cc is not None else "default rigid (no YAML block)")}
        if self.crawler_layout is not None:
            sup.EnableCollision(True)
            mat = make_nsc_material(params.l2b.rigid_floor.crawler_friction)
            if mode == "compliant" and crawler:
                assert cc is not None
                mat.SetCompliance(float(cc.compliance_m_N))
                mat.SetDampingF(float(cc.damping_f_s))
                bundle.floor_material.SetDampingF(float(cc.damping_f_s))
                self.crawler_contact.update(
                    compliance_m_N=float(cc.compliance_m_N), damping_f_s=float(cc.damping_f_s),
                    material_float32={"compliance": float(mat.GetCompliance()),
                                      "dampingf": float(mat.GetDampingF()),
                                      "floor_dampingf": float(bundle.floor_material.GetDampingF())},
                    composite="compliance = sum (floor 0), dampingf = min(crawler, floor); "
                              "pad-floor: compliance 0 -> rigid (dampingf unused)")
            centres = self.crawler_layout.centres_body_m(self.floor_z_m)
            self.crawler_centres_local_m = centres - com_body
            for c in centres:
                sup.AddCollisionShape(
                    ch.ChCollisionShapeSphere(mat, self.crawler_layout.sphere_radius_m),
                    ch.ChFramed(chvec(c - com_body), ch.QUNIT),
                )
            set_family(sup, FAMILY_SUPERSTRUCTURE)
        self.system.Add(sup)
        self.superstructure = sup
        self.sup_com_body_m = com_body
        self.origin_in_cog_frame_ch = chvec(-com_body)

        # legs: pad spheres, force motors
        legs = make_leg_moving_parts(params, ext, self.pose)
        q_link = self.pose.chrono_quat() * ch.QuatFromAngleX(np.pi)  # link Z = body -z (R4)
        direction = np.asarray(params.actuator.extension_direction, dtype=float)
        motors, functions, centres_local, radii, ball_frames = [], [], [], [], []
        for i, (leg, body) in enumerate(zip(params.legs, legs, strict=True)):
            radius = leg.pad.swivel_center_above_pad_bottom_m
            centre_body = pad_sphere_centre_body_m(params, i, ext[i])
            centre_local = centre_body - leg_com_body_m(params, i, ext[i])
            body.EnableCollision(True)
            body.AddCollisionShape(
                ch.ChCollisionShapeSphere(make_nsc_material(friction), radius),
                ch.ChFramed(chvec(centre_local), ch.QUNIT),
            )
            set_family(body, FAMILY_ROD, no_collision_with=(FAMILY_SUPERSTRUCTURE,))
            self.system.Add(body)
            attachment = np.asarray(leg.attachment_point_m, dtype=float)
            frame_body = ch.ChFramed(chvec(self.pose.to_world(attachment)), q_link)
            frame_rod = ch.ChFramed(
                chvec(self.pose.to_world(attachment + ext[i] * direction)), q_link
            )
            motor, function = make_force_motor(
                body, sup, frame_rod, frame_body, name=f"motor_{leg.name}"
            )
            self.system.Add(motor)
            motors.append(motor)
            functions.append(function)
            centres_local.append(centre_local)
            radii.append(radius)
            ball_frames.append(ch.ChFramed(chvec(self.pose.to_world(centre_body)), q_link))
        self.legs: tuple[ch.ChBody, ...] = tuple(legs)
        self.motors = tuple(motors)
        self.sphere_centres_local_m = tuple(np.asarray(c) for c in centres_local)
        self.sphere_centres_local_ch = tuple(chvec(c) for c in centres_local)
        self.sphere_radii_m = tuple(radii)

        values = lateral_bushing_values(params)
        if lateral_damping_scale != 1.0:
            values = dataclasses.replace(
                values,
                damping_N_s_m=tuple(lateral_damping_scale * c for c in values.damping_N_s_m),
                source=values.source + f" x {lateral_damping_scale}",
            )
        self.bushings = LateralBushings(self.system, legs, sup, ball_frames, values)

        # start forces and references (computed above: s_ref0, f0, k0 = k_ax(s_ref0))
        self.start_kind = start if isinstance(start, str) else "forces"
        self.actuator = L2bForceActuator.from_params(
            params,
            self.motors,
            functions,
            s_ref0,
            force_saturation=force_saturation,
            ramp_s=actuator_ramp_s,
            damping=damping,
            rod_side=rod_side,
            rod_side_armed=rod_side_armed,
        )
        self.actuator.set_initial_force(f0)
        self.start_forces_N = f0
        self.k_ax0_N_m = k0
        self.damping = damping
        self.lateral_damping_scale = float(lateral_damping_scale)
        self.last_probe: ProbeState | None = None
        self.actuator_hooks: list[StepHook] = [self._actuator_hook]
        self.load_hooks: list[StepHook] = []
        self.record_hooks: list[RecordHook] = []
        self._fixed_superstructure = False

    # --- helpers ------------------------------------------------------------------------------

    def system_gravity(self) -> tuple[float, float, float]:
        g = self.system.GetGravitationalAcceleration()
        return (float(g.x), float(g.y), float(g.z))

    def floor_normal_world(self) -> NDArray[np.float64]:
        z = self.floor.GetRot().GetAxisZ()
        return np.array([z.x, z.y, z.z], dtype=float)

    def fix_superstructure(self) -> None:
        """Hold the superstructure fixed (V11 air stroke, sign test)."""
        self.superstructure.SetFixed(True)
        self._fixed_superstructure = True

    @property
    def bodies(self) -> tuple[ch.ChBody, ...]:
        return (self.superstructure, *self.legs)

    @property
    def body_names(self) -> tuple[str, ...]:
        return tuple(str(b.GetName()) for b in self.bodies)

    @property
    def s_ref_m(self) -> NDArray[np.float64]:
        return self.actuator.reference.s_ref_m

    @property
    def u_applied_m_s(self) -> NDArray[np.float64]:
        return self.actuator.reference.u_applied_m_s

    def set_command(self, leg_speed_m_s: ArrayLike) -> None:
        self.actuator.set_command(leg_speed_m_s)

    def set_dt(self, dt_s: float) -> None:
        """Change the step (explicit force law: no pending segment to re-integrate)."""
        dt = float(dt_s)
        if not (dt > 0.0 and np.isfinite(dt)):
            raise ValueError(f"dt must be positive: {dt_s!r}")
        self.dt_s = dt

    # --- stepping -----------------------------------------------------------------------------

    def step(self, *, capture: bool = False) -> L2bStepResult:
        t0 = float(self.system.GetChTime())
        self.actuator.on_step_start(t0)
        self.bushings.on_step_start(t0)
        self.system.DoStepDynamics(self.dt_s)
        self.actuator.on_step_end()
        self.bushings.on_step_end()
        return self.after_step(self.dt_s, capture=capture)

    def after_step(self, dt_s: float, *, capture: bool = False) -> L2bStepResult:
        probe = read_l2b_probe(self) if (capture or self.record_hooks) else None
        self.last_probe = probe
        t = float(self.system.GetChTime())
        self.bushings.hook(t)
        for hook in self.actuator_hooks:
            hook(self, dt_s)
        for hook in self.load_hooks:
            hook(self, dt_s)
        if probe is not None:
            for record in self.record_hooks:
                record(self, probe)
        return L2bStepResult(probe)

    def _actuator_hook(self, model: L2bModel, dt_s: float) -> None:
        self.actuator.hook(float(self.system.GetChTime()), dt_s)

    def probe(self) -> ProbeState:
        return read_l2b_probe(self)

    def truth(self, probe: ProbeState) -> TruthState:
        """:class:`TruthState` of a probe copy; ``stroke_true_m`` = ``s + F / k_out``
        (``L2bForceActuator.stroke_true_m``)."""
        state = truth_state(
            probe, s_ref_m=self.s_ref_m, u_applied_m_s=self.u_applied_m_s,
            k_oil_N_m=[np.inf] * len(LEG_ORDER),
        )
        stroke = (self.actuator.stroke_sensor_true_m(probe.motor_pos_m)
                  if self.actuator.friction_path
                  else self.actuator.stroke_true_m(probe.motor_pos_m, probe.motor_force_N))
        return dataclasses.replace(state, stroke_true_m=stroke)

    # --- snapshot (R16) -------------------------------------------------------------------------

    def snapshot(self, held_command: Command | None = None) -> Snapshot:
        t = float(self.system.GetChTime())
        if held_command is None:
            held_command = Command(t_s=t, leg_speed_m_s=self.actuator.reference.command_m_s)
        return capture_snapshot(
            self.system,
            engine=engine_info(ChronoModel.L2B_NSC.value),
            params_sha256=self.params.sha256,
            held_command=held_command,
            bodies=self.bodies,
            motors=self.motors,
            s_ref_m=self.actuator.reference.s_ref_m,
            parts={ACTUATOR_PART: self.actuator, BUSHING_PART: self.bushings},
        )

    def restore(self, snapshot: Snapshot) -> float:
        """Restore a snapshot of the same model (same params, level, start not relevant)."""
        restored = restore_snapshot(
            snapshot,
            self.system,
            engine=engine_info(ChronoModel.L2B_NSC.value),
            params_sha256=self.params.sha256,
            bodies=self.bodies,
            motors=self.motors,
            parts={ACTUATOR_PART: self.actuator, BUSHING_PART: self.bushings},
        )
        self.actuator.set_command(restored.held_command.leg_speed_m_s)
        return restored.time_s

    # --- meta and checks ------------------------------------------------------------------------

    def meta(self) -> dict[str, Any]:
        meta = self.bundle.meta()
        meta.update(
            engine_version=engine_info(ChronoModel.L2B_NSC.value).version,
            model="L2b_NSC four legs (S7)",
            auger_level=self.params.level.value,
            extensions_m=list(self.extensions_m),
            initial_pose={"origin_m": list(self.pose.origin_m),
                          "quat_wxyz": list(self.pose.quat_wxyz)},
            start=self.start_kind,
            start_forces_N=self.start_forces_N.tolist(),
            k_ax0_N_m=self.k_ax0_N_m.tolist(),
            crawler_spheres=0 if self.crawler_layout is None else self.crawler_layout.n_points,
            crawler_contact=self.crawler_contact,
            floor_pose=None if self.floor_pose is None else {
                "origin_m": list(self.floor_pose.origin_m),
                "quat_wxyz": list(self.floor_pose.quat_wxyz)},
            damping_basis=self.damping,
            damping_source=self.params.l2b.actuator.damping_source,
            lateral_damping_scale=self.lateral_damping_scale,
            actuator=self.actuator.meta(),
            lateral_bushing=self.bushings.meta(),
            collision_families={"floor": FAMILY_FLOOR, "superstructure": FAMILY_SUPERSTRUCTURE,
                                "rod": FAMILY_ROD,
                                "disabled_pairs": ["rod-superstructure (incl. crawler)"]},
            input_lag_steps=1,
        )
        return meta

    def v0_inventory(self) -> dict[str, Any]:
        """Values as Chrono holds them (V0), before the first step."""
        self.system.Update()
        rot = self.pose.rotation
        origin = np.asarray(self.pose.origin_m, dtype=float)

        def entry(body: ch.ChBody) -> dict[str, Any]:
            props = read_mass_properties(body)
            return {
                "name": str(body.GetName()),
                "mass_kg": props.mass_kg,
                "com_body_m": (rot.T @ (props.com_world_m - origin)).tolist(),
                "inertia_kg_m2": props.inertia_kg_m2.tolist(),
                "collision": shape_materials(body) if body.GetCollisionModel() else [],
            }

        g = self.system.GetGravitationalAcceleration()
        return {
            "gravity_m_s2": [g.x, g.y, g.z],
            "collision_system_is_bullet": bool(
                self.system.GetCollisionSystem().GetType() == ch.ChCollisionSystem.Type_BULLET
            ),
            "floor": {"mass_kg": float(self.floor.GetMass()), "fixed": bool(self.floor.IsFixed()),
                      "collision": shape_materials(self.floor)},
            "superstructure": entry(self.superstructure),
            "legs": [entry(b) for b in self.legs],
            "motor_pos_m": [float(m.GetMotorPos()) for m in self.motors],
            "motor_constraints": [int(m.GetNumConstraintsBilateral()) for m in self.motors],
            "lateral_bushing": self.bushings.meta(),
        }


# --- V1 cross-check of the NSC pad normal force (plan S7 risk 5) -----------------------------


def pad_force_crosscheck(model: L2bModel) -> dict[str, Any]:
    """Three readings of the pad normal force of the step just taken (call right after a step):

    * ``get_contact_force_N``: ``ChBody.GetContactForce()`` along the floor normal per rod;
    * ``report_contacts_N``: ``ReportAllContacts`` summed per rod (independent path);
    * ``axial_balance_N``: ``F_acting n_axis . n + m_rod g`` along the normal plus the lateral
      bushing force on the rod (rod equilibrium at rest; differs by the rod inertia while moving);
    * ``total``: pads + crawler along the normal versus the total weight.
    """
    n = model.floor_normal_world()
    names = [str(b.GetName()) for b in model.legs]
    via_body = np.array([_v(b.GetContactForce()) for b in model.legs]) @ n
    report = report_contacts(model.system, names)
    via_report = report.force_world_N @ n
    g = np.asarray(model.system_gravity(), dtype=float)
    q_body = model.superstructure.GetRot()
    axis = _v(q_body.Rotate(chvec(model.params.actuator.extension_direction)))
    masses = np.array([leg.moving_part.mass_kg for leg in model.params.legs])
    f = model.actuator.acting_force_N
    lateral = model.bushings.force_on_rod_world_N(acting=True)
    # rod at rest: contact + cylinder (along +axis = push down) + lateral + weight = 0
    balance = -((f[:, None] * axis[None, :] + lateral + masses[:, None] * g[None, :]) @ n)
    crawler = (
        report_sphere_contacts(model.system, model.superstructure,
                               model.crawler_centres_local_m).force_world_N @ n
        if model.crawler_layout is not None
        else np.zeros(0)
    )
    m_total = model.params.superstructure.mass_properties.mass_kg + masses.sum()
    weight_n = -float(m_total * (g @ n))
    total = float(via_body.sum() + crawler.sum())
    return {
        "t_s": float(model.system.GetChTime()),
        "get_contact_force_N": via_body.tolist(),
        "report_contacts_N": via_report.tolist(),
        "report_contact_count": report.count.tolist(),
        "axial_balance_N": balance.tolist(),
        "crawler_total_N": float(crawler.sum()),
        "pads_plus_crawler_N": total,
        "weight_along_normal_N": weight_n,
        "max_abs_body_minus_report_N": float(np.abs(via_body - via_report).max()),
        "max_abs_body_minus_balance_N": float(np.abs(via_body - balance).max()),
        "total_rel_error": (total - weight_n) / weight_n,
    }


# --- settle helper ----------------------------------------------------------------------------


@dataclass
class L2bSettleRun:
    t_s: NDArray[np.float64]
    pad_normal_N: NDArray[np.float64]
    cylinder_force_N: NDArray[np.float64]
    roll_pitch_deg: NDArray[np.float64]
    motor_pos_m: NDArray[np.float64]
    body_pos_m: NDArray[np.float64]
    crawler_normal_N: NDArray[np.float64]
    nonfinite_steps: int
    steps: int
    wall_s: float


def run_l2b_settle(model: L2bModel, duration_s: float, *, sample_every: int = 1) -> L2bSettleRun:
    """Step ``duration_s`` and keep every ``sample_every``-th state copy."""
    from outrigger_sim.frames import roll_pitch_from_quat

    n_steps = round(duration_s / model.dt_s)
    rows: dict[str, list[Any]] = {k: [] for k in ("t", "N", "F", "rp", "s", "o", "cr")}
    bad = 0
    t0 = time.perf_counter()
    for k in range(1, n_steps + 1):
        res = model.step(capture=(k % sample_every == 0))
        p = res.probe
        if p is None:
            continue
        values = (p.pad_normal_force_N, p.motor_force_N, p.body_pos_m)
        if not all(np.all(np.isfinite(v)) for v in values):
            bad += 1
        rows["t"].append(p.t_s)
        rows["N"].append(p.pad_normal_force_N)
        rows["F"].append(p.motor_force_N)
        rows["rp"].append(np.degrees(roll_pitch_from_quat(p.body_quat_wxyz)))
        rows["s"].append(p.motor_pos_m)
        rows["o"].append(p.body_pos_m)
        rows["cr"].append(float(p.crawler_contact_world_N @ p.floor_normal_world))
    wall = time.perf_counter() - t0
    return L2bSettleRun(
        t_s=np.asarray(rows["t"]), pad_normal_N=np.asarray(rows["N"]),
        cylinder_force_N=np.asarray(rows["F"]), roll_pitch_deg=np.asarray(rows["rp"]),
        motor_pos_m=np.asarray(rows["s"]), body_pos_m=np.asarray(rows["o"]),
        crawler_normal_N=np.asarray(rows["cr"]), nonfinite_steps=bad, steps=n_steps,
        wall_s=wall,
    )


__all__ = [
    "ACTUATOR_PART",
    "CRAWLER_CHECK_NOTE",
    "CRAWLER_CHECK_PASSED",
    "BUSHING_PART",
    "L2bModel",
    "L2bSettleRun",
    "L2bStepResult",
    "axial_stiffness_at_N_m",
    "pad_force_crosscheck",
    "read_l2b_probe",
    "run_l2b_settle",
    "static_cylinder_forces_N",
]
