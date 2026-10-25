"""Per-case detail: 0.5 s work bins (rev. 52 definition), 0.1 s trace of D - D0, n.u, and the
pad airborne / settle info. Usage: python -I c36_work_detail.py <case_dir> [...]"""
import json
import sys
from pathlib import Path

import numpy as np

N_TW = np.array([0.5, -0.5, -0.5, 0.5])
LEGS = ["FL", "FR", "RL", "RR"]
for c in sys.argv[1:]:
    case = Path(c)
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    t_ev = float(res["event_t_s"])
    pads = np.load(case / "pads.npz", allow_pickle=True)
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    tp = pads["t"]
    m = (tp >= t_ev - 0.5) & (tp <= t_ev + 8.0)
    t = tp[m] - t_ev
    f = pads["F_cyl"][m]
    air = pads["airborne"][m].astype(bool)
    d = (f[:, 0] + f[:, 3]) - (f[:, 1] + f[:, 2])
    d0 = np.median(d[t < 0])
    tr = rec["t"] - t_ev
    ua = rec["u_applied"]
    uc = rec["u_cmd"]
    j = np.clip(np.searchsorted(tr, t, side="right") - 1, 0, len(tr) - 1)
    u = (ua @ N_TW)[j]
    p = 0.5 * (d - d0) * u
    print(f"== {case.name} {res.get('episode')} D0 {d0/1e3:.1f} kN, t_end {t[-1]:.2f}")
    bins = [p[(t >= a) & (t < a + 0.5)].sum() * 1e-3 for a in np.arange(0, min(8, t[-1]), 0.5)]
    print("  bins J:", " ".join(f"{b:+.0f}" for b in bins))
    print("  t   dD[kN] n.u[mm/s]  u_applied FL FR RL RR [mm/s]  airborne")
    for a in np.arange(0.0, min(5.0, t[-1]), 0.1):
        k = np.argmin(np.abs(t - a))
        kr = np.argmin(np.abs(tr - a))
        print(f"  {a:3.1f} {(d[k]-d0)/1e3:+7.1f} {1e3*u[k]:+6.2f}   "
              + " ".join(f"{1e3*x:+6.2f}" for x in ua[kr])
              + "   " + "".join(LEGS[i] if air[k, i] else "--" for i in range(4)))
