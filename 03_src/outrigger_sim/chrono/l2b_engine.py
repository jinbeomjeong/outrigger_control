"""L2b-NSC Chrono model behind the engine-independent boundary (``SimEngine`` + closed-loop hooks).

Same structure as :class:`outrigger_sim.chrono.l1_engine.L1Engine` (plan 3.1-3.3): the engine's
hook sits at the head of :attr:`L2bModel.actuator_hooks` (after the state copy and the lateral
bushing hook, before the force-law hook), so a command applied inside the step callback drives
the reference of step ``n + 1``; between steps it is used from step ``n + 2``.

Measurements (ideal, plan S7 "제어 ③ 준비" is later work): IMU from
:class:`outrigger_sim.chrono.truth.L1SensorTruth` (kinematics only, engine independent),
cylinder forces = the force-law value that acted in the step (``L2bForceActuator.
acting_force_N``), head pressure = ``(F + p_r A_ann) / A_p`` with the rod-side law pressure
(0 when the law is off), strokes = ``s + F / k_out`` (``L2bForceActuator.stroke_true_m``). The
two-pressure sensor path of the controller (R6-P) reads them through ``measure_l2b``; wiring it
into the S6 runner is control ③ (python-expert / control-expert).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.chrono.l2b_model import L2bModel, read_l2b_probe
from outrigger_sim.chrono.snapshot import engine_info
from outrigger_sim.chrono.system import ChronoModel
from outrigger_sim.chrono.truth import ImuTruthSample, L1SensorTruth
from outrigger_sim.engine import AnalyticStart, EngineClosedError, EngineInfo, Snapshot
from outrigger_sim.sensors.averaging import PeriodAverage
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M
from outrigger_sim.signals import LEG_COUNT, Command, Measurements, TruthState

StepCallback = Callable[["L2bEngine"], None]


class _TruthView:
    """What ``L1SensorTruth`` reads from a model (IMU path only)."""

    def __init__(self, model: L2bModel) -> None:
        self.params = model.params
        self.system = model.system
        self.superstructure = model.superstructure
        self.sup_com_body_m = model.sup_com_body_m
        self.origin_in_cog_frame_ch = model.origin_in_cog_frame_ch
        self.motors = model.motors
        self.k_oil_N_m = np.full(LEG_COUNT, np.inf)
        self.rod_chamber = None


class L2bEngine:
    """Closed-loop engine around an :class:`L2bModel` (module docstring)."""

    def __init__(self, model: L2bModel, *, imu_mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
                 imu_method: str = "sensors_imu") -> None:
        self.model = model
        self.sensor_truth = L1SensorTruth(_TruthView(model), imu_mount_point_body_m,
                                          imu_method=imu_method)
        self._callback: StepCallback | None = None
        self._closed = False
        self._held = Command(t_s=self.time_s, leg_speed_m_s=model.actuator.reference.command_m_s)
        self._reset_monitor()
        model.actuator_hooks.insert(0, self._pre_actuator_hook)

    # --- SimEngine members ------------------------------------------------------------------

    @property
    def time_s(self) -> float:
        return float(self.model.system.GetChTime())

    @property
    def dt_s(self) -> float:
        return float(self.model.dt_s)

    @property
    def params_sha256(self) -> str:
        return self.model.params.sha256

    @property
    def info(self) -> EngineInfo:
        return engine_info(ChronoModel.L2B_NSC.value)

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def held_command(self) -> Command:
        return self._held

    def meta(self) -> dict[str, Any]:
        meta = self.model.meta()
        meta.update(engine="pychrono", model=ChronoModel.L2B_NSC.value,
                    params_sha256=self.model.params.sha256,
                    closed_loop_hook="step callback at the head of L2bModel.actuator_hooks")
        return meta

    def reset(self, start: AnalyticStart | Snapshot = AnalyticStart.ON_PADS) -> TruthState:
        self._check_open()
        if not isinstance(start, Snapshot):
            raise NotImplementedError("L2bEngine.reset takes a Snapshot; analytic starts are "
                                      "built with the L2bModel constructor")
        self.restore(start)
        self._reset_monitor()
        return self.truth()

    def step(self, *, capture: bool = False) -> float:
        self._check_open()
        self.model.step(capture=capture)
        return self.time_s

    def set_dt(self, dt_s: float) -> None:
        self._check_open()
        self.model.set_dt(dt_s)

    def apply_command(self, command: Command) -> None:
        self._check_open()
        if not isinstance(command, Command):
            raise TypeError(f"expected a Command, got {type(command).__name__}")
        self.model.set_command(command.leg_speed_m_s)
        self._held = command

    def measure_l2b(self) -> dict[str, NDArray[np.float64]]:
        """Ideal leg readings of the step just taken (module docstring)."""
        act = self.model.actuator
        f = act.acting_force_N
        s = np.array([m.GetMotorPos() for m in self.model.motors], dtype=float)
        p_r = (np.zeros(LEG_COUNT) if act.rod_side is None or not act.rod_side.armed
               else act.rod_side.rod_pressure_Pa)
        a_r = np.asarray(self.model.params.l2b.rod_side.annulus_area_m2, dtype=float)
        return {
            "cylinder_force_N": f,
            "rod_pressure_Pa": p_r,
            "head_pressure_Pa": (f + p_r * a_r) / act.head_area_m2,
            "stroke_m": act.stroke_true_m(s, f),
            "link_displacement_m": s,
        }

    def measure(self) -> Measurements:
        """Ideal measurements (instantaneous IMU; head-only pressure ``F / A_p`` and the
        piston stroke ``s + F / k_out`` through the L1 sensor-truth formulas). The rod-side
        pressures are in :meth:`measure_l2b` (two-pressure wiring is control ③)."""
        s = self.imu_sample()
        avg = PeriodAverage(s.t_s, s.specific_force_m_s2, s.angular_rate_rad_s, 1)
        leg = self.measure_l2b()
        return self.sensor_truth.ideal_measurements(
            avg, cylinder_force_N=leg["cylinder_force_N"], s_motor_m=leg["stroke_m"]
        )

    def imu_sample(self) -> ImuTruthSample:
        return self.sensor_truth.imu()

    def truth(self) -> TruthState:
        self._check_open()
        probe = self.model.last_probe
        if probe is None or probe.t_s != self.time_s:
            probe = read_l2b_probe(self.model)
        return self.model.truth(probe)

    def snapshot(self) -> Snapshot:
        self._check_open()
        return self.model.snapshot(held_command=self._held)

    def restore(self, snapshot: Snapshot) -> None:
        self._check_open()
        t = self.model.restore(snapshot)
        self._held = Command(t_s=t, leg_speed_m_s=self.model.actuator.reference.command_m_s)

    def close(self) -> None:
        if self._closed:
            return
        self._callback = None
        hooks = self.model.actuator_hooks
        if self._pre_actuator_hook in hooks:
            hooks.remove(self._pre_actuator_hook)
        self._closed = True

    # --- closed-loop extension ----------------------------------------------------------------

    def set_step_callback(self, callback: StepCallback | None) -> None:
        self._check_open()
        self._callback = callback

    def step_monitor(self) -> dict[str, Any]:
        return {
            "steps": self._mon_steps,
            "nonfinite_steps": self._mon_nonfinite,
            "first_nonfinite_t_s": self._mon_first_bad,
            "cylinder_force_max_N": self._f_max.tolist(),
            "cylinder_force_max_t_s": self._f_max_t.tolist(),
            "cylinder_force_min_N": self._f_min.tolist(),
            "cylinder_force_min_t_s": self._f_min_t.tolist(),
            "saturation_step_count": self.model.actuator.reference.saturation_step_count.tolist(),
        }

    def _reset_monitor(self) -> None:
        self._mon_steps = 0
        self._mon_nonfinite = 0
        self._mon_first_bad: float | None = None
        self._f_max = np.full(LEG_COUNT, -np.inf)
        self._f_max_t = np.full(LEG_COUNT, np.nan)
        self._f_min = np.full(LEG_COUNT, np.inf)
        self._f_min_t = np.full(LEG_COUNT, np.nan)

    def _pre_actuator_hook(self, model: L2bModel, dt_s: float) -> None:
        del dt_s
        t = self.time_s
        forces = model.actuator.acting_force_N
        pos = model.superstructure.GetPos()
        finite = bool(np.all(np.isfinite(forces))) and all(
            math.isfinite(c) for c in (pos.x, pos.y, pos.z))
        self._mon_steps += 1
        if not finite:
            self._mon_nonfinite += 1
            if self._mon_first_bad is None:
                self._mon_first_bad = t
        else:
            up = forces > self._f_max
            self._f_max = np.where(up, forces, self._f_max)
            self._f_max_t = np.where(up, t, self._f_max_t)
            down = forces < self._f_min
            self._f_min = np.where(down, forces, self._f_min)
            self._f_min_t = np.where(down, t, self._f_min_t)
        if self._callback is not None:
            self._callback(self)

    def _check_open(self) -> None:
        if self._closed:
            raise EngineClosedError("L2bEngine is closed")


__all__ = ["L2bEngine", "StepCallback"]
