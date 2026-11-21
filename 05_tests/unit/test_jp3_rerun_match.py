"""Addenda 4a-6 G-4 and 4a-7 2: ``jp3_rerun_match.py`` compares the reproducible values of
steps (1) .. (4b) of two attempts and reports only names (synthetic attempts)."""

from __future__ import annotations

import hashlib
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
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_rerun_match as match  # noqa: E402
from test_jp3_addendum_4a2 import _case_f_rows, _grid  # noqa: E402

CLASS_NAMES = np.array(["lock", "hold", "carry_ext", "carry_ret", "ext", "ret"])
CODES = {"p1": {"tool:base_judge_compare": 0, "tool:t12_selfcheck": 0},
         "dry": {"tool:summarize": 0}, "fpath": {"tool:case_f_path": 0},
         "cases": {"tool:x11": 0, "tool:baseline_compare": 0}, "casef": {"tool:case_f": 0}}
CASE_ROWS = {"j9_cases.jsonl": (("VBJ", True), ("VB", False)), "cd.jsonl": (("LSJ1", True),)}
"""Synthetic step 4a rows: (setting, revision 5) per ``jp3_baseline_compare`` row file."""
GRID_TEXT = json.dumps(_grid())


@pytest.fixture(autouse=True)
def synthetic_grid_sha(monkeypatch) -> None:
    """The fixed grid sha of the synthetic ``case-f`` grid input."""
    sha = hashlib.sha256(GRID_TEXT.encode("utf-8")).hexdigest()
    monkeypatch.setattr(fixed, "GRID_SHA256", sha)


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


def _case_row(setting: str, is_revision_5: bool) -> dict:
    check = ({"rule_revision": 5, **{key: [0] * 4 for key in match.P4_3A_KEYS},
              "retract_tracker_dominated_reads": [0] * 4} if is_revision_5
             else {"rule_revision": 4})
    return {"job": {"case": "R12", "eps": 0.0, "setting": setting}, "commands_sha256": "a" * 64,
            "hydraulics_record": {"extend_bound_check": check, "relock_step_over_1bar_count": 0,
                                  "p1_retract_seed_count": 9,
                                  "p1_retract_seed_step_max_bar": 1.25}}


