"""Per-level failure rates of past same-seed setting pairs; restrict to Dg-3 cases."""
import json
import sys
from pathlib import Path

import pandas as pd

S = Path(sys.argv[1])
rows = pd.read_csv(S / "past_rows.csv")
h6_cases = set(rows[rows.file == "h6_dg3_v4on.json"].case)
h6_keys = set(rows[rows.file == "h6_dg3_v4on.json"].key)
d = pd.read_csv(S / "pairs_noise_V0_vs_VB.csv")
out = {}
for direction, (b, n) in {"V0_base": ("ta", "tb"), "VB_base": ("tb", "ta")}.items():
    br = d[b].notna()
    fail = br & (d[n].isna() | ((d[n] - d[b]) > 30))
    d[f"fail_{direction}"] = fail
    res = {}
    for lev, sub in d.groupby("level"):
        res[lev] = {"n": int(len(sub)), "base_ready": int(br[sub.index].sum()), "fail": int(fail[sub.index].sum()),
                    "fail_cases": int(sub[fail[sub.index]].case.nunique())}
    sub = d[d.case.isin(h6_cases)]
    res["dg3_cases_all_seeds"] = {"n": int(len(sub)), "fail": int(fail[sub.index].sum()),
                                  "fail_cases": int(sub[fail[sub.index]].case.nunique())}
    sub = d[d.key.isin(h6_keys)]
    res["dg3_keys"] = {"n": int(len(sub)), "fail": int(fail[sub.index].sum())}
    sub = d[d.case.isin(h6_cases) & ~d.key.isin(h6_keys)]
    res["dg3_cases_other_seeds"] = {"n": int(len(sub)), "fail": int(fail[sub.index].sum()),
                                    "fail_cases": int(sub[fail[sub.index]].case.nunique())}
    out[direction] = res
# how many seeds of the same case fail together (clustering)
for direction in ("V0_base", "VB_base"):
    g = d.groupby("case")[f"fail_{direction}"].agg(["sum", "size"])
    out[f"cluster_{direction}"] = g[g["sum"] > 0].value_counts().reset_index().astype(int).to_dict("records")
# base no-READY by case among Dg-3 cases in VB across seeds
(S / "pair_level.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ok")
