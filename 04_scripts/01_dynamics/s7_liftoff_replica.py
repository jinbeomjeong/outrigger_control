"""S7 control-3 prep: reduced replica of the crawler lift-off, compliant vs rigid crawler (dynamics_model.md 5.25).

Independent of Chrono and of 03_src. Nonlinear 6-DoF rigid body (superstructure top + 4 rods frozen at
the lift-off strokes), floor frame (floor plane z = crawler bottom ZF, gravity tilted by the Chrono
``floor_pose`` of the case), body quaternion wxyz (body -> floor frame), body angular velocity.

* crawler: the 24 spheres of YAML ``contact.crawler.sphere_layout`` (layout D); normal spring-dashpot
  max(0, k pen - c pen_dot) with k = kn_per_sphere x scale, c = c_sphere x sqrt(scale) (same zeta);
  tangential spring-dashpot to a floor anchor with circular Coulomb return mapping (mu 0.5),
  kt = Chrono L1 crawler bushing 1.942e6 N/m x scale_t (``crawler_bushings`` of the L1 case meta),
  ct = 7.92e3 N s/m x sqrt(scale_t). scale 1 = L1 (SMC crawler + crawler bushings); scale 1e3 .. 1e4 =
  rigid limit (stand-in for the L2b NSC crawler: rigid, stick friction mu 0.5).
* legs: pad normal spring-dashpot along the floor normal at the ball centre,
  N = max(0, k_pad pen + c_pad pen_dot), pen = R_pad - (z_ball - ZF), ball = ball_retracted - (s + delta) z_body;
  k_pad = YAML L1 kn_per_pad (fixed, e_op), c_pad = L1 cn_per_pad (LOCK) or the L2b moving value;
  tangential: L1 pad bushing (kt_per_pad, ct_per_pad) with Coulomb mu 0.5. Rods laterally rigid (L1).
* drive: Chrono 1 ms ``pads.s_motor`` of one engine (L1 motor position / L2b force-law s_ref), linear
  interpolation, s_dot = central difference. Per-leg stroke offset delta (4): replica touch stroke (body
  settled on the drive engine's own crawler, x1 for L1 / x1000 for L2b) minus the Chrono stroke at the
  Chrono first pad contact (pad N > 500 N); absorbs the mm-level geometric offsets. The swap runs (drive
  of one engine on another crawler) keep the drive engine's offsets. The pad loads at TOUCH end - 0.2 s
  are reported against Chrono as a check (not fitted).
* integration: semi-implicit (symplectic) Euler, dt 1e-4 s (scale <= 10), 5e-5 s (100 .. 1e3),
  2e-5 s (1e4); settle 1.5 s on the crawler (added body damper 30 1/s, no slip) with the strokes of
  t_s = first Chrono contact - 0.3 s (pads clear), then the drive from t_s to lift-off + 6 s without the
  damper, mu 0.5. Record 1 ms.

Metrics as ``s7_liftoff_transient.py`` (same band-passes); the modal basis is the linear 6-DoF L1 model
at the replica lift-off geometry. Floor frame z up, g = 9.80665 m/s^2. Units SI, kN / J in the output.

Run (project root, dynamics-dev)::

    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s7_liftoff_replica.py [--workers N]
Writes 06_analysis/00_dynamics/s7_liftoff_replica.json (+ .png).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from numba import njit
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import s7_liftoff_transient as lt  # noqa: E402

P = lt.P
GEO = lt.GEO
LEGS = dm.LEG_NAMES
G = float(P["meta"]["gravity_m_s2"])
ZF = lt.ZF
LAY = P["contact"]["crawler"]["sphere_layout"]
RAD = float(LAY["sphere_radius_m"])
KN_SPH = float(P["contact"]["crawler"]["kn_per_sphere_N_m"])
N_ROL = 2 * len(LAY["roller_x_m"])
C_SPH = float(P["contact"]["crawler"]["damping_total_N_s_m"]) / N_ROL
KT_SPH = 1942437.5460074937  # L1 case meta crawler_bushings.kt_N_m (ASSUMPTION, Q12 option)
CT_SPH = 7920.979376872223   # L1 case meta crawler_bushings.ct_N_s_m (actual)
MU = float(P["contact"]["rigid_floor"]["friction"])
L1Y = P["contact"]["rigid_floor"]["L1"]
K_PAD = np.array([float(L1Y["kn_per_pad_N_m"][n]) for n in LEGS])
C_PAD = np.array([float(L1Y["cn_per_pad_N_s_m"][n]) for n in LEGS])
C_PAD_MOV = np.array([100206.06547702239, 100206.06547702239, 86949.01443833958, 86949.01443833958])  # L2b meta
KT_PAD = np.array([float(L1Y["bushing_stiffness_per_pad_N_m"][n]) for n in LEGS])
CT_PAD = np.array([float(L1Y["ct_per_pad_N_s_m"][n]) for n in LEGS])
R_PAD = float(P["legs"]["FL"]["pad"]["swivel_center_above_pad_bottom_m"])
OUT = ROOT / "06_analysis" / "00_dynamics" / "s7_liftoff_replica.json"
SETTLE_S, SETTLE_DAMP = 1.5, 30.0
MU_SETTLE = 1e6  # no slip while settling (smooth in the stroke offsets); the drive uses MU with the settled anchors


def crawler_centres():
    yc = float(LAY["track_centre_y_m"])
    pts = []
    for y in (yc, -yc):
        for x in LAY["roller_x_m"]:
            pts.append((x, y, ZF + RAD))
        for x, g in zip(LAY["end_shoe_x_m"], LAY["end_shoe_gap_m"]):
            pts.append((x, y, ZF + g + RAD))
    return np.array(pts, float)


C_CR = crawler_centres()
PAD_BALL0 = np.column_stack([GEO.pad_xy, GEO.pad_z_retracted + R_PAD])


@njit(cache=False)
def _qmat(q):
    w, x, y, z = q[0], q[1], q[2], q[3]
    R = np.empty((3, 3))
    R[0, 0] = 1 - 2 * (y * y + z * z); R[0, 1] = 2 * (x * y - w * z); R[0, 2] = 2 * (x * z + w * y)
    R[1, 0] = 2 * (x * y + w * z); R[1, 1] = 1 - 2 * (x * x + z * z); R[1, 2] = 2 * (y * z - w * x)
    R[2, 0] = 2 * (x * z - w * y); R[2, 1] = 2 * (y * z + w * x); R[2, 2] = 1 - 2 * (x * x + y * y)
    return R


@njit(cache=False)
def _cross(a, b):
    return np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])


@njit(cache=False)
def _contact(p, v, pen, k, c, kt, ct, mu, anc):
    """Normal + tangential force (floor frame) of one point; anchor (2,) updated in place."""
    f = np.zeros(3)
    if pen <= 0.0:
        anc[0] = p[0]; anc[1] = p[1]
        return f, 0.0
    N = k * pen - c * v[2]
    if N < 0.0:
        N = 0.0
    fx = -kt * (p[0] - anc[0]); fy = -kt * (p[1] - anc[1])
    fm = math.sqrt(fx * fx + fy * fy)
    cap = mu * N
    if fm > cap:
        s = cap / fm
        fx *= s; fy *= s
        if kt > 0:
            anc[0] = p[0] + fx / kt; anc[1] = p[1] + fy / kt
    else:
        fx -= ct * v[0]; fy -= ct * v[1]
        fm2 = math.sqrt(fx * fx + fy * fy)
        if fm2 > cap:
            fx *= cap / fm2; fy *= cap / fm2
    f[0] = fx; f[1] = fy; f[2] = N
    return f, N


@njit(cache=False)
def simulate(t0, t1, dt, x, q, v, w, anc_c, anc_p, s_tab, sd_tab, tab_t0, tab_dt, delta,
             crb, padb, kc, cc, ktc, ctc, kp, cp, ktp, ctp, mu, m, I, Iinv, gf, damp, rec_dt, zf, rad, rpad):
    n = int(round((t1 - t0) / dt))
    every = max(1, int(round(rec_dt / dt)))
    nrec = n // every + 1
    out_t = np.empty(nrec); out_N = np.empty((nrec, 4)); out_Nc = np.empty(nrec)
    out_wb = np.empty((nrec, 6)); out_cr = np.empty((nrec, 6)); out_x = np.empty((nrec, 7))
    ir = 0
    ntab = s_tab.shape[0]
    zb = np.zeros(3)
    for k in range(n + 1):
        t = t0 + k * dt
        u = (t - tab_t0) / tab_dt
        j = int(math.floor(u))
        if j < 0:
            j = 0; fr = 0.0
        elif j >= ntab - 1:
            j = ntab - 2; fr = 1.0
        else:
            fr = u - j
        R = _qmat(q)
        wW = R @ w
        Fpad = np.zeros(3); Mpad = np.zeros(3); Fcr = np.zeros(3); Mcr = np.zeros(3)
        Nc_sum = 0.0
        Npad = np.zeros(4)
        for i in range(crb.shape[0]):
            r = R @ crb[i]
            p = x + r
            vp = v + _cross(wW, r)
            pen = rad - (p[2] - zf)
            f, N = _contact(p, vp, pen, kc, cc, ktc, ctc, mu, anc_c[i])
            Nc_sum += N
            Fcr += f; Mcr += _cross(r, f)
        zb[0] = R[0, 2]; zb[1] = R[1, 2]; zb[2] = R[2, 2]
        for i in range(4):
            s = s_tab[j, i] * (1 - fr) + s_tab[j + 1, i] * fr + delta[i]
            sd = sd_tab[j, i] * (1 - fr) + sd_tab[j + 1, i] * fr
            r = R @ padb[i] - s * zb
            p = x + r
            vp = v + _cross(wW, r) - sd * zb
            pen = rpad - (p[2] - zf)
            f, N = _contact(p, vp, pen, kp[i], cp[i], ktp[i], ctp[i], mu, anc_p[i])
            Npad[i] = N
            Fpad += f; Mpad += _cross(r, f)
        Ftot = Fcr + Fpad + m * gf - damp * m * v
        tb = R.T @ (Mcr + Mpad) - damp * (I @ w)
        if k % every == 0 and ir < nrec:
            out_t[ir] = t; out_N[ir] = Npad; out_Nc[ir] = Nc_sum
            out_wb[ir, 0:3] = R.T @ Fpad; out_wb[ir, 3:6] = R.T @ Mpad
            out_cr[ir, 0:3] = R.T @ Fcr; out_cr[ir, 3:6] = R.T @ Mcr
            out_x[ir, 0:3] = x; out_x[ir, 3:7] = q
            ir += 1
        v = v + dt * Ftot / m
        x = x + dt * v
        w = w + dt * (Iinv @ (tb - _cross(w, I @ w)))
        wn = math.sqrt(w[0] * w[0] + w[1] * w[1] + w[2] * w[2])
        if wn > 0:
            a = 0.5 * dt * wn
            sa = math.sin(a) / wn
            d0, d1, d2, d3 = math.cos(a), w[0] * sa, w[1] * sa, w[2] * sa
            q = np.array([q[0] * d0 - q[1] * d1 - q[2] * d2 - q[3] * d3,
                          q[0] * d1 + q[1] * d0 + q[2] * d3 - q[3] * d2,
                          q[0] * d2 - q[1] * d3 + q[2] * d0 + q[3] * d1,
                          q[0] * d3 + q[1] * d2 - q[2] * d1 + q[3] * d0])
            q = q / math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2)
    return out_t[:ir], out_N[:ir], out_Nc[:ir], out_wb[:ir], out_cr[:ir], out_x[:ir], x, q, v, w


def load_case(pair, eng):
    suf, b1, b2 = lt.PAIRS[pair]
    B = ROOT / (b1 if eng == "L1" else b2)
    case = f"{eng}_{suf}"
    vj = json.loads((B / "verify_S7C.json").read_text(encoding="utf-8"))
    tm = {m["case"]: m for m in vj["metrics"]}[case]["times_s"]
    cj = json.loads((B / case / "case.json").read_text(encoding="utf-8"))
    fq = np.array(cj["run_meta"]["engine"]["floor_pose"]["quat_wxyz"], float)
    p = np.load(B / case / "pads.npz")
    t = p["t"] - tm["t0"]
    sel = (t >= tm["touch"] - 8.0) & (t <= tm["liftoff"] + 8.0)
    Fc = p["F_cyl_min_interval"][sel]
    return {"case": case, "tm": tm, "floor_q": fq, "t": t[sel], "s": p["s_motor"][sel], "N": p["N"][sel],
            "Fcyl": Fc}


def modal_basis(bw, padb_s, F0):
    """Mass-normalised modes of the linear 6-DoF L1 model (q about the CoM, body frame)."""
    M = dm.mass_6dof(bw)
    K = np.zeros((6, 6))
    for i in range(4):
        ax, ay, az = dm.a_vec(padb_s[i])
        K += K_PAD[i] * np.outer(az, az) + KT_PAD[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        K[3:, 3:] -= F0[i] * dm._hz(padb_s[i])
    w2, f, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
    return f, Phi, cls


def liftoff_time(t, Nc, tmax):
    on = np.where((Nc > 0.0) & (t <= tmax))[0]
    return float(t[on[-1] + 1]) if len(on) and on[-1] + 1 < len(t) else math.nan


def metrics(t, N, Nc, wb, cr, lo, bw, padb_s, W):
    """Release, band and modal metrics (t relative to the same origin as lo)."""
    fs = 1.0 / np.median(np.diff(t))
    out = {"liftoff_s": lo}
    for d in (1.0, 0.5, 0.2, 0.1, 0.05):
        k = int(np.argmin(np.abs(t - (lo - d))))
        fz = cr[k, 2]
        cop = None
        if fz > 2e3:
            zc = ZF - bw.com[2]
            cop = [float(-(cr[k, 4] - zc * cr[k, 0]) / fz + bw.com[0]), float((cr[k, 3] + zc * cr[k, 1]) / fz + bw.com[1])]
        out[f"Nc_minus_{d:g}_kN"] = float(Nc[k] / 1e3)
        out[f"Fh_minus_{d:g}_kN"] = float(np.hypot(cr[k, 0], cr[k, 1]) / 1e3)
        out[f"cop_minus_{d:g}"] = cop
    a03 = (t >= lo) & (t <= lo + 3.0)
    a36 = (t >= lo + 3.0) & (t <= lo + 6.0)
    sos2 = butter(4, [1.0, 4.0], btype="band", fs=fs, output="sos")
    fo = sosfiltfilt(sos2, N, axis=0)
    out["band_halfamp_0_3_kN"] = ((fo[a03].max(0) - fo[a03].min(0)) / 2e3).tolist()
    out["band_halfamp_3_6_kN"] = ((fo[a36].max(0) - fo[a36].min(0)) / 2e3).tolist()
    late = (t >= lo + 4.0) & (t <= lo + 6.0)
    f, Phi, cls = modal_basis(bw, padb_s, N[late].mean(0))
    sos = butter(4, [0.7, 15.0], btype="band", fs=fs, output="sos")
    eta = sosfiltfilt(sos, wb, axis=0) @ Phi
    om = 2 * np.pi * f
    out["modes_f_Hz"] = f.tolist()
    out["modes_dof"] = [list(c)[:2] for c in cls]
    out["modal_E_0_3_J"] = [float((eta[a03, j] ** 2).max() / (2 * om[j] ** 2)) for j in range(6)]
    out["modal_E_3_6_J"] = [float((eta[a36, j] ** 2).max() / (2 * om[j] ** 2)) for j in range(6)]
    out["min_N_0_3_kN"] = (N[a03].min(0) / 1e3).tolist()
    return out


def run(spec):
    tic = time.perf_counter()
    pair, eng_in, scale, scale_t, cpad, mu_c = (spec["pair"], spec["input"], spec["scale"], spec["scale_t"],
                                               spec["cpad"], spec["mu_c"])
    cal_scale = spec.get("cal_scale", scale)
    c = load_case(pair, eng_in)
    tm = c["tm"]
    t = c["t"]
    # first pad contact per leg in Chrono (pad normal force > 500 N); the drive starts 0.3 s before the first
    t_first = np.array([float(t[np.where(c["N"][:, i] > 500.0)[0][0]]) for i in range(4)])
    s_first = np.array([np.interp(t_first[i], t, c["s"][:, i]) for i in range(4)])
    t_s = float(t_first.min()) - 0.3
    t_end = tm["liftoff"] + 6.0
    ks = int(np.argmin(np.abs(t - t_s)))
    t_chk = tm["touch"] - 0.2   # check time for the load distribution (TOUCH end - 0.2 s)
    w50 = (t >= t_chk - 0.025) & (t <= t_chk + 0.025)
    N_target = c["N"][w50].mean(0)
    tab = (t >= t_s - 0.01) & (t <= t_end + 0.01)
    s_tab = np.ascontiguousarray(c["s"][tab])
    tab_t0, tab_dt = float(t[tab][0]), float(np.median(np.diff(t)))
    sd_tab = np.ascontiguousarray(np.gradient(s_tab, tab_dt, axis=0))
    k_lo = int(np.argmin(np.abs(t - tm["liftoff"])))
    bw = dm.body_with_rods(P, GEO, "top", c["s"][k_lo])
    com = bw.com
    crb = np.ascontiguousarray(C_CR - com)
    padb = np.ascontiguousarray(PAD_BALL0 - com)
    Rf = lt.qmat(c["floor_q"])
    gf = Rf.T @ np.array([0.0, 0.0, -G])
    I = np.ascontiguousarray(bw.inertia)
    Iinv = np.linalg.inv(I)
    cp = C_PAD_MOV if cpad == "L2b_moving" else C_PAD
    dt_of = lambda sc: 1e-4 if sc <= 10 else (5e-5 if sc <= 1000 else 2e-5)  # noqa: E731

    def settle(delta, sc, sct, s_fix):
        dt = dt_of(max(sc, sct))
        x0 = com.copy(); q0 = np.array([1.0, 0, 0, 0]); z3 = np.zeros(3)
        anc_c = np.ascontiguousarray(C_CR[:, :2].copy()); anc_p = np.ascontiguousarray(PAD_BALL0[:, :2].copy())
        s_const = np.ascontiguousarray(np.repeat(np.asarray(s_fix, float)[None, :], 2, axis=0))
        fric = 1.0 if mu_c > 0 else 0.0  # mu_c = 0: crawler tangential spring off (pads keep MU)
        r = simulate(0.0, SETTLE_S, dt, x0, q0, z3, z3.copy(), anc_c, anc_p, s_const, np.zeros_like(s_const),
                     0.0, 1.0, delta, crb, padb, KN_SPH * sc, C_SPH * math.sqrt(sc), KT_SPH * sct * fric,
                     CT_SPH * math.sqrt(sct) * fric, K_PAD, cp, KT_PAD, CT_PAD, MU_SETTLE,
                     bw.mass, I, Iinv, gf, SETTLE_DAMP, 1e-3, ZF, RAD, R_PAD)
        Nend = r[1][-50:].mean(0)
        return Nend, r, anc_c, anc_p

    # touch-offset calibration on the drive engine's own crawler (cal_scale): settle on the crawler with the
    # pads retracted, then delta_i = replica touch stroke - Chrono stroke at the Chrono first contact
    r_cal = settle(np.zeros(4), cal_scale, cal_scale, np.zeros(4))[1]
    xc, qc = r_cal[6], r_cal[7]
    Rc = lt.qmat(qc)
    s_touch = (xc[2] + (padb @ Rc.T)[:, 2] - ZF - R_PAD) / Rc[2, 2]
    delta = s_touch - s_first
    # settle on the run crawler at the start strokes (pads still clear), then the drive
    Nset, r0, anc_c, anc_p = settle(delta, scale, scale_t, c["s"][ks])
    x, q, v, w = r0[6], r0[7], r0[8], r0[9]
    dt = dt_of(max(scale, scale_t))
    fric = 1.0 if mu_c > 0 else 0.0
    rt, rN, rNc, rwb, rcr, rx, *_ = simulate(
        t_s, t_end, dt, x, q, v, w, anc_c, anc_p, s_tab, sd_tab, tab_t0, tab_dt, delta, crb, padb,
        KN_SPH * scale, C_SPH * math.sqrt(scale), KT_SPH * scale_t * fric, CT_SPH * math.sqrt(scale_t) * fric,
        K_PAD, cp, KT_PAD, CT_PAD, MU, bw.mass, I, Iinv, gf, 0.0, 1e-3, ZF, RAD, R_PAD)
    lo_r = liftoff_time(rt, rNc, tm["liftoff"] + 2.0)
    s_lo = np.array([np.interp(lo_r, t, c["s"][:, i]) for i in range(4)]) + delta
    padb_s = padb - np.column_stack([np.zeros(4), np.zeros(4), s_lo])
    W = bw.mass * G
    met = metrics(rt, rN, rNc, rwb, rcr, lo_r, bw, padb_s, W)
    kchk = int(np.argmin(np.abs(rt - t_chk)))
    rf = [float(rt[np.where(rN[:, i] > 500.0)[0][0]]) if (rN[:, i] > 500.0).any() else math.nan for i in range(4)]
    met.update({"delta_mm": (delta * 1e3).tolist(), "touch_first_chrono_s": t_first.tolist(),
                "touch_first_replica_minus_chrono_s": (np.array(rf) - t_first).tolist(),
                "N_chrono_touch_end_m0p2_kN": (N_target / 1e3).tolist(),
                "N_replica_touch_end_m0p2_kN": (rN[kchk] / 1e3).tolist(),
                "Nc_replica_touch_end_m0p2_kN": float(rNc[kchk] / 1e3),
                "N_settled_start_kN": (Nset / 1e3).tolist(), "t_s": t_s, "chrono_liftoff_s": tm["liftoff"],
                "liftoff_minus_chrono_s": lo_r - tm["liftoff"], "dt_s": dt, "wall_s": time.perf_counter() - tic})
    keep = (rt >= lo_r - 1.5) & (rt <= lo_r + 6.0)
    series = {"t": (rt[keep][::5] - lo_r).tolist(), "N": (rN[keep][::5] / 1e3).tolist(),
              "Nc": (rNc[keep][::5] / 1e3).tolist()}
    return spec, met, series


def chrono_band(pair, eng):
    """Chrono pad normal force band 1..4 Hz half amplitude after the lift-off (same filter as the replica)."""
    c = load_case(pair, eng)
    t, N, lo = c["t"], c["N"], c["tm"]["liftoff"]
    fs = 1.0 / np.median(np.diff(t))
    fo = sosfiltfilt(butter(4, [1.0, 4.0], btype="band", fs=fs, output="sos"), N, axis=0)
    a = (t >= lo) & (t <= lo + 3.0)
    return ((fo[a].max(0) - fo[a].min(0)) / 2e3).tolist(), (N[a].min(0) / 1e3).tolist()


def specs():
    out = []
    for pair in ("rpB", "roll5.5", "fup3.5", "flat", "fdown3.5"):
        for inp in ("L1", "L2b"):
            for sc in (1.0, 3.0, 10.0, 100.0, 1000.0):
                out.append({"pair": pair, "input": inp, "scale": sc, "scale_t": sc, "cpad": "L1_lock", "mu_c": MU,
                            "cal_scale": 1.0 if inp == "L1" else 1000.0, "tag": "sweep"})
    for pair in ("rpB", "roll5.5"):
        for inp in ("L1", "L2b"):
            cal = 1.0 if inp == "L1" else 1000.0
            out.append({"pair": pair, "input": inp, "scale": 1e4, "scale_t": 1e4, "cpad": "L1_lock", "mu_c": MU,
                        "cal_scale": cal, "tag": "rigid_1e4"})
            out.append({"pair": pair, "input": inp, "scale": 1000.0, "scale_t": 1.0, "cpad": "L1_lock", "mu_c": MU,
                        "cal_scale": cal, "tag": "rigid_normal_compliant_tangential"})
            out.append({"pair": pair, "input": inp, "scale": 1000.0, "scale_t": 1000.0, "cpad": "L1_lock", "mu_c": 0.0,
                        "cal_scale": cal, "tag": "rigid_no_crawler_friction"})
            out.append({"pair": pair, "input": inp, "scale": 1000.0, "scale_t": 1000.0, "cpad": "L2b_moving", "mu_c": MU,
                        "cal_scale": cal, "tag": "rigid_L2b_leg_damping"})
            out.append({"pair": pair, "input": inp, "scale": 1.0, "scale_t": 1.0, "cpad": "L2b_moving", "mu_c": MU,
                        "cal_scale": cal, "tag": "compliant_L2b_leg_damping"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--only", default=None, help="pair name filter (debug)")
    a = ap.parse_args()
    sp = specs()
    if a.only:
        sp = [s for s in sp if s["pair"] == a.only and s["tag"] == "sweep"]
    tic = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(run, sp))
    chrono = {}
    for pair in {s["pair"] for s in sp}:
        for eng in ("L1", "L2b"):
            band, mn = chrono_band(pair, eng)
            chrono[f"{pair}/{eng}"] = {"band_halfamp_0_3_kN": band, "min_N_0_3_kN": mn}
    rows = []
    for spec, met, ser in res:
        rows.append({"spec": spec, "metrics": met})
    doc = {"meta": {"script": "04_scripts/01_dynamics/s7_liftoff_replica.py", "doc": "dynamics_model.md 5.25",
                    "wall_s": time.perf_counter() - tic,
                    "assumptions": {"pad": "L1 kn_per_pad fixed, cn LOCK (or L2b moving), L1 pad bushing, rods rigid",
                                    "crawler": "layout D spheres, kn x scale, c x sqrt(scale), L1 crawler bushing kt x scale_t, mu 0.5",
                                    "body": "superstructure top + rods frozen at the Chrono lift-off strokes",
                                    "calibration": "per-leg stroke offset so that pad N = Chrono at t_s (50 ms mean)"}},
           "chrono_pad_N_band": chrono, "runs": rows}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    figure(res, chrono)
    for spec, met, _ in res:
        print(f"{spec['pair']:8s} in {spec['input']:3s} sc {spec['scale']:7.0f} t {spec['scale_t']:6.0f} "
              f"{spec['cpad']:10s} mu {spec['mu_c']:.1f} {spec['tag'][:22]:22s} lo {met['liftoff_minus_chrono_s']:+.3f} "
              f"Nc-0.2/-0.1 {met['Nc_minus_0.2_kN']:6.1f}/{met['Nc_minus_0.1_kN']:6.1f} Fh-0.1 {met['Fh_minus_0.1_kN']:5.1f} "
              f"band {np.round(met['band_halfamp_0_3_kN'], 2)} chk {np.round(met['N_replica_touch_end_m0p2_kN'], 0)} vs {np.round(met['N_chrono_touch_end_m0p2_kN'], 0)} E1,2,heave {met['modal_E_0_3_J'][0]:.2f},"
              f"{met['modal_E_0_3_J'][1]:.2f},{met['modal_E_0_3_J'][5]:.2f} touch {np.round(met['touch_first_replica_minus_chrono_s'], 3)} "
              f"wall {met['wall_s']:.1f}")
    for k, v in chrono.items():
        print("chrono", k, np.round(v["band_halfamp_0_3_kN"], 2), np.round(v["min_N_0_3_kN"], 1))
    print(f"total wall {time.perf_counter() - tic:.1f} s")


def figure(res, chrono):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pairs = ("rpB", "roll5.5", "flat")
    fig, ax = plt.subplots(2, len(pairs), figsize=(5 * len(pairs), 7), sharex=True)
    for j, pr in enumerate(pairs):
        for spec, met, ser in res:
            if spec["pair"] != pr or spec["tag"] != "sweep" or spec["scale"] not in (1.0, 1000.0):
                continue
            ls = "-" if spec["scale"] == 1.0 else "--"
            col = "#1f77b4" if spec["input"] == "L1" else "#d62728"
            lab = f"drive {spec['input']}, crawler x{spec['scale']:g}"
            ax[0, j].plot(ser["t"], ser["Nc"], ls, color=col, lw=1, label=lab)
            Nmin = np.array(ser["N"])
            leg = 1 if pr != "flat" else 2
            ax[1, j].plot(ser["t"], Nmin[:, leg], ls, color=col, lw=0.8, label=lab)
        ax[0, j].set_title(f"replica {pr}")
        ax[0, j].set_ylabel("crawler normal force [kN]")
        ax[1, j].set_ylabel(f"pad normal force {LEGS[1 if pr != 'flat' else 2]} [kN]")
        ax[1, j].set_xlabel("t - replica lift-off [s]")
        for a_ in ax[:, j]:
            a_.axvline(0, color="k", lw=0.5)
            a_.grid(alpha=0.3)
        ax[0, j].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT.with_suffix(".png"), dpi=110)


if __name__ == "__main__":
    main()
