"""Stroke s_motor [mm] and pad sinkage at the rear / front first contact (swivel events) per run, to see
whether the shorter FB front-rear contact gap comes from a later rear contact or an earlier front contact.
argv: <openloop_fb_compare.json> (run paths are re-listed here)."""
import json
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
FB = R / "batch_V5-OPENLOOP-FB_20261108_183849"
RUNS = {"V0": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
        "prop": R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop",
        "V0_FB": FB / "P3a_J1_B_V0_FB", "VB_FB": FB / "P3a_J1_B_VB_FB"}
for n, p in RUNS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t, sm = z["t_s"], z["s_motor_m"]
    th = z["roll_pitch_deg"][:, 1]
    ev = res["swivel"]["events"]
    tc = [min(e[0] for e in ev if e[1] == i) for i in range(4)]
    kr, kf = int(np.searchsorted(t, tc[2])), int(np.searchsorted(t, tc[0]))
    print(f"{n:6s} rear t {tc[2]:.4f} s_rear {sm[kr, 2] * 1e3:.3f} s_front {sm[kr, 0] * 1e3:.3f} pitch {th[kr]:.4f} | "
          f"front t {tc[0]:.4f} s_front {sm[kf, 0] * 1e3:.3f} s_rear {sm[kf, 2] * 1e3:.3f} pitch {th[kf]:.4f} "
          f"dpitch {th[kf] - th[kr]:.4f}")
