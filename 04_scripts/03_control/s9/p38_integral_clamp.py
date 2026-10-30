"""P-S8-38 ZIC candidate (control spec 429.3 / 429.5): attitude integral zero-crossing cap.

Harness-only subclass factory on any C2 class (03_src unchanged until adoption), used by the
wrapper ``s9_slope_fix_candidates.py`` (tokens ``P38z`` c 0.5, ``P38z25`` c 0.25, ``P38z1``
c 0.5 with the first-DONE window; parameters ``p38_cap_fraction``, ``p38_window``) and, through
its ``_install_candidate``, by the study A screen (``R426A_CANDIDATE``) and the r67 screen
(``R67_CANDIDATE``).

Window: LEVEL periods from the first ``crawler_liftoff_confirmed`` of the run (latched; a LOC
revocation keeps the window) until the end chosen by ``window`` (wrapper ``p38_window``):
  - ``"first_ready"`` (P38z, P38z25; default): until the first READY entry (the re-level after a
    probe included; never after the first READY).
  - ``"first_done"`` (P38z1, spec 429.7 redesign): until the first DONE after the first LOC
    (the re-level after a probe excluded). DONE is latched from the phase at the end of an
    update, as the wrapper's DS watch and ``t_first_done_s`` read it.
Never before the first LOC.
Rule: after the c2 integral update of ``_attitude_pi`` and before its output, per axis, with
``e != 0``, ``sign(I) != sign(e)`` and ``|I| > I_cap``: ``I <- sign(I) I_cap``, where
``I_cap = c theta_done K_p / K_i`` (c = ``cap_fraction``, theta_done = ``done_attitude_rad``).
The output is computed from the cut integral with the c2 formula ``K_p e + K_i I``.
Record: ``INFO_ATT_INT_CLAMP:<roll|pitch>:<I before>`` (events are not in the command hash) and
``clamps`` rows (time, axis, integral before / after).
The stroke-guard HOLD_ALL restore of c2 ``_level`` (369.2) runs after the LEVEL step, so it
still puts back the period-start integrals over a cut one.
With ``enable`` False the factory returns ``base_class`` itself. Units SI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

CLAMP_EVENT = "INFO_ATT_INT_CLAMP"
AXES = ("roll", "pitch")
RECORD_ROWS_MAX = 50
WINDOW_FIRST_READY = "first_ready"
WINDOW_FIRST_DONE = "first_done"
WINDOWS = (WINDOW_FIRST_READY, WINDOW_FIRST_DONE)


@dataclass(frozen=True)
class IntegralClampSettings:
    """ZIC settings (spec 429.3 ``AttitudeIntegralClampSettings``)."""

    enable: bool = False
    cap_fraction: float = 0.5
    """c of ``I_cap = c theta_done K_p / K_i`` (0.5: equilibrium deviation 0.015 deg)."""
    window: str = WINDOW_FIRST_READY
    """Window end: ``"first_ready"`` (P38z) or ``"first_done"`` (P38z1, spec 429.7)."""

    def __post_init__(self) -> None:
        if not self.cap_fraction > 0.0:
            raise ValueError(f"cap_fraction must be > 0, got {self.cap_fraction}")
        if self.window not in WINDOWS:
            raise ValueError(f"window must be one of {WINDOWS}, got {self.window!r}")


@dataclass
class IntegralClampState:
    """Per-run window latches and the clamp record."""

    first_loc_s: float | None = None
    has_entered_ready: bool = False
    first_done_s: float | None = None
    """First DONE at or after the first LOC (latched for every window; it ends only
    ``"first_done"``)."""
    clamps: list = field(default_factory=list)
    clamp_count: int = 0

    def has_window_ended(self, window: str) -> bool:
        """The window end of ``window`` has been passed."""
        if self.has_entered_ready:
            return True
        return window == WINDOW_FIRST_DONE and self.first_done_s is not None


def integral_cap(cap_fraction: float, done_attitude_rad: float, kp_1_s: float,
                 ki_1_s2: float) -> float:
    """``I_cap = c theta_done K_p / K_i`` [rad s]."""
    return cap_fraction * done_attitude_rad * kp_1_s / ki_1_s2


def clamped_integral(error_rad: float, integral: float, cap: float) -> float:
    """The ZIC rule on one axis: the integral pushing past the target, above ``cap``, is cut to
    ``sign(I) cap``; otherwise unchanged (the same float object value)."""
    if error_rad == 0.0 or integral == 0.0:
        return integral
    if math.copysign(1.0, integral) == math.copysign(1.0, error_rad):
        return integral
    if abs(integral) <= cap:
        return integral
    return math.copysign(cap, integral)


def integral_clamp_record(controller) -> dict | None:
    """Run record of the ZIC layer (None on a controller without it)."""
    state = getattr(controller, "p38_state", None)
    if state is None:
        return None
    settings = getattr(controller, "integral_clamp", None)
    window = settings.window if settings is not None else WINDOW_FIRST_READY
    return {"window": window, "first_loc_s": state.first_loc_s,
            "has_entered_ready": state.has_entered_ready, "first_done_s": state.first_done_s,
            "clamp_count": state.clamp_count, "clamps": list(state.clamps)}


def has_integral_clamp_acted(record: dict | None) -> bool:
    return bool(record and record.get("clamp_count"))


def make_integral_clamp_class(c2, base_class, settings: IntegralClampSettings):
    """Subclass of ``base_class`` with the ZIC of ``settings``; ``base_class`` when off."""
    if not settings.enable:
        return base_class

    class IntegralClampC2(base_class):
        integral_clamp = settings

        def reset(self) -> None:
            super().reset()
            self.p38_state = IntegralClampState()
            self._p38_axis = None

        def _p38(self) -> IntegralClampState:
            state = getattr(self, "p38_state", None)
            if state is None:
                state = self.p38_state = IntegralClampState()
            return state

        def update(self, measurements):
            command = super().update(measurements)
            window = self._p38()
            if window.first_loc_s is None and self._is_liftoff_confirmed():
                window.first_loc_s = float(measurements.t_s)  # a LOC outside a PI call
            phase = self._state.phase
            if phase is c2.C2Phase.READY:
                window.has_entered_ready = True
            is_first_done = (phase is c2.C2Phase.DONE and window.first_loc_s is not None
                             and window.first_done_s is None)
            if is_first_done:
                window.first_done_s = float(measurements.t_s)
            return command

        def _p38_in_window(self) -> bool:
            window = self._p38()
            if window.has_window_ended(settings.window):
                return False
            if self._state.phase is not c2.C2Phase.LEVEL:
                return False
            if window.first_loc_s is None and self._is_liftoff_confirmed():
                window.first_loc_s = float(self._state.last_reading.t_s)
            return window.first_loc_s is not None

        def _attitude_rates(self):
            self._p38_axis = 0
            try:
                return super()._attitude_rates()
            finally:
                self._p38_axis = None

        def _attitude_pi(self, error_rad, integral, joint_error_rad=None):
            rate, new_integral = super()._attitude_pi(error_rad, integral, joint_error_rad)
            axis = getattr(self, "_p38_axis", None)
            if axis is not None:
                self._p38_axis = axis + 1
            if axis is None or axis >= len(AXES) or not self._p38_in_window():
                return rate, new_integral
            gains = self.config.gains
            cap = integral_cap(settings.cap_fraction, self.config.thresholds.done_attitude_rad,
                               gains.attitude_kp_1_s, gains.attitude_ki_1_s2)
            cut = clamped_integral(error_rad, new_integral, cap)
            if cut == new_integral:
                return rate, new_integral
            self._p38_note(AXES[axis], new_integral, cut)
            return gains.attitude_kp_1_s * error_rad + gains.attitude_ki_1_s2 * cut, cut

        def _p38_note(self, axis: str, before: float, after: float) -> None:
            window = self._p38()
            t_s = float(self._state.last_reading.t_s)
            window.clamp_count += 1
            if len(window.clamps) < RECORD_ROWS_MAX:
                window.clamps.append({"t_s": round(t_s, 2), "axis": axis,
                                      "before": before, "after": after})
            self._add_event(t_s, f"{CLAMP_EVENT}:{axis}:{before:.5f}")

    IntegralClampC2.__name__ = IntegralClampC2.__qualname__ = (
        f"IntegralClamp{base_class.__name__}")
    return IntegralClampC2
