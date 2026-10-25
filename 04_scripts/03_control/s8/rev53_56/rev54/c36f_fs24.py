"""MLJ_FS24_Fs0: post-window true-force dip (RR 6.97 kN) in bundle D vs the original MLJ run.

Prints per-leg true rod force, pad N, phase, re-approach / probe events between event + 2 s and
re-READY; same for the original run. Also the minimum over [event + 2.71 s, re-READY].
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
RUNS = {
    "D": str(REPO / r"07_results\S8\c36_20261025_155317\D_fs24\MLJ_FS24_Fs0"),
    "orig": str(REPO / r"07_results\S8\mlj_20261025_080212\MLJ_FS24_Fs0"),
}
pat = re.compile(r"t_s=([0-9.]+), name='([^']+)'")
LEGS = ["FL", "FR", "RL", "RR"]
for tag, path in RUNS.items():
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    keys = [k for k in r if "event" in k.lower()]
    te = None
    for k in ("event_t_s", "t_event_s"):
        if k in r:
            te = r[k]
    if te is None and isinstance(r.get("event"), dict):
        te = r["event"].get("t_s")
    print("=====", tag, "event keys", keys, "te", te)
    ev = json.load(open(os.path.join(path, "controller_events.json"), encoding="utf-8"))
    evs = []
    for e in ev:
        m = pat.search(e)
        if m:
            evs.append((float(m.group(1)), m.group(2)))
    # S8C result.json event time is in the judge base; series / pads are 3.0 s later (engine base)
    te = te + 3.0
    print("  events:", [(round(t - te, 2), n) for t, n in evs if -0.2 < t - te < 30 and not n.startswith("INFO_PRESSURE_STEP")])
    s = np.load(os.path.join(path, "r8_series.npz"))
    ts, ph = s["t"], s["phase"]
    idx = np.where(ts > te)[0]
    seqp = []
    for i in idx:
        if not seqp or seqp[-1][0] != ph[i]:
            seqp.append((str(ph[i]), round(ts[i] - te, 1)))
    print("  phases:", seqp)
    p = np.load(os.path.join(path, "pads.npz"))
    t = p["t"]
    F = p["F_cyl"] / 1e3
    rr = None
    for name, tt in seqp:
        if name == "ready" and tt > 1:
            rr = tt
    w = (t >= te + 2.71) & (t <= te + (rr if rr else 30))
    j = np.argmin(F[w], axis=0)
    print("  min F over [ev+2.71, re-READY] per leg:",
          [(LEGS[k], round(float(F[w][j[k], k]), 2), round(float(t[w][j[k]] - te), 2)) for k in range(4)])
    for tt in np.arange(2.5, 4.1, 0.1):
        i = int(np.argmin(np.abs(t - (te + tt))))
        k = int(np.argmin(np.abs(ts - (te + tt))))
        print(f"   +{tt:.1f} ph={ph[k]:6s} F={np.round(F[i], 1)} N={np.round(p['N_raw'][i]/1e3, 1)} "
              f"u_issued[mm/s]={np.round(s['issued_u'][k]*1e3, 2)} reapp_u={np.round(s['cmp_reapproach_u'][k]*1e3, 2)} "
              f"Flow={np.round(s['F_lower_est_N'][k]/1e3, 1)}")
