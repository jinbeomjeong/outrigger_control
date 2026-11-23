"""Ed. 6 T-JR-12b: pre-registered k_allow re-decision from VBKL0 b1/b2 and its procedure-level
false-failure rate and power (stats-design-expert, 2026-11-23, design only; no VBK/VBKL output).

Pair model = erratum 8 design (ed5_design/stats_e8/e8_rule_sim.py, same author): 167 cases
(tau_C 84 / tau_R 83) x blocks b1, b2; per case stall probability q_i ~ Beta with line rate p_cell
and beta-binomial rho; both-reached pairs exceed +30 s with prob r2 (and -30 s with r2).
Null c = 1: every VBKL pair is a fresh draw of the case's VBKL0 distribution.
Procedure P (proposed for spec 6.4):
  1. from VBKL0 b1, b2: p_hat per cell = stalled lines / lines; rho_hat = pooled method-of-moments
     over all 167 cases (n = 2), clipped to [0, 0.95] (0 if no stall); r2_hat = 0.5 * (#|dREADY| >
     30 s) / (#both reached) (A/A, erratum 8 8-1 definition);
  2. build the per-pair posterior stall probability from the observed per-case stall pattern
     (same as e8 build_pairs) and simulate the c = 1 null (n_inner draws, fixed seed);
  3. k_allow = smallest k with P(n23 > k) <= alpha (alpha 0.025).
Truth scenarios: T0 = erratum 8 point values (p_C 0.0357, p_R 0.0060, rho 0.67/0.57, r2 0.0031),
T1 = A(i) cuts stalls to one third, T2 = stalls x 2, T3 = T0 with rho 0 (homogeneous),
T4 = T0 with r2 at its 95 % upper (0.0170).
Outputs s70_12b_kallow.json / .txt. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20261114
N_CASE = (84, 83)
ALPHA = 0.025


def draw_q(rng, p, rho, n):
    if rho <= 0 or p <= 0:
        return np.full(n, p)
    ab = 1.0 / rho - 1.0
    return rng.beta(p * ab, (1 - p) * ab, n)


def gen_vbk0(rng, truth):
    q = np.concatenate([draw_q(rng, truth["pC"], truth["rhoC"], N_CASE[0]),
                        draw_q(rng, truth["pR"], truth["rhoR"], N_CASE[1])])
    cell = np.repeat([0, 1], N_CASE)
    st = rng.random((q.size, 2)) < q[:, None]
    both = ~st.any(1)
    aa30 = both & (rng.random(q.size) < 2 * truth["r2"])
    return {"q": q, "cell": cell, "stall": st, "aa30": int(aa30.sum()), "n_both": int(both.sum())}


def estimate(v):
    st, cell = v["stall"], v["cell"]
    p = [st[cell == c].mean() for c in (0, 1)]
    k = st.sum(1).astype(float)
    pbar = k.mean() / 2
    if pbar <= 0 or pbar >= 1:
        rho = 0.0
    else:
        rho = float(np.clip(k.var(ddof=1) / (2 * pbar * (1 - pbar)) - 1.0, 0.0, 0.95))
    r2 = 0.5 * v["aa30"] / max(v["n_both"], 1)
    return {"pC": float(p[0]), "pR": float(p[1]), "rho": rho, "r2": r2}


def posterior(v, est):
    post = np.empty(v["q"].size)
    for c, pc in ((0, est["pC"]), (1, est["pR"])):
        m = v["cell"] == c
        k = v["stall"][m].sum(1)
        if est["rho"] <= 0 or pc <= 0:
            post[m] = pc
        else:
            ab = 1.0 / est["rho"] - 1.0
            a, b = pc * ab, (1 - pc) * ab
            post[m] = (a + k) / (a + b + 2)
    return post


def n23_draws(rng, q_case, reached, r2, n, delta=0.0):
    """VBKL-worse count n23 under c = 1 for opportunity pairs (reached = VBKL0 reached)."""
    qp = np.repeat(q_case, 2)[reached.ravel()]
    m = qp.size
    stall = rng.random((n, m)) < qp
    b3 = stall
    b2 = (~stall) & (rng.random((n, m)) < r2)
    if delta > 0:
        harm = rng.random((n, m)) < delta
        b3 = b3 | harm
        b2 = b2 & ~harm
    return (b3 | b2).sum(1)


def k_allow(rng, v, est, n_inner=3000):
    post = posterior(v, est)
    reached = ~v["stall"]
    b = n23_draws(rng, post, reached, est["r2"], n_inner)
    for k in range(0, 60):
        if (b > k).mean() <= ALPHA:
            return k, float((b > k).mean())
    return 60, float((b > 60).mean())


def k_allow_pred(rng, v, n_par=300, n_rep=10):
    """Procedure P-pred: posterior-predictive n23 (parameter uncertainty propagated).
    p_cell ~ Beta(k + 0.5, n - k + 0.5) (Jeffreys), r2 ~ 0.5 Beta(a30 + 0.5, n_both - a30 + 0.5),
    rho = pooled MoM on a case bootstrap (167 cases resampled within cell)."""
    st, cell = v["stall"], v["cell"]
    reached = ~st
    draws = []
    idx_c = [np.flatnonzero(cell == c) for c in (0, 1)]
    for _ in range(n_par):
        kc = [int(st[cell == c].sum()) for c in (0, 1)]
        nc = [2 * int((cell == c).sum()) for c in (0, 1)]
        est = {"pC": float(rng.beta(kc[0] + 0.5, nc[0] - kc[0] + 0.5)),
               "pR": float(rng.beta(kc[1] + 0.5, nc[1] - kc[1] + 0.5)),
               "r2": float(0.5 * rng.beta(v["aa30"] + 0.5, v["n_both"] - v["aa30"] + 0.5))}
        bs = np.concatenate([rng.choice(ix, ix.size) for ix in idx_c])
        k = st[bs].sum(1).astype(float)
        pbar = k.mean() / 2
        est["rho"] = 0.0 if pbar <= 0 else float(np.clip(
            k.var(ddof=1) / (2 * pbar * (1 - pbar)) - 1.0, 0.0, 0.95))
        post = posterior(v, est)
        draws.append(n23_draws(rng, post, reached, est["r2"], n_rep))
    b = np.concatenate(draws)
    for kk in range(0, 80):
        if (b > kk).mean() <= ALPHA:
            return kk, float((b > kk).mean())
    return 80, float((b > 80).mean())


def pick(b, alpha):
    for kk in range(0, 120):
        if (b > kk).mean() <= alpha:
            return kk
    return 120


def inner_plugin(rng, v, n_inner=3000):
    est = estimate(v)
    return n23_draws(rng, posterior(v, est), ~v["stall"], est["r2"], n_inner)


def inner_pred(rng, v, n_par=300, n_rep=10):
    st, cell = v["stall"], v["cell"]
    reached = ~st
    draws = []
    idx_c = [np.flatnonzero(cell == c) for c in (0, 1)]
    kc = [int(st[cell == c].sum()) for c in (0, 1)]
    nc = [2 * int((cell == c).sum()) for c in (0, 1)]
    for _ in range(n_par):
        est = {"pC": float(rng.beta(kc[0] + 0.5, nc[0] - kc[0] + 0.5)),
               "pR": float(rng.beta(kc[1] + 0.5, nc[1] - kc[1] + 0.5)),
               "r2": float(0.5 * rng.beta(v["aa30"] + 0.5, v["n_both"] - v["aa30"] + 0.5))}
        bs = np.concatenate([rng.choice(ix, ix.size) for ix in idx_c])
        k = st[bs].sum(1).astype(float)
        pbar = k.mean() / 2
        est["rho"] = 0.0 if pbar <= 0 else float(np.clip(
            k.var(ddof=1) / (2 * pbar * (1 - pbar)) - 1.0, 0.0, 0.95))
        draws.append(n23_draws(rng, posterior(v, est), reached, est["r2"], n_rep))
    return np.concatenate(draws)


ALPHAS = {"plugin": (0.025, 0.01, 0.005, 0.0025), "pred": (0.025, 0.05, 0.10, 0.20)}


def run_truth(rng, truth, reps=200, mode="plugin"):
    alphas = ALPHAS[mode]
    ks = {a: [] for a in alphas}
    fpr = {a: [] for a in alphas}
    pw = {a: {d: [] for d in (0.01, 0.02, 0.03)} for a in alphas}
    for _ in range(reps):
        v = gen_vbk0(rng, truth)
        binner = inner_plugin(rng, v) if mode == "plugin" else inner_pred(rng, v)
        reached = ~v["stall"]
        b = n23_draws(rng, v["q"], reached, truth["r2"], 1500)
        bds = {d: n23_draws(rng, v["q"], reached, truth["r2"], 600, delta=d) for d in pw[alphas[0]]}
        for a in alphas:
            k = pick(binner, a)
            ks[a].append(k)
            fpr[a].append(float((b > k).mean()))
            for d, bd in bds.items():
                pw[a][d].append(float((bd > k).mean()))
    res = {}
    for a in alphas:
        kk = np.array(ks[a])
        res[f"alpha{a}"] = {
            "k_allow_quantiles": [int(x) for x in np.percentile(kk, [5, 25, 50, 75, 95])],
            "procedure_fpr": float(np.mean(fpr[a])),
            "fpr_p95_conditional": float(np.percentile(fpr[a], 95)),
            "power": {str(d): float(np.mean(x)) for d, x in pw[a].items()}}
    return res


def ed5_replay(rng):
    """Apply procedure P to the observed ed. 5 VBK0 b1/b2 pattern (erratum 8 8-1)."""
    st = np.zeros((167, 2), bool)
    st[0] = (1, 1); st[1] = (1, 1); st[2] = (1, 0); st[3] = (0, 1)   # tau_C cases
    st[84] = (1, 0)                                                   # tau_R case
    v = {"q": np.zeros(167), "cell": np.repeat([0, 1], N_CASE), "stall": st, "aa30": 1,
         "n_both": 162}
    est = estimate(v)
    k, p = k_allow(rng, v, est, n_inner=20000)
    bp = inner_plugin(rng, v, 20000)
    bq = inner_pred(rng, v, 1000, 20)
    return {"est": est, "k_allow": k, "p_at_k": p,
            "plugin_k_by_alpha": {str(a): pick(bp, a) for a in ALPHAS["plugin"]},
            "pred_k_by_alpha": {str(a): pick(bq, a) for a in ALPHAS["pred"]}}


def main() -> int:
    rng = np.random.default_rng(SEED)
    base = {"pC": 6 / 168, "pR": 1 / 166, "rhoC": 0.674, "rhoR": 0.572, "r2": 1 / 324}
    truths = {
        "T0_ed5_point": base,
        "T1_stall_third": {**base, "pC": base["pC"] / 3, "pR": base["pR"] / 3},
        "T2_stall_x2": {**base, "pC": base["pC"] * 2, "pR": base["pR"] * 2},
        "T3_rho0": {**base, "rhoC": 0.0, "rhoR": 0.0},
        "T4_r2_upper": {**base, "r2": 0.016956},
    }
    out = {"seed": SEED, "alpha": ALPHA, "ed5_replay": ed5_replay(rng), "truths": {}}
    for name, t in truths.items():
        for mode in ("plugin", "pred"):
            out["truths"][f"{name}|{mode}"] = {"truth": t, **run_truth(
                rng, t, reps=200 if mode == "plugin" else 120, mode=mode)}
    ok = out["ed5_replay"]["k_allow"] in (6, 7, 8)
    out["self_check_ed5_k_in_6_8"] = ok
    (HERE / "s70_12b_kallow.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                              encoding="utf-8")
    L = [f"alpha {ALPHA}; ed5 replay {out['ed5_replay']}"]
    for n, rr in out["truths"].items():
        for a, r in rr.items():
            if a == "truth":
                continue
            L.append(f"{n:<22} {a:<12} k q05/25/50/75/95 {r['k_allow_quantiles']} | proc FPR "
                     f"{100*r['procedure_fpr']:.2f}% (cond p95 {100*r['fpr_p95_conditional']:.2f}%)"
                     f" | power d1/2/3% " + " ".join(f"{100*v:.1f}" for v in r["power"].values()))
    (HERE / "s70_12b_kallow.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
