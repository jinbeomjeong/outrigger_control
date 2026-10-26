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
from outrigger_sim.control.contact_replay import ReplayInput, ReplaySettings
from outrigger_sim.control.r5_fallback_replay import (
    OPTIMISM_ALLOWANCE_L1_N,
    OPTIMISM_ALLOWANCE_L2B_N,
    ProbedLegSource,
    RowClass,
    TrueForceSource,
    judged_summary,
    offset_allowance,
    optimism_allowance_N,
    optimism_rows,
    probed_leg_track,
    replay_case,
    row_class,
    true_forces_at,
)
from outrigger_sim.control.two_pressure import FallbackSlopeInputs
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


@pytest.mark.parametrize("source", ["plant_meta", "column_nominal"])
def test_record_official_judgement_passes(record_replay, source) -> None:
    """V-2 official verdict (control 2026-10-26): ``judged_falling`` optimism within 0.05 kN
    (L1), no missed trigger on any watched row; the rising-head rows exceed the allowance but
    are records (neither prediction fires R-5 there)."""
    assert record_replay["true_force_source"] == "F_cyl_no_friction"
    variant = record_replay["variants"][source]
    classes = variant["row_classes"]
    print(f"{source}: " + ", ".join(
        f"{kind} {entry['rows']} rows max {entry['max_difference_N']} missed {entry['missed']}"
        for kind, entry in classes.items()))
    assert variant["judgement_passed"] is True
    assert classes["judged_falling"]["rows"] > 0
    assert classes["judged_falling"]["max_difference_N"] <= OPTIMISM_ALLOWANCE_L1_N
    assert variant["watched_missed"] == 0
    assert classes["record_rising"]["max_difference_N"] > OPTIMISM_ALLOWANCE_L1_N
    assert not variant["record_level_missed_flag"]
    assert set(variant["record_level"]["by_condition"]) <= {"moving", "short", "other"}


def test_record_169_0_row_is_not_watched(record_replay) -> None:
    """The +2.1 kN level row of O-4 (169.0 s): REANCHOR, FL moving, not an R-5 period."""
    row = _row_of(record_replay, 169.0)
    print(f"169.0 s: phase {row['phase']}, watched {row['is_watched']}, "
          f"condition {row['condition']}, difference {row['difference_N']:.0f} N")
    assert (row["phase"], row["is_watched"], row["condition"]) == ("reanchor", False, "moving")
    assert row["rule"] == "level"


# --- P-1 truth source and missed triggers (synthetic) -----------------------------------------


def _write_pads(path: Path, *, with_pressure: bool) -> Path:
    t_s = np.round(np.arange(1, 1001) * 1e-3, 6)
    arrays = {"t": t_s, "F_cyl": np.full((t_s.size, 4), 50e3)}
    if with_pressure:
        arrays["F_pressure"] = np.full((t_s.size, 4), 48e3)
    np.savez(path, **arrays)
    return path


def test_truth_prefers_f_pressure(tmp_path) -> None:
    pads = _write_pads(tmp_path / "pads.npz", with_pressure=True)
    truth = true_forces_at(pads, np.array([0.1, 0.2]), {"seal_friction_N": [4e3] * 4}, "L2b")
    assert truth.source is TrueForceSource.F_PRESSURE
    assert np.all(truth.force_N == 48e3)


def test_truth_without_f_pressure_needs_no_seal_friction(tmp_path) -> None:
    pads = _write_pads(tmp_path / "pads.npz", with_pressure=False)
    t_s = np.array([0.1, 0.2])
    with_friction = true_forces_at(pads, t_s, {"seal_friction_N": [4e3, 4e3, 3.3e3, 3.3e3]},
                                   "L2b_NSC")
    assert with_friction.force_N is None and "seal friction" in with_friction.note
    unknown = true_forces_at(pads, t_s, {}, "L2b_NSC")
    assert unknown.force_N is None
    frictionless = true_forces_at(pads, t_s, {"seal_friction_N": [0.0] * 4}, "L2b_NSC")
    assert frictionless.source is TrueForceSource.F_CYL_NO_FRICTION
    l1 = true_forces_at(pads, t_s, {}, "L1")
    assert l1.source is TrueForceSource.F_CYL_NO_FRICTION and np.all(l1.force_N == 50e3)


