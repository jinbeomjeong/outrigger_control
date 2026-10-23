"""V11b creep under law C: reference index = first saturated flag vs first reading >= limit.

usage: v11b_creep_ref.py [batch_dir] [verify_S6_L1_infra.json]   (defaults: batch_20261021_194136 and its verify JSON)
rev. 30: force limits and v_max are read per case from the run metadata (model.force_limits_N, model.max_speed_m_s),
so per-leg REXOME35 limits (front 278.7 / 79.2 kN, rear 199.6 / 66.0 kN) are used for new batches; the old batch
metadata holds 218124.705 / 18555.0316 N and 0.0226666667 m/s (the previous literals were 218124.7 / 18555.0, 0.68/30).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
B = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "07_results/S6/batch_20261021_194136"
VJ = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "06_analysis/01_chrono/16_S6/verify_S6_L1_infra.json"
V = json.loads(VJ.read_text(encoding="utf-8"))
for case in ("v11b_FL_dt2e-4", "v11b_RL_dt2e-4", "v11b_FL_dt1e-5", "v11b_RL_dt1e-5"):
    z = np.load(B / case / "series.npz")
    print(case, sorted(z.files)[:12])
    t, F, s, sat, ua = z["t"], z["F_cyl"], z["s_motor"], z["saturated"].astype(bool), z["u_applied"]
    m = V["v11b"][case]["model"]
    F_EXT, F_RET = (float(x) for x in m["force_limits_N"])
    VMAX = float(m["max_speed_m_s"])
    PH = {"extend": (0.1, 3.0, 1.0, F_EXT), "retract": (3.0, 5.5, -1.0, F_RET)}
    k, c = m["spring"]["k_N_m"], m["spring"]["c_N_s_m"]
    ref = c * VMAX / k
    dt = m["dt_s"]
    for nm, (t0, t1, sg, lim) in PH.items():
        idx = np.flatnonzero((t > t0) & (t <= t1) & (sg * ua >= 0))
        idx = idx[t[idx] > t[idx[0]] + 0.05]
        jf = idx[sat[idx]][0]
        jr = idx[(sg * F[idx]) >= lim][0]
        for lab, j in (("flag", jf), ("reading", jr)):
            seg = idx[idx >= j]
            pos = s[seg] * sg
            cr = pos.max() - pos[0]
            print(f"  {nm:7s} {lab:7s} t {t[j]:.5f} creep {cr*1e6:7.2f} um  /ref {cr/ref:.3f}  ref {ref*1e6:.2f} um"
                  f"  vdt {VMAX*dt*1e6:.2f} um  step offset {(jf-jr)}")
