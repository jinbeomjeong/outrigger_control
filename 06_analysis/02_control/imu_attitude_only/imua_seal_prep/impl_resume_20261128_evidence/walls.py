"""wall_s per smoke line: full IMU (smoke_before) against A-type (smoke_imua, smoke_imua2)."""

import json
import sys
from pathlib import Path

root = Path(sys.argv[1])


def walls(folder: Path) -> dict:
    out = {}
    for path in folder.glob("*.json"):
        if path.name.endswith(".identity.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("records") or payload.get("results") or []:
            key = (path.name, entry.get("controller") or "C2")
            out[key] = entry.get("wall_s")
    for path in folder.glob("*.jsonl"):
        for text in path.read_text(encoding="utf-8").splitlines():
            line = json.loads(text)
            out[(path.name, line["job"]["setting"])] = line.get("wall_s")
    return out


before = walls(root / "smoke_before")
after = {**walls(root / "smoke_imua"), **walls(root / "smoke_imua2")}
for key in sorted(before):
    print(key, "full", before[key], "A-type", after.get(key))
