"""DONE gate check: twist reading n^T F_hat vs done_twist_N (3 kN), A vs 768, in LEVEL."""
import json
import os
import sys
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = str(REPO / r"07_results\S8")
A = ROOT + r"\c36_20261025_155317\A_rt\episodes"
REF = ROOT + r"\ml_main_20261025_090131\episodes"
n = np.array([1.0, -1.0, -1.0, 1.0]) / 2.0


def run(path, tag):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    s = np.load(os.path.join(path, "r8_series.npz"))
    t = s["t"] - te
    ph = s["phase"]
    tw = s["F_hat_N"] @ n / 1e3
    p = np.load(os.path.join(path, "pads.npz"))
    tp = p["t"] - te
    twt = p["F_cyl"] @ n / 1e3
    line = []
    for tt in (6, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26):
        i = int(np.argmin(np.abs(t - tt)))
        j = int(np.argmin(np.abs(tp - tt)))
        line.append(f"{tt}:{ph[i][:2]} {tw[i]:+.1f}/{twt[j]:+.1f}")
    print(f"  [{tag}] nT F_hat / nT F_true [kN]:", " | ".join(line))
    lv = (ph == "level") & (t > 3)
    if lv.any():
        frac = float(np.mean(np.abs(tw[lv]) < 3.0))
        print(f"  [{tag}] LEVEL (t>3 s) samples {int(lv.sum())}, fraction |twist reading| < 3 kN: {frac:.2f}")


for c in sys.argv[1:]:
    print("=====", c)
    run(os.path.join(A, c), "A")
    run(os.path.join(REF, c), "R")
