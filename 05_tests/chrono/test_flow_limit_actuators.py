"""Shared-pump flow limit on the Chrono leg actuators: L1 equals ``SpeedReference`` on the limit,
absent = unchanged, and the L2b friction path hands the limit the pressure force ``F - f``."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.actuation import FLOW_OPEN_KEY, SpeedReference  # noqa: E402
from outrigger_sim.chrono.actuators import L1SpeedActuator, make_motion_function  # noqa: E402
from outrigger_sim.chrono.l2b_actuator import L2bForceActuator  # noqa: E402
from outrigger_sim.hydraulics.flow_limit_run import (  # noqa: E402
    FlowLimitSetting,
    RecordedFlowLimiter,
)
from outrigger_sim.hydraulics.flow_share import flow_circuit_from_params  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

pytestmark = pytest.mark.chrono

DT_S = 1.0e-4
RAMP_S = 0.1
FORCE_N = np.array([90.0e3, 88.0e3, 70.0e3, 68.0e3])
STROKE = (0.0, 0.7)


@pytest.fixture(scope="module")
def params():
    return load_params()


def _limiter(params, eta_v=0.85):
    return RecordedFlowLimiter(flow_circuit_from_params(params), FlowLimitSetting(eta_v=eta_v))


def _l1(v_max, *, valve):
    functions = [make_motion_function(0.1) for _ in range(4)]
    actuator = L1SpeedActuator([object()] * 4, functions, [0.1] * 4, [STROKE] * 4,
                               max_speed_m_s=v_max, ramp_s=RAMP_S)
    if valve:
        actuator.configure_valve(tau_s=0.1)
    return actuator, functions


def _reference(v_max, *, valve):
    reference = SpeedReference([0.1] * 4, [STROKE] * 4, max_speed_m_s=v_max, ramp_s=RAMP_S)
    if valve:
        reference.configure_valve(tau_s=0.1)
    return reference


@pytest.mark.parametrize("valve", [True, False])
def test_l1_equals_the_speed_reference_with_the_limit(params, valve) -> None:
    v_max = float(params.get("actuator.max_speed_m_s"))
    l1, _ = _l1(v_max, valve=valve)
    reference = _reference(v_max, valve=valve)
    l1.set_flow_limit(_limiter(params))
    reference.set_flow_limit(_limiter(params))
    for actuator in (l1, reference):
        actuator.set_command([v_max] * 4)
    for k in range(10000):
        l1.advance(DT_S, k * DT_S, cylinder_force_N=FORCE_N)
        reference.advance(DT_S, cylinder_force_N=FORCE_N, t_s=k * DT_S)
        assert np.array_equal(l1.u_applied_m_s, reference.u_applied_m_s)
        assert np.array_equal(l1.s_ref_m, reference.s_ref_m)
    assert l1.u_applied_m_s.min() < 0.95 * v_max


def test_l1_without_a_limit_has_no_flow_key_and_design_point_is_identical(params) -> None:
    v_max = float(params.get("actuator.max_speed_m_s"))
    free, free_fn = _l1(v_max, valve=True)
    on, on_fn = _l1(v_max, valve=True)
    on.set_flow_limit(_limiter(params, 0.95))
    assert FLOW_OPEN_KEY not in free.state_arrays()
    assert FLOW_OPEN_KEY in on.state_arrays()
    for actuator in (free, on):
        actuator.set_command([v_max] * 4)
    for k in range(3000):
        free.advance(DT_S, k * DT_S, cylinder_force_N=FORCE_N)
        on.advance(DT_S, k * DT_S, cylinder_force_N=FORCE_N)
    assert np.array_equal(free.s_ref_m, on.s_ref_m)
    assert [f.GetDer(0.0) for f in free_fn] == [f.GetDer(0.0) for f in on_fn]


def test_l1_snapshot_round_trip_with_the_limit(params) -> None:
    v_max = float(params.get("actuator.max_speed_m_s"))
    first, _ = _l1(v_max, valve=False)
    first.set_flow_limit(_limiter(params))
    first.set_command([v_max] * 4)
    for k in range(1500):
        first.advance(DT_S, k * DT_S, cylinder_force_N=FORCE_N)
    state = first.state_arrays()
    second, _ = _l1(v_max, valve=False)
    second.set_flow_limit(_limiter(params))
    second.restore_state(state)
    second.finish_restore()
    second.set_command([v_max] * 4)
    for k in range(1500, 2000):
        first.advance(DT_S, k * DT_S, cylinder_force_N=FORCE_N)
        second.advance(DT_S, k * DT_S, cylinder_force_N=FORCE_N)
    assert np.array_equal(first.s_ref_m, second.s_ref_m)


class _ForceProbe:
    """A flow limit that passes the request and keeps the force it was given."""

    def __init__(self):
        self.forces = []

    def limit(self, t_s, dt_s, request, force):
        self.forces.append(np.array(force, dtype=float))
        return np.array(request, dtype=float)


def test_l2b_friction_path_gives_the_pressure_force(params) -> None:
    """Friction path: the limit reads ``acting_force_N - acting_friction_N`` (F_p of seal_friction)."""
    p2 = load_params(model="L2b_NSC", overrides={"actuator.seal_friction.level_N": 4000.0})
    motors = [_MotorStub() for _ in range(4)]
    functions = [_FunctionStub() for _ in range(4)]
    actuator = L2bForceActuator.from_params(p2, motors, functions, [0.1] * 4)
    probe = _ForceProbe()
    actuator.set_flow_limit(probe)
    v_max = float(p2.get("actuator.max_speed_m_s"))
    actuator.set_command([v_max] * 4)
    t = 0.0
    for k in range(2000):
        for i, motor in enumerate(motors):
            motor.pos = 0.1 + 0.5 * v_max * t
            motor.vel = 0.5 * v_max
        actuator.on_step_end()
        expected = actuator.acting_force_N - actuator.acting_friction_N
        np.testing.assert_array_equal(expected, actuator.acting_pressure_force_N)
        actuator.hook(t, DT_S)
        np.testing.assert_array_equal(probe.forces[-1], expected)
        t += DT_S
    assert np.any(actuator.acting_friction_N != 0.0)


class _MotorStub:
    pos = 0.1
    vel = 0.0

    def GetMotorPos(self):
        return self.pos

    def GetMotorPosDt(self):
        return self.vel


class _FunctionStub:
    def SetConstant(self, value):
        self.value = value
