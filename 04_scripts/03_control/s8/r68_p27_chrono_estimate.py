"""P-S8-27 candidate 1 on the C-S8-73 Chrono records (spec rev. 68 356): first latch time estimate.

Open-loop estimate from the recorded 10 Hz readings of the pre-grounded leg (net two-pressure force
p_h A_p - p_r A_ann, sensor values as delivered): the touchdown load with the P-S8-26 cap is
reading - (m_rod g + F_s,cap) - m_rod g, the level 1.5 F_min. Project rule: latch after 0.5 s of
consecutive samples at the level (``touch_hold_s``; the sample at since + 0.5 s latches). Candidate 1: one sample
below the level is tolerated, two in a row drop the candidate. The record is valid for the candidate up to the
first tolerated dip (the runs diverge there: project resumes the push, candidate stays stopped), so the estimate
is the candidate latch time if it falls before that dip, else 'diverges at'.
Also reported: the motor stroke of that leg from the TOUCH start at the estimated latch (extra stroke estimate).
Threshold sensitivity: the level shifted by +-4 kN (zero-calibration deduction / reading offset unknowns).

Usage: python -I r68_p27_chrono_estimate.py <c73 batch dir>
"""
import sys
from pathlib import Path

import numpy as np

F_MIN = 9414.6
ROD_W = {"FL": 1047.0, "RR": 718.0}
CAP_EXCESS = {"FL": 8000.0, "RR": 6666.4}
AREAS = {"FL": (np.pi / 4 * 0.130 ** 2, np.pi / 4 * (0.130 ** 2 - 0.110 ** 2)),
         "RR": (np.pi / 4 * 0.110 ** 2, np.pi / 4 * (0.110 ** 2 - 0.090 ** 2))}
LEGS = ("FL", "FR", "RL", "RR")


def latch_times(load, level, t, tolerate):
    since, miss = None, 0
    first_dip = None
    for k in range(load.size):
        if load[k] >= level:
            miss = 0
            if since is None:
                since = t[k]
            if t[k] - since >= 0.5 - 1e-9:
                return t[k], first_dip
        else:
            if since is not None and miss < tolerate:
                miss += 1
                if first_dip is None:
                    first_dip = t[k]
                continue
            since, miss = None, 0
    return None, first_dip


for case in ("PS7a_RR_R8", "PS7b_RR_R8", "PS7c_RR_R8", "PS7a_FL_R8"):
    d = Path(sys.argv[1]) / case
    leg = case.split("_")[1]
    j = LEGS.index(leg)
    rec = np.load(d / "record" / "record.npz")
    r8 = np.load(d / "r8_series.npz")
    ph = np.array([str(p) for p in r8["phase"]])
    k = np.flatnonzero(ph == "touch")
    t = r8["t"][k] - r8["t"][k[0]]
    ap, aa = AREAS[leg]
    reading = rec["meas.head_pressure"][k, j] * ap - rec["meas.rod_pressure"][k, j] * aa
    load = reading - (ROD_W[leg] + CAP_EXCESS[leg]) - ROD_W[leg]
    s = rec["s_motor"][k, j] * 1e3
    s = s - s[0]
    proj_latch = r8["touched"][k, j]
    t_proj = t[np.flatnonzero(proj_latch)[0]] if proj_latch.any() else None
    out = [f"{case}: project latch (record) {t_proj:.1f} s, motor stroke there {np.interp(t_proj, t, s):.1f} mm"]
    for dl in (-4000.0, 0.0, 4000.0):
        level = 1.5 * F_MIN + dl
        tp, _ = latch_times(load, level, t, 0)
        tc, dip = latch_times(load, level, t, 1)
        t2, _ = latch_times(load, level, t, 2)
        out.append(f"   level {level / 1e3:5.1f} kN: rule-proj {None if tp is None else round(tp, 1)} s | "
                   f"cand1 latch {None if tc is None else round(tc, 1)} s (first tolerated dip "
                   f"{None if dip is None else round(dip, 1)}) stroke "
                   f"{None if tc is None else round(float(np.interp(tc, t, s)), 1)} mm | 2-dip variant latch "
                   f"{None if t2 is None else round(t2, 1)} s stroke "
                   f"{None if t2 is None else round(float(np.interp(t2, t, s)), 1)} mm")
    print("\n".join(out))
