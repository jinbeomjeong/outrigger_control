"""Ed. 7 confirmation pool (spec v7 6.3 (ga')/(da')) from the stored V0 grid and the ed. 6 grid
sample: pool size, V0 opportunity, within-cluster V0 structure and a harmless-churn floor.
stats-design-expert, 2026-11-24, design only.

Inputs (public, no ed. 7 result exists):
  - stored V0 grid touch_phase/acceptance/c4g2_only/grid/{grid_r67_main, grid_r67_top,
    grid_r69_bottom, grid_r69_top}.json (V0 base arm, v5_criteria.md section 10)
  - ed. 6 grid sample ed6_design/stats_v6/s50_grid_sample.csv (sha256 6170e240..., the source of
    the sealed ed. 6 key file confirm_b_grid192.json): the offset used per cluster in ed. 6 (b)
Definitions follow s50: run id = (level, fs_kN, timing, leg, event, offset_s), exact duplicates
kept once (later file wins); cluster = (level, fs_kN, timing, leg, event).
Outputs (argv[1] folder): s30_grid_pool.json, s30_grid_pool.txt, s30_pool_runs.csv
stdout: status only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
GRID = ROOT / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
S50 = ROOT / "j_p3_cause" / "ed6_design" / "stats_v6" / "s50_grid_sample.csv"
MARGIN_KEYS = ("Fmin_after_event_minus_Fmin_kN", "Fmin_after_W_minus_Fmin_kN",
               "pair_union_to_1.8_s", "last_touch_to_3.0_s", "adj_sum_to_0.5_s")
# margin key -> gate whose presence in run["gates"] makes the margin a judged quantity
MARGIN_GATE = {"Fmin_after_event_minus_Fmin_kN": "Fmin_after_event",
               "Fmin_after_W_minus_Fmin_kN": "Fmin_after_W",
               "pair_union_to_1.8_s": "U832_pair_union",
               "last_touch_to_3.0_s": "U832_last_touch",
               "adj_sum_to_0.5_s": "U57_outside"}


def event_name(ev) -> str:
    if isinstance(ev, dict):
        for k in ("name", "kind", "type", "label"):
            if k in ev:
                return str(ev[k])
    return str(ev)


def load_runs():
    runs, n_rows = {}, 0
    for fn in FILES:
        d = json.loads((GRID / fn).read_text(encoding="utf-8"))
        for job in d["results"]:
            items = job["runs"].items() if isinstance(job["runs"], dict) else enumerate(job["runs"])
            for rk, run in items:
                n_rows += 1
                ident = (job["level"], float(job["fs_kN"]), job["timing"], job["leg"],
                         event_name(run.get("event")), float(run["offset_s"]))
                gates = run.get("gates") or {}
                mg = run.get("margins") or {}
                runs[ident] = {"file": fn, "v0_pass": bool(run.get("pass")),
                               "sha": run.get("commands_sha256"),
                               "failed_gates": sorted(g for g, v in gates.items() if not v),
                               "gate_names": sorted(gates),
                               "margins": {k: (mg.get(k) if MARGIN_GATE[k] in gates else None)
                                           for k in MARGIN_KEYS},
                               "fast": bool(run.get("fast"))}
    return runs, n_rows


def icc_binary(groups):
    """ANOVA (one-way) ICC estimator for binary outcomes with unequal group sizes."""
    ys = [np.asarray(g, float) for g in groups if len(g) >= 2]
    n = np.array([len(g) for g in ys])
    N, k = n.sum(), len(ys)
    grand = np.concatenate(ys).mean()
    ssb = sum(len(g) * (g.mean() - grand) ** 2 for g in ys)
    ssw = sum(((g - g.mean()) ** 2).sum() for g in ys)
    msb, msw = ssb / (k - 1), ssw / (N - k)
    n0 = (N - (n ** 2).sum() / N) / (k - 1)
    return float((msb - msw) / (msb + (n0 - 1) * msw)) if (msb + (n0 - 1) * msw) > 0 else 0.0


def main() -> int:
    out_dir = Path(sys.argv[1])
    runs, n_rows = load_runs()
    clusters = defaultdict(list)
    for ident in sorted(runs):
        clusters[ident[:5]].append(ident)
    used = {}
    with S50.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cl = (r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"])
            used[cl] = float(r["offset_s"])
    s50_sha = hashlib.sha256(S50.read_bytes()).hexdigest()

    pool, rows_csv = [], []
    for cl, members in clusters.items():
        for ident in members:
            r = runs[ident]
            is_used = used.get(cl) == ident[5]
            rows_csv.append({"level": cl[0], "fs_kN": cl[1], "timing": cl[2], "leg": cl[3],
                             "event": cl[4], "offset_s": ident[5], "n_offsets": len(members),
                             "used_ed6": is_used, "v0_pass": r["v0_pass"],
                             "v0_failed_gates": ";".join(r["failed_gates"]),
                             "v0_sha": r["sha"]})
            if not is_used:
                pool.append(ident)
    with (out_dir / "s30_pool_runs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_csv[0]))
        w.writeheader()
        w.writerows(rows_csv)

    res = {"n_rows_768": n_rows, "n_unique_runs": len(runs), "n_clusters": len(clusters),
           "cluster_size_hist": dict(Counter(len(m) for m in clusters.values())),
           "s50_sha256": s50_sha, "n_used_ed6": sum(1 for c in clusters if c in used)}
    # pool size and composition
    res["pool_unique_runs"] = len(pool)
    res["pool_v0_pass"] = sum(runs[i]["v0_pass"] for i in pool)
    res["pool_by_timing"] = {t: {"runs": sum(1 for i in pool if i[2] == t),
                                 "v0_pass": sum(runs[i]["v0_pass"] for i in pool if i[2] == t),
                                 "clusters": sum(1 for c in clusters if c[2] == t)}
                             for t in sorted({c[2] for c in clusters})}
    res["pool_by_event"] = {e: sum(1 for i in pool if i[4] == e) for e in sorted({c[4] for c in clusters})}
    # within-cluster distinct command hashes (V0): offsets giving the same V0 trajectory
    dup_sha = 0
    for cl, members in clusters.items():
        shas = [runs[i]["sha"] for i in members]
        dup_sha += len(shas) - len(set(shas))
    res["v0_same_sha_within_cluster_extra_runs"] = dup_sha
    # V0 failure structure across offsets
    groups = [[0.0 if runs[i]["v0_pass"] else 1.0 for i in m] for m in clusters.values()]
    nf = Counter((len(g), int(sum(g))) for g in groups)
    res["v0_fail_pattern_(n_offsets,n_fail)"] = {f"{k[0]},{k[1]}": v for k, v in sorted(nf.items())}
    res["v0_icc_fail_across_offsets"] = icc_binary(groups)
    res["v0_fail_rate_all"] = float(np.mean(np.concatenate([np.array(g) for g in groups])))
    # nonparametric harmless-churn floor: a V0-passing pool row "redrawn" inside its cluster
    # fails with prob = V0 fail fraction among the OTHER offsets of the cluster.
    p_row, p_row_by_cluster = [], defaultdict(list)
    for ident in pool:
        if not runs[ident]["v0_pass"]:
            continue
        cl = ident[:5]
        others = [j for j in clusters[cl] if j != ident]
        p = float(np.mean([0.0 if runs[j]["v0_pass"] else 1.0 for j in others])) if others else 0.0
        p_row.append(p)
        p_row_by_cluster[cl].append(p)
    p_row = np.array(p_row)
    res["churn_floor_np"] = {"n_opp_pool": int(p_row.size), "expected_fails": float(p_row.sum()),
                             "rows_with_p_gt0": int((p_row > 0).sum()),
                             "clusters_with_p_gt0": int(sum(1 for v in p_row_by_cluster.values()
                                                            if max(v) > 0))}
    # margin scatter across offsets (V0, continuous gates)
    msum = {}
    for key in MARGIN_KEYS:
        within, cvals = [], []
        for cl, m in clusters.items():
            vals = [runs[i]["margins"][key] for i in m if runs[i]["margins"][key] is not None]
            if len(vals) >= 2:
                v = np.array(vals, float)
                within.append(((v - v.mean()) ** 2).sum())
                cvals.append((len(v) - 1))
        if not cvals:
            continue
        sd_w = float(np.sqrt(sum(within) / sum(cvals)))
        cs = []
        for ident in pool:
            r = runs[ident]
            mv = r["margins"][key]
            if r["v0_pass"] and mv is not None and sd_w > 0:
                cs.append(mv / sd_w)
        cs = np.array(cs)
        msum[key] = {"sd_within_offsets": sd_w, "n_pool_opp_with_margin": int(cs.size),
                     "c_quantiles_5_25_50": [float(x) for x in np.percentile(cs, [5, 25, 50])]
                     if cs.size else None,
                     "n_c_lt": {str(t): int((cs < t).sum()) for t in (1.0, 2.0, 2.5, 3.0, 3.5)}}
    res["margin_scatter"] = msum
    # margin-model harmless floor per pool opportunity row: a redraw with the pooled within-cluster
    # offset scatter fails a judged continuous gate with prob Phi(-c); gates independent.
    from scipy.stats import norm
    sd = {k: v["sd_within_offsets"] for k, v in msum.items()}
    pm = {}
    for ident in pool:
        r = runs[ident]
        if not r["v0_pass"]:
            continue
        surv = 1.0
        for key, mv in r["margins"].items():
            if mv is not None and sd.get(key, 0) > 0:
                surv *= float(norm.cdf(mv / sd[key]))
        pm[ident] = 1.0 - surv
    pmv = np.array(list(pm.values()))
    res["churn_floor_margin"] = {"expected_fails": float(pmv.sum()),
                                 "rows_p_gt_1pct": int((pmv > 0.01).sum()),
                                 "rows_p_gt_10pct": int((pmv > 0.10).sum()),
                                 "max_p": float(pmv.max())}
    with (out_dir / "s30_pool_opp_p.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["level", "fs_kN", "timing", "leg", "event", "offset_s", "p_np", "p_margin"])
        for ident in pool:
            if not runs[ident]["v0_pass"]:
                continue
            cl = ident[:5]
            others = [j for j in clusters[cl] if j != ident]
            pnp = float(np.mean([0.0 if runs[j]["v0_pass"] else 1.0 for j in others])) if others else 0.0
            w.writerow([*ident, pnp, pm[ident]])
    # failed-gate census of V0 fails (all runs)
    res["v0_failed_gate_counts"] = dict(Counter(g for r in runs.values() for g in r["failed_gates"]))
    res["gate_sets"] = {";".join(k): v for k, v in Counter(tuple(r["gate_names"])
                                                           for r in runs.values()).items()}
    # V0 failing clusters (identifiers only) for the target/stop list
    res["v0_fail_clusters"] = ["|".join(str(x) for x in cl) + f" fails {sum(not runs[i]['v0_pass'] for i in m)}/{len(m)}"
                               for cl, m in clusters.items() if any(not runs[i]["v0_pass"] for i in m)]
    (out_dir / "s30_grid_pool.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = [json.dumps({k: v for k, v in res.items() if k not in ("margin_scatter",)}, indent=None)]
    for k, v in msum.items():
        L.append(f"margin {k}: {json.dumps(v)}")
    (out_dir / "s30_grid_pool.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    ok = len(runs) == 672 and len(clusters) == 192 and res["n_used_ed6"] == 192
    print("ok" if ok else "frame_mismatch")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
