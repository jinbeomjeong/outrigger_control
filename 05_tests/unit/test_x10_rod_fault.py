"""X-10 rod sensor fault plan of the r79 noise runs (edition 5 6.2a.2 - 6.2a.4, 6.2a.8;
``04_scripts/03_control/s8/rod_fault_plan.py`` and its use in ``r79_sensor_screen.py``).

Unit part (no harness run): plan validation and sha, the anchors' trigger and first faulty read
(read k + 1 for tau_R), only the fault leg's rod reading changes, the record and T4h arrays, the
-100 bar D1 latch in the monitor (same read) and hydraulics test (가) (the latch read is never
the ⑤ last valid reading), the setting / plan identity guard.

Harness part (numba, one subprocess per run, all runs of the module in parallel, about 1 min):
  (i)   without a plan VBJ / VBJ0 are the commit before X-10 bit for bit (row and T4h; needs
        ``X10_BASE_ROOT`` = a checkout of that commit, skipped without it);
  (ii)  VBK0 with a plan that never arms (``t:`` after the run end) = VBJ0 of the same seed
        (new keys and the setting name aside);
  (c)   a real tau_R / tau_C fault: D1 latch on the first faulty read, the fallback starts
        there, the commands before it are the VBJ0 commands (6.2a.4 (나)), the trigger read
        is the one of the VBJ0 command / phase columns;
  (d)   the addendum 4a-2 B2 evidence equation holds on the VBK0 rows;
  (e)   the guard of both runners exits 2 (setting without plan, plan without VBK setting, an
        empty plan, plan keys other than the job keys).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (S8_DIR, COUPLED_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import r79_sensor_screen as screen  # noqa: E402
import rod_fault_plan as rfp  # noqa: E402

from outrigger_sim.control.c2 import C2Config  # noqa: E402
from outrigger_sim.control.two_pressure import (  # noqa: E402
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.signals import Measurements  # noqa: E402

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
F_MIN_N = 9414.59
STROKE_MAX_M = 0.70
FR = 1
U_HOLD = 0.01 * V_MAX
GATE_VALUE_BAR = -100.0
RUN_KEY = "cand=current#L2|s30|ref|0|rigid|B|0,0"
"""A short ref key (rigid, pad B, flat; about 40 s): READY within the run, a retract carry
after LEVEL on FR, CHECK on (L2)."""
RUN_TIMEOUT_S = 1200
BASE_ROOT_ENV = "X10_BASE_ROOT"
"""A checkout of the commit before X-10 (df95158d) for (i); the test is skipped without it."""
VOLATILE_ROW_KEYS = ("wall_s",)
NEW_T4H_ARRAYS = ("rod_pressure_pre_fault_Pa", "rod_fault_applied")


# ------------------------------------------------------------------------------- plan files
def _fault(**changes) -> dict:
    entry = {"fault_id": "x10-test", "leg": "FR", "kind": "STUCK",
             "value_bar": GATE_VALUE_BAR, "anchor": "retract_start_after:LEVEL",
             "delay_reads": 0}
    return {**entry, **changes}


def _write_plan(path: Path, faults: dict | None = None, **top) -> Path:
    document = {"schema": rfp.PLAN_SCHEMA, "faults": faults if faults is not None
                else {RUN_KEY: _fault()}, **top}
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_plan_is_read_with_its_sha256_and_meta(tmp_path) -> None:
    path = _write_plan(tmp_path / "plan.json")
    plan = rfp.load_plan(path)
    assert plan.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert plan.meta() == {"path": str(path), "sha256": plan.sha256, "n_faults": 1,
                           "schema": rfp.PLAN_SCHEMA}
    fault = plan.fault_for(RUN_KEY)
    assert (fault.leg_index, fault.value_Pa, fault.kind) == (FR, -100e5, rfp.FaultKind.STUCK)
    assert fault.anchor.kind is rfp.AnchorKind.RETRACT_START_AFTER_LEVEL


@pytest.mark.parametrize(("text", "match"), [
    ("not json", "cannot be read"),
    (json.dumps({"schema": rfp.PLAN_SCHEMA}), "top-level keys"),
    (json.dumps({"schema": rfp.PLAN_SCHEMA, "faults": {RUN_KEY: _fault()}, "x": 1}),
     "top-level keys"),
    (json.dumps({"schema": "r79_rod_fault_plan/0", "faults": {RUN_KEY: _fault()}}), "schema"),
    (json.dumps({"schema": rfp.PLAN_SCHEMA, "faults": {}}), "empty plan"),
    (json.dumps({"schema": rfp.PLAN_SCHEMA, "faults": []}), "non-empty object"),
    ('{"schema": "r79_rod_fault_plan/1", "schema": "r79_rod_fault_plan/1", "faults": {}}',
     "repeated JSON keys"),
])
def test_plan_file_errors(tmp_path, text, match) -> None:
    path = tmp_path / "plan.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(rfp.RodFaultPlanError, match=match):
        rfp.load_plan(path)


def _without(key: str) -> dict:
    entry = _fault()
    entry.pop(key)
    return entry


@pytest.mark.parametrize(("entry", "match"), [
    (_without("delay_reads"), "keys missing"),
    ({**_fault(), "note": "x"}, "extra"),
    (_fault(leg="F1"), "leg"),
    (_fault(kind="OFFSET"), "kind"),
    (_fault(value_bar=None), "finite number"),
    (_fault(value_bar=float("nan")), "finite number"),
    (_fault(value_bar=True), "finite number"),
    (_fault(kind="DROPOUT"), "value_bar null"),
    (_fault(delay_reads=-1), "delay_reads"),
    (_fault(delay_reads=1.0), "delay_reads"),
    (_fault(delay_reads=True), "delay_reads"),
    (_fault(anchor="phase_exit:LEVEL"), "unknown anchor"),
    (_fault(anchor="t:-1"), "unknown anchor"),
    (_fault(anchor=3), "anchor must be a string"),
    (_fault(fault_id=""), "fault_id"),
])
def test_plan_entry_errors(tmp_path, entry, match) -> None:
    with pytest.raises(rfp.RodFaultPlanError, match=match):
        rfp.load_plan(_write_plan(tmp_path / "plan.json", {RUN_KEY: entry}))


def test_repeated_fault_ids_are_refused(tmp_path) -> None:
    faults = {RUN_KEY: _fault(), RUN_KEY + "x": _fault()}
    with pytest.raises(rfp.RodFaultPlanError, match="repeated fault_id"):
        rfp.load_plan(_write_plan(tmp_path / "plan.json", faults))


def test_dropout_and_time_anchors_parse(tmp_path) -> None:
    faults = {RUN_KEY: _fault(kind="DROPOUT", value_bar=None, anchor="t:12.5", delay_reads=2)}
    fault = rfp.load_plan(_write_plan(tmp_path / "plan.json", faults)).fault_for(RUN_KEY)
    assert math.isnan(fault.value_Pa) and fault.anchor.time_s == 12.5
    assert rfp.parse_anchor("t:1e6").time_s == 1e6


def test_key_problems_name_missing_and_extra_keys(tmp_path) -> None:
    plan = rfp.load_plan(_write_plan(tmp_path / "plan.json"))
    assert plan.key_problems([RUN_KEY]) == []
    missing = plan.key_problems([RUN_KEY, "other"])
    extra = plan.key_problems([])
    assert len(missing) == 1 and "without a fault" in missing[0]
    assert len(extra) == 1 and "no job of the run" in extra[0]
    with pytest.raises(rfp.RodFaultPlanError, match="no fault"):
        plan.fault_for("other")


def test_hold_speed_is_the_rev5_ratio_of_the_yaml_v_max() -> None:
    from outrigger_sim.control.extend_start_bound import HOLD_SPEED_RATIO
    from outrigger_sim.params import load_params

    expected = HOLD_SPEED_RATIO * load_params().actuator.max_speed_m_s
    assert rfp.hold_speed_m_s() == expected
    assert rfp.hold_speed_m_s() == pytest.approx(0.20924e-3, abs=1e-8)


# ------------------------------------------------------------------------------- injector
class FakeController:
    """The parts of a ``LoggedController`` the injector reads: phase in effect, the 10 Hz log
    (t, phase after the update, command), events and the annulus areas."""

    def __init__(self) -> None:
        self.phase = "check"
        self.events: list[SimpleNamespace] = []
        self.geometry = SimpleNamespace(annulus_area_m2=ANNULUS)

    def update(self, t_s: float, phase_after: str, command: np.ndarray) -> None:
        self.__dict__.setdefault("period_log", []).append((t_s, phase_after, command.copy()))
        self.phase = phase_after


def _measurements(t_s: float, rod_bar: float = 5.0) -> Measurements:
    rod = np.array([rod_bar, rod_bar + 1.0, rod_bar + 2.0, rod_bar + 3.0]) * BAR
    return Measurements(t_s=t_s, specific_force_m_s2=np.array([0.0, 0.0, 9.81]),
                        angular_rate_rad_s=np.zeros(3), head_pressure_Pa=np.full(4, 80 * BAR),
                        stroke_m=np.full(4, 0.3), rod_pressure_Pa=rod)


def _drive(injector, phases: list[str], commands_fr: list[float]):
    """Reads 0 .. n-1 with update k leaving phase ``phases[k]`` and FR command
    ``commands_fr[k]``; returns the controller and the measurements the controller read."""
    ctrl = FakeController()
    read = []
    for k, (phase, command) in enumerate(zip(phases, commands_fr, strict=True)):
        delivered = injector.apply(ctrl, _measurements(k * PERIOD_S))
        read.append(delivered)
        commands = np.zeros(4)
        commands[FR] = command
        ctrl.update(k * PERIOD_S, phase, commands)
    return ctrl, read


def _injector(anchor: str, delay_reads: int = 0, kind=rfp.FaultKind.STUCK, value=-100.0):
    fault = rfp.RodFault(RUN_KEY, "unit", "FR", kind, value, rfp.parse_anchor(anchor),
                         delay_reads)
    return rfp.RodFaultInjector(fault, "sha", U_HOLD)


PHASES = ["check"] * 4 + ["level"] * 4 + ["probe"] * 4
"""Phase after update k: update 4 leaves CHECK, so read 5 is the first read in effect outside
it (reads 0 .. 4 are read in CHECK)."""
FIRST_OUTSIDE_CHECK = 5


def _first_faulty(read: list[Measurements]) -> int:
    return next(k for k, m in enumerate(read) if m.rod_pressure_Pa[FR] == -100 * BAR)


def test_phase_exit_check_arms_on_the_first_read_in_effect_outside_check() -> None:
    injector = _injector("phase_exit:CHECK")
    _, read = _drive(injector, PHASES, [0.0] * len(PHASES))
    assert injector.trigger_read == injector.first_applied_read == FIRST_OUTSIDE_CHECK
    assert injector.armed_t_s == pytest.approx(0.5)
    assert _first_faulty(read) == FIRST_OUTSIDE_CHECK


def test_phase_enter_check_is_faulty_from_read_zero() -> None:
    injector = _injector("phase_enter:CHECK")
    _, read = _drive(injector, PHASES, [0.0] * len(PHASES))
    assert (injector.trigger_read, injector.first_applied_read, _first_faulty(read)) == (0, 0, 0)


def test_time_anchor_and_delay() -> None:
    injector = _injector("t:0.5", delay_reads=2)
    _, read = _drive(injector, PHASES, [0.0] * len(PHASES))
    assert (injector.trigger_read, injector.first_applied_read, _first_faulty(read)) == (5, 7, 7)


def test_time_anchor_after_the_run_never_arms() -> None:
    injector = _injector("t:1000000")
    ctrl, read = _drive(injector, PHASES, [0.0] * len(PHASES))
    record = injector.record(ctrl)
    assert not record["is_armed"] and record["applied_periods"] == 0
    assert record["first_applied_read"] is None and record["latched"]["is_latched"] is False
    assert record["rod_fault_sum_offset_N"] is None
    assert all(m.rod_pressure_Pa[FR] == 6 * BAR for m in read)


def test_retract_start_after_level_triggers_on_k_and_faults_from_k_plus_1() -> None:
    """Update 2 retracts before LEVEL (ignored); LEVEL from update 4; update 5 holds exactly at
    u_hold (counts as hold), update 6 retracts at exactly -u_hold (no carry), update 7 holds,
    update 8 retracts: trigger read 8, faulty from read 9."""
    commands = [0.0, 0.0, -5e-3, 0.0, 0.0, U_HOLD, -U_HOLD, 0.0, -5e-3, -5e-3, 0.0, 0.0]
    injector = _injector("retract_start_after:LEVEL")
    ctrl, read = _drive(injector, PHASES, commands)
    assert (injector.trigger_read, injector.first_applied_read, _first_faulty(read)) == (8, 9, 9)
    assert injector.armed_t_s == pytest.approx(0.8)
    assert injector.first_applied_t_s == pytest.approx(0.9)
    expected = np.array([row[2] for row in ctrl.period_log[:9]], float).reshape(-1, 4)
    assert injector.pre_trigger_commands_sha256 == hashlib.sha256(expected.tobytes()).hexdigest()
    assert injector.pre_trigger_commands_sha256 == rfp.commands_sha256(ctrl.period_log, 9)


def test_retract_trigger_right_at_the_first_level_update() -> None:
    """``k >= first LEVEL update``: a carry starting on that very update triggers."""
    phases = ["check", "check", "level", "level", "level"]
    injector = _injector("retract_start_after:LEVEL")
    _drive(injector, phases, [0.0, 0.0, -5e-3, 0.0, 0.0])
    assert (injector.trigger_read, injector.first_applied_read) == (2, 3)


def test_retract_without_a_carry_start_never_arms() -> None:
    injector = _injector("retract_start_after:LEVEL")
    ctrl, _ = _drive(injector, PHASES, [0.0] * 6 + [5e-3] * 6)
    assert injector.record(ctrl)["is_armed"] is False


def test_only_the_fault_legs_rod_reading_changes() -> None:
    injector = _injector("phase_exit:CHECK")
    ctrl, read = _drive(injector, PHASES, [0.0] * len(PHASES))
    for k, delivered in enumerate(read):
        clean = _measurements(k * PERIOD_S)
        np.testing.assert_array_equal(delivered.head_pressure_Pa, clean.head_pressure_Pa)
        others = [leg for leg in range(4) if leg != FR]
        np.testing.assert_array_equal(delivered.rod_pressure_Pa[others],
                                      clean.rod_pressure_Pa[others])
        np.testing.assert_array_equal(injector.pre_fault_rod_Pa[k], clean.rod_pressure_Pa)
        is_faulty = k >= FIRST_OUTSIDE_CHECK
        expected_fr = -100 * BAR if is_faulty else clean.rod_pressure_Pa[FR]
        assert delivered.rod_pressure_Pa[FR] == expected_fr
    offset = injector.record(ctrl)["rod_fault_sum_offset_N"]
    assert offset["n_reads"] == len(PHASES) - FIRST_OUTSIDE_CHECK
    assert offset["first_N"] == pytest.approx(-ANNULUS[FR] * (-100 * BAR - 6 * BAR))


def test_dropout_gives_nan_and_no_finite_offset() -> None:
    injector = _injector("phase_exit:CHECK", kind=rfp.FaultKind.DROPOUT, value=None)
    ctrl, read = _drive(injector, PHASES, [0.0] * len(PHASES))
    assert math.isnan(read[5].rod_pressure_Pa[FR])
    offset = injector.record(ctrl)["rod_fault_sum_offset_N"]
    assert offset["n_finite"] == 0 and offset["first_N"] is None


def test_record_latch_fallback_and_t4h_arrays() -> None:
    injector = _injector("phase_exit:CHECK")
    ctrl = FakeController()
    ctrl.events.append(SimpleNamespace(t_s=0.1, name="WARN_ROD_PRESSURE_FALLBACK:RL"))
    for k, phase in enumerate(PHASES):
        injector.apply(ctrl, _measurements(k * PERIOD_S))
        if k == FIRST_OUTSIDE_CHECK:  # the monitor latches the leg on the first faulty read
            ctrl.events += [SimpleNamespace(t_s=0.5, name="WARN_ROD_PRESSURE_FALLBACK:FR"),
                            SimpleNamespace(t_s=0.5,
                                            name="INFO_ROD_PRESSURE_FAULT_REASON:FR:D1")]
        ctrl.update(k * PERIOD_S, phase, np.zeros(4))
    record = injector.record(ctrl)
    assert set(record) == {
        "plan_sha256", "fault_id", "leg", "kind", "value", "value_unit", "anchor",
        "delay_reads", "hold_speed_m_s", "hold_speed_source", "is_armed", "trigger_read",
        "armed_t_s", "first_applied_read", "first_applied_t_s", "applied_periods", "latched",
        "pre_trigger_commands_sha256", "pre_trigger_fallback", "pre_trigger_fallback_events",
        "rod_fault_sum_offset_N", "reads", "updates"}
    assert record["latched"] == {"is_latched": True, "reason": "D1", "t_s": 0.5,
                                 "reads_after_first": 0, "is_same_read_d1": True}
    assert record["pre_trigger_fallback"] is True
    assert record["pre_trigger_fallback_events"] == [(0.1, "WARN_ROD_PRESSURE_FALLBACK:RL")]
    assert (record["applied_periods"], record["reads"], record["updates"]) == (7, 12, 12)
    period_t = np.array([row[0] for row in ctrl.period_log])
    arrays = injector.t4h_arrays(np.r_[period_t, 99.0])  # a row without a delivered read
    assert arrays["rod_fault_applied"][:, FR].tolist() == [False] * 5 + [True] * 7 + [False]
    assert not arrays["rod_fault_applied"][:, [0, 2, 3]].any()
    assert np.isnan(arrays["rod_pressure_pre_fault_Pa"][-1]).all()
    assert arrays["rod_pressure_pre_fault_Pa"][5, FR] == 6 * BAR


def test_no_rod_channel_is_an_error() -> None:
    injector = _injector("phase_exit:CHECK")
    plain = Measurements(t_s=0.0, specific_force_m_s2=np.array([0.0, 0.0, 9.81]),
                         angular_rate_rad_s=np.zeros(3), head_pressure_Pa=np.full(4, 80 * BAR),
                         stroke_m=np.full(4, 0.3))
    with pytest.raises(RuntimeError, match="no rod reading"):
        injector.apply(FakeController(), plain)


def test_tau_r_without_the_command_log_is_an_error() -> None:
    injector = _injector("retract_start_after:LEVEL")
    ctrl = FakeController()
    injector.apply(ctrl, _measurements(0.0))
    with pytest.raises(RuntimeError, match="command log"):
        injector.apply(ctrl, _measurements(0.1))


# ------------------------------------------------------------------------------- monitor latch
def _monitor(settings: TwoPressureSettings | None = None) -> TwoPressureMonitor:
    settings = settings or C2Config().with_10hz_d1().two_pressure
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              stroke_max_m=STROKE_MAX_M)


def _hold_settings() -> TwoPressureSettings:
    from dataclasses import replace

    from outrigger_sim.control.extend_start_bound import EXTEND_HOLD_REVISION, ExtendStartBound

    return replace(C2Config().with_10hz_d1().two_pressure, extend_start_rule="tracked_bound",
                   extend_start_bound=ExtendStartBound(revision=EXTEND_HOLD_REVISION))


@pytest.mark.parametrize("settings", [None, "hold"], ids=["preset_column_bound", "rev5_hold"])
def test_minus_100_bar_latches_d1_on_that_read_and_is_never_the_last_valid_reading(
        settings) -> None:
    """6.2a.2 latch and hydraulics test (가): locked FR reads 120 bar, then -100 bar. The same
    read falls back with reason D1, and ⑤ keeps the 120 bar reading (the latch comes first)."""
    monitor = _monitor(None if settings is None else _hold_settings())
    head, rod, stroke = np.full(4, 100 * BAR), np.full(4, 120 * BAR), np.full(4, 0.40)
    monitor.read(0.0, head, rod, np.full(4, 0.5 * V_MAX), False, 2e3, stroke_m=stroke)
    for k in range(1, 15):
        monitor.read(k * PERIOD_S, head, rod, np.zeros(4), False, 2e3, stroke_m=stroke)
    stretch = monitor._stretch_states()[FR]
    assert stretch.valid_rod_Pa == 120 * BAR
    monitor.pop_events()
    faulty = rod.copy()
    faulty[FR] = -100 * BAR
    monitor.read(1.5, head, faulty, np.zeros(4), False, 2e3, stroke_m=stroke)
    assert monitor.rod_state[FR] is RodSensorState.FALLBACK
    assert all(monitor.rod_state[leg] is RodSensorState.OK for leg in (0, 2, 3))
    names = [name for name, _ in monitor.pop_events()]
    assert "WARN_ROD_PRESSURE_FALLBACK:FR" in names
    assert "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1" in names
    assert monitor._stretch_states()[FR].valid_rod_Pa == 120 * BAR


# ------------------------------------------------------------------------------- guard
@pytest.fixture()
def guard_env(monkeypatch):
    """A clean plan cache and no X-10 / v5 variables."""
    monkeypatch.setattr(screen, "_ROD_FAULT_PLANS", {})
    for name in (screen.V5_SETTING_ENV, screen.ROD_FAULT_PLAN_ENV,
                 screen.ROD_FAULT_PLAN_SHA256_ENV):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_guard_without_plan_and_setting_is_silent(guard_env) -> None:
    guard_env.setenv(screen.V5_SETTING_ENV, "VBJ0")
    assert screen.rod_fault_plan_problems([RUN_KEY]) == []
    assert screen.apply_rod_fault_guard([RUN_KEY]) is None
    assert screen.rod_fault_injector(RUN_KEY) is None
    guard_env.setenv(screen.ROD_FAULT_PLAN_ENV, "")  # a runner's restored unset variable
    assert screen.rod_fault_injector(RUN_KEY) is None


@pytest.mark.parametrize(("setting", "has_plan", "match"), [
    ("VBK0", False, "needs R79_ROD_FAULT_PLAN"),
    ("VBJ0", True, "is no VBK setting"),
    (None, True, "is no VBK setting"),
])
def test_guard_refuses_setting_and_plan_apart(guard_env, tmp_path, setting, has_plan,
                                              match) -> None:
    if setting is not None:
        guard_env.setenv(screen.V5_SETTING_ENV, setting)
    if has_plan:
        guard_env.setenv(screen.ROD_FAULT_PLAN_ENV, str(_write_plan(tmp_path / "plan.json")))
    assert match in screen.rod_fault_plan_problems([RUN_KEY])[0]
    with pytest.raises(SystemExit) as stop:
        screen.apply_rod_fault_guard([RUN_KEY])
    assert stop.value.code == screen.ROD_FAULT_GUARD_EXIT == 2
    with pytest.raises(ValueError, match=match):
        screen.rod_fault_injector(RUN_KEY)


@pytest.mark.parametrize(("faults", "keys", "match"), [
    ({}, [RUN_KEY], "empty plan"),
    ({RUN_KEY: _fault()}, [RUN_KEY, RUN_KEY + "2"], "without a fault"),
    ({RUN_KEY: _fault(), "other": _fault(fault_id="b")}, [RUN_KEY], "no job of the run"),
])
def test_guard_refuses_empty_plans_and_other_keys(guard_env, tmp_path, faults, keys,
                                                  match) -> None:
    guard_env.setenv(screen.V5_SETTING_ENV, "VBK0")
    guard_env.setenv(screen.ROD_FAULT_PLAN_ENV, str(_write_plan(tmp_path / "plan.json", faults)))
    assert any(match in text for text in screen.rod_fault_plan_problems(keys))
    with pytest.raises(SystemExit) as stop:
        screen.apply_rod_fault_guard(keys)
    assert stop.value.code == 2


def test_guard_passes_pins_the_sha_and_workers_check_it(guard_env, tmp_path) -> None:
    path = _write_plan(tmp_path / "plan.json")
    guard_env.setenv(screen.V5_SETTING_ENV, "VBK0")
    guard_env.setenv(screen.ROD_FAULT_PLAN_ENV, str(path))
    meta = screen.apply_rod_fault_guard([RUN_KEY])
    assert meta == rfp.load_plan(path).meta()
    assert os.environ[screen.ROD_FAULT_PLAN_SHA256_ENV] == meta["sha256"]
    injector = screen.rod_fault_injector(RUN_KEY)
    assert injector.fault.fault_id == "x10-test" and injector.plan_sha256 == meta["sha256"]
    with pytest.raises(rfp.RodFaultPlanError, match="no fault"):
        screen.rod_fault_injector("another key")
    guard_env.setenv(screen.ROD_FAULT_PLAN_SHA256_ENV, "0" * 64)
    with pytest.raises(ValueError, match="is not the checked"):
        screen.rod_fault_injector(RUN_KEY)


def test_vbk_vbk0_are_the_vbj_vbj0_options_and_rod_fault_settings() -> None:
    import j_p3_inputs
    import run_v5

    assert run_v5.JP3_SETTINGS["VBK0"] == run_v5.JP3_SETTINGS["VBJ0"]
    assert run_v5.JP3_SETTINGS["VBK"] == run_v5.JP3_SETTINGS["VBJ"]  # ③ rev 6 (edition 5)
    assert all(screen.is_rod_fault_setting(name) for name in run_v5.ROD_FAULT_SETTINGS)
    assert not any(screen.is_rod_fault_setting(name) for name in run_v5.ALL_SETTINGS
                   if name not in run_v5.ROD_FAULT_SETTINGS)
    assert not j_p3_inputs.is_p3_expected(None, "VBK0")  # ③ off, never a J-P3 row
    assert j_p3_inputs.is_p3_expected(None, "VBK")


def test_common_ps1_runs_vbk_and_vbk0_with_plant_truth() -> None:
    text = (ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9" / "run_steps"
            / "common.ps1").read_text(encoding="utf-8")
    assert "VBK0 = 'plant_truth'" in text and "'R79_ROD_FAULT_PLAN'" in text
    assert "VBK = 'plant_truth'" in text


# ------------------------------------------------------------------------------- X-10 extension
def _drive_with_strokes(injector, phases, commands_fr, strokes_fr):
    """:func:`_drive` with a delivered ``stroke_m`` per read (FR column ``strokes_fr[k]``)."""
    ctrl = FakeController()
    read = []
    for k, (phase, command) in enumerate(zip(phases, commands_fr, strict=True)):
        measured = _measurements(k * PERIOD_S)
        stroke = np.full(4, 0.3)
        stroke[FR] = strokes_fr[k]
        measured = Measurements(t_s=measured.t_s, specific_force_m_s2=measured.specific_force_m_s2,
                                angular_rate_rad_s=measured.angular_rate_rad_s,
                                head_pressure_Pa=measured.head_pressure_Pa, stroke_m=stroke,
                                rod_pressure_Pa=measured.rod_pressure_Pa)
        read.append(injector.apply(ctrl, measured))
        commands = np.zeros(4)
        commands[FR] = command
        ctrl.update(k * PERIOD_S, phase, commands)
    return ctrl, read


TRW_PHASES = ["check"] * 3 + ["level"] * 17
TRW_COMMANDS = ([0.0] * 4 + [-5e-3] * 3 + [0.0] * 2 + [-5e-3] * 6 + [0.0] * 5)
"""Carry A (updates 4 .. 6) moves 0.8 mm only; carry B (updates 9 .. 14) is witnessed."""
TRW_STROKES = ([0.40] * 5 + [0.3996, 0.3992] + [0.3992] * 3
               + [0.3986, 0.3984, 0.3978, 0.3970, 0.3960] + [0.3960] * 5)


def test_trw_anchor_is_the_first_witnessed_retract_carry() -> None:
    """Edition 5 6.3.3 TRw: carry B starts at update 9 (s_ref = read 9, 0.3992); read 12
    reaches 1.4 mm with u_12 < -u_hold: trigger read 12, faulty from read 13."""
    injector = _injector("retract_witness_after:LEVEL")
    ctrl, read = _drive_with_strokes(injector, TRW_PHASES, TRW_COMMANDS, TRW_STROKES)
    assert (injector.trigger_read, injector.first_applied_read, _first_faulty(read)) == (
        12, 13, 13)
    record = injector.record(ctrl)
    assert record["witness"] == {"carry_start_read": 9, "witness_read": 12,
                                 "witness_ref_m": 0.3992,
                                 "witness_ds_m": pytest.approx(1.4e-3)}
    assert record["anchor"] == "retract_witness_after:LEVEL"


def test_trw_offline_function_agrees_with_the_injector() -> None:
    """The record function of the gate judge (``retract_witnesses``) gives the injector's
    trigger on the same columns, also on random command / stroke sequences."""
    arrays_phase = np.array(TRW_PHASES)
    commands = np.zeros((len(TRW_COMMANDS), 4))
    commands[:, FR] = TRW_COMMANDS
    strokes = np.full((len(TRW_STROKES), 4), 0.3)
    strokes[:, FR] = TRW_STROKES
    assert rfp.retract_witnesses(arrays_phase, commands, strokes, FR, U_HOLD)[0] == (9, 12)
    rng = np.random.default_rng(11)
    armed = 0
    for _ in range(40):
        size = 60
        phases = ["check"] * 5 + ["level"] * (size - 5)
        command_fr = rng.choice([0.0, -1e-4, -5e-3, 5e-3], size=size, p=[0.35, 0.1, 0.45, 0.1])
        stroke_fr = 0.40 + np.cumsum(np.where(command_fr < -U_HOLD, -4e-4, 0.0)) \
            + rng.normal(0.0, 1e-4, size)
        injector = _injector("retract_witness_after:LEVEL")
        _drive_with_strokes(injector, phases, list(command_fr), list(stroke_fr))
        commands = np.zeros((size, 4))
        commands[:, FR] = command_fr
        strokes = np.full((size, 4), 0.3)
        strokes[:, FR] = stroke_fr
        found = rfp.retract_witnesses(np.array(phases), commands, strokes, FR, U_HOLD)
        # a witness on the last read arms only at a read the run never delivers
        expected = found[0][1] if found and found[0][1] < size - 1 else None
        assert injector.trigger_read == expected
        if expected is not None:
            assert injector.first_applied_read == expected + 1
            armed += 1
    assert 10 <= armed < 40  # both outcomes occur


def test_trw_counts_witnesses_after_a_read() -> None:
    commands = np.zeros((len(TRW_COMMANDS), 4))
    commands[:, FR] = TRW_COMMANDS
    strokes = np.full((len(TRW_STROKES), 4), 0.3)
    strokes[:, FR] = TRW_STROKES
    assert rfp.retract_witnesses(np.array(TRW_PHASES), commands, strokes, FR, U_HOLD,
                                 from_read=12) == [(9, 12)]
    # the carry's witness read is 12: it does not count again from read 13 on
    assert rfp.retract_witnesses(np.array(TRW_PHASES), commands, strokes, FR, U_HOLD,
                                 from_read=13) == []
    assert rfp.retract_witnesses(np.array(["check"] * 20), commands, strokes, FR, U_HOLD) == []


@pytest.mark.parametrize("anchor", ["phase_exit:CHECK", "retract_start_after:LEVEL",
                                    "retract_witness_after:LEVEL"])
def test_gate_anchor_with_a_delay_is_refused(tmp_path, anchor) -> None:
    """Audit W2 / 6.3.2: a gate plan needs ``delay_reads`` 0."""
    with pytest.raises(rfp.RodFaultPlanError, match="needs delay_reads 0"):
        rfp.load_plan(_write_plan(tmp_path / "plan.json",
                                  {RUN_KEY: _fault(anchor=anchor, delay_reads=1)}))
    rfp.load_plan(_write_plan(tmp_path / "ok.json", {RUN_KEY: _fault(anchor=anchor)}))
    rfp.load_plan(_write_plan(tmp_path / "ck.json",
                              {RUN_KEY: _fault(anchor="phase_enter:CHECK", delay_reads=2)}))


@pytest.mark.parametrize(("events", "expected"), [
    ([(0.5, "D1")], True),
    ([(0.6, "D1")], False),  # a later latch
    ([(0.5, "D1_stuck")], False),  # another reason
    ([], False),
])
def test_latch_is_the_same_read_d1_only(events, expected) -> None:
    """Audit B3: only a D1 reason on the first faulty read itself is a latch."""
    injector = _injector("phase_exit:CHECK")
    ctrl = FakeController()
    for k, phase in enumerate(PHASES):
        injector.apply(ctrl, _measurements(k * PERIOD_S))
        for t_s, reason in events:
            if abs(k * PERIOD_S - t_s) < 1e-9:
                ctrl.events.append(SimpleNamespace(
                    t_s=t_s, name=f"INFO_ROD_PRESSURE_FAULT_REASON:FR:{reason}"))
        ctrl.update(k * PERIOD_S, phase, np.zeros(4))
    assert injector.record(ctrl)["latched"]["is_same_read_d1"] is expected


# ------------------------------------------------------------------------------- harness runs
REV5_ALIAS = "VBJ5"
"""The edition 4a revision 5 VBJ on the edition 5 code (``rod_fault_runner`` alias, test only)."""
TRW_KEY = "cand=current#L2|s30|ref|3|rigid|B|0,3.2"
"""A short ref key (pitch 3.2 deg) whose VBJ run has a witnessed retract carry on RL after LEVEL
(probe run of this commit: carry start 373, witness 388); :data:`RUN_KEY` has none."""
TRW_LEG = "RL"


def _run_environment(setting: str, t4h_dir: Path, plan: Path | None) -> dict:
    environment = {name: value for name, value in os.environ.items()
                   if not name.startswith(("R79_", "R72_", "R67_", "LAS_T3_", "X10_"))}
    environment.update(PYTHONDONTWRITEBYTECODE="1", MKL_THREADING_LAYER="TBB",
                       OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", R72_PATH="per_leg",
                       R79_ROD_MODEL="plant_truth", R79_V5_SETTING=setting,
                       R79_T4H_DIR=str(t4h_dir))
    if plan is not None:
        environment["R79_ROD_FAULT_PLAN"] = str(plan)
    if setting == REV5_ALIAS:
        environment["X10_REV5_ALIAS"] = f"{REV5_ALIAS}=VBJ"
    return environment


def _start_run(root: Path, folder: Path, label: str, setting: str, plan: Path | None,
               key: str = RUN_KEY):
    out = folder / f"{label}.json"
    process = subprocess.Popen(
        [sys.executable, "-I", "-B", str(ROOT / "05_tests" / "unit" / "rod_fault_runner.py"),
         str(root), key, str(out)], cwd=root, env=_run_environment(
            setting, folder / f"{label}_t4h", plan),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process, out


@pytest.fixture(scope="module")
def runs(tmp_path_factory) -> dict:
    """Every harness run of this module, started together: label -> (row, T4h path, runner
    line)."""
    pytest.importorskip("numba", reason="harness run (r79 imports the harness lazily)")
    folder = tmp_path_factory.mktemp("x10_runs")
    plans = {
        "unarmed": _write_plan(folder / "unarmed.json", {RUN_KEY: _fault(anchor="t:1000000")}),
        "tau_r": _write_plan(folder / "tau_r.json", {RUN_KEY: _fault()}),
        "tau_c": _write_plan(folder / "tau_c.json",
                             {RUN_KEY: _fault(leg="RL", anchor="phase_exit:CHECK")}),
        "trw": _write_plan(folder / "trw.json",
                           {TRW_KEY: _fault(leg=TRW_LEG, anchor="retract_witness_after:LEVEL")}),
    }
    specs = {"VBJ": (ROOT, "VBJ", None, RUN_KEY), "VBJ0": (ROOT, "VBJ0", None, RUN_KEY),
             REV5_ALIAS: (ROOT, REV5_ALIAS, None, RUN_KEY),
             "VBK0_unarmed": (ROOT, "VBK0", plans["unarmed"], RUN_KEY),
             "VBK0_tau_r": (ROOT, "VBK0", plans["tau_r"], RUN_KEY),
             "VBK0_tau_c": (ROOT, "VBK0", plans["tau_c"], RUN_KEY),
             "VBK_unarmed": (ROOT, "VBK", plans["unarmed"], RUN_KEY),
             "VBJ_trw_key": (ROOT, "VBJ", None, TRW_KEY),
             "VBK_trw": (ROOT, "VBK", plans["trw"], TRW_KEY),
             "VBK0_trw": (ROOT, "VBK0", plans["trw"], TRW_KEY)}
    base_root = os.environ.get(BASE_ROOT_ENV)
    if base_root:
        specs.update({"base_VBJ": (Path(base_root), "VBJ", None, RUN_KEY),
                      "base_VBJ0": (Path(base_root), "VBJ0", None, RUN_KEY)})
    started = {label: _start_run(root, folder, label, setting, plan, key)
               for label, (root, setting, plan, key) in specs.items()}
    results = {}
    for label, (process, out) in started.items():
        stdout, stderr = process.communicate(timeout=RUN_TIMEOUT_S)
        assert process.returncode == 0, f"{label}: {stderr[-2000:]}"
        line = json.loads(stdout.strip().splitlines()[-1])
        row = json.loads(out.read_text(encoding="utf-8"))
        assert row.get("error") is None, f"{label}: {row.get('error')}"
        results[label] = (row, folder / f"{label}_t4h" / row["t4h_file"], line)
    return results


def _without_wall_times(value):
    """``value`` without any ``wall_s`` key at any depth (the run row and its harness
    ``base`` record both time themselves)."""
    if isinstance(value, dict):
        return {key: _without_wall_times(item) for key, item in value.items()
                if key not in VOLATILE_ROW_KEYS}
    if isinstance(value, list):
        return [_without_wall_times(item) for item in value]
    return value


def _canonical(row: dict, drop: tuple[str, ...] = ()) -> str:
    """The row as sorted JSON without wall times and the top-level ``drop`` keys (NaN
    compares equal as text)."""
    kept = {key: value for key, value in row.items() if key not in drop}
    return json.dumps(_without_wall_times(kept), sort_keys=True)


def _t4h(path: Path) -> tuple[dict, dict]:
    with np.load(path, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files if name != "meta_json"}
        meta = json.loads(str(data["meta_json"]))
    return arrays, meta


def _arrays_equal(left: dict, right: dict) -> list[str]:
    """Names of the arrays that differ (shape, dtype or values; NaN equal to NaN)."""
    different = sorted(set(left) ^ set(right))
    for name in sorted(set(left) & set(right)):
        a, b = left[name], right[name]
        is_float = np.issubdtype(a.dtype, np.floating)
        if a.shape != b.shape or a.dtype != b.dtype or not np.array_equal(
                a, b, equal_nan=is_float):
            different.append(name)
    return different


NEW_ROW_KEYS = ("run_extend_start_rule", "run_extend_start_revision")
"""Edition 5 line keys of a ③-on r79 row (4.6); the new T4h arrays are the ``jp3_*`` of X-1."""


def _without_new_t4h_arrays(arrays: dict) -> dict:
    return {name: value for name, value in arrays.items() if not name.startswith("jp3_")}


@pytest.mark.parametrize(("setting", "base_setting"), [(REV5_ALIAS, "VBJ"), ("VBJ0", "VBJ0")])
def test_i_without_a_plan_the_rows_are_the_commit_before_x10(runs, setting,
                                                             base_setting) -> None:
    """7.2 X-10 (i): without a plan VBJ (③ rev 5, the edition 4a options) and VBJ0 give the
    row (``wall_s``, the setting name and the new edition 5 keys aside) and the T4h record
    (the new ``jp3_*`` arrays aside) of the commit before X-10, and the plan module is not
    imported."""
    row, t4h_path, line = runs[setting]
    assert line["rod_fault_imported"] is False
    assert screen.ROD_FAULT_KEY not in row
    _, meta = _t4h(t4h_path)
    assert not {screen.ROD_FAULT_KEY, screen.ROD_FAULT_PLAN_KEY} & set(meta)
    if f"base_{base_setting}" not in runs:
        pytest.skip(f"{BASE_ROOT_ENV} not set (a checkout of the commit before X-10)")
    base_row, base_t4h, base_line = runs[f"base_{base_setting}"]
    assert Path(base_line["module_file"]).resolve().is_relative_to(
        Path(os.environ[BASE_ROOT_ENV]).resolve())
    assert row["v5_setting"] == setting and base_row["v5_setting"] == base_setting
    assert _canonical(_without_setting_name(row), NEW_ROW_KEYS) == _canonical(
        _without_setting_name(base_row))
    assert row["commands_sha256"] == base_row["commands_sha256"]
    arrays, meta = _t4h(t4h_path)
    base_arrays, base_meta = _t4h(base_t4h)
    assert _arrays_equal(_without_new_t4h_arrays(arrays), base_arrays) == []
    assert not any(name.startswith("jp3_") for name in base_arrays)
    assert meta["job"].pop("setting") == setting
    assert base_meta["job"].pop("setting") == base_setting
    assert meta == base_meta


def test_i_vbj_rev6_has_the_rev5_commands_without_a_fallback(runs) -> None:
    """P5-1 on the test key (7.2 (iii) is P5-1's): VBJ now runs ③ rev 6; with no
    ``WARN_ROD_PRESSURE_FALLBACK`` on either side its commands are those of revision 5 (the
    commit before X-10 and the alias run of this code); its records name revision 6."""
    row, t4h_path, _ = runs["VBJ"]
    alias_row, alias_t4h, _ = runs[REV5_ALIAS]
    for path in (t4h_path, alias_t4h):
        events = _t4h(path)[1]["events"]
        assert not [name for _, name in events if name.startswith("WARN_ROD_PRESSURE_FALLBACK")]
    assert row["r79"]["rod_fallback"] == alias_row["r79"]["rod_fallback"] == []
    assert row["commands_sha256"] == alias_row["commands_sha256"]
    check = row["hydraulics_record"]["extend_bound_check"]
    assert check["rule_revision"] == 6 and check["spec_edition"] == "fe6f5844"
    assert row["run_extend_start_revision"] == 6
    assert alias_row["hydraulics_record"]["extend_bound_check"]["rule_revision"] == 5
    arrays, meta = _t4h(t4h_path)
    assert meta["controller_tag"] == "final_C4G2_P3W_LAS_K1"
    assert {"jp3_r58_witness", "jp3_r59_substeps", "jp3_r510_candidates",
            "jp3_class"} <= set(arrays)
    if "base_VBJ" in runs:
        assert row["commands_sha256"] == runs["base_VBJ"][0]["commands_sha256"]


def _without_setting_name(row: dict) -> dict:
    return {**row, "v5_setting": "<setting>"}


def test_ii_an_unarmed_plan_is_vbj0_bit_for_bit(runs) -> None:
    """6.2a.8 (ii): VBK0 with a plan that never arms = VBJ0 (``rod_fault`` and the setting
    name aside); its T4h arrays and meta likewise, with an empty applied mask."""
    row, t4h_path, line = runs["VBK0_unarmed"]
    base_row, base_t4h, _ = runs["VBJ0"]
    assert line["rod_fault_imported"] is True
    record = row[screen.ROD_FAULT_KEY]
    assert record["is_armed"] is False and record["applied_periods"] == 0
    assert record["reads"] == record["updates"] > 0
    assert row["v5_setting"] == "VBK0" and base_row["v5_setting"] == "VBJ0"
    drop = (screen.ROD_FAULT_KEY,)
    assert _canonical(_without_setting_name(row), drop) == _canonical(
        _without_setting_name(base_row), drop)
    assert row["commands_sha256"] == base_row["commands_sha256"]
    arrays, meta = _t4h(t4h_path)
    base_arrays, base_meta = _t4h(base_t4h)
    assert _arrays_equal({k: v for k, v in arrays.items() if k not in NEW_T4H_ARRAYS},
                         base_arrays) == []
    assert not arrays["rod_fault_applied"].any()
    np.testing.assert_array_equal(arrays["rod_pressure_pre_fault_Pa"],
                                  base_arrays["rod_pressure_Pa"])
    assert meta.pop(screen.ROD_FAULT_PLAN_KEY)["sha256"] == record["plan_sha256"]
    assert meta.pop(screen.ROD_FAULT_KEY)["is_armed"] is False
    assert meta["job"].pop("setting") == "VBK0" and base_meta["job"].pop("setting") == "VBJ0"
    assert meta == base_meta


def test_ii_an_unarmed_plan_on_vbk_is_vbj_bit_for_bit(runs) -> None:
    """7.2 X-10 (ii) for VBK (③ rev 6): an unarmed plan gives the VBJ row and T4h record
    (``rod_fault``, its two arrays and the setting name aside)."""
    row, t4h_path, _ = runs["VBK_unarmed"]
    base_row, base_t4h, _ = runs["VBJ"]
    assert row[screen.ROD_FAULT_KEY]["is_armed"] is False
    drop = (screen.ROD_FAULT_KEY,)
    assert _canonical(_without_setting_name(row), drop) == _canonical(
        _without_setting_name(base_row), drop)
    arrays, meta = _t4h(t4h_path)
    base_arrays, base_meta = _t4h(base_t4h)
    assert _arrays_equal({k: v for k, v in arrays.items() if k not in NEW_T4H_ARRAYS},
                         base_arrays) == []
    meta.pop(screen.ROD_FAULT_PLAN_KEY)
    meta.pop(screen.ROD_FAULT_KEY)
    assert meta["job"].pop("setting") == "VBK" and base_meta["job"].pop("setting") == "VBJ"
    assert meta == base_meta


def test_trw_harness_run_latches_after_the_witness_and_runs_r59(runs) -> None:
    """7.2 (라) on the harness: VBK and VBK0 arm on the same TRw read (the witness read of
    the VBJ columns, ``retract_witnesses``), D1 latches on read n + 1, the commands before it
    are the same on both arms, and the rev 6 arm counts R5-9 sub-steps on the fault leg in the
    n -> n + 1 period."""
    row, t4h_path, _ = runs["VBK_trw"]
    row0, t4h0_path, _ = runs["VBK0_trw"]
    vbj_arrays, _ = _t4h(runs["VBJ_trw_key"][1])
    leg = rfp.LEGS.index(TRW_LEG)
    found = rfp.retract_witnesses(vbj_arrays["phase"], vbj_arrays["command_m_s"],
                                  vbj_arrays["motor_stroke_m"], leg, rfp.hold_speed_m_s())
    assert found, "no witnessed retract carry on the TRw leg of the test key"
    witness_read = found[0][1]
    for record in (row[screen.ROD_FAULT_KEY], row0[screen.ROD_FAULT_KEY]):
        assert record["trigger_read"] == witness_read
        assert record["first_applied_read"] == witness_read + 1
        assert record["witness"]["witness_read"] == witness_read
        assert record["latched"]["is_same_read_d1"] is True
        assert record["pre_trigger_fallback"] is False
    assert (row[screen.ROD_FAULT_KEY]["pre_trigger_commands_sha256"]
            == row0[screen.ROD_FAULT_KEY]["pre_trigger_commands_sha256"])
    arrays, _ = _t4h(t4h_path)
    first_t_s = row[screen.ROD_FAULT_KEY]["first_applied_t_s"]
    jp3_row = int(np.flatnonzero(np.isclose(arrays["jp3_t_s"], first_t_s))[0])
    assert arrays["jp3_r59_substeps"][jp3_row, leg] > 0
    # the release evidence of read n: the monitor's witness, or a gate seen open by then
    assert arrays["jp3_r58_witness"][jp3_row - 1, leg] or arrays["jp3_gate_open"][jp3_row - 1,
                                                                                  leg]
    assert row["hydraulics_record"]["extend_bound_check"]["jp3_r59_substeps"][leg] > 0
    arrays0, _ = _t4h(t4h0_path)
    assert not any(name.startswith("jp3_") for name in arrays0)  # VBK0: ③ off


def _expected_tau_r_read(arrays: dict, leg: int) -> int:
    """tau_R from the VBJ0 T4h columns (the rule of ``ed5_design/control_c/c2_triggers_b.py``
    (a), an independent path)."""
    phase, command = arrays["phase"].astype(str), arrays["command_m_s"]
    start = max(int(np.flatnonzero(phase == "level")[0]), 1)
    hold = rfp.hold_speed_m_s()
    return next(k for k in range(start, len(phase))
                if abs(command[k - 1, leg]) <= hold and command[k, leg] < -hold)


@pytest.mark.parametrize(("label", "leg"), [("VBK0_tau_r", "FR"), ("VBK0_tau_c", "RL")])
def test_c_a_real_fault_latches_d1_and_starts_the_fallback(runs, label, leg) -> None:
    """(c): the fault arms on the VBJ0 trigger read, latches D1 on its first faulty read, the
    fallback starts there; before it the commands and readings are the VBJ0 ones."""
    row, t4h_path, _ = runs[label]
    base_arrays, _ = _t4h(runs["VBJ0"][1])
    arrays, meta = _t4h(t4h_path)
    record = row[screen.ROD_FAULT_KEY]
    index = rfp.LEGS.index(leg)
    if label == "VBK0_tau_r":
        assert record["trigger_read"] == _expected_tau_r_read(base_arrays, index)
        assert record["first_applied_read"] == record["trigger_read"] + 1
    else:  # the read right after the update that left CHECK
        first_outside = int(np.flatnonzero(base_arrays["phase"].astype(str) != "check")[0])
        assert record["trigger_read"] == record["first_applied_read"] == first_outside + 1
    first = record["first_applied_read"]
    assert record["latched"] == {"is_latched": True, "reason": "D1",
                                 "t_s": round(record["first_applied_t_s"], 6),
                                 "reads_after_first": 0, "is_same_read_d1": True}
    assert record["pre_trigger_fallback"] is False
    assert record["applied_periods"] == record["reads"] - first
    assert meta["fallback_start_s"][index] == round(record["first_applied_t_s"], 6)
    assert (round(record["first_applied_t_s"], 2), leg) in [tuple(x) for x in
                                                            row["r79"]["rod_fallback"]]
    # 6.2a.4 (나): the commands before the first faulty read are VBJ0's
    base_commands = base_arrays["command_m_s"][:first]
    assert record["pre_trigger_commands_sha256"] == hashlib.sha256(
        np.ascontiguousarray(base_commands, float).tobytes()).hexdigest()
    np.testing.assert_array_equal(arrays["command_m_s"][:first], base_commands)
    # only the fault leg's rod reading changes; the head reading of that read is VBJ0's
    assert arrays["rod_fault_applied"][:, index].tolist() == (
        [False] * first + [True] * (len(arrays["t_s"]) - first))
    assert (arrays["rod_pressure_Pa"][first:, index] == GATE_VALUE_BAR * BAR).all()
    others = [k for k in range(4) if k != index]
    np.testing.assert_array_equal(arrays["rod_pressure_Pa"][:, others],
                                  arrays["rod_pressure_pre_fault_Pa"][:, others])
    np.testing.assert_array_equal(arrays["head_pressure_Pa"][:first + 1],
                                  base_arrays["head_pressure_Pa"][:first + 1])
    offset = record["rod_fault_sum_offset_N"]
    assert offset["n_finite"] == offset["n_reads"] == record["applied_periods"]
    assert offset["min_N"] > 0.0  # -A_ann (-100 bar - p_r) > 0 for any p_r > -100 bar


@pytest.mark.parametrize("label", ["VBK0_unarmed", "VBK0_tau_r", "VBK0_tau_c"])
def test_d_b2_evidence_holds_on_the_vbk0_rows(runs, label) -> None:
    """Addendum 4a-2 B2: P4 on, truth readings = monitor rod reads > 0 (the fault does not
    break the evidence)."""
    import j_p3_inputs

    row = runs[label][0]
    record = row["hydraulics_record"]
    assert j_p3_inputs.rod_reading_evidence_problems(record, row["hydraulic_options"]) == []
    assert record["rod_reading_truth_calls"] == record["two_pressure_reads"] > 0


# ------------------------------------------------------------------------------- runner guards
def _guard_environment(tmp_path: Path, setting: str | None, faults: dict | None) -> dict:
    environment = {name: value for name, value in os.environ.items()
                   if not name.startswith(("R79_", "R72_", "R67_", "LAS_T3_"))}
    environment.update(PYTHONDONTWRITEBYTECODE="1", MKL_THREADING_LAYER="TBB",
                       R79_SET="ref", R79_LEVELS="L2", R79_SEEDS="30",
                       R79_FILTER="|ref|0|rigid|B|", R79_CANDIDATE="current")
    if setting is not None:
        environment["R79_V5_SETTING"] = setting
    if faults is not None:
        environment["R79_ROD_FAULT_PLAN"] = str(_write_plan(tmp_path / "plan.json", faults))
    return environment


GUARD_CASES = [
    ("VBK0", None, "needs R79_ROD_FAULT_PLAN"),
    ("VBJ0", {RUN_KEY: _fault()}, "is no VBK setting"),
    ("VBK0", {}, "empty plan"),
    ("VBK0", {"cand=current#L2|s31|ref|0|rigid|B|0,0": _fault()}, "without a fault"),
]


@pytest.mark.parametrize(("setting", "faults", "match"), GUARD_CASES)
def test_e_r79_main_exits_2_before_any_job(tmp_path, setting, faults, match) -> None:
    pytest.importorskip("numba", reason="the job list imports the harness modules")
    done = subprocess.run(
        [sys.executable, "-I", "-B", str(S8_DIR / "r79_sensor_screen.py"), str(ROOT),
         str(tmp_path / "out.json"), "1"], cwd=ROOT,
        env=_guard_environment(tmp_path, setting, faults), capture_output=True, text=True,
        timeout=RUN_TIMEOUT_S)
    assert done.returncode == 2, done.stderr[-2000:]
    assert match in done.stderr and not (tmp_path / "out.json").exists()


@pytest.mark.parametrize(("setting", "faults", "match"), GUARD_CASES[:2])
def test_e_l3l4_runner_exits_2_before_any_job(tmp_path, setting, faults, match) -> None:
    pytest.importorskip("numba", reason="the job list imports the harness modules")
    environment = _guard_environment(tmp_path, setting, faults)
    for name in ("R79_SET", "R79_LEVELS", "R79_SEEDS", "R79_FILTER", "R79_CANDIDATE"):
        environment.pop(name)
    keys_file = tmp_path / "keys.txt"
    keys_file.write_text(RUN_KEY + "\n", encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "-I", "-B", str(S8_DIR / "r79_L3L4_final.py"), str(ROOT), "run",
         str(tmp_path / "out.json"), "--levels", "L2", "--keys-file", str(keys_file),
         "--workers", "1"], cwd=ROOT, env=environment, capture_output=True, text=True,
        timeout=RUN_TIMEOUT_S)
    assert done.returncode == 2, done.stderr[-2000:]
    assert match in done.stderr and not (tmp_path / "out.json").exists()
