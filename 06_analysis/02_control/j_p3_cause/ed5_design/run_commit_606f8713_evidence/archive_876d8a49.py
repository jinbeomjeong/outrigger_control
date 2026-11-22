"""Archive the 876d8a49 prelaunch (erratum 6 6-4): move ed5_inputs, local-only list, backup, SUMS.

Writes nothing that already exists (stops with exit 2), prints counts only.
"""

import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(r"C:\workspace\outrigger_control")
CAUSE = "06_analysis/02_control/j_p3_cause"
RUN_FOLDER = REPO / CAUSE / "j9_runs" / "876d8a49"
SOURCE_INPUTS = REPO / CAUSE / "prelaunch_j9" / "ed5_inputs"
BACKUP = Path(r"C:\Users\jinbeom\.claude\backups\outrigger-ed5\876d8a49_l1ref_a1")
LOCAL_ONLY_NAMES = ("L1_VBJ.json", "L1_VBJ.json.partial.jsonl")
GITHUB_LIMIT_BYTES = 100 * 1024 * 1024
CHUNK_BYTES = 1 << 22


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def refuse_existing(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            print(f"STOP: {path} exists")
            sys.exit(2)


def main() -> None:
    target_inputs = RUN_FOLDER / "ed5_inputs"
    local_only_list = RUN_FOLDER / "l1ref_a1_LOCAL_ONLY.SHA256SUMS"
    sums = RUN_FOLDER / "SHA256SUMS"
    refuse_existing(target_inputs, local_only_list, sums, BACKUP)
    if not SOURCE_INPUTS.is_dir():
        print(f"STOP: {SOURCE_INPUTS} missing")
        sys.exit(2)

    shutil.move(str(SOURCE_INPUTS), str(target_inputs))
    print("moved ed5_inputs files:", sum(1 for p in target_inputs.rglob("*") if p.is_file()))

    local_only = [RUN_FOLDER / "l1ref_a1" / name for name in LOCAL_ONLY_NAMES]
    local_lines = [f"{sha256_of(path)} *{repo_path(path)}\n" for path in local_only]
    local_only_list.write_bytes("".join(local_lines).encode("ascii"))

    BACKUP.mkdir(parents=True)
    backup_lines = []
    for path in local_only:
        copy = BACKUP / path.name
        shutil.copy2(path, copy)
        if sha256_of(copy) != sha256_of(path):
            print(f"STOP: backup sha differs for {path.name}")
            sys.exit(3)
        backup_lines.append(f"{sha256_of(copy)} *{copy.name}\n")
    (BACKUP / "SHA256SUMS").write_bytes("".join(backup_lines).encode("ascii"))

    files = sorted(
        (p for p in RUN_FOLDER.rglob("*") if p.is_file() and p != sums),
        key=repo_path,
    )
    sums.write_bytes(
        "".join(f"{sha256_of(p)} *{repo_path(p)}\n" for p in files).encode("utf-8")
    )

    to_add = [p for p in files if p not in local_only] + [sums]
    too_big = [repo_path(p) for p in to_add if p.stat().st_size >= GITHUB_LIMIT_BYTES]
    pathspec = Path(sys.argv[1])
    pathspec.write_bytes("".join(f"{repo_path(p)}\n" for p in to_add).encode("utf-8"))
    largest = max(to_add, key=lambda p: p.stat().st_size)
    print("sums lines:", len(files))
    print("to add:", len(to_add), "local only:", len(local_only))
    print("largest to add:", repo_path(largest), largest.stat().st_size)
    print("over 100 MB in add list:", too_big)
    print("local-only list lines:", len(local_lines), "backup files:", len(backup_lines))


if __name__ == "__main__":
    main()
