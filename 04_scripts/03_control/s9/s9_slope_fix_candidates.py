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
  L1 / L2 / L4  spec 424.3 (Q-D, deep virgin-branch pad sinking): L1 revokes the LOC when the 1 s
      mean load sum rises above W_hat + max(2 kN, 0.005 W_ref) on 2 periods before 20 mm of
      mean stroke past the LOC or the first DONE (max 2, ``FIX_LOC_REVOKE``); L2 holds a flat
      window with c_min(t_P) > 10 mm for 5 mm more stroke and confirms only with a rise <= 1 kN
      (``FIX_L2_CONFIRM`` / ``FIX_L2_REJECT``); L4 keeps the result of a leg an earlier probe
      round confirmed instead of probing it again (``FIX_PROBE_REUSE``).
  L1g / L1gs / L2g  spec 424.10.1 (after the L1+L2 regression): L1g watches only a LOC with a
      soil sign (soil mode ran, or c_min(t_P) > 10 mm on a settle tilt > 1 deg); L1gs adds the
      stroke guard (max motor stroke >= lift guard - 40 mm: no revocation, record
      ``FIX_LOC_REVOKE_SKIPPED:stroke``; a revocation keeps the P-S8-31 margin); L2g holds a
      window only when the soil mode ran in the lifting cycle.
  D1 / D2 / D3  spec 424.4.1 (Q-C redefined 2026-10-29, the leg losing its load while the
      LWa-delayed LOC waits): before the LOC, soil mode or not, a leg of the four (a
      re-approaching one included) whose lower load is below 3 F_min and fell >= 1 kN since the
      last period: D1 stops the other legs (``FIX_FALL_HOLD``), D2 slows them to a mean of
      0.16 v_max (``FIX_FALL_SLOW``); until that leg reads 3.5 F_min, a re-approach of it makes
      contact, or 3 s. D3: the second and later pre-LOC re-approach of a leg runs at x 2 instead
      of x 4 and the other legs slow as D2 while it runs (``FIX_REAPPROACH_SLOW``). A period in
      which the P30fz slowdown runs is left to P30fz (no overlay). D1 and D2 are alternatives.
  D1p  spec 424.9 decision 2: D1, and in a P30fz period the D1 stop still runs once the watched
      leg fell >= 1 kN since the last period and reads below 2 F_min (latched until the D1
      release, ``FIX_FALL_HOLD_OVER_P30FZ``). D1p counts the fall only in a period the P30fz
      slowdown already ran into (the leg kept falling under it); D1p0 (comparison) also in the
      period P30fz starts.
  D1r  spec 424.9.2: predictive stop. Before the final LOC, a leg whose C2 R-5 prediction (4
      periods ahead, past the output delay and the ramp) is below F_min + 5 kN while its lower
      load reads below 3 F_min stops the other legs in that period, also over P30fz
      (``FIX_DIAG_HOLD_PRED``); released at a prediction >= F_min + 10 kN, a re-approach
      contact of that leg, or 3 s. Alternative to D1 / D2; D1r+D3 allowed.
  D1q / D1qa / D1qb / D2q  spec 424.9.3 (the D1p0 timing with a narrower gate and a shorter
      stop): in the period the P30fz gate starts a slowdown, its leg i is checked against
      G-a "deep fall" (lower load minus 4 x its fall since the last period below F_min + 5 kN)
      and G-b "one soft pad" (stroke twist (s_FL - s_FR) - (s_RL - s_RR) of the rod-stroke
      change since the first pre-LOC LEVEL period, its stroke-plane part removed, above
      ``d1q_twist_m`` in size). D1q needs G-a and G-b, D1qa G-a, D1qb G-b; the other legs (not
      a re-approaching one) stop over P30fz (D2q: slow to 0.16 v_max), ``FIX_DIAG_HOLD_Q:<leg>:
      <a|b|ab>``; released at 3.5 F_min, a re-approach contact of leg i, ``d1q_hold_max_s``
      (1.5 s) per event, ``d1q_hold_total_s`` (3 s) per run. Alternatives to each other and to
      D1 / D2 / D1p / D1p0 / D1r; with D3 allowed.
  Parameters can also ride in a candidate name as ``name=value`` tokens (r79 ``R79_CANDIDATE``
  has no ``--param``), e.g. ``D1q+d1q_twist_m=0.010``.
  S5 / S6  spec 424.8.2 (operating weight +20 %, the soil-mode push runs out): S5 grows the push
      limit (150 mm) by 50 mm when the last 50 mm of push raised the load sum by >= 0.02 W_ref
      and the longest leg + 50 mm stays 30 mm below the lift guard stroke, up to a 300 mm limit
      (``FIX_PUSH_EXTEND:<limit mm>``); S6 confirms the LOC on a saturating S-1 rise (r_k <=
      0.3 r_(k-1), r_k <= 4 kN, the 0.85 W_ref clause kept) on a run with the soil sign
      (``FIX_S6_LOC``), only with L1. Every run records ``s1_rise_trace`` (window end t, mean
      stroke mm, rise kN, mean load kN, soil push mm).
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
  h6     spec 422.3 operating-weight sensitivity, 32 cases (``s9_soil_slope.py`` group H6, mass
         scale and F_s per case, settle table attached as for slope)
  v3s    spec 424.10 R-e: V-3 sensor 72 + beta 16 = 88 cases (``s9_runs.sensor_cases`` /
         ``beta_cases``, the ids of ``07_results/S9/v3/sensor.json`` / ``beta.json``) with the
         project preset and the p3b record
Compared per case against "current": verdict, command SHA-256, dREADY, d min true F_cyl, d end
attitude, false LOCs (crawler force >= 0.01 W in the LOC period), crawler re-contacts in READY;
whether a fix acted (a ``FIX_*`` event), idle runs with a changed hash (spec 424.6 A-5) and, on
the slope / h6 suites, A-3 (relaxed 2026-10-29: rigid / G1 hash = current; J1 / J2 / S1 with an
acted fix: no pass -> fail, no new P3-2 violation, READY <= +5 s).

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

import late_loc_rule  # noqa: E402  (shared harness judge rules)
from late_loc_rule import crawler_recontact_record  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev80"
SETTLE_TABLE_PATH = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
SETTLE_TABLE_KEY = "hook_harness"
SETTLE_HOOK_ENV = "S9_SETTLE_HOOK"

BASELINE = "current"
CANDIDATE_TOKENS = ("E1", "E2", "E3", "E4", "RA", "S4", "E3w", "E3c7", "E3c10", "LWa", "LWb",
                    "L1", "L2", "L4", "D1", "D1p", "D1p0", "D1r", "D2", "D3", "S5", "S6",
                    "D1q", "D1qa", "D1qb", "D2q", "L1g", "L1gs", "L2g")
