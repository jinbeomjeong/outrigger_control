"""Unit tests for the pressure / stroke sensors and the 350 bar indicator (plan S6, py)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.params import Params, load_params
from outrigger_sim.sensors.hydraulic import (
    LegSensorConfig,
    LegSensorModel,
    head_area_from_params,
    head_area_m2,
    locked_pressure_limit_from_params,
    locked_pressure_report,
    reduced_model_leg_sensor_config,
)

PRESSURES = [9.0e6, 9.1e6, 8.0e6, 8.1e6]
STROKES = [0.10, 0.10, 0.12, 0.12]


@pytest.fixture(scope="module")
def params(params_path: Path) -> Params:
    return load_params(params_path)


# --- areas and limits from the parameters ------------------------------------------------


def test_head_area_and_locked_limit_match_the_yaml(params: Params) -> None:
    area = head_area_from_params(params)
    assert area == pytest.approx(head_area_m2(0.115))
    assert area == pytest.approx(0.0103869, rel=1e-5)  # YAML annulus comment
    limit = locked_pressure_limit_from_params(params)
    assert limit == 35.0e6
    assert limit * area == pytest.approx(363541.0, abs=1.0)  # YAML: 350 bar x head area


def test_reduced_model_noise_levels() -> None:
    config = reduced_model_leg_sensor_config(head_area_m2(0.115))
    assert config.pressure_noise_std_Pa == pytest.approx(300.0 / head_area_m2(0.115))
    assert config.stroke_noise_std_m == 1e-4
    assert config.pressure_resolution_Pa == config.stroke_resolution_m == 0.0


# --- virtual sensors ---------------------------------------------------------------------


def test_ideal_sensors_pass_values_through() -> None:
    reading = LegSensorModel(LegSensorConfig()).measure(PRESSURES, STROKES)
    np.testing.assert_array_equal(reading.head_pressure_Pa, PRESSURES)
    np.testing.assert_array_equal(reading.stroke_m, STROKES)
    assert reading.stroke_corrected_m is None


def test_noise_statistics_and_one_noise_for_both_strokes() -> None:
    config = LegSensorConfig(pressure_noise_std_Pa=3.0e4, stroke_noise_std_m=1e-4)
    model = LegSensorModel(config, seed=11)
    corrected = np.array(STROKES) - 0.005
    pressure_errors, stroke_errors = [], []
    for _ in range(3000):
        reading = model.measure(PRESSURES, STROKES, corrected)
        pressure_errors.append(reading.head_pressure_Pa - PRESSURES)
        stroke_errors.append(reading.stroke_m - STROKES)
        assert reading.stroke_corrected_m is not None
        np.testing.assert_allclose(
            reading.stroke_corrected_m - corrected, stroke_errors[-1], atol=1e-15
        )
    np.testing.assert_allclose(np.std(pressure_errors, axis=0), 3.0e4, rtol=0.06)
    np.testing.assert_allclose(np.std(stroke_errors, axis=0), 1e-4, rtol=0.06)


def test_resolution_quantises_the_readings() -> None:
    config = LegSensorConfig(pressure_resolution_Pa=1.0e4, stroke_resolution_m=1e-3)
    reading = LegSensorModel(config).measure(
        [9.0049e6, 1.0, 2.0e4, 0.0], [0.1004, 0, 0, 0], [0.0996, 0, 0, 0]
    )
    np.testing.assert_allclose(reading.head_pressure_Pa, [9.0e6, 0.0, 2.0e4, 0.0])
    np.testing.assert_allclose(reading.stroke_m, [0.100, 0, 0, 0], atol=1e-15)
    assert reading.stroke_corrected_m is not None
    np.testing.assert_allclose(reading.stroke_corrected_m, [0.100, 0, 0, 0], atol=1e-15)


def test_seed_repeats_and_reset_restarts() -> None:
    config = LegSensorConfig(pressure_noise_std_Pa=1.0e4, stroke_noise_std_m=1e-4)
    first = LegSensorModel(config, seed=5).measure(PRESSURES, STROKES).head_pressure_Pa
    model = LegSensorModel(config, seed=5)
    np.testing.assert_array_equal(model.measure(PRESSURES, STROKES).head_pressure_Pa, first)
    model.reset()
    np.testing.assert_array_equal(model.measure(PRESSURES, STROKES).head_pressure_Pa, first)


@pytest.mark.parametrize("field_name", ["pressure_noise_std_Pa", "stroke_resolution_m"])
def test_config_rejects_negative_values(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        LegSensorConfig(**{field_name: -1.0})


def test_inputs_need_four_finite_values() -> None:
    model = LegSensorModel(LegSensorConfig())
    with pytest.raises(ValueError, match="head_pressure_Pa"):
        model.measure(PRESSURES[:3], STROKES)
    with pytest.raises(ValueError, match="stroke_m"):
        model.measure(PRESSURES, [0.1, 0.1, 0.1, math.nan])


# --- 350 bar indicator -------------------------------------------------------------------

LIMIT_PA = 35.0e6


def _run_pressures() -> tuple[np.ndarray, np.ndarray]:
    t_s = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    pressures = np.full((5, 4), 10.0e6)
    pressures[2, 3] = 36.0e6  # RR above the limit first at 0.2 s
    pressures[3, 1] = 37.0e6  # FR maximum at 0.3 s
    pressures[3, 3] = 35.5e6
    return t_s, pressures


def test_report_finds_maximum_and_first_exceedance() -> None:
    t_s, pressures = _run_pressures()
    report = locked_pressure_report(t_s, pressures, LIMIT_PA)
    assert report.is_exceeded
    assert (report.max_pressure_Pa, report.max_leg, report.max_t_s) == (37.0e6, 1, 0.3)
    assert (report.first_exceed_t_s, report.first_exceed_leg) == (0.2, 3)
    assert report.exceed_sample_count_per_leg == (0, 1, 0, 2)
    assert report.max_per_leg_Pa == (10.0e6, 37.0e6, 10.0e6, 36.0e6)
    summary = report.to_dict()
    assert json.loads(json.dumps(summary)) == summary
    assert (summary["max_leg"], summary["first_exceed_leg"]) == ("FR", "RR")


def test_report_ignores_samples_that_are_not_locked() -> None:
    t_s, pressures = _run_pressures()
    is_locked = np.ones(pressures.shape, dtype=bool)
    is_locked[2:4, :] = False  # legs moving during 0.2-0.3 s
    report = locked_pressure_report(t_s, pressures, LIMIT_PA, is_locked=is_locked)
    assert not report.is_exceeded
    assert report.first_exceed_t_s is None and report.first_exceed_leg is None
    assert report.max_pressure_Pa == 10.0e6


def test_report_marks_legs_without_considered_samples() -> None:
    t_s, pressures = _run_pressures()
    is_locked = np.ones(pressures.shape, dtype=bool)
    is_locked[:, 0] = False
    report = locked_pressure_report(t_s, pressures, LIMIT_PA, is_locked=is_locked)
    assert math.isnan(report.max_per_leg_Pa[0])
    assert report.to_dict()["max_per_leg_Pa"]["FL"] is None


def test_pressure_exactly_at_the_limit_is_not_an_exceedance() -> None:
    report = locked_pressure_report([0.0], [[LIMIT_PA, 0.0, 0.0, 0.0]], LIMIT_PA)
    assert not report.is_exceeded


@pytest.mark.parametrize(
    ("t_s", "pressures", "is_locked", "message"),
    [
        ([0.0, 0.1], np.zeros((3, 4)), None, "expected"),
        ([0.0], [[0.0, 0.0, math.nan, 0.0]], None, "NaN"),
        ([0.0], np.zeros((1, 4)), np.zeros((1, 3), dtype=bool), "is_locked"),
        ([0.0], np.zeros((1, 4)), np.zeros((1, 4), dtype=bool), "no sample"),
        ([], np.zeros((0, 4)), None, "no sample"),
    ],
)
def test_report_rejects_bad_input(t_s, pressures, is_locked, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        locked_pressure_report(t_s, pressures, LIMIT_PA, is_locked=is_locked)
