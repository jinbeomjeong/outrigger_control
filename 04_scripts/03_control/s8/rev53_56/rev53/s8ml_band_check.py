"""Seal band and probe context: training episodes by F_s against the two N gate runs (read only)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = REPO
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402

from outrigger_sim.contact_episode import load_episode  # noqa: E402

RUN = ROOT / r"07_results\S8\ml_main_20261025_090131"


def summary(ep, leg=3):
    lifted = np.asarray(ep["is_lifted"], bool)
    band = np.asarray(ep["seal_band_N"], float)[lifted, leg]
    has_probe = np.isfinite(np.asarray(ep["probe_is_grounded"], float)[lifted, leg])
    return (np.nanmin(band) if band.size else np.nan, np.nanmax(band) if band.size else np.nan,
            float(has_probe.mean()) if has_probe.size else np.nan)


rows = []
for path in sorted((RUN / "ml_dataset").glob("*.npz")):
    ep = load_episode(path)
    fs = ep.meta.get("seal_friction_N")
    fs_rr = float(np.atleast_1d(fs)[-1]) if fs is not None else np.nan
    bmin, bmax, probe = summary(ep)
    rows.append((fs_rr, bmin, bmax, probe))
arr = np.array(rows, float)
for lo, hi in ((0, 2e3), (2e3, 4e3), (4e3, 6e3), (6e3, 1e4)):
    sel = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
    if sel.any():
        print(f"train-all F_s,RR [{lo/1e3:.0f},{hi/1e3:.0f}) kN n={sel.sum():3d}: band RR min "
              f"median {np.nanmedian(arr[sel, 1])/1e3:.2f} kN, band<13 kN share "
              f"{np.mean(arr[sel, 1] < 12.99e3):.2f}, probe-available share median "
              f"{np.nanmedian(arr[sel, 3]):.2f}")
for run in ("N_G4_Fs8_pressure", "N_SS_Fs8_pressure", "E_G4_Fs8", "E_SS_Fs8"):
    ep = load_episode(RUN / "ml_dataset_en" / f"{run}.npz")
    bmin, bmax, probe = summary(ep)
    print(f"{run}: band RR {bmin/1e3:.2f}..{bmax/1e3:.2f} kN, probe-available share {probe:.2f}, "
          f"controller judge {ep.meta.get('controller', {}).get('ground_judge', ep.meta.get('controller', {}).get('judge'))}")
