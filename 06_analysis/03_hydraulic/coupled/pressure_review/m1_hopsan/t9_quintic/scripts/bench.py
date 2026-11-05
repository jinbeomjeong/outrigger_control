"""Single-leg pilot-operated check bench for the M1 extrapolation check (Hopsan, current REXOME35).

The leg: flow source + meter-out land + neutral vent, two lines, two checks, cylinder, Coulomb rod, k_st, load mass,
prescribed load. Checks are either the stock Hopsan component or a "logic" pair (orifice + comparator) with the same
opening law but without the stock unconditional anti-cavitation branch, so a void can stay in the rod chamber.

Pressures: Hopsan absolute; every value leaving this module is bar gauge (p_atm 1e5 Pa). Hopsan floor = 0 Pa abs.
"""
from __future__ import annotations

import ctypes
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(HERE.parent / "hyd_review"))
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "m1_check"))

import numpy as np
from common import P_ATM, Hmf, lag_series  # also sets the project and tool paths
from hopsan_run import run_hopsan
from m1_plant import M1Config, dead_strokes_m
from params import load_params, static_loads

AFFINITY_MASK = 0x00FF0000
TS = 1.0e-5
TAU_V = 0.1  # ASSUMPTION
PSI = 3.5  # ASSUMPTION
P_CRACK = 3.0e5  # ASSUMPTION
POC_KS = 7.0e-7  # ASSUMPTION
V_LINE = 2.85e-4  # ASSUMPTION
BETA_HOSE = 0.5e9  # ASSUMPTION
RHO, CQ = 860.0, 0.67  # ASSUMPTION VG46 50 C
NEUTRAL_FRACTION = 0.05  # ASSUMPTION A,B->T opening relative to the full land
FRONT_C_LOCK, REAR_C_LOCK = 34403.5, 30348.5
REAR_FS_SCALE = 0.833
LEG_NAMES = ("FL", "FR", "RL", "RR")
WORKERS = 4


def pin() -> None:
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), AFFINITY_MASK)


@dataclass(frozen=True)
class Bench:
    """One single-leg run. Pressures in Pa gauge."""

    name: str
    leg: int
    p_h_target: float | None  # head pressure after the load change; None = static
    F_s: float = 0.0
    start: str = "ramp"  # "ramp" = load ramp from p_r0, "ic_floor" = rod chamber starts at the floor, "static"
    neutral: str = "vent"  # "vent" or "block"
    p_T: float = 2.0e5
    p_r0: float = 2.0e5
    crack: float = P_CRACK
    crack_b: float | None = None  # rod side check, None = same
    pilot_ref_b: bool = False  # True: the rod check pilot is referenced to the tank line (back pressure gives no opening)
    stock_check: bool = False
    deadband: bool = False  # no pump flow below the vent closure opening (spool overlap)
    vent_close: float = 0.02  # ASSUMPTION spool opening fraction where the centre vent is shut
    neutral_fraction: float = NEUTRAL_FRACTION
    cmd_t: np.ndarray | None = field(default=None, compare=False)  # command times relative to t_cmd [s]
    cmd_u: np.ndarray | None = field(default=None, compare=False)  # ZOH leg command [m/s]
    t_ramp: float = 1.0
    t_settle: float = 0.5
    t_hold: float = 0.2
    t_after: float = 0.5
    F_load: float | None = None  # gauge load for start="static"; None = the static leg load
    line_a0_g: float | None = None  # block neutral: trapped line A gauge pressure; None = p_h + crack


def geometry(p, i: int):
    return float(p.A_h[i]), float(p.A_r[i]), float(p.s0[i]), float(static_loads(p)[i])


