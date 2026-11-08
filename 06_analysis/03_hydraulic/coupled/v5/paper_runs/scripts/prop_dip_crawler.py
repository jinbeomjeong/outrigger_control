"""Crawler state before and during the rear-only phase (V0 vs prop): body heave, crawler front/rear
point vertical motion, crawler normal force, aligned by rear stroke progress since rear contact.

Crawler points are body points at x = +1.30 / -1.31 m (end-shoe x range, YAML contact.crawler) on the
centre line; vertical displacement from body z and pitch (small angle, pitch > 0 = nose down, so a
point at x moves by -x*dpitch). Units: mm, kN, deg.
"""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {"V0": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
        "prop": R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop"}
XF, XR = 1.30, -1.31
out = {}
for name, p in RUNS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t = z["t_s"]
    zb = z["body_pos_m"][:, 2]
    th = np.radians(z["roll_pitch_deg"][:, 1])
    cr = z["scm_crawler_normal_N"]
    sm = z["s_motor_m"]
    fc = z["F_cyl_N"]
    tc = min(e[0] for e in res["swivel"]["events"] if e[1] == 2)
    kc = int(np.searchsorted(t, tc))
    zf = zb - XF * th
    zr = zb - XR * th
    pre = {}
    for tt in (8.0, 12.0, 16.0, 20.0, 24.0):
        k = int(np.searchsorted(t, tt))
        pre[f"{tt:.0f}"] = {"z_body_mm": zb[k] * 1e3, "pitch_deg": float(np.degrees(th[k])), "crawler_kN": cr[k] / 1e3}
    pre["rear_contact"] = {"t": float(t[kc]), "z_body_mm": zb[kc] * 1e3, "pitch_deg": float(np.degrees(th[kc])),
                           "crawler_kN": cr[kc] / 1e3}
    # body z rate over 12..(contact-1) s
    m = (t > 12) & (t < tc - 1.0)
    rate = np.polyfit(t[m], zb[m], 1)[0]
    pre["z_body_rate_12s_to_contact_mm_s"] = rate * 1e3
    prog = (sm[:, 2] - sm[kc, 2]) * 1e3
    rows = []
    for g in (0.5, 1.0, 1.5, 2.0, 2.4, 3.0, 3.5, 4.0):
        idx = np.nonzero((t >= tc) & (prog >= g))[0][0]
        rows.append({"prog_mm": g, "t_rel_s": float(t[idx] - tc),
                     "dz_body_mm": (zb[idx] - zb[kc]) * 1e3,
                     "dz_crawler_front_mm": (zf[idx] - zf[kc]) * 1e3,
                     "dz_crawler_rear_mm": (zr[idx] - zr[kc]) * 1e3,
                     "dpitch_mdeg": float(np.degrees(th[idx] - th[kc]) * 1e3),
                     "crawler_kN": cr[idx] / 1e3, "F_rear_kN": fc[idx, 2:].mean() / 1e3,
                     "F_front_kN": fc[idx, :2].mean() / 1e3,
                     "rear_stroke_minus_body_rise_mm": None})
    out[name] = {"pre": pre, "rear_only": rows}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
for name, o in out.items():
    print("==", name)
    for k, v in o["pre"].items():
        print("  ", k, v)
    for r in o["rear_only"]:
        print("   prog {prog_mm:4.1f} t+{t_rel_s:.3f} dzb {dz_body_mm:+.3f} dzCF {dz_crawler_front_mm:+.3f} "
              "dzCR {dz_crawler_rear_mm:+.3f} dth {dpitch_mdeg:+.2f} mdeg cr {crawler_kN:.1f} Fr {F_rear_kN:.2f} "
              "Ff {F_front_kN:.2f}".format(**r))
