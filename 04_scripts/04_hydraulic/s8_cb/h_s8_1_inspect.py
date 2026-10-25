"""H-S8-1: list the arrays of one S8 Chrono case (read only).

Usage: python -I h_s8_1_inspect.py <case_dir>
"""
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
for name in ("r8_series.npz", "s8_series.npz", "pads.npz"):
    p = case / name
    if not p.exists():
        continue
    with np.load(p, allow_pickle=True) as z:
        print(f"== {name}")
        for k in z.files:
            a = z[k]
            print(f"  {k:32s} {a.dtype!s:10s} {a.shape}")
