"""Back up the run's npz files and add them to the LOCAL_ONLY list (user decision 2026-11-27).

Each npz under j9_runs/56849248 is hashed, checked against RUN_ALL.SHA256SUMS, copied to the
backup folder under its repo-relative path (never overwriting) and hashed again there. Lines
`<sha256> *<repo-relative path>` are appended to 56849248_LOCAL_ONLY.SHA256SUMS (LF), and the
updated list is copied to the backup. Prints counts only. Exit 0 ok / 1 a mismatch or refusal.

Usage: python -I -B npz_local_only.py [--apply]   (without --apply: check only, write nothing)
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(r"C:\workspace\outrigger_control")
RUN = REPO / "06_analysis/02_control/j_p3_cause/j9_runs/56849248"
LIST = RUN.parent / "56849248_LOCAL_ONLY.SHA256SUMS"
BACKUP = Path(r"C:\Users\jinbeom\.claude\backups\outrigger-ed8\j9_runs_56849248")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(apply: bool) -> int:
    run_all = {}
    for line in (RUN / "RUN_ALL.SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split(None, 1)
        run_all[rel.lstrip("*").strip()] = digest
    listed = {line.split(None, 1)[1].lstrip("*") for line in
              LIST.read_text(encoding="utf-8").splitlines() if line.strip()}
    npz = sorted(RUN.rglob("*.npz"))
    problems, new_lines, copied = [], [], 0
    for path in npz:
        rel_run = path.relative_to(RUN).as_posix()
        rel_repo = path.relative_to(REPO).as_posix()
        digest = sha256(path)
        if run_all.get(rel_run) != digest:
            problems.append(f"RUN_ALL mismatch or missing: {rel_run}")
            continue
        if rel_repo in listed:
            problems.append(f"already listed: {rel_repo}")
            continue
        target = BACKUP / rel_repo
        if target.exists():
            problems.append(f"backup exists: {rel_repo}")
            continue
        new_lines.append(f"{digest} *{rel_repo}")
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if sha256(target) != digest:
                problems.append(f"backup copy differs: {rel_repo}")
            copied += 1
    if problems:
        print("\n".join(problems[:20]))
        print(f"problems {len(problems)}")
        return 1
    if apply:
        with LIST.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(new_lines) + "\n")
        list_copy = BACKUP / LIST.relative_to(REPO)
        shutil.copy2(LIST, list_copy)
        print(f"list sha256 {sha256(LIST)} lines {len(LIST.read_text(encoding='utf-8').splitlines())}")
    print(f"npz {len(npz)} new_lines {len(new_lines)} copied {copied} apply {apply}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv[1:]))
