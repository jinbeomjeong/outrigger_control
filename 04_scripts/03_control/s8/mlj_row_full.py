"""Print full JSON of rows whose item contains a pattern (and case pattern)."""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\07_results\S8\mlj_20261025_080212")
d = json.loads((ROOT / "verify_S8C.json").read_text(encoding="utf-8"))
pat, case_pat = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
for r in d["rows"]:
    if pat.lower() in str(r.get("item")).lower() and case_pat in str(r.get("case")):
        print(json.dumps(r, ensure_ascii=True, indent=1)[:6000])
        print("-----")
