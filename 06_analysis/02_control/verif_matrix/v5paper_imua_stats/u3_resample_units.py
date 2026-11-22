"""Effective sample size of U-3 under a coarser resampling unit:
map cluster -> (g8: drop leg/direction) and (cross-study: drop study prefix and |Fs<n>).
Reports units, Kish, weighted mean size, READY ICC, deff, n_eff per setting, and per-study unit counts.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5paper_imua_stats")
LAS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\v5_rerun\las_k1")
rows = list(csv.DictReader((V / "u3_cluster_map.csv").open(encoding="utf-8")))


def unit(study: str, cluster: str) -> str:
    b = cluster.split("::", 1)[1]
    b = re.sub(r"\|Fs[0-9]+", "", b)
    if study == "g8":
        b = "|".join(x for x in b.split("|") if x not in ("FL", "FR", "RL", "RR", "raised", "lowered", "none", "ref"))
        return "g8::" + b
    return b  # cross-study merge (C+g6, slope+x426b)


umap = {(r["study"], r["key"]): unit(r["study"], r["cluster"]) for r in rows}


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
    return float((msb - msw) / (msb + (n0 - 1) * msw))

sizes = defaultdict(int)
per_study_units = defaultdict(set)
for (st, key), u in umap.items():
    sizes[u] += 1
    per_study_units[st].add(u)
m = np.array(list(sizes.values()), float)
N = m.sum()
mw = (m ** 2).sum() / N
out = {"units": len(m), "kish_units": float(N ** 2 / (m ** 2).sum()), "m_weighted": float(mw),
       "per_study_units": {k: len(v) for k, v in per_study_units.items()}}
for setting in ("V0", "VB"):
    g = defaultdict(list)
    for f in sorted(LAS.glob(f"u3_*_{setting}.json")):
        st = f.stem[3:].rsplit("_", 1)[0]
        obj = json.loads(f.read_text(encoding="utf-8"))
        for rec in obj.get("records") or obj.get("results") or []:
            t = rec.get("t_ready_s")
            if isinstance(t, (int, float)) and not isinstance(t, bool):
                g[umap[(st, rec.get("id") or rec.get("key"))]].append(t)
    r = icc(list(g.values()))
    out[setting] = {"icc": r, "deff": float(1 + (mw - 1) * r), "n_eff": float(N / (1 + (mw - 1) * r))}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
