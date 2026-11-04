"""Re-run the 14 v4 manuscript rows with current code and the final preset. No plant or controller option is changed.

Four case processes at most on the P pool (self-pinned pcore); if the P average stays above 80 % the limit falls to 3.
Flow limit off (no flow_limit key), table cases as they are. Main tree code. Run with -B.
Usage: python -I -B -X utf8 -u run_v4recheck.py
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import subprocess
import sys
import time
from collections import deque
from multiprocessing.connection import wait
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

MAIN = Path(r"C:\workspace\outrigger_control")
CASES = ("N_G4_Fs0_pressure", "N_G4_Fs4_pressure", "N_G4_Fs8_pressure", "N_SS_Fs0_pressure", "N_SS_Fs4_pressure", "N_SS_Fs8_pressure",
         "K0V_top_fdown3.5_Fs0", "K24_top_fdown3.5_Fs2", "K8_top_fdown3.5_Fs8", "E_SS_Fs0", "E_SS_Fs8", "E_RE1bF_Fs0", "E_RE1bP_Fs0", "E_RE1bP_Fs8")
TIMEOUT_S = 5400.0  # run_S8C.CASE_TIMEOUT_S
P_LOGICAL = list(range(16))
P_LIMIT = 80.0
SAMPLE_PY = r"C:\Users\jinbeom\.claude\tools\cpu-scheduler\sample.py"
DEV_PY = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe"
sys.path.insert(0, str(MAIN / "03_src"))
sys.path.insert(0, str(MAIN / "04_scripts" / "02_chrono"))


def job(case, case_dir):
    import run_S8C as s8

    if not Path(s8.__file__).resolve().is_relative_to(MAIN):
        raise SystemExit(f"wrong run_S8C: {s8.__file__}")
    return s8.job_case(case, case_dir)


def code_hashes() -> dict[str, str]:
    files = sorted((MAIN / "03_src").rglob("*.py")) + sorted((MAIN / "04_scripts/02_chrono").glob("*.py")) + [MAIN / "02_params/rexome33.yaml"]
    return {str(f.relative_to(MAIN)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


def p_use(psutil) -> float:
    per = psutil.cpu_percent(interval=2.0, percpu=True)
    return sum(per[i] for i in P_LOGICAL) / len(P_LOGICAL)


def main() -> None:
    import psutil

    from outrigger_sim import batch as B
    from outrigger_sim.batch import Case

    overrides = {k: v for k, v in os.environ.items() if k.startswith("OUTRIGGER_")}
    if overrides:
        raise SystemExit(f"OUTRIGGER_* set, refusing: {overrides}")
    d = MAIN / "07_results/S8" / time.strftime("final_v4recheck_%Y%m%d_%H%M%S")
    d.mkdir(parents=False, exist_ok=False)
    head = (MAIN / ".git/refs/heads/master").read_text(encoding="utf-8").strip()
    before = code_hashes()
    (d / "code_state.json").write_text(json.dumps({"main_head": head, "code_sha256": before}, indent=1), encoding="utf-8")
    log = (d / "runner.log").open("a", encoding="utf-8", buffering=1)

    def say(msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log.write(line + "\n")

    jobs = [Case(c, {"duration_s": None}) for c in CASES]
    B._check_timeout(TIMEOUT_S)
    B._check_inputs(jobs, job, d, 4)
    ctx = multiprocessing.get_context("spawn")
    pending = deque(jobs)
    running: dict[int, object] = {}
    outcomes: dict[str, object] = {}
    started_utc = B._utc_now_text()
    t0 = time.perf_counter()
    limit, sampler, use, high_since = 4, None, p_use(psutil), None
    say(f"start P use {use:.1f} % batch {d}")
    last_start = -1e9
    while pending or running:
        use = p_use(psutil)
        now = time.perf_counter()
        # three start at once; the fourth only after the load of the first three shows; later fills one at a time
        if len(running) >= 4 and use > P_LIMIT:
            high_since = high_since if high_since is not None else now
            if limit == 4 and now - high_since > 60.0:
                limit = 3
                say(f"P use {use:.1f} % above {P_LIMIT} % for 60 s: limit 3 (no running case is touched)")
        else:
            high_since = None
        gap_ok = len(running) < 3 or now - last_start > 60.0
        if pending and len(running) < limit and gap_ok and (use <= P_LIMIT or len(running) < 3):
            case = pending.popleft()
            rc = B._start_case(ctx, job, case, d, B.Placement.PCORE, TIMEOUT_S)
            running[rc.process.sentinel] = rc
            last_start = now
            say(f"started {case.case_id} pid {rc.process.pid} P use {use:.1f} % running {len(running)}")
            if sampler is None:
                out = d / f"sample_{case.case_id}.sample.json"
                sampler = subprocess.Popen([DEV_PY, "-I", SAMPLE_PY, "--pid", str(rc.process.pid), "--interval", "5", "--no-gpu", "--out", str(out)],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                say(f"sample.py pid {sampler.pid} on {case.case_id} -> {out}")
            continue
        if not running:
            continue
        ended = wait(list(running), timeout=min(10.0, B._wait_timeout_s(running)))
        for sentinel in {*ended, *B._terminate_timed_out(running)}:
            rc = running.pop(sentinel)
            o = B._finish_case(rc)
            outcomes[rc.case.case_id] = o
            say(f"finished {o.case_id} {o.status} {o.wall_s:.1f} s; pending {len(pending)} running {len(running)}")
    ordered = [outcomes[c.case_id] for c in jobs]
    doc = B._batch_document(ordered, job, started_utc, time.perf_counter() - t0, 4, B.Placement.PCORE)
    doc["placement"] = f"runner slots 4 (limit at end {limit}), self-pinned pcore"
    B._write_text_atomically(d / B.BATCH_META_NAME, B._json_text(doc))
    after = code_hashes()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    (d / "code_state_end.json").write_text(json.dumps({"main_head": (MAIN / ".git/refs/heads/master").read_text(encoding="utf-8").strip(), "changed_during_run": changed}, indent=1), encoding="utf-8")
    say(f"done wall {time.perf_counter() - t0:.1f} s; code changed during run: {changed}; statuses {[(o.case_id, o.status) for o in ordered if o.status != 'ok']}")


if __name__ == "__main__":
    main()
