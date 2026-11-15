"""R18-2a view reuse check for the R3b path 1 judgement (python-expert 2026-11-15).

The R3 view (``judge_576eb87/chrono_path1/chrono_view``) is reused when ``make_view.py`` has the
sealed sha256 prefix and every source and copy in ``view_map.json`` still has the recorded sha256.

Usage: python -I -B view_check.py <view folder> <out.json>
Exit codes: 0 reusable, 1 a sha differs (rebuild the view), 2 input missing.
"""

import hashlib
import json
import sys
from pathlib import Path

MAKE_VIEW_SHA_PREFIX = "adb01782"
VIEW_MAP_SHA_PREFIX = "1b2c500f"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    view, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    map_path = view / "view_map.json"
    if not map_path.is_file():
        print("view_map.json missing")
        return 2
    doc = json.loads(map_path.read_text(encoding="utf-8"))
    problems, checked = [], 0
    for entry in doc["entries"]:
        for side, key in (("source", "sha256_source"), ("copy", "sha256_copy")):
            got = sha256(Path(entry[side]))
            checked += 1
            if got != entry[key]:
                problems.append({"case": entry.get("case"), "side": side, "path": entry[side],
                                 "recorded": entry[key], "now": got})
    report = {"make_view_sha256": sha256(view / "make_view.py"),
              "view_map_sha256": sha256(map_path), "entries": len(doc["entries"]),
              "files_checked": checked, "problems": problems}
    report["make_view_ok"] = str(report["make_view_sha256"]).startswith(MAKE_VIEW_SHA_PREFIX)
    report["view_map_ok"] = str(report["view_map_sha256"]).startswith(VIEW_MAP_SHA_PREFIX)
    report["reusable"] = report["make_view_ok"] and report["view_map_ok"] and not problems
    out_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("entries", "files_checked", "make_view_ok",
                                             "view_map_ok", "reusable")}))
    return 0 if report["reusable"] else 1


if __name__ == "__main__":
    sys.exit(main())
