"""Show the structure of rev80 harness files and their settle blocks (read-only)."""
import json
import sys
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev80")
for n in sys.argv[1:]:
    doc = json.loads((D / n).read_text(encoding="utf-8"))
    print("==", n, type(doc).__name__, list(doc)[:10] if isinstance(doc, dict) else len(doc))
    meta = doc.get("meta", {}) if isinstance(doc, dict) else {}
    print("   meta keys:", list(meta)[:30])
    recs = None
    for k in ("results", "records", "rows", "cases"):
        if isinstance(doc, dict) and k in doc:
            recs = doc[k]
            break
    if recs is None:
        continue
    seq = list(recs.values()) if isinstance(recs, dict) else recs
    print("   n:", len(seq))
    r = seq[0]
    print("   rec keys:", list(r)[:40])
    for key in ("settle", "settle_check", "settle_error"):
        if key in r:
            print("   ", key, json.dumps(r[key])[:900])
    print("   id/case:", r.get("id"), json.dumps(r.get("case"))[:300])
