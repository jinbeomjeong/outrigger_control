"""Final tables: P7-7 open ratios (2 mm only, c2), witness, item 3 records, item 4 table proposal."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 500)
S = pd.read_csv(OUT / "probe_retract_segments.csv")
L = pd.read_csv(OUT / "lines.csv")
R = pd.read_csv(OUT / "d6_rounds.csv")
SH = pd.read_csv(OUT / "ib_shots.csv")
S = S[S.oil_cmd_mm >= 1.5].copy()
S["front"] = S.leg.isin(["FL", "FR"])
S["ratio_sent"] = S.oil_cmd_mm / S.p1_ret_need_first_mm
S["ratio_fill"] = S.p1_ret_x_max_mm / S.p1_ret_need_at_xmax_mm
c2 = S[S.arm == "c2"]
print("=== c2 (2 mm only) retract line: opened (line dir -1) by plant / front ===")
print(c2.groupby(["plant", "front"]).agg(n=("p1_open_ret", "size"), opened=("p1_open_ret", "sum"),
                                         ratio_sent_min=("ratio_sent", "min"),
                                         ratio_sent_med=("ratio_sent", "median"),
                                         ratio_fill_min=("ratio_fill", "min"),
                                         ratio_fill_med=("ratio_fill", "median")).to_string())
print("\nc2 not opened rows")
no = c2[~c2.p1_open_ret.astype(bool)]
print(no[["key", "plant", "leg", "t_start_s", "oil_cmd_mm", "p1_ret_x_max_mm", "p1_ret_need_at_xmax_mm",
          "ratio_sent", "ratio_fill", "e3_drop_mm", "p_h_read_bar", "stroke_before_mm", "p_tr_rise_bar"]]
      .sort_values(["plant", "key", "t_start_s"]).to_string(index=False))
print("\nc2 opened but e3 drop < 0.3 mm:")
ow = c2[c2.p1_open_ret.astype(bool) & (c2.e3_drop_mm < 0.3)]
print(ow[["key", "plant", "leg", "t_start_s", "oil_cmd_mm", "ratio_fill", "e3_drop_mm", "p_h_read_bar"]]
      .to_string(index=False))
print("\nwitness arms: segments not opened on the retract line:", int((~S[S.arm != "c2"].p1_open_ret.astype(bool)).sum()))
# R12 FL state rows
st = S[(S.leg == "FL") & S.key.str.startswith("R12_top-") & S.key.str.contains("Fs0-o0")
       & (S.t_start_s.between(32.0, 32.2)) & S.plant.isin(["M", "Mslow"])]
print("\nR12 FL state (t 32.1 s, p_h 99.48 bar, s 408.36 mm), keys top-FR/RL-Fs0:")
print(st[["key", "plant", "arm", "oil_cmd_mm", "p1_ret_x_max_mm", "p1_ret_need_first_mm",
          "p1_ret_need_at_xmax_mm", "ratio_sent", "ratio_fill", "p1_open_ret", "e3_drop_mm",
          "p_tr_rise_bar"]].sort_values(["plant", "arm", "key"]).to_string(index=False))
print("\nM c2 opened: p_tr rise by front/rear")
print(c2[(c2.plant == "M") & c2.p1_open_ret.astype(bool)].groupby("front").p_tr_rise_bar.describe().to_string())

# ---- item 3 ----
print("\n=== item 3: reversed rounds ===")
print("rows is_reversed:", int((R.is_reversed == True).sum()), "rev_not_sub sum:", L.rev_not_sub.sum(),
      "rev_sub sum:", L.rev_sub.sum())
print("k1_mid_opened values on non-reversed rows:", R[R.is_reversed == False].k1_mid_opened.isna().all())
print("lines with d6 record by arm:", L[L.has_d6_record].groupby("arm").size().to_dict())
ev = L[~L.head_only.astype(bool)]
print("event-path lines by arm / has_d6_record:")
print(pd.crosstab(ev.arm, ev.has_d6_record))
print("head-only lines with d6 record:", int((L.head_only.astype(bool) & L.has_d6_record).sum()))
print("\n=== item 3: A_ib ===")
print("completion_known False shots:", int((SH.completion_known == False).sum()), "of", len(SH))
print(SH.groupby(["arm"]).agg(shots=("leg", "size"), unknown=("completion_known", lambda s: (s == False).sum())).to_string())
print("lines ib_unknown>0:")
print(L[L.ib_unknown.fillna(0) > 0][["key", "plant", "arm", "ib_triggers", "ib_unknown"]].to_string(index=False))
print("latched lines:")
print(L[L.ib_latches.fillna(0) > 0][["key", "plant", "arm", "ib_triggers", "ib_n_rev", "ib_latches", "n_latch_ev"]].to_string(index=False))
print("n_rev>0 lines:")
print(L[L.ib_n_rev.fillna(0) > 0][["key", "plant", "arm", "ib_triggers", "ib_n_rev", "ib_latches"]].to_string(index=False))
print("protect blocked:", L.ib_protect_periods.sum(), "protect events:", L.n_protect_ev.sum())
print("ib_on rising edges != triggers notes:",
      L.ib_on_edges_vs_triggers.dropna().tolist() if "ib_on_edges_vs_triggers" in L else "none")
print("event-path a1 lines without d6 record:")
print(ev[(ev.arm == "a1") & ~ev.has_d6_record.astype(bool)][["key", "plant", "final_phase", "t_event_s",
                                                             "d6_missing_note"]].to_string(index=False))
sc = 0
for (k, p, a_, leg), g_ in SH.sort_values("start_t_s").groupby(["key", "plant", "arm", "leg"]):
    sc += int((g_.sign.diff().fillna(0) != 0).sum())
print("fired sign changes (same leg, any LEVEL) over all shots:", sc)
print("shots per (line, leg) max:", SH.groupby(["key", "plant", "arm", "leg"]).size().max())
print("A_ib off arms (a1) with blind triggers:", L[(L.arm == "a1")].ib_triggers.fillna(0).sum())
print("shot end reasons by arm:")
print(pd.crosstab(SH.arm, SH.end.fillna("none")))

# ---- item 4: proposal table, arm a2 (and a1 for reference), main part ----
print("\n=== item 4: per key x plant, arm a2 (main part) ===")
a = L[(L.part == "main") & (L.arm == "a2")].copy()
d6n = R.groupby(["key", "plant", "arm"]).is_opened.apply(lambda s: int((~s.astype(bool)).sum()))
a["d6_not_judgeable"] = [d6n.get((k, p, "a2"), np.nan) for k, p in zip(a.key, a.plant)]
cols = ["key", "plant", "min_F_after_liftoff_kN", "min_F_after_event_kN", "level_after_event_s",
        "ib_triggers", "ib_dD_med_kN", "ib_dD_max_kN", "ib_four_leg", "ib_n_rev", "ib_latches",
        "d6_not_judgeable", "cond_reads_indep", "cond_breach_indep", "final_phase", "faults"]
print(a[cols].sort_values(["key", "plant"]).to_string(index=False))
print("\nD part (a2) same columns:")
d = L[L.part == "d"].copy()
d["d6_not_judgeable"] = [d6n.get((k, p, "a2"), np.nan) for k, p in zip(d.key, d.plant)]
print(d[cols].sort_values(["key", "plant"]).to_string(index=False))
print("\nfinal_phase != ready:")
print(L[L.final_phase != "ready"][["key", "plant", "arm", "part", "final_phase", "warns"]].to_string(index=False))
