"""Reduced 5-DoF rocking model (own code, numba) shared by g04 / g06 of the G' window-shift note.

Not a copy of the project harness (no seal friction, no rod-side law, no controller in the loop, no yaw,
no crawler). Used ONLY for differences between floor-drop shapes at the same key.

Coordinates (body = superstructure, small angles, right-handed, x forward, y left, z up):
  u, v  horizontal CoM displacement [m]; w heave [m]; phi roll about +x; theta pitch about +y
  (theta > 0 = nose down, as the project convention). Pads at body xy (x_i, y_i) relative to the CoM and
  height -h below the CoM (h = CoM height above the pad bottom plane).
  pad vertical displacement  z_i = w + y_i phi - x_i theta
  pad horizontal displacement p_xi = u - h theta, p_yi = v + h phi
Mass / CoM / inertia: YAML superstructure.auger_levels.bottom (Ixx, Iyy, Ixy about the CoM; yaw dropped).
Legs: unilateral axial spring k_lock x kf (YAML contact.rigid_floor.L1.derivation.k_lock_N_m) with dashpot
  (C_LOCK, or C_MOVE on a leg whose prescribed valve rate is non-zero, as r51 DAMP_SWITCH) x cf;
  compression delta_i = F0_i / k_i - z_i + g_i(t) + e_i(t), F_i = max(0, k delta + c d(delta)/dt) if delta > 0.
  Preload F0 = YAML bottom static_leg_loads. Event-pad floor g(t) = -depth Poly345(t / ramp).
  e_i(t) = prescribed leg extension = integral of the stored valve output of the same key (1 ms grid).
Pad tangential: spring kt_per_pad (YAML L1, already in series with the swivel) + dashpot ct_per_pad to an
  anchor set at touch-down; circular Coulomb cap mu F_i by moving the anchor after each step (return
  mapping, as the L1 bushing); anchor follows the pad while airborne.
Moments about the CoM include the lever-arm change of the vertical forces (P-delta, x_i - h theta,
  y_i + h phi).
Integrator: classical RK4 with fixed dt; anchors updated between steps.
"""
import numpy as np
from numba import njit

M = 38400.8366
COM = np.array([0.460190503, -0.00136232581])
I2 = np.array([[176282.442, -941.461576], [-941.461576, 331469.51]])
PAD = np.array([[2.29376465, 1.32376465], [2.29376465, -1.32376465], [-2.556, 1.1679], [-2.556, -1.2429]])
K_LOCK = np.array([33929017.0, 33929017.0, 26402111.0, 26402111.0])
C_LOCK = np.array([34403.519, 34403.519, 30348.4527, 30348.4527])
C_MOVE = np.array([100206.065477022, 100206.065477022, 86949.0144383396, 86949.0144383396])
KT = np.array([7152770.33, 7152770.33, 3707388.61, 3707388.61])
CT = np.array([15796.2635, 15796.2635, 11372.3779, 11372.3779])
F0 = np.array([118099.1, 116106.0, 72096.68, 70281.81])
REL = PAD - COM
X = REL[:, 0].copy()
Y = REL[:, 1].copy()
I2INV = np.linalg.inv(I2)
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
W_ROD = 1050.0
F_EXIT = 14414.6
H_DEFAULT = 1.88     # ASSUMPTION: CoM z (bottom 0.783 m, body frame) - pad bottom (ground -1.051 m - ~0.05 m clearance)


@njit(cache=False)
def _floor(t, depth, ramp):
    tau = t / ramp
    if tau <= 0.0:
        return 0.0, 0.0
    if tau >= 1.0:
        return -depth, 0.0
    s = 10 * tau**3 - 15 * tau**4 + 6 * tau**5
    ds = (30 * tau**2 - 60 * tau**3 + 30 * tau**4) / ramp
    return -depth * s, -depth * ds


@njit(cache=False)
def _valve(t, ve, vv, vt0, vdt, use, i):
    if (not use) or t <= vt0:
        return 0.0, 0.0
    n = ve.shape[0]
    x = (t - vt0) / vdt
    j = int(x)
    if j >= n - 1:
        j = n - 2
    a = x - j
    return ve[j, i] * (1 - a) + ve[j + 1, i] * a, vv[j, i] * (1 - a) + vv[j + 1, i] * a


