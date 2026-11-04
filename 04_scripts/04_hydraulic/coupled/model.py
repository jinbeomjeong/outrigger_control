"""Four-leg shared-pump flow-saturation model, numpy RK4 (hydraulic_coupling.md sec. 3).

States (GAUGE pressures, s = extension from the barrel, positive extending):
  q   = [z, phi, theta]            body heave, roll, pitch at the CoM
  dq  = time derivative of q
  s, v                             extension and extension speed per leg
  p_h, p_r                         head and rod chamber pressure per leg
  p_P                              P gallery pressure

The compensators and the inlet compensator are quasi-static (user decision: no LS
or compensator dynamics). Commands are signed fractions of v_max per leg:
u > 0 extends (P->A head, B->T rod), u = 0 locks, u < 0 retracts (P->B rod, head
outflow metered by the pilot-operated check, simplified, numpy and hand only).
Params.law selects the distribution law, Params.flow_limit False gives ample supply.

A run takes a Scenario (constant commands, static loads) or a replay.Replay
(recorded commands and cylinder forces). Both give command(t), load(t), s_start,
coupled, eta_v, t_end.
"""
from __future__ import annotations

import csv
import math
import time
from pathlib import Path

import numpy as np

from flow_share import smin
from params import LEGS, Params

EPS_DP = 1.0e2  # Pa, orifice regularisation at zero pressure drop
TAU_RETRACT = 5.0e-3  # s, relaxation of the simplified retract branch


def initial_state(p: Params, sc) -> np.ndarray:
    F0 = sc.load_fn(p)(sc.t_start)
    u = sc.command_fn(p)(sc.t_start + 1e-3)
    p_r0 = np.full(4, p.p_T)
    p_h0 = (F0 + p.A_r * p_r0) / p.A_h
    active = u != 0
    p_L = np.where(u < 0, p_r0, p_h0)
    ls = max(p.p_T, float(p_L[active].max()) if active.any() else p.p_T)
    p_P0 = min(ls, p.p_relief) + p.dp_unl
    return np.concatenate([np.zeros(6), sc.s_start(p), np.zeros(4), p_h0, p_r0, [p_P0]])


def spool_drop(p: Params, K: np.ndarray, D: np.ndarray) -> np.ndarray:
    """Quasi-static compensator + spool: spool pressure drop y for D = p_P - p_L (or - LS)."""
    D_pos = np.maximum(D, 0.0)
    if p.law == "proportional":  # flow sharing: the same spool drop on every section
        return np.maximum(smin(p.dp_comp, D_pos, p.width), 0.0)
    y_open = D_pos * p.X_comp**2 / (p.X_comp**2 + K**2)  # compensator fully open, series orifices
    return np.maximum(smin(p.dp_comp, y_open, p.width), 0.0)


