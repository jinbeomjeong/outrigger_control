"""``control/two_pressure`` D1' explained steps (U-S8-26, P-S8-12 ①, control spec rev. 47
217.5), the stroke check on by default (U-S8-28, P-S8-12 ②), and monitors / settings pickled
before P-S8-12 (P-S8-12 ③, ML ``branch.pkl``).

Synthetic cases use the ML pilot pressures of 217.2; the record replays at the end use
``07_results/S8`` (git-ignored) and are skipped without it.
"""

from __future__ import annotations

import json
import pickle
import re
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.two_pressure import (
    LoadEstimate,
    StepRule,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
ANNULUS = np.array([3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3])
V_MAX = 0.020924
F_MIN = load_params().control.F_min_cylinder_N
LOAD_N = np.array([118e3, 118e3, 72e3, 72e3])
STILL = np.zeros(4)
START_STROKE_M = 0.2
GRAVITY_M_S2 = 9.80665
FR, RR = 1, 3


def _monitor(**changes) -> TwoPressureMonitor:
    settings = replace(TwoPressureSettings().with_r8_period(), **changes)
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, PERIOD_S, settings=settings)


def _pressures(load_N=LOAD_N, rod_bar=2.0):
    rod = np.full(4, rod_bar * BAR)
    return (load_N + rod * ANNULUS) / HEAD_AREA, rod


def _with(values, leg, bar):
    changed = np.array(values, dtype=float)
    changed[leg] = bar * BAR
    return changed


def _command(leg, fraction_of_v_max):
    command = np.zeros(4)
    command[leg] = fraction_of_v_max * V_MAX
    return command


def _read_two(monitor, before, after, commands=(STILL, STILL), locked=True):
    """Read ``before`` then ``after`` (head, rod) one period apart; returns the event names."""
    stroke = np.full(4, START_STROKE_M)
    for k, ((head, rod), command) in enumerate(zip((before, after), commands, strict=True)):
        stroke = stroke + command * PERIOD_S
        monitor.read(k * PERIOD_S, head, rod, command, locked, 2e3, stroke_m=stroke)
    return [name for name, _ in monitor.pop_events()]


def _faults(names):
    return [name for name in names if "FALLBACK" in name or "FAULT" in name]


# --- D1' rod side --------------------------------------------------------------------------


def _locked_load_loss():
    """ML00_ep5 FR 61.10 s: locked, rod 2.1 -> 111.2 bar, head 88.9 -> 40.8 bar."""
    head, rod = _pressures()
    return (head, rod), (_with(head, FR, 40.8), _with(rod, FR, 111.2))


def test_rod_rise_of_a_locked_leg_with_the_head_falling_is_explained() -> None:
    monitor = _monitor()
    names = _read_two(monitor, *_locked_load_loss())
    assert monitor.fallback_legs == []
    assert names == ["INFO_PRESSURE_STEP:FR:rod:lock_load_loss"]


def test_jump_rule_keeps_the_old_fault_on_the_same_step() -> None:
    monitor = _monitor(step_rule="jump")
    assert monitor.settings.step_rule is StepRule.JUMP
    names = _read_two(monitor, *_locked_load_loss())
    assert monitor.fallback_legs == [FR]
    assert "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1" in names
    assert not [name for name in names if name.startswith("INFO_PRESSURE_STEP")]


@pytest.mark.parametrize("case", ["head_unchanged", "commanded_before", "commanded_now"])
def test_rod_rise_without_the_lock_law_is_a_fault(case) -> None:
    """217.5: a rod jump with no head change, or on a leg commanded this or the last period,
    is not the lock law (the 150 bar "jump" of the unit tests)."""
    (head, rod), (head_after, rod_after) = _locked_load_loss()
    extend = _command(FR, 0.5)
    commands = {"head_unchanged": (STILL, STILL), "commanded_before": (extend, STILL),
                "commanded_now": (STILL, extend)}[case]
    if case == "head_unchanged":
        head_after = head
    monitor = _monitor()
    names = _read_two(monitor, (head, rod), (head_after, rod_after), commands)
    assert monitor.fallback_legs == [FR]
    assert "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1" in names


def _trapped_rod_drain(after_bar=4.6):
    """ML02_ep1 RR 63.30 s: rod 115.4 -> 4.6 bar as the re-approach opens the pilot check."""
    head, rod = _pressures()
    return (head, _with(rod, RR, 115.4)), (head, _with(rod, RR, after_bar))


