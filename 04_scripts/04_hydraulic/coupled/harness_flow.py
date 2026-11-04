"""Adapter: the shared-pump flow limit of ``outrigger_sim.hydraulics.flow_share`` on the harness.

It holds no controller or harness logic: :class:`FlowLimiter` maps a leg speed request and the net
oil force to the delivered leg speeds and records every 1 ms chunk; :func:`make_flow_plant_class`
puts it in front of any plant whose ``step(u, nsteps)`` integrates leg speeds. Without a limiter, or
before ``arm()``, the plant is the base class bit for bit.

Request and loads per chunk:
  u_i  mean valve output over the chunk (``_lagged_step`` passes it to ``plant.step``), the spool
       opening that draws the flow
  F_i  net oil force ``plant.pressure()`` at the chunk start; it holds the seal friction, which
       the head pressure has to overcome
  p_L  extending ``(F + A_r p_r) / A_h``, p_r = tank + B->T land drop; retracting p_pilot
       (hydraulic_coupling.md sec. 3, 6; same formula as ``replay_share.py``)

Pressures GAUGE [Pa], flows m3/s, speeds m/s, extension positive.
"""
from __future__ import annotations

import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from params import LEGS, Params, load_params

# ``-I`` puts no source folder on the path, and this module is imported before any harness module
SOURCE_DIR = Path(__file__).resolve().parents[3] / "03_src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from outrigger_sim.hydraulics.flow_share import (  # noqa: E402
    FlowCircuit,
    FlowShareAssumptions,
    FlowShareLaw,
    FlowShareResult,
    PumpFlowLimiter,
)

LAW_PRIORITY = FlowShareLaw.PRIORITY.value
LAW_PROPORTIONAL = FlowShareLaw.PROPORTIONAL.value
FAST_PATH_AUDIT_INTERVAL = 1000
"""Every n-th fast-path chunk is also solved by ``share`` and compared (counted in the record)."""
RESIDUAL_TIE_PA = 0.5e5
"""Criteria 7.3 E-4 (revision 3): spool drops within this of the minimum form one residual group."""
LEG_COUNT = len(LEGS)
INITIAL_ROWS = 4096

COLUMNS = (
    "t", *(f"u_{leg}" for leg in LEGS), *(f"v_{leg}" for leg in LEGS),
    *(f"oil_force_{leg}" for leg in LEGS), *(f"p_load_{leg}" for leg in LEGS),
    *(f"y_{leg}" for leg in LEGS), "p_P", "Q_byp", "Q_dem", "Q_sum", "limited_mask",
    "residual_mask", *(f"true_force_{leg}" for leg in LEGS), "crawler", "roll", "pitch",
)
"""One row per 1 ms chunk. The masks hold bit i for leg i. p_P, Q_byp and y are NaN on a
fast-path chunk (demand met, nothing solved)."""
COLUMN = {name: index for index, name in enumerate(COLUMNS)}


def _leg_slice(prefix: str) -> slice:
    start = COLUMN[f"{prefix}_{LEGS[0]}"]
    return slice(start, start + LEG_COUNT)


U, V, OIL_FORCE, P_LOAD, Y, TRUE_FORCE = (
    _leg_slice(name) for name in ("u", "v", "oil_force", "p_load", "y", "true_force"))


