"""Record-only shadow of the LOC anchor attitude (plan A of ``loc_anchor_review.md`` 5.1).

The controller's S-3 bias (path 1) and LOC anchor (path 2) read the raw tilt of one period, the
first sample ``t_P`` of the confirming S-1 tail. Plan A replaces it by the mean raw tilt over
``[t_P - w, t_P + w]`` with ``w = min(0.5 s, t_L - t_P)``. This module computes that estimate
next to the controller's own and records both; the controller's commands never see it.

What is recorded per controller (``record_of``), per confirmed LOC (a LOC revoked by L1gs and
confirmed again gets a second entry):

* ``t_P_s``, ``t_L_s``, the path (``"1"`` S-3 bias, ``"2"`` LOC anchor, ``"3"`` none) and
  ``c_min(t_P)``;
* the raw tilt ring buffer: every period-mean raw tilt the S-1 window update saw in
  ``[t_P - 1 s, t_L]`` (deg);
* the single-period tilt the controller used, the centred mean (plan A), its window, sample
  count and standard deviation, and the ``rho_rel`` uncertainty
  ``(y_max - y_min) sigma_phi + (x_max - x_min) sigma_theta`` (A+, record only);
* the biases ``b_k`` (current and shadow) and the clearance estimate ``c_hat`` at ``t_L``;
* over every update while this LOC holds: ``d = c_hat(current) - c_hat(shadow)`` minimum,
  maximum and the value at ``t_L`` (mm; ``d > 0`` = the current estimate is the more
  optimistic one).

How it stays out of the commands: the three wrappers call the original method unchanged and
only read controller state through pure methods (``_period_raw_attitude_rad``,
``_settle_attitude_rad``, ``_corner_bias_m``, ``_loc_anchor_bias_m``,
``_clearance_estimate_m``, ``geometry.clearance_corners_m``). The window wrapper reads
``self._state.soil`` directly (``_soil_state()`` would create it). The record lives in the
instance attribute :data:`STATE_ATTRIBUTE`, which no controller method reads. The run
drivers check this by the command hash against the stored lines.

Off by default: :func:`install` refuses unless the environment has
``OUTRIGGER_LOC_SHADOW=1``.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

ENV_SWITCH = "OUTRIGGER_LOC_SHADOW"
ENV_ON = "1"
MAX_HALF_WINDOW_S = 0.5
"""Plan A half window: ``w = min(0.5 s, t_L - t_P)``."""
SHORT_WINDOW_S = 0.3
"""Below this ``w`` the record carries ``short_window`` (plan A's
``INFO_LOC_ANCHOR_SHORT_WINDOW``)."""
TIME_TOLERANCE_S = 1e-6
"""Inclusive window ends (the control times are sums of 0.1 s steps)."""
BUFFER_BEFORE_T_P_S = 1.0
"""The exported ring buffer starts this long before ``t_P``."""
STATE_ATTRIBUTE = "_loc_shadow"
PATH_BIAS, PATH_ANCHOR, PATH_NONE = "1", "2", "3"
M_TO_MM = 1e3
INSTALLED_MARK = "_loc_shadow_installed"

_REGISTRY: list[Any] = []
"""Controllers that ran at least one update since :func:`clear_registry` (worker only)."""


@dataclass
class _LocEntry:
    """One confirmed LOC and the running comparison of both estimates after it."""

    t_P_s: float
    t_L_s: float
    path: str
    bias_shadow_m: np.ndarray
    summary: dict[str, Any]
    differences_mm: list[float] = field(default_factory=list)
    current_min_mm: float = math.inf
    shadow_min_mm: float = math.inf
    is_closed: bool = False


@dataclass
class _ShadowState:
    """Per-controller record: raw tilt samples before the LOC and the LOC entries."""

    tilt_samples: list[tuple[float, float, float]] = field(default_factory=list)
    """(t_s, roll_rad, pitch_rad) of every S-1 window update before a LOC."""
    entries: list[_LocEntry] = field(default_factory=list)


# ----------------------------------------------------------------------------- helpers
def _shadow_state(controller) -> _ShadowState:
    state = controller.__dict__.get(STATE_ATTRIBUTE)
    if state is None:
        state = _ShadowState()
        controller.__dict__[STATE_ATTRIBUTE] = state
        _REGISTRY.append(controller)
    return state


def _mm_list(values_m) -> list[float]:
    return [float(value) * M_TO_MM for value in np.asarray(values_m, dtype=float)]


def _deg_pair(attitude_rad) -> list[float]:
    return [math.degrees(float(attitude_rad[0])), math.degrees(float(attitude_rad[1]))]


def _window_samples(samples, t_P_s: float, half_s: float) -> list[tuple[float, float, float]]:
    low_s, high_s = t_P_s - half_s - TIME_TOLERANCE_S, t_P_s + half_s + TIME_TOLERANCE_S
    return [sample for sample in samples if low_s <= sample[0] <= high_s]


def _rho_uncertainty_mm(controller, std_rad: np.ndarray) -> float:
    corners_xy = np.asarray(controller.geometry.crawler_corners_xy_m, dtype=float)
    x_span_m = float(np.ptp(corners_xy[:, 0]))
    y_span_m = float(np.ptp(corners_xy[:, 1]))
    return (y_span_m * float(std_rad[0]) + x_span_m * float(std_rad[1])) * M_TO_MM


def _path_of(controller, soil) -> str:
    if soil.is_loc_anchor_applied:
        return PATH_ANCHOR
    if soil.clearance_at_plateau_start_m > controller.config.soil.corner_bias_deadzone_m:
        return PATH_BIAS
    return PATH_NONE


def _shadow_bias_m(controller, path: str, raw_shadow_m: np.ndarray, c_min_m: float) -> np.ndarray:
    """The controller's bias rule (``_confirm_liftoff``) applied to the shadow raw bias."""
    if path == PATH_ANCHOR:
        return np.asarray(controller._loc_anchor_bias_m(raw_shadow_m, c_min_m), dtype=float)
    if path == PATH_BIAS:
        return np.maximum(raw_shadow_m, 0.0)
    return np.zeros_like(raw_shadow_m)


