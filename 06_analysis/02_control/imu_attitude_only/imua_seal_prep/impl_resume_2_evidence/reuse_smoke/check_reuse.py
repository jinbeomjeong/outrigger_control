"""Summary of the A-type --reuse-d1 smoke: per U-3 record its reuse, tag, A-type keys and the
2.2 record status (resolved through the H-1 result folder for a reused record).

Usage: check_reuse.py <worktree> <smoke folder>  (prints JSON lines; values are record fields)
"""

import json
import sys
from pathlib import Path

WORKTREE = Path(sys.argv[1])
FOLDER = Path(sys.argv[2])
sys.path.insert(0, str(WORKTREE / "04_scripts" / "04_hydraulic" / "coupled"))

import imua_records  # noqa: E402

h1 = FOLDER / "h1_d1.jsonl"
for text in h1.read_text(encoding="utf-8").splitlines():
    line = json.loads(text)
    path = imua_records.locate_record(h1, line)
    print(json.dumps({"h1": line["job"]["d1"]["key"], "error": line.get("error"),
                      "tag": line.get("controller_tag"),
                      "commands_sha256": line.get("commands_sha256"),
                      "record": imua_records.record_status(path, line.get("controller_tag"))}))
out = FOLDER / "u3_slope_V0.json"
payload = json.loads(out.read_text(encoding="utf-8"))
for record in payload["records"]:
    block = record.get("v5") or {}
    path = imua_records.locate_record(out, block, h1_result_path=h1)
    print(json.dumps({"u3": record["id"], "reuse": record.get("reuse"),
                      "error": record.get("error"), "tag": block.get("controller_tag"),
                      "logged_commands_sha256": block.get("logged_commands_sha256"),
                      "family_sample": block.get("family_sample"),
                      "imu_sensor_gains": (block.get("imu_sensor") or {}).get("gains_preset"),
                      "has_g5": block.get("imua_check_g5") is not None,
                      "record_file": block.get("imua_record_file"),
                      "record_source": block.get("imua_record_source"),
                      "record": imua_records.record_status(path, block.get("controller_tag"))}))
reuse = (payload.get("meta") or {}).get("reuse") or (payload.get("meta") or {}).get("v5", {})
print(json.dumps({"meta_reuse_keys": sorted(reuse) if isinstance(reuse, dict) else None}))
