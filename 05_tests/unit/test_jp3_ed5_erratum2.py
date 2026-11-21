"""436.9 edition 5 erratum 2 (``jp3_remedy_spec_v5_erratum2.md``): the 12b L1 key file (2-1),
the probe record form read by the 12b seed scan (2-3) and the extra fixed-list entries."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import j_p3_inputs as inputs  # noqa: E402
import jp3_12b_judge as judge  # noqa: E402
import jp3_12b_l1_keys as l1  # noqa: E402
import jp3_12b_plan as plan  # noqa: E402
import jp3_rerun_match as rerun  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402


def _noise(path: Path, *, drop_l1: str | None = None) -> str:
    """A case source: 167 L2 cases over two seeds, their L1 lines at s0; cases 0 and 1 share
    (harness, inner) with cases 100 and 101 (another index)."""
    cases = [f"g6|{index}|x{index % 100}|top|Fs0" for index in range(167)]
    results = []
    for seed in range(2):
        results += [{"key": f"cand=current#L2|s{seed}|{case}", "level": "L2"} for case in cases]
    results += [{"key": f"cand=current#L1|s0|{case}", "level": "L1"} for case in cases
                if case != drop_l1]
    path.write_text(json.dumps({"results": results}), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_l1_keys_one_per_harness_inner_in_first_order(tmp_path) -> None:
    noise = tmp_path / "noise.json"
    sha = _noise(noise)
    out = tmp_path / "l1_keys.txt"
    record = l1.write_l1_keys(noise, out, noise_sha256=sha)
    keys = out.read_bytes().decode("utf-8").split("\n")
    assert keys[-1] == "" and record["keys"] == len(keys) - 1 == 100  # x0 .. x99
    assert keys[:2] == ["L1|s0|g6|0|x0|top|Fs0", "L1|s0|g6|1|x1|top|Fs0"]
    assert "L1|s0|g6|100|x0|top|Fs0" not in keys  # the later case of the same inner
    assert record["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    with pytest.raises(plan.NotUsable, match="exists"):
        l1.write_l1_keys(noise, out, noise_sha256=sha)


def test_l1_keys_refusals(tmp_path) -> None:
    noise = tmp_path / "noise.json"
    sha = _noise(noise, drop_l1="g6|5|x5|top|Fs0")
    with pytest.raises(plan.NotUsable, match="no L1 job"):
        l1.write_l1_keys(noise, tmp_path / "a.txt", noise_sha256=sha)
    with pytest.raises(plan.NotUsable, match="--noise"):
        l1.write_l1_keys(noise, tmp_path / "b.txt", noise_sha256="0" * 64)
    assert not (tmp_path / "a.txt").exists()


def test_l1_keys_main_in_another_folder(tmp_path, monkeypatch, capsys) -> None:
    noise = tmp_path / "in" / "noise.json"
    noise.parent.mkdir()
    sha = _noise(noise)
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setattr(l1.write_l1_keys, "__defaults__", (sha,))
    assert l1.main(["--noise", str(noise), "--out", str(tmp_path / "out" / "k.txt")]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["keys"] == 100
    assert l1.main(["--noise", str(noise), "--out", str(tmp_path / "out" / "k.txt")]) == 2


def _l1_run(path: Path, hashes: dict[str, str]) -> Path:
    path.write_text(json.dumps({"results": [
        {"key": f"cand=current#{key}", "level": "L1", "commands_sha256": sha}
        for key, sha in hashes.items()]}), encoding="utf-8")
    return path


def test_l1_overlap_counts_same_and_differing_hashes(tmp_path, monkeypatch, capsys) -> None:
    """2-1 (audit warning 5): a record of the keys both L1 references hold."""
    a, b = "a" * 64, "b" * 64
    run_12b = _l1_run(tmp_path / "12b.json", {"L1|s0|g6|0|x": a, "L1|s0|g6|1|y": a,
                                              "L1|s0|ref|0|z": a})
    run_12a = _l1_run(tmp_path / "12a.json", {"L1|s0|g6|0|x": a, "L1|s0|g6|1|y": b,
                                              "L1|s0|g8|0|w": a})
    record = judge.l1_overlap({"VBJ": (run_12b, run_12a)})["VBJ"]
    assert (record["common_keys"], record["same_hash"], record["differing_hash"]) == (2, 1, 1)
    assert record["differing_keys"] == ["L1|s0|g6|1|y"]
    assert (record["only_12b"], record["only_12a"]) == (1, 1)
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "overlap.json"
    assert judge.main(["l1-overlap", "--pair", f"VBJ0={run_12b},{run_12a}", "--out",
                       str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["by_setting"]["VBJ0"]["common_keys"] == 2
    assert judge.main(["l1-overlap", "--pair", f"VB={run_12b},{run_12a}", "--out",
                       str(tmp_path / "bad.json")]) == 2


def test_l1_reference_runs_are_no_judged_input(tmp_path) -> None:
    """2-1: an L1 reference line in J-P3 rows is a setting defect; an L1 reference file is no
    T-JR-12 input."""
    check = {"rule_revision": 6, "jp3a_breach_reads": [0] * 4,
             "jp3b_breach_over_tol_reads": [0] * 4, "jp3c_breach_reads": [0] * 4}
    row = {"p3_expected": True, inputs.RULE_KEY: inputs.P3_RULE, inputs.REVISION_KEY: 6,
           "extend_bound_check": check, "setting": "VBJ"}
    clean = inputs.j_p3_over_rows([dict(row)])
    with_l1 = inputs.j_p3_over_rows([dict(row), {**row, "key": "cand=current#L1|s0|g6|0|x",
                                                 "level": "L1"}])
    assert clean["l1_reference_runs"] == 0  # (this synthetic row has other defects too)
    assert with_l1["l1_reference_runs"] == 1 and with_l1["status"] == "setting_defect"
    l1_file = _l1_run(tmp_path / "l1.json", {"L1|s0|g6|0|x": "a" * 64})
    dg3 = tmp_path / "dg3.json"
    dg3.write_text(json.dumps({"results": [{"key": "L2|s0|g6|0|x", "level": "L2"},
                                           {"key": "L1|s0|g6|0|x", "level": "L1"}]}),
                   encoding="utf-8")
    assert tjr.t12_file_defects(dg3, l1_file)[0].startswith("--new")
    assert tjr.t12_file_defects(l1_file, dg3)[0].startswith("--base")
    other = tmp_path / "dg3b.json"
    other.write_text(json.dumps({"results": [{"key": "L2|s1|g6|0|x", "level": "L2"}]}),
                     encoding="utf-8")
    assert tjr.t12_file_defects(dg3, other) == []


def _p1_folder(folder: Path, runs: list[dict], extract: list[dict]) -> Path:
    folder.mkdir(parents=True)
    (folder / "h6_base_judge.json").write_text(json.dumps(
        {"table": [{"group": "g6"}], "reference": [], "runs": runs, "unmatched": [],
         "errors": []}), encoding="utf-8")
    (folder / "h6_base_judge_L1_reference.json").write_text(json.dumps(
        {"meta": {"x": 1}, "results": extract}), encoding="utf-8")
    return folder


def test_p1_content_match_sorts_and_compares_the_judge_parts(tmp_path) -> None:
    """2-4 (audit warning 4): when the import closure meets a changed file, the P-1 judge parts
    are compared sorted (another order is the same; another grade differs)."""
    runs = [{"key": "a", "pass": True}, {"key": "b", "pass": False}]
    extract = [{"key": "L1|s0|g6|0|x"}, {"key": "L1|s0|g6|1|y"}]
    codes = {"tool:base_judge_compare": 0, "tool:t12_selfcheck": 0}
    old = _p1_folder(tmp_path / "old" / "p1_a1", runs, extract)
    same = _p1_folder(tmp_path / "new" / "p1_a1", list(reversed(runs)), list(reversed(extract)))
    other = _p1_folder(tmp_path / "other" / "p1_a1", [runs[0], {"key": "b", "pass": True}],
                       extract)
    report, code = rerun.compare_items([rerun.Side(old.parent, old, codes)],
                                       rerun.Side(same.parent, same, codes), ["p1_content"])
    assert code == rerun.EXIT_SAME and report["items"]["p1_content"]["status"] == "same"
    report, code = rerun.compare_items([rerun.Side(old.parent, old, codes)],
                                       rerun.Side(other.parent, other, codes), ["p1_content"])
    assert code == rerun.EXIT_DIFFERS
    assert report["items"]["p1_content"]["differing"] == ["h6_base_judge.json runs"]


def test_grade_input_problems_names_each_defect(tmp_path) -> None:
    """Audit F-1: the grade input defects are listed (a record), one per arm."""
    good = tmp_path / "g.json"
    good.write_text(json.dumps({"runs": []}), encoding="utf-8")
    sha = hashlib.sha256(good.read_bytes()).hexdigest()
    broken = tmp_path / "b.json"
    broken.write_text("[1]", encoding="utf-8")
    problems = judge.grade_input_problems({
        "vbk0": (None, None), "vbk": (good, "0" * 64)})
    assert problems[0].startswith("vbk0: no grade-judge file") and "sha256" in problems[1]
    assert judge.grade_input_problems({"vbk0": (good, sha)}) == []
    assert "no r79 judge output" in judge.grade_input_problems(
        {"vbk": (broken, hashlib.sha256(broken.read_bytes()).hexdigest())})[0]


def test_probe_record_form_is_read_by_the_12b_scan(tmp_path) -> None:
    """2-3: a probe line ``{"key": ..., "setting": ...}`` under 06_analysis is an r79 key of the
    12b base scan."""
    probes = tmp_path / "02_control" / "j_p3_cause" / "ed5_design" / "probes"
    probes.mkdir(parents=True)
    (probes / "probes_ed5.json").write_text(json.dumps({"results": [
        {"key": "L2|s30|ref|0|rigid|B|0,0", "setting": "VBJ", "commit": "8a3c48c7",
         "purpose": "unit tests", "output": "none"}]}, indent=1), encoding="utf-8")
    scan = plan.scan_r79_keys(tmp_path)
    assert scan.keys == {"L2|s30|ref|0|rigid|B|0,0"} and scan.seed_max == 30
