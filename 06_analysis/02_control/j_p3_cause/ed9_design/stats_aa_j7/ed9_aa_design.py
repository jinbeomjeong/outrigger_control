"""Edition-9 (436.9) A/A floor and J7 handling: design calculations.

Inputs are published numbers only (ed8 closing judgement 4.3/4.4, aa_cause_analysis 0-3,
diag2_interpretation 2.3/3.3, sweep_summary.csv window). No stage-5 jsonl values are read.

Sections
  A  CP95 reachability: max x_AA allowed by P0_UB_MAX at n_AA
  B  stop probability of the CP rule under a binomial A/A floor
  C  k (Jeffreys predictive) and MDE80 per scenario, false failure at r x floor
  D  J7 option A detection loss (fraction phi of harmful failures visible only in one-shot warnings)
  E  layer pairing: outcome-dependent (ed8 7.4) vs pre-treatment covariate, E-layer censoring of FAULT
  F  phase design: lattice vs continuous phases vs boundary avoidance (treatment-only window entry)
  G  reach of minimum-count gates (P8-5/P8-8/P8-15 style) for the expected-count register

Usage: python -I -B ed9_aa_design.py <out_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

SEED = 20261114
ALPHA = 0.025
P0_UB_MAX = 0.025


def cp_upper(x, n, conf=0.95):
    """One-sided Clopper-Pearson upper bound."""
    if x >= n:
        return 1.0
    return float(stats.beta.ppf(conf, x + 1, n - x))


def k_pp(n, x, naa, alpha=ALPHA):
    """Smallest k with P(BetaBin(n, x + 0.5, naa - x + 0.5) > k) <= alpha (ed8 rule 7.5)."""
    dist = stats.betabinom(n, x + 0.5, naa - x + 0.5)
    k = 0
    while dist.sf(k) > alpha:
        k += 1
    return k


def mde80(n, k, p0=0.0):
    """Smallest additive defect rate d with P(Bin(n, p0 + d) > k) >= 0.8."""
    lo, hi = 0.0, 1.0 - p0
    for _ in range(60):
        mid = (lo + hi) / 2
        if stats.binom.sf(k, n, p0 + mid) >= 0.8:
            hi = mid
        else:
            lo = mid
    return hi


def ff(n, k, p):
    """P(Bin(n, p) > k)."""
    return float(stats.binom.sf(k, n, min(p, 1.0)))


def section_a():
    out = []
    for naa in (280, 300, 310, 320, 334):
        row = {"n_aa": naa}
        for ub in (0.025, 0.03, 0.04, 0.05, 0.06):
            xmax = -1
            for x in range(0, 60):
                if cp_upper(x, naa) <= ub:
                    xmax = x
                else:
                    break
            row[f"xmax_ub{ub}"] = xmax
        row["cp95"] = {x: round(cp_upper(x, naa), 4) for x in range(0, 13)}
        out.append(row)
    return out


def section_b():
    out = []
    naa = 310
    xmax = max(x for x in range(60) if cp_upper(x, naa) <= P0_UB_MAX)
    for p in (0.001, 0.002, 0.003, 0.005, 0.0097, 0.013, 0.02, 0.0355):
        out.append({"n_aa": naa, "p_aa": p, "xmax": xmax,
                    "p_stop": float(stats.binom.sf(xmax, naa, p)),
                    "expected_x": naa * p})
    return out


SCEN = [
    ("S0 current items, floor 11/310 (no stop; threshold redesigned)", 11),
    ("S1 J7-A only: 3 D1 FAULT left", 3),
    ("S1+1 J7-A, one extra flip", 4),
    ("S3 J7-B (gyro) + 2 changed lines", 5),
    ("S2 J7-A or B + D1-C: 0 left", 0),
    ("x 1", 1),
    ("x 2", 2),
    ("x 6", 6),
    ("x 8", 8),
]


def section_c(n=310, naa=310):
    out = []
    for name, x in SCEN:
        k = k_pp(n, x, naa)
        p0 = x / naa
        row = {"scenario": name, "n": n, "n_aa": naa, "x_aa": x, "cp95": round(cp_upper(x, naa), 4),
               "ed8_stop": cp_upper(x, naa) > P0_UB_MAX, "k": k,
               "mde80_p0_0": mde80(n, k, 0.0), "mde80_p0_floor": mde80(n, k, p0)}
        for r in (1, 2, 3):
            row[f"ff_r{r}"] = ff(n, k, r * p0) if x > 0 else None
        # floor unknown but nonzero after x=0: use 0.002/0.005 anchors
        if x == 0:
            row["ff_p0.002"] = ff(n, k, 0.002)
            row["ff_p0.005"] = ff(n, k, 0.005)
        out.append(row)
    return out


def section_c2(naa=310, n=310):
    """Integrated over a NEW A/A draw (stochastic floor): stop and false failure."""
    out = []
    xs = np.arange(0, naa + 1)
    ks = {int(x): k_pp(n, int(x), naa) for x in range(0, 60)}
    for p_aa in (0.002, 0.005, 0.0097, 0.02, 0.0355):
        px = stats.binom.pmf(xs, naa, p_aa)
        for rule in ("cp_stop_0.025", "no_stop"):
            for r in (1, 2, 3):
                p_stop = 0.0
                p_ff = 0.0
                for x, w in zip(xs, px):
                    if w < 1e-12 or x >= 60:
                        continue
                    if rule == "cp_stop_0.025" and cp_upper(int(x), naa) > P0_UB_MAX:
                        p_stop += w
                        continue
                    p_ff += w * ff(n, ks[int(x)], r * p_aa)
                out.append({"p_aa": p_aa, "rule": rule, "r": r, "p_stop": p_stop, "p_false_fail": p_ff,
                            "p_stop_or_ff": p_stop + p_ff})
    return out


def section_d(n=310, naa=310):
    """J7-A detection loss. keep: x=11, all items visible. A: x=3, a share phi of harmful failures
    appear only as one-shot warnings and are lost."""
    k_keep = k_pp(n, 11, naa)
    k_a = k_pp(n, 3, naa)
    k_ac = k_pp(n, 0, naa)
    m_keep = mde80(n, k_keep, 11 / naa)
    m_a = mde80(n, k_a, 3 / naa)
    m_ac = mde80(n, k_ac, 0.0)
    rows = []
    for phi in (0.0, 0.1, 0.25, 0.5, 0.75):
        rows.append({"phi": phi, "mde80_keep_redesign": m_keep, "mde80_j7A": m_a / (1 - phi),
                     "mde80_j7A_d1C": m_ac / (1 - phi)})
    return {"k_keep": k_keep, "k_A": k_a, "k_A_C": k_ac, "breakeven_phi_A": 1 - m_a / m_keep,
            "breakeven_phi_A_C": 1 - m_ac / m_keep, "rows": rows}


def section_e(nE=24, kE=1, reps=200000, rng=None):
    """E layer: FAULT candidates are N by construction under outcome-dependent pairing (ed8 7.4),
    so E A/A never sees them; the judged E unit layer is pre-treatment (6.3), so VBN FAULT counts in E.
    q = per-line FAULT probability in E slots (same for A/A candidate and treatment, r = 1)."""
    out = []
    for q in (0.0, 0.01, 0.02, 0.04, 0.07):
        # ed8: x_E for this mechanism is always 0 -> no E stop; treatment X_E ~ Bin(nE, q)
        ff_cur = float(stats.binom.sf(kE, nE, q))
        # pre-treatment pairing: x_E ~ Bin(nE, q); stop if x_E >= 2 (ed8 E stop) before treatment runs
        p_stop_pre = float(stats.binom.sf(1, nE, q))
        ff_pre = (1 - p_stop_pre) * ff_cur
        out.append({"q": q, "nE": nE, "kE": kE, "current_p_stop": 0.0, "current_ff": ff_cur,
                    "pretreat_p_stop": p_stop_pre, "pretreat_ff": ff_pre,
                    "pretreat_stop_or_ff": p_stop_pre + ff_pre})
    return out


def section_f(rng, reps=400000):
    """Phase design with a lift-phase window of width W around a 10 Hz sample instant.
    Slot lift delay d ~ U(0, 100 ms) (relative to the offset 0 sample grid) [assumption].
    A line fails (D1 false FAULT) if (o + d) mod 100 ms lies in [-2.2, +4.7] ms of a sample.
    Susceptible share f of slots (others have no window). A/A rate = P(candidate fails | base passes)."""
    lo, hi = -2.2, 4.7
    W = hi - lo

    def in_win(t_ms):
        u = np.mod(t_ms - lo, 100.0)
        return u < W

    res = {}
    d = rng.uniform(0, 100, reps)
    schemes = {
        "lattice4_new": np.array([12.5, 37.5, 62.5, 87.5]),
        "lattice8_new_and_main": np.array([0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]),
    }
    for name, ph in schemes.items():
        m = len(ph)
        ib = rng.integers(0, m, reps)
        ic = (ib + rng.integers(1, m, reps)) % m
        base = in_win(ph[ib] + d)
        cand = in_win(ph[ic] + d)
        ok = ~base
        rate = float(np.mean(cand[ok]))
        # slot-level determinism: share of susceptible slots that have any failing lattice phase
        any_hit = np.zeros(reps, bool)
        for p in ph:
            any_hit |= in_win(p + d)
        res[name] = {"aa_rate_given_susceptible": rate, "base_fail_rate": float(np.mean(base)),
                     "share_slots_with_hit_phase": float(np.mean(any_hit))}
    ob = rng.uniform(0, 100, reps)
    oc = rng.uniform(0, 100, reps)
    base = in_win(ob + d)
    cand = in_win(oc + d)
    res["continuous"] = {"aa_rate_given_susceptible": float(np.mean(cand[~base])),
                         "base_fail_rate": float(np.mean(base)), "window_fraction": W / 100}
    # boundary avoidance: choose o so that predicted lift phase is outside window +/- margin;
    # treatment shifts lift time by s ~ U(-S, S) ms on a share g of slots.
    avoid = []
    for margin in (0.0, 3.0, 5.0):
        for S in (2.0, 5.0, 10.0, 20.0):
            # base lift position uniform over the allowed zone
            zone_lo, zone_hi = hi + margin, 100 + lo - margin
            pos = rng.uniform(zone_lo, zone_hi, reps)
            shift = rng.uniform(-S, S, reps)
            enter = in_win(pos + shift)
            avoid.append({"margin_ms": margin, "shift_halfwidth_ms": S,
                          "treat_only_entry_given_shifted": float(np.mean(enter)),
                          "excluded_phase_share": (W + 2 * margin) / 100})
    res["avoid"] = avoid
    # treatment-only rate q -> N false failure with A/A floor x (A/A cannot see it)
    n, naa = 310, 310
    tbl = []
    for x in (0, 3):
        k = k_pp(n, x, naa)
        for q in (0.001, 0.002, 0.004, 0.006, 0.01):
            tbl.append({"x_aa": x, "k": k, "q_treat_only": q,
                        "ff": ff(n, k, x / naa + q)})
    res["treat_only_ff"] = tbl
    return res


def section_g():
    """Reach of a minimum-count gate: X ~ Bin(N, pi), threshold m. P(X >= m)."""
    out = []
    for N, m in ((23, 15), (23, 5), (23, 20), (27, 20), (40, 15), (40, 20)):
        row = {"N": N, "m": m}
        for pi in (0.5, 0.6, 0.65, 0.7, 0.8, 0.9, 0.95):
            row[f"reach_pi{pi}"] = float(stats.binom.sf(m - 1, N, pi))
        # largest m with P(X >= m) >= 0.9 at pi lower bound 0.623 (P8-5 Wilson low)
        out.append(row)
    sizing = []
    for pi in (0.6, 0.7, 0.8, 0.9):
        for m in (5, 15, 20):
            Nmin = next(N for N in range(m, 400) if stats.binom.sf(m - 1, N, pi) >= 0.9)
            sizing.append({"pi_low": pi, "m": m, "N_for_reach90": Nmin})
    return {"reach": out, "sizing": sizing}


def selfcheck():
    """Known answers."""
    ok = {}
    ok["cp_3_310"] = abs(cp_upper(3, 310) - 0.0248) < 5e-4
    ok["cp_11_310"] = abs(cp_upper(11, 310) - 0.0581) < 5e-4
    ok["cp_6_312"] = abs(cp_upper(6, 312) - 0.0376) < 5e-4
    # ed8 published MDE80 at n 300 x 0: 1.8 % (rule 315); n_aa = n assumed there
    ok["mde_300_x0"] = abs(mde80(300, k_pp(300, 0, 300)) - 0.018) < 0.002
    ok["mde_200_x0"] = abs(mde80(200, k_pp(200, 0, 200)) - 0.027) < 0.002
    return ok


def main():
    out_dir = Path(sys.argv[1])
    rng = np.random.default_rng(SEED)
    res = {"seed": SEED, "selfcheck": selfcheck()}
    res["A_cp_reach"] = section_a()
    res["B_cp_stop"] = section_b()
    res["C_k_mde_fixed_floor"] = section_c()
    res["C2_new_draw"] = section_c2()
    res["D_j7A_loss"] = section_d()
    res["E_pairing"] = section_e()
    res["F_phase"] = section_f(rng)
    res["G_reach"] = section_g()
    (out_dir / "ed9_aa_design.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("status", "ok" if all(res["selfcheck"].values()) else "selfcheck_fail")


if __name__ == "__main__":
    main()
