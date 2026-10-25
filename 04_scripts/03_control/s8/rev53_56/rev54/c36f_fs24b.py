"""Cross-check the judge value 6.97 kN (FS24_Fs0 RR, window end .. re-READY) with pads 1 ms arrays."""
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
P = str(REPO / r"07_results\S8\c36_20261025_155317\D_fs24\MLJ_FS24_Fs0\pads.npz")
O = str(REPO / r"07_results\S8\mlj_20261025_080212\MLJ_FS24_Fs0\pads.npz")
te = 47.70000000039165 + 3.0
for tag, path in (("D", P), ("orig", O)):
    p = np.load(path)
    t = p["t"] - te
    w = (t >= 2.713) & (t <= 27.4)
    for key in ("F_cyl", "F_cyl_min_interval", "F_cyl_mean_20ms"):
        a = p[key][w, 3] / 1e3
        i = int(np.argmin(a))
        print(tag, key, "RR min %.2f kN at +%.3f s" % (a[i], t[w][i]))
