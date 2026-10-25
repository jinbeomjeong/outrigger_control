"""RE1b: contact / normal force during the settlement window, and sign behaviour of r."""
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
for case in ("RE1b_top_flat_settleRR30", "G4_top_flat_settleRR_combined"):
    c = B + "\\" + case + "\\"
    rj = json.load(open(c + "result.json", encoding="utf-8"))
    t0 = rj["runner"]["start_t_s"]
    p = np.load(c + "pads.npz", allow_pickle=False)
    tp = p["t"] - t0
    N = p["N"] / 1e3
    z = p["ball_centre_world"][:, :, 2] * 1e3
    print("==", case, "phases", [(round(a, 2), b) for a, b in rj["phases"]], "event", rj["settings"].get("event"))
    ev = 42.02
    for a, b in ((ev - 1, ev), (ev, ev + 1.0), (ev + 1.0, ev + 1.78), (ev + 1.78, ev + 3), (ev + 3, ev + 6),
                 (ev + 6, ev + 12), (ev + 12, ev + 21.6)):
        s = (tp >= a) & (tp < b)
        if not s.any():
            continue
        print(f"  [{a - ev:5.2f},{b - ev:5.2f}) s  Nmin kN {np.round(N[s].min(0), 2)}  "
              f"z-z0 mm min {np.round((z[s] - z[np.argmin(abs(tp - (ev - 0.5)))]).min(0), 2)} "
              f"max {np.round((z[s] - z[np.argmin(abs(tp - (ev - 0.5)))]).max(0), 2)}")
    df = pd.read_csv(c + "ge1_timeseries.csv")
    t = df["t_s"].to_numpy()
    r = df["r_mm"].to_numpy(float)
    post = t > 63.6
    if case.startswith("RE1b"):
        rp = r[post]
        rp = rp[np.isfinite(rp)]
        print("  post-ref r: n", rp.size, "positive", int((rp > 0).sum()), "negative", int((rp < 0).sum()),
              "min", rp.min(), "max", rp.max())
        dcols = df[["d_FL_mm", "d_FR_mm", "d_RL_mm", "d_RR_mm"]].to_numpy(float)[post]
        print("  post-ref d sign flips per leg:",
              [int(np.sum(np.diff(np.sign(dcols[np.isfinite(dcols[:, k]), k])) != 0)) for k in range(4)])