QUICK_HOLD_TOKENS = ("D1q", "D1qa", "D1qb", "D2q")
"""Spec 424.9.3 variants: alternatives to each other (one per candidate)."""
TWIST_SIGNS = np.array([1.0, -1.0, -1.0, 1.0])
"""Stroke twist ``(s_FL - s_FR) - (s_RL - s_RR)`` in the leg order FL, FR, RL, RR."""
LW_RESTART_EVENT = "FIX_LW_RESTART"
LW_SET_EVENT = "FIX_LW_SET"
LOC_REVOKE_EVENT = "FIX_LOC_REVOKE"
LOC_REVOKE_SKIPPED_EVENT = "FIX_LOC_REVOKE_SKIPPED"
"""L1-s record (``:stroke``): a revocation the stroke guard withheld; commands unchanged."""
RECORD_ONLY_FIX_EVENTS = (LOC_REVOKE_SKIPPED_EVENT,)
"""``FIX_*`` events that change no command (not "acted" for the hash rule A-5)."""
L2_REJECT_EVENT = "FIX_L2_REJECT"
L2_CONFIRM_EVENT = "FIX_L2_CONFIRM"
PROJECT_L1_EVENTS = ("INFO_LOC_REVOKED", "INFO_LOC_REVOKE_SKIPPED")
"""03_src P-S8-33 events (spec 424.10.2), kept in ``fix_events`` with the tokens' ones."""
PROBE_REUSE_EVENT = "FIX_PROBE_REUSE"
FALL_HOLD_EVENT = "FIX_FALL_HOLD"
FALL_SLOW_EVENT = "FIX_FALL_SLOW"
REPEAT_REAPPROACH_SLOW_EVENT = "FIX_REAPPROACH_SLOW"
FALL_HOLD_OVER_P30FZ_EVENT = "FIX_FALL_HOLD_OVER_P30FZ"
DIAG_HOLD_PRED_EVENT = "FIX_DIAG_HOLD_PRED"
DIAG_HOLD_QUICK_EVENT = "FIX_DIAG_HOLD_Q"
QUICK_GATE_CHECKS_MAX = 20
"""Rows kept of the D1q gate record (one per P30fz start)."""
REAPPROACH_CONTACT_OUTCOME = "contact"
LEG_NAMES = ("FL", "FR", "RL", "RR")
PUSH_EXTEND_EVENT = "FIX_PUSH_EXTEND"
S6_LOC_EVENT = "FIX_S6_LOC"
S1_RISE_TRACE_MAX = 400
"""Rows kept of ``s1_rise_trace`` (10 Hz: 40 s of window ends)."""
SUITES = ("slope", "g6", "g8", "p3b", "h6", "v3s")

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
A3_SUITES = ("slope", "h6")
A3_HARD_GROUNDS = ("rigid", "G1")
"""Spec 424.6 A-3: grounds where every candidate must keep the "current" command hash."""
A3_SOFT_GROUNDS = ("J1", "J2", "S1")
"""Spec 424.6 A-3 (relaxed 2026-10-29): an acted candidate may change the hash here."""
A3_TIME_ROW = "P3-2"
A3_READY_INCREASE_MAX_S = 5.0

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
    # spec 424.3 Q-D (deep virgin-branch pad sinking)
    l1_revoke: bool = False
    """L1: after the LOC (until the mean motor stroke is ``l1_watch_m`` past it or the first
    DONE) a 1 s mean load sum above W_hat + max(``l1_rise_N``, ``l1_rise_fraction_W`` W_ref) on
    ``l1_confirm_periods`` periods in a row revokes the LOC (``FIX_LOC_REVOKE``)."""
    l1_watch_m: float = 0.020
    l1_rise_N: float = 2000.0
    l1_rise_fraction_W: float = 0.005
    l1_mean_s: float = 1.0
    l1_confirm_periods: int = 2
    l1_max_revokes: int = 2
    l2_confirm_window: bool = False
    """L2: a flat window with c_min(t_P) above ``l2_min_clearance_at_P_m`` confirms only after
    ``l2_extra_m`` more mean stroke with a load-sum rise <= ``l2_rise_N``; else the window is
    cleared (``FIX_L2_REJECT``)."""
    l2_min_clearance_at_P_m: float = 0.010
    l2_extra_m: float = 0.005
    l2_rise_N: float = 1000.0
    # spec 424.10.1 (2026-10-29): gated L1 / L2 after the L1+L2 regression
    l1_soil_gate: bool = False
    """L1-g: the L1 watch starts only at a LOC with a soil sign: the soil mode ran, or
    ``c_min(t_P)`` > ``l1_gate_min_clearance_at_P_m`` with a settle tilt above
    ``l1_gate_tilt_min_rad`` (the E3c10 sign; a level rigid floor never has it)."""
    l1_gate_min_clearance_at_P_m: float = 0.010
    l1_gate_tilt_min_rad: float = math.radians(1.0)
    l1_stroke_guard: bool = False
    """L1-s: no revocation when the largest motor stroke is at or above the lift guard stroke
    minus ``l1_stroke_margin_m`` (682.8 - 40 = 642.8 mm); the watch ends with
    ``FIX_LOC_REVOKE_SKIPPED:stroke`` (record only). A revocation keeps the P-S8-31 margin
    already applied (no second application at the next LOC)."""
    l1_stroke_margin_m: float = 0.040
    l2_soil_gate: bool = False
    """L2-g: the confirmation window holds a flat window only in a run whose soil mode ran
    (``c_min(t_P)`` alone is noise on hard ground, V-3 sensor G1)."""
    l4_probe_reuse: bool = False
    """L4: a leg confirmed by an earlier probe round of the run (grounded, not skipped) keeps
    that result and is not probed again (``FIX_PROBE_REUSE``)."""
    # spec 424.4.1 Q-C (a leg losing its load while the LWa-delayed LOC waits)
    d1_fall_hold: bool = False
    """D1: before the LOC (soil mode or not), a leg of the four (a re-approaching one included)
    whose lower load is below ``d_level_fraction_F_min`` F_min and fell >= ``d_drop_N`` since the
    last period stops the lift of the other legs (``FIX_FALL_HOLD``) until it reads
    ``d_release_fraction_F_min`` F_min, a re-approach of it makes contact, or ``d_max_s``."""
    d2_fall_slow: bool = False
    """D2: as D1 but the other legs slow to a mean of ``d2_slow_fraction`` v_max (the P30fz slow
    lift, ``FIX_FALL_SLOW``)."""
    d3_repeat_reapproach_slow: bool = False
    """D3: the second and later pre-LOC re-approach of the same leg runs at
    ``d3_reapproach_factor`` instead of the P-S8-30 x 4, and the other legs slow as D2 while it
    runs (``FIX_REAPPROACH_SLOW``)."""
    d1p_over_p30fz: bool = False
    """D1p (spec 424.9 decision 2, token ``D1p`` = D1 + this): in a period the P30fz slowdown
    runs, a D1 watch whose leg still fell >= ``d_drop_N`` since the last period and reads below
    ``d1p_level_fraction_F_min`` F_min stops the other legs anyway
    (``FIX_FALL_HOLD_OVER_P30FZ``). Once it acted it holds for the rest of that watch (release
    and time limit as D1)."""
    d1p_level_fraction_F_min: float = 2.0
    d1p_needs_running_p30fz: bool = True
    """D1p: count the fall only in a period the P30fz slowdown already ran into (its pause leg
    set at the period start), i.e. the leg kept falling under the slowdown. False: also the
    period P30fz starts in (token ``D1p0``, comparison only)."""
    d1r_predicted_hold: bool = False
    """D1r (spec 424.9.2, token ``D1r``): before the final LOC, a leg of the four (a
    re-approaching one included) whose C2 R-5 prediction (horizon 4 periods) is below F_min +
    ``d1r_trigger_margin_N`` and whose lower load reads below ``d_level_fraction_F_min`` F_min
    stops the lift of the other legs in that period, also over a P30fz slowdown
    (``FIX_DIAG_HOLD_PRED``), until the prediction reads F_min + ``d1r_release_margin_N``, a
    re-approach of it makes contact, or ``d_max_s``."""
    d1r_trigger_margin_N: float = 5000.0
    d1r_release_margin_N: float = 10000.0
    d1q_hold: bool = False
    """D1q family (spec 424.9.3, tokens ``D1q`` / ``D1qa`` / ``D1qb`` / ``D2q``): in the period
    the P30fz gate starts a slowdown, its leg is checked against the gates switched on below;
    if they pass, the other legs stop (``d1q_slow``: slow) over P30fz
    (``FIX_DIAG_HOLD_Q:<leg>:<a|b|ab>``) until the leg reads ``d_release_fraction_F_min``
    F_min, a re-approach of it makes contact, ``d1q_hold_max_s`` or the run total
    ``d1q_hold_total_s``."""
    d1q_gate_a: bool = True
    """G-a "deep fall": lower load - ``d1q_horizon_periods`` x (fall since the last period) <
    F_min + ``d1q_trigger_margin_N``."""
    d1q_gate_b: bool = True
    """G-b "one soft pad": |stroke twist of the rod-stroke change since the first pre-LOC LEVEL
    period, stroke-plane part removed| > ``d1q_twist_m``."""
    d1q_slow: bool = False
    """D2q: slow the other legs to ``d2_slow_fraction`` v_max instead of stopping them."""
    d1q_horizon_periods: int = 4
    d1q_trigger_margin_N: float = 5000.0
    d1q_twist_m: float = 0.015
    """ASSUMPTION (spec 424.9.3, compared at 10 / 15 / 20 mm)."""
    d1q_hold_max_s: float = 1.5
    d1q_hold_total_s: float = 3.0
    """Stop time per run (the G6-2 delay bound)."""
    d_level_fraction_F_min: float = 3.0
    d_release_fraction_F_min: float = 3.5
    d_drop_N: float = 1000.0
    d_max_s: float = 3.0
    d2_slow_fraction: float = 0.16
    d3_reapproach_factor: float = 2.0
    # spec 424.8.2 (operating weight +20 %: the soil-mode push runs out before the LOC)
    s5_push_extend: bool = False
    """S5: when the soil-mode push reaches its limit (``max_push_m``, 150 mm) and the load sum
    rose by >= ``s5_progress_frac`` W_ref over the last ``s5_eval_m`` of push, and the longest
    leg + ``s5_step_m`` stays ``s5_stroke_margin_m`` below the lift guard stroke, the limit grows
    by ``s5_step_m`` (``FIX_PUSH_EXTEND:<limit mm>``), up to a push limit of
    ``s5_max_total_m``."""
    s5_eval_m: float = 0.050
    s5_progress_frac: float = 0.02
    s5_step_m: float = 0.050
    s5_stroke_margin_m: float = 0.030
    s5_max_total_m: float = 0.300
    """Largest push limit (ASSUMPTION: "총 300 mm" read as the limit itself, not 150 + 300)."""
    s6_saturation_loc: bool = False
    """S6: before the LOC, on a run with the soil sign (window-start c_min above
    ``s6_min_clearance_m`` or soil mode used), the S-1 rise r_k of the current 10 mm window and
    r_(k-1) of the window that ended 10 mm earlier with r_k <= ``s6_ratio`` r_(k-1) and
    r_k <= ``s6_rise_max_N`` (saturating load sum) confirm the LOC (``FIX_S6_LOC``); the 0.85
    W_ref plausibility stays. Only together with L1."""
    s6_ratio: float = 0.3
    s6_rise_max_N: float = 4000.0
    s6_min_clearance_m: float = 0.010

    def __post_init__(self) -> None:
        if self.s4_stroke_basis not in ("max", "mean"):
            raise ValueError(f"s4_stroke_basis must be max or mean, got {self.s4_stroke_basis!r}")
        if not 0.0 < self.e2_drop_fraction < 1.0:
            raise ValueError(f"e2_drop_fraction must be in (0, 1), got {self.e2_drop_fraction}")
        if self.e3_margin_m < 0.0 or self.e1_max_mismatch_m <= 0.0:
            raise ValueError("e3_margin_m must be >= 0 and e1_max_mismatch_m > 0")
        if self.lw_restart and self.lw_exclude:
            raise ValueError("LWa and LWb are alternatives (418), not a combination")
        if self.d1_fall_hold and self.d2_fall_slow:
            raise ValueError("D1 and D2 are alternatives (424.4), not a combination")
        if self.d_release_fraction_F_min < self.d_level_fraction_F_min:
            raise ValueError("d_release_fraction_F_min must be >= d_level_fraction_F_min")
        if (self.l1_soil_gate or self.l1_stroke_guard) and not self.l1_revoke:
            raise ValueError("L1-g / L1-s gate L1: they need l1_revoke (tokens L1g / L1gs)")
        if self.l2_soil_gate and not self.l2_confirm_window:
            raise ValueError("L2-g gates L2: it needs l2_confirm_window (token L2g)")
        if self.s6_saturation_loc and not self.l1_revoke:
            raise ValueError("S6 runs only together with L1 (424.8.2: L1 is its safety net)")
        if self.d1p_over_p30fz and not self.d1_fall_hold:
            raise ValueError("D1p overlays the D1 stop: it needs d1_fall_hold (token D1p)")
        if self.d1r_predicted_hold and (self.d1_fall_hold or self.d2_fall_slow):
            raise ValueError("D1r and D1 / D2 are alternatives (424.9.2), not a combination")
        if self.d1r_release_margin_N < self.d1r_trigger_margin_N:
            raise ValueError("d1r_release_margin_N must be >= d1r_trigger_margin_N")
        self._check_quick_hold()

    def _check_quick_hold(self) -> None:
        if self.d1q_slow and not self.d1q_hold:
            raise ValueError("d1q_slow is the D2q action: it needs d1q_hold (token D2q)")
        if not self.d1q_hold:
            return
        if self.d1_fall_hold or self.d2_fall_slow or self.d1r_predicted_hold:
            raise ValueError("D1q and D1 / D2 / D1p / D1p0 / D1r are alternatives (424.9.3), "
                             "not a combination")
        if not (self.d1q_gate_a or self.d1q_gate_b):
            raise ValueError("D1q needs at least one of the gates G-a / G-b")
        if self.d1q_hold_max_s <= 0.0 or self.d1q_hold_total_s <= 0.0:
            raise ValueError("d1q_hold_max_s and d1q_hold_total_s must be > 0")
        if self.d1q_twist_m <= 0.0 or self.d1q_horizon_periods < 1:
            raise ValueError("d1q_twist_m must be > 0 and d1q_horizon_periods >= 1")

    @property
    def has_qc_token(self) -> bool:
        """Any of the spec 424.4.1 / 424.9.2 / 424.9.3 tokens D1 / D2 / D3 / D1r / D1q is on."""
        return (self.d1_fall_hold or self.d2_fall_slow or self.d3_repeat_reapproach_slow
                or self.d1r_predicted_hold or self.d1q_hold)

    @property
    def quick_hold_reason(self) -> str:
        """Gates a D1q start needs: "a", "b" or "ab"."""
        return ("a" if self.d1q_gate_a else "") + ("b" if self.d1q_gate_b else "")


