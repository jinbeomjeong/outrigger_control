"""S2b actuator scenarios: legs in the air (V0 motor sign, V11) and the touch / lift event test.

``00_docs/03_chrono/chrono_build_plan.md`` S2b (``scenarios/stroke``), R4, R15;
``dynamics_model.md`` 5 (V0 motor sign, V11), 4.6 ruling 3. Engine independent: start poses
and piecewise-constant command schedules; the engine runs them.

* **Air** (:func:`air_pose`): superstructure held fixed (the engine fixes the body) high
  enough that the pads stay :data:`AIR_CLEARANCE_M` above the floor at full stroke; no
  contact, so the motor reaction is the rod weight plus the rod inertia force.
* **V11 schedule** (:data:`V11_SEGMENTS`): commands beyond ``v_max`` and beyond the stroke
  ends in both directions, long enough for a full stroke 0 -> 0.68 m and back.
* **Event test** (:func:`event_schedule`): the machine settled on the crawler (analytic
  pose, ``scenarios/crawler_settle``), one leg starts ``start_gap_m`` above its touch
  extension and is driven down (touch, ground bushing created), held, up (lift-off, bushing
  removed), held and down again (re-touch). Times are fixed so that runs at dt 1e-4 s and
  1e-5 s are comparable (R15 tuning, ``dynamics_model.md`` 4.6 ruling 3).

The schedules are ASSUMPTIONS of this test (magnitudes and times), not machine data.
Units SI.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.geometry import pad_sphere_centre_body_m
from outrigger_sim.params import LEG_ORDER, Params

AIR_CLEARANCE_M = 0.5
"""Pad sphere bottom above the floor at full stroke in the air scenario [m]."""

BIG_SPEED_M_S = 1.0
"""'Large' speed command of V11 (44 x v_max) [m/s]."""


@dataclass(frozen=True)
class Segment:
    """Command held from ``t0_s`` on (until the next segment)."""

    t0_s: float
    leg_speed_m_s: tuple[float, float, float, float]


class Schedule:
    """Piecewise-constant command schedule; ``schedule(t)`` returns a new command when a
    segment starts (None otherwise), suitable for ``chrono/runs.run_commanded``."""

    def __init__(self, segments: Sequence[Segment], end_s: float) -> None:
        if not segments or segments[0].t0_s != 0.0:
            raise ValueError("the first segment must start at t = 0")
        times = [s.t0_s for s in segments]
        if any(b <= a for a, b in zip(times, times[1:], strict=False)) or end_s <= times[-1]:
            raise ValueError(f"segment times must increase and end before {end_s}: {times}")
        self.segments = tuple(segments)
        self.end_s = float(end_s)
        self._t_origin: float | None = None
        self._next = 0

    def reset(self) -> None:
        self._t_origin = None
        self._next = 0

    def __call__(self, t_s: float) -> NDArray[np.float64] | None:
        if self._t_origin is None:
            self._t_origin = float(t_s)
        rel = t_s - self._t_origin
        out = None
        # half-step guard so a segment starts at the step whose start time is its t0
        while self._next < len(self.segments) and rel >= self.segments[self._next].t0_s - 1e-9:
            out = np.asarray(self.segments[self._next].leg_speed_m_s, dtype=float)
            self._next += 1
        return out

    def command_at(self, rel_t_s: float) -> NDArray[np.float64]:
        """Held command at time ``rel_t_s`` after the start (for plots and checks)."""
        current = self.segments[0]
        for seg in self.segments:
            if rel_t_s >= seg.t0_s:
                current = seg
        return np.asarray(current.leg_speed_m_s, dtype=float)

    def as_dict(self) -> dict[str, object]:
        return {
            "end_s": self.end_s,
            "segments": [
                {"t0_s": s.t0_s, "leg_speed_m_s": list(s.leg_speed_m_s)} for s in self.segments
            ],
        }


def air_pose(params: Params, clearance_m: float = AIR_CLEARANCE_M) -> tuple[float, float, float]:
    """Level body origin such that every pad sphere bottom is ``clearance_m`` above the floor
    at the top of its stroke range."""
    lowest = []
    for i, leg in enumerate(params.legs):
        hi = float(leg.extension_range_m[1])
        centre = pad_sphere_centre_body_m(params, i, hi)
        lowest.append(centre[2] - leg.pad.swivel_center_above_pad_bottom_m)
    z = params.ground.crawler_bottom_z_m + clearance_m - min(lowest)
    return (0.0, 0.0, float(z))


def v11_schedule(params: Params) -> Schedule:
    """V11: big and exact-``v_max`` commands, beyond both stroke ends (``dynamics_model.md`` 5
    V11; 'large speed, beyond the end').

    0 s: FL +1 m/s, FR +v_max, RL +2 v_max, RR -1 m/s (already at 0, must stay).
    31 s: FL -1 m/s, FR -v_max, RL -2 v_max, RR +1 m/s. End 62 s.
    Every leg makes one full stroke (0 -> hi or hi -> 0) per half and is pushed against the
    end for about 0.9 s.
    """
    v = params.actuator.max_speed_m_s
    big = BIG_SPEED_M_S
    return Schedule(
        [
            Segment(0.0, (big, v, 2.0 * v, -big)),
            Segment(31.0, (-big, -v, -2.0 * v, big)),
        ],
        end_s=62.0,
    )


def sign_test_schedule(params: Params) -> Schedule:
    """V0 motor sign: +v_max on every leg for 1 s, then 0 (ramped stop) for 0.2 s."""
    v = params.actuator.max_speed_m_s
    return Schedule([Segment(0.0, (v, v, v, v)), Segment(1.0, (0.0, 0.0, 0.0, 0.0))], 1.2)


def expected_full_stroke_time_s(params: Params, ramp_s: float | None = None) -> float:
    """0 -> hi from rest to rest with the acceleration ramp: ``stroke / v_max + ramp`` (the
    ramp-up and the braking each cost ``ramp / 2``); ``ramp_s`` None = YAML
    ``actuator.command_ramp_s``."""
    ramp = params.actuator.command_ramp_s if ramp_s is None else float(ramp_s)
    return params.actuator.stroke_m / params.actuator.max_speed_m_s + ramp


@dataclass(frozen=True)
class EventCase:
    """One touch / lift / re-touch test (module docstring)."""

    name: str
    leg: int
    speed_m_s: float
    start_gap_m: float
    down_s: float
    hold_s: float
    up_s: float
    down2_s: float
    tail_s: float

    def schedule(self) -> Schedule:
        zero = (0.0, 0.0, 0.0, 0.0)

        def leg_cmd(u: float) -> tuple[float, float, float, float]:
            c = [0.0, 0.0, 0.0, 0.0]
            c[self.leg] = u
            return (c[0], c[1], c[2], c[3])

        t1 = self.down_s
        t2 = t1 + self.hold_s
        t3 = t2 + self.up_s
        t4 = t3 + self.hold_s
        t5 = t4 + self.down2_s
        return Schedule(
            [
                Segment(0.0, leg_cmd(self.speed_m_s)),
                Segment(t1, zero),
                Segment(t2, leg_cmd(-self.speed_m_s)),
                Segment(t3, zero),
                Segment(t4, leg_cmd(self.speed_m_s)),
                Segment(t5, zero),
            ],
            end_s=t5 + self.tail_s,
        )

    @property
    def leg_name(self) -> str:
        return LEG_ORDER[self.leg]

    def expected_events(self) -> list[tuple[int, int]]:
        """(leg, kind) in order: create, remove, create (R15 kinds 1 / 2)."""
        return [(self.leg, 1), (self.leg, 2), (self.leg, 1)]


def event_cases(params: Params) -> tuple[EventCase, ...]:
    """Fast (v_max) and slow (1 mm/s) FL cases (ASSUMPTION: test magnitudes).

    fast: 2 mm gap, down 0.5 s (about 8 mm past touch), hold 0.3 s, up 0.8 s (about 18 mm),
    down 0.7 s, tail 0.5 s; slow: 0.5 mm gap, down 3 s (2.5 mm past touch), up 4 s, down 3 s.
    """
    v = params.actuator.max_speed_m_s
    return (
        EventCase("fast_FL", 0, v, 2.0e-3, 0.5, 0.3, 0.8, 0.7, 0.5),
        EventCase("slow_FL", 0, 1.0e-3, 0.5e-3, 3.0, 0.3, 4.0, 3.0, 0.5),
    )


def lift_time_check(
    t_first_nonpositive_s: float, t_removed_s: float, lift_time_s: float, dt_s: float
) -> float:
    """Removal delay after the first ``N <= 0`` step minus the expected ``(n_lift - 1) dt``
    (0 when the R15 rule acted as designed) [s]."""
    n_lift = max(1, math.ceil(lift_time_s / dt_s * (1.0 - 1e-9)))
    return (t_removed_s - t_first_nonpositive_s) - (n_lift - 1) * dt_s
