"""Rev. 49 (D1'' R41-3): false-fault risk of the D1'' IMU-residual head rule at higher seal friction,
on the dynamics reduced replica (D-S8-7, 04_scripts/01_dynamics/ds87_replica.py, same model; the simulate
kernel is copied here with the seal force and the body acceleration recorded).

For each fast-settlement episode extracted by ds87_extract.py (scratchpad npz), the replica is re-run with the
per-leg seal limits scaled to a target F_s (mean over the four legs; the run's leg ratios kept), with the nominal
leg damping and x 1/3. Open loop: the Chrono 1 ms s_motor of the episode drives the legs (as D-S8-7).

At the controller 10 Hz samples t_k (Chrono r8 't' of the episode) it forms what the monitor sees (sensor
errors left out):
  F_p,i(t_k) = F_i(t_k) - f_i(t_k)           (pressure force = cylinder force - seal force)
  f_z(t_k)   = mean over (t_k - 10 ms, t_k] of [a_z + g + (alpha x r)_z]  (IMU last partial mean, true)
  r_k        = sum F_p(t_k) - M f_z(t_k)      (D1'' residual with the true mass)
  r_k^lev    = r_k + M mean_last10 (alpha x r)_z   (exact lever-arm removal; real gyro adds noise)
and per period: head step of each leg |dF_p,i| / A_p in bar, step force J = |dF_p,i|, |d r|, |d r^lev|, the seal
part |d sum f| and its ratio to 2 sum F_s,i. Reports, per target F_s, the head steps > 100 bar with |d r| / J and
the transient-period |d r| distribution; writes a JSON.
Usage: python -I s8d1pp_replica_fs.py <extract_dir> <out_json> RUN [RUN ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from numba import njit

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

P = dm.load_params()
GEO = dm.geometry_from_params(P)
LEGS = list(dm.LEG_NAMES)
G = 9.80665
A_ANN = np.array([dm.annulus_area(i) for i in range(4)])
STROKE = 0.70
LEVER_YX = np.array([0.881, 0.150])  # (alpha x r)_z = 0.881 alpha_x + 0.150 alpha_y (5.28)


def poly345(x):
    x = np.clip(x, 0.0, 1.0)
    return 10 * x**3 - 15 * x**4 + 6 * x**5


@njit(cache=False)
def oil_force(x, x0, F0oil, kh, kb):
    if x >= x0:
        return F0oil + kh * (x - x0)
    return F0oil + kb * (x - x0)


@njit(cache=False)
def simulate(dt, n, Minv, Kg, W, Aatt, Apx, Apy, sref, u, moving, zg, sgeo0, x0, F0oil, kh, kb, kout,
             Fs, f0, cl, cm, khl, chl, rec_every):
    q = np.zeros(6)
    v = np.zeros(6)
    sp = sref[0] - x0
    f = f0.copy()
    anc = np.zeros((4, 2))
    incontact = np.ones(4, np.bool_)
    nrec = n // rec_every + 1
    out_F = np.empty((nrec, 4))
    out_f = np.empty((nrec, 4))
    out_a = np.empty((nrec, 6))
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
        a = Minv @ Q
        if k % rec_every == 0 and ir < nrec:
            for i in range(4):
                out_F[ir, i] = Fleg[i]
                out_f[ir, i] = f[i]
            for j in range(6):
                out_a[ir, j] = a[j]
            ir += 1
        for j in range(6):
            v[j] += dt * a[j]
            q[j] += dt * v[j]
    return out_F[:ir], out_f[:ir], out_a[:ir]


def run(z, info, fs_target_N, cscale, dt=1e-4, T_end=6.0, T_pre=0.3):
    tp = z["p_t"]
    t_ev = info["t_ev"]
    pre = (tp > t_ev - 0.6) & (tp < t_ev - 0.1)
    F0 = np.median(z["p_F_cyl"][pre], axis=0)
    lim = np.array(info["seal_limits_N"], float)
    ratio = lim / lim.mean() if lim.mean() > 0 else np.ones(4)
    Fs = fs_target_N * ratio
    f0 = np.median(z["p_f_seal"][pre], axis=0)
    f0 = np.clip(f0, -Fs, Fs)  # the run's stuck preload, limited to the new seal limit
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
    beta, Ap, L0h = info["beta_Pa"], np.array(info["head_area_m2"]), info["head_dead_m"]
    kh = beta * Ap / (L0h + s)
    kb = kh.copy()
    kout = 1 / (1 / np.array(info["k_rod_N_m"]) + 1 / info["frame_N_m"] + 1 / info["k_concrete_N_m"])
    t0 = t_ev - T_pre
    n = int(round((T_pre + T_end) / dt))
    tt = t0 + dt * np.arange(n)
    sref = np.column_stack([np.interp(tt, tp, z["p_s_motor"][:, i]) for i in range(4)])
    u = np.gradient(sref, dt, axis=0)
    qt, qv = z["q_t"], z["q_valve_u"]
    idx = np.clip(np.searchsorted(qt, tt, side="right") - 1, 0, len(qt) - 1)
    moving = np.abs(qv[idx]) > 1e-6
    zg = np.zeros((n, 4))
    L = LEGS.index(info["leg"])
    zg[:, L] = -info["depth_m"] * poly345((tt - t_ev) / info["ramp_s"])
    x0 = (F0 - f0) / kh
    F0oil = F0 - f0
    sp0 = sref[0] - x0
    sgeo0 = sp0 - F0 / kout
    rec_every = int(round(1e-3 / dt))
    Fl, fl, acc = simulate(dt, n, Minv, Kg, W, Aatt, Apx, Apy, sref, u, moving, zg, sgeo0, x0, F0oil, kh, kb, kout,
                           Fs, f0, cscale * np.array(info["c_locked"]), cscale * np.array(info["c_moving"]),
                           np.array(info["k_lat"]), np.array(info["c_lat"]), rec_every)
    tr = t0 + 1e-3 * np.arange(len(Fl))
    return tr, Fl, fl, acc, W / G, Fs, np.array(Ap)


def periods(tr, Fl, fl, acc, mass, Ap, qt, t_ev):
    lever = acc[:, 3] * LEVER_YX[0] + acc[:, 4] * LEVER_YX[1]
    fz = acc[:, 2] + G + lever
    tk = qt[(qt >= tr[0] + 0.02) & (qt <= tr[-1])]
    rows = []
    for t in tk:
        j = int(np.argmin(np.abs(tr - t)))
        w = (tr > t - 0.01 + 1e-9) & (tr <= t + 1e-9)
        Fp = Fl[j] - fl[j]
        rows.append(dict(t=t - t_ev, Fp=Fp, sum_f=fl[j].sum(), fz=fz[w].mean(), lev=lever[w].mean()))
    out = []
    for a, b in zip(rows[:-1], rows[1:]):
        dFp = b["Fp"] - a["Fp"]
        r_a = a["Fp"].sum() - mass * a["fz"]
        r_b = b["Fp"].sum() - mass * b["fz"]
        out.append(dict(t=b["t"], dp_bar=(dFp / Ap / 1e5).tolist(), dr=r_b - r_a,
                        dr_lev=(r_b + mass * b["lev"]) - (r_a + mass * a["lev"]), dseal=b["sum_f"] - a["sum_f"],
                        dsum=b["Fp"].sum() - a["Fp"].sum()))
    return out


src, out_json = Path(sys.argv[1]), Path(sys.argv[2])
result = {}
for name in sys.argv[3:]:
    z = np.load(src / f"{name}.npz", allow_pickle=True)
    info = json.loads(str(z["info"]))
    result[name] = dict(info={k: info[k] for k in ("leg", "depth_m", "ramp_s", "level", "fs_kN")}, cases={})
    for fs_kN in (0.0, 2.0, 4.0, 8.0):
        for cs in (1.0, 1 / 3):
            tr, Fl, fl, acc, mass, Fs, Ap = run(z, info, fs_kN * 1e3, cs)
            per = periods(tr, Fl, fl, acc, mass, Ap, z["q_t"], info["t_ev"])
            post = [p for p in per if p["t"] >= 0.0]
            steps = []
            for p in post:
                for i, dp in enumerate(p["dp_bar"]):
                    if abs(dp) > 100.0:
                        J = abs(dp) * 1e5 * Ap[i]
                        steps.append(dict(t=round(p["t"], 2), leg=LEGS[i], dp=round(dp, 1), J_kN=round(J / 1e3, 1),
                                          ratio=round(abs(p["dr"]) / J, 3), ratio_lev=round(abs(p["dr_lev"]) / J, 3),
                                          ratio_sum=round(abs(p["dsum"]) / J, 3),
                                          dseal_kN=round(p["dseal"] / 1e3, 1)))
            trans = [p for p in post if max(abs(x) for x in p["dp_bar"]) > 30.0]
            dr = np.array([abs(p["dr"]) for p in trans]) / 1e3 if trans else np.zeros(1)
            drl = np.array([abs(p["dr_lev"]) for p in trans]) / 1e3 if trans else np.zeros(1)
            ds = np.array([abs(p["dseal"]) for p in post]) / 1e3
            key = f"Fs{fs_kN:g}_c{cs:.2f}"
            two_sum = 2 * Fs.sum() / 1e3
            result[name]["cases"][key] = dict(
                two_sum_Fs_kN=round(two_sum, 1), steps=steps, n_trans=len(trans),
                dr_max_kN=round(float(dr.max()), 1), dr_p99_kN=round(float(np.percentile(dr, 99)), 1),
                dr_lev_max_kN=round(float(drl.max()), 1), dseal_max_kN=round(float(ds.max()), 1),
                dseal_ratio_max=round(float(ds.max() / two_sum), 3) if two_sum > 0 else None)
            st = ", ".join(f"{s['leg']} {s['dp']:+.0f} bar r {s['ratio']:.2f}/{s['ratio_lev']:.2f} (sum {s['ratio_sum']:.2f})"
                           for s in steps) or "-"
            print(f"{name} {key}: 2sumFs {two_sum:5.1f} kN | trans {len(trans):3d} |dr| max {dr.max():5.1f} p99 "
                  f"{np.percentile(dr, 99):5.1f} lev max {drl.max():5.1f} | dseal max {ds.max():5.1f} | steps>100: {st}",
                  flush=True)
out_json.write_text(json.dumps(result, indent=1), encoding="utf-8")
