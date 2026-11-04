"""Print harness C4G1 rows of R4 / R9 / S7 from the touch_phase tables. Read only.

Usage: python -I -B -X utf8 peek_touch.py
"""
from __future__ import annotations

import json
from pathlib import Path

T = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase")


def main() -> None:
    doc = json.loads((T / "rows_C4G1_compare.json").read_text(encoding="utf-8"))
    print(type(doc).__name__, list(doc)[:20] if isinstance(doc, dict) else len(doc))
    print(json.dumps(doc, ensure_ascii=False)[:2500])
    for line in (T / "rows_C4G1.jsonl").read_text(encoding="utf-8").splitlines()[:40]:
        r = json.loads(line)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in ("id", "case", "row", "tau_te", "D_te", "D_lift", "F_min", "leg", "t_ready", "paused", "paused_periods", "target_mm")})
    t = json.loads((T / "bias_C4G1_table.json").read_text(encoding="utf-8"))
    print("bias", json.dumps(t, ensure_ascii=False)[:1800])


if __name__ == "__main__":
    main()
