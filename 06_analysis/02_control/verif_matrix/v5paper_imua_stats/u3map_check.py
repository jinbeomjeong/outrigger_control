"""Check the control-written U-3 cluster map (376 clusters).

- size distribution, Kish effective number of clusters, design effect / n_eff at the 436.8 READY ICC
  (READY record items only from las_k1/u3_*.json; no grade fields)
- cross-study near-duplicates: clusters whose base (study prefix and |Fs<n> stripped) repeats in
  another study (e.g. C 'g6|...|Fs8' vs g6 'g6|...|Fs0')
- R-1 cluster-bootstrap coverage with the actual size distribution (bundle layer, and study layers
  with >= 50 clusters), gamma cluster effect + normal row noise, ICC from data.
Seed 20261114.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 20261114
rng = np.random.default_rng(SEED)
V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5paper_imua_stats")
LAS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\v5_rerun\las_k1")
rows = list(csv.DictReader((V / "u3_cluster_map.csv").open(encoding="utf-8")))
cmap = {(r["study"], r["key"]): r["cluster"] for r in rows}
out: dict = {"seed": SEED, "map_rows": len(rows)}


def icc_oneway(groups):
    g = [np.asarray([x for x in v if x is not None], float) for v in groups]
    g = [x for x in g if len(x)]
    k = len(g)
    n = np.array([len(x) for x in g])
    N = n.sum()
    allv = np.concatenate(g)
    gm = allv.mean()
    ssb = sum(len(x) * (x.mean() - gm) ** 2 for x in g)
    ssw = sum(((x - x.mean()) ** 2).sum() for x in g)
    msb, msw = ssb / (k - 1), ssw / (N - k)
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    return float((msb - msw) / (msb + (n0 - 1) * msw))


sizes = defaultdict(int)
for r in rows:
    sizes[r["cluster"]] += 1
m = np.array(list(sizes.values()), float)
N = m.sum()
kish = N ** 2 / (m ** 2).sum()
mw = (m ** 2).sum() / N
out["sizes"] = {"clusters": len(m), "N": int(N), "max": int(m.max()), "mean": float(m.mean()),
                "hist": {str(int(k)): int((m == k).sum()) for k in sorted(set(m))},
                "kish_clusters": float(kish), "m_weighted": float(mw)}

# READY ICC per setting with this map
icc = {}
unmapped = 0
for setting in ("V0", "VB"):
    groups = defaultdict(list)
    for f in sorted(LAS.glob(f"u3_*_{setting}.json")):
        study = f.stem[3:].rsplit("_", 1)[0]
        obj = json.loads(f.read_text(encoding="utf-8"))
        for rec in obj.get("records") or obj.get("results") or []:
            key = rec.get("id") or rec.get("key")
            c = cmap.get((study, key))
            if c is None:
                unmapped += 1
                continue
            t = rec.get("t_ready_s")
            groups[c].append(t if isinstance(t, (int, float)) and not isinstance(t, bool) else None)
    rho = icc_oneway(list(groups.values()))
    deff = 1 + (mw - 1) * rho
    icc[setting] = {"icc_ready": rho, "deff": float(deff), "n_eff_rows": float(N / deff)}
out["icc"] = icc
out["unmapped_rows"] = unmapped

# cross-study duplicates
def base(c):
    b = c.split("::", 1)[1]
    b = re.sub(r"\|Fs[0-9]+", "", b)
    return b

bases = defaultdict(set)
for c in sizes:
    bases[base(c)].add(c.split("::", 1)[0])
dup = {b: sorted(s) for b, s in bases.items() if len(s) > 1}
pairs = defaultdict(int)
for s in dup.values():
    pairs["+".join(s)] += 1
out["cross_study_shared_bases"] = {"n_bases": len(dup), "by_study_pair": dict(pairs),
                                   "clusters_if_merged": len(bases), "examples": list(dup.items())[:6]}

# R-1 coverage with actual sizes
def coverage(msz, icc_v, n_rep=300, B=1000):
    msz = np.asarray(msz, int)
    shape, scale = 2.0, 10.0
    var = shape * scale ** 2
    vc, vr = icc_v * var, (1 - icc_v) * var
    th = np.sqrt(vc / shape)
    # true quantiles of the cluster-mean-free row population, cluster-weighted design: use big sim
    big = []
    for _ in range(40):
        ce = rng.gamma(shape, th, len(msz))
        big.append(np.repeat(ce, msz) + rng.normal(0, np.sqrt(vr), msz.sum()))
    big = np.concatenate(big)
    tmed, tp90 = np.median(big), np.percentile(big, 90)
    cid = np.repeat(np.arange(len(msz)), msz)
    starts = np.concatenate([[0], np.cumsum(msz)[:-1]])
    hit = {"med": 0, "p90": 0}
    for _ in range(n_rep):
        ce = rng.gamma(shape, th, len(msz))
        x = np.repeat(ce, msz) + rng.normal(0, np.sqrt(vr), msz.sum())
        idx = rng.integers(0, len(msz), (B, len(msz)))
        meds = np.empty(B)
        p90s = np.empty(B)
        for b in range(B):
            sel = np.concatenate([x[starts[i]:starts[i] + msz[i]] for i in idx[b]])
            meds[b] = np.median(sel)
            p90s[b] = np.percentile(sel, 90)
        lo, hi = np.percentile(meds, [2.5, 97.5])
        hit["med"] += lo <= tmed <= hi
        lo, hi = np.percentile(p90s, [2.5, 97.5])
        hit["p90"] += lo <= tp90 <= hi
    return {k: v / n_rep for k, v in hit.items()} | {"mcse": float(np.sqrt(0.95 * 0.05 / n_rep)), "C": int(len(msz))}

rho = icc["VB"]["icc_ready"]
cov = {"bundle_layer_376": coverage(list(sizes.values()), rho, n_rep=200, B=600)}
per_study = defaultdict(list)
for c, s in sizes.items():
    per_study[c.split("::", 1)[0]].append(s)
for st in ("g8", "p3b", "g6"):
    cov[f"study_{st}"] = coverage(per_study[st], rho, n_rep=300, B=800)
out["R1_coverage_row_weighted"] = cov
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print("ok")