def make_rhs(p: Params, sc):
    load_fn = sc.load_fn(p)
    command = sc.command_fn(p)
    K_ext = p.K_spool
    K_ret = K_ext * p.A_r / p.A_h  # ASSUMPTION: the command gives the same speed in both directions
    gain = 1.0 if sc.coupled else 0.0
    Q_p = p.Q_pump(sc.eta_v)
    M = np.array([p.mass, p.I_roll, p.I_pitch])
    area_ratio = p.A_h / p.A_r
    s_ref = sc.s_start(p)

    def rhs(t: float, y: np.ndarray, out: dict | None = None) -> np.ndarray:
        dq = y[3:6]
        s, v, p_h, p_r, p_P = y[6:10], y[10:14], y[14:18], y[18:22], y[22]
        q = y[0:3]
        w = q[0] + p.yp * q[1] - p.xp * q[2]
        dw = dq[0] + p.yp * dq[1] - p.xp * dq[2]
        dF = gain * (p.k_st * (s - s_ref - w) + p.c_g * (v - dw))
        F_ext = load_fn(t) + dF

        u = command(t)
        ext, ret = u > 0, u < 0
        active = ext | ret
        abs_u = np.abs(u)
        K = np.where(ret, K_ret, K_ext) * abs_u
        p_L = np.where(ret, p_r, p_h)
        ls = min(max(p.p_T, float(p_L[active].max()) if active.any() else p.p_T), p.p_relief)
        D = np.full(4, p_P - ls) if p.law == "proportional" else p_P - p_L
        ydrop = spool_drop(p, K, D)
        Q_in = K * np.sqrt(ydrop)
        # extending: rod side drains through B->T, chambers from the flow balance
        dp_r_t = p_r - p.p_T
        Q_bt = K_ext * abs_u * p.bt_ratio * dp_r_t / np.sqrt(np.abs(dp_r_t) + EPS_DP)
        Q_head = np.where(ext, Q_in, 0.0)
        Q_rod = np.where(ext, -Q_bt, 0.0)

        F_cyl = p.A_h * p_h - p.A_r * p_r
        hose = np.where(active, p.V_hose, 0.0)
        V_h = p.A_h * p.L0h + hose + p.A_h * s
        V_r = p.A_r * p.L0r + hose + p.A_r * (p.stroke - s)
        dp_h = p.beta / V_h * (Q_head - p.A_h * v)
        dp_r = p.beta / V_r * (p.A_r * v + Q_rod)
        dv = (F_cyl - F_ext) / p.m_rod
        # retracting (simplified, flow consumption only): speed from the rod inflow, rod side held
        # at the check valve pilot threshold, head pressure from the force balance
        dv = np.where(ret, (-Q_in / p.A_r - v) / TAU_RETRACT, dv)
        dp_r = np.where(ret, (p.p_pilot - p_r) / TAU_RETRACT, dp_r)
        dp_h = np.where(ret, ((F_ext + p.A_r * p_r) / p.A_h - p_h) / TAU_RETRACT, dp_h)

        ddq = np.array([dF.sum(), (p.yp * dF).sum(), (-p.xp * dF).sum()]) / M

        dpP_T = max(p_P - p.p_T, 0.0)
        b_u = p.Cs_unl + p.Cf_unl * dpP_T
        x_u = min(max((p_P - p.dp_unl - ls) / b_u, 0.0), p.X_unl)
        Q_byp = x_u * math.sqrt(dpP_T)
        dp_P = p.beta / p.V_g * (Q_p - Q_in.sum() - Q_byp)
        if out is not None:
            out.update(Q_in=Q_in, Q_out=np.where(ext, Q_bt, np.where(ret, area_ratio * Q_in, 0.0)), Q_byp=Q_byp,
                       F_ext=F_ext, Q_p=Q_p, ls=ls, u=u)
        return np.concatenate([dq, ddq, v, dv, dp_h, dp_r, [dp_P]])

    return rhs


def simulate(p: Params, sc, dt: float = 5e-5, log_dt: float = 1e-3) -> dict:
    rhs = make_rhs(p, sc)
    y = initial_state(p, sc)
    n = int(round((sc.t_end - sc.t_start) / dt))
    every = max(1, int(round(log_dt / dt)))
    rows, t_log = [], []
    t0 = time.perf_counter()
    for k in range(n + 1):
        t = sc.t_start + k * dt
        if k % every == 0:
            info: dict = {}
            rhs(t, y, info)
            t_log.append(t)
            rows.append(np.concatenate([
                y[10:14], y[6:10], y[14:18], y[18:22], info["Q_in"], info["Q_out"], info["F_ext"], info["u"],
                [y[22], info["Q_byp"], info["Q_p"], info["ls"], y[0], y[1], y[2]],
            ]))
        if k == n:
            break
        k1 = rhs(t, y)
        k2 = rhs(t + dt / 2, y + dt / 2 * k1)
        k3 = rhs(t + dt / 2, y + dt / 2 * k2)
        k4 = rhs(t + dt, y + dt * k3)
        y = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    names = [f"{q}_{leg}" for q in ("v", "s", "p_h", "p_r", "Q_in", "Q_out", "F_ext", "u") for leg in LEGS]
    names += ["p_P", "Q_byp", "Q_pump", "p_LS", "z", "roll", "pitch"]
    return {"time": np.array(t_log), "names": names, "data": np.array(rows),
            "wall_s": time.perf_counter() - t0, "dt": dt}


def write_csv(res: dict, path: Path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time", *res["names"]])
        for t, row in zip(res["time"], res["data"]):
            w.writerow([f"{t:.6g}", *[f"{v:.9g}" for v in row]])
