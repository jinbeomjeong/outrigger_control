"""F1 on the calibrated reading: controller nominal = F_lower (no fallback, no allowance) after CHECK."""
import sys, os, json, numpy as np
d = sys.argv[1]
pads = np.load(os.path.join(d, "pads.npz"))
r8 = np.load(os.path.join(d, "r8_series.npz"))
res = json.load(open(os.path.join(d, "result.json"), encoding="utf-8"))
t = r8["t"]; tp = pads["t"]
idx = np.clip(np.searchsorted(tp, t - 1e-9), 0, tp.size - 1)
F = pads["F_cyl"][idx]; f = pads["f_seal"][idx]
ph = r8["phase"]
cal = r8["F_lower_N"]
raw = r8["F_hat_N"]
post = ph != "check"
off = (raw - cal)[post]
print("raw - calibrated (per leg, kN) min/max:", np.round(off.min(0) / 1e3, 3), np.round(off.max(0) / 1e3, 3))
e = (cal - F + f)[post]
print("calibrated sensor error eps+f (kN) min:", np.round(e.min(0) / 1e3, 3), "max:", np.round(e.max(0) / 1e3, 3))
fs = np.array([8000, 8000, 6666.4, 6666.4])
exc = np.abs(cal - F)[post] - fs - 600
print("F1 (calibrated) excess max kN:", round(exc.max() / 1e3, 3), "violations:", int((exc > 1).sum()))
# near F_min band (F in [F_min-5, F_min+10] kN)
fmin = 9414.59
near = (F[post] > fmin - 5e3) & (F[post] < fmin + 10e3)
if near.any():
    print("near-F_min calibrated sensor error eps+f max |.| kN:", round(np.abs(e[near]).max() / 1e3, 3), "n", int(near.sum()))
