"""P-S8-22 R-5 fallback slope in the offline replay (spec rev. 61 302.2, V-2 premise).

* the replay uses the controller's rule (:func:`~outrigger_sim.control.c2.fallback_slope_drops`)
  on per-update :class:`FallbackSlopeInputs`, and nothing changes with ``level`` or without
  inputs;
* the fallback rows come from the controller's events (D4 / D6: one row later);
* record replay of ``current_dur125`` (``07_results``, git-ignored; skipped without it): the level
  replay gives the controller's two ``relevel_predicted:FL`` (127.8 / 141.5 s), the fallback slope
  gives none, with the 302.5 values.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.contact_episode import MachineConstants, build_episode, read_controller_events
from outrigger_sim.control.c2 import C2Config, C2Geometry
from outrigger_sim.control.contact_replay import (
    ActionKind,
    Judge,
    ReplayInput,
    ReplaySettings,
    fallback_rows_from_events,
    replay_fallback_monitor,
    replay_judge,
)
from outrigger_sim.control.two_pressure import FallbackSlopeInputs
from outrigger_sim.params import load_params

F_MIN_N = 9414.59
HEAD_AREA_M2 = 1.3273229e-2
ANNULUS_M2 = 3.76991118e-3
FL = 0
PERIOD_S = 0.1
CASE = (Path(__file__).resolve().parents[2] / "07_results" / "R3_PS2_fdown_diag_20261026"
        / "current_dur125")


def _settings(**fast_relevel_changes) -> ReplaySettings:
    settings = ReplaySettings.from_config(C2Config().with_10hz_d1(), F_MIN_N)
    return replace(settings, fast_relevel=replace(settings.fast_relevel, **fast_relevel_changes))


def _inputs_with_drop(drop_N: float) -> FallbackSlopeInputs:
    """``D = drop_N`` from the nominal term alone (ratio 1, no reserve)."""
    gain = HEAD_AREA_M2 + ANNULUS_M2
    return FallbackSlopeInputs(drop_N / gain, 0.0, 1.0, 1.0, 1.0, HEAD_AREA_M2, ANNULUS_M2)


def _falling_input(fallback_inputs: FallbackSlopeInputs | None) -> ReplayInput:
    """READY, FL lower estimate 60 -> 30 kN in 3 periods; FL inputs on the last row."""
    loads = np.full((4, 4), 80e3)
    loads[:, FL] = (60e3, 50e3, 40e3, 30e3)
    marks = np.zeros((4, 4), dtype=bool)
    slope_inputs = np.full((4, 4), None, dtype=object)
    slope_inputs[-1, FL] = fallback_inputs
    return ReplayInput(
        t_s=(np.arange(4) + 1) * PERIOD_S, watch_phase=np.full(4, "ready"),
        lower_reading_N=loads, seal_band_N=np.zeros((4, 4)), motor_stroke_m=np.zeros((4, 4)),
        is_lifted=np.ones(4, dtype=bool), touched=np.ones((4, 4), dtype=bool),
        probed_leg=np.full(4, -1), ge2_lift_mark=marks, ge2_trigger_mark=marks,
        probe_not_grounded_mark=marks, fallback_slope_inputs=slope_inputs,
    )


def _r5_events(replay) -> list[tuple]:
    kinds = (ActionKind.R5, ActionKind.R5_FALLBACK_SLOPE)
    return [(event.leg, event.kind, event.values_kN) for event in replay.events
            if event.kind in kinds]


def test_level_rule_ignores_the_inputs() -> None:
    replay = replay_judge(_falling_input(_inputs_with_drop(1e3)), _settings(fallback_slope="level"),
                          Judge.PRESSURE)
    assert _r5_events(replay) == [(FL, ActionKind.R5, None)]


def test_slow_fallback_fall_neither_triggers_nor_reports() -> None:
    replay = replay_judge(_falling_input(_inputs_with_drop(6e3)), _settings(), Judge.PRESSURE)
    assert _r5_events(replay) == []


def test_fast_fallback_fall_reports_over_the_horizon_and_triggers() -> None:
    replay = replay_judge(_falling_input(_inputs_with_drop(12e3)), _settings(), Judge.PRESSURE)
    (report, trigger) = _r5_events(replay)
    assert report[:2] == (FL, ActionKind.R5_FALLBACK_SLOPE)
    assert report[2] == pytest.approx((16.0, 0.0))  # (h / n) D with h 4, n 3
    assert trigger == (FL, ActionKind.R5, None)


def test_no_inputs_is_the_level_rule() -> None:
    replay = replay_judge(_falling_input(None), _settings(), Judge.PRESSURE)
    assert _r5_events(replay) == [(FL, ActionKind.R5, None)]


def test_fallback_rows_follow_the_reason() -> None:
    t_s = (np.arange(10) + 1) * PERIOD_S
    events = [
        (0.3, "WARN_ROD_PRESSURE_FALLBACK:FL"), (0.3, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D2"),
        (0.5, "WARN_ROD_PRESSURE_FALLBACK:RR"), (0.5, "INFO_ROD_PRESSURE_FAULT_REASON:RR:D4"),
    ]
    assert fallback_rows_from_events(events, t_s, PERIOD_S) == (2, None, None, 5)


# --- record replay (V-2 premise) ---------------------------------------------------------------


def _probed_leg_from_commands(inputs: ReplayInput, commands_m_s: np.ndarray) -> ReplayInput:
    """Aborted probe rounds are not in ``probe_history.json``, so the episode puts LEG 0 there;
    in PROBE the leg the issued command of the update before moves is the probed one."""
    speeds = np.abs(commands_m_s)
    moving = np.where(speeds.max(axis=1) > 0.0, speeds.argmax(axis=1), -1)
    moving_before = np.concatenate(([-1], moving[:-1]))
    is_probe = np.asarray(inputs.watch_phase) == "probe"
    probed = np.where(is_probe, moving_before, inputs.probed_leg)
    return replace(inputs, probed_leg=probed)


def _record_replay(fast_relevel_changes: dict):
    geometry = C2Geometry.from_params(load_params())
    episode = build_episode(CASE, MachineConstants.from_geometry(geometry))
    events = read_controller_events(CASE / "controller_events.json")
    meta = json.loads((CASE / "result.json").read_text(encoding="utf-8"))["controller_meta"]
    run = ReplaySettings.from_controller_meta(meta, episode.F_min_N)
    fast = replace(run.fast_relevel, **fast_relevel_changes)
    config = C2Config().with_10hz_d1()
    config = replace(config, r8=replace(config.r8, fast_relevel=fast))
    monitor_replay = replay_fallback_monitor(episode, events, geometry, config)
    inputs = ReplayInput.from_episode(episode).with_fallback_monitor(monitor_replay)
    inputs = _probed_leg_from_commands(inputs, np.asarray(episode["command_m_s"]))
    replay = replay_judge(inputs, replace(run, fast_relevel=fast), Judge.COMBINED)
    return replay, events


def _r5_times(replay, kind: ActionKind) -> list[tuple[float, int]]:
    return [(round(e.t_s, 2), e.leg) for e in replay.events if e.kind is kind]


@pytest.mark.skipif(not CASE.is_dir(), reason=f"{CASE} not present")
def test_record_level_replay_reproduces_the_controller() -> None:
    replay, events = _record_replay({"fallback_slope": "level"})
    controller = [(round(t, 2), FL) for t, name in events if name == "relevel_predicted:FL"]
    assert controller == [(127.8, FL), (141.5, FL)]
    assert _r5_times(replay, ActionKind.R5) == controller


@pytest.mark.skipif(not CASE.is_dir(), reason=f"{CASE} not present")
@pytest.mark.parametrize(("source", "values_127_8_kN"), [
    ("plant_meta", (11.44, 0.0)),        # 302.5 L1 setting: nominal 11.44 kN
    ("column_nominal", (35.80, 8.98)),   # 302.5 machine setting: 26.83 + 8.98 kN
])
def test_record_fallback_slope_replay_has_no_false_relevel(source, values_127_8_kN) -> None:
    replay, _ = _record_replay({"fallback_slope": "nominal_gap", "fallback_ratio_source": source})
    assert _r5_times(replay, ActionKind.R5) == []
    (values,) = [e.values_kN for e in replay.events
                 if e.kind is ActionKind.R5_FALLBACK_SLOPE and round(e.t_s, 2) == 127.8]
    assert values == pytest.approx(values_127_8_kN, abs=0.01)
