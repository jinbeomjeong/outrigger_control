"""Inspect structure of the b46bdf8f a2 repro jsonl (first line) and one T4h npz."""
import json
import sys
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2")


def walk(obj, prefix="", depth=0, maxdepth=4):
    if depth > maxdepth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            t = type(v).__name__
            extra = ""
            if isinstance(v, list):
                extra = f" len={len(v)}"
            elif not isinstance(v, dict):
                extra = f" = {str(v)[:80]}"
            print(f"{'  ' * depth}{prefix}{k}: {t}{extra}")
            if isinstance(v, dict):
                walk(v, "", depth + 1, maxdepth)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                walk(v[0], "[0].", depth + 1, maxdepth)


with open(RUN / "ed7_probe_a2.jsonl", encoding="utf-8") as fh:
    first = json.loads(fh.readline())
print("TOP KEYS:", list(first.keys()))
for k in ("job", "key", "plant", "arm", "tag", "setting"):
    if k in first:
        print(k, "=", str(first[k])[:200])


def find(obj, name, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k == name:
                yield p, v
            yield from find(v, name, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):
            yield from find(v, name, f"{path}[{i}]")


for name in ("lsb_record", "blind"):
    for p, v in find(first, name):
        print("FOUND", p)
        break

lsb = None
for p, v in find(first, "lsb_record"):
    lsb = v
    break
if lsb is not None:
    print("---- lsb_record structure")
    walk(lsb, maxdepth=3)

npzs = sorted((RUN / "ed7_probe_a2_t4h").glob("*.npz"))
z = np.load(npzs[0], allow_pickle=False)
print("---- npz", npzs[0].name)
for n in z.files:
    a = z[n]
    print(n, a.dtype, a.shape)
sys.stdout.flush()
