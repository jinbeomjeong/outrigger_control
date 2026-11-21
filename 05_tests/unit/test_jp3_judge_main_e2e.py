"""End to end ``main`` of every J-P3 judge tool on inputs of the real output form (run_v5 rows
with a name-only ``t4h_file`` and ``<stem>_t4h/`` folders, r79 run files), run from another
working folder (j9 step 4a diagnosis 2026-11-21: ``jp3_baseline_compare`` read the new rows'
T4h from the CWD; the tests had given ``compare_reads`` direct paths only).

Synthetic data only; the fixed input sha constants are patched to the synthetic files.
"""

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

import h8_noise_judge_4368 as h8  # noqa: E402
import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_t8_rules as t8_rules  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import (  # noqa: E402
    REPLAY_REPORTS,
    T4H_NAMES,
    _case_f_rows,
    _dg3_document,
    _grid,
    valid_lock_rows,
)
from test_jp3_addendum_4a3 import (  # noqa: E402
    SELECTION,
    STORED_RECORD,
    _main_jsonl,
    _new_record,
    _path_grid,
    _path_rows,
    _summary_files,
)

CLASS_NAMES = np.array(["lock", "hold", "carry_ext", "carry_ret", "ext", "ret"])
BAR = 1.0e5


@pytest.fixture
def elsewhere(tmp_path, monkeypatch) -> Path:
    """The working folder of the run: none of the inputs lies in it."""
    folder = tmp_path / "elsewhere"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _write_json(path: Path, document) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _t4h_folder(rows_file: Path) -> Path:
    folder = rows_file.with_name(f"{rows_file.stem}_t4h")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _baseline(folder: Path, monkeypatch, files: dict[str, list[dict]], npz=None) -> Path:
    """A sealed-form baseline (``SHA256SUMS`` of every file, its sha patched as the fixed one)."""
    listed = []
    for name, rows in files.items():
        listed.append(_write_rows(folder / name, rows))
        t4h = _t4h_folder(folder / name)
        for row in rows:
            path = t4h / row["t4h_file"]
            (npz or (lambda p: np.savez(p, x=np.zeros(2))))(path)
            listed.append(path)
    lines = [f"{_sha(path)} *{path.relative_to(folder).as_posix()}" for path in listed]
    sums = folder / "SHA256SUMS"
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(compare, "BASELINE_SUMS_SHA256", _sha(sums))
    return folder


# --- jp3_baseline_compare -----------------------------------------------------------------------

def _case_row(setting: str, case: str = "R12") -> dict:
    """A run_v5 row: ``t4h_file`` is the name only (``run_v5.py`` writes ``path.name``)."""
    return {"job": {"case": case, "eps": 0.0, "offset_s": 0.0, "setting": setting},
            "commands_sha256": "a" * 64, "t4h_file": f"{case}_{setting}.npz",
            "hydraulics_record": {"extend_bound_check": {}, "rod_reading_truth_calls": 0,
                                  "two_pressure_reads": 4}}


