"""OC of the opportunity-based E-1 'larger than expected' rule in D-1 (A-v5 delays).

Upper bound U = 97.5 % predictive quantile at delay scale 1 (check-cluster bootstrap x key draw).
Flag probability P(count > U) when the true delay distribution is the check pool scaled by s,
with the check pool itself fixed (true world) - i.e. only the D-1 key-level draw varies.
Also the share of predicted E-1 failures that lie inside the 45 s cap opportunity set.
Seed 20261114.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 20261114
rng = np.random.default_rng(SEED)
inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = inp["check"]["A-v5"]["rows"]
pools = {"V0": defaultdict(list), "VB": defaultdict(list)}
for r in rows:
    if r["delta"] is not None:
        pools["V0" if r["setting"] == "V0" else "VB"][r["cluster"]].append(r["delta"])
pools = {k: [np.asarray(v) for v in d.values()] for k, d in pools.items()}
by_key = defaultdict(list)
for x in inp["d1"]["recs"]:
    if x["t_ready"] is not None and x["t_ready_limit"] is not None:
        by_key[(x["setting"], x["key"])].append(x["t_ready_limit"] - x["t_ready"])

out = {"seed": SEED}
for setting in ("V0", "VB"):
    pos = [np.asarray(v)[np.asarray(v) >= 0] for k, v in by_key.items() if k[0] == setting]
    cl = pools[setting]

    def draw(scale, boot=True):
        src = [cl[i] for i in rng.integers(0, len(cl), len(cl))] if boot else cl
        ci = rng.integers(0, len(src), len(pos))
        d = scale * np.array([src[i][rng.integers(0, len(src[i]))] for i in ci])
        return sum(int((p < dd).sum()) for p, dd in zip(pos, d))

    base = np.array([draw(1.0) for _ in range(4000)])
    U = float(np.percentile(base, 97.5))
    res = {"U97_5_rows": U, "flag_prob": {}}
    for s in (0.75, 1.0, 1.25, 1.5, 2.0):
        c = np.array([draw(s, boot=False) for _ in range(3000)])
        res["flag_prob"][f"scale{s:g}"] = float((c > U).mean())
        res.setdefault("mean_count", {})[f"scale{s:g}"] = float(c.mean())
    out[setting] = res
Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ok")
