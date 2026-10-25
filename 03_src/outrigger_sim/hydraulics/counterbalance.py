"""Counterbalance (CB) lock valve of the L2b legs: locked-volume over-pressure relief and the moving
rod-side pressure it regulates (engine independent, no pychrono).

Specification ``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 4 (hydraulics-expert,
2026-10-24), user decisions U-S8-H5 / H6 (2026-10-24): option ``actuator.lock_valve =
"counterbalance"`` with the ASSUMPTION parameters of ``actuator.counterbalance`` (4.4); the default
lock valve stays the pilot-operated check.

Locked over-pressure element (4.2), per leg and per side (head; rod when ``sides == "both"``),
only while the leg is locked (``|u| <= eps``):

    p_cr,eff = p_set - (psi - 1) p_T                 (neutral A, B -> T)
    y*       = max(p - p_cr,eff + dp_hys l, 0) / dp_ov
    y       <- y* + (y - y*) exp(-dt / tau)          (tau = 0: y = y*)
    Q        = Q_r y,   dV = Q dt

``p`` = head pressure ``(F_p + p_r A_ann) / A_p`` (pressure force, independent of the seal
friction) or the locked rod pressure. ``l`` = opening latch (1 while ``y > 0``). The head
discharge moves the oil reference (``s_ref -= dV / A_p`` with the head anchor shifted, rod side
unchanged: the CB check refills the rod side); the rod discharge lowers the rod lock pressure
(``p_r0 -= k_r dV / A_ann^2``, ``F_lock += k_r dV / A_ann``). Both act from the next step
(explicit). While the leg moves the element is off (``y = 0``; law C limits the moving pressure).

Moving rod-side pressure (4.3) replaces the POC target of the L1-R machine:

* extend (rod-side CB meters B, pilot = A ~ p_h): ``p_r = max(p_back, (p_set A_p - psi F_p) /
  (A_p + psi A_ann))``;
* retract (head CB meters A, pilot = B ~ p_r): ``p_r = (p_set A_p - F_p) / (psi A_p + A_ann)``;
* lock instant ``p_r0``: the same expression with the force at the lock instant.

Discharge ``"blocked_line"`` caps the cumulative discharge per side at
``blocked_line_capacity_m3`` (neutral A, B blocked: the line compresses only).

Units SI, gauge pressures; arrays per leg in the order given.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode

STATE_KEYS = (
    "y_head", "y_rod", "latch_head", "latch_rod", "shift_head_m", "volume_head_m3",
    "volume_rod_m3", "open_time_head_s", "open_time_rod_s", "open_count_head", "open_count_rod",
    "p_head_max_Pa", "p_rod_max_Pa", "dissipation_J",
)


@dataclasses.dataclass(frozen=True)
class CounterbalanceLegParams(RodChamberLegParams):
    """L1-R machine parameters whose moving rod-side target is the CB regulation (4.3)."""

    cb_p_set_Pa: float = math.nan
    cb_pilot_ratio: float = math.nan
    cb_back_pressure_Pa: float = math.nan

    def moving_target_rod_pressure_Pa(
        self, direction: RodChamberMode, cylinder_force_N: float
    ) -> float:
        return cb_rod_pressure_Pa(direction, cylinder_force_N, self.head_area_m2,
                                  self.annulus_area_m2, self.cb_p_set_Pa, self.cb_pilot_ratio,
                                  self.cb_back_pressure_Pa, self.floor_gauge_Pa, self.relief_Pa)


def cb_rod_pressure_Pa(direction: RodChamberMode, pressure_force_N: float, head_area_m2: float,
                       annulus_area_m2: float, p_set_Pa: float, pilot_ratio: float,
                       back_pressure_Pa: float, floor_gauge_Pa: float, relief_Pa: float) -> float:
    """Rod-side pressure regulated by the CB while moving / at the lock instant (4.3) [Pa g]."""
    a_p, a_r, psi = head_area_m2, annulus_area_m2, pilot_ratio
    if direction is RodChamberMode.EXT:
        value = max(back_pressure_Pa, (p_set_Pa * a_p - psi * pressure_force_N) / (a_p + psi * a_r))
    else:
        value = (p_set_Pa * a_p - pressure_force_N) / (psi * a_p + a_r)
    return float(min(max(value, floor_gauge_Pa), relief_Pa))


class Counterbalance:
    """Locked over-pressure element of all legs (module docstring).

    Args:
        params: :class:`outrigger_sim.params.CounterbalanceParams` (or an object with the same
            attributes).
        head_area_m2, annulus_area_m2: Per leg.
    """

    def __init__(self, params: Any, head_area_m2: ArrayLike, annulus_area_m2: ArrayLike) -> None:
        self.params = params
        self._a_p = np.array(head_area_m2, dtype=float).reshape(-1)
        self._n = self._a_p.size
        self._a_r = np.array(annulus_area_m2, dtype=float).reshape(self._n)
        p = params
        self.p_cr_eff_Pa = float(p.p_set_Pa - (p.pilot_ratio - 1.0) * p.tank_pressure_Pa)
        self.flow_gain_m3_s_Pa = float(p.rated_flow_m3_s / p.override_Pa)
        self.rod_side = p.sides == "both"
        self.capacity_m3 = (float(p.blocked_line_capacity_m3) if p.discharge == "blocked_line"
                            else math.inf)
        self.reset()

    @property
    def n_legs(self) -> int:
        return self._n

    # read-only views (names of chrono/s8_plant_adapter)
    @property
    def y(self) -> NDArray[np.float64]:
        """Head CB opening ``y`` (0 = closed, 1 = rated flow)."""
        return self.y_head.copy()

    @property
    def delta_cb_m(self) -> NDArray[np.float64]:
        """Cumulative head push-back ``delta_cb = sum dV / A_p`` [m]."""
        return self.shift_head_m.copy()

    @property
    def volume_m3(self) -> NDArray[np.float64]:
        """Cumulative discharged volume, head + rod [m^3]."""
        return self.volume_head_m3 + self.volume_rod_m3

    def reset(self) -> None:
        n = self._n
        self.y_head = np.zeros(n)
        self.y_rod = np.zeros(n)
        self.latch_head = np.zeros(n, dtype=bool)
        self.latch_rod = np.zeros(n, dtype=bool)
        self.shift_head_m = np.zeros(n)
        """Cumulative oil reference shift ``delta_cb = sum dV / A_p`` [m] (leg pushed in)."""
        self.volume_head_m3 = np.zeros(n)
        self.volume_rod_m3 = np.zeros(n)
        self.open_time_head_s = np.zeros(n)
        self.open_time_rod_s = np.zeros(n)
        self.open_count_head = np.zeros(n, dtype=np.int64)
        self.open_count_rod = np.zeros(n, dtype=np.int64)
        self.p_head_max_Pa = np.full(n, -np.inf)
        self.p_rod_max_Pa = np.full(n, -np.inf)
        self.dissipation_J = np.zeros(n)
        """``sum (p - p_T) dV`` per leg (V8(b) term)."""

    def _side(self, dt: float, locked: NDArray[np.bool_], p: NDArray[np.float64],
              y: NDArray[np.float64], latch: NDArray[np.bool_],
              used: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64],
                                                  NDArray[np.bool_]]:
        prm = self.params
        y_star = np.maximum(p - self.p_cr_eff_Pa + prm.hysteresis_Pa * latch, 0.0) / prm.override_Pa
        keep = math.exp(-dt / prm.tau_s) if prm.tau_s > 0.0 else 0.0
        y_new = np.where(locked, y_star + (y - y_star) * keep, 0.0)
        dv = self.flow_gain_m3_s_Pa * prm.override_Pa * y_new * dt
        dv = np.minimum(dv, np.maximum(self.capacity_m3 - used, 0.0))
        return y_new, dv, y_new > 0.0

    def step(self, dt_s: float, locked: ArrayLike, head_pressure_Pa: ArrayLike,
             rod_pressure_Pa: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Advance one step; returns the discharged volumes ``(dV_head, dV_rod)`` [m^3]."""
        dt = float(dt_s)
        lk = np.array(locked, dtype=bool).reshape(self._n)
        ph = np.array(head_pressure_Pa, dtype=float).reshape(self._n)
        pr = np.array(rod_pressure_Pa, dtype=float).reshape(self._n)
        self.p_head_max_Pa = np.where(lk, np.maximum(self.p_head_max_Pa, ph), self.p_head_max_Pa)
        self.p_rod_max_Pa = np.where(lk, np.maximum(self.p_rod_max_Pa, pr), self.p_rod_max_Pa)
        y_h, dv_h, open_h = self._side(dt, lk, ph, self.y_head, self.latch_head, self.volume_head_m3)
        self.open_count_head += open_h & ~self.latch_head
        self.y_head, self.latch_head = y_h, open_h
        self.open_time_head_s += open_h * dt
        self.volume_head_m3 += dv_h
        self.shift_head_m += dv_h / self._a_p
        self.dissipation_J += (ph - self.params.tank_pressure_Pa) * dv_h
        dv_r = np.zeros(self._n)
        if self.rod_side:
            y_r, dv_r, open_r = self._side(dt, lk, pr, self.y_rod, self.latch_rod,
                                           self.volume_rod_m3)
            self.open_count_rod += open_r & ~self.latch_rod
            self.y_rod, self.latch_rod = y_r, open_r
            self.open_time_rod_s += open_r * dt
            self.volume_rod_m3 += dv_r
            self.dissipation_J += (pr - self.params.tank_pressure_Pa) * dv_r
        return dv_h, dv_r

    # --- record / snapshot -------------------------------------------------------------------

    def record(self) -> dict[str, Any]:
        def fin(a: NDArray[np.float64]) -> list[float | None]:
            return [float(v) if math.isfinite(v) else None for v in a]

        return {
            "y_head": self.y_head.tolist(), "y_rod": self.y_rod.tolist(),
            "shift_head_m": self.shift_head_m.tolist(),
            "volume_head_m3": self.volume_head_m3.tolist(),
            "volume_rod_m3": self.volume_rod_m3.tolist(),
            "open_time_head_s": self.open_time_head_s.tolist(),
            "open_time_rod_s": self.open_time_rod_s.tolist(),
            "open_count_head": self.open_count_head.tolist(),
            "open_count_rod": self.open_count_rod.tolist(),
            "p_head_max_locked_Pa": fin(self.p_head_max_Pa),
            "p_rod_max_locked_Pa": fin(self.p_rod_max_Pa),
            "dissipation_J": self.dissipation_J.tolist(),
        }

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        return {
            "y_head": self.y_head.copy(), "y_rod": self.y_rod.copy(),
            "latch_head": self.latch_head.copy(), "latch_rod": self.latch_rod.copy(),
            "shift_head_m": self.shift_head_m.copy(), "volume_head_m3": self.volume_head_m3.copy(),
            "volume_rod_m3": self.volume_rod_m3.copy(),
            "open_time_head_s": self.open_time_head_s.copy(),
            "open_time_rod_s": self.open_time_rod_s.copy(),
            "open_count_head": self.open_count_head.copy(),
            "open_count_rod": self.open_count_rod.copy(),
            "p_head_max_Pa": self.p_head_max_Pa.copy(), "p_rod_max_Pa": self.p_rod_max_Pa.copy(),
            "dissipation_J": self.dissipation_J.copy(),
        }

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        missing = [k for k in STATE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"counterbalance state lacks {missing}")
        n = self._n
        for key in STATE_KEYS:
            dtype = (bool if key.startswith("latch") else np.int64 if "count" in key else float)
            setattr(self, key, np.array(arrays[key], dtype=dtype).reshape(n))

    def meta(self) -> dict[str, Any]:
        return {
            "model": "linear pressure-flow CB with first-order lag, locked legs only (S8 spec 4.2); "
                     "moving rod-side regulation 4.3",
            "params": {k: getattr(self.params, k) for k in (
                "p_set_Pa", "override_Pa", "rated_flow_m3_s", "tau_s", "hysteresis_Pa",
                "pilot_ratio", "tank_pressure_Pa", "back_pressure_Pa", "sides", "discharge",
                "blocked_line_capacity_m3")},
            "p_cr_eff_Pa": self.p_cr_eff_Pa,
            "flow_gain_m3_s_Pa": self.flow_gain_m3_s_Pa,
            "assumption": "all CB parameters ASSUMPTION (no manufacturer data, U-S8-H5)",
        }


__all__ = ["STATE_KEYS", "Counterbalance", "CounterbalanceLegParams", "cb_rod_pressure_Pa"]
