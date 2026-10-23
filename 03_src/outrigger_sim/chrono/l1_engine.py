"""L1 Chrono model behind the engine-independent boundary (``SimEngine`` + closed-loop hooks).

``00_docs/03_chrono/chrono_build_plan.md`` 3.1-3.3, S6 (``runner``). :class:`L1Engine` wraps an
:class:`~outrigger_sim.chrono.model.L1Model` built with ``actuator=True`` and gives the
:mod:`outrigger_sim.runner` what it needs without the runner importing pychrono:

* :class:`outrigger_sim.engine.SimEngine` members (time, dt, info, meta, step, apply_command,
  measure, truth, snapshot, restore, close);
* the closed-loop extension of :class:`outrigger_sim.runner.ClosedLoopEngine`:
  :meth:`L1Engine.set_step_callback`, :meth:`L1Engine.imu_sample`,
  :meth:`L1Engine.ideal_measurements`, :meth:`L1Engine.step_monitor`.

**Where the controller runs** (hook order of ``L1Model.after_step``, ``dynamics_model.md``
4.6): the engine inserts its hook at the head of ``model.actuator_hooks``, i.e. after the state
copy (1), the ground-bushing hook (2) and the L1-R rod-chamber machine step (2b, so the sensor
truth of the callback is the machine output of the same step, ``chrono/rod_chamber_link``) and
**before** the actuator hook (3). The step
callback (the runner) therefore sees the final state of step ``n`` and a command it applies
there is integrated by the actuator hook of the same ``after_step``: the command issued at the
control instant ``t_n`` drives the motor segment of step ``n + 1`` (zero-order hold from
``t_n``; like every hook input it is loaded by Chrono with the one-step lag of
``input_lag_steps = 1``, which for the ramp motor function only delays the velocity term
``Ct``, ``chrono/actuators`` timing). ``apply_command`` between two steps (outside the
callback) is integrated by the hook of the next step (step ``n + 2``), as in
``chrono/runs.run_commanded``.

**State reads.** :meth:`L1Engine.truth` uses the state copy taken before the ground-bushing
hook of the step (R9) when the step was stepped with ``capture=True``; otherwise it copies the
state now (between steps the bushing anchors are those set for the next step).
:meth:`L1Engine.imu_sample` and the leg readings of :meth:`L1Engine.ideal_measurements` read
bodies and motors, which no hook changes between the end of a step and the next step.

**Per-step monitor** (:meth:`L1Engine.step_monitor`): every step the cylinder forces, motor
positions and the IMU-relevant body state are checked for non-finite values (V13), and the
per-leg extremes of the cylinder force with their times are kept (210 bar / 350 bar paths:
one-step peaks are invisible in 20 ms samples).

``reset(start)`` accepts a :class:`~outrigger_sim.engine.Snapshot` only and keeps the snapshot
time (the runner works from :attr:`L1Engine.time_s`); analytic starts are built by the scenario
code (``scenarios/settle``) when the model is constructed.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.chrono.model import L1Model
from outrigger_sim.chrono.probes import read_probe
from outrigger_sim.chrono.snapshot import engine_info
from outrigger_sim.chrono.system import ChronoModel
from outrigger_sim.chrono.truth import ImuTruthSample, L1SensorTruth
from outrigger_sim.engine import AnalyticStart, EngineClosedError, EngineInfo, Snapshot
from outrigger_sim.sensors.averaging import PeriodAverage
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M
from outrigger_sim.signals import LEG_COUNT, Command, Measurements, TruthState

StepCallback = Callable[["L1Engine"], None]


class L1Engine:
    """Closed-loop engine around an actuated :class:`L1Model` (module docstring).

    Args:
        model: Model built with ``actuator=True`` (force saturation as built).
        imu_mount_point_body_m: IMU point (body coordinates, m); default C1 (plan S6 risk 2).
        stroke_model: ``chrono.truth.STROKE_MODELS`` entry for ``stroke_corrected_m``.
        imu_method: ``chrono.truth.IMU_METHODS`` entry (per-step IMU truth path).
    """

    def __init__(
        self,
        model: L1Model,
        *,
        imu_mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
        stroke_model: str = "operating_point",
        imu_method: str = "sensors_imu",
    ) -> None:
        if model.actuator is None:
            raise ValueError("L1Engine needs a model built with actuator=True")
        self.model = model
        self.sensor_truth = L1SensorTruth(
            model, imu_mount_point_body_m, stroke_model=stroke_model, imu_method=imu_method
        )
        self._callback: StepCallback | None = None
        self._closed = False
        self._held = Command(
            t_s=float(model.system.GetChTime()), leg_speed_m_s=model.actuator.command_m_s
        )
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
        return engine_info(ChronoModel.L1.value)

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def rod_chamber(self) -> Any:
        """The model's L1-R link (``chrono.rod_chamber_link.L1RodChamber``): its ``machine``
        is the only owner of the rod-chamber state; ``last_step`` is the output of the latest
        engine step (sensor sources read it, ``step_observers`` are told of every step)."""
        return self.model.rod_chamber

    @property
    def held_command(self) -> Command:
        """Command the actuator integrates at the next hook."""
        return self._held

    def meta(self) -> dict[str, Any]:
        meta = self.model.meta()
        meta.update(
            engine="pychrono",
            model=ChronoModel.L1.value,
            params_sha256=self.model.params.sha256,
            sensor_truth=self.sensor_truth.meta(),
            closed_loop_hook=(
                "step callback at the head of L1Model.actuator_hooks (after state copy and "
                "ground bushing, before the actuator hook): command issued at t_n drives the "
                "segment of step n+1"
            ),
        )
        return meta

    def reset(self, start: AnalyticStart | Snapshot = AnalyticStart.ON_PADS) -> TruthState:
        """Restore a snapshot (time kept, module docstring); analytic starts are refused."""
        self._check_open()
        if not isinstance(start, Snapshot):
            raise NotImplementedError(
                "L1Engine.reset takes a Snapshot; build analytic starts with the L1Model pose"
            )
        self.restore(start)
        self._reset_monitor()
        return self.truth()

    def step(self, *, capture: bool = False) -> float:
        """One physics step (``L1Model.step``); ``capture`` keeps the R9 state copy for
        :meth:`truth`. Returns the time after the step."""
        self._check_open()
        self.model.step(capture=capture)
        return self.time_s

    def set_dt(self, dt_s: float) -> None:
        """Change the step size between two steps (``L1Model.set_dt``; runner ``dt_schedule``)."""
        self._check_open()
        self.model.set_dt(dt_s)

    def apply_command(self, command: Command) -> None:
        """Hold ``command`` (module docstring: inside the step callback it drives the next
        step, between steps the step after next)."""
        self._check_open()
        if not isinstance(command, Command):
            raise TypeError(f"expected a Command, got {type(command).__name__}")
        self.model.set_command(command.leg_speed_m_s)
        self._held = command

    def measure(self) -> Measurements:
        """Ideal measurements from the instantaneous IMU truth (no control-period average;
        the runner averages :meth:`imu_sample` over the period)."""
        s = self.imu_sample()
        avg = PeriodAverage(s.t_s, s.specific_force_m_s2, s.angular_rate_rad_s, 1)
        return self.sensor_truth.ideal_measurements(avg)

    def truth(self) -> TruthState:
        self._check_open()
        probe = self.model.last_probe
        if probe is None or probe.t_s != self.time_s:
            probe = read_probe(self.model)
        return self.model.truth(probe)

    def snapshot(self) -> Snapshot:
        self._check_open()
        return self.model.snapshot(held_command=self._held)

    def restore(self, snapshot: Snapshot) -> None:
        self._check_open()
        t = self.model.restore(snapshot)
        self._held = Command(t_s=t, leg_speed_m_s=self.model.actuator.command_m_s)

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
        """Call ``callback(engine)`` after every step, before the actuator hook (module
        docstring); None removes it."""
        self._check_open()
        self._callback = callback

    def imu_sample(self) -> ImuTruthSample:
        """IMU truth at the current state (mounting point of the engine)."""
        return self.sensor_truth.imu()

    def ideal_measurements(self, imu_average: PeriodAverage) -> Measurements:
        """Ideal measurements at the period end (``chrono.truth.L1SensorTruth``)."""
        return self.sensor_truth.ideal_measurements(imu_average)

    def step_monitor(self) -> dict[str, Any]:
        """Per-step extremes and non-finite count since construction / reset (JSON-ready)."""
        return {
            "steps": self._mon_steps,
            "nonfinite_steps": self._mon_nonfinite,
            "first_nonfinite_t_s": self._mon_first_bad,
            "cylinder_force_max_N": self._f_max.tolist(),
            "cylinder_force_max_t_s": self._f_max_t.tolist(),
            "cylinder_force_min_N": self._f_min.tolist(),
            "cylinder_force_min_t_s": self._f_min_t.tolist(),
            "saturation_step_count": self.model.actuator.saturation_step_count.tolist(),
        }

    def reset_step_monitor(self) -> None:
        self._reset_monitor()

    # --- internals ----------------------------------------------------------------------------

    def _reset_monitor(self) -> None:
        self._mon_steps = 0
        self._mon_nonfinite = 0
        self._mon_first_bad: float | None = None
        self._f_max = np.full(LEG_COUNT, -np.inf)
        self._f_max_t = np.full(LEG_COUNT, np.nan)
        self._f_min = np.full(LEG_COUNT, np.inf)
        self._f_min_t = np.full(LEG_COUNT, np.nan)

    def _pre_actuator_hook(self, model: L1Model, dt_s: float) -> None:
        del dt_s
        t = float(model.system.GetChTime())
        forces: NDArray[np.float64] = np.array(
            [m.GetMotorForce() for m in model.motors], dtype=float
        )
        pos = model.superstructure.GetPos()
        finite = bool(np.all(np.isfinite(forces))) and all(
            math.isfinite(c) for c in (pos.x, pos.y, pos.z)
        )
        self._mon_steps += 1
        if not finite:
            self._mon_nonfinite += 1
            if self._mon_first_bad is None:
                self._mon_first_bad = t
        else:
            up = forces > self._f_max
            if up.any():
                self._f_max = np.where(up, forces, self._f_max)
                self._f_max_t = np.where(up, t, self._f_max_t)
            down = forces < self._f_min
            if down.any():
                self._f_min = np.where(down, forces, self._f_min)
                self._f_min_t = np.where(down, t, self._f_min_t)
        if self._callback is not None:
            self._callback(self)

    def _check_open(self) -> None:
        if self._closed:
            raise EngineClosedError("L1Engine is closed")


__all__ = ["L1Engine", "StepCallback"]
