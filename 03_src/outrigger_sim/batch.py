"""Parallel batch runner: independent cases in separate processes (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` S3 ("병렬 실행기와 meta") and risk #24. This module
never imports a physics engine; the work of a case is a callable (the *job*) that builds its
own engine. ``runner`` (plan 3.1) stays the name of the zero-order-hold control loop.

Rules:

* **One fresh process per case** (``spawn``), at most ``max_workers`` at a time (default 4).
  Engine state never leaks between cases.
* **Placement.** Before the job runs, the case process pins itself with
  :func:`outrigger_sim.hostcpu.place_process` (default ``pcore``: P-cores, EcoQoS off), because
  Windows runs window-less child processes on the E-cores about 2.5x slower.
* **Failure isolation, no retry.** An exception in the job, an invalid result, or the process
  dying (crash, ``os._exit``) marks only that case ``failed``; the other cases go on.
* **Timeout** (optional ``timeout_s``, user decision 2026-10-20): a case still running after
  ``timeout_s`` of wall time is terminated and marked ``failed`` with ``runner.reason`` =
  ``"timeout"``, so one hung engine cannot block the batch.
* **Files** (``<output_dir>`` is created; a case directory must not exist yet)::

      <output_dir>/<case_id>/case.json   runner meta + run meta + job summary
      <output_dir>/<case_id>/case.log    logging output of the case process
      <output_dir>/batch.json            batch summary, written last

  The job may write any other file into its case directory (Record, figures).
* **Run meta.** A job that runs an engine returns the dict of
  :func:`outrigger_sim.record.make_run_meta` as :attr:`CaseResult.run_meta`; it must hold
  :data:`REQUIRED_RUN_META_KEYS` (``Params.sha256`` / ``file_sha256``, reference SHA-256,
  ``dt_s``, solver, ``input_lag_steps``, versions). The runner adds the wall clock, the
  process placement and the status (``case.json`` key ``runner``).

Job contract: ``job(case, case_dir) -> CaseResult``, a **module-level function** (spawn sends
it by import path; lambdas and closures are rejected before any process starts). Every
value in the result must be JSON-serialisable.
"""

from __future__ import annotations

import json
import logging
import math
import multiprocessing
import os
import pickle
import platform
import re
import time
import traceback
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from multiprocessing.connection import wait
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any

from outrigger_sim.hostcpu import cpu_sets, place_process

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 4
CASE_META_NAME = "case.json"
CASE_LOG_NAME = "case.log"
BATCH_META_NAME = "batch.json"
BATCH_FORMAT = "outrigger_sim.batch"
TIMEOUT_REASON = "timeout"
PROCESS_EXIT_REASON = "process_exit"
FORMAT_VERSION = 1

REQUIRED_RUN_META_KEYS: tuple[str, ...] = (
    "params_sha256",
    "params_file_sha256",
    "reference_sha256",
    "dt_s",
    "solver",
    "input_lag_steps",
    "versions",
)
"""Keys of :func:`outrigger_sim.record.make_run_meta` a case's run meta must contain."""

# Case ids become directory names: letters, digits, '.', '_' and '-' only.
_CASE_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class Placement(StrEnum):
    """Core placement of the case processes (:func:`outrigger_sim.hostcpu.place_process`)."""

    PCORE = "pcore"
    ECORE = "ecore"
    OS = "os"


class CaseStatus(StrEnum):
    """Outcome of one case."""

    OK = "ok"
    FAILED = "failed"


@dataclass(frozen=True)
class Case:
    """One unit of work.

    Attributes:
        case_id: Unique name, also the case directory name (``[A-Za-z0-9._-]+``).
        settings: JSON-serialisable arguments for the job (scenario, level, dt, ...).
    """

    case_id: str
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        is_valid_name = isinstance(self.case_id, str) and _CASE_ID_PATTERN.fullmatch(self.case_id)
        if not is_valid_name or self.case_id in (".", ".."):
            raise ValueError(f"case_id must match [A-Za-z0-9._-]+, got {self.case_id!r}")


@dataclass(frozen=True)
class CaseResult:
    """What a job returns.

    Attributes:
        summary: JSON-serialisable results (check values, key numbers, file names).
        run_meta: :func:`outrigger_sim.record.make_run_meta` output for a job that ran an
            engine, ``None`` for a job without one (post-processing).
    """

    summary: Mapping[str, Any] = field(default_factory=dict)
    run_meta: Mapping[str, Any] | None = None


