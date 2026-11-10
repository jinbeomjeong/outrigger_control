"""T4-0 / T4 / T5 replay of Chrono L2b records (v5 stage 3 R-6; criteria rev. 6 4-7).

For each case folder (read only):

* settings: the R8 preset with the run's valve lag, plant lock window (``apply_lock_window`` of
  the stored v5 options) and the L2b fallback-ratio source; the rebuilt ``two_pressure`` meta
  must equal the run's (``r5_fallback_replay.monitor_setting_differences``), else no verdict;
* T4-0: the monitor replayed with the run's own events must give the recorded lower reading
  (``s8_series.npz`` ``F_lower_N``) to a relative 1e-12, else no verdict (tool defect);
* T4: all four legs fall back from the first row; judged samples = zero acting command with a
  truth value, ``law_locked`` 1 (locked) or 0 (tail); -1 (no armed law) is counted only;
  excess = ``lower - F_pressure`` > 0.6 kN;
* T5 (``--t5``): per leg and command-free stretch, every start sample ``m`` alone falls back
  (the monitor state before ``m`` is the T4-0 replay's, copied);
* records: the lift-off time (D-a, ``lift_times``), the M2 clip split at it, the H-b release
  judgement (``m2_release_log.judge_release``) and the extension lock anchor counters
  (``ext_lock_*``) from ``hydraulics_record.m2_releases``.

Truth: ``pads.npz`` ``F_pressure`` (net oil force) at ``j = searchsorted(t_pads, t_k - 1e-9)``
when ``|t_pads[j] - t_k| <= 0.5 ms``; ``law_locked``, ``airborne`` and
``F_pressure_min_interval`` at the same ``j``.

Criteria revision (``--criteria``, default ``rev7`` since the user decision of 2026-11-08;
``rev6`` only when given explicitly, its output is unchanged):

* ``rev6``: the judged samples and the failure above;
* ``rev7`` (``v5_criteria_rev7.md`` 3): the E samples (CHECK, before the leg's zero calibration,
  tail, airborne, last motion a retraction) leave the judged samples when the forced lower
  bound there is below 0 kN (guard 3.2; T4 forced from the first row, T5 from the start ``m``);
  sensor-error rows (``settings.bundle_c.sensor_model``) fail on the fallback's own excess
  ``(lower - F_p) - max(plain - F_p, 0)`` (B1 3.3, ``plain`` = replay without any fallback);
  the 3.4 records are added and the report carries ``"criteria": "rev7"``.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/chrono_t45_replay.py <out_json> <case or batch>
      [...] [--t5] [--extend-start tracked_bound] [--criteria rev6]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from j_p3_inputs import is_p3_expected, j_p3_over_rows  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
EXCESS_LIMIT_N = 600.0
"""Criteria rev. 6 4.3: lower bound <= truth + 0.6 kN."""
ALIGN_TOL_S = 0.5e-3
ALIGN_EPS_S = 1.0e-9
RELATIVE_TOL = 1.0e-12
"""T4-0: replayed against recorded lower reading."""
LAW_LOCKED, LAW_MOVING, LAW_UNARMED = 1, 0, -1
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
FAULT_REASON_EVENT = "INFO_ROD_PRESSURE_FAULT_REASON"
PRE_LIFT_PHASES = ("idle", "check", "touch")
SUSTAINED_LIFT_WEIGHT_FRACTION = 0.01
"""D-a: ``F_cr,n <= 0.01 W`` held to the run end (``stop_crawler_values`` threshold)."""
FALSE_LIFTOFF_S = 0.1
"""H-18: above ``0.01 W`` longer than this after ``t_lift``."""
GRAVITY_M_S2 = 9.81
EXT_LOCK_EXCESS_PA = 0.1e5
EXT_LOCK_RISK_PA = 11.0e5
"""Criteria rev. 6 4.5: excess above 11 bar (``p_r0`` above the 13 bar fallback start)."""
ANCHOR_MATCH_PA = 1.0e-6
CONSERVATISM_PERCENTILES = (50, 90, 99)
HARNESS_VALVE_TAU_S = 0.1
READY_PHASE = "ready"
"""``C2Phase.READY.value``."""
CHECK_PHASE = "check"
"""``C2Phase.CHECK.value`` (criteria rev. 7 E1)."""
CRITERIA_REV6, CRITERIA_REV7 = "rev6", "rev7"
DEFAULT_CRITERIA = CRITERIA_REV7
"""Criteria revision used unless ``rev6`` is asked for explicitly (user decision 2026-11-08)."""
GUARD_LIMIT_N = 0.0
"""Criteria rev. 7 3.2: an E sample leaves the judged samples only below this forced lower."""


# ------------------------------------------------------------------------------- inputs
@dataclass
class CaseRecord:
    """One case folder ready for the replays."""

    case_dir: Path
    result: dict
    events: list[tuple[float, str]]
    episode: Any
    geometry: Any
    config: Any
    allowance: Any
    truth_N: np.ndarray
    """``F_pressure`` at the samples (NaN without a truth value), (n, 4)."""
    truth_min_N: np.ndarray
    law_state: np.ndarray
    """``law_locked`` at the samples (``LAW_UNARMED`` without a truth value), (n, 4)."""
    airborne: np.ndarray
    acting_m_s: np.ndarray


def align_truth(t_pads: np.ndarray, t_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(index ``j`` per sample, has truth) with the 0.5 ms rule (criteria rev. 6 4.1)."""
    t_pads = np.asarray(t_pads, float)
    index = np.searchsorted(t_pads, np.asarray(t_s, float) - ALIGN_EPS_S)
    clipped = np.clip(index, 0, len(t_pads) - 1)
    has_truth = (index < len(t_pads)) & (np.abs(t_pads[clipped] - t_s) <= ALIGN_TOL_S)
    return clipped, has_truth


