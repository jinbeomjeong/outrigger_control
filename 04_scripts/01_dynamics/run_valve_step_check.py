"""10 Hz valve command steps on the L1 6-DoF plant: leg-force transients incl. rocking / twist (dynamics_model.md
rev. 32 supplement 2, section 5.16; hydraulics rod_side_pressure.md 18 used a heave 1-DoF).

Model (linear, about the static state; body x forward, y left, z up; gravity -z; leg order FL FR RL RR):
* configuration "legs" (levelled, crawler clear): the L1 ball-centre 6-DoF of l1r_reference.Level (rev. 13), leg
  springs k2 (head only = moving / L1) or k1 (L1-R LOCK), pad dashpot c_n (YAML, LOCK basis), bushing k_t, c_t;
* configuration "crawler+legs" (touch phase, top): crawler roller springs (YAML layout D, vertical only, no tangential
  restraint = R8) + the four legs k2 at the touch extension; preload shared by stiffness (static_unilateral);
* actuator option under test: command v_cmd held for 0.1 s (10 Hz ZOH), applied speed v_f = first-order lag tau_v of
  v_cmd (tau_v 0 = ideal valve), leg extension e' = v_f (rigid motor, no force limit);
* leg force N = k (e - a_z q) + c (v_f - a_z q') (pad force; cylinder force = N - m_rod g, rod inertia neglected);
  quasi-static N_qs(e) = elastic statics for the same e; dynamic d = N - N_qs.
Scenarios: one 10 Hz step (v_max -> 0 "stop" from steady motion, 0 -> v_max "start") of: all four legs (heave),
single legs, pairs; per leg the adversarial bound max_t sum_i |d_ji(t)| over sign patterns of simultaneous steps
(each leg stepping by v_max); a per-mode decomposition of d after the step and its 10 Hz alias frequencies.
Deterministic. usage: run_valve_step_check.py [out.json]   (dynamics-dev, E-cores, about 1 min)
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402
import l1r_reference as L  # noqa: E402
import run_reference as rr  # noqa: E402

TAUS = (0.0, 0.02, 0.05, 0.1, 0.15)
H = 2.0e-4          # exact (ZOH-of-input) discretisation step of the linear system
T_END = 3.0
FS = 10.0           # control / sample rate [Hz]
r = rr.r


class Plant:
    """Linear 6-DoF with leg extension inputs. pts: (n,3) spring points; first 4 = legs."""

    def __init__(self, M, K, C, az, k_leg, c_leg, name):
        self.M, self.K, self.C, self.az, self.k, self.c, self.name = M, K, C, az, k_leg, c_leg, name
        self.Bk = az.T @ np.diag(k_leg)
        self.Bc = az.T @ np.diag(c_leg)
        self.G = np.linalg.solve(K, self.Bk)            # q_qs = G e

    def modes(self):
        fd, zd = dm.complex_modes(self.M, self.K, self.C)
        return fd[:6], zd[:6]

    def system(self, tau):
        """Continuous A, B (input v_cmd), output matrices for N and N_qs; state [q, q', e, (v_f)]."""
        Minv = np.linalg.inv(self.M)
        n = 16 if tau == 0 else 20
        A = np.zeros((n, n)); B = np.zeros((n, 4))
        A[:6, 6:12] = np.eye(6)
        A[6:12, :6] = -Minv @ self.K
        A[6:12, 6:12] = -Minv @ self.C
        A[6:12, 12:16] = Minv @ self.Bk
        Cy = np.zeros((4, n)); Dy = np.zeros((4, 4))
        Cy[:, :6] = -np.diag(self.k) @ self.az
        Cy[:, 6:12] = -np.diag(self.c) @ self.az
        Cy[:, 12:16] = np.diag(self.k)
        if tau == 0:
            B[6:12] = Minv @ self.Bc
            B[12:16] = np.eye(4)
            Dy = np.diag(self.c)
        else:
            A[6:12, 16:20] = Minv @ self.Bc
            A[12:16, 16:20] = np.eye(4)
            A[16:20, 16:20] = -np.eye(4) / tau
            B[16:20] = np.eye(4) / tau
            Cy[:, 16:20] = np.diag(self.c)
        Cqs = np.zeros((4, n))
        Cqs[:, 12:16] = np.diag(self.k) - np.diag(self.k) @ self.az @ self.G
        return A, B, Cy, Dy, Cqs

    def steady(self, v, tau):
        """State of steady motion at leg speeds v (e = 0 at t = 0)."""
        a = self.G @ v
        b = np.linalg.solve(self.K, self.Bc @ v - self.C @ a)
        x = np.r_[b, a, np.zeros(4)]
        return x if tau == 0 else np.r_[x, v]

    def response(self, v0, v1, tau):
        """Command v0 (steady) -> v1 at t = 0 held: dynamic leg force d(t) (4, nt)."""
        A, B, Cy, Dy, Cqs = self.system(tau)
        n = A.shape[0]
        Z = np.zeros((n + 4, n + 4)); Z[:n, :n] = A * H; Z[:n, n:] = B * H
        E = expm(Z)
        Phi, Gam = E[:n, :n], E[:n, n:]
        x = self.steady(v0, tau)
        nt = int(round(T_END / H)) + 1
        out = np.empty((4, nt))
        u = np.asarray(v1, float)
        for k in range(nt):
            out[:, k] = Cy @ x + Dy @ u - Cqs @ x
            x = Phi @ x + Gam @ u
        return out

    def modal_split(self, v0, v1, tau):
        """Amplitude of each oscillatory eigen-pair in d_j after the step (free system with v_cmd = v1 held)."""
        A, B, Cy, Dy, Cqs = self.system(tau)
        x0 = self.steady(v0, tau)
        u = np.asarray(v1, float)
        # shift to the particular (ramp) solution of the held input: remove it by differencing - the response to a
        # held input is homogeneous + particular; the particular part of d is constant (viscous offset) -> drop it
        lam, V = np.linalg.eig(A)
        W = np.linalg.inv(V)
        # particular solution for constant u: A x_p' ... use the steady state of the new command
        xp = self.steady(u, tau)
        c = W @ (x0 - xp)
        Cd = Cy - Cqs
        res = []
        for idx in np.where(lam.imag > 1e-6)[0]:
            amp = 2 * np.abs((Cd @ V[:, idx]) * c[idx])
            f = abs(lam[idx]) / (2 * math.pi)
            res.append((f, -lam[idx].real / abs(lam[idx]), amp))
        res.sort()
        return res


def alias(f):
    return abs(f - FS * round(f / FS))


def legs_plant(p, geo, lp, lvl, state):
    lv = L.Level(p, geo, lp, lvl)
    m = lv.mats[state]
    k = lp["k1"] if state == "LOCK" else lp["k2"]
    return Plant(lv.M, m["K"], m["C"], lv.az, k, lp["cn"], f"legs {lvl} {state}"), lv


def crawler_plant(p, geo, lp):
    """Touch phase: legs at the touch extension (pads just loaded) + crawler roller springs, preload by stiffness."""
    g, xy = geo.g, geo.pad_xy
    e_t = geo.touch_extension
    bw = dm.body_with_rods(p, geo, "top", e_t)
    cxy, ck, cc = dm.crawler_points(p)
    gaps = dm.crawler_gaps(p)
    act = gaps <= 0
    hb = rr._ball_heights(p)
    zl = geo.pad_z_retracted - e_t + hb
    pts = np.vstack([np.column_stack([xy, zl]), np.column_stack([cxy[act], np.full(act.sum(), geo.crawler_bottom_z)])])
    kv = np.r_[lp["k2"], ck[act]]
    cv = np.r_[lp["cn"], cc[act]]
    F, _q, _a = dm.static_unilateral(pts[:, :2], kv, np.zeros(len(kv)), bw.mass * g, bw.com[:2])
    M = dm.mass_6dof(bw)
    K = np.zeros((6, 6)); C = np.zeros((6, 6)); az_all = []
    for i in range(len(pts)):
        ax, ay, az = dm.a_vec(pts[i] - bw.com)
        K += kv[i] * np.outer(az, az); C += cv[i] * np.outer(az, az)
        K[3:, 3:] -= F[i] * dm._hz(pts[i] - bw.com)
        if i < 4:
            K += lp["kt"][i] * (np.outer(ax, ax) + np.outer(ay, ay))
            C += lp["ct"][i] * (np.outer(ax, ax) + np.outer(ay, ay))
        az_all.append(az)
    az_all = np.array(az_all)
    return Plant(M, K, C, az_all[:4], lp["k2"], lp["cn"], "crawler+legs top (touch, k2)"), F


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    lp = L.leg_parameters(p, geo)
    vmax = float(p["actuator"]["max_speed_m_s"])
    Fmin = float(p["control"]["F_min_cylinder_N"])
    out = {"meta": {"model": " ".join(__doc__.split("\n\n")[1].split()), "v_max_m_s": vmax, "F_min_N": Fmin,
                    "taus_s": list(TAUS), "dt_discretisation_s": H, "window_s": T_END, "sample_rate_Hz": FS,
                    "units": "forces N (pad = cylinder + m_rod g; dynamic part d = N - N_qs), frequencies Hz"}}
    plants = {}
    for lvl in dm.LEVELS:
        for st in ("FLOOR", "LOCK"):
            pl, lv = legs_plant(p, geo, lp, lvl, st)
            plants[pl.name] = pl
            if st == "FLOOR" and lvl == "top":
                lv_top = lv
    pc, Fc = crawler_plant(p, geo, lp)
    plants[pc.name] = pc
    out["meta"]["crawler+legs preload (legs FL..RR, crawler sum) N"] = [r(Fc[:4]), r(Fc[4:].sum())]
    # self-check: legs FLOOR top modes = reference FLOOR (l1r block)
    fd, zd = plants["legs top FLOOR"].modes()
    if np.abs(fd - lv_top.mats["FLOOR"]["fd"][:6]).max() > 1e-9:
        raise RuntimeError("legs plant does not reproduce the FLOOR modes")
    out["modes"] = {nm: {"f_Hz": r(pl.modes()[0], 5), "zeta": r(pl.modes()[1], 4),
                         "alias_10Hz": r([alias(f) for f in pl.modes()[0]], 4)} for nm, pl in plants.items()}
    # 1-DoF check (hydraulics 18.1): ideal stop, Delta v sqrt(k m_eff) with omega 7.4 Hz
    w = 2 * math.pi * 7.4
    out["meta"]["heave_1dof_closed_form_stop_N (FL, RL)"] = r([vmax * lp["k2"][0] / w, vmax * lp["k2"][2] / w])
    one = np.zeros(4)
    sc = {"all4 (heave)": np.ones(4), "FL": np.array([1, 0, 0, 0.]), "RL": np.array([0, 0, 1, 0.]),
          "front pair FL+FR": np.array([1, 1, 0, 0.]), "left pair FL+RL": np.array([1, 0, 1, 0.]),
          "diagonal FL+RR": np.array([1, 0, 0, 1.]), "twist n (+-)": np.sign(dm.twist_vector(geo.pad_xy))}
    res = {}
    for nm, pl in plants.items():
        ent = {}
        for tau in TAUS:
            row = {}
            unit = [pl.response(np.eye(4)[i] * vmax, one, tau) for i in range(4)]
            for snm, s in sc.items():
                d_stop = sum(unit[i] * s[i] for i in range(4))
                row[snm] = {"stop_min_N": r(d_stop.min(axis=1), 4), "stop_max_N": r(d_stop.max(axis=1), 4),
                            "stop_peak_abs_N": r(np.abs(d_stop).max(axis=1), 4)}
                if snm == "all4 (heave)":
                    d_st = sum(pl.response(one, np.eye(4)[i] * vmax, tau) for i in range(4))
                    row[snm]["start_peak_abs_N"] = r(np.abs(d_st).max(axis=1), 4)
            bound = np.abs(np.array(unit)).sum(axis=0).max(axis=1)     # per leg j: max_t sum_i |d_ji|
            row["adversarial bound (all legs step v_max, worst signs) N"] = r(bound, 4)
            row["adversarial bound / F_min"] = r(bound / Fmin, 3)
            ent[f"tau {tau:g}"] = row
        res[nm] = ent
        print(nm, "done", round(time.perf_counter() - t0, 1), "s", flush=True)
    out["step_transients (one 10 Hz step, v_max)"] = res
    # modal split / aliasing (legs top and crawler+legs; stop of all4, FL, adversarial unit FL)
    al = {}
    for nm in ("legs top FLOOR", "legs top LOCK", "legs middle LOCK", "legs bottom LOCK", "crawler+legs top (touch, k2)"):
        pl = plants[nm]
        ent = {}
        for tau in (0.0, 0.1):
            for snm in ("all4 (heave)", "FL", "front pair FL+FR", "left pair FL+RL"):
                s = sc[snm]
                ms = pl.modal_split(s * vmax, one, tau)
                ent[f"tau {tau:g} / {snm}"] = [{"f_Hz": r(f, 4), "zeta": r(z, 3), "alias_Hz": r(alias(f), 3),
                                                 "amp_per_leg_N": r(a, 3)} for f, z, a in ms]
        al[nm] = ent
    out["modal_split_after_stop (amplitude of each mode in d_j, v_max stop)"] = al
    out["meta"]["runtime_s"] = round(time.perf_counter() - t0, 1)
    dst = Path(sys.argv[1]) if len(sys.argv) > 1 else dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "valve_step_check.json"
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("written", dst)


if __name__ == "__main__":
    main()
