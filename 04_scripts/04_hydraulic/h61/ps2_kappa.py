"""H-61-1: PS2 two instants (spec 299.3 / 302.5 inputs) with a state-dependent R_hi.

D = max{G(R_rate) dh, G(R_hi) dh - (n/h) C},  C = (R_lvl - R_hi) A_ann d,  L_hat = L - (h/n) D
R_hi = max(1, kappa_hi) * R_ub / 1.10,  kappa_hi = beta_r(p_r_hat) / beta_h(p_h - margin)
Inputs copied from s6_control_spec.md 299.3 (front leg FL, bar g).  Prints both instants.
Usage: python -I ps2_kappa.py
"""
import numpy as np

BAR = 1e5
PATM = 1.01325e5
A_P, A_R = 0.013273229, 0.00376991118
N, H, P5 = 3, 4, 16.91e3


def beta(p_g, k1, x_air):
    p_abs = max(p_g + PATM, 1e3)
    return 1.0 / (1.0 / (1e9 + k1 * (p_g - 100 * BAR)) + x_air * (PATM / p_abs) ** (1 / 1.4) / (1.4 * p_abs))


def g(r):
    return A_P + r * A_R  # N/Pa


cases = [  # t, R_ub, h_a, p_h, dh, p_r_hat, L [N], R_rate
    (127.8, 14.56, 97.28, 89.25, 4.73, 129.9, 56.50e3, 7.77),
    (141.5, 14.76, 95.70, 87.53, 4.20, 133.7, 52.78e3, 7.84),
]
for t, r_ub, h_a, p_h, dh, prh, lvl, r_rate in cases:
    d = (h_a - p_h) * BAR
    for k1 in (10.0, 5.0):
        for margin in (0.0, 10.0):
            kap = beta(prh * BAR, k1, 0.0) / beta((p_h - margin) * BAR, k1, 0.002)
            for lab, r_hi in (("R_ub/kappa", r_ub / 1.1), ("kappa_hi*R_ub/kappa", max(1.0, kap) * r_ub / 1.1)):
                c = (r_ub - r_hi) * A_R * d
                dd = max(g(r_rate) * dh * BAR, g(r_hi) * dh * BAR - N / H * c)
                lh = lvl - H / N * dd
                print(f"t {t}  K1 {k1:4.1f}  p_h margin {margin:4.1f} bar  kappa_hi {kap:.4f}  {lab:20s} "
                      f"R_hi {r_hi:6.3f}  C {c/1e3:5.2f} kN  L_hat {lh/1e3:6.2f} kN  margin to P5 {(lh-P5)/1e3:+5.2f} kN")
