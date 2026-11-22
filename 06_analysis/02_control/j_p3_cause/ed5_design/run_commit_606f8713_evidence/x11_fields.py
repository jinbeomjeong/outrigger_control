"""Print the plan fields of an x11 selection.json (seeds, union check, counts) and file shas."""

import hashlib
import json
import sys
from pathlib import Path

WORDS = ("seed", "union", "repeat", "shift", "moved", "dry", "count", "pairs", "status", "c9")
MAX_LIST = 12


def walk(value: object, prefix: str, depth: int) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if depth < 3:
                walk(item, path, depth + 1)
    elif any(word in prefix.lower() for word in WORDS):
        if isinstance(value, list):
            shown = value if len(value) <= MAX_LIST and all(not isinstance(v, (dict, list)) for v in value) else f"list[{len(value)}]"
            print(f"{prefix} = {shown}")
        else:
            print(f"{prefix} = {value!r}")


def main() -> None:
    folder = Path(sys.argv[1])
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            print(hashlib.sha256(path.read_bytes()).hexdigest()[:8], path.stat().st_size, path.relative_to(folder).as_posix())
    selection = json.loads((folder / "selection.json").read_text(encoding="utf-8"))
    print("top-level:", sorted(selection))
    walk(selection, "", 0)


if __name__ == "__main__":
    main()
