"""Edition-9 (436.9) implementation round 1: statistical checks (review mode, not a judgement).

Inputs (design files only; no stage-5 jsonl, no judge smoke slot contents):
  - control harness injection detail: ed9_design/control_d1_rule/injection_detail.csv
  - published counts from ed9_design/d1_prerun/impl_report.md 5절 table (typed below)

Sections
  Q1  stop probability of zero-allowance comparisons that would keep the J7 closed list as failures
  Q5  cluster (trace label) bootstrap of the harness C-m margins: C-m - D1' (transient) and
      C0 - C-m outside k1 (P9-D1-5 / P9-D1-6 definitions, control report 2.3)
  Q6  ed9 A/A floor scenarios on the same model path: CP95, k (Jeffreys predictive), MDE80, false failure
      plus probability of extra failures from changed / new lines (model, [estimate])

Usage: python -I -B ed9_impl_check.py <injection_detail.csv> <out_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SEED = 20261114
ALPHA = 0.025
P0_UB_MAX = 0.025
B_BOOT = 10000


def cp_upper(x, n, conf=0.95):
    if x >= n:
        return 1.0
    return float(stats.beta.ppf(conf, x + 1, n - x))


def k_pp(n, x, naa, alpha=ALPHA):
    """Smallest k with P(BetaBin(n, x + 0.5, naa - x + 0.5) > k) <= alpha (ed8 rule 7.5 form)."""
    dist = stats.betabinom(n, x + 0.5, naa - x + 0.5)
    k = 0
    while dist.sf(k) > alpha:
        k += 1
    return k


def mde80(n, k, p0=0.0):
    lo, hi = 0.0, 1.0 - p0
    for _ in range(60):
        mid = (lo + hi) / 2
        if stats.binom.sf(k, n, p0 + mid) >= 0.8:
            hi = mid
        else:
            lo = mid
    return hi


def ff(n, k, p):
    return float(stats.binom.sf(k, n, min(p, 1.0)))


# ---------------- Q1 ----------------
def q1():
    out = []
    for m, what in ((100, "C-J (i) VBN lines"), (184, "C-S judged 4 settings units"),
                    (288, "C-J (ii) LSN1-4 lines (4 x 72)"), (388, "C-J all lines")):
        row = {"units": m, "what": what}
        for p in (0.0005, 0.001, 0.002, 0.005, 0.01, 0.026):
            row[f"p_stop_flip{p}"] = 1.0 - (1.0 - p) ** m
        out.append(row)
    # flip rate that gives 5 % / 50 % stop
    inv = {}
    for m in (100, 184, 288, 388):
        inv[m] = {"p_for_5pct": 1 - 0.95 ** (1 / m), "p_for_50pct": 1 - 0.5 ** (1 / m)}
    return {"table": out, "inverse": inv,
            "note": "binomial, independent units; ed8 G' A/A list-warning flip rate 8/310 = 2.6 % is the "
                    "only same-mechanism anchor (different population) [estimate]"}


# ---------------- Q5 ----------------
def q5(detail_path):
    df = pd.read_csv(detail_path)
    cand = df[df["threshold_kN"].notna() & (df["kind"] == "transient")].copy()
    cand["k1"] = (cand["t_minus_event_s"] >= 0.1) & (cand["t_minus_event_s"] < 0.2)
    rng = np.random.default_rng(SEED)
    labels = np.array(sorted(cand["label"].unique()))
    res = {"n_labels": int(len(labels)), "B": B_BOOT, "seed": SEED, "rows": []}
    # self-check: reproduce control report 2.3 table
    check = {}
    for jb, g in cand.groupby("jump_bar"):
        check[str(jb)] = {"n": int(len(g)), "C0": round(g["C0"].mean() * 100, 1),
                          "Cm": round(g["Cm"].mean() * 100, 1), "D1p": round(g["D1p"].mean() * 100, 1)}
    res["reproduce_2_3"] = check
    expected = {"-150.0": (4206, 98.3, 97.9, 90.2), "-100.0": (2313, 88.5, 86.6, 81.0),
                "100.0": (2450, 88.4, 83.6, 82.3), "150.0": (4251, 99.4, 99.3, 90.5)}
    ok = all(check[k]["n"] == v[0] and abs(check[k]["C0"] - v[1]) < 0.051 and abs(check[k]["Cm"] - v[2]) < 0.051
             and abs(check[k]["D1p"] - v[3]) < 0.051 for k, v in expected.items())
    res["self_check_reproduce"] = ok
    for jb, g in cand.groupby("jump_bar"):
        # per-label sums
        agg_all = g.groupby("label")[["C0", "Cm", "D1p"]].agg(["sum", "count"])
        out_k1 = g[~g["k1"]]
        agg_out = out_k1.groupby("label")[["C0", "Cm"]].agg(["sum", "count"])
        la = agg_all.index.to_numpy()
        lo = agg_out.index.to_numpy()
        a_cm = agg_all[("Cm", "sum")].to_numpy(float)
        a_d1 = agg_all[("D1p", "sum")].to_numpy(float)
        a_n = agg_all[("Cm", "count")].to_numpy(float)
        o_c0 = agg_out[("C0", "sum")].to_numpy(float)
        o_cm = agg_out[("Cm", "sum")].to_numpy(float)
        o_n = agg_out[("Cm", "count")].to_numpy(float)
        late = g[(g["t_minus_event_s"] >= 0.3) & (g["t_minus_event_s"] < 2.5)]
        agg_late = late.groupby("label")[["C0", "Cm"]].agg(["sum", "count"])
        l_c0 = agg_late[("C0", "sum")].to_numpy(float)
        l_cm = agg_late[("Cm", "sum")].to_numpy(float)
        l_n = agg_late[("Cm", "count")].to_numpy(float)

        m_pt = _diff_ratio(a_cm, a_d1, a_n, np.arange(len(la)))
        l_pt = _diff_ratio(o_c0, o_cm, o_n, np.arange(len(lo)))
        ll_pt = _diff_ratio(l_c0, l_cm, l_n, np.arange(len(l_n)))
        mb = np.empty(B_BOOT)
        lb = np.empty(B_BOOT)
        llb = np.empty(B_BOOT)
        for b in range(B_BOOT):
            mb[b] = _diff_ratio(a_cm, a_d1, a_n, rng.integers(0, len(la), len(la)))
            lb[b] = _diff_ratio(o_c0, o_cm, o_n, rng.integers(0, len(lo), len(lo)))
            llb[b] = _diff_ratio(l_c0, l_cm, l_n, rng.integers(0, len(l_n), len(l_n)))
        res["rows"].append({
            "jump_bar": float(jb), "n_transient": int(len(g)), "n_labels_with_candidates": int(len(la)),
            "margin_cm_minus_d1p_pp": m_pt * 100,
            "margin_ci95_pp": [float(np.percentile(mb, 2.5) * 100), float(np.percentile(mb, 97.5) * 100)],
            "p_boot_margin_below_0": float((mb < 0).mean()),
            "n_outside_k1": int(len(out_k1)), "n_labels_outside_k1": int(len(lo)),
            "loss_c0_minus_cm_outside_k1_pp": l_pt * 100,
            "loss_ci95_pp": [float(np.percentile(lb, 2.5) * 100), float(np.percentile(lb, 97.5) * 100)],
            "p_boot_loss_above_3pp": float((lb > 0.03).mean()),
            "candidates_lost_outside_k1": int(out_k1["C0"].sum() - out_k1["Cm"].sum()),
            "n_late": int(len(late)), "loss_late_band_pp": ll_pt * 100,
            "loss_late_ci95_pp": [float(np.percentile(llb, 2.5) * 100), float(np.percentile(llb, 97.5) * 100)],
            "p_boot_late_loss_above_3pp": float((llb > 0.03).mean()),
            "candidates_lost_late": int(late["C0"].sum() - late["Cm"].sum()),
        })
    # R2 Chrono ML (aggregate only; no band split in ml_inject_cm.csv) typed from impl_report 7절 / csv
    r2 = {"-150": (1004, 991, 1004, 1003), "-100": (537, 502, 527, 524),
          "+100": (582, 542, 560, 556), "+150": (1011, 993, 1011, 1011)}
    r2_rows = []
    for jb, (n, d1p, c0, cm) in r2.items():
        lost = c0 - cm
        r2_rows.append({"jump_bar": jb, "n_transient": n, "margin_cm_minus_d1p_count": cm - d1p,
                        "margin_pp": (cm - d1p) / n * 100, "c0_minus_cm_count": lost,
                        "c0_minus_cm_pp_all_transient": lost / n * 100,
                        "wilson95_upper_loss_pp": float(_wilson_upper(lost, n) * 100)})
    res["r2_chrono_ml"] = r2_rows
    return res


def _diff_ratio(num_a, num_b, den, idx):
    """(sum a - sum b) / sum den over resampled cluster indices."""
    return (num_a[idx].sum() - num_b[idx].sum()) / den[idx].sum()


def _wilson_upper(x, n, z=1.959963984540054):
    p = x / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c + r) / den


# ---------------- Q6 ----------------
def q6():
    rows = []
    for layer, ns, xs in (("N", (306, 312, 315), (0, 1, 2, 3, 4)), ("E", (23, 24, 27), (0, 1, 2))):
        for n in ns:
            for x in xs:
                naa = n  # same-hash exclusions expected 0 (smoke counts sum to n with 7 not run)
                k = k_pp(n, x, naa)
                p0 = x / naa
                row = {"layer": layer, "n": n, "n_aa": naa, "x_aa": x, "cp95": cp_upper(x, naa),
                       "cp_stop_0.025": cp_upper(x, naa) > P0_UB_MAX, "k": k,
                       "mde80_p0_0_pp": mde80(n, k, 0.0) * 100, "mde80_floor_pp": mde80(n, k, p0) * 100}
                if x > 0:
                    row["ff_r1"] = ff(n, k, p0)
                    row["ff_r2"] = ff(n, k, 2 * p0)
                else:
                    row["ff_true0.002"] = ff(n, k, 0.002)
                    row["ff_true0.005"] = ff(n, k, 0.005)
                rows.append(row)
    # extra failures from m affected lines (changed S lines in pairs + new same-shape candidates)
    extra = []
    for m in (8, 15):
        for p in (0.0016, 0.01, 0.05, 0.1):
            extra.append({"m_lines": m, "p_fail_per_line": p,
                          "P_ge1": float(stats.binom.sf(0, m, p)), "P_ge2": float(stats.binom.sf(1, m, p)),
                          "P_ge3": float(stats.binom.sf(2, m, p))})
    return {"table": rows, "extra_from_affected_lines": extra,
            "p_floor_jeffreys_0_of_310": (0 + 0.5) / (310 + 1)}


def self_checks():
    c = {
        "cp_3_310": round(cp_upper(3, 310), 4) == 0.0248,
        "cp_11_310": round(cp_upper(11, 310), 4) == 0.0581,
        "k_310_x3": k_pp(310, 3, 310) == 10,
        "k_310_x0": k_pp(310, 0, 310) == 3,
        "mde_310_x0_k3": abs(mde80(310, 3) * 100 - 1.8) < 0.1,
        "ff_limit_large_p": ff(310, 3, 0.5) > 0.999,
    }
    return c


def main():
    detail, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    sc = self_checks()
    res = {"self_checks": sc, "q1": q1(), "q5": q5(detail), "q6": q6()}
    res["status"] = "ok" if all(sc.values()) and res["q5"]["self_check_reproduce"] else "self_check_failed"
    (out_dir / "ed9_impl_check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": res["status"], "out": str(out_dir / "ed9_impl_check.json")}))


if __name__ == "__main__":
    main()
