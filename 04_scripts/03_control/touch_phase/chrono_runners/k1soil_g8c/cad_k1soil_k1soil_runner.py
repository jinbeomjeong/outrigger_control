"""Slot runner of the K1 soil batch: the three base runs first, then each base's event pair at the same event time.

2 slots while the S8 flow-off runs live (process command line), 4 after. Each row: job_exec.py (memory 6144 MB, kill on close, ends with this runner)
around run_k1soil_case.py, OMP_NUM_THREADS=4, OUTRIGGER_PLACEMENT=pcore. After a base: the event-time step, then off (mid@base) and on (t<loop s>).
Reservation scm-K1soil on the P mask, renewed hourly, released at the end. A rerun skips rows with result.json; a folder without it stops the row.
A failed base or a base without DONE stops that row only. Python-dev interpreter (psutil).
Usage: python -I -B -X utf8 -u k1soil_runner.py
"""
from __future__ import annotations

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
CASE = HERE / "run_k1soil_case.py"
BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
LOGS = HERE / "logs"
NAMES = {"B1": "S9EV_G1_FLFs0_base", "1a": "S9EV_G1_FLFs0_RE1bF_on", "1b": "S9EV_G1_FLFs0_RE1bF_off", "B2": "S9EV_G1_FLFs8_base", "2a": "S9EV_G1_FLFs8_RE1bF_on", "2b": "S9EV_G1_FLFs8_RE1bF_off",
         "B3": "S9EV_G1_RRFs0_base", "3a": "S9EV_G1_RRFs0_RE1bF_on", "3b": "S9EV_G1_RRFs0_RE1bF_off"}
AFTER = {"B1": ("1b", "1a"), "B2": ("2b", "2a"), "B3": ("3b", "3a")}
SLOTS_WITH_S8, SLOTS_FREE = 2, 4
MEMORY_MB = 6144
TTL_MIN = 1200
"""Worst-case 16.3 h: bases 2 x 2 h at 2 slots, events 6 x 4.1 h at 2 slots."""
S8_MARK = "s8_off\\run_s8_eps.py"
POLL_S = 15.0
RENEW_S = 3600.0


def say(msg: str) -> None:
    line = f"{time.strftime('%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with (LOGS / "runner.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def s8_running() -> list[int]:
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            if S8_MARK in " ".join(p.info["cmdline"] or []):
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


def start_row(row: str, t_ev: float | None) -> subprocess.Popen:
    cmd = [DEV_PY, "-I", str(TOOLS / "job_exec.py"), "--memory-mb", str(MEMORY_MB), "--kill-on-close", "--runner-pid", str(os.getpid()), "--",
           CHRONO_PY, "-I", "-B", "-X", "utf8", "-u", str(CASE), "--row", row]
    if t_ev is not None:
        cmd += ["--t-ev-loop", repr(t_ev)]
    env = dict(os.environ, OMP_NUM_THREADS="4", OUTRIGGER_PLACEMENT="pcore", PYTHONIOENCODING="utf-8")
    log = (LOGS / f"{row}_{NAMES[row]}.log").open("a", encoding="utf-8")
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(HERE))


def event_time(row: str) -> dict | None:
    r = subprocess.run([CHRONO_PY, "-I", "-B", "-X", "utf8", "-u", str(CASE), "--event-time", row], capture_output=True, text=True, stdin=subprocess.DEVNULL, env=dict(os.environ, OMP_NUM_THREADS="1"), cwd=str(HERE))
    if r.returncode != 0:
        say(f"STOP {row}: no event time, rc {r.returncode}: {(r.stdout + r.stderr)[-500:]}")
        return None
    t = json.loads(r.stdout.strip().splitlines()[-1])
    say(f"{row} event time: LOC {t['t_loc_s']:.3f} DONE {t['t_done_s']:.3f} mid {t['t_mid_s']:.3f} loop-relative {t['t_ev_loop_s']!r}")
    return t


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    BATCH.mkdir(parents=True, exist_ok=True)
    res = tool("add", "--owner", "scm-K1soil", "--mask", "0xFFFF", "--pid", str(os.getpid()), "--ttl-min", str(TTL_MIN), "--note", "K1 soil 9 rows, up to 4 x 4 threads")
    rid = res.get("id") or (res.get("reservation") or {}).get("id")
    say(f"reservation {rid}; runner pid {os.getpid()}")
    queue: list[tuple[str, float | None]] = [("B1", None), ("B2", None), ("B3", None)]
    running: dict[str, tuple[subprocess.Popen, float]] = {}
    stopped: list[str] = []
    finished: list[str] = []
    last_slots, last_renew = None, time.monotonic()

    def done_base(b: str) -> None:
        t = event_time(b)
        if t is None:
            stopped.extend([b, *AFTER[b]])
            return
        off, on = AFTER[b]
        queue.extend([(off, None), (on, float(t["t_ev_loop_s"]))])

    try:
        while queue or running:
            for row, (proc, t0) in list(running.items()):
                rc = proc.poll()
                if rc is None:
                    continue
                del running[row]
                has_result = (BATCH / NAMES[row] / "result.json").exists()
                say(f"finished {row} {NAMES[row]} rc {rc} wall {time.monotonic() - t0:.0f} s result {has_result}")
                if rc != 0 or not has_result:
                    stopped.extend([row, *AFTER.get(row, ())])
                    say(f"STOP {row}: see logs\\{row}_{NAMES[row]}.log; its rows do not start")
                else:
                    finished.append(row)
                    if row in AFTER:
                        done_base(row)
            s8 = s8_running()
            slots = SLOTS_WITH_S8 if s8 else SLOTS_FREE
            if slots != last_slots:
                say(f"slots {slots} (S8 off pids {s8})")
                last_slots = slots
            while queue and len(running) < slots:
                row, t_ev = queue.pop(0)
                d = BATCH / NAMES[row]
                if (d / "result.json").exists():
                    say(f"skip {row}: result.json exists")
                    finished.append(row)
                    if row in AFTER:
                        done_base(row)
                    continue
                if d.exists():
                    say(f"STOP {row}: folder without result.json: {d}")
                    stopped.extend([row, *AFTER.get(row, ())])
                    continue
                running[row] = (start_row(row, t_ev), time.monotonic())
                say(f"started {row} {NAMES[row]} pid {running[row][0].pid} t_ev_loop {t_ev!r} running {len(running)}")
            if rid and time.monotonic() - last_renew > RENEW_S:
                tool("renew", "--id", rid, "--ttl-min", str(TTL_MIN))
                last_renew = time.monotonic()
            time.sleep(POLL_S)
    finally:
        if rid:
            tool("release", "--id", rid)
    say(f"done; finished {finished}; stopped {stopped}")
    sys.exit(1 if stopped else 0)


if __name__ == "__main__":
    main()
