"""Closed-loop runner: zero-order hold of the controller command (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` 3.1 (``runner``), 3.3 (controller boundary), 3.5,
S6 (``runner``: control-period zero-order hold; risks 1-3; 6 #24). This module never imports a
physics engine. The engine side is :class:`ClosedLoopEngine` (Chrono:
:class:`outrigger_sim.chrono.l1_engine.L1Engine`).

Loop (:func:`run_closed_loop`), per physics step ``n`` (time ``t_n``):

1. the engine steps and calls the runner's step callback with the final state of step ``n``
   (Chrono: after the state copy and the ground-bushing hook, before the actuator hook);
2. the runner adds the IMU truth of the step (:meth:`ClosedLoopEngine.imu_sample`, ideal, at
   the engine's mounting point) to :class:`~outrigger_sim.sensors.averaging.ControlPeriodAverager`
   (user decision 2026-10-20 (1): the IMU input is the control-period time average);
3. when the sample closes a control period (every ``T / dt`` steps, ``T`` =
   ``controller.period_s``, default 20 ms):

   a. ideal measurements at ``t_n`` (averaged IMU, instantaneous pressures and strokes,
      :meth:`ClosedLoopEngine.ideal_measurements`);
   b. :class:`~outrigger_sim.sensors.suite.SensorSuite` applies every sensor error;
   c. ``controller.update(measurements)`` - **the controller gets the** :class:`Measurements`
      **object only** (plan S6 risk 1; the runner checks the type and never hands over the
      engine, the truth or the ideal values);
   d. the Record row at ``t_n``: truth of step ``n``, the command that was held during step
      ``n`` (Record ``u_cmd`` = input that acted during the step, as ``u_applied``) and the
      delivered measurements (``meas.*``);
   e. the new command is applied (zero-order hold): it drives the actuator from step
      ``n + 1`` (Chrono: the actuator hook right after the callback; ``input_lag_steps`` 1
      unchanged, see ``chrono/l1_engine``).

Options (S6 control matrix, ``00_docs/04_control/s6_control_spec.md`` 4 and 6):

* ``command_delay_periods`` = d: the command issued at ``t_k`` is applied at ``t_{k+d}``
  (zero speed until then); d = 1 reproduces the reduced model's "ZOH + 1 step" (one control
  period, 20 ms). Default 0 (report the runs as "delay 0"). Record ``u_cmd`` is the applied
  (acting) command; :attr:`ClosedLoopResult.command_m_s` holds the issued ones.
* ``step_hook(engine)``: called every physics step inside the step callback, before the control
  logic (per-step bookkeeping, e.g. :class:`outrigger_sim.chrono.pad_record.PadRecorder`).
* ``capture_every_steps`` = m: also keep the engine's state copy every m steps (for a
  ``step_hook`` that reads ``engine.truth()`` / the probe at a finer rate than ``T``).
* ``on_control(measurements, command)``: observer after every update.
* ``dt_schedule`` (:class:`DtSchedule`, S6 RE1b-F / RE1b-P contact-transition windows,
  CLAUDE.md "접지 전환 해석 1e-5 s"): the step size may change during the run. The observer
  opens / closes a window at a control instant (:meth:`DtSchedule.open` /
  :meth:`DtSchedule.close`); the new ``dt`` acts from the next step (``engine.set_dt``
  between two steps, ``L1Model.set_dt`` re-times the pending actuator segment). The loop then
  runs on time instead of a step count: control instants are the averager's period ends (the
  IMU average is weighted by the step lengths), ``capture_every_s`` replaces
  ``capture_every_steps``. Every ``dt`` used must divide the control period. Without a
  schedule the loop is the fixed-step loop (bit-identical to the runs before this option).

Before the first control instant the held command is zero speed (``Command.stopped``). There
is no Record row at the start time (no averaged IMU value exists yet).

Placement: :func:`run_closed_loop` pins the process (``placement``, default ``"pcore"``:
P-cores + EcoQoS off, :func:`outrigger_sim.hostcpu.place_process`, plan 6 #24). Set
``OPENBLAS_NUM_THREADS=1`` before numpy loads when several runs share the P-cores.

Units SI; per-leg arrays in LEG_ORDER.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.control.protocol import Controller
from outrigger_sim.record import Record, Recorder
from outrigger_sim.sensors.averaging import ControlPeriodAverager, PeriodAverage
from outrigger_sim.sensors.suite import SensorSuite
from outrigger_sim.signals import LEG_COUNT, Command, Measurements, TruthState

PERIOD_STEP_REL_TOL = 1.0e-9
"""``T / dt`` must be an integer within this relative tolerance (zero-order hold on steps)."""


class RunnerError(RuntimeError):
    """The loop cannot run as specified (period not a multiple of dt, bad controller output,
    measurement time mismatch)."""


@runtime_checkable
class ClosedLoopEngine(Protocol):
    """Engine side of the closed loop (``SimEngine`` subset + step callback)."""

    @property
    def time_s(self) -> float: ...

    @property
    def dt_s(self) -> float: ...

    def meta(self) -> dict[str, Any]: ...

    def step(self, *, capture: bool = False) -> float:
        """One physics step; ``capture`` keeps the step's state copy for :meth:`truth`."""
        ...

    def apply_command(self, command: Command) -> None: ...

    def truth(self) -> TruthState: ...

    def set_step_callback(self, callback: Callable[[Any], None] | None) -> None:
        """Call ``callback(engine)`` after every step with the step's final state, before the
        actuator integrates the next segment."""
        ...

    def imu_sample(self) -> Any:
        """IMU truth at the current state: object with ``t_s``, ``specific_force_m_s2``,
        ``angular_rate_rad_s`` (sensor axes)."""
        ...

    def ideal_measurements(self, imu_average: PeriodAverage) -> Measurements:
        """Ideal measurements at ``imu_average.t_s`` (= current time)."""
        ...


