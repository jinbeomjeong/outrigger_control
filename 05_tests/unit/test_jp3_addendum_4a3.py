"""436.9 J-P3 edition 4a addendum 4a-3 (``jp3_remedy_spec_addendum_4a3.md``) table 6: K-1 .. K-9.

* K-1 ``jp3_tjr_judge.py t8`` on the 22-job rule: 3.1 A, B and the record equality outside the
  3.2 paths (the constants equal the 3.2 table and the keys the code writes), C recorded, the
  stored line's tag and ③ revision asserted.
* K-2 .. K-4 ``t12``: READY read as ``r79_sensor_judge._ready_time`` (4.1), the four cases of
  4.2, the stored H-6 self comparison (4.1 expectation), pass -> fail on L2 only (4.3), the
  evidence rule on the VBJ0 base lines (4.4).
* K-5 the ``j9_t8`` batch with the VB record bundle (88), K-6 the dry check selection and
  summary, K-8 the F-A path equivalence judge, K-9 the 1.2 record table. K-7 runs in
  ``test_jp3_harness_units.py`` (dynamics-dev).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_record_table as record_table  # noqa: E402
import jp3_t8_rules as t8_rules  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
"""Stored files (git-ignored) of the main checkout when the run names it."""
V5_DIR = DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
H6_PATH = V5_DIR / "resume_k1" / "h6_dg3_v4on.json"
H6_SHA256 = "ea0ab94c81e58eeb83ab2b6a63494a56c16bcd4165a62de47eba5efd03f23c89"
"""4a-3 5.4."""
EVIDENCE_FOLDER = DATA_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "j4a_remedy_3b949f5"
BASELINE_FOLDER = DATA_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "baseline_221456d"
FALLBACK = "WARN_ROD_PRESSURE_FALLBACK"


# --- K-1: t8 --------------------------------------------------------------------------------

TABLE_3_2 = {
    "p3": ("extend_bound_check", "tension_truth"),
    "text": ("m2_law.rule",),
    "lock_log": ("lock_log", "lock_log_columns", "relock_count", "relock_step_over_1bar_count",
                 "max_abs_dp_tr_step_bar", "p1_retract_seed_count",
                 "p1_retract_seed_step_max_bar", "p1_retract_seed_log",
                 "p1_retract_seed_log_columns"),
    "evidence": ("rod_reading_truth_calls", "two_pressure_reads"),
}
"""The 3.2 table of addendum 4a-3, typed here from the document."""


def test_k1_allowed_paths_are_the_3_2_table_and_the_written_keys() -> None:
    import harness_hydraulics

    assert t8_rules.P3_RECORD_KEYS == TABLE_3_2["p3"]
    assert t8_rules.TEXT_ONLY_PATHS == TABLE_3_2["text"]
    assert t8_rules.LOCK_LOG_KEYS == TABLE_3_2["lock_log"]
    assert t8_rules.EVIDENCE_KEYS == TABLE_3_2["evidence"]
    assert set(harness_hydraulics._LockLog().record()) == set(t8_rules.LOCK_LOG_KEYS)
    assert t8_rules.EVIDENCE_KEYS == harness_hydraulics.ROD_READING_EVIDENCE_KEYS
    assert not {"line_fill_gate", "p1_output_exceptions", "check_delay"} & set(
        t8_rules.NEW_ONLY_KEYS)


STORED_RECORD = {"ext_lock_count": [1, 0, 0, 2], "lock_events": [[1.0, 3, True]],
                 "m2_law": {"law": "flow_limited_r5", "rule": "old text"},
                 "m2_shift_total_mm": [0.1, 0.2, 0.3, 0.4],
                 "extend_bound_check": {"breach_reads": [0, 0, 0, 0]}}


def _new_record() -> dict:
    return {**json.loads(json.dumps(STORED_RECORD)),
            "m2_law": {"law": "flow_limited_r5", "rule": "new text"},
            "extend_bound_check": {"rule_revision": 5},
            **{key: 1 for key in t8_rules.LOCK_LOG_KEYS},
            "rod_reading_truth_calls": 0, "two_pressure_reads": 4}


def _t8_line(setting: str, case: int, record: dict, *, events=None, tag="final_C4G2_P3H_LAS_K1",
             commands: str | None = None) -> dict:
    return {"job": {"case": f"C{case}", "eps": 0.0, "setting": setting},
            "commands_sha256": commands or f"{case:064d}", "controller_tag": tag,
            "event_names": ["INFO_X"], "events": events or [[1.0, "INFO_X"]],
            "hydraulics_record": record, "t4h_file": f"C{case}_{setting}.npz"}


def _t8_inputs(change=None, jobs: int = 22) -> tjr.T8Inputs:
    keys = [tjr._job_identity({"case": f"C{k}", "eps": 0.0}) for k in range(22)]
    stored = {"VB": {}}
    rerun = {setting: {} for setting in ("VBH", "VBJ", "VBJ0", "VB")}
    for k, key in enumerate(keys):
        stored["VB"][key] = _t8_line("VB", k, dict(STORED_RECORD), tag=t8_rules.STORED_TAG)
        for setting in rerun:
            if k < jobs:
                rerun[setting][key] = _t8_line(setting, k, _new_record())
    meta = {key: {"two_pressure_settings": {"extend_start_bound": {"revision": 4}}}
            for key in keys}
    inputs = tjr.T8Inputs(tuple(keys), stored, rerun, meta, {key: {} for key in keys})
    if change is not None:
        change(inputs, keys[3])
    return inputs


def _t8_status(change=None, jobs: int = 22) -> tuple[dict, str]:
    problems = compare.Problems()
    report = tjr.judge_t8(_t8_inputs(change, jobs), problems)
    return report, problems.status()


def test_k1_allowed_differences_pass_and_the_c_record_is_written() -> None:
    report, status = _t8_status()
    assert status == compare.STATUS_PASS
    assert report["T-JR-10"]["passing"] == 22 and report["T-JR-11"]["equal"] == 22
    assert report["T-JR-10"]["pair_rows"][0]["C_record"] == {"record": "no record"}
    assert report["VB_rerun_record"]["stop_before_reading_T-JR-10"] is False


def _set_new_record(inputs, key, path, value):
    inputs.rerun["VBH"][key]["hydraulics_record"][path] = value


@pytest.mark.parametrize(("change", "status"), [
    (lambda inputs, key: _set_new_record(inputs, key, "m2_shift_total_mm", [9.0] * 4),
     compare.STATUS_FAILED),                                       # outside the list
    (lambda inputs, key: _set_new_record(inputs, key, "check_delay", {"x": 1}),
     compare.STATUS_FAILED),                                       # P1 / M1c key on VBH
    (lambda inputs, key: inputs.stored["VB"][key]["hydraulics_record"].update(
        relock_count=7), compare.STATUS_FAILED),                   # allowed key stored, differs
    (lambda inputs, key: inputs.rerun["VBH"][key].update(
        event_names=["INFO_X", FALLBACK], events=[[1.0, "INFO_X"], [2.0, f"{FALLBACK}:RR"]]),
     compare.STATUS_FAILED),                                       # A on the new side
    (lambda inputs, key: inputs.stored["VB"][key].update(
        events=[[1.0, "INFO_X"], [2.0, f"{FALLBACK}:RR"]]), compare.STATUS_FAILED),
    (lambda inputs, key: inputs.rerun["VBH"][key].update(commands_sha256="f" * 64),
     compare.STATUS_FAILED),                                       # B
    (lambda inputs, key: inputs.rerun["VBJ"][key].update(commands_sha256="f" * 64),
     compare.STATUS_FAILED),                                       # T-JR-11
    (lambda inputs, key: inputs.stored["VB"][key].update(controller_tag="final_C4G2_P3_LAS"),
     compare.STATUS_NOT_JUDGEABLE),                                # stored tag
    (lambda inputs, key: inputs.stored_meta.update(
        {key: {"two_pressure_settings": {"extend_start_bound": {"revision": 5}}}}),
     compare.STATUS_NOT_JUDGEABLE),                                # stored ③ revision
    (lambda inputs, key: inputs.stored_meta.update({key: None}),
     compare.STATUS_NOT_JUDGEABLE),                                # stored T4h missing
])
def test_k1_t8_conditions(change, status) -> None:
    assert _t8_status(change)[1] == status


def test_k1_t8_needs_exactly_the_22_jobs_and_records_vb() -> None:
    assert _t8_status(jobs=21)[1] == compare.STATUS_NOT_JUDGEABLE

    def stale_vb(inputs, key):
        inputs.rerun["VB"][key]["commands_sha256"] = "e" * 64

    report, status = _t8_status(stale_vb)
    assert status == compare.STATUS_PASS  # VB is a record only (4a-3 5.3)
    assert report["VB_rerun_record"]["stop_before_reading_T-JR-10"] is True


def test_k1_c_record_compares_the_fallback_estimates() -> None:
    record = t8_rules.fallback_estimate_record({"fallback_rod_estimate_Pa": [1.0e5, 2.0e5]},
                                               {"fallback_rod_estimate_Pa": [1.0e5, 1.5e5]})
    assert record["new_minus_stored_Pa"] == [0.0, -0.5e5]
    assert record["at_least_minus_1_Pa"] == [True, False]


# --- K-2 .. K-4: t12 ------------------------------------------------------------------------

def _line(key: int, level: str, base: dict, *, truth: int, is_p4: bool) -> dict:
    return {"key": f"cand=current#{level}|s0|h|{key}|inner", "level": level,
            "base": base, "r79": {"warn_fault": ["WARN_X"]},
            "hydraulic_options": {"rod_reading_truth": is_p4},
            "hydraulics_record": {"rod_reading_truth_calls": truth,
                                  "two_pressure_reads": max(truth, 9)}}


def _document(bases: list[dict], *, truth: int = 0, is_p4: bool | None = None) -> dict:
    """135-ish r79 lines (the first is L2); ``is_p4`` None = P4 exactly when ``truth`` > 0."""
    p4 = truth > 0 if is_p4 is None else is_p4
    return {"meta": {}, "results": [_line(k, "L2" if k == 0 else "L3", base, truth=truth,
                                          is_p4=p4) for k, base in enumerate(bases)]}


READY_BASES = [{"t_ready_s": 100.0}] * 130 + [{"t_ready": 90.0, "final_phase": "ready"}] * 3 + [
    {"final_phase": "level"}] * 2


@pytest.fixture
def stub_grades(monkeypatch):
    """Grades from the line's ``base.grade`` (default pass): the judge rows are not under
    test here (``r79_sensor_judge`` makes them)."""
    import h8_noise_judge_4368 as h8

    def grade_lines(results, judge):
        return {h8.plain_key(run["key"]): {"grade": run["base"].get("grade", h8.GRADE_PASS),
                                           "level": run["level"]} for run in results}

    monkeypatch.setattr(h8, "grade_lines", grade_lines)
    return h8


def test_k2_ready_reads_like_r79_sensor_judge() -> None:
    r79_sensor_judge = tjr._r79_judge()
    for base in ({"t_ready_s": 5.0}, {"t_ready": 6.0}, {"t_ready_s": 5.0, "t_ready": 6.0},
                 {"t_ready_s": None, "t_ready": 6.0}, {}):
        line = {"base": base}
        assert tjr.ready_time_s(line) == r79_sensor_judge._ready_time(line)
    assert tjr.ready_time_s({}) is None


@pytest.mark.parametrize(("base", "new", "kind"), [
    ({"t_ready": 90.0}, {"t_ready_s": 125.0}, "failures"),           # later than + 30 s
    ({"t_ready": 90.0}, {"t_ready_s": 119.0}, None),                 # within 30 s
    ({"t_ready_s": 90.0}, {"final_phase": "fault"}, "failures"),     # base READY, new none
    ({"final_phase": "level"}, {"final_phase": "probe"}, "both_missing"),
    ({"final_phase": "level"}, {"t_ready": 50.0}, "improved"),
])
def test_k2_ready_table_of_4_2(base, new, kind) -> None:
    cases = tjr._ready_cases({"k": {"base": base}}, {"k": {"base": new}})
    for name, rows in cases.items():
        assert bool(rows) == (name == kind), (name, rows)
    if kind == "both_missing":
        assert cases["both_missing"][0] == {"key": "k", "base_final_phase": "level",
                                            "new_final_phase": "probe"}


def test_k2_t_ready_lines_and_records(stub_grades) -> None:
    report, problems = tjr.judge_t12("VBH", _document(READY_BASES), {},
                                     _document(READY_BASES), {})
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    assert len(report["ready_both_missing_record"]) == 2 and not report["ready_failures"]


@pytest.mark.skipif(not H6_PATH.is_file(), reason="stored H-6 not present (07_results-like "
                    "stored data; run with OUTRIGGER_RECORDS_ROOT)")
def test_k2_stored_h6_self_comparison(stub_grades) -> None:
    """4a-3 4.1 check before any run: H-6 as base and as new gives not judgeable 0, failures 0,
    7 pairs without READY on both sides, 135 pairs, 1 L2 line (grades stubbed: the READY
    reading is under test)."""
    assert hashlib.sha256(H6_PATH.read_bytes()).hexdigest() == H6_SHA256
    h6 = json.loads(H6_PATH.read_text(encoding="utf-8"))
    report, problems = tjr.judge_t12("VBH", h6, {}, h6, {})
    assert problems.not_judgeable == [] and problems.failures == []
    assert len(report["ready_both_missing_record"]) == 7
    assert report["pairs"] == 135
    assert sum(run.get("level") == "L2" for run in h6["results"]) == 1


@pytest.mark.parametrize(("level", "base_grade", "new_grade", "status"), [
    ("L3", "pass", "fail", compare.STATUS_PASS),
    ("L2", "pass", "fail", compare.STATUS_FAILED),
    ("L2", "flag", "fail", compare.STATUS_FAILED),
    ("L2", "pass", "flag", compare.STATUS_PASS),
])
def test_k3_pass_to_fail_is_judged_on_l2_only(stub_grades, level, base_grade, new_grade,
                                              status) -> None:
    index = 0 if level == "L2" else 5
    bases = [{"t_ready_s": 100.0} for _ in range(135)]
    news = [dict(base) for base in bases]
    bases[index]["grade"], news[index]["grade"] = base_grade, new_grade
    report, problems = tjr.judge_t12("VBH", _document(bases), {}, _document(news), {})
    assert problems.status() == status
    transition = f"{base_grade}->{new_grade}"
    assert report["grade_transitions_record"][level][transition] == 1


def test_k4_vbj0_base_lines_need_the_p4_evidence(stub_grades, monkeypatch) -> None:
    monkeypatch.setattr(tjr, "_dg3_j_p3", lambda lines, problems: {"status": "pass"})
    bases = [{"t_ready_s": 100.0}] * 135
    _, problems = tjr.judge_t12("VBJ", _document(bases, truth=9), {},
                                _document(bases, truth=9), {})
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    _, problems = tjr.judge_t12("VBJ", _document(bases, truth=0, is_p4=True), {},
                                _document(bases, truth=9), {})
    assert problems.status() == compare.STATUS_SETTING_DEFECT
    assert all(text.startswith("base ") for text in problems.setting_defects)


# --- K-5: j9_t8, j9_case_f_path ---------------------------------------------------------------

def _main_jsonl(path: Path) -> Path:
    lines = [{"job": {"case": f"C{k}", "eps": 0.0, "setting": setting}}
             for k in range(22) for setting in ("V0", "VB")]
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return path


def test_k5_j9_t8_is_88_rows_with_the_vb_record(tmp_path, monkeypatch) -> None:
    import run_v5

    source = _main_jsonl(tmp_path / "main.jsonl")
    jobs = run_v5.j9_t8_jobs(source)
    assert len(jobs) == 88
    assert {job["setting"] for job in jobs} == {"VBH", "VBJ", "VBJ0", "VB"}
    monkeypatch.setattr(run_v5, "P3_HASH_SOURCE_OVERRIDE", [None])
    run_v5._parse_args(["j9_t8", "--p3-hash-source", str(source)])
    assert len(run_v5.batch_jobs(run_v5.J9_T8_BATCH)) == 88
    with pytest.raises(SystemExit):
        run_v5._parse_args(["j9_cases", "--p3-hash-source", str(source)])
    path_jobs = run_v5.batch_jobs(run_v5.J9_CASE_F_PATH_BATCH)
    assert [job["offset_s"] for job in path_jobs] == list(case_judge.PATH_OFFSETS_S)
    assert all(job["setting"] == "VB" for job in path_jobs)


# --- K-6: dry check ---------------------------------------------------------------------------

def test_k6_no_candidate_outside_the_union_stops(monkeypatch) -> None:
    union = {dryrun.normalised_job(job) for job in dryrun.EVENT_CANDIDATES}
    monkeypatch.setattr(dryrun, "judged_union", lambda *args: {
        "event_union": union, "dg3_keys": set(), "sizes": {}, "union_size": len(union),
        "dg3_key_count": 0})
    with pytest.raises(dryrun.Stop, match="확인 필요"):
        dryrun.select(Path("main"), Path("baseline"), {"results": []}, {"results": []})


@pytest.mark.skipif(not (V5_DIR / "main.jsonl").is_file() or not BASELINE_FOLDER.is_dir(),
                    reason="stored main.jsonl / baseline not present")
def test_k6_selection_shows_the_jobs_outside_the_union() -> None:
    noise = {"results": [{"key": "cand=current#L2|s0|g6|52|ref|J1|top|Fs0", "level": "L2"},
                         {"key": "cand=current#L2|s9|x|1|y", "level": "L2"}]}
    dg3 = {"results": [{"key": "cand=current#L2|s0|g6|52|ref|J1|top|Fs0"}]}
    selection = dryrun.select(V5_DIR / "main.jsonl", BASELINE_FOLDER, dg3, noise)
    first = next(row for row in selection["event_candidates"] if not row["in_union"])
    assert first["job"] == selection["event_job"]
    assert selection["r79_key"] == "L2|s9|x|1|y" and selection["r79_key_in_dg3"] is False
    assert selection["union_sizes"]["j9_t8"] == 22


def test_k6_summary_holds_only_the_evidence_keys(tmp_path) -> None:
    def write(name, truth, monitor, *, r79=False):
        record = {"job": {}, "commands_sha256": "secret", "values": {"x": 1},
                  "hydraulics_record": {"rod_reading_truth_calls": truth,
                                        "two_pressure_reads": monitor,
                                        "extend_bound_check": {"breach_reads": [9] * 4}}}
        path = tmp_path / name
        text = json.dumps({"results": [record]}) if r79 else json.dumps(record) + "\n"
        path.write_text(text, encoding="utf-8")
        return path

    events = {"VBJ": write("e1", 5, 5), "VBH": write("e2", 0, 5), "VBJ0": write("e3", 4, 4)}
    r79 = {"VBJ": write("r1", 3, 3, r79=True), "VBH": write("r2", 0, 3, r79=True)}
    summary, code = dryrun.summarize(events, r79)
    assert code == dryrun.EXIT_DONE
    for row in summary["rows"]:
        for evidence in row["evidence"]:
            assert set(evidence) == {"error", "rod_reading_truth_calls", "two_pressure_reads"}
    events["VBH"] = write("e4", 2, 5)
    assert dryrun.summarize(events, r79)[1] == dryrun.EXIT_MISSED
    assert dryrun.summarize({}, r79)[1] == dryrun.EXIT_NOT_JUDGEABLE


# --- K-8: F-A path equivalence ---------------------------------------------------------------

def _path_grid() -> dict:
    runs = []
    for offset in (*case_judge.PATH_OFFSETS_S, 0.075):
        prefix = case_judge.PATH_HASH_PREFIXES.get(offset, "3a50f96eadf3")
        runs.append({"event": "G4", "offset_s": offset,
                     "commands_sha256": prefix + "0" * 52,
                     "hydraulics_record": {"extend_bound_check": {
                         "breach_reads": [0, 1, 0, 0], "min_gap_bar": [1.0, 0.5, 2.0, 3.0],
                         "min_gap_t_s": [1.0, 2.0, 3.0, 4.0]}}})
    results = [{} for _ in range(14)]
    results[13] = {"key": case_judge.GRID_KEY, "runs": runs}
    return {"results": results}


def _path_rows(grid: dict) -> list[dict]:
    rows = []
    for run in grid["results"][13]["runs"][:3]:
        rows.append({"job": {**case_judge.CASE_F_JOB, "offset_s": run["offset_s"],
                             "setting": "VB"},
                     "harness_commands_sha256": run["commands_sha256"],
                     "hydraulics_record": json.loads(json.dumps(run["hydraulics_record"]))})
    return rows


def test_k8_path_equivalence_statuses() -> None:
    grid = _path_grid()
    _, problems = case_judge.judge_case_f_path(_path_rows(grid), grid)
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    rows = _path_rows(grid)
    rows[1]["hydraulics_record"]["extend_bound_check"]["min_gap_bar"][1] += 1e-6
    _, problems = case_judge.judge_case_f_path(rows, grid)
    assert problems.status() == compare.STATUS_FAILED
    judged = {**_path_rows(grid)[0]}
    judged["job"] = {**judged["job"], "offset_s": 0.075}
    _, problems = case_judge.judge_case_f_path([*_path_rows(grid), judged], grid)
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE
    assert any("0.075" in text for text in problems.not_judgeable)


def test_k8_grid_sha_is_asserted(tmp_path) -> None:
    grid = tmp_path / "grid.json"
    grid.write_text(json.dumps(_path_grid()), encoding="utf-8")
    rows = tmp_path / "rows.jsonl"
    rows.write_text("", encoding="utf-8")
    code = case_judge.main(["case-f-path", "--out", str(tmp_path / "out.json"), "--rows",
                            str(rows), "--grid", str(grid)])
    assert code == compare.EXIT_NOT_JUDGEABLE


# --- K-9: the 1.2 record table ----------------------------------------------------------------

def test_k9_match_rule_is_the_printed_precision() -> None:
    item = record_table.SentenceValue("x", -20.008, 3, "f", ("a",))
    assert record_table.matches(item, -20.00815)
    assert not record_table.matches(item, -20.0086)


@pytest.mark.skipif(not (EVIDENCE_FOLDER / "records_full").is_dir(),
                    reason="evidence folder j4a_remedy_3b949f5 not present")
def test_k9_sentence_values_equal_the_record_files() -> None:
    table, code = record_table.build_table(EVIDENCE_FOLDER)
    assert code == record_table.EXIT_PASS, [row for row in table["rows"] if not row["matches"]]
    assert table["mismatches"] == 0 and len(table["rows"]) == len(record_table.SENTENCE_VALUES)
