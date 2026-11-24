"""FL series of the first probe (before the event) in confirmation (가) T4h files (read only).

Per controller read (0.1 s): command, motor stroke, locked flag, head / rod reading, the plant rod
truth p_tr and the retract target p*_ret of the jp3 record, the P1 line fill and gate flag, the
true leg force and the seal band. Usage: h1_probe_series.py LEG T0 T1 FILE [FILE ...]."""
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")
LEGS = ("FL", "FR", "RL", "RR")
BAR = 1e5


def main(leg_name: str, t0: float, t1: float, names: list[str]) -> None:
    leg = LEGS.index(leg_name)
    for name in names:
        with np.load(T4H / name, allow_pickle=False) as d:
            t = d["t_s"]
            sel = (t >= t0 - 1e-9) & (t <= t1 + 1e-9)
            cols = {
                "u_mm_s": d["command_m_s"][sel, leg] * 1e3,
                "s_mm": d["motor_stroke_m"][sel, leg] * 1e3,
                "lock": d["locked"][sel, leg].astype(int),
                "ph": d["head_pressure_Pa"][sel, leg] / BAR,
                "pr": d["rod_pressure_Pa"][sel, leg] / BAR,
                "ptr": d["jp3_p_tr_Pa"][sel, leg] / BAR,
                "pstar": d["jp3_p_star_ret_Pa"][sel, leg] / BAR,
                "fill_mm": d["jp3_gate_fill_m"][sel, leg] * 1e3,
                "gate": d["jp3_gate_open"][sel, leg].astype(int),
                "F_kN": d["true_force_N"][sel, leg] / 1e3,
                "band_kN": d["seal_band_N"][sel, leg] / 1e3,
                "lsb_out": d["lsb_output_m_s"][sel, leg] * 1e3,
            }
            phase = d["phase"][sel]
            tt = t[sel]
        print(f"== {name} leg {leg_name} {t0}-{t1} s")
        print("   t     ph    " + " ".join(f"{k:>8s}" for k in cols))
        for k in range(len(tt)):
            vals = " ".join(f"{cols[c][k]:8.3f}" for c in cols)
            print(f"{tt[k]:6.1f} {phase[k]:5s} {vals}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4:])
