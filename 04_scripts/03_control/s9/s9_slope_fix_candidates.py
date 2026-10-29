"""Fix candidates for the soft soil x slope defects of study 1 (control-expert 2026-10-28), compared
on the reduced harnesses before one is adopted (user decision: 03_src stays unchanged until then).

Defects (``06_analysis/02_control/s9/rev78/s9_soil_slope.json``):
  E   false LOC: the downhill pads punch into J1 / J2 (Bekker n << 1, dF/dz = nF/z: a 10 mm window
      rises about 1.0 / 1.7 kN, under the 2 kN S-1 threshold) while the downhill crawler still
      carries load; the LOC bias then reads 50 mm with 1.5 .. 2.2 mm true clearance at READY.
  RA  REANCHOR on soft soil aborts (attitude, band) and adds virgin front sink -> FAULT.
  S4  S-4 (150 mm of soil-mode push) is longer than the stroke left on a slope -> FAULT_STROKE_END.

Candidates (tokens, combined with "+", e.g. "E1+E2"; "current" = the project controller):
  E1  S-1 window veto: over the confirming tail, the raw-tilt corner rise
      rho_k = y_k dphi - x_k dtheta must follow the stroke-plane corner clearance change dc_k
      up to a common heave; a spread ptp(dc_k - rho_k) above ``e1_max_mismatch_m`` (the body
      pivots on a loaded crawler edge) clears the window instead of confirming.
  E2  re-contact in DONE / PROBE / READY: sum F / W_hat (LOC value) below 1 - ``e2_drop_fraction``
      for ``e2_confirm_samples`` periods undoes the LOC (soil mode again, a new S-1 window and
      bias) and re-levels; at most ``e2_max_relifts`` times.
  E3  at the LOC, a run that used soil mode or got a corner bias, on a crawler settle tilt above
      ``e3_tilt_min_rad``,
      raises the clearance target by ``e3_margin_m`` (penetration margin).
  E3w / E3c7 / E3c10  composite E3 tokens (spec 417, 2026-10-29): E3w = E3 with
      ``e3_require_soil_use`` False (E3wide); E3c7 / E3c10 = E3w only when the soil sign
      c_min(t_P) (``soil.clearance_at_plateau_start_m``) is above 7 / 10 mm
      (``e3_min_clearance_at_P_m``).
  E4  S-1 window veto from the IMU (dynamics-expert proposal, 2026-10-28): the body rise over the
      tail, double-integrated from |f| - g_ref (g_ref: mean |f| over the last TOUCH samples,
      integration from the LEVEL start where the body rests on the crawler), must reach
      ``e4_min_rise_ratio`` of the mean motor-stroke advance; less clears the window. Sensor
      signals only (the true pad sink is used for judgement, never as an input).
  RA  ``_reanchor_skip_reason`` returns "soil" when the run used soil mode or the LOC bias is
      non-zero (only where REANCHOR would otherwise start).
  LWa / LWb  418 (spec 419, 2026-10-29), the S-1 window against a lifted re-approach: LWa clears
      the window and adds no sample while any re-approach is active (``FIX_LW_RESTART``); LWb
      builds the window on the legs without an active re-approach (mean motor stroke and the
      plateau-period speed condition over them, load sum of all four legs) and clears it when
      the re-approach set changes (``FIX_LW_SET``). Alternatives, not combinable.
  S4  S-4 also fires when the stroke reaches the lift guard stroke s_g before the LOC
      (``s4_stroke_basis`` "max": longest leg, "mean": mean motor stroke) ->
      ``WARN_CRAWLER_LIFTOFF_UNCONFIRMED:stroke`` and FAULT.

Every controller of a run (baseline included) records passively, without changing a command:
the true crawler force per control period (max over the 1 ms chunks, wrapped ``cl._lagged_step``),
the controller load sum, the E1 spread and the E4 rise ratio at every confirming tail, and
(metrics ``crawler_recontact``, 2026-10-29) the U-S9-G6d recontact intervals after the crawler
departure from the 1 ms crawler force (``run_S9.py`` rules).

Suites (each harness path imported, not copied; the settle hook "harness" is the default):
  slope  study 1, 177 cases (``s9_soil_slope.py``, settle table ``hook_harness`` attached)
  g6     G6 weak pad, 116 cases (``s8/r72_g6_screen.py`` sets all + rigid_all)
  g8     G8 non-planar start, 516 cases (``s8/r70_p28_screen.py`` set all, variant proj)
  p3b    uniform soil 72 (283.2 grid, 3 levels x F_s 0/4/8) + rigid 135 (281 regression) with the
         project preset on ``s9_soil_closed_loop.py``
Compared per case against "current": verdict, command SHA-256, dREADY, d min true F_cyl, d end
attitude, false LOCs (crawler force >= 0.01 W in the LOC period), crawler re-contacts in READY.

Usage (project root; dynamics-dev with numba; MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I s9_slope_fix_candidates.py run --suite slope --candidates current,E1,E2 \
      [--filter SUBSTR,...] [--workers N] [--affinity 0xMASK] [--param name=value ...] \
      [--settle-hook harness|p0] [--out JSON]
  python -I s9_slope_fix_candidates.py list --suite g8 [--filter ...]
  python -I s9_slope_fix_candidates.py compare --out JSON RUN_JSON [RUN_JSON ...]
Units SI unless the key says otherwise (mm, kN, deg, s).
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import math
import os
import sys
import time
import traceback
from collections import deque
from dataclasses import asdict, dataclass, field, fields, replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (ROOT / "03_src", HERE, S8_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from late_loc_rule import crawler_recontact_record  # noqa: E402  (shared harness judge rules)

DEFAULT_OUT_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev80"
SETTLE_TABLE_PATH = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
SETTLE_TABLE_KEY = "hook_harness"
SETTLE_HOOK_ENV = "S9_SETTLE_HOOK"

BASELINE = "current"
CANDIDATE_TOKENS = ("E1", "E2", "E3", "E4", "RA", "S4", "E3w", "E3c7", "E3c10", "LWa", "LWb")
LW_RESTART_EVENT = "FIX_LW_RESTART"
LW_SET_EVENT = "FIX_LW_SET"
SUITES = ("slope", "g6", "g8", "p3b")

LOC_EVENT = "crawler_liftoff_confirmed"
FALSE_LOC_WEIGHT_FRACTION = 0.01
"""P3-2: no LOC while the crawler carries more than 0.01 W."""
TIME_MATCH_S = 1e-6
FIX_EVENT_PREFIX = "FIX_"
WINDOW_VETO_EVENT = "FIX_WINDOW_VETO"
E2_EVENT = "FIX_E2_RECONTACT"
E3_EVENT = "FIX_E3_TARGET"
S4_STROKE_EVENT = "WARN_CRAWLER_LIFTOFF_UNCONFIRMED:stroke"
REANCHOR_SOIL_REASON = "soil"
FAULT_PHASES = ("fault", "fault_reground")
ATTITUDE_TOL_DEG = 0.2
RUT_MIN_MM = 25.0
LOC_DELAY_MAX_S = 2.9

_TRUTH: dict = {"crawler_max_N": 0.0, "weight_N": None, "crawler_series": []}
"""Per-worker truth of the running case, filled by the wrapped ``cl._lagged_step``;
``crawler_series`` = (plant t s, crawler force N) of every 1 ms chunk (record only)."""
_RUNNING: dict = {}
"""Per-worker: the last controller built (the harnesses build one per run)."""


# ------------------------------------------------------------------------------- settings
@dataclass(frozen=True)
class CandidateSettings:
    """Which fixes are on and their constants (defaults: control-expert proposal values)."""

    e1: bool = False
    e1_max_mismatch_m: float = 0.004
    e2: bool = False
    e2_drop_fraction: float = 0.08
    """sum F below (1 - this) W_hat. W_hat carries the seal friction of the lifting window: a
    clean READY reads 0.946 (G1 flat), the E cases 0.88 .. 0.89 (smoke 2026-10-28)."""
    e2_confirm_samples: int = 2
    e2_max_relifts: int = 2
    e3: bool = False
    e3_tilt_min_rad: float = math.radians(1.0)
    e3_margin_m: float = 0.030
    """Clearance target 50 + 30 = 80 mm, below the Z1 limit 92.4 mm."""
    e3_require_soil_use: bool = True
    """False: every LOC on a settle tilt above the limit (the settle-table E cases confirm with
    neither soil mode nor a bias, smoke 2026-10-28)."""
    e3_min_clearance_at_P_m: float = -1.0
    """Soil sign of the E3 variants E3c7 / E3c10 (spec 417, 2026-10-29): the margin is added only
    when the controller's crawler clearance estimate at the plateau start, ``c_min(t_P)`` =
    ``soil.clearance_at_plateau_start_m``, is above this [m]. On rigid / G1 slopes the stored
    study-1 values are -4.0 .. 6.5 mm, on the soft-soil cases E3wide improved 7.7 .. 63 mm.
    Negative = no condition (E3 / E3wide as run before)."""
    e4: bool = False
    e4_min_rise_ratio: float = 0.5
    e4_gravity_samples: int = 100
    """IMU samples (10 ms) of the TOUCH end that give g_ref."""
    reanchor_soil_skip: bool = False
    s4_stroke_limit: bool = False
    s4_stroke_basis: str = "max"
    lw_restart: bool = False
    """418 LW-a: no S-1 window sample while a lifted re-approach is active (window cleared)."""
    lw_exclude: bool = False
    """418 LW-b: the S-1 window runs on the legs without an active re-approach (mean stroke and
    the plateau-period speed condition over those legs; load sum of all four legs); a change of
    the re-approach set clears the window."""

    def __post_init__(self) -> None:
        if self.s4_stroke_basis not in ("max", "mean"):
            raise ValueError(f"s4_stroke_basis must be max or mean, got {self.s4_stroke_basis!r}")
        if not 0.0 < self.e2_drop_fraction < 1.0:
            raise ValueError(f"e2_drop_fraction must be in (0, 1), got {self.e2_drop_fraction}")
        if self.e3_margin_m < 0.0 or self.e1_max_mismatch_m <= 0.0:
            raise ValueError("e3_margin_m must be >= 0 and e1_max_mismatch_m > 0")
        if self.lw_restart and self.lw_exclude:
            raise ValueError("LWa and LWb are alternatives (418), not a combination")


TOKEN_FLAGS = {"E1": "e1", "E2": "e2", "E3": "e3", "E4": "e4", "RA": "reanchor_soil_skip",
               "S4": "s4_stroke_limit", "LWa": "lw_restart", "LWb": "lw_exclude"}
TOKEN_PRESETS = {
    "E3w": {"e3": True, "e3_require_soil_use": False},
    "E3c7": {"e3": True, "e3_require_soil_use": False, "e3_min_clearance_at_P_m": 0.007},
    "E3c10": {"e3": True, "e3_require_soil_use": False, "e3_min_clearance_at_P_m": 0.010},
}
"""Composite E3 variants (spec 417, 2026-10-29): E3w = E3wide (the adopted candidate of 404.1),
E3c7 / E3c10 = E3wide only with the soil sign c_min(t_P) above 7 / 10 mm. The preset values win
over ``--param`` overrides of the same field."""


def parse_candidate(name: str, overrides: dict | None = None) -> CandidateSettings:
    """Settings of a candidate name ("current" or tokens joined by "+") with parameter overrides.

    Raises:
        ValueError: unknown token or override name.
    """
    flags: dict = {}
    if name != BASELINE:
        for token in name.split("+"):
            if token in TOKEN_PRESETS:
                flags.update(TOKEN_PRESETS[token])
                continue
            if token not in TOKEN_FLAGS:
                raise ValueError(f"unknown candidate token {token!r}, expected {CANDIDATE_TOKENS}")
            flags[TOKEN_FLAGS[token]] = True
    known = {f.name for f in fields(CandidateSettings)}
    unknown = sorted(set(overrides or {}) - known)
    if unknown:
        raise ValueError(f"unknown parameters {unknown}")
    return CandidateSettings(**{**(overrides or {}), **flags})


def parse_param_overrides(items: list[str]) -> dict:
    """``name=value`` strings -> typed values (the field default's type)."""
    types = {f.name: type(f.default) for f in fields(CandidateSettings)}
    out = {}
    for item in items:
        name, _, text = item.partition("=")
        if name not in types:
            raise ValueError(f"unknown parameter {name!r}")
        if types[name] is str:
            out[name] = text
        elif types[name] is bool:
            out[name] = text.strip().lower() in ("1", "true", "yes")
        else:
            out[name] = types[name](float(text))
    return out


# ------------------------------------------------------------------------ pure signal maths
def corner_rise_m(corners_xy_m: np.ndarray, roll_change_rad: float,
                  pitch_change_rad: float) -> np.ndarray:
    """Corner rise of an attitude change, ``y_k dphi - x_k dtheta`` (c2 S-3 convention)."""
    xy = np.asarray(corners_xy_m, float)
    return xy[:, 1] * roll_change_rad - xy[:, 0] * pitch_change_rad


def kinematic_mismatch_m(corners_xy_m, clearance_start_m, clearance_end_m, attitude_start_rad,
                         attitude_end_rad) -> float:
    """E1 spread ``ptp(dc_k - rho_k)``: the stroke-plane corner clearance change against the corner
    rise of the measured tilt change; the common heave cancels, 0 for a rigid lift."""
    clearance_change = np.asarray(clearance_end_m, float) - np.asarray(clearance_start_m, float)
    rise = corner_rise_m(corners_xy_m, attitude_end_rad[0] - attitude_start_rad[0],
                         attitude_end_rad[1] - attitude_start_rad[1])
    return float(np.ptp(clearance_change - rise))


class VerticalIntegrator:
    """E4 body heave from the IMU specific-force magnitude: v' = |f| - g_ref, z' = v.

    g_ref is the mean |f| of the last ``gravity_samples`` samples fed before :meth:`start`; the
    integration starts at rest (body on the crawler at the LEVEL start)."""

    def __init__(self, gravity_samples: int) -> None:
        self._gravity = deque(maxlen=gravity_samples)
        self.g_ref: float | None = None
        self.velocity_m_s = 0.0
        self.height_m = 0.0
        self._heights: dict[float, float] = {}

    @property
    def is_running(self) -> bool:
        return self.g_ref is not None

    def collect_gravity(self, magnitudes_m_s2) -> None:
        self._gravity.extend(float(m) for m in magnitudes_m_s2)

    def start(self) -> None:
        self.g_ref = float(np.mean(self._gravity)) if self._gravity else None
        self.velocity_m_s = 0.0
        self.height_m = 0.0

    def integrate(self, t_s: float, magnitudes_m_s2, sample_s: float) -> None:
        for magnitude in magnitudes_m_s2:
            self.velocity_m_s += (float(magnitude) - self.g_ref) * sample_s
            self.height_m += self.velocity_m_s * sample_s
        self._heights[float(t_s)] = self.height_m

    def height_at(self, t_s: float) -> float | None:
        if t_s in self._heights:
            return self._heights[t_s]
        near = [t for t in self._heights if abs(t - t_s) <= TIME_MATCH_S]
        return self._heights[near[0]] if near else None


def rise_ratio(height_start_m: float | None, height_end_m: float | None,
               stroke_advance_m: float) -> float | None:
    """E4: body rise over the tail per mean motor-stroke advance (None without heights)."""
    if height_start_m is None or height_end_m is None or stroke_advance_m <= 0.0:
        return None
    return (height_end_m - height_start_m) / stroke_advance_m


def specific_force_magnitudes(measurements) -> tuple[np.ndarray, bool]:
    """|f| of the IMU samples of a period (or of the period mean); True when per sample."""
    samples = getattr(measurements, "imu_specific_force_samples_m_s2", None)
    if samples is not None and len(samples):
        return np.linalg.norm(np.asarray(samples, float), axis=1), True
    return np.array([np.linalg.norm(np.asarray(measurements.specific_force_m_s2, float))]), False


# ----------------------------------------------------------------------- controller classes
@dataclass
class _FixState:
    """Candidate bookkeeping of one run (cleared by ``reset``)."""

    log: list = field(default_factory=list)
    """(t_s, phase, crawler max N, controller sum F N) per update."""
    window_checks: list = field(default_factory=list)
    """Every confirming tail: t_s, E1 spread, E4 rise ratio, vetoed."""
    e2_low_count: int = 0
    e2_relifts: int = 0
    e3_applied: bool = False
    s4_fired: bool = False
    lw_window_legs: frozenset = frozenset()
    """418 LW-b: re-approach set the current S-1 window was built with."""
    lw_clears: int = 0
    """418: windows cleared by LW-a / LW-b (a non-empty window only)."""


def make_candidate_class(c2, base_class, settings: CandidateSettings):
    """Subclass of the project C2 (``base_class``, the module's original class) with the passive
    record and the fixes of ``settings``; with every fix off the commands are the project's."""

    class CandidateC2(base_class):
        candidate = settings

        def __init__(self, geometry, config=None) -> None:
            super().__init__(geometry, config)
            self._base_config = self.config
            self._new_fix_state()
            _RUNNING["controller"] = self

        def _new_fix_state(self) -> None:
            self.fix = _FixState()
            period_s = self.config.r8.imu_sample_period_s or self.config.period_s
            self._imu_sample_s = period_s
            self._vertical = VerticalIntegrator(settings.e4_gravity_samples)

        def reset(self) -> None:
            self.config = self._base_config  # E3 changes the target per run
            super().reset()
            self._new_fix_state()

        # ------------------------------------------------------------ passive record
        def update(self, measurements):
            self._feed_vertical(measurements)
            command = super().update(measurements)
            self._record_period(measurements.t_s)
            return command

        def _feed_vertical(self, measurements) -> None:
            magnitudes, is_per_sample = specific_force_magnitudes(measurements)
            sample_s = self._imu_sample_s if is_per_sample else self.config.period_s
            phase = self._state.phase
            if phase is c2.C2Phase.TOUCH:
                self._vertical.collect_gravity(magnitudes)
                return
            if not self._vertical.is_running and phase is c2.C2Phase.LEVEL:
                self._vertical.start()
            if self._vertical.is_running:
                self._vertical.integrate(measurements.t_s, magnitudes, sample_s)

        def _record_period(self, t_s: float) -> None:
            reading = self._state.last_reading
            load_sum = float(np.sum(reading.cylinder_force_N)) if reading is not None else None
            self.fix.log.append((float(t_s), str(self._state.phase), _TRUTH["crawler_max_N"],
                                 load_sum))
            _TRUTH["crawler_max_N"] = 0.0

        # ------------------------------------------------------------ E1 / E4 / E3
        def _window_signals(self, tail) -> tuple[float, float | None]:
            first, last = tail[0], tail[-1]
            spread = kinematic_mismatch_m(self.geometry.crawler_corners_xy_m,
                                          first.corner_clearance_m, last.corner_clearance_m,
                                          first.raw_attitude_rad, last.raw_attitude_rad)
            ratio = rise_ratio(self._vertical.height_at(first.t_s),
                               self._vertical.height_at(last.t_s),
                               last.mean_motor_stroke_m - first.mean_motor_stroke_m)
            return spread, ratio

        def _veto_reason(self, spread: float, ratio: float | None) -> str | None:
            if settings.e1 and spread > settings.e1_max_mismatch_m:
                return f"E1:{spread * 1e3:.1f}mm"
            if settings.e4 and ratio is not None and ratio < settings.e4_min_rise_ratio:
                return f"E4:{ratio:.2f}"
            return None

        def _confirm_liftoff(self, t_s, tail, mean_load_N) -> None:
            spread, ratio = self._window_signals(tail)
            reason = self._veto_reason(spread, ratio)
            self.fix.window_checks.append({"t_s": round(float(t_s), 2),
                                           "e1_spread_mm": round(spread * 1e3, 2),
                                           "e4_rise_ratio": None if ratio is None
                                           else round(ratio, 3), "vetoed": reason})
            if reason is not None:
                self._soil_state().window.clear()
                self._add_event(t_s, f"{WINDOW_VETO_EVENT}:{reason}")
                return
            super()._confirm_liftoff(t_s, tail, mean_load_N)
            if settings.e3:
                self._apply_e3_margin(t_s)

        def _apply_e3_margin(self, t_s: float) -> None:
            soil = self._soil_state()
            settle = self._settle_attitude_rad()
            # the E cases confirm before the crawler-zone release (no soil mode) but carry a bias
            used_soil_response = soil.soil_mode_start_s is not None or soil.has_corner_bias
            if settings.e3_require_soil_use and not used_soil_response:
                return
            if settings.e3_min_clearance_at_P_m >= 0.0:
                c_min_tP = soil.clearance_at_plateau_start_m
                if c_min_tP is None or c_min_tP <= settings.e3_min_clearance_at_P_m:
                    return
            if self.fix.e3_applied or settle is None:
                return
            if max(abs(settle[0]), abs(settle[1])) <= settings.e3_tilt_min_rad:
                return
            thresholds = self.config.thresholds
            target_m = thresholds.clearance_target_m + settings.e3_margin_m
            self.config = replace(self.config,
                                  thresholds=replace(thresholds, clearance_target_m=target_m))
            self.fix.e3_applied = True
            self._add_event(t_s, f"{E3_EVENT}:{target_m * 1e3:.0f}mm")

        # ------------------------------------------------------------ 418 LW-a / LW-b
        def _update_liftoff_window(self, reading) -> None:
            if not (settings.lw_restart or settings.lw_exclude):
                super()._update_liftoff_window(reading)
                return
            soil = self._soil_state()
            if soil.is_liftoff_confirmed:
                return
            active = frozenset(int(leg) for leg in self._state.active_reapproaches)
            if settings.lw_restart:
                if active:
                    self._clear_lw_window(reading.t_s, LW_RESTART_EVENT, active)
                    return
                super()._update_liftoff_window(reading)
                return
            if active != self.fix.lw_window_legs:
                self._clear_lw_window(reading.t_s, LW_SET_EVENT, active)
                self.fix.lw_window_legs = active
            if not active:
                super()._update_liftoff_window(reading)
                return
            keep = np.array([leg not in active for leg in range(len(c2.LEG_ORDER))])
            if not keep.any():
                soil.window.clear()
                return
            self._update_liftoff_window_on(reading, keep)

        def _clear_lw_window(self, t_s: float, event: str, active: frozenset) -> None:
            soil = self._soil_state()
            if soil.window:
                self.fix.lw_clears += 1
                legs = ",".join(c2.LEG_ORDER[leg] for leg in sorted(active)) or "none"
                self._add_event(t_s, f"{event}:{legs}")
            soil.window.clear()

        def _update_liftoff_window_on(self, reading, keep: np.ndarray) -> None:
            """c2 ``_update_liftoff_window`` with the plateau-period speed condition and the mean
            motor stroke over the ``keep`` legs (LW-b); load sum of all four legs."""
            soil = self._soil_state()
            applied = np.asarray(self._state.applied_output_m_s, dtype=float)[keep]
            min_mean_m_s = (self.config.soil.plateau_mean_speed_fraction
                            * self.geometry.max_speed_m_s)
            if not (np.all(applied >= 0.0) and float(np.mean(applied)) >= min_mean_m_s):
                soil.window.clear()
                return
            strokes_m = np.asarray(reading.motor_stroke_m, dtype=float)
            soil.window.append(c2._PlateauSample(
                t_s=float(reading.t_s),
                mean_motor_stroke_m=float(np.mean(strokes_m[keep])),
                load_sum_N=float(np.sum(reading.cylinder_force_N)),
                corner_clearance_m=self.geometry.clearance_corners_m(reading.rod_stroke_m),
                raw_attitude_rad=self._period_raw_attitude_rad()))
            tail = self._plateau_tail()
            if tail is None:
                return
            soil_settings = self.config.soil
            rise_N = self._plateau_rise_N(tail)
            mean_load_N = float(np.mean([sample.load_sum_N for sample in tail]))
            if (rise_N <= soil_settings.plateau_rise_max_N and mean_load_N
                    >= soil_settings.plausibility_fraction * self._reference_weight_N()):
                self._confirm_liftoff(reading.t_s, tail, mean_load_N)

        # ------------------------------------------------------------ E2
        def _hold_probe_or_relevel(self, reading):
            if settings.e2 and self._is_recontact_suspected(reading):
                self._undo_liftoff(reading.t_s)
                self._start_relevel()
                return None
            return super()._hold_probe_or_relevel(reading)

        def _is_recontact_suspected(self, reading) -> bool:
            soil = self._soil_state()
            if not (self.config.soil.enable and soil.is_liftoff_confirmed):
                return False
            if soil.weight_estimate_N is None or self.fix.e2_relifts >= settings.e2_max_relifts:
                return False
            ratio = float(np.sum(reading.cylinder_force_N)) / soil.weight_estimate_N
            is_low = ratio < 1.0 - settings.e2_drop_fraction
            self.fix.e2_low_count = self.fix.e2_low_count + 1 if is_low else 0
            if self.fix.e2_low_count < settings.e2_confirm_samples:
                return False
            self._add_event(reading.t_s, f"{E2_EVENT}:{ratio:.3f}", is_warning=True)
            return True

        def _undo_liftoff(self, t_s: float) -> None:
            """Back to "lift-off not confirmed": soil mode starts again at the next LEVEL period
            and DONE waits for a new S-1 window (the bias stays until the new LOC)."""
            soil = self._soil_state()
            soil.is_liftoff_confirmed = False
            soil.is_soil_mode = False
            soil.soil_mode_start_stroke_m = None
            soil.window.clear()
            self.fix.e2_low_count = 0
            self.fix.e2_relifts += 1

        # ------------------------------------------------------------ RA
        def _reanchor_skip_reason(self, reading):
            reason = super()._reanchor_skip_reason(reading)
            if reason is not None or not settings.reanchor_soil_skip:
                return reason
            soil = self._soil_state()
            if soil.soil_mode_start_s is not None or soil.has_corner_bias:
                return REANCHOR_SOIL_REASON
            return None

        # ------------------------------------------------------------ S4
        def _hold_crawler_zone_until_liftoff(self, reading) -> None:
            super()._hold_crawler_zone_until_liftoff(reading)
            if not settings.s4_stroke_limit or self._state.phase is c2.C2Phase.FAULT:
                return
            soil = self._soil_state()
            if soil.is_liftoff_confirmed or not soil.is_soil_mode:
                return
            strokes = np.asarray(reading.motor_stroke_m, float)
            stroke_m = strokes.max() if settings.s4_stroke_basis == "max" else strokes.mean()
            if stroke_m >= self._lift_guard_stroke_m():
                self.fix.s4_fired = True
                self._add_event(reading.t_s, S4_STROKE_EVENT, is_warning=True)
                self._state.phase = c2.C2Phase.FAULT

        def _lift_guard_stroke_m(self) -> float:
            extra_m = self.config.lift_stroke_guard.extra_margin_m
            return self.geometry.stroke_soft_max_m - c2.STROKE_END_MARGIN_M - extra_m

    CandidateC2.__name__ = CandidateC2.__qualname__ = "CandidateC2"
    return CandidateC2


# --------------------------------------------------------------------------- run metrics
def run_metrics(log, events, weight_N: float | None) -> dict:
    """False LOCs and READY crawler re-contacts from the per-period truth log.

    Args:
        log: (t_s, phase, crawler max N, controller sum F N) per control period.
        events: (t_s, name) controller events.
        weight_N: plant weight m g (None: false LOC not judged).
    """
    crawler_by_t = {round(t, 6): crawler for t, _, crawler, _ in log}
    loc_crawler_kN = []
    for t_s, name in events:
        if name.startswith(LOC_EVENT):
            loc_crawler_kN.append(crawler_by_t.get(round(t_s, 6), math.nan) / 1e3)
    limit_kN = None if weight_N is None else FALSE_LOC_WEIGHT_FRACTION * weight_N / 1e3
    false_locs = 0 if limit_kN is None else sum(1 for v in loc_crawler_kN if v >= limit_kN)
    recontacts, ready_max_N, was_loaded_ready = 0, 0.0, False
    for _, phase, crawler, _ in log:
        is_ready = phase == "ready"
        is_loaded = is_ready and crawler > 0.0
        if is_loaded and not was_loaded_ready:
            recontacts += 1
        if is_ready:
            ready_max_N = max(ready_max_N, crawler)
        was_loaded_ready = is_loaded
    return {"n_loc": len(loc_crawler_kN), "loc_crawler_kN": [round(v, 2) for v in loc_crawler_kN],
            "false_loc": false_locs, "false_loc_limit_kN": limit_kN,
            "ready_recontacts": recontacts, "ready_crawler_max_kN": round(ready_max_N / 1e3, 2)}


def ready_load_ratio_min(log, weight_estimate_N: float | None) -> float | None:
    """Smallest controller sum F / W_hat in READY (the E2 signal, recorded for every run)."""
    if not weight_estimate_N:
        return None
    ratios = [load / weight_estimate_N for _, phase, _, load in log
              if phase == "ready" and load is not None]
    return round(min(ratios), 4) if ratios else None


# ------------------------------------------------------------------------- worker patching
@contextlib.contextmanager
def _argv_as_root():
    """The s8 screens read ``sys.argv[1]`` as the project root at import."""
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


def _install_truth_hook(cl) -> None:
    if getattr(cl._lagged_step, "is_truth_hook", False):
        return
    original = cl._lagged_step

    def lagged_step_recorded(plant, command, valve, steps):
        accumulated = original(plant, command, valve, steps)
        _TRUTH["crawler_max_N"] = max(_TRUTH["crawler_max_N"], float(accumulated[15]))
        _TRUTH["crawler_series"].append((float(plant.t), float(accumulated[15])))
        if _TRUTH["weight_N"] is None and hasattr(plant, "m") and hasattr(plant, "g"):
            _TRUTH["weight_N"] = float(plant.m * plant.g)
        return accumulated

    lagged_step_recorded.is_truth_hook = True
    cl._lagged_step = lagged_step_recorded


def _install_candidate(candidate: str, overrides: dict):
    """Swap ``c2.C2Controller`` (every harness builds through the module attribute) for the
    candidate class of this job and hook the truth record."""
    from outrigger_sim.control import c2

    original = _RUNNING.setdefault("original_class", c2.C2Controller)
    settings = parse_candidate(candidate, overrides)
    c2.C2Controller = make_candidate_class(c2, original, settings)
    import s9_soil_closed_loop as sl

    _install_truth_hook(sl._imports()[0])
    _TRUTH.update(crawler_max_N=0.0, weight_N=None, crawler_series=[])
    _RUNNING.pop("controller", None)
    return c2, settings


# --------------------------------------------------------------------------- suite adapters
def _slope_cases() -> list[dict]:
    import s9_soil_slope as slope

    table = json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))[SETTLE_TABLE_KEY]
    cases = slope.attach_settle_table(slope.build_cases(), table)
    return [case.to_dict() for case in cases]


