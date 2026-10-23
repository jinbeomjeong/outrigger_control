"""Rod-side values at the static leg loads of the current YAML (02_params/rexome33.yaml).

Retract-lock pilot threshold p_r0, head-only bias, knee / F_fl, lift-off deflection and lift-off
readings per leg (rod_side_pressure.md 14.7 (5)). Gauge pressures. Reads the YAML (read only).
Run: conda run -n hydraulics-dev python -I rod_side_static_update.py [--yaml PATH] [--level top]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import yaml

G = 9.80665
FLOOR_G = 0.1e5 - 1.01325e5
PSI, P_CR, P_BA, P_R0_EXT = 3.5, 3e5, 5e5, 2e5
BETA, L0, S_MAX = 1.0e9, 0.05, 0.70
GEOM = {"FL": (0.130, 0.110, 0.4011, 2.166e8), "FR": (0.130, 0.110, 0.4011, 2.166e8),
        "RL": (0.110, 0.090, 0.3909, 2.051e8), "RR": (0.110, 0.090, 0.3909, 2.051e8)}
OLD = {"FL": 118.25e3, "FR": 118.25e3, "RL": 72.8e3, "RR": 72.8e3}  # values used in 12.2 / 14.4
M_ROD = {"FL": 106.783666, "FR": 106.783666, "RL": 73.1629937, "RR": 73.1629937}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", type=Path,
                    default=Path(__file__).resolve().parents[2] / "02_params" / "rexome33.yaml")
    ap.add_argument("--level", default="top")
    a = ap.parse_args()
    y = yaml.safe_load(a.yaml.read_text(encoding="utf-8"))
    loads = None
    stack = [y]
    while stack:  # find auger_levels.<level>.static_leg_loads_N anywhere in the tree
        d = stack.pop()
        if isinstance(d, dict):
            if "auger_levels" in d and a.level in d["auger_levels"]:
                loads = d["auger_levels"][a.level]["static_leg_loads_N"]
                break
            stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
        elif isinstance(d, list):
            stack.extend(v for v in d if isinstance(v, (dict, list)))
    print("static_leg_loads_N", a.level, loads)
    for leg, (b, dr, e, k_out) in GEOM.items():
        F = float(loads[leg])
        a_p = math.pi / 4 * b * b
        a_ann = math.pi / 4 * (b * b - dr * dr)
        k_h = BETA * a_p / (L0 + e)
        k_r = BETA * a_ann / (S_MAX - e + L0)
        r = k_r / (k_h + k_r)
        kn2 = 1 / (1 / (k_h + k_r) + 1 / k_out)
        phi = a_p / a_ann

        def thr(f):
            p_h = max(P_BA, (f / a_ann + P_CR + P_BA * (1 - 1 / PSI)) / (phi - 1 / PSI))
            return (p_h * a_p - f) / a_ann

        p0, po, w = thr(F), thr(OLD[leg]), M_ROD[leg] * G
        lift_ext = P_R0_EXT + r * (F + w) / a_ann
        lift_ret = p0 + r * (F + w) / a_ann
        print(f"{leg}: F {F/1e3:.3f} kN | p_r0_RET {p0/1e5:.3f} bar (was {po/1e5:.3f} at {OLD[leg]/1e3:.2f} kN,"
              f" d {(p0-po)/1e5:+.3f}) | bias RET {p0*a_ann/1e3:.3f} kN, EXT {P_R0_EXT*a_ann/1e3:.3f} kN"
              f" | p_h lock EXT {(F+P_R0_EXT*a_ann)/a_p/1e5:.2f} RET {(F+p0*a_ann)/a_p/1e5:.2f} bar"
              f" | knee EXT {(P_R0_EXT-FLOOR_G)*a_ann/r/1e3:.3f} RET {(p0-FLOOR_G)*a_ann/r/1e3:.3f} kN"
              f" | F_fl EXT {(F+(P_R0_EXT-FLOOR_G)*a_ann/r)/1e3:.3f} RET {(F+(p0-FLOOR_G)*a_ann/r)/1e3:.3f} kN"
              f" | lift d {-(F+w)/kn2*1e3:.4f} mm, p_r EXT {lift_ext/1e5:.2f} RET {lift_ret/1e5:.2f} bar,"
              f" head-only EXT {(-w+lift_ext*a_ann)/1e3:.2f} RET {(-w+lift_ret*a_ann)/1e3:.2f} kN")


if __name__ == "__main__":
    main()
