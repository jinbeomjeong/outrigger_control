"""Every file listed in a SHA256SUMS.txt still has its sha256 (rules rev22 R22-3: the R3c
folder is read only; checked before and after the R3d run; python-expert 2026-11-15 draft).

Usage: python -I -B sums_check.py <folder with SHA256SUMS.txt> <out.json> [<relative path> ...]
With paths: only those entries (they must be listed). Exit codes: 0 all equal, 1 a difference,
a missing file or an unlisted path (S-11).
"""

import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    folder, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    wanted = sys.argv[3:]
    listed = {}
    for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            listed[name.strip()] = digest
    names = wanted or sorted(listed)
    rows, ok = [], True
    for name in names:
        path = folder / name
        now = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        same = name in listed and now == listed[name]
        ok &= same
        rows.append({"file": name, "listed": listed.get(name), "now": now, "same": same})
    out_path.write_text(json.dumps({"folder": str(folder), "entries": len(listed),
                                    "checked": len(rows), "all_same": ok, "files": rows},
                                   indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"entries": len(listed), "checked": len(rows), "all_same": ok}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
