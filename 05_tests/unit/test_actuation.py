"""Engine-independent speed reference (``outrigger_sim.actuation``, plan S7 force law s_ref)."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.actuation import SATURATION_STOP_S, SpeedReference

V_MAX = 0.0209243016
RAMP = 0.1
DT = 1e-4
F_EXT = 278737.808
F_RET = 79168.1349


def _ref(s0=0.3, limits=True, rod=None):
    kw = {"max_force_extend_N": F_EXT, "max_force_retract_N": F_RET} if limits else {}
    return SpeedReference(
        [s0], [(0.0, 0.7)], max_speed_m_s=V_MAX, ramp_s=RAMP, rod_mass_kg=rod, **kw
    )


def test_ramp_reaches_v_max_in_ramp_time_and_integrates() -> None:
    r = _ref(limits=False)
    r.set_command([1.0])
    s0 = r.s_ref_m[0]
    n = round(RAMP / DT)
    for _ in range(n):
        r.advance(DT)
    assert r.u_applied_m_s[0] == pytest.approx(V_MAX, rel=1e-9)
    # trapezoid: sum of u_k dt = a dt^2 n(n+1)/2
    a = V_MAX / RAMP
    assert r.s_ref_m[0] - s0 == pytest.approx(a * DT * DT * n * (n + 1) / 2, rel=1e-9)


def test_brakes_exactly_onto_the_stroke_end() -> None:
    r = _ref(s0=0.69, limits=False)
    r.set_command([1.0])
    for _ in range(20000):
        r.advance(DT)
    assert r.s_ref_m[0] == pytest.approx(0.7, abs=1e-12)
    assert r.u_applied_m_s[0] == 0.0


def test_saturation_decelerates_in_t_sat_and_holds() -> None:
    r = _ref()
    r.set_command([1.0])
    for _ in range(round(RAMP / DT) + 10):
        r.advance(DT, cylinder_force_N=[100e3])
    assert r.u_applied_m_s[0] == pytest.approx(V_MAX)
    steps = 0
    while r.u_applied_m_s[0] > 0.0:
        r.advance(DT, cylinder_force_N=[F_EXT])
        steps += 1
    assert steps == pytest.approx(SATURATION_STOP_S / DT, abs=1)
    assert r.saturation_start_count[0] == 1
    s_hold = r.s_ref_m[0]
    for _ in range(100):  # start from rest in the saturated direction stays 0
        r.advance(DT, cylinder_force_N=[F_EXT * 1.001])
    assert r.s_ref_m[0] == s_hold
    # below the limit the leg resumes with the command ramp
    r.advance(DT, cylinder_force_N=[F_EXT - 1.0])
    assert r.u_applied_m_s[0] == pytest.approx(V_MAX / RAMP * DT)


def test_retract_saturation_and_opposite_command_followed() -> None:
    r = _ref()
    r.set_command([-1.0])
    for _ in range(50):
        r.advance(DT, cylinder_force_N=[-F_RET])
    assert r.u_applied_m_s[0] == 0.0
    assert r.saturated[0]
    r.set_command([1.0])
    r.advance(DT, cylinder_force_N=[-F_RET])
    assert r.u_applied_m_s[0] > 0.0
    assert not r.saturated[0]


def test_without_rod_mass_the_judged_force_is_the_force() -> None:
    r = _ref()
    r.set_command([1.0])
    for _ in range(5):
        r.advance(DT, cylinder_force_N=[1234.5])
    assert r.last_judged_force_N[0] == 1234.5
    r2 = _ref(rod=[106.78])
    r2.set_command([1.0])
    for _ in range(5):
        r2.advance(DT, cylinder_force_N=[1234.5])
    assert r2.last_judged_force_N[0] == pytest.approx(1234.5 - 106.78 * V_MAX / RAMP)


def test_state_round_trip_is_bit_exact() -> None:
    rng = np.random.default_rng(3)
    a = _ref()
    for _ in range(300):
        a.set_command([rng.uniform(-0.03, 0.03)])
        a.advance(DT, cylinder_force_N=[rng.uniform(-9e4, 3e5)])
    b = _ref()
    b.restore_state(a.state_arrays())
    for _ in range(300):
        cmd, f = [rng.uniform(-0.03, 0.03)], [rng.uniform(-9e4, 3e5)]
        for r in (a, b):
            r.set_command(cmd)
            r.advance(DT, cylinder_force_N=f)
        assert a.s_ref_m[0] == b.s_ref_m[0]
        assert a.u_applied_m_s[0] == b.u_applied_m_s[0]


def test_bad_inputs_raise() -> None:
    with pytest.raises(ValueError):
        SpeedReference([0.8], [(0.0, 0.7)], max_speed_m_s=V_MAX, ramp_s=RAMP)
    with pytest.raises(ValueError):
        SpeedReference(
            [0.1], [(0.0, 0.7)], max_speed_m_s=V_MAX, ramp_s=RAMP, max_force_extend_N=1.0
        )
    with pytest.raises(ValueError):
        _ref().advance(0.0)
