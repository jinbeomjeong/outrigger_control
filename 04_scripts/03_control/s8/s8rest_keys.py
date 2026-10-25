"""Print array keys / shapes of the npz files of one S8 case folder (read only)."""
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
for name in ("r8_series.npz", "s8_series.npz", "pads.npz"):
    p = case / name
    if not p.exists():
        continue
    with np.load(p, allow_pickle=True) as z:
        print("==", name)
        for k in z.files:
            a = z[k]
            print(f"  {k}: {a.shape} {a.dtype}")
