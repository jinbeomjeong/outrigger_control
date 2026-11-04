"""TOUCH latch phase-scatter candidates as harness wrappers (nothing in 03_src changes).

Each candidate is a subclass of the project ``C2Controller`` (or a config replacement) that the
harness builds through ``c2.C2Controller``, as the study wrappers of spec 344.3 / 427.11 do.
With ``CANDIDATES["OFF"]`` the subclass is installed but every override falls through, so the
command hash must equal the stored harness hash (``run_touch_phase.py`` batch ``hash``).

Candidates (spec: this study, user decision 2026-11-04):
  A1  touch window speed 0.25 v_max, window 40 mm (grid 0.523 mm)
  A2  touch window speed 0.25 v_max, window 20 mm
  B1  per-leg trim at LEVEL entry from the TOUCH-end forces, -(F_i - mean F) / k_nom
  B2  per-leg trim at LEVEL entry from the first-detection forces
  C1  one-shot twist trim at LEVEL entry, Delta = -(D_hat / k_nom) n, running with the heave
  C3  the same trim, extension only, the heave held until it is done (<= 1.5 s)
  D1  no stop cancel: touch_seen after one sample, dips held for the whole 0.5 s window
  F1  pre-probe twist gain at the measured-scale floor (scale 1.0 instead of 1.2)

Trim law (period T = 0.1 s, d = 1, valve lag 0.1 s): deviation of the motor strokes from their
common motion is driven to the target shape by ``u_i += K_TRIM e_i``; commands never reverse a
leg (``max(u, 0)``) so the seal friction state stays the extending one, and the set is rescaled to
v_max. The twist load D_hat = n^T F is friction free in that state (n^T F_s = 0 for the front /
rear F_s pattern). Units: SI inside; RECORD in kN and mm.
"""
from __future__ import annotations

from collections import deque
from dataclasses import replace

import numpy as np

K_TRIM_1_S = 2.5
"""ASSUMPTION: trim P gain; delay d + T/2 + tau_v = 0.25 s gives about 54 deg phase margin."""
TRIM_DONE_M = 0.03e-3
TRIM_TIMEOUT_S = 2.0
HOLD_TIMEOUT_S = 1.5
TAU_HOLD_S = 1.5
"""ASSUMPTION: covers the LEVEL start ramp (about 0.8 s) and the lift-off on the screened rows."""
TRIM_CAP_M = 3.0e-3
"""ASSUMPTION: largest |Delta tau|, about 68 kN of D at k_nom (twice the widest Chrono step set)."""
RAMP_TWIST_TOL_M_S = 0.2e-3
"""ASSUMPTION: G2 threshold on |n^T du| per period: 0.02 mm of twist a period, 0.5 kN of D."""
K2_FAST_DROP_N = 5.0e3
"""ASSUMPTION: K2 lets a re-trigger start on one sample when the estimate fell this much in a period
(50 kN/s; the touchdown-bounce samples of R16 fall 0.5 .. 3.5 kN)."""
D_HAT_DEADBAND_N = 1.0e3
D_HAT_SAMPLES = 3
"""Last TOUCH samples (0.3 s) averaged for D_hat; every leg has been at rest for at least 0.2 s."""

