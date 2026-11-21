"""Attitude-only IMU alternatives: linear loop margins of the C2 R8-D1 loops (exploratory design study).

Reuses the exact multirate model ``04_scripts/03_control/r8d1/r8d1_lin.py`` (read only). The plant's
accelerometer-tilt outputs ``phi_acc`` / ``theta_acc`` are replaced by the output of a continuous sensor model
(states appended to the plant):

* ``S0``  current IMU: accelerometer tilt (no change).
* ``A``   inclinometer: accelerometer tilt -> 2 identical first-order stages tau_s = 1 / (2 pi f_s).
* ``B``   AHRS: complementary filter with gyro-bias integrator (Mahony PI), x' = w + kP (y_acc - x) - b,
          b' = -kI (y_acc - x); kP = 2 zeta w_c, kI = w_c^2, zeta = 1, w_c = 2 pi f_c. Gyro = true body rate.
Sensor transport delay: ``p_imu`` substeps of h = 10 ms (r8d1_lin Cfg.p_imu).
C2 preset (with_10hz_d1): Kp 0.2, Ki 0.01, tau_f x 2 (100 Hz), Ktw 0.5 / k_nom, tau_tw 0.2, Kz 0.5, tau_z 0.2,
d = 1, T = 0.1 s, tau_v = 0.1 s; guard Kg 0.15. Negative feedback v = -K y, loop broken at the decoupled command.

Usage (dynamics-dev, E cores): python -I -B imuatt_lin.py <out.json> [workers] [--quick]
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace

import numpy as np

R8D1 = Path(r"C:\workspace\outrigger_control\.claude\worktrees\journal-v0\04_scripts\03_control\r8d1")
sys.path.insert(0, str(R8D1))
import r8d1_lin as R  # noqa: E402

N6 = 6
BASE = R.Cfg(d=1, tau_v=0.1, Kp=0.2, Ki=0.01, tau_f=0.8, n_st=2, Ktw=0.5, tau_tw=0.2, Kz=0.5, tau_z=0.2)
KG = 0.15

# name: (sensor kind, parameter [Hz], p_imu substeps, controller tau_f [s][, Kp, Ki])
VARIANTS = {
    "S0": ("S0", None, 0, 0.8),
    "S0_d10": ("S0", None, 1, 0.8),
    "S0_d20": ("S0", None, 2, 0.8),
    "A_f5.0": ("A", 5.0, 2, 0.8),
    "A_f2.0": ("A", 2.0, 2, 0.8),
    "A_f1.0": ("A", 1.0, 2, 0.8),
    "A_f1.0_d0": ("A", 1.0, 0, 0.8),
    "A_f0.5": ("A", 0.5, 2, 0.8),
    "A_f0.3": ("A", 0.3, 2, 0.8),
    "A_f1.0_tf0.64": ("A", 1.0, 2, 0.64),
    "A_f1.0_tf1.0": ("A", 1.0, 2, 1.0),
    "A_f0.5_tf0.48": ("A", 0.5, 2, 0.48),
    "A_f1.0_Kp0.15": ("A", 1.0, 2, 0.8, 0.15, 0.0075),
    "A_f0.5_Kp0.15": ("A", 0.5, 2, 0.8, 0.15, 0.0075),
    "A_f0.3_Kp0.15": ("A", 0.3, 2, 0.8, 0.15, 0.0075),
    "B_c0.05": ("B", 0.05, 1, 0.8),
    "B_c0.05_d20": ("B", 0.05, 2, 0.8),
    "B_c0.05_tf0.5": ("B", 0.05, 1, 0.5),
    "B_c0.05_tf0.4": ("B", 0.05, 1, 0.4),
    "B_c0.05_tf0.3": ("B", 0.05, 1, 0.3),
    "B_c0.05_tf0.2": ("B", 0.05, 1, 0.2),
    "B_c0.02_tf0.4": ("B", 0.02, 1, 0.4),
    "B_c0.1": ("B", 0.1, 1, 0.8),
    "B_c0.1_tf0.4": ("B", 0.1, 1, 0.4),
    "B_c0.2": ("B", 0.2, 1, 0.8),
    "B_c0.2_tf0.4": ("B", 0.2, 1, 0.4),
}
GUARD_VARIANTS = ("S0", "A_f1.0", "A_f0.5", "A_f1.0_Kp0.15", "A_f0.5_Kp0.15", "B_c0.05", "B_c0.05_tf0.4",
                  "B_c0.1")


def sensor_plant(lp, kind, par):
    """Plant with the IMU tilt rows replaced by the sensor output (new states appended)."""
    A, B, C, D = (np.asarray(m, float) for m in (lp.A, lp.B, lp.C, lp.D))
    names = list(lp.out_names)
    if kind == "S0":
        return SimpleNamespace(A=A, B=B, C=C, D=D, out_names=names, idx=names.index, case=lp.case)
    nx = A.shape[0]
    ip, it = names.index("phi_acc"), names.index("theta_acc")
    acc_C = C[[ip, it]]
    acc_D = D[[ip, it]]
    ns = 4  # two states per axis
    Aa = np.zeros((nx + ns, nx + ns)); Aa[:nx, :nx] = A
    Ba = np.zeros((nx + ns, B.shape[1])); Ba[:nx] = B
    if kind == "A":
        tau = 1.0 / (2.0 * math.pi * par)
        for ax in range(2):
            s1, s2 = nx + 2 * ax, nx + 2 * ax + 1
            Aa[s1, :nx] = acc_C[ax] / tau; Aa[s1, s1] = -1.0 / tau; Ba[s1] = acc_D[ax] / tau
            Aa[s2, s1] = 1.0 / tau; Aa[s2, s2] = -1.0 / tau
        out_state = [nx + 1, nx + 3]
    elif kind == "B":
        wc = 2.0 * math.pi * par
        kP, kI = 2.0 * wc, wc * wc
        rate_idx = [N6 + 3, N6 + 4]          # phi_dot, theta_dot (gyro, small angles)
        for ax in range(2):
            xh, bh = nx + 2 * ax, nx + 2 * ax + 1
            # xh' = rate + kP (acc - xh) - bh ; bh' = -kI (acc - xh)
            Aa[xh, rate_idx[ax]] += 1.0
            Aa[xh, :nx] += kP * acc_C[ax]; Aa[xh, xh] = -kP; Aa[xh, bh] = -1.0; Ba[xh] = kP * acc_D[ax]
            Aa[bh, :nx] += -kI * acc_C[ax]; Aa[bh, xh] = kI; Ba[bh] = -kI * acc_D[ax]
        out_state = [nx, nx + 2]
    else:
        raise ValueError(kind)
    Ca = np.hstack([C, np.zeros((C.shape[0], ns))]); Da = D.copy()
    for row, st in ((ip, out_state[0]), (it, out_state[1])):
        Ca[row] = 0.0; Ca[row, st] = 1.0; Da[row] = 0.0
    return SimpleNamespace(A=Aa, B=Ba, C=Ca, D=Da, out_names=names, idx=names.index, case=lp.case)


def one(job):
    item_index, vname, guard_leg = job
    items = R.catalogue_ext()
    lp = R.make_plant(items[item_index])
    kind, par, p_imu, tau_f, *gains = VARIANTS[vname]
    sp = sensor_plant(lp, kind, par)
    cfg = replace(BASE, p_imu=p_imu, tau_f=tau_f)
    if gains:
        cfg = replace(cfg, Kp=gains[0], Ki=gains[1])
    if guard_leg >= 0:
        cfg = replace(cfg, guard_leg=guard_leg, Kg=KG)
    t0 = time.perf_counter()
    try:
        res, _ = R.analyse(sp, cfg)
    except Exception as exc:  # noqa: BLE001
        return {"plant": R.tag(lp), "variant": vname, "guard_leg": guard_leg, "error": repr(exc)}
    out = {"plant": R.tag(lp), "variant": vname, "guard_leg": guard_leg, "elapsed_s": time.perf_counter() - t0,
           "Ms_max": res["Ms_max"], "Ms_ch": res["Ms_ch"], "rho": res["rho"]}
    for ch in R.CH:
        out[ch] = {k: (None if v is None else float(v)) for k, v in res[ch].items()}
    return out


def main():
    out_path = Path(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    quick = "--quick" in sys.argv
    items = R.catalogue_ext()
    idx = range(len(items))
    if quick:
        tags = [R.tag(R.make_plant(items[i])) for i in idx]
        idx = [i for i, t in enumerate(tags) if t in ("top_pads_b1.6_sup_lower", "bottom_pads_b1.6_sup_upper",
                                                    "middle_pads_b1.6_sup_upper", "top_pads_b1_rigid")]
    jobs = [(i, v, -1) for i in idx for v in VARIANTS]
    # guard-active loops (pads support plants only, the four legs), for the main variants
    pads = [i for i in idx if items[i][0].support == "pads" and items[i][1] == 1.0]
    jobs += [(i, v, g) for i in pads for v in GUARD_VARIANTS for g in range(4)]
    t0 = time.time()
    with get_context("spawn").Pool(workers) as pool:
        results = pool.map(one, jobs, chunksize=4)
    json.dump({"base": BASE.__dict__, "Kg": KG, "variants": VARIANTS, "results": results,
               "elapsed_s": time.time() - t0}, open(out_path, "w"), indent=1, default=str)
    print(f"{len(results)} jobs, {sum('error' in r for r in results)} errors, {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
