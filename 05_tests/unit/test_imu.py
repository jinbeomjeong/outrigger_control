"""Unit tests for the IMU truth kinematics and the IMU error model (plan S6, py)."""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.frames import quat_from_euler_zyx, roll_pitch_from_specific_force
from outrigger_sim.sensors import imu as imu_module
from outrigger_sim.sensors.hydraulic import LegSensorConfig
from outrigger_sim.sensors.imu import (
    IMU_GRADES,
    IMU_MOUNT_C1_BODY_M,
    STANDARD_GRAVITY_M_S2,
    ImuErrorConfig,
    ImuGradeName,
    ImuModel,
    angular_rate_in_body,
    field_zero_offset,
    imu_config_for_grade,
    specific_force_at_point,
)
from outrigger_sim.sensors.suite import SensorSuite
from outrigger_sim.signals import Measurements

G = STANDARD_GRAVITY_M_S2
LEVEL = (1.0, 0.0, 0.0, 0.0)
ZERO = (0.0, 0.0, 0.0)
LEVEL_FORCE = (0.0, 0.0, G)


# --- truth at the mounting point ---------------------------------------------------------


def test_default_mount_point_is_c1() -> None:
    assert IMU_MOUNT_C1_BODY_M == (0.31, 0.88, 0.040)


def test_level_body_at_rest_reads_plus_g_at_any_point() -> None:
    for point in (IMU_MOUNT_C1_BODY_M, (5.0, -3.0, 2.0)):
        force = specific_force_at_point(LEVEL, ZERO, ZERO, ZERO, point)
        np.testing.assert_allclose(force, LEVEL_FORCE, atol=1e-12)


def test_static_tilt_is_recovered_from_the_specific_force() -> None:
    roll, pitch = math.radians(1.5), math.radians(-0.7)
    quat = quat_from_euler_zyx(0.3, pitch, roll)
    force = specific_force_at_point(quat, ZERO, ZERO, ZERO)
    measured_roll, measured_pitch = roll_pitch_from_specific_force(force)
    assert measured_roll == pytest.approx(roll, abs=1e-12)
    assert measured_pitch == pytest.approx(pitch, abs=1e-12)


def test_centripetal_term_depends_on_the_mount_point() -> None:
    yaw_rate = 0.5
    omega = (0.0, 0.0, yaw_rate)
    at_c1 = specific_force_at_point(LEVEL, ZERO, omega, ZERO)
    x, y, _ = IMU_MOUNT_C1_BODY_M
    np.testing.assert_allclose(at_c1, [-(yaw_rate**2) * x, -(yaw_rate**2) * y, G], atol=1e-12)
    moved = specific_force_at_point(LEVEL, ZERO, omega, ZERO, point_body_m=(1.0, 0.0, 0.0))
    np.testing.assert_allclose(moved, [-(yaw_rate**2), 0.0, G], atol=1e-12)


def test_angular_acceleration_term_uses_the_lever_arm() -> None:
    alpha = (2.0, 0.0, 0.0)  # roll acceleration
    force = specific_force_at_point(LEVEL, ZERO, ZERO, alpha, point_body_m=(0.0, 0.0, 1.0))
    # alpha x r = (2, 0, 0) x (0, 0, 1) = (0, -2, 0)
    np.testing.assert_allclose(force, [0.0, -2.0, G], atol=1e-12)


def test_gyro_truth_is_the_world_rate_in_body_axes() -> None:
    quarter_turn_yaw = quat_from_euler_zyx(math.pi / 2, 0.0, 0.0)
    rate = angular_rate_in_body(quarter_turn_yaw, (1.0, 0.0, 0.0))
    np.testing.assert_allclose(rate, [0.0, -1.0, 0.0], atol=1e-12)


# --- grades ------------------------------------------------------------------------------