TOKEN_FLAGS = {"E1": "e1", "E2": "e2", "E3": "e3", "E4": "e4", "RA": "reanchor_soil_skip",
               "S4": "s4_stroke_limit", "LWa": "lw_restart", "LWb": "lw_exclude",
               "L1": "l1_revoke", "L2": "l2_confirm_window", "L4": "l4_probe_reuse",
               "D1": "d1_fall_hold", "D2": "d2_fall_slow", "D3": "d3_repeat_reapproach_slow",
               "S5": "s5_push_extend", "S6": "s6_saturation_loc", "D1r": "d1r_predicted_hold"}
TOKEN_PRESETS = {
    "E3w": {"e3": True, "e3_require_soil_use": False},
    "E3c7": {"e3": True, "e3_require_soil_use": False, "e3_min_clearance_at_P_m": 0.007},
    "E3c10": {"e3": True, "e3_require_soil_use": False, "e3_min_clearance_at_P_m": 0.010},
    "D1p": {"d1_fall_hold": True, "d1p_over_p30fz": True},
    "D1p0": {"d1_fall_hold": True, "d1p_over_p30fz": True, "d1p_needs_running_p30fz": False},
    "L1g": {"l1_revoke": True, "l1_soil_gate": True},
    "L1gs": {"l1_revoke": True, "l1_soil_gate": True, "l1_stroke_guard": True},
    "L2g": {"l2_confirm_window": True, "l2_soil_gate": True},
    "D1q": {"d1q_hold": True, "d1q_gate_a": True, "d1q_gate_b": True},
    "D1qa": {"d1q_hold": True, "d1q_gate_a": True, "d1q_gate_b": False},
    "D1qb": {"d1q_hold": True, "d1q_gate_a": False, "d1q_gate_b": True},
    "D2q": {"d1q_hold": True, "d1q_gate_a": True, "d1q_gate_b": True, "d1q_slow": True},
}
"""Composite variants. E3 (spec 417, 2026-10-29): E3w = E3wide (the adopted candidate of 404.1),
E3c7 / E3c10 = E3wide only with the soil sign c_min(t_P) above 7 / 10 mm. D1p (spec 424.9):
D1 that also stops over a P30fz slowdown. The preset values win over ``--param`` overrides of
the same field."""


def parse_candidate(name: str, overrides: dict | None = None) -> CandidateSettings:
    """Settings of a candidate name ("current" or tokens joined by "+") with parameter overrides.

    A ``name=value`` token is an override carried in the name (e.g. ``D1q+d1q_twist_m=0.010``);
    it wins over ``overrides``, the token flags and presets win over both.

    Raises:
        ValueError: unknown token or override name, or two spec 424.9.3 variants in one name.
    """
    flags: dict = {}
    overrides = dict(overrides or {})
    if name != BASELINE:
        quick_tokens = [token for token in name.split("+") if token in QUICK_HOLD_TOKENS]
        if len(quick_tokens) > 1:
            raise ValueError(f"{quick_tokens} are alternatives (424.9.3), not a combination")
        for token in name.split("+"):
            if "=" in token:
                overrides.update(parse_param_overrides([token]))
                continue
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


def falling_leg_below(loads_N, previous_loads_N, level_N: float, drop_N: float) -> int | None:
    """424.4.1 D1 / D2: the lowest leg among those that fell by >= ``drop_N`` since the previous
    period, if it reads below ``level_N``; else None (the P30fz rule with the D thresholds)."""
    loads = np.asarray(loads_N, float)
    has_fallen = np.asarray(previous_loads_N, float) - loads >= drop_N
    candidate_loads_N = np.where(has_fallen, loads, np.inf)
    if not float(np.min(candidate_loads_N)) < level_N:
        return None
    return int(np.argmin(candidate_loads_N))


def slow_lift(leg_speeds_m_s, mean_speed_m_s: float) -> np.ndarray:
    """P30fz slow lift on a leg subset: a command whose mean is above ``mean_speed_m_s`` loses
    its common positive heave and is raised back to that mean; a slower one stays."""
    speeds = np.asarray(leg_speeds_m_s, float)
    if float(np.mean(speeds)) <= mean_speed_m_s:
        return speeds
    without_heave = speeds - max(0.0, float(np.min(speeds)))
    return without_heave + max(0.0, mean_speed_m_s - float(np.mean(without_heave)))


def extrapolated_lower_N(lower_N: float, previous_lower_N: float, horizon_periods: int) -> float:
    """424.9.3 G-a: the measured lower load carried ``horizon_periods`` ahead on its fall
    since the previous sample (raw slope, no R-5 estimator lag)."""
    fall_per_period_N = previous_lower_N - lower_N
    return lower_N - horizon_periods * fall_per_period_N


def stroke_twist_residual_m(pad_xy_m, stroke_change_m) -> float:
    """424.9.3 G-b: stroke twist ``(s_FL - s_FR) - (s_RL - s_RR)`` of a stroke change whose
    stroke-plane part (least-squares ``a + b x + c y`` over the pads, i.e. heave and the
    attitude change) is removed; 0 for a rigid-body move of the body on firm pads."""
    pad_xy = np.asarray(pad_xy_m, float)
    change = np.asarray(stroke_change_m, float)
    plane_basis = np.column_stack([np.ones(len(change)), pad_xy])
    plane_coefficients, *_ = np.linalg.lstsq(plane_basis, change, rcond=None)
    residual = change - plane_basis @ plane_coefficients
    return float(TWIST_SIGNS @ residual)


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
    l1_watch: dict | None = None
    """424.3 L1: {t_loc_s, stroke_loc_m, W_hat_N, loads: [(t, sum F)], count} after a LOC."""
    l1_revokes: int = 0
    l1_skips: int = 0
    """424.10.1 L1-s: revocations withheld by the stroke guard."""
    l2_pending: dict | None = None
    """424.3 L2: {tail, t_last_s} of a flat window waiting for its confirmation stroke."""
    l2_confirms: int = 0
    l2_rejects: int = 0
    l4_reused: list = field(default_factory=list)
    """424.3 L4: (round, leg) of every probe result reused from an earlier round."""
    fall_watch: dict | None = None
    """424.4.1 D1 / D2: {leg, t_start_s} of the falling leg the other legs are restrained for."""
    fall_prev_lower_N: object = None
    """Lower load estimates of the previous LEVEL period [N] (the per-sample fall)."""
    pre_loc_reapproach_counts: list = field(default_factory=lambda: [0] * len(LEG_NAMES))
    """424.4.1 D3: re-approach runs per leg started inside the pre-LOC window."""
    reapproach_runs_seen: int = 0
    """Length of the controller's ``reapproach_history`` already counted."""
    slow_reapproach_legs: set = field(default_factory=set)
    """424.4.1 D3: legs whose running re-approach is their second or later before the LOC."""
    diag_events: int = 0
    """Starts of D1 / D2 / D3 restraints (sum of the two counts below)."""
    fall_events: int = 0
    repeat_reapproach_events: int = 0
    restrain_periods: int = 0
    """Periods in which D1 / D2 / D3 changed the leg command."""
    yielded_periods: int = 0
    """Periods with a D restraint due while the P30fz slowdown ran (left to P30fz, 424.4.1)."""
    is_watched_leg_falling: bool = False
    """424.9 D1p: this period the watched leg fell >= ``d_drop_N`` and reads below 2 F_min."""
    p30fz_override_watch_s: float | None = None
    """424.9 D1p: ``t_start_s`` of the watch whose stop overrides the P30fz slowdown."""
    p30fz_overrides: int = 0
    """424.9 D1p: watches whose stop overrode a P30fz slowdown."""
    p30fz_override_periods: int = 0
    pred_watch: dict | None = None
    """424.9.2 D1r: {leg, t_start_s} of the leg whose R-5 prediction stops the other legs."""
    pred_hold_events: int = 0
    quick_watch: dict | None = None
    """424.9.3 D1q: {leg, t_start_s, reason} of the leg the other legs are held for."""
    quick_hold_events: int = 0
    quick_hold_total_s: float = 0.0
    """D1q stop (or D2q slow) time of the run so far [s]."""
    quick_stroke_ref_m: object = None
    """D1q G-b: rod strokes of the first pre-LOC LEVEL period [m] (the twist reference)."""
    quick_gate_checks: list = field(default_factory=list)
    """D1q: {t_s, leg, extrapolated kN, twist mm, gate a, gate b, started} per P30fz start."""
    push_trace: list = field(default_factory=list)
    """424.8.2 S5: (mean motor stroke m, load sum N) of every soil-mode period before the LOC."""
    push_extensions: list = field(default_factory=list)
    """424.8.2 S5: (t_s, new push limit m) of every extension."""
    s6_confirms: int = 0
    s1_rise_trace: list = field(default_factory=list)
    """424.8.2 record (every candidate): (t_s, mean stroke mm, S-1 rise kN, mean load kN,
    soil push mm) at each S-1 window end before the LOC."""


