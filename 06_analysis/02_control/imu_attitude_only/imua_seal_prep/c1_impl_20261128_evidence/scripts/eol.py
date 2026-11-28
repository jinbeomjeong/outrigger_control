"""Count CRLF and bare LF line ends of files; with --to-crlf convert bare LF files to CRLF."""
import sys
from pathlib import Path

conv = "--to-crlf" in sys.argv
for name in [a for a in sys.argv[1:] if a != "--to-crlf"]:
    p = Path(name)
    b = p.read_bytes()
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    print(f"{name}: CRLF {crlf} bare LF {lf}")
    if conv and lf:
        p.write_bytes(b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        print("  -> converted to CRLF")
