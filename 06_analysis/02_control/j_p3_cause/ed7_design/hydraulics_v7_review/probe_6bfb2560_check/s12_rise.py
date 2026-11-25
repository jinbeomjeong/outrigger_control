"""Delta p_fill(x) of the P1 patch volume law (check_open_delay.fill_line_pressure_Pa, copied)
for the P7-7 slow state: review assumption vs the probe fill.

Usage: python -I -B s12_rise.py
"""
import math

A_H, A_ANN = 0.013273229, 0.00376991118
S_MAX, P_T, DELTA = 0.70, 2e5, 3e5
BETA, S_L, S_D = 0.69e9, 1.5, 1.5          # slow
V_LINE, BETA_HOSE, L0 = 285e-6, 0.5e9, 0.05


def fill_line_pressure_Pa(volume, tank, rod_start, yield_start, c_l, c_r, c_h):
    terms = ((tank, c_l), (rod_start, c_r), (yield_start, c_h))
    p = min(tank, rod_start)
    rem = max(volume, 0.0)
    for limit in sorted({s for s, _ in terms if s > p} | {math.inf}):
        slope = sum(c for s, c in terms if s <= p)
        if slope <= 0.0:
            p = limit
            continue
        seg = slope * (limit - p)
        if rem <= seg:
            return p + rem / slope
        rem -= seg
        p = limit
    return p


def rise_bar(x_m, p_r, s=0.408358, band=0.0, void=0.0):
    c_l = V_LINE * S_L / BETA_HOSE
    c_r = A_ANN * (L0 * S_D + S_MAX - s) / BETA
    k_h = BETA * A_H / (L0 * S_D + s)
    c_h = A_ANN ** 2 / k_h
    rod_start = DELTA + p_r
    p_b = fill_line_pressure_Pa(max(x_m - void, 0.0) * A_ANN, P_T, rod_start,
                                rod_start + band / A_ANN, c_l, c_r, c_h)
    return max(p_b - rod_start, 0.0) / 1e5


for label, x, pr in (("review: x 2.098 mm, p_r 5.07", 2.098e-3, 5.07e5),
                     ("probe peak x 2.0538, p_r 5.07", 2.0538e-3, 5.07e5),
                     ("probe peak x 2.0538, p_r 4.71 (fill start read)", 2.0538e-3, 4.71e5),
                     ("probe peak x 2.0538, p_r 4.51", 2.0538e-3, 4.51e5),
                     ("read x 2.0013, p_r 4.71", 2.0013e-3, 4.71e5)):
    print(f"  {label}: Delta p_fill {rise_bar(x, pr):.3f} bar")
d = (rise_bar(2.0538e-3 + 1e-5, 4.71e5) - rise_bar(2.0538e-3, 4.71e5)) / 1e-2
print(f"  d rise / d x = {d:.2f} bar per mm")
