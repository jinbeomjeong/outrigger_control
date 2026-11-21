"""Export cases of the revision-1 models for the independent Julia check (check_jl2.jl)."""
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imuatt_lin3 as L3  # noqa: E402

L = L3.L
R = L3.R
cl, dm = R.cl, R.dm
CAT = {c.tag(): c for c in R.rcd.catalogue(full=True)}
JOBS = [("top_pads_b1.6_sup_lower", "A2_bessel1_Kp0.2_Kg0.15", -1),
        ("top_pads_b1_sup_lower", "A2_butter1_Kp0.2_Kg0.15", -1),
        ("top_pads_b1.6_sup_lower", "A2_butter1_Kp0.12_Kg0.1", 1),
        ("top_pads_b1.6_sup_lower", "A2_butter5_Kp0.15_Kg0.1", -1),
        ("top_pads_b1.6_sup_lower", "MA200_Kp0.2_Kg0.15", -1),
        ("top_pads_b1_sup_lower_k0.5-1-1-0.5", "B_c0.032_tf0.4", -1),
        ("top_pads_b1.6_sup_lower", "B_c0.032_tf0.4", 1)]
cc = cl.nominal_controller_constants()
out = []
for tag, vname, g in JOBS:
    lp = cl.build_plant(CAT[tag])
    kind, args, p_imu, over, kg = L3.V[vname]
    cfg = replace(L.BASE, p_imu=p_imu, **over)
    if g >= 0:
        cfg = replace(cfg, guard_leg=g, Kg=kg)
    res, _ = R.analyse(L3.build(lp, kind, args), cfg)
    sensor = ({"kind": "A2", "shape": args[0], "f_hz": args[1]} if kind == "A2"
              else {"kind": kind, "f_hz": args[0]})
    out.append({"plant": tag, "name": vname, "guard_leg": g, "sensor": sensor,
                "A": lp.A.tolist(), "B": lp.B.tolist(), "C": lp.C.tolist(), "D": lp.D.tolist(),
                "i_pa": lp.idx("phi_acc") + 1, "i_ta": lp.idx("theta_acc") + 1, "i_clr": lp.idx("clr") + 1,
                "i_phidot": 10, "i_thetadot": 11, "iP": [lp.idx(f"P_{nm}") + 1 for nm in dm.LEG_NAMES],
                "Amat": cc["A"].tolist(), "n": cc["n"].tolist(), "k_nom": cc["k_nom"],
                "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
                "python_Ms": {c: res[c]["Ms"] for c in R.CH}})
json.dump(out, open(HERE / "export2.json", "w"))
print("exported", len(out))
