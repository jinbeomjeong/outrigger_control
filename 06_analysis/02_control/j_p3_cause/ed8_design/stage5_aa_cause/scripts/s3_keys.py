"""Step 3: the structure of one stage 5 result line (keys, sizes) to find the fields to read."""
import json
import sys
from pathlib import Path

path = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248\ho_v0_a1\ed8_heldout_v0.jsonl")
with path.open(encoding="utf-8") as fh:
    row = json.loads(fh.readline())


def walk(obj, prefix="", depth=0):
    if isinstance(obj, dict):
        for k, v in obj.items():
            size = len(json.dumps(v, default=str))
            kind = type(v).__name__
            short = json.dumps(v, default=str)[:120] if size < 160 else f"<{size} chars>"
            print("  " * depth + f"{prefix}{k} [{kind}] {short}")
            if isinstance(v, dict) and depth < 2 and size >= 160:
                walk(v, "", depth + 1)


walk(row)
