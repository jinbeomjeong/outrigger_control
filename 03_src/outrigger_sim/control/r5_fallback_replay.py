"""V-2 replay of the R-5 fallback slope on one Chrono record (P-S8-22, O-4).

``00_docs/04_control/s6_control_spec.md`` rev. 61 303 V-2 with the control decisions O-4
(2026-10-26). The replay itself is :mod:`outrigger_sim.control.contact_replay`; this module adds
what a judgement on the result needs:

1. **Probed leg per update** (watch time: the leg ``C2Controller._probed_leg`` returns at the R-5
   check of update ``k``), first source that has it, recorded per row in ``probed_leg_source``:

   * ``record``: the runner's 10 Hz ``probed_leg`` (``r8_series.npz``, after the update),
   * ``history``: a finished round of ``probe_history.json`` (leg ``j`` from the row after the
     previous leg's second hold end to its own),
   * ``command``: an aborted round (not in the history): the leg the probe moves, i.e. the
     largest ``|computed_u|`` of each PROBE update that stays in PROBE, carried over the holds;
     a round without such an update has no probed leg (``none``, every leg watched).

   ``command`` is used only when it agrees with ``history`` on every row of every finished round
   of the run, and a round it decides must not have its probed leg equal to the leg of the
   ``probe_aborted_low_load:<leg>`` that ended it (the controller never watches the probed leg).
2. **Gate** (:class:`GateKind`): only when the replay reproduces the run do its ``nominal_gap``
   replays count.

   * ``level`` (a run with the ``level`` rule or R-5 off, i.e. before P-S8-22): the ``level``
     replay gives the controller's ``relevel_predicted:<leg>`` and
     ``probe_aborted_low_load:<leg>`` at the same rows and legs.
   * ``same_run`` (a run that ran ``nominal_gap``; spec rev. 62 316 "같은 실행 관문", 316.6
     D-4, an ASSUMPTION of control 317 (1)): the replay of the run's own
     ``fallback_ratio_source`` gives those events and every ``INFO_R5_FALLBACK_SLOPE``
     (time, leg, ``D`` and gap to the event's 0.01 kN). The ``level`` replay of such a run is
     a record (``level_gate``, ``role`` ``record``).
3. **Monitor inputs**: the E-6 deduction from the run meta (missing with a failed calibration:
   not replayable; missing without one: 0, noted); the replay's two-pressure settings equal the
   run's ``controller_meta.two_pressure.settings`` field by field (only the P-S8-22 keys of
   ``r8.fast_relevel`` may differ, noted; keys that are no setting, e.g. cad C-1's
   ``fallback_plant_ratio_source``, are records, noted); the fallback is forced at the run's
   events (the monitor's own diagnosis is not replayed, noted).
4. **Optimism record** (P-1): per fallback-leg row the watch phase, whether R-5 watches the
   leg there (READY, or PROBE on a leg not being probed), the 302.2 condition (``met`` /
   ``moving`` / ``short`` / ``other``), the replayed prediction ``L_hat_fb`` and the R-5
   prediction a healthy rod sensor would have given, ``L_hat_true`` (truth at ``t_k`` minus the
   band ``b`` of the healthy legs, over the controller's ``n`` and ``h``), and whether the healthy
   R-5 fires (all three conditions) where the fallback one does not (a missed trigger). Truth
   (``true_force_source``): ``pads.npz`` ``F_pressure`` (two-sensor net force); without it
   ``F_cyl`` only for a run with ``F_s = 0`` (``F_cyl_no_friction``), else not replayable.
   ``F_s`` comes from the episode meta, else from cad C-2's record
   ``settings.bundle_c.pads_seal_fields`` (316.6 D-2), else 0 for L1. The engine (allowance)
   comes from the episode meta, ``settings.s8.engine``, ``settings.s7c.engine`` (D-3) or the
   case id prefix. Row
   classes (:class:`RowClass`): ``judged_falling`` (watched ``nominal_gap`` rows with
   ``Dh >= 0``), ``record_rising``, ``record_level``, ``unwatched``. The one official verdict
   ``judgement_passed`` (control decision 2026-10-26): the ``judged_falling`` optimism within the
   allowance (L1 0.05 kN, L2b 1.2 kN) and no missed trigger on the watched rows that meet 302.2
   (``judged_falling`` + ``record_rising``); a missed trigger on a ``record_level`` row only
   sets ``level_missed_trigger_flag``; the rest is recorded.

Units SI; per-leg arrays follow ``LEG_ORDER``; times are controller times (``record.npz`` ``t``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import (
    LEG_COUNT,
    LEG_NAMES,
    MachineConstants,
    build_episode,
    read_controller_events,
)
from outrigger_sim.control.c2 import FALLBACK_SLOPE_EVENT, C2Config, C2Geometry, C2Phase
from outrigger_sim.control.contact_replay import (
    FAST_RELEVEL_SETTING_KEYS,
    ActionKind,
    Judge,
    ReplayInput,
    ReplaySettings,
    replay_fallback_monitor,
    replay_judge,
)

# Record-only allowances of L_hat_fb - L_hat_true (control O-4, 2026-10-26).
OPTIMISM_ALLOWANCE_L1_N = 50.0
OPTIMISM_ALLOWANCE_L2B_N = 1200.0
PADS_TIME_TOLERANCE_S = 5e-4
"""The 1 ms truth sample used for ``t_k`` must lie within half a millisecond of it."""
TIME_KEY_DECIMALS = 6
P_S8_22_FAST_RELEVEL_KEYS = frozenset({
    "fallback_slope",
    "fallback_ratio_source",
    "fallback_nominal_head_dead_m",
    "fallback_nominal_rod_dead_m",
    "fallback_plant_ratio",
})
MONITOR_META_KEYS = (
    "fallback_lock_stroke_max_m",
    "fallback_lock_retract_floor_Pa",
    "head_area_m2",
    "annulus_area_m2",
    "rod_weight_N",
)
"""Monitor values resolved from the YAML at construction, compared with the run's meta."""
RELEVEL_EVENT = "relevel_predicted"
PROBE_ABORT_EVENT = "probe_aborted_low_load"
ZERO_CALIBRATION_WARNING_PREFIX = "WARN_PRESSURE_ZERO"
RECORDED_PROBED_LEG_KEY = "probed_leg"
"""ASSUMPTION: the runner's 10 Hz key holds ``C2Controller._probed_leg()`` after the update
(-1 = none), the episode convention."""
PADS_SEAL_FIELDS_KEY = "pads_seal_fields"
"""cad C-2 record in ``settings.bundle_c``: ``F_s_front_N`` and ``friction_path`` of the run."""
ENGINE_SETTING_PATHS = (("s8", "engine"), ("s7c", "engine"))
"""Where S8 / S7 runner settings state the engine (spec rev. 62 316.6 D-3), in this order."""
SLOPE_VALUE_FORMAT = ".2f"
"""``INFO_R5_FALLBACK_SLOPE`` values: kN with two decimals (``FallbackSlopeReport``)."""


