"""Unit tests for the control-period average of the IMU truth (user decision 2026-10-20 (1))."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.sensors.averaging import ControlPeriodAverager

PERIOD_S = 0.02
STEP_S = 1e-4
STEPS_PER_PERIOD = 200


def _feed(averager: ControlPeriodAverager, times, force_of_t, rate_of_t):
    averages = []
    for t_s in times:
        average = averager.add(t_s, force_of_t(t_s), rate_of_t(t_s))
        if average is not None:
            averages.append(average)
    return averages


def test_constant_input_gives_one_average_per_period_from_accumulated_time() -> None:
    averager = ControlPeriodAverager()
    t_s, times = 0.0, []
    for _ in range(3 * STEPS_PER_PERIOD):
        t_s += STEP_S  # repeated additions, as an engine clock does
        times.append(t_s)
    averages = _feed(averager, times, lambda t: (0.1, -0.2, 9.8), lambda t: (0.0, 0.01, 0.0))
    assert [a.sample_count for a in averages] == [STEPS_PER_PERIOD] * 3
    assert [a.t_s for a in averages] == pytest.approx([0.02, 0.04, 0.06])
    for average in averages:
        np.testing.assert_allclose(average.specific_force_m_s2, [0.1, -0.2, 9.8], rtol=1e-12)
        np.testing.assert_allclose(average.angular_rate_rad_s, [0.0, 0.01, 0.0], atol=1e-15)
        assert not average.specific_force_m_s2.flags.writeable


def test_average_of_a_ramp_is_its_end_point_rule_mean() -> None:
    averager = ControlPeriodAverager()
    times = [STEP_S * k for k in range(1, STEPS_PER_PERIOD + 1)]
    (average,) = _feed(averager, times, lambda t: (t, 0.0, 0.0), lambda t: (0.0, 0.0, 0.0))
    # mean of the step-end values: (T + dt) / 2
    assert average.specific_force_m_s2[0] == pytest.approx((PERIOD_S + STEP_S) / 2)


def test_period_average_gain_at_rocking_is_the_sinc() -> None:
    frequency_hz = 1.784  # 1st rocking mode, top level
    averager = ControlPeriodAverager()
    times = [STEP_S * k for k in range(1, 50 * STEPS_PER_PERIOD + 1)]
    averages = _feed(
        averager,
        times,
        lambda t: (math.sin(2 * math.pi * frequency_hz * t), 0.0, 9.8),
        lambda t: (0.0, 0.0, 0.0),
    )
    peak = max(abs(a.specific_force_m_s2[0]) for a in averages)
    expected_gain = abs(
        math.sin(math.pi * frequency_hz * PERIOD_S) / (math.pi * frequency_hz * PERIOD_S)
    )
    # A 20 ms average barely attenuates 1.8 Hz rocking (gain 0.99); the low-pass does that.
    assert peak == pytest.approx(expected_gain, abs=0.01)


def test_mixed_step_sizes_are_time_weighted() -> None:
    averager = ControlPeriodAverager()
    # first half of the period at dt 1e-4 with value 1, second half at dt 1e-5 with value 3
    coarse = [STEP_S * k for k in range(1, 101)]
    fine = [0.01 + 1e-5 * k for k in range(1, 1001)]
    averages = _feed(
        averager,
        coarse + fine,
        lambda t: (1.0 if t <= 0.01 + 1e-12 else 3.0, 0.0, 0.0),
        lambda t: (0.0, 0.0, 0.0),
    )
    (average,) = averages
    assert average.sample_count == 1100
    assert average.specific_force_m_s2[0] == pytest.approx(2.0, rel=1e-9)


def test_reset_starts_a_new_period_at_the_given_time() -> None:
    averager = ControlPeriodAverager(start_t_s=10.0)
    assert averager.period_end_s == pytest.approx(10.02)
    assert averager.add(10.01, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0)) is None
    averager.reset(20.0)
    average = averager.add(20.02, (5.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert average is not None and average.sample_count == 1
    assert average.specific_force_m_s2[0] == 5.0


def test_bad_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="period_s"):
        ControlPeriodAverager(period_s=0.0)
    averager = ControlPeriodAverager()
    with pytest.raises(ValueError, match="not after"):
        averager.add(0.0, (0.0, 0.0, 9.8), (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="specific_force_m_s2"):
        averager.add(1e-4, (0.0, 9.8), (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="angular_rate_rad_s"):
        averager.add(1e-4, (0.0, 0.0, 9.8), (0.0, 0.0, math.nan))
