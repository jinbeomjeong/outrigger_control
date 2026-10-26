"""V-2 replay tool of the R-5 fallback slope (P-S8-22 O-4, ``control/r5_fallback_replay.py``).

Synthetic: probed-leg sources and their checks, the E-6 deduction rules, the engine
allowances. Record (``07_results``, git-ignored; skipped without it): ``current_dur125`` passes
the level gate, the command source agrees with the finished round on every row, the aborted
rounds probed RL, and the 302.5 reconstruction at 127.8 s with ``L_hat_true``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config, C2Geometry
from outrigger_sim.control.r5_fallback_replay import (
    OPTIMISM_ALLOWANCE_L1_N,
    OPTIMISM_ALLOWANCE_L2B_N,
    ProbedLegSource,
    offset_allowance,
    optimism_allowance_N,
    probed_leg_track,
    replay_case,
)
from outrigger_sim.params import load_params

PERIOD_S = 0.1
FL, FR, RL = 0, 1, 2
CASE = (Path(__file__).resolve().parents[2] / "07_results" / "R3_PS2_fdown_diag_20261026"
        / "current_dur125")


def _times(count: int) -> np.ndarray:
    return np.round((np.arange(count) + 1) * PERIOD_S, 10)


def _probe_stay(moving_legs: list[int]) -> tuple[list[str], np.ndarray]:
    """Phases after each update and computed commands of one PROBE stay ended by a re-level:
    the entering update (watch phase not PROBE), one watched PROBE update per moving leg,
    and the aborting update (after it LEVEL, its command a LEVEL one)."""
    phases = ["probe"] * (1 + len(moving_legs)) + ["level"]
    computed = np.zeros((len(phases), 4))
    for offset, leg in enumerate(moving_legs):
        computed[1 + offset, leg] = 1e-3
    computed[-1] = 2e-3  # the LEVEL command of the aborting update is not a probe move
    return phases, computed


def _run(*stays: tuple[list[str], np.ndarray]):
    phases = ["ready"]
    computed = [np.zeros((1, 4))]
    for stay_phases, stay_computed in stays:
        phases += stay_phases
        computed.append(stay_computed)
    return _times(len(phases)), np.array(phases), np.vstack(computed)


def test_command_source_picks_the_moving_leg_of_an_aborted_round() -> None:
    t_s, phases, computed = _run(_probe_stay([FL, FL, FR, RL]))
    events = [(float(t_s[-1]), "probe_aborted_low_load:FL")]
    track = probed_leg_track(t_s, phases, computed, [], events)
    # watched rows 2.. : the leg each PROBE update moves; the aborting row carries RL
    assert track.legs[2:].tolist() == [FL, FL, FR, RL, RL]
    assert set(track.sources[2:]) == {ProbedLegSource.COMMAND.value}
    assert any("unverified" in problem for problem in track.problems)
    assert not any("aborted the probe" in problem for problem in track.problems)


def test_probed_leg_equal_to_the_aborting_leg_is_a_contradiction() -> None:
    t_s, phases, computed = _run(_probe_stay([FL, RL]))
    events = [(float(t_s[-1]), "probe_aborted_low_load:RL")]
    track = probed_leg_track(t_s, phases, computed, [], events)
    assert any("RL" in problem and "aborted the probe" in problem
               for problem in track.problems)


def test_round_without_probe_move_has_no_probed_leg() -> None:
    t_s, phases, computed = _run(_probe_stay([FL, FL]))
    computed[:-1] = 0.0
    track = probed_leg_track(t_s, phases, computed, [], [])
    assert track.legs[2:].tolist() == [-1, -1, -1]
    assert set(track.sources[2:]) == {ProbedLegSource.NONE.value}


def test_command_source_must_match_every_finished_round() -> None:
    finished_phases, finished_computed = _probe_stay([FL, FR])
    finished_phases[-1] = "ready"  # the round finished
    finished_computed[-1] = 0.0
    t_s, phases, computed = _run((finished_phases, finished_computed), _probe_stay([FL]))
    history = [[
        {"leg_index": FL, "t_second_hold_end_s": float(t_s[2])},
        {"leg_index": RL, "t_second_hold_end_s": float(t_s[4])},  # the commands say FR
    ]]
    track = probed_leg_track(t_s, phases, computed, history, [])
    assert track.sources[2:5].tolist() == [ProbedLegSource.HISTORY.value] * 3
    assert track.command_history_match < 1.0
    assert any("disagrees" in problem for problem in track.problems)


def test_recorded_probed_leg_comes_first() -> None:
    t_s, phases, computed = _run(_probe_stay([FL, FR]))
    recorded = np.array([-1, RL, RL, RL, -1])
    track = probed_leg_track(t_s, phases, computed, [], [], recorded_after=recorded)
    assert track.legs[2:].tolist() == [RL, RL, RL]
    assert set(track.sources[2:]) == {ProbedLegSource.RECORD.value}


def test_e6_deduction_rules() -> None:
    present = offset_allowance({"zero_calibration": {
        "pressure_offset_allowance_N": [0.0, 5500.0, 0.0, 0.0], "result": {"t_end_s": 80.0}}}, [])
    assert present.deduction_N.tolist() == [0.0, 5500.0, 0.0, 0.0] and present.from_s == 80.0
    failed = offset_allowance({"zero_calibration": {"result": {
        "legs": [{"status": "calibrated"}, {"status": "skipped"}]}}}, [])
    assert failed.deduction_N is None
    quiet = offset_allowance({"zero_calibration": {}}, [])
    assert quiet.deduction_N.tolist() == [0.0] * 4 and "0" in quiet.note


def test_engine_allowances() -> None:
    assert optimism_allowance_N("L1") == optimism_allowance_N("L1R") == OPTIMISM_ALLOWANCE_L1_N
    assert optimism_allowance_N("L2b_NSC") == OPTIMISM_ALLOWANCE_L2B_N
    assert optimism_allowance_N(None) is None


# --- record ----------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def record_replay():
    if not CASE.is_dir():
        pytest.skip(f"{CASE} not present")
    return replay_case(CASE, C2Geometry.from_params(load_params()), C2Config().with_10hz_d1())


def _row_of(replay, t_s: float) -> dict:
    (row,) = [row for row in replay["variants"]["column_nominal"]["optimism_rows"]
              if round(row["t_s"], 1) == t_s]
    return row


def test_record_passes_the_level_gate(record_replay) -> None:
    assert record_replay["replayable"], record_replay["reasons"]
    gate = record_replay["level_gate"]
    assert gate["passed"]
    assert gate["controller"]["relevel_predicted"] == [(127.8, FL), (141.5, FL)]
    assert gate["controller"]["probe_aborted_low_load"] == [(127.8, FL), (141.5, FL)]


def test_record_command_source_matches_and_aborted_rounds_probed_rl(record_replay) -> None:
    assert record_replay["command_history_match"] == 1.0
    assert record_replay["probed_leg_source_counts"][ProbedLegSource.HISTORY.value] > 0
    t_s = np.asarray(record_replay["t_s"])
    for abort_s in (127.8, 141.5):
        row = int(np.argmin(np.abs(t_s - abort_s)))
        assert record_replay["probed_leg"][row] == RL
        assert record_replay["probed_leg_source"][row] == ProbedLegSource.COMMAND.value


@pytest.mark.parametrize(("source", "fallback_kN"), [("plant_meta", 45.06),
                                                      ("column_nominal", 20.70)])
def test_record_302_5_reconstruction_with_l_hat_true(record_replay, source, fallback_kN) -> None:
    variant = record_replay["variants"][source]
    assert variant["r5_events"] == {"relevel_predicted": [], "probe_aborted_low_load": []}
    (row,) = [row for row in variant["optimism_rows"] if round(row["t_s"], 1) == 127.8]
    assert row["rule"] == "nominal_gap"
    assert row["L_hat_fb_N"] / 1e3 == pytest.approx(fallback_kN, abs=0.05)
    assert row["L_hat_true_N"] / 1e3 == pytest.approx(88.06, abs=0.05)
    assert row["difference_N"] < 0.0
    assert variant["allowance_N"] == OPTIMISM_ALLOWANCE_L1_N
    assert variant["is_within_allowance"]
