"""C2 LAS-b lift-off approach slowdown (variant b0, ``las_targeted_rules.md`` 1.2, rev1 2).

The stage method is called directly on a LEVEL bench controller of ``test_c2_p30.py`` (pressure
judge, so the lower load estimate is the reading); the run state is set by hand for each start
gate S1 .. S8 / S7' and each end reason. The closed-loop identity with the targeted-run wrapper
(``04_scripts/04_hydraulic/coupled/las_targeted.py``) is the bit test B-2 / B-3 of rules 6, run
outside the unit tests.
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_c2_p30 import geometry, level_bench, load_reading, soil_on_config  # noqa: F401

from outrigger_sim.control.c2 import (
    LIFTOFF_SLOW_END_EVENT,
    LIFTOFF_SLOW_EVENT,
    C2Config,
    C2Controller,
    C2Phase,
    LiftoffApproachSlowSettings,
    LiftoffSlowEnd,
    OutputLimit,
    _RunState,
    diagonal_deficit_ratio,
)
from outrigger_sim.params import LEG_ORDER

FR = LEG_ORDER.index("FR")
RL = LEG_ORDER.index("RL")
PERIOD_S = 0.1
TWISTED_LOADS_N = np.array([120e3, 20e3, 30e3, 110e3])
"""Sum 280 kN (above 0.6 W_ref = 226 kN), FR lightest (below 3.5 F_min = 33 kN), rho 0.643."""
MORE_TWISTED_LOADS_N = np.array([121e3, 19e3, 30e3, 110e3])
"""Same sum, rho a little higher (rising)."""
HEAVY_LOADS_N = np.array([150e3, 20e3, 30e3, 150e3])
"""Sum 350 kN: above 0.85 W_ref (320 kN), the ``sum`` end level."""
FAST_SPEEDS_M_S = np.array([0.020, 0.018, 0.019, 0.017])
"""Mean 18.5 mm/s, above 0.16 v_max (3.35 mm/s)."""


def las_config(**changes) -> C2Config:
    """Soil response on, LAS-b on with the b0 values (``changes`` replace settings keys)."""
    config = soil_on_config()
    settings = replace(config.liftoff_approach_slow, enable=True, **changes)
    return replace(config, liftoff_approach_slow=settings)


@pytest.fixture
def controller(geometry) -> C2Controller:  # noqa: F811
    """LEVEL, crawler zone, no LOC, no soil mode, ``t`` at 20 s."""
    bench_controller = level_bench(geometry, las_config()).controller
    bench_controller._state.in_crawler_zone = True
    bench_controller._state.liftoff_slow = None
    bench_controller._las_t_s = 20.0
    return bench_controller


def stage(
    controller: C2Controller,
    loads_N: np.ndarray,
    speeds_m_s: np.ndarray = FAST_SPEEDS_M_S,
    reapproaching: np.ndarray | None = None,
) -> np.ndarray:
    """One LEVEL step of the stage, 0.1 s after the last one."""
    controller._las_t_s = round(controller._las_t_s + PERIOD_S, 10)
    if reapproaching is None:
        reapproaching = np.zeros(4, dtype=bool)
    reading = load_reading(controller._las_t_s, np.asarray(loads_N, dtype=float))
    return controller._apply_liftoff_approach_slow(reading, speeds_m_s, reapproaching)


def start(controller: C2Controller) -> np.ndarray:
    """First step without ``rho_{k-1}``, then a rising one: the slowdown starts."""
    stage(controller, TWISTED_LOADS_N)
    return stage(controller, MORE_TWISTED_LOADS_N)


def slow_events(controller: C2Controller) -> list[str]:
    prefixes = (f"{LIFTOFF_SLOW_EVENT}:", f"{LIFTOFF_SLOW_END_EVENT}:")
    return [event.name for event in controller.events if event.name.startswith(prefixes)]


def slow_mean_m_s(controller: C2Controller) -> float:
    return 0.16 * controller.geometry.max_speed_m_s


# --- settings, preset, defaults ----------------------------------------------------------------


def test_class_default_is_off_and_preset_is_b0() -> None:
    assert not C2Config().liftoff_approach_slow.enable
    assert _RunState.liftoff_slow is None  # class attribute (old pickles)
    assert C2Config().with_10hz_d1().liftoff_approach_slow == LiftoffApproachSlowSettings(
        enable=True,
        sum_on_fraction_W=0.6,
        light_leg_fraction_of_F_min=3.5,
        slow_mean_fraction=0.16,
        sum_off_fraction_W=0.85,
        off_periods=5,
        max_s=1.5,
        rho_on=0.18,
    )
    switched_off = C2Config().with_10hz_d1(liftoff_approach_slow=False)
    assert switched_off.liftoff_approach_slow == LiftoffApproachSlowSettings()


@pytest.mark.parametrize(
    "bad",
    [
        {"sum_on_fraction_W": 0.0},
        {"light_leg_fraction_of_F_min": 0.0},
        {"slow_mean_fraction": 0.0},
        {"slow_mean_fraction": 1.1},
        {"sum_on_fraction_W": 0.9, "sum_off_fraction_W": 0.85},
        {"off_periods": 0},
        {"max_s": 0.0},
    ],
)
def test_settings_validation(bad) -> None:
    with pytest.raises(ValueError):
        LiftoffApproachSlowSettings(**bad)


def test_old_pickle_reads_the_rule_off(geometry) -> None:  # noqa: F811
    copied = pickle.loads(pickle.dumps(C2Controller(geometry, C2Config())))
    copied.config.__dict__.pop("liftoff_approach_slow")
    copied._state.__dict__.pop("liftoff_slow")
    aged = pickle.loads(pickle.dumps(copied))
    assert aged.config.liftoff_approach_slow == LiftoffApproachSlowSettings()
    meta = json.loads(json.dumps(aged.meta()))["liftoff_approach_slow"]
    assert meta == {"settings": json.loads(json.dumps(LiftoffApproachSlowSettings().__dict__))}


def test_output_limit_key() -> None:
    assert OutputLimit.LIFTOFF_SLOW.value == "liftoff_slow"


# --- rho of S7' (rev1 2) -----------------------------------------------------------------------


def test_rho_formula_and_diagonal_partner() -> None:
    rho, leg = diagonal_deficit_ratio(TWISTED_LOADS_N)
    assert leg == FR
    assert rho == pytest.approx((280e3 - 2.0 * (20e3 + 30e3)) / 280e3)
    rho_rr, leg_rr = diagonal_deficit_ratio([100e3, 90e3, 80e3, 10e3])
    assert leg_rr == 3
    assert rho_rr == pytest.approx((280e3 - 2.0 * (10e3 + 100e3)) / 280e3)  # RR pairs FL


def test_rho_tie_picks_the_smaller_index() -> None:
    _, leg = diagonal_deficit_ratio([50e3, 10e3, 10e3, 50e3])
    assert leg == FR


def test_rho_without_a_positive_sum_is_nan() -> None:
    rho, _ = diagonal_deficit_ratio([0.0, 0.0, 0.0, 0.0])
    assert math.isnan(rho)


# --- start ---------------------------------------------------------------------------------------


def test_start_on_a_rising_twist_and_scale_to_the_slow_mean(controller) -> None:
    first = stage(controller, TWISTED_LOADS_N)
    assert first is FAST_SPEEDS_M_S  # no rho_{k-1}: not rising
    scaled = stage(controller, MORE_TWISTED_LOADS_N)
    assert slow_events(controller) == [f"{LIFTOFF_SLOW_EVENT}:FR"]
    cap_m_s = slow_mean_m_s(controller)
    expected = FAST_SPEEDS_M_S * (cap_m_s / float(np.mean(FAST_SPEEDS_M_S)))
    np.testing.assert_array_equal(scaled, expected)  # the wrapper's expression, bit for bit
    assert float(np.mean(scaled)) == pytest.approx(cap_m_s)
    np.testing.assert_allclose(scaled / FAST_SPEEDS_M_S, scaled[0] / FAST_SPEEDS_M_S[0])
    meta = controller.meta()["liftoff_approach_slow"]
    assert meta["start_s"] == pytest.approx(20.2)
    assert meta["start_leg"] == "FR"
    assert meta["start_rho"] == diagonal_deficit_ratio(MORE_TWISTED_LOADS_N)[0]
    assert meta["start_rho_prev"] == diagonal_deficit_ratio(TWISTED_LOADS_N)[0]
    assert meta["active_periods"] == 1
    assert meta["scaled_periods"] == 1


def test_a_slow_command_stays_while_active(controller) -> None:
    start(controller)
    slow = np.full(4, 0.5 * slow_mean_m_s(controller))
    assert stage(controller, MORE_TWISTED_LOADS_N, slow) is slow
    meta = controller.meta()["liftoff_approach_slow"]
    assert meta["active_periods"] == 2
    assert meta["scaled_periods"] == 1


def _block_s1(controller):
    controller.config = replace(controller.config, soil=replace(controller.config.soil,
                                                                enable=False))


def _block_s2(controller):
    controller._state.phase = C2Phase.DONE


def _block_s3(controller):
    controller._soil_state().is_liftoff_confirmed = True


def _block_s4(controller):
    controller._soil_state().is_soil_mode = True


def _block_s5(controller):
    controller._state.in_crawler_zone = False


GATE_BLOCKERS = {"S1": _block_s1, "S2": _block_s2, "S3": _block_s3, "S4": _block_s4,
                 "S5": _block_s5}


@pytest.mark.parametrize("gate", sorted(GATE_BLOCKERS))
def test_start_gate_blocks(controller, gate) -> None:
    stage(controller, TWISTED_LOADS_N)
    GATE_BLOCKERS[gate](controller)
    assert stage(controller, MORE_TWISTED_LOADS_N) is FAST_SPEEDS_M_S
    assert slow_events(controller) == []


def test_s1_can_be_dropped_for_a_baseline_without_soil_response(controller) -> None:
    """U-6 ABL (user decision 2026-11-08): ``require_soil_response`` False starts without it."""
    _block_s1(controller)
    settings = replace(controller.config.liftoff_approach_slow, require_soil_response=False)
    controller.config = replace(controller.config, liftoff_approach_slow=settings)
    assert start(controller) is not FAST_SPEEDS_M_S
    assert slow_events(controller) == [f"{LIFTOFF_SLOW_EVENT}:FR"]


def test_s6_reapproach_blocks(controller) -> None:
    stage(controller, TWISTED_LOADS_N)
    reapproaching = np.array([False, True, False, False])
    assert stage(controller, MORE_TWISTED_LOADS_N, reapproaching=reapproaching) is (
        FAST_SPEEDS_M_S)
    assert slow_events(controller) == []


@pytest.mark.parametrize(
    ("name", "first", "second"),
    [
        ("sum below alpha W_ref", TWISTED_LOADS_N * 0.5, MORE_TWISTED_LOADS_N * 0.5),
        ("light leg not below beta F_min",
         np.array([90e3, 40e3, 45e3, 105e3]), np.array([91e3, 39.5e3, 45e3, 105e3])),
        ("rho below rho_on",
         np.array([70e3, 30e3, 110e3, 70e3]), np.array([71e3, 29e3, 110e3, 70e3])),
        ("rho not rising", MORE_TWISTED_LOADS_N, TWISTED_LOADS_N),
        ("rho equal", TWISTED_LOADS_N, TWISTED_LOADS_N),
    ],
)
def test_s7_prime_blocks(controller, name, first, second) -> None:
    stage(controller, first)
    assert stage(controller, second) is FAST_SPEEDS_M_S, name
    assert slow_events(controller) == []


def test_s7_prime_rho_values_of_the_cases() -> None:
    low_rho, _ = diagonal_deficit_ratio([71e3, 29e3, 110e3, 70e3])
    assert diagonal_deficit_ratio([70e3, 30e3, 110e3, 70e3])[0] < low_rho < 0.18  # rising
    light_rho, _ = diagonal_deficit_ratio([91e3, 39.5e3, 45e3, 105e3])
    assert light_rho >= 0.18  # blocked by the light-leg condition alone


def test_s7_prime_needs_the_previous_period_to_be_a_level_step(controller) -> None:
    stage(controller, TWISTED_LOADS_N)
    controller._liftoff_slow_state().has_level_step_run = False
    controller._finish_liftoff_slow_period(20.15)  # a period without a LEVEL step
    assert controller._liftoff_slow_state().previous_rho is None
    assert stage(controller, MORE_TWISTED_LOADS_N) is FAST_SPEEDS_M_S
    assert stage(controller, np.array([122e3, 18e3, 30e3, 110e3])) is not FAST_SPEEDS_M_S


def test_s8_slow_mean_blocks(controller) -> None:
    slow = np.full(4, slow_mean_m_s(controller))  # mean equal: not above
    stage(controller, TWISTED_LOADS_N, slow)
    assert stage(controller, MORE_TWISTED_LOADS_N, slow) is slow
    assert slow_events(controller) == []


# --- ends ----------------------------------------------------------------------------------------


def _end_and_check(controller, reason: LiftoffSlowEnd, loads=MORE_TWISTED_LOADS_N, **kwargs):
    out = stage(controller, loads, **kwargs)
    assert out is FAST_SPEEDS_M_S  # the ending period keeps its command
    assert slow_events(controller) == [f"{LIFTOFF_SLOW_EVENT}:FR",
                                       f"{LIFTOFF_SLOW_END_EVENT}:{reason}"]
    assert controller.meta()["liftoff_approach_slow"]["end_reason"] == str(reason)


@pytest.mark.parametrize(
    ("reason", "blocker"),
    [(LiftoffSlowEnd.LOC, _block_s3), (LiftoffSlowEnd.PHASE, _block_s2),
     (LiftoffSlowEnd.SOIL, _block_s4)],
)
def test_end_on_a_state_change(controller, reason, blocker) -> None:
    start(controller)
    blocker(controller)
    _end_and_check(controller, reason)


def test_loc_end_stays_after_a_revocation(controller) -> None:
    start(controller)
    _block_s3(controller)
    _end_and_check(controller, LiftoffSlowEnd.LOC)
    controller._soil_state().is_liftoff_confirmed = False  # revoked: the latch stays
    assert controller._liftoff_slow_state().has_loc_been_seen


def test_end_on_a_reapproach(controller) -> None:
    start(controller)
    _end_and_check(controller, LiftoffSlowEnd.REAPPROACH,
                   reapproaching=np.array([False, False, True, False]))


def _without_soil_response(controller) -> None:
    """The U-6 ABL settings: soil response off, S1 dropped."""
    _block_s1(controller)
    settings = replace(controller.config.liftoff_approach_slow, require_soil_response=False)
    controller.config = replace(controller.config, liftoff_approach_slow=settings)


def test_abl_ends_in_the_period_that_leaves_the_crawler_zone(controller) -> None:
    """Spec 436.9.4: ``zone`` (S5 false) ends a slowdown without the soil response."""
    _without_soil_response(controller)
    start(controller)
    assert stage(controller, MORE_TWISTED_LOADS_N) is not FAST_SPEEDS_M_S  # still in the zone
    _block_s5(controller)
    _end_and_check(controller, LiftoffSlowEnd.ZONE)


def test_zone_comes_after_reapproach_and_before_sum(controller) -> None:
    _without_soil_response(controller)
    start(controller)
    _block_s5(controller)
    _end_and_check(controller, LiftoffSlowEnd.REAPPROACH,
                   reapproaching=np.array([False, False, True, False]))
    assert list(LiftoffSlowEnd).index(LiftoffSlowEnd.ZONE) == (
        list(LiftoffSlowEnd).index(LiftoffSlowEnd.REAPPROACH) + 1)
    assert list(LiftoffSlowEnd).index(LiftoffSlowEnd.SUM) == (
        list(LiftoffSlowEnd).index(LiftoffSlowEnd.ZONE) + 1)


def test_leaving_the_zone_does_not_end_the_c2_slowdown(controller) -> None:
    """With the soil response (C2 / V0 / VB) there is no ``zone`` end: commands unchanged."""
    start(controller)
    _block_s5(controller)
    assert stage(controller, MORE_TWISTED_LOADS_N) is not FAST_SPEEDS_M_S
    assert slow_events(controller) == [f"{LIFTOFF_SLOW_EVENT}:FR"]


def _release_zone_into_soil_mode(controller) -> None:
    """The crawler zone released before any LOC: with the soil response on, the soil mode
    starts in the same period (U-S9-C1)."""
    _block_s5(controller)
    _block_s4(controller)


NO_ACTION = None
REAPPROACHING_RL = np.array([False, False, True, False])
SOIL_ON_SCENARIOS = {
    "time": [(NO_ACTION, MORE_TWISTED_LOADS_N, None)] * 15,
    "sum": [(NO_ACTION, HEAVY_LOADS_N, None)] * 5,
    "reapproach": [(NO_ACTION, MORE_TWISTED_LOADS_N, REAPPROACHING_RL)],
    "loc": [(_block_s3, MORE_TWISTED_LOADS_N, None)],
    "phase": [(_block_s2, MORE_TWISTED_LOADS_N, None)],
    "zone released before LOC": [(NO_ACTION, MORE_TWISTED_LOADS_N, None),
                                 (_release_zone_into_soil_mode, MORE_TWISTED_LOADS_N, None)],
}
"""Steps after :func:`start`: (state change before the step, loads, re-approach flags)."""
TAIL_STEPS = 2
"""Steps after the scenario (no second start may differ either)."""


def _soil_on_run(bench_geometry, require_soil_response: bool, steps) -> tuple[list[bytes], str]:
    """Per-period command bytes and the end reason of one scenario with the soil response on."""
    bench_controller = level_bench(
        bench_geometry, las_config(require_soil_response=require_soil_response)).controller
    bench_controller._state.in_crawler_zone = True
    bench_controller._state.liftoff_slow = None
    bench_controller._las_t_s = 20.0
    commands = [stage(bench_controller, TWISTED_LOADS_N),
                stage(bench_controller, MORE_TWISTED_LOADS_N)]
    for action, loads, reapproaching in steps:
        if action is not None:
            action(bench_controller)
        commands.append(stage(bench_controller, loads, reapproaching=reapproaching))
    for _ in range(TAIL_STEPS):
        commands.append(stage(bench_controller, MORE_TWISTED_LOADS_N))
    end_reason = bench_controller.meta()["liftoff_approach_slow"]["end_reason"]
    return [np.asarray(command).tobytes() for command in commands], end_reason


@pytest.mark.parametrize("scenario", sorted(SOIL_ON_SCENARIOS))
def test_require_soil_response_is_inert_with_soil_response_on(
    geometry, scenario  # noqa: F811
) -> None:
    """ABL28 (control-expert decision (가), spec 436.9.4): with the soil response on, dropping
    S1 changes nothing, the ``zone`` end never comes first (a zone released before LOC starts
    the soil mode, end ``soil``)."""
    steps = SOIL_ON_SCENARIOS[scenario]
    commands_with_s1, end_with_s1 = _soil_on_run(geometry, True, steps)
    commands_without_s1, end_without_s1 = _soil_on_run(geometry, False, steps)
    assert commands_with_s1 == commands_without_s1
    assert end_with_s1 == end_without_s1
    assert end_with_s1 != str(LiftoffSlowEnd.ZONE)
    if scenario == "zone released before LOC":
        assert end_with_s1 == str(LiftoffSlowEnd.SOIL)


def test_end_on_a_period_without_a_level_step(controller) -> None:
    start(controller)
    slow = controller._liftoff_slow_state()
    slow.has_level_step_run = False
    controller._finish_liftoff_slow_period(20.3)
    assert slow_events(controller) == [f"{LIFTOFF_SLOW_EVENT}:FR",
                                       f"{LIFTOFF_SLOW_END_EVENT}:{LiftoffSlowEnd.PHASE}"]
    assert slow.end_s == pytest.approx(20.3)


def test_end_on_the_load_sum_after_five_periods_in_a_row(controller) -> None:
    start(controller)  # start period below the end level: count 0
    for _ in range(4):
        assert stage(controller, HEAVY_LOADS_N) is not FAST_SPEEDS_M_S
    stage(controller, MORE_TWISTED_LOADS_N)  # below: the count returns to 0
    for _ in range(4):
        assert stage(controller, HEAVY_LOADS_N) is not FAST_SPEEDS_M_S
    _end_and_check(controller, LiftoffSlowEnd.SUM, loads=HEAVY_LOADS_N)
    assert controller._liftoff_slow_state().end_s == pytest.approx(21.2)


def test_end_on_time(controller) -> None:
    start(controller)  # t_start 20.2 s
    for _ in range(14):
        assert stage(controller, MORE_TWISTED_LOADS_N) is not FAST_SPEEDS_M_S
    _end_and_check(controller, LiftoffSlowEnd.TIME)  # 21.7 s - 20.2 s = 1.5 s
    meta = controller.meta()["liftoff_approach_slow"]
    assert meta["end_s"] == pytest.approx(21.7)
    assert meta["active_periods"] == 15


def test_one_start_per_run(controller) -> None:
    start(controller)
    _block_s4(controller)
    stage(controller, MORE_TWISTED_LOADS_N)  # end: soil
    controller._soil_state().is_soil_mode = False
    stage(controller, TWISTED_LOADS_N)
    assert stage(controller, MORE_TWISTED_LOADS_N) is FAST_SPEEDS_M_S  # gates hold again
    assert len(slow_events(controller)) == 2


def test_reset_clears_the_run(controller) -> None:
    start(controller)
    controller.reset()
    assert controller._state.liftoff_slow is None


def test_off_leaves_the_state_alone(geometry) -> None:  # noqa: F811
    config = replace(las_config(), liftoff_approach_slow=LiftoffApproachSlowSettings())
    bench = level_bench(geometry, config)
    for _ in range(3):
        bench.step()
    assert bench.controller._state.liftoff_slow is None
    assert "start_s" not in bench.controller.meta()["liftoff_approach_slow"]
