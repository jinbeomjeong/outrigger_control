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


def _sealed_set(folder: Path, monkeypatch) -> dict[str, Path]:
    """Rules, rev1 and design texts sealed in ``folder`` (the tool's sealed values patched to
    their hashes), as the keywords of ``sealed_check``."""
    paths = {}
    for stem, constant in (("fb_targeted_rules", "RULES_SHA256"),
                           ("fb_targeted_rules_rev1", "RULES_REV1_SHA256")):
        text = folder / f"{stem}.md"
        text.write_text(f"sealed {stem}", encoding="utf-8")
        digest = ft.file_sha256(text)
        sha = folder / f"{stem}.sha256"
        sha.write_text(f"{digest}  {text.name}  sealed\n", encoding="utf-8")
        monkeypatch.setattr(ft, constant, digest)
        paths[stem] = text
        paths[f"{stem}_sha"] = sha
    design = folder / "fb_design.md"
    design.write_text("d", encoding="utf-8")
    return {"rules_path": paths["fb_targeted_rules"], "sha_path": paths["fb_targeted_rules_sha"],
            "rev1_path": paths["fb_targeted_rules_rev1"],
            "rev1_sha_path": paths["fb_targeted_rules_rev1_sha"], "design_path": design}


def test_sealed_check_passes_the_sealed_set(tmp_path, monkeypatch) -> None:
    assert ft.sealed_check(**_sealed_set(tmp_path, monkeypatch)) == []


def test_sealed_check_reports_a_changed_rules_file(tmp_path, monkeypatch) -> None:
    paths = _sealed_set(tmp_path, monkeypatch)
    paths["rules_path"].write_text("changed", encoding="utf-8")
    problems = ft.sealed_check(**paths)
    assert len(problems) == 1 and "fb_targeted_rules.md sha256" in problems[0]
    paths["design_path"].unlink()
    assert any("missing" in p for p in ft.sealed_check(**paths))


def test_sealed_check_stops_without_rev1(tmp_path, monkeypatch) -> None:
    paths = _sealed_set(tmp_path, monkeypatch)
    paths["rev1_path"].unlink()
    assert ft.sealed_check(**paths) == [f"missing {paths['rev1_path']}"]
    paths = _sealed_set(tmp_path, monkeypatch)
    paths["rev1_sha_path"].unlink()
    assert ft.sealed_check(**paths) == [f"missing {paths['rev1_sha_path']}"]


def test_sealed_check_reports_a_changed_rev1_byte(tmp_path, monkeypatch) -> None:
    paths = _sealed_set(tmp_path, monkeypatch)
    raw = bytearray(paths["rev1_path"].read_bytes())
    raw[0] ^= 1
    paths["rev1_path"].write_bytes(bytes(raw))
    problems = ft.sealed_check(**paths)
    assert len(problems) == 1 and "fb_targeted_rules_rev1.md sha256" in problems[0]


def test_sealed_check_reports_a_rev1_seal_value_the_tool_does_not_expect(
        tmp_path, monkeypatch) -> None:
    paths = _sealed_set(tmp_path, monkeypatch)
    paths["rev1_sha_path"].write_text("0" * 64 + "  fb_targeted_rules_rev1.md\n", encoding="utf-8")
    problems = ft.sealed_check(**paths)
    assert any("fb_targeted_rules_rev1.sha256 holds" in p for p in problems)


def test_f4_runs_r2_with_reanchor_on() -> None:
    assert ft.F4_CASES[0] == "R2ra"


# ------------------------------------------------------------------------------- audit fixes
def _c2_or_skip():
    try:
        from outrigger_sim.control import c2
    except ImportError:
        pytest.skip("outrigger_sim not importable")
    return c2


