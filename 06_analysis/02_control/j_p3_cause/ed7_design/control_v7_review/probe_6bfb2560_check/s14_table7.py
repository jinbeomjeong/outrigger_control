"""Section 7 table proposal CSV (fillable columns only, every arm; the seal arm is chosen later)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
L = pd.read_csv(OUT / "lines.csv")
R = pd.read_csv(OUT / "d6_rounds.csv")
nj = R.groupby(["key", "plant", "arm"]).is_opened.apply(lambda s: int((~s.astype(bool)).sum()))
t = pd.DataFrame({
    "key": L.key, "plant": L.plant, "arm": L.arm, "part": L.part,
    "min_F_after_liftoff_kN": L.min_F_after_liftoff_kN,
    "min_F_after_event_kN_all_legs": L.min_F_after_event_kN,
    "level_after_event_s": L.level_after_event_s,
    "done_path_strict_relax": "not_recorded",
    "ib_triggers": L.ib_triggers, "ib_absdD_median_kN": L.ib_dD_med_kN, "ib_absdD_max_kN": L.ib_dD_max_kN,
    "ib_four_leg_twist_triggers": L.ib_four_leg,
    "absD_over_15kN_entries": "not_recorded",
    "ib_n_rev": L.ib_n_rev, "ib_latches": L.ib_latches,
    "d6_not_judgeable_rounds": [nj.get((k, p, a), np.nan) for k, p, a in zip(L.key, L.plant, L.arm)],
    "d6_record_present": L.has_d6_record,
    "jp3_rev7_condition_reads": L.cond_reads_indep, "jp3_rev7_condition_breach_reads": L.cond_breach_indep,
    "jp3_rev7_min_gap_bar": L.cond_min_gap_read_bar,
    "line_jp3a_breach_reads": L.get("ebc_jp3a_breach_reads"),
    "faults": L.faults.fillna(""), "final_phase": L.final_phase, "head_only": L.head_only,
    "commands_sha256": L.commands_sha256})
t = t.sort_values(["part", "arm", "key", "plant"])
t.to_csv(OUT / "table7_proposal_all_arms.csv", index=False)
print("rows", len(t), "status ok")
