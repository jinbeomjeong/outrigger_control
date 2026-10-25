"""D1' rod drain hold of ``control/two_pressure`` (P-S8-21, U-S8-56 (a), control spec rev. 54
260.5 as changed by rev. 55 268.3 (R-2 excess form, R-4 ``p_hi`` of D2)).

A locked leg that lifts off traps 125-174 bar on the rod side; when the check opens the
pressure drains with ``tau_d`` about 50 ms and the next 10 Hz sample still reads 21-28 bar,
above the D2 extend range. Synthetic cases (268.3 #5 (i)-(vii), pickles before P-S8-21) and
record replays of ``07_results/S8`` (git-ignored; skipped without it): the 17 false fallbacks
of c36 A (260.1), the other 38 A runs unchanged, no hold in c36 B / C / D, and no new sensor
fault in the 768 / p1r / rest / CB records.
"""

from __future__ import annotations

import copy
import json
import pickle
import re
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

import numpy as np
import pytest
from test_two_pressure_d1_imu import case_settings, read_period, run_inputs  # same test folder

from outrigger_sim.control.two_pressure import (
    ROD_DRAIN_HOLD_RATIO,
    LoadEstimate,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.params import load_params

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
F_MIN_N = 9414.59
LOAD_N = np.array([118e3, 118e3, 72e3, 72e3])
STROKE_M = 0.30
FR = 1
STILL = np.zeros(4)
REAPPROACH = np.array([0.0, 0.25 * V_MAX, 0.0, 0.0])
CB_PARAMS = load_params(level="top", model="L2b_NSC").l2b.counterbalance


def _monitor(settings: TwoPressureSettings | None = None) -> TwoPressureMonitor:
    settings = settings or TwoPressureSettings().with_r8_period()
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              stroke_max_m=0.70)


def _read_rod_series(monitor, rod_bar, commands, head_bar=None):
    """Read FR rod-side ``rod_bar`` (one value per period; the other legs 2 bar) with the head
    fixed; returns (event names per period, nominal FR force per period)."""
    head = (LOAD_N + 2 * BAR * ANNULUS) / HEAD_AREA
    if head_bar is not None:
        head[FR] = head_bar * BAR
    names, forces = [], []
    for k, (bar, command) in enumerate(zip(rod_bar, commands, strict=True)):
        rod = np.full(4, 2 * BAR)
        rod[FR] = bar * BAR
        out = monitor.read(k * PERIOD_S, head, rod, command, False, 2e3,
                           stroke_m=np.full(4, STROKE_M))
        names.append([name for name, _ in monitor.pop_events()])
        forces.append(out.nominal[FR])
    return names, forces


def _fallback_period(names) -> int | None:
    for k, period in enumerate(names):
        if "WARN_ROD_PRESSURE_FALLBACK:FR" in period:
            return k
    return None


def _drains(names) -> list[str]:
    return [name for period in names for name in period if name.endswith(":check_draining")]


# --- 260.5 #5 -----------------------------------------------------------------------------------


def test_i_drain_confirmed_by_the_next_reading_is_explained() -> None:
    """(i) 124 -> 21 -> 4 bar under a positive command (4 <= 12 + 0.5 x 9 = 16.5): no
    fallback, one INFO, and the held period still reads the 21 bar rod side (260.5 #3)."""
    monitor = _monitor()
    names, forces = _read_rod_series(monitor, [124.0, 21.0, 4.0], [STILL, REAPPROACH,
                                                                   REAPPROACH])
    assert monitor.fallback_legs == []
    assert _drains(names) == ["INFO_PRESSURE_STEP:FR:rod:check_draining"]
    assert names[1] == []  # the hold itself raises nothing
    head_force_N = LOAD_N[FR] + 2 * BAR * ANNULUS[FR]
    assert forces[1] == pytest.approx(head_force_N - 21.0 * BAR * ANNULUS[FR], rel=0, abs=1e-6)


def test_ii_reading_that_stays_up_falls_back_one_period_late() -> None:
    """(ii) 124 -> 21 -> 21 bar (21 > 16.5): D1 fallback at the confirming period."""
    monitor = _monitor()
    names, _ = _read_rod_series(monitor, [124.0, 21.0, 21.0], [STILL, REAPPROACH, REAPPROACH])
    assert monitor.fallback_legs == [FR]
    assert _fallback_period(names) == 2
    assert "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1" in names[2]
    assert _drains(names) == []


