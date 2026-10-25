"""Compact listing of verify_S8ML.json rows (rev. 48 review of the ML pilot rerun).

Usage: python -I s8ml2_rows.py <batch_dir> [maxlen]
ML-1 forced-retract rows are summarised (count, fallback, F2 max) instead of printed one by one.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
batch = Path(sys.argv[1])
maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 600
v = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
forced = []
for r in v["rows"]:
    item = r.get("item", "")
    if item.startswith("ML-1 forced retract episode"):
        forced.append(r)
        continue
    val = json.dumps(r.get("value"), ensure_ascii=False)
    note = str(r.get("note", ""))
    extra = {k: x for k, x in r.items() if k not in ("item", "case", "value", "limit", "passed", "note", "kind", "source", "failed")}
    print(f"- [{r.get('kind')}] {item} | case={r.get('case')} | passed={r.get('passed')} | limit={r.get('limit')}")
    print(f"    value={val[:maxlen]}")
    print(f"    note={note[:maxlen]}")
    if extra:
        print(f"    extra={json.dumps(extra, ensure_ascii=False)[:maxlen]}")
print(f"\nML-1 forced rows: {len(forced)}")
for r in forced:
    note = r.get("note", "")
    fb = r.get("fallback")
    fw = r.get("forced_window", {})
    print(f"  {r['case']}: leg {fw.get('leg')} start {fw.get('start_s'):.1f} done {fw.get('done_s')} fallback {fb} | {note.split(';')[1] if ';' in note else ''}")
