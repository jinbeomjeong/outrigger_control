"""Summarise S8 verify files: failed judged rows, C-S8-36 / C-S8-37 / C-S8-40 / U-S8-32 / I1 rows.

Moved from the cad scratchpad (``cad-run/summ54.py``, 2026-10-25).

usage::

    python -I -X utf8 summ54.py <verify_*.json> [...]
"""
import json
import sys
from pathlib import Path

for p in map(Path, sys.argv[1:]):
    doc = json.loads(p.read_text(encoding="utf-8"))
    m = doc["meta"]
    print(f"===== {p}\n rows {m['rows']} failed {m['failed']} rev {str(m.get('judge_revision'))[:40]}"
          f" ref {m.get('ref_twist_work') or m.get('ref_batch')}")
    for r in doc["rows"]:
        if r["passed"] is False:
            print("  FAIL:", r["item"][:120], "|", r["case"], "|", str(r["value"])[:160])
    for r in doc["rows"]:
        it = r["item"]
        if it.startswith(("C-S8-36", "C-S8-40", "C-S8-37")) or ("U-S8-32" in it and r["case"] == "*") \
                or it.startswith("I1 J_C"):
            print("  ROW:", it[:140], "| case", r["case"])
            print("       kind", r["kind"], "passed", r["passed"], "value", str(r["value"])[:260])
            if r.get("note"):
                print("       note", str(r["note"])[:700])
            if r.get("per_run") and "FLAG" in it:
                print("       per_run", json.dumps(r["per_run"])[:1500])
