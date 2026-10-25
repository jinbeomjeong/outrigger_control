"""H-S8-3: 10 Hz command / head / rod readings and plant spool speed of one leg in a window.

Usage: python -I h_s8_3_head10.py <case_dir> <leg> <t0> <t1>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def main() -> None:
    case, leg = Path(sys.argv[1]), LEGS.index(sys.argv[2])
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    with np.load(case / "r8_series.npz", allow_pickle=True) as z:
        t, issued, valve = z["t"], z["issued_u"][:, leg], z["valve_u"][:, leg]
    with np.load(case / "record" / "record.npz", allow_pickle=True) as z:
        rt, hm, rm = z["t"], z["meas.head_pressure"][:, leg], z["meas.rod_pressure"][:, leg]
        st = z["meas.stroke"][:, leg]
    ir = np.clip(np.searchsorted(rt, t - 1e-9), 0, rt.size - 1)
    cmd = np.r_[0.0, issued[:-1]]
    for k in np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9)):
        print(f"{t[k]:7.2f} cmd {1e3 * cmd[k]:7.3f} valve {1e3 * valve[k]:8.4f} mm/s "
              f"head {hm[ir[k]] / 1e5:7.2f} rod {rm[ir[k]] / 1e5:7.2f} bar g stroke {st[ir[k]]:.4f}")


if __name__ == "__main__":
    main()
