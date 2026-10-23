"""R8 with one-period output delay (d = 1): exact multirate (lifted) linear model of the C2 loops.

Structure (per 10 Hz period T, N substeps of h = T / N):
  * plant (c2_linear.build_plant, continuous) driven by the leg speed u_a; valve = first-order lag
    tau_v u_a' = u_c - u_a (tau_v = 0: u_a = u_c), u_c = ZOH of the controller command, applied d periods
    after the sample it was computed from (d = 1: read at t_k, output at t_{k+1});
  * IMU accelerometer tilt = mean over each substep h (100 Hz, IMU internal decimation, ASSUMPTION boxcar),
    attitude low-pass (n stages x first-order tau_f, forward-Euler at h, as the spec 99.3 multirate filter);
  * pressure (n^T P) and stroke (clearance) = instantaneous samples at t_k;
  * attitude read at t_k + m h (m = 0: same instant as the pressures; m > 0 'late IMU read', needs d >= 1);
  * controller at T: heave Kz with first-order clearance LPF tau_z (forward Euler), attitude PI
    Kp + Ki T z / (z - 1) (filter is in the plant here), twist P Ktw / k_nom; optional Smith-type predictor
    per channel: y_ctrl = y + G_m (1 - z^-d) v (pending-command prediction, G_m = static gain x
    integrator x valve-lag model (x attitude filter model), ZOH at T).
Loop broken at the decoupled command v = [z_dot, phi_dot, theta_dot, tau_dot]; negative feedback v = -K y.
Units: m, rad, N, s; T discrete (ZOH). Validation: N = 1, tau_v = 0, m = 0 reproduces c2_linear.discrete_loop
at T = 0.1 (filter at T, tilt mean over T) = run_c2_r8_linear_check 'T0.1_prop_d1' (worst M_s 2.5819).
"""
from __future__ import annotations

import inspect
import math
import sys
import warnings
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import scipy.linalg as sla

PROJ = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(PROJ / "04_scripts" / "03_control"))
sys.path.insert(0, str(PROJ / "04_scripts" / "01_dynamics"))
import c2_linear as cl  # noqa: E402
import run_c2_design as rcd  # noqa: E402
import dyn_model as dm  # noqa: E402

warnings.filterwarnings("ignore")
CH = ("z", "phi", "theta", "tw")

# --- crawler tangential stiffness variant (build_plant copy with one line changed, read-only use of c2_linear)
_src = inspect.getsource(cl.build_plant)
_old = "khh = np.concatenate([kt, kcr])"
assert _src.count(_old) == 1
_src = _src.replace("def build_plant(case: PlantCase) -> LinPlant:", "def build_plant_kt(case, kt_cr_scale=1.0):")
_src = _src.replace(_old, "khh = np.concatenate([kt, kcr * kt_cr_scale])")
_src = _src.replace("sc = build_plant(pc).inertia_scale", "sc = cl.build_plant(pc).inertia_scale")
_ns = dict(cl.__dict__); _ns["cl"] = cl
exec(compile(_src, "build_plant_kt", "exec"), _ns)
build_plant_kt = _ns["build_plant_kt"]


@dataclass(frozen=True)
class Cfg:
    T: float = 0.1            # control / pressure / output period [s]
    N: int = 10               # IMU substeps per period (h = T / N)
    d: int = 1                # output delay [periods]
    tau_v: float = 0.0        # valve first-order lag [s]
    m_att: int = 0            # attitude read at t_k + m_att h
    Kp: float = 0.2
    Ki: float = 0.01
    tau_f: float = 0.8
    n_st: int = 2
    Kz: float = 0.5
    tau_z: float = 0.2
    Ktw: float = 1.0
    smith: tuple = ()         # channels with the pending-command predictor, subset of CH
    smith_lag: bool = True    # predictor model includes the valve lag (tau_v_model)
    tau_v_model: float | None = None   # predictor valve lag model (None = tau_v)
    smith_scale: tuple = (1.0, 1.0, 1.0, 1.0)  # multiplier on the predictor static gains (mismatch study)
    q_out: int = 0            # output switches at t_{k+d} + q_out h (transmission / ramp offset inside the period)
    p_imu: int = 0            # IMU transport delay [substeps h]
    pd: int = 0               # extra delay [periods] on the pressure / stroke outputs (harness 'late' scheme)
    tau_tw: float = 0.0       # first-order low-pass on n^T P in the twist loop [s] (0 = none)
    tau_v_leg: tuple = ()     # per-leg valve lag (overrides tau_v when given)
    kq_leg: tuple = ()        # per-leg flow-gain multiplier
    guard_leg: int = -1       # F_min guard active on this leg (0..3): twist command += -Kg/k_nom sgn(n_i) P_i
    Kg: float = 1.0           # guard gain [1/s]