@pytest.mark.parametrize("command_period", [0, 1])
def test_rod_fall_into_the_extend_range_under_a_command_is_explained(command_period) -> None:
    """A positive command this or the last period opens the pilot check."""
    reapproach = _command(RR, 0.25)
    commands = (reapproach, STILL) if command_period == 0 else (STILL, reapproach)
    monitor = _monitor()
    names = _read_two(monitor, *_trapped_rod_drain(), commands=commands, locked=False)
    assert monitor.fallback_legs == []
    assert names == ["INFO_PRESSURE_STEP:RR:rod:check_opened"]


@pytest.mark.parametrize(("after_bar", "is_commanded"),
                         [(4.6, False), (14.0, True), (-4.0, True)])
def test_rod_fall_without_a_command_or_outside_the_range_is_a_fault(after_bar, is_commanded):
    """217.5: a locked rod reading that drops (lower bound optimistic) or a drop that ends
    outside the D2 extend range (-1 .. 12 bar) is a sensor fault. Since P-S8-21 a drop under
    a command that ends above the range (14 bar) is held one period first: the reading stays
    there, so it falls back one period late."""
    reapproach = _command(RR, 0.25)
    commands = (STILL, reapproach) if is_commanded else (STILL, STILL)
    monitor = _monitor()
    before, after = _trapped_rod_drain(after_bar)
    names = _read_two(monitor, before, after, commands=commands, locked=False)
    if after_bar > 12.0:
        assert monitor.fallback_legs == []
        monitor.read(2 * PERIOD_S, *after, commands[1], False, 2e3,
                     stroke_m=np.full(4, START_STROKE_M) + 2 * commands[1] * PERIOD_S)
        names += [name for name, _ in monitor.pop_events()]
    assert monitor.fallback_legs == [RR]
    assert "INFO_ROD_PRESSURE_FAULT_REASON:RR:D1" in names


# --- D1' head side -------------------------------------------------------------------------


def test_head_steps_that_move_load_between_legs_are_explained() -> None:
    """ML00_ep5 61.40 s: FR head +107 bar with the four-leg sum nearly unchanged (ratio
    0.007). Here 146 kN moves from FL to FR: both head steps (+-110 bar) are explained."""
    moved_N = 110.0 * BAR * HEAD_AREA[0]
    before = _pressures(np.array([200e3, 60e3, 72e3, 72e3]))
    after = _pressures(np.array([200e3 - moved_N, 60e3 + moved_N, 72e3, 72e3]))
    monitor = _monitor()
    names = _read_two(monitor, before, after, locked=False)
    assert monitor.head_fault_legs == []
    assert names == ["INFO_PRESSURE_STEP:FL:head:load_redistribution",
                     "INFO_PRESSURE_STEP:FR:head:load_redistribution"]


def test_head_sensor_jump_moving_the_sum_is_a_fault() -> None:
    """A head jump moves the net-force sum by the whole step force (ratio about 1)."""
    head, rod = _pressures()
    monitor = _monitor()
    names = _read_two(monitor, (head, rod), (_with(head, FR, 89.5 + 110.0), rod),
                      locked=False)
    assert monitor.head_fault_legs == [FR]
    assert _faults(names) == ["FAULT_HEAD_PRESSURE:FR",
                              "INFO_HEAD_PRESSURE_FAULT_REASON:FR:D1_step"]


def test_range_fault_is_not_explained() -> None:
    """A reading out of range is a fault even when the step would be explained."""
    (head, rod), (head_after, _) = _locked_load_loss()
    monitor = _monitor()
    names = _read_two(monitor, (head, rod), (head_after, _with(rod, FR, 450.0)))
    assert monitor.fallback_legs == [FR]
    assert not [name for name in names if name.startswith("INFO_PRESSURE_STEP")]


# --- D2 with the stroke check on (U-S8-28) -------------------------------------------------


@pytest.mark.parametrize("fault", ["stuck_high", "dropped"])
def test_rod_sensor_fault_while_extending_is_still_detected(fault) -> None:
    """217.6 (2) test: with the stroke check on by default, a rod sensor stuck at 40 bar or
    dropped to -4 bar (inside the sensor range and current) on an extending grounded leg
    falls back by D2 after the 1 s settle and the 1 s hold (2.0 s)."""
    monitor = _monitor()
    assert monitor.settings.moving_stroke_check
    extend = np.full(4, 0.5 * V_MAX)
    head, rod = _pressures()
    bad_bar = {"stuck_high": 40.0, "dropped": -4.0}[fault]
    rod_reading = _with(rod, RR, bad_bar)
    head_reading = (LOAD_N + rod_reading * ANNULUS) / HEAD_AREA  # load unchanged
    stroke = np.full(4, START_STROKE_M)
    fell_back_s = None
    for k in range(round(3.0 / PERIOD_S)):
        stroke = stroke + extend * PERIOD_S
        monitor.read(k * PERIOD_S, head_reading, rod_reading, extend, False, 2e3,
                     stroke_m=stroke)
        if fell_back_s is None and monitor.fallback_legs:
            fell_back_s = k * PERIOD_S
    assert monitor.fallback_legs == [RR]
    assert fell_back_s == pytest.approx(2.0)
    assert "INFO_ROD_PRESSURE_FAULT_REASON:RR:D2" in [n for n, _ in monitor.pop_events()]


