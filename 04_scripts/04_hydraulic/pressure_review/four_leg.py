"""Four-leg comparison: plant law (L2bRodSide + SpeedReference) vs two-chamber numpy vs two-chamber Hopsan.

Current REXOME35 dimensions, top auger, 3-DOF rigid body (circuit comparison model, hydraulic_coupling.md 3.4,
not for absolute waveform comparison with Chrono). All three use the same body, series stiffness k_st and
the same parallel dashpot c(u - v) as the plant law, so only the hydraulics differ.
usage: four_leg.py [names...]
"""
from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from common import P_ATM, SCRATCH, Hmf, dump, lag_series, pin_two_cores
from build_hopsan_spec import X_VMAX, build_spec, log_vars, scenario_overrides
from hopsan_run import run_hopsan
from model import spool_drop
from params import LEGS, Params, load_params, static_loads
from scenarios import Scenario

from outrigger_sim.actuation import SpeedReference
from outrigger_sim.hydraulics.flow_share import FlowCircuit, FlowShareAssumptions, PumpFlowLimiter
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide

TS = 1.0e-5
TAU_V = 0.1
OVERLAP = 0.02  # spool closes below this fraction of v_max (hydraulics 11.4, ASSUMPTION)
C_LOCK = np.array([34403.5, 34403.5, 30348.5, 30348.5])  # L2b rev33 values in the l2b_actuator docstring
C_MOVE = np.array([100206.0, 100206.0, 86949.0, 86949.0])
GRID_DT = 1.0e-3
FLOOR_PA = -0.9e5  # 0.1 bar abs, as the plant law
AIR4 = np.array([4000.0 - 1047.2, 4000.0 - 1047.2, 3333.2 - 717.5, 3333.2 - 717.5])


@dataclass
class Case:
    name: str
    t_end: float
    t_event: float
    eta: float
    commands: list  # (t_on, [u FL, FR, RL, RR] as fraction of v_max)
    coupled: bool = True
    p_r0: np.ndarray = field(default_factory=lambda: np.full(4, 2.0e5))
    loads: np.ndarray | None = None
    drop: tuple | None = None  # (leg index, depth m, t0, duration)
    contact: tuple | None = None  # (leg index, s offset above s0 at t_on, stiff)
    unilateral: bool = False
    damped: bool = True
    tao_comp: float = 1.0e-4
    v_gallery: float = 5.0e-4
    run_law: bool = True
    run_numpy: bool = True
    body_fixed: bool = False
    note: str = ""


def cases(p: Params) -> list[Case]:
    all_up = [1.0, 1.0, 1.0, 1.0]
    zero = [0.0, 0.0, 0.0, 0.0]
    r0 = np.array([34.818e5, 2e5, 2e5, 2e5])
    f_air = p.m_rod * 9.80665
    return [
        Case("A_stop_all_eta95", 4.0, 2.0, 0.95, [(0.0, all_up), (2.0, zero)], note="four legs v_max, all stop (locks), flat"),
        Case("A2_stop_all_eta85", 4.0, 2.0, 0.85, [(0.0, all_up), (2.0, zero)], note="saturated pump, all stop: S8 'just after stop' class without crawler"),
        Case("B_twist", 6.0, 1.5, 0.95, [(1.5, [0.0, 0.25, 0.25, 0.25]), (3.5, zero)], unilateral=True, note="FL locked, others 0.25 v_max 2 s, stop: twist transfer"),
        Case("C1_release_air", 1.0, 0.2, 0.95, [(0.2, [0.25, 0.0, 0.0, 0.0])], coupled=False, p_r0=np.array([124.4e5, 2e5, 2e5, 2e5]), run_law=False,
             loads=np.array([-f_air[0], 118e3, 72e3, 72e3]), note="FL in the air, rod 124 bar g trapped (ML00_ep5 class), opens to extend 0.25 v_max; law = closed form"),
        Case("C2_release_ground", 3.0, 1.5, 0.95, [(1.5, [0.25, 0.0, 0.0, 0.0]), (2.0, zero)], p_r0=r0, note="FL grounded, locked after retract 34.8 bar g, extend 0.25 v_max 0.5 s"),
        Case("C3_release_ground_r2", 3.0, 1.5, 0.95, [(1.5, [0.25, 0.0, 0.0, 0.0]), (2.0, zero)], note="control case: same move with rod 2 bar g at the start"),
        Case("D_drop_RR30", 4.0, 1.5, 0.95, [], drop=(3, 0.030, 1.5, 0.05), unilateral=True, note="all locked, ground under RR falls 30 mm in 50 ms"),
        Case("E_touch_eta85", 1.9, 1.0, 0.85, [(0.0, all_up)], coupled=False, loads=AIR4.copy(), contact=(0, 1.0, None), damped=False,
             run_law=False, note="legs in the air with F_s, FL touches at t = 1 s, others keep rising, body fixed"),
        Case("E_touch_tao20ms", 1.9, 1.0, 0.85, [(0.0, all_up)], coupled=False, loads=AIR4.copy(), contact=(0, 1.0, None), damped=False, tao_comp=2.0e-2,
             run_law=False, run_numpy=False, note="same, compensator lag 20 ms (Hopsan only)"),
        Case("E_touch_Vg2L", 1.9, 1.0, 0.85, [(0.0, all_up)], coupled=False, loads=AIR4.copy(), contact=(0, 1.0, None), damped=False, v_gallery=2.0e-3,
             run_law=False, note="same, gallery 2 L"),
    ]


