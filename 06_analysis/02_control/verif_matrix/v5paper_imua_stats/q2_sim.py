"""Q1/Q2 simulations for the v5paper A-type rules review.

1. E-2 (READY lost after declaration) rows in the check runs (taken from the two public reviews,
   imua_check_review.md 'Correction' and imua_check_a2_review.md section 1) and whether the R0
   (current IMU) probe attitude change ranks those rows (possible opportunity predictor).
2. E-1 (READY delay) opportunity-based predicted failure counts in D-1, using 436.8 H-1 records
   (t_ready, t_ready_limit) and check-run A - R0 delays, with check-cluster bootstrap and
   D-1 key-shared delays (eps pair shares one delay draw).
3. Operating characteristics of a rate-based 'expected count interval' rule for a rare clustered
   event (beta-binomial at cluster level), anchored on check-run cluster rates.
4. ICC of 436.8 READY time across V0/VB within D-1 key.
Seed 20261114.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

SEED = 20261114
inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out: dict = {"seed": SEED}
rng = np.random.default_rng(SEED)

# ---------- 1. E-2 rows (from the reviews) ----------
E2 = {
    "A-v5": {("S5", "VB", 0.8, 0.002), ("S5", "VB", 0.8, 0.003)},
    "A2": {("S3", "VB", 0.85, 0.0), ("S3", "VB", 0.85, 0.002), ("S5", "VB", 0.8, 0.001),
           ("S5", "VB", 0.8, 0.002), ("S4", "VB", None, 0.0)},
}
e2out = {}
for arm in ("A-v5", "A2"):
    rows = inp["check"][arm]["rows"]
    vb = [r for r in rows if r["setting"] == "VB" and r["t_ready_A"] is not None]
    flags = [((r["case"], r["setting"], r["eta"], r["eps"]) in E2[arm]) for r in vb]
    pac = np.array([r["probe_att_change_R0"] if r["probe_att_change_R0"] is not None else np.nan for r in vb])
    ev = np.array(flags)
    ok = np.isfinite(pac)
    auc = None
    if ev[ok].any() and (~ev[ok]).any():
        u = stats.mannwhitneyu(pac[ok & ev], pac[ok & ~ev], alternative="two-sided")
        auc = float(u.statistic / (ev[ok].sum() * (~ev[ok]).sum()))
    clusters = defaultdict(list)
    for r, f in zip(vb, flags):
        clusters[r["cluster"]].append(f)
    e2out[arm] = {
        "vb_rows_with_ready": len(vb), "event_rows": int(ev.sum()),
        "vb_clusters": len(clusters), "event_clusters": sum(1 for v in clusters.values() if any(v)),
        "rows_in_event_clusters": sum(len(v) for v in clusters.values() if any(v)),
        "probe_att_change_R0_event": [float(x) for x in pac[ev]],
        "probe_att_change_R0_nonevent_quantiles": [float(np.nanpercentile(pac[~ev], q)) for q in (10, 50, 90)],
        "auc_R0_probe_change": auc,
    }
out["E2_check"] = e2out

# ---------- 2. E-1 predicted counts in D-1 ----------
def delta_pools(arm: str):
    rows = inp["check"][arm]["rows"]
    pools = {"V0": defaultdict(list), "VB": defaultdict(list)}
    for r in rows:
        if r["delta"] is None:
            continue
        pools["V0" if r["setting"] == "V0" else "VB"][r["cluster"]].append(r["delta"])
    return {k: [np.asarray(v) for v in d.values()] for k, d in pools.items()}

recs = inp["d1"]["recs"]
by_key = defaultdict(list)
for x in recs:
    if x["t_ready"] is None or x["t_ready_limit"] is None:
        continue
    by_key[(x["setting"], x["key"])].append(x["t_ready_limit"] - x["t_ready"])

e1 = {}
B = 4000
for arm in ("A-v5", "A2"):
    pools = delta_pools(arm)
    e1[arm] = {}
    for setting in ("V0", "VB"):
        keys = [k for k in by_key if k[0] == setting]
        margins = [np.asarray(by_key[k]) for k in keys]
        pos = [m[m >= 0] for m in margins]  # 436.8 pair passed READY (condition 1 of 4.2)
        n_rows_pass = int(sum(len(p) for p in pos))
        cl = pools[setting]
        counts_rows = np.empty(B)
        counts_clusters = np.empty(B)
        for b in range(B):
            boot = [cl[i] for i in rng.integers(0, len(cl), len(cl))]  # check-cluster bootstrap
            # one cluster-level delay per D-1 key: pick a boot cluster, then a row delay in it;
            # both eps rows of the key share it (436.8 eps ICC ~ 0.996)
            ci = rng.integers(0, len(boot), len(pos))
            d = np.array([boot[i][rng.integers(0, len(boot[i]))] for i in ci])
            fails = [int((p < dd).sum()) for p, dd in zip(pos, d)]
            counts_rows[b] = sum(fails)
            counts_clusters[b] = sum(1 for f in fails if f > 0)
        e1[arm][setting] = {
            "d1_rows_ready_pass_436_8": n_rows_pass, "d1_keys": len(keys),
            "pred_fail_rows_mean": float(counts_rows.mean()),
            "pred_fail_rows_q": [float(np.percentile(counts_rows, q)) for q in (2.5, 50, 97.5)],
            "pred_fail_keys_q": [float(np.percentile(counts_clusters, q)) for q in (2.5, 50, 97.5)],
            "check_clusters_in_pool": len(cl),
        }
out["E1_D1_predicted"] = e1

# ---------- 3. OC of a rate-anchored expected-count rule ----------
def predictive_upper(x_cl, n_cl, C, m, q_a, q_b, level=0.975, draws=40000):
    """Posterior predictive upper quantile of row count in a new bundle of C clusters x m rows.
    cluster event prob ~ Beta(x+0.5, n-x+0.5); given an event cluster, each row fails w.p. q~Beta(q_a,q_b)."""
    pi = rng.beta(x_cl + 0.5, n_cl - x_cl + 0.5, draws)
    q = rng.beta(q_a, q_b, draws)
    k = rng.binomial(C, pi)
    rows = rng.binomial(k * m, q) if m > 1 else k
    return float(np.quantile(rows, level)), float(np.mean(rows))

oc = {}
scen = {"D1_VB_217x2": (217, 2), "U6_C2_242x1": (242, 1), "U3_VB_340x3": (340, 3)}
q_a, q_b = 6 + 0.5, 4 + 0.5  # within-event-cluster row rate 6/10 rows (both arms pooled)
for arm, (xc, nc) in {"A-v5": (1, 15), "A2": (3, 15)}.items():
    oc[arm] = {}
    pi_hat = xc / nc
    for name, (C, m) in scen.items():
        U, mean_pred = predictive_upper(xc, nc, C, m, q_a, q_b)
        res = {"upper_97_5": U, "pred_mean": mean_pred, "flag_prob": {}}
        for r in (0.1, 0.5, 1.0, 2.0, 3.0, 5.0):
            pi_true = min(1.0, r * pi_hat)
            n = 20000
            k = rng.binomial(C, pi_true, n)
            rows = rng.binomial(k * m, 0.6) if m > 1 else k
            res["flag_prob"][f"{r:g}x"] = float((rows > U).mean())
        oc[arm][name] = res
out["rate_rule_OC"] = oc

# ---------- 4. ICC of 436.8 READY across V0/VB within D-1 key ----------
pairs = defaultdict(dict)
for x in recs:
    if x["t_ready"] is not None:
        pairs[x["key"]].setdefault(x["setting"], []).append(x["t_ready"])
v0 = []
vb = []
for k, d in pairs.items():
    if "V0" in d and "VB" in d:
        v0.append(np.mean(d["V0"]))
        vb.append(np.mean(d["VB"]))
v0 = np.asarray(v0)
vb = np.asarray(vb)
out["D1_ready_V0_VB"] = {"n_keys": len(v0), "pearson": float(np.corrcoef(v0, vb)[0, 1]),
                         "median_abs_diff": float(np.median(np.abs(vb - v0))),
                         "frac_abs_diff_le_1s": float((np.abs(vb - v0) <= 1).mean())}

Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ok")
