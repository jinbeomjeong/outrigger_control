"""D-S8-5 (1): seal-friction state through the CHECK zero-calibration round trip.

For each leg prints, per CHECK stage window (from the 10 Hz controller record), the 1 ms truth:
F_cyl (rod axial force), f_seal, seal_stuck share, stroke motion, and the pressures; then the
hold means used by the calibration and the implied friction residual
    c_fric = -(mean f_e + mean f_r) / 2 + (mean F_e + mean F_r) / 2 + m_rod g
(ideal reading F - f; the controller c_i uses the 10 Hz readings).
Usage: python -I ds85_check_holds.py <case dir> [leg ...]
"""
import json
import os
import sys

import numpy as np

d = sys.argv[1]
legs = [int(x) for x in sys.argv[2:]] or [0, 1, 2, 3]
pads = np.load(os.path.join(d, "pads.npz"))
r8 = np.load(os.path.join(d, "r8_series.npz"))
with open(os.path.join(d, "result.json"), encoding="utf-8") as fh:
    res = json.load(fh)
zc = res["controller_meta"]["zero_calibration"]
off = np.array(zc["offsets_N"])
t0, t1 = zc["result"]["t_start_s"], zc["result"]["t_end_s"]
start = res["settings"]["start_t_s"]  # record time of controller t = 0
tp = pads["t"]
t8 = r8["t"]
u = r8["issued_u"]
print("case", os.path.basename(d), "CHECK controller t", t0, t1, "record offset", round(start, 3))
print("t8 range", t8[0], t8[-1], "pads t range", tp[0], tp[-1])
# controller time -> record time: r8 t is already record time? compare with phases
ph = r8["phase"]
k_chk = np.flatnonzero(ph == "check")
print("r8 check rows t", t8[k_chk[0]], t8[k_chk[-1]])
rodw = np.array([1047.2, 1047.2, 718.0, 718.0])
for leg in legs:
    print(f"--- leg {leg}  c_i {off[leg]:+.1f} N")
    # stage segmentation by issued command sign of this leg within CHECK rows
    seg = []
    for k in k_chk:
        s = np.sign(round(u[k, leg] * 1e6))
        if not seg or seg[-1][0] != s:
            seg.append([s, t8[k], t8[k]])
        else:
            seg[-1][2] = t8[k]
    for s, a, b in seg:
        m = (tp >= a) & (tp < b + 0.1)
        print(f"  cmd {s:+.0f} t[{a:.2f},{b + 0.1:.2f}) F_cyl {pads['F_cyl'][m, leg].mean():8.1f} "
              f"[{pads['F_cyl'][m, leg].min():8.1f},{pads['F_cyl'][m, leg].max():8.1f}] "
              f"f {pads['f_seal'][m, leg].mean():8.1f} [{pads['f_seal'][m, leg].min():8.1f},{pads['f_seal'][m, leg].max():8.1f}] "
              f"stuck {pads['seal_stuck'][m, leg].mean():.2f} p_h {pads['head_pressure'][m, leg].mean() / 1e5:6.2f} "
              f"p_r {pads['rod_pressure'][m, leg].mean() / 1e5:6.2f} bar  s_mot {1e3 * pads['s_motor'][m, leg].mean():7.3f} "
              f"s_p {1e3 * pads['s_piston'][m, leg].mean():7.3f} mm")
    # hold windows used by calibration: zero command rows after the first move
    holds = [(a, b + 0.1) for s, a, b in seg if s == 0 and a > seg[0][1] + 1e-9]
    print("  holds", [(round(a, 2), round(b, 2)) for a, b in holds])