@njit(cache=False)
def _forces(t, s, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, ve, vv, vt0, vdt, use):
    u, v, w, ph, th = s[0], s[1], s[2], s[3], s[4]
    ud, vd, wd, phd, thd = s[5], s[6], s[7], s[8], s[9]
    Fz = np.zeros(4)
    Fx = np.zeros(4)
    Fy = np.zeros(4)
    dl_out = np.zeros(4)
    g, gd = _floor(t, depth, ramp)
    px = u - h * th
    py = v + h * ph
    pxd = ud - h * thd
    pyd = vd + h * phd
    for i in range(4):
        z = w + Y[i] * ph - X[i] * th
        zd = wd + Y[i] * phd - X[i] * thd
        e, ed = _valve(t, ve, vv, vt0, vdt, use, i)
        gi = g if i == leg else 0.0
        gdi = gd if i == leg else 0.0
        dl = d0[i] - z + gi + e
        dld = -zd + gdi + ed
        c = cm[i] if abs(ed) > 1e-6 else cl[i]
        dl_out[i] = dl
        if dl > 0:
            f = k[i] * dl + c * dld
            if f > 0:
                Fz[i] = f
                fx = -kt[i] * (px - anc[i, 0]) - ct[i] * pxd
                fy = -kt[i] * (py - anc[i, 1]) - ct[i] * pyd
                fm = np.sqrt(fx * fx + fy * fy)
                cap = mu * f
                if fm > cap and fm > 0:
                    fx *= cap / fm
                    fy *= cap / fm
                Fx[i] = fx
                Fy[i] = fy
    return Fz, Fx, Fy, dl_out


@njit(cache=False)
def _rhs(t, s, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, I2INV, M, ve, vv, vt0, vdt, use):
    Fz, Fx, Fy, _ = _forces(t, s, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, ve, vv, vt0, vdt, use)
    ph, th = s[3], s[4]
    out = np.empty(10)
    for j in range(5):
        out[j] = s[5 + j]
    out[5] = Fx.sum() / M
    out[6] = Fy.sum() / M
    out[7] = (Fz.sum() - M * 9.81) / M
    tx = 0.0
    ty = 0.0
    for i in range(4):
        tx += (Y[i] + h * ph) * Fz[i] + h * Fy[i]
        ty += -(X[i] - h * th) * Fz[i] - h * Fx[i]
    out[8] = I2INV[0, 0] * tx + I2INV[0, 1] * ty
    out[9] = I2INV[1, 0] * tx + I2INV[1, 1] * ty
    return out


@njit(cache=False)
def _sim(leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, I2INV, M, ve, vv, vt0, vdt, use, t_end, dt, rec_every):
    ns = int(round(t_end / dt))
    nr = ns // rec_every + 1
    rt = np.empty(nr)
    rF = np.empty((nr, 4))
    rg = np.empty((nr, 4))
    s = np.zeros(10)
    anc = np.zeros((4, 2))
    t = 0.0
    r = 0
    for n in range(ns + 1):
        Fz, Fx, Fy, dl = _forces(t, s, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, ve, vv, vt0, vdt, use)
        if n % rec_every == 0 and r < nr:
            rt[r] = t
            for i in range(4):
                rF[r, i] = Fz[i]
                rg[r, i] = -dl[i] if dl[i] < 0 else 0.0
            r += 1
        # anchor update (return mapping) at the start of the step
        px = s[0] - h * s[4]
        py = s[1] + h * s[3]
        for i in range(4):
            if Fz[i] <= 0:
                anc[i, 0] = px
                anc[i, 1] = py
            else:
                ex = px - anc[i, 0]
                ey = py - anc[i, 1]
                em = np.sqrt(ex * ex + ey * ey)
                lim = mu * Fz[i] / kt[i]
                if em > lim and em > 0:
                    anc[i, 0] = px - ex * lim / em
                    anc[i, 1] = py - ey * lim / em
        if n == ns:
            break
        k1 = _rhs(t, s, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, I2INV, M, ve, vv, vt0, vdt, use)
        k2 = _rhs(t + dt / 2, s + dt / 2 * k1, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, I2INV, M, ve, vv, vt0, vdt, use)
        k3 = _rhs(t + dt / 2, s + dt / 2 * k2, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, I2INV, M, ve, vv, vt0, vdt, use)
        k4 = _rhs(t + dt, s + dt * k3, anc, leg, depth, ramp, k, d0, cl, cm, kt, ct, mu, h, X, Y, I2INV, M, ve, vv, vt0, vdt, use)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        t += dt
    return rt[:r], rF[:r], rg[:r]


