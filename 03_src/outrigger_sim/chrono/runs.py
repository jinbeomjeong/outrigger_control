"""Chrono run loops of S2a: free vibration after an initial velocity, gravity-ramp statics.

``00_docs/03_chrono/chrono_build_plan.md`` S2a; ``dynamics_model.md`` 5 (V7, V12, V13), 4.5,
4.6. The loops step an :class:`~outrigger_sim.chrono.model.L1Model` with its fixed hook
order (``L1Model.after_step``) and collect copied samples (R9) into a :class:`Series`.

* :func:`set_rigid_velocity` adds a rigid-body velocity field (``v + omega x (p - point)``)
  to every non-fixed body, so the locked legs move with the superstructure and the motor
  constraints see a consistent velocity (no impulsive constraint correction).
* :func:`run_free_vibration` (V7): steps a given time and samples every ``sample_s``.
* :func:`run_gravity_ramp` (V12): sets the gravity ``g * ramp(t_n + dt)`` before each step n
  (step n integrates from ``t_n`` to ``t_{n+1}``). Like every hook input, a gravity change
  made between steps acts one step later (pychrono 10.0.0, measured 2026-10-20 with a free
  body: the body gravity force is loaded in the Update at the end of a step), except on the
  first step after a structural change; so the ramp is delayed by one step (1e-4 s on a
  3 s ramp). ``gravity_scale`` in the series is the value set before the sampled step.
  With ``hold_deadline_s`` (the ramp duration) the ground-bushing initial hold is checked
  once the run time reaches it: a leg still held raises
  :class:`~outrigger_sim.chrono.ground_bushing.HoldNotReleasedError` (run invalid,
  ``dynamics_model.md`` 5.3 ruling 1 condition 2).

Units SI, world frame Z-up. Contact counts per leg come from ``ReportContactCallback``
(``chrono/contact.report_contacts``) every ``contact_check_s``.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.contact import report_contacts
from outrigger_sim.chrono.ground_bushing import BushingEvent
from outrigger_sim.chrono.probes import ProbeState
from outrigger_sim.chrono.system import set_gravity

SampleHook = Callable[[ProbeState], None]


def set_rigid_velocity(
    model: Any,
    v_point_world: Sequence[float],
    omega_world: Sequence[float],
    point_world: Sequence[float],
) -> None:
    """Add the rigid velocity field ``v + omega x (p - point)`` to every body of ``model``.

    ``model.bodies`` = superstructure and the four leg moving parts (all Chrono COG frames).
    """
    v = np.asarray(v_point_world, dtype=float)
    w = np.asarray(omega_world, dtype=float)
    c = np.asarray(point_world, dtype=float)
    for body in model.bodies:
        p = body.GetPos()
        r = np.array([p.x, p.y, p.z]) - c
        dv = v + np.cross(w, r)
        old_v = body.GetPosDt()
        old_w = body.GetAngVelParent()
        body.SetPosDt(ch.ChVector3d(old_v.x + dv[0], old_v.y + dv[1], old_v.z + dv[2]))
        body.SetAngVelParent(ch.ChVector3d(old_w.x + w[0], old_w.y + w[1], old_w.z + w[2]))


@dataclass
class Series:
    """Copied samples of one run (lists while running, numpy arrays from :meth:`arrays`)."""

    rows: dict[str, list[Any]] = field(
        default_factory=lambda: {
            k: []
            for k in (
                "t",
                "origin",
                "quat",
                "vel",
                "omega",
                "pad_contact_world",
                "bushing_force_world",
                "normal",
                "penetration",
                "motor_force",
                "motor_violation",
                "crawler_force",
                "n_contacts",
                "cb_count",
                "bushing_disp",
                "gravity_scale",
            )
        }
    )

    def add(
        self,
        model: Any,
        probe: ProbeState,
        *,
        contacts: bool,
        gravity_scale: float,
    ) -> None:
        r = self.rows
        r["t"].append(probe.t_s)
        r["origin"].append(probe.body_pos_m)
        r["quat"].append(probe.body_quat_wxyz)
        r["vel"].append(probe.body_vel_m_s)
        r["omega"].append(probe.body_omega_rad_s)
        r["pad_contact_world"].append(probe.pad_contact_world_N)
        r["bushing_force_world"].append(probe.bushing_force_world_N)
        r["normal"].append(probe.pad_normal_force_N)
        r["penetration"].append(probe.penetration_m)
        r["motor_force"].append(probe.motor_force_N)
        r["motor_violation"].append(float(np.abs(probe.leg_offset_in_body_m).max()))
        r["crawler_force"].append(probe.crawler_contact_world_N)
        r["n_contacts"].append(probe.n_contacts)
        if contacts:
            report = report_contacts(model.system, model.body_names)
            r["cb_count"].append(report.count.copy())
        else:
            r["cb_count"].append(np.full(len(model.body_names), -1, dtype=np.int64))
        # geometric in-plane deformation (anchors as set for the next step; static: same)
        r["bushing_disp"].append(model.bushing.tangential_displacement_m())
        r["gravity_scale"].append(gravity_scale)

    def arrays(self) -> dict[str, NDArray[Any]]:
        return {k: np.asarray(v) for k, v in self.rows.items()}


@dataclass
class RunResult:
    """Output of the run loops."""

    series: dict[str, NDArray[Any]]
    events: list[BushingEvent]
    steps: int
    wall_s: float
    t_start_s: float
    t_end_s: float


def _step_loop(
    model: Any,
    n_steps: int,
    *,
    sample_every: Callable[[int], int],
    contact_every: int,
    before_step: Callable[[float], float] | None,
    on_sample: SampleHook | None,
    after_step: Callable[[float], None] | None = None,
) -> RunResult:
    series = Series()
    events: list[BushingEvent] = []
    t_start = float(model.system.GetChTime())
    scale = 1.0
    t0 = time.perf_counter()
    for k in range(1, n_steps + 1):
        if before_step is not None:
            scale = before_step(float(model.system.GetChTime()))
        every = sample_every(k)
        capture = k % every == 0
        result = model.step(capture=capture)
        if after_step is not None:
            after_step(float(model.system.GetChTime()))
        events.extend(result.events)
        if result.probe is not None:
            if on_sample is not None:
                on_sample(result.probe)
            series.add(model, result.probe, contacts=(k % contact_every == 0), gravity_scale=scale)
    wall = time.perf_counter() - t0
    return RunResult(
        series=series.arrays(),
        events=events,
        steps=n_steps,
        wall_s=wall,
        t_start_s=t_start,
        t_end_s=float(model.system.GetChTime()),
    )


def run_free_vibration(
    model: Any,
    duration_s: float,
    *,
    sample_s: float = 1.0e-3,
    contact_check_s: float = 1.0e-2,
    on_sample: SampleHook | None = None,
) -> RunResult:
    """Step ``duration_s`` from the current state (no input), sampling every ``sample_s``."""
    dt = model.dt_s
    every = max(1, round(sample_s / dt))
    contact_every = max(every, round(contact_check_s / dt))
    return _step_loop(
        model,
        round(duration_s / dt),
        sample_every=lambda _k: every,
        contact_every=contact_every,
        before_step=None,
        on_sample=on_sample,
    )


CommandFn = Callable[[float], "Sequence[float] | NDArray[np.float64] | None"]
"""``command(t_n)`` -> leg speeds held from now on (None = keep the held command)."""

COMMANDED_FIELDS = (
    "t",
    "origin",
    "quat",
    "omega",
    "motor_pos",
    "motor_vel",
    "motor_force",
    "s_ref",
    "u_applied",
    "u_cmd",
    "pad_normal",
    "pad_in_contact",
    "crawler_force",
    "motor_violation",
    "n_contacts",
)


@dataclass
class CommandedRun:
    """Output of :func:`run_commanded` (sampled series + per-step contact transitions)."""

    series: dict[str, NDArray[Any]]
    events: list[BushingEvent]
    raw_contact_transitions: list[tuple[float, int, int]]
    """Every step at which ``N_raw > 0`` of a pad changed: ``(t, leg, 1 on / 0 off)``."""
    first_positive_N_t_s: NDArray[np.float64]
    """Per leg, first step time with ``N_raw > 0`` (NaN if never)."""
    steps: int
    wall_s: float
    t_start_s: float
    t_end_s: float
    max_motor_speed_m_s: NDArray[np.float64]
    """Per leg max ``|GetMotorPosDt()|`` over every step (not only the samples)."""
    max_motor_violation_m: float
    """Max over every step of ``|motor position - acting target|`` (axial constraint)."""
    motor_pos_min_m: NDArray[np.float64]
    motor_pos_max_m: NDArray[np.float64]
    """Per leg extreme motor positions over every step."""
    max_force_dev_N: NDArray[np.float64] | None
    """Per leg max ``|GetMotorForce() - force_ref_N|`` over every step (None: not tracked)."""
    max_pad_normal_N: NDArray[np.float64] | None = None
    """Per leg max of the hook's raw pad normal force over every step (S3)."""
    max_pad_normal_t_s: NDArray[np.float64] | None = None
    """Time of :attr:`max_pad_normal_N` per leg."""
    max_motor_force_N: NDArray[np.float64] | None = None
    """Per leg max ``GetMotorForce()`` (cylinder force, + = pushing the pad down) over every
    step (S3 V4 upper bound)."""
    max_motor_force_t_s: NDArray[np.float64] | None = None
    dt_segments: list[tuple[float, float, float]] | None = None
    """``(t_start, t_end, dt)`` of each fixed-dt segment, absolute times (run_windowed)."""


