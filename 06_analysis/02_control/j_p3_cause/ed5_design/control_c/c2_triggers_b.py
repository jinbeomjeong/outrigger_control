"""Alternative TR anchors on the stored VBJ0 Dg-3 T4h (record trajectories only): the first read
of a retract carry start (|u_{k-1}| <= u_hold, u_k < -u_hold) after (a) the first LEVEL read,
(b) the first DONE read, (c) the first PROBE read; and the phase at which it falls."""
from collections import Counter
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\78fd5d2d\dg3_a1\VBJ0_t4h")
U_HOLD = 0.01 * 0.020924
files = sorted(T4H.glob("*.npz"))
for anchor in ("level", "done", "probe"):
    found = Counter()
    phase_at = Counter()
    delays = []
    for f in files:
        with np.load(f, allow_pickle=False) as z:
            t, u, ph = z["t_s"], z["command_m_s"], z["phase"].astype(str)
        idx = np.flatnonzero(ph == anchor)
        if not idx.size:
            found["no_anchor"] += 4
            continue
        k0 = max(int(idx[0]), 1)
        for leg in range(4):
            ks = [k for k in range(k0, len(t)) if abs(u[k - 1, leg]) <= U_HOLD and u[k, leg] < -U_HOLD]
            if ks:
                found["yes"] += 1
                phase_at[ph[ks[0]]] += 1
                delays.append(float(t[ks[0]] - t[k0]))
            else:
                found["no"] += 1
    d = np.array(delays) if delays else np.array([np.nan])
    print(anchor, dict(found), "phase at trigger", dict(phase_at),
          "delay p10/p50/p90", np.nanpercentile(d, [10, 50, 90]).round(2))
