"""V-2 replay tool of the R-5 fallback slope (P-S8-22 O-4, ``control/r5_fallback_replay.py``).

Synthetic: probed-leg sources and their checks, the E-6 deduction rules, the engine
allowances. Record (``07_results``, git-ignored; skipped without it): ``current_dur125`` passes
the level gate, the command source agrees with the finished round on every row, the aborted
rounds probed RL, and the 302.5 reconstruction at 127.8 s with ``L_hat_true``.

Spec rev. 62 316.6 D-1 .. D-4 (records after P-S8-22): record-only ``r8.fast_relevel`` keys,
the C-2 seal-friction record, the S8 / S7 engine settings and the same-run gate; the four V-4
records replay without a workaround and give control's verdicts.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config, C2Geometry
from outrigger_sim.control.contact_replay import (
    ReplayInput,
    ReplaySettings,
    fast_relevel_record_only_keys,
    replay_meta_from_config,
)
from outrigger_sim.control.r5_fallback_replay import (
    OPTIMISM_ALLOWANCE_L1_N,
    OPTIMISM_ALLOWANCE_L2B_N,
    GateKind,
    ProbedLegSource,
    RowClass,
    TrueForceSource,
    controller_fallback_slope_events,
    judged_summary,
    monitor_setting_differences,
    offset_allowance,
    optimism_allowance_N,
    optimism_rows,
    probed_leg_track,
    recorded_seal_friction_N,
    replay_case,
    row_class,
    run_engine,
    run_own_slope_source,
    same_run_gate,
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
    assert variant["slope_rows_missed_triggers"] == 0
    assert classes["record_rising"]["max_difference_N"] > OPTIMISM_ALLOWANCE_L1_N
    assert variant["level_missed_triggers"] == 0
    assert not variant["level_missed_trigger_flag"]
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


def test_missed_trigger_on_level_rows_is_only_flagged() -> None:
    rows, summary = _missed_case(None)
    assert [row["is_missed"] for row in rows] == [True, True, True]
    assert {row["condition"] for row in rows} == {"other"}
    assert {row["row_class"] for row in rows} == {"record_level"}
    assert summary["record_level"]["by_condition"]["other"]["missed"] == 3
    assert summary["level_missed_triggers"] == 3
    assert summary["level_missed_trigger_flag"]
    assert summary["slope_rows_missed_triggers"] == 0
    assert summary["judgement_passed"] is None  # no judged_falling row to judge


def _summary_row(row_class_name: str, *, difference_N: float, is_missed: bool) -> dict:
    """A watched row of the given class, as ``optimism_rows`` builds it."""
    is_level = row_class_name == "record_level"
    head_drop_Pa = None if is_level else (-1e5 if row_class_name == "record_rising" else 1e5)
    return {"is_watched": True, "rule": "level" if is_level else "nominal_gap",
            "head_drop_Pa": head_drop_Pa, "condition": "moving" if is_level else "met",
            "difference_N": difference_N, "fallback_drop_N": 1e3, "is_missed": is_missed}


def test_one_level_missed_trigger_passes_with_the_flag() -> None:
    rows = [
        _summary_row("judged_falling", difference_N=-200.0, is_missed=False),
        _summary_row("record_rising", difference_N=3e3, is_missed=False),
        _summary_row("record_level", difference_N=4e3, is_missed=True),
    ]
    summary = judged_summary(rows, OPTIMISM_ALLOWANCE_L1_N)
    assert summary["judgement_passed"] is True
    assert summary["level_missed_trigger_flag"] is True
    assert summary["level_missed_triggers"] == 1


def test_missed_trigger_on_a_rising_row_fails_the_judgement() -> None:
    rows = [
        _summary_row("judged_falling", difference_N=-200.0, is_missed=False),
        _summary_row("record_rising", difference_N=3e3, is_missed=True),
    ]
    summary = judged_summary(rows, OPTIMISM_ALLOWANCE_L1_N)
    assert summary["slope_rows_missed_triggers"] == 1
    assert summary["judgement_passed"] is False


def test_missed_trigger_on_judged_rows_fails_the_judgement() -> None:
    rows, summary = _missed_case(1e3)  # D far below the true fall: the fallback R-5 stays quiet
    assert {row["row_class"] for row in rows} == {"judged_falling"}
    assert summary["row_classes"]["judged_falling"]["missed"] == 3
    assert summary["judgement_passed"] is False
    _, fires = _missed_case(40e3)  # D of the true fall: both fire, nothing missed
    assert fires["slope_rows_missed_triggers"] == 0


def test_row_classes() -> None:
    base = {"is_watched": True, "rule": "nominal_gap", "head_drop_Pa": 0.0}
    assert row_class(base) is RowClass.JUDGED_FALLING  # Dh = 0 is judged
    assert row_class({**base, "head_drop_Pa": -1.0}) is RowClass.RECORD_RISING
    assert row_class({**base, "rule": "level", "head_drop_Pa": None}) is RowClass.RECORD_LEVEL
    assert row_class({**base, "is_watched": False}) is RowClass.UNWATCHED


# --- 316.6 D-1 .. D-4: records after P-S8-22 (spec rev. 62) ----------------------------------


def _nominal_gap_config(source: str = "column_nominal") -> C2Config:
    config = C2Config().with_10hz_d1()
    fast = replace(config.r8.fast_relevel, fallback_slope="nominal_gap",
                   fallback_ratio_source=source)
    return replace(config, r8=replace(config.r8, fast_relevel=fast))


C1_RECORD_KEYS = {
    "fallback_plant_ratio_source": {"kind": "plant_params", "ratio_override_keys": [],
                                    "dead_length_override_keys": [],
                                    "known_plant_ratio_upper": False},
    "fallback_ratio_source_override": None,
    "override_env_name": None,
}
"""cad C-1 record-only keys a runner adds to ``controller_meta.r8.fast_relevel``."""


def test_d1_record_only_fast_relevel_keys_are_ignored() -> None:
    config = _nominal_gap_config()
    meta = replay_meta_from_config(config)
    plain = ReplaySettings.from_controller_meta(meta, 9414.59)
    meta["r8"]["fast_relevel"] = {**meta["r8"]["fast_relevel"], **C1_RECORD_KEYS}
    with_records = ReplaySettings.from_controller_meta(meta, 9414.59)  # no TypeError
    assert with_records == plain
    assert fast_relevel_record_only_keys(meta["r8"]["fast_relevel"]) == sorted(C1_RECORD_KEYS)


def test_d1_record_only_keys_are_notes_not_differences() -> None:
    config = _nominal_gap_config()
    run_meta = {
        "two_pressure": {"settings": json.loads(json.dumps(config.two_pressure.to_meta()))},
        "r8": {"fast_relevel": {**json.loads(json.dumps(config.r8.fast_relevel.to_meta())),
                                **C1_RECORD_KEYS}},
    }
    geometry = C2Geometry.from_params(load_params())
    differences, notes = monitor_setting_differences(run_meta, config, geometry)
    assert differences == []
    for key in C1_RECORD_KEYS:
        assert any(key in note and "record-only" in note for note in notes)


def _bundle_c(**record) -> dict:
    return {"settings": {"bundle_c": {"pads_seal_fields": record}}}


def test_d2_c2_record_states_the_seal_friction() -> None:
    assert recorded_seal_friction_N(_bundle_c(F_s_front_N=0.0, friction_path=False)) == 0.0
    assert recorded_seal_friction_N(_bundle_c(F_s_front_N=4e3, friction_path=True)) == 4e3
    # contradicting or incomplete records do not say
    assert recorded_seal_friction_N(_bundle_c(F_s_front_N=4e3, friction_path=False)) is None
    assert recorded_seal_friction_N(_bundle_c(F_s_front_N=0.0, friction_path=True)) is None
    assert recorded_seal_friction_N(_bundle_c(F_s_front_N=0.0)) is None
    assert recorded_seal_friction_N({"settings": {}}) is None


def test_d2_l2b_truth_from_the_c2_record(tmp_path) -> None:
    pads = _write_pads(tmp_path / "pads.npz", with_pressure=False)
    t_s = np.array([0.1, 0.2])
    frictionless = true_forces_at(pads, t_s, {}, "L2b_NSC", recorded_seal_friction=0.0)
    assert frictionless.source is TrueForceSource.F_CYL_NO_FRICTION
    assert np.all(frictionless.force_N == 50e3)
    with_friction = true_forces_at(pads, t_s, {}, "L2b_NSC", recorded_seal_friction=4e3)
    assert with_friction.force_N is None
    # the episode meta comes first
    meta_first = true_forces_at(pads, t_s, {"seal_friction_N": [4e3] * 4}, "L2b_NSC",
                                recorded_seal_friction=0.0)
    assert meta_first.force_N is None


def test_d3_engine_from_the_s8_and_s7c_settings() -> None:
    s8 = {"settings": {"case_id": "MLJ_K0V_fdown3.5_G4RF_Fs0", "s8": {"engine": "L2b_NSC"},
                       "s7c": {"engine": "L2b_NSC"}}}
    assert run_engine(s8, {}) == "L2b_NSC"
    assert optimism_allowance_N(run_engine(s8, {})) == OPTIMISM_ALLOWANCE_L2B_N
    s7 = {"settings": {"case_id": "L1_PS2", "s7c": {"engine": "L1R"}}}
    assert run_engine(s7, {}) == "L1R"
    assert run_engine(s7, {"engine": "L2b"}) == "L2b"  # episode meta first
    assert run_engine({"settings": {"case_id": "L2b_PS2"}}, {}) == "L2b"  # case id prefix
    assert run_engine({"settings": {"case_id": "MLJ_x"}}, {}) is None


def test_d4_own_source_picks_the_gate() -> None:
    level = ReplaySettings.from_config(C2Config().with_10hz_d1(), 9414.59)
    level = replace(level, fast_relevel=replace(level.fast_relevel, fallback_slope="level"))
    assert run_own_slope_source(level) is None
    assert run_own_slope_source(replace(level, fast_relevel=None)) is None
    gap = ReplaySettings.from_config(_nominal_gap_config("plant_meta"), 9414.59)
    assert run_own_slope_source(gap) == "plant_meta"
    assert {kind.value for kind in GateKind} == {"level", "same_run"}


def test_d4_same_run_gate_needs_r5_and_every_info_event() -> None:
    events = [(127.8, "INFO_R5_FALLBACK_SLOPE:FL:11.44:0.00"), (127.8, "relevel_predicted:FL"),
              (130.0, "INFO_R5_FALLBACK_SLOPE:FL:-0.00:1.25")]
    controller_slope = controller_fallback_slope_events(events)
    assert controller_slope == [(127.8, "FL", "11.44", "0.00"), (130.0, "FL", "-0.00", "1.25")]
    controller_r5 = {"relevel_predicted": [(127.8, FL)], "probe_aborted_low_load": []}
    variant = {"r5_events": controller_r5,
               "fallback_slope_events": [(127.8, "FL", (11.4449, 0.0)),
                                         (130.0, "FL", (-0.001, 1.2504))]}
    assert same_run_gate(variant, controller_r5, controller_slope)["passed"]
    off_by_a_cent = {**variant, "fallback_slope_events": [(127.8, "FL", (11.43, 0.0)),
                                                          (130.0, "FL", (-0.001, 1.2504))]}
    gate = same_run_gate(off_by_a_cent, controller_r5, controller_slope)
    assert not gate["passed"] and gate["r5_equal"] and not gate["fallback_slope_equal"]
    assert gate["first_fallback_slope_difference"] == ((127.8, "FL", "11.43", "0.00"),
                                                       (127.8, "FL", "11.44", "0.00"))
    missing = {**variant, "fallback_slope_events": variant["fallback_slope_events"][:1]}
    assert not same_run_gate(missing, controller_r5, controller_slope)["passed"]
    no_r5 = {**variant, "r5_events": {"relevel_predicted": [], "probe_aborted_low_load": []}}
    assert not same_run_gate(no_r5, controller_r5, controller_slope)["r5_equal"]


# V-4 records of spec rev. 62 316.2 / 316.3 (git-ignored; skipped without them): the fixed tool
# replays them without a workaround and gives control's verdicts (316.2 / 316.3 tables).
RESULTS = Path(__file__).resolve().parents[2] / "07_results"
V4_CASES = {
    # label: (case folder, own source, engine, INFO count, judged_falling max [kN])
    "L1_PS2": ("S7/ctrl3_check_20261027_010709/L1_PS2_fdown3.5_old_worst_nocal",
               "plant_meta", "L1R", 7, -0.133),
    "L2b_PS2": ("S7/ctrl3_check_20261027_010707/L2b_PS2_fdown3.5_old_worst_nocal",
                "column_nominal", "L2b_NSC", 22, -3.05),
    "G4RF_Fs0": ("S8/v4_c29_Fs0_20261027_011211/MLJ_K0V_fdown3.5_G4RF_Fs0",
                 "column_nominal", "L2b_NSC", 14, -15.29),
    "G4RF_Fs8": ("S8/v4_c29_Fs8_20261027_011151/MLJ_K0V_fdown3.5_G4RF_Fs8",
                 "column_nominal", "L2b_NSC", 6, -5.99),
}


def _run_config(case: Path) -> C2Config:
    """The run's preset with its recorded ratio source (L1: ``plant_meta`` + plant ratio)."""
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    fast = result["controller_meta"]["r8"]["fast_relevel"]
    config = C2Config().with_10hz_d1()
    if fast["fallback_ratio_source"] == "column_nominal":
        return config
    ratio = fast.get("fallback_plant_ratio")
    return config.with_fallback_ratio_source(fast["fallback_ratio_source"],
                                             None if ratio is None else tuple(ratio))


