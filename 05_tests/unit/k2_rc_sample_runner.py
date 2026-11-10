"""I-8 R-c sample (``k2_touch_creep_rules.md`` I-8): the first 24 jobs of a stored ``hrx_off.jsonl`` in key order
run again through ``run_v5.run_one``; their ``commands_sha256`` are compared with the stored lines.

Usage (dynamics-dev, BLAS one thread; the workers inherit the affinity of this process)::

    python -I -B k2_rc_sample_runner.py <checkout> <hrx_off.jsonl> <out.json> <workers>

The last stdout line is the JSON summary ``{n, equal, errors, head}``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

CHECKOUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CHECKOUT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(CHECKOUT / "03_src"))
import run_v5  # noqa: E402

SAMPLE_ROWS = 24


def run_job(job: dict) -> dict:
    row = run_v5.run_one(job)
    return {"key": job["d1"]["key"], "commands_sha256": row.get("commands_sha256"), "error": row.get("error")}


def main() -> None:
    stored_path, out_path, workers = Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
    lines = [json.loads(line) for line in stored_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sample = sorted(lines, key=lambda line: line["job"]["d1"]["key"])[:SAMPLE_ROWS]
    with Pool(min(workers, len(sample)), maxtasksperchild=1) as pool:  # one job per process (patches)
        rows = pool.map(run_job, [line["job"] for line in sample], chunksize=1)
    for row, line in zip(rows, sample, strict=True):  # pool.map keeps the order
        row["want"] = line["commands_sha256"]
        row["equal"] = row["commands_sha256"] == row["want"]
    head = subprocess.run(["git", "-C", str(CHECKOUT), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=False).stdout.strip()
    summary = {"n": len(rows), "equal": sum(row["equal"] for row in rows),
               "errors": sum(row["error"] is not None for row in rows), "head": head}
    out_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