def test_the_r8_preset_is_las_b_b0_and_a_changed_value_is_refused() -> None:
    from dataclasses import replace

    c2 = _c2_or_skip()
    settings = c2.C2Config().with_10hz_d1().liftoff_approach_slow
    assert ft.preset_las_problems(settings) == []
    off = replace(settings, enable=False)
    assert ft.preset_las_problems(off) == ["liftoff_approach_slow.enable is False"]
    other = replace(settings, rho_on=0.2)
    assert ft.preset_las_problems(other) == ["rho_on 0.2 != b0 0.18"]
    assert ft.preset_las_problems(None) == ["no liftoff_approach_slow settings"]
    no_soil = replace(settings, require_soil_response=False)
    assert "require_soil_response" in ft.preset_las_problems(no_soil)[0]


def test_install_candidate_checks_the_preset_and_never_installs_the_las_wrapper(
        monkeypatch) -> None:
    import las_targeted as lt

    calls = []
    monkeypatch.setattr(ft, "check_preset_las", lambda: calls.append("preset"))
    monkeypatch.setattr(ft, "install", lambda params: calls.append("fb"))
    monkeypatch.setattr(ft, "_capture_runs", lambda: calls.append("capture"))
    monkeypatch.setattr(lt, "install", lambda *args: calls.append("las wrapper"))
    ft._install_candidate(ft.CANDIDATES["L"])
    assert calls == ["preset", "capture"]
    calls.clear()
    ft._install_candidate(ft.CANDIDATES["LF"])
    assert calls == ["preset", "fb", "capture"]


def test_check_preset_las_stops_when_the_preset_has_las_off(monkeypatch) -> None:
    c2 = _c2_or_skip()
    preset = c2.C2Config.with_10hz_d1
    monkeypatch.setattr(c2.C2Config, "with_10hz_d1",
                        lambda self, **kw: preset(self, **{**kw, "liftoff_approach_slow": False}))
    with pytest.raises(RuntimeError, match="not LAS-b b0"):
        ft.check_preset_las()


def test_check_preset_las_stops_with_the_las_wrapper_installed(monkeypatch) -> None:
    import las_targeted as lt

    _c2_or_skip()
    monkeypatch.setitem(lt._INSTALLED, "params", lt.CANDIDATES["b0"])
    with pytest.raises(RuntimeError, match="act twice"):
        ft.check_preset_las()


def _las_meta(start_s=22.8, leg="RL") -> dict:
    settings = {"enable": True, "sum_on_fraction_W": 0.6, "light_leg_fraction_of_F_min": 3.5,
                "slow_mean_fraction": 0.16, "sum_off_fraction_W": 0.85, "off_periods": 5,
                "max_s": 1.5, "rho_on": 0.18, "require_soil_response": True}
    return {"settings": settings, "start_s": start_s, "start_leg": leg, "start_rho": 0.207,
            "start_rho_prev": 0.132, "end_s": 23.5, "end_reason": "sum", "active_periods": 7,
            "scaled_periods": 7}


def test_las_block_from_meta_has_the_las_targeted_fields() -> None:
    import las_targeted as lt

    harness = {"loc_delay_s": 1.0, "t_loc_s": 24.6, "t_off_s": 23.6}
    block = ft.las_block_from_meta(_las_meta(), True, 376583.56, harness)
    wrapper_block = lt.las_block("b0", lt.CANDIDATES["b0"], lt.MODE_ACT, lt.LasRun(
        lt.CANDIDATES["b0"], lt.MODE_ACT), harness)
    assert set(wrapper_block) <= set(block)
    assert block["params"] == lt.CANDIDATES["b0"].to_dict()
    assert (block["candidate"], block["mode"]) == ("b0", "act")
    assert block["start_leg"] == 2 and block["start_t_s"] == 22.8
    assert block["end_reason"] == "sum" and block["active_periods"] == 7
    assert block["s7p_first"] is None and block["start_rho"] == 0.207
    assert block["loc_minus_t_off_s"] == 1.0 and block["source"] == ft.LAS_SOURCE


def test_las_block_without_a_las_state_is_not_reached() -> None:
    meta = {"settings": _las_meta()["settings"]}
    block = ft.las_block_from_meta(meta, True, 1.0, None)
    assert block["wrapper_reached"] is False and block["params"]["n_end"] == 5
    assert ft.las_block_from_meta(_las_meta(start_s=None, leg=None), True, 1.0,
                                  None)["start_leg"] is None


