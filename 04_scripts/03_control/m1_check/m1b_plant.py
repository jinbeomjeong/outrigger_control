"""M1b check-valve opening model as a wrapper of the reduced-harness plant (nothing in 03_src changes).

Rules from the Hopsan extrapolation check (pressure_review/m1_hopsan, formulas of t5_formula.py and t2_chop.py).
All hydraulic inputs are ASSUMPTIONS. Pressures gauge [Pa], u = leg speed m/s, extension +.

Retract, d_s = [V_line (p_B - p_T) / beta_h + V_r (p_rod - p_r) / beta + A_ann V_h dp_h / (beta A_h)] / A_ann + void:
  p_T + psi p_B - p_h - dp_h - p_cr = 0,  dp_h = (A_ann (p_rod - p_r) - F_band)+ / A_h,  p_rod = max(p_B - delta, p_r)
  delta = p_cr when the rod check passes forward, 0 when it is piloted open.
  F_band = F_s - f: friction band left in the retract direction, from the kernel friction state f.
  void = (c - c_lock - knee)+ while locked: oil the floor-limited rod spring did not get (the law carries it, so
  refilling is a shift of its anchor c_lock).
State of the line, stroke units: x' = |u| - K_n (1 - |u| / (c_v v_max))+ sqrt((p_open - p_T) x / d_s) / A, x >= 0;
  x >= d_s opens; a direction change empties it. Extend uses A_h, retract A_ann. K_n = 0.05 K_land (ASSUMPTION).
Rod chamber exchange through the centre vent, locked legs, circuit VR only:
  refill  p_r < p_T: Q = K_n (1 - |u| / (c_v v_max))+ sqrt(p_T - p_r)
  rule 4  p_T < p_r < p_T (1 + psi) - p_cr: the check is open, Q out = same form of sqrt(p_r - p_T)
Option 5 (not tested on Hopsan): extension needs the rod check open too, d_s,ext = max(head, V_line (p_A - p_T) / (beta_h A_h)),
  p_A = (p_r + p_cr - p_T) / psi.
Extension dead stroke keeps the line part only; the head compression by friction is the plant kernel's band.
Reference creep during a retract fill and the head discharge at opening: as ``m1_plant``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

EPS_M_S = 1.0e-6
MAX_LOGGED_FILLS = 600


@dataclass(frozen=True)
class M1bConfig:
    """One M1b setting (module docstring); every value is an ASSUMPTION.

    Attributes:
        neutral: "vent" or "block".
        refill: Rod refill through the vent (VR).
        rod_open_low: Rule 4, rod chamber vents below p_T (1 + psi) - p_cr (VR).
        rod_forward: delta = p_cr (VN); False = piloted open, delta = 0 (VR, BL).
        c_v: Spool opening where the vent is shut, fraction of v_max.
        volume_scale: Factor on line, rod chamber, creep and head discharge volumes (not the void).
        rod_release: Option 5.
        no_delay: Rod exchange only, no dead stroke (to separate rule 4 from the delay).
    """

    neutral: str = "vent"
    refill: bool = False
    rod_open_low: bool = False
    rod_forward: bool = False
    c_v: float = 0.02
    volume_scale: float = 1.0
    rod_release: bool = False
    no_delay: bool = False
    rod_early: bool = False
    """Added after the first R12 result (not in the criteria list, not on the Hopsan unit tables): extension releases the
    rod law at the line pressure that opens the rod check, not at the head check opening."""
    v_line_m3: float = 285e-6
    beta_hose_Pa: float = 0.5e9
    psi: float = 3.5
    p_crack_Pa: float = 3e5
    neutral_fraction: float = 0.05

    def __post_init__(self) -> None:
        if self.neutral not in ("vent", "block"):
            raise ValueError(f"neutral {self.neutral!r}")


def retract_dead(cfg: M1bConfig, p_h, p_r, F_band, s, void_m, A_h, A_ann, s_max, L0r, L0h, beta, p_T, delta=None) -> dict:
    """Retract dead stroke and its parts for one leg (scalars) [m], pressures [Pa]."""
    p_h = max(float(p_h), 0.0)
    delta = (cfg.p_crack_Pa if cfg.rod_forward else 0.0) if delta is None else delta
    drive = p_h + cfg.p_crack_Pa - p_T
    p_free = max(drive / cfg.psi, 0.0)
    if A_ann * (p_free - delta - p_r) > F_band:
        p_b = (drive - (A_ann * (delta + p_r) + F_band) / A_h) / (cfg.psi - A_ann / A_h)
    else:
        p_b = p_free
    p_rod = max(p_b - delta, p_r)
    dp_h = max(A_ann * (p_rod - p_r) - F_band, 0.0) / A_h
    v_head = A_h * (L0h + s)
    v_rod = A_ann * (L0r + s_max - s)
    scale = cfg.volume_scale
    volume = (cfg.v_line_m3 * max(p_b - p_T, 0.0) / cfg.beta_hose_Pa + v_rod * (p_rod - p_r) / beta
              + A_ann * v_head * dp_h / (beta * A_h)) * scale
    rise = p_rod - p_r
    creep_ref = v_head * A_ann * rise / (beta * A_h * A_h) * scale
    start = min(F_band / A_ann / rise, 1.0) if rise > 0.0 else 1.0
    discharge = cfg.v_line_m3 * scale * max(p_h + dp_h - p_T, 0.0) / cfg.beta_hose_Pa / A_h
    return {"need": volume / A_ann + void_m, "p_open": p_b, "dp_h": dp_h, "creep_ref": creep_ref, "creep_start": start,
            "discharge": discharge}


def extend_dead(cfg: M1bConfig, p_h, p_r, F_s, A_h, p_T) -> dict:
    """Extend dead stroke for one leg (scalars) [m]."""
    p_h = max(float(p_h), 0.0)
    p_open = p_h + F_s / A_h + cfg.p_crack_Pa
    if cfg.rod_release:
        p_open = max(p_open, (p_r + cfg.p_crack_Pa - p_T) / cfg.psi)
    return {"need": cfg.v_line_m3 * cfg.volume_scale * max(p_open - p_T, 0.0) / cfg.beta_hose_Pa / A_h, "p_open": p_open}


class M1bState:
    """Per-plant M1b bookkeeping (deep-copied with the event branches)."""

    def __init__(self, cfg: M1bConfig, params) -> None:
        self.cfg = cfg
        self.A_h = np.asarray(params.A_h, float)
        self.A_ann = np.asarray(params.A_r, float)
        self.s_max = float(params.stroke)
        self.L0r = float(params.L0r)
        self.L0h = float(params.L0h)
        self.beta = float(params.beta)
        self.p_T = float(params.p_T)
        self.v_max = float(params.v_max)
        k_land = self.A_h * self.v_max / math.sqrt(float(params.dp_comp))
        self.K_n = (cfg.neutral_fraction if cfg.neutral == "vent" else 0.0) * k_land
        self.rod_open_limit = self.p_T * (1.0 + cfg.psi) - cfg.p_crack_Pa
        self.x = np.zeros(4)
        self.line_dir = np.zeros(4, int)
        self.is_open = np.zeros(4, bool)
        self.charged = np.zeros(4, bool)
        self.crept = np.zeros(4)
        self.fill_start_t = np.full(4, np.nan)
        self.pending_shift_m = np.zeros(4)
        self.hold_s = np.zeros((4, 2))
        self.lost_mm = np.zeros((4, 2))
        self.n_fills = np.zeros((4, 2), int)
        self.discharge_mm = np.zeros(4)
        self.creep_mm = np.zeros(4)
        self.rod_in_cm3 = np.zeros(4)
        self.rod_out_cm3 = np.zeros(4)
        self.void_peak_mm = np.zeros(4)
        self.drained_mm = np.zeros(4)
        self.fills: list = []

    def summary(self) -> dict:
        return {"n_fills": self.n_fills.tolist(), "hold_s": np.round(self.hold_s, 3).tolist(),
                "lost_mm": np.round(self.lost_mm, 4).tolist(), "discharge_mm": np.round(self.discharge_mm, 4).tolist(),
                "creep_mm": np.round(self.creep_mm, 4).tolist(), "rod_in_cm3": np.round(self.rod_in_cm3, 3).tolist(),
                "rod_out_cm3": np.round(self.rod_out_cm3, 3).tolist(), "void_peak_mm": np.round(self.void_peak_mm, 3).tolist(),
                "drained_mm": np.round(self.drained_mm, 3).tolist(), "fills": self.fills[:MAX_LOGGED_FILLS]}


def _void_m(plant, leg: int) -> float:
    if not plant.locked[leg]:
        return 0.0
    knee = (plant.p_r0[leg] - plant.p_floor) * plant.A_ann[leg] / plant.kr[leg]
    return max(float(plant.sref[leg] - plant.x[leg] - plant.c_lock[leg] - knee), 0.0)


def _rod_exchange(state: M1bState, plant, speed: np.ndarray, chunk_s: float) -> None:
    """Vent exchange of a locked rod chamber: an anchor shift of the law (void and refill stay in one number)."""
    cfg = state.cfg
    if not (cfg.refill or cfg.rod_open_low):
        return
    p_r = np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann, float)
    for i in range(4):
        if not plant.locked[i]:
            continue
        gate = max(1.0 - speed[i] / (cfg.c_v * state.v_max), 0.0)
        if gate == 0.0:
            continue
        if p_r[i] < state.p_T and cfg.refill:
            volume = state.K_n[i] * gate * math.sqrt(state.p_T - max(p_r[i], plant.p_floor)) * chunk_s
            plant.c_lock[i] += volume / state.A_ann[i]
            state.rod_in_cm3[i] += volume * 1e6
        elif state.p_T < p_r[i] < state.rod_open_limit and cfg.rod_open_low:
            volume = state.K_n[i] * gate * math.sqrt(p_r[i] - state.p_T) * chunk_s
            plant.c_lock[i] -= volume / state.A_ann[i]
            state.rod_out_cm3[i] += volume * 1e6


def filter_speeds(state: M1bState, plant, u: np.ndarray, chunk_s: float, c_lock: np.ndarray | None):
    """Delivered speeds of one chunk; updates the state, the oil reference and the leg damping."""
    cfg = state.cfg
    delivered = u.copy()
    speed = np.abs(u)
    _rod_exchange(state, plant, speed, chunk_s)
    if cfg.no_delay:
        return delivered
    direction = np.where(speed > EPS_M_S, np.sign(u).astype(int), 0)
    p_r = np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann, float)
    p_h = (plant.pressure() + p_r * plant.A_ann) / state.A_h
    for i in range(4):
        void = _void_m(plant, i)
        state.void_peak_mm[i] = max(state.void_peak_mm[i], void * 1e3)
        d = int(direction[i])
        if d != 0 and state.line_dir[i] not in (0, d):  # a direction change empties the line
            state.x[i] = 0.0
            state.is_open[i] = False
            state.charged[i] = False
            state.line_dir[i] = 0
            state.crept[i] = 0.0
        active = d if d != 0 else int(state.line_dir[i])
        if active == 0:
            continue
        side = 0 if active > 0 else 1
        area = state.A_h[i] if active > 0 else state.A_ann[i]
        if active > 0:
            values = extend_dead(cfg, p_h[i], p_r[i], float(plant.Fs[i]), state.A_h[i], state.p_T)
        else:
            f_band = float(plant.Fs[i]) - float(plant.f[i])
            values = retract_dead(cfg, p_h[i], p_r[i], f_band, float(plant.sref[i]), void, state.A_h[i], state.A_ann[i],
                                  state.s_max, state.L0r, state.L0h, state.beta, state.p_T)
        need = values["need"]
        gate = max(1.0 - speed[i] / (cfg.c_v * state.v_max), 0.0)
        rise = max(values["p_open"] - state.p_T, 0.0)
        level = min(state.x[i] / need, 1.0) if need > 0.0 else 0.0
        drain = state.K_n[i] * gate * math.sqrt(rise * level) / area
        state.drained_mm[i] += min(drain * chunk_s, state.x[i]) * 1e3
        if d == 0:  # no flow in: the line bleeds down
            state.x[i] = max(state.x[i] - drain * chunk_s, 0.0)
            state.is_open[i] = False
            _creep_step(state, plant, i, values, active, need)
            if state.x[i] == 0.0:
                if cfg.neutral == "vent":
                    state.line_dir[i] = 0
                    state.charged[i] = False
                state.fill_start_t[i] = np.nan
            continue
        state.line_dir[i] = d
        if state.is_open[i]:
            if speed[i] >= drain:
                delivered[i] = d * (speed[i] - drain)
                state.x[i] = need
                continue
            state.is_open[i] = False
        if np.isnan(state.fill_start_t[i]):
            state.fill_start_t[i] = plant.t
        state.x[i] = max(state.x[i] + (speed[i] - drain) * chunk_s, 0.0)
        if state.x[i] >= need:
            state.x[i] = need
            state.is_open[i] = True
            if not state.charged[i]:  # first opening since the line was empty; a re-opening recharges nothing
                state.charged[i] = True
                state.n_fills[i, side] += 1
                if len(state.fills) < MAX_LOGGED_FILLS:
                    state.fills.append((round(float(state.fill_start_t[i]), 3), round(float(plant.t), 3), int(i), d,
                                        round(float(need) * 1e3, 4), round(float(p_h[i]) / 1e5, 2), round(float(p_r[i]) / 1e5, 2),
                                        round(void * 1e3, 3)))
                if d < 0:  # after this chunk, so the rod law releases from its locked value
                    remaining = max(float(values["creep_ref"]) - float(state.crept[i]), 0.0)
                    state.pending_shift_m[i] = float(values["discharge"]) + remaining
                    state.discharge_mm[i] += float(values["discharge"]) * 1e3
                    state.creep_mm[i] += remaining * 1e3
            state.fill_start_t[i] = np.nan
            state.crept[i] = 0.0
            continue
        delivered[i] = 0.0
        if cfg.rod_early and d > 0 and need > 0.0:
            # the rod check opens when line A reaches (p_r + p_cr - p_T) / psi, before the head check: the law releases
            # (a speed just above its lock threshold, about 1e-3 mm over a fill) while the piston still stands
            p_a = (p_r[i] + cfg.p_crack_Pa - state.p_T) / cfg.psi
            if state.x[i] / need >= (p_a - state.p_T) / max(values["p_open"] - state.p_T, 1.0):
                delivered[i] = 1.5 * EPS_M_S
        state.hold_s[i, side] += chunk_s
        state.lost_mm[i, side] += speed[i] * chunk_s * 1e3
        if c_lock is not None:
            plant.cn = np.array(plant.cn, float)
            plant.cn[i] = c_lock[i]
        _creep_step(state, plant, i, values, active, need)
    return delivered


def _creep_step(state: M1bState, plant, i: int, values: dict, active: int, need: float) -> None:
    """Reference creep of a retract fill with the fill level, reversible while the line bleeds down."""
    if active >= 0 or need <= 0.0:
        return
    start = float(values["creep_start"])
    progress = 0.0 if start >= 1.0 else max(state.x[i] / need - start, 0.0) / (1.0 - start)
    target = float(values["creep_ref"]) * min(progress, 1.0)
    step = target - state.crept[i]
    if step != 0.0:
        plant.sref[i] -= step
        if plant.locked[i]:
            plant.c_lock[i] -= step
        state.crept[i] = target
        state.creep_mm[i] += step * 1e3


LAST_PLANT: list = [None]


def install(verdict_runs, cfg: M1bConfig | None, c_lock: np.ndarray | None) -> None:
    """Wrap ``verdict_runs.make_flow_plant_class``: M1b in front of the flow limiter; None leaves the bits alone."""
    original = verdict_runs.make_flow_plant_class

    def make_class(base, setting):
        flow_class = original(base, setting)

        class M1bPlant(flow_class):
            """Flow-limited harness plant with the M1b check opening (module docstring)."""

            def arm(self):
                LAST_PLANT[0] = self
                result = super().arm()
                if cfg is not None:
                    self.m1b = M1bState(cfg, self.flow_limiter.params)
                return result

            def step(self, u, nsteps):
                if cfg is None or not self.armed:
                    return super().step(u, nsteps)
                state = self.m1b
                delivered = filter_speeds(state, self, np.asarray(u, float), nsteps * self.dt, c_lock)
                accumulated = super().step(delivered, nsteps)
                if state.pending_shift_m.any():
                    self.sref -= state.pending_shift_m
                    state.pending_shift_m[:] = 0.0
                return accumulated

        return M1bPlant

    verdict_runs.make_flow_plant_class = make_class
