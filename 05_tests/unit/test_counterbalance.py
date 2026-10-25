"""S8 counterbalance option (hydraulics/counterbalance; spec s8_seal_friction_counterbalance.md 4)."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from outrigger_sim.hydraulics.counterbalance import Counterbalance, cb_rod_pressure_Pa
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.params import load_params

DT = 1.0e-4


@pytest.fixture(scope="module")
def p2():
    return load_params(level="top", model="L2b_NSC")


def _single_leg_case(cb_params, ramp_s: float, dt: float = 1.0e-4):
    """Spec 4.5 test rig: front cylinder, V1 = A_p x 0.40 m, beta 1 GPa, B_p 33.9 kN s/m, mass
    9,690 kg + spring 4.77 kN/mm; load 0 -> 116.3 kN (0-1 s), hold, 2 s -> 700 kN in ramp_s."""
    a_p, beta, b_p, m, k_s = 0.013273229, 1.0e9, 33.9e3, 9690.0, 4.77e6
    v0 = a_p * 0.40
    cb = Counterbalance(cb_params, [a_p], [0.0037699])

    def load(t):
        if t < 1.0:
            return 116.3e3 * t
        if t < 2.0:
            return 116.3e3
        return 116.3e3 + (700e3 - 116.3e3) * min((t - 2.0) / ramp_s, 1.0)

    x = v = vout = t = p = 0.0
    p_max = 0.0
    for _ in range(round(6.0 / dt)):
        p = beta * (a_p * x - vout) / v0
        v += (load(t) - p * a_p - b_p * v - k_s * x) / m * dt
        x += v * dt
        t += dt
        p = beta * (a_p * x - vout) / v0
        p_max = max(p_max, p)
        dv, _ = cb.step(dt, [True], [p], [0.0])
        vout += float(dv[0])
    return p, p_max, vout, cb


def _rig_params(p2):
    # Hopsan rig: relief cracking 330 bar g, no pilot / tank shift (p_T 0), head side only
    return dataclasses.replace(p2.l2b.counterbalance, tank_pressure_Pa=0.0, sides="head")


def test_case_a_slow_ramp_matches_reference(p2) -> None:
    """C-9 (5): spec 4.5 case A, final p_h 329.9 bar g +-0.5 %, discharge 553.6 cm^3 +-1 %,
    max 346.3 bar g (+-1 %)."""
    p, p_max, vout, cb = _single_leg_case(_rig_params(p2), ramp_s=2.0)
    assert p / 1e5 == pytest.approx(329.9, rel=5e-3)
    assert vout * 1e6 == pytest.approx(553.6, rel=1e-2)
    assert p_max / 1e5 == pytest.approx(346.3, rel=1e-2)
    assert cb.open_count_head[0] == 1
    assert cb.dissipation_J[0] > 0.0


def test_case_b_fast_ramp_within_transient_allowance(p2) -> None:
    """Spec 4.5 case B (5 ms ramp): max 600.4 bar g (spec model), allowance 5 % (transient)."""
    p, p_max, vout, _ = _single_leg_case(_rig_params(p2), ramp_s=0.005, dt=2.0e-5)
    assert p_max / 1e5 == pytest.approx(600.4, rel=0.05)
    assert p / 1e5 == pytest.approx(328.1, rel=0.01)
    assert vout * 1e6 == pytest.approx(554.8, rel=0.02)


def test_effective_cracking_and_closed_below(p2) -> None:
    cb = Counterbalance(p2.l2b.counterbalance, [0.0133] * 4, [0.0038] * 4)
    assert cb.p_cr_eff_Pa == pytest.approx(324e5)
    dv_h, dv_r = cb.step(DT, [True] * 4, [300e5] * 4, [250e5] * 4)
    assert np.all(dv_h == 0.0) and np.all(dv_r == 0.0)
    # moving legs: element off even above cracking
    dv_h, _ = cb.step(DT, [False] * 4, [400e5] * 4, [0.0] * 4)
    assert np.all(dv_h == 0.0) and np.all(cb.y_head == 0.0)


def test_tau_zero_and_rated_flow(p2) -> None:
    prm = dataclasses.replace(p2.l2b.counterbalance, tau_s=0.0)
    cb = Counterbalance(prm, [0.0133], [0.0038])
    # at p_cr,eff + override: rated flow 1e-3 m^3/s
    dv, _ = cb.step(DT, [True], [cb.p_cr_eff_Pa + prm.override_Pa], [0.0])
    assert dv[0] == pytest.approx(1.0e-3 * DT, rel=1e-12)
    assert cb.y[0] == pytest.approx(1.0)


def test_blocked_line_caps_the_discharge(p2) -> None:
    prm = dataclasses.replace(p2.l2b.counterbalance, discharge="blocked_line", tau_s=0.0)
    cb = Counterbalance(prm, [0.0133], [0.0038])
    for _ in range(1000):
        cb.step(DT, [True], [cb.p_cr_eff_Pa + 10e5], [0.0])
    assert cb.volume_head_m3[0] == pytest.approx(prm.blocked_line_capacity_m3, rel=1e-12)


def test_rod_regulation_table(p2) -> None:
    """Spec 4.3 table (static loads 118.1 / 72.1 kN, p_set 330 bar g, p_back 2 bar g)."""
    a = p2.l2b.actuator
    a_r = p2.l2b.rod_side.annulus_area_m2

    def pr(i, d, f, psi):
        return cb_rod_pressure_Pa(d, f, a.head_area_m2[i], a_r[i], 330e5, psi, 2e5,
                                  -0.913e5, 210e5) / 1e5

    ext, ret = RodChamberMode.EXT, RodChamberMode.RET
    assert pr(0, ext, 118.1e3, 3.0) == pytest.approx(34.1, abs=0.06)
    assert pr(0, ret, 118.1e3, 3.0) == pytest.approx(73.4, abs=0.06)
    assert pr(2, ext, 72.1e3, 3.0) == pytest.approx(51.4, abs=0.06)
    assert pr(2, ret, 72.1e3, 3.0) == pytest.approx(76.3, abs=0.06)
    assert pr(0, ext, 118.1e3, 4.0) == pytest.approx(2.0, abs=1e-9)
    assert pr(0, ret, 118.1e3, 4.0) == pytest.approx(56.3, abs=0.06)
    assert pr(2, ext, 72.1e3, 4.0) == pytest.approx(11.4, abs=0.06)
    assert pr(2, ret, 72.1e3, 4.0) == pytest.approx(58.7, abs=0.06)
    assert pr(0, ret, 118.1e3, 8.0) == pytest.approx(29.1, abs=0.06)
    assert pr(2, ret, 72.1e3, 8.0) == pytest.approx(30.5, abs=0.06)


def _locked_oil(p2, cb=None):
    law = L2bRodSide.from_params(p2, [0, 1, 2, 3], mechanics="one_sided_parallel", oil_only=True,
                                 counterbalance=cb)
    s = np.array(p2.contact.rigid_floor.L1.operating_extension_m)
    c = np.full(4, 3.0e-3)
    law.spring_force_N(DT, DT, np.zeros(4), s, c, np.zeros(4))
    assert np.all(law.locked)
    return law, s, c


def test_head_shift_drops_head_force_only(p2) -> None:
    """Spec 4.2: s_ref -= delta with the anchor shift -> force drops k_h delta, p_r unchanged."""
    law, s, c = _locked_oil(p2)
    f0 = np.array([law.oil_force_N(i, c[i]) for i in range(4)])
    law.refresh_readings(c)
    pr0 = law.rod_pressure_Pa
    delta = 20e-6
    for i in range(4):
        law.shift_head(i, delta)
    law.refresh_readings(c - delta)
    f1 = np.array([law.oil_force_N(i, c[i] - delta) for i in range(4)])
    k_h = np.array([law.head_stiffness_N_m(i, s[i]) for i in range(4)])
    np.testing.assert_allclose(f0 - f1, k_h * delta, rtol=1e-9)
    np.testing.assert_allclose(law.rod_pressure_Pa, pr0, rtol=0, atol=1e-6)


def test_rod_vent_lowers_rod_pressure(p2) -> None:
    law, s, c = _locked_oil(p2)
    law.refresh_readings(c)
    pr0 = law.rod_pressure_Pa.copy()
    f0 = np.array([law.oil_force_N(i, c[i]) for i in range(4)])
    dv = 1.0e-7  # 0.76 bar: stays above the 0.1 bar abs floor from 2 bar g
    law.vent_rod(0, dv)
    law.refresh_readings(c)
    k_r, a_r = law.rod_stiffness_N_m(0, s[0]), law.annulus_area_m2[0]
    assert pr0[0] - law.rod_pressure_Pa[0] == pytest.approx(k_r * dv / a_r**2, rel=1e-9)
    assert law.oil_force_N(0, c[0]) - f0[0] == pytest.approx(k_r * dv / a_r, rel=1e-9)


def test_cb_lock_pressure_after_extension(p2) -> None:
    """With the CB, p_r0 at the lock instant follows the regulation (4.3), not the YAML 2 bar."""
    cb = dataclasses.replace(p2.l2b.counterbalance, pilot_ratio=3.0)
    law = L2bRodSide.from_params(p2, [0, 1, 2, 3], mechanics="one_sided_parallel", oil_only=True,
                                 counterbalance=cb)
    s = np.array(p2.contact.rigid_floor.L1.operating_extension_m)
    f_static = np.array([118.1e3, 118.1e3, 72.1e3, 72.1e3])
    c = f_static / np.array([law.head_stiffness_N_m(i, s[i]) for i in range(4)])
    # extend one step, then lock with the static pressure force
    law.spring_force_N(DT, DT, np.full(4, 1e-3), s, c, f_static)
    law.spring_force_N(2 * DT, DT, np.zeros(4), s, c, f_static)
    table = law.lock_table()
    assert np.array(table["p_r0_Pa"]) / 1e5 == pytest.approx([34.1, 34.1, 51.4, 51.4], abs=0.06)
