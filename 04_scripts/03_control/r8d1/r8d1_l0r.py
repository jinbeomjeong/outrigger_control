"""L1-R rod-side chamber stiffening (hydraulics rod_side_pressure.md 19.2: 1st rocking 2.04-2.70 Hz, 6th 8.8-13.6 Hz):
(1) range of the 1st / 6th modes in the 80-plant catalogue, (2) extra plants with uniform leg stiffness scale
k_scale 1.3 / 1.75 / 2.2 (surrogate of the rod-side parallel spring raising f1 by up to 2.70 / 2.04), all levels,
pads, beta 1.0 / 1.6, masts rigid / sup_upper / sup_lower; C1, C2 designs with guard, +20 ms."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, time
import numpy as np
from multiprocessing import Pool
import r8d1_lin as R
import c2_linear as cl

A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)
DES = {"C1": (dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9), 0.25),
       "C2": (dict(Ktw=0.5, tau_tw=0.2, **A8), 0.15),
       "R7": (dict(Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0, T=0.02, N=2), 1.0)}


def cfgs():
    out = {}
    for dn, (dv, kg) in DES.items():
        for tv in (0.05, 0.1, 0.15):
            out[f"{dn}_tv{tv:g}"] = R.Cfg(d=1, tau_v=tv, **dv)
            for gl in range(4):
                out[f"{dn}_tv{tv:g}_G{gl}"] = R.Cfg(d=1, tau_v=tv, guard_leg=gl, Kg=kg, **dv)
        if dn != "R7":
            out[f"{dn}_tv0.1_q2"] = R.Cfg(d=1, tau_v=0.1, q_out=2, **dv)
    return out


def plants():
    P = []
    for lv in ("top", "middle", "bottom"):
        for b in (1.0e9, 1.6e9):
            for mast in ("rigid", "sup_upper", "sup_lower"):
                for s in (1.3, 1.75, 2.2):
                    P.append(cl.PlantCase(level=lv, support="pads", beta=b, mast=mast, k_scale=(s, s, s, s)))
    return P


def job(case):
    lp = cl.build_plant(case)
    res = {"f": lp.modes_hz[:6].tolist()}
    for n, c in cfgs().items():
        r, _ = R.analyse(lp, c)
        res[n] = r["Ms_max"]
    return case.tag(), res


def modes(case):
    lp = cl.build_plant(case)
    return case.tag(), lp.modes_hz[:6].tolist()


if __name__ == "__main__":
    t0 = time.perf_counter()
    with Pool(14) as p:
        cat = p.map(modes, R.rcd.catalogue(full=True), chunksize=2)
        rows = p.map(job, plants(), chunksize=1)
    f1 = [m[0] for _, m in cat]; f6 = [m[5] for _, m in cat]
    pads = [m[0] for t, m in cat if "_pads_" in t]
    print("catalogue f1 range %.3f-%.3f Hz (pads %.3f-%.3f), f6 range %.2f-%.2f Hz" % (min(f1), max(f1), min(pads), max(pads), min(f6), max(f6)))
    ex_f1 = [r["f"][0] for _, r in rows]; ex_f6 = [r["f"][5] for _, r in rows]
    print("stiffened set f1 %.3f-%.3f Hz, f6 %.2f-%.2f Hz" % (min(ex_f1), max(ex_f1), min(ex_f6), max(ex_f6)))
    names = list(cfgs())
    summ = {}
    for n in names:
        w = max(rows, key=lambda x: x[1][n])
        summ[n] = (round(w[1][n], 4), w[0], sum(r[n] > 1.5 for _, r in rows))
    agg = {}
    for n, v in summ.items():
        base = n[:-3] if n[-3:-1] == "_G" else n
        if n[-2] == "G" and n[-3] == "_":
            base = n[:-3] + "_G"
        a = agg.setdefault(base, v)
        if v[0] > a[0]:
            agg[base] = v
    for k, v in agg.items():
        print(f"{k:16s} worst Ms {v[0]:.3f} ({v[1]}) n>1.5 {v[2]}")
    json.dump({"catalogue_modes": cat, "rows": rows, "summary": summ}, open("r8d1_l0r.json", "w"), indent=1)
    print("wall", round(time.perf_counter() - t0, 1))
