"""D-S8-7: list the arrays of one ML episode (record.npz, pads.npz, r8_series.npz, s8_series.npz).

Usage: python -I ds87_keys.py <episode_dir>
"""
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
d = Path(sys.argv[1])
for f in [d / "record" / "record.npz", d / "pads.npz", d / "r8_series.npz", d / "s8_series.npz"]:
    z = np.load(f, allow_pickle=True)
    print(f"== {f.name}")
    for k in z.files:
        a = z[k]
        extra = ""
        if k == "t" and a.ndim == 1 and len(a) > 2:
            extra = f" t0 {a[0]:.4f} t1 {a[-1]:.4f} dt {np.median(np.diff(a)):.2e}"
        print(f"  {k:40s} {str(a.dtype):10s} {a.shape}{extra}")
