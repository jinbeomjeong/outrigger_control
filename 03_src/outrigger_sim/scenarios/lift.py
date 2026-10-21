"""S3 scenarios: lift from the crawler (V4) and single-leg steps (V5, V6, V9) (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` S3 (``scenarios/lift``, ``scenarios/leg_step``);
``dynamics_model.md`` 5 V4 / V5 / V6 / V9 and 5.6 (command ramp, V4 time origin).

**Lift (V4, revision 15 procedure).** ``t < 0``: legs at 0 on the crawler (S2b crawler settle
snapshot). Run time 0: all four motors get ``+v_max``. The command ramp ``T_r`` (0 -> ``v_max``
in ``T_r``) makes the position ``v_max (t - T_r / 2)`` after the ramp, so the **equivalent
start** (the step start with the same position) is ``T_r / 2`` after the start command; V4
touch and crawler-off times are measured from it. Every leg stops with the same ramp at its
operating extension ``e_op`` (``contact.rigid_floor.L1.derivation.operating_extension_m``):
the actuator's soft limit ``e_op`` makes it start braking at ``t_b = e_op / v_max`` (command
time; equivalent time ``e_op / v_max - T_r / 2``) and stop exactly on ``e_op`` at
``t_b + T_r``. "Last stop" is the latest of these stop times. After it the machine settles
``LIFT_SETTLE_AFTER_LAST_STOP_S`` (15 s, V4 residual check) plus three first-rocking periods
(the V1 / V3 / V9 mean window).

**Transition window** (``simulation.dt_transition_s``, CLAUDE.md '시뮬레이션 시간 간격'):
from ``TRANSITION_LEAD_S`` before the earliest reference touch to ``TRANSITION_TAIL_S`` after the
last stop, both shifted by ``T_r / 2`` (``dynamics_model.md`` 5.6) and widened to the
``TRANSITION_GRID_S`` grid so that the edges lie on every coarse time grid. The window edges
are an ASSUMPTION of the plan (S3 lift).

**Leg steps.** One leg moves at a constant speed towards a soft limit (exact ramped stop),
from a settled state on the pads (S1 snapshot).

Units SI; times in s of run time (0 = run start = start command) unless named ``*_eq``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.scenarios.stroke import Schedule, Segment

LIFT_SETTLE_AFTER_LAST_STOP_S = 15.0
"""V4: residual rocking amplitude is judged 15 s after the last stop (dynamics_model.md 5 V4)."""

MEAN_WINDOW_PERIODS = 3
"""V1 / V3 / V9: means over the last three first-rocking periods."""

TRANSITION_LEAD_S = 0.1
"""Transition window starts this long before the earliest reference touch (plan S3)."""

TRANSITION_TAIL_S = 0.3
"""Transition window ends this long after the last stop (plan S3)."""

TRANSITION_GRID_S = 0.01
"""Window edges are rounded outwards to this grid (multiple of 1e-4 / 2e-4 / 20 ms...)."""

COMMAND_PERIOD_S = 0.02
"""Control-period grid on which the lift command changes (open-loop replay at 20 ms ZOH,
CLAUDE.md control period assumption)."""


@dataclass(frozen=True)
class LiftPlan:
    """Lift schedule of one run (module docstring)."""

    v_max_m_s: float
    ramp_s: float
    e_op_m: tuple[float, float, float, float]
    brake_start_s: tuple[float, float, float, float]
    """``e_op / v_max`` per leg (command time)."""
    stop_s: tuple[float, float, float, float]
    """``brake_start + ramp`` per leg (command time): exact stop on ``e_op``."""
    last_stop_s: float
    equivalent_origin_s: float
    """``ramp / 2``: V4 times are measured from here (``*_eq``)."""
    transition_window_s: tuple[float, float]
    command_zero_s: float
    """Command set back to 0 here (on the control grid, after every stop)."""
    end_s: float
    rocking_period_s: float
    mean_window_s: tuple[float, float]
    """V1 / V3 means: the last ``MEAN_WINDOW_PERIODS`` rocking periods of the run."""
    residual_window_s: tuple[float, float]
    """One rocking period starting ``LIFT_SETTLE_AFTER_LAST_STOP_S`` after the last stop."""
    reference_touch_eq_s: tuple[float, float, float, float]
    notes: dict[str, str] = field(default_factory=dict)

    def schedule(self) -> Schedule:
        v = self.v_max_m_s
        return Schedule(
            [Segment(0.0, (v, v, v, v)), Segment(self.command_zero_s, (0.0, 0.0, 0.0, 0.0))],
            end_s=self.end_s,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "v_max_m_s": self.v_max_m_s,
            "ramp_s": self.ramp_s,
            "e_op_m": list(self.e_op_m),
            "brake_start_s": list(self.brake_start_s),
            "stop_s": list(self.stop_s),
            "last_stop_s": self.last_stop_s,
            "equivalent_origin_s": self.equivalent_origin_s,
            "transition_window_s": list(self.transition_window_s),
            "command_zero_s": self.command_zero_s,
            "end_s": self.end_s,
            "rocking_period_s": self.rocking_period_s,
            "mean_window_s": list(self.mean_window_s),
            "residual_window_s": list(self.residual_window_s),
            "reference_touch_eq_s": list(self.reference_touch_eq_s),
            "notes": dict(self.notes),
            "leg_order": list(LEG_ORDER),
        }


def _floor_to(x: float, grid: float) -> float:
    return math.floor(x / grid + 1e-9) * grid


def _ceil_to(x: float, grid: float) -> float:
    return math.ceil(x / grid - 1e-9) * grid


def lift_plan(
    params: Params,
    *,
    ramp_s: float | None = None,
    reference_touch_eq_s: Sequence[float],
    first_rocking_Hz: float,
) -> LiftPlan:
    """Lift plan from the YAML (``actuator.max_speed_m_s``, ``contact.rigid_floor.L1.
    derivation.operating_extension_m``), the command ramp and the V4 reference touch times
    (equivalent-origin times, ``dynamic_events_s / touch_s``) of the layout being run.

    Args:
        ramp_s: Command ramp ``T_r``; None = YAML ``actuator.command_ramp_s`` (the equivalent
            origin ``T_r / 2`` and the stop times follow from it).
        first_rocking_Hz: First rocking frequency on the pads (V7 / rev. 13 reference) for the
            mean and residual windows.
    """
    if ramp_s is None:
        ramp_s = float(params.actuator.command_ramp_s)
    v = float(params.actuator.max_speed_m_s)
    e_op = tuple(float(e) for e in params.contact.rigid_floor.L1.operating_extension_m)
    if len(e_op) != len(LEG_ORDER):
        raise ValueError(f"need {len(LEG_ORDER)} operating extensions, got {e_op}")
    touch = tuple(float(t) for t in reference_touch_eq_s)
    if len(touch) != len(LEG_ORDER):
        raise ValueError(f"need {len(LEG_ORDER)} reference touch times, got {touch}")
    brake = tuple(e / v for e in e_op)
    stop = tuple(b + ramp_s for b in brake)
    last = max(stop)
    t_eq = 0.5 * ramp_s
    w0 = _floor_to(min(touch) + t_eq - TRANSITION_LEAD_S, TRANSITION_GRID_S)
    w1 = _ceil_to(last + TRANSITION_TAIL_S, TRANSITION_GRID_S)
    zero = _ceil_to(w1, COMMAND_PERIOD_S)
    period = 1.0 / float(first_rocking_Hz)
    r0 = last + LIFT_SETTLE_AFTER_LAST_STOP_S
    end = _ceil_to(r0 + MEAN_WINDOW_PERIODS * period, TRANSITION_GRID_S)
    return LiftPlan(
        v_max_m_s=v,
        ramp_s=float(ramp_s),
        e_op_m=e_op,  # type: ignore[arg-type]
        brake_start_s=brake,  # type: ignore[arg-type]
        stop_s=stop,  # type: ignore[arg-type]
        last_stop_s=last,
        equivalent_origin_s=t_eq,
        transition_window_s=(w0, w1),
        command_zero_s=zero,
        end_s=end,
        rocking_period_s=period,
        mean_window_s=(end - MEAN_WINDOW_PERIODS * period, end),
        residual_window_s=(r0, r0 + period),
        reference_touch_eq_s=touch,  # type: ignore[arg-type]
        notes={
            "stop": "ramped brake to the soft limit e_op (exact), braking from e_op / v_max",
            "window": "ASSUMPTION (plan S3): earliest reference touch - 0.1 s .. last stop + "
            "0.3 s, shifted by ramp / 2, rounded outwards to 0.01 s",
        },
    )


def equivalent_origin_from_trajectory(
    t_s: Sequence[float],
    s_ref_m: Sequence[float],
    v_max_m_s: float,
    t_from_s: float,
    t_to_s: float,
) -> float:
    """Measured equivalent start ``t - s / v_max`` averaged over samples in ``[t_from, t_to]``
    (constant-speed phase; every leg moves alike before its stop). Run-time seconds."""
    t = np.asarray(t_s, dtype=float)
    s = np.asarray(s_ref_m, dtype=float)
    mask = (t >= t_from_s) & (t <= t_to_s)
    if not np.any(mask):
        raise ValueError(f"no samples in [{t_from_s}, {t_to_s}]")
    return float(np.mean(t[mask] - s[mask] / v_max_m_s))


@dataclass(frozen=True)
class LegStep:
    """One leg moved at ``speed_m_s`` by ``delta_m`` (sign = direction) with a soft-limit stop.

    ``hold_before_s`` of zero command first (baseline window), then the move, then
    ``hold_after_s``. The move takes ``|delta| / |speed|`` (+ the ramp, which costs nothing in
    distance with a symmetric start and stop).
    """

    name: str
    leg: int
    speed_m_s: float
    delta_m: float
    hold_before_s: float
    hold_after_s: float
    transition_from_delta_m: float | None = None
    """|delta| from which the transition dt is used (lift-off part of V6); None = never."""

    @property
    def move_s(self) -> float:
        return abs(self.delta_m) / abs(self.speed_m_s)

    def command(self) -> tuple[float, float, float, float]:
        c = [0.0, 0.0, 0.0, 0.0]
        c[self.leg] = math.copysign(abs(self.speed_m_s), self.delta_m)
        return (c[0], c[1], c[2], c[3])

    def soft_limits(
        self, s0_m: Sequence[float], stroke_range_m: Sequence[Sequence[float]]
    ) -> tuple[list[float], list[float]]:
        """``(lo, hi)`` per leg: the moving leg is limited to ``s0 + delta``, the others keep
        the stroke range."""
        lo = [float(r[0]) for r in stroke_range_m]
        hi = [float(r[1]) for r in stroke_range_m]
        target = float(s0_m[self.leg]) + self.delta_m
        if self.delta_m >= 0.0:
            hi[self.leg] = target
        else:
            lo[self.leg] = target
        return lo, hi

    def schedule(self, ramp_s: float) -> Schedule:
        zero = (0.0, 0.0, 0.0, 0.0)
        t_move_end = self.hold_before_s + self.move_s + ramp_s
        return Schedule(
            [Segment(0.0, zero), Segment(self.hold_before_s, self.command())],
            end_s=t_move_end + self.hold_after_s,
        )

    def end_s(self, ramp_s: float) -> float:
        return self.hold_before_s + self.move_s + ramp_s + self.hold_after_s

    def transition_window_s(self, ramp_s: float) -> tuple[float, float] | None:
        if self.transition_from_delta_m is None:
            return None
        t0 = self.hold_before_s + abs(self.transition_from_delta_m) / abs(self.speed_m_s)
        return (_floor_to(t0, TRANSITION_GRID_S), _ceil_to(self.end_s(ramp_s), TRANSITION_GRID_S))

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "leg": LEG_ORDER[self.leg],
            "speed_m_s": self.speed_m_s,
            "delta_m": self.delta_m,
            "hold_before_s": self.hold_before_s,
            "hold_after_s": self.hold_after_s,
            "move_s": self.move_s,
            "transition_from_delta_m": self.transition_from_delta_m,
        }


def crossing(
    x: Sequence[float], y: Sequence[float], level: float, *, falling: bool
) -> float | None:
    """First ``x`` where ``y`` crosses ``level`` (linear interpolation between samples)."""
    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)
    hit = np.flatnonzero(yy <= level) if falling else np.flatnonzero(yy >= level)
    if not hit.size:
        return None
    k = int(hit[0])
    if k == 0:
        return float(xx[0])
    y0, y1 = yy[k - 1], yy[k]
    if y1 == y0:
        return float(xx[k])
    return float(xx[k - 1] + (level - y0) * (xx[k] - xx[k - 1]) / (y1 - y0))
