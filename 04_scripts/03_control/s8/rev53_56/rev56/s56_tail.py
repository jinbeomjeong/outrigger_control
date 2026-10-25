"""Where the [3 s, re-READY] minimum sits and per-leg minima over [3, 4] s and [4, end] for given ids
(E / A / 768). Also airborne intervals of a given leg over [0, 4] s.
usage: s56_tail.py ID LEG
"""
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
B = {"E": ROOT + r"\c37_20261025_180821\E_drain\episodes",
     "A": ROOT + r"\c36_20261025_155317\A_rt\episodes",
     "R": ROOT + r"\ml_main_20261025_090131\episodes"}
LEGS = ["FL", "FR", "RL", "RR"]
c, leg = sys.argv[1], sys.argv[2]
k = LEGS.index(leg)
for b, root in B.items():
    p = os.path.join(root, c)
    if not os.path.isdir(p):
        continue
    te = float(json.load(open(os.path.join(p, "result.json"), encoding="utf-8"))["event_t_s"])
    d = np.load(os.path.join(p, "pads.npz"))
    t = d["t"] - te
    J = d["F_cyl_min_interval"].astype(float).copy()
    air = d["airborne"].astype(bool)
    J[air] = d["F_cyl_mean_20ms"][air]
    J /= 1e3
    for a, z in ((3.0, 4.0), (4.0, float(t[-1]))):
        w = (t >= a) & (t <= z)
        i = int(np.argmin(J[w].min(axis=1)))
        kk = int(np.argmin(J[w][i]))
        print(b, f"[{a},{z:.1f}] min {J[w][i, kk]:.3f} kN {LEGS[kk]} @ {t[w][i]:.3f} s;",
              "per leg", np.round(J[w].min(axis=0), 2))
    w = (t >= 0) & (t <= 4.0)
    a_ = air[w, k]
    tt = t[w]
    edges = np.flatnonzero(np.diff(a_.astype(int)))
    iv = []
    st = tt[0] if a_[0] else None
    for e in edges:
        if not a_[e] and a_[e + 1]:
            st = tt[e + 1]
        elif a_[e] and not a_[e + 1]:
            iv.append((round(float(st), 3), round(float(tt[e]), 3)))
            st = None
    if st is not None:
        iv.append((round(float(st), 3), round(float(tt[-1]), 3)))
    dt = float(np.median(np.diff(d["t"])))
    print(b, leg, "airborne intervals 0..4 s", iv, "sum", round(float(a_.sum() * dt), 3),
          "min J 0..4", round(float(J[w, k].min()), 3), "@", round(float(tt[np.argmin(J[w, k])]), 3))
