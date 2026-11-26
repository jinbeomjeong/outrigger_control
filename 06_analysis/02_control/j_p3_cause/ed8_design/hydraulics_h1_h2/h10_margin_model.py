"""h10: hand model of the K1-window overlap, checked against the T4h windows of h03 (R12 rows only:
the case seal limit is known, base 4 kN, twin rows their ``fs_kN``; front F_s, rear 0.833 F_s).

  oil the plant takes after the head-check opening before the K1 mid read:  ds_mid (T4h)
  oil the stuck seal takes to turn from the retract limit to the extend limit:
      s_stick,max = 2 F_s / k_h(s),  k_h = beta A_h / (L0h + s)   (beta 1 GPa, L0h 0.05 m, ASSUMED)
  margin m = ds_mid - s_stick,max  (m < 0: the end of the stick lies inside the K1 window)

Reports the slope of the first K1-window interval and the warned-round share in bins of m, per
setting group; legs 2-4 of a round (extend line filled from empty, x_open known).
Also checks the line-fill formula x_open = (p_a,open - p_T) s_L V_line / (A_h beta_hose) with the
recorded p_a at the opening (p_T 2 bar, V_line 285 cm3, beta_hose 0.5 GPa: CheckValveValues
defaults, ASSUMED to be the plant values).

Output: h10_out.txt
"""
import csv
import math
import os
from collections import defaultdict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(OUT, "h03_rows.csv"), encoding="utf-8"))
        if r["reversed"] == "False" and r["key"].startswith("R12") and r["x_open_mm"] != ""]
A_H = {"F": math.pi / 4 * 0.13 ** 2, "R": math.pi / 4 * 0.11 ** 2}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


lines = []
# line fill formula check
err = []
for r in rows:
    a_h = A_H[r["leg"][0]]
    pa = f(r["p_a_open_bar"])
    sl = f(r["line_scale"]) if r["line_scale"] else 1.0
    pred = (pa - 2.0) * 1e5 * sl * 285e-6 / (a_h * 0.5e9) * 1e3
    err.append(pred - f(r["x_open_mm"]))
err = np.array(err)
lines.append(f"x_open formula check (n {len(err)}): pred - recorded med {np.median(err):.4f} mm,"
             f" max |.| {np.max(np.abs(err)):.4f} mm")

GROUPS = {"s_L 0.5 (h05, fast)": ("VBMh05", "VBMfast"),
          "s_L 1.0 (VBM j9main, sens b/c/d)": ("VBM", "VBMb069", "VBMb16", "VBMc005", "VBMc04",
                                               "VBMd05", "VBMd15"),
          "s_L 1.5 (h15, slow)": ("VBMh15", "VBMslow"),
          "probe a2 (M, Mslow, Mfast, Mc005, Mc04, L)": tuple(f"P7-{p}-a2" for p in
                                                              ("M", "Mslow", "Mfast", "Mc005", "Mc04", "L")),
          "probe c2 (same plants)": tuple(f"P7-{p}-c2" for p in
                                          ("M", "Mslow", "Mfast", "Mc005", "Mc04", "L")),
          "probe Mslow-a2 only": ("P7-Mslow-a2",),
          "probe Mslow-c2 only": ("P7-Mslow-c2",),
          "probe M-c2 only": ("P7-M-c2",)}
BINS = [(-9, -0.2), (-0.2, -0.1), (-0.1, 0.0), (0.0, 0.1), (0.1, 0.2), (0.2, 9)]
allm = []
for name, settings in GROUPS.items():
    sub = [r for r in rows if r["setting"] in settings]
    lines.append(f"== {name}: windows {len(sub)}")
    acc = defaultdict(list)
    for r in sub:
        fs_kN = 4.0
        if "Fs" in r["key"]:
            fs_kN = float(r["key"].split("Fs")[1])
        fs = fs_kN * 1e3 * (1.0 if r["leg"][0] == "F" else 0.8333)
        s = f(r["s_start_mm"]) * 1e-3
        kh = 1.0e9 * A_H[r["leg"][0]] / (0.05 + s)
        stick = 2.0 * fs / kh * 1e3
        m = f(r["ds_mid_mm"]) - stick
        allm.append((name, m, f(r["slope_win1_MN_m"]), r["round_warn_ratio"] != ""))
        for lo, hi in BINS:
            if lo <= m < hi:
                acc[(lo, hi)].append((f(r["slope_win1_MN_m"]), r["round_warn_ratio"] != "", fs_kN))
    for lo, hi in BINS:
        v = acc.get((lo, hi), [])
        if not v:
            continue
        sw = np.array([a for a, _, _ in v])
        sw = sw[np.isfinite(sw)]
        wr = np.mean([b for _, b, _ in v])
        fsd = defaultdict(int)
        for _, _, c in v:
            fsd[c] += 1
        lines.append(f"  m in [{lo:+.1f}, {hi:+.1f}) mm: n {len(v):3d} slope_win1 med "
                     f"{(np.median(sw) if len(sw) else float('nan')):6.2f} MN/m, warned-round share "
                     f"{wr:.2f}, F_s mix {dict(sorted(fsd.items()))}")
with open(os.path.join(OUT, "h10_out.txt"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("\n".join(lines) + "\n")
print("\n".join(lines))
