"""S-1 review calculations for edition 8 design (436.9 J-P3).

Inputs (no edition-7 metric files):
  - stored V0 grid pool frame (s30_pool_runs.csv, stats ed7 design output)
  - sealed G1 key file (keys and V0 pair flags only)
Outputs: JSON + TXT in the output folder given as argv[1].

Parts
  A  sensitivity cluster rule (setting,row; >=2 failing phases or singles > k=4) under the
     s31 margin model: unit fails iff c + sqrt(rho) z_row + sqrt(1-rho) e_unit < 0.
     A1 unconditional null false-failure vs rho (Monte Carlo, self-check vs q10 rho .5 c 2.8).
     A2 conditional false-failure given the sealed fixed-table pattern (only VBMslow S7 seen
        phase failed, 39 seen units passed), by numerical integration + DP over rows.
     A3 floor bound c implied by 0 failures in 788 units when units are row-correlated.
  B  confirmation stage G1 (k = 3, 168 lines): Poisson-approx P(N=3), P(N>=3) for the
     sealed null expectations, and the N=3 implied floor interval.
  C  held-out design table: k for FPR <= 5 %, MDE80 defect fraction, for n and p0 grid.
  D  remaining grid pool after editions 6 and 7 (keys only).
  E  effective sample size under phase/seed ICC.
"""

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import integrate, stats

SEED = 20261114
OUT = Path(sys.argv[1])
POOL_CSV = Path(sys.argv[2])
G1_JSON = Path(sys.argv[3])

# ---------------------------------------------------------------- frame (q01_inspect.json)
# per setting: rows -> (n_phases, n_seen)
ROWS = [
    ("R12", 4, 1),
    ("R12_top-FL-Fs0", 2, 0),
    ("R12_top-FL-Fs8", 2, 1),
    ("R12_top-FR-Fs4", 2, 1),
    ("R12_top-RL-Fs4", 2, 0),
    ("R12_top-RR-Fs4", 2, 0),
    ("R12_bottom-FL-Fs4", 2, 1),
    ("R12_bottom-RR-Fs4", 2, 0),
    ("R14", 2, 0),
    ("R15", 2, 2),
    ("R16", 4, 0),
    ("S1", 4, 1),
    ("S4", 4, 1),
    ("S5", 4, 1),
    ("S7", 4, 1),
    ("R2ra", 4, 0),
]
SETTINGS = ["VBMslow", "VBMfast", "VBMc005", "VBMc04"]
K_SINGLE = 4
assert sum(r[1] for r in ROWS) == 46 and sum(r[2] for r in ROWS) == 10


def rule_fail(fails_per_row):
    """fails_per_row: array (..., n_rows_total) of failing-phase counts."""
    multi = (fails_per_row >= 2).any(axis=-1)
    singles = (fails_per_row == 1).sum(axis=-1)
    return multi | (singles > K_SINGLE)


def mc_unconditional(rho, c, reps, rng):
    nph = np.array([r[1] for r in ROWS] * len(SETTINGS))
    nrow = nph.size
    maxp = nph.max()
    z = rng.standard_normal((reps, nrow, 1))
    e = rng.standard_normal((reps, nrow, maxp))
    margin = c + math.sqrt(rho) * z + math.sqrt(1.0 - rho) * e
    mask = np.arange(maxp)[None, None, :] < nph[None, :, None]
    fails = ((margin < 0) & mask).sum(axis=-1)
    f = rule_fail(fails)
    p = f.mean()
    return float(p), float(math.sqrt(p * (1 - p) / reps))


def p_unit(z, rho, c):
    if rho >= 1.0:
        return 1.0 if c + z < 0 else 0.0
    return stats.norm.cdf((-c - math.sqrt(rho) * z) / math.sqrt(1.0 - rho))


Z_GRID = np.linspace(-14.0, 14.0, 56001)
PHI_Z = stats.norm.pdf(Z_GRID)


