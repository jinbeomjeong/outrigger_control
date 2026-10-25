"""L2b-NSC Chrono model behind the engine-independent boundary (``SimEngine`` + closed-loop hooks).

Same structure as :class:`outrigger_sim.chrono.l1_engine.L1Engine` (plan 3.1-3.3): the engine's
hook sits at the head of :attr:`L2bModel.actuator_hooks` (after the state copy and the lateral
bushing hook, before the force-law hook), so a command applied inside the step callback drives
the reference of step ``n + 1``; between steps it is used from step ``n + 2``.

Measurements (ideal; :meth:`L2bEngine.ideal_measurements`, the runner's closed-loop member,
S7 control ③ preparation 2026-10-24). Same definitions as the L1-R sensor truth
(``chrono/truth.L1SensorTruth`` with the rod-chamber machine):

* IMU: :class:`outrigger_sim.chrono.truth.L1SensorTruth` (kinematics only, engine independent);
* cylinder force ``F`` = the force-law value that acted in the step just taken
  (``L2bForceActuator.acting_force_N``; the hook computed it from the state at ``t_{n-1}``);
* head pressure ``p_h = (F + p_r A_ann) / A_p`` and rod pressure ``p_r`` = the rod-side law
  pressure of the same hook call (two sensors, R6-P net force ``p_h A_p - p_r A_ann = F``);
  S8-A1 (``dynamics_model.md`` 5.26.10): ``p_h`` has a floor (return back pressure 2 bar g while
  the leg moves, the rod-side cavitation floor when locked) and ``p_r`` is re-solved from ``F``
  where it binds (``L2bForceActuator.pressure_split``; net force unchanged);
  with the rod-side law off: ``p_h = F / A_p`` and ``rod_pressure_Pa`` None (L1 mechanics-off
  convention). ``p_r`` and ``F`` are one physics step (1e-4 s) older than the kinematics, the
  same for every leg (negligible at 10 Hz);
* ``stroke_m`` = ``s_ref`` (the oil-volume coordinate the stroke limiter clips; = the L1 motor
  position, which is the L1 ``s_ref``);
* ``stroke_corrected_m`` = the piston-to-head stroke ``s + F / k_out``
  (``L2bForceActuator.stroke_true_m``; L1: ``s_motor - F / k_oil``, the same quantity of the
  cylinder-internal sensor).

Truth contact forces (:meth:`L2bEngine.truth`, Record ``F_contact_n``, ``F_crawler``): trailing
mean over ``contact_window_s`` (default 20 ms) of every step, the 5.22.3 read-out rule. On the
rigid NSC crawler single steps can carry zero crawler force (position jitter, the body leaves
the floor for a step), which the S6 judge would read as the crawler lift-off.
"""

from __future__ import annotations

import dataclasses
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

