"""Dump the P1 V16 J2 / J1 single-pad results (read-only): structure, then sinkage-related scalars."""
import json
import sys
from pathlib import Path

root = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_P1_V16_20261026_032113")
names = sys.argv[1:] or ["V16bp_J2_B_RL_1cm", "V16bp_J2_B_RL_2cm"]


def walk(o, pre="", depth=0, out=None):
    if depth > 4:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{pre}.{k}" if pre else k
            if isinstance(v, (dict, list)) and not (isinstance(v, list) and len(v) <= 6 and all(isinstance(x, (int, float, str, type(None))) for x in v)):
                if isinstance(v, list):
                    print(f"{p}: list[{len(v)}]")
                    if v and isinstance(v[0], dict) and depth < 3:
                        walk(v[0], p + "[0]", depth + 1)
                else:
                    walk(v, p, depth + 1)
            else:
                s = json.dumps(v)
                print(f"{p} = {s[:160]}")


for n in names:
    print("=" * 30, n)
    r = json.loads((root / n / "result.json").read_text(encoding="utf-8"))
    walk(r)
