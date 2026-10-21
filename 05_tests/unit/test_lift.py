"""S3 lift / leg-step scenario plans (engine independent): ``scenarios/lift``."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.params import load_params
from outrigger_sim.scenarios.lift import (
    LegStep,
    crossing,
    equivalent_origin_from_trajectory,
    lift_plan,
)

RAMP_S = 0.1
TOUCH_D = (15.050, 15.049, 15.177, 15.177)  # dynamic_events_s / touch_s, layout D
F1_HZ = 1.7983


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def test_lift_plan_stops_and_windows(params) -> None:
    plan = lift_plan(params, ramp_s=RAMP_S, reference_touch_eq_s=TOUCH_D, first_rocking_Hz=F1_HZ)
    v = params.actuator.max_speed_m_s
    e = params.contact.rigid_floor.L1.operating_extension_m
    # braking from e_op / v_max after the start command (dynamics_model.md 5 V4 rev. 15)
    assert plan.brake_start_s == pytest.approx([ei / v for ei in e], rel=1e-12)
    assert plan.brake_start_s[0] == pytest.approx(17.696, abs=5e-4)
    assert plan.brake_start_s[2] == pytest.approx(17.246, abs=5e-4)
    assert plan.stop_s == pytest.approx([b + RAMP_S for b in plan.brake_start_s])
    assert plan.equivalent_origin_s == 0.05
    w0, w1 = plan.transition_window_s
    # earliest touch 15.049 + 0.05 - 0.1 = 14.999 -> 14.99; last stop 17.796 + 0.3 -> 18.10
    assert w0 == pytest.approx(14.99, abs=1e-9)
    assert w1 == pytest.approx(18.10, abs=1e-9)
    assert plan.command_zero_s >= w1
    assert abs(plan.command_zero_s / 0.02 - round(plan.command_zero_s / 0.02)) < 1e-9
    r0, r1 = plan.residual_window_s
    assert r0 == pytest.approx(plan.last_stop_s + 15.0)
    assert r1 - r0 == pytest.approx(1.0 / F1_HZ)
    assert plan.end_s >= r0 + 3.0 / F1_HZ - 1e-9
    sched = plan.schedule()
    assert sched.command_at(1.0).tolist() == [v] * 4
    assert sched.command_at(plan.command_zero_s + 0.01).tolist() == [0.0] * 4


def test_equivalent_origin_of_a_ramped_start() -> None:
    v, ramp, dt = 0.0226666667, 0.1, 1.0e-4
    t = np.arange(0.0, 3.0, dt)
    # discrete ramp of the actuator: segment k has speed min(k a dt, v), starting at t = dt
    a = v / ramp
    u = np.minimum(np.arange(len(t)) * a * dt, v)
    s = np.concatenate([[0.0], np.cumsum(u[:-1] * dt)])
    t_eq = equivalent_origin_from_trajectory(t, s, v, 1.0, 2.9)
    assert t_eq == pytest.approx(ramp / 2.0 + dt / 2.0, abs=1e-9)


def test_leg_step_soft_limits_and_window() -> None:
    step = LegStep("v6", 0, 1.0e-4, -14.68e-3, 0.5, 0.5, transition_from_delta_m=13.78e-3)
    lo, hi = step.soft_limits([0.4011, 0.4011, 0.3909, 0.3909], [(0.0, 0.68)] * 4)
    assert lo[0] == pytest.approx(0.4011 - 14.68e-3)
    assert hi[0] == 0.68 and lo[1] == 0.0
    assert step.command() == (-1.0e-4, 0.0, 0.0, 0.0)
    w = step.transition_window_s(0.1)
    assert w is not None and w[0] == pytest.approx(138.3, abs=0.01)
    assert w[1] >= step.end_s(0.1)


def test_crossing_interpolates() -> None:
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([10.0, 8.0, 4.0, 0.0])
    assert crossing(x, y, 6.0, falling=True) == pytest.approx(1.5)
    assert crossing(x, y, 20.0, falling=False) is None
