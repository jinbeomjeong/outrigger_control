"""v5 criteria revision 9 (``v5_criteria_rev9.md`` 3): the five-row J-P3 table per run, the
22-row expectation of the 7.2 hash check (3.3), and the replay tools' coverage of every VB / LS
run (``runs_expected`` / ``runs_judged``, own rule missing = setting defect)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    J_P3_DEFECT_NO_RECORD,
    J_P3_DEFECT_RECORD_WITHOUT_READING,
    J_P3_DEFECT_UNDECLARED,
    J_P3_JUDGED,
    J_P3_NO_ROD_READING,
    j_p3_judgement,
    j_p3_run_case,
)

CLEAN = {"breach_reads": [0, 0, 0, 0], "margin_used_reads": [0, 1, 0, 0],
         "locked_breach_over_tol_reads": [0, 0, 0, 0]}
BREACH = {**CLEAN, "breach_reads": [0, 2, 0, 0]}


# ---------------------------------------------------------------------- 3.2 table, per run
@pytest.mark.parametrize(("record", "has_rod", "declared", "expected"), [
    (CLEAN, True, False, J_P3_JUDGED),                         # 1
    (CLEAN, True, True, J_P3_JUDGED),                          # 1 (declaration irrelevant)
    (None, True, False, J_P3_DEFECT_NO_RECORD),                # 2
    (None, False, True, J_P3_NO_ROD_READING),                  # 3
    (None, False, False, J_P3_DEFECT_UNDECLARED),              # 4
    (CLEAN, False, False, J_P3_DEFECT_UNDECLARED),             # 4 (whatever the record)
    (CLEAN, False, True, J_P3_DEFECT_RECORD_WITHOUT_READING),  # 5
])
def test_run_case_table(record, has_rod, declared, expected) -> None:
    assert j_p3_run_case(record, has_rod, declared) == expected


@pytest.mark.parametrize(("records", "rods", "declared", "status"), [
    ([CLEAN, CLEAN], [True, True], [False, False], "pass"),
    ([CLEAN, BREACH], [True, True], [False, False], "H-7"),
    ([CLEAN, None], [True, True], [False, False], "setting_defect"),     # #2
    ([CLEAN, None], [True, False], [False, True], "pass"),               # #3 counted
    ([CLEAN, None], [True, False], [False, False], "setting_defect"),    # #4
    ([CLEAN, CLEAN], [True, False], [False, True], "setting_defect"),    # #5
    ([BREACH, None], [True, False], [False, False], "setting_defect"),   # defect before H-7
])
def test_judgement_statuses(records, rods, declared, status) -> None:
    assert j_p3_judgement(records, rods, declared)["status"] == status


def test_judgement_counts_the_table_rows() -> None:
    result = j_p3_judgement([CLEAN, None, None], [True, False, False], [False, True, True])
    assert result["status"] == "pass"
    assert result["runs"] == 3 and result["runs_judged"] == 1
    assert result["no_rod_reading_runs"] == 2 and result["margin_used_reads_flag"] == 1
    assert result["runs_by_case"][J_P3_NO_ROD_READING] == 2


# ----------------------------------------------------------------------- replay coverage
def test_replay_rows_cover_every_vb_and_ls_run() -> None:
    import j_p3_inputs

    assert j_p3_inputs.is_p3_expected("final_C4G2_P3", None)
    assert j_p3_inputs.is_p3_expected(None, "LS3") and j_p3_inputs.is_p3_expected(None, "VB")
    assert not j_p3_inputs.is_p3_expected(None, "V0")
    rows = [{"p3_expected": True, "run_extend_start_rule": "tracked_bound",
             "extend_bound_check": CLEAN, "has_rod_reading": True},
            {"p3_expected": False, "run_extend_start_rule": None}]
    result = j_p3_inputs.j_p3_over_rows(rows)
    assert result["status"] == "pass"
    assert result["runs_expected"] == 1 and result["runs_judged"] == 1
    missing_rule = rows + [{"p3_expected": True, "extend_bound_check": CLEAN}]
    result = j_p3_inputs.j_p3_over_rows(missing_rule)
    assert result["status"] == "setting_defect"
    assert result["runs_expected"] == 2 and result["rule_missing_runs"] == 1


def test_chrono_rows_count_as_two_pressure() -> None:
    """Chrono rows carry no declaration and no rod flag: a null record is a defect (3.2 #4)."""
    import j_p3_inputs

    rows = [{"p3_expected": True, "run_extend_start_rule": "tracked_bound",
             "extend_bound_check": None}]
    assert j_p3_inputs.j_p3_over_rows(rows)["status"] == "setting_defect"


def test_harness_declaration_from_meta_or_the_case_path() -> None:
    import j_p3_inputs

    assert j_p3_inputs.harness_head_only_declared({"head_only_declared": False,
                                                   "job": {"case": "R1"}}) is False
    assert j_p3_inputs.harness_head_only_declared({"job": {"case": "R1"}}) is True
    assert j_p3_inputs.harness_head_only_declared({"job": {"case": "R12"}}) is False
    assert j_p3_inputs.harness_head_only_declared({"job": {"key": "x"}}) is False


# ---------------------------------------------------------------- 3.3, p3_hash_check rows
def _pair(case: str, record, has_rod: bool, tmp_path: Path):
    import json

    import numpy as np
    import p3_hash_check

    rod = np.full((3, 4), 1e5 if has_rod else np.nan)
    meta = {"two_pressure_settings": {"extend_start_rule": "tracked_bound",
                                      "extend_start_bound": {"revision": 4}}}
    np.savez(tmp_path / "r.npz", rod_pressure_Pa=rod, meta_json=np.array(json.dumps(meta)))
    job = {"case": case, "eps": 0.0, "setting": "VB"}
    stored = {"job": job, "commands_sha256": "a" * 64, "hydraulics_record": {}}
    rerun = {"job": job, "commands_sha256": "a" * 64, "controller_tag": "final_C4G2_P3",
             "hydraulics_record": {"extend_bound_check": record}, "t4h_file": "r.npz"}
    return p3_hash_check.check_pair(stored, rerun, tmp_path)


def test_hash_check_rows_of_revision_9(tmp_path: Path) -> None:
    steady = _pair("R1", None, False, tmp_path)
    assert steady["pass"] and steady["j_p3"] == "no_rod_reading"
    assert steady["head_only_declared"] is True
    event = _pair("R12", CLEAN, True, tmp_path)
    assert event["pass"] and event["j_p3"] == "pass"
    # an event row without its record, a steady row with a rod reading: defects
    assert not _pair("R12", None, True, tmp_path)["checks"]["6_rev9_row_case"]
    wrong = _pair("R1", CLEAN, True, tmp_path)
    assert not wrong["checks"]["6_rev9_row_case"] and not wrong["pass"]
