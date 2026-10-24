"""P-R8-14: where does the component sum differ from computed_u? Break down by phase."""
import argparse
import os
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
S6_RESULTS_DIR = REPO_ROOT / "07_results" / "S6"
DEFAULT_BATCH = "bundleC_rerun34_L1R_20261024_141040"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("case", help="case folder name inside the batch")
parser.add_argument("--batch", default=DEFAULT_BATCH, help="batch folder under 07_results/S6")
args = parser.parse_args()

ROOT = S6_RESULTS_DIR / args.batch
case = args.case
r = np.load(os.path.join(ROOT, case, "r8_series.npz"))
comps = ["cmp_attitude_u", "cmp_heave_u", "cmp_twist_u", "cmp_guard_u", "cmp_reapproach_u"]
fin = np.isfinite(r["cmp_attitude_u"]).all(axis=1)
tot = sum(np.nan_to_num(r[k]) for k in comps)
cu = r["computed_u"]
iu = r["issued_u"]
sc = r["scale_used"]
ph = r["phase"]
err = np.abs(tot - cu).max(axis=1)
err_s = np.abs(tot * sc[:, None] - cu).max(axis=1)
for p in np.unique(ph):
    m = ph == p
    mf = m & fin
    print(f"{p:10s} n={m.sum():4d} finite={mf.sum():4d} max|sum-cu|={np.nanmax(err[mf]) if mf.any() else np.nan:.2e}"
          f" max|sum*scale-cu|={np.nanmax(err_s[mf]) if mf.any() else np.nan:.2e}"
          f" scale range {np.nanmin(sc[m]):.3f}..{np.nanmax(sc[m]):.3f}"
          f" max|cu| {np.nanmax(np.abs(cu[m])) * 1e3:.2f} mm/s")
k = np.nanargmax(np.where(fin, err, -1))
print("worst t", r["t"][k] - 68.5, "phase", ph[k], "sum", np.round(tot[k] * 1e3, 3), "cu", np.round(cu[k] * 1e3, 3),
      "issued", np.round(iu[k] * 1e3, 3), "scale", sc[k], "raw", r["scale_raw"][k])
for c in comps:
    print("  ", c, np.round(r[c][k] * 1e3, 3))
