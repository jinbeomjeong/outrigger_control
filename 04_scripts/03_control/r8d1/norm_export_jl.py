"""Export the gain-normalisation check loops (C2, stiffened plant) for the independent Julia lift (r8d1_check.jl).

Spec rev. 31 142 D; result 06_analysis/02_control/r8_10hz/d1/norm_export.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r8d1_lin as R  # noqa: E402
import c2_linear as cl  # noqa: E402
import dyn_model as dm  # noqa: E402

A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)
cc = cl.nominal_controller_constants()
CASES = []
for s, r, g in ((1.2, 1.0, -1), (1.2, 1.0, 0), (1.2, 1.0, 1), (1.2, 1.0, 2), (1.2, 1.0, 3),
                (1.2, 1.2, 0), (1.2, 1.2, 1), (1.2, 1.2, 2), (1.2, 1.2, 3), (1.3, 1.3, -1)):
    case = cl.PlantCase(level="top", support="pads", beta=1.6e9, mast="sup_lower", k_scale=(s,) * 4)
    cfg = R.Cfg(d=1, tau_v=0.1, Ktw=0.5 / r, tau_tw=0.2, **A8)
    if g >= 0:
        cfg = R.Cfg(d=1, tau_v=0.1, Ktw=0.5 / r, tau_tw=0.2, guard_leg=g, Kg=0.15 / r, **A8)
    CASES.append((case, f"C2_s{s:g}_r{r:g}_G{g}", cfg))
out = []
for case, name, cfg in CASES:
    lp = cl.build_plant(case)
    res, _ = R.analyse(lp, cfg)
    out.append({"plant": case.tag(), "name": name, "A": lp.A.tolist(), "B": lp.B.tolist(), "C": lp.C.tolist(),
                "D": lp.D.tolist(), "i_pa": lp.idx("phi_acc") + 1, "i_ta": lp.idx("theta_acc") + 1,
                "i_clr": lp.idx("clr") + 1, "iP": [lp.idx(f"P_{nm}") + 1 for nm in dm.LEG_NAMES],
                "Amat": cc["A"].tolist(), "n": cc["n"].tolist(), "k_nom": cc["k_nom"],
                "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
                "python_Ms": {c: res[c]["Ms"] for c in R.CH}})
    print(name, {c: round(res[c]["Ms"], 4) for c in R.CH})
json.dump(out, open(sys.argv[1], "w"))
