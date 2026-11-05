"""M1c check-valve model on the reduced harness: the extend start of E1 and the rod vent of E3; retract as M1b.

Rules: hydraulics-expert, pressure_review/m1_hopsan/t9_quintic. All hydraulic inputs are ASSUMPTIONS. Pressures gauge [Pa],
u = leg speed m/s, extension +. Nothing in 03_src changes and ``m1b_plant`` stays as it was.

E1, extend start. Line state x (stroke units): x' = |u| - K_n g sqrt(p_A - p_T) / A_h, g = (1 - |u| / (c_v v_max))+,
  p_A = p_T + x A_h beta_h / V_line.
  Rod check opens when p_B + psi (p_A - p_ref) - p_r - p_cr > 0 with p_B = p_T; p_ref = 0 for VR and BL, p_T for VN.
  After that p_B = (C_r p_r + C_l p_T) / (C_r + C_l), then it follows p_r (the smaller of the two).
  Head check, every chunk: p_A + psi p_B - p_h - p_cr > 0. The friction term stays out; the kernel band has it.
  Until the head check opens the piston gets no commanded flow; the rod law still releases (a speed just above its lock
  threshold, about 1e-3 mm over a fill) and makes the release motion.
E3, VR only, locked: a rod check that starts open stays open with no upper bound, Q_out = K_n g sqrt(p_r - p_T), p_r > p_T.
  The vent line follows the rod (p_B = p_r), so it closes only if p_r - p_B > psi p_A - p_cr. A lock above
  p_T (1 + psi) - p_cr starts closed; a closed check opens by the opening law above.
Refill (VR, p_r < p_T) and the whole retract side: as ``m1b_plant.retract_dead``.
Sensitivities, off in the nominal: E2, rod law after release (C_r + C_l + C_h) p_r' = A_ann u - K_land (|u| / v_max) sqrt(p_r - p_T),
  p_r(0+) = p_B,eq; E4, locked with p_T + psi p_r >= p_h + p_cr: s_ref' = -K_n g sqrt(p_h - p_T) / A_h after the discharge
  V_line (p_h - p_T) / (beta_h A_h) into line A.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from m1b_plant import M1bConfig, _void_m, retract_dead

EPS_M_S = 1.0e-6
RELEASE_SPEED_M_S = 1.5 * EPS_M_S
MAX_LOGGED_FILLS = 600


@dataclass(frozen=True)
class M1cConfig:
    """One setting. ``kind``: "VR", "VN" or "BL". ``no_delay``: no line state at all (with ``e2`` only the release law)."""

    kind: str = "VN"
    c_v: float = 0.02
    volume_scale: float = 1.0
    e2: bool = False
    e4: bool = False
    no_delay: bool = False
    v_line_m3: float = 285e-6
    beta_hose_Pa: float = 0.5e9
    psi: float = 3.5
    p_crack_Pa: float = 3e5
    neutral_fraction: float = 0.05

    def __post_init__(self) -> None:
        if self.kind not in ("VR", "VN", "BL"):
            raise ValueError(f"kind {self.kind!r}")

    @property
    def is_vent(self) -> bool:
        return self.kind != "BL"

    @property
    def p_ref_T(self) -> bool:
        return self.kind == "VN"

    def retract_config(self) -> M1bConfig:
        return M1bConfig(neutral="vent" if self.is_vent else "block", rod_forward=self.kind == "VN", c_v=self.c_v,
                         volume_scale=self.volume_scale, v_line_m3=self.v_line_m3, beta_hose_Pa=self.beta_hose_Pa,
                         psi=self.psi, p_crack_Pa=self.p_crack_Pa, neutral_fraction=self.neutral_fraction)


def p_a_of_x(cfg: M1cConfig, x: float, A_h: float, p_T: float) -> float:
    return p_T + x * A_h * cfg.beta_hose_Pa / (cfg.v_line_m3 * cfg.volume_scale)


def rod_opens(cfg: M1cConfig, p_a: float, p_r: float, p_b: float, p_T: float) -> bool:
    """Opening law of the rod check."""
    p_ref = p_T if cfg.p_ref_T else 0.0
    return p_b + cfg.psi * (p_a - p_ref) - p_r - cfg.p_crack_Pa > 0.0


def p_b_equalized(p_r: float, p_T: float, c_r: float, c_l: float) -> float:
    return (c_r * p_r + c_l * p_T) / (c_r + c_l)


def head_opens(cfg: M1cConfig, p_a: float, p_b: float, p_h: float) -> bool:
    return p_a + cfg.psi * p_b - p_h - cfg.p_crack_Pa > 0.0


def drain_speed(K_n: float, gate: float, p_a: float, p_T: float, A_h: float) -> float:
    return K_n * gate * math.sqrt(max(p_a - p_T, 0.0)) / A_h


class M1cState:
    """Per-plant M1c bookkeeping (deep-copied with the event branches)."""

    def __init__(self, cfg: M1cConfig, params, plant) -> None:
        self.cfg = cfg
        self.retract_cfg = cfg.retract_config()
        self.A_h = np.asarray(params.A_h, float)
        self.A_ann = np.asarray(params.A_r, float)
        self.s_max = float(params.stroke)
        self.L0r = float(params.L0r)
        self.L0h = float(params.L0h)
        self.beta = float(params.beta)
        self.p_T = float(params.p_T)
        self.v_max = float(params.v_max)
        self.K_land = self.A_h * self.v_max / math.sqrt(float(params.dp_comp))
        self.K_n = (cfg.neutral_fraction if cfg.is_vent else 0.0) * self.K_land
        self.rod_limit = self.p_T * (1.0 + cfg.psi) - cfg.p_crack_Pa
        self.x = np.zeros(4)
        self.line_dir = np.zeros(4, int)
        self.is_open = np.zeros(4, bool)
        self.charged = np.zeros(4, bool)
        self.crept = np.zeros(4)
        self.fill_start_t = np.full(4, np.nan)
        self.pending_shift_m = np.zeros(4)
        self.rod_released = np.zeros(4, bool)
        self.p_b_after = np.full(4, np.nan)
        self.rod_vent_open = np.ones(4, bool) if cfg.kind == "VR" else np.zeros(4, bool)
        self.was_locked = np.ones(4, bool)
        self.e2_p_r = np.full(4, np.nan)
        self.u_cmd = np.zeros(4)
        self.e4_discharged = np.zeros(4, bool)
        self.hold_s = np.zeros((4, 2))
        self.lost_mm = np.zeros((4, 2))
        self.n_fills = np.zeros((4, 2), int)
        self.discharge_mm = np.zeros(4)
        self.creep_mm = np.zeros(4)
        self.rod_in_cm3 = np.zeros(4)
        self.rod_out_cm3 = np.zeros(4)
        self.void_peak_mm = np.zeros(4)
        self.e4_mm = np.zeros(4)
        self.n_rod_closed = np.zeros(4, int)
        self.fills: list = []
        self.ext_starts: list = []

    def compliances(self, plant, i: int) -> tuple[float, float, float]:
        s = float(plant.sref[i])
        c_r = self.A_ann[i] * (self.L0r + self.s_max - s) / self.beta
        c_l = self.cfg.v_line_m3 * self.cfg.volume_scale / self.cfg.beta_hose_Pa
        c_h = self.A_ann[i] ** 2 * (self.L0h + s) / (self.beta * self.A_h[i])
        return c_r, c_l, c_h

    def summary(self) -> dict:
        return {"n_fills": self.n_fills.tolist(), "hold_s": np.round(self.hold_s, 3).tolist(), "lost_mm": np.round(self.lost_mm, 4).tolist(),
                "discharge_mm": np.round(self.discharge_mm, 4).tolist(), "creep_mm": np.round(self.creep_mm, 4).tolist(),
                "rod_in_cm3": np.round(self.rod_in_cm3, 3).tolist(), "rod_out_cm3": np.round(self.rod_out_cm3, 3).tolist(),
                "void_peak_mm": np.round(self.void_peak_mm, 3).tolist(), "e4_mm": np.round(self.e4_mm, 3).tolist(),
                "n_rod_closed": self.n_rod_closed.tolist(), "fills": self.fills[:MAX_LOGGED_FILLS], "ext_starts": self.ext_starts}


def rod_pressure(plant) -> np.ndarray:
    return np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann, float)


def _rod_exchange(state: M1cState, plant, speed: np.ndarray, p_r: np.ndarray, chunk_s: float) -> None:
    """E3 and the refill, VR only: an anchor shift of the locked law."""
    if state.cfg.kind != "VR":
        return
    for i in range(4):
        if not plant.locked[i]:
            continue
        gate = max(1.0 - speed[i] / (state.cfg.c_v * state.v_max), 0.0)
        if p_r[i] < state.p_T:
            if gate > 0.0:
                volume = state.K_n[i] * gate * math.sqrt(state.p_T - max(p_r[i], plant.p_floor)) * chunk_s
                plant.c_lock[i] += volume / state.A_ann[i]
                state.rod_in_cm3[i] += volume * 1e6
        elif state.rod_vent_open[i] and gate > 0.0:
            volume = state.K_n[i] * gate * math.sqrt(p_r[i] - state.p_T) * chunk_s
            plant.c_lock[i] -= volume / state.A_ann[i]
            state.rod_out_cm3[i] += volume * 1e6


def _update_rod_vent(state: M1cState, plant, p_r: np.ndarray) -> None:
    """E3: state of the rod check of a locked leg, line A at the line state, line B following the rod while open."""
    if state.cfg.kind != "VR":
        return
    for i in range(4):
        locked = bool(plant.locked[i])
        if locked and not state.was_locked[i]:
            state.rod_vent_open[i] = bool(p_r[i] <= state.rod_limit)
        elif locked and not state.rod_vent_open[i]:
            p_a = p_a_of_x(state.cfg, state.x[i], state.A_h[i], state.p_T) if state.line_dir[i] > 0 else state.p_T
            if rod_opens(state.cfg, p_a, p_r[i], state.p_T, state.p_T):
                state.rod_vent_open[i] = True
        state.was_locked[i] = locked


def _e4_step(state: M1cState, plant, speed: np.ndarray, p_r: np.ndarray, p_h: np.ndarray, chunk_s: float) -> None:
    """E4 sensitivity: the rod pressure pilots the head check open on a locked leg."""
    cfg = state.cfg
    for i in range(4):
        if plant.locked[i] and state.p_T + cfg.psi * p_r[i] >= p_h[i] + cfg.p_crack_Pa and p_h[i] > state.p_T:
            step = 0.0
            if not state.e4_discharged[i]:
                state.e4_discharged[i] = True
                step += cfg.v_line_m3 * cfg.volume_scale * (p_h[i] - state.p_T) / cfg.beta_hose_Pa / state.A_h[i]
            gate = max(1.0 - speed[i] / (cfg.c_v * state.v_max), 0.0)
            step += state.K_n[i] * gate * math.sqrt(p_h[i] - state.p_T) / state.A_h[i] * chunk_s
            plant.sref[i] -= step
            plant.c_lock[i] -= step
            state.e4_mm[i] += step * 1e3
        elif not plant.locked[i] or state.p_T + cfg.psi * p_r[i] < p_h[i] + cfg.p_crack_Pa:
            state.e4_discharged[i] = False


def filter_speeds(state: M1cState, plant, u: np.ndarray, chunk_s: float, c_lock: np.ndarray | None):
    """Delivered speeds of one chunk; updates the state, the oil reference and the leg damping."""
    cfg = state.cfg
    delivered = u.copy()
    speed = np.abs(u)
    state.u_cmd = speed.copy()
    p_r = rod_pressure(plant)
    p_h = (plant.pressure() + p_r * plant.A_ann) / state.A_h
    _update_rod_vent(state, plant, p_r)
    _rod_exchange(state, plant, speed, p_r, chunk_s)
    if cfg.e4:
        _e4_step(state, plant, speed, p_r, p_h, chunk_s)
    if cfg.no_delay:
        return delivered
    direction = np.where(speed > EPS_M_S, np.sign(u).astype(int), 0)
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
            state.rod_released[i] = False
            state.p_b_after[i] = np.nan
        active = d if d != 0 else int(state.line_dir[i])
        if plant.locked[i] and d == 0:
            state.rod_released[i] = False
            state.p_b_after[i] = np.nan
        if active == 0:
            continue
        gate = max(1.0 - speed[i] / (cfg.c_v * state.v_max), 0.0)
        if active > 0:
            _extend_chunk(state, plant, i, d, speed[i], gate, p_r[i], p_h[i], chunk_s, delivered, c_lock)
        else:
            _retract_chunk(state, plant, i, d, speed[i], gate, p_r[i], p_h[i], void, chunk_s, delivered, c_lock)
    return delivered


def _extend_chunk(state, plant, i, d, speed, gate, p_r, p_h, chunk_s, delivered, c_lock) -> None:
    cfg = state.cfg
    A_h = state.A_h[i]
    p_a = p_a_of_x(cfg, state.x[i], A_h, state.p_T)
    drain = drain_speed(state.K_n[i], gate, p_a, state.p_T, A_h)
    if d == 0:  # no flow in: the line bleeds down, the head check is shut
        state.x[i] = max(state.x[i] - drain * chunk_s, 0.0)
        state.is_open[i] = False
        if state.x[i] == 0.0 and cfg.is_vent:
            state.line_dir[i] = 0
            state.charged[i] = False
        return
    if state.x[i] == 0.0 and not state.is_open[i] and not state.charged[i] and len(state.ext_starts) < MAX_LOGGED_FILLS:
        # the state a fill starts from (record only): compared with the zones the boundary unit missed
        state.ext_starts.append((round(float(plant.t), 3), int(i), round(float(p_h) / 1e5, 2), round(float(p_r) / 1e5, 2), round(float(speed) * 1e3, 3)))
    state.line_dir[i] = 1
    state.x[i] = max(state.x[i] + (speed - drain) * chunk_s, 0.0)
    p_a = p_a_of_x(cfg, state.x[i], A_h, state.p_T)
    rod_open_now = cfg.kind == "VR" and bool(state.rod_vent_open[i])
    if not state.rod_released[i]:
        if rod_open_now or rod_opens(cfg, p_a, p_r, state.p_T, state.p_T):
            state.rod_released[i] = True
            if not rod_open_now:
                c_r, c_l, _ = state.compliances(plant, i)
                state.p_b_after[i] = p_b_equalized(p_r, state.p_T, c_r, c_l)
            if cfg.e2:
                c_r, c_l, _ = state.compliances(plant, i)
                state.e2_p_r[i] = p_r if rod_open_now else p_b_equalized(p_r, state.p_T, c_r, c_l)
    if state.rod_released[i]:
        p_b = p_r if np.isnan(state.p_b_after[i]) else min(state.p_b_after[i], p_r)
    else:
        p_b = state.p_T
    if state.rod_released[i] and head_opens(cfg, p_a, p_b, p_h):
        if not state.charged[i]:
            state.charged[i] = True
            state.n_fills[i, 0] += 1
            if len(state.fills) < MAX_LOGGED_FILLS:
                start = plant.t if np.isnan(state.fill_start_t[i]) else state.fill_start_t[i]
                state.fills.append((round(float(start), 3), round(float(plant.t), 3), int(i), 1, round(float(state.x[i]) * 1e3, 4),
                                    round(float(p_h) / 1e5, 2), round(float(p_r) / 1e5, 2), round(float(p_a) / 1e5, 2), round(float(p_b) / 1e5, 2)))
            state.fill_start_t[i] = np.nan
        state.is_open[i] = True
        # the line stays at the opening pressure while the flow passes the check
        delivered[i] = max(speed - drain, RELEASE_SPEED_M_S)
        target = (p_h + cfg.p_crack_Pa - cfg.psi * p_b - state.p_T) * (cfg.v_line_m3 * cfg.volume_scale) / (A_h * cfg.beta_hose_Pa)
        state.x[i] = max(target, 0.0)
        return
    state.is_open[i] = False
    if np.isnan(state.fill_start_t[i]):
        state.fill_start_t[i] = plant.t
    delivered[i] = RELEASE_SPEED_M_S if state.rod_released[i] else 0.0
    state.hold_s[i, 0] += chunk_s
    state.lost_mm[i, 0] += speed * chunk_s * 1e3
    if c_lock is not None:
        plant.cn = np.array(plant.cn, float)
        plant.cn[i] = c_lock[i]


def _retract_chunk(state, plant, i, d, speed, gate, p_r, p_h, void, chunk_s, delivered, c_lock) -> None:
    f_band = float(plant.Fs[i]) - float(plant.f[i])
    values = retract_dead(state.retract_cfg, p_h, p_r, f_band, float(plant.sref[i]), void, state.A_h[i], state.A_ann[i], state.s_max,
                          state.L0r, state.L0h, state.beta, state.p_T)
    need = values["need"]
    rise = max(values["p_open"] - state.p_T, 0.0)
    level = min(state.x[i] / need, 1.0) if need > 0.0 else 0.0
    drain = state.K_n[i] * gate * math.sqrt(rise * level) / state.A_ann[i]
    if d == 0:
        state.x[i] = max(state.x[i] - drain * chunk_s, 0.0)
        state.is_open[i] = False
        _creep_step(state, plant, i, values, need)
        if state.x[i] == 0.0:
            if state.cfg.is_vent:
                state.line_dir[i] = 0
                state.charged[i] = False
            state.fill_start_t[i] = np.nan
        return
    state.line_dir[i] = -1
    if state.is_open[i]:
        if speed >= drain:
            delivered[i] = -(speed - drain)
            state.x[i] = need
            return
        state.is_open[i] = False
    if np.isnan(state.fill_start_t[i]):
        state.fill_start_t[i] = plant.t
    state.x[i] = max(state.x[i] + (speed - drain) * chunk_s, 0.0)
    if state.x[i] >= need:
        state.x[i] = need
        state.is_open[i] = True
        if not state.charged[i]:
            state.charged[i] = True
            state.n_fills[i, 1] += 1
            if len(state.fills) < MAX_LOGGED_FILLS:
                state.fills.append((round(float(state.fill_start_t[i]), 3), round(float(plant.t), 3), int(i), -1, round(float(need) * 1e3, 4),
                                    round(float(p_h) / 1e5, 2), round(float(p_r) / 1e5, 2), round(float(void) * 1e3, 3), 0.0))
            remaining = max(float(values["creep_ref"]) - float(state.crept[i]), 0.0)
            state.pending_shift_m[i] = float(values["discharge"]) + remaining
            state.discharge_mm[i] += float(values["discharge"]) * 1e3
            state.creep_mm[i] += remaining * 1e3
        state.fill_start_t[i] = np.nan
        state.crept[i] = 0.0
        return
    delivered[i] = 0.0
    state.hold_s[i, 1] += chunk_s
    state.lost_mm[i, 1] += speed * chunk_s * 1e3
    if c_lock is not None:
        plant.cn = np.array(plant.cn, float)
        plant.cn[i] = c_lock[i]
    _creep_step(state, plant, i, values, need)


def _creep_step(state: M1cState, plant, i: int, values: dict, need: float) -> None:
    if need <= 0.0:
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


def install(verdict_runs, cfg: M1cConfig | None, c_lock: np.ndarray | None) -> None:
    """Wrap ``verdict_runs.make_flow_plant_class``: M1c in front of the flow limiter; None leaves the bits alone."""
    original = verdict_runs.make_flow_plant_class

    def make_class(base, setting):
        flow_class = original(base, setting)

        class M1cPlant(flow_class):
            """Flow-limited harness plant with M1c (module docstring)."""

            def arm(self):
                LAST_PLANT[0] = self
                result = super().arm()
                if cfg is not None:
                    self.m1c = M1cState(cfg, self.flow_limiter.params, self)
                self.pr_log_t, self.pr_log = [], []
                return result

            def _rod_force(self, u):
                Gr = super()._rod_force(u)
                if cfg is None or not cfg.e2:
                    return Gr
                state = self.m1c
                dt = self.dt
                for i in range(4):
                    if self.locked[i] or u[i] <= EPS_M_S:  # extension only; the retract side keeps the fixed tau
                        state.e2_p_r[i] = np.nan
                        continue
                    if np.isnan(state.e2_p_r[i]):
                        state.e2_p_r[i] = self.p_r0[i] - self.r0[i] / self.A_ann[i]
                    c_r, c_l, c_h = state.compliances(self, i)
                    y = state.e2_p_r[i]
                    spool = float(state.u_cmd[i])  # the land follows the valve, not the delivered speed
                    q = state.K_land[i] * (spool / state.v_max) * math.sqrt(max(y - state.p_T, 0.0))
                    y = max(y + (self.A_ann[i] * spool - q) / (c_r + c_l + c_h) * dt, self.p_floor)
                    state.e2_p_r[i] = y
                    # the release takes the place of the fixed tau: the law's own value is overwritten
                    Gr[i] = (self.p_r0[i] - y) * self.A_ann[i]
                self.Gr = Gr
                return Gr

            def step(self, u, nsteps):
                if cfg is None:
                    accumulated = super().step(u, nsteps)
                else:
                    if not self.armed:
                        return super().step(u, nsteps)
                    state = self.m1c
                    delivered = filter_speeds(state, self, np.asarray(u, float), nsteps * self.dt, c_lock)
                    accumulated = super().step(delivered, nsteps)
                    if state.pending_shift_m.any():
                        self.sref -= state.pending_shift_m
                        state.pending_shift_m[:] = 0.0
                if self.armed:
                    self.pr_log_t.append(float(self.t))
                    self.pr_log.append(rod_pressure(self).tolist())
                return accumulated

        return M1cPlant

    verdict_runs.make_flow_plant_class = make_class
