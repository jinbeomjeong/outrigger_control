"""R3c (control ``ed9_design/control_cm_switch/report.md`` 2.3): run the 59 diagnosis V0 jobs
with C-m off or on, optionally with the D1 trace (record only; not a judgement).

Each job runs in its own spawned worker with ``run_v5.run_one`` of ``--worktree`` (the C9
worktree for the plain runs, the trace worktree for ``--trace-dir``). The C-m state is the
edition 9 batch switch: ``verdict_runs.install_d1_median`` in the worker before the run (as
``run_v5``'s pool initializer does), so the line carries the ``_CM`` tag and the
``d1_settings`` record exactly as a C-m batch line. The harness gyro stays off (the default;
the gyro variants B / C of edition 8 diagnosis 2 are optional records, not run here).

Usage (dynamics-dev ``python.exe -I -B``; ``NUMBA_CACHE_DIR`` set to a new folder outside the
worktree)::

    python r3c_run.py --worktree <C9' or trace worktree> --expect-head <40-char commit>
        --jobs <r3c_jobs.json> --d1-median off|on --out-jsonl <runs.jsonl>
        [--trace-dir <folder>] [--mask HEX] [--workers N]

Writes ``--out-jsonl`` (one line per job, ``label`` first), ``<out>.log.json`` (argv,
interpreter, environment, worktree HEAD at the start and the end, per-run wall time) and with
``--trace-dir`` ``trace_<label>.json``. Refuses outputs that exist. ``--expect-head`` (audit
M-5): the worktree must be at that commit with no tracked change at the start (else nothing
runs) and at the end (else the written lines are not of that code).

Exit codes: 0 every run finished; 1 a run returned an error; 2 input error (an existing output,
a bad argument, or the worktree not at ``--expect-head`` / with a tracked change at the start or
the end; an end problem leaves the outputs and records ``head_problem`` in the log).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from multiprocessing import get_context
from pathlib import Path

FULL_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
RUN_V5_RELATIVE = Path("04_scripts") / "04_hydraulic" / "coupled" / "run_v5.py"
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")
SWITCH_STATES = {"off": False, "on": True}


def _load_run_v5(worktree: Path):
    """``run_v5`` of the worktree; importing it puts the worktree's ``03_src`` first."""
    spec = importlib.util.spec_from_file_location("run_v5", worktree / RUN_V5_RELATIVE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_v5"] = module
    spec.loader.exec_module(module)
    return module


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


def run_job(job: dict, is_d1_median: bool, is_trace_on: bool, worktree: str) -> dict:
    """Worker: the C-m state, then one ``run_one`` (+ the trace when on)."""
    run_v5 = _load_run_v5(Path(worktree))
    import verdict_runs  # noqa: I001 - after run_v5 put the worktree's paths first
    from outrigger_sim.control import two_pressure

    verdict_runs.install_d1_median(is_d1_median)
    if is_trace_on and not hasattr(two_pressure, "start_d1_trace"):
        raise RuntimeError(f"{two_pressure.__file__} has no D1 trace (use the trace worktree)")
    trace = two_pressure.start_d1_trace() if is_trace_on else None
    record = run_v5.run_one(dict(job))
    if is_trace_on and two_pressure.stop_d1_trace() is not trace:
        raise RuntimeError("the D1 trace was replaced during the run")
    for key in RUNTIME_JOB_KEYS:
        record["job"].pop(key, None)
    record["diag"] = {"d1_median": is_d1_median, "trace": is_trace_on,
                      "two_pressure_file": two_pressure.__file__,
                      "run_v5_file": run_v5.__file__}
    payload = {"record": record}
    if trace is not None:
        payload["trace"] = {"monitors": trace.monitors, "rows": trace.rows}
    return json.loads(json.dumps(payload, default=_json_default))


def _git_head(worktree: Path) -> dict:
    """HEAD and whether tracked files are unchanged; None for a git call that failed (never
    read as clean)."""
    def git(*arguments):
        done = subprocess.run(["git", "-C", str(worktree), *arguments], capture_output=True,
                              text=True, timeout=120, check=False)
        return done.stdout.strip() if done.returncode == 0 else None

    status = git("status", "--porcelain", "--untracked-files=no")
    return {"head": git("rev-parse", "HEAD"),
            "is_clean": None if status is None else status == ""}


def head_problem(state: dict, expected_head: str, moment: str) -> str | None:
    """Audit M-5: the worktree is at ``expected_head`` with no tracked change (a failed git
    call is a problem, never a clean tree)."""
    if state.get("head") is None or state.get("is_clean") is None:
        return f"{moment}: git HEAD / status could not be read"
    if state["head"] != expected_head:
        return f"{moment}: HEAD {state['head']} is not the expected {expected_head}"
    if state["is_clean"] is not True:
        return f"{moment}: tracked files changed"
    return None


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True, help="[{label, job, ...}]")
    parser.add_argument("--d1-median", choices=sorted(SWITCH_STATES), required=True)
    parser.add_argument("--out-jsonl", type=Path, required=True)
    parser.add_argument("--trace-dir", type=Path, default=None)
    parser.add_argument("--mask", default=None, help="hex affinity mask of the workers")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--expect-head", required=True,
                        help="the 40-character commit the worktree must be at, clean, at the "
                             "start and the end (audit M-5)")
    args = parser.parse_args(argv)
    if not (args.worktree / RUN_V5_RELATIVE).is_file():
        parser.error(f"no {RUN_V5_RELATIVE} under {args.worktree}")
    if not FULL_COMMIT_PATTERN.fullmatch(args.expect_head):
        parser.error("--expect-head needs a full 40-character lowercase commit id")
    if not os.environ.get("NUMBA_CACHE_DIR"):
        parser.error("set NUMBA_CACHE_DIR (a new folder) before the run")
    return args


