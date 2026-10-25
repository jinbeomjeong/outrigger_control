"""H-S8-2: keys of record/record.npz and the rod-side parts of result.json / pads meta.

Usage: python -I h_s8_2_record_keys.py <case_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
with np.load(case / "record" / "record.npz", allow_pickle=True) as z:
    for k in z.files:
        a = z[k]
        print(f"   {k:40s} {a.dtype} {a.shape}")
meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))


def walk(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{path}.{k}" if path else k
            if any(s in k.lower() for s in ("rod", "lock", "dead", "beta", "bulk", "stroke", "valve", "counter")):
                s = json.dumps(v)
                print("META", p, s[:400])
            else:
                walk(v, p)


walk(meta)
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
walk(res)
with np.load(case / "pads.npz", allow_pickle=True) as z:
    print("pads meta:", str(z["meta_json"])[:2400])
