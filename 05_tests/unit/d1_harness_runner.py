"""One D-1 harness run in a fresh process; writes a small JSON report.

Helper of ``test_d1_harness.py``: the harness needs dynamics-dev (numba) and patches module
globals, so every run gets its own process. Requests (JSON, first argument):

  {"kind": "r72", "key": ..., "slope": [roll, pitch] | null, "settle_hook": ... | null,
   "path": "per_leg" | "per_leg_force" | "s9", "run_limit_s": float | null}
      ``r72_g6_screen.job`` -> {"hash", "final_phase", "settle"}
  {"kind": "v5", "job": {...}, "run_limit_s": float | null}
      ``run_v5.run_one`` -> {"hash", "final_phase", "d1"}

Usage:
  python -I -B d1_harness_runner.py <request json> <out.json>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S8_DIR = PROJECT_ROOT / "04_scripts" / "03_control" / "s8"
MAIN_TREE_ROOT = Path(r"C:\workspace\outrigger_control")
"""``r8d1_td.py`` inserts a folder of this tree whichever checkout it runs in."""


class _ThisCheckoutSysPath(list):
    """``sys.path`` whose ``insert`` maps a main-tree folder onto this checkout (git worktree)."""

    def insert(self, index, folder) -> None:
        path = Path(folder)
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            folder = str(PROJECT_ROOT / path.relative_to(MAIN_TREE_ROOT))
        super().insert(index, folder)


sys.path = _ThisCheckoutSysPath(sys.path)
for _path in (COUPLED_DIR, SOURCE_DIR):
    sys.path.insert(0, str(_path))


def _run_r72(request: dict) -> dict:
    os.environ["R72_PATH"] = request.get("path") or "per_leg"
    saved = sys.argv
    sys.argv = [saved[0], str(PROJECT_ROOT)]  # r72 reads the project root at import
    sys.path.insert(0, str(S8_DIR))
    try:
        import r72_g6_screen as r72
    finally:
        sys.argv = saved
    result = r72.job(request["key"], slope=request.get("slope"),
                     settle_hook=request.get("settle_hook"))
    if "error" in result:
        raise RuntimeError(f"{request}: {result['error']}\n{result.get('tb')}")
    return {"hash": result["commands_sha256"], "final_phase": result["final_phase"],
            "settle": result.get("settle")}


def _run_v5(request: dict) -> dict:
    import run_v5

    record = run_v5.run_one({**request["job"], "mask": None, "t4h_dir": None})
    if "error" in record:
        raise RuntimeError(f"{request}: {record['error']}\n{record.get('tb')}")
    return {"hash": record["commands_sha256"], "final_phase": record["final_phase"],
            "d1": record.get("d1")}


def main() -> None:
    request, out_path = json.loads(sys.argv[1]), Path(sys.argv[2])
    if request.get("run_limit_s") is not None:  # read by s9_soil_closed_loop at import
        os.environ["S9_RUN_LIMIT_S"] = str(request["run_limit_s"])
    runners = {"r72": _run_r72, "v5": _run_v5}
    report = runners[request["kind"]](request)
    out_path.write_text(json.dumps(report, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
