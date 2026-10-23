"""Brute-force 100 Hz simulation of the open loop G (v -> [clr, phi_f, theta_f, nP]) vs the lifted model."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, scipy.linalg as sla
import r8d1_lin as R, c2_linear as cl, dyn_model as dm

def brute(lp, cfg, V):
    cc = cl.nominal_controller_constants(); Tdec = np.column_stack([cc["A"], cc["n"]])
    h = cfg.T / cfg.N
    A, B, C, D = lp.A, lp.B, lp.C, lp.D
    nx = A.shape[0]
    if cfg.tau_v > 0:
        Aa = np.block([[A, B], [np.zeros((4, nx)), -np.eye(4) / cfg.tau_v]]); Ba = np.vstack([np.zeros((nx, 4)), np.eye(4) / cfg.tau_v])
        Ca = np.hstack([C, D]); Da = np.zeros_like(D)
    else:
        Aa, Ba, Ca, Da = A, B, C, D
    # independent discretisation: 200 sub-sub-steps with exact ZOH matrices, tilt mean by midpoint-free exact sums
    K = 50; dt = h / K
    E = sla.expm(np.block([[Aa, Ba], [np.zeros((4, Aa.shape[0] + 4))]]) * dt)
    Ad, Bd = E[:Aa.shape[0], :Aa.shape[0]], E[:Aa.shape[0], Aa.shape[0]:]
    ia, it = lp.idx("phi_acc"), lp.idx("theta_acc"); iP = [lp.idx(f"P_{n}") for n in dm.LEG_NAMES]
    x = np.zeros(Aa.shape[0]); f = np.zeros((cfg.n_st, 2)); a = h / cfg.tau_f
    tilt_hist = []
    Y = []
    nk = V.shape[0]
    vhist = {}
    for k in range(nk):
        vhist[k] = V[k]
        att_read = None
        for j in range(cfg.N):
            if j == cfg.m_att and k >= 0:
                att_read = f[-1].copy()
            if j == 0:
                y0 = [Ca[lp.idx("clr")] @ x, cc["n"] @ (Ca[iP] @ x)]
            lag = cfg.d + (1 if j < cfg.q_out else 0)
            u = Tdec @ vhist.get(k - lag, np.zeros(4))
            # tilt mean over the substep: trapezoid on K sub-sub-steps (Simpson-like accuracy, dt small)
            acc = np.zeros(2)
            for i in range(K):
                t0 = Ca[[ia, it]] @ x + Da[[ia, it]] @ u
                x = Ad @ x + Bd @ u
                t1 = Ca[[ia, it]] @ x + Da[[ia, it]] @ u
                acc += 0.5 * (t0 + t1) / K
            tilt_hist.append(acc)
            inp = tilt_hist[-1 - cfg.p_imu] if len(tilt_hist) > cfg.p_imu else np.zeros(2)
            for s in range(cfg.n_st):
                f[s] = (1 - a) * f[s] + a * inp
                inp = f[s]
        # note: outputs belong to t_k (start of period k); att_read taken at substep m (m = 0 -> start)
        Y.append([y0[0], att_read[0], att_read[1], y0[1]])
    return np.array(Y)

def lifted(lp, cfg, V):
    G, _ = R.lifted_plant(lp, cfg)
    A, B, C, Dm = (np.asarray(m) for m in (G.A, G.B, G.C, G.D))
    z = np.zeros(A.shape[0]); Y = []
    for k in range(V.shape[0]):
        Y.append(C @ z + Dm @ V[k]); z = A @ z + B @ V[k]
    return np.array(Y)

rng = np.random.default_rng(7)
lp = cl.build_plant(cl.PlantCase(level="top", support="pads", beta=1.6e9, mast="sup_lower"))
V = rng.normal(size=(30, 4)) * np.array([1e-3, 1e-3, 1e-3, 1e-3])
for kw in (dict(d=1), dict(d=1, tau_v=0.1), dict(d=1, tau_v=0.1, m_att=9), dict(d=1, tau_v=0.05, q_out=3),
           dict(d=1, tau_v=0.05, q_out=3, m_att=6), dict(d=1, tau_v=0.05, p_imu=2, m_att=9), dict(d=2, q_out=4, m_att=2, p_imu=1)):
    cfg = R.Cfg(**kw)
    Yb, Yl = brute(lp, cfg, V), lifted(lp, cfg, V)
    rel = np.abs(Yb - Yl).max(axis=0) / np.abs(Yl).max(axis=0)
    print(kw, "max rel diff per output", np.array2string(rel, precision=2))
