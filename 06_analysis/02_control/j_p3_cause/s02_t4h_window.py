"""Step 2: print the T4h 10 Hz record around the J-P3 breach window.

Usage: python -I -B s02_t4h_window.py <npz> [t0] [t1]
Columns per leg: command [mm/s], head/rod reading [bar], true force [kN],
locked flag, motor stroke [mm]. Prints meta keys and the lock events.
"""
import json
import sys

import numpy as np


def main():
    path = sys.argv[1]
    t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 46.0
    t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 51.0
    z = np.load(path, allow_pickle=True)
    meta = json.loads(str(z["meta_json"]))
    print("meta keys:", list(meta.keys()))
    print(json.dumps(meta, indent=None)[:7000])
    t = z["t_s"]
    le = z["lock_events"]
    print("lock events in window:")
    for row in le:
        if t0 - 3 <= row[0] <= t1:
            print("  ", row)
    m = (t >= t0) & (t <= t1)
    legs = ["FL", "FR", "RL", "RR"]
    for i in np.nonzero(m)[0]:
        parts = [f"{t[i]:6.2f} {z['phase'][i]:5s}"]
        for j, lg in enumerate(legs):
            parts.append(
                f"{lg} u{z['command_m_s'][i, j]*1e3:+6.2f} ph{z['head_pressure_Pa'][i, j]/1e5:6.1f}"
                f" pr{z['rod_pressure_Pa'][i, j]/1e5:5.1f} F{z['true_force_N'][i, j]/1e3:6.1f}"
                f" Fm{z['true_force_min_N'][i, j]/1e3:6.1f} L{int(z['locked'][i, j])}"
                f" s{z['motor_stroke_m'][i, j]*1e3:7.2f}"
            )
        print(" | ".join(parts))


if __name__ == "__main__":
    main()
