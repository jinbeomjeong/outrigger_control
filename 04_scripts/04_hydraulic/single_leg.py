"""Single-leg test bench for the L2 hydraulic force law (spec 6): mechanics, scenarios, metrics.

Two mechanical topologies, both 2 masses + 1 spring + the actuator:
  physical  ground -- k_g -- rod m_r -- [cylinder] -- barrel+superstructure share M   (Chrono intent)
  flipped   barrel fixed -- [cylinder] -- piston/rod m_r -- k_g -- M                  (= Hopsan model;
            HydraulicCylinderC has the barrel fixed to the inertial frame)
  k_g = rod (+) frame (+) concrete in series. Both topologies have the same static state and the same
  dominant mode; they differ only by O(m_r/M) in the rod local mode (spec 6.1).
Optional "merged" variant (L2b-NSC form): no rod mass, k_g moved into the force law as the massless
series spring k_s (l2_cylinder k_series_N_m).

Integrator = what Chrono does with a Python force hook (spec 5): semi-implicit (symplectic) Euler for
the explicit forces; the actuator force is computed after the step from the new state and applied
`lag` steps later (lag 0 = textbook symplectic Euler, lag 1 = pychrono hook, dynamics_model.md 4.6).
`predict` evaluates the force at the state extrapolated to the time it acts (lag compensation).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import l2_cylinder as lc
import numpy as np


@dataclass
class Schedule:
    """Piecewise-linear signals (same breakpoints are written into the Hopsan lookup tables)."""
    D2_N: list = field(default_factory=lambda: [(0.0, 0.0), (1e3, 0.0)])          # downward on M
    q_head: list = field(default_factory=lambda: [(0.0, 0.0), (1e3, 0.0)])         # m^3/s into A
    rod_open: list = field(default_factory=lambda: [(0.0, 0.0), (1e3, 0.0)])       # 0..1
    p_rod_line_g: list = field(default_factory=lambda: [(0.0, 0.0), (1e3, 0.0)])   # Pa gauge
    moving: list = field(default_factory=lambda: [(0.0, 0.0), (1e3, 0.0)])         # 0/1 (c_h switch)

    @staticmethod
    def at(sig: list, t: float) -> float:
        ts, vs = zip(*sig, strict=True)
        return float(np.interp(t, ts, vs))


@dataclass
class Bench:
    prm: lc.CylinderParams
    c: dict                       # scenario constants (l2_params.build)
    topology: str = "physical"    # physical | flipped | merged
    M: float | None = None        # override superstructure mass (stall test: huge)
    F_preload: float | None = None  # constant downward force on M (default M g)


def run(bench: Bench, sch: Schedule, t_end: float, dt: float, lag: int = 0, predict: bool = False,
        out_dt: float = 1e-4, rod_valve_Ks: float | None = None) -> dict:
    """Simulate; return arrays sampled every out_dt."""
    c = bench.c
    prm = bench.prm
    M = bench.M or c["M_eq"]
    F_pre = bench.F_preload if bench.F_preload is not None else c["M_eq"] * c["g"]
    F0 = F_pre if bench.topology != "physical" else F_pre  # cylinder force at rest
    m_r, k_g, g = c["m_r"], c["k_g"], c["g"]
    Ks = c["rod_valve_Ks"] if rod_valve_Ks is None else rod_valve_Ks
    cyl = lc.L2Cylinder(prm)
    s0 = c["s0"]
    cyl.init_static(s0, F0, p_rod_g0=c["p_rod0_g"])

    # state: xM, vM (up +), xr, vr (physical/merged: rod up +; flipped: piston extension +)
    xM = vM = xr = vr = 0.0
    topo = bench.topology
    if topo == "physical":
        dg0 = (F0 + m_r * g) / k_g        # ground spring compression at rest (rod weight to ground)
    else:
        dg0 = F0 / k_g
    F_q = [F0] * (lag + 1)               # force pipeline: F_q[0] acts in the next step
    n = int(round(t_end / dt))
    every = max(1, int(round(out_dt / dt)))
    rec = {k: [] for k in ("t", "s", "v", "xM", "vM", "F", "F_sensor", "p_A_g", "p_B_g",
                           "F_fric", "q_relief", "q_cb", "q_rod", "F_g", "z")}
    last = None
    t = 0.0
    for k in range(n + 1):
        if k > 0:
            F_cyl = F_q[0]
            D2 = Schedule.at(sch.D2_N, t)        # value at the start of the step (explicit)
            if topo == "physical":
                Fg = k_g * (dg0 - xr)
                aM = (F_cyl - F_pre - D2) / M
                ar = (-F_cyl + Fg - m_r * g) / m_r
            elif topo == "flipped":
                Fg = k_g * (dg0 + xr - xM)
                aM = (Fg - F_pre - D2) / M
                ar = (F_cyl - Fg) / m_r
            else:  # merged: rod rigid on the ground, series spring inside the force law
                Fg = F_cyl
                aM = (F_cyl - F_pre - D2) / M
                ar = 0.0
            vM += dt * aM
            vr += dt * ar
            xM += dt * vM
            xr += dt * vr
            t = k * dt
        # hook: link state at the end of the step
        if topo == "physical":
            s, v = s0 + xM - xr, vM - vr
        elif topo == "flipped":
            s, v = s0 + xr, vr
        else:
            s, v = s0 + xM, vM
        inp = lc.Inputs(q_head_m3_s=Schedule.at(sch.q_head, t),
                        rod_valve_open=Schedule.at(sch.rod_open, t), rod_valve_Ks=Ks,
                        p_rod_line_g_Pa=Schedule.at(sch.p_rod_line_g, t),
                        moving=Schedule.at(sch.moving, t) > 0.5,
                        head_poc_open=Schedule.at(sch.moving, t) > 0.5)
        if k == 0:
            out = {"F": F0, "F_sensor": (cyl.st.p_A - prm.fluid.p_atm_Pa) * prm.geometry.area_head_m2,
                   "p_A_g": cyl.st.p_A - prm.fluid.p_atm_Pa, "p_B_g": cyl.st.p_B - prm.fluid.p_atm_Pa,
                   "F_fric": 0.0, "q_relief": 0.0, "q_cb": 0.0, "q_rod": 0.0, "z": 0.0}
            F_new = F0
        else:
            out = cyl.step(s, v, dt, inp)
            F_new = out["F"]
            if predict and lag > 0:
                F_new = cyl.force_preview(s + lag * dt * v, v, dt, inp)
            F_q = F_q[1:] + [F_new]
        last = out
        if k % every == 0:
            Fg_now = (k_g * (dg0 - xr) if topo == "physical" else
                      (k_g * (dg0 + xr - xM) if topo == "flipped" else out["F"]))
            for key, val in (("t", t), ("s", s), ("v", v), ("xM", xM), ("vM", vM), ("F", out["F"]),
                             ("F_sensor", out["F_sensor"]), ("p_A_g", out["p_A_g"]),
                             ("p_B_g", out["p_B_g"]), ("F_fric", out.get("F_fric", 0.0)),
                             ("q_relief", out.get("q_relief", 0.0)), ("q_cb", out.get("q_cb", 0.0)),
                             ("q_rod", out.get("q_rod", 0.0)), ("F_g", Fg_now), ("z", out.get("z", 0.0))):
                rec[key].append(val)
        if not math.isfinite(F_new) or abs(F_new) > 1e9:
            rec["diverged_at_s"] = t
            break
    res = {k: np.asarray(v) for k, v in rec.items() if isinstance(v, list)}
    if "diverged_at_s" in rec:
        res["diverged_at_s"] = rec["diverged_at_s"]
    res["final"] = last
    return res


# ---------------------------------------------------------------------------------------------
# metrics (shared by the Python and Hopsan results)
# ---------------------------------------------------------------------------------------------


def step_metrics(t: np.ndarray, y: np.ndarray, t_step: float, t_end_window: float = 0.6) -> dict:
    """Peak, final, overshoot, dominant frequency and damping (log decrement) of a step response."""
    pre = y[(t > t_step - 0.05) & (t < t_step)]
    y0 = float(np.mean(pre)) if pre.size else float(y[0])
    post = t >= t_step
    tt, yy = t[post], y[post]
    yf = float(np.mean(yy[tt > tt[-1] - t_end_window]))
    imax = int(np.argmax(yy))
    peak = float(yy[imax])
    step = yf - y0
    out = {"initial": y0, "final": yf, "peak": peak, "t_peak": float(tt[imax] - t_step),
           "overshoot_ratio": (peak - yf) / step if step else float("nan")}
    # damped frequency and damping from successive maxima of (y - yf)
    e = yy - yf
    idx = [i for i in range(1, len(e) - 1) if e[i] > e[i - 1] and e[i] >= e[i + 1] and e[i] > 0.02 * abs(step)]
    if len(idx) >= 3:
        tp = tt[idx]
        ap = e[idx]
        Td = float(np.median(np.diff(tp[:6])))
        dec = np.log(ap[:-1] / ap[1:])[:5]
        delta = float(np.mean(dec))
        zeta = delta / math.sqrt(4 * math.pi ** 2 + delta ** 2)
        out.update({"f_damped_Hz": 1.0 / Td, "zeta_logdec": zeta, "n_peaks": len(idx)})
    band = 0.02 * abs(step) if step else 0.0
    outside = np.where(np.abs(yy - yf) > band)[0]
    out["settle_2pct_s"] = float(tt[outside[-1]] - t_step) if outside.size else 0.0
    return out
