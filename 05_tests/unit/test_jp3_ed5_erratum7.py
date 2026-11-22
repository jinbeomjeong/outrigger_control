"""436.9 J-P3 edition 5 erratum 7 (``jp3_remedy_spec_v5_erratum7.md``, sealed ``38fdc574``)
7-4: the cells of the 6-6 coverage table (``ed5_design/junit/coverage_6_6_*.md``) no other
test fills - record items that must leave the status unchanged, and exit codes through
``main`` - for ``jp3_tjr_judge records`` (T-JR-13 / T-JR-15), ``jp3_case_judge`` (x11, case-f)
and ``jp3_p5_fixed_values p54`` (P5-4). Each test asserts one exact exit code and every
problem class. Synthetic inputs of the edition 5 form (the helpers of the edition 4a tests);
no edition 5 run output is read.
"""

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

import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_p5_fixed_values as p5  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import (  # noqa: E402
    GOOD_SEED_ROWS,
    REPLAY_REPORTS,
    T4H_NAMES,
    _case_f_rows,
    _dg3_document,
    _grid,
    _lock_row,
    h6_keys,
    valid_lock_rows,
)
from test_jp3_judge_main_e2e import (  # noqa: E402
    _baseline,
    _case_row,
    _sha,
    _t4h_folder,
    _write_json,
    _write_rows,
    _x11_npz,
)


@pytest.fixture
def elsewhere(tmp_path, monkeypatch) -> Path:
    folder = tmp_path / "elsewhere"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


def _classes(report: dict) -> dict:
    return {kind: report.get(kind) for kind in ("failures", "setting_defects", "not_judgeable")}


# --- jp3_tjr_judge records ----------------------------------------------------------------------

def _records_main(tmp_path: Path, monkeypatch, replays: list[dict],
                  lock_rows: list[dict]) -> tuple[int, dict]:
    """``records`` through ``main`` (the 4a-5 E-1 call), the fixed name lists patched."""
    folder = tmp_path / "records"
    folder.mkdir()
    paths = []
    for index, document in enumerate(replays):
        paths.append(_write_json(folder / f"replay_{index}.json", document))
    for setting in tjr.T_JR_14_BUNDLES:
        _write_json(folder / f"dg3_{setting}.json", _dg3_document(setting=setting))
    rows = _write_rows(folder / "rows.jsonl", lock_rows)
    monkeypatch.setattr(tjr, "t4h_names_of", lambda sums: (T4H_NAMES, []))
    monkeypatch.setattr(tjr, "h6_keys_of", lambda path: (h6_keys(), []))
    out = folder / "out.json"
    code = tjr.main(["records", "--out", str(out), "--replay", *map(str, paths),
                     "--dg3", str(folder / "dg3_VBH.json"), str(folder / "dg3_VBJ.json"),
                     "--lock-rows", str(rows), "--t4h-sums", "unused", "--h6", "unused"])
    return code, json.loads(out.read_text(encoding="utf-8"))


def _replays(**changes) -> list[dict]:
    reports = json.loads(json.dumps(REPLAY_REPORTS))
    for report in reports:
        report.update(changes)
    return reports


def test_records_main_passes_on_the_valid_set(tmp_path, monkeypatch, elsewhere) -> None:
    code, report = _records_main(tmp_path, monkeypatch, _replays(), valid_lock_rows())
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}


def test_records_t_jr_13_replay_jp3_and_runs_over_are_records(tmp_path, monkeypatch,
                                                              elsewhere) -> None:
    """T-JR-13: the replays' own J-P3 status and ``runs_over`` are records (4a-5 1: no
    threshold) - an H-7 replay J-P3 and runs over leave exit 0 and every class empty."""
    replays = _replays(runs_over=9, **{"J-P3": {"status": "H-7"}})
    code, report = _records_main(tmp_path, monkeypatch, replays, valid_lock_rows())
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    assert [row["J-P3"] for row in report["T-JR-13"]] == ["H-7", "H-7"]
    assert [row["runs_over"] for row in report["T-JR-13"]] == [9, 9]