class ProbedLegSource(StrEnum):
    NOT_PROBE = ""
    RECORD = "record"
    HISTORY = "history"
    COMMAND = "command"
    NONE = "none"
    """An aborted round without a probe move: no probed leg, every leg watched."""


@dataclass
class ProbedLegTrack:
    """Watch-time probed leg per row and where it came from."""

    legs: NDArray[np.int64]
    sources: NDArray[np.str_]
    command_history_match: float | None = None
    """Share of the finished-round rows on which ``command`` equals ``history``."""
    problems: list[str] = field(default_factory=list)


def _probe_stays(is_probe: NDArray[np.bool_]) -> list[tuple[int, int]]:
    """``[start, stop)`` row ranges of consecutive watch-time PROBE rows."""
    stays = []
    row = 0
    while row < is_probe.size:
        if not is_probe[row]:
            row += 1
            continue
        start = row
        while row < is_probe.size and is_probe[row]:
            row += 1
        stays.append((start, row))
    return stays


def _history_legs(t_s, stays, probe_history) -> NDArray[np.int64]:
    """``history`` source (-9 = no finished round covers the row)."""
    legs = np.full(t_s.size, -9, dtype=np.int64)
    for results in probe_history:
        ends = sorted((float(result["t_second_hold_end_s"]), int(result["leg_index"]))
                      for result in results if result.get("t_second_hold_end_s") is not None)
        if not ends:
            continue
        stay = next(((start, stop) for start, stop in stays
                     if t_s[start] - 1e-6 <= ends[0][0] <= t_s[stop - 1] + 1e-6), None)
        if stay is None:
            continue
        previous_end_s = -np.inf
        rows = np.arange(*stay)
        for end_s, leg in ends:
            covered = rows[(t_s[rows] > previous_end_s + 1e-6) & (t_s[rows] <= end_s + 1e-6)]
            legs[covered] = leg
            previous_end_s = end_s
    return legs


def _command_legs(stays, computed_u, phase_after) -> NDArray[np.int64]:
    """``command`` source: the leg of the largest ``|computed_u|`` of each update that stays in
    PROBE, carried over the holds of the round (-1 before the first move)."""
    legs = np.full(computed_u.shape[0], -1, dtype=np.int64)
    for start, stop in stays:
        current = -1
        for row in range(start, stop):
            speeds = np.abs(computed_u[row])
            if phase_after[row] == C2Phase.PROBE.value and speeds.max() > 0.0:
                current = int(speeds.argmax())
            legs[row] = current
    return legs


def probed_leg_track(
    t_s: NDArray[np.float64],
    phase_after: NDArray[np.str_],
    computed_u: NDArray[np.float64],
    probe_history: Sequence[Sequence[Mapping[str, Any]]],
    events: Sequence[tuple[float, str]],
    recorded_after: NDArray[np.int64] | None = None,
) -> ProbedLegTrack:
    """Watch-time probed leg per row (module docstring, 1).

    Args:
        t_s: Row times (n,).
        phase_after: C2 phase after each update (n,).
        computed_u: Computed (not yet delayed) leg commands per update (n, 4).
        probe_history: ``probe_history.json`` (finished rounds).
        events: Controller events (``read_controller_events``).
        recorded_after: The runner's probed leg after each update, when recorded.
    """
    phase_after = np.asarray(phase_after).astype(str)
    watch_phase = np.concatenate(([""], phase_after[:-1]))
    is_probe = watch_phase == C2Phase.PROBE.value
    stays = _probe_stays(is_probe)
    legs = np.full(t_s.size, -1, dtype=np.int64)
    sources = np.full(t_s.size, ProbedLegSource.NOT_PROBE.value, dtype="U8")
    if recorded_after is not None:
        recorded = np.concatenate(([-1], np.asarray(recorded_after, dtype=np.int64)[:-1]))
        legs[is_probe] = recorded[is_probe]
        sources[is_probe] = ProbedLegSource.RECORD.value
        track = ProbedLegTrack(legs, sources)
        _check_abort_consistency(track, t_s, events)
        return track
    history = _history_legs(t_s, stays, probe_history)
    command = _command_legs(stays, np.asarray(computed_u, dtype=float), phase_after)
    is_finished = history != -9
    track = ProbedLegTrack(legs, sources)
    if is_finished.any():
        track.command_history_match = float(np.mean(command[is_finished] == history[is_finished]))
    for start, stop in stays:
        rows = np.arange(start, stop)
        if is_finished[rows].all():
            legs[rows], sources[rows] = history[rows], ProbedLegSource.HISTORY.value
            continue
        legs[rows] = command[rows]
        sources[rows] = np.where(command[rows] >= 0, ProbedLegSource.COMMAND.value,
                                 ProbedLegSource.NONE.value)
    uses_command = bool(np.any(sources == ProbedLegSource.COMMAND.value))
    if uses_command and track.command_history_match is None:
        track.problems.append("command source unverified: no finished round in the run")
    elif uses_command and track.command_history_match < 1.0:
        track.problems.append(
            f"command source disagrees with the finished rounds "
            f"(match {track.command_history_match:.4f})")
    _check_abort_consistency(track, t_s, events)
    return track