def run_config(result: dict, extend_start: str | None = None):
    """The run's controller setting: R8 preset, valve lag of the plant, controller options of
    the stored v5 options (read only, ``HydraulicOptions.from_stored``: lock window and, for a
    criteria revision 8 VB / LS run, the ③ start bound; a ③-on run without the option key
    takes the stored monitor rule), L2b ratio source. ``extend_start`` overrides the rule."""
    from outrigger_sim.chrono.fallback_ratio import with_engine_fallback_ratio
    from outrigger_sim.control.c2 import C2Config
    from outrigger_sim.hydraulics.v5_options import (
        EXTEND_START_TRACKED_RULE,
        HydraulicOptions,
        apply_controller_options,
        check_extend_start,
    )
    from outrigger_sim.params import load_params

    v5 = result.get("v5_hydraulics") or {}
    valve_tau_s = float(((v5.get("actuator") or {}).get("valve") or {}).get(
        "tau_v_s", HARNESS_VALVE_TAU_S))
    config = C2Config().with_10hz_d1(liftoff_approach_slow=recorded_liftoff_slow(result),
                                     flat_soil_margin_order_gate=recorded_order_gate(result))
    config, _ = with_engine_fallback_ratio(config, "L2b_NSC")
    if config.two_pressure.lock_window_valve_tau_s != valve_tau_s:
        config = replace(config, two_pressure=replace(config.two_pressure,
                                                      lock_window_valve_tau_s=valve_tau_s))
    stored = v5.get("hydraulic_options")
    options = None if stored is None else HydraulicOptions.from_stored(stored)
    if options is not None:
        config = apply_controller_options(config, options,
                                          load_params().actuator.max_speed_m_s, valve_tau_s)
    stored_rule = (((result.get("controller_meta") or {}).get("two_pressure") or {})
                   .get("settings") or {}).get("extend_start_rule")
    if extend_start is None and stored_rule == EXTEND_START_TRACKED_RULE:
        extend_start = stored_rule
    if extend_start is not None:
        check_extend_start(options, extend_start)
        config = replace(config, two_pressure=replace(config.two_pressure,
                                                      extend_start_rule=extend_start))
    return config


def load_case(case_dir: Path, extend_start: str | None = None) -> CaseRecord:
    from outrigger_sim.contact_episode import (
        MachineConstants,
        build_episode,
        read_controller_events,
    )
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.control.r5_fallback_replay import offset_allowance
    from outrigger_sim.params import load_params

    case_dir = Path(case_dir)
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    events = read_controller_events(case_dir / "controller_events.json")
    level = (result.get("settings") or {}).get("level") or "top"
    geometry = C2Geometry.from_params(load_params(level=level))
    episode = build_episode(case_dir, MachineConstants.from_geometry(geometry))
    t_s = np.asarray(episode["t_s"], float)
    with np.load(case_dir / "pads.npz", allow_pickle=False) as pads:
        index, has_truth = align_truth(pads["t"], t_s)
        truth = np.where(has_truth[:, None], pads["F_pressure"][index], np.nan)
        truth_min = np.where(has_truth[:, None], pads["F_pressure_min_interval"][index], np.nan)
        law = np.where(has_truth[:, None], pads["law_locked"][index], LAW_UNARMED)
        airborne = np.where(has_truth[:, None], pads["airborne"][index], False)
    acting = np.zeros_like(np.asarray(episode["command_m_s"], float))
    acting[1:] = np.asarray(episode["command_m_s"], float)[:-1]
    return CaseRecord(case_dir, result, events, episode, geometry,
                      run_config(result, extend_start),
                      offset_allowance(result["controller_meta"], events), truth, truth_min,
                      law.astype(int), airborne.astype(bool), acting)


# ------------------------------------------------------------------------------- replays
def _replay(record: CaseRecord, events) -> np.ndarray:
    from outrigger_sim.control.contact_replay import replay_fallback_monitor

    allowance = record.allowance
    return replay_fallback_monitor(
        record.episode, events, record.geometry, record.config,
        offset_allowance_N=allowance.deduction_N,
        offset_allowance_from_s=allowance.from_s).lower_reading_N


def _without_fallback(events) -> list[tuple[float, str]]:
    return [(t, name) for t, name in events
            if not name.startswith((FALLBACK_EVENT, FAULT_REASON_EVENT))]


def forced_events(record: CaseRecord, starts: dict[int, float]) -> list[tuple[float, str]]:
    """The run's events without its fallbacks, with ``starts`` {leg: time} forced first."""
    forced = [(t, f"{FALLBACK_EVENT}:{LEGS[leg]}") for leg, t in sorted(starts.items())]
    return forced + _without_fallback(record.events)


def t4_0(record: CaseRecord) -> dict:
    """Criteria rev. 6 4.2: the replay with the run's events equals the recorded reading."""
    replayed = _replay(record, record.events)
    recorded = np.asarray(record.episode["lower_reading_N"], float)
    scale = np.maximum(np.abs(recorded), 1.0)
    difference = np.where(np.isnan(replayed) & np.isnan(recorded), 0.0,
                          np.abs(replayed - recorded) / scale)
    worst = float(np.nanmax(difference)) if difference.size else 0.0
    return {"t4_0": bool(np.isfinite(worst) and worst <= RELATIVE_TOL),
            "max_relative_difference": worst}


def _judged(record: CaseRecord) -> np.ndarray:
    """Zero acting command, a truth value and an armed law (criteria rev. 6 4.3)."""
    return ((record.acting_m_s == 0.0) & np.isfinite(record.truth_N)
            & (record.law_state != LAW_UNARMED))


def command_free_stretches(acting_column: np.ndarray) -> list[tuple[int, int]]:
    """(first row, last row) of each run of zero acting commands of one leg."""
    stretches, start = [], None
    for row, command in enumerate(acting_column):
        if command == 0.0 and start is None:
            start = row
        elif command != 0.0 and start is not None:
            stretches.append((start, row - 1))
            start = None
    if start is not None:
        stretches.append((start, len(acting_column) - 1))
    return stretches


def _excess_summary(record: CaseRecord, lower: np.ndarray, judged: np.ndarray,
                    leg: int, failure_excess_N: np.ndarray | None = None) -> dict:
    """Judged-sample counts and the over counts of one leg; ``failure_excess_N`` (n,) is the
    quantity the failure reads (rev. 7 B1), the raw excess ``lower - F_p`` without it."""
    t_s = np.asarray(record.episode["t_s"], float)
    excess = lower[:, leg] - record.truth_N[:, leg]
    failing = excess if failure_excess_N is None else failure_excess_N
    locked = judged[:, leg] & (record.law_state[:, leg] == LAW_LOCKED)
    tail = judged[:, leg] & (record.law_state[:, leg] == LAW_MOVING)
    over = judged[:, leg] & (failing > EXCESS_LIMIT_N)
    out = {"judged_locked": int(locked.sum()), "judged_tail": int(tail.sum()),
           "airborne_judged": int((judged[:, leg] & record.airborne[:, leg]).sum()),
           "over_0p6kN_locked": int((over & locked).sum()),
           "over_0p6kN_tail": int((over & tail).sum()),
           "max_excess_N": None, "max_excess_t_s": None, "max_excess_class": None}
    if judged[:, leg].any():
        rows = np.flatnonzero(judged[:, leg])
        worst = rows[int(np.argmax(excess[rows]))]
        out.update(max_excess_N=float(excess[worst]), max_excess_t_s=float(t_s[worst]),
                   max_excess_class="locked" if locked[worst] else "tail")
        window = lower[rows, leg] - record.truth_min_N[rows, leg]
        finite = window[np.isfinite(window)]
        out["max_excess_vs_window_min_N"] = float(finite.max()) if finite.size else None
    return out


