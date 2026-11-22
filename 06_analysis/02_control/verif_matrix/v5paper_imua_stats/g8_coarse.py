"""Correlation between map clusters of g8 that share a base slope case (leg / direction dropped).

ICC(1) of map-cluster mean READY times (436.8 VB and V0 records) within coarse groups.
High ICC means the 84 g8 clusters are not independent at the coarse level.
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
cmap = {(r["study"], r["key"]): r["cluster"] for r in csv.DictReader((V / "u3_cluster_map.csv").open(encoding="utf-8"))}


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


def coarse(cluster: str) -> str:
    b = cluster.split("::", 1)[1]
    t = [x for x in b.split("|") if x not in ("FL", "FR", "RL", "RR", "raised", "lowered", "none", "ref")]
    return "|".join(t)

out = {}
for setting in ("V0", "VB"):
    obj = json.loads((LAS / f"u3_g8_{setting}.json").read_text(encoding="utf-8"))
    cl = defaultdict(list)
    for rec in obj["records"]:
        t = rec.get("t_ready_s")
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            cl[cmap[("g8", rec["id"])]].append(t)
    means = {c: float(np.mean(v)) for c, v in cl.items()}
    grp = defaultdict(list)
    for c, mu in means.items():
        grp[coarse(c)].append(mu)
    r, k, n = icc(list(grp.values()))
    out[setting] = {"coarse_groups": k, "map_clusters": n, "icc_between_map_clusters_within_coarse": r,
                    "group_sizes": sorted(len(v) for v in grp.values())}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
