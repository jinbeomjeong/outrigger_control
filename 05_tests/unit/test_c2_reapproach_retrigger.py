"""Re-approach re-trigger rule RT (P-S8-16, ``s6_control_spec.md`` rev. 52 228.3 / 229, U-S8-49).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` (twist-mode preset, pressure judge):

* T2 a single re-approach is bit-identical with and without the rule,
* T3 an other-diagonal start inside 0.8 s waits for two samples below 0 N (one deferral event),
* T4 a same-diagonal start inside 2 s starts at once and runs at 0.6 of the speed,
* T5 a start 2.1 s after the end is a first run again,
* T6 a controller unpickled from code without the new keys reads them as "off",
* T7 the offline replay (``contact_replay``) gives the controller's start and deferral times.

T1 (class defaults bit-identical) is the rest of the unit suite and the closed-loop hash of
``c2py_r8d1_closed_loop.py``; T8 is the acceptance run of ``r51_reapp_closed_loop.py``.
"""

from __future__ import annotations

import pickle
from dataclasses import fields, replace

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    FL,
    PERIOD_S,
    READY_SETTLE_PERIODS,
    RR,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    lifted_rr_forces,
    operating_strokes,
    ready_bench,
)

from outrigger_sim.control.c2 import (
    R8_D1_SETTINGS,
    REAPPROACH_DEFERRED_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    LiftedReapproachSettings,
    _Reapproach,
    _RunState,
)
from outrigger_sim.control.contact_replay import (
    DIAGONAL_SIGNS,
    ActionKind,
    Judge,
    ReplayInput,
    ReplaySettings,
    WatchMode,
    replay_judge,
)
from outrigger_sim.params import LEG_ORDER, load_params

FR = LEG_ORDER.index("FR")
LIFTED_READING_N = -1e3
OPPOSITE_LOW_READING_N = 5e3
"""T3: below 1.4 F_min (13.2 kN) but not below the 0 N strong level."""
EXIT_SAMPLES = 3
RT_KEYS = (
    "retrigger_window_s",
    "retrigger_speed_factor",
    "opposite_window_s",
    "opposite_strong_level_N",
    "opposite_strong_samples",
)
RT_OFF = {
    "retrigger_window_s": None,
    "retrigger_speed_factor": 1.0,
    "opposite_window_s": None,
}
RUN_STATE_KEYS = ("reapproach_last_end_s", "reapproach_last_sign", "reapproach_strong_counts")


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


class ReapproachRecorder(C2Controller):
    """C2 that logs what the re-approach bookkeeping saw in each period (replay input)."""

    def __init__(self, geometry: C2Geometry, config: C2Config) -> None:
        super().__init__(geometry, config)
        self.rows: list[dict] = []

    def _update_lifted_reapproach(self, reading) -> None:
        state = self._state
        probed = self._probed_leg()
        self.rows.append(
            {
                "t_s": reading.t_s,
                "phase": str(state.phase),
                "is_lifted": state.is_lifted,
                "touched": state.touched.copy(),
                "probed_leg": -1 if probed is None else probed,
                "lower_N": np.array(reading.cylinder_force_lower_N, dtype=float),
                "motor_stroke_m": np.array(reading.motor_stroke_m, dtype=float),
            }
        )
        super()._update_lifted_reapproach(reading)


def rule_config(**reapproach_changes) -> C2Config:
    config = bench_config()
    reapproach = replace(config.r8.lifted_reapproach, **reapproach_changes)
    return replace(config, r8=replace(config.r8, lifted_reapproach=reapproach))