def command_series(case: Case, p: Params):
    grid = np.arange(0.0, case.t_end + GRID_DT / 2, GRID_DT)
    cmd = np.zeros((len(grid), 4))
    for t_on, u in case.commands:
        cmd[grid >= t_on] = np.array(u)
    u_lag = np.column_stack([lag_series(grid, cmd[:, i], TAU_V) for i in range(4)])
    u_snap = np.where(np.abs(u_lag) < OVERLAP, 0.0, u_lag)
    return grid, cmd, u_snap


def base_loads(case: Case, p: Params) -> np.ndarray:
    return static_loads(p) if case.loads is None else case.loads


def contact_position(case: Case, p: Params) -> float:
    return float(p.s0[case.contact[0]])  # at t_contact the leg sits at s0 (see the shifted start below)


def build_hopsan(case: Case, p: Params, grid, u_snap, folder: Path):
    p_use = p.with_(V_hose=0.0, V_g=case.v_gallery)
    spec = build_spec(p_use, stop_s=case.t_end, ts=TS)
    sc = Scenario(case.name, case.note, case.eta, tuple(float(x) if x != 0 else 1.0 for x in [1, 1, 1, 1]), case.coupled)
    sc = Scenario(case.name, case.note, case.eta, (1.0, 1.0, 1.0, 1.0), case.coupled,
                  force_override=tuple((leg, float(f)) for leg, f in zip(LEGS, base_loads(case, p))))
    ov = scenario_overrides(p_use, sc)
    for key in list(ov):
        if key.startswith("Cmd"):
            del ov[key]
    h = Hmf(case.name, case.t_end, TS)
    h.comp("SignalTime", "Clock")
    drop_conns = set()
    f0 = base_loads(case, p)
    for comp in spec["components"]:
        if comp["name"].startswith("Cmd"):
            continue
        if case.drop is not None and comp["name"] == f"S0{LEGS[case.drop[0]]}":
            continue
        if case.contact is not None and comp["name"] == f"S0{LEGS[case.contact[0]]}":
            continue
        if comp["name"].startswith("Body"):
            pars = dict(comp["parameters"])
            if not case.coupled or case.contact is not None or case.body_fixed:
                pars["m"] = 1.0e9
            h.comp(comp["typename"], comp["name"], pars)
            continue
        if comp["name"].startswith("HydraulicPressureCompensatingValve") or comp["name"].startswith("Comp") and comp["typename"] == "HydraulicPressureCompensatingValve":
            pars = dict(comp["parameters"])
            pars["tao"] = case.tao_comp
            h.comp(comp["typename"], comp["name"], pars)
            continue
        h.comp(comp["typename"], comp["name"], comp["parameters"])
    for i, leg in enumerate(LEGS):
        h.lookup(folder, f"Cmd{leg}", grid, u_snap[:, i] * X_VMAX, f"Spool{leg}", "in")
        # parallel dashpot of the plant law: Load F = Ftot - c u + c v (c switches with the lock state)
        c_series = np.where(u_snap[:, i] == 0.0, C_LOCK[i], C_MOVE[i]) if case.damped else np.zeros(len(grid))
        h.lookup(folder, f"CU{leg}", grid, c_series * u_snap[:, i] * p.v_max, f"LoadSub{leg}", "in2")
        h.lookup(folder, f"CC{leg}", grid, c_series, f"CV{leg}", "in1")
        h.comp("SignalSubtract", f"LoadSub{leg}")
        h.comp("SignalMultiply", f"CV{leg}")
        h.comp("SignalAdd", f"LoadAdd{leg}")
        dmin = (-float(f0[i]) - float(p.m_rod[i]) * 9.80665) if case.unilateral else -1.0e9
        if case.contact is not None:
            dmin = 0.0
        h.comp("SignalConstant", f"DMin{leg}", {"y#Value": dmin})
        h.comp("SignalMax", f"DClip{leg}")
        drop_conns.add((f"dF{leg}#out"))
    for c in spec["connections"]:
        a, b = c["from"], c["to"]
        if a.startswith("Cmd") or b.startswith("Cmd"):
            continue
        ca, pa = a.split("#")
        cb, pb = b.split("#")
        leg = cb[-2:]
        if a in drop_conns:  # dF out now goes through the unilateral clip
            ca = f"DClip{ca[-2:]}"
        if case.drop is not None and ca == f"S0{LEGS[case.drop[0]]}":
            continue
        if ca.startswith("Ftot") and cb.startswith("Load"):
            h.connect(ca, pa, f"LoadSub{cb[-2:]}", "in1")
            continue
        h.connect(ca, pa, cb, pb)
    for i, leg in enumerate(LEGS):
        h.connect(f"dF{leg}", "out", f"DClip{leg}", "in")
        h.connect(f"DMin{leg}", "y", f"DClip{leg}", "in")
        h.connect(f"SVel{leg}", "out", f"CV{leg}", "in2")
        h.connect(f"LoadSub{leg}", "out", f"LoadAdd{leg}", "in1")
        h.connect(f"CV{leg}", "out", f"LoadAdd{leg}", "in2")
        h.connect(f"LoadAdd{leg}", "out", f"Load{leg}", "F")
    if case.drop is not None:
        i, depth, t0, dur = case.drop
        leg = LEGS[i]
        h.lookup(folder, f"S0{leg}", np.array([0.0, t0, t0 + dur, case.t_end]),
                 np.array([p.s0[i], p.s0[i], p.s0[i] + depth, p.s0[i] + depth]), f"Comprn{leg}", "insub")
    if case.contact is not None:
        i, t_touch, _ = case.contact
        leg = LEGS[i]
        s_c = float(p.s0[i])
        h.comp("SignalConstant", f"S0{leg}", {"y#Value": s_c})
    for i, leg in enumerate(LEGS):
        # gauge chamber start values, rod side from the case
        p_r = float(case.p_r0[i])
        ph = (float(f0[i]) + p.A_r[i] * p_r) / p.A_h[i]
        ov[f"Cyl{leg}#P2#Pressure"] = P_ATM + p_r
        ov[f"Cyl{leg}#P1#Pressure"] = P_ATM + float(ph)
        ov[f"C{leg}#k#Value"] = 0.0
        ov[f"K{leg}#k#Value"] = float(p.k_st[i]) if case.coupled else 0.0
    if case.contact is not None:
        i, t_touch, _ = case.contact
        ov[f"K{LEGS[i]}#k#Value"] = float(p.k_st[i])
        for j, leg in enumerate(LEGS):
            start = float(p.s0[j]) - (p.v_max * t_touch if j == i else 0.0) * 0.95  # contact about t_touch
            ov[f"Cyl{leg}#P3#Position"] = -start
            ov[f"Load{leg}#P1#Position"] = start
    model = h.write(folder / f"{case.name}.hmf", n_log=int(case.t_end / 2e-4) + 1)
    return model, ov


