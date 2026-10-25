"""Why do some bundle-A episodes level slower than 768? Events, flags and attitude timeline."""
import json
import os
import re
import sys
from collections import Counter
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = str(REPO / r"07_results\S8")
A = ROOT + r"\c36_20261025_155317\A_rt\episodes"
REF = ROOT + r"\ml_main_20261025_090131\episodes"
pat = re.compile(r"t_s=([0-9.]+), name='([^']+)'")


def rp(q):
    w, x, y, z = q.T
    roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    pitch = np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))
    return roll, pitch


def show(path, tag):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    ev = json.load(open(os.path.join(path, "controller_events.json"), encoding="utf-8"))
    evs = []
    for e in ev:
        m = pat.search(e)
        if m and float(m.group(1)) >= te - 0.05:
            evs.append((round(float(m.group(1)) - te, 1), m.group(2)))
    c = Counter(n.split(":")[0] for _, n in evs)
    print(f"  [{tag}] event counts:", dict(c))
    print(f"  [{tag}] non-step events:", [x for x in evs if not x[1].startswith("INFO_PRESSURE_STEP")][:40])
    s = np.load(os.path.join(path, "r8_series.npz"))
    t = s["t"] - te
    rec = np.load(os.path.join(path, "record", "record.npz"))
    roll, pitch = rp(rec["body_quat_wxyz"])
    tr = rec["t"] - te
    flags = s["limit_flags"]
    for tt in (1, 3, 5, 8, 10, 12, 15, 18, 21, 24, 27):
        i = int(np.argmin(np.abs(t - tt)))
        j = int(np.argmin(np.abs(tr - tt)))
        print(f"   t+{tt:2d} ph={s['phase'][i]:6s} roll={roll[j]:+.3f} pitch={pitch[j]:+.3f} "
              f"u[mm/s]={np.round(s['issued_u'][i]*1e3, 2)} guard={bool(s['guard_active'][i])} "
              f"Flow[kN]={np.round(s['F_lower_est_N'][i]/1e3, 1)} band={np.round(s['leg_band_N'][i]/1e3, 1)} flags={flags[i][:90]}")


for case in sys.argv[1:]:
    print("=====", case)
    show(os.path.join(A, case), "A")
    show(os.path.join(REF, case), "R")
