"""Q2 opportunity strata, Q3 cluster-bootstrap coverage, Q4 identity-sample detection.

Q2b: check-run E-2 rate by R0 probe attitude change stratum (>0.10, 0.07-0.10, <=0.07 deg).
Q3 : coverage of percentile cluster bootstrap 95 % CI for median and P90 of a clustered,
     skewed delay (gamma shape 2, scale 10 s; cluster effect share ICC), vs a row bootstrap.
     Self-check: ICC = 0, m = 1 should give near-nominal coverage for the median at large C.
Q4 : probability that a simple random identity sample of n rows from N detects >= 1 changed row
     when D rows changed (hypergeometric), and D needed for 95 % detection.
Seed 20261114.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

SEED = 20261114
rng = np.random.default_rng(SEED)
inp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out: dict = {"seed": SEED}

E2 = {
    "A-v5": {("S5", "VB", 0.8, 0.002), ("S5", "VB", 0.8, 0.003)},
    "A2": {("S3", "VB", 0.85, 0.0), ("S3", "VB", 0.85, 0.002), ("S5", "VB", 0.8, 0.001),
           ("S5", "VB", 0.8, 0.002), ("S4", "VB", None, 0.0)},
}
q2b = {}
for arm in ("A-v5", "A2"):
    rows = [r for r in inp["check"][arm]["rows"] if r["setting"] == "VB" and r["t_ready_A"] is not None]
    strata = {"gt0.10": lambda x: x > 0.10, "0.07-0.10": lambda x: 0.07 < x <= 0.10, "le0.07": lambda x: x <= 0.07}
    res = {}
    for name, f in strata.items():
        sel = [r for r in rows if r["probe_att_change_R0"] is not None and f(r["probe_att_change_R0"])]
        ev = sum(1 for r in sel if (r["case"], r["setting"], r["eta"], r["eps"]) in E2[arm])
        res[name] = {"rows": len(sel), "events": ev, "clusters": len({r["cluster"] for r in sel})}
    q2b[arm] = res
out["Q2b_check_strata"] = q2b


# ---------- Q3 ----------
def gen(C, m, icc, n_rep):
    """Delay = cluster effect + row noise, both gamma-ish; total var fixed, share icc to cluster."""
    shape, scale = 2.0, 10.0
    var = shape * scale ** 2
    vc, vr = icc * var, (1 - icc) * var
    # cluster effects from gamma with variance vc, row noise normal with variance vr
    if vc > 0:
        k_c = shape
        th_c = np.sqrt(vc / k_c)
        ce = rng.gamma(k_c, th_c, (n_rep, C, 1))
    else:
        ce = np.zeros((n_rep, C, 1))
    rn = rng.normal(0, np.sqrt(vr), (n_rep, C, m)) if vr > 0 else np.zeros((n_rep, C, m))
    return ce + rn


def true_quantiles(m, icc):
    big = gen(4000, m, icc, 25).reshape(-1)
    return float(np.median(big)), float(np.percentile(big, 90))


def coverage(C, m, icc, n_rep, B):
    tmed, tp90 = true_quantiles(m, icc)
    data = gen(C, m, icc, n_rep)
    cov = {"cl_med": 0, "cl_p90": 0, "row_med": 0, "row_p90": 0}
    widths = {"cl_med": [], "row_med": []}
    for r in range(n_rep):
        x = data[r]  # C x m
        idx = rng.integers(0, C, (B, C))
        res = x[idx].reshape(B, -1)
        med = np.median(res, axis=1)
        p90 = np.percentile(res, 90, axis=1)
        lo, hi = np.percentile(med, [2.5, 97.5])
        cov["cl_med"] += lo <= tmed <= hi
        widths["cl_med"].append(hi - lo)
        lo, hi = np.percentile(p90, [2.5, 97.5])
        cov["cl_p90"] += lo <= tp90 <= hi
        flat = x.reshape(-1)
        ridx = rng.integers(0, flat.size, (B, flat.size))
        rr = flat[ridx]
        med = np.median(rr, axis=1)
        p90 = np.percentile(rr, 90, axis=1)
        lo, hi = np.percentile(med, [2.5, 97.5])
        cov["row_med"] += lo <= tmed <= hi
        widths["row_med"].append(hi - lo)
        lo, hi = np.percentile(p90, [2.5, 97.5])
        cov["row_p90"] += lo <= tp90 <= hi
    res = {k: v / n_rep for k, v in cov.items()}
    res["mcse"] = float(np.sqrt(0.95 * 0.05 / n_rep))
    res["width_ratio_row_over_cluster_med"] = float(np.mean(widths["row_med"]) / np.mean(widths["cl_med"]))
    return res


q3 = {}
plan = [(200, 1, 0.0, 400, 1000, "selfcheck_C200_m1_icc0"),
        (13, 3, 0.8, 600, 1000, "C13_m3_icc0.8(check-run VB)"),
        (24, 1, 0.0, 600, 1000, "C24_m1(Chrono L2b rows)"),
        (50, 2, 0.8, 600, 1000, "C50_m2_icc0.8"),
        (217, 2, 0.8, 300, 1000, "C217_m2_icc0.8(D-1 per setting)"),
        (217, 2, 0.99, 300, 1000, "C217_m2_icc0.99(436.8 eps ICC)"),
        (340, 3, 0.9, 200, 1000, "C340_m3_icc0.9(U-3 per setting)")]
for C, m, icc, n_rep, B, name in plan:
    q3[name] = coverage(C, m, icc, n_rep, B)
out["Q3_bootstrap_coverage"] = q3

# ---------- Q4 ----------
q4 = {}
for N, n, label in [(4064, 50, "all harness rows, n=50"), (868, 10, "D-1, n=10"), (2228, 30, "U-3, n=30"),
                    (968, 10, "U-6, n=10"), (4064, 150, "all, n=150"), (35, 1, "Chrono, n=1"), (35, 3, "Chrono, n=3")]:
    rec = {}
    for frac in (0.01, 0.02, 0.05, 0.10, 0.25):
        D = max(1, int(round(frac * N)))
        rec[f"detect@{frac:g}"] = float(1 - stats.hypergeom.pmf(0, N, D, n))
    Ds = np.arange(1, N + 1)
    p = 1 - stats.hypergeom.pmf(0, N, Ds, n)
    D95 = int(Ds[np.argmax(p >= 0.95)]) if (p >= 0.95).any() else None
    rec["D_for_95pct"] = D95
    rec["frac_for_95pct"] = (D95 / N) if D95 else None
    q4[label] = rec
out["Q4_identity_detection"] = q4

Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ok")
