"""Ed. 7 dynamics review (Q7-D1, Q7-D2), step 0: list the T4h arrays of one counterfactual C line
(dynamics-expert, 2026-11-24, analysis only, read only). stdout ASCII."""
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\records_after_stop\C_a2\counterfactual_t4h")

for name in ("R12_top-FR-Fs0-o0.0_P6-J-a1a2b3.npz",):
    with np.load(T4H / name, allow_pickle=False) as d:
        for k in d.files:
            a = d[k]
            print(f"{k:40s} {str(a.dtype):10s} {a.shape}")