CONTACT_WINDOW_S = 0.020
"""Default trailing window of the truth contact forces (dynamics_model.md 5.22.3, >= 20 ms)."""


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
                 imu_method: str = "sensors_imu",
                 contact_window_s: float | None = CONTACT_WINDOW_S) -> None:
        self.model = model
        self.sensor_truth = L1SensorTruth(_TruthView(model), imu_mount_point_body_m,
                                          imu_method=imu_method)
        self._callback: StepCallback | None = None
        self._closed = False
        # 5.22.3: truth contact forces as a trailing window mean of every step (None = raw)
        self.contact_window_s = None if contact_window_s is None else float(contact_window_s)
        self._cwin = (0 if contact_window_s is None
                      else max(1, round(float(contact_window_s) / float(model.dt_s))))
        self._cbuf = np.zeros((max(self._cwin, 1), LEG_COUNT + 1, 3))
        self._cn = 0
        self._ci = 0
        self._held = Command(t_s=self.time_s, leg_speed_m_s=model.actuator.reference.command_m_s)
        self.pressure_floor_samples = np.zeros(LEG_COUNT, dtype=np.int64)
        """Measurement calls (per leg) whose head pressure hit the S8-A1 floor."""
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
                    sensor_truth=self.sensor_meta(),
                    truth_contact=self.contact_window_meta(),
                    closed_loop_hook="step callback at the head of L2bModel.actuator_hooks "
                                     "(after the lateral-bushing hook, before the force-law "
                                     "hook): command issued at t_n drives step n+1")
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
        # S8 (C-6): pressure force F - f and the piston stroke s_p; = F and s + F / k_out on the
        # S7 path (seal friction level 0, pilot check), bit-identical
        f = act.acting_pressure_force_N
        s = np.array([m.GetMotorPos() for m in self.model.motors], dtype=float)
        p_r = (np.zeros(LEG_COUNT) if act.rod_side is None or not act.rod_side.armed
               else act.rod_side.rod_pressure_Pa)
        # S8-A1: head-side floor (return 2 bar g moving, cavitation floor locked); u = the speed
        # that acted in the step just taken (this runs before the force-law hook)
        p_h, p_r, hit = act.pressure_split(f, p_r, act.reference.u_applied_m_s)
        self.pressure_floor_samples += hit
        return {
            "cylinder_force_N": f,
            "rod_pressure_Pa": p_r,
            "head_pressure_Pa": p_h,
            "stroke_m": act.stroke_sensor_true_m(s),
            "actual_force_N": act.acting_force_N,
            "link_displacement_m": s,
        }

    def measure(self) -> Measurements:
        """Ideal measurements with the instantaneous IMU (the runner averages
        :meth:`imu_sample` over the period; module docstring for the leg readings)."""
        s = self.imu_sample()
        avg = PeriodAverage(s.t_s, s.specific_force_m_s2, s.angular_rate_rad_s, 1)
        return self.ideal_measurements(avg)

    def ideal_measurements(self, imu_average: PeriodAverage) -> Measurements:
        """Ideal measurements at the period end ``imu_average.t_s`` (= now; module docstring)."""
        t_now = self.time_s
        if abs(t_now - imu_average.t_s) > 1e-9 * max(1.0, abs(t_now)):
            raise ValueError(f"measurement at {imu_average.t_s!r} s but the model is at "
                             f"{t_now!r} s")
        leg = self.measure_l2b()
        act = self.model.actuator
        rod_on = act.rod_side is not None
        return Measurements(
            t_s=imu_average.t_s,
            specific_force_m_s2=imu_average.specific_force_m_s2,
            angular_rate_rad_s=imu_average.angular_rate_rad_s,
            head_pressure_Pa=leg["head_pressure_Pa"],
            stroke_m=act.reference.s_ref_m,
            stroke_corrected_m=leg["stroke_m"],
            rod_pressure_Pa=leg["rod_pressure_Pa"] if rod_on else None,
        )

    @property
    def rod_chamber(self) -> None:
        """No L1-R link (the rod side is inside the L2b force law)."""
        return None

    def sensor_meta(self) -> dict[str, Any]:
        """Leg-reading definitions for the run meta (module docstring)."""
        act = self.model.actuator
        return {
            **self.sensor_truth.meta(),
            "pressure": ("p_h = max(floor, (F + p_r A_ann) / A_p), p_r = rod-side law pressure of "
                         "the same hook, re-solved (p_h A_p - F) / A_ann where the floor binds "
                         "(S8-A1: floor = return 2 bar g while moving, rod-side cavitation floor "
                         "locked; two sensors)" if act.rod_side is not None
                         else "p_h = F / A_p, no rod-side sensor"),
            "pressure_floor_enabled": act.pressure_floor_enabled,
            "cylinder_force": "pressure force F - f of the step (S8; = force-law value without "
                              "seal friction)",
            "stroke_m": "s_ref (oil-volume coordinate, = L1 motor position)",
            "stroke_corrected_m": ("piston state s_p (seal friction path)" if act.friction_path
                                   else "piston s + F / k_out (cylinder-internal sensor truth)"),
            "head_area_m2": act.head_area_m2.tolist(),
            "k_oil_N_m": None,
            "stroke_model": "piston s + F / k_out",
        }

    def imu_sample(self) -> ImuTruthSample:
        return self.sensor_truth.imu()

    def truth(self) -> TruthState:
        """Truth of the current state; with ``contact_window_s`` the pad and crawler contact
        forces are the trailing mean over that window of every step (5.22.3: the single-step
        NSC contact force is noise; a 1-step airborne jitter would read as a lift-off)."""
        self._check_open()
        probe = self.model.last_probe
        if probe is None or probe.t_s != self.time_s:
            probe = read_l2b_probe(self.model)
        state = self.model.truth(probe)
        if self._cwin == 0 or self._cn == 0:
            return state
        mean = self._cbuf[: self._cn].mean(axis=0)
        n = np.asarray(probe.floor_normal_world, dtype=float)
        pads = mean[:LEG_COUNT]
        fn = pads @ n
        return dataclasses.replace(
            state, F_contact_n_N=fn, F_contact_t_N=(pads - np.outer(fn, n))[:, :2],
            is_pad_in_contact=fn > 0.0, F_crawler_N=mean[LEG_COUNT].copy())

    def contact_window_meta(self) -> dict[str, Any]:
        return {"contact_window_s": self.contact_window_s, "contact_window_steps": self._cwin,
                "rule": "TruthState pad / crawler contact forces = trailing mean of every step "
                        "over the window (dynamics_model.md 5.22.3); raw when None"}

    def snapshot(self) -> Snapshot:
        self._check_open()
        return self.model.snapshot(held_command=self._held)

    def restore(self, snapshot: Snapshot) -> None:
        self._check_open()
        t = self.model.restore(snapshot)
        self._held = Command(t_s=t, leg_speed_m_s=self.model.actuator.reference.command_m_s)
        self._clear_contact_window()

    def _clear_contact_window(self) -> None:
        """Drop the contact-force window so ``truth()`` after a restore (and so after
        ``reset``) never averages steps from before the restored state; until the first
        post-restore step it returns the raw probe forces."""
        self._cbuf[:] = 0.0
        self._cn = 0
        self._ci = 0

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
            "pressure_floor_measurements": self.pressure_floor_samples.tolist(),
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
        if self._cwin:
            row = self._cbuf[self._ci]
            for i, leg in enumerate(model.legs):
                c = leg.GetContactForce()
                row[i, 0], row[i, 1], row[i, 2] = c.x, c.y, c.z
            c = model.superstructure.GetContactForce()
            row[LEG_COUNT, 0], row[LEG_COUNT, 1], row[LEG_COUNT, 2] = c.x, c.y, c.z
            self._ci = (self._ci + 1) % self._cwin
            self._cn = min(self._cn + 1, self._cwin)
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


__all__ = ["CONTACT_WINDOW_S", "L2bEngine", "StepCallback"]
