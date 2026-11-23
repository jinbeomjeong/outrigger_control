"""Ed. 6 review of spec rev. 9 6.4 P-pred provisional handling (stats-design-expert, 2026-11-24).

Checks against the s70 model (same author):
 (1) inputs counted on 'opportunity' + 'VBKL0 READY-unreached' lines only (trigger-none and
     pre-trigger-fallback lines dropped); rho bootstrap on n_i = 2 cases; pi_i = (a_c + k_i) /
     (a_c + b_c + n_i). Risk: a stall that prevents the trigger makes the line 'trigger-none'
     and drops it from the rate -> variant 'incl' counts those lines' READY outcome too.
 (2) b4 (TRw, one line per case, 167): spec 'A' = parameters and case posterior from b1/b2,
     b4 pairs take the tau_R cell rate; proposal 'C' = b4 gets its own Jeffreys rate from the
     observed b4 VBKL0 lines, no case pooling for b4 pairs (rho = 0, conservative);
     'B' = own TRw cell as C, posterior of the reached b4 line itself (n = 1, k = 0) with the
     b1/b2 rho draw, i.e. p_T * ab / (ab + 1).
 (3) whole-procedure false failure at alpha 0.10 for b1/b2 and b1/b2/b4.
 (4) c < 1 thinning check: n23 under c is a thinned sum of the c = 1 sum.
Truths: T0 erratum 8 point values (s70) with TRw rate p_T in {p_R, p_C, 2 p_C}, cross-phase
case dependence 'shared' (q_T = q_i p_T / p_cell) or 'indep' (own Beta, same rho); pre-trigger
stall fraction f_pre in {0, 0.5}.
Writes s71_ppred_rev9.json / .txt. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20261124
ALPHA = 0.10
N_CASE = (84, 83)
NC = sum(N_CASE)


def beta_draw(rng, p, rho, n):
    if rho <= 0 or p <= 0:
        return np.full(n, p)
    ab = 1.0 / rho - 1.0
    return rng.beta(p * ab, (1 - p) * ab, n)


def gen(rng, t):
    cell = np.repeat([0, 1], N_CASE)
    q = np.concatenate([beta_draw(rng, t["pC"], t["rho"], N_CASE[0]),
                        beta_draw(rng, t["pR"], t["rho"], N_CASE[1])])
    if t["cross"] == "shared":
        qT = np.clip(q * t["pT"] / np.where(cell == 0, t["pC"], t["pR"]), 0, 1)
    else:
        qT = beta_draw(rng, t["pT"], t["rho"], NC)
    st = rng.random((NC, 2)) < q[:, None]
    st4 = rng.random(NC) < qT
    # a stall before the trigger turns the line into 'trigger-none' (excluded by the spec)
    pre = st & (rng.random((NC, 2)) < t["f_pre"])
    pre4 = st4 & (rng.random(NC) < t["f_pre"])
    both = ~st.any(1)
    aa30 = both & (rng.random(NC) < 2 * t["r2"])
    return {"cell": cell, "q": q, "qT": qT, "st": st, "st4": st4, "pre": pre, "pre4": pre4,
            "aa30": aa30}


def inputs(v, mode):
    """Per-line inclusion for the rate inputs; opportunity = included and reached."""
    incl = np.ones_like(v["st"]) if mode == "incl" else ~v["pre"]
    k = (v["st"] & incl).sum(1)
    n = incl.sum(1)
    two = n == 2
    a30 = int((v["aa30"] & two).sum())
    nboth = int((two & (k == 0)).sum())
    opp = ~v["st"]                      # opportunity lines (reached; never trigger-none)
    return {"k": k, "n": n, "two": two, "a30": a30, "nboth": nboth, "opp": opp}


def inner(rng, v, inp, b4mode, n_par=300, n_rep=10):
    cell = v["cell"]
    K = [int(inp["k"][cell == c].sum()) for c in (0, 1)]
    N = [int(inp["n"][cell == c].sum()) for c in (0, 1)]
    idx2 = [np.flatnonzero((cell == c) & inp["two"]) for c in (0, 1)]
    opp4 = ~v["st4"] if b4mode else None
    if b4mode in ("B", "C"):
        K4 = int((v["st4"] & ~v["pre4"]).sum())
        N4 = int((~v["pre4"]).sum())
    out = []
    for _ in range(n_par):
        p = [rng.beta(K[c] + 0.5, N[c] - K[c] + 0.5) for c in (0, 1)]
        r2 = 0.5 * rng.beta(inp["a30"] + 0.5, max(inp["nboth"], 1) - inp["a30"] + 0.5)
        bs = np.concatenate([rng.choice(ix, ix.size) for ix in idx2 if ix.size])
        kk = inp["k"][bs].astype(float)
        pb = kk.mean() / 2 if kk.size else 0.0
        rho = 0.0 if pb <= 0 or kk.size < 2 else float(np.clip(
            kk.var(ddof=1) / (2 * pb * (1 - pb)) - 1.0, 0.0, 0.95))
        pc = np.where(cell == 0, p[0], p[1])
        if rho > 0:
            ab = 1.0 / rho - 1.0
            post = (pc * ab + inp["k"]) / (ab + inp["n"])
            postR = (p[1] * ab + inp["k"]) / (ab + inp["n"])
        else:
            post, postR = pc, np.full(NC, p[1])
        probs = [np.repeat(post, 2)[inp["opp"].ravel()]]
        if b4mode == "A":
            probs.append(postR[opp4])
        elif b4mode in ("B", "C"):
            pT = rng.beta(K4 + 0.5, N4 - K4 + 0.5)
            if b4mode == "B" and rho > 0:   # own TRw cell, the b4 line itself (n = 1, k = 0)
                pT = pT * ab / (ab + 1.0)
            probs.append(np.full(int(opp4.sum()), pT))
        pp = np.concatenate(probs)
        stall = rng.random((n_rep, pp.size)) < pp
        b2 = (~stall) & (rng.random((n_rep, pp.size)) < r2)
        out.append((stall | b2).sum(1))
    return np.concatenate(out)


def truth_null(rng, v, t, b4, n, delta=0.0):
    pp = [np.repeat(v["q"], 2)[(~v["st"]).ravel()]]
    if b4:
        pp.append(v["qT"][~v["st4"]])
    pp = np.concatenate(pp)
    stall = rng.random((n, pp.size)) < pp
    b2 = (~stall) & (rng.random((n, pp.size)) < t["r2"])
    if delta > 0:
        h = rng.random((n, pp.size)) < delta
        stall |= h
        b2 &= ~h
    return (stall | b2).sum(1)


def pick(b, alpha=ALPHA):
    for k in range(200):
        if (b > k).mean() <= alpha:
            return k
    return 200


def run(rng, t, mode, b4mode, reps):
    fpr, pw2, pw3, ks = [], [], [], []
    for _ in range(reps):
        v = gen(rng, t)
        inp = inputs(v, mode)
        k = pick(inner(rng, v, inp, b4mode))
        b4 = b4mode is not None
        ks.append(k)
        fpr.append(float((truth_null(rng, v, t, b4, 1500) > k).mean()))
        pw2.append(float((truth_null(rng, v, t, b4, 500, 0.02) > k).mean()))
        pw3.append(float((truth_null(rng, v, t, b4, 500, 0.03) > k).mean()))
    return {"k_q05_50_95": [int(x) for x in np.percentile(ks, [5, 50, 95])],
            "fpr": float(np.mean(fpr)), "fpr_cond_p95": float(np.percentile(fpr, 95)),
            "power_d2": float(np.mean(pw2)), "power_d3": float(np.mean(pw3))}


def thinning_check(rng):
    """c < 1: n23 = sum over changed pairs only (each a fresh draw) <= c = 1 sum, pathwise."""
    q = np.full(330, 0.03)
    draw = rng.random((20000, 330)) < q
    changed = rng.random((20000, 330)) < 0.3
    full, thin = draw.sum(1), (draw & changed).sum(1)
    return {"pathwise_le": bool((thin <= full).all()),
            "P_gt7_c1": float((full > 7).mean()), "P_gt7_c03": float((thin > 7).mean())}


def main() -> int:
    rng = np.random.default_rng(SEED)
    base = {"pC": 6 / 168, "pR": 1 / 166, "rho": 0.6, "r2": 1 / 324, "cross": "shared",
            "f_pre": 0.0, "pT": 1 / 166}
    cfg = {}
    for fpre in (0.0, 0.5):
        for mode in ("spec", "incl"):
            cfg[f"b12|fpre{fpre}|{mode}"] = ({**base, "f_pre": fpre}, mode, None)
    for pTn, pT in (("pR", base["pR"]), ("pC", base["pC"]), ("2pC", 2 * base["pC"])):
        for cross in ("shared", "indep"):
            for b4mode in ("A", "B", "C"):
                cfg[f"b124|pT={pTn}|{cross}|{b4mode}"] = ({**base, "pT": pT, "cross": cross},
                                                          "spec", b4mode)
    out = {"seed": SEED, "alpha": ALPHA, "thinning": thinning_check(rng), "configs": {}}
    for name, (t, mode, b4) in cfg.items():
        out["configs"][name] = run(rng, t, mode, b4, reps=150)
    ok = out["thinning"]["pathwise_le"]
    (HERE / "s71_ppred_rev9.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                              encoding="utf-8")
    L = [f"alpha {ALPHA}; thinning {out['thinning']}"]
    for n, r in out["configs"].items():
        L.append(f"{n:<26} k q05/50/95 {r['k_q05_50_95']} | FPR {100*r['fpr']:.2f}% "
                 f"(cond p95 {100*r['fpr_cond_p95']:.1f}%) | power d2 {100*r['power_d2']:.1f}% "
                 f"d3 {100*r['power_d3']:.1f}%")
    (HERE / "s71_ppred_rev9.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
