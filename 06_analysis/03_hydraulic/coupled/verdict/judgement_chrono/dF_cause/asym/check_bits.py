"""Why do six derived pad arrays differ between the 40 s control and the stored run; first contact."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
b = next(d for d in sorted((HERE / "runs").glob("batch_*")) if (d / "ctrl_none").exists())
stored = Path(r"C:\workspace\outrigger_control\07_results\S8\final_A_bottom_rpB_Fs0_20261031_011936\A_bottom_rpB_Fs0")
a = np.load(b / "ctrl_none" / "pads.npz", allow_pickle=False)
s = np.load(stored / "pads.npz", allow_pickle=False)
print("t", a["t"].shape, s["t"].shape, "every", a["every_steps"], s["every_steps"], "sample", a["sample_s"], s["sample_s"])
for k in ("R_world", "N", "T", "L", "utilisation", "F_cyl_mean_20ms", "N_raw", "F_cyl"):
    x, y = a[k], s[k]
    n = min(len(x), len(y))
    d = np.abs(x[:n] - y[:n])
    j = np.flatnonzero(np.nan_to_num(d.reshape(n, -1)).max(axis=1) > 0) if n else []
    print(k, x.shape, y.shape, "maxdiff", np.nanmax(d), "n_diff", len(j),
          "first", None if not len(j) else int(j[0]), "last", None if not len(j) else int(j[-1]))

N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
for name in ("ctrl_none", "asym2_d000"):
    d = b / name
    p = np.load(d / "pads.npz", allow_pickle=False)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    r = np.load(d / "record" / "record.npz", allow_pickle=False)
    off = float(r["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t = p["t"] - off
    raw = p["N_raw"]
    s_m = p["s_motor"] * 1e3
    s_l = p["s_link"] * 1e3
    tc = [int(np.argmax(raw[:, i] > 0)) for i in range(4)]
    print(name, "first N_raw>0 t", np.round(t[tc], 3), "s_motor", np.round([s_m[tc[i], i] for i in range(4)], 3),
          "s_link", np.round([s_l[tc[i], i] for i in range(4)], 3))
    q = p["body_quat_wxyz"]
    for tq in (15.0, 21.0, 22.0, 22.5, 23.0, 23.5, 24.0):
        k = int(np.searchsorted(t, tq))
        print("  t", tq, "s", np.round(s_m[k], 2), "F", np.round(p["F_cyl"][k] / 1e3, 1), "tau", round(float(N @ s_m[k]), 3), "q", np.round(q[k], 6))