def test_iii_fall_without_a_command_falls_back_at_once() -> None:
    """(iii) 124 -> 21 bar with the command zero: the rule before P-S8-21."""
    monitor = _monitor()
    names, _ = _read_rod_series(monitor, [124.0, 21.0], [STILL, STILL])
    assert _fallback_period(names) == 1


@pytest.mark.parametrize(("confirm_bar", "is_explained"),
                         [(21.0, True), (21.1, False), (20.9, True), (-0.5, True),
                          (-1.5, False)])
def test_vii_confirmation_bound_is_the_excess_form(confirm_bar, is_explained):
    """(vii) rev. 55 268.3 #2 (R-2): ``p_hi + rho (p_k - p_hi)`` with ``rho`` 0.5, 30 bar held
    -> 12 + 0.5 x 18 = 21 bar, equality explained (``<=``); below ``p_lo`` = -1 bar is no
    drain (ASSUMPTION of this implementation)."""
    assert ROD_DRAIN_HOLD_RATIO == 0.5
    monitor = _monitor()
    names, _ = _read_rod_series(monitor, [150.0, 30.0, confirm_bar],
                                [STILL, REAPPROACH, STILL])
    assert (monitor.fallback_legs == []) is is_explained
    assert bool(_drains(names)) is is_explained


def test_rise_or_a_fall_into_the_range_keeps_its_old_reason() -> None:
    """A fall straight into the extend range stays ``check_opened`` (no hold)."""
    monitor = _monitor()
    names, _ = _read_rod_series(monitor, [124.0, 6.0], [STILL, REAPPROACH])
    assert names[1] == ["INFO_PRESSURE_STEP:FR:rod:check_opened"]


@pytest.mark.parametrize("rule", ["off", "jump"])
def test_hold_off_and_jump_rule_fall_back_at_once(rule) -> None:
    settings = TwoPressureSettings().with_r8_period()
    settings = (replace(settings, rod_drain_hold_ratio=None) if rule == "off"
                else replace(settings, step_rule="jump"))
    monitor = _monitor(settings)
    names, _ = _read_rod_series(monitor, [124.0, 21.0, 4.0], [STILL, REAPPROACH, REAPPROACH])
    assert _fallback_period(names) == 1


def test_invalid_ratio_is_rejected() -> None:
    with pytest.raises(ValueError, match="rod_drain_hold_ratio"):
        TwoPressureSettings(rod_drain_hold_ratio=-0.1)


# --- counterbalance (260.5 #4) ------------------------------------------------------------------


def _cb_monitor() -> TwoPressureMonitor:
    settings = TwoPressureSettings().with_r8_period().with_lock_valve("counterbalance",
                                                                      CB_PARAMS)
    return _monitor(settings)


def _head_bar_for_cb_law(monitor, law_bar: float) -> float:
    """Head reading at which the CB extend law regulates the rod side to ``law_bar``."""
    law = monitor.settings.counterbalance
    head_bar = (law.p_set_Pa - law_bar * BAR) / law.pilot_ratio / BAR
    assert law.extend_rod_pressure_Pa(head_bar * BAR) == pytest.approx(law_bar * BAR)
    return head_bar


def test_cb_p_hi_is_the_law_plus_the_d2_margin() -> None:
    """R-4: the hold reads ``p_hi^CB`` = CB law + 15 bar from the D2 range function."""
    monitor = _cb_monitor()
    head_bar = _head_bar_for_cb_law(monitor, 150.0)
    _, high_Pa = monitor._extend_rod_range_Pa(head_bar * BAR)
    assert high_Pa == pytest.approx((150.0 + 15.0) * BAR)


