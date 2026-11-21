"""Revision 1 sweep: product-shaped inclinometer filters (2nd-order Bessel / Butterworth, moving average as its
group delay) and the SICK default AHRS time constant (5 s ~ 0.032 Hz). Same lifted model as imuatt_lin.py.

New kind "A2": 2nd-order low pass  y'' + a1 y' + a0 y = a0 u  (a0 = wn^2, a1 = 2 zeta wn), coefficients from
scipy.signal.bessel / butter (analog, -3 dB at f). Moving average of length Tm = pure delay Tm / 2 (its exact
phase) with magnitude 1 (conservative: the real sinc magnitude attenuates the rocking band).
Usage (dynamics-dev, E cores): python -I -B imuatt_lin3.py <out.json> [workers]
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
from scipy import signal

sys.path.insert(0, r"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4"
                   r"\scratchpad\control-imuatt")
import imuatt_lin as L  # noqa: E402

R = L.R


def second_order(kind: str, f_hz: float):
    w = 2 * math.pi * f_hz
    if kind == "bessel":
        b, a = signal.bessel(2, w, analog=True, norm="mag")
    else:
        b, a = signal.butter(2, w, analog=True)
    a = np.asarray(a) / a[0]
    return float(a[1]), float(a[2])          # a1, a0


def sensor_plant2(lp, shape, f_hz):
    A, B, C, D = (np.asarray(m, float) for m in (lp.A, lp.B, lp.C, lp.D))
    names = list(lp.out_names)
    nx = A.shape[0]
    ip, it = names.index("phi_acc"), names.index("theta_acc")
    acc_C, acc_D = C[[ip, it]], D[[ip, it]]
    a1, a0 = second_order(shape, f_hz)
    Aa = np.zeros((nx + 4, nx + 4)); Aa[:nx, :nx] = A
    Ba = np.zeros((nx + 4, B.shape[1])); Ba[:nx] = B
    outs = []
    for ax in range(2):
        y, yd = nx + 2 * ax, nx + 2 * ax + 1
        Aa[y, yd] = 1.0
        Aa[yd, :nx] = a0 * acc_C[ax]; Aa[yd, y] = -a0; Aa[yd, yd] = -a1; Ba[yd] = a0 * acc_D[ax]
        outs.append(y)
    Ca = np.hstack([C, np.zeros((C.shape[0], 4))]); Da = D.copy()
    for row, st in ((ip, outs[0]), (it, outs[1])):
        Ca[row] = 0.0; Ca[row, st] = 1.0; Da[row] = 0.0
    return SimpleNamespace(A=Aa, B=Ba, C=Ca, D=Da, out_names=names, idx=names.index, case=lp.case)


# name: (builder, args, p_imu, cfg overrides, Kg)
V = {}
for shape in ("bessel", "butter"):
    for kp, kg in ((0.2, 0.15), (0.15, 0.15), (0.15, 0.10), (0.12, 0.10)):
        V[f"A2_{shape}1_Kp{kp}_Kg{kg}"] = ("A2", (shape, 1.0), 2, {"Kp": kp, "Ki": kp * 0.05}, kg)
for kp, kg in ((0.2, 0.15), (0.15, 0.10)):
    V[f"A2_butter5_Kp{kp}_Kg{kg}"] = ("A2", ("butter", 5.0), 2, {"Kp": kp, "Ki": kp * 0.05}, kg)
for kp, kg in ((0.2, 0.15), (0.15, 0.10), (0.12, 0.10)):
    V[f"MA200_Kp{kp}_Kg{kg}"] = ("S0", (None,), 2 + 10, {"Kp": kp, "Ki": kp * 0.05}, kg)
for tf in (0.8, 0.4):
    V[f"B_c0.032_tf{tf}"] = ("B", (0.032,), 1, {"tau_f": tf}, 0.15)
    V[f"B_c0.032_tf{tf}_d0"] = ("B", (0.032,), 0, {"tau_f": tf}, 0.15)


def build(lp, kind, args):
    if kind == "A2":
        return sensor_plant2(lp, *args)
    return L.sensor_plant(lp, kind, args[0])


def one(job):
    i, vname, g = job
    lp = R.make_plant(R.catalogue_ext()[i])
    kind, args, p_imu, over, kg = V[vname]
    cfg = replace(L.BASE, p_imu=p_imu, **over)
    if g >= 0:
        cfg = replace(cfg, guard_leg=g, Kg=kg)
    try:
        res, _ = R.analyse(build(lp, kind, args), cfg)
    except Exception as exc:  # noqa: BLE001
        return {"plant": R.tag(lp), "variant": vname, "guard_leg": g, "error": repr(exc)}
    out = {"plant": R.tag(lp), "variant": vname, "guard_leg": g, "Ms_max": res["Ms_max"], "Ms_ch": res["Ms_ch"],
           "rho": res["rho"]}
    for ch in R.CH:
        out[ch] = {k: (None if v is None else float(v)) for k, v in res[ch].items()}
    return out


def main():
    items = R.catalogue_ext()
    pads = [i for i in range(len(items)) if items[i][0].support == "pads" and items[i][1] == 1.0]
    jobs = [(i, v, -1) for i in range(len(items)) for v in V] + [(i, v, g) for i in pads for v in V for g in range(4)]
    t0 = time.time()
    with get_context("spawn").Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 12) as pool:
        results = pool.map(one, jobs, chunksize=4)
    json.dump({"variants": V, "results": results}, open(sys.argv[1], "w"), indent=1, default=str)
    print(f"{len(results)} jobs, {sum('error' in r for r in results)} errors, {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
