"""Rev. 49: list arrays (name, shape, dtype) of one ML episode's r8_series / record / pads and meta keys.
Usage: python -I s8d1pp_keys.py <episode_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
d = Path(sys.argv[1])
for name in ("r8_series.npz", "record/record.npz", "pads.npz"):
    z = np.load(d / name, allow_pickle=True)
    print("==", name)
    for k in z.files:
        a = z[k]
        print(f"  {k:40s} {str(a.shape):18s} {a.dtype}")
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
print("== result.json keys", list(res.keys()))
print("settings", {k: v for k, v in res.get("settings", {}).items() if not isinstance(v, (dict, list))})
meta = json.loads((d / "record" / "meta.json").read_text(encoding="utf-8"))
print("== meta keys", list(meta.keys())[:80])