# --- pickles written before P-S8-12 --------------------------------------------------------


def _settings_pickled_before_p_s8_12() -> TwoPressureSettings:
    """A frozen settings object restored from a pickle without the P-S8-12 fields."""
    settings = TwoPressureSettings().with_r8_period()
    state = dict(settings.__dict__)
    del state["step_rule"], state["explained_step_sum_ratio"]
    state["moving_stroke_check"] = False
    old = object.__new__(TwoPressureSettings)
    old.__dict__.update(state)
    return pickle.loads(pickle.dumps(old))


def test_settings_pickled_before_read_the_class_defaults() -> None:
    """Since P-S8-14 the class default is D1'' (``explained_imu``); the rod-side reasons of
    this case are the same."""
    old = _settings_pickled_before_p_s8_12()
    assert "step_rule" not in old.__dict__
    assert old.step_rule is StepRule.EXPLAINED_IMU
    assert old.explained_step_sum_ratio == 0.5
    assert old.moving_stroke_check is False  # stored value of the old run
    meta = old.to_meta()
    assert meta["step_rule"] == "explained_imu" and "moving_stroke_check" not in meta
    json.dumps(meta)
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, PERIOD_S, settings=old)
    assert _read_two(monitor, *_locked_load_loss()) == [
        "INFO_PRESSURE_STEP:FR:rod:lock_load_loss"]


def test_refresh_settings_keeps_the_state_and_guards_the_buffer_sizes() -> None:
    old_settings = _settings_pickled_before_p_s8_12()
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN, PERIOD_S,
                                 settings=old_settings)
    head, rod = _pressures()
    _read_two(monitor, (head, rod), (head, _with(rod, RR, 450.0)))
    assert monitor.fallback_legs == [RR]
    current = TwoPressureSettings().with_r8_period()
    monitor.refresh_settings(current)
    assert monitor.settings is current and monitor.fallback_legs == [RR]
    with pytest.raises(ValueError, match="stuck_window_s"):
        monitor.refresh_settings(replace(current, stuck_window_s=5.0))


# --- record replays (07_results/S8, git-ignored) -------------------------------------------

ML_PILOT = Path(__file__).resolve().parents[2] / "07_results" / "S8" / "ml_pilot_20261025_002044"
ML_OLD_EPISODES = ML_PILOT / "episodes" / "_replaced_20261025_015059"
"""The first ML run's episodes (the ML rerun of rev. 48 moved them here); only they hold the
D1 fault records of 217.2."""
ML_EPISODES = {
    "ML00_ep5": ["INFO_PRESSURE_STEP:FR:rod:lock_load_loss",
                 "INFO_PRESSURE_STEP:FR:rod:check_opened",
                 "INFO_PRESSURE_STEP:FR:head:load_redistribution",
                 "INFO_PRESSURE_STEP:FL:head:load_redistribution",
                 "INFO_PRESSURE_STEP:FR:rod:lock_load_loss"],
    "ML02_ep1": ["INFO_PRESSURE_STEP:RR:rod:check_opened"],
    "ML02_ep5": ["INFO_PRESSURE_STEP:RL:rod:check_opened"],
    "ML22_ep4": ["INFO_PRESSURE_STEP:FL:rod:lock_load_loss"],
}
"""217.2: the eight steps above 100 bar of the four D1 episodes, in time order."""
RECORDED_EVENT = re.compile(r"name='([^']+)'")


