"""S3 V checks (chrono_build_plan.md S3, 3.4): V4 lift, V5, V8(a).

``sim``: the touch phase of the V4 lift at dt 2e-4 s from the S2b crawler snapshot (15.4 s
simulated, about 25 s wall) and V5 FL +1 mm at dt 2e-4 s (about 15 s). ``slow``: the judged V4
run (windowed 1e-4 / 1e-5 s, about 2.5 min) and V8(a) on the pads at dt 2e-4 s (about 1.5 min),
both through the job functions of ``04_scripts/02_chrono/run_S3.py`` (the judging run with every
case is ``run_S3.py run``; summary ``06_analysis/01_chrono/verify_S3_L1.json``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.batch import Case  # noqa: E402
from outrigger_sim.chrono.runs import run_commanded  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_snapshot  # noqa: E402
from outrigger_sim.scenarios.crawler_settle import crawler_static_pose  # noqa: E402
from outrigger_sim.scenarios.lift import equivalent_origin_from_trajectory, lift_plan  # noqa: E402
from outrigger_sim.verify.reference import (  # noqa: E402
    L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
    LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
    load_references,
)
from outrigger_sim.verify.s3 import V4_TOUCH_TOL_S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STATES = ROOT / "07_results" / "states"


def _script():
    path = ROOT / "04_scripts" / "02_chrono" / "run_S3.py"
    spec = importlib.util.spec_from_file_location("run_S3_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_S3_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _failed(checks):
    return [(c["id"], c["item"], c["value"], c["ref"], c["tol"]) for c in checks if not c["passed"]]


@pytest.mark.sim
def test_v4_touch_phase_at_2e4() -> None:
    params = load_params(level="top")
    refs = load_references()
    touch_ref = refs.get(LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D)
    plan = lift_plan(params, reference_touch_eq_s=touch_ref,
                     first_rocking_Hz=refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level="top")[0])
    m = _script()
    model = m._crawler_model(params, crawler_static_pose(params), 2.0e-4)
    snap = load_snapshot("S2b_crawler_top", params_sha256=params.sha256, directory=STATES)
    model.restore(snap)
    t0 = float(model.system.GetChTime())
    model.actuator.set_soft_limits(hi_m=plan.e_op_m)
    run = run_commanded(model, 15.4, plan.schedule(), sample_s=0.01)
    t = run.series["t"] - t0
    t_eq = equivalent_origin_from_trajectory(t, run.series["s_ref"][:, 0],
                                             params.actuator.max_speed_m_s, 1.0, 14.0)
    assert t_eq == pytest.approx(params.actuator.command_ramp_s / 2 + 1.0e-4, abs=1e-9)
    touch = run.first_positive_N_t_s - t0 - t_eq
    assert np.all(np.abs(touch - np.asarray(touch_ref)) <= V4_TOUCH_TOL_S)
    assert [e.kind for e in run.events] == [1, 1, 1, 1]
    assert run.max_motor_violation_m < 1e-9


@pytest.mark.sim
def test_v5_plus_1mm_at_2e4(tmp_path) -> None:
    m = _script()
    out = m.job_v5(Case("v5", {"kind": "v5", "dt": 2.0e-4}), tmp_path)
    plus1 = [c for c in out.summary["checks"] if "+1 mm" in c["item"]]
    assert plus1 and not _failed(plus1)


@pytest.mark.slow
def test_v4_judged_run(tmp_path) -> None:
    m = _script()
    out = m.job_v4(Case("v4_D_w1e-04", m.case_settings("v4_D_w1e-04") | {"record": False}),
                   tmp_path)
    assert not _failed(out.summary["checks"])


@pytest.mark.slow
def test_v8a_pads_at_2e4(tmp_path) -> None:
    m = _script()
    out = m.job_v8a(Case("v8a_pads_dt2e-04", m.case_settings("v8a_pads_dt2e-04")), tmp_path)
    assert not _failed(out.summary["checks"])
