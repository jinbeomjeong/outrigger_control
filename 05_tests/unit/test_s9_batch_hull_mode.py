"""s9_batch hull hook records (post-switch audit 2026-11-09): the effective mode copied from each row's result.json,
MIXED_HULL_MODE over SCM rows, and the --resume check of the earlier hull request and commit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import s9_batch as sb  # noqa: E402

WRITE_RESULT = (
    "import json, pathlib, sys\n"
    "args = sys.argv\n"
    "folder = pathlib.Path(args[args.index('--out-root') + 1]) / args[args.index('--case') + 1]\n"
    "folder.mkdir(parents=True, exist_ok=True)\n"
    "hull = None if args[1] == 'none' else {'mode': args[1], 'fallback_reason': args[2] or None}\n"
    "doc = {} if hull is None else {'hull_hook': hull}\n"
    "(folder / 'result.json').write_text(json.dumps(doc), encoding='utf-8')\n"
)
"""Child of a test row: writes ``<out-root>/<case>/result.json`` with ``hull_hook`` = (argv[1] mode, argv[2] reason)."""


def _row(case: str, mode: str, reason: str = "") -> dict:
    return {"case": case, "argv": [sys.executable, "-c", WRITE_RESULT, mode, reason], "est_s": 1.0}


@pytest.fixture
def batch_env(monkeypatch, tmp_path):
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    monkeypatch.delenv("OMP_WAIT_POLICY", raising=False)
    monkeypatch.setattr(sb, "ROOT", tmp_path)

    def use_rows(rows: list[dict]) -> None:
        monkeypatch.setattr(sb, "batches", lambda **_: {"TEST-HULL": rows})

    return use_rows


def _write_result(folder: Path, case: str, hull: dict | None) -> None:
    (folder / case).mkdir(parents=True, exist_ok=True)
    doc = {} if hull is None else {"hull_hook": hull}
    (folder / case / "result.json").write_text(json.dumps(doc), encoding="utf-8")


def test_hull_hook_effective(tmp_path) -> None:
    _write_result(tmp_path, "scm", {"mode": "off", "fallback_reason": "dll_sha_unvalidated", "stats": None})
    _write_result(tmp_path, "l1", None)
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "result.json").write_text("{", encoding="utf-8")
    assert sb.hull_hook_effective(tmp_path, "scm") == {"mode": "off", "fallback_reason": "dll_sha_unvalidated"}
    assert sb.hull_hook_effective(tmp_path, "l1") is None
    assert sb.hull_hook_effective(tmp_path, "missing") is None
    bad = sb.hull_hook_effective(tmp_path, "bad")
    assert bad["mode"] is None and "JSONDecodeError" in bad["error"]


def test_run_batch_copies_effective_and_logs_mixed(batch_env) -> None:
    batch_env([_row("scm_fast", "fast"), _row("scm_off", "off", "dll_sha_unvalidated"), _row("l1", "none")])
    folder = sb.run_batch("TEST-HULL", parallel=3)
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    got = {c["case"]: c["hull_hook_effective"] for c in doc["cases"]}
    assert got == {"scm_fast": {"mode": "fast", "fallback_reason": None},
                   "scm_off": {"mode": "off", "fallback_reason": "dll_sha_unvalidated"}, "l1": None}
    assert doc["mixed_hull_mode"] is True
    log = (folder / "progress.log").read_text("utf-8")
    assert "MIXED_HULL_MODE fast: scm_fast; off: scm_off" in log


def test_run_batch_same_mode_not_mixed(batch_env) -> None:
    batch_env([_row("a", "fast"), _row("b", "fast"), _row("l1", "none")])
    folder = sb.run_batch("TEST-HULL", parallel=3)
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    assert doc["mixed_hull_mode"] is False
    assert "MIXED_HULL_MODE" not in (folder / "progress.log").read_text("utf-8")


def _earlier_launch(folder: Path, entry: dict) -> None:
    """A batch folder whose row ``done`` finished in an earlier launch (result.json + batch.json entry)."""
    _write_result(folder, "done", {"mode": "fast", "fallback_reason": None})
    doc = {"cases": [{"case": "done", "argv": [], "rc": 0, "wall_s": 1.0, "est_s": 1.0, "pool": "pcore", **entry}]}
    (folder / "batch.json").write_text(json.dumps(doc), encoding="utf-8")


@pytest.mark.parametrize("entry", [{"hull_hook_requested": "off"}, {}], ids=["off", "pre-switch"])
def test_resume_stops_on_other_hull_request(batch_env, tmp_path, entry) -> None:
    folder = tmp_path / "earlier"
    _earlier_launch(folder, entry)
    batch_env([_row("done", "fast"), _row("todo", "fast")])
    with pytest.raises(SystemExit) as e:
        sb.run_batch("TEST-HULL", resume=str(folder))
    expected_before = entry.get("hull_hook_requested", "pre-switch")
    assert f"done ({expected_before} -> fast)" in str(e.value) and sb.MIXED_HULL_ARG in str(e.value)
    assert not (folder / "todo").exists()  # nothing was launched


def test_resume_allow_mixed_hull_continues_and_records(batch_env, tmp_path) -> None:
    folder = tmp_path / "earlier"
    _earlier_launch(folder, {"hull_hook_requested": "off"})
    batch_env([_row("done", "fast"), _row("todo", "fast")])
    sb.run_batch("TEST-HULL", resume=str(folder), allow_mixed_hull=True)
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    assert doc["resume_check"]["allow_mixed_hull"] is True
    assert doc["resume_check"]["hull_conflicts"] == [{"case": "done", "before": "off", "now": "fast"}]
    assert "RESUME_MIXED_HULL done requested off earlier, fast now" in (folder / "progress.log").read_text("utf-8")
    assert {c["case"] for c in doc["cases"]} == {"done", "todo"}


def test_resume_same_request_passes(batch_env, tmp_path) -> None:
    folder = tmp_path / "earlier"
    _earlier_launch(folder, {"hull_hook_requested": "fast"})
    batch_env([_row("done", "fast"), _row("todo", "fast")])
    sb.run_batch("TEST-HULL", resume=str(folder))
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    assert doc["resume_check"] == {"hull_conflicts": [], "hull_unrecorded": [], "allow_mixed_hull": False,
                                   "head_changes": []}


def test_former_hull_request_sources() -> None:
    former = {"keyed": {"hull_hook_requested": "off"}, "old": {}}
    progress = ("START post 2026-11-09T10:00:00 pid=1 est_s=1 pool=pcore OMP_WAIT_POLICY=PASSIVE hull_hook=shadow\n"
                "START pre 2026-11-01T10:00:00 pid=2 est_s=1 pool=pcore OMP_WAIT_POLICY=PASSIVE\n")
    assert sb.former_hull_request("keyed", former, progress) == "off"
    assert sb.former_hull_request("old", former, progress) == "pre-switch"
    assert sb.former_hull_request("post", former, progress) == "shadow"
    assert sb.former_hull_request("pre", former, progress) == "pre-switch"
    assert sb.former_hull_request("never", former, progress) is None


def test_resume_without_any_record_warns_only(batch_env, tmp_path) -> None:
    folder = tmp_path / "earlier"
    _write_result(folder, "done", {"mode": "fast", "fallback_reason": None})  # no batch.json, no progress.log
    batch_env([_row("done", "fast"), _row("todo", "fast")])
    sb.run_batch("TEST-HULL", resume=str(folder))
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    assert doc["resume_check"]["hull_unrecorded"] == ["done"]
    assert "WARN_RESUME_HULL_UNRECORDED done" in (folder / "progress.log").read_text("utf-8")


def test_resume_progress_start_line_conflict_stops(batch_env, tmp_path) -> None:
    folder = tmp_path / "earlier"
    _write_result(folder, "done", {"mode": "off", "fallback_reason": None})
    (folder / "progress.log").write_text("START done 2026-11-09T10:00:00 pid=1 est_s=1 pool=pcore hull_hook=off\n",
                                         encoding="utf-8")
    batch_env([_row("done", "fast"), _row("todo", "fast")])
    with pytest.raises(SystemExit) as e:
        sb.run_batch("TEST-HULL", resume=str(folder))
    assert "done (off -> fast)" in str(e.value)


def test_resume_head_change_warns_only(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    monkeypatch.setattr(sb, "_git_head", lambda _root: "b" * 40)
    former = {"done": {"hull_hook_requested": "fast", "code_at_launch": {"git": {"head": "a" * 40}}}}
    check = sb.resume_launch_check([{"case": "done"}], former, allow_mixed_hull=False)
    assert check["hull_conflicts"] == []
    assert check["head_changes"] == [{"case": "done", "before": "a" * 40, "now": "b" * 40}]
    monkeypatch.setattr(sb, "_git_head", lambda _root: "a" * 40)
    assert sb.resume_launch_check([{"case": "done"}], former, allow_mixed_hull=False)["head_changes"] == []


def test_resume_check_uses_row_env(monkeypatch) -> None:
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    row = {"case": "done", "run_env": {"OUTRIGGER_HULL_HOOK": "off"}}
    check = sb.resume_launch_check([row], {"done": {"hull_hook_requested": "off"}}, allow_mixed_hull=False)
    assert check["hull_conflicts"] == []


def test_cli_has_allow_mixed_hull() -> None:
    args = sb.build_parser().parse_args(["run", sorted(sb.batches())[0], "--allow-mixed-hull"])
    assert args.allow_mixed_hull is True