def build(b: Bench, p, folder: Path):
    i = b.leg
    A_h, A_r, s0, F_static = geometry(p, i)
    F_s = b.F_s
    t_cmd = b.t_settle + (b.t_ramp if b.start == "ramp" else 0.0) + b.t_hold
    t_end = t_cmd + float(b.cmd_t[-1]) + b.t_after
    grid = np.arange(0.0, t_end + 1e-9, 1.0e-3)
    idx = np.searchsorted(b.cmd_t, grid - t_cmd, side="right") - 1
    cmd = np.where(idx >= 0, b.cmd_u[np.clip(idx, 0, len(b.cmd_u) - 1)], 0.0)
    cmd[grid < t_cmd] = 0.0
    u = lag_series(grid, cmd, TAU_V)
    frac = np.abs(u) / p.v_max

    # gauge chamber state and the load (Hopsan cylinder force has no atmosphere term)
    atm = (A_h - A_r) * P_ATM
    p_line_t = P_ATM + b.p_T
    if b.start == "ic_floor":
        p_r_abs = 0.0
        p_h_g = b.p_h_target
        F_gauge = A_h * p_h_g - A_r * (-P_ATM)
        F_start = F_gauge + atm
        F_end = F_start
        p_h_abs = P_ATM + p_h_g
    else:
        p_r_abs = P_ATM + b.p_r0
        F_start = (F_static if b.F_load is None else b.F_load) + atm
        p_h_abs = (F_start + A_r * p_r_abs) / A_h
        if b.start == "ramp":
            # target head pressure reached with the friction taken up against the load rise
            F_end = F_start + A_h * (b.p_h_target - (p_h_abs - P_ATM)) + F_s
        else:
            F_end = F_start
    M = F_static / 9.80665
    load = np.interp(grid, [0.0, b.t_settle, b.t_settle + b.t_ramp, t_end], [F_start, F_start, F_end, F_end])

    k_land = A_h * p.v_max / np.sqrt(p.dp_comp)
    a_full = k_land / (CQ * np.sqrt(2.0 / RHO))
    a_neutral = b.neutral_fraction * a_full if b.neutral == "vent" else 0.0
    h = Hmf(b.name, float(t_end), TS)
    h.comp("SignalTime", "Clock")
    h.comp("HydraulicTankC", "TankA", {"p": p_line_t})
    h.comp("HydraulicTankC", "TankB", {"p": p_line_t})
    # block neutral: line A trapped near the head pressure of the last extension, line B at tank
    line_a0 = p_line_t if b.neutral == "vent" else (p_h_abs + b.crack if b.line_a0_g is None else P_ATM + b.line_a0_g)
    h.comp("HydraulicVolumeMultiPort", "LineA", {"V#Value": V_LINE, "Beta_e#Value": BETA_HOSE, "P1#Pressure": line_a0})
    h.comp("HydraulicVolumeMultiPort", "LineB", {"V#Value": V_LINE, "Beta_e#Value": BETA_HOSE, "P1#Pressure": p_line_t})
    for name, line in (("QA", "LineA"), ("QB", "LineB")):
        h.comp("HydraulicFlowSourceQ", name, {"q#Value": 0.0})
        h.connect(name, "P1", line, "P1")
    for name, line, tank in (("OA", "LineA", "TankA"), ("OB", "LineB", "TankB")):
        h.comp("HydraulicTurbulentOrifice", name, {"A#Value": 0.0, "C_q#Value": CQ, "rho#Value": RHO})
        h.connect(name, "P1", line, "P1")
        h.connect(name, "P2", tank, "P1")
    crack_b = b.crack if b.crack_b is None else b.crack_b
    shift_b = PSI * b.p_T if b.pilot_ref_b else 0.0
    a_check = POC_KS / (CQ * np.sqrt(2.0 / RHO))
    for name, line, port, pilot, crack, shift in (("POCA", "LineA", "P1", "LineB", b.crack, 0.0),
                                                  ("POCB", "LineB", "P2", "LineA", crack_b, shift_b)):
        pf = crack + shift + P_ATM * PSI  # all absolute; memory hopsan-pressure-valves-absolute
        if b.stock_check:
            h.comp("HydraulicPilotControlledCheckValve", name, {"phi#Value": PSI, "p_f#Value": pf, "K_s": POC_KS})
            h.connect(name, "P1", line, "P1")
            h.connect(name, "P2", "Cyl", port)
            h.connect(name, "P_PILOT", pilot, "P1")
            continue
        h.comp("HydraulicTurbulentOrifice", name, {"A#Value": 0.0, "C_q#Value": CQ, "rho#Value": RHO})
        h.connect(name, "P1", line, "P1")
        h.connect(name, "P2", "Cyl", port)
        for sensor in ("SL", "SP", "SC"):
            h.comp("HydraulicPressureSensor", f"{sensor}{name}")
        h.comp("SignalGain", f"GP{name}", {"k#Value": PSI})
        h.comp("SignalSub", f"D{name}")
        h.comp("SignalConstant", f"Pf{name}", {"y#Value": pf})
        h.comp("SignalGreaterThan", f"GT{name}", {"x_limit#Value": 0.0})
        h.comp("SignalGain", f"AG{name}", {"k#Value": a_check})
        h.connect(f"SL{name}", "P1", name, "P1")
        h.connect(f"SC{name}", "P1", name, "P2")
        other = "OB" if pilot == "LineB" else "OA"
        h.connect(f"SP{name}", "P1", other, "P1")
        h.connect(f"SP{name}", "out", f"GP{name}", "in")
        h.connect(f"SL{name}", "out", f"D{name}", "insum")
        h.connect(f"GP{name}", "out", f"D{name}", "insum")
        h.connect(f"SC{name}", "out", f"D{name}", "insub")
        h.connect(f"Pf{name}", "y", f"D{name}", "insub")
        h.connect(f"D{name}", "out", f"GT{name}", "in")
        h.connect(f"GT{name}", "out", f"AG{name}", "in")
        h.connect(f"AG{name}", "out", name, "A")
    c_lock = FRONT_C_LOCK if i < 2 else REAR_C_LOCK
    h.comp("HydraulicCylinderC", "Cyl", {
        "P1#Pressure": p_h_abs, "P1#WaveVariable": p_h_abs, "P2#Pressure": p_r_abs, "P2#WaveVariable": p_r_abs,
        "P3#Position": -s0, "P3#Force": F_start, "P3#WaveVariable": F_start,
        "A_1#Value": A_h, "A_2#Value": A_r, "s_l#Value": p.stroke,
        "V_1#Value": A_h * p.L0h, "V_2#Value": A_r * p.L0r, "B_p#Value": c_lock, "Beta_e#Value": p.beta,
        "c_leak#Value": 0.0, "use_sl": False})
    if F_s > 0.0:
        h.comp("MechanicTranslationalMassWithCoulombFriction", "Rod", {
            "m": float(p.m_rod[i]), "b#Value": 0.0, "f_s#Value": F_s, "f_k#Value": F_s,
            "x_min#Value": -1e3, "x_max#Value": 1e3})
    else:
        h.comp("MechanicTranslationalMass", "Rod", {"m": float(p.m_rod[i]), "B#Value": 0.0, "k#Value": 0.0,
                                                     "x_min#Value": -1e3, "x_max#Value": 1e3})
    k_g = float(p.k_st[i])
    h.comp("MechanicTranslationalSpring", "Kg", {"k#Value": k_g, "P1#Force": F_start, "P2#Force": F_start,
                                                  "P1#Position": s0, "P2#Position": 0.0,
                                                  "P1#WaveVariable": F_start, "P2#WaveVariable": F_start})
    h.comp("MechanicTranslationalMass", "Sup", {"m": M, "B#Value": 0.0, "k#Value": 0.0,
                                                 "x_min#Value": -1e3, "x_max#Value": 1e3})
    h.comp("MechanicForceTransformer", "Load", {"F#Value": F_start, "P1#Force": F_start, "P1#Position": 0.0})
    h.connect("Cyl", "P3", "Rod", "P1")
    h.connect("Rod", "P2", "Kg", "P1")
    h.connect("Kg", "P2", "Sup", "P1")
    h.connect("Sup", "P2", "Load", "P1")
    h.lookup(folder, "LUF", grid, load, "Load", "F")
    q_gate = (frac >= b.vent_close) if b.deadband else np.ones_like(frac, bool)
    h.lookup(folder, "LUqa", grid, A_h * np.maximum(u, 0.0) * q_gate, "QA", "q")
    h.lookup(folder, "LUqb", grid, A_r * np.maximum(-u, 0.0) * q_gate, "QB", "q")
    vent = a_neutral * np.clip(1.0 - frac / b.vent_close, 0.0, 1.0)
    h.lookup(folder, "LUoa", grid, vent + a_full * frac * (u < 0), "OA", "A")
    h.lookup(folder, "LUob", grid, vent + a_full * frac * (u > 0), "OB", "A")
    n_log = int(t_end / 2e-4) + 1
    model = h.write(folder / f"{b.name}.hmf", n_log=n_log)
    return model, grid, u, t_cmd, t_end, n_log


