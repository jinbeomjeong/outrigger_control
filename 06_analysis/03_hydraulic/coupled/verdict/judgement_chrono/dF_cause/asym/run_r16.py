"""R16 (G1L_RE1bF_FL_top_o050_Fs4), flow limit off, right pads on the larger gap, three approach phases.

Same job as the stored run (``run_S8C.job_case`` through ``outrigger_sim.batch``, placement pcore, end
rule on), worktree code first on sys.path. One batch folder per phase with the case folder named by the
case id, so ``judge_batch`` reads it unchanged. At most two at once; every run is stopped at the deadline.

Usage: python -I run_r16.py all              (orchestrator)
       python -I run_r16.py one <run id>     (one batch, started by the orchestrator)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from functools import partial
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-ae9039e69988d5282")
OUT = Path(__file__).resolve().parent / "runs_r16"
CASE_ID = "G1L_RE1bF_FL_top_o050_Fs4"
DEADLINE_S = 1800.0
MAX_RUNNING = 2
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))


def gaps(delta_m: float) -> list[float]:
    """Offsets (FL, FR, RL, RR): left -2 mm, right +2 mm, all + delta [m]."""
    return [-2.0e-3 + delta_m, 2.0e-3 + delta_m, -2.0e-3 + delta_m, 2.0e-3 + delta_m]


RUNS = {"r16_mirror2_d000": gaps(0.0), "r16_mirror2_d035": gaps(0.35e-3), "r16_mirror2_d070": gaps(0.70e-3)}


def job(case, case_dir):
    from outrigger_sim.chrono import l2b_model

    import run_S8C as s8

    real = l2b_model.L2bModel
    l2b_model.L2bModel = partial(real, pad_gap_offsets_m=tuple(case.settings["pad_gap_offsets_m"]))
    return s8.job_case(case, case_dir)


def one(run_id: str) -> None:
    from outrigger_sim.batch import Case, run_cases

    d = OUT / run_id
    d.mkdir(parents=True, exist_ok=False)
    run_cases([Case(CASE_ID, {"duration_s": None, "pad_gap_offsets_m": RUNS[run_id]})], job, d,
              max_workers=1, placement="pcore", timeout_s=DEADLINE_S)


def orchestrate() -> None:
    t0 = time.monotonic()
    pending = list(RUNS)
    running: dict[str, tuple[subprocess.Popen, float]] = {}
    log = OUT.parent / "r16_orchestrator.json"
    rows: dict[str, dict] = {}
    OUT.mkdir(parents=True, exist_ok=True)
    stopped = False
    while pending or running:
        now = time.monotonic() - t0
        if now > DEADLINE_S and not stopped:
            stopped = True
            pending.clear()
            for rid, (proc, _start) in running.items():
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], check=False, capture_output=True)
                rows[rid] = {"stopped_at_deadline": True}
        while pending and len(running) < MAX_RUNNING:
            rid = pending.pop(0)
            running[rid] = (subprocess.Popen([sys.executable, "-I", __file__, "one", rid], stdin=subprocess.DEVNULL), now)
        for rid, (proc, start) in list(running.items()):
            code = proc.poll()
            if code is not None:
                rows.setdefault(rid, {}).update(exit_code=code, wall_s=now - start)
                del running[rid]
                print(rid, rows[rid], flush=True)
        log.write_text(json.dumps({"elapsed_s": now, "pending": pending, "running": list(running), "rows": rows}, indent=1), encoding="utf-8")
        time.sleep(5.0)
    print("all done", round(time.monotonic() - t0, 1), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "all":
        orchestrate()
    else:
        one(sys.argv[2])
