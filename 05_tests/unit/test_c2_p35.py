"""C2 P-S8-35 differential pad sinking after the LOC, form DSb75 (control spec 424.11 / 424.11.1 /
424.11.2), tests 1 .. 9 of the python implementation draft.

The watch is driven through ``_diff_sink_update`` with simple readings; ``_diff_sink_rates_m_s``
is replaced where a test needs a given signal. Test 9 runs harness cases of
``s9_slope_fix_candidates.py`` in a subprocess (slow) against the stored wrapper ``DSb75`` rows.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from collections import deque
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_p28 import level_bench, p28_config  # same test folder
from test_c2_r8d1 import operating_strokes  # same test folder

from outrigger_sim.control import c2 as c2_module
from outrigger_sim.control.c2 import (
    DIFF_SINK_HOLD_EVENT,
    DIFF_SINK_RELEASE_EVENT,
    C2Config,
    C2Controller,
    C2Phase,
    DiffSinkSettings,
    _RunState,
)
from outrigger_sim.params import load_params

ROOT = Path(__file__).resolve().parents[2]
WRAPPER_DIR = ROOT / "04_scripts" / "03_control" / "s9"
WRAPPER_SCRIPT = WRAPPER_DIR / "s9_slope_fix_candidates.py"
PRE_SWITCH_RUNNER = Path(__file__).with_name("pre_switch_preset_runner.py")
REV83 = ROOT / "06_analysis" / "02_control" / "s9" / "rev83"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The harnesses need dynamics-dev (numba, sympy), not the Chrono-dev test env."""
PERIOD_S = 0.1
STROKE_M = 0.30
STROKE_LIMIT_M = 0.6428
"""Lift guard stroke 682.8 mm minus the 40 mm margin."""


class _Reading:
    def __init__(self, t_s: float, strokes_m) -> None:
        self.t_s = t_s
        self.motor_stroke_m = np.asarray(strokes_m, float)


@pytest.fixture(scope="module")
def params():
    return load_params()


def watching_controller(params, *, is_gate_open: bool = True, **changes) -> C2Controller:
    """R8 preset controller in LEVEL whose watch started at a LOC at 1.0 s."""
    config = C2Config().with_10hz_d1()
    config = replace(config, diff_sink=replace(config.diff_sink, **changes))
    controller = C2Controller.from_params(params, config)
    controller._state.phase = C2Phase.LEVEL
    sink = controller._diff_sink_state()
    sink.first_loc_s = 1.0
    sink.is_gate_open = is_gate_open
    sink.gyro_roll = deque([0.0] * 100, maxlen=100)
    return controller


def drive(controller, rates_m_s, periods: int, t_start_s: float = 2.0,
          stroke_m: float = STROKE_M, monkeypatch=None) -> float:
    """``periods`` LEVEL periods with ``_diff_sink_rates_m_s`` fixed at ``rates_m_s``."""
    monkeypatch.setattr(controller, "_diff_sink_rates_m_s", lambda: np.asarray(rates_m_s, float))
    t_s = t_start_s
    for _ in range(periods):
        t_s = round(t_s + PERIOD_S, 10)
        controller._diff_sink_update(_Reading(t_s, [stroke_m] * 4))
    return t_s


def event_names(controller) -> list[str]:
    return [e.name for e in controller.events if e.name.startswith("INFO_DIFF_SINK")]


def hold(controller):
    return controller._diff_sink_state().hold


# --- 1: settings, defaults, off = bit for bit --------------------------------------------------


def test_1_class_default_is_off_and_the_r8_preset_is_dsb75() -> None:
    assert not DiffSinkSettings().enable and C2Config().diff_sink == DiffSinkSettings()
    assert _RunState.diff_sink is None  # class attribute (old pickles)
    preset = C2Config().with_10hz_d1().diff_sink
    assert preset == DiffSinkSettings(enable=True)
    sys.path.insert(0, str(WRAPPER_DIR))
    import s9_slope_fix_candidates as fx

    token = fx.parse_candidate("DSb75")
    assert (preset.threshold_m_s, preset.confirm_s, preset.release_m_s, preset.release_s,
            preset.max_s, preset.gain, preset.add_cap_fraction, preset.track_w_m,
            preset.gate_max_settle_tilt_rad, preset.stroke_margin_m) == (
        token.ds_threshold_m_s, token.ds_confirm_s, token.ds_release_m_s, token.ds_release_s,
        token.ds_max_s, token.ds_gain, token.ds_add_cap_fraction, token.ds_track_w_m,
        token.ds_gate_max_settle_tilt_rad, token.l1_stroke_margin_m)