def _g6_keys() -> list[str]:
    with _argv_as_root():
        import r72_g6_screen as g6
    return g6.all_jobs("all") + g6.all_jobs("rigid_all")


def _g8_keys() -> list[str]:
    with _argv_as_root():
        import r70_p28_screen as p28
    return p28.all_jobs("all", ["proj"])


def _p3b_cases() -> list[dict]:
    import s9_runs

    soil = s9_runs.soil_cases(("base",))
    rigid = [case for case in s9_runs.rigid_cases() if case["id"].startswith("base|")]
    return [{**case, "trace": False} for case in soil + rigid]


def suite_cases(suite: str) -> list[tuple[str, object]]:
    """(case id, job payload) of a suite."""
    if suite == "slope":
        return [(case["id"], case) for case in _slope_cases()]
    if suite == "g6":
        return [(key, key) for key in _g6_keys()]
    if suite == "g8":
        return [(key, key) for key in _g8_keys()]
    if suite == "p3b":
        return [(case["id"], case) for case in _p3b_cases()]
    raise ValueError(f"unknown suite {suite!r}, expected {SUITES}")


def _slope_record(payload: dict) -> dict:
    import s9_soil_slope as slope

    result = slope.run_one(payload)
    if "error" in result:
        return {"error": result["error"], "tb": result.get("tb")}
    run, rows = result["run"], result["rows"]
    return {"verdict": result["verdict"], "passed": result["verdict"] in (
        slope.VERDICT_PASS, slope.VERDICT_STROKE_LIMITED_PASS),
        "failed_rows": result["failed_rows"], "hash": run.get("commands_sha256"),
        "t_ready_s": run.get("t_ready_s"), "min_force_kN": rows["SL-1"]["min_true_Fcyl_kN"],
        "att_end_deg": run.get("att_end_deg"), "max_stroke_mm": run.get("max_motor_stroke_mm"),
        "final_phase": run.get("final_phase"), "rut_ready_mm": run.get("clear_true_ready_mm"),
        "crawler_N_max_after_ready": run.get("crawler_N_max_after_ready"),
        "warnings": result.get("warnings", []),
        # spec 420.2b P3-1_transient_recontact, spec 419.8 P3-2_late_loc_reapproach and its five
        # conditions (s9_soil_slope judge)
        "flags": (list(rows["P3-1"].get("flag_names") or [])
                  + ([rows["P3-2"]["flag_name"]] if rows["P3-2"].get("flag") else [])),
        "late_loc_reapproach": rows["P3-2"].get("late_loc_reapproach")}


