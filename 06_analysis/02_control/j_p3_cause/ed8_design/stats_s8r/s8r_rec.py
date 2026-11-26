"""S8-R design, part 4: recommended G' rule vs the draft rule (procedure-level Monte Carlo).

Draft (spec v8 rules 7.4-7.5 with 14 suggested values): per stratum k from Bin(n, CP95 upper of A/A),
  alpha 0.05, stop if CP95 upper > P0_UB_MAX 0.01 (both strata).
Recommended: N k from the Jeffreys posterior predictive at alpha_N 0.025, stop if CP95 upper > 0.025;
  E fixed k_E = 1, stop if A/A E failures >= 2. A/A one pair per unit, frozen at stage 5.
Model: latent liability, family ICC rho; true G' floor = mult x A/A floor.

Usage: python -I -B s8r_rec.py <out_folder> [reps]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

OUT = Path(sys.argv[1])
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
SEED = 20261114
rng = np.random.default_rng(SEED)
FAM_E, FAM_N = 8, 44
XMAX = 40


def cp_upper(x, n, conf=0.95):
    x = np.asarray(x)
    return np.where(x >= n, 1.0, stats.beta.ppf(conf, x + 1, np.maximum(n - x, 1)))


def k_binom(n, p, alpha):
    if p <= 0:
        return 0
    k = 0
    while stats.binom.sf(k, n, p) > alpha:
        k += 1
    return k


def k_pp(n, x, naa, alpha):
    d = stats.betabinom(n, x + 0.5, naa - x + 0.5)
    k = 0
    while d.sf(k) > alpha:
        k += 1
    return k


_T = {}


def table(n, naa, rule, alpha, pmax):
    key = (n, naa, rule, alpha, pmax)
    if key not in _T:
        xs = np.arange(naa + 1)
        k = np.full(naa + 1, n, int)
        for x in range(min(naa, XMAX) + 1):
            k[x] = k_binom(n, float(cp_upper(x, naa)), alpha) if rule == "cp" else k_pp(n, x, naa, alpha)
        stop = (cp_upper(xs, naa) > pmax) | (xs > XMAX)
        _T[key] = (k, stop)
    return _T[key]


def sizes(n, nf):
    s = np.full(nf, n // nf)
    s[: n % nf] += 1
    return s


def draw(sz, p0, rho, extra=None):
    fam = np.repeat(np.arange(len(sz)), sz)
    if p0 <= 0:
        f = np.zeros((REPS, fam.size), bool)
    else:
        c = stats.norm.ppf(min(p0, 0.5))
        f = (np.sqrt(rho) * rng.standard_normal((REPS, len(sz)))[:, fam]
             + np.sqrt(1 - rho) * rng.standard_normal((REPS, fam.size))) < c
    if extra is not None:
        f |= rng.random(f.shape) < extra
    return f


def procedure(design, nE, nN, p0, rho, mult=1.0, alt=None):
    szE, szN = sizes(nE, FAM_E), sizes(nN, FAM_N)
    xE, xN = draw(szE, p0, rho).sum(1), draw(szN, p0, rho).sum(1)
    exE = exN = None
    if alt is not None:
        exE, exN = alt(szE, szN)
    fE, fN = draw(szE, p0 * mult, rho, exE).sum(1), draw(szN, p0 * mult, rho, exN).sum(1)
    if design == "draft":
        kE, sE = table(nE, nE, "cp", 0.05, 0.01)
        kN, sN = table(nN, nN, "cp", 0.05, 0.01)
        stop = sE[xE] | sN[xN]
        failE, failN = fE > kE[xE], fN > kN[xN]
    else:
        kN, sN = table(nN, nN, "pp", 0.025, 0.025)
        stop = sN[xN] | (xE >= 2)
        failE, failN = fE > 1, fN > kN[xN]
    fail = (~stop) & (failE | failN)
    return {"stop": float(stop.mean()), "fail": float(fail.mean()),
            "fail_E": float(((~stop) & failE).mean()), "fail_N": float(((~stop) & failN).mean()),
            "pass": float(((~stop) & ~(failE | failN)).mean())}


def a_E_onefam(q):
    def f(szE, szN):
        e = np.zeros((REPS, szE.sum()))
        e[:, : szE[0]] = q
        return e, None
    return f


def a_E_diff(pi):
    return lambda szE, szN: (np.full((REPS, szE.sum()), pi), None)


def a_N_diff(pi):
    return lambda szE, szN: (None, np.full((REPS, szN.sum()), pi))


def a_N_fam(frac, q):
    def f(szE, szN):
        fam = np.repeat(np.arange(len(szN)), szN)
        bad = rng.random((REPS, len(szN))) < frac
        return None, np.where(bad[:, fam], q, 0.0)
    return f


res = {"seed": SEED, "reps": REPS, "null": [], "power": []}
txt = ["NULL (stop / fail / fail_E / fail_N / pass)"]
for design in ["draft", "rec"]:
    for nE, nN in [(24, 200), (30, 300)]:
        for p0 in [0.0, 0.001, 0.002, 0.005]:
            for rho in [0.13, 0.5]:
                for mult in [1.0, 3.0]:
                    r = procedure(design, nE, nN, p0, rho, mult)
                    r.update({"design": design, "nE": nE, "nN": nN, "p0_aa": p0, "rho": rho, "mult": mult})
                    res["null"].append(r)
                    txt.append(f"  {design:<5} nE {nE} nN {nN} p0 {p0:<5} rho {rho:<4} x{mult}: stop {r['stop']:.3f} "
                               f"fail {r['fail']:.4f} (E {r['fail_E']:.4f} N {r['fail_N']:.4f}) pass {r['pass']:.3f}")
alts = {"E_onefam_q0.8": a_E_onefam(0.8), "E_onefam_q0.5": a_E_onefam(0.5), "E_diff_0.10": a_E_diff(0.10),
        "N_diff_0.01": a_N_diff(0.01), "N_diff_0.02": a_N_diff(0.02), "N_diff_0.03": a_N_diff(0.03),
        "N_fam_0.05_q0.8": a_N_fam(0.05, 0.8)}
txt.append("\nPOWER at p0 0.002, rho 0.13 (P(fail) incl. stop as non-fail; stop reported)")
for design in ["draft", "rec"]:
    for nE, nN in [(24, 200), (30, 300)]:
        for name, a in alts.items():
            r = procedure(design, nE, nN, 0.002, 0.13, 1.0, a)
            r.update({"design": design, "nE": nE, "nN": nN, "alt": name})
            res["power"].append(r)
            txt.append(f"  {design:<5} nE {nE} nN {nN} {name:<16}: fail {r['fail']:.3f} (E {r['fail_E']:.3f} "
                       f"N {r['fail_N']:.3f}) stop {r['stop']:.3f}")
# exact single-stratum E numbers (independent units)
ex = []
for nE in [16, 20, 24, 30, 40]:
    for p0 in [0.001, 0.002, 0.005, 0.01]:
        ex.append({"nE": nE, "p0": p0, "P_gt0": float(stats.binom.sf(0, nE, p0)),
                   "P_gt1": float(stats.binom.sf(1, nE, p0))})
res["E_exact_size"] = ex
txt.append("\nE exact size (independent): P(F>0), P(F>1)")
for r in ex:
    txt.append(f"  nE {r['nE']} p0 {r['p0']}: >0 {r['P_gt0']:.4f}  >1 {r['P_gt1']:.4f}")
# one-family detection, exact: m E units in the defective family, per-unit q
fam_det = []
for m in [2, 3, 4, 5]:
    for q in [0.5, 0.8, 1.0]:
        fam_det.append({"m": m, "q": q, "P_ge1": 1 - (1 - q) ** m,
                        "P_ge2": float(stats.binom.sf(1, m, q))})
res["E_onefam_exact"] = fam_det
txt.append("\nE one defective family with m units, per-unit q (null failures ignored): P(>=1), P(>=2)")
for r in fam_det:
    txt.append(f"  m {r['m']} q {r['q']}: >=1 {r['P_ge1']:.3f}  >=2 {r['P_ge2']:.3f}")
(OUT / "s8r_rec.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
(OUT / "s8r_rec.txt").write_text("\n".join(txt), encoding="utf-8")
print(json.dumps({"status": "ok"}))
