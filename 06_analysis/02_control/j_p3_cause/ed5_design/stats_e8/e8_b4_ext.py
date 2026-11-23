"""Erratum 8 extension: pooled allowance k when the TRw witness block b4 (seed 43) is added.

b4 = 167 more pairs, all in the TRw phase (late, retract-carry trigger, like tau_R). Its VBK0
outcomes are not known at design time; null per pair (diverged): stall prob p_TRw, then
VBK-worse (+30 s) prob r2. p_TRw uses the tau_R line rate (1/166, point) or its CP upper
(1/246 pooled with c dry, 2.24 %), opportunity ~ 167 x (1 - p_TRw). b1+b2 part reuses the
F3 (c = 1) and F2u null of e8_rule_sim.py by importing its model functions.
Writes e8_b4_ext.json. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# isort: split
import e8_rule_sim as m  # noqa: E402

SEED = 20261124
N_SIM = 20_000


def b4_counts(rng, n_sim, c, p, r2, delta):
    n = 167
    reached0 = rng.random((n_sim, n)) >= p          # VBK0 outcome (unknown at design time)
    div = rng.random((n_sim, n)) < c
    stall = rng.random((n_sim, n)) < p
    b3 = div & reached0 & stall
    both = div & reached0 & ~stall
    b2 = both & (rng.random((n_sim, n)) < r2)
    if delta > 0:
        harm = reached0 & (rng.random((n_sim, n)) < delta)
        b3 |= harm
        b2 &= ~harm
    return (b3 | b2).sum(1), reached0.sum(1)


def main() -> int:
    rng = np.random.default_rng(SEED)
    pC, rhoC = m.mom_rho("tau_C")
    pR, _ = m.mom_rho("tau_R")
    base = m.build_pairs({"tau_C": pC, "tau_R": pR}, {"tau_C": rhoC, "tau_R": 0.5716654297399295})
    upper = m.build_pairs({"tau_C": m.cp_upper(8, 248), "tau_R": m.cp_upper(1, 246)},
                          {"tau_C": rhoC, "tau_R": 0.5716654297399295})
    c_up = m.cp_upper(*m.C_DRY)
    r2_pt = 0.5 * 1 / 162
    r2_up = 0.5 * m.cp_upper(1, 162)
    scen = {"F3_c1_point": (base, 1.0, 1.0, r2_pt, pR),
            "F2u_c_dry_up_prone1_upper": (upper, c_up, 1.0, r2_up, m.cp_upper(1, 246))}
    out = {"seed": SEED, "n_sim": N_SIM, "scenarios": {}}
    for name, (pairs, cg, cp_, r2, p4) in scen.items():
        res = {}
        for d in (0.0, 0.01, 0.02, 0.03, 0.04):
            o = m.simulate(pairs, cg, cp_, r2, d, (0, 1), 0.0, rng, N_SIM)
            b12 = o["B2"] + o["B3"]
            c4 = cg if name.startswith("F3") else c_up
            b4, opp4 = b4_counts(rng, N_SIM, c4, p4, r2, d)
            tot = b12 + b4
            res[f"delta_{d}"] = {f"k{k}": float((tot > k).mean()) for k in range(5, 15)}
            res[f"delta_{d}"]["mean_B"] = float(tot.mean())
            res[f"delta_{d}"]["mean_opp_b4"] = float(opp4.mean())
        out["scenarios"][name] = res
    (HERE / "e8_b4_ext.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
