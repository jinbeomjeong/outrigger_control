"""Compare the work-tree mtime of every file a commit changed with the commit time."""

import json
import subprocess
import sys
from pathlib import Path


def git(worktree: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(worktree), *arguments], check=True,
                          capture_output=True, text=True).stdout


def main() -> int:
    worktree, commit, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    commit_time = int(git(worktree, "log", "-1", "--format=%ct", commit).strip())
    parent = git(worktree, "rev-parse", f"{commit}^").strip()
    names = git(worktree, "diff", "--name-only", parent, commit).split()
    rows = []
    for name in names:
        mtime = (worktree / name).stat().st_mtime
        rows.append({"path": name, "mtime_minus_commit_s": round(mtime - commit_time, 3)})
    after = [row["path"] for row in rows if row["mtime_minus_commit_s"] > 0]
    report = {"commit": commit, "commit_time": commit_time, "files": len(rows),
              "after_commit": after, "rows": rows}
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"files": len(rows), "after_commit": len(after)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