@pytest.mark.parametrize("law_bar", [143.0, 156.0])
@pytest.mark.parametrize("pre_bar", [324.0, None])
def test_v_cb_lift_off_drain_to_the_regulated_value_is_explained(law_bar, pre_bar) -> None:
    """(v) H-S8-5 CB case: locked 324 -> ``law + 81`` -> ``law + 11`` bar (CB end value 143-156
    bar g) is no fault. From 324 bar the first change is at most 100 bar, so D1 sees no step
    at all; ``pre_bar = None`` starts 110 bar above ``law + 81`` so the step is held and
    ``law + 11 <= law + 15 + 0.5 x 66`` explains it."""
    monitor = _cb_monitor()
    head_bar = _head_bar_for_cb_law(monitor, law_bar)
    held_bar = law_bar + 81.0
    first_bar = held_bar + 110.0 if pre_bar is None else pre_bar
    names, _ = _read_rod_series(monitor, [first_bar, held_bar, law_bar + 11.0],
                                [STILL, REAPPROACH, REAPPROACH], head_bar=head_bar)
    assert monitor.fallback_legs == []
    expected = [] if pre_bar is not None else ["INFO_PRESSURE_STEP:FR:rod:check_draining"]
    assert [name for period in names for name in period if "FR:rod" in name] == expected


def test_vi_cb_reading_stuck_after_the_step_falls_back() -> None:
    """(vi) CB stuck: ``law + 81`` -> ``law + 81`` bar after a held step, D1 fallback at the
    confirming period (``law + 81 > law + 15 + 0.5 x 66``)."""
    monitor = _cb_monitor()
    law_bar = 150.0
    head_bar = _head_bar_for_cb_law(monitor, law_bar)
    held_bar = law_bar + 81.0
    names, _ = _read_rod_series(monitor, [held_bar + 110.0, held_bar, held_bar],
                                [STILL, REAPPROACH, REAPPROACH], head_bar=head_bar)
    assert _fallback_period(names) == 2
    assert _drains(names) == []


def test_cb_fall_into_the_cb_range_is_check_opened() -> None:
    head_bar = 60.0
    monitor = _cb_monitor()
    _, high_Pa = monitor._extend_rod_range_Pa(head_bar * BAR)
    names, _ = _read_rod_series(monitor, [high_Pa / BAR + 120.0, high_Pa / BAR - 2.0],
                                [STILL, REAPPROACH], head_bar=head_bar)
    assert names[1] == ["INFO_PRESSURE_STEP:FR:rod:check_opened"]


# --- pickles written before P-S8-21 -------------------------------------------------------------


def test_settings_and_monitor_pickled_before_read_the_defaults() -> None:
    settings = TwoPressureSettings().with_r8_period()
    state = dict(settings.__dict__)
    del state["rod_drain_hold_ratio"]
    old_settings = object.__new__(TwoPressureSettings)
    old_settings.__dict__.update(state)
    old_settings = pickle.loads(pickle.dumps(old_settings))
    assert old_settings.rod_drain_hold_ratio == ROD_DRAIN_HOLD_RATIO
    json.dumps(old_settings.to_meta())

    monitor = _monitor(old_settings)
    del monitor.__dict__["_rod_drain_held_Pa"]
    monitor = pickle.loads(pickle.dumps(monitor))
    assert monitor._rod_drain_held_Pa is None
    names, _ = _read_rod_series(monitor, [124.0, 21.0, 4.0], [STILL, REAPPROACH, REAPPROACH])
    assert monitor.fallback_legs == []
    assert _drains(names) == ["INFO_PRESSURE_STEP:FR:rod:check_draining"]


# --- record replays (07_results/S8, git-ignored) ------------------------------------------------

RESULTS = Path(__file__).resolve().parents[2] / "07_results" / "S8"
ML_MAIN = RESULTS / "ml_main_20261025_090131"
C36_A = RESULTS / "c36_20261025_155317" / "A_rt" / "episodes"
FALSE_FALLBACKS = {
    "ML00_ep5": "FR", "ML10_ep0": "RL", "ML21_ep1": "FR", "ML24_ep6": "RR", "ML25_ep7": "RL",
    "ML33_ep4": "FL", "ML34_ep7": "RR", "ML39_ep5": "FL", "ML42_ep6": "RR", "ML51_ep4": "RR",
    "ML54_ep0": "RR", "ML59_ep7": "RL", "ML71_ep6": "RL", "ML81_ep5": "FL", "ML87_ep1": "RL",
    "ML87_ep5": "RR", "ML89_ep0": "RL",
}
"""260.1: the 17 c36 A runs with ``WARN_ROD_PRESSURE_FALLBACK`` (D1) at event + 0.3-0.4 s."""
RECORDED_EVENT = re.compile(r"name='([^']+)'")
OTHER_BATCHES = ("p1r_20261024_222013", "rest_20261024_233615", "cb_20261025_013946")
"""Records replayed for no new fault besides the 768 ML episodes (``rest`` ``L_*`` runs record
no seal band and are left out)."""


