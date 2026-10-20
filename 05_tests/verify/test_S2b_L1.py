"""S2b V checks (chrono_build_plan.md S2b, 3.4): crawler settle and R15 touch / lift events.

``sim``: crawler settle on the analytic exact pose (top, 3 s, about 5 s wall) and the fast FL
event at dt 1e-4 s (3.3 s simulated, about 6 s). ``slow``: the same event at dt 1e-5 s and the
1 ms event-time rule (about 45 s). The judging run with every case and the Records is
``04_scripts/02_chrono/run_S2b.py all``; this test uses the same library functions.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.model import L1Model  # noqa: E402
from outrigger_sim.chrono.runs import run_commanded  # noqa: E402
from outrigger_sim.frames import roll_pitch_from_quat  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.scenarios.crawler_settle import (  # noqa: E402
    crawler_static_pose,
    pad_touch_extension_m,
)
from outrigger_sim.scenarios.stroke import event_cases  # noqa: E402
from outrigger_sim.verify.s2b import event_checks, event_dt_checks  # noqa: E402


def _failed(results):
    return [(r.id, r.item, r.value, r.ref, r.tol) for r in results if not r.passed]


@pytest.mark.sim
def test_crawler_settle_holds_the_analytic_pose() -> None:
    params = load_params(level="top")
    pose = crawler_static_pose(params)
    model = L1Model(
        params,
        pose=BodyPose(pose.origin_m, pose.quat_wxyz),
        extensions_m=(0.0, 0.0, 0.0, 0.0),
        attach_bushings=False,
        actuator=True,
    )
    run = run_commanded(model, 3.0, lambda _t: None, sample_s=0.1)
    roll, pitch = roll_pitch_from_quat(run.series["quat"][-10:])
    assert np.degrees(pitch).mean() == pytest.approx(pose.pitch_deg, abs=1e-4)
    assert np.degrees(roll).mean() == pytest.approx(pose.roll_deg, abs=1e-4)
    assert run.series["origin"][-10:, 2].mean() == pytest.approx(pose.u_z_m, abs=1e-6)
    spheres = model.crawler_sphere_contacts()
    assert int(np.sum(spheres.force_world_N[:, 2] > 0.0)) == 14
    assert not run.events
    assert run.max_motor_violation_m < 1e-9


def _event(dt_s: float):
    params = load_params(level="top")
    case = event_cases(params)[0]  # fast FL
    pose = crawler_static_pose(params)
    ext = [0.0, 0.0, 0.0, 0.0]
    for _ in range(3):
        ext[0] = pad_touch_extension_m(params, 0, pose.origin_m, pose.quat_wxyz) - case.start_gap_m
        pose = crawler_static_pose(params, tuple(ext))
    model = L1Model(
        params,
        pose=BodyPose(pose.origin_m, pose.quat_wxyz),
        extensions_m=tuple(ext),
        attach_bushings=False,
        actuator=True,
        dt_s=dt_s,
    )
    sched = case.schedule()
    run = run_commanded(model, sched.end_s, sched, sample_s=0.01)
    t0 = run.t_start_s
    return case, [[e.t_s - t0, e.leg, e.kind] for e in run.events]


@pytest.mark.sim
def test_event_fast_dt_1e4() -> None:
    case, events = _event(1.0e-4)
    assert not _failed(event_checks("fast_FL", events, case.expected_events()))


@pytest.mark.sim
@pytest.mark.slow
def test_event_fast_dt_pair_within_1ms() -> None:
    case, coarse = _event(1.0e-4)
    _, fine = _event(1.0e-5)
    assert not _failed(event_checks("fast_FL dt1e-5", fine, case.expected_events()))
    assert not _failed(event_dt_checks("fast_FL", coarse, fine))