def run_case_hopsan(case: Case, p: Params, grid, u_snap):
    folder = SCRATCH / "four" / case.name
    model, ov = build_hopsan(case, p, grid, u_snap, folder)
    df, _u, info = run_hopsan(model, folder, sim=(0.0, TS, case.t_end), params=ov, log_only=log_vars(),
                              num_log_samples=int(case.t_end / 2e-4) + 1, timeout=280.0)
    t = df.index.to_numpy()
    f0 = base_loads(case, p)
    out = {"t": t, "wall_s": info["wall_s"], "csv": info["csv"]}
    atm = (p.A_h - p.A_r) * P_ATM
    F = np.column_stack([df[f"Ftot{leg}#out#Value"].to_numpy() - atm[i] for i, leg in enumerate(LEGS)])
    out["F"] = F
    out["v"] = np.column_stack([df[f"Mass{leg}#P2#Velocity"].to_numpy() for leg in LEGS])
    out["pos"] = np.column_stack([df[f"Mass{leg}#P2#Position"].to_numpy() for leg in LEGS])
    # read port: PA and PB multiport pressures of the spool = chamber pressures here (no POC, no hose)
    out["p_h"] = np.column_stack([df[f"Spool{leg}#PA#Pressure"].to_numpy() - P_ATM for leg in LEGS])
    out["p_r"] = np.column_stack([df[f"Spool{leg}#PB#Pressure"].to_numpy() - P_ATM for leg in LEGS])
    out["p_P"] = df["Pump#P2#Pressure"].to_numpy() - P_ATM
    return out


