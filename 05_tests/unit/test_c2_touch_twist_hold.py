"""C4G2: twist hold and vector ramp at the LEVEL entry (TOUCH phase study, 2026-11-04).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` for the rules; the slow test runs stored harness rows
in dynamics-dev (``returned_clip_hash_runner.py``) with both switches off. The bench strokes do not
follow the commands, so a hold keeps the error ``tau*`` of its first period.
"""

from __future__ import annotations

import copy
import json
import os
import pickle
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    PERIOD_S,
    RR,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    computed_command,
    lifted_rr_forces,
    operating_strokes,
)

from outrigger_sim.control.c2 import (
    COMMAND_COMPONENT_NAMES,
    TOUCH_TWIST_HOLD_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    OutputLimit,
    TouchTwistHoldSettings,
)
from outrigger_sim.params import load_params

HASH_RUNNER = Path(__file__).with_name("returned_clip_hash_runner.py")
ROOT = Path(__file__).resolve().parents[2]
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The harnesses need dynamics-dev (numba, sympy), not the Chrono-dev test env."""
HARNESS_WORKERS = 4
HARNESS_TIMEOUT_S = 900
STORED_HASHES = {
    "R4": "ca3d46ecf9bb90646bf1ed19fd197fb64f8f6d8c56ab089a80e8c42f8b66976d",
    "R9": "3bf5fb08b7efe3d8b673782b2ceb76fcb7efddcd5a45374583d22380231148bf",
    "R16": "83afbea09ebba4696970a2e957a2aba8106857a4eef1dabc4e731b9e92d3a5af",
    "S1": "6198f676af09c56ee58a0718c2b9f2d5d1b1d1b016044839f995db5cb57628b1",
}
"""``06_analysis/02_control/touch_phase/hash_check.json`` (commands before C4G1 and the clip)."""
GAIN_1_S = 2.5
HOLD_S = 1.5
CAP_M = 3.0e-3
DEADBAND_N = 1.0e3
RAMP_TWIST_TOL_M_S = 0.2e-3
HOLD_PERIODS = round(HOLD_S / PERIOD_S)
TWIST_LOAD_N = 20e3
PERIODS_PAST_THE_HOLD = 5


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def hold_config(*, is_clipped: bool = False, is_hold_on: bool = True) -> C2Config:
    settings = TouchTwistHoldSettings(enable=is_hold_on, vector_ramp=is_hold_on)
    return replace(bench_config(), touch_twist_hold=settings, clip_returned_command=is_clipped)


def forces_with_twist(geometry: C2Geometry, twist_load_N: float) -> np.ndarray:
    """Leg forces with ``n^T F = twist_load_N``, every leg above the touch load."""
    return STEADY_LOAD_N + twist_load_N * geometry.twist_vector


def level_entry_bench(
    geometry: C2Geometry,
    twist_load_N: float,
    config: C2Config | None = None,
) -> Bench:
    """TOUCH with this twist load on every sample, stopped at the first LEVEL period."""
    controller = C2Controller(geometry, hold_config() if config is None else config)
    bench = Bench(controller, geometry, operating_strokes(geometry))
    forces = forces_with_twist(geometry, twist_load_N)
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step(forces)
    assert controller.phase is C2Phase.LEVEL
    return bench


def scripted_bench(geometry, monkeypatch, config: C2Config, fractions) -> Bench:
    """10 Hz bench in LEVEL whose ``_phase_command`` returns ``fractions * v_max``."""
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert bench.controller.phase is C2Phase.LEVEL
    speeds = iter(np.asarray(fractions, float) * geometry.max_speed_m_s)
    zero = np.zeros(4)
    monkeypatch.setattr(bench.controller, "_phase_command", lambda _reading: next(speeds, zero))
    return bench


def computed_commands_of(bench: Bench, periods: int) -> np.ndarray:
    commands = []
    for _ in range(periods):
        bench.step()
        commands.append(computed_command(bench.controller))
    return np.array(commands)


def apply_hold_to(controller: C2Controller, leg_speeds: np.ndarray) -> np.ndarray:
    """The hold stage alone on a chosen LEVEL command, on the last reading."""
    return controller._apply_touch_twist_hold(controller._state.last_reading, leg_speeds)


def correction_of(bench: Bench) -> np.ndarray:
    return bench.controller.command_components_m_s["touch_twist"]


# --- settings ------------------------------------------------------------------------------------


def test_off_by_default_and_in_the_preset() -> None:
    assert C2Config().touch_twist_hold == TouchTwistHoldSettings()
    assert C2Config.touch_twist_hold == TouchTwistHoldSettings()  # class attribute (old pickles)
    preset = C2Config().with_10hz_d1().touch_twist_hold
    assert preset.enable is False
    assert preset.vector_ramp is False


def test_preset_keyword_touches_only_the_two_switches() -> None:
    preset = C2Config().with_10hz_d1()
    switched_on = C2Config().with_10hz_d1(touch_twist_hold=True)
    assert switched_on.touch_twist_hold.enable is True
    assert switched_on.touch_twist_hold.vector_ramp is True
    assert replace(switched_on, touch_twist_hold=TouchTwistHoldSettings()) == preset


def test_unpickled_config_without_the_field_reads_off() -> None:
    older_config = pickle.loads(pickle.dumps(C2Config()))
    object.__delattr__(older_config, "touch_twist_hold")
    assert older_config.touch_twist_hold.enable is False
    assert older_config.touch_twist_hold.vector_ramp is False


def test_settings_are_the_specified_values() -> None:
    settings = TouchTwistHoldSettings()
    assert settings.gain_1_s == GAIN_1_S
    assert settings.hold_s == HOLD_S
    assert settings.cap_m == CAP_M
    assert settings.deadband_N == DEADBAND_N
    assert settings.estimate_samples == 3


@pytest.mark.parametrize(
    "bad", [{"gain_1_s": 0.0}, {"hold_s": 0.0}, {"cap_m": -1.0}, {"estimate_samples": 0},
            {"deadband_N": -1.0}]
)
def test_bad_settings_are_refused(bad) -> None:
    with pytest.raises(ValueError):
        TouchTwistHoldSettings(**bad)


def test_twist_vector_is_the_specified_one(geometry) -> None:
    np.testing.assert_allclose(geometry.twist_vector, (0.476, -0.476, -0.523, 0.523), atol=1e-3)


# --- D_hat and the target -------------------------------------------------------------------------


@pytest.mark.parametrize("twist_load_N", [TWIST_LOAD_N, -TWIST_LOAD_N])
def test_target_is_minus_the_twist_load_over_the_stiffness(geometry, twist_load_N) -> None:
    bench = level_entry_bench(geometry, twist_load_N)
    meta = bench.controller.meta()["touch_twist_hold"]
    expected_m = -twist_load_N / geometry.nominal_pad_stiffness_N_m
    assert meta["twist_load_estimate_N"] == pytest.approx(twist_load_N)
    assert meta["target_m"] == pytest.approx(expected_m)
    assert abs(expected_m) < CAP_M


def test_estimate_takes_the_last_three_touch_samples(geometry) -> None:
    controller = C2Controller(geometry, hold_config())
    bench = Bench(controller, geometry, operating_strokes(geometry))
    twist_loads_N = (90e3, 90e3, 90e3, 3e3, 6e3, 9e3)
    assert len(twist_loads_N) == TOUCH_HOLD_SAMPLES
    for twist_load_N in twist_loads_N:
        bench.step(forces_with_twist(geometry, twist_load_N))
    estimate_N = controller.meta()["touch_twist_hold"]["twist_load_estimate_N"]
    assert estimate_N == pytest.approx(6e3)


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_target_is_clipped_to_three_millimetres(geometry, sign) -> None:
    large_load_N = sign * 1.5 * CAP_M * geometry.nominal_pad_stiffness_N_m
    bench = level_entry_bench(geometry, large_load_N)
    assert bench.controller.meta()["touch_twist_hold"]["target_m"] == -sign * CAP_M


@pytest.mark.parametrize("twist_load_N", [0.0, 0.99 * DEADBAND_N, -0.99 * DEADBAND_N])
def test_inside_the_dead_band_no_hold_starts(geometry, twist_load_N) -> None:
    bench = level_entry_bench(geometry, twist_load_N)
    controller = bench.controller
    assert controller.meta()["touch_twist_hold"]["target_m"] is None
    assert not [event for event in controller.events if TOUCH_TWIST_HOLD_EVENT in event.name]
    for _ in range(3):
        bench.step(forces_with_twist(geometry, twist_load_N))
        np.testing.assert_array_equal(correction_of(bench), 0.0)


def test_just_outside_the_dead_band_a_hold_starts(geometry) -> None:
    bench = level_entry_bench(geometry, 1.01 * DEADBAND_N)
    assert bench.controller.meta()["touch_twist_hold"]["target_m"] is not None
    names = [event.name for event in bench.controller.events]
    assert any(name.startswith(f"{TOUCH_TWIST_HOLD_EVENT}:") for name in names)


# --- the hold -------------------------------------------------------------------------------------


def test_correction_is_gain_times_error_along_the_twist_vector(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    target_m = bench.controller.meta()["touch_twist_hold"]["target_m"]
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    bench.step(forces)
    np.testing.assert_allclose(
        correction_of(bench), GAIN_1_S * target_m * geometry.twist_vector, rtol=1e-12
    )


def test_error_is_measured_from_the_touch_end_strokes(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    target_m = bench.controller.meta()["touch_twist_hold"]["target_m"]
    twist = geometry.twist_vector
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    bench.strokes_m = bench.strokes_m + target_m * twist  # moved all the way to the target
    bench.step(forces)
    np.testing.assert_allclose(correction_of(bench), 0.0, atol=1e-5 * abs(GAIN_1_S * target_m))


def test_common_motion_does_not_count_as_twist(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    target_m = bench.controller.meta()["touch_twist_hold"]["target_m"]
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    bench.strokes_m = bench.strokes_m + 0.010  # n sums to zero
    bench.step(forces)
    np.testing.assert_allclose(
        correction_of(bench), GAIN_1_S * target_m * geometry.twist_vector, atol=1e-9
    )


def test_hold_ends_after_its_time_and_the_meta_reports_it(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    entry_t_s = bench.t_s
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    active_periods = 0
    for _ in range(HOLD_PERIODS + PERIODS_PAST_THE_HOLD):
        bench.step(forces)
        active_periods += int(np.any(correction_of(bench) != 0.0))
    meta = bench.controller.meta()["touch_twist_hold"]
    assert meta["start_t_s"] == entry_t_s
    assert meta["end_t_s"] == pytest.approx(entry_t_s + HOLD_S, abs=PERIOD_S + 1e-9)
    assert active_periods in (HOLD_PERIODS - 1, HOLD_PERIODS)
    np.testing.assert_array_equal(correction_of(bench), 0.0)


def test_hold_starts_once_only(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    for _ in range(HOLD_PERIODS + PERIODS_PAST_THE_HOLD):
        bench.step(forces)
    names = [event.name for event in bench.controller.events]
    assert sum(TOUCH_TWIST_HOLD_EVENT in name for name in names) == 1


def test_no_leg_gets_a_negative_command(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    correction = correction_of(bench)
    assert correction.min() < 0.0, "the bench must ask for a negative leg"
    speeds = apply_hold_to(bench.controller, np.zeros(4))
    assert speeds.min() == 0.0
    is_negative = correction < 0.0
    np.testing.assert_array_equal(speeds[is_negative], 0.0)
    np.testing.assert_allclose(speeds[~is_negative], correction[~is_negative], rtol=1e-12)


def test_set_above_the_limit_is_rescaled_to_v_max(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    correction = correction_of(bench)
    limit = geometry.max_speed_m_s
    speeds = apply_hold_to(bench.controller, np.full(4, limit))
    assert speeds.max() == pytest.approx(limit, rel=1e-15)
    unscaled = np.full(4, limit) + correction
    np.testing.assert_allclose(speeds, unscaled * limit / unscaled.max(), rtol=1e-12)


def test_set_within_the_limit_is_not_rescaled(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    correction = correction_of(bench)
    base = np.full(4, 0.5 * geometry.max_speed_m_s)
    np.testing.assert_allclose(apply_hold_to(bench.controller, base), base + correction, rtol=1e-12)


def test_limit_flag_marks_a_rescaled_period(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    controller = bench.controller
    controller._state.output_limit_flags[OutputLimit.SPEED_SCALE.value][:] = False
    apply_hold_to(controller, np.full(4, geometry.max_speed_m_s))
    assert controller.output_limit_flags[OutputLimit.SPEED_SCALE.value].any()


def test_component_is_named_and_the_sum_stays_the_raw_output(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    controller = bench.controller
    components = controller.command_components_m_s
    assert COMMAND_COMPONENT_NAMES[-1] == "phase_path"  # outside LEVEL: only that one
    assert tuple(components) == COMMAND_COMPONENT_NAMES
    assert np.any(components["touch_twist"] != 0.0)
    np.testing.assert_allclose(sum(components.values()), controller.raw_output_m_s, atol=1e-12)


def test_deep_copied_controller_goes_on_with_the_same_hold(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    bench.step(forces)
    copied = replace_controller_with_copy(bench)
    for _ in range(HOLD_PERIODS + PERIODS_PAST_THE_HOLD):
        original_output = bench.step(forces)
        copied_output = copied.step(forces)
        assert original_output.tobytes() == copied_output.tobytes()


def replace_controller_with_copy(bench: Bench) -> Bench:
    return Bench(
        copy.deepcopy(bench.controller),
        bench.geometry,
        bench.strokes_m.copy(),
        t_s=bench.t_s,
    )


# --- a re-approach ends the hold ------------------------------------------------------------------


def test_reapproach_ends_the_hold_and_the_meta_says_why(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    controller = bench.controller
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    assert np.any(correction_of(bench) != 0.0)
    bench.step(lifted_rr_forces())
    assert RR in controller._state.active_reapproaches
    np.testing.assert_array_equal(correction_of(bench), 0.0)
    meta = controller.meta()["touch_twist_hold"]
    assert meta["end_reason"] == "reapproach"
    assert meta["end_t_s"] == bench.t_s
    assert controller._state.touch_twist.is_holding is False


def test_correction_does_not_come_back_after_the_reapproach(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    controller = bench.controller
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    bench.step(forces)
    controller._state.active_reapproaches[RR] = object()
    leg_speeds = np.full(4, 0.5 * geometry.max_speed_m_s)
    assert apply_hold_to(controller, leg_speeds) is leg_speeds
    del controller._state.active_reapproaches[RR]
    assert apply_hold_to(controller, leg_speeds) is leg_speeds
    assert controller.meta()["touch_twist_hold"]["end_reason"] == "reapproach"


def test_hold_time_is_the_end_reason_without_a_reapproach(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    assert bench.controller.meta()["touch_twist_hold"]["end_reason"] is None
    for _ in range(HOLD_PERIODS + PERIODS_PAST_THE_HOLD):
        bench.step(forces)
    assert bench.controller.meta()["touch_twist_hold"]["end_reason"] == "time"


def test_leaving_level_is_the_end_reason(geometry) -> None:
    bench = level_entry_bench(geometry, TWIST_LOAD_N)
    bench.step(forces_with_twist(geometry, TWIST_LOAD_N))
    controller = bench.controller
    controller._state.phase = C2Phase.DONE
    leg_speeds = np.zeros(4)
    assert apply_hold_to(controller, leg_speeds) is leg_speeds
    assert controller.meta()["touch_twist_hold"]["end_reason"] == "phase"


# --- G2: the twist test ---------------------------------------------------------------------------


def level_controller(geometry, tolerance_m_s: float = RAMP_TWIST_TOL_M_S) -> C2Controller:
    settings = TouchTwistHoldSettings(vector_ramp=True, ramp_twist_tol_m_s=tolerance_m_s)
    config = replace(bench_config(), touch_twist_hold=settings)
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert bench.controller.phase is C2Phase.LEVEL
    return bench.controller


def set_with_limited_twist(geometry, twist_m_s: float) -> tuple[np.ndarray, np.ndarray]:
    """(requested, per-leg limited): RR cut alone, the limited set with ``n^T du = twist_m_s``."""
    twist = geometry.twist_vector
    limit = 0.25 * geometry.max_speed_m_s
    limited = np.array([limit, limit, limit, limit])
    limited[RR] = limit + twist_m_s / twist[RR]
    requested = limited.copy()
    requested[RR] = 2.0 * limited[RR]
    return requested, limited


def test_tolerance_is_the_assumed_value() -> None:
    assert TouchTwistHoldSettings().ramp_twist_tol_m_s == RAMP_TWIST_TOL_M_S


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_limited_twist_below_the_tolerance_keeps_the_per_leg_limit(geometry, sign) -> None:
    controller = level_controller(geometry)
    requested, limited = set_with_limited_twist(geometry, sign * 0.99 * RAMP_TWIST_TOL_M_S)
    result = controller._vector_ramp_increment(requested, requested, limited)
    assert result is limited
    assert controller._state.is_vector_ramp_done is False


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_limited_twist_above_the_tolerance_takes_the_common_ratio(geometry, sign) -> None:
    controller = level_controller(geometry)
    requested, limited = set_with_limited_twist(geometry, sign * 1.01 * RAMP_TWIST_TOL_M_S)
    result = controller._vector_ramp_increment(requested, requested, limited)
    np.testing.assert_allclose(result, 0.5 * requested, rtol=1e-12)


def test_zero_tolerance_is_g1(geometry) -> None:
    controller = level_controller(geometry, tolerance_m_s=0.0)
    requested, limited = set_with_limited_twist(geometry, 0.0)
    result = controller._vector_ramp_increment(requested, requested, limited)
    np.testing.assert_allclose(result, 0.5 * requested, rtol=1e-12)


def test_front_rear_difference_keeps_its_bits(geometry, monkeypatch) -> None:
    """A level start: rear slower than front, every leg at the limit, ``n^T du`` = 0."""
    direction = np.array([1.0, 1.0, 0.9, 0.9])
    fractions = [direction] * 8
    bench_off = scripted_bench(geometry, monkeypatch, hold_config(is_hold_on=False), fractions)
    bench_on = scripted_bench(geometry, monkeypatch, hold_config(), fractions)
    commands_off = computed_commands_of(bench_off, 8)
    commands_on = computed_commands_of(bench_on, 8)
    assert commands_on.tobytes() == commands_off.tobytes()


def test_uncut_period_ends_the_ramp_also_below_the_tolerance(geometry) -> None:
    controller = level_controller(geometry)
    small = np.array([1e-5, 1e-5, 1e-5, 1e-5])
    assert controller._vector_ramp_increment(small, small, small) is small
    assert controller._state.is_vector_ramp_done is True


# --- G1 rule of the ratio -------------------------------------------------------------------------


def test_ramp_scales_all_four_increments_by_one_ratio(geometry, monkeypatch) -> None:
    direction = np.array([1.0, 0.5, -0.5, 0.0])
    bench = scripted_bench(geometry, monkeypatch, hold_config(), [direction] * 8)
    commands = computed_commands_of(bench, 4)
    limit = geometry.max_speed_m_s
    for period, command in enumerate(commands, start=1):
        np.testing.assert_allclose(command, period * 0.25 * direction * limit, rtol=1e-12)


def test_off_each_leg_ramps_on_its_own(geometry, monkeypatch) -> None:
    direction = np.array([1.0, 0.5, -0.5, 0.0])
    config = hold_config(is_hold_on=False)
    bench = scripted_bench(geometry, monkeypatch, config, [direction] * 8)
    first = computed_commands_of(bench, 1)[0]
    np.testing.assert_allclose(
        first, np.array([0.25, 0.25, -0.25, 0.0]) * geometry.max_speed_m_s, rtol=1e-12
    )


def test_ramp_ends_at_the_first_period_without_a_cut(geometry, monkeypatch) -> None:
    direction = np.array([1.0, 0.5, -0.5, 0.0])
    later_step = np.array([1.0, 0.0, 0.0, 1.0])
    fractions = [direction] * 5 + [later_step] * 5
    bench = scripted_bench(geometry, monkeypatch, hold_config(), fractions)
    commands = computed_commands_of(bench, 5)
    assert bench.controller._state.is_vector_ramp_done is True
    np.testing.assert_allclose(commands[-1], direction * geometry.max_speed_m_s, rtol=1e-12)
    bench.step()
    limit = geometry.max_speed_m_s
    expected = (direction + np.array([0.0, -0.25, 0.25, 0.25])) * limit  # per leg again
    np.testing.assert_allclose(computed_command(bench.controller), expected, rtol=1e-12)


def test_zero_command_does_not_end_the_ramp(geometry, monkeypatch) -> None:
    direction = np.array([1.0, 0.5, -0.5, 0.0])
    bench = scripted_bench(geometry, monkeypatch, hold_config(), [np.zeros(4)] * 2 + [direction])
    computed_commands_of(bench, 2)
    assert bench.controller._state.is_vector_ramp_done is False
    np.testing.assert_allclose(
        computed_commands_of(bench, 1)[0], 0.25 * direction * geometry.max_speed_m_s, rtol=1e-12
    )


def test_ramp_does_not_act_outside_level(geometry) -> None:
    controller = C2Controller(geometry, hold_config())
    bench = Bench(controller, geometry, np.full(4, 0.1))
    bench.step(np.zeros(4))
    assert controller.phase is C2Phase.TOUCH
    requested = np.array([1.0, 0.5, 0.25, 0.0])
    limited = np.array([0.25, 0.25, 0.25, 0.0])
    assert controller._vector_ramp_increment(requested, requested, limited) is limited


@pytest.mark.parametrize(
    "direction",
    [(1.0, 1.0, 1.0, 1.0), (1.0, -1.0, 1.0, -1.0), (1.0, 1.0, 0.0, 0.0)],
    ids=["same_way", "opposite_ways", "two_still"],
)
def test_one_common_limit_ratio_keeps_the_bits_of_the_per_leg_limit(
    geometry, monkeypatch, direction
) -> None:
    fractions = [np.array(direction)] * 8
    bench_off = scripted_bench(geometry, monkeypatch, hold_config(is_hold_on=False), fractions)
    bench_on = scripted_bench(geometry, monkeypatch, hold_config(), fractions)
    commands_off = computed_commands_of(bench_off, 8)
    commands_on = computed_commands_of(bench_on, 8)
    assert commands_on.tobytes() == commands_off.tobytes()


def test_no_correction_needed_stays_bit_for_bit(geometry) -> None:
    """Dead band and equal legs: with C4G1 on, the whole run returns what it does off."""
    bench_off = level_entry_bench(geometry, 0.0, hold_config(is_hold_on=False))
    bench_on = level_entry_bench(geometry, 0.0)
    for _ in range(40):
        output_off = bench_off.step()
        output_on = bench_on.step()
        assert output_on.tobytes() == output_off.tobytes()
    assert np.any(np.array(bench_off.outputs) != 0.0), "the bench must move"


# --- the returned-command clip --------------------------------------------------------------------


def test_clip_cuts_only_the_returned_command_with_the_ramp_on(geometry, monkeypatch) -> None:
    fractions = [np.array([1.75, 0.5, -0.5, 0.0])] * 12
    bench_plain = scripted_bench(geometry, monkeypatch, hold_config(), fractions)
    bench_clipped = scripted_bench(geometry, monkeypatch, hold_config(is_clipped=True), fractions)
    limit = geometry.max_speed_m_s
    peak_plain = 0.0
    for _ in fractions:
        plain = bench_plain.step()
        clipped = bench_clipped.step()
        peak_plain = max(peak_plain, float(np.abs(plain).max()))
        np.testing.assert_array_equal(clipped, np.clip(plain, -limit, limit))
        np.testing.assert_array_equal(
            computed_command(bench_clipped.controller), computed_command(bench_plain.controller)
        )
    assert peak_plain > limit


def test_clip_changes_nothing_in_a_hold(geometry) -> None:
    """The hold rescales to ``v_max`` itself, so the clip has nothing left to cut."""
    forces = forces_with_twist(geometry, TWIST_LOAD_N)
    bench_plain = level_entry_bench(geometry, TWIST_LOAD_N)
    bench_clipped = level_entry_bench(geometry, TWIST_LOAD_N, hold_config(is_clipped=True))
    for _ in range(HOLD_PERIODS + PERIODS_PAST_THE_HOLD):
        plain = bench_plain.step(forces)
        clipped = bench_clipped.step(forces)
        assert plain.tobytes() == clipped.tobytes()
    assert np.array(bench_plain.outputs).max() <= geometry.max_speed_m_s


# --- stored harness rows -------------------------------------------------------------------------


def _run_harness_row(case_id: str, out_dir: Path) -> dict:
    out_path = out_dir / f"{case_id}.json"
    environment = {
        **os.environ,
        "MKL_THREADING_LAYER": "TBB",
        "OMP_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run(
        [str(HARNESS_PYTHON), "-I", "-B", str(HASH_RUNNER), case_id, "off", str(out_path)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        timeout=HARNESS_TIMEOUT_S,
    )
    return json.loads(out_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def harness_rows(tmp_path_factory) -> dict[str, dict]:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_dir = tmp_path_factory.mktemp("touch_twist_hold")
    with ThreadPoolExecutor(HARNESS_WORKERS) as pool:
        rows = list(pool.map(lambda case_id: _run_harness_row(case_id, out_dir), STORED_HASHES))
    for row in rows:
        assert row["foreign_modules"] == [], "the run must import this checkout only"
    return {row["case"]: row for row in rows}


@pytest.mark.slow
@pytest.mark.parametrize("case_id", STORED_HASHES)
def test_clip_off_and_hold_off_equal_the_stored_row(harness_rows, case_id) -> None:
    assert harness_rows[case_id]["hash"] == STORED_HASHES[case_id]
