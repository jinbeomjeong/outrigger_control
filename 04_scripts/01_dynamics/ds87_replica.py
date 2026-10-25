"""D-S8-7 (dynamics_model.md rev. 41): reduced replica of the response to a fast pad settlement, independent of
Chrono and of 03_src, compared with the L2b-NSC Chrono records of the ML pilot rerun.

Model (SI, body frame x forward / y left / z up, small motion about the pre-event pose, g = 9.80665 m/s^2):
* rigid superstructure, YAML auger level (mass, inertia about the CoM; rods not included: in contact they move
  with the ground). Generalised coordinates q = [ux, uy, uz, phi, theta, psi] of the CoM. Geometric (preload)
  stiffness -F0_i Hz(d_pad_i) as dyn_model.stiffness_6dof.
* floor tilt not modelled: the CoM x, y are replaced by the centre of the pre-event Chrono cylinder forces
  (equivalent CoP, ASSUMPTION), so the pre-event Chrono loads are an exact equilibrium.
* each leg: massless rod. Oil spring Phi(x), x = s_ref - s_p (head k_h = beta A_p / (L0h + s); variant 'b' adds
  the locked rod side k_r = beta A_ann / (L0r + 0.7 - s) for x below the pre-event anchor), massless piston s_p
  with Coulomb seal friction |f| <= F_s (rigid stick, per-leg limits of the run), outer spring k_out (rod,
  frame, concrete) to the floor, unilateral: F_out = k_out max(0, s_p - s_geo). Leg force on the body
  F = max(0, F_out + c (u - ds_geo/dt)) while in contact (c = locked / moving value from the Chrono valve
  output), 0 in the air. s_geo = needed extension = s_geo0 + dz_att - dz_ground.
* lateral: pad spring-dashpot (L2b lateral bushing k, c of the run) to an anchor set at touch-down; no slip.
* drive: Chrono 1 ms s_motor (= s_ref) of the episode, u = ds_ref/dt (central difference).
* settled leg: ground z = -depth Poly345((t - t_ev) / ramp).
* integration: semi-implicit Euler, dt 1e-4 s (check: 5e-5 s on one run), start t_ev - 0.3 s, end t_ev + 6 s.

Metrics vs Chrono (0 .. 3 s after the event): sum F / W min / max, per-leg max force, airborne time per leg,
rotation about the FL-RR / FR-RL diagonals (rms difference, ESPRIT dominant f in 0.25 .. 1.5 s and 1.5 .. 3 s).
Variants: 'h' (head only), 'b' (bilinear rod side), each with seal friction; 'h0' without seal friction;
'h_c033' / 'h_c05' / 'h_c2': 'h' with the leg damping (locked and moving) x 1/3, 0.5, 2. Event pair (settled leg + diagonal):
first lift, last touch-down, union airborne time over 0 .. 6 s (replica airborne = 20 ms mean force <= 1 N).
Writes 06_analysis/00_dynamics/ds87_replica.json and a figure ds87_replica.png.
Usage: python -I ds87_replica.py <extract_dir> RUN [RUN ...]
"""
import json
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from numba import njit  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
from ds87_modes import dominant, rp_from_quat  # noqa: E402

P = dm.load_params()
GEO = dm.geometry_from_params(P)
LEGS = list(dm.LEG_NAMES)
G = 9.80665
A_ANN = np.array([dm.annulus_area(i) for i in range(4)])
STROKE = 0.70
OUT = ROOT / "06_analysis" / "00_dynamics" / "ds87_replica.json"


def poly345(x):
    x = np.clip(x, 0.0, 1.0)
    return 10 * x**3 - 15 * x**4 + 6 * x**5


@njit(cache=False)
def oil_force(x, x0, F0oil, kh, kb):
    if x >= x0:
        return F0oil + kh * (x - x0)
    return F0oil + kb * (x - x0)


