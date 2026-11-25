"""Summaries of s05 outputs for the report (argv[1] = s05 output folder)."""
import sys
from pathlib import Path

import pandas as pd

OUT = Path(sys.argv[1])
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
L = pd.read_csv(OUT / "lines.csv")
R = pd.read_csv(OUT / "d6_rounds.csv")
S = pd.read_csv(OUT / "probe_retract_segments.csv")
D = pd.read_csv(OUT / "d_condition_reads.csv")
SH = pd.read_csv(OUT / "ib_shots.csv")

print("=== P7-8: D part lines ===")
d = L[L.part == "d"].copy()
cols = ["key", "plant", "final_phase", "faults", "warns", "cond_reads_tool", "cond_reads_indep",
        "cond_breach_tool", "cond_breach_indep", "cond_min_gap_read_bar", "cond_min_gap_pre_release_bar",
        "ebc_jp3a_breach_reads", "ebc_jp3b_breach_reads", "ebc_jp3c_breach_reads", "rod_fallback",
        "min_F_after_event_kN", "event_pass", "n_info_d6", "n_warn_retract", "ib_triggers"]
print(d[cols].sort_values(["plant", "key"]).to_string(index=False))
print("D lines", len(d), "faults>0", (d.faults.fillna("") != "").sum(), "final fault",
      (d.final_phase == "fault").sum())
print("D reads by plant: min gap read / pre-release")
print(D.groupby("plant")[["gap_read_bar", "gap_pre_release_bar"]].agg(["count", "min", "median", "max"]))

print("\n=== whole probe: faults / final phase by plant x arm ===")
L["has_fault"] = L.faults.fillna("") != ""
print(pd.crosstab([L.plant], L.arm, values=L.has_fault, aggfunc="sum"))
print(L[L.has_fault][["key", "plant", "arm", "faults", "final_phase"]].to_string(index=False))
print("final_phase counts", L.final_phase.value_counts().to_dict())

print("\n=== condition tool states for judged plants (main part) ===")
m = L[(L.part == "main") & (~L.head_only.astype(bool))]
print(m.groupby("plant")[["cond_reads_indep", "cond_breach_indep"]].sum())
print("min gap read by plant", m.groupby("plant").cond_min_gap_read_bar.min().to_dict())
print("min gap pre-release by plant", m.groupby("plant").cond_min_gap_pre_release_bar.min().to_dict())

print("\n=== D6 witness rounds by plant x arm ===")
R["opened"] = R.is_opened.astype(bool)
g = R.groupby(["plant", "arm"]).agg(rounds=("opened", "size"), not_opened=("opened", lambda s: (~s).sum()),
                                    reversed=("is_reversed", "sum"),
                                    target_reached=("retract_target_reached", lambda s: (s == True).sum()),
                                    wit_min_mm=("retract_witness_mm", "min"),
                                    wit_med_mm=("retract_witness_mm", "median"),
                                    rise_min=("rise_bar", "min"), rise_med=("rise_bar", "median"),
                                    rise_max=("rise_bar", "max"), req_max=("required_bar", "max"),
                                    extra_med_mm=("retract_extra_m", lambda s: s.median() * 1e3),
                                    extra_max_mm=("retract_extra_m", lambda s: s.max() * 1e3))
print(g.to_string())
print("rise < required (judgeable rounds):")
j = R[R.opened]
print(j[j.rise_bar < j.required_bar].groupby(["plant", "arm"]).size())
print("not-opened rounds detail:")
print(R[~R.opened][["key", "plant", "arm", "leg", "t_s", "retract_witness_mm", "is_reversed",
                    "k1_mid_opened", "rise_bar", "required_bar", "retract_extra_m",
                    "retract_target_reached"]].to_string(index=False))

print("\n=== INFO_D6 / WARN_RETRACT / rod fallback by plant x arm ===")
print(L.groupby(["plant", "arm"])[["n_info_d6", "n_warn_retract"]].sum().unstack())
L["fb"] = L.rod_fallback.fillna("") != ""
print("lines with rod fallback reason:")
print(L[L.fb][["key", "plant", "arm", "rod_fallback"]].to_string(index=False))

print("\n=== probe retract segments (T4h), by plant x arm ===")
S["seg_kind"] = S.oil_cmd_mm.apply(lambda v: "first(<=2.3mm)" if v <= 2.3 else "with_extra")
gs = S.groupby(["plant", "arm"]).agg(n=("e3_drop_mm", "size"),
                                     opened=("p1_open_any", "sum"),
                                     drop_ge_0p3=("e3_drop_mm", lambda s: (s >= 0.3).sum()),
                                     oil_med=("oil_cmd_mm", "median"),
                                     x_over_need_min=("p1_max_x_over_need", "min"),
                                     x_over_need_med=("p1_max_x_over_need", "median"),
                                     ph_max=("p_h_read_bar", "max"),
                                     ptr_rise_med=("p_tr_rise_bar", "median"))
print(gs.to_string())
print("segments not opened (p1_open_any False):")
no = S[S.p1_open_any == False]
print(no.groupby(["plant", "arm"]).size())
print(no[["key", "plant", "arm", "leg", "t_start_s", "oil_cmd_mm", "e3_drop_mm", "p_h_read_bar",
          "stroke_before_mm", "p1_need_mm", "p1_max_x_mm", "p1_max_x_over_need", "p_tr_rise_bar",
          "p_r_read_before_bar", "p_r_read_after_bar"]].to_string(index=False))

print("\n=== reversed rounds and k1_mid_opened ===")
rv = R[R.is_reversed == True]
print(rv[["key", "plant", "arm", "leg", "t_s", "retract_witness_mm", "is_opened", "k1_mid_opened",
          "rise_bar", "required_bar", "retract_extra_m", "retract_target_reached"]].to_string(index=False))
print(L.groupby(["plant", "arm"])[["rev_not_sub", "rev_sub"]].sum().unstack())

print("\n=== A_ib by plant x arm ===")
print(L.groupby(["plant", "arm"])[["ib_triggers", "ib_unknown", "ib_latches", "ib_n_rev",
                                    "ib_protect_periods", "ib_four_leg", "ib_shots_grew",
                                    "n_latch_ev", "n_protect_ev", "n_cap_ev"]].sum().to_string())
print("edges vs triggers notes:", L.ib_on_edges_vs_triggers.dropna().tolist()[:20])
print("shots completion_known False:")
print(SH[SH.completion_known == False][["key", "plant", "arm", "leg", "sign", "start_t_s", "end",
                                       "delta_D_N"]].to_string(index=False))
print("shot end reasons:", SH.end.value_counts(dropna=False).to_dict())
lat = L[L.ib_latches.fillna(0) > 0]
print("latched lines:")
print(lat[["key", "plant", "arm", "ib_triggers", "ib_n_rev", "ib_latches", "n_latch_ev"]].to_string(index=False))