def run_commanded(
    model: Any,
    duration_s: float,
    command: CommandFn,
    *,
    sample_s: float = 1.0e-3,
    on_sample: SampleHook | None = None,
    force_ref_N: Sequence[float] | None = None,
) -> CommandedRun:
    """Step an actuator model (``L1Model(actuator=True)``) for ``duration_s``.

    Before each step (time ``t_n``) ``command(t_n)`` may set a new held command; the actuator
    hook after the step integrates it (so a command set at ``t_n`` moves the motor target
    from step ``n + 2`` on, ``chrono/actuators`` timing). Every step the pad normal forces of
    the ground-bushing hook (``normal_force_raw_N``), the motor speeds and the axial motor
    constraint violation are checked; samples (state copies, R9) every ``sample_s``.
    With ``force_ref_N`` the largest motor-force deviation from it is tracked every step
    (one-step inertial spikes are invisible in the samples).
    """
    dt = model.dt_s
    n_steps = round(duration_s / dt)
    every = max(1, round(sample_s / dt))
    rows: dict[str, list[Any]] = {k: [] for k in COMMANDED_FIELDS}
    events: list[BushingEvent] = []
    n_legs = len(model.motors)
    positive = model.bushing.normal_force_raw_N > 0.0
    first_pos = np.full(n_legs, np.nan)
    transitions: list[tuple[float, int, int]] = []
    vmax = np.zeros(n_legs)
    pmin = np.full(n_legs, np.inf)
    pmax = np.full(n_legs, -np.inf)
    viol_max = 0.0
    f_ref = None if force_ref_N is None else [float(f) for f in force_ref_N]
    f_dev = np.zeros(n_legs)
    n_max = np.full(n_legs, -np.inf)
    n_max_t = np.full(n_legs, np.nan)
    fm_max = np.full(n_legs, -np.inf)
    fm_max_t = np.full(n_legs, np.nan)
    motors = model.motors
    t_start = float(model.system.GetChTime())
    t0 = time.perf_counter()
    for k in range(1, n_steps + 1):
        u = command(float(model.system.GetChTime()))
        if u is not None:
            model.set_command(u)
        result = model.step(capture=(k % every == 0))
        events.extend(result.events)
        t_now = float(model.system.GetChTime())
        n_raw = model.bushing.normal_force_raw_N
        pos_now = n_raw > 0.0
        changed = np.flatnonzero(pos_now != positive)
        for leg in changed:
            transitions.append((t_now, int(leg), int(pos_now[leg])))
            if pos_now[leg] and np.isnan(first_pos[leg]):
                first_pos[leg] = t_now
        positive = pos_now
        higher = n_raw > n_max
        if np.any(higher):
            n_max = np.where(higher, n_raw, n_max)
            n_max_t = np.where(higher, t_now, n_max_t)
        acting = model.actuator.acting_s_ref_m
        for i, m in enumerate(motors):
            fm = m.GetMotorForce()
            if fm > fm_max[i]:
                fm_max[i] = fm
                fm_max_t[i] = t_now
            v = abs(m.GetMotorPosDt())
            if v > vmax[i]:
                vmax[i] = v
            pos = m.GetMotorPos()
            if pos < pmin[i]:
                pmin[i] = pos
            if pos > pmax[i]:
                pmax[i] = pos
            dev = abs(pos - acting[i])
            if dev > viol_max:
                viol_max = dev
            if f_ref is not None:
                fd = abs(fm - f_ref[i])
                if fd > f_dev[i]:
                    f_dev[i] = fd
        probe = result.probe
        if probe is None:
            continue
        if on_sample is not None:
            on_sample(probe)
        rows["t"].append(probe.t_s)
        rows["origin"].append(probe.body_pos_m)
        rows["quat"].append(probe.body_quat_wxyz)
        rows["omega"].append(probe.body_omega_rad_s)
        rows["motor_pos"].append(probe.motor_pos_m)
        rows["motor_vel"].append(np.array([m.GetMotorPosDt() for m in motors]))
        rows["motor_force"].append(probe.motor_force_N)
        rows["s_ref"].append(acting)
        rows["u_applied"].append(model.actuator.acting_u_m_s)
        rows["u_cmd"].append(model.actuator.command_m_s)
        rows["pad_normal"].append(probe.pad_normal_force_N)
        rows["pad_in_contact"].append(probe.bushing_in_contact)
        rows["crawler_force"].append(probe.crawler_contact_world_N)
        rows["motor_violation"].append(float(np.abs(probe.leg_offset_in_body_m).max()))
        rows["n_contacts"].append(probe.n_contacts)
    wall = time.perf_counter() - t0
    return CommandedRun(
        series={k: np.asarray(v) for k, v in rows.items()},
        events=events,
        raw_contact_transitions=transitions,
        first_positive_N_t_s=first_pos,
        steps=n_steps,
        wall_s=wall,
        t_start_s=t_start,
        t_end_s=float(model.system.GetChTime()),
        max_motor_speed_m_s=vmax,
        max_motor_violation_m=viol_max,
        motor_pos_min_m=pmin,
        motor_pos_max_m=pmax,
        max_force_dev_N=None if f_ref is None else f_dev,
        max_pad_normal_N=n_max,
        max_pad_normal_t_s=n_max_t,
        max_motor_force_N=fm_max,
        max_motor_force_t_s=fm_max_t,
        dt_segments=[(t_start, float(model.system.GetChTime()), float(dt))],
    )