@pytest.mark.parametrize("bad", [{"release_m_s": 0.004}, {"gain": 0.0}, {"max_s": -1.0},
                                 {"add_cap_fraction": 0.0}])
def test_1_settings_reject_bad_values(bad) -> None:
    with pytest.raises(ValueError):
        DiffSinkSettings(**bad)


def test_1_on_and_off_command_alike_without_a_loc(params) -> None:
    geometry = c2_module.C2Geometry.from_params(params)
    outputs = []
    for is_on in (True, False):
        config = replace(p28_config(), diff_sink=DiffSinkSettings(enable=is_on))
        bench = level_bench(geometry, config, operating_strokes(geometry))
        for _ in range(60):
            bench.step()
        outputs.append(np.array(bench.outputs))
    np.testing.assert_array_equal(outputs[0], outputs[1])


def test_1_meta(params) -> None:
    controller = watching_controller(params)
    meta = json.loads(json.dumps(controller.meta()))["diff_sink"]
    assert meta["gate_open"] and meta["first_loc_s"] == 1.0 and meta["events"] == []


# --- signal ------------------------------------------------------------------------------------


def test_signal_is_the_stroke_slope_difference_minus_the_gyro_roll(params) -> None:
    controller = watching_controller(params)
    sink = controller._diff_sink_state()
    roll_rate = 0.001
    sink.gyro_roll = deque([roll_rate] * 100, maxlen=100)
    for k in range(10):
        t_s = 2.0 + 0.1 * k
        strokes = [STROKE_M + 0.005 * t_s, STROKE_M + 0.001 * t_s, STROKE_M, STROKE_M + 0.002 * t_s]
        sink.strokes.append((t_s, np.array(strokes)))
    rates = controller._diff_sink_rates_m_s()
    assert rates[0] == pytest.approx(0.004 - 2.648 * roll_rate, abs=1e-9)
    assert rates[1] == pytest.approx(-0.002 - 2.411 * roll_rate, abs=1e-9)


# --- 2: threshold, 1 s confirmation ------------------------------------------------------------


@pytest.mark.parametrize(("rate_m_s", "is_held"), [(0.0029, False), (0.0031, True)])
def test_2_threshold(params, monkeypatch, rate_m_s, is_held) -> None:
    controller = watching_controller(params)
    drive(controller, [rate_m_s, 0.0], 10, monkeypatch=monkeypatch)
    assert (hold(controller) is not None) is is_held


def test_2_needs_ten_periods_in_a_row(params, monkeypatch) -> None:
    controller = watching_controller(params)
    t_s = drive(controller, [0.0, -0.004], 9, monkeypatch=monkeypatch)
    t_s = drive(controller, [0.0, 0.0], 1, t_s, monkeypatch=monkeypatch)
    t_s = drive(controller, [0.0, -0.004], 9, t_s, monkeypatch=monkeypatch)
    assert hold(controller) is None
    drive(controller, [0.0, -0.004], 1, t_s, monkeypatch=monkeypatch)
    assert hold(controller).axis == 1 and hold(controller).legs == (1, 3)
    assert hold(controller).sign == -1.0
    assert event_names(controller) == [f"{DIFF_SINK_HOLD_EVENT}:FR,RR:4.0"]


# --- 3: release --------------------------------------------------------------------------------


def held(params, monkeypatch, rates=(0.005, 0.0)):
    controller = watching_controller(params)
    t_s = drive(controller, list(rates), 10, monkeypatch=monkeypatch)
    assert hold(controller) is not None
    return controller, t_s