def _g6_record(key: str) -> dict:
    with _argv_as_root():
        import r72_g6_screen as g6
    rec = g6.job(key)
    if "error" in rec:
        return {"error": rec["error"], "tb": rec.get("tb")}
    return {"verdict": "pass" if rec["pass"] else "fail", "passed": rec["pass"],
            "failed_rows": [k for k, v in rec["gates"].items() if not v],
            "hash": rec.get("commands_sha256"), "t_ready_s": rec.get("t_ready_s"),
            "min_force_kN": rec.get("min_true_Fcyl_after_off_kN"),
            "att_end_deg": rec.get("att_end_deg"), "max_stroke_mm": rec.get("max_motor_stroke_mm"),
            "final_phase": rec.get("final_phase"), "rut_ready_mm": rec.get("rut_clear_ready_mm"),
            "warnings": rec.get("warnings", []),
            # spec 419.8: G6-2_late_loc_reapproach and its five conditions (r72 judge)
            "flags": rec.get("flags", []), "late_loc_reapproach": rec.get("late_loc_reapproach")}


def _g8_record(key: str) -> dict:
    with _argv_as_root():
        import r70_p28_screen as p28
    res = p28.job(f"{key}" if key.endswith("|proj") else f"{key}|proj")
    if "error" in res:
        return {"error": res["error"], "tb": res.get("trace")}
    min_force = res.get("min_F_after_liftoff_kN")
    return {"verdict": "pass" if res["pass"] else "fail", "passed": res["pass"],
            "failed_rows": [k for k, v in res["gates"].items() if not v] + res.get("flags", []),
            "hash": res.get("cmd_sha256"), "t_ready_s": res.get("t_ready"),
            "min_force_kN": None if not min_force else min(min_force.values()),
            "att_end_deg": res.get("att_end_deg"),
            "max_stroke_mm": max(res.get("stroke_max_run_mm") or [math.nan]),
            "final_phase": res.get("final_phase"), "warnings": sorted(
                {name.split(":")[0] for _, name in res.get("events", [])
                 if name.startswith(("WARN", "FAULT"))})}


