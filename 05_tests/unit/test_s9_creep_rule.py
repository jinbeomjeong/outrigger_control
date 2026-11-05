"""P3-4 creep rule of spec 433 (2026-11-05): sinkage rate over 1 s, a short window is no pass.

The stored-rows test recomputes the 116 rows of ``creep_window_recalc.json`` from their result
folders with the code of ``run_S9.py`` and compares with that file. ``07_results`` is not in git, so
a worktree reads it from the main tree; the test skips where neither has it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9 as r9  # noqa: E402
from test_s9_p3b_records import _run  # noqa: E402  (same test folder)

MAIN_TREE_ROOT = Path(r"C:\workspace\outrigger_control")
RECALC_JSON = (
    ROOT / "06_analysis/02_control/touch_phase/chrono/k1soil/creep_window_recalc.json"
)
S9_RESULTS = Path("07_results") / "S9"
STORED_ROW_COUNT = 116
J2_ROW = ("batch_FINAL-REP_20261030_223359", "P3b_J2_B_top_Fs4_m1p1")
J2_WINDOW_S = 0.32
K1_ROW = ("batch_k1soil_G1_20261105", "S9EV_G1_FLFs8_RE1bF_on")
TAIL_FREQUENCY_HZ = 2.0
TAIL_AMPLITUDE_M = 1.0e-4
"""A 2 Hz sinkage tail as in the SCM pad edge limit cycle: 0.2 s differences reach 0.5 mm/s."""
SERIES_DT_S = 1.0e-3
RECALC_ABSMAX_TOLERANCE_DEG = 1.0e-5
LIMIT_READY_PHASES = [(1.0, "level"), (20.0, "ready")]


def _sinkage_with_tail(
    duration_s: float = 12.0, settle_s: float = 3.0
) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(0.0, duration_s, SERIES_DT_S)
    sinkage = np.zeros((t.size, 4))
    is_settled = t >= settle_s
    sinkage[is_settled, 0] = TAIL_AMPLITUDE_M * np.sin(
        2.0 * np.pi * TAIL_FREQUENCY_HZ * (t[is_settled] - settle_s)
    )
    return t, sinkage


def test_rules_of_the_decision() -> None:
    assert r9.CURRENT_CREEP_RULE == r9.CreepRule(rate_window_s=1.0, is_short_window_a_pass=False)
    assert r9.LEGACY_CREEP_RULE == r9.CreepRule(rate_window_s=0.2, is_short_window_a_pass=True)
    assert r9.CREEP_RATE_WINDOW_S == 1.0


def test_one_second_window_averages_the_two_hertz_tail() -> None:
    t, sinkage = _sinkage_with_tail()
    legacy = r9.creep_stop(t, sinkage, 1.0, window_s=r9.LEGACY_CREEP_RATE_WINDOW_S)
    current = r9.creep_stop(t, sinkage, 1.0)
    assert legacy["t_final_two_sided_s"] is None
    assert current["t_final_two_sided_s"] is not None
    assert current["rate_window_s"] == 1.0
    assert legacy["rate_window_s"] == 0.2


def _attitude_series(end_pitch_deg: float) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(0.0, 30.0, 0.01)
    roll_pitch = np.zeros((t.size, 2))
    roll_pitch[:, 1] = end_pitch_deg
    return t, roll_pitch


SHORT_WINDOW_CREEP = {"t_final_s": 10.0, "t_final_two_sided_s": 29.68}
"""Leaves 0.32 s to the end of :func:`_attitude_series`, as the stored J2 row."""


def test_short_window_inside_the_limit_is_a_flag_not_a_pass() -> None:
    t, roll_pitch = _attitude_series(end_pitch_deg=0.03)
    window = r9.p34_judgement_window(t, roll_pitch, SHORT_WINDOW_CREEP, LIMIT_READY_PHASES)
    assert window["window_short"] and "window_short" in window["flags"]
    assert window["verdict"] == "flag"
    assert window["within_0p2"] is False
    assert window["absmax_within_0p2_record"] is True


def test_short_window_above_the_limit_stays_a_fail() -> None:
    t, roll_pitch = _attitude_series(end_pitch_deg=0.25)
    window = r9.p34_judgement_window(t, roll_pitch, SHORT_WINDOW_CREEP, LIMIT_READY_PHASES)
    assert window["verdict"] == "fail"
    assert window["within_0p2"] is False


def test_legacy_rule_counts_a_short_window_as_before() -> None:
    t, roll_pitch = _attitude_series(end_pitch_deg=0.03)
    window = r9.p34_judgement_window(
        t, roll_pitch, SHORT_WINDOW_CREEP, LIMIT_READY_PHASES, rule=r9.LEGACY_CREEP_RULE
    )
    assert window["window_short"]
    assert window["verdict"] == "pass"
    assert window["within_0p2"] is True


def test_no_creep_stop_is_a_fail() -> None:
    t, roll_pitch = _attitude_series(end_pitch_deg=0.03)
    creep = {"t_final_s": None, "t_final_two_sided_s": None}
    window = r9.p34_judgement_window(t, roll_pitch, creep, LIMIT_READY_PHASES)
    assert window["verdict"] == "fail"
    assert window["within_0p2"] is False


def test_p3b_records_use_the_rule_of_the_context() -> None:
    series, rows, events, phases, ctx = _run()
    current = r9.p3b_records(series, rows, events, phases, ctx)
    legacy = r9.p3b_records(
        series, rows, events, phases, {**ctx, "creep_rule": r9.LEGACY_CREEP_RULE}
    )
    assert current["creep_stop"]["rate_window_s"] == 1.0
    assert current["checks"]["P3-4_verdict"] == "pass"
    assert "spec 433" in current["P3-4_attitude"]["criterion"]
    assert legacy["creep_stop"]["rate_window_s"] == 0.2
    assert "spec 433" not in legacy["P3-4_attitude"]["criterion"]


def test_stored_block_keeps_its_rule_in_a_rejudgement() -> None:
    assert r9.stored_creep_rule({"creep_stop": {"rule": "over 0.2 s"}}) == r9.LEGACY_CREEP_RULE
    assert r9.stored_creep_rule({}) == r9.LEGACY_CREEP_RULE
    assert r9.stored_creep_rule({"creep_stop": {"rate_window_s": 1.0}}) == r9.CURRENT_CREEP_RULE


def test_level_option_is_absent_by_default() -> None:
    parser = r9.build_parser()
    assert not hasattr(parser.parse_args(["level", "--soil", "J1"]), "creep_rule")
    args = parser.parse_args(["level", "--soil", "J1", "--creep-rule", "legacy_0p2"])
    assert args.creep_rule == "legacy_0p2"


def _results_root() -> Path:
    for root in (ROOT, MAIN_TREE_ROOT):
        results = root / S9_RESULTS
        if results.is_dir():
            return results
    pytest.skip("07_results/S9 is not here (not in git)")


def _case_folder(results: Path, batch: str, case: str) -> Path:
    folder = results / batch / case
    if (folder / "step_series.npz").exists():
        return folder
    for series_path in (results / batch).rglob(f"{case}/step_series.npz"):
        return series_path.parent
    raise FileNotFoundError(f"{batch}/{case}")


def _judge_stored_row(folder: Path, rule: r9.CreepRule) -> dict[str, Any]:
    result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    t_from_s = result["p3b"]["creep_stop"]["t_from_s"]
    phases = [(float(p["t_s"]), str(p["phase"])) for p in result["phases"]]
    with np.load(folder / "step_series.npz", allow_pickle=False) as series:
        t = np.asarray(series["t_s"], dtype=float)
        sinkage = np.asarray(series["pad_sinkage_geometric_m"], dtype=float)
        roll_pitch = np.asarray(series["roll_pitch_deg"], dtype=float)
    creep = r9.creep_stop(t, sinkage, t_from_s, window_s=rule.rate_window_s)
    return r9.p34_judgement_window(t, roll_pitch, creep, phases, rule=rule)


def _assert_matches_recalc(window: dict[str, Any], recalc: dict[str, Any]) -> None:
    assert window["absmax_within_0p2_record"] == recalc["within"]
    if recalc["absmax"] is None:
        assert window["p34_absmax_overall_deg"] is None
    else:
        assert window["p34_absmax_overall_deg"] == pytest.approx(
            recalc["absmax"], abs=RECALC_ABSMAX_TOLERANCE_DEG
        )
    assert window["flags"] == recalc["flags"]


def test_stored_rows_match_the_recalculation_and_the_two_changes() -> None:
    results = _results_root()
    rows = json.loads(RECALC_JSON.read_text(encoding="utf-8"))["rows"]
    assert len(rows) == STORED_ROW_COUNT
    current_by_row = {}
    for row in rows:
        folder = _case_folder(results, row["batch"], row["case"])
        legacy = _judge_stored_row(folder, r9.LEGACY_CREEP_RULE)
        current = _judge_stored_row(folder, r9.CURRENT_CREEP_RULE)
        _assert_matches_recalc(legacy, row["w02"])
        _assert_matches_recalc(current, row["w10"])
        assert legacy["within_0p2"] == row["stored_within"]
        current_by_row[(row["batch"], row["case"])] = (legacy, current)

    pass_to_not_pass = [
        k for k, (a, b) in current_by_row.items() if a["within_0p2"] and not b["within_0p2"]
    ]
    assert pass_to_not_pass == []
    newly_inside = [
        k for k, (a, b) in current_by_row.items()
        if b["absmax_within_0p2_record"] and not a["absmax_within_0p2_record"]
    ]
    assert sorted(newly_inside) == sorted([J2_ROW, K1_ROW])

    _, j2_current = current_by_row[J2_ROW]
    assert j2_current["verdict"] == "flag"
    assert j2_current["within_0p2"] is False
    assert j2_current["p34_window_length_s"] == pytest.approx(J2_WINDOW_S, abs=0.005)
    _, k1_current = current_by_row[K1_ROW]
    assert k1_current["verdict"] == "pass"
    flags = [k for k, (_, b) in current_by_row.items() if b["verdict"] == "flag"]
    assert flags == [J2_ROW]
