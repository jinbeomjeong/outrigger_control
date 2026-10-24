"""R8 runner options (s6_control_spec.md rev. 31 148): IMU 100 Hz samples (R-1), double-delay
guard (R-4), output time offset (R-5). Engine-free (fake engine of test_runner_fake_engine)."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.runner import RunnerError, run_closed_loop
from outrigger_sim.sensors.averaging import ControlPeriodAverager
from outrigger_sim.sensors.hydraulic import LegSensorConfig
from outrigger_sim.sensors.imu import ImuErrorConfig
from outrigger_sim.sensors.suite import SensorSuite
from outrigger_sim.signals import Command, Measurements

from test_runner_fake_engine import FakeEngine  # noqa: E402  (same test folder)


class Spy:
    def __init__(self, period=0.1, d=None):
        self.period = period
        self.d = d
        self.seen: list[Measurements] = []

    @property
    def period_s(self):
        return self.period

    def reset(self):
        self.seen.clear()

    def update(self, m):
        self.seen.append(m)
        return Command(t_s=m.t_s, leg_speed_m_s=np.full(4, 0.001 * len(self.seen)))

    def meta(self):
        out = {"controller": "spy"}
        if self.d is not None:
            out["timing"] = {"d": self.d}
        return out


def _suite(sample_period_s, **imu):
    return SensorSuite(ImuErrorConfig(sample_period_s=sample_period_s, **imu), LegSensorConfig(),
                       seed=3)


# --- averager --------------------------------------------------------------------------------


def _feed(averager, times, rng):
    outs = []
    prev = None
    for t in times:
        f = rng.normal(size=3)
        w = rng.normal(size=3)
        out = averager.add(t, f, w)
        if out is not None:
            outs.append(out)
        prev = t
    del prev
    return outs


def test_period_mean_bit_identical_with_sub_samples() -> None:
    times = np.round(2e-4 * np.arange(1, 2001), 12)  # 0.4 s
    a = _feed(ControlPeriodAverager(0.1, 0.0), times, np.random.default_rng(5))
    b = _feed(ControlPeriodAverager(0.1, 0.0, sample_period_s=0.01), times,
              np.random.default_rng(5))
    assert len(a) == len(b) == 4
    for x, y in zip(a, b, strict=True):
        assert x.t_s == y.t_s
        assert np.array_equal(x.specific_force_m_s2, y.specific_force_m_s2)
        assert np.array_equal(x.angular_rate_rad_s, y.angular_rate_rad_s)
        assert x.sample_t_s is None and y.sample_t_s.shape == (10,)
        assert y.sample_specific_force_m_s2.shape == (10, 3)
        # equal sub-periods: the mean of the 10 box means is the period mean
        assert np.allclose(y.sample_specific_force_m_s2.mean(axis=0), y.specific_force_m_s2,
                           rtol=0, atol=1e-14)


def test_equal_sample_period_is_the_plain_average() -> None:
    av = ControlPeriodAverager(0.02, 0.0, sample_period_s=0.02)
    assert av.sample_period_s is None and av.samples_per_period == 1


def test_constant_input_samples_equal_the_truth() -> None:
    av = ControlPeriodAverager(0.1, 0.0, sample_period_s=0.01)
    f = np.array([0.1, -0.2, 9.8])
    out = None
    for t in np.round(2e-4 * np.arange(1, 501), 12):
        out = av.add(t, f, np.zeros(3)) or out
    assert out is not None
    assert np.allclose(out.sample_specific_force_m_s2, f, rtol=1e-15, atol=0)


def test_sample_boundaries_on_the_10ms_grid_across_a_dt_window() -> None:
    """2e-4 s steps, a 1e-5 s window from 0.13 to 0.17 s, 2e-4 s again (spec 148 R-1)."""
    t, times = 0.0, []
    while t < 0.3 - 1e-12:
        dt = 1e-5 if 0.13 - 1e-12 <= t < 0.17 - 1e-12 else 2e-4
        t += dt  # summed float steps, as the engine does
        times.append(t)
    av = ControlPeriodAverager(0.1, 0.0, sample_period_s=0.01)
    outs = [o for o in (av.add(x, np.array([x, 0.0, 9.8]), np.zeros(3)) for x in times) if o]
    assert len(outs) == 3
    grid = np.concatenate([o.sample_t_s for o in outs])
    assert np.allclose(grid, 0.01 * np.arange(1, 31), atol=1e-9)
    # linear input x = t: each box mean is the box midpoint (step-end samples, weight = step)
    for o in outs:
        for k, tk in enumerate(o.sample_t_s):
            lo = tk - 0.01
            sel = [x for x in times if lo + 1e-9 < x <= tk + 1e-9]
            w = np.diff(np.concatenate([[lo], sel]))
            assert o.sample_specific_force_m_s2[k, 0] == pytest.approx(
                np.sum(np.asarray(sel) * w) / np.sum(w), rel=1e-9)


# --- runner ----------------------------------------------------------------------------------


def test_runner_delivers_ten_imu_samples() -> None:
    eng = FakeEngine(dt=1e-3)
    spy = Spy(period=0.1)
    res = run_closed_loop(eng, spy, _suite(0.01), 0.3, placement=None)
    assert res.n_control == 3
    assert res.meta["imu_samples_per_period"] == 10
    for m in spy.seen:
        s = m.imu_specific_force_samples_m_s2
        assert s.shape == (10, 3)
        for k in range(10):
            ts = m.t_s - 0.1 + 0.01 * k + 1e-3 * np.arange(1, 11)
            assert s[k, 0] == pytest.approx(np.mean(np.sin(2 * np.pi * ts)), abs=1e-12)
        assert np.allclose(m.specific_force_m_s2, s.mean(axis=0), rtol=0, atol=1e-15)


def test_imu_noise_applied_per_sample() -> None:
    density = 1e-3
    eng = FakeEngine(dt=1e-3)
    spy = Spy(period=0.1)
    run_closed_loop(eng, spy, _suite(0.01, accel_noise_density_m_s2_rtHz=density), 20.0,
                    placement=None)
    resid = np.concatenate([m.imu_specific_force_samples_m_s2[:, 2] for m in spy.seen]) - 9.8
    sigma = density * np.sqrt(1.0 / (2.0 * 0.01))
    assert np.std(resid) == pytest.approx(sigma, rel=0.05)


def test_r7_without_samples_has_no_sample_field() -> None:
    eng = FakeEngine(dt=1e-3)
    spy = Spy(period=0.02)
    res = run_closed_loop(eng, spy, _suite(0.02), 0.06, placement=None)
    assert all(m.imu_specific_force_samples_m_s2 is None for m in spy.seen)
    assert "imu_samples_per_period" not in res.meta


def test_double_delay_is_refused() -> None:
    with pytest.raises(RunnerError, match="twice"):
        run_closed_loop(FakeEngine(), Spy(period=0.02, d=1), _suite(0.02), 0.04,
                        placement=None, command_delay_periods=1)
    res = run_closed_loop(FakeEngine(), Spy(period=0.02, d=1), _suite(0.02), 0.04,
                          placement=None)
    assert res.meta["controller_output_delay_periods"] == 1


def test_command_offset_shifts_the_applied_command() -> None:
    def run(offset):
        eng = FakeEngine(dt=1e-3)
        speeds = []
        run_closed_loop(eng, Spy(period=0.02), _suite(0.02), 0.1, placement=None,
                        command_offset_s=offset,
                        step_hook=lambda e: speeds.append((e.t, float(e.u[0]))))
        return np.array(speeds)

    base, late = run(0.0), run(0.005)
    # FakeEngine: the hook sees u of the step just taken; the command issued at 0.02 s acts
    # from the step ending at 0.021 s (offset 0) or 0.026 s (offset 5 ms)
    first = lambda a: a[np.flatnonzero(a[:, 1] > 0)[0], 0]  # noqa: E731
    assert first(base) == pytest.approx(0.021)
    assert first(late) == pytest.approx(0.026)
    with pytest.raises(ValueError):
        run_closed_loop(FakeEngine(), Spy(period=0.02), _suite(0.02), 0.04, placement=None,
                        command_offset_s=0.02)
