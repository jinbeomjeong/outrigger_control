"""verify/metrics multi-output ERA (S4 V7 cross-check, beta sensitivity frequencies).

Synthetic free decays with known frequencies, damping ratios and shapes: the six L1 modes of
the top level (close modes 5.8 / 6.4 / 7.6 / 8.0 Hz, plan risk #14) on six channels.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.verify.metrics import (
    era_free_decay,
    mass_mac,
    modal_amplitudes,
    projection_leakage,
    select_era_mode,
)

F_HZ = np.array([1.7983, 3.0046, 5.8191, 6.4214, 7.6073, 7.9996])
ZETA = np.array([0.00783, 0.014, 0.0372, 0.0362, 0.0323, 0.0491])


def _system(seed: int = 3):
    rng = np.random.default_rng(seed)
    m = np.diag(rng.uniform(1.0, 4.0, 6))
    a = rng.normal(size=(6, 6))
    q, _ = np.linalg.qr(a)
    phi = np.linalg.inv(np.sqrt(m)) @ q  # mass-normalised: phi^T M phi = I
    return m, phi


def _free_decay(phi, amps, phases, t, f=F_HZ, zeta=ZETA):
    wn = 2.0 * math.pi * f
    wd = wn * np.sqrt(1.0 - zeta**2)
    eta = amps * np.exp(-np.outer(t, zeta * wn)) * np.cos(np.outer(t, wd) + phases)
    return eta @ phi.T, eta


def _matched(era, phi, m, f=F_HZ):
    out = []
    for i in range(6):
        k = select_era_mode(era, i, phi, m, float(f[i]))
        assert k is not None
        out.append(era.modes[k])
    return out


@pytest.mark.parametrize("order", [12, 20])
def test_era_recovers_six_close_modes_noise_free(order: int) -> None:
    m, phi = _system()
    t = np.arange(0.0, 20.0, 5e-3)
    amps = np.array([1.0, 0.8, 0.5, 0.6, 0.4, 0.3])
    y, _ = _free_decay(phi, amps, np.linspace(0.1, 2.0, 6), t)
    era = era_free_decay(t, y, order=order, channel_scale=np.sqrt(np.diag(m)))
    got = _matched(era, phi, m)
    f = np.array([g.f_undamped_Hz for g in got])
    z = np.array([g.zeta for g in got])
    assert np.allclose(f, F_HZ, rtol=1e-7)
    assert np.allclose(z, ZETA, rtol=1e-5)
    assert era.residual_rms_rel < 1e-8
    for i, g in enumerate(got):
        assert mass_mac(g.shape, phi[:, i], m) > 1.0 - 1e-9
        # start amplitude of eta_i from the ERA shape = the synthetic amplitude
        assert modal_amplitudes(era, phi, m)[i, era.modes.index(g)] == pytest.approx(
            amps[i], rel=1e-6
        )


def test_era_with_noise_and_short_window() -> None:
    m, phi = _system(7)
    rng = np.random.default_rng(11)
    t = np.arange(0.0, 2.0, 5e-3)
    amps = np.array([0.2, 0.2, 1.0, 1.0, 1.0, 1.0])
    y, _ = _free_decay(phi, amps, np.zeros(6), t)
    y = y + 1e-4 * np.std(y) * rng.normal(size=y.shape)
    era = era_free_decay(t, y, order=24, channel_scale=np.sqrt(np.diag(m)))
    got = _matched(era, phi, m)
    for i in range(2, 6):  # the high modes are the 2-s window targets
        assert got[i].f_undamped_Hz == pytest.approx(F_HZ[i], rel=1e-4)
        assert got[i].zeta == pytest.approx(ZETA[i], rel=1e-2)


def test_projection_leakage_zero_for_pure_mode_and_positive_for_mixed() -> None:
    m, phi = _system()
    t = np.arange(0.0, 2.0, 5e-3)
    y, _ = _free_decay(phi, np.array([0, 0, 1.0, 0, 0, 0]), np.zeros(6), t)
    era = era_free_decay(t, y, order=2)
    k = select_era_mode(era, 2, phi, m, float(F_HZ[2]))
    assert projection_leakage(era, 2, k, phi, m) < 1e-8
    # a contaminated "eta_2": shapes that are not the reference columns mix the modes
    phi_wrong = phi.copy()
    phi_wrong[:, 2] = phi[:, 2] + 0.3 * phi[:, 3]
    y2, _ = _free_decay(phi_wrong, np.array([0, 0, 1.0, 1.0, 0, 0]), np.zeros(6), t)
    era2 = era_free_decay(t, y2, order=4)
    k2 = select_era_mode(era2, 2, phi, m, float(F_HZ[2]))
    assert era2.modes[k2].f_undamped_Hz == pytest.approx(F_HZ[2], rel=1e-7)
    assert projection_leakage(era2, 2, k2, phi, m) == pytest.approx(0.0, abs=1e-8)
    assert projection_leakage(era2, 3, 1 - k2, phi, m) > 0.1


def test_exclusive_selection_skips_a_leaking_close_neighbour() -> None:
    m, phi = _system(5)
    t = np.arange(0.0, 2.0, 5e-3)
    shapes = phi.copy()
    shapes[:, 4] = phi[:, 4] + 0.2 * phi[:, 5]  # mode 5 leaks into eta_6
    y, _ = _free_decay(shapes, np.array([0, 0, 0, 0, 10.0, 0.5]), np.zeros(6), t)
    era = era_free_decay(t, y, order=4, channel_scale=np.sqrt(np.diag(m)))
    k_greedy = select_era_mode(era, 5, phi, m, float(F_HZ[5]), exclusive=False)
    k_excl = select_era_mode(era, 5, phi, m, float(F_HZ[5]))
    assert era.modes[k_greedy].f_undamped_Hz == pytest.approx(F_HZ[4], rel=1e-6)
    assert era.modes[k_excl].f_undamped_Hz == pytest.approx(F_HZ[5], rel=1e-6)
    assert era.modes[k_excl].zeta == pytest.approx(ZETA[5], rel=1e-5)


def test_era_input_checks() -> None:
    t = np.arange(0.0, 1.0, 1e-2)
    y = np.sin(2 * math.pi * 3 * t)
    with pytest.raises(ValueError):
        era_free_decay(t, y, order=50, n_block_rows=10)
    with pytest.raises(ValueError):
        era_free_decay(np.r_[t[:-1], 2.0], y, order=2)
    era = era_free_decay(t, y, order=2, n_block_rows=10)
    assert era.modes[0].f_undamped_Hz == pytest.approx(3.0, rel=1e-9)
    assert era.modes[0].zeta == pytest.approx(0.0, abs=1e-9)