@dataclass(frozen=True)
class FlowSetting:
    """Pump and compensator values of one run (criteria 8.2, 8.3).

    Attributes:
        is_enabled: False = the leg speeds stay as requested; chunks are still recorded.
        eta_v: Pump volumetric efficiency.
        dp_comp_Pa, dp_unload_Pa, width_Pa, law: None = the nominal value of ``params.py``.
        always_solve: Skip the fast path, every chunk goes through the full solution.
    """

    is_enabled: bool = True
    eta_v: float = 0.95
    dp_comp_Pa: float | None = None
    dp_unload_Pa: float | None = None
    width_Pa: float | None = None
    law: str | None = None
    always_solve: bool = False

    def params(self) -> Params:
        """Parameters of ``params.py`` with this setting's non-nominal values."""
        nominal = load_params()
        return nominal.with_(
            flow_limit=self.is_enabled,
            dp_comp=nominal.dp_comp if self.dp_comp_Pa is None else self.dp_comp_Pa,
            dp_unl=nominal.dp_unl if self.dp_unload_Pa is None else self.dp_unload_Pa,
            width=nominal.width if self.width_Pa is None else self.width_Pa,
            law=nominal.law if self.law is None else self.law)

    def to_dict(self) -> dict:
        return asdict(self)


def pump_flow_limiter(setting: FlowSetting, params: Params) -> PumpFlowLimiter:
    """The ``03_src`` limiter with the values of ``params.py`` and this run's setting."""
    circuit = FlowCircuit(
        head_area_m2=params.A_h, annulus_area_m2=params.A_r, pump_flow_m3_s=params.Q_pump_th,
        max_speed_m_s=params.v_max, relief_pressure_Pa=params.p_relief)
    assumptions = FlowShareAssumptions(
        eta_v=setting.eta_v, is_enabled=setting.is_enabled, compensator_drop_Pa=params.dp_comp,
        unloading_drop_Pa=params.dp_unl, smoothing_width_Pa=params.width,
        law=FlowShareLaw(params.law), tank_pressure_Pa=params.p_T,
        pilot_pressure_Pa=params.p_pilot, back_land_ratio=params.bt_ratio,
        compensator_open_coefficient=params.X_comp,
        unloading_spring_coefficient=params.Cs_unl,
        unloading_flow_force_coefficient=params.Cf_unl,
        unloading_open_coefficient=params.X_unl)
    return PumpFlowLimiter(circuit, assumptions)


