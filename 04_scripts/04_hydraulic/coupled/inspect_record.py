"""Print the keys and shapes of a Chrono run record (read only)."""
from __future__ import annotations

import sys

import numpy as np

for path in sys.argv[1:]:
    print("==", path)
    with np.load(path, allow_pickle=True) as d:
        for k in d.files:
            a = d[k]
            desc = f"{a.shape} {a.dtype}"
            if a.dtype.kind == "f" and a.size:
                desc += f" min {np.nanmin(a):.5g} max {np.nanmax(a):.5g}"
            print(f"{k:32s} {desc}")
