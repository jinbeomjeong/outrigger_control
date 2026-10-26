"""Offline replay of the pressure-only (J_P) and combined (J_C) contact judges (P-S8-1).

``00_docs/04_control/s6_control_spec.md`` rev. 39 203.2 / 209.2. From one recorded run
(:class:`outrigger_sim.contact_episode.Episode`, 10 Hz) both judges are computed on the same
inputs, independent of what the controller did:

* **decision level** ("미달 표시"): J_P ``F_hat < F_min``; J_C ``F_hat - F_band < F_min``, or a
  GE2 G1-L lift flag (``shadow_G1L``), or a probe verdict "not grounded".
* **action level** ("재레벨·재접근 표시"): P5 (lowest load estimate below ``F_min + 7.5 kN`` for
  ``relevel_samples`` periods), R-5 (predicted estimate), the lifted-leg re-approach start
  (estimate below ``F_min / 2``), and for J_C the GE2 trigger.

The load estimate is the controller's ``_load_estimate_N``: J_P the lower reading itself, J_C the
lower reading minus the per-leg seal band. P5, R-5 and the re-approach are the arithmetic of
``C2Controller._needs_relevel`` / ``_leg_falling_below`` / ``_update_lifted_reapproach`` with the
controller's own settings classes (:class:`~outrigger_sim.control.c2.FastRelevelSettings`,
:class:`~outrigger_sim.control.c2.LiftedReapproachSettings`); the GE2 and probe inputs are the
controller's recorded events and probe results (not recomputed). The re-approach follows the
re-trigger rule RT of P-S8-16 (spec rev. 52 228.3) when the settings turn it on: an
other-diagonal start inside the opposite window waits for the strong confirmation (event
``leg_reapproach_deferred``), so the replay gives the controller's start times.

:attr:`WatchMode.CONTROLLER` gates P5 / R-5 / re-approach on the recorded phases (READY, PROBE
with the low-load abort, the re-approach phases), so a replay of the controller's own judge
reproduces its events; :attr:`WatchMode.CONTINUOUS` watches every period after lift-off, for
comparing judges on a record whose phases came from the other judge.

R-5 fallback slope (P-S8-22, spec rev. 61 302.2, V-2): with ``fallback_slope = "nominal_gap"``
in the replay settings and the per-period :class:`FallbackSlopeInputs` of
:func:`replay_fallback_monitor` in the input (:meth:`ReplayInput.with_fallback_monitor`), R-5
uses the controller's own rule :func:`~outrigger_sim.control.c2.fallback_slope_drops` and
reports ``INFO_R5_FALLBACK_SLOPE`` events. The inputs come from a two-pressure monitor run
offline on the recorded readings, with the rod-side fallback forced at the controller's
``WARN_ROD_PRESSURE_FALLBACK`` events (the monitor's own diagnosis is off).

Not replayed: the attitude re-level (it resets the P5 counter in the controller) and the periods
a U67 lock tail skips the READY check; both only shift a P5 confirmation by a period.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, fields, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import (
    LEG_COUNT,
    LEG_NAMES,
    NO_LEG,
    ZERO_CALIBRATED_EVENT,
    Episode,
)
from outrigger_sim.control.c2 import (
    FALLBACK_SLOPE_EVENT,
    REAPPROACH_PHASES,
    C2Config,
    C2Geometry,
    C2Phase,
    FallbackSlopeReport,
    FastRelevelSettings,
    LiftedReapproachSettings,
    fallback_slope_drops,
)
from outrigger_sim.control.two_pressure import (
    FallbackSlopeInputs,
    RodSensorState,
    TwoPressureMonitor,
)
from outrigger_sim.verify.contact_metrics import RecordJudgement, truth_classes


class Judge(StrEnum):
    """The two judges of spec 203.2."""

    PRESSURE = "J_P"
    COMBINED = "J_C"


class WatchMode(StrEnum):
    """When the action-level rules are evaluated."""

    CONTROLLER = "controller"
    """On the recorded phases, as the controller did (replay of the controller's own judge)."""
    CONTINUOUS = "continuous"
    """Every period once lifted (judge comparison on one record)."""


class ActionKind(StrEnum):
    """Action-level events."""

    P5 = "p5_relevel"
    R5 = "relevel_predicted"
    REAPPROACH_START = "leg_reapproach_start"
    REAPPROACH_CONTACT = "leg_reapproach_contact"
    REAPPROACH_NO_CONTACT = "leg_reapproach_no_contact"
    REAPPROACH_DEFERRED = "leg_reapproach_deferred"
    """P-S8-16 RT 1: first sample of a deferred other-diagonal start (bookkeeping)."""
    GE2 = "support_changed"
    R5_FALLBACK_SLOPE = FALLBACK_SLOPE_EVENT
    """P-S8-22: a fallback leg's R-5 fall passed the rate threshold (information)."""


ACTION_START_KINDS = frozenset(
    {ActionKind.P5, ActionKind.R5, ActionKind.REAPPROACH_START, ActionKind.GE2}
)
"""Events that are a "재레벨·재접근 표시" (the re-approach ends are bookkeeping)."""

LOW_LOAD_WATCH_PHASES = frozenset({C2Phase.READY.value})

DIAGONAL_SIGNS = (1.0, -1.0, -1.0, 1.0)
"""``sign(n_i)`` of the twist vector in leg order (FL, FR, RL, RR): FL / RR and FR / RL are the
two diagonals. Only equal or unequal signs matter to rule RT (P-S8-16), so the overall sign
of ``n`` does not."""


@dataclass(frozen=True)
class ReplaySettings:
    """Thresholds of the replayed rules, taken from the controller configuration.

    Attributes:
        period_s: Control period.
        F_min_N: Minimum cylinder force.
        relevel_margin_N: P5 level above ``F_min`` (``thresholds.relevel_load_margin_N``).
        relevel_samples: P5 confirmation (``r8.confirmation.relevel_samples``).
        output_delay_periods: ``d`` (R-5 default horizon ``1 + d``).
        probe_abort_on_low_load: P-R8-11: P5 / R-5 also watch PROBE.
        fast_relevel: R-5 settings, ``None`` = off.
        reapproach: P-R8-12 / 13 settings.
    """

    period_s: float
    F_min_N: float
    relevel_margin_N: float
    relevel_samples: int
    output_delay_periods: int
    probe_abort_on_low_load: bool
    fast_relevel: FastRelevelSettings | None
    reapproach: LiftedReapproachSettings

    @classmethod
    def from_config(cls, config: C2Config, F_min_N: float) -> ReplaySettings:
        """From a :class:`C2Config` (e.g. ``C2Config().with_10hz_d1()``)."""
        r8 = config.r8
        return cls(
            period_s=config.period_s,
            F_min_N=float(F_min_N),
            relevel_margin_N=config.thresholds.relevel_load_margin_N,
            relevel_samples=r8.confirmation.relevel_samples,
            output_delay_periods=r8.output_delay_periods,
            probe_abort_on_low_load=r8.probe_abort_on_low_load,
            fast_relevel=r8.fast_relevel,
            reapproach=r8.lifted_reapproach,
        )

    @classmethod
    def from_controller_meta(cls, meta: Mapping[str, Any], F_min_N: float) -> ReplaySettings:
        """From ``C2Controller.meta()`` as saved in ``result.json`` (``controller_meta``).

        ``r8.fast_relevel`` keys that are not :class:`FastRelevelSettings` fields are ignored:
        runners add record-only keys there (cad C-1, spec rev. 62 316.6 D-1:
        ``fallback_plant_ratio_source``, ``fallback_ratio_source_override``, ...); see
        :func:`fast_relevel_record_only_keys`.
        """
        r8 = meta["r8"]
        fast = r8.get("fast_relevel")
        return cls(
            period_s=float(meta["period_s"]),
            F_min_N=float(F_min_N),
            relevel_margin_N=float(meta["thresholds"]["relevel_load_margin_N"]),
            relevel_samples=int(r8["confirmation"]["relevel_samples"]),
            output_delay_periods=int(r8["output_delay_periods"]),
            probe_abort_on_low_load=bool(r8.get("probe_abort_on_low_load", False)),
            fast_relevel=None if fast is None else _fast_relevel_from_meta(fast),
            reapproach=_reapproach_from_meta(r8.get("lifted_reapproach") or {}),
        )

    @property
    def relevel_level_N(self) -> float:
        return self.F_min_N + self.relevel_margin_N

    @property
    def fast_relevel_horizon_periods(self) -> int:
        settings = self.fast_relevel
        if settings is None or settings.horizon_periods is None:
            return 1 + self.output_delay_periods
        return settings.horizon_periods

    @property
    def reapproach_samples(self) -> int:
        return self.reapproach.samples or self.relevel_samples


def replay_meta_from_config(config: C2Config) -> dict[str, Any]:
    """The part of ``C2Controller.meta()`` that :meth:`ReplaySettings.from_controller_meta`
    reads, for records made without a controller (synthetic episodes, tests)."""
    r8 = config.r8
    fast = r8.fast_relevel
    reapproach = asdict(r8.lifted_reapproach)
    reapproach["mode"] = str(r8.lifted_reapproach.mode)
    return {
        "period_s": config.period_s,
        "thresholds": {"relevel_load_margin_N": config.thresholds.relevel_load_margin_N},
        "r8": {
            "confirmation": asdict(r8.confirmation),
            "output_delay_periods": r8.output_delay_periods,
            "probe_abort_on_low_load": r8.probe_abort_on_low_load,
            "fast_relevel": None if fast is None else asdict(fast),
            "lifted_reapproach": reapproach,
        },
    }


FAST_RELEVEL_SETTING_KEYS = frozenset(setting.name for setting in fields(FastRelevelSettings))
"""The ``r8.fast_relevel`` meta keys that are settings (the rest are records)."""


def fast_relevel_record_only_keys(fast_meta: Mapping[str, Any]) -> list[str]:
    """Keys of a recorded ``r8.fast_relevel`` that are not settings (ignored by the replay)."""
    return sorted(set(fast_meta) - FAST_RELEVEL_SETTING_KEYS)


def _fast_relevel_from_meta(fast_meta: Mapping[str, Any]) -> FastRelevelSettings:
    settings = {key: value for key, value in fast_meta.items()
                if key in FAST_RELEVEL_SETTING_KEYS}
    return FastRelevelSettings(**settings)


def _reapproach_from_meta(meta: Mapping[str, Any]) -> LiftedReapproachSettings:
    """Settings of the run; a meta without ``mode`` is a revision-33 (P-R8-12) run, whose
    class had no mode / single-leg / exit keys and behaved as :meth:`leg_mode`."""
    if not meta:
        return LiftedReapproachSettings()
    if "mode" not in meta:
        return replace(LiftedReapproachSettings.leg_mode(), **meta)
    return LiftedReapproachSettings(**meta)


@dataclass(frozen=True)
class ReplayInput:
    """Per update ``k``: what the controller saw when it judged (state of update ``k - 1``).

    Attributes:
        t_s: Period end times (n,).
        watch_phase: Phase at the start of update ``k`` (n,).
        lower_reading_N: ``forces.lower`` read in update ``k`` (n, 4).
        seal_band_N: Per-leg band at that read (n, 4).
        motor_stroke_m: Motor stroke (n, 4), for the re-approach travel.
        is_lifted: Lifted latch at the start of update ``k`` (n,).
        touched: Touch latch at the start of update ``k`` (n, 4).
        probed_leg: Probed leg at the start of update ``k`` (n,), -1 = none.
        ge2_lift_mark, ge2_trigger_mark, probe_not_grounded_mark: J_C marks (n, 4).
        fallback_slope_inputs: P-S8-22 R-5 inputs of update ``k`` (n, 4 objects,
            :class:`FallbackSlopeInputs` or ``None``); ``None`` = not replayed (level rule).
    """

    t_s: NDArray[np.float64]
    watch_phase: NDArray[np.str_]
    lower_reading_N: NDArray[np.float64]
    seal_band_N: NDArray[np.float64]
    motor_stroke_m: NDArray[np.float64]
    is_lifted: NDArray[np.bool_]
    touched: NDArray[np.bool_]
    probed_leg: NDArray[np.int64]
    ge2_lift_mark: NDArray[np.bool_]
    ge2_trigger_mark: NDArray[np.bool_]
    probe_not_grounded_mark: NDArray[np.bool_]
    fallback_slope_inputs: NDArray[np.object_] | None = None

    @property
    def sample_count(self) -> int:
        return int(self.t_s.size)

    def with_fallback_monitor(self, monitor_replay: FallbackMonitorReplay) -> ReplayInput:
        """Copy with the replayed fallback readings: from its fallback row on, the lower
        reading of a fallback leg is the monitor's column-bound one (an S7 episode records
        the net force there), and the R-5 fallback inputs per update."""
        lower = np.array(self.lower_reading_N, dtype=float)
        for leg, first_row in enumerate(monitor_replay.fallback_rows):
            if first_row is not None:
                lower[first_row:, leg] = monitor_replay.lower_reading_N[first_row:, leg]
        return replace(self, lower_reading_N=lower,
                       fallback_slope_inputs=monitor_replay.slope_inputs)

    @classmethod
    def from_episode(cls, episode: Episode) -> ReplayInput:
        """Shift the after-update state fields of ``episode`` by one period."""
        not_grounded = episode["probe_round_end"][:, None] & (episode["probe_is_grounded"] == 0.0)
        return cls(
            t_s=np.asarray(episode["t_s"], dtype=float),
            watch_phase=_previous(episode["phase"]),
            lower_reading_N=np.asarray(episode["lower_reading_N"], dtype=float),
            seal_band_N=_previous(np.asarray(episode["seal_band_N"], dtype=float)),
            motor_stroke_m=np.asarray(episode["motor_stroke_m"], dtype=float),
            is_lifted=_previous(episode["is_lifted"], fill=False),
            touched=_previous(episode["touched"], fill=False),
            probed_leg=_previous(np.asarray(episode["probed_leg"]), fill=NO_LEG),
            ge2_lift_mark=np.asarray(episode["ge2_lift_mark"], dtype=bool),
            ge2_trigger_mark=np.asarray(episode["ge2_trigger_mark"], dtype=bool),
            probe_not_grounded_mark=np.asarray(not_grounded, dtype=bool),
        )


def _previous(values: NDArray[Any], fill: Any = None) -> NDArray[Any]:
    """Row ``k`` -> row ``k - 1``; row 0 keeps its own value unless ``fill`` is given."""
    shifted = np.empty_like(values)
    shifted[1:] = values[:-1]
    shifted[0] = values[0] if fill is None else fill
    return shifted


@dataclass(frozen=True)
class ReplayEvent:
    """One action-level event (``t_s`` = period end of the update that raised it)."""

    t_s: float
    leg: int
    kind: ActionKind
    values_kN: tuple[float, float] | None = None
    """``R5_FALLBACK_SLOPE``: ``((h / n) D, (h / n) gap)`` in kN, as the controller event."""


@dataclass
class JudgeReplay:
    """Per-sample judge outputs (n, 4) and the event list of one judge."""

    judge: Judge
    load_estimate_N: NDArray[np.float64]
    decision_flags: NDArray[np.bool_]
    action_flags: NDArray[np.bool_]
    events: list[ReplayEvent] = field(default_factory=list)

    def event_tuples(self, kinds: frozenset[ActionKind] | None = None) -> list[tuple]:
        """``(t_s rounded to 1 us, leg, kind)`` for comparisons."""
        return [
            (round(event.t_s, 6), event.leg, event.kind.value)
            for event in self.events
            if kinds is None or event.kind in kinds
        ]


def load_estimate_N(
    lower_reading_N: NDArray[np.float64], seal_band_N: NDArray[np.float64], judge: Judge
) -> NDArray[np.float64]:
    """``C2Controller._load_estimate_N``: the reading (J_P) or reading minus band (J_C)."""
    if judge is Judge.PRESSURE:
        return np.asarray(lower_reading_N, dtype=float)
    return np.asarray(lower_reading_N, dtype=float) - np.asarray(seal_band_N, dtype=float)


def predicted_falling_leg(
    history: deque[NDArray[np.float64]],
    settings: ReplaySettings,
    excluded_leg: int,
) -> int | None:
    """R-5 (``C2Controller._leg_falling_below``) on the estimate history, or ``None``."""
    leg, _ = predicted_falling_leg_with_reports(history, settings, excluded_leg)
    return leg


def predicted_falling_leg_with_reports(
    history: deque[NDArray[np.float64]],
    settings: ReplaySettings,
    excluded_leg: int,
    fallback_inputs: Sequence[FallbackSlopeInputs | None] | None = None,
) -> tuple[int | None, list[FallbackSlopeReport]]:
    """R-5 with the P-S8-22 fallback slope when the settings have it and ``fallback_inputs``
    (per leg, this update) are given: (triggered leg or ``None``, fallback slope reports)."""
    fast = settings.fast_relevel
    if fast is None or len(history) < fast.rate_intervals + 1:
        return None, []
    oldest, previous, latest = history[0], history[-2], history[-1]
    drop_per_period = (oldest - latest) / fast.rate_intervals
    horizon_periods = settings.fast_relevel_horizon_periods
    reports = []
    if fast.uses_fallback_slope and fallback_inputs is not None:
        drop_per_period, reports = fallback_slope_drops(
            drop_per_period, fallback_inputs, fast, horizon_periods, settings.period_s,
            None if excluded_leg == NO_LEG else excluded_leg,
        )
    predicted = latest - drop_per_period * horizon_periods
    is_fast = drop_per_period / settings.period_s > fast.rate_threshold_N_s
    triggered = is_fast & (previous > latest) & (predicted < settings.relevel_level_N)
    if excluded_leg != NO_LEG:
        triggered[excluded_leg] = False
    if not triggered.any():
        return None, reports
    return int(np.argmin(np.where(triggered, predicted, np.inf))), reports


@dataclass
class _ReapproachRun:
    start_motor_stroke_m: float
    exit_samples_seen: int = 0


@dataclass
class _ReplayState:
    history: deque
    relevel_low_count: int = 0
    active: dict[int, _ReapproachRun] = field(default_factory=dict)
    armed: NDArray[np.bool_] = field(default_factory=lambda: np.ones(LEG_COUNT, dtype=bool))
    low_counts: NDArray[np.int64] = field(
        default_factory=lambda: np.zeros(LEG_COUNT, dtype=np.int64)
    )
    strong_counts: NDArray[np.int64] = field(
        default_factory=lambda: np.zeros(LEG_COUNT, dtype=np.int64)
    )
    """P-S8-16 RT 1: consecutive watched low samples below the strong level."""
    last_end_s: float | None = None
    """P-S8-16: end time of the last re-approach (any outcome)."""
    last_sign: float = 0.0
    """P-S8-16: diagonal sign of the leg of the last re-approach."""


class _Replayer:
    """Steps the replayed rules through the periods of one record (one judge)."""

    def __init__(self, inputs: ReplayInput, settings: ReplaySettings, judge: Judge,
                 watch: WatchMode) -> None:
        self.inputs = inputs
        self.settings = settings
        self.watch = watch
        self.estimate = load_estimate_N(inputs.lower_reading_N, inputs.seal_band_N, judge)
        history_length = 1 if settings.fast_relevel is None else (
            settings.fast_relevel.rate_intervals + 1
        )
        self.state = _ReplayState(history=deque(maxlen=history_length))
        self.events: list[ReplayEvent] = []

    def run(self) -> list[ReplayEvent]:
        for row in range(self.inputs.sample_count):
            loads = self.estimate[row]
            self.state.history.append(loads)  # every period, as ``_read`` does
            self._step_reapproach(row, loads)
            self._step_low_load(row, loads)
        return self.events

    def _add(self, row: int, leg: int, kind: ActionKind) -> None:
        self.events.append(ReplayEvent(float(self.inputs.t_s[row]), leg, kind))

    def _is_reapproach_watched(self, row: int) -> bool:
        if not self.inputs.is_lifted[row]:
            return False
        if self.watch is WatchMode.CONTINUOUS:
            return True
        return str(self.inputs.watch_phase[row]) in REAPPROACH_PHASE_NAMES

    def _is_low_load_watched(self, row: int) -> bool:
        if not self.inputs.is_lifted[row]:
            return False
        if self.watch is WatchMode.CONTINUOUS:
            return True
        phase = str(self.inputs.watch_phase[row])
        if phase in LOW_LOAD_WATCH_PHASES:
            return True
        return phase == C2Phase.PROBE.value and self.settings.probe_abort_on_low_load

    def _step_reapproach(self, row: int, loads: NDArray[np.float64]) -> None:
        """``C2Controller._update_lifted_reapproach``."""
        rules = self.settings.reapproach
        if not rules.enable:
            return
        state = self.state
        if not self._is_reapproach_watched(row):
            for leg in list(state.active):
                self._end_reapproach(row, leg)
            state.low_counts[:] = 0
            state.strong_counts[:] = 0
            return
        self._end_reapproaches(row, loads, rules)
        self._start_reapproaches(row, loads, rules)

    def _end_reapproach(self, row: int, leg: int) -> None:
        """``C2Controller._end_reapproach``: the P-S8-16 windows count from here."""
        state = self.state
        del state.active[leg]
        state.last_end_s = float(self.inputs.t_s[row])
        state.last_sign = DIAGONAL_SIGNS[leg]

    def _end_reapproaches(self, row, loads, rules: LiftedReapproachSettings) -> None:
        state = self.state
        F_min = self.settings.F_min_N
        for leg, run in list(state.active.items()):
            travel = float(self.inputs.motor_stroke_m[row, leg]) - run.start_motor_stroke_m
            run.exit_samples_seen = run.exit_samples_seen + 1 if (
                loads[leg] >= F_min + rules.exit_margin_N
            ) else 0
            if run.exit_samples_seen >= rules.exit_samples:
                self._end_reapproach(row, leg)
                self._add(row, leg, ActionKind.REAPPROACH_CONTACT)
            elif travel > rules.max_travel_m:
                self._end_reapproach(row, leg)
                state.armed[leg] = False
                self._add(row, leg, ActionKind.REAPPROACH_NO_CONTACT)
        state.armed |= loads >= F_min

    def _start_reapproaches(self, row, loads, rules: LiftedReapproachSettings) -> None:
        state = self.state
        lift_off_level = rules.load_fraction_of_F_min * self.settings.F_min_N
        required_samples = self.settings.reapproach_samples
        probed_leg = int(self.inputs.probed_leg[row])
        for leg in range(LEG_COUNT):
            is_another_leg_active = rules.single_leg and bool(state.active)
            is_watched = (
                bool(self.inputs.touched[row, leg])
                and bool(state.armed[leg])
                and leg not in state.active
                and leg != probed_leg
                and not is_another_leg_active
            )
            if not is_watched or loads[leg] >= lift_off_level:
                state.low_counts[leg] = 0
                state.strong_counts[leg] = 0
                continue
            state.low_counts[leg] += 1
            is_strong = loads[leg] < rules.opposite_strong_level_N
            state.strong_counts[leg] = state.strong_counts[leg] + 1 if is_strong else 0
            if state.low_counts[leg] < required_samples:
                continue
            if self._defers_reapproach(row, leg, rules):
                # first sample of the deferred stretch (the low count keeps rising)
                if state.low_counts[leg] == required_samples:
                    self._add(row, leg, ActionKind.REAPPROACH_DEFERRED)
                continue
            state.low_counts[leg] = 0
            state.strong_counts[leg] = 0
            state.active[leg] = _ReapproachRun(float(self.inputs.motor_stroke_m[row, leg]))
            self._add(row, leg, ActionKind.REAPPROACH_START)

    def _defers_reapproach(self, row: int, leg: int, rules: LiftedReapproachSettings) -> bool:
        """``C2Controller._defers_reapproach`` (P-S8-16 RT 1)."""
        state = self.state
        needs_confirmation = rules.needs_strong_confirmation(
            float(self.inputs.t_s[row]), state.last_end_s, state.last_sign, DIAGONAL_SIGNS[leg]
        )
        return needs_confirmation and state.strong_counts[leg] < rules.opposite_strong_samples

    def _step_low_load(self, row: int, loads: NDArray[np.float64]) -> None:
        """The load part of ``C2Controller._needs_relevel`` (R-5 first, then P5)."""
        state = self.state
        if not self._is_low_load_watched(row):
            state.relevel_low_count = 0
            return
        probed_leg = int(self.inputs.probed_leg[row])
        all_inputs = self.inputs.fallback_slope_inputs
        predicted_leg, reports = predicted_falling_leg_with_reports(
            state.history, self.settings, probed_leg,
            None if all_inputs is None else list(all_inputs[row]),
        )
        for report in reports:
            values_kN = (report.horizon_drop_N / 1e3, report.horizon_gap_N / 1e3)
            self.events.append(ReplayEvent(float(self.inputs.t_s[row]), report.leg,
                                           ActionKind.R5_FALLBACK_SLOPE, values_kN))
        if predicted_leg is not None:
            self._add(row, predicted_leg, ActionKind.R5)
            state.relevel_low_count = 0
            return
        watched_loads = loads.copy()
        if probed_leg != NO_LEG:
            watched_loads[probed_leg] = np.inf
        lowest_leg = int(np.argmin(watched_loads))
        is_low = float(watched_loads[lowest_leg]) < self.settings.relevel_level_N
        state.relevel_low_count = state.relevel_low_count + 1 if is_low else 0
        if state.relevel_low_count >= self.settings.relevel_samples:
            self._add(row, lowest_leg, ActionKind.P5)
            state.relevel_low_count = 0


REAPPROACH_PHASE_NAMES = frozenset(phase.value for phase in REAPPROACH_PHASES)


def replay_judge(
    inputs: ReplayInput,
    settings: ReplaySettings,
    judge: Judge,
    *,
    watch: WatchMode = WatchMode.CONTROLLER,
) -> JudgeReplay:
    """Decision and action flags of one judge on one record (module docstring).

    Args:
        inputs: The record as the controller saw it (:meth:`ReplayInput.from_episode`).
        settings: Thresholds (:meth:`ReplaySettings.from_controller_meta` of the run).
        judge: J_P or J_C.
        watch: Phase gating of the action rules.

    Returns:
        Per-sample flags (n, 4) and the events.
    """
    replayer = _Replayer(inputs, settings, judge, watch)
    events = replayer.run()
    estimate = replayer.estimate
    decision = estimate < settings.F_min_N
    action = np.zeros_like(decision)
    if judge is Judge.COMBINED:
        decision = decision | inputs.ge2_lift_mark | inputs.probe_not_grounded_mark
        action = action | inputs.ge2_trigger_mark
        for row, leg in zip(*np.nonzero(inputs.ge2_trigger_mark), strict=True):
            events.append(ReplayEvent(float(inputs.t_s[row]), int(leg), ActionKind.GE2))
    row_of_time = {round(float(t), 9): row for row, t in enumerate(inputs.t_s)}
    for event in events:
        if event.kind in ACTION_START_KINDS:
            action[row_of_time[round(event.t_s, 9)], event.leg] = True
    events.sort(key=lambda event: (event.t_s, event.leg))
    return JudgeReplay(judge, estimate, decision, action, events)


def replay_both(
    episode: Episode,
    settings: ReplaySettings | None = None,
    *,
    watch: WatchMode = WatchMode.CONTROLLER,
) -> dict[Judge, JudgeReplay]:
    """J_P and J_C on one episode; ``settings`` default = the run's own controller meta."""
    if settings is None:
        settings = ReplaySettings.from_controller_meta(episode.meta["controller"], episode.F_min_N)
    inputs = ReplayInput.from_episode(episode)
    return {judge: replay_judge(inputs, settings, judge, watch=watch) for judge in Judge}


# --- P-S8-22: two-pressure monitor replay for the R-5 fallback slope (V-2) ------------------

FALLBACK_EVENT_PREFIX = "WARN_ROD_PRESSURE_FALLBACK"
FAULT_REASON_PREFIX = "INFO_ROD_PRESSURE_FAULT_REASON"
LATE_FALLBACK_REASONS = frozenset({"D4", "D6"})
"""Fallbacks the controller's monitor raises after the period's estimate update (D4 in the
locked check on the forces, D6 at a probe round end): forced from the next row on. D1-D3 are
judged before the estimate update of the same read."""
EVENT_TIME_TOLERANCE_FRACTION = 0.25
"""An event belongs to the row whose period end lies within this fraction of ``T``."""


@dataclass(frozen=True)
class FallbackMonitorReplay:
    """Offline two-pressure monitor of one record (:func:`replay_fallback_monitor`).

    Attributes:
        lower_reading_N: The monitor's ``forces.lower`` per update (n, 4).
        slope_inputs: R-5 fallback inputs per update (n, 4 objects, ``None`` = none).
        fallback_rows: Per leg the first row read as a fallback leg (``None`` = never).
    """

    lower_reading_N: NDArray[np.float64]
    slope_inputs: NDArray[np.object_]
    fallback_rows: tuple[int | None, ...]


def _row_of_event(t_s: NDArray[np.float64], time_s: float, period_s: float) -> int | None:
    row = int(np.argmin(np.abs(t_s - time_s)))
    if abs(t_s[row] - time_s) > EVENT_TIME_TOLERANCE_FRACTION * period_s:
        return None
    return row


def _leg_of_event(name: str) -> int | None:
    parts = name.split(":")
    if len(parts) < 2 or parts[1] not in LEG_NAMES:
        return None
    return LEG_NAMES.index(parts[1])


def fallback_rows_from_events(
    events: Sequence[tuple[float, str]], t_s: NDArray[np.float64], period_s: float
) -> tuple[int | None, ...]:
    """Per leg the first row the controller's monitor read as a fallback leg, from
    ``WARN_ROD_PRESSURE_FALLBACK:<leg>`` and the reason of
    ``INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>`` (:data:`LATE_FALLBACK_REASONS`: next
    row)."""
    reasons: dict[int, str] = {}
    for _, name in events:
        if name.startswith(FAULT_REASON_PREFIX):
            leg = _leg_of_event(name)
            if leg is not None:
                reasons.setdefault(leg, name.split(":")[2] if name.count(":") >= 2 else "")
    rows: list[int | None] = [None] * LEG_COUNT
    for time_s, name in events:
        leg = _leg_of_event(name)
        if not name.startswith(FALLBACK_EVENT_PREFIX) or leg is None or rows[leg] is not None:
            continue
        row = _row_of_event(t_s, time_s, period_s)
        if row is None:
            continue
        rows[leg] = row + 1 if reasons.get(leg) in LATE_FALLBACK_REASONS else row
    return tuple(rows)


def _calibration_rows(events, t_s, period_s) -> NDArray[np.int64]:
    """Per leg the first row with the zero offset removed (the row after its event)."""
    first = np.full(LEG_COUNT, t_s.size, dtype=np.int64)
    for time_s, name in events:
        leg = _leg_of_event(name)
        if not name.startswith(ZERO_CALIBRATED_EVENT) or leg is None:
            continue
        row = _row_of_event(t_s, time_s, period_s)
        if row is not None:
            first[leg] = min(first[leg], row + 1)
    return first


def replay_fallback_monitor(
    episode: Episode,
    events: Sequence[tuple[float, str]],
    geometry: C2Geometry,
    config: C2Config,
    *,
    offset_allowance_N: NDArray[np.float64] | None = None,
    offset_allowance_from_s: float | None = None,
) -> FallbackMonitorReplay:
    """Run the controller's two-pressure monitor offline on a record (P-S8-22 V-2).

    The monitor is built as :class:`~outrigger_sim.control.c2.C2Controller` builds it, but
    with its diagnosis off: the rod-side fallback is forced at the recorded events
    (:func:`fallback_rows_from_events`), so the replay does not depend on the IMU inputs of
    D1''. Each row reads the delivered head / rod pressures and measured strokes with the
    issued command of the row before (the output acting during the period, ``d = 1``), as
    the controller's read did; the zero offsets (episode meta ``zero_offset_N``) apply from
    the row after each leg's ``INFO_PRESSURE_ZERO_CALIBRATED`` event.

    Args:
        episode: The record (head and rod-side pressures needed).
        events: The controller events of the run (``read_controller_events``).
        geometry: Machine of the run (``C2Geometry.from_params``).
        config: Controller setting of the run, with the fallback-slope choice to replay
            (``r8.fast_relevel``; ``level`` gives no inputs) and the run's lock valve.
        offset_allowance_N: E-6 lower-bound deduction per leg (not in the episode; ``None``
            = zero), from the calibration row of the leg on, or from
            ``offset_allowance_from_s`` when given.
        offset_allowance_from_s: Time from which the deduction applies to every leg (the
            calibration end ``zero_calibration.result.t_end_s``, when the controller set it).

    Raises:
        ValueError: The episode has no rod-side pressure.
    """
    if not episode.has("rod_pressure_Pa"):
        raise ValueError("replay_fallback_monitor needs the rod-side pressure of the record")
    t_s = np.asarray(episode["t_s"], dtype=float)
    period_s = config.period_s
    head = np.asarray(episode["head_pressure_Pa"], dtype=float)
    rod = np.asarray(episode["rod_pressure_Pa"], dtype=float)
    stroke = np.asarray(episode["motor_stroke_m"], dtype=float)
    acting = _previous(np.asarray(episode["command_m_s"], dtype=float), fill=0.0)
    is_ready = _previous(np.asarray(episode["phase"]), fill="") == C2Phase.READY.value
    seal_band = _previous(np.asarray(episode["seal_band_N"], dtype=float))
    monitor = _offline_monitor(geometry, config)
    fallback_rows = fallback_rows_from_events(events, t_s, period_s)
    calibration_rows = _calibration_rows(events, t_s, period_s)
    offsets = np.asarray(episode.meta.get("zero_offset_N") or np.zeros(LEG_COUNT), dtype=float)
    allowance = np.zeros(LEG_COUNT) if offset_allowance_N is None else np.asarray(
        offset_allowance_N, dtype=float)
    fast = config.r8.fast_relevel
    choice = None if fast is None else fast.fallback_ratio_choice()
    lower = np.empty_like(head)
    inputs = np.full(head.shape, None, dtype=object)
    for row in range(t_s.size):
        is_calibrated = calibration_rows <= row
        monitor.set_zero_offsets_N(np.where(is_calibrated, offsets, 0.0))
        if offset_allowance_from_s is None:
            has_allowance = is_calibrated
        else:
            has_allowance = np.full(LEG_COUNT, t_s[row] > offset_allowance_from_s + 1e-9)
        monitor.set_offset_allowance_N(np.where(has_allowance, allowance, 0.0))
        for leg, first_row in enumerate(fallback_rows):
            if first_row == row:
                monitor.rod_state[leg] = RodSensorState.FALLBACK
        forces = monitor.read(float(t_s[row]), head[row], rod[row], acting[row],
                              bool(is_ready[row]), seal_band[row], stroke_m=stroke[row],
                              r5_fallback_ratios=choice)
        lower[row] = forces.lower
        for leg in range(LEG_COUNT):
            inputs[row, leg] = monitor.r5_fallback_inputs(leg)
    return FallbackMonitorReplay(lower, inputs, fallback_rows)


def _offline_monitor(geometry: C2Geometry, config: C2Config) -> TwoPressureMonitor:
    """The monitor of ``C2Controller.__init__`` with the diagnosis off."""
    return TwoPressureMonitor(
        geometry.head_area_m2,
        geometry.annulus_area_m2,
        geometry.max_speed_m_s,
        geometry.F_min_N,
        config.period_s,
        config.load_estimate,
        replace(config.two_pressure, diagnostics=False),
        geometry.rod_weight_N,
        stroke_max_m=geometry.stroke_max_m,
        retract_lock_rod_pressure_Pa=geometry.rod_lock_pressure_after_retract_Pa,
        counterbalance_lag_tau_s=geometry.counterbalance_lag_tau_s,
        body_mass_kg=geometry.superstructure_mass_kg,
        imu_lever_arm_m=geometry.imu_lever_arm_m,
    )


def watched_samples(episode: Episode) -> NDArray[np.bool_]:
    """Samples scored by the 203.3 metrics: lifted (crawler off the floor, spec 205.1) and
    with a truth value on every leg."""
    has_truth = np.all(np.isfinite(episode["true_force_min_N"]), axis=1)
    return np.asarray(episode["is_lifted"], dtype=bool) & has_truth


def record_judgement(episode: Episode, replay: JudgeReplay) -> RecordJudgement:
    """Metric input (:mod:`outrigger_sim.verify.contact_metrics`) of one judge on one record."""
    return RecordJudgement(
        t_s=np.asarray(episode["t_s"], dtype=float),
        classes=truth_classes(episode["true_force_min_N"], episode.rod_weight_N,
                              episode.F_min_N),
        decision_flags=replay.decision_flags,
        action_flags=replay.action_flags,
        estimate_N=replay.load_estimate_N,
        true_force_N=np.asarray(episode["true_force_N"], dtype=float),
        true_force_min_N=np.asarray(episode["true_force_min_N"], dtype=float),
        watched=watched_samples(episode),
    )
