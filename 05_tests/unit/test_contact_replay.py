"""Offline J_P / J_C replay (P-S8-1, spec rev. 39 203.2): rules and recorded-run equivalence."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.contact_episode import (
    LEG_NAMES,
    NO_LEG,
    MachineConstants,
    build_episode,
    read_controller_events,
)
from outrigger_sim.control.c2 import C2Config, C2Geometry, LiftedReapproachSettings
from outrigger_sim.control.contact_replay import (
    ActionKind,
    Judge,
    ReplayInput,
    ReplaySettings,
    WatchMode,
    replay_both,
    replay_judge,
    replay_meta_from_config,
)

F_MIN_N = 9414.59
HIGH_LOAD_N = 60e3
RESULTS = Path(__file__).resolve().parents[2] / "07_results" / "S6"
RERUN34 = RESULTS / "bundleC_rerun34_L1R_20261024_141040"
RERUN33 = RESULTS / "bundleC_rerun33_L1R_20261024_125604"
RECORDED_CASES = [
    RERUN34 / "C1_G4_combined_ph0.075",
    RERUN34 / "C1_RE1bF_top_flat_dropRR30",
    RERUN34 / "C1_RE1bP_top_flat_dropRR30_probe",
    RERUN34 / "C1_RE1b_top_flat_settleRR30",
    RERUN34 / "C1_D8_top_rpB_b0.69",
    RERUN33 / "C1_RE1bF_top_flat_dropRR30",
    RERUN33 / "C1_RE1bP_top_flat_dropRR30_probe",
]
CONTROLLER_EVENT_KINDS = {
    "relevel_predicted": ActionKind.R5.value,
    "leg_reapproach_start": ActionKind.REAPPROACH_START.value,
    "leg_reapproach_contact": ActionKind.REAPPROACH_CONTACT.value,
    "WARN_LEG_REAPPROACH_NO_CONTACT": ActionKind.REAPPROACH_NO_CONTACT.value,
}


def r8_settings(**changes) -> ReplaySettings:
    settings = ReplaySettings.from_config(C2Config().with_10hz_d1(), F_MIN_N)
    return ReplaySettings(**{**settings.__dict__, **changes})


def ready_input(loads_N: np.ndarray, *, band_N: float = 0.0, phase: str = "ready",
                probed_leg: int = NO_LEG, motor_stroke_m: np.ndarray | None = None) -> ReplayInput:
    """A lifted, touched record in one phase with the given lower readings (n, 4)."""
    loads_N = np.asarray(loads_N, dtype=float)
    count = loads_N.shape[0]
    marks = np.zeros((count, 4), dtype=bool)
    return ReplayInput(
        t_s=(np.arange(count) + 1) * 0.1,
        watch_phase=np.full(count, phase),
        lower_reading_N=loads_N,
        seal_band_N=np.full((count, 4), band_N),
        motor_stroke_m=np.zeros((count, 4)) if motor_stroke_m is None else motor_stroke_m,
        is_lifted=np.ones(count, dtype=bool),
        touched=np.ones((count, 4), dtype=bool),
        probed_leg=np.full(count, probed_leg),
        ge2_lift_mark=marks.copy(),
        ge2_trigger_mark=marks.copy(),
        probe_not_grounded_mark=marks.copy(),
    )


def constant_loads(count: int, rr_N: float) -> np.ndarray:
    loads = np.full((count, 4), HIGH_LOAD_N)
    loads[:, 3] = rr_N
    return loads


def kinds(replay) -> list[tuple[int, str]]:
    return [(event.leg, event.kind.value) for event in replay.events]


def test_settings_from_meta_match_the_config():
    config = C2Config().with_10hz_d1()
    from_config = ReplaySettings.from_config(config, F_MIN_N)
    from_meta = ReplaySettings.from_controller_meta(replay_meta_from_config(config), F_MIN_N)
    assert from_meta == from_config


def test_meta_without_mode_is_the_revision_33_leg_mode():
    meta = replay_meta_from_config(C2Config().with_10hz_d1())
    meta["r8"]["lifted_reapproach"] = {"enable": True, "load_fraction_of_F_min": 0.5,
                                       "samples": None, "speed_fraction": 0.25,
                                       "max_travel_m": 0.04}
    settings = ReplaySettings.from_controller_meta(meta, F_MIN_N)
    assert settings.reapproach == LiftedReapproachSettings.leg_mode()


def test_p5_needs_the_confirmation_count():
    level = F_MIN_N + 7500.0
    settings = r8_settings(fast_relevel=None, relevel_samples=2)
    one_low = constant_loads(4, HIGH_LOAD_N)
    one_low[1, 3] = level - 100.0
    assert replay_judge(ready_input(one_low), settings, Judge.PRESSURE).events == []
    two_low = one_low.copy()
    two_low[2, 3] = level - 100.0
    replay = replay_judge(ready_input(two_low), settings, Judge.PRESSURE)
    assert kinds(replay) == [(3, ActionKind.P5.value)]
    assert replay.action_flags[2, 3] and replay.action_flags.sum() == 1


def test_band_moves_the_combined_judge_below_the_pressure_judge():
    settings = r8_settings(fast_relevel=None)
    loads = constant_loads(3, F_MIN_N + 3000.0)
    inputs = ready_input(loads, band_N=5000.0)
    pressure = replay_judge(inputs, settings, Judge.PRESSURE)
    combined = replay_judge(inputs, settings, Judge.COMBINED)
    assert not pressure.decision_flags[:, 3].any()
    assert combined.decision_flags[:, 3].all()
    np.testing.assert_allclose(combined.load_estimate_N, pressure.load_estimate_N - 5000.0)


def test_r5_predicts_a_fast_fall_and_skips_the_probed_leg():
    settings = r8_settings(relevel_samples=50)  # keep P5 out of the way
    falling = np.linspace(40e3, 22e3, 6)  # 3.6 kN per period = 36 kN/s
    loads = constant_loads(6, 0.0)
    loads[:, 3] = falling
    replay = replay_judge(ready_input(loads), settings, Judge.PRESSURE)
    assert kinds(replay)[0] == (3, ActionKind.R5.value)
    assert replay.events[0].t_s == pytest.approx(0.4)  # history of 4 samples, horizon 4
    probing = ready_input(loads, phase="probe", probed_leg=3)
    assert replay_judge(probing, settings, Judge.PRESSURE).events == []


def test_reapproach_starts_ends_on_contact_and_disarms_after_no_contact():
    settings = r8_settings(fast_relevel=None, relevel_samples=50)
    lifted, contact = 1000.0, F_MIN_N + 6000.0
    loads = constant_loads(8, lifted)
    loads[4:, 3] = contact
    replay = replay_judge(ready_input(loads), settings, Judge.PRESSURE)
    assert kinds(replay) == [(3, "leg_reapproach_start"), (3, "leg_reapproach_contact")]
    assert replay.events[1].t_s == pytest.approx(0.7)  # three samples at the exit level

    stroke = np.zeros((8, 4))
    stroke[:, 3] = np.linspace(0.0, 0.07, 8)  # 10 mm per period, limit 40 mm
    stuck = ready_input(constant_loads(8, lifted), motor_stroke_m=stroke)
    events = kinds(replay_judge(stuck, settings, Judge.PRESSURE))
    assert events == [(3, "leg_reapproach_start"), (3, "leg_reapproach_no_contact")]


def test_controller_watch_follows_the_phase_and_continuous_does_not():
    settings = r8_settings(fast_relevel=None)
    # Below the P5 level F_min + 7.5 kN, above the re-approach start 1.4 F_min (P-S8-5), which
    # also watches DONE.
    loads = constant_loads(5, F_MIN_N + 5000.0)
    inputs = ready_input(loads, phase="done")
    assert replay_judge(inputs, settings, Judge.PRESSURE).events == []
    continuous = replay_judge(inputs, settings, Judge.PRESSURE, watch=WatchMode.CONTINUOUS)
    assert (3, ActionKind.P5.value) in kinds(continuous)


def test_combined_marks_reach_the_flags():
    settings = r8_settings(fast_relevel=None)
    inputs = ready_input(constant_loads(4, HIGH_LOAD_N))
    inputs.ge2_lift_mark[1, 2] = True
    inputs.ge2_trigger_mark[2, 2] = True
    pressure = replay_judge(inputs, settings, Judge.PRESSURE)
    combined = replay_judge(inputs, settings, Judge.COMBINED)
    assert not pressure.decision_flags.any() and not pressure.action_flags.any()
    assert combined.decision_flags[1, 2] and combined.action_flags[2, 2]
    assert kinds(combined) == [(2, ActionKind.GE2.value)]


@pytest.fixture(scope="module")
def machine() -> MachineConstants:
    from outrigger_sim.params import load_params

    return MachineConstants.from_geometry(C2Geometry.from_params(load_params(level="top")))


@pytest.mark.parametrize("case_dir", RECORDED_CASES, ids=lambda p: f"{p.parent.name[:16]}/{p.name}")
def test_replayed_events_equal_the_controller_events(case_dir, machine):
    """Spec 209.2 P-S8-1 test: replay of J_C on a bundle-C record = the controller's events."""
    if not (case_dir / "record" / "record.npz").is_file():
        pytest.skip(f"record not present: {case_dir}")
    expected = []
    for time_s, name in read_controller_events(case_dir / "controller_events.json"):
        kind, _, leg = name.partition(":")
        if kind in CONTROLLER_EVENT_KINDS:
            expected.append((round(time_s, 6), LEG_NAMES.index(leg), CONTROLLER_EVENT_KINDS[kind]))
    replay = replay_both(build_episode(case_dir, machine))[Judge.COMBINED]
    replayed = [event for event in replay.event_tuples() if event[2] in
                set(CONTROLLER_EVENT_KINDS.values())]
    assert sorted(replayed) == sorted(expected)
