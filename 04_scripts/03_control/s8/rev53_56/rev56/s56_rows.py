"""Dump selected verify rows in full (by item substring) for a verify JSON."""
import json
import sys
from pathlib import Path

f = Path(sys.argv[1])
subs = sys.argv[2:]
d = json.loads(f.read_text(encoding="utf-8"))
for r in d["rows"]:
    if not subs or any(s in r["item"] for s in subs):
        print(json.dumps(r, ensure_ascii=False, default=str, indent=None))
        print()
