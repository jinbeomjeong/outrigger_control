"""H-S8-2: list the record keys of one case (pads.npz, r8_series.npz, s8_series.npz, record/).

Usage: python -I h_s8_2_keys.py <case_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
for name in ("pads.npz", "r8_series.npz", "s8_series.npz"):
    p = case / name
    if not p.exists():
        continue
    with np.load(p, allow_pickle=True) as z:
        print(name)
        for k in z.files:
            a = z[k]
            print(f"   {k:32s} {a.dtype} {a.shape}")
rec = case / "record"
if rec.exists():
    for p in sorted(rec.rglob("*"))[:60]:
        print("record:", p.relative_to(case), p.stat().st_size if p.is_file() else "")
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
print("result keys:", list(res)[:80])
cj = json.loads((case / "case.json").read_text(encoding="utf-8"))
print("case.json:", json.dumps(cj)[:3000])
