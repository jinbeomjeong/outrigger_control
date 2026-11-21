"""436.9 addendum 4a-8 (H8-1 .. H8-5 and the 6.1 closure tool): the B2 evidence k rule, the
VBJ / VBJ0 L1 key file and reference, the judge row checks of ``dg3-judge`` and ``t12``.

Synthetic data, except the real H-6 / L1 extract key test (H8-3), which reads keys only.
"""

from __future__ import annotations

import json
import os
import subprocess
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
import jp3_import_closure as closure  # noqa: E402
import jp3_rejudge_inputs as rejudge  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import _dg3_document  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
ANALYSIS = DATA_ROOT / "06_analysis"
H6_PATH = ANALYSIS / "03_hydraulic" / "coupled" / "v5" / "resume_k1" / "h6_dg3_v4on.json"
L1_EXTRACT = (ANALYSIS / "02_control" / "verif_matrix" / "v5_resume_4368" / "judge_932f1fb"
              / "harness_path1" / "h6_L1_reference.json")


def _evidence(truth: int, reads: int) -> dict:
    return {"rod_reading_truth_calls": truth, "two_pressure_reads": reads}


# --- H8-1: k -----------------------------------------------------------------------------------

@pytest.mark.parametrize(("line", "k"), [
    ({"key": "cand=current#L3|s0|g8|2|slope|edge|top|4.0|FL|raised|170.0"}, 2),
    ({"key": "L2|s25|g8|0|slope|edge|top|4.0|ref|none|0"}, 2),
    ({"key": "cand=current#L2|s0|g6|52|ref|J1|top|Fs0"}, 1),
    ({"key": "L2|s0|ref|0|rigid|B|0,0"}, 1),
    ({"job": {"case": "R12", "setting": "VBJ"}}, 1),           # a run_v5 line: no r79 key
    ({"key": "screen|top|8.0|ready|FR"}, 1),                    # not an r79 key
])
def test_h8_1_multiplier(line, k) -> None:
    assert compare.evidence_multiplier(line) == k


P4 = {"rod_reading_truth": True}
G8 = "L3|s0|g8|2|slope|edge|top|4.0|FL|raised|170.0"
G6 = "L2|s0|g6|52|ref|J1|top|Fs0"


@pytest.mark.parametrize(("key", "evidence", "options", "is_sound"), [
    (G8, _evidence(80, 40), P4, True),    # g8: 1 = 2 x 2 passes
    (G8, _evidence(40, 40), P4, False),   # g8: 1 = 2 fails
    (G6, _evidence(80, 40), P4, False),   # g6: 1 = 2 x 2 fails
    (G6, _evidence(40, 40), P4, True),
    (None, _evidence(7, 7), P4, True),    # a run_v5 line: k = 1
    (None, _evidence(14, 7), P4, False),
    (G8, _evidence(0, 0), P4, False),     # P4 on, no rod read
    (G8, _evidence(0, 5), {}, True),      # P4 off: 1 = 0
    (G8, {"two_pressure_reads": 5}, P4, False),  # a key missing: not 0
])
def test_h8_1_rod_evidence_rule(key, evidence, options, is_sound) -> None:
    line = {"hydraulics_record": evidence, "hydraulic_options": options,
            **({} if key is None else {"key": f"cand=current#{key}"})}
    problems = compare.line_evidence_problems(line)
    assert (problems == []) is is_sound, problems


@pytest.mark.parametrize(("evidence", "k", "is_declared", "is_sound"), [
    (_evidence(80, 40), 2, False, True),
    (_evidence(40, 40), 2, False, False),
    (_evidence(80, 40), 1, False, False),
    (_evidence(0, 0), 2, True, True),    # declared head-only: 1 = 2 = 0 whatever k is
    ({}, 2, False, False),
])
def test_h8_1_judged_line_rule(evidence, k, is_declared, is_sound) -> None:
    problems = compare.judged_line_evidence_problems(evidence, is_declared, k)
    assert (problems == []) is is_sound, problems


def _vbj_line(key: str, truth: int, reads: int) -> dict:
    return {"key": f"cand=current#{key}", "level": key[:2], "v5_setting": "VBJ",
            "hydraulic_options": P4,
            "hydraulics_record": {**_evidence(truth, reads), "extend_bound_check": {
                "rule_revision": 5, **compare.DEFAULT_IDENTITY}}}


@pytest.mark.parametrize(("line", "defects"), [
    (_vbj_line(G8, 80, 40), 0),
    (_vbj_line(G8, 40, 40), 2),   # the B2 check and the erratum 1 9 check
    (_vbj_line(G6, 40, 40), 0),
    (_vbj_line(G6, 80, 40), 2),
])
def test_h8_1_t12_lines(line, defects) -> None:
    problems = compare.Problems()
    tjr._check_lines("VBJ", {}, {"k": line}, problems)
    assert len(problems.setting_defects) == defects, problems.setting_defects


