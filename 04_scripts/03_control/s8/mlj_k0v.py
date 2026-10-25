"""MLJ_K0V_fdown3.5_G4RF (C-S8-29): rod-sensor fault on FR + G4 on RR, timeline and checks.

Judge time base (engine - start_t_s). Prints phases, event / fault times, per-leg true 1 ms
minima per segment, FR command components after the fault, FR fallback lower bound vs truth,
head pressure while pushing, and h* per lock window from the controller meta (spec 218.10:
h* = (F_min + 5 kN + F_band + M A_ann + R_ub h_a A_ann) / (A_p + R_ub A_ann)).
"""
import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([np.pi / 4 * (0.13**2 - 0.11**2)] * 2 + [np.pi / 4 * (0.11**2 - 0.09**2)] * 2)
F_MIN = 9414.59
F_BAND_FALLBACK = 13000.0

d = Path(sys.argv[1])
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
T0 = float(res["settings"]["start_t_s"])
pads = np.load(d / "pads.npz", allow_pickle=True)
r8 = np.load(d / "r8_series.npz", allow_pickle=True)
rec = np.load(d / "record" / "record.npz", allow_pickle=True)
tp = pads["t"] - T0
t = r8["t"] - T0 if r8["t"][0] > 2.0 else r8["t"]
tr = rec["t"] - T0
print("event:", json.dumps(res.get("event"), ensure_ascii=True)[:400])
print("event_t_s", res.get("event_t_s"), "rod_fault", json.dumps(res.get("rod_fault"), ensure_ascii=True)[:400],
      "rod_fault_t_s", res.get("rod_fault_t_s"))
print("phases", [(round(float(a), 2), b) for a, b in res["phases"]])
t_ev = float(res["event_t_s"])
t_f = float(res["rod_fault_t_s"]) if res.get("rod_fault_t_s") is not None else None
print("r8 t[0]", r8["t"][0], "rec t[0]", rec["t"][0])
t_lo = next(float(a) for a, b in res["phases"] if b == "level")
fmin = pads["F_cyl_min_interval"]
segs = {"liftoff..event": (tp >= t_lo) & (tp < t_ev)}
if t_f is not None:
    segs["event..fault"] = (tp >= t_ev) & (tp < t_f)
    segs["fault..end"] = tp >= t_f
for name, m in segs.items():
    if m.any():
        out = {LEGS[j]: (round(float(fmin[m, j].min()) / 1e3, 2), round(float(tp[m][np.argmin(fmin[m, j])]), 2))
               for j in range(4)}
        print(f"true 1 ms min [{name}] kN (t):", out)
print("lifted samples after lift-off per leg:", (pads["N"][tp >= t_lo] <= 0).sum(axis=0))
if t_f is None:
    sys.exit()
# FR after fault
j = 1
m = t >= t_f
cg, cr, ct = r8["cmp_guard_u"][:, j], r8["cmp_reapproach_u"][:, j], r8["cmp_twist_u"][:, j]
iss = r8["issued_u"][:, j]
print(f"FR after fault: periods {m.sum()}, guard!=0 {np.sum(m & (cg != 0)) * 0.1:.1f} s, "
      f"reapproach!=0 {np.sum(m & (cr != 0)) * 0.1:.1f} s, twist>0 {np.sum(m & (ct > 0)) * 0.1:.1f} s, "
      f"issued>0 {np.sum(m & (iss > 0)) * 0.1:.1f} s, guard_active(any) {np.sum(m & (r8['guard_active'] != 0)) * 0.1:.1f} s")
print("guard_u FR max after fault mm/s:", float(np.max(np.abs(r8["guard_u"][m, j]))) * 1e3)
# lower bound vs truth on FR after fault (10 Hz controller samples vs 1 ms truth at sample time)
F_true_at = np.interp(t[m], tp, pads["F_cyl"][:, j])
lo = r8["F_lower_est_N"][m, j]
nom = r8["F_nominal_N"][m, j]
dlo = (lo - F_true_at) / 1e3
print(f"FR F_lower_est - F_true after fault: max {dlo.max():+.2f} kN (optimism if >0), median {np.median(dlo):+.2f}, "
      f"min {dlo.min():+.2f}; nominal - true median {np.median((nom - F_true_at) / 1e3):+.2f} kN")
k = int(np.argmin(dlo))
print(f"  most conservative at t={t[m][k]:.1f}: lower {lo[k]/1e3:.1f}, true {F_true_at[k]/1e3:.1f} kN")
lowtrue = F_true_at < 50e3
if lowtrue.any():
    print(f"  where true < 50 kN: n={lowtrue.sum()}, lower-true max {dlo[lowtrue].max():+.2f}, min {dlo[lowtrue].min():+.2f}")
# head pressure while FR pushes (u_applied > 0) after fault, Record
ua = rec["u_applied"][:, j]
mr = (tr >= t_f) & (ua > 0)
ph = rec["meas.head_pressure"][:, j] / 1e5
print(f"FR head (meas) while extending after fault: n={mr.sum()}, max {ph[mr].max() if mr.any() else None}")
print(f"FR head true 1 ms max after fault: {pads['head_pressure'][tp >= t_f, j].max() / 1e5:.1f} bar; "
      f"F_cyl/A_p max {pads['F_cyl'][tp >= t_f, j].max() / A_P[j] / 1e5:.1f} bar")
# h* per lock window: lock log of the controller meta as carried by the C-S8-29 verify row
ver = json.loads((d.parent / "verify_S8C.json").read_text(encoding="utf-8"))
fb = []
for row in ver["rows"]:
    if row.get("case") == d.name and str(row.get("item")).startswith("C-S8-29 rod-sensor fault + G4"):
        cm = row["rod_fault"]["controller_fallback_meta"]
        fb = list(cm.get("two_pressure.fallback_lock_log") or []) + list(cm.get("two_pressure.fallback_lock_current") or [])
        print("verify row values:", {k: row["value"][k] for k in row["value"]})
# guard component on every leg after the fault
cgall = r8["cmp_guard_u"][m]
print("guard component nonzero after fault per leg [s]:", (np.abs(cgall) > 1e-9).sum(axis=0) * 0.1,
      "| issued FR >= 0.95 x 2.5 mm/s [s]:", float(np.sum(r8["issued_u"][m, j] >= 0.95 * 2.5e-3)) * 0.1)
for w in fb:
    R, ha, M = w["ratio_bound"], w["anchor_head_Pa"], w["start_Pa"]
    hs = (F_MIN + 5000 + F_BAND_FALLBACK + M * A_ANN[j] + R * ha * A_ANN[j]) / (A_P[j] + R * A_ANN[j])
    tw = w["t_start_s"] - T0 if w["t_start_s"] > t[-1] else w["t_start_s"]
    # true head at window start..+5 s max
    mm = (tp >= tw) & (tp <= tw + 5)
    print(f"lock window t={w['t_start_s']:.2f} (judge {tw:.2f}) s={w['stroke_window_max_m']:.3f} R_ub={R:.2f} "
          f"h_a={ha/1e5:.1f} bar M={M/1e5:.1f} bar -> h*={hs/1e5:.1f} bar; F_lo at h_a="
          f"{(ha*A_P[j]-M*A_ANN[j]-F_BAND_FALLBACK)/1e3:.1f} kN; true F/A_p max next 5 s "
          f"{pads['F_cyl'][mm, j].max()/A_P[j]/1e5 if mm.any() else float('nan'):.1f} bar")