def main(argv: list[str] | None = None) -> int:
    for name in THREAD_VARIABLES:
        os.environ[name] = "1"
    os.environ["MKL_THREADING_LAYER"] = "TBB"
    args = _parse_args(argv)
    entries = json.loads(args.jobs.read_text(encoding="utf-8"))
    is_trace_on = args.trace_dir is not None
    is_d1_median = SWITCH_STATES[args.d1_median]
    traces = [None] * len(entries)
    if is_trace_on:
        traces = [args.trace_dir / f"trace_{entry['label']}.json" for entry in entries]
    outputs = [args.out_jsonl, args.out_jsonl.with_suffix(".log.json"), *filter(None, traces)]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        print(json.dumps({"status": "input_error", "reason": f"refusing {existing[:3]}"}))
        return 2
    start_state = _git_head(args.worktree)
    problem = head_problem(start_state, args.expect_head, "start")
    if problem is not None:  # nothing run, nothing written
        print(json.dumps({"status": "input_error", "reason": problem}))
        return 2
    mask = None if args.mask is None else int(args.mask, 16)  # run_one pins each worker
    log = {"argv": sys.argv, "python": sys.executable, "d1_median": is_d1_median,
           "trace": is_trace_on, "started": time.strftime("%Y-%m-%d %H:%M:%S %z"),
           "mask": args.mask, "workers": args.workers, "expect_head": args.expect_head,
           "worktree": {"path": str(args.worktree), **start_state},
           "environment": {name: os.environ.get(name) for name in
                           (*THREAD_VARIABLES, "MKL_THREADING_LAYER", "NUMBA_CACHE_DIR")},
           "runs": []}
    tasks = [({**entry["job"], "mask": mask, "t4h_dir": None}, is_d1_median, is_trace_on,
              str(args.worktree)) for entry in entries]
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool:
        payloads = pool.starmap(run_job, tasks, chunksize=1)
    if is_trace_on:
        args.trace_dir.mkdir(parents=True, exist_ok=True)
    has_error = False
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("x", encoding="utf-8") as handle:
        for entry, payload, trace_path in zip(entries, payloads, traces, strict=True):
            record = {"label": entry["label"], **payload["record"]}
            handle.write(json.dumps(record) + "\n")
            if trace_path is not None:
                with trace_path.open("x", encoding="utf-8") as trace_handle:
                    json.dump(payload["trace"], trace_handle)
            is_error = "error" in record
            has_error |= is_error
            state = "error" if is_error else "done"  # no result value on the console
            log["runs"].append({"label": entry["label"], "wall_s": record.get("wall_s"),
                                "state": state})
            print(f"{entry['label']} d1_median={args.d1_median} trace={is_trace_on}: {state}",
                  flush=True)
    log["done"] = time.strftime("%Y-%m-%d %H:%M:%S %z")
    log["worktree_end"] = _git_head(args.worktree)
    end_problem = head_problem(log["worktree_end"], args.expect_head, "end")
    log["head_problem"] = end_problem
    with args.out_jsonl.with_suffix(".log.json").open("x", encoding="utf-8") as handle:
        json.dump(log, handle, indent=1)
    if end_problem is not None:  # the lines are written but not of the expected code
        print(json.dumps({"status": "input_error", "reason": end_problem}))
        return 2
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