# --- H8-3: the L1 key file --------------------------------------------------------------------

@pytest.mark.skipif(not H6_PATH.is_file() or not L1_EXTRACT.is_file(),
                    reason="stored H-6 / L1 extract not present (run with OUTRIGGER_RECORDS_ROOT)")
def test_h8_3_l1_keys_of_the_stored_h6(tmp_path) -> None:
    """4a-8 4.2: 102 keys (g6 63, g8 29, ref 10), each an L1 key of the P-1a extract (same
    string, same case index); keys only are read."""
    keys_out = tmp_path / "l1_keys.json"
    out = tmp_path / "report.json"
    code = tjr.main(["l1-keys", "--h6", str(H6_PATH), "--keys-out", str(keys_out),
                     "--l1-extract", str(L1_EXTRACT), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_PASS, report
    assert report["keys"] == rejudge.L1_KEY_COUNT == 102
    assert report["by_harness"] == {"g6": 63, "g8": 29, "ref": 10}
    assert report["keys_not_in_extract"] == 0
    keys = [row["key"] for row in json.loads(keys_out.read_text(encoding="utf-8"))["results"]]
    extract = {h8.plain_key(line["key"])
               for line in json.loads(L1_EXTRACT.read_text(encoding="utf-8"))["results"]}
    assert len(set(keys)) == 102 and set(keys) <= extract
    assert report["keys_file_sha256"] == fixed.file_sha256(keys_out)
    again = tjr.main(["l1-keys", "--h6", str(H6_PATH), "--keys-out", str(keys_out),
                      "--out", str(tmp_path / "again.json")])
    assert again == compare.EXIT_NOT_JUDGEABLE  # never overwritten


def test_h8_3_keys_in_first_appearance_order() -> None:
    h6 = {"results": [
        {"harness": "g6", "inner": "a", "case_index": 4},
        {"harness": "g8", "inner": "b|c", "case_index": 0},
        {"harness": "g6", "inner": "a", "case_index": 4},   # the same pair again
        {"harness": "ref", "inner": "rigid|B|0,0", "case_index": 1}]}
    assert tjr.l1_keys_of(h6) == ["L1|s0|g6|4|a", "L1|s0|g8|0|b|c", "L1|s0|ref|1|rigid|B|0,0"]
    assert tjr.l1_key_pairs(tjr.l1_keys_of(h6)) == [("g6", "a"), ("g8", "b|c"),
                                                     ("ref", "rigid|B|0,0")]


# --- H8-4: dg3-judge -----------------------------------------------------------------------------

L1_KEYS = ("L1|s0|g6|0|a|x", "L1|s0|g8|1|b|y")


def _l1_files(tmp_path: Path, setting: str, **changes) -> tuple[Path, Path]:
    """A 4a-8 4.2 key file of two keys and the L1 run of ``setting`` on it."""
    keys_file = tmp_path / "l1_keys.json"
    keys_file.write_text(json.dumps({"results": [{"key": key} for key in L1_KEYS]}),
                         encoding="utf-8")
    lines = []
    for key in L1_KEYS:
        tokens = key.split("|", 4)
        lines.append({"key": f"cand=current#{key}", "level": "L1", "rod_model": "plant_truth",
                      "v5_setting": setting, "candidate": "current", "harness": tokens[2],
                      "inner": tokens[4], **changes})
    meta = {"keys_file": {"sha256": fixed.file_sha256(keys_file), "n_keys": len(L1_KEYS)}}
    run = tmp_path / f"l1_{setting}.json"
    run.write_text(json.dumps({"meta": meta, "results": lines}), encoding="utf-8")
    return keys_file, run


@pytest.fixture
def two_l1_keys(monkeypatch):
    monkeypatch.setattr(rejudge, "L1_KEY_COUNT", len(L1_KEYS))


def _judge_stub(drop: int = 0, unmatched: int = 0):
    def run_r79_judge(out, files):
        lines = json.loads(files[0].read_text(encoding="utf-8"))["results"]
        keys = [line["key"] for line in lines]
        out.write_text(json.dumps({"runs": [{"key": key} for key in keys[:len(keys) - drop]],
                                   "unmatched": keys[:unmatched], "errors": []}),
                       encoding="utf-8")
        return {"exit_code": 0}
    return run_r79_judge


def _dg3_judge_main(tmp_path, setting, keys_file, l1_run, extra=()) -> tuple[int, dict]:
    dg3 = tmp_path / f"dg3_{setting}.json"
    dg3.write_text(json.dumps(_dg3_document(setting=setting)), encoding="utf-8")
    out = tmp_path / "report.json"
    args = ["dg3-judge", "--setting", setting, "--dg3", str(dg3), "--l1-reference", str(l1_run),
            "--l1-reference-sha256", fixed.file_sha256(l1_run),
            "--judge-out", str(tmp_path / "judge.json"), "--out", str(out), *extra]
    if keys_file is not None:
        args += ["--l1-keys-file", str(keys_file)]
    code = tjr.main(args)
    return code, json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("setting", ["VBJ", "VBJ0"])
def test_h8_4_plant_truth_reference_passes(tmp_path, monkeypatch, two_l1_keys, setting) -> None:
    monkeypatch.setattr(h8, "run_r79_judge", _judge_stub())
    keys_file, l1_run = _l1_files(tmp_path, setting)
    code, report = _dg3_judge_main(tmp_path, setting, keys_file, l1_run)
    assert code == compare.EXIT_PASS, report
    assert report["judge_rows"] == {"runs": 135, "unmatched": 0, "errors": 0, "lines": 135}


@pytest.mark.parametrize(("changes", "stub", "keys"), [
    ({"rod_model": "dyn_map"}, _judge_stub(), True),   # a dyn_map reference for VBJ lines
    ({"v5_setting": "VBJ0"}, _judge_stub(), True),     # another setting's L1 run
    ({"level": "L2"}, _judge_stub(), True),
    ({"candidate": "other"}, _judge_stub(), True),
    ({}, _judge_stub(), False),                        # no key file
    ({}, _judge_stub(drop=135), True),                 # zero judged rows
    ({}, _judge_stub(drop=1), True),                   # 134 judged rows
    ({}, _judge_stub(unmatched=1), True),              # an unmatched line
])
def test_h8_4_vbj_not_judgeable(tmp_path, monkeypatch, two_l1_keys, changes, stub,
                                keys) -> None:
    monkeypatch.setattr(h8, "run_r79_judge", stub)
    keys_file, l1_run = _l1_files(tmp_path, "VBJ", **changes)
    code, report = _dg3_judge_main(tmp_path, "VBJ", keys_file if keys else None, l1_run)
    assert code == compare.EXIT_NOT_JUDGEABLE, report
    assert report["status"] == compare.STATUS_NOT_JUDGEABLE


def test_h8_4_dyn_map_extract_for_vbj_is_not_judgeable(tmp_path, monkeypatch,
                                                       two_l1_keys) -> None:
    """The 78fd5d2d case: the P-1a (dyn_map, VB) extract given as the VBJ reference."""
    monkeypatch.setattr(h8, "run_r79_judge", _judge_stub())
    keys_file, _ = _l1_files(tmp_path, "VBJ")
    extract = tmp_path / "p1a_extract.json"
    extract.write_text(json.dumps({"results": [
        {"key": f"cand=current#{key}", "level": "L1", "rod_model": "dyn_map",
         "v5_setting": "VB", "candidate": "current"} for key in L1_KEYS]}), encoding="utf-8")
    code, report = _dg3_judge_main(tmp_path, "VBJ", keys_file, extract)
    assert code == compare.EXIT_NOT_JUDGEABLE
    assert any("rod_model" in text for text in report["not_judgeable"])


def test_h8_4_vbh_keeps_the_fixed_p1a_extract(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(h8, "run_r79_judge", _judge_stub())
    extract = tmp_path / "extract.json"
    extract.write_text("{}", encoding="utf-8")
    code, report = _dg3_judge_main(tmp_path, "VBH", None, extract)
    assert code == compare.EXIT_NOT_JUDGEABLE  # not the fixed a591c3a8 sha
    assert any("P-1a" in text for text in report["not_judgeable"])
    monkeypatch.setattr(fixed, "STORED_H6_L1_REFERENCE_SHA256", fixed.file_sha256(extract))
    folder = tmp_path / "fixed"
    folder.mkdir()
    code, report = _dg3_judge_main(folder, "VBH", None, extract)
    assert code == compare.EXIT_PASS, report


def test_h8_4_dg3_sha_is_asserted(tmp_path, monkeypatch, two_l1_keys) -> None:
    monkeypatch.setattr(h8, "run_r79_judge", _judge_stub())
    keys_file, l1_run = _l1_files(tmp_path, "VBJ")
    code, report = _dg3_judge_main(tmp_path, "VBJ", keys_file, l1_run,
                                   extra=("--dg3-sha256", "0" * 64))
    assert code == compare.EXIT_NOT_JUDGEABLE
    assert any("--dg3" in text for text in report["not_judgeable"])


def test_h8_4_5_l1_hash_record(tmp_path) -> None:
    def l1(name, hashes):
        path = tmp_path / name
        path.write_text(json.dumps({"results": [
            {"harness": "g6", "inner": str(index), "base": {"commands_sha256": value}}
            for index, value in enumerate(hashes)]}), encoding="utf-8")
        return path

    out = tmp_path / "record.json"
    code = tjr.main(["l1-hash-record", "--vbj-l1", str(l1("a.json", ["x", "y", "z"])),
                     "--vbj0-l1", str(l1("b.json", ["x", "q", "z"])), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_PASS, report
    assert (report["pairs"], report["same_command_hash"], report["other_command_hash"]) == (
        3, 2, 1)
    code = tjr.main(["l1-hash-record", "--vbj-l1", str(l1("c.json", ["x"])),
                     "--vbj0-l1", str(l1("d.json", ["x", "y"])),
                     "--out", str(tmp_path / "other.json")])
    assert code == compare.EXIT_NOT_JUDGEABLE  # a pair on one side only


def test_h8_rejudge_constants() -> None:
    """4a-8 6.2 3 / 7, typed from the document."""
    assert rejudge.DG3_VBJ0_SHA256.startswith("c1201b2d160dc2fe")
    assert rejudge.DG3_VBJ_SHA256.startswith("603e4b815d8abc11")
    assert rejudge.DG3_VBH_SHA256.startswith("1cf7f86691163267")
    assert rejudge.RUN_COMMIT_78FD5D2D.startswith("78fd5d2d")


# --- 6.1: the import closure -------------------------------------------------------------------

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _synthetic_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _write(repo / "04_scripts" / "a" / "runner.py",
           "import helper\nfrom pkg import mod\nRUNNER = 'extra_runner.py'\n"
           "def f():\n    import lazy\n")
    _write(repo / "04_scripts" / "a" / "helper.py", "import json\n")
    _write(repo / "04_scripts" / "b" / "lazy.py", "")
    _write(repo / "05_tests" / "unit" / "extra_runner.py", "")
    _write(repo / "03_src" / "pkg" / "__init__.py", "")
    _write(repo / "03_src" / "pkg" / "mod.py", "from . import sub\n")
    _write(repo / "03_src" / "pkg" / "sub.py", "")
    _write(repo / "04_scripts" / "a" / "judge.py", "import helper\n")
    return repo


def test_6_1_closure_follows_imports_and_py_literals(tmp_path) -> None:
    repo = _synthetic_repo(tmp_path)
    found = closure.import_closure(repo, repo / "04_scripts" / "a" / "runner.py")
    assert set(found.files) == {
        "04_scripts/a/runner.py", "04_scripts/a/helper.py", "04_scripts/b/lazy.py",
        "05_tests/unit/extra_runner.py", "03_src/pkg/__init__.py", "03_src/pkg/mod.py",
        "03_src/pkg/sub.py"}
    assert "04_scripts/a/judge.py" not in found.files


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.mark.parametrize(("changed", "expected"), [
    ("04_scripts/a/judge.py", closure.EXIT_DISJOINT),
    ("03_src/pkg/sub.py", closure.EXIT_MEETS),
])
def test_6_1_closure_against_a_commit_range(tmp_path, changed, expected) -> None:
    repo = _synthetic_repo(tmp_path)
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base")
    _write(repo / changed, "# changed\n")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-am", "fix")
    out = tmp_path / "closure.json"
    code = closure.main(["--repo", str(repo), "--entry", "04_scripts/a/runner.py",
                         "--base", "HEAD~1", "--head", "HEAD", "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == expected, report
    assert report["meeting"] == ([] if expected == closure.EXIT_DISJOINT else [changed])


def test_6_1_bad_revision_is_an_input_error(tmp_path) -> None:
    repo = _synthetic_repo(tmp_path)
    _git(repo, "init", "-q")
    out = tmp_path / "closure.json"
    code = closure.main(["--repo", str(repo), "--entry", "04_scripts/a/runner.py",
                         "--base", "nope", "--head", "HEAD", "--out", str(out)])
    assert code == closure.EXIT_INPUT


def test_6_1_real_runner_closure_holds_the_runner_not_the_judge_tools() -> None:
    """The worktree's ``las_t3_dg3.py`` closure: the r79 runner and harness are in it; the
    judge tools this addendum changes are not (``jp3_fixed_inputs`` and ``j_p3_inputs`` are, so
    they stay unchanged)."""
    found = closure.import_closure(ROOT, COUPLED_DIR / "las_t3_dg3.py")
    names = {Path(path).name for path in found.files}
    assert {"r79_L3L4_final.py", "r79_sensor_screen.py", "harness_hydraulics.py",
            "run_v5.py", "jp3_fixed_inputs.py", "j_p3_inputs.py",
            "pre_las_preset_runner.py"} <= names
    assert not names & {"jp3_tjr_judge.py", "jp3_baseline_compare.py", "jp3_case_judge.py",
                        "jp3_dryrun_evidence.py", "jp3_rejudge_inputs.py",
                        "jp3_import_closure.py", "jp3_rerun_match.py"}
