"""Multi-loop disk margin (balanced, alpha = 1 / mu(S - I/2), diagonal complex) at the 4 leg inputs and at the
decoupled channels, top-5 plants by sigma_max(S_leg) per design; mu upper bound by D-scaling (run_c2_design)
and dkpy LMI check at the peak frequencies."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, math, time
import numpy as np
from multiprocessing import Pool
import r8d1_lin as R, c2_linear as cl

G7 = dict(Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0)
DES_OLD = {
    "R7_50Hz": R.Cfg(T=0.02, N=2, d=1, tau_v=0.0, **G7),
    "R7_50Hz_tv0.1": R.Cfg(T=0.02, N=2, d=1, tau_v=0.1, **G7),
    "A8_tv0.1": R.Cfg(d=1, tau_v=0.1, Kp=0.2, Ki=0.01, tau_f=0.8, Ktw=1.0),
    "A8k08_tv0.1": R.Cfg(d=1, tau_v=0.1, Kp=0.2, Ki=0.01, tau_f=0.8, Ktw=0.8),
    "M6L_tv0.1": R.Cfg(d=1, tau_v=0.1, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0, m_att=9),
    "M6Lk08_tv0.1": R.Cfg(d=1, tau_v=0.1, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9),
    "M5L_tv0.1": R.Cfg(d=1, tau_v=0.1, Kp=0.3, Ki=0.015, tau_f=0.5, Ktw=1.0, m_att=9),
}
A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8)
DES = {}
for tv in (0.05, 0.1, 0.15):
    DES[f"C1_tv{tv:g}"] = R.Cfg(d=1, tau_v=tv, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9)
    DES[f"C2_tv{tv:g}"] = R.Cfg(d=1, tau_v=tv, Ktw=0.5, tau_tw=0.2, **A8)
    DES[f"C2b_tv{tv:g}"] = R.Cfg(d=1, tau_v=tv, Ktw=0.5, **A8)
DES["C1_tv0.1_q2"] = R.Cfg(d=1, tau_v=0.1, q_out=2, Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9)
DES["C2_tv0.1_q2"] = R.Cfg(d=1, tau_v=0.1, q_out=2, Ktw=0.5, tau_tw=0.2, **A8)
DES["R8rev26_d0_tv0.1"] = R.Cfg(d=0, tau_v=0.1, Ktw=1.0, **A8)
cc = cl.nominal_controller_constants(); Tdec = np.column_stack([cc["A"], cc["n"]]); Ti = np.linalg.inv(Tdec)

def sens(lp, cfg, w):
    R.set_T(cfg.T)
    L = R.loop(lp, cfg)
    H = R.rcd.freq_resp(L, w)
    S = np.linalg.inv(np.eye(4)[None] + H)
    Su = np.einsum("ij,wjk,kl->wil", Tdec, S, Ti)
    return S, Su

def screen(args):
    item, name = args
    lp = R.make_plant(item); cfg = DES[name]
    w = np.logspace(-3, math.log10(math.pi / cfg.T * 0.9999), 1500)
    S, Su = sens(lp, cfg, w)
    return R.tag(lp), name, float(np.linalg.svd(Su - 0.5 * np.eye(4), compute_uv=False)[:, 0].max())

def mu_job(args):
    item, name = args
    lp = R.make_plant(item); cfg = DES[name]
    w = np.logspace(-3, math.log10(math.pi / cfg.T * 0.9999), 600)
    S, Su = sens(lp, cfg, w)
    out = {}
    for nm, Sx in (("legs", Su), ("decoupled", S)):
        Nd = Sx - 0.5 * np.eye(4)
        sv = np.linalg.svd(Nd, compute_uv=False)[:, 0]
        # mu only where the unstructured bound is within 60 % of its max (mu <= sigma)
        idx = np.where(sv >= 0.4 * sv.max())[0]
        mu = np.zeros_like(sv)
        for k in idx:
            mu[k] = R.rcd.mu_upper_dscale(Nd[k])
        k = int(np.argmax(mu))
        # refine around the peak
        wr = np.linspace(w[max(k - 2, 0)], w[min(k + 2, len(w) - 1)], 41)
        S2, Su2 = sens(lp, cfg, wr)
        N2 = (Su2 if nm == "legs" else S2) - 0.5 * np.eye(4)
        mu2 = np.array([R.rcd.mu_upper_dscale(n_) for n_ in N2])
        kk = int(np.argmax(mu2))
        mpk = max(float(mu.max()), float(mu2.max()))
        a = 1.0 / mpk
        lb = R.rcd.mu_lower_phase(N2[kk], np.random.default_rng(12345))
        out[nm] = {"alpha": a, "w_peak": float(wr[kk]), "mu_peak": mpk, "mu_lower": lb,
                   "DGM_dB": 20 * math.log10((1 + a / 2) / (1 - a / 2)) if a < 2 else math.inf,
                   "DPM_deg": math.degrees(2 * math.atan(a / 2)), "Npk": N2[kk]}
        try:
            import dkpy
            Nw = np.transpose(N2[[kk]], (1, 2, 0))
            mu_lmi, _, _, _ = dkpy.SsvLmiBisection(n_jobs=None, bisection_rtol=1e-5).compute_ssv(
                Nw, [dkpy.ComplexFullBlock(1, 1) for _ in range(4)])
            out[nm]["mu_dkpy"] = float(mu_lmi[0])
        except Exception as e:
            out[nm]["mu_dkpy"] = repr(e)
        out[nm].pop("Npk")
    return R.tag(lp), name, out

if __name__ == "__main__":
    t0 = time.perf_counter()
    items = R.catalogue_ext()
    with Pool(14) as p:
        scr = p.map(screen, [(it, n) for n in DES for it in items], chunksize=4)
    top = {}
    for n in DES:
        rows = sorted([(v, t) for t, nn, v in scr if nn == n], reverse=True)[:5]
        top[n] = rows
    jobs = []
    tagmap = {R.tag(R.make_plant(it)) if it[1] != 1.0 else it[0].tag(): it for it in items}
    for n, rows in top.items():
        for v, t in rows:
            jobs.append((tagmap[t], n))
    with Pool(14) as p:
        res = p.map(mu_job, jobs, chunksize=1)
    out = {}
    for t, n, r in res:
        out.setdefault(n, []).append({"plant": t, **{k: {kk: vv for kk, vv in v.items()} for k, v in r.items()}})
    summ = {n: {"legs_alpha_min": min(x["legs"]["alpha"] for x in v), "legs_plant": min(v, key=lambda x: x["legs"]["alpha"])["plant"],
                "legs_w": min(v, key=lambda x: x["legs"]["alpha"])["legs"]["w_peak"],
                "dec_alpha_min": min(x["decoupled"]["alpha"] for x in v),
                "dkpy_relmax": max(abs(x[k]["mu_dkpy"] - x[k]["mu_peak"]) / x[k]["mu_peak"] for x in v for k in ("legs", "decoupled") if isinstance(x[k]["mu_dkpy"], float)),
                "mu_lower_ratio_min": min(x[k]["mu_lower"] / x[k]["mu_peak"] for x in v for k in ("legs", "decoupled"))}
            for n, v in out.items()}
    json.dump({"summary": summ, "detail": out, "screen_top5": top}, open("r8d1_mimo_final.json", "w"), indent=1, default=float)
    for n, s in summ.items():
        a = s["legs_alpha_min"]
        print(n, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}, "DGM legs %.2f dB DPM %.1f deg" % (20 * math.log10((1 + a / 2) / (1 - a / 2)), math.degrees(2 * math.atan(a / 2))))
    print("wall", round(time.perf_counter() - t0, 1))
