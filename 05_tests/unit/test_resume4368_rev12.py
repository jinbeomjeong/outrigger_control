"""436.8 rules rev12 (``v5_resume_4368_rules_rev12.md``, sealed 78f1f99b) in the path 1 tools.

R12-6: the three seal lists carry rev12. R12-1 (Q-R12-1 = A): every judgement that reads a T4h
(H-6, stage 1, U-9 J-P3 rod reading) looks only in the result file's runner convention folders
(one ``--t4h-dir`` only without them); a recorded ``t4h_file`` found 0 or 2+ times is S-2, a line
without ``t4h_file`` keeps the R3-C8 configuration rule. R12-2 / R12-4: Chrono dirty and the
open-loop ``code_state`` are recorded only (judge side; gs-check in
``test_v5_resume_4368_chrono_rows.py``). R12-5: the row-folder time window (START..END else stamp
+ ``wall_s``, no ``est_s``) and the exact runner folder names. Synthetic inputs only.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
CHRONO_SCRIPTS = ROOT / "04_scripts" / "02_chrono"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, CHRONO_SCRIPTS, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import chrono_rows_judge_4368 as chrono_judge  # noqa: E402
import h6_judge_4368 as h6j  # noqa: E402
import judge4368_common as common  # noqa: E402
import judge_stage1_4368 as stage1  # noqa: E402
import resume4368_judge as judge  # noqa: E402
import u9_judge_4368 as u9j  # noqa: E402

REV12_NAME = "v5_resume_4368_rules_rev12.md"
REV12_SHA256 = "78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140"
T4H_NAME = "L3_s1_g8_34.npz"
TAG_P3 = "final_C4G2_P3_LAS_K1"


# ------------------------------------------------------------------------------ R12-6 seals
def test_every_path1_seal_list_has_rev12() -> None:
    assert (judge.RULES_REV12_NAME, judge.RULES_REV12_SHA256) == (REV12_NAME, REV12_SHA256)
    assert (REV12_NAME, REV12_SHA256) in judge.SEALED_REVISIONS
    assert (REV12_NAME, REV12_SHA256) in common.SEALED_RULES
    assert chrono_judge.RULES_SEALS[REV12_NAME] == REV12_SHA256


def test_stored_rev12_matches_its_seal() -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert common.seal_report()["problems"] == []
    assert chrono_judge.seal_check(common.RULES_DIR)["ok"] is True


@pytest.mark.parametrize("missing", [REV12_NAME, REV12_NAME.replace(".md", ".sha256")])
def test_a_missing_rev12_file_is_s1(tmp_path: Path, missing: str) -> None:
    for name in [*chrono_judge.RULES_SEALS, *(n for n, _ in judge.SEALED_REVISIONS)]:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, tmp_path / path.name)
    (tmp_path / missing).unlink()
    assert judge.sealed_rules_check(tmp_path)["stop_S1"] is True
    assert common.seal_report(tmp_path)["stop_S1"] is True
    assert chrono_judge.seal_check(tmp_path)["ok"] is False


# ------------------------------------------------------------------- R12-1 shared T4h lookup
def _write_t4h(folder: Path, rod: np.ndarray | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    arrays = {"t_s": np.zeros(2)} | ({} if rod is None else {"rod_pressure_Pa": rod})
    np.savez(folder / T4H_NAME, **arrays)
    return folder


def _result(tmp_path: Path, stem: str) -> Path:
    path = tmp_path / f"{stem}.json"
    path.write_text("{}", encoding="utf-8")
    return path


def test_convention_folders_only(tmp_path: Path) -> None:
    result = _result(tmp_path, "h6_dg3_v4on")
    own = _write_t4h(tmp_path / "h6_dg3_v4on_t4h")
    records = [{"t4h_file": T4H_NAME}]
    assert common.t4h_folders(result, records) == [own]
    with pytest.raises(common.InputError, match="convention folder"):
        common.t4h_folders(result, records, [tmp_path / "elsewhere"])
    with pytest.raises(common.InputError, match="at most one"):
        common.t4h_folders(result, records, [tmp_path / "a", tmp_path / "b"])


def test_one_folder_only_without_convention_folders(tmp_path: Path) -> None:
    result = _result(tmp_path, "h9_stage1")
    other = _write_t4h(tmp_path / "elsewhere")
    assert common.t4h_folders(result, [{"t4h_file": T4H_NAME}], [other]) == [other]
    assert common.t4h_folders(result, [{"job": {}}], [other]) == []  # no T4h records


@pytest.mark.parametrize(
    ("record", "folders", "status"),
    [
        ({"job": {}}, [], "no_t4h_file"),
        ({"t4h_file": T4H_NAME}, ["one"], "found"),
        ({"t4h_file": T4H_NAME}, [], "S-2"),
        ({"t4h_file": T4H_NAME}, ["one", "two"], "S-2"),
        ({"t4h_file": None}, ["one"], "S-2"),
    ],
)
def test_locate_t4h(tmp_path: Path, record, folders, status) -> None:
    paths = [_write_t4h(tmp_path / name) for name in folders]
    assert common.locate_t4h(record, paths)["status"] == status


# ------------------------------------------------------------------------ R12-1 in the judges
def test_h6_rod_reading_without_t4h_file_uses_the_configuration_rule() -> None:
    assert h6j.rod_reading({"key": "k"}, ()) == (True, h6j.ROD_BASIS_CONFIGURATION)


def test_h6_rod_reading_of_the_own_file(tmp_path: Path) -> None:
    folder = _write_t4h(tmp_path / "h6_t4h", np.array([np.nan, 2.0e6]))
    assert h6j.rod_reading({"t4h_file": T4H_NAME}, (folder,)) == (True, h6j.ROD_BASIS_T4H)


@pytest.mark.parametrize("n_folders", [0, 2])
def test_h6_recorded_t4h_found_0_or_2_times_is_s2(tmp_path: Path, n_folders: int) -> None:
    """Q-R12-1 = A: never the configuration rule (it was before rev12)."""
    folders = tuple(_write_t4h(tmp_path / f"f{i}") for i in range(n_folders))
    has_reading, basis = h6j.rod_reading({"t4h_file": T4H_NAME}, folders)
    assert has_reading is None and basis.startswith("S-2")


def test_h6_j_p3_stops_on_s2(tmp_path: Path) -> None:
    run = {"key": "k", "controller_tag": TAG_P3, "t4h_file": T4H_NAME,
           "controller_settings": {h6j.EXTEND_START_SETTING: "tracked_bound"}}
    out = h6j.j_p3(run, ())
    assert (out["case"], out["stop"]) == (h6j.J_P3_NOT_JUDGEABLE, "S-2")


def _stage1_line(**extra) -> dict:
    return {"controller_tag": TAG_P3, "head_only_declared": False, "is_event": False, "row": "R1",
            "bound_check": None, "rod_reading": True, "setting": "VB", **extra}


def test_stage1_j_p3_s2_when_the_recorded_t4h_is_not_found_once(tmp_path: Path) -> None:
    record = {"t4h_file": T4H_NAME, "job": {"t4h_dir": str(_write_t4h(tmp_path / "job_dir"))}}
    lookup = stage1.t4h_lookup(record, ())  # job.t4h_dir is not searched (rev12 R12-1)
    assert lookup["status"] == "S-2" and stage1.rod_reading(record, ()) is None
    items = stage1.j_p3_item(_stage1_line(rod_reading=None, t4h_lookup=lookup))
    assert [(i["item"], i["kind"]) for i in items] == [("J-P3", "stop")]
    assert items[0]["detail"].startswith("S-2")


def test_stage1_line_without_t4h_file_is_unchanged() -> None:
    lookup = stage1.t4h_lookup({"job": {}}, ())
    items = stage1.j_p3_item(_stage1_line(rod_reading=None, t4h_lookup=lookup))
    assert [(i["item"], i["kind"]) for i in items] == [("J-P3", "not_judgeable")]


def test_u9_collects_s2_of_every_setting() -> None:
    s2 = {"item": "J-P3", "kind": "stop", "detail": "S-2: t4h_file x found 0 times"}
    keys = [{"case": "D1", "eps": 0.0, "VB0.85": {"J": []}, "VB0.8": {"J": [s2]}}]
    assert u9j.t4h_stops(keys) == ["D1|0.0|VB0.8: S-2: t4h_file x found 0 times"]


# ---------------------------------------------------------------- R12-2 / R12-4 judge side
def test_dirty_and_open_loop_code_state_are_recorded_only() -> None:
    git = {"head": "ba2da55" + "0" * 33, "dirty": [" M x.py"], "clean": False}
    other = {"code_state": {"git_at_start": {"head": "4312b8e" + "0" * 33}}}
    identity = chrono_judge.commit_identity_of({"code_at_launch": {"git": git}}, other,
                                               is_open_loop=True, git_at_start="ba2da55")
    assert identity["status"] == "match" and identity["dirty"] == [" M x.py"]
    assert identity["result_same_as_git_at_start"] is False


# --------------------------------------------------------------------- R12-5 time window
TAG = "r4368gs_D1C1_top_flat_crx3"
ONLY = "D1C1_top_flat_crx3"
WINDOW = (chrono_judge._stamp_time("20261113_082117"), chrono_judge._stamp_time("20261113_082506"))


def _runner_folder(root: Path, name: str, *, with_result: bool = True) -> Path:
    folder = root / name
    (folder / ONLY).mkdir(parents=True)
    if with_result:
        (folder / ONLY / "result.json").write_text("{}", encoding="utf-8")
    return folder


def test_s6_exact_name_only(tmp_path: Path) -> None:
    good = _runner_folder(tmp_path / "S6", f"bundleC_d1c1_{TAG}_L1R_20261113_082118")
    _runner_folder(tmp_path / "S6", f"bundleC_d1c1_{TAG}_check_L1R_20261113_082119")  # check form
    _runner_folder(tmp_path / "S6", f"bundleC_d1c1_{TAG}x_L1R_20261113_082120")  # another tag
    _runner_folder(tmp_path / "S6", f"bundleC_{TAG}_L1R_20261113_082121", with_result=False)
    hits = chrono_judge.runner_folder_candidates("run_S6C.py", TAG, ONLY, tmp_path, WINDOW)
    assert hits == [good / ONLY]


def test_s8_exact_name_and_window(tmp_path: Path) -> None:
    good = _runner_folder(tmp_path / "S8", f"{TAG}_20261113_082508")  # END + 2 s
    _runner_folder(tmp_path / "S8", f"{TAG}_20261113_082509")  # outside the slack
    _runner_folder(tmp_path / "S8", f"x_{TAG}_20261113_082200")  # not the exact name
    hits = chrono_judge.runner_folder_candidates("run_S8C.py", TAG, ONLY, tmp_path, WINDOW)
    assert hits == [good / ONLY]


def test_the_window_never_uses_est_s(tmp_path: Path) -> None:
    batch = tmp_path / "batch_X_20261113_082117"
    batch.mkdir()
    with pytest.raises(chrono_judge.InputError, match="R12-5"):
        chrono_judge._case_window("C", "", batch, {"est_s": 300.0})
    start, end, basis = chrono_judge._case_window("C", "", batch, {"wall_s": 228.6, "est_s": 900.0})
    assert end - start == pytest.approx(228.6) and basis == "batch stamp + wall_s"


def test_judge_row_without_window_is_exit_2(tmp_path: Path, capsys) -> None:
    results = tmp_path / "07_results"
    batch = results / "S9" / "batch_X_20261113_082117"
    batch.mkdir(parents=True)
    argv = ["python.exe", "C:/x/run_S6C.py", "run", "--only", ONLY, "--tag", TAG]
    case = {"case": "GS_D1C1", "argv": argv, "est_s": 300.0, "criteria_id": "C-1"}
    (batch / "batch.json").write_text(json.dumps({"cases": [case]}), encoding="utf-8")
    _runner_folder(results / "S6", f"bundleC_d1c1_{TAG}_L1R_20261113_082118")
    code = chrono_judge.main(["judge", "--git-at-start", "4312b8e",
                              "--out", str(tmp_path / "o.json"),
                              "--batch", str(batch), "--results-root", str(results)])
    assert code == 2 and "R12-5" in capsys.readouterr().out