def test_records_t_jr_15_vbh_rows_are_records(tmp_path, monkeypatch, elsewhere) -> None:
    """T-JR-15: a VBH row's relock count is a record (only VBJ / LSJ rows are judged)."""
    rows = valid_lock_rows() + [_lock_row(GOOD_SEED_ROWS, setting="VBH", relocks=3)]
    code, report = _records_main(tmp_path, monkeypatch, _replays(), rows)
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    assert report["T-JR-15"]["judged_rows"] == len(valid_lock_rows())


def test_records_t_jr_15_vbj_relock_fails_through_main(tmp_path, monkeypatch, elsewhere) -> None:
    rows = valid_lock_rows()
    rows[0]["hydraulics_record"]["relock_step_over_1bar_count"] = 1
    code, report = _records_main(tmp_path, monkeypatch, _replays(), rows)
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert report["setting_defects"] == [] and report["not_judgeable"] == []
    assert len(report["failures"]) == 1
    assert report["failures"][0].endswith("relock_step_over_1bar_count 1")


def test_records_t_jr_15_missing_relock_is_not_judgeable_through_main(tmp_path, monkeypatch,
                                                                      elsewhere) -> None:
    rows = valid_lock_rows()
    del rows[0]["hydraulics_record"]["relock_step_over_1bar_count"]
    code, report = _records_main(tmp_path, monkeypatch, _replays(), rows)
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "not_judgeable"
    assert report["failures"] == [] and report["setting_defects"] == []
    assert len(report["not_judgeable"]) == 1
    assert report["not_judgeable"][0].endswith("relock_step_over_1bar_count None")


# --- jp3_case_judge x11 / case-f ----------------------------------------------------------------

def _x11_main(tmp_path: Path, monkeypatch, over: list[int], drop_column: str | None = None
              ) -> tuple[int, dict]:
    command_hash = case_judge.X11_BASELINE_HASH_PREFIX + "0" * 52
    lsj4 = {**_case_row("LSJ4"), "commands_sha256": command_hash}
    baseline = _baseline(tmp_path / "baseline", monkeypatch, {"j9_cases.jsonl": [lsj4]})
    row = {**_case_row("LSJ4_X11"), "commands_sha256": command_hash,
           "hydraulic_options": {"rod_reading_truth": True},
           "hydraulics_record": {"rod_reading_truth_calls": 5, "two_pressure_reads": 5,
                                 "extend_bound_check": {
                                     "rule_revision": 5, **case_judge.X11_IDENTITY,
                                     "jp3b_breach_over_tol_reads": over}}}
    both = _write_rows(tmp_path / "run" / "lsj4_x11.jsonl", [row])
    npz = _t4h_folder(both) / row["t4h_file"]
    _x11_npz(npz)
    if drop_column is not None:
        with np.load(npz, allow_pickle=False) as data:
            arrays = {name: data[name] for name in data.files if name != drop_column}
        np.savez(npz, **arrays)
    out = tmp_path / "x11.json"
    code = case_judge.main(["x11", "--both", str(both), "--baseline", str(baseline),
                            "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_x11_main_pass_failure_and_not_judgeable(tmp_path, monkeypatch, elsewhere) -> None:
    """P4-5a through ``main``: FL 1 over-tolerance read passes (0); none fails (1); a T4h
    without ``jp3_p_tr_Pa`` is not judgeable (2)."""
    code, report = _x11_main(tmp_path / "a", monkeypatch, [1, 0, 0, 0])
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    code, report = _x11_main(tmp_path / "b", monkeypatch, [0, 0, 0, 0])
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert _classes(report) == {"setting_defects": [], "not_judgeable": [], "failures": [
        "P4-5a J-P3b over-tolerance reads are not 1 on FL"]}
    code, report = _x11_main(tmp_path / "c", monkeypatch, [1, 0, 0, 0], drop_column="jp3_p_tr_Pa")
    assert code == compare.EXIT_NOT_JUDGEABLE and report["status"] == "not_judgeable"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": [
        "P4-5a T4h without ['jp3_p_tr_Pa']"]}


