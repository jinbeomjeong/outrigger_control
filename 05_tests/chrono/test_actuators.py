"""S2b actuator checks (chrono_build_plan.md S2b): L1SpeedActuator limits, ramp, stroke-end
braking, motor sign (R4), inertial reaction, no target hiccup at ground-bushing events and the
snapshot round trip with the actuator state (R16)."""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.actuators import (  # noqa: E402
    ACCEL_RAMP_S,
    L1SpeedActuator,
    make_motion_function,
)
from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.model import L1Model  # noqa: E402
from outrigger_sim.chrono.runs import run_commanded  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.scenarios.crawler_settle import (  # noqa: E402
    crawler_static_pose,
    pad_touch_extension_m,
)
from outrigger_sim.scenarios.stroke import air_pose  # noqa: E402

pytestmark = pytest.mark.chrono

V_MAX = 0.0226666667


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def _standalone(n=1, ramp_s=ACCEL_RAMP_S, s0=0.0):
    functions = [make_motion_function(s0) for _ in range(n)]
    act = L1SpeedActuator(
        [object()] * n, functions, [s0] * n, [(0.0, 0.68)] * n, max_speed_m_s=V_MAX, ramp_s=ramp_s
    )
    return act, functions


def test_ramp_saturation_and_exact_end_stop() -> None:
    act, functions = _standalone()
    dt = 1.0e-4
    a = V_MAX / ACCEL_RAMP_S
    act.set_command([5.0])
    u_prev, us, ss = 0.0, [], []
    for k in range(int(30.2 / dt)):
        act.advance(dt, k * dt)
        u = float(act.u_applied_m_s[0])
        # the last braking step lands on the end by a clip (rounding of the remaining
        # distance): allow 0.1 % over a dt
        assert abs(u - u_prev) <= a * dt * (1.0 + 1e-3)
        assert u <= V_MAX
        us.append(u)
        ss.append(float(act.s_ref_m[0]))
        u_prev = u
    assert ss[-1] == pytest.approx(0.68, abs=1e-15)
    assert max(ss) <= 0.68
    t_end = (np.flatnonzero(np.asarray(us) > 0.0)[-1] + 1) * dt
    assert t_end == pytest.approx(0.68 / V_MAX + ACCEL_RAMP_S, abs=2 * dt)
    # ramp function value at t_n is the reference at t_n, slope = applied speed
    f = functions[0]
    assert f.GetDer(0.0) == u_prev


def test_retract_beyond_lower_end_stays_at_zero() -> None:
    act, _ = _standalone()
    act.set_command([-1.0])
    for k in range(100):
        act.advance(1.0e-4, k * 1.0e-4)
    assert act.s_ref_m[0] == 0.0
    assert act.u_applied_m_s[0] == 0.0


def test_no_ramp_is_a_speed_step() -> None:
    act, _ = _standalone(ramp_s=0.0)
    act.set_command([1.0])
    act.advance(1.0e-4, 0.0)
    assert act.u_applied_m_s[0] == V_MAX


def test_rejects_constant_function() -> None:
    with pytest.raises(TypeError):
        L1SpeedActuator(
            [object()], [ch.ChFunctionConst(0.0)], [0.0], [(0.0, 0.68)], max_speed_m_s=V_MAX
        )


def _air_model(params, ramp_s=ACCEL_RAMP_S, dt_s=1.0e-4):
    model = L1Model(
        params,
        pose=BodyPose(air_pose(params)),
        extensions_m=(0.0, 0.0, 0.0, 0.0),
        crawler=False,
        attach_bushings=False,
        actuator=True,
        actuator_ramp_s=ramp_s,
        dt_s=dt_s,
    )
    model.superstructure.SetFixed(True)
    return model


