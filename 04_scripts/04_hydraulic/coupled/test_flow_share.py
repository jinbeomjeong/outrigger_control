"""Checks of flow_share.share: criteria V-1, V-2, the law limits and the on/off switch.

Run: conda run -n hydraulics-dev python -I -m pytest <this file> (from this folder).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from flow_share import share, smin  # noqa: E402
from params import load_params  # noqa: E402

P = load_params()
CFG = P.share_config()
RNG = np.random.default_rng(20261104)
LOADS = np.array([89.8e5, 88.3e5, 76.9e5, 75.0e5])


def test_smin_is_exact_outside_the_band():
    assert smin(10.0, 13.0, 2.0) == 10.0
    assert smin(13.0, 10.0, 2.0) == 10.0
    assert smin(10.0, 10.0, 2.0) == pytest.approx(10.0 - 0.5)


@pytest.mark.parametrize("law", ["priority", "proportional"])
def test_demand_met_returns_the_command_exactly(law):
    """V-1: at eta 0.95 four legs at v_max are within the 1e-6 supply tolerance."""
    cfg = P.with_(law=law).share_config()
    u = np.full(4, P.v_max)
    r = share(u, LOADS, P.Q_pump(0.95), cfg)
    assert np.array_equal(r.v, u)
    assert not r.limited.any()


def test_off_switch_returns_the_command():
    u = np.full(4, P.v_max)
    r = share(u, LOADS, P.Q_pump(0.5), P.with_(flow_limit=False).share_config())
    assert np.array_equal(r.v, u)


@pytest.mark.parametrize("eta", [0.95, 0.90, 0.85])
@pytest.mark.parametrize("law", ["priority", "proportional"])
def test_flow_never_above_supply(eta, law):
    """V-2: sum Q_i <= Q_sup (1 + 1e-6), and v = u wherever the demand is met and no LS shortage."""
    cfg = P.with_(law=law).share_config()
    Q_sup = P.Q_pump(eta)
    for _ in range(300):
        u = RNG.uniform(-P.v_max, P.v_max, 4) * RNG.choice([0.0, 1.0], 4, p=[0.2, 0.8])
        load = RNG.uniform(0.0, 150e5, 4)
        r = share(u, load, Q_sup, cfg)
        assert r.Q.sum() <= Q_sup * (1 + 1e-6)
        if r.Q_dem <= Q_sup * 0.999:
            assert np.allclose(r.v, u, atol=1e-12)
        assert np.all(np.abs(r.v) <= np.abs(u) + 1e-15)


def test_priority_slows_the_highest_load_first():
    r = share(np.full(4, P.v_max), LOADS, P.Q_pump(0.90), CFG)
    assert r.v[0] < r.v[1] < r.v[2]
    assert r.Q.sum() + r.Q_byp == pytest.approx(P.Q_pump(0.90), rel=1e-6)


def test_proportional_scales_all_legs_alike():
    r = share(np.full(4, P.v_max), LOADS, P.Q_pump(0.85), P.with_(law="proportional").share_config())
    assert np.ptp(r.v) == pytest.approx(0.0, abs=1e-9)
    assert r.v[0] / P.v_max == pytest.approx(0.85 / 0.95, rel=1e-4)
