"""M2 revision 5 on the L2b rod-side law: extend lock anchor (hydraulics-expert ``r5_spec.md``,
user decision B 2026-11-07): ``p_r0 = max(p_ext + max(p_tr - p*, 0), p_floor)`` with M2 on,
``p_ext`` with M2 off. One law object with two legs (FL, RL), column coordinate 0.30 m frozen,
F 94 kN, dt 1e-4 s; the leg first locks after a retract (anchor ``p_ret`` 34.818 bar), then
extends and stops (cases U1-U10).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw, flow_limited_rod_pressure

BAR = 1.0e5
DT_S = 1.0e-4
V_MAX = 0.0209243016
S_M = 0.30
FORCE_N = 94.0e3
BETA = 1.0e9
L0 = 0.05
STROKE = 0.7
P_EXT, P_RET, P_FLOOR_ABS = 2.0e5, 34.818e5, 0.1e5
P_FLOOR = P_FLOOR_ABS - 101325.0
P_STAR = 5.0e5
TAU = 0.05
HEAD = np.array([0.013273229, 0.00950331778])
ANNULUS = np.array([0.00376991118, 0.00314159265])


def _law(*, m2: bool, k_out: float = math.inf, closing_delay_s: float = 0.0) -> L2bRodSide:
    law = L2bRodSide(head_area_m2=HEAD, annulus_area_m2=ANNULUS, k_out_N_m=[k_out] * 2,
                     bulk_modulus_Pa=BETA, head_dead_length_m=L0, rod_dead_length_m=[L0] * 2,
                     stroke_m=STROKE, p_r0_after_extend_Pa=[P_EXT] * 2,
                     p_r0_after_retract_Pa=[P_RET] * 2, p_floor_abs_Pa=P_FLOOR_ABS,
                     release_tau_s=TAU, lock_eps_m_s=1.0e-6, closing_delay_s=closing_delay_s)
    if m2:
        law.set_rod_pressure_flow_law(RodPressureFlowLaw())
    return law


class _Drive:
    def __init__(self, law: L2bRodSide, force_N: float = FORCE_N) -> None:
        self.law = law
        self.t = 0.0
        self.s = np.full(2, S_M)
        self.c = force_N / (BETA * HEAD / (L0 + S_M))
        self.f = np.full(2, force_N)

    def step(self, u: float) -> np.ndarray:
        out = self.law.spring_force_N(self.t, DT_S, np.full(2, u), self.s, self.c, self.f)
        self.t += DT_S
        return out

    def retract_lock(self, hold_s: float = 6 * DT_S) -> None:
        for _ in range(20):
            self.step(-0.01 * V_MAX)
        for _ in range(round(hold_s / DT_S)):
            self.step(0.0)

    def extend(self, fraction: float, duration_s: float) -> np.ndarray:
        for _ in range(round(duration_s / DT_S)):
            self.step(fraction * V_MAX)
        return self.law.rod_pressure_Pa


def _replica(leg: int, fraction: float, duration_s: float) -> float:
    """Independent one-leg lag (the spec replica): ``round(T / dt)`` steps from ``p_ret``."""
    k_h = BETA * HEAD[leg] / (L0 + S_M)
    k_r = BETA * ANNULUS[leg] / (STROKE - S_M + L0)
    c_r = ANNULUS[leg] ** 2 * (1.0 / k_r + 1.0 / k_h)
    p = P_RET
    for _ in range(round(duration_s / DT_S)):
        p = flow_limited_rod_pressure(p, P_STAR, fraction * V_MAX, DT_S, TAU, c_r, HEAD[leg],
                                      ANNULUS[leg], False)
    return p


def _closed_form(leg: int, fraction: float, duration_s: float) -> float:
    k_h = BETA * HEAD[leg] / (L0 + S_M)
    k_r = BETA * ANNULUS[leg] / (STROKE - S_M + L0)
    c_r = ANNULUS[leg] ** 2 * (1.0 / k_r + 1.0 / k_h)
    x = fraction * V_MAX * duration_s
    root = math.sqrt(P_RET - 2.0e5) - HEAD[leg] * x / (2.0 * c_r * math.sqrt(10.0e5))
    return max(2.0e5 + max(root, 0.0) ** 2, P_STAR)


def _anchor_after(fraction: float, duration_s: float,
                  **law_kwargs) -> tuple[np.ndarray, np.ndarray]:
    drive = _Drive(_law(**law_kwargs))
    drive.retract_lock()
    p_tr = drive.extend(fraction, duration_s).copy()
    drive.step(0.0)
    return p_tr, drive.law.lock_anchor_rod_pressure_Pa


@pytest.mark.parametrize("fraction, duration_s, expected_bar", [
    (0.01, 0.5, (20.7957, 22.4655)),   # U1
    (0.10, 0.1, (12.0179, 14.6757)),   # U2
    (0.01, 1.0, (12.0211, None)),      # U2b
    (0.25, 0.1, (6.0354, None)),       # U3b (lag limited)
])
def test_u1_u3b_anchor_is_the_replica(fraction, duration_s, expected_bar) -> None:
    p_tr, anchor = _anchor_after(fraction, duration_s, m2=True)
    for leg in range(2):
        replica = _replica(leg, fraction, duration_s)
        assert p_tr[leg] == pytest.approx(replica, rel=1e-12)
        assert anchor[leg] == pytest.approx(P_EXT + replica - P_STAR, rel=1e-12)
        if expected_bar[leg] is not None:
            assert anchor[leg] / BAR == pytest.approx(expected_bar[leg], abs=5e-5)
        if fraction == 0.01:
            closed = _closed_form(leg, fraction, duration_s)
            assert p_tr[leg] == pytest.approx(closed, abs=0.01 * BAR)


def test_u3_finished_decompression_keeps_p_ext() -> None:
    _p_tr, anchor = _anchor_after(0.01, 5.0, m2=True)
    assert np.all(np.abs(anchor - P_EXT) <= 1e-6)


def test_u4_hanging_leg_keeps_p_ext() -> None:
    drive = _Drive(_law(m2=True), force_N=-40.0e3)
    drive.retract_lock()
    drive.extend(0.01, 1.0)
    drive.step(0.0)
    assert drive.law.lock_anchor_rod_pressure_Pa[0] == pytest.approx(P_EXT, abs=1e-3)


def test_u5_m2_off_keeps_p_ext() -> None:
    _p_tr, anchor = _anchor_after(0.01, 0.5, m2=False)
    assert np.array_equal(anchor, np.full(2, P_EXT))


def test_lock_hook_force_is_the_moving_value_and_rod_reading_steps_to_the_anchor() -> None:
    forces, readings = {}, {}
    for m2 in (True, False):
        drive = _Drive(_law(m2=m2))
        drive.retract_lock()
        drive.extend(0.01, 0.5)
        forces[m2] = drive.step(0.0)
        readings[m2] = drive.law.rod_pressure_Pa
        anchor = drive.law.lock_anchor_rod_pressure_Pa
        assert np.array_equal(readings[m2], anchor)
        head = drive.law.head_pressure_Pa(forces[m2])
        assert np.allclose(head, (forces[m2] + readings[m2] * ANNULUS) / HEAD, rtol=0, atol=1e-6)
    assert np.array_equal(forces[True], forces[False])  # F_lock = f_before: no step in F


@pytest.mark.parametrize("k_out", [math.inf, 3.0e8])
def test_knee_of_the_r5_anchor(k_out) -> None:
    drive = _Drive(_law(m2=True, k_out=k_out))
    drive.retract_lock()
    drive.extend(0.01, 0.5)
    drive.step(0.0)
    law = drive.law
    k_h = BETA * HEAD / (L0 + S_M)
    k_r = BETA * ANNULUS / (STROKE - S_M + L0)
    knee = (law.lock_anchor_rod_pressure_Pa - P_FLOOR) * ANNULUS * (k_h + k_r) / k_r
    assert knee[0] / 1e3 == pytest.approx(45.23, abs=0.01)  # U1 FL table
    assert knee[1] / 1e3 == pytest.approx(35.91, abs=0.01)  # U1 RL table
    for leg in range(2):
        assert law.knee_force_N(leg) == pytest.approx(knee[leg], rel=1e-9)
        dc_knee = law.knee_force_N(leg) / law.k1_lock(leg)
        c_lock = drive.c[leg]
        assert law.oil_slope_N_m(leg, c_lock + 0.5 * dc_knee) == law.k1_lock(leg)
        assert law.oil_slope_N_m(leg, c_lock + 1.5 * dc_knee) == law.k2_lock(leg)


def test_u7_closing_delay_gives_the_same_anchor() -> None:
    _p_tr, plain = _anchor_after(0.01, 0.5, m2=True)
    drive = _Drive(_law(m2=True, closing_delay_s=0.05))
    drive.retract_lock(hold_s=0.06)
    assert np.array_equal(drive.law.lock_anchor_rod_pressure_Pa, np.full(2, P_RET))
    drive.extend(0.01, 0.5)
    for _ in range(round(0.06 / DT_S)):
        drive.step(0.0)
    assert np.all(drive.law.locked)
    # t_c holds the tracked pressure (u = 0 drains nothing), so the anchor is the U1 one
    assert np.array_equal(drive.law.lock_anchor_rod_pressure_Pa, plain)


def test_u9_snapshot_continuation_is_bit_identical() -> None:
    _p_tr, whole = _anchor_after(0.01, 0.5, m2=True)
    first = _Drive(_law(m2=True))
    first.retract_lock()
    first.extend(0.01, 0.2)
    second = _Drive(_law(m2=True))
    second.law.restore_state(first.law.state_arrays())
    second.t = first.t
    second.extend(0.01, 0.3)
    second.step(0.0)
    assert np.array_equal(second.law.lock_anchor_rod_pressure_Pa, whole)


@pytest.mark.parametrize("m2", [True, False])
def test_u10_retract_lock_keeps_p_ret(m2) -> None:
    drive = _Drive(_law(m2=m2))
    drive.retract_lock()
    assert np.array_equal(drive.law.lock_anchor_rod_pressure_Pa, np.full(2, P_RET))


def test_u8_m1c_seed_moves_only_the_release_start() -> None:
    drive = _Drive(_law(m2=True))
    drive.retract_lock()
    drive.extend(0.01, 0.5)
    drive.step(0.0)
    anchor = drive.law.lock_anchor_rod_pressure_Pa.copy()
    locked_p = drive.law.rod_pressure_Pa.copy()
    drive.law.seed_release_pressure(0, 7.0 * BAR)
    drive.step(0.01 * V_MAX)
    start = drive.law.releases_of_last_call[0]
    assert start.start_pressure_Pa == 7.0 * BAR
    assert start.drop_Pa == pytest.approx(anchor[0] - locked_p[0], abs=1e-6)


def test_first_lock_after_arming_keeps_p_ext_even_above_the_target() -> None:
    """The EXT direction and the tracked p_ext at the arming are initial values, not an
    extension: a leg that has not moved locks at p_ext (here 34.818 bar > p* 5 bar)."""
    law = L2bRodSide(head_area_m2=HEAD, annulus_area_m2=ANNULUS, k_out_N_m=[math.inf] * 2,
                     bulk_modulus_Pa=BETA, head_dead_length_m=L0, rod_dead_length_m=[L0] * 2,
                     stroke_m=STROKE, p_r0_after_extend_Pa=[P_RET] * 2,
                     p_r0_after_retract_Pa=[P_RET] * 2, p_floor_abs_Pa=P_FLOOR_ABS,
                     release_tau_s=TAU, lock_eps_m_s=1.0e-6)
    law.set_rod_pressure_flow_law(RodPressureFlowLaw())
    drive = _Drive(law)
    drive.step(0.0)
    assert np.array_equal(law.lock_anchor_rod_pressure_Pa, np.full(2, P_RET))
    # after an extension the r5 rule applies
    drive.extend(0.01, 0.5)
    drive.step(0.0)
    assert np.all(law.lock_anchor_rod_pressure_Pa > P_RET)


def test_extended_flag_is_a_snapshot_key_with_m2_only() -> None:
    assert "m2_extended_since_arm" in _law(m2=True).state_arrays()
    assert "m2_extended_since_arm" not in _law(m2=False).state_arrays()


def test_meta_key_only_with_m2() -> None:
    assert "lock_anchor_after_extend" in _law(m2=True).meta()
    assert "lock_anchor_after_extend" not in _law(m2=False).meta()
