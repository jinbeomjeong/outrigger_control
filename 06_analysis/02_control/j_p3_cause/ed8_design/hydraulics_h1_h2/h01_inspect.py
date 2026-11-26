"""h01: list T4h npz keys and the jsonl record layout of the edition 7 sensitivity run (read only).

Usage: python -I -B h01_inspect.py  -> prints to stdout (h01_out.txt by redirect is not used).
"""
import json
import os

import numpy as np

J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
NPZ = os.path.join(J9, r"sens_a1\sens_t4h\R12_top-FL-Fs8-o0.0_VBMh15.npz")
JSONL = os.path.join(J9, r"sens_a1\sens.jsonl")
OUT = os.path.dirname(os.path.abspath(__file__))

lines = []
z = np.load(NPZ, allow_pickle=False)
for k in sorted(z.files):
    a = z[k]
    lines.append(f"{k} {a.dtype} {a.shape}")
with open(JSONL, encoding="utf-8") as f:
    d = json.loads(f.readline())


def walk(obj, prefix, depth):
    if depth > 3:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            tag = type(v).__name__
            size = len(v) if isinstance(v, (list, dict, str)) else ""
            lines.append(f"{prefix}{k}: {tag} {size}")
            if isinstance(v, dict):
                walk(v, prefix + "  ", depth + 1)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                walk(v[0], prefix + "  [0].", depth + 1)


walk(d, "", 0)
with open(os.path.join(OUT, "h01_out.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print(len(lines))
