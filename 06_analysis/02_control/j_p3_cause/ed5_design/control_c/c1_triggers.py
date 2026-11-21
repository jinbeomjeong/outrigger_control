"""How often the proposed triggers exist (record trajectories only, no judged values):
T0' = first read after the controller leaves CHECK; TR = first read after the first READY where
the leg's acting command goes from |u| <= u_hold to u < -u_hold. Uses the stored VBJ0 Dg-3 T4h
(P1~P4 plant, no 3) because VBK0 is that plant with 3 off."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1\VBJ0_t4h")
U_HOLD = 0.01 * 0.020924
LEGS = ["FL", "FR", "RL", "RR"]
files = sorted(T4H.glob("*.npz"))
stats = Counter()
tr_delay = []
check_end = []
end_after_ready = []
for f in files:
    with np.load(f, allow_pickle=False) as z:
        t, u, ph = z["t_s"], z["command_m_s"], z["phase"].astype(str)
    stats["runs"] += 1
    not_check = np.flatnonzero(ph != "check")
    if not_check.size:
        check_end.append(float(t[not_check[0]]))
    ready = np.flatnonzero(ph == "ready")
    if not ready.size:
        stats["no_ready"] += 1
        continue
    k0 = int(ready[0])
    end_after_ready.append(float(t[-1] - t[k0]))
    for leg in range(4):
        found = None
        for k in range(max(k0, 1), len(t)):
            if abs(u[k - 1, leg]) <= U_HOLD and u[k, leg] < -U_HOLD:
                found = k
                break
        stats[f"leg_{LEGS[leg]}_tr_{'yes' if found is not None else 'no'}"] += 1
        if found is not None:
            tr_delay.append(float(t[found] - t[k0]))
print(dict(stats))
print("first non-CHECK read time [s] min/median/max", np.min(check_end), np.median(check_end), np.max(check_end))
print("time after first READY to run end [s] p10/p50/p90", np.percentile(end_after_ready, [10, 50, 90]).round(1))
if tr_delay:
    print("TR delay after READY [s] p10/p50/p90", np.percentile(tr_delay, [10, 50, 90]).round(1), "n", len(tr_delay))
print("phases seen", sorted({p for f in files[:20] for p in np.load(f)["phase"].astype(str)}))
