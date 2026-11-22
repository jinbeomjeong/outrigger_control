"""Count late files and their same-as-commit flags in baseline_check identity json reports."""

import json
import sys
from collections import Counter
from pathlib import Path


def main() -> None:
    for report_path in sorted(Path(sys.argv[1]).glob("*.json")):
        mtime = json.loads(report_path.read_text(encoding="utf-8"))["mtime"]
        flags = Counter(str(item["same_as_commit_now"]) for item in mtime["late_files"])
        before_run = sum(1 for item in mtime["late_files"] if item["before_run"])
        times = sorted(item["mtime"] for item in mtime["late_files"])
        print(
            report_path.stem,
            f"changed={mtime['changed_files']} late={len(mtime['late_files'])}",
            f"before_run={before_run} same={dict(flags)}",
            f"commit={mtime['commit_time']} mtimes={times[0]}..{times[-1]}",
        )


if __name__ == "__main__":
    main()
