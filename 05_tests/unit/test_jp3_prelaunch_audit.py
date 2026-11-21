"""436.9 J-P3 prelaunch audit (``prelaunch_j9/audit_prelaunch.md``, 2026-11-21) items of
python-expert and the user decisions appended to it:

* B-1: the stored H-6 self check passes with no setting defect (real H-6, real r79 grades of
  the 436.8 path 1 judge of the same H-6); the P4 evidence applies to 436.9 lines only.
* M-3: t12 checks the lines' setting and revision, the VBJ base setting and base != new file.
* M-4: t8 applies the 13.6 identity and the B2 evidence to its VBH / VBJ / VBJ0 lines; T-JR-11
  needs 64-character hashes.
* M-5: a missing J-P3 judged key or P4-9 key is not judgeable, never 0.
* M-6: ``records`` with an empty input, a test-only or short replay report is not judgeable;
  a T-JR-15 seed row over 1 N fails.
* M-8: ``dg3-judge`` (the new-side judge file with the P-1a L1 extract), the keys file of the
  new side, the judge sha of both bundles.
* R-7: ``h8_noise_judge_4368.reference_extract`` never overwrites; R-8: the stored
  ``h6_judge.json`` sha; M-1: ``jp3_run_identity.py``.
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

import h8_noise_judge_4368 as h8  # noqa: E402
import jp3_baseline_compare as compare  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_run_identity as run_identity  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import REPLAY_REPORTS, _dg3_document, _seed_record  # noqa: E402
from test_jp3_addendum_4a3 import _t8_inputs  # noqa: E402

from outrigger_sim.control import extend_start_bound as esb  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
ANALYSIS = DATA_ROOT / "06_analysis"
H6_PATH = ANALYSIS / "03_hydraulic" / "coupled" / "v5" / "resume_k1" / "h6_dg3_v4on.json"
PATH1_JUDGE = (ANALYSIS / "02_control" / "verif_matrix" / "v5_resume_4368" / "judge_932f1fb"
               / "harness_path1" / "h6_r79_judge.json")
HAS_STORED = H6_PATH.is_file() and PATH1_JUDGE.is_file()
STORED_REASON = "stored H-6 / 436.8 path 1 judge not present (run with OUTRIGGER_RECORDS_ROOT)"


@pytest.fixture
def pass_grades(monkeypatch):
    """Every line graded pass (the judge rows are not under test)."""
    monkeypatch.setattr(h8, "grade_lines", lambda results, judge: {
        h8.plain_key(run["key"]): {"grade": h8.GRADE_PASS, "level": run["level"]}
        for run in results})


# --- B-1 --------------------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_STORED, reason=STORED_REASON)
def test_b1_stored_h6_self_check_passes_with_the_real_grades() -> None:
    """``t12-selfcheck`` on the real H-6 with a real r79 judge of it (the 436.8 path 1 judge:
    the P-1a file is made by the main session, not here): setting defects 0, status pass and
    the whole 4a-4 6 table (no expectation miss)."""
    assert fixed.file_sha256(H6_PATH) == fixed.H6_SHA256
    assert fixed.file_sha256(PATH1_JUDGE) == fixed.STORED_H6_R79_JUDGE_SHA256
    report, outcome, _ = tjr.t12_selfcheck(H6_PATH, PATH1_JUDGE, fixed.STORED_H6_R79_JUDGE_SHA256)
    assert report["t12_problems"]["setting_defects"] == []
    assert report["t12_problems"]["not_judgeable"] == []
    assert report["t12_problems"]["failures"] == []
    assert report["expectation_misses"] == []
    assert outcome.status() == compare.STATUS_PASS
    assert report["l2_lines"] == 1 and report["t12_report"]["pairs"] == 135


@pytest.mark.skipif(not H6_PATH.is_file(), reason=STORED_REASON)
def test_b1_m3_stored_h6_as_a_vbh_new_side_is_a_setting_defect(pass_grades) -> None:
    """The self check turns the M-3 checks off; a real VBH t12 with the H-6 on the new side
    (VB lines, no rev 5 record, no keys file) is refused."""
    h6 = json.loads(H6_PATH.read_text(encoding="utf-8"))
    _, problems = tjr.judge_t12("VBH", h6, {}, h6, {})
    assert problems.status() == compare.STATUS_SETTING_DEFECT
    assert not any("evidence" in text for text in problems.setting_defects)


def _without_evidence(document: dict) -> dict:
    for line in document["results"]:
        for key in ("rod_reading_truth_calls", "two_pressure_reads"):
            line["hydraulics_record"].pop(key)
    return document


def test_b1_evidence_is_checked_on_436_9_lines_only(pass_grades) -> None:
    base = _without_evidence(_dg3_document(setting="VB"))
    _, problems = tjr.judge_t12("VBH", base, {}, _dg3_document(), {})
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    _, problems = tjr.judge_t12("VBH", _dg3_document(setting="VB"), {},
                                _without_evidence(_dg3_document()), {})
    assert problems.status() == compare.STATUS_SETTING_DEFECT
    assert all("P4 evidence keys missing" in text for text in problems.setting_defects)


def test_b1_436_9_settings_are_the_run_v5_ones() -> None:
    import run_v5

    assert set(tjr.JP3_LINE_SETTINGS) == set(run_v5.JP3_SETTINGS)


# --- M-3 --------------------------------------------------------------------------------------

def _set_lines(document: dict, **values) -> dict:
    for line in document["results"]:
        line.update(values)
    return document


@pytest.mark.parametrize(("bundle", "base_setting", "new_setting", "revision"), [
    ("VBH", "VB", "VBJ", 5),      # a new line of another setting
    ("VBH", "VB", "VB", 5),
    ("VBJ", "VBJ0", "VBJ0", 5),   # VBJ and VBJ0 swapped on the new side
    ("VBJ", "VBH", "VBJ", 5),     # a VBJ base not VBJ0
    ("VBH", "VB", "VBH", 4),      # not a revision 5 record
])
def test_m3_setting_and_revision_of_the_lines(pass_grades, monkeypatch, bundle, base_setting,
                                              new_setting, revision) -> None:
    monkeypatch.setattr(tjr, "_dg3_j_p3", lambda lines, problems: {"status": "pass"})
    new = _dg3_document(setting=new_setting)
    for line in new["results"]:
        line["hydraulics_record"]["extend_bound_check"]["rule_revision"] = revision
    _, problems = tjr.judge_t12(bundle, _dg3_document(setting=base_setting), {}, new, {})
    assert problems.status() == compare.STATUS_SETTING_DEFECT


def test_m3_vbj_bundle_of_the_right_settings_passes(pass_grades, monkeypatch) -> None:
    monkeypatch.setattr(tjr, "_dg3_j_p3", lambda lines, problems: {"status": "pass"})
    _, problems = tjr.judge_t12("VBJ", _dg3_document(setting="VBJ0"), {},
                                _dg3_document(setting="VBJ"), {})
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()


def test_m3_new_file_equal_to_the_base_file(tmp_path) -> None:
    base, new, other = tmp_path / "base.json", tmp_path / "new.json", tmp_path / "other.json"
    for path, text in ((base, "{}"), (new, "{}"), (other, "[]")):
        path.write_text(text, encoding="utf-8")
    assert tjr.t12_file_defects(base, new)
    assert tjr.t12_file_defects(base, other) == []


def test_m3_t12_command_refuses_the_base_file_as_new(tmp_path, pass_grades,
                                                     monkeypatch) -> None:
    monkeypatch.setattr(tjr, "_dg3_j_p3", lambda lines, problems: {"status": "pass"})
    document = _dg3_document()
    files = {name: tmp_path / f"{name}.json" for name in ("base", "new", "judge")}
    files["base"].write_text(json.dumps(document), encoding="utf-8")
    files["new"].write_text(json.dumps(document), encoding="utf-8")
    files["judge"].write_text("{}", encoding="utf-8")
    judge_sha = fixed.file_sha256(files["judge"])
    exit_code = tjr.main(["t12", "--out", str(tmp_path / "out.json"), "--bundle", "VBJ",
                          "--base", str(files["base"]), "--base-judge", str(files["judge"]),
                          "--new", str(files["new"]), "--new-judge", str(files["judge"]),
                          "--base-judge-sha256", judge_sha, "--new-judge-sha256", judge_sha])
    report = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert exit_code == compare.STATUS_EXIT[compare.STATUS_SETTING_DEFECT]
    assert report["status"] == compare.STATUS_SETTING_DEFECT
    assert any("the same run on both sides" in text for text in report["setting_defects"])


# --- M-8 --------------------------------------------------------------------------------------

def test_m8_new_side_without_the_h6_keys_file_is_not_judgeable(pass_grades) -> None:
    new = _dg3_document()
    new["meta"] = {}
    _, problems = tjr.judge_t12("VBH", _dg3_document(setting="VB"), {}, new, {})
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE
    assert tjr.keys_file_problems("x", {"meta": {"keys_file": {
        "sha256": fixed.H6_SHA256, "n_keys": 134}}})


def test_m8_t12_needs_the_new_judge_sha(tmp_path) -> None:
    judge = tmp_path / "judge.json"
    judge.write_text("{}", encoding="utf-8")
    assert "missing" in tjr.judge_sha_problems("--new-judge", judge, None)[0]
    assert tjr.judge_sha_problems("--new-judge", judge, fixed.file_sha256(judge)) == []
    assert tjr.judge_sha_problems("--new-judge", judge, "0" * 64)


def _dg3_inputs(tmp_path, *, setting="VBJ0", document=None) -> tjr.Dg3JudgeInputs:
    extract, dg3 = tmp_path / "L1.json", tmp_path / "dg3.json"
    extract.write_text("{}", encoding="utf-8")
    dg3.write_text(json.dumps(document or _dg3_document(setting="VBJ0")), encoding="utf-8")
    return tjr.Dg3JudgeInputs(setting, dg3, extract, fixed.file_sha256(extract),
                              tmp_path / "judge.json")


def test_m8_dg3_judge_runs_r79_with_the_p1a_extract(tmp_path, monkeypatch) -> None:
    calls = []

    def run_r79_judge(out, files):
        calls.append([out, *files])
        out.write_text('{"runs": []}', encoding="utf-8")
        return {"exit_code": 0}

    monkeypatch.setattr(h8, "run_r79_judge", run_r79_judge)
    inputs = _dg3_inputs(tmp_path)
    report, problems, _ = tjr.make_dg3_judge(inputs)
    assert problems.status() == compare.STATUS_PASS, problems.as_dict()
    assert calls == [[inputs.judge_out, inputs.dg3, inputs.l1_reference]]
    assert report["judge_sha256"] == fixed.file_sha256(inputs.judge_out)
    assert report["l1_reference_sha256"] == inputs.l1_reference_sha256


@pytest.mark.parametrize("change", ["extract_sha", "judge_exists", "setting", "keys_file"])
def test_m8_dg3_judge_input_problems(tmp_path, change) -> None:
    document = _dg3_document(setting="VBJ0")
    if change == "keys_file":
        document["meta"] = {}
    inputs = _dg3_inputs(tmp_path, document=document,
                         setting="VBJ" if change == "setting" else "VBJ0")
    if change == "extract_sha":
        inputs = tjr.Dg3JudgeInputs(inputs.setting, inputs.dg3, inputs.l1_reference, "0" * 64,
                                    inputs.judge_out)
    if change == "judge_exists":
        inputs.judge_out.write_text("{}", encoding="utf-8")
    assert len(tjr.dg3_input_problems(inputs)) == 1


# --- M-4 --------------------------------------------------------------------------------------

def _t8_status(change) -> dict:
    problems = compare.Problems()
    return tjr.judge_t8(_t8_inputs(change), problems)


def _check_of(inputs, setting, key) -> dict:
    return inputs.rerun[setting][key]["hydraulics_record"]["extend_bound_check"]


@pytest.mark.parametrize(("change", "test"), [
    (lambda inputs, key: _check_of(inputs, "VBH", key).update(rule_revision=4), "T-JR-10"),
    (lambda inputs, key: _check_of(inputs, "VBH", key).update(spec_edition="f2f7dfad"),
     "T-JR-10"),
    (lambda inputs, key: _check_of(inputs, "VBJ", key).update(carry_end_rule="fresh_stretch"),
     "T-JR-11"),
    (lambda inputs, key: inputs.rerun["VBJ0"][key]["hydraulics_record"].pop(
        "two_pressure_reads"), "T-JR-11"),
    (lambda inputs, key: inputs.rerun["VBH"][key]["hydraulics_record"].update(
        rod_reading_truth_calls=3), "T-JR-10"),
])
def test_m4_t8_identity_and_evidence_are_setting_defects(change, test) -> None:
    report = _t8_status(change)
    assert report[test]["status"] == compare.STATUS_SETTING_DEFECT
    other = "T-JR-11" if test == "T-JR-10" else "T-JR-10"
    assert report[other]["status"] == compare.STATUS_PASS


@pytest.mark.parametrize("value", [None, "a" * 10])
def test_m4_t_jr_11_needs_64_character_hashes(value) -> None:
    def same_short_hash(inputs, key):
        inputs.rerun["VBJ"][key]["commands_sha256"] = value
        inputs.rerun["VBJ0"][key]["commands_sha256"] = value

    report = _t8_status(same_short_hash)
    assert report["T-JR-11"]["status"] == compare.STATUS_FAILED


# --- M-5 --------------------------------------------------------------------------------------

JUDGED_ROW = {"rule_revision": 5, "jp3a_breach_reads": [0] * 4,
              "jp3b_breach_over_tol_reads": [0] * 4, "jp3c_breach_reads": [0] * 4,
              "sensor_grade": "normal", "spec_edition": "8be9de22",
              "carry_end_rule": "inherit_when_gate_shut", "retract_start_rule": "with_tracker"}


@pytest.mark.parametrize("change", [{"jp3c_breach_reads": None}, {"jp3a_breach_reads": [0] * 3},
                                    {"jp3b_breach_over_tol_reads": 0}])
def test_m5_j_p3_rev5_missing_judged_key_is_not_judgeable(change) -> None:
    row = {key: value for key, value in {**JUDGED_ROW, **change}.items() if value is not None}
    result = esb.j_p3_judgement_rev5([JUDGED_ROW, row])
    assert result["status"] == "no_judged_runs"
    assert result["judged_key_missing_runs"] == 1
    assert esb.j_p3_judgement_rev5([JUDGED_ROW])["status"] == "pass"


@pytest.mark.parametrize(("check", "kind"), [
    ({"retract_tracker_dominated_reads": [0] * 4, "retract_tracker_stretch_log": []}, None),
    ({"retract_tracker_dominated_reads": [0, 1, 0, 0], "retract_tracker_stretch_log": []},
     "failures"),
    ({"retract_tracker_dominated_reads": [0] * 4, "retract_tracker_stretch_log": [{}]},
     "failures"),
    ({"retract_tracker_stretch_log": []}, "not_judgeable"),
    ({"retract_tracker_dominated_reads": [0] * 4}, "not_judgeable"),
    ({"retract_tracker_dominated_reads": [0] * 3, "retract_tracker_stretch_log": []},
     "not_judgeable"),
])
def test_m5_p4_9_missing_key_is_not_judgeable(check, kind) -> None:
    problems = compare.Problems()
    compare.retract_tracker_problems("VBJ", check, problems)
    for name in ("failures", "not_judgeable"):
        assert bool(getattr(problems, name)) == (name == kind)


# --- M-6 --------------------------------------------------------------------------------------

GOOD_LOCK_ROW = {"job": {"setting": "VBJ"},
                 "hydraulics_record": _seed_record([[1.0, 2, 0.0, False]])}


@pytest.mark.parametrize("empty", ["replay", "dg3", "lock_rows"])
def test_m6_empty_records_input_is_not_judgeable(empty) -> None:
    inputs = {"replay": REPLAY_REPORTS, "dg3": [_dg3_document(count=1)],
              "lock_rows": [GOOD_LOCK_ROW]}
    inputs[empty] = []
    _, problems = tjr.judge_records(inputs["replay"], inputs["dg3"], inputs["lock_rows"])
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE
    _, problems = tjr.judge_records([], [], [])
    assert len(problems.not_judgeable) == 3


@pytest.mark.parametrize("change", [
    lambda reports: reports[0].update(judged=False),
    lambda reports: reports[0].update(stop="ideal_record"),
    lambda reports: reports[1].update(runs=134),
    lambda reports: reports[1]["rows"].__setitem__(0, {"error": "x"}),
    lambda reports: reports.pop(1),
    lambda reports: reports[0].update(runs=400, rows=[{}] * 400),
])
def test_m6_replay_reports_of_t_jr_13(change) -> None:
    reports = json.loads(json.dumps(REPLAY_REPORTS))
    change(reports)
    _, problems = tjr.judge_records(reports, [_dg3_document(count=1)], [GOOD_LOCK_ROW])
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


def test_m6_t_jr_15_seed_net_force_over_1n_fails(tmp_path) -> None:
    over = {"job": {"setting": "VBJ"}, "hydraulics_record": _seed_record([[1.0, 2, 1.5, False]])}
    _, problems = tjr.judge_records(REPLAY_REPORTS, [_dg3_document(count=1)],
                                    [GOOD_LOCK_ROW, over])
    assert problems.status() == compare.STATUS_FAILED
    paths = []
    for name, document in (("replay_a", REPLAY_REPORTS[0]), ("replay_b", REPLAY_REPORTS[1]),
                           ("dg3", _dg3_document(count=1))):
        paths.append(tmp_path / f"{name}.json")
        paths[-1].write_text(json.dumps(document), encoding="utf-8")
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps(GOOD_LOCK_ROW) + "\n" + json.dumps(over) + "\n",
                    encoding="utf-8")
    exit_code = tjr.main(["records", "--out", str(tmp_path / "out.json"), "--replay",
                          str(paths[0]), str(paths[1]), "--dg3", str(paths[2]),
                          "--lock-rows", str(rows)])
    assert exit_code == compare.STATUS_EXIT[compare.STATUS_FAILED] == 1


# --- R-7, R-8 ---------------------------------------------------------------------------------

def test_r7_reference_extract_never_overwrites(tmp_path) -> None:
    noise = {"meta": {}, "results": [{"key": "a", "level": h8.LEVEL_REFERENCE}]}
    path = tmp_path / "L1.json"
    h8.reference_extract(noise, path)
    first = path.read_bytes()
    h8.reference_extract(noise, path)  # the same bytes: kept, as before
    assert path.read_bytes() == first
    noise["results"].append({"key": "b", "level": h8.LEVEL_REFERENCE})
    with pytest.raises(FileExistsError):
        h8.reference_extract(noise, path)
    assert path.read_bytes() == first


def test_r7_base_judge_refuses_an_existing_extract(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fixed, "sha_problem", lambda path, expected, label: None)
    judge_out = tmp_path / "h6_base_judge.json"
    tjr.l1_reference_path(judge_out).write_text("{}", encoding="utf-8")
    _, problems, _ = tjr.make_base_judge(tmp_path / "h6.json", tmp_path / "noise.json",
                                         judge_out)
    assert any("_L1_reference.json exists" in text for text in problems.not_judgeable)


def test_r8_stored_h6_judge_sha_is_fixed(tmp_path) -> None:
    assert fixed.STORED_H6_JUDGE_SHA256 == (
        "f8352c5d12d31aebcffe2a4bc5bdfa7919e605a3f3261da8455640df3bad0d0b")
    for name in ("h6.json", "new.json", "stored.json", "h6_judge.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    inputs = tjr.JudgeCompareInputs(tmp_path / "h6.json", tmp_path / "new.json", "0" * 64,
                                    tmp_path / "stored.json", tmp_path / "h6_judge.json")
    _, problems, _ = tjr.compare_base_judges(inputs)
    assert any("--stored-h6-judge" in text for text in problems.not_judgeable)


# --- M-1 --------------------------------------------------------------------------------------

def test_m1_wrap_writes_start_and_end_and_returns_the_exit_code(tmp_path) -> None:
    output = tmp_path / "case_C.jsonl"
    exit_code = run_identity.main(["wrap", str(output), "--", sys.executable, "-I", "-c",
                                   "raise SystemExit(3)"])
    assert exit_code == 3
    sidecar = json.loads(run_identity.sidecar_path(output).read_text(encoding="utf-8"))
    assert [len(sidecar["start"]), len(sidecar["end"])] == [1, 1]
    for record in (sidecar["start"][0], sidecar["end"][0]):
        assert len(record["git"]["head"]) == 40 and "is_clean" in record["git"]
    assert run_identity.main(["mark", str(output), "end"]) == 0  # the same head: appended


def test_m1_records_of_another_head_are_refused(tmp_path) -> None:
    output = tmp_path / "dg3_VBH.json"
    run_identity.sidecar_path(output).write_text(
        json.dumps({"start": [{"git": {"head": "0" * 40}}]}), encoding="utf-8")
    before = hashlib.sha256(run_identity.sidecar_path(output).read_bytes()).hexdigest()
    assert run_identity.main(["mark", str(output), "start"]) == run_identity.REFUSED_EXIT
    assert run_identity.main(["wrap", str(output), "--", sys.executable, "-I", "-c",
                              "raise SystemExit(0)"]) == run_identity.REFUSED_EXIT
    after = hashlib.sha256(run_identity.sidecar_path(output).read_bytes()).hexdigest()
    assert before == after
