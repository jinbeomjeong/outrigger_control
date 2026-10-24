"""C2 (R8-D1, U-R8-6) twist / guard gain normalisation: true leg-stiffness scale s (uniform k_scale on the
pad plants, L1-R surrogate of spec 135) x gain divisor r (Ktw = 0.5 / r, Kg = 0.15 / r).

Metrics per (s, r): worst channel M_s (guard off) and worst guard-active M_s (4 legs), tau_v 0.1 s (and 0.15),
d = 1, T = 0.1 s, exact lifted model r8d1_lin. Also the twist-channel crossover (speed proxy) on the nominal
plant. Usage: python -I c2_norm_sweep.py <out.json> [workers]
Spec rev. 31 142 B; result 06_analysis/02_control/r8_10hz/d1/c2_norm.json.
"""
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r8d1_lin as R  # noqa: E402
import c2_linear as cl  # noqa: E402

S_TRUE = (1.0, 1.2, 1.3, 1.5, 1.75)
R_DIV = (1.0, 1.2, 1.3, 1.5, 1.75)
A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)


def job(args):
    case, s = args
    lp = cl.build_plant(case)
    out = {}
    for tv in (0.1, 0.15):
        for r in R_DIV:
            base = dict(d=1, tau_v=tv, Ktw=0.5 / r, tau_tw=0.2, **A8)
            res, _ = R.analyse(lp, R.Cfg(**base))
            g = max(R.analyse(lp, R.Cfg(guard_leg=k, Kg=0.15 / r, **base))[0]["Ms_max"] for k in range(4))
            out[f"tv{tv:g}_r{r:g}"] = dict(Ms=res["Ms_max"], ch=res["Ms_ch"], G=g, wgc_tw=res["tw"]["wgc"],
                                           PM_tw=res["tw"]["PMmin"])
    return case.tag(), s, out


if __name__ == "__main__":
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    jobs = []
    for s in S_TRUE:
        for lv in ("top", "middle", "bottom"):
            for b in (0.69e9, 1.0e9, 1.6e9):
                for mast in ("rigid", "sup_upper", "sup_lower"):
                    ks = None if s == 1.0 else (s,) * 4
                    case = cl.PlantCase(level=lv, support="pads", beta=b, mast=mast) if ks is None else \
                        cl.PlantCase(level=lv, support="pads", beta=b, mast=mast, k_scale=ks)
                    jobs.append((case, s))
    t0 = time.perf_counter()
    with Pool(workers) as p:
        rows = p.map(job, jobs, chunksize=1)
    json.dump(rows, open(sys.argv[1], "w"), indent=1)
    print("rows", len(rows), "wall", round(time.perf_counter() - t0, 1))
    for tv in (0.1, 0.15):
        print(f"tau_v {tv}: worst channel / guard M_s (n>1.5 of 27 per s)")
        print("   s\\r " + "".join(f"{r:>16g}" for r in R_DIV))
        for s in S_TRUE:
            sub = [x for x in rows if x[1] == s]
            cells = []
            for r in R_DIV:
                k = f"tv{tv:g}_r{r:g}"
                ms = max(x[2][k]["Ms"] for x in sub); g = max(x[2][k]["G"] for x in sub)
                n = sum(max(x[2][k]["Ms"], x[2][k]["G"]) > 1.5 for x in sub)
                cells.append(f"{ms:.3f}/{g:.3f}({n})")
            print(f"  {s:4g} " + "".join(f"{c:>16s}" for c in cells))
