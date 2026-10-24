"""FL floor-point rise per lift episode (same formula as s6_control._floor_point_heights_m)."""
import json
import sys
from pathlib import Path

import numpy as np

KN = np.array([25905744.2, 25905744.2, 19504614.9, 19504614.9])  # YAML contact.rigid_floor.L1.kn_per_pad_N_m
for d in map(Path, sys.argv[1:]):
    pads = np.load(d / "pads.npz")
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    t0 = res["settings"]["start_t_s"]
    t_ev = res["event_t_s"]
    tp = pads["t"] - t0
    n = np.asarray(pads["n_world"], float)
    n4 = np.repeat(n[:, None, :], 4, axis=1)
    load = np.clip(pads["N"], 0, None)
    fp = pads["contact_point_world"] + (load / KN)[..., None] * n4
    h = np.einsum("tij,tij->ti", fp, n4)
    before = (tp >= t_ev - 0.1) & (tp < t_ev)
    rise = h[:, 0] - h[before, 0].mean()
    lifted = pads["N"][:, 0] <= 0
    m = (tp >= t_ev) & (tp <= t_ev + 5) & lifted
    idx = np.flatnonzero(m)
    br = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[br + 1]]
    ends = np.r_[idx[br], idx[-1]]
    out = []
    for a, b in zip(starts, ends):
        out.append((round(float(tp[a] - t_ev), 3), round(float(tp[b] - tp[a]) + 0.001, 3), round(float(rise[a:b + 1].max()) * 1e3, 2)))
    smot = pads["s_motor"][:, 0]
    k0 = np.searchsorted(tp, t_ev)
    print(d.name, "episodes (t_rel, dur s, rise mm):", out)
    print("   FL motor stroke change at episode peaks [mm]:",
          [round(float(smot[np.searchsorted(tp, t_ev + e[0])] - smot[k0]) * 1e3, 2) for e in out])