def test_baseline_compare_finds_each_new_t4h_next_to_its_rows_file(tmp_path, monkeypatch,
                                                                    elsewhere) -> None:
    files = {"j9_cases.jsonl": [_case_row("VB"), _case_row("VBH")],
             "cd.jsonl": [_case_row("VBG4")]}
    baseline = _baseline(tmp_path / "baseline", monkeypatch, files)
    run = tmp_path / "run"
    news = []
    for name, rows in files.items():
        news.append(_write_rows(run / name, rows))
        for row in rows:  # other bytes than the baseline npz: the sha shows which file was read
            np.savez(_t4h_folder(run / name) / row["t4h_file"], x=np.ones(3))
    out = tmp_path / "report.json"
    code = compare.main([str(baseline), "--new", *map(str, news), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code != compare.EXIT_ERROR, report.get("error")
    expected = {}
    for name, rows in files.items():
        for row in rows:
            expected[row["job"]["setting"]] = _sha(_t4h_folder(run / name) / row["t4h_file"])
    found = {pair["setting"]: pair["new_t4h_sha256"] for pair in report["pairs"]}
    assert found == expected  # each new T4h read from its own rows file's _t4h folder


def test_read_new_rows_keeps_t4h_file_and_adds_the_path(tmp_path) -> None:
    rows_file = _write_rows(tmp_path / "x" / "cd.jsonl", [_case_row("VBG4")])
    rows = compare.read_new_rows([rows_file])
    assert rows[0]["t4h_file"] == "R12_VBG4.npz"
    assert Path(rows[0][compare.NEW_T4H_PATH_KEY]) == tmp_path / "x" / "cd_t4h" / "R12_VBG4.npz"


# --- jp3_case_judge x11, case-f, case-f-path ----------------------------------------------------

def _x11_npz(path: Path) -> None:
    t_s = np.round(np.arange(48.5, 49.25, 0.1), 9)
    classes = np.zeros((t_s.size, 4), dtype=np.int8)
    classes[np.isclose(t_s, 49.0), case_judge.FL] = 1  # hold
    used = np.full((t_s.size, 4), 120.0 * BAR)
    truth = used.copy()
    truth[np.isclose(t_s, 49.0), case_judge.FL] += case_judge.X11_GAP_BAR * BAR
    np.savez(path, jp3_t_s=t_s, jp3_class=classes, jp3_class_names=CLASS_NAMES,
             jp3_used_bound_Pa=used, jp3_p_tr_Pa=truth)


def test_x11_main(tmp_path, monkeypatch, elsewhere) -> None:
    command_hash = case_judge.X11_BASELINE_HASH_PREFIX + "0" * 52
    lsj4 = {**_case_row("LSJ4"), "commands_sha256": command_hash}
    baseline = _baseline(tmp_path / "baseline", monkeypatch, {"j9_cases.jsonl": [lsj4]})
    row = {**_case_row("LSJ4_X11"), "commands_sha256": command_hash,
           "hydraulic_options": {"rod_reading_truth": True},
           "hydraulics_record": {"rod_reading_truth_calls": 5, "two_pressure_reads": 5,
                                 "extend_bound_check": {
                                     "rule_revision": 5, **case_judge.X11_IDENTITY,
                                     "jp3b_breach_over_tol_reads": [1, 0, 0, 0]}}}
    both = _write_rows(tmp_path / "run" / "lsj4_x11.jsonl", [row])
    _x11_npz(_t4h_folder(both) / row["t4h_file"])
    out = tmp_path / "x11.json"
    code = case_judge.main(["x11", "--both", str(both), "--baseline", str(baseline),
                            "--out", str(out)])
    assert code == compare.EXIT_PASS, json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("command", "rows", "grid"), [
    ("case-f", _case_f_rows(), _grid()),
    ("case-f-path", _path_rows(_path_grid()), _path_grid()),
])
def test_case_f_mains(tmp_path, monkeypatch, elsewhere, command, rows, grid) -> None:
    rows_file = _write_rows(tmp_path / "run" / "j9_case_f.jsonl", rows)
    grid_file = _write_json(tmp_path / "stored" / "grid_r67_top.json", grid)
    monkeypatch.setattr(case_judge, "GRID_SHA256", _sha(grid_file))
    out = tmp_path / f"{command}.json"
    code = case_judge.main([command, "--rows", str(rows_file), "--grid", str(grid_file),
                            "--out", str(out)])
    assert code == compare.EXIT_PASS, json.loads(out.read_text(encoding="utf-8"))


# --- jp3_tjr_judge t8, t12, records ------------------------------------------------------------

def _meta_npz(path: Path, meta: dict) -> None:
    np.savez(path, meta_json=np.array(json.dumps(meta)))


def test_t8_main(tmp_path, monkeypatch, elsewhere) -> None:
    import run_v5

    (tmp_path / "stored").mkdir()
    main_jsonl = _main_jsonl(tmp_path / "stored" / "main.jsonl")
    monkeypatch.setattr(fixed, "MAIN_JSONL_SHA256", _sha(main_jsonl))
    jobs = run_v5.j9_t8_jobs(main_jsonl)
    hashes = {tjr._job_identity(job): f"{index:064d}" for index, job in enumerate(jobs)}
    stored_rows, rerun_rows = [], []
    for job in jobs:
        key = tjr._job_identity(job)
        name = f"{job['case']}_{job['setting']}.npz"
        line = {"job": job, "commands_sha256": hashes[key],
                "controller_tag": "final_C4G2_P3H_LAS_K1", "event_names": ["INFO_X"],
                "events": [[1.0, "INFO_X"]], "t4h_file": name, "hydraulics_record": _new_record()}
        rerun_rows.append(line)
        if job["setting"] == "VB":
            stored_rows.append({**line, "controller_tag": t8_rules.STORED_TAG,
                                "hydraulics_record": json.loads(json.dumps(STORED_RECORD))})
    stored = _write_rows(tmp_path / "stored" / "h10_reuse_rerun.jsonl", stored_rows)
    rerun = _write_rows(tmp_path / "run" / "j9_t8.jsonl", rerun_rows)
    monkeypatch.setattr(fixed, "H10_SHA256", _sha(stored))
    for row in stored_rows:
        _meta_npz(_t4h_folder(stored) / row["t4h_file"],
                  {"two_pressure_settings": {"extend_start_bound": {"revision": 4}}})
    for row in rerun_rows:
        if row["job"]["setting"] == "VBH":
            _meta_npz(_t4h_folder(rerun) / row["t4h_file"], {})
    out = tmp_path / "t8.json"
    code = tjr.main(["t8", "--stored", str(stored), "--rerun", str(rerun), "--main-jsonl",
                     str(main_jsonl), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_PASS, report
    assert report["T-JR-10"]["passing"] == 22  # the stored T4h meta was read from its folder


@pytest.fixture
def pass_grades(monkeypatch):
    monkeypatch.setattr(h8, "grade_lines", lambda results, judge: {
        h8.plain_key(run["key"]): {"grade": h8.GRADE_PASS, "level": run["level"]}
        for run in results})


def test_t12_main(tmp_path, monkeypatch, elsewhere, pass_grades) -> None:
    base = _write_json(tmp_path / "stored" / "h6_dg3_v4on.json", _dg3_document(setting="VB"))
    monkeypatch.setattr(fixed, "H6_SHA256", _sha(base))
    new_document = _dg3_document(setting="VBH")
    new_document["meta"]["keys_file"]["sha256"] = _sha(base)
    new = _write_json(tmp_path / "run" / "dg3_VBH.json", new_document)
    judge = _write_json(tmp_path / "run" / "judge.json", {})
    out = tmp_path / "t12.json"
    code = tjr.main(["t12", "--bundle", "VBH", "--base", str(base), "--base-judge", str(judge),
                     "--base-judge-sha256", _sha(judge), "--new", str(new), "--new-judge",
                     str(judge), "--new-judge-sha256", _sha(judge), "--out", str(out)])
    assert code == compare.EXIT_PASS, json.loads(out.read_text(encoding="utf-8"))


def test_records_main(tmp_path, monkeypatch, elsewhere) -> None:
    prelaunch = tmp_path / "prelaunch"
    prelaunch.mkdir()
    sums = {}
    for name, runs in (("h10_reuse_rerun_t4h.SHA256SUMS", 426),
                       ("h6_dg3_v4on_t4h.SHA256SUMS", 135)):
        lines = [f"{'0' * 64} *{file}" for file in sorted(T4H_NAMES[runs])]
        sums[name] = prelaunch / name
        sums[name].write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(tjr, "T4H_SUMS_SHA256", {name: _sha(path) for name, path in sums.items()})
    h6 = _write_json(tmp_path / "stored" / "h6_dg3_v4on.json", _dg3_document(setting="VB"))
    monkeypatch.setattr(fixed, "H6_SHA256", _sha(h6))
    run = tmp_path / "run"
    replays = [_write_json(run / f"t4h_replay_{index}.json", document)
               for index, document in enumerate(REPLAY_REPORTS)]
    rows = valid_lock_rows()
    vbh = _write_json(run / "dg3_VBH.json", _dg3_document(setting="VBH"))
    vbj = _write_json(run / "dg3_VBJ.json", {**_dg3_document(setting="VBJ"), "results": rows[5:]})
    cases = _write_rows(run / "j9_cases.jsonl", rows[:5])
    out = tmp_path / "records.json"
    code = tjr.main(["records", "--replay", *map(str, replays), "--t4h-sums",
                     *map(str, sums.values()), "--dg3", str(vbh), str(vbj), "--h6", str(h6),
                     "--lock-rows", str(vbj), str(cases), "--out", str(out)])
    assert code == compare.EXIT_PASS, json.loads(out.read_text(encoding="utf-8"))


# --- jp3_dryrun_evidence summarize --------------------------------------------------------------

def test_dryrun_summarize_main(tmp_path, elsewhere) -> None:
    folder = tmp_path / "dry"
    folder.mkdir()
    events, r79 = _summary_files(folder)
    selection = _write_json(folder / "selection.json", SELECTION)
    out = tmp_path / "summary.json"
    code = dryrun.main(["summarize", "--selection", str(selection), "--out", str(out),
                        "--event", *[f"{k}={v}" for k, v in events.items()],
                        "--r79", *[f"{k}={v}" for k, v in r79.items()]])
    assert code == dryrun.EXIT_DONE, json.loads(out.read_text(encoding="utf-8"))