def _check_abort_consistency(track: ProbedLegTrack, t_s, events) -> None:
    """The leg of ``probe_aborted_low_load:<leg>`` is never the probed one (it is not watched)."""
    for time_s, name in events:
        prefix, _, leg_name = name.partition(":")
        if prefix != PROBE_ABORT_EVENT or leg_name not in LEG_NAMES:
            continue
        row = int(np.argmin(np.abs(t_s - time_s)))
        if track.legs[row] == LEG_NAMES.index(leg_name):
            track.problems.append(
                f"probed leg {leg_name} ({track.sources[row]}) at {time_s:.2f} s is the leg "
                "that aborted the probe")


# --- gate, inputs, optimism -------------------------------------------------------------------


def _event_key(time_s: float, leg: int) -> tuple[float, int]:
    return round(float(time_s), TIME_KEY_DECIMALS), leg


def controller_r5_events(events: Sequence[tuple[float, str]]) -> dict[str, list[tuple]]:
    """The run's R-5 re-levels and probe aborts as ``(t_s, leg)``."""
    found: dict[str, list[tuple]] = {RELEVEL_EVENT: [], PROBE_ABORT_EVENT: []}
    for time_s, name in events:
        prefix, _, leg_name = name.partition(":")
        if prefix in found and leg_name in LEG_NAMES:
            found[prefix].append(_event_key(time_s, LEG_NAMES.index(leg_name)))
    return found


def replay_r5_events(replay, inputs: ReplayInput) -> dict[str, list[tuple]]:
    """The replay's R-5 re-levels, and its probe aborts: every P5 / R-5 action on a PROBE row."""
    row_of_time = {round(float(t), 9): row for row, t in enumerate(inputs.t_s)}
    found: dict[str, list[tuple]] = {RELEVEL_EVENT: [], PROBE_ABORT_EVENT: []}
    for event in replay.events:
        if event.kind not in (ActionKind.R5, ActionKind.P5):
            continue
        key = _event_key(event.t_s, event.leg)
        if event.kind is ActionKind.R5:
            found[RELEVEL_EVENT].append(key)
        row = row_of_time[round(event.t_s, 9)]
        if str(inputs.watch_phase[row]) == C2Phase.PROBE.value:
            found[PROBE_ABORT_EVENT].append(key)
    return found


SlopeEventKey = tuple[float, str, str, str]
"""``(t_s, leg name, D_kN, gap_kN)`` of an ``INFO_R5_FALLBACK_SLOPE``, values as the event's
text (two decimals)."""


def controller_fallback_slope_events(events: Sequence[tuple[float, str]]) -> list[SlopeEventKey]:
    """The run's ``INFO_R5_FALLBACK_SLOPE:<leg>:<D_kN>:<gap_kN>`` events."""
    found = []
    for time_s, name in events:
        prefix, _, rest = name.partition(":")
        if prefix != FALLBACK_SLOPE_EVENT:
            continue
        leg_name, drop_kN, gap_kN = rest.split(":")
        found.append((round(float(time_s), TIME_KEY_DECIMALS), leg_name, drop_kN, gap_kN))
    return found


def replay_fallback_slope_events(
    slope_events: Sequence[tuple[float, str, Sequence[float]]],
) -> list[SlopeEventKey]:
    """A variant's ``fallback_slope_events`` formatted as the controller writes them."""
    return [
        (round(float(time_s), TIME_KEY_DECIMALS), leg_name,
         format(float(values_kN[0]), SLOPE_VALUE_FORMAT),
         format(float(values_kN[1]), SLOPE_VALUE_FORMAT))
        for time_s, leg_name, values_kN in slope_events
    ]


class GateKind(StrEnum):
    """Which replay must reproduce the run (module docstring, 2)."""

    LEVEL = "level"
    SAME_RUN = "same_run"


def run_own_slope_source(run: ReplaySettings) -> str | None:
    """``fallback_ratio_source`` of a run that ran ``nominal_gap``; ``None`` = ``level`` rule or
    R-5 off (the ``level`` gate applies)."""
    fast = run.fast_relevel
    if fast is None or not fast.uses_fallback_slope:
        return None
    return str(fast.fallback_ratio_source)


