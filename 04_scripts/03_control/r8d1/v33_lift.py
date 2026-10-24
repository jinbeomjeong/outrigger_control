"""Lift-off intervals (1 ms pads) of all legs after the event, plus RR stroke rate, for any batch."""
import json
import sys
from pathlib import Path

import numpy as np

d = Path(sys.argv[1])
pads = np.load(d / "pads.npz")
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
t0 = res["settings"]["start_t_s"]
t_ev = res.get("event_t_s")
if t_ev is None:
    t_ev = float(sys.argv[2])
tp = pads["t"] - t0
N = pads["N"]
dt = tp[1] - tp[0]
print(d.parent.name, d.name, "t_ev", round(t_ev, 3), "phases", [(round(a, 2), b) for a, b in res["phases"] if t_ev - 0.5 < a < t_ev + 30])
for leg, name in enumerate(["FL", "FR", "RL", "RR"]):
    m = (tp >= t_ev) & (tp <= t_ev + 6.0) & (N[:, leg] <= 0)
    if not m.any():
        continue
    idx = np.flatnonzero(m)
    br = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[br + 1]]
    ends = np.r_[idx[br], idx[-1]]
    iv = [(round(float(tp[a] - t_ev), 3), round(float(tp[b] - t_ev), 3)) for a, b in zip(starts, ends)]
    print(f"  {name} lift {m.sum()*dt:.3f} s {iv}")
# RR motor stroke change over the first 4 s
s = pads["s_motor"]
k0 = np.searchsorted(tp, t_ev)
for tt in (0.5, 1.0, 2.0, 3.0, 4.0):
    k = np.searchsorted(tp, t_ev + tt)
    print(f"  ds_motor at +{tt}s [mm] {np.round((s[k]-s[k0])*1e3,2)}")
# FL load envelope per rocking cycle (min/max in 0.75 s bins)
for b in range(7):
    m = (tp >= t_ev + 0.1 + 0.75 * b) & (tp < t_ev + 0.1 + 0.75 * (b + 1))
    print(f"  bin {b}: FL N min {N[m,0].min()/1e3:7.1f} max {N[m,0].max()/1e3:7.1f} kN; RR max {N[m,3].max()/1e3:6.1f}")
