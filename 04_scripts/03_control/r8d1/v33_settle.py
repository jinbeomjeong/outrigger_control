"""RE1b settle case: RR load history around the R-5 trigger, compare with the first-pass batch."""
import json
import sys
from pathlib import Path

import numpy as np

for d in map(Path, sys.argv[1:]):
    rec = np.load(d / "record" / "record.npz")
    pads = np.load(d / "pads.npz")
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    ev = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
    t0 = res["settings"]["start_t_s"]
    t_ev = res.get("event_t_s")
    print("==", d.parent.name, d.name, "event_t_s", t_ev, "event", res["settings"].get("event"))
    print("phases", [(round(a, 2), b) for a, b in res["phases"] if a > 20])
    for e in ev:
        ts = float(e.split("t_s=")[1].split(",")[0]) - t0
        if ts > 20 and "INFO_PRESSURE_ZERO" not in e:
            print(f"  ev {ts:8.3f} {e.split('name=')[1]}")
    t = rec["t"] - t0
    tp = pads["t"] - t0
    N = pads["N"]
    F = rec["F_cyl"]
    hp = rec["meas.head_pressure"]
    m = (t >= t_ev - 0.3) & (t <= t_ev + 3.5)
    for k in np.flatnonzero(m):
        j = min(np.searchsorted(tp, t[k]), len(tp) - 1)
        print(f"  t-tev {t[k]-t_ev:5.2f} Fcyl kN {np.round(F[k]/1e3,1)} padN RR {N[j,3]/1e3:6.1f} "
              f"u_cmd mm/s {np.round(rec['u_cmd'][k]*1e3,2)}")
    # RR min force 1 ms after event
    mm = tp >= t_ev
    print("  min Fcyl_min_interval after event per leg kN", np.round(pads["F_cyl_min_interval"][mm].min(axis=0) / 1e3, 2))