def _install_probe_reuse(probe_round, confirmed: dict, controller) -> None:
    """424.3 L4 on one ``ProbeRound``: a confirmed leg is not moved; its latest confirming result
    is kept (``FIX_PROBE_REUSE:<leg>``). The round's stroke-guard skip list is not touched, so
    C2 raises no ``probe_skipped`` warning for it."""
    first_move_sign = probe_round._first_move_sign
    skip_leg = probe_round._skip_leg

    def reusing_first_move_sign(reading):
        if probe_round.leg in confirmed:
            return None
        return first_move_sign(reading)

    def reusing_skip_leg(reading):
        leg = probe_round.leg
        if leg not in confirmed:
            skip_leg(reading)
            return
        probe_round.results.append(confirmed[leg])
        probe_round._stage_start_s = reading.t_s
        probe_round.leg += 1
        controller.fix.l4_reused.append((controller._state.probe_round_count, leg))
        controller._add_event(reading.t_s, f"{PROBE_REUSE_EVENT}:{LEG_NAMES[leg]}")

    probe_round._first_move_sign = reusing_first_move_sign
    probe_round._skip_leg = reusing_skip_leg


def _without_project_l1(config, settings: CandidateSettings):
    """``config`` with the 03_src P-S8-33 turned off where a token L1 / L1g / L1gs runs.

    Spec 424.10.2: the R8 preset carries L1gs since the 03_src implementation, so the
    candidate ``current`` is L1gs; a token L1* on top would act twice. The token keeps its own
    (bit-identical) rule and ``FIX_*`` events, the project rule steps aside. P-S8-34 (L2) has
    no 03_src form; the tokens L2 / L2g stay for re-running stored records.
    """
    if config is None or not settings.l1_revoke:
        return config
    if getattr(config, "loc_revoke", None) is None:
        return config
    return replace(config, loc_revoke=replace(config.loc_revoke, enable=False))