def _conservatism(record: CaseRecord, lower: np.ndarray, judged: np.ndarray,
                  leg: int) -> dict:
    """``F_p - lower`` at the last judged sample of each command-free stretch (kN)."""
    values = []
    for first, last in command_free_stretches(record.acting_m_s[:, leg]):
        rows = [row for row in range(first, last + 1) if judged[row, leg]]
        if rows:
            values.append((record.truth_N[rows[-1], leg] - lower[rows[-1], leg]) / 1e3)
    if not values:
        return {f"p{p}_kN": None for p in CONSERVATISM_PERCENTILES}
    return {f"p{p}_kN": float(np.percentile(values, p)) for p in CONSERVATISM_PERCENTILES}


def _tail_after_extension(record: CaseRecord, judged: np.ndarray, leg: int) -> int:
    """Tail samples of stretches that follow an extension, from the first READY on."""
    phase = np.asarray(record.episode["phase"]).astype(str)
    ready_rows = np.flatnonzero(phase == READY_PHASE)
    if ready_rows.size == 0:
        return 0
    count = 0
    for first, last in command_free_stretches(record.acting_m_s[:, leg]):
        if first == 0 or record.acting_m_s[first - 1, leg] <= 0.0 or first <= ready_rows[0]:
            continue
        rows = np.arange(first, last + 1)
        count += int(np.sum(judged[rows, leg] & (record.law_state[rows, leg] == LAW_MOVING)))
    return count


# ------------------------------------------------------------------- criteria rev. 7 (3)
@dataclass(frozen=True)
class Rev7Samples:
    """Criteria rev. 7 3.1 / 3.3 inputs of one record; masks are (n, 4) on the rev. 6
    judged samples."""

    excluded_candidate: np.ndarray
    """E1-E5 all hold (the guard 3.2 still decides per forced lower)."""
    e1_to_e4: np.ndarray
    """E1-E4 (3.4 reference count, E5 left out)."""
    check_precalibration: np.ndarray
    """E1 and E2 (CHECK before the leg's zero calibration)."""
    is_sensor_model_row: bool
    plain_lower_N: np.ndarray | None
    """Replay without any fallback event (B1 ``l^plain``); only on sensor-error rows."""


def last_motion_was_retraction(acting_m_s: np.ndarray) -> np.ndarray:
    """(n, 4): the last nonzero acting command before row ``k`` is negative (E5)."""
    acting_m_s = np.asarray(acting_m_s, float)
    is_retraction = np.zeros(acting_m_s.shape, bool)
    for leg in range(acting_m_s.shape[1]):
        last_command = 0.0
        for row, command in enumerate(acting_m_s[:, leg]):
            is_retraction[row, leg] = last_command < 0.0
            if command != 0.0:
                last_command = command
    return is_retraction


def is_sensor_model_row(result: dict) -> bool:
    """Criteria rev. 7 3.3: ``settings.bundle_c.sensor_model`` of ``result.json`` (absent =
    false)."""
    bundle_c = ((result.get("settings") or {}).get("bundle_c") or {})
    return bool(bundle_c.get("sensor_model"))


def rev7_samples(record: CaseRecord, judged: np.ndarray) -> Rev7Samples:
    """The E masks (3.1) and the plain lower bound of a sensor-error row (3.3)."""
    from outrigger_sim.control.contact_replay import _calibration_rows

    t_s = np.asarray(record.episode["t_s"], float)
    is_check = (np.asarray(record.episode["phase"]).astype(str) == CHECK_PHASE)[:, None]
    calibration_rows = _calibration_rows(record.events, t_s, record.config.period_s)
    is_precalibration = np.arange(t_s.size)[:, None] < calibration_rows[None, :]
    check_precalibration = judged & is_check & is_precalibration
    e1_to_e4 = (check_precalibration & (record.law_state == LAW_MOVING)
                & record.airborne)
    candidate = e1_to_e4 & last_motion_was_retraction(record.acting_m_s)
    is_sensor_row = is_sensor_model_row(record.result)
    plain = _replay(record, _without_fallback(record.events)) if is_sensor_row else None
    return Rev7Samples(candidate, e1_to_e4, check_precalibration, is_sensor_row, plain)