def row_dist_given_seen(rho, c, n_seen, f_seen, n_unseen):
    """P(#unseen fails = j | seen pattern), j = 0..n_unseen (trapezoid on a fine z grid)."""
    p = stats.norm.cdf((-c - math.sqrt(rho) * Z_GRID) / math.sqrt(1.0 - rho))
    w = PHI_Z * p ** f_seen * (1 - p) ** (n_seen - f_seen)
    den = np.trapezoid(w, Z_GRID)
    out = [np.trapezoid(w * math.comb(n_unseen, j) * p ** j * (1 - p) ** (n_unseen - j),
                        Z_GRID) / den for j in range(n_unseen + 1)]
    return np.array(out)


def row_dist_quad_check(rho, c):
    """Independent quad evaluation of P(other S7 phase fails | seen fails) for one case."""
    zc = -c / math.sqrt(rho)

    def w(z):
        return stats.norm.pdf(z) * p_unit(z, rho, c)

    def g(z):
        p = p_unit(z, rho, c)
        return stats.norm.pdf(z) * p * (1 - (1 - p) ** 3)

    den = integrate.quad(w, -12, 12, points=[zc], limit=200)[0]
    return integrate.quad(g, -12, 12, points=[zc], limit=200)[0] / den


def conditional_fail(rho, c):
    """P(rule fails | fixed table: VBMslow S7 seen phase failed, all other seen passed)."""
    # DP over rows: state = singles count (0..K+1 capped), absorbing 'failed'
    state = np.zeros(K_SINGLE + 2)  # index K+1 = singles > K
    state[0] = 1.0
    p_failed = 0.0
    for s in SETTINGS:
        for name, nph, nseen in ROWS:
            f_seen = 1 if (s == "VBMslow" and name == "S7") else 0
            nun = nph - nseen
            if nun == 0:
                dist = np.array([1.0])
            else:
                dist = row_dist_given_seen(rho, c, nseen, f_seen, nun)
            tot = {}
            for j, pj in enumerate(dist):
                t = f_seen + j
                tot[t] = tot.get(t, 0.0) + pj
            p_multi = sum(v for t, v in tot.items() if t >= 2)
            p_one = tot.get(1, 0.0)
            p_zero = tot.get(0, 0.0)
            new = np.zeros_like(state)
            p_failed += state.sum() * p_multi
            new += state * p_zero
            shifted = np.zeros_like(state)
            shifted[1:] = state[:-1]
            shifted[-1] += state[-1]
            new += shifted * p_one
            state = new
    p_failed += state[-1]
    return float(p_failed)


def s7_other_phase(rho, c):
    """P(at least one of 3 unseen S7 phases fails | seen S7 phase failed)."""
    d = row_dist_given_seen(rho, c, 1, 1, 3)
    return float(1 - d[0])


def floor_c(n_units, deff):
    n_eff = n_units / deff
    up = 1 - 0.05 ** (1 / n_eff)  # 95 % one-sided upper bound for 0 events
    return n_eff, up, float(-stats.norm.ppf(up))


