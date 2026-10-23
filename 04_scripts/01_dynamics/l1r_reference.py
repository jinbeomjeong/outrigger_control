"""L1-R reference block: rod-side chamber as a one-sided parallel spring on locked legs.

00_docs/01_dynamics/dynamics_model.md rev. 32, section 5.14 (definition 5.12.4 / 5.12.8, hydraulics
00_docs/02_hydraulic/rod_side_pressure.md 14). Called by run_reference.py only with an option:

    run_reference.py --l1r-out <path>   writes this block alone to <path> (reference.json untouched)
    run_reference.py --with-l1r         runs main() and adds the block to reference.json under L1R_KEY

Model (form (i), per leg, pad normal along +z at the ball centre; compression delta > 0):
* moving leg (EXT / RET): N = k2 delta (head-only pad stiffness k2 = k_h (+) k_out, the L1 SMC k_n);
* locked leg, anchor (delta_lock, N_lock) taken when the leg stops:
  N = N_lock + k1 (delta - delta_lock)                         below the knee,
  N = N_lock + dF_knee + k2 (delta - delta_lock - dF_knee / k1)  above (rod side on its floor),
  k1 = (k_h + k_r) (+) k_out, dF_knee = (p_r0 - p_floor_gauge) A_ann / r, r = k_r / (k_h + k_r);
* one pad dashpot c_n (LOCK basis, YAML cn_per_pad_N_s_m) in every state, tangential bushing k_t, c_t (stick).

The 6-DoF replica (V5 step, V7b) is the rev. 13 ball-centre L1 model (dynamics_model.md 5.4, run_reference
_l1_matrices: linear kinematics, preload geometric term) plus the piecewise normal law above as a generalised
force; it is integrated with DOP853 (rtol 1e-11). No P-delta, no rod inertia (rods rigid with the body at e_op),
no bushing yield, no lift-off (flagged if reached). Units SI, body frame x forward, y left, z up, level body =
world axes, gravity -z (YAML meta.gravity_m_s2), angles rad (deg only in *_deg keys), leg order FL FR RL RR.
Deterministic (no random numbers).
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import dyn_model as dm
import numpy as np
import run_reference as rr
from scipy.integrate import solve_ivp

L1R_KEY = "L1R_rod_side_reference_rev32"
P_ATM_PA = 1.01325e5            # = outrigger_sim.hydraulics.rod_chamber.ATMOSPHERE_PA (floor is absolute)
V7A_LIMIT = 0.5                 # dynamics_model.md 5.12.5: per-leg elastic contact-force amplitude <= 0.5 dF_knee
V7A_DESIGN = 0.4                # ASSUMPTION (rev. 32): design value of the linear predicted peak, 20 % below the limit
V7B_DESIGN = 3.0                # ASSUMPTION (rev. 32): linear predicted peak / knee of the V7b kicks (6 x the V7a limit;
                                # 1.5 changed the replica peak force by only 4-8 %, 3.0 gives 6-13 % (clear signature))
DT_RUN = 2.0e-4                 # YAML simulation.L1.dt_s (checked)
DT_REF = 1.0e-5                 # reference-solution dt (dynamics_model.md 4.3)
RTOL, ATOL_Q, ATOL_V = 1e-11, 1e-14, 1e-12
SAMPLE_S = 5.0e-4               # output grid of the replica series

# S4 excitations (03_src/outrigger_sim/verify/s4.py EXCITATIONS, copied: name, kind, axis, S4 amplitude
# [deg | m], 0-based target mode whose reference frequency sets the speed, window [s])
EXCITATIONS = (
    ("roll", "rotation", (1.0, 0.0, 0.0), 0.02, 0, 20.0),
    ("pitch", "rotation", (0.0, 1.0, 0.0), 0.02, 1, 20.0),
    ("yaw", "rotation", (0.0, 0.0, 1.0), 0.01, 2, 2.0),
    ("surge", "translation", (1.0, 0.0, 0.0), 0.5e-3, 3, 2.0),
    ("heave", "translation", (0.0, 0.0, 1.0), 0.5e-3, 4, 2.0),
    ("sway", "translation", (0.0, 1.0, 0.0), 0.25e-3, 5, 2.0),
)
LONG_WINDOW_MODES = (0, 1)      # S4: modes 1-2 judged only in >= 20 s windows
V7B_CASES = (("heave", 2.0), ("roll", 10.0), ("pitch", 10.0))   # top level, window [s]
V9_HOLD_S, V9_END_S = 0.5, 12.0  # run_S3 V9_STEP_HOLD_S / V9_STEP_END_S
V5_STEPS_MM = (0.3, 1.0, 5.0)


r = rr.r


def _no_move(t):
    return np.zeros(4), np.zeros(4)


def _floor2(x):
    """Round down to 2 significant digits."""
    e = math.floor(math.log10(abs(x)))
    return float(f"{math.floor(x / 10 ** (e - 1) + 1e-9) * 10 ** (e - 1):.2g}")


# ------------------------------------------------------------------ parameters
def leg_parameters(p, geo):
    """Per-leg L1-R parameters from the YAML, recomputed and checked against the YAML derived keys."""
    A_ = dm.ASSUMPTIONS
    act, rs = p["actuator"], p["actuator"]["rod_side"]
    L1 = p["contact"]["rigid_floor"]["L1"]
    d = L1["derivation"]
    leg = lambda tbl: np.array([float(tbl[n]) for n in dm.LEG_NAMES])  # noqa: E731
    e_op = geo.touch_extension + A_["crawler_clearance_m"]
    beta = float(act["oil_bulk_modulus_eff_Pa"])
    L0h, L0r = float(act["oil_dead_length_m"]), float(act["rod_dead_length_m"])
    A_p = np.broadcast_to(dm.piston_area(), (4,)).astype(float)
    A_ann = np.broadcast_to(dm.annulus_area(), (4,)).astype(float)
    k_h = beta * A_p / (L0h + e_op)
    L_r = geo.stroke - e_op + L0r
    k_r = beta * A_ann / L_r
    kc = dm.k_concrete_westergaard()["k_slab_N_m"]
    k_out = dm.series(dm.k_rod(), A_["frame_bracket_stiffness_N_m"], kc)
    k2 = dm.series(k_h, k_out)
    k1 = dm.series(k_h + k_r, k_out)
    ratio_r = k_r / (k_h + k_r)
    p_floor_g = float(rs["p_floor_Pa"]) - P_ATM_PA
    p_ext, p_ret = leg(rs["p_r0_after_extend_Pa"]), leg(rs["p_r0_after_retract_Pa"])
    knee_ext = (p_ext - p_floor_g) * A_ann / ratio_r
    knee_ret = (p_ret - p_floor_g) * A_ann / ratio_r
    # Chrono: the SMC material holds k_n as float32; the module re-solves k_out from it (rod_chamber_link)
    k2_f32 = np.array([float(np.float32(x)) for x in leg(L1["kn_per_pad_N_m"])])
    k1_f32 = dm.series(k_h + k_r, 1.0 / (1.0 / k2_f32 - 1.0 / k_h))
    checks = {
        "e_op vs YAML derivation.operating_extension_m (4 digits)": float(np.abs(e_op - leg(d["operating_extension_m"])).max()),
        "k_h vs YAML derivation.k_oil_N_m (rel)": float(np.abs(k_h / leg(d["k_oil_N_m"]) - 1).max()),
        "k_h vs dyn_model.k_oil(e_op) (rel)": float(np.abs(k_h / dm.k_oil(e_op) - 1).max()),
        "k_r vs YAML actuator.rod_side.k_rod_side_N_m (rel)": float(np.abs(k_r / leg(rs["k_rod_side_N_m"]) - 1).max()),
        "L_r vs YAML actuator.rod_side.column_length_m (4 digits)": float(np.abs(L_r - leg(rs["column_length_m"])).max()),
        "k2 vs YAML kn_per_pad_N_m (rel)": float(np.abs(k2 / leg(L1["kn_per_pad_N_m"]) - 1).max()),
        "k1 vs YAML derivation.k_lock_N_m (rel)": float(np.abs(k1 / leg(d["k_lock_N_m"]) - 1).max()),
        "k1 from float32 k_n vs k1 (rel, Chrono / module)": float(np.abs(k1_f32 / k1 - 1).max()),
    }
    lim = {"e_op": 5e-5, "k_h vs YAML": 1e-8, "k_h vs dyn": 1e-12, "k_r": 1e-8, "L_r": 5e-5, "k2": 1e-8, "k1 vs": 1e-8,
           "k1 from": 1e-6}
    for key, v in checks.items():
        tol = next(t for kk, t in lim.items() if key.startswith(kk))
        if not v <= tol:
            raise RuntimeError(f"L1-R parameter check failed: {key} = {v:.3e} > {tol:.1e}")
    if float(p["simulation"]["L1"]["dt_s"]) != DT_RUN:
        raise RuntimeError("YAML simulation.L1.dt_s differs from DT_RUN")
    return dict(e_op=e_op, beta=beta, L0h=L0h, L0r=L0r, L_r=L_r, A_p=A_p, A_ann=A_ann, k_h=k_h, k_r=k_r, k_out=k_out,
                k1=k1, k2=k2, r=ratio_r, p_floor_g=p_floor_g, p_r0_ext=p_ext, p_r0_ret=p_ret,
                knee_ext=knee_ext, knee_ret=knee_ret, k2_f32=k2_f32, k1_f32=k1_f32,
                cn=leg(L1["cn_per_pad_N_s_m"]), ct=leg(L1["ct_per_pad_N_s_m"]),
                cn_head=leg(L1["cn_per_pad_head_only_N_s_m"]), kt=leg(L1["kt_per_pad_N_m"]),
                mu=float(p["contact"]["rigid_floor"]["friction"]), checks=checks)


# ------------------------------------------------------------------ 6-DoF model per level
class Level:
    """L1 6-DoF about the CoM of superstructure + rods at e_op (rev. 13 ball-centre springs)."""

    def __init__(self, p, geo, lp, lvl):
        g, xy = geo.g, geo.pad_xy
        self.name = lvl
        self.xy = xy
        self.bw = dm.body_with_rods(p, geo, lvl, lp["e_op"])
        b = dm.body_from_params(p, lvl)
        F_cyl, q_st, _ = dm.static_loads(lp["k2"], xy, self.bw.mass * g, self.bw.com[:2])
        self.F_cyl = F_cyl - geo.rod_mass * g          # cylinder (net) force, superstructure share
        self.F0 = F_cyl                                  # contact force incl. rod weight (static_loads on bw)
        self.q_static = q_st
        self.F_min = float(p["control"]["F_min_cylinder_N"])
        self.F_min_rule = dm.ASSUMPTIONS["F_min_fraction_of_mean_leg_load"] * b.mass * g / 4
        self.rodw = geo.rod_mass * g
        hb = rr._ball_heights(p)
        self.z_ball = geo.pad_z_retracted - lp["e_op"] + hb
        self.M = dm.mass_6dof(self.bw)
        self.az = np.zeros((4, 6)); self.ax = np.zeros((4, 6)); self.ay = np.zeros((4, 6))
        for i in range(4):
            ax, ay, az = dm.a_vec(np.array([xy[i, 0], xy[i, 1], self.z_ball[i]]) - self.bw.com)
            self.ax[i], self.ay[i], self.az[i] = ax, ay, az
        self.lp = lp
        self.mats = {}
        for name, kv in (("LOCK", lp["k1"]), ("FLOOR", lp["k2"])):
            K, Cn, Ct, Kb = rr._l1_matrices(self.bw, xy, self.z_ball, self.z_ball, kv, lp["kt"], lp["cn"], lp["ct"], self.F0)
            w2, f_und, Phi, cls, orth = dm.modal(self.M, K, dm.DOF6)
            fd, zd = dm.complex_modes(self.M, K, Cn + Ct)
            share = np.array([Phi[:, j] @ Kb @ Phi[:, j] / w2[j] for j in range(6)])
            Ph = Phi[:, :6].copy()
            for jm in range(6):
                imax = int(np.argmax(np.abs(Ph[:6, jm])))
                if Ph[imax, jm] < 0:
                    Ph[:, jm] *= -1.0
            self.mats[name] = dict(K=K, C=Cn + Ct, Kb=Kb, w2=w2, f=f_und, Phi=Ph, cls=cls, orth=orth, fd=fd, zd=zd,
                                   share=share)

    def zeta_num(self, state, dt):
        m = self.mats[state]
        return m["share"] * np.sqrt(m["w2"]) * dt / 2

    def c_num(self, state, dt):
        """Modal damping matrix of the numerical damping r omega dt / 2 (semi-implicit bushing share)."""
        m = self.mats[state]
        zn = self.zeta_num(state, dt)
        MP = self.M @ m["Phi"]
        return MP @ np.diag(2 * zn * np.sqrt(m["w2"])) @ MP.T

    def qdot0(self, exc, amp, f_target):
        _, kind, axis, _, _, _ = exc
        w = 2 * math.pi * f_target
        a = np.asarray(axis, float)
        return np.r_[np.zeros(3), a * math.radians(amp) * w] if kind == "rotation" else np.r_[a * amp * w, np.zeros(3)]

    def linear_response(self, state, qd0, t, extra_C=None):
        """Free response of the linear model (state LOCK or FLOOR) from q = 0, dq/dt = qd0, at times t."""
        m = self.mats[state]
        C = m["C"] if extra_C is None else m["C"] + extra_C
        Minv = np.linalg.inv(self.M)
        A = np.block([[np.zeros((6, 6)), np.eye(6)], [-Minv @ m["K"], -Minv @ C]])
        lam, V = np.linalg.eig(A)
        c = np.linalg.solve(V, np.r_[np.zeros(6), qd0])
        X = (V * c) @ np.exp(np.outer(lam, t))
        return X.real


# ------------------------------------------------------------------ replica with the piecewise law
class LegStates:
    """Per-leg L1-R state of the replica (dynamics_model.md 5.12.8 interface item 5).

    locked (4,) bool: LOCK / FLOOR (True) or moving EXT / RET (False).
    LOCK:   F_extra = F_res + dk min(dd - dd_lock, dF_knee / k1)  (F_res = release residual absorbed at the lock)
    moving: F_extra = F_x0 exp(-(t - t_rel) / tau_v)            (release decay of the value at the release)
    Initial state of every case: static equilibrium, all four legs LOCK after an extension, anchors at 0.
    """

    def __init__(self):
        self.locked = np.ones(4, bool)
        self.dd_lock = np.zeros(4)
        self.F_res = np.zeros(4)
        self.F_x0 = np.zeros(4)
        self.t_rel = np.zeros(4)

    def copy(self):
        s = LegStates()
        for k in ("locked", "dd_lock", "F_res", "F_x0", "t_rel"):
            setattr(s, k, getattr(self, k).copy())
        return s


class Replica:
    """6-DoF L1 model with the L1-R normal law (module docstring). State x = [q, dq/dt] about the static state.

    e_fun(t) -> (e, de/dt): commanded extension change of every leg (pushes the pad down = more compression).
    """

    def __init__(self, lv, knee, extra_C=None, tau_v=None, zero_damping=False):
        self.lv, self.lp = lv, lv.lp
        self.K = lv.mats["FLOOR"]["K"]                   # k2 springs + bushing + geometric term
        self.C = lv.mats["FLOOR"]["C"] if extra_C is None else lv.mats["FLOOR"]["C"] + extra_C
        self.cn = self.lp["cn"]
        if zero_damping:
            self.C, self.cn = np.zeros((6, 6)), np.zeros(4)
        self.Minv = np.linalg.inv(lv.M)
        self.knee = np.asarray(knee, float)
        self.ddk = self.knee / self.lp["k1"]
        self.dk = self.lp["k1"] - self.lp["k2"]
        self.tau = tau_v
        self.lift_flag = False

    def dd(self, q, e):
        return -self.lv.az @ q + e

    def extra(self, t, dd, st):
        lockF = st.F_res + self.dk * np.minimum(dd - st.dd_lock, self.ddk)
        if self.tau is None:
            moveF = np.zeros(4)
        else:
            moveF = st.F_x0 * np.exp(-np.maximum(t - st.t_rel, 0.0) / self.tau)
        return np.where(st.locked, lockF, moveF)

    def normal(self, t, q, e, st):
        """Elastic pad normal force N (machine output, no dashpot) [N]."""
        dd = self.dd(q, e)
        return self.lv.F0 + self.lp["k2"] * dd + self.extra(t, dd, st)

    def run(self, x0, t_span, e_fun, st, t_eval):
        az = self.lv.az

        def rhs(t, x):
            q, v = x[:6], x[6:]
            e, ed = e_fun(t)
            dd = -az @ q + e
            Fx = self.extra(t, dd, st)
            if (self.lv.F0 + self.lp["k2"] * dd + Fx <= 0).any():
                self.lift_flag = True
            gen = az.T @ (self.lp["k2"] * e + self.cn * ed + Fx)
            return np.r_[v, self.Minv @ (gen - self.K @ q - self.C @ v)]

        def ev(i):
            def f(t, x):
                e, _ = e_fun(t)
                return (-az[i] @ x[:6] + e[i]) - st.dd_lock[i] - self.ddk[i]
            return f
        atol = np.r_[np.full(6, ATOL_Q), np.full(6, ATOL_V)]
        sol = solve_ivp(rhs, t_span, x0, method="DOP853", rtol=RTOL, atol=atol, t_eval=t_eval,
                        events=[ev(i) for i in range(4)])
        if not sol.success:
            raise RuntimeError(sol.message)
        crossings = [(float(te), i) for i in range(4) for te in sol.t_events[i] if st.locked[i]]
        return sol, sorted(crossings)

    def energy_undamped(self, x, e, st):
        """Mechanical energy of the undamped model (e constant, all legs locked, F_res = 0)."""
        q, v = x[:6], x[6:]
        rel = self.dd(q, e) - st.dd_lock
        kn = self.ddk
        U_R = np.where(rel <= kn, 0.5 * self.dk * rel ** 2, 0.5 * self.dk * kn ** 2 + self.dk * kn * (rel - kn))
        # linear part: 0.5 q K q is the potential of K (symmetric); the constant e-load az^T k2 e adds -(az^T k2 e) q
        U_e = -(self.lv.az.T @ (self.lp["k2"] * e)) @ q
        return 0.5 * v @ self.lv.M @ v + 0.5 * q @ self.K @ q + U_e + np.where(st.locked, U_R, 0.0).sum()


class Moves:
    """Commanded leg moves (t_start, leg, distance [m], speed [m/s]) with the acceleration limit a: trapezoidal
    (triangular when the cruise speed is not reached) speed profile that stops exactly on the target - the continuous
    form of the L1SpeedActuator ramp start and braking cap (03_src/outrigger_sim/chrono/actuators.py)."""

    def __init__(self, moves, a):
        self.moves = []
        for t0, leg, d, v in moves:
            s = math.copysign(1.0, d); d = abs(d)
            vp = min(v, math.sqrt(a * d))
            ta = vp / a
            tc = (d - vp * ta) / vp
            self.moves.append((t0, leg, s, d, vp, ta, tc, t0 + 2 * ta + tc))
        self.a = a

    def breakpoints(self):
        bp = set()
        for t0, _, _, _, _, ta, tc, t1 in self.moves:
            bp |= {t0, t0 + ta, t0 + ta + tc, t1}
        return sorted(bp)

    def __call__(self, t):
        e = np.zeros(4); ed = np.zeros(4)
        a = self.a
        for t0, leg, s, d, vp, ta, tc, t1 in self.moves:
            if t <= t0:
                continue
            if t >= t1:
                e[leg] += s * d
                continue
            u = t - t0
            if u <= ta:
                x, v = 0.5 * a * u * u, a * u
            elif u <= ta + tc:
                x, v = 0.5 * vp * ta + vp * (u - ta), vp
            else:
                w = t1 - t
                x, v = d - 0.5 * a * w * w, a * w
            e[leg] += s * x; ed[leg] += s * v
        return e, ed

    def moving(self, t_mid):
        m = np.zeros(4, bool)
        for t0, leg, *_rest, t1 in self.moves:
            if t0 <= t_mid < t1:
                m[leg] = True
        return m


def simulate_moves(lv, moves: Moves, t_end, tau_v, extra_C=None, sample=SAMPLE_S):
    """Replica run from the static state with all legs LOCK; legs release at a move start (F_x0 = their F_extra
    then) and lock at the move end (anchor = state then, F_res = F_extra then). Returns t, q, N, states, crossings."""
    rep = Replica(lv, lv.lp["knee_ext"], extra_C, tau_v)
    st = LegStates()
    x = np.zeros(12)
    bps = [b for b in moves.breakpoints() if 0.0 < b < t_end] + [t_end]
    t_prev = 0.0
    ts, qs, Ns, cr_all, log = [], [], [], [], []
    for b in bps:
        if b <= t_prev:
            continue
        mv = moves.moving(0.5 * (t_prev + b))
        e_now, _ = moves(t_prev)
        dd_now = rep.dd(x[:6], e_now)
        F_now = rep.extra(t_prev, dd_now, st)
        for i in range(4):
            if st.locked[i] and mv[i]:          # release (lock -> move)
                st.locked[i] = False; st.F_x0[i] = F_now[i]; st.t_rel[i] = t_prev
                log.append((t_prev, dm.LEG_NAMES[i], "release", float(F_now[i])))
            elif not st.locked[i] and not mv[i]:  # lock at the stop
                st.locked[i] = True; st.dd_lock[i] = dd_now[i]; st.F_res[i] = F_now[i]
                log.append((t_prev, dm.LEG_NAMES[i], "lock", float(F_now[i])))
        tt = np.arange(t_prev, b, sample)
        tt = np.r_[tt, b] if tt[-1] < b else tt
        sol, cr = rep.run(x, (t_prev, b), moves, st, tt)
        x = sol.y[:, -1].copy()
        keep = slice(None, -1) if b < t_end else slice(None)
        ts.append(tt[keep]); qs.append(sol.y[:6, keep])
        Ns.append(np.array([rep.normal(tt[j], sol.y[:6, j], moves(tt[j])[0], st) for j in range(len(tt))]).T[:, keep])
        cr_all += cr
        t_prev = b
    return (np.concatenate(ts), np.concatenate(qs, axis=1), np.concatenate(Ns, axis=1), st, sorted(cr_all), log,
            rep.lift_flag)


def _peaks(t, y):
    """Local maxima of y (parabolic refinement): (t_peak, y_peak) arrays."""
    i = np.where((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:]))[0] + 1
    tp, yp = [], []
    for k in i:
        y0, y1, y2 = y[k - 1], y[k], y[k + 1]
        den = y0 - 2 * y1 + y2
        dx = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        h = t[k + 1] - t[k]
        tp.append(t[k] + dx * h)
        yp.append(y1 - 0.25 * (y0 - y2) * dx)
    return np.array(tp), np.array(yp)


def _up_crossings(t, y):
    i = np.where((y[:-1] < 0) & (y[1:] >= 0))[0]
    return t[i] - y[i] * (t[i + 1] - t[i]) / (y[i + 1] - y[i])


# ------------------------------------------------------------------ quasi-static piecewise solve
def quasi_static(lv, de, moving, knee):
    """Rigid-body vertical statics (support_matrix about the frame origin) with the L1-R law: moving legs k2,
    locked legs k1 up to the knee then k2; lift-off (contact force 0) removes the leg. Returns dF (4,), q (3,)."""
    lp = lv.lp
    A = dm.support_matrix(lv.xy)
    k1, k2 = lp["k1"], lp["k2"]

    def law(dd):
        F = np.zeros(4); K = np.zeros(4)
        for i in range(4):
            if moving[i]:
                F[i], K[i] = k2[i] * dd[i], k2[i]
            else:
                ddk = knee[i] / k1[i]
                if dd[i] <= ddk:
                    F[i], K[i] = k1[i] * dd[i], k1[i]
                else:
                    F[i], K[i] = knee[i] + k2[i] * (dd[i] - ddk), k2[i]
            if lv.F0[i] + F[i] < 0:
                F[i], K[i] = -lv.F0[i], 0.0
        return F, K
    q = np.zeros(3)
    for _ in range(60):
        F, K = law(de - A @ q)
        res = A.T @ F
        if np.max(np.abs(res)) < 1e-7:
            return F, q
        H = A.T @ np.diag(K) @ A
        if np.linalg.matrix_rank(H) < 3:      # two pads lifted: mechanism (only reached past the V6 lift point)
            return np.full(4, np.nan), np.full(3, np.nan)
        q = q + np.linalg.solve(H, res)
    raise RuntimeError("quasi-static L1-R solve did not converge")


# ------------------------------------------------------------------ block
def build_block(p=None, ref_res=None, npz_out: Path | None = None):
    t0 = time.perf_counter()
    p = dm.load_params() if p is None else p
    geo = dm.geometry_from_params(p)
    g = geo.g
    lp = leg_parameters(p, geo)
    lvls = {lvl: Level(p, geo, lp, lvl) for lvl in dm.LEVELS}
    out = {"meta": {
        "model": " ".join(" ".join(__doc__.split("\n\n")[3:5]).split()),
        "definition": "dynamics_model.md 5.12.4 / 5.12.8 (rev. 30), rev. 32 section 5.14; rod_side_pressure.md 14",
        "frame": "body x forward, y left, z up; level body = world axes; q about the CoM of superstructure + 4 rods at e_op",
        "gravity_m_s2": [0.0, 0.0, -g],
        "pressure_convention": "gauge Pa except p_floor (absolute in the YAML, gauge here = abs - 101325 Pa)",
        "lock_pressure_source": "RULE (p_r0 after an extension = YAML actuator.rod_side.p_r0_after_extend_Pa, 2 bar g), "
                                "dynamics_model.md 5.12.10",
        "assumptions": {"V7a_design_peak_over_knee": V7A_DESIGN, "V7a_limit_peak_over_knee": V7A_LIMIT,
                        "V7b_linear_peak_over_knee": V7B_DESIGN,
                        "replica": "no P-delta, rods rigid with the body, no bushing yield, continuous time (no hook lag)"},
        "integrator": f"scipy solve_ivp DOP853 rtol {RTOL:g}, atol q {ATOL_Q:g} m|rad, v {ATOL_V:g}; output grid {SAMPLE_S:g} s",
    }}
    # ---- stiffness table
    out["leg_parameters"] = {
        "e_op_m": r(lp["e_op"]), "column_length_rod_side_m": r(lp["L_r"]),
        "head_area_m2": r(lp["A_p"]), "annulus_area_m2": r(lp["A_ann"]),
        "k_head_N_m": r(lp["k_h"]), "k_rod_side_N_m": r(lp["k_r"]), "k_out_N_m (rod, frame, concrete)": r(lp["k_out"]),
        "r = k_r / (k_h + k_r)": r(lp["r"]),
        "k2_head_only_N_m (FLOOR, moving, = YAML kn_per_pad)": r(lp["k2"]),
        "k1_lock_N_m (= YAML derivation.k_lock_N_m)": r(lp["k1"]),
        "k1 / k2": r(lp["k1"] / lp["k2"], 5), "k_r / k_h": r(lp["k_r"] / lp["k_h"], 5),
        "dk = k1 - k2 N_m": r(lp["k1"] - lp["k2"]),
        "k2_float32_N_m (Chrono SMC material)": r(lp["k2_f32"], 9), "k1_from_float32_N_m (module)": r(lp["k1_f32"], 9),
        "p_floor_gauge_Pa": r(lp["p_floor_g"]),
        "p_r0_after_extend_Pa": r(lp["p_r0_ext"]), "p_r0_after_retract_Pa": r(lp["p_r0_ret"]),
        "knee_dF_after_extend_N": r(lp["knee_ext"]), "knee_dF_after_retract_N": r(lp["knee_ret"]),
        "knee_ddelta_after_extend_m": r(lp["knee_ext"] / lp["k1"]),
        "knee_per_bar_N (A_ann / r x 1e5)": r(lp["A_ann"] / lp["r"] * 1e5),
        "c_n_N_s_m (LOCK basis, every state)": r(lp["cn"]), "c_n_head_only_N_s_m (regression)": r(lp["cn_head"]),
        "c_t_N_s_m": r(lp["ct"]), "k_t_N_m": r(lp["kt"]),
        "checks (max deviation)": {k: r(v, 3) for k, v in lp["checks"].items()},
    }
    # ---- statics (V1-V3: the lock adds no force at the static state, values = head-only L1)
    st = {}
    for lvl, lv in lvls.items():
        Fc = lv.F0
        dlift = -Fc / lp["k1"]
        st[lvl] = {
            "contact_force_N": r(Fc), "cylinder_force_N": r(lv.F_cyl),
            "penetration_mm (contact / k2)": r(Fc / lp["k2"] * 1e3),
            "attitude_deg (roll, pitch)": r(np.degrees(lv.q_static[1:]), 4),
            "F_min_cylinder_N": r(lv.F_min_rule),
            "F_fl_cylinder_N after extend (knee)": r(lv.F_cyl + lp["knee_ext"]),
            "F_fl_cylinder_N after retract (knee)": r(lv.F_cyl + lp["knee_ret"]),
            "lift_deflection_from_lock_mm (-(F_cyl + m g) / k1)": r(dlift * 1e3, 5),
            "rod_pressure_at_lift_bar (after extend, linear)": r((lp["p_r0_ext"] + lp["r"] * Fc / lp["A_ann"]) / 1e5, 5),
        }
    out["statics_V1_V3"] = st
    if ref_res is not None:
        L1 = ref_res["chrono_test_references"]["L1_rigid_motor_lumped_contact"]
        for lvl in dm.LEVELS:
            refl = L1["levels"][lvl]
            if r(lvls[lvl].F0) != refl["contact_force_N"] or r(lvls[lvl].F_cyl) != refl["cylinder_force_N"]:
                raise RuntimeError(f"{lvl}: statics differ from reference.json L1 block")
            vb = refl["V7_ball_centre_bushing_rev13"]
            m = lvls[lvl].mats["FLOOR"]
            if r(m["fd"], 5) != vb["f_damped_Hz"] or r(m["zd"], 3) != vb["zeta"]:
                raise RuntimeError(f"{lvl}: FLOOR modes do not reproduce reference.json V7_ball_centre_bushing_rev13")
        if r(lp["cn"]) != L1["c_pad_N_s_m"] or r(lp["ct"]) != L1["c_tan_N_s_m"]:
            raise RuntimeError("dashpots differ from reference.json")
        out["meta"]["cross_check_reference_json"] = ("statics, c_n, c_t and the FLOOR (head-only) ball-centre modes "
                                                    "reproduce reference.json L1 / V7_ball_centre_bushing_rev13 (printed digits)")
    # ---- modes (V7a reference LOCK, FLOOR for the report), V8(a) numbers
    modes = {}
    for lvl, lv in lvls.items():
        ent = {}
        for state in ("LOCK", "FLOOR"):
            m = lv.mats[state]
            ent[state] = {
                "f_undamped_Hz": r(m["f"], 5), "f_damped_Hz (|lambda| / 2 pi)": r(m["fd"], 5),
                "zeta": r(m["zd"], 4), "mode_content": m["cls"], "orthogonality_err": r(m["orth"], 3),
                "implicit_strain_energy_share r (bushing)": r(m["share"], 4),
                "zeta_num_r_omega_dt_half": {f"{dt:g}": r(lv.zeta_num(state, dt), 3) for dt in (1e-4, 2e-4)},
                "zeta_num_over_zeta (2e-4)": r(lv.zeta_num(state, 2e-4) / m["zd"], 3),
                "V8a_limit_0.1_zeta": r(0.1 * m["zd"], 3),
            }
        m = lv.mats["LOCK"]
        ent["LOCK"]["mode_shapes"] = {
            "coordinates": list(dm.DOF6),
            "reference_point_m (rotations about it, translations of it; body axes, level body = world)": r(lv.bw.com),
            "units": "translations m, rotations rad (small angles), per sqrt(kg)",
            "Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)": r(m["Phi"], 12),
            "mass_matrix (same coordinates)": r(lv.M, 12),
            "projection": "eta = Phi^T M q; sign: largest body component of each column positive",
        }
        ent["LOCK_over_FLOOR_f"] = r(lv.mats["LOCK"]["fd"] / lv.mats["FLOOR"]["fd"], 4)
        modes[lvl] = ent
    out["modes_V7a"] = modes
    # ---- V7a cases
    t_long = np.arange(0.0, 20.0 + 1e-12, SAMPLE_S)
    v7a = {}
    for lvl, lv in lvls.items():
        m = lv.mats["LOCK"]
        knee = lp["knee_ext"]
        runs, amps_pred = {}, {}
        for exc in EXCITATIONS:
            name, kind, axis, a_s4, tgt, win = exc
            f_t = float(m["fd"][tgt])
            t = t_long[t_long <= win + 1e-12]
            X = lv.linear_response("LOCK", lv.qdot0(exc, a_s4, f_t), t)
            dd = -lv.az @ X[:6]
            dN = lp["k1"][:, None] * dd
            ratio_s4 = float((dN.max(axis=1) / knee).max())
            a = a_s4 if ratio_s4 <= V7A_DESIGN else _floor2(a_s4 * V7A_DESIGN / ratio_s4)
            s = a / a_s4
            dN, X = dN * s, X * s
            dtot = dN + lp["cn"][:, None] * (-lv.az @ X[6:])
            tang = np.hypot(lv.ax @ X[:6], lv.ay @ X[:6]) * lp["kt"][:, None]
            qd0 = lv.qdot0(exc, a, f_t)
            pred = np.abs(m["Phi"].T @ lv.M @ qd0) / np.sqrt(m["w2"])
            amps_pred[name] = pred
            runs[name] = {
                "amplitude (deg rotation | m translation)": a, "S4_amplitude": a_s4, "scale_vs_S4": r(s, 4),
                "target_mode (0-based, sets the speed)": tgt, "f_target_Hz (LOCK f_damped)": r(f_t, 5),
                "initial_velocity_point_m_s (of the reference point)": r(qd0[:3], 6),
                "initial_angular_velocity_rad_s": r(qd0[3:], 6),
                "window_s": win,
                "predicted_peak_elastic_dN_N (k1 ddelta, max over t)": r(dN.max(axis=1), 4),
                "predicted_min_elastic_dN_N": r(dN.min(axis=1), 4),
                "predicted_peak_over_knee (max leg)": r(float((dN.max(axis=1) / knee).max()), 3),
                "predicted_peak_total_dN_N (with dashpot, information)": r(np.abs(dtot).max(axis=1), 4),
                "predicted_peak_bushing_force_over_muN": r(float((tang.max(axis=1) / (lp["mu"] * lv.F0)).max()), 3),
                "predicted_start_amplitude_eta (sqrt(kg) m)": r(pred, 4),
            }
        assign = {}
        for i in range(6):
            elig = [nm for nm, *_rest, win in EXCITATIONS if (i not in LONG_WINDOW_MODES or win >= 20.0)]
            ranked = sorted(elig, key=lambda nm: amps_pred[nm][i], reverse=True)
            assign[f"mode {i + 1}"] = {"run": ranked[0], "runner_up": ranked[1],
                                       "runner_up_ratio": r(amps_pred[ranked[1]][i] / amps_pred[ranked[0]][i], 3),
                                       "f_ref_Hz": r(float(m["fd"][i]), 5), "zeta_ref": r(float(m["zd"][i]), 4),
                                       "zeta_num_2e-4": r(float(lv.zeta_num("LOCK", 2e-4)[i]), 3)}
        v7a[lvl] = {"runs": runs, "judged_run_per_mode (S4 rule, largest predicted start amplitude)": assign}
    out["V7a_cases"] = v7a
    # replica check against the linear LOCK solution (small amplitude, no knee crossing)
    lv = lvls["top"]
    rep = Replica(lv, lp["knee_ext"])
    exc = EXCITATIONS[0]
    a = v7a["top"]["runs"]["roll"]["amplitude (deg rotation | m translation)"]
    qd0 = lv.qdot0(exc, a, float(lv.mats["LOCK"]["fd"][0]))
    tt = np.arange(0.0, 5.0 + 1e-12, SAMPLE_S)
    sol, cr = rep.run(np.r_[np.zeros(6), qd0], (0.0, 5.0), _no_move, LegStates(), tt)
    Xl = lv.linear_response("LOCK", qd0, tt)
    rep_err = float(np.abs(sol.y[:6] - Xl[:6]).max() / np.abs(Xl[:6]).max())
    out["meta"]["replica_vs_linear_LOCK (top roll V7a, 5 s, max rel)"] = r(rep_err, 3)
    if rep_err > 1e-7 or cr:
        raise RuntimeError(f"replica does not reproduce the linear LOCK response ({rep_err:.2e}, crossings {cr[:4]})")
    # ---- V7b (top): knee crossing free vibration
    series = {}
    v7b = {}
    for name, win in V7B_CASES:
        exc = next(e for e in EXCITATIONS if e[0] == name)
        m = lv.mats["LOCK"]
        tgt = exc[4]
        f_t = float(m["fd"][tgt])
        a7 = v7a["top"]["runs"][name]
        a_lin = a7["amplitude (deg rotation | m translation)"]
        a = _floor2(a_lin * V7B_DESIGN / a7["predicted_peak_over_knee (max leg)"])
        qd0 = lv.qdot0(exc, a, f_t)
        tt = np.arange(0.0, win + 1e-12, SAMPLE_S)
        pred = np.abs(m["Phi"].T @ lv.M @ qd0) / np.sqrt(m["w2"])
        jdom = int(np.argmax(pred))
        res_c = {}
        for variant, extra in (("physical (judge the 1e-5 s run)", None),
                               ("with_zeta_num_2e-4 (judge the 2e-4 s run)", lv.c_num("LOCK", DT_RUN))):
            rep = Replica(lv, lp["knee_ext"], extra)
            st = LegStates()
            sol, cr = rep.run(np.r_[np.zeros(6), qd0], (0.0, win), _no_move, st, tt)
            q = sol.y[:6]
            N = np.array([rep.normal(tt[k], q[:, k], np.zeros(4), st) for k in range(q.shape[1])]).T
            dN = N - lv.F0[:, None]
            eta = m["Phi"].T @ lv.M @ q
            tp, yp = _peaks(tt, eta[jdom])
            per = np.diff(_up_crossings(tt, eta[jdom]))
            above = (dN > lp["knee_ext"][:, None])
            res_c[variant] = {
                "dominant_LOCK_mode (1-based)": jdom + 1,
                "eta_peaks_first10 (t_s, sqrt(kg) m)": [[r(a_, 6), r(b_, 6)] for a_, b_ in zip(tp[:10], yp[:10], strict=True)],
                "periods_first10_s (eta up-crossings)": r(per[:10], 6),
                "mean_period_first10_s": r(float(per[:10].mean()), 6),
                "max_elastic_dN_N": r(dN.max(axis=1), 5), "min_elastic_dN_N": r(dN.min(axis=1), 5),
                "max_dN_over_knee": r(dN.max(axis=1) / lp["knee_ext"], 4),
                "FLOOR_dwell_s (dN > knee)": r(above.sum(axis=1) * SAMPLE_S, 4),
                "knee_crossings (t_s, leg)": [[r(tc, 6), dm.LEG_NAMES[i]] for tc, i in cr[:60]],
                "n_knee_crossings": len(cr), "last_knee_crossing_s": r(cr[-1][0], 6) if cr else None,
                "lift_off": bool(rep.lift_flag),
            }
            series[f"V7b_{name}_{variant.split(' ')[0]}"] = dict(t=tt, q=q, dN=dN, eta=eta)
        # linear LOCK without the knee, same kick (size of the nonlinear effect = what the test can discriminate)
        Xl = lv.linear_response("LOCK", qd0, tt)
        etal = m["Phi"].T @ lv.M @ Xl[:6]
        dNl = lp["k1"][:, None] * (-lv.az @ Xl[:6])
        tpl, ypl = _peaks(tt, etal[jdom])
        perl = np.diff(_up_crossings(tt, etal[jdom]))
        phys = res_c["physical (judge the 1e-5 s run)"]
        v7b[name] = {
            "level": "top", "amplitude (deg rotation | m translation)": a,
            "linear_predicted_peak_over_knee": r(a / a_lin * a7["predicted_peak_over_knee (max leg)"], 3),
            "target_mode (0-based, sets the speed)": tgt, "f_target_Hz (LOCK f_damped)": r(f_t, 5),
            "initial_velocity_point_m_s": r(qd0[:3], 6), "initial_angular_velocity_rad_s": r(qd0[3:], 6),
            "predicted_peak_bushing_force_over_muN": r(a / a_lin * a7["predicted_peak_bushing_force_over_muN"], 3),
            "window_s": win, "initial_state": "static equilibrium, all four legs LOCK after an extension (p_r0 2 bar g)",
            "replica": res_c,
            "linear_LOCK_no_knee (information: the result a missing knee would give)": {
                "max_elastic_dN_N": r(dNl.max(axis=1), 5),
                "max_dN_over_knee": r(dNl.max(axis=1) / lp["knee_ext"], 4),
                "mean_period_first10_s": r(float(perl[:10].mean()), 6),
                "eta_peaks_first10": r(ypl[:10], 6),
                "knee_effect_on_max_dN_rel (replica / linear - 1)": r(np.array(phys["max_elastic_dN_N"]) / dNl.max(axis=1) - 1, 4),
                "knee_effect_on_period_rel": r(float(phys["mean_period_first10_s"]) / float(perl[:10].mean()) - 1, 4),
                "knee_effect_on_eta_peak1..3_rel": r(np.array([x[1] for x in phys["eta_peaks_first10 (t_s, sqrt(kg) m)"][:3]]) / ypl[:3] - 1, 4),
            },
        }
    out["V7b_cases"] = v7b
    # energy check of the replica (undamped, V7b heave kick): piecewise-elastic energy must be conserved
    rep0 = Replica(lv, lp["knee_ext"], zero_damping=True)
    exc = next(e for e in EXCITATIONS if e[0] == "heave")
    qd0 = lv.qdot0(exc, v7b["heave"]["amplitude (deg rotation | m translation)"], float(lv.mats["LOCK"]["fd"][exc[4]]))
    tt = np.arange(0.0, 1.0 + 1e-12, SAMPLE_S)
    st0 = LegStates()
    sol, cr = rep0.run(np.r_[np.zeros(6), qd0], (0.0, 1.0), _no_move, st0, tt)
    E = np.array([rep0.energy_undamped(sol.y[:, k], np.zeros(4), st0) for k in range(len(tt))])
    drift = float(np.abs(E - E[0]).max() / E[0])
    out["meta"]["replica_energy_drift_undamped (V7b heave kick, 1 s, max |E - E0| / E0, knee crossings)"] = [r(drift, 3), len(cr)]
    if drift > 1e-6 or not cr:   # agent rule: conserved system drift <= 1e-6 (match)
        raise RuntimeError(f"replica energy check failed: drift {drift:.3e}, crossings {len(cr)}")
    # ---- V5 / V6 quasi-static and probe S_ii (top)
    q5 = {}
    for lvl in ("top",):
        lv = lvls[lvl]
        knee = lp["knee_ext"]
        ent = {}
        for label, moving_all in (("head_only (all k2, = reference.json V5)", True), ("L1R (FL moving, others LOCK)", False)):
            mv = np.array([True, moving_all, moving_all, moving_all])
            rows = {}
            for dmm in V5_STEPS_MM:
                F, q = quasi_static(lv, np.array([dmm * 1e-3, 0, 0, 0]), mv, knee)
                rows[f"FL +{dmm:g} mm"] = {"dF_N": r(F, 6), "droll_deg": r(math.degrees(q[1]), 5),
                                           "dpitch_deg": r(math.degrees(q[2]), 5),
                                           "legs_above_knee": [dm.LEG_NAMES[i] for i in range(4) if not mv[i] and F[i] > knee[i]],
                                           "max_increase_over_knee": r(max(F[i] / knee[i] for i in range(4) if not mv[i]) if not moving_all else 0.0, 4)}
            for sgn, nm in ((+1, "FL+"), (-1, "FL-")):
                for target, what in ((lv.F_min, "F_min"), (0.0, "lift")):
                    a_, b_ = 0.0, 0.05
                    for _ in range(80):
                        mid = 0.5 * (a_ + b_)
                        F, _q = quasi_static(lv, np.array([sgn * mid, 0, 0, 0]), mv, knee)
                        val = (lv.F0 + F - lv.rodw) if what == "F_min" else (lv.F0 + F)
                        if np.min(np.delete(val, 0)) > target:
                            a_ = mid
                        else:
                            b_ = mid
                    F, _q = quasi_static(lv, np.array([sgn * b_, 0, 0, 0]), mv, knee)
                    val = (lv.F0 + F - lv.rodw) if what == "F_min" else (lv.F0 + F)
                    j = 1 + int(np.argmin(np.delete(val, 0)))
                    rows[f"V6 {nm} {what}"] = {"leg": dm.LEG_NAMES[j], "travel_mm": r(0.5 * (a_ + b_) * 1e3, 5)}
            ent[label] = rows
        S = {}
        for i, leg in enumerate(dm.LEG_NAMES):
            kn = lp["k1"].copy(); kn[i] = lp["k2"][i]
            mv = np.zeros(4, bool); mv[i] = True
            sec = []
            for dsec in (+2e-3, -2e-3):
                de = np.zeros(4); de[i] = dsec
                F, _q = quasi_static(lv, de, mv, knee)
                sec.append(F[i] / dsec)
            S[leg] = {"head_only_kN_mm": r(dm.load_sensitivity(lp["k2"], geo.pad_xy)[i, i] / 1e6, 5),
                      "small_signal_kN_mm": r(dm.load_sensitivity(kn, geo.pad_xy)[i, i] / 1e6, 5),
                      "secant_+2mm_kN_mm": r(sec[0] / 1e6, 5), "secant_-2mm_kN_mm": r(sec[1] / 1e6, 5)}
        ent["probe_S_ii (probed leg moving, others LOCK)"] = S
        q5[lvl] = ent
    out["V5_V6_quasi_static"] = q5
    # ---- V5 dynamic replicas (FL moves, the other legs LOCK; FL locks at each stop): the S3 V5 sequence and the
    #      +0.3 mm step variants for the V9 smooth test 1
    lv = lvls["top"]
    a_cmd = float(p["actuator"]["command_accel_limit_m_s2"])
    v_max = float(p["actuator"]["max_speed_m_s"])
    tau_v = float(p["actuator"]["rod_side"]["release_tau_s"])
    T1 = 1.0 / float(lv.mats["LOCK"]["fd"][0])
    knee = lp["knee_ext"]

    def fl_case(moves, t_end, finals, trans):
        mv = Moves(moves, a_cmd)
        t, q, N, st, cr, log, lift = simulate_moves(lv, mv, t_end, tau_v)
        dN = N - lv.F0[:, None]
        out_c = {"moves (t_start_s, leg, distance_m, speed_m_s)": [[m_[0], dm.LEG_NAMES[m_[1]], m_[2], m_[3]] for m_ in moves],
                 "move_end_s": [r(m_[7], 7) for m_ in mv.moves],
                 "lock_release_log (t_s, leg, event, F_extra_N)": [[r(a_, 7), b_, c_, r(d_, 5)] for a_, b_, c_, d_ in log],
                 "knee_crossings (t_s, leg)": [[r(tc, 6), dm.LEG_NAMES[i]] for tc, i in cr[:40]],
                 "n_knee_crossings": len(cr), "lift_off": bool(lift)}
        for lab, (ta, tb) in trans.items():
            w = (t >= ta) & (t <= tb)
            out_c[f"transient {lab} [{ta:.4g}, {tb:.4g}] s"] = {
                "min_dF_N": r(dN[:, w].min(axis=1), 6), "max_dF_N": r(dN[:, w].max(axis=1), 6),
                "t_min_RL_s": r(float(t[w][int(np.argmin(dN[2, w]))]), 6),
                "max_dF_over_knee (FR RL RR)": r(dN[1:, w].max(axis=1) / knee[1:], 4)}
        for lab, (tend, d_fl) in finals.items():
            w = (t >= tend - 3 * T1) & (t <= tend)
            Fq, _q = quasi_static(lv, np.array([d_fl, 0, 0, 0]), np.array([True, False, False, False]), knee)
            out_c[f"final {lab} (mean over [{tend - 3 * T1:.4g}, {tend:.4g}] s)"] = {
                "dF_N": r(dN[:, w].mean(axis=1), 6),
                "dattitude_deg (roll, pitch)": r(np.degrees(q[3:5, w].mean(axis=1)), 5),
                "quasi_static_dF_N": r(Fq, 6),
                "minus_quasi_static_N (dynamic-lock path dependence)": r(dN[:, w].mean(axis=1) - Fq, 4),
                "minus_quasi_static_rel_of_max": r(float(np.abs(dN[:, w].mean(axis=1) - Fq).max() / np.abs(Fq).max()), 4)}
        return out_c, dict(t=t, q=q, dN=dN)

    v5d = {}
    # S3 job_v5 sequence (run_S3.py: hold 3 s, +1 mm at 0.5 mm/s, move + 0.2 + 10 s, then to +5 mm, same)
    sp = 0.5e-3
    t1s = 3.0; t1e = t1s + 1e-3 / sp + 0.2 + 10.0
    t2e = t1e + 4e-3 / sp + 0.2 + 10.0
    c, s_ = fl_case([(t1s, 0, 1e-3, sp), (t1e, 0, 4e-3, sp)], t2e,
                    {"+1 mm": (t1e, 1e-3), "+5 mm": (t2e, 5e-3)}, {"+1 mm move": (t1s, t1s + 2.5 + 2.0)})
    v5d["S3 V5 sequence (0.5 mm/s, +1 then +5 mm)"] = c
    series["V5_seq"] = s_
    # +0.3 mm variants for V9-1 (hold 0.5 s, end 12 s as run_S3 V9 step)
    for lab, d_, v_ in (("+0.3 mm at v_max (run_S3 V9 step form)", 0.3e-3, v_max),
                        ("+0.3 mm at 0.5 mm/s", 0.3e-3, 0.5e-3),
                        ("+0.15 mm at v_max", 0.15e-3, v_max),
                        ("+0.12 mm at v_max", 0.12e-3, v_max)):
        c, s_ = fl_case([(V9_HOLD_S, 0, d_, v_)], V9_END_S, {"end": (V9_END_S, d_)},
                        {"V9": (V9_HOLD_S, V9_HOLD_S + 2.5 + d_ / v_)})
        v5d[lab] = c
        if v_ != v_max:   # only the chosen V9-1 case (0.5 mm/s) is kept as a series; the v_max variants are evidence
            series["V5_p0p3mm_0p5mm_s"] = s_
    v5d["note"] = ("rods rigid with the body: the FL motor reaction m_rod a (about 22 N at the ramp) is not modelled; "
                   f"T1 = {T1:.6f} s (LOCK mode 1); dF = elastic pad normal force change from the static state")
    out["V5_dynamic_replica"] = v5d
    out["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)
    if npz_out is not None:
        flat = {}
        for key, d in series.items():
            for kk, vv in d.items():
                flat[f"{key}__{kk}"] = vv
        flat["units"] = np.array("t s; q [m m m rad rad rad] about the CoM (surge sway heave roll pitch yaw); "
                                 "dN elastic pad normal force change N (FL FR RL RR); eta = Phi_LOCK^T M q sqrt(kg) m")
        np.savez_compressed(npz_out, **flat)
        try:
            out["meta"]["series_npz"] = Path(npz_out).resolve().relative_to(dm.PROJECT_ROOT).as_posix()
        except ValueError:
            out["meta"]["series_npz"] = str(npz_out).replace("\\", "/")
    return out