@njit(cache=False)
def simulate(t0, dt, n, Minv, Kg, W, Aatt, Apx, Apy, sref, u, moving, zg, sgeo0, x0, F0oil, kh, kb, kout,
             Fs, f0, cl, cm, khl, chl, rec_every):
    q = np.zeros(6)
    v = np.zeros(6)
    sp = sref[0] - x0  # piston
    stuck = np.ones(4, np.bool_)
    f = f0.copy()
    anc = np.zeros((4, 2))
    incontact = np.ones(4, np.bool_)
    nrec = n // rec_every + 1
    out_F = np.empty((nrec, 4))
    out_q = np.empty((nrec, 6))
    out_air = np.empty((nrec, 4), np.bool_)
    ir = 0
    sgeo_prev = np.empty(4)
    for i in range(4):
        sgeo_prev[i] = sgeo0[i]
    for k in range(n):
        Q = np.zeros(6)
        Q[2] -= W
        Fleg = np.zeros(4)
        for i in range(4):
            dz = 0.0
            for j in range(6):
                dz += Aatt[i, j] * q[j]
            sgeo = sgeo0[i] + dz - zg[k, i]
            sgd = (sgeo - sgeo_prev[i]) / dt if k > 0 else 0.0
            sgeo_prev[i] = sgeo
            sr = sref[k, i]
            # piston equilibrium: g(sp) = kout*max(0, sp - sgeo) - Phi(sr - sp) - f, |f| <= Fs
            Fout = kout[i] * max(0.0, sp[i] - sgeo)
            ftr = Fout - oil_force(sr - sp[i], x0[i], F0oil[i], kh[i], kb[i])
            if abs(ftr) <= Fs[i]:
                f[i] = ftr
            else:
                fs = Fs[i] if ftr > 0 else -Fs[i]
                lo, hi = sp[i] - 0.05, sp[i] + 0.05
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    gm = kout[i] * max(0.0, mid - sgeo) - oil_force(sr - mid, x0[i], F0oil[i], kh[i], kb[i]) - fs
                    if gm > 0:
                        hi = mid
                    else:
                        lo = mid
                sp[i] = 0.5 * (lo + hi)
                f[i] = fs
                Fout = kout[i] * max(0.0, sp[i] - sgeo)
            c = cm[i] if moving[k, i] else cl[i]
            if Fout > 0.0:
                Fl = Fout + c * (u[k, i] - sgd)
                if Fl < 0.0:
                    Fl = 0.0
                if not incontact[i]:
                    # touch-down: new lateral anchor
                    hx = 0.0
                    hy = 0.0
                    for j in range(6):
                        hx += Apx[i, j] * q[j]
                        hy += Apy[i, j] * q[j]
                    anc[i, 0] = hx
                    anc[i, 1] = hy
                incontact[i] = True
            else:
                Fl = 0.0
                incontact[i] = False
            Fleg[i] = Fl
            for j in range(6):
                Q[j] += Aatt[i, j] * Fl
            if incontact[i]:
                ux = 0.0
                uy = 0.0
                vx = 0.0
                vy = 0.0
                for j in range(6):
                    ux += Apx[i, j] * q[j]
                    uy += Apy[i, j] * q[j]
                    vx += Apx[i, j] * v[j]
                    vy += Apy[i, j] * v[j]
                Hx = -khl[i] * (ux - anc[i, 0]) - chl[i] * vx
                Hy = -khl[i] * (uy - anc[i, 1]) - chl[i] * vy
                for j in range(6):
                    Q[j] += Apx[i, j] * Hx + Apy[i, j] * Hy
        for j in range(6):
            s = 0.0
            for m in range(6):
                s += Kg[j, m] * q[m]
            Q[j] -= s
        if k % rec_every == 0 and ir < nrec:
            for i in range(4):
                out_F[ir, i] = Fleg[i]
                out_air[ir, i] = not incontact[i]
            for j in range(6):
                out_q[ir, j] = q[j]
            ir += 1
        a = Minv @ Q
        for j in range(6):
            v[j] += dt * a[j]
            q[j] += dt * v[j]
    return out_F[:ir], out_q[:ir], out_air[:ir]


