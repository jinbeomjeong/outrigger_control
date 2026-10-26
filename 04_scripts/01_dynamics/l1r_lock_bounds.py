"""Stroke bands where fixed-e_op L1-R matches k(s): k1 within 5/10 %, R within 10/30 %.
Also L0 sensitivity of k1 band (L0h = L0r in {0.02, 0.05, 0.1} m), k_out fixed from nominal.
"""
import numpy as np

beta, smax = 1.0e9, 0.70
legs = {"front": (0.013273229, 0.00376991118, 0.4011, 216946308.9),
        "rear": (0.00950331778, 0.00314159265, 0.3909, 204594048.1)}
s = np.linspace(0.25, 0.69, 44001)


def band(mask):
    idx = np.where(mask)[0]
    return (round(float(s[idx[0]]), 4), round(float(s[idx[-1]]), 4)) if idx.size else None


for side, (Ap, Aa, e, ko) in legs.items():
    for L0 in (0.02, 0.05, 0.10):
        def k1(x):
            kh = beta * Ap / (L0 + x)
            kr = beta * Aa / (L0 + smax - x)
            return 1.0 / (1.0 / (kh + kr) + 1.0 / ko)
        # L1-R plant uses nominal L0 0.05 at e_op
        kh0 = beta * Ap / (0.05 + e); kr0 = beta * Aa / (0.05 + smax - e)
        k1p = 1.0 / (1.0 / (kh0 + kr0) + 1.0 / ko)
        rel = k1(s) / k1p - 1.0
        R = (L0 + s) / (L0 + smax - s); Rp = (0.05 + e) / (0.05 + smax - e)
        rr = R / Rp - 1.0
        sel = (s >= 0.325) & (s <= 0.66)
        print(side, "L0", L0,
              "k1 |rel|<=5%", band(np.abs(rel) <= 0.05),
              "<=10%", band(np.abs(rel) <= 0.10),
              "k1 rel range in 0.325-0.66", round(float(rel[sel].min()), 4), round(float(rel[sel].max()), 4),
              "R within 10%", band(np.abs(rr) <= 0.10),
              "R/Rp range", round(float((R / Rp)[sel].min()), 3), round(float((R / Rp)[sel].max()), 3))
