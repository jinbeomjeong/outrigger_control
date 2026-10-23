"""S6 force saturation (chrono_build_plan.md S6 'cad: 힘 포화', V11b): per-step cut of the
leg speed at the 210 bar limits in ``L1SpeedActuator``, and the single-leg spring model."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.actuators import (  # noqa: E402
    L1SpeedActuator,
    leg_force_limits_N,
    make_motion_function,
)
from outrigger_sim.chrono.single_leg import SingleLegModel, run_schedule  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.verify.s6 import v11b_analysis, v11b_checks  # noqa: E402

pytestmark = pytest.mark.chrono

V_MAX = 0.0226666667
RAMP_S = 0.1
F_EXT = 218124.705
F_RET = 18555.0316


def _actuator(n=2, limits=True, s0=0.3):
    functions = [make_motion_function(s0) for _ in range(n)]
    kw = {"max_force_extend_N": F_EXT, "max_force_retract_N": F_RET} if limits else {}
    act = L1SpeedActuator(
        [object()] * n, functions, [s0] * n, [(0.0, 0.68)] * n, max_speed_m_s=V_MAX,
        ramp_s=RAMP_S, **kw,
    )
    return act


def _run_to_speed(act, command, dt=2e-4, steps=600):
    act.set_command(command)
    for k in range(steps):
        act.advance(dt, k * dt, cylinder_force_N=np.zeros(act.n_legs))
    return steps * dt


def test_extend_cut_only_in_the_saturated_direction() -> None:
    act = _actuator()
    dt = 2e-4
    t = _run_to_speed(act, [V_MAX, -V_MAX], dt)
    assert np.allclose(act.u_applied_m_s, [V_MAX, -V_MAX])
    # leg 0 at the extend limit and moving out -> cut; leg 1 at the extend limit but
    # retracting -> not cut
    act.advance(dt, t, cylinder_force_N=[F_EXT, F_EXT])
    # law C: decelerate with a_sat = v_max / t_sat (2 ms) in the saturated direction
    a_sat = V_MAX / act.saturation_stop_s
    assert act.u_applied_m_s[0] == pytest.approx(V_MAX - a_sat * dt)
    assert act.u_applied_m_s[1] == pytest.approx(-V_MAX)
    assert act.saturated.tolist() == [True, False]
    assert act.saturation_step_count.tolist() == [1, 0]
    for k in range(20):
        act.advance(dt, t + (k + 1) * dt, cylinder_force_N=[F_EXT, F_EXT])
    assert act.u_applied_m_s[0] == 0.0
    assert act.saturation_start_count.tolist() == [1, 0]


def test_retract_cut_and_immediate_reverse() -> None:
    act = _actuator(n=1)
    dt = 2e-4
    t = _run_to_speed(act, [-V_MAX], dt)
    for k in range(11):
        act.advance(dt, t + k * dt, cylinder_force_N=[-F_RET])
    assert act.u_applied_m_s[0] == 0.0  # stopped within t_sat = 2 ms = 10 steps
    t = t + 10 * dt
    # reversed command while still at the pull limit: followed at once (not cut)
    act.set_command([V_MAX])
    act.advance(dt, t + dt, cylinder_force_N=[-F_RET * 1.5])
    assert act.u_applied_m_s[0] == pytest.approx(V_MAX / RAMP_S * dt)


def test_below_the_limits_bit_identical_to_no_saturation() -> None:
    with_limits, without = _actuator(), _actuator(limits=False)
    dt = 2e-4
    for act in (with_limits, without):
        act.set_command([V_MAX, -0.5 * V_MAX])
    for k in range(2000):
        with_limits.advance(dt, k * dt, cylinder_force_N=[F_EXT * 0.999, -F_RET * 0.999])
        without.advance(dt, k * dt)
        assert np.array_equal(with_limits.u_applied_m_s, without.u_applied_m_s)
        assert np.array_equal(with_limits.s_ref_m, without.s_ref_m)
    assert with_limits.saturation_step_count.tolist() == [0, 0]
    assert without.force_limits_N is None


def test_from_params_default_on_and_switch_off() -> None:
    params = load_params(level="top")
    fns = [make_motion_function(0.3) for _ in range(4)]
    on = L1SpeedActuator.from_params(params, [object()] * 4, fns, [0.3] * 4)
    off = L1SpeedActuator.from_params(params, [object()] * 4, fns, [0.3] * 4,
                                      force_saturation=False)
    # per leg (legs.<leg>.cylinder.*, REXOME35); one float while the legs are equal (old YAML)
    ext, ret = leg_force_limits_N(params)
    expected = tuple(v[0] if all(x == v[0] for x in v) else v for v in (ext, ret))
    assert on.force_limits_N == expected
    assert off.force_limits_N is None


def test_single_leg_extend_saturation_v11b_subset() -> None:
    """Extend into the 218 kN limit and hold the command: V11b force and settled motion."""
    params = load_params(level="top")
    model = SingleLegModel(params, "FL")
    v = params.actuator.max_speed_m_s
    a = run_schedule(model, [(0.0, 0.0), (0.05, v), (1.6, -v)], 1.8)
    # start: spring at rest, the motor holds the rod weight
    assert a["F_cyl"][0] == pytest.approx(-model.rod_mass_kg * params.meta.gravity_m_s2, rel=1e-3)
    f_ext, f_ret = model.actuator.force_limits_N
    ana = v11b_analysis(a, f_ext_N=f_ext, f_ret_N=f_ret, v_max_m_s=v)
    checks = {c.id: c for c in v11b_checks(ana, f_ext_N=f_ext, f_ret_N=f_ret,
                                           ramp_s=model.actuator.ramp_s, dt_s=model.dt_s)}
    assert checks["V11b.extend.reached"].passed
    assert checks["V11b.extend.force"].passed
    assert checks["V11b.extend.motion"].passed
    assert checks["V11b.reverse_to_retract.steps"].passed
    ext = ana["phases"][0]
    # creep until the static force reaches the limit is about c v / k (module docstring)
    creep = model.spring_c_N_s_m * v / model.spring_k_N_m
    assert 0.5 * creep < ext["creep_from_first_m"] < 1.5 * creep
