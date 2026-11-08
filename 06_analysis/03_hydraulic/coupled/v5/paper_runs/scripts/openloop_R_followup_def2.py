"""Operational R-1 definition (2): per-leg min of F_cyl from the rear peak before front contact
(argmax over rear contact..front contact) to crawler lift-off; plus F at rear contact and R-4 at 4 decimals.
Also the soil-R share estimate in the rear-only phase: sum over crawler of R*Vn is not recorded, so only the
leg moving dashpot bound c_move*u is printed. Units kN, mm, s."""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
B = R / "batch_V5-OPENLOOP-R_20261108_231840"
RUNS = {"V0_R992k": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
        "R888k": B / "P3a_J1_B_V0_R888k", "R600k": B / "P3a_J1_B_V0_R600k", "R300k": B / "P3a_J1_B_V0_R300k",
        "VB_prop": R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop",
        "rep_a": Path(r"C:\workspace\outrigger_control\07_results\S9\batch_V5-OPENLOOP-RFU_20261109_0100\P3a_J1_B_V0_rep"), "R1490k": Path(r"C:\workspace\outrigger_control\07_results\S9\batch_V5-OPENLOOP-RFU_20261109_0100\P3a_J1_B_V0_R1490k")}
XF = 1.30
out = {}
for name, p in RUNS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t = z["t_s"]; fc = z["F_cyl_N"]; cr = z["scm_crawler_normal_N"]; W = res["p3a"]["weight_N"]
    zb = z["body_pos_m"][:, 2]; th = np.radians(z["roll_pitch_deg"][:, 1])
    ev = res["swivel"]["events"]
    tc = min(e[0] for e in ev if e[1] == 2); tf = min(e[0] for e in ev if e[1] == 0)
    kc = int(np.searchsorted(t, tc)); kf = int(np.searchsorted(t, tf))
    lift = t > 8.0 + 1e-9
    idx = np.nonzero(lift)[0]
    m = cr[lift] < 0.01 * W
    # first 0.1 s run
    klo = None
    k = 0
    tl = t[lift]
    while k < len(tl):
        if m[k]:
            j = k
            while j < len(tl) and m[j]:
                j += 1
            if tl[j - 1] - tl[k] >= 0.1 - 1e-9:
                klo = int(idx[k]); break
            k = j
        else:
            k += 1
    r = {}
    for leg, i in (("RL", 2), ("RR", 3)):
        kp = kc + int(np.argmax(fc[kc:kf, i]))
        kmin = kp + int(np.argmin(fc[kp:klo + 1, i]))
        r[leg] = {"F_min_kN": fc[kmin, i] / 1e3, "t_min_rel_front_s": t[kmin] - tf, "t_peak_rel_front_s": t[kp] - tf,
                  "F_at_rear_contact_kN": fc[kc, i] / 1e3}
    zf = (zb - XF * th) - (zb[kc] - XF * th[kc])
    k14 = int(np.searchsorted(t, tc + 0.14))
    out[name] = {"R1_def2_postpeak": r, "R4_dz_0p14_mm": zf[k14] * 1e3,
                 "crawler_kN_at_front_contact": cr[kf] / 1e3, "crawler_kN_at_rear_contact": cr[kc] / 1e3,
                 "front_F_at_front_contact_plus70ms_kN": (fc[int(np.searchsorted(t, tf + 0.07)), :2] / 1e3).tolist()}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
for n, o in out.items():
    print(n, {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in o["R1_def2_postpeak"].items()},
          "R4 %.4f" % o["R4_dz_0p14_mm"], "cr@c %.2f cr@f %.2f" % (o["crawler_kN_at_rear_contact"], o["crawler_kN_at_front_contact"]))
print("leg moving dashpot bound rear: c*u =", 86949.0 * 0.020924 / 1e3, "kN; speed-ratio share",
      86949.0 * 0.020924 * (1 - 0.894736837) / 1e3, "kN")
