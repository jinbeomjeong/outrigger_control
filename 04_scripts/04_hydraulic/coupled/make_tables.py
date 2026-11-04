"""Steady tables of the three paths, sensitivity corners and the summary figure.

Writes scenario_table.csv (long format, hand / numpy / hopsan), corner_table.csv and
fig_speed_ratio.png in 06_analysis/03_hydraulic/coupled. Steady value = mean over the
scenario window. Speeds mm/s, flows L/min, pressures bar GAUGE.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from cross_check import read_hopsan, read_numpy  # noqa: E402
from hand_calc import solve  # noqa: E402
from params import LEGS, OUT_DIR, load_params  # noqa: E402
from scenarios import BY_NAME, SCENARIOS  # noqa: E402


def hand_row(p, sc) -> dict:
    r = solve(p, sc)
    row = {"p_P": r["p_P"] / 1e5, "Q_byp": r["Q_byp"] * 6e4}
    for i, leg in enumerate(LEGS):
        row.update({f"v_{leg}": r["v"][i] * 1e3, f"Q_{leg}": r["Q"][i] * 6e4, f"p_h_{leg}": r["p_h"][i] / 1e5})
    return row


def numpy_row(sc, tag="") -> dict:
    t, n = read_numpy(OUT_DIR / "numpy" / f"{sc.name}{tag}.csv")
    m = t >= sc.t_end - sc.window
    row = {"p_P": n["p_P"][m].mean() / 1e5, "Q_byp": n["Q_byp"][m].mean() * 6e4}
    for leg in LEGS:
        row.update({f"v_{leg}": n[f"v_{leg}"][m].mean() * 1e3, f"Q_{leg}": n[f"Q_in_{leg}"][m].mean() * 6e4,
                    f"p_h_{leg}": n[f"p_h_{leg}"][m].mean() / 1e5})
    return row


def hopsan_row(sc, tag="") -> dict:
    t, h = read_hopsan(OUT_DIR / "hopsan" / f"{sc.name}{tag}.csv")
    m = t >= sc.t_end - sc.window
    row = {"p_P": (h["Pump#P2#Pressure"][m].mean() - 1e5) / 1e5, "Q_byp": h["Unloader#P2#Flow"][m].mean() * 6e4}
    for leg in LEGS:
        row.update({f"v_{leg}": h[f"Mass{leg}#P2#Velocity"][m].mean() * 1e3, f"Q_{leg}": h[f"Spool{leg}#PA#Flow"][m].mean() * 6e4,
                    f"p_h_{leg}": (h[f"Spool{leg}#PA#Pressure"][m].mean() - 1e5) / 1e5})
    return row


def main() -> None:
    p = load_params()
    fields = ["p_P", "Q_byp"] + [f"{q}_{leg}" for q in ("v", "Q", "p_h") for leg in LEGS]
    with open(OUT_DIR / "scenario_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "path", "eta_v", *fields])
        for sc in SCENARIOS:
            paths = [("hand", hand_row(p, sc)), ("numpy", numpy_row(sc))]
            if sc.hopsan:
                paths.append(("hopsan", hopsan_row(sc)))
            for path, row in paths:
                w.writerow([sc.name, path, sc.eta_v, *[f"{row[k]:.4f}" for k in fields]])

    # sensitivity corners (hand, numpy, Hopsan)
    corners = {"_low": {"dp_comp": 6e5, "dp_unl": 12e5}, "_high": {"dp_comp": 20e5, "dp_unl": 30e5},
               "_prop": {"law": "proportional"}, "_w05": {"width": 0.5e5}, "_w2": {"width": 2e5}}
    with open(OUT_DIR / "corner_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["corner", "scenario", "path", "r_FL", "r_FR", "r_RL", "r_RR", "p_P_bar_g"])
        for tag, kw in corners.items():
            pk = p.with_(**kw)
            for name in ("B85p", "B85c", "C185p", "C185c"):
                sc = BY_NAME[name]
                paths = [("hand", hand_row(pk, sc))]
                if (OUT_DIR / "numpy" / f"{name}{tag}.csv").exists():
                    paths.append(("numpy", numpy_row(sc, tag)))
                if (OUT_DIR / "hopsan" / f"{name}{tag}.csv").exists():
                    paths.append(("hopsan", hopsan_row(sc, tag)))
                for path, row in paths:
                    w.writerow([tag, name, path, *[f"{row[f'v_{leg}'] / (u * p.v_max * 1e3):.4f}" for leg, u in zip(LEGS, sc.u)],
                                f"{row['p_P']:.2f}"])
                    print(tag, name, path, [round(row[f"v_{leg}"] / (u * p.v_max * 1e3), 4) for leg, u in zip(LEGS, sc.u)],
                          round(row["p_P"], 2))

    # figure: speed ratio, numpy line and Hopsan dashes, prescribed vs rigid body at eta_v 0.85
    colours = {"FL": "#1b6ca8", "FR": "#c87f0a", "RL": "#7a5195", "RR": "#2a9d8f"}  # validate_palette.js pass
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), sharey=True, constrained_layout=True)
    for ax, name, title in ((axes[0], "B85p", "Prescribed loads: load order decides"),
                            (axes[1], "B85c", "Rigid body: twist equalises FL and FR")):
        sc = BY_NAME[name]
        tn, n = read_numpy(OUT_DIR / "numpy" / f"{name}.csv")
        th, h = read_hopsan(OUT_DIR / "hopsan" / f"{name}.csv")
        for leg in LEGS:
            ax.plot(tn, n[f"v_{leg}"] / p.v_max, color=colours[leg], lw=1.6, label=leg)
            ax.plot(th, h[f"Mass{leg}#P2#Velocity"] / p.v_max, color=colours[leg], lw=1.0, ls=(0, (2, 2)))
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("time [s]")
        ax.set_xlim(0, sc.t_end)
        ax.set_ylim(0.6, 1.08)
        ax.grid(alpha=0.25, lw=0.5)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("leg speed / $v_{max}$ [-]")
    axes[0].legend(ncol=4, frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("Four legs at $v_{max}$, $\\eta_v$ 0.85, level (solid numpy, dashed Hopsan)", fontsize=11, x=0.01, ha="left")
    fig.savefig(OUT_DIR / "fig_speed_ratio.png", dpi=200)

    # exposure summary from record_share.json
    table = json.loads((OUT_DIR / "record_share.json").read_text(encoding="utf-8"))
    print(json.dumps({c: {e: {"swaps": table[c][e]["swaps"], "res": {k: round(v, 1) for k, v in table[c][e]["residual_leg_time_s"].items()}}
                          for e in ("0.90", "0.85")} for c in list(table)[:2]}))


if __name__ == "__main__":
    main()