def test_five_grades_with_the_documented_values() -> None:
    # 00_docs/05_sensors/imu_cabin_and_accuracy_review.md 4.1: degrees, mg and ug/rtHz
    expected = {
        ImuGradeName.IDEAL: (0.0, 0.0, 15.0),
        ImuGradeName.GOOD_ZEROED: (0.046, 0.80, 15.0),
        ImuGradeName.NORMAL_ZEROED: (0.072, 1.26, 82.0),
        ImuGradeName.NORMAL_ZEROED_REPEATABILITY: (0.122, 2.13, 82.0),
        ImuGradeName.NORMAL_AS_SHIPPED: (0.17, 2.97, 82.0),
    }
    assert set(IMU_GRADES) == set(expected)
    for name, (degrees, milli_g, density) in expected.items():
        grade = IMU_GRADES[name]
        assert grade.zero_error_deg == degrees
        assert grade.zero_error_mg == pytest.approx(milli_g, abs=0.005)
        assert grade.noise_density_ug_rtHz == density


def test_grade_bias_has_the_same_sign_on_x_and_y_and_none_on_z() -> None:
    config = imu_config_for_grade("normal_zeroed")
    bias_x, bias_y, bias_z = config.accel_bias_m_s2
    assert bias_x == bias_y == pytest.approx(math.sin(math.radians(0.072)) * G)
    assert bias_z == 0.0
    assert config.grade == "normal_zeroed"


# s6_control_spec.md 10.3 (ASSUMPTION, user decision U9): ARW deg/sqrt(h), bias deg/h.
GYRO_GRADES = {
    ImuGradeName.IDEAL: (0.0, 0.0),
    ImuGradeName.GOOD_ZEROED: (0.15, 5.0),
    ImuGradeName.NORMAL_ZEROED: (0.30, 20.0),
    ImuGradeName.NORMAL_ZEROED_REPEATABILITY: (0.30, 20.0),
    ImuGradeName.NORMAL_AS_SHIPPED: (0.30, 20.0),
}


def test_grade_gyro_errors_and_their_si_values() -> None:
    for name, (arw_deg_rt_h, bias_deg_h) in GYRO_GRADES.items():
        config = imu_config_for_grade(name)
        bias_rad_s = math.radians(bias_deg_h) / 3600.0
        assert config.gyro_bias_rad_s == pytest.approx((bias_rad_s,) * 3, abs=0.0)
        density = math.radians(arw_deg_rt_h) / 60.0
        assert config.gyro_noise_density_rad_s_rtHz == pytest.approx(density, rel=1e-12)
    # spec table: 0.15 deg/sqrt(h) = 4.36e-5 rad/s/sqrt(Hz)
    good = imu_config_for_grade("good_zeroed")
    assert good.gyro_noise_density_rad_s_rtHz == pytest.approx(4.36e-5, rel=1e-3)


def test_grade_gyro_errors_reach_the_delivered_rate() -> None:
    """The error model applies the grade's gyro bias and ARW to the delivered angular rate."""
    config = dataclasses.replace(imu_config_for_grade("normal_zeroed"))
    model = ImuModel(config, seed=3)
    sample_count = 20_000
    rates = np.array(
        [model.measure(0.02 * k, LEVEL_FORCE, ZERO).angular_rate_rad_s for k in range(sample_count)]
    )
    expected_std = config.gyro_noise_density_rad_s_rtHz * math.sqrt(1.0 / (2.0 * 0.02))
    standard_error = expected_std / math.sqrt(sample_count)
    np.testing.assert_allclose(rates.mean(axis=0), config.gyro_bias_rad_s, atol=5 * standard_error)
    np.testing.assert_allclose(rates.std(axis=0), expected_std, rtol=0.03)


