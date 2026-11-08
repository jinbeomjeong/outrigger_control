"""Time trace of VB open-loop runs: roll / pitch, stroke differences, sinkage, pad loads, leg speeds."""
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {"J1_VB": R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_J1_B_VB",
        "G1_VB": R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_G1_B_VB",
        "J1_V0": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0"}
lines = []
for name, p in RUNS.items():
    z = np.load(p / "series.npz")
    t = z["t_s"]
    lines.append(f"== {name}")
    lines.append("t  roll  pitch | s FL FR RL RR [mm] | sink FL FR RL RR [mm] | N FL FR RL RR [kN] | crawler kN")
    for tq in (20, 24, 25, 25.5, 26.0, 26.2, 26.32, 26.4, 26.6, 27, 28, 29, 29.4, 30, 31, 32, 33, 34, 35, 36):
        k = min(int(np.searchsorted(t, tq - 1e-9)), len(t) - 1)
        s = z["s_motor_m"][k] * 1e3
        sk = z["pad_sinkage_geometric_m"][k] * 1e3
        n = z["scm_pad_normal_N"][k] / 1e3
        rp = z["roll_pitch_deg"][k]
        fc = z["F_cyl_N"][k] / 1e3
        lines.append(f"{t[k]:6.3f} {rp[0]:+.3f} {rp[1]:+.3f} | " + " ".join(f"{v:6.1f}" for v in s) + " | "
                     + " ".join(f"{v:6.1f}" for v in sk) + " | " + " ".join(f"{v:6.1f}" for v in n)
                     + f" | Fcyl " + " ".join(f"{v:6.1f}" for v in fc)
                     + f" | {z['scm_crawler_normal_N'][k] / 1e3:7.1f}")
    fp = p / "flow_series.npz"
    if fp.exists():
        f = np.load(fp)
        cols = [str(c) for c in f["columns"]]
        rows = f["rows"]
        ci = {c: i for i, c in enumerate(cols)}
        lines.append("flow: t v_FL v_FR v_RL v_RR [mm/s] p_load FL FR RL RR [bar] Q_dem Q_sum [L/min]")
        for tq in (10, 15, 20, 24, 26, 28, 30, 32, 34, 35.9):
            k = min(int(np.searchsorted(rows[:, 0], tq - 1e-9)), len(rows) - 1)
            r = rows[k]
            lines.append(f"{r[0]:6.2f} " + " ".join(f"{r[ci['v_' + l]] * 1e3:6.2f}" for l in ("FL", "FR", "RL", "RR"))
                         + " | " + " ".join(f"{r[ci['p_load_' + l]] / 1e5:6.1f}" for l in ("FL", "FR", "RL", "RR"))
                         + f" | {r[ci['Q_dem']] * 6e4:6.2f} {r[ci['Q_sum']] * 6e4:6.2f}")
Path(sys.argv[1]).write_text("\n".join(lines), "utf-8")
print("ok")
