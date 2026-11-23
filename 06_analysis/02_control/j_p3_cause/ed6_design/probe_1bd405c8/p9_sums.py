"""Write SHA256SUMS (LF) of this folder and print the edition 6 draft sha."""
import hashlib
from pathlib import Path

OUT = Path(__file__).resolve().parent
SPEC = OUT.parents[1] / "jp3_remedy_spec_v6.md"
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
lines = [f"{h(p)}  {p.name}" for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(OUT / "SHA256SUMS").write_bytes(("\n".join(lines) + "\n").encode())
print("\n".join(lines))
print("spec_v6", h(SPEC))
