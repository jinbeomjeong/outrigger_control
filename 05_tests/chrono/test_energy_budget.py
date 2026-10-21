"""S4 energy budget on Chrono: ground-bushing slip accumulators and ``EnergyBudget``.

* Block on a 30 deg slope (the stick-friction baseline, ``conftest.block_factory``): the
  return-mapping accumulators give ``sum mu N |delta a|`` = ``mu W cos(a) x slip`` and
  ``D_slip / sum mu N |delta a|`` just above 1.
* L1 model from the S1 settled snapshot: at rest the budget residual stays at the J level;
  right after a rigid horizontal kick the kinetic term is ``1/2 M v^2``; after the kick (all
  bushings yield) the residual is small, first order in ``dt`` and closed by the four
  discrete shares (anchor lag, bushing implicit, kinetic implicit, contact explicit), the slip
  ratio is in 1.00-1.05, and the SMC contact damping model reproduces Chrono's pad forces.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.energy import EnergyBudget, energy_residual_J  # noqa: E402
from outrigger_sim.params import Params  # noqa: E402

pytestmark = pytest.mark.chrono

S1_SNAPSHOT = "S1_L1_top"


def test_block_slide_slip_accumulators(block_factory: Callable[..., Any]) -> None:
    model = block_factory(30.0)
    for _ in range(4000):
        model.step()
    gb = model.bushing
    slip = float(np.linalg.norm(gb.slip_total_m[0]))
    assert gb.yield_steps[0] > 1000 and slip > 1e-3
    a = math.radians(30.0)
    mu = 0.5
    coulomb = float(gb.slip_coulomb_work_J[0])
    # N per step follows W cos(a) up to the contact oscillation; the slip is along one line
    assert coulomb == pytest.approx(mu * model.weight_N * math.cos(a) * slip, rel=0.01)
    ratio = float(gb.slip_dissipation_J[0]) / coulomb
    assert 1.0 < ratio < 1.05


def _s1_model(params_top: Params, root: Path, dt: float) -> Any:
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose
    from outrigger_sim.verify.reference import load_references

    refs = load_references()
    sp = analytic_static_pose(params_top, refs, operating_extensions_m(params_top))
    model = L1Model(params_top, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt)
    snap = load_snapshot(
        S1_SNAPSHOT, params_sha256=params_top.sha256, directory=root / "07_results" / "states"
    )
    model.restore(snap)
    return model


@pytest.fixture(scope="module")
def params_top() -> Params:
    from outrigger_sim.params import load_params

    return load_params(level="top")


def _kick_run(params_top: Params, root: Path, dt: float, t_s: float, v: tuple[float, float]):
    from outrigger_sim.chrono.runs import set_rigid_velocity

    model = _s1_model(params_top, root, dt)
    cog = model.superstructure.GetPos()
    set_rigid_velocity(model, (v[0], v[1], 0.0), (0.0, 0.0, 0.0), (cog.x, cog.y, cog.z))
    budget = EnergyBudget(model)
    e0 = budget.read()
    for _ in range(round(t_s / dt)):
        model.step()
        budget.after_step(model.dt_s)
    return model, budget, e0, budget.read()


def test_budget_at_rest(params_top: Params, project_root: Path) -> None:
    model, budget, e0, e1 = _kick_run(params_top, project_root, 2.0e-4, 0.2, (0.0, 0.0))
    assert e0.kinetic < 1e-3
    assert abs(energy_residual_J(e0, e1)) < 1.0  # J, against ~1e3 J of contact spring energy
    assert e1.dissipated_slip == 0.0 and e1.motor_work == pytest.approx(0.0, abs=1e-6)
    assert budget.crawler_contact_max_N == 0.0


def test_budget_after_kick(params_top: Params, project_root: Path) -> None:
    v = (0.4, 0.3)
    out = {}
    for dt in (1.0e-4, 2.0e-4):
        model, budget, e0, e1 = _kick_run(params_top, project_root, dt, 0.6, v)
        mass = sum(float(b.GetMass()) for b in model.bodies)
        # rel 2e-5: cross term with the ~1e-6 m/s residual motion of the snapshot
        assert e0.kinetic == pytest.approx(0.5 * mass * (v[0] ** 2 + v[1] ** 2), rel=2e-5)
        assert np.all(model.bushing.yield_steps > 0)
        assert 1.0 < e1.dissipated_slip / e1.slip_coulomb_work < 1.05
        # SMC Hooke damping c_n = g_n m_eff and Chrono's clip reproduce the pad forces
        # (geometric delta against Bullet's float32 distance)
        assert budget.contact_force_check_max_N < 20.0
        out[dt] = energy_residual_J(e0, e1)
        assert abs(out[dt]) / e0.kinetic < 0.03
        # the four discrete shares close the residual (dyn rev. 19 diagnostics)
        shares = e1.bushing_lag + e1.bushing_implicit + e1.kinetic_implicit + e1.contact_explicit
        assert abs(out[dt] - shares) < 0.05 * abs(out[dt])
        t_dev, leg_dev = budget.contact_force_check_max_at
        assert 0 <= leg_dev < 4 and e0.t_s < t_dev <= e1.t_s
    # first order in dt (dissipative integration / anchor-lag error)
    assert out[2.0e-4] / out[1.0e-4] == pytest.approx(2.0, rel=0.2)