def run_replica(z, info, variant, dt=1e-4, T_end=6.0, T_pre=0.3):
    tp = z["p_t"]
    t_ev = info["t_ev"]
    pre = (tp > t_ev - 0.6) & (tp < t_ev - 0.1)
    F0 = np.median(z["p_F_cyl"][pre], axis=0)
    f0 = np.median(z["p_f_seal"][pre], axis=0) if variant != "h0" else np.zeros(4)
    cscale = {"h_c033": 1 / 3, "h_c05": 0.5, "h_c2": 2.0}.get(variant, 1.0)  # damping sensitivity (locked and moving c)
    s = np.median(z["p_s_link"][pre], axis=0)
    body = dm.body_from_params(P, info["level"])
    W = float(F0.sum())
    cop = (F0[:, None] * GEO.pad_xy).sum(0) / W
    com = np.array([cop[0], cop[1], body.com[2]])
    M = np.zeros((6, 6))
    M[:3, :3] = (W / G) * np.eye(3)
    M[3:, 3:] = body.inertia
    Minv = np.linalg.inv(M)
    Aatt = np.zeros((4, 6))
    Apx = np.zeros((4, 6))
    Apy = np.zeros((4, 6))
    Kg = np.zeros((6, 6))
    for i in range(4):
        d_att = np.array([*GEO.pad_xy[i], GEO.attach_z[i]]) - com
        d_pad = np.array([*GEO.pad_xy[i], GEO.pad_z_retracted[i] - s[i]]) - com
        Aatt[i] = dm.a_vec(d_att)[2]
        Apx[i], Apy[i] = dm.a_vec(d_pad)[0], dm.a_vec(d_pad)[1]
        Kg[3:, 3:] -= F0[i] * dm._hz(d_pad)
    beta, Ap, L0h, L0r = info["beta_Pa"], np.array(info["head_area_m2"]), info["head_dead_m"], info["L0r_m"]
    kh = beta * Ap / (L0h + s)
    kr = beta * A_ANN / (L0r + STROKE - s)
    kb = kh + kr if variant == "b" else kh.copy()
    kout = 1 / (1 / np.array(info["k_rod_N_m"]) + 1 / info["frame_N_m"] + 1 / info["k_concrete_N_m"])
    Fs = np.array(info["seal_limits_N"], float) if variant != "h0" else np.zeros(4)
    t0 = t_ev - T_pre
    n = int(round((T_pre + T_end) / dt))
    tt = t0 + dt * np.arange(n)
    sref = np.column_stack([np.interp(tt, tp, z["p_s_motor"][:, i]) for i in range(4)])
    u = np.gradient(sref, dt, axis=0)
    # valve state (10 Hz record of the valve speed): moving if |valve_u| > 1e-6 m/s in the last sample <= t
    qt, qv = z["q_t"], z["q_valve_u"]
    idx = np.clip(np.searchsorted(qt, tt, side="right") - 1, 0, len(qt) - 1)
    moving = np.abs(qv[idx]) > 1e-6
    zg = np.zeros((n, 4))
    L = LEGS.index(info["leg"])
    zg[:, L] = -info["depth_m"] * poly345((tt - t_ev) / info["ramp_s"])
    Fout0 = F0  # outer spring carries the cylinder force
    x0 = (F0 - f0) / kh  # oil compression at the anchor (bookkeeping: Phi(x0) = F0 - f0)
    F0oil = F0 - f0
    sp0 = sref[0] - x0
    sgeo0 = sp0 - Fout0 / kout
    rec_every = int(round(1e-3 / dt))
    Fl, qq, air = simulate(t0, dt, n, Minv, Kg, W, Aatt, Apx, Apy, sref, u, moving, zg, sgeo0, x0, F0oil, kh, kb,
                           kout, Fs, f0, cscale * np.array(info["c_locked"]), cscale * np.array(info["c_moving"]),
                           np.array(info["k_lat"]), np.array(info["c_lat"]), rec_every)
    tr = t0 + 1e-3 * np.arange(len(Fl))
    return tr - t_ev, Fl, qq, air, W


