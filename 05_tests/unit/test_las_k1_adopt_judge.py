"""Unit tests of ``las_k1_adopt_judge.py`` on synthetic result.json documents (no Chrono, no git).

Fixtures follow ``las_k1_rules_adopt.md`` 10.1 items 1-10; no stored 07_results file is read.

Run (dynamics-dev, PowerShell, project root):
  $env:PYTHONDONTWRITEBYTECODE = '1'
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -m pytest -q -p no:cacheprovider
      05_tests/unit/test_las_k1_adopt_judge.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JUDGE_PATH = PROJECT_ROOT / "06_analysis/02_control/verif_matrix/scripts/las_k1_adopt_judge.py"
RULES_PATH = PROJECT_ROOT / "06_analysis/02_control/verif_matrix/las_k1_rules_adopt.md"
_SPEC = importlib.util.spec_from_file_location("las_k1_adopt_judge", JUDGE_PATH)
judge = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = judge  # dataclasses look the module up while the class is built
_SPEC.loader.exec_module(judge)

ROW_PATH = "S9/batch_TEST/row/result.json"
APPLIED_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN:80"
SKIP_ORDER_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"


# ---------------------------------------------------------------- synthetic rows
def make_row(
    events: list[tuple[float, str]],
    *,
    t_P_s: float | None,
    t_loc_s: float | None,
    soil_mode_t_s: float | None,
    soil: str = "J1",
    soil_patch: str | None = None,
    order_gate: dict[str, Any] | None = None,
    mode_starts: list[float] | None = None,
) -> dict[str, Any]:
    """A run_S9 ``level`` result.json reduced to the keys the judge reads."""
    soil_meta: dict[str, Any] = {
        "settings": {"enable": True},
        "t_P_s": t_P_s,
        "t_loc_s": t_loc_s,
        "soil_mode_t_s": soil_mode_t_s,
        "restored_from": None,
    }
    if mode_starts is not None:
        soil_meta["mode_starts"] = [{"t_s": t_s, "source": "release"} for t_s in mode_starts]
    margin: dict[str, Any] = {"settings": {"flat_soil_margin_m": 0.03}}
    if order_gate is not None:
        margin["order_gate"] = order_gate
    return {
        "action": "level",
        "args": {
            "case": "row",
            "soil": soil,
            "soil_patch": soil_patch,
            "level": "top",
            "floor_roll": 0.0,
            "floor_pitch": 0.0,
            "mass_scale": 1.0,
            "fs_kN": 4.0,
            "expect_controller": "final_C4G2",
        },
        "controller_meta": {
            "period_s": 0.1,
            "soil": soil_meta,
            "slope_clearance_margin": margin,
        },
        "c2_soil": copy.deepcopy(soil_meta),
        "events": [{"t_s": t_s, "name": name} for t_s, name in events],
        "code_state": {"git_at_start": {"head": "a" * 40}},
    }


def old_row_one_loc(t_P_s: float = 34.2, t_S_s: float = 30.0) -> dict[str, Any]:
    events = [
        (t_S_s, "soil_mode_start"),
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, APPLIED_EVENT),
    ]
    return make_row(events, t_P_s=t_P_s, t_loc_s=35.4, soil_mode_t_s=t_S_s)


def decision(t_loc_s: float, *, would_block: bool, applied: bool) -> dict[str, Any]:
    return {
        "t_loc_s": t_loc_s,
        "t_P_s": 34.9,
        "t_S_s": 36.9,
        "n_P": 349,
        "n_S": 369,
        "dP": -20,
        "r4_due_without_gate": True,
        "would_block": would_block,
        "applied": applied,
    }


def decisions_row(*, gate_on: bool) -> dict[str, Any]:
    """The S-Ch shape: plateau 34.9 s, soil mode 36.9 s, LOC 37.5 s (dP -20)."""
    r4_event = SKIP_ORDER_EVENT if gate_on else APPLIED_EVENT
    events = [(36.9, "soil_mode_start"), (37.5, "crawler_liftoff_confirmed"), (37.5, r4_event)]
    order_gate = {
        "enabled": gate_on,
        "decisions": [decision(37.5, would_block=True, applied=not gate_on)],
    }
    return make_row(
        events,
        t_P_s=34.9,
        t_loc_s=37.5,
        soil_mode_t_s=36.9,
        soil="G1",
        soil_patch="FL:J2",
        order_gate=order_gate,
        mode_starts=[36.9],
    )


def analyze(document: dict[str, Any], *, is_known: bool = False) -> Any:
    return judge.analyze_row(ROW_PATH, document, is_known)


def failed_checks(analysis: Any) -> list[str]:
    return [check_id for check_id, problems in analysis.problems.items() if problems]


def all_true_checks() -> list[dict[str, Any]]:
    return [{"id": check_id, "ok": True, "problems": []} for check_id in judge.K_IDS]


def loc_record(row_class: str, state: str, dP: int | None, *, row: str = ROW_PATH) -> Any:
    return judge.LocRecord(
        row=row,
        floor="-",
        row_class=row_class,
        kind="applied",
        t_R_s=35.4,
        n_R=354,
        source="b",
        state=state,
        t_P_s=None,
        t_S_s=None,
        n_P=None,
        n_S=None,
        dP=dP,
        loc_revokes=0,
        is_known_row=False,
        case="row",
        tag="-",
        level="top",
        floor_roll=0.0,
        floor_pitch=0.0,
        mass_scale=1.0,
        fs_kN=4.0,
        n_R_minus_n_S=None,
    )


# ---------------------------------------------------------------- 10.1 #1 old row, one LOC
def test_old_row_one_loc_source_b_exact_dP() -> None:
    analysis = analyze(old_row_one_loc())
    assert failed_checks(analysis) == []
    (loc,) = analysis.locs
    assert (loc.source, loc.state, loc.kind) == ("b", "OK", "applied")
    assert (loc.n_R, loc.n_P, loc.n_S, loc.dP) == (354, 342, 300, 42)
    assert analysis.record.row_class == "MUST"


# ---------------------------------------------------------------- 10.1 #2 / #3 revocations
def test_r4_loc_revoked_then_new_loc_is_unrecoverable() -> None:
    events = [
        (30.0, "soil_mode_start"),
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, APPLIED_EVENT),
        (37.0, "INFO_LOC_REVOKED:3.1"),
        (40.0, "crawler_liftoff_confirmed"),
    ]
    document = make_row(events, t_P_s=39.0, t_loc_s=40.0, soil_mode_t_s=30.0)
    analysis = analyze(document)
    (loc,) = analysis.locs
    assert (loc.source, loc.state, loc.t_P_s, loc.dP) == ("c", "UNRECOVERABLE", None, None)
    assert failed_checks(analysis) == []
    judge.mark_revoked_after_r4(document, analysis.record, analysis.locs)
    assert analysis.record.flags == ["REVOKED_AFTER_R4"]
    assert analysis.record.loc_revokes == 1


def test_last_loc_revoked_is_unrecoverable() -> None:
    events = [
        (30.0, "soil_mode_start"),
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, APPLIED_EVENT),
        (37.0, "INFO_LOC_REVOKED:3.1"),
    ]
    analysis = analyze(make_row(events, t_P_s=None, t_loc_s=None, soil_mode_t_s=30.0))
    (loc,) = analysis.locs
    assert (loc.source, loc.state) == ("c", "UNRECOVERABLE")
    assert failed_checks(analysis) == []


# ---------------------------------------------------------------- 10.1 #4 decisions row, K-6
def test_decisions_row_source_a_and_gate_blocked_loc() -> None:
    analysis = analyze(decisions_row(gate_on=True), is_known=True)
    assert failed_checks(analysis) == []
    (loc,) = analysis.locs
    assert (loc.source, loc.state, loc.kind) == ("a", "OK", "gate_blocked")
    assert (loc.n_P, loc.n_S, loc.dP, loc.is_known_row) == (349, 369, -20, True)
    assert analysis.record.row_class == "PATCH"


def test_decisions_row_gate_off_counts_applied_event() -> None:
    (loc,) = analyze(decisions_row(gate_on=False)).locs
    assert (loc.source, loc.kind, loc.dP) == ("a", "applied", -20)


def test_k6_extra_r4_due_decision_period() -> None:
    document = decisions_row(gate_on=True)
    margin = document["controller_meta"]["slope_clearance_margin"]
    margin["order_gate"]["decisions"].append(decision(40.0, would_block=True, applied=False))
    assert failed_checks(analyze(document)) == ["K-6"]


def test_k6_gate_on_applied_with_would_block_true() -> None:
    document = decisions_row(gate_on=True)
    document["events"][-1]["name"] = APPLIED_EVENT
    assert failed_checks(analyze(document)) == ["K-6"]


def test_k6_two_decisions_for_one_loc() -> None:
    document = decisions_row(gate_on=True)
    decisions = document["controller_meta"]["slope_clearance_margin"]["order_gate"]["decisions"]
    decisions.append(copy.deepcopy(decisions[0]))
    analysis = analyze(document)
    assert "K-6" in failed_checks(analysis)
    assert analysis.locs[0].state == "UNRECOVERABLE"


# ---------------------------------------------------------------- 10.1 #5 _SKIPPED prefix trap
def test_skipped_order_in_gate_off_row_is_not_r4_and_breaks_k6() -> None:
    events = [
        (30.0, "soil_mode_start"),
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, SKIP_ORDER_EVENT),
    ]
    analysis = analyze(make_row(events, t_P_s=34.2, t_loc_s=35.4, soil_mode_t_s=30.0))
    assert analysis.locs == []
    assert analysis.record.row_class == "NONE"
    assert failed_checks(analysis) == ["K-6"]


def test_other_skipped_variant_is_not_r4() -> None:
    events = [
        (30.0, "soil_mode_start"),
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:other"),
    ]
    analysis = analyze(make_row(events, t_P_s=34.2, t_loc_s=35.4, soil_mode_t_s=30.0))
    assert analysis.locs == []
    assert failed_checks(analysis) == []


def test_applied_event_with_value_counts() -> None:
    assert judge.event_base_name(APPLIED_EVENT) == "INFO_LOC_FLAT_SOIL_MARGIN"
    assert judge.event_base_name(SKIP_ORDER_EVENT) != "INFO_LOC_FLAT_SOIL_MARGIN"


# ---------------------------------------------------------------- 10.1 #6 same-period soil start
def test_soil_start_in_loc_period_is_excluded() -> None:
    events = [
        (30.0, "soil_mode_start"),
        (35.36, "soil_mode_start"),  # period 354 = the LOC period: after the LOC (K1 0.1)
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, APPLIED_EVENT),
    ]
    analysis = analyze(make_row(events, t_P_s=34.2, t_loc_s=35.4, soil_mode_t_s=35.36))
    assert failed_checks(analysis) == []
    (loc,) = analysis.locs
    assert (loc.n_S, loc.t_S_s, loc.dP) == (300, 30.0, 42)


def test_only_same_period_soil_start_is_k8() -> None:
    events = [
        (35.4, "soil_mode_start"),
        (35.4, "crawler_liftoff_confirmed"),
        (35.4, APPLIED_EVENT),
    ]
    analysis = analyze(make_row(events, t_P_s=34.2, t_loc_s=35.4, soil_mode_t_s=35.4))
    assert failed_checks(analysis) == ["K-8"]


# ---------------------------------------------------------------- 10.1 #7 soil vs c2_soil
def test_c2_soil_copy_differs_is_k7_stop() -> None:
    document = old_row_one_loc()
    document["c2_soil"]["t_P_s"] = 34.3
    analysis = analyze(document)
    assert failed_checks(analysis) == ["K-7"]
    checks = all_true_checks()
    checks[7] = {"id": "K-7", "ok": False, "problems": analysis.problems["K-7"]}
    grade, _, _ = judge.decide_grade(checks, analysis.locs)
    assert grade is judge.Grade.STOP
    assert judge.GRADE_EXIT_CODES[grade] == 2


def test_error_block_and_restored_row_are_k3() -> None:
    error_row = old_row_one_loc()
    error_row["controller_meta"]["soil"] = {"error": "RuntimeError: x"}
    assert failed_checks(analyze(error_row)) == ["K-3"]
    restored_row = old_row_one_loc()
    restored_row["controller_meta"]["soil"]["restored_from"] = "checkpoint.json"
    assert failed_checks(analyze(restored_row)) == ["K-3"]


def test_period_other_than_0p1_is_k4() -> None:
    document = old_row_one_loc()
    document["controller_meta"]["period_s"] = 0.02
    assert failed_checks(analyze(document)) == ["K-4"]


# ---------------------------------------------------------------- 10.1 #8 grades
def test_must_zero_is_undecidable() -> None:
    locs = [loc_record("PATCH", "OK", -20)]
    grade, _, _ = judge.decide_grade(all_true_checks(), locs)
    assert grade is judge.Grade.UNDECIDABLE


def test_must_dP_zero_is_fail() -> None:
    locs = [loc_record("MUST", "OK", 0), loc_record("PATCH", "OK", -20)]
    grade, reasons, _ = judge.decide_grade(all_true_checks(), locs)
    assert grade is judge.Grade.FAIL
    assert reasons


def test_t_P_none_is_blocked_missing_and_must_fail() -> None:
    analysis = analyze(old_row_one_loc(t_P_s=None))
    assert failed_checks(analysis) == []
    (loc,) = analysis.locs
    assert (loc.state, loc.dP) == ("BLOCKED_MISSING", None)
    grade, _, _ = judge.decide_grade(all_true_checks(), analysis.locs)
    assert grade is judge.Grade.FAIL


def test_fail_wins_over_undecidable() -> None:
    locs = [loc_record("MUST", "OK", -1), loc_record("MUST", "UNRECOVERABLE", None)]
    grade, _, _ = judge.decide_grade(all_true_checks(), locs)
    assert grade is judge.Grade.FAIL


def test_pass_partial_and_known_rows_only() -> None:
    known_patch = loc_record("PATCH", "OK", -20)
    known_patch.is_known_row = True
    grade, reasons, conditions = judge.decide_grade(
        all_true_checks(), [loc_record("MUST", "OK", 31), known_patch]
    )
    assert grade is judge.Grade.PASS
    assert conditions["condition_2_known_rows_only"] is True
    assert any("known" in reason for reason in reasons)
    grade, _, _ = judge.decide_grade(
        all_true_checks(), [loc_record("MUST", "OK", 31), loc_record("PATCH", "OK", 3)]
    )
    assert grade is judge.Grade.PARTIAL
    assert judge.GRADE_EXIT_CODES[grade] == 1


# ---------------------------------------------------------------- 10.1 #9 rounding
def test_period_round_half_to_even_on_the_stored_float() -> None:
    assert judge.period_of(34.95) == 350
    assert judge.period_of(34.85) == 348


def test_dP_from_half_period_times() -> None:
    analysis = analyze(old_row_one_loc(t_P_s=34.95, t_S_s=34.85))
    (loc,) = analysis.locs
    assert (loc.n_P, loc.n_S, loc.dP) == (350, 348, 2)


# ---------------------------------------------------------------- 10.1 #10 appendix A parse
def test_appendix_parse_of_the_sealed_rules() -> None:
    sealed = judge.parse_sealed_lists(RULES_PATH.read_text(encoding="utf-8"))
    assert sealed.problems == []
    assert len(sealed.rows_a) == 74
    assert len(sealed.rows_b) == 43
    assert len(sealed.rows_e) == 183
    assert all(judge.is_sha256_hex(row.sha256) for row in sealed.rows_a)
    assert all(row.path.startswith("S9/batch_") for row in sealed.rows_a)
    assert all(row.path.endswith("/result.json") for row in sealed.rows_a)
    assert judge.KNOWN_A_ROWS <= {row.path for row in sealed.rows_a}
    assert judge.KNOWN_B_ROWS <= {row.path for row in sealed.rows_b}


def test_appendix_parse_detects_a_changed_sha() -> None:
    text = RULES_PATH.read_text(encoding="utf-8")
    changed = text.replace("c75f0757703c052a", "c75f0757703c052b", 1)
    assert judge.parse_sealed_lists(changed).problems


# ---------------------------------------------------------------- selection rules (2.2)
@pytest.mark.parametrize(
    ("soil", "patch", "want"),
    [
        ("G1", "FL:J1", "PATCH"),
        ("G1", "FL:G1", "UNIFORM_G1"),
        ("G1", None, "UNIFORM_G1"),
        ("J2", None, "UNIFORM_SOFT"),
        ("J1", "", "UNIFORM_SOFT"),
        ("G1", "FL:J1,RR:G1", "PATCH"),
    ],
)
def test_floor_class(soil: str, patch: str | None, want: str) -> None:
    assert judge.floor_class({"soil": soil, "soil_patch": patch}) == want


def test_selection_steps() -> None:
    row = old_row_one_loc()
    assert judge.selection(row) == ("A", None)
    assert judge.selection(None) == ("E", "load_error")
    assert judge.selection({**row, "action": "machine"}) == ("E", "not_run_S9_level")
    old_margin = copy.deepcopy(row)
    old_margin["controller_meta"]["slope_clearance_margin"]["settings"]["flat_soil_margin_m"] = 0.0
    assert judge.selection(old_margin) == ("B", None)
    soil_off = copy.deepcopy(row)
    soil_off["controller_meta"]["soil"]["settings"]["enable"] = False
    assert judge.selection(soil_off) == ("E", "soil_response_off")
    fields_missing = copy.deepcopy(row)
    del fields_missing["controller_meta"]["soil"]["t_P_s"]
    assert judge.selection(fields_missing) == ("E", "soil_meta_fields_missing")


def test_canonical_list_sha_is_order_free() -> None:
    entries = [("S9/b/x/result.json", "1" * 64), ("S9/a/y/result.json", "2" * 64)]
    assert judge.canonical_list_sha256(entries) == judge.canonical_list_sha256(entries[::-1])


# ---------------------------------------------------------------- command line (synthetic tree)
def write_synthetic_tree(results_root: Path) -> None:
    row_dir = results_root / "S9" / "batch_TEST" / "row"
    row_dir.mkdir(parents=True)
    text = json.dumps(old_row_one_loc())
    (row_dir / "result.json").write_text(text, encoding="utf-8")


def test_list_on_a_synthetic_tree_is_exit_2_without_values(tmp_path: Path) -> None:
    write_synthetic_tree(tmp_path / "07_results")
    out = tmp_path / "list.json"
    code = judge.main(
        [
            "list",
            "--results-root",
            str(tmp_path / "07_results"),
            "--rules",
            str(RULES_PATH),
            "--root",
            str(tmp_path),
            "--out",
            str(out),
        ]
    )
    assert code == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["population"]["count"] == 1
    assert len(report["post_seal_new_files"]) == 1
    assert "t_P_s" not in out.read_text(encoding="utf-8")


def test_judge_on_a_synthetic_tree_is_stop(tmp_path: Path) -> None:
    write_synthetic_tree(tmp_path / "07_results")
    out = tmp_path / "judge.json"
    code = judge.main(
        [
            "judge",
            "--results-root",
            str(tmp_path / "07_results"),
            "--rules",
            str(RULES_PATH),
            "--root",
            str(tmp_path),
            "--out",
            str(out),
            "--no-git",
            "--expect-tool-sha",
            "0" * 64,
        ]
    )
    assert code == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["grade"] == "stop"
    failed = {check["id"] for check in report["k_checks"] if check["ok"] is False}
    assert {"K-0", "K-1", "K-2"} <= failed
    assert report["k_checks"][0]["rules_sha256"] == judge.RULES_SHA256