LOG = ["Rod#P2#Velocity", "Rod#P2#Position", "POCA#P2#Pressure", "POCB#P2#Pressure", "POCA#P1#Pressure",
       "POCB#P1#Pressure", "Kg#P1#Force", "POCA#P1#Flow", "POCB#P1#Flow"]


def run(b: Bench, p, work: Path) -> dict:
    folder = work / b.name
    model, grid, u, t_cmd, t_end, n_log = build(b, p, folder)
    log = list(LOG) + ([] if b.stock_check else ["GTPOCA#out", "GTPOCB#out"]) + (["POCA#x", "POCB#x"] if b.stock_check else [])
    df, _units, info = run_hopsan(model, folder, sim=(0.0, TS, t_end), log_only=log, num_log_samples=n_log, timeout=280.0)
    t = df.index.to_numpy()
    key = {"a": "POCA#x#Value" if b.stock_check else "GTPOCA#out#Value",
           "b": "POCB#x#Value" if b.stock_check else "GTPOCB#out#Value"}
    res = {"t": t, "v": df["Rod#P2#Velocity"].to_numpy(), "x": df["Rod#P2#Position"].to_numpy(),
           "p_h": df["POCA#P2#Pressure"].to_numpy() / 1e5 - 1.0, "p_r": df["POCB#P2#Pressure"].to_numpy() / 1e5 - 1.0,
           "line_a": df["POCA#P1#Pressure"].to_numpy() / 1e5 - 1.0, "line_b": df["POCB#P1#Pressure"].to_numpy() / 1e5 - 1.0,
           "F": df["Kg#P1#Force"].to_numpy(), "open_a": df[key["a"]].to_numpy(), "open_b": df[key["b"]].to_numpy(),
           "grid": grid, "u": u, "t_cmd": t_cmd, "t_end": t_end, "wall_s": info["wall_s"]}
    return res


