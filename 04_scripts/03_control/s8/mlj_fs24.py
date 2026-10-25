"""MLJ_FS24 (front FR fast settlement) decomposition of the s6 common rows 3 / 4 / 5a.

Reads one case directory (Record 10 Hz + pads 1 ms). Engine time [s]. Window = event ..
last re-contact of the event legs (FR + diagonal RL) + T3 0.82 s (U-S8-32 / U58 physical).
Prints: per-leg true cylinder force minima before / in / after the window, lift-off spans,
moving head pressure F/A_p (Record, u_applied != 0) split by in / out window and direction,
the peak's leg / time / phase / command, and the rocking amplitude (1 s moving-mean residual,
s6 definition) in the window and after the re-READY.
"""
import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])  # head area [m^2], spec 219.2
T3 = 0.82

d = Path(sys.argv[1])
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
rec = np.load(d / "record" / "record.npz", allow_pickle=True)
pads = np.load(d / "pads.npz", allow_pickle=True)
r8 = np.load(d / "r8_series.npz", allow_pickle=True)
print("event:", json.dumps(res.get("event"), ensure_ascii=True)[:800])
t_ev = float(res["event_t_s"])
phases = [(float(a), b) for a, b in res["phases"]]
print("phases:", phases)
T0 = float(res["settings"]["start_t_s"])  # engine time of controller t = 0 (judge time base)
tp = pads["t"] - T0
t = rec["t"] - T0
print(f"time bases: record t[0]={t[0]:.3f} pads t[0]={tp[0]:.4f} event_t_s={t_ev:.3f}")

N = pads["N"]
lifted = N <= 0.0
fmin = pads["F_cyl_min_interval"]
# event legs FR (1) + diagonal RL (2)
ev_legs = [1, 2]
after = tp >= t_ev
last_rc = t_ev
for j in ev_legs:
    idx = np.flatnonzero(lifted[after, j])
    if len(idx):
        last_rc = max(last_rc, float(tp[after][min(idx[-1] + 1, after.sum() - 1)]))
w_end = last_rc + T3
print(f"window [{t_ev:.3f}, {w_end:.3f}] (rel end {w_end - t_ev:.3f} s)")
re_ready = next((a for a, b in phases if a > t_ev and b == "ready"), None)
print("re-READY", re_ready)

# crawler lift-off: first pad time after which all legs carry (approx: phase level start)
t_lo = next(a for a, b in phases if b == "level")
segs = {"before": (tp >= t_lo) & (tp < t_ev), "window": (tp >= t_ev) & (tp <= w_end),
        "after": tp > w_end}
for name, msk in segs.items():
    mins = [float(fmin[msk, j].min()) / 1e3 for j in range(4)]
    arg = [float(tp[msk][np.argmin(fmin[msk, j])]) for j in range(4)]
    print(f"F_cyl 1 ms min [{name}] kN:", {LEGS[j]: (round(mins[j], 2), round(arg[j], 3)) for j in range(4)})
dt = float(np.median(np.diff(tp)))
for j in range(4):
    lw = lifted[segs["window"], j].sum() * dt
    lo = lifted[segs["after"], j].sum() * dt
    lb = lifted[segs["before"], j].sum() * dt
    print(f"lift {LEGS[j]}: before {lb:.3f} s, window {lw:.3f} s, after {lo:.3f} s")

# item 4: Record F_cyl / A_p at moving samples
ua = rec["u_applied"]
p = rec["F_cyl"] / A_P / 1e5
moving = ua != 0
inw = (t >= t_ev) & (t <= w_end)
for name, msk in (("all moving", moving), ("moving out of window", moving & ~inw[:, None]),
                  ("extend out of window", (ua > 0) & ~inw[:, None]),
                  ("moving in window", moving & inw[:, None])):
    if msk.any():
        k, j = np.unravel_index(np.argmax(np.where(msk, p, -np.inf)), p.shape)
        ph = r8["phase"][k] if "phase" in r8.files else None
        print(f"item4 [{name}]: {p[k, j]:.1f} bar {LEGS[j]} t={t[k]:.2f} (rel {t[k]-t_ev:+.2f}) "
              f"u_applied={ua[k, j]*1e3:+.2f} mm/s issued={r8['issued_u'][k, j]*1e3:+.2f} phase={ph}")
# samples above 180 bar while moving
hi = moving & (p > 180.0)
for k, j in zip(*np.nonzero(hi)):
    print(f"  >180 bar moving: {LEGS[j]} t={t[k]:.2f} rel {t[k]-t_ev:+.2f} p={p[k, j]:.1f} "
          f"u_applied={ua[k, j]:+.3e} m/s, issued={r8['issued_u'][k, j]*1e3:+.2f} mm/s, reapproach cmp={r8['cmp_reapproach_u'][k, j]*1e3:+.2f}, "
          f"twist cmp={r8['cmp_twist_u'][k, j]*1e3:+.2f}, guard={r8['cmp_guard_u'][k, j]*1e3:+.2f}")
# 1 ms head peak in window (any state)
pw = pads["F_cyl"][segs["window"]] / A_P / 1e5
k, j = np.unravel_index(np.argmax(pw), pw.shape)
print(f"1 ms head F/A_p peak in window: {pw[k, j]:.1f} bar {LEGS[j]} t={tp[segs['window']][k]:.3f}")
print("1 ms head_pressure max per leg whole run [bar]:", np.round(pads["head_pressure"].max(axis=0) / 1e5, 1))

if re_ready is not None:
    mr = tp >= re_ready
    print("F_cyl 1 ms min after re-READY kN:", np.round(fmin[mr].min(axis=0) / 1e3, 2))
    mo = (tp > w_end) & (tp < re_ready)
    print("F_cyl 1 ms min window end .. re-READY kN:", np.round(fmin[mo].min(axis=0) / 1e3, 2))
hpk = pads["head_pressure"]
kk, jj = np.unravel_index(np.argmax(hpk), hpk.shape)
ir = min(int(np.searchsorted(t, tp[kk])), len(t) - 1)
print(f"1 ms head_pressure peak {hpk[kk, jj]/1e5:.1f} bar {LEGS[jj]} t={tp[kk]:.3f} (rel {tp[kk]-t_ev:+.3f}); "
      f"rod {pads['rod_pressure'][kk, jj]/1e5:.1f} bar; u_applied(Record next) {ua[ir, jj]*1e3:+.3f} mm/s; "
      f"law-C saturation steps (result.monitor) {res['monitor'].get('saturation_step_count')}")

# item 5a: rocking amplitude, s6 definition = max |att - 1 s moving mean| (10 samples at 10 Hz)
q = rec["body_quat_wxyz"]
w, x, y, z = q.T
roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
pitch = np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))
rp = np.column_stack([roll, pitch])


def amp(mask):
    seg = rp[mask]
    if len(seg) < 12:
        return None
    kern = np.ones(10) / 10
    mov = np.column_stack([np.convolve(seg[:, i], kern, mode="same") for i in range(2)])
    r = np.abs(seg - mov)[5:-5]
    k = int(np.argmax(r.max(axis=1)))
    return float(r.max()), float(t[mask][5:-5][k])


print("rocking amp whole after lift-off:", amp(t >= t_lo))
print("rocking amp before event:", amp((t >= t_lo) & (t < t_ev)))
print("rocking amp in window:", amp(inw))
if re_ready is not None:
    print("rocking amp after re-READY:", amp(t >= re_ready))
print("rocking amp after window:", amp(t > w_end))
