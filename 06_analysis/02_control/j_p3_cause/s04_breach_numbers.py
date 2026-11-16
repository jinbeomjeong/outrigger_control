"""Step 4: exact numbers of the R12 breach reads from the T4h records (no simulation).

For each R12 bottom-FL-Fs4 o0.0 record (VB, LS1..LS4) prints, for the violating leg RR and the
reads 48.4..49.6 s: acting command (output of the previous read, d = 1), head / rod reading,
true force, locked flag, and the monitor's pilot-check retract moving model
``p_back + (p_h - p_back) / ratio + p_crack`` (+ delta_m) from the stored two-pressure settings.
The rod reading is compared with that value: the hypothesis is that p_hat was set by the
retract branch at the one retracting read and not raised to the lock's model bound (4).

Also prints the lock events of the leg and the plant settings (closing delay / overlap ratio).
"""
import json
import sys
from pathlib import Path

import numpy as np

RK1 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
T4H = RK1 / "h10_reuse_rerun_t4h"
LEGS = ("FL", "FR", "RL", "RR")


def retract_model_Pa(head_Pa, s):
    back = s["fallback_head_back_Pa"]
    return back + (head_Pa - back) / s["fallback_pilot_ratio"] + s["fallback_cracking_Pa"]


def show(name, leg, t0, t1):
    z = np.load(T4H / name, allow_pickle=True)
    meta = json.loads(str(z["meta_json"]))
    s = meta["two_pressure_settings"]
    margin = s["extend_start_bound"]["margin_Pa"]
    t = z["t_s"]
    u = z["command_m_s"][:, leg]
    ph = z["head_pressure_Pa"][:, leg]
    pr = z["rod_pressure_Pa"][:, leg]
    f = z["true_force_N"][:, leg]
    lk = z["locked"][:, leg]
    print("=" * 100)
    print(name, "leg", LEGS[leg], "lock_closure", meta["hydraulic_options"]["lock_closure"],
          "flow eta_v", meta["flow_setting"]["eta_v"])
    print("  bound check:", {k: meta["extend_bound_check"][k][leg] for k in
                             ("breach_reads", "min_gap_bar", "min_gap_t_s", "first_breach_t_s")})
    print("  lock events of leg:", [tuple(r) for r in z["lock_events"] if int(r[1]) == leg
                                    and t0 - 10 <= r[0] <= t1])
    print("  t      out_u[mm/s]  act_u[mm/s]  p_h[bar]  p_r[bar]  F[kN]  locked  "
          "retract_model+dm[bar]  p_r - (model+dm)[bar]")
    for i in np.nonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9))[0]:
        act = u[i - 1] if i > 0 else np.nan
        model = (retract_model_Pa(ph[i], s) + margin) / 1e5
        print(f"  {t[i]:6.2f}  {u[i]*1e3:+10.5f}  {act*1e3:+10.5f}  {ph[i]/1e5:8.3f}"
              f"  {pr[i]/1e5:8.3f}  {f[i]/1e3:6.2f}  {int(lk[i])}  {model:8.3f}"
              f"  {pr[i]/1e5 - model:+8.3f}")


def main():
    t0, t1 = (48.3, 49.6) if len(sys.argv) < 3 else (float(sys.argv[1]), float(sys.argv[2]))
    for setting in ("VB", "LS1", "LS2", "LS3", "LS4"):
        show(f"R12_bottom-FL-Fs4-o0.0_{setting}.npz", 3, t0, t1)


if __name__ == "__main__":
    main()
