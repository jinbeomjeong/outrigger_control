"""MLJ_SS9P (C-S8-24, R45-4 dedicated): probe request after re-READY, round-start lower bounds.

Judge time base. Prints the event, phases, probe_request record, probe intervals and, at each
probe start after the event, the controller lower bound F_lower_est_N and the true 1 ms force
of every leg, against F_min + 15 kN (R45-4 trigger).
"""
import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
F_MIN = 9414.59
d = Path(sys.argv[1])
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
T0 = float(res["settings"]["start_t_s"])
pads = np.load(d / "pads.npz", allow_pickle=True)
r8 = np.load(d / "r8_series.npz", allow_pickle=True)
tp = pads["t"] - T0
t = r8["t"] - T0
print("event:", json.dumps(res.get("event"), ensure_ascii=True)[:500])
print("event_t_s", res.get("event_t_s"))
print("phases", [(round(float(a), 2), b) for a, b in res["phases"]])
pr = res.get("probe_request")
print("probe_request:", json.dumps(pr, ensure_ascii=True)[:1500])
print("probe_intervals:", json.dumps(res.get("probe_intervals"), ensure_ascii=True)[:800])
t_ev = float(res["event_t_s"])
ph = json.loads((d / "probe_history.json").read_text(encoding="utf-8"))
print("probe_history type", type(ph).__name__, (list(ph.keys())[:10] if isinstance(ph, dict) else len(ph)))
rounds = ph if isinstance(ph, list) else ph.get("rounds", ph.get("history", []))
for r in rounds[:40]:
    if isinstance(r, dict):
        print({k: (v if not isinstance(v, (list, dict)) else str(v)[:120]) for k, v in r.items()})
# lower bounds around the probe intervals after the event
for iv in res.get("probe_intervals") or []:
    a = float(iv[0]) if isinstance(iv, (list, tuple)) else float(iv.get("t_start_s", 0))
    if a < t_ev:
        continue
    k = int(np.searchsorted(t, a))
    lo = r8["F_lower_est_N"][k] / 1e3
    tru = np.array([np.interp(t[k], tp, pads["F_cyl"][:, j]) for j in range(4)]) / 1e3
    print(f"probe start {a:.2f}: lower {np.round(lo, 1)} true {np.round(tru, 1)} kN; trigger < {(F_MIN + 15e3) / 1e3:.2f}")
# min lower bound per leg in READY after re-READY and min true
m = t >= t_ev
k = int(np.nanargmin(r8["F_lower_est_N"][m, 3]))
print(f"RR lower min at t={t[m][k]:.1f} phase={r8['phase'][m][k]}")
print("min F_lower_est after event per leg kN:", np.round(np.nanmin(r8["F_lower_est_N"][m], axis=0) / 1e3, 2))
mm = tp >= t_ev
print("min true 1 ms after event per leg kN:", np.round(pads["F_cyl_min_interval"][mm].min(axis=0) / 1e3, 2))