def _avg_maps(A, B, h):
    return cl.c2d_zoh_avg(A, B, h)


def lifted_plant(lp, cfg: Cfg):
    """10 Hz state-space G: v (4, decoupled) -> y = [clr, phi_f, theta_f, nP], incl. delay line, valve, IMU filter."""
    import control as ct
    cc = cl.nominal_controller_constants()
    Tdec = np.column_stack([cc["A"], cc["n"]])
    T, N = cfg.T, cfg.N
    h = T / N
    A, B, C, D = lp.A, lp.B, lp.C, lp.D
    nx = A.shape[0]
    kq = np.diag(cfg.kq_leg) if cfg.kq_leg else np.eye(4)
    tvl = np.asarray(cfg.tau_v_leg, float) if cfg.tau_v_leg else np.full(4, cfg.tau_v)
    if np.any(tvl > 0):
        if np.any(tvl <= 0):
            raise ValueError("mixed zero / non-zero per-leg lag not supported")
        Aa = np.zeros((nx + 4, nx + 4)); Aa[:nx, :nx] = A; Aa[:nx, nx:] = B; Aa[nx:, nx:] = -np.diag(1.0 / tvl)
        Ba = np.zeros((nx + 4, 4)); Ba[nx:] = np.diag(1.0 / tvl) @ kq
        Ca = np.hstack([C, D]); Da = np.zeros_like(D)
    else:
        Aa, Ba, Ca, Da = A, B @ kq, C, D @ kq
    na = Aa.shape[0]
    Ah, Bh, Exh, Euh = _avg_maps(Aa, Ba, h)
    i_pa, i_ta = lp.idx("phi_acc"), lp.idx("theta_acc")
    Rt = Ca[[i_pa, i_ta]] @ Exh                         # tilt mean over substep j from xi_{j-1}
    Qt = Ca[[i_pa, i_ta]] @ Euh + Da[[i_pa, i_ta]]
    ns = cfg.n_st
    a = h / cfg.tau_f
    p = cfg.p_imu
    nc = 2 * p
    nz = na + nc + 2 * ns                                 # [xi, imu delay c_1..c_p (2 each), f stages (2 each)]
    M = np.zeros((nz, nz)); Nin = np.zeros((nz, 4))
    M[:na, :na] = Ah; Nin[:na] = Bh
    raw_z = np.zeros((2, nz)); raw_z[:, :na] = Rt; raw_u = Qt.copy()
    if p > 0:
        M[na:na + 2] = raw_z; Nin[na:na + 2] = raw_u     # c_1(j) = raw_j
        for i in range(1, p):
            M[na + 2 * i:na + 2 * i + 2, na + 2 * (i - 1):na + 2 * i] = np.eye(2)
        inp_z = np.zeros((2, nz)); inp_z[:, na + 2 * (p - 1):na + 2 * p] = np.eye(2); inp_u = np.zeros((2, 4))
    else:
        inp_z, inp_u = raw_z, raw_u
    f0 = na + nc
    for s_ in range(ns):
        sl = slice(f0 + 2 * s_, f0 + 2 * s_ + 2)
        row_z = (1 - a) * np.eye(2, nz, k=f0 + 2 * s_) + a * inp_z
        row_u = a * inp_u
        M[sl] = row_z; Nin[sl] = row_u
        inp_z, inp_u = row_z, row_u
    Mp = [np.eye(nz)]
    for _ in range(N):
        Mp.append(Mp[-1] @ M)
    Gam = [np.zeros((nz, 4))]
    for j in range(1, N + 1):
        Gam.append(Gam[-1] + Mp[j - 1] @ Nin)             # sum_{i<j} M^i Nin
    Phi = Mp[N]
    q = cfg.q_out
    if not 0 <= q < N:
        raise ValueError("q_out out of range")
    iP = [lp.idx(f"P_{nm}") for nm in dm.LEG_NAMES]
    Cclr = np.zeros(nz); Cclr[:na] = Ca[lp.idx("clr")]
    CnP = np.zeros(nz); CnP[:na] = cc["n"] @ Ca[iP]
    fsel = np.zeros((2, nz)); fsel[:, f0 + 2 * (ns - 1): f0 + 2 * ns] = np.eye(2)
    m = cfg.m_att
    d = cfg.d
    if m > 0 and d < 1:
        raise ValueError("late attitude read needs d >= 1")
    # inputs during period k: old = Tdec v_{k-d-1} for substeps < q, new = Tdec v_{k-d} otherwise
    G_new, G_old = Gam[N - q], Gam[N] - Gam[N - q]
    if m <= q:
        A_old, A_new = Gam[m], np.zeros((nz, 4))
    else:
        A_old, A_new = Gam[m] - Gam[m - q], Gam[m - q]
    nline = d + (1 if q > 0 else 0)
    Ntot = nz + 4 * nline
    A10 = np.zeros((Ntot, Ntot)); B10 = np.zeros((Ntot, 4)); C10 = np.zeros((4, Ntot)); D10 = np.zeros((4, 4))
    A10[:nz, :nz] = Phi
    if nline > 0:
        B10[nz:nz + 4] = Tdec
        for j in range(1, nline):
            A10[nz + 4 * j:nz + 4 * j + 4, nz + 4 * (j - 1):nz + 4 * j] = np.eye(4)

    def put(lag, Mz, rows_A=None, rows_C=None):
        """input v_{k-lag} enters through Mz (nz x 4, applied to Tdec v)."""
        if lag == 0:
            if rows_A is not None:
                B10[:nz] += Mz @ Tdec
            else:
                raise ValueError("direct feedthrough to the outputs")
        else:
            blk = slice(nz + 4 * (lag - 1), nz + 4 * lag)
            if rows_A is not None:
                A10[:nz, blk] += Mz
            else:
                C10[1:3, blk] += rows_C @ Mz
    put(d, G_new, rows_A=True)
    if q > 0:
        put(d + 1, G_old, rows_A=True)
    C10[0, :nz] = Cclr
    C10[1:3, :nz] = fsel @ Mp[m]
    if m > 0:
        if np.any(A_new):
            put(d, A_new, rows_C=fsel)
        if np.any(A_old):
            put(d + 1, A_old, rows_C=fsel)
    C10[3, :nz] = CnP
    if cfg.pd > 0:
        # extra output delay line for rows 0 (clr) and 3 (nP): 2 * pd states
        nl = 2 * cfg.pd
        A2 = np.zeros((Ntot + nl, Ntot + nl)); A2[:Ntot, :Ntot] = A10
        B2 = np.zeros((Ntot + nl, 4)); B2[:Ntot] = B10
        A2[Ntot:Ntot + 2, :Ntot] = C10[[0, 3]]
        for j in range(1, cfg.pd):
            A2[Ntot + 2 * j:Ntot + 2 * j + 2, Ntot + 2 * (j - 1):Ntot + 2 * j] = np.eye(2)
        C2 = np.zeros((4, Ntot + nl)); C2[1:3, :Ntot] = C10[1:3]
        C2[0, Ntot + nl - 2] = 1.0; C2[3, Ntot + nl - 1] = 1.0
        A10, B10, C10 = A2, B2, C2
    if cfg.guard_leg >= 0:
        if cfg.pd > 0:
            raise ValueError("guard with pd not supported")
        i = cfg.guard_leg
        rowg = np.zeros(C10.shape[1]); rowg[:nz] = np.sign(cc["n"][i]) * np.r_[Ca[iP[i]], np.zeros(nz - na)]
        C10 = np.vstack([C10, rowg]); D10 = np.vstack([D10, np.zeros((1, 4))])
    return ct.ss(A10, B10, C10, D10, T), Tdec


