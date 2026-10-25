"""Uncalibrated pressure sensors: one-sided (reads high = unsafe) exceedance of the margins.

Reuses the error model of s6r14_sensor_error.py (same folder, same seed). Reports, per grade,
P(dF > x) per leg and per machine (worst of the four legs) at guard-level load and at a
REANCHOR stop level, and the one-sided bound b at 99.9 % per leg.
"""

import json
import sys
from pathlib import Path

import numpy as np

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s6r14_sensor_error as m  # noqa: E402  (runs its own Monte Carlo once, fine)

N = 200_000
rng = np.random.default_rng(20261023)
m.rng = rng
F_MIN = m.F_MIN
levels = {"guard": F_MIN + 5e3, "reanchor_floor_L1": F_MIN + 2.4e3 + 11.5e3,
          "reanchor_floor_L2b": F_MIN + 4.7e3 + 11.5e3}
out = {}
for case in ("normal", "conservative"):
    rows = {}
    for lname, F in levels.items():
        per_leg = []
        for leg in ("front", "front", "rear", "rear"):
            g = m.LEGS[leg]
            sh, sr = m.draw(case, N), m.draw(case, N)
            p_h = (F + 2e5 * g["Aann"]) / g["Ap"] / 1e5
            dF = m.err(sh, p_h) * 1e5 * g["Ap"] - m.err(sr, 2.0) * 1e5 * g["Aann"]
            per_leg.append(dF / 1e3)
        D = np.array(per_leg)  # (4, N) kN, + = reads high
        r = {}
        for x in (2.5, 5.0, 7.5):
            r[f"P_leg_front_gt_{x}"] = float((D[0] > x).mean())
            r[f"P_machine_any_gt_{x}"] = float((D.max(axis=0) > x).mean())
        r["b999_front_kN"] = float(np.percentile(D[0], 99.9))
        r["b999_rear_kN"] = float(np.percentile(D[2], 99.9))
        r["max_front_kN"] = float(D[0].max())
        r["max_rear_kN"] = float(D[2].max())
        rows[lname] = r
    out[case] = rows
(OUT_DIR / "s6r14b_uncal.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
