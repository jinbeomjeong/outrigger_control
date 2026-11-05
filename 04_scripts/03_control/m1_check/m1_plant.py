"""M1 check-valve opening delay as a wrapper of the reduced-harness plant (nothing in 03_src changes).

Values: pressure_review/m1_m2_reference.json and sec. 12.3 of the report (FL, F_s 0: retract 1.63 mm, net 0.89 mm,
extend 0.39 mm). When a command starts the piston stands until the line (and for a retraction the rod chamber) is
filled up to the check opening pressure. Dead stroke per leg, integral of |u| dt:

  retract  p_B from  p_T + psi p_B - p_h - p_cr = 0,  p_h rising by dp_h = (A_ann (p_B - p_r) - F_s)+ / A_h
           V = V_line (p_B - p_T) / beta_hose + V_r (p_B - p_r)+ / beta + A_ann creep,
           creep = V_h dp_h / (beta A_h),  V_r = A_ann (L0r + s_max - s),  V_h = A_h (L0h + s)
           d_s = V / A_ann
  extend   d_s = V_line (p_h + F_s / A_h + p_cr - p_T) / (beta_hose A_h)

Harness mapping, because the plant kernel already has the seal friction band on its oil reference:
  * extend: the reference file adds V_h F_s / (beta A_h) to the dead stroke. That head compression is what the plant
    friction does once the reference moves (F_s / k_oil), so only the line part is added here.
  * retract: while the fill runs the delivered speed is 0 (the L1-R law stays locked, leg damping = locked), and the
    oil reference creeps down with the fill, by V_h A_ann (p_B - p_r) / (beta A_h^2). The kernel friction band takes
    its first F_s / k_oil, which leaves the reference's friction-reduced piston creep. The creep starts when the
    filled fraction has raised the rod pressure by F_s / A_ann. The anchor c_lock moves with it, so the locked rod
    spring does not read it. The rod pressure rise during the fill is not put into the net force (M2 territory).
  * retract opening: the head chamber charges the head line, the reference drops by
    V_line (p_h + dp_h - p_T) / (beta_hose A_h), after that chunk (so the rod law releases from its locked value).

Neutral form (V-6 unanswered):
  vent   A, B -> T in neutral. The check closes and the line vents whenever the spool passes back into the
         neutral: |u| falling below ``vent_fraction`` v_max (2 % opening of the Hopsan model) or |u| <= eps.
  block  A, B blocked. Only a direction change empties the line (a same direction restart is free).

All inputs are ASSUMPTIONS of the review. Units SI; pressures gauge [Pa]; u = leg speed m/s, extension +.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPS_M_S = 1.0e-6
"""Same threshold as the L1-R rod law (YAML actuator.rod_side.lock_eps_m_s)."""
MAX_LOGGED_FILLS = 600


@dataclass(frozen=True)
class M1Config:
    """One M1 setting. All values are ASSUMPTIONS of the pressure review.

    Attributes:
        neutral: "vent" (A, B -> T) or "block" (A, B blocked).
        volume_scale: Factor on the whole dead volume, the creep and the head discharge.
        vent_fraction: vent only, spool opening below which the line vents; 0 = only at |u| <= eps.
        v_line_m3: MCV to check line volume per port.
        beta_hose_Pa: Effective bulk modulus of the line.
        psi: Pilot ratio of the check.
        p_crack_Pa: Cracking pressure.
    """

    neutral: str = "vent"
    volume_scale: float = 1.0
    vent_fraction: float = 0.02
    v_line_m3: float = 285e-6
    beta_hose_Pa: float = 0.5e9
    psi: float = 3.5
    p_crack_Pa: float = 3e5
    only_side: str = "both"
    """Cause separation: "extend" or "retract" keeps M1 on that side only."""

    def __post_init__(self) -> None:
        if self.neutral not in ("vent", "block"):
            raise ValueError(f"neutral {self.neutral!r}")


def dead_strokes_m(cfg: M1Config, p_h, p_r, s, F_s, A_h, A_ann, s_max, L0r, L0h, beta, p_T) -> dict:
    """Per-leg M1 strokes [m] from the current pressures (arrays or scalars).

    Keys: extend, retract (dead strokes), discharge (reference drop at a retract opening), creep_ref (reference
    creep over a retract fill, friction left to the plant), creep_start (filled fraction where it starts),
    creep_piston (the reference file's piston creep, for the checks), p_open.
    """
    p_h = np.maximum(np.asarray(p_h, float), 0.0)
    p_r = np.asarray(p_r, float)
    s = np.asarray(s, float)
    F_s = np.asarray(F_s, float)
    v_line = cfg.v_line_m3
    extend = v_line * np.maximum(p_h + F_s / A_h + cfg.p_crack_Pa - p_T, 0.0) / cfg.beta_hose_Pa / A_h
    # opening pressure of line B with the head rising once the rod pressure beats the seal friction
    drive = p_h + cfg.p_crack_Pa - p_T
    p_free = np.maximum(drive / cfg.psi, 0.0)
    p_rising = (drive - (A_ann * p_r + F_s) / A_h) / (cfg.psi - A_ann / A_h)
    is_rising = A_ann * (p_free - p_r) > F_s
    p_open = np.where(is_rising, p_rising, p_free)
    dp_h = np.maximum(A_ann * (p_open - p_r) - F_s, 0.0) / A_h
    v_head = A_h * (L0h + s)
    creep_piston = v_head * dp_h / (beta * A_h)
    v_rod = A_ann * (L0r + s_max - s)
    rise = np.maximum(p_open - p_r, 0.0)
    volume = (v_line * np.maximum(p_open - p_T, 0.0) / cfg.beta_hose_Pa + v_rod * rise / beta + A_ann * creep_piston)
    creep_ref = v_head * A_ann * rise / (beta * A_h * A_h)
    with np.errstate(divide="ignore", invalid="ignore"):
        creep_start = np.where(rise > 0.0, np.minimum(F_s / A_ann / rise, 1.0), 1.0)
    scale = cfg.volume_scale
    return {"extend": extend * scale, "retract": volume / A_ann * scale,
            "discharge": v_line * scale * np.maximum(p_h + dp_h - p_T, 0.0) / cfg.beta_hose_Pa / A_h,
            "creep_ref": creep_ref * scale, "creep_start": creep_start, "creep_piston": creep_piston * scale,
            "p_open": p_open, "dp_h": dp_h}


class M1State:
    """Per-plant M1 bookkeeping (deep-copied with the event branches)."""

    def __init__(self, cfg: M1Config, params) -> None:
        self.cfg = cfg
        self.A_h = np.asarray(params.A_h, float)
        self.A_ann = np.asarray(params.A_r, float)
        self.s_max = float(params.stroke)
        self.L0r = float(params.L0r)
        self.L0h = float(params.L0h)
        self.beta = float(params.beta)
        self.p_T = float(params.p_T)
        self.vent_speed = cfg.vent_fraction * float(params.v_max)
        self.open_dir = np.zeros(4, int)
        self.fill_dir = np.zeros(4, int)
        self.filled = np.zeros(4)
        self.crept = np.zeros(4)
        self.fill_start_t = np.full(4, np.nan)
        self.was_above_vent = np.zeros(4, bool)
        self.hold_s = np.zeros((4, 2))
        self.lost_mm = np.zeros((4, 2))
        self.n_fills = np.zeros((4, 2), int)
        self.discharge_mm = np.zeros(4)
        self.creep_mm = np.zeros(4)
        self.pending_shift_m = np.zeros(4)
        self.fills: list = []

    def _empty(self, leg: int) -> None:
        self.open_dir[leg] = 0
        self.filled[leg] = 0.0
        self.crept[leg] = 0.0
        self.fill_dir[leg] = 0

    def summary(self) -> dict:
        """Fill counts, hold time [s], swallowed stroke [mm]; columns extend, retract."""
        return {"n_fills": self.n_fills.tolist(), "hold_s": np.round(self.hold_s, 3).tolist(),
                "lost_mm": np.round(self.lost_mm, 4).tolist(),
                "discharge_mm": np.round(self.discharge_mm, 4).tolist(),
                "creep_mm": np.round(self.creep_mm, 4).tolist(),
                "fills": self.fills[:MAX_LOGGED_FILLS]}


def filter_speeds(state: M1State, plant, u: np.ndarray, chunk_s: float, c_lock: np.ndarray | None):
    """Delivered speeds of one chunk; updates the state, the oil reference and the leg damping."""
    cfg = state.cfg
    delivered = u.copy()
    speed = np.abs(u)
    direction = np.where(speed > EPS_M_S, np.sign(u).astype(int), 0)
    for i in range(4):
        d = direction[i]
        if d != 0 and state.open_dir[i] not in (0, d):  # a direction change empties the line either way
            state._empty(i)
        if d != 0 and state.fill_dir[i] not in (0, d):
            state._empty(i)
        if cfg.neutral == "vent":
            if d == 0 or (state.was_above_vent[i] and speed[i] < state.vent_speed):
                state._empty(i)
                state.was_above_vent[i] = False
            elif speed[i] >= state.vent_speed:
                state.was_above_vent[i] = True
    closed = (direction != 0) & (state.open_dir != direction)
    if not closed.any():
        return delivered
    p_r = np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann, float)
    p_h = (plant.pressure() + p_r * plant.A_ann) / state.A_h
    values = dead_strokes_m(cfg, p_h, p_r, plant.sref, plant.Fs, state.A_h, state.A_ann, state.s_max, state.L0r,
                            state.L0h, state.beta, state.p_T)
    if cfg.only_side == "extend":
        values["retract"], values["discharge"], values["creep_ref"] = (np.zeros(4), np.zeros(4), np.zeros(4))
    elif cfg.only_side == "retract":
        values["extend"] = np.zeros(4)
    for i in np.flatnonzero(closed):
        d = direction[i]
        side = 0 if d > 0 else 1
        if state.fill_dir[i] != d or np.isnan(state.fill_start_t[i]):
            state.fill_dir[i] = d
            state.fill_start_t[i] = plant.t
        state.filled[i] += speed[i] * chunk_s
        need = values["extend"][i] if d > 0 else values["retract"][i]
        if state.filled[i] >= need:
            state.open_dir[i] = d
            state.n_fills[i, side] += 1
            if len(state.fills) < MAX_LOGGED_FILLS:
                state.fills.append((round(float(state.fill_start_t[i]), 3), round(float(plant.t), 3), int(i), int(d),
                                    round(float(need) * 1e3, 4), round(float(p_h[i]) / 1e5, 2),
                                    round(float(p_r[i]) / 1e5, 2)))
            state.fill_start_t[i] = np.nan
            if d < 0:  # applied after this chunk, so the rod law releases from its locked value
                remaining = max(float(values["creep_ref"][i]) - float(state.crept[i]), 0.0)
                state.pending_shift_m[i] = float(values["discharge"][i]) + remaining
                state.discharge_mm[i] += float(values["discharge"][i]) * 1e3
                state.creep_mm[i] += remaining * 1e3
            state.crept[i] = 0.0
        else:
            delivered[i] = 0.0
            state.hold_s[i, side] += chunk_s
            state.lost_mm[i, side] += speed[i] * chunk_s * 1e3
            if c_lock is not None:
                plant.cn = np.array(plant.cn, float)
                plant.cn[i] = c_lock[i]
            if d < 0 and need > 0.0:
                start = float(values["creep_start"][i])
                fraction = state.filled[i] / need
                progress = 0.0 if start >= 1.0 else max(fraction - start, 0.0) / (1.0 - start)
                target = float(values["creep_ref"][i]) * progress
                step = target - state.crept[i]
                if step > 0.0:
                    plant.sref[i] -= step
                    if plant.locked[i]:
                        plant.c_lock[i] -= step
                    state.crept[i] = target
                    state.creep_mm[i] += step * 1e3
    return delivered


LAST_PLANT: list = [None]


def install(verdict_runs, cfg: M1Config | None, c_lock: np.ndarray | None) -> None:
    """Wrap ``verdict_runs.make_flow_plant_class``: the M1 filter in front of the flow limiter.

    With ``cfg`` None the subclass only reports itself (``LAST_PLANT``); it must leave the bits alone.
    """
    original = verdict_runs.make_flow_plant_class

    def make_class(base, setting):
        flow_class = original(base, setting)

        class M1Plant(flow_class):
            """Flow-limited harness plant with the check opening delay (module docstring)."""

            def arm(self):
                LAST_PLANT[0] = self
                result = super().arm()
                if cfg is not None:
                    self.m1 = M1State(cfg, self.flow_limiter.params)
                return result

            def step(self, u, nsteps):
                if cfg is None or not self.armed:
                    return super().step(u, nsteps)
                state = self.m1
                delivered = filter_speeds(state, self, np.asarray(u, float), nsteps * self.dt, c_lock)
                accumulated = super().step(delivered, nsteps)
                if state.pending_shift_m.any():
                    self.sref -= state.pending_shift_m
                    state.pending_shift_m[:] = 0.0
                return accumulated

        return M1Plant

    verdict_runs.make_flow_plant_class = make_class