Job = Callable[[Case, Path], CaseResult]


@dataclass(frozen=True)
class CaseOutcome:
    """Result of one case as seen by the parent process.

    Attributes:
        case_id: The case.
        status: ``ok`` or ``failed``.
        wall_s: Wall time from process start to process end (spawn and imports included).
        exit_code: Exit code of the case process.
        error: Traceback or reason if failed, else ``None``.
        case_dir: Case directory.
        document: Contents of ``case.json``.
    """

    case_id: str
    status: CaseStatus
    wall_s: float
    exit_code: int | None
    error: str | None
    case_dir: Path
    document: Mapping[str, Any]


@dataclass(frozen=True)
class BatchReport:
    """All outcomes in the order of the input cases, and the ``batch.json`` path."""

    outcomes: tuple[CaseOutcome, ...]
    batch_meta_path: Path

    @property
    def failed_case_ids(self) -> list[str]:
        """Ids of the failed cases."""
        return [outcome.case_id for outcome in self.outcomes if outcome.status is CaseStatus.FAILED]

    @property
    def is_all_ok(self) -> bool:
        """Whether every case succeeded."""
        return not self.failed_case_ids


@dataclass
class _RunningCase:
    case: Case
    case_dir: Path
    process: BaseProcess
    start_s: float
    timeout_s: float | None
    is_timed_out: bool = False

    def seconds_left(self, now_s: float) -> float | None:
        """Time until the timeout (may be negative), ``None`` without a timeout."""
        if self.timeout_s is None:
            return None
        return self.start_s + self.timeout_s - now_s


# --- small helpers -----------------------------------------------------------------------


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_text_atomically(path: Path, text: str) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _json_text(document: Mapping[str, Any]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False, allow_nan=True) + "\n"


def _job_name(job: Job) -> str:
    return f"{getattr(job, '__module__', '?')}.{getattr(job, '__qualname__', repr(job))}"


def _check_result(result: object) -> CaseResult:
    if not isinstance(result, CaseResult):
        raise TypeError(f"job must return CaseResult, got {type(result).__name__}")
    if result.run_meta is not None:
        missing = [key for key in REQUIRED_RUN_META_KEYS if key not in result.run_meta]
        if missing:
            raise ValueError(f"run_meta lacks {missing} (use record.make_run_meta)")
    return result


