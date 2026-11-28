"""R3c (control ``ed9_design/control_cm_switch/report.md`` 2.1, 2.2): the unique V0 jobs of the
three edition 8 diagnosis job files (61 labels, 59 jobs), with every label they had.

Reads only the job definitions (``label`` and ``job``; the files' ``stored`` fields are not
copied). Writes ``[{label, labels, job}]`` (the first label in file order names the job) and
prints counts only.

Usage (python-dev ``python.exe -I -B``)::

    python make_r3c_jobs.py --jobs <diag_jobs.json> --jobs <jobs_sweep.json>
        --jobs <jobs_sweep_ext.json> --out <r3c_jobs.json>

Exit codes: 0 written; 2 input error (a missing file, an existing ``--out``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

RUN_ONLY_JOB_FIELDS = ("mask", "t4h_dir")
EXPECTED_LABELS, EXPECTED_JOBS = 61, 59
"""Control 2.2 (J1 = J1shape_o0.0875, J3 = J3shape_o0.0875)."""


def job_key(job: dict) -> str:
    return json.dumps({k: v for k, v in sorted(job.items()) if k not in RUN_ONLY_JOB_FIELDS},
                      sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--jobs", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists() or not all(path.is_file() for path in args.jobs):
        print(json.dumps({"status": "input_error"}))
        return 2
    unique: dict[str, dict] = {}
    labels = 0
    for path in args.jobs:
        for entry in json.loads(path.read_text(encoding="utf-8")):
            labels += 1
            key = job_key(entry["job"])
            found = unique.setdefault(key, {"label": entry["label"], "labels": [],
                                            "job": {k: v for k, v in entry["job"].items()
                                                    if k not in RUN_ONLY_JOB_FIELDS}})
            found["labels"].append(entry["label"])
    entries = list(unique.values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=1)
    sources = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in args.jobs]
    print(json.dumps({"status": "ok", "labels": labels, "jobs": len(entries),
                      "as_expected": (labels, len(entries)) == (EXPECTED_LABELS, EXPECTED_JOBS),
                      "sources": sources, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
