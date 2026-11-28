"""Ed9 (436.9) pre-R3 statistics check: cluster resampling for P9-D1-5 / P9-D1-6.

Inputs (design data, no judged-run outputs):
  argv[1] ml_inject_cm_runs.csv   R2 Chrono ML open-loop replay, one row per (population, run, jump, class, band)
  argv[2] ml_inject_cm_bands.csv  R2 totals (used only to check that the per-run file sums to it)
  argv[3] injection_detail.csv    harness trace injection rows (control_d1_rule)
  argv[4] output folder

Statistics
  margin  = (C-m flagged - D1' flagged) / candidates      (P9-D1-5, ">=" so margin 0 passes)
  loss    = (C0 flagged - C-m flagged) / candidates       (P9-D1-6, C-m is a subset of C0 so loss >= 0)
  Cluster percentile bootstrap, B = 10,000, seed 20261114, ratio of resampled sums.
  Clusters: R2 episodes -> base run (24, primary) and episode (192, sensitivity);
            R2 bases -> run (24); harness -> trace label.
  Leave-one-cluster-out (jackknife) minimum of the margin count, cluster concentration counts.
  Zero-miss rows: one-sided Clopper-Pearson 95 % upper bound at n = candidates and n = clusters.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SEED = 20261114
B = 10_000
BANDS = [("pre", -np.inf, 0.0), ("k0", 0.0, 0.1), ("k1", 0.1, 0.2), ("k2", 0.2, 0.3),
         ("late", 0.3, 2.5), ("tail", 2.5, np.inf)]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cp_upper(x, n, conf=0.95):
    if n <= 0:
        return None
    if x >= n:
        return 1.0
    return float(stats.beta.ppf(conf, x + 1, n - x))


def boot_ratio(a, b, d, rng):
    """Percentile bootstrap of (sum a - sum b) / sum d over clusters (arrays per cluster)."""
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    sd = d[idx].sum(1)
    val = (a[idx].sum(1) - b[idx].sum(1)) / np.where(sd > 0, sd, np.nan)
    return val


def summarize(g, cluster_col, rng, a_col, b_col, label):
    agg = g.groupby(cluster_col)[[a_col, b_col, "candidates"]].sum()
    agg = agg[agg["candidates"] > 0]
    a = agg[a_col].to_numpy(float)
    b = agg[b_col].to_numpy(float)
    d = agg["candidates"].to_numpy(float)
    n = d.sum()
    pt = (a.sum() - b.sum()) / n if n > 0 else None
    out = {"stat": label, "n_candidates": int(n), "n_clusters": int(len(d)),
           "count_diff": int(a.sum() - b.sum()), "point_pp": None if pt is None else pt * 100}
    if len(d) == 0:
        return out
    diff = a - b
    out["clusters_diff_neg"] = int((diff < 0).sum())
    out["clusters_diff_pos"] = int((diff > 0).sum())
    # leave-one-cluster-out minimum of the count difference
    out["jackknife_min_count_diff"] = int((diff.sum() - diff).min()) if len(d) > 1 else None
    if len(d) >= 2 and np.any(diff != 0):
        v = boot_ratio(a, b, d, rng)
        out["ci95_pp"] = [float(np.nanpercentile(v, 2.5) * 100), float(np.nanpercentile(v, 97.5) * 100)]
        out["p_boot_below_0"] = float(np.nanmean(v < 0))
        out["p_boot_above_3pp"] = float(np.nanmean(v > 0.03))
        out["boot_sd_pp"] = float(np.nanstd(v) * 100)
    else:
        out["ci95_pp"] = [out["point_pp"], out["point_pp"]] if out["point_pp"] is not None else None
        out["p_boot_below_0"] = 0.0 if (out["point_pp"] or 0) >= 0 else 1.0
        out["p_boot_above_3pp"] = 0.0 if (out["point_pp"] or 0) <= 3 else 1.0
        out["boot_sd_pp"] = 0.0
        out["degenerate"] = "all clusters have zero difference" if np.all(diff == 0) else "one cluster"
    return out


def rate_block(g, cluster_col, flag_col):
    agg = g.groupby(cluster_col)[[flag_col, "candidates"]].sum()
    agg = agg[agg["candidates"] > 0]
    n = int(agg["candidates"].sum())
    x = int(agg[flag_col].sum())
    miss = n - x
    clusters_with_miss = int((agg["candidates"] - agg[flag_col] > 0).sum())
    return {"n": n, "flagged": x, "rate": x / n if n else None, "misses": miss,
            "clusters": int(len(agg)), "clusters_with_miss": clusters_with_miss,
            "cp95_upper_miss_rate_n": cp_upper(miss, n),
            "cp95_upper_miss_rate_clusters": cp_upper(clusters_with_miss, int(len(agg))) if len(agg) else None}


def r2_analysis(runs, rng):
    runs = runs.copy()
    runs["base"] = runs["run"].str.split("_ep").str[0]
    res = []
    for (pop, jb, cls, band), g in runs.groupby(["population", "injected_jump_bar", "period_class", "band"]):
        row = {"population": pop, "jump": jb, "class": cls, "band": band}
        row["rates"] = {k: rate_block(g, "base", c) for k, c in
                        (("D1p", "d1p_flagged"), ("C0", "c0_flagged"), ("Cm", "cm_flagged"))}
        row["margin_cm_d1p_base"] = summarize(g, "base", rng, "cm_flagged", "d1p_flagged", "Cm-D1p")
        row["loss_c0_cm_base"] = summarize(g, "base", rng, "c0_flagged", "cm_flagged", "C0-Cm")
        if pop == "episodes":
            row["margin_cm_d1p_episode"] = summarize(g, "run", rng, "cm_flagged", "d1p_flagged", "Cm-D1p")
            row["loss_c0_cm_episode"] = summarize(g, "run", rng, "c0_flagged", "cm_flagged", "C0-Cm")
        res.append(row)
    # pooled P9-D1-5 rows: transient per jump over bands, quiet per jump over bands
    pooled = []
    for (pop, jb, cls), g in runs.groupby(["population", "injected_jump_bar", "period_class"]):
        pooled.append({"population": pop, "jump": jb, "class": cls, "band": "all",
                       "rates": {k: rate_block(g, "base", c) for k, c in
                                 (("D1p", "d1p_flagged"), ("C0", "c0_flagged"), ("Cm", "cm_flagged"))},
                       "margin_cm_d1p_base": summarize(g, "base", rng, "cm_flagged", "d1p_flagged", "Cm-D1p"),
                       "loss_c0_cm_base": summarize(g, "base", rng, "c0_flagged", "cm_flagged", "C0-Cm")})
    return res, pooled


def bases_phase_profile(runs):
    """Per base: C-m outcome at the phase-rule failing rows (k0/k1, negative jumps)."""
    g = runs[(runs["population"] == "bases_phase") & (runs["band"].isin(["k0", "k1"]))
             & (runs["injected_jump_bar"].isin(["-100", "-150"]))]
    out = []
    for (jb, band), h in g.groupby(["injected_jump_bar", "band"]):
        per = h.groupby("run")[["candidates", "cm_flagged", "d1p_flagged"]].sum()
        per = per[per["candidates"] > 0]
        miss = per["candidates"] - per["cm_flagged"]
        out.append({"jump": jb, "band": band, "bases_with_candidates": int(len(per)),
                    "bases_with_cm_miss": int((miss > 0).sum()),
                    "bases_all_missed": int((per["cm_flagged"] == 0).sum()),
                    "candidates_per_base": per["candidates"].value_counts().sort_index().to_dict(),
                    "cm_misses_per_base": miss.value_counts().sort_index().to_dict()})
    return out


def harness_analysis(detail, rng):
    df = pd.read_csv(detail, usecols=["label", "t_minus_event_s", "jump_bar", "kind", "threshold_kN",
                                      "C0", "Cm", "D1p"])
    cand = df[df["threshold_kN"].notna()].copy()
    for c in ("C0", "Cm", "D1p"):
        cand[c] = cand[c].astype(bool).astype(int)
    cand["candidates"] = 1
    t = cand["t_minus_event_s"].to_numpy()
    cand["band"] = ""
    for name, lo, hi in BANDS:
        cand.loc[(t >= lo) & (t < hi), "band"] = name
    checks = {}
    tr = cand[cand["kind"] == "transient"]
    for jb, g in tr.groupby("jump_bar"):
        checks[str(jb)] = {"n": int(len(g)), "C0": round(g["C0"].mean() * 100, 1),
                           "Cm": round(g["Cm"].mean() * 100, 1), "D1p": round(g["D1p"].mean() * 100, 1)}
    exp = {"-150.0": (4206, 98.3, 97.9, 90.2), "-100.0": (2313, 88.5, 86.6, 81.0),
           "100.0": (2450, 88.4, 83.6, 82.3), "150.0": (4251, 99.4, 99.3, 90.5)}
    ok = all(checks[k]["n"] == v[0] and abs(checks[k]["C0"] - v[1]) < 0.051
             and abs(checks[k]["Cm"] - v[2]) < 0.051 and abs(checks[k]["D1p"] - v[3]) < 0.051
             for k, v in exp.items())
    rows = []
    for (jb, kind, band), g in cand.groupby(["jump_bar", "kind", "band"]):
        rows.append({"jump": float(jb), "class": kind, "band": band,
                     "rates": {k: rate_block(g, "label", k) for k in ("D1p", "C0", "Cm")},
                     "margin_cm_d1p": summarize(g, "label", rng, "Cm", "D1p", "Cm-D1p"),
                     "loss_c0_cm": summarize(g, "label", rng, "C0", "Cm", "C0-Cm")})
    late_loss = {}
    for jb, g in tr[tr["band"] == "late"].groupby("jump_bar"):
        late_loss[str(jb)] = round((g["C0"].sum() - g["Cm"].sum()) / len(g) * 100, 2)
    exp_late = {"-150.0": 0.55, "-100.0": 2.41, "100.0": 1.99, "150.0": 0.08}
    ok_late = all(abs(late_loss[k] - v) < 0.006 for k, v in exp_late.items())
    tr_range = {str(jb): [float(g["t_minus_event_s"].min()), float(g["t_minus_event_s"].max())]
                for jb, g in tr.groupby("jump_bar")}
    return {"rows": rows, "self_check_2_3": ok, "self_check_late_loss": ok_late,
            "transient_t_minus_event_range_s": tr_range, "late_loss_pp": late_loss,
            "n_labels": int(cand["label"].nunique())}


def self_checks(rng):
    out = {}
    # 1. identical clusters -> zero-width interval
    a = np.full(20, 9.0)
    b = np.full(20, 8.0)
    d = np.full(20, 10.0)
    v = boot_ratio(a, b, d, rng)
    out["identical_clusters_zero_width"] = bool(np.allclose(v, 0.1))
    # 2. iid clusters of size 1 -> bootstrap SD close to binomial SD of the difference of paired indicators
    p_diff = 0.05
    n = 2000
    x = (rng.random(n) < p_diff).astype(float)
    v = boot_ratio(x, np.zeros(n), np.ones(n), rng)
    sd_an = np.sqrt(x.mean() * (1 - x.mean()) / n)
    out["iid_sd_ratio"] = float(np.std(v) / sd_an)
    out["iid_sd_ok"] = bool(abs(out["iid_sd_ratio"] - 1) < 0.05)
    # 3. CP upper for 0/23 and 0/24
    out["cp_0_23"] = cp_upper(0, 23)
    out["cp_ok"] = bool(abs(cp_upper(0, 299) - 0.01) < 0.0005)
    return out


def main():
    runs_p, bands_p, detail_p, out_dir = (Path(x) for x in sys.argv[1:5])
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    sc = self_checks(rng)
    runs = pd.read_csv(runs_p, dtype={"injected_jump_bar": str})
    bands = pd.read_csv(bands_p, dtype={"injected_jump_bar": str})
    cols = ["candidates", "d1p_flagged", "c0_flagged", "cm_flagged"]
    s_runs = runs.groupby(["population", "injected_jump_bar", "period_class", "band"])[cols].sum().sort_index()
    s_bands = bands.set_index(["population", "injected_jump_bar", "period_class", "band"])[cols].sort_index()
    sc["runs_sum_to_bands"] = bool(s_runs.equals(s_bands.astype(s_runs.dtypes.to_dict())))
    sc["n_runs"] = {p: int(g["run"].nunique()) for p, g in runs.groupby("population")}
    r2_rows, r2_pooled = r2_analysis(runs, rng)
    profile = bases_phase_profile(runs)
    harness = harness_analysis(detail_p, rng)
    ok = (sc["identical_clusters_zero_width"] and sc["iid_sd_ok"] and sc["cp_ok"] and sc["runs_sum_to_bands"]
          and harness["self_check_2_3"] and harness["self_check_late_loss"])
    res = {"tool": "ed9_r3_stats", "seed": SEED, "B": B,
           "inputs": {str(p): sha256(p) for p in (runs_p, bands_p, detail_p)},
           "script_sha256": sha256(Path(__file__)),
           "self_checks": sc, "r2_rows": r2_rows, "r2_pooled": r2_pooled, "bases_phase_profile": profile,
           "harness": harness, "elapsed_s": round(time.time() - t0, 1), "status": "ok" if ok else "self_check_fail"}
    out = out_dir / "ed9_r3_stats.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({"status": res["status"], "out": str(out), "elapsed_s": res["elapsed_s"]}))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
