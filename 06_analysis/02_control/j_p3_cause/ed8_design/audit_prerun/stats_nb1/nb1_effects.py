"""Ed. 8 NB-1 statistical effects (stats-design-expert, review mode). Exact sums, no Monte Carlo.

Rule (sealed S8-R 7.4-7.5, re-implemented here from the rule text, not imported):
  N stop: one-sided 95 % Clopper-Pearson upper of x_AA/n_AA > 0.025, or n_AA = 0.
  k_N: least k with P(BetaBin(n_N, x_AA + 0.5, n_AA - x_AA + 0.5) > k) <= 0.025.
  G' fail: F > k_N, F ~ Bin(n_N, p_true) (independent units).
Model:
  A/A failures x_AA = Bin(n_AA - m_s, p0) + Bin(m_s, p_s)   (m_s shape-different pairs, Q-3)
  G' null rate p_true = p0 + q                                (q = J9/J11-only rate invisible to A/A, Q-1)
Usage: nb1_effects.py <out.json>
"""
import json
import sys
from functools import lru_cache

import numpy as np
from scipy import stats

ALPHA = 0.025
CP_LIMIT = 0.025


@lru_cache(maxsize=None)
def k_of(n, x, naa):
    a, b = x + 0.5, naa - x + 0.5
    sf = stats.betabinom.sf(np.arange(n + 1), n, a, b)  # P(X > k)
    return int(np.argmax(sf <= ALPHA))


@lru_cache(maxsize=None)
def cp_upper(x, n):
    if n == 0:
        return 1.0
    if x >= n:
        return 1.0
    return float(stats.beta.ppf(0.95, x + 1, n - x))


def is_stop(x, naa):
    return naa == 0 or cp_upper(x, naa) > CP_LIMIT


def pmf_x(naa, p0, m_s=0, p_s=None):
    a = stats.binom.pmf(np.arange(naa - m_s + 1), naa - m_s, p0)
    if m_s:
        b = stats.binom.pmf(np.arange(m_s + 1), m_s, p_s)
        a = np.convolve(a, b)
    return a


def rule_probs(n, naa, p0, q=0.0, m_s=0, p_s=None, delta=0.02):
    pm = pmf_x(naa, p0, m_s, p_s)
    stop = fail0 = power = 0.0
    ek = 0.0
    for x, w in enumerate(pm):
        if w < 1e-15:
            continue
        if is_stop(x, naa):
            stop += w
            continue
        k = k_of(n, x, naa)
        ek += w * k
        fail0 += w * stats.binom.sf(k, n, p0 + q)
        power += w * stats.binom.sf(k, n, p0 + q + delta)
    return {"p_stop": stop, "false_fail": fail0, "power_delta": power,
            "E_k_given_go": ek / max(1e-15, 1 - stop), "E_x_AA": float(np.dot(np.arange(len(pm)), pm))}


def mde80(n, k):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if stats.binom.sf(k, n, mid) >= 0.8:
            hi = mid
        else:
            lo = mid
    return hi


def ub0(n):
    return 1 - 0.05 ** (1 / n)