def guarded_exclusion(candidate: np.ndarray,
                      forced_lower_N: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(excluded, guard violations): an E sample leaves only with a forced lower < 0 kN."""
    is_negative = np.asarray(forced_lower_N, float) < GUARD_LIMIT_N
    return candidate & is_negative, candidate & ~is_negative


def own_excess_N(raw_excess_N: np.ndarray, plain_excess_N: np.ndarray) -> np.ndarray:
    """B1: ``(l^forced - F_p) - max(l^plain - F_p, 0)``."""
    return raw_excess_N - np.maximum(plain_excess_N, 0.0)


def _over_and_max(values: np.ndarray) -> tuple[int, float | None]:
    over = int(np.sum(values > EXCESS_LIMIT_N))
    return over, (float(values.max()) if values.size else None)


def _rev7_leg_record(record: CaseRecord, samples: Rev7Samples, lower: np.ndarray,
                     judged_rev6: np.ndarray, judged: np.ndarray, leg: int) -> dict:
    """Criteria rev. 7 3.4 records of one leg (T4)."""
    t_s = np.asarray(record.episode["t_s"], float)
    raw_excess = lower[:, leg] - record.truth_N[:, leg]
    candidate = samples.excluded_candidate[:, leg]
    excluded = candidate & ~judged[:, leg]
    grounded = samples.check_precalibration[:, leg] & ~record.airborne[:, leg]
    excluded_over, excluded_max = _over_and_max(raw_excess[excluded])
    rev6_over, _ = _over_and_max(raw_excess[judged_rev6[:, leg]])
    raw_over, _ = _over_and_max(raw_excess[judged[:, leg]])
    out = {"judged_samples_rev6": int(judged_rev6[:, leg].sum()),
           "e_excluded": int(excluded.sum()),
           "e_excluded_over_0p6kN": excluded_over,
           "e_excluded_max_excess_N": excluded_max,
           "guard_violations": int((candidate & judged[:, leg]).sum()),
           "e1_to_e4_samples": int(samples.e1_to_e4[:, leg].sum()),
           "check_precal_grounded": int(grounded.sum()),
           "check_precal_grounded_t_s": [float(t) for t in t_s[grounded]],
           "over_0p6kN_rev6": rev6_over, "raw_over_0p6kN": raw_over}
    if samples.is_sensor_model_row:
        plain_excess = samples.plain_lower_N[:, leg] - record.truth_N[:, leg]
        own = own_excess_N(raw_excess, plain_excess)[judged[:, leg]]
        out["own_over_0p6kN"], out["max_own_excess_N"] = _over_and_max(own)
        out["plain_over_0p6kN"], out["max_plain_excess_N"] = _over_and_max(
            plain_excess[judged[:, leg]])
    return out


def _rev7_totals(legs: dict, samples: Rev7Samples) -> dict:
    """Row totals of the rev. 7 leg records (T4 and T5 share the keys they have)."""
    keys = ("judged_samples_rev6", "e_excluded", "guard_violations", "over_0p6kN_rev6",
            "raw_over_0p6kN", "check_precal_grounded")
    totals = {key: sum(row[key] for row in legs.values()) for key in keys
              if all(key in row for row in legs.values())}
    owns = [row["max_own_excess_N"] for row in legs.values()
            if row.get("max_own_excess_N") is not None]
    return {"criteria": CRITERIA_REV7, "sensor_model": samples.is_sensor_model_row, **totals,
            "max_own_excess_N": max(owns) if owns else None}


def t4(record: CaseRecord, criteria: str = DEFAULT_CRITERIA) -> dict:
    """Criteria rev. 6 4.3 / 4.5: all legs fall back from the first row; ``rev7`` judges the
    samples left after the guarded E exclusion, sensor-error rows on the own excess (3)."""
    t0 = float(np.asarray(record.episode["t_s"], float)[0])
    lower = _replay(record, forced_events(record, {leg: t0 for leg in range(len(LEGS))}))
    judged = _judged(record)
    if criteria == CRITERIA_REV7:
        return _t4_rev7(record, lower, judged)
    legs = {}
    for leg, name in enumerate(LEGS):
        legs[name] = {**_excess_summary(record, lower, judged, leg),
                      "unarmed": int(((record.acting_m_s[:, leg] == 0.0)
                                      & (record.law_state[:, leg] == LAW_UNARMED)).sum()),
                      "conservatism": _conservatism(record, lower, judged, leg),
                      "tail_ready_extend_samples": _tail_after_extension(record, judged, leg)}
    over = sum(row["over_0p6kN_locked"] + row["over_0p6kN_tail"] for row in legs.values())
    return {"legs": legs, "over_0p6kN": over}


def _t4_rev7(record: CaseRecord, lower: np.ndarray, judged_rev6: np.ndarray) -> dict:
    samples = rev7_samples(record, judged_rev6)
    excluded, _ = guarded_exclusion(samples.excluded_candidate, lower)
    judged = judged_rev6 & ~excluded
    failure = lower - record.truth_N
    if samples.is_sensor_model_row:
        failure = own_excess_N(failure, samples.plain_lower_N - record.truth_N)
    legs = {}
    for leg, name in enumerate(LEGS):
        legs[name] = {**_excess_summary(record, lower, judged, leg, failure[:, leg]),
                      "unarmed": int(((record.acting_m_s[:, leg] == 0.0)
                                      & (record.law_state[:, leg] == LAW_UNARMED)).sum()),
                      "conservatism": _conservatism(record, lower, judged, leg),
                      "tail_ready_extend_samples": _tail_after_extension(record, judged, leg),
                      **_rev7_leg_record(record, samples, lower, judged_rev6, judged, leg)}
    over = sum(row["over_0p6kN_locked"] + row["over_0p6kN_tail"] for row in legs.values())
    judged_samples = sum(row["judged_locked"] + row["judged_tail"] for row in legs.values())
    return {"legs": legs, "over_0p6kN": over, "judged_samples": judged_samples,
            "e1_to_e4_samples": int(samples.e1_to_e4.sum()),
            **_rev7_totals(legs, samples)}


class _MonitorStepper:
    """``replay_fallback_monitor`` one row at a time (the T5 copies need its state)."""

    def __init__(self, record: CaseRecord, events) -> None:
        from outrigger_sim.control.contact_replay import (
            _calibration_rows,
            _offline_monitor,
            _previous,
            fallback_rows_from_events,
        )
        from outrigger_sim.control.two_pressure import RodSensorState

        episode, config = record.episode, record.config
        self.fallback_state = RodSensorState.FALLBACK
        self.t_s = np.asarray(episode["t_s"], float)
        self.head = np.asarray(episode["head_pressure_Pa"], float)
        self.rod = np.asarray(episode["rod_pressure_Pa"], float)
        self.stroke = np.asarray(episode["motor_stroke_m"], float)
        self.acting = record.acting_m_s
        self.is_ready = _previous(np.asarray(episode["phase"]), fill="") == READY_PHASE
        self.seal_band = _previous(np.asarray(episode["seal_band_N"], float))
        self.monitor = _offline_monitor(record.geometry, config)
        self.fallback_rows = fallback_rows_from_events(events, self.t_s, config.period_s)
        self.calibration_rows = _calibration_rows(events, self.t_s, config.period_s)
        self.offsets = np.asarray(episode.meta.get("zero_offset_N") or np.zeros(len(LEGS)),
                                  float)
        allowance = record.allowance
        self.allowance = (np.zeros(len(LEGS)) if allowance.deduction_N is None
                          else np.asarray(allowance.deduction_N, float))
        self.allowance_from_s = allowance.from_s
        fast = config.r8.fast_relevel
        self.choice = None if fast is None else fast.fallback_ratio_choice()

    def step(self, row: int, monitor=None) -> np.ndarray:
        monitor = self.monitor if monitor is None else monitor
        is_calibrated = self.calibration_rows <= row
        monitor.set_zero_offsets_N(np.where(is_calibrated, self.offsets, 0.0))
        if self.allowance_from_s is None:
            has_allowance = is_calibrated
        else:
            has_allowance = np.full(len(LEGS), self.t_s[row] > self.allowance_from_s + 1e-9)
        monitor.set_offset_allowance_N(np.where(has_allowance, self.allowance, 0.0))
        for leg, first_row in enumerate(self.fallback_rows):
            if first_row == row:
                monitor.rod_state[leg] = self.fallback_state
        forces = monitor.read(float(self.t_s[row]), self.head[row], self.rod[row],
                              self.acting[row], bool(self.is_ready[row]), self.seal_band[row],
                              stroke_m=self.stroke[row], r5_fallback_ratios=self.choice)
        return np.asarray(forces.lower, float)


def _stepper_with_states(record: CaseRecord) -> tuple[_MonitorStepper, list]:
    """The T4-0 replay stepped through, with the monitor state before every row."""
    stepper = _MonitorStepper(record, record.events)
    states = []
    for row in range(len(stepper.t_s)):
        states.append(copy.deepcopy(stepper.monitor))
        stepper.step(row)
    return stepper, states


@dataclass
class _Rev7StartTally:
    """Criteria rev. 7 counts of one leg over all T5 starts (guard per start, 3.2)."""

    over: int = 0
    raw_over: int = 0
    e_excluded: int = 0
    guard_violations: int = 0
    worst_N: float = -math.inf
    worst_own_N: float = -math.inf

    def add(self, raw_excess: np.ndarray, own_excess: np.ndarray | None,
            candidate: np.ndarray, lower: np.ndarray) -> None:
        """One start: arrays over the judged rev. 6 rows of the stretch from that start."""
        excluded, violations = guarded_exclusion(candidate, lower)
        self.e_excluded += int(excluded.sum())
        self.guard_violations += int(violations.sum())
        kept = ~excluded
        if not kept.any():
            return
        raw = raw_excess[kept]
        failure = raw if own_excess is None else own_excess[kept]
        self.raw_over += int(np.sum(raw > EXCESS_LIMIT_N))
        self.over += int(np.sum(failure > EXCESS_LIMIT_N))
        self.worst_N = max(self.worst_N, float(raw.max()))
        if own_excess is not None:
            self.worst_own_N = max(self.worst_own_N, float(failure.max()))

    def record(self, rev6_over: int, rev6_worst_N: float) -> dict:
        def finite_or_none(value: float) -> float | None:
            return None if value == -math.inf else value

        return {"over_0p6kN": self.over, "max_excess_N": finite_or_none(self.worst_N),
                "over_0p6kN_rev6": rev6_over, "max_excess_N_rev6": finite_or_none(rev6_worst_N),
                "raw_over_0p6kN": self.raw_over, "e_excluded": self.e_excluded,
                "guard_violations": self.guard_violations,
                "max_own_excess_N": finite_or_none(self.worst_own_N)}


def t5(record: CaseRecord, criteria: str = DEFAULT_CRITERIA) -> dict:
    """Criteria rev. 6 4.4: per leg, stretch and start ``m``, that leg alone from ``m``;
    ``rev7`` applies the guarded E exclusion and B1 to every start (3)."""
    stepper, states = _stepper_with_states(record)
    judged = _judged(record)
    samples = rev7_samples(record, judged) if criteria == CRITERIA_REV7 else None
    legs = {}
    for leg, name in enumerate(LEGS):
        starts = over = 0
        worst = -math.inf
        tally = _Rev7StartTally()
        for first, last in command_free_stretches(record.acting_m_s[:, leg]):
            for start in range(first, last + 1):
                lower = _stepped_lower(stepper, states[start], leg, start, last)
                rows = [row for row in range(start, last + 1) if judged[row, leg]]
                starts += 1
                if not rows:
                    continue
                judged_lower = lower[[row - start for row in rows]]
                excess = judged_lower - record.truth_N[rows, leg]
                over += int(np.sum(excess > EXCESS_LIMIT_N))
                worst = max(worst, float(excess.max()))
                if samples is not None:
                    _add_rev7_start(tally, samples, record, judged_lower, excess, rows, leg)
        if samples is None:
            legs[name] = {"starts": starts, "over_0p6kN": over,
                          "max_excess_N": None if worst == -math.inf else worst}
        else:
            legs[name] = {"starts": starts, **tally.record(over, worst)}
    out = {"legs": legs, "over_0p6kN": sum(row["over_0p6kN"] for row in legs.values())}
    if samples is not None:
        out.update(_rev7_totals(legs, samples))
    return out


def _add_rev7_start(tally: _Rev7StartTally, samples: Rev7Samples, record: CaseRecord,
                    lower: np.ndarray, raw_excess: np.ndarray, rows: list[int],
                    leg: int) -> None:
    own = None
    if samples.is_sensor_model_row:
        plain_excess = samples.plain_lower_N[rows, leg] - record.truth_N[rows, leg]
        own = own_excess_N(raw_excess, plain_excess)
    tally.add(raw_excess, own, samples.excluded_candidate[rows, leg], lower)


def _stepped_lower(stepper: _MonitorStepper, state, leg: int, start: int,
                   last: int) -> np.ndarray:
    monitor = copy.deepcopy(state)
    monitor.rod_state[leg] = stepper.fallback_state
    return np.array([stepper.step(row, monitor)[leg] for row in range(start, last + 1)])


def t5_naive_check(record: CaseRecord, samples: int = 3, seed: int = 0) -> dict:
    """Spec R-6 #5: the copied-state T5 equals a full replay with the start forced."""
    stepper, states = _stepper_with_states(record)
    t_s = np.asarray(record.episode["t_s"], float)
    candidates = [(leg, start, last) for leg in range(len(LEGS))
                  for first, last in command_free_stretches(record.acting_m_s[:, leg])
                  for start in (first, (first + last) // 2)]
    rng = np.random.default_rng(seed)
    picks = [candidates[i] for i in rng.choice(len(candidates),
                                               size=min(samples, len(candidates)),
                                               replace=False)]
    worst = 0.0
    for leg, start, last in picks:
        stepped = _stepped_lower(stepper, states[start], leg, start, last)
        actual = [(t, name) for t, name in record.events]
        full = _replay(record, [(float(t_s[start]), f"{FALLBACK_EVENT}:{LEGS[leg]}")] + actual)
        worst = max(worst, float(np.max(np.abs(stepped - full[start:last + 1, leg]))))
    return {"compared": len(picks), "max_abs_difference_N": worst}


# ----------------------------------------------------------------------------- lift-off
def lift_times(t_ms: np.ndarray, normal_N: np.ndarray, period_t: np.ndarray,
               period_phase: np.ndarray, weight_N: float) -> dict:
    """D-a (criteria rev. 6 5): first 1 ms sample after the pre-lift phases with
    ``F_cr,n <= 0``; re-contacts after it, ``t_lift,sus`` and the false lift-off flag."""
    t_ms = np.asarray(t_ms, float)
    normal = np.asarray(normal_N, float)
    phases = _sample_phases(t_ms, period_t, period_phase)
    is_lifted = ~np.isin(phases, PRE_LIFT_PHASES) & (normal <= 0.0)
    if not is_lifted.any():
        return {"t_lift_s": None, "t_lift_basis": "1ms", "t_lift_sus_s": None,
                "relift_contacts": {"samples": 0, "max_N": None, "last_t_s": None},
                "false_liftoff": False}
    first = int(np.argmax(is_lifted))
    after = slice(first, None)
    contacts = np.flatnonzero(normal[after] > 0.0) + first
    threshold_N = SUSTAINED_LIFT_WEIGHT_FRACTION * weight_N
    above = np.flatnonzero(normal[after] > threshold_N) + first
    sustained_s = (float(t_ms[first]) if above.size == 0
                   else (float(t_ms[above[-1] + 1]) if above[-1] + 1 < len(t_ms) else None))
    return {"t_lift_s": float(t_ms[first]), "t_lift_basis": "1ms",
            "t_lift_sus_s": sustained_s,
            "relift_contacts": {"samples": int(contacts.size),
                                "max_N": float(normal[contacts].max()) if contacts.size else None,
                                "last_t_s": float(t_ms[contacts[-1]]) if contacts.size else None},
            "false_liftoff": _longest_run_s(t_ms, normal > threshold_N, first) > FALSE_LIFTOFF_S}


def _sample_phases(t_ms, period_t, period_phase) -> np.ndarray:
    """``verdict_metrics.chunk_phases`` rule on the 1 ms times."""
    import verdict_metrics
    from harness_flow import COLUMN

    rows = np.zeros((len(t_ms), max(COLUMN.values()) + 1))
    rows[:, COLUMN["t"]] = t_ms
    return np.asarray(verdict_metrics.chunk_phases(rows, np.asarray(period_t, float),
                                                   np.asarray(period_phase).astype(str)),
                      dtype=str)


def _longest_run_s(t_ms: np.ndarray, condition: np.ndarray, first: int) -> float:
    longest, start = 0.0, None
    for index in range(first, len(t_ms)):
        if condition[index] and start is None:
            start = index
        elif not condition[index] and start is not None:
            longest = max(longest, float(t_ms[index] - t_ms[start]))
            start = None
    if start is not None:
        longest = max(longest, float(t_ms[-1] - t_ms[start]))
    return longest


def bracket_lift_10hz(t_s: np.ndarray, crawler_N: np.ndarray, period_phase) -> dict:
    """D-a fallback without a 1 ms crawler record: last > 0 sample ``t_a`` and the first
    <= 0 sample ``t_b`` after the pre-lift phases; the split time is ``t_a + 1 ms``."""
    t_s = np.asarray(t_s, float)
    crawler = np.asarray(crawler_N, float)
    eligible = ~np.isin(np.asarray(period_phase).astype(str), PRE_LIFT_PHASES)
    lifted = np.flatnonzero(eligible & (crawler <= 0.0))
    if lifted.size == 0:
        return {"t_lift_s": None, "t_lift_basis": "bracket_10Hz", "t_a_s": None, "t_b_s": None}
    t_b_row = int(lifted[0])
    loaded = np.flatnonzero(crawler[:t_b_row] > 0.0)
    t_a = float(t_s[loaded[-1]]) if loaded.size else None
    return {"t_lift_s": None if t_a is None else t_a + 1e-3, "t_lift_basis": "bracket_10Hz",
            "t_a_s": t_a, "t_b_s": float(t_s[t_b_row])}


def lift_record(record: CaseRecord) -> dict:
    """The lift-off of the case: 1 ms (rigid ``pads.npz`` ``crawler_normal_N``, soil
    ``step_series.npz`` ``scm_crawler_normal_N``) or the 10 Hz bracket."""
    from outrigger_sim.params import load_params

    case_dir = record.case_dir
    level = (record.result.get("settings") or {}).get("level") or "top"
    weight_N = load_params(level=level).superstructure.mass_properties.mass_kg * GRAVITY_M_S2
    series_path = case_dir / ("s8_series.npz" if (case_dir / "s8_series.npz").is_file()
                              else "r8_series.npz")
    with np.load(series_path, allow_pickle=False) as series:
        period_t, period_phase = np.asarray(series["t"], float), np.asarray(series["phase"])
    normal = _one_ms_crawler(case_dir)
    if normal is not None:
        return lift_times(*normal, period_t, period_phase, weight_N)
    with np.load(case_dir / "record" / "record.npz", allow_pickle=False) as data:
        t_s, crawler = np.asarray(data["t"], float), np.asarray(data["F_crawler"], float)
    if crawler.ndim == 2:  # force vector: its component on the floor normal of the sample
        with np.load(case_dir / "pads.npz", allow_pickle=False) as pads:
            index, _ = align_truth(pads["t"], t_s)
            crawler = np.sum(crawler * np.asarray(pads["n_world"], float)[index], axis=1)
    return bracket_lift_10hz(t_s, crawler, _period_phase_at(t_s, period_t, period_phase))


def _period_phase_at(t_s, period_t, period_phase) -> np.ndarray:
    """Phase the controller ended the previous period with (``chunk_phases`` rule)."""
    return _sample_phases(np.asarray(t_s, float), period_t, period_phase)


def _one_ms_crawler(case_dir: Path):
    with np.load(case_dir / "pads.npz", allow_pickle=False) as pads:
        if "crawler_normal_N" in pads.files:
            return np.asarray(pads["t"], float), np.asarray(pads["crawler_normal_N"], float)
    step_path = case_dir / "step_series.npz"
    if step_path.is_file():
        with np.load(step_path, allow_pickle=False) as steps:
            if "scm_crawler_normal_N" in steps.files:
                return (np.asarray(steps["t_s"], float),
                        np.asarray(steps["scm_crawler_normal_N"], float))
    return None


# ------------------------------------------------------------------------- M2 records
def clip_record(hydraulics: dict, lift: dict) -> dict:
    """Clip split at the lift-off (harness function) and the clips inside the lift transient."""
    from harness_hydraulics import clipped_steps_by_lift

    times = hydraulics.get("m2_clip_times_s")
    if times is None:
        return {}
    split = clipped_steps_by_lift(times, hydraulics["m2_clipped_steps"], lift.get("t_lift_s"))
    t_lift, t_sus = lift.get("t_lift_s"), lift.get("t_lift_sus_s")
    if t_lift is not None and t_sus is not None:
        split["m2_clipped_steps_in_lift_transient"] = sum(
            1 for leg_times in times for t in leg_times if t_lift <= t <= t_sus)
    if lift.get("t_lift_basis") == "bracket_10Hz" and lift.get("t_b_s") is not None:
        split["m2_clipped_steps_unresolved"] = sum(
            1 for leg_times in times for t in leg_times if lift["t_a_s"] < t < lift["t_b_s"])
    return split


def release_judgements(hydraulics: dict, params, head_area_m2) -> dict:
    """H-b judgement of every release entry (``m2_release_log.judge_release``)."""
    from outrigger_sim.chrono.m2_release_log import judge_release

    rod_side = params.l2b.rod_side
    beta = params.l2b.actuator.oil_bulk_modulus_eff_Pa  # L2b block (L1 Actuator has no beta)
    rows = []
    for entry in hydraulics.get("m2_releases") or []:
        leg = int(entry["leg"])
        rows.append(judge_release(entry, float(rod_side.annulus_area_m2[leg]),
                                  float(head_area_m2[leg]), beta))
    flags = sorted({flag for row in rows for flag in row["flags"]})
    return {"releases": rows, "flags": flags}


def ext_lock_counters(hydraulics: dict, params) -> dict:
    """Criteria rev. 6 4.5 from the released locks of ``m2_releases`` (a lock still held at the
    run end has no entry): a lock whose anchor is not ``p_ret`` followed an extension; excess =
    ``p_r0 - p_ext``; ``dF_knee = (p_r0 - p_floor) A_ann (k_h + k_r) / k_r`` with ``k_h`` of the
    release and ``k_r = beta A_ann / (L0r + s_max - s_ref,rel)``."""
    rod_side = params.l2b.rod_side
    beta = params.l2b.actuator.oil_bulk_modulus_eff_Pa
    floor_Pa = rod_side.p_floor_abs_Pa - 101325.0
    counts = {key: [0] * len(LEGS) for key in ("ext_lock_count", "ext_lock_excess_count",
                                               "ext_lock_risk_count")}
    excess_max = [0.0] * len(LEGS)
    knee_max = [0.0] * len(LEGS)
    for entry in hydraulics.get("m2_releases") or []:
        leg = int(entry["leg"])
        anchor = float(entry["p_r0_Pa"])
        if abs(anchor - rod_side.p_r0_after_retract_Pa[leg]) <= ANCHOR_MATCH_PA:
            continue
        excess = anchor - rod_side.p_r0_after_extend_Pa[leg]
        annulus = float(rod_side.annulus_area_m2[leg])
        rod_column = (rod_side.rod_dead_length_m[leg] + rod_side.stroke_m
                      - float(entry["s_ref_rel_m"]))
        k_r = beta * annulus / rod_column
        k_h = float(entry["k_h_at_rel_N_m"])
        knee_N = (anchor - floor_Pa) * annulus * (k_h + k_r) / k_r
        counts["ext_lock_count"][leg] += 1
        counts["ext_lock_excess_count"][leg] += int(excess > EXT_LOCK_EXCESS_PA)
        counts["ext_lock_risk_count"][leg] += int(excess > EXT_LOCK_RISK_PA)
        excess_max[leg] = max(excess_max[leg], excess / 1e5)
        knee_max[leg] = max(knee_max[leg], knee_N / 1e3)
    return {**counts, "ext_lock_excess_max_bar": excess_max, "ext_lock_knee_max_kN": knee_max,
            "ext_lock_basis": "released locks of m2_releases"}


# --------------------------------------------------------------------------------- driver
def replay_case(case_dir: Path, *, with_t5: bool = False,
                extend_start: str | None = None, criteria: str = DEFAULT_CRITERIA) -> dict:
    """All values of one case folder (module docstring); ``criteria`` picks the T4 / T5
    judgement (``rev6`` or ``rev7``)."""
    from outrigger_sim.control.extend_start_bound import check_extend_start_meta
    from outrigger_sim.control.r5_fallback_replay import monitor_setting_differences
    from outrigger_sim.params import load_params

    record = load_case(case_dir, extend_start)
    stored_settings = record.result["controller_meta"]["two_pressure"]["settings"]
    check_extend_start_meta(stored_settings)
    differences, notes = monitor_setting_differences(record.result["controller_meta"],
                                                     record.config, record.geometry)
    # an override of another rule changes only the ③ start keys; the same rule compares them
    # all, the bound revision included
    stored_rule = stored_settings.get("extend_start_rule", "constant")
    if extend_start is not None and extend_start != stored_rule:
        differences = [d for d in differences if ".extend_start_" not in d]
    replay_settings = record.config.two_pressure.to_meta()
    row = {"case": Path(case_dir).name, "settings_equal": not differences,
           "setting_differences": differences, "setting_notes": notes,
           "extend_start_rule": extend_start,
           # key only for a run with a ③ rule (the rows of ③-off runs stay as they were)
           **({} if "extend_start_rule" not in stored_settings
              else {"run_extend_start_rule": stored_rule}),
           "extend_start_revision": (replay_settings.get("extend_start_bound") or {}).get(
               "revision"),
           # criteria revision 9 (j_p3_inputs): a VB / LS run must be in J-P3
           "p3_expected": is_p3_expected(run_controller_tag(record.result), None)}
    if differences:
        return row
    row.update(t4_0(record))
    if not row["t4_0"]:
        return row
    row["T4"] = t4(record, criteria)
    if with_t5:
        row["T5"] = t5(record, criteria)
    lift = lift_record(record)
    row["lift"] = lift
    hydraulics = record.result.get("hydraulics_record") or {}
    if hydraulics:
        level = (record.result.get("settings") or {}).get("level") or "top"
        params = load_params(level=level, model="L2b_NSC")
        row["m2_clip_split"] = clip_record(hydraulics, lift)
        row["m2_release_judgement"] = release_judgements(hydraulics, params,
                                                         record.geometry.head_area_m2)
        row["ext_lock"] = ext_lock_counters(hydraulics, params)
        # premise ① truth of the ③ bound (tension_premise.md S-2; None before it was recorded)
        row["tension_truth"] = hydraulics.get("tension_truth")
        row["extend_bound_check"] = hydraulics.get("extend_bound_check")
    return row


def case_folders(paths: list[str]) -> list[Path]:
    """Case folders (with ``result.json``), or the case folders of a batch folder."""
    folders = []
    for path in map(Path, paths):
        if (path / "result.json").is_file():
            folders.append(path)
        else:
            folders += sorted(p for p in path.iterdir() if (p / "result.json").is_file())
    return folders


def summary(rows: list[dict]) -> dict:
    judged = [row for row in rows if row.get("t4_0")]
    over_t4 = sum(row["T4"]["over_0p6kN"] for row in judged)
    over_t5 = sum(row["T5"]["over_0p6kN"] for row in judged if "T5" in row)
    risk = sum(sum(row["ext_lock"]["ext_lock_risk_count"]) for row in judged
               if "ext_lock" in row)
    return {"rows": len(rows), "settings_equal": sum(row["settings_equal"] for row in rows),
            "t4_0_passed": len(judged), "T4_over_0p6kN": over_t4, "T5_over_0p6kN": over_t5,
            "ext_lock_risk_count": risk,
            "tension_truth_substeps_over_margin": sum(
                sum(row["tension_truth"]["substeps_over_margin"]) for row in judged
                if row.get("tension_truth")),
            # ③ judgement (tension_premise.md 5.4): breach sum 0 passes, margin use is a FLAG
            "extend_bound_breach_reads": sum(
                sum(row["extend_bound_check"]["breach_reads"]) for row in judged
                if row.get("extend_bound_check")),
            "extend_bound_margin_used_reads": sum(
                sum(row["extend_bound_check"]["margin_used_reads"]) for row in judged
                if row.get("extend_bound_check")),
            # locked legs: judged by T4 (③-on setting); the online ④ check is a FLAG (6.3)
            "extend_bound_locked_over_tol_reads": sum(
                sum(row["extend_bound_check"].get("locked_breach_over_tol_reads", []))
                for row in judged if row.get("extend_bound_check")),
            "anchor_note": "앵커 위험 미관측" if risk == 0 else "앵커 위험 관측"}


def recorded_liftoff_slow(result: dict) -> bool:
    """LAS-b of the recorded run (switch 2026-11-08): on when its controller meta has the block
    on or its tag ends with ``_LAS``; a run before the switch has neither and replays it off."""
    from outrigger_sim.hydraulics.v5_options import is_liftoff_slow_tag

    block = ((result.get("controller_meta") or {}).get("liftoff_approach_slow") or {})
    if (block.get("settings") or {}).get("enable"):
        return True
    expected = ((result.get("c2_setup") or {}).get("expect_controller") or {}).get("name")
    return is_liftoff_slow_tag(run_controller_tag(result)) or is_liftoff_slow_tag(expected)


def recorded_order_gate(result: dict) -> bool:
    """LAS-b K1 order gate of the recorded run (K1 switch, ``las_k1_rules_adopt.md`` 9.2): on
    when its controller meta has ``slope_clearance_margin.settings.flat_soil_margin_order_gate``
    on or its tag ends with ``_K1``; a run before the switch has neither and replays it off."""
    from outrigger_sim.hydraulics.v5_options import is_order_gate_tag

    margin = (result.get("controller_meta") or {}).get("slope_clearance_margin") or {}
    if (margin.get("settings") or {}).get("flat_soil_margin_order_gate"):
        return True
    expected = ((result.get("c2_setup") or {}).get("expect_controller") or {}).get("name")
    return is_order_gate_tag(run_controller_tag(result)) or is_order_gate_tag(expected)


def run_controller_tag(result: dict) -> str | None:
    """Controller tag a Chrono run recorded (``v5_hydraulics.controller_tag``, criteria
    revision 8 3.1; a top-level ``controller_tag`` is read too)."""
    return result.get("controller_tag") or (result.get("v5_hydraulics") or {}).get(
        "controller_tag")


def j_p3_of(rows: list[dict]) -> dict:
    """Criteria revision 8 3.2 with the revision 9 table (rev7 reports): every VB / LS row
    (tag ``final_C4G2_P3``) or ``tracked_bound`` row; a VB / LS row without the own rule is a
    setting defect. Chrono reads both pressures: every row counts as having rod readings, so
    a null record is a defect (revision 9 3.2 #2 / #4)."""
    return j_p3_over_rows(rows)


def rev7_summary(rows: list[dict]) -> dict:
    """Criteria rev. 7 3.4 totals over the rows (added to ``summary`` under ``rev7``)."""
    judged = [row for row in rows if row.get("t4_0")]

    def total(test: str, key: str) -> int:
        return sum(row[test][key] for row in judged if test in row)

    def largest(test: str, key: str) -> float | None:
        values = [row[test][key] for row in judged
                  if test in row and row[test][key] is not None]
        return max(values) if values else None

    judged_samples = total("T4", "judged_samples")
    excluded = total("T4", "e_excluded")
    return {"T4_judged_samples_rev6": total("T4", "judged_samples_rev6"),
            "T4_judged_samples": judged_samples, "T4_e_excluded": excluded,
            "T4_e1_to_e4_samples": total("T4", "e1_to_e4_samples"),
            "T4_over_0p6kN_rev6": total("T4", "over_0p6kN_rev6"),
            "T4_raw_over_0p6kN": total("T4", "raw_over_0p6kN"),
            "T4_guard_violations": total("T4", "guard_violations"),
            "T4_check_precal_grounded": total("T4", "check_precal_grounded"),
            "T4_max_own_excess_N": largest("T4", "max_own_excess_N"),
            "T5_over_0p6kN_rev6": total("T5", "over_0p6kN_rev6"),
            "T5_raw_over_0p6kN": total("T5", "raw_over_0p6kN"),
            "T5_e_excluded": total("T5", "e_excluded"),
            "T5_guard_violations": total("T5", "guard_violations"),
            "T5_max_own_excess_N": largest("T5", "max_own_excess_N"),
            "sensor_model_rows": sum(row["T4"]["sensor_model"] for row in judged),
            "sample_note": (f"개정 7 판정 표본(E 제외 {judged_samples:,}, "
                            f"제외 표본 {excluded:,})")}


def report_of(rows: list[dict], criteria: str, extend_start: str | None) -> dict:
    """The output document; the rev. 6 document is the tool's original one."""
    # criteria revision 8 2 #3 / #4: the run's own (or a tracked_bound) setting is T4, the
    # ③-off override is the record T4-const
    record = "T4-const" if extend_start == "constant" else "T4"
    if criteria == CRITERIA_REV6:
        return {"rule": "criteria rev. 6 4 (T4-0, T4, T5) and 5 / 7 records",
                "record": record, "summary": summary(rows), "rows": rows}
    return {"rule": ("criteria rev. 7 3 (E exclusion, guard, B1) on rev. 6 4 (T4-0, T4, T5) "
                     "and 5 / 7 records"),
            "criteria": CRITERIA_REV7, "record": record,
            "summary": {**summary(rows), "criteria": CRITERIA_REV7,
                        "rev7": rev7_summary(rows), "J-P3": j_p3_of(rows)},
            "rows": rows}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line of ``main`` (``argv`` None reads ``sys.argv``)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json")
    parser.add_argument("cases", nargs="+", help="case folders or batch folders")
    parser.add_argument("--t5", action="store_true")
    parser.add_argument("--extend-start", choices=("constant", "tracked_bound"), default=None,
                        help="override the ③ start rule (constant: record T4-const)")
    parser.add_argument("--criteria", choices=(CRITERIA_REV6, CRITERIA_REV7),
                        default=DEFAULT_CRITERIA,
                        help=("T4 / T5 judgement revision (default rev7: E exclusion, guard, "
                              "B1; rev6 reproduces the stage 3 judgement)"))
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    rows = [replay_case(folder, with_t5=args.t5, extend_start=args.extend_start,
                        criteria=args.criteria)
            for folder in case_folders(args.cases)]
    report = report_of(rows, args.criteria, args.extend_start)
    Path(args.out_json).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps(report["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
