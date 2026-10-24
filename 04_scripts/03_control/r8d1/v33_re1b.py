"""RE1b event cases: FL lift intervals (1 ms), phases, commands and stroke around the RR drop.

Times are case-relative (record t, same as verify windows: pads t - t0 handled by using record t).
"""
import json
import sys
from pathlib import Path

import numpy as np

batch = Path(sys.argv[1])
case = sys.argv[2]
d = batch / case
rec = np.load(d / "record" / "record.npz")
r8 = np.load(d / "r8_series.npz", allow_pickle=True)
pads = np.load(d / "pads.npz")
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
ev = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
t0 = res["settings"]["start_t_s"]
t_ev = res["event_t_s"]
print("case", case, "event_t_s", t_ev, "t0", t0)
print("phases", [(round(a, 2), b) for a, b in res["phases"] if t_ev - 2 < a < t_ev + 60])
print("probe_intervals", res.get("probe_intervals"))
for e in ev:
    ts = float(e.split("t_s=")[1].split(",")[0]) - t0
    if t_ev - 2 < ts < t_ev + 40:
        print(f"  ev {ts:8.3f} {e.split('name=')[1]}")
tp = pads["t"]
# pads t: absolute or relative? compare
print("pads t range", tp[0], tp[-1], "record t range", rec["t"][0], rec["t"][-1])
tp = tp - t0
N = pads["N"]
dt = tp[1] - tp[0]
for leg, name in enumerate(["FL", "FR", "RL", "RR"]):
    m = (tp >= t_ev) & (tp <= t_ev + 5.0) & (N[:, leg] <= 0)
    if not m.any():
        continue
    idx = np.flatnonzero(m)
    # group intervals
    br = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[br + 1]]
    ends = np.r_[idx[br], idx[-1]]
    iv = [(round(tp[a] - t_ev, 3), round(tp[b] - t_ev, 3)) for a, b in zip(starts, ends)]
    print(f"{name} lift total {m.sum()*dt:.3f} s, intervals rel. event {iv}")
t = rec["t"] - t0
ph = r8["phase"]
w = np.flatnonzero((t >= t_ev - 0.3) & (t <= t_ev + 3.0))
print(" t-tev  phase    N[kN] FL FR RL RR | u_issued mm/s | s_motor-s_motor(ev) mm | guard")
k0 = np.searchsorted(t, t_ev)
s_ev = rec["s_motor"][k0]
for k in w:
    j = min(np.searchsorted(tp, t[k]), len(tp) - 1)
    print(f"{t[k]-t_ev:5.2f} {str(ph[k]):8s} {np.round(N[j]/1e3,1)} | {np.round(r8['issued_u'][k]*1e3,2)} | "
          f"{np.round((rec['s_motor'][k]-s_ev)*1e3,2)} | {bool(r8['guard_active'][k])}")
