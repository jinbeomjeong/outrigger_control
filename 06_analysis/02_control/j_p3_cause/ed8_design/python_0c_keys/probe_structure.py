"""0c step 1: structure of the census key inputs (names and counts only, no values).

Prints, for each input, the field names and label counts (settings, cases) needed to map
census rows to their V0 pair. Never prints a start list, a start time, a ``fast`` value or
any result field value.

Usage: python -I -B probe_structure.py <repo root> <out json>
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

J9_MAIN = "06_analysis/02_control/j_p3_cause/j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl"
SENS_KEYS = "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/sens_keys_ed7.json"
G1_KEYS = "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json"
GRID192_KEYS = "06_analysis/02_control/j_p3_cause/ed6_design/keys/confirm_b_grid192.json"
D_KEYS_BLOB = ("3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/"
               "d_grid_keys12.json")


def field_names(record: dict) -> str:
    return ",".join(sorted(record))


def probe_j9_main(root: Path) -> dict:
    lines = (root / J9_MAIN).read_text(encoding="utf-8").splitlines()
    top_fields: Counter = Counter()
    job_fields: Counter = Counter()
    settings: Counter = Counter()
    cases: Counter = Counter()
    for raw in lines:
        if not raw.strip():
            continue
        line = json.loads(raw)
        top_fields[field_names(line)] += 1
        job = line.get("job") or {}
        job_fields[field_names(job)] += 1
        settings[str(job.get("setting"))] += 1
        cases[str(job.get("case"))] += 1
    return {"top_level_field_sets": dict(top_fields), "job_field_sets": dict(job_fields),
            "settings": dict(sorted(settings.items())), "cases": dict(sorted(cases.items()))}


def probe_key_document(document) -> dict:
    lines = document.get("lines") if isinstance(document, dict) else document
    line_fields: Counter = Counter()
    pair_fields: Counter = Counter()
    job_fields: Counter = Counter()
    settings: Counter = Counter()
    for line in lines or []:
        line_fields[field_names(line)] += 1
        pair = line.get("v0_pair")
        if isinstance(pair, dict):
            pair_fields[field_names(pair)] += 1
        job = line.get("job")
        if isinstance(job, dict):
            job_fields[field_names(job)] += 1
            settings[str(job.get("setting"))] += 1
    return {"top_level_keys": sorted(document) if isinstance(document, dict) else "list",
            "lines": len(lines or []), "line_field_sets": dict(line_fields),
            "v0_pair_field_sets": dict(pair_fields), "job_field_sets": dict(job_fields),
            "settings": dict(sorted(settings.items()))}


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    result = {"j9_main": probe_j9_main(root)}
    for name, rel in (("sens_keys_ed7", SENS_KEYS), ("confirm_g1_grid171", G1_KEYS),
                      ("confirm_b_grid192", GRID192_KEYS)):
        result[name] = probe_key_document(json.loads((root / rel).read_text(encoding="utf-8")))
    blob = subprocess.run(["git", "-C", str(root), "show", D_KEYS_BLOB], capture_output=True,
                          check=True, timeout=60, stdin=subprocess.DEVNULL).stdout
    d_document = json.loads(blob)
    result["d_grid_keys12"] = {
        "top_level_keys": sorted(d_document) if isinstance(d_document, dict) else "list",
        "job_entry_field_sets": dict(Counter(field_names(entry)
                                             for entry in d_document.get("jobs", []))),
    }
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "ok", "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
