"""Does the proposed stationary gate (38 (a)+(b)) close during READY settlement (body tilting)?"""
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
LEGS = ["FL", "FR", "RL", "RR"]
EV = 42.02


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


for case in ("RE1b_top_flat_settleRR30", "G4_top_flat_settleRR_combined", "G4_top_flat_settleRR_pressure"):
    c = B + "\\" + case + "\\"
    rj = json.load(open(c + "result.json", encoding="utf-8"))
    df = pd.read_csv(c + "ge1_timeseries.csv")
    left = next((p[0] for p in rj["phases"] if p[0] > EV and p[1] != "ready"), EV + 12.0)
    z = np.load(c + r"record\record.npz", allow_pickle=False)
    t = df["t_s"].to_numpy()
    b = np.degrees(np.array(rj["controller_meta"]["target"]["gyro_bias_rad_s"][:2], float))
    w = np.degrees(z["meas.angular_rate"][:, :2]) - b  # ideal grade: sigma 0
    rms = np.sqrt(wmean(w ** 2, 25)).max(1)
    m1 = np.abs(wmean(w, 50)).max(1)
    u = df[[f"u_{l}_m_s" for l in LEGS]].to_numpy(float)
    phase_ok = np.isin(df["phase"].to_numpy(str), ["done", "probe", "ready"])
    cmd0 = run_hold(np.all(u == 0, 1), 50)
    cond_a = rms <= 0.02
    cond_b = m1 <= 0.02
    gate = phase_ok & cmd0 & run_hold(cond_a & cond_b, 25)
    d = df[[f"d_{l}_mm" for l in LEGS]].to_numpy(float)
    win = (t >= EV) & (t < left)
    print(f"== {case}: READY window {EV:.2f}-{left:.2f} s ({left - EV:.2f} s), n={int(win.sum())}")
    print(f"   max 1 s mean rate {np.nanmax(m1[win]):.4f} deg/s, max 0.5 s RMS {np.nanmax(rms[win]):.4f} deg/s")
    k_b = np.where(win & ~cond_b)[0]
    k_g = np.where(win & ~gate)[0]
    print(f"   (b) first violated at +{(t[k_b[0]] - EV) if len(k_b) else None} s; "
          f"gate first closed at +{(t[k_g[0]] - EV) if len(k_g) else None} s")
    open_w = win & gate
    if open_w.any():
        print(f"   gate-open samples {int(open_w.sum())}, others max |d| (FL,FR,RL) "
              f"{np.round(np.nanmax(np.abs(d[open_w][:, :3]), 0), 2)} mm, RR min {np.nanmin(d[open_w][:, 3]):.2f} mm")
    closed_w = win & ~gate
    if closed_w.any():
        print(f"   gate-closed samples {int(closed_w.sum())}, others max |d| "
              f"{np.round(np.nanmax(np.abs(d[closed_w][:, :3]), 0), 2)} mm")
    # sampled timeline every 0.2 s
    for tt in np.arange(EV, left, 0.2):
        k = int(np.argmin(np.abs(t - tt)))
        print(f"     +{t[k] - EV:4.2f}s m1={m1[k]:.4f} rms={rms[k]:.4f} gate={bool(gate[k])} "
              f"d={np.round(d[k], 2)}")
