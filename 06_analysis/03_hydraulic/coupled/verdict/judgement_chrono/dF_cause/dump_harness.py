"""Re-run coupling-verdict harness rows and keep the 1 ms chunk record (read-only for the project).

The stored verdict npz holds only the 10 Hz controller log; the force minimum analysis needs the
1 ms true cylinder force. Each row is reproduced exactly (command hash compared to the stored one).

Usage: conda run -n dynamics-dev python -I dump_harness.py R4,R8,R9 [eta] [tag]
"""
from __future__ import annotations

import ctypes
import json
import sys
import time
from ctypes import wintypes
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
OUT = Path(__file__).resolve().parent / "harness"
VERDICT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "verdict"
MASK = 0x0C000000
for path in (HERE, S9_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pin(mask: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
        raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


def run_one(job: tuple[str, str, float | None]) -> dict:
    case_id, run_id, eta = job
    pin(MASK)
    import numpy as np
    import s9_soil_slope as slope
    import verdict_cases
    import verdict_runs
    from harness_flow import COLUMNS, FlowSetting

    t0 = time.perf_counter()
    setting = FlowSetting(is_enabled=False) if eta is None else FlowSetting(is_enabled=True, eta_v=eta)
    case = verdict_cases.resolve_case(case_id, {"R13": "ss_fs4", "S6": "alias_s5", "R2": "reanchor_on"})
    result, series = verdict_runs.execute(case, setting, None)
    plant = slope._CAP.get("plant") if not isinstance(case.twin, verdict_cases.EventTwin) else None
    if plant is None:
        return {"run_id": run_id, "error": "no plant captured"}
    rows = plant.flow_limiter.rows()
    OUT.mkdir(exist_ok=True)
    np.savez_compressed(OUT / f"{run_id}.npz", rows=rows, columns=np.array(COLUMNS), **series)
    stored_path = VERDICT / f"{run_id}.json"
    stored = json.loads(stored_path.read_text(encoding="utf-8")) if stored_path.is_file() else {}
    (OUT / f"{run_id}.events.json").write_text(json.dumps(result["events"]), encoding="utf-8")
    return {"run_id": run_id, "wall_s": round(time.perf_counter() - t0, 1),
            "hash_same_as_stored": result["commands_sha256"] == stored.get("commands_sha256"),
            "forces": result["values"]["forces"]}


def main() -> None:
    pin(MASK)
    cases = sys.argv[1].split(",")
    import verdict_runs

    verdict_runs.warm_numba_cache()
    jobs = []
    for case_id in cases:
        jobs.append((case_id, f"A_{case_id}_eta0.85", 0.85))
        jobs.append((case_id, f"OFF_{case_id}", None))
    with get_context("spawn").Pool(2, maxtasksperchild=1) as pool:
        for out in pool.imap_unordered(run_one, jobs):
            print(json.dumps(out, default=str), flush=True)


if __name__ == "__main__":
    main()