@dataclass
class ClosedLoopResult:
    """What :func:`run_closed_loop` returns (arrays SI, LEG_ORDER).

    Attributes:
        record: Record of the control instants (truth + ``u_cmd`` + ``meas.*``), or None.
        command_t_s: Issue time of every controller command, shape (k,).
        command_m_s: The issued (controller output) leg speeds, shape (k, 4); applied
            ``command_delay_periods`` periods later.
        n_steps: Physics steps taken.
        n_control: Controller updates.
        steps_per_period: ``T / dt``.
        wall_s: Wall time of the loop (s).
        nonfinite_imu_steps: Steps whose IMU truth was not finite (V13).
        meta: Runner settings and placement (JSON-ready).
    """

    record: Record | None
    command_t_s: NDArray[np.float64]
    command_m_s: NDArray[np.float64]
    n_steps: int
    n_control: int
    steps_per_period: int
    wall_s: float
    nonfinite_imu_steps: int
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DtSegment:
    """One piece of a :class:`DtSchedule` (``t1_s`` None = still open)."""

    t0_s: float
    t1_s: float | None
    dt_s: float
    reason: str


class DtSchedule:
    """Step-size plan of one closed-loop run, changed by the scenario at control instants.

    Args:
        base_dt_s: ``dt`` outside the windows (normally the model's ``dt``).
        period_s: Control period; every ``dt`` must divide it (:func:`steps_per_period`).
    """

    def __init__(self, base_dt_s: float, period_s: float) -> None:
        steps_per_period(period_s, base_dt_s)
        self.base_dt_s = float(base_dt_s)
        self.period_s = float(period_s)
        self.dt_s = self.base_dt_s
        self.segments: list[DtSegment] = [DtSegment(math.nan, None, self.base_dt_s, "base")]
        self._started = False

    @property
    def is_open(self) -> bool:
        """A window (``dt`` other than the base) is in force."""
        return self.dt_s != self.base_dt_s

    def start(self, t_s: float) -> None:
        """Run start (called by the runner)."""
        if not self._started:
            self.segments[0] = DtSegment(float(t_s), None, self.base_dt_s, "base")
            self._started = True

    def _switch(self, t_s: float, dt_s: float, reason: str) -> None:
        last = self.segments[-1]
        self.segments[-1] = DtSegment(last.t0_s, float(t_s), last.dt_s, last.reason)
        self.segments.append(DtSegment(float(t_s), None, float(dt_s), reason))
        self.dt_s = float(dt_s)

    def open(self, t_s: float, dt_s: float, reason: str = "window") -> None:
        """Use ``dt_s`` from the next step on (call at a control instant)."""
        steps_per_period(self.period_s, dt_s)
        if self.is_open:
            raise RunnerError(f"dt window already open at {t_s!r} s")
        if dt_s != self.base_dt_s:
            self._switch(t_s, dt_s, reason)

    def close(self, t_s: float, reason: str = "close") -> None:
        """Back to the base ``dt`` from the next step on (no-op when no window is open)."""
        if self.is_open:
            self._switch(t_s, self.base_dt_s, reason)

    def finish(self, t_s: float) -> None:
        last = self.segments[-1]
        if last.t1_s is None:
            self.segments[-1] = DtSegment(last.t0_s, float(t_s), last.dt_s, last.reason)

    def to_meta(self) -> list[dict[str, Any]]:
        return [
            {"t0_s": s.t0_s, "t1_s": s.t1_s, "dt_s": s.dt_s, "reason": s.reason}
            for s in self.segments
        ]