def _make_preset_controller(cl, c2, variant):
    """Project preset factory for the p3b suite (as r72 ``make_controller_preset``)."""
    del variant
    config = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True,
                              with_reapproach=True)
    controller = c2.C2Controller.from_params(cl.PARAMS, config)
    controller.reset()
    return controller


def p3_lite_gates(out: dict, f_min_kN: float) -> dict:
    """P3-1 .. P3-5 and FAULT / READY on a ``run_case`` output (as the r72 G6 rows, no rut end)."""
    min_off = out.get("min_true_Fcyl_after_off_kN")
    att_end = out.get("att_end_deg") or [math.nan, math.nan]
    return {
        "crawler": bool(out.get("crawler_N_max_after_ready") == 0.0
                        and out.get("n_crawler_recontact", 1) == 0),
        "Fmin": bool(min_off is not None and min_off >= f_min_kN),
        "att": bool(np.all(np.abs(att_end) <= ATTITUDE_TOL_DEG)),
        "rut": bool((out.get("clear_true_ready_mm") or -1.0) >= RUT_MIN_MM),
        "fault_ready": bool(out.get("final_phase") not in FAULT_PHASES
                            and out.get("t_ready_s") is not None),
    }


def _p3b_record(case: dict) -> dict:
    import s9_soil_closed_loop as sl

    sl.make_controller = _make_preset_controller
    out = sl.run_case(case)
    f_min_kN = _RUNNING["controller"].geometry.F_min_N / 1e3
    gates = p3_lite_gates(out, f_min_kN)
    return {"verdict": "pass" if all(gates.values()) else "fail", "passed": all(gates.values()),
            "failed_rows": [k for k, v in gates.items() if not v],
            "hash": out.get("commands_sha256"), "t_ready_s": out.get("t_ready_s"),
            "min_force_kN": out.get("min_true_Fcyl_after_off_kN"),
            "att_end_deg": out.get("att_end_deg"), "max_stroke_mm": out.get("max_motor_stroke_mm"),
            "final_phase": out.get("final_phase"), "rut_ready_mm": out.get("clear_true_ready_mm"),
            "warnings": sorted({e.split(" ", 1)[1].split(":")[0] for e in out.get("events", [])
                                if e.split(" ", 1)[1].startswith(("WARN", "FAULT"))})}


