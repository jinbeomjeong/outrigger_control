"""436.9 J-P3 edition 4a addendum 4a-4 (``jp3_remedy_spec_addendum_4a4.md``) table 7:
D1-a / D1-b (the r79 dry key outside every stored key, the runner's take of it), W1 (the r79
dry commands of the T-JR-12 runner), W2 (the VB record makes T-JR-10 alone not judgeable), D2
(the fixed input sha of 5) and P-1 (the stored H-6 self check with the real judge file).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a3 import (  # noqa: E402
    SELECT_INPUTS,
    SELECTION,
    _summary_files,
    _t8_inputs,
)

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
NOISE_PATH = DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "resume_k1" / (
    "h8_noise_VB.json")

TABLE_5 = {
    "H10_SHA256": "ce526b1f71e635e6b80d538f36841ece01710af46f02acb4b3fa1355a5a4dcb3",
    "MAIN_JSONL_SHA256": "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e",
    "H6_SHA256": "ea0ab94c81e58eeb83ab2b6a63494a56c16bcd4165a62de47eba5efd03f23c89",
    "NOISE_VB_SHA256": "2219ab9782b22fbe07e6c1f90e8b49c6b3703b0575b5d7cfb7d72b4f067bec43",
    "BASELINE_SUMS_SHA256": "197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361",
    "GRID_SHA256": "7160f9f19b497ea264e9dd90c58c2da25540ded51e8510197205cf91f00bd827",
}
"""4a-4 5 table (with the 1 table's ``h8_noise_VB.json``), typed from the document."""


# --- D2 -------------------------------------------------------------------------------------

def test_d2_fixed_values_are_the_table() -> None:
    for name, value in TABLE_5.items():
        assert getattr(fixed, name) == value, name
    assert compare.BASELINE_SUMS_SHA256 == fixed.BASELINE_SUMS_SHA256
    assert case_judge.GRID_SHA256 == fixed.GRID_SHA256


def test_d2_sha_problem(tmp_path) -> None:
    path = tmp_path / "x.json"
    path.write_text("{}", encoding="utf-8")
    assert fixed.sha_problem(path, fixed.file_sha256(path), "x") is None
    assert "not the fixed" in fixed.sha_problem(path, fixed.H6_SHA256, "x")
    assert "missing" in fixed.sha_problem(tmp_path / "none", fixed.H6_SHA256, "x")


def test_d2_t8_stored_sha_makes_t_jr_10_not_judgeable() -> None:
    inputs = replace(_t8_inputs(), stored_sha_problem="--stored: other sha")
    problems = compare.Problems()
    report = tjr.judge_t8(inputs, problems)
    assert report["T-JR-10"]["status"] == compare.STATUS_NOT_JUDGEABLE
    assert report["T-JR-11"]["status"] == compare.STATUS_PASS


def test_d2_t8_main_jsonl_of_another_sha_is_not_judgeable(tmp_path) -> None:
    for name in ("main.jsonl", "stored.jsonl", "rerun.jsonl"):
        (tmp_path / name).write_text("", encoding="utf-8")
    args = tjr._parser().parse_args([
        "t8", "--out", str(tmp_path / "out.json"), "--stored", str(tmp_path / "stored.jsonl"),
        "--rerun", str(tmp_path / "rerun.jsonl"), "--main-jsonl", str(tmp_path / "main.jsonl")])
    problems = compare.Problems()
    inputs, _ = tjr.t8_inputs(args, problems)
    assert any("--main-jsonl" in text for text in problems.not_judgeable)
    assert inputs.stored_sha_problem is not None
    assert tjr.main(["t8", "--out", str(tmp_path / "out2.json"), "--stored",
                     str(tmp_path / "stored.jsonl"), "--rerun", str(tmp_path / "rerun.jsonl"),
                     "--main-jsonl", str(tmp_path / "main.jsonl")]) == compare.EXIT_NOT_JUDGEABLE


def test_d2_t12_vbh_needs_the_fixed_base_and_the_judge_sha(tmp_path) -> None:
    base, judge = tmp_path / "h6.json", tmp_path / "judge.json"
    base.write_text("{}", encoding="utf-8")
    judge.write_text("{}", encoding="utf-8")
    problems = tjr.t12_input_problems("VBH", base, judge, None)
    assert any("--base (stored H-6)" in text for text in problems)
    assert any("--base-judge-sha256 missing" in text for text in problems)
    wrong = tjr.t12_input_problems("VBJ", base, judge, "0" * 64)
    assert any("--base-judge" in text for text in wrong)
    assert tjr.t12_input_problems("VBJ", base, judge, fixed.file_sha256(judge)) == []
    # prelaunch audit M-8: the VBJ bundle needs the VBJ0 judge sha too
    assert any("--base-judge-sha256 missing" in text
               for text in tjr.t12_input_problems("VBJ", base, judge, None))


def test_d2_run_v5_p3_hash_source_of_another_sha_is_refused(tmp_path, monkeypatch) -> None:
    import run_v5

    source = tmp_path / "main.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(run_v5, "P3_HASH_SOURCE_OVERRIDE", [None])
    with pytest.raises(SystemExit) as stop:
        run_v5._parse_args(["j9_t8", "--p3-hash-source", str(source)])
    assert stop.value.code == 2
    assert run_v5.P3_HASH_SOURCE_OVERRIDE[0] is None


def test_d2_select_refuses_other_inputs(tmp_path) -> None:
    for name in ("noise", "dg3", "main"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    inputs = dryrun.SelectInputs(tmp_path, tmp_path / "main", tmp_path, tmp_path / "dg3",
                                 tmp_path / "noise")
    assert len(dryrun.fixed_input_problems(inputs)) == 3
    with pytest.raises(dryrun.Stop, match="--noise"):
        dryrun.select(inputs)


# --- W2 -------------------------------------------------------------------------------------

def _t8_report(change):
    problems = compare.Problems()
    return tjr.judge_t8(_t8_inputs(change), problems), problems


@pytest.mark.parametrize("change", [
    lambda inputs, key: inputs.rerun["VB"][key].update(commands_sha256="e" * 64),
    lambda inputs, key: inputs.rerun["VB"].pop(key),
    lambda inputs, key: (inputs.rerun["VB"].pop(key), inputs.bad_rows.update({"rerun:VB": 1})),
    lambda inputs, key: inputs.rerun["VB"][key].update(commands_sha256="e" * 10),
], ids=["vb_hash_differs", "vb_line_missing", "vb_error_row", "vb_hash_not_64"])
def test_w2_vb_record_makes_only_t_jr_10_not_judgeable(change) -> None:
    report, problems = _t8_report(change)
    assert report["T-JR-10"]["status"] == compare.STATUS_NOT_JUDGEABLE
    assert tjr.VB_STALE_REASON in problems.not_judgeable[0]
    assert report["T-JR-11"]["status"] == compare.STATUS_PASS
    assert report["T-JR-11"]["equal"] == 22
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


def test_w2_t_jr_11_is_still_judged_when_t_jr_10_is_not() -> None:
    def stale_and_t11_differs(inputs, key):
        inputs.rerun["VB"][key]["commands_sha256"] = "e" * 64
        inputs.rerun["VBJ"][key]["commands_sha256"] = "f" * 64

    report, problems = _t8_report(stale_and_t11_differs)
    assert report["T-JR-11"]["status"] == compare.STATUS_FAILED
    assert report["T-JR-10"]["status"] == compare.STATUS_NOT_JUDGEABLE
    assert report["VB_rerun_record"]["differing_count"] == 1


# --- D1-a / D1-b / W1 -------------------------------------------------------------------------

BASE_KEY = "L2|s0|g6|0|g6|G1+J1@FL|top|Fs0"


def test_d1a_only_the_seed_token_changes() -> None:
    key, seed = dryrun.generated_key(BASE_KEY, frozenset())
    assert (key, seed) == ("L2|s25|g6|0|g6|G1+J1@FL|top|Fs0", 25)
    assert key.split("|")[0] == "L2" and key.split("|")[2:] == BASE_KEY.split("|")[2:]


def test_d1a_seed_rises_past_scanned_keys() -> None:
    scanned = frozenset({"L2|s25|g6|0|g6|G1+J1@FL|top|Fs0", "L2|s26|g6|0|g6|G1+J1@FL|top|Fs0"})
    key, seed = dryrun.generated_key(BASE_KEY, scanned)
    assert seed == 27 and key not in scanned


def test_d1a_scan_reads_keys_of_json_and_jsonl_without_prefix(tmp_path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.json").write_text(json.dumps({"results": [
        {"key": "cand=current#L2|s25|g6|0|g6|G1+J1@FL|top|Fs0"},
        {"key": "screen|top|8.0|ready|FR"}]}), encoding="utf-8")
    (tmp_path / "b.jsonl").write_text(json.dumps({"key": "L3|s7|g6|1|x"}) + "\n",
                                      encoding="utf-8")
    (tmp_path / "c.txt").write_text('"key": "L2|s99|x|1|y"', encoding="utf-8")
    scan = dryrun.scan_r79_keys(tmp_path)
    assert scan.keys == {"L2|s25|g6|0|g6|G1+J1@FL|top|Fs0", "L3|s7|g6|1|x"}
    assert scan.seed_max == 25 and len(scan.files) == 2
    key, seed = dryrun.generated_key(BASE_KEY, scan.keys)
    assert seed == 26 and key not in scan.keys


