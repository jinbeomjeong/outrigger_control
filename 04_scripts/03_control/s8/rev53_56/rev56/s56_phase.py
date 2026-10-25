"""Phase transitions (10 Hz r8_series) and selected controller events after the event, E / A / 768.

usage: s56_phase.py ID [ID ...]
"""
import json
import os
import re
import sys
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = str(REPO / r"07_results\S8")
B = {"E": ROOT + r"\c37_20261025_180821\E_drain\episodes",
     "A": ROOT + r"\c36_20261025_155317\A_rt\episodes",
     "R": ROOT + r"\ml_main_20261025_090131\episodes"}
PAT = re.compile(r"t_s=([-0-9.e]+), name='([^']+)'")
SKIP = ("leg_reapproach_start", "leg_reapproach_end", "INFO_PRESSURE_STEP")

for c in sys.argv[1:]:
    print("=" * 10, c)
    for b, root in B.items():
        p = os.path.join(root, c)
        r = json.load(open(os.path.join(p, "result.json"), encoding="utf-8"))
        te = float(r["event_t_s"])
        s = np.load(os.path.join(p, "r8_series.npz"), allow_pickle=True)
        t, ph = s["t"] - te, [str(x) for x in s["phase"]]
        tr = [(round(float(t[0]), 1), ph[0])] + [(round(float(t[i]), 1), ph[i]) for i in range(1, len(t))
                                                 if ph[i] != ph[i - 1] and t[i] >= -0.05]
        print(" ", b, "phases:", tr)
        ev = []
        for e in json.load(open(os.path.join(p, "controller_events.json"), encoding="utf-8")):
            m = PAT.search(e)
            if m and float(m.group(1)) >= te + 3.0 and not m.group(2).startswith(SKIP):
                ev.append((round(float(m.group(1)) - te, 2), m.group(2)))
        print("    events >= +3 s:", ev[:40])
