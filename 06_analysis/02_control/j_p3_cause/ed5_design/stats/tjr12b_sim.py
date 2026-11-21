"""T-JR-12b (held-out seed gate) design simulation.

Gate (13.9 sentence applied per pair): pass iff zero failures over all pairs,
failure = base READY & (new READY missing or new - base > 30 s), plus new FAULT
on any pair. Pairs = case x new seed, base = VB rev 4, new = rev 6.

Generative model (past VB rev 4 rows from h8_noise_VB.json, allowed input):
  * each case has stored rows (L3: 3 seeds, L2: 5 seeds) with READY time or
    none, and a substitute-leg indicator S (r79.rod_fallback non-empty);
  * a new seed draws a base row from the case's rows with Dirichlet(1) weights
    (Bayesian bootstrap: propagates the 3-seed uncertainty);
  * rev 6 equals rev 4 on pairs without a substitute leg (T8 hash design);
  * on a substitute pair, commands change with probability c; a changed pair
    draws its new outcome independently from the case's rows (decorrelation
    floor = harmless-change false rejection);
  * defect: each substitute pair additionally fails with probability delta
    (D1 homogeneous) or cases are susceptible with probability pi and a
    susceptible case's substitute pairs fail with min(1, delta/pi) (D2).
Seeds within a case share the case's outcome distribution (cluster structure).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
OUT = Path(sys.argv[1])
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
SEED = 20261114
M_MAX = 6
C_GRID = [0.0, 0.05, 0.25, 0.5, 1.0]
D_GRID = [0.0, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.05]
PI_D2 = 0.05


def strip_key(k):
    return k.split("#", 1)[1] if "#" in k else k


def case_id(k):
    t = k.split("|")
    return "|".join([t[0]] + t[2:])


def load_rows():
    vb = json.loads((ROOT / "h8_noise_VB.json").read_text(encoding="utf-8"))["results"]
    h6 = json.loads((ROOT / "h6_dg3_v4on.json").read_text(encoding="utf-8"))["results"]
    dg3_cases = {case_id(strip_key(r["key"])) for r in h6}
    cases = {}
    for r in vb:
        k = strip_key(r["key"])
        b = r.get("base") or {}
        t = b.get("t_ready_s")
        if t is None:
            t = b.get("t_ready")
        s = len((r.get("r79") or {}).get("rod_fallback") or []) > 0
        cases.setdefault(case_id(k), {"level": r.get("level"), "rows": []})["rows"].append(
            (np.nan if t is None else float(t), s)
        )
    return cases, dg3_cases


def build_population(cases, keep):
    names = [c for c in sorted(cases) if keep(c, cases[c])]
    nmax = max(len(cases[c]["rows"]) for c in names)
    T = np.full((len(names), nmax), np.nan)
    S = np.zeros((len(names), nmax), bool)
    valid = np.zeros((len(names), nmax), bool)
    for i, c in enumerate(names):
        for j, (t, s) in enumerate(cases[c]["rows"]):
            T[i, j], S[i, j], valid[i, j] = t, s, True
    return names, T, S, valid


def betabinom_fit(k, n):
    """MLE of beta-binomial (a, b) for per-case substitute counts k of n."""
    from scipy.optimize import minimize

    def nll(x):
        a, b = np.exp(x)
        return -stats.betabinom.logpmf(k, n, a, b).sum()

    r = minimize(nll, x0=np.log([1.0, 3.0]), method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-8, "fatol": 1e-10})
    a, b = np.exp(r.x)
    p = k.sum() / n.sum()
    nll_binom = -stats.binom.logpmf(k, n, p).sum()
    return {"a": float(a), "b": float(b), "rho_icc": float(1 / (a + b + 1)), "p_mean": float(a / (a + b)),
            "nll_betabinom": float(r.fun), "nll_binom": float(nll_binom), "p_binom": float(p)}


def simulate(T, S, valid, rng, reps, thin=None):
    """Return per-replicate arrays (reps, n_cases, M_MAX) of base/new draws.

    thin: optional per-case factor in (0, 1] applied to S (selection-bias
    correction for cases chosen because a stored seed had a substitute leg).
    """
    n, nmax = T.shape
    # Dirichlet(1) weights over each case's valid rows
    g = rng.gamma(1.0, size=(reps, n, nmax)) * valid[None]
    w = g / g.sum(axis=2, keepdims=True)
    cw = np.cumsum(w, axis=2)
    u_b = rng.random((reps, n, M_MAX, 1))
    u_d = rng.random((reps, n, M_MAX, 1))
    b = (u_b > cw[:, :, None, :]).sum(axis=3)
    d = (u_d > cw[:, :, None, :]).sum(axis=3)
    b = np.minimum(b, nmax - 1)
    d = np.minimum(d, nmax - 1)
    ii = np.arange(n)[None, :, None]
    tb, sb = T[ii, b], S[ii, b]
    if thin is not None:
        sb = sb & (rng.random(sb.shape) < thin[None, :, None])
    td = T[ii, d]
    base_ready = ~np.isnan(tb)
    floor_fail = base_ready & (np.isnan(td) | ((td - tb) > 30.0))
    return {
        "sb": sb,
        "floor_fail": floor_fail & sb,
        "u_c": rng.random((reps, n, M_MAX)),
        "u_def": rng.random((reps, n, M_MAX)),
        "susc": rng.random((reps, n)) < PI_D2,
        "base_noready": ~base_ready,
    }


def evaluate(sim, m, c, delta, model):
    sb = sim["sb"][:, :, :m]
    floor = sim["floor_fail"][:, :, :m] & (sim["u_c"][:, :, :m] < c)
    if model == "D1":
        p = np.full(sb.shape, delta)
    else:
        q = min(1.0, delta / PI_D2)
        p = np.where(sim["susc"][:, :, None], q, 0.0) * np.ones(sb.shape)
    defect = sb & (sim["u_def"][:, :, :m] < p)
    fails = (floor | defect).sum(axis=(1, 2))
    n_opp = sb.sum(axis=(1, 2))
    passed = fails == 0
    pr = passed.mean()
    pr1 = float((fails <= 1).mean())
    return {
        "p_pass": float(pr),
        "mcse": float(np.sqrt(pr * (1 - pr) / len(passed))),
        "p_pass_le1": pr1,
        "mcse_le1": float(np.sqrt(pr1 * (1 - pr1) / len(passed))),
        "n_opp_mean": float(n_opp.mean()),
        "n_opp_p05": float(np.quantile(n_opp, 0.05)),
        "n_pairs": int(sb.shape[1] * m),
    }


def analytic_checks(T, S, valid, m, delta, thin=None):
    """Fixed equal weights, c = 0: P(pass) = prod_i (1 - ps_i * delta)^m."""
    ps = (S & valid).sum(1) / valid.sum(1)
    if thin is not None:
        ps = ps * thin
    return float(np.prod((1 - ps * delta) ** m))


def main():
    t0 = time.time()
    cases, dg3_cases = load_rows()
    l2_dg3 = [c for c in dg3_cases if cases[c]["level"] == "L2"]
    pops = {
        "dg3_102L3+L2": lambda c, v: c in dg3_cases,
        "all_167L3+L2dg3": lambda c, v: v["level"] == "L3" or c in l2_dg3,
    }
    rng = np.random.default_rng(SEED)
    out = {
        "reps": REPS,
        "seed": SEED,
        "pi_D2": PI_D2,
        "source": "h8_noise_VB.json sha256 2219ab97 (VB rev 4 noise, L3 3 seeds, L2 5 seeds); "
        "h6_dg3_v4on.json sha256 ea0ab94c (Dg-3 135 keys -> case ids)",
        "pops": {},
    }
    # substitute-leg overdispersion over all L3 cases (3 seeds each)
    _, T3, S3, v3 = build_population(cases, lambda c, v: v["level"] == "L3")
    k3 = (S3 & v3).sum(1)
    n3 = v3.sum(1)
    bb = betabinom_fit(k3, n3)
    bb["count_hist"] = {int(x): int((k3 == x).sum()) for x in range(4)}
    bb["binom_expected"] = {int(x): float(len(k3) * stats.binom.pmf(x, 3, bb["p_binom"])) for x in range(4)}
    out["substitute_overdispersion_L3"] = bb
    for pname, keep in pops.items():
        names, T, S, valid = build_population(cases, keep)
        ps_all = float(S[valid].mean())
        thin = None
        if pname.startswith("dg3"):
            # posterior predictive per-seed substitute rate given k of n stored
            k = (S & valid).sum(1)
            n = valid.sum(1)
            a, b = bb["a"], bb["b"]
            post = (a + k) / (a + b + n)
            l3 = np.array([cases[c]["level"] == "L3" for c in names])
            # L2: few substitutes at L2 (1 of 835 rows), keep raw row rate
            raw = np.where(n > 0, k / n, 0.0)
            target = np.where(l3, post, raw)
            thin = np.where(raw > 0, np.minimum(1.0, target / np.maximum(raw, 1e-12)), 1.0)
        sim = simulate(T, S, valid, rng, REPS, thin)
        pres = {
            "n_cases": len(names),
            "p_sub_per_row": ps_all,
            "p_sub_new_seed_expected": float(sim["sb"][:, :, 0].mean()),
            "base_noready_per_row": float(np.isnan(T[valid]).mean()),
            "grid": [],
            "checks": {},
        }
        # self checks: c=0, delta=0 -> pass 1; delta=1 -> pass ~0; D1 vs analytic
        pres["checks"]["c0_d0_pass"] = evaluate(sim, 3, 0.0, 0.0, "D1")["p_pass"]
        pres["checks"]["d1_pass"] = evaluate(sim, 3, 0.0, 1.0, "D1")["p_pass"]
        for dlt in (0.01, 0.03):
            e = evaluate(sim, 3, 0.0, dlt, "D1")
            pres["checks"][f"D1_m3_d{dlt}_sim"] = e["p_pass"]
            pres["checks"][f"D1_m3_d{dlt}_sim_mcse"] = e["mcse"]
            pres["checks"][f"D1_m3_d{dlt}_analytic_equalw"] = analytic_checks(T, S, valid, 3, dlt, thin)
            # binomial with mean opportunity
            pres["checks"][f"D1_m3_d{dlt}_binom_Nopp"] = float((1 - dlt) ** e["n_opp_mean"])
        for m in range(1, M_MAX + 1):
            for c in C_GRID:
                for dlt in D_GRID:
                    for model in ("D1", "D2"):
                        if dlt == 0.0 and model == "D2":
                            continue
                        e = evaluate(sim, m, c, dlt, model)
                        e.update({"m": m, "c": c, "delta": dlt, "model": model})
                        pres["grid"].append(e)
        out["pops"][pname] = pres
    # analytic zero-count helpers
    out["zero_count"] = {
        str(n): {
            "upper95_rate": float(1 - 0.05 ** (1 / n)),
            "delta80": float(1 - 0.2 ** (1 / n)),
            "cp_upper95_check": float(stats.beta.ppf(0.95, 1, n)),
        }
        for n in (27, 45, 90, 100, 120, 135, 178, 223, 270)
    }
    out["single_case_detect"] = {
        str(m): float(1 - (1 - 0.267) ** m) for m in range(1, 11)
    }
    out["wall_s"] = time.time() - t0
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("ok", round(out["wall_s"], 1))


if __name__ == "__main__":
    main()