SUITE_RUNNERS = {"slope": _slope_record, "g6": _g6_record, "g8": _g8_record, "p3b": _p3b_record}


def _controller_record(controller) -> dict:
    """Candidate record of the run's controller: metrics, window checks, fix events."""
    events = [(float(e.t_s), e.name) for e in controller.events]
    soil = controller._soil_state()
    metrics = run_metrics(controller.fix.log, events, _TRUTH["weight_N"])
    metrics["ready_load_ratio_min"] = ready_load_ratio_min(controller.fix.log,
                                                           soil.weight_estimate_N)
    metrics["window_checks"] = controller.fix.window_checks[:20]
    metrics["fix_events"] = [(round(t, 2), n) for t, n in events
                             if n.startswith((FIX_EVENT_PREFIX, S4_STROKE_EVENT))
                             or n.startswith("reanchor_")][:30]
    metrics["e3_applied"] = controller.fix.e3_applied
    metrics["lw_clears"] = controller.fix.lw_clears
    t_loc_s = next((t for t, name in events if name.startswith(LOC_EVENT)), None)
    metrics["crawler_recontact"] = crawler_recontact_record(
        _TRUTH["crawler_series"], _TRUTH["weight_N"], t_loc_s)
    return metrics


def run_job(job: dict) -> dict:
    """Worker entry: one case of one suite with one candidate."""
    t0 = time.perf_counter()
    record = {"suite": job["suite"], "id": job["id"], "candidate": job["candidate"]}
    try:
        _install_candidate(job["candidate"], job.get("params") or {})
        record.update(SUITE_RUNNERS[job["suite"]](job["payload"]))
        controller = _RUNNING.get("controller")
        if controller is not None and "error" not in record:
            record["metrics"] = _controller_record(controller)
    except Exception as exc:  # keep the batch going, record the failure
        record.update(error=repr(exc), tb=traceback.format_exc()[-3000:])
    record["wall_s"] = round(time.perf_counter() - t0, 1)
    return record