def main():
    out = {"model": __doc__, "checks": {}, "q1": [], "q3": [], "q1q3": [], "q4": {}}
    # self-checks against published values (stats_t8_check.md:29-33, spec 7.5:315)
    chk = out["checks"]
    chk["k_n300_x0_1_2"] = [k_of(300, x, 300) for x in (0, 1, 2)]       # expect 3/6/8
    chk["mde_n300_x0_1_2"] = [round(100 * mde80(300, k_of(300, x, 300)), 3) for x in (0, 1, 2)]  # 1.8/3.0/3.8
    chk["mde_n200_x0_1_2"] = [round(100 * mde80(200, k_of(200, x, 200)), 3) for x in (0, 1, 2)]  # 2.7/4.5/5.6
    r = rule_probs(300, 300, 0.002)
    chk["n300_naa300_p0.002"] = {"p_stop_pct": round(100 * r["p_stop"], 2),
                                 "false_fail_pct": round(100 * r["false_fail"], 2)}  # expect 2.3 / 0.18
    r = rule_probs(300, 285, 0.005)
    chk["n300_naa285_p0.005"] = {"p_stop_pct": round(100 * r["p_stop"], 1),
                                 "false_fail_pct": round(100 * r["false_fail"], 2)}  # expect 17.2 / 1.59
    chk["cp_stop_min_naa_x0_1_2_3"] = [next(n for n in range(1, 1000) if not is_stop(x, n)) for x in range(4)]
    chk["ok"] = (chk["k_n300_x0_1_2"] == [3, 6, 8]
                 and [round(v, 1) for v in chk["mde_n300_x0_1_2"]] == [1.8, 3.0, 3.8]
                 and [round(v, 1) for v in chk["mde_n200_x0_1_2"]] == [2.7, 4.5, 5.6]
                 and chk["n300_naa300_p0.002"] == {"p_stop_pct": 2.3, "false_fail_pct": 0.18}
                 and chk["cp_stop_min_naa_x0_1_2_3"] == [119, 188, 250, 308])

    # q anchors: one-sided 95 % upper of 0/n for stored VB-family evidence (see report)
    q_anchor = {"0": 0.0, "ub_lines_2679": ub0(2679), "ub_R12grid_lines_363": ub0(363),
                "ub_grid_clusters_192": ub0(192), "q_0.005": 0.005}
    out["q_anchor"] = q_anchor
    for n, naa in ((300, 300), (300, 285), (300, 270), (250, 240)):
        for p0 in (0.0005, 0.001, 0.002, 0.005):
            base = rule_probs(n, naa, p0)
            for name, q in q_anchor.items():
                r = rule_probs(n, naa, p0, q=q)
                out["q1"].append({"n_N": n, "n_AA": naa, "p0_AA": p0, "q_name": name, "q": q,
                                  "p_stop": r["p_stop"], "false_fail": r["false_fail"],
                                  "d_false_fail": r["false_fail"] - base["false_fail"],
                                  "power_+2pp": r["power_delta"],
                                  "d_power": r["power_delta"] - base["power_delta"]})
    # Q-3: shape-different A/A pairs in N (m_s ~ 21 of ~27 b_shape first-candidate pairs, rest E)
    for n, naa in ((300, 300), (300, 285)):
        for p0 in (0.001, 0.002, 0.005):
            base = rule_probs(n, naa, p0)
            for m_s in (21, 27):
                for p_s in (p0, 0.01, 0.02, 0.05, 0.10):
                    r = rule_probs(n, naa, p0, m_s=m_s, p_s=p_s)
                    out["q3"].append({"n_N": n, "n_AA": naa, "p0": p0, "m_s": m_s, "p_s": p_s,
                                      "E_x_AA": r["E_x_AA"], "p_stop": r["p_stop"],
                                      "d_p_stop": r["p_stop"] - base["p_stop"],
                                      "false_fail": r["false_fail"],
                                      "d_false_fail": r["false_fail"] - base["false_fail"],
                                      "power_+2pp": r["power_delta"],
                                      "d_power": r["power_delta"] - base["power_delta"],
                                      "E_k_given_go": r["E_k_given_go"]})
    # Q-1 x Q-3 combined
    for p0 in (0.001, 0.002, 0.005):
        base = rule_probs(300, 285, p0)
        for q in (0.0, ub0(2679), ub0(363)):
            for p_s in (p0, 0.02, 0.05):
                r = rule_probs(300, 285, p0, q=q, m_s=21, p_s=p_s)
                out["q1q3"].append({"n_N": 300, "n_AA": 285, "p0": p0, "q": q, "m_s": 21, "p_s": p_s,
                                    "p_stop": r["p_stop"], "false_fail": r["false_fail"],
                                    "d_false_fail": r["false_fail"] - base["false_fail"],
                                    "power_+2pp": r["power_delta"],
                                    "d_power": r["power_delta"] - base["power_delta"]})
    # Q-4: k / stop step structure in n_AA and x_AA; per-pair occurrence bound
    q4 = out["q4"]
    q4["k_by_naa"] = {str(n): {str(naa): [("stop" if is_stop(x, naa) else k_of(n, x, naa)) for x in range(4)]
                               for naa in (300, 299, 298, 297, 295, 290, 285, 280, 275, 270, 260, 250)}
                      for n in (300, 250)}
    p_line = ub0(3339)
    q4["per_line_ub95_0_of_3339"] = p_line
    q4["per_pair_ub95"] = 1 - (1 - p_line) ** 2
    q4["p_any_in_300_pairs_at_ub"] = 1 - (1 - p_line) ** 600
    # informative drop: a pair that would have failed is dropped -> x - 1, n_AA - 1
    rows = []
    for naa in (300, 285):
        for x in (1, 2, 3):
            rows.append({"n_N": 300, "n_AA_true": naa, "x_true": x,
                         "count_as_fail": "stop" if is_stop(x, naa) else k_of(300, x, naa),
                         "drop_informative": "stop" if is_stop(x - 1, naa - 1) else k_of(300, x - 1, naa - 1),
                         "drop_mcar_if_pair_passed": "stop" if is_stop(x, naa - 1) else k_of(300, x, naa - 1)})
    q4["drop_vs_count"] = rows
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"status": "ok" if chk["ok"] else "selfcheck_failed", "checks_ok": chk["ok"]}))


if __name__ == "__main__":
    main()
