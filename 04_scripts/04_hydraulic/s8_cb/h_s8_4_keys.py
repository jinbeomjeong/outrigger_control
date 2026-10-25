"""H-S8-4: list keys/shapes of the ML88_ep0 episode files (pads.npz, r8_series, s8_series)."""

import sys
from pathlib import Path

import numpy as np

ep = Path(sys.argv[1])
for name in ("pads.npz", "r8_series.npz", "s8_series.npz", "record/record.npz"):
    p = ep / name
    if not p.exists():
        continue
    z = np.load(p, allow_pickle=True)
    print("==", name)
    for k in z.files:
        a = z[k]
        print(f"  {k:40s} {a.dtype} {a.shape}")
