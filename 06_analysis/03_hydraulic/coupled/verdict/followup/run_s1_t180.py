"""S1 for 180 s (no stop at READY + 10 s) with the flow limit on at eta 0.90 or off.

Bundle names stay outside aggregate_verdict's A .. E and OFF, so the stored tables do not change.

Usage: <dynamics-dev python> -I -B run_s1_t180.py on|off <out dir>
"""
from __future__ import annotations

import sys
import time
from dataclasses import asdict
from pathlib import Path

COUPLED = Path(r"C:\workspace\outrigger_control\04_scripts\04_hydraulic\coupled")
sys.path.insert(0, str(COUPLED))

import numpy as np  # noqa: E402
import run_verdict  # noqa: E402  (its import sets the harness paths)
import verdict_runs  # noqa: E402
from harness_flow import FlowSetting  # noqa: E402
from verdict_cases import CASES  # noqa: E402

ETA_V = 0.90
RUNS = {
    "on": ("B_S1_eta0.90_t180s", "S1_T180_ON", FlowSetting(is_enabled=True, eta_v=ETA_V)),
    "off": ("OFF_S1_t180s", "S1_T180_OFF", FlowSetting(is_enabled=False)),
}


def main() -> None:
    mode, out_text = sys.argv[1:]
    out_dir = Path(out_text)
    run_id, bundle, setting = RUNS[mode]
    t_start = time.perf_counter()
    result, series = verdict_runs.execute(CASES["S1"], setting, "run_180s")
    if "error" in result:
        raise RuntimeError(f"{result['error']}\n{result.get('tb')}")
    header = {
        "run_id": run_id, "bundle": bundle, "case_id": "S1",
        "chrono_name": CASES["S1"].chrono_name, "setting": asdict(setting),
        "decision": "run_180s", "note": "run limit 180 s, READY does not end the run",
        "wall_s": round(time.perf_counter() - t_start, 1),
    }
    np.savez_compressed(out_dir / f"{run_id}.npz", **series)
    run_verdict.write_json_atomic(out_dir / f"{run_id}.json", {**header, **result})
    print(run_id, "done", header["wall_s"], flush=True)


if __name__ == "__main__":
    main()
