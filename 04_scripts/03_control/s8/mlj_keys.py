"""List keys of one MLJ case directory (case.json, result.json, npz files)."""
import json
import sys
from pathlib import Path

import numpy as np

d = Path(sys.argv[1])
case = json.loads((d / "case.json").read_text(encoding="utf-8"))
print("case.json:", json.dumps(case, ensure_ascii=True)[:3000])
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
print("result keys:", list(res.keys()))
print("settings:", json.dumps(res.get("settings"), ensure_ascii=True)[:3000])
for k in ("event_t_s", "phases", "end_cause"):
    print(k, str(res.get(k))[:1500])
for name in ("pads.npz", "r8_series.npz", "s8_series.npz"):
    f = d / name
    if f.exists():
        z = np.load(f, allow_pickle=True)
        print(name, {k: z[k].shape for k in z.files})
rec = d / "record"
if rec.exists():
    for f in rec.iterdir():
        print("record/", f.name)
        if f.suffix == ".npz":
            z = np.load(f, allow_pickle=True)
            print({k: z[k].shape for k in z.files})