def test_d1a_empty_scan_is_not_judgeable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(dryrun, "fixed_input_problems", lambda inputs: [])
    monkeypatch.setattr(dryrun, "judged_union", lambda *args: {"event_union": set(),
                                                               "sizes": {}})
    inputs = replace(SELECT_INPUTS, scan_root=tmp_path)
    with pytest.raises(dryrun.Stop, match="scan found nothing"):
        dryrun.select(inputs)


STORED_DRY_SELECTION = (DATA_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9"
                        / "ed5_inputs" / "dry_selection.json")
"""The edition 5 prelaunch dry selection of the current run commit (``prelaunch_ed5.ps1 -Part
dry``), once written."""


def _listed_scan(scan_root: Path, stored_scan: dict) -> dryrun.KeyScan:
    """Erratum 6 (D-5): the 4a-4 1 scan over exactly the files a stored selection recorded
    (path and sha256 each, scanned and excluded); a changed or missing file fails the test.
    The same key rule as :func:`jp3_dryrun_evidence.scan_r79_keys` (no value is read)."""
    def read(item: dict) -> tuple[str, str, list]:
        relative = item["path"]
        path = scan_root / relative
        assert path.is_file(), f"stored scan file {relative} missing"
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest == item["sha256"], f"stored scan file {relative} changed"
        return relative, digest, dryrun.R79_KEY_PATTERN.findall(data)

    keys: set[str] = set()
    files, excluded, seed_max = [], [], None
    for item in stored_scan["files"]:  # the recorded order (the scan's own path order)
        relative, digest, found = read(item)
        assert not dryrun.is_scan_excluded(relative), relative
        for key, seed in found:
            keys.add(dryrun.plain_key(key.decode("utf-8")))
            seed_max = int(seed) if seed_max is None else max(seed_max, int(seed))
        files.append((relative, digest, len(found)))
    for item in stored_scan["excluded"]:
        relative, digest, found = read(item)
        assert dryrun.is_scan_excluded(relative), relative
        excluded.append((relative, digest, len(found),
                         frozenset(dryrun.plain_key(key.decode("utf-8")) for key, _ in found)))
    return dryrun.KeyScan(frozenset(keys), tuple(files), seed_max, tuple(excluded))


