"""Stored flow-off S8 soil run: code state, first contact per leg, approach speed, command before TOUCH. Read only."""
import json
from pathlib import Path

import numpy as np

D = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_FINAL-REP_20261030_223359\S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0")
r = json.loads((D / "result.json").read_text(encoding="utf-8"))
print("meta keys", list(r["meta"])[:30])
print("runner_meta", str(r.get("runner_meta"))[:300])
print("params", r["meta"].get("params_sha256"), r["meta"].get("params_file_sha256"), r["meta"].get("reference_sha256") and "refs")
cs = r.get("code_state") or {}
print("code keys", list(cs))
for k in ("git", "files", "code_files", "git_files", "git_state"):
    if k in cs:
        print(k, json.dumps(cs[k])[:1500])
print("c2_setup keys", list(r["c2_setup"]))
print("step_series", str(r.get("step_series"))[:300])
z = np.load(D / "record" / "record.npz", allow_pickle=False)
print("rec keys", list(z.keys()))
t = z["t"]
print("rec t", t[0], t[1], t[-1], len(t), "dt", t[1] - t[0])
Fn = z["F_contact_n"]
s = z["s_motor"] * 1e3
u = z["u_cmd"] * 1e3
ua = z["u_applied"] * 1e3
F = z["F_cyl"] / 1e3
for i, leg in enumerate(("FL", "FR", "RL", "RR")):
    k = int(np.argmax(Fn[:, i] > 0.0))
    k2 = int(np.argmax(Fn[:, i] > 3000.0))
    print(leg, "first Fn>0 t", round(float(t[k]), 2), "s", round(float(s[k, i]), 3), "Fn", round(float(Fn[k, i]), 1), "Fn>3kN t", round(float(t[k2]), 2), "s", round(float(s[k2, i]), 3))
for tq in (8.1, 10, 12.0, 12.7, 12.8, 12.9, 13, 15, 20, 22, 24, 26, 28, 29, 30, 31, 31.5, 31.6, 32):
    k = int(np.searchsorted(t, tq - 1e-6))
    print("t", round(float(t[k]), 2), "u", np.round(u[k], 3), "ua", np.round(ua[k], 3), "s", np.round(s[k], 2), "Fcyl", np.round(F[k], 1), "Fn", np.round(Fn[k] / 1e3, 1))
print("r8 keys", list(np.load(D / "r8_series.npz", allow_pickle=False).keys()))
print("step keys", list(np.load(D / "step_series.npz", allow_pickle=False).keys())[:40])
