"""Gate variant (per-axis 1 s mean <= 0.02 deg/s) and Q1 abstention count per case."""
import glob
import json
import math
import os

import numpy as np
import pandas as pd

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
B = str(REPO / r"07_results\S6\stage2_20261021_232845")
LEGS = ["FL", "FR", "RL", "RR"]
ARW = {"ideal": 0.0, "good_zeroed": 0.15, "normal_zeroed": 0.30, "normal_zeroed_repeatability": 0.30}


def run_hold(mask, n):
    out = np.zeros_like(mask)
    c = 0
    for k, m in enumerate(mask):
        c = c + 1 if m else 0
        out[k] = c >= n
    return out


def wmean(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0, axis=0), axis=0)
    return np.concatenate([np.full((n - 1,) + x.shape[1:], np.nan), (c[n:] - c[:-n]) / n])


tot = abst = 0
for cdir in sorted(glob.glob(B + r"\*\\")):
    case = os.path.basename(os.path.normpath(cdir))
    rj = json.load(open(cdir + "result.json", encoding="utf-8"))
    grade = rj["settings"]["grade"]
    t0 = rj["runner"]["start_t_s"]
    ph = json.load(open(cdir + "probe_history.json", encoding="utf-8"))
    flat = [p for rnd in ph for p in (rnd if isinstance(rnd, list) else [rnd])]
    n_ab = sum(1 for p in flat if p.get("is_attitude_consistent") is None and not p.get("is_skipped"))
    n_all = sum(1 for p in flat if not p.get("is_skipped"))
    wrong = sum(1 for p in flat if p.get("is_attitude_consistent") is False)
    tot += n_all
    abst += n_ab
    drift = [round(p.get("attitude_drift_ratio") or 0, 2) for p in flat]
    line = f"{case:46s} {grade:28s} probes {n_all:2d} abstain {n_ab:2d} attitude-inconsistent {wrong}"
    if grade != "ideal" or "roll5.5" in case:
        df = pd.read_csv(cdir + "ge1_timeseries.csv")
        z = np.load(cdir + r"record\record.npz", allow_pickle=False)
        b = np.degrees(np.array(rj["controller_meta"]["target"]["gyro_bias_rad_s"][:2], float))
        w = np.degrees(z["meas.angular_rate"][:, :2]) - b
        sig = ARW[grade] / 60.0 * math.sqrt(1 / 0.04)
        rms = np.sqrt(np.clip(wmean(w ** 2, 25) - sig ** 2, 0, None)).max(1)
        m1 = np.abs(wmean(w, 50)).max(1)
        u = df[[f"u_{l}_m_s" for l in LEGS]].to_numpy(float)
        phase_ok = np.isin(df["phase"].to_numpy(str), ["done", "probe", "ready"])
        cmd0 = run_hold(np.all(u == 0, 1), 50)
        base = phase_ok & cmd0 & np.isfinite(df["d_FL_mm"].to_numpy(float))
        for thr in (0.01, 0.02):
            g = base & run_hold((rms <= 0.02) & (m1 <= thr), 25)
            d = df[[f"d_{l}_mm" for l in LEGS]].to_numpy(float)[g]
            line += f" | mean<={thr}: n={int(g.sum())}/{int(base.sum())} maxd={np.abs(d).max() if d.size else None}"
        line += f" drift={drift}"
    print(line)
print("total probes", tot, "abstain", abst, f"{abst / tot:.3f}")