def diag_angles(phi, theta):
    xy = GEO.pad_xy
    u1 = (xy[3] - xy[0]) / np.linalg.norm(xy[3] - xy[0])
    u2 = (xy[2] - xy[1]) / np.linalg.norm(xy[2] - xy[1])
    return np.degrees(phi * u1[0] + theta * u1[1]), np.degrees(phi * u2[0] + theta * u2[1])


DIAG = {0: 3, 3: 0, 1: 2, 2: 1}


def metrics(t, F, phi, theta, air, W, leg=None):
    w = (t >= 0) & (t <= 3.0)
    sF = F[w].sum(1) / W
    a1, a2 = diag_angles(phi, theta)
    res = dict(sumF_min=round(float(sF.min()), 3), sumF_max=round(float(sF.max()), 3),
               Fmax_kN=np.round(F[w].max(0) / 1e3, 1).tolist(),
               air_s=np.round(air[w].sum(0) * 1e-3, 3).tolist())
    if leg is not None:
        w6 = (t >= 0) & (t <= 6.0)
        u = air[w6, leg] | air[w6, DIAG[leg]]
        iu = np.flatnonzero(u)
        tt = t[w6]
        res["pair_first_lift_s"] = round(float(tt[iu[0]]), 3) if len(iu) else None
        res["pair_last_touch_s"] = round(float(tt[iu[-1]]), 3) if len(iu) else None
        res["pair_union_s"] = round(float(u.sum() * 1e-3), 3)
    for lo, hi in ((0.25, 1.5), (1.5, 3.0)):
        ww = (t >= lo) & (t < hi)
        tb = t[ww][::5]
        for name, x in (("roll", np.degrees(phi)), ("pitch", np.degrees(theta))):
            y = x[ww][::5]
            y = y - np.polyval(np.polyfit(tb, y, 2), tb)
            res[f"{name}_{lo}-{hi}"] = dominant(y, 0.005, (0.8, 4.0))
    return res, a1, a2


