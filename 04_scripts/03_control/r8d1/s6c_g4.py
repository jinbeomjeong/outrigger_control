"""G4 settlement: RR true force, readings, command and timing for several cases."""
import json
import sys
from pathlib import Path

import numpy as np

batch = Path(sys.argv[1])
RR = 3
for case in sys.argv[2:]:
    rec = np.load(batch / case / "record" / "record.npz")
    r8 = np.load(batch / case / "r8_series.npz")
    pads = np.load(batch / case / "pads.npz")
    res = json.loads((batch / case / "result.json").read_text(encoding="utf-8"))
    t = rec["t"]
    ev = json.loads((batch / case / "controller_events.json").read_text(encoding="utf-8"))
    ready = np.where(r8["phase"] == "ready")[0]
    t_ready = t[ready[0]]
    t_set = t_ready + 5.0
    tp = pads["t"]
    F = pads["F_cyl_min_interval"][:, RR] if "F_cyl_min_interval" in pads.files else pads["F_cyl"][:, RR]
    sel = (tp >= t_set - 0.5) & (tp <= t_set + 8)
    i = np.argmin(np.where(sel, F, np.inf))
    print(f"== {case}: READY {t_ready:.2f} s, settle start {t_set:.2f} s, min RR {F[i]/1e3:.2f} kN at {tp[i]:.3f} s")
    print("   events:", [e for e in ev if "WARN" in e or "relevel" in e.lower() or "P5" in e or "R5" in e or "level" in e.lower()][:12])
    A = None
    w = np.where((t >= t_set - 0.3) & (t <= t_set + 4.0))[0]
    for k in w:
        print(f"   t={t[k]:7.2f} ph={r8['phase'][k]:7s} Ftrue={rec['F_cyl'][k,RR]/1e3:6.1f} p_h={rec['meas.head_pressure'][k,RR]/1e5:6.1f}bar "
              f"p_r={rec['meas.rod_pressure'][k,RR]/1e5:5.1f}bar u_iss={r8['issued_u'][k]*1e3} valve={np.round(r8['valve_u'][k,RR]*1e3,2)} "
              f"guard={bool(r8['guard_active'][k])} scale={r8['scale_used'][k]:.2f}")