@dataclass(frozen=True)
class DtWindow:
    """A time-step window of :func:`run_windowed`: ``dt_s`` from ``t0_s`` to ``t1_s`` (run
    time, i.e. seconds after the run start)."""

    t0_s: float
    t1_s: float
    dt_s: float
    sample_s: float | None = None
    """Sample period inside the window (None: the run's ``sample_s``)."""


def _merge_max(a: NDArray | None, ta: NDArray | None, b: NDArray | None, tb: NDArray | None):
    if a is None:
        return b, tb
    if b is None:
        return a, ta
    take_b = b > a
    return np.where(take_b, b, a), np.where(take_b, tb, ta)


def run_windowed(
    model: Any,
    duration_s: float,
    command: CommandFn,
    *,
    windows: Sequence[DtWindow] = (),
    base_dt_s: float | None = None,
    sample_s: float = 1.0e-3,
    on_sample: SampleHook | None = None,
    force_ref_N: Sequence[float] | None = None,
) -> CommandedRun:
    """:func:`run_commanded` with time-step windows (S3: ``simulation.dt_transition_s``
    inside the contact-transition window, the general ``dt`` elsewhere).

    The run is cut at the window edges; each piece runs at its own ``dt`` through
    :meth:`L1Model.set_dt` (target continuous across the change, ``chrono/actuators``
    module docstring: change ``dt`` only while the applied speeds are constant). The same
    ``command`` object is used for every piece, so a :class:`~outrigger_sim.scenarios.
    stroke.Schedule` keeps its time origin (the first call = run start). Piece lengths are
    rounded to their ``dt``; window edges should lie on the coarse grid.

    Args:
        windows: Non-overlapping windows in increasing order inside ``[0, duration_s]``.
        base_dt_s: ``dt`` outside the windows (default: the model's current ``dt_s``).

    Returns:
        The merged :class:`CommandedRun` (series concatenated, maxima over all pieces,
        :attr:`CommandedRun.dt_segments` lists the pieces).
    """
    base = float(model.dt_s if base_dt_s is None else base_dt_s)
    pieces: list[tuple[float, float, float, float]] = []
    t = 0.0
    for w in sorted(windows, key=lambda w: w.t0_s):
        if w.t0_s < t - 1e-12 or w.t1_s <= w.t0_s or w.t1_s > duration_s + 1e-12:
            raise ValueError(f"window {w} overlaps, is empty or ends after {duration_s} s")
        if w.t0_s > t:
            pieces.append((t, w.t0_s, base, sample_s))
        pieces.append((w.t0_s, w.t1_s, w.dt_s, sample_s if w.sample_s is None else w.sample_s))
        t = w.t1_s
    if duration_s > t + 1e-12:
        pieces.append((t, duration_s, base, sample_s))

    merged: CommandedRun | None = None
    t_run0 = float(model.system.GetChTime())
    for t0, t1, dt, smp in pieces:
        model.set_dt(dt)
        # cut by the remaining run time so that rounding errors do not accumulate
        elapsed = float(model.system.GetChTime()) - t_run0
        part = run_commanded(
            model,
            round((t1 - elapsed) / dt) * dt,
            command,
            sample_s=smp,
            on_sample=on_sample,
            force_ref_N=force_ref_N,
        )
        if merged is None:
            merged = part
            continue
        series = {}
        for k, a in merged.series.items():
            b = part.series[k]
            series[k] = np.concatenate([a, b]) if (a.size and b.size) else (a if a.size else b)
        first = np.where(
            np.isnan(merged.first_positive_N_t_s), part.first_positive_N_t_s,
            merged.first_positive_N_t_s,
        )
        n_max, n_max_t = _merge_max(
            merged.max_pad_normal_N, merged.max_pad_normal_t_s,
            part.max_pad_normal_N, part.max_pad_normal_t_s,
        )
        f_max, f_max_t = _merge_max(
            merged.max_motor_force_N, merged.max_motor_force_t_s,
            part.max_motor_force_N, part.max_motor_force_t_s,
        )
        merged = CommandedRun(
            series=series,
            events=[*merged.events, *part.events],
            raw_contact_transitions=[
                *merged.raw_contact_transitions, *part.raw_contact_transitions
            ],
            first_positive_N_t_s=first,
            steps=merged.steps + part.steps,
            wall_s=merged.wall_s + part.wall_s,
            t_start_s=merged.t_start_s,
            t_end_s=part.t_end_s,
            max_motor_speed_m_s=np.maximum(merged.max_motor_speed_m_s, part.max_motor_speed_m_s),
            max_motor_violation_m=max(merged.max_motor_violation_m, part.max_motor_violation_m),
            motor_pos_min_m=np.minimum(merged.motor_pos_min_m, part.motor_pos_min_m),
            motor_pos_max_m=np.maximum(merged.motor_pos_max_m, part.motor_pos_max_m),
            max_force_dev_N=None
            if merged.max_force_dev_N is None
            else np.maximum(merged.max_force_dev_N, part.max_force_dev_N),
            max_pad_normal_N=n_max,
            max_pad_normal_t_s=n_max_t,
            max_motor_force_N=f_max,
            max_motor_force_t_s=f_max_t,
            dt_segments=[*(merged.dt_segments or []), *(part.dt_segments or [])],
        )
    if merged is None:
        raise ValueError(f"empty run: duration {duration_s} s")
    model.set_dt(base)
    return merged


