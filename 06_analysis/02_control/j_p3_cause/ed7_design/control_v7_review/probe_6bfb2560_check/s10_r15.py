"""R15 Mslow a1 lines without D6 record: probe phases and retract segments."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(sys.argv[1])
S = pd.read_csv(OUT / "probe_retract_segments.csv")
for key in ("R15_o0.0", "R15_o0.05"):
    for arm in ("a1", "a2"):
        s = S[(S.key == key) & (S.plant == "Mslow") & (S.arm == arm) & (S.oil_cmd_mm >= 1.5)]
        print(key, arm, "probe retract segments:", len(s), s[["leg", "t_start_s", "oil_cmd_mm", "p1_open_ret"]].values.tolist())
    name = f"{key}_P7-Mslow-a1.npz"
    d = np.load(rf"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560\ed7_probe_a1\ed7_probe_t4h\{name}")
    ph = np.array([str(p) for p in d["phase"]])
    t = d["t_s"]
    changes = [(round(float(t[0]), 1), ph[0])] + [(round(float(t[k]), 1), ph[k]) for k in range(1, len(ph)) if ph[k] != ph[k - 1]]
    print(name, "phase changes:", changes, "t_end", round(float(t[-1]), 1))
