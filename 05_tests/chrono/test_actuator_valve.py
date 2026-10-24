"""R8 valve model of L1SpeedActuator (s6_control_spec.md rev. 31 148 R-2 / R-3): exact
first-order spool lag with step-mean speed, amplifier ramps, tau -> 0 limit, retime, snapshot
keys, and the default (valve off) unchanged."""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.actuators import (  # noqa: E402
    VALVE_STATE_KEYS,
    L1SpeedActuator,
    make_motion_function,
)

pytestmark = pytest.mark.chrono

V_MAX = 0.020924
RAMP = 0.1


def _act(n=1, s0=0.3, ramp_s=RAMP):
    fns = [make_motion_function(s0) for _ in range(n)]
    return L1SpeedActuator([object()] * n, fns, [s0] * n, [(0.0, 0.7)] * n,
                           max_speed_m_s=V_MAX, ramp_s=ramp_s), fns


def test_step_response_is_the_exact_exponential() -> None:
    tau, dt = 0.1, 2e-4
    act, fns = _act()
    act.configure_valve(tau_s=tau)
    assert not act.command_ramp_active
    act.set_command([V_MAX])
    s0 = 0.3
    for k in range(1, 2001):
        act.advance(dt, (k - 1) * dt)
        t = k * dt
        assert act.valve_state_m_s[0] == pytest.approx(V_MAX * (1 - math.exp(-t / tau)),
                                                       abs=1e-12 * V_MAX + 1e-18)
        # position = exact integral of the lagged speed
        s_exact = s0 + V_MAX * (t - tau * (1 - math.exp(-t / tau)))
        assert act.s_ref_m[0] == pytest.approx(s_exact, abs=1e-12)
    # the motion function slope is the step mean speed
    assert fns[0].GetDer(0.0) == act.u_applied_m_s[0]


def test_tau_zero_equals_the_unramped_actuator() -> None:
    a, _ = _act(ramp_s=0.0)
    b, _ = _act()
    b.configure_valve(tau_s=0.0)
    cmds = [0.01, -0.005, 0.03, 0.0, -0.02]
    for k in range(500):
        u = cmds[(k // 100) % len(cmds)]
        a.set_command([u])
        b.set_command([u])
        a.advance(2e-4, k * 2e-4)
        b.advance(2e-4, k * 2e-4)
        assert a.u_applied_m_s[0] == b.u_applied_m_s[0]
        assert a.s_ref_m[0] == b.s_ref_m[0]


@pytest.mark.parametrize("mode", ["full_scale", "per_step"])
def test_amplifier_ramps(mode) -> None:
    dt = 1e-3
    act, _ = _act()
    act.configure_valve(tau_s=0.0, amp_ramp=mode, amp_ramp_s=0.1)
    act.set_command([0.25 * V_MAX])
    out = []
    for k in range(200):
        act.advance(dt, k * dt)
        out.append(act.amp_output_m_s[0])
    out = np.asarray(out)
    if mode == "full_scale":  # 0.25 v_max at v_max / 0.1 s: reached after 25 ms
        assert out[23] < 0.25 * V_MAX
        assert out[25] == pytest.approx(0.25 * V_MAX, rel=1e-12)
        assert out[0] == pytest.approx(V_MAX / 0.1 * dt)
    else:  # any change takes 0.1 s
        assert out[98] < 0.25 * V_MAX
        assert out[100] == pytest.approx(0.25 * V_MAX, rel=1e-12)
        assert out[0] == pytest.approx(0.25 * V_MAX / 0.1 * dt)


def test_retime_redoes_the_pending_valve_step() -> None:
    tau = 0.1
    a, _ = _act()
    a.configure_valve(tau_s=tau)
    a.set_command([V_MAX])
    a.advance(2e-4, 0.0)
    a.retime(0.0, 1e-5)  # the pending step is 1e-5 s long after all
    assert a.valve_state_m_s[0] == pytest.approx(V_MAX * (1 - math.exp(-1e-5 / tau)), rel=1e-12)


def test_snapshot_keys_only_with_valve() -> None:
    off, _ = _act()
    assert not any(k in off.state_arrays() for k in VALVE_STATE_KEYS)
    on, _ = _act()
    on.configure_valve(tau_s=0.1)
    on.set_command([V_MAX])
    for k in range(10):
        on.advance(2e-4, k * 2e-4)
    arrays = on.state_arrays()
    assert all(k in arrays for k in VALVE_STATE_KEYS)
    other, _ = _act()
    other.configure_valve(tau_s=0.1)
    other.restore_state(arrays)
    assert np.array_equal(other.valve_state_m_s, on.valve_state_m_s)
    del arrays["valve_u_m_s"]
    other.restore_state(arrays)  # no valve keys = run start
    assert np.all(other.valve_state_m_s == 0.0)


def test_bad_settings() -> None:
    act, _ = _act()
    with pytest.raises(ValueError):
        act.configure_valve(tau_s=-1.0)
    with pytest.raises(ValueError):
        act.configure_valve(tau_s=0.1, amp_ramp="linear")
    with pytest.raises(ValueError):
        act.configure_valve(tau_s=0.1, amp_ramp="per_step", amp_ramp_s=0.0)