class FlowLimiter:
    """Delivered leg speeds of one run and their 1 ms record."""

    def __init__(self, setting: FlowSetting, params: Params | None = None) -> None:
        self.setting = setting
        self.params = setting.params() if params is None else params
        self.pump = pump_flow_limiter(setting, self.params)
        self.supply_m3_s = self.pump.supply_m3_s
        self._rows = np.empty((INITIAL_ROWS, len(COLUMNS)))
        self._count = 0
        self.fast_path_chunks = 0
        self.solved_chunks = 0
        self.audit_chunks = 0
        self.audit_mismatches = 0
        self.max_stroke_reading_m = 0.0

    # ------------------------------------------------------------------------------- the limit
    def limit(self, t_s: float, u: np.ndarray, oil_force_N: np.ndarray) -> np.ndarray:
        """Delivered leg speeds for one chunk; records the chunk."""
        u = np.asarray(u, float)
        oil_force_N = np.asarray(oil_force_N, float)
        p_load = self.pump.load_pressures_Pa(u, oil_force_N)
        if not self.setting.is_enabled:
            return self._record_unsolved(t_s, u, u.copy(), oil_force_N, p_load)
        if not self.setting.always_solve and self.pump.is_demand_met_with_margin(u, p_load):
            self.fast_path_chunks += 1
            if self.fast_path_chunks % FAST_PATH_AUDIT_INTERVAL == 0:
                self._audit_fast_path(u, p_load)
            return self._record_unsolved(t_s, u, u.copy(), oil_force_N, p_load)
        self.solved_chunks += 1
        return self._record_solved(t_s, u, oil_force_N, p_load, self.pump.solve(u, p_load))

    def _audit_fast_path(self, u: np.ndarray, p_load: np.ndarray) -> None:
        self.audit_chunks += 1
        if not np.array_equal(self.pump.solve(u, p_load).speed_m_s, u):
            self.audit_mismatches += 1

    # --------------------------------------------------------------------------------- record
    def _new_row(self) -> np.ndarray:
        if self._count == len(self._rows):
            self._rows = np.concatenate([self._rows, np.empty_like(self._rows)])
        row = self._rows[self._count]
        self._count += 1
        return row

    def _record_unsolved(self, t_s, u, v, oil_force_N, p_load) -> np.ndarray:
        demand = self.pump.demand_m3_s(u)
        row = self._new_row()
        row[:] = math.nan
        row[0] = t_s
        row[U], row[V], row[OIL_FORCE], row[P_LOAD] = u, v, oil_force_N, p_load
        row[COLUMN["Q_dem"]] = row[COLUMN["Q_sum"]] = demand
        row[COLUMN["limited_mask"]] = row[COLUMN["residual_mask"]] = 0
        return v

    def _record_solved(self, t_s, u, oil_force_N, p_load, result: FlowShareResult) -> np.ndarray:
        row = self._new_row()
        row[:] = math.nan
        row[0] = t_s
        row[U], row[V], row[OIL_FORCE], row[P_LOAD] = u, result.speed_m_s, oil_force_N, p_load
        row[Y] = result.spool_drop_Pa
        row[COLUMN["p_P"]] = result.gallery_pressure_Pa
        row[COLUMN["Q_byp"]] = result.bypass_flow_m3_s
        row[COLUMN["Q_dem"]] = result.demand_m3_s
        row[COLUMN["Q_sum"]] = float(result.flow_m3_s.sum())
        row[COLUMN["limited_mask"]] = _leg_mask(result.is_limited)
        row[COLUMN["residual_mask"]] = _residual_mask(result.is_limited, result.spool_drop_Pa)
        return result.speed_m_s

    def record_plant_state(self, plant, accumulated: np.ndarray) -> None:
        """True cylinder force, crawler force and attitude after the chunk (same row)."""
        row = self._rows[self._count - 1]
        row[TRUE_FORCE] = np.asarray(accumulated[11:15], float) - plant.Wr
        row[COLUMN["crawler"]] = float(accumulated[15])
        row[COLUMN["roll"]], row[COLUMN["pitch"]] = plant.attitude()
        self.max_stroke_reading_m = max(self.max_stroke_reading_m, float(np.max(plant.sref)))

    def rows(self) -> np.ndarray:
        """All recorded chunks, ``COLUMNS`` order."""
        return self._rows[: self._count].copy()

    def counters(self) -> dict:
        return {"fast_path_chunks": self.fast_path_chunks, "solved_chunks": self.solved_chunks,
                "audit_chunks": self.audit_chunks, "audit_mismatches": self.audit_mismatches}


def _leg_mask(flags: np.ndarray) -> int:
    return int(sum(1 << i for i in range(LEG_COUNT) if flags[i]))


def _residual_mask(limited: np.ndarray, spool_drop_Pa: np.ndarray) -> int:
    """Criteria 7.3 E-4: limited legs whose spool drop is within 0.5 bar of the lowest."""
    if not limited.any():
        return 0
    lowest = float(spool_drop_Pa[limited].min())
    return _leg_mask(limited & (spool_drop_Pa <= lowest + RESIDUAL_TIE_PA))


def make_flow_plant_class(base: type, setting: FlowSetting) -> type:
    """Subclass of ``base`` with a :class:`FlowLimiter` in front of ``step`` once armed.

    The limiter comes from ``__init__`` so that a plant built inside a harness needs no extra
    call. ``deepcopy`` of a plant copies its limiter and record, as the event branches expect.
    """

    class FlowLimitedPlant(base):
        """``base`` plant with the shared-pump flow limit (module docstring)."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.flow_limiter = FlowLimiter(setting)

        def step(self, u, nsteps):
            if not self.armed:
                return super().step(u, nsteps)
            limiter = self.flow_limiter
            delivered = limiter.limit(self.t, u, self.pressure())
            accumulated = super().step(delivered, nsteps)
            limiter.record_plant_state(self, accumulated)
            return accumulated

    return FlowLimitedPlant
