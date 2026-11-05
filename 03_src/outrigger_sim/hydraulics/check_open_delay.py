"""M1c: check valve opening delay of a starting leg (engine independent, no pychrono).

``00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`` 2.4. A port of
``04_scripts/03_control/m1_check/m1c_plant.py`` and ``m1b_plant.retract_dead`` (circuits VN and BL),
**the formulas unchanged**. The units missed their criteria: every result of this model is reference
data (``UNIT_STATUS``); the fix waits for the manufacturer answers (V-5, V-6). Left out on
purpose: circuit VR and its paths, E2 (rod law after release), E4 (self opening), ``no_delay``,
``rod_early``.

Extend (E1), line state ``x`` in stroke units::

    x' = |u| - K_n g sqrt(p_A - p_T) / A_h,  g = (1 - |u| / (c_v v_max))+,
    p_A = p_T + x A_h beta_h / V_line
    rod check opens:  p_T + psi (p_A - p_ref) - p_r - p_cr > 0   (p_ref = p_T for VN, 0 for BL)
    head check opens: p_A + psi p_B - p_h - p_cr > 0

Retract: the dead stroke of :func:`retract_dead`; the reference creeps back while the line fills and
drops by the head discharge at the opening (after that chunk).

All valve values are ASSUMPTIONS (:class:`CheckValveValues`). Pressures gauge [Pa], speeds m/s,
extension positive, arrays per leg.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .v5_options import CheckCircuit, CheckDelaySetting

UNIT_STATUS = "below_criteria_reference_only"
"""Spec 2.4: the M1c units missed their criteria (``unit_m1c.json``); meta and tables carry it."""
EPS_M_S = 1.0e-6
RELEASE_SPEED_M_S = 1.5 * EPS_M_S
"""Delivered speed with the rod check open and the head check shut: the rod law releases."""
MAX_LOGGED_FILLS = 600


@dataclass(frozen=True)
class CheckValveValues:
    """Line and pilot-check values (all ASSUMPTION: Q-M9, V-6)."""

    v_line_m3: float = 285e-6
    beta_hose_Pa: float = 0.5e9
    psi: float = 3.5
    p_crack_Pa: float = 3e5
    neutral_fraction: float = 0.05


@dataclass(frozen=True)
class CheckDelayCircuit:
    """Cylinder and valve values the model needs (YAML and flow-share assumptions)."""

    head_area_m2: NDArray[np.float64]
    annulus_area_m2: NDArray[np.float64]
    stroke_m: float
    rod_dead_length_m: float
    head_dead_length_m: float
    bulk_modulus_Pa: float
    tank_pressure_Pa: float
    max_speed_m_s: float
    compensator_drop_Pa: float


@dataclass(frozen=True)
class RetractConfig:
    """The ``m1b_plant.M1bConfig`` fields that :func:`retract_dead` reads."""

    rod_forward: bool
    volume_scale: float
    v_line_m3: float
    beta_hose_Pa: float
    psi: float
    p_crack_Pa: float


def retract_dead(cfg: RetractConfig, p_h, p_r, F_band, s, void_m, A_h, A_ann, s_max, L0r, L0h,
                 beta, p_T, delta=None) -> dict:
    """Retract dead stroke and its parts for one leg (scalars) [m], pressures [Pa].

    ``m1b_plant.retract_dead`` unchanged; ``p_rod`` (the rod pressure at the opening) is added to
    the result for the M2 seed (spec 2.4).
    """
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
    return {"need": volume / A_ann + void_m, "p_open": p_b, "dp_h": dp_h, "creep_ref": creep_ref,
            "creep_start": start, "discharge": discharge, "p_rod": p_rod}


def p_a_of_x(values: CheckValveValues, volume_scale: float, x: float, A_h: float,
             p_T: float) -> float:
    return p_T + x * A_h * values.beta_hose_Pa / (values.v_line_m3 * volume_scale)


def rod_opens(values: CheckValveValues, is_vent_ref: bool, p_a: float, p_r: float, p_b: float,
              p_T: float) -> bool:
    """Opening law of the rod check."""
    p_ref = p_T if is_vent_ref else 0.0
    return p_b + values.psi * (p_a - p_ref) - p_r - values.p_crack_Pa > 0.0


def p_b_equalized(p_r: float, p_T: float, c_r: float, c_l: float) -> float:
    return (c_r * p_r + c_l * p_T) / (c_r + c_l)


def head_opens(values: CheckValveValues, p_a: float, p_b: float, p_h: float) -> bool:
    return p_a + values.psi * p_b - p_h - values.p_crack_Pa > 0.0


def drain_speed(K_n: float, gate: float, p_a: float, p_T: float, A_h: float) -> float:
    return K_n * gate * math.sqrt(max(p_a - p_T, 0.0)) / A_h


@dataclass
class CheckDelayInputs:
    """Plant state of one step or chunk (spec 2.4 common inputs).

    Attributes:
        t_s, dt_s: Time and length of the step.
        u_m_s: Requested leg speed (after the valve).
        p_h, p_r: Head and rod pressure (gauge, no pressure floor).
        locked: Rod-side law locked per leg.
        void_m: Oil the floor-limited rod spring did not get, ``(c - c_lock - knee)+``.
        band_N: Friction band left in the retract direction, ``F_s - f``.
        s_ref_m: Oil reference per leg.
    """

    t_s: float
    dt_s: float
    u_m_s: NDArray[np.float64]
    p_h: NDArray[np.float64]
    p_r: NDArray[np.float64]
    locked: NDArray[np.bool_]
    void_m: NDArray[np.float64]
    band_N: NDArray[np.float64]
    s_ref_m: NDArray[np.float64]


@dataclass
class CheckDelayOutput:
    """What the plant does with one step.

    Attributes:
        speed_m_s: Delivered leg speeds.
        creep_shift_m: Lower ``s_ref`` by this now (and the anchor of a locked leg).
        opening_shift_m: Lower ``s_ref`` by this after the step (head discharge at a retract
            opening plus the creep still missing).
        lock_damping: Legs held by the delay: locked dashpot.
        opening_rod_pressure_Pa: Rod pressure at a retract opening (M2 seed); NaN elsewhere.
    """

    speed_m_s: NDArray[np.float64]
    creep_shift_m: NDArray[np.float64]
    opening_shift_m: NDArray[np.float64]
    lock_damping: NDArray[np.bool_]
    opening_rod_pressure_Pa: NDArray[np.float64] = field(default_factory=lambda: np.full(4, np.nan))


class CheckOpenDelay:
    """M1c state of one plant (deep-copied with the event branches).

    Args:
        setting: Circuit, volume scale and ``c_v``.
        circuit: Cylinder and valve values.
        values: Line and check values.
    """

    def __init__(self, setting: CheckDelaySetting, circuit: CheckDelayCircuit,
                 values: CheckValveValues | None = None) -> None:
        self.setting = setting
        self.values = CheckValveValues() if values is None else values
        self.circuit = circuit
        self.is_vent = setting.kind == CheckCircuit.VENT_NO_REFILL.value
        self.retract_cfg = RetractConfig(
            rod_forward=self.is_vent, volume_scale=setting.volume_scale,
            v_line_m3=self.values.v_line_m3, beta_hose_Pa=self.values.beta_hose_Pa,
            psi=self.values.psi, p_crack_Pa=self.values.p_crack_Pa)
        self.A_h = np.asarray(circuit.head_area_m2, float)
        self.A_ann = np.asarray(circuit.annulus_area_m2, float)
        self.s_max = float(circuit.stroke_m)
        self.L0r = float(circuit.rod_dead_length_m)
        self.L0h = float(circuit.head_dead_length_m)
        self.beta = float(circuit.bulk_modulus_Pa)
        self.p_T = float(circuit.tank_pressure_Pa)
        self.v_max = float(circuit.max_speed_m_s)
        self.K_land = self.A_h * self.v_max / math.sqrt(float(circuit.compensator_drop_Pa))
        self.K_n = (self.values.neutral_fraction if self.is_vent else 0.0) * self.K_land
        n = len(self.A_h)
        self.x = np.zeros(n)
        self.line_dir = np.zeros(n, int)
        self.is_open = np.zeros(n, bool)
        self.charged = np.zeros(n, bool)
        self.crept = np.zeros(n)
        self.fill_start_t = np.full(n, np.nan)
        self.rod_released = np.zeros(n, bool)
        self.p_b_after = np.full(n, np.nan)
        self.hold_s = np.zeros((n, 2))
        self.lost_mm = np.zeros((n, 2))
        self.n_fills = np.zeros((n, 2), int)
        self.discharge_mm = np.zeros(n)
        self.creep_mm = np.zeros(n)
        self.void_peak_mm = np.zeros(n)
        self.fills: list = []
        self.ext_starts: list = []

    # --- per step ------------------------------------------------------------------------------
    def compliances(self, s_ref_m: float, i: int) -> tuple[float, float]:
        c_r = self.A_ann[i] * (self.L0r + self.s_max - s_ref_m) / self.beta
        c_l = self.values.v_line_m3 * self.setting.volume_scale / self.values.beta_hose_Pa
        return c_r, c_l

    def filter(self, inputs: CheckDelayInputs) -> CheckDelayOutput:
        """Delivered speeds of one step; advances the state (``m1c_plant.filter_speeds``)."""
        u = np.asarray(inputs.u_m_s, float)
        n = len(u)
        out = CheckDelayOutput(u.copy(), np.zeros(n), np.zeros(n), np.zeros(n, bool),
                               np.full(n, np.nan))
        speed = np.abs(u)
        direction = np.where(speed > EPS_M_S, np.sign(u).astype(int), 0)
        for i in range(n):
            void = float(inputs.void_m[i])
            self.void_peak_mm[i] = max(self.void_peak_mm[i], void * 1e3)
            d = int(direction[i])
            if d != 0 and self.line_dir[i] not in (0, d):  # a direction change empties the line
                self._empty_line(i)
            active = d if d != 0 else int(self.line_dir[i])
            if inputs.locked[i] and d == 0:
                self.rod_released[i] = False
                self.p_b_after[i] = np.nan
            if active == 0:
                continue
            gate = max(1.0 - speed[i] / (self.setting.c_v * self.v_max), 0.0)
            if active > 0:
                self._extend_step(inputs, out, i, d, speed[i], gate)
            else:
                self._retract_step(inputs, out, i, d, speed[i], gate, void)
        return out

    def _empty_line(self, i: int) -> None:
        self.x[i] = 0.0
        self.is_open[i] = False
        self.charged[i] = False
        self.line_dir[i] = 0
        self.crept[i] = 0.0
        self.rod_released[i] = False
        self.p_b_after[i] = np.nan

    def _extend_step(self, inputs, out, i, d, speed, gate) -> None:
        values, scale = self.values, self.setting.volume_scale
        A_h = self.A_h[i]
        p_r, p_h = inputs.p_r[i], inputs.p_h[i]
        p_a = p_a_of_x(values, scale, self.x[i], A_h, self.p_T)
        drain = drain_speed(self.K_n[i], gate, p_a, self.p_T, A_h)
        if d == 0:  # no flow in: the line bleeds down, the head check is shut
            self.x[i] = max(self.x[i] - drain * inputs.dt_s, 0.0)
            self.is_open[i] = False
            if self.x[i] == 0.0 and self.is_vent:
                self.line_dir[i] = 0
                self.charged[i] = False
            return
        if (self.x[i] == 0.0 and not self.is_open[i] and not self.charged[i]
                and len(self.ext_starts) < MAX_LOGGED_FILLS):
            self.ext_starts.append((round(float(inputs.t_s), 3), int(i), round(float(p_h) / 1e5, 2),
                                    round(float(p_r) / 1e5, 2), round(float(speed) * 1e3, 3)))
        self.line_dir[i] = 1
        self.x[i] = max(self.x[i] + (speed - drain) * inputs.dt_s, 0.0)
        p_a = p_a_of_x(values, scale, self.x[i], A_h, self.p_T)
        if not self.rod_released[i] and rod_opens(values, self.is_vent, p_a, p_r, self.p_T,
                                                   self.p_T):
            self.rod_released[i] = True
            c_r, c_l = self.compliances(float(inputs.s_ref_m[i]), i)
            self.p_b_after[i] = p_b_equalized(p_r, self.p_T, c_r, c_l)
        if self.rod_released[i]:
            p_b = p_r if np.isnan(self.p_b_after[i]) else min(self.p_b_after[i], p_r)
        else:
            p_b = self.p_T
        if self.rod_released[i] and head_opens(values, p_a, p_b, p_h):
            if not self.charged[i]:
                self.charged[i] = True
                self.n_fills[i, 0] += 1
                if len(self.fills) < MAX_LOGGED_FILLS:
                    start = inputs.t_s if np.isnan(self.fill_start_t[i]) else self.fill_start_t[i]
                    self.fills.append((round(float(start), 3), round(float(inputs.t_s), 3), int(i),
                                       1, round(float(self.x[i]) * 1e3, 4),
                                       round(float(p_h) / 1e5, 2), round(float(p_r) / 1e5, 2),
                                       round(float(p_a) / 1e5, 2), round(float(p_b) / 1e5, 2)))
                self.fill_start_t[i] = np.nan
            self.is_open[i] = True
            # the line stays at the opening pressure while the flow passes the check
            out.speed_m_s[i] = max(speed - drain, RELEASE_SPEED_M_S)
            target = ((p_h + values.p_crack_Pa - values.psi * p_b - self.p_T)
                      * (values.v_line_m3 * scale) / (A_h * values.beta_hose_Pa))
            self.x[i] = max(target, 0.0)
            return
        self.is_open[i] = False
        if np.isnan(self.fill_start_t[i]):
            self.fill_start_t[i] = inputs.t_s
        out.speed_m_s[i] = RELEASE_SPEED_M_S if self.rod_released[i] else 0.0
        self.hold_s[i, 0] += inputs.dt_s
        self.lost_mm[i, 0] += speed * inputs.dt_s * 1e3
        out.lock_damping[i] = True

    def _retract_step(self, inputs, out, i, d, speed, gate, void) -> None:
        values = retract_dead(self.retract_cfg, inputs.p_h[i], inputs.p_r[i],
                              float(inputs.band_N[i]), float(inputs.s_ref_m[i]), void, self.A_h[i],
                              self.A_ann[i], self.s_max, self.L0r, self.L0h, self.beta, self.p_T)
        need = values["need"]
        rise = max(values["p_open"] - self.p_T, 0.0)
        level = min(self.x[i] / need, 1.0) if need > 0.0 else 0.0
        drain = self.K_n[i] * gate * math.sqrt(rise * level) / self.A_ann[i]
        if d == 0:
            self.x[i] = max(self.x[i] - drain * inputs.dt_s, 0.0)
            self.is_open[i] = False
            self._creep(out, i, values, need)
            if self.x[i] == 0.0:
                if self.is_vent:
                    self.line_dir[i] = 0
                    self.charged[i] = False
                self.fill_start_t[i] = np.nan
            return
        self.line_dir[i] = -1
        if self.is_open[i]:
            if speed >= drain:
                out.speed_m_s[i] = -(speed - drain)
                self.x[i] = need
                return
            self.is_open[i] = False
        if np.isnan(self.fill_start_t[i]):
            self.fill_start_t[i] = inputs.t_s
        self.x[i] = max(self.x[i] + (speed - drain) * inputs.dt_s, 0.0)
        if self.x[i] >= need:
            self.x[i] = need
            self.is_open[i] = True
            if not self.charged[i]:
                self.charged[i] = True
                self.n_fills[i, 1] += 1
                if len(self.fills) < MAX_LOGGED_FILLS:
                    self.fills.append((round(float(self.fill_start_t[i]), 3),
                                       round(float(inputs.t_s), 3), int(i), -1,
                                       round(float(need) * 1e3, 4),
                                       round(float(inputs.p_h[i]) / 1e5, 2),
                                       round(float(inputs.p_r[i]) / 1e5, 2),
                                       round(float(void) * 1e3, 3), 0.0))
                remaining = max(float(values["creep_ref"]) - float(self.crept[i]), 0.0)
                out.opening_shift_m[i] = float(values["discharge"]) + remaining
                out.opening_rod_pressure_Pa[i] = float(values["p_rod"])
                self.discharge_mm[i] += float(values["discharge"]) * 1e3
                self.creep_mm[i] += remaining * 1e3
            self.fill_start_t[i] = np.nan
            self.crept[i] = 0.0
            return
        out.speed_m_s[i] = 0.0
        self.hold_s[i, 1] += inputs.dt_s
        self.lost_mm[i, 1] += speed * inputs.dt_s * 1e3
        out.lock_damping[i] = True
        self._creep(out, i, values, need)

    def _creep(self, out: CheckDelayOutput, i: int, values: dict, need: float) -> None:
        """Reference creep of a retract fill with the fill level, reversible while it bleeds."""
        if need <= 0.0:
            return
        start = float(values["creep_start"])
        progress = 0.0 if start >= 1.0 else max(self.x[i] / need - start, 0.0) / (1.0 - start)
        target = float(values["creep_ref"]) * min(progress, 1.0)
        step = target - self.crept[i]
        if step != 0.0:
            out.creep_shift_m[i] = step
            self.crept[i] = target
            self.creep_mm[i] += step * 1e3

    # --- record --------------------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        return {"unit_status": UNIT_STATUS, "setting": {"kind": self.setting.kind,
                                                         "volume_scale": self.setting.volume_scale,
                                                         "c_v": self.setting.c_v},
                "n_fills": self.n_fills.tolist(), "hold_s": np.round(self.hold_s, 3).tolist(),
                "lost_mm": np.round(self.lost_mm, 4).tolist(),
                "discharge_mm": np.round(self.discharge_mm, 4).tolist(),
                "creep_mm": np.round(self.creep_mm, 4).tolist(),
                "void_peak_mm": np.round(self.void_peak_mm, 3).tolist(),
                "fills": self.fills[:MAX_LOGGED_FILLS], "ext_starts": self.ext_starts}

    def meta(self) -> dict[str, Any]:
        return {"unit_status": UNIT_STATUS, "kind": self.setting.kind,
                "volume_scale": self.setting.volume_scale, "c_v": self.setting.c_v,
                "values": {"v_line_m3": self.values.v_line_m3,
                           "beta_hose_Pa": self.values.beta_hose_Pa, "psi": self.values.psi,
                           "p_crack_Pa": self.values.p_crack_Pa,
                           "neutral_fraction": self.values.neutral_fraction},
                "status": "ASSUMPTION (Q-M9, V-6); port of m1c_plant VN / BL, VR E2 E4 left out"}


__all__ = ["UNIT_STATUS", "CheckDelayCircuit", "CheckDelayInputs", "CheckDelayOutput",
           "CheckOpenDelay", "CheckValveValues", "RetractConfig", "retract_dead"]
