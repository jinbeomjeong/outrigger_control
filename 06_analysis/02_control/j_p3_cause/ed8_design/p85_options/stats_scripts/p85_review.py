"""P8-5 (ed8) not-judgeable review: coverage, reach, follow-up sizing, masking.

Inputs: only published counts (judgement rev 5: 14/23 same pairs, P8-8 6/23,
P8-15 21 judged of 23 readable / 27) and the pre-seal design input
control_k1_window/k02_rounds.csv (offline PSW replay, public before the seal).
No stage-4 row values are read.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

OUT = Path(sys.argv[1])
K02 = Path(sys.argv[2])
SEED = 20261114
REPS = 20000
rng = np.random.default_rng(SEED)
res: dict = {"seed": SEED, "reps": REPS}

N_PAIR, N_SAME, THR = 23, 14, 15


def q95(n: int, alpha: float = 0.05) -> float:
    """One-sided exact upper bound on per-pair leak rate after 0 failures in n."""
    return 1.0 - alpha ** (1.0 / n) if n > 0 else 1.0


# ---- A. coverage meaning of the threshold (zero-failure bound) ----
A = {}
for n in (5, 6, 7, 14, 15, 20, 21, 23, 29, 37):
    cp = float(stats.beta.ppf(0.95, 1, n))  # Clopper-Pearson one-sided 0/n
    A[str(n)] = {
        "q95_upper": q95(n),
        "q95_cp_check": cp,
        "detect_q0.10": 1 - 0.9 ** n,
        "detect_q0.20": 1 - 0.8 ** n,
    }
    assert abs(cp - q95(n)) < 1e-12
# clustering: cases x 3 plants; effective n under within-case ICC
A["cluster_neff"] = {}
for rho in (0.0, 0.3, 0.6, 1.0):
    for n in (14, 15, 23):
        neff = n / (1 + (3 - 1) * rho)
        A["cluster_neff"][f"n{n}_rho{rho}"] = {"n_eff": neff, "q95": 1 - 0.05 ** (1 / neff)}
res["A_coverage"] = A

# ---- B. design-time round -> pair conversion from k02_rounds.csv ----
rows: dict[str, list[dict]] = {}
with K02.open(newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        rows.setdefault(r["run"], []).append(r)


def fnum(s: str):
    return float(s) if s not in ("", None) else None


B = {}
for arm in ("A", "a2"):
    runs = {k: v for k, v in rows.items() if k.endswith("-" + arm)}
    n_rounds = 0
    n_round_changed = 0
    n_row_changed = 0
    per_row = []
    for k, rr in runs.items():
        rr = sorted(rr, key=lambda x: int(x["round"]))
        prev_old, prev_new = 1.2, 1.2
        changed_any = False
        for r in rr:
            o = fnum(r["k1_old_scale"])
            nw = fnum(r["a0.05_k1_scale"])
            o = prev_old if o is None else o
            nw = prev_new if nw is None else nw
            n_rounds += 1
            if o != nw:
                n_round_changed += 1
                changed_any = True
            prev_old, prev_new = o, nw
        n_row_changed += int(changed_any)
        per_row.append({"rounds": len(rr), "changed": changed_any})
    n_rows = len(runs)
    p_row = (n_rows - n_row_changed) / n_rows
    B[arm] = {
        "rows": n_rows,
        "rounds": n_rounds,
        "rounds_changed": n_round_changed,
        "rows_changed": n_row_changed,
        "p_same_row": p_row,
        "mean_rounds_per_row": n_rounds / n_rows,
        "expected_same_of_23": 23 * p_row,
        "P_reach15_of_23": float(stats.binom.sf(THR - 1, 23, p_row)),
        "P_le14_of_23": float(stats.binom.cdf(14, 23, p_row)),
    }
# generic (1-r)^R table
gen = {}
for r in (1 / 19, 0.1, 6 / 23, 0.3):
    for R in (1, 1.7, 2, 3):
        p = (1 - r) ** R
        gen[f"r{r:.3f}_R{R}"] = {"p_same": p, "E_same23": 23 * p,
                                  "P_reach15": float(stats.binom.sf(14, 23, p))}
B["generic"] = gen
# implied per-round change rate from observed 14/23 at the replay's rounds/row
for arm in ("A", "a2"):
    R = B[arm]["mean_rounds_per_row"]
    B[arm]["implied_r_from_14of23"] = 1 - (N_SAME / N_PAIR) ** (1 / R)
res["B_design_time"] = B

# ---- C. reach probability of the sealed rule ----
ph = N_SAME / N_PAIR
jl, jh = stats.beta.ppf([0.025, 0.975], N_SAME + 0.5, N_PAIR - N_SAME + 0.5)
C = {"p_hat": ph, "jeffreys95": [float(jl), float(jh)]}
for p in (float(jl), ph, float(jh), 0.8, 0.9):
    an = float(stats.binom.sf(THR - 1, N_PAIR, p))
    sim = float((rng.binomial(N_PAIR, p, REPS) >= THR).mean())
    C[f"p{p:.3f}"] = {"analytic": an, "sim": sim, "mcse": math.sqrt(an * (1 - an) / REPS)}
    assert abs(an - sim) < 5 * math.sqrt(an * (1 - an) / REPS) + 1e-9
# smallest p with P(reach) >= 0.8 / 0.95
for tgt in (0.5, 0.8, 0.95):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if stats.binom.sf(THR - 1, N_PAIR, mid) >= tgt:
            hi = mid
        else:
            lo = mid
    C[f"p_needed_reach{tgt}"] = hi
res["C_reach"] = C


# ---- D. follow-up sizing m ----
def betabinom_sf(k: int, m: int, a: float, b: float) -> float:
    return float(stats.betabinom.sf(k - 1, m, a, b)) if m > 0 else float(k <= 0)


def min_m(need: int, prob_fn, target=0.95, m_max=2000):
    for m in range(need, m_max + 1):
        if prob_fn(m) >= target:
            return m
    return None


priors = {
    "plugin_p0.609": ("binom", ph),
    "jeffreys_low_0.406": ("binom", float(jl)),
    "predictive_jeffreys_post_B(14.5,9.5)": ("bb", (14.5, 9.5)),
    "predictive_power_prior_a0.5_B(7.5,5.0)": ("bb", (0.5 + 0.5 * 14, 0.5 + 0.5 * 9)),
    "no_result_design_prior_k02A": ("bb", (0.5 + (B["A"]["rows"] - B["A"]["rows_changed"]),
                                             0.5 + B["A"]["rows_changed"])),
    "no_result_vague_B(1,1)": ("bb", (1.0, 1.0)),
}
D = {}
for name, (kind, par) in priors.items():
    def pf(need):
        if kind == "binom":
            return lambda m: float(stats.binom.sf(need - 1, m, par))
        a, b = par
        return lambda m: betabinom_sf(need, m, a, b)
    D[name] = {"ga1_m_for_15new": min_m(15, pf(15)), "ga2_m_for_1new": min_m(1, pf(1))}
# clustered new keys (cases x 3 plants), plug-in mean p, within-case ICC rho


def sim_cluster_reach(m_cases: int, p: float, rho: float, need: int, reps=REPS) -> float:
    if rho <= 0:
        x = rng.binomial(3 * m_cases, p, reps)
    elif rho >= 1:
        x = 3 * rng.binomial(m_cases, p, reps)
    else:
        s = 1 / rho - 1
        pc = rng.beta(p * s, (1 - p) * s, (reps, m_cases))
        x = rng.binomial(3, pc).sum(axis=1)
    return float((x >= need).mean())


Dc = {}
for rho in (0.0, 0.3, 0.6):
    for p in (ph, float(jl)):
        mc = None
        for m_cases in range(5, 60):
            if sim_cluster_reach(m_cases, p, rho, 15) >= 0.95:
                mc = m_cases
                break
        Dc[f"p{p:.3f}_rho{rho}"] = {"cases": mc, "keys": None if mc is None else 3 * mc}
D["ga1_clustered_cases_x3"] = Dc
res["D_sizing"] = D


# ---- E. leak detection with masking; designs conditional on stage-1 (14 same, 0 diff) ----
def sim_stage(m: int, p: float, q: float, mu: float, reps=REPS):
    """Per pair: scale-same (no leak) w.p. p. Leak manifests w.p. q; if it manifests
    on a scale-same pair it also diverges a round scale w.p. mu (masked -> excluded),
    else the pair stays scale-same with a command difference (detected)."""
    u_same = rng.random((reps, m)) < p
    u_leak = rng.random((reps, m)) < q
    u_mask = rng.random((reps, m)) < mu
    masked = u_same & u_leak & u_mask
    detected = u_same & u_leak & ~u_mask
    n_same = (u_same & ~masked).sum(axis=1)
    det = detected.any(axis=1)
    return n_same, det


E = {}
for p_new in (ph, 0.8):
    for q in (0.0, 0.05, 0.1, 0.2, 0.3):
        for mu in (0.0, 0.5, 0.9):
            row = {}
            for label, m, need in (("ga1_m32", 32, 15), ("ga1_m50", 50, 15),
                                   ("ga2_m4", 4, 1), ("ga2_m6", 6, 1), ("ga2_m32", 32, 1)):
                ns, det = sim_stage(m, p_new, q, mu)
                passed = (~det) & (ns >= need)
                fail = det
                nj = (~det) & (ns < need)
                row[label] = {"pass": float(passed.mean()), "fail": float(fail.mean()),
                              "not_judgeable": float(nj.mean())}
            E[f"pnew{p_new:.3f}_q{q}_mu{mu}"] = row
# sequential (ga2-seq): add one key at a time until pooled same >= 15, cap 50
seq = {}
for q in (0.0, 0.1, 0.2):
    for mu in (0.0, 0.9):
        ns, det_first = None, None
        u_same = rng.random((REPS, 50)) < ph
        u_leak = rng.random((REPS, 50)) < q
        u_mask = rng.random((REPS, 50)) < mu
        masked = u_same & u_leak & u_mask
        detected = u_same & u_leak & ~u_mask
        csame = np.cumsum(u_same & ~masked, axis=1)
        stop = np.argmax(csame >= 1, axis=1)
        reached = (csame >= 1).any(axis=1)
        cdet = np.cumsum(detected, axis=1) > 0
        det_by_stop = cdet[np.arange(REPS), stop] & reached
        passed = reached & ~det_by_stop
        seq[f"q{q}_mu{mu}"] = {"pass": float(passed.mean()),
                               "mean_keys": float((stop[reached] + 1).mean())}
E["ga2_sequential_cap50"] = seq
# unconditional two-stage view vs sealed single-stage (from the design start)
U = {}
for q in (0.0, 0.1, 0.2):
    for mu in (0.0, 0.9):
        ns1, det1 = sim_stage(23, ph, q, mu)
        single = (~det1) & (ns1 >= 15)
        ns2, det2 = sim_stage(32, ph, q, mu)
        ga1 = single | ((~det1) & (ns1 < 15) & (~det2) & (ns2 >= 15))
        ns3, det3 = sim_stage(4, ph, q, mu)
        ga2 = single | ((~det1) & (ns1 < 15) & (~det3) & (ns1 + ns3 >= 15))
        U[f"q{q}_mu{mu}"] = {"sealed_single": float(single.mean()),
                             "ga1_two_stage_m32": float(ga1.mean()),
                             "ga2_two_stage_m4": float(ga2.mean())}
E["unconditional_pass"] = U
E["mcse_max"] = 0.5 / math.sqrt(REPS)
res["E_masking"] = E

# ---- F. sibling gates (published counts only) ----
F = {}
for name, k, n, thr in (("P8-5", 14, 23, 15), ("P8-8", 6, 23, 5), ("P8-15_readable", 21, 23, 20),
                        ("P8-15_all27", 21, 27, 20)):
    p = k / n
    lo, hi = stats.beta.ppf([0.025, 0.975], k + 0.5, n - k + 0.5)
    F[name] = {"k": k, "n": n, "thr": thr, "p_hat": p, "jeffreys95": [float(lo), float(hi)],
               "retro_P_reach_plugin": float(stats.binom.sf(thr - 1, n, p)),
               "retro_P_reach_jeff_low": float(stats.binom.sf(thr - 1, n, lo)),
               "q95_if_pass_at_thr": q95(thr)}
# P8-15 design-time derivable: F8-19 L-2 acts in 3/27 rows (one is r79 g6|56, disclosure 7)
for exempt in (2, 3):
    p = (23 - exempt) / 23
    F[f"P8-15_design_pred_exempt{exempt}_of23"] = {
        "E_same": 23 - exempt, "P_reach20_binom": float(stats.binom.sf(19, 23, p))}
res["F_siblings"] = F

OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"status": "ok", "out": str(OUT)}))
