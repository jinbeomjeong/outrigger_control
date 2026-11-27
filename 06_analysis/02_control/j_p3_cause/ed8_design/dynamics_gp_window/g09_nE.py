"""G' window shift, part 9: stratum-E size n_E of G' under the stats slot structure (f3_sizes, reading I =
RE1bF only) with the per-phase E probabilities of g07 instead of "P_RE x m".

Slots per RE1bF E-candidate family (4 families: bottom front {level, ready} x {FL, FR}), all independent
Bernoulli as in f3 (no cluster correlation, same simplification):
  (a) phase source: 4 slots, phase uniform in O' = {0.0125, 0.0375, 0.0625, 0.0875}
  (b) depth source: 4 slots, phase uniform in O' + the 4 stored phases, shape uniform {25/0.05, 30/0.04}
  (c) F_s source: 3 slots (F_s 1, 3, 6 kN), phase uniform in the 8 phases
Cases: stats tables with m = 1 (check against f3: mean 26.4, P 0.0006), g07 nominal, g07 window-length
sensitivity (25/0.05 replaced by 25L<x>), (a) from the stats interval model or from the g07 base model.
Seed 8817 (own; not a G' or stats seed). 20,000 replications.
Usage: python -I -B g09_nE.py <out_folder>
"""
import json
import sys
from pathlib import Path

import numpy as np

out = Path(sys.argv[1])
g7 = json.loads((out / "g07_window_m.json").read_text(encoding="utf-8"))["conditions"]
PH = ["0.0", "0.0125", "0.025", "0.0375", "0.05", "0.0625", "0.075", "0.0875"]
NEW = [1, 3, 5, 7]
STATS = np.array([15 / 16, 0.5, 0.0, 0.0, 4 / 16, 1.0, 1.0, 1.0])


def tab(c):
    return np.array([g7[c]["P_by_phase"][p] for p in PH])


rng = np.random.default_rng(8817)
REPS = 20000


def draw(pa, pb_list, pc_list):
    nE = np.zeros(REPS, int)
    for r in range(REPS):
        c = 0
        for _fam in range(4):
            for _ in range(4):                        # (a)
                c += rng.random() < pa[NEW[rng.integers(4)]]
            for _ in range(4):                        # (b)
                pb = pb_list[rng.integers(len(pb_list))]
                c += rng.random() < pb[rng.integers(8)]
            for pc in pc_list:                        # (c)
                c += rng.random() < pc[rng.integers(8)]
        nE[r] = c
    return nE


cases = {
    "stats m=1 (check)": (STATS, [STATS], [STATS] * 3),
    "stats m=0.7 (check)": (STATS, [STATS * 0.7], [STATS * 0.7] * 3),
    "g07 nominal, (a) stats": (STATS, [tab("25/0.05"), tab("30/0.04")], [tab("Fs1"), tab("Fs3"), tab("Fs6")]),
    "g07 nominal, (a) model": (tab("base"), [tab("25/0.05"), tab("30/0.04")], [tab("Fs1"), tab("Fs3"), tab("Fs6")]),
    "L=0 (window translates), (a) model": (tab("base"), [tab("25L0"), tab("30/0.04")], [tab("Fs1"), tab("Fs3"), tab("Fs6")]),
    "L=-10 ms (window shrinks), (a) model": (tab("base"), [tab("25L-10"), tab("30/0.04")],
                                             [tab("Fs1"), tab("Fs3"), tab("Fs6")]),
    "L=+30 ms, (a) model": (tab("base"), [tab("25L30"), tab("30/0.04")], [tab("Fs1"), tab("Fs3"), tab("Fs6")]),
}
res = []
lines = ["n_E of G' stratum E (reading I, independent slots as f3): mean, 5-95 %, P(n_E < 16) +- MCSE"]
for name, (pa, pb, pc) in cases.items():
    nE = draw(pa, pb, pc)
    p = float((nE < 16).mean())
    se = float(np.sqrt(max(p * (1 - p), 1e-12) / REPS))
    exp_mean = 4 * (4 * pa[NEW].mean() + 4 * np.mean([b.mean() for b in pb]) + sum(c.mean() for c in pc))
    res.append({"case": name, "mean": float(nE.mean()), "expected_mean": float(exp_mean), "p05": int(np.percentile(nE, 5)),
                "p95": int(np.percentile(nE, 95)), "P_lt_16": p, "mcse": se})
    lines.append(f"{name:40s} mean {nE.mean():5.1f} (exact {exp_mean:5.1f}) 5-95 % {np.percentile(nE, 5):.0f}-"
                 f"{np.percentile(nE, 95):.0f}  P(n_E<16) {p:.4f} +- {se:.4f}")
(out / "g09_nE.json").write_text(json.dumps({"seed": 8817, "reps": REPS, "cases": res}, indent=1), encoding="utf-8")
(out / "g09_nE.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(json.dumps({"status": "ok"}))
