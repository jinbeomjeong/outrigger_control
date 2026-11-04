"""Where and how much do the new rows differ from p1r before the event; the same check for F_s 4 (p1r vs final). Read only."""
from pathlib import Path

import numpy as np

S8 = Path(r"C:\workspace\outrigger_control\07_results\S8")
P1R = S8 / "p1r_20261024_222013"
HERE = Path(__file__).resolve().parent
NEW = sorted(HERE.glob("final_E_G4_Fs0Fs8_ph0.05_off_*"))[-1]
PAIRS = {"Fs0_ph0.05": (NEW / "E_G4_Fs0_ph0.05", P1R / "E_G4_Fs0_ph0.05"),
         "Fs8_ph0.05": (NEW / "E_G4_Fs8_ph0.05", P1R / "E_G4_Fs8_ph0.05"),
         "Fs4_ph0": (S8 / "final_E_G4_Fs4_20261030_233941/E_G4_Fs4", P1R / "E_G4_Fs4"),
         "Fs4_ph0.05": (next(HERE.glob("final_E_G4_Fs4_ph0.05_off_*")) / "E_G4_Fs4_ph0.05", P1R / "E_G4_Fs4_ph0.05")}
for name, (a_d, b_d) in PAIRS.items():
    a, b = np.load(a_d / "record/record.npz", allow_pickle=False), np.load(b_d / "record/record.npz", allow_pickle=False)
    n = min(len(a["t"]), len(b["t"]))
    t = a["t"][:n]
    print("==", name, "rows", len(a["t"]), len(b["t"]))
    firsts = []
    for k in a.files:
        if k not in b.files or a[k].ndim == 0 or len(a[k]) != len(a["t"]) or len(b[k]) != len(b["t"]) or a[k].dtype.kind != "f":
            continue
        x, y = a[k][:n], b[k][:n]
        same = ((x == y) | (np.isnan(x) & np.isnan(y))).reshape(n, -1).all(axis=1)
        if not same.all():
            i = int(np.argmin(same))
            d = np.abs(x - y).reshape(n, -1)
            firsts.append((round(float(t[i]), 2), k, float(np.nanmax(d[i])), float(np.nanmax(d[: min(i + 100, n)]))))
    for row in sorted(firsts)[:8]:
        print("   first t, key, max at first, max within +10 s:", row)
    if not firsts:
        print("   record equal")
    # pre-event true states
    for k, scale in (("F_cyl", 1e-3), ("s_motor", 1e3)):
        d = np.abs(a[k][:n] - b[k][:n]) * scale
        for tq in (10.0, 20.0, 30.0, 40.0, 50.0):
            j = int(np.searchsorted(t, tq))
            print("   ", k, "t", tq, "max leg diff", float(d[j].max()))
