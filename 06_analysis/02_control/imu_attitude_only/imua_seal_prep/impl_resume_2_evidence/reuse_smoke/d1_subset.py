"""run_v5 d1 on a few D-1 rows only (smoke of the A-type --reuse-d1 path).

Usage: d1_subset.py <worktree> <row key>[,<row key>...] <setting> -- <run_v5 arguments>
The parent replaces run_v5.batch_jobs by the selected eps-0 jobs, then calls run_v5.main;
the spawned workers import this file as __mp_main__ and only run run_v5.run_one.
"""

import sys
from pathlib import Path

WORKTREE = Path(sys.argv[1])
sys.path.insert(0, str(WORKTREE / "04_scripts" / "04_hydraulic" / "coupled"))

import run_v5  # noqa: E402


def main() -> None:
    keys = sys.argv[2].split(",")
    setting = sys.argv[3]
    rest = sys.argv[sys.argv.index("--") + 1:]
    original = run_v5.batch_jobs

    def selected(name: str) -> list[dict]:
        jobs = [job for job in original(name) if job["d1"]["key"] in keys
                and job["setting"] == setting and float(job.get("eps", 0.0)) == 0.0]
        if len(jobs) != len(keys):
            raise SystemExit(f"{len(jobs)} jobs for {keys}")
        return jobs

    run_v5.batch_jobs = selected
    run_v5.main(["d1", *rest])


if __name__ == "__main__":
    main()
