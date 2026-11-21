"""Second sweep: inclinometer gain reduction, guard gain, single-stage filter, tau_v 0.15 sensitivity.

Same model as imuatt_lin.py (sensor_plant, BASE). Variant = (kind, f [Hz], p_imu, Cfg overrides, Kg).
Usage (dynamics-dev, E cores): python -I -B imuatt_lin2.py <out.json> [workers]
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imuatt_lin as L  # noqa: E402

R = L.R
KI_RATIO = 0.05  # Ki / Kp of the preset (0.01 / 0.2)

VARIANTS = {}
for f in (1.0, 0.5):
    for kp in (0.15, 0.12, 0.10):
        for kg in (0.15, 0.10):
            VARIANTS[f"A_f{f}_Kp{kp}_Kg{kg}"] = ("A", f, 2, {"Kp": kp, "Ki": kp * KI_RATIO}, kg)
    VARIANTS[f"A_f{f}_n1"] = ("A", f, 2, {"n_st": 1}, 0.15)
    VARIANTS[f"A_f{f}_n1_Kp0.15"] = ("A", f, 2, {"n_st": 1, "Kp": 0.15, "Ki": 0.0075}, 0.15)
VARIANTS["S0_tv0.15"] = ("S0", None, 0, {"tau_v": 0.15}, 0.15)
VARIANTS["A_f1.0_Kp0.12_tv0.15"] = ("A", 1.0, 2, {"tau_v": 0.15, "Kp": 0.12, "Ki": 0.006}, 0.10)
VARIANTS["A_f0.5_Kp0.12_tv0.15"] = ("A", 0.5, 2, {"tau_v": 0.15, "Kp": 0.12, "Ki": 0.006}, 0.10)
VARIANTS["B_c0.05_tv0.15"] = ("B", 0.05, 1, {"tau_v": 0.15}, 0.15)
VARIANTS["B_c0.05_tf0.4_tv0.15"] = ("B", 0.05, 1, {"tau_v": 0.15, "tau_f": 0.4}, 0.15)
VARIANTS["B_c0.05_tf0.4_d30"] = ("B", 0.05, 3, {"tau_f": 0.4}, 0.15)
VARIANTS["B_c0.05_tf0.5_d30"] = ("B", 0.05, 3, {"tau_f": 0.5}, 0.15)


def one(job):
    item_index, vname, guard_leg = job
    items = R.catalogue_ext()
    lp = R.make_plant(items[item_index])
    kind, par, p_imu, over, kg = VARIANTS[vname]
    sp = L.sensor_plant(lp, kind, par)
    cfg = replace(L.BASE, p_imu=p_imu, **over)
    if guard_leg >= 0:
        cfg = replace(cfg, guard_leg=guard_leg, Kg=kg)
    try:
        res, _ = R.analyse(sp, cfg)
    except Exception as exc:  # noqa: BLE001
        return {"plant": R.tag(lp), "variant": vname, "guard_leg": guard_leg, "error": repr(exc)}
    out = {"plant": R.tag(lp), "variant": vname, "guard_leg": guard_leg,
           "Ms_max": res["Ms_max"], "Ms_ch": res["Ms_ch"], "rho": res["rho"]}
    for ch in R.CH:
        out[ch] = {k: (None if v is None else float(v)) for k, v in res[ch].items()}
    return out


def main():
    out_path = Path(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    items = R.catalogue_ext()
    idx = range(len(items))
    pads = [i for i in idx if items[i][0].support == "pads" and items[i][1] == 1.0]
    jobs = [(i, v, -1) for i in idx for v in VARIANTS]
    jobs += [(i, v, g) for i in pads for v in VARIANTS for g in range(4)]
    t0 = time.time()
    with get_context("spawn").Pool(workers) as pool:
        results = pool.map(one, jobs, chunksize=4)
    json.dump({"base": L.BASE.__dict__, "variants": VARIANTS, "results": results,
               "elapsed_s": time.time() - t0}, open(out_path, "w"), indent=1, default=str)
    print(f"{len(results)} jobs, {sum('error' in r for r in results)} errors, {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
