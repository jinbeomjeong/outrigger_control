"""C2 P-S8-30 (user decision 2026-10-28, variant P30fz of ``r74_p30_screen.py``): the slow lift
and the fast re-approach before the lift-off confirmation (tests T1 .. T9 of the task).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` (no CHECK, pressure judge, so the lower load
estimate is the reading) with the soil response turned on: ``bench_config()`` has it off. The
bench strokes keep the crawler on the floor (clearance 0), so the crawler-zone latch is not
released and the soil mode does not start by itself. The closed-loop acceptance
(``r74_p30_screen.py`` with the project controller against the P30fz hashes) runs outside the
unit tests.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
)

from outrigger_sim.control.c2 import (
    LIFT_PAUSED_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    PreLocLiftPauseSettings,
    SoilResponseSettings,
    _Reading,
    _RunState,
)
from outrigger_sim.params import LEG_ORDER, load_params

RR = LEG_ORDER.index("RR")
FL = LEG_ORDER.index("FL")
HIGH_LOW_LOAD_N = 30e3
"""Above the 3.0 ``F_min`` start level (28.2 kN)."""
FALLEN_LOAD_N = 25e3
"""Below the start level, 5 kN under ``HIGH_LOW_LOAD_N`` (more than the 2 kN fall)."""
RECOVERED_LOAD_N = 34e3
"""Above the 3.5 ``F_min`` end level (33.0 kN)."""
SLOW_LIFT_MEAN_FRACTION = 0.16
MAX_PAUSE_S = 3.0
PERIOD_S = 0.1


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


class RecordingController(C2Controller):
    """Keeps the leg speeds that leave the P-S8-30 stage each period."""

    def __init__(self, geometry: C2Geometry, config: C2Config) -> None:
        super().__init__(geometry, config)
        self.stage_inputs: list[np.ndarray] = []
        self.stage_outputs: list[np.ndarray] = []

    def _apply_pre_loc_lift_pause(self, reading, leg_speeds):
        speeds = super()._apply_pre_loc_lift_pause(reading, leg_speeds)
        self.stage_inputs.append(np.array(leg_speeds))
        self.stage_outputs.append(np.array(speeds))
        return speeds


def soil_on_config(**pause_changes) -> C2Config:
    config = replace(bench_config(), soil=SoilResponseSettings(enable=True))
    if pause_changes:
        pause = replace(config.pre_loc_lift_pause, **pause_changes)
        config = replace(config, pre_loc_lift_pause=pause)
    return config


def level_bench(geometry: C2Geometry, config: C2Config) -> Bench:
    """LEVEL with the crawler on the floor (clearance 0) and no lift-off confirmation."""
    controller = RecordingController(geometry, config)
    bench = Bench(controller, geometry, geometry.operating_extension_m(0.0))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    assert not controller._is_liftoff_confirmed()
    return bench


def forces_with(leg: int, force_N: float) -> np.ndarray:
    forces = np.full(4, STEADY_LOAD_N)
    forces[leg] = force_N
    return forces


def load_reading(t_s: float, forces_N: np.ndarray) -> _Reading:
    """A reading for the stage methods called directly (lower estimate = reading)."""
    strokes = np.full(4, 0.3)
    return _Reading(
        t_s=t_s,
        cylinder_force_N=forces_N,
        rod_stroke_m=strokes,
        motor_stroke_m=strokes,
        cylinder_force_lowpass_N=forces_N,
        cylinder_force_lower_N=forces_N,
        cylinder_force_upper_N=forces_N,
        head_only_force_N=forces_N,
    )


def pause_events(controller: C2Controller) -> list[str]:
    return [
        event.name for event in controller.events if event.name.startswith(f"{LIFT_PAUSED_EVENT}:")
    ]


def pause_meta(controller: C2Controller) -> dict:
    return json.loads(json.dumps(controller.meta()))["pre_loc_lift_pause"]


def start_pause_on_rr(bench: Bench) -> None:
    """Two periods with RR at 30 kN, then RR falls to 25 kN: the slowdown starts."""
    for _ in range(2):
        bench.step(forces_with(RR, HIGH_LOW_LOAD_N))
    bench.step(forces_with(RR, FALLEN_LOAD_N))


# --- T1 / T9 settings ------------------------------------------------------------------------


def test_t1_class_default_is_off() -> None:
    assert C2Config().pre_loc_lift_pause == PreLocLiftPauseSettings()
    assert not PreLocLiftPauseSettings().enable
    assert _RunState.pre_loc_pause_leg is None  # class attributes (old pickles)
    assert _RunState.pre_loc_prev_loads_N is None


def test_t1_off_does_nothing_on_a_falling_leg(geometry) -> None:
    bench = level_bench(geometry, soil_on_config(enable=False))
    start_pause_on_rr(bench)
    controller = bench.controller
    assert pause_events(controller) == []
    assert controller._state.pre_loc_pause_leg is None
    assert controller._state.pre_loc_prev_loads_N is None
    np.testing.assert_array_equal(controller.stage_outputs, controller.stage_inputs)
    assert pause_meta(controller)["pauses"] == 0


def test_t1_old_pickle_reads_the_pause_off(geometry) -> None:
    controller = C2Controller(geometry, C2Config())
    copied = pickle.loads(pickle.dumps(controller))
    copied.config.__dict__.pop("pre_loc_lift_pause")
    for name in (
        "pre_loc_pause_leg",
        "pre_loc_pause_since_s",
        "pre_loc_prev_loads_N",
        "pre_loc_pause_count",
        "pre_loc_pause_periods",
    ):
        copied._state.__dict__.pop(name)
    aged = pickle.loads(pickle.dumps(copied))
    assert aged.config.pre_loc_lift_pause == PreLocLiftPauseSettings()
    assert aged._state.pre_loc_pause_leg is None
    assert pause_meta(aged) == {
        "settings": json.loads(json.dumps(PreLocLiftPauseSettings().__dict__)),
        "pauses": 0,
        "pause_periods": 0,
    }


def test_t9_preset_values() -> None:
    preset = C2Config().with_10hz_d1()
    assert preset.pre_loc_lift_pause == PreLocLiftPauseSettings(
        enable=True,
        on_fraction_of_F_min=3.0,
        off_fraction_of_F_min=3.5,
        falling_N=2000.0,
        max_pause_s=3.0,
        slow_lift_mean_fraction=0.16,
        reapproach_speed_factor=4.0,
        only_before_soil_mode=True,
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"on_fraction_of_F_min": 0.0},
        {"on_fraction_of_F_min": 3.0, "off_fraction_of_F_min": 2.9},
        {"slow_lift_mean_fraction": 0.0},
        {"slow_lift_mean_fraction": 1.1},
        {"reapproach_speed_factor": 0.9},
        {"max_pause_s": 0.0},
        {"falling_N": -1.0},
    ],
)
def test_t9_settings_validation(bad) -> None:
    with pytest.raises(ValueError):
        PreLocLiftPauseSettings(**bad)


# --- T2 .. T4 start, slowdown, end ---------------------------------------------------------------


def test_t2_falling_leg_starts_one_slowdown(geometry) -> None:
    bench = level_bench(geometry, soil_on_config())
    controller = bench.controller
    start_pause_on_rr(bench)
    assert pause_events(controller) == [f"{LIFT_PAUSED_EVENT}:RR"]
    assert controller._state.pre_loc_pause_leg == RR
    assert controller._state.pre_loc_pause_since_s == pytest.approx(bench.t_s)
    stage_input, stage_output = controller.stage_inputs[-1], controller.stage_outputs[-1]
    slow_mean_speed = SLOW_LIFT_MEAN_FRACTION * geometry.max_speed_m_s
    assert np.mean(stage_input) > slow_mean_speed  # the bench lift is faster
    assert np.mean(stage_output) == pytest.approx(slow_mean_speed, rel=1e-12)
    assert np.min(stage_output) >= 0.0
    # the same reading again: no second start
    bench.step(forces_with(RR, FALLEN_LOAD_N))
    assert len(pause_events(controller)) == 1
    meta = pause_meta(controller)
    assert (meta["pauses"], meta["pause_periods"]) == (1, 2)


def test_t2_slow_lift_keeps_the_attitude_and_twist_parts(geometry) -> None:
    """``u - max(0, min u)`` then a common rise: the leg differences stay."""
    controller = C2Controller(geometry, soil_on_config())
    speeds = np.array([0.6, 0.8, 0.7, 0.9]) * geometry.max_speed_m_s
    slowed = controller._slow_lift(speeds)
    np.testing.assert_allclose(np.diff(slowed), np.diff(speeds), rtol=0, atol=1e-15)
    assert np.mean(slowed) == pytest.approx(SLOW_LIFT_MEAN_FRACTION * geometry.max_speed_m_s)


@pytest.mark.parametrize(
    "rr_loads_N",
    [
        (20e3, FALLEN_LOAD_N),  # low but rising
        (FALLEN_LOAD_N, FALLEN_LOAD_N),  # low and standing
        (FALLEN_LOAD_N + 1.5e3, FALLEN_LOAD_N),  # fell by less than 2 kN
        (40e3, 30e3),  # fell 10 kN but above 3.0 F_min
    ],
)
def test_t3_no_start_without_a_fall_below_the_start_level(geometry, rr_loads_N) -> None:
    bench = level_bench(geometry, soil_on_config())
    for load_N in rr_loads_N:
        bench.step(forces_with(RR, load_N))
    assert pause_events(bench.controller) == []
    assert bench.controller._state.pre_loc_pause_leg is None


def test_t3_no_start_on_the_first_window_period(geometry) -> None:
    """Without a previous window sample there is no fall to judge."""
    controller = C2Controller(geometry, soil_on_config())
    controller._state.phase = C2Phase.LEVEL
    speeds = np.full(4, 0.5 * geometry.max_speed_m_s)
    reading = load_reading(1.0, forces_with(RR, 1e3))
    np.testing.assert_array_equal(controller._apply_pre_loc_lift_pause(reading, speeds), speeds)
    assert controller._state.pre_loc_pause_leg is None
    np.testing.assert_array_equal(controller._state.pre_loc_prev_loads_N, forces_with(RR, 1e3))


def test_t4_watched_leg_back_above_the_end_level_ends_it(geometry) -> None:
    bench = level_bench(geometry, soil_on_config())
    controller = bench.controller
    start_pause_on_rr(bench)
    bench.step(forces_with(RR, 32e3))  # above 3.0, below 3.5 F_min: still slowed
    assert controller._state.pre_loc_pause_leg == RR
    bench.step(forces_with(RR, RECOVERED_LOAD_N))
    assert controller._state.pre_loc_pause_leg is None
    np.testing.assert_array_equal(controller.stage_outputs[-1], controller.stage_inputs[-1])
    assert pause_meta(controller)["pause_periods"] == 2


def test_t4_time_limit_ends_it_after_3_s(geometry) -> None:
    bench = level_bench(geometry, soil_on_config())
    controller = bench.controller
    start_pause_on_rr(bench)
    start_s = bench.t_s
    while controller._state.pre_loc_pause_leg is not None and bench.t_s - start_s < 10.0:
        bench.step(forces_with(RR, FALLEN_LOAD_N))
    assert bench.t_s - start_s == pytest.approx(MAX_PAUSE_S)
    meta = pause_meta(controller)
    assert (meta["pauses"], meta["pause_periods"]) == (1, round(MAX_PAUSE_S / PERIOD_S))
    # a new fall starts the next one
    bench.step(forces_with(RR, FALLEN_LOAD_N - 3e3))
    assert len(pause_events(controller)) == 2


# --- T5 .. T8 window and limits ------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["is_soil_mode", "soil_mode_start_s"])
def test_t5_no_new_start_after_the_soil_mode_start(geometry, flag) -> None:
    bench = level_bench(geometry, soil_on_config())
    soil = bench.controller._soil_state()
    setattr(soil, flag, True if flag == "is_soil_mode" else bench.t_s)
    start_pause_on_rr(bench)
    assert pause_events(bench.controller) == []


def test_t5_running_slowdown_survives_the_soil_mode_start(geometry) -> None:
    bench = level_bench(geometry, soil_on_config())
    controller = bench.controller
    start_pause_on_rr(bench)
    controller._soil_state().soil_mode_start_s = bench.t_s
    for _ in range(5):
        bench.step(forces_with(RR, FALLEN_LOAD_N))
    assert controller._state.pre_loc_pause_leg == RR
    assert pause_meta(controller)["pause_periods"] == 6


def test_t5_without_the_soil_mode_rule_it_starts(geometry) -> None:
    bench = level_bench(geometry, soil_on_config(only_before_soil_mode=False))
    bench.controller._soil_state().soil_mode_start_s = bench.t_s
    start_pause_on_rr(bench)
    assert pause_events(bench.controller) == [f"{LIFT_PAUSED_EVENT}:RR"]


def test_t6_no_slowdown_after_the_liftoff_confirmation(geometry) -> None:
    bench = level_bench(geometry, soil_on_config())
    controller = bench.controller
    controller._soil_state().is_liftoff_confirmed = True
    start_pause_on_rr(bench)
    assert pause_events(controller) == []
    assert controller._state.pre_loc_prev_loads_N is None  # not updated outside the window
    np.testing.assert_array_equal(controller.stage_outputs, controller.stage_inputs)


def test_t6_confirmation_ends_a_running_slowdown(geometry) -> None:
    bench = level_bench(geometry, soil_on_config())
    controller = bench.controller
    start_pause_on_rr(bench)
    controller._soil_state().is_liftoff_confirmed = True
    bench.step(forces_with(RR, FALLEN_LOAD_N))
    assert controller._state.pre_loc_pause_leg is None
    np.testing.assert_array_equal(controller.stage_outputs[-1], controller.stage_inputs[-1])


def test_t6_outside_level_and_with_the_soil_response_off(geometry) -> None:
    speeds = np.full(4, 0.5 * geometry.max_speed_m_s)
    for config, phase in ((soil_on_config(), C2Phase.DONE), (bench_config(), C2Phase.LEVEL)):
        controller = C2Controller(geometry, config)
        controller._state.phase = phase
        controller._state.pre_loc_prev_loads_N = forces_with(RR, HIGH_LOW_LOAD_N)
        reading = load_reading(1.0, forces_with(RR, FALLEN_LOAD_N))
        result = controller._apply_pre_loc_lift_pause(reading, speeds)
        np.testing.assert_array_equal(result, speeds)
        assert controller._state.pre_loc_pause_leg is None


def fake_reapproach(controller: C2Controller, leg: int, *, is_retrigger: bool) -> None:
    controller._state.active_reapproaches[leg] = SimpleNamespace(is_retrigger=is_retrigger)


@pytest.mark.parametrize(
    ("config_name", "phase", "is_confirmed", "is_retrigger", "factor"),
    [
        ("pause_on", C2Phase.LEVEL, False, False, 4.0),
        ("pause_on", C2Phase.LEVEL, False, True, 0.6 * 4.0),
        ("pause_on", C2Phase.LEVEL, True, False, 1.0),
        ("pause_on", C2Phase.LEVEL, True, True, 0.6),
        ("pause_on", C2Phase.DONE, False, False, 1.0),
        ("pause_off", C2Phase.LEVEL, False, False, 1.0),
        ("soil_off", C2Phase.LEVEL, False, False, 1.0),
    ],
)
def test_t7_reapproach_factor_only_inside_the_window(
    geometry, config_name, phase, is_confirmed, is_retrigger, factor
) -> None:
    config = {
        "pause_on": soil_on_config(),
        "pause_off": soil_on_config(enable=False),
        "soil_off": bench_config(),
    }[config_name]
    controller = C2Controller(geometry, config)
    controller._state.phase = phase
    controller._soil_state().is_liftoff_confirmed = is_confirmed
    fake_reapproach(controller, RR, is_retrigger=is_retrigger)
    assert controller._reapproach_speed_factor(RR) == factor  # exact: same product order


def test_t7_reapproach_factor_applies_without_a_slowdown(geometry) -> None:
    controller = C2Controller(geometry, soil_on_config())
    controller._state.phase = C2Phase.LEVEL
    fake_reapproach(controller, FL, is_retrigger=False)
    assert controller._state.pre_loc_pause_leg is None
    assert controller._reapproach_speed_factor(FL) == 4.0


@pytest.mark.parametrize(
    "fractions",
    [
        (0.16, 0.16, 0.16, 0.16),  # exactly at the slow mean
        (0.08, 0.13, 0.12, 0.07),
        (-0.07, 0.0, 0.02, -0.15),
    ],
)
def test_t8_command_at_or_below_the_slow_mean_stays(geometry, fractions) -> None:
    controller = C2Controller(geometry, soil_on_config())
    speeds = np.array(fractions) * geometry.max_speed_m_s
    assert controller._slow_lift(speeds) is speeds
