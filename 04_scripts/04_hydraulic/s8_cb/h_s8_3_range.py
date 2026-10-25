"""H-S8-3: min / max of the 1 ms rod and head pressure truth of one leg in a time window.

Usage: python -I h_s8_3_range.py <case_dir> <leg> <t0> <t1>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def main() -> None:
    case, leg = Path(sys.argv[1]), LEGS.index(sys.argv[2])
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    with np.load(case / "pads.npz", allow_pickle=True) as z:
        t, pr, ph = z["t"], z["rod_pressure"][:, leg], z["head_pressure"][:, leg]
    m = (t >= t0) & (t <= t1)
    for name, x in (("rod", pr[m]), ("head", ph[m])):
        print(f"{name}: min {x.min() / 1e5:.1f} max {x.max() / 1e5:.1f} bar g")


if __name__ == "__main__":
    main()
