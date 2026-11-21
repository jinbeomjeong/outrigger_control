"""Substitute-leg (rod fallback) occurrence per stored row, past VB/V0 noise runs.

Checks (a) whether the Dg-3 135 keys equal the rows with a substitute leg,
(b) per-seed substitute probability within Dg-3 cases (opportunity rate for
new seeds), (c) agreement of the indicator between V0 and VB at the same key.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
S = Path(sys.argv[1])


def strip_key(k):
    return k.split("#", 1)[1] if "#" in k else k


def load(name):
    data = json.loads((ROOT / name).read_text(encoding="utf-8"))
    rec = []
    for r in data["results"]:
        k = strip_key(r["key"])
        lwa = r.get("lock_window_alignment") or {}
        fl = lwa.get("fallback_legs") or {}
        reasons = r.get("rod_fallback_reasons") or []
        r79fb = (r.get("r79") or {}).get("rod_fallback") or []
        toks = k.split("|")
        rec.append(
            {
                "key": k,
                "case": "|".join([toks[0]] + toks[2:]),
                "level": r.get("level"),
                "seed": int(r.get("seed_index")),
                "fb_legs": len(fl),
                "fb_reasons": len(reasons),
                "fb_r79": len(r79fb),
                "has_lwa": bool(lwa),
            }
        )
    return pd.DataFrame(rec)


vb = load("h8_noise_VB.json")
v0 = load("h8_noise_V0.json")
h6 = load("h6_dg3_v4on.json")
dg3 = set(h6.key)
out = {}
for col in ("fb_legs", "fb_reasons", "fb_r79"):
    ind = vb[col] > 0
    out[f"VB_{col}_rows"] = int(ind.sum())
    out[f"VB_{col}_by_level"] = vb[ind].level.value_counts().to_dict()
    inset = vb.key.isin(dg3)
    out[f"VB_{col}_vs_dg3"] = {
        "both": int((ind & inset).sum()),
        "ind_only": int((ind & ~inset).sum()),
        "dg3_only": int((~ind & inset).sum()),
    }
out["VB_has_lwa"] = int(vb.has_lwa.sum())
out["h6_fb"] = {c: int((h6[c] > 0).sum()) for c in ("fb_legs", "fb_reasons", "fb_r79")}

# choose indicator = Dg-3 membership for the opportunity estimate (definition of Dg-3)
vb["sub"] = vb.key.isin(dg3)
dg3_cases = set(h6.case)
sub = vb[vb.case.isin(dg3_cases)]
for lev, s in sub.groupby("level"):
    g = s.groupby("case")["sub"].agg(["sum", "size"])
    out[f"dg3cases_{lev}"] = {
        "cases": int(len(g)),
        "rows": int(g["size"].sum()),
        "sub_rows": int(g["sum"].sum()),
        "p_sub_per_seed": float(g["sum"].sum() / g["size"].sum()),
        "dist_sub_count_per_case": g.value_counts().reset_index().astype(int).to_dict("records"),
    }
    # per-case p for later simulation
    g.to_csv(S / f"subcount_{lev}.csv")

# V0 vs VB agreement of substitute indicator (use r79 rod_fallback count as indicator)
m = vb.merge(v0, on="key", suffixes=("_vb", "_v0"))
for col in ("fb_legs", "fb_r79"):
    a = m[f"{col}_vb"] > 0
    b = m[f"{col}_v0"] > 0
    out[f"agree_{col}"] = {
        "both": int((a & b).sum()),
        "vb_only": int((a & ~b).sum()),
        "v0_only": int((~a & b).sum()),
        "neither": int((~a & ~b).sum()),
    }
(S / "subst_past.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ok")
