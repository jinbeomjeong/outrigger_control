"""S8 independent time-domain check of the V15 reference, stuck-leg modes (D-3) and the V8(b) ledger terms (D-4).

dynamics_model.md rev. 39. Chrono-independent (no pychrono, no 03_src). Reuses the geometry / statics of
s8_v15_reference.Model (l2b_reference.SlopeSystem rows) but integrates in time with the hook algorithm of the
hydraulics spec (s8_seal_friction_counterbalance.md 2.5): per step, explicit, one return mapping per leg.

Model (linear about the settled pose, top level, level floor):
* superstructure 6 DoF about its CoM (mass_6dof of the body without rods); the rods stand on the rigid NSC floor
  (KC_RIGID eliminated: rod vertical displacement 0 while N > 0), so a leg acts on the body only through its
  attachment row az_att (link extension s_i = az_att . q) and the lateral bushing k_t, c_t at the contact point;
* leg force F = F_spr + c (u - ds/dt), F_spr = F0 + k_out (dsp - s) = G(dc) + f, dc = ds_ref - dsp, |f| <= F_s
  (rigid stick, static = kinetic); G: moving FL k_h(s_ref) (c0 + dc), locked F0 + k_h dc + k_r min(dc, dc_knee)
  (rod_side) or F0 + k_h dc (head_only); c = c_mov on the moving leg, c_lock on the locked ones;
* contact N_i = F_i + m_rod g (rod static); lift-off = first N_i <= 0;
* semi-implicit (symplectic) Euler, forces from the state at the step start (explicit hook, as the L2b law);
* FL speed profile with the command ramp 0.1 s (YAML actuator.command_ramp_s).

Energy ledger (D-4, V8(b) for L2b with seal friction and CB): E = 1/2 v'Mv + sum F0_i s_i + 1/2 q'K_lat q
+ sum [F_spr_i^2 / (2 k_out) + U_oil,i(dc_i)]; W_m = int F_p u dt (F_p = F - f = pressure force, valve power),
W_L = int 1/2 k_h'(s_ref) c^2 u dt (moving column length), D_visc = int [c (u - ds)^2 + v'C_lat v] dt,
D_f = sum -f (dsp_new - dsp_old) >= 0, D_cb = sum G dS_cb (vent, spec 4.2). Residual R = dE + D - W.

Also: a single-leg CB case (spec 4.2 s_ref shift, mass-spring as cb_ref.py case A, constant column) to close
the ledger with the D_cb term.
Conventions: body x fwd, y left, z up, g -9.80665 z, leg order FL FR RL RR, compression +, SI inside.
Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s8_v15_dynamic_check.py [workers]
Writes 06_analysis/00_dynamics/s8_v15_dynamic_check.json and .png. Deterministic.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numba as nb  # noqa: E402
import dyn_model as dm  # noqa: E402
import s8_v15_reference as ref  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "s8_v15_dynamic_check.json"
RAMP_S = 0.1


# ------------------------------------------------------------------ kernel
@nb.njit(cache=True)
def kernel(dt, u_arr, M, Minv, az, kout, F0, Fs, kh_lock, kr_lock, knee_c, rod_side, c_damp, Klat, Clat, Wr,
           kh_beta_A, L0h, s_ref0, c0_fl, F_min, q, v, sp, f, stick, s_ref, out_ev, ledger,
           stop_at_liftoff, rec_every, rec):
    """Integrate len(u_arr) steps. Leg 0 moves with u_arr (s_ref), legs 1-3 locked.
    out_ev: [lam F_min_true, lam F_min_net, lam liftoff, leg F_min_true, leg net, leg lift, net reading at lift (4),
             true at lift(4), f at lift(4)] (-1 = not reached)
    ledger: [W_m, W_L, D_visc, D_f, E0, E_end, R_max, R_min]"""
    n = u_arr.shape[0]
    lam_prev = 0.0
    Fp_prev = np.zeros(4); Gp_prev = np.zeros(4); Np_prev = np.zeros(4)
    nrec = 0
    E0 = 0.0
    for k in range(n):
        u0 = u_arr[k]
        # ---- leg forces at the step start
        s = az @ q
        sd = az @ v
        F = np.zeros(4); G = np.zeros(4); N = np.zeros(4); Fspr = np.zeros(4)
        sp_old = sp.copy()
        for i in range(4):
            dsr = s_ref - s_ref0 if i == 0 else 0.0
            # oil law segment parameters: G = A + kseg * dc on its segment
            if i == 0:
                khm = kh_beta_A / (L0h + s_ref)
                A1 = khm * c0_fl; k1 = khm; A2 = A1; k2 = k1; kn = 1e300
            else:
                if rod_side:
                    A1 = F0[i]; k1 = kh_lock[i] + kr_lock[i]
                    kn = knee_c[i]
                    A2 = F0[i] + kr_lock[i] * kn; k2 = kh_lock[i]
                else:
                    A1 = F0[i]; k1 = kh_lock[i]; A2 = A1; k2 = k1; kn = 1e300
            dc_tr = dsr - sp[i]
            if dc_tr <= kn:
                G_tr = A1 + k1 * dc_tr
            else:
                G_tr = A2 + k2 * dc_tr
            Fspr_tr = F0[i] + kout[i] * (sp[i] - s[i])
            f_tr = Fspr_tr - G_tr
            if Fs[i] > 0.0 and abs(f_tr) <= Fs[i]:
                f[i] = f_tr; stick[i] = 1
                G[i] = G_tr; Fspr[i] = Fspr_tr
            else:
                sg = 0.0
                if Fs[i] > 0.0:
                    sg = 1.0 if f_tr > 0 else -1.0
                fs = sg * Fs[i]
                # segment 1
                x = (kout[i] * s[i] - F0[i] + A1 + k1 * dsr + fs) / (kout[i] + k1)
                if dsr - x > kn:
                    x = (kout[i] * s[i] - F0[i] + A2 + k2 * dsr + fs) / (kout[i] + k2)
                sp[i] = x
                f[i] = fs; stick[i] = 0
                dc = dsr - x
                G[i] = A1 + k1 * dc if dc <= kn else A2 + k2 * dc
                Fspr[i] = F0[i] + kout[i] * (x - s[i])
            ui = u0 if i == 0 else 0.0
            F[i] = Fspr[i] + c_damp[i] * (ui - sd[i])
            N[i] = F[i] + Wr[i]
        # ---- energy (state at the step start)
        lam = s_ref - s_ref0
        E = 0.5 * (v @ (M @ v)) + 0.5 * (q @ (Klat @ q))
        for i in range(4):
            E += F0[i] * s[i] + Fspr[i] * Fspr[i] / (2.0 * kout[i])
            dsr = s_ref - s_ref0 if i == 0 else 0.0
            dc = dsr - sp[i]
            if i == 0:
                khm = kh_beta_A / (L0h + s_ref)
                E += 0.5 * khm * (c0_fl + dc) ** 2
            else:
                E += F0[i] * dc + 0.5 * kh_lock[i] * dc * dc
                if rod_side:
                    if dc <= knee_c[i]:
                        E += 0.5 * kr_lock[i] * dc * dc
                    else:
                        E += kr_lock[i] * (knee_c[i] * dc - 0.5 * knee_c[i] ** 2)
        if k == 0:
            E0 = E
            ledger[4] = E0
        R = (E - E0) + ledger[2] + ledger[3] - ledger[0] - ledger[1]
        if R > ledger[6]:
            ledger[6] = R
        if R < ledger[7]:
            ledger[7] = R
        ledger[5] = E
        # ---- events (linear interpolation in lam between steps)
        if k > 0:
            for key in range(3):
                if out_ev[key] < 0.0:
                    if key == 0:
                        cur = F; prv = Fp_prev; thr = F_min
                    elif key == 1:
                        cur = G; prv = Gp_prev; thr = F_min
                    else:
                        cur = N; prv = Np_prev; thr = 0.0
                    for i in range(4):
                        if cur[i] <= thr and prv[i] > thr:
                            w = (prv[i] - thr) / (prv[i] - cur[i])
                            out_ev[key] = lam_prev + w * (lam - lam_prev)
                            out_ev[3 + key] = i
                            if key == 2:
                                for j in range(4):
                                    out_ev[6 + j] = G[j]
                                    out_ev[10 + j] = F[j]
                                    out_ev[14 + j] = f[j]
                            break
        if stop_at_liftoff and out_ev[2] >= 0.0:
            return k
        Fp_prev[:] = F; Gp_prev[:] = G; Np_prev[:] = N; lam_prev = lam
        if rec_every > 0 and k % rec_every == 0 and nrec < rec.shape[0]:
            rec[nrec, 0] = k * dt; rec[nrec, 1] = lam
            for i in range(4):
                rec[nrec, 2 + i] = F[i]; rec[nrec, 6 + i] = G[i]; rec[nrec, 10 + i] = f[i]
            rec[nrec, 14] = R
            for a in range(6):
                rec[nrec, 15 + a] = q[a]
            nrec += 1
        # ---- body update (semi-implicit Euler)
        gen = -(Klat @ q) - (Clat @ v)
        for i in range(4):
            gen += (F[i] - F0[i]) * az[i]
        acc = Minv @ gen
        # ledger power terms over this step (rectangle, step-start values)
        for i in range(4):
            ui = u0 if i == 0 else 0.0
            ledger[2] += c_damp[i] * (ui - sd[i]) ** 2 * dt
        ledger[2] += (v @ (Clat @ v)) * dt
        Fp0 = G[0] + c_damp[0] * (u0 - sd[0])
        ledger[0] += Fp0 * u0 * dt
        khm = kh_beta_A / (L0h + s_ref)
        cfl = c0_fl + (s_ref - s_ref0) - sp[0]
        ledger[1] += 0.5 * (-khm / (L0h + s_ref)) * cfl * cfl * u0 * dt
        v += dt * acc
        q += dt * v
        s_ref += u0 * dt
        # friction dissipation of the mapping done at this step start: the piston moved from sp_old to sp
        for i in range(4):
            ledger[3] += -f[i] * (sp[i] - sp_old[i])
    return n


def speed_profile(dt, u0, legs_mm, hold_s=2.0):
    """Trapezoid FL speed: for each target (mm, absolute from 0), accelerate in RAMP_S, cruise, decelerate in RAMP_S
    so that s_ref ends exactly on the target; then hold."""
    seq = []
    pos = 0.0
    for tgt in legs_mm:
        dist = tgt * 1e-3 - pos
        sgn = 1.0 if dist > 0 else -1.0
        D = abs(dist)
        t_cruise = (D - u0 * RAMP_S) / u0
        n_r = int(round(RAMP_S / dt))
        n_c = int(round(t_cruise / dt))
        up = (np.arange(n_r) + 0.5) / n_r * u0
        prof = np.concatenate([up, np.full(n_c, u0), up[::-1]])
        # exact endpoint: scale the cruise speed slightly
        err = D - prof.sum() * dt
        prof[n_r:n_r + n_c] += err / (n_c * dt)
        seq.append(sgn * prof)
        pos = tgt * 1e-3
    seq.append(np.zeros(int(round(hold_s / dt))))
    return np.concatenate(seq)


def build(m, Fs_front, rear_scale, variant):
    ss = m.sysm
    az = np.array([ss.b[i][:6] for i in range(4)])
    Klat = np.zeros((6, 6)); Clat = np.zeros((6, 6))
    for i in range(4):
        for row in (ss.G[i][0, :6], ss.G[i][1, :6]):
            Klat += m.lp["kt"][i] * np.outer(row, row)
            Clat += m.lp["ct"][i] * np.outer(row, row)
    M = dm.mass_6dof(m.body)
    Fs = np.array([Fs_front, Fs_front, rear_scale * Fs_front, rear_scale * Fs_front], float)
    knee_c = m.knee_G / (m.kh + m.kr)
    c_damp = np.array([m.c_mov[0], m.c_lock[1], m.c_lock[2], m.c_lock[3]])
    return dict(Minv=np.linalg.inv(M), M=M, az=az, Klat=Klat, Clat=Clat, Fs=Fs, knee_c=knee_c, c_damp=c_damp,
                rod_side=(variant == "rod_side"))


def run_case(args):
    Fs_front, variant, kind, u0, dt = args
    m = ref.Model("top")
    B = build(m, Fs_front, ref.REAR_SCALE, variant)
    if kind == "a":
        u_arr = speed_profile(dt, u0, [20.0], hold_s=0.0)
        stop = True
    else:
        u_arr = speed_profile(dt, u0, [10.0, 0.0], hold_s=10.0)
        stop = False
    q = np.zeros(6); v = np.zeros(6); sp = np.zeros(4); f = np.zeros(4); stick = np.ones(4, np.int64)
    out_ev = np.full(18, -1.0); out_ev[6:] = 0.0
    ledger = np.zeros(8); ledger[6] = -1e300; ledger[7] = 1e300
    rec = np.zeros((4000, 21))
    rec_every = max(1, len(u_arr) // 4000)
    s_ref0 = float(m.e_op[0])
    beta_A = m.beta * m.A_p[0]
    c0 = m.F0[0] / (beta_A / (m.L0h + s_ref0))
    t0 = time.perf_counter()
    nstep = kernel(dt, u_arr, B["M"], B["Minv"], B["az"], m.kout, m.F0, B["Fs"], m.kh, m.kr, B["knee_c"],
                   B["rod_side"], B["c_damp"], B["Klat"], B["Clat"], m.Wr, beta_A, m.L0h, s_ref0, c0, m.F_min, q, v,
                   sp, f, stick, s_ref0, out_ev, ledger, stop, rec_every, rec)
    wall = time.perf_counter() - t0
    res = {"F_s_front_N": Fs_front, "variant": variant, "kind": kind, "u_m_s": u0, "dt_s": dt, "steps": int(nstep),
           "wall_s": wall,
           "lam_F_min_true_mm": out_ev[0] * 1e3 if out_ev[0] >= 0 else None,
           "lam_F_min_net_mm": out_ev[1] * 1e3 if out_ev[1] >= 0 else None,
           "lam_liftoff_mm": out_ev[2] * 1e3 if out_ev[2] >= 0 else None,
           "legs (true, net, lift)": [dm.LEG_NAMES[int(x)] if x >= 0 else None for x in out_ev[3:6]],
           "net_at_liftoff_N": out_ev[6:10].tolist(), "true_at_liftoff_N": out_ev[10:14].tolist(),
           "f_at_liftoff_N": out_ev[14:18].tolist(),
           "ledger": {"W_m_J": ledger[0], "W_L_J": ledger[1], "D_visc_J": ledger[2], "D_f_J": ledger[3],
                      "dE_J": ledger[5] - ledger[4], "R_max_J": ledger[6], "R_min_J": ledger[7]},
           "end": {"F_spr_minus_F0_N": None}}
    if kind == "b":
        # residuals after the return and the hold: recompute the leg state at the end
        s = B["az"] @ q
        Fspr = m.F0 + m.kout * (sp - s)
        G = Fspr - f
        res["end"] = {"residual_true_N": (Fspr - m.F0).tolist(), "residual_net_N": (G - m.F0).tolist(),
                      "f_N": f.tolist(), "stick": stick.tolist(), "sp_um": (sp * 1e6).tolist()}
    led = res["ledger"]
    led["R_end_J"] = led["dE_J"] + led["D_visc_J"] + led["D_f_J"] - led["W_m_J"] - led["W_L_J"]
    led["E_ref_J (D_visc + D_f, V8(b))"] = led["D_visc_J"] + led["D_f_J"]
    res["rec_tail"] = rec[: max(1, int(nstep) // rec_every)][::50].tolist() if kind == "b" else None
    return res


# ------------------------------------------------------------------ stuck-leg modes (D-3)
def stuck_modes(level):
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    import l2b_reference as l2b
    lp = l2b.leg_parameters(p, geo)
    e_op = np.zeros(4) + np.asarray(lp["e_op"], float)
    b = dm.body_from_params(p, level)
    k1 = lp["k1_f"](e_op); kout = np.asarray(lp["k_out"], float)
    out = {}
    for name, ko in (("LOCK (k1)", k1), ("STUCK (k_out)", kout)):
        M, K, C, labels, _ = dm.model_10dof(b, geo, e_op, ko=ko, kc=np.full(4, l2b.KC_RIGID), kh=lp["kt"],
                                            co=lp["c_lock"], cc=np.zeros(4), ch=lp["ct"])
        w2, fu, Phi, cls, orth = dm.modal(M, K, labels)
        fd, zd = dm.complex_modes(M, K, C)
        # bushing (lateral) energy share r_i and numerical damping r w dt / 2 at dt 1e-4 s (implicit bushings)
        Kbush = np.zeros((10, 10))
        for i in range(4):     # lateral springs at the pad bottom, as in dm.model_10dof
            d_pad = np.array([*geo.pad_xy[i], geo.pad_z_retracted[i] - e_op[i]]) - b.com
            ax_p, ay_p, _ = dm.a_vec(d_pad)
            for a_ in (ax_p, ay_p):
                aa = np.zeros(10); aa[:6] = a_
                Kbush += lp["kt"][i] * np.outer(aa, aa)
        r_i = np.array([Phi[:, j] @ Kbush @ Phi[:, j] / w2[j] for j in range(6)])
        zn = r_i * np.sqrt(w2[:6]) * 1e-4 / 2
        out[name] = {"f_undamped_Hz": fu[:6], "f_damped_Hz": fd[:6], "zeta": zd[:6], "mode_content": cls[:6],
                     "orthogonality_err": orth, "bushing_energy_share_r": r_i,
                     "zeta_num_dt1e-4 (r w dt / 2)": zn, "zeta_num_over_zeta": zn / zd[:6]}
    s, l = out["STUCK (k_out)"], out["LOCK (k1)"]
    out["ratio_stuck_over_lock"] = {"f": np.array(s["f_undamped_Hz"]) / np.array(l["f_undamped_Hz"]),
                                    "zeta": np.array(s["zeta"]) / np.array(l["zeta"])}
    return out


# ------------------------------------------------------------------ ring-down (centre vs band edge)
def ringdown_case(args):
    """Free vibration of the locked machine (rod side on, u = 0) started in one stuck mode with a leg-force
    amplitude amp_N. start 'centre': f = 0 on every leg (armed at rest); 'edge': f = -F_s on every leg (state
    after an extension: the oil anchor is G_lock = F0 + F_s, the spring part F0, statics unchanged)."""
    Fs_front, start, amp_N, mode_idx = args
    m = ref.Model("top")
    B = build(m, Fs_front, ref.REAR_SCALE, "rod_side")
    Fs = B["Fs"]
    M = B["M"]
    K_stuck = B["Klat"] + sum(m.kout[i] * np.outer(B["az"][i], B["az"][i]) for i in range(4))
    kser = 1.0 / (1.0 / (m.kh + m.kr) + 1.0 / m.kout)
    K_lock = B["Klat"] + sum(kser[i] * np.outer(B["az"][i], B["az"][i]) for i in range(4))
    C = B["Clat"] + sum(m.c_lock[i] * np.outer(B["az"][i], B["az"][i]) for i in range(4))
    from scipy.linalg import eigh
    w2s, Ps = eigh(K_stuck, M)
    fd_s, z_s = dm.complex_modes(M, K_stuck, C)
    fd_l, z_l = dm.complex_modes(M, K_lock, C)
    phi = Ps[:, mode_idx]
    dF_unit = np.array([m.kout[i] * abs(B["az"][i] @ phi) for i in range(4)])
    w = math.sqrt(w2s[mode_idx])
    scale = amp_N / dF_unit.max()
    q = np.zeros(6); v = phi * scale * w
    sp = np.zeros(4); f = np.zeros(4)
    G0 = m.F0 + (Fs if start == "edge" else 0.0)
    if start == "edge":
        f[:] = -Fs
    dt = 1e-4; T = 6.0; n = int(T / dt); rec_every = 10
    rec = np.zeros((n // rec_every + 1, 15))
    nrec = ringdown_general(dt, n, B["Minv"], B["az"], m.kout, m.F0, G0, Fs, m.kh, m.kr, B["knee_c"],
                            m.c_lock, B["Klat"], B["Clat"], q, v, sp, f, rec, rec_every)
    rec = rec[:nrec]
    t = rec[:, 0]
    eta = rec[:, 1:7] @ (M @ phi)
    fmax = np.abs(rec[:, 11:15]).max(axis=0)
    return {"F_s_front_N": Fs_front, "start": start, "leg_force_amplitude_N": amp_N, "mode_index": mode_idx,
            "linear_stuck": {"f_Hz": fd_s[mode_idx], "zeta": z_s[mode_idx]},
            "linear_lock_slip": {"f_Hz": fd_l[mode_idx], "zeta": z_l[mode_idx]},
            "fit_modal_coordinate": fit_decay(t, eta),
            "max_abs_dF_N": float(np.abs(rec[:, 7:11] - m.F0).max()),
            "legs_reaching_band_edge": [bool(fmax[i] >= Fs[i] * (1 - 1e-9)) for i in range(4)],
            "final_load_shift_N": (rec[-1, 7:11] - m.F0).tolist(),
            "final_f_N": rec[-1, 11:15].tolist()}


@nb.njit(cache=True)
def ringdown_general(dt, n, Minv, az, kout, F0, G0, Fs, kh, kr, knee_c, c_damp, Klat, Clat, q, v, sp, f, rec,
                     rec_every):
    """All legs locked, u = 0; oil anchor G0 separate from the spring preload F0 (f = F0 - G0 at rest)."""
    nrec = 0
    for k in range(n):
        s = az @ q; sd = az @ v
        F = np.zeros(4)
        for i in range(4):
            A1 = G0[i]; k1 = kh[i] + kr[i]; kn = knee_c[i]; A2 = G0[i] + kr[i] * kn; k2 = kh[i]
            dc_tr = -sp[i]
            G_tr = A1 + k1 * dc_tr if dc_tr <= kn else A2 + k2 * dc_tr
            Fspr_tr = F0[i] + kout[i] * (sp[i] - s[i])
            f_tr = Fspr_tr - G_tr
            if abs(f_tr) <= Fs[i] * (1.0 + 1e-12):
                f[i] = f_tr; Fspr = Fspr_tr
            else:
                sg = 1.0 if f_tr > 0 else -1.0
                fs = sg * Fs[i]
                x = (kout[i] * s[i] - F0[i] + A1 + fs) / (kout[i] + k1)
                if -x > kn:
                    x = (kout[i] * s[i] - F0[i] + A2 + fs) / (kout[i] + k2)
                sp[i] = x; f[i] = fs
                Fspr = F0[i] + kout[i] * (x - s[i])
            F[i] = Fspr - c_damp[i] * sd[i]
        if k % rec_every == 0 and nrec < rec.shape[0]:
            rec[nrec, 0] = k * dt
            for a in range(6):
                rec[nrec, 1 + a] = q[a]
            for i in range(4):
                rec[nrec, 7 + i] = F[i]
                rec[nrec, 11 + i] = f[i]
            nrec += 1
        gen = -(Klat @ q) - (Clat @ v)
        for i in range(4):
            gen += (F[i] - F0[i]) * az[i]
        v += dt * (Minv @ gen)
        q += dt * v
    return nrec


def fit_decay(t, x):
    """Frequency from zero crossings, decay from successive positive peaks (log decrement over the record)."""
    x = x - x[-len(x) // 5:].mean() if len(x) > 50 else x
    zc = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0))
    if len(zc) < 3:
        return None
    tz = t[zc] - x[zc] * (t[zc + 1] - t[zc]) / (x[zc + 1] - x[zc])
    T = np.diff(tz)
    peaks = []
    for a, b in zip(zc[:-1], zc[1:], strict=True):
        seg = x[a:b]
        peaks.append(seg.max())
    peaks = np.array(peaks)
    out = {"f_Hz_mean": float(1 / T.mean()), "f_Hz_first3": float(1 / T[:3].mean()),
           "f_Hz_last3": float(1 / T[-3:].mean()), "n_cycles": int(len(T))}
    good = peaks > peaks[0] * 1e-3
    if good.sum() >= 3:
        lp = np.log(peaks[good]); n = np.arange(len(lp))
        slope = np.polyfit(n, lp, 1)[0]
        delta = -slope
        out["zeta_logdec"] = float(delta / math.sqrt(4 * math.pi ** 2 + delta ** 2))
        out["peak_ratio_per_cycle_first3"] = (peaks[1:4] / peaks[0:3]).tolist()
        # Coulomb signature: linear (constant decrement) vs geometric decay
        out["peak_drop_per_cycle_first3"] = (peaks[0:3] - peaks[1:4]).tolist()
    return out


# ------------------------------------------------------------------ single-leg CB ledger (spec 4.2)
@nb.njit(cache=True)
def cb_leg(dt, n, M, KS, BP, A1, kh, p_cr, dp_ov, Q_r, tau, F_s, t1, t2, f_end, out):
    """Mass M (x down +) on a spring KS and a locked head chamber behind a CB (rod side ambient, gauge).
    Oil law G = kh (s_ref - x_p) with s_ref shifted by the vented volume / A1 (spec 4.2); seal friction
    |f| <= F_s in parallel with the oil (rod rigid, piston = mass). Ledger: E = 1/2 M v^2 + 1/2 KS x^2 + G^2/(2 kh),
    W = int load v dt, D = int BP v^2 + D_f + D_cb (D_cb = sum G dS_cb). Returns p_max, p_end, x_end, vent, R."""
    x = 0.0; v = 0.0; s_ref = 0.0; y = 0.0; vent = 0.0; f = 0.0
    W = 0.0; Dv = 0.0; Df = 0.0; Dcb = 0.0; pmax = 0.0
    E0 = 0.0
    Rmax = -1e300; Rmin = 1e300
    for k in range(n):
        t = k * dt
        load = 116.3e3 * min(t / 1.0, 1.0)
        if t > t1:
            load += (f_end - 116.3e3) * min((t - t1) / (t2 - t1), 1.0)
        # piston = mass (rigid rod); friction between piston and barrel; oil compression c = x - s_ref
        c = x - s_ref
        G = kh * c
        p = G / A1
        if p > pmax:
            pmax = p
        # friction: the mass sees G + f with f opposing the velocity (rigid stick handled by velocity sign)
        # Coulomb with a stick test on the trial acceleration
        Fnet0 = load - G - KS * x - BP * v
        if F_s > 0.0:
            if abs(v) < 1e-9 and abs(Fnet0) <= F_s:
                f = Fnet0; acc = 0.0; v = 0.0
            else:
                sgn = 1.0 if (v > 0 or (v == 0 and Fnet0 > 0)) else -1.0
                f = sgn * F_s
                acc = (Fnet0 - f) / M
        else:
            f = 0.0
            acc = Fnet0 / M
        E = 0.5 * M * v * v + 0.5 * KS * x * x + G * G / (2 * kh)
        if k == 0:
            E0 = E
        R = (E - E0) + Dv + Df + Dcb - W
        if R > Rmax:
            Rmax = R
        if R < Rmin:
            Rmin = R
        # CB (spec 4.2), first-order lag, explicit vent applied from the next step
        ystar = max(p - p_cr, 0.0) / dp_ov
        if tau > 0:
            y = ystar + (y - ystar) * math.exp(-dt / tau)
        else:
            y = ystar
        Q = Q_r * y
        dS = Q * dt / A1
        # powers over the step (step-start values)
        W += load * v * dt
        Dv += BP * v * v * dt
        v_new = v + dt * acc
        if F_s > 0.0 and v != 0.0 and v_new * v < 0.0:
            v_new = 0.0                                   # Coulomb stop (no reversal through the band)
        Df += abs(f) * abs(v_new) * dt if F_s > 0.0 else 0.0
        v = v_new
        x += dt * v
        # vent: s_ref moves with the vented volume; the oil energy released at constant x = G dS - kh dS^2 / 2
        Dcb += G * dS - 0.5 * kh * dS * dS
        s_ref += dS
        vent += Q * dt
    out[0] = pmax; out[1] = kh * (x - s_ref) / A1; out[2] = x; out[3] = vent; out[4] = Rmax; out[5] = Rmin
    out[6] = W; out[7] = Dv; out[8] = Df; out[9] = Dcb; out[10] = (0.5 * M * v * v + 0.5 * KS * x * x
                                                                 + (kh * (x - s_ref)) ** 2 / (2 * kh)) - E0
    return out


def cb_case(args):
    dt, F_s, f_end, t2 = args
    A1 = 0.013273229; beta = 1e9; L = 0.40
    kh = beta * A1 / L
    out = np.zeros(11)
    n = int(round(6.0 / dt))
    cb_leg(dt, n, 9690.0, 4.77e6, 33900.0, A1, kh, 330e5, 20e5, 1e-3, 0.01, F_s, 2.0, t2, f_end, out)
    W, Dv, Df, Dcb, dE = out[6], out[7], out[8], out[9], out[10]
    return {"dt_s": dt, "F_s_N": F_s, "ramp_end_s": t2, "p_max_bar_g": out[0] / 1e5, "p_end_bar_g": out[1] / 1e5,
            "x_end_mm": out[2] * 1e3, "vented_cm3": out[3] * 1e6, "W_ext_J": W, "D_visc_J": Dv, "D_f_J": Df,
            "D_cb_J": Dcb, "dE_J": dE, "R_end_J": dE + Dv + Df + Dcb - W, "R_max_J": out[4], "R_min_J": out[5],
            "E_ref_J": Dv + Df + Dcb}


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    t0 = time.perf_counter()
    m = ref.Model("top")
    # warm the numba cache in the main process before the spawn pool (numba cache + spawn lesson)
    run_case((4e3, "rod_side", "a", 1e-4, 1e-3))
    ringdown_case((4e3, "centre", 1e3, 0))
    cb_case((1e-4, 0.0, 700e3, 4.0))
    jobs = []
    for L in ref.LEVELS_KN:
        for var in ("rod_side", "head_only"):
            jobs.append((L * 1e3, var, "a", 1e-4, 1e-4))
            jobs.append((L * 1e3, var, "b", 1e-4, 1e-4))
        jobs.append((L * 1e3, "rod_side", "a", 1e-4, 5e-5))      # dt halving
        jobs.append((L * 1e3, "rod_side", "b", 1e-4, 5e-5))
        jobs.append((L * 1e3, "rod_side", "b", 1e-4, 2e-4))      # dt doubling (ledger order)
    jobs.append((8e3, "rod_side", "a", 5e-5, 1e-4))              # inertia check 0.05 mm/s
    jobs.append((8e3, "rod_side", "b", 5e-5, 1e-4))
    rjobs = [(Fs, st, amp, mi) for Fs in (4e3, 8e3) for st in ("centre", "edge") for amp, mi in
             ((1e3, 0), (1e3, 1), (1e3, 5), (3e3, 0))]
    cjobs = [(dt, Fs, fe, t2) for dt in (1e-5, 2e-5) for Fs in (0.0, 4e3) for fe, t2 in ((700e3, 4.0),)]
    with Pool(workers) as pool:
        runs = pool.map(run_case, jobs, chunksize=1)
        rds = pool.map(ringdown_case, rjobs, chunksize=1)
        cbs = pool.map(cb_case, cjobs, chunksize=1)
    # quasi-static comparison
    cmp = []
    for rres in runs:
        if rres["kind"] != "a":
            continue
        qs = ref.run_path(m, rres["F_s_front_N"], variant=rres["variant"])
        fi = qs["first"]
        lift_leg = dm.LEG_NAMES.index(fi["liftoff"]["leg"])
        cmp.append({"F_s_front_N": rres["F_s_front_N"], "variant": rres["variant"], "u": rres["u_m_s"],
                    "dt": rres["dt_s"],
                    "d_F_min_true_um": (rres["lam_F_min_true_mm"] - fi["F_min_true"]["lam_mm"]) * 1e3,
                    "d_F_min_net_um": (None if rres["lam_F_min_net_mm"] is None or "F_min_net" not in fi else
                                       (rres["lam_F_min_net_mm"] - fi["F_min_net"]["lam_mm"]) * 1e3),
                    "d_liftoff_um": (rres["lam_liftoff_mm"] - fi["liftoff"]["lam_mm"]) * 1e3,
                    "d_net_reading_at_liftoff_N": rres["net_at_liftoff_N"][lift_leg] - fi["liftoff"]["G_N"][lift_leg],
                    "same_legs": rres["legs (true, net, lift)"] == [fi["F_min_true"]["leg"],
                                                                   fi.get("F_min_net", {}).get("leg"),
                                                                   fi["liftoff"]["leg"]]})
    cmpb = []
    for rres in runs:
        if rres["kind"] != "b":
            continue
        qs = ref.run_path(m, rres["F_s_front_N"], variant=rres["variant"], targets=(0.010, 0.0),
                          stop_at_liftoff=False)
        cmpb.append({"F_s_front_N": rres["F_s_front_N"], "variant": rres["variant"], "u": rres["u_m_s"],
                     "dt": rres["dt_s"],
                     "d_residual_true_N": (np.array(rres["end"]["residual_true_N"]) - (qs["end"]["F_N"] - m.F0)).tolist(),
                     "d_residual_net_N": (np.array(rres["end"]["residual_net_N"]) - (qs["end"]["G_N"] - m.F0)).tolist(),
                     "ledger": rres["ledger"]})
    res = {"meta": {"script": "04_scripts/01_dynamics/s8_v15_dynamic_check.py", "doc": __doc__.split("\n\n")[0],
                    "workers": workers, "runtime_s": None},
           "runs": [{k: v for k, v in x.items() if k != "rec_tail"} for x in runs],
           "compare_a_dynamic_minus_quasistatic": cmp, "compare_b_dynamic_minus_quasistatic": cmpb,
           "stuck_modes (D-3)": {lvl: stuck_modes(lvl) for lvl in dm.LEVELS},
           "ringdown (D-3)": rds, "cb_single_leg_ledger (D-4)": cbs}
    res["meta"]["runtime_s"] = time.perf_counter() - t0
    OUT.write_text(json.dumps(ref.r(res), indent=1, ensure_ascii=False, default=lambda o: ref.r(np.asarray(o))),
                   encoding="utf-8")
    # figure: (b) trajectories at L8 rod_side
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        sel = [x for x in runs if x["kind"] == "b" and x["variant"] == "rod_side" and x["dt_s"] == 1e-4
               and x["u_m_s"] == 1e-4]
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
        for x in sel:
            rec = np.array(x["rec_tail"])
            if rec.size == 0:
                continue
            lab = f"F_s {x['F_s_front_N'] / 1e3:g} kN"
            axs[0].plot(rec[:, 1] * 1e3, (rec[:, 4] - m.F0[2]) / 1e3, label=lab + " true")
            axs[0].plot(rec[:, 1] * 1e3, (rec[:, 8] - m.F0[2]) / 1e3, "--", label=lab + " net reading")
            axs[1].plot(rec[:, 0], rec[:, 14], label=lab)
        axs[0].set_xlabel("FL s_ref change [mm]"); axs[0].set_ylabel("RL load change [kN]")
        axs[0].set_title("V15(b) round trip, RL (rod side on, rear F_s = 0.833 x front)")
        axs[0].grid(True); axs[0].legend(fontsize=7)
        axs[1].set_xlabel("time [s]"); axs[1].set_ylabel("ledger residual R [J]")
        axs[1].set_title("V8(b) residual with D_f (dt 1e-4 s)"); axs[1].grid(True); axs[1].legend(fontsize=7)
        fig.tight_layout(); fig.savefig(OUT.with_suffix(".png"), dpi=130)
    except Exception as exc:  # noqa: BLE001
        print("figure failed:", exc)
    print("wrote", OUT, f"{res['meta']['runtime_s']:.1f} s")


if __name__ == "__main__":
    main()