def test_3_settled_after_half_a_second(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    t_s = drive(controller, [0.0009, 0.0009], 4, t_s, monkeypatch=monkeypatch)
    assert hold(controller) is not None
    drive(controller, [0.0009, 0.0009], 1, t_s, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == f"{DIFF_SINK_RELEASE_EVENT}:settled"


def test_3_ten_seconds(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    t_s = drive(controller, [0.005, 0.0], 99, t_s, monkeypatch=monkeypatch)
    assert hold(controller) is not None
    drive(controller, [0.005, 0.0], 1, t_s, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == f"{DIFF_SINK_RELEASE_EVENT}:time"


def test_3_stroke_limit(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    limit_m = controller._diff_sink_stroke_limit_m()
    assert limit_m == pytest.approx(STROKE_LIMIT_M, abs=1e-9)
    t_s = drive(controller, [0.005, 0.0], 1, t_s, stroke_m=limit_m - 0.0001,
                monkeypatch=monkeypatch)  # 642.7 mm
    assert hold(controller) is not None
    t_s = drive(controller, [0.005, 0.0], 1, t_s, stroke_m=limit_m, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == f"{DIFF_SINK_RELEASE_EVENT}:stroke"
    drive(controller, [0.005, 0.0], 20, t_s, stroke_m=limit_m, monkeypatch=monkeypatch)
    assert hold(controller) is None  # no new hold at the limit


def test_3_leaving_level_releases_and_done_ends_the_watch(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    controller._state.phase = C2Phase.DONE
    controller._diff_sink_after_update(t_s)
    assert hold(controller) is None and controller._diff_sink_state().is_watch_over
    assert event_names(controller)[-1] == f"{DIFF_SINK_RELEASE_EVENT}:done"
    controller._state.phase = C2Phase.LEVEL
    drive(controller, [0.005, 0.0], 15, t_s, monkeypatch=monkeypatch)
    assert hold(controller) is None


# --- 4: gate -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("has_sign", "tilt_deg", "is_open"),
    [(True, 1.0, True), (True, 1.01, False), (True, -1.01, False), (True, None, False),
     (False, 0.0, False)],
)
def test_4_gate_at_the_first_loc(params, monkeypatch, has_sign, tilt_deg, is_open) -> None:
    controller = watching_controller(params)
    controller._diff_sink_state().first_loc_s = None
    settle = None if tilt_deg is None else (math.radians(tilt_deg), 0.0)
    monkeypatch.setattr(controller, "_has_loc_soil_sign", lambda: has_sign)
    monkeypatch.setattr(controller, "_settle_attitude_rad", lambda: settle)
    controller._soil_state().is_liftoff_confirmed = True
    controller._diff_sink_note_loc(10.0)
    monkeypatch.setattr(controller, "_has_loc_soil_sign", lambda: not has_sign)
    controller._diff_sink_note_loc(12.0)  # a later LOC keeps the first decision
    sink = controller._diff_sink_state()
    assert sink.first_loc_s == 10.0 and sink.is_gate_open is is_open


def test_4_no_tilt_limit_keeps_the_soil_sign_gate(params, monkeypatch) -> None:
    controller = watching_controller(params, gate_max_settle_tilt_rad=None)
    controller._diff_sink_state().first_loc_s = None
    monkeypatch.setattr(controller, "_has_loc_soil_sign", lambda: True)
    monkeypatch.setattr(controller, "_settle_attitude_rad", lambda: None)
    controller._soil_state().is_liftoff_confirmed = True
    controller._diff_sink_note_loc(10.0)
    assert controller._diff_sink_state().is_gate_open


def test_4_closed_gate_and_no_loc_never_hold(params, monkeypatch) -> None:
    controller = watching_controller(params, is_gate_open=False)
    drive(controller, [0.02, 0.02], 30, monkeypatch=monkeypatch)
    assert hold(controller) is None
    controller = watching_controller(params)
    controller._diff_sink_state().first_loc_s = None
    drive(controller, [0.02, 0.02], 30, monkeypatch=monkeypatch)
    assert hold(controller) is None and event_names(controller) == []


# --- 5: a LOC revocation does not touch the watch ----------------------------------------------


def test_5_watch_survives_a_loc_revocation(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    controller._soil_state().is_liftoff_confirmed = True
    controller._revoke_loc(t_s, 2300.0)
    sink = controller._diff_sink_state()
    assert sink.hold is not None and sink.first_loc_s == 1.0 and sink.is_gate_open


# --- 6 .. 8: reverse, cap, other legs ----------------------------------------------------------


@pytest.mark.parametrize(("reverse_m_s", "reason"), [(-0.0011, "reversed"), (-0.0009, None)])
def test_6_reverse(params, monkeypatch, reverse_m_s, reason) -> None:
    controller, t_s = held(params, monkeypatch)
    drive(controller, [reverse_m_s, 0.0], 1, t_s, monkeypatch=monkeypatch)
    if reason is None:
        assert hold(controller) is not None
    else:
        assert event_names(controller)[-1] == f"{DIFF_SINK_RELEASE_EVENT}:{reason}"


def test_6_reverse_comes_before_the_stroke_release(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch, rates=(0.0, -0.005))
    limit_m = controller._diff_sink_stroke_limit_m()
    drive(controller, [0.0, 0.002], 1, t_s, stroke_m=limit_m, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == f"{DIFF_SINK_RELEASE_EVENT}:reversed"


def test_7_added_speed_and_cap(params, monkeypatch) -> None:
    controller, _ = held(params, monkeypatch, rates=(0.005, 0.004))  # left sinks
    v_max = controller.geometry.max_speed_m_s
    command = np.full(4, 0.1 * v_max)
    out = controller._diff_sink_added_speeds(command)
    assert out[0] == pytest.approx(command[0] + 1.5 * 0.005)
    assert out[2] == pytest.approx(command[2] + 1.5 * 0.004)
    monkeypatch.setattr(controller, "_diff_sink_rates_m_s", lambda: np.array([1.0, 1.0]))
    out = controller._diff_sink_added_speeds(command)
    assert out[0] == pytest.approx(command[0] + 0.75 * v_max)
    assert out[2] == pytest.approx(command[2] + 0.75 * v_max)


def test_8_other_legs_and_an_opposite_axis_stay_bit_for_bit(params, monkeypatch) -> None:
    controller, _ = held(params, monkeypatch, rates=(0.004, 0.0))
    monkeypatch.setattr(controller, "_diff_sink_rates_m_s", lambda: np.array([0.004, -0.002]))
    command = np.array([0.0123, -0.0045, 0.0067, 0.0089])
    out = controller._diff_sink_added_speeds(command)
    assert out[0] == command[0] + min(1.5 * 0.004, 0.75 * controller.geometry.max_speed_m_s)
    assert out[1] == command[1] and out[2] == command[2] and out[3] == command[3]
    monkeypatch.setattr(controller, "_diff_sink_rates_m_s", lambda: np.array([-0.0005, -0.002]))
    np.testing.assert_array_equal(controller._diff_sink_added_speeds(command), command)


def test_wrapper_ds_token_steps_the_project_rule_aside() -> None:
    sys.path.insert(0, str(WRAPPER_DIR))
    import s9_slope_fix_candidates as fx

    preset = C2Config().with_10hz_d1()
    for token in ("DS", "DSb", "DSb75"):
        assert not fx._without_project_ds(preset, fx.parse_candidate(token)).diff_sink.enable
    assert fx._without_project_ds(preset, fx.parse_candidate("current")) is preset
    candidate_class = fx.make_candidate_class(c2_module, C2Controller, fx.parse_candidate("DSb75"))
    project_methods = {name for name in vars(C2Controller) if name.startswith("_diff_sink")}
    assert len(project_methods) >= 10
    assert not project_methods & set(vars(candidate_class))


# --- 9: wrapper hash ---------------------------------------------------------------------------

WRAPPER_CASES = (
    ("h6", "H6|J1|B|top|flat|m1.1", "regDSb75_h6.json", True),
    ("slope", "H1|J1|B|top|flat", "regDSb75_slope.json", True),
    ("slope", "H2|J1|B|bottom|roll_pos", "regDSb75_slope.json", False),
)
"""(suite, case, stored file, DS acts): a hold on H6 and on a level study-1 case, and a tilted
settle that closes the gate (424.11.2)."""


def stored_dsb75_hash(file_name: str, case_id: str) -> str | None:
    """The DSb75 row of a re-check record file, None while the file is not there."""
    path = REV83 / file_name
    if not path.exists():
        return None
    stored = json.loads(path.read_text(encoding="utf-8"))["records"]
    (reference,) = [r for r in stored if r["id"] == case_id and r["candidate"] == "DSb75"]
    return reference["hash"]


@pytest.mark.slow
def test_9_project_preset_matches_the_wrapper_dsb75_hash(tmp_path) -> None:
    """``current`` (R8 preset = 03_src DSb75) commands as the wrapper token ``DSb75`` run in the
    same job set (the token steps the project rule aside), and as the stored re-check rows."""
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_path = tmp_path / "p35.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "OMP_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run(  # the DSb75 rows predate the spec 429.11 preset switch (SGS, R4 off)
        [str(HARNESS_PYTHON), "-I", "-B", str(PRE_SWITCH_RUNNER), str(WRAPPER_SCRIPT), "run",
         "--suite", "h6,slope",
         "--candidates", "current,DSb75", "--ids", ";".join(c[1] for c in WRAPPER_CASES),
         "--workers", "4", "--out", str(out_path)],
        cwd=ROOT, env=environment, check=True, capture_output=True, timeout=1800,
    )
    records = {(r["id"], r["candidate"]): r
               for r in json.loads(out_path.read_text(encoding="utf-8"))["records"]}
    for _, case_id, file_name, is_acting in WRAPPER_CASES:
        current, token = records[(case_id, "current")], records[(case_id, "DSb75")]
        assert "error" not in current and "error" not in token, case_id
        assert current["hash"] == token["hash"], case_id
        stored = stored_dsb75_hash(file_name, case_id)
        assert stored is None or current["hash"] == stored, case_id
        holds = [name for _, name in current["metrics"]["fix_events"]
                 if name.startswith(DIFF_SINK_HOLD_EVENT)]
        assert bool(holds) is is_acting, case_id
