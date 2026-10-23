"""Linear plant and discrete C2 loop models for the C2 levelling controller design (00_docs/04_control/c2_design.md).

Plant (continuous, small motions about the operating point, read-only use of dyn_model.py and 02_params/rexome33.yaml)
  * Rigid body = superstructure (auger level) + 4 rods lumped at the operating extension (dyn_model.body_with_rods),
    6 DoF q = [ux, uy, uz, phi, theta, psi] about the combined CoM (same body as run_control_comparison.Plant).
  * Pads ("pads" support): vertical series spring k_v = k_oil(e_op; beta) (+) k_rod (+) k_frame (+) k_concrete at the
    pad bottom, dashpot c_n acting on (u_i - pad vertical velocity) exactly as the reduced nonlinear model
    (run_control_comparison.physics: F = k_s c + c_n (u - v_n)), tangential bushing k_t, c_t (L1 YAML),
    geometric (preload) stiffness of the static pad forces (dyn_model.stiffness_6dof convention).
  * "crawler" support (start of levelling, pads just touched, crawler still bears the load): pads at the touch
    extension + the 12 floor-contact crawler rollers of layout D (k = 1e8 / 12 N/m each, tangential k_t = k_n per
    point as in the reduced model, heave zeta 0.05 dashpots), all bilateral (linearised about the touched state).
  * Leg reference strokes s (4) are integrator states, s_dot = u (leg speed command, m/s), F_seal = 0 (L1).
  * Optional mast surrogate: roll / pitch inertia scaled so that the 1st / 2nd rocking frequencies equal the coupled
    flexible-mast values of dynamics_model.md 3.9.3 (ASSUMPTION: inertia-scaling surrogate, damping matrix unchanged
    so the modal zeta drops with the frequency - conservative).
Outputs
  * phi_acc, theta_acc: accelerometer tilt at the IMU point (phi + a_y/g, theta - a_x/g, body axes, small angles),
  * phi, theta: true attitude,
  * P (4): cylinder-force (pressure) reading = k_v (s - pad vertical displacement) (spring part only, as the reduced
    model's k_oil (s_ref - x)),
  * x (4): stroke sensor (rod position) = s - P / k_oil,
  * clr: crawler clearance estimate from the strokes (run_control_comparison.Ctx.clearance_est linearised at the
    mean crawler corner).
Units: m, rad, N, s. Feedback sign: negative feedback v = -K y in the decoupled channels (heave, roll, pitch, twist).
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.linalg as sla

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
import dyn_model as dm  # noqa: E402

T_CTRL = 0.02                       # control period [s] (CLAUDE.md "제어 주기(기본 20 ms 가정)")
IMU_POINT_C1_BODY_M = (0.31, 0.88, 0.040)   # user decision 2026-10-20 (CLAUDE.md)
G = 9.80665

# coupled flexible-mast rocking frequencies [Hz] (dynamics_model.md 3.9.3, rows: level -> support case -> (1st, 2nd))
MAST_COUPLED_HZ = {
    "top": {"rigid": (1.785, 2.984), "sup_rigid": (1.601, 2.440), "sup_upper": (1.415, 2.102), "sup_lower": (0.914, 1.536)},
    "middle": {"rigid": (2.309, 3.509), "sup_rigid": (2.232, 3.203), "sup_upper": (2.031, 2.932), "sup_lower": (1.380, 2.311)},
    "bottom": {"rigid": (2.857, 3.928), "sup_rigid": (2.776, 3.794), "sup_upper": (2.606, 3.605), "sup_lower": (1.858, 2.934)},
}


@dataclass
class PlantCase:
    level: str = "top"
    support: str = "pads"           # "pads" | "crawler"
    beta: float = 1.0e9             # effective bulk modulus [Pa]
    mast: str = "rigid"             # key of MAST_COUPLED_HZ[level]
    k_scale: tuple = (1.0, 1.0, 1.0, 1.0)   # per-leg multiplier on the vertical support stiffness (soft pad cases)
    imu_point: tuple = IMU_POINT_C1_BODY_M
    c_scale: float = 1.0            # multiplier on the pad dashpots c_n, c_t (1/3: leg zeta 0.03 -> 0.01, sensitivity)

    def tag(self):
        ks = "" if tuple(self.k_scale) == (1.0, 1.0, 1.0, 1.0) else "_k" + "-".join(f"{v:g}" for v in self.k_scale)
        cs = "" if self.c_scale == 1.0 else f"_c{self.c_scale:.3g}"
        return f"{self.level}_{self.support}_b{self.beta / 1e9:g}_{self.mast}{ks}{cs}"


@dataclass
class LinPlant:
    case: PlantCase
    A: np.ndarray
    B: np.ndarray
    C: np.ndarray
    D: np.ndarray
    out_names: list
    M: np.ndarray
    K: np.ndarray
    Cd: np.ndarray
    Bk: np.ndarray
    Bc: np.ndarray
    kv: np.ndarray
    ko: np.ndarray
    J_K: np.ndarray                 # quasi-static d[uz_o, phi, theta]/ds (about the frame origin), 3x4
    S: np.ndarray                   # quasi-static dP/ds, 4x4
    modes_hz: np.ndarray = field(default_factory=lambda: np.zeros(0))
    modes_zeta: np.ndarray = field(default_factory=lambda: np.zeros(0))
    inertia_scale: tuple = (1.0, 1.0)

    def idx(self, name):
        return self.out_names.index(name)


def _ctx():
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    return p, geo


def nominal_controller_constants():
    """A (4x3), n (4), k_nom (mean L1 pad stiffness, beta 1.0 GPa), F_min, v_max: as run_control_comparison.Ctx."""
    p, geo = _ctx()
    L1 = p["contact"]["rigid_floor"]["L1"]
    kn = np.array([L1["kn_per_pad_N_m"][nm] for nm in dm.LEG_NAMES], float)
    W = dm.body_from_params(p, "top").mass * geo.g
    return {"A": dm.support_matrix(geo.pad_xy), "n": dm.twist_vector(geo.pad_xy), "k_nom": float(kn.mean()),
            "F_min": 0.1 * W / 4, "v_max": geo.v_max, "stroke": geo.stroke, "pad_xy": geo.pad_xy}


def build_plant(case: PlantCase) -> LinPlant:
    p, geo = _ctx()
    A_ = dm.ASSUMPTIONS
    e_op = geo.touch_extension + A_["crawler_clearance_m"]
    e_lin = e_op if case.support == "pads" else geo.touch_extension
    body = dm.body_with_rods(p, geo, case.level, e_op)
    m = body.mass
    Ib = body.inertia.copy()
    com = body.com
    kc = dm.k_concrete_westergaard()["k_slab_N_m"]
    # per leg (4,): k_rod() is per leg once the legs carry different rod diameters (rev. 30, as Plant)
    ks = np.broadcast_to(np.asarray(dm.series(dm.k_rod(), A_["frame_bracket_stiffness_N_m"], kc), float), (4,)).copy()
    ko = np.asarray(dm.k_oil(e_op, beta=case.beta), float)   # oil column at the operating extension (as Plant)
    kv = 1.0 / (1.0 / ko + 1.0 / ks)
    kv = kv * np.asarray(case.k_scale, float)
    L1 = p["contact"]["rigid_floor"]["L1"]
    kt = np.array([L1["kt_per_pad_N_m"][nm] for nm in dm.LEG_NAMES], float)
    cn = np.array([L1["cn_per_pad_N_s_m"][nm] for nm in dm.LEG_NAMES], float) * case.c_scale
    ct = np.array([L1["ct_per_pad_N_s_m"][nm] for nm in dm.LEG_NAMES], float) * case.c_scale
    pad_pts = np.column_stack([geo.pad_xy, geo.pad_z_retracted - e_lin])
    W = m * geo.g
    # crawler (rollers only, layout D) for the "crawler" support
    cxy, kcr, _ = dm.crawler_points(p)
    cgap = dm.crawler_gaps(p)
    rol = cgap <= 0
    cxy, kcr = cxy[rol], kcr[rol]
    c_tot = dm.crawler_damping_total(float(p["contact"]["crawler"]["kn_total_N_m"]), m)
    ccr = np.full(len(cxy), c_tot / len(cxy))
    cr_pts = np.column_stack([cxy, np.full(len(cxy), geo.crawler_bottom_z)])
    # static vertical forces (for the geometric stiffness)
    if case.support == "pads":
        F0, _, _ = dm.static_loads(kv, geo.pad_xy, W, com[:2])
        Fcr = np.zeros(0)
        pts = pad_pts; kvv = kv; khh = kt; cvv = cn; chh = ct
    else:
        P_touch = 1.5 * 0.1 * dm.body_from_params(p, case.level).mass * geo.g / 4   # pads preloaded to the touch threshold
        xy_all = np.vstack([geo.pad_xy, cxy])
        k_all = np.concatenate([kv, kcr])
        delta = np.concatenate([P_touch / kv, np.zeros(len(cxy))])
        Fall, _, _ = dm.static_unilateral(xy_all, k_all, delta, W, com[:2])
        F0, Fcr = Fall[:4], Fall[4:]
        pts = np.vstack([pad_pts, cr_pts]); kvv = np.concatenate([kv, kcr]); khh = np.concatenate([kt, kcr])
        cvv = np.concatenate([cn, ccr]); chh = np.concatenate([ct, ccr])
        F0 = np.concatenate([F0, Fcr])
    # mass / stiffness / damping
    Mm = np.zeros((6, 6)); Mm[:3, :3] = m * np.eye(3); Mm[3:, 3:] = Ib
    K = np.zeros((6, 6)); Cd = np.zeros((6, 6))
    for i in range(len(pts)):
        d = pts[i] - com
        ax, ay, az = dm.a_vec(d)
        K += kvv[i] * np.outer(az, az) + khh[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        Cd += cvv[i] * np.outer(az, az) + chh[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        K[3:, 3:] -= F0[i] * dm._hz(d)
    Bk = np.zeros((6, 4)); Bc = np.zeros((6, 4)); Az = np.zeros((4, 6))
    for i in range(4):
        _, _, az = dm.a_vec(pad_pts[i] - com)
        Bk[:, i] = kv[i] * az; Bc[:, i] = cn[i] * az; Az[i] = az
    # mast surrogate: scale Ixx, Iyy to hit the coupled rocking frequencies
    sc = (1.0, 1.0)
    if case.mast != "rigid" and case.support == "pads":
        # same frequency ratios (coupled / rigid, beta 1.0 in dynamics_model.md 3.9.3) applied to this beta's rigid modes
        f_r = np.sort(_modes(Mm, K))[:2]
        ref = MAST_COUPLED_HZ[case.level]
        tgt = (f_r[0] * ref[case.mast][0] / ref["rigid"][0], f_r[1] * ref[case.mast][1] / ref["rigid"][1])
        sc = _fit_inertia_scale(Mm, K, tuple(f_r), tgt)
    elif case.mast != "rigid":
        # crawler support: reuse the pads scale of the same level / mast case
        pc = PlantCase(case.level, "pads", case.beta, case.mast, case.k_scale, case.imu_point, case.c_scale)
        sc = build_plant(pc).inertia_scale
    if sc != (1.0, 1.0):
        Dm = np.diag([math.sqrt(sc[0]), math.sqrt(sc[1]), 1.0])
        Mm[3:, 3:] = Dm @ Ib @ Dm
    Minv = np.linalg.inv(Mm)
    n6 = 6
    nx = 2 * n6 + 4
    A = np.zeros((nx, nx)); B = np.zeros((nx, 4))
    A[:n6, n6:2 * n6] = np.eye(n6)
    A[n6:2 * n6, :n6] = -Minv @ K
    A[n6:2 * n6, n6:2 * n6] = -Minv @ Cd
    A[n6:2 * n6, 2 * n6:] = Minv @ Bk
    B[n6:2 * n6, :] = Minv @ Bc
    B[2 * n6:, :] = np.eye(4)
    # outputs
    rho = np.asarray(case.imu_point, float) - com
    ax_i, ay_i, _ = dm.a_vec(rho)
    acc_row = lambda a: (a @ A[n6:2 * n6, :], a @ B[n6:2 * n6, :])  # noqa: E731  translational accel of the IMU point
    rows = []; Drows = []; names = []
    ay_x, ay_u = acc_row(ay_i)
    r = np.zeros(nx); r[3] = 1.0
    rows.append(r + ay_x / G); Drows.append(ay_u / G); names.append("phi_acc")
    ax_x, ax_u = acc_row(ax_i)
    r = np.zeros(nx); r[4] = 1.0
    rows.append(r - ax_x / G); Drows.append(-ax_u / G); names.append("theta_acc")
    for j, nm in ((3, "phi"), (4, "theta")):
        r = np.zeros(nx); r[j] = 1.0
        rows.append(r); Drows.append(np.zeros(4)); names.append(nm)
    Prow = np.zeros((4, nx))
    for i in range(4):
        Prow[i, :n6] = -kv[i] * Az[i]; Prow[i, 2 * n6 + i] = kv[i]
        rows.append(Prow[i]); Drows.append(np.zeros(4)); names.append(f"P_{dm.LEG_NAMES[i]}")
    for i in range(4):
        r = -Prow[i] / ko[i]; r[2 * n6 + i] += 1.0
        rows.append(r); Drows.append(np.zeros(4)); names.append(f"x_{dm.LEG_NAMES[i]}")
    # clearance estimate (stroke plane fit) linearised: clr = zcb - (c0 + corner . c12), c = pinv([1 x y]) (zp - x)
    (x0, x1), (y0, y1) = geo.crawler_xy_box
    corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
    Mfit = np.column_stack([np.ones(4), geo.pad_xy])
    w_clr = np.concatenate([[1.0], corners.mean(axis=0)]) @ np.linalg.pinv(Mfit)   # d clr / d x
    xs = np.array(rows[-4:])
    rows.append(w_clr @ xs); Drows.append(np.zeros(4)); names.append("clr")
    C = np.array(rows); D = np.array(Drows)
    # quasi-static sensitivities (pads support): attitude about the frame origin and load
    kv_pad = kv
    J_K = dm.attitude_sensitivity(kv_pad, geo.pad_xy)
    S = dm.load_sensitivity(kv_pad, geo.pad_xy)
    lam = np.linalg.eigvals(A[:2 * n6, :2 * n6])
    lam = lam[np.imag(lam) > 1e-6]
    wn = np.abs(lam); order = np.argsort(wn)
    return LinPlant(case, A, B, C, D, names, Mm, K, Cd, Bk, Bc, kv, ko, J_K, S,
                    wn[order] / (2 * np.pi), (-np.real(lam) / wn)[order], sc)


def _modes(Mm, K):
    w2 = sla.eigh(K, Mm, eigvals_only=True)
    return np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)


def _fit_inertia_scale(Mm, K, f_rigid, f_target):
    """Scale factors (sx, sy) on Ixx, Iyy giving the target 1st / 2nd rocking frequencies (undamped)."""
    from scipy.optimize import least_squares
    Ib = Mm[3:, 3:].copy()

    def res(lg):
        sx, sy = np.exp(lg)
        Dm = np.diag([math.sqrt(sx), math.sqrt(sy), 1.0])
        M2 = Mm.copy(); M2[3:, 3:] = Dm @ Ib @ Dm
        f = np.sort(_modes(M2, K))
        return [math.log(f[0] / f_target[0]), math.log(f[1] / f_target[1])]

    g0 = [2 * math.log(f_rigid[0] / f_target[0]), 2 * math.log(f_rigid[1] / f_target[1])]
    r = least_squares(res, g0, xtol=1e-14, ftol=1e-14, gtol=1e-14)
    if max(abs(v) for v in res(r.x)) > 1e-8:
        raise RuntimeError(f"inertia scale fit failed: {r.message} {res(r.x)}")
    return tuple(float(v) for v in np.exp(r.x))


# ---------------------------------------------------------------------------- discretisation (ZOH + 20 ms average)


def c2d_zoh_avg(A, B, T):
    """ZOH discretisation and the interval-average maps.

    x[k+1] = Ad x[k] + Bd u[k];  (1/T) int_{kT}^{(k+1)T} x dt = Ex x[k] + Eu u[k]
    via one block exponential of [[A, B, 0, 0], [0, 0, 0, 0] ...] (Van Loan type)."""
    n, m = B.shape
    # block [[A, B, 0], [0, 0, 0], [I, 0, 0]] on [x; u; int x]
    Big = np.zeros((2 * n + m, 2 * n + m))
    Big[:n, :n] = A; Big[:n, n:n + m] = B
    Big[n + m:, :n] = np.eye(n)
    E = sla.expm(Big * T)
    Ad = E[:n, :n]; Bd = E[:n, n:n + m]
    Ix = E[n + m:, :n]; Iu = E[n + m:, n:n + m]     # int_0^T x(t) dt = Ix x0 + Iu u
    return Ad, Bd, Ix / T, Iu / T


@dataclass
class Gains:
    Kp: float = 0.4          # attitude proportional [1/s]
    Ki: float = 0.02         # attitude integral [1/s^2]
    Kz: float = 0.5          # heave (clearance) [1/s]
    Ktw: float = 0.5         # twist load loop [1/s] (rate = -Ktw n^T P / k_nom)
    tau_f: float = 0.5       # per first-order stage of the attitude low-pass [s]
    n_stages: int = 2
    delay_steps: int = 1     # extra input delay (computation / transmission) [control steps]
    ramp_delay_s: float = 0.0  # extra pure delay to represent the 0.1 s valve ramp in the small-signal model (0 or 0.05)
    tau_z: float = 0.0       # first-order low-pass on the stroke-based clearance used by the heave loop [s] (0 = none)


def discrete_loop(lp: LinPlant, gains: Gains, T=T_CTRL, k_nom=None, channels=("z", "phi", "theta", "tw")):
    """Discrete broken-loop model in the decoupled channels v = [z_dot, phi_dot, theta_dot, tau_dot] (others omitted
    if not in `channels`).

    Returns dict with state-space (Ad, Bd, Cd, Dd) of the plant G: v -> y_dec = [clr, phi_f_in, theta_f_in, nP]
    including: input map u = [A, n] v, extra input delay z^-d, ZOH plant, 20 ms averaged accelerometer tilt with its
    one-step availability delay, and the controller blocks (filter, PI, P) as separate SISO discrete systems.
    """
    import control as ct
    cc = nominal_controller_constants()
    Amat, n = cc["A"], cc["n"]
    k_nom = cc["k_nom"] if k_nom is None else k_nom
    Tdec = np.column_stack([Amat, n])                  # u = Tdec v
    Ad, Bd, Ex, Eu = c2d_zoh_avg(lp.A, lp.B, T)
    nx = Ad.shape[0]
    C = lp.C; D = lp.D
    i_pa, i_ta = lp.idx("phi_acc"), lp.idx("theta_acc")
    Cav = C[[i_pa, i_ta]] @ Ex
    Dav = C[[i_pa, i_ta]] @ Eu + D[[i_pa, i_ta]]
    iP = [lp.idx(f"P_{nm}") for nm in dm.LEG_NAMES]
    CnP = n @ C[iP]
    Cclr = C[lp.idx("clr")]
    # augmented plant: states [x (nx), d_avg (2), input delay line (4*delay)]
    dsteps = int(gains.delay_steps) + int(round(gains.ramp_delay_s / T))
    nd = 4 * dsteps
    N = nx + 2 + nd
    Aa = np.zeros((N, N)); Ba = np.zeros((N, 4))
    # applied input u_app = last element of the delay line (or v directly if no delay)
    if dsteps == 0:
        Bu_x = Bd @ Tdec; Bu_d = Dav @ Tdec
        Aa[:nx, :nx] = Ad; Ba[:nx] = Bu_x
        Aa[nx:nx + 2, :nx] = Cav; Ba[nx:nx + 2] = Bu_d
    else:
        Aa[:nx, :nx] = Ad
        last = slice(nx + 2 + 4 * (dsteps - 1), nx + 2 + 4 * dsteps)
        Aa[:nx, last] = Bd
        Aa[nx:nx + 2, :nx] = Cav; Aa[nx:nx + 2, last] = Dav
        # delay line: first block <- Tdec v ; block j <- block j-1
        Ba[nx + 2:nx + 6] = Tdec
        for j in range(1, dsteps):
            Aa[nx + 2 + 4 * j:nx + 6 + 4 * j, nx + 2 + 4 * (j - 1):nx + 6 + 4 * (j - 1)] = np.eye(4)
    Ca = np.zeros((4, N))
    Ca[0, :nx] = Cclr
    Ca[1, nx] = 1.0; Ca[2, nx + 1] = 1.0
    Ca[3, :nx] = CnP
    Da = np.zeros((4, 4))
    G = ct.ss(Aa, Ba, Ca, Da, T)
    # controller (negative feedback v = -K y): heave P, attitude F^n * PI, twist P
    a = T / gains.tau_f
    zf = ct.tf([a, 0.0], [1.0, -(1.0 - a)], T)
    F = ct.tf([1.0], [1.0], T)
    for _ in range(gains.n_stages):
        F = F * zf
    PI = ct.tf([gains.Kp + gains.Ki * T, -gains.Kp], [1.0, -1.0], T)    # Kp + Ki T z/(z-1)
    Katt = ct.minreal(F * PI, verbose=False) if gains.Ki > 0 else F * gains.Kp
    Kz = ct.tf([gains.Kz], [1.0], T)
    if gains.tau_z > 0:
        az_ = T / gains.tau_z
        Kz = Kz * ct.tf([az_, 0.0], [1.0, -(1.0 - az_)], T)
    Ktw = ct.tf([gains.Ktw / k_nom], [1.0], T)
    return {"G": G, "Katt": Katt, "Kz": Kz, "Ktw": Ktw, "F": F, "PI": PI, "Tdec": Tdec, "k_nom": k_nom,
            "dsteps": dsteps}


def loop_matrix(dl):
    """L = K_diag G (4x4 discrete ss, loop broken at the decoupled controller output v, negative feedback)."""
    import control as ct
    Kd = ct.append(ct.ss(dl["Kz"]), ct.ss(dl["Katt"]), ct.ss(dl["Katt"]), ct.ss(dl["Ktw"]))
    return Kd * dl["G"], Kd
