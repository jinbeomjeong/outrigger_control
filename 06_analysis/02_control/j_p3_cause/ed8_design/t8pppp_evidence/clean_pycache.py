"""Remove the ignored ``__pycache__`` folders git lists in the ed8-judge4 worktree (only paths
whose last part is ``__pycache__``; every other path is left and printed)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4")


def main() -> int:
    status = subprocess.run(["git", "-C", str(WT), "status", "--porcelain", "--ignored"],
                            capture_output=True, encoding="utf-8", timeout=120, check=True).stdout
    removed, kept = [], []
    for line in status.splitlines():
        path = line[3:].rstrip("/")
        target = (WT / path).resolve()
        is_pycache = (line.startswith("!! ") and target.name == "__pycache__"
                      and target.is_relative_to(WT.resolve()) and target.is_dir())
        if is_pycache:
            shutil.rmtree(target)
            removed.append(path)
        else:
            kept.append(line)
    print(f"removed {len(removed)}: {removed}")
    print(f"kept {len(kept)}: {kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
