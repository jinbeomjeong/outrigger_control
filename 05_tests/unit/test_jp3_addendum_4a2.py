"""436.9 J-P3 edition 4a addendum 4a-2 (``jp3_remedy_spec_addendum_4a2.md``): the judge tools
of the remedy (table 4).

* J4a-9 R1 / section 2: the P4-2 chain of ``jp3_baseline_compare`` (two synthetic traces: the
  E-row chain stretch -> extension -> new stretch is explained, a raise after the chain broke is
  not), R2 (missing P4-3a keys), R3 / X11 (setting defects), R4 (a revision 5 pair without its
  trace), section 3.4 (seed net force rules).
* R6: ``j_p3_inputs`` (judged revision 5 settings, an unkeyed revision 5 record) and the
  revision 4 judgement refusing a revision 5 record.
* B2: the P4 evidence rule and the install on an imported ``r64`` module.
* R7 / R8: case F batch rows and judge, the P4-5a FL read; B4: the T-JR judges' counts.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import j_p3_inputs  # noqa: E402
import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_fixed_inputs  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402

from outrigger_sim.control import extend_start_bound as esb  # noqa: E402

BAR = 1.0e5
CLASS_NAMES = np.array(["lock", "hold", "carry_ext", "carry_ret", "ext", "ret"])
SOURCE_NAMES = np.array(list(esb.JP3_SOURCE_NAMES))
LOCK, EXT, CARRY_EXT, RET = 0, 4, 2, 5
TRACKER = list(esb.JP3_SOURCE_NAMES).index("retract_tracker")
EXTEND_BOUND = list(esb.JP3_SOURCE_NAMES).index("extend_bound")
PILOT = list(esb.JP3_SOURCE_NAMES).index("pilot_model")
RR = 3


# --- P4-2 chain (4a-2 2.2, J4a-9 R1) ---------------------------------------------------------

def _trace(classes: list[int], sources: list[int], used_new: list[float],
           used_old: list[float], ext_new: list[float], ext_old: list[float]):
    """New and baseline arrays of one RR trace (other legs constant, never raised)."""
    count = len(classes)

    def legs(values, fill):
        array = np.full((count, 4), fill, dtype=float)
        array[:, RR] = values
        return array

    new = {"jp3_t_s": np.round(0.1 * np.arange(1, count + 1), 9),
           "jp3_class": legs(classes, LOCK).astype(np.int8),
           "jp3_class_names": CLASS_NAMES,
           "jp3_used_bound_Pa": legs(used_new, 50 * BAR),
           "jp3_ext_bound_Pa": legs(ext_new, 30 * BAR),
           "jp3_model_bound_source": legs(sources, PILOT).astype(np.int8),
           "jp3_source_names": SOURCE_NAMES,
           "jp3_model_bound_inherited": np.zeros((count, 4), dtype=bool)}
    old = {"jp3_t_s": new["jp3_t_s"].copy(), "jp3_class": new["jp3_class"].copy(),
           "jp3_used_bound_Pa": legs(used_old, 50 * BAR),
           "jp3_ext_bound_Pa": legs(ext_old, 30 * BAR)}
    return new, old


def test_p4_2_chain_after_a_retraction_stretch_is_explained() -> None:
    """4a-2 2.2 (unit test 1 of J4a-9 R1): the baseline E-row chain shape, a stretch after a
    retraction whose ④ is the R5-7 term (raised), an extension carrying the raised ``p_hat``,
    a new stretch whose ④ = the raised ``p_hat + delta_m`` (source ``extend_bound``): 0
    unexplained raises."""
    classes = [RET, LOCK, LOCK, EXT, EXT, CARRY_EXT, LOCK, LOCK]
    sources = [-1, TRACKER, TRACKER, -1, -1, -1, EXTEND_BOUND, EXTEND_BOUND]
    used_old = [np.nan, 60, 60, 40, 40, 40, 45, 45]
    used_new = [np.nan, 70, 70, 52, 52, 52, 52, 52]
    ext_old = [40, 40, 40, 40, 40, 40, 45, 45]
    ext_new = [40, 52, 52, 52, 52, 52, 52, 52]
    new, old = _trace(classes, sources, [v * BAR for v in used_new],
                      [v * BAR for v in used_old], [v * BAR for v in ext_new],
                      [v * BAR for v in ext_old])
    counts = compare._read_counts(new, old)
    assert counts["raised_reads"] == 7
    assert counts["unexplained_raised_reads"] == 0
    assert counts["explained_by_stretch_source"] == 2
    assert counts["explained_by_tracker_chain"] == 3
    assert counts["explained_by_lookback"] == 2
    assert counts["lowered_reads"] == 0 and counts["bad_class_changes"] == 0


def test_p4_2_raise_after_the_chain_broke_is_unexplained() -> None:
    """4a-2 2.2 (unit test 2): after the R5-7 stretch the extension's ``p_hat`` falls back to
    the baseline (``E`` false) for longer than the 0.3 s lookback; a later stretch's raise is
    unexplained (P4-2 can still fail)."""
    classes = [RET, LOCK, LOCK, EXT, EXT, EXT, EXT, EXT, EXT, LOCK]
    sources = [-1, TRACKER, TRACKER, -1, -1, -1, -1, -1, -1, PILOT]
    used_old = [np.nan, 60, 60, 40, 40, 40, 40, 40, 40, 45]
    used_new = [np.nan, 70, 70, 40, 40, 40, 40, 40, 40, 48]
    ext_old = [40, 40, 40, 40, 40, 40, 40, 40, 40, 45]
    ext_new = [40, 52, 52, 40, 40, 40, 40, 40, 40, 45]
    new, old = _trace(classes, sources, [v * BAR for v in used_new],
                      [v * BAR for v in used_old], [v * BAR for v in ext_new],
                      [v * BAR for v in ext_old])
    counts = compare._read_counts(new, old)
    assert counts["unexplained_raised_reads"] >= 1
    row = counts["unexplained_rows"][0]
    assert row["t_s"] == pytest.approx(1.0) and row["leg"] == RR and row["class"] == "lock"
    assert row["source"] == "pilot_model"


def test_p4_2_lookback_is_the_monitor_lookback() -> None:
    from outrigger_sim.control import two_pressure

    assert compare.LOOKBACK_S == two_pressure.LOCKED_START_LOOKBACK_S


def test_p4_2_revision_5_pair_without_its_trace_is_not_judgeable(tmp_path) -> None:
    """J4a-9 R4: a revision 5 pair whose baseline npz has no trace stops (not judgeable)."""
    new, _ = _trace([LOCK], [TRACKER], [50 * BAR], [50 * BAR], [30 * BAR], [30 * BAR])
    np.savez(tmp_path / "new.npz", **new)
    np.savez(tmp_path / "old.npz", rod_pressure_Pa=np.zeros(3))
    with pytest.raises(compare.NotJudgeable, match="jp3_t_s"):
        compare.compare_reads(tmp_path / "old.npz", tmp_path / "new.npz", True)
    out = compare.compare_reads(tmp_path / "old.npz", tmp_path / "new.npz", False)
    assert out["has_trace"] is False


# --- setting defects, P4-3a / P4-4 rules -----------------------------------------------------

def _row(setting: str, check: dict | None = None, **hydraulics) -> dict:
    return {"job": {"case": "R12", "setting": setting}, "commands_sha256": "a" * 64,
            "hydraulics_record": {"extend_bound_check": check or {}, **hydraulics}}


def test_identity_applies_to_every_revision_5_row_vbg5_included() -> None:
    """J4a-9 R3: VBG5 gets the rule identity check too; a revision 4 row has none."""
    good = {"rule_revision": 5, **compare.DEFAULT_IDENTITY}
    assert compare.identity_problems(_row("VBG5", good)) == []
    bad = {**good, "retract_start_rule": "model_only"}
    assert compare.identity_problems(_row("VBG5", bad))
    assert compare.identity_problems(_row("VBG4", {"breach_reads": [0] * 4})) == []


def test_x11_row_in_the_compared_set_is_a_setting_defect() -> None:
    problems = compare.Problems()

    class EmptyBaseline:
        def rows(self, name):
            return []

    compare.pair_rows(EmptyBaseline(), [_row("LSJ4_X11")], problems)
    assert problems.setting_defects and problems.status() == compare.STATUS_SETTING_DEFECT
    problems.not_judgeable.append("x")
    assert problems.status() == compare.STATUS_SETTING_DEFECT  # the defect outranks


def test_missing_p4_3a_key_is_not_judgeable() -> None:
    """J4a-9 R2: a missing judged key is never summed as 0."""
    problems = compare.Problems()
    compare.judged_key_problems("VBJ", {"jp3a_breach_reads": [0] * 4}, {}, problems)
    assert len(problems.not_judgeable) == 3 and not problems.failures
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


SEED_COLUMNS = ["t_s", "leg", "net_force_seed_step_N", "m2_shift_clipped"]


def _seed_record(rows: list[list], count: int | None = None, columns=SEED_COLUMNS) -> dict:
    return {"p1_retract_seed_count": len(rows) if count is None else count,
            "p1_retract_seed_step_max_bar": 33.9, "p1_retract_seed_log": rows,
            "p1_retract_seed_log_columns": columns}


@pytest.mark.parametrize(("record", "status"), [
    (_seed_record([[1.0, 2, 3e-10, False]]), compare.STATUS_PASS),
    (_seed_record([[1.0, 2, -1.0e4, False]]), compare.STATUS_FAILED),
    (_seed_record([[1.0, 2, 3e-10, True]]), compare.STATUS_NOT_JUDGEABLE),     # clipped
    (_seed_record([[1.0, 2, 3e-10, False]], count=2), compare.STATUS_NOT_JUDGEABLE),
    (_seed_record([]), compare.STATUS_NOT_JUDGEABLE),                          # zero rows
    (_seed_record([[1.0, 2, 3e-10]], columns=SEED_COLUMNS[:3]), compare.STATUS_NOT_JUDGEABLE),
])
def test_p4_4_seed_net_force_rules(record, status) -> None:
    """4a-2 3.4: |net_force_seed_step_N| <= 1 N per row; a clipped row, a row count other than
    the seed count, zero rows or a missing column is not judgeable (never a pass)."""
    problems = compare.Problems()
    compare.seed_problems("VBJ", {"hydraulics_record": record}, {"hydraulics_record": record},
                          problems)
    assert problems.status() == status


# --- R6 (j_p3_inputs), revision 4 refusal ----------------------------------------------------

REV5_CLEAN = {"rule_revision": 5, **compare.DEFAULT_IDENTITY, "sensor_grade": "normal",
              **{key: [0] * 4 for key in esb.J_P3_REV5_JUDGED_KEYS}}


def _rev5_row(setting: str, keyed: bool = True) -> dict:
    row = {"p3_expected": True, "run_extend_start_rule": "tracked_bound", "setting": setting,
           "extend_bound_check": dict(REV5_CLEAN), "has_rod_reading": True}
    if keyed:
        row[j_p3_inputs.REVISION_KEY] = 5
    return row


def test_r6_revision_5_judgement_takes_the_judged_settings_only() -> None:
    result = j_p3_inputs.j_p3_over_rows([_rev5_row("VBJ"), _rev5_row("VBH")])
    assert result["rev5"]["status"] == "pass" and result["rev5"]["runs"] == 1
    assert result["rev5_unjudged_setting_runs"] == 1
    assert result["rev5_record_only"]["runs"] == 1
    only_vbh = j_p3_inputs.j_p3_over_rows([_rev5_row("VBH")])
    assert only_vbh["rev5"]["status"] == "no_judged_runs"
    assert only_vbh["status_by_revision"] == {"4": "no_p3_runs", "5": "no_judged_runs"}


def test_r6_unkeyed_revision_5_record_is_refused() -> None:
    result = j_p3_inputs.j_p3_over_rows([_rev5_row("VBJ", keyed=False)])
    assert result["status"] == "setting_defect"
    assert result["revision_key_missing_runs"] == 1 and result["runs_judged"] == 0


def test_r6_revision_4_judgement_refuses_a_revision_5_record() -> None:
    result = esb.j_p3_judgement([dict(REV5_CLEAN, breach_reads=[0] * 4)])
    assert result["status"] == "setting_defect"
    assert result["runs_by_case"][esb.J_P3_DEFECT_REVISION_5_RECORD] == 1


# --- B2 evidence ------------------------------------------------------------------------------

@pytest.mark.parametrize(("record", "options", "is_fit"), [
    ({"rod_reading_truth_calls": 5, "two_pressure_reads": 5}, {"rod_reading_truth": True}, True),
    ({"rod_reading_truth_calls": 4, "two_pressure_reads": 5}, {"rod_reading_truth": True}, False),
    ({"rod_reading_truth_calls": 0, "two_pressure_reads": 0}, {"rod_reading_truth": True}, False),
    ({"rod_reading_truth_calls": 0, "two_pressure_reads": 7}, {"rod_reading_truth": False}, True),
    ({"rod_reading_truth_calls": 0, "two_pressure_reads": 7}, None, True),
    ({"rod_reading_truth_calls": 2, "two_pressure_reads": 7}, {}, False),
    ({}, {"rod_reading_truth": True}, False),
])
def test_b2_rod_reading_evidence_rule(record, options, is_fit) -> None:
    """4a-2 B2: P4 rows 1 = 2 > 0, P4-off rows 1 = 0; missing keys are a defect."""
    assert (j_p3_inputs.rod_reading_evidence_problems(record, options) == []) is is_fit


@dataclass(frozen=True)
class _Reading:
    head_pressure_Pa: np.ndarray
    rod_pressure_Pa: np.ndarray


class _TruthPlant:
    A_ann = np.full(4, 3.0e-3)

    def plant_rod_pressure_Pa(self):
        return np.full(4, 10.0 * BAR)

    def pressure(self):
        return np.full(4, 100.0e3)


def test_b2_truth_reading_counts_its_calls_and_patches_an_imported_r64(monkeypatch) -> None:
    """4a-2 B2: the P4 reading counts its calls on the plant; the install patches an
    ``r64_g4_closed_loop`` imported before it (the standalone r67 worker)."""
    import harness_hydraulics

    plant = _TruthPlant()
    reading = _Reading(np.zeros(4), np.zeros(4))
    out = harness_hydraulics.with_plant_truth_pressures(plant, reading, np.full(4, 1.3e-2))
    harness_hydraulics.with_plant_truth_pressures(plant, reading, np.full(4, 1.3e-2))
    assert plant.rod_reading_truth_calls == 2
    assert np.allclose(out.rod_pressure_Pa, 10.0 * BAR)
    r64 = types.ModuleType("r64_g4_closed_loop")
    r64.with_two_pressures = lambda plant, m, ha: m
    study_a = types.ModuleType("s9_soil_event_screen")
    study_a._s8_modules = lambda: {"r64": r64}
    monkeypatch.setitem(sys.modules, "r64_g4_closed_loop", r64)
    monkeypatch.setitem(sys.modules, "s9_soil_event_screen", study_a)
    harness_hydraulics.install_rod_reading_truth()
    assert r64.with_two_pressures is harness_hydraulics.with_plant_truth_pressures


# --- R8 / R7: case F --------------------------------------------------------------------------

def test_r8_case_f_is_a_run_v5_batch_of_the_event_path() -> None:
    import run_v5

    jobs = run_v5.batch_jobs(run_v5.J9_CASE_F_BATCH)
    assert len(jobs) == 15
    assert [job["setting"] for job in jobs] == [
        setting for settings in case_judge.CASE_F_GROUPS.values() for setting in settings]
    for job in jobs:
        assert {k: v for k, v in job.items() if k != "setting"} == case_judge.CASE_F_JOB
    assert all(job["setting"] in run_v5.T4H_SETTINGS for job in jobs)
    assert run_v5.t4h_file_name(jobs[0]) == "R12_top-FR-Fs8-o0.075_VB.npz"


def _case_f_rows() -> list[dict]:
    rows = []
    for group, settings in case_judge.CASE_F_GROUPS.items():
        for index, setting in enumerate(settings):
            check = ({"breach_reads": [0, 3, 0, 0], "min_gap_bar": [1.0, -0.9000863, 2.0, 3.0],
                      "min_gap_t_s": [50.0, 48.7, 51.0, 52.0]} if group == "A"
                     else {"rule_revision": 5, **compare.DEFAULT_IDENTITY,
                           **{key: [0] * 4 for key in esb.J_P3_REV5_JUDGED_KEYS}})
            truth = 12 if group == "E" else 0
            rows.append({"job": {**case_judge.CASE_F_JOB, "setting": setting},
                         "commands_sha256": f"{index:064d}",
                         "harness_commands_sha256": "h" * 64,
                         "hydraulic_options": {"rod_reading_truth": group == "E"},
                         "hydraulics_record": {"extend_bound_check": check,
                                               "relock_step_over_1bar_count": 0,
                                               "rod_reading_truth_calls": truth,
                                               "two_pressure_reads": 12}})
    return rows


def _grid() -> dict:
    runs = [{} for _ in range(4)]
    runs[3] = {"event": "G4", "offset_s": 0.075, "commands_sha256": "h" * 64,
               "hydraulics_record": {"extend_bound_check": {
                   "breach_reads": [0, 3, 0, 0], "min_gap_bar": [1.0, -0.9000863, 2.0, 3.0],
                   "min_gap_t_s": [50.0, 48.7, 51.0, 52.0]}}}
    results = [{} for _ in range(14)]
    results[13] = {"key": case_judge.GRID_KEY, "runs": runs}
    return {"results": results}


def test_r7_case_f_judge_statuses() -> None:
    _, problems = case_judge.judge_case_f(_case_f_rows(), _grid())
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    rows = _case_f_rows()
    rows[5]["commands_sha256"] = "f" * 64  # VBH hash differs from VB (T8)
    _, problems = case_judge.judge_case_f(rows, _grid())
    assert problems.status() == compare.STATUS_FAILED
    rows = _case_f_rows()
    rows[10]["hydraulics_record"]["rod_reading_truth_calls"] = 0  # VBJ without P4 evidence
    _, problems = case_judge.judge_case_f(rows, _grid())
    assert problems.status() == compare.STATUS_SETTING_DEFECT
    _, problems = case_judge.judge_case_f(_case_f_rows()[:14], _grid())
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


def test_r7_x11_read_is_the_fl_hold_read_at_49_s(tmp_path) -> None:
    """P4-5a reads FL at 49.0 s: class and ``p_tr - ④``."""
    t_s = np.round(np.arange(48.5, 49.25, 0.1), 9)
    classes = np.full((t_s.size, 4), LOCK, dtype=np.int8)
    classes[np.isclose(t_s, 49.0), 0] = 1  # hold
    used = np.full((t_s.size, 4), 120.0 * BAR)
    truth = used.copy()
    truth[np.isclose(t_s, 49.0), 0] += 10.674 * BAR
    np.savez(tmp_path / "x11.npz", jp3_t_s=t_s, jp3_class=classes, jp3_class_names=CLASS_NAMES,
             jp3_used_bound_Pa=used, jp3_p_tr_Pa=truth)
    read = case_judge._x11_read(tmp_path / "x11.npz", compare.Problems())
    assert read["class"] == "hold" and read["gap_bar"] == pytest.approx(10.674)


# --- B4: T-JR judges --------------------------------------------------------------------------

def _dg3_document(fault: str | None = None, ready_s: float | None = 100.0, count: int = 135,
                  truth_calls: int = 0, setting: str = "VBH") -> dict:
    """Dg-3 lines of ``setting`` (prelaunch audit M-3 / M-8: rev 5 records of the sealed
    identity, meta ``keys_file`` = the stored H-6; 4a-5 1 T-JR-14: a J11 record with
    ``n_late_fallback`` 0)."""
    results = []
    for k in range(count):
        names = ["WARN_X"] + ([fault] if fault and k == 7 else [])
        results.append({"key": f"cand=current#L{2 if k == 0 else 3}|s0|h|{k}|inner",
                        "level": "L2" if k == 0 else "L3", "r79": {"warn_fault": names},
                        "base": {"t_ready_s": ready_s}, "v5_setting": setting,
                        "hydraulic_options": {"rod_reading_truth": truth_calls > 0},
                        "lock_window_alignment": {"n_late_fallback": 0,
                                                  "n_late_by_leg": dict.fromkeys(LEGS, 0)},
                        "hydraulics_record": {"rod_reading_truth_calls": truth_calls,
                                              "two_pressure_reads": max(truth_calls, 9),
                                              "extend_bound_check": {
                                                  "rule_revision": 5,
                                                  **compare.DEFAULT_IDENTITY}}})
    keys_file = {"sha256": jp3_fixed_inputs.H6_SHA256, "n_keys": 135}
    return {"meta": {"keys_file": keys_file}, "results": results}


def test_b4_t12_counts_faults_and_ready(monkeypatch) -> None:
    """13.9: exactly 135 pairs, 1 L2 line; a new FAULT and a missing READY fail."""
    import h8_noise_judge_4368 as h8

    monkeypatch.setattr(h8, "grade_lines", lambda results, judge: {
        h8.plain_key(run["key"]): {"grade": h8.GRADE_PASS, "level": run["level"]}
        for run in results})
    base = _dg3_document(setting="VB")
    _, problems = tjr.judge_t12("VBH", base, {}, _dg3_document(), {})
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    _, problems = tjr.judge_t12("VBH", base, {}, _dg3_document(fault="FAULT_NEW"), {})
    assert problems.status() == compare.STATUS_FAILED
    _, problems = tjr.judge_t12("VBH", base, {}, _dg3_document(ready_s=None), {})
    assert problems.status() == compare.STATUS_FAILED
    _, problems = tjr.judge_t12("VBH", base, {}, _dg3_document(count=134), {})
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE
    report, _ = tjr.judge_t12("VBH", base, {}, _dg3_document(), {})
    assert "0.1 s" in report["records"]["ret_after_gate_s_resolution"]  # R9


def test_b4_records_seed_force_rules() -> None:
    """T-JR-15 (4a-2 3.4) in the record bundle: a clipped seed row is not judgeable."""
    good = _lock_row([[1.0, 2, 0.0, False]])
    clipped = _lock_row([[1.0, 2, 0.0, True]])
    _, problems = tjr.judge_records(records_inputs([good]))
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    _, problems = tjr.judge_records(records_inputs([good, clipped]))
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE
    _, problems = tjr.judge_records(records_inputs([_lock_row([])]))
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


LEGS = ("FL", "FR", "RL", "RR")
T4H_NAMES = {runs: {f"r{runs}_{k}.npz" for k in range(runs)} for runs in tjr.REPLAY_RUN_COUNTS}
"""Stand-ins of the two fixed T4h name lists (``--t4h-sums``)."""
REPLAY_REPORTS = [{"runs": runs, "runs_over": 0, "extend_start_revision": 5,
                   "rows": [{"file": name} for name in sorted(T4H_NAMES[runs])],
                   "J-P3": {"status": "pass"}} for runs in tjr.REPLAY_RUN_COUNTS]
"""Two judged ``t4h_replay --extend-start-revision 5`` reports of the T-JR-13 run counts."""


def _lock_row(seed_rows: list[list], *, setting: str = "VBJ", relocks: int | None = 0) -> dict:
    record = _seed_record(seed_rows)
    if relocks is not None:
        record["relock_step_over_1bar_count"] = relocks
    return {"job": {"setting": setting, "case": "E"}, "hydraulics_record": record}


def records_inputs(lock_rows: list[dict], *, replays: list[dict] | None = None,
                   dg3: list[dict] | None = None) -> tjr.RecordsInputs:
    """Valid T-JR-13 / 14 inputs around the given T-JR-15 rows (4a-5 1)."""
    return tjr.RecordsInputs(
        json.loads(json.dumps(REPLAY_REPORTS if replays is None else replays)),
        [_dg3_document(setting="VBH"), _dg3_document(setting="VBJ")] if dg3 is None else dg3,
        lock_rows, T4H_NAMES)


def test_judges_refuse_to_overwrite_a_report(tmp_path) -> None:
    out = tmp_path / "report.json"
    out.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        tjr.main(["records", "--out", str(out)])
    assert stop.value.code == 2