@pytest.mark.skipif(not NOISE_PATH.is_file(), reason="stored h8_noise_VB.json not present")
def test_d1a_selection_of_the_stored_data(tmp_path, monkeypatch) -> None:
    """4a-4 1 / 2 on the main checkout's ``06_analysis``: seed max 24 in the scan outside the
    J-P3 run outputs (``j9_runs/`` left out, user decision 2026-11-21: their dry r79 runs hold
    the dry key itself; only paths are listed, no value is read), the generated key ``s25`` of
    the base key, in neither the scan nor the Dg-3 keys.

    Edition 5 erratum 6 (D-5): once the run commit's prelaunch dry selection exists, the scan
    is the one it recorded (every listed file with its sha256; the selection's own outputs were
    written after it), and the reproduced selection must equal the stored one."""
    analysis = DATA_ROOT / "06_analysis"
    v5 = analysis / "03_hydraulic" / "coupled" / "v5"
    inputs = dryrun.SelectInputs(analysis, v5 / "main.jsonl",
                                 analysis / "02_control" / "j_p3_cause" / "baseline_221456d",
                                 v5 / "resume_k1" / "h6_dg3_v4on.json", NOISE_PATH)
    stored = None
    if STORED_DRY_SELECTION.is_file():
        stored = json.loads(STORED_DRY_SELECTION.read_text(encoding="utf-8"))
        monkeypatch.setattr(dryrun, "scan_r79_keys",
                            lambda root: _listed_scan(root, stored["scan"]))
    selection = dryrun.select(inputs)
    if stored is not None:
        for name in ("event_job", "r79_base_key", "r79_key", "r79_seed", "r79_key_in_scan",
                     "r79_key_in_dg3"):
            assert selection[name] == stored[name], name
        # ``keys_file`` is added by ``main`` after ``select`` (the key file it writes)
        assert {family: {k: v for k, v in chosen.items() if k != "keys_file"}
                for family, chosen in stored["r79_families"].items()} == selection["r79_families"]
        assert selection["scan"] == {**stored["scan"], "root": str(analysis)}
    assert selection["r79_base_key"] == BASE_KEY
    # 24 in the stored runs; 30 once the edition 5 probe record (erratum 2 2-3,
    # ed5_design/probes/probes_ed5.json, s30 keys) is under 06_analysis: no s25 key either way
    probe_files = [item for item in selection["scan"]["files"]
                   if item["path"].endswith("ed5_design/probes/probes_ed5.json")]
    assert selection["scan"]["seed_max"] == (30 if probe_files else 24)
    assert selection["scan"]["excluded_folder"] == "02_control/j_p3_cause/j9_runs/"
    assert selection["scan"]["files_excluded"] == len(selection["scan"]["excluded"]) > 0
    assert all(item["path"].startswith("02_control/j_p3_cause/j9_runs/")
               for item in selection["scan"]["excluded"])
    assert selection["r79_seed"] == 25 and selection["r79_key"] == dryrun.generated_key(
        BASE_KEY, frozenset())[0]
    assert selection["r79_key_in_scan"] is False and selection["r79_key_in_dg3"] is False
    assert selection["scan"]["files_with_r79_keys"] > 0
    # addendum 4a-8 3: one key per family, the base keys of its table, outside the scan
    base_keys = {family: chosen["base_key"]
                 for family, chosen in selection["r79_families"].items()}
    assert base_keys == {"g6": BASE_KEY, "g8": "L2|s0|g8|0|slope|edge|top|4.0|ref|none|0",
                         "ref": "L2|s0|ref|0|rigid|B|0,0"}
    for chosen in selection["r79_families"].values():
        assert chosen["seed"] == 25 and chosen["in_scan"] is False
        assert chosen["in_dg3"] is False