CANDIDATES: dict[str, dict] = {
    "OFF": {},
    "A1": {"r8": {"touch_window_speed_fraction": 0.25}},
    "A2": {"r8": {"touch_window_speed_fraction": 0.25, "touch_window_m": 0.02}},
    "B1": {"trim": "leg_te"},
    "B2": {"trim": "leg_first"},
    "C1": {"trim": "twist"},
    "C3": {"trim": "twist", "hold": True},
    "D1": {"r8": {"touch_seen_samples": 1, "touch_hold_dip_samples": 5}},
    "F1": {"r8": {"pre_probe_stiffness_scale": 1.0}},
    "C1F1": {"trim": "twist", "r8": {"pre_probe_stiffness_scale": 1.0}},
    # Added after the screen found the start-ramp twist (increment limit per leg at LEVEL entry):
    "C4": {"trim": "twist_hold"},
    "G1": {"vector_ramp": True},
    "C4G1": {"trim": "twist_hold", "vector_ramp": True},
    "C5": {"trim": "tau_hold"},
    "C5G1": {"trim": "tau_hold", "vector_ramp": True},
    # Re-approach start rules (2026-11-04, spec of the rule: c2.py _start_reapproaches). All act
    # only on a re-trigger (a start within retrigger_window_s after the previous end); the first
    # start after an event keeps its one sample, so the sink response does not get later.
    "K1": {"reapp": "two_samples"},
    "K7": {"reapp": "two_samples_above_fmin"},
    "K2": {"reapp": "two_samples_unless_fast"},
    "K9": {"reapp": "two_samples_all"},
    "C6": {"trim": "twist_hold", "vector_ramp": True, "no_hold_in_deadband": True, "ramp_twist_only": True},
    "C4G1K1": {"trim": "twist_hold", "vector_ramp": True, "reapp": "two_samples"},
    "C4G1K7": {"trim": "twist_hold", "vector_ramp": True, "reapp": "two_samples_above_fmin"},
    "C4G1K2": {"trim": "twist_hold", "vector_ramp": True, "reapp": "two_samples_unless_fast"},
}
"""C4: tau driven to tau_te - D_hat / k_nom along n for TAU_HOLD_S after the LEVEL entry (projection,
the attitude and heave commands untouched). C5: the same with Delta tau = 0 (no force reading).
G1: while the LEVEL start ramp is limited, the change of all four legs is scaled by one factor, so
the commanded direction (and n^T u) stays that of the unlimited command."""

RECORD: dict = {}
"""Trim of the last controller that left TOUCH in this process (kN, mm, s)."""
LOG_ESTIMATES: list = [False]
"""True: RECORD["estimates"] takes (t, active leg or -1, load estimate per leg kN) every watched period."""


class _TrimState:
    """Per-controller trim bookkeeping (deep-copied with the controller)."""

    def __init__(self) -> None:
        self.twist_history: deque[float] = deque(maxlen=D_HAT_SAMPLES)
        self.force_history: deque[np.ndarray] = deque(maxlen=D_HAT_SAMPLES)
        self.first_force_N: list[float | None] = [None, None, None, None]
        self.shape_m: np.ndarray | None = None
        self.start_stroke_m: np.ndarray | None = None
        self.start_t_s: float | None = None
        self.is_holding = False
        self.tau_target_m: float | None = None


