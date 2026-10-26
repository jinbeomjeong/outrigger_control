"""Planar (surge x, heave z, pitch theta) replica of the S9 machine crawler settle on SCM (G1 by default).

Purpose: judge whether the ~1 Hz pitch-surge oscillation of the Chrono smoke run (machine G1 B b-prime, 1.5 s)
is the physical rocking mode of the model (crawler on SCM normal law + track anchor bushings), and find its
frequency / damping, the settle time and the effect of a gravity ramp.

Model (same laws as Chrono 10 SCM, SCMTerrain.cpp:1394-1465 via chrono-rag):
  node sigma_trial = K (s - s_p); sigma < 0 -> no contact (no damping); if sigma_trial > sigma_y:
  sigma = Kphi s^n (Kc = 0 for G1; general Kc/b ignored -> G1 only), sigma_y = sigma, s_p = s - sigma/K;
  sigma += -Vn R (unclamped).  Force per node = h^2 sigma.  SCM loads explicit (start-of-step state).
  Track anchors: 2 x (k, c) horizontal at the flat-box centre, block-bottom height (stick; utilisation 2 %).
  Rigid body = superstructure 'top' + 4 moving parts (dyn_model.body_with_rods), legs/pads rigid.
  Integrator: symplectic Euler with explicit forces (= EULER_IMPLICIT_LINEARIZED with constant loads).
Frame: body x forward, z up; pitch > 0 nose down; SI; gravity (0, 0, -9.80665).
Usage: python -I 04_scripts/01_dynamics/s9_crawler_rocking_replica.py [--soil G1] [--t-end 20] [--ramp 0|T] [--shape linear|poly345] [--out <prefix>]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WT / "04_scripts" / "01_dynamics"))
import run_pad_bekker_p0 as p0  # noqa: E402

G = 9.80665
SOILS = json.load(open(WT / "02_params" / "scm_soil_sets.json", encoding="utf-8"))["sets"]
K_TRACK = 11037928.62254772     # per track, S9 run meta crawler_anchor (G1)
C_TRACK = 46251.3875611972      # per track, actual
X_TRACK, Z_TRACK = -0.019565, -1.0469


def build(soil_key, h=0.02):
    s = SOILS[soil_key]["chrono"]
    b = p0.body("top")
    X, Y, hb = p0.crawler_nodes(h)
    ok = np.isfinite(hb)
    # collapse y: per x column count nodes and height (C boxes: height depends on x only)
    xs = X[:, 0]
    w = ok.sum(axis=1).astype(float) * 2.0 * h * h   # both tracks
    hcol = np.array([hb[i][ok[i]].min() if ok[i].any() else np.inf for i in range(len(xs))])
    m = w > 0
    return dict(s=s, mass=b.mass, com=b.com, Iyy=b.inertia[1, 1], x=xs[m], zb=p0.Z_SURF + hcol[m], w=w[m],
                ny=ok.sum(axis=1)[m])


def ramp_factor(t, T, shape):
    if T <= 0:
        return 1.0
    u = min(max(t / T, 0.0), 1.0)
    if shape == "linear":
        return u
    return 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5


def simulate(md, t_end, dt=1e-4, ramp=0.0, shape="poly345", rec_every=10, R_scale=1.0, track=True):
    s = md["s"]
    K, Kphi, n, R = s["elastic_K"], s["Kphi"], s["n"], s["damping_R"] * R_scale
    m, Iyy, com = md["mass"], md["Iyy"], md["com"]
    dxb = md["x"] - com[0]
    dzb = md["zb"] - com[2]
    tdx, tdz = X_TRACK - com[0], Z_TRACK - com[2]
    w = md["w"]
    xg, zg, th = com[0], com[2], 0.0
    vx = vz = om = 0.0
    sp = np.zeros_like(w)
    sy = np.zeros_like(w)
    x_tr0 = X_TRACK
    nsteps = int(round(t_end / dt))
    out = []
    for k in range(nsteps):
        t = k * dt
        c, sn = math.cos(th), math.sin(th)
        # world offsets of node points (rotation about +y: x' = c x + s z, z' = -s x + c z)
        ox = c * dxb + sn * dzb
        oz = -sn * dxb + c * dzb
        zw = zg + oz
        vzn = vz + om * (-c * dxb - sn * dzb)
        sink = p0.Z_SURF - zw
        sig = K * (sink - sp)
        con = sig > 0
        load = con & (sig > sy)
        bek = Kphi * np.maximum(sink, 0.0) ** n
        sig = np.where(load, bek, sig)
        sy = np.where(load, bek, sy)
        sp = np.where(load, sink - bek / K, sp)
        sig = np.where(con, sig - vzn * R, 0.0)
        fz = sig * w
        Fz = fz.sum()
        My = -(ox * fz).sum()            # tau_y = dz Fx - dx Fz
        Fx = 0.0
        if track:
            ptx = xg + c * tdx + sn * tdz
            pvx = vx + om * (-sn * tdx + c * tdz)
            fx = -2 * K_TRACK * (ptx - x_tr0) - 2 * C_TRACK * pvx
            Fx += fx
            My += (-sn * tdx + c * tdz) * fx
        gf = ramp_factor(t, ramp, shape)
        ax = Fx / m
        az = Fz / m - G * gf
        al = My / Iyy
        vx += dt * ax
        vz += dt * az
        om += dt * al
        xg += dt * vx
        zg += dt * vz
        th += dt * om
        if (k + 1) % rec_every == 0:
            # body origin position
            c2, s2 = math.cos(th), math.sin(th)
            ox0 = xg + c2 * (-com[0]) + s2 * (-com[2])
            oz0 = zg - s2 * (-com[0]) + c2 * (-com[2])
            out.append((t + dt, math.degrees(th), ox0, oz0, Fz, con.sum(), float((sp * w).sum())))
    return np.array(out), (sp, con.astype(float))


def fit_osc(t, y, f0=1.0):
    """Fit y = a + b t + A exp(-zeta w t) cos(w_d t + p) by least squares (scipy)."""
    from scipy.optimize import least_squares

    def r(p):
        a, b, A, z, f, ph = p
        wn = 2 * math.pi * f
        return a + b * t + A * np.exp(-z * wn * (t - t[0])) * np.cos(wn * math.sqrt(max(1 - z * z, 1e-9)) * (t - t[0]) + ph) - y

    best = None
    for ph in np.linspace(-3, 3, 7):
        res = least_squares(r, [y.mean(), 0, (y.max() - y.min()) / 2, 0.02, f0, ph],
                            bounds=([-np.inf, -np.inf, 0, -0.5, 0.2, -10], [np.inf, np.inf, np.inf, 0.9, 5, 10]))
        if best is None or res.cost < best.cost:
            best = res
    a, b, A, z, f, ph = best.x
    return dict(mean=a, trend_per_s=b, amp=A, zeta=z, f_n_Hz=f, f_d_Hz=f * math.sqrt(max(1 - z * z, 0)),
                rms_resid=float(np.sqrt(np.mean(best.fun ** 2))))


def linear_modes(md, sp_state=None, R_scale=1.0):
    """Elastic-branch linear 3-DoF modes about the COG: contact nodes (sink > s_p at the end) with K h^2,
    damping R h^2, track springs; gravity P-delta -W h."""
    s = md["s"]
    K, R = s["elastic_K"], s["damping_R"] * R_scale
    m, Iyy, com = md["mass"], md["Iyy"], md["com"]
    dx = md["x"] - com[0]
    w = md["w"] if sp_state is None else md["w"] * sp_state
    Kz = K * w
    Cz = R * w
    Kt = np.zeros((3, 3))
    Ct = np.zeros((3, 3))
    for i in range(len(dx)):
        a = np.array([0.0, 1.0, -dx[i]])     # vertical displacement gradient wrt [x, z, theta]
        Kt += Kz[i] * np.outer(a, a)
        Ct += Cz[i] * np.outer(a, a)
    a = np.array([1.0, 0.0, Z_TRACK - com[2]])  # horizontal at the track point
    Kt += 2 * K_TRACK * np.outer(a, a)
    Ct += 2 * C_TRACK * np.outer(a, a)
    W = m * G
    h = com[2] - Z_TRACK
    Kt[2, 2] -= W * h
    M = np.diag([m, m, Iyy])
    n = 3
    A = np.block([[np.zeros((n, n)), np.eye(n)], [-np.linalg.solve(M, Kt), -np.linalg.solve(M, Ct)]])
    lam, V = np.linalg.eig(A)
    rows = []
    for j in np.argsort(np.abs(lam)):
        if lam[j].imag <= 0:
            continue
        wn = abs(lam[j])
        v = V[:n, j]
        v = v / v[np.argmax(np.abs(v))]
        rows.append(dict(f_n_Hz=wn / 2 / math.pi, zeta=-lam[j].real / wn, shape_x_z_theta=[f"{c.real:+.3g}" for c in v]))
    from scipy.linalg import eigh
    w2, Phi = eigh(Kt, M)
    und = [float(math.sqrt(max(v, 0)) / 2 / math.pi) for v in w2]
    # rotation centre height of the rocking (pitch) mode: x displacement of a point at z = 0 when theta = 1
    return dict(complex=rows, undamped_Hz=und, Kt=Kt.tolist(), Iyy=Iyy, mass=m, com=com.tolist(), W_h=W * h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--soil", default="G1")
    ap.add_argument("--t-end", type=float, default=1.5)
    ap.add_argument("--ramp", type=float, default=0.0)
    ap.add_argument("--shape", default="poly345")
    ap.add_argument("--R-scale", type=float, default=1.0)
    ap.add_argument("--fit-from", type=float, default=0.3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    md = build(a.soil)
    print("mass", md["mass"], "com", md["com"], "Iyy_cog", md["Iyy"], "nodes x", len(md["x"]))
    out, (sp, con_last) = simulate(md, a.t_end, ramp=a.ramp, shape=a.shape, R_scale=a.R_scale)
    t, th, xo, zo = out[:, 0], out[:, 1], out[:, 2], out[:, 3]
    for tt in np.arange(0.05, a.t_end + 1e-9, max(0.05, a.t_end / 40)):
        i = np.argmin(abs(t - tt))
        print(f"{t[i]:.3f} pitch {th[i]:.4f} x {xo[i]*1e3:.3f} z {zo[i]*1e3:.3f} Fz {out[i,4]/1e3:.1f} ncon {out[i,5]:.0f}")
    sel = t >= max(a.fit_from, a.ramp + 0.2)
    fit = fit_osc(t[sel], th[sel])
    print("fit pitch", json.dumps(fit))
    con_end = con_last
    lm = linear_modes(md, None, a.R_scale)
    print("linear modes (all nodes in contact)", json.dumps(lm["complex"]), "undamped", lm["undamped_Hz"])
    lm2 = linear_modes(md, con_end, a.R_scale)
    print("linear modes (end contact columns, n=%d)" % int(con_end.sum()), json.dumps(lm2["complex"]))
    lm = dict(all_contact=lm, end_contact=lm2)
    res = dict(args=vars(a), fit=fit, modes=lm, end=dict(pitch_deg=float(th[-1]), x_mm=float(xo[-1] * 1e3),
               z_mm=float(zo[-1] * 1e3)), mean_last_period=float(th[t >= t[-1] - 1.0].mean()))
    print("mean pitch last 1 s", res["mean_last_period"])
    if a.out:
        np.savez(a.out + ".npz", out=out)
        Path(a.out + ".json").write_text(json.dumps(res, indent=1), "utf-8")


if __name__ == "__main__":
    main()