def same_run_gate(
    variant: Mapping[str, Any],
    controller_r5: Mapping[str, list[tuple]],
    controller_slope: Sequence[SlopeEventKey],
) -> dict[str, Any]:
    """Same-run gate on the variant of the run's own source: its R-5 re-levels, probe aborts
    and ``INFO_R5_FALLBACK_SLOPE`` events equal the controller's."""
    replayed_slope = replay_fallback_slope_events(variant["fallback_slope_events"])
    is_r5_equal = variant["r5_events"] == controller_r5
    is_slope_equal = replayed_slope == list(controller_slope)
    # Counts may differ (reported separately); the first differing pair is a pointer only.
    paired = zip(replayed_slope, controller_slope, strict=False)
    first_difference = next(
        ((replayed, recorded) for replayed, recorded in paired if replayed != recorded), None)
    return {
        "passed": is_r5_equal and is_slope_equal,
        "r5_equal": is_r5_equal,
        "fallback_slope_equal": is_slope_equal,
        "controller_fallback_slope_count": len(controller_slope),
        "replay_fallback_slope_count": len(replayed_slope),
        "first_fallback_slope_difference": first_difference,
    }


def _normalized(value: Any) -> Any:
    return json.loads(json.dumps(value))


def monitor_setting_differences(
    run_meta: Mapping[str, Any], config: C2Config, geometry: C2Geometry
) -> tuple[list[str], list[str]]:
    """(differences, notes): the replay's two-pressure settings and resolved monitor values
    against the run's ``controller_meta``; ``r8.fast_relevel`` settings other than P-S8-22's.
    Record-only ``r8.fast_relevel`` keys (no setting) are notes."""
    differences, notes = [], []
    run_monitor = run_meta["two_pressure"]
    run_settings = run_monitor["settings"]
    replay_settings = _normalized(config.two_pressure.to_meta())
    for key in sorted(set(run_settings) | set(replay_settings)):
        if run_settings.get(key, "<missing>") != replay_settings.get(key, "<missing>"):
            differences.append(f"two_pressure.settings.{key}: run {run_settings.get(key)!r} "
                               f"replay {replay_settings.get(key)!r}")
    replay_values = {
        "fallback_lock_stroke_max_m": geometry.stroke_max_m,
        "fallback_lock_retract_floor_Pa": list(geometry.rod_lock_pressure_after_retract_Pa),
        "head_area_m2": list(geometry.head_area_m2),
        "annulus_area_m2": list(geometry.annulus_area_m2),
        "rod_weight_N": list(geometry.rod_weight_N),
    }
    for key in MONITOR_META_KEYS:
        if key in run_monitor and not np.allclose(run_monitor[key], replay_values[key],
                                                  rtol=1e-12, atol=0.0):
            differences.append(f"two_pressure.{key}: run {run_monitor[key]!r} "
                               f"replay {replay_values[key]!r}")
    run_fast = run_meta["r8"].get("fast_relevel") or {}
    replay_fast = _normalized(config.r8.fast_relevel.to_meta())
    for key in sorted(set(run_fast) | set(replay_fast)):
        if run_fast.get(key, "<missing>") == replay_fast.get(key, "<missing>"):
            continue
        if key not in FAST_RELEVEL_SETTING_KEYS:  # cad C-1 records (316.6 D-1), not settings
            notes.append(f"r8.fast_relevel.{key}: run {run_fast.get(key)!r} "
                         "(record-only key, ignored by the replay)")
        elif key in P_S8_22_FAST_RELEVEL_KEYS:
            notes.append(f"r8.fast_relevel.{key}: run {run_fast.get(key)!r} "
                         f"replay {replay_fast.get(key)!r} (P-S8-22 key)")
        else:
            differences.append(f"r8.fast_relevel.{key}: run {run_fast.get(key)!r} "
                               f"replay {replay_fast.get(key)!r}")
    return differences, notes


@dataclass(frozen=True)
class OffsetAllowance:
    """E-6 deduction of the replay (``deduction_N`` ``None`` = not replayable)."""

    deduction_N: NDArray[np.float64] | None
    from_s: float | None
    """Calibration end, from which the controller deducted it (``None`` = per-leg
    calibration rows; no deduction without one)."""
    note: str


def offset_allowance(
    run_meta: Mapping[str, Any], events: Sequence[tuple[float, str]]
) -> OffsetAllowance:
    """E-6 deduction from the run meta (module docstring, 3)."""
    calibration = run_meta.get("zero_calibration") or {}
    allowance = calibration.get("pressure_offset_allowance_N")
    result = calibration.get("result") or {}
    if allowance is not None:
        deduction = np.asarray(allowance, dtype=float)
        end_s = result.get("t_end_s")
        if np.any(deduction != 0.0) and end_s is None:
            return OffsetAllowance(None, None, "nonzero E-6 deduction without a calibration "
                                   "end time: its start is not known")
        return OffsetAllowance(deduction, end_s, "E-6 deduction from the run meta")
    legs = result.get("legs") or []
    has_failure = any(leg.get("status") != "calibrated" for leg in legs if leg) or any(
        name.startswith(ZERO_CALIBRATION_WARNING_PREFIX) for _, name in events)
    if has_failure:
        return OffsetAllowance(None, None, "E-6 deduction missing from the meta with a failed "
                               "zero calibration")
    return OffsetAllowance(np.zeros(LEG_COUNT), None,
                           "E-6 deduction missing from the meta, no failed calibration: 0")


def optimism_allowance_N(engine: str | None) -> float | None:
    """Record-only allowance of the engine (``None`` = engine unknown)."""
    if engine is None:
        return None
    if engine.upper().startswith("L2B"):
        return OPTIMISM_ALLOWANCE_L2B_N
    if engine.upper().startswith("L1"):
        return OPTIMISM_ALLOWANCE_L1_N
    return None


class TrueForceSource(StrEnum):
    F_PRESSURE = "F_pressure"
    """``pads.npz`` ``F_pressure``: the two-sensor net force truth (S8 L2b pad record)."""
    F_CYL_NO_FRICTION = "F_cyl_no_friction"
    """``F_cyl`` of a run without seal friction (``F_s = 0``): equal to the pressure force."""