def static_gains(lp):
    cc = cl.nominal_controller_constants()
    Tdec = np.column_stack([cc["A"], cc["n"]])
    return rcd.static_dec_gain(lp, Tdec)


_G0_NOM = None


def g0_nominal():
    global _G0_NOM
    if _G0_NOM is None:
        _G0_NOM = np.diag(static_gains(cl.build_plant(cl.PlantCase()))).copy()
    return _G0_NOM


def controller(cfg: Cfg, k_nom):
    import control as ct
    T = cfg.T
    PI = ct.tf([cfg.Kp + cfg.Ki * T, -cfg.Kp], [1.0, -1.0], T)
    Kz = ct.tf([cfg.Kz], [1.0], T)
    if cfg.tau_z > 0:
        az = T / cfg.tau_z
        Kz = Kz * ct.tf([az, 0.0], [1.0, -(1.0 - az)], T)
    Ktw = ct.tf([cfg.Ktw / k_nom], [1.0], T)
    if cfg.tau_tw > 0:
        at = T / cfg.tau_tw
        Ktw = Ktw * ct.tf([at, 0.0], [1.0, -(1.0 - at)], T)
    Ks = [Kz, PI, PI, Ktw]
    if cfg.smith:
        g0 = g0_nominal() * np.asarray(cfg.smith_scale)
        tvm = cfg.tau_v if cfg.tau_v_model is None else cfg.tau_v_model
        for j, ch in enumerate(CH):
            if ch not in cfg.smith:
                continue
            num, den = [g0[j]], [1.0, 0.0]                # g0 / s
            if cfg.smith_lag and tvm > 0:
                den = np.polymul(den, [tvm, 1.0])
            if ch in ("phi", "theta"):
                for _ in range(cfg.n_st):
                    den = np.polymul(den, [cfg.tau_f, 1.0])
            Gm = ct.sample_system(ct.tf(num, den), T, "zoh")
            # (1 - z^-d) G_m, cancel the integrator pole exactly
            dz = ct.tf(np.r_[1.0, np.zeros(cfg.d - 1), -1.0], np.r_[1.0, np.zeros(cfg.d)], T)
            Pi = ct.minreal(dz * Gm, tol=1e-9, verbose=False)
            # v = -K (y + Pi v)  ->  -v = feedback(K, Pi) y
            Ks[j] = ct.feedback(Ks[j], Pi)
    return Ks


