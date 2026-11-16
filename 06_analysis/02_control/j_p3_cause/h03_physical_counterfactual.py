"""Physical (continuously trapped) RR rod pressure vs the plant p_tr and the monitor bound.

Rule (two pilot-checked chambers trapped, no flow, oil springs in parallel, body-fixed split):
  p_r(t) = p_r(t_a) + r (F(t_a) - F(t)) / A_ann,   r = k_r / (k_h + k_r)
  p_h(t) = (F(t) + p_r(t) A_ann) / A_h
with t_a = 48.6 s (last read of the long lock, plant and reading agree there), F = stored true
force of each run (closed loop of the plant, so an approximation for the physical machine).
Monitor: p_hat + delta_m = p_ret + 0.5 bar = 31.091 bar (report 2.3).
Locked model bound (4) estimate: M + R_ub (p_h,lock - p_h)^+, M = 13 bar, R_ub = 1.1 * 1.232,
p_h,lock = head reading at the first read after the 43.4 s lock.

Usage: python -I -B c01_physical_counterfactual.py <out_json>
"""
import json
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1"
           r"\h10_reuse_rerun_t4h")
A_ANN = np.pi / 4 * (0.110 ** 2 - 0.090 ** 2)
A_H = np.pi / 4 * 0.110 ** 2
K_H, K_R = 2.1554e7, 8.7485e6  # fitted from the plant trace (long lock 48.30..48.60 s)
R = K_R / (K_H + K_R)
BAR = 1e5
LEG = 3
MONITOR_BAR = 31.091
M_BAR, R_UB = 13.0, 1.1 * 1.232
READS = (48.6, 48.7, 48.8, 48.9, 49.0)
GAP_FROM_REPORT = {"VB": -9.806, "LS1": 0.486, "LS2": -9.643, "LS3": -26.334, "LS4": 0.500}


def main():
    out = {"r": R, "k_h": K_H, "k_r": K_R, "ratio_dpr_dph": -(K_R / A_ANN) / (K_H / A_H),
           "rows": {}}
    for s in ("VB", "LS1", "LS2", "LS3", "LS4"):
        z = np.load(T4H / f"R12_bottom-FL-Fs4-o0.0_{s}.npz", allow_pickle=True)
        t = z["t_s"]
        F = z["true_force_N"][:, LEG]
        Fmin = z["true_force_min_N"][:, LEG]
        ph = z["head_pressure_Pa"][:, LEG]
        pr = z["rod_pressure_Pa"][:, LEG]
        lk = z["locked"][:, LEG]
        ia = int(np.argmin(np.abs(t - 48.6)))
        # head at the start of the long lock (first read with locked after 43.3 s)
        il = int(np.flatnonzero((t > 43.3) & (lk > 0.5))[0])
        ph_lock = float(ph[il])
        rows = []
        for tr in READS:
            i = int(np.argmin(np.abs(t - tr)))
            p_phys = pr[ia] + R * (F[ia] - F[i]) / A_ANN
            p_phys_min = pr[ia] + R * (F[ia] - Fmin[i]) / A_ANN
            h_phys = (F[i] + p_phys * A_ANN) / A_H
            bound4 = M_BAR * BAR + R_UB * max(ph_lock - h_phys, 0.0)
            rows.append({"t": tr, "F_kN": float(F[i] / 1e3), "p_r_phys_bar": float(p_phys / BAR),
                         "p_r_phys_at_Fmin_bar": float(p_phys_min / BAR),
                         "p_h_phys_bar": float(h_phys / BAR),
                         "gap_phys_bar": float(MONITOR_BAR - p_phys / BAR),
                         "bound4_phys_bar": float(bound4 / BAR),
                         "bound4_minus_phys_bar": float((bound4 - p_phys) / BAR),
                         "optimism_phys_kN": float(max(p_phys / BAR - MONITOR_BAR, 0) * BAR
                                                   * A_ANN / 1e3)})
        out["rows"][s] = {"p_h_lock_start_bar": ph_lock / BAR, "t_lock_read": float(t[il]),
                          "gap_recorded_min_bar": GAP_FROM_REPORT[s], "reads": rows}
        print(s, f"p_h,lock {ph_lock / BAR:.1f} bar @ {t[il]:.2f}")
        for r in rows:
            print("   ", json.dumps({k: round(v, 3) for k, v in r.items()}))
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
