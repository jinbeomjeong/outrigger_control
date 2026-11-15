"""R21-4 reuse check: files copied from the R3b output folder have the sha256 recorded in the R3b
``SHA256SUMS.txt`` (python-expert 2026-11-15).

Usage: python -I -B reuse_check.py <R3b folder> <R3c folder> <out.json> <relative path> [...]
Exit codes: 0 all equal, 1 a difference or a missing record.
"""

import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    old, new, out_path = map(Path, sys.argv[1:4])
    recorded = {}
    for line in (old / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            recorded[name.strip()] = digest
    rows, ok = [], True
    for rel in sys.argv[4:]:
        now = hashlib.sha256((new / rel).read_bytes()).hexdigest()
        same = recorded.get(rel) == now
        ok &= same
        rows.append({"file": rel, "r3b_recorded": recorded.get(rel), "r3c_copy": now, "same": same})
    out_path.write_text(json.dumps({"all_same": ok, "files": rows}, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({"all_same": ok, "files": len(rows)}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
