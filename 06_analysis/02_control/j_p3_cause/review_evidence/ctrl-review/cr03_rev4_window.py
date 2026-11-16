"""Rev 4 vs rev 5 locked bound of one leg around the RR lock (read only).

Usage: python -I -B cr03_rev4_window.py <npz_rev4> <npz_rev5> <leg> <t0> <t1>
Prints the keys that hold a model or locked bound, then per T4h sample: head, rod reading,
the rev 4 bound series (if any) and the rev 5 jp3 model bound. Pressures in bar.
"""

import sys

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def main() -> None:
    p4, p5, leg_name = sys.argv[1], sys.argv[2], sys.argv[3]
    t0, t1 = float(sys.argv[4]), float(sys.argv[5])
    leg = LEGS.index(leg_name)
    with np.load(p4, allow_pickle=False) as d4, np.load(p5, allow_pickle=False) as d5:
        print("rev4 keys:", sorted(d4.files))
        bound_keys = [k for k in d4.files if "bound" in k or "estimate" in k or "lower" in k]
        print("rev4 bound-like keys:", bound_keys)
        t = d4["t_s"]
        sel = np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9))
        t5 = d5["jp3_t_s"]
        for k in sel:
            j = int(np.argmin(np.abs(t5 - t[k])))
            row = f"t={t[k]:6.2f} head={d4['head_pressure_Pa'][k, leg] / 1e5:7.2f}"
            for key in bound_keys:
                arr = d4[key]
                if arr.ndim == 2 and arr.shape[0] == t.size and arr.shape[1] == 4:
                    row += f" {key}={arr[k, leg] / 1e5:8.2f}"
            row += f" | rev5 model={d5['jp3_model_bound_Pa'][j, leg] / 1e5:8.2f}"
            if "command_m_s" in d4.files:
                row += f" u={d4['command_m_s'][k, leg] * 1e3:8.4f}"
            print(row)


if __name__ == "__main__":
    main()
