"""D1 step candidate rule check: a one-period sensor step > 100 bar is a fault only when the
four-leg two-sensor net-force sum changes in the same period by at least half of the step's own
force (|dp| x area of that sensor). Physical steps redistribute load (sum nearly unchanged);
a sensor jump moves the sum by the full step force.

Prints every step > 100 bar (head and rod) with ratio = |d sum net| / (|dp| A); and for the
whole batch the largest ratio-free sum change (context). Pressures are the true record at the
10 Hz samples (exact alignment); areas REXOME35 (spec 64.1).
Usage: python -I s8ml_step_explained.py <batch_dir> [...]
"""
import sys
from pathlib import Path

import numpy as np

A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
LIMIT = 100.0


def runs(batch: Path):
    for sub in (batch, batch / "bases", batch / "episodes"):
        if sub.is_dir():
            for d in sorted(sub.iterdir()):
                if d.is_dir() and (d / "pads.npz").exists() and (d / "r8_series.npz").exists():
                    yield d


for b in sys.argv[1:]:
    n = 0
    for d in runs(Path(b)):
        try:
            r8 = np.load(d / "r8_series.npz", allow_pickle=True)
            pads = np.load(d / "pads.npz", allow_pickle=True)
            t, tp = r8["t"], pads["t"]
            idx = np.clip(np.searchsorted(tp, t), 0, len(tp) - 1)
            ph = pads["head_pressure"][idx] / 1e5
            pr = pads["rod_pressure"][idx] / 1e5
        except Exception:
            continue
        net = (ph * A_P - pr * A_ANN) * 1e2  # kN (bar * m^2 * 1e5 / 1e3)
        dsum = np.diff(net.sum(axis=1))
        for name, p, area in (("head", ph, A_P), ("rod", pr, A_ANN)):
            dp = np.diff(p, axis=0)
            for k, leg in zip(*np.nonzero(np.abs(dp) > LIMIT)):
                own = abs(dp[k, leg]) * area[leg] * 1e2
                n += 1
                print(f"  {d.name:12s} {name:4s} leg {leg} t {t[k+1]:.2f} dp {dp[k, leg]:+7.1f} bar"
                      f" own {own:6.1f} kN  d(sum net) {dsum[k]:+7.1f} kN  ratio {abs(dsum[k])/own:.3f}")
    print(f"{Path(b).name}: steps > {LIMIT:g} bar: {n}")