def main():
    rng = np.random.default_rng(SEED)
    res = {"seed": SEED, "notes": "see module docstring"}

    # ---------------- A1 unconditional
    rhos = [0.0, 0.5, 0.8, 0.9, 0.95, 0.99, 1.0]
    cs = [2.3, 2.5, 2.8, 3.0, 3.5]
    a1 = {}
    for rho in rhos:
        for c in cs:
            reps = 40000
            p, se = mc_unconditional(min(rho, 1.0), c, reps, rng)
            a1[f"rho{rho}|c{c}"] = {"fpr": p, "mcse": se, "reps": reps}
    res["A1_unconditional"] = a1
    # analytic limits for self-check
    nrows = len(ROWS) * len(SETTINGS)
    res["A1_check"] = {
        "q10_rho0.5_c2.8_ref": 0.0325,
        "mc_rho0.5_c2.8": a1["rho0.5|c2.8"]["fpr"],
        "rho1_analytic_c2.8": 1 - (1 - stats.norm.cdf(-2.8)) ** nrows,
        "mc_rho1_c2.8": a1["rho1.0|c2.8"]["fpr"],
    }
    # ---------------- A2 conditional
    a2 = {}
    for rho in [0.0, 0.5, 0.8, 0.9, 0.95, 0.99]:
        for c in [2.3, 2.5, 2.8, 3.0, 3.5]:
            a2[f"rho{rho}|c{c}"] = {
                "p_rule_fail_given_fixed": conditional_fail(rho, c),
                "p_s7_other_phase_fail_given_seen_fail": s7_other_phase(rho, c),
            }
    a2["rho1.0|any_c"] = {"p_rule_fail_given_fixed": 1.0,
                          "p_s7_other_phase_fail_given_seen_fail": 1.0}
    res["A2_conditional"] = a2
    res["A2_check_quad_rho0.5_c2.8"] = {
        "quad": row_dist_quad_check(0.5, 2.8),
        "grid": a2["rho0.5|c2.8"]["p_s7_other_phase_fail_given_seen_fail"],
    }
    # rho = 0 analytic: other phases independent of the seen failure
    res["A2_check_rho0_analytic"] = 1 - (1 - stats.norm.cdf(-2.8)) ** 3
    # ---------------- A3 floor bound
    mean_ph = 46 / 16
    a3 = {}
    for rho in [0.0, 0.5, 0.8, 0.95, 0.99]:
        deff = 1 + (mean_ph - 1) * rho
        n_eff, up, c = floor_c(788, deff)
        a3[f"rho{rho}"] = {"deff": deff, "n_eff": n_eff, "upper95": up, "c_sigma": c}
    res["A3_floor_bound_788"] = a3

    # ---------------- B G1 boundary (Poisson approximation of Poisson-binomial)
    e_tab = {"0": 0.24, "0.002": 0.57, "0.005": 1.08, "0.01": 1.92, "0.017": 3.09}
    b = {}
    for p0, e in e_tab.items():
        b[p0] = {"E": e, "P_N_eq_3": float(stats.poisson.pmf(3, e)),
                 "P_N_ge_3": float(stats.poisson.sf(2, e)),
                 "P_N_gt_3": float(stats.poisson.sf(3, e))}
    lo, hi = stats.chi2.ppf(0.025, 6) / 2, stats.chi2.ppf(0.975, 8) / 2
    margin_e = 0.24
    b["N3_exact_poisson_ci"] = {"mu_lo": lo, "mu_hi": hi,
                                "p0_lo": max(0.0, (lo - margin_e) / 168),
                                "p0_mle": (3 - margin_e) / 168,
                                "p0_hi": (hi - margin_e) / 168}
    lo1, hi1 = stats.chi2.ppf(0.025, 2) / 2, stats.chi2.ppf(0.975, 4) / 2
    b["N1_nonU832_poisson_ci"] = {"mu_lo": lo1, "mu_hi": hi1,
                                  "p0_hi": (hi1 - margin_e) / 168}
    res["B_G1_boundary"] = b

    # ---------------- C held-out design table (independent clusters, 1 line each)
    m_line = 0.24 / 168
    c_tab = {}
    for n in [100, 140, 168, 250, 400]:
        for p0 in [0.0, 0.002, 0.005, 0.01, 0.017]:
            p = m_line + p0
            k = 0
            while stats.binom.sf(k, n, p) > 0.05:
                k += 1
            fpr = float(stats.binom.sf(k, n, p))
            # MDE80: defect fraction pi with q = 1 on top of the null
            pis = np.linspace(0, 0.3, 3001)
            pw = stats.binom.sf(k, n, 1 - (1 - pis) * (1 - p))
            idx = np.argmax(pw >= 0.8)
            mde = float(pis[idx]) if pw[idx] >= 0.8 else None
            pw2 = float(stats.binom.sf(k, n, 1 - (1 - 0.02) * (1 - p)))
            c_tab[f"n{n}|p0{p0}"] = {"k": k, "fpr": fpr, "mde80_pi": mde,
                                     "power_pi0.02": pw2,
                                     "mde80_clusters": None if mde is None else mde * n}
    res["C_heldout_table"] = c_tab

    # ---------------- D remaining pool
    rows = list(csv.DictReader(POOL_CSV.open(encoding="utf-8")))
    g1 = json.loads(G1_JSON.read_text(encoding="utf-8"))
    used7 = set()
    off_by_family = {}
    for ln in g1["lines"]:
        j = ln["job"]
        t = j["twin"]
        ck = (t["level"], float(t["fs_kN"]), t["timing"], t["leg"], t["event"])
        used7.add(ck + (float(j["offset_s"]),))
        if t["event"] == "RE1bF" and t["timing"] == "ready":
            fam = f'{t["level"]}-{"front" if t["leg"] in ("FL", "FR") else "rear"}'
            off_by_family.setdefault(fam, {}).setdefault(str(j["offset_s"]), 0)
            off_by_family[fam][str(j["offset_s"])] += 1
    clusters = {}
    for r in rows:
        ck = (r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"])
        off = float(r["offset_s"])
        d = clusters.setdefault(ck, {"n_offsets": int(r["n_offsets"]), "free_pass": 0,
                                     "free_any": 0})
        if r["used_ed6"] == "True" or (ck + (off,)) in used7:
            continue
        d["free_any"] += 1
        if r["v0_pass"] == "True":
            d["free_pass"] += 1
    n_cl = len(clusters)
    with_free = sum(1 for d in clusters.values() if d["free_pass"] > 0)
    res["D_remaining_pool"] = {
        "clusters_in_csv": n_cl,
        "g1_lines_matched": len(used7),
        "clusters_with_unused_v0_pass_offset": with_free,
        "unused_v0_pass_lines": sum(d["free_pass"] for d in clusters.values()),
        "unused_lines_any": sum(d["free_any"] for d in clusters.values()),
        "g1_RE1bF_ready_offsets_by_family": off_by_family,
        "note": "csv rows = pool after ed6 (b); ed6 grid offsets flagged used_ed6",
    }

    # ---------------- E n_eff
    e = {}
    for icc in [0.0, 0.5, 0.8, 0.95, 0.99]:
        for m in [1, 2, 4]:
            e[f"icc{icc}|m{m}"] = {"deff": 1 + (m - 1) * icc,
                                   "n_eff_per_100_rows": 100 * m / (1 + (m - 1) * icc)}
    res["E_neff"] = e

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "s1_review.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    lines = []
    for sec, val in res.items():
        lines.append(f"== {sec}")
        if isinstance(val, dict):
            for kk, vv in val.items():
                lines.append(f"{kk}: {json.dumps(vv)}")
        else:
            lines.append(str(val))
    (OUT / "s1_review.txt").write_text("\n".join(lines), encoding="utf-8")
    ok = abs(res["A1_check"]["mc_rho0.5_c2.8"] - 0.0325) < 4 * 0.0009 + 0.001 and \
        abs(res["A1_check"]["mc_rho1_c2.8"] - res["A1_check"]["rho1_analytic_c2.8"]) < 0.01 and \
        abs(res["A2_check_quad_rho0.5_c2.8"]["quad"]
            - res["A2_check_quad_rho0.5_c2.8"]["grid"]) < 1e-4 and \
        abs(res["A2_check_rho0_analytic"]
            - a2["rho0.0|c2.8"]["p_s7_other_phase_fail_given_seen_fail"]) < 1e-6
    print(json.dumps({"status": "ok" if ok else "self_check_failed", "out": str(OUT)}))


if __name__ == "__main__":
    main()
