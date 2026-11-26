"""d07 (D-2): the RR command, A(i) floor and P1 gate in the first re-level after PROBE 1 (S7).

T4h keys per read: ``lsb_input_m_s`` (C2 output before the lock-start components),
``lsb_output_m_s`` (after), ``lsb_a1_floor_m_s`` / ``lsb_a1_on`` (A(i)), ``lsb_ib_on``,
``command_m_s``, ``locked``, ``jp3_gate_open``, ``jp3_gate_fill_m``, ``jp3_class``; plant
``line_fill_gate.x`` (P1 fill state) and ``locked`` from the d00 plant log. Legs and window
from argv.

Usage: conda run -n dynamics-dev python -I -B d07_d2_gate_kick.py <d00 scratch dir> <leg> <t0> <t1> <run>...
Output: d07_d2_gate_kick.csv (this folder, appended per call with the run name).
"""
import csv
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")


def longest(path: Path) -> dict:
    z = np.load(path, allow_pickle=False)
    objs = sorted({k.split("|")[0] for k in z.files})
    best = max(objs, key=lambda o: len(z[f"{o}|t"]))
    return {k.split("|", 1)[1]: z[k] for k in z.files if k.startswith(best + "|")}


def main() -> int:
    scratch = Path(sys.argv[1])
    leg = LEGS.index(sys.argv[2])
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    rows = []
    for run in sys.argv[5:]:
        z = dict(np.load(scratch / "t4h" / f"{run}.npz", allow_pickle=False))
        plant = longest(scratch / "logs" / f"{run}_plant.npz")
        t = z["t_s"]
        for k in np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9)):
            ip = int(np.argmin(np.abs(plant["t"] - t[k])))
            rows.append({
                "run": run, "leg": LEGS[leg], "t_s": round(float(t[k]), 2),
                "phase": str(z["phase"][k]),
                "in_mm_s": round(float(z["lsb_input_m_s"][k, leg]) * 1e3, 4),
                "out_mm_s": round(float(z["lsb_output_m_s"][k, leg]) * 1e3, 4),
                "cmd_mm_s": round(float(z["command_m_s"][k, leg]) * 1e3, 4),
                "a1_on": int(z["lsb_a1_on"][k, leg]),
                "a1_floor_mm_s": round(float(z["lsb_a1_floor_m_s"][k, leg]) * 1e3, 4),
                "ib_on": int(z["lsb_ib_on"][k, leg]),
                "locked_t4h": int(z["locked"][k, leg]),
                "gate_open": int(z["jp3_gate_open"][k, leg]) if "jp3_gate_open" in z else None,
                "gate_fill_mm": round(float(z["jp3_gate_fill_m"][k, leg]) * 1e3, 4)
                if "jp3_gate_fill_m" in z else None,
                "jp3_class": int(z["jp3_class"][k, leg]) if "jp3_class" in z else None,
                "plant_locked": int(plant["locked"][ip, leg]),
                "plant_fill_x_mm": round(float(plant["line_fill_gate.x"][ip, leg]) * 1e3, 4),
                "plant_gate_open": int(plant["line_fill_gate.is_open"][ip, leg]),
                "D_kN": round(float(z["lsb_ib_twist_load_N"][k]) / 1e3, 3)})
    path = OUT / "d07_d2_gate_kick.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new:
            w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(" ".join(f"{k}={v}" for k, v in r.items() if k not in ("leg",)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
