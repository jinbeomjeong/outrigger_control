"""True rod-side pressure (pads rod_pressure, 1 ms) at the pending sample k (INFO time - 0.1 s) and the
confirmation sample k+1 (INFO time) for each check_draining INFO in E; bound p_hi + rho (p_k - p_hi),
p_hi = 12 bar g, rho = 0.5. Also the true value 0.1 s before k (locked, pre-release).
Pressures in bar g assuming pads rod_pressure is Pa abs or gauge (printed raw first sample to tell).
"""
import json
import os
import re
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = str(REPO / r"07_results\S8\c37_20261025_180821\E_drain\episodes")
LEGS = ["FL", "FR", "RL", "RR"]
PAT = re.compile(r"t_s=([-0-9.e]+), name='INFO_PRESSURE_STEP:(\w\w):rod:check_draining'")
P_HI, RHO = 12.0, 0.5
rows = []
for c in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, c)
    d = np.load(os.path.join(p, "pads.npz"))
    t = d["t"]
    rp = d["rod_pressure"]
    for e in json.load(open(os.path.join(p, "controller_events.json"), encoding="utf-8")):
        m = PAT.search(e)
        if not m:
            continue
        tc, leg = float(m.group(1)), m.group(2)
        k = LEGS.index(leg)

        def at(x):
            return float(rp[int(np.argmin(abs(t - x))), k]) / 1e5

        pre, pk, pk1 = at(tc - 0.2), at(tc - 0.1), at(tc)
        rows.append((c, leg, round(pre, 1), round(pk, 1), round(pk1, 1)))
off = 0.0
print("raw rod_pressure sample (bar):", rows[0])
for c, leg, pre, pk, pk1 in rows:
    b = P_HI + RHO * (pk - P_HI)
    print(c, leg, "pre", pre, "p_k", pk, "p_k+1", pk1, "bound", round(b, 1), "margin", round(b - pk1, 1),
          "ratio excess", round((pk1 - 5.0) / (pk - 5.0), 3) if pk > 5 else None)
pk = np.array([r[3] for r in rows]); pk1 = np.array([r[4] for r in rows])
print("p_k", pk.min(), pk.max(), "p_k+1", pk1.min(), pk1.max(), "min margin", round(float((P_HI + RHO * (pk - P_HI) - pk1).min()), 2))
