"""L2b rod-side law (hydraulics/l2b_rod_side, dynamics_model.md rev. 33 5.20.2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.params import load_params

DT = 1.0e-4


@pytest.fixture(scope="module")
def p2():
    return load_params(level="top", model="L2b_NSC")


def _law(p2, armed=True):
    return L2bRodSide.from_params(p2, [0, 1, 2, 3], armed=armed, mechanics="one_sided_parallel")


def _k2_at(law, s):
    return np.array([law.k2_N_m(i, s[i]) for i in range(4)])


def test_rev33_leg_parameters_match_the_reference_block(p2) -> None:
    """k_h, k_r, k_2, k_1 and the knee at e_op equal reference.json L2b_NSC_reference_rev33 /
    leg_parameters / k_of_s_table / e_op (6 printed digits)."""
    law = _law(p2)
    e = p2.contact.rigid_floor.L1.operating_extension_m
    k_h = [29424100.0, 29424100.0, 21554400.0, 21554400.0]
    k_r = [10805100.0, 10805100.0, 8748520.0, 8748520.0]
    k2 = [25905700.0, 25905700.0, 19504600.0, 19504600.0]
    k1 = [33929000.0, 33929000.0, 26402100.0, 26402100.0]
    for i in range(4):
        assert law.head_stiffness_N_m(i, e[i]) == pytest.approx(k_h[i], rel=5e-6)
        assert law.rod_stiffness_N_m(i, e[i]) == pytest.approx(k_r[i], rel=5e-6)
        assert law.k2_N_m(i, e[i]) == pytest.approx(k2[i], rel=5e-6)
        assert law.k1_N_m(i, e[i]) == pytest.approx(k1[i], rel=5e-6)
    a = p2.l2b.actuator
    assert a.damping_lock_N_s_m == pytest.approx((34403.5, 34403.5, 30348.5, 30348.5), rel=2e-6)
    assert a.damping_moving_N_s_m == pytest.approx((100206.0, 100206.0, 86949.0, 86949.0),
                                                   rel=1e-5)


def test_locks_without_a_force_step_and_follows_k1_then_k2(p2) -> None:
    law = _law(p2)
    s = np.array(p2.contact.rigid_floor.L1.operating_extension_m)
    c0 = 4.0e-3
    c = np.full(4, c0)
    f0 = law.spring_force_N(DT, DT, np.zeros(4), s, c, np.zeros(4))
    assert np.all(law.locked)
    np.testing.assert_allclose(f0, _k2_at(law, s) * c0, rtol=1e-12)
    # small increment below the knee: slope k1
    knee = np.array([law.knee_force_N(i) for i in range(4)])
    k1 = np.array([law.k1_lock(i) for i in range(4)])
    k2 = np.array([law.k2_lock(i) for i in range(4)])
    dc = 0.5 * knee / k1
    f1 = law.spring_force_N(2 * DT, DT, np.zeros(4), s, c + dc, f0)
    np.testing.assert_allclose(f1 - f0, k1 * dc, rtol=1e-12)
    # beyond the knee: slope k2 (rod side at the floor)
    big = 3.0 * knee / k1
    f2 = law.spring_force_N(3 * DT, DT, np.zeros(4), s, c + big, f1)
    np.testing.assert_allclose(f2 - f0, knee + k2 * (big - knee / k1), rtol=1e-9)
    assert law.mode() == ["FLOOR"] * 4
    # knee after an extension at e_op = reference 4.09 / 3.17 kN
    assert knee == pytest.approx([4089.04, 4089.04, 3170.13, 3170.13], rel=1e-5)


def test_unloading_is_unclipped_and_pressure_rises(p2) -> None:
    """A locked rod that unloads (hanging) gets a negative force on k1; rod pressure rises."""
    law = _law(p2)
    s = np.full(4, 0.3)
    law.spring_force_N(DT, DT, np.zeros(4), s, np.full(4, 1e-3), np.zeros(4))
    f = law.spring_force_N(2 * DT, DT, np.zeros(4), s, np.full(4, -1e-4), np.zeros(4))
    k1 = np.array([law.k1_lock(i) for i in range(4)])
    k2 = np.array([law.k2_lock(i) for i in range(4)])
    np.testing.assert_allclose(f, k2 * 1e-3 + k1 * (-1.1e-3), rtol=1e-12)
    assert np.all(f < 0.0)
    assert np.all(law.rod_pressure_Pa > 2.0e5)


def test_release_decays_with_tau(p2) -> None:
    law = _law(p2)
    s = np.full(4, 0.4)
    c = np.full(4, 4e-3)
    law.spring_force_N(DT, DT, np.zeros(4), s, c, np.zeros(4))
    law.spring_force_N(2 * DT, DT, np.zeros(4), s, c + 1e-4, np.zeros(4))  # k1 part
    locked = law.spring_force_N(3 * DT, DT, np.zeros(4), s, c + 1e-4, np.zeros(4))
    moving0 = law.spring_force_N(4 * DT, DT, np.full(4, 1e-3), s, c + 1e-4, np.zeros(4))
    assert not np.any(law.locked)
    np.testing.assert_allclose(moving0, locked, rtol=1e-12)  # residual carried, no step
    tau = p2.l2b.rod_side.release_tau_s
    later = law.spring_force_N(4 * DT + tau, DT, np.full(4, 1e-3), s, c + 1e-4, np.zeros(4))
    head = _k2_at(law, s) * (c + 1e-4)
    np.testing.assert_allclose(later - head, (locked - head) * math.exp(-1.0), rtol=1e-9)


def test_lock_after_retract_uses_yaml_pressure(p2) -> None:
    law = _law(p2)
    s = np.full(4, 0.4)
    c = np.full(4, 3e-3)
    law.spring_force_N(DT, DT, np.full(4, -1e-3), s, c, np.zeros(4))  # retracting
    law.spring_force_N(2 * DT, DT, np.zeros(4), s, c, np.zeros(4))  # locks
    np.testing.assert_allclose(law.rod_pressure_Pa, p2.l2b.rod_side.p_r0_after_retract_Pa)


def test_disarmed_is_head_only_and_state_round_trip(p2) -> None:
    law = _law(p2, armed=False)
    s = np.full(4, 0.35)
    c = np.full(4, 2e-3)
    f = law.spring_force_N(DT, DT, np.zeros(4), s, c, np.zeros(4))
    np.testing.assert_allclose(f, _k2_at(law, s) * c, rtol=0)
    law.arm()
    rng = np.random.default_rng(3)
    for k in range(50):
        u = rng.choice([0.0, 1e-3, -1e-3], size=4)
        law.spring_force_N((k + 2) * DT, DT, u, s + rng.normal(0, 1e-3, 4),
                           c + rng.normal(0, 1e-4, 4), np.zeros(4))
    state = law.state_arrays()
    twin = _law(p2)
    twin.restore_state(state)
    for k in range(50, 120):
        u = rng.choice([0.0, 1e-3, -1e-3], size=4)
        args = ((k + 2) * DT, DT, u, s + rng.normal(0, 1e-3, 4), c + rng.normal(0, 1e-4, 4),
                np.zeros(4))
        np.testing.assert_array_equal(law.spring_force_N(*args), twin.spring_force_N(*args))
