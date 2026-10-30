"""Spec 427.9 (P-S8-36 SGS, user decision 2026-10-30): the judgement class ``stroke_limited_stop``
of a run the soil-guard stop ended, for the reduced harness judges (``s9_soil_slope.py``
``classify``, ``r72_g6_screen.py`` G6) and the ``s9_slope_fix_candidates.py`` compare.

A run whose first FAULT is ``FAULT_LIFT_STROKE_LIMIT:soil:<legs>`` is a "safe stop, target not
reached" (neither pass nor fail) when all of these hold, otherwise it is a fail:

1. the stop reason is the soil guard (the first ``FAULT*`` event is the soil stop);
2. no ``FAULT_STROKE_END``;
3. no leg lift (pad contact force true F_cyl + rod weight never reaches 0 after the LEVEL start);
4. true F_cyl minimum after the crawler lift-off to the run end >= F_min;
5. moving pressure <= 180 bar and no saturation: head-equivalent F_cyl / A_p of the 1 ms chunks
   with |valve| > 1e-6 m/s (the E-4 harness form of ``s9_soil_event_screen``, here over the
   whole run), saturation = an extending chunk at >= 210 bar (relief).

The 1 ms pressure comes from :func:`install_moving_pressure_recorder` (record only, no command
change). Units: s, N, bar, kN where the key says so.

Records at the stop (spec 427.12.1 item 1, record only, the class rule is unchanged): a stop
before the crawler lift-off keeps condition 4 unmet (fail); :func:`stop_state_record` adds
``stop_with_crawler_loaded`` (true crawler force at the stop > 0.01 W) and the four-leg true
F_cyl minimum of the stop period (``min_true_Fcyl_at_stop_kN``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

SOIL_STOP_EVENT = "FAULT_LIFT_STROKE_LIMIT:soil"
"""``FAULT_LIFT_STROKE_LIMIT:soil:<legs>`` (spec 427.9, wrapper token P36s)."""
FAULT_EVENT_PREFIX = "FAULT"
STROKE_END_FAULT_EVENT = "FAULT_STROKE_END"
VERDICT_STROKE_LIMITED_STOP = "stroke_limited_stop"
MOVING_PRESSURE_MAX_BAR = 180.0
RELIEF_PRESSURE_BAR = 210.0
MOVING_SPEED_EPS_M_S = 1e-6
"""|valve| above this is a moving chunk (``s9_soil_event_screen.MOVING_SPEED_EPS_M_S``)."""
PA_PER_BAR = 1e5
LEGS = ("FL", "FR", "RL", "RR")
CRAWLER_LOADED_WEIGHT_FRACTION = 0.01
"""The crawler still carries load at the stop above this fraction of W (spec 427.12.1)."""
TIME_MATCH_S = 1e-6
"""Sample times up to this after the stop event count as "at the stop"."""


@dataclass
class MovingPressureRecord:
    """Running maxima of the head-equivalent pressure over the 1 ms chunks of one run."""

    max_moving_bar: float = 0.0
    max_moving_leg: str | None = None
    t_max_moving_s: float | None = None
    max_extending_bar: float = 0.0
    saturation_ms: int = 0
    """Extending chunks at or above the relief pressure (leg-chunks)."""
    chunks: int = 0

    def add(self, t_s: float, cylinder_force_N, valve_m_s, piston_area_m2) -> None:
        """One chunk: true F_cyl [N], valve speed at the chunk end [m/s], A_p [m^2] per leg."""
        self.chunks += 1
        valve = np.asarray(valve_m_s, float)
        moving = np.abs(valve) > MOVING_SPEED_EPS_M_S
        if not moving.any():
            return
        pressure_bar = (np.asarray(cylinder_force_N, float)
                        / np.asarray(piston_area_m2, float) / PA_PER_BAR)
        moving_bar = np.where(moving, pressure_bar, -np.inf)
        leg = int(np.argmax(moving_bar))
        if moving_bar[leg] > self.max_moving_bar:
            self.max_moving_bar = float(moving_bar[leg])
            self.max_moving_leg = LEGS[leg]
            self.t_max_moving_s = float(t_s)
        extending = valve > MOVING_SPEED_EPS_M_S
        if extending.any():
            self.max_extending_bar = max(self.max_extending_bar,
                                         float(pressure_bar[extending].max()))
            self.saturation_ms += int(np.sum(pressure_bar[extending] >= RELIEF_PRESSURE_BAR))

    def to_dict(self) -> dict:
        return {"max_moving_bar": round(self.max_moving_bar, 2),
                "max_moving_leg": self.max_moving_leg,
                "t_max_moving_s": None if self.t_max_moving_s is None
                else round(self.t_max_moving_s, 3),
                "max_extending_bar": round(self.max_extending_bar, 2),
                "saturation_ms": self.saturation_ms, "chunks": self.chunks,
                "definition": "1 ms chunks, |valve| > 1e-6 m/s, F_cyl / A_p, whole run"}


def install_moving_pressure_recorder(
        cl, record_of_run: Callable[[], MovingPressureRecord | None]) -> None:
    """Wrap ``cl._lagged_step`` once (record only): every chunk adds the plant's true F_cyl
    (contact force - rod weight), the valve state after the chunk and ``plant.Ap`` to the record
    ``record_of_run()`` returns (``None``: not recording).

    The wrapper keeps the ``is_*`` markers of the function it wraps, so the other one-time hooks
    (``late_loc_rule.install_crawler_recorder``, the wrapper ``is_truth_hook``) still see
    themselves installed.
    """
    current = cl._lagged_step
    if getattr(current, "is_moving_pressure_recorder", False):
        return

    def lagged_step_with_pressure_record(plant, command, valve, steps):
        accumulated = current(plant, command, valve, steps)
        record = record_of_run()
        if record is not None:
            force_N = np.asarray(accumulated[11:15], float) - plant.Wr
            record.add(plant.t, force_N, valve, plant.Ap)
        return accumulated

    markers = {name: value for name, value in getattr(current, "__dict__", {}).items()
               if name.startswith("is_")}
    lagged_step_with_pressure_record.__dict__.update(markers)
    lagged_step_with_pressure_record.is_moving_pressure_recorder = True
    cl._lagged_step = lagged_step_with_pressure_record


def is_soil_stop(event_names: Sequence[str]) -> bool:
    """The run has a soil-guard stop event."""
    return any(name.startswith(SOIL_STOP_EVENT) for name in event_names)


def _first_fault(event_names: Sequence[str]) -> str | None:
    return next((name for name in event_names if name.startswith(FAULT_EVENT_PREFIX)), None)


def soil_stop_time_s(events: Sequence[tuple[float, str]]) -> float | None:
    """Time of the first soil-guard stop event of (t_s, name) events; None without one."""
    return next((float(t_s) for t_s, name in events if name.startswith(SOIL_STOP_EVENT)), None)


def _last_index_at_or_before(times_s: Sequence[float], t_s: float) -> int | None:
    """Index of the last sample at or before ``t_s`` (times in increasing order)."""
    index = int(np.searchsorted(np.asarray(times_s, float), t_s + TIME_MATCH_S, side="right")) - 1
    return None if index < 0 else index


def _crawler_force_at_N(crawler_series: Sequence[tuple[float, float]],
                        t_s: float) -> float | None:
    if not crawler_series:
        return None
    index = _last_index_at_or_before([t for t, _ in crawler_series], t_s)
    return None if index is None else float(crawler_series[index][1])


def _leg_force_min_at_kN(leg_force_rows: Sequence[tuple[float, Sequence[float]]],
                         t_s: float) -> tuple[float | None, list[float] | None]:
    if not leg_force_rows:
        return None, None
    index = _last_index_at_or_before([t for t, _ in leg_force_rows], t_s)
    if index is None:
        return None, None
    per_leg_kN = [float(v) for v in leg_force_rows[index][1]]
    return min(per_leg_kN), per_leg_kN


def stop_state_record(stop_time_s: float | None,
                      crawler_series: Sequence[tuple[float, float]] | None,
                      weight_N: float | None,
                      leg_force_rows_kN: Sequence[tuple[float, Sequence[float]]] | None) -> dict:
    """Spec 427.12.1 records of the state at the soil-guard stop (record only).

    Args:
        stop_time_s: time of the soil-stop event (None: no stop, all values None).
        crawler_series: (t_s, true crawler force N) of every 1 ms plant chunk; the chunk at or
            just before the stop is used.
        weight_N: plant weight W [N] of the 0.01 W threshold.
        leg_force_rows_kN: (t_s, per-leg true F_cyl minimum of the control period [kN]) of every
            period; the period that ends at the stop (the one the stop decision read) is used.

    Returns:
        {"stop_t_s", "stop_with_crawler_loaded", "crawler_N_at_stop",
        "crawler_loaded_threshold_N", "min_true_Fcyl_at_stop_kN",
        "true_Fcyl_at_stop_kN"}; ``stop_with_crawler_loaded`` is None when the crawler force or
        W is unknown.
    """
    record = {"stop_t_s": stop_time_s, "stop_with_crawler_loaded": None,
              "crawler_N_at_stop": None, "crawler_loaded_threshold_N": None,
              "min_true_Fcyl_at_stop_kN": None, "true_Fcyl_at_stop_kN": None}
    if stop_time_s is None:
        return record
    crawler_N = _crawler_force_at_N(crawler_series or [], stop_time_s)
    threshold_N = (None if weight_N is None
                   else CRAWLER_LOADED_WEIGHT_FRACTION * float(weight_N))
    min_kN, per_leg_kN = _leg_force_min_at_kN(leg_force_rows_kN or [], stop_time_s)
    record.update(
        crawler_N_at_stop=None if crawler_N is None else round(crawler_N, 1),
        crawler_loaded_threshold_N=None if threshold_N is None else round(threshold_N, 1),
        stop_with_crawler_loaded=(None if crawler_N is None or threshold_N is None
                                  else bool(crawler_N > threshold_N)),
        min_true_Fcyl_at_stop_kN=None if min_kN is None else round(min_kN, 3),
        true_Fcyl_at_stop_kN=(None if per_leg_kN is None
                              else [round(v, 3) for v in per_leg_kN]))
    return record


def stroke_limited_stop_row(event_names: Sequence[str], lifted_legs: Sequence[str],
                            min_force_after_off_kN: float | None, f_min_kN: float,
                            moving_pressure: dict | None,
                            stop_state: dict | None = None) -> dict | None:
    """The spec 427.9 safe-stop conditions of a run with a soil-guard stop; None without one.

    Args:
        event_names: controller events of the run in time order.
        lifted_legs: legs whose pad contact force reached 0 after the LEVEL start.
        min_force_after_off_kN: true F_cyl minimum after the crawler lift-off (None: unknown).
        f_min_kN: F_min.
        moving_pressure: :meth:`MovingPressureRecord.to_dict` of the run (None: not recorded,
            the pressure conditions then fail).
        stop_state: :func:`stop_state_record` of the run (record only, not a condition);
            None leaves its keys None.

    Returns:
        {"pass", "conditions", "stop_event", "lifted_legs", "min_true_Fcyl_after_off_kN",
        "moving_pressure", "stop_with_crawler_loaded", "min_true_Fcyl_at_stop_kN",
        "stop_state"}; ``pass`` means the class ``stroke_limited_stop``.
    """
    if not is_soil_stop(event_names):
        return None
    first_fault = _first_fault(event_names)
    pressure = moving_pressure or {}
    max_moving_bar = pressure.get("max_moving_bar")
    saturation_ms = pressure.get("saturation_ms")
    conditions = {
        "stop_reason_soil": first_fault is not None and first_fault.startswith(SOIL_STOP_EVENT),
        "no_stroke_end_fault": not any(name.startswith(STROKE_END_FAULT_EVENT)
                                       for name in event_names),
        "no_leg_lift": not lifted_legs,
        "min_force_after_off": (min_force_after_off_kN is not None
                                and min_force_after_off_kN >= f_min_kN),
        "moving_pressure": max_moving_bar is not None and max_moving_bar <= MOVING_PRESSURE_MAX_BAR,
        "no_saturation": saturation_ms == 0,
    }
    return {"pass": all(conditions.values()), "conditions": conditions,
            "stop_event": next(name for name in event_names if name.startswith(SOIL_STOP_EVENT)),
            "lifted_legs": list(lifted_legs),
            "min_true_Fcyl_after_off_kN": min_force_after_off_kN,
            "moving_pressure": moving_pressure,
            "stop_with_crawler_loaded": (stop_state or {}).get("stop_with_crawler_loaded"),
            "min_true_Fcyl_at_stop_kN": (stop_state or {}).get("min_true_Fcyl_at_stop_kN"),
            "stop_state": stop_state}
