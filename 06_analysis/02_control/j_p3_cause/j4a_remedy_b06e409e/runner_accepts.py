"""Does the r79 runner take a key (no run): r79_L3L4_final's --keys job list and its --keys-file
check. Usage: python -I -B runner_accepts.py <worktree> <key>"""
import sys
from pathlib import Path

root, key = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, str(root / "04_scripts" / "03_control" / "s8"))
sys.argv = [sys.argv[0], str(root)]  # the harness modules read the project root at import
import r79_L3L4_final as final  # noqa: E402

levels = ["L2"]
jobs = final.plain_jobs(levels)
print("default L2 jobs", len(jobs), "key in the --keys job list:", key in jobs)
print("--keys-file problems:", final.keys_file_problems([key], levels))
base = key.replace("|s25|", "|s0|")
print("base key in the --keys job list:", base in jobs)
