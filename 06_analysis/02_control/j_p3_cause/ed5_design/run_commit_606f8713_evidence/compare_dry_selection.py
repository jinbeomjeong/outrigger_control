"""Compare two dry_selection.json files: top-level keys, and scan file lists as path sets."""

import json
import sys
from pathlib import Path

SHOWN = 8


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def by_path(entries: list[dict]) -> dict[str, dict]:
    return {entry["path"]: entry for entry in entries}


def report_list(name: str, old: list[dict], new: list[dict]) -> None:
    old_map, new_map = by_path(old), by_path(new)
    added = sorted(set(new_map) - set(old_map))
    removed = sorted(set(old_map) - set(new_map))
    changed = sorted(p for p in set(old_map) & set(new_map) if old_map[p] != new_map[p])
    print(f"scan.{name}: old {len(old)} new {len(new)} added {len(added)} removed {len(removed)} changed {len(changed)}")
    keyed = [p for p in added if new_map[p].get("r79_keys") or new_map[p].get("has_generated_key")]
    print(f"  added with r79 keys or generated key: {len(keyed)}")
    for path in keyed[:SHOWN]:
        entry = new_map[path]
        print("   ", path, entry.get("r79_keys"), entry.get("has_generated_key"))
    for path in added[:SHOWN]:
        print("  +", path)
    for path in removed[:SHOWN]:
        print("  -", path)
    for path in changed[:SHOWN]:
        print("  ~", path)


def main() -> None:
    old, new = load(sys.argv[1]), load(sys.argv[2])
    for key in sorted(set(old) | set(new)):
        if key == "scan":
            continue
        print(f"{key}: {'same' if old.get(key) == new.get(key) else 'DIFFERENT'}")
    old_scan, new_scan = old["scan"], new["scan"]
    for key in sorted(set(old_scan) | set(new_scan)):
        before, after = old_scan.get(key), new_scan.get(key)
        if isinstance(before, list) and before and isinstance(before[0], dict):
            report_list(key, before, after)
        else:
            print(f"scan.{key}: {before!r} -> {after!r}" if before != after else f"scan.{key}: same")


if __name__ == "__main__":
    main()
