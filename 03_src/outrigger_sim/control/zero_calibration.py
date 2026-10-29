"""CHECK airborne round-trip zero calibration of the pressure force readings (E-3, U71).

``00_docs/04_control/s6_control_spec.md`` 72.1 (1)-(2), 76.1 E-3 and 76.2. During CHECK the
four legs are in the air (the crawler stands). They extend ``+3 mm`` together at
``0.25 v_max``, hold 0.5 s, retract ``-3 mm`` and hold 0.5 s. With ``F_e`` and ``F_r`` the
mean readings of the two holds,

    c_i = (F_e + F_r) / 2 + m_rod,i g        (net-force zero offset of the leg)
    F_s,air = (F_e - F_r) / 2                (seal friction in the air, recorded only)

and the controller uses ``F_hat - c_i`` from then on. Failure handling (76.2): an implausible
offset (``|c_i|`` above 7 kN front / 6 kN rear), a leg already grounded at the start, a leg
that cannot make the +-3 mm or an unsteady hold (std above 0.5 kN) keeps ``c_i = 0`` and gets
the E-6 lower-bound allowance (5.5 / 4.0 kN) for the rest of the run. The retract counts as
returned at or below the start stroke; with ``return_timeout_tolerance_m`` set (spec 416.3,
R8 preset 0.5 mm) a leg that came within it is accepted at the time-out instead of skipped.

Engine independent: it sees the motor strokes and the force readings of the controller.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum, StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER
from outrigger_sim.signals import LEG_COUNT

TIME_SLACK_S = 1e-9
FRONT_REAR = (0, 0, 1, 1)


def _per_leg(front: float, rear: float) -> tuple[float, ...]:
    return tuple((front, rear)[side] for side in FRONT_REAR)


class ZeroCalibrationMode(StrEnum):
    """E-3 setting ``zero_calibration``."""

    AIRBORNE_ROUNDTRIP = "airborne_roundtrip"
    """Calibrate in CHECK (U71 default)."""
    OFF = "off"
    """No calibration (legacy presets): CHECK as before, bit for bit."""


class LegCalibrationStatus(StrEnum):
    CALIBRATED = "calibrated"
    IMPLAUSIBLE = "implausible"
    SKIPPED = "skipped"


class SkipReason(StrEnum):
    """Why a leg could not make the round trip (``WARN_PRESSURE_ZERO_SKIPPED:<leg>:<reason>``)."""

    GROUNDED = "grounded"
    STROKE_END = "stroke_end"
    MOVE = "move"
    UNSTEADY = "unsteady"
    NO_CHECK = "no_check"
    """Calibration on but CHECK has no length (76.4 (3) a): all four legs, one event."""


@dataclass(frozen=True)
class ZeroCalibrationSettings:
    """E-3 / E-6 settings (spec 76.1, 76.2); per-leg tuples follow LEG_ORDER."""

    mode: ZeroCalibrationMode = ZeroCalibrationMode.AIRBORNE_ROUNDTRIP
    move_m: float = 3e-3
    speed_fraction: float = 0.25
    """Move speed as a fraction of ``v_max``."""
    hold_s: float = 0.5
    plausible_offset_N: tuple[float, ...] = _per_leg(7000.0, 6000.0)
    """``|c_i|`` limit (front: 5 bar head + 5 bar rod side equivalent; rear 6 kN)."""
    max_hold_std_N: float = 500.0
    """A hold whose readings scatter more than this (1 sigma) is unsteady."""
    max_hold_std_per_leg_N: tuple[float, ...] | None = None
    """R8 R-3 (spec 99.3): per-leg limit instead of ``max_hold_std_N``, ``sigma_0
    sqrt(chi2_{9, 0.999} / 9)`` = 0.73 kN front / 0.53 kN rear for a 10-sample hold;
    ``None`` = ``max_hold_std_N`` on every leg."""
    hold_std_ddof: int = 0
    """Delta degrees of freedom of the hold scatter (R-3 derives its limit from the sample
    variance, ``ddof = 1``; 0 = the population scatter of R6)."""
    air_seal_friction_record_N: float = 15e3
    """``F_s,air`` above this is recorded (info event), not acted on."""
    move_timeout_factor: float = 3.0
    """A move fails when it takes longer than this times its nominal duration."""
    return_timeout_tolerance_m: float | None = None
    """Spec 416.3 (variant D, user decision 2026-10-29): at the retract time-out a leg whose
    smallest displacement of the retract stage is at most this counts as returned
    (``INFO_PRESSURE_ZERO_RETURN_TOL:<leg>:<mm>``) instead of ``skipped: move``. The single
    noisy start sample and the full-retraction hard stop otherwise leave about 10 % of the
    legs unable to read ``<= 0``. ``None`` = the old rule (class default, bit identical)."""
    failure_allowance_N: tuple[float, ...] = _per_leg(5500.0, 4000.0)
    """E-6 allowance of a leg whose calibration failed (normal-grade maximum, 75.2)."""
    recalibration_temperature_change_K: float = 15.0
    """E-5 / 72.1 (5): ``WARN_PRESSURE_RECAL_DUE`` when the oil temperature moved this far
    from the calibration (ASSUMPTION: about 0.3 % of span = 1.1 bar)."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ZeroCalibrationMode(self.mode))
        for name in ("move_m", "speed_fraction", "hold_s", "move_timeout_factor"):
            if not getattr(self, name) > 0.0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)!r}")
        for name in ("plausible_offset_N", "failure_allowance_N"):
            values = tuple(float(value) for value in getattr(self, name))
            if len(values) != LEG_COUNT or min(values) < 0.0:
                raise ValueError(f"{name}: expected {LEG_COUNT} values >= 0, got {values!r}")
            object.__setattr__(self, name, values)
        if self.max_hold_std_per_leg_N is not None:
            limits = tuple(float(value) for value in self.max_hold_std_per_leg_N)
            if len(limits) != LEG_COUNT or min(limits) <= 0.0:
                raise ValueError(f"max_hold_std_per_leg_N: expected {LEG_COUNT} values > 0")
            object.__setattr__(self, "max_hold_std_per_leg_N", limits)
        if self.hold_std_ddof not in (0, 1):
            raise ValueError(f"hold_std_ddof must be 0 or 1, got {self.hold_std_ddof!r}")
        tolerance_m = self.return_timeout_tolerance_m
        if tolerance_m is not None and not tolerance_m >= 0.0:
            raise ValueError(f"return_timeout_tolerance_m must be >= 0, got {tolerance_m!r}")

    @property
    def is_enabled(self) -> bool:
        return self.mode is ZeroCalibrationMode.AIRBORNE_ROUNDTRIP

    def max_hold_std_for_leg_N(self, leg: int) -> float:
        """Unsteady-hold limit of ``leg`` (per-leg R-3 value or the common one)."""
        if self.max_hold_std_per_leg_N is None:
            return self.max_hold_std_N
        return self.max_hold_std_per_leg_N[leg]

    def to_meta(self) -> dict[str, Any]:
        """Settings for the run meta; the spec 416.3 key appears only when in use."""
        meta = asdict(self)
        meta["mode"] = str(self.mode)
        if self.return_timeout_tolerance_m is None:
            del meta["return_timeout_tolerance_m"]
        return {key: list(value) if isinstance(value, tuple) else value
                for key, value in meta.items()}


