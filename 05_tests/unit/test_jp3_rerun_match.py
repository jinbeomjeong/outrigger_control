"""Addendum 4a-6 G-4: ``jp3_rerun_match.py`` compares the reproducible values of steps (1) ..
(4a) of two attempts and reports only names (synthetic attempts)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_case_judge as case_judge  # noqa: E402
import jp3_rerun_match as match  # noqa: E402

CLASS_NAMES = np.array(["lock", "hold", "carry_ext", "carry_ret", "ext", "ret"])
CODES = {"p1": {"tool:base_judge_compare": 0, "tool:t12_selfcheck": 0},
         "dry": {"tool:summarize": 0}, "fpath": {"tool:case_f_path": 0},
         "cases": {"tool:x11": 0, "tool:baseline_compare": 3}}


def _evidence_record(truth: int, reads: int) -> dict:
    return {"hydraulics_record": {"rod_reading_truth_calls": truth, "two_pressure_reads": reads,
                                  "secret": 1}}


def _x11_npz(path: Path, gap_bar: float) -> None:
    t_s = np.round(np.arange(48.5, 49.25, 0.1), 9)
    classes = np.zeros((t_s.size, 4), dtype=np.int8)
    classes[np.isclose(t_s, 49.0), case_judge.FL] = 1
    used = np.full((t_s.size, 4), 120.0e5)
    truth = used.copy()
    truth[np.isclose(t_s, 49.0), case_judge.FL] += gap_bar * 1.0e5
    np.savez(path, jp3_t_s=t_s, jp3_class=classes, jp3_class_names=CLASS_NAMES,
             jp3_used_bound_Pa=used, jp3_p_tr_Pa=truth)


def _attempt(root: Path, *, judge_bytes: bytes = b"judge", truth: int = 3,
             harness: str = "h" * 64, gap_bar: float = 10.674, codes=None) -> Path:
    """A runs root with p1 / dry / fpath done and cases stopped (the b51ed6e1 layout)."""
    codes = codes or CODES
    for step, marker in (("p1", "done"), ("dry", "done"), ("fpath", "done"), ("cases", "stop")):
        folder = root / f"{step}_a1"
        folder.mkdir(parents=True)
        (folder / "step_record.json").write_text(json.dumps({"codes": codes[step]}),
                                                 encoding="utf-8")
        (root / f"{step}.{marker}").write_text(
            json.dumps({"folder": f"C:\\elsewhere\\{step}_a1", "codes": codes[step]}),
            encoding="utf-8")
    p1 = root / "p1_a1"
    (p1 / "h6_base_judge.json").write_bytes(judge_bytes)
    (p1 / "h6_base_judge_L1_reference.json").write_bytes(b"l1")
    dry = root / "dry_a1"
    for name in match.DRY_EVENT_FILES:
        (dry / name).write_text(json.dumps(_evidence_record(truth, 3)) + "\n", encoding="utf-8")
    for name in match.DRY_R79_FILES:
        (dry / name).write_text(json.dumps({"meta": {}, "results": [_evidence_record(0, 3)]}),
                                encoding="utf-8")
    rows = [{"job": {"offset_s": offset}, "harness_commands_sha256": harness}
            for offset in (0.0, 0.025, 0.05)]
    (root / "fpath_a1" / match.FPATH_ROWS).write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    cases = root / "cases_a1"
    row = {"job": {"setting": "LSJ4_X11"}, "commands_sha256": "c" * 64,
           "t4h_file": "R12_LSJ4_X11.npz"}
    (cases / match.X11_ROWS).write_text(json.dumps(row) + "\n", encoding="utf-8")
    (cases / "lsj4_x11_t4h").mkdir()
    _x11_npz(cases / "lsj4_x11_t4h" / row["t4h_file"], gap_bar)
    return root


def _run(tmp_path: Path, new_root: Path, *extra: str) -> tuple[int, dict]:
    old = _attempt(tmp_path / "old")
    out = tmp_path / f"report_{len(list(tmp_path.glob('report_*')))}.json"
    code = match.main(["--old", str(old), "--new", str(new_root), "--out", str(out), *extra])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_same_attempts(tmp_path) -> None:
    code, report = _run(tmp_path, _attempt(tmp_path / "new"))
    assert code == 0 and report["status"] == "same"
    assert set(report["items"]) == {"p1", "dry", "fpath", "x11"}


@pytest.mark.parametrize(("change", "item", "name"), [
    ({"judge_bytes": b"other"}, "p1", "sha256 h6_base_judge.json"),
    ({"truth": 4}, "dry", "evidence event_VBJ.jsonl"),
    ({"harness": "e" * 64}, "fpath", "harness_commands_sha256 offset 0.0"),
    ({"gap_bar": 10.675}, "x11", "FL 49.0 s gap_bar"),
    ({"codes": {**CODES, "fpath": {"tool:case_f_path": 1}}}, "fpath",
     "code tool:case_f_path"),
])
def test_a_differing_value_is_named_not_written(tmp_path, change, item, name) -> None:
    code, report = _run(tmp_path, _attempt(tmp_path / "new", **change))
    assert code == 1
    assert report["items"][item]["status"] == "differs"
    assert name in report["items"][item]["differing"]
    text = json.dumps(report)
    assert "other" not in text and "10.675" not in text and "e" * 64 not in text


def test_a_missing_input_is_exit_2(tmp_path) -> None:
    new = _attempt(tmp_path / "new")
    (new / "dry_a1" / "r79_VBH.json").unlink()
    code, report = _run(tmp_path, new)
    assert code == 2 and report["items"]["dry"]["status"] == "missing"


def test_a_running_step_by_folder_and_codes(tmp_path) -> None:
    new = _attempt(tmp_path / "new")
    codes = tmp_path / "codes.json"
    codes.write_text(json.dumps(CODES["cases"]), encoding="utf-8")
    code, report = _run(tmp_path, tmp_path / "no_markers", "--items", "x11", "--new-folder",
                        str(new / "cases_a1"), "--new-codes", str(codes))
    assert code == 0 and list(report["items"]) == ["x11"]
    with pytest.raises(SystemExit):
        match.main(["--old", "a", "--new", "b", "--out", str(tmp_path / "x.json"),
                    "--new-folder", "f"])  # without --new-codes
