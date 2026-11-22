"""READY ICC and n_eff of U-3 on control's map r1 (resample_unit, 284) from 436.8 READY records.

Also: per-study unit counts, size histogram, units with all rows READY-missing, a check that every
g8 'ref|none' row joins a perturbed base unit, and unit-weighted R-1 bootstrap coverage
(gamma unit effect + normal row noise at the estimated ICC, actual unit sizes; median and P90 of
unit means) at the bundle layer. Seed 20261114.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 20261114
rng = np.random.default_rng(SEED)
V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5paper_imua_stats")
LAS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\v5_rerun\las_k1")
rows = list(csv.DictReader((V / "u3_cluster_map_r1.csv").open(encoding="utf-8")))
umap = {(r["study"], r["key"]): r["resample_unit"] for r in rows}
cmap = {(r["study"], r["key"]): r["cluster"] for r in rows}


def icc(groups):
    g = [np.asarray(x, float) for x in groups if len(x)]
    k = len(g)
    n = np.array([len(x) for x in g])
    N = n.sum()
    allv = np.concatenate(g)
    gm = allv.mean()
    ssb = sum(len(x) * (x.mean() - gm) ** 2 for x in g)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in g)
    msb, msw = ssb / (k - 1), ssw / (N - k)
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    return float((msb - msw) / (msb + (n0 - 1) * msw)), int(k), int(N)


out: dict = {"seed": SEED, "rows": len(rows)}
for col, mp in (("cluster", cmap), ("resample_unit", umap)):
    sizes = defaultdict(int)
    per_study = defaultdict(set)
    for (st, key), u in mp.items():
        sizes[u] += 1
        per_study[st].add(u)
    m = np.array(list(sizes.values()), float)
    N = m.sum()
    mw = float((m ** 2).sum() / N)
    rec = {"units": len(m), "max": int(m.max()), "kish_units": float(N ** 2 / (m ** 2).sum()), "m_weighted": mw,
           "per_study_units": {k: len(v) for k, v in per_study.items()}}
    for setting in ("V0", "VB"):
        g = defaultdict(list)
        missing = 0
        for f in sorted(LAS.glob(f"u3_*_{setting}.json")):
            st = f.stem[3:].rsplit("_", 1)[0]
            obj = json.loads(f.read_text(encoding="utf-8"))
            for r in obj.get("records") or obj.get("results") or []:
                t = r.get("t_ready_s")
                if isinstance(t, (int, float)) and not isinstance(t, bool):
                    g[mp[(st, r.get("id") or r.get("key"))]].append(t)
                else:
                    missing += 1
        rho, k, n_obs = icc(list(g.values()))
        rec[setting] = {"icc_ready": rho, "units_with_ready": k, "rows_with_ready": n_obs, "rows_ready_missing": missing,
                        "deff": 1 + (mw - 1) * rho, "n_eff": float(N / (1 + (mw - 1) * rho))}
    rec["n_eff_by_icc"] = {f"{r:g}": float(N / (1 + (mw - 1) * r)) for r in (0.90, 0.92, 0.93, 0.946)}
    out[col] = rec

# g8 ref rows: does each ref row share its unit with perturbed rows?
g8_units = defaultdict(list)
for r in rows:
    if r["study"] == "g8":
        g8_units[r["resample_unit"]].append(r["key"])
ref_alone = [u for u, ks in g8_units.items() if all("|ref|" in k for k in ks)]
out["g8_units"] = {"n": len(g8_units), "sizes": sorted(len(v) for v in g8_units.values()), "ref_only_units": ref_alone}

# unit-weighted coverage at the bundle layer
sizes = defaultdict(int)
for u in umap.values():
    sizes[u] += 1
msz = np.array(list(sizes.values()), int)
rho = out["resample_unit"]["VB"]["icc_ready"]
shape, scale = 2.0, 10.0
var = shape * scale ** 2
th = np.sqrt(rho * var / shape)
sr = np.sqrt((1 - rho) * var)


def unit_means():
    ce = rng.gamma(shape, th, len(msz))
    return ce + rng.normal(0, sr, len(msz)) / np.sqrt(msz)

big = np.concatenate([unit_means() for _ in range(400)])
tmed, tp90 = np.median(big), np.percentile(big, 90)
hit = {"med": 0, "p90": 0}
n_rep, B = 1000, 2000
for _ in range(n_rep):
    x = unit_means()
    res = x[rng.integers(0, len(x), (B, len(x)))]
    lo, hi = np.percentile(np.median(res, axis=1), [2.5, 97.5])
    hit["med"] += lo <= tmed <= hi
    lo, hi = np.percentile(np.percentile(res, 90, axis=1), [2.5, 97.5])
    hit["p90"] += lo <= tp90 <= hi
out["R1_unit_weighted_coverage_bundle"] = {k: v / n_rep for k, v in hit.items()} | {
    "units": int(len(msz)), "mcse": float(np.sqrt(0.95 * 0.05 / n_rep)), "B": B}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print("ok")
