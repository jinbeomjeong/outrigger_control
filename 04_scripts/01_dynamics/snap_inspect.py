"""Inspect L1-R crawler snapshots: rod-chamber state and pad loads (read only)."""
import sys
from pathlib import Path

import numpy as np

STATES = Path(__file__).resolve().parents[2] / "07_results" / "states_L1R"
NAMES = ["top_roll5.5", "top_fdown3.5", "top_fup3.5", "top_rp05", "middle_rp05",
         "bottom_rp05", "top_fdown3.2", "top_roll4.4", "top_flat", "top_flat_RRpre"]
first = True
for n in NAMES:
    f = STATES / f"S6_crawler_{n}.npz"
    z = np.load(f, allow_pickle=False)
    if first:
        keys = sorted(z.files)
        print("N keys", len(keys))
        for k in keys:
            if any(s in k for s in ("rod_chamber", "actuator", "ground_bushing", "s_ref", "meta", "sha")):
                print("  ", k, z[k].shape, z[k].dtype)
        first = False
    first = False

    def g(k):
        k = "payload." + k
        return z[k] if k in z.files else None
    print("==", n)
    for k in ("rod_chamber.l1r_state", "rod_chamber.l1r_F_lock_N", "rod_chamber.l1r_delta_lock_m",
              "rod_chamber.l1r_delta_m", "rod_chamber.l1r_p_r0_Pa", "rod_chamber.l1r_F_cyl_lock_N",
              "rod_chamber.l1r_last_direction", "rod_chamber.l1r_Fx_prev_N",
              "rod_chamber.engine_last_normal_force_N", "rod_chamber.engine_last_cylinder_force_N",
              "rod_chamber.engine_last_head_pressure_Pa", "rod_chamber.engine_last_rod_pressure_Pa",
              "rod_chamber.engine_last_stroke_true_m", "rod_chamber.engine_last_mode",
              "rod_chamber.engine_mechanics_on", "actuator.s_ref_m",
              "ground_bushing.in_contact", "ground_bushing.normal_force_raw_N",
              "l1_actuator.u_applied_m_s"):
        v = g(k)
        print(f"  {k:45s}", None if v is None else np.array2string(np.asarray(v), precision=6))
sys.exit(0)
