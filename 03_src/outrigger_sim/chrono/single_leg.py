"""Single-leg test model for the 210 bar force saturation (plan S6 V11b).

``00_docs/03_chrono/chrono_build_plan.md`` S6 (cad: 단일 다리 시험 모델). One leg moving part
of the L1 model hangs from a **fixed** frame body on its ``ChLinkMotorLinearPosition`` (guide
PRISMATIC, link Z = body -z, R4, same frames as ``chrono/model``), driven by
:class:`~outrigger_sim.chrono.actuators.L1SpeedActuator` with the YAML speed, ramp and force
limits. The pad is tied to the floor by a **two-way linear spring-damper** ``ChLinkTSDA`` along
the leg axis with ``k = contact.rigid_floor.L1.kn_per_pad_N_m`` and ``c =
contact.rigid_floor.L1.cn_per_pad_N_s_m`` (the actual damping, plan: '감쇠 = c_n 실제값'): a
rigid tie would be in series with the rigid motor (force undetermined), and a contact cannot
pull (retract test). The spring is at its rest length at the start, so the start force is the
rod weight held by the motor (``F_cyl = -m_rod g``).

The spring runs from the pad bottom point straight down by :data:`SPRING_LENGTH_M` to a floor
point; the prismatic guide carries every lateral load, so only the axial spring acts.

Hook order per step (as ``L1Model.step`` / ``after_step`` step 3): hook guard -> step ->
``on_step_end`` -> actuator hook (force saturation from the step's cylinder force, ``s_ref``
integration). There is no contact, ground bushing or crawler. Gravity on (R1), collision
system Bullet (R2, no shapes), floor 1e9 kg fixed (R6), integrator and solver as the L1 model
(``make_system``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.actuators import (
    L1SpeedActuator,
    leg_force_limits_N,
    make_motion_function,
)
from outrigger_sim.chrono.bodies import BodyPose, make_leg_moving_parts
from outrigger_sim.chrono.model import operating_extensions_m
from outrigger_sim.chrono.probes import chvec
from outrigger_sim.chrono.system import ChronoModel, make_system
from outrigger_sim.geometry import pad_sphere_centre_body_m
from outrigger_sim.params import LEG_ORDER, Params

SPRING_LENGTH_M = 1.0
"""Rest length of the pad-floor spring (geometry only; the force depends on the stretch)."""
FRAME_ORIGIN_Z_M = 2.0
"""Height of the fixed frame body origin (body axes = world axes, level)."""


@dataclass(frozen=True)
class SingleLegSample:
    """One step of the single-leg model (SI)."""

    t_s: float
    cylinder_force_N: float
    motor_pos_m: float
    spring_force_N: float
    u_applied_m_s: float
    u_cmd_m_s: float
    saturated: bool


class SingleLegModel:
    """One actuated leg tied to the floor by a two-way spring (module docstring).

    Args:
        params: Parameters.
        leg: Leg name (``FL`` ... ``RR``).
        extension_m: Start extension; default the operating extension of the leg.
        dt_s: Time step; default YAML ``simulation.L1.dt_s``.
        force_saturation: Actuator force limits from the YAML (False = none).
        spring_k_N_m, spring_c_N_s_m: Spring overrides (default YAML pad ``k_n``, ``c_n``).
    """

    def __init__(
        self,
        params: Params,
        leg: str = "FL",
        *,
        extension_m: float | None = None,
        dt_s: float | None = None,
        force_saturation: bool = True,
        spring_k_N_m: float | None = None,
        spring_c_N_s_m: float | None = None,
    ) -> None:
        if leg not in LEG_ORDER:
            raise ValueError(f"unknown leg {leg!r}")
        index = LEG_ORDER.index(leg)
        self.params = params
        self.leg = leg
        self.leg_index = index
        e0 = operating_extensions_m(params)[index] if extension_m is None else float(extension_m)
        self.extension0_m = e0
        bundle = make_system(params, ChronoModel.L1, dt=dt_s, floor_plate=False)
        self.bundle = bundle
        self.system: ch.ChSystem = bundle.system
        self.floor: ch.ChBody = bundle.floor
        self.dt_s = bundle.dt_s
        pose = BodyPose((0.0, 0.0, FRAME_ORIGIN_Z_M))
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
        self.system.Add(body)
        self.leg_body = body
        spec = params.legs[index]
        attachment = np.asarray(spec.attachment_point_m, dtype=float)
        direction = np.asarray(params.actuator.extension_direction, dtype=float)
        q_link = pose.chrono_quat() * ch.QuatFromAngleX(np.pi)
        frame_body = ch.ChFramed(chvec(pose.to_world(attachment)), q_link)
        frame_leg = ch.ChFramed(chvec(pose.to_world(attachment + e0 * direction)), q_link)
        motor = ch.ChLinkMotorLinearPosition()
        motor.SetName(f"motor_{leg}")
        motor.Initialize(body, frame, False, frame_leg, frame_body)
        function = make_motion_function(e0)
        motor.SetMotionFunction(function)
        self.system.Add(motor)
        self.motor = motor
        self.motors = (motor,)

        kn = params.get("contact.rigid_floor.L1.kn_per_pad_N_m")
        cn = params.get("contact.rigid_floor.L1.cn_per_pad_N_s_m")
        self.spring_k_N_m = float(kn[leg]) if spring_k_N_m is None else float(spring_k_N_m)
        self.spring_c_N_s_m = float(cn[leg]) if spring_c_N_s_m is None else float(spring_c_N_s_m)
        radius = spec.pad.swivel_center_above_pad_bottom_m
        bottom = pose.to_world(pad_sphere_centre_body_m(params, index, e0)) - np.array(
            [0.0, 0.0, radius]
        )
        anchor = bottom - np.array([0.0, 0.0, SPRING_LENGTH_M])
        spring = ch.ChLinkTSDA()
        spring.SetName(f"pad_spring_{leg}")
        spring.Initialize(body, self.floor, False, chvec(bottom), chvec(anchor))
        spring.SetRestLength(SPRING_LENGTH_M)
        spring.SetSpringCoefficient(self.spring_k_N_m)
        spring.SetDampingCoefficient(self.spring_c_N_s_m)
        self.system.Add(spring)
        self.spring = spring
        self.rod_mass_kg = float(spec.moving_part.mass_kg)

        f_ext = f_ret = None
        if force_saturation:
            ext_all, ret_all = leg_force_limits_N(params)
            f_ext, f_ret = ext_all[LEG_ORDER.index(leg)], ret_all[LEG_ORDER.index(leg)]
        self.actuator = L1SpeedActuator(
            [motor],
            [function],
            [e0],
            [spec.extension_range_m],
            max_speed_m_s=params.actuator.max_speed_m_s,
            ramp_s=params.actuator.command_ramp_s,
            max_force_extend_N=f_ext,
            max_force_retract_N=f_ret,
            rod_mass_kg=[self.rod_mass_kg],
            saturation_stop_max_s=[
                2.0 * float(cn[leg]) / float(kn[leg])
            ],
        )

    def set_command(self, speed_m_s: float) -> None:
        self.actuator.set_command([float(speed_m_s)])

    def step(self) -> SingleLegSample:
        """Hook guard -> ``DoStepDynamics`` -> actuator hook (module docstring)."""
        act = self.actuator
        act.on_step_start(not self.system.IsUpdated(), float(self.system.GetChTime()), self.dt_s)
        self.system.DoStepDynamics(self.dt_s)
        act.on_step_end()
        sample = SingleLegSample(
            t_s=float(self.system.GetChTime()),
            cylinder_force_N=float(self.motor.GetMotorForce()),
            motor_pos_m=float(self.motor.GetMotorPos()),
            spring_force_N=float(self.spring.GetForce()),
            u_applied_m_s=float(act.acting_u_m_s[0]),
            u_cmd_m_s=float(act.command_m_s[0]),
            saturated=False,
        )
        act.hook(self, self.dt_s)
        return SingleLegSample(**{**sample.__dict__, "saturated": bool(act.saturated[0])})

    def meta(self) -> dict[str, Any]:
        meta = self.bundle.meta()
        meta.update(
            model="single leg (S6 V11b)",
            leg=self.leg,
            extension0_m=self.extension0_m,
            spring={
                "type": "ChLinkTSDA, two-way, pad bottom -> floor along the leg axis",
                "k_N_m": self.spring_k_N_m,
                "c_N_s_m": self.spring_c_N_s_m,
                "rest_length_m": SPRING_LENGTH_M,
                "source": "contact.rigid_floor.L1.kn_per_pad_N_m / cn_per_pad_N_s_m",
            },
            rod_mass_kg=self.rod_mass_kg,
            force_limits_N=self.actuator.force_limits_N,
            max_speed_m_s=self.actuator.max_speed_m_s,
            ramp_s=self.actuator.ramp_s,
            input_lag_steps=1,
        )
        return meta


def run_schedule(
    model: SingleLegModel, schedule: list[tuple[float, float]], end_s: float
) -> dict[str, NDArray[Any]]:
    """Step to ``end_s`` with a piecewise-constant command ``[(t_from, speed), ...]`` (set
    before the step that starts at or after ``t_from``; the hook after that step integrates
    it). Returns per-step arrays (``t`` relative to the start)."""
    t_start = float(model.system.GetChTime())
    n = round(end_s / model.dt_s)
    events = sorted(schedule)
    rows: dict[str, list[Any]] = {
        k: [] for k in ("t", "F_cyl", "s_motor", "F_spring", "u_applied", "u_cmd", "saturated")
    }
    j = 0
    for _ in range(n):
        t_rel = float(model.system.GetChTime()) - t_start
        while j < len(events) and events[j][0] <= t_rel + 1e-12:
            model.set_command(events[j][1])
            j += 1
        s = model.step()
        rows["t"].append(s.t_s - t_start)
        rows["F_cyl"].append(s.cylinder_force_N)
        rows["s_motor"].append(s.motor_pos_m)
        rows["F_spring"].append(s.spring_force_N)
        rows["u_applied"].append(s.u_applied_m_s)
        rows["u_cmd"].append(s.u_cmd_m_s)
        rows["saturated"].append(s.saturated)
    out = {k: np.asarray(v, dtype=float) for k, v in rows.items() if k != "saturated"}
    out["saturated"] = np.asarray(rows["saturated"], dtype=bool)
    return out


__all__ = ["SPRING_LENGTH_M", "SingleLegModel", "SingleLegSample", "run_schedule"]
