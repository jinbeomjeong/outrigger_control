"""Analytic (binomial) comparison of (N, k) rules for the VBK 12b gate.

Homogeneous per-pair failure; the simulation (vbk_gate_sim.py) shows case
concentration changes these by <= 2 %p at this scale. Floor = c * f (+ g).
"""
import json
import sys
from pathlib import Path

from scipy import optimize, stats

OUT = Path(sys.argv[1])
RULES = [(167, 0), (334, 0), (501, 0), (334, 1), (501, 1), (668, 1), (501, 2), (668, 2),
         (835, 2), (668, 3), (1002, 3), (1002, 4), (1336, 5)]
FLOORS = {"c0.3f0.1": 0.0003, "c0.5f0.35": 0.00175, "c0.8f0.35": 0.0028, "c0.5f1": 0.005, "c0.8f1": 0.008}
G = 0.0036
RUN_S = 38 * 60 / (3 * 135)  # s per run, P 4 workers (Dg-3 three bundles 38 min, main's figure)


def pass_p(n, k, p):
    return float(stats.binom.cdf(k, n, p))


def add80(n, k, floor):
    """Extra per-pair failure delta (on top of floor) with P(pass) = 0.2."""
    if pass_p(n, k, floor) <= 0.2:
        return 0.0
    return float(optimize.brentq(lambda d: pass_p(n, k, floor + d) - 0.2, 0.0, 0.5))


rows = []
for n, k in RULES:
    r = {"N": n, "k": k, "m": n / 167, "cost_min_2runs": 2 * n * RUN_S / 60,
         "mde80_no_floor": add80(n, k, 0.0),
         "upper95_if_k_seen": float(stats.beta.ppf(0.95, k + 1, n - k))}
    for name, fl in FLOORS.items():
        r[f"rej_{name}"] = 1 - pass_p(n, k, fl)
        r[f"rej_{name}_g"] = 1 - pass_p(n, k, fl + G)
        r[f"add80_{name}"] = add80(n, k, fl)
    rows.append(r)
OUT.write_text(json.dumps({"run_s": RUN_S, "g": G, "rows": rows}, indent=1), encoding="utf-8")
print("ok")
