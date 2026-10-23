"""Export raw plant data (continuous A, B, C, D, output indices, controller constants) and configuration parameters
for an independent Julia construction of the lifted loop (r8d1_check.jl). Python channel M_s from r8d1_lin."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import numpy as np
import r8d1_lin as R
import c2_linear as cl
import dyn_model as dm

CAT = {c.tag(): c for c in R.rcd.catalogue(full=True)}
A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)
CASES = [
    ("top_pads_b1.6_sup_lower", "C1_tv0.1", R.Cfg(d=1, tau_v=0.1, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9)),
    ("top_pads_b1.6_sup_lower", "C1_tv0.1_G0", R.Cfg(d=1, tau_v=0.1, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9, guard_leg=0, Kg=0.25)),
    ("top_pads_b1.6_sup_lower", "C2_tv0.1", R.Cfg(d=1, tau_v=0.1, Ktw=0.5, tau_tw=0.2, **A8)),
    ("top_pads_b1.6_sup_lower", "A8_tv0.1", R.Cfg(d=1, tau_v=0.1, Ktw=1.0, **A8)),
    ("top_pads_b1.6_sup_lower", "A8_tv0.1_G0", R.Cfg(d=1, tau_v=0.1, Ktw=1.0, guard_leg=0, Kg=1.0, **A8)),
    ("top_pads_b1_sup_lower_k0.5-1-1-0.5", "C1_tv0.15", R.Cfg(d=1, tau_v=0.15, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9)),
    ("top_pads_b1.6_sup_upper", "G7L_tv0.1", R.Cfg(d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0, m_att=9)),
    ("middle_pads_b1.6_sup_upper", "G7_d1_tv0", R.Cfg(d=1, tau_v=0.0, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0)),
    ("top_pads_b1.6_sup_upper", "T0.04_G7_tv0.1", R.Cfg(T=0.04, N=4, d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0)),
]
cc = cl.nominal_controller_constants()
out = []
for tag, name, cfg in CASES:
    lp = cl.build_plant(CAT[tag])
    r, _ = R.analyse(lp, cfg)
    out.append({"plant": tag, "name": name, "A": lp.A.tolist(), "B": lp.B.tolist(), "C": lp.C.tolist(), "D": lp.D.tolist(),
                "i_pa": lp.idx("phi_acc") + 1, "i_ta": lp.idx("theta_acc") + 1, "i_clr": lp.idx("clr") + 1,
                "iP": [lp.idx(f"P_{nm}") + 1 for nm in dm.LEG_NAMES],
                "Amat": cc["A"].tolist(), "n": cc["n"].tolist(), "k_nom": cc["k_nom"],
                "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
                "python_Ms": {c: r[c]["Ms"] for c in R.CH}})
json.dump(out, open("r8d1_export.json", "w"))
print("exported", len(out))
