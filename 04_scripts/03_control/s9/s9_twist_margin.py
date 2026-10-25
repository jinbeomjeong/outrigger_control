"""Twist-loop margin of R8 C2 with a soil-softened pad stiffness (spec rev. 57 283.5).

Discrete loop, 10 Hz (T 0.1 s), negative feedback u = -K e, broken at the twist command:
  L(z) = K r F(z) z^-1 P(z),  P(z) = ZOH{1 / (s (tau_v s + 1))},  F(z) = (1 - a) / (1 - a z^-1), a = exp(-T / tau_tw)
  K = Ktw = 0.5 1/s (R8 C2), tau_v 0.1 s (valve), tau_tw 0.2 s (n^T P low-pass), d = 1 (z^-1),
  r = k_eff / (k_nom scale): the loaded-branch pad stiffness ratio (scale >= 1, P-R8-2 bound; so soil lowers r).
Prints GM (abs, dB), PM (deg), crossover (rad/s), Ms for r in R_LIST; writes s9_twist_margin.json.
"""
import json
import sys
from pathlib import Path

import control as ct
import numpy as np

T, KTW, TAU_V, TAU_TW = 0.1, 0.5, 0.1, 0.2
R_LIST = [1.3, 1.0, 0.3, 0.1, 0.03, 0.01]
out = []
P = ct.sample_system(ct.tf([1.0], [TAU_V, 1.0, 0.0]), T, "zoh")
a = np.exp(-T / TAU_TW)
F = ct.tf([1 - a, 0.0], [1.0, -a], T)
Z1 = ct.tf([1.0], [1.0, 0.0], T)
for r in R_LIST:
    L = KTW * r * F * Z1 * P
    gm, pm, wpc, wgc = ct.margin(L)
    w = np.logspace(-5, np.log10(np.pi / T), 400000)
    Lw = L(np.exp(1j * w * T))
    S = 1 / (1 + Lw)
    # gain crossover on the grid (ct.margin falls back to 'frd' and misses it for this type-1 discrete loop)
    k = np.flatnonzero(np.diff(np.sign(np.abs(Lw) - 1.0)))
    if k.size:
        i = k[0]
        f = (1.0 - abs(Lw[i])) / (abs(Lw[i + 1]) - abs(Lw[i]))
        wgc = w[i] + f * (w[i + 1] - w[i])
        pm = 180.0 + np.degrees(np.angle(L(np.exp(1j * wgc * T))))
    ms = float(np.max(np.abs(S)))
    poles = ct.poles(ct.feedback(L, 1))
    out.append({"r": r, "GM": float(gm), "GM_dB": float(20 * np.log10(gm)), "PM_deg": float(pm),
                "w_pc_rad_s": float(wpc), "w_gc_rad_s": float(wgc), "delay_margin_s": float(np.radians(pm) / wgc),
                "Ms": ms, "max_abs_pole": float(np.max(np.abs(poles)))})
    print(out[-1])
Path(sys.argv[1]).write_text(json.dumps({"T": T, "Ktw": KTW, "tau_v": TAU_V, "tau_tw": TAU_TW, "rows": out},
                                        indent=1), encoding="utf-8")
