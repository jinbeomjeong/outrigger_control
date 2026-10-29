"""CHECK zero calibration: the retract time-out tolerance (control spec 416.3, variant D,
user decision 2026-10-29).

Bench: four hanging legs at 10 Hz (the R8 period). The true strokes follow the commands and
stop at the full-retraction hard stop (``floor``) or at a jam (``ceiling``); the readings add
stroke noise. ``ZeroCalibration`` is driven directly, without the C2 controller.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config
from outrigger_sim.control.zero_calibration import (
    LegCalibrationStatus,
    SkipReason,
    ZeroCalibration,
    ZeroCalibrationSettings,
)
from outrigger_sim.params import LEG_ORDER

PERIOD_S = 0.1
MAX_SPEED_M_S = 20.924e-3
ROD_WEIGHT_N = np.array([1000.0, 1000.0, 717.5, 717.5])
STROKE_LIMIT_M = 0.6848
STROKE_NOISE_M = 0.1e-3
FORCE_NOISE_N = 100.0
RUN_LIMIT_S = 10.0
TOLERANCE_M = 0.5e-3
MONTE_CARLO_SEEDS = 1000
FR = LEG_ORDER.index("FR")

R8_SETTINGS = C2Config().with_10hz_d1().zero_calibration
OLD_SETTINGS = replace(R8_SETTINGS, return_timeout_tolerance_m=None)

NoiseSource = Callable[[], np.ndarray]


@dataclass
class _HangingLegs:
    """True strokes between ``floor_m`` and ``ceiling_m``, noisy stroke and force readings."""

    rng: np.random.Generator
    stroke_noise: NoiseSource | None = None
    true_stroke_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    floor_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    ceiling_m: np.ndarray = field(default_factory=lambda: np.full(4, STROKE_LIMIT_M))

    def read_strokes(self) -> np.ndarray:
        if self.stroke_noise is not None:
            return self.true_stroke_m + self.stroke_noise()
        return self.true_stroke_m + self.rng.normal(0.0, STROKE_NOISE_M, 4)

    def read_forces(self) -> np.ndarray:
        return -ROD_WEIGHT_N + self.rng.normal(0.0, FORCE_NOISE_N, 4)

    def move(self, speeds_m_s: np.ndarray) -> None:
        moved = self.true_stroke_m + speeds_m_s * PERIOD_S
        self.true_stroke_m = np.clip(moved, self.floor_m, self.ceiling_m)


@dataclass
class _Outcome:
    calibration: ZeroCalibration
    commands: np.ndarray

    @property
    def results(self):
        return self.calibration.results

    @property
    def events(self) -> list[str]:
        return [name for name, _ in self.calibration.events()]

    def move_skipped_legs(self) -> list[int]:
        return [leg for leg, result in enumerate(self.results)
                if result.reason is SkipReason.MOVE]


def _run(settings: ZeroCalibrationSettings, legs: _HangingLegs) -> _Outcome:
    calibration = ZeroCalibration(settings, MAX_SPEED_M_S, ROD_WEIGHT_N, STROKE_LIMIT_M)
    calibration.start(0.0, legs.read_strokes(), np.zeros(4, dtype=bool))
    commands = []
    period_index = 0
    while not calibration.is_finished and period_index * PERIOD_S < RUN_LIMIT_S:
        period_index += 1
        t_s = period_index * PERIOD_S
        speeds = calibration.step(t_s, legs.read_strokes(), legs.read_forces())
        commands.append(speeds.copy())
        legs.move(speeds)
    assert calibration.is_finished
    return _Outcome(calibration, np.array(commands))


def _scripted_fr_noise() -> NoiseSource:
    """Spec 416.3 test 2: FR start sample -0.15 mm, then -0.05 .. +0.12 mm, never below the
    start sample (the other legs read exactly)."""
    later_samples_m = np.array([-0.05, 0.12, 0.0, 0.08, -0.02, 0.05]) * 1e-3
    sample_index = -1

    def noise() -> np.ndarray:
        nonlocal sample_index
        values = np.zeros(4)
        values[FR] = -0.15e-3 if sample_index < 0 else later_samples_m[sample_index % 6]
        sample_index += 1
        return values

    return noise


def _is_same_outcome(first: _Outcome, second: _Outcome) -> bool:
    return (first.commands.shape == second.commands.shape
            and np.array_equal(first.commands, second.commands)
            and first.results == second.results
            and first.events == second.events
            and first.calibration.t_end_s == second.calibration.t_end_s)


# --- settings ----------------------------------------------------------------------------------


def test_class_default_is_the_old_rule_and_the_r8_preset_takes_0_5_mm() -> None:
    assert ZeroCalibrationSettings().return_timeout_tolerance_m is None
    assert C2Config().zero_calibration.return_timeout_tolerance_m is None
    assert R8_SETTINGS.return_timeout_tolerance_m == TOLERANCE_M
    assert C2Config().with_soil_response().zero_calibration.return_timeout_tolerance_m == (
        TOLERANCE_M
    )


def test_meta_key_appears_only_when_the_tolerance_is_on() -> None:
    assert "return_timeout_tolerance_m" not in ZeroCalibrationSettings().to_meta()
    assert R8_SETTINGS.to_meta()["return_timeout_tolerance_m"] == TOLERANCE_M
    old_run = _run(OLD_SETTINGS, _HangingLegs(np.random.default_rng(0)))
    assert "return_within_tolerance_m" not in old_run.calibration.to_meta()


def test_negative_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="return_timeout_tolerance_m"):
        ZeroCalibrationSettings(return_timeout_tolerance_m=-1e-4)


# --- spec 416.3 tests 1 .. 5 -------------------------------------------------------------------


def test_1_tolerance_off_keeps_the_old_skip() -> None:
    """Test 1: tolerance ``None`` -> the scripted hard-stop case is ``skipped: move`` after
    the time-out, with no tolerance event (bit identity with the old code: before/after
    comparison of 2026-10-29)."""
    legs = _HangingLegs(np.random.default_rng(1), stroke_noise=_scripted_fr_noise())
    outcome = _run(OLD_SETTINGS, legs)
    assert outcome.move_skipped_legs() == [FR]
    assert "WARN_PRESSURE_ZERO_SKIPPED:FR:move" in outcome.events
    assert not any(name.startswith("INFO_PRESSURE_ZERO_RETURN_TOL") for name in outcome.events)


def test_2_hard_stop_with_a_low_start_sample_is_accepted_at_the_time_out() -> None:
    """Test 2: the old rule skips FR, variant D calibrates it with one tolerance event."""
    old = _run(OLD_SETTINGS, _HangingLegs(np.random.default_rng(1),
                                          stroke_noise=_scripted_fr_noise()))
    new = _run(R8_SETTINGS, _HangingLegs(np.random.default_rng(1),
                                         stroke_noise=_scripted_fr_noise()))
    assert old.results[FR].reason is SkipReason.MOVE
    assert new.results[FR].status is LegCalibrationStatus.CALIBRATED
    assert all(result.is_calibrated for result in new.results)
    tolerance_events = [name for name in new.events
                        if name.startswith("INFO_PRESSURE_ZERO_RETURN_TOL")]
    # smallest FR displacement: -0.05 mm - (-0.15 mm) = +0.10 mm
    assert tolerance_events == ["INFO_PRESSURE_ZERO_RETURN_TOL:FR:0.100"]
    assert new.events.index(tolerance_events[0]) < new.events.index(
        "INFO_PRESSURE_ZERO_CALIBRATED:FR")
    assert new.calibration.to_meta()["return_within_tolerance_m"] == {
        "FR": pytest.approx(0.10e-3, abs=1e-12)}
    # the retract stage lasts until the time-out, as on the old skip path
    np.testing.assert_array_equal(new.commands[: len(old.commands)], old.commands)


def test_3_returns_within_the_time_keep_commands_and_results() -> None:
    """Test 3: whenever no leg reaches the retract time-out (mid-stroke start, or a hard-stop
    run whose noise allowed ``<= 0``), variant D and the old rule are identical."""
    compared_runs = 0
    for seed in range(200):
        for start_stroke_m in (0.0, 0.1):
            def legs(start=start_stroke_m, seed=seed) -> _HangingLegs:
                return _HangingLegs(np.random.default_rng(seed),
                                    true_stroke_m=np.full(4, start))

            old = _run(OLD_SETTINGS, legs())
            if old.move_skipped_legs():
                continue
            new = _run(R8_SETTINGS, legs())
            assert _is_same_outcome(old, new), (seed, start_stroke_m)
            compared_runs += 1
    assert compared_runs > 300


def test_4_a_leg_that_stays_0_8_mm_out_is_still_skipped() -> None:
    """Test 4: FR jams 0.8 mm above its start on the way back -> ``skipped: move`` with D."""
    floor_m = np.zeros(4)
    floor_m[FR] = 0.8e-3
    legs = _HangingLegs(np.random.default_rng(2), stroke_noise=lambda: np.zeros(4),
                        floor_m=floor_m)
    outcome = _run(R8_SETTINGS, legs)
    assert outcome.move_skipped_legs() == [FR]
    assert not any(name.startswith("INFO_PRESSURE_ZERO_RETURN_TOL") for name in outcome.events)


def test_5_the_extend_stage_is_unchanged() -> None:
    """Test 5: a leg that cannot make +3 mm (jam at +2.9 mm) is skipped as before, with the
    same commands under both settings."""
    ceiling_m = np.full(4, STROKE_LIMIT_M)
    ceiling_m[FR] = 2.9e-3

    def legs() -> _HangingLegs:
        return _HangingLegs(np.random.default_rng(3), stroke_noise=lambda: np.zeros(4),
                            ceiling_m=ceiling_m)

    old, new = _run(OLD_SETTINGS, legs()), _run(R8_SETTINGS, legs())
    assert new.move_skipped_legs() == [FR]
    assert _is_same_outcome(old, new)


# --- spec 416.3 test 6 -------------------------------------------------------------------------


def _move_skip_rate(settings: ZeroCalibrationSettings) -> float:
    skipped_legs = 0
    for seed in range(MONTE_CARLO_SEEDS):
        outcome = _run(settings, _HangingLegs(np.random.default_rng(seed)))
        skipped_legs += len(outcome.move_skipped_legs())
    return skipped_legs / (4 * MONTE_CARLO_SEEDS)


def test_6_monte_carlo_hard_stop_start() -> None:
    """Test 6: 1,000 seeds, stroke noise 0.1 mm, start at the hard stop: the old rule skips
    about 1 / (K + 1) of the legs (K samples at the stop before the time-out), variant D at
    most 0.1 %."""
    old_rate = _move_skip_rate(OLD_SETTINGS)
    new_rate = _move_skip_rate(R8_SETTINGS)
    assert 0.05 <= old_rate <= 0.15, old_rate
    assert new_rate <= 1e-3, new_rate