@dataclass(frozen=True)
class LegCalibration:
    """Calibration result of one leg.

    Attributes:
        status: Calibrated, implausible or skipped.
        offset_N: ``c_i`` applied (0 unless calibrated).
        measured_offset_N: ``c_i`` from the holds (``None`` when no hold was measured).
        air_seal_friction_N: ``F_s,air`` (``None`` when no hold was measured).
        allowance_N: E-6 allowance this result asks for (0 when calibrated).
        reason: Skip reason, ``None`` otherwise.
    """

    status: LegCalibrationStatus
    offset_N: float = 0.0
    measured_offset_N: float | None = None
    air_seal_friction_N: float | None = None
    allowance_N: float = 0.0
    reason: SkipReason | None = None

    @property
    def is_calibrated(self) -> bool:
        return self.status is LegCalibrationStatus.CALIBRATED

    def to_meta(self) -> dict[str, Any]:
        meta = asdict(self)
        meta["status"] = str(self.status)
        meta["reason"] = None if self.reason is None else str(self.reason)
        return meta


class _Stage(Enum):
    EXTEND = "extend"
    HOLD_EXTENDED = "hold_extended"
    RETRACT = "retract"
    HOLD_RETRACTED = "hold_retracted"
    DONE = "done"


_MOVE_STAGES = {_Stage.EXTEND: 1.0, _Stage.RETRACT: -1.0}
_NEXT_STAGE = {
    _Stage.EXTEND: _Stage.HOLD_EXTENDED,
    _Stage.HOLD_EXTENDED: _Stage.RETRACT,
    _Stage.RETRACT: _Stage.HOLD_RETRACTED,
    _Stage.HOLD_RETRACTED: _Stage.DONE,
}


