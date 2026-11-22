"""Pathspec list for the 606f8713 prep commit: ed5_inputs and the run folder minus local-only files."""

import sys
from pathlib import Path

REPO = Path(r"C:\workspace\outrigger_control")
CAUSE = REPO / "06_analysis/02_control/j_p3_cause"
ROOTS = (CAUSE / "prelaunch_j9/ed5_inputs", CAUSE / "j9_runs/606f8713")
LOCAL_ONLY = {
    CAUSE / "j9_runs/606f8713/l1ref_a1/L1_VBJ.json",
    CAUSE / "j9_runs/606f8713/l1ref_a1/L1_VBJ.json.partial.jsonl",
}
GITHUB_LIMIT_BYTES = 100 * 1024 * 1024


def main() -> None:
    files = sorted(
        (p for root in ROOTS for p in root.rglob("*") if p.is_file() and p not in LOCAL_ONLY),
        key=lambda p: p.as_posix(),
    )
    too_big = [p for p in files if p.stat().st_size >= GITHUB_LIMIT_BYTES]
    if too_big:
        print("STOP: over 100 MB:", too_big)
        sys.exit(2)
    Path(sys.argv[1]).write_bytes(
        "".join(f"{p.relative_to(REPO).as_posix()}\n" for p in files).encode("utf-8")
    )
    for root in ROOTS:
        print(root.name, sum(1 for p in files if root in p.parents))
    largest = max(files, key=lambda p: p.stat().st_size)
    print("total", len(files), "largest", largest.name, largest.stat().st_size)


if __name__ == "__main__":
    main()
