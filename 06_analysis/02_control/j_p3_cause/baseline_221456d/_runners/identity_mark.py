"""Write a run identity next to a baseline output (``run_v5._write_identity`` of the worktree).

The 221456d ``jp3_case_replay.py`` writes no identity; this marks its output (and the
``fresh_stretch`` diagnostic) at the start and the end with the same record ``run_v5`` uses.

Usage (dynamics-dev):
  python -I -B identity_mark.py <worktree root> <output jsonl> start|end
"""

import sys
from pathlib import Path

WORKTREE = Path(sys.argv[1])
COUPLED = WORKTREE / "04_scripts" / "04_hydraulic" / "coupled"
sys.path.insert(0, str(COUPLED))

import run_v5  # noqa: E402

if Path(run_v5.ROOT).resolve() != WORKTREE.resolve():
    raise SystemExit(f"run_v5 ROOT {run_v5.ROOT} is not the worktree {WORKTREE}")
run_v5._write_identity(Path(sys.argv[2]), sys.argv[3])
print("identity", sys.argv[3], "written next to", sys.argv[2])
