"""Write SHA256SUMS for every file in the given folder except SHA256SUMS itself (sorted, LF)."""
import hashlib
import sys
from pathlib import Path

d = Path(sys.argv[1])
lines = []
for p in sorted(d.iterdir()):
    if p.is_file() and p.name != "SHA256SUMS":
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
(d / "SHA256SUMS").write_bytes(("\n".join(lines) + "\n").encode("ascii"))
print("\n".join(lines))
