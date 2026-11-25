"""Summarise |D| > 15 kN LEVEL episodes (twist_over_limit) of the a2 repro and
relate them to the event time, the previous phase, shots and LEVEL completion."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--q02", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
q = Path(a.q02)
ep = pd.read_csv(q / "a2_twist_over_limit_episodes.csv")
ln = pd.read_csv(q / "a2_lines.csv")
sh = pd.read_csv(q / "a2_shots.csv")
dn = pd.read_csv(q / "a2_level_done.csv")
lines = []
p = lines.append
p(f"episodes {len(ep)}, lines with entries {int((ln.tol_entries > 0).sum())}/{len(ln)}")
ep["dur_s"] = ep.end_t_s - ep.start_t_s
p("periods: " + ep.periods.describe().round(2).to_string().replace("\n", " | "))
p("dur_s: " + ep.dur_s.describe().round(2).to_string().replace("\n", " | "))
p("max_abs_twist_kN: " + ep.max_abs_twist_kN.describe().round(2).to_string().replace("\n", " | "))
p("t_since_event_s: " + ep.t_since_event_s.describe().round(2).to_string().replace("\n", " | "))
p("prev_phase counts: " + ep.prev_phase.value_counts().to_string().replace("\n", " | "))
p("end_phase counts: " + ep.end_phase.value_counts().to_string().replace("\n", " | "))
p(f"open episodes (end None): {int(ep.end_t_s.isna().sum())}")
# entry type: first LEVEL read already > 15 (entered LEVEL above limit) vs crossing inside LEVEL
p(f"episodes starting before event (t_since_event<0): {int((ep.t_since_event_s < 0).sum())}; after event: {int((ep.t_since_event_s >= 0).sum())}; no event: {int(ep.t_since_event_s.isna().sum())}")
# bins by t_since_event
bins = [-1e9, 0, 1, 3, 10, 30, 1e9]
p("t_since_event bins: " + pd.cut(ep.t_since_event_s, bins).value_counts(sort=False).to_string().replace("\n", " | "))
# per plant
p("per plant entries: " + ln.groupby("plant").tol_entries.sum().to_string().replace("\n", " | "))
p("per plant lines with entries: " + ln.assign(h=ln.tol_entries > 0).groupby("plant").h.sum().to_string().replace("\n", " | "))
# episodes whose end_phase is level -> exited by dropping below limit within LEVEL
# relation to level completion: any level_done while |D|>15? check done times inside episodes
inside = 0
for _, d in dn.iterrows():
    e = ep[(ep.key == d.key) & (ep.plant == d.plant)]
    for _, r in e.iterrows():
        en = r.end_t_s if not np.isnan(r.end_t_s) else 1e9
        if r.start_t_s <= d.t_s <= en:
            inside += 1
p(f"level_done inside a |D|>15 episode: {inside}")
# max |D| level per line vs whether DONE was relax
p("relax done rows:\n" + dn[dn.path == "relax"].to_string())
# lines whose final phase is not ready
p("non-ready lines:\n" + ln[ln.final_phase != "ready"][["key", "plant", "final_phase", "tol_entries", "shots", "level_seg_ends"]].to_string())
# largest episodes
p("top 12 episodes by max|D|:\n" + ep.sort_values("max_abs_twist_kN", ascending=False).head(12)[["key", "plant", "start_t_s", "end_t_s", "periods", "max_abs_twist_kN", "t_since_event_s", "prev_phase", "end_phase", "D_true_at_start_kN"]].to_string())
p("longest 12 episodes:\n" + ep.sort_values("periods", ascending=False).head(12)[["key", "plant", "start_t_s", "end_t_s", "periods", "max_abs_twist_kN", "t_since_event_s", "prev_phase", "end_phase"]].to_string())
# shots summary per plant
p("shots per plant: " + sh.groupby("plant").size().to_string().replace("\n", " | "))
p("grew per plant: " + sh.groupby("plant").twist_grew.agg(["sum", "count"]).to_string().replace("\n", " | "))
vbm5 = sh[sh.plant != "L"]
p(f"VBM5 shots {len(vbm5)}, grew {int(vbm5.twist_grew.sum())} -> {vbm5.twist_grew.mean():.3f}")
p("shot sign reduces D by geometry (rank-1 sign): " + sh.shot_reduces_D_by_sign.value_counts().to_string().replace("\n", " | "))
p("consistency twist_grew vs (not reduces): " + str(int(((~sh.shot_reduces_D_by_sign) == sh.twist_grew).sum())) + f"/{len(sh)}")
r = sh.dD_rec_kN / sh.dD_pred_rank1_kN
p("dD_rec / rank1 pred: " + r.describe().round(3).to_string().replace("\n", " | "))
p("|D_before| kN: " + sh.D_before_rec_kN.abs().describe().round(2).to_string().replace("\n", " | "))
p("|D_after| kN: " + sh.D_after_rec_kN.abs().describe().round(2).to_string().replace("\n", " | "))
p("grew shots |D_after| kN: " + sh[sh.twist_grew].D_after_rec_kN.abs().describe().round(2).to_string().replace("\n", " | "))
p("stroke change mm: " + sh.stroke_change_mm.describe().round(3).to_string().replace("\n", " | "))
p("end reasons: " + sh.end.value_counts().to_string().replace("\n", " | "))
p("t_since_event of shots: " + sh.t_since_event_s.describe().round(2).to_string().replace("\n", " | "))
p("minF before/win kN min: %.2f / %.2f; max drop %.2f" % (sh.minF_before_kN.min(), sh.minF_win_kN.min(), (sh.minF_before_kN - sh.minF_win_kN).max()))
txt = "\n".join(lines)
Path(a.out).write_text(txt, encoding="utf-8")
print(txt)