def run_case_numpy(case: Case, p: Params, grid, u_snap, with_hose: bool, dt: float = 5.0e-5):
    p_use = p.with_(V_g=case.v_gallery, V_hose=(p.V_hose if with_hose else 0.0))
    M = np.array([p.mass, p.I_roll, p.I_pitch])
    K_ext = p_use.K_spool
    f0 = base_loads(case, p)
    dmin = -f0 - p.m_rod * 9.80665 if case.unilateral else np.full(4, -1e12)
    if case.contact is not None:
        dmin = np.zeros(4)
    ks = p.k_st if case.coupled or case.contact is not None else np.zeros(4)
    body_on = case.coupled and case.contact is None and not case.body_fixed
    s_start = p.s0.copy()
    s_ground = p.s0.copy()
    if case.contact is not None:
        i, t_touch, _ = case.contact
        s_start[i] = p.s0[i] - p.v_max * t_touch * 0.95
        ks = np.zeros(4)
        ks[i] = p.k_st[i]

    def u_at(t):
        j = min(int(t / GRID_DT), len(grid) - 2)
        a = (t - grid[j]) / GRID_DT
        return u_snap[j] + (u_snap[j + 1] - u_snap[j]) * a

    def drop_at(t):
        out = np.zeros(4)
        if case.drop is not None:
            i, depth, t0, dur = case.drop
            out[i] = depth * min(max((t - t0) / dur, 0.0), 1.0)
        return out

    q = np.zeros(3)
    dq = np.zeros(3)
    y = np.zeros(6 + 4 * 4 + 1)
    p_r0 = case.p_r0.copy()
    y[6:10] = s_start
    y[14:18] = (f0 + p.A_r * p_r0) / p.A_h
    y[18:22] = p_r0
    y[22] = max(p.p_T, y[14:18].max()) + p.dp_unl
    Q_p = p.Q_pump(case.eta)

    def rhs(t, st):
        q, dq = st[:3], st[3:6]
        s, v, pP = st[6:10], st[10:14], st[22]
        ph, pr = np.maximum(st[14:18], FLOOR_PA), np.maximum(st[18:22], FLOOR_PA)  # oil mass kept: the raw state stays below the floor
        w = q[0] + p.yp * q[1] - p.xp * q[2]
        dw = dq[0] + p.yp * dq[1] - p.xp * dq[2]
        dF = np.maximum(ks * (s - s_ground - w - drop_at(t)), dmin)
        F_ext = f0 + dF
        u = u_at(t)
        ext = u > 0
        c = np.where(u == 0.0, C_LOCK, C_MOVE) if case.damped else np.zeros(4)
        active = ext
        K = K_ext * np.abs(u)
        ls = min(max(p.p_T, float(ph[active].max()) if active.any() else p.p_T), p.p_relief)
        D = pP - ph
        ydrop = spool_drop(p_use, K, D)
        Q_in = K * np.sqrt(ydrop)
        dp_rt = pr - p.p_T
        Q_bt = K_ext * np.abs(u) * p_use.bt_ratio * dp_rt / np.sqrt(np.abs(dp_rt) + 1e2)
        hose = np.where(active, p_use.V_hose, 0.0)
        V_h = p.A_h * p.L0h + hose + p.A_h * s
        V_r = p.A_r * p.L0r + hose + p.A_r * (p.stroke - s)
        dp_h = p.beta / V_h * (np.where(ext, Q_in, 0.0) - p.A_h * v)
        dp_r = p.beta / V_r * (p.A_r * v - np.where(ext, Q_bt, 0.0))
        F_cyl = p.A_h * ph - p.A_r * pr + c * (u * p.v_max - v)
        dv = (F_cyl - F_ext) / p.m_rod
        ddq = np.array([dF.sum(), (p.yp * dF).sum(), (-p.xp * dF).sum()]) / M if body_on else np.zeros(3)
        dpP_T = max(pP - p.p_T, 0.0)
        b_u = p.Cs_unl + p.Cf_unl * dpP_T
        x_u = min(max((pP - p.dp_unl - ls) / b_u, 0.0), p.X_unl)
        Q_byp = x_u * math.sqrt(dpP_T)
        dpP = p.beta / p_use.V_g * (Q_p - Q_in.sum() - Q_byp)
        return np.concatenate([dq, ddq, v, dv, dp_h, dp_r, [dpP]]), F_ext

    n = int(round(case.t_end / dt))
    every = max(1, int(round(2e-4 / dt)))
    rows = []
    t0 = time.perf_counter()
    for k in range(n + 1):
        t = k * dt
        k1, F_ext = rhs(t, y)
        if k % every == 0:
            rows.append(np.concatenate([[t], F_ext, y[10:14], np.maximum(y[14:18], FLOOR_PA), np.maximum(y[18:22], FLOOR_PA), y[6:10], [y[22]]]))
        k2, _ = rhs(t + dt / 2, y + dt / 2 * k1)
        k3, _ = rhs(t + dt / 2, y + dt / 2 * k2)
        k4, _ = rhs(t + dt, y + dt * k3)
        y = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    a = np.array(rows)
    return {"t": a[:, 0], "F": a[:, 1:5], "v": a[:, 5:9], "p_h": a[:, 9:13], "p_r": a[:, 13:17], "pos": a[:, 17:21], "p_P": a[:, 21],
            "wall_s": time.perf_counter() - t0}


