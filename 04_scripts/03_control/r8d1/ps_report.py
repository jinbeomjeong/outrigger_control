"""Summarise probe_scatter output: estimator spread (ratio to U63 C1 S_ii) and variant effects.

Input: 06_analysis/02_control/r8_10hz/d1/ps_all.json (spec rev. 31 144.1).
"""
import json
import sys
from collections import defaultdict

import numpy as np

NOM = (5.83e6, 5.83e6, 6.98e6, 6.98e6)
rows = json.load(open(sys.argv[1]))
base = [r for r in rows if r["case"]["variant"] == "base"]
for est in ("half", "full", "rt"):
    per_leg = defaultdict(list)
    means = []
    meds = []
    first_round = []
    for r in base:
        rr = []
        for p in r["probes"]:
            v = p[est]
            if p["grounded_stiff"] and np.isfinite(v):
                per_leg[p["leg"]].append(v / NOM[p["leg"]])
        # per round of 4 legs
        pr = r["probes"]
        for i in range(0, len(pr) - 3, 4):
            vals = [pr[i + j][est] / NOM[pr[i + j]["leg"]] for j in range(4)
                    if pr[i + j]["grounded_stiff"] and np.isfinite(pr[i + j][est])]
            if vals:
                means.append(np.mean(vals))
                meds.append(np.median(vals))
    print(f"[{est}] per-leg ratio min/median/max:")
    for leg in range(4):
        a = np.array(per_leg[leg])
        print(f"   leg {leg}: n {a.size} {a.min():.2f} / {np.median(a):.2f} / {a.max():.2f}  (abs {a.min()*NOM[leg]/1e6:.1f}-{a.max()*NOM[leg]/1e6:.1f} MN/m)")
    m = np.array(means); md = np.array(meds)
    print(f"   round mean ratio: min {m.min():.2f} p50 {np.median(m):.2f} max {m.max():.2f}; round median ratio max {md.max():.2f}")
mf = [p["mid_frac"] for r in base for p in r["probes"] if np.isfinite(p["mid_frac"])]
print("mid reading at fraction of first-move rod travel: %.2f-%.2f" % (min(mf), max(mf)))
print("rounds per run:", sorted(set(len(r["probes"]) // 4 for r in base)))
# variant effects
key = lambda r: (r["case"]["level"], r["case"]["roll"], r["case"]["pitch"], r["case"]["beta"], r["case"]["fs"])
by = defaultdict(dict)
for r in rows:
    by[key(r)][r["case"]["variant"]] = r
print("\nvariant  fmin_level(min)  fmin_after_lift(min)  t_ready(max/mean)  att_max  scale range  not-ready")
for v in ("base", "pre12", "knom"):
    rs = [by[k][v] for k in by]
    tr = [r["t_ready"] for r in rs if r["t_ready"] is not None]
    sc = [r["scale"] for r in rs if r["scale"] is not None]
    print(f"{v:6s} {min(r['fmin_level_kN'] for r in rs):8.2f} {min(r['fmin_lift_kN'] for r in rs):8.2f} "
          f"{max(tr):7.1f}/{np.mean(tr):5.1f} {max(r['att_max'] or 0 for r in rs):.4f} "
          f"{(min(sc) if sc else float('nan')):.2f}-{(max(sc) if sc else float('nan')):.2f} "
          f"{sum(r['t_ready'] is None for r in rs)}")
print("\nper case pre12 - base: d fmin_level [kN], d t_ready [s]")
d1 = [by[k]["pre12"]["fmin_level_kN"] - by[k]["base"]["fmin_level_kN"] for k in by]
d2 = [by[k]["pre12"]["t_ready"] - by[k]["base"]["t_ready"] for k in by if by[k]["pre12"]["t_ready"] and by[k]["base"]["t_ready"]]
print("  dF min %.2f max %.2f mean %.2f; dT min %.2f max %.2f mean %.2f" % (min(d1), max(d1), np.mean(d1), min(d2), max(d2), np.mean(d2)))
worst = sorted(by, key=lambda k: by[k]["base"]["fmin_level_kN"])[:5]
for k in worst:
    print("  ", k, {v: round(by[k][v]["fmin_level_kN"], 2) for v in by[k]})
