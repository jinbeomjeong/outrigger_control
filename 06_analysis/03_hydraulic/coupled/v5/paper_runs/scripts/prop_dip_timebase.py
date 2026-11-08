"""Time-based vs stroke-based comparison of the rear-only phase (V0 vs prop, J1 pad B).

Tests the creep hypothesis: if the crawler front sinks at a rate set by the load excess (viscous SCM R
term on a yielding crawler), its sinkage matches at equal TIME since rear contact, not at equal stroke.
Also: rear force at equal commanded stroke s_ref progress = u (t - t_c); split of the rear min into
(value at front contact) + (front pick-up dip). Units mm, mm/s, kN.
"""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {"V0": (R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0", 0.020924),
        "prop": (R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop", 0.020924 * 0.894736837447082)}
XF = 1.30
F_MIN = 9414.58911
out = {}
for name, (p, u) in RUNS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t = z["t_s"]
    zb = z["body_pos_m"][:, 2]
    th = np.radians(z["roll_pitch_deg"][:, 1])
    fc = z["F_cyl_N"]
    tc = min(e[0] for e in res["swivel"]["events"] if e[1] == 2)
    tf = min(e[0] for e in res["swivel"]["events"] if e[1] == 0)
    kc = int(np.searchsorted(t, tc))
    zf = (zb - XF * th) - (zb[kc] - XF * th[kc])
    by_time = []
    for dt in (0.04, 0.08, 0.10, 0.12, 0.14):
        k = int(np.searchsorted(t, tc + dt))
        by_time.append({"t_rel_s": dt, "dz_crawler_front_mm": zf[k] * 1e3, "F_rear_kN": fc[k, 2:].mean() / 1e3})
    m = (t > tc + 0.06) & (t < tc + 0.14)
    rate = np.polyfit(t[m], zf[m], 1)[0] * 1e3
    by_sref = []
    for sp in (1.0, 2.0, 2.5, 3.0):
        k = int(np.searchsorted(t, tc + sp * 1e-3 / u))
        by_sref.append({"sref_prog_mm": sp, "F_rear_kN": fc[k, 2:].mean() / 1e3, "dz_crawler_front_mm": zf[k] * 1e3,
                        "dpitch_mdeg": float(np.degrees(th[k] - th[kc]) * 1e3)})
    kf = int(np.searchsorted(t, tf))
    kmin = kc + int(np.argmin(fc[kc:int(np.searchsorted(t, 27.0 if name == 'V0' else 29.0)), 2]))
    # restrict min to after first > 1.4 F_min, as the stored rule
    a = np.nonzero((t > tc) & (fc[:, 2] > 1.4 * F_MIN))[0][0]
    lo = np.nonzero((t > 8) & (z["scm_crawler_normal_N"] < 0.01 * res["p3a"]["weight_N"]))[0][0]
    kmin = a + int(np.argmin(fc[a:lo + 1, 2]))
    out[name] = {"t_rear_contact_s": tc, "t_front_contact_s": tf,
                 "contact_gap_sref_mm": (tf - tc) * u * 1e3,
                 "crawler_front_sink_rate_mm_s_0p06_0p14": rate,
                 "by_time": by_time, "by_sref": by_sref,
                 "F_rear_at_front_contact_kN": fc[kf, 2:].tolist(),
                 "F_rear_min_kN": fc[kmin, 2:].tolist(), "t_min_rel_front_contact_s": float(t[kmin] - tf),
                 "dip_from_front_contact_kN": ((fc[kmin, 2:] - fc[kf, 2:]) / 1e3).tolist(),
                 "rear_peak_before_front_kN": (fc[kc:kf, 2:].max(axis=0) / 1e3).tolist()}
out["diff_prop_minus_V0"] = {
    "F_rear_at_front_contact_kN": ((np.array(out["prop"]["F_rear_at_front_contact_kN"]) -
                                    np.array(out["V0"]["F_rear_at_front_contact_kN"])) / 1e3).tolist(),
    "F_rear_min_kN": ((np.array(out["prop"]["F_rear_min_kN"]) - np.array(out["V0"]["F_rear_min_kN"])) / 1e3).tolist(),
    "rear_peak_kN": (np.array(out["prop"]["rear_peak_before_front_kN"]) -
                     np.array(out["V0"]["rear_peak_before_front_kN"])).tolist(),
    "rear_peak_ratio": (np.array(out["prop"]["rear_peak_before_front_kN"]) /
                        np.array(out["V0"]["rear_peak_before_front_kN"])).tolist(),
}
soil = json.loads(Path(r"C:\workspace\outrigger_control\02_params\scm_soil_sets.json").read_text("utf-8"))
out["soil_n_R"] = {k: {"n": soil[k]["n"], "R": soil[k].get("chrono", {}).get("damping_R")} for k in ("J1", "G1") if k in soil}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
print(json.dumps(out, indent=1, default=float))