def test_sensor_suite_delivers_the_grade_gyro_bias() -> None:
    """The runner path (SensorSuite.apply) carries the gyro errors into Measurements."""
    config = dataclasses.replace(
        imu_config_for_grade("good_zeroed"), gyro_noise_density_rad_s_rtHz=0.0
    )
    suite = SensorSuite(config, LegSensorConfig(), seed=0)
    ideal = Measurements(
        t_s=0.02,
        specific_force_m_s2=LEVEL_FORCE,
        angular_rate_rad_s=ZERO,
        head_pressure_Pa=np.zeros(4),
        stroke_m=np.zeros(4),
    )
    delivered = suite.apply(ideal)
    np.testing.assert_allclose(delivered.angular_rate_rad_s, config.gyro_bias_rad_s, rtol=1e-12)


def test_grade_zero_error_reads_as_tilt_of_that_size() -> None:
    angle_rad = math.radians(IMU_GRADES[ImuGradeName.GOOD_ZEROED].zero_error_deg)
    model = ImuModel(
        dataclasses.replace(imu_config_for_grade("good_zeroed"), accel_noise_density_m_s2_rtHz=0.0)
    )
    reading = model.measure(0.0, LEVEL_FORCE, ZERO)
    roll, pitch = roll_pitch_from_specific_force(reading.specific_force_m_s2)
    # +y bias -> positive roll, +x bias -> negative pitch
    assert roll == pytest.approx(angle_rad, abs=1e-8)
    assert pitch == pytest.approx(-angle_rad, abs=1e-8)


# --- configuration -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("accel_bias_m_s2", (0.0, 0.0)),
        ("gyro_bias_rad_s", (0.0, np.nan, 0.0)),
        ("accel_noise_density_m_s2_rtHz", -1.0),
        ("gyro_resolution_rad_s", math.inf),
        ("delay_samples", -1),
        ("delay_samples", 1.5),
        ("delay_samples", True),
        ("sample_period_s", 0.0),
    ],
)
def test_config_rejects_bad_values(field_name: str, bad_value: object) -> None:
    with pytest.raises(ValueError, match=field_name):
        ImuErrorConfig(**{field_name: bad_value})


def test_config_meta_is_json_ready() -> None:
    meta = imu_config_for_grade("normal_as_shipped", delay_samples=2).to_meta()
    assert json.loads(json.dumps(meta)) == meta
    assert meta["grade"] == "normal_as_shipped"
    assert meta["delay_samples"] == 2


def test_unknown_grade_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="excellent"):
        imu_config_for_grade("excellent")


# --- noise, seed, delay, quantisation, zero offset ---------------------------------------


def _accel_series(model: ImuModel, count: int) -> np.ndarray:
    return np.array(
        [model.measure(0.02 * k, LEVEL_FORCE, ZERO).specific_force_m_s2 for k in range(count)]
    )


def test_noise_std_is_density_times_root_half_sample_rate() -> None:
    config = imu_config_for_grade("normal_zeroed")
    expected_std = 82e-6 * G * math.sqrt(1.0 / (2.0 * 0.02))
    assert config.accel_noise_std_m_s2 == pytest.approx(expected_std)
    samples = _accel_series(ImuModel(config, seed=7), 4000)
    noise = samples - (np.array(LEVEL_FORCE) + config.accel_bias_m_s2)
    np.testing.assert_allclose(noise.std(axis=0), expected_std, rtol=0.05)
    np.testing.assert_allclose(noise.mean(axis=0), 0.0, atol=4 * expected_std / math.sqrt(4000))


def test_same_seed_repeats_and_reset_restarts_the_sequence() -> None:
    config = imu_config_for_grade("good_zeroed")
    first = _accel_series(ImuModel(config, seed=12345), 20)
    model = ImuModel(config, seed=12345)
    np.testing.assert_array_equal(_accel_series(model, 20), first)
    model.reset()
    np.testing.assert_array_equal(_accel_series(model, 20), first)
    assert not np.array_equal(_accel_series(ImuModel(config, seed=1), 20), first)


def test_unseeded_model_can_be_repeated_from_its_entropy() -> None:
    config = imu_config_for_grade("ideal")
    model = ImuModel(config)
    repeated = ImuModel(config, seed=model.seed_entropy)  # type: ignore[arg-type]
    np.testing.assert_array_equal(_accel_series(model, 5), _accel_series(repeated, 5))