def loop(lp, cfg: Cfg):
    import control as ct
    G, _ = lifted_plant(lp, cfg)
    k_nom = cl.nominal_controller_constants()["k_nom"]
    Ks = controller(cfg, k_nom)
    if cfg.guard_leg >= 0:
        Ks = Ks + [ct.tf([cfg.Kg / k_nom], [1.0], cfg.T)]
        Kd = ct.append(*[ct.ss(k) for k in Ks])
        Msum = np.zeros((4, 5)); Msum[:4, :4] = np.eye(4); Msum[3, 4] = 1.0
        return ct.ss([], [], [], Msum, cfg.T) * Kd * G if False else _sum(Kd, Msum) * G
    Kd = ct.append(*[ct.ss(k) for k in Ks])
    return Kd * G


def _sum(Kd, Msum):
    import control as ct
    return ct.ss(Kd.A, Kd.B, Msum @ Kd.C, Msum @ Kd.D, Kd.dt)


def set_T(T):
    rcd.T = T; rcd.W_NYQ = math.pi / T


def analyse(lp, cfg: Cfg, open_too=False):
    import control as ct
    set_T(cfg.T)
    L = loop(lp, cfg)
    res = {}
    for j, ch in enumerate(CH):
        F = np.eye(4); F[j, j] = 0.0
        Lc = ct.feedback(L, F)
        sj = ct.ss(Lc.A, Lc.B[:, [j]], Lc.C[[j], :], Lc.D[[j], [j]], cfg.T)
        r = rcd.siso_margins(sj)
        res[ch] = {"Ms": r["Ms"], "w_Ms": r["w_Ms_rad_s"], "PM": r["PM_deg"], "PMmin": r["PM_min_deg"],
                   "GMup": r["GM_upper"], "wgc": r["w_gc_rad_s"], "DM": r["delay_margin_s"]}
    cc = cl.nominal_controller_constants(); Tdec = np.column_stack([cc["A"], cc["n"]])
    w = np.logspace(-3, math.log10(math.pi / cfg.T * 0.9999), 3000)
    H = rcd.freq_resp(L, w)
    Hu = np.einsum("ij,wjk,kl->wil", Tdec, H, np.linalg.inv(Tdec))
    res["Ms_leg_sv"] = float(max(np.linalg.svd(np.linalg.inv(np.eye(4)[None] + Hu), compute_uv=False)[:, 0]))
    p = ct.feedback(L, np.eye(4)).poles()
    res["rho"] = float(np.max(np.abs(p)))
    res["Ms_max"] = max(res[c]["Ms"] for c in CH)
    res["Ms_ch"] = max(CH, key=lambda c: res[c]["Ms"])
    return res, L


def catalogue_ext():
    """76 plants of run_c2_design.catalogue(full=True) + crawler tangential stiffness x0.3 / x3 (top, crawler,
    beta 1.0, rigid / sup_lower) = 80."""
    out = [(c, 1.0) for c in rcd.catalogue(full=True)]
    for s in (0.3, 3.0):
        for mast in ("rigid", "sup_lower"):
            out.append((cl.PlantCase(level="top", support="crawler", beta=1.0e9, mast=mast), s))
    return out


def make_plant(item):
    case, s = item
    if s == 1.0:
        return cl.build_plant(case)
    lp = build_plant_kt(case, s)
    lp.case = replace(case)
    lp._kt_tag = f"_ktcr{s:g}"
    return lp


def tag(lp):
    return lp.case.tag() + getattr(lp, "_kt_tag", "")
