"""Probe reproducibility after the record keys: commands_sha256 of the rerun lines against the
stored 6bfb2560 probe lines (by job), and the new record keys present (no values printed)."""
import json
import sys
from pathlib import Path

RUNTIME = ("mask", "t4h_dir")


def identity(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in RUNTIME}, sort_keys=True)


stored_path, rerun_path, out_path = (Path(arg) for arg in sys.argv[1:4])
rerun = {}
for text in rerun_path.read_text(encoding="utf-8").splitlines():
    if text.strip():
        line = json.loads(text)
        rerun[identity(line["job"])] = line
stored = {}
with stored_path.open(encoding="utf-8") as handle:
    for text in handle:
        line = json.loads(text)
        key = identity(line["job"])
        if key in rerun:
            stored[key] = line.get("commands_sha256")
rows = []
for key, line in rerun.items():
    blind = (line.get("lsb_record") or {}).get("blind") or {}
    t4h = rerun_path.with_name(f"{rerun_path.stem}_t4h") / line["t4h_file"]
    import numpy as np

    with np.load(t4h, allow_pickle=False) as data:
        has_array = "lsb_ib_twist_load_N" in data.files
    rows.append({"setting": line["job"]["setting"], "job": json.loads(key),
                 "error": "error" in line,
                 "same_commands_sha256": stored.get(key) == line.get("commands_sha256"),
                 "stored_found": key in stored,
                 "has_level_done": "level_done" in blind,
                 "level_done_paths": [entry["path"] for entry in blind.get("level_done", [])],
                 "has_twist_over_limit": "twist_over_limit" in blind,
                 "has_lsb_ib_twist_load_N": has_array})
summary = {"lines": len(rows), "same": sum(r["same_commands_sha256"] for r in rows),
           "stored_found": sum(r["stored_found"] for r in rows),
           "with_new_keys": sum(r["has_level_done"] and r["has_twist_over_limit"]
                                and r["has_lsb_ib_twist_load_N"] for r in rows),
           "errors": sum(r["error"] for r in rows)}
out_path.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
print(json.dumps(summary))
