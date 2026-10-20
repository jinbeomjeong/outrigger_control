"""Independent nonlinear time-domain check of the linear reference (model R1, top level).

Nonlinear 6-DoF rigid body (superstructure + rods, rods rigid), 4 unilateral pad contacts:
  normal  F_n = max(0, kv*pen + cv*pen_dot)   (pen = penetration of the pad bottom centre, world z)
  tangent F_t = -kh*(p_xy - anchor_xy) - ch*v_xy  (stick, anchor = first contact point; no slip)
Rotation: quaternion (w, x, y, z) scalar first, body->world. Angular velocity in body frame.
Gravity (0, 0, -9.80665) m/s^2.

Checks
  T1 static loads after damped settling vs linear static solution (equal stiffness)
  T2 free vibration frequencies (roll-sway, pitch-surge, heave modes) vs linear eigenvalues (R1)
  T3 energy conservation of the undamped free vibration
  T4 load change for +1 mm extension of FL vs linear sensitivity dF/d(delta)
Writes 06_analysis/00_dynamics/timedomain_check.json.

Run: conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_timedomain_check.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "timedomain_check.json"


def quat_to_R(q):
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def quat_dot(q, wb):
    w, x, y, z = q
    p, qq, r = wb
    return 0.5 * np.array([-x * p - y * qq - z * r, w * p + y * r - z * qq, w * qq + z * p - x * r, w * r + x * qq - y * p])


class Rig:
    def __init__(self, body, pads_body, kv, kh, cv, ch, g, z_ground):
        self.m = body.mass
        self.I = body.inertia
        self.Iinv = np.linalg.inv(body.inertia)
        self.r = pads_body - body.com  # pad bottom centres relative to the CoM (body axes)
        self.kv, self.kh = np.broadcast_to(kv, (4,)).astype(float), np.broadcast_to(kh, (4,)).astype(float)
        self.cv, self.ch = cv, ch
        self.g = g
        self.zg = z_ground
        self.anchor = None

    def pad_state(self, y):
        p, q, v, wb = y[:3], y[3:7], y[7:10], y[10:13]
        R = quat_to_R(q / np.linalg.norm(q))
        P = p + self.r @ R.T
        V = v + np.cross(R @ wb, P - p)
        return R, P, V

    def forces(self, y):
        R, P, V = self.pad_state(y)
        pen = self.zg - P[:, 2]
        F = np.zeros((4, 3))
        for i in range(4):
            if pen[i] > 0:
                fn = self.kv[i] * pen[i] - self.cv * V[i, 2]
                F[i, 2] = max(fn, 0.0)
                F[i, :2] = -self.kh[i] * (P[i, :2] - self.anchor[i]) - self.ch * V[i, :2]
        return R, P, F, pen

    def rhs(self, t, y):
        p, q, v, wb = y[:3], y[3:7], y[7:10], y[10:13]
        R, P, F, _ = self.forces(y)
        Ftot = F.sum(0) + np.array([0, 0, -self.m * self.g])
        tau_w = np.cross(P - p, F).sum(0)
        tau_b = R.T @ tau_w
        wdot = self.Iinv @ (tau_b - np.cross(wb, self.I @ wb))
        return np.concatenate([v, quat_dot(q, wb), Ftot / self.m, wdot])

    def energy(self, y):
        p, q, v, wb = y[:3], y[3:7], y[7:10], y[10:13]
        R, P, V = self.pad_state(y)
        pen = np.clip(self.zg - P[:, 2], 0, None)
        e = 0.5 * self.m * v @ v + 0.5 * wb @ self.I @ wb + self.m * self.g * p[2]
        e += 0.5 * (self.kv * pen**2).sum()
        e += 0.5 * (self.kh * ((P[:, :2] - self.anchor) ** 2).sum(1) * (pen > 0)).sum()
        return e


def euler_small(R):
    """roll, pitch, yaw (ZYX intrinsic = XYZ extrinsic) from R."""
    pitch = -math.asin(R[2, 0])
    roll = math.atan2(R[2, 1], R[2, 2])
    yaw = math.atan2(R[1, 0], R[0, 0])
    return np.array([roll, pitch, yaw])


def run_case(p, geo, name, kv, kh, deltas_mm):
    """T1-T4 for one stiffness configuration (top level). kv, kh: per-pad contact stiffness (4,)."""
    g = geo.g
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    bw = dm.body_with_rods(p, geo, "top", e_op)
    pads = np.column_stack([geo.pad_xy, geo.pad_z_retracted - e_op])
    kv = np.asarray(kv, float); kh = np.asarray(kh, float)
    c_settle = 2 * 0.5 * math.sqrt(kv.mean() * bw.mass / 4)  # strong damping for settling (heave zeta 0.5)
    z_ground = pads[:, 2].mean()  # floor at the nominal pad height (pads exactly touching at q=0)
    rig = Rig(bw, pads, kv, kh, c_settle, c_settle, g, z_ground)
    rig.anchor = pads[:, :2].copy()
    y0 = np.concatenate([bw.com, [1, 0, 0, 0], np.zeros(6)])
    opts = dict(method="DOP853", rtol=1e-10, atol=1e-12)
    T_settle = 8.0 if kv.mean() < 1e8 else 4.0  # longer settling for soft (lumped) contacts
    sol = solve_ivp(rig.rhs, (0, T_settle), y0, **opts)
    ys = sol.y[:, -1].copy(); ys[7:] = 0.0
    _, _, F, pen = rig.forces(ys)
    F_lin, q_lin, _ = dm.static_loads(kv, geo.pad_xy, bw.mass * g, bw.com[:2])
    res = {"kv_N_m": kv.tolist(), "kh_N_m": kh.tolist(), "settle_time_s": T_settle}
    res["T1_static"] = {
        "F_nonlinear_N": F[:, 2].round(2).tolist(), "F_linear_N": F_lin.round(2).tolist(),
        "max_rel_diff": float(np.max(np.abs(F[:, 2] - F_lin) / F_lin)),
        "sum_F_minus_W_rel": float(abs(F[:, 2].sum() - bw.mass * g) / (bw.mass * g)),
        "penetration_mm": (pen * 1e3).round(5).tolist(),
        "attitude_deg (roll, pitch, yaw)": np.degrees(euler_small(quat_to_R(ys[3:7]))).round(6).tolist(),
        "attitude_linear_deg (roll, pitch)": np.degrees(q_lin[1:]).round(6).tolist(),
    }
    # ---- T2/T3: undamped free vibration in single linear modes
    rig.cv = rig.ch = 0.0
    rig.anchor = rig.pad_state(ys)[1][:, :2].copy()  # re-anchor at equilibrium (no horizontal preload)
    Kl = dm.stiffness_6dof(bw, pads, kv, kh, F_lin)
    Ml = dm.mass_6dof(bw)
    w2, f_lin, Phi, cls, _ = dm.modal(Ml, Kl, dm.DOF6)
    T2 = {}
    for j in range(6):
        v0 = Phi[:, j] / np.abs(Phi[:, j]).max() * 1e-3
        y1 = ys.copy(); R0 = quat_to_R(ys[3:7])
        y1[7:10] = v0[:3]; y1[10:13] = R0.T @ v0[3:]
        Tend = 12.0 / f_lin[j]
        tt = np.linspace(0, Tend, 4000)
        s = solve_ivp(rig.rhs, (0, Tend), y1, t_eval=tt, **opts)
        qd = np.vstack([s.y[7:10], np.array([quat_to_R(s.y[3:7, i]) @ s.y[10:13, i] for i in range(len(tt))]).T])
        eta = Phi[:, j] @ Ml @ qd
        zc = np.where(np.diff(np.sign(eta)) != 0)[0]
        tz = [tt[i] - eta[i] * (tt[i + 1] - tt[i]) / (eta[i + 1] - eta[i]) for i in zc]
        f_meas = (len(tz) - 1) / 2 / (tz[-1] - tz[0])
        E = np.array([rig.energy(s.y[:, i]) for i in range(len(tt))])
        Ekin0 = 0.5 * v0 @ Ml @ v0
        T2[f"mode{j+1} {list(cls[j].keys())}"] = {
            "f_linear_Hz": float(f_lin[j]), "f_nonlinear_Hz": float(f_meas),
            "rel_err": float(abs(f_meas - f_lin[j]) / f_lin[j]),
            "energy_drift_rel_to_Ekin0": float(np.abs(E - E[0]).max() / Ekin0)}
    res["T2_T3_free_vibration"] = T2
    # ---- T4: FL extension (pad pushed down in the body frame), damped re-settle
    S = dm.load_sensitivity(kv, geo.pad_xy)
    Q = dm.attitude_sensitivity(kv, geo.pad_xy)
    rig.cv = rig.ch = c_settle
    r0 = rig.r.copy()
    for k_, dmm in enumerate(deltas_mm):
        rig.r = r0.copy(); rig.r[0, 2] -= dmm * 1e-3
        s = solve_ivp(rig.rhs, (0, T_settle), ys, **opts)
        y4 = s.y[:, -1].copy(); y4[7:] = 0
        _, _, F4, _ = rig.forces(y4)
        att = np.degrees(euler_small(quat_to_R(y4[3:7])) - euler_small(quat_to_R(ys[3:7])))
        F_as, q_as, act = dm.static_loads(kv, geo.pad_xy, bw.mass * g, bw.com[:2], delta=np.array([dmm * 1e-3, 0, 0, 0]))
        entry = {"F_after_nonlinear_N": F4[:, 2].round(1).tolist(),
                 "F_after_static_active_set_N": F_as.round(1).tolist(),
                 "legs_in_contact (static)": act.tolist(),
                 "max_rel_err_vs_static (vs W/4)": float(np.abs(F4[:, 2] - F_as).max() / (bw.mass * g / 4)),
                 "droll_dpitch_deg_nonlinear": att[:2].round(6).tolist(),
                 "droll_dpitch_deg_static": np.degrees(q_as[1:] - q_lin[1:]).round(6).tolist()}
        if k_ == 0:
            entry["dF_nonlinear_N"] = (F4[:, 2] - F[:, 2]).round(1).tolist()
            entry["dF_linear_N"] = (S[:, 0] * dmm * 1e-3).round(1).tolist()
            entry["droll_dpitch_deg_linear"] = np.degrees(Q[1:, 0] * dmm * 1e-3).round(6).tolist()
        res[f"T4_FL_plus_{dmm}mm"] = entry
    return res


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    kc = dm.k_concrete_westergaard()["k_slab_N_m"]
    ko_eff = dm.series(dm.k_oil(e_op), dm.k_rod(), dm.ASSUMPTIONS["frame_bracket_stiffness_N_m"])
    k_L1 = dm.series(ko_eff, kc)
    kt_L1 = dm.series(dm.k_leg_lateral_legs(geo, e_op, False), kc)
    res = {"meta": {"script": "04_scripts/01_dynamics/run_timedomain_check.py",
                    "model": "nonlinear 6-DoF rigid body (superstructure + rods, top level), 4 unilateral penalty pads",
                    "integrator": "solve_ivp DOP853 rtol 1e-10 atol 1e-12", "quaternion_order": "wxyz (scalar first)"}}
    # L1 (temporary default): 5 mm (linear range) and 15 mm (beyond the 14.08 mm lift-off threshold)
    res["L1_rigid_motor_lumped_contact"] = run_case(p, geo, "L1", k_L1, kt_L1, (5.0, 15.0))
    # R1 (informational): 0.5 mm and 1.0 mm (threshold 0.915 mm)
    res["R1_rigid_motor_concrete"] = run_case(p, geo, "R1", np.full(4, kc), np.full(4, kc), (0.5, 1.0))
    res["meta"]["runtime_s"] = round(time.perf_counter() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
