"""Wrapper tokens DS / DS50 of ``s9_slope_fix_candidates.py`` (control spec 424.11, P-S8-35
differential pad sinking after the LOC) and the HB-1 record, tests 1 .. 5 of the spec.

The watch is driven through ``_ds_update`` with simple readings; ``_ds_rates_m_s`` is replaced
where a test needs a given signal. Tests 1 and 5 run H6 cases in a subprocess (slow).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import s9_slope_fix_candidates as fx  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

PERIOD_S = 0.1
STROKE_M = 0.30
WRAPPER_SCRIPT = ROOT / "04_scripts" / "03_control" / "s9" / "s9_slope_fix_candidates.py"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
STORED_L1GS = ROOT / "06_analysis" / "02_control" / "s9" / "rev83" / "regBE_h6.json"
SOFT_CASE = "H6|J1|B|top|flat|m1.1"
HARD_CASE = "H6|G1|B|top|flat|m1.2"


class _Reading:
    def __init__(self, t_s: float, strokes_m) -> None:
        self.t_s = t_s
        self.motor_stroke_m = np.asarray(strokes_m, float)
        self.rod_stroke_m = self.motor_stroke_m
        self.cylinder_force_N = np.full(4, 9e4)


@pytest.fixture(scope="module")
def params():
    return load_params()


def ds_controller(params, name: str = "DS", *, is_gate_open: bool = True):
    cls = fx.make_candidate_class(c2, c2.C2Controller, fx.parse_candidate(name))
    controller = cls.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    controller._state.phase = c2.C2Phase.LEVEL
    controller.fix.ds_first_loc_s = 1.0
    controller.fix.ds_gate_open = is_gate_open
    controller.fix.ds_gyro_roll = deque([0.0] * 100, maxlen=100)
    return controller


def drive(controller, rates_m_s, periods: int, t_start_s: float = 2.0,
          stroke_m: float = STROKE_M, monkeypatch=None) -> float:
    """``periods`` LEVEL periods with ``_ds_rates_m_s`` fixed at ``rates_m_s``."""
    monkeypatch.setattr(controller, "_ds_rates_m_s", lambda: np.asarray(rates_m_s, float))
    t_s = t_start_s
    for _ in range(periods):
        t_s = round(t_s + PERIOD_S, 10)
        controller._ds_update(_Reading(t_s, [stroke_m] * 4))
    return t_s


def event_names(controller) -> list[str]:
    return [e.name for e in controller.events if e.name.startswith("FIX_DIFF_SINK")]


# --- settings ----------------------------------------------------------------------------------


def test_tokens() -> None:
    ds, ds50 = fx.parse_candidate("DS"), fx.parse_candidate("DS50")
    assert ds.ds_enable and ds.ds_push_fraction == pytest.approx(0.25)
    assert ds50.ds_enable and ds50.ds_push_fraction == pytest.approx(0.5)
    assert ds.ds_track_w_m == (2.648, 2.411)
    assert not fx.parse_candidate("current").ds_enable
    with pytest.raises(ValueError):
        fx.parse_candidate("DS", {"ds_release_m_s": 0.004})


# --- signal ------------------------------------------------------------------------------------


def test_signal_is_the_stroke_slope_difference_minus_the_gyro_roll(params) -> None:
    controller = ds_controller(params)
    roll_rate = 0.001  # rad/s
    controller.fix.ds_gyro_roll = deque([roll_rate] * 100, maxlen=100)
    for k in range(10):
        t_s = 2.0 + 0.1 * k
        strokes = [STROKE_M + 0.005 * t_s, STROKE_M + 0.001 * t_s, STROKE_M, STROKE_M + 0.002 * t_s]
        controller.fix.ds_strokes.append((t_s, np.array(strokes)))
    rates = controller._ds_rates_m_s()
    assert rates[0] == pytest.approx(0.004 - 2.648 * roll_rate, abs=1e-9)
    assert rates[1] == pytest.approx(-0.002 - 2.411 * roll_rate, abs=1e-9)


# --- 2: threshold and the 1 s confirmation -----------------------------------------------------


@pytest.mark.parametrize(("rate_m_s", "is_held"), [(0.0029, False), (0.0031, True)])
def test_2_threshold(params, monkeypatch, rate_m_s, is_held) -> None:
    controller = ds_controller(params)
    drive(controller, [rate_m_s, 0.0], 10, monkeypatch=monkeypatch)
    assert (controller.fix.ds_active is not None) is is_held


def test_2_needs_ten_periods_in_a_row(params, monkeypatch) -> None:
    controller = ds_controller(params)
    t_s = drive(controller, [0.0, -0.004], 9, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None
    t_s = drive(controller, [0.0, 0.0], 1, t_s, monkeypatch=monkeypatch)  # interrupted
    t_s = drive(controller, [0.0, -0.004], 9, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None
    drive(controller, [0.0, -0.004], 1, t_s, monkeypatch=monkeypatch)
    active = controller.fix.ds_active
    assert active is not None and active["axis"] == 1 and active["legs"] == fx.RIGHT_LEGS
    assert event_names(controller) == ["FIX_DIFF_SINK_HOLD:FR,RR:4.0"]


# --- 3: release --------------------------------------------------------------------------------


def held(params, monkeypatch, rates=(0.005, 0.0)):
    controller = ds_controller(params)
    t_s = drive(controller, list(rates), 10, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is not None
    return controller, t_s


def test_3_release_after_half_a_second_settled(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    t_s = drive(controller, [0.0009, -0.0009], 4, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is not None
    drive(controller, [0.0009, -0.0009], 1, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None
    assert event_names(controller)[-1] == "FIX_DIFF_SINK_RELEASE:settled"


def test_3_one_axis_above_1_mm_s_keeps_the_hold(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    drive(controller, [0.0005, 0.0011], 8, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is not None


def test_3_release_after_ten_seconds(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    t_s = drive(controller, [0.005, 0.0], 99, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is not None
    drive(controller, [0.005, 0.0], 1, t_s, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == "FIX_DIFF_SINK_RELEASE:time"


def test_3_stroke_limit_642_8_mm(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    limit_m = controller._ds_stroke_limit_m()
    assert limit_m == pytest.approx(0.6428, abs=1e-9)
    t_s = drive(controller, [0.005, 0.0], 1, t_s, stroke_m=limit_m - 0.0001,
                monkeypatch=monkeypatch)
    assert controller.fix.ds_active is not None
    drive(controller, [0.005, 0.0], 1, t_s, stroke_m=limit_m, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == "FIX_DIFF_SINK_RELEASE:stroke"
    drive(controller, [0.005, 0.0], 20, t_s + 0.1, stroke_m=limit_m, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None  # no new hold at the stroke limit


def test_3_leaving_level_releases_and_done_ends_the_watch(params, monkeypatch) -> None:
    controller, t_s = held(params, monkeypatch)
    controller._state.phase = c2.C2Phase.DONE
    controller._ds_after_update(t_s)
    assert controller.fix.ds_active is None and controller.fix.ds_watch_over
    assert event_names(controller)[-1] == "FIX_DIFF_SINK_RELEASE:done"
    controller._state.phase = c2.C2Phase.LEVEL
    drive(controller, [0.005, 0.0], 15, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None


# --- action: command and DONE ------------------------------------------------------------------


@pytest.mark.parametrize(("name", "fraction"), [("DS", 0.25), ("DS50", 0.5)])
def test_hold_clips_the_other_side_and_pushes_the_sinking_side(params, monkeypatch, name,
                                                                fraction) -> None:
    controller = ds_controller(params, name)
    drive(controller, [0.005, 0.0], 10, monkeypatch=monkeypatch)  # left (FL, RL) sinks
    v_max = controller.geometry.max_speed_m_s
    command = np.array([0.1, 0.4, 0.9, -0.2]) * v_max
    out = controller._apply_lift_stroke_guard(_Reading(5.0, [STROKE_M] * 4), command)
    assert out[0] == pytest.approx(fraction * v_max)  # pushed up to f v_max
    assert out[2] == pytest.approx(0.9 * v_max)  # a faster command stays
    assert out[1] == 0.0 and out[3] == pytest.approx(-0.2 * v_max)  # other side: u <= 0


def test_no_done_while_held(params, monkeypatch) -> None:
    monkeypatch.setattr(c2.C2Controller, "_update_completion", lambda self, r, c: True)
    controller = ds_controller(params)
    assert controller._update_completion(None, 0.05)
    drive(controller, [0.005, 0.0], 10, monkeypatch=monkeypatch)
    controller._state.complete_since_s = 3.0
    assert not controller._update_completion(None, 0.05)
    assert controller._state.complete_since_s is None


# --- 6 .. 8: DSb (spec 424.11.1) ---------------------------------------------------------------


def test_dsb_tokens() -> None:
    dsb, dsb10 = fx.parse_candidate("DSb"), fx.parse_candidate("DSb10")
    assert (dsb.ds_mode, dsb.ds_gain, dsb.ds_add_cap_fraction, dsb.ds_release_on_reverse) == (
        "add", 1.5, 0.5, True)
    assert (dsb10.ds_mode, dsb10.ds_gain, dsb10.ds_add_cap_fraction) == ("add", 1.0, 0.25)
    dsb75 = fx.parse_candidate("DSb75")  # spec 424.11.2: DSb, cap 0.75 v_max, level settle gate
    assert dsb75 == fx.CandidateSettings(**{**vars(dsb), "ds_add_cap_fraction": 0.75,
                                            "ds_gate_max_settle_tilt_rad": math.radians(1.0)})
    for name in ("DS", "DS50", "DSb", "DSb10"):
        assert fx.parse_candidate(name).ds_gate_max_settle_tilt_rad is None
    assert fx.parse_candidate("DS").ds_mode == "floor"
    with pytest.raises(ValueError):
        fx.parse_candidate("DS", {"ds_mode": "push"})  # a preset value would win the override


@pytest.mark.parametrize(("reverse_m_s", "reason"), [(-0.0011, "reversed"), (-0.0009, None)])
def test_6_reverse_release(params, monkeypatch, reverse_m_s, reason) -> None:
    controller = ds_controller(params, "DSb")
    t_s = drive(controller, [0.005, 0.0], 10, monkeypatch=monkeypatch)
    assert controller.fix.ds_active["sign"] == 1.0
    drive(controller, [reverse_m_s, 0.0], 1, t_s, monkeypatch=monkeypatch)
    if reason is None:
        assert controller.fix.ds_active is not None
    else:
        assert controller.fix.ds_active is None
        assert event_names(controller)[-1] == f"FIX_DIFF_SINK_RELEASE:{reason}"


def test_6_reverse_comes_before_the_stroke_release(params, monkeypatch) -> None:
    controller = ds_controller(params, "DSb")
    t_s = drive(controller, [0.0, -0.005], 10, monkeypatch=monkeypatch)
    limit_m = controller._ds_stroke_limit_m()
    drive(controller, [0.0, 0.002], 1, t_s, stroke_m=limit_m, monkeypatch=monkeypatch)
    assert event_names(controller)[-1] == "FIX_DIFF_SINK_RELEASE:reversed"


def test_6_floor_mode_ignores_a_reverse(params, monkeypatch) -> None:
    controller = ds_controller(params, "DS")
    t_s = drive(controller, [0.005, 0.0], 10, monkeypatch=monkeypatch)
    drive(controller, [-0.004, 0.0], 1, t_s, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is not None


@pytest.mark.parametrize(("name", "gain", "cap"), [("DSb", 1.5, 0.5), ("DSb10", 1.0, 0.25),
                                                    ("DSb75", 1.5, 0.75)])
def test_7_added_speed_is_capped(params, monkeypatch, name, gain, cap) -> None:
    controller = ds_controller(params, name)
    drive(controller, [0.005, 0.004], 10, monkeypatch=monkeypatch)  # left sinks
    v_max = controller.geometry.max_speed_m_s
    command = np.array([0.1, 0.1, 0.1, 0.1]) * v_max
    out = controller._apply_lift_stroke_guard(_Reading(5.0, [STROKE_M] * 4), command)
    assert out[0] == pytest.approx(command[0] + gain * 0.005)
    assert out[2] == pytest.approx(command[2] + gain * 0.004)
    monkeypatch.setattr(controller, "_ds_rates_m_s", lambda: np.array([1.0, 1.0]))
    out = controller._apply_lift_stroke_guard(_Reading(5.1, [STROKE_M] * 4), command)
    assert out[0] == pytest.approx(command[0] + cap * v_max)
    assert out[2] == pytest.approx(command[2] + cap * v_max)


def test_8_other_legs_and_an_opposite_axis_stay_bit_for_bit(params, monkeypatch) -> None:
    controller = ds_controller(params, "DSb")
    drive(controller, [0.004, 0.0], 10, monkeypatch=monkeypatch)  # front left sinks: sign +
    monkeypatch.setattr(controller, "_ds_rates_m_s", lambda: np.array([0.004, -0.002]))
    command = np.array([0.0123, -0.0045, 0.0067, 0.0089])
    out = controller._apply_lift_stroke_guard(_Reading(5.0, [STROKE_M] * 4), command)
    assert out[0] == command[0] + min(1.5 * 0.004, 0.5 * controller.geometry.max_speed_m_s)
    assert out[1] == command[1] and out[2] == command[2] and out[3] == command[3]
    # rear r < 0 against the hold sign: no increment on RR either
    monkeypatch.setattr(controller, "_ds_rates_m_s", lambda: np.array([-0.0005, -0.002]))
    out = controller._apply_lift_stroke_guard(_Reading(5.1, [STROKE_M] * 4), command)
    np.testing.assert_array_equal(out, command)


# --- 4: gate -----------------------------------------------------------------------------------


def test_4_closed_gate_never_holds(params, monkeypatch) -> None:
    controller = ds_controller(params, is_gate_open=False)
    drive(controller, [0.02, 0.02], 30, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None and event_names(controller) == []


@pytest.mark.parametrize("has_sign", [False, True])
def test_4_gate_is_the_l1g_sign_at_the_first_loc(params, monkeypatch, has_sign) -> None:
    controller = ds_controller(params)
    controller.fix.ds_first_loc_s = None
    monkeypatch.setattr(controller, "_has_l1_soil_sign", lambda: has_sign)
    controller._soil_state().is_liftoff_confirmed = True
    controller._ds_note_loc(10.0)
    monkeypatch.setattr(controller, "_has_l1_soil_sign", lambda: not has_sign)
    controller._ds_note_loc(12.0)  # a later LOC keeps the first decision
    assert controller.fix.ds_first_loc_s == 10.0 and controller.fix.ds_gate_open is has_sign


@pytest.mark.parametrize(
    ("name", "tilt_deg", "is_open"),
    [("DSb75", 1.0, True), ("DSb75", 1.01, False), ("DSb75", -1.01, False),
     ("DSb75", None, False),  # unknown settle closes the tilt gate
     ("DSb", 1.01, True), ("DSb", None, True)],  # None limit: the gate as before
)
def test_4_dsb75_settle_tilt_gate(params, monkeypatch, name, tilt_deg, is_open) -> None:
    controller = ds_controller(params, name)
    controller.fix.ds_first_loc_s = None
    monkeypatch.setattr(controller, "_has_l1_soil_sign", lambda: True)
    settle = None if tilt_deg is None else (0.0, math.radians(tilt_deg))
    monkeypatch.setattr(controller, "_settle_attitude_rad", lambda: settle)
    controller._soil_state().is_liftoff_confirmed = True
    controller._ds_note_loc(10.0)
    assert controller.fix.ds_gate_open is is_open


def test_4_dsb75_tilt_gate_needs_the_soil_sign_as_well(params, monkeypatch) -> None:
    controller = ds_controller(params, "DSb75")
    controller.fix.ds_first_loc_s = None
    monkeypatch.setattr(controller, "_has_l1_soil_sign", lambda: False)
    monkeypatch.setattr(controller, "_settle_attitude_rad", lambda: (0.0, 0.0))
    controller._soil_state().is_liftoff_confirmed = True
    controller._ds_note_loc(10.0)
    assert not controller.fix.ds_gate_open


def test_no_watch_before_the_first_loc(params, monkeypatch) -> None:
    controller = ds_controller(params)
    controller.fix.ds_first_loc_s = None
    drive(controller, [0.02, 0.0], 20, monkeypatch=monkeypatch)
    assert controller.fix.ds_active is None


# --- HB-1 --------------------------------------------------------------------------------------


def test_hb1_metrics_from_the_final_loc_to_the_first_done() -> None:
    fix = fx._FixState()
    fix.log = [(t / 10, "done" if t >= 40 else "level", 0.0, None) for t in range(50)]
    fix.truth_log = [(t / 10, -0.01 * t, [t * 1.0, 0.0, t * 2.0, 0.0]) for t in range(50)]
    fix.ds_active_periods = 12
    events = [(1.0, "crawler_liftoff_confirmed"), (1.5, "FIX_LOC_REVOKE:2.3"),
              (2.0, "crawler_liftoff_confirmed")]
    crawler = [(1.2, 500.0), (2.5, 300.0), (3.0, 800.0)]
    out = fx.hb1_metrics(fix, events, crawler, 0.1)
    assert out["roll_abs_max_after_loc_deg"] == pytest.approx(0.40)  # t 2.0 .. 4.0 s
    assert out["side_sink_after_loc_mm"] == [pytest.approx(30.0), 0.0]  # (20 + 40) / 2 mm
    assert out["ds_active_s"] == pytest.approx(1.2)
    assert out["recontact_after_final_loc_N_max"] == pytest.approx(800.0)


def test_rut_clear_min_from_the_final_loc_to_ready_plus_10_s() -> None:
    log = {"t_s": [t / 10 for t in range(200)],
           "rut_clear_mm": [None if t == 30 else 50.0 - 0.1 * t for t in range(200)]}
    events = [(1.0, "crawler_liftoff_confirmed"), (1.5, "FIX_LOC_REVOKE:2.3"),
              (2.0, "crawler_liftoff_confirmed")]
    # window 2.0 .. 5.0 + 10 = 15.0 s: least value at 15.0 s (50 - 15)
    assert fx.rut_clear_min_after_final_loc_mm(log, events, 5.0) == pytest.approx(35.0)
    assert fx.rut_clear_min_after_final_loc_mm(log, events, None) == pytest.approx(30.1)
    assert fx.rut_clear_min_after_final_loc_mm(log, [], 5.0) is None  # no LOC
    assert fx.rut_clear_min_after_final_loc_mm(None, events, 5.0) is None


def test_exact_ids_do_not_take_the_longer_ids() -> None:
    cases = [("H6|J1|B|top|flat", 1), ("H6|J1|B|top|flat|m1.2", 2), ("base|rigid|0,0|top", 3)]
    assert fx._filtered(cases, "H6|J1|B|top|flat") == cases[:2]  # substring: both
    assert fx._filtered(cases, "", "H6|J1|B|top|flat") == cases[:1]
    assert fx._filtered(cases, "", "base|rigid|0,0|top; H6|J1|B|top|flat|m1.2") == cases[1:]
    assert fx._filtered(cases, "", "H6|J9") == []


def test_ids_are_checked_over_all_suites(monkeypatch) -> None:
    suites = {"h6": [("H6|a", 1)], "g6": [("ref|b", 2)]}
    monkeypatch.setattr(fx, "suite_cases", lambda suite: suites[suite])
    fx._check_ids("h6,g6", "H6|a;ref|b")  # each id in one of the suites
    with pytest.raises(ValueError, match="unknown"):
        fx._check_ids("h6", "H6|a;ref|b")


def test_plant_truth_row() -> None:
    class Soil:
        z = np.array([0.001, 0.002, 0.003, 0.004])

    class Plant:
        soil = Soil()

        def attitude(self):
            return math.radians(0.5), 0.0

    assert fx.plant_truth_row(1.0, None) == (1.0, None, None)
    t_s, roll_deg, sink_mm = fx.plant_truth_row(1.0, Plant())
    assert roll_deg == pytest.approx(0.5) and sink_mm == pytest.approx([1.0, 2.0, 3.0, 4.0])


# --- 1, 5: harness -----------------------------------------------------------------------------


@pytest.mark.slow
def test_1_5_harness(tmp_path) -> None:
    """1: ``current`` keeps the stored L1gs hashes; DS on the G1 case (gate closed) as well.
    5: on J1 B x1.1 the first hold comes after the final LOC."""
    if not HARNESS_PYTHON.exists() or not STORED_L1GS.exists():
        pytest.skip("dynamics-dev or the rev. 83 L1gs records missing")
    out_path = tmp_path / "ds.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "OMP_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run(
        [str(HARNESS_PYTHON), "-I", "-B", str(WRAPPER_SCRIPT), "run", "--suite", "h6",
         "--candidates", "current,DS", "--filter", f"{SOFT_CASE},{HARD_CASE}",
         "--workers", "4", "--out", str(out_path)],
        cwd=ROOT, env=environment, check=True, capture_output=True, timeout=1800,
    )
    records = {(r["id"], r["candidate"]): r
               for r in json.loads(out_path.read_text(encoding="utf-8"))["records"]}
    stored = {r["id"]: r["hash"] for r in json.loads(STORED_L1GS.read_text(encoding="utf-8"))
              ["records"] if r["candidate"] == "L1gs"}
    # The R8 preset carries the 03_src P-S8-35 (DSb75): its gate stays closed on G1, so the
    # G1 current keeps the L1gs hash; the J1 current is test_c2_p35 test 9.
    assert records[(HARD_CASE, "current")]["hash"] == stored[HARD_CASE]
    assert records[(HARD_CASE, "current")]["metrics"]["ds_events"] == []
    assert records[(HARD_CASE, "DS")]["hash"] == stored[HARD_CASE]
    soft = records[(SOFT_CASE, "DS")]
    events = [(t, name) for t, name in soft["metrics"]["fix_events"]]
    holds = [t for t, name in events if name.startswith(fx.DS_HOLD_EVENT)]
    locs = [check["t_s"] for check in soft["metrics"]["window_checks"]
            if check.get("vetoed") is None]
    assert holds and locs and holds[0] > max(t for t in locs if t <= holds[0])
    assert soft["metrics"]["roll_abs_max_after_loc_deg"] is not None
    assert soft["metrics"]["rut_clear_min_after_final_loc_mm"] is not None
