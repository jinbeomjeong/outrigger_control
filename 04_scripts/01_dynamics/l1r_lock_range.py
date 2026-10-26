"""Light check: L1-R locked-leg stiffness and pressure ratio vs lock stroke.

L1-R fixes k_h, k_r at e_op (Q-D7). Real / L2b use k_h(s), k_r(s) at lock stroke s.
Nominal dead volumes L0h = L0r = 0.05 m (assumption, hydraulics nominal), beta 1.0 GPa.
"""
import json
import numpy as np
import yaml

P = r"C:\workspace\outrigger_control\02_params\rexome33.yaml"
with open(P, encoding="utf-8") as f:
    y = yaml.safe_load(f)

beta = float(y["actuator"]["oil_bulk_modulus_eff_Pa"])
smax = float(y["actuator"]["stroke_m"])
out = {"beta_Pa": beta, "stroke_m": smax}
L0h = L0r = 0.05
e_op = {"front": 0.4011, "rear": 0.3909}
k_out = {}
for side, leg in (("front", "FL"), ("rear", "RL")):
    cyl = y["legs"][leg]["cylinder"]
    Ap, Aa = float(cyl["head_area_m2"]), float(cyl["annulus_area_m2"])
    e = e_op[side]
    kh_op = beta * Ap / (L0h + e)
    kr_op = beta * Aa / (L0r + smax - e)
    # k_out from documented k_2 (head-only series) 2.591e7 / 1.950e7
    k2 = {"front": 2.591e7, "rear": 1.950e7}[side]
    ko = 1.0 / (1.0 / k2 - 1.0 / kh_op)
    k1_op = 1.0 / (1.0 / (kh_op + kr_op) + 1.0 / ko)
    R_op = (L0h + e) / (L0r + smax - e)
    rows = []
    for s in (0.30, 0.325, 0.35, 0.40, e, 0.45, 0.50, 0.55, 0.60, 0.65, 0.659, 0.66, 0.68):
        kh = beta * Ap / (L0h + s)
        kr = beta * Aa / (L0r + smax - s)
        k1 = 1.0 / (1.0 / (kh + kr) + 1.0 / ko)
        R = (L0h + s) / (L0r + smax - s)
        rows.append({
            "s_m": round(s, 4),
            "k1_N_m": k1, "k1_rel_to_L1R": k1 / k1_op - 1.0,
            "kh_plus_kr_rel": (kh + kr) / (kh_op + kr_op) - 1.0,
            "R": R, "R_over_Rplant": R / R_op,
            "G_kN_per_bar": (Ap + R * Aa) * 1e5 / 1e3,
        })
    out[side] = {"Ap": Ap, "Aann": Aa, "e_op": e, "kh_op": kh_op, "kr_op": kr_op,
                 "k_out": ko, "k1_op": k1_op, "R_plant": R_op,
                 "G_plant_kN_per_bar": (Ap + R_op * Aa) * 1e5 / 1e3, "rows": rows}

print(json.dumps(out, indent=1, default=float))
