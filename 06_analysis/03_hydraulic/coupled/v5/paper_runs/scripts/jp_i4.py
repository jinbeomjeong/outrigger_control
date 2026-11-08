"""Print I4 and item 6 rows of the 12 J_P verify files, and the reapproach events after the event."""
import json
import sys
from pathlib import Path

vdir = Path(sys.argv[1])
for f in sorted(vdir.glob("verify_*.json")):
    d = json.loads(f.read_text("utf-8"))
    for r in d["rows"]:
        if r["item"].startswith("I4 classification") or r["item"].startswith("6 ") or "reapproach" in r["item"].lower():
            print(f.stem, "|", r["item"], "|", json.dumps(r.get("value"))[:160], "| limit", json.dumps(r.get("limit"))[:120],
                  "|", r.get("passed"), "|", (r.get("note") or "")[:160])
