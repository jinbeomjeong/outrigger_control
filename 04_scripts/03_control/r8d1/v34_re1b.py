"""rerun33 RE1b diagnosis: command components per 10 Hz sample around the RR drop.

Usage: python v34_re1b.py <case_dir> [t_after_s]
Times are relative to the event (event_t_s in result.json, case-relative).
"""
import json
import sys
from pathlib import Path

import numpy as np

d = Path(sys.argv[1])
t_after = float(sys.argv[2]) if len(sys.argv) > 2 else 4.5
rec = np.load(d / "record" / "record.npz")
r8 = dict(np.load(d / "r8_series.npz", allow_pickle=True))
for _k in ('cmp_attitude_u','cmp_heave_u','cmp_twist_u','cmp_guard_u','cmp_reapproach_u','guard_u'):
    r8.setdefault(_k, np.full_like(r8['issued_u'], np.nan))
print('guard_u present', 'guard_u' in r8, 'cmp all nan', bool(np.isnan(r8['cmp_twist_u']).all()))
pads = np.load(d / "pads.npz")
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
ev = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
t0 = res["settings"]["start_t_s"]
t_ev = res["event_t_s"]
print("case", d.name, "t_ev(rel)", round(t_ev, 3))
for e in ev:
    ts = float(e.split("t_s=")[1].split(",")[0]) - t0
    if t_ev - 1 < ts < t_ev + 8:
        print(f"  ev {ts - t_ev:7.3f} {e.split('name=')[1][:-1]}")
meta = res.get("controller_meta", {})
for k, v in meta.items():
    if "reappro" in k.lower() or "lifted" in k.lower():
        print("meta", k, json.dumps(v)[:1500])
tp = pads["t"] - t0
N = pads["N"]
Fc = pads["F_cyl"]
t = r8["t"] - t0 if r8["t"][0] > 50 else r8["t"]
ph = r8["phase"]
k0 = np.searchsorted(tp, t_ev)
s_ev = pads["s_motor"][k0].copy()
w = np.flatnonzero((t >= t_ev - 0.2) & (t <= t_ev + t_after))
mm = lambda x: np.round(np.asarray(x) * 1e3, 2)
print(" t-ev  phase   | N 1ms [kN] FL FR RL RR | Fcyl@sample | issued mm/s | att | heave | twist | guard | reappr | ds_motor mm")
for k in w:
    j = min(np.searchsorted(tp, t[k]), len(tp) - 1)
    print(f"{t[k]-t_ev:5.2f} {str(ph[k])[:7]:7s} | {np.round(N[j]/1e3,1)} | {np.round(Fc[j]/1e3,1)} | {mm(r8['issued_u'][k])} | "
          f"{mm(r8['cmp_attitude_u'][k])} | {mm(r8['cmp_heave_u'][k])} | {mm(r8['cmp_twist_u'][k])} | {mm(r8['cmp_guard_u'][k])} | "
          f"{mm(r8['cmp_reapproach_u'][k])} | g {mm(r8['guard_u'][k])} | {mm(pads['s_motor'][j]-s_ev)}")
# lift intervals for all legs
dt = tp[1] - tp[0]
for leg, name in enumerate(["FL", "FR", "RL", "RR"]):
    m = (tp >= t_ev) & (tp <= t_ev + 6.0) & (N[:, leg] <= 0)
    if not m.any():
        continue
    idx = np.flatnonzero(m)
    br = np.flatnonzero(np.diff(idx) > 1)
    st = np.r_[idx[0], idx[br + 1]]
    en = np.r_[idx[br], idx[-1]]
    print(f"  {name} lift {m.sum()*dt:.3f} s", [(round(float(tp[a]-t_ev), 3), round(float(tp[b]-tp[a]+dt), 3)) for a, b in zip(st, en)])
# RR contact (N>0) intervals after event
m = (tp >= t_ev) & (tp <= t_ev + 8) & (N[:, 3] > 0)
idx = np.flatnonzero(m)
if idx.size:
    br = np.flatnonzero(np.diff(idx) > 1)
    st = np.r_[idx[0], idx[br + 1]]
    en = np.r_[idx[br], idx[-1]]
    print("  RR contact intervals", [(round(float(tp[a]-t_ev), 3), round(float(tp[b]-tp[a]+dt), 3)) for a, b in zip(st, en)][:12])