def formula(b: Bench, p, p_h_bar: float, p_r_bar: float) -> dict:
    """The M1 strokes of m1_plant.dead_strokes_m at the given gauge pressures [mm]."""
    i = b.leg
    A_h, A_r, s0, _ = geometry(p, i)
    values = dead_strokes_m(M1Config(p_crack_Pa=b.crack), p_h_bar * 1e5, p_r_bar * 1e5, s0, b.F_s, A_h, A_r, p.stroke,
                            p.L0r, p.L0h, p.beta, b.p_T)
    return {k: float(v) * (1e3 if k not in ("p_open", "dp_h", "creep_start") else (1e-5 if k != "creep_start" else 1.0))
            for k, v in values.items()}


def open_metrics(b: Bench, res: dict) -> dict:
    """Time and delivered stroke at the first head check opening after the command; pressures just before the command."""
    t, t_cmd = res["t"], res["t_cmd"]
    pre = (t >= t_cmd - 0.05) & (t < t_cmd)
    out = {"p_h_pre": float(res["p_h"][pre].mean()), "p_r_pre": float(res["p_r"][pre].mean()),
           "line_a_pre": float(res["line_a"][pre].mean()), "line_b_pre": float(res["line_b"][pre].mean()),
           "open_b_pre": float(res["open_b"][pre].mean())}
    grid, u = res["grid"], res["u"]
    delivered = np.concatenate([[0.0], np.cumsum(0.5 * (np.abs(u[1:]) + np.abs(u[:-1])) * np.diff(grid))])
    # only spool flow counts: in deadband runs below the closure no pump flow enters
    # first sustained opening (the head check chatters later): first sample open after the command
    k = np.flatnonzero((t >= t_cmd) & (res["open_a"] > 0.5))
    # a vented run with the line low has the check shut; the block run can start open for an instant, take the first
    if k.size == 0:
        out.update({"t_open_s": float("nan"), "stroke_open_mm": float("nan")})
        return out
    j = k[0]
    out.update({"t_open_s": float(t[j] - t_cmd), "stroke_open_mm": float(np.interp(t[j], grid, delivered) * 1e3),
                "p_b_open": float(res["line_b"][j]), "p_h_open": float(res["p_h"][j]), "p_r_open": float(res["p_r"][j]),
                "p_a_open": float(res["line_a"][j])})
    pre_x = float(res["x"][pre].mean())
    out["creep_at_open_mm"] = float((pre_x - res["x"][j]) * 1e3)
    return out


def run_many(benches: list[Bench], p, work: Path, keep=None) -> list[tuple[Bench, dict]]:
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda b: (b, run(b, p, work)), benches))
    return results


__all__ = ["Bench", "BETA_HOSE", "PSI", "REAR_FS_SCALE", "V_LINE", "LEG_NAMES", "formula", "geometry", "load_params", "open_metrics", "pin", "replace", "run", "run_many"]
