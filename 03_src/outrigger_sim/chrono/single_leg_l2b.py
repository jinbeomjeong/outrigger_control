"""Single-leg L2b-NSC test model (plan S7 checklist items 1-3: guide, force law, lateral bushing).

One leg moving part hangs from a **fixed** frame body on a ``ChLinkMotorLinearForce`` (link Z =
body -z, R4; guide x, y free, ``chrono/l2b_actuator``) driven by :class:`~outrigger_sim.chrono.
l2b_actuator.L2bForceActuator`, with the lateral bushing (``chrono/lateral_bushing``) between
rod and frame at the ball centre. ``ChSystemNSC`` from ``make_system(params, "L2b_NSC")`` (PSOR
50, mu 0.5, gravity R1, Bullet R2, floor R6).

* ``floor=True``: the pad sphere (radius = ball height, NSC mu = ``contact.rigid_floor.L2b_NSC.
  friction``) just touches the default floor plate at the start extension (frame height chosen
  for that); the start force is the preload ``preload_N`` with ``s_ref = e0 + preload / k_ax``.
* ``floor=False``: no floor plate; the start force holds the rod weight along the leg axis
  (``s_ref = e0 + F0 / k_ax``, ``F0 = m g_axis``, sign + = extend).

Step order (as the L1 model, ``dynamics_model.md`` 4.6 ruling 2): hook guard -> ``DoStepDynamics``
-> ``on_step_end`` -> actuator hook (judgement with the force that acted, ``s_ref`` integration,
new force from the state at ``t_n``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.bodies import BodyPose, make_leg_moving_parts
from outrigger_sim.chrono.l2b_actuator import L2bForceActuator, make_force_motor
from outrigger_sim.chrono.lateral_bushing import LateralBushings, lateral_bushing_values
from outrigger_sim.chrono.model import operating_extensions_m
from outrigger_sim.chrono.probes import chvec
from outrigger_sim.chrono.system import (
    ChronoModel,
    floor_material_values,
    make_nsc_material,
    make_system,
    set_gravity,
)
from outrigger_sim.geometry import leg_com_body_m, pad_sphere_centre_body_m
from outrigger_sim.params import LEG_ORDER, Params, axial_stiffness_N_m

FRAME_ORIGIN_Z_AIR_M = 2.0
"""Frame height without a floor (body axes = world axes, level)."""


@dataclass(frozen=True)
class SingleLegL2bSample:
    t_s: float
    force_N: float
    """Force that acted during the step (cylinder force)."""
    motor_pos_m: float
    motor_vel_m_s: float
    s_ref_m: float
    u_applied_m_s: float
    contact_force_world_N: tuple[float, float, float]
    bushing_force_N: tuple[float, float]
    """Lateral bushing force on the rod that acted in the step, link axes (x, y) [N]."""
    bushing_disp_m: tuple[float, float]
    """Lateral offset of the ball point at the step end, link axes (x, y) [m]."""
    ball_centre_world_m: tuple[float, float, float]
    saturated: bool


class SingleLegL2bModel:
    """One L2b-NSC leg on a fixed frame (module docstring).

    Args:
        params: Loaded with ``model="L2b_NSC"``.
        leg: Leg name.
        extension_m: Start extension (default: the L1 operating extension).
        floor: Pad on the NSC floor plate (True) or in the air (False).
        preload_N: Start force with the floor (+ = pad pushed down).
        dt_s: Time step (default ``simulation.L2b_NSC.dt_s``).
        gravity_m_s2: World gravity vector (default ``(0, 0, -g)``; R1, set explicitly).
        lateral_bushing: Add the lateral bushing (False only with ``free_xy=False``).
        free_xy: Free the motor guide in x, y.
        force_saturation: Per-leg 210 bar limits (law C).
        damping: ``"rev33"`` (default, ``dynamics_model.md`` 5.20.3) or ``"yaml_pre_rev33"``.
        rod_side: Rod-side law (default off: these single-leg checks are of the head-only law;
            the four-leg model has it on).
    """

    def __init__(
        self,
        params: Params,
        leg: str = "FL",
        *,
        extension_m: float | None = None,
        floor: bool = True,
        preload_N: float = 0.0,
        dt_s: float | None = None,
        gravity_m_s2: tuple[float, float, float] | None = None,
        lateral_bushing: bool = True,
        free_xy: bool = True,
        force_saturation: bool = True,
        damping: str = "rev33",
        rod_side: bool = False,
    ) -> None:
        if params.l2b is None:
            raise ValueError('params must be loaded with model="L2b_NSC"')
        if leg not in LEG_ORDER:
            raise ValueError(f"unknown leg {leg!r}")
        if free_xy and not lateral_bushing:
            raise ValueError("a freed guide needs the lateral bushing (rod would be loose)")
        index = LEG_ORDER.index(leg)
        self.params = params
        self.leg = leg
        e0 = operating_extensions_m(params)[index] if extension_m is None else float(extension_m)
        self.extension0_m = e0
        bundle = make_system(params, ChronoModel.L2B_NSC, dt=dt_s, floor_plate=floor)
        self.bundle = bundle
        self.system: ch.ChSystem = bundle.system
        self.dt_s = bundle.dt_s
        g = params.meta.gravity_m_s2
        self.gravity = (0.0, 0.0, -g) if gravity_m_s2 is None else tuple(map(float, gravity_m_s2))
        set_gravity(self.system, self.gravity)

        spec = params.legs[index]
        radius = spec.pad.swivel_center_above_pad_bottom_m
        centre_body = pad_sphere_centre_body_m(params, index, e0)
        if floor:
            z0 = params.ground.crawler_bottom_z_m + radius - float(centre_body[2])
        else:
            z0 = FRAME_ORIGIN_Z_AIR_M
        pose = BodyPose((0.0, 0.0, z0))
        self.pose = pose

        frame = ch.ChBody()
        frame.SetName("frame_fixed")
        frame.SetMass(1.0e9)
        frame.SetPos(chvec(pose.origin_m))
        frame.SetFixed(True)
        self.system.Add(frame)
        self.frame = frame

        exts = list(operating_extensions_m(params))
        exts[index] = e0
        body = make_leg_moving_parts(params, exts, pose)[index]
        self.centre_local = np.asarray(centre_body, dtype=float) - leg_com_body_m(
            params, index, e0
        )
        if floor:
            mat = make_nsc_material(floor_material_values(params, ChronoModel.L2B_NSC)["friction"])
            body.EnableCollision(True)
            body.AddCollisionShape(
                ch.ChCollisionShapeSphere(mat, radius),
                ch.ChFramed(chvec(self.centre_local), ch.QUNIT),
            )
        self.system.Add(body)
        self.rod = body
        self.rod_mass_kg = float(spec.moving_part.mass_kg)

        attachment = np.asarray(spec.attachment_point_m, dtype=float)
        direction = np.asarray(params.actuator.extension_direction, dtype=float)
        q_link = pose.chrono_quat() * ch.QuatFromAngleX(np.pi)
        frame_body = ch.ChFramed(chvec(pose.to_world(attachment)), q_link)
        frame_rod = ch.ChFramed(chvec(pose.to_world(attachment + e0 * direction)), q_link)
        motor, function = make_force_motor(
            body, frame, frame_rod, frame_body, name=f"motor_{leg}", free_xy=free_xy
        )
        self.system.Add(motor)
        self.motor = motor

        self.bushings: LateralBushings | None = None
        if lateral_bushing:
            ball_world = pose.to_world(centre_body)
            self.bushings = LateralBushings(
                self.system,
                [body],
                frame,
                [ch.ChFramed(chvec(ball_world), q_link)],
                lateral_bushing_values(params, [leg]),
            )

        # start force and reference: preload on the floor, the rod weight share in the air
        g_axis = float(np.dot(np.asarray(self.gravity), direction))  # gravity along +extension
        f0 = float(preload_N) if floor else -self.rod_mass_kg * g_axis
        a = params.l2b.actuator

        def k_at(s: float) -> float:
            return axial_stiffness_N_m(
                s,
                bulk_modulus_Pa=a.oil_bulk_modulus_eff_Pa,
                head_area_m2=a.head_area_m2[index],
                dead_length_m=a.oil_dead_length_m,
                k_rod_N_m=a.k_rod_N_m[index],
                k_frame_N_m=a.frame_stiffness_N_m,
                k_concrete_N_m=a.k_concrete_N_m,
            )

        # the law evaluates k at s_ref (column convention, rev. 33 supplement 1): fixed point
        # s_ref = e0 + f0 / k(s_ref) so that the law gives f0 at the start
        s_ref0 = e0 + f0 / k_at(e0)
        for _ in range(6):
            s_ref0 = e0 + f0 / k_at(s_ref0)
        k0 = k_at(s_ref0)
        lo, hi = spec.extension_range_m
        if not lo <= s_ref0 <= hi:
            raise ValueError(f"start reference {s_ref0} m outside the stroke {lo} .. {hi}")
        self.actuator = L2bForceActuator.from_params(
            params, [motor], [function], [s_ref0], legs=[leg], force_saturation=force_saturation,
            damping=damping, rod_side=rod_side,
        )
        self.actuator.set_initial_force([f0])
        self.start_force_N = f0
        self.k_ax0_N_m = k0

    def set_command(self, speed_m_s: float) -> None:
        self.actuator.set_command([float(speed_m_s)])

    def ball_centre_world(self) -> NDArray[np.float64]:
        p = self.rod.TransformPointLocalToParent(chvec(self.centre_local))
        return np.array([p.x, p.y, p.z])

    def step(self) -> SingleLegL2bSample:
        act = self.actuator
        t0 = float(self.system.GetChTime())
        act.on_step_start(t0)
        if self.bushings is not None:
            self.bushings.on_step_start(t0)
        self.system.DoStepDynamics(self.dt_s)
        act.on_step_end()
        if self.bushings is not None:
            self.bushings.on_step_end()
        cf = self.rod.GetContactForce()
        bf = (0.0, 0.0)
        bd = (0.0, 0.0)
        if self.bushings is not None:
            bf = tuple(float(v) for v in self.bushings.acting_force_on_rod_N[0])
            bd = tuple(float(v) for v in self.bushings.displacement_m()[0])
        sample = dict(
            t_s=float(self.system.GetChTime()),
            force_N=float(act.acting_force_N[0]),
            motor_pos_m=float(self.motor.GetMotorPos()),
            motor_vel_m_s=float(self.motor.GetMotorPosDt()),
            s_ref_m=float(act.reference.s_ref_m[0]),
            u_applied_m_s=float(act.reference.u_applied_m_s[0]),
            contact_force_world_N=(float(cf.x), float(cf.y), float(cf.z)),
            bushing_force_N=bf,
            bushing_disp_m=bd,
            ball_centre_world_m=tuple(float(v) for v in self.ball_centre_world()),
        )
        t1 = float(self.system.GetChTime())
        if self.bushings is not None:
            self.bushings.hook(t1)
        act.hook(t1, self.dt_s)
        return SingleLegL2bSample(**sample, saturated=bool(act.reference.saturated[0]))

    def meta(self) -> dict[str, Any]:
        meta = self.bundle.meta()
        meta.update(
            model="single leg L2b-NSC (S7)",
            leg=self.leg,
            extension0_m=self.extension0_m,
            gravity_m_s2=list(self.gravity),
            start_force_N=self.start_force_N,
            k_ax0_N_m=self.k_ax0_N_m,
            rod_mass_kg=self.rod_mass_kg,
            actuator=self.actuator.meta(),
            lateral_bushing=None if self.bushings is None else self.bushings.meta(),
        )
        return meta


def run_steps(
    model: SingleLegL2bModel, end_s: float, schedule: list[tuple[float, float]] | None = None
) -> dict[str, NDArray[Any]]:
    """Step ``end_s`` with a piecewise-constant command ``[(t_from, speed), ...]``; arrays per
    step (``t`` relative to the start)."""
    t0 = float(model.system.GetChTime())
    events = sorted(schedule or [])
    j = 0
    rows: dict[str, list[Any]] = {}
    for _ in range(round(end_s / model.dt_s)):
        t_rel = float(model.system.GetChTime()) - t0
        while j < len(events) and events[j][0] <= t_rel + 1e-12:
            model.set_command(events[j][1])
            j += 1
        s = model.step()
        for key, value in s.__dict__.items():
            rows.setdefault(key, []).append(value)
    out = {k: np.asarray(v) for k, v in rows.items()}
    out["t_s"] = out["t_s"] - t0
    return out


__all__ = ["SingleLegL2bModel", "SingleLegL2bSample", "run_steps"]