class SlopeCondition(StrEnum):
    """302.2 conditions of a fallback-leg row (``met`` = the monitor gave R-5 inputs)."""

    MET = "met"
    MOVING = "moving"
    """The leg's acting command is not zero this period."""
    SHORT = "short"
    """The lock stretch is younger than ``n`` periods (opened after ``t_(k-n)``)."""
    OTHER = "other"
    """No inputs for another reason (no finite level bound, a gap in the reading history)."""


@dataclass(frozen=True)
class TrueForces:
    """Truth for ``L_hat_true`` (``force_N`` ``None`` = not replayable, ``note`` says why)."""

    force_N: NDArray[np.float64] | None
    source: TrueForceSource | None
    note: str


def _sample_at(pads_t: NDArray, values: NDArray, t_s: NDArray) -> NDArray[np.float64]:
    """``values`` of the 1 ms sample nearest each ``t_k``; NaN beyond the tolerance."""
    index = np.clip(np.searchsorted(pads_t, t_s), 1, pads_t.size - 1)
    nearer = np.where(np.abs(pads_t[index - 1] - t_s) <= np.abs(pads_t[index] - t_s),
                      index - 1, index)
    out = np.asarray(values, dtype=float)[nearer].copy()
    out[np.abs(pads_t[nearer] - t_s) > PADS_TIME_TOLERANCE_S] = np.nan
    return out


def recorded_seal_friction_N(result: Mapping[str, Any]) -> float | None:
    """Largest seal friction limit stated by cad C-2's record
    ``settings.bundle_c.pads_seal_fields`` (spec rev. 62 316.6 D-2).

    ``friction_path`` false with ``F_s_front_N`` 0: no seal-friction element, 0. ``friction_path``
    true with ``F_s_front_N`` > 0: that front limit (the rear one is smaller). Otherwise
    (no record, missing or contradicting fields): ``None`` = the record does not say.
    """
    bundle = (result.get("settings") or {}).get("bundle_c") or {}
    record = bundle.get(PADS_SEAL_FIELDS_KEY)
    if not isinstance(record, Mapping):
        return None
    front_N = record.get("F_s_front_N")
    has_friction_path = record.get("friction_path")
    if front_N is None or not isinstance(has_friction_path, bool):
        return None
    front_N = float(front_N)
    if not has_friction_path and front_N == 0.0:
        return 0.0
    if has_friction_path and front_N > 0.0:
        return front_N
    return None


def _seal_friction_N(
    episode_meta: Mapping[str, Any], engine: str | None, recorded_N: float | None
) -> float | None:
    """Largest seal friction limit of the run: the episode meta ``seal_friction_N``, else the
    C-2 record (``recorded_N``); L1 runs without either have none (the L1 / L1-R plant has no
    seal-friction element); ``None`` = unknown."""
    friction = episode_meta.get("seal_friction_N")
    if friction is not None:
        return float(np.max(np.atleast_1d(np.asarray(friction, dtype=float))))
    if recorded_N is not None:
        return recorded_N
    if engine is not None and engine.upper().startswith("L1"):
        return 0.0
    return None


def true_forces_at(
    pads_path: Path, t_s: NDArray[np.float64], episode_meta: Mapping[str, Any],
    engine: str | None, *, recorded_seal_friction: float | None = None,
) -> TrueForces:
    """Net-force truth at each ``t_k`` (n, 4): ``F_pressure`` first; without it ``F_cyl``
    only for a run with ``F_s = 0`` (``F_s > 0`` or unknown: not replayable).

    Args:
        pads_path: The run's ``pads.npz``.
        t_s: Update times (n,).
        episode_meta: Episode meta (``seal_friction_N`` when the runner gave it).
        engine: Engine of the run (:func:`run_engine`).
        recorded_seal_friction: Seal friction limit [N] of the C-2 record
            (:func:`recorded_seal_friction_N`), used without an episode ``seal_friction_N``.
    """
    with np.load(pads_path, allow_pickle=False) as pads:
        pads_t = np.asarray(pads["t"], dtype=float)
        if "F_pressure" in pads.files:
            force = _sample_at(pads_t, pads["F_pressure"], t_s)
            return TrueForces(force, TrueForceSource.F_PRESSURE, "truth: pads F_pressure")
        friction_N = _seal_friction_N(episode_meta, engine, recorded_seal_friction)
        if friction_N is None:
            return TrueForces(None, None, "no pads F_pressure and the seal friction is unknown")
        if friction_N > 0.0:
            return TrueForces(None, None, f"no pads F_pressure with seal friction "
                              f"{friction_N:.0f} N > 0: F_cyl is not the pressure force")
        force = _sample_at(pads_t, pads["F_cyl"], t_s)
    return TrueForces(force, TrueForceSource.F_CYL_NO_FRICTION,
                      "truth: pads F_cyl of a run without seal friction")


def _stretch_start_rows(acting_m_s: NDArray[np.float64]) -> NDArray[np.int64]:
    """Per row and leg the first row of the current run of zero acting commands (the row
    itself when the command is not zero)."""
    starts = np.zeros(acting_m_s.shape, dtype=np.int64)
    for leg in range(acting_m_s.shape[1]):
        start = 0
        for row in range(acting_m_s.shape[0]):
            if acting_m_s[row, leg] != 0.0 or row == 0:
                start = row
            starts[row, leg] = start
    return starts


def _slope_condition(slope, acting_m_s, stretch_starts, row, leg, n) -> SlopeCondition:
    if slope is not None:
        return SlopeCondition.MET
    if acting_m_s[row, leg] != 0.0:
        return SlopeCondition.MOVING
    if stretch_starts[row, leg] > row - n:
        return SlopeCondition.SHORT
    return SlopeCondition.OTHER


