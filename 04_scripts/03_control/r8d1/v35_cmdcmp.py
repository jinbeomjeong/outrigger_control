"""Compare 10 Hz valve commands r32 vs r34 around crawler lift-off, aligned on lift-off time."""
import argparse
import os
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT = REPO_ROOT / "07_results" / "S6"
DEFAULT_BATCH_R32 = "bundleC_rerun32_L1R_20261024_114455"
DEFAULT_BATCH_R34 = "bundleC_rerun34_L1R_20261024_141040"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("case", help="case folder name inside both batches")
parser.add_argument("lo32", type=float, help="r32 lift-off time [s, rel]")
parser.add_argument("lo34", type=float, help="r34 lift-off time [s, rel]")
parser.add_argument("win", type=float, nargs="?", default=2.0, help="window after lift-off [s]")
parser.add_argument("--batch-r32", default=DEFAULT_BATCH_R32, help="first (r32) batch folder")
parser.add_argument("--batch-r34", default=DEFAULT_BATCH_R34, help="second (r34) batch folder")
args = parser.parse_args()

r32 = os.path.join(ROOT, args.batch_r32, args.case)
r34 = os.path.join(ROOT, args.batch_r34, args.case)
lo32, lo34 = args.lo32, args.lo34
win = args.win

a = np.load(os.path.join(r32, "r8_series.npz"))
b = np.load(os.path.join(r34, "r8_series.npz"))
ta = a["t"] - 68.5 - lo32
tb = b["t"] - 68.5 - lo34
ma = (ta >= -1.0) & (ta <= win)
mb = (tb >= -1.0) & (tb <= win)
ua = a["valve_u"][ma]
ub = b["valve_u"][mb]
n = min(len(ua), len(ub))
d = (ub[:n] - ua[:n]) * 1e3
print("aligned samples", n, "max |du| per leg [mm/s]", np.abs(d).max(axis=0).round(3))
print("mean du per leg [mm/s]", d.mean(axis=0).round(3))
# cumulative stroke difference over window (sum u*T)
print("cum stroke diff per leg [mm]", (d.sum(axis=0) * 0.1).round(3))
pa = np.load(os.path.join(r32, "pads.npz"))
pb = np.load(os.path.join(r34, "pads.npz"))
for tag, p, lo in (("r32", pa, lo32), ("r34", pb, lo34)):
    t = p["t"] - 68.5 - lo
    m = (t >= -0.5) & (t <= win)
    F = p["F_cyl"][m] / 1e3
    s = p["s_motor"][m] * 1e3
    i = np.argmin(F[:, 2])
    print(tag, f"RL min {F[i, 2]:.2f} kN at lift-off +{t[m][i]:.3f} s; motor stroke at min [mm]", s[i].round(2),
          "| all-leg F at min", F[i].round(1))
