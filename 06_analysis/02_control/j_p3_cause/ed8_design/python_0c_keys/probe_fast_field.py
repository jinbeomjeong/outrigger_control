"""0c step 2: where is the fast-event flag stored? (key names and paths only, no values)

For the V0 event lines of the stored main.jsonl and for one grid run of each grid file
referenced by the census key files, lists the key names of ``event_output`` (main) or of the
run (grid), and every dotted path whose last component contains ``fast`` (case-insensitive).
Values are never printed or written.

Usage: python -I -B probe_fast_field.py <repo root> <out json>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

MAIN_JSONL = "06_analysis/03_hydraulic/coupled/v5/main.jsonl"
KEY_FILES = (
    "06_analysis/02_control/j_p3_cause/ed6_design/keys/confirm_b_grid192.json",
    "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json",
)
EVENT_CASES = ("R12", "R14", "R15", "R16")
FAST_TOKEN = "fast"


def fast_paths(node, prefix: str = "") -> list[str]:
    """Dotted paths (list items as ``[]``) whose last key contains ``fast``."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if FAST_TOKEN in str(key).lower():
                found.append(path)
            found.extend(fast_paths(value, path))
    elif isinstance(node, list):
        for item in node:
            found.extend(fast_paths(item, f"{prefix}[]"))
    return found


def probe_main(root: Path) -> dict:
    output_key_sets: Counter = Counter()
    paths: Counter = Counter()
    job_fast_fields: Counter = Counter()
    for raw in (root / MAIN_JSONL).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        line = json.loads(raw)
        job = line.get("job") or {}
        if job.get("setting") != "V0" or job.get("case") not in EVENT_CASES:
            continue
        output = line.get("event_output")
        output_key_sets[",".join(sorted(output)) if isinstance(output, dict) else "absent"] += 1
        for path in set(fast_paths(line)):
            paths[path] += 1
        job_fast_fields[",".join(sorted(job.get("twin") or {}))] += 1
    return {"v0_event_lines_event_output_key_sets": dict(output_key_sets),
            "v0_event_lines_fast_paths": dict(paths),
            "v0_event_lines_job_twin_field_sets": dict(job_fast_fields)}


def probe_grid(root: Path) -> dict:
    grid_names: set[str] = set()
    for rel in KEY_FILES:
        document = json.loads((root / rel).read_text(encoding="utf-8"))
        for line in document["lines"]:
            grid_names.add(line["v0_pair"]["file"])
    report = {}
    for name in sorted(grid_names):
        stored = json.loads((root / name).read_text(encoding="utf-8"))
        run_key_sets: Counter = Counter()
        paths: Counter = Counter()
        for result in stored.get("results", []):
            for run in result.get("runs", []):
                run_key_sets[",".join(sorted(run))] += 1
                for path in set(fast_paths(run)):
                    paths[path] += 1
        report[name] = {"top_level_keys": sorted(stored),
                        "run_key_sets": dict(run_key_sets), "run_fast_paths": dict(paths)}
    return report


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    result = {"main_jsonl": probe_main(root), "grid_files": probe_grid(root)}
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "ok", "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
