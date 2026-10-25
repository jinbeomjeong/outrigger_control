"""Inspect the structure of target_envelope.json."""
import json
import sys

d = json.load(open(sys.argv[1]))


def show(o, depth=0):
    if depth > 4:
        return
    if isinstance(o, dict):
        for k, v in list(o.items())[:30]:
            t = type(v).__name__
            ln = len(v) if hasattr(v, "__len__") and not isinstance(v, str) else ""
            val = v if isinstance(v, (int, float, str)) else ""
            print("  " * depth + str(k), t, ln, str(val)[:80])
            show(v, depth + 1)
    elif isinstance(o, list) and o:
        if isinstance(o[0], (dict, list)):
            show(o[0], depth + 1)


show(d)
