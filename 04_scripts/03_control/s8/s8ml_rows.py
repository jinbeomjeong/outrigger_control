"""Print verify_S8ML.json rows (without the bulky 'failed' dict) and the plan of chosen episodes.

Usage: python -I s8ml_rows.py <batch_dir> [episode_id ...]
"""
import json
import sys
from pathlib import Path

batch = Path(sys.argv[1])
want = sys.argv[2:]
v = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
print(json.dumps(v["meta"], indent=1, ensure_ascii=False)[:1500])
for r in v["rows"]:
    r = {k: val for k, val in r.items() if k != "failed"}
    s = json.dumps(r, ensure_ascii=False)
    print("-", s[:2500])
plan = json.loads((batch / "ml_plan.json").read_text(encoding="utf-8"))
print("plan keys:", list(plan.keys()))
for bid, eps in plan.get("episodes", {}).items():
    for ep in eps:
        if ep["episode_id"] in want:
            print(json.dumps(ep, ensure_ascii=False))
for b in plan.get("bases", []):
    bid = b.get("base_id") if isinstance(b, dict) else None
    if bid and any(w.startswith(bid + "_") for w in want):
        print("BASE", json.dumps(b, ensure_ascii=False))