def _ready_input(lower_N: np.ndarray) -> ReplayInput:
    count = lower_N.shape[0]
    marks = np.zeros((count, 4), dtype=bool)
    return ReplayInput(
        t_s=_times(count), watch_phase=np.full(count, "ready"), lower_reading_N=lower_N,
        seal_band_N=np.zeros((count, 4)), motor_stroke_m=np.zeros((count, 4)),
        is_lifted=np.ones(count, dtype=bool), touched=np.ones((count, 4), dtype=bool),
        probed_leg=np.full(count, -1), ge2_lift_mark=marks, ge2_trigger_mark=marks,
        probe_not_grounded_mark=marks,
    )


def _missed_case(slope_drop_N: float | None):
    """FL fallback reading flat at 60 kN; its truth falls 10 kN per period (healthy R-5
    fires from row 3); ``slope_drop_N`` = a fallback-slope ``D`` on every row, or level."""
    count = 6
    lower = np.full((count, 4), 80e3)
    lower[:, FL] = 60e3 - 100.0 * np.arange(count)  # falling a little: latest < previous
    truth = np.full((count, 4), 80e3)
    truth[:, FL] = 60e3 - 10e3 * np.arange(count)
    slope_inputs = np.full((count, 4), None, dtype=object)
    if slope_drop_N is not None:
        gain = 1.3273229e-2 + 3.76991118e-3
        for row in range(count):
            slope_inputs[row, FL] = FallbackSlopeInputs(
                slope_drop_N / gain, 0.0, 1.0, 1.0, 1.0, 1.3273229e-2, 3.76991118e-3)
    settings = ReplaySettings.from_config(C2Config().with_10hz_d1(), 9414.59)
    rows = optimism_rows(_ready_input(lower), slope_inputs, (0, None, None, None), truth,
                         np.zeros((count, 4)), settings)
    return rows, judged_summary(rows, OPTIMISM_ALLOWANCE_L1_N)


def test_missed_trigger_on_level_rows_fails_the_judgement() -> None:
    rows, summary = _missed_case(None)
    assert [row["is_missed"] for row in rows] == [True, True, True]
    assert {row["condition"] for row in rows} == {"other"}
    assert {row["row_class"] for row in rows} == {"record_level"}
    assert summary["record_level"]["by_condition"]["other"]["missed"] == 3
    assert summary["record_level_missed_flag"]
    assert summary["watched_missed"] == 3
    assert summary["judgement_passed"] is False  # (ii): every watched row


def test_missed_trigger_on_judged_rows_fails_the_judgement() -> None:
    rows, summary = _missed_case(1e3)  # D far below the true fall: the fallback R-5 stays quiet
    assert {row["row_class"] for row in rows} == {"judged_falling"}
    assert summary["row_classes"]["judged_falling"]["missed"] == 3
    assert summary["judgement_passed"] is False
    _, fires = _missed_case(40e3)  # D of the true fall: both fire, nothing missed
    assert fires["watched_missed"] == 0


def test_row_classes() -> None:
    base = {"is_watched": True, "rule": "nominal_gap", "head_drop_Pa": 0.0}
    assert row_class(base) is RowClass.JUDGED_FALLING  # Dh = 0 is judged
    assert row_class({**base, "head_drop_Pa": -1.0}) is RowClass.RECORD_RISING
    assert row_class({**base, "rule": "level", "head_drop_Pa": None}) is RowClass.RECORD_LEVEL
    assert row_class({**base, "is_watched": False}) is RowClass.UNWATCHED