# ----------------------------------------------------------------------------- comparison
def _max_abs(values) -> float | None:
    if not values:
        return None
    return float(np.max(np.abs(np.asarray(values, float))))


def _difference(after, before):
    return None if after is None or before is None else round(after - before, 3)


def compare_records(before: dict, after: dict) -> dict:
    """One case: candidate ``after`` against the baseline ``before``."""
    m_before, m_after = before.get("metrics", {}), after.get("metrics", {})
    return {
        "suite": after["suite"], "id": after["id"], "candidate": after["candidate"],
        "verdict_before": before.get("verdict"), "verdict_after": after.get("verdict"),
        "verdict_changed": before.get("verdict") != after.get("verdict"),
        "hash_same": before.get("hash") is not None and before.get("hash") == after.get("hash"),
        "d_ready_s": _difference(after.get("t_ready_s"), before.get("t_ready_s")),
        "d_min_force_kN": _difference(after.get("min_force_kN"), before.get("min_force_kN")),
        "d_att_end_deg": _difference(_max_abs(after.get("att_end_deg")),
                                     _max_abs(before.get("att_end_deg"))),
        "false_loc_before": m_before.get("false_loc"), "false_loc_after": m_after.get("false_loc"),
        "ready_recontacts_before": m_before.get("ready_recontacts"),
        "ready_recontacts_after": m_after.get("ready_recontacts"),
        "ready_crawler_max_kN_after": m_after.get("ready_crawler_max_kN"),
        "final_phase_after": after.get("final_phase"),
        "fix_events_after": ";".join(n for _, n in m_after.get("fix_events", [])[:6]),
    }


