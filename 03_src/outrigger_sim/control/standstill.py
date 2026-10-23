"""Gyro standstill pieces of C2 R5: CHECK gyro bias estimate (B1') and the standstill gate (GE1').

``00_docs/04_control/s6_control_spec.md`` revision 7, sections 38, 39 and 42.1, with revision 8
section 45.1 (user decisions U35-a, U36-a, U40-a, U41-a of 2026-10-22). Engine independent, no
controller state: :class:`C2Controller` feeds the samples.

All RMS values are taken about the window mean (deviation RMS) and noise-corrected,
``sqrt(max(0, RMS^2 - sigma_g^2))``; the mean itself is the bias estimate (B1') or condition
(b) of the gate (spec 44.4).

* B1' (:func:`gyro_bias_window_s`, :func:`gyro_bias_motion_limit_rad_s`): the gyro bias is the
  mean rate of the last ``T_b`` of the CHECK standstill, ``T_b = clamp(T (sigma_g /
  sigma_b*)^2, check_time_s, check_max_s)`` (ideal 2 s, good 2.5 s, normal 10 s), and only when
  that window is quiet: RMS per axis ``<= min(0.01 sqrt(T_b / 2), 0.02) deg/s`` (R5-B: a longer
  window leaves less of the rocking in the mean). A window that is never quiet before
  ``check_max_s`` leaves the bias unremoved; an estimate above the plausibility limit
  (60 deg/h) is discarded.
* Standstill gate (:class:`StandstillGate`, spec 38 / 44.1): per axis, bias removed, (a) 1.0 s
  RMS <= 0.02 deg/s (R5-G: 0.5 s left the gate open only 79-86 % of a still normal-grade
  record) and (b) 1.0 s mean ``|w|`` <= 0.02 deg/s, both held 0.5 s without a
  break, together with every leg command 0 for 1.0 s and an allowed phase. The GE1' stroke
  geometry is evaluated only while the gate is open (the 2nd-order attitude filter lags about
  1 s, so a turning body reads as false pad heights, spec 32.1).

``sigma_g`` is the per-sample gyro noise of the grade (``ImuErrorConfig.gyro_noise_std_rad_s``;
ASSUMPTION in simulation, the data-sheet ARW on the machine). Units SI (rad/s, s).
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np

AXIS_COUNT = 2
"""Roll and pitch rate."""
TIME_SLACK_S = 1e-9
"""Float sample times (k T) may miss a window length by rounding."""


def deg_per_hour(value_deg_h: float) -> float:
    """Convert deg/h to rad/s."""
    return math.radians(value_deg_h) / 3600.0


def noise_corrected_rms(rms_rad_s: float, noise_std_rad_s: float) -> float:
    """``sqrt(max(0, RMS^2 - sigma^2))``: the RMS left after the sensor white noise."""
    return math.sqrt(max(0.0, rms_rad_s * rms_rad_s - noise_std_rad_s * noise_std_rad_s))


# --- B1': CHECK gyro bias -----------------------------------------------------------------


def gyro_bias_window_s(
    noise_std_rad_s: float,
    target_std_rad_s: float,
    sample_period_s: float,
    min_window_s: float,
    max_window_s: float,
) -> float:
    """Averaging length ``T_b`` that brings the bias noise to ``target_std_rad_s`` (spec 39).

    The mean of ``n = T_b / T`` white samples of std ``sigma_g`` has std ``sigma_g / sqrt(n)``,
    so ``T_b = T (sigma_g / sigma_b*)^2``, clamped to ``[min_window_s, max_window_s]``.
    """
    unclamped_s = sample_period_s * (noise_std_rad_s / target_std_rad_s) ** 2
    return min(max(unclamped_s, min_window_s), max_window_s)


def gyro_bias_motion_limit_rad_s(
    window_s: float, base_limit_rad_s: float, base_window_s: float, cap_rad_s: float
) -> float:
    """``omega_th(T_b) = min(base sqrt(T_b / base_window), cap)`` (spec 44.2, R5-B).

    The 1.3 Hz rocking leaves at most ``A / (pi f T_b)`` in the window mean, so a longer window
    tolerates more motion for the same residue: 0.01 deg/s at 2 s, 0.0112 at 2.5 s, the cap
    0.02 deg/s at 10 s (residue <= 2.5 deg/h there).
    """
    return min(base_limit_rad_s * math.sqrt(window_s / base_window_s), cap_rad_s)


class GyroBiasOutcome(StrEnum):
    """What the end of CHECK did with the gyro bias."""

    ACCEPTED = "accepted"
    """Removed from the rate-integrated attitude."""
    SKIPPED_MOTION = "skipped_motion"
    """The window was never quiet before ``check_max_s``: not removed (WARN_GYRO_BIAS_SKIPPED)."""
    REJECTED_IMPLAUSIBLE = "rejected_implausible"
    """Above the plausibility limit: not removed (WARN_GYRO_BIAS_IMPLAUSIBLE)."""
    NO_CHECK = "no_check"
    """``check_time_s = 0``: no standstill, nothing measured."""


@dataclass(frozen=True)
class GyroBiasEstimate:
    """Result of the B1' estimate at the end of CHECK (meta, cad records).

    Attributes:
        outcome: What was done with the estimate.
        window_s: Planned averaging length ``T_b``.
        check_duration_s: CHECK length up to this decision (``>= check_time_s``).
        estimate_rad_s: Window mean (roll, pitch) rate, ``None`` with ``NO_CHECK``; kept for the
            record even when it was not accepted.
        motion_rms_rad_s: Noise-corrected RMS about the window mean per axis of the last
            window judged, ``None`` with ``NO_CHECK``.
        motion_limit_rad_s: ``omega_th(T_b)`` the RMS was judged against (``None`` = no motion
            condition, R4.1 settings, or ``NO_CHECK``).
    """

    outcome: GyroBiasOutcome
    window_s: float
    check_duration_s: float
    estimate_rad_s: tuple[float, float] | None = None
    motion_rms_rad_s: tuple[float, float] | None = None
    motion_limit_rad_s: float | None = None

    @property
    def is_accepted(self) -> bool:
        return self.outcome is GyroBiasOutcome.ACCEPTED

    @property
    def bias_rad_s(self) -> tuple[float, float] | None:
        """The bias to remove: the estimate when accepted, else ``None``."""
        return self.estimate_rad_s if self.is_accepted else None

    def to_meta(self) -> dict[str, Any]:
        return {
            "outcome": str(self.outcome),
            "is_accepted": self.is_accepted,
            "window_s": self.window_s,
            "check_duration_s": self.check_duration_s,
            "estimate_rad_s": None if self.estimate_rad_s is None else list(self.estimate_rad_s),
            "motion_rms_rad_s": (
                None if self.motion_rms_rad_s is None else list(self.motion_rms_rad_s)
            ),
            "motion_limit_rad_s": self.motion_limit_rad_s,
        }


@dataclass(frozen=True)
class GyroWindowStatistics:
    """Mean and noise-corrected RMS about the mean of one window, per axis."""

    mean_rad_s: tuple[float, float]
    motion_rms_rad_s: tuple[float, float]


def window_statistics(
    times_s: Sequence[float],
    rates_rad_s: Sequence[tuple[float, float]],
    end_t_s: float,
    window_s: float,
    noise_std_rad_s: float,
) -> GyroWindowStatistics:
    """Statistics of the samples with ``t >= end_t_s - window_s`` (both ends included).

    The mean is ``np.mean`` over the selected samples in their order, so a window that holds
    every CHECK sample gives the R4.1 bias bit for bit.
    """
    times = np.asarray(times_s, dtype=float)
    rates = np.array(rates_rad_s, dtype=float).reshape(-1, AXIS_COUNT)
    selected = rates[times >= end_t_s - window_s - TIME_SLACK_S]
    mean = np.mean(selected, axis=0)
    rms_about_mean = np.sqrt(np.mean((selected - mean) ** 2, axis=0))
    motion = tuple(noise_corrected_rms(float(rms), noise_std_rad_s) for rms in rms_about_mean)
    return GyroWindowStatistics((float(mean[0]), float(mean[1])), (motion[0], motion[1]))


# --- GE1': standstill gate ----------------------------------------------------------------


@dataclass(frozen=True)
class StandstillGateSettings:
    """Standstill gate of spec 38 / 44.1 (U35-a, U40-a); the defaults are the decided values
    (ASSUMPTION)."""

    rate_rms_limit_rad_s: float = math.radians(0.02)
    """(a) Noise-corrected RMS about the window mean over ``rms_window_s`` per axis (rocking)."""
    rms_window_s: float = 1.0
    """R5-G (U40-a): 1.0 s (50 samples); 0.5 s in the first R5 draft."""
    mean_rate_limit_rad_s: float = math.radians(0.02)
    """(b) ``|mean rate|`` over ``mean_window_s`` per axis (slow tilting; 1 s filter lag x
    0.02 deg/s x 2.4 m arm = 0.84 mm, inside the 2.5 mm budget of d)."""
    mean_window_s: float = 1.0
    hold_s: float = 0.5
    """(a) and (b) must hold this long without a break."""
    zero_command_s: float = 1.0
    """Every leg command must have been 0 this long (the attitude filter lag)."""

    def __post_init__(self) -> None:
        windows = (self.rms_window_s, self.mean_window_s)
        if min(windows) <= 0.0 or self.hold_s < 0.0 or self.zero_command_s < 0.0:
            raise ValueError("gate windows must be > 0 and hold / zero-command times >= 0")


@dataclass(frozen=True)
class StandstillGateState:
    """Gate values of one period (cad records it with asdict every period).

    Attributes:
        is_open: ``is_geometry_valid``.
        is_phase_allowed: Phase DONE, PROBE or READY.
        zero_command_duration_s: Time every leg command has been 0 (``None`` = never moved).
        rates_quiet_since_s: Start of the unbroken run of (a) and (b), ``None`` if broken.
        motion_rms_rad_s: (a) noise-corrected RMS per axis, ``None`` until the windows fill.
        mean_rate_rad_s: (b) window mean rate per axis, ``None`` until the windows fill.
    """

    is_open: bool
    is_phase_allowed: bool
    zero_command_duration_s: float | None
    rates_quiet_since_s: float | None
    motion_rms_rad_s: tuple[float, float] | None
    mean_rate_rad_s: tuple[float, float] | None


class StandstillGate:
    """Per-period standstill gate ``is_geometry_valid`` (spec 38, 42.1 GE1'-c).

    Args:
        settings: Limits and windows.
        noise_std_rad_s: Per-sample gyro noise ``sigma_g`` of the grade.
        period_s: Control period (sets the window sample counts).
    """

    def __init__(
        self, settings: StandstillGateSettings, noise_std_rad_s: float, period_s: float
    ) -> None:
        self.settings = settings
        self.noise_std_rad_s = noise_std_rad_s
        self._rms_samples = max(1, round(settings.rms_window_s / period_s))
        self._mean_samples = max(1, round(settings.mean_window_s / period_s))
        self._rates: deque[tuple[float, float]] = deque(
            maxlen=max(self._rms_samples, self._mean_samples)
        )
        self.reset()

    def reset(self) -> None:
        self._rates.clear()
        self.is_open = False
        self.rates_quiet_since_s: float | None = None
        self.motion_rms_rad_s: tuple[float, float] | None = None
        self.mean_rate_rad_s: tuple[float, float] | None = None
        self.zero_command_duration_s = 0.0
        self.is_phase_allowed = False

    def update(
        self,
        t_s: float,
        rate_rad_s: tuple[float, float],
        zero_command_duration_s: float,
        is_phase_allowed: bool,
    ) -> bool:
        """Add one bias-removed (roll, pitch) rate sample; returns whether the gate is open."""
        self._rates.append(rate_rad_s)
        self.zero_command_duration_s = zero_command_duration_s
        self.is_phase_allowed = is_phase_allowed
        are_rates_quiet = self._are_rates_quiet()
        if not are_rates_quiet:
            self.rates_quiet_since_s = None
        elif self.rates_quiet_since_s is None:
            self.rates_quiet_since_s = t_s
        settings = self.settings
        has_held = (
            self.rates_quiet_since_s is not None
            and t_s - self.rates_quiet_since_s >= settings.hold_s - TIME_SLACK_S
        )
        has_stopped = zero_command_duration_s >= settings.zero_command_s - TIME_SLACK_S
        self.is_open = bool(is_phase_allowed and has_stopped and has_held)
        return self.is_open

    def _are_rates_quiet(self) -> bool:
        """(a) and (b) on full windows; ``False`` until enough samples are in."""
        if len(self._rates) < max(self._rms_samples, self._mean_samples):
            self.motion_rms_rad_s = self.mean_rate_rad_s = None
            return False
        rates = np.array(self._rates, dtype=float)
        rms_window = rates[-self._rms_samples :]
        # Deviation RMS (spec 44.4): the mean part of the rate is condition (b).
        rms = np.sqrt(np.mean((rms_window - np.mean(rms_window, axis=0)) ** 2, axis=0))
        motion = tuple(noise_corrected_rms(float(value), self.noise_std_rad_s) for value in rms)
        mean = np.mean(rates[-self._mean_samples :], axis=0)
        self.motion_rms_rad_s = (motion[0], motion[1])
        self.mean_rate_rad_s = (float(mean[0]), float(mean[1]))
        settings = self.settings
        is_rms_quiet = max(motion) <= settings.rate_rms_limit_rad_s
        is_mean_quiet = float(np.max(np.abs(mean))) <= settings.mean_rate_limit_rad_s
        return is_rms_quiet and is_mean_quiet

    def state(self) -> StandstillGateState:
        """Values of the last :meth:`update`."""
        zero_command_s = self.zero_command_duration_s
        return StandstillGateState(
            is_open=self.is_open,
            is_phase_allowed=self.is_phase_allowed,
            zero_command_duration_s=None if math.isinf(zero_command_s) else zero_command_s,
            rates_quiet_since_s=self.rates_quiet_since_s,
            motion_rms_rad_s=self.motion_rms_rad_s,
            mean_rate_rad_s=self.mean_rate_rad_s,
        )

    def to_meta(self) -> dict[str, Any]:
        settings = self.settings
        state = asdict(self.state())
        for key in ("motion_rms_rad_s", "mean_rate_rad_s"):
            state[key] = None if state[key] is None else list(state[key])
        return {
            **state,
            "noise_std_rad_s": self.noise_std_rad_s,
            "settings": {
                "rate_rms_limit_rad_s": settings.rate_rms_limit_rad_s,
                "rms_window_s": settings.rms_window_s,
                "mean_rate_limit_rad_s": settings.mean_rate_limit_rad_s,
                "mean_window_s": settings.mean_window_s,
                "hold_s": settings.hold_s,
                "zero_command_s": settings.zero_command_s,
            },
        }
