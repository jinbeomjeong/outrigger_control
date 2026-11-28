"""CP95 one-sided upper bounds for the A/A combinations and the one-period FAULT-delay bound.

Usage (dynamics-dev): python.exe -I -B cp_and_delay.py <output json>

CP upper (one-sided 95 %) = beta.ppf(0.95, x + 1, n - x). Delay bound: one extra 0.1 s period
of a command that the faulty reading can move by at most the increment limit 0.25 v_max
(U-R8-27); its stroke through a first-order valve is the command times T (area kept). Load
change = stroke x stiffness (bracket: twist stiffness from dynamics 5.28.6 d_c, oil column of
spec 323.5). Attitude = stroke / span (YAML attachment points).
"""

from __future__ import annotations

import json
import sys

from scipy.stats import beta


def cp_upper(x: int, n: int) -> float:
    return float(beta.ppf(0.95, x + 1, n - x)) if x < n else 1.0


def main() -> int:
    out = sys.argv[1]
    combos = {}
    for n in (310, 313):
        for x in (0, 1, 2, 3, 4, 8, 11):
            combos[f"x{x}_n{n}"] = round(cp_upper(x, n), 5)
    v_max = 20.924e-3
    period = 0.1
    inc = 0.25 * v_max
    k_twist = 72.8e3 / 8.2e-3      # rear static load / d_c (dynamics 5.28.6), N/m
    k_oil = 7e7                    # oil column per leg (spec 323.5), N/m
    track = 1.3238 * 2             # front FL-FR attachment y span, m
    wheelbase = 2.2938 + 2.556     # FL x - RL x, m
    strokes = {"inc_0p25vmax": inc * period, "full_vmax": v_max * period}
    delay = {}
    for name, s in strokes.items():
        delay[name] = {"stroke_mm": round(s * 1e3, 3),
                       "load_kN_twist": round(s * k_twist / 1e3, 2),
                       "load_kN_oil": round(s * k_oil / 1e3, 2),
                       "roll_deg": round(s / track * 57.29578, 4),
                       "pitch_deg": round(s / wheelbase * 57.29578, 4)}
    result = {"cp95_upper": combos, "delay_bound": delay,
              "inputs": {"v_max_m_s": v_max, "T_s": period, "k_twist_N_m": k_twist,
                         "k_oil_N_m": k_oil, "track_m": track, "wheelbase_m": wheelbase}}
    with open(out, "x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
