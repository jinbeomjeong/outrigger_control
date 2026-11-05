"""One row runner of S9EV_G1_FLFs0_RE1bF_d003_C4G2: reservation scm-K1d003, job_exec memory 6144 MB and kill on close, 4 threads, P pool.

Python-dev interpreter. Log logs\\d003_S9EV_G1_FLFs0_RE1bF_d003_C4G2.log, runner lines in logs\\runner_d003.log.
Usage: python -I -B -X utf8 -u k1d003_runner.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHRONO_PY = r"C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
DEV_PY = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe"
TOOLS = Path(r"C:\Users\jinbeom\.claude\tools\cpu-scheduler")
LOGS = HERE / "logs"
CASE = "S9EV_G1_FLFs0_RE1bF_d003_C4G2"
RESULT = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105") / CASE / "result.json"
TTL_MIN = 300
MASK = "0x55"
"""Batch table: P physical cores 0 to 3, logical 0, 2, 4, 6; run_k1d003.py applies it after run_S9.place."""


def say(msg: str) -> None:
    line = f"{time.strftime('%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with (LOGS / "runner_d003.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> None:
    r = subprocess.run([DEV_PY, "-I", str(TOOLS / "reserve.py"), "add", "--owner", "scm-K1d003", "--mask", MASK, "--pid", str(os.getpid()), "--ttl-min", str(TTL_MIN), "--note", "K1 soil d003 C4G2, 4 threads"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    rid = json.loads(r.stdout).get("id") if r.returncode == 0 else None
    say(f"reservation {rid} rc {r.returncode}; runner pid {os.getpid()}")
    cmd = [DEV_PY, "-I", str(TOOLS / "job_exec.py"), "--memory-mb", "6144", "--kill-on-close", "--runner-pid", str(os.getpid()), "--", CHRONO_PY, "-I", "-B", "-X", "utf8", "-u", str(HERE / "run_k1d003.py")]
    env = dict(os.environ, OMP_NUM_THREADS="4", OUTRIGGER_PLACEMENT="pcore", K1D003_MASK=MASK, PYTHONIOENCODING="utf-8")
    t0 = time.monotonic()
    try:
        with (LOGS / f"d003_{CASE}.log").open("a", encoding="utf-8") as log:
            rc = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(HERE)).returncode
    finally:
        if rid:
            subprocess.run([DEV_PY, "-I", str(TOOLS / "reserve.py"), "release", "--id", rid], capture_output=True, stdin=subprocess.DEVNULL)
    say(f"finished rc {rc} wall {time.monotonic() - t0:.0f} s result {RESULT.exists()}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
