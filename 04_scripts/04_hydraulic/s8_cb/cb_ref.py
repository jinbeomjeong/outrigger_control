"""Independent reference of the S8 counterbalance (CB) spec model vs Hopsan.

Single front leg, head chamber locked behind a CB/relief that vents to tank, rod side at
tank pressure (make-up), superstructure share as a mass on a spring (other legs).
Spec model: Q_cb = Q_r * y, tau dy/dt = y* - y, y* = max(p - p_cr, 0) / dp_ov (linear gradient).
Usage: python -I cb_ref.py <out.json> [hopsan_csv_A] [hopsan_csv_B]
Pressures absolute Pa inside, gauge bar in the report (p_atm = 1e5 Pa).
"""

import json
import sys

import numpy as np
from scipy.integrate import solve_ivp

P_ATM = 1.0e5
A1, A2 = 0.013273229, 0.00376991118
V1 = A1 * 0.40
BETA = 1.0e9
BP = 33900.0
M = 9690.0
KS = 4.77e6
P_CR = 330.0e5 + P_ATM          # crack, absolute
DP_OV = 20.0e5                  # override to rated flow
Q_R = 1.0e-3                    # rated flow 60 L/min
TAU = 0.01


def load(t, f_end, t1, t2):
    f = 116.3e3 * min(t / 1.0, 1.0)
    if t > t1:
        f += (f_end - 116.3e3) * min((t - t1) / (t2 - t1), 1.0)
    return f


def run(f_end, t1, t2, t_stop=6.0, tau=TAU):
    def rhs(t, z):
        x, v, p, y, vout = z
        ystar = max(p - P_CR, 0.0) / DP_OV
        q = Q_R * (max(y, 0.0) if tau > 0 else ystar)
        dp = BETA / (V1 - A1 * x) * (A1 * v - q)
        acc = (load(t, f_end, t1, t2) - (A1 * p - A2 * P_ATM) - KS * x - BP * v) / M
        dy = (ystar - y) / tau if tau > 0 else 0.0
        return [v, acc, dp, dy, q]

    sol = solve_ivp(rhs, (0.0, t_stop), [0.0, 0.0, P_ATM, 0.0, 0.0], method="LSODA",
                    max_step=2e-4, rtol=1e-8, atol=[1e-10, 1e-9, 1.0, 1e-9, 1e-12],
                    dense_output=False)
    t, (x, v, p, y, vout) = sol.t, sol.y
    return {
        "p_max_bar_g": float((p.max() - P_ATM) / 1e5),
        "p_final_bar_g": float((p[-1] - P_ATM) / 1e5),
        "x_final_mm": float(x[-1] * 1e3),
        "vented_cm3": float(vout[-1] * 1e6),
        "slide_by_venting_mm": float(vout[-1] / A1 * 1e3),
    }


def hopsan_metrics(csv_path):
    rows = {}
    with open(csv_path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split(",")
            if len(parts) > 3:
                try:
                    rows[parts[0]] = np.array([float(s) for s in parts[3:]])
                except ValueError:
                    continue
    p = rows["CB#P1#Pressure"]
    q = rows["CB#P1#Flow"]
    t = rows["Time"]
    vent = -np.trapezoid(q, t)
    return {
        "p_max_bar_g": float((p.max() - P_ATM) / 1e5),
        "p_final_bar_g": float((p[-1] - P_ATM) / 1e5),
        "x_final_mm": float(rows["Mass#P1#Position"][-1] * 1e3),
        "vented_cm3": float(vent * 1e6),
    }


def main():
    out = {"A_slow_ramp_700kN_2s": run(700e3, 2.0, 4.0),
           "B_fast_ramp_700kN_5ms": run(700e3, 2.0, 2.005),
           "B_fast_tau_0": run(700e3, 2.0, 2.005, tau=0.0),
           "B_fast_tau_30ms": run(700e3, 2.0, 2.005, tau=0.03)}
    if len(sys.argv) > 2:
        out["hopsan_A"] = hopsan_metrics(sys.argv[2])
    if len(sys.argv) > 3:
        out["hopsan_B"] = hopsan_metrics(sys.argv[3])
    for key in ("A", "B"):
        h = out.get(f"hopsan_{key}")
        r = out["A_slow_ramp_700kN_2s" if key == "A" else "B_fast_ramp_700kN_5ms"]
        if h:
            out[f"rel_diff_{key}"] = {k: (r[k] - h[k]) / abs(h[k]) for k in h if abs(h[k]) > 0}
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
