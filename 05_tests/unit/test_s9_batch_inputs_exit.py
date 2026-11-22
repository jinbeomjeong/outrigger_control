"""s9_batch (2026-11-22): ``run`` exits non-zero when a row failed, and stops before any launch when a git-ignored
input of a row (L1-R start snapshot in ``07_results/states_L1R``, hull hook DLL of an SCM row) is missing."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import s9_batch as sb  # noqa: E402

G8C1 = "G8C1_top_edge_FL_g170"
"""A real run_S6C case (FINAL-R / JOURNAL-V0-RIGID L1-R row, set ``g8c76_p28acc``)."""

MARK = (
    "import pathlib, sys\n"
    "pathlib.Path(sys.argv[1]).write_text('ran', encoding='utf-8')\n"
    "sys.exit(int(sys.argv[2]))\n"
)
"""Child of a test row: writes the marker file argv[1] and exits with argv[2]."""


def _row(case: str, marker: Path, rc: int = 0, **extra) -> dict:
    return {"case": case, "argv": [sys.executable, "-c", MARK, str(marker), str(rc)], "est_s": 1.0, **extra}


def _s6c_row(marker: Path, case_id: str = G8C1) -> dict:
    row = _row(case_id, marker, 0, s6c=True, fixed_pcore=True)
    row["argv"] += ["run", "--set", "g8c76_p28acc", "--only", case_id, "--approved", "--jobs", "1"]
    return row


@pytest.fixture
def batch_env(monkeypatch, tmp_path):
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    monkeypatch.delenv("OUTRIGGER_L1_FALLBACK_RATIO_SOURCE", raising=False)
    monkeypatch.setattr(sb, "ROOT", tmp_path)

    def use_rows(rows: list[dict], name: str = "TEST-IN") -> None:
        monkeypatch.setattr(sb, "batches", lambda **_: {name: rows})

    return use_rows


# --- defect 1: exit code of a failed batch ------------------------------------------------------------------------


def test_run_failed_row_exits_nonzero(batch_env, tmp_path, capsys) -> None:
    batch_env([_row("ok1", tmp_path / "ok1.txt"), _row("bad", tmp_path / "bad.txt", rc=1),
               _row("after", tmp_path / "after.txt")])
    with pytest.raises(SystemExit) as e:
        sb.main(["run", "TEST-IN", "--parallel", "1"])
    assert e.value.code == sb.BATCH_FAILED_EXIT != 0
    err = capsys.readouterr().err
    assert "batch TEST-IN FAILED: bad rc=1" in err and "not started: after" in err
    folder = next((tmp_path / "07_results" / "S9").glob("batch_TEST-IN_*"))
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    assert doc["failed"] is True
    assert "failed=True" in (folder / "progress.log").read_text("utf-8")
    assert not (tmp_path / "after.txt").exists()  # the stop-new-launches rule is unchanged


def test_run_all_ok_returns_normally(batch_env, tmp_path) -> None:
    batch_env([_row("a", tmp_path / "a.txt"), _row("b", tmp_path / "b.txt")])
    assert sb.main(["run", "TEST-IN", "--parallel", "2"]) is None
    assert (tmp_path / "a.txt").exists() and (tmp_path / "b.txt").exists()


def test_raise_if_failed_reads_batch_json(tmp_path, capsys) -> None:
    doc = {"failed": True, "cases": [{"case": "s8", "rc": sb.S8C_FAILED_RC}, {"case": "ok", "rc": 0},
                                     {"case": "skip", "rc": None}]}
    (tmp_path / "batch.json").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        sb.raise_if_failed("X", tmp_path)
    assert e.value.code == sb.BATCH_FAILED_EXIT
    assert f"s8 rc={sb.S8C_FAILED_RC}" in capsys.readouterr().err
    (tmp_path / "batch.json").write_text(json.dumps({"failed": False, "cases": []}), encoding="utf-8")
    sb.raise_if_failed("X", tmp_path)  # no exception
    (tmp_path / "batch.json").unlink()
    with pytest.raises(SystemExit):
        sb.raise_if_failed("X", tmp_path)


def test_run_batch_still_returns_folder_on_failure(batch_env, tmp_path) -> None:
    """Callers of run_batch (tests, scripts) keep the folder; only the ``run`` command exits non-zero."""
    batch_env([_row("bad", tmp_path / "bad.txt", rc=3)])
    folder = sb.run_batch("TEST-IN", parallel=1)
    assert json.loads((folder / "batch.json").read_text("utf-8"))["failed"] is True


# --- defect 2: git-ignored inputs checked before any launch -------------------------------------------------------


def test_s6c_snapshot_resolved_from_run_s6c(tmp_path) -> None:
    snap, why = sb.l1r_snapshot_of(_s6c_row(tmp_path / "m.txt"), {})
    assert why is None and snap and snap.startswith("S6_crawler_")


def test_run_stops_before_launch_when_snapshot_missing(batch_env, tmp_path) -> None:
    marker = tmp_path / "ran.txt"
    other = tmp_path / "other.txt"
    batch_env([_row("first", other), _s6c_row(marker)])
    snap, _ = sb.l1r_snapshot_of(_s6c_row(marker), {})
    with pytest.raises(SystemExit) as e:
        sb.run_batch("TEST-IN", parallel=1)
    msg = str(e.value)
    assert "nothing was launched" in msg and G8C1 in msg and f"states_L1R/{snap}.npz" in msg
    assert "l1r_snapshot" in msg and "run_S6C.py snaps" in msg
    assert not marker.exists() and not other.exists()  # no row started, not even the one without the input
    assert not (tmp_path / "07_results" / "S9").exists()  # no batch folder either
    # with the snapshot in place the same batch runs
    states = tmp_path / "07_results" / "states_L1R"
    states.mkdir(parents=True)
    (states / f"{snap}.npz").write_bytes(b"")
    folder = sb.run_batch("TEST-IN", parallel=1)
    assert marker.exists() and other.exists()
    assert "# input check ok: 1 git-ignored input(s) present" in (folder / "progress.log").read_text("utf-8")


def test_run_cli_missing_snapshot_exit_nonzero(batch_env, tmp_path) -> None:
    batch_env([_s6c_row(tmp_path / "ran.txt")])
    with pytest.raises(SystemExit) as e:
        sb.main(["run", "TEST-IN", "--parallel", "1"])
    assert e.value.code not in (0, None) and not (tmp_path / "ran.txt").exists()


def test_resume_checks_only_rows_still_to_run(batch_env, tmp_path) -> None:
    """--resume: a finished s6c row (its log names an ok case) needs no snapshot; nothing missing -> runs."""
    folder = tmp_path / "earlier"
    folder.mkdir()
    rdir = tmp_path / "S6" / "b"
    (rdir / G8C1).mkdir(parents=True)
    (rdir / G8C1 / "result.json").write_text("{}", encoding="utf-8")
    (folder / f"{G8C1}.log").write_text(f"{G8C1}: ok 1s\nbatch wall 1 s -> {rdir}\n", encoding="utf-8")
    row = {**_s6c_row(tmp_path / "ran.txt"), "s8c": True}  # row_finished reads an s8c-style log
    batch_env([row, _row("todo", tmp_path / "todo.txt")])
    sb.run_batch("TEST-IN", parallel=1, resume=str(folder))
    assert (tmp_path / "todo.txt").exists() and not (tmp_path / "ran.txt").exists()


def test_s8c_l1r_twin_needs_snapshot_l2b_does_not(tmp_path) -> None:
    tables = {"s8c": {"T1": SimpleNamespace(engine="L1R", base=SimpleNamespace(snapshot="S6_x")),
                      "L2": SimpleNamespace(engine="L2b_NSC", base=SimpleNamespace(snapshot="S6_y"))}}
    rows = [{"case": c, "s8c": True, "argv": ["run_S8C.py", "run", "--set", "s", "--only", c]} for c in ("T1", "L2")]
    chk = sb.untracked_input_check(rows, root=tmp_path, tables=tables)
    assert not chk["ok"] and chk["checked"] == 1
    assert [(m["case"], m["input"]) for m in chk["missing"]] == [("T1", "l1r_snapshot")]
    (tmp_path / "07_results" / "states_L1R").mkdir(parents=True)
    (tmp_path / "07_results" / "states_L1R" / "S6_x.npz").write_bytes(b"")
    assert sb.untracked_input_check(rows, root=tmp_path, tables=tables)["ok"]


def test_unresolved_row_is_reported_not_stopped(tmp_path) -> None:
    rows = [{"case": "x", "s6c": True, "argv": ["run_S6C.py", "run"]},
            {"case": "y", "s6c": True, "argv": ["run_S6C.py", "run", "--only", "NOPE"]}]
    chk = sb.untracked_input_check(rows, root=tmp_path, tables={"s6c": {}})
    assert chk["ok"] and [u["case"] for u in chk["unresolved"]] == ["x", "y"]
    assert any(line.startswith("WARN_INPUT_UNRESOLVED x") for line in sb.input_check_lines("B", chk))


def _scm_row(case: str, **env) -> dict:
    return {"case": case, "argv": [sys.executable, "-I", "-u", "04_scripts/02_chrono/run_S9.py", "level"],
            "est_s": 1.0, "run_env": env}


def test_hull_dll_checked_on_scm_rows(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED", raising=False)
    hh = sb._hull_hook_module()
    dll = tmp_path / "chrono_hull_hook.dll"
    rows = [_scm_row("scm", OUTRIGGER_HULL_HOOK_DLL=str(dll)),
            _scm_row("scm_off", OUTRIGGER_HULL_HOOK="off", OUTRIGGER_HULL_HOOK_DLL=str(dll)),
            {"case": "not_scm", "argv": [sys.executable, "-c", "pass"], "est_s": 1.0,
             "run_env": {"OUTRIGGER_HULL_HOOK_DLL": str(dll)}}]
    chk = sb.untracked_input_check(rows, root=tmp_path)
    assert [(m["case"], m["input"]) for m in chk["missing"]] == [("scm", "hull_hook_dll")]
    assert "missing (hull request fast)" in chk["missing"][0]["reason"]
    dll.write_bytes(b"not the validated build")
    chk = sb.untracked_input_check(rows, root=tmp_path)
    assert [m["case"] for m in chk["missing"]] == ["scm"] and "!= validated" in chk["missing"][0]["reason"]
    rows[0]["run_env"][hh.ENV_ALLOW_UNVALIDATED] = "1"
    assert sb.untracked_input_check(rows, root=tmp_path)["ok"]


def test_hull_dll_validated_build_passes(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    hh = sb._hull_hook_module()
    dll = tmp_path / "hook.dll"
    dll.write_bytes(b"x")
    monkeypatch.setattr(hh, "VALIDATED_DLL_SHA256", hh._sha256(dll))
    assert sb.untracked_input_check([_scm_row("scm", OUTRIGGER_HULL_HOOK_DLL=str(dll))], root=tmp_path)["ok"]


def test_check_inputs_cli(batch_env, tmp_path, capsys) -> None:
    batch_env([_s6c_row(tmp_path / "ran.txt")])
    with pytest.raises(SystemExit) as e:
        sb.main(["check-inputs", "TEST-IN"])
    assert e.value.code == 1 and "MISSING" in capsys.readouterr().out
    snap, _ = sb.l1r_snapshot_of(_s6c_row(tmp_path / "ran.txt"), {})
    (tmp_path / "07_results" / "states_L1R").mkdir(parents=True)
    (tmp_path / "07_results" / "states_L1R" / f"{snap}.npz").write_bytes(b"")
    sb.main(["check-inputs", "TEST-IN"])
    assert capsys.readouterr().out.strip().endswith("present over 1 rows)")
    assert not (tmp_path / "ran.txt").exists()  # check-inputs launches nothing
