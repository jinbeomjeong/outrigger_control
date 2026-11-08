"""Checks of the FB wrapper and judge (``fb_targeted_rules.md`` 1, 4), no harness run.

The wrapper is installed on a stand-in controller class (same method names as
``C2Controller``); the detector is fed synthetic stroke readings; the judge gets synthetic
lines. Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fb_judge as fj  # noqa: E402
import fb_targeted as ft  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

V_MAX_M_S = 0.020924
PERIOD_S = 0.1
PUMP_M3_S = 1.00333e-3
"""YAML ``actuator.pump_flow_m3_s`` (60.2 L/min, rules 1.1)."""
HEAD_M2 = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
ANNULUS_M2 = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
GEOMETRY = ft.DetectGeometry(HEAD_M2, ANNULUS_M2, V_MAX_M_S, 0.6948, 1.0e9, 0.05)
NOMINAL_M3_S = ft.nominal_budget_m3_s(PUMP_M3_S)


class Phase(StrEnum):
    TOUCH = "touch"
    LEVEL = "level"
    DONE = "done"


@dataclass
class Reading:
    t_s: float
    motor_stroke_m: np.ndarray
    cylinder_force_N: np.ndarray


@dataclass
class State:
    phase: Phase = Phase.TOUCH
    previous_output_m_s: np.ndarray = field(default_factory=lambda: np.zeros(4))
    last_reading: Reading | None = None
    touch_seen: np.ndarray = field(default_factory=lambda: np.zeros(4, bool))


@dataclass
class Command:
    t_s: float
    leg_speed_m_s: np.ndarray


class Config:
    period_s = PERIOD_S


class FakeController:
    """Stand-in: the ramp passes the request, ``update`` returns the given speeds."""

    def __init__(self) -> None:
        self.geometry = GEOMETRY
        self.config = Config()
        self._state = State()
        self.events: list[tuple[float, str]] = []
        self.next_command = np.zeros(4)
        self.level_speeds = np.zeros(4)

    def _apply_output_ramp(self, leg_speeds):
        output = np.asarray(leg_speeds, float).copy()
        self._state.previous_output_m_s = output
        return output

    def update(self, measurements):
        self._state.last_reading = measurements
        return Command(measurements.t_s, self.next_command.copy())

    def _level_step(self, reading):
        return self.level_speeds.copy()

    def _add_event(self, t_s, name):
        self.events.append((float(t_s), name))


@pytest.fixture
def installed():
    def do_install(name: str):
        ft.install(ft.CANDIDATES[name], FakeController, Phase, pump_m3_s=PUMP_M3_S)
        return FakeController()

    yield do_install
    ft.uninstall()


# ------------------------------------------------------------------------------- FB-a
def test_nominal_budget_is_the_sealed_value() -> None:
    assert NOMINAL_M3_S * ft.M3_S_TO_L_MIN == pytest.approx(50.1466, abs=5e-4)
    four_legs = ft.command_flow_m3_s(np.full(4, V_MAX_M_S), HEAD_M2, ANNULUS_M2)
    assert NOMINAL_M3_S / four_legs == pytest.approx(0.876840, abs=5e-5)


def test_yaml_pump_flow_is_read() -> None:
    if not ft.YAML_PATH.exists():
        pytest.skip("no YAML")
    assert ft.pump_flow_m3_s() == pytest.approx(PUMP_M3_S, rel=1e-4)


def test_budget_scales_the_ramp_output_and_stores_it(installed) -> None:
    controller = installed("LF")
    out = controller._apply_output_ramp(np.full(4, V_MAX_M_S))
    flow = ft.command_flow_m3_s(out, HEAD_M2, ANNULUS_M2)
    assert flow == pytest.approx(NOMINAL_M3_S)
    assert np.allclose(out, 0.876840 * V_MAX_M_S, rtol=5e-5)
    assert controller._state.previous_output_m_s is out
    budget = controller.__dict__["_fb_run"]
    assert budget.acted_periods == {"touch": 1}
    assert budget.min_scale == pytest.approx(0.876840, abs=5e-5)


def test_budget_keeps_direction_and_never_makes_a_retraction(installed) -> None:
    controller = installed("LF")
    request = np.array([V_MAX_M_S, 0.0, -0.5 * V_MAX_M_S, V_MAX_M_S])
    request_flow = ft.command_flow_m3_s(request, HEAD_M2, ANNULUS_M2)
    controller.__dict__["_fb_run"] = ft.FbState(NOMINAL_M3_S, 0.5 * request_flow)
    out = controller._apply_output_ramp(request)
    assert np.allclose(out, 0.5 * request)
    assert np.array_equal(np.sign(out), np.sign(request))
    assert out[1] == 0.0
    assert np.all(out[request >= 0.0] >= 0.0)


def test_budget_inside_returns_the_ramp_output_untouched(installed) -> None:
    controller = installed("LF")
    request = np.array([0.5, 0.5, 0.5, 0.5]) * V_MAX_M_S
    out = controller._apply_output_ramp(request)
    assert np.array_equal(out, request)
    assert controller.__dict__["_fb_run"].acted_periods == {}


def test_off_switch_changes_nothing(installed) -> None:
    controller = installed("LF-off")
    out = controller._apply_output_ramp(np.full(4, V_MAX_M_S))
    assert np.array_equal(out, np.full(4, V_MAX_M_S))
    reading = Reading(0.0, np.zeros(4), np.zeros(4))
    controller.next_command = np.full(4, V_MAX_M_S)
    controller.update(reading)
    assert "_fb_run" not in controller.__dict__ and controller.events == []


def test_install_guards(installed) -> None:
    installed("LF")
    with pytest.raises(RuntimeError):
        ft.install(ft.CANDIDATES["LF"], FakeController, Phase, pump_m3_s=PUMP_M3_S)
    ft.uninstall()
    with pytest.raises(ValueError):
        ft.install(ft.CANDIDATES["L"], FakeController, Phase, pump_m3_s=PUMP_M3_S)


# ------------------------------------------------------------------------------- FB-b
def _feed(state: ft.FbState, periods: int, ratio, *, command=V_MAX_M_S, phase="touch",
          touch_seen=False, force_step_N=0.0, start_t_s=0.0, stroke_m=None):
    """Constant command ``a``; the stroke moves by ratio x the modelled valve mean."""
    stroke = np.full(4, 0.1) if stroke_m is None else stroke_m.copy()
    force = np.zeros(4)
    ratio = np.broadcast_to(np.asarray(ratio, float), 4)
    events = []
    for k in range(periods):
        t_s = start_t_s + k * PERIOD_S
        if state.previous is not None:
            stroke = stroke + ratio * state.previous.mean_m_s * PERIOD_S
            force = force + force_step_N
        names = ft.detect_step(state, stroke, force, np.full(4, command), phase, touch_seen,
                               GEOMETRY, PERIOD_S, t_s)
        events += [(round(t_s, 6), name) for name in names]
    return events, stroke


def test_valve_mean_matches_the_first_order_lag() -> None:
    mean, valve = ft.valve_step(np.zeros(4), np.full(4, 1.0), PERIOD_S)
    assert mean[0] == pytest.approx(1.0 - (1.0 - math.exp(-1.0)))
    assert valve[0] == pytest.approx(1.0 - math.exp(-1.0))


def test_four_slow_legs_in_free_touch_confirm_u_and_a97_after_two_periods() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 4, 0.85)
    # update 0 has no period, period 0 is not steady (a_{-1} = 0), periods 1 and 2 count
    assert events == [(0.3, "INFO_FLOW_BUDGET_CUT:U"), (0.3, "INFO_FLOW_BUDGET_CUT:A97")]
    assert state.budget_m3_s < NOMINAL_M3_S
    assert state.budget_m3_s >= ft.FLOOR_FRACTION * NOMINAL_M3_S
    assert [cut.rule for cut in state.cuts] == ["U", "A97"]
    assert state.u_count == 0 and state.a97_count == 0


def test_cut_is_097_of_the_measured_delivery() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    delivered = np.full(4, 0.8 * V_MAX_M_S)
    event = ft.apply_cut(state, "U", delivered, GEOMETRY, 1.0)
    expected = 0.97 * ft.command_flow_m3_s(delivered, HEAD_M2, ANNULUS_M2)
    assert state.budget_m3_s == pytest.approx(expected)
    assert event == "INFO_FLOW_BUDGET_CUT:U"


def test_cut_has_a_floor_and_the_budget_never_rises() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    _feed(state, 4, 0.2, touch_seen=True)
    assert state.budget_m3_s == pytest.approx(ft.FLOOR_FRACTION * NOMINAL_M3_S)
    floor = state.budget_m3_s
    events, _ = _feed(state, 6, 1.0, touch_seen=True, start_t_s=1.0)
    assert events == [] and state.budget_m3_s == floor


def test_u_alone_outside_free_touch() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 4, 0.85, touch_seen=True)
    assert [name for _, name in events] == ["INFO_FLOW_BUDGET_CUT:U"]
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 4, 0.85, phase="level")
    assert [name for _, name in events] == ["INFO_FLOW_BUDGET_CUT:U"]


def test_a97_alone_when_every_leg_is_just_short() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 4, 0.95)
    assert [name for _, name in events] == ["INFO_FLOW_BUDGET_CUT:A97"]
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 4, 0.95, phase="level")
    assert events == []


def test_two_slow_legs_do_not_confirm_u() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 6, [0.85, 0.85, 1.0, 1.0], touch_seen=True)
    assert events == []
    assert state.r_min[0] == pytest.approx(0.85) and state.r_min[3] == pytest.approx(1.0)


def test_load_change_gate_blocks_u_only() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    # 0.02 k_oil(0.1 m) m T is about 2 .. 3 kN here; 5 kN per period fails the gate
    events, _ = _feed(state, 5, 0.85, touch_seen=True, force_step_N=5000.0)
    assert events == []
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 4, 0.95, force_step_N=5000.0)
    assert [name for _, name in events] == ["INFO_FLOW_BUDGET_CUT:A97"]


def test_slow_command_or_stroke_end_is_not_evaluated() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 6, 0.5, command=0.2 * V_MAX_M_S)
    assert events == [] and state.evaluated_periods == 0
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    events, _ = _feed(state, 6, 0.5, stroke_m=np.full(4, 0.68))
    assert events == [] and state.evaluated_periods == 0


def test_a_broken_run_resets_the_counter() -> None:
    state = ft.FbState(NOMINAL_M3_S, NOMINAL_M3_S)
    _feed(state, 3, 0.85, touch_seen=True)
    assert state.u_count == 1
    _feed(state, 1, 1.0, touch_seen=True, start_t_s=0.3, stroke_m=state.previous.stroke_m)
    assert state.u_count == 0 and state.cuts == []


def test_update_wrapper_adds_the_event_and_latches_the_budget(installed) -> None:
    controller = installed("LF")
    controller.next_command = np.full(4, V_MAX_M_S)
    stroke = np.full(4, 0.1)
    for k in range(4):
        budget = controller.__dict__.get("_fb_run")
        if budget is not None and budget.previous is not None:
            stroke = stroke + 0.85 * budget.previous.mean_m_s * PERIOD_S
        controller.update(Reading(k * PERIOD_S, stroke.copy(), np.zeros(4)))
    assert [name for _, name in controller.events] == ["INFO_FLOW_BUDGET_CUT:U",
                                                       "INFO_FLOW_BUDGET_CUT:A97"]
    cut_budget = controller.__dict__["_fb_run"].budget_m3_s
    out = controller._apply_output_ramp(np.full(4, V_MAX_M_S))
    assert ft.command_flow_m3_s(out, HEAD_M2, ANNULUS_M2) == pytest.approx(cut_budget)


# ------------------------------------------------------------------------------- OL
def test_open_loop_window_holds_v_max_for_eight_seconds(installed) -> None:
    controller = installed("OL-L")
    controller._state.phase = Phase.LEVEL
    controller.level_speeds = np.array([0.001, 0.002, 0.003, 0.004])
    first = controller._level_step(Reading(20.0, np.zeros(4), np.zeros(4)))
    assert np.array_equal(first, np.full(4, V_MAX_M_S))
    controller._state.phase = Phase.DONE
    inside = controller._level_step(Reading(27.9, np.zeros(4), np.zeros(4)))
    assert np.array_equal(inside, np.full(4, V_MAX_M_S))
    assert controller._state.phase is Phase.LEVEL
    after = controller._level_step(Reading(28.0, np.zeros(4), np.zeros(4)))
    assert np.array_equal(after, controller.level_speeds)
    assert controller.__dict__["_fb_run"].open_loop_periods == 2
    out = controller._apply_output_ramp(np.full(4, V_MAX_M_S))
    assert np.array_equal(out, np.full(4, V_MAX_M_S))  # OL-L: no budget


# ------------------------------------------------------------------------------- judge
def _line(candidate: str, key: str, *, verdict="pass", fail_items=(), events=None,
          sha="a" * 64, t_ready=60.0, stroke=0.6, setting="VB") -> dict:
    return {"job": {"setting": setting}, "commands_sha256": sha, "final_phase": "ready",
            "event_names": events or {}, "values": {"times": {"t_first_ready_s": t_ready}},
            "d1": {"verdict": verdict, "fail_items": list(fail_items), "t_ready_s": t_ready,
                   "stroke_max_m": stroke, "F_judged_min_N": 12e3},
            "fb": {"candidate": candidate, "key": key, "budget": {"cuts": []},
                   "saturation_s": {"all": {"any_s": 0.0}}}}


def test_c2_counts_pass_to_fail_new_items_and_new_warnings() -> None:
    reference = _line("L", "k", fail_items=["G6-2_loc"], verdict="fail")
    candidate = _line("LF", "k", verdict="fail", fail_items=["G6-2_loc", "P3-2_x"],
                      events={"WARN_X": 1, "INFO_Y": 1})
    assert fj.c2_violations(reference, candidate) == ["(a) new P3-2_x failure", "(c) new WARN_X"]
    assert fj.c2_violations(_line("L", "k"), _line("LF", "k", verdict="fail")) == [
        "(a) pass -> fail []"]
    assert fj.c2_violations(_line("L", "k"), _line("LF", "k")) == []


def test_c7_needs_equal_hashes_and_the_stored_b0_hash() -> None:
    vb_key, v0_key = ft.F0_KEYS
    lines = [_line("L", vb_key), _line("LF-off", vb_key), _line("L", v0_key),
             _line("LF-off", v0_key)]
    stored = {vb_key: _line("b0", vb_key)}
    assert fj.check_c7(lines, stored)["pass"]
    stored = {vb_key: _line("b0", vb_key, sha="b" * 64)}
    assert not fj.check_c7(lines, stored)["pass"]
    lines[1] = _line("LF-off", vb_key, sha="c" * 64)
    assert not fj.check_c7(lines, {vb_key: _line("b0", vb_key)})["pass"]


def test_sealed_check_reports_a_changed_file(tmp_path) -> None:
    rules = tmp_path / "fb_targeted_rules.md"
    rules.write_text("changed", encoding="utf-8")
    sha = tmp_path / "fb_targeted_rules.sha256"
    sha.write_text(f"{ft.RULES_SHA256}  fb_targeted_rules.md  sealed\n", encoding="utf-8")
    design = tmp_path / "fb_design.md"
    assert any("missing" in p for p in ft.sealed_check(rules, sha, design))
    design.write_text("d", encoding="utf-8")
    problems = ft.sealed_check(rules, sha, design)
    assert len(problems) == 1 and "!= sealed" in problems[0]
