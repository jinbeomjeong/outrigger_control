"""H-S8-1: slope / event table of the D2-eligible extension (CB-equivalent) and sensor-error
quantiles of the CB identity residual (read only; JSON from h_s8_1_cb_ranges.py).

Usage: python -I h_s8_1_slope_table.py <h_s8_1_cb_ranges.json>
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

BAR = 1e5
r = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = [x for x in r["C_rows"] if "RE1c" not in x["case"]]  # forced open-loop window (216.3)


def tag(case: str) -> str:
    for pat in ("flat", "fdown3.2", "fdown3.5", "fup3.2", "fup3.5", "roll4.4", "roll5.5",
                "rpBop", "rpB", "G4", "SS9", "SS", "RE1bF", "RE1bP", "HOLD120"):
        if pat in case:
            return pat
    return "other"


groups: dict = {}
for x in rows:
    key = (tag(x["case"]), x["side"])
    groups.setdefault(key, []).append(x)
print("tag       side  n  Fs_levels   Fp_min..Fp_max [kN]  p_r_max [bar g]  held over POC12 [bar]  case(max p_r)")
for (tg, side), xs in sorted(groups.items()):
    fs = sorted({x["Fs_level"] for x in xs})
    best = max(xs, key=lambda x: x["p_r_max_bar"])
    print(f"{tg:9s} {side:5s} {len(xs):2d} {','.join(f'{v:g}' for v in fs):10s} "
          f"{min(x['Fp_min_kN'] for x in xs):7.2f}..{max(x['Fp_max_kN'] for x in xs):7.2f} "
          f"{best['p_r_max_bar']:8.2f}   {max(x['held_poc12_bar'] for x in xs):7.2f}   {best['case']} {best['leg']}")

print("\nMC of the CB batch traces (recorded truth, normal grade), P(false D2 fallback)")
for m in r["D_mc"]:
    if m["cb"] and max(m["p_fallback"].values()) > 0:
        print(f"  {m['case']:22s} {m['leg']} {m['form']:14s} " +
              " ".join(f"{k}:{v:.4f}" for k, v in m["p_fallback"].items()))

# quantiles of e_r - psi e_h (normal grade, static + one noise sample) at representative points
rng = np.random.default_rng(20261025)
N = 1_000_000


def err(p):
    u = rng.uniform(-1, 1, (N, 7))
    off = (u[:, 0] * 1.2 + u[:, 1] * 0.4 + u[:, 6] * 0.4) * BAR
    x = p / (400 * BAR)
    par = (x - x * x - 1 / 6) / (1 / 6)
    e = off + u[:, 3] * 0.005 * p + u[:, 5] * 2.0 * BAR * par
    return np.clip(e, -4 * BAR, 4 * BAR) + rng.normal(0, 0.2 * BAR, N)


print("\nquantiles of e_r - psi e_h [bar] (psi 4), and two-sensor F_p form equivalent margin")
for name, ph, pr, k in (("rear loaded", 80e5, 15e5, 2.322), ("rear light", 55e5, 110e5, 2.322),
                        ("front light", 55e5, 110e5, 2.136)):
    d = (err(pr) - 4.0 * err(ph)) / BAR
    q = np.quantile(d, [0.5, 0.9, 0.99, 0.999, 0.9999])
    print(f"  {name:12s} p_h {ph/BAR:.0f} p_r {pr/BAR:.0f}: sd {d.std():.2f}, q50/90/99/99.9/99.99 "
          + " ".join(f"{v:.2f}" for v in q) + f", max {d.max():.2f}; P(>3) {np.mean(d>3):.4f} "
          f"P(>7) {np.mean(d>7):.5f} P(>10) {np.mean(d>10):.6f} P(>12) {np.mean(d>12):.7f}; "
          f"two-sensor m=3 -> identity {3*k:.2f}, m=5 -> {5*k:.2f}")
