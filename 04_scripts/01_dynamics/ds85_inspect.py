"""D-S8-5 helper: list keys of one S8 case record (r8_series, s8_series, pads, case/result json).

Usage: python -I ds85_inspect.py <case dir>
"""
import json
import os
import sys

import numpy as np

d = sys.argv[1]
for name in ("r8_series.npz", "s8_series.npz", "pads.npz"):
    z = np.load(os.path.join(d, name), allow_pickle=False)
    print("==", name)
    for k in z.files:
        a = z[k]
        print(f"  {k:32s} {a.dtype} {a.shape}")


def walk(o, prefix="", depth=0, maxdepth=3):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)) and depth < maxdepth:
                print(f"{'  ' * depth}{prefix}{k}: {type(v).__name__}({len(v)})")
                walk(v, "", depth + 1, maxdepth)
            else:
                s = repr(v)
                print(f"{'  ' * depth}{prefix}{k}: {s[:140]}")
    elif isinstance(o, list) and o and depth < maxdepth:
        print(f"{'  ' * depth}[0] of {len(o)}:")
        walk(o[0], "", depth + 1, maxdepth)


for name in sys.argv[2:]:
    print("==", name)
    with open(os.path.join(d, name), encoding="utf-8") as fh:
        walk(json.load(fh), maxdepth=int(os.environ.get("DEPTH", "2")))