def _case_f_main(tmp_path: Path, monkeypatch, rows: list[dict]) -> tuple[int, dict]:
    rows_file = _write_rows(tmp_path / "run" / "j9_case_f.jsonl", rows)
    grid_file = _write_json(tmp_path / "stored" / "grid_r67_top.json", _grid())
    monkeypatch.setattr(case_judge, "GRID_SHA256", _sha(grid_file))
    out = tmp_path / "case_f.json"
    code = case_judge.main(["case-f", "--rows", str(rows_file), "--grid", str(grid_file),
                            "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_case_f_records_do_not_change_the_status(tmp_path, monkeypatch, elsewhere) -> None:
    """case-f: the A LS rows' bound check and the LSH rows' J-P3 keys are records (F-B judges
    VBH's J-P3a only) - exit 0 with every class empty; VBH's J-P3a fails (exit 1)."""
    rows = _case_f_rows()
    by_setting = {row["job"]["setting"]: row for row in rows}
    by_setting["LS2"]["hydraulics_record"]["extend_bound_check"]["breach_reads"] = [5, 5, 5, 5]
    by_setting["LSH2"]["hydraulics_record"]["extend_bound_check"]["jp3a_breach_reads"] = [
        1, 0, 0, 0]
    code, report = _case_f_main(tmp_path / "a", monkeypatch, rows)
    assert code == compare.EXIT_PASS and report["status"] == "pass"
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    assert report["A_LS_record"]["LS2"]["breach_reads"] == [5, 5, 5, 5]
    rows = _case_f_rows()
    next(row for row in rows if row["job"]["setting"] == "VBH")["hydraulics_record"][
        "extend_bound_check"]["jp3a_breach_reads"] = [0, 1, 0, 0]
    code, report = _case_f_main(tmp_path / "b", monkeypatch, rows)
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert _classes(report) == {"setting_defects": [], "not_judgeable": [],
                                "failures": ["F-B VBH J-P3a reads > 0"]}


# --- jp3_j9main_judge LS conditions -------------------------------------------------------------

def test_j9main_l_d_is_a_record_and_l_b_l_e_fail() -> None:
    """j9_main LS conditions (2-7.1): L-d is a record (D-16) - any content leaves the status
    pass; L-b and an LS J11 stop (L-e, in ``stops``) are failures."""
    from test_jp3_j9main import _status_of

    assert _status_of(**{"L-d": {"LS1": {"j6_worse": True, "rows": 3}}}) == "pass"
    assert _status_of(**{"L-b": [{"setting": "LS2", "item": "J3"}]}) == "failed"
    assert _status_of(stops=[{"setting": "LS3", "item": "L-e"}]) == "failed"


# --- jp3_p5_fixed_values p54 (P5-4, a record) ---------------------------------------------------

def _p54_main(folder: Path, out: Path, monkeypatch, dominated: int) -> int:
    monkeypatch.setattr(p5, "p54_record", lambda path, revision: {
        "file": path.name, "revision": revision,
        "dominated_reads": dominated if revision == p5.REVISIONS[0] else 0,
        "stretches": 0, "max_over_kN": [1.0]})
    monkeypatch.setattr(p5, "proxy_disclosure", lambda: {"judged": False})
    return p5.main(["p54", "--t4h", str(folder), "--out", str(out)])


def test_p54_main_written_not_usable_and_record(tmp_path, monkeypatch, capsys) -> None:
    """P5-4 is a record: written (0) whatever the reduction; an existing ``--out`` or no T4h
    input is not usable (2); it has no failure exit."""
    folder = tmp_path / "VBH_t4h"
    folder.mkdir()
    for index in range(2):
        (folder / f"k{index}.npz").write_bytes(bytes([index]) * 8)
    out = tmp_path / "p54.json"
    assert _p54_main(folder, out, monkeypatch, dominated=1000) == p5.EXIT_WRITTEN
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["files"] == 2 and report["dominated_reduction"] == pytest.approx(1.0)
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "written"
    assert _p54_main(folder, out, monkeypatch, dominated=1) == p5.EXIT_NOT_USABLE
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "not_usable"
    empty = tmp_path / "empty_t4h"
    empty.mkdir()
    assert _p54_main(empty, tmp_path / "p54_empty.json", monkeypatch, dominated=1) == (
        p5.EXIT_NOT_USABLE)
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["reason"] == "no input row"
