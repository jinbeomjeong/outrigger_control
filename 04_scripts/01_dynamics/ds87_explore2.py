"""D-S8-7 exploratory look 2: per-leg cylinder force (force law, 1 ms), airborne flags, leg compression
s_motor - s_link, seal state, for selected settle episodes (event - 0.2 .. event + T s).

Usage: python -I ds87_explore2.py <extract_dir> <out_png> <T_s> RUN [RUN ...]
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
src = Path(sys.argv[1])
T = float(sys.argv[3])
runs = sys.argv[4:]
fig, axs = plt.subplots(len(runs), 2, figsize=(17, 2.8 * len(runs)), squeeze=False)
for r, run in enumerate(runs):
    z = np.load(src / f"{run}.npz", allow_pickle=True)
    info = json.loads(str(z["info"]))
    t = z["p_t"] - info["t_ev"]
    w = (t > -0.2) & (t < T)
    F = z["p_F_cyl"] / 1e3
    ax = axs[r, 0]
    for i, n in enumerate(LEGS):
        ax.plot(t[w], F[w, i], label=n, color=f"C{i}")
        air = z["p_airborne"][w, i]
        ax.fill_between(t[w], -20 - 8 * i, -14 - 8 * i, where=air, color=f"C{i}", step="mid")
    ax.legend(ncol=4, fontsize=7)
    ax.set_ylabel(f"{run}\nF_cyl [kN]")
    ax.set_title(f"{info['leg']} {info['depth_m']*1e3:.1f} mm / {info['ramp_s']:.3f} s, Fs {info['fs_kN']}")
    ax = axs[r, 1]
    c = (z["p_s_motor"] - z["p_s_link"]) * 1e3
    for i, n in enumerate(LEGS):
        ax.plot(t[w], c[w, i] - c[(t > -1) & (t < -0.1), i].mean(), label=n, color=f"C{i}")
    ax.set_ylabel("compression change [mm]")
    for a in axs[r]:
        a.grid(alpha=0.3)
for a in axs[-1]:
    a.set_xlabel("t - t_event [s]")
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=80)
print("saved", sys.argv[2])
