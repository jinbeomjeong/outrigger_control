"""Closure time of the spec-38 gate for RMS window 0.5 s vs 1.0 s in Chrono READY disturbances."""
import json

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
EV = 42.02


def wmean(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0, axis=0), axis=0)
    return np.concatenate([np.full((n - 1,) + x.shape[1:], np.nan), (c[n:] - c[:-n]) / n])


for case in ("RE1b_top_flat_settleRR30", "G4_top_flat_settleRR_combined"):
    c = B + "\\" + case + "\\"
    rj = json.load(open(c + "result.json", encoding="utf-8"))
    df = pd.read_csv(c + "ge1_timeseries.csv")
    z = np.load(c + r"record\record.npz", allow_pickle=False)
    t = df["t_s"].to_numpy()
    b = np.degrees(np.array(rj["controller_meta"]["target"]["gyro_bias_rad_s"][:2], float))
    w = np.degrees(z["meas.angular_rate"][:, :2]) - b
    d = df[["d_FL_mm", "d_FR_mm", "d_RL_mm"]].to_numpy(float)
    m1 = np.abs(wmean(w, 50)).max(1)
    for n in (25, 50):
        rms = np.sqrt(np.clip(wmean(w ** 2, n) - wmean(w, n) ** 2, 0, None)).max(1)  # about window mean
        bad = ((rms > 0.02) | (m1 > 0.02)) & (t >= EV)
        k = np.where(bad)[0][0]
        print(f"{case:32s} RMS window {n * 0.02:.1f} s: gate closes +{t[k] - EV:.2f} s, "
              f"others |d| at closure {np.round(np.abs(d[k]), 2)} mm")
