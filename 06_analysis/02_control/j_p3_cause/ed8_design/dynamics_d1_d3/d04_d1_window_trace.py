"""d04 (D-1): 10 Hz trace of one probe leg's first move with the plant state of all legs.

For runs R12 top-FR-Fs8 o0.0 M-a2 / M-A, round 1, probed legs FR, RL, RR: per read from 0.3 s
before the first extend command to 0.3 s after the extended read: command, motor stroke
(s_ref), piston x (plant), the controller's piston reading (``m.stroke_corrected_m``), force
reading (T4h ``p_h A_h - p_r A_ann``), the seal force f and F_s, stick flag, locked flag, for
every leg; plus the event of the window: which read is mid / extended.

Usage: conda run -n dynamics-dev python -I -B d04_d1_window_trace.py <d00 scratch dir>
Output: d04_d1_window_trace.csv (this folder).
"""
import csv
import math
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
A_H = np.array([math.pi / 4 * 0.13 ** 2] * 2 + [math.pi / 4 * 0.11 ** 2] * 2)
A_ROD = np.array([math.pi / 4 * 0.11 ** 2] * 2 + [math.pi / 4 * 0.09 ** 2] * 2)
A_ANN = A_H - A_ROD
RUNS = ("R12_top-FR-Fs8-o0.0_D8-M-a2", "R12_top-FR-Fs8-o0.0_D8-M-A")


def longest(path: Path) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    key = "t" if f"{objs[0]}|t" in z.files else "m.t_s"
    best = max(objs, key=lambda o: len(z[f"{o}|{key}"]) if f"{o}|{key}" in z.files else 0)
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


def main() -> int:
    scratch = Path(sys.argv[1])
    rows = []
    for run in RUNS:
        t4h = dict(np.load(scratch / "t4h" / f"{run}.npz", allow_pickle=False))
        plant = longest(scratch / "logs" / f"{run}_plant.npz")
        ctrl = longest(scratch / "logs" / f"{run}_ctrl.npz")
        t = t4h["t_s"]
        F = t4h["head_pressure_Pa"] * A_H - t4h["rod_pressure_Pa"] * A_ANN
        ph = np.char.lower(t4h["phase"].astype(str))
        first_probe = np.flatnonzero(ph == "probe")
        i_a = first_probe[0]
        i_b = i_a
        while i_b < len(t) and ph[i_b] == "probe":
            i_b += 1
        for k in range(max(i_a - 3, 0), min(i_b + 3, len(t))):
            ip = int(np.argmin(np.abs(plant["t"] - t[k])))
            ic = int(np.argmin(np.abs(ctrl["m.t_s"] - t[k])))
            row = {"run": run, "t_s": round(float(t[k]), 2), "phase": ph[k],
                   "plant_t_s": round(float(plant["t"][ip]), 3)}
            for j, leg in enumerate(LEGS):
                Fs = float(plant["Fs"][ip, j])
                f = float(plant["f"][ip, j])
                row.update({
                    f"{leg}_cmd_mm_s": round(float(t4h["command_m_s"][k, j]) * 1e3, 3),
                    f"{leg}_sref_mm": round(float(plant["sref"][ip, j]) * 1e3, 4),
                    f"{leg}_x_mm": round(float(plant["x"][ip, j]) * 1e3, 4),
                    f"{leg}_read_piston_mm": round(float(ctrl["m.stroke_corrected_m"][ic, j]) * 1e3, 4)
                    if "m.stroke_corrected_m" in ctrl else None,
                    f"{leg}_motor_t4h_mm": round(float(t4h["motor_stroke_m"][k, j]) * 1e3, 4),
                    f"{leg}_F_kN": round(float(F[k, j]) / 1e3, 3),
                    f"{leg}_f_kN": round(f / 1e3, 3),
                    f"{leg}_stuck": int(abs(f) < Fs - 1.0),
                    f"{leg}_locked": int(plant["locked"][ip, j]),
                })
            rows.append(row)
    with (OUT / "d04_d1_window_trace.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("rows", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
