"""Unit tests for the sensor suite and the controller boundary (plan S6, 3.3; py)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from outrigger_sim.control.hold import HoldController
from outrigger_sim.control.protocol import Controller
from outrigger_sim.sensors.hydraulic import LegSensorConfig
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M, ImuErrorConfig, imu_config_for_grade
from outrigger_sim.sensors.suite import SensorSuite
from outrigger_sim.signals import Command, Measurements

NOISY_LEGS = LegSensorConfig(pressure_noise_std_Pa=3.0e4, stroke_noise_std_m=1e-4)


def _ideal(t_s: float, *, with_corrected_stroke: bool = True) -> Measurements:
    return Measurements(
        t_s=t_s,
        specific_force_m_s2=[0.0, 0.0, 9.80665],
        angular_rate_rad_s=[0.0, 0.0, 0.0],
        head_pressure_Pa=[9.0e6, 9.1e6, 8.0e6, 8.1e6],
        stroke_m=[0.10, 0.10, 0.12, 0.12],
        stroke_corrected_m=[0.095, 0.095, 0.115, 0.115] if with_corrected_stroke else None,
    )


def _apply_series(suite: SensorSuite, count: int) -> list[Measurements]:
    return [suite.apply(_ideal(0.02 * k)) for k in range(count)]


def _as_array(series: list[Measurements]) -> np.ndarray:
    return np.array(
        [np.concatenate([m.specific_force_m_s2, m.head_pressure_Pa, m.stroke_m]) for m in series]
    )


# --- sensor suite ------------------------------------------------------------------------


def test_ideal_suite_returns_the_ideal_values() -> None:
    suite = SensorSuite(ImuErrorConfig(), LegSensorConfig(), seed=0)
    ideal = _ideal(0.04)
    delivered = suite.apply(ideal)
    assert delivered.t_s == ideal.t_s
    for name in (
        "specific_force_m_s2",
        "angular_rate_rad_s",
        "head_pressure_Pa",
        "stroke_m",
        "stroke_corrected_m",
    ):
        np.testing.assert_array_equal(getattr(delivered, name), getattr(ideal, name))
    assert suite.apply(_ideal(0.06, with_corrected_stroke=False)).stroke_corrected_m is None


def test_grade_bias_reaches_the_controller_side() -> None:
    config = imu_config_for_grade("normal_as_shipped")
    suite = SensorSuite(
        ImuErrorConfig(accel_bias_m_s2=config.accel_bias_m_s2), LegSensorConfig(), seed=0
    )
    delivered = suite.apply(_ideal(0.0))
    np.testing.assert_allclose(
        delivered.specific_force_m_s2 - _ideal(0.0).specific_force_m_s2, config.accel_bias_m_s2
    )


def test_one_seed_reproduces_every_noise_stream() -> None:
    imu_config = imu_config_for_grade("normal_zeroed")
    first = _as_array(_apply_series(SensorSuite(imu_config, NOISY_LEGS, seed=42), 10))
    suite = SensorSuite(imu_config, NOISY_LEGS, seed=42)
    np.testing.assert_array_equal(_as_array(_apply_series(suite, 10)), first)
    suite.reset()
    np.testing.assert_array_equal(_as_array(_apply_series(suite, 10)), first)
    other = _as_array(_apply_series(SensorSuite(imu_config, NOISY_LEGS, seed=43), 10))
    assert not np.array_equal(other, first)


def test_leg_noise_does_not_depend_on_the_imu_settings() -> None:
    ideal_imu = SensorSuite(imu_config_for_grade("ideal"), NOISY_LEGS, seed=9)
    delayed_imu = SensorSuite(
        imu_config_for_grade("normal_zeroed", delay_samples=3), NOISY_LEGS, seed=9
    )
    for a, b in zip(_apply_series(ideal_imu, 5), _apply_series(delayed_imu, 5), strict=True):
        np.testing.assert_array_equal(a.head_pressure_Pa, b.head_pressure_Pa)


def test_unseeded_suite_records_a_seed_that_repeats_the_run() -> None:
    imu_config = imu_config_for_grade("good_zeroed")
    suite = SensorSuite(imu_config, NOISY_LEGS, seed=None)
    repeated = SensorSuite(imu_config, NOISY_LEGS, seed=suite.seed)
    np.testing.assert_array_equal(
        _as_array(_apply_series(suite, 5)), _as_array(_apply_series(repeated, 5))
    )


def test_setup_is_json_ready_with_mount_point_and_seed() -> None:
    suite = SensorSuite(imu_config_for_grade("ideal"), NOISY_LEGS, seed=7)
    setup = suite.setup()
    assert setup.noise_seed == 7
    assert json.loads(json.dumps(dict(setup.config))) == dict(setup.config)
    assert setup.config["imu_mount_point_body_m"] == list(IMU_MOUNT_C1_BODY_M)
    assert setup.config["imu"]["grade"] == "ideal"
    moved = SensorSuite(ImuErrorConfig(), LegSensorConfig(), 7, imu_mount_point_body_m=(1, 2, 3))
    assert moved.setup().config["imu_mount_point_body_m"] == [1.0, 2.0, 3.0]


# --- controller boundary -----------------------------------------------------------------


def test_hold_controller_satisfies_the_protocol_and_stops_every_leg() -> None:
    controller = HoldController()
    assert isinstance(controller, Controller)
    assert controller.period_s == 0.02
    controller.reset()
    command = controller.update(_ideal(1.24))
    assert isinstance(command, Command)
    assert command.t_s == 1.24
    assert command.leg_speed_m_s.tolist() == [0.0, 0.0, 0.0, 0.0]
    meta = controller.meta()
    assert json.loads(json.dumps(meta)) == meta == {"controller": "hold", "period_s": 0.02}


def test_hold_controller_rejects_a_bad_period() -> None:
    with pytest.raises(ValueError, match="period_s"):
        HoldController(period_s=0.0)


def test_hold_controller_closes_a_loop_with_the_sensor_suite() -> None:
    # 60 s of a closed loop at 20 ms without an engine: measurements -> controller -> command.
    suite = SensorSuite(imu_config_for_grade("normal_zeroed"), NOISY_LEGS, seed=1)
    controller = HoldController()
    for step in range(3000):
        command = controller.update(suite.apply(_ideal(step * controller.period_s)))
        assert not command.leg_speed_m_s.any()
