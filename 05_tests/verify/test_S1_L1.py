"""S1 V checks (chrono_build_plan.md S1, 3.4): level statics from the analytic start.

``sim``: top level, settle 10 s + still 5 s (about 20 s wall on a P-core). ``slow``: the
53 s cross-check without the analytic start. The judging run with all levels, records and
snapshots is ``04_scripts/02_chrono/run_S1.py all``; this test uses the same functions.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.model import (  # noqa: E402
    L1Model,
    operating_extensions_m,
    run_settle,
    zero_pose,
)
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.scenarios.settle import (  # noqa: E402
    SETTLE_S,
    STILL_S,
    analytic_static_pose,
    cross_settle_s,
)
from outrigger_sim.verify.reference import load_references  # noqa: E402
from outrigger_sim.verify.s1 import v1_v3_checks, v13_checks  # noqa: E402


def _failed(results):
    return [(r.id, r.item, r.value, r.ref, r.tol) for r in results if not r.passed]


@pytest.mark.sim
def test_s1_top_analytic_start() -> None:
    params = load_params(level="top")
    refs = load_references()
    start = analytic_static_pose(params, refs, operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(start.origin_m, start.quat_wxyz))
    run = run_settle(model, SETTLE_S, STILL_S)
    assert not run.events
    results = v1_v3_checks(params, refs, run.stats) + v13_checks(refs, run.stats)
    assert not _failed(results)


@pytest.mark.sim
@pytest.mark.slow
def test_s1_top_cross_without_analytic_start() -> None:
    params = load_params(level="top")
    refs = load_references()
    model = L1Model(params, pose=zero_pose(params, operating_extensions_m(params)))
    run = run_settle(model, cross_settle_s(params), STILL_S)
    results = v1_v3_checks(params, refs, run.stats) + v13_checks(refs, run.stats)
    assert not _failed(results)
