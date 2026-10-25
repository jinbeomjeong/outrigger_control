"""Head-step consistency test candidate: at a one-period head step > 100 bar, how much does the
four-leg cylinder-force sum change in the same period (physical load redistribution keeps the
sum near the weight; a head-sensor jump fault moves the sum by >= 100 bar x A_p = 95 / 133 kN).

Prints, per batch, the largest one-period |change of sum F_cyl| over all runs (true record at
the 10 Hz samples, exact alignment), and the sum change at every head step > 100 bar.
Usage: python -I s8ml_sum_step.py <batch_dir> [...]
"""
import sys
from pathlib import Path

import numpy as np


def runs(batch: Path):
    for sub in (batch, batch / "bases", batch / "episodes"):
        if sub.is_dir():
            for d in sorted(sub.iterdir()):
                if d.is_dir() and (d / "pads.npz").exists() and (d / "r8_series.npz").exists():
                    yield d


for b in sys.argv[1:]:
    worst = (0.0, "")
    for d in runs(Path(b)):
        try:
            r8 = np.load(d / "r8_series.npz", allow_pickle=True)
            pads = np.load(d / "pads.npz", allow_pickle=True)
            t, tp = r8["t"], pads["t"]
            idx = np.clip(np.searchsorted(tp, t), 0, len(tp) - 1)
            F = pads["F_cyl"][idx] / 1e3
            ph = pads["head_pressure"][idx] / 1e5
        except Exception:
            continue
        ds = np.diff(F.sum(axis=1))
        k = int(np.argmax(np.abs(ds)))
        if abs(ds[k]) > abs(worst[0]):
            worst = (float(ds[k]), f"{d.name} @{t[k+1]:.2f}")
        dph = np.diff(ph, axis=0)
        for kk, leg in zip(*np.nonzero(np.abs(dph) > 100.0)):
            print(f"  {d.name} leg {leg} t {t[kk+1]:.2f} dp_h {dph[kk, leg]:+.1f} bar,"
                  f" dF_leg {F[kk+1, leg]-F[kk, leg]:+.1f} kN, d(sum F) {ds[kk]:+.1f} kN")
    print(f"{Path(b).name}: largest one-period |d sum F_cyl| {worst[0]:+.1f} kN ({worst[1]})")
