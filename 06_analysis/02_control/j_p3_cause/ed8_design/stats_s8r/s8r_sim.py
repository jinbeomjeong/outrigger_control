"""S8-R design, part 3: allowance rules for census and held-out G' (exact binomial + Monte Carlo).

No ed8 result is read. Inputs are numbers from s8r_frame / s8r_floor (pre-ed8) and the rule text.

Sections
  A  reachability: smallest CP 95 % upper bound vs P0_UB_MAX (spec 7.4), as a function of n_AA
  B  k tables: draft rule (binomial at CP upper, spec 7.5) vs Jeffreys posterior predictive
  C  procedure-level Monte Carlo for G' (decide k from A/A, then judge), stratified E/N and pooled,
     with family clustering of the null failures (latent-liability model)
  D  census: P(at least k+1 failures | harmless divergence floor p0) for the census opportunity sizes
  self-checks: rho 0 MC vs exact binomial; CP upper vs closed form for x = 0

Usage: python -I -B s8r_sim.py <out_folder> [reps]
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
res = {"seed": SEED, "reps": REPS}
txt = []


def cp_upper(x, n, conf=0.95):
    """One-sided Clopper-Pearson upper bound."""
    x = np.asarray(x)
    out = np.where(x >= n, 1.0, stats.beta.ppf(conf, x + 1, np.maximum(n - x, 1)))
    return out


def k_binom(n, p, alpha):
    """Smallest k with P(Bin(n, p) > k) <= alpha."""
    if p <= 0:
        return 0
    k = int(stats.binom.isf(alpha, n, p))
    while stats.binom.sf(k, n, p) > alpha:
        k += 1
    while k > 0 and stats.binom.sf(k - 1, n, p) <= alpha:
        k -= 1
    return k


def k_pp(n, x, naa, alpha):
    """Smallest k with P(BetaBin(n, x + 0.5, naa - x + 0.5) > k) <= alpha (Jeffreys predictive)."""
    a, b = x + 0.5, naa - x + 0.5
    dist = stats.betabinom(n, a, b)
    k = 0
    while dist.sf(k) > alpha:
        k += 1
    return k


def mde80(n, k, p0=0.0):
    """Smallest added per-unit defect rate pi with P(Bin(n, p0 + pi(1-p0)) > k) >= 0.8."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if stats.binom.sf(k, n, p0 + mid * (1 - p0)) >= 0.8:
            hi = mid
        else:
            lo = mid
    return hi


# ---------------------------------------------------------------- A reachability of P0_UB_MAX
A = []
for pmax in [0.01, 0.015, 0.02, 0.03]:
    row = {"p0_ub_max": pmax}
    for x in [0, 1, 2]:
        n = 1
        while cp_upper(x, n) > pmax:
            n += 1
        row[f"min_n_aa_x{x}"] = int(n)
    A.append(row)
res["A_reachability"] = A
txt.append("A. smallest A/A opportunity count n_AA for CP95 upper <= P0_UB_MAX (x = A/A failures)")
for r in A:
    txt.append(f"  P0_UB_MAX {r['p0_ub_max']}: x0 n>={r['min_n_aa_x0']}, x1 n>={r['min_n_aa_x1']}, x2 n>={r['min_n_aa_x2']}")
for n in [30, 40, 150, 170, 200, 300]:
    txt.append(f"  CP95 upper at 0/{n} = {float(cp_upper(0, n)):.4f}")

# ---------------------------------------------------------------- B k tables
B = []
for n in [20, 30, 40, 150, 170, 200, 250, 300, 340]:
    for x in [0, 1, 2, 3]:
        for alpha in [0.025, 0.05]:
            pu = float(cp_upper(x, n))
            kc = k_binom(n, pu, alpha)
            kp = k_pp(n, x, n, alpha)
            B.append({"n": n, "n_aa": n, "x_aa": x, "alpha": alpha, "p0_ub": pu, "k_draft_cp": kc,
                      "k_jeffreys_pp": kp, "mde80_draft": mde80(n, kc), "mde80_pp": mde80(n, kp)})
res["B_k_tables"] = B
txt.append("\nB. k by rule (n_AA = n): draft = binomial at CP95 upper; pp = Jeffreys predictive")
for r in B:
    if r["alpha"] == 0.025 or r["n"] in (30, 170, 300):
        txt.append(f"  n {r['n']:>3} x {r['x_aa']} a {r['alpha']}: p0_ub {r['p0_ub']:.4f}  k draft {r['k_draft_cp']:>2} "
                   f"(MDE80 {r['mde80_draft']:.3f})  k pp {r['k_jeffreys_pp']:>2} (MDE80 {r['mde80_pp']:.3f})")

