"""Verify the neutral input copy against its SHA256SUMS and print the SUMS file hash."""
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
sums = root / "SHA256SUMS"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


print("SUMS", sha(sums))
listed = set()
bad = []
for line in sums.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    digest, name = line.split(None, 1)
    name = name.lstrip("*").strip()
    listed.add(Path(name).as_posix())
    p = root / name
    if not p.is_file():
        bad.append(("missing", name))
    elif sha(p) != digest.lower():
        bad.append(("mismatch", name))
present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
extra = sorted(present - listed - {"SHA256SUMS"})
print("listed", len(listed), "present", len(present), "bad", len(bad), "extra", len(extra))
for b in bad[:20]:
    print(b)
for e in extra[:20]:
    print("extra", e)
tops = {}
for n in listed:
    t = n.split("/")[0]
    tops[t] = tops.get(t, 0) + 1
print(tops)
