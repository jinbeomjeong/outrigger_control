"""Event-leg exit window vs the 10 Hz sample grid (u10 reruns).

For every rerun: the event leg's loaded window after its first rocking lift (1 ms true cylinder
force >= exit level F_min + 5 kN, from the first re-load to the next lift), the controller samples
inside it and the exit-confirmation sample (3rd consecutive sample at or above the exit level of
the lower load estimate, from u11_periods). Prints the per-period table of selected runs and
writes u12_exit_window.csv and u12_exit_window.png.

Usage: python -I -B u12_exit_window.py <rerun_dir> <folder>
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
rerun, folder = Path(sys.argv[1]), Path(sys.argv[2])
runs = list(csv.DictReader((folder / "u11_runs.csv").open(encoding="utf-8")))
periods = list(csv.DictReader((folder / "u11_periods.csv").open(encoding="utf-8")))
out_rows = []
fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for r in runs:
    if r["event"] != "RE1bF":
        continue
    leg = LEGS.index(r["leg"])
    dg = DIAG[leg]
    stem = f"R12_{r['level']}-{r['leg']}-Fs{float(r['fs_kN']):g}-o{r['offset_s']}-{r['event']}-ready_{r['setting']}"
    z = np.load(rerun / "logs" / f"{stem}_rows.npz")
    rows, t_ev = z["rows"], float(z["t_ev"])
    tr = rows[:, 0] - t_ev
    contact, F = rows[:, 1:5], rows[:, 5:9]
    pr = [p for p in periods if p["run"] == r["run"]]
    exit_level = float(pr[0]["exit_level_kN"]) * 1e3
    ev_l = json.loads(r["event_leg_lifts"])
    dg_l = json.loads(r["diag_leg_lifts"])
    t_reload = float(r["event_leg_reload_to_exit_level_s"])
    t_relift = ev_l[1][0] if len(ev_l) > 1 else np.nan
    # last 1 ms time before the relift with F >= exit level
    m = (tr > t_reload) & (tr < t_relift) & (F[:, leg] >= exit_level)
    t_hold_end = float(tr[np.flatnonzero(m)[-1]]) if m.any() else np.nan
    samples = [float(p["t_rel_s"]) for p in pr if 0.0 < float(p["t_rel_s"]) <= 1.2]
    inside = [s for s in samples if t_reload <= s <= t_hold_end]
    starts = json.loads(r["reapp_starts"])
    ends = json.loads(r["reapp_ends"])
    out_rows.append({"run": r["run"], "offset_s": r["offset_s"], "phase_phi_s": round(float(r["offset_s"]) % 0.1, 4),
                     "t_reload_s": t_reload, "t_hold_end_s": round(t_hold_end, 3),
                     "window_s": round(t_hold_end - t_reload, 3),
                     "samples_in_window": ";".join(f"{s:g}" for s in inside),
                     "n_samples_in_window": len(inside),
                     "event_leg_exit_s": ends.get(r["leg"], [None])[0],
                     "diag_start_s": starts.get(LEGS[dg], [None])[0],
                     "diag_first_lift_end_s": dg_l[0][1] if dg_l else None,
                     "diag_start_inside_first_lift": (starts.get(LEGS[dg], [99])[0] < dg_l[0][1]) if dg_l else None,
                     "n_event_lifts": len(ev_l), "n_diag_lifts": len(dg_l),
                     "pair_union_s": r["pair_union_s"], "pass": r["pass"], "failed": r["failed"]})
    if r["setting"] in ("V0", "VBM") and r["leg"] in ("FL", "FR") and float(r["fs_kN"]) in (2.0, 4.0):
        ax = axes[0] if r["setting"] == "V0" else axes[1]
        w = (tr >= -0.05) & (tr <= 1.2)
        line, = ax.plot(tr[w], F[w, leg] / 1e3, lw=0.9,
                        label=f"{r['leg']}-Fs{float(r['fs_kN']):g} o{r['offset_s']} pu {r['pair_union_s']} s")
        ss = np.array(samples)
        ax.plot(ss, np.interp(ss, tr, F[:, leg]) / 1e3, "o", ms=3, color=line.get_color())
for ax, title in zip(axes, ("V0 (stored-grid offsets)", "VBM (edition 7 a2, seen keys)")):
    ax.axhline(14.415, color="k", lw=0.8, ls="--")
    ax.set_ylabel("event-leg cylinder force F [kN]")
    ax.set_title(title + ": dots = 10 Hz controller samples; dashed = exit level F_min + 5 kN")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(alpha=0.3)
axes[1].set_xlabel("time after the event start t - t_ev [s]")
fig.tight_layout()
fig.savefig(folder / "u12_exit_window.png", dpi=130)
keys = list(out_rows[0].keys())
with (folder / "u12_exit_window.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(out_rows)
for o in out_rows:
    print(o["run"], "reload", o["t_reload_s"], "hold_end", o["t_hold_end_s"], "in", o["samples_in_window"],
          "exit", o["event_leg_exit_s"], "diag_start", o["diag_start_s"], "diag_lift1_end",
          o["diag_first_lift_end_s"], "lifts", o["n_event_lifts"], o["n_diag_lifts"], "pu", o["pair_union_s"])
# per-period table of two contrasting runs
for run in ("V0|bottom-FL-Fs2-RE1bF-o0.0", "V0|bottom-FL-Fs2-RE1bF-o0.025",
            "VBM|bottom-FR-Fs0-RE1bF-o0.0", "VBM|bottom-FR-Fs2-RE1bF-o0.075"):
    print("\n##", run)
    for p in periods:
        if p["run"] == run and -0.05 <= float(p["t_rel_s"]) <= 1.1:
            print(f"  t {float(p['t_rel_s']):6.3f} {p['phase']:<14} load FL {p['load_FL_kN']:>7} FR {p['load_FR_kN']:>7} "
                  f"RL {p['load_RL_kN']:>7} RR {p['load_RR_kN']:>7} low {p['low_FL']}{p['low_FR']}{p['low_RL']}{p['low_RR']} "
                  f"active [{p['active']}]")
