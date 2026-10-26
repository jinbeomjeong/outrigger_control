"""Knee load dF_knee(s) = (p_r0 - p_floor) * (A_ann + A_p / R(s)), after-extend lock p_r0 2 bar g,
p_floor 0.1 bar abs = -0.913 bar g. Same as (p_r0-p_floor) A_ann (k_h+k_r)/k_r (5.12.4)."""
dp = (2.0 + 0.913) * 1e5
smax, L0 = 0.70, 0.05
for side, Ap, Aa, e in (("front", 0.013273229, 0.00376991118, 0.4011),
                        ("rear", 0.00950331778, 0.00314159265, 0.3909)):
    out = []
    for s in (0.325, 0.35, e, 0.5, 0.6, 0.66):
        R = (L0 + s) / (L0 + smax - s)
        out.append((round(s, 4), round(dp * (Aa + Ap / R) / 1e3, 3)))
    print(side, out)
