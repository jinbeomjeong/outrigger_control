"""ML-2: D1 rod-sensor fallback on pilot-check settle episodes.

For one episode and leg, prints the 10 Hz controller samples around the event: phase, issued
command, the 1 ms record's true head / rod pressure at the sample, the one-period step of the
rod pressure (D1 step check: |dp| > 100 bar), the 1 ms max |dp_r/dt| between samples, cylinder
force, controller lower bound and its estimate, and the minimum true force after the event.
Also F2 = F_lower_est - F (the lower bound the controller used minus the truth).

Usage: python -I s8ml_d1.py <case_dir> <leg 0-3> [t_before_s t_after_s]
Times printed are engine times (r8_series / pads 't').
"""
import json
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1])
leg = int(sys.argv[2])
tb = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
ta = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
ev_t = float(res["event_t_s"])
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
t, tp = r8["t"], pads["t"]
print(f"case {case.name} leg {leg} event_t {ev_t:.3f} r8 t [{t[0]:.2f},{t[-1]:.2f}] pads t [{tp[0]:.3f},{tp[-1]:.3f}]")
print("episode", res["episode"])
idx = np.clip(np.searchsorted(tp, t), 0, len(tp) - 1)  # exact alignment (python-expert 2026-10-25)
ph, pr = pads["head_pressure"][:, leg], pads["rod_pressure"][:, leg]
F = pads["F_cyl"][:, leg]
print("  t      phase    u_iss  p_h   p_r   dp_r(1per) F_cyl  F_hat  F_lowEst  F2=Flow-F  s_motor  stroke_true")
prev = None
for k in np.flatnonzero((t >= ev_t - tb) & (t <= ev_t + ta)):
    j = idx[k]
    dpr = (pr[j] - pr[idx[k - 1]]) / 1e5 if k > 0 else float("nan")
    print(f" {t[k]:6.2f} {str(r8['phase'][k]):8s} {1e3*r8['issued_u'][k, leg]:+6.2f}"
          f" {ph[j]/1e5:6.1f} {pr[j]/1e5:6.1f} {dpr:+8.1f}"
          f" {F[j]/1e3:7.2f} {r8['F_hat_N'][k, leg]/1e3:7.2f} {r8['F_lower_est_N'][k, leg]/1e3:8.2f}"
          f" {(r8['F_lower_est_N'][k, leg]-F[j])/1e3:+8.2f}"
          f" {1e3*pads['s_motor'][j, leg]:8.2f} {1e3*pads['stroke_true'][j, leg]:8.2f}")
m = tp >= ev_t
print(f" min true F_cyl after event: {F[m].min()/1e3:.2f} kN at {tp[m][np.argmin(F[m])]:.3f}; "
      f"min F_cyl_min_interval {pads['F_cyl_min_interval'][m, leg].min()/1e3:.2f} kN")
print(f" max rod p after event {pr[m].max()/1e5:.1f} bar; max |dp_r/dt| 1ms {np.max(np.abs(np.diff(pr[m])))/1e5/1e-3:.0f} bar/s")
# F2 sample stats after event (controller samples)
k_after = np.flatnonzero(t >= ev_t)
F2 = r8["F_lower_est_N"][k_after, leg] - F[idx[k_after]]
print(f" F2 > 0.6 kN samples after event: {(F2 > 600).sum()} of {len(k_after)}, max {F2.max()/1e3:.2f} kN")
# Is the true force ever below F_min while the lower bound says > 1.4 F_min?
fmin = 9414.59  # YAML control.F_min_cylinder_N
low = F[idx[k_after]] < fmin
print(f" samples with true F < F_min: {low.sum()}; with true F < 1.4 F_min: {(F[idx[k_after]] < 1.4*fmin).sum()};"
      f" of those, lower-bound >= 1.4 F_min: {((F[idx[k_after]] < 1.4*fmin) & (r8['F_lower_est_N'][k_after, leg] >= 1.4*fmin)).sum()}")
# all legs min true force after event
for L in range(4):
    print(f"  leg {L}: min F_cyl after event {pads['F_cyl'][m, L].min()/1e3:7.2f} kN, airborne any {bool(pads['airborne'][m, L].any())}")
ev = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
for e in ev:
    print("  ev", e)
