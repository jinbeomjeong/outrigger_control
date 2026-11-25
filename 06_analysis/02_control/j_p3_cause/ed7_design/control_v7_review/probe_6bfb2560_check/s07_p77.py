"""P7-7 focus: probe-round retract segments (oil >= 1.5 mm) by plant, arm, leg."""
import sys
from pathlib import Path

import pandas as pd

OUT = Path(sys.argv[1])
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 500)
S = pd.read_csv(OUT / "probe_retract_segments.csv")
R = pd.read_csv(OUT / "d6_rounds.csv")
S = S[S.oil_cmd_mm >= 1.5].copy()
S["front"] = S.leg.isin(["FL", "FR"])
S["moved"] = S.e3_drop_mm >= 0.3
print("probe-round segments (oil >= 1.5 mm)")
g = S.groupby(["plant", "arm"]).agg(n=("moved", "size"), p1_open=("p1_open_any", "sum"),
                                    moved=("moved", "sum"),
                                    oil_min=("oil_cmd_mm", "min"), oil_med=("oil_cmd_mm", "median"),
                                    oil_max=("oil_cmd_mm", "max"),
                                    xn_min=("p1_max_x_over_need", "min"),
                                    xn_med=("p1_max_x_over_need", "median"),
                                    rise_min=("p_tr_rise_bar", "min"),
                                    rise_med=("p_tr_rise_bar", "median"),
                                    rise_max=("p_tr_rise_bar", "max"))
print(g.to_string())
c2 = S[S.arm == "c2"]
print("\nc2 (2 mm only, no witness/target): not opened per plant, front/rear")
print(c2.groupby(["plant", "front"]).agg(n=("moved", "size"), not_open=("p1_open_any", lambda s: (~s.astype(bool)).sum()),
                                         not_moved=("moved", lambda s: (~s).sum())).to_string())
no = c2[~c2.p1_open_any.astype(bool)]
print("\nc2 not-opened segments: x/need, p_h, p_tr rise, rod reading rise")
no = no.assign(rod_rise=no.p_r_read_after_bar - no.p_r_read_before_bar)
print(no[["key", "plant", "leg", "t_start_s", "oil_cmd_mm", "e3_drop_mm", "p_h_read_bar", "stroke_before_mm",
          "p1_need_mm", "p1_max_x_mm", "p1_max_x_over_need", "p_tr_rise_bar", "rod_rise"]]
      .sort_values(["plant", "key", "t_start_s"]).to_string(index=False))
print("\nc2 Mslow opened segments: min/max p_h by front/rear")
op = c2[(c2.plant == "Mslow") & c2.p1_open_any.astype(bool)]
print(op.groupby("front").p_h_read_bar.describe())
nop = c2[(c2.plant == "Mslow") & ~c2.p1_open_any.astype(bool)]
print(nop.groupby("front").p_h_read_bar.describe())
print("\nx/need (2 mm only) by plant for c2, front legs, all segments:")
print(c2.groupby(["plant", "front"]).p1_max_x_over_need.describe().to_string())
print("\nM c2 rise (opened) vs prediction 28-36 bar:")
print(c2[c2.p1_open_any.astype(bool)].groupby("plant").p_tr_rise_bar.describe().to_string())
# rod reading rise for c2 not opened, compare 20.5-21.6
print("\nwitness rows (target on): rise vs plant, front/rear")
R["front"] = R.leg.isin(["FL", "FR"])
print(R.groupby(["plant", "front"]).rise_bar.describe().to_string())
print("\nwitness rows: retract_extra_m (beyond 2 mm) quantiles by plant")
print(R.groupby("plant").retract_extra_m.describe().to_string())
print("target_reached False:", int((R.retract_target_reached != True).sum()))
# R12 FL rounds in Fs0 keys
print("\nR12 Fs0 keys, FL leg segments, plants M / Mslow, arms a2 / c2:")
f = S[S.key.str.contains("Fs0") & S.key.str.startswith("R12") & (S.leg == "FL")
      & S.plant.isin(["M", "Mslow"]) & S.arm.isin(["a2", "c2"])]
print(f[["key", "plant", "arm", "t_start_s", "oil_cmd_mm", "e3_drop_mm", "p_h_read_bar", "stroke_before_mm",
         "p1_need_mm", "p1_max_x_over_need", "p1_open_any", "p_tr_rise_bar"]].sort_values(
    ["key", "arm", "plant", "t_start_s"]).to_string(index=False))
