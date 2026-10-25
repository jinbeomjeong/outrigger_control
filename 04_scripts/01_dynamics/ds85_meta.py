"""D-S8-5 helper: print sensor and zero-calibration meta of one S8 case (result.json).

Usage: python -I ds85_meta.py <case dir>
"""
import json
import os
import sys

d = sys.argv[1]
with open(os.path.join(d, "result.json"), encoding="utf-8") as fh:
    r = json.load(fh)


def find(o, key, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}.{k}"
            if k == key:
                yield p, v
            yield from find(v, key, p)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from find(v, key, f"{path}[{i}]")


for key in sys.argv[2:]:
    for p, v in find(r, key):
        print("==", p)
        print(json.dumps(v, indent=1)[:6000])