class _Limiter:
    def __init__(self, limiter):
        self.limiter = limiter

    def limit(self, t_s, dt_s, request_m_s, force_N):
        return self.limiter.delivered_speeds_m_s(request_m_s, force_N)


def run_case_law(case: Case, p: Params, grid, cmd, with_limit: bool, dt: float = 1.0e-4):
    """Plant law with a massless rod (L2bForceActuator hook order, no pychrono)."""
    f0 = base_loads(case, p)
    law = L2bRodSide(head_area_m2=p.A_h, annulus_area_m2=p.A_r, k_out_N_m=p.k_st, bulk_modulus_Pa=p.beta, head_dead_length_m=p.L0h,
                     rod_dead_length_m=[p.L0r] * 4, stroke_m=p.stroke, p_r0_after_extend_Pa=case.p_r0, p_r0_after_retract_Pa=case.p_r0,
                     p_floor_abs_Pa=1.0e4, release_tau_s=0.05, lock_eps_m_s=1.0e-6, mechanics="one_sided_parallel", armed=True)
    k2 = np.array([law.k2_N_m(i, float(p.s0[i])) for i in range(4)])
    s_ref0 = p.s0 + f0 / k2
    ref = SpeedReference(s_ref0, [[0.0, 0.9]] * 4, max_speed_m_s=p.v_max, ramp_s=0.1)
    ref.configure_valve(tau_s=TAU_V)
    if with_limit:
        circuit = FlowCircuit(head_area_m2=p.A_h, annulus_area_m2=p.A_r, pump_flow_m3_s=p.Q_pump_th, max_speed_m_s=p.v_max, relief_pressure_Pa=p.p_relief)
        ref.set_flow_limit(_Limiter(PumpFlowLimiter(circuit, FlowShareAssumptions(eta_v=case.eta, is_enabled=True))))
    q = np.zeros(3)
    dq = np.zeros(3)
    M = np.array([p.mass, p.I_roll, p.I_pitch])
    force = f0.copy()
    u_act = np.zeros(4)
    rows = []
    n = int(round(case.t_end / dt))
    for k in range(n + 1):
        t = k * dt
        j = min(int(t / GRID_DT), len(grid) - 1)
        ref.set_command(cmd[j] * p.v_max)
        s_ref_now = ref.s_ref_m
        ref.advance(dt, cylinder_force_N=force, t_s=t)
        u = ref.u_applied_m_s
        w = q[0] + p.yp * q[1] - p.xp * q[2] if case.coupled else np.zeros(4)
        dw = dq[0] + p.yp * dq[1] - p.xp * dq[2] if case.coupled else np.zeros(4)
        drop = np.zeros(4)
        if case.drop is not None:
            i, depth, t0, dur = case.drop
            drop[i] = depth * min(max((t - t0) / dur, 0.0), 1.0)
            ddrop = np.zeros(4)
            if t0 <= t < t0 + dur:
                ddrop[i] = depth / dur
        else:
            ddrop = np.zeros(4)
        s_link = p.s0 + w + drop
        ds = dw + ddrop
        spring = law.spring_force_N(t, dt, u_act, s_ref_now, s_ref_now - s_link, force)
        c = np.where(np.abs(u) <= 1e-6, C_LOCK, C_MOVE)
        f_raw = spring + c * (u - ds)
        if case.unilateral:
            f_raw = np.maximum(f_raw, -p.m_rod * 9.80665)
        force = f_raw
        dF = force - f0
        p_r = law.rod_pressure_Pa
        rows.append(np.concatenate([[t], force, u, (force + p_r * p.A_r) / p.A_h, p_r, s_ref_now]))
        ddq = np.array([dF.sum(), (p.yp * dF).sum(), (-p.xp * dF).sum()]) / M
        if case.coupled:
            dq = dq + ddq * dt
            q = q + dq * dt
        u_act = u
    a = np.array(rows)
    return {"t": a[:, 0], "F": a[:, 1:5], "v": a[:, 5:9], "p_h": a[:, 9:13], "p_r": a[:, 13:17], "pos": a[:, 17:21]}


