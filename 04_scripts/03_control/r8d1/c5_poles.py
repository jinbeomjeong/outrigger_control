"""Closed-loop dominant modes of C2 R8-D1 (d = 1, T = 0.1 s ZOH, tau_v, negative feedback u = -K y,
exact lifted model r8d1_lin) for the C-5 oscillation-criterion check: frequency of the M_s peak and
decay (halving time) of the lightly damped closed-loop poles, guard off / guard active."""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r8d1_lin as R  # noqa: E402
import c2_linear as cl  # noqa: E402
import control as ct  # noqa: E402

A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)
out = []
for lv, b, mast, s in (("top", 1.6e9, "sup_lower", 1.3), ("top", 1.6e9, "sup_lower", 1.2),
                       ("top", 1.0e9, "rigid", 1.0), ("top", 1.6e9, "rigid", 1.2),
                       ("top", 0.69e9, "rigid", 1.0)):
    kw = dict(level=lv, support="pads", beta=b, mast=mast)
    if s != 1.0:
        kw["k_scale"] = (s,) * 4
    lp = cl.build_plant(cl.PlantCase(**kw))
    for guard in (-1, 0, 3):
        r = 1.2
        cfg = R.Cfg(d=1, tau_v=0.1, Ktw=0.5 / r, tau_tw=0.2, guard_leg=guard, Kg=0.15 / r, **A8)
        res, L = R.analyse(lp, cfg)
        p = ct.feedback(L, np.eye(4)).poles()
        sc = np.log(p[np.abs(p) > 1e-9].astype(complex)) / 0.1
        osc = [x for x in sc if x.imag > 1e-3]
        modes = sorted(({"f_Hz": x.imag / (2 * math.pi), "zeta": -x.real / abs(x),
                         "t_half_s": math.log(2) / -x.real if x.real < 0 else None} for x in osc),
                       key=lambda m: m["t_half_s"] or 1e9, reverse=True)
        worst = max(R.CH, key=lambda c: res[c]["Ms"])
        out.append({"plant": f"{lv}_b{b/1e9:g}_{mast}_s{s}", "guard_leg": guard,
                    "Ms": res[worst]["Ms"], "ch": worst, "w_Ms_rad_s": res[worst]["w_Ms"],
                    "rho": res["rho"],
                    "slow_osc_modes": [m for m in modes if m["f_Hz"] < 3.0][:6]})
for o in out:
    print(o["plant"], "guard", o["guard_leg"], f"Ms {o['Ms']:.3f} {o['ch']} w_Ms {o['w_Ms_rad_s']:.3f} rad/s "
          f"({o['w_Ms_rad_s']/2/math.pi:.3f} Hz) rho {o['rho']:.4f}")
    for m in o["slow_osc_modes"]:
        print(f"    f {m['f_Hz']:.3f} Hz zeta {m['zeta']:.3f} t_half {m['t_half_s'] and round(m['t_half_s'], 2)} s")
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