def is_e_case(record: dict) -> bool:
    """Baseline run with the defect E: a false LOC or crawler load in READY."""
    metrics = record.get("metrics") or {}
    return bool(metrics.get("false_loc") or metrics.get("ready_recontacts"))


def summarize(records: list[dict]) -> dict:
    """Per suite and candidate: counts against the baseline of the same case."""
    baseline = {(r["suite"], r["id"]): r for r in records
                if r["candidate"] == BASELINE and "error" not in r}
    rows, summary = [], {}
    for record in records:
        if record["candidate"] == BASELINE:
            continue
        before = baseline.get((record["suite"], record["id"]))
        key = f"{record['suite']}|{record['candidate']}"
        entry = summary.setdefault(key, {"n": 0, "errors": 0, "no_baseline": 0,
                                         "verdict_changed": 0, "pass_to_fail": 0,
                                         "fail_to_pass": 0, "hash_same": 0, "e_cases": 0,
                                         "e_resolved": 0, "false_loc_after": 0,
                                         "ready_recontacts_after": 0})
        entry["n"] += 1
        if "error" in record:
            entry["errors"] += 1
            continue
        if before is None:
            entry["no_baseline"] += 1
            continue
        row = compare_records(before, record)
        rows.append(row)
        _count_row(entry, row, before, record)
    return {"by_suite_candidate": summary, "rows": rows}


