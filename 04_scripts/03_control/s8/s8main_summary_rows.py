"""Rev. 51: print the single summary rows (not per-episode U-S8-32 / ML-1 forced rows) of the
main ML verify_S8ML.json, the ml_metrics block and the ml_masks summary.

Usage: python -I s8main_summary_rows.py <batch_dir> [maxlen]
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
batch = Path(sys.argv[1])
maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
v = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
for r in v["rows"]:
    it = r.get("item", "")
    if it.startswith("U-S8-32 event legs") or it.startswith("U-S8-32 adjacent legs") or it.startswith("ML-1 forced retract episode"):
        continue
    print(f"- [{r.get('kind')}] {it} | case={r.get('case')} | passed={r.get('passed')} | limit={r.get('limit')}")
    print(f"    value={json.dumps(r.get('value'), ensure_ascii=False)[:maxlen]}")
    print(f"    note={str(r.get('note', ''))[:maxlen]}")
print("\nml_metrics:", json.dumps(v.get("ml_metrics"), ensure_ascii=False)[:4000])
masks = v.get("ml_masks", {})
from collections import Counter
print(f"\nml_masks: {len(masks)} entries; reasons {Counter(tuple(m.get('reasons', [])) for m in masks.values())}")
