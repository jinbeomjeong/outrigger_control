"""Ed. 8 S8-R final review, part 4: analytic re-checks of the numbers written in spec 5.3, 7.4, 7.5.

  - census stop forecast 1 - (1 - p)^n for n 450 / 740 (spec 5.3)
  - N-layer A/A stop rule: smallest n_AA with one-sided 95 % Clopper-Pearson upper <= 0.025 for x 0..3 (spec 7.4)
  - Jeffreys posterior-predictive k_N (spec 7.5) and MDE80 = smallest p with P(Bin(n, p) > k) >= 0.8,
    with n_AA = n_N (assumption used in stats_s8r), for n 200 / 300 and x_AA 0 / 1 / 2
  - E layer k_E = 1: MDE80 at n_E 16, 18, 21, 26, 28 and null size P(Bin(n, p0) > 1) for p0 0.001 / 0.002 / 0.005
All values are analytic (scipy), independent units.
Usage: python -I -B f4_checks.py <out_folder>
"""
import json
import sys
from pathlib import Path

from scipy import optimize, stats

OUT = Path(sys.argv[1])
res = {}
res["census_stop"] = {str(n): {str(p): round(1 - (1 - p) ** n, 4) for p in (0.0005, 0.001, 0.002, 0.005)}
                      for n in (450, 740)}


def cp_upper(x, n, a=0.05):
    return 1.0 if x >= n else float(stats.beta.ppf(1 - a, x + 1, n - x))


res["aa_cp_min_n"] = {}
for x in range(4):
    n = x + 1
    while cp_upper(x, n) > 0.025:
        n += 1
    res["aa_cp_min_n"][str(x)] = n


def k_pred(n, x, naa, alpha=0.025):
    d = stats.betabinom(n, x + 0.5, naa - x + 0.5)
    k = 0
    while d.sf(k) > alpha:
        k += 1
    return k


def mde(n, k, power=0.8):
    return float(optimize.brentq(lambda p: stats.binom.sf(k, n, p) - power, 1e-9, 0.999999))


res["N"] = {}
for n in (200, 300):
    for x in (0, 1, 2):
        k = k_pred(n, x, n)
        res["N"][f"n{n}_x{x}"] = {"k": k, "mde80": round(mde(n, k), 4)}
res["E"] = {}
for n in (16, 18, 21, 26, 28):
    res["E"][f"n{n}"] = {"mde80": round(mde(n, 1), 4),
                         "size": {str(p): round(float(stats.binom.sf(1, n, p)), 5) for p in (0.001, 0.002, 0.005)}}
(OUT / "f4_checks.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({"status": "ok"}))
