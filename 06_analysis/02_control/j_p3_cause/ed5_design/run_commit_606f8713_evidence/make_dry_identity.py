"""Write a synthetic identity record (head, clean, now) for a dry baseline_check identity run."""

import json
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    folder, head = Path(sys.argv[1]), sys.argv[2]
    folder.mkdir(parents=True, exist_ok=False)
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    block = {"time": now, "git": {"head": head, "is_clean": True}}
    record = {"start": [block], "end": [block]}
    (folder / "dry.identity.json").write_text(json.dumps(record), encoding="utf-8")
    print("written", now)


if __name__ == "__main__":
    main()