class ZeroCalibration:
    """One airborne round trip of the four legs (module docstring).

    Args:
        settings: E-3 settings.
        max_speed_m_s: ``v_max``.
        rod_weight_N: ``m_rod g`` per leg (4,).
        stroke_limit_m: Highest stroke a leg may be moved to (soft stroke end).
    """

    def __init__(
        self,
        settings: ZeroCalibrationSettings,
        max_speed_m_s: float,
        rod_weight_N: ArrayLike,
        stroke_limit_m: float,
    ) -> None:
        self.settings = settings
        self.speed_m_s = settings.speed_fraction * float(max_speed_m_s)
        self.rod_weight_N = np.asarray(rod_weight_N, dtype=float)
        self.stroke_limit_m = float(stroke_limit_m)
        self._move_timeout_s = settings.move_timeout_factor * settings.move_m / self.speed_m_s
        self._stage = _Stage.EXTEND
        self._stage_start_s = 0.0
        self._start_stroke_m = np.zeros(LEG_COUNT)
        self._active = np.zeros(LEG_COUNT, dtype=bool)
        self._reached = np.zeros(LEG_COUNT, dtype=bool)
        self._min_displacement_m = np.full(LEG_COUNT, np.inf)
        self._skipped: dict[int, SkipReason] = {}
        self._returned_within_tolerance_m: dict[int, float] = {}
        """Spec 416.3: legs whose retract was accepted at the time-out -> smallest displacement."""
        self._holds: dict[_Stage, list[NDArray[np.float64]]] = {
            _Stage.HOLD_EXTENDED: [],
            _Stage.HOLD_RETRACTED: [],
        }
        self._reused: dict[int, LegCalibration] = {}
        self.results: tuple[LegCalibration, ...] | None = None
        self.t_start_s: float | None = None
        self.t_end_s: float | None = None

    @property
    def is_finished(self) -> bool:
        return self.results is not None

    def start(
        self,
        t_s: float,
        motor_stroke_m: ArrayLike,
        is_grounded: ArrayLike,
        reused: dict[int, LegCalibration] | None = None,
    ) -> None:
        """First CHECK period: grounded legs and legs without +3 mm of room are skipped.

        ``reused``: results of legs calibrated by an earlier CHECK of the run (76.4 (3) b);
        they keep that result, do not move and raise no new event.
        """
        strokes = np.asarray(motor_stroke_m, dtype=float)
        grounded = np.asarray(is_grounded, dtype=bool)
        self.t_start_s = float(t_s)
        self._start_stroke_m = strokes.copy()
        self._reused = dict(reused or {})
        for leg in range(LEG_COUNT):
            if leg in self._reused:
                continue
            if grounded[leg]:
                self._skipped[leg] = SkipReason.GROUNDED
            elif strokes[leg] + self.settings.move_m > self.stroke_limit_m:
                self._skipped[leg] = SkipReason.STROKE_END
        self._active = np.array(
            [leg not in self._skipped and leg not in self._reused for leg in range(LEG_COUNT)]
        )
        self._enter(_Stage.EXTEND, t_s)
        if not self._active.any():
            self._finish(t_s)

    def skip_all(self, t_s: float, reason: SkipReason) -> None:
        """No round trip at all (76.4 (3) a): every leg skipped, with its allowance."""
        self.t_start_s = float(t_s)
        self._skipped = dict.fromkeys(range(LEG_COUNT), reason)
        self._active = np.zeros(LEG_COUNT, dtype=bool)
        self._finish(t_s)

    def step(
        self, t_s: float, motor_stroke_m: ArrayLike, force_N: ArrayLike
    ) -> NDArray[np.float64]:
        """Leg speeds of this period (zero once finished)."""
        speeds = np.zeros(LEG_COUNT)
        if self.is_finished:
            return speeds
        stage = self._stage
        if stage in _MOVE_STAGES:
            return self._move(t_s, np.asarray(motor_stroke_m, dtype=float), _MOVE_STAGES[stage])
        self._holds[stage].append(np.asarray(force_N, dtype=float).copy())
        if t_s - self._stage_start_s >= self.settings.hold_s - TIME_SLACK_S:
            self._enter(_NEXT_STAGE[stage], t_s)
            if self._stage is _Stage.DONE:
                self._finish(t_s)
        return speeds

    def _enter(self, stage: _Stage, t_s: float) -> None:
        self._stage = stage
        self._stage_start_s = float(t_s)
        self._reached = np.zeros(LEG_COUNT, dtype=bool)
        self._min_displacement_m = np.full(LEG_COUNT, np.inf)

    def _move(self, t_s: float, strokes: NDArray[np.float64], sign: float) -> NDArray:
        """Move the active legs to +move_m (extend) or back to the start (retract)."""
        displacement = strokes - self._start_stroke_m
        if sign > 0.0:
            self._reached |= displacement >= self.settings.move_m
        else:
            self._reached |= displacement <= 0.0
            self._min_displacement_m = np.minimum(self._min_displacement_m, displacement)
        if t_s - self._stage_start_s > self._move_timeout_s + TIME_SLACK_S:
            if sign < 0.0:
                self._accept_returns_within_tolerance()
            for leg in np.flatnonzero(self._active & ~self._reached):
                self._skipped[int(leg)] = SkipReason.MOVE
                self._active[leg] = False
        moving = self._active & ~self._reached
        if not moving.any():
            self._enter(_NEXT_STAGE[self._stage], t_s)
            return np.zeros(LEG_COUNT)
        return np.where(moving, sign * self.speed_m_s, 0.0)

    def _accept_returns_within_tolerance(self) -> None:
        """Spec 416.3 (3): at the retract time-out a leg that came within the tolerance of its
        start stroke counts as returned (stroke noise against the full-retraction stop)."""
        tolerance_m = self.settings.return_timeout_tolerance_m
        if tolerance_m is None:
            return
        for leg in np.flatnonzero(self._active & ~self._reached):
            if self._min_displacement_m[leg] <= tolerance_m:
                self._reached[leg] = True
                self._returned_within_tolerance_m[int(leg)] = float(
                    self._min_displacement_m[leg]
                )

    def _finish(self, t_s: float) -> None:
        self.t_end_s = float(t_s)
        self.results = tuple(self._leg_result(leg) for leg in range(LEG_COUNT))

    def _leg_result(self, leg: int) -> LegCalibration:
        if leg in self._reused:
            return self._reused[leg]
        allowance = self.settings.failure_allowance_N[leg]
        if leg in self._skipped:
            return LegCalibration(
                LegCalibrationStatus.SKIPPED, allowance_N=allowance, reason=self._skipped[leg]
            )
        extended = np.array([sample[leg] for sample in self._holds[_Stage.HOLD_EXTENDED]])
        retracted = np.array([sample[leg] for sample in self._holds[_Stage.HOLD_RETRACTED]])
        ddof = self.settings.hold_std_ddof
        scatter_N = max(extended.std(ddof=ddof), retracted.std(ddof=ddof))
        is_unsteady = scatter_N > self.settings.max_hold_std_for_leg_N(leg)
        if is_unsteady:
            return LegCalibration(
                LegCalibrationStatus.SKIPPED, allowance_N=allowance, reason=SkipReason.UNSTEADY
            )
        force_extended, force_retracted = float(extended.mean()), float(retracted.mean())
        offset = 0.5 * (force_extended + force_retracted) + float(self.rod_weight_N[leg])
        friction = 0.5 * (force_extended - force_retracted)
        if abs(offset) > self.settings.plausible_offset_N[leg]:
            return LegCalibration(
                LegCalibrationStatus.IMPLAUSIBLE,
                measured_offset_N=offset,
                air_seal_friction_N=friction,
                allowance_N=allowance,
            )
        return LegCalibration(
            LegCalibrationStatus.CALIBRATED,
            offset_N=offset,
            measured_offset_N=offset,
            air_seal_friction_N=friction,
        )

    # --- results ---

    @property
    def offsets_N(self) -> NDArray[np.float64]:
        if self.results is None:
            return np.zeros(LEG_COUNT)
        return np.array([result.offset_N for result in self.results])

    @property
    def allowance_N(self) -> NDArray[np.float64]:
        if self.results is None:
            return np.zeros(LEG_COUNT)
        return np.array([result.allowance_N for result in self.results])

    def events(self) -> list[tuple[str, bool]]:
        """(name, is_warning) of the finished calibration (76.2)."""
        if self.results is None:
            return []
        if set(self._skipped.values()) == {SkipReason.NO_CHECK}:
            return [(f"WARN_PRESSURE_ZERO_SKIPPED:all:{SkipReason.NO_CHECK}", True)]
        events: list[tuple[str, bool]] = []
        for leg, result in enumerate(self.results):
            if leg in self._reused:
                continue
            name = LEG_ORDER[leg]
            if leg in self._returned_within_tolerance_m:
                min_displacement_mm = 1e3 * self._returned_within_tolerance_m[leg]
                events.append(
                    (f"INFO_PRESSURE_ZERO_RETURN_TOL:{name}:{min_displacement_mm:.3f}", False)
                )
            if result.status is LegCalibrationStatus.IMPLAUSIBLE:
                events.append((f"WARN_PRESSURE_ZERO_IMPLAUSIBLE:{name}", True))
            elif result.status is LegCalibrationStatus.SKIPPED:
                events.append((f"WARN_PRESSURE_ZERO_SKIPPED:{name}:{result.reason}", True))
            else:
                events.append((f"INFO_PRESSURE_ZERO_CALIBRATED:{name}", False))
            friction = result.air_seal_friction_N
            if friction is not None and friction > self.settings.air_seal_friction_record_N:
                events.append((f"INFO_PRESSURE_ZERO_AIR_FRICTION_HIGH:{name}", False))
        if all(result.status is not LegCalibrationStatus.CALIBRATED for result in self.results):
            events.append(("WARN_PRESSURE_ZERO_ALL_FAILED", True))
        return events

    def to_meta(self) -> dict[str, Any]:
        """Run meta; the spec 416.3 key appears only with the tolerance setting on."""
        meta: dict[str, Any] = {
            "t_start_s": self.t_start_s,
            "t_end_s": self.t_end_s,
            "reused_legs": [LEG_ORDER[leg] for leg in sorted(self._reused)],
            "legs": (
                None
                if self.results is None
                else {LEG_ORDER[leg]: result.to_meta() for leg, result in enumerate(self.results)}
            ),
        }
        if self.settings.return_timeout_tolerance_m is not None:
            meta["return_within_tolerance_m"] = {
                LEG_ORDER[leg]: value
                for leg, value in sorted(self._returned_within_tolerance_m.items())
            }
        return meta
