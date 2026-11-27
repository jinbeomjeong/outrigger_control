"""REJECTED first attempt (kept as record; run as g04_reduced_model.py, renamed g04a_3dof_model.py):
3-DoF model without lateral pad restraint reached re-contact 0.14 s (stored 0.19 s) and window 0.18 s
(stored 0.27 s) -> replaced by the 5-DoF model g00_rock_model.py (lateral pad springs, P-delta).

G' window shift, part 4: independent reduced model (NOT the harness) of the 3-point diagonal
rocking after a fast floor drop under one front pad, used only for DIFFERENCES between the stored
condition (30 mm / 0.05 s) and the held-out shapes (25 mm / 0.05 s, 30 mm / 0.04 s).

Model (own code, numpy, no project import):
  rigid body, 3 DoF (heave w up, roll phi about +x, pitch theta about +y, right-handed, small angles),
  mass / CoM / inertia: YAML superstructure.auger_levels.bottom (CoM xy, Ixx, Iyy, Ixy about CoM);
  4 unilateral leg springs at the pad xy (legs.*.pad_bottom_center), stiffness k_lock (YAML
  contact.rigid_floor.L1.derivation.k_lock_N_m) x calibration factor, dashpot c (YAML cn_per_pad
  LOCK; event leg C_MOVE while its valve is on, as r51 DAMP_SWITCH) x factor;
  preload = YAML static_leg_loads (bottom); floor of the event pad: Poly345 drop d over ramp T;
  leg extension prescribed from the stored rerun valve outputs (all 4 legs, same history relative to
  the event in every shape: the controller cannot see the floor depth while the pad is airborne).
  Pad vertical position z_i = w + y_i phi - x_i theta; compression
  delta_i = delta0_i - z_i + g_i(t) + e_i(t); F_i = max(0, k delta + c d(delta)/dt) if delta > 0.
Integrator: RK4, fixed dt (default 2.5e-5 s; convergence check with dt/2), contact switching inside.
Calibration: k and c factors on a grid, matched to the stored V0 rerun features of the same key
(lift, re-contact, peak, re-lift of the event leg; lift / land of the diagonal).
Usage: python -I -B g04_reduced_model.py <rerun_dir> <out_folder>
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

YAML = Path(r"C:\workspace\outrigger_control\02_params\rexome33.yaml")
LEGS = ("FL", "FR", "RL", "RR")
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
G = 9.81
F_EXIT = 14414.6
rerun, out = Path(sys.argv[1]), Path(sys.argv[2])

# --- parameters typed from the YAML (read with Read, values copied; see report 'inputs') -------------
M = 38400.8366
COM = np.array([0.460190503, -0.00136232581])
I2 = np.array([[176282.442, -941.461576], [-941.461576, 331469.51]])   # bottom, about CoM (roll, pitch)
PAD = np.array([[2.29376465, 1.32376465], [2.29376465, -1.32376465], [-2.556, 1.1679], [-2.556, -1.2429]])
K_LOCK = np.array([33929017.0, 33929017.0, 26402111.0, 26402111.0])
C_LOCK = np.array([34403.519, 34403.519, 30348.4527, 30348.4527])
C_MOVE = np.array([100206.065477022, 100206.065477022, 86949.0144383396, 86949.0144383396])
F0 = np.array([118099.1, 116106.0, 72096.68, 70281.81])      # bottom static_leg_loads (equal springs)
REL = PAD - COM
X, Y = REL[:, 0], REL[:, 1]
I2inv = np.linalg.inv(I2)


def poly345(tau):
    tau = np.clip(tau, 0.0, 1.0)
    return 10 * tau**3 - 15 * tau**4 + 6 * tau**5


def dpoly345(tau):
    inside = (tau > 0) & (tau < 1)
    return np.where(inside, 30 * tau**2 - 60 * tau**3 + 30 * tau**4, 0.0)


class Valve:
    """Prescribed leg extension e_i(t) and rate from a stored rerun (1 ms valve output, m/s)."""

    def __init__(self, t, v):
        self.t = t
        self.v = v
        e = np.zeros_like(v)
        e[1:] = np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(t)[:, None], axis=0)
        self.e = e

    def __call__(self, tq):
        if tq <= self.t[0]:
            return np.zeros(4), np.zeros(4)
        i = min(int(np.searchsorted(self.t, tq)), len(self.t) - 1)
        return self.e[i], self.v[i]


def simulate(leg, depth, ramp, kf, cf, valve, t_end=0.8, dt=2.5e-5, damp_switch=True):
    k = K_LOCK * kf
    d0 = F0 / k
    ns = int(round(t_end / dt))
    s = np.zeros(6)                       # w, phi, theta, wd, phid, thetad
    rec_t = np.empty(ns + 1)
    rec_F = np.empty((ns + 1, 4))
    rec_gap = np.empty((ns + 1, 4))

    def forces(t, s):
        w, ph, th, wd, phd, thd = s
        z = w + Y * ph - X * th
        zd = wd + Y * phd - X * thd
        g = np.zeros(4)
        gd = np.zeros(4)
        g[leg] = -depth * poly345(t / ramp)
        gd[leg] = -depth * dpoly345(t / ramp) / ramp
        e, ed = valve(t) if valve is not None else (np.zeros(4), np.zeros(4))
        dl = d0 - z + g + e
        dld = -zd + gd + ed
        c = C_LOCK * cf
        if damp_switch:
            c = np.where(np.abs(ed) > 1e-6, C_MOVE * cf, c)
        F = np.where(dl > 0, np.maximum(k * dl + c * dld, 0.0), 0.0)
        return F, dl

    def rhs(t, s):
        F, _ = forces(t, s)
        acc_w = (F.sum() - M * G) / M
        tq = np.array([np.dot(F, Y), -np.dot(F, X)])
        acc_r = I2inv @ tq
        return np.array([s[3], s[4], s[5], acc_w, acc_r[0], acc_r[1]])

    t = 0.0
    for n in range(ns + 1):
        F, dl = forces(t, s)
        rec_t[n] = t
        rec_F[n] = F
        rec_gap[n] = np.where(dl > 0, 0.0, -dl)
        if n == ns:
            break
        k1 = rhs(t, s)
        k2 = rhs(t + dt / 2, s + dt / 2 * k1)
        k3 = rhs(t + dt / 2, s + dt / 2 * k2)
        k4 = rhs(t + dt, s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        t += dt
    return rec_t, rec_F, rec_gap


def features(t, F, gap, leg):
    dg = DIAG[leg]
    Fe = F[:, leg] - 1050.0          # true F column = contact - W_rod (W_rod ~ 1.05 kN, front)
    air = F[:, leg] <= 0
    out = {}
    il = np.flatnonzero((t >= 0) & air)
    if not il.size:
        return None
    i_lift = il[0]
    ib = np.flatnonzero((t > t[i_lift]) & ~air)
    if not ib.size:
        return None
    i_back = ib[0]
    ir = np.flatnonzero((t > t[i_back]) & (Fe >= F_EXIT))
    irl = np.flatnonzero((t > t[i_back]) & air)
    if not ir.size or not irl.size:
        return None
    i_rel, i_relift = ir[0], irl[0]
    m = (t > t[i_rel]) & (t < t[i_relift]) & (Fe >= F_EXIT)
    i_hold = np.flatnonzero(m)[-1]
    out.update(t_lift=t[i_lift], t_contact=t[i_back], t_reload=t[i_rel], t_hold=t[i_hold], t_relift=t[i_relift],
               F_peak=Fe[i_back:i_relift].max() / 1e3, t_peak=t[i_back + np.argmax(Fe[i_back:i_relift])],
               gap_max=gap[i_lift:i_back, leg].max() * 1e3,
               v_imp=(gap[max(i_back - 200, 0), leg] - gap[i_back - 1, leg]) / (t[i_back - 1] - t[max(i_back - 200, 0)]))
    airD = F[:, dg] <= 0
    a = np.flatnonzero((t > 0) & airD)
    if a.size:
        b = np.flatnonzero((t > t[a[0]]) & ~airD)
        out.update(d_lift=t[a[0]], d_land=t[b[0]] if b.size else np.nan)
    else:
        out.update(d_lift=np.nan, d_land=np.nan)
    return {k: float(v) for k, v in out.items()}


def load_valve(stem):
    z = np.load(rerun / "logs" / f"{stem}_rows.npz")
    rows, t_ev = z["rows"], float(z["t_ev"])
    t = rows[:, 0] - t_ev
    w = (t >= -0.001) & (t <= 1.0)
    return Valve(t[w], rows[w, 9:13]), t, rows


def stored_features(t, rows, leg):
    F = rows[:, 1:5]
    gap = rows[:, 13:17]
    w = (t >= -0.01) & (t <= 0.8)
    return features(t[w], F[w], gap[w], leg)


if __name__ == "__main__":
    t0 = time.time()
    cases = [("R12_bottom-FR-Fs4-o0.0-RE1bF-ready_V0", 1), ("R12_bottom-FL-Fs2-o0.0-RE1bF-ready_V0", 0),
             ("R12_bottom-FR-Fs4-o0.075-RE1bF-ready_V0", 1), ("R12_bottom-FL-Fs2-o0.075-RE1bF-ready_V0", 0)]
    keys = ["t_lift", "t_contact", "t_reload", "t_hold", "t_relift", "F_peak", "t_peak", "gap_max", "v_imp",
            "d_lift", "d_land"]
    W = {"t_lift": 1e3, "t_contact": 1e3, "t_reload": 0, "t_hold": 0, "t_relift": 1e3, "F_peak": 0.05,
         "t_peak": 0, "gap_max": 0.5, "v_imp": 0, "d_lift": 1e3, "d_land": 1e3}
    rows_out = []
    calib = []
    for stem, leg in cases[:2]:
        valve, t_s, rows_s = load_valve(stem)
        ref = stored_features(t_s, rows_s, leg)
        best = None
        for kf in (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2):
            for cf in (0.5, 1.0, 2.0):
                tt, FF, gg = simulate(leg, 0.030, 0.05, kf, cf, valve, dt=1e-4)
                f = features(tt, FF, gg, leg)
                if f is None:
                    continue
                cost = sum(W[k] * (f[k] - ref[k]) ** 2 for k in keys if W[k] and np.isfinite(f[k]) and np.isfinite(ref[k]))
                calib.append({"stem": stem, "kf": kf, "cf": cf, "cost": cost, **{k: round(f[k], 4) for k in keys}})
                if best is None or cost < best[0]:
                    best = (cost, kf, cf, f)
        rows_out.append({"stem": stem, "ref": ref, "best_kf": best[1], "best_cf": best[2], "best": best[3]})
        print(json.dumps({"stem": stem, "ref": {k: round(ref[k], 4) for k in keys},
                          "best": {"kf": best[1], "cf": best[2], **{k: round(best[3][k], 4) for k in keys}}}))
    with (out / "g04_calibration_grid.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(calib[0]))
        w.writeheader()
        w.writerows(calib)
    (out / "g04_calibration.json").write_text(json.dumps(rows_out, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"status": "ok", "elapsed_s": round(time.time() - t0, 1)}))
