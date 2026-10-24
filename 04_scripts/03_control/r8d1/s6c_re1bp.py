"""RE1bP: timeline around the RR drop (phases, commands, FL contact force, events)."""
import json
import sys
from pathlib import Path

import numpy as np

batch = Path(sys.argv[1])
case = sys.argv[2]
rec = np.load(batch / case / "record" / "record.npz")
r8 = np.load(batch / case / "r8_series.npz")
pads = np.load(batch / case / "pads.npz")
res = json.loads((batch / case / "result.json").read_text(encoding="utf-8"))
ev = json.loads((batch / case / "controller_events.json").read_text(encoding="utf-8"))
t_ev = res.get("event_t_s") + res["settings"]["start_t_s"]
print("event_t_s", t_ev, "phases", [p for p in res["phases"] if p[0] > 20])
print("events near", [e for e in ev if t_ev is not None and abs(float(e.split("t_s=")[1].split(",")[0]) - t_ev) < 80])
print("probe intervals", res.get("probe_intervals"))
tp = pads["t"]
N = pads["N"]
sel = (tp > t_ev - 0.2) & (tp < t_ev + 3.5)
lift = sel & (N[:, 0] <= 0)
if lift.any():
    print(f"FL N<=0 from {tp[lift][0]:.3f} to {tp[lift][-1]:.3f}, total {lift.sum()*(tp[1]-tp[0]):.3f} s")
t = rec["t"]
w = np.where((t >= t_ev - 0.3) & (t <= t_ev + 3.0))[0]
for k in w:
    j = np.searchsorted(tp, t[k])
    print(f"t={t[k]:6.2f} ph={r8['phase'][k]:9s} N={np.round(N[min(j,len(N)-1)]/1e3,1)} Fcyl={np.round(rec['F_cyl'][k]/1e3,1)} "
          f"u_iss mm/s={np.round(r8['issued_u'][k]*1e3,2)} u_comp={np.round(r8['computed_u'][k]*1e3,2)} guard={bool(r8['guard_active'][k])}")
