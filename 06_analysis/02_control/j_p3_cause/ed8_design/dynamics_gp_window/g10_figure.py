"""G' window shift, part 10: figure (window edges per condition, P(E) by phase, m vs window lengthening).
Usage: python -I -B g10_figure.py <out_folder>
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

out = Path(sys.argv[1])
g7 = json.loads((out / "g07_window_m.json").read_text(encoding="utf-8"))
C = g7["conditions"]
fit_r, fit_h = g7["fit"]["t_r"]["coef"], g7["fit"]["t_h"]["coef"]
PH = ["0.0", "0.0125", "0.025", "0.0375", "0.05", "0.0625", "0.075", "0.0875"]
fig, ax = plt.subplots(1, 3, figsize=(16, 5))
# (1) windows: V0 ready FL / FR at F_s 2 / 4, start 0.1, base and 25/0.05 (g06 ensemble mean shifts)
sh = {k: np.array(v) / 1e3 for k, v in g7["shape_shift_pairs_ms"].items()}
rows = []
for leg, fs in (("FL", 2.0), ("FR", 4.0)):
    tr = fit_r[f"V0|{leg}"] + fit_r["a_Fs"] * fs
    th = fit_h[f"V0|{leg}"] + fit_h["a_Fs"] * fs
    rows.append((f"{leg} Fs{fs:g} 30/0.05", tr, th))
    for k in ("25/0.05", "30/0.04"):
        d = sh[k].mean(axis=0)
        rows.append((f"{leg} Fs{fs:g} {k}", tr + d[0], th + d[1]))
    for f2 in (1.0, 6.0):
        rows.append((f"{leg} Fs{f2:g} 30/0.05", fit_r[f"V0|{leg}"] + fit_r["a_Fs"] * f2,
                     fit_h[f"V0|{leg}"] + fit_h["a_Fs"] * f2))
for i, (lab, a, b) in enumerate(rows):
    ax[0].plot([a, b], [i, i], lw=5, color="tab:blue" if "30/0.05" in lab and "Fs1" not in lab and "Fs6" not in lab
               else "tab:orange")
    ax[0].plot([a + 0.2, a + 0.2], [i - 0.3, i + 0.3], color="k", lw=1)
ax[0].axvline(0.45, color="r", ls="--", lw=1, label="E limit 0.450 s")
ax[0].set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=7)
ax[0].set_xlabel("time after event [s] (controller-effective load window [t_r*, t_h*]; tick = t_r* + 0.2 s)")
ax[0].legend(fontsize=7)
ax[0].grid(alpha=0.3)
# (2) P(E) by phase
x = np.arange(8)
for j, c in enumerate(["base", "25/0.05", "30/0.04", "Fs1", "Fs3", "Fs6"]):
    ax[1].bar(x + (j - 2.5) * 0.13, [C[c]["P_by_phase"][p] for p in PH], width=0.13, label=f"{c} (m {C[c]['m_vs_model_base']})")
ax[1].plot(x, [C["stats_P_RE"]["P_by_phase"][p] for p in PH], "k*", label="stats P_RE")
ax[1].set_xticks(x, PH, fontsize=8)
ax[1].set_xlabel("phase phi = offset mod 0.1 [s]")
ax[1].set_ylabel("P(E) (diag first start <= 0.450 s)")
ax[1].legend(fontsize=7)
ax[1].grid(alpha=0.3)
# (3) m vs window lengthening for 25/0.05
L = [-10, 0, 10, 20, 30]
ax[2].plot(L, [C[f"25L{v}"]["m_vs_model_base"] for v in L], "o-", label="25/0.05, rising edge from data, window +L")
d = sh["25/0.05"]
Lm = 1e3 * (d[:, 1] - d[:, 0])
ax[2].axvspan(Lm.min(), Lm.max(), color="tab:orange", alpha=0.2, label="reduced-model L range (ensemble + valve off)")
ax[2].axhline(1.0, color="k", lw=0.8)
for mm in (0.7, 0.5):
    ax[2].axhline(mm, color="r", ls=":", lw=0.8)
ax[2].set_xlabel("window lengthening L = d t_h* - d t_r* [ms]")
ax[2].set_ylabel("m = mean P(E) / base")
ax[2].legend(fontsize=7)
ax[2].grid(alpha=0.3)
fig.tight_layout()
fig.savefig(out / "g10_window_m.png", dpi=120)
print(json.dumps({"status": "ok"}))
