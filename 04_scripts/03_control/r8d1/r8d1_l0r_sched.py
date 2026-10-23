"""C1 on the stiffened plants with the twist / guard gains normalised by the leg-stiffness scale (gain scheduling on
the measured twist stiffness S_ii, i.e. Ktw = 0.8 / s, Kg = 0.25 / s)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from multiprocessing import Pool
import r8d1_lin as R
import c2_linear as cl


def job(args):
    case, s = args
    lp = cl.build_plant(case)
    out = {}
    for tv in (0.05, 0.1, 0.15):
        base = dict(d=1, tau_v=tv, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8 / s, m_att=9)
        out[f"tv{tv:g}"] = R.analyse(lp, R.Cfg(**base))[0]["Ms_max"]
        out[f"tv{tv:g}_G"] = max(R.analyse(lp, R.Cfg(guard_leg=g, Kg=0.25 / s, **base))[0]["Ms_max"] for g in range(4))
    out["tv0.1_q2"] = R.analyse(lp, R.Cfg(d=1, tau_v=0.1, q_out=2, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8 / s, m_att=9))[0]["Ms_max"]
    return case.tag(), s, out


if __name__ == "__main__":
    jobs = []
    for s in (1.3, 1.75):
        for lv in ("top", "middle", "bottom"):
            for b in (1.0e9, 1.6e9):
                for mast in ("rigid", "sup_upper", "sup_lower"):
                    jobs.append((cl.PlantCase(level=lv, support="pads", beta=b, mast=mast, k_scale=(s,) * 4), s))
    with Pool(14) as p:
        rows = p.map(job, jobs, chunksize=1)
    for s in (1.3, 1.75):
        sub = [r for r in rows if r[1] == s]
        for k in sub[0][2]:
            w = max(sub, key=lambda r: r[2][k])
            print(f"k{s} {k:10s} worst {w[2][k]:.3f} n>1.5 {sum(r[2][k] > 1.5 for r in sub)} ({w[0]})")
    json.dump(rows, open("r8d1_l0r_sched.json", "w"), indent=1)
