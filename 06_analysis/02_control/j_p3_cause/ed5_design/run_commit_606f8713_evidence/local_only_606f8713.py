"""Local-only list and backup of the 606f8713 l1ref files over 100 MB (never overwrites)."""

import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(r"C:\workspace\outrigger_control")
RUN_FOLDER = REPO / "06_analysis/02_control/j_p3_cause/j9_runs/606f8713"
BACKUP = Path(r"C:\Users\jinbeom\.claude\backups\outrigger-ed5\606f8713_l1ref_a1")
LOCAL_ONLY_NAMES = ("L1_VBJ.json", "L1_VBJ.json.partial.jsonl")
GITHUB_LIMIT_BYTES = 100 * 1024 * 1024
CHUNK_BYTES = 1 << 22


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    local_list = RUN_FOLDER / "l1ref_a1_LOCAL_ONLY.SHA256SUMS"
    for path in (local_list, BACKUP):
        if path.exists():
            print(f"STOP: {path} exists")
            sys.exit(2)
    big = sorted(
        p.relative_to(REPO).as_posix()
        for p in RUN_FOLDER.rglob("*")
        if p.is_file() and p.stat().st_size >= GITHUB_LIMIT_BYTES
    )
    print("files over 100 MB:", big)
    local_only = [RUN_FOLDER / "l1ref_a1" / name for name in LOCAL_ONLY_NAMES]
    if sorted(p.relative_to(REPO).as_posix() for p in local_only) != big:
        print("STOP: the files over 100 MB are not exactly the local-only pair")
        sys.exit(2)
    digests = {path: sha256_of(path) for path in local_only}
    local_list.write_bytes(
        "".join(f"{d} *{p.relative_to(REPO).as_posix()}\n" for p, d in digests.items()).encode("ascii")
    )
    BACKUP.mkdir(parents=True)
    lines = []
    for path, digest in digests.items():
        copy = BACKUP / path.name
        shutil.copy2(path, copy)
        if sha256_of(copy) != digest:
            print(f"STOP: backup differs for {path.name}")
            sys.exit(3)
        lines.append(f"{digest} *{copy.name}\n")
    (BACKUP / "SHA256SUMS").write_bytes("".join(lines).encode("ascii"))
    for path, digest in digests.items():
        print(path.name, digest[:8])


if __name__ == "__main__":
    main()
