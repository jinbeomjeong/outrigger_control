"""Ed. 8 T8 review (stats-design-expert): two interpretation checks of the T8 WIP rules module
against the sealed spec (jp3_remedy_spec_v8_rules.md 7.3 .. 7.5).

Q1  MDE80 - does "least p with P(Bin(n, p) > k) >= 0.8" (T8 `minimum_detectable_rate`) reproduce
    the published 7.5 numbers (N n 200: 2.7 / 4.5 / 5.6 %, n 300: 1.8 / 3.0 / 3.8 % for x_AA 0/1/2;
    E k 1: n 16 17.6 %, n 28 10.3 %)? Published values were made with k = Jeffreys k_N at n_AA = n_N
    (audit_preseal/stats_final/f4_checks.py lines 5-6, 35-51). Here: independent scipy
    re-implementation, the T8 functions (loaded from an exported copy of commit 01b5cc2c, used
    only as the object under test), a grid agreement check of k and MDE80, and the dependence of
    k_N / MDE80 on n_AA < n_N.
Q2  A/A pairing - exact (analytic, independent units) consequences of n_AA loss: N A/A stop
    probability (CP95 > 0.025), k_N, null false failure and power, for n_AA values that the
    alternative readings would give (same-hash exclusion without moving on vs moving on; original
    layer vs merged layer pairing).

Usage: python -I -B t8_mde_aa_check.py <t8_rules_copy.py> <out_folder>
All numbers are analytic (scipy / exact sums); nothing is simulated, no result file is read.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy import optimize, stats

RULES = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("t8_rules_copy", RULES)
t8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t8)

ALPHA = 0.025
CP_STOP = 0.025


def k_pred(n, x, naa, alpha=ALPHA):
    d = stats.betabinom(n, x + 0.5, naa - x + 0.5)
    k = 0
    while d.sf(k) > alpha:
        k += 1
    return k


def mde(n, k, power=0.8):
    if n <= k:
        return None
    return float(optimize.brentq(lambda p: stats.binom.sf(k, n, p) - power, 1e-12, 1 - 1e-12,
                                 xtol=1e-14))


def cp_upper(x, n, a=0.05):
    return 1.0 if x >= n else float(stats.beta.ppf(1 - a, x + 1, n - x))


res = {"published": {"N": {"200": [2.7, 4.5, 5.6], "300": [1.8, 3.0, 3.8]},
                     "E": {"16": 17.6, "28": 10.3}},
       "source_published": "jp3_remedy_spec_v8_rules.md:315; f4_checks.py:5-6,35-51"}

# ---- Q1 A: reproduction at n_AA = n_N
repro = {}
for n in (200, 300):
    for i, x in enumerate((0, 1, 2)):
        k_s = k_pred(n, x, n)
        k_t = t8.jeffreys_predictive_k(n, x, n)
        m_s = mde(n, k_s)
        m_t = t8.minimum_detectable_rate(n, k_t)
        pub = res["published"]["N"][str(n)][i]
        repro[f"N_n{n}_x{x}"] = {"k_scipy": k_s, "k_t8": k_t, "mde80_scipy_pct": round(100 * m_s, 3),
                                 "mde80_t8_pct": round(100 * m_t, 3), "published_pct": pub,
                                 "match_1dp": round(100 * m_t, 1) == pub}
for n in (16, 28):
    m_s = mde(n, 1)
    m_t = t8.minimum_detectable_rate(n, t8.K_E)
    pub = res["published"]["E"][str(n)]
    repro[f"E_n{n}_k1"] = {"mde80_scipy_pct": round(100 * m_s, 3), "mde80_t8_pct": round(100 * m_t, 3),
                           "published_pct": pub, "match_1dp": round(100 * m_t, 1) == pub}
res["q1_reproduction"] = repro

# ---- Q1 B: the alternative reading "MDE80 from a k without Jeffreys" (k from CP95 upper + Bin, old draft)
alt = {}
for n in (200, 300):
    for x in (0, 1, 2):
        pub_p = cp_upper(x, n)  # draft: Bin(n, CP95 upper), alpha 0.05 tail
        k_cp = int(stats.binom.ppf(0.95, n, pub_p))
        alt[f"n{n}_x{x}"] = {"k_cp_draft": k_cp, "mde80_pct": round(100 * mde(n, k_cp), 2)}
res["q1_alt_reading_cp_draft_k"] = alt

# ---- Q1 C: grid agreement T8 vs scipy (k and MDE80)
mism_k, mism_m, cnt = [], [], 0
max_dm = 0.0
for n in range(150, 341, 10):
    for naa in range(60, 341, 20):
        for x in range(0, 5):
            if x > naa:
                continue
            ks = k_pred(n, x, naa)
            kt = t8.jeffreys_predictive_k(n, x, naa)
            cnt += 1
            if ks != kt:
                mism_k.append([n, naa, x, ks, kt])
            ms, mt = mde(n, kt), t8.minimum_detectable_rate(n, kt)
            dm = abs(ms - mt)
            max_dm = max(max_dm, dm)
            if dm > 1e-9:
                mism_m.append([n, naa, x, ms, mt])
for n in range(2, 41):
    ms, mt = mde(n, 1), t8.minimum_detectable_rate(n, 1)
    cnt += 1
    max_dm = max(max_dm, abs(ms - mt))
res["q1_grid_agreement"] = {"cases": cnt, "k_mismatch": mism_k, "mde_mismatch": mism_m,
                            "max_abs_mde_diff": max_dm}
# CP upper agreement
cp_m = []
for naa in range(50, 400, 25):
    for x in range(0, 6):
        a, b = cp_upper(x, naa), t8.clopper_pearson_upper(x, naa)
        if abs(a - b) > 1e-9:
            cp_m.append([x, naa, a, b])
res["q1_cp_agreement_mismatch"] = cp_m

# ---- Q1 D: k_N and MDE80 when n_AA < n_N
dep = {}
for n in (200, 250, 300):
    for frac in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
        naa = int(round(frac * n))
        row = {}
        for x in (0, 1, 2, 3):
            k = k_pred(n, x, naa)
            row[f"x{x}"] = {"k": k, "mde80_pct": round(100 * mde(n, k), 2),
                            "cp95_stop": cp_upper(x, naa) > CP_STOP}
        dep[f"n{n}_naa{naa}"] = row
res["q1_naa_dependence"] = dep

# ---- Q2: exact operating characteristics as a function of n_AA (independent units)


def oc(n_n, naa, p_aa, p_true):
    """Exact over x_AA ~ Bin(naa, p_aa): P(stop), P(judged fail | p_true), E[k | not stop]."""
    xs = np.arange(0, naa + 1)
    px = stats.binom.pmf(xs, naa, p_aa)
    p_stop = p_fail = ek = p_go = 0.0
    for x, w in zip(xs, px):
        if w < 1e-14:
            continue
        if cp_upper(int(x), naa) > CP_STOP:
            p_stop += w
            continue
        k = k_pred(n_n, int(x), naa)
        p_go += w
        ek += w * k
        p_fail += w * stats.binom.sf(k, n_n, p_true)
    return {"p_stop": round(p_stop, 4), "p_fail_judged": round(p_fail, 4),
            "p_fail_given_go": round(p_fail / p_go, 4) if p_go else None,
            "E_k_given_go": round(ek / p_go, 3) if p_go else None}


q2 = {}
n_n = 300
for naa in (300, 285, 270, 255, 240, 225, 210):
    row = {}
    for p0 in (0.001, 0.002, 0.005):
        row[f"p0_{p0}"] = {"null": oc(n_n, naa, p0, p0),
                           "null_3x": oc(n_n, naa, p0, 3 * p0),
                           "power_p0+2pp": oc(n_n, naa, p0, p0 + 0.02)}
    q2[f"nN{n_n}_naa{naa}"] = row
res["q2_oc_by_naa"] = q2

# stop threshold n_AA per x
thr = {}
for x in range(0, 5):
    m = x + 1
    while cp_upper(x, m) > CP_STOP:
        m += 1
    thr[str(x)] = m
res["q2_cp_min_naa_by_x"] = thr

# same-hash exclusion scenarios: N base-pass slots n0 = 300, fraction h of slots whose first
# same-layer candidate is a same-hash pair. Reading A (T8): slot dropped. Reading B (move on):
# recovered when a later same-layer candidate exists and is not same-hash. Two mechanisms:
# systematic (offset not effective -> every candidate same hash, recover 0) and accidental
# (independent, recover with prob (1 - h) per further candidate, at most 2 more tries).
scen = {}
n0 = 300
for h in (0.0, 0.02, 0.05, 0.10, 0.20):
    naa_a = n0 * (1 - h)
    rec_acc = h * ((1 - h) + h * (1 - h))  # second or third candidate usable (same layer assumed)
    scen[f"h{h}"] = {"naa_T8": round(naa_a, 1), "naa_moveon_systematic": round(naa_a, 1),
                     "naa_moveon_accidental": round(naa_a + n0 * rec_acc, 1),
                     "gain_moveon_max": round(n0 * rec_acc, 1)}
res["q2_same_hash_scenarios"] = scen

# merged case: reading C (after E merged into N every candidate is "same layer"). Only original
# E slots can cross; n_E < 16 base-pass slots -> at most 15 extra A/A pairs. Effect bound:
merged = {}
for n_nm in (200, 230, 260):
    for naa in (n_nm - 30, n_nm - 15):
        r = {}
        for x in (0, 1, 2):
            r[f"x{x}"] = {"k_T8": k_pred(n_nm, x, naa), "k_plus15": k_pred(n_nm, x, naa + 15),
                          "stop_T8": cp_upper(x, naa) > CP_STOP,
                          "stop_plus15": cp_upper(x, naa + 15) > CP_STOP}
        merged[f"nN{n_nm}_naa{naa}"] = r
res["q2_merged_reading_bound"] = merged

(OUT / "t8_mde_aa_check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False),
                                          encoding="utf-8")
ok = (all(v["match_1dp"] for v in repro.values()) and not mism_k and not mism_m and not cp_m)
print(json.dumps({"status": "ok" if ok else "mismatch"}))
