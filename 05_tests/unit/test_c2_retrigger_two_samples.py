"""K1: a re-trigger start needs two low samples in a row (TOUCH phase study, 2026-11-04).

Synthetic 10 Hz benches of ``test_c2_reapproach_retrigger.py``. The first start after an event
keeps its one sample, so the response to a real sink does not get later.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from test_c2_r8d1 import FL, RR, lifted_rr_forces  # same test folder
from test_c2_reapproach_retrigger import (
    EXIT_SAMPLES,
    FR,
    LIFTED_READING_N,
    OPPOSITE_LOW_READING_N,
    names,
    recorded_input,
    recorder_ready_bench,
    rr_settled_forces,
    rule_config,
    start_and_end_rr,
    step_quiet,
    with_leg,
)

from outrigger_sim.contact_episode import (
    EVENTS_FILE,
    MachineConstants,
    build_episode,
    read_controller_events,
)
from outrigger_sim.control.c2 import (
    R8_D1_REAPPROACH_RETRIGGER_WINDOW_S,
    C2Config,
    C2Geometry,
    LiftedReapproachSettings,
)
from outrigger_sim.control.contact_replay import (
    ActionKind,
    Judge,
    ReplaySettings,
    WatchMode,
    replay_both,
    replay_judge,
    replay_meta_from_config,
)
from outrigger_sim.params import LEG_ORDER, load_params

PERIOD_S = 0.1
DEFERRED_RR = "leg_reapproach_deferred:RR:retrigger"
PERIODS_PAST_THE_WINDOW = round(R8_D1_REAPPROACH_RETRIGGER_WINDOW_S / PERIOD_S) + 1
REPLAYED_KINDS = frozenset(
    {ActionKind.REAPPROACH_START, ActionKind.REAPPROACH_DEFERRED, ActionKind.REAPPROACH_CONTACT}
)
REPLAYED_EVENT_PREFIXES = frozenset(kind.value for kind in REPLAYED_KINDS)
STORED_RESULTS_DIR = Path(r"C:\workspace\outrigger_control\07_results\S8")
"""Chrono runs of commit 74032be, kept in the main tree only (results are not in git)."""
STORED_K1_RUNS = (
    "c4g2_R16_mirror2_d000_C4G2K1_20261104_222344",
    "c4g2_R16_mirror2_d070_C4G2K1_20261104_222344",
    "c4g2_R15_C4G2K1_20261104_222344",
    "c4g2_R12_C4G2K1_20261104_222344",
    "c4g2_R9_mirror2_d035_Fs4_C4G2K1_20261104_222344",
)
STORED_K1_OFF_RUNS = (
    "c4g2_R16_mirror2_d000_C4G2_20261104_222344",
    "c4g2_R9_mirror2_d035_Fs4_off_20261104_222344",
)


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


# --- the offline replay knows K1 ------------------------------------------------------------------


def controller_reapproach_events(events: list[tuple[float, str]]) -> list[tuple[float, int, str]]:
    """(t_s, leg, kind) of the controller events the replay gives; the K1 reason is not kept."""
    found = []
    for time_s, name in events:
        parts = name.split(":")
        if parts[0] in REPLAYED_EVENT_PREFIXES:
            found.append((round(time_s, 3), LEG_ORDER.index(parts[1]), parts[0]))
    return sorted(found)


def replayed_events(replay) -> list[tuple[float, int, str]]:
    return sorted((round(t, 3), leg, kind) for t, leg, kind in replay.event_tuples(REPLAYED_KINDS))


def rr_retrigger_run(geometry: C2Geometry, retrigger_samples: int):
    """RR ends, then a one-sample dip, then two low samples, on a recording bench."""
    config = rule_config(retrigger_samples=retrigger_samples)
    bench = recorder_ready_bench(geometry, config)
    start_and_end_rr(bench)
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    step_quiet(bench, 1)
    for _ in range(2):
        bench.step(lifted_rr_forces(LIFTED_READING_N))
    step_quiet(bench, 5)
    return bench, ReplaySettings.from_config(config, geometry.F_min_N)


@pytest.mark.parametrize("retrigger_samples", [1, 2])
def test_replay_gives_the_controller_events(geometry, retrigger_samples) -> None:
    bench, settings = rr_retrigger_run(geometry, retrigger_samples)
    replay = replay_judge(
        recorded_input(bench.controller.rows), settings, Judge.PRESSURE, watch=WatchMode.CONTROLLER
    )
    events = [(event.t_s, event.name) for event in bench.controller.events]
    assert replayed_events(replay) == controller_reapproach_events(events)


def test_replay_without_the_rule_starts_a_sample_earlier(geometry) -> None:
    bench, settings = rr_retrigger_run(geometry, 2)
    inputs = recorded_input(bench.controller.rows)
    without_rule = replace(
        settings, reapproach=replace(settings.reapproach, retrigger_samples=1)
    )
    with_rule = replay_judge(inputs, settings, Judge.PRESSURE, watch=WatchMode.CONTROLLER)
    off = replay_judge(inputs, without_rule, Judge.PRESSURE, watch=WatchMode.CONTROLLER)
    assert replayed_events(with_rule) != replayed_events(off)


def test_replay_settings_read_the_count_from_the_meta() -> None:
    config = rule_config(retrigger_samples=2)
    meta = replay_meta_from_config(config)
    assert ReplaySettings.from_controller_meta(meta, 9414.59).reapproach.retrigger_samples == 2
    del meta["r8"]["lifted_reapproach"]["retrigger_samples"]
    assert ReplaySettings.from_controller_meta(meta, 9414.59).reapproach.retrigger_samples == 1


def stored_case_dir(run_name: str) -> Path:
    batch = STORED_RESULTS_DIR / run_name
    if not batch.is_dir():
        pytest.skip(f"stored record {run_name} missing")
    return next(path for path in batch.iterdir() if (path / "result.json").exists())


@pytest.mark.parametrize("run_name", STORED_K1_RUNS + STORED_K1_OFF_RUNS)
def test_replay_of_a_stored_run_gives_its_recorded_events(geometry, run_name) -> None:
    case_dir = stored_case_dir(run_name)
    machine = MachineConstants.from_geometry(geometry)
    episode = build_episode(case_dir, machine)
    replay = replay_both(episode, watch=WatchMode.CONTROLLER)[Judge.COMBINED]
    recorded = read_controller_events(case_dir / EVENTS_FILE)
    assert replayed_events(replay) == controller_reapproach_events(recorded)


def test_stored_k1_run_needs_the_rule(geometry) -> None:
    case_dir = stored_case_dir(STORED_K1_RUNS[0])
    episode = build_episode(case_dir, MachineConstants.from_geometry(geometry))
    settings = ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)
    assert settings.reapproach.retrigger_samples == 2
    without_rule = replace(
        settings, reapproach=replace(settings.reapproach, retrigger_samples=1)
    )
    replay = replay_both(episode, without_rule, watch=WatchMode.CONTROLLER)[Judge.COMBINED]
    recorded = read_controller_events(case_dir / EVENTS_FILE)
    assert replayed_events(replay) != controller_reapproach_events(recorded)