def window_stats(r, t_event, t_end):
    t = r["t"]
    pre = (t >= t_event - 0.05) & (t < t_event) if t_event > 0.1 else t < 0.01
    post = t >= t_event
    F_pre = r["F"][pre].mean(axis=0)
    dF = r["F"][post] - F_pre
    return {
        "F_pre_kN": (F_pre / 1e3).tolist(),
        "dF_max_kN": (dF.max(axis=0) / 1e3).tolist(), "dF_min_kN": (dF.min(axis=0) / 1e3).tolist(),
        "F_end_kN": (r["F"][-20:].mean(axis=0) / 1e3).tolist(),
        "p_h_max_bar": (r["p_h"][post].max(axis=0) / 1e5).tolist(), "p_h_min_bar": (r["p_h"][post].min(axis=0) / 1e5).tolist(),
        "p_r_max_bar": (r["p_r"][post].max(axis=0) / 1e5).tolist(), "p_r_min_bar": (r["p_r"][post].min(axis=0) / 1e5).tolist(),
        "p_h_end_bar": (r["p_h"][-20:].mean(axis=0) / 1e5).tolist(), "p_r_end_bar": (r["p_r"][-20:].mean(axis=0) / 1e5).tolist(),
    }


def compare(a, b, t_event, t_end, mode="delta"):
    """Max |a - b| per leg of force change, 10 Hz sampled pressures."""
    t = np.arange(t_event, t_end, 2e-4)
    pre = (a["t"] >= t_event - 0.05) & (a["t"] < t_event)
    pre_b = (b["t"] >= t_event - 0.05) & (b["t"] < t_event)
    res = {}
    fa = np.column_stack([np.interp(t, a["t"], a["F"][:, i]) - (a["F"][pre, i].mean() if pre.any() else a["F"][0, i]) for i in range(4)])
    fb = np.column_stack([np.interp(t, b["t"], b["F"][:, i]) - (b["F"][pre_b, i].mean() if pre_b.any() else b["F"][0, i]) for i in range(4)])
    res["dF_abs_max_kN"] = (np.abs(fa - fb).max(axis=0) / 1e3).tolist()
    res["dF_rms_kN"] = (np.sqrt(((fa - fb) ** 2).mean(axis=0)) / 1e3).tolist()
    t10 = np.arange(t_event + 0.1, t_end, 0.1)
    for key in ("p_h", "p_r"):
        pa = np.column_stack([np.interp(t10, a["t"], a[key][:, i]) for i in range(4)])
        pb = np.column_stack([np.interp(t10, b["t"], b[key][:, i]) for i in range(4)])
        res[f"{key}_10Hz_abs_max_bar"] = (np.abs(pa - pb).max(axis=0) / 1e5).tolist()
    net = {}
    for tag, src in (("a", a), ("b", b)):
        net[tag] = np.column_stack([p_area * np.interp(t10, src["t"], src["p_h"][:, i]) - r_area * np.interp(t10, src["t"], src["p_r"][:, i])
                                    for i, (p_area, r_area) in enumerate(zip(AH, AR))])
    res["F_net_10Hz_abs_max_kN"] = (np.abs(net["a"] - net["b"]).max(axis=0) / 1e3).tolist()
    return res


