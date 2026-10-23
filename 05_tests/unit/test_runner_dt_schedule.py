"""Runner with a variable step size (``runner.DtSchedule``, S6 RE1b-F / RE1b-P transition dt)."""

from __future__ import annotations

import numpy as np
import pytest
from test_runner_fake_engine import FakeEngine, Spy, _suite

from outrigger_sim.runner import DtSchedule, RunnerError, run_closed_loop


class FakeEngineDt(FakeEngine):
    def __init__(self, dt=1e-3):
        super().__init__(dt=dt)
        self.dts: list[float] = []
        self.captures: list[float] = []

    def set_dt(self, dt):
        self.dt = float(dt)

    def step(self, *, capture=False):
        self.dts.append(self.dt)
        if capture:
            self.captures.append(round(self.t + self.dt, 9))
        return super().step(capture=capture)


def test_no_schedule_is_the_fixed_step_loop() -> None:
    a = run_closed_loop(FakeEngine(dt=1e-3), Spy(), _suite(), 0.1, run_meta={}, placement=None)
    b = run_closed_loop(FakeEngineDt(dt=1e-3), Spy(), _suite(), 0.1, run_meta={},
                        placement=None, dt_schedule=DtSchedule(1e-3, 0.02))
    assert a.n_control == b.n_control == 5 and a.n_steps == b.n_steps == 100
    for k in ("t", "u_cmd", "meas.specific_force"):
        np.testing.assert_allclose(a.record.arrays[k], b.record.arrays[k], rtol=0, atol=1e-12)


def test_window_opened_by_the_observer_keeps_the_control_grid() -> None:
    eng = FakeEngineDt(dt=1e-3)
    sched = DtSchedule(1e-3, 0.02)
    spy = Spy()

    def observe(meas, _cmd):
        if abs(meas.t_s - 0.04) < 1e-9:
            sched.open(meas.t_s, 1e-4, "test")
        if abs(meas.t_s - 0.08) < 1e-9:
            sched.close(meas.t_s)

    res = run_closed_loop(eng, spy, _suite(), 0.12, run_meta={}, placement=None,
                          on_control=observe, dt_schedule=sched, capture_every_s=5e-3)
    assert res.n_control == 6
    assert res.record.arrays["t"].tolist() == pytest.approx([0.02 * k for k in range(1, 7)])
    assert res.n_steps == 40 + 400 + 40  # 0-0.04 at 1 ms, 0.04-0.08 at 0.1 ms, then 1 ms
    assert eng.dts[39] == 1e-3 and eng.dts[40] == 1e-4 and eng.dts[-1] == 1e-3
    # control-period average stays a time average across the window (sin(2 pi t) exact mean)
    m = spy.seen[2]  # period (0.04, 0.06] at 0.1 ms
    ts = 0.04 + 1e-4 * np.arange(1, 201)
    assert m.specific_force_m_s2[0] == pytest.approx(np.mean(np.sin(2 * np.pi * ts)))
    assert all(round(c / 5e-3, 6) == round(c / 5e-3) for c in eng.captures)
    segs = res.meta["dt_segments"]
    assert [s["dt_s"] for s in segs] == [1e-3, 1e-4, 1e-3]
    assert segs[1]["t0_s"] == pytest.approx(0.04) and segs[1]["t1_s"] == pytest.approx(0.08)


def test_schedule_rejects_a_dt_that_does_not_divide_the_period() -> None:
    sched = DtSchedule(1e-3, 0.02)
    with pytest.raises(RunnerError):
        sched.open(0.0, 3e-3)
    with pytest.raises(RunnerError):
        run_closed_loop(FakeEngine(dt=1e-3), Spy(), _suite(), 0.04, placement=None,
                        dt_schedule=DtSchedule(1e-3, 0.02))  # engine without set_dt


class DriftingEngine(FakeEngineDt):
    """Step-time sum that drifts (no rounding, 1e-7 relative per step)."""

    def step(self, *, capture=False):
        self.dts.append(self.dt)
        if capture:
            self.captures.append(self.t + self.dt)
        self.s = self.s + self.u * self.dt
        self.t = self.t + self.dt * (1.0 + 1.0e-7)
        if self.callback is not None:
            self.callback(self)
        self.u = self.pending.copy()
        return self.t


def test_extra_captures_survive_a_drifting_step_sum() -> None:
    """RE3 lesson: an exact-grid test stopped capturing once the summed times drifted."""
    eng = DriftingEngine(dt=1e-4)
    sched = DtSchedule(1e-4, 0.02)
    run_closed_loop(eng, Spy(), _suite(), 1.0, run_meta={}, placement=None, dt_schedule=sched,
                    capture_every_s=1e-3)
    caps = np.array(eng.captures)
    gaps = np.diff(caps)
    assert caps.size >= 990 and gaps.max() < 1.5e-3