# ---------------------------------------------------------------- C procedure-level Monte Carlo


def family_sizes(n, nfam):
    base = np.full(nfam, n // nfam)
    base[: n % nfam] += 1
    return base


def draw_fail(sizes, p0, rho, reps, extra=None):
    """Latent-liability failures; returns (reps, units) bool. extra: (reps, units) added failure prob."""
    nfam = len(sizes)
    fam_id = np.repeat(np.arange(nfam), sizes)
    if p0 <= 0:
        f = np.zeros((reps, fam_id.size), bool)
    else:
        c = stats.norm.ppf(p0)
        z = rng.standard_normal((reps, nfam))[:, fam_id]
        e = rng.standard_normal((reps, fam_id.size))
        f = (np.sqrt(rho) * z + np.sqrt(1 - rho) * e) < c
    if extra is not None:
        f |= rng.random(f.shape) < extra
    return f, fam_id


_TAB = {}
XMAX = 40  # A/A counts above this always stop (CP upper >> any P0_UB_MAX used here)


def tables_for(n, naa, alpha, rule, pmax):
    key = (n, naa, alpha, rule, pmax)
    if key not in _TAB:
        xs = np.arange(naa + 1)
        k = np.full(naa + 1, n, int)
        for x in range(min(naa, XMAX) + 1):
            k[x] = k_binom(n, float(cp_upper(x, naa)), alpha) if rule == "cp" else k_pp(n, x, naa, alpha)
        stop = (cp_upper(xs, naa) > pmax) | (xs > XMAX)
        _TAB[key] = (k, stop)
    return _TAB[key]


def run_config(nE, nN, famE, famN, p0E, p0N, rho, alphaN, ruleN, pmaxN, kE, stopE_x, alt=None,
               reps=REPS, mult=1.0):
    """Stratified G': N judged by ruleN (k from A/A), E fixed kE (stop if A/A E failures >= stopE_x).
    mult = true G' floor / A/A floor (misspecification). Returns rates."""
    szE, szN = family_sizes(nE, famE), family_sizes(nN, famN)
    kN_tab, stopN_tab = tables_for(nN, nN, alphaN, ruleN, pmaxN)
    # A/A (same structure, independent draw)
    aaE, _ = draw_fail(szE, p0E, rho, reps)
    aaN, _ = draw_fail(szN, p0N, rho, reps)
    xE, xN = aaE.sum(1), aaN.sum(1)
    stop = stopN_tab[xN] | (xE >= stopE_x)
    exE = exN = None
    if alt is not None:
        exE, exN = alt(szE, szN, reps)
    gE, _ = draw_fail(szE, min(p0E * mult, 0.5), rho, reps, exE)
    gN, _ = draw_fail(szN, min(p0N * mult, 0.5), rho, reps, exN)
    failE = gE.sum(1) > kE
    failN = gN.sum(1) > kN_tab[xN]
    fail = (~stop) & (failE | failN)
    return {"P_stop": float(stop.mean()), "P_fail": float(fail.mean()),
            "P_fail_E": float(((~stop) & failE).mean()), "P_fail_N": float(((~stop) & failN).mean()),
            "mcse_fail": float(np.sqrt(max(fail.mean() * (1 - fail.mean()), 1e-12) / reps))}


def run_pooled(nE, nN, famE, famN, p0E, p0N, rho, alpha, rule, pmax, alt=None, reps=REPS, mult=1.0):
    szE, szN = family_sizes(nE, famE), family_sizes(nN, famN)
    n = nE + nN
    k_tab, stop_tab = tables_for(n, n, alpha, rule, pmax)
    aaE, _ = draw_fail(szE, p0E, rho, reps)
    aaN, _ = draw_fail(szN, p0N, rho, reps)
    x = aaE.sum(1) + aaN.sum(1)
    stop = stop_tab[x]
    exE = exN = None
    if alt is not None:
        exE, exN = alt(szE, szN, reps)
    gE, _ = draw_fail(szE, min(p0E * mult, 0.5), rho, reps, exE)
    gN, _ = draw_fail(szN, min(p0N * mult, 0.5), rho, reps, exN)
    fail = (~stop) & ((gE.sum(1) + gN.sum(1)) > k_tab[x])
    return {"P_stop": float(stop.mean()), "P_fail": float(fail.mean())}


def alt_E_onefam(q):
    def f(szE, szN, reps):
        exE = np.zeros((reps, szE.sum()))
        exE[:, : szE[0]] = q  # one E family defective (families exchangeable)
        return exE, None
    return f


def alt_E_diffuse(pi):
    def f(szE, szN, reps):
        return np.full((reps, szE.sum()), pi), None
    return f


def alt_N_diffuse(pi):
    def f(szE, szN, reps):
        return None, np.full((reps, szN.sum()), pi)
    return f


def alt_N_fam(frac, q):
    def f(szE, szN, reps):
        fam_id = np.repeat(np.arange(len(szN)), szN)
        bad = rng.random((reps, len(szN))) < frac
        return None, np.where(bad[:, fam_id], q, 0.0)
    return f


# self-check: rho 0, p0 0.01, CP rule -> MC size of N vs exact procedure size
nchk = 170
k_tab, stop_tab = tables_for(nchk, nchk, 0.025, "cp", 1.0)
xs = np.arange(nchk + 1)
px = stats.binom.pmf(xs, nchk, 0.01)
exact = float(sum(px[x] * stats.binom.sf(k_tab[x], nchk, 0.01) for x in xs))
mc = run_config(0, nchk, 1, 40, 0.0, 0.01, 0.0, 0.025, "cp", 1.0, kE=99, stopE_x=99)
chk1 = abs(mc["P_fail_N"] - exact) < 4 * np.sqrt(exact * (1 - exact) / REPS) + 1e-4
cpx0 = abs(float(cp_upper(0, 200)) - (1 - 0.05 ** (1 / 200))) < 1e-9
res["self_checks"] = {"rho0_mc_vs_exact": [mc["P_fail_N"], exact, bool(chk1)], "cp_x0_closed_form": bool(cpx0)}
txt.append(f"\nself-checks: rho0 MC {mc['P_fail_N']:.4f} vs exact {exact:.4f} -> {chk1}; CP x0 closed form {cpx0}")

# frame values (s8r_frame / s8r_floor): E families 8; N families ~44 (48 minus excluded top-front RE1bF)
FAM_E, FAM_N = 8, 44
C = []
scen_null = []
for nN in [170, 200, 300]:
    for nE in [20, 30, 40]:
        for p0 in [0.0, 0.001, 0.002, 0.005, 0.01]:
            for rho in [0.0, 0.13, 0.5]:
                for ruleN in ["cp", "pp"]:
                    for kE in [0, 1]:
                        r = run_config(nE, nN, FAM_E, FAM_N, p0, p0, rho, 0.025, ruleN, 0.02, kE, 2)
                        r.update({"nN": nN, "nE": nE, "p0": p0, "rho": rho, "ruleN": ruleN, "kE": kE,
                                  "alphaN": 0.025, "p0_ub_max": 0.02, "mult": 1.0})
                        scen_null.append(r)
res["C_null"] = scen_null
txt.append("\nC1. null (harmless; A/A floor = G' floor), alphaN 0.025, P0_UB_MAX 0.02, E stop if A/A E >= 2")
for r in scen_null:
    if r["nE"] == 30 and r["rho"] in (0.0, 0.13, 0.5):
        txt.append(f"  nN {r['nN']} nE {r['nE']} p0 {r['p0']:<5} rho {r['rho']:<4} {r['ruleN']} kE {r['kE']}: "
                   f"stop {r['P_stop']:.3f} fail {r['P_fail']:.4f} (E {r['P_fail_E']:.4f}, N {r['P_fail_N']:.4f})")

# misspecified floor: true G' floor 3x the A/A floor
mis = []
for nN in [200, 300]:
    for p0 in [0.001, 0.002, 0.005]:
        for ruleN in ["cp", "pp"]:
            for kE in [0, 1]:
                r = run_config(30, nN, FAM_E, FAM_N, p0, p0, 0.13, 0.025, ruleN, 0.02, kE, 2, mult=3.0)
                r.update({"nN": nN, "nE": 30, "p0_aa": p0, "mult": 3.0, "ruleN": ruleN, "kE": kE})
                mis.append(r)
res["C_null_misspecified_x3"] = mis
txt.append("\nC2. null with G' floor = 3 x A/A floor (rho 0.13, nE 30)")
for r in mis:
    txt.append(f"  nN {r['nN']} p0_aa {r['p0_aa']:<5} {r['ruleN']} kE {r['kE']}: stop {r['P_stop']:.3f} fail {r['P_fail']:.4f}"
               f" (E {r['P_fail_E']:.4f}, N {r['P_fail_N']:.4f})")

# power
pw = []
alts = {"E_onefam_q0.5": alt_E_onefam(0.5), "E_onefam_q0.8": alt_E_onefam(0.8),
        "E_diffuse_0.05": alt_E_diffuse(0.05), "E_diffuse_0.10": alt_E_diffuse(0.10),
        "N_diffuse_0.01": alt_N_diffuse(0.01), "N_diffuse_0.02": alt_N_diffuse(0.02),
        "N_diffuse_0.03": alt_N_diffuse(0.03), "N_fam_0.05_q0.8": alt_N_fam(0.05, 0.8),
        "N_fam_0.10_q0.5": alt_N_fam(0.10, 0.5)}
for nN in [200, 300]:
    for name, alt in alts.items():
        for ruleN in ["cp", "pp"]:
            for kE in [0, 1]:
                r = run_config(30, nN, FAM_E, FAM_N, 0.002, 0.002, 0.13, 0.025, ruleN, 0.02, kE, 2, alt=alt)
                rp = run_pooled(30, nN, FAM_E, FAM_N, 0.002, 0.002, 0.13, 0.05, ruleN, 0.02, alt=alt)
                pw.append({"nN": nN, "nE": 30, "alt": name, "ruleN": ruleN, "kE": kE, "strat": r["P_fail"],
                           "strat_E": r["P_fail_E"], "strat_N": r["P_fail_N"], "pooled_a05": rp["P_fail"],
                           "stop": r["P_stop"]})
res["C_power"] = pw
txt.append("\nC3. power (p0 0.002 both strata, rho 0.13, nE 30): stratified (aN 0.025 + fixed kE) vs pooled (a 0.05)")
for r in pw:
    txt.append(f"  nN {r['nN']} {r['alt']:<16} {r['ruleN']} kE {r['kE']}: strat {r['strat']:.3f} "
               f"(E {r['strat_E']:.3f} N {r['strat_N']:.3f})  pooled {r['pooled_a05']:.3f}  stop {r['stop']:.3f}")

# per-stratum MDE80 (independent units, exact) for the recommended rule
mde = []
for nN in [170, 200, 300]:
    for x in [0, 1, 2]:
        kp = k_pp(nN, x, nN, 0.025)
        mde.append({"stratum": "N", "n": nN, "x_aa": x, "k": kp, "mde80": mde80(nN, kp)})
for nE in [20, 30, 40]:
    for kE in [0, 1]:
        mde.append({"stratum": "E", "n": nE, "x_aa": None, "k": kE, "mde80": mde80(nE, kE)})
res["mde80"] = mde
txt.append("\nMDE80 (independent units, added defect rate; N: Jeffreys pp k at a 0.025, n_AA = n)")
for r in mde:
    txt.append(f"  {r['stratum']} n {r['n']} x_aa {r['x_aa']} k {r['k']}: MDE80 {r['mde80']:.4f}")

# ---------------------------------------------------------------- D census harmless-stop probability
D = []
for n in [180, 300, 450, 740]:
    for p0 in [0.0005, 0.001, 0.002, 0.0035, 0.005]:
        row = {"n_opp": n, "p0": p0}
        for k in [0, 1, 2, 3, 4]:
            row[f"P_gt_{k}"] = float(stats.binom.sf(k, n, p0))
        row["k_for_5pct"] = k_binom(n, p0, 0.05)
        D.append(row)
res["D_census"] = D
txt.append("\nD. census: P(failures > k | harmless divergence floor p0 per opportunity unit)")
for r in D:
    txt.append(f"  n {r['n_opp']:>3} p0 {r['p0']:<6}: >0 {r['P_gt_0']:.3f} >1 {r['P_gt_1']:.3f} >2 {r['P_gt_2']:.3f} "
               f">3 {r['P_gt_3']:.3f}; k for 5 % {r['k_for_5pct']}")

ok = bool(chk1 and cpx0)
res["status"] = "ok" if ok else "self_check_failed"
(OUT / "s8r_sim.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
(OUT / "s8r_sim.txt").write_text("\n".join(txt), encoding="utf-8")
print(json.dumps({"status": res["status"]}))