def _count_row(entry: dict, row: dict, before: dict, after: dict) -> None:
    entry["verdict_changed"] += row["verdict_changed"]
    entry["pass_to_fail"] += bool(before.get("passed") and not after.get("passed"))
    entry["fail_to_pass"] += bool(not before.get("passed") and after.get("passed"))
    entry["hash_same"] += row["hash_same"]
    entry["false_loc_after"] += bool(row["false_loc_after"])
    entry["ready_recontacts_after"] += bool(row["ready_recontacts_after"])
    if is_e_case(before):
        entry["e_cases"] += 1
        entry["e_resolved"] += not is_e_case(after)


def write_outputs(out_path: Path, records: list[dict], meta: dict) -> dict:
    summary = summarize(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "summary": summary["by_suite_candidate"],
               "comparison": summary["rows"], "records": records}
    out_path.write_text(json.dumps(payload, indent=1, default=float), encoding="utf-8")
    rows = summary["rows"]
    if rows:
        with open(out_path.with_name(out_path.stem + "_compare.csv"), "w", encoding="utf-8",
                  newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return summary


# ------------------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="S9 slope fix candidates on the reduced harnesses")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "list"):
        command = sub.add_parser(name)
        command.add_argument("--suite", required=True, help=f"comma list of {SUITES}")
        command.add_argument("--filter", default="", help="comma list of case-id substrings")
    run = sub.choices["run"]
    run.add_argument("--candidates", default=BASELINE)
    run.add_argument("--workers", type=int, default=2)
    run.add_argument("--affinity", default=None, help="hex mask of the parent (inherited)")
    run.add_argument("--param", action="append", default=[], help="name=value override")
    run.add_argument("--settle-hook", default="harness", choices=("harness", "p0"))
    run.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR / "fix_candidates.json")
    merge = sub.add_parser("compare")
    merge.add_argument("--out", type=Path, required=True)
    merge.add_argument("inputs", nargs="+", type=Path)
    return parser


def _filtered(cases, text: str):
    needles = [n for n in text.split(",") if n]
    return [c for c in cases if not needles or any(n in c[0] for n in needles)]


def _run(args) -> None:
    import s9_soil_slope as slope

    os.environ[SETTLE_HOOK_ENV] = args.settle_hook  # g6 / p3b plants read it (pool inherits)
    overrides = parse_param_overrides(args.param)
    candidates = [c for c in args.candidates.split(",") if c]
    for candidate in candidates:
        parse_candidate(candidate, overrides)  # fail before any run
    placement = slope.set_parent_affinity(slope.parse_affinity(args.affinity))
    records, t0 = [], time.perf_counter()
    for suite in args.suite.split(","):
        cases = _filtered(suite_cases(suite), args.filter)
        jobs = [{"suite": suite, "id": case_id, "payload": payload, "candidate": candidate,
                 "params": overrides} for case_id, payload in cases for candidate in candidates]
        with Pool(max(1, min(args.workers, len(jobs)))) as pool:
            records += pool.map(run_job, jobs, chunksize=1)
    meta = {"script": "04_scripts/03_control/s9/s9_slope_fix_candidates.py",
            "suites": args.suite, "candidates": candidates, "params": overrides,
            "defaults": asdict(CandidateSettings()), "filter": args.filter,
            "settle_hook": args.settle_hook, "workers": args.workers, "placement": placement,
            "wall_s": round(time.perf_counter() - t0, 1), "n_records": len(records)}
    summary = write_outputs(args.out, records, meta)
    _print_records(records)
    print(json.dumps(summary["by_suite_candidate"], indent=1))
    print("wall", meta["wall_s"], "s ->", args.out)


def _print_records(records: list[dict]) -> None:
    for record in records:
        if "error" in record:
            print(record["suite"], record["id"], record["candidate"], "ERROR", record["error"])
            continue
        metrics = record.get("metrics", {})
        print(record["suite"], record["id"], record["candidate"], record["verdict"],
              "hash", (record.get("hash") or "")[:12], "ready", record.get("t_ready_s"),
              "minF", record.get("min_force_kN"), "att", record.get("att_end_deg"),
              "falseLOC", metrics.get("false_loc"), "LOCcrawler", metrics.get("loc_crawler_kN"),
              "READYrecontact", metrics.get("ready_recontacts"),
              "ratioREADY", metrics.get("ready_load_ratio_min"),
              "windows", [(w["t_s"], w["e1_spread_mm"], w["e4_rise_ratio"], w["vetoed"])
                          for w in metrics.get("window_checks", [])][:6],
              "fix", metrics.get("fix_events"), "phase", record.get("final_phase"),
              "wall", record["wall_s"])


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "list":
        for suite in args.suite.split(","):
            cases = _filtered(suite_cases(suite), args.filter)
            for case_id, _ in cases:
                print(suite, case_id)
            print(suite, len(cases), "cases")
        return
    if args.command == "compare":
        records = []
        for path in args.inputs:
            records += json.loads(path.read_text(encoding="utf-8"))["records"]
        summary = write_outputs(args.out, records, {"merged_from": [str(p) for p in args.inputs]})
        print(json.dumps(summary["by_suite_candidate"], indent=1))
        return
    _run(args)


if __name__ == "__main__":
    main()
