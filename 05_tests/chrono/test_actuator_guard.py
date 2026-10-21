"""Actuator hook guard, soft travel limits and time-step change (S3 preliminary).

``dynamics_model.md`` 5.6 ruling 1 condition 1: with ``ChFunctionRamp`` motion functions a
step without the actuator hook keeps moving with the last slope, so the hook must run after
every step; a guard detects the miss (exception) and :meth:`L1SpeedActuator.freeze` sets the
slopes to 0 for code that steps without the hook. Also: soft limits stop a leg exactly with
the ramped brake (S3 lift ``e_op`` stop), and ``L1Model.set_dt`` keeps the motor target
continuous across a time-step change (S3 transition window).
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.actuators import (  # noqa: E402
    ActuatorHookMissedError,
    L1SpeedActuator,
    make_motion_function,
)
from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.model import L1Model  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.scenarios.stroke import air_pose  # noqa: E402

pytestmark = pytest.mark.chrono

DT = 1.0e-4
ACCEL_RAMP_S = load_params(level="top").actuator.command_ramp_s
"""YAML ``actuator.command_ramp_s`` (0.1 s, ASSUMPTION user decision 2026-10-20)."""


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def _air(params, dt_s=DT):
    """Superstructure fixed, legs in the air (no contact, no bushing)."""
    model = L1Model(
        params,
        pose=BodyPose(air_pose(params)),
        extensions_m=(0.0, 0.0, 0.0, 0.0),
        attach_bushings=False,
        actuator=True,
        dt_s=dt_s,
    )
    model.superstructure.SetFixed(True)
    return model


def _moving(params, steps=50, dt_s=DT):
    model = _air(params, dt_s)
    v = params.actuator.max_speed_m_s
    model.set_command([v, v, v, v])
    for _ in range(steps):
        model.step()
    assert model.actuator.is_moving_segment
    return model


def test_step_without_hook_raises(params) -> None:
    model = _moving(params)
    model.actuator_hooks.clear()  # the hook is gone: the slope stays
    model.step()  # this step was prepared by the last hook: allowed
    with pytest.raises(ActuatorHookMissedError, match="hook last ran"):
        model.step()


def test_direct_step_while_moving_is_caught(params) -> None:
    model = _moving(params)
    model.system.DoStepDynamics(model.dt_s)  # bypasses the hook
    with pytest.raises(ActuatorHookMissedError):
        model.step()


def test_holding_still_needs_no_hook(params) -> None:
    model = _air(params)
    for _ in range(3):
        model.system.DoStepDynamics(model.dt_s)  # slope 0: constant target
    model.step()  # no exception


def test_freeze_stops_the_ramp_for_hookless_stepping(params) -> None:
    model = _moving(params, steps=2000)  # past the 0.1 s ramp: at v_max
    t = float(model.system.GetChTime())
    model.actuator.freeze(t)
    assert not model.actuator.is_moving_segment
    model.actuator_hooks.clear()
    positions = []
    for _ in range(5):
        model.step()
        positions.append([m.GetMotorPos() for m in model.motors])
    p = np.asarray(positions)
    # one-step lag: the first step after the freeze still uses the loaded slope
    assert np.all(np.abs(p[2:] - p[1]) < 1e-15)


def test_dt_change_without_retime_raises(params) -> None:
    model = _moving(params)
    model.dt_s = 1.0e-5  # bypasses set_dt
    with pytest.raises(ActuatorHookMissedError, match="time step"):
        model.step()


def test_set_dt_keeps_the_target_continuous(params) -> None:
    v = params.actuator.max_speed_m_s
    model = _moving(params, steps=1500)  # constant v_max after the ramp
    t_switch = float(model.system.GetChTime())
    s_switch = model.motors[0].GetMotorPos()
    model.set_dt(1.0e-5)
    for _ in range(200):
        model.step()
        for m, s_act in zip(model.motors, model.actuator.acting_s_ref_m, strict=True):
            assert abs(m.GetMotorPos() - s_act) < 1e-12
            assert abs(m.GetMotorPosDt() - v) < 1e-9 * v
    model.set_dt(DT)
    for _ in range(100):
        model.step()
    t = float(model.system.GetChTime())
    # constant speed through both switches: position grows by v (t - t_switch) exactly
    assert model.motors[0].GetMotorPos() - s_switch == pytest.approx(v * (t - t_switch), abs=1e-12)
    assert model.bushing.dt_s == DT


def test_restore_into_another_dt_continues(params) -> None:
    v = params.actuator.max_speed_m_s
    model = _moving(params, steps=1500)
    snap = model.snapshot()
    fresh = _air(params, dt_s=5.0e-5)
    fresh.restore(snap)
    t0 = float(fresh.system.GetChTime())
    s0 = fresh.motors[0].GetMotorPos()
    for _ in range(100):
        fresh.step()  # no ActuatorHookMissedError
    t = float(fresh.system.GetChTime())
    assert fresh.motors[0].GetMotorPos() - s0 == pytest.approx(v * (t - t0), abs=1e-12)


def _standalone(n=1):
    functions = [make_motion_function(0.0) for _ in range(n)]
    act = L1SpeedActuator(
        [object()] * n,
        functions,
        [0.0] * n,
        [(0.0, 0.68)] * n,
        max_speed_m_s=0.0226666667,
        ramp_s=ACCEL_RAMP_S,
    )
    return act


@pytest.mark.parametrize("dt", [2.0e-4, 1.0e-4, 1.0e-5])
def test_soft_limit_ramped_stop_is_exact(dt: float) -> None:
    """S3 lift: command +v_max from rest, soft limit e: braking starts at e / v_max after the
    command and the leg stops exactly on e at e / v_max + ramp (dynamics_model.md 5 V4)."""
    act = _standalone()
    v = act.max_speed_m_s
    e = 0.3909
    act.set_soft_limits(hi_m=[e])
    act.set_command([v])
    n = round((e / v + ACCEL_RAMP_S + 0.05) / dt)
    u = np.empty(n)
    s = np.empty(n)
    for k in range(n):
        act.advance(dt, k * dt)
        u[k], s[k] = act.u_applied_m_s[0], act.s_ref_m[0]
    assert s[-1] == pytest.approx(e, abs=1e-15)
    assert s.max() <= e
    # segment k spans [k dt, (k + 1) dt]
    full = np.flatnonzero(u >= v * (1.0 - 1e-9))
    k_brake = full[-1] + 1
    k_stop = np.flatnonzero(u > 0.0)[-1] + 1
    assert k_brake * dt == pytest.approx(e / v, abs=2.0 * dt)
    assert k_stop * dt == pytest.approx(e / v + ACCEL_RAMP_S, abs=2.0 * dt)


def test_soft_limits_must_contain_the_reference() -> None:
    act = _standalone()
    act.set_command([act.max_speed_m_s])
    for k in range(5000):
        act.advance(1.0e-4, k * 1.0e-4)
    with pytest.raises(ValueError, match="outside the new soft limits"):
        act.set_soft_limits(hi_m=[0.001])
    with pytest.raises(ValueError, match="stroke range"):
        act.set_soft_limits(hi_m=[0.7])
    act.clear_soft_limits()
    assert act.soft_limits_m.tolist() == [[0.0, 0.68]]
