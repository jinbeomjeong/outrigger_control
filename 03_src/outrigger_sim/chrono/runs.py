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