def steps_per_period(period_s: float, dt_s: float) -> int:
    """``T / dt`` as an integer.

    Raises:
        RunnerError: Not an integer within :data:`PERIOD_STEP_REL_TOL`, or < 1.
    """
    ratio = float(period_s) / float(dt_s)
    n = round(ratio)
    if n < 1 or abs(ratio - n) > PERIOD_STEP_REL_TOL * ratio:
        raise RunnerError(f"control period {period_s!r} s is not a multiple of dt {dt_s!r} s")
    return n


def runner_meta(
    controller: Controller, sensors: SensorSuite, period_s: float, dt_s: float
) -> dict[str, Any]:
    """Runner part of the run meta (``record.make_run_meta(extra=...)``)."""
    return {
        "runner": "outrigger_sim.runner.run_closed_loop",
        "control_period_s": period_s,
        "steps_per_period": steps_per_period(period_s, dt_s),
        "zero_order_hold": "command applied at the control instant t_n drives step n+1 on",
        "record_u_cmd": "command held during the step ending at the sample time",
        "record_instants": "control instants only (no row at the start time)",
        "controller": controller.meta(),
        "sensors": dict(sensors.setup().config),
        "sensor_seed": sensors.seed,
    }


def run_closed_loop(
    engine: ClosedLoopEngine,
    controller: Controller,
    sensors: SensorSuite,
    duration_s: float,
    *,
    recorder: Recorder | None = None,
    run_meta: Mapping[str, Any] | None = None,
    placement: str | None = "pcore",
    on_control: Callable[[Measurements, Command], None] | None = None,
    command_delay_periods: int = 0,
    step_hook: Callable[[Any], None] | None = None,
    capture_every_steps: int | None = None,
    dt_schedule: DtSchedule | None = None,
    capture_every_s: float | None = None,
) -> ClosedLoopResult:
    """Run ``controller`` in closed loop for ``duration_s`` from the engine's current state.

    Args:
        engine: Closed-loop engine (module docstring).
        controller: Any :class:`~outrigger_sim.control.protocol.Controller`; reset here.
        sensors: Sensor errors; reset here. Its IMU sample period must equal the control
            period (noise ``sigma = density sqrt(1 / (2 T))``).
        duration_s: Simulated time; rounded to whole physics steps.
        recorder: Record target (rows appended at the control instants).
        run_meta: Without ``recorder``: run meta (``record.make_run_meta``) of a new recorder.
            Neither given = no Record.
        placement: ``hostcpu.place_process`` mode or None (no placement).
        on_control: Optional observer ``(measurements, command)`` after each update (for
            scenario bookkeeping; it gets the same delivered values as the controller).
        command_delay_periods: Extra command delay in control periods (module docstring).
        step_hook: Per-step callable ``step_hook(engine)`` (module docstring).
        capture_every_steps: Extra state-copy rate in steps for ``step_hook``.
        dt_schedule: Variable step size (module docstring); the engine needs ``set_dt``.
        capture_every_s: With ``dt_schedule``: extra state-copy rate in seconds.

    Raises:
        RunnerError: Period not a multiple of ``dt``, sensor period mismatch, a controller
            output that is not a :class:`Command` issued at the measurement time.
    """
    if not isinstance(controller, Controller):
        raise TypeError(f"{type(controller).__name__} does not follow the Controller protocol")
    dt = float(engine.dt_s)
    period = float(controller.period_s)
    n_period = steps_per_period(period, dt)
    sample_period = float(sensors.imu.config.sample_period_s)
    if abs(sample_period - period) > PERIOD_STEP_REL_TOL * period:
        raise RunnerError(
            f"IMU sample period {sample_period!r} s differs from the control period {period!r} s"
        )
    if not (duration_s > 0.0 and math.isfinite(duration_s)):
        raise ValueError(f"duration_s must be positive: {duration_s!r}")
    n_steps = round(duration_s / dt)
    is_int = isinstance(command_delay_periods, int) and not isinstance(command_delay_periods, bool)
    if not is_int or command_delay_periods < 0:
        raise ValueError(f"command_delay_periods must be an int >= 0: {command_delay_periods!r}")
    delay = int(command_delay_periods)
    if capture_every_steps is not None and capture_every_steps < 1:
        raise ValueError(f"capture_every_steps must be >= 1: {capture_every_steps!r}")

    placement_info: dict[str, Any] | None = None
    if placement is not None:
        from outrigger_sim.hostcpu import place_process

        placement_info = place_process(placement)

    if recorder is None and run_meta is not None:
        recorder = Recorder(run_meta)
    controller.reset()
    sensors.reset()
    t0 = float(engine.time_s)
    averager = ControlPeriodAverager(period, t0)
    held = Command.stopped(t0)
    engine.apply_command(held)
    cmd_t: list[float] = []
    cmd_u: list[NDArray[np.float64]] = []
    state = {"held": held, "nonfinite": 0, "updates": 0}
    queue: list[Command] = []

    def on_step(eng: Any) -> None:
        if step_hook is not None:
            step_hook(eng)
        sample = eng.imu_sample()
        force = np.asarray(sample.specific_force_m_s2, dtype=float)
        rate = np.asarray(sample.angular_rate_rad_s, dtype=float)
        if not (np.all(np.isfinite(force)) and np.all(np.isfinite(rate))):
            state["nonfinite"] += 1
            raise RunnerError(f"non-finite IMU truth at t = {sample.t_s!r} s")
        average = averager.add(sample.t_s, force, rate)
        if average is None:
            return
        ideal = eng.ideal_measurements(average)
        delivered = sensors.apply(ideal)
        if type(delivered) is not Measurements:
            raise RunnerError(f"sensors returned {type(delivered).__name__}, not Measurements")
        command = controller.update(delivered)  # Measurements only (plan S6 risk 1)
        if not isinstance(command, Command):
            raise RunnerError(f"controller returned {type(command).__name__}, not a Command")
        if command.t_s != delivered.t_s:
            raise RunnerError(
                f"command issued at {command.t_s!r} s for measurements at {delivered.t_s!r} s"
            )
        if recorder is not None:
            recorder.append(eng.truth(), state["held"], delivered)
        queue.append(command)
        if len(queue) > delay:
            issued = queue.pop(0)
            applied = Command(t_s=delivered.t_s, leg_speed_m_s=issued.leg_speed_m_s)
        else:
            applied = Command.stopped(delivered.t_s)
        eng.apply_command(applied)
        state["held"] = applied
        state["updates"] += 1
        cmd_t.append(command.t_s)
        cmd_u.append(np.array(command.leg_speed_m_s, dtype=float))
        if on_control is not None:
            on_control(delivered, command)

    engine.set_step_callback(on_step)
    wall0 = time.perf_counter()
    try:
        if dt_schedule is None:
            for k in range(1, n_steps + 1):
                capture = k % n_period == 0
                if capture_every_steps is not None and k % capture_every_steps == 0:
                    capture = True
                engine.step(capture=capture)
        else:
            n_steps = _run_scheduled(
                engine, dt_schedule, averager, t0, n_steps * dt, period, capture_every_s
            )
    finally:
        engine.set_step_callback(None)
    wall = time.perf_counter() - wall0
    expected_updates = (
        n_steps // n_period
        if dt_schedule is None
        else int(math.floor(round(duration_s / dt) * dt / period + 1e-9))
    )
    if state["updates"] != expected_updates:
        raise RunnerError(
            f"{state['updates']} controller updates for {n_steps} steps of {n_period} per period"
        )
    meta = runner_meta(controller, sensors, period, dt)
    meta.update(placement=placement_info, start_t_s=t0, n_steps=n_steps,
                command_delay_periods=delay,
                command_delay_note="delay 0" if delay == 0 else f"ZOH + {delay} control period(s)")
    if dt_schedule is not None:
        meta.update(dt_segments=dt_schedule.to_meta(), capture_every_s=capture_every_s)
    return ClosedLoopResult(
        record=None if recorder is None else recorder.finish(),
        command_t_s=np.asarray(cmd_t, dtype=float),
        command_m_s=np.asarray(cmd_u, dtype=float).reshape(-1, LEG_COUNT),
        n_steps=n_steps,
        n_control=int(state["updates"]),
        steps_per_period=n_period,
        wall_s=wall,
        nonfinite_imu_steps=int(state["nonfinite"]),
        meta=meta,
    )


