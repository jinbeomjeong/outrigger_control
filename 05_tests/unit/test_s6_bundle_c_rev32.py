"""Spec rev. 32 163.2 cad work: C-R4 (item 5a window = 1 s x record rate), C-R5 (CHECK
attitude error row, A1 rejection run row), C-R7 (G4 settlement phase offset, rerun32 set)."""

from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s6_bundle_c as bc
from outrigger_sim.verify import s6_control as s6

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"


# --- C-R4 ------------------------------------------------------------------------------------


@pytest.mark.parametrize(("rate", "samples"), [(50.0, 50), (10.0, 10), (100.0, 100)])
def test_rocking_window_is_one_second_of_samples(rate: float, samples: int) -> None:
    t = np.arange(0.0, 20.0, 1.0 / rate)
    assert s6.rocking_window_samples(t) == samples
    assert s6.rocking_window_samples(None) == s6.ROCKING_WINDOW_SAMPLES


def test_rocking_amplitude_10hz_ramp_corner_is_not_read_as_rocking() -> None:
    """A ramp with a corner (LEVEL end) on a 10 Hz record: the 5 s window (old 50 samples) reads
    the curvature, the 1 s window (10 samples) does not."""
    t = np.arange(0.0, 30.0, 0.1)
    roll = np.where(t < 15.0, 0.1 * (15.0 - t), 0.0)  # deg, 0.1 deg/s ramp to 0 then flat
    att = np.column_stack([roll, np.zeros_like(roll)])
    old = s6._rocking_amp_deg(att)  # no time vector: 50 samples
    new = s6._rocking_amp_deg(att, t)
    assert old > 0.04
    assert new < old / 3.0
    # a 2 Hz rocking of 0.03 deg is still seen with the 1 s window
    rock = att + np.column_stack([0.03 * np.sin(2 * np.pi * 2.0 * t + 0.3), np.zeros_like(t)])
    assert s6._rocking_amp_deg(rock, t) > 0.02


def test_rocking_50hz_unchanged() -> None:
    rng = np.random.default_rng(1)
    t = np.round(np.arange(0.0, 10.0, 0.02), 10)
    att = rng.normal(size=(t.size, 2)) * 0.01
    assert s6._rocking_amp_deg(att, t) == s6._rocking_amp_deg(att)


# --- C-R5 ------------------------------------------------------------------------------------


def _m(final_phase: str, usage_truth: float, *, err=(0.0, -0.097), grade="ideal") -> dict:
    return {"case": "X", "final_phase": final_phase, "grade": grade,
            "check_attitude": {"code": bc.REJ_SLOPE_D8, "usage_controller": 1.0256,
                               "usage_truth_crawler": usage_truth, "usage_floor_nominal": 1.0,
                               "usage_tolerance": 0.01, "error_deg": list(err),
                               "error_maxabs_deg": max(abs(v) for v in err), "n_samples": 10,
                               "window_source": "test"}}


def test_a1_rejection_with_true_usage_inside_is_a_failure() -> None:
    row = {"item": "run", "case": "X", "value": "idle", "passed": False, "note": "",
           "kind": "function"}
    bc._a1_reject_run_row(row, _m("idle", 0.9986))
    assert row["passed"] is False and "false rejection" in row["note"]


def test_a1_rejection_with_true_usage_outside_is_info() -> None:
    row = {"item": "run", "case": "X", "value": "idle", "passed": False, "note": "",
           "kind": "function"}
    bc._a1_reject_run_row(row, _m("idle", 1.0126))
    assert row["passed"] is None and row["kind"] == "info"
    assert "correct rejection" in row["note"]


def test_ready_run_row_untouched() -> None:
    row = {"item": "run", "case": "X", "value": "ready", "passed": True, "note": "",
           "kind": "function"}
    bc._a1_reject_run_row(row, _m("ready", 0.9))
    assert row["passed"] is True and row["note"] == ""


def test_check_attitude_error_row_limits_and_graded_imu() -> None:
    rows = bc._check_attitude_rows(_m("ready", 1.0, err=(0.001, 0.016)))
    err = next(r for r in rows if r["item"].startswith("C-R5 CHECK"))
    assert err["passed"] is True and err["limit"] == bc.CHECK_ATT_ERR_LIMIT_DEG
    rows = bc._check_attitude_rows(_m("ready", 1.0, err=(0.0, 0.018)))
    assert next(r for r in rows if r["item"].startswith("C-R5 CHECK"))["passed"] is False
    rows = bc._check_attitude_rows(_m("ready", 1.0, err=(0.07, 0.07), grade="normal_zeroed"))
    assert next(r for r in rows if r["item"].startswith("C-R5 CHECK"))["passed"] is None


# --- C-R7 ------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def run_s6c():
    """Load the script as a module; its import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test", SCRIPTS / "run_S6C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield mod
    sys.modules.pop(spec.name, None)
    sys.path[:] = path


def test_rerun32_has_26_cases_in_four_groups(run_s6c) -> None:
    groups = run_s6c.rerun32_groups()
    assert {k: len(v) for k, v in groups.items()} == {"A": 7, "B": 12, "C": 3, "D": 4}
    cases = run_s6c.rerun32_cases()
    assert len({c.case_id for c in cases}) == 26
    offsets = sorted(c.settle_offset_s for c in groups["B"]
                     if c.config == "C-1" and c.scenario.contact == "pressure")
    assert offsets == [0.0, 0.025, 0.05, 0.075]
    rpb = [c for c in groups["A"] if c.scenario.floor == "rpB"]
    assert len(rpb) == 6
    roll, pitch = run_s6c.NEW_FLOORS["rpB"]
    assert abs(roll / 5.5 + pitch / 3.5 - 1.0) < 1e-4
    run_s6c.case_table()  # shared ids have one definition


def test_settle_offset_must_be_a_dt_multiple(run_s6c) -> None:
    case = next(c for c in run_s6c.rerun32_cases() if c.case_id == "C1_G4_pressure_ph0.025")
    run_s6c.check_settle_offset(case, 2.0e-4)
    with pytest.raises(ValueError):
        run_s6c.check_settle_offset(case, 3.0e-4)
    from dataclasses import replace

    bad = replace(next(c for c in run_s6c.rerun32_cases()
                       if c.case_id == "C1_D8_top_rpB_b1.6"), settle_offset_s=0.05)
    with pytest.raises(ValueError):
        run_s6c.check_settle_offset(bad, 2.0e-4)


def test_settle_checks_start_follows_the_offset() -> None:
    tp = np.arange(0.0, 30.0, 1e-3)
    f = np.full((tp.size, 4), 50e3)
    f[(tp >= 15.0) & (tp < 15.05), 3] = 1e3  # dip just before ready + 5 + 0.075
    case = {"pads": {"t": tp, "F_cyl_min_interval": f},
            "result": {"phases": [[0.0, "level"], [10.0, "ready"]],
                       "settings": {"bundle_c": {"settle_offset_s": 0.075}}},
            "rec": {"t": np.arange(0.0, 30.0, 0.1), "F_cyl": np.full((300, 4), 50e3),
                    "body_quat_wxyz": np.tile([1.0, 0.0, 0.0, 0.0], (300, 1))}}
    metrics = {"times_s": {"t0": 0.0, "ready": 10.0, "end": 29.9}, "F_min_N": 9414.59}
    out = s6.settle_checks(case, metrics)
    assert math.isclose(out["settlement_start_s"], 15.075)
    assert out["min_cyl_after_start_kN"] == pytest.approx(50.0)
