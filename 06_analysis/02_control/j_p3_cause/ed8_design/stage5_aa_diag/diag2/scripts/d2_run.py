"""436.9 edition 8 stage-5 A/A diagnosis 2: run V0 jobs with a harness gyro mode (record only).

Each job runs in its own spawned worker (``run_v5.run_one`` of the diagnostic worktree, as
the stage-5 batch did). Gyro modes (the harness switch ``R51_DIAG_GYRO_SAMPLES`` of
``r51_reapp_closed_loop.control_period``):
  off     switch unset: the current harness (no gyro samples)
  all     switch on: ``imu_angular_rate_samples_rad_s`` reaches every controller consumer
          (D1'' lever term and the DSb75 gyro window)
  d1only  switch on, and the DSb75 gyro window is fed as with the switch off (the samples
          are dropped from its input only), so only D1'' sees the samples
Not a judgement; the output is a design input of edition 9.

Usage (dynamics-dev):
  python.exe -I -B d2_run.py --worktree <ed8-diag> --jobs <jobs.json> --gyro off|all|d1only
      --out-jsonl <runs.jsonl> [--trace-dir <folder>] [--mask HEX] [--workers N]

``--trace-dir`` turns the D1 trace on and writes ``trace_<label>.json`` there. Refuses
outputs that exist. Exit codes: 0 every run finished, 1 a run returned an error, 2 input error.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
GYRO_SWITCH = "R51_DIAG_GYRO_SAMPLES"
GYRO_MODES = ("off", "all", "d1only")
RUN_V5_RELATIVE = Path("04_scripts") / "04_hydraulic" / "coupled" / "run_v5.py"
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")


def _load_run_v5(worktree: Path):
    """``run_v5`` of the worktree; importing it puts the worktree's ``03_src`` first."""
    spec = importlib.util.spec_from_file_location("run_v5", worktree / RUN_V5_RELATIVE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_v5"] = module
    spec.loader.exec_module(module)
    return module


def _keep_diff_sink_off_gyro() -> None:
    """``d1only``: the DSb75 gyro window gets the measurements without gyro samples."""
    from outrigger_sim.control import c2

    original = c2.C2Controller._diff_sink_feed_gyro

    def feed_without_samples(self, measurements):
        original(self, dataclasses.replace(measurements, imu_angular_rate_samples_rad_s=None))

    c2.C2Controller._diff_sink_feed_gyro = feed_without_samples


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


def traced_run(job: dict, is_trace_on: bool, gyro_mode: str, worktree: str) -> dict:
    """Worker: one ``run_one``; the record (+ the trace when on)."""
    run_v5 = _load_run_v5(Path(worktree))
    from outrigger_sim.control import two_pressure

    if gyro_mode == "d1only":
        _keep_diff_sink_off_gyro()
    trace = two_pressure.start_d1_trace() if is_trace_on else None
    record = run_v5.run_one(dict(job))
    stopped = two_pressure.stop_d1_trace()
    if is_trace_on and stopped is not trace:
        raise RuntimeError("the D1 trace was replaced during the run")
    for key in RUNTIME_JOB_KEYS:
        record["job"].pop(key, None)
    r51 = sys.modules.get("r51_reapp_closed_loop")
    record["diag"] = {"gyro_mode": gyro_mode, "trace": is_trace_on,
                      "two_pressure_file": two_pressure.__file__,
                      "r51_file": None if r51 is None else r51.__file__,
                      "r51_gyro_switch": None if r51 is None else r51.DIAG_GYRO_SAMPLES}
    payload = {"record": record}
    if trace is not None:
        payload["trace"] = {"monitors": trace.monitors, "rows": trace.rows}
    return json.loads(json.dumps(payload, default=_json_default))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True, help="[{label, job, ...}]")
    parser.add_argument("--gyro", choices=GYRO_MODES, required=True)
    parser.add_argument("--out-jsonl", type=Path, required=True)
    parser.add_argument("--trace-dir", type=Path, default=None)
    parser.add_argument("--mask", default=None, help="hex affinity mask of the workers")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    if not (args.worktree / RUN_V5_RELATIVE).is_file():
        parser.error(f"no {RUN_V5_RELATIVE} under {args.worktree}")
    if not os.environ.get("NUMBA_CACHE_DIR"):
        parser.error("set NUMBA_CACHE_DIR (a new folder) before the run")
    if os.environ.get(GYRO_SWITCH) is not None:
        parser.error(f"{GYRO_SWITCH} is set outside; --gyro sets it")
    return args


def main(argv: list[str] | None = None) -> int:
    for name in THREAD_VARIABLES:
        os.environ[name] = "1"
    os.environ["MKL_THREADING_LAYER"] = "TBB"
    args = _parse_args(argv)
    entries = json.loads(args.jobs.read_text(encoding="utf-8"))
    is_trace_on = args.trace_dir is not None
    traces = [] if not is_trace_on else [args.trace_dir / f"trace_{e['label']}.json"
                                         for e in entries]
    existing = [str(p) for p in [args.out_jsonl, args.out_jsonl.with_suffix(".log.json"),
                                 *traces] if p.exists()]
    if existing:
        print(f"refusing to overwrite {existing}")
        return 2
    if args.gyro != "off":
        os.environ[GYRO_SWITCH] = "on"  # before the pool: the spawned workers inherit it
    mask = None if args.mask is None else int(args.mask, 16)  # run_one pins each worker
    log = {"argv": sys.argv, "python": sys.executable, "gyro_mode": args.gyro,
           "started": time.strftime("%Y-%m-%d %H:%M:%S %z"), "mask": args.mask,
           "workers": args.workers,
           "environment": {name: os.environ.get(name) for name in
                           (*THREAD_VARIABLES, "MKL_THREADING_LAYER", "NUMBA_CACHE_DIR",
                            GYRO_SWITCH)}, "runs": []}
    tasks = [({**entry["job"], "mask": mask, "t4h_dir": None}, is_trace_on, args.gyro,
              str(args.worktree)) for entry in entries]
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool:
        payloads = pool.starmap(traced_run, tasks, chunksize=1)
    if is_trace_on:
        args.trace_dir.mkdir(parents=True, exist_ok=True)
    has_error = False
    with args.out_jsonl.open("x", encoding="utf-8") as handle:
        for entry, payload, trace_path in zip(entries, payloads, traces or [None] * len(entries),
                                              strict=True):
            record = {"label": entry["label"], **payload["record"]}
            handle.write(json.dumps(record) + "\n")
            if trace_path is not None:
                with trace_path.open("x", encoding="utf-8") as trace_handle:
                    json.dump(payload["trace"], trace_handle)
            has_error |= "error" in record
            state = record.get("error") or (
                f"{record['final_phase']} {record['commands_sha256'][:12]}")
            log["runs"].append({"label": entry["label"], "wall_s": record.get("wall_s"),
                                "state": state[:300]})
            print(f"{entry['label']} gyro={args.gyro} trace={is_trace_on}: {state[:120]}",
                  flush=True)
    log["done"] = time.strftime("%Y-%m-%d %H:%M:%S %z")
    with args.out_jsonl.with_suffix(".log.json").open("x", encoding="utf-8") as handle:
        json.dump(log, handle, indent=1)
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