def _write_lines(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _write_cases_ae(cases: Path) -> None:
    pairs = []
    for name, settings in CASE_ROWS.items():
        _write_lines(cases / name, [_case_row(*setting) for setting in settings])
        pairs += [{"setting": setting, "row_file": name, "commands_sha256": "a" * 12,
                   "reads": {"lowered_reads": 0, "unexplained_raised_reads": 0,
                             "bad_class_changes": 0, "has_trace": True},
                   "seed": {"over_1N_rows": 0} if is_revision_5 else {}}
                  for setting, is_revision_5 in settings]
    (cases / "judge").mkdir()
    (cases / match.CASE_REPORT).write_text(json.dumps({"pairs": pairs, "status": "pass"}),
                                           encoding="utf-8")


def _write_case_f(root: Path, casef: Path) -> None:
    _write_lines(casef / match.CASE_F_ROWS, _case_f_rows())
    grid = root / "grid_r67_top.json"
    grid.write_text(GRID_TEXT, encoding="utf-8")
    (casef / "judge").mkdir()
    inputs = [{"path": str(casef / match.CASE_F_ROWS), "sha256": "r" * 64},
              {"path": str(grid), "sha256": fixed.GRID_SHA256}]
    (casef / match.CASE_F_REPORT).write_text(json.dumps({"status": "pass", "inputs": inputs}),
                                             encoding="utf-8")


def _attempt(root: Path, *, judge_bytes: bytes = b"judge", truth: int = 3,
             harness: str = "h" * 64, gap_bar: float = 10.674, codes=None) -> Path:
    """A runs root with steps p1 .. casef done (the fa997f4c layout)."""
    codes = codes or CODES
    for step in CODES:
        folder = root / f"{step}_a1"
        folder.mkdir(parents=True)
        (folder / "step_record.json").write_text(json.dumps({"codes": codes[step]}),
                                                 encoding="utf-8")
        (root / f"{step}.done").write_text(
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
    _write_lines(root / "fpath_a1" / match.FPATH_ROWS, rows)
    cases = root / "cases_a1"
    row = {"job": {"setting": "LSJ4_X11"}, "commands_sha256": "c" * 64,
           "t4h_file": "R12_LSJ4_X11.npz"}
    _write_lines(cases / match.X11_ROWS, [row])
    (cases / "lsj4_x11_t4h").mkdir()
    _x11_npz(cases / "lsj4_x11_t4h" / row["t4h_file"], gap_bar)
    _write_cases_ae(cases)
    _write_case_f(root, root / "casef_a1")
    return root


def _run(tmp_path: Path, new_root: Path, *extra: str) -> tuple[int, dict]:
    old = _attempt(tmp_path / "old")
    out = tmp_path / f"report_{len(list(tmp_path.glob('report_*')))}.json"
    code = match.main(["--old", str(old), "--new", str(new_root), "--out", str(out), *extra])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_same_attempts(tmp_path) -> None:
    code, report = _run(tmp_path, _attempt(tmp_path / "new"))
    assert code == 0 and report["status"] == "same", report
    assert set(report["items"]) == {"p1", "dry", "fpath", "x11", "cases_ae", "casef"}
    for entry in report["items"].values():
        assert entry["compared"] and not entry["differing"]


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


def _edit_lines(path: Path, setting: str, edit) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    for row in rows:
        if row["job"]["setting"] == setting:
            edit(row)
    _write_lines(path, rows)


def _edit_json(path: Path, edit) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    edit(document)
    path.write_text(json.dumps(document), encoding="utf-8")


def _check(row: dict) -> dict:
    return row["hydraulics_record"]["extend_bound_check"]


def _pair(document: dict, setting: str) -> dict:
    return next(pair for pair in document["pairs"] if pair["setting"] == setting)


CASES_AE_ROWS, CASE_F_ROWS = f"cases_a1/{match.CASE_ROW_FILES[0]}", f"casef_a1/{match.CASE_F_ROWS}"
CASES_AE_CD = f"cases_a1/{match.CASE_ROW_FILES[1]}"
CASES_REPORT, CASE_F_REPORT = f"cases_a1/{match.CASE_REPORT}", f"casef_a1/{match.CASE_F_REPORT}"


@pytest.mark.parametrize(("path", "setting", "edit", "item", "name"), [
    # 4a-7 2.1 (4a) A .. E: one value at a time
    (CASES_AE_ROWS, "VBJ", lambda row: row.update(commands_sha256="e" * 64), "cases_ae",
     "commands_sha256"),
    (CASES_AE_ROWS, "VBJ", lambda row: _check(row).update(jp3a_breach_reads=[0, 1, 0, 0]),
     "cases_ae", "P4-3a jp3a_breach_reads sum"),
    (CASES_AE_CD, "LSJ1", lambda row: _check(row).update(
        jp3b_breach_over_tol_reads=[0, 0, 2, 0]), "cases_ae",
     "P4-3a jp3b_breach_over_tol_reads sum"),
    (CASES_AE_CD, "LSJ1", lambda row: _check(row).update(jp3c_breach_reads=[3, 0, 0, 0]),
     "cases_ae", "P4-3a jp3c_breach_reads sum"),
    (CASES_AE_ROWS, "VBJ", lambda row: row["hydraulics_record"].update(
        relock_step_over_1bar_count=1), "cases_ae", "P4-3a relock_step_over_1bar_count"),
    (CASES_AE_ROWS, "VBJ", lambda row: row["hydraulics_record"].update(
        p1_retract_seed_count=8), "cases_ae", "P4-4 p1_retract_seed_count"),
    (CASES_AE_CD, "LSJ1", lambda row: row["hydraulics_record"].update(
        p1_retract_seed_step_max_bar=1.5), "cases_ae", "P4-4 p1_retract_seed_step_max_bar"),
    (CASES_AE_ROWS, "VBJ", lambda row: _check(row).update(
        retract_tracker_dominated_reads=[0, 0, 0, 5]), "cases_ae",
     "P4-9 retract_tracker_dominated_reads sum"),
    (CASES_REPORT, None, lambda doc: _pair(doc, "VBJ")["reads"].update(lowered_reads=4),
     "cases_ae", "pair j9_cases.jsonl VBJ #1 P4-2 lowered_reads"),
    (CASES_REPORT, None, lambda doc: _pair(doc, "LSJ1")["reads"].update(
        unexplained_raised_reads=2), "cases_ae", "pair cd.jsonl LSJ1 #1 P4-2 "
                                                 "unexplained_raised_reads"),
    (CASES_REPORT, None, lambda doc: _pair(doc, "VB")["reads"].update(bad_class_changes=1),
     "cases_ae", "pair j9_cases.jsonl VB #1 P4-2 bad_class_changes"),
    (CASES_REPORT, None, lambda doc: _pair(doc, "VBJ")["seed"].update(over_1N_rows=1),
     "cases_ae", "pair j9_cases.jsonl VBJ #1 P4-4 over_1N_rows"),
    (CASES_REPORT, None, lambda doc: doc.update(status="failed"), "cases_ae",
     "baseline_compare status"),
    ("cases_a1/step_record.json", None, lambda doc: doc["codes"].update(
        {"tool:baseline_compare": 1}), "cases_ae", "code tool:baseline_compare"),
    # 4a-7 2.1 (4b) case F
    (CASE_F_ROWS, "LSJ3", lambda row: row.update(commands_sha256="e" * 64), "casef",
     "LSJ3 commands_sha256"),
    (CASE_F_ROWS, "VB", lambda row: row.update(harness_commands_sha256="e" * 64), "casef",
     "VB harness_commands_sha256"),
    (CASE_F_ROWS, "VB", lambda row: _check(row).update(min_gap_bar=[1.0, -0.8, 2.0, 3.0]),
     "casef", "F-A status"),
    (CASE_F_ROWS, "VBH", lambda row: _check(row).update(jp3a_breach_reads=[0, 1, 0, 0]),
     "casef", "F-B status"),
    (CASE_F_ROWS, "LSJ2", lambda row: row["hydraulics_record"].update(
        relock_step_over_1bar_count=1), "casef", "F-E status"),
    (CASE_F_REPORT, None, lambda doc: doc.update(status="failed"), "casef", "case_f status"),
    ("casef_a1/step_record.json", None, lambda doc: doc["codes"].update({"tool:case_f": 1}),
     "casef", "code tool:case_f"),
])
def test_4a7_items_one_value_at_a_time(tmp_path, path, setting, edit, item, name) -> None:
    """4a-7 5 H-3: each value of (4a) A .. E and (4b) changed alone gives exit 1, named only."""
    new = _attempt(tmp_path / "new")
    if setting is None:
        _edit_json(new / path, edit)
    else:
        _edit_lines(new / path, setting, edit)
    code, report = _run(tmp_path, new, "--items", item)
    entry = report["items"][item]
    assert (code, entry["status"]) == (1, "differs"), entry
    assert any(found.endswith(name) for found in entry["differing"]), entry["differing"]
    text = json.dumps(report)
    assert "e" * 64 not in text and "-0.8" not in text and "1.5" not in text


def test_two_earlier_attempts(tmp_path) -> None:
    """``--old`` twice: each attempt is compared (the run steps pass fa997f4c alone)."""
    first, second = _attempt(tmp_path / "b51ed6e1"), _attempt(tmp_path / "fa997f4c",
                                                              harness="e" * 64)
    new = _attempt(tmp_path / "new")
    out = tmp_path / "two.json"
    code = match.main(["--old", str(first), "--old", str(second), "--new", str(new),
                       "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1
    fpath = report["items"]["fpath"]
    assert fpath["by_old"]["b51ed6e1"]["status"] == "same"
    assert fpath["by_old"]["fa997f4c"]["status"] == "differs"
    assert fpath["status"] == "differs"
    assert report["items"]["p1"]["status"] == "same"
    assert report["old"] == [str(first), str(second)]


def _drop_case_row(root: Path) -> None:
    (root / CASES_AE_CD).write_text("", encoding="utf-8")


def _drop_case_f_row(root: Path) -> None:
    lines = (root / CASE_F_ROWS).read_text(encoding="utf-8").splitlines()
    (root / CASE_F_ROWS).write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")


@pytest.mark.parametrize(("change", "item"), [
    (lambda root: (root / "dry_a1" / "r79_VBH.json").unlink(), "dry"),
    (lambda root: (root / CASES_REPORT).unlink(), "cases_ae"),
    (lambda root: (root / CASE_F_REPORT).unlink(), "casef"),
    (_drop_case_row, "cases_ae"),  # another pair count
    (_drop_case_f_row, "casef"),  # 14 case F rows
    (lambda root: _edit_json(root / CASE_F_REPORT, lambda doc: doc.update(inputs=[])),
     "casef"),  # no fixed grid input
])
def test_a_missing_input_or_other_pair_count_is_exit_2(tmp_path, change, item) -> None:
    new = _attempt(tmp_path / "new")
    change(new)
    code, report = _run(tmp_path, new, "--items", item)
    assert code == 2 and report["items"][item]["status"] == "missing", report


@pytest.mark.parametrize(("item", "step"), [("x11", "cases"), ("cases_ae", "cases"),
                                            ("casef", "casef")])
def test_a_running_step_by_folder_and_codes(tmp_path, item, step) -> None:
    """The run steps call the match inside the running step (no marker, codes so far)."""
    new = _attempt(tmp_path / "new")
    codes = tmp_path / "codes.json"
    codes.write_text(json.dumps(CODES[step]), encoding="utf-8")
    code, report = _run(tmp_path, tmp_path / "no_markers", "--items", item, "--new-folder",
                        str(new / f"{step}_a1"), "--new-codes", str(codes))
    assert code == 0 and list(report["items"]) == [item]


def test_new_folder_needs_new_codes(tmp_path) -> None:
    with pytest.raises(SystemExit):
        match.main(["--old", "a", "--new", "b", "--out", str(tmp_path / "x.json"),
                    "--new-folder", "f"])  # without --new-codes
