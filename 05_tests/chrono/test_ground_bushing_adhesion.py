"""S9 adhesion argument of ``GroundBushingCoulomb`` (``dynamics_model.md`` 5.33.7 #4, 5.33.11).

* Regression: a short sliding L1 four-leg case (``05_tests/data/make_ground_bushing_l1_ref.py``,
  reference written with the code before the argument existed, commit 8616be9) is bit-identical
  with the default (no adhesion) and with adhesion passed explicitly as 0 per leg.
* Limit: the return-mapping limit is ``mu N + c A min(1, N / N_c)``; a block on a 30 deg slope
  with ``mu`` 0.5 slides at ``F_t = limit`` and sticks once ``c A`` is large enough.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.ground_bushing import (  # noqa: E402
    ADHESION_FULL_NORMAL_N,
    GroundBushingCoulomb,
    PadBushingSpec,
)
from outrigger_sim.chrono.system import make_smc_material, make_system  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

pytestmark = pytest.mark.chrono

DATA = Path(__file__).resolve().parents[1] / "data"
REF = DATA / "ground_bushing_l1_slide_ref.npy"  # + .json layout (HEAD 8616be9 code)


def _ref_module():
    spec = importlib.util.spec_from_file_location("make_gb_ref", DATA / "make_ground_bushing_l1_ref.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("adhesion", [None, (0.0, 0.0, 0.0, 0.0)], ids=["default", "explicit_zero"])
def test_l1_sliding_case_bit_identical(adhesion) -> None:
    mod = _ref_module()
    ref = mod.load_reference()
    got = mod.run_case(adhesion)
    assert int(ref["yield"][-1].sum()) > 1000  # the limit path really runs
    for key in ref:
        assert np.array_equal(got[key], ref[key], equal_nan=True), key


def _block(adhesion_N: float, *, mass_kg: float = 1000.0, slope_deg: float = 30.0):
    """Block on a slope (gravity tilted) with one bushing; returns (system, block, bushing)."""
    params = load_params(level="top")
    bundle = make_system(params, "L1", floor_plate=False)
    s = bundle.system
    floor = bundle.floor
    floor.EnableCollision(True)
    mat = make_smc_material(1.0e8, 0.0)
    floor.AddCollisionShape(ch.ChCollisionShapeBox(mat, 4.0, 4.0, 0.4), ch.ChFramed(ch.ChVector3d(0, 0, -0.2)))
    block = ch.ChBody()
    block.SetMass(mass_kg)
    block.SetInertiaXX(ch.ChVector3d(10, 10, 10))
    r = 0.05
    block.SetPos(ch.ChVector3d(0, 0, r - mass_kg * 9.80665 / 1.0e8))
    block.EnableCollision(True)
    block.AddCollisionShape(ch.ChCollisionShapeSphere(make_smc_material(1.0e8, 0.0), r), ch.ChFramed())
    s.Add(block)
    a = math.radians(slope_deg)
    g = 9.80665
    s.SetGravitationalAcceleration(ch.ChVector3d(g * math.sin(a), 0.0, -g * math.cos(a)))
    spec = PadBushingSpec("blk", block, (0.0, 0.0, 0.0), r, 1.0e6, 2.2e4, adhesion_N=adhesion_N)  # zeta ~0.7
    bushing = GroundBushingCoulomb(s, floor, [spec], friction=0.5, slip_damping_reenable_speed_m_s=1e-3,
                                   dt_s=bundle.dt_s)
    bushing.attach()
    return s, block, bushing, bundle.dt_s, mass_kg * g * math.cos(a), mass_kg * g * math.sin(a)


def test_limit_formula() -> None:
    s, block, bushing, dt, n, t = _block(5000.0)
    lim = bushing.tangential_limit_N([0.0])[0]
    assert lim == 0.0
    assert bushing.tangential_limit_N([5000.0])[0] == pytest.approx(0.5 * 5000.0 + 5000.0 * 0.5)
    assert bushing.tangential_limit_N([2.0e4])[0] == pytest.approx(0.5 * 2.0e4 + 5000.0)
    assert bushing.adhesion_full_normal_N == ADHESION_FULL_NORMAL_N


def _run(adhesion_N: float, t_end: float = 0.6):
    s, block, bushing, dt, n_expected, t_load = _block(adhesion_N)
    xs, fts = [], []
    for _ in range(round(t_end / dt)):
        s.DoStepDynamics(dt)
        bushing.after_step()
        xs.append(block.GetPos().x)
        fts.append(-bushing.tangential_force_world_N()[0][0])
    return np.array(xs), np.array(fts), bushing, n_expected, t_load


def test_slides_at_mohr_coulomb_limit() -> None:
    # W sin 30 = 4903 N > mu N = 4247 N; adhesion 300 N x min(1, 8493 / 1e4) -> limit 4502 N:
    # slides at the limit (1-step lag excess about 1 %, L1 block test)
    x, ft, bushing, n, t = _run(300.0)
    late = slice(len(x) // 2, None)
    assert bushing.yield_steps[0] > 100
    expected = 0.5 * n + 300.0 * min(1.0, n / ADHESION_FULL_NORMAL_N)
    assert np.mean(ft[late]) == pytest.approx(expected, rel=0.015)


def test_sticks_with_enough_adhesion() -> None:
    # adhesion 6000 N -> limit about 9.3 kN > 4903 N: after the first touch-down steps (SMC
    # normal force builds up from 0, limit 0 then) the block sticks: no further yield, no drift
    x, ft, bushing, n, t = _run(6000.0)
    assert bushing.yield_steps[0] < 50  # touch-down only
    assert x[-1] == pytest.approx(t / 1.0e6, rel=2e-3)  # elastic offset W sin(a) / k, no slip
    assert ft[-1] == pytest.approx(t, rel=2e-3)