def _replay_events(case: Path, settings: TwoPressureSettings) -> list[str]:
    """Event names of the monitor fed the 10 Hz readings of a recorded episode (true pad-record
    pressures and strokes at the sample instant, the applied command, READY, the band, the
    run's zero offsets); the monitor starts at the branch."""
    controller = json.loads((case / "result.json").read_text(encoding="utf-8"))["controller_meta"]
    meta = controller["two_pressure"]
    monitor = TwoPressureMonitor(
        meta["head_area_m2"], meta["annulus_area_m2"], controller["geometry"]["max_speed_m_s"],
        controller["geometry"]["F_min_N"], controller["period_s"],
        LoadEstimate(meta["load_estimate"]), settings, meta["rod_weight_N"])
    monitor.set_zero_offsets_N(meta["zero_offsets_N"])
    with np.load(case / "r8_series.npz") as r8, np.load(case / "pads.npz") as pads:
        t = r8["t"]
        index = np.clip(np.searchsorted(pads["t"], t - 1e-9), 0, len(pads["t"]) - 1)
        head, rod = pads["head_pressure"][index], pads["rod_pressure"][index]
        stroke = pads["stroke_true"][index]
        issued, phase, band = r8["issued_u"], r8["phase"], r8["F_band_N"]
    commanded = np.vstack([np.zeros((1, 4)), issued[:-1]])
    names = []
    for k in range(len(t)):
        locked = bool(k) and phase[k - 1] == "READY"
        bands = monitor.leg_seal_bands_N(band[k - 1] if k else band[0])
        monitor.read(t[k], head[k], rod[k], commanded[k], locked, bands, stroke_m=stroke[k])
        names += [name for name, _ in monitor.pop_events()]
    return names


def _recorded_pressure_faults(case: Path) -> list[str]:
    """Sensor fault events the episode's controller recorded (in order)."""
    lines = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
    names = [RECORDED_EVENT.search(line).group(1) for line in lines]
    return [name for name in _faults(names) if "PRESSURE" in name]


@pytest.mark.skipif(not ML_OLD_EPISODES.is_dir(), reason="07_results/S8 old ML episodes absent")
@pytest.mark.parametrize("episode", sorted(ML_EPISODES))
def test_ml_d1_episodes_have_no_false_fault_with_explained_steps(episode) -> None:
    """217.9 #1: the four ML-2 episodes: ``jump`` reproduces the recorded D1 fallbacks and head
    faults (the head fault reason is new in P-S8-14, not in the old record); D1'
    (``explained``, stroke check on) has none and records the steps."""
    case = ML_OLD_EPISODES / episode
    settings = replace(TwoPressureSettings().with_r8_period(), step_rule="explained")
    jump = _replay_events(case, replace(settings, step_rule="jump", moving_stroke_check=False))
    jump_faults = [name for name in _faults(jump)
                   if not name.startswith("INFO_HEAD_PRESSURE_FAULT_REASON")]
    assert jump_faults == _recorded_pressure_faults(case)
    explained = _replay_events(case, settings)
    assert _faults(explained) == []
    assert [name for name in explained if name.startswith("INFO_PRESSURE_STEP")] == (
        ML_EPISODES[episode])


ML_BASES = sorted(ML_PILOT.glob("bases/ML*/branch.pkl")) if ML_PILOT.is_dir() else []


@pytest.mark.skipif(not ML_BASES, reason="07_results/S8 ML pilot bases not present")
@pytest.mark.parametrize("branch", ML_BASES, ids=lambda path: path.parent.name)
def test_controller_from_an_old_branch_runs_on_the_current_settings(branch) -> None:
    """P-S8-12 ③ / C-S8-25 ③: a controller pickled before P-S8-12 restores, takes the current
    code's monitor settings (stroke check on, explained steps) and keeps running."""
    with open(branch, "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own batch file
    controller = blob["controller"]
    inner = getattr(controller, "inner", controller)
    monitor = inner._pressures
    current = TwoPressureSettings().with_r8_period()
    if monitor.settings.lock_valve != current.lock_valve:
        pytest.skip("counterbalance base (current settings need the CB law)")
    monitor.refresh_settings(current)
    assert monitor.settings.moving_stroke_check
    assert monitor.settings.step_rule == "explained_imu"
    head = np.asarray(inner._state.last_forces.head_only) / monitor.head_area_m2
    stroke = np.asarray(inner._state.last_reading.motor_stroke_m, dtype=float)
    level = np.array([0.0, 0.0, GRAVITY_M_S2])
    for k in range(5):
        command = controller.update(Measurements(
            t_s=float(blob["t_s"]) + (k + 1) * PERIOD_S,
            specific_force_m_s2=level,
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head,
            stroke_m=stroke,
            rod_pressure_Pa=np.full(4, 5e5),
            imu_specific_force_samples_m_s2=np.tile(level, (10, 1)),
        ))
        assert np.all(np.isfinite(command.leg_speed_m_s))
