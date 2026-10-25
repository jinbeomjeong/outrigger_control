"""Show selected s6 common rows of RE1b / settlement cases in reference batches."""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\07_results\S8")
ITEMS = ("3 F_min (1 ms)", "4 max moving pressure", "5a rocking amplitude", "6 min after settlement")
case_pat = sys.argv[1] if len(sys.argv) > 1 else "RE1b"
for b in sorted(ROOT.iterdir()):
    for name in ("verify_S8C.json", "verify_S8ML.json"):
        f = b / name
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        for r in d["rows"]:
            if case_pat in str(r.get("case")) and any(r.get("item", "").startswith(i) for i in ITEMS):
                v = r.get("value")
                v = f"{v:.4g}" if isinstance(v, float) else v
                print(f"{b.name}/{name} [{r['case']}] {r['item']} v={v} lim={r.get('limit')} pass={r.get('passed')} kind={r.get('kind')} | {str(r.get('note'))[:120]}")
