"""List the C-5 rows of the 436.8 manifest (case, engine, setting, est, argv tail)."""
import json
import sys
from pathlib import Path

doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
batches = doc.get("batches") or doc
print(type(batches).__name__, list(batches)[:3] if isinstance(batches, dict) else len(batches))
if isinstance(batches, dict):
    for name, v in batches.items():
        print(name, type(v).__name__, list(v)[:8] if isinstance(v, dict) else len(v))
    batches = {k: (v.get("rows") if isinstance(v, dict) else v) for k, v in batches.items()}
for name, rows in (batches.items() if isinstance(batches, dict) else []):
    if not name.endswith("C5") and not name.endswith("C1"):
        continue
    if not isinstance(rows, list):
        continue
    for r in rows:
        print(name, r.get("case"), r.get("s8c_case_id"), (r.get("r4368") or {}).get("engine"),
              r.get("v5_setting"), r.get("est_s"), " ".join(r.get("argv_tail") or [])[:220])
print(list(doc.keys())[:20])