def _is_watched(inputs: ReplayInput, settings: ReplaySettings, row: int, leg: int) -> bool:
    """``C2Controller._needs_relevel`` watches the leg: lifted, and READY, or PROBE (with the
    P-R8-11 abort) on a leg not being probed."""
    if not inputs.is_lifted[row]:
        return False
    phase = str(inputs.watch_phase[row])
    if phase == C2Phase.READY.value:
        return True
    is_probe_watch = phase == C2Phase.PROBE.value and settings.probe_abort_on_low_load
    return is_probe_watch and int(inputs.probed_leg[row]) != leg


def _r5_fires(drop_N: float, previous_N: float, latest_N: float, predicted_N: float,
              settings: ReplaySettings) -> bool:
    """The three R-5 conditions of one leg: rate, latest period falling, prediction below P5."""
    fast = settings.fast_relevel
    is_fast = drop_N / fast.rate_intervals / settings.period_s > fast.rate_threshold_N_s
    return bool(is_fast and previous_N > latest_N and predicted_N < settings.relevel_level_N)


def optimism_rows(
    inputs: ReplayInput,
    monitor_slope_inputs: NDArray[np.object_],
    fallback_rows: Sequence[int | None],
    true_force_N: NDArray[np.float64],
    acting_m_s: NDArray[np.float64],
    settings: ReplaySettings,
) -> list[dict[str, Any]]:
    """Per fallback-leg row from its fallback row on (module docstring, 4): phase, R-5 watch,
    302.2 condition, both predictions and whether a healthy sensor's R-5 would fire where the
    fallback one does not (``is_missed``)."""
    fast = settings.fast_relevel
    n = fast.rate_intervals
    h = settings.fast_relevel_horizon_periods
    healthy_band = np.min(inputs.seal_band_N, axis=1)
    estimate = inputs.lower_reading_N - inputs.seal_band_N
    true_level = true_force_N - healthy_band[:, None]
    stretch_starts = _stretch_start_rows(acting_m_s)
    rows = []
    for leg, first_row in enumerate(fallback_rows):
        if first_row is None:
            continue
        for row in range(max(first_row, n), inputs.sample_count):
            slope = monitor_slope_inputs[row, leg]
            uses_slope = fast.uses_fallback_slope and slope is not None
            if uses_slope:
                drop_N, _ = slope.drop_N(n, h)
            else:
                drop_N = estimate[row - n, leg] - estimate[row, leg]
            fallback_N = estimate[row, leg] - h / n * drop_N
            true_drop_N = true_level[row - n, leg] - true_level[row, leg]
            healthy_N = true_level[row, leg] - h / n * true_drop_N
            fallback_fires = _r5_fires(drop_N, estimate[row - 1, leg], estimate[row, leg],
                                       fallback_N, settings)
            healthy_fires = _r5_fires(true_drop_N, true_level[row - 1, leg],
                                      true_level[row, leg], healthy_N, settings)
            rows.append({
                "t_s": float(inputs.t_s[row]),
                "leg": LEG_NAMES[leg],
                "phase": str(inputs.watch_phase[row]),
                "is_watched": _is_watched(inputs, settings, row, leg),
                "condition": _slope_condition(slope, acting_m_s, stretch_starts, row, leg,
                                              n).value,
                "rule": "nominal_gap" if uses_slope else "level",
                "head_drop_Pa": None if slope is None else float(slope.head_drop_Pa),
                "fallback_drop_N": float(drop_N),
                "L_hat_fb_N": float(fallback_N),
                "L_hat_true_N": float(healthy_N),
                "difference_N": float(fallback_N - healthy_N),
                "is_rate_passed": bool(drop_N / n / settings.period_s > fast.rate_threshold_N_s),
                "fallback_fires": fallback_fires,
                "healthy_fires": healthy_fires,
                "is_missed": healthy_fires and not fallback_fires,
            })
    return rows


def _rule_summary(rows: Sequence[Mapping[str, Any]], rule: str) -> dict[str, Any]:
    """Watched rows of ``rule``: largest ``L_hat_fb - L_hat_true`` and missed triggers, also
    per 302.2 condition."""
    watched = [row for row in rows if row["rule"] == rule and row["is_watched"]
               and np.isfinite(row["difference_N"])]
    by_condition: dict[str, dict[str, Any]] = {}
    for row in watched:
        entry = by_condition.setdefault(row["condition"],
                                        {"rows": 0, "max_difference_N": None, "missed": 0})
        entry["rows"] += 1
        worst = entry["max_difference_N"]
        entry["max_difference_N"] = (row["difference_N"] if worst is None
                                     else max(worst, row["difference_N"]))
        entry["missed"] += int(row["is_missed"])
    # 302.3 covers a falling head (fall >= 0); on a rising head neither prediction fires R-5.
    falling = [row["difference_N"] for row in watched if row["fallback_drop_N"] >= 0.0]
    return {
        "watched_rows": len(watched),
        "max_difference_N": max((row["difference_N"] for row in watched), default=None),
        "max_difference_falling_N": max(falling, default=None),
        "falling_rows": len(falling),
        "missed": sum(int(row["is_missed"]) for row in watched),
        "by_condition": by_condition,
    }


