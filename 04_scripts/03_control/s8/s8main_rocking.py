"""Rev. 51: diagonal rocking after a fast front settle (ML78 tail) - lift intervals, rocking decay,
actuator work in the twist mode.

Usage: python -I s8main_rocking.py <case_dir> [t_span_s]
Engine time; t_ev = result.event_t_s.
  - per leg lift intervals from pads.airborne (1 ms), with the max pad gap estimate
    (pads 'N' <= 0; gap = not recorded -> stroke-based: s_motor change not used; we print
    the minimum F_cyl and the airborne duration only)
  - diagonal load D(t) = (F_FL + F_RR) - (F_FR + F_RL) [kN], 5 ms mean, its successive
    extrema after the event and the log-decrement damping estimate between them
  - twist-mode actuator velocity n . u_applied (n = (+,-,-,+)/2 from the record, 10 Hz,
    zero-order hold) and the twist work W_tw = sum over 1 ms of D/2 * (n . u) dt per 0.5 s
    bin (positive = actuators push energy into the diagonal load difference)
  - controller reapproach events
Read only.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
case = Path(sys.argv[1])
span = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
t_ev = float(res["event_t_s"])
pads = np.load(case / "pads.npz", allow_pickle=True)
rec = np.load(case / "record" / "record.npz", allow_pickle=True)
tp = pads["t"]
m = (tp >= t_ev - 0.5) & (tp <= t_ev + span)
t = tp[m] - t_ev
F = pads["F_cyl"][m] / 1e3
air = pads["airborne"][m].astype(bool)
print(f"event t {t_ev:.3f} s; pre-event F_cyl (mean -0.5..0 s) {np.round(F[t < 0].mean(axis=0), 1)} kN")
for L in range(4):
    a = air[:, L]
    edges = np.flatnonzero(np.diff(a.astype(int)))
    starts = [t[i + 1] for i in edges if not a[i]]
    ends = [t[i + 1] for i in edges if a[i]]
    if a[0]:
        starts = [t[0]] + starts
    if a[-1]:
        ends = ends + [t[-1]]
    iv = [(round(s, 3), round(e, 3), round(e - s, 3)) for s, e in zip(starts, ends)]
    print(f"  {LEGS[L]} lifts {iv}; min F {F[:, L].min():.1f} kN at {t[np.argmin(F[:, L])]:.3f}")
# diagonal load, 5 ms mean
k = 5
n5 = len(t) // k
t5 = t[: n5 * k].reshape(n5, k).mean(axis=1)
F5 = F[: n5 * k].reshape(n5, k, 4).mean(axis=1)
D = (F5[:, 0] + F5[:, 3]) - (F5[:, 1] + F5[:, 2])
D0 = np.median(D[t5 < 0])
d = D - D0
post = t5 > 0.05
idx = np.flatnonzero(post)
ext = [i for i in idx[1:-1] if (d[i] - d[i - 1]) * (d[i + 1] - d[i]) < 0 and abs(d[i]) > 2.0]
# keep alternating extrema with the largest magnitude per half-cycle
pk = []
for i in ext:
    if pk and np.sign(d[pk[-1]]) == np.sign(d[i]):
        if abs(d[i]) > abs(d[pk[-1]]):
            pk[-1] = i
    else:
        pk.append(i)
print(f"diagonal load D0 {D0:.1f} kN; extrema (t, dD kN):")
print("   " + ", ".join(f"({t5[i]:.2f},{d[i]:+.0f})" for i in pk[:30]))
amps = np.array([abs(d[i]) for i in pk])
if len(amps) >= 3:
    # log decrement over full cycles (every 2nd extremum)
    for j in range(0, len(pk) - 2, 2):
        a0, a2 = amps[j], amps[j + 2]
        T = t5[pk[j + 2]] - t5[pk[j]]
        zeta = np.log(a0 / a2) / np.sqrt(4 * np.pi**2 + np.log(a0 / a2) ** 2) if a2 > 0 else np.nan
        print(f"   cycle {t5[pk[j]]:.2f}-{t5[pk[j+2]]:.2f} s: f {1/T:.2f} Hz, |dD| {a0:.0f} -> {a2:.0f} kN, zeta {zeta:.3f}")
# twist actuator work
tr = rec["t"] - t_ev
ua = rec["u_applied"]
nvec = np.array([0.5, -0.5, -0.5, 0.5])
utw = ua @ nvec  # m/s
j = np.clip(np.searchsorted(tr, t, side="right") - 1, 0, len(tr) - 1)
utw_1ms = utw[j]
Dfull = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2]) - D0
P = 0.5 * Dfull * 1e3 * utw_1ms  # W
dt = np.median(np.diff(t))
print("twist actuator power per 0.5 s bin [J] (D/2 * n.u), and mean n.u [mm/s]:")
for b0 in np.arange(0.0, span, 0.5):
    mb = (t >= b0) & (t < b0 + 0.5)
    print(f"   {b0:4.1f}-{b0+0.5:4.1f} s: W {P[mb].sum()*dt:+8.1f} J, n.u {1e3*utw_1ms[mb].mean():+5.2f} mm/s, |dD| max {np.abs(Dfull[mb]).max():6.1f} kN")
ev = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
print("controller events after the event:")
for e in ev:
    ts = float(str(e).split("t_s=")[1].split(",")[0])
    if t_ev - 0.1 <= ts <= t_ev + span:
        print(f"   {ts - t_ev:+.2f} {str(e).split('name=')[1][:-1]}")
