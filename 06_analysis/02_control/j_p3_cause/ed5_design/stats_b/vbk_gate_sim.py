"""T-JR-12b on VBK(ga) vs VBK0 with injected rod-sensor faults: rule comparison.

Unit: pair = (L2 case, seed block j, injected leg, injection phase); one pair
per case per block (balanced rotation of leg x phase), 167 L2 cases.
Per-pair failure probability in case k:
    p_k = c * f * Z_k  (harmless divergence floor: commands change with prob c,
                        a changed pair fails with prob f * Z_k)
        + g            (L2 grade pass->fail floor, independent)
        + delta_k      (defect: D1 homogeneous delta; D2 5 % of cases get delta/0.05)
Z_k: homogeneous (Z = 1) or concentrated (10 % of cases Z = 10, rest 0; mean 1),
the concentrated form mimics stored L3 rows where all cross-seed READY losses sat
in 7 of 103 cases. Rule: pass iff total failures <= k.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

OUT = Path(sys.argv[1])
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
SEED = 20261114
N_CASE = 167
M_GRID = [1, 2, 3, 4, 6, 8]
K_GRID = [0, 1, 2, 3]
C_GRID = [0.3, 0.5, 0.8]
F_GRID = [0.001, 0.0035, 0.01]
G_GRID = [0.0, 0.0036]
D_GRID = [0.0, 0.0025, 0.005, 0.01, 0.02, 0.03]


def draw(rng, reps, m, c, f, g, delta, conc, dmodel):
    if conc:
        z = np.where(rng.random((reps, N_CASE)) < 0.10, 10.0, 0.0)
    else:
        z = np.ones((reps, N_CASE))
    if dmodel == "D1":
        dk = np.full((reps, N_CASE), delta)
    else:
        dk = np.where(rng.random((reps, N_CASE)) < 0.05, min(1.0, delta / 0.05), 0.0)
    p = np.clip(c * f * z + g + dk, 0, 1)
    return rng.binomial(m, p).sum(axis=1)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    for m in M_GRID:
        for c in C_GRID:
            for f in F_GRID:
                for g in G_GRID:
                    for conc in (False, True):
                        for delta in D_GRID:
                            for dm in ("D1", "D2"):
                                if delta == 0.0 and dm == "D2":
                                    continue
                                cnt = draw(rng, REPS, m, c, f, g, delta, conc, dm)
                                for k in K_GRID:
                                    pr = float((cnt <= k).mean())
                                    rows.append({"m": m, "N": m * N_CASE, "c": c, "f": f, "g": g,
                                                 "conc": conc, "delta": delta, "dmodel": dm, "k": k,
                                                 "p_pass": pr, "mcse": float(np.sqrt(pr * (1 - pr) / REPS))})
    # self checks: homogeneous, c f g = 0 -> binomial(N, delta) tail
    checks = {}
    for m, k, d in ((3, 0, 0.01), (3, 1, 0.01), (6, 2, 0.005)):
        sim = [r for r in rows if r["m"] == m and r["k"] == k and r["delta"] == d and r["dmodel"] == "D1"
               and not r["conc"] and r["g"] == 0.0 and r["f"] == 0.001 and r["c"] == 0.3]
        exact = float(stats.binom.cdf(k, m * N_CASE, 0.3 * 0.001 + d))
        checks[f"m{m}_k{k}_d{d}"] = {"sim": sim[0]["p_pass"], "mcse": sim[0]["mcse"], "exact": exact}
    out = {"reps": REPS, "seed": SEED, "n_case": N_CASE, "rows": rows, "checks": checks,
           "wall_s": time.time() - t0}
    OUT.write_text(json.dumps(out), encoding="utf-8")
    print("ok", round(out["wall_s"], 1))


if __name__ == "__main__":
    main()
