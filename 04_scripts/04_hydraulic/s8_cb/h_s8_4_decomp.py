"""H-S8-4: physical rod-side decompression time when the valve really opens (EXT, meter-out).

Rod chamber V_r = A_ann (L_0r + s_max - s) vents through the B->T orifice of the opened spool:
    dp/dt = -(beta / V_r) K sqrt(p),   K = Q_n / sqrt(dp_n),   Q_n = A_ann * u_cmd
    -> sqrt(p) falls linearly; time from p0 to p_end:
    t = 2 V_r (sqrt(p0) - sqrt(p_end)) / (beta K)
ASSUMPTIONS: spool already at the commanded opening (spool lag excluded), meter-out pressure drop
at the commanded flow dp_n = 5 / 10 / 20 bar, gauge pressures, back pressure p_end = 2 bar g.
Also the volume vented and its equivalent rod travel.

Usage: h_s8_4_decomp.py <report.json> <batch_dir> <out.json>
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1.0e5
S_MAX = 0.70
LEGS = ("FL", "FR", "RL", "RR")


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def main() -> None:
    rep = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    batch = Path(sys.argv[2])
    rows = []
    for s in rep["seven"]:
        ep = batch / "episodes" / s["case"]
        leg = LEGS.index(s["leg"])
        meta = json.loads((ep / "record" / "meta.json").read_text(encoding="utf-8"))
        l0r = float(find_key(meta, "rod_dead_length_m")[leg])
        # REXOME35 areas (front / rear), as in section 1 of the hydraulics S8 document
        a_p = 1.3273e-2 if leg < 2 else 9.503e-3
        a_ann = 3.770e-3 if leg < 2 else 3.142e-3
        beta = float(find_key(meta, "bulk_modulus_Pa"))
        z = np.load(ep / "pads.npz", allow_pickle=True)
        i = int(np.searchsorted(z["t"], s["t_release_s"])) - 1
        s_ref = float(z["s_motor"][i, leg])
        v_r = a_ann * (l0r + S_MAX - s_ref)
        p0 = s["rod_before_bar"] * BAR
        p_end = 2.0 * BAR
        dv = v_r * (p0 - p_end) / beta
        u = abs(s["u_new_m_s"])
        out = {"case": s["case"], "leg": s["leg"], "s_ref_m": s_ref, "L0r_m": l0r,
               "beta_Pa": beta, "A_ann_m2": a_ann, "A_p_m2": a_p, "V_r_m3": v_r,
               "p0_bar_g": p0 / BAR, "vent_volume_cm3": dv * 1e6,
               "equivalent_rod_travel_mm": dv / a_ann * 1e3, "u_cmd_m_s": u, "t_vent_s": {}}
        for dpn in (5.0, 10.0, 20.0):
            k = a_ann * u / math.sqrt(dpn * BAR)
            out["t_vent_s"][f"dp_n_{dpn:g}bar"] = (
                2.0 * v_r * (math.sqrt(p0) - math.sqrt(p_end)) / (beta * k))
        rows.append(out)
    Path(sys.argv[3]).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for r in rows:
        print(r["case"], r["leg"], f"s {r['s_ref_m']:.4f} L0r {r['L0r_m']:.4f} beta {r['beta_Pa']:.3g}",
              f"V {r['V_r_m3'] * 1e6:.0f} cm3 dV {r['vent_volume_cm3']:.2f} cm3 "
              f"x {r['equivalent_rod_travel_mm']:.2f} mm u {r['u_cmd_m_s']:.2e}",
              {k: round(v, 3) for k, v in r["t_vent_s"].items()})


if __name__ == "__main__":
    main()
