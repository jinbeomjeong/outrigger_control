"""Spec rev. 69 draft (coverage gap G5 remainder): the rev. 67 event screen (``r67_g1_screen``, mode "screen") at the
intermediate seal friction F_s = 2 / 4 kN (front value, rear 0.833 x), which rev. 67 ran only at 0 / 8 kN.

Nothing is copied: the job list of r67 is built with ``FS_KN`` replaced, and each job is r67's own ``run_job`` (the
F_s value travels in the job key, so the spawned workers need no patch). Events G4 / RE1bF / FS24, legs FL / FR /
RL / RR, auger top / bottom, timing READY + 5 s / middle of LEVEL, start phase offsets from R67_OFFSETS (default
here 0,0.025,0.05,0.075 as the rev. 67 top phase refinement). Judgement rows = rev. 67 342.3 (instantaneous F_min
after W; the U-S8-74 0.5 s mean and the U-S8-75 (b) exception are applied in the table step).

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r69_g5_screen.py <project_root> <out_json> [workers]
Env: as r67 (R67_FILTER, R67_SLICE, R67_AFFINITY, R67_OFFSETS); R69_FS = comma list (default 2,4).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(sys.argv[1]).resolve() / "04_scripts" / "03_control" / "s8"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import r67_g1_screen as r67  # noqa: E402


def main():
    r67.FS_KN = tuple(float(x) for x in os.environ.get("R69_FS", "2,4").split(","))
    os.environ["R67_MODE"] = "screen"
    os.environ.setdefault("R67_OFFSETS", "0,0.025,0.05,0.075")
    if len(sys.argv) > 2 and sys.argv[2] == "--list":
        for j in r67.all_jobs("screen"):
            print(j)
        return
    r67.main()


if __name__ == "__main__":
    main()
