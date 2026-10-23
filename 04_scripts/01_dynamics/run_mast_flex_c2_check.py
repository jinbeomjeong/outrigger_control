"""G5: C2 re-judgement with a one-mode-per-direction equivalent flexible mast (dynamics_model.md 3.9.7, revision 16).

Why: the control-expert mast surrogate (c2_linear / run_c2_timedomain, roll / pitch inertia scaled to the coupled
rocking frequencies) failed F_min at top diag 3 deg / pitch +3.7 deg. That surrogate puts all rocking energy into the
rigid superstructure, opposite to the detailed flexible-mast result of 3.9.5 (pad dynamic deviation x0.49..0.82).
This script replaces it with a physical reduced mast:

Equivalent mast (per auger level and support case, ASSUMPTION-level model, calibrated to dynamics_model.md 3.9.2):
  * mast set = mast slices + top sheave + winch + lower guide + backstay equivalent mass + auger (drive + tool) + boom
    (the MastSystem masses of run_mast_bending_check, 13,189 kg), one rigid body (mass, CoM, inertia about CoM);
  * 2 relative rotations about horizontal axes through the hinge pin H1 (2.033, 0, 1.371) m: alpha_x (about +x,
    lateral / LAT), alpha_y (about +y, fore-aft / FA), linear relative kinematics, gravity second-order (P-delta) term
    -m g h alpha (h = mast-set CoM height above H1) included explicitly, spring preload so that alpha = 0 is the
    equilibrium with the body level;
  * rotational springs k_x, k_y set so that the mast-only first LAT / FA frequencies (body fixed, P-delta included)
    equal the detailed model (run_mast_bending_check.MastSystem) for the support case; coupled rocking checked against
    3.9.3 (not fitted);
  * dashpots c_j = 2 zeta_j sqrt(k_eff,j M_jj) on the mast-only modes, zeta 0.015 nominal (sensitivity 0.012 / 0.023);
  * support cases: upper (k_bs 4.18e8 N/m, k_cyl 2.1e8 N/m) and lower (1e8, 3e7), as 3.9.1.
Nonlinear time-domain plant: copy of run_control_comparison.physics (pads L1 + crawler D, Coulomb bushings,
symplectic Euler dt 5e-4 s) with the superstructure split into rest body + mast set: unknowns [a_body(3), wdot(3),
alpha_ddot(2)] from an 8x8 mass matrix every step (velocity-product terms included). The C2 controller, sensors,
delay / ramp and metrics are those of run_c2_timedomain.run_case (imported, not modified): rcc.Plant is replaced at
run time by FlexPlant in this process only.

Conventions: body frame x forward, y left, z up; gravity -9.80665 z_hat (world); roll about +x, pitch about +y
(pitch > 0 nose down); quaternion wxyz (scalar first) as run_control_comparison; leg order FL, FR, RL, RR; SI units.

Run (project root, dynamics-dev activated, E-cores 16-27; run 'main' first, 'robust' adds to its JSON):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_mast_flex_c2_check.py --stage main     # ~9.2 min
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_mast_flex_c2_check.py --stage robust   # ~8.7 min
  (--quick: top only, 3 slopes, separate *_quick.json; --selftest: pool smoke test)
Writes 06_analysis/00_dynamics/mast_flex_c2_check.json and mast_flex_c2_check_{timeseries,slope_map,cause,robust}.png.
Seeds: run_control_comparison CA seed 12345 (robust stage 12345..12347).
Support cases: stiff (rigid supports, flexible beam), upper, lower (dynamics_model.md 3.9.1).
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "03_control"))
import dyn_model as dm  # noqa: E402
import run_control_comparison as rcc  # noqa: E402
import run_mast_bending_check as mbc  # noqa: E402
import numba as nb  # noqa: E402

ROOT = dm.PROJECT_ROOT
OUT_DIR = ROOT / "06_analysis" / "00_dynamics"
OUT_JSON = OUT_DIR / "mast_flex_c2_check.json"
G = 9.80665
DEG = 180.0 / math.pi
NACC = 53       # 45:49 / 49:53 = floor-plane |T| / normal N per pad, written only with fric_mode 1 (rev. 26)
ZETA_NOM = 0.015
# grounding threshold: YAML control.F_min_cylinder_N (net cylinder force), in kN
F_MIN_KN = float(dm.load_params()["control"]["F_min_cylinder_N"]) / 1e3
D8_FORCE_MARGIN_KN = 5.0  # D8 slope criterion: min cylinder force >= F_min + 5 kN (figure line)
# support cases of dynamics_model.md 3.9.1: stiff = rigid supports (beam still flexible, 3.9.3 "강체 지지"),
# upper = oil-only backstay + assumed locked boom cylinder, lower = hoses / unlocked (ASSUMPTION, Q-B1 / Q-B3 open)
SUPPORTS = {"stiff": (1.0e12, 1.0e12), "upper": (mbc.K_BS_NOM, mbc.K_CYL_NOM), "lower": (mbc.K_BS_LOW, mbc.K_CYL_LOW)}
DOC_KEY = {"stiff": "sup_rigid", "upper": "sup_upper", "lower": "sup_lower"}
FLEX = tuple(SUPPORTS)
ORIG_PLANT = rcc.Plant
CONFIG: dict = {}
LAST = {}

# --------------------------------------------------------------------------------------------- numba kernel


@nb.njit(cache=True)
def _skew(d):
    S = np.zeros((3, 3))
    S[0, 1] = -d[2]; S[0, 2] = d[1]; S[1, 0] = d[2]; S[1, 2] = -d[0]; S[2, 0] = -d[1]; S[2, 1] = d[0]
    return S


@nb.njit(cache=True)
def physics_flex(nsteps, dt, u_cmd, r, v, q, w, al, ald, sref, x, f, panc, pflag, canc, cflag,
                 m, Ib, Ibinv, pad_rel, cr_rel, imu_rel, nrm, g,
                 ko, ks, cn, kt, ct, Wr, Fs, kcr, ccr, ktcr, ctcr, mu, mu_cr, smax, Fext, Fret, goff,
                 flex, mr, dr, Ir, mm, dm0, Gm, Im, Ka, Ca, hgt, M0, acc, fmode, tez):
    """run_control_comparison.physics + 2-DoF equivalent mast (flex = 1). flex = 0 reproduces physics exactly.
    Extra slots: acc[24:28] min pad contact force over the call, acc[28:32] / acc[32:36] pad tangential force along
    body x / y (last step), acc[36] crawler tangential force along body x (last step), acc[37:39] alpha (last),
    acc[39:41] max |alpha| over the call, acc[41:45] pad slipping flag (last step).
    fmode 0 (default) = original pad decomposition; fmode 1 = Chrono L1 decomposition (see
    run_control_comparison.physics): acc[11+i] = rod axial load N (a . n) + T . e_z, acc[28:36] = body x / y of the whole
    pad force N n + T (= rod lateral load L, perpendicular to the leg axis), acc[45:49] = |T| (floor plane),
    acc[49:53] = N (dynamics_model.md 3.15, rev. 26)."""
    gv = np.array([0.0, 0.0, -g])
    E = np.zeros((3, 2)); E[0, 0] = 1.0; E[1, 1] = 1.0
    for _ in range(nsteps):
        R = _R(q)
        ez = R[:, 2]
        a_n = nrm[0] * ez[0] + nrm[1] * ez[1] + nrm[2] * ez[2]
        ww = R @ w
        F = m * gv
        T = np.zeros(3)
        ctx = 0.0
        for i in range(4):
            P = ko[i] * (sref[i] - x[i])
            ui = u_cmd[i]
            if ui > 0 and P >= Fext[i]:   # per-leg limits (4,) (rev. 30)
                ui = 0.0
                acc[3 + i] += 1
            if ui < 0 and P <= -Fret[i]:
                ui = 0.0
            s_new = sref[i] + ui * dt
            if s_new > smax:
                s_new = smax; ui = 0.0; acc[7 + i] += 1
            if s_new < 0.0:
                s_new = 0.0; ui = 0.0; acc[7 + i] += 1
            sref[i] = s_new
            d0 = R @ pad_rel[i]
            p0 = r + d0
            gax = (nrm[0] * p0[0] + nrm[1] * p0[1] + nrm[2] * p0[2] + goff[i]) / a_n
            if fmode == 0:
                Fel = ks[i] * max(x[i] - gax, 0.0)
                ftr = Fel - ko[i] * (sref[i] - x[i]) - Wr[i]
                if abs(ftr) <= Fs[i] and Fs[i] > 0:
                    f[i] = ftr
                else:
                    fs = Fs[i] * (1.0 if ftr > 0 else -1.0)
                    rhs = ko[i] * sref[i] + Wr[i] + fs
                    x1 = rhs / ko[i]
                    if x1 <= gax:
                        x[i] = x1
                    else:
                        x[i] = (rhs + ks[i] * gax) / (ks[i] + ko[i])
                    f[i] = fs
            else:
                ksa = ks[i] * a_n
                te = tez[i] if x[i] > gax else 0.0
                Fel = ksa * max(x[i] - gax, 0.0) + te
                ftr = Fel - ko[i] * (sref[i] - x[i]) - Wr[i]
                if abs(ftr) <= Fs[i] and Fs[i] > 0:
                    f[i] = ftr
                else:
                    fs = Fs[i] * (1.0 if ftr > 0 else -1.0)
                    rhs = ko[i] * sref[i] + Wr[i] + fs
                    x1 = rhs / ko[i]
                    if x1 <= gax:
                        x[i] = x1
                    else:
                        x[i] = (rhs - te + ksa * gax) / (ksa + ko[i])
                    f[i] = fs
            c = x[i] - gax
            Pn = ko[i] * (sref[i] - x[i])
            if Pn > acc[16 + i]:
                acc[16 + i] = Pn
            if Pn < acc[20 + i]:
                acc[20 + i] = Pn
            dp = d0 - x[i] * ez
            pp = r + dp
            vp = v + _cross(ww, dp)
            acc[41 + i] = 0.0
            if c > 0:
                Fel = ks[i] * c
                vn = vp[0] * nrm[0] + vp[1] * nrm[1] + vp[2] * nrm[2]
                Fl = Fel + cn[i] * (ui - vn / a_n)
                if Fl < 0:
                    Fl = 0.0
                Fv = Fl * ez
                if pflag[i] == 0:
                    panc[i, :] = pp
                    pflag[i] = 1
                dd = pp - panc[i]
                dn = dd[0] * nrm[0] + dd[1] * nrm[1] + dd[2] * nrm[2]
                dt_ = dd - dn * nrm
                vt = vp - vn * nrm
                Ft = -kt[i] * dt_
                Nn = Fl * a_n if fmode == 0 else Fl
                fe = math.sqrt(Ft[0] ** 2 + Ft[1] ** 2 + Ft[2] ** 2)
                if fe > mu * Nn:
                    sc = mu * Nn / fe if fe > 0 else 0.0
                    Ft = Ft * sc
                    panc[i, :] = pp + Ft / kt[i]
                    acc[41 + i] = 1.0
                else:
                    Ft = Ft - ct[i] * vt
                if fmode == 0:
                    Fi = Fv + Ft
                    acc[11 + i] = Fl
                    acc[28 + i] = Ft[0] * R[0, 0] + Ft[1] * R[1, 0] + Ft[2] * R[2, 0]
                    acc[32 + i] = Ft[0] * R[0, 1] + Ft[1] * R[1, 1] + Ft[2] * R[2, 1]
                else:
                    Fi = Fl * nrm + Ft
                    tez[i] = Ft[0] * ez[0] + Ft[1] * ez[1] + Ft[2] * ez[2]
                    acc[11 + i] = Fl * a_n + tez[i]
                    acc[28 + i] = Fi[0] * R[0, 0] + Fi[1] * R[1, 0] + Fi[2] * R[2, 0]
                    acc[32 + i] = Fi[0] * R[0, 1] + Fi[1] * R[1, 1] + Fi[2] * R[2, 1]
                    acc[45 + i] = math.sqrt(Ft[0] ** 2 + Ft[1] ** 2 + Ft[2] ** 2)
                    acc[49 + i] = Fl
            else:
                pflag[i] = 0
                Fi = np.zeros(3)
                acc[11 + i] = 0.0
                acc[28 + i] = 0.0; acc[32 + i] = 0.0
                tez[i] = 0.0
                if fmode != 0:
                    acc[45 + i] = 0.0; acc[49 + i] = 0.0
            if acc[11 + i] < acc[24 + i]:
                acc[24 + i] = acc[11 + i]
            F += Fi
            T += _cross(dp, Fi)
        Fc_tot = 0.0
        for j in range(cr_rel.shape[0]):
            dp = R @ cr_rel[j]
            pp = r + dp
            dn0 = pp[0] * nrm[0] + pp[1] * nrm[1] + pp[2] * nrm[2]
            if dn0 < 0:
                vp = v + _cross(ww, dp)
                vn = vp[0] * nrm[0] + vp[1] * nrm[1] + vp[2] * nrm[2]
                N = -kcr[j] * dn0 - ccr[j] * vn
                if N < 0:
                    N = 0.0
                if cflag[j] == 0:
                    canc[j, :] = pp
                    cflag[j] = 1
                dd = pp - canc[j]
                dn = dd[0] * nrm[0] + dd[1] * nrm[1] + dd[2] * nrm[2]
                dt_ = dd - dn * nrm
                vt = vp - vn * nrm
                Ft = -ktcr[j] * dt_
                fe = math.sqrt(Ft[0] ** 2 + Ft[1] ** 2 + Ft[2] ** 2)
                if fe > mu_cr * N:
                    sc = mu_cr * N / fe if fe > 0 else 0.0
                    Ft = Ft * sc
                    canc[j, :] = pp + Ft / ktcr[j] if ktcr[j] > 0 else pp
                else:
                    Ft = Ft - ctcr[j] * vt
                Fj = N * nrm + Ft
                Fc_tot += N
                ctx += Ft[0] * R[0, 0] + Ft[1] * R[1, 0] + Ft[2] * R[2, 0]
                F += Fj
                T += _cross(dp, Fj)
            else:
                cflag[j] = 0
        acc[15] = Fc_tot
        acc[36] = ctx
        Tb = R.T @ T
        if flex == 0:
            a_lin = F / m
            wd = Ibinv @ (Tb - _cross(w, Ib @ w))
            a_b = R.T @ a_lin
        else:
            gb = R.T @ gv
            Fb = R.T @ F
            ua = Gm @ al
            dmv = dm0 + ua
            Tb = Tb + mm * _cross(ua, gb)            # mast weight at the displaced CoM (composite CoM = ref at 0)
            Sr = _skew(dr); Sm = _skew(dmv)
            Mx = np.zeros((8, 8))
            for a in range(3):
                Mx[a, a] = mr + mm
            Mx[0:3, 3:6] = -mr * Sr - mm * Sm
            Mx[3:6, 0:3] = mr * Sr + mm * Sm
            Mx[3:6, 3:6] = Ir + Im + mr * (Sr.T @ Sr) + mm * (Sm.T @ Sm)
            Mx[0:3, 6:8] = mm * Gm
            Mx[6:8, 0:3] = mm * Gm.T
            Cm = mm * (Sm @ Gm) + Im @ E
            Mx[3:6, 6:8] = Cm
            Mx[6:8, 3:6] = Cm.T
            Mx[6:8, 6:8] = mm * (Gm.T @ Gm) + E.T @ Im @ E
            vrel = Gm @ ald
            wm = w + E @ ald
            cr_r = _cross(w, _cross(w, dr))
            cr_m = _cross(w, _cross(w, dmv)) + 2.0 * _cross(w, vrel)
            gyr_m = _cross(wm, Im @ wm) + Im @ _cross(w, E @ ald)
            rhs = np.zeros(8)
            rhs[0:3] = Fb - mr * cr_r - mm * cr_m
            rhs[3:6] = Tb - mr * _cross(dr, cr_r) - mm * _cross(dmv, cr_m) - _cross(w, Ir @ w) - gyr_m
            Qa = M0 - Ka * al - Ca * ald + mm * (Gm.T @ gb) - mm * gb[2] * hgt * al
            rhs[6:8] = Qa - mm * (Gm.T @ cr_m) - E.T @ gyr_m
            y = np.linalg.solve(Mx, rhs)
            a_b = y[0:3]; wd = y[3:6]
            a_lin = R @ a_b
            ald += dt * y[6:8]
            al += dt * ald
            for jj in range(2):
                if abs(al[jj]) > acc[39 + jj]:
                    acc[39 + jj] = abs(al[jj])
        rho = imu_rel
        a_imu_b = a_b + _cross(wd, rho) + _cross(w, _cross(w, rho))
        fb = a_imu_b - R.T @ gv
        acc[0] += fb[0]; acc[1] += fb[1]; acc[2] += fb[2]
        v += dt * a_lin
        w += dt * wd
        r += dt * v
        qw, qx, qy, qz = q[0], q[1], q[2], q[3]
        p_, q_, r_ = w[0], w[1], w[2]
        q[0] += dt * 0.5 * (-qx * p_ - qy * q_ - qz * r_)
        q[1] += dt * 0.5 * (qw * p_ + qy * r_ - qz * q_)
        q[2] += dt * 0.5 * (qw * q_ + qz * p_ - qx * r_)
        q[3] += dt * 0.5 * (qw * r_ + qx * q_ - qy * p_)
        nq = math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2)
        q /= nq
    acc[37] = al[0]; acc[38] = al[1]


_R = rcc._R
_cross = rcc._cross

# --------------------------------------------------------------------------------------------- equivalent mast


def mast_set(ms):
    """(mass, CoM, inertia about CoM) of every MastSystem mass (mast + attachments + auger + boom)."""
    m = sum(x[1] for x in ms.masses)
    c = sum(x[1] * x[2] for x in ms.masses) / m
    Ic = np.zeros((3, 3))
    for (_, mi, ci, I3, _) in ms.masses:
        d = ci - c
        Ic += I3 + mi * (d @ d * np.eye(3) - np.outer(d, d))
    return m, c, Ic


def g_matrix(c, P):
    """3x2: CoM displacement per unit alpha_x (about +x through P) and alpha_y (about +y through P)."""
    return np.column_stack([np.cross([1.0, 0, 0], c - P), np.cross([0, 1.0, 0], c - P)])


def alpha_mass(m, c, Ic, P):
    Gm = g_matrix(c, P)
    E = np.zeros((3, 2)); E[0, 0] = E[1, 1] = 1.0
    return m * Gm.T @ Gm + E.T @ Ic @ E


def equivalent_mast(level, support, boom, mast, zeta=(ZETA_NOM, ZETA_NOM)):
    kbs, kcy = SUPPORTS[support]
    ms = mbc.MastSystem(mast, level, boom=boom, k_bs=kbs, k_cyl=kcy)
    _, f, cls, fam = mbc.mast_only_table(mast, level, boom, k_bs=kbs, k_cyl=kcy)
    f_lat, f_fa = fam["LAT"][0], fam["FA"][0]
    m, c, Ic = mast_set(ms)
    P = np.array(ms.r_hinge, float)
    Ma = alpha_mass(m, c, Ic, P)
    h = c[2] - P[2]
    k = np.array([Ma[0, 0] * (2 * math.pi * f_lat) ** 2 + m * G * h, Ma[1, 1] * (2 * math.pi * f_fa) ** 2 + m * G * h])
    keff = k - m * G * h
    # mast-only check (2x2 generalised eigenproblem, incl. the small product of inertia)
    from scipy.linalg import eigh
    w2 = eigh(np.diag(keff), Ma, eigvals_only=True)
    cdamp = 2 * np.asarray(zeta) * np.sqrt(keff * np.diag(Ma))
    return {"level": level, "support": support, "k_bs_N_m": kbs, "k_cyl_N_m": kcy, "mass_kg": m, "com_m": c.tolist(),
            "inertia_about_com_kg_m2": Ic.tolist(), "pivot_m": P.tolist(), "h_com_above_pivot_m": h,
            "k_rot_N_m_rad": k.tolist(), "k_eff_N_m_rad": keff.tolist(), "M_alpha_kg_m2": Ma.tolist(),
            "c_rot_N_m_s_rad": cdamp.tolist(), "zeta": list(zeta),
            "target_mast_only_f_Hz (LAT, FA)": [f_lat, f_fa],
            "equivalent_mast_only_f_Hz": np.sort(np.sqrt(w2) / (2 * math.pi)).tolist(),
            "_ms": ms}


def eq_linear(l1, eq):
    """8-DoF linear equivalent [body 6 about the composite CoM | alpha_x, alpha_y] on an l1-like basis
    (M6, K6, C6 of the rigid 6-DoF). Returns M, K, C."""
    m = eq["mass_kg"]; c = np.array(eq["com_m"]); Ic = np.array(eq["inertia_about_com_kg_m2"]); P = np.array(eq["pivot_m"])
    ref = l1["body"].com
    Gm = g_matrix(c, P)
    B = np.zeros((6, 2)); B[:3] = Gm; B[3, 0] = B[4, 1] = 1.0
    Me = np.zeros((6, 6)); Me[:3, :3] = m * np.eye(3); Me[3:, 3:] = Ic
    A = mbc.a_off(c - ref)
    M = np.zeros((8, 8)); K = np.zeros((8, 8)); C = np.zeros((8, 8))
    M[:6, :6] = l1["M6"]; M[:6, 6:] = A.T @ Me @ B; M[6:, :6] = M[:6, 6:].T; M[6:, 6:] = B.T @ Me @ B
    K[:6, :6] = l1["K6"]
    K[6:, 6:] = np.diag(eq["k_rot_N_m_rad"]) - m * G * eq["h_com_above_pivot_m"] * np.eye(2)
    K[3, 6:] += m * G * Gm[1]; K[6:, 3] += m * G * Gm[1]
    K[4, 6:] += -m * G * Gm[0]; K[6:, 4] += -m * G * Gm[0]
    C[:6, :6] = l1["C6"]; C[6:, 6:] = np.diag(eq["c_rot_N_m_s_rad"])
    return M, K, C


def complex_modes(M, K, C, n=8):
    nd = M.shape[0]
    Minv = np.linalg.inv(M)
    A = np.block([[np.zeros((nd, nd)), np.eye(nd)], [-Minv @ K, -Minv @ C]])
    lam = np.linalg.eigvals(A)
    lam = lam[np.imag(lam) > 1e-9]
    wn = np.abs(lam); o = np.argsort(wn)
    return (wn[o] / (2 * math.pi))[:n], (-np.real(lam[o]) / wn[o])[:n]


# --------------------------------------------------------------------------------------------- nonlinear plant


class FlexPlant(ORIG_PLANT):
    """run_control_comparison.Plant with the 2-DoF equivalent mast (CONFIG['mast_eq'] None = rigid, physics_flex
    with flex = 0, identical to the original kernel). Variant knobs (diagnostics): kt_scale (pad tangential k, c),
    mu_pad, ktcr_scale (crawler tangential), mu_cr, fric_mode (pad friction decomposition 0 original / 1 Chrono L1,
    dynamics_model.md 3.15, rev. 26)."""

    def __init__(self, level="top", slope_roll_deg=0.0, slope_pitch_deg=0.0, beta=1.0e9, Fs=0.0, soft_FL=False,
                 dt=rcc.DT, init_ext=None):
        super().__init__(level, slope_roll_deg, slope_pitch_deg, beta, Fs, soft_FL, dt, init_ext)
        cfg = CONFIG
        self.acc = np.zeros(NACC)
        ks_ = float(cfg.get("kt_scale", 1.0))
        self.kt = self.kt * ks_; self.ct = self.ct * ks_
        self.mu_pad = float(cfg.get("mu_pad", self.mu))
        self.mu_cr = float(cfg.get("mu_cr", self.mu))
        kc_ = float(cfg.get("ktcr_scale", 1.0))
        self.ktcr = self.ktcr * kc_; self.ctcr = self.ctcr * kc_
        eq = cfg.get("mast_eq")
        self.al = np.zeros(2); self.ald = np.zeros(2)
        com = self.body.com
        if eq is None:
            self.flex = 0
            self.mr = self.m; self.dr = np.zeros(3); self.Ir = self.Ib.copy(); self.mm = 0.0
            self.dm0 = np.zeros(3); self.Gm = np.zeros((3, 2)); self.Im = np.zeros((3, 3))
            self.Ka = np.zeros(2); self.Ca = np.zeros(2); self.hgt = np.zeros(2); self.M0 = np.zeros(2)
        else:
            self.flex = 1
            mm = float(eq["mass_kg"]); c = np.array(eq["com_m"], float); Im = np.array(eq["inertia_about_com_kg_m2"])
            P = np.array(eq["pivot_m"], float)
            mr = self.m - mm
            cr = (self.m * com - mm * c) / mr
            dmv = c - com; drv = cr - com
            I_o = self.Ib - (Im + mm * (dmv @ dmv * np.eye(3) - np.outer(dmv, dmv)))     # rest about com
            Ir = I_o - mr * (drv @ drv * np.eye(3) - np.outer(drv, drv))
            if np.linalg.eigvalsh(Ir).min() <= 0:
                raise ValueError("rest-body inertia not positive definite")
            self.mr, self.dr, self.Ir, self.mm, self.dm0, self.Im = mr, drv, Ir, mm, dmv, Im
            self.Gm = g_matrix(c, P)
            self.Ka = np.array(eq["k_rot_N_m_rad"], float)
            self.Ca = np.array(eq["c_rot_N_m_s_rad"], float) * float(cfg.get("mast_c_scale", 1.0))
            self.hgt = np.full(2, c[2] - P[2])
            self.M0 = mm * G * self.Gm[2]          # alpha = 0 is the equilibrium with the body level
        self.hist_t = []; self.hist = []
        self.record = bool(cfg.get("record", False))
        self.fmode = int(cfg.get("fric_mode", getattr(self, "fmode", 0)))   # rev. 26 option, default 0
        self.tez = np.zeros(4)
        self.rec_hi = 45 if self.fmode == 0 else 53
        LAST["plant"] = self

    def step(self, u, nsteps):
        a = self.acc
        a[:11] = 0.0
        a[16:20] = -1e12; a[20:24] = 1e12
        a[24:28] = 1e12; a[39:41] = 0.0
        physics_flex(nsteps, self.dt, np.asarray(u, float), self.r, self.v, self.q, self.w, self.al, self.ald,
                     self.sref, self.x, self.f, self.panc, self.pflag, self.canc, self.cflag, self.m, self.Ib,
                     self.Ibinv, self.pad_rel, self.cr_rel, self.imu_rel, self.nrm, self.g, self.ko, self.ks, self.cn,
                     self.kt, self.ct, self.Wr, self.Fs, self.kcr, self.ccr, self.ktcr, self.ctcr, self.mu_pad,
                     self.mu_cr, self.geo.stroke, self.Fext, self.Fret, self.goff, self.flex, self.mr, self.dr,
                     self.Ir, self.mm, self.dm0, self.Gm, self.Im, self.Ka, self.Ca, self.hgt, self.M0, a,
                     self.fmode, self.tez)
        self.t += nsteps * self.dt
        if nsteps > 1000:          # crawler settle before the run (run_case resets t afterwards)
            self.hist_t = []; self.hist = []
        else:
            self.hist_t.append(self.t)
            self.hist.append(a[11:self.rec_hi].copy() if self.record else np.concatenate([a[24:28], a[39:41], a[15:16]]))
        return a[:24]               # run_c2_timedomain copies a 24-slot array (original layout)


rcc.Plant = FlexPlant           # this process only (run_c2_timedomain.run_case builds rcc.Plant(...))
import run_c2_timedomain as c2t  # noqa: E402  (after the patch; it reads rcc.Plant at call time anyway)
C2D_ORIG = c2t.C2D


class C2DRule(C2D_ORIG):
    """DIAGNOSTIC ONLY (cause study, not a design proposal of this script): C2D with a modified 'no retraction while
    the crawler may still bear load' rule of run_control_comparison.Controller.update (clearance estimate < 20 mm ->
    add pure heave). CONFIG['rule'] = 'filtered': the rule uses the 0.2 s low-passed clearance (clr_f, as the heave
    loop); 'latched': the rule is dropped for good once the raw estimate has exceeded 20 mm."""

    def update(self, m, t):
        mode = CONFIG.get("rule")
        if mode is None or self.phase == "touch" or self.done:
            return super().update(m, t)
        c = self.c
        raw_fn = c.clearance_est
        state = self

        def est(x):
            v = raw_fn(x)
            if mode == "latched":
                if v >= 0.02:
                    state.rule_off = True
                return 1.0 if getattr(state, "rule_off", False) else v
            return v

        idx_rule = 2 if self.lifted else 3   # Controller.update: [lifted check if not lifted], outer (heave), rule

        def est_rule(x):               # replaces only the call made by the no-retraction rule (last call per update)
            state.calls = getattr(state, "calls", 0) + 1
            if mode == "filtered" and state.calls == idx_rule and getattr(state, "clr_f", None) is not None:
                return state.clr_f
            if mode == "latched" and state.calls == idx_rule:
                return est(x)
            return raw_fn(x)
        self.calls = 0
        c.clearance_est = est_rule
        try:
            return super().update(m, t)
        finally:
            c.clearance_est = raw_fn

# --------------------------------------------------------------------------------------------- runs

SLOPES = [("flat", 0, 0), ("pitch+1", 0, 1), ("pitch+2", 0, 2), ("pitch+2.5", 0, 2.5), ("pitch+3", 0, 3),
          ("pitch+3.3", 0, 3.3), ("pitch+3.5", 0, 3.5), ("pitch+3.7", 0, 3.7), ("pitch-3", 0, -3), ("pitch-3.3", 0, -3.3), ("pitch-3.5", 0, -3.5),
          ("pitch-3.7", 0, -3.7),
          ("roll+1", 1, 0), ("roll+3", 3, 0), ("roll+4", 4, 0), ("roll+5", 5, 0), ("roll+5.7", 5.7, 0),
          ("diag1", 0.7071, 0.7071), ("diag2", 1.4142, 1.4142), ("diag2.5", 1.7678, 1.7678), ("diag2.8", 1.9799, 1.9799),
          ("diag3", 2.1213, 2.1213), ("diag3.2", 2.2627, 2.2627)]
SLOPE_ANG = {t: (ro, pi) for t, ro, pi in SLOPES}


def _run(kw):
    kw = dict(kw)
    cfg = kw.pop("cfg", {})
    CONFIG.clear(); CONFIG.update(cfg)
    rcc.Plant = FlexPlant        # re-assert the patch with THIS module's class (spawned workers also run __mp_main__)
    c2t.C2D = C2DRule if cfg.get("rule") else C2D_ORIG     # diagnostic controller variant (cause study only)
    tag = kw.pop("tag"); grp = kw.pop("group"); gs = kw.pop("gainset"); mast = kw.pop("mast")
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[gs])
    for k_, v_ in cfg.get("ca", {}).items():
        rcc.CA[k_] = v_
    t0 = time.perf_counter()
    try:
        r = c2t.run_case(keep_series=True, **kw)
        S = r.pop("_series")
        pl = LAST["plant"]
        if pl.flex != (0 if cfg.get("mast_eq") is None else 1):
            raise RuntimeError("plant flex flag does not match the case configuration")
        r["plant_flex"] = int(pl.flex)
        r.update(extra_metrics(S, r, pl))
        if cfg.get("keep_series"):
            r["_series"] = series_out(S, pl)
    except Exception as e:  # noqa: BLE001
        import traceback
        r = {"error": repr(e), "tb": traceback.format_exc()[-800:]}
    r.update({"slope": tag, "group": grp, "gainset": gs, "mast": mast, "seed": kw.get("seed"),
              "zeta_mast": cfg.get("zeta"), "variant": cfg.get("variant", ""), "wall_s": round(time.perf_counter() - t0, 1)})
    return r


def extra_metrics(S, r, pl):
    out = {}
    if not pl.hist:
        return out
    t = np.array(pl.hist_t); H = np.array(pl.hist)
    if pl.record:
        fmin = H[:, 13:17]; alabs = H[:, 28:30]          # a[24:28] -> idx 13..16, a[39:41] -> 28..29
    else:
        fmin = H[:, 0:4]; alabs = H[:, 4:6]
    tl = r.get("t_crawler_liftoff_s"); tt = r.get("t_touch_s")
    if tl is not None:
        post = t >= tl
        Ft = fmin[post] - pl.Wr
        j = int(np.argmin(Ft.min(axis=1)))
        out["min_true_cyl_force_substep_kN"] = round(float(Ft.min()) / 1e3, 2)
        out["min_true_leg_substep"] = dm.LEG_NAMES[int(np.argmin(Ft.min(axis=0)))]
        out["t_min_force_substep_s"] = round(float(t[post][j]), 3)
        out["t_min_after_liftoff_s"] = round(float(t[post][j] - tl), 3)
        # per-leg minimum force after lift-off (control samples, as min_true_cyl_force_kN)
        tc = S["t"]; postc = tc >= tl
        out["min_true_per_leg_kN"] = [round(float(v) / 1e3, 2) for v in S["Ftrue"][postc].min(axis=0)]
        if r.get("t_ready_s") is not None:
            lev = postc & (tc <= r["t_ready_s"])
            if lev.any():
                out["min_true_during_levelling_kN"] = round(float(S["Ftrue"][lev].min()) / 1e3, 2)
    if tt is not None:
        a = alabs[t >= tt]
        if len(a):
            out["mast_alpha_maxabs_deg (LAT x, FA y)"] = [round(float(v) * DEG, 4) for v in a.max(axis=0)]
    return out


def series_out(S, pl):
    t = np.array(pl.hist_t); H = np.array(pl.hist)
    keep = {"t": S["t"], "phi": S["phi"], "theta": S["theta"], "Ftrue": S["Ftrue"], "P": S["P"], "x": S["x"],
            "u": S["u"], "crawler_N": S["crawler_N"], "clr": S["clr"], "phi_m": S["phi_m"], "theta_m": S["theta_m"]}
    if pl.record and len(t):
        idx = np.searchsorted(t, S["t"] - 1e-9)
        idx = np.clip(idx, 0, len(t) - 1)
        Hs = H[idx]
        keep.update({"Fl": Hs[:, 0:4], "Ft_x": Hs[:, 17:21], "Ft_y": Hs[:, 21:25], "crawler_Ftx": Hs[:, 25],
                     "alpha": Hs[:, 26:28], "slip": Hs[:, 30:34]})
    return {k: np.asarray(v).tolist() for k, v in keep.items()}


# --------------------------------------------------------------------------------------------- verification


def verify_frozen_identity():
    """FlexPlant with flex = 0 vs the original kernel: same scenario (top, diag 3, proposal), bitwise state."""
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[c2t.PROPOSAL])
    CONFIG.clear()
    out = {}
    for name, cls in (("orig", ORIG_PLANT), ("flex0", FlexPlant)):
        pl = cls("top", 2.1213, 2.1213)
        if name == "orig":
            pl.acc = np.zeros(24)
        pl.step(np.zeros(4), 2000)
        u = np.array([0.02, 0.022, 0.018, 0.021])
        for _ in range(400):
            pl.step(u, 40)
        out[name] = np.concatenate([pl.r, pl.v, pl.q, pl.w, pl.x, pl.sref, pl.acc[11:16]])
    d = np.abs(out["orig"] - out["flex0"]).max()
    return {"max_abs_state_diff": float(d), "steps": 2000 + 400 * 40, "scenario": "top, roll 2.12 / pitch 2.12 deg, "
            "crawler settle 1 s then legs 18-22 mm/s for 8 s"}


def plant_jacobian(level, eq, settle_s=20.0, h=1e-7, dts=1e-8):
    """Numerical linearisation of the nonlinear kernel on a flat floor at the levelled e_op (pads only)."""
    CONFIG.clear(); CONFIG["mast_eq"] = eq
    geo = dm.geometry_from_params(dm.load_params())
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    pl = FlexPlant(level, init_ext=e_op)
    pl.step(np.zeros(4), int(settle_s / pl.dt))
    pl.v[:] = 0; pl.w[:] = 0; pl.ald[:] = 0
    base = {k: getattr(pl, k).copy() for k in ("r", "v", "q", "w", "al", "ald", "sref", "x", "f", "panc", "pflag",
                                                   "canc", "cflag")}
    nz = 8 if pl.flex else 6

    def accel(dx):
        for k, val in base.items():
            setattr(pl, k, val.copy())
        pl.r += dx[0:3]
        th = dx[3:6]; ang = np.linalg.norm(th)
        if ang > 0:
            dq = np.concatenate([[math.cos(ang / 2)], math.sin(ang / 2) * th / ang])
            pl.q[:] = rcc._qmul(pl.q, dq)
        if pl.flex:
            pl.al += dx[6:8]
        pl.v += dx[nz:nz + 3]; pl.w += dx[nz + 3:nz + 6]
        if pl.flex:
            pl.ald += dx[nz + 6:nz + 8]
        v0 = pl.v.copy(); w0 = pl.w.copy(); a0 = pl.ald.copy()
        dt0 = pl.dt; pl.dt = dts
        pl.step(np.zeros(4), 1)
        pl.dt = dt0
        out = np.concatenate([(pl.v - v0) / dts, (pl.w - w0) / dts] + ([(pl.ald - a0) / dts] if pl.flex else []))
        return out

    n = 2 * nz
    J = np.zeros((nz, n))
    for k in range(n):
        e = np.zeros(n); e[k] = h if k < nz else 1e-6
        J[:, k] = (accel(e) - accel(-e)) / (2 * e[k])
    A = np.zeros((n, n)); A[:nz, nz:] = np.eye(nz); A[nz:] = J
    lam = np.linalg.eigvals(A)
    lam = lam[np.imag(lam) > 1e-6]
    wn = np.abs(lam); o = np.argsort(wn)
    return (wn[o] / (2 * math.pi)), (-np.real(lam[o]) / wn[o])


def cl_basis(level):
    import c2_linear as cl
    lp = cl.build_plant(cl.PlantCase(level=level))
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    return {"body": dm.body_with_rods(p, geo, level, e_op), "M6": lp.M, "K6": lp.K, "C6": lp.Cd}


# --------------------------------------------------------------------------------------------- main


def load_boom():
    with open(mbc.PARTS_CSV, encoding="utf-8-sig") as f:
        rec = next(rw for rw in csv.DictReader(f) if rw["instance_path"] == mbc.BOOM_PART)
    return (float(rec["mass_step_kg"]), np.array([float(rec["centroid_z_mm"]), float(rec["centroid_x_mm"]),
                                                  float(rec["centroid_y_mm"])]) / 1e3)


def public(eq):
    return {k: v for k, v in eq.items() if not k.startswith("_")}


def calibration(p, geo, ref, mast, boom):
    """Equivalent parameters + checks against the detailed model (frequencies, 3.9.5 transients)."""
    from scipy.linalg import eigh
    out = {}
    eqs = {}
    for lv in dm.LEVELS:
        l1 = mbc.l1_setup(p, geo, ref, lv)
        for sup in SUPPORTS:
            eq = equivalent_mast(lv, sup, boom, mast)
            ms = eq["_ms"]
            Mf, Kf = mbc.coupled_modes(ms, l1, nmodes=14)[3:5]
            w2f, Phif = eigh(Kf, Mf)
            ff = np.sqrt(np.clip(w2f, 0, None)) / (2 * math.pi)
            Me, Ke, Ce = eq_linear(l1, eq)
            w2e, Phie = eigh(Ke, Me)
            fe = np.sqrt(np.clip(w2e, 0, None)) / (2 * math.pi)
            # rocking modes: MAC on the body coordinates vs the rigid L1 modes (8-DoF eq. model)
            tre = mbc.mac_track(l1, Phie, Me)
            rock_e = [float(fe[t[2]]) for t in tre[:2]]
            rock_f_doc = mbc_doc_coupled(lv, sup)
            ent = public(eq)
            ent.update({"coupled_rocking_eq_Hz": rock_e, "coupled_rocking_detailed_doc_Hz (3.9.3)": rock_f_doc,
                        "coupled_rocking_rel_err": [rock_e[i] / rock_f_doc[i] - 1 for i in range(2)],
                        "lowest8_eq_Hz": fe[:8].tolist(), "lowest8_detailed_Hz": ff[:8].tolist(),
                        "mac_eq": [t[3] for t in tre[:2]]})
            out[f"{lv}_{sup}"] = ent
            eqs[(lv, sup)] = eq
    # transients of 3.9.5 (top): detailed vs equivalent (zeta matched to the stiffness-proportional detailed model)
    l1 = mbc.l1_setup(p, geo, ref, "top")
    l1c = mbc.l1_setup(p, geo, ref, "top", lifted=False)
    T_rel = 15.584 - 15.050
    tr = {}
    rig = (l1["M6"], l1["K6"], l1["C6"])
    r_stop = mbc.stop_metrics(mbc.simulate_stop(rig, l1, geo))
    r_rel = mbc.stop_metrics(mbc.simulate_release(rig, l1, l1c, geo, T_rel))
    tr["rigid_L1"] = {"leg_stop_dev_N": r_stop["max_abs_pad_force_dev_from_quasi_static_N"],
                      "release_dev_N": r_rel["max_abs_pad_force_dev_from_quasi_static_N"]}
    for sup in SUPPORTS:
        eq0 = eqs[("top", sup)]; ms = eq0["_ms"]
        fm = ms.modes(nmodes=2)[0]
        M, K, _ = mbc.coupled(ms, l1)
        C = mbc.damping_coupled(ms, l1, 2 * ZETA_NOM / (2 * np.pi * fm[0]))
        f_lat, f_fa = eq0["target_mast_only_f_Hz (LAT, FA)"]
        zfa = ZETA_NOM * f_fa / f_lat if f_lat < f_fa else ZETA_NOM
        zla = ZETA_NOM if f_lat < f_fa else ZETA_NOM * f_lat / f_fa
        eqm = equivalent_mast("top", sup, boom, mast, zeta=(zla, zfa))
        Me, Ke, Ce = eq_linear(l1, eqm)
        row = {"zeta_eq (LAT, FA) matched to beta K": [zla, zfa]}
        for key, fun in (("leg_stop", lambda s_: mbc.simulate_stop(s_, l1, geo)),
                         ("release", lambda s_: mbc.simulate_release(s_, l1, l1c, geo, T_rel))):
            d_full = mbc.stop_metrics(fun((M, K, C)))["max_abs_pad_force_dev_from_quasi_static_N"]
            d_eq = mbc.stop_metrics(fun((Me, Ke, Ce)))["max_abs_pad_force_dev_from_quasi_static_N"]
            r0 = tr["rigid_L1"]["leg_stop_dev_N" if key == "leg_stop" else "release_dev_N"]
            row[key] = {"detailed_N": d_full, "equivalent_N": d_eq, "eq_vs_detailed": d_eq / d_full - 1,
                        "ratio_vs_rigid_detailed": d_full / r0, "ratio_vs_rigid_equivalent": d_eq / r0}
        tr[sup] = row
    out["transients_top_3_9_5"] = tr
    return out, eqs


def mbc_doc_coupled(lv, sup):
    import c2_linear as cl
    return list(cl.MAST_COUPLED_HZ[lv][DOC_KEY[sup]])


def eq_case(eqs, lv, sup, zeta=None):
    """Picklable equivalent-mast dict for a case (None = rigid L1 mast); optional modal zeta override."""
    if sup == "rigid":
        return None
    e = public(eqs[(lv, sup)])
    if zeta is not None:
        sc = np.array(zeta) / np.array(e["zeta"])
        e = dict(e); e["c_rot_N_m_s_rad"] = (np.array(e["c_rot_N_m_s_rad"]) * sc).tolist(); e["zeta"] = list(zeta)
    return e


def case_list(eqs, quick=False):
    """Stage 'main': matrix (rigid at top only = regression to c2_design; stiff / upper / lower at all levels),
    sensitivities at top (upper / lower)."""
    cases = []
    gp = c2t.PROPOSAL
    lvls = ("top",) if quick else dm.LEVELS
    slopes = [s for s in SLOPES if s[0] in ("flat", "diag3", "pitch+3.7")] if quick else SLOPES
    for lv in lvls:
        for mast in (("rigid",) if lv == "top" else ()) + FLEX:
            for tag, ro, pi in slopes:
                cases.append(dict(gainset=gp, level=lv, roll=ro, pitch=pi, tag=tag, group="matrix", mast=mast,
                                  cfg={"mast_eq": eq_case(eqs, lv, mast), "zeta": None if mast == "rigid" else ZETA_NOM}))
    if quick:
        return cases
    key = [s for s in SLOPES if s[0] in ("pitch+3.5", "pitch+3.7", "diag2.8", "diag3", "diag3.2", "roll+5.7")]
    for mast in ("upper", "lower"):
        for z in (0.012, 0.023):
            for tag, ro, pi in key:
                cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, tag=tag, group=f"zeta{z}", mast=mast,
                                  cfg={"mast_eq": eq_case(eqs, "top", mast, (z, z)), "zeta": z}))
        for tag, ro, pi in key:
            cases.append(dict(gainset="it0_current", level="top", roll=ro, pitch=pi, tag=tag, group="gain_it0",
                              mast=mast, cfg={"mast_eq": eq_case(eqs, "top", mast), "zeta": ZETA_NOM}))
        for tag, ro, pi in [s for s in SLOPES if s[0] in ("flat", "roll+3", "diag3", "pitch+3.7")]:
            cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, damping_scale=1 / 3, tag=tag,
                              group="leg_damp_1/3", mast=mast, cfg={"mast_eq": eq_case(eqs, "top", mast), "zeta": ZETA_NOM}))
        for tag, ro, pi in [s for s in SLOPES if s[0] in ("flat", "diag3", "pitch+3.7")]:
            for fs in (5e3, 12e3):
                cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, Fs=fs, contact="combined", tag=tag,
                                  group=f"seal{fs / 1e3:g}_combined", mast=mast,
                                  cfg={"mast_eq": eq_case(eqs, "top", mast), "zeta": ZETA_NOM}))
    return cases


ROBUST_TOP = ("pitch+3", "pitch+3.3", "pitch+3.5", "pitch+3.7", "pitch-3", "pitch-3.3", "pitch-3.5", "roll+5",
              "roll+5.7", "diag2.5", "diag2.8", "diag3", "diag3.2")
ROBUST_LOW = ("pitch+3.7", "pitch-3.5", "roll+5.7", "diag3.2")
N_SEEDS = 3


def case_list_robust(eqs):
    """Stage 'robust': seeds 12345..12347 x extra delay 1 / 0 steps (it3_proposal / _d0), beta 0.69 / 1.6 (seed
    12345, delay 1); rigid L1 and the three supports; top = ROBUST_TOP, middle / bottom = ROBUST_LOW.
    Plus the cause study (contact variants, rule diagnostic) on the rigid mast."""
    cases = []
    gp = c2t.PROPOSAL
    for lv, tags in (("top", ROBUST_TOP), ("middle", ROBUST_LOW), ("bottom", ROBUST_LOW)):
        for mast in ("rigid",) + FLEX:
            base = {"mast_eq": eq_case(eqs, lv, mast), "zeta": None if mast == "rigid" else ZETA_NOM}
            for tag in tags:
                ro, pi = SLOPE_ANG[tag]
                for gs in (gp, "it3_proposal_d0"):
                    for s in range(N_SEEDS):
                        cases.append(dict(gainset=gs, level=lv, roll=ro, pitch=pi, tag=tag, group="robust_seed",
                                          mast=mast, seed=12345 + s, cfg=dict(base)))
                if lv == "top":
                    for b in (0.69e9, 1.6e9):
                        cases.append(dict(gainset=gp, level=lv, roll=ro, pitch=pi, beta=b, tag=tag,
                                          group="robust_beta", mast=mast, cfg=dict(base)))
    # cause study (Q2): rigid mast, top, diagnostic contact variants (record pad tangential forces)
    variants = {"base": {}, "pad_kt_x0.01": {"kt_scale": 0.01}, "pad_no_slip_mu5": {"mu_pad": 5.0},
                "crawler_kt_x0.01": {"ktcr_scale": 0.01}, "crawler_no_slip_mu5": {"mu_cr": 5.0}}
    for vn, vv in variants.items():
        for gs in (gp, "it3_proposal_d0"):
            for tag in ("pitch+3.7", "pitch+3.5", "diag3.2"):
                ro, pi = SLOPE_ANG[tag]
                cfg = {"mast_eq": None, "variant": vn, "record": True}
                cfg.update(vv)
                cases.append(dict(gainset=gs, level="top", roll=ro, pitch=pi, tag=tag, group="cause", mast="rigid",
                                  cfg=cfg))
    for rule in ("filtered", "latched"):
        for tag in ("pitch+3.7", "pitch+3.5", "pitch+3.3", "diag3.2"):
            ro, pi = SLOPE_ANG[tag]
            for gs in (gp, "it3_proposal_d0"):
                for s in range(N_SEEDS):
                    cases.append(dict(gainset=gs, level="top", roll=ro, pitch=pi, tag=tag, group="rule_diag",
                                      mast="rigid", seed=12345 + s,
                                      cfg={"mast_eq": None, "rule": rule, "variant": f"rule_{rule}"}))
    return cases


KEEP = ("gainset", "group", "mast", "plant_flex", "variant", "zeta_mast", "seed", "slope", "level", "beta_GPa", "Fs_kN", "contact",
        "damping_scale", "t_touch_s", "t_crawler_liftoff_s", "t_ready_s", "t_level_after_touch_s", "t_within_target_s",
        "ss_true_att_deg_maxabs", "min_true_cyl_force_kN", "min_true_leg", "min_true_cyl_force_substep_kN",
        "min_true_leg_substep", "t_min_force_substep_s", "t_min_after_liftoff_s", "min_true_per_leg_kN",
        "min_true_during_levelling_kN", "min_pressure_reading_kN", "t_below_Fmin_true_s", "max_pressure_bar",
        "levelled_loads_true_kN", "rocking_peak_deg", "overshoot_true_deg", "guard_active_s",
        "mast_alpha_maxabs_deg (LAT x, FA y)", "probe_rounds", "fails", "events", "error", "tb", "wall_s")


def compact(r):
    if r.get("t_ready_s") is not None and r.get("t_touch_s") is not None:
        r["t_level_after_touch_s"] = round(r["t_ready_s"] - r["t_touch_s"], 2)
    return {k: r[k] for k in KEEP if k in r and r[k] is not None}


def series_case(level, tag, mast, eqs, gs=None, variant=None, seed=None):
    ro, pi = SLOPE_ANG[tag]
    cfg = {"mast_eq": None if mast == "rigid" else public(eqs[(level, mast)]), "record": True, "keep_series": True}
    if variant:
        cfg.update(variant)
    kw = dict(gainset=gs or c2t.PROPOSAL, level=level, roll=ro, pitch=pi, tag=tag, group="series", mast=mast, cfg=cfg)
    if seed is not None:
        kw["seed"] = seed
    return _run(kw)


def summarise(runs):
    out = {}
    F_min = F_MIN_KN
    for r in runs:
        if r.get("group") != "matrix":
            continue
        key = f"{r['level']}:{r['mast']}"
        e = out.setdefault(key, {"runs": 0, "pass": 0, "fail_cases": [], "min_force_kN": {}, "t_level_max_s": 0.0,
                                 "ss_max_deg": 0.0, "max_bar": 0.0})
        e["runs"] += 1
        if not r.get("fails") and "error" not in r:
            e["pass"] += 1
        else:
            e["fail_cases"].append(f"{r['slope']}:{'/'.join(r.get('fails', []))}{r.get('error', '')}")
        e["min_force_kN"][r["slope"]] = r.get("min_true_cyl_force_kN")
        e["t_level_max_s"] = max(e["t_level_max_s"], r.get("t_level_after_touch_s", 0.0) or 0.0)
        e["ss_max_deg"] = max(e["ss_max_deg"], r.get("ss_true_att_deg_maxabs", 0.0) or 0.0)
        e["max_bar"] = max(e["max_bar"], r.get("max_pressure_bar", 0.0) or 0.0)
    # slope limit per direction / level / mast: largest tested slope with min force >= F_min + margin (no fails)
    lim = {}
    dirs = {"pitch+": [t for t, _, _ in SLOPES if t.startswith("pitch+")],
            "pitch-": [t for t, _, _ in SLOPES if t.startswith("pitch-")],
            "roll+": [t for t, _, _ in SLOPES if t.startswith("roll+")], "diag": [t for t, _, _ in SLOPES if t.startswith("diag")]}
    for key, e in out.items():
        for d, tags in dirs.items():
            ok = [float(t.split("+")[-1].split("-")[-1].replace("diag", "")) for t in tags
                  if e["min_force_kN"].get(t) is not None and e["min_force_kN"][t] >= F_min
                  and not any(fc.startswith(t + ":") for fc in e["fail_cases"])]
            first_fail = [t for t in tags if any(fc.startswith(t + ":") for fc in e["fail_cases"])]
            lim.setdefault(key, {})[d] = {"max_pass_deg": max(ok) if ok else None, "fails": first_fail}
    return out, lim


def figures(series, runs, stem):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paths = []
    F_min = F_MIN_KN
    cols = {"rigid": "#7f7f7f", "stiff": "#2ca02c", "upper": "#1f77b4", "lower": "#d62728"}
    # 1. time series: top diag 3 / pitch +3.7, min true cyl force and attitude, rigid / upper / lower
    fig, ax = plt.subplots(3, 2, figsize=(12, 9), sharex="col")
    for j, tag in enumerate(("diag3", "pitch+3.7")):
        for mast in ("rigid",) + FLEX:
            S = series.get(("top", tag, mast))
            if S is None:
                continue
            t = np.array(S["t"]); Ft = np.array(S["Ftrue"]) / 1e3
            ax[0, j].plot(t, Ft.min(axis=1), color=cols[mast], lw=0.9, label=f"mast {mast}")
            ax[1, j].plot(t, np.degrees(S["phi"]), color=cols[mast], lw=0.9)
            ax[1, j].plot(t, np.degrees(S["theta"]), color=cols[mast], lw=0.9, ls="--")
            if "alpha" in S:
                al = np.degrees(np.array(S["alpha"]))
                ax[2, j].plot(t, al[:, 0], color=cols[mast], lw=0.8)
                ax[2, j].plot(t, al[:, 1], color=cols[mast], lw=0.8, ls="--")
        ax[0, j].axhline(F_min, color="k", ls=":", lw=0.8)
        ax[0, j].set_ylim(0, 130); ax[0, j].set_ylabel("min true cylinder force [kN]")
        ax[0, j].set_title(f"top auger, ground {tag}: C2 proposal (delay 1, ramp 0.1 s)", fontsize=9)
        ax[0, j].legend(fontsize=8)
        ax[1, j].set_ylabel("true roll (solid) / pitch (dashed) [deg]")
        ax[2, j].set_ylabel("mast rel. rotation LAT (solid) / FA (dashed) [deg]")
        ax[2, j].set_xlabel("time from leg start [s]")
        ax[2, j].set_xlim(12, 45)
        for a in ax[:, j]:
            a.grid(alpha=0.3)
    fig.tight_layout()
    p = OUT_DIR / f"{stem}_timeseries.png"; fig.savefig(p, dpi=90); plt.close(fig); paths.append(p)
    # 2. slope map: min true force vs slope magnitude, per direction, level, mast
    fig, ax = plt.subplots(3, 4, figsize=(14, 9), sharey=True)
    dirs = [("pitch+", lambda t: t.startswith("pitch+")), ("pitch-", lambda t: t.startswith("pitch-")),
            ("roll+", lambda t: t.startswith("roll+")), ("diag (roll+, pitch+)", lambda t: t.startswith("diag"))]
    for i, lv in enumerate(dm.LEVELS):
        for j, (dn, sel) in enumerate(dirs):
            a = ax[i, j]
            for mast in ("rigid",) + FLEX:
                rr = sorted([r for r in runs if r.get("group") == "matrix" and r.get("level") == lv and r.get("mast") == mast
                             and (sel(r["slope"]) or r["slope"] == "flat")],
                            key=lambda r: math.hypot(*SLOPE_ANG[r["slope"]]))
                xs = [math.hypot(*SLOPE_ANG[r["slope"]]) for r in rr]
                ys = [max(-2.0, r.get("min_true_cyl_force_kN", -2.0) or -2.0) for r in rr]
                a.plot(xs, ys, "o-", color=cols[mast], ms=3, lw=1, label=mast)
            a.axhline(F_min, color="k", ls=":", lw=0.8)
            a.set_title(f"{lv}, {dn}", fontsize=9); a.grid(alpha=0.3)
            if j == 0:
                a.set_ylabel("min true cyl. force after lift-off [kN]")
            if i == 2:
                a.set_xlabel("ground slope magnitude [deg]")
    ax[0, 0].legend(fontsize=8)
    fig.tight_layout()
    p = OUT_DIR / f"{stem}_slope_map.png"; fig.savefig(p, dpi=90); plt.close(fig); paths.append(p)
    # 3. cause (Q2): rigid top pitch +3.7: rear leg forces, tangential forces, crawler load, leg speeds
    S = series.get(("top", "pitch+3.7", "rigid"))
    S2 = series.get(("top", "pitch+3.7", "rigid_kt0.01"))
    if S is not None:
        fig, ax = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
        t = np.array(S["t"])
        F = np.array(S["Ftrue"]) / 1e3
        for k, nm in enumerate(dm.LEG_NAMES):
            ax[0].plot(t, F[:, k], lw=0.9, label=nm)
        if S2 is not None:
            F2 = np.array(S2["Ftrue"]) / 1e3
            ax[0].plot(np.array(S2["t"]), F2[:, 2:].min(axis=1), "k--", lw=0.8, label="rear min, pad k_t x0.01")
        ax[0].axhline(F_min, color="k", ls=":", lw=0.8)
        ax[0].set_ylabel("true cylinder force [kN]"); ax[0].legend(fontsize=8, ncol=5); ax[0].set_ylim(0, 200)
        ax[0].set_title("rigid mast, top, ground pitch +3.7 deg (front low), C2 proposal", fontsize=9)
        if "Ft_x" in S:
            Ftx = np.array(S["Ft_x"]) / 1e3
            for k, nm in enumerate(dm.LEG_NAMES):
                ax[1].plot(t, Ftx[:, k], lw=0.9, label=nm)
            ax[1].plot(t, np.array(S["crawler_Ftx"]) / 1e3, "k", lw=0.8, label="crawler sum")
            ax[1].set_ylabel("tangential force along body x [kN]"); ax[1].legend(fontsize=8, ncol=5)
        ax[2].plot(t, np.array(S["crawler_N"]) / 1e3, "k", lw=0.9)
        ax[2].set_ylabel("crawler normal force [kN]")
        U = np.array(S["u"]) * 1e3
        for k, nm in enumerate(dm.LEG_NAMES):
            ax[3].plot(t, U[:, k], lw=0.8, label=nm)
        ax[3].set_ylabel("applied leg speed [mm/s]"); ax[3].set_xlabel("time from leg start [s]")
        ax[3].set_xlim(13, 40)
        for a in ax:
            a.grid(alpha=0.3)
        fig.tight_layout()
        p = OUT_DIR / f"{stem}_cause.png"; fig.savefig(p, dpi=90); plt.close(fig); paths.append(p)
    return paths


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="pool smoke test (top, lower support, pitch +3.7)")
    ap.add_argument("--stage", choices=("main", "robust"), default="main",
                    help="main: calibration, verification, matrix, sensitivities, cause, figures (new JSON); "
                         "robust: seeds x delay, beta, rule diagnostic, merged into the existing JSON")
    args = ap.parse_args()
    cores = c2t.set_affinity()
    if args.stage == "robust":
        return robust_stage(args, cores)
    if args.selftest:
        eq = public(equivalent_mast("top", "lower", load_boom(), mbc.load_mast()))
        cs = [dict(gainset=c2t.PROPOSAL, level="top", roll=0, pitch=3.7, tag="pitch+3.7", group="selftest", mast=m_,
                   cfg={"mast_eq": e_}) for m_, e_ in (("rigid", None), ("lower", eq))]
        print(verify_frozen_identity())
        print(plant_jacobian("top", None)[0][:3], plant_jacobian("top", eq)[0][:3])
        r0 = _run(dict(cs[0]))
        print("main", r0.get("min_true_cyl_force_kN"), r0.get("mast_alpha_maxabs_deg (LAT x, FA y)"))
        from multiprocessing import Pool
        with Pool(2) as pool:
            for r_ in pool.map(_run, cs):
                print(r_["mast"], r_.get("min_true_cyl_force_kN"), r_.get("mast_alpha_maxabs_deg (LAT x, FA y)"), r_.get("error"))
        return
    t_start = time.perf_counter()
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    with open(mbc.REF_JSON, encoding="utf-8") as f:
        ref = json.load(f)
    mast = mbc.load_mast(); boom = load_boom()
    cal, eqs = calibration(p, geo, ref, mast, boom)
    ver = {"frozen_kernel_identity": verify_frozen_identity()}
    # linearisation of the nonlinear kernel vs the 8-DoF linear equivalent on the c2_linear basis
    lin = {}
    for lv in ("top", "bottom"):
        b6 = cl_basis(lv)
        f6, z6 = complex_modes(b6["M6"], b6["K6"], b6["C6"], 6)
        fj6, zj6 = plant_jacobian(lv, None)
        ent = {"rigid": {"linear_f_Hz": f6.tolist(), "kernel_f_Hz": fj6[:6].tolist(),
                         "linear_zeta": z6.tolist(), "kernel_zeta": zj6[:6].tolist()}}
        for sup in SUPPORTS:
            eq = public(eqs[(lv, sup)])
            M8, K8, C8 = eq_linear(b6, eq)
            f8, z8 = complex_modes(M8, K8, C8, 8)
            fj, zj = plant_jacobian(lv, eq)
            ent[sup] = {"linear_f_Hz": f8.tolist(), "kernel_f_Hz": fj[:8].tolist(), "linear_zeta": z8.tolist(),
                        "kernel_zeta": zj[:8].tolist(),
                        "max_rel_f_diff": float(np.max(np.abs(fj[:8] / f8 - 1)))}
        ent["rigid"]["max_rel_f_diff"] = float(np.max(np.abs(fj6[:6] / f6 - 1)))
        lin[lv] = ent
    ver["kernel_linearisation_vs_linear_equivalent"] = lin
    print("calibration + verification", round(time.perf_counter() - t_start, 1), "s", flush=True)
    cases = case_list(eqs, args.quick)
    _run(dict(cases[0]))            # compile / load the numba cache in the main process before the pool
    from multiprocessing import Pool
    with Pool(args.workers) as pool:
        raw = pool.map(_run, cases, chunksize=1)
    runs = [compact(r) for r in raw]
    print("runs", len(runs), round(time.perf_counter() - t_start, 1), "s", flush=True)
    # series for the figures (main process)
    series = {}
    for tag in ("diag3", "pitch+3.7"):
        for mast_ in ("rigid",) + FLEX:
            r = series_case("top", tag, mast_, eqs)
            series[("top", tag, mast_)] = r.get("_series")
    r = series_case("top", "pitch+3.7", "rigid", eqs, variant={"kt_scale": 0.01})
    series[("top", "pitch+3.7", "rigid_kt0.01")] = r.get("_series")
    r = series_case("top", "pitch+3.7", "rigid", eqs, gs="it3_proposal_d0")
    series[("top", "pitch+3.7", "rigid_d0")] = r.get("_series")
    stem = "mast_flex_c2_check" + ("_quick" if args.quick else "")
    figs = figures(series, runs, stem)
    summ, lim = summarise(runs)
    # compact cause-study series excerpt (rigid pitch +3.7): around the rear minimum
    excerpt = {}
    for key in (("top", "pitch+3.7", "rigid"), ("top", "pitch+3.7", "rigid_d0"), ("top", "pitch+3.7", "rigid_kt0.01")):
        S = series.get(key)
        if S is None:
            continue
        t = np.array(S["t"]); F = np.array(S["Ftrue"])
        cr = np.array(S["crawler_N"])
        tl = t[np.argmax((cr == 0) & (t > 10))]
        post = t >= tl
        j = int(np.argmin(np.where(post[:, None], F, np.inf).min(axis=1)))
        w = (t >= t[j] - 1.5) & (t <= t[j] + 1.0)
        sl = slice(None, None, 5)
        excerpt["/".join(key)] = {"t_liftoff_s": float(tl), "t_min_s": float(t[j]), "min_kN": float(F[j].min() / 1e3),
                                  "t": t[w][sl].round(3).tolist(), "Ftrue_kN": (F[w][sl] / 1e3).round(2).tolist(),
                                  "Ft_x_kN": (np.array(S["Ft_x"])[w][sl] / 1e3).round(2).tolist() if "Ft_x" in S else None,
                                  "slip": np.array(S["slip"])[w][sl].astype(int).tolist() if "slip" in S else None,
                                  "u_mm_s": (np.array(S["u"])[w][sl] * 1e3).round(2).tolist(),
                                  "theta_deg": np.degrees(np.array(S["theta"])[w][sl]).round(4).tolist(),
                                  "crawler_kN": (cr[w][sl] / 1e3).round(2).tolist()}
    res = {"meta": {"script": "04_scripts/01_dynamics/run_mast_flex_c2_check.py",
                    "doc": "00_docs/01_dynamics/dynamics_model.md 3.9.7 (revision 16)",
                    "argv": sys.argv[1:], "affinity": cores, "dt_s": rcc.DT, "T_ctrl_s": rcc.T_CTRL,
                    "gainsets_used": {k: c2t.GAINSETS[k] for k in (c2t.PROPOSAL, "it3_proposal_d0", "it0_current")},
                    "seed": rcc.CA["seed"], "F_min_kN": F_MIN_KN,
                    "frame": "body x fwd, y left, z up; gravity -9.80665 z_hat; pitch > 0 nose down; roll > 0 left up",
                    "assumptions": {
                        "equivalent_mast": "rigid mast set (mast+attachments+auger+boom) on 2 rotational springs about "
                                           "x / y axes through hinge H1; k from mast-only f1 (detailed model, P-delta)",
                        "zeta_mast": f"{ZETA_NOM} nominal on the mast-only modes, sensitivity 0.012 / 0.023",
                        "boom": "rolls and pitches with the mast set (detailed model: rolls only)",
                        "linear_relative_kinematics": "alpha small (< 0.2 deg); mast inertia orientation fixed",
                        "plant_rest": "run_control_comparison reduced model (L1 pads, crawler D, Coulomb bushings, "
                                      "symplectic Euler 5e-4 s), controller / sensors run_c2_timedomain (it3_proposal)"},
                    "figures": [str(pth.relative_to(ROOT)).replace("\\", "/") for pth in figs]},
           "calibration": mbc.r(cal), "verification": mbc.r(ver), "summary": summ, "slope_limits": lim,
           "cause_excerpt": excerpt, "runs": runs}
    res["meta"]["wall_s"] = round(time.perf_counter() - t_start, 1)
    out = OUT_JSON if not args.quick else OUT_DIR / "mast_flex_c2_check_quick.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print("wrote", out, res["meta"]["wall_s"], "s")
    print(json.dumps(summ, indent=0)[:4000])
    print(json.dumps(lim, indent=0))


def robust_stage(args, cores):
    t_start = time.perf_counter()
    mast = mbc.load_mast(); boom = load_boom()
    eqs = {(lv, sup): equivalent_mast(lv, sup, boom, mast) for lv in dm.LEVELS for sup in SUPPORTS}
    cases = case_list_robust(eqs)
    _run(dict(cases[0]))
    from multiprocessing import Pool
    with Pool(args.workers) as pool:
        raw = pool.map(_run, cases, chunksize=1)
    runs = [compact(r) for r in raw]
    env = {}
    for r in runs:
        if r["group"] not in ("robust_seed", "robust_beta"):
            continue
        d0 = r["gainset"] == "it3_proposal_d0"
        key = f"{r['level']}:{r['mast']}:{r['slope']}"
        e = env.setdefault(key, {"delay1_min_kN": None, "delay1_fails": 0, "delay1_runs": 0, "delay0_min_kN": None,
                                 "delay0_fails": 0, "delay0_runs": 0, "t_level_max_s": 0.0, "ss_max_deg": 0.0,
                                 "max_bar": 0.0, "fail_kinds": []})
        k = "delay0" if d0 else "delay1"
        v = r.get("min_true_cyl_force_kN")
        if v is not None:
            e[k + "_min_kN"] = v if e[k + "_min_kN"] is None else min(e[k + "_min_kN"], v)
        e[k + "_runs"] += 1
        if r.get("fails") or "error" in r:
            e[k + "_fails"] += 1
            e["fail_kinds"] = sorted(set(e["fail_kinds"]) | set(r.get("fails", [])) | ({"error"} if "error" in r else set()))
        e["t_level_max_s"] = max(e["t_level_max_s"], r.get("t_level_after_touch_s", 0.0) or 0.0)
        e["ss_max_deg"] = max(e["ss_max_deg"], r.get("ss_true_att_deg_maxabs", 0.0) or 0.0)
        e["max_bar"] = max(e["max_bar"], r.get("max_pressure_bar", 0.0) or 0.0)
    rule = {}
    for r in runs:
        if r["group"] == "rule_diag":
            rule.setdefault(f"{r['variant']}:{r['slope']}:{r['gainset']}", []).append(
                [r.get("min_true_cyl_force_kN"), r.get("t_min_after_liftoff_s"), r.get("fails", [])])
    with open(OUT_JSON, encoding="utf-8") as fh:
        res = json.load(fh)
    res["robustness"] = {"meta": {"argv": sys.argv[1:], "affinity": cores, "seeds": [12345 + s for s in range(N_SEEDS)],
                                  "top_slopes": ROBUST_TOP, "middle_bottom_slopes": ROBUST_LOW,
                                  "wall_s": round(time.perf_counter() - t_start, 1),
                                  "note": "delay1 = it3_proposal (seeds + beta 0.69 / 1.6 at seed 12345), "
                                          "delay0 = it3_proposal_d0 (seeds)"},
                         "envelope": env, "rule_diagnostic": rule, "runs": runs}
    figs = robust_figure(env)
    res["meta"].setdefault("figures", [])
    for pth in figs:
        rel = str(pth.relative_to(ROOT)).replace("\\", "/")
        if rel not in res["meta"]["figures"]:
            res["meta"]["figures"].append(rel)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print("robust", len(runs), "runs", res["robustness"]["meta"]["wall_s"], "s")
    for k_, v_ in env.items():
        print(k_, v_)
    for k_, v_ in rule.items():
        print(k_, v_)


def robust_figure(env):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"rigid": "#7f7f7f", "stiff": "#2ca02c", "upper": "#1f77b4", "lower": "#d62728"}
    dirs = [("pitch+ (front low)", "pitch+"), ("pitch- (front high)", "pitch-"), ("roll+ (left high)", "roll+"),
            ("diag (roll+, pitch+)", "diag")]
    fig, ax = plt.subplots(2, 4, figsize=(15, 7), sharey=True)
    for j, (dn, pre) in enumerate(dirs):
        for i, k in enumerate(("delay1", "delay0")):
            a = ax[i, j]
            for mast in ("rigid",) + FLEX:
                pts = sorted((math.hypot(*SLOPE_ANG[t]), env[f"top:{mast}:{t}"][k + "_min_kN"], env[f"top:{mast}:{t}"][k + "_fails"])
                             for t in ROBUST_TOP if t.startswith(pre) and f"top:{mast}:{t}" in env)
                if not pts:
                    continue
                xs = [p_[0] for p_ in pts]; ys = [max(-2.0, p_[1] if p_[1] is not None else -2.0) for p_ in pts]
                a.plot(xs, ys, "o-", color=cols[mast], ms=3, lw=1, label=mast)
                for x_, y_, f_ in pts:
                    if f_:
                        a.plot(x_, max(-2.0, y_ if y_ is not None else -2.0), "x", color=cols[mast], ms=9, mew=2)
            a.axhline(F_MIN_KN, color="k", ls=":", lw=0.8); a.axhline(F_MIN_KN + D8_FORCE_MARGIN_KN, color="k", ls="--", lw=0.6)
            a.set_title(f"top, {dn}, {'extra delay 1 step + beta' if k == 'delay1' else 'no extra delay'}", fontsize=8)
            a.grid(alpha=0.3)
            if j == 0:
                a.set_ylabel("worst min true cyl. force [kN] (x = a run failed)")
            if i == 1:
                a.set_xlabel("ground slope magnitude [deg]")
    ax[0, 0].legend(fontsize=8)
    fig.tight_layout()
    p = OUT_DIR / "mast_flex_c2_check_robust.png"
    fig.savefig(p, dpi=90); plt.close(fig)
    return [p]


if __name__ == "__main__":
    main()
