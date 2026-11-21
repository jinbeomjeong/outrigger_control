"""Summarise structure and within-case seed variability of stored VB rev 4 rows."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

S = Path(sys.argv[1])
df = pd.read_csv(S / "past_rows.csv")
out = {}

h6 = df[df.file == "h6_dg3_v4on.json"].copy()
nz = df[df.file == "h8_noise_VB.json"].copy()
se = df[df.file == "h8_seedext_VB.json"].copy()

out["h6_n"] = len(h6)
out["h6_by_level"] = h6.level.value_counts().to_dict()
out["h6_by_family"] = h6.family.value_counts().to_dict()
out["h6_by_seed"] = h6.seed_tok.value_counts().to_dict()
out["h6_distinct_case_ids"] = int(h6.case.nunique())
out["h6_distinct_harness_inner"] = int(h6[["harness", "inner"]].drop_duplicates().shape[0])
out["h6_no_ready"] = int(h6.t_ready.isna().sum())
out["h6_final_phase"] = h6.final_phase.value_counts(dropna=False).to_dict()
out["h6_tokens_example"] = h6.key.head(5).tolist()
out["h6_ntok"] = h6.key.str.count(r"\|").add(1).value_counts().to_dict()
# family x level
out["h6_family_level"] = h6.groupby(["family", "level"]).size().astype(int).to_dict()
out["h6_family_level"] = {f"{a}/{b}": v for (a, b), v in out["h6_family_level"].items()}

# duplicated (harness, inner) groups in h6
grp = h6.groupby(["harness", "inner"]).size()
out["h6_harness_inner_group_sizes"] = grp.value_counts().sort_index().to_dict()

# collisions: for each h6 case id, seeds present in noise / seedext
nz_seeds = nz.groupby("case")["seed_index"].apply(lambda s: sorted(set(int(x) for x in s)))
se_seeds = se.groupby("case")["seed_index"].apply(lambda s: sorted(set(int(x) for x in s)))
h6["noise_seeds"] = h6.case.map(nz_seeds)
h6["seedext_seeds"] = h6.case.map(se_seeds)
out["h6_cases_in_noise"] = int(h6.noise_seeds.notna().sum())
out["h6_cases_in_seedext"] = int(h6.seedext_seeds.notna().sum())
coll = {}
for s in range(3, 8):
    n = 0
    for v1, v2 in zip(h6.noise_seeds, h6.seedext_seeds):
        st = set(v1 if isinstance(v1, list) else []) | set(v2 if isinstance(v2, list) else [])
        n += s in st
    coll[f"s{s}"] = n
out["h6_case_seed_collision_count"] = coll
out["noise_seed_set"] = sorted(set(int(x) for x in nz.seed_index))
out["noise_n"] = len(nz)
out["noise_by_level"] = nz.level.value_counts().to_dict()
out["noise_by_family"] = nz.family.value_counts().to_dict()


def within(dfx, label):
    res = {}
    g = dfx.groupby("case")
    sizes = g.size()
    res["n_cases"] = int(len(sizes))
    res["seeds_per_case"] = sizes.value_counts().sort_index().to_dict()
    sds, ranges, miss_frac = [], [], []
    pair_tot = pair_gt30 = pair_mix = pair_gt30_or_mix = 0
    case_rows = []
    for c, sub in g:
        t = sub.t_ready.to_numpy(dtype=float)
        have = ~np.isnan(t)
        miss_frac.append(1 - have.mean())
        if have.sum() >= 2:
            sds.append(float(np.std(t[have], ddof=1)))
            ranges.append(float(np.ptp(t[have])))
        npair_gt30 = npair_mix = npair = 0
        for a, b in itertools.permutations(range(len(t)), 2):
            # ordered pairs: a = base, b = new
            if np.isnan(t[a]):
                continue  # base no READY -> record only
            npair += 1
            if np.isnan(t[b]):
                npair_mix += 1
            elif t[b] - t[a] > 30.0:
                npair_gt30 += 1
        pair_tot += npair
        pair_gt30 += npair_gt30
        pair_mix += npair_mix
        case_rows.append((c, len(t), int((~have).sum()), npair, npair_gt30, npair_mix))
    sds = np.array(sds)
    res["ready_sd_s_quantiles"] = (
        {q: float(np.quantile(sds, q)) for q in (0.5, 0.75, 0.9, 0.95, 1.0)} if len(sds) else None
    )
    res["ready_range_s_quantiles"] = (
        {q: float(np.quantile(ranges, q)) for q in (0.5, 0.9, 0.95, 1.0)} if ranges else None
    )
    mf = np.array(miss_frac)
    res["cases_any_no_ready"] = int((mf > 0).sum())
    res["cases_all_no_ready"] = int((mf == 1).sum())
    res["cases_mixed_no_ready"] = int(((mf > 0) & (mf < 1)).sum())
    res["ordered_pairs_base_ready"] = pair_tot
    res["pairs_new_minus_base_gt30"] = pair_gt30
    res["pairs_new_missing"] = pair_mix
    res["pair_fail_rate_if_decorrelated"] = (pair_gt30 + pair_mix) / pair_tot if pair_tot else None
    cr = pd.DataFrame(case_rows, columns=["case", "n", "n_noready", "npair", "gt30", "miss"])
    cr["q"] = (cr.gt30 + cr.miss) / cr.npair.replace(0, np.nan)
    res["cases_with_q_gt0"] = int((cr.q > 0).sum())
    res["q_distribution_over_cases"] = cr.q.describe().to_dict()
    res["q_top10"] = cr.sort_values("q", ascending=False).head(10)[["n", "n_noready", "q"]].to_dict("records")
    res["final_phase"] = dfx.final_phase.value_counts(dropna=False).to_dict()
    cr.to_csv(S / f"within_{label}.csv", index=False)
    return res


out["within_noise_all"] = within(nz, "noise_all")
out["within_noise_L3"] = within(nz[nz.level == "L3"], "noise_L3")
h6_cases = set(h6.case)
out["within_noise_h6cases"] = within(nz[nz.case.isin(h6_cases)], "noise_h6cases")
out["within_seedext"] = within(se, "seedext")
(S / "past_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("ok")
