"""Unit tests for the parallel batch runner (plan S3 '병렬 실행기와 meta').

The jobs are tiny module-level functions (a spawned case process imports this module to
find them); one shared batch covers success, exceptions, a dying process and bad results.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import pytest

from outrigger_sim import batch as batch_module
from outrigger_sim.batch import (
    BATCH_META_NAME,
    CASE_LOG_NAME,
    CASE_META_NAME,
    REQUIRED_RUN_META_KEYS,
    BatchReport,
    Case,
    CaseResult,
    CaseStatus,
    run_cases,
)
from outrigger_sim.params import load_params
from outrigger_sim.record import make_run_meta

JOB_SLEEP_S = 0.3
MAX_WORKERS = 3
HANG_S = 60.0
TIMEOUT_S = 10.0 if os.environ.get("PYTEST_XDIST_WORKER") else 3.0
"""Under pytest-xdist (-n 16) the spawned 'quick' child alone can take > 3 s to start (CPU
load of the other workers), so the timeout gets more room there; still << HANG_S / 2."""


# --- jobs (run inside case processes) ----------------------------------------------------


def job_by_kind(case: Case, case_dir: Path) -> CaseResult:
    started = time.time()
    kind = case.settings["kind"]
    if kind == "raise":
        raise RuntimeError("deliberate failure")
    if kind == "exit":
        os._exit(3)
    if kind == "bad_meta":
        return CaseResult(run_meta={"dt_s": 1e-4})
    if kind == "not_json":
        return CaseResult(summary={"value": object()})
    if kind == "not_a_result":
        return {"value": 1}  # type: ignore[return-value]
    logging.getLogger("test_batch.job").info("hello from %s", case.case_id)
    (case_dir / "output.txt").write_text(case.case_id, encoding="utf-8")
    time.sleep(JOB_SLEEP_S)
    run_meta = {key: None for key in REQUIRED_RUN_META_KEYS}
    summary = {
        "double": 2 * case.settings["x"],
        "pid": os.getpid(),
        "start": started,
        "end": time.time(),
    }
    return CaseResult(summary=summary, run_meta=run_meta)


def job_quick(case: Case, case_dir: Path) -> CaseResult:
    return CaseResult(summary={"case": case.case_id})


def job_hang_or_quick(case: Case, case_dir: Path) -> CaseResult:
    if case.settings.get("hang"):
        time.sleep(HANG_S)
    return CaseResult(summary={"case": case.case_id})


# --- shared batch --------------------------------------------------------------------------

OK_IDS = ("ok_a", "ok_b", "ok_c", "ok_d")
FAILING_KINDS = ("raise", "exit", "bad_meta", "not_json", "not_a_result")


@pytest.fixture(scope="module")
def batch_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("batch") / "run"


@pytest.fixture(scope="module")
def report(batch_dir: Path) -> BatchReport:
    cases = [Case(case_id, {"kind": "ok", "x": index}) for index, case_id in enumerate(OK_IDS)]
    cases += [Case(f"fail_{kind}", {"kind": kind}) for kind in FAILING_KINDS]
    return run_cases(cases, job_by_kind, batch_dir, max_workers=MAX_WORKERS, placement="os")


def _outcomes_by_id(report: BatchReport) -> dict[str, Any]:
    return {outcome.case_id: outcome for outcome in report.outcomes}


def test_outcomes_keep_the_input_order(report: BatchReport) -> None:
    expected = [*OK_IDS, *(f"fail_{kind}" for kind in FAILING_KINDS)]
    assert [outcome.case_id for outcome in report.outcomes] == expected


def test_successful_cases_run_in_separate_processes(report: BatchReport) -> None:
    outcomes = _outcomes_by_id(report)
    pids = set()
    for index, case_id in enumerate(OK_IDS):
        outcome = outcomes[case_id]
        assert outcome.status is CaseStatus.OK
        assert outcome.exit_code == 0
        assert outcome.error is None
        assert outcome.document["summary"]["double"] == 2 * index
        assert (outcome.case_dir / "output.txt").read_text(encoding="utf-8") == case_id
        pids.add(outcome.document["summary"]["pid"])
    assert len(pids) == len(OK_IDS)
    assert os.getpid() not in pids


def test_no_more_than_max_workers_run_at_once(report: BatchReport) -> None:
    intervals = [
        (outcome.document["summary"]["start"], outcome.document["summary"]["end"])
        for outcome in report.outcomes
        if outcome.status is CaseStatus.OK
    ]
    for start, _ in intervals:
        overlapping = sum(other_start <= start < other_end for other_start, other_end in intervals)
        assert overlapping <= MAX_WORKERS


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("raise", "RuntimeError: deliberate failure"),
        ("exit", "exited with code 3"),
        ("bad_meta", "run_meta lacks"),
        ("not_json", "not JSON-serialisable"),
        ("not_a_result", "must return CaseResult"),
    ],
)
def test_failures_are_isolated_and_explained(report: BatchReport, kind: str, message: str) -> None:
    outcome = _outcomes_by_id(report)[f"fail_{kind}"]
    assert outcome.status is CaseStatus.FAILED
    assert outcome.error is not None and message in outcome.error
    on_disk = json.loads((outcome.case_dir / CASE_META_NAME).read_text(encoding="utf-8"))
    assert on_disk["runner"]["status"] == "failed"
    if kind == "exit":
        assert outcome.exit_code == 3


def test_case_file_holds_runner_meta_run_meta_and_log(report: BatchReport) -> None:
    outcome = _outcomes_by_id(report)["ok_a"]
    document = json.loads((outcome.case_dir / CASE_META_NAME).read_text(encoding="utf-8"))
    assert document["case_id"] == "ok_a"
    assert document["settings"] == {"kind": "ok", "x": 0}
    assert set(document["run_meta"]) == set(REQUIRED_RUN_META_KEYS)
    runner = document["runner"]
    assert runner["job"].endswith("job_by_kind")
    assert runner["placement"]["mode"] == "os"
    assert runner["job_wall_s"] >= JOB_SLEEP_S
    assert outcome.wall_s >= runner["job_wall_s"]
    log_text = (outcome.case_dir / CASE_LOG_NAME).read_text(encoding="utf-8")
    assert "hello from ok_a" in log_text


def test_batch_file_summarises_the_run(report: BatchReport, batch_dir: Path) -> None:
    assert report.batch_meta_path == batch_dir / BATCH_META_NAME
    document = json.loads(report.batch_meta_path.read_text(encoding="utf-8"))
    assert document["counts"] == {"ok": len(OK_IDS), "failed": len(FAILING_KINDS)}
    assert document["max_workers"] == MAX_WORKERS
    assert document["placement"] == "os"
    assert [row["case_id"] for row in document["cases"]] == [o.case_id for o in report.outcomes]
    failed_row = next(row for row in document["cases"] if row["case_id"] == "fail_raise")
    assert failed_row["error"] == "RuntimeError: deliberate failure"
    assert report.failed_case_ids == [f"fail_{kind}" for kind in FAILING_KINDS]
    assert not report.is_all_ok


def test_existing_case_directory_or_batch_file_is_refused(batch_dir: Path, report) -> None:
    with pytest.raises(FileExistsError, match="ok_a"):
        run_cases([Case("ok_a")], job_quick, batch_dir)
    with pytest.raises(FileExistsError, match=BATCH_META_NAME):
        run_cases([Case("new_case")], job_quick, batch_dir)


# --- placement and input checks ------------------------------------------------------------


def test_pcore_placement_is_recorded(tmp_path: Path) -> None:
    report = run_cases([Case("only")], job_quick, tmp_path / "pcore", max_workers=1)
    assert report.is_all_ok
    placement = report.outcomes[0].document["runner"]["placement"]
    assert placement["mode"] == "pcore"
    if placement["efficiency_classes"]:  # Windows with CPU sets
        assert placement["power_throttling_off_ok"] is True


def test_empty_batch_writes_a_batch_file(tmp_path: Path) -> None:
    report = run_cases([], job_quick, tmp_path / "empty")
    assert report.outcomes == ()
    assert json.loads(report.batch_meta_path.read_text(encoding="utf-8"))["counts"] == {
        "ok": 0,
        "failed": 0,
    }


@pytest.mark.parametrize("bad_workers", [0, -1, 1.5, True])
def test_max_workers_must_be_a_positive_int(tmp_path: Path, bad_workers: Any) -> None:
    with pytest.raises(ValueError, match="max_workers"):
        run_cases([Case("a")], job_quick, tmp_path, max_workers=bad_workers)


def test_duplicate_case_ids_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        run_cases([Case("a"), Case("a")], job_quick, tmp_path)


def test_jobs_that_cannot_reach_a_process_are_refused(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="module-level"):
        run_cases([Case("a")], lambda case, case_dir: CaseResult(), tmp_path)
    assert not (tmp_path / "a").exists()


@pytest.mark.parametrize("bad_id", ["", "a/b", "..", "space here", "한글"])
def test_case_ids_must_be_directory_safe(bad_id: str) -> None:
    with pytest.raises(ValueError, match="case_id"):
        Case(bad_id)


def test_unknown_placement_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fastest"):
        run_cases([Case("a")], job_quick, tmp_path, placement="fastest")


def test_required_keys_are_produced_by_make_run_meta(params_path: Path) -> None:
    params = load_params(params_path)
    engine_meta = {"engine": "fake", "dt_s": 1e-4, "params_sha256": params.sha256}
    run_meta = make_run_meta(params, engine_meta, scenario="dummy")
    assert set(REQUIRED_RUN_META_KEYS) <= set(run_meta)


def test_module_has_no_engine_dependency() -> None:
    source = Path(batch_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("import pychrono", "from pychrono"):
        assert forbidden not in source


# --- timeout -------------------------------------------------------------------------------


def test_timed_out_case_is_terminated_and_failed(tmp_path: Path) -> None:
    cases = [Case("hangs", {"hang": True}), Case("quick")]
    start_s = time.perf_counter()
    report = run_cases(
        cases, job_hang_or_quick, tmp_path / "timeout", placement="os", timeout_s=TIMEOUT_S
    )
    assert time.perf_counter() - start_s < HANG_S / 2
    hung, quick = report.outcomes
    assert quick.status is CaseStatus.OK
    assert hung.status is CaseStatus.FAILED
    assert hung.error is not None and hung.error.startswith("timeout")
    assert TIMEOUT_S <= hung.wall_s < HANG_S / 2
    on_disk = json.loads((hung.case_dir / CASE_META_NAME).read_text(encoding="utf-8"))
    assert on_disk["runner"]["reason"] == "timeout"
    batch_document = json.loads(report.batch_meta_path.read_text(encoding="utf-8"))
    assert batch_document["counts"] == {"ok": 1, "failed": 1}


@pytest.mark.parametrize("bad_timeout", [0.0, -1.0, float("nan"), float("inf"), "5", True])
def test_timeout_must_be_positive_seconds(tmp_path: Path, bad_timeout: Any) -> None:
    with pytest.raises(ValueError, match="timeout_s"):
        run_cases([Case("a")], job_quick, tmp_path, timeout_s=bad_timeout)
