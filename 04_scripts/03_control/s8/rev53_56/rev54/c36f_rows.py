"""Dump judged/recorded rows of verify JSON files compactly."""
import json
import sys


def short(v, n=220):
    s = json.dumps(v, ensure_ascii=False, default=str) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + "..."


for name in sys.argv[1:]:
    with open(name, encoding="utf-8") as f:
        d = json.load(f)
    rows = d.get("rows", [])
    m = d.get("meta", {})
    print("=====", name)
    print("meta:", short({k: m[k] for k in m if k in ("rows", "failed", "judge_revision", "plan")}, 600))
    for i, r in enumerate(rows):
        print(f"[{i}] {r.get('kind')} pass={r.get('passed')} | {short(r.get('item'),160)} | case={short(r.get('case'),60)} | value={short(r.get('value'),200)} | limit={short(r.get('limit'),60)}")
        note = r.get("note")
        if note:
            print("      note:", short(note, 400))