def _tail_mismatch_deg(samples, tail) -> float | None:
    """Largest |buffer tilt - tail tilt| at the tail times (both are the period means)."""
    by_time = {round(sample[0], 6): sample for sample in samples}
    worst = None
    for point in tail:
        sample = by_time.get(round(float(point.t_s), 6))
        if sample is None:
            continue
        gap = max(abs(sample[1] - point.raw_attitude_rad[0]),
                  abs(sample[2] - point.raw_attitude_rad[1]))
        worst = gap if worst is None else max(worst, gap)
    return None if worst is None else math.degrees(worst)


def _new_entry(controller, t_L_s: float, tail) -> _LocEntry:
    """Plan A at a LOC the controller has just confirmed (its soil state is final here)."""
    soil = controller._state.soil
    shadow = _shadow_state(controller)
    first = tail[0]
    t_P_s = float(first.t_s)
    half_s = min(MAX_HALF_WINDOW_S, t_L_s - t_P_s)
    window = _window_samples(shadow.tilt_samples, t_P_s, half_s)
    tilts_rad = np.array([[sample[1], sample[2]] for sample in window], dtype=float)
    centred_rad = tilts_rad.mean(axis=0) if len(window) else np.asarray(first.raw_attitude_rad)
    std_rad = tilts_rad.std(axis=0) if len(window) else np.zeros(2)
    centred_sample = replace(first, raw_attitude_rad=(float(centred_rad[0]), float(centred_rad[1])))
    raw_shadow_m = np.asarray(controller._corner_bias_m(centred_sample), dtype=float)
    c_min_m = float(soil.clearance_at_plateau_start_m)
    path = _path_of(controller, soil)
    bias_shadow_m = _shadow_bias_m(controller, path, raw_shadow_m, c_min_m)
    corners_tL_m = np.asarray(tail[-1].corner_clearance_m, dtype=float)
    settle = controller._settle_attitude_rad()
    buffer_low_s = t_P_s - BUFFER_BEFORE_T_P_S - TIME_TOLERANCE_S
    summary = {
        "t_P_s": t_P_s, "t_L_s": float(t_L_s), "path": path, "c_min_tP_mm": c_min_m * M_TO_MM,
        "window_half_s": half_s, "window_n": len(window), "short_window": half_s < SHORT_WINDOW_S,
        "window_t_s": [window[0][0], window[-1][0]] if window else None,
        "att_single_deg": _deg_pair(first.raw_attitude_rad),
        "att_centred_deg": _deg_pair(centred_rad),
        "att_window_std_deg": _deg_pair(std_rad),
        "settle_deg": None if settle is None else _deg_pair(settle),
        "rho_uncertainty_mm": _rho_uncertainty_mm(controller, std_rad),
        "bias_raw_current_mm": _mm_list(soil.corner_bias_raw_m),
        "bias_current_mm": _mm_list(soil.corner_bias_m),
        "bias_raw_shadow_mm": _mm_list(raw_shadow_m),
        "bias_shadow_mm": _mm_list(bias_shadow_m),
        "c_hat_tL_current_mm": float(np.min(corners_tL_m - soil.corner_bias_m)) * M_TO_MM,
        "c_hat_tL_shadow_mm": float(np.min(corners_tL_m - bias_shadow_m)) * M_TO_MM,
        "tail_mismatch_deg": _tail_mismatch_deg(shadow.tilt_samples, tail),
        "raw_tilt_buffer": [[sample[0], math.degrees(sample[1]), math.degrees(sample[2])]
                            for sample in shadow.tilt_samples
                            if buffer_low_s <= sample[0] <= t_L_s + TIME_TOLERANCE_S],
    }
    summary["diff_tL_mm"] = summary["c_hat_tL_current_mm"] - summary["c_hat_tL_shadow_mm"]
    return _LocEntry(t_P_s=t_P_s, t_L_s=float(t_L_s), path=path, bias_shadow_m=bias_shadow_m,
                     summary=summary)