@cache
def _branch_monitor(base: str) -> TwoPressureMonitor:
    with open(ML_MAIN / "bases" / base / "branch.pkl", "rb") as handle:
        blob = pickle.load(handle)  # noqa: S301 - own batch file
    controller = blob["controller"]
    return getattr(controller, "inner", controller)._pressures


def _start_monitor(case: Path, settings: TwoPressureSettings):
    """As ``test_two_pressure_d1_imu.start_monitor``, with the ML main bases (c36, 768)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    base = result.get("base")
    if isinstance(base, str):
        monitor = copy.deepcopy(_branch_monitor(base))
        monitor.refresh_settings(settings)
        return monitor, None
    controller = result["controller_meta"]
    meta = controller["two_pressure"]
    monitor = TwoPressureMonitor(
        meta["head_area_m2"], meta["annulus_area_m2"], controller["geometry"]["max_speed_m_s"],
        controller["geometry"]["F_min_N"], controller["period_s"],
        LoadEstimate(meta["load_estimate"]), settings, meta["rod_weight_N"],
        stroke_max_m=controller["geometry"]["stroke_max_m"])
    calibration = controller.get("zero_calibration") or {}
    end_s = (calibration.get("result") or {}).get("t_end_s")
    if end_s is None:
        monitor.set_zero_offsets_N(meta["zero_offsets_N"])
        return monitor, None
    return monitor, (end_s, calibration["offsets_N"])


@dataclass
class _Replay:
    """Monitor outputs of one replayed run."""

    names: list[str]
    forces: np.ndarray
    """(n, 3, 4): nominal, lower, upper per period."""
    bands_N: np.ndarray
    """(n, 4): per-leg seal band (U65) of the recorded scalar band after each read."""
    meta: dict


def _replay_outputs(case: Path, *, is_hold_on: bool) -> _Replay:
    settings = case_settings(case, "explained_imu")
    if not is_hold_on:
        settings = replace(settings, rod_drain_hold_ratio=None)
    inputs = run_inputs(case)
    with np.load(case / "r8_series.npz") as r8:
        scalar_band_N = r8["F_band_N"]
    monitor, calibration = _start_monitor(case, settings)
    names, forces, bands = [], [], []
    for k in range(inputs.t_s.size):
        out = read_period(monitor, inputs, k)
        forces.append(np.stack([out.nominal, out.lower, out.upper]))
        bands.append(monitor.leg_seal_bands_N(scalar_band_N[k]))
        names += [name for name, _ in monitor.pop_events()]
        if calibration is not None and inputs.t_s[k] >= calibration[0] - 1e-9:
            monitor.set_zero_offsets_N(calibration[1])
            calibration = None
    return _Replay(names, np.array(forces), np.array(bands), monitor.meta())


def _replay(case: Path, *, is_hold_on: bool) -> list[str]:
    return _replay_outputs(case, is_hold_on=is_hold_on).names


def _sensor_faults(names) -> list[str]:
    return [name for name in names if "ROD_PRESSURE_FALLBACK" in name
            or name.startswith(("FAULT_HEAD_PRESSURE", "INFO_ROD_PRESSURE_FAULT_REASON"))]


def _recorded_sensor_faults(case: Path) -> list[str]:
    lines = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
    return _sensor_faults([RECORDED_EVENT.search(line).group(1) for line in lines])


def _replayable(batch: Path) -> list[Path]:
    runs = []
    for result in sorted(batch.rglob("result.json")):
        case = result.parent
        if not (case / "record" / "record.npz").is_file():
            continue
        with np.load(case / "r8_series.npz") as r8:
            if "F_band_N" in r8.files:
                runs.append(case)
    return runs


@pytest.mark.skipif(not (C36_A.is_dir() and ML_MAIN.is_dir()), reason="c36 A records absent")
def test_c36_a_false_fallbacks_are_drains() -> None:
    """260.5 #6: the monitor-only replay of the 55 A runs reproduces the recorded sensor faults
    without the hold (17 rod fallbacks, D1) and has none with it, each of the 17 with one
    ``check_draining`` on its leg. Up to the recorded fallback the closed-loop inputs are the
    same, so the replay is exact to that instant."""
    runs = sorted(path for path in C36_A.iterdir() if path.is_dir())
    assert len(runs) == 55
    for case in runs:
        old = _replay(case, is_hold_on=False)
        assert _sensor_faults(old) == _recorded_sensor_faults(case), case.name
        new = _replay(case, is_hold_on=True)
        assert _sensor_faults(new) == [], case.name
        drains = [name for name in new if name.endswith(":rod:check_draining")]
        if case.name in FALSE_FALLBACKS:
            leg = FALSE_FALLBACKS[case.name]
            assert _sensor_faults(old) == [f"WARN_ROD_PRESSURE_FALLBACK:{leg}",
                                           f"INFO_ROD_PRESSURE_FAULT_REASON:{leg}:D1"]
            assert drains == [f"INFO_PRESSURE_STEP:{leg}:rod:check_draining"]
        else:
            assert _sensor_faults(old) == [] and drains == []


CONTROLLER_STATE_KEYS = ("rod_sensor_state", "head_sensor_state", "fallback_lock_current",
                         "fallback_lock_log")
"""Monitor meta that the controller records and a monitor-only replay reproduces (the load
reference log needs the controller's store calls)."""


@pytest.mark.skipif(not (C36_A.is_dir() and ML_MAIN.is_dir()), reason="c36 A records absent")
def test_c36_a_other_38_runs_keep_their_controller_outputs() -> None:
    """Rev. 55 268.3 #6: the 38 A runs outside the 17 read the same with the hold: forces and
    per-leg bands bit for bit against the rule without it, and fallback state and lock log as
    the record (``result.json`` ``controller_meta.two_pressure``) and the recorded band
    ``leg_band_N``. A run that differs would join bundle E (none)."""
    differing = []
    for case in sorted(path for path in C36_A.iterdir() if path.is_dir()):
        if case.name in FALSE_FALLBACKS:
            continue
        old = _replay_outputs(case, is_hold_on=False)
        new = _replay_outputs(case, is_hold_on=True)
        recorded = json.loads((case / "result.json").read_text(encoding="utf-8"))[
            "controller_meta"]["two_pressure"]
        with np.load(case / "r8_series.npz") as r8:
            recorded_bands_N = r8["leg_band_N"]
        is_same = (np.array_equal(old.forces, new.forces)
                   and np.array_equal(old.bands_N, new.bands_N)
                   and np.array_equal(new.bands_N, recorded_bands_N)
                   and all(new.meta[key] == recorded[key] for key in CONTROLLER_STATE_KEYS))
        if not is_same:
            differing.append(case.name)
    assert differing == []


@pytest.mark.skipif(not C36_A.is_dir(), reason="c36 records absent")
@pytest.mark.parametrize("bundle", ["B_f1only", "C_gate", "D_fs24"])
def test_c36_b_c_d_have_no_drain_hold(bundle) -> None:
    """Rev. 55 269.1: the regression runs of bundle E (C, D) and B never hold a drain, so the
    rerun of them under P-S8-21 reads as before."""
    runs = _replayable(C36_A.parents[1] / bundle)
    assert len(runs) == 2
    for case in runs:
        old = _replay_outputs(case, is_hold_on=False)
        new = _replay_outputs(case, is_hold_on=True)
        assert not [name for name in new.names if name.endswith(":check_draining")]
        assert new.names == old.names
        assert np.array_equal(new.forces, old.forces)


@pytest.mark.skipif(not ML_MAIN.is_dir(), reason="07_results/S8 records absent")
@pytest.mark.parametrize("batch", ["ml_main_20261025_090131/episodes", *OTHER_BATCHES])
def test_other_records_gain_no_sensor_fault(batch) -> None:
    """260.5 #6: the hold removes faults only; no run gains a fallback or a head FAULT."""
    runs = _replayable(RESULTS / batch)
    assert runs
    gained = []
    for case in runs:
        old = _sensor_faults(_replay(case, is_hold_on=False))
        new = _sensor_faults(_replay(case, is_hold_on=True))
        if [name for name in new if name not in old]:
            gained.append(case.name)
    assert gained == []
