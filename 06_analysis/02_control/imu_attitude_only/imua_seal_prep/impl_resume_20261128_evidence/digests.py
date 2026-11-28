"""Per-run command digests, tags and A-type fields of one smoke folder (JSON to stdout)."""

import json
import sys
from pathlib import Path

FOLDER = Path(sys.argv[1])


def screen_rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("records") or payload.get("results") or []
    rows = []
    for entry in entries:
        v5 = entry.get("v5") or {}
        rows.append({
            "key": entry.get("id") or entry.get("key") or entry.get("case"),
            "controller": entry.get("controller"),
            "error": (entry.get("error") or "")[:300] or None,
            "tag": v5.get("controller_tag"),
            "commands": v5.get("commands_sha256"),
            "logged": v5.get("logged_commands_sha256"),
            "imu_sensor": (v5.get("imu_sensor") or {}).get("model"),
            "g5": v5.get("imua_check_g5") is not None,
            "record": v5.get("imua_record_file"),
        })
    return rows


def d1_rows(path: Path) -> list[dict]:
    rows = []
    for text in path.read_text(encoding="utf-8").splitlines():
        line = json.loads(text)
        rows.append({
            "key": (line["job"].get("d1") or {}).get("key"), "setting": line["job"]["setting"],
            "error": (line.get("error") or "")[:300] or None,
            "tag": line.get("controller_tag"), "commands": line.get("commands_sha256"),
            "imu_sensor": (line.get("imu_sensor") or {}).get("model"),
            "g5": line.get("imua_check_g5") is not None, "record": line.get("imua_record_file"),
        })
    return rows


def main() -> None:
    out = {}
    for path in sorted(FOLDER.glob("*.json")):
        if path.name.endswith(".identity.json"):
            continue
        out[path.name] = screen_rows(path)
    for path in sorted(FOLDER.glob("*.jsonl")):
        out[path.name] = d1_rows(path)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
