"""Export raw continuous plants + sensor / controller settings for the independent Julia check
(imuatt_check.jl), with the Python channel M_s of imuatt_lin (sensor augmentation done again in Julia)."""
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imuatt_lin as L  # noqa: E402
import imuatt_lin2 as L2  # noqa: E402

R = L.R
cl = R.cl
dm = R.dm
CAT = {c.tag(): c for c in R.rcd.catalogue(full=True)}
PLANTS = ("top_pads_b1.6_sup_lower", "top_pads_b1_sup_lower_k0.5-1-1-0.5", "bottom_pads_b1.6_sup_upper")
VARS = ("S0", "S0_d20", "A_f1.0", "A_f0.5", "B_c0.05", "B_c0.05_tf0.4", "B_c0.1_tf0.4")
VARS2 = ("A_f0.5_Kp0.12_Kg0.1", "A_f1.0_Kp0.12_Kg0.1")
GUARD = (("top_pads_b1.6_sup_lower", "B_c0.05_tf0.4", 1), ("top_pads_b1.6_sup_lower", "S0", 1),
         ("top_pads_b1.6_sup_lower", "A_f0.5_Kp0.12_Kg0.1", 1))


def spec(vname):
    if vname in L.VARIANTS:
        kind, par, p_imu, tau_f, *g = L.VARIANTS[vname]
        over = {"tau_f": tau_f}
        if g:
            over.update(Kp=g[0], Ki=g[1])
        return kind, par, p_imu, over, L.KG
    kind, par, p_imu, over, kg = L2.VARIANTS[vname]
    return kind, par, p_imu, dict(over), kg


cc = cl.nominal_controller_constants()
out = []
jobs = [(p, v, -1) for p in PLANTS for v in VARS + VARS2] + list(GUARD)
for tag, vname, g in jobs:
    lp = cl.build_plant(CAT[tag])
    kind, par, p_imu, over, kg = spec(vname)
    cfg = replace(L.BASE, p_imu=p_imu, **over)
    if g >= 0:
        cfg = replace(cfg, guard_leg=g, Kg=kg)
    res, _ = R.analyse(L.sensor_plant(lp, kind, par), cfg)
    out.append({"plant": tag, "name": vname, "guard_leg": g, "sensor": {"kind": kind, "f_hz": par},
                "A": lp.A.tolist(), "B": lp.B.tolist(), "C": lp.C.tolist(), "D": lp.D.tolist(),
                "i_pa": lp.idx("phi_acc") + 1, "i_ta": lp.idx("theta_acc") + 1, "i_clr": lp.idx("clr") + 1,
                "i_phidot": 6 + 3 + 1, "i_thetadot": 6 + 4 + 1,
                "iP": [lp.idx(f"P_{nm}") + 1 for nm in dm.LEG_NAMES],
                "Amat": cc["A"].tolist(), "n": cc["n"].tolist(), "k_nom": cc["k_nom"],
                "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
                "python_Ms": {c: res[c]["Ms"] for c in R.CH}})
json.dump(out, open(HERE / "imuatt_export.json", "w"))
print("exported", len(out))