def make_candidate_class(c2, base_class, settings: CandidateSettings):
    """Subclass of the project C2 (``base_class``, the module's original class) with the passive
    record and the fixes of ``settings``; with every fix off the commands are the project's."""

    class CandidateC2(base_class):
        candidate = settings

        def __init__(self, geometry, config=None) -> None:
            super().__init__(geometry, _without_project_l1(config, settings))
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
            if settings.l1_revoke:
                self._l1_watch_step()
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
            if settings.l2_confirm_window and self._l2_defers(tail):
                return
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
            if settings.l1_revoke:
                self._start_l1_watch(t_s)

        # ------------------------------------------------------------ 424.3 L1 / L2
        def _start_l1_watch(self, t_s: float) -> None:
            soil = self._soil_state()
            if not soil.is_liftoff_confirmed or self.fix.l1_revokes >= settings.l1_max_revokes:
                return
            if settings.l1_soil_gate and not self._has_l1_soil_sign():
                return
            reading = self._state.last_reading
            self.fix.l1_watch = {
                "t_loc_s": float(t_s),
                "stroke_loc_m": float(np.mean(reading.motor_stroke_m)),
                "W_hat_N": float(soil.weight_estimate_N), "loads": [], "count": 0}

        def _l1_watch_step(self) -> None:
            """After each update: the 1 s mean load sum against W_hat (L1 revocation)."""
            watch = self.fix.l1_watch
            if watch is None:
                return
            reading = self._state.last_reading
            soil = self._soil_state()
            mean_stroke_m = float(np.mean(reading.motor_stroke_m))
            if (not soil.is_liftoff_confirmed or self._state.phase is not c2.C2Phase.LEVEL
                    or mean_stroke_m - watch["stroke_loc_m"] >= settings.l1_watch_m):
                self.fix.l1_watch = None  # the first DONE or 20 mm past the LOC ends the watch
                return
            t_s = float(reading.t_s)
            watch["loads"].append((t_s, float(np.sum(reading.cylinder_force_N))))
            recent = [load for t, load in watch["loads"]
                      if t > t_s - settings.l1_mean_s + TIME_MATCH_S]
            mean_load_N = float(np.mean(recent))
            limit_N = watch["W_hat_N"] + max(settings.l1_rise_N, settings.l1_rise_fraction_W
                                             * self._reference_weight_N())
            watch["count"] = watch["count"] + 1 if mean_load_N > limit_N else 0
            if watch["count"] < settings.l1_confirm_periods:
                return
            if settings.l1_stroke_guard and self._is_l1_stroke_guarded(reading):
                self.fix.l1_watch = None  # record only: the stroke budget keeps this LOC
                self.fix.l1_skips += 1
                self._add_event(t_s, f"{LOC_REVOKE_SKIPPED_EVENT}:stroke")
                return
            self._revoke_liftoff(t_s, mean_load_N - watch["W_hat_N"])

        def _has_l1_soil_sign(self) -> bool:
            """L1-g at the LOC: the soil mode ran, or the E3c10 sign (c_min(t_P), settle tilt)."""
            soil = self._soil_state()
            if soil.soil_mode_start_s is not None:
                return True
            c_min_tP = soil.clearance_at_plateau_start_m
            settle = self._settle_attitude_rad()
            if c_min_tP is None or settle is None:
                return False
            is_tilted = max(abs(settle[0]), abs(settle[1])) > settings.l1_gate_tilt_min_rad
            return c_min_tP > settings.l1_gate_min_clearance_at_P_m and is_tilted

        def _is_l1_stroke_guarded(self, reading) -> bool:
            """L1-s: the largest motor stroke is within ``l1_stroke_margin_m`` of the guard."""
            limit_m = self._lift_guard_stroke_m() - settings.l1_stroke_margin_m
            return float(np.max(reading.motor_stroke_m)) >= limit_m

        def _revoke_liftoff(self, t_s: float, rise_N: float) -> None:
            """Back to "lift-off not confirmed": a new S-1 window; the S-3 bias, E3c10 margin
            and W_hat are found again at the next LOC (soil mode re-entry by the S-2 rule)."""
            soil = self._soil_state()
            soil.is_liftoff_confirmed = False
            soil.is_soil_mode = False
            soil.soil_mode_start_stroke_m = None
            soil.window.clear()
            soil.corner_bias_m = np.zeros(len(c2.LEG_ORDER))
            soil.corner_bias_raw_m = None
            soil.is_loc_anchor_applied = False
            for name in ("liftoff_s", "plateau_start_s", "weight_estimate_N", "weight_ratio",
                         "clearance_at_plateau_start_m", "clearance_at_liftoff_m"):
                setattr(soil, name, None)
            state = self._state
            if not settings.l1_stroke_guard:  # L1-s keeps the first P-S8-31 application
                state.clearance_target_m = None
                state.slope_margin_applied_s = None
                state.slope_margin_settle_rad = None
            if settings.e3:
                self.config = self._base_config
                self.fix.e3_applied = False
            self.fix.l1_revokes += 1
            self.fix.l1_watch = None
            self._add_event(t_s, f"{LOC_REVOKE_EVENT}:{rise_N / 1e3:.1f}", is_warning=True)

        def _has_used_soil_mode(self) -> bool:
            """L2-g: the soil mode is on or ran in this lifting cycle."""
            soil = self._soil_state()
            return soil.is_soil_mode or soil.soil_mode_start_s is not None

        def _l2_defers(self, tail) -> bool:
            """L2: hold a flat window with the soil sign for its confirmation stroke."""
            if getattr(self, "_l2_releasing", False):
                return False
            if self.fix.l2_pending is not None:
                return True
            if settings.l2_soil_gate and not self._has_used_soil_mode():
                return False
            if float(tail[0].corner_clearance_m.min()) > settings.l2_min_clearance_at_P_m:
                self.fix.l2_pending = {"tail": list(tail), "t_last_s": float(tail[-1].t_s)}
                return True
            return False

        def _l2_check(self, reading) -> None:
            """L2: after ``l2_extra_m`` more mean stroke, confirm (rise <= l2_rise_N) or clear."""
            pending = self.fix.l2_pending
            if pending is None:
                return
            soil = self._soil_state()
            window = list(soil.window)
            index = next((i for i, sample in enumerate(window)
                          if abs(sample.t_s - pending["t_last_s"]) <= TIME_MATCH_S), None)
            if soil.is_liftoff_confirmed or index is None:
                self.fix.l2_pending = None  # confirmed meanwhile, or the window was cleared
                return
            extra = window[index:]
            if extra[-1].mean_motor_stroke_m - extra[0].mean_motor_stroke_m < settings.l2_extra_m:
                return
            strokes_m = np.array([sample.mean_motor_stroke_m for sample in extra])
            loads_N = np.array([sample.load_sum_N for sample in extra])
            if len(extra) >= 3:
                slope_N_m = float(np.polyfit(strokes_m - strokes_m.mean(), loads_N, 1)[0])
            else:
                slope_N_m = (loads_N[-1] - loads_N[0]) / max(strokes_m[-1] - strokes_m[0], 1e-9)
            rise_N = slope_N_m * settings.l2_extra_m
            self.fix.l2_pending = None
            if rise_N > settings.l2_rise_N:
                soil.window.clear()
                self.fix.l2_rejects += 1
                self._add_event(reading.t_s, f"{L2_REJECT_EVENT}:{rise_N / 1e3:.2f}")
                return
            tail = pending["tail"] + extra[1:]
            mean_load_N = float(np.mean([sample.load_sum_N for sample in tail]))
            self.fix.l2_confirms += 1
            self._add_event(reading.t_s, f"{L2_CONFIRM_EVENT}:{rise_N / 1e3:.2f}")
            self._l2_releasing = True
            try:
                self._confirm_liftoff(reading.t_s, tail, mean_load_N)
            finally:
                self._l2_releasing = False

        # ------------------------------------------------------------ 424.3 L4
        def _confirmed_probe_results(self) -> dict:
            """Leg -> latest result of a probe that confirmed it (grounded, not skipped)."""
            confirmed = {}
            for results in self._state.probe_history:
                for result in results:
                    if result.is_grounded and not result.is_skipped:
                        confirmed[result.leg_index] = result
            return confirmed

        def _probe_step(self, reading):
            state = self._state
            is_new_round = (state.probe_round is None and state.reground is None
                            and bool(state.probe_history))
            confirmed = self._confirmed_probe_results() if settings.l4_probe_reuse else {}
            if not (is_new_round and confirmed):
                return super()._probe_step(reading)
            original = c2.ProbeRound
            controller = self

            def reusing_round(*args, **kwargs):
                probe_round = original(*args, **kwargs)
                _install_probe_reuse(probe_round, confirmed, controller)
                return probe_round

            c2.ProbeRound = reusing_round
            try:
                return super()._probe_step(reading)
            finally:
                c2.ProbeRound = original

        # ------------------------------------------------------------ 424.4.1 D1 / D2 / D3
        # Order of one LEVEL period: c2 ``update`` starts / ends the re-approaches, then
        # ``_level_step`` (the watches below), ``_apply_reapproach_speeds`` (D3 factor) and
        # ``_apply_pre_loc_lift_pause`` (P30fz, then the D restraint).
        def _level_step(self, reading):
            if settings.has_qc_token:
                self._count_pre_loc_reapproaches(reading)
                if settings.d1_fall_hold or settings.d2_fall_slow:
                    self._update_fall_watch(reading)
                if settings.d1r_predicted_hold:
                    self._update_predicted_watch(reading)
            return super()._level_step(reading)

        # ------------------------------------------------------------ 424.9.2 D1r
        def _r5_predicted_lower_N(self) -> np.ndarray | None:
            """The C2 R-5 prediction ``L - r_hat h`` of every leg (``_leg_falling_below``
            arithmetic: same history, rate intervals, horizon and P-S8-22 fallback slope;
            without its rate / falling gates and without its events). None before the
            history is full or with R-5 off."""
            r5 = self.config.r8.fast_relevel
            history = self._state.load_estimate_history
            if r5 is None or len(history) < r5.rate_intervals + 1:
                return None
            drop_per_period = (history[0] - history[-1]) / r5.rate_intervals
            horizon = r5.horizon_periods
            if horizon is None:
                horizon = 1 + self.config.r8.output_delay_periods
            if r5.uses_fallback_slope:
                inputs = [self._pressures.r5_fallback_inputs(leg)
                          for leg in range(len(LEG_NAMES))]
                drop_per_period, _ = c2.fallback_slope_drops(
                    drop_per_period, inputs, r5, horizon, self.config.period_s, None)
            return np.asarray(history[-1] - drop_per_period * horizon, float)

        def _update_predicted_watch(self, reading) -> None:
            """D1r: end a running watch, or start one on the leg with the lowest R-5 prediction
            below F_min + 5 kN whose lower load reads below 3 F_min (a period that ends a
            watch does not start the next one)."""
            fix = self.fix
            if not self._is_in_pre_loc_window():
                fix.pred_watch = None
                return
            predicted_N = self._r5_predicted_lower_N()
            if predicted_N is None:
                return
            f_min_N = self.geometry.F_min_N
            if fix.pred_watch is not None:
                if self._has_predicted_watch_ended(fix.pred_watch, predicted_N, reading.t_s):
                    fix.pred_watch = None
                return
            lower_N = np.asarray(self._load_estimate_N(reading.cylinder_force_lower_N), float)
            is_at_risk = ((predicted_N < f_min_N + settings.d1r_trigger_margin_N)
                          & (lower_N < settings.d_level_fraction_F_min * f_min_N))
            if not is_at_risk.any():
                return
            leg = int(np.argmin(np.where(is_at_risk, predicted_N, np.inf)))
            fix.pred_watch = {"leg": leg, "t_start_s": float(reading.t_s)}
            fix.pred_hold_events += 1
            fix.diag_events += 1
            self._add_event(reading.t_s, f"{DIAG_HOLD_PRED_EVENT}:{LEG_NAMES[leg]}")

        def _has_predicted_watch_ended(self, watch: dict, predicted_N: np.ndarray,
                                       t_s: float) -> bool:
            leg, t_start_s = watch["leg"], watch["t_start_s"]
            release_N = self.geometry.F_min_N + settings.d1r_release_margin_N
            if predicted_N[leg] >= release_N:
                return True
            has_timed_out = t_s - t_start_s >= settings.d_max_s - TIME_MATCH_S
            return has_timed_out or self._has_reapproach_contact_since(leg, t_start_s)

        def _count_pre_loc_reapproaches(self, reading) -> None:
            """D3 bookkeeping: count the re-approaches started this period inside the pre-LOC
            window; a leg's second and later one joins ``slow_reapproach_legs``."""
            fix = self.fix
            history = self._state.reapproach_history
            new_runs = history[fix.reapproach_runs_seen:]
            fix.reapproach_runs_seen = len(history)
            if not self._is_in_pre_loc_window():
                fix.slow_reapproach_legs.clear()
                return
            fix.slow_reapproach_legs &= set(self._state.active_reapproaches)
            for run in new_runs:
                if abs(run.start_s - reading.t_s) > TIME_MATCH_S:
                    continue  # started outside LEVEL: not a pre-LOC re-approach
                fix.pre_loc_reapproach_counts[run.leg] += 1
                is_repeat = fix.pre_loc_reapproach_counts[run.leg] >= 2
                if settings.d3_repeat_reapproach_slow and is_repeat:
                    fix.slow_reapproach_legs.add(run.leg)
                    fix.repeat_reapproach_events += 1
                    fix.diag_events += 1
                    self._add_event(reading.t_s,
                                    f"{REPEAT_REAPPROACH_SLOW_EVENT}:{LEG_NAMES[run.leg]}")

        def _update_fall_watch(self, reading) -> None:
            """D1 / D2: end a running watch or start one on a falling leg (P30fz pattern: a
            period that ends a watch does not start the next one)."""
            fix = self.fix
            lower_N = np.array(self._load_estimate_N(reading.cylinder_force_lower_N), float)
            previous_N = fix.fall_prev_lower_N
            fix.fall_prev_lower_N = lower_N
            fix.is_watched_leg_falling = False
            if not self._is_in_pre_loc_window():
                fix.fall_watch = None
                return
            if fix.fall_watch is not None:
                if self._has_fall_watch_ended(fix.fall_watch, lower_N, reading.t_s):
                    fix.fall_watch = None
                else:
                    self._mark_watched_leg_fall(lower_N, previous_N)
                return
            if previous_N is None:
                return
            level_N = settings.d_level_fraction_F_min * self.geometry.F_min_N
            leg = falling_leg_below(lower_N, previous_N, level_N, settings.d_drop_N)
            if leg is None:
                return
            fix.fall_watch = {"leg": leg, "t_start_s": float(reading.t_s)}
            fix.fall_events += 1
            fix.diag_events += 1
            event = FALL_HOLD_EVENT if settings.d1_fall_hold else FALL_SLOW_EVENT
            self._add_event(reading.t_s, f"{event}:{LEG_NAMES[leg]}")
            self._mark_watched_leg_fall(lower_N, previous_N)

        def _mark_watched_leg_fall(self, lower_N: np.ndarray, previous_N) -> None:
            """D1p: the watched leg fell >= ``d_drop_N`` this period and reads below
            ``d1p_level_fraction_F_min`` F_min."""
            if not settings.d1p_over_p30fz or previous_N is None:
                return
            # "keeps falling while P30fz runs": the slowdown decided last period is still on
            if settings.d1p_needs_running_p30fz and not self._is_p30fz_slowing():
                return
            leg = self.fix.fall_watch["leg"]
            level_N = settings.d1p_level_fraction_F_min * self.geometry.F_min_N
            drop_N = float(previous_N[leg] - lower_N[leg])
            self.fix.is_watched_leg_falling = bool(drop_N >= settings.d_drop_N
                                                   and lower_N[leg] < level_N)

        def _is_p30fz_overridden(self, mode: str, t_s: float) -> bool:
            """D1p: the D1 stop also runs in a P30fz period once its watched leg kept falling
            below 2 F_min (latched for the rest of the watch). D1r (424.9.2): its predicted
            stop always runs over P30fz (the 0.16 v_max slowdown is what came too late), and so
            does a D1q / D2q hold (424.9.3, started in the P30fz start period)."""
            fix = self.fix
            if fix.pred_watch is not None or fix.quick_watch is not None:
                return True
            if not settings.d1p_over_p30fz or mode != "stop" or fix.fall_watch is None:
                return False
            watch_start_s = fix.fall_watch["t_start_s"]
            if fix.p30fz_override_watch_s == watch_start_s:
                return True
            if not fix.is_watched_leg_falling:
                return False
            fix.p30fz_override_watch_s = watch_start_s
            fix.p30fz_overrides += 1
            self._add_event(t_s, f"{FALL_HOLD_OVER_P30FZ_EVENT}:"
                                 f"{LEG_NAMES[fix.fall_watch['leg']]}")
            return True

        def _has_fall_watch_ended(self, watch: dict, lower_N: np.ndarray, t_s: float) -> bool:
            leg, t_start_s = watch["leg"], watch["t_start_s"]
            release_N = settings.d_release_fraction_F_min * self.geometry.F_min_N
            if lower_N[leg] >= release_N:
                return True
            has_timed_out = t_s - t_start_s >= settings.d_max_s - TIME_MATCH_S
            return has_timed_out or self._has_reapproach_contact_since(leg, t_start_s)

        def _has_reapproach_contact_since(self, leg: int, t_start_s: float) -> bool:
            return any(run.leg == leg and run.outcome == REAPPROACH_CONTACT_OUTCOME
                       and run.end_s is not None and run.end_s >= t_start_s - TIME_MATCH_S
                       for run in self._state.reapproach_history)

        # ------------------------------------------------------------ 424.9.3 D1q
        def _update_quick_watch(self, reading, previous_lower_N) -> None:
            """D1q: end a running hold, or check the gates in the period P30fz starts a
            slowdown and start a hold on its leg (a period that ends a hold starts none)."""
            fix = self.fix
            if not self._is_in_pre_loc_window():
                fix.quick_watch = None
                return
            if fix.quick_stroke_ref_m is None:
                fix.quick_stroke_ref_m = np.array(reading.rod_stroke_m, dtype=float)
            lower_N = np.asarray(self._load_estimate_N(reading.cylinder_force_lower_N), float)
            if fix.quick_watch is not None:
                if self._has_quick_watch_ended(fix.quick_watch, lower_N, reading.t_s):
                    fix.quick_watch = None
                else:
                    fix.quick_hold_total_s += self.config.period_s
                return
            if previous_lower_N is None or not self._has_p30fz_started(reading.t_s):
                return
            leg = self._state.pre_loc_pause_leg
            check = self._quick_gate_check(reading, leg, lower_N, previous_lower_N)
            has_budget = fix.quick_hold_total_s < settings.d1q_hold_total_s - TIME_MATCH_S
            is_gate_open = ((check["a"] or not settings.d1q_gate_a)
                            and (check["b"] or not settings.d1q_gate_b))
            check["started"] = is_gate_open and has_budget
            if len(fix.quick_gate_checks) < QUICK_GATE_CHECKS_MAX:
                fix.quick_gate_checks.append(check)
            if not check["started"]:
                return
            reason = settings.quick_hold_reason
            fix.quick_watch = {"leg": leg, "t_start_s": float(reading.t_s), "reason": reason}
            fix.quick_hold_events += 1
            fix.quick_hold_total_s += self.config.period_s
            fix.diag_events += 1
            self._add_event(reading.t_s, f"{DIAG_HOLD_QUICK_EVENT}:{LEG_NAMES[leg]}:{reason}")

        def _has_p30fz_started(self, t_s: float) -> bool:
            """P30fz started its slowdown in this period (the D1p0 moment)."""
            state = self._state
            return (state.pre_loc_pause_leg is not None
                    and state.pre_loc_pause_since_s is not None
                    and abs(state.pre_loc_pause_since_s - t_s) <= TIME_MATCH_S)

        def _quick_gate_check(self, reading, leg: int, lower_N: np.ndarray,
                              previous_lower_N) -> dict:
            """G-a and G-b of leg ``leg`` in this period (both always evaluated, for the
            record)."""
            f_min_N = self.geometry.F_min_N
            extrapolated_N = extrapolated_lower_N(float(lower_N[leg]),
                                                  float(previous_lower_N[leg]),
                                                  settings.d1q_horizon_periods)
            stroke_change_m = (np.asarray(reading.rod_stroke_m, float)
                               - self.fix.quick_stroke_ref_m)
            twist_m = stroke_twist_residual_m(self.geometry.pad_xy_m, stroke_change_m)
            return {"t_s": round(float(reading.t_s), 2), "leg": LEG_NAMES[leg],
                    "lower_kN": round(float(lower_N[leg]) / 1e3, 3),
                    "extrapolated_kN": round(extrapolated_N / 1e3, 3),
                    "twist_mm": round(twist_m * 1e3, 2),
                    "a": bool(extrapolated_N < f_min_N + settings.d1q_trigger_margin_N),
                    "b": bool(abs(twist_m) > settings.d1q_twist_m)}

        def _has_quick_watch_ended(self, watch: dict, lower_N: np.ndarray, t_s: float) -> bool:
            leg, t_start_s = watch["leg"], watch["t_start_s"]
            if lower_N[leg] >= settings.d_release_fraction_F_min * self.geometry.F_min_N:
                return True
            has_timed_out = t_s - t_start_s >= settings.d1q_hold_max_s - TIME_MATCH_S
            is_budget_spent = (self.fix.quick_hold_total_s
                               >= settings.d1q_hold_total_s - TIME_MATCH_S)
            return (has_timed_out or is_budget_spent
                    or self._has_reapproach_contact_since(leg, t_start_s))

        def _restraint_mode(self) -> str | None:
            """"stop" (D1, D1r, D1q), "slow" (D2, D3, D2q) or None for this period."""
            if self.fix.quick_watch is not None:
                return "slow" if settings.d1q_slow else "stop"
            if self.fix.pred_watch is not None:
                return "stop"
            if self.fix.fall_watch is not None:
                return "stop" if settings.d1_fall_hold else "slow"
            if self.fix.slow_reapproach_legs:
                return "slow"
            return None

        def _restrained_legs(self) -> list[int]:
            """The legs that lift for the body: not the watched leg and not a leg in a
            re-approach (that one seeks contact)."""
            exempt = set(self._state.active_reapproaches)
            for watch in (self.fix.fall_watch, self.fix.pred_watch, self.fix.quick_watch):
                if watch is not None:
                    exempt.add(watch["leg"])
            return [leg for leg in range(len(LEG_NAMES)) if leg not in exempt]

        def _is_p30fz_slowing(self) -> bool:
            return self._state.pre_loc_pause_leg is not None

        def _apply_pre_loc_lift_pause(self, reading, leg_speeds):
            previous_lower_N = self._state.pre_loc_prev_loads_N  # P30fz overwrites it below
            speeds = super()._apply_pre_loc_lift_pause(reading, leg_speeds)
            if settings.d1q_hold:
                self._update_quick_watch(reading, previous_lower_N)
            mode = self._restraint_mode()
            if mode is None or not self._is_in_pre_loc_window():
                return speeds
            if self._is_p30fz_slowing():  # 424.4.1: P30fz first, no overlay in its period ...
                if not self._is_p30fz_overridden(mode, reading.t_s):  # ... unless D1p (424.9)
                    self.fix.yielded_periods += 1
                    return speeds
                self.fix.p30fz_override_periods += 1
            legs = self._restrained_legs()
            if not legs:
                return speeds
            out = np.array(speeds, dtype=float)
            if mode == "stop":
                out[legs] = 0.0
            else:
                slow_m_s = settings.d2_slow_fraction * self.geometry.max_speed_m_s
                out[legs] = slow_lift(out[legs], slow_m_s)
            if not np.array_equal(out, speeds):
                self.fix.restrain_periods += 1
            return out

        def _reapproach_speed_factor(self, leg: int) -> float:
            """D3: x ``d3_reapproach_factor`` instead of the P30fz x 4 for a repeated pre-LOC
            re-approach. P30fz decides its slowdown later in the period, so a slowdown running
            from the previous period is what makes D3 yield here."""
            factor = super()._reapproach_speed_factor(leg)
            pause = self.config.pre_loc_lift_pause
            is_slow_run = (settings.d3_repeat_reapproach_slow
                           and leg in self.fix.slow_reapproach_legs)
            if not (is_slow_run and pause.enable and self._is_in_pre_loc_window()):
                return factor
            if self._is_p30fz_slowing():
                return factor
            return factor / pause.reapproach_speed_factor * settings.d3_reapproach_factor

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
            self._update_liftoff_window_lw(reading)
            if settings.l2_confirm_window:
                self._l2_check(reading)
            rise_row = self._record_s1_rise(reading)
            if settings.s6_saturation_loc and rise_row is not None:
                self._s6_check(reading)

        # ------------------------------------------------------------ 424.8.2 S5 / S6
        def _record_s1_rise(self, reading) -> tuple | None:
            """Passive ``s1_rise_trace`` row of a window that took this period's sample."""
            soil = self._soil_state()
            window = soil.window
            if soil.is_liftoff_confirmed or not window:
                return None
            if abs(window[-1].t_s - reading.t_s) > TIME_MATCH_S:
                return None
            tail = self._plateau_tail()
            if tail is None:
                return None
            mean_load_N = float(np.mean([sample.load_sum_N for sample in tail]))
            push_m = getattr(soil, "push_m", None) if soil.is_soil_mode else None
            row = (round(float(reading.t_s), 2), round(tail[-1].mean_motor_stroke_m * 1e3, 2),
                   round(self._plateau_rise_N(tail) / 1e3, 3), round(mean_load_N / 1e3, 2),
                   None if push_m is None else round(push_m * 1e3, 1))
            self.fix.s1_rise_trace.append(row)
            return row

        def _has_soil_sign(self, tail) -> bool:
            soil = self._soil_state()
            is_soil_mode_used = soil.is_soil_mode or soil.soil_mode_start_s is not None
            c_min_m = float(tail[0].corner_clearance_m.min())
            return is_soil_mode_used or c_min_m > settings.s6_min_clearance_m

        def _previous_window_rise_N(self, stroke_m: float, t_window_start_s: float) -> float | None:
            """S-1 rise of the window that ended one window length (10 mm) of stroke earlier,
            inside the same uninterrupted S-1 window (from ``t_window_start_s``)."""
            span_mm = self.config.soil.plateau_window_m * 1e3
            earlier = [row for row in self.fix.s1_rise_trace
                       if row[0] >= round(t_window_start_s, 2) - TIME_MATCH_S
                       and row[1] <= stroke_m * 1e3 - span_mm + 1e-6]
            return None if not earlier else earlier[-1][2] * 1e3

        def _s6_check(self, reading) -> None:
            """S6: a saturating load sum confirms the LOC (the plausibility clause stays)."""
            soil = self._soil_state()
            if soil.is_liftoff_confirmed or self.fix.l2_pending is not None:
                return
            tail = self._plateau_tail()
            if tail is None or not self._has_soil_sign(tail):
                return
            rise_N = self._plateau_rise_N(tail)
            previous_N = self._previous_window_rise_N(tail[-1].mean_motor_stroke_m,
                                                      soil.window[0].t_s)
            if previous_N is None or previous_N <= 0.0:
                return
            if rise_N > settings.s6_ratio * previous_N or rise_N > settings.s6_rise_max_N:
                return
            mean_load_N = float(np.mean([sample.load_sum_N for sample in tail]))
            plausible_N = self.config.soil.plausibility_fraction * self._reference_weight_N()
            if mean_load_N < plausible_N:
                return
            self.fix.s6_confirms += 1
            self._add_event(reading.t_s, f"{S6_LOC_EVENT}:{rise_N / 1e3:.1f}/"
                                         f"{previous_N / 1e3:.1f}")
            self._confirm_liftoff(reading.t_s, tail, mean_load_N)

        def _s5_extends_push(self, reading) -> None:
            """S5: before the S-4 limit check, grow the push limit on a push with progress."""
            soil = self._soil_state()
            if soil.is_liftoff_confirmed or not soil.is_soil_mode:
                return
            if soil.soil_mode_start_stroke_m is None:
                return
            strokes_m = np.asarray(reading.motor_stroke_m, float)
            mean_stroke_m = float(np.mean(strokes_m))
            load_sum_N = float(np.sum(reading.cylinder_force_N))
            self.fix.push_trace.append((mean_stroke_m, load_sum_N))
            limit_m = self.config.soil.max_push_m
            if mean_stroke_m - soil.soil_mode_start_stroke_m <= limit_m:
                return
            new_limit_m = limit_m + settings.s5_step_m
            if new_limit_m > settings.s5_max_total_m + TIME_MATCH_S:
                return
            if not self._has_push_progress(mean_stroke_m, load_sum_N):
                return
            guard_m = self._lift_guard_stroke_m() - settings.s5_stroke_margin_m
            if float(strokes_m.max()) + settings.s5_step_m > guard_m:
                return
            self.config = replace(self.config,
                                  soil=replace(self.config.soil, max_push_m=new_limit_m))
            self.fix.push_extensions.append((float(reading.t_s), new_limit_m))
            self._add_event(reading.t_s, f"{PUSH_EXTEND_EVENT}:{new_limit_m * 1e3:.0f}")

        def _has_push_progress(self, mean_stroke_m: float, load_sum_N: float) -> bool:
            """Load-sum rise over the last ``s5_eval_m`` of push >= the progress fraction."""
            earlier = [load for stroke, load in self.fix.push_trace
                       if stroke <= mean_stroke_m - settings.s5_eval_m + 1e-9]
            if not earlier:
                return False
            rise_N = load_sum_N - earlier[-1]
            return rise_N >= settings.s5_progress_frac * self._reference_weight_N()

        def _update_liftoff_window_lw(self, reading) -> None:
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
            if settings.s5_push_extend:
                self._s5_extends_push(reading)
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

    The LOCs judged are those not revoked (spec 424.8.1: after an L1 revocation the last
    confirmed LOC; without a revocation every LOC event, as before); a revoked LOC is kept in
    ``revoked_loc_crawler_kN`` as a record (only with a revocation).

    Args:
        log: (t_s, phase, crawler max N, controller sum F N) per control period.
        events: (t_s, name) controller events.
        weight_N: plant weight m g (None: false LOC not judged).
    """
    crawler_by_t = {round(t, 6): crawler for t, _, crawler, _ in log}

    def crawler_kN_at(times_s) -> list[float]:
        return [crawler_by_t.get(round(t_s, 6), math.nan) / 1e3 for t_s in times_s]

    timeline = late_loc_rule.loc_timeline(events)
    loc_crawler_kN = crawler_kN_at(late_loc_rule.judged_loc_times(events))
    limit_kN = None if weight_N is None else FALSE_LOC_WEIGHT_FRACTION * weight_N / 1e3
    false_locs = 0 if limit_kN is None else sum(1 for v in loc_crawler_kN if v >= limit_kN)
    revoked = {}
    if timeline["revoke_times_s"]:
        revoked = {"revoked_loc_crawler_kN": [round(v, 2) for v in
                                              crawler_kN_at(timeline["revoked_loc_s"])],
                   "t_loc_first_s": timeline["t_loc_first_s"],
                   "t_loc_final_s": timeline["t_loc_final_s"]}
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
            "ready_recontacts": recontacts, "ready_crawler_max_kN": round(ready_max_N / 1e3, 2),
            **revoked}


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


def _h6_cases() -> list[dict]:
    """Spec 422.3 H6 (32: J1 B / A, J2 B, G1, rigid x mass scale 1.0 / 1.1 / 1.2, flat), settle
    table hook_harness attached as in study 1; mass scale and F_s ride in the case dicts."""
    import s9_soil_slope as slope

    table = json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))[SETTLE_TABLE_KEY]
    cases = slope.attach_settle_table(slope.build_cases(("H6",)), table)
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


def _v3s_cases() -> list[dict]:
    """Spec 424.10 R-e: the V-3 sensor (72) and beta (16) cases of ``s9_runs`` (ids as in
    ``07_results/S9/v3/sensor.json`` / ``beta.json``), run with the project preset like p3b."""
    import s9_runs

    return [{**case, "trace": False} for case in s9_runs.sensor_cases() + s9_runs.beta_cases()]


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
    if suite == "h6":
        return [(case["id"], case) for case in _h6_cases()]
    if suite == "v3s":
        return [(case["id"], case) for case in _v3s_cases()]
    raise ValueError(f"unknown suite {suite!r}, expected {SUITES}")


def _p32_flag_names(row: dict) -> list[str]:
    """FLAGs of a P3-2 row: both 419.8 and 424.8.1 names when both hold (``flag_names``)."""
    if not row.get("flag"):
        return []
    return list(row.get("flag_names") or [row["flag_name"]])


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
        "flags": list(rows["P3-1"].get("flag_names") or []) + _p32_flag_names(rows["P3-2"]),
        "late_loc_reapproach": rows["P3-2"].get("late_loc_reapproach")}


def _g6_record(key: str) -> dict:
    with _argv_as_root():
        import r72_g6_screen as g6
    rec = g6.job(key)
    if "error" in rec:
        return {"error": rec["error"], "tb": rec.get("tb")}
    record = {"verdict": "pass" if rec["pass"] else "fail", "passed": rec["pass"],
              "failed_rows": [k for k, v in rec["gates"].items() if not v],
              "hash": rec.get("commands_sha256"), "t_ready_s": rec.get("t_ready_s"),
              "min_force_kN": rec.get("min_true_Fcyl_after_off_kN"),
              "att_end_deg": rec.get("att_end_deg"),
              "max_stroke_mm": rec.get("max_motor_stroke_mm"),
              "final_phase": rec.get("final_phase"), "rut_ready_mm": rec.get("rut_clear_ready_mm"),
              "warnings": rec.get("warnings", []),
              # spec 419.8: G6-2_late_loc_reapproach and its five conditions (r72 judge)
              "flags": rec.get("flags", []), "late_loc_reapproach": rec.get("late_loc_reapproach")}
    if "late_loc_revoked" in rec:  # spec 424.8.1 / 424.9: runs with a LOC revocation only
        record["late_loc_revoked"] = rec["late_loc_revoked"]
    return record


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


SUITE_RUNNERS = {"slope": _slope_record, "g6": _g6_record, "g8": _g8_record, "p3b": _p3b_record,
                 "h6": _slope_record, "v3s": _p3b_record}


def qc_record(fix: _FixState) -> dict:
    """Spec 424.4.1 D1 / D2 / D3 counters of one run (also the r79 ``candidate_record``)."""
    return {"diag_events": fix.diag_events, "fall_events": fix.fall_events,
            "repeat_reapproach_events": fix.repeat_reapproach_events,
            "restrain_periods": fix.restrain_periods, "yielded_periods": fix.yielded_periods,
            "pre_loc_reapproach_counts": list(fix.pre_loc_reapproach_counts),
            "p30fz_overrides": fix.p30fz_overrides,
            "p30fz_override_periods": fix.p30fz_override_periods,
            "pred_hold_events": fix.pred_hold_events,
            "quick_hold_events": fix.quick_hold_events,
            "quick_hold_total_s": round(fix.quick_hold_total_s, 3),
            "quick_gate_checks": list(fix.quick_gate_checks)}


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
                             or n.startswith(PROJECT_L1_EVENTS)
                             or n.startswith("reanchor_")][:30]
    metrics["e3_applied"] = controller.fix.e3_applied
    metrics["lw_clears"] = controller.fix.lw_clears
    # spec 424.3 / 424.4 candidates
    # token counts plus the 03_src P-S8-33 counts (spec 424.10.2; one of them is 0)
    state = controller._state
    metrics["l1_revokes"] = controller.fix.l1_revokes + len(getattr(state, "loc_revokes", ()))
    metrics["l2_confirms"] = controller.fix.l2_confirms
    metrics["l2_rejects"] = controller.fix.l2_rejects
    metrics["l1_skips"] = controller.fix.l1_skips + len(getattr(state, "loc_revoke_skips", ()))
    metrics["l4_reused"] = list(controller.fix.l4_reused)
    metrics.update(qc_record(controller.fix))
    # spec 424.8.2 S5 / S6 and the S-1 rise record (last rows: the ones before the LOC / FAULT)
    metrics["push_extensions"] = [(round(t, 2), round(limit * 1e3)) for t, limit
                                  in controller.fix.push_extensions]
    metrics["s6_confirms"] = controller.fix.s6_confirms
    metrics["s1_rise_trace"] = controller.fix.s1_rise_trace[-S1_RISE_TRACE_MAX:]
    push_m = getattr(soil, "push_m", None)  # last soil-mode push of the run (S-4 value)
    metrics["soil_push_mm"] = None if push_m is None else round(float(push_m) * 1e3, 1)
    t_loc_s = late_loc_rule.loc_timeline(events)["t_loc_final_s"]  # spec 424.8.1
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


def case_ground(suite: str, case_id: str) -> str | None:
    """Soil of a slope / h6 case id (``group|soil|pad|level|slope[...]``); None elsewhere."""
    if suite not in A3_SUITES:
        return None
    parts = case_id.split("|")
    return parts[1] if len(parts) > 1 else None


def has_candidate_acted(record: dict) -> bool:
    """A fix of the candidate fired in the run: a ``FIX_*`` / S4 stroke event or the E3 target.

    RA (REANCHOR skip) raises no fix event; its runs count as idle, so they meet the stricter
    hash rule.
    """
    metrics = record.get("metrics") or {}
    if metrics.get("e3_applied"):
        return True
    return any(name.startswith((FIX_EVENT_PREFIX, S4_STROKE_EVENT))
               and name.split(":", 1)[0] not in RECORD_ONLY_FIX_EVENTS
               for _, name in metrics.get("fix_events") or [])


def _failed_rows(record: dict) -> list[str]:
    rows = record.get("failed_rows") or []
    return rows.split(",") if isinstance(rows, str) else list(rows)


def _soft_ground_regressions(before: dict, after: dict) -> list[str]:
    """A-3 relaxation on J1 / J2 / S1 for a run the candidate acted in."""
    reasons = []
    if before.get("passed") and not after.get("passed"):
        reasons.append("pass -> fail")
    if A3_TIME_ROW in _failed_rows(after) and A3_TIME_ROW not in _failed_rows(before):
        reasons.append(f"new {A3_TIME_ROW} violation")
    ready_before_s, ready_after_s = before.get("t_ready_s"), after.get("t_ready_s")
    if ready_before_s is not None and ready_after_s is None:
        reasons.append("no READY")
    elif ready_before_s is not None and ready_after_s - ready_before_s > A3_READY_INCREASE_MAX_S:
        reasons.append(f"READY +{ready_after_s - ready_before_s:.1f} s")
    return reasons


def acceptance_a3(suite: str, case_id: str, before: dict, after: dict) -> dict | None:
    """Spec 424.6 A-3 (relaxed 2026-10-29) of one slope / h6 case; None outside its scope.

    Rigid / G1: the command hash equals "current". J1 / J2 / S1: an idle candidate keeps the
    hash; where a fix acted, no pass -> fail, no new P3-2 violation and READY at most 5 s later.
    """
    ground = case_ground(suite, case_id)
    if ground not in A3_HARD_GROUNDS + A3_SOFT_GROUNDS:
        return None
    is_hash_same = before.get("hash") is not None and before.get("hash") == after.get("hash")
    acted = has_candidate_acted(after)
    if ground in A3_HARD_GROUNDS or not acted:
        reasons = [] if is_hash_same else [
            "hash differs" if acted else "hash differs without a candidate event"]
    else:
        reasons = _soft_ground_regressions(before, after)
    return {"ground": ground, "acted": acted, "pass": not reasons, "reasons": reasons}


def compare_records(before: dict, after: dict) -> dict:
    """One case: candidate ``after`` against the baseline ``before``."""
    m_before, m_after = before.get("metrics", {}), after.get("metrics", {})
    a3 = acceptance_a3(after["suite"], after["id"], before, after)
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
        "acted": has_candidate_acted(after),
        "a3_pass": None if a3 is None else a3["pass"],
        "a3_reasons": "" if a3 is None else ";".join(a3["reasons"]),
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
                                         "ready_recontacts_after": 0, "acted": 0,
                                         "idle_hash_differs": 0, "a3_checked": 0,
                                         "a3_fail": 0})
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
    entry["acted"] += row["acted"]
    # spec 424.6 A-5: a run the candidate did not act in keeps the "current" hash
    entry["idle_hash_differs"] += not row["acted"] and not row["hash_same"]
    if row["a3_pass"] is not None:
        entry["a3_checked"] += 1
        entry["a3_fail"] += not row["a3_pass"]
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


# ------------------------------------------------------ spec 424.8.1 re-judgement (stored)
REJUDGED_ROWS = ("P3-1", "P3-2")
REJUDGEABLE_VERDICTS = ("pass", "fail")
"""Verdicts recomputed from the failed rows (stroke-limited ones need rows the record lacks)."""


def _stored_loc_events(metrics: dict) -> list[tuple[float, str]]:
    """LOC and revocation events of a stored record: a LOC at every window check that was not
    vetoed (the wrapper logs each ``_confirm_liftoff``, L2 releases included), the revocations
    from ``fix_events``."""
    locs = [(float(check["t_s"]), LOC_EVENT) for check in metrics.get("window_checks") or []
            if check.get("vetoed") is None]
    revokes = [(float(t), name) for t, name in metrics.get("fix_events") or []
               if name.split(":", 1)[0] in late_loc_rule.LOC_REVOKE_EVENTS]
    return sorted(locs + revokes)


def _reclassify_at_final_loc(recontact: dict, t_loc_s: float, t_ready_s: float | None) -> dict:
    """U-S9-G6d / Q-G classes of stored recontact events against t_LOC^fin."""
    run_s9 = late_loc_rule._run_s9()
    events = recontact["recontact_events"]
    weight_N = events["weight_N"]
    threshold_N = late_loc_rule.DEPARTURE_FRACTION_OF_W * weight_N
    classes = []
    for event in events["events"]:
        ends_before = event["t_end_s"] is not None and event["t_end_s"] <= t_loc_s + 1e-12
        is_transient = (ends_before
                        and event["duration_s"] <= run_s9.P31_TRANSIENT_MAX_S + 1e-12
                        and event["max_normal_N"] <= run_s9.P31_TRANSIENT_MAX_W * weight_N)
        if is_transient:
            classes.append(late_loc_rule.CLASS_TRANSIENT)
        elif late_loc_rule.is_threshold_chatter(event, t_loc_s, threshold_N, t_ready_s):
            classes.append(late_loc_rule.CLASS_CHATTER)
        else:
            classes.append(late_loc_rule.CLASS_STRICT)
    return {"classes": classes, "pass": late_loc_rule.CLASS_STRICT not in classes}


def _final_loc_reapproach(block: dict, t_off_s: float, t_loc_s: float) -> tuple[bool, float | None]:
    """Spec 419.8 condition 1 and t_re_end at t_LOC^fin from the stored re-approach intervals."""
    overlapping = [iv for iv in block.get("reapproach_intervals") or []
                   if iv["start_s"] <= t_loc_s + 1e-9
                   and (iv["end_s"] is None or iv["end_s"] >= t_off_s - 1e-9)]
    has_restart = any(iv["window_restarts_s"] for iv in overlapping)
    if not overlapping or any(iv["end_s"] is None for iv in overlapping):
        return has_restart, None
    return has_restart, max(iv["end_s"] for iv in overlapping)


def _rejudge_p32(record: dict, metrics: dict, timeline: dict, f_min_kN: float) -> dict:
    block = record.get("late_loc_reapproach") or {}
    t_off_s, t_loc_s = block.get("t_off_s"), timeline["t_loc_final_s"]
    if t_off_s is None or t_loc_s is None:
        return {"pass": False, "note": "no lift-off or no final LOC"}
    delay_s = t_loc_s - t_off_s
    if delay_s <= late_loc_rule.LOC_DELAY_MAX_S + 1e-9:
        return {"pass": True, "loc_delay_s": delay_s, "flag_names": []}
    judged = late_loc_rule.judged_loc_times(_stored_loc_events(metrics))
    loc_kN = dict(zip(judged, metrics.get("loc_crawler_kN") or [], strict=False))
    crawler_N = None if t_loc_s not in loc_kN else loc_kN[t_loc_s] * 1e3
    has_restart, t_re_end_s = _final_loc_reapproach(block, t_off_s, t_loc_s)
    has_fault = (record.get("final_phase") in FAULT_PHASES
                 or any(name.startswith("FAULT") for name in record.get("warnings") or []))
    revoked = late_loc_rule.late_loc_revoked(
        t_off_s=t_off_s, t_loc_final_s=t_loc_s, t_done_s=None,
        revoke_times_s=timeline["revoke_times_s"], crawler_loc_period_max_N=crawler_N,
        weight_N=(block.get("crawler_threshold_N") or 0.0) / late_loc_rule.DEPARTURE_FRACTION_OF_W,
        min_force_after_off_kN=record.get("min_force_kN"), f_min_kN=f_min_kN,
        has_fault=has_fault, reapproach_restart=has_restart, t_reapproach_end_s=t_re_end_s)
    flags = []
    if revoked["is_flag"] and has_restart:
        flags.append(late_loc_rule.P32_FLAG)
    if revoked["is_flag"]:
        flags.append(late_loc_rule.P32_REVOKED_FLAG)
    return {"pass": revoked["is_flag"], "loc_delay_s": delay_s, "flag_names": flags,
            "late_loc_revoked": revoked}


def rejudge_final_loc(record: dict, f_min_kN: float) -> dict:
    """Spec 424.8.1 on a stored candidate record (no re-run): P3-1 and P3-2 at t_LOC^fin.

    A record without a revocation is returned unchanged. Approximations of the stored inputs:
    the LOC times are the window-check times (0.01 s), condition 3 reads the controller-period
    crawler maximum of the LOC period, condition 5 is taken as true (after a revocation DONE
    waits for a new LOC), and the spec 419.8 FLAG at t_LOC^fin holds exactly when the 424.8.1
    FLAG holds with its condition 1 (same conditions 2 .. 5).
    """
    if "error" in record or "metrics" not in record:
        return record
    metrics = record["metrics"]
    timeline = late_loc_rule.loc_timeline(_stored_loc_events(metrics))
    if not timeline["revoke_times_s"] or timeline["t_loc_final_s"] is None:
        return record
    t_loc_s = timeline["t_loc_final_s"]
    recontact = metrics.get("crawler_recontact")
    p31 = None
    if recontact is not None:
        p31 = _reclassify_at_final_loc(recontact, t_loc_s, record.get("t_ready_s"))
        p31["pass"] = bool(p31["pass"] and record.get("crawler_N_max_after_ready") == 0.0
                           and record.get("t_ready_s") is not None)
    p32 = _rejudge_p32(record, metrics, timeline, f_min_kN)
    failed = [row for row in record.get("failed_rows") or [] if row not in REJUDGED_ROWS]
    if p31 is not None and not p31["pass"]:
        failed.append("P3-1")
    elif p31 is None and "P3-1" in (record.get("failed_rows") or []):
        failed.append("P3-1")  # no 1 ms record: the stored row stays
    if not p32["pass"]:
        failed.append("P3-2")
    failed = sorted(failed)
    verdict = record.get("verdict")
    if verdict in REJUDGEABLE_VERDICTS:
        verdict = "pass" if not failed else "fail"
    return {**record, "verdict": verdict, "passed": verdict in ("pass", "stroke_limited_pass"),
            "failed_rows": failed,
            "rejudge_finloc": {"verdict_stored": record.get("verdict"),
                               "failed_rows_stored": record.get("failed_rows"),
                               "t_loc_first_s": timeline["t_loc_first_s"],
                               "t_loc_final_s": t_loc_s,
                               "revoke_times_s": timeline["revoke_times_s"],
                               "P3-1": p31, "P3-2": p32,
                               "verdict_recomputed": record.get("verdict")
                               in REJUDGEABLE_VERDICTS}}


def _rejudge_file(in_path: Path, out_path: Path) -> None:
    from outrigger_sim.params import load_params

    f_min_kN = load_params().control.F_min_cylinder_N / 1e3
    stored = json.loads(in_path.read_text(encoding="utf-8"))
    records = [rejudge_final_loc(record, f_min_kN) for record in stored["records"]]
    pass_counts = {}
    for before, after in zip(stored["records"], records, strict=True):
        entry = pass_counts.setdefault(after["candidate"], {"stored": 0, "final_loc": 0,
                                                            "changed": []})
        entry["stored"] += bool(before.get("passed"))
        entry["final_loc"] += bool(after.get("passed"))
        if before.get("verdict") != after.get("verdict"):
            entry["changed"].append(f"{after['id']}: {before.get('verdict')} -> "
                                    f"{after.get('verdict')}")
    meta = {"rejudged_from": str(in_path), "rule": "spec 424.8.1 (t_LOC^fin), no re-run",
            "F_min_kN": f_min_kN, "pass_counts": pass_counts,
            "stored_meta": stored.get("meta")}
    write_outputs(out_path, records, meta)
    print(json.dumps(pass_counts, indent=1))


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
    rejudge = sub.add_parser("rejudge-finloc", help="spec 424.8.1 re-judgement of a run file")
    rejudge.add_argument("--out", type=Path, required=True)
    rejudge.add_argument("input", type=Path)
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
    if args.command == "rejudge-finloc":
        _rejudge_file(args.input, args.out)
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
