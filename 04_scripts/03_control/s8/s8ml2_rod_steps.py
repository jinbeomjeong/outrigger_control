"""Rev. 48: every rod-pressure step > 100 bar in the ML pilot rerun against a lock-law band.

The lock law (hydraulics s8 10.1): a locked leg has dp_r = -R(s) dp_h above the rod floor,
R(s) = (beta_r/beta_h) (L0h + s) / (L0r + s_max - s). Bounds over the sensitivity range
(L0h 0.05..0.08, L0r 0.02..0.10, kappa_beta 1.10, stroke margin 5 mm):
  R_ub(s) = 1.10 (0.08 + s') / (0.02 + 0.70 - s'), s' = min(s + 0.005, 0.699)
  R_lb(s) = (0.05 + s'') / (0.10 + 0.70 - s'') / 1.10, s'' = max(s - 0.005, 0)
A rise toward the floor clamp can give |dp_r| < R |dp_h| (floor), so the band test for a fall
uses ratio <= R_ub only when the new reading is near the floor (<= 5 bar g).

Prints per step: run, leg, t, dp_r, dp_h (readings), stroke reading, ratio = -dp_r/dp_h, R_lb,
R_ub, previous-period issued command, current-period issued command, the INFO reason the
controller logged (if any), and the verdict of the band rule.
Usage: python -I s8ml2_rod_steps.py <batch_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
S_MAX = 0.70


def r_ub(s):
    s1 = min(s + 0.005, S_MAX - 1e-3)
    return 1.10 * (0.08 + s1) / (0.02 + S_MAX - s1)


def r_lb(s):
    s2 = max(s - 0.005, 0.0)
    return (0.05 + s2) / (0.10 + S_MAX - s2) / 1.10


batch = Path(sys.argv[1])
n = {"band": 0, "not": 0}
for d in sorted((batch / "episodes").iterdir()):
    if d.name.startswith("_") or not (d / "r8_series.npz").exists():
        continue
    rec = np.load(d / "record" / "record.npz", allow_pickle=True)
    r8 = np.load(d / "r8_series.npz", allow_pickle=True)
    t = rec["t"]
    hm = rec["meas.head_pressure"] / 1e5
    rm = rec["meas.rod_pressure"] / 1e5
    st = rec["meas.stroke"]
    u = r8["issued_u"] * 1e3
    ev = [str(e) for e in json.loads((d / "controller_events.json").read_text(encoding="utf-8"))]
    dr = np.diff(rm, axis=0)
    dh = np.diff(hm, axis=0)
    for k, leg in zip(*np.nonzero(np.abs(dr) > 100.0)):
        tk = t[k + 1]
        reason = [e.split("name='")[1].rstrip("')") for e in ev
                  if f"t_s={tk:.1f}" in e.replace(f"{tk:.14f}", f"{tk:.1f}") and LEGS[leg] in e
                  and ("INFO_PRESSURE_STEP" in e or "FALLBACK" in e or "FAULT_REASON" in e)]
        if not reason:
            reason = [e.split("name='")[1].rstrip("')") for e in ev
                      if abs(float(e.split("t_s=")[1].split(",")[0]) - tk) < 0.05 and LEGS[leg] in e
                      and ("INFO_PRESSURE_STEP" in e or "FALLBACK" in e or "FAULT_REASON" in e)]
        s = float(st[k, leg])
        ratio = -dr[k, leg] / dh[k, leg] if abs(dh[k, leg]) > 1e-6 else np.inf
        lo, hi = r_lb(s), r_ub(s)
        opposite = np.sign(dr[k, leg]) == -np.sign(dh[k, leg])
        near_floor = rm[k + 1, leg] <= 5.0 or rm[k, leg] <= 5.0
        in_band = opposite and (ratio <= hi * 1.4) and (ratio >= lo / 1.4 or near_floor)
        n["band" if in_band else "not"] += 1
        print(f" {d.name:10s} {LEGS[leg]} t {tk:6.2f} dp_r {dr[k, leg]:+7.1f} dp_h {dh[k, leg]:+7.1f} s {s:.3f}"
              f" ratio {ratio:6.2f} band [{lo:.2f},{hi:.2f}] u_prev {u[k, leg]:+5.2f} u_now {u[k+1, leg]:+5.2f}"
              f" logged {reason} -> lock-law band {'yes' if in_band else 'no'}")
print(n)
