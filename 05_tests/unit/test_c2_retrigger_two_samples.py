"""K1: a re-trigger start needs two low samples in a row (TOUCH phase study, 2026-11-04).

Synthetic 10 Hz benches of ``test_c2_reapproach_retrigger.py``. The first start after an event
keeps its one sample, so the response to a real sink does not get later.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from test_c2_r8d1 import FL, RR, lifted_rr_forces  # same test folder
from test_c2_reapproach_retrigger import (
    EXIT_SAMPLES,
    FR,
    LIFTED_READING_N,
    OPPOSITE_LOW_READING_N,
    names,
    recorder_ready_bench,
    rr_settled_forces,
    rule_config,
    start_and_end_rr,
    step_quiet,
    with_leg,
)

from outrigger_sim.control.c2 import (
    R8_D1_REAPPROACH_RETRIGGER_WINDOW_S,
    C2Config,
    C2Geometry,
    LiftedReapproachSettings,
)
from outrigger_sim.params import load_params

PERIOD_S = 0.1
DEFERRED_RR = "leg_reapproach_deferred:RR:retrigger"
PERIODS_PAST_THE_WINDOW = round(R8_D1_REAPPROACH_RETRIGGER_WINDOW_S / PERIOD_S) + 1


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def k1_bench(geometry: C2Geometry, retrigger_samples: int = 2):
    return recorder_ready_bench(geometry, rule_config(retrigger_samples=retrigger_samples))


def test_off_by_default_and_in_the_preset() -> None:
    assert LiftedReapproachSettings().retrigger_samples == 1
    assert C2Config().with_10hz_d1().r8.lifted_reapproach.retrigger_samples == 1


def test_preset_keyword_touches_only_the_sample_count() -> None:
    preset = C2Config().with_10hz_d1()
    switched_on = C2Config().with_10hz_d1(reapproach_retrigger_two_samples=True)
    reapproach = switched_on.r8.lifted_reapproach
    assert reapproach.retrigger_samples == 2
    assert reapproach.retrigger_window_s == R8_D1_REAPPROACH_RETRIGGER_WINDOW_S
    restored = replace(reapproach, retrigger_samples=1)
    assert replace(switched_on, r8=replace(switched_on.r8, lifted_reapproach=restored)) == preset


def test_bad_sample_count_is_refused() -> None:
    with pytest.raises(ValueError):
        LiftedReapproachSettings(retrigger_samples=0)


def test_first_start_keeps_its_one_sample(geometry) -> None:
    bench = k1_bench(geometry)
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    assert names(bench.controller) == ["leg_reapproach_start:RR"]


def test_retrigger_inside_the_window_waits_for_the_second_sample(geometry) -> None:
    bench = k1_bench(geometry)
    start_and_end_rr(bench)
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    assert names(bench.controller)[-1] == DEFERRED_RR
    assert RR not in bench.controller._state.active_reapproaches
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_start:RR"
    assert RR in bench.controller._state.active_reapproaches


def test_off_retrigger_starts_on_one_sample(geometry) -> None:
    bench = k1_bench(geometry, retrigger_samples=1)
    start_and_end_rr(bench)
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_start:RR"


def test_start_outside_the_window_takes_one_sample(geometry) -> None:
    bench = k1_bench(geometry)
    start_and_end_rr(bench)
    step_quiet(bench, PERIODS_PAST_THE_WINDOW)
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_start:RR"
    assert DEFERRED_RR not in names(bench.controller)


def test_one_low_sample_alone_starts_nothing_and_each_stretch_reports_once(geometry) -> None:
    bench = k1_bench(geometry)
    start_and_end_rr(bench)
    for _ in range(2):
        bench.step(lifted_rr_forces(LIFTED_READING_N))
        step_quiet(bench, 1)
    assert RR not in bench.controller._state.active_reapproaches
    assert names(bench.controller).count(DEFERRED_RR) == 2


def test_samples_during_another_legs_reapproach_do_not_count(geometry) -> None:
    """FL reads low through the whole RR run (the single-leg rule resets its count), so at the RR
    end it has its first counted sample: deferred once, started on the next."""
    bench = k1_bench(geometry)
    exit_level_N = geometry.F_min_N + 5e3
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    assert names(bench.controller) == ["leg_reapproach_start:RR"]
    for _ in range(EXIT_SAMPLES):
        bench.step(with_leg(lifted_rr_forces(exit_level_N), FL, LIFTED_READING_N))
    assert names(bench.controller) == [
        "leg_reapproach_start:RR",
        "leg_reapproach_contact:RR",
        "leg_reapproach_deferred:FL:retrigger",
    ]
    assert bench.controller._state.reapproach_low_counts[FL] == 1
    bench.step(with_leg(lifted_rr_forces(exit_level_N), FL, LIFTED_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_start:FL"


def test_other_diagonal_strong_samples_start_on_the_second(geometry) -> None:
    bench = k1_bench(geometry)
    start_and_end_rr(bench)
    settled = rr_settled_forces(geometry)
    bench.step(with_leg(settled, FR, LIFTED_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_deferred:FR:retrigger"
    bench.step(with_leg(settled, FR, LIFTED_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_start:FR"


def test_other_diagonal_weak_samples_stay_on_the_rt1_rule_after_the_second(geometry) -> None:
    bench = k1_bench(geometry)
    start_and_end_rr(bench)
    settled = rr_settled_forces(geometry)
    for _ in range(3):
        bench.step(with_leg(settled, FR, OPPOSITE_LOW_READING_N))
    assert FR not in bench.controller._state.active_reapproaches
    deferred = [name for name in names(bench.controller) if "deferred" in name]
    assert deferred == ["leg_reapproach_deferred:FR:retrigger"]


def test_rt1_alone_keeps_its_plain_event(geometry) -> None:
    bench = k1_bench(geometry, retrigger_samples=1)
    start_and_end_rr(bench)
    bench.step(with_leg(rr_settled_forces(geometry), FR, OPPOSITE_LOW_READING_N))
    assert names(bench.controller)[-1] == "leg_reapproach_deferred:FR"
