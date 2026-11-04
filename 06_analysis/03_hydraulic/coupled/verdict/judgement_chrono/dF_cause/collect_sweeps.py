"""Tables and a figure from the harness interventions (sweep folder given as argument). Read only.

Run: conda run -n dynamics-dev python -I collect_sweeps.py <folder with phase_off.json, sync2.json, zero_twist.json>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
SWEEP = Path(sys.argv[1])
FIELDS = ("F_min", "leg", "F_RL_min_first8", "mean1s_RL_min", "F_RL_win", "D_te", "D_lift", "tau_te", "t_ready", "final_phase")
phase = json.loads((SWEEP / "phase_off.json").read_text(encoding="utf-8"))
sync = json.loads((SWEEP / "sync2.json").read_text(encoding="utf-8"))
zero = json.loads((SWEEP / "zero_twist.json").read_text(encoding="utf-8"))
with (HERE / "harness_interventions.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["set", "case", "eta", "eps_or_stage", *FIELDS])
    for name, rows in (("phase_off", phase), ("sync_perturbation", sync), ("zero_twist", zero)):
        for r in rows:
            j = r["job"]
            w.writerow([name, j["case"], j["eta"], j.get("eps", j.get("stage", "")),
                        *[round(r[k], 3) if isinstance(r.get(k), float) else r.get(k) for k in FIELDS]])
summary = {}
for case in ("R4", "R8", "R9"):
    off = [r for r in phase if r["job"]["case"] == case]
    sync_on = [r for r in sync if r["job"]["case"] == case and r["job"]["eta"] == 0.85]
    sync_off = [r for r in sync if r["job"]["case"] == case and r["job"]["eta"] is None]
    x = np.array([r["D_lift"] for r in off + sync_on + sync_off])
    y = np.array([r["F_RL_win"] for r in off + sync_on + sync_off])
    slope, intercept = np.polyfit(x, y, 1)
    zp = {("on" if r["job"]["eta"] else "off"): r for r in zero if r["job"]["case"] == case}
    summary[case] = {
        "phase_off_F_min_range": [min(r["F_min"] for r in off), max(r["F_min"] for r in off)],
        "phase_off_D_lift_range": [min(r["D_lift"] for r in off), max(r["D_lift"] for r in off)],
        "phase_off_tau_levels_mm": sorted({round(r["tau_te"], 3) for r in off}),
        "F_RL_win_vs_D_lift": {"slope": float(slope), "intercept": float(intercept),
                               "max_residual": float(np.abs(y - slope * x - intercept).max()), "points": len(x)},
        "on_all_F_min": [round(r["F_min"], 2) for r in sync_on],
        "off_all_F_min": sorted(round(r["F_min"], 2) for r in off + sync_off),
        "zero_twist": {"on_F_min": zp["on"]["F_min"], "off_F_min": zp["off"]["F_min"], "delta": zp["on"]["F_min"] - zp["off"]["F_min"],
                       "delta_RL_1s": zp["on"]["mean1s_RL_min"] - zp["off"]["mean1s_RL_min"],
                       "D_lift_on_off": [zp["on"]["D_lift"], zp["off"]["D_lift"]]},
    }
(HERE / "harness_interventions.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True, constrained_layout=True)
for ax, case in zip(axes, ("R4", "R8", "R9"), strict=True):
    off = sorted((r for r in phase if r["job"]["case"] == case), key=lambda r: r["job"]["eps"])
    ax.plot([r["job"]["eps"] * 100 for r in off], [r["F_RL_min_first8"] for r in off], "o-", color="C0")
    ax.set_title(f"{case}: flow limit off, RL minimum in the first 8 s")
    ax.set_xlabel("approach speed change [%]")
    ax.grid(alpha=0.3)
axes[0].set_ylabel("F_RL minimum [kN]")
fig.savefig(HERE / "phase_sweep.png", dpi=130)
print(json.dumps(summary, indent=0)[:6000])