src = Path(sys.argv[1])
runs = sys.argv[2:]
out = {}
fig, axs = plt.subplots(len(runs), 3, figsize=(18, 2.7 * len(runs)), squeeze=False)
for r, run in enumerate(runs):
    z = np.load(src / f"{run}.npz", allow_pickle=True)
    info = json.loads(str(z["info"]))
    tp = z["p_t"] - info["t_ev"]
    pre = (tp > -0.6) & (tp < -0.1)
    roll, pitch = rp_from_quat(z["p_body_quat_wxyz"])
    roll -= np.median(roll[pre]); pitch -= np.median(pitch[pre])
    Lidx = LEGS.index(info["leg"])
    mc, c1, c2 = metrics(tp, z["p_F_cyl"], roll, pitch, z["p_airborne"], float(np.median(z["p_F_cyl"][pre].sum(1))), Lidx)
    entry = dict(info={k: info[k] for k in ("leg", "depth_m", "ramp_s", "level", "fs_kN")}, chrono=mc, replica={})
    print(f"== {run} {info['leg']} {info['depth_m']*1e3:.1f} mm / {info['ramp_s']:.3f} s {info['level']} Fs {info['fs_kN']}")
    print(f"   chrono   sumF/W {mc['sumF_min']:.3f}..{mc['sumF_max']:.3f} Fmax {mc['Fmax_kN']} air {mc['air_s']}"
          f" roll {mc['roll_0.25-1.5']} {mc['roll_1.5-3.0']} pair lift {mc['pair_first_lift_s']}..{mc['pair_last_touch_s']} union {mc['pair_union_s']}")
    tw = (tp >= -0.2) & (tp <= 3.0)
    axs[r, 0].plot(tp[tw], z["p_F_cyl"][tw].sum(1) / 1e3, "k", lw=1.2, label="Chrono")
    axs[r, 1].plot(tp[tw], c1[tw], "k", lw=1.2, label="Chrono FL-RR")
    axs[r, 2].plot(tp[tw], z["p_F_cyl"][tw] / 1e3, "k", lw=1.0)
    for variant, col in (("h", "C0"), ("b", "C3"), ("h0", "C2"), ("h_c033", "C6"), ("h_c05", "C4"), ("h_c2", "C5")):
        t0w = time.perf_counter()
        t, Fl, qq, air, W = run_replica(z, info, variant)
        wall = time.perf_counter() - t0w
        kern = np.ones(20) / 20.0  # 20 ms centred mean, as the Chrono pad record airborne rule (S8-A2)
        air20 = np.column_stack([np.convolve(Fl[:, i], kern, mode="same") <= 1.0 for i in range(4)])
        m, a1, a2 = metrics(t, Fl, qq[:, 3], qq[:, 4], air20, W, Lidx)
        # rms differences on the common 1 ms grid (0 .. 3 s)
        ww = (t >= 0) & (t <= 3.0)
        cF = np.column_stack([np.interp(t[ww], tp, z["p_F_cyl"][:, i]) for i in range(4)])
        cr1 = np.interp(t[ww], tp, c1)
        m["rms_dF_kN"] = round(float(np.sqrt(((Fl[ww] - cF) ** 2).mean()) / 1e3), 2)
        m["rms_d_diag_FLRR_deg"] = round(float(np.sqrt(((a1[ww] - cr1) ** 2).mean())), 4)
        m["rms_chrono_diag_FLRR_deg"] = round(float(np.sqrt(((cr1 - cr1.mean()) ** 2).mean())), 4)
        m["wall_s"] = round(wall, 2)
        entry["replica"][variant] = m
        print(f"   rep {variant:3s} sumF/W {m['sumF_min']:.3f}..{m['sumF_max']:.3f} Fmax {m['Fmax_kN']} air {m['air_s']}"
              f" roll {m['roll_0.25-1.5']} {m['roll_1.5-3.0']} rms dF {m['rms_dF_kN']} kN d diag {m['rms_d_diag_FLRR_deg']} deg"
              f" (chrono rms {m['rms_chrono_diag_FLRR_deg']}) pair lift {m['pair_first_lift_s']}..{m['pair_last_touch_s']} union {m['pair_union_s']} {wall:.1f} s")
        tw2 = (t >= -0.2) & (t <= 3.0)
        axs[r, 0].plot(t[tw2], Fl[tw2].sum(1) / 1e3, col, lw=0.8, label=f"replica {variant}")
        axs[r, 1].plot(t[tw2], a1[tw2], col, lw=0.8, label=f"replica {variant}")
        if variant == "h":
            axs[r, 2].plot(t[tw2], Fl[tw2] / 1e3, col, lw=0.8, ls="--")
    axs[r, 0].set_ylabel(f"{run}\nsum F_cyl [kN]")
    axs[r, 0].set_title(f"{info['leg']} {info['depth_m']*1e3:.1f} mm / {info['ramp_s']:.3f} s, {info['level']}, F_s {info['fs_kN']} kN")
    axs[r, 1].set_ylabel("rotation about FL-RR [deg]")
    axs[r, 2].set_ylabel("leg F_cyl [kN] (black Chrono, dashed 'h')")
    axs[r, 0].legend(fontsize=7, ncol=2)
    for a in axs[r]:
        a.grid(alpha=0.3)
    out[run] = entry
for a in axs[-1]:
    a.set_xlabel("t - t_event [s]")
fig.tight_layout()
fig.savefig(OUT.with_suffix(".png"), dpi=80)
# time-step check on the first run
z = np.load(src / f"{runs[0]}.npz", allow_pickle=True)
info = json.loads(str(z["info"]))
t1, F1, *_ = run_replica(z, info, "h", dt=1e-4)
t2, F2, *_ = run_replica(z, info, "h", dt=5e-5)
nn = min(len(F1), len(F2))
out["_dt_check"] = dict(run=runs[0], max_abs_dF_kN=round(float(np.abs(F1[:nn] - F2[:nn]).max() / 1e3), 3),
                        max_F_kN=round(float(F1.max() / 1e3), 1))
print("dt check (1e-4 vs 5e-5 s):", out["_dt_check"])
OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
print("wrote", OUT)
