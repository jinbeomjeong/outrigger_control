"""WIKA cases: sensor error (eps + f) against load level and phase; controller lower above F_hat."""
import sys, os, numpy as np
d = sys.argv[1]
pads = np.load(os.path.join(d, "pads.npz"))
r8 = np.load(os.path.join(d, "r8_series.npz"))
t = r8["t"]; tp = pads["t"]
idx = np.clip(np.searchsorted(tp, t - 1e-9), 0, tp.size - 1)
F = pads["F_cyl"][idx]; f = pads["f_seal"][idx]
Fhat = r8["F_hat_N"]; low = r8["F_lower_N"]; ph = r8["phase"]
e = Fhat - F + f  # sensor share of the reading error (friction removed)
post = ph != "check"
bins = [(-20e3, 5e3), (5e3, 20e3), (20e3, 60e3), (60e3, 100e3), (100e3, 200e3)]
for leg in range(4):
    line = []
    for a, b in bins:
        s = post & (F[:, leg] >= a) & (F[:, leg] < b)
        if s.any():
            line.append(f"[{a/1e3:.0f},{b/1e3:.0f}) n={s.sum()} e[{e[s,leg].min()/1e3:.2f},{e[s,leg].max()/1e3:.2f}]")
    print("leg", leg, " | ".join(line))
pos = (low - Fhat) > 100
k = np.flatnonzero(pos.any(axis=1))
print("lower > F_hat samples:", k.size, "phases:", sorted(set(ph[k].tolist())) if k.size else None,
      "t range:", (t[k].min(), t[k].max()) if k.size else None)
# F1 limit excess by phase (limit = F_s,leg + 0.6 kN)
fs = np.array([8000, 8000, 6666.4, 6666.4])
exc = np.abs(Fhat - F) - fs - 600
for p in sorted(set(ph.tolist())):
    s = ph == p
    print(f"phase {p:6s} F1 excess max {exc[s].max()/1e3:.2f} kN, viol {int((exc[s] > 1).sum())}")