def install_candidate(name: str | None, *, bias_N: float = 0.0, cap_m: float = TRIM_CAP_M) -> None:
    """Replace ``c2.C2Controller`` in this process; ``None`` leaves the project class alone.

    Args:
        name: A key of ``CANDIDATES`` or None.
        bias_N: Added to D_hat (sensor zero error of the twist reading, sensitivity runs).
        cap_m: Largest |Delta tau|.
    """
    if name is None:
        return
    from outrigger_sim.control import c2

    spec = CANDIDATES[name]
    base = c2.C2Controller
    trim_kind = spec.get("trim")
    is_hold = bool(spec.get("hold"))
    is_vector_ramp = bool(spec.get("vector_ramp"))
    reapp_rule = spec.get("reapp")
    r8_keys = spec.get("r8", {})

    class TouchPhaseController(base):
        """Project C2 with one TOUCH phase candidate."""

        @classmethod
        def from_params(cls, params, config=None, *args, **kwargs):
            if r8_keys and config is not None:
                config = replace(config, r8=replace(config.r8, **r8_keys))
            return super().from_params(params, config, *args, **kwargs)

        def _start_reapproaches(self, reading, loads_N, settings):
            if LOG_ESTIMATES[0]:
                active = sorted(self._state.active_reapproaches)
                RECORD.setdefault("estimates", []).append(
                    (round(float(reading.t_s), 2), active[0] if active else -1,
                     [round(float(v) / 1e3, 2) for v in loads_N]))
            super()._start_reapproaches(reading, loads_N, settings)
            if reapp_rule is not None:
                self.__dict__["_previous_loads_N"] = np.array(loads_N, float)

        def _defers_reapproach(self, leg, t_s, strong_count, settings):
            if reapp_rule is not None and self._holds_first_retrigger_sample(leg, t_s, settings):
                RECORD["n_retrigger_held"] = RECORD.get("n_retrigger_held", 0) + 1
                return True
            return super()._defers_reapproach(leg, t_s, strong_count, settings)

        def _holds_first_retrigger_sample(self, leg, t_s, settings) -> bool:
            """A re-trigger whose low count is still 1 waits one period, unless the rule lets the
            sample through (K7: already below F_min; K2: falling faster than K2_FAST_DROP_N)."""
            state = self._state
            is_all_starts = reapp_rule == "two_samples_all"  # K9: the price of a global rule
            if not is_all_starts and not settings.is_retrigger(t_s, state.reapproach_last_end_s):
                return False
            if state.reapproach_low_counts[leg] >= 2:
                return False
            loads = self._load_estimate_N(state.last_reading.cylinder_force_lower_N)
            if reapp_rule == "two_samples_above_fmin":
                return bool(loads[leg] >= self.geometry.F_min_N)
            if reapp_rule == "two_samples_unless_fast":
                previous = self.__dict__.get("_previous_loads_N")
                return previous is None or bool(previous[leg] - loads[leg] < K2_FAST_DROP_N)
            return True

        def _trim_state(self) -> _TrimState:
            return self.__dict__.setdefault("_touch_trim", _TrimState())

        def _touch(self, reading):
            if trim_kind is None:
                return super()._touch(reading)
            trim = self._trim_state()
            twist = self.geometry.twist_vector
            force = np.array(reading.cylinder_force_N, float)
            trim.twist_history.append(float(twist @ force))
            trim.force_history.append(force)
            speeds = super()._touch(reading)
            for leg, since_s in enumerate(self._state.touch_candidate_since_s):
                if trim.first_force_N[leg] is None and since_s is not None:
                    trim.first_force_N[leg] = float(force[leg])
            if self._state.phase is c2.C2Phase.LEVEL:
                self._start_trim(reading, trim)
            return speeds

        def _limited_increment(self, leg_speeds):
            limited = super()._limited_increment(leg_speeds)
            if not is_vector_ramp or self._state.phase is not c2.C2Phase.LEVEL:
                return limited
            if self.__dict__.get("_vector_ramp_done"):
                return limited
            requested = leg_speeds - self._state.previous_output_m_s
            if spec.get("ramp_twist_only"):
                # G2: the per-leg limit stays when its increment makes no twist (a front / rear
                # difference has n^T du = 0), so a symmetric start keeps its bits.
                if abs(float(self.geometry.twist_vector @ limited)) < RAMP_TWIST_TOL_M_S:
                    return limited
            cut = np.abs(requested) > np.abs(limited) + 1e-12
            if not cut.any():
                if np.any(leg_speeds != 0.0):
                    self.__dict__["_vector_ramp_done"] = True
                return limited
            ratio = float(np.min(np.abs(limited[cut]) / np.abs(requested[cut])))
            return requested * ratio

        def _start_trim(self, reading, trim: _TrimState) -> None:
            stiffness = self.geometry.nominal_pad_stiffness_N_m
            twist = self.geometry.twist_vector
            d_hat = float(np.mean(trim.twist_history)) + bias_N
            if trim_kind in ("twist_hold", "tau_hold"):
                delta_tau = float(np.clip(-d_hat / stiffness, -cap_m, cap_m))
                if trim_kind == "tau_hold" or abs(d_hat) < D_HAT_DEADBAND_N:
                    delta_tau = 0.0
                    if spec.get("no_hold_in_deadband"):  # as the implementation, commit 15176d1
                        RECORD.update(t_s=float(reading.t_s), D_hat_kN=d_hat / 1e3, delta_tau_mm=0.0)
                        return
                trim.tau_target_m = delta_tau
                trim.start_stroke_m = np.array(reading.motor_stroke_m, float)
                trim.start_t_s = float(reading.t_s)
                RECORD.update(t_s=float(reading.t_s), D_hat_kN=d_hat / 1e3, delta_tau_mm=delta_tau * 1e3,
                              k_nom_kN_mm=stiffness / 1e6)
                return
            if trim_kind == "twist":
                delta_tau = float(np.clip(-d_hat / stiffness, -cap_m, cap_m))
                shape = delta_tau * twist if abs(d_hat) >= D_HAT_DEADBAND_N else np.zeros(4)
            else:
                if trim_kind == "leg_te":
                    forces = np.mean(trim.force_history, axis=0)
                else:
                    forces = np.array(trim.first_force_N, float)
                shape = np.clip(-(forces - forces.mean()) / stiffness, -cap_m, cap_m)
            RECORD.update(t_s=float(reading.t_s), D_hat_kN=d_hat / 1e3,
                          shape_mm=(shape * 1e3).round(4).tolist(),
                          delta_tau_mm=float(twist @ shape) * 1e3,
                          k_nom_kN_mm=stiffness / 1e6,
                          first_force_kN=[None if f is None else round(f / 1e3, 3)
                                          for f in trim.first_force_N])
            if np.any(shape != 0.0):
                trim.shape_m = shape
                trim.start_stroke_m = np.array(reading.motor_stroke_m, float)
                trim.start_t_s = float(reading.t_s)
                trim.is_holding = is_hold

        def _level(self, reading):
            if trim_kind is None:
                return super()._level(reading)
            trim = self._trim_state()
            if trim.tau_target_m is not None:
                return self._level_tau_hold(reading, trim)
            if trim.shape_m is None:
                return super()._level(reading)
            moved = np.array(reading.motor_stroke_m, float) - trim.start_stroke_m
            error = trim.shape_m - (moved - moved.mean())
            elapsed_s = float(reading.t_s) - trim.start_t_s
            limit_s = HOLD_TIMEOUT_S if trim.is_holding else TRIM_TIMEOUT_S
            if np.max(np.abs(error)) < TRIM_DONE_M or elapsed_s >= limit_s:
                RECORD.update(trim_time_s=elapsed_s, trim_left_mm=float(np.max(np.abs(error))) * 1e3)
                trim.shape_m = None
                trim.is_holding = False
                return super()._level(reading)
            base_speeds = self._zero_speeds() if trim.is_holding else super()._level(reading)
            if self._state.phase is not c2.C2Phase.LEVEL:
                return base_speeds  # the period's level step left LEVEL: no trim on top of it
            speeds = np.maximum(base_speeds + K_TRIM_1_S * error, 0.0)
            largest = float(np.max(speeds))
            v_max = self.geometry.max_speed_m_s
            return speeds * (v_max / largest) if largest > v_max else speeds

        def _level_tau_hold(self, reading, trim: _TrimState):
            """One LEVEL period with n^T(s - s_te) held at the target for TAU_HOLD_S."""
            base_speeds = super()._level(reading)
            twist = self.geometry.twist_vector
            moved = np.array(reading.motor_stroke_m, float) - trim.start_stroke_m
            error = trim.tau_target_m - float(twist @ moved)
            elapsed_s = float(reading.t_s) - trim.start_t_s
            if elapsed_s >= TAU_HOLD_S or self._state.phase is not c2.C2Phase.LEVEL:
                RECORD.update(trim_time_s=elapsed_s, trim_left_mm=abs(error) * 1e3)
                trim.tau_target_m = None
                return base_speeds
            speeds = np.maximum(base_speeds + K_TRIM_1_S * error * twist, 0.0)
            largest = float(np.max(speeds))
            v_max = self.geometry.max_speed_m_s
            return speeds * (v_max / largest) if largest > v_max else speeds

    c2.C2Controller = TouchPhaseController


def install_gap_plant(verdict_runs, gaps_m) -> None:
    """Floor gaps per leg (+ = floor lower at that pad, rigid floor only) from ``plant.arm``.

    ``verdict_runs.make_flow_plant_class`` is wrapped so the plant also reports itself, whether a
    gap is given or not: ``LAST_PLANT[0]`` is the plant armed last in this process (the event path
    runs deep copies for its timeline, the armed original stays the one that is judged).
    """
    original = verdict_runs.make_flow_plant_class
    gaps = None if gaps_m is None else np.asarray(gaps_m, float)

    def make_class(base, setting):
        flow_class = original(base, setting)

        class GapPlant(flow_class):
            def arm(self):
                if gaps is not None:
                    self.goff[:] = np.asarray(self.goff) + gaps
                LAST_PLANT[0] = self
                return super().arm()

        return GapPlant

    verdict_runs.make_flow_plant_class = make_class


LAST_PLANT: list = [None]
