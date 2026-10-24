"""7c load-estimate check: probe estimate vs truth (0.5 s mean F_cyl before move) per round/leg."""
import argparse
import json
import os
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
S6_RESULTS_DIR = REPO_ROOT / "07_results" / "S6"
DEFAULT_BATCH = "bundleC_rerun34_L1R_20261024_141040"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("cases", nargs="+", help="case folder names inside the batch")
parser.add_argument("--batch", default=DEFAULT_BATCH, help="batch folder under 07_results/S6")
args = parser.parse_args()

ROOT = S6_RESULTS_DIR / args.batch
LEGS = ["FL", "FR", "RL", "RR"]
for case in args.cases:
    d = os.path.join(ROOT, case)
    ph = json.load(open(os.path.join(d, "probe_history.json"), encoding="utf-8"))
    p = np.load(os.path.join(d, "pads.npz"))
    t = p["t"]
    F = p["F_cyl"]
    print("=====", case)
    for k, rnd in enumerate(ph):
        for e in rnd:
            i = e["leg_index"]
            t0 = e["t_move_start_s"]
            m = (t >= t0 - 0.5) & (t < t0)
            truth = F[m, i].mean() / 1e3
            sd = F[m, i].std() / 1e3
            est = e["load_estimate_N"] / 1e3
            tol = max(5.0, 0.1 * truth)
            print(f"  round {k} {LEGS[i]} t_move {t0 - 68.5:6.2f} est {est:7.2f} truth {truth:7.2f} (sd {sd:5.2f})"
                  f" err {est - truth:+7.2f} tol {tol:5.2f} excess {abs(est - truth) - tol:+6.2f}"
                  f" drift {e['attitude_drift_ratio']:.2f} ripple {e['is_attitude_rippled']} cons {e['is_attitude_consistent']}"
                  f" seal {e['seal_friction_estimate_N'] / 1e3:+6.2f} k_inc {e['incremental_stiffness_N_m'] / 1e6:6.2f}")
