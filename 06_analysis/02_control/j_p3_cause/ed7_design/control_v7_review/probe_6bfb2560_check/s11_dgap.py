"""D part: the smallest-margin condition reads and the ③ trace around them."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
D = pd.read_csv(OUT / "d_condition_reads.csv")
D["k_in_leg"] = D.groupby(["key", "plant", "leg"]).cumcount()
print("gap by position of the carry read after the transition (0 = first):")
print(D.groupby(["plant", "k_in_leg"])[["gap_read_bar", "gap_pre_release_bar"]].agg(["min", "median"]).to_string())
print("\nper (key, plant, leg) first read:")
f = D[D.k_in_leg == 0]
print(f[["key", "plant", "leg", "t_s", "t_transition_s", "used_bar", "p_tr_read_bar", "p_tr_pre_release_bar",
         "gap_read_bar", "gap_pre_release_bar"]].sort_values("gap_pre_release_bar").to_string(index=False))
print("\nreads with gap_pre_release < 7.9 bar:", int((D.gap_pre_release_bar < 7.9).sum()), "of", len(D),
      "; lines:", D[D.gap_pre_release_bar < 7.9].groupby(["key", "plant"]).ngroups)
print("reads with gap_read < 7.9 bar:", int((D.gap_read_bar < 7.9).sum()))

DIR = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
       r"\6bfb2560\ed7_probe_a1\ed7_probe_t4h")
LEGS = ["FL", "FR", "RL", "RR"]
for name, leg, t0, t1 in [("R12_bottom-FL-Fs2-o0.075-FS24-level_P7-M-a2.npz", None, None, None),
                          ("R12_bottom-RR-Fs0-o0.05-FS24-level_P7-M-a2.npz", None, None, None)]:
    key = name.split("_P7-")[0]
    rows = D[(D.key == key) & (D.plant == "M")]
    worst = rows.sort_values("gap_pre_release_bar").iloc[0]
    li = LEGS.index(worst.leg)
    t0, t1 = worst.t_transition_s - 1.5, worst.t_s + 0.3
    with np.load(f"{DIR}\\{name}") as d:
        t = d["jp3_t_s"]
        cls = [str(s) for s in d["jp3_class_names"]]
        pst = [str(s) for s in d["jp3_plant_state_names"]]
        src = [str(s) for s in d["jp3_source_names"]]
        sel = np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9))
        print(f"\n== {name} leg {worst.leg}")
        print("t class pstate used model carry ext p_tr src inherited u[mm/s] gate_fill x need open rod_rel")
        for k in sel:
            print(f"{t[k]:6.1f} {cls[d['jp3_class'][k, li]]:9s} {pst[d['jp3_plant_state'][k, li]]:10s} "
                  f"{d['jp3_used_bound_Pa'][k, li]/1e5:7.2f} {d['jp3_model_bound_Pa'][k, li]/1e5:7.2f} "
                  f"{d['jp3_carry_bound_Pa'][k, li]/1e5:7.2f} {d['jp3_ext_bound_Pa'][k, li]/1e5:7.2f} "
                  f"{d['jp3_p_tr_Pa'][k, li]/1e5:7.2f} {src[d['jp3_model_bound_source'][k, li]]:15s} "
                  f"{int(d['jp3_model_bound_inherited'][k, li])} {d['jp3_u_m_s'][k, li]*1e3:7.3f} "
                  f"{d['jp3_gate_fill_m'][k, li]*1e3:6.3f} {d['p1_x_m'][k, li]*1e3:6.3f} "
                  f"{d['p1_need_m'][k, li]*1e3:6.3f} {int(d['p1_is_open'][k, li])} {int(d['p1_rod_released'][k, li])}")
