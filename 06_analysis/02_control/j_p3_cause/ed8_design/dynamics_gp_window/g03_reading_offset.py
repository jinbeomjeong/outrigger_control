"""G' window shift, part 3: offset between the true event-leg force (1 ms column F = contact - W_rod)
and the controller's lower load estimate L (u11_periods, = cylinder force lower - seal band) at the
10 Hz samples of the stored reruns. Gives the controller-effective exit threshold in true-force terms,
F_thr = F_exit + (F_true - L), on the loading (re-contact) and the unloading (hold end) edges, per F_s.
Usage: python -I -B g03_reading_offset.py <u832_folder> <out_folder>
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

src, out = Path(sys.argv[1]), Path(sys.argv[2])
z = np.load(out / "g02_traces.npz")
tr = {r["run"]: r for r in csv.DictReader((out / "g02_traces.csv").open(encoding="utf-8"))}
periods = list(csv.DictReader((src / "u11_periods.csv").open(encoding="utf-8")))
rows = []
for p in periods:
    run = p["run"]                      # e.g. V0|bottom-FR-Fs4-RE1bF-o0.025
    setting, rest = run.split("|")
    lv, leg, fs, ev, off = rest.split("-")
    if ev != "RE1bF":
        continue
    key = f"R12_{lv}-{leg}-{fs}-{off}-{ev}-ready_{setting}"
    if key not in z.files:
        continue
    t_s = float(p["t_rel_s"])
    if not (0.1 <= t_s <= 0.55):
        continue
    tt, Fe = z[key][0], z[key][1]
    i = int(np.argmin(np.abs(tt - t_s)))
    if abs(tt[i] - t_s) > 6e-4:
        continue
    L = float(p[f"load_{leg}_kN"])
    F = float(Fe[i]) / 1e3
    r = tr[key]
    edge = ("air" if F <= 0 else ("load" if t_s < float(r["t_peak_s"]) else "unload"))
    rows.append({"run": key, "setting": setting, "leg": leg, "fs_kN": float(fs[2:]), "t_s": t_s,
                 "F_true_kN": round(F, 2), "L_kN": L, "offset_kN": round(F - L, 2), "edge": edge})
with (out / "g03_reading_offset.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
agg = defaultdict(list)
for r in rows:
    agg[(r["fs_kN"], r["edge"])].append(r["offset_kN"])
lines = ["offset F_true - L [kN] by (Fs, edge): n, min, mean, max"]
for k in sorted(agg):
    v = np.array(agg[k])
    lines.append(f"Fs {k[0]:g} {k[1]:6s} n {v.size:3d}  min {v.min():7.2f} mean {v.mean():7.2f} max {v.max():7.2f}")
(out / "g03_reading_offset.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(json.dumps({"status": "ok", "rows": len(rows)}))