AH = np.zeros(4)
AR = np.zeros(4)


def main() -> None:
    pin_two_cores()
    p = load_params()
    AH[:] = p.A_h
    AR[:] = p.A_r
    want = set(sys.argv[1:])
    out = {"meta": {
        "dimensions": "current REXOME35 (02_params/rexome33.yaml through coupled/params.py), top auger, flat unless noted",
        "pressure": "bar gauge; Hopsan absolute minus 1e5 Pa", "ts_hopsan_s": TS, "dt_numpy_s": 5e-5, "dt_law_s": 1e-4,
        "fluid": {"beta_Pa": p.beta, "rho": p.rho, "note": "VG46 50 C, beta 1.0 GPa ASSUMPTION (YAML)"},
        "assumptions": {"tau_v_s": TAU_V, "overlap_fraction": OVERLAP, "dp_comp_bar": p.dp_comp / 1e5, "dp_ls_bar": p.dp_unl / 1e5,
                        "p_T_bar": p.p_T / 1e5, "V_hose_m3": p.V_hose, "comp_k_cs": p.comp_k_cs, "comp_k_cf": p.comp_k_cf,
                        "c_lock": C_LOCK.tolist(), "c_move": C_MOVE.tolist(),
                        "hopsan_hose": "0: the circuit has no check valve, a hose would stay in the locked chamber"},
        "body": "3-DOF small angle (hydraulic_coupling.md 3.4), not comparable with Chrono waveforms",
        "law_rod": "massless rod: rod-oil ringing (about 100 Hz) absent in the law column",
    }, "cases": {}}
    for case in cases(p):
        if want and case.name not in want:
            continue
        grid, cmd, u_snap = command_series(case, p)
        entry = {"note": case.note, "t_event": case.t_event, "eta_v": case.eta}
        t0 = time.perf_counter()
        hop = run_case_hopsan(case, p, grid, u_snap)
        entry["hopsan"] = window_stats(hop, case.t_event, case.t_end)
        entry["hopsan_wall_s"] = hop["wall_s"]
        s_int = np.column_stack([hop["pos"][0, i] + np.concatenate([[0.0], np.cumsum(0.5 * (hop["v"][1:, i] + hop["v"][:-1, i]) * np.diff(hop["t"]))]) for i in range(4)])
        entry["hopsan_pos_minus_int_v_mm_end"] = ((hop["pos"][-1] - s_int[-1]) * 1e3).tolist()
        nump = run_case_numpy(case, p, grid, u_snap, with_hose=False) if case.run_numpy else None
        if nump is not None:
            entry["numpy_no_hose"] = window_stats(nump, case.t_event, case.t_end)
            entry["numpy_vs_hopsan"] = compare(nump, hop, case.t_event, case.t_end)
            entry["numpy_wall_s"] = nump["wall_s"]
            if case.coupled and case.name in ("A_stop_all_eta95", "C2_release_ground", "D_drop_RR30"):
                nh = run_case_numpy(case, p, grid, u_snap, with_hose=True)
                entry["numpy_hose"] = window_stats(nh, case.t_event, case.t_end)
                entry["hose_vs_no_hose"] = compare(nh, nump, case.t_event, case.t_end)
        if case.run_law:
            law = run_case_law(case, p, grid, cmd, with_limit=case.eta < 0.9)
            entry["law"] = window_stats(law, case.t_event, case.t_end)
            entry["law_vs_hopsan"] = compare(law, hop, case.t_event, case.t_end)
            if nump is not None:
                entry["law_vs_numpy"] = compare(law, nump, case.t_event, case.t_end)
            np.savez_compressed(SCRATCH / "four" / case.name / "law.npz", **{k: v for k, v in law.items()})
        if case.contact is not None:
            i = case.contact[0]
            t = hop["t"]
            win = (t > 0.5) & (t < case.t_end)
            entry["speeds_hopsan_mm_s"] = {leg: {"min": float(hop["v"][win, j].min() * 1e3), "max": float(hop["v"][win, j].max() * 1e3), "end": float(hop["v"][-50:, j].mean() * 1e3)} for j, leg in enumerate(LEGS)}
            entry["p_P_bar"] = {"before": float(hop["p_P"][(t > 0.5) & (t < 0.7)].mean() / 1e5), "max": float(hop["p_P"][win].max() / 1e5), "end": float(hop["p_P"][-50:].mean() / 1e5)}
            entry["F_contact_kN_end"] = float(hop["F"][-50:, i].mean() / 1e3)
            np.savez_compressed(SCRATCH / "four" / case.name / "hop.npz", **{k: hop[k] for k in ("t", "F", "v", "p_h", "p_r", "p_P", "pos")})
        np.savez_compressed(SCRATCH / "four" / case.name / "hop_all.npz", **{k: hop[k] for k in ("t", "F", "v", "p_h", "p_r", "p_P", "pos")})
        if nump is not None:
            np.savez_compressed(SCRATCH / "four" / case.name / "num_all.npz", **{k: nump[k] for k in ("t", "F", "v", "p_h", "p_r", "p_P", "pos")})
        out["cases"][case.name] = entry
        dump("four_leg_partial.json", out)
        print(case.name, "wall", round(time.perf_counter() - t0, 1), "hopsan", hop["wall_s"])
        print("  hopsan dF max", np.round(entry["hopsan"]["dF_max_kN"], 2), "min", np.round(entry["hopsan"]["dF_min_kN"], 2), "ph max", np.round(entry["hopsan"]["p_h_max_bar"], 1), "pr", np.round(entry["hopsan"]["p_r_min_bar"], 1), np.round(entry["hopsan"]["p_r_max_bar"], 1))
        if "numpy_no_hose" in entry:
            print("  numpy  dF max", np.round(entry["numpy_no_hose"]["dF_max_kN"], 2), "min", np.round(entry["numpy_no_hose"]["dF_min_kN"], 2), "ph max", np.round(entry["numpy_no_hose"]["p_h_max_bar"], 1), "pr", np.round(entry["numpy_no_hose"]["p_r_min_bar"], 1), np.round(entry["numpy_no_hose"]["p_r_max_bar"], 1))
        if "law" in entry:
            print("  law    dF max", np.round(entry["law"]["dF_max_kN"], 2), "min", np.round(entry["law"]["dF_min_kN"], 2), "ph max", np.round(entry["law"]["p_h_max_bar"], 1), "pr", np.round(entry["law"]["p_r_min_bar"], 1), np.round(entry["law"]["p_r_max_bar"], 1))
            print("  law-hop", {k: np.round(v, 2).tolist() for k, v in entry["law_vs_hopsan"].items()})
        if "numpy_vs_hopsan" in entry:
            print("  np-hop ", {k: np.round(v, 2).tolist() for k, v in entry["numpy_vs_hopsan"].items()})
        print("  pos-intv mm", np.round(entry["hopsan_pos_minus_int_v_mm_end"], 3))
        if case.contact is not None:
            print("  speeds", entry["speeds_hopsan_mm_s"], entry["p_P_bar"], entry["F_contact_kN_end"])
    dump("four_leg.json" if not want else "four_leg_partial.json", out)


if __name__ == "__main__":
    main()
