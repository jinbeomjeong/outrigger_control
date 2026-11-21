"""L2 (normal grade) divergence floor from stored pre-4a VB rev 4 noise rows.

Inputs: past_rows.csv extracted earlier from h8_noise_VB.json (sha 2219ab97),
plus V0 vs VB same-seed pass/READY transitions at L2 (h8_noise_V0.json 54d17316).
Outputs: per-case cross-seed READY failure (independent-draw model), base.pass
mixing across seeds, V0->VB same-seed pass->fail and READY loss at L2.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PAST = Path(sys.argv[1])
ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
OUT = Path(sys.argv[2])

df = pd.read_csv(PAST)
nz = df[(df.file == "h8_noise_VB.json") & (df.level == "L2")].copy()
res = {"n_rows": len(nz), "n_cases": int(nz.case.nunique()),
       "seeds_per_case": nz.groupby("case").size().value_counts().to_dict(),
       "no_ready_rows": int(nz.t_ready.isna().sum()),
       "final_phase": nz.final_phase.value_counts(dropna=False).to_dict()}
tot = fail = 0
fail_cases = set()
sds = []
pass_mixed = 0
for c, sub in nz.groupby("case"):
    t = sub.t_ready.to_numpy(float)
    if (~np.isnan(t)).sum() >= 2:
        sds.append(np.nanstd(t, ddof=1))
    p = sub["pass"].astype(str).str.lower().eq("true").to_numpy()
    if 0 < p.sum() < len(p):
        pass_mixed += 1
    for a, b in itertools.permutations(range(len(t)), 2):
        if np.isnan(t[a]):
            continue
        tot += 1
        if np.isnan(t[b]) or t[b] - t[a] > 30.0:
            fail += 1
            fail_cases.add(c)
res["ordered_pairs"] = tot
res["indep_draw_fail"] = fail
res["indep_draw_fail_cases"] = len(fail_cases)
res["upper95_rate_if_zero"] = 1 - 0.05 ** (1 / tot) if tot else None
res["ready_sd_q"] = {q: float(np.quantile(sds, q)) for q in (0.5, 0.9, 0.99, 1.0)}
res["cases_pass_mixed_across_seeds"] = pass_mixed
res["pass_rate_rows"] = float(nz["pass"].astype(str).str.lower().eq("true").mean())


def load(name):
    data = json.loads((ROOT / name).read_text(encoding="utf-8"))["results"]
    out = {}
    for r in data:
        k = r["key"].split("#", 1)[-1]
        if r.get("level") != "L2":
            continue
        b = r.get("base") or {}
        t = b.get("t_ready_s")
        if t is None:
            t = b.get("t_ready")
        out[k] = (t, bool(b.get("pass")))
    return out


v0 = load("h8_noise_V0.json")
vb = load("h8_noise_VB.json")
keys = sorted(set(v0) & set(vb))
pf = sum(1 for k in keys if v0[k][1] and not vb[k][1])
fp = sum(1 for k in keys if (not v0[k][1]) and vb[k][1])
rl = sum(1 for k in keys if v0[k][0] is not None and (vb[k][0] is None or vb[k][0] - v0[k][0] > 30))
res["V0_to_VB_L2"] = {"pairs": len(keys), "pass_to_fail": pf, "fail_to_pass": fp, "ready_loss": rl}
OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("ok")
