"""Runner ``stop_when`` (S8 run end rule, ``s6_control_spec.md`` rev. 43 C-S8-17)."""

from __future__ import annotations

import numpy as np
import pytest
from test_runner_dt_schedule import FakeEngineDt
from test_runner_fake_engine import FakeEngine, Spy, _suite

from outrigger_sim.runner import DtSchedule, run_closed_loop


def test_stop_when_ends_at_a_control_instant() -> None:
    seen: list[float] = []

    def observe(meas, _cmd):
        seen.append(meas.t_s)

    res = run_closed_loop(FakeEngine(dt=1e-3), Spy(), _suite(), 1.0, run_meta={},
                          placement=None, on_control=observe,
                          stop_when=lambda: seen[-1] >= 0.06 - 1e-9)
    assert res.n_control == 3 and res.n_steps == 60
    assert res.meta["stopped_early"] is True
    assert res.meta["run_length_s"] == pytest.approx(0.06)
    assert res.meta["duration_upper_s"] == 1.0
    assert res.record.arrays["t"].tolist() == pytest.approx([0.02, 0.04, 0.06])


def test_stop_when_never_true_runs_the_upper_bound() -> None:
    res = run_closed_loop(FakeEngine(dt=1e-3), Spy(), _suite(), 0.1, run_meta={},
                          placement=None, stop_when=lambda: False)
    assert res.n_control == 5 and res.n_steps == 100
    assert res.meta["stopped_early"] is False


def test_without_stop_when_the_meta_is_unchanged() -> None:
    res = run_closed_loop(FakeEngine(dt=1e-3), Spy(), _suite(), 0.1, run_meta={},
                          placement=None)
    assert "stopped_early" not in res.meta


def test_stop_when_with_a_dt_schedule() -> None:
    eng = FakeEngineDt(dt=1e-3)
    sched = DtSchedule(1e-3, 0.02)
    seen: list[float] = []

    def observe(meas, _cmd):
        seen.append(meas.t_s)
        if abs(meas.t_s - 0.04) < 1e-9:
            sched.open(meas.t_s, 1e-4, "test")

    res = run_closed_loop(eng, Spy(), _suite(), 1.0, run_meta={}, placement=None,
                          on_control=observe, dt_schedule=sched,
                          stop_when=lambda: seen[-1] >= 0.08 - 1e-9)
    assert res.n_control == 4
    assert res.n_steps == 40 + 400
    assert eng.dt == 1e-3  # restored to the base step after the early end
    np.testing.assert_allclose(res.record.arrays["t"], [0.02, 0.04, 0.06, 0.08], atol=1e-9)
    assert res.meta["stopped_early"] is True
