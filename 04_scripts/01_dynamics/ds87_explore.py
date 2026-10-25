"""D-S8-7 exploratory look: sum of cylinder forces / weight, pad normal forces, body rotation about the
two diagonals, seal state, for selected settle episodes (event .. event + 4 s).

Inputs: the per-episode npz written by ds87_extract.py. Plot only (no verdict).
Usage: python -I ds87_explore.py <extract_dir> <out_png> RUN [RUN ...]
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

P = dm.load_params()
GEO = dm.geometry_from_params(P)


def rp_from_quat(q):
    w, x, y, z = q.T
    R20 = 2 * (x * z - w * y)
    R21 = 2 * (y * z + w * x)
    R22 = 1 - 2 * (x * x + y * y)
    roll = np.arctan2(R21, R22)
    pitch = -np.arcsin(np.clip(R20, -1, 1))
    return roll, pitch


src = Path(sys.argv[1])
runs = sys.argv[3:]
fig, axs = plt.subplots(len(runs), 3, figsize=(17, 2.6 * len(runs)), squeeze=False)
xy = GEO.pad_xy
u1 = (xy[3] - xy[0]) / np.linalg.norm(xy[3] - xy[0])  # FL -> RR diagonal
u2 = (xy[2] - xy[1]) / np.linalg.norm(xy[2] - xy[1])  # FR -> RL diagonal
for r, run in enumerate(runs):
    z = np.load(src / f"{run}.npz", allow_pickle=True)
    info = json.loads(str(z["info"]))
    t = z["p_t"] - info["t_ev"]
    F = z["p_F_cyl"]
    pre = (t > -1.5) & (t < -0.1)
    W = np.median(F[pre].sum(1))
    roll, pitch = rp_from_quat(z["p_body_quat_wxyz"])
    roll -= np.median(roll[pre]); pitch -= np.median(pitch[pre])
    a1 = np.degrees(roll * u1[0] + pitch * u1[1])  # rotation about FL-RR axis
    a2 = np.degrees(roll * u2[0] + pitch * u2[1])
    w = (t > -0.3) & (t < 4)
    ax = axs[r, 0]
    ax.plot(t[w], F[w].sum(1) / W, "k")
    ax.set_ylabel(f"{run}\nsum F_cyl / W")
    ax.set_title(f"{info['leg']} {info['depth_m']*1e3:.1f} mm / {info['ramp_s']:.3f} s, W {W/1e3:.1f} kN, Fs {info['fs_kN']}")
    ax = axs[r, 1]
    for i, n in enumerate(dm.LEG_NAMES):
        ax.plot(t[w], z["p_N_raw"][w, i] / 1e3, label=n)
    ax.legend(ncol=4, fontsize=7)
    ax.set_ylabel("N_raw [kN]")
    ax = axs[r, 2]
    ax.plot(t[w], a1[w], label="about FL-RR")
    ax.plot(t[w], a2[w], label="about FR-RL")
    ax.legend(fontsize=7)
    ax.set_ylabel("rotation [deg]")
    for a in axs[r]:
        a.grid(alpha=0.3)
for a in axs[-1]:
    a.set_xlabel("t - t_event [s]")
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=80)
print("saved", sys.argv[2])
