"""Rev. 46 numbers vs pad-record alignment: searchsorted - 1 (s8cb_d2.py, s8rest_re1c_f2.py) vs
the exact searchsorted (judge, python-expert 2026-10-25).

For one case / leg / window prints, for both alignments: rod pressure range, true F_cyl range,
F_lower_est - F_cyl range, and |F_hat - F_cyl| median / max (record consistency).
Usage: python -I s8_align_check.py <case_dir> <leg> <t0> <t1>
"""
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
leg = int(sys.argv[2])
t0, t1 = float(sys.argv[3]), float(sys.argv[4])
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
t, tp = r8["t"], pads["t"]
k = np.flatnonzero((t >= t0) & (t <= t1))
for name, idx in (("ss-1", np.clip(np.searchsorted(tp, t) - 1, 0, len(tp) - 1)),
                  ("ss", np.clip(np.searchsorted(tp, t), 0, len(tp) - 1))):
    j = idx[k]
    pr = pads["rod_pressure"][j, leg] / 1e5
    F = pads["F_cyl"][j, leg] / 1e3
    lo = r8["F_lower_est_N"][k, leg] / 1e3
    hat = r8["F_hat_N"][k, leg] / 1e3
    whole = np.abs(r8["F_hat_N"][:, leg] / 1e3 - pads["F_cyl"][idx, leg] / 1e3)
    print(f"{case.name} leg {leg} [{t0},{t1}] {name:5s}: p_r {pr.min():6.1f}..{pr.max():6.1f} bar,"
          f" F {F.min():7.2f}..{F.max():7.2f} kN, F_lowEst-F {np.min(lo-F):+7.2f}..{np.max(lo-F):+7.2f},"
          f" |F_hat-F| window med {np.median(np.abs(hat-F)):.2f} max {np.max(np.abs(hat-F)):.2f};"
          f" whole run med {np.median(whole):.2f} max {whole.max():.2f} kN")
