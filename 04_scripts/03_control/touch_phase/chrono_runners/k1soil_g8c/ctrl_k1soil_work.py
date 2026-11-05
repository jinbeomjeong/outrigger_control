"""Energy view of the READY tail: work F_cyl * d(s_motor) per leg and SCM normal force work on the pad sinkage, per 10 s block, for the Fs8 on and off rows.
Twist displacement commanded during the hold window on the Fs0 on row. Also the D profile at 0.5 s steps after the event. Writes work.json."""
import json
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
HERE = Path(__file__).resolve().parent
out = {}
for tag, s in (("FLFs8", "RE1bF_on"), ("FLFs8", "RE1bF_off"), ("FLFs0", "RE1bF_on")):
    d = BATCH / f"S9EV_G1_{tag}_{s}"
    z = np.load(d / "step_series.npz")
    t = np.asarray(z["t_s"], float)
    F = np.asarray(z["F_cyl_N"], float)
    sm = np.asarray(z["s_motor_m"], float)
    N = np.asarray(z["scm_pad_normal_N"], float)
    sink = np.asarray(z["pad_sinkage_geometric_m"], float)
    rows = []
    for lo in np.arange(70.0, 128.0, 10.0):
        m = (t >= lo) & (t < lo + 10)
        W_act = np.sum(0.5 * (F[m][1:] + F[m][:-1]) * np.diff(sm[m], axis=0), axis=0)
        W_scm = np.sum(0.5 * (N[m][1:] + N[m][:-1]) * np.diff(sink[m], axis=0), axis=0)
        rows.append({"t_s": float(lo), "W_motor_J": W_act.round(4).tolist(), "W_motor_sum_J": round(float(W_act.sum()), 4), "W_scm_J": W_scm.round(4).tolist(), "W_scm_sum_J": round(float(W_scm.sum()), 4)})
    out[f"{tag}_{s}"] = rows
    print(tag, s)
    for r in rows:
        print("  ", json.dumps(r))
n = np.array([1, -1, -1, 1]) / 2.0
for tag, s in (("FLFs0", "RE1bF_on"), ("FLFs0", "RE1bF_off")):
    cc = np.load(BATCH / f"S9EV_G1_{tag}_{s}" / "controller_commands.npz")
    tc, u = np.asarray(cc["t_s"]), np.asarray(cc["issued_u_m_s"])
    rec = {}
    for hi in (33.2, 33.3, 36.3):
        m = (tc >= 31.7) & (tc <= hi)
        rec[f"n_int_u_mm_to_{hi}"] = round(float(np.sum(u[m] @ n) * 0.1 * 1e3), 4)
    m = (tc >= 31.7) & (tc <= 33.2)
    rec["u_mean_mm_s"] = (u[m].mean(axis=0) * 1e3).round(3).tolist()
    out[f"hold_{tag}_{s}"] = rec
    print(tag, s, rec)
for tag in ("FLFs0", "FLFs8", "RRFs0"):
    prof = {}
    for s in ("RE1bF_off", "RE1bF_on"):
        res = json.loads((BATCH / f"S9EV_G1_{tag}_{s}" / "result.json").read_text(encoding="utf-8"))
        tev = float(res["soil_event"]["driver"]["t_ev_s"])
        r = np.asarray(np.load(BATCH / f"S9EV_G1_{tag}_{s}" / "soil_event_series.npz")["rows"], float)
        tt = r[:, 0] - tev
        F = r[:, 5:9]
        D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
        prof[s] = {f"{x:g}": round(float(D[(tt >= x) & (tt < x + 0.5)].mean()) / 1e3, 2) for x in (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25)}
    out[f"D_profile_{tag}"] = prof
    print(tag, "D", prof)
(HERE / "work.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
