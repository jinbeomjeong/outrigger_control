"""Print the judge meta of S8 verify files (revision head, ref / lookup batches, rows, failed).

Moved from the cad scratchpad (``cad-run/verify_meta.py``, 2026-10-25).

usage::

    python -I -X utf8 verify_meta.py <verify_*.json> [...]
"""
import json
import sys
from pathlib import Path

for p in map(Path, sys.argv[1:]):
    if not p.exists():
        print(p, "MISSING")
        continue
    doc = json.loads(p.read_text(encoding="utf-8"))
    m = doc["meta"]
    print("==", p, f"{p.stat().st_size / 1e6:.1f} MB")
    print("  rev:", str(m.get("judge_revision"))[:90])
    print("  ref_batch:", m.get("ref_batch"), "lookup:", m.get("lookup_batches"),
          "ref_twist_work:", m.get("ref_twist_work"))
    print("  rows:", m.get("rows"), "failed:", m.get("failed"))
