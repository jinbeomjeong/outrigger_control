"""Rough false-failure exposure of 6.3.7 (2)(3) at the measured A/A floor (preliminary).

Assumptions (control-expert 2026-11-23, to be replaced by stats-design-expert):
  - only pairs whose VBK/VBK0 commands differ can differ in READY (identical commands give
    identical lines); their share is the dry c (20/158, run 606f8713 cdry_a1 dry_c.json);
  - a diverging pair differs in READY like two seeds of VBK0 (cross-seed A/A rate
    4/167, a conservative proxy), and half of those go the VBK-worse way (2)/(3);
  - N_opp = 327 (b1 163 + b2 164, VBK0 classification, aa_inspect.json);
  - failure counts are Poisson.
Inputs are counts only; no VBK READY/FAULT value is read. Writes ``aa_falsefail.json``.
"""
import json
from pathlib import Path

from scipy.stats import beta, poisson

HERE = Path(__file__).resolve().parent


def cp(k: int, n: int) -> tuple[float, float]:
    lo = beta.ppf(0.025, k, n - k + 1) if k else 0.0
    hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return float(lo), float(hi)


def main() -> None:
    n_opp = 327
    aa = (4, 167)
    c = (20, 158)
    out = {"aa_rate": aa[0] / aa[1], "aa_cp95": cp(*aa), "c": c[0] / c[1], "c_cp95": cp(*c),
           "tau_C_no_ready": {"k": 8, "n": 248, "cp95": cp(8, 248)},
           "tau_R_no_ready": {"k": 1, "n": 246, "cp95": cp(1, 246)},
           "grid": []}
    for c_val in (out["c"], out["c_cp95"][1]):
        for r in (out["aa_rate"], out["aa_cp95"][1]):
            lam = c_val * n_opp * r / 2
            out["grid"].append({"c": c_val, "aa_rate": r, "lambda": lam,
                                "P_ge1": 1 - poisson.cdf(0, lam),
                                "P_ge2": 1 - poisson.cdf(1, lam),
                                "P_ge3": 1 - poisson.cdf(2, lam)})
    (HERE / "aa_falsefail.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for g in out["grid"]:
        print({k: round(v, 3) for k, v in g.items()})


if __name__ == "__main__":
    main()
