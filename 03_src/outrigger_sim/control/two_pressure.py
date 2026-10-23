"""Two-pressure load reading of C2 R6-P: net force, sensor diagnosis, fallback, rod-side watch.

``00_docs/04_control/s6_control_spec.md`` 51.1 (P-1 .. P-8), 53.3 (diagnosis thresholds and the
fallback of U45), 53.4 (P-9 .. P-13) and 61.3 (P-15, P-16); user decisions U43 .. U52. Engine
independent: it sees the delivered head and rod-side pressures, the controller's own leg
commands and its phase.

* Load estimate (P-2, U43): ``F = p_h A_p - p_r A_ann`` per leg (``net``); ``head_only`` and a
  measurement without a rod-side pressure give ``p_h A_p``, the R5 reading bit for bit.
* Diagnosis (P-4, 53.3): D1 range / step / stuck / NaN on both sensors, D2 rod side while
  extending, D3 while retracting (off by default), D4 physical lower bound when locked (held
  2 samples / 0.1 s, spec 110.2), D5 sum of the load changes in READY (warning only, held
  ``sum_hold_s``), D6 probe
  consistency (off by default). The geometry / pressure conflicts D7 (K-3, K-6) are raised by
  the controller's GE2 step.
* Load baseline (spec 110.1): D5, the E-5 drift and ``Delta F1`` compare against a baseline of
  their own, stored by the controller in READY / DONE after the commands have been zero for
  ``load_reference_settle_s`` (never at the TOUCH end), and are judged only while the commands
  stay zero that long. The baseline is the mean of the command-free readings of the stay over
  ``load_reference_mean_s`` (spec 120), not one sample on the heave ringing.
* Fallback (P-5, U45 = 53.3): a rod-side fault switches that leg alone, latched, to the head
  reading with a model upper bound of the rod-side pressure ``p_r_hat`` removed for the lower
  bound judgements (``lower``); BELOW uses the head reading plus the -0.9 bar floor
  (``upper``); the twist loop keeps the head reading (``nominal``). A head-side fault is a
  FAULT of the run.
* Rod-side watch (P-13, U46): locked ``p_r`` above 350 / 300 bar, predicted lift-off pressure
  ``p_r + r (F + m_rod g) / A_ann`` above 350 bar, a slow rise without load change (info).
* Shadows (no command depends on them, ``shadow_`` events): the load drop ``Delta F1`` against
  the load baseline (P-6, U47) and the retraction lift-off confirmation of the one-sided band
  (P-11, U50).

Every threshold here depends on the cylinder dimensions; the defaults are the values of spec 53
for the YAML cylinder and are settings only, to be replaced after the REXOME35 recalculation
(spec 61.2, 61.3). Units SI (Pa, N, m, s); per-leg arrays follow ``LEG_ORDER``.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER
from outrigger_sim.sensors.pressure_error import (
    SIGNAL_CURRENT_RANGE_MA,
    pressure_to_current_mA,
)
from outrigger_sim.signals import LEG_COUNT

BAR_PA = 1e5

# R8 (10 Hz) diagnosis constants, spec rev. 29 126 #3 (ASSUMPTION where the spec says so)
R8_LOAD_REFERENCE_SETTLE_S = 0.5
R8_LOAD_REFERENCE_MEAN_S = 1.5
R8_D4_MIN_SAMPLES = 2
R8_D4_HOLD_S = 0.2
R8_SUM_HOLD_S = 0.5
R8_DRIFT_HOLD_S = 30.0


class LoadEstimate(StrEnum):
    """Load estimate of C2 (P-2, U43)."""

    NET = "net"
    """``p_h A_p - p_r A_ann`` when a rod-side pressure is measured (R6 default)."""
    HEAD_ONLY = "head_only"
    """``p_h A_p`` (R5; the rod-side pressure is ignored)."""


class RodSensorState(StrEnum):
    OK = "ok"
    FALLBACK = "fallback"


class HeadSensorState(StrEnum):
    OK = "ok"
    FAULT = "fault"


FRONT_REAR = (0, 0, 1, 1)
"""Index of the front / rear value of a per-leg pair, LEG_ORDER (FL, FR, RL, RR)."""


def _per_leg(front: float, rear: float) -> tuple[float, ...]:
    return tuple((front, rear)[side] for side in FRONT_REAR)


ROD_WEIGHT_WITHOUT_YAML_N = _per_leg(1047.0, 701.0)
"""``m_rod g`` for monitors built without the YAML (tests); the controller passes the YAML
moving-part masses (spec 76.4 (2))."""


def _four(values: ArrayLike, name: str) -> NDArray[np.float64]:
    array = np.array(np.broadcast_to(np.asarray(values, dtype=float), (LEG_COUNT,)))
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name}: expected {LEG_COUNT} finite values, got {values!r}")
    return array


@dataclass(frozen=True)
class TwoPressureSettings:
    """Thresholds of the two-pressure reading (spec 64.2 defaults for the REXOME35 cylinders,
    replacing 53.3 / 53.4; every value ASSUMPTION unless the spec says otherwise).

    Names follow the spec items; ``*_Pa`` gauge pressures, ``*_N`` cylinder forces; tuples are
    per leg (LEG_ORDER).
    """

    diagnostics: bool = True
    """Run D1-D6, the fallback and the rod-side watch (``False`` = net force only)."""
    # D1
    sensor_range_Pa: tuple[float, float] = (-6.0 * BAR_PA, 410.0 * BAR_PA)
    """U72 (spec 72, 76.1): raw-value range; a normal sensor reads about -1.3 bar at 0 bar,
    which the old [-1, 400] bar range judged a fault."""
    signal_current_range_mA: tuple[float, float] | None = SIGNAL_CURRENT_RANGE_MA
    """U72: a reading whose 4-20 mA current lies outside this range (NAMUR NE 43) is a
    fault; ``None`` = no current check."""
    max_step_Pa: float = 100.0 * BAR_PA
    """Largest change of one reading in one period."""
    pressure_noise_std_Pa: float = 0.0
    """Sensor noise of the run (0.3 bar for the specified sensors, P-16): widens the range by
    3 sigma and enables the stuck check (a reading that did not change over
    ``stuck_window_s``). 0 for ideal sensors (no stuck check)."""
    stuck_window_s: float = 10.0
    # D2 / D3
    moving_speed_fraction: float = 0.25
    moving_settle_s: float = 1.0
    """D2 / D3 judge a leg after a continuous move this long (64.2: >= 1 s)."""
    reversal_exclusion_s: float = 2.0
    """D2: not checked for this long after a retract -> extend reversal (64.2 R-H5: the
    pressure of the retraction end stays 128-191 bar into the next extension)."""
    extend_min_head_Pa: float = 20.0 * BAR_PA
    extend_rod_range_Pa: tuple[float, float] = (-1.0 * BAR_PA, 12.0 * BAR_PA)
    violation_hold_s: float = 1.0
    retract_check: bool = True
    """D3 (64.2): lower bound ``0.5 (3 + (p_h - 3) / 6 + 1)`` bar, upper 215 bar."""
    retract_pilot_ratio: float = 6.0
    retract_head_back_Pa: float = 3.0 * BAR_PA
    retract_cracking_Pa: float = 1.0 * BAR_PA
    retract_upper_Pa: float = 215.0 * BAR_PA
    # D4 / D5
    force_sigma_N: tuple[float, ...] = _per_leg(414.0, 300.0)
    """1 sigma of one two-sensor force reading (0.3 bar per sensor, 64.2)."""
    d4_min_samples: int = 2
    d4_hold_s: float = 0.1
    """110.2 (ASSUMPTION, 3 x the 30 ms M4 window): D4 falls back only after at least
    ``d4_min_samples`` violating samples in a row covering ``d4_hold_s`` (samples x period);
    the first violating sample is ``INFO_ROD_D4_TRANSIENT``."""
    sum_extra_N: float = 2500.0
    sum_hold_s: float = 0.5
    """D5 warns only when the sum change stays beyond its limit this long while judged
    (ASSUMPTION, not in spec 110.1): a floor event's dynamic transient (RE1b-F replay: sum
    -63 kN while the body drops, before the controller's first re-level command) is no sensor
    inconsistency; a static mismatch persists. 0 = the first sample warns."""
    load_reference_settle_s: float = 0.5
    """110.1 (ASSUMPTION: U67 tail 0.3 s + a few heave periods): the load baseline of D5, E-5
    and ``Delta F1`` needs every leg command zero for this long, and they are judged only
    while that holds."""
    load_reference_mean_s: float = 0.5
    """120 (ASSUMPTION, R7 25 samples): the load baseline is the mean nominal reading over this
    long before the store, so the 8.7 Hz heave ringing after a tail or probe does not bias it
    (one sample: up to -3.4 kN). Only command-free samples of the READY / DONE stay count; a
    value up to one period is the single-sample baseline of 110.1."""
    # D6
    probe_consistency_check: bool = True
    """D6 (64.2): ``p_r`` at the R hold end - at the E hold end >= max(3 bar, p_h / 12)."""
    probe_rise_min_Pa: float = 3.0 * BAR_PA
    probe_rise_head_ratio: float = 1.0 / 12.0
    probe_misses: int = 2
    # fallback (U45 a', 64.2)
    fallback_extend_Pa: float = 8.0 * BAR_PA
    fallback_pilot_ratio: float = 3.0
    fallback_head_back_Pa: float = 15.0 * BAR_PA
    fallback_cracking_Pa: float = 3.0 * BAR_PA
    fallback_locked_ratio: tuple[float, ...] = _per_leg(1.296, 1.232)
    """``-dp_r / dp_h`` of a locked leg (D8 ratio, hydraulics 12.2)."""
    fallback_floor_Pa: float = -0.9 * BAR_PA
    fallback_min_band_N: float = 13e3
    """U65: the friction band of a fallback leg is at least this (its head-only F_s estimate
    and probe midpoint are not used)."""
    # rod-side watch (P-13)
    rod_limit_Pa: float = 350.0 * BAR_PA
    """``rod_pressure_limit_Pa`` (ASSUMPTION 350 bar until the rod-side rating, Q-R5)."""
    rod_warning_margin_Pa: float = 5.0 * BAR_PA
    """E-4 (U72): ``rod_pressure_over_limit`` is raised above ``rod_limit_Pa`` minus this
    (345 bar; the sensor error near 350 bar is about 3 bar after the calibration)."""
    rod_prewarning_Pa: float = 300.0 * BAR_PA
    liftoff_rod_share: tuple[float, ...] = _per_leg(0.269, 0.289)
    """U49 ``r`` (upper value, L_0r 0.05 m; hydraulics 12.2)."""
    rod_weight_N: tuple[float, ...] | None = None
    """``m_rod g`` per leg; ``None`` = the YAML ``legs.<leg>.moving_part.mass_kg`` x g given
    to the monitor (spec 76.4 (2), single source), or :data:`ROD_WEIGHT_WITHOUT_YAML_N`
    without one."""
    rising_window_s: float = 10.0
    rising_min_Pa: float = 5.0 * BAR_PA
    rising_load_tolerance_N: float = 3000.0
    # shadows
    load_drop_N: float = 20000.0
    """P-6 (U47): ``Delta F`` below ``-load_drop_N`` for ``load_drop_hold_s``."""
    load_drop_hold_s: float = 0.5
    retract_speed_fraction: float = 0.1
    retract_settle_s: float = 0.3
    retract_average_s: float = 0.5
    retract_pad_limit_N: float = 2500.0
    """P-11 (U50): retraction lift-off when ``mean F + F_band + m_rod g`` is below this."""
    # E-5 static load sum drift (72.1 (6), U73)
    drift_sum_N: float | None = 4000.0
    """``WARN_PRESSURE_DRIFT`` when ``|sum F - sum F_ref|`` stays above this for
    ``drift_hold_s`` in READY (ASSUMPTION: 4 x 0.6 kN calibration residue + noise margin);
    ``None`` = off. Only the change of the sum is used, never ``sum F = W``."""
    drift_hold_s: float = 30.0

    def with_r8_period(self) -> TwoPressureSettings:
        """Copy with the 10 Hz (R8) diagnosis constants of spec rev. 29 126 #3.

        Load baseline settle 0.5 s (5 samples) and mean 1.5 s (15 samples, twice the 0.77 s
        period of the 8.7 Hz heave aliased to 1.3 Hz, ASSUMPTION), D4 two samples = 0.2 s
        (110.2), D5 hold 0.5 s (5 samples), E-5 hold 30 s. Only these fields are touched.
        """
        return replace(
            self,
            load_reference_settle_s=R8_LOAD_REFERENCE_SETTLE_S,
            load_reference_mean_s=R8_LOAD_REFERENCE_MEAN_S,
            d4_min_samples=R8_D4_MIN_SAMPLES,
            d4_hold_s=R8_D4_HOLD_S,
            sum_hold_s=R8_SUM_HOLD_S,
            drift_hold_s=R8_DRIFT_HOLD_S,
        )

    def to_meta(self) -> dict[str, Any]:
        return {key: list(value) if isinstance(value, tuple) else value
                for key, value in asdict(self).items()}


@dataclass(frozen=True, eq=False)
class PressureForces:
    """Cylinder-force readings of one period (N, (4,) each).

    Attributes:
        nominal: The load reading: net force, the head reading on a fallback leg (twist loop,
            completion, GE1' deflection, REANCHOR stop).
        lower: Lower-bound reading for ABOVE, guard, P5, Q2 and the probe: ``nominal`` except
            on a fallback leg (head reading minus ``p_r_hat A_ann``).
        upper: Upper-bound reading for BELOW (fallback leg: head reading plus the floor).
        head_only: ``p_h A_p`` (P-3: the 350 bar check uses the raw head pressure).
    """

    nominal: NDArray[np.float64]
    lower: NDArray[np.float64]
    upper: NDArray[np.float64]
    head_only: NDArray[np.float64]


@dataclass
class _LegWatch:
    """Per-leg bookkeeping of the diagnosis."""

    moving_since_s: float | None = None
    moving_sign: float = 0.0
    violation_since_s: float | None = None
    rod_estimate_Pa: float = 0.0
    lock_rod_estimate_Pa: float | None = None
    lock_head_Pa: float | None = None
    load_drop_since_s: float | None = None
    d4_violation_samples: int = 0
    probe_misses: int = 0
    retract_samples: int = 0
    last_retract_t_s: float = -math.inf


@dataclass
class _ReadyBaseline:
    """Load baseline of D5, E-5 and ``Delta F1`` (110.1; no longer the GE1' reference)."""

    loads_N: NDArray[np.float64]
    t_s: float
    is_active: bool = True
    """``False`` from a new READY / DONE stay until the next store (stale baseline)."""
    load_drop_flagged: set[int] = field(default_factory=set)
    sum_mismatch_since_s: float | None = None
    """D5: start of the unbroken run of judged samples with the sum change beyond the limit."""
    is_sum_warned: bool = False
    drift_since_s: float | None = None
    """E-5: start of the unbroken run of samples with the sum change above the limit."""
    drift_fallback_count: int = 0
    """Fallback legs at the start of that run (a new fallback is an event: the run restarts)."""


class TwoPressureMonitor:
    """Net force, diagnosis, fallback and rod-side watch of the four legs (module docstring).

    Args:
        head_area_m2: ``A_p`` per leg (4,).
        annulus_area_m2: ``A_ann`` per leg (4,).
        max_speed_m_s: ``v_max`` (moving conditions).
        F_min_N: ``F_min`` (a leg is grounded for D2 / D3 when ``F - F_band >= F_min``).
        period_s: Control period.
        load_estimate: ``net`` or ``head_only``.
        settings: Thresholds.
        rod_weight_N: ``m_rod g`` per leg from the YAML; an explicit
            ``settings.rod_weight_N`` wins.
    """

    def __init__(
        self,
        head_area_m2: ArrayLike,
        annulus_area_m2: ArrayLike,
        max_speed_m_s: float,
        F_min_N: float,
        period_s: float,
        load_estimate: LoadEstimate = LoadEstimate.NET,
        settings: TwoPressureSettings | None = None,
        rod_weight_N: ArrayLike | None = None,
    ) -> None:
        self.head_area_m2 = np.asarray(head_area_m2, dtype=float)
        self.annulus_area_m2 = np.asarray(annulus_area_m2, dtype=float)
        self.max_speed_m_s = float(max_speed_m_s)
        self.F_min_N = float(F_min_N)
        self.period_s = float(period_s)
        self.load_estimate = LoadEstimate(load_estimate)
        self.settings = settings or TwoPressureSettings()
        weight = self.settings.rod_weight_N
        if weight is None:
            weight = ROD_WEIGHT_WITHOUT_YAML_N if rod_weight_N is None else rod_weight_N
        self.rod_weight_N = _four(weight, "rod_weight_N")
        self.reset()

    def reset(self) -> None:
        self.rod_state = [RodSensorState.OK] * LEG_COUNT
        self.head_state = [HeadSensorState.OK] * LEG_COUNT
        self.has_rod_sensor = False
        """A rod-side pressure was seen (and used) in this run."""
        # start = locked after an extension (rod side at the return back pressure)
        start_estimate = self.settings.fallback_extend_Pa
        self._legs = [_LegWatch(rod_estimate_Pa=start_estimate) for _ in range(LEG_COUNT)]
        self._previous: tuple[NDArray[np.float64], NDArray[np.float64] | None] | None = None
        window = max(1, round(self.settings.stuck_window_s / self.period_s))
        self._stuck_history: deque[tuple[NDArray, NDArray | None]] = deque(maxlen=window)
        rising = max(1, round(self.settings.rising_window_s / self.period_s))
        self._ready_history: deque[tuple[NDArray, NDArray]] = deque(maxlen=rising)
        self._retract_history: deque[NDArray] = deque(
            maxlen=max(1, round(self.settings.retract_average_s / self.period_s)))
        self._history: deque[tuple[float, NDArray, NDArray | None]] = deque(
            maxlen=max(1, round(20.0 / self.period_s)))
        self._baseline: _ReadyBaseline | None = None
        self._command_free_samples: int | None = None
        """Reads in a row whose acting command was zero on every leg; ``None`` = no command
        seen yet (command-free since ever, as the controller's GE1'-c count)."""
        mean_samples = max(1, round(self.settings.load_reference_mean_s / self.period_s))
        self._load_samples: deque[NDArray[np.float64]] = deque(maxlen=mean_samples)
        """120: command-free nominal readings of the current READY / DONE stay (newest last),
        averaged into the load baseline; emptied by a command and by a new stay."""
        self._load_reference_log: list[dict[str, Any]] = []
        self._load_sum_log: list[dict[str, Any]] = []
        self._reported: set[str] = set()
        self._events: list[tuple[str, bool]] = []
        self.zero_offsets_N = np.zeros(LEG_COUNT)
        """E-3: ``c_i`` removed from every force reading (CHECK zero calibration)."""
        self.offset_allowance_N = np.zeros(LEG_COUNT)
        """E-6: deduction of the lower-bound reading (the larger of it and the fallback
        bound is used, never both)."""

    # --- public ---

    @property
    def fallback_legs(self) -> list[int]:
        return [leg for leg, state in enumerate(self.rod_state) if state is RodSensorState.FALLBACK]

    @property
    def head_fault_legs(self) -> list[int]:
        return [leg for leg, state in enumerate(self.head_state) if state is HeadSensorState.FAULT]

    def set_zero_offsets_N(self, offsets_N: ArrayLike) -> None:
        """E-3: net-force zero offsets ``c_i`` removed from now on (0 = not calibrated)."""
        self.zero_offsets_N = _four(offsets_N, "offsets_N")

    def set_offset_allowance_N(self, allowance_N: ArrayLike) -> None:
        """E-6: lower-bound deduction per leg from now on (``>= 0``)."""
        allowance = _four(allowance_N, "allowance_N")
        if np.any(allowance < 0.0):
            raise ValueError(f"allowance_N: expected values >= 0, got {allowance_N!r}")
        self.offset_allowance_N = allowance

    def pop_events(self) -> list[tuple[str, bool]]:
        """(name, is_warning) raised since the last call."""
        events, self._events = self._events, []
        return events

    def read(
        self,
        t_s: float,
        head_pressure_Pa: NDArray[np.float64],
        rod_pressure_Pa: NDArray[np.float64] | None,
        commanded_m_s: NDArray[np.float64],
        is_locked_phase: bool,
        seal_band_N: float | NDArray[np.float64],
    ) -> PressureForces:
        """One period: the force readings; diagnosis and watch events go to :meth:`pop_events`.

        ``commanded_m_s`` = the controller's output of the previous period (what the legs do
        now); ``is_locked_phase`` = READY (legs locked, D4 / D5 / rod-side watch).
        """
        self._count_command_free(commanded_m_s)
        head_only = head_pressure_Pa * self.head_area_m2
        if rod_pressure_Pa is None or self.load_estimate is LoadEstimate.HEAD_ONLY:
            forces = self._corrected(PressureForces(head_only, head_only, head_only, head_only))
            self._collect_load_sample(forces.nominal)
            if self.settings.diagnostics:
                self._watch_drift(t_s, forces.nominal, is_locked_phase)
            return forces
        self.has_rod_sensor = True
        rod = np.asarray(rod_pressure_Pa, dtype=float)
        if self.settings.diagnostics:
            net = head_only - rod * self.annulus_area_m2
            if self._has_zero_offsets:
                net = net - self.zero_offsets_N
            grounded = net - seal_band_N >= self.F_min_N
            self._diagnose_sensors(t_s, head_pressure_Pa, rod, commanded_m_s, grounded)
        self._update_rod_estimates(t_s, head_pressure_Pa, rod, commanded_m_s)
        forces = self._forces(head_pressure_Pa, rod, head_only)
        self._collect_load_sample(forces.nominal)
        if self.settings.diagnostics:
            self._check_locked(t_s, rod, forces, is_locked_phase, seal_band_N)
            self._watch_retraction(forces.nominal, commanded_m_s, seal_band_N)
            self._watch_drift(t_s, forces.nominal, is_locked_phase)
        self._history.append((float(t_s), np.array(rod), np.array(head_pressure_Pa)))
        return forces

    @property
    def command_free_s(self) -> float:
        """Time every leg command has been zero up to the last read (``inf`` before any
        command); the command read at ``t`` acted over the period before ``t``."""
        if self._command_free_samples is None:
            return math.inf
        return self._command_free_samples * self.period_s

    @property
    def is_load_watch_open(self) -> bool:
        """110.1 (4): D5, E-5 and ``Delta F1`` are judged now (active baseline, commands zero
        for ``load_reference_settle_s``)."""
        baseline = self._baseline
        if baseline is None or not baseline.is_active:
            return False
        return self.command_free_s >= self.settings.load_reference_settle_s - 1e-9

    def store_load_reference(
        self, t_s: float, loads_N: NDArray[np.float64], source: str = ""
    ) -> None:
        """Store the load baseline of D5, E-5 and ``Delta F1`` (110.1, 120).

        The controller calls this on the first READY / DONE period with the GE1'-c gate open
        and the commands zero for ``load_reference_settle_s``, never at the TOUCH end. The
        baseline is the mean of the command-free readings of this stay over the last
        ``load_reference_mean_s`` (this period's reading included); ``loads_N`` is used only
        when none is buffered. The sum change against the previous baseline is logged (the
        sum should not change).

        Args:
            t_s: Time of the reading.
            loads_N: Nominal cylinder-force readings of this period (4,).
            source: Phase that stored it (meta).
        """
        sample_count = len(self._load_samples)
        if sample_count:
            loads = np.mean(np.array(self._load_samples), axis=0)
        else:
            loads = np.array(loads_N, dtype=float)
        sum_N = float(np.sum(loads))
        previous = self._baseline
        previous_sum_N = None if previous is None else float(np.sum(previous.loads_N))
        sum_change_N = None if previous_sum_N is None else sum_N - previous_sum_N
        self._load_reference_log.append({
            "t_s": float(t_s),
            "source": source,
            "sum_N": sum_N,
            "previous_sum_N": previous_sum_N,
            "sum_change_N": sum_change_N,
            "mean_window_s": self.settings.load_reference_mean_s,
            "sample_count": max(sample_count, 1),
            "last_sample_sum_N": float(np.sum(loads_N)),
        })
        self._baseline = _ReadyBaseline(loads, float(t_s))

    def suspend_load_reference(self) -> None:
        """A new READY / DONE stay began: the old baseline is not judged until the next
        :meth:`store_load_reference` (110.1 (5)), and the readings of the stay before are
        dropped from the baseline mean; the newest one, read in the period that entered the
        stay, is kept when command-free (120)."""
        newest = self._load_samples[-1] if self._load_samples else None
        self._load_samples.clear()
        if newest is not None:
            self._load_samples.append(newest)
        if self._baseline is not None:
            self._baseline.is_active = False
            self._baseline.drift_since_s = None

    def load_change_N(self, loads_N: NDArray[np.float64]) -> NDArray[np.float64] | None:
        """``F - F(t_ref)`` against the last load baseline (``None`` before one)."""
        if self._baseline is None:
            return None
        return np.asarray(loads_N, dtype=float) - self._baseline.loads_N

    def probe_round_finished(self, results) -> None:
        """D6 (off by default): the rod side must rise from the extend hold to the retract
        hold of a probe (31-37 bar trapped after a retraction, 53.3)."""
        if not (self.settings.diagnostics and self.settings.probe_consistency_check):
            return
        for result in results:
            leg = result.leg_index
            if result.is_skipped or self.rod_state[leg] is RodSensorState.FALLBACK:
                continue
            extend_s, retract_s = result.t_first_hold_end_s, result.t_second_hold_end_s
            if result.is_reversed:
                extend_s, retract_s = retract_s, extend_s
            at_extend, at_retract = self._sample_at(extend_s), self._sample_at(retract_s)
            if at_extend is None or at_retract is None:
                continue
            rise = at_retract[0][leg] - at_extend[0][leg]
            required = max(self.settings.probe_rise_min_Pa,
                           self.settings.probe_rise_head_ratio * at_retract[1][leg])
            watch = self._legs[leg]
            watch.probe_misses = watch.probe_misses + 1 if rise < required else 0
            if watch.probe_misses >= self.settings.probe_misses:
                self._fall_back(leg, "D6")

    def leg_seal_bands_N(self, seal_band_N: float) -> NDArray[np.float64]:
        """U65: per-leg friction band; a fallback leg takes at least ``fallback_min_band_N``."""
        bands = np.full(LEG_COUNT, float(seal_band_N))
        for leg in self.fallback_legs:
            bands[leg] = max(bands[leg], self.settings.fallback_min_band_N)
        return bands

    def meta(self) -> dict[str, Any]:
        return {
            "load_estimate": str(self.load_estimate),
            "has_rod_sensor": self.has_rod_sensor,
            "rod_sensor_state": {LEG_ORDER[i]: str(s) for i, s in enumerate(self.rod_state)},
            "head_sensor_state": {LEG_ORDER[i]: str(s) for i, s in enumerate(self.head_state)},
            "fallback_rod_estimate_Pa": [w.rod_estimate_Pa for w in self._legs],
            "zero_offsets_N": self.zero_offsets_N.tolist(),
            "offset_allowance_N": self.offset_allowance_N.tolist(),
            "head_area_m2": self.head_area_m2.tolist(),
            "annulus_area_m2": self.annulus_area_m2.tolist(),
            "rod_weight_N": self.rod_weight_N.tolist(),
            "load_reference": list(self._load_reference_log),
            "load_sum_events": list(self._load_sum_log),
            "settings": self.settings.to_meta(),
        }

    # --- events ---

    def _event_once(self, name: str, is_warning: bool = True) -> None:
        if name not in self._reported:
            self._reported.add(name)
            self._events.append((name, is_warning))

    def _fall_back(self, leg: int, reason: str) -> None:
        if self.rod_state[leg] is RodSensorState.FALLBACK:
            return
        self.rod_state[leg] = RodSensorState.FALLBACK
        self._event_once(f"WARN_ROD_PRESSURE_FALLBACK:{LEG_ORDER[leg]}")
        self._event_once(f"INFO_ROD_PRESSURE_FAULT_REASON:{LEG_ORDER[leg]}:{reason}", False)

    def _head_fault(self, leg: int) -> None:
        if self.head_state[leg] is HeadSensorState.FAULT:
            return
        self.head_state[leg] = HeadSensorState.FAULT
        self._event_once(f"FAULT_HEAD_PRESSURE:{LEG_ORDER[leg]}")

    # --- D1, D2, D3 ---

    def _diagnose_sensors(self, t_s, head, rod, commanded, grounded) -> None:
        head_previous, rod_previous = self._previous or (None, None)
        for leg in self._sensor_faults(head, head_previous):
            self._head_fault(leg)
        for leg in self._sensor_faults(rod, rod_previous):
            self._fall_back(leg, "D1")
        self._stuck_history.append((np.array(head), np.array(rod)))
        for name, legs in self._stuck_legs().items():
            for leg in legs:
                if name == "head":
                    self._head_fault(leg)
                else:
                    self._fall_back(leg, "D1_stuck")
        self._previous = (np.array(head), np.array(rod))
        self._check_moving(t_s, head, rod, commanded, grounded)

    def _sensor_faults(
        self, values: NDArray[np.float64], previous: NDArray[np.float64] | None
    ) -> list[int]:
        """D1: not finite, outside the range (widened by 3 sigma of the noise), or a jump."""
        settings = self.settings
        margin = 3.0 * settings.pressure_noise_std_Pa
        low, high = settings.sensor_range_Pa
        with np.errstate(invalid="ignore"):
            bad = ~np.isfinite(values) | (values < low - margin) | (values > high + margin)
            if settings.signal_current_range_mA is not None:
                current_low, current_high = settings.signal_current_range_mA
                current = pressure_to_current_mA(values)
                bad |= (current < current_low) | (current > current_high)
            if previous is not None:
                bad |= np.abs(values - previous) > settings.max_step_Pa
        return [int(leg) for leg in np.flatnonzero(bad)]

    def _stuck_legs(self) -> dict[str, list[int]]:
        """D1 stuck: a reading that did not change at all over the window (noise > 0 only)."""
        history = self._stuck_history
        if self.settings.pressure_noise_std_Pa <= 0.0 or len(history) < history.maxlen:
            return {}
        out = {}
        for index, name in ((0, "head"), (1, "rod")):
            samples = np.array([entry[index] for entry in history])
            with np.errstate(invalid="ignore"):
                spread = np.ptp(samples, axis=0)
            out[name] = [int(leg) for leg in np.flatnonzero(spread == 0.0)]
        return out

    def _check_moving(self, t_s, head, rod, commanded, grounded) -> None:
        """D2 (extend) and D3 (retract) on a grounded leg moving for the settle time; D2 not
        within ``reversal_exclusion_s`` of a retraction (R-H5)."""
        settings = self.settings
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            sign = self._moving_sign(commanded[leg], settings.moving_speed_fraction)
            if commanded[leg] < 0.0:
                watch.last_retract_t_s = float(t_s)
            if sign != watch.moving_sign:
                watch.moving_sign, watch.moving_since_s = sign, (t_s if sign else None)
                watch.violation_since_s = None
            if not sign or not grounded[leg]:
                continue
            if t_s - watch.moving_since_s < settings.moving_settle_s - 1e-9:
                continue
            after_retract_s = t_s - watch.last_retract_t_s
            if sign > 0 and after_retract_s < settings.reversal_exclusion_s - 1e-9:
                continue
            is_violation = self._moving_violation(sign, head[leg], rod[leg])
            if is_violation is None:
                continue
            if not is_violation:
                watch.violation_since_s = None
                continue
            if watch.violation_since_s is None:
                watch.violation_since_s = t_s
            if t_s - watch.violation_since_s >= settings.violation_hold_s - 1e-9:
                self._fall_back(leg, "D2" if sign > 0 else "D3")

    def _moving_sign(self, command_m_s: float, fraction: float) -> float:
        if abs(command_m_s) < fraction * self.max_speed_m_s:
            return 0.0
        return math.copysign(1.0, command_m_s)

    def _moving_violation(self, sign: float, head_Pa: float, rod_Pa: float) -> bool | None:
        """``None`` when the check does not apply."""
        settings = self.settings
        if not math.isfinite(rod_Pa) or head_Pa < settings.extend_min_head_Pa:
            return None
        if sign > 0:
            low, high = settings.extend_rod_range_Pa
            return not low <= rod_Pa <= high
        if not settings.retract_check:
            return None
        threshold = (settings.retract_head_back_Pa
                     + (head_Pa - settings.retract_head_back_Pa) / settings.retract_pilot_ratio
                     + settings.retract_cracking_Pa)
        return not 0.5 * threshold <= rod_Pa <= settings.retract_upper_Pa

    # --- fallback estimate (53.3) ---

    def _update_rod_estimates(self, t_s, head, rod, commanded) -> None:
        """Model upper bound ``p_r_hat`` of every leg (used on fallback legs only)."""
        settings = self.settings
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            command = commanded[leg]
            if command > 0.0:
                watch.rod_estimate_Pa = settings.fallback_extend_Pa
                watch.lock_rod_estimate_Pa = None
            elif command < 0.0:
                back = settings.fallback_head_back_Pa
                watch.rod_estimate_Pa = (back + (head[leg] - back) / settings.fallback_pilot_ratio
                                         + settings.fallback_cracking_Pa)
                watch.lock_rod_estimate_Pa = None
            else:
                if watch.lock_rod_estimate_Pa is None:
                    watch.lock_rod_estimate_Pa = watch.rod_estimate_Pa
                    watch.lock_head_Pa = float(head[leg])
                head_drop = max(0.0, watch.lock_head_Pa - float(head[leg]))
                watch.rod_estimate_Pa = (watch.lock_rod_estimate_Pa
                                         + settings.fallback_locked_ratio[leg] * head_drop)

    def _forces(self, head, rod, head_only) -> PressureForces:
        net = head_only - rod * self.annulus_area_m2
        fallback = np.zeros(LEG_COUNT, dtype=bool)
        fallback[self.fallback_legs] = True
        if not fallback.any():
            return self._corrected(PressureForces(net, net, net, head_only))
        estimate = np.array([watch.rod_estimate_Pa for watch in self._legs])
        nominal = np.where(fallback, head_only, net)
        upper = np.where(
            fallback, head_only - self.settings.fallback_floor_Pa * self.annulus_area_m2, net)
        if not self._has_offset_allowance:
            lower = np.where(fallback, head_only - estimate * self.annulus_area_m2, net)
            return self._corrected(PressureForces(nominal, lower, upper, head_only))
        # 76.2: only the larger of the fallback bound and the E-6 allowance is deducted.
        fallback_bound = np.where(fallback, estimate * self.annulus_area_m2, 0.0)
        deduction = np.maximum(fallback_bound, self.offset_allowance_N)
        offsets = self.zero_offsets_N
        return PressureForces(
            nominal - offsets, nominal - offsets - deduction, upper - offsets, head_only
        )

    @property
    def _has_zero_offsets(self) -> bool:
        return bool(np.any(self.zero_offsets_N != 0.0))

    @property
    def _has_offset_allowance(self) -> bool:
        return bool(np.any(self.offset_allowance_N != 0.0))

    def _corrected(self, forces: PressureForces) -> PressureForces:
        """E-3 offsets off every reading but ``head_only``, E-6 allowance off ``lower``.

        Without offsets and allowance the readings pass unchanged (same arrays), so the
        uncalibrated runs stay bit for bit."""
        if not (self._has_zero_offsets or self._has_offset_allowance):
            return forces
        offsets = self.zero_offsets_N
        nominal = forces.nominal - offsets
        lower = forces.lower - offsets - self.offset_allowance_N
        upper = forces.upper - offsets
        return PressureForces(nominal, lower, upper, forces.head_only)

    # --- locked checks: D4, D5, rod-side watch, Delta F1 ---

    def _check_locked(self, t_s, rod, forces, is_locked_phase, seal_band_N) -> None:
        if not is_locked_phase:
            self._ready_history.clear()
            for watch in self._legs:
                watch.load_drop_since_s = None
                watch.d4_violation_samples = 0
            return
        self._check_physical_lower_bound(forces.nominal, seal_band_N)
        self._watch_rod_side(rod, forces.nominal)
        self._ready_history.append((np.array(rod), np.array(forces.nominal)))
        self._watch_rising_rod_pressure()
        if self.is_load_watch_open:
            self._watch_load_changes(t_s, forces.nominal, seal_band_N)
            return
        for watch in self._legs:
            watch.load_drop_since_s = None
        if self._baseline is not None:
            self._baseline.sum_mismatch_since_s = None

    def _check_physical_lower_bound(self, loads, seal_band_N) -> None:
        """D4 with the 110.2 hold: a reading below ``-(m_rod g + F_band) - 3 sigma`` falls the
        leg back only after ``d4_min_samples`` samples in a row covering ``d4_hold_s``; a
        shorter dip (an M4 drop transient read by one sample) is ``INFO_ROD_D4_TRANSIENT``."""
        settings = self.settings
        lower_bound = -(self.rod_weight_N + seal_band_N) - 3.0 * np.array(
            settings.force_sigma_N)
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            is_judged = (self.rod_state[leg] is RodSensorState.OK
                         and self.head_state[leg] is not HeadSensorState.FAULT)
            if not (is_judged and loads[leg] < lower_bound[leg]):
                watch.d4_violation_samples = 0
                continue
            watch.d4_violation_samples += 1
            if watch.d4_violation_samples == 1:
                self._events.append((f"INFO_ROD_D4_TRANSIENT:{LEG_ORDER[leg]}", False))
            held_s = watch.d4_violation_samples * self.period_s
            if (watch.d4_violation_samples >= settings.d4_min_samples
                    and held_s >= settings.d4_hold_s - 1e-9):
                self._fall_back(leg, "D4")

    def _watch_rod_side(self, rod, loads) -> None:
        settings = self.settings
        share = np.array(settings.liftoff_rod_share)
        predicted = rod + share * (loads + self.rod_weight_N) / self.annulus_area_m2
        warning_Pa = settings.rod_limit_Pa - settings.rod_warning_margin_Pa
        for leg in range(LEG_COUNT):
            if self.rod_state[leg] is RodSensorState.FALLBACK or not math.isfinite(rod[leg]):
                continue
            name = LEG_ORDER[leg]
            if rod[leg] > warning_Pa:
                self._event_once(f"rod_pressure_over_limit:{name}")
            if rod[leg] > settings.rod_prewarning_Pa:
                self._event_once(f"rod_pressure_prewarning:{name}")
            if predicted[leg] > settings.rod_limit_Pa:
                self._event_once(f"WARN_ROD_LIFTOFF_OVERPRESSURE_RISK:{name}")

    def _watch_rising_rod_pressure(self) -> None:
        """P-13 (4): ``p_r`` up by ``rising_min_Pa`` over the window without a load change."""
        history = self._ready_history
        if len(history) < history.maxlen:
            return
        settings = self.settings
        count = max(1, round(1.0 / self.period_s))
        rods = np.array([entry[0] for entry in history])
        loads = np.array([entry[1] for entry in history])
        rise = rods[-count:].mean(axis=0) - rods[:count].mean(axis=0)
        load_change = np.abs(loads[-count:].mean(axis=0) - loads[:count].mean(axis=0))
        rising = (rise >= settings.rising_min_Pa) & (load_change < settings.rising_load_tolerance_N)
        for leg in np.flatnonzero(rising):
            self._event_once(f"INFO_ROD_PRESSURE_RISING:{LEG_ORDER[leg]}", False)

    def _watch_load_changes(self, t_s, loads, seal_band_N) -> None:
        """P-6 ``Delta F1`` shadow and the D5 sum check against the load baseline (called only
        while :attr:`is_load_watch_open`)."""
        baseline = self._baseline
        settings = self.settings
        change = loads - baseline.loads_N
        allowed = 4.0 * float(np.max(seal_band_N)) + settings.sum_extra_N
        if abs(float(change.sum())) <= allowed:
            baseline.sum_mismatch_since_s = None
        elif baseline.sum_mismatch_since_s is None:
            baseline.sum_mismatch_since_s = float(t_s)
        is_held = (baseline.sum_mismatch_since_s is not None
                   and t_s - baseline.sum_mismatch_since_s >= settings.sum_hold_s - 1e-9)
        if is_held and not baseline.is_sum_warned:
            baseline.is_sum_warned = True
            self._events.append(("WARN_LOAD_SUM_MISMATCH", True))
            self._log_load_sum_event(t_s, "WARN_LOAD_SUM_MISMATCH", loads, allowed)
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            if change[leg] >= -settings.load_drop_N:
                watch.load_drop_since_s = None
                continue
            if watch.load_drop_since_s is None:
                watch.load_drop_since_s = t_s
            held = t_s - watch.load_drop_since_s >= settings.load_drop_hold_s - 1e-9
            if held and leg not in baseline.load_drop_flagged:
                baseline.load_drop_flagged.add(leg)
                self._events.append((f"shadow_load_drop:{LEG_ORDER[leg]}", False))

    # --- E-5 static load sum drift ---

    def _watch_drift(self, t_s: float, loads: NDArray[np.float64], is_locked_phase: bool) -> None:
        """72.1 (6): ``|sum F - sum F_ref| > drift_sum_N`` for ``drift_hold_s`` in READY with
        no external-force event meanwhile (a load-drop condition or a new fallback restarts
        the hold) -> ``WARN_PRESSURE_DRIFT`` once per run. Judged only while
        :attr:`is_load_watch_open` (110.1): a command restarts the hold."""
        settings = self.settings
        baseline = self._baseline
        is_judged = is_locked_phase and self.is_load_watch_open
        if settings.drift_sum_N is None or baseline is None or not is_judged:
            if baseline is not None:
                baseline.drift_since_s = None
            return
        change = abs(float(np.sum(loads) - np.sum(baseline.loads_N)))
        is_disturbed = any(watch.load_drop_since_s is not None for watch in self._legs)
        fallback_count = len(self.fallback_legs)
        if change <= settings.drift_sum_N or is_disturbed:
            baseline.drift_since_s = None
            return
        if baseline.drift_since_s is None or fallback_count != baseline.drift_fallback_count:
            baseline.drift_since_s = float(t_s)
            baseline.drift_fallback_count = fallback_count
        if t_s - baseline.drift_since_s >= settings.drift_hold_s - 1e-9:
            if "WARN_PRESSURE_DRIFT" not in self._reported:
                self._log_load_sum_event(t_s, "WARN_PRESSURE_DRIFT", loads, settings.drift_sum_N)
            self._event_once("WARN_PRESSURE_DRIFT")

    def _log_load_sum_event(self, t_s, name, loads, allowed_N) -> None:
        """110.1: sum, baseline sum and limit of a D5 / E-5 warning (meta ``load_sum_events``)."""
        self._load_sum_log.append({
            "t_s": float(t_s),
            "event": name,
            "sum_N": float(np.sum(loads)),
            "reference_sum_N": float(np.sum(self._baseline.loads_N)),
            "reference_t_s": self._baseline.t_s,
            "allowed_N": float(allowed_N),
        })

    def _count_command_free(self, commanded_m_s) -> None:
        if np.any(np.asarray(commanded_m_s) != 0.0):
            self._command_free_samples = 0
        elif self._command_free_samples is not None:
            self._command_free_samples += 1

    def _collect_load_sample(self, loads_N: NDArray[np.float64]) -> None:
        """120: buffer a command-free reading for the baseline mean; a command empties it."""
        if self._command_free_samples == 0:
            self._load_samples.clear()
            return
        self._load_samples.append(np.array(loads_N, dtype=float))

    # --- P-11 retraction lift-off shadow ---

    def _watch_retraction(self, loads, commanded, seal_band_N) -> None:
        """P-11 (U50, shadow): while a leg retracts at >= the speed fraction, after the settle
        time, the mean net force over the last ``retract_average_s`` plus ``F_band`` and the
        rod weight is the upper bound of the pad force (one-sided band: retracting reads
        ``L - F_s``); below ``retract_pad_limit_N`` the lift-off is confirmed (once per
        retraction)."""
        settings = self.settings
        self._retract_history.append(np.array(loads))
        settle = round(settings.retract_settle_s / self.period_s)
        average = self._retract_history.maxlen or 1
        threshold = settings.retract_speed_fraction * self.max_speed_m_s
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            key = f"shadow_retract_liftoff:{LEG_ORDER[leg]}"
            if commanded[leg] > -threshold:
                watch.retract_samples = 0
                self._reported.discard(key)  # one confirmation per retraction
                continue
            watch.retract_samples += 1
            if watch.retract_samples < settle + average:
                continue
            mean_load = float(np.mean([entry[leg] for entry in self._retract_history]))
            band = float(np.broadcast_to(seal_band_N, LEG_COUNT)[leg])
            if mean_load + band + self.rod_weight_N[leg] < settings.retract_pad_limit_N:
                self._event_once(key, False)

    def _sample_at(self, t_s: float):
        if not math.isfinite(t_s) or not self._history:
            return None
        nearest = min(self._history, key=lambda entry: abs(entry[0] - t_s))
        if abs(nearest[0] - t_s) > self.period_s:
            return None
        return nearest[1], nearest[2]
