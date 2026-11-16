"""Issued commands, readings and lock flags of one leg in several T4h files (read only).

Usage: python -I -B cr05_commands.py <leg> <t0> <t1> <npz> [<npz> ...]
Command in mm/s (issued at t; it acts in the next period, d = 1), pressures in bar.
"""

import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def main() -> None:
    leg = LEGS.index(sys.argv[1])
    t0, t1 = float(sys.argv[2]), float(sys.argv[3])
    for path in map(Path, sys.argv[4:]):
        with np.load(path, allow_pickle=False) as d:
            t = d["t_s"]
            sel = np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9))
            print(path.name)
            for k in sel:
                print(f"  t={t[k]:6.2f} u_issued={d['command_m_s'][k, leg] * 1e3:8.4f} "
                      f"head={d['head_pressure_Pa'][k, leg] / 1e5:7.2f} "
                      f"rod={d['rod_pressure_Pa'][k, leg] / 1e5:7.2f} "
                      f"locked={bool(d['locked'][k, leg])} "
                      f"F={d['true_force_N'][k, leg] / 1e3:7.2f} kN phase={d['phase'][k]}")


if __name__ == "__main__":
    main()
