"""Ed. 7 Q7-S3/S4: confirmation-pool rules, (setting, row) cluster rule for the new sensitivity
settings, probe key count, and J-P3 rev 7 exceedance under exchangeability.
stats-design-expert, 2026-11-24, design only.

(A) grid pool (spec v7 6.3 (ga')), frame and per-row harmless-churn floor from s30
    (s30_pool_opp_p.csv: 420 V0-passing pool rows in 192 clusters; p_np = V0 failure share of the
    other offsets of the cluster, p_margin = Phi(-c) from the V0 within-cluster offset scatter).
    Null: row fails with prob min(1, f * p_i) (+ a uniform floor p0 per row), rows in a cluster
    correlated through a Gaussian copula (rho_c). f in {1, 3, 6}: the ed. 6 grid showed 3 non-tail
    opportunity failures in 174 (U832, rows with V0 p_margin ~ 0.002) -> about 5x the V0 floor.
    Harm: a share pi_c of clusters carries a defect, each offset of it fails independently with
    q (offset-specific final failure, records B: no-READY concordance o0.0/o0.05 phi ~ 0).
    Designs: G1 = one new V0-passing offset per cluster (174..192 rows), G2 = all 420.
    Rules: count(k) = fail iff failures > k; clus(k) = fail iff a cluster has >= 2 failing offsets
    or isolated failures > k.
(B) sensitivity rows, margin-scatter model of s40 (same author): S settings x 46 units, probe-seen
    units in the probe-corner settings are stop-only. Rules: clus(k) on (setting, row) as spec v7
    6.2; alternative xrow(k): additionally a row failing in >= 2 settings fails.
(C) probe: P(component effect invisible) and P(zero firings) vs keys/plants/lines.
(D) J-P3 rev 7: if the bound is fitted to cover the n seen reads, P(any of m new exchangeable reads
    exceeds) = m / (n + m); margin needed for a fitted normal / exponential tail.
Outputs (argv[1]): s31_confirm_rules.json / .txt. stdout: status only.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import norm

SEED = 20261114
HERE = Path(__file__).resolve().parent


def load_pool():
    """V0-passing pool rows by cluster; clusters with mixed V0 outcome (p_np > 0) are set apart
    (recommended record-only, like V0-failing rows)."""
    rows = list(csv.DictReader((HERE / "s30_pool_opp_p.csv").open(encoding="utf-8")))
    cl, mixed = defaultdict(list), defaultdict(list)
    for r in rows:
        key = (r["level"], r["fs_kN"], r["timing"], r["leg"], r["event"])
        (mixed if float(r["p_np"]) > 0 else cl)[key].append(float(r["p_margin"]))
    return list(cl.values()), {"|".join(k): len(v) for k, v in mixed.items()}


def grid_sim(rng, clusters, design, f, p0, rho_c, n_sim, harm=None, ks=(0, 1, 2, 3, 4, 6)):
    """design G1: one pool row per cluster drawn afresh in every replicate; G2: all pool rows."""
    ncl = len(clusters)
    if design == "G1":
        pick = [rng.integers(len(c), size=n_sim) for c in clusters]
        P = np.stack([np.minimum(1.0, f * np.array(c)[pk] + p0) for c, pk in zip(clusters, pick)], 1)
        cid = np.arange(ncl)
        z = rng.standard_normal((n_sim, ncl))
        fail = z < norm.ppf(np.clip(P, 1e-15, 1 - 1e-15))
        nrows = ncl
    else:
        sizes = np.array([len(c) for c in clusters])
        p = np.concatenate([np.minimum(1.0, f * np.array(c) + p0) for c in clusters])
        cid = np.repeat(np.arange(ncl), sizes)
        z = rng.standard_normal((n_sim, ncl))[:, cid] * np.sqrt(rho_c) \
            + rng.standard_normal((n_sim, p.size)) * np.sqrt(1 - rho_c)
        fail = z < norm.ppf(np.clip(p, 1e-15, 1 - 1e-15))[None, :]
        nrows = p.size
    ps = clusters
    if harm is not None:
        pi_c, q = harm
        bad = rng.random((n_sim, len(ps))) < pi_c
        fail |= bad[:, cid] & (rng.random((n_sim, nrows)) < q)
    nf = np.zeros((n_sim, len(ps)), int)
    np.add.at(nf.T, cid, fail.T)
    tot = nf.sum(1)
    clus = (nf >= 2).any(1)
    iso = (nf * (nf == 1)).sum(1)
    out = {"n_rows": int(nrows), "E_fail": float(tot.mean())}
    for k in ks:
        out[f"count{k}"] = float((tot > k).mean())
        out[f"clus{k}"] = float((clus | (iso > k)).mean())
    return out


def sens_frame():
    rows = [(4, 1)] + [(2, 1)] * 3 + [(2, 0)] * 4
    rows += [(2, 0), (2, 2), (4, 0), (4, 1), (4, 0), (4, 1), (4, 0), (4, 0)]
    return rows                       # 46 units per setting (ed6 6.2), seen = probe D0 units


def sens_sim(rng, S, n_probe_settings, c, rho_e, n_sim, harm=None, ks=(2, 3, 4, 5, 6)):
    one = sens_frame()
    frame = []
    for s in range(S):
        for (p, seen) in one:
            frame.append((p, seen if s < n_probe_settings else 0, s))
    ncl = len(frame)
    pmax = 4
    mu = np.full(ncl, c)
    z = rng.standard_normal((n_sim, ncl, 1))
    eps = rng.standard_normal((n_sim, ncl, pmax))
    e = np.sqrt(rho_e) * z + np.sqrt(1 - rho_e) * eps
    fail = (mu[None, :, None] + e) < 0
    if harm is not None:
        kind, q = harm
        rowidx = 0                    # R12 row (4 phases) of each setting
        targets = [rowidx] if kind == "one_setting" else [s * len(one) + rowidx for s in range(S)]
        for t in targets:
            fail[:, t, :] |= rng.random((n_sim, pmax)) < q
    valid = np.zeros((ncl, pmax), bool)
    for i, (p, s, _) in enumerate(frame):
        valid[i, s:p] = True
    fail &= valid[None]
    nf = fail.sum(2)
    tot = nf.sum(1)
    n_unseen = np.array([p - s for p, s, _ in frame])
    clustered = (nf >= 2) & (n_unseen[None, :] >= 2)
    iso = tot - (nf * clustered).sum(1)
    anyclus = clustered.any(1)
    # cross-setting: same row index failing (any phase) in >= 2 settings
    rowfail = (nf > 0).reshape(n_sim, S, len(one))
    xrow = (rowfail.sum(1) >= 2).any(1)
    out = {"n_units_unseen": int(n_unseen.sum()), "E_fail": float(tot.mean())}
    for k in ks:
        out[f"clus{k}"] = float((anyclus | (iso > k)).mean())
        out[f"xrow{k}"] = float((anyclus | xrow | (iso > k)).mean())
    return out


def probe_tables():
    out = {}
    for pi in (0.02, 0.05, 0.10, 0.20):
        out[f"pi{pi}"] = {f"keys{K}": float((1 - pi) ** K) for K in (8, 14, 20, 30)}
        out[f"pi{pi}"].update({f"units{n}": float((1 - pi) ** n) for n in (100, 300, 600)})
    out["P_zero_fire"] = {f"rate{r}": {f"lines{n}": float((1 - r) ** n) for n in (60, 120, 300)}
                          for r in (0.01, 0.03, 0.05, 0.10)}
    return out


def exch_table():
    out = {}
    for n in (50, 65, 150, 300):
        out[f"n_seen{n}"] = {f"m_new{m}": float(m / (n + m)) for m in (10, 50, 100, 200, 400)}
    # tail margin: seen max of n normal reads; margin d (in sd) above the true mean so that
    # P(any of m new > bound) <= 5 %: bound = mu + z_{1-0.05/m} sd (Bonferroni-like, independent)
    out["normal_bound_sd_for_5pct"] = {f"m{m}": float(norm.ppf(1 - 0.05 / m)) for m in (50, 100, 200, 400)}
    out["expected_max_sd_of_n_seen"] = {f"n{n}": float(norm.ppf(n / (n + 1))) for n in (50, 65, 150, 300)}
    return out


def main() -> int:
    out_dir = Path(sys.argv[1])
    rng = np.random.default_rng(SEED)
    clusters, mixed = load_pool()
    res = {"seed": SEED, "pool_clusters": len(clusters),
           "pool_rows": int(sum(len(c) for c in clusters)), "mixed_v0_clusters_set_apart": mixed,
           "grid": {}, "sens": {}}
    n_sim = 20000
    for design in ("G1", "G2"):
        for f in (1, 3):
            for p0 in (0.0, 0.005, 0.017):
                for rho in ((0.0,) if design == "G1" else (0.0, 0.5, 0.9)):
                    res["grid"][f"{design}|null|f{f}|p0{p0}|rho{rho}"] = grid_sim(
                        rng, clusters, design, f, p0, rho, n_sim)
        for pi_c in (0.01, 0.02, 0.05):
            for q in (0.3, 0.6, 1.0):
                res["grid"][f"{design}|harm|pi{pi_c}|q{q}"] = grid_sim(
                    rng, clusters, design, 1, 0.005, 0.5, n_sim // 2, harm=(pi_c, q))
    for S in (4, 6, 8):
        for c in (2.5, 2.8, 3.0, 3.5):
            res["sens"][f"S{S}|null|c{c}"] = sens_sim(rng, S, min(4, S), c, 0.5, n_sim)
        for kind, q in (("one_setting", 0.5), ("one_setting", 1.0), ("all_settings", 0.25),
                        ("all_settings", 0.5)):
            res["sens"][f"S{S}|harm|{kind}|q{q}"] = sens_sim(rng, S, min(4, S), 3.0, 0.5, n_sim // 2,
                                                             harm=(kind, q))
    res["probe"] = probe_tables()
    res["jp3_exchangeability"] = exch_table()
    # self check: independent zero rule analytic (G2, f=1, rho 0)
    p = np.concatenate([np.minimum(1.0, np.array(c) + 0.005) for c in clusters])
    an = 1 - np.prod(1 - p)
    mc = res["grid"]["G2|null|f1|p00.005|rho0.0"]["count0"]
    res["self_check"] = {"G2_zero_rule_analytic": float(an), "mc": mc,
                         "ok": abs(mc - an) < 4 * np.sqrt(an * (1 - an) / n_sim) + 1e-9}
    (out_dir / "s31_confirm_rules.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item()),
                                                    encoding="utf-8")
    L = [f"pool clusters {res['pool_clusters']} rows {res['pool_rows']}",
         f"self_check {json.dumps(res['self_check'], default=lambda o: o.item())}", "== grid =="]
    for k, v in res["grid"].items():
        L.append(f"{k:<32} rows {v['n_rows']} E {v['E_fail']:.2f} | " + " ".join(
            f"c{j} {100*v[f'count{j}']:.1f}" for j in (0, 1, 2, 3, 4, 6)) + " | " + " ".join(
            f"cl{j} {100*v[f'clus{j}']:.1f}" for j in (0, 1, 2, 3, 4, 6)))
    L.append("== sens (setting,row) ==")
    for k, v in res["sens"].items():
        L.append(f"{k:<30} unseen {v['n_units_unseen']} E {v['E_fail']:.2f} | " + " ".join(
            f"cl{j} {100*v[f'clus{j}']:.1f}" for j in (2, 3, 4, 5, 6)) + " | " + " ".join(
            f"xr{j} {100*v[f'xrow{j}']:.1f}" for j in (2, 3, 4, 5, 6)))
    L.append("== probe == " + json.dumps(res["probe"]))
    L.append("== J-P3 exchangeability == " + json.dumps(res["jp3_exchangeability"]))
    (out_dir / "s31_confirm_rules.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    ok = bool(res["self_check"]["ok"])
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