def _open_entry(controller) -> _LocEntry | None:
    """The entry of the LOC in force now, closing entries whose LOC was revoked."""
    soil = controller._state.soil
    entries = _shadow_state(controller).entries
    if not entries:
        return None
    last = entries[-1]
    is_same_loc = (soil is not None and soil.is_liftoff_confirmed and soil.liftoff_s is not None
                   and abs(soil.liftoff_s - last.t_L_s) < TIME_TOLERANCE_S)
    if not is_same_loc:
        last.is_closed = True
        return None
    return None if last.is_closed else last


def _compare_this_period(controller) -> None:
    entry = _open_entry(controller)
    reading = controller._state.last_reading
    if entry is None or reading is None:
        return
    rod_stroke_m = reading.rod_stroke_m
    current_m = float(controller._clearance_estimate_m(rod_stroke_m))
    corners_m = np.asarray(controller.geometry.clearance_corners_m(rod_stroke_m), dtype=float)
    shadow_m = float(np.min(corners_m - entry.bias_shadow_m))
    entry.differences_mm.append((current_m - shadow_m) * M_TO_MM)
    entry.current_min_mm = min(entry.current_min_mm, current_m * M_TO_MM)
    entry.shadow_min_mm = min(entry.shadow_min_mm, shadow_m * M_TO_MM)


# ----------------------------------------------------------------------------- wrappers
def _wrap_window(original):
    def _update_liftoff_window(self, reading):
        soil = self._state.soil
        if self.config.soil.enable and (soil is None or not soil.is_liftoff_confirmed):
            roll_rad, pitch_rad = self._period_raw_attitude_rad()
            sample = (float(reading.t_s), float(roll_rad), float(pitch_rad))
            _shadow_state(self).tilt_samples.append(sample)
        return original(self, reading)

    return _update_liftoff_window


def _wrap_confirm(original):
    def _confirm_liftoff(self, t_s, tail, mean_load_N):
        result = original(self, t_s, tail, mean_load_N)
        _shadow_state(self).entries.append(_new_entry(self, float(t_s), tail))
        return result

    return _confirm_liftoff


def _wrap_update(original):
    def update(self, measurements):
        command = original(self, measurements)
        _shadow_state(self)
        _compare_this_period(self)
        return command

    return update


# ----------------------------------------------------------------------------- public API
def is_enabled(environ: dict[str, str] | None = None) -> bool:
    """Whether the environment switches the shadow on (``OUTRIGGER_LOC_SHADOW=1``)."""
    environ = os.environ if environ is None else environ
    return environ.get(ENV_SWITCH) == ENV_ON


def install(controller_class=None) -> bool:
    """Wrap ``C2Controller`` once in this process (a second call does nothing).

    Returns:
        True when this call installed the wrappers, False when they were already in place.

    Raises:
        RuntimeError: The environment does not switch the shadow on.
    """
    if not is_enabled():
        raise RuntimeError(f"loc_anchor_shadow: set {ENV_SWITCH}={ENV_ON} to install the shadow")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    if getattr(controller_class, INSTALLED_MARK, False):
        return False
    controller_class._update_liftoff_window = _wrap_window(controller_class._update_liftoff_window)
    controller_class._confirm_liftoff = _wrap_confirm(controller_class._confirm_liftoff)
    controller_class.update = _wrap_update(controller_class.update)
    setattr(controller_class, INSTALLED_MARK, True)
    return True


def clear_registry() -> None:
    """Forget the controllers seen so far (call at the start of each job in a reused worker)."""
    _REGISTRY.clear()


def registered_controllers() -> list[Any]:
    """Controllers that ran an update since :func:`clear_registry`, in order of first update."""
    return list(_REGISTRY)


def _entry_record(entry: _LocEntry) -> dict[str, Any]:
    differences = entry.differences_mm
    return {
        **entry.summary,
        "periods_compared": len(differences),
        "diff_min_mm": min(differences) if differences else None,
        "diff_max_mm": max(differences) if differences else None,
        "c_hat_min_current_mm": None if not differences else entry.current_min_mm,
        "c_hat_min_shadow_mm": None if not differences else entry.shadow_min_mm,
    }


def record_of(controller) -> dict[str, Any] | None:
    """The shadow record of one controller (JSON-serialisable), None without the shadow."""
    state = controller.__dict__.get(STATE_ATTRIBUTE)
    if state is None:
        return None
    soil = controller._state.soil
    locs = [_entry_record(entry) for entry in state.entries]
    differences = [value for entry in state.entries for value in entry.differences_mm]
    return {
        "plan": "A centred mean, w = min(0.5 s, t_L - t_P), period-mean raw tilt",
        "soil_t_P_s": None if soil is None else soil.plateau_start_s,
        "n_loc": len(locs),
        "paths": [loc["path"] for loc in locs],
        "diff_min_mm": min(differences) if differences else None,
        "diff_max_mm": max(differences) if differences else None,
        "locs": locs,
    }
