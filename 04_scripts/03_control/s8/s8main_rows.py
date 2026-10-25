"""Rev. 51: list non-passing / flagged rows of the main ML batch verify_S8ML.json.

Usage: python -I s8main_rows.py <batch_dir> [maxlen] [pattern]
Prints judge meta, counts by kind/passed, every row with passed False (or None with kind gate),
and rows whose item contains <pattern> (optional).
"""
import collections
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
batch = Path(sys.argv[1])
maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 800
pat = sys.argv[3] if len(sys.argv) > 3 else None
v = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
print("top keys", list(v.keys()))
meta = {k: x for k, x in v.items() if k != "rows"}
print(json.dumps(meta, ensure_ascii=False)[:3000])
rows = v["rows"]
cnt = collections.Counter((r.get("kind"), r.get("passed")) for r in rows)
print("counts", dict(cnt))
items = collections.Counter(r.get("item", "")[:70] for r in rows)
print("items (top 60):")
for k, n in items.most_common(60):
    print(f"  {n:5d}  {k}")


def show(r):
    val = json.dumps(r.get("value"), ensure_ascii=False)
    extra = {k: x for k, x in r.items() if k not in ("item", "case", "value", "limit", "passed", "note", "kind")}
    print(f"- [{r.get('kind')}] {r.get('item')} | case={r.get('case')} | passed={r.get('passed')} | limit={r.get('limit')}")
    print(f"    value={val[:maxlen]}")
    print(f"    note={str(r.get('note', ''))[:maxlen]}")
    if extra:
        print(f"    extra={json.dumps(extra, ensure_ascii=False)[:maxlen]}")


print("\n=== failed rows ===")
for r in rows:
    if r.get("passed") is False:
        show(r)
if pat:
    print(f"\n=== rows matching {pat!r} ===")
    for r in rows:
        if pat in str(r.get("item", "")) and r.get("passed") is not False:
            show(r)