@pytest.fixture(scope="module", params=sorted(V4_CASES))
def v4_replay(request):
    folder, *expected = V4_CASES[request.param]
    case = RESULTS / folder
    if not case.is_dir():
        pytest.skip(f"{case} not present")
    replay = replay_case(case, C2Geometry.from_params(load_params()), _run_config(case))
    return replay, expected


def test_v4_record_passes_the_same_run_gate(v4_replay) -> None:
    replay, (own_source, engine, info_count, _) = v4_replay
    assert replay["replayable"], replay["reasons"]
    assert replay["gate"] == {"kind": "same_run", "passed": True}
    assert replay["level_gate"]["role"] == "record"
    gate = replay["same_run_gate"]
    assert gate["source"] == own_source
    assert gate["r5_equal"] and gate["fallback_slope_equal"]
    assert gate["controller_fallback_slope_count"] == info_count
    assert replay["engine"] == engine


def test_v4_record_official_judgement(v4_replay) -> None:
    replay, (own_source, _, _, worst_kN) = v4_replay
    variant = replay["variants"][own_source]
    judged = variant["row_classes"]["judged_falling"]
    print(f"{replay['case']}: judged_falling {judged}")
    assert variant["judgement_passed"] is True
    assert judged["max_difference_N"] / 1e3 == pytest.approx(worst_kN, abs=0.01)
    assert variant["slope_rows_missed_triggers"] == 0


def test_v4_own_source_is_replayed_even_when_not_asked() -> None:
    folder, own_source, *_ = V4_CASES["L1_PS2"]
    case = RESULTS / folder
    if not case.is_dir():
        pytest.skip(f"{case} not present")
    replay = replay_case(case, C2Geometry.from_params(load_params()), _run_config(case),
                         sources=("column_nominal",))
    assert set(replay["variants"]) == {"column_nominal", own_source}
    assert replay["gate"] == {"kind": "same_run", "passed": True}


def test_v4_record_truth_source(v4_replay) -> None:
    """S7 records have no ``F_pressure``: ``F_cyl`` (L1, and L2b by the C-2 record ``F_s`` 0);
    S8 records have it."""
    replay, _ = v4_replay
    stage = Path(replay["case"]).parent.parent.name
    expected = (TrueForceSource.F_CYL_NO_FRICTION if stage == "S7"
                else TrueForceSource.F_PRESSURE)
    assert replay["true_force_source"] == expected.value