@pytest.mark.parametrize(("key", "seed"), [
    ("cand=current#L2|s0|g6|0|g6|G1+J1@FL|top|Fs0", 25),
    ("cand=current#L2|s25|g6|0|g6|G1+J1@FL|top|Fs0", 0),
])
def test_d1b_runner_must_take_the_generated_key(tmp_path, key, seed) -> None:
    events, r79 = _summary_files(tmp_path, r79_key=key, r79_seed=seed)
    summary, code = dryrun.summarize(SELECTION, events, r79)
    assert code == dryrun.EXIT_NOT_JUDGEABLE
    assert all(row.get("stop") == dryrun.ASK_AGAIN for row in summary["rows"]
               if row["run"] in ("r79_VBJ", "r79_VBH"))  # the g6 runs took another key


def test_w1_r79_commands_are_the_t_jr_12_runner_and_environment(tmp_path) -> None:
    commands = dryrun._commands({"case": "R14"}, {"g6": tmp_path / "key.txt",
                                                  "g8": tmp_path / "key_g8.txt"})
    assert "--keys-file " + str(tmp_path / "key_g8.txt") in commands["r79_VBJ_g8"]
    for setting in ("VBJ", "VBH"):
        command = commands[f"r79_{setting}"]
        for word in (f"R79_V5_SETTING={setting}", f"R79_T4H_DIR=dryrun_evidence/{setting}_t4h",
                     "LAS_T3_DG3_LAS=on", "LAS_T3_DG3_K1=on", "LAS_T3_DG3_P3=on",
                     "las_t3_dg3.py", "--levels L2", f"--keys-file {tmp_path / 'key.txt'}"):
            assert word in command, (setting, word)
    assert "R79_ROD_MODEL=plant_truth" in commands["r79_VBJ"]
    assert "R79_ROD_MODEL" not in commands["r79_VBH"]
    assert dryrun.EXPECTED[("r79", "VBH")] == "truth_zero_monitor_positive"
    assert dryrun.meets("truth_zero_monitor_positive",
                        {"error": False, "rod_reading_truth_calls": 0, "two_pressure_reads": 0}
                        ) is False


# --- P-1 --------------------------------------------------------------------------------------

def _selfcheck_report(**changes) -> dict:
    report = {"pairs": 135, "l2_pass_to_fail": [], "new_fault": [], "ready_failures": [],
              "ready_improved_record": [], "ready_both_missing_record": [{}] * 7,
              "grade_transitions_record": {"L2": {"pass->pass": 1},
                                           "L3": {"pass->pass": 120, "fail->fail": 14}}}
    report.update(changes)
    return report


@pytest.mark.parametrize(("changes", "misses"), [
    ({}, 0),
    ({"ready_both_missing_record": [{}] * 6}, 1),
    ({"grade_transitions_record": {"L3": {"pass->fail": 1}}}, 1),
    ({"new_fault": ["k"]}, 1),
    ({"pairs": 134}, 1),
])
def test_p1_selfcheck_expectations_are_the_6_table(changes, misses) -> None:
    assert len(tjr.selfcheck_problems(_selfcheck_report(**changes), compare.Problems())) == misses


def test_p1_selfcheck_needs_the_fixed_h6_and_the_judge_sha(tmp_path) -> None:
    h6, judge = tmp_path / "h6.json", tmp_path / "judge.json"
    h6.write_text("{}", encoding="utf-8")
    judge.write_text("{}", encoding="utf-8")
    _, problems, _ = tjr.t12_selfcheck(h6, judge, fixed.file_sha256(judge))
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE
