"""G' window shift, part 5: re-contact time of a shallower drop from the stored airborne trajectory.

Argument (data, no simulation): after the event pad has lifted (t ~ 0.015 s), neither the plant nor the
controller can see the final floor depth until the pad touches again (pressure, stroke and IMU are the
same), so the body and pad trajectory up to the first re-contact is that of the stored 30 mm run. With
the floor final level 5 mm higher (25 mm), the pad touches when the stored gap (clearance above the
30 mm floor) reaches 5 mm. The only difference before the lift (0 ... ~0.016 s: slower floor descent of
25/0.05) is a small extra upward impulse on the event corner; it is taken from the reduced model
(g04/g06 difference) and added afterwards. For 30 mm / 0.04 s the final floor is the same; only the
pre-lift difference matters (g06).
Output: g05_contact_shift.csv (per stored rerun: t at gap = 5 mm, closing speed there and at contact).
Usage: python -I -B g05_contact_shift.py <out_folder>
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

out = Path(sys.argv[1])
z = np.load(out / "g02_traces.npz")
meta = {r["run"]: r for r in csv.DictReader((out / "g02_traces.csv").open(encoding="utf-8"))}
res = []
for key in z.files:
    tt, Fe, ge, ve, Fd, gd = z[key]
    m = meta[key]
    t_gm = float(m["t_gap_max_s"])
    t_c = float(m["t_contact_s"])
    for dz in (5.0e-3,):
        w = np.flatnonzero((tt > t_gm) & (tt < t_c + 0.002))
        g = ge[w]
        j = int(np.flatnonzero(g <= dz)[0])
        # linear interpolation of the crossing
        t1, t0 = tt[w[j]], tt[w[j - 1]]
        g1, g0 = g[j], g[j - 1]
        tx = float(t0 + (g0 - dz) / (g0 - g1) * (t1 - t0))
        k0 = max(j - 5, 0)
        v_x = float((g[k0] - g[min(j + 5, len(g) - 1)]) / (tt[w[min(j + 5, len(g) - 1)]] - tt[w[k0]]))
        gd_x = float(np.interp(tx, tt, gd))
        gd_c = float(np.interp(t_c, tt, gd))
        res.append({"run": key, "setting": m["setting"], "leg": m["leg"], "fs_kN": m["fs_kN"],
                    "offset_s": m["offset_s"], "t_contact_30_s": t_c, "t_gap5mm_s": round(tx, 4),
                    "dt_contact_25_minus_30_s": round(tx - t_c, 4), "v_close_at_5mm_m_s": round(v_x, 4),
                    "v_impact_30_m_s": float(m["v_impact_m_s"]), "diag_gap_at_contact25_mm": round(gd_x * 1e3, 2),
                    "diag_gap_at_contact30_mm": round(gd_c * 1e3, 2)})
with (out / "g05_contact_shift.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(res[0]))
    w.writeheader()
    w.writerows(res)
d = np.array([r["dt_contact_25_minus_30_s"] for r in res])
v5 = np.array([r["v_close_at_5mm_m_s"] for r in res])
print(json.dumps({"status": "ok", "n": len(res), "dt_c25_min": float(d.min()), "dt_c25_mean": float(d.mean()),
                  "dt_c25_max": float(d.max()), "v5_min": float(v5.min()), "v5_max": float(v5.max())}))
for r in res:
    print(json.dumps(r))