def test_a_run_without_captured_objects_is_an_error() -> None:
    entry = {"name": "L", "bundle": "F-0"}
    job = {"d1": {"key": "D1|x"}, "setting": "VB", "eps": 0.0}
    with pytest.raises(RuntimeError, match="not captured"):
        ft._fb_block(entry, job, ft.CANDIDATES["L"], None, object(), {})
    with pytest.raises(RuntimeError, match="not captured"):
        ft._fb_block(entry, job, ft.CANDIDATES["L"], object(), None, {})


def test_thread_variables_are_forced_to_one() -> None:
    import os

    assert all(os.environ[name] == "1" for name in ft.THREAD_VARIABLES)
    values = ft.thread_values({"MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "4"})
    assert ft.thread_problems(values) == ["OMP_NUM_THREADS='4'", "OPENBLAS_NUM_THREADS=None",
                                          "NUMBA_NUM_THREADS=None"]
    assert ft.thread_problems(ft.thread_values()) == []


def test_run_identity_records_commit_hashes_and_threads(tmp_path) -> None:
    import subprocess

    tool = tmp_path / "tool.py"
    tool.write_text("x = 1\n", encoding="utf-8")
    try:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=60)
        for args in (["add", "tool.py"], ["-c", "user.name=t", "-c", "user.email=t@t",
                                          "commit", "-q", "-m", "t"]):
            subprocess.run(["git", "-C", str(tmp_path), *args], check=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git not usable")
    identity = ft.run_identity(tmp_path, {"tool.py": tool})
    assert len(identity["git_head"]) == 40 and identity["git_dirty"] is False
    assert identity["sha256"]["tool.py"] == ft.file_sha256(tool)
    assert identity["threads"]["MKL_NUM_THREADS"] == "1"
    (tmp_path / "untracked.md").write_text("u", encoding="utf-8")
    assert ft.run_identity(tmp_path, {"tool.py": tool})["git_dirty"] is False
    tool.write_text("x = 2\n", encoding="utf-8")
    changed = ft.run_identity(tmp_path, {"tool.py": tool})
    assert changed["git_dirty"] is True and changed["dirty_files"] == ["tool.py"]
    assert ft.identity_mismatch(identity, changed) == [
        f"sha256 {identity['sha256']} != {changed['sha256']}"]


IDENTITY = {"git_head": "a" * 40, "git_dirty": False, "sha256": {"c2.py": "1" * 64},
            "threads": {"MKL_NUM_THREADS": "1"}}


def _identified(line: dict, identity: dict | None = IDENTITY) -> dict:
    line["fb"]["identity"] = identity
    return line


def test_stale_lines_name_another_commit_or_a_missing_identity() -> None:
    same = _identified(_line("L", "k1"))
    other = _identified(_line("LF", "k1"), {**IDENTITY, "git_head": "b" * 40})
    none = _identified(_line("L", "k2"), None)
    assert ft.stale_lines([same], IDENTITY) == []
    stale = ft.stale_lines([same, other, none], IDENTITY)
    assert len(stale) == 2 and "git_head" in stale[0] and "no run identity" in stale[1]


def test_f0_gate_stops_on_lines_of_another_identity(tmp_path) -> None:
    import json

    vb_key, v0_key = ft.F0_KEYS
    lines = [_identified(_line(name, key), {**IDENTITY, "git_head": "b" * 40})
             for key in (vb_key, v0_key) for name in ("L", "LF-off")]
    (tmp_path / "fb_F0.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines),
                                          encoding="utf-8")
    reason = ft._check_f0_gate(tmp_path, IDENTITY)
    assert reason is not None and "another run identity" in reason


def test_main_refuses_to_resume_into_a_file_of_another_identity(tmp_path, monkeypatch,
                                                               capsys) -> None:
    import json

    out = tmp_path / "fb_F0.jsonl"
    old = _identified(_line("L", ft.F0_KEYS[0]), {**IDENTITY, "git_head": "b" * 40})
    out.write_text(json.dumps(old) + "\n", encoding="utf-8")
    monkeypatch.setattr(ft, "sealed_check", lambda: [])
    monkeypatch.setattr(ft, "run_identity", lambda: IDENTITY)
    monkeypatch.setattr(ft, "run_batch", lambda *a, **k: pytest.fail("must not run"))
    assert ft.main(["run", "--bundle", "F-0", "--out", str(out)]) == 1
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["stop"] == "identity"


def test_batch_watch_counts_the_earlier_lines_and_checks_identity() -> None:
    lines = []
    for index in range(5):
        key = f"k{index}"
        lines += [_identified(_line("L", key)),
                  _identified(_line("LF", key, verdict="fail"))]
    watch = ft.preloaded_watch("F-1", {}, lines[:8], IDENTITY)
    assert len(watch.c2_violations) == 4 and watch.identity_problems == []
    watch.note(lines[8])
    watch.note(lines[9])
    assert len(watch.c2_violations) == 5
    watch.note(_identified(_line("L", "k9"), {**IDENTITY, "git_head": "c" * 40}))
    assert watch.identity_problems and "git_head" in watch.identity_problems[0]


def test_run_batch_stops_before_running_when_the_file_has_five_violations() -> None:
    lines = []
    for index in range(5):
        lines += [_identified(_line("L", f"k{index}")),
                  _identified(_line("LF", f"k{index}", verdict="fail"))]
    summary = ft.run_batch([{"never": "run"}], Path("unused.jsonl"), 1, "F-1", None, lines,
                           IDENTITY)
    assert summary["runs"] == 0 and summary["stop"].startswith("H-4")


@pytest.mark.parametrize("content", ["", "   \n", "not-a-hash  fb_targeted_rules.md\n"])
def test_sealed_check_reports_a_sha256_file_without_a_value(tmp_path, monkeypatch,
                                                            content) -> None:
    paths = _sealed_set(tmp_path, monkeypatch)
    paths["sha_path"].write_text(content, encoding="utf-8")
    problems = ft.sealed_check(**paths)
    assert problems == ["fb_targeted_rules.sha256 holds no sha256 value"]


def test_main_stops_with_h1_on_an_empty_sha256_file(tmp_path, monkeypatch, capsys) -> None:
    paths = _sealed_set(tmp_path, monkeypatch)
    paths["sha_path"].write_text("", encoding="utf-8")
    # sealed_check's defaults are bound at definition: point them at the test set
    monkeypatch.setattr(ft.sealed_check, "__defaults__", (
        paths["rules_path"], paths["sha_path"], paths["design_path"], paths["rev1_path"],
        paths["rev1_sha_path"]))
    assert ft.main(["list", "--bundle", "F-0"]) == 2
    assert fj.main(["--out-dir", str(tmp_path)]) == 2
    assert "H-1" in capsys.readouterr().out


# ------------------------------------------------------------------------------- judge fixes
def _data(bundles: dict, expected: dict | None = None, family=None, stored=None) -> fj.Data:
    by_bundle = {bundle: fj.lines_by_key(lines) for bundle, lines in bundles.items()}
    expected = expected if expected is not None else {
        bundle: sorted(by_bundle.get(bundle, {})) for bundle in fj.JUDGED_BUNDLES}
    family = family if family is not None else [f"fam{i}" for i in range(8)]
    return fj.Data(by_bundle, stored or {}, family, expected)


def test_missing_saturation_breaks_c1_and_c5() -> None:
    line = _line("LF", "k")
    line["fb"]["saturation_s"] = None
    data = _data({"F-1": [_line("L", "k"), line]})
    assert fj.c1(data).passed is False
    eta80 = _line("LF", "k80")
    eta80["job"]["eta_v"] = 0.80
    eta80["fb"]["u9_values"] = {"longest_ge3_s": 0.0}
    result = fj.c5(_data({"F-1": [eta80]}))
    assert result.passed is False and any("TOUCH" in text for text in result.details)


def test_completion_needs_the_paired_keys_to_equal_the_expected_keys() -> None:
    lines = [_line("L", "a"), _line("LF", "a"), _line("L", "b"), _line("LF", "b")]
    expected = {"F-1": ["a", "c"], "F-2": ["x"], "F-3": ["y"], "F-4": ["z"]}
    data = _data({"F-1": lines}, expected)
    # "b" paired but not expected and "c" expected but not paired: 2 (+ 3 empty bundles)
    assert data.missing_pairs(("F-1",)) == 2
    assert fj.c2(data).passed is None
    nothing_expected = _data({"F-1": lines}, {"F-1": []})
    assert nothing_expected.missing_pairs(("F-1",)) == 3


def _every_bundle_paired(reference_ready_s: float | None) -> fj.Data:
    """One pair per judged bundle (F-2: stored L); the L lines have the given READY time."""
    bundles, stored = {}, {}
    for bundle in fj.JUDGED_BUNDLES:
        key = f"{bundle}-k"
        reference = _line("L", key)
        reference["d1"]["t_ready_s"] = reference_ready_s
        if bundle == "F-2":
            stored[key] = reference
            bundles[bundle] = [_line("LF", key)]
        else:
            bundles[bundle] = [reference, _line("LF", key)]
    return _data(bundles, stored=stored)


def test_c4_without_a_judged_pair_is_incomplete() -> None:
    no_ready = _every_bundle_paired(None)
    assert no_ready.missing_pairs() == 0
    assert fj.c4(no_ready).passed is None
    assert fj.c4(_every_bundle_paired(60.0)).passed is True


def test_c3_needs_all_eight_family_keys() -> None:
    family = [f"fam{i}" for i in range(8)]
    stored = {key: _line("b0", key) for key in family}
    lines = [_line("LF", key) for key in family[:7]]
    assert fj.c3(_data({"F-2": lines}, family=family, stored=stored)).passed is None
    lines.append(_line("LF", family[7]))
    assert fj.c3(_data({"F-2": lines}, family=family, stored=stored)).passed is True


def test_load_data_refuses_a_family_that_is_not_eight_keys(tmp_path) -> None:
    with pytest.raises(ValueError, match="8"):
        fj.load_data(tmp_path, family_keys=["a"] * 8, stored_paths=())


def test_identity_problems_per_bundle_and_f2_stored_lines_apart() -> None:
    good = [_identified(_line("L", "a")), _identified(_line("LF", "a"))]
    assert fj.identity_problems(fj.bundle_identities(_data({"F-1": good}))) == []
    mixed = good + [_identified(_line("L", "b"), {**IDENTITY, "git_head": "b" * 40}),
                    _identified(_line("LF", "b"), None)]
    problems = fj.identity_problems(fj.bundle_identities(_data({"F-1": mixed})))
    assert any("without identity" in p for p in problems)
    assert any("2 commits" in p for p in problems)
    stored = {"s": _line("b0", "s")}  # a stored F-2 L line has no identity: not a problem
    f2 = _data({"F-2": [_identified(_line("LF", "s"))]}, stored=stored)
    assert fj.identity_problems(fj.bundle_identities(f2)) == []
    assert any("저장" in text for text in fj.identity_report(f2, fj.bundle_identities(f2)))
    assert fj.verdict_of([], ["F-1: 2 commits"]) == fj.IDENTITY_VERDICT


def test_event_count_record_marks_truncation(monkeypatch) -> None:
    import verdict_runs

    monkeypatch.setattr(verdict_runs, "_stored_events", lambda controller: [(0.0, "x")] * 401)
    assert ft.event_count_record(object()) == {"events_total": 401, "events_truncated": True,
                                               "events_stored_limit": 400}
    monkeypatch.setattr(verdict_runs, "_stored_events", lambda controller: [])
    assert ft.event_count_record(object())["events_truncated"] is False