def run_engine_and_origin(
    result: Mapping[str, Any], episode_meta: Mapping[str, Any]
) -> tuple[str | None, str]:
    """Engine of the run and where it was read (:func:`run_engine`)."""
    engine = episode_meta.get("engine")
    if engine:
        return str(engine), "episode meta"
    settings = result.get("settings") or {}
    for block, key in ENGINE_SETTING_PATHS:
        engine = (settings.get(block) or {}).get(key)
        if engine:
            return str(engine), f"settings.{block}.{key}"
    case_id = str(settings.get("case_id", ""))
    prefix = case_id.split("_", 1)[0]
    if prefix.upper().startswith(("L1", "L2B")):
        return prefix, "case id prefix"
    return None, "not found"


def run_engine(result: Mapping[str, Any], episode_meta: Mapping[str, Any]) -> str | None:
    """Engine of the run: the episode meta, else ``settings.s8.engine`` /
    ``settings.s7c.engine`` (S8 / S7 runners), else the case id prefix (``L1_...``,
    ``L2b_...``); ``None`` = unknown."""
    engine, _ = run_engine_and_origin(result, episode_meta)
    return engine


# --- one case ---------------------------------------------------------------------------------


def _variant_settings(run: ReplaySettings, slope: str, source: str | None) -> ReplaySettings:
    changes: dict[str, Any] = {"fallback_slope": slope}
    if source is not None:
        changes["fallback_ratio_source"] = source
    return replace(run, fast_relevel=replace(run.fast_relevel, **changes))


def _replay_variant(episode, events, geometry, config, run, track, slope, source, allowance):
    settings = _variant_settings(run, slope, source)
    variant_config = replace(config, r8=replace(config.r8, fast_relevel=settings.fast_relevel))
    monitor_replay = replay_fallback_monitor(
        episode, events, geometry, variant_config, offset_allowance_N=allowance.deduction_N,
        offset_allowance_from_s=allowance.from_s)
    inputs = ReplayInput.from_episode(episode).with_fallback_monitor(monitor_replay)
    inputs = replace(inputs, probed_leg=track.legs)
    replay = replay_judge(inputs, settings, Judge.COMBINED)
    return replay, inputs, monitor_replay, settings


def replay_case(
    case_dir: Path,
    geometry: C2Geometry,
    config: C2Config,
    *,
    sources: Sequence[str] = ("plant_meta", "column_nominal"),
) -> dict[str, Any]:
    """V-2 replay of one case folder (module docstring).

    Args:
        case_dir: Runner case folder (``record/record.npz``, ``r8_series.npz``, ``pads.npz``,
            ``result.json``, ``controller_events.json``, ``probe_history.json``).
        geometry: Machine of the run (``C2Geometry.from_params``).
        config: The run's controller setting (lock valve included); its ``r8.fast_relevel``
            is replaced per variant.
        sources: ``fallback_ratio_source`` values replayed with ``nominal_gap``; a run that
            ran ``nominal_gap`` has its own source replayed as well (same-run gate).

    Returns:
        JSON-able result: ``replayable``, ``reasons``, ``notes``, the probed-leg sources, the
        gate (``gate``: kind and verdict; ``level_gate``: the ``level`` replay, the gate or a
        record; ``same_run_gate``: ``None`` for a ``level`` run) and per source the events and
        the optimism record.
    """
    case_dir = Path(case_dir)
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    run_meta = result["controller_meta"]
    events = read_controller_events(case_dir / "controller_events.json")
    episode = build_episode(case_dir, MachineConstants.from_geometry(geometry))
    history_path = case_dir / "probe_history.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.is_file() \
        else []
    with np.load(case_dir / "r8_series.npz", allow_pickle=False) as series:
        computed_u = np.asarray(series["computed_u"], dtype=float)
        recorded = (np.asarray(series[RECORDED_PROBED_LEG_KEY], dtype=np.int64)
                    if RECORDED_PROBED_LEG_KEY in series.files else None)
    t_s = np.asarray(episode["t_s"], dtype=float)
    track = probed_leg_track(t_s, episode["phase"], computed_u, history, events, recorded)
    reasons = list(track.problems)
    notes = ["fallback forced at the run's events; the monitor's own diagnosis is not replayed"]
    differences, setting_notes = monitor_setting_differences(run_meta, config, geometry)
    reasons += differences
    notes += setting_notes
    allowance = offset_allowance(run_meta, events)
    notes.append(allowance.note)
    if allowance.deduction_N is None:
        reasons.append(allowance.note)
        allowance = replace(allowance, deduction_N=np.zeros(LEG_COUNT))  # replay still runs
    run = ReplaySettings.from_controller_meta(run_meta, episode.F_min_N)
    own_source = run_own_slope_source(run)
    gate_kind = GateKind.LEVEL if own_source is None else GateKind.SAME_RUN
    controller = controller_r5_events(events)
    level_replay, level_inputs, _, _ = _replay_variant(
        episode, events, geometry, config, run, track, "level", None, allowance)
    level_events = replay_r5_events(level_replay, level_inputs)
    is_level_equal = level_events == controller
    level_difference = (f"level replay differs from the controller: replay {level_events}, "
                        f"controller {controller}")
    if gate_kind is GateKind.LEVEL and not is_level_equal:
        reasons.append(level_difference)
    elif not is_level_equal:
        notes.append(f"{level_difference} (record: the run ran nominal_gap)")
    engine, engine_origin = run_engine_and_origin(result, episode.meta)
    notes.append(f"engine {engine!r} from {engine_origin}")
    truth = true_forces_at(case_dir / "pads.npz", t_s, episode.meta, engine,
                           recorded_seal_friction=recorded_seal_friction_N(result))
    notes.append(truth.note)
    if truth.force_N is None:
        reasons.append(truth.note)
    limit_N = optimism_allowance_N(engine)
    if limit_N is None:
        notes.append(f"engine {engine!r} unknown: no optimism allowance")
    commands = np.asarray(episode["command_m_s"], dtype=float)
    acting = np.vstack((np.zeros((1, LEG_COUNT)), commands[:-1]))  # d = 1: output of k - 1
    replayed_sources = list(sources)
    if own_source is not None and own_source not in replayed_sources:
        replayed_sources.append(own_source)  # the same-run gate needs it
    variants = {}
    for source in replayed_sources:
        replay, inputs, monitor_replay, settings = _replay_variant(
            episode, events, geometry, config, run, track, "nominal_gap", source, allowance)
        variant: dict[str, Any] = {
            "r5_events": replay_r5_events(replay, inputs),
            "fallback_slope_events": [
                (round(e.t_s, TIME_KEY_DECIMALS), LEG_NAMES[e.leg], e.values_kN)
                for e in replay.events if e.kind is ActionKind.R5_FALLBACK_SLOPE],
        }
        if truth.force_N is not None:
            rows = optimism_rows(inputs, monitor_replay.slope_inputs,
                                 monitor_replay.fallback_rows, truth.force_N, acting, settings)
            variant.update(judged_summary(rows, limit_N))
        variants[source] = variant
    same_run = None
    if own_source is not None:
        same_run = {"source": own_source, **same_run_gate(
            variants[own_source], controller, controller_fallback_slope_events(events))}
        if not same_run["passed"]:
            reasons.append(f"same-run replay ({own_source}) differs from the controller: "
                           f"{same_run}")
    is_gate_passed = is_level_equal if same_run is None else same_run["passed"]
    source_counts = {source.value: int(np.sum(track.sources == source.value))
                     for source in ProbedLegSource if source is not ProbedLegSource.NOT_PROBE}
    return {
        "case": str(case_dir),
        "engine": engine,
        "replayable": not reasons,
        "reasons": reasons,
        "notes": notes,
        "probed_leg_source_counts": source_counts,
        "t_s": t_s.tolist(),
        "probed_leg_source": track.sources.tolist(),
        "probed_leg": track.legs.tolist(),
        "command_history_match": track.command_history_match,
        "gate": {"kind": gate_kind.value, "passed": is_gate_passed},
        "level_gate": {"passed": is_level_equal, "replay": level_events,
                       "controller": controller,
                       "role": "gate" if gate_kind is GateKind.LEVEL else "record"},
        "same_run_gate": same_run,
        "true_force_source": None if truth.source is None else truth.source.value,
        "variants": variants,
    }


