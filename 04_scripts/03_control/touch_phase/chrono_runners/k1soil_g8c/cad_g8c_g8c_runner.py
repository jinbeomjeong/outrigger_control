"""Slot runner of the G8C3 batch: 3 slots by default, default rows E1 R2 R3 R2L1 R3L1 (run_g8c_case.py).

Each row: job_exec.py (memory 6144 MB, kill on close, ends with this runner), OMP_NUM_THREADS=4, OUTRIGGER_PLACEMENT=pcore.
Reservation scm-G8C3 on the P mask, released at the end. A rerun skips rows with result.json; a folder without it (interrupted row)
moves to _interrupted_<stamp> and the row runs again. Refuses to start while the K1 soil runner lives. Python-dev interpreter (psutil).
Usage: python -I -B -X utf8 -u g8c_runner.py [--rows E1 R2 R3 R2L1 R3L1] [--slots 3|4|5]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
CHRONO_PY = r"C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
DEV_PY = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe"
TOOLS = Path(r"C:\Users\jinbeom\.claude\tools\cpu-scheduler")
CASE = HERE / "run_g8c_case.py"
BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_g8c3_20261105")
LOGS = HERE / "logs"
NAMES = {"E1": "G8C3_top_edge_RL_g230_C4G2", "R2": "G8CL2b_top_rpB_RL_g230_Fs4_off", "R3": "G8CL2b_top_rpB_RL_g230_Fs4_C4G2",
         "R2L1": "G8C3_top_rpB_RL_g230_off", "R3L1": "G8C3_top_rpB_RL_g230_C4G2", "E0L2": "G8CL2b_top_edge_RL_g230_Fs4_off", "E1L2": "G8CL2b_top_edge_RL_g230_Fs4_C4G2"}
DEFAULT_ROWS = ("E1", "R2", "R3", "R2L1", "R3L1")
SLOTS = 3
"""Default; --slots 5 is fine once K1 soil has ended (one thread and about 0.5 GB per row, 8 physical P-cores)."""
MEMORY_MB = 6144
TTL_MIN = 120
"""Worst case about 20 min per row (L2b FAULT row to the upper bound 134 s + settles, 8.6 s/s); margin for a loaded pool."""
K1_MARK = "k1soil_runner.py"
POLL_S = 5.0


def say(msg: str) -> None:
    line = f"{time.strftime('%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with (LOGS / "runner.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def k1_running() -> list[int]:
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            if K1_MARK in " ".join(p.info["cmdline"] or []):
                out.append(p.info["pid"])
        except psutil.Error:
            pass
    return out


def tool(*args: str) -> dict:
    r = subprocess.run([DEV_PY, "-I", str(TOOLS / "reserve.py"), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        say(f"reserve {args[0]} rc {r.returncode}: {r.stderr[-300:]}")
        return {}
    return json.loads(r.stdout)


def start_row(row: str) -> subprocess.Popen:
    cmd = [DEV_PY, "-I", str(TOOLS / "job_exec.py"), "--memory-mb", str(MEMORY_MB), "--kill-on-close", "--runner-pid", str(os.getpid()), "--",
           CHRONO_PY, "-I", "-B", "-X", "utf8", "-u", str(CASE), "--row", row]
    env = dict(os.environ, OMP_NUM_THREADS="4", OUTRIGGER_PLACEMENT="pcore", PYTHONIOENCODING="utf-8")
    env.pop("OUTRIGGER_RUN_PLACEMENT", None)
    log = (LOGS / f"{row}_{NAMES[row]}.log").open("a", encoding="utf-8")
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(HERE))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="+", choices=tuple(NAMES), default=list(DEFAULT_ROWS))
    ap.add_argument("--slots", type=int, choices=(3, 4, 5), default=SLOTS)
    me = ap.parse_args()
    LOGS.mkdir(exist_ok=True)
    k1 = k1_running()
    if k1:
        say(f"refused: the K1 soil runner is alive, pids {k1}")
        sys.exit(2)
    BATCH.mkdir(parents=True, exist_ok=True)
    res = tool("add", "--owner", "scm-G8C3", "--mask", "0xFFFF", "--pid", str(os.getpid()), "--ttl-min", str(TTL_MIN), "--note", f"G8C3 {len(me.rows)} Chrono rows, rigid floor, {me.slots} slots")
    rid = res.get("id") or (res.get("reservation") or {}).get("id")
    say(f"reservation {rid}; runner pid {os.getpid()}; rows {me.rows}")
    queue = list(me.rows)
    running: dict[str, tuple[subprocess.Popen, float]] = {}
    finished: list[str] = []
    stopped: list[str] = []
    try:
        while queue or running:
            for row, (proc, t0) in list(running.items()):
                rc = proc.poll()
                if rc is None:
                    continue
                del running[row]
                ok = (BATCH / NAMES[row] / "result.json").exists() and (BATCH / NAMES[row] / "g8c_job_side.json").exists()
                say(f"finished {row} {NAMES[row]} rc {rc} wall {time.monotonic() - t0:.0f} s result {ok}")
                (finished if rc == 0 and ok else stopped).append(row)
                if row in stopped:
                    say(f"STOP {row}: see logs\\{row}_{NAMES[row]}.log")
            while queue and len(running) < me.slots:
                row = queue.pop(0)
                d = BATCH / NAMES[row]
                if (d / "result.json").exists():
                    say(f"skip {row}: result.json exists")
                    finished.append(row)
                    continue
                if d.exists():
                    aside = d.with_name(f"_interrupted_{time.strftime('%H%M%S')}_{d.name}")
                    d.rename(aside)
                    say(f"{row}: folder without result.json moved to {aside.name}")
                running[row] = (start_row(row), time.monotonic())
                say(f"started {row} {NAMES[row]} pid {running[row][0].pid} running {len(running)}")
            time.sleep(POLL_S)
    finally:
        if rid:
            tool("release", "--id", rid)
    say(f"done; finished {finished}; stopped {stopped}")
    sys.exit(1 if stopped else 0)


if __name__ == "__main__":
    main()
