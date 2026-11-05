"""Shared-pump flow limit of a closed-loop plant run: setting, per-step limit and record.

Engine independent (no pychrono). :class:`RecordedFlowLimiter` sits between the valve output and the
leg speed of ``SpeedReference`` / ``L1SpeedActuator`` (``set_flow_limit``), called once per physics
step. It holds no state that changes the result; the record is for the coupled re-judgement
(``hydraulic_coupling_criteria.md`` 7.3, 9, 9.1). **Off by default**: without a limiter on the
actuator no line of this module runs (criteria 9 step 1; D-5 not switched, S8 F-5, decision_log
2026-11-05).

Per step (``flow_share`` module docstring, conditions 1 to 3):
  request  speed after the valve (spool lag step mean, or the command ramp on a plant without the
           valve model), the opening that draws the flow
  force    pressure force of the step just taken: ``F`` (L1, L2b without friction), ``F - f`` (L2b
           friction path, ``seal_friction``: ``F = G + f``, ``f`` + towards extension, so a sliding
           extending leg has ``F - f = F + F_s``: the head pressure also overcomes the seal)

Record ``flow_series.npz``: ``rows`` (one row per ``record_period_s``, instantaneous values of the
first physics step at or after the sample time), ``columns`` (:data:`COLUMNS`, the first columns are
the 1 ms layout of ``04_scripts/04_hydraulic/coupled/harness_flow.COLUMNS``; ``true_force_*``,
``crawler``, ``roll``, ``pitch`` are NaN here because the run record ``record/record.npz`` holds
them at 10 Hz), ``supply_m3_s``, ``setting_json``. ``p_P``, ``Q_byp``, ``y_*`` are NaN on a fast-path
step (demand met, nothing solved). The exact per-step counters are in :meth:`RecordedFlowLimiter.summary`.

Units: pressures gauge [Pa] in the rows, bar in the summary; flows m^3/s in the rows, L/min in the
summary; speeds m/s, extension positive; arrays in ``LEG_ORDER``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..params import LEG_ORDER, Params
from .flow_share import (
    SUPPLY_REL_TOL,
    FlowCircuit,
    FlowShareAssumptions,
    FlowShareLaw,
    PumpFlowLimiter,
    flow_circuit_from_params,
)

FLOW_SERIES_NAME = "flow_series.npz"
PA_PER_BAR = 1.0e5
L_MIN_PER_M3_S = 6.0e4
MM_PER_M = 1.0e3
DEFAULT_RECORD_PERIOD_S = 1.0e-3
FAST_PATH_AUDIT_INTERVAL = 1000
"""Every n-th fast-path step is also solved and compared (``audit_*`` in the summary)."""
RESIDUAL_TIE_PA = 0.5e5
"""Criteria 7.3 E-4 (revision 3): spool drops within this of the lowest form one residual group."""
SPEED_RATIO_WINDOW_S = 1.0
SPEED_RATIO_MIN_REQUEST = 0.1
"""Criteria sec. 1: ``r_i`` only where the 1 s mean request is at least 0.1 v_max."""
SPEED_RATIO_FLAG = 0.93
"""Criteria 7.3 E-2."""
SAMPLE_TIME_TOL_S = 1.0e-9
INITIAL_ROWS = 4096
LEG_COUNT = len(LEG_ORDER)


def _leg_columns(prefix: str) -> tuple[str, ...]:
    return tuple(f"{prefix}_{leg}" for leg in LEG_ORDER)


COLUMNS: tuple[str, ...] = (
    "t", *_leg_columns("u"), *_leg_columns("v"), *_leg_columns("oil_force"),
    *_leg_columns("p_load"), *_leg_columns("y"), "p_P", "Q_byp", "Q_dem", "Q_sum", "limited_mask",
    "residual_mask", *_leg_columns("true_force"), "crawler", "roll", "pitch",
    *_leg_columns("deficit_integral"),
)
"""Row layout (module docstring). The masks hold bit i for leg i; ``deficit_integral_*`` = the
integral of ``(u - v) dt`` over every physics step so far [m]."""
COLUMN = {name: index for index, name in enumerate(COLUMNS)}


def _leg_slice(prefix: str) -> slice:
    first = COLUMN[f"{prefix}_{LEG_ORDER[0]}"]
    return slice(first, first + LEG_COUNT)


U, V, OIL_FORCE, P_LOAD, Y, DEFICIT = (
    _leg_slice(name) for name in ("u", "v", "oil_force", "p_load", "y", "deficit_integral"))


@dataclass(frozen=True)
class FlowLimitSetting:
    """Pump and compensator values of one run (criteria 8.2, 8.3; all ASSUMPTION, Q-M1, Q-M4, Q-M5).

    The defaults are the nominal compensator values of criteria 8.3. ``eta_v`` has no default: a run
    with a setting has chosen its level (0.95 is the design point, criteria 3).
    """

    eta_v: float
    compensator_drop_bar: float = 10.0
    unloading_drop_bar: float = 20.0
    smoothing_width_bar: float = 1.0
    law: str = FlowShareLaw.PRIORITY.value
    record_period_s: float = DEFAULT_RECORD_PERIOD_S

    def assumptions(self) -> FlowShareAssumptions:
        """The enabled ``flow_share`` assumptions of this setting; other values stay nominal."""
        return FlowShareAssumptions(
            eta_v=float(self.eta_v), is_enabled=True,
            compensator_drop_Pa=float(self.compensator_drop_bar) * PA_PER_BAR,
            unloading_drop_Pa=float(self.unloading_drop_bar) * PA_PER_BAR,
            smoothing_width_Pa=float(self.smoothing_width_bar) * PA_PER_BAR,
            law=FlowShareLaw(self.law))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> FlowLimitSetting:
        return cls(**values)


def add_flow_limit_arguments(parser: argparse.ArgumentParser) -> None:
    """CLI options of the limit. Absent stays absent (``argparse.SUPPRESS``), so a run without them
    keeps its ``vars(args)``, its meta and its result unchanged."""
    group = parser.add_argument_group("shared-pump flow limit (default off, criteria 9)")
    group.add_argument("--flow-eta-v", dest="flow_eta_v", type=float, default=argparse.SUPPRESS,
                       help="turn the limit on at this pump volumetric efficiency (criteria 8.2)")
    group.add_argument("--flow-dp-comp-bar", dest="flow_dp_comp_bar", type=float,
                       default=argparse.SUPPRESS, help="section compensator drop [bar], nominal 10")
    group.add_argument("--flow-dp-unload-bar", dest="flow_dp_unload_bar", type=float,
                       default=argparse.SUPPRESS, help="LS standby drop [bar], nominal 20")
    group.add_argument("--flow-width-bar", dest="flow_width_bar", type=float,
                       default=argparse.SUPPRESS, help="compensator transition width [bar], nominal 1")
    group.add_argument("--flow-law", dest="flow_law", choices=[law.value for law in FlowShareLaw],
                       default=argparse.SUPPRESS, help="division of a short supply, nominal priority")
    group.add_argument("--flow-record-s", dest="flow_record_s", type=float,
                       default=argparse.SUPPRESS, help="flow_series.npz row period [s], nominal 1e-3")


def flow_setting_from_args(args: argparse.Namespace) -> FlowLimitSetting | None:
    """The setting of the options of :func:`add_flow_limit_arguments`; None = limit off.

    Raises:
        SystemExit: A compensator option without ``--flow-eta-v``.
    """
    given = {key: getattr(args, key) for key in ("flow_dp_comp_bar", "flow_dp_unload_bar",
                                                 "flow_width_bar", "flow_law", "flow_record_s")
             if hasattr(args, key)}
    if not hasattr(args, "flow_eta_v"):
        if given:
            raise SystemExit(f"{sorted(given)} need --flow-eta-v (the limit is off without it)")
        return None
    defaults = FlowLimitSetting(eta_v=args.flow_eta_v)
    return FlowLimitSetting(
        eta_v=args.flow_eta_v,
        compensator_drop_bar=given.get("flow_dp_comp_bar", defaults.compensator_drop_bar),
        unloading_drop_bar=given.get("flow_dp_unload_bar", defaults.unloading_drop_bar),
        smoothing_width_bar=given.get("flow_width_bar", defaults.smoothing_width_bar),
        law=given.get("flow_law", defaults.law),
        record_period_s=given.get("flow_record_s", defaults.record_period_s))


def _leg_mask(flags: NDArray[np.bool_]) -> int:
    return int(sum(1 << i for i in range(LEG_COUNT) if flags[i]))


def _mask_name(mask: int) -> str:
    return "+".join(leg for i, leg in enumerate(LEG_ORDER) if mask >> i & 1)


def _residual_mask(limited: NDArray[np.bool_], spool_drop_Pa: NDArray[np.float64]) -> int:
    if not limited.any():
        return 0
    lowest = float(spool_drop_Pa[limited].min())
    return _leg_mask(limited & (spool_drop_Pa <= lowest + RESIDUAL_TIE_PA))


def _contiguous_runs(flags: NDArray[np.bool_]) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    edges = np.diff(np.concatenate(([0], flags.astype(int), [0])))
    return np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1


def _longest_run(flags: NDArray[np.bool_]) -> int:
    first, last = _contiguous_runs(flags)
    return int((last - first + 1).max()) if first.size else 0


def _rounded(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(float(value), digits)


class RecordedFlowLimiter:
    """Delivered leg speeds per physics step and their record (module docstring).

    The limiter is not part of the actuator snapshots: a restored actuator needs
    ``set_flow_limit`` again, and the record covers what this object saw.

    Args:
        circuit: Known circuit values (normally :func:`flow_circuit_from_params`).
        setting: Pump and compensator values.
    """

    def __init__(self, circuit: FlowCircuit, setting: FlowLimitSetting) -> None:
        self.circuit = circuit
        self.setting = setting
        self.pump = PumpFlowLimiter(circuit, setting.assumptions())
        self.supply_m3_s = self.pump.supply_m3_s
        self._period = float(setting.record_period_s)
        if not self._period > 0.0:
            raise ValueError(f"record period must be > 0: {self._period!r}")
        self._next_row_s = -np.inf
        self._rows = np.empty((INITIAL_ROWS, len(COLUMNS)))
        self._count = 0
        self._deficit_integral_m = np.zeros(LEG_COUNT)
        self.fast_path_steps = 0
        self.solved_steps = 0
        self.audit_steps = 0
        self.audit_mismatches = 0
        self.short_s = 0.0
        self.limited_s = np.zeros(LEG_COUNT)
        self.max_deficit_m3_s = 0.0
        self.max_sum_over_supply = -np.inf
        self.demand_met_limited_steps = 0

    @classmethod
    def from_params(cls, params: Params, setting: FlowLimitSetting) -> RecordedFlowLimiter:
        return cls(flow_circuit_from_params(params), setting)

    # ------------------------------------------------------------------------------- the limit
    def limit(self, t_s: float, dt_s: float, request_m_s: ArrayLike,
              force_N: ArrayLike) -> NDArray[np.float64]:
        """Delivered leg speeds of the step that starts at ``t_s`` (module docstring)."""
        u = np.array(request_m_s, dtype=float)
        force = np.asarray(force_N, dtype=float)
        load = self.pump.load_pressures_Pa(u, force)
        if self.pump.is_demand_met_with_margin(u, load):
            self.fast_path_steps += 1
            if self.fast_path_steps % FAST_PATH_AUDIT_INTERVAL == 0:
                self._audit_fast_path(u, load)
            demand = self.pump.demand_m3_s(u)
            self.max_sum_over_supply = max(self.max_sum_over_supply, demand / self.supply_m3_s)
            if t_s >= self._next_row_s - SAMPLE_TIME_TOL_S:
                self._write_row(t_s, u, u, force, load, None, demand, demand)
            return u
        self.solved_steps += 1
        result = self.pump.solve(u, load)
        delivered = result.speed_m_s
        flow_sum = float(result.flow_m3_s.sum())
        self.max_sum_over_supply = max(self.max_sum_over_supply, flow_sum / self.supply_m3_s)
        self._deficit_integral_m += (u - delivered) * dt_s
        self.limited_s += result.is_limited * dt_s
        deficit = result.demand_m3_s - self.supply_m3_s
        if deficit > self.supply_m3_s * SUPPLY_REL_TOL:
            self.short_s += dt_s
            self.max_deficit_m3_s = max(self.max_deficit_m3_s, deficit)
        elif result.is_limited.any():
            self.demand_met_limited_steps += 1
        if t_s >= self._next_row_s - SAMPLE_TIME_TOL_S:
            self._write_row(t_s, u, delivered, force, load, result, result.demand_m3_s, flow_sum)
        return delivered

    def _audit_fast_path(self, u: NDArray[np.float64], load: NDArray[np.float64]) -> None:
        self.audit_steps += 1
        if not np.array_equal(self.pump.solve(u, load).speed_m_s, u):
            self.audit_mismatches += 1

    # --------------------------------------------------------------------------------- record
    def _write_row(self, t_s, u, v, force, load, result, demand, flow_sum) -> None:
        if self._count == len(self._rows):
            self._rows = np.concatenate([self._rows, np.empty_like(self._rows)])
        row = self._rows[self._count]
        self._count += 1
        row[:] = np.nan
        row[0] = t_s
        row[U], row[V], row[OIL_FORCE], row[P_LOAD] = u, v, force, load
        row[COLUMN["Q_dem"]] = demand
        row[COLUMN["Q_sum"]] = flow_sum
        row[COLUMN["limited_mask"]] = row[COLUMN["residual_mask"]] = 0
        row[DEFICIT] = self._deficit_integral_m
        if result is not None:
            row[Y] = result.spool_drop_Pa
            row[COLUMN["p_P"]] = result.gallery_pressure_Pa
            row[COLUMN["Q_byp"]] = result.bypass_flow_m3_s
            row[COLUMN["limited_mask"]] = _leg_mask(result.is_limited)
            row[COLUMN["residual_mask"]] = _residual_mask(result.is_limited, result.spool_drop_Pa)
        self._next_row_s = (np.floor((t_s + SAMPLE_TIME_TOL_S) / self._period) + 1.0) * self._period

    def rows(self) -> NDArray[np.float64]:
        """All recorded rows, :data:`COLUMNS` order."""
        return self._rows[: self._count].copy()

    def save(self, path: str | Path) -> dict[str, Any]:
        """Write the series (module docstring); returns the entry for the run summary."""
        rows = self.rows()
        np.savez_compressed(path, rows=rows, columns=np.array(COLUMNS),
                            supply_m3_s=np.array(self.supply_m3_s),
                            setting_json=np.array(json.dumps(self.setting.to_dict())))
        return {"file": Path(path).name, "rows": len(rows), "period_s": self._period,
                "columns": "harness_flow.COLUMNS layout + deficit_integral_*"}

    # -------------------------------------------------------------------------------- summary
    def meta(self) -> dict[str, Any]:
        """Setting, circuit and code provenance (run meta)."""
        assumptions = self.pump.assumptions
        source = Path(__file__).resolve()
        return {
            "enabled": True,
            "setting": self.setting.to_dict(),
            "supply_L_min": self.supply_m3_s * L_MIN_PER_M3_S,
            "circuit": {"head_area_m2": self.circuit.head_area_m2.tolist(),
                        "annulus_area_m2": self.circuit.annulus_area_m2.tolist(),
                        "pump_flow_m3_s": self.circuit.pump_flow_m3_s,
                        "max_speed_m_s": self.circuit.max_speed_m_s,
                        "relief_pressure_Pa": self.circuit.relief_pressure_Pa},
            "assumptions": {"tank_pressure_Pa": assumptions.tank_pressure_Pa,
                            "pilot_pressure_Pa": assumptions.pilot_pressure_Pa,
                            "back_land_ratio": assumptions.back_land_ratio},
            "code_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in (
                ("flow_share.py", source.with_name("flow_share.py")),
                ("flow_limit_run.py", source))},
            "basis": "hydraulic_coupling_criteria.md 9, 9.1; per physics step after the valve, "
                     "before stroke-end braking and law C",
        }

    def summary(self, phase_start_s: ArrayLike = (), phase_names: tuple[str, ...] = ()) -> dict[str, Any]:
        """Per-step counters and the per-phase tables of criteria 7.3 E-1 to E-4.

        Args:
            phase_start_s: Time each controller phase starts, same clock as ``t_s`` of :meth:`limit`.
            phase_names: Name of each phase.
        """
        rows = self.rows()
        out: dict[str, Any] = {
            "steps": {"fast_path": self.fast_path_steps, "solved": self.solved_steps,
                      "audit": self.audit_steps, "audit_mismatches": self.audit_mismatches,
                      "demand_met_but_limited": self.demand_met_limited_steps},
            "short_s": _rounded(self.short_s, 4),
            "limited_s": dict(zip(LEG_ORDER, np.round(self.limited_s, 4).tolist(), strict=True)),
            "max_deficit_L_min": _rounded(self.max_deficit_m3_s * L_MIN_PER_M3_S, 5),
            "max_sum_Q_over_supply_minus_1": _rounded(self.max_sum_over_supply - 1.0, 12),
            "deficit_integral_end_mm": dict(zip(
                LEG_ORDER, np.round(self._deficit_integral_m * MM_PER_M, 4).tolist(), strict=True)),
        }
        if len(rows) == 0:
            return out
        phases = self._row_phases(rows, phase_start_s, phase_names)
        out["by_phase"] = {str(name): self._phase_table(rows, phases == name)
                           for name in dict.fromkeys(phases.tolist())}
        out["speed_ratio"] = self._speed_ratio(rows, phases)
        out["tracking"] = self._tracking(rows)
        out["limited_sets"] = self._limited_sets(rows)
        out["residual_groups"] = self._residual_groups(rows)
        return out

    def _row_phases(self, rows, phase_start_s, phase_names) -> NDArray[Any]:
        starts = np.asarray(phase_start_s, dtype=float)
        names = np.array(list(phase_names) if len(phase_names) else ["unknown"], dtype=object)
        if starts.size == 0:
            return np.full(len(rows), "unknown", dtype=object)
        index = np.searchsorted(starts, rows[:, 0] + SAMPLE_TIME_TOL_S, side="right") - 1
        return names[np.clip(index, 0, None)]

    def _phase_table(self, rows, selected) -> dict[str, Any]:
        period = self._period
        demand = rows[selected, COLUMN["Q_dem"]]
        limited = rows[selected, COLUMN["limited_mask"]].astype(int)
        gallery = rows[selected, COLUMN["p_P"]]
        solved = np.isfinite(gallery)
        is_short = demand > self.supply_m3_s * (1.0 + SUPPLY_REL_TOL)
        return {
            "duration_s": _rounded(selected.sum() * period, 3),
            "short_s": _rounded(is_short.sum() * period, 3),
            "max_deficit_L_min": _rounded(
                max(0.0, float((demand - self.supply_m3_s).max())) * L_MIN_PER_M3_S, 4),
            "limited_s": {leg: _rounded(float(((limited >> i) & 1).sum()) * period, 3)
                          for i, leg in enumerate(LEG_ORDER)},
            "limited_set_s": {_mask_name(int(mask)): _rounded(float((limited == mask).sum()) * period, 3)
                              for mask in np.unique(limited[limited > 0])},
            "gallery_bar": None if not solved.any() else [
                _rounded(float(gallery[solved].min()) / PA_PER_BAR, 3),
                _rounded(float(gallery[solved].max()) / PA_PER_BAR, 3)],
        }

    def _speed_ratio(self, rows, phases) -> dict[str, Any]:
        window = max(1, round(SPEED_RATIO_WINDOW_S / self._period))
        table: dict[str, Any] = {}
        for i, leg in enumerate(LEG_ORDER):
            if len(rows) < window:
                table[leg] = {"min_r_by_phase": {}, "longest_below_0p93_s": 0.0}
                continue
            kernel = np.ones(window) / window
            mean_u = np.convolve(rows[:, U][:, i], kernel, "valid")
            mean_v = np.convolve(rows[:, V][:, i], kernel, "valid")
            with np.errstate(invalid="ignore", divide="ignore"):
                ratio = np.where(np.abs(mean_u) >= SPEED_RATIO_MIN_REQUEST * self.circuit.max_speed_m_s,
                                 mean_v / mean_u, np.nan)
            ratio = np.concatenate([np.full(window - 1, np.nan), ratio])
            valid = np.isfinite(ratio)
            by_phase = {}
            for name in dict.fromkeys(phases.tolist()):
                chosen = valid & (phases == name)
                if chosen.any():
                    by_phase[str(name)] = _rounded(ratio[chosen].min(), 5)
            table[leg] = {"min_r_by_phase": by_phase, "longest_below_0p93_s": _rounded(
                _longest_run(valid & (ratio < SPEED_RATIO_FLAG)) * self._period, 3)}
        return table

    def _tracking(self, rows) -> dict[str, Any]:
        integral_mm = rows[:, DEFICIT] * MM_PER_M
        spread = integral_mm.max(axis=1) - integral_mm.min(axis=1)
        return {"max_abs_integral_mm": dict(zip(
            LEG_ORDER, np.round(np.abs(integral_mm).max(axis=0), 3).tolist(), strict=True)),
                "max_between_legs_mm": _rounded(float(spread.max()), 3)}

    def _limited_sets(self, rows) -> dict[str, float]:
        """Longest unbroken duration per limited-leg set (criteria T-4 inputs)."""
        masks = rows[:, COLUMN["limited_mask"]].astype(int)
        return {_mask_name(int(mask)): _rounded(_longest_run(masks == mask) * self._period, 3)
                for mask in np.unique(masks[masks > 0])}

    def _residual_groups(self, rows) -> dict[str, Any]:
        masks = rows[:, COLUMN["residual_mask"]].astype(int)
        swaps = []
        previous = 0
        for index in np.flatnonzero(masks > 0):
            mask = int(masks[index])
            if previous != 0 and (mask & previous) == 0:
                swaps.append(float(rows[index, 0]))
            previous = mask
        most_in_1s = 0
        if swaps:
            times = np.array(swaps)
            most_in_1s = int((np.searchsorted(times, times + 1.0) - np.arange(len(times))).max())
        return {"sample_period_s": self._period, "tie_width_bar": RESIDUAL_TIE_PA / PA_PER_BAR,
                "group_s": {_mask_name(int(mask)): _rounded(float((masks == mask).sum()) * self._period, 3)
                            for mask in np.unique(masks[masks > 0])},
                "disjoint_swaps": len(swaps), "max_disjoint_swaps_in_1s": most_in_1s}


__all__ = [
    "COLUMNS",
    "DEFAULT_RECORD_PERIOD_S",
    "FLOW_SERIES_NAME",
    "FlowLimitSetting",
    "RecordedFlowLimiter",
    "add_flow_limit_arguments",
    "flow_setting_from_args",
]