class RowClass(StrEnum):
    """Role of a fallback-leg row in the V-2 judgement (control decision 2026-10-26)."""

    JUDGED_FALLING = "judged_falling"
    """Watched, ``nominal_gap``, head falling or still (``Dh >= 0``): its optimism is judged."""
    RECORD_RISING = "record_rising"
    """Watched, ``nominal_gap``, head rising: recorded (neither prediction fires R-5 there)."""
    RECORD_LEVEL = "record_level"
    """Watched, ``level`` rule (302.2 not met): recorded per condition."""
    UNWATCHED = "unwatched"
    """R-5 does not watch the leg in this period."""


def row_class(row: Mapping[str, Any]) -> RowClass:
    if not row["is_watched"]:
        return RowClass.UNWATCHED
    if row["rule"] == "level":
        return RowClass.RECORD_LEVEL
    if row["head_drop_Pa"] >= 0.0:
        return RowClass.JUDGED_FALLING
    return RowClass.RECORD_RISING


def _class_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    summary = {}
    for kind in RowClass:
        members = [row for row in rows if row["row_class"] == kind.value]
        differences = [row["difference_N"] for row in members
                       if np.isfinite(row["difference_N"])]
        summary[kind.value] = {
            "rows": len(members),
            "max_difference_N": max(differences, default=None),
            "missed": sum(int(row["is_missed"]) for row in members),
        }
    return summary


def judged_summary(rows: list[dict[str, Any]], limit_N: float | None) -> dict[str, Any]:
    """V-2 judgement of one variant (control decision 2026-10-26).

    ``judgement_passed`` (the only official verdict): the ``judged_falling`` rows have their
    largest ``L_hat_fb - L_hat_true`` within the engine allowance, and the watched rows that
    meet 302.2 (``judged_falling`` + ``record_rising``) have no missed trigger. Such a missed
    trigger fails it in any case; otherwise ``None`` = no judged row or no allowance (engine
    unknown). A missed trigger on a ``record_level`` row only sets
    ``level_missed_trigger_flag`` (count ``level_missed_triggers``); the rest is recorded.
    """
    for row in rows:
        row["row_class"] = row_class(row).value
    classes = _class_summary(rows)
    judged = classes[RowClass.JUDGED_FALLING.value]
    slope_missed = judged["missed"] + classes[RowClass.RECORD_RISING.value]["missed"]
    level_missed = classes[RowClass.RECORD_LEVEL.value]["missed"]
    worst_N = judged["max_difference_N"]
    is_within = None if worst_N is None or limit_N is None else worst_N <= limit_N
    if slope_missed > 0:
        verdict: bool | None = False
    else:
        verdict = is_within
    return {
        "optimism_rows": rows,
        "row_classes": classes,
        "allowance_N": limit_N,
        "judged_falling_within_allowance": is_within,
        "slope_rows_missed_triggers": slope_missed,
        "judgement_passed": verdict,
        "level_missed_triggers": level_missed,
        "level_missed_trigger_flag": level_missed >= 1,
        "record_nominal_gap": _rule_summary(rows, "nominal_gap"),
        "record_level": _rule_summary(rows, "level"),
    }
