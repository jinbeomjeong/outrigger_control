"""D-S8-5 (2): residual (READY) rod SF -- static (SF 1.5, P = N_pad) and 350 bar lock (SF 1.0, P = P_lock).

Same beam model as dynamics_model.md 5.19 (direct_sf.py 'residual' rows): READY lateral L (mean from
READY + 1 s to the end of the run) at e = s_motor. Reads ds85_h4_sf.json for the READY values.
Usage: python -I ds85_residual_lock.py <ds85_h4_sf.json> <case dir> [...]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\04_scripts\00_cad")
import leg_rod_lateral_check as lr  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
p = lr.load_params()
geo = lr.leg_geometry(p)
g0 = float(p["meta"]["gravity_m_s2"])
W_rod = np.array([float(p["legs"][n]["moving_part"]["mass_kg"]) * g0 for n in LEGS])
Npad = lr.static_cylinder_forces_kn(p) + W_rod
SY = lr.ASSUMPTIONS["rod_yield_Pa"]
SF_REQ = lr.ASSUMPTIONS["required_yield_safety_factor"]
rep = json.load(open(sys.argv[1], encoding="utf-8"))
by_case = {c["case"]: c for c in rep["cases"]}
for d in sys.argv[2:]:
    name = os.path.basename(d)
    c = by_case[name]
    pads = np.load(os.path.join(d, "pads.npz"))
    t = pads["t"]
    m = t >= c["t_ready"] + 1.0
    print("==", name)
    for j, g in enumerate(LEGS):
        L = c["legs"][g]["L_ready_kN"] * 1e3
        e = float(pads["s_motor"][m, j].mean())
        row = [f"{g}: L_res {L / 1e3:.2f} kN e {e:.4f} m"]
        for mat in SY:
            fa_s = lr.allowable_lateral(geo[g], p, round(e, 4), round(Npad[j], -2), "swivel", SY[mat], SF_REQ)
            fa_l = lr.allowable_lateral(geo[g], p, round(e, 4), round(geo[g]["P_lock_N"], -2), "swivel", SY[mat], 1.0)
            row.append(f"[{mat}] static {SF_REQ * fa_s / L:.3f} lock {1.0 * fa_l / L:.3f}")
        print("  " + " | ".join(row))
