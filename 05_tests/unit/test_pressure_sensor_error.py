"""WIKA A-10 pressure sensor error model (E-1, E-2; control spec 71, 76.1, U70 / U72)."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.sensors.hydraulic import (
    LegSensorConfig,
    LegSensorModel,
    pressure_spec_leg_sensor_config,
    reduced_model_leg_sensor_config,
    wika_a10_leg_sensor_config,
)
from outrigger_sim.sensors.pressure_error import (
    BAR_PA,
    CHAIN_RESOLUTION_PA,
    PressureErrorGrade,
    current_to_pressure_Pa,
    draw_unit_terms,
    error_terms_from_unit,
    pressure_to_current_mA,
    wika_noise_std_Pa,
)

HEAD_AREA = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
ANNULUS = np.array([3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3])
HEAD = np.array([90e5, 91e5, 76e5, 77e5])
ROD = np.full(4, 2e5)
STROKES = np.array([0.10, 0.10, 0.12, 0.12])
DRAWS = 200_000

SPEC_71_P95_KN = {
    # (grade, head bar, front/rear): uncalibrated p95 of |dF| from the spec 71 table
    ("normal", 89.6, 0): 2.26,
    ("normal", 76.4, 1): 1.66,
    ("normal", 11.4, 0): 3.26,
    ("normal", 15.8, 1): 2.29,
    ("conservative", 89.6, 0): 6.19,
    ("old_worst", 89.6, 0): 14.2,
}


def _readings(config: LegSensorConfig, seed: int = 5, samples: int = 20):
    model = LegSensorModel(config, seed)
    return [model.measure(HEAD, STROKES, STROKES, ROD, t_s=0.02 * k) for k in range(samples)]


@pytest.mark.parametrize(
    "config",
    [LegSensorConfig(), reduced_model_leg_sensor_config(HEAD_AREA),
     pressure_spec_leg_sensor_config()],
)
def test_legacy_configs_carry_no_static_error(config) -> None:
    """E-1: the existing configurations are the ``legacy`` grade with the R6-P meta keys."""
    assert config.pressure_error_grade is PressureErrorGrade.LEGACY
    assert not config.has_static_error
    assert "pressure_error_grade" not in config.to_meta()
    assert LegSensorModel(config, 1).error_meta() is None


def test_static_terms_leave_the_noise_streams_unchanged() -> None:
    """E-1: a normal-grade sensor differs from the legacy one by a per-sensor constant at a
    constant pressure, so the noise samples (head, rod and stroke) are the same draws."""
    noise = wika_noise_std_Pa("normal")
    legacy = LegSensorConfig(pressure_noise_std_Pa=noise, rod_pressure_noise_std_Pa=noise,
                             stroke_noise_std_m=1e-4)
    graded = LegSensorConfig(pressure_noise_std_Pa=noise, rod_pressure_noise_std_Pa=noise,
                             stroke_noise_std_m=1e-4, pressure_error_grade="normal")
    head_shifts, rod_shifts = [], []
    for plain, with_error in zip(_readings(legacy), _readings(graded), strict=True):
        np.testing.assert_array_equal(plain.stroke_m, with_error.stroke_m)
        head_shifts.append(with_error.head_pressure_Pa - plain.head_pressure_Pa)
        rod_shifts.append(with_error.rod_pressure_Pa - plain.rod_pressure_Pa)
    for shifts in (head_shifts, rod_shifts):
        np.testing.assert_allclose(shifts, np.broadcast_to(shifts[0], np.shape(shifts)), atol=1e-6)
        assert np.all(shifts[0] != 0.0)
        assert np.all(np.abs(shifts[0]) <= 4.0 * BAR_PA + 1e-6)  # normal-grade clip


def test_same_seed_reproduces_the_eight_sensor_terms() -> None:
    config = wika_a10_leg_sensor_config("normal")
    first, again = LegSensorModel(config, 42), LegSensorModel(config, 42)
    other = LegSensorModel(config, 43)
    assert first.error_meta() == again.error_meta()
    assert first.error_meta() != other.error_meta()
    assert len(first.error_meta()) == 8
    first.reset()
    assert first.error_meta() == again.error_meta()  # reset restarts the noise only


@pytest.mark.parametrize(("case", "expected_kN"), SPEC_71_P95_KN.items())
def test_monte_carlo_p95_matches_spec_71(case, expected_kN) -> None:
    """E-1 test: 200,000 draws, |dF| = |dp_h A_p - dp_r A_ann| (rod side locked at 2 bar),
    one noise sample per sensor; p95 within 5 % of the spec 71 table."""
    grade, head_bar, side = case
    leg = 0 if side == 0 else 2
    rng = np.random.default_rng(20261022)
    terms = error_terms_from_unit(draw_unit_terms(rng, (DRAWS, 2)), grade)
    noise = rng.normal(0.0, wika_noise_std_Pa(grade), (DRAWS, 2))
    pressures = np.broadcast_to(np.array([head_bar, 2.0]) * BAR_PA, (DRAWS, 2))
    error = terms.error_Pa(pressures) + noise
    force_error = error[:, 0] * HEAD_AREA[leg] - error[:, 1] * ANNULUS[leg]
    p95_kN = np.percentile(np.abs(force_error), 95) / 1e3
    assert p95_kN == pytest.approx(expected_kN, rel=0.05)


def test_current_chain_saturates_and_quantises() -> None:
    """E-2: 4-20 mA over 0-400 bar, NAMUR 3.8 / 20.5 mA saturation, 0.025 bar resolution."""
    assert pressure_to_current_mA([0.0, 400 * BAR_PA]) == pytest.approx([4.0, 20.0])
    assert current_to_pressure_Pa([3.8, 20.5]) == pytest.approx([-5 * BAR_PA, 412.5 * BAR_PA])
    config = wika_a10_leg_sensor_config("normal", stroke_noise_std_m=0.0,
                                        pressure_noise_std_Pa=0.0, rod_pressure_noise_std_Pa=0.0)
    model = LegSensorModel(config, 3)
    reading = model.measure([-50e5, 0.0, 300e5, 500e5], STROKES, rod_pressure_Pa=ROD)
    head = reading.head_pressure_Pa
    assert head[0] == pytest.approx(-5 * BAR_PA) and head[3] == pytest.approx(412.5 * BAR_PA)
    counts = head / CHAIN_RESOLUTION_PA
    np.testing.assert_allclose(counts, np.round(counts), atol=1e-9)


def test_offsets_and_drift() -> None:
    """PS-4 / PS-5 settings: a fixed head offset, and a linear drift from its start time."""
    config = LegSensorConfig(head_offset_Pa=(4e5, 0.0, 0.0, -4e5),
                             head_zero_drift_Pa_per_s=(2e5 / 600.0, 0.0, 0.0, 0.0),
                             zero_drift_start_s=100.0)
    model = LegSensorModel(config, 1)
    before = model.measure(HEAD, STROKES, t_s=50.0).head_pressure_Pa
    later = model.measure(HEAD, STROKES, t_s=700.0).head_pressure_Pa
    np.testing.assert_allclose(before - HEAD, [4e5, 0.0, 0.0, -4e5], atol=1e-6)
    np.testing.assert_allclose(later - HEAD, [6e5, 0.0, 0.0, -4e5], atol=1e-6)
    assert config.to_meta()["head_offset_Pa"] == [4e5, 0.0, 0.0, -4e5]


def test_wika_config_meta_and_legacy_grade() -> None:
    config = wika_a10_leg_sensor_config()
    assert config.pressure_error_grade is PressureErrorGrade.NORMAL
    assert config.pressure_noise_std_Pa == pytest.approx(0.2e5)
    meta = config.to_meta()
    assert meta["nonlinearity_shape"] == "bfsl_parabola"
    assert meta["current_range_mA"] == [3.8, 20.5]
    assert wika_a10_leg_sensor_config("old_worst").pressure_noise_std_Pa == pytest.approx(0.27e5)
    assert wika_a10_leg_sensor_config("legacy") == pressure_spec_leg_sensor_config()