def _run_scheduled(
    engine: Any,
    schedule: DtSchedule,
    averager: ControlPeriodAverager,
    t0: float,
    duration_s: float,
    period: float,
    capture_every_s: float | None,
) -> int:
    """Time-driven loop of :func:`run_closed_loop` with a :class:`DtSchedule`; step count."""
    if not hasattr(engine, "set_dt"):
        raise RunnerError(f"{type(engine).__name__} has no set_dt: no dt schedule possible")
    schedule.start(t0)
    t_end = t0 + duration_s
    steps = 0
    # next extra capture time: the first step ending at or after it captures (crossing rule;
    # the summed step times drift, an exact-grid test would stop matching)
    next_cap = None if capture_every_s is None else t0 + capture_every_s
    while True:
        t = float(engine.time_s)
        dt = schedule.dt_s
        if t >= t_end - 0.5 * min(dt, schedule.base_dt_s):
            break
        if dt != float(engine.dt_s):
            engine.set_dt(dt)
        t_next = t + dt
        capture = t_next >= averager.period_end_s - 1.0e-9 * period
        if next_cap is not None and t_next >= next_cap - 0.5 * dt:
            capture = True
            while next_cap <= t_next + 0.5 * dt:
                next_cap += capture_every_s
        engine.step(capture=capture)
        steps += 1
    if float(engine.dt_s) != schedule.base_dt_s:
        engine.set_dt(schedule.base_dt_s)
    schedule.finish(float(engine.time_s))
    return steps


__all__ = [
    "DtSchedule",
    "DtSegment",
    "ClosedLoopEngine",
    "ClosedLoopResult",
    "RunnerError",
    "run_closed_loop",
    "runner_meta",
    "steps_per_period",
]