def run_gravity_ramp(
    model: Any,
    gravity_full_m_s2: Sequence[float],
    ramp: Callable[[float], float],
    total_s: float,
    *,
    fine_from_s: float,
    coarse_sample_s: float = 1.0e-2,
    fine_sample_s: float = 1.0e-3,
    contact_check_s: float = 1.0e-2,
    on_sample: SampleHook | None = None,
    hold_deadline_s: float | None = None,
) -> RunResult:
    """Gravity ``g_full * ramp(t)`` from the model's current time (taken as t = 0 of the ramp).

    Samples every ``coarse_sample_s`` before ``fine_from_s`` (ramp time) and every
    ``fine_sample_s`` from then on; contact counts every ``contact_check_s``.

    Args:
        hold_deadline_s: Ramp time by which every ground-bushing initial hold must be
            released (pass the ramp duration). After the first step that ends at or after it,
            ``model.bushing.assert_hold_released`` is called once. None: not checked.

    Raises:
        HoldNotReleasedError: A leg is still held at ``hold_deadline_s``.
    """
    dt = model.dt_s
    g = np.asarray(gravity_full_m_s2, dtype=float)
    t_origin = float(model.system.GetChTime())
    coarse = max(1, round(coarse_sample_s / dt))
    fine = max(1, round(fine_sample_s / dt))
    contact_every = max(fine, round(contact_check_s / dt))
    k_fine = round(fine_from_s / dt)
    deadline = math.inf if hold_deadline_s is None else float(hold_deadline_s)
    hold_checked = hold_deadline_s is None

    def after(t_now: float) -> None:
        nonlocal hold_checked
        if not hold_checked and t_now - t_origin >= deadline - 0.5 * dt:
            hold_checked = True
            model.bushing.assert_hold_released(f"at the end of the gravity ramp ({deadline} s)")

    def before(t_now: float) -> float:
        scale = ramp(t_now + dt - t_origin)
        set_gravity(model.system, tuple(float(v) for v in g * scale))
        return scale

    return _step_loop(
        model,
        round(total_s / dt),
        sample_every=lambda k: fine if k > k_fine else coarse,
        contact_every=contact_every,
        before_step=before,
        on_sample=on_sample,
        after_step=None if hold_deadline_s is None else after,
    )