def _attach_case_log(case_dir: Path) -> logging.Handler:
    handler = logging.FileHandler(case_dir / CASE_LOG_NAME, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler


# --- case process ------------------------------------------------------------------------


def _case_document(
    case: Case,
    runner_meta: Mapping[str, Any],
    result: CaseResult | None,
) -> dict[str, Any]:
    return {
        "format": BATCH_FORMAT,
        "format_version": FORMAT_VERSION,
        "case_id": case.case_id,
        "settings": dict(case.settings),
        "runner": dict(runner_meta),
        "run_meta": None if result is None or result.run_meta is None else dict(result.run_meta),
        "summary": None if result is None else dict(result.summary),
    }


def _run_job(job: Job, case: Case, case_dir: Path) -> tuple[CaseResult | None, str | None]:
    try:
        return _check_result(job(case, case_dir)), None
    except Exception:  # isolation: any job failure fails this case only, never the batch
        logger.exception("case %s failed", case.case_id)
        return None, traceback.format_exc()


def _run_case_process(job: Job, case: Case, case_dir: Path, placement: Placement) -> None:
    """Entry point of a case process: place, run the job, write ``case.json``."""
    _attach_case_log(case_dir)
    started_utc = _utc_now_text()
    placement_info = place_process(placement.value)
    logger.info("case %s started, placement %s", case.case_id, placement_info)
    start_s = time.perf_counter()
    result, error = _run_job(job, case, case_dir)
    runner_meta = {
        "status": (CaseStatus.OK if error is None else CaseStatus.FAILED).value,
        "error": error,
        "job": _job_name(job),
        "started_utc": started_utc,
        "job_wall_s": time.perf_counter() - start_s,
        "pid": os.getpid(),
        "placement": placement_info,
    }
    try:
        text = _json_text(_case_document(case, runner_meta, result))
    except (TypeError, ValueError) as json_error:
        logger.exception("case %s: result is not JSON-serialisable", case.case_id)
        runner_meta |= {
            "status": CaseStatus.FAILED.value,
            "error": f"result is not JSON-serialisable: {json_error}",
        }
        text = _json_text(_case_document(case, runner_meta, None))
    _write_text_atomically(case_dir / CASE_META_NAME, text)
    logger.info("case %s finished: %s", case.case_id, runner_meta["status"])


# --- parent side -------------------------------------------------------------------------


def _check_inputs(cases: list[Case], job: Job, output_dir: Path, max_workers: int) -> None:
    if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
        raise ValueError(f"max_workers must be an int >= 1, got {max_workers!r}")
    case_ids = [case.case_id for case in cases]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate case ids {duplicates}")
    try:
        pickle.dumps(job)
    except (pickle.PicklingError, AttributeError, TypeError) as error:
        raise TypeError(f"job must be a module-level function: {error}") from None
    existing = [name for name in [*case_ids, BATCH_META_NAME] if (output_dir / name).exists()]
    if existing:
        raise FileExistsError(f"case directories already exist in {output_dir}: {existing}")


def _start_case(
    context: multiprocessing.context.SpawnContext,
    job: Job,
    case: Case,
    output_dir: Path,
    placement: Placement,
    timeout_s: float | None,
) -> _RunningCase:
    case_dir = output_dir / case.case_id
    case_dir.mkdir()
    process = context.Process(
        target=_run_case_process,
        args=(job, case, case_dir, placement),
        name=f"case-{case.case_id}",
    )
    start_s = time.perf_counter()
    process.start()
    logger.info("started case %s (pid %s)", case.case_id, process.pid)
    return _RunningCase(case, case_dir, process, start_s, timeout_s)


def _read_case_document(running: _RunningCase, exit_code: int | None) -> dict[str, Any]:
    """``case.json`` of a finished case; written here if the process died before writing."""
    path = running.case_dir / CASE_META_NAME
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if running.is_timed_out:
        runner_meta = {
            "status": CaseStatus.FAILED.value,
            "reason": TIMEOUT_REASON,
            "error": f"{TIMEOUT_REASON}: no result after {running.timeout_s} s, process terminated",
        }
    else:
        runner_meta = {
            "status": CaseStatus.FAILED.value,
            "reason": PROCESS_EXIT_REASON,
            "error": f"case process exited with code {exit_code} before writing {CASE_META_NAME}",
        }
    document = _case_document(running.case, runner_meta, None)
    _write_text_atomically(path, _json_text(document))
    return document


def _finish_case(running: _RunningCase) -> CaseOutcome:
    running.process.join()
    wall_s = time.perf_counter() - running.start_s
    exit_code = running.process.exitcode
    document = _read_case_document(running, exit_code)
    runner_meta = document["runner"]
    status = CaseStatus(runner_meta["status"])
    if exit_code != 0:
        logger.warning("case %s: process exit code %s", running.case.case_id, exit_code)
    if status is CaseStatus.FAILED:
        logger.error("case %s failed: %s", running.case.case_id, runner_meta["error"])
    else:
        logger.info("case %s ok (%.1f s)", running.case.case_id, wall_s)
    return CaseOutcome(
        case_id=running.case.case_id,
        status=status,
        wall_s=wall_s,
        exit_code=exit_code,
        error=runner_meta["error"],
        case_dir=running.case_dir,
        document=document,
    )


def _terminate_timed_out(running: dict[int, _RunningCase]) -> list[int]:
    """Terminate every case past its timeout; return their sentinels."""
    now_s = time.perf_counter()
    expired = []
    for sentinel, item in running.items():
        seconds_left = item.seconds_left(now_s)
        if seconds_left is not None and seconds_left <= 0.0 and item.process.is_alive():
            logger.error(
                "case %s: timeout after %s s, terminating", item.case.case_id, item.timeout_s
            )
            item.is_timed_out = True
            item.process.terminate()
            expired.append(sentinel)
    return expired


def _wait_timeout_s(running: dict[int, _RunningCase]) -> float | None:
    """How long to wait for a process end before checking the timeouts again."""
    now_s = time.perf_counter()
    left = [item.seconds_left(now_s) for item in running.values()]
    deadlines = [seconds for seconds in left if seconds is not None]
    return max(0.0, min(deadlines)) if deadlines else None


def _check_timeout(timeout_s: float | None) -> None:
    if timeout_s is None:
        return
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, int | float):
        raise ValueError(f"timeout_s must be a number of seconds or None, got {timeout_s!r}")
    if not math.isfinite(timeout_s) or timeout_s <= 0.0:
        raise ValueError(f"timeout_s must be > 0, got {timeout_s!r}")