def test_motor_sign_speed_and_inertial_reaction(params) -> None:
    model = _air_model(params)
    weight = params.legs[0].moving_part.mass_kg * params.meta.gravity_m_s2
    model.set_command([V_MAX, V_MAX, V_MAX, V_MAX])
    p0 = model.step(capture=True).probe
    assert np.allclose(p0.motor_force_N, -weight, atol=1.0)  # hanging rod pulls: F < 0
    run = run_commanded(model, 0.5, lambda _t: None, sample_s=0.5, force_ref_N=[-weight] * 4)
    p1 = model.probe()
    dz = p1.pad_sphere_centre_world_m[:, 2] - p0.pad_sphere_centre_world_m[:, 2]
    ds = p1.motor_pos_m - p0.motor_pos_m
    assert np.all(dz < 0.0)
    assert np.allclose(dz, -ds, atol=1e-12)
    assert np.allclose(run.max_motor_speed_m_s, V_MAX, rtol=1e-6)
    m_a = params.legs[0].moving_part.mass_kg * V_MAX / ACCEL_RAMP_S
    assert np.allclose(run.max_force_dev_N, m_a, rtol=0.01)
    assert run.max_motor_violation_m < 1e-9


def test_speed_step_without_ramp_gives_one_step_spike(params) -> None:
    model = _air_model(params, ramp_s=0.0)
    weight = params.legs[0].moving_part.mass_kg * params.meta.gravity_m_s2
    model.set_command([V_MAX] * 4)
    run = run_commanded(model, 0.05, lambda _t: None, sample_s=0.05, force_ref_N=[-weight] * 4)
    expected = params.legs[0].moving_part.mass_kg * V_MAX / model.dt_s
    assert np.allclose(run.max_force_dev_N, expected, rtol=0.01)


def _event_model(params, gap_m=1.0e-3):
    pose = crawler_static_pose(params)
    touch = pad_touch_extension_m(params, 0, pose.origin_m, pose.quat_wxyz)
    ext = (touch - gap_m, 0.0, 0.0, 0.0)
    pose = crawler_static_pose(params, ext)
    return L1Model(
        params,
        pose=BodyPose(pose.origin_m, pose.quat_wxyz),
        extensions_m=ext,
        attach_bushings=False,
        actuator=True,
    )


def test_no_target_hiccup_at_bushing_creation(params) -> None:
    """The step after a bushing is created starts with a full Update; the ramp motion
    function keeps the motor velocity on the applied speed (no +-v_max step)."""
    model = _event_model(params)
    model.set_command([V_MAX, 0.0, 0.0, 0.0])
    worst = 0.0
    created = None
    for _ in range(int(0.25 / model.dt_s)):
        res = model.step()
        if res.events and created is None:
            created = float(model.system.GetChTime())
        dev = abs(model.motors[0].GetMotorPosDt() - float(model.actuator.acting_u_m_s[0]))
        worst = max(worst, dev)
    assert created is not None
    a = V_MAX / ACCEL_RAMP_S
    assert worst <= 2.0 * a * model.dt_s


def _positions(model):
    return np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in model.bodies])


@pytest.mark.parametrize("at_event", [False, True])
def test_snapshot_round_trip_with_actuator(params, at_event) -> None:
    """Snapshot while the leg moves (mid-ramp) or in the hook that created the bushing
    (structural change pending): restore into a fresh build, continue 0.05 s, same state."""
    model = _event_model(params)
    model.set_command([V_MAX, 0.0, 0.0, 0.0])
    if at_event:
        while not model.step().events:
            pass
        assert not model.system.IsUpdated()
    else:
        for _ in range(300):  # 30 ms: inside the 0.1 s ramp
            model.step()
    snap = model.snapshot()
    n = 500
    for _ in range(n):
        model.step()
    expected = _positions(model)
    fresh = _event_model(params)
    fresh.restore(snap)
    np.testing.assert_array_equal(fresh.actuator.command_m_s, [V_MAX, 0.0, 0.0, 0.0])
    for _ in range(n):
        fresh.step()
    assert np.abs(_positions(fresh) - expected).max() <= 1.0e-12
    assert math.isclose(
        float(fresh.system.GetChTime()), float(model.system.GetChTime()), abs_tol=1e-12
    )
