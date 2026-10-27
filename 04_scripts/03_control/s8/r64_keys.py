"""Rev. 64 helper: list the arrays of the npz files of one case folder (or of given npz files).

Usage: python -I r64_keys.py <case_dir | file.npz> [...]
Read only.
"""
import sys
from pathlib import Path

import numpy as np

NAMES = ("r8_series.npz", "pads.npz", "record/record.npz", "s8_series.npz",
         "controller_commands.npz", "step_series.npz")
for arg in sys.argv[1:]:
    p = Path(arg)
    files = [p] if p.suffix == ".npz" else [p / n for n in NAMES if (p / n).exists()]
    for f in files:
        z = np.load(f, allow_pickle=True)
        print(f"== {f}")
        for k in z.files:
            a = z[k]
            print(f"   {k:40s} {a.dtype} {a.shape}")
