"""H-S8-3 item 1: R_ub(s) row of s8 spec 10.2 table 1 with the implemented rule.

R_ub(s) = kappa (L0h_max + s') / (L0r_min + s_max - s'),  s' = min(s + ds, s_max - 1 mm)
kappa 1.10, L0h_max 0.08 m, L0r_min 0.02 m, ds 5 mm, s_max 0.70 m (P-S8-13 (1),
two_pressure._ratio_bound). Also prints the kappa = 1.0 row (the old table values).

Usage: python -I h_s8_3_rub_row.py
"""
from __future__ import annotations

S_GRID = (0.0, 0.1, 0.2, 0.3, 0.39, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.68, 0.6948)
S_MAX, GAP, DS = 0.70, 1.0e-3, 5.0e-3
L0H, L0R = 0.08, 0.02


def r_ub(s: float, kappa: float, gap: float) -> float:
    s1 = min(max(s + DS, 0.0), S_MAX - gap)
    return kappa * (L0H + s1) / (L0R + S_MAX - s1)


def main() -> None:
    for label, kappa, gap in (("kappa 1.0, s' <= s_max (old table)", 1.0, 0.0),
                              ("kappa 1.1, s' <= s_max (formula text)", 1.1, 0.0),
                              ("kappa 1.1, s' <= s_max - 1 mm (implemented)", 1.1, GAP)):
        vals = [r_ub(s, kappa, gap) for s in S_GRID]
        print(label)
        print(" | ".join(f"{v:.4g}" for v in vals))
    print("front 0.668 m:", round(r_ub(0.668, 1.1, GAP), 3), " 0.66 m:", round(r_ub(0.66, 1.1, GAP), 3),
          " 0.50 m:", round(r_ub(0.50, 1.1, GAP), 3))


if __name__ == "__main__":
    main()
