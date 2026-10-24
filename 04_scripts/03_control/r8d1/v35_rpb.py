"""Compare rpB beta 1.6 D8 transients: rerun32 (leaky) vs rerun34 (fixed).

Prints cylinder/pad force minima per leg, timing, and 10 Hz command series
around the crawler lift-off transient.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT = REPO_ROOT / "07_results" / "S6"
DEFAULT_BATCH_R32 = "bundleC_rerun32_L1R_20261024_114455"
DEFAULT_BATCH_R34 = "bundleC_rerun34_L1R_20261024_141040"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("case", help="case folder name inside both batches")
parser.add_argument("t_lo", type=float, nargs="?", default=24.0, help="window start [s, rel]")
parser.add_argument("t_hi", type=float, nargs="?", default=30.0, help="window end [s, rel]")
parser.add_argument("--batch-r32", default=DEFAULT_BATCH_R32, help="first (r32) batch folder")
parser.add_argument("--batch-r34", default=DEFAULT_BATCH_R34, help="second (r34) batch folder")
args = parser.parse_args()

RUNS = {
    "r32": args.batch_r32,
    "r34": args.batch_r34,
}
LEGS = ["FL", "FR", "RL", "RR"]
case = args.case
t_lo = args.t_lo
t_hi = args.t_hi

for tag, run in RUNS.items():
    d = os.path.join(ROOT, run, case)
    if not os.path.isdir(d):
        print(tag, "missing")
        continue
    p = np.load(os.path.join(d, "pads.npz"))
    r = dict(np.load(os.path.join(d, "r8_series.npz")))
    for _k in ("cmp_guard_u", "cmp_twist_u", "cmp_attitude_u", "cmp_heave_u"):
        r.setdefault(_k, np.full_like(r["valve_u"], np.nan))
    res = json.load(open(os.path.join(d, "result.json"), encoding="utf-8"))
    t = p["t"]
    t = t - 68.5
    m = (t >= t_lo) & (t <= t_hi)
    print(f"===== {tag} {case}")
    for key in ("controller_params_beta_GPa", "crawler_kt_scale_beta"):
        print(f"  {key}: {res.get(key, res.get('bundle_c', {}).get(key) if isinstance(res.get('bundle_c'), dict) else None)}")
    Fc = p["F_cyl"][m] / 1e3
    Fi = p["F_cyl_min_interval"][m] / 1e3
    N = p["N"][m] / 1e3
    tt = t[m]
    for i, leg in enumerate(LEGS):
        j = np.argmin(Fc[:, i]); k = np.argmin(N[:, i]); q = np.argmin(Fi[:, i])
        print(f"  {leg}: Fcyl min {Fc[j, i]:7.2f} @ {tt[j]:.3f}  Fcyl_int min {Fi[q, i]:7.2f} @ {tt[q]:.3f}"
              f"  pad N min {N[k, i]:7.2f} @ {tt[k]:.3f}  Fcyl@padmin {Fc[k, i]:7.2f}")
    # 10 Hz series
    tr = r["t"] - 68.5
    off = None
    # find controller time offset: r8 t vs pads t
    print("  r8 t range", tr[0], tr[-1], " pads t range", t[0], t[-1])
    mr = (tr >= t_lo) & (tr <= t_hi)
    if not mr.any():
        # try offset 68.5
        mr = (tr - 68.5 >= t_lo) & (tr - 68.5 <= t_hi)
        off = 68.5
    print("  t     phase   guard  valve_u[mm/s] FL FR RL RR | guard_u | twist | att | heave | Fcyl(1ms at t) RL")
    for idx in np.where(mr)[0]:
        tc = tr[idx] - (off or 0.0)
        jj = np.argmin(np.abs(t - tc))
        print(f"  {tc:6.2f} {str(r['phase'][idx]):7s} {int(r['guard_active'][idx])} "
              + " ".join(f"{1e3*v:6.2f}" for v in r["valve_u"][idx]) + " | "
              + " ".join(f"{1e3*v:6.2f}" for v in r["cmp_guard_u"][idx]) + " | "
              + " ".join(f"{1e3*v:6.2f}" for v in r["cmp_twist_u"][idx]) + " | "
              + " ".join(f"{1e3*v:5.2f}" for v in r["cmp_attitude_u"][idx]) + " | "
              + " ".join(f"{1e3*v:5.2f}" for v in r["cmp_heave_u"][idx]) + " | "
              + " ".join(f"{v/1e3:6.1f}" for v in p["F_cyl"][jj]))