def valve_arrays(t, v):
    """Uniform-grid extension e and rate v from the stored 1 ms valve output (t from the event)."""
    m = t >= -1e-9
    t, v = t[m], v[m]
    vdt = float(np.median(np.diff(t)))
    e = np.zeros_like(v)
    e[1:] = np.cumsum(0.5 * (v[1:] + v[:-1]) * vdt, axis=0)
    return np.ascontiguousarray(e), np.ascontiguousarray(v), float(t[0]), vdt


def simulate(leg, depth, ramp, kf=1.0, cf=1.0, valve=None, t_end=1.0, dt=5e-5, rec_dt=1e-3, mu=0.5, h=H_DEFAULT,
             ktf=1.0, i2=None):
    """i2: optional 2x2 roll/pitch inertia about the CoM (default YAML bottom); used only by the g08 check."""
    i2inv = I2INV if i2 is None else np.linalg.inv(np.asarray(i2, float))
    k = K_LOCK * kf
    d0 = F0 / k
    if valve is None:
        ve = np.zeros((4, 4))
        vv = np.zeros((4, 4))
        vt0, vdt, use = 0.0, 1.0, False
    else:
        ve, vv, vt0, vdt = valve
        use = True
    return _sim(leg, depth, ramp, k, d0, C_LOCK * cf, C_MOVE * cf, KT * ktf, CT * cf, mu, h, X, Y, i2inv, M,
                ve, vv, vt0, vdt, use, t_end, dt, max(int(round(rec_dt / dt)), 1))


def load_valve(rerun, stem):
    z = np.load(rerun / "logs" / f"{stem}_rows.npz")
    rows, t_ev = z["rows"], float(z["t_ev"])
    t = rows[:, 0] - t_ev
    w = (t >= -1e-9) & (t <= 1.2)
    return valve_arrays(t[w], rows[w, 9:13]), t, rows


def window_features(t, F, gap, leg, fs_kN=None, w_rod=W_ROD):
    """Event-leg window: lift, re-contact, re-lift, F peak; controller-effective edges if fs_kN given."""
    Fe = F[:, leg] - w_rod
    air = F[:, leg] <= 0
    il = np.flatnonzero((t >= 0) & air)
    if not il.size:
        return None
    il = il[0]
    ib = np.flatnonzero((t > t[il]) & ~air)
    if not ib.size:
        return None
    ib = ib[0]
    irl = np.flatnonzero((t > t[ib]) & air)
    irl = irl[0] if irl.size else len(t) - 1
    seg = slice(ib, irl)
    out = {"t_lift": t[il], "t_contact": t[ib], "t_relift": t[irl], "relift_found": float(irl < len(t) - 1),
           "F_peak_kN": Fe[seg].max() / 1e3, "t_peak": t[ib + int(np.argmax(Fe[seg]))],
           "gap_max_mm": gap[il:ib, leg].max() * 1e3 if ib > il else np.nan}
    k0 = max(ib - 6, il)
    out["v_imp"] = (gap[k0, leg] - gap[ib - 1, leg]) / max(t[ib - 1] - t[k0], 1e-9)
    ir = np.flatnonzero(Fe[seg] >= F_EXIT)
    out["t_reload"] = t[ib + ir[0]] if ir.size else np.nan
    out["t_hold"] = t[ib + ir[-1]] if ir.size else np.nan
    if fs_kN is not None:
        thr_r = (F_EXIT / 1e3 + 6.1 + 2.4 * fs_kN) * 1e3
        thr_h = (F_EXIT / 1e3 - 6.6 + 0.5 * fs_kN) * 1e3
        a = np.flatnonzero(Fe[seg] >= thr_r)
        b = np.flatnonzero(Fe[seg] >= thr_h)
        out["t_r_star"] = t[ib + a[0]] if a.size else np.nan
        out["t_h_star"] = t[ib + b[-1]] if b.size else np.nan
    dg = DIAG[leg]
    airD = F[:, dg] <= 0
    a = np.flatnonzero((t > 0) & airD)
    out["d_lift"] = t[a[0]] if a.size else np.nan
    if a.size:
        b = np.flatnonzero((t > t[a[0]]) & ~airD)
        out["d_land"] = t[b[0]] if b.size else np.nan
    else:
        out["d_land"] = np.nan
    return {kk: float(v) for kk, v in out.items()}
