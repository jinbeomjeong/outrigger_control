"""436.9 addendum 4a-4 erratum 1 (``jp3_remedy_spec_addendum_4a4_erratum1.md``) and the user's
R-2 decision: the r79 dry key file (``select --keys-file`` reuse of the repository copy, the
``summarize`` check of the r79 output meta ``keys_file``) and ``base-judge-compare`` (new H-6
judge grades against the 436.8 path 1 judge, a record).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a3 import (  # noqa: E402
    DRY_KEYS_FILE_SHA256,
    SELECTION,
    _summary_files,
)

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
ANALYSIS = DATA_ROOT / "06_analysis"
REPO_KEYS_FILE = (ANALYSIS / "02_control" / "j_p3_cause" / "j4a_remedy_b06e409e"
                  / "dryrun_selection_r79_key.txt")
PATH1_FOLDER = (ANALYSIS / "02_control" / "verif_matrix" / "v5_resume_4368" / "judge_932f1fb"
                / "harness_path1")
H6_PATH = ANALYSIS / "03_hydraulic" / "coupled" / "v5" / "resume_k1" / "h6_dg3_v4on.json"
DRY_KEY = "L2|s25|g6|0|g6|G1+J1@FL|top|Fs0"


def test_fixed_values_of_the_erratum_and_r2() -> None:
    assert fixed.DRY_KEYS_FILE_SHA256 == DRY_KEYS_FILE_SHA256
    assert fixed.STORED_H6_R79_JUDGE_SHA256 == (
        "d95627ac83a0bfc165df763e898956fbdcbf7c299fb2d9face8915ef478ed57b")
    assert fixed.STORED_H6_L1_REFERENCE_SHA256 == (
        "a591c3a8c5b3ad5822877e7f69ce2acf75e4cc96fff139a52fef7b6439d56ce7")


# --- R-1: the key file ------------------------------------------------------------------------

def test_r1_key_file_is_written_once_and_reused(tmp_path) -> None:
    path = tmp_path / "key.txt"
    written = dryrun.place_keys_file(path, DRY_KEY)
    assert written["sha256"] == DRY_KEYS_FILE_SHA256 and written["reused_existing_file"] is False
    reused = dryrun.place_keys_file(path, DRY_KEY)
    assert reused["reused_existing_file"] is True and reused["sha256"] == DRY_KEYS_FILE_SHA256


def test_r1_other_key_file_content_stops(tmp_path) -> None:
    path = tmp_path / "key.txt"
    path.write_text("L2|s26|g6|0|g6|G1+J1@FL|top|Fs0\n", encoding="utf-8")
    with pytest.raises(dryrun.Stop, match="another key"):
        dryrun.place_keys_file(path, DRY_KEY)
    with pytest.raises(dryrun.Stop, match="fixed"):
        dryrun.place_keys_file(tmp_path / "other.txt", "L2|s26|g6|0|g6|G1+J1@FL|top|Fs0")


@pytest.mark.skipif(not REPO_KEYS_FILE.is_file(), reason="repository key file copy not present")
def test_r1_repository_copy_is_the_fixed_key_file() -> None:
    record = dryrun.place_keys_file(REPO_KEYS_FILE, DRY_KEY)
    assert record["reused_existing_file"] is True


@pytest.mark.parametrize("meta", [
    {},
    {"keys_file": {"n_keys": 2, "sha256": DRY_KEYS_FILE_SHA256}},
    {"keys_file": {"n_keys": 1, "sha256": "0" * 64}},
])
def test_r1_summary_needs_the_keys_file_of_the_selection(tmp_path, meta) -> None:
    events, r79 = _summary_files(tmp_path, r79_meta=meta)
    summary, code = dryrun.summarize(SELECTION, events, r79)
    assert code == dryrun.EXIT_NOT_JUDGEABLE
    assert all(row.get("stop") == dryrun.ASK_AGAIN and row["keys_file_problems"]
               for row in summary["rows"] if row["run"].startswith("r79"))


def test_r1_selection_of_another_key_file_sha_stops(tmp_path) -> None:
    events, r79 = _summary_files(tmp_path)
    selection = {**SELECTION, "r79_keys_file": {"sha256": "0" * 64}}
    assert dryrun.summarize(selection, events, r79)[1] == dryrun.EXIT_NOT_JUDGEABLE


# --- R-2: base-judge-compare --------------------------------------------------------------------

def _grades(grade: str = "pass", keys: int = 135) -> dict:
    return {f"L3|s0|h|{k}|x": {"grade": grade, "failed_gates": [], "flags": [], "level": "L3"}
            for k in range(keys)}


def test_r2_grade_differences() -> None:
    problems = compare.Problems()
    same = tjr._grade_differences(_grades(), _grades(), problems, "x")
    assert same["differing"] == 0 and problems.status() == compare.STATUS_PASS
    other = _grades()
    other["L3|s0|h|4|x"] = {"grade": "fail", "failed_gates": ["S-6"], "flags": []}
    record = tjr._grade_differences(_grades(), other, problems, "x")
    assert record["differing"] == 1 and record["rows"][0]["stored_grade"] == "fail"
    assert problems.status() == compare.STATUS_FAILED
    problems = compare.Problems()
    tjr._grade_differences(_grades(keys=134), _grades(), problems, "x")
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


def test_r2_inputs_of_another_sha_are_not_judgeable(tmp_path) -> None:
    for name in ("h6.json", "new.json", "stored.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    inputs = tjr.JudgeCompareInputs(tmp_path / "h6.json", tmp_path / "new.json", "0" * 64,
                                    tmp_path / "stored.json")
    _, problems, _ = tjr.compare_base_judges(inputs)
    assert len(problems.not_judgeable) == 3


@pytest.mark.skipif(not (PATH1_FOLDER / "h6_r79_judge.json").is_file() or not H6_PATH.is_file(),
                    reason="stored 436.8 path 1 judge / H-6 not present")
def test_r2_stored_judge_against_itself_and_the_h6_judge_line_grades() -> None:
    """Tool check on stored data only: the stored judge as the "new" one gives 0 differing
    keys, and its grades equal the stored ``h6_judge.json`` line grades (135 keys)."""
    stored = PATH1_FOLDER / "h6_r79_judge.json"
    inputs = tjr.JudgeCompareInputs(H6_PATH, stored, fixed.file_sha256(stored), stored,
                                    PATH1_FOLDER / "h6_judge.json")
    report, problems, _ = tjr.compare_base_judges(inputs)
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    assert report["stored_judge"]["differing"] == 0
    assert report["stored_h6_judge"]["keys"] == 135
    assert report["stored_h6_judge"]["differing"] == 0
