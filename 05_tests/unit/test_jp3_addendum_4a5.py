"""436.9 J-P3 addendum 4a-5 (``jp3_remedy_spec_addendum_4a5.md``) table 8, the remaining items:

* E-1 / E-1b / E-1c: ``records`` judges T-JR-13 (error row fails, the ③ revision 5 record, the
  report's input folder by the fixed T4h name lists), T-JR-14 (135 lines of VBH and VBJ, a
  ``LockWindowMismatchError`` line or ``n_late_fallback`` >= 1 fails) and T-JR-15 (seed net
  force and ``relock_step_over_1bar_count`` on the VBJ / LSJ rows; VBH rows are records).
* E-2: a T-JR-10 / T-JR-11 hash that is not 64 characters is not judgeable.
* E-4: ``judged_key_missing`` and its priority.
* E-5: the VBJ bundle needs ``--base-judge-sha256``.
* E-7: every judge tool prints the 0 / 1 / 2 / 3 table in ``--help`` and exits 3 on a tool
  error.
(E-3 base sha != new sha and E-6 identity: ``test_jp3_prelaunch_audit.py`` and the verif tool
``baseline_check.py`` tests.)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import j_p3_inputs  # noqa: E402
import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import (  # noqa: E402
    REPLAY_REPORTS,
    T4H_NAMES,
    _dg3_document,
    _lock_row,
    h6_keys,
    records_inputs,
    valid_lock_rows,
)
from test_jp3_addendum_4a3 import _t8_inputs  # noqa: E402

from outrigger_sim.control import extend_start_bound as esb  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
PRELAUNCH = DATA_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9"
T4H_SUMS = [PRELAUNCH / "h10_reuse_rerun_t4h.SHA256SUMS", PRELAUNCH / "h6_dg3_v4on_t4h.SHA256SUMS"]
H6_PATH = DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "resume_k1" / (
    "h6_dg3_v4on.json")
GOOD_ROW = [[1.0, 2, 0.0, False]]


def _status(inputs: tjr.RecordsInputs) -> str:
    return tjr.judge_records(inputs)[1].status()


def test_valid_records_inputs_pass() -> None:
    report, problems = tjr.judge_records(records_inputs())
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    assert report["T-JR-14"]["VBH"]["lines"] == report["T-JR-14"]["VBJ"]["lines"] == 135
    assert report["T-JR-15"]["judged_rows"] == 140  # 135 Dg-3 VBJ + 5 case E


@pytest.mark.parametrize("empty", ["replays", "dg3_files", "lock_rows", "h6_keys"])
def test_empty_records_input_is_not_judgeable(empty) -> None:
    inputs = records_inputs()
    values = {name: getattr(inputs, name)
              for name in ("replays", "dg3_files", "lock_rows", "h6_keys")}
    values[empty] = frozenset() if empty == "h6_keys" else []
    assert _status(tjr.RecordsInputs(**values, t4h_names=T4H_NAMES)) == (
        compare.STATUS_NOT_JUDGEABLE)


# --- E-1: T-JR-13 -----------------------------------------------------------------------------

def _replays(change) -> list[dict]:
    reports = json.loads(json.dumps(REPLAY_REPORTS))
    change(reports)
    return reports


def test_e1_replay_error_row_fails() -> None:
    reports = _replays(lambda r: r[1]["rows"][0].update(error="ValueError: x"))
    assert _status(records_inputs(replays=reports)) == (
        compare.STATUS_FAILED)


@pytest.mark.parametrize("change", [
    lambda r: r[0].update(extend_start_revision=4),
    lambda r: r[0].pop("extend_start_revision"),
    lambda r: r[0].update(judged=False),
    lambda r: r[0].update(stop="ideal_record"),
    lambda r: r.pop(1),
    lambda r: r.append(json.loads(json.dumps(r[1]))),
    lambda r: r[1].update(runs=134),
    lambda r: r[1]["rows"].__setitem__(0, {"file": "other.npz"}),
    lambda r: r.__setitem__(1, {**r[0]}),
], ids=["revision_4", "revision_missing", "test_only", "stop", "one_report", "three_reports",
        "rows_not_runs", "other_file", "two_426"])
def test_e1_replay_reports_not_judgeable(change) -> None:
    reports = _replays(change)
    assert _status(records_inputs(replays=reports)) == (
        compare.STATUS_NOT_JUDGEABLE)


@pytest.mark.skipif(not all(path.is_file() for path in T4H_SUMS),
                    reason="prelaunch_j9 T4h lists not present (run with OUTRIGGER_RECORDS_ROOT)")
def test_e1_fixed_t4h_lists() -> None:
    names, problems = tjr.t4h_names_of(T4H_SUMS)
    assert problems == []
    assert sorted(names) == sorted(tjr.REPLAY_RUN_COUNTS)
    assert all(name.endswith(".npz") for listed in names.values() for name in listed)


def test_e1_t4h_lists_of_another_sha_are_refused(tmp_path) -> None:
    path = tmp_path / "h10_reuse_rerun_t4h.SHA256SUMS"
    path.write_text(f"{'0' * 64} *a.npz\n", encoding="utf-8")
    other = tmp_path / "other.SHA256SUMS"
    other.write_text("", encoding="utf-8")
    names, problems = tjr.t4h_names_of([path, other])
    assert names == {} and len(problems) == 3  # sha, unknown list, both counts missing
    assert fixed.H10_T4H_SUMS_SHA256.startswith("3d0ed49a")
    assert fixed.H6_T4H_SUMS_SHA256.startswith("c426f518")


# --- E-1b: T-JR-14 ----------------------------------------------------------------------------

def _dg3(change) -> list[dict]:
    files = [_dg3_document(setting="VBH"), _dg3_document(setting="VBJ")]
    change(files)
    return files


def _alignment(files, index, **values):
    files[1]["results"][index]["lock_window_alignment"].update(values)


def test_e1b_late_fallback_fails() -> None:
    files = _dg3(lambda f: _alignment(f, 3, n_late_fallback=1))
    report, problems = tjr.judge_records(records_inputs(dg3=files))
    assert problems.status() == compare.STATUS_FAILED
    assert report["T-JR-14"]["VBJ"]["late_lines"] == 1


def test_e1b_lock_window_mismatch_error_line_fails() -> None:
    error = "LockWindowMismatchError: stretch_mismatch [('FL', 1.0)], window max |diff| 0.1 s"
    files = _dg3(lambda f: f[0]["results"][5].update(error=error))
    report, problems = tjr.judge_records(records_inputs(dg3=files))
    assert problems.status() == compare.STATUS_FAILED
    assert report["T-JR-14"]["VBH"]["mismatch_error_lines"] == 1


@pytest.mark.parametrize("change", [
    lambda f: f[0]["results"][5].update(error="ValueError: x"),       # another error line
    lambda f: f[1]["results"][2].update(lock_window_alignment={"n_late": None,
                                                                "reason": "no rod reading"}),
    lambda f: f[1]["results"][2].pop("lock_window_alignment"),
    lambda f: _alignment(f, 2, n_late_fallback=None),
    lambda f: _alignment(f, 2, n_late_fallback=True),
    lambda f: f[1]["results"].pop(),                                  # 134 lines
    lambda f: f.append(_dg3_document(setting="VBJ0", count=1)),       # another setting
    lambda f: f.pop(0),                                               # no VBH
    lambda f: f[1]["results"][4].update(key="cand=current#L3|s9|h|999|inner"),  # other key
    lambda f: f[0]["results"].__setitem__(                            # a key twice
        6, {**f[0]["results"][6], "key": f[0]["results"][5]["key"]}),
], ids=["other_error", "reason", "no_record", "none", "bool", "134_lines", "other_setting",
        "one_bundle", "other_key", "key_twice"])
def test_e1b_not_judgeable(change) -> None:
    assert _status(records_inputs(dg3=_dg3(change))) == (
        compare.STATUS_NOT_JUDGEABLE)


# --- E-1c: T-JR-15 ----------------------------------------------------------------------------

def _rows(change) -> list[dict]:
    """The valid T-JR-15 set (rows 0 .. 4 = case E VBJ, LSJ1 .. LSJ4; 5 .. = Dg-3 VBJ lines)
    after ``change``."""
    rows = valid_lock_rows()
    change(rows)
    return rows


def _record(rows, index, **values):
    rows[index]["hydraulics_record"].update(values)


@pytest.mark.parametrize(("change", "status"), [
    (lambda rows: _record(rows, 0, relock_step_over_1bar_count=1), compare.STATUS_FAILED),
    (lambda rows: _record(rows, 2, relock_step_over_1bar_count=2), compare.STATUS_FAILED),
    (lambda rows: _record(rows, 40, relock_step_over_1bar_count=1), compare.STATUS_FAILED),
    (lambda rows: rows[3]["hydraulics_record"].pop("relock_step_over_1bar_count"),
     compare.STATUS_NOT_JUDGEABLE),
    (lambda rows: rows.__setitem__(0, _lock_row([[1.0, 2, 1.5, False]])),
     compare.STATUS_FAILED),                                                  # seed > 1 N
    (lambda rows: rows.append(_lock_row(GOOD_ROW, setting="VBH", relocks=5)),
     compare.STATUS_PASS),                                                    # VBH: record
    (lambda rows: rows.append(_lock_row([[1.0, 2, 9.0, True]], setting="VBH", relocks=None)),
     compare.STATUS_PASS),                                                    # VBH: record
], ids=["relock_vbj", "relock_lsj", "relock_dg3_vbj", "relock_missing", "seed_over",
        "vbh_relock_record", "vbh_seed_record"])
def test_e1c_relock_and_seed(change, status) -> None:
    assert _status(records_inputs(_rows(change))) == status


@pytest.mark.parametrize("change", [
    lambda rows: rows.pop(2),                                        # a case E row missing
    lambda rows: rows.pop(),                                         # a Dg-3 VBJ line missing
    lambda rows: rows.append(json.loads(json.dumps(rows[1]))),       # a case E row twice
    lambda rows: rows.append(json.loads(json.dumps(rows[7]))),       # a Dg-3 line twice
    lambda rows: rows[9].update(key="cand=current#L3|s9|h|999|inner"),   # another key
    lambda rows: rows[0]["job"].update(offset_s=0.075),              # a case F row
    lambda rows: rows.append(_dg3_document(setting="LSJ1", count=1)["results"][0]),
    lambda rows: rows.clear() or rows.append(_lock_row(GOOD_ROW, setting="VBH")),
], ids=["case_e_missing", "dg3_missing", "case_e_twice", "dg3_twice", "dg3_other_key",
        "case_f_row", "dg3_other_setting", "vbh_only"])
def test_e1c_judged_set_is_fixed(change) -> None:
    """4a-5 erratum 1: the Dg-3 VBJ 135 lines of the stored H-6 keys + the five case E rows;
    missing, repeated or other rows are not judgeable."""
    assert _status(records_inputs(_rows(change))) == compare.STATUS_NOT_JUDGEABLE


def test_e1c_lock_rows_read_dg3_json_and_jsonl(tmp_path) -> None:
    document = _dg3_document(setting="VBJ", count=2)
    (tmp_path / "dg3_VBJ.json").write_text(json.dumps(document), encoding="utf-8")
    (tmp_path / "rows.jsonl").write_text(json.dumps(_lock_row(GOOD_ROW)) + "\n",
                                         encoding="utf-8")
    lines = tjr.read_lock_rows(tmp_path / "dg3_VBJ.json")
    record = tjr._lock_record(lines[0])
    assert len(lines) == 2 and record["setting"] == "VBJ" and record["source"] == "dg3"
    assert record["key"] == "L2|s0|h|0|inner"  # the cand=...# prefix removed
    assert len(tjr.read_lock_rows(tmp_path / "rows.jsonl")) == 1


def test_e1_records_command_exit_codes(tmp_path, monkeypatch) -> None:
    """Through ``main``: pass 0, a T-JR-13 error row 1, a revision 4 report 2 (4a-5 8 E-1)."""
    def run(name, replays) -> int:
        folder = tmp_path / name
        folder.mkdir()
        paths = []
        for index, document in enumerate(replays):
            paths.append(folder / f"replay_{index}.json")
            paths[-1].write_text(json.dumps(document), encoding="utf-8")
        for setting in tjr.T_JR_14_BUNDLES:
            (folder / f"dg3_{setting}.json").write_text(
                json.dumps(_dg3_document(setting=setting)), encoding="utf-8")
        rows = valid_lock_rows()
        (folder / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows),
                                           encoding="utf-8")
        return tjr.main(["records", "--out", str(folder / "out.json"), "--replay",
                         *map(str, paths), "--dg3", str(folder / "dg3_VBH.json"),
                         str(folder / "dg3_VBJ.json"), "--lock-rows",
                         str(folder / "rows.jsonl"), "--t4h-sums", "unused", "--h6", "unused"])

    monkeypatch.setattr(tjr, "t4h_names_of", lambda paths: (T4H_NAMES, []))
    monkeypatch.setattr(tjr, "h6_keys_of", lambda path: (h6_keys(), []))
    assert run("pass", REPLAY_REPORTS) == 0
    assert run("error_row", _replays(lambda r: r[0]["rows"][0].update(error="x"))) == 1
    assert run("revision_4", _replays(lambda r: r[0].update(extend_start_revision=4))) == 2


@pytest.mark.skipif(not H6_PATH.is_file(), reason="stored H-6 not present")
def test_erratum1_h6_keys_of_the_stored_h6(tmp_path) -> None:
    keys, problems = tjr.h6_keys_of(H6_PATH)
    assert problems == [] and len(keys) == 135
    assert not any("#" in key for key in keys)
    other = tmp_path / "h6.json"
    other.write_text('{"results": []}', encoding="utf-8")
    assert tjr.h6_keys_of(other)[1] and tjr.h6_keys_of(None)[1]


# --- E-2: t8 hashes ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "a" * 10, 7])
@pytest.mark.parametrize(("test", "settings"), [("T-JR-11", ("VBJ", "VBJ0")),
                                                ("T-JR-11", ("VBJ",)),
                                                ("T-JR-10", ("VBH",))])
def test_e2_hash_not_64_characters_is_not_judgeable(value, test, settings) -> None:
    def broken(inputs, key):
        for setting in settings:
            inputs.rerun[setting][key]["commands_sha256"] = value

    problems = compare.Problems()
    report = tjr.judge_t8(_t8_inputs(broken), problems)
    assert report[test]["status"] == compare.STATUS_NOT_JUDGEABLE
    assert problems.failures == []


def test_e2_stored_hash_not_64_characters_is_not_judgeable() -> None:
    def broken(inputs, key):
        inputs.stored["VB"][key]["commands_sha256"] = "a" * 63

    problems = compare.Problems()
    report = tjr.judge_t8(_t8_inputs(broken), problems)
    assert report["T-JR-10"]["status"] == compare.STATUS_NOT_JUDGEABLE


def test_e2_64_character_hashes_that_differ_still_fail() -> None:
    def differ(inputs, key):
        inputs.rerun["VBJ"][key]["commands_sha256"] = "f" * 64

    problems = compare.Problems()
    assert tjr.judge_t8(_t8_inputs(differ), problems)["T-JR-11"]["status"] == (
        compare.STATUS_FAILED)


# --- E-4: judged_key_missing ------------------------------------------------------------------

ROW = {"rule_revision": 5, "jp3a_breach_reads": [0] * 4, "jp3b_breach_over_tol_reads": [0] * 4,
       "jp3c_breach_reads": [0] * 4, "sensor_grade": "normal", "spec_edition": "8be9de22",
       "carry_end_rule": "inherit_when_gate_shut", "retract_start_rule": "with_tracker"}
MISSING = {key: value for key, value in ROW.items() if key != "jp3b_breach_over_tol_reads"}
BREACH = {**ROW, "jp3a_breach_reads": [1, 0, 0, 0]}
DEFECT = {**ROW, "retract_start_rule": "model_only"}
CONSERVATIVE = {**ROW, "sensor_grade": "conservative"}


@pytest.mark.parametrize(("rows", "expected_runs", "status"), [
    ([MISSING], None, "judged_key_missing"),
    ([CONSERVATIVE], None, "no_judged_runs"),
    ([MISSING, DEFECT], None, "setting_defect"),             # defect first
    ([MISSING, BREACH], None, "judged_key_missing"),         # over H-7
    ([MISSING, ROW], 1, "judged_key_missing"),               # over no_judged_runs (count)
    ([ROW, ROW], 1, "no_judged_runs"),
    ([BREACH], None, "H-7"),
    ([ROW], None, "pass"),
])
def test_e4_status_priority(rows, expected_runs, status) -> None:
    result = esb.j_p3_judgement_rev5(rows, expected_judged_runs=expected_runs)
    assert result["status"] == status
    assert result["judged_key_missing_runs"] == sum(row is MISSING for row in rows)


def test_e4_status_order_of_the_two_revision_judgement() -> None:
    assert j_p3_inputs._worse_status("no_judged_runs", "judged_key_missing") == (
        "judged_key_missing")
    assert j_p3_inputs._worse_status("judged_key_missing", "setting_defect") == "setting_defect"
    assert j_p3_inputs._worse_status("H-7", "judged_key_missing") == "judged_key_missing"


def test_e4_t12_vbj_j_p3_judged_key_missing_is_not_judgeable() -> None:
    lines = [{"hydraulics_record": {"extend_bound_check": MISSING}}]
    problems = compare.Problems()
    record = tjr._dg3_j_p3(lines, problems)
    assert record["status"] == "judged_key_missing"
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


def test_e4_p4_3a_message_names_judged_key_missing() -> None:
    problems = compare.Problems()
    compare.judged_key_problems("VBJ", {}, {"relock_step_over_1bar_count": 0}, problems)
    assert all("judged_key_missing" in text for text in problems.not_judgeable)
    assert len(problems.not_judgeable) == 3


# --- E-5 --------------------------------------------------------------------------------------

def test_e5_vbj_bundle_needs_the_base_judge_sha(tmp_path) -> None:
    judge = tmp_path / "judge.json"
    judge.write_text("{}", encoding="utf-8")
    problems = tjr.t12_input_problems("VBJ", tmp_path / "base.json", judge, None)
    assert problems == ["--base-judge-sha256 missing (required, prelaunch audit M-8)"]


# --- E-7: exit codes ------------------------------------------------------------------------

HELP_COMMANDS = [
    (tjr.main, []), *[(tjr.main, [name]) for name in (
        "t8", "t12", "dg3-judge", "base-judge", "base-judge-compare", "t12-selfcheck",
        "records")],
    (compare.main, []), (case_judge.main, []), (case_judge.main, ["x11"]),
    (case_judge.main, ["case-f"]), (case_judge.main, ["case-f-path"]),
    (dryrun.main, []), (dryrun.main, ["summarize"]),
]


@pytest.mark.parametrize(("main", "argv"), HELP_COMMANDS)
def test_e7_help_prints_the_exit_table(main, argv, capsys) -> None:
    with pytest.raises(SystemExit) as stop:
        main([*argv, "--help"])
    assert stop.value.code == 0
    text = capsys.readouterr().out
    assert "exit codes (addendum 4a-5 5.1" in text
    for code in ("0", "1", "2", "3"):
        assert f"\n  {code}  " in text


def _broken(tmp_path) -> Path:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    return path


def test_e7_tool_errors_exit_3(tmp_path, monkeypatch) -> None:
    """Exit 3 = a tool error (4a-5 5.1): broken JSON, a missing file, an input of another
    shape; the report holds ``error``."""
    broken = _broken(tmp_path)
    shaped = tmp_path / "list.json"
    shaped.write_text("[1, 2]", encoding="utf-8")
    monkeypatch.setattr(compare, "Baseline", lambda path: object())  # reach the new rows
    cases = [
        (tjr.main, ["records", "--replay", str(broken)]),
        (tjr.main, ["records", "--replay", str(shaped)]),          # another shape
        (tjr.main, ["t12", "--bundle", "VBH", "--base", str(broken), "--base-judge",
                    str(broken), "--new", str(broken), "--new-judge", str(broken)]),
        (case_judge.main, ["case-f", "--rows", str(broken), "--grid",
                           str(tmp_path / "missing_grid.json")]),
        (compare.main, [str(tmp_path / "baseline"), "--new", str(broken)]),
        (dryrun.main, ["summarize", "--selection", str(broken)]),
    ]
    for index, (main, argv) in enumerate(cases):
        out = tmp_path / f"out_{index}.json"
        assert main([*argv, "--out", str(out)]) == compare.EXIT_ERROR == 3, index
        report = json.loads(out.read_text(encoding="utf-8"))
        assert "error" in report, (index, report)
