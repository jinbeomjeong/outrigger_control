"""List keys / shapes of one ML episode's records and its settings.episode / ml_meta.

Usage: python -I s8ml_keys.py <case_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
for name in ("r8_series.npz", "pads.npz", "s8_series.npz"):
    d = np.load(case / name, allow_pickle=True)
    print(name, {k: d[k].shape for k in d.files})
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
print("result keys", list(res.keys()))
st = res.get("settings", {})
print("settings keys", list(st.keys()))
for k in ("episode", "branch_t_s", "ml_meta"):
    if k in st:
        print(k, json.dumps(st[k], ensure_ascii=False)[:1500])
ev = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
print("events type", type(ev), (list(ev.keys()) if isinstance(ev, dict) else len(ev)))
items = ev if isinstance(ev, list) else ev.get("events", [])
for e in items[:400]:
    s = json.dumps(e, ensure_ascii=False)
    if any(x in s for x in ("ROD", "FALLBACK", "SETTLE", "settle", "REAPPROACH", "R5", "PRED")):
        print(" ", s[:300])
print([p.name for p in (case / "record").iterdir()][:20])
