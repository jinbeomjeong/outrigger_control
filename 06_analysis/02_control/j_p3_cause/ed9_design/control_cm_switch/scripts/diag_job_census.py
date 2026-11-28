"""Count unique diag jobs (stage5_aa_diag 7 + sweep 34 + sweep_ext 20) by job key.

Prints only labels, counts and duplicate groups (no run values).
"""
import json
import sys
from pathlib import Path

DIAG = Path(sys.argv[1])
files = [DIAG / "diag_jobs.json", DIAG / "diag2" / "jobs_sweep.json",
         DIAG / "diag2" / "jobs_sweep_ext.json", DIAG / "diag2" / "jobs_gyro.json"]
groups = {}
per_file = {}
for path in files:
    entries = json.loads(path.read_text(encoding="utf-8"))
    per_file[path.name] = len(entries)
    if path.name == "jobs_gyro.json":
        gyro_keys = {json.dumps(e["job"], sort_keys=True) for e in entries}
        continue
    for entry in entries:
        key = json.dumps(entry["job"], sort_keys=True)
        groups.setdefault(key, []).append(entry["label"])
diag_keys = {json.dumps(e["job"], sort_keys=True)
             for e in json.loads(files[0].read_text(encoding="utf-8"))}
out = {"per_file": per_file, "labels": sum(len(v) for v in groups.values()),
       "unique_jobs": len(groups),
       "duplicates": [v for v in groups.values() if len(v) > 1],
       "gyro_jobs_equal_diag_jobs": gyro_keys == diag_keys}
print(json.dumps(out, indent=1))