def _error_summary(error: str | None) -> str | None:
    """Last line of a traceback (the exception), or the whole reason."""
    if error is None:
        return None
    lines = error.strip().splitlines()
    return lines[-1] if lines else error


def _batch_document(
    outcomes: list[CaseOutcome],
    job: Job,
    started_utc: str,
    wall_s: float,
    max_workers: int,
    placement: Placement,
) -> dict[str, Any]:
    case_rows = [
        {
            "case_id": outcome.case_id,
            "status": outcome.status.value,
            "wall_s": outcome.wall_s,
            "exit_code": outcome.exit_code,
            "error": _error_summary(outcome.error),
        }
        for outcome in outcomes
    ]
    failed_count = sum(outcome.status is CaseStatus.FAILED for outcome in outcomes)
    return {
        "format": BATCH_FORMAT,
        "format_version": FORMAT_VERSION,
        "job": _job_name(job),
        "started_utc": started_utc,
        "finished_utc": _utc_now_text(),
        "wall_s": wall_s,
        "max_workers": max_workers,
        "placement": placement.value,
        "host": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_efficiency_classes": sorted({cpu["efficiency_class"] for cpu in cpu_sets()}),
        },
        "counts": {"ok": len(outcomes) - failed_count, "failed": failed_count},
        "cases": case_rows,
    }


def run_cases(
    cases: Iterable[Case],
    job: Job,
    output_dir: str | Path,
    *,
    max_workers: int = DEFAULT_MAX_WORKERS,
    placement: Placement | str = Placement.PCORE,
    timeout_s: float | None = None,
) -> BatchReport:
    """Run every case in its own process, at most ``max_workers`` at a time.

    Args:
        cases: Cases to run, in start order.
        job: Module-level function ``job(case, case_dir) -> CaseResult``.
        output_dir: Directory for the case directories and ``batch.json``.
        max_workers: Maximum number of case processes at a time.
        placement: Core placement of every case process.
        timeout_s: Wall-time limit per case, counted from its process start (spawn and
            imports included); a case still running then is terminated and marked
            ``failed`` with reason ``timeout``. ``None`` = no limit.

    Returns:
        Outcomes in the order of ``cases``.

    Raises:
        ValueError: ``max_workers`` < 1, ``timeout_s`` <= 0 or duplicate case ids.
        TypeError: ``job`` cannot be sent to a process (lambda, closure, local function).
        FileExistsError: A case directory or ``batch.json`` exists already (nothing has
            been started).
    """
    case_list = list(cases)
    output_path = Path(output_dir)
    placement = Placement(placement)
    _check_timeout(timeout_s)
    _check_inputs(case_list, job, output_path, max_workers)
    output_path.mkdir(parents=True, exist_ok=True)

    context = multiprocessing.get_context("spawn")
    started_utc = _utc_now_text()
    batch_start_s = time.perf_counter()
    pending = deque(case_list)
    running: dict[int, _RunningCase] = {}
    outcomes: dict[str, CaseOutcome] = {}
    while pending or running:
        while pending and len(running) < max_workers:
            started = _start_case(
                context, job, pending.popleft(), output_path, placement, timeout_s
            )
            running[started.process.sentinel] = started
        ended = wait(list(running), timeout=_wait_timeout_s(running))
        for sentinel in {*ended, *_terminate_timed_out(running)}:
            finished = running.pop(sentinel)
            outcomes[finished.case.case_id] = _finish_case(finished)

    ordered = [outcomes[case.case_id] for case in case_list]
    wall_s = time.perf_counter() - batch_start_s
    document = _batch_document(ordered, job, started_utc, wall_s, max_workers, placement)
    batch_meta_path = output_path / BATCH_META_NAME
    _write_text_atomically(batch_meta_path, _json_text(document))
    logger.info("batch finished: %s", document["counts"])
    return BatchReport(outcomes=tuple(ordered), batch_meta_path=batch_meta_path)
