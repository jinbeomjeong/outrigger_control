"""Unit tests for the attitude low-pass and the tilt estimate (plan S6, py)."""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

from outrigger_sim.frames import quat_from_euler_zyx
from outrigger_sim.sensors.attitude import AttitudeEstimator, CascadedLowPass
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2, specific_force_at_point

ZERO = (0.0, 0.0, 0.0)


def test_defaults_are_the_decided_filter() -> None:
    low_pass = CascadedLowPass()
    assert low_pass.time_constant_s == 0.5
    assert low_pass.stage_count == 2
    assert low_pass.sample_period_s == 0.02
    assert low_pass.pole == pytest.approx(0.96)


def test_two_stage_step_response_matches_the_closed_form() -> None:
    low_pass = CascadedLowPass()
    gain, pole = low_pass.gain, low_pass.pole
    assert low_pass.update(0.0) == 0.0  # the first sample initialises every stage
    for k in range(1, 200):
        output = float(low_pass.update(1.0))
        # stage 1: 1 - p^k, stage 2: 1 - p^k - k a p^k
        assert output == pytest.approx(1.0 - pole**k - k * gain * pole**k, abs=1e-12)


def test_first_sample_starts_without_transient_and_reset_forgets() -> None:
    low_pass = CascadedLowPass()
    assert low_pass.update(0.3) == pytest.approx(0.3)
    assert low_pass.update(0.3) == pytest.approx(0.3)
    low_pass.update(5.0)
    low_pass.reset()
    assert low_pass.update(-1.0) == pytest.approx(-1.0)


def test_channels_are_filtered_independently() -> None:
    low_pass = CascadedLowPass()
    low_pass.update([0.0, 1.0])
    output = low_pass.update([1.0, 1.0])
    assert output[0] == pytest.approx(low_pass.gain**2)
    assert output[1] == pytest.approx(1.0)


def test_half_power_near_the_continuous_corner() -> None:
    # 2 x first order: |H| = 1 / (1 + (w tau)^2) -> 0.5 at f = 1 / (2 pi tau) = 0.318 Hz.
    low_pass = CascadedLowPass()
    corner_hz = 1.0 / (2.0 * math.pi * low_pass.time_constant_s)
    z = cmath.exp(1j * 2.0 * math.pi * corner_hz * low_pass.sample_period_s)
    stage = low_pass.gain / (1.0 - low_pass.pole / z)
    # The Euler pole (0.96 vs exp(-T/tau) 0.9608) moves the value by about 2 %.
    assert abs(stage) ** 2 == pytest.approx(0.5, rel=0.03)


@pytest.mark.parametrize(
    ("period_s", "tau_s", "stages"), [(0.02, 0.01, 2), (0.0, 0.5, 2), (0.02, 0.5, 0)]
)
def test_invalid_filter_settings_are_rejected(period_s: float, tau_s: float, stages: int) -> None:
    with pytest.raises(ValueError):
        CascadedLowPass(tau_s, stages, period_s)


def test_estimator_recovers_a_static_tilt_and_filters_a_step() -> None:
    roll, pitch = math.radians(2.0), math.radians(-1.0)
    tilted = specific_force_at_point(quat_from_euler_zyx(0.0, pitch, roll), ZERO, ZERO, ZERO)
    estimator = AttitudeEstimator()
    level = estimator.update(0.0, (0.0, 0.0, STANDARD_GRAVITY_M_S2))
    assert (level.roll_rad, level.pitch_rad) == (0.0, 0.0)
    first = estimator.update(0.02, tilted)
    assert first.roll_raw_rad == pytest.approx(roll, abs=1e-12)
    assert first.pitch_raw_rad == pytest.approx(pitch, abs=1e-12)
    assert first.roll_rad == pytest.approx(roll * estimator.low_pass.gain**2)
    for k in range(2, 1000):
        estimate = estimator.update(0.02 * k, tilted)
    assert estimate.roll_rad == pytest.approx(roll, abs=1e-12)
    assert estimate.pitch_rad == pytest.approx(pitch, abs=1e-12)
    estimator.reset()
    restarted = estimator.update(0.0, tilted)
    assert np.isclose(restarted.roll_rad, roll)
