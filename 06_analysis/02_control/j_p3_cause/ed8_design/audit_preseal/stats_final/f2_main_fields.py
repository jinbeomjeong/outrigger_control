"""Ed. 8 S8-R final review, part 2: v5/main.jsonl top-level field names and event-name fields (no metric values).

Writes: top-level key counts; for lines with a non-empty event_output, the counts of candidate
event-name / fast fields found at top level or inside a twin/job dict (key names and the event
name strings only, which are pre-treatment case labels).
Usage: python -I -B f2_main_fields.py <out_folder>
"""
import json
import sys
from collections import Counter
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl")
out = Path(sys.argv[1])
top = Counter()
nested = Counter()
label_fields = Counter()
for line in MAIN.open(encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    top.update(r.keys())
    eo = r.get("event_output") or {}
    for k, v in r.items():
        if isinstance(v, dict) and k != "event_output":
            nested.update(f"{k}.{kk}" for kk in v.keys())
    if eo:
        for k in ("event", "event_name", "case", "fast", "setting", "config", "twin"):
            if k in r:
                val = r[k]
                label_fields[f"top.{k}={val if isinstance(val, (str, bool)) else type(val).__name__}"] += 1
        for k in ("twin", "job", "case_spec"):
            if isinstance(r.get(k), dict):
                for kk in ("event", "fast", "leg", "kind"):
                    if kk in r[k]:
                        val = r[k][kk]
                        label_fields[f"{k}.{kk}={val if isinstance(val, (str, bool)) else type(val).__name__}"] += 1
res = {"top_keys": dict(top), "nested_keys": dict(nested), "event_line_labels": dict(label_fields)}
(out / "f2_main_fields.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"status": "ok"}))
