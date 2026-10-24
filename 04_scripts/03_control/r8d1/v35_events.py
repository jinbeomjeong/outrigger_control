"""E-group event analysis: other-leg minima, re-approach command activity, P-R8-14 component sum check."""
import argparse
import json
import os
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
S6_RESULTS_DIR = REPO_ROOT / "07_results" / "S6"
DEFAULT_BATCH = "bundleC_rerun34_L1R_20261024_141040"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--batch", default=DEFAULT_BATCH, help="batch folder under 07_results/S6")
ROOT = S6_RESULTS_DIR / parser.parse_args().batch
V = json.load(open(os.path.join(ROOT, "verify_S6C.json"), encoding="utf-8"))
LEGS = ["FL", "FR", "RL", "RR"]
OFF = 68.5
for m in V["metrics"]:
    case = m["case"]
    d = os.path.join(ROOT, case)
    r = np.load(os.path.join(d, "r8_series.npz"))
    comps = ["cmp_attitude_u", "cmp_heave_u", "cmp_twist_u", "cmp_guard_u", "cmp_reapproach_u"]
    tot = sum(np.nan_to_num(r[k]) for k in comps)
    cu = r["computed_u"]
    ok = np.isfinite(cu).all(axis=1) & np.isfinite(r["cmp_attitude_u"]).all(axis=1)
    err = np.abs(tot[ok] - cu[ok]).max() if ok.any() else np.nan
    nan_frac = float(np.mean(~np.isfinite(r["cmp_attitude_u"]).all(axis=1)))
    line = f"{case[:40]:40s} P-R8-14 max|sum-computed| {err:.2e} m/s (finite rows {ok.sum()}/{len(ok)}, nan frac {nan_frac:.2f})"
    tev = m.get("floor_event_t_s")
    if tev is None:
        print(line)
        continue
    p = np.load(os.path.join(d, "pads.npz"))
    t = p["t"] - OFF
    w = (t >= tev) & (t <= tev + 5.0)
    F = p["F_cyl"][w] / 1e3
    mins = {LEGS[i]: round(float(F[:, i].min()), 2) for i in range(4)}
    tr = r["t"] - OFF
    wr = (tr >= tev) & (tr <= tev + 5.0)
    rea = r["cmp_reapproach_u"][wr] * 1e3
    tw = r["cmp_twist_u"][wr] * 1e3
    act = np.nan_to_num(np.abs(rea)).max(axis=1) > 1e-9
    print(line)
    print(f"   event {tev:.2f}: other-leg min F_cyl [kN] (event..+5 s) {mins}")
    if act.any():
        idx = np.where(act)[0]
        print(f"   re-approach component active {act.sum()} samples, t {tr[wr][idx[0]] - tev:+.2f}..{tr[wr][idx[-1]] - tev:+.2f} s;"
              f" first active u_rea [mm/s] {np.round(rea[idx[0]], 2)}; twist cmp at that sample {np.round(tw[idx[0]], 2)}")
        zero = [k for k in idx if np.allclose(rea[k], 0)]
    else:
        print("   re-approach component never non-zero in window; twist cmp max", np.round(np.nan_to_num(np.abs(tw)).max(axis=0), 2))
