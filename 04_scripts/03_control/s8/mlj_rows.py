"""Dump MLJ verify_S8C.json rows compactly (failed / flagged / selected)."""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\07_results\S8\mlj_20261025_080212")
d = json.loads((ROOT / "verify_S8C.json").read_text(encoding="utf-8"))
pat = sys.argv[1] if len(sys.argv) > 1 else None
case_pat = sys.argv[2] if len(sys.argv) > 2 else None


def short(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) < 160 else s[:160] + "..."


for r in d["rows"]:
    if case_pat and case_pat not in str(r.get("case")):
        continue
    if pat is None:
        if r.get("passed") is True:
            continue
    elif pat != "*" and pat.lower() not in str(r.get("item")).lower():
        continue
    extra = {k: v for k, v in r.items() if k not in ("item", "case", "value", "limit", "passed", "note", "kind", "source", "record_rate_hz")}
    print(f"[{r.get('case')}] {r.get('item')} | v={short(r.get('value'))} lim={short(r.get('limit'))} "
          f"pass={r.get('passed')} kind={r.get('kind')} src={r.get('source')} | {short(r.get('note'))} | {short(extra) if extra else ''}")
