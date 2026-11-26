"""Q8-11 extra: do the 12 D jobs (d_grid_keys12.json) find their V0 pair in confirm_b_grid192?

Read only; counts and structure, no values. Usage: python -I -B d_pair_check.py <repo root> <out>
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

D_BLOB = ("3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/"
          "d_grid_keys12.json")
GRID192 = "06_analysis/02_control/j_p3_cause/ed6_design/keys/confirm_b_grid192.json"
IGNORED = ("setting", "mask", "t4h_dir")


def plain(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in IGNORED}, sort_keys=True)


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    blob = subprocess.run(["git", "-C", str(root), "show", D_BLOB], capture_output=True,
                          check=True, timeout=60).stdout
    d_doc = json.loads(blob)
    grid = json.loads((root / GRID192).read_text(encoding="utf-8"))
    grid_by_job = Counter(plain(line["job"]) for line in grid["lines"])
    jobs = d_doc["jobs"]
    entry_types = Counter(type(entry).__name__ for entry in jobs)
    entry_fields = Counter(",".join(sorted(entry)) for entry in jobs if isinstance(entry, dict))
    matches = Counter()
    for entry in jobs:
        job = entry.get("job", entry) if isinstance(entry, dict) else {}
        matches[f"grid192_matches:{grid_by_job.get(plain(job), 0)}"] += 1
    result = {"d_jobs": len(jobs), "entry_types": dict(entry_types),
              "entry_fields": dict(entry_fields), "matches": dict(matches)}
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
