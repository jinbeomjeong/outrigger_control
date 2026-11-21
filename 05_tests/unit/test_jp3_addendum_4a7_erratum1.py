"""Addendum 4a-7 erratum 1 on the path 1 J-P3 judgement tools (synthetic data only).

* 9: the P4 evidence of the J-P3 judged-setting lines (VBJ, LSJ1 .. 4): an event-path line
  ① = ② > 0, a declared head-only line ① = ② = 0, a missing key a setting defect; in
  ``t12`` (VBJ bundle), ``jp3_baseline_compare`` (P4-3a rows) and ``case-f`` (F-E rows).
* 7: ``t12`` VBJ with judged rows but not the fixed number is ``judged_row_count_mismatch``.
* 3: a noise-run result line (``level``) is an event-path line.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import _case_f_rows, _grid  # noqa: E402
from test_jp3_addendum_4a5 import ROW  # noqa: E402
from test_jp3_judge_main_e2e import _baseline, _case_row, _t4h_folder, _write_rows  # noqa: E402

ERRATUM_9 = "erratum 1 9"


def _evidence(truth, reads) -> dict:
    return {"rod_reading_truth_calls": truth, "two_pressure_reads": reads}


@pytest.mark.parametrize(("record", "is_declared", "is_sound"), [
    (_evidence(12, 12), False, True),
    (_evidence(11, 12), False, False),
    (_evidence(0, 0), False, False),   # event line without rod reads
    (_evidence(0, 4), False, False),   # P4 off on a judged line
    (_evidence(0, 0), True, True),
    (_evidence(0, 3), True, False),    # declared head-only with rod reads
    ({"two_pressure_reads": 4}, False, False),  # a key missing: never read as 0
    (_evidence(True, True), False, False),      # not integers
    (None, True, False),
])
def test_judged_line_evidence_rule(record, is_declared, is_sound) -> None:
    problems = compare.judged_line_evidence_problems(record, is_declared)
    assert (problems == []) is is_sound, problems


def test_a_noise_run_line_is_an_event_line() -> None:
    """Erratum 1 3 rule 1: a line with ``level`` is not declared, whatever it says."""
    line = {"level": "L2", "head_only_declared": True, "job": {"case": "R1"}}
    assert compare.is_head_only_line(line, {"head_only_declared": True}) is False
    assert compare.is_head_only_line({"job": {"case": "R1"}}) is True       # steady case
    assert compare.is_head_only_line({"job": {"case": "C0"}}) is False      # outside: event


def _vbj_line(truth: int, reads: int, *, is_p4: bool) -> dict:
    return {"v5_setting": "VBJ", "level": "L2", "hydraulic_options": {"rod_reading_truth": is_p4},
            "hydraulics_record": {**_evidence(truth, reads), "extend_bound_check": dict(ROW)}}


@pytest.mark.parametrize(("line", "has_erratum_defect"), [
    (_vbj_line(9, 9, is_p4=True), False),
    (_vbj_line(0, 0, is_p4=False), True),  # the options rule (P4 off: 1 = 0) alone passes it
    (_vbj_line(0, 7, is_p4=False), True),
])
def test_t12_vbj_lines_need_the_judged_line_evidence(line, has_erratum_defect) -> None:
    problems = compare.Problems()
    tjr._check_lines("VBJ", {}, {"k": line}, problems)
    found = [text for text in problems.setting_defects if ERRATUM_9 in text]
    assert bool(found) is has_erratum_defect, problems.setting_defects


@pytest.mark.parametrize(("records", "status"), [
    ([dict(ROW)], "pass"),
    ([dict(ROW), dict(ROW)], tjr.JUDGED_ROW_COUNT_MISMATCH),  # judged rows, not exactly 1
    ([{**ROW, "sensor_grade": "conservative"}], "no_judged_runs"),  # zero judged rows
])
def test_t12_vbj_judged_row_count_names(records, status) -> None:
    lines = [{"hydraulics_record": {"extend_bound_check": record}} for record in records]
    problems = compare.Problems()
    assert tjr._dg3_j_p3(lines, problems)["status"] == status
    expected = compare.STATUS_PASS if status == "pass" else compare.STATUS_NOT_JUDGEABLE
    assert problems.status() == expected


@pytest.mark.parametrize(("case", "evidence", "has_erratum_defect"), [
    ("R12", _evidence(0, 4), True),    # event VBJ row with P4 off: 1 != 2
    ("R12", _evidence(5, 5), False),
    ("R1", _evidence(0, 0), False),    # a declared head-only (steady) VBJ row
    ("R1", _evidence(0, 4), True),
])
def test_baseline_compare_judged_rows_need_the_evidence(tmp_path, monkeypatch, case, evidence,
                                                        has_erratum_defect) -> None:
    row = _case_row("VBJ", case)
    row["hydraulics_record"].update(evidence)
    baseline = _baseline(tmp_path / "baseline", monkeypatch,
                         {"j9_cases.jsonl": [row], "cd.jsonl": []})
    new = _write_rows(tmp_path / "run" / "j9_cases.jsonl", [row])
    (_t4h_folder(new) / row["t4h_file"]).write_bytes(
        (baseline / "j9_cases_t4h" / row["t4h_file"]).read_bytes())
    out = tmp_path / "report.json"
    compare.main([str(baseline), "--new", str(new), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert len(report["pairs"]) == 1, report.get("not_judgeable")  # the pair was compared
    found = [text for text in report.get("setting_defects") or [] if ERRATUM_9 in text]
    assert bool(found) is has_erratum_defect, report.get("setting_defects")


def test_case_f_e_rows_need_the_judged_line_evidence() -> None:
    rows = _case_f_rows()
    _, problems = case_judge.judge_case_f(rows, _grid())
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    lsj2 = next(row for row in rows if row["job"]["setting"] == "LSJ2")
    lsj2["hydraulic_options"] = {"rod_reading_truth": False}  # the options rule: 1 = 0 passes
    lsj2["hydraulics_record"].update(_evidence(0, 12))
    _, problems = case_judge.judge_case_f(rows, _grid())
    assert problems.status() == compare.STATUS_SETTING_DEFECT
    assert any(ERRATUM_9 in text and text.startswith("LSJ2") for text in problems.setting_defects)
