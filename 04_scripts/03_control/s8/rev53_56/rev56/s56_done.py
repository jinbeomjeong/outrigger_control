"""First DONE time after the event (10 Hz r8_series phase) for the 17 ids: E / A / 768, plus the
DONE-gate quantities at 1 s before DONE is impossible to rebuild, so we report the twist reading
|n^T F_hat| (s8_series F_hat_N, n = [+1, -1, -1, +1] for FL FR RL RR) at 10, 12, 14, 16 s.
"""
import json
import os
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s8" / "rev53_56" / "rev56"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ---
ROOT = str(REPO / r"07_results\S8")
B = {"E": ROOT + r"\c37_20261025_180821\E_drain\episodes",
     "A": ROOT + r"\c36_20261025_155317\A_rt\episodes",
     "R": ROOT + r"\ml_main_20261025_090131\episodes"}
IDS = sorted(os.listdir(B["E"]))
N = np.array([1.0, -1.0, -1.0, 1.0])
out = {}
for c in IDS:
    row = {}
    for b, root in B.items():
        p = os.path.join(root, c)
        te = float(json.load(open(os.path.join(p, "result.json"), encoding="utf-8"))["event_t_s"])
        s = np.load(os.path.join(p, "r8_series.npz"), allow_pickle=True)
        t, ph = s["t"] - te, [str(x) for x in s["phase"]]
        done = next((round(float(t[i]), 1) for i in range(len(t)) if t[i] >= 0 and ph[i] == "done"), None)
        s8 = np.load(os.path.join(p, "s8_series.npz"), allow_pickle=True)
        t8 = s8["t"] - te
        tw = s8["F_hat_N"] @ N / 1e3
        samp = {}
        for tt in (8, 10, 12, 14, 16, 20):
            i = int(np.argmin(abs(t8 - tt)))
            samp[tt] = round(float(tw[i]), 2)
        row[b] = dict(done=done, twist_kN=samp)
    out[c] = row
for c in IDS:
    print(c, {b: out[c][b]["done"] for b in "EAR"}, "twist E", out[c]["E"]["twist_kN"], "R", out[c]["R"]["twist_kN"])
d_er = [out[c]["E"]["done"] - out[c]["R"]["done"] for c in IDS if out[c]["E"]["done"] and out[c]["R"]["done"]]
d_ea = [out[c]["E"]["done"] - out[c]["A"]["done"] for c in IDS if out[c]["E"]["done"] and out[c]["A"]["done"]]
d_ar = [out[c]["A"]["done"] - out[c]["R"]["done"] for c in IDS if out[c]["A"]["done"] and out[c]["R"]["done"]]
for name, d in (("E-768", d_er), ("E-A", d_ea), ("A-768", d_ar)):
    d = np.array(d)
    print(name, "n", len(d), "median", round(float(np.median(d)), 2), "mean", round(float(d.mean()), 2),
          "later>0.1", int((d > 0.1).sum()), "earlier<-0.1", int((d < -0.1).sum()), "max", round(float(d.max()), 1),
          "min", round(float(d.min()), 1))
for b in "EAR":
    v = [out[c][b]["done"] for c in IDS if out[c][b]["done"] is not None]
    print("done", b, "n", len(v), "median", float(np.median(v)), "max", max(v))
json.dump(out, open(os.path.join(str(OUT_DIR), "s56_done.json"), "w"), indent=1)
