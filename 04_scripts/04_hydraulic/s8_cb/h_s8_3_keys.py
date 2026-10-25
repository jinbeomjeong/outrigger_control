"""H-S8-3: list the record keys of one CB case (pads.npz, r8_series.npz, record.npz, meta).

Usage: python -I h_s8_3_keys.py <case_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    case = Path(sys.argv[1])
    for name in ("pads.npz", "r8_series.npz", "s8_series.npz", "record/record.npz"):
        path = case / name
        if not path.exists():
            continue
        with np.load(path, allow_pickle=True) as z:
            print(name, {k: z[k].shape for k in z.files})
    meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    act = meta.get("run", {}).get("engine", {}).get("actuator", {})
    print("valve", json.dumps(act.get("valve"), indent=None))
    s8 = act.get("s8", {})
    print("s8 keys", list(s8.keys()) if isinstance(s8, dict) else s8)
    if isinstance(s8, dict) and "counterbalance" in s8:
        print("cb", json.dumps(s8["counterbalance"], indent=None)[:1500])
    rs = act.get("rod_side")
    print("rod_side", json.dumps(rs, indent=None)[:1500])


if __name__ == "__main__":
    main()