def test_grades_share_the_noise_sequence_for_the_same_seed() -> None:
    ideal = imu_config_for_grade("ideal")
    normal = imu_config_for_grade("normal_zeroed")
    ideal_noise = _accel_series(ImuModel(ideal, seed=3), 10) - LEVEL_FORCE
    normal_noise = _accel_series(ImuModel(normal, seed=3), 10) - LEVEL_FORCE
    normal_noise -= normal.accel_bias_m_s2
    np.testing.assert_allclose(normal_noise, ideal_noise * 82.0 / 15.0, atol=1e-12)


def test_delay_shifts_by_whole_samples_and_starts_with_the_first_value() -> None:
    model = ImuModel(ImuErrorConfig(delay_samples=2))
    outputs = []
    for k in range(5):
        reading = model.measure(0.02 * k, (float(k), 0.0, G), (0.0, 0.0, float(k)))
        assert reading.t_s == pytest.approx(0.02 * k)
        outputs.append((reading.specific_force_m_s2[0], reading.angular_rate_rad_s[2]))
    assert outputs == [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    model.reset()
    assert model.measure(0.0, (9.0, 0.0, G), ZERO).specific_force_m_s2[0] == 9.0


def test_quantisation_rounds_to_the_resolution() -> None:
    model = ImuModel(ImuErrorConfig(accel_resolution_m_s2=0.01, gyro_resolution_rad_s=0.001))
    reading = model.measure(0.0, (0.0123, -0.0177, 9.80665), (0.00049, 0.0021, 0.0))
    np.testing.assert_allclose(reading.specific_force_m_s2, [0.01, -0.02, 9.81], atol=1e-12)
    np.testing.assert_allclose(reading.angular_rate_rad_s, [0.0, 0.002, 0.0], atol=1e-12)


def test_readings_are_read_only_copies() -> None:
    reading = ImuModel(ImuErrorConfig()).measure(0.0, LEVEL_FORCE, ZERO)
    with pytest.raises(ValueError, match="read-only"):
        reading.specific_force_m_s2[0] = 1.0


def test_input_shape_is_checked() -> None:
    with pytest.raises(ValueError, match="specific_force_m_s2"):
        ImuModel(ImuErrorConfig()).measure(0.0, (0.0, G), ZERO)


def test_field_zero_removes_a_raw_bias_at_the_reference_attitude() -> None:
    raw_bias = (0.02, -0.015, 0.03)
    roll, pitch = math.radians(0.4), math.radians(-0.25)
    true_force = G * np.array(
        [-math.sin(pitch), math.sin(roll) * math.cos(pitch), math.cos(roll) * math.cos(pitch)]
    )
    uncalibrated = ImuModel(ImuErrorConfig(accel_bias_m_s2=raw_bias))
    mean_reading = uncalibrated.measure(0.0, true_force, ZERO).specific_force_m_s2
    offset = field_zero_offset(mean_reading, reference_roll_rad=roll, reference_pitch_rad=pitch)
    np.testing.assert_allclose(offset, raw_bias, atol=1e-12)

    calibrated = ImuModel(ImuErrorConfig(accel_bias_m_s2=raw_bias, zero_offset_m_s2=offset))
    reading = calibrated.measure(0.0, true_force, ZERO).specific_force_m_s2
    np.testing.assert_allclose(reading, true_force, atol=1e-12)
    # A second calibration on corrected readings keeps the total offset.
    again = field_zero_offset(
        reading, reference_roll_rad=roll, reference_pitch_rad=pitch, current_offset_m_s2=offset
    )
    np.testing.assert_allclose(again, offset, atol=1e-12)


def test_module_has_no_engine_dependency() -> None:
    source = Path(imu_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("import pychrono", "from pychrono"):
        assert forbidden not in source
