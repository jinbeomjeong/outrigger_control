import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import math, json, time, argparse
import numpy as np
from multiprocessing import Pool
import r8d1_lin as R, c2_linear as cl
cc = cl.nominal_controller_constants(); Tdec = np.column_stack([cc["A"], cc["n"]]); Ti = np.linalg.inv(Tdec)

def leg_alpha(lp, cfg, n=500):
    R.set_T(cfg.T)
    L = R.loop(lp, cfg)
    w = np.logspace(-3, math.log10(math.pi / cfg.T * 0.9999), n)
    def Nleg(ww):
        H = R.rcd.freq_resp(L, ww)
        S = np.linalg.inv(np.eye(4)[None] + H)
        return np.einsum("ij,wjk,kl->wil", Tdec, S, Ti) - 0.5 * np.eye(4)
    N = Nleg(w)
    sv = np.linalg.svd(N, compute_uv=False)[:, 0]
    idx = np.where(sv >= 0.5 * sv.max())[0]
    mu = np.zeros(len(w))
    for k in idx:
        mu[k] = R.rcd.mu_upper_dscale(N[k])
    k = int(np.argmax(mu))
    wr = np.linspace(w[max(k - 1, 0)], w[min(k + 1, len(w) - 1)], 21)
    mu2 = [R.rcd.mu_upper_dscale(x) for x in Nleg(wr)]
    m = max(mu.max(), max(mu2))
    return 1.0 / m, float(wr[int(np.argmax(mu2))])

PL = ["top_pads_b1.6_sup_lower", "middle_pads_b1.6_sup_lower", "top_pads_b1.6_sup_upper", "bottom_pads_b1.6_sup_lower",
      "top_pads_b1_sup_lower", "top_crawler_b1.6_sup_lower"]
CAT = {c.tag(): c for c in R.rcd.catalogue(full=True)}
A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)
M6L = dict(Kp=0.3, Ki=0.015, tau_f=0.6, m_att=9)
CFG = {
  "A8_d0_tv0.1": R.Cfg(d=0, tau_v=0.1, Ktw=1.0, **A8),
  "A8_d1_tv0": R.Cfg(d=1, tau_v=0.0, Ktw=1.0, **A8),
  "A8_d1_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=1.0, **A8),
  "A8k05_d1_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=0.5, **A8),
  "A8L_k08_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=0.8, m_att=9, **{k: v for k, v in A8.items()}),
  "A8_ttw0.3_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=1.0, tau_tw=0.3, **A8),
  "M6L_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=1.0, **M6L),
  "M6L_k08_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=0.8, **M6L),
  "M6L_k06_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=0.6, **M6L),
  "M6L_ttw0.3_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=1.0, tau_tw=0.3, **M6L),
  "M6L_k08_tv0.05": R.Cfg(d=1, tau_v=0.05, Ktw=0.8, **M6L),
  "M6L_k08_tv0.15": R.Cfg(d=1, tau_v=0.15, Ktw=0.8, **M6L),
  "G7L_k08_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=0.8, Kp=0.4, Ki=0.02, tau_f=0.5, m_att=9),
  "M5L_k08_tv0.1": R.Cfg(d=1, tau_v=0.1, Ktw=0.8, Kp=0.3, Ki=0.015, tau_f=0.5, m_att=9),
  "R7_50Hz_tv0.1": R.Cfg(T=0.02, N=2, d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0),
  "R7_50Hz_tv0": R.Cfg(T=0.02, N=2, d=1, tau_v=0.0, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0),
  "T0.05_G7_tv0.1": R.Cfg(T=0.05, N=5, d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0),
  "T0.04_G7_tv0.1": R.Cfg(T=0.04, N=4, d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0),
  "T0.03_G7_tv0.1": R.Cfg(T=0.03, N=3, d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0),
  "T0.05_G7L_tv0.1": R.Cfg(T=0.05, N=5, d=1, tau_v=0.1, Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0, m_att=4),
}

def job(a):
    t, n = a
    lp = cl.build_plant(CAT[t])
    al, w = leg_alpha(lp, CFG[n])
    return n, t, al, w

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); a = ap.parse_args()
    names = [n for n in CFG if not a.only or n in a.only.split(",")]
    t0 = time.perf_counter()
    with Pool(14) as p:
        res = p.map(job, [(t, n) for n in names for t in PL], chunksize=1)
    out = {}
    for n, t, al, w in res:
        out.setdefault(n, {})[t] = (round(al, 4), round(w, 3))
    for n in names:
        worst = min(out[n].items(), key=lambda x: x[1][0])
        print(f"{n:20s} min alpha_legs {worst[1][0]:.3f} @ {worst[1][1]} rad/s ({worst[0]})", {k[:22]: v[0] for k, v in out[n].items()})
    json.dump(out, open("r8d1_alpha.json", "w"), indent=1)
    print("wall", round(time.perf_counter() - t0, 1))