def recorder_ready_bench(geometry: C2Geometry, config: C2Config) -> Bench:
    """``ready_bench`` (level crawler) driving a :class:`ReapproachRecorder`."""
    bench = Bench(ReapproachRecorder(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    bench.run_while(C2Phase.LEVEL)
    bench.run_while(C2Phase.DONE)
    assert bench.controller.phase is C2Phase.READY
    for _ in range(READY_SETTLE_PERIODS):
        bench.step()
    return bench


def names(controller: C2Controller) -> list[str]:
    return [
        event.name
        for event in controller.events
        if event.name.startswith(("leg_reapproach_", "WARN_LEG_REAPPROACH_"))
    ]


def start_and_end_rr(bench: Bench) -> float:
    """RR lifts (first run, starts on one sample) and ends on three samples at the exit
    level; returns the end time ``t_e``."""
    bench.step(lifted_rr_forces(LIFTED_READING_N))
    exit_level_N = bench.geometry.F_min_N + 5e3
    for _ in range(EXIT_SAMPLES):
        bench.step(lifted_rr_forces(exit_level_N))
    assert names(bench.controller) == ["leg_reapproach_start:RR", "leg_reapproach_contact:RR"]
    return bench.t_s


def rr_settled_forces(geometry: C2Geometry) -> np.ndarray:
    """RR back on the floor at the exit level, the others steady."""
    return lifted_rr_forces(geometry.F_min_N + 5e3)


def step_quiet(bench: Bench, count: int) -> None:
    for _ in range(count):
        bench.step(rr_settled_forces(bench.geometry))


def with_leg(forces: np.ndarray, leg: int, reading_N: float) -> np.ndarray:
    changed = forces.copy()
    changed[leg] = reading_N
    return changed


def expected_twist_rate(geometry: C2Geometry, leg: int, factor: float) -> float:
    twist = geometry.twist_vector
    rate = np.sign(twist[leg]) * 0.25 * geometry.max_speed_m_s / float(np.max(np.abs(twist)))
    return float(rate) * factor


# --- settings ---------------------------------------------------------------------------------


def test_class_defaults_turn_the_rule_off() -> None:
    settings = LiftedReapproachSettings()
    assert (settings.retrigger_window_s, settings.retrigger_speed_factor) == (None, 1.0)
    assert settings.opposite_window_s is None
    assert (settings.opposite_strong_level_N, settings.opposite_strong_samples) == (0.0, 2)
    assert not settings.is_retrigger(1.0, 0.9)
    assert not settings.needs_strong_confirmation(1.0, 0.9, 1.0, -1.0)


def test_preset_turns_the_rule_on() -> None:
    preset = R8_D1_SETTINGS.lifted_reapproach
    assert tuple(getattr(preset, key) for key in RT_KEYS) == (2.0, 0.6, 0.8, 0.0, 2)


@pytest.mark.parametrize(
    "changes",
    [
        {"retrigger_window_s": 0.0},
        {"opposite_window_s": -0.1},
        {"retrigger_speed_factor": 0.0},
        {"retrigger_speed_factor": 1.2},
        {"opposite_strong_samples": 0},
        {"opposite_strong_samples": True},
        {"opposite_strong_samples": 2.0},
    ],
)
def test_invalid_rule_values_are_rejected(changes) -> None:
    with pytest.raises(ValueError):
        LiftedReapproachSettings(**changes)


def test_windows_end_exactly_one_window_after_the_end() -> None:
    preset = R8_D1_SETTINGS.lifted_reapproach
    assert preset.is_retrigger(3.9, 2.0)
    assert not preset.is_retrigger(round(2.0 + 2.0, 10), 2.0)
    assert preset.needs_strong_confirmation(2.7, 2.0, 1.0, -1.0)
    assert not preset.needs_strong_confirmation(2.8, 2.0, 1.0, -1.0)
    assert not preset.needs_strong_confirmation(2.3, 2.0, 1.0, 1.0)  # same diagonal


def test_replay_diagonal_signs_match_the_twist_vector(geometry) -> None:
    signs = np.sign(geometry.twist_vector)
    assert np.array_equal(signs, DIAGONAL_SIGNS) or np.array_equal(-signs, DIAGONAL_SIGNS)


# --- T2: one re-approach is unchanged --------------------------------------------------------


def test_t2_single_reapproach_is_bit_identical(geometry) -> None:
    """A G4-type single re-approach (RR lifts, re-approaches, touches) and then quiet: the
    commands with the rule equal those without it to the last bit."""
    outputs = {}
    for name, changes in (("rule", {}), ("off", RT_OFF)):
        bench = ready_bench(geometry, rule_config(**changes))
        start_and_end_rr(bench)
        step_quiet(bench, 30)
        outputs[name] = np.array(bench.outputs)
        (interval,) = bench.controller.meta()["lifted_reapproach"]
        assert interval["is_retrigger"] is False
    np.testing.assert_array_equal(outputs["rule"], outputs["off"])


# --- T3: other diagonal inside 0.8 s ----------------------------------------------------------


def t3_bench(geometry: C2Geometry) -> tuple[Bench, float]:
    """RR run ends at ``t_e``; FR reads 5 kN at ``t_e + 0.3`` and ``+ 0.4`` s, then -1 kN at
    ``+ 0.5`` and ``+ 0.6`` s."""
    bench = ready_bench(geometry, bench_config())
    end_s = start_and_end_rr(bench)
    step_quiet(bench, 2)
    settled = rr_settled_forces(geometry)
    for reading in (OPPOSITE_LOW_READING_N, OPPOSITE_LOW_READING_N, LIFTED_READING_N):
        bench.step(with_leg(settled, FR, reading))
    return bench, end_s


def test_t3_other_diagonal_waits_for_two_samples_below_zero(geometry) -> None:
    bench, end_s = t3_bench(geometry)
    controller = bench.controller
    assert names(controller) == [
        "leg_reapproach_start:RR",
        "leg_reapproach_contact:RR",
        f"{REAPPROACH_DEFERRED_EVENT}:FR",
    ]
    deferred = [
        event for event in controller.events if event.name == f"{REAPPROACH_DEFERRED_EVENT}:FR"
    ]
    assert deferred[0].t_s == pytest.approx(end_s + 0.3)
    assert not controller._state.active_reapproaches
    bench.step(with_leg(rr_settled_forces(geometry), FR, LIFTED_READING_N))
    assert names(controller)[-1] == "leg_reapproach_start:FR"
    assert bench.t_s == pytest.approx(end_s + 0.6)
    assert controller._state.active_reapproaches[FR].is_retrigger


def test_t3_deferral_keeps_the_guard_path(geometry) -> None:
    """While FR is deferred no re-approach is active, so the twist and guard terms act."""
    bench, _ = t3_bench(geometry)
    components = bench.controller.command_components_m_s
    np.testing.assert_array_equal(components["reapproach"], 0.0)
    assert np.any(components["guard"] != 0.0)


# --- T4 / T5: re-trigger speed ----------------------------------------------------------------


def test_t4_same_diagonal_restart_is_slowed(geometry) -> None:
    bench = ready_bench(geometry, bench_config())
    end_s = start_and_end_rr(bench)
    step_quiet(bench, 2)
    bench.step(with_leg(rr_settled_forces(geometry), FL, LIFTED_READING_N))
    controller = bench.controller
    assert names(controller)[-1] == "leg_reapproach_start:FL"
    assert bench.t_s == pytest.approx(end_s + 0.3)
    run = controller._state.active_reapproaches[FL]
    assert run.is_retrigger
    components = controller.command_components_m_s
    expected = geometry.twist_vector * expected_twist_rate(geometry, FL, 0.6)
    np.testing.assert_allclose(components["reapproach"], expected, rtol=1e-12, atol=0.0)
    assert np.max(np.abs(components["reapproach"])) == pytest.approx(
        0.6 * 0.25 * geometry.max_speed_m_s, rel=1e-12
    )
    assert controller.meta()["lifted_reapproach"][-1]["is_retrigger"] is True


def test_t5_start_after_the_window_is_a_first_run(geometry) -> None:
    bench = ready_bench(geometry, bench_config())
    end_s = start_and_end_rr(bench)
    step_quiet(bench, 20)
    bench.step(with_leg(rr_settled_forces(geometry), FL, LIFTED_READING_N))
    controller = bench.controller
    assert bench.t_s == pytest.approx(end_s + 2.1)
    assert names(controller)[-1] == "leg_reapproach_start:FL"
    assert not controller._state.active_reapproaches[FL].is_retrigger
    expected = geometry.twist_vector * expected_twist_rate(geometry, FL, 1.0)
    np.testing.assert_allclose(
        controller.command_components_m_s["reapproach"], expected, rtol=1e-12, atol=0.0
    )


def test_leg_mode_retrigger_scales_the_leg_speed(geometry) -> None:
    """Leg mode (P-R8-12): ``speed_fraction`` times the factor on a re-trigger run."""
    leg_mode = replace(
        LiftedReapproachSettings.leg_mode(),
        samples=1,
        exit_samples=EXIT_SAMPLES,
        exit_margin_N=5e3,
        **{key: getattr(R8_D1_SETTINGS.lifted_reapproach, key) for key in RT_KEYS},
    )
    config = bench_config(lifted_reapproach=leg_mode)
    bench = ready_bench(geometry, config)
    start_and_end_rr(bench)
    step_quiet(bench, 2)
    bench.step(with_leg(rr_settled_forces(geometry), FL, LIFTED_READING_N))
    commanded = bench.controller._state.previous_output_m_s
    assert commanded[FL] == pytest.approx(0.25 * 0.6 * geometry.max_speed_m_s, rel=1e-12)


# --- T6: old pickles --------------------------------------------------------------------------


def aged(controller: C2Controller) -> C2Controller:
    """``controller`` as unpickled from code without the P-S8-16 keys: the new instance
    attributes of the settings, the run state and the re-approach runs are missing."""
    copied = pickle.loads(pickle.dumps(controller))
    old_settings = object.__new__(LiftedReapproachSettings)
    current = copied.config.r8.lifted_reapproach
    old_settings.__dict__.update(
        {
            item.name: getattr(current, item.name)
            for item in fields(current)
            if item.name not in RT_KEYS
        }
    )
    r8 = replace(copied.config.r8, lifted_reapproach=old_settings)
    copied.config = replace(copied.config, r8=r8)
    for key in RUN_STATE_KEYS:
        copied._state.__dict__.pop(key)
    for run in copied._state.reapproach_history:
        run.__dict__.pop("is_retrigger")
    return pickle.loads(pickle.dumps(copied))


def test_t6_old_pickle_reads_class_defaults_and_behaves_as_before(geometry) -> None:
    """The run state and the settings of an old pickle lack the new keys: they read the class
    defaults (rule off), and the controller then acts as one with the rule off."""
    reference = ready_bench(geometry, rule_config(**RT_OFF))
    start_and_end_rr(reference)
    restored_bench = Bench(aged(reference.controller), geometry, reference.strokes_m.copy())
    restored_bench.t_s = reference.t_s
    restored = restored_bench.controller
    settings = restored.config.r8.lifted_reapproach
    for key in RT_KEYS:
        assert key not in settings.__dict__
        assert getattr(settings, key) == getattr(LiftedReapproachSettings, key)
    for key in RUN_STATE_KEYS:
        assert key not in restored._state.__dict__
    assert restored._state.reapproach_last_end_s is None
    assert restored._state.reapproach_strong_counts == _RunState.reapproach_strong_counts
    assert restored._state.reapproach_history[0].is_retrigger is _Reapproach.is_retrigger
    settled = rr_settled_forces(geometry)
    sequence = [
        settled,
        settled,
        with_leg(settled, FR, OPPOSITE_LOW_READING_N),
        with_leg(settled, FR, OPPOSITE_LOW_READING_N),
        settled,
        settled,
    ]
    for forces in sequence:
        reference.step(forces)
        restored_bench.step(forces)
    np.testing.assert_array_equal(
        np.array(reference.outputs[-len(sequence) :]), np.array(restored_bench.outputs)
    )
    assert names(restored) == names(reference.controller)
    assert restored.meta()["lifted_reapproach"] == reference.controller.meta()["lifted_reapproach"]


def test_t6_old_run_state_takes_the_refreshed_preset(geometry) -> None:
    """The branch refresh replaces the settings only: an old run state under the preset rule
    counts its windows from the next end (no AttributeError, class defaults until then)."""
    reference = ready_bench(geometry, rule_config(**RT_OFF))
    start_and_end_rr(reference)
    bench = Bench(aged(reference.controller), geometry, reference.strokes_m.copy())
    bench.t_s = reference.t_s
    bench.controller.config = rule_config()
    settled = rr_settled_forces(geometry)
    bench.step(with_leg(settled, FR, OPPOSITE_LOW_READING_N))
    run = bench.controller._state.active_reapproaches[FR]
    assert not run.is_retrigger  # the old state had no end time
    for _ in range(EXIT_SAMPLES):
        bench.step(with_leg(settled, FR, geometry.F_min_N + 5e3))
    end_s = bench.t_s
    assert bench.controller._state.reapproach_last_end_s == end_s
    bench.step(with_leg(with_leg(settled, FR, geometry.F_min_N + 5e3), RR, OPPOSITE_LOW_READING_N))
    assert names(bench.controller)[-1] == f"{REAPPROACH_DEFERRED_EVENT}:RR"


# --- T7: replay = controller ------------------------------------------------------------------


def recorded_input(rows: list[dict]) -> ReplayInput:
    count = len(rows)
    marks = np.zeros((count, 4), dtype=bool)
    return ReplayInput(
        t_s=np.array([row["t_s"] for row in rows]),
        watch_phase=np.array([row["phase"] for row in rows]),
        lower_reading_N=np.array([row["lower_N"] for row in rows]),
        seal_band_N=np.zeros((count, 4)),
        motor_stroke_m=np.array([row["motor_stroke_m"] for row in rows]),
        is_lifted=np.array([row["is_lifted"] for row in rows]),
        touched=np.array([row["touched"] for row in rows]),
        probed_leg=np.array([row["probed_leg"] for row in rows], dtype=np.int64),
        ge2_lift_mark=marks.copy(),
        ge2_trigger_mark=marks.copy(),
        probe_not_grounded_mark=marks.copy(),
    )


CONTROLLER_KINDS = {
    "leg_reapproach_start": ActionKind.REAPPROACH_START,
    "leg_reapproach_contact": ActionKind.REAPPROACH_CONTACT,
    REAPPROACH_DEFERRED_EVENT: ActionKind.REAPPROACH_DEFERRED,
}


def controller_tuples(controller: C2Controller) -> list[tuple]:
    out = []
    for event in controller.events:
        prefix, _, leg_name = event.name.partition(":")
        if prefix in CONTROLLER_KINDS:
            out.append(
                (round(event.t_s, 6), LEG_ORDER.index(leg_name), CONTROLLER_KINDS[prefix].value)
            )
    return sorted(out, key=lambda item: (item[0], item[1]))


@pytest.mark.parametrize("scenario", ["T3", "T4"])
def test_t7_replay_gives_the_controller_start_and_deferral_times(geometry, scenario) -> None:
    config = bench_config()
    bench = recorder_ready_bench(geometry, config)
    controller = bench.controller
    start_and_end_rr(bench)
    step_quiet(bench, 2)
    settled = rr_settled_forces(geometry)
    if scenario == "T3":
        readings = [
            OPPOSITE_LOW_READING_N,
            OPPOSITE_LOW_READING_N,
            LIFTED_READING_N,
            LIFTED_READING_N,
        ]
        sequence = [with_leg(settled, FR, reading) for reading in readings]
    else:
        sequence = [with_leg(settled, FL, LIFTED_READING_N)]
    for forces in sequence + [settled] * 5:
        bench.step(forces)
    settings = ReplaySettings.from_config(config, geometry.F_min_N)
    replay = replay_judge(
        recorded_input(controller.rows), settings, Judge.PRESSURE, watch=WatchMode.CONTROLLER
    )
    kinds = frozenset(CONTROLLER_KINDS.values())
    assert replay.event_tuples(kinds) == controller_tuples(controller)
    assert any(
        kind == ActionKind.REAPPROACH_DEFERRED.value for _, _, kind in replay.event_tuples(kinds)
    ) is (scenario == "T3")


def test_replay_old_meta_without_rule_keys_is_off() -> None:
    settings = ReplaySettings.from_controller_meta(
        {
            "period_s": PERIOD_S,
            "thresholds": {"relevel_load_margin_N": 7500.0},
            "r8": {
                "confirmation": {"relevel_samples": 2},
                "output_delay_periods": 1,
                "lifted_reapproach": {"enable": True, "mode": "twist"},
            },
        },
        9414.59,
    )
    assert settings.reapproach.opposite_window_s is None
    assert settings.reapproach.retrigger_window_s is None
