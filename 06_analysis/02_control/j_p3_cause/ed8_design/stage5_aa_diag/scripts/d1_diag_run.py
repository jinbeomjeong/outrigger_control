"""436.9 edition 8 stage-5 A/A diagnosis: run V0 jobs with and without the D1 trace (record only).

Each job runs twice in its own spawned worker (``run_v5.run_one`` of the diagnostic worktree,
as the stage-5 batch did): once with the D1 trace off (reproduction check against the stored
stage-5 line) and once with it on (``two_pressure.start_d1_trace``). Not a judgement; the
output is a design input of edition 9.

Usage (dynamics-dev):
  python.exe -I -B d1_diag_run.py --worktree <ed8-diag> --jobs <diag_jobs.json> --out <folder>
      [--mask HEX] [--workers N]

Writes into ``--out`` (refuses files that exist):
  runs_trace_off.jsonl, runs_trace_on.jsonl   one ``run_one`` record per job (+ ``label``,
                                              ``trace``, ``two_pressure_file``)
  trace_<label>.json                          ``D1Trace`` of the traced run (monitors, rows)
  run_log.json                                commands, environment, wall times, exit state

Exit codes: 0 every run finished without error, 1 a run returned an error, 2 input error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
RUN_V5_RELATIVE = Path("04_scripts") / "04_hydraulic" / "coupled" / "run_v5.py"
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")


def _set_thread_environment() -> None:
    """One thread each and the TBB MKL layer, as the stage-5 run (before numpy is imported)."""
    for name in THREAD_VARIABLES:
        os.environ[name] = "1"
    os.environ["MKL_THREADING_LAYER"] = "TBB"


def _load_run_v5(worktree: Path):
    """``run_v5`` of the worktree; importing it puts the worktree's ``03_src`` first."""
    path = worktree / RUN_V5_RELATIVE
    spec = importlib.util.spec_from_file_location("run_v5", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_v5"] = module
    spec.loader.exec_module(module)
    return module


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


def traced_run(job: dict, is_trace_on: bool, worktree: str) -> dict:
    """Worker: one ``run_one`` with the D1 trace on or off; the record and the trace."""
    run_v5 = _load_run_v5(Path(worktree))
    from outrigger_sim.control import two_pressure

    trace = two_pressure.start_d1_trace() if is_trace_on else None
    record = run_v5.run_one(dict(job))
    stopped = two_pressure.stop_d1_trace()
    if is_trace_on and stopped is not trace:
        raise RuntimeError("the D1 trace was replaced during the run")
    for key in RUNTIME_JOB_KEYS:
        record["job"].pop(key, None)
    record["two_pressure_file"] = two_pressure.__file__
    payload = {"record": record}
    if trace is not None:
        payload["trace"] = {"monitors": trace.monitors, "rows": trace.rows}
    return json.loads(json.dumps(payload, default=_json_default))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True,
                        help="diag_jobs.json: [{label, job, stored}]")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mask", default=None, help="hex affinity mask of the workers")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    if not (args.worktree / RUN_V5_RELATIVE).is_file():
        parser.error(f"no {RUN_V5_RELATIVE} under {args.worktree}")
    if not os.environ.get("NUMBA_CACHE_DIR"):
        parser.error("set NUMBA_CACHE_DIR (a new folder) before the run")
    return args


def _refuse_existing(paths: list[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise SystemExit(f"refusing to overwrite: {existing}")


def _run_all(tasks: list[tuple[dict, bool, str]], workers: int) -> list[dict]:
    """Every (job, trace, worktree) in its own spawned worker (``maxtasksperchild=1``: the
    harness patches of a run stay in its process), results in task order."""
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
        return pool.starmap(traced_run, tasks, chunksize=1)


def _write_outputs(out: Path, entries: list[dict], payloads: list[dict], log: dict) -> bool:
    """The two jsonl files and the traces; True when a run returned an error."""
    has_error = False
    by_trace = {False: [], True: []}
    for index, payload in enumerate(payloads):
        is_trace_on = index >= len(entries)
        entry = entries[index % len(entries)]
        record = {"label": entry["label"], "trace": is_trace_on, **payload["record"]}
        by_trace[is_trace_on].append(record)
        if is_trace_on:
            with (out / f"trace_{entry['label']}.json").open("x", encoding="utf-8") as handle:
                json.dump(payload["trace"], handle)
        has_error |= "error" in record
        state = record.get("error") or (
            f"{record['final_phase']} {record['commands_sha256'][:12]}")
        log["runs"].append({"label": entry["label"], "trace": is_trace_on,
                            "wall_s": record.get("wall_s"), "state": state[:300]})
        print(f"{entry['label']} trace={is_trace_on}: {state[:120]}", flush=True)
    for is_trace_on, records in by_trace.items():
        name = "runs_trace_on.jsonl" if is_trace_on else "runs_trace_off.jsonl"
        with (out / name).open("x", encoding="utf-8") as handle:
            handle.writelines(json.dumps(record) + "\n" for record in records)
    return has_error


def main(argv: list[str] | None = None) -> int:
    _set_thread_environment()
    args = _parse_args(argv)
    entries = json.loads(args.jobs.read_text(encoding="utf-8"))
    labels = [entry["label"] for entry in entries]
    out_paths = [args.out / "runs_trace_off.jsonl", args.out / "runs_trace_on.jsonl",
                 args.out / "run_log.json", *(args.out / f"trace_{label}.json"
                                              for label in labels)]
    _refuse_existing(out_paths)
    args.out.mkdir(parents=True, exist_ok=True)
    mask = None if args.mask is None else int(args.mask, 16)  # run_one pins each worker
    log = {"argv": sys.argv, "python": sys.executable,
           "started": time.strftime("%Y-%m-%d %H:%M:%S %z"),
           "environment": {name: os.environ.get(name) for name in
                           (*THREAD_VARIABLES, "MKL_THREADING_LAYER", "NUMBA_CACHE_DIR")},
           "mask": args.mask, "workers": args.workers, "runs": []}
    tasks = [({**entry["job"], "mask": mask, "t4h_dir": None}, is_trace_on, str(args.worktree))
             for is_trace_on in (False, True) for entry in entries]
    payloads = _run_all(tasks, args.workers)
    has_error = _write_outputs(args.out, entries, payloads, log)
    log["done"] = time.strftime("%Y-%m-%d %H:%M:%S %z")
    with (args.out / "run_log.json").open("x", encoding="utf-8") as handle:
        json.dump(log, handle, indent=1)
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
