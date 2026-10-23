"""S2b checks: V0 (motor sign, crawler gaps), V11 (actuator limits), command ramp, R15 events,
crawler settle (V13 on the crawler) and the snapshot round trip.

``00_docs/03_chrono/chrono_build_plan.md`` S2b table; ``dynamics_model.md`` 5 (V0, V11, V13,
V0 crawler addendum), 4.5 item 1, 4.6 ruling 3. Engine independent: the inputs are numbers
the run script collected. Automatic pass / fail is a pre-check; the final physical judgement
is the dynamics-expert's.

V11 full-stroke time: the reference ``actuator.full_stroke_time_s`` is ``stroke / v_max``
without acceleration limits (33.454 s on the 0.70 m YAML). With the command ramp (user
decision 2026-10-20, YAML ``actuator.command_ramp_s`` since 2026-10-21) a stroke from rest
to rest takes ``ramp`` more (ramp-up and braking each cost ``ramp / 2``): the check uses
``stroke / v_max + ramp`` with the V11 tolerance and reports the difference to the reference
as a note.

V11 criteria (``dynamics_model.md`` 5.12.12; values for the 0.70 m YAML, v_max 20.924 mm/s,
ramp 0.1 s): speed <= v_max (1 + 1e-3) = 20.945 mm/s and v_max reached; position in
[-1e-4, 0.7001] m; rest-to-rest full stroke 33.554 +- 0.05 s; inertial reaction of the
hanging rod per leg over the whole run <= 9/8 m_rod a (1 + 1 %) = 25.388 N (FL, FR) /
17.395 N (RL, RR), m_rod a = 22.34 / 15.31 N (9/8: stroke-end braking last step, see
:data:`STROKE_END_LAST_STEP_FACTOR`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from outrigger_sim.params import LEG_ORDER
from outrigger_sim.verify.checks import (
    CheckResult,
    check_abs,
    check_equal,
    check_max,
)

V11_SPEED_REL_TOL = 1.0e-3
V11_POS_MIN_M = -1.0e-4
V11_POS_END_MARGIN_M = 1.0e-4
"""V11 position band ``[-1e-4, stroke + 1e-4]`` m (0.7001 m for the 0.70 m stroke)."""
V11_TIME_TOL_S = 0.05
V13_MOTOR_VIOLATION_M = 1.0e-6
V13_DRIFT_DEG = 1.0e-4
V13_FORCE_FRACTION_OF_QUARTER_WEIGHT = 1.0e-3
SIGN_POS_TOL_M = 1.0e-9
SPIKE_REL_TOL = 0.01
"""Inertial reaction ``m_rod a`` / ``m_rod dv / dt`` within this relative band."""
SPIKE_ABS_TOL_N = 1.0
STROKE_END_LAST_STEP_FACTOR = 9.0 / 8.0
"""Bound of the last speed change at a stroke end in units of ``a dt``: the discrete braking
cap leaves a fractional final step r and the end clip adds ``r (1 - r) / 2`` (max 1/8 at
r = 1/2), so ``|dv| <= (1 + 1/8) a dt`` (dynamics_model.md 5.12.12 supplement 8 Q1 (discrete
braking cap, max 1 + r(1-r)/2 = 9/8)). Only the whole V11 run
(stroke ends included) uses it; the air_short ramp check stays at ``m_rod a``."""
EVENT_TIME_DIFF_MAX_S = 1.0e-3
"""R15 tuning rule: event times of the dt 1e-4 s and 1e-5 s runs within 1 ms."""
SNAPSHOT_POS_TOL_M = 1.0e-12
CRAWLER_ACTIVE_SPHERES = 14
"""``dynamics_model.md`` 5 V0 addendum: 12 rollers + the first front end shoe per track."""
CRAWLER_POSE_TOL_MM = 1.0e-3
CRAWLER_POSE_TOL_DEG = 1.0e-4


def motor_sign_checks(
    pad_dz_m: ArrayLike, motor_ds_m: ArrayLike, hanging_force_N: ArrayLike, rod_weight_N: ArrayLike
) -> list[CheckResult]:
    """V0 / R4: +speed moves the pad down by the motor travel; the hanging rod pulls (F < 0).

    Args:
        pad_dz_m: World z change of each pad sphere centre after the +v_max second.
        motor_ds_m: Motor position change in the same time.
        hanging_force_N: Motor force at rest in the air (start).
        rod_weight_N: ``m_rod g`` per leg.
    """
    dz = np.asarray(pad_dz_m, dtype=float)
    ds = np.asarray(motor_ds_m, dtype=float)
    return [
        check_equal(
            "V0", "motor +speed moves the pad down (sign of dz)", np.sign(dz), -np.ones_like(dz)
        ),
        check_abs(
            "V0",
            "pad dz = -motor travel (link Z = body -z, R4)",
            dz,
            -ds,
            SIGN_POS_TOL_M,
            "m",
        ),
        check_abs(
            "V0",
            "motor reaction of a hanging rod = -m_rod g (+ pushes the pad down)",
            hanging_force_N,
            -np.asarray(rod_weight_N, dtype=float),
            SPIKE_ABS_TOL_N,
            "N",
        ),
    ]


def v11_position_max_m(stroke_m: float) -> float:
    """Upper end of the V11 position band for the YAML stroke."""
    return float(stroke_m) + V11_POS_END_MARGIN_M


def v11_stroke_time_key(leg: str, stroke_m: float, *, is_extending: bool) -> str:
    """``"<leg> 0->0.70"`` / ``"<leg> 0.70->0"`` (stroke printed with 2 decimals)."""
    end = f"{stroke_m:.2f}"
    return f"{leg} 0->{end}" if is_extending else f"{leg} {end}->0"


def v11_checks(
    *,
    v_max: float,
    max_speed_per_leg: ArrayLike,
    commanded_at_least_vmax: Sequence[bool],
    pos_min: ArrayLike,
    pos_max: ArrayLike,
    stroke_times_s: Mapping[str, float],
    expected_time_s: float,
    reference_time_s: float,
    motor_violation_max_m: float,
    stroke_m: float,
    rod_force_dev_N: ArrayLike | None = None,
    ramp_force_N: ArrayLike | None = None,
) -> list[CheckResult]:
    """V11 (legs in the air, superstructure fixed).

    Args:
        max_speed_per_leg: Per-step max ``|ds/dt|`` per leg over the whole run.
        commanded_at_least_vmax: Legs that got ``|u| >= v_max`` (must reach v_max).
        pos_min / pos_max: Per-step extremes of the motor position.
        stroke_times_s: :func:`v11_stroke_time_key` -> measured time.
        stroke_m: YAML ``actuator.stroke_m`` (upper end of the position band).
        expected_time_s: ``stroke / v_max + ramp``.
        reference_time_s: ``actuator.full_stroke_time_s`` (no ramp).
        rod_force_dev_N: Per-step max ``|F_motor + m_rod g|`` per leg (whole run, stroke
            ends included); judged per leg against ``9/8 ramp_force_N (1 + 1 %)``.
        ramp_force_N: ``m_rod v_max / ramp`` per leg in :data:`LEG_ORDER` (front and rear
            moving parts differ), or one value for every leg.
    """
    pos_max_limit = v11_position_max_m(stroke_m)
    vmax_meas = np.asarray(max_speed_per_leg, dtype=float)
    reach = [float(v) for v, c in zip(vmax_meas, commanded_at_least_vmax, strict=True) if c]
    times = np.array(list(stroke_times_s.values()), dtype=float)
    return [
        check_max(
            "V11",
            "speed <= v_max (1 + 1e-3), every step",
            vmax_meas,
            v_max * (1.0 + V11_SPEED_REL_TOL),
            "m/s",
        ),
        check_abs(
            "V11",
            "speed reaches v_max (ramp motion function, plan: ChFunctionConst)",
            reach,
            [v_max] * len(reach),
            v_max * V11_SPEED_REL_TOL,
            "m/s",
        ),
        check_equal(
            "V11",
            f"position within [{V11_POS_MIN_M:g}, {pos_max_limit:.4f}] m, every step",
            bool(np.min(pos_min) >= V11_POS_MIN_M and np.max(pos_max) <= pos_max_limit),
            True,
            note=f"min {float(np.min(pos_min))!r}, max {float(np.max(pos_max))!r}",
        ),
        check_abs(
            "V11",
            "full stroke time (rest to rest) = stroke / v_max + ramp",
            times,
            [expected_time_s] * len(times),
            V11_TIME_TOL_S,
            "s",
            note=(
                f"keys {list(stroke_times_s)}; reference actuator.full_stroke_time_s "
                f"{reference_time_s} s has no ramp: measured - reference = "
                f"{(times - reference_time_s).round(4).tolist()} s"
            ),
        ),
        check_max(
            "V13",
            "axial motor constraint |s_motor - acting target|, every step",
            motor_violation_max_m,
            V13_MOTOR_VIOLATION_M,
            "m",
        ),
    ] + (
        []
        if rod_force_dev_N is None or ramp_force_N is None
        else _inertial_reaction_checks(rod_force_dev_N, ramp_force_N)
    )


def _inertial_reaction_checks(
    rod_force_dev_N: ArrayLike, ramp_force_N: ArrayLike
) -> list[CheckResult]:
    """One check per leg: ``max |F_motor + m_rod g| <= 9/8 m_rod a (1 + 1 %)`` (V11 ruling).

    The whole V11 run includes the stroke-end braking, whose last step may change the speed
    by up to 9/8 ``a dt`` (:data:`STROKE_END_LAST_STEP_FACTOR`).
    """
    deviation_N = np.asarray(rod_force_dev_N, dtype=float)
    expected_N = np.broadcast_to(np.asarray(ramp_force_N, dtype=float), deviation_N.shape)
    return [
        check_max(
            "ramp",
            f"{leg}: no inertial spike: max |F_motor + m_rod g| <= 9/8 m_rod a (1 %), "
            "whole V11 run",
            leg_deviation_N,
            STROKE_END_LAST_STEP_FACTOR * leg_expected_N * (1.0 + SPIKE_REL_TOL),
            "N",
            note=(
                f"m_rod a = {leg_expected_N:.3f} N (ramp start / stop); "
                "stroke-end braking last step <= 9/8 a dt (discrete cap + end clip)"
            ),
        )
        for leg, leg_deviation_N, leg_expected_N in zip(
            LEG_ORDER, deviation_N, expected_N, strict=True
        )
    ]


def ramp_spike_checks(cases: Sequence[Mapping[str, Any]]) -> list[CheckResult]:
    """Inertial reaction of a +v_max command step on a hanging rod (``chrono/actuators``).

    Each case: ``name``, ``ramp_s``, ``dt_s``, ``max_force_dev_N`` (per leg), ``expected_N``
    (``m_rod a`` with the ramp, ``m_rod v_max / dt`` without; per leg in :data:`LEG_ORDER`
    because the front and rear moving parts differ, or one value for every leg). One check
    per case and leg, tolerance ``max(1 % expected, 1 N)`` of that leg.
    """
    out = []
    for c in cases:
        deviation_N = np.asarray(c["max_force_dev_N"], dtype=float)
        expected_N = np.broadcast_to(np.asarray(c["expected_N"], dtype=float), deviation_N.shape)
        for leg, leg_deviation_N, leg_expected_N in zip(
            LEG_ORDER, deviation_N, expected_N, strict=True
        ):
            out.append(
                check_abs(
                    "ramp",
                    f"{c['name']} {leg}: max |F_motor + m_rod g| "
                    f"(ramp {c['ramp_s']} s, dt {c['dt_s']} s)",
                    leg_deviation_N,
                    leg_expected_N,
                    max(SPIKE_REL_TOL * float(leg_expected_N), SPIKE_ABS_TOL_N),
                    "N",
                    note="with ramp: m_rod v_max / ramp; without: m_rod v_max / dt (one step)",
                )
            )
    return out


def event_checks(
    name: str,
    events: Sequence[Sequence[float]],
    expected: Sequence[tuple[int, int]],
) -> list[CheckResult]:
    """R15 event test of one run: events (t, leg, kind) equal the expected sequence."""
    got = [(int(e[1]), int(e[2])) for e in events]
    return [
        check_equal(
            "R15",
            f"{name}: events = touch create, lift remove, re-touch create (chatter 0)",
            got,
            list(expected),
        )
    ]


def event_dt_checks(
    name: str, events_coarse: Sequence[Sequence[float]], events_fine: Sequence[Sequence[float]]
) -> list[CheckResult]:
    """R15 tuning rule: same events at both dt, times within 1 ms."""
    same = [(int(e[1]), int(e[2])) for e in events_coarse] == [
        (int(e[1]), int(e[2])) for e in events_fine
    ]
    out = [check_equal("R15", f"{name}: same event sequence at dt 1e-4 / 1e-5 s", same, True)]
    if same and events_coarse:
        tc = np.array([e[0] for e in events_coarse], dtype=float)
        tf = np.array([e[0] for e in events_fine], dtype=float)
        out.append(
            check_max(
                "R15",
                f"{name}: |event time (dt 1e-4) - event time (dt 1e-5)|",
                np.abs(tc - tf),
                EVENT_TIME_DIFF_MAX_S,
                "s",
            )
        )
    return out


def crawler_settle_checks(
    *,
    level: str,
    analytic: Mapping[str, Any],
    window: Mapping[str, Any],
    quarter_weight_N: float,
) -> list[CheckResult]:
    """Crawler settle (legs at 0, analytic start) and V13 in the still window.

    Args:
        analytic: ``u_z_mm``, ``roll_deg``, ``pitch_deg`` of the analytic (exact) pose.
        window: ``u_z_mm``, ``roll_deg``, ``pitch_deg`` (means), ``roll_span_deg``,
            ``pitch_span_deg``, ``crawler_fz_span_N``, ``active_min``, ``active_max``,
            ``pad_contacts_max``, ``motor_violation_max_m``, ``any_nan``.
    """
    return [
        check_abs(
            "S2b",
            f"{level}: settled pose = analytic exact pose (u_z)",
            window["u_z_mm"],
            analytic["u_z_mm"],
            CRAWLER_POSE_TOL_MM,
            "mm",
        ),
        check_abs(
            "S2b",
            f"{level}: settled pose = analytic exact pose (roll, pitch)",
            [window["roll_deg"], window["pitch_deg"]],
            [analytic["roll_deg"], analytic["pitch_deg"]],
            CRAWLER_POSE_TOL_DEG,
            "deg",
        ),
        check_equal(
            "V0",
            f"{level}: active crawler spheres = 14 (min, max in the window)",
            [int(window["active_min"]), int(window["active_max"])],
            [CRAWLER_ACTIVE_SPHERES, CRAWLER_ACTIVE_SPHERES],
        ),
        check_equal(
            "V13", f"{level}: no pad contact (legs at 0)", int(window["pad_contacts_max"]), 0
        ),
        check_max(
            "V13",
            f"{level}: attitude drift in the still window (roll, pitch span)",
            [window["roll_span_deg"], window["pitch_span_deg"]],
            V13_DRIFT_DEG,
            "deg",
        ),
        check_max(
            "V13",
            f"{level}: crawler vertical force variation (span)",
            window["crawler_fz_span_N"],
            V13_FORCE_FRACTION_OF_QUARTER_WEIGHT * quarter_weight_N,
            "N",
            note="tol = 0.1 % W/4",
        ),
        check_max(
            "V13",
            f"{level}: motor constraint violation (leg COG offset)",
            window["motor_violation_max_m"],
            V13_MOTOR_VIOLATION_M,
            "m",
        ),
        check_equal("V13", f"{level}: no NaN", bool(window["any_nan"]), False),
    ]


def crawler_gap_checks(
    sphere_bottom_above_floor_m: ArrayLike, yaml_gap_m: ArrayLike
) -> list[CheckResult]:
    """V0 / R13: built sphere bottoms above the crawler plane = YAML gaps (0 for rollers)."""
    return [
        check_abs(
            "V0",
            "crawler sphere bottom above the crawler plane = YAML end_shoe_gap_m (rollers 0)",
            sphere_bottom_above_floor_m,
            yaml_gap_m,
            1.0e-9,
            "m",
        )
    ]


def snapshot_checks(name: str, max_pos_diff_m: float) -> list[CheckResult]:
    return [
        check_max(
            "R16",
            f"{name}: snapshot round trip (restore into a fresh build, continue), position diff",
            max_pos_diff_m,
            SNAPSHOT_POS_TOL_M,
            "m",
        )
    ]
