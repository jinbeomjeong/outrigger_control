"""Open-loop vs closed-loop damping of the lightly damped modes (< 3 Hz), T = 0.1 s lifted model."""
import math
import sys

from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r8d1_lin as R  # noqa: E402
import c2_linear as cl  # noqa: E402
import control as ct  # noqa: E402

for mast, s in (("sup_lower", 1.3), ("sup_lower", 1.0), ("rigid", 1.3)):
    kw = dict(level="top", support="pads", beta=1.6e9, mast=mast)
    if s != 1.0:
        kw["k_scale"] = (s,) * 4
    lp = cl.build_plant(cl.PlantCase(**kw))
    cfg = R.Cfg(d=1, tau_v=0.1, Ktw=0.5 / 1.2, tau_tw=0.2, Kp=0.2, Ki=0.01, tau_f=0.8)
    R.set_T(0.1)
    G, _ = R.lifted_plant(lp, cfg)
    L = R.loop(lp, cfg)
    for name, sys_ in (("open G", G), ("closed", ct.feedback(L, np.eye(4)))):
        p = sys_.poles()
        p = p[np.abs(p) > 1e-9].astype(complex)
        sc = np.log(p) / 0.1
        m = sorted((x.imag / 2 / math.pi, -x.real / abs(x)) for x in sc if 0.5 < x.imag / 2 / math.pi < 3.0)
        print(mast, s, name, [(round(f, 3), round(z, 4)) for f, z in m])
