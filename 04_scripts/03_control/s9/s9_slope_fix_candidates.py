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
  P36c5 / P36c8 / P36u8  spec 427 (P-S8-36 candidate, 2026-10-30): a run whose lift stroke guard
      acted (latch ``reload_armed`` from the first ``WARN_LIFT_STROKE_LIMITED`` to the run end)
      watches the load-sum ratio in LEVEL after the LOC, DONE, PROBE and READY. The corrected
      ratio rho_c = sum(F_i - sigma_i F_s,i) / (W_hat - sum F_s,i) (F_s,i: TOUCH free-air reading
      minus the rod weight, cut at the P-S8-26 cap; sigma_i: sign of the output in force, the last
      moving direction while a leg stands) or the plain rho_u = sum F_i / W_hat ("u"), 1 s mean
      (PROBE motion periods and 0.5 s after them left out), below 1 - delta on 2 periods ->
      ``WARN_CRAWLER_RELOAD:<mean>``; then with the largest motor stroke <= s_g - 40 mm and no
      re-lift yet the LOC is undone and the body re-levelled (E2 path,
      ``INFO_LOC_REVOKED_RELOAD:<mean>``), otherwise ``FAULT_LIFT_STROKE_LIMIT:reload`` (the
      guard FAULT handling). c = corrected, u = plain; 5 / 8 = delta 0.05 / 0.08
      (``p36_delta=`` overrides the token value). Every candidate records the arming time and
      the per-phase ratio minima after it (``metrics["p36"]``, no command change).
  P36s  spec 427.9 / 427.10 (P-S8-36 SGS, soil guard stop; user decision 2026-10-30: stop in the
      first guard period): the soil sign is latched at every LOC (the L1gs gate of 424.10.2:
      the soil mode ran in the lifting cycle -> "soil_mode", or c_min(t_P) > 10 mm on a settle
      tilt > 1 deg -> "clearance_tilt"; a LOC revocation clears it, the next LOC judges again).
      With the sign on, the first lift stroke guard period in LEVEL (SHIFT_DOWN or HOLD_ALL)
      blocks DONE and ends in FAULT through the guard FAULT handling (attitude integrators of
      the period start, U-S8-79 re-ground of the lifted legs): ``WARN_LIFT_STROKE_LIMITED:<legs>``
      (c2, same period) then ``FAULT_LIFT_STROKE_LIMIT:soil:<legs>``. Every candidate records the
      sign, its history and the first guard period with the sign on (``metrics["p36s"]``); the
      judges class such a run ``stroke_limited_stop`` or fail (``soil_guard_stop_rule.py``).
  P36sa  spec 427.12.2 (나) (user decision 2026-10-30): P36s armed at every LOC of a
      soil-response run (sign ``any_loc`` where neither L1gs reason holds); clearing and stop as
      P36s. Alternative to P36s; its stop counts as the part "P36s" in ``acted_parts``.
  P37t  spec 428.5.2 (P-S8-37 R1' twist ledger, ``p37_floor_twist.py``): a re-approach after the
      LOC keeps the rod-stroke twist tau at its start; after its contact, with the attitude
      settled (``p37_settle_att_rad``, negative = ``done_attitude_rad``), ``|delta tau| >=
      p37_min_twist_m`` books ``d_leg += sign_leg delta tau`` (cut at ``p37_max_offset_m``,
      ``INFO_FLOOR_DROP_OFFSET:<leg>:<mm>``) and the clearance paths read ``c_k(x - d)``.
  R4c20 / R4c30  spec 428.5.2 R4: a LOC after the soil mode on a flat settle (tilt <= 1 deg, no
      P-S8-31 margin) raises the clearance target by ``r4_margin_m`` 0.02 / 0.03 m
      (``INFO_LOC_FLAT_SOIL_MARGIN:<mm>``). Alternatives.
  P38z / P38z25  spec 429.3 / 429.5 (P-S8-38 ZIC, ``p38_integral_clamp.py``): from the first LOC
      to the first READY, in LEVEL, an attitude integral pushing past the target is cut to
      ``p38_cap_fraction`` (0.5 / 0.25) x done_attitude_rad K_p / K_i
      (``INFO_ATT_INT_CLAMP:<axis>:<I>``). Alternatives.
  P38z1  spec 429.7 redesign: P38z (c 0.5) with ``p38_window`` "first_done": the window ends at
      the first DONE after the first LOC (the re-level after a probe excluded). Alternative to
      P38z / P38z25; its cut counts as the part "P38z" in ``acted_parts``.
  Combinations: any tokens joined by "+", e.g. ``P36s+P37t+R4c30+P38z``; the alternatives above
  (and P36c5 / P36c8 / P36u8, the 424.9.3 variants) raise ValueError when combined.

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
  x426b  spec 426.4 study B for spec 427: the 21 study-1 points x {F_s 0, F_s 8, auger middle,
         mass x 1.1} = 84 cases, made from ``s9_soil_slope.build_cases(("H1", "H3"))`` by
         replacing the SlopeCase fields ``fs_kN`` / ``level`` / ``mass_scale`` (settle table
         attached after the replacement, so a middle case gets its middle row)
  h9     spec 430.2 roll boundary refinement, 36 cases (``s9_soil_slope.py`` group H9, settle
         table attached as for slope; a slope without a table row runs uncorrected and is
         marked ``no_table_row``)
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
import hashlib
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
import p37_floor_twist  # noqa: E402  (spec 428.5.2 P-S8-37 layer)
import p38_integral_clamp  # noqa: E402  (spec 429.3 P-S8-38 layer)
import soil_guard_stop_rule  # noqa: E402  (spec 427.9 safe-stop class)
from late_loc_rule import crawler_recontact_record  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev80"
SETTLE_TABLE_PATH = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
SETTLE_TABLE_KEY = "hook_harness"
SETTLE_HOOK_ENV = "S9_SETTLE_HOOK"

BASELINE = "current"
CANDIDATE_TOKENS = ("E1", "E2", "E3", "E4", "RA", "S4", "E3w", "E3c7", "E3c10", "LWa", "LWb",
                    "L1", "L2", "L4", "D1", "D1p", "D1p0", "D1r", "D2", "D3", "S5", "S6",
                    "D1q", "D1qa", "D1qb", "D2q", "L1g", "L1gs", "L2g", "DS", "DS50",
                    "DSb", "DSb10", "DSb75", "P36c5", "P36c8", "P36u8", "P36s",
                    "P36sa", "P37t", "R4c20", "R4c30", "P38z", "P38z25", "P38z1")
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
DS_HOLD_EVENT = "FIX_DIFF_SINK_HOLD"
"""``FIX_DIFF_SINK_HOLD:<sinking legs>:<|r| mm/s>`` (spec 424.11; c2 ``INFO_DIFF_SINK_HOLD``)."""
DS_RELEASE_EVENT = "FIX_DIFF_SINK_RELEASE"
"""``FIX_DIFF_SINK_RELEASE:<settled|time|stroke|reversed|done>``."""
DS_SIGNAL_WINDOW_S = 1.0
"""Moving window of the stroke slope and of the gyro roll-rate mean."""
DS_SIGNAL_PERIODS = 10
"""Control periods (10 Hz) of ``DS_SIGNAL_WINDOW_S``."""
LEFT_LEGS = (0, 2)
RIGHT_LEGS = (1, 3)
"""FL, RL / FR, RR in LEG_ORDER; axis 0 = front (FL - FR), axis 1 = rear (RL - RR)."""
L2_REJECT_EVENT = "FIX_L2_REJECT"
L2_CONFIRM_EVENT = "FIX_L2_CONFIRM"
PROJECT_L1_EVENTS = ("INFO_LOC_REVOKED", "INFO_LOC_REVOKE_SKIPPED", "INFO_DIFF_SINK_HOLD",
                     "INFO_DIFF_SINK_RELEASE")
"""03_src P-S8-33 / P-S8-35 events (spec 424.10.2 / 424.11.2), kept in ``fix_events`` with the
tokens' ones."""
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
SUITES = ("slope", "g6", "g8", "p3b", "h6", "v3s", "x426b", "h9")

# spec 427 P-S8-36 candidate (crawler re-load after the lift stroke guard acted)
P36_RELOAD_WARNING_EVENT = "WARN_CRAWLER_RELOAD"
"""``WARN_CRAWLER_RELOAD:<1 s mean ratio>``: the re-load suspicion (427.2)."""
P36_RELIFT_EVENT = "INFO_LOC_REVOKED_RELOAD"
"""``INFO_LOC_REVOKED_RELOAD:<1 s mean ratio>``: LOC undone, the body lifted again (427.3)."""
P36_FAULT_EVENT = "FAULT_LIFT_STROKE_LIMIT:reload"
P36_EVENTS = (P36_RELOAD_WARNING_EVENT, P36_RELIFT_EVENT, P36_FAULT_EVENT)
P36_BRANCH_RELIFT = "relift"
P36_BRANCH_FAULT = "fault"
P36_COMPENSATED = "last_motion"
P36_UNCOMPENSATED = "none"
P36_MIN_VALID_PERIODS = 5
"""Periods the 1 s mean needs after the left-out ones (427.2)."""
P36_RELOAD_ACTIONS_MAX = 10
# spec 427.9 P-S8-36 SGS (soil guard stop)
P36S_STOP_EVENT = soil_guard_stop_rule.SOIL_STOP_EVENT
"""``FAULT_LIFT_STROKE_LIMIT:soil:<legs>``: the guard period the soil sign turns into a stop."""
P36S_SIGN_SOIL_MODE = "soil_mode"
P36S_SIGN_CLEARANCE_TILT = "clearance_tilt"
"""Soil-sign reasons: the soil mode ran / c_min(t_P) and the settle tilt above the gate."""
P36S_SIGN_ANY_LOC = "any_loc"
"""P36sa (spec 427.12.2 (나)): a LOC of a soil-response run without either reason above."""
X426B_POINTS = (
    "H1|G1|B|top|nose_down", "H1|G1|B|top|roll_pos", "H1|G1|B|top|edge_nd",
    *(f"H3|{soil}|B|top|{direction}@k{k}" for soil in ("J1", "J2", "S1")
      for direction in ("nose_down", "roll_pos", "edge_nd") for k in ("0.5", "0.75")),
)
"""Spec 426.4: the 21 study-1 points (ids of ``rev85/x426_B_m1p1.json`` without ``|m1.1``)."""
X426B_VARIANTS = (
    # (fs_kN, level, mass_scale): F_s 0, F_s 8, auger middle, operating weight x 1.1
    (0.0, "top", 1.0), (8.0, "top", 1.0), (4.0, "middle", 1.0), (4.0, "top", 1.1),
)
HARNESS_HASH_FILES = (
    Path("04_scripts/03_control/s9/s9_soil_slope.py"),
    Path("04_scripts/03_control/s8/r72_g6_screen.py"),
    Path("04_scripts/03_control/s9/s9_soil_closed_loop.py"),
    Path("04_scripts/03_control/s9/soil_guard_stop_rule.py"),  # spec 427.9 judge rule
)
"""Spec 427.6: the harnesses another task extends; their SHA-256 (LF) go into the run meta."""

VERDICT_STROKE_LIMITED_STOP = soil_guard_stop_rule.VERDICT_STROKE_LIMITED_STOP

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
A3_SUITES = ("slope", "h6", "x426b", "h9")
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
    # spec 424.11 P-S8-35 (2026-10-30): differential pad sinking after the LOC
    ds_enable: bool = False
    """DS: from the first LOC (with the L1-g soil sign at that LOC) to the first DONE, an axis
    differential sinking rate ``r_a = (s'_L - s'_R) - w_a phi'`` above ``ds_threshold_m_s``
    for ``ds_confirm_s`` holds the common lift of the other side (u <= 0) and pushes the
    sinking side at ``ds_push_fraction`` v_max (no DONE while held)."""
    ds_threshold_m_s: float = 0.003
    ds_confirm_s: float = 1.0
    ds_release_m_s: float = 0.001
    ds_release_s: float = 0.5
    ds_max_s: float = 10.0
    ds_push_fraction: float = 0.25
    ds_track_w_m: tuple = (2.648, 2.411)
    """Pad track width front / rear [m] (the roll lever of each axis)."""
    ds_mode: str = "floor"
    """"floor" (DS, DS50: the other side u <= 0, the sinking side at least ds_push_fraction
    v_max) or "add" (DSb, spec 424.11.1: only the sinking leg of each axis sinking the way of
    the hold gets ``min(ds_gain |r_a|, ds_add_cap_fraction v_max)`` added)."""
    ds_gain: float = 1.0
    """DSb gain k [(m/s) per (m/s) of r_a]."""
    ds_add_cap_fraction: float = 0.25
    ds_release_on_reverse: bool = False
    """DSb: release first when the holding axis's r passes the release level the other way."""
    ds_gate_max_settle_tilt_rad: float | None = None
    """Spec 424.11.2 (DSb75): the gate also needs the settle tilt ``max(|roll|, |pitch|)`` (the
    P-S8-31 / E3c10 settle attitude) at the first LOC to be at most this value; an unknown
    settle closes it. None = no tilt condition (DS, DS50, DSb, DSb10)."""
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
    # spec 427 P-S8-36 candidate (crawler re-load after the lift stroke guard acted)
    p36: bool = False
    """P36: after the latch ``reload_armed`` a 1 s mean load-sum ratio below 1 - ``p36_delta``
    on ``p36_confirm_periods`` periods re-lifts (LOC undone) or FAULTs (427.2, 427.3)."""
    p36_delta: float = 0.05
    p36_compensation: str = P36_COMPENSATED
    """"last_motion": the corrected ratio rho_c (seal friction by the last moving direction);
    "none": the plain ratio rho_u = sum F / W_hat."""
    p36_mean_s: float = 1.0
    p36_confirm_periods: int = 2
    p36_probe_settle_s: float = 0.5
    """Left out of the mean after a PROBE period with any output in force (427.2)."""
    p36_relift_margin_m: float = 0.040
    """Re-lift only with the largest motor stroke <= lift guard stroke - this (642.8 mm)."""
    p36_max_relifts: int = 1
    # spec 427.9 P-S8-36 SGS
    p36s: bool = False
    """P36s: with the soil sign of the LOC, the first lift stroke guard period in LEVEL is a stop
    (``FAULT_LIFT_STROKE_LIMIT:soil:<legs>``) instead of a stroke-limited completion."""
    p36s_all_loc: bool = False
    """P36sa (spec 427.12.2 (나), user decision 2026-10-30): with the soil response on, every
    confirmed LOC latches the sign (reason ``any_loc`` where neither L1gs sign holds); the
    clearing (revocation, no LOC) and the stop are those of P36s."""
    # spec 428.5.2 P-S8-37 (``p37_floor_twist.py``)
    p37: bool = False
    """P37t: R1' twist ledger."""
    p37_min_twist_m: float = 0.005
    p37_max_offset_m: float = 0.06
    p37_settle_att_rad: float = -1.0
    """Settled attitude of the ledger; negative = the config ``done_attitude_rad``."""
    r4_margin_m: float = 0.0
    """R4c20 / R4c30: flat-soil LOC clearance margin; 0 = off."""
    # spec 429.3 P-S8-38 ZIC (``p38_integral_clamp.py``)
    p38: bool = False
    p38_cap_fraction: float = 0.5
    p38_window: str = p38_integral_clamp.WINDOW_FIRST_READY
    """ZIC window end: "first_ready" (P38z, P38z25) or "first_done" (P38z1, spec 429.7)."""

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
        if not 0.0 < self.ds_release_m_s < self.ds_threshold_m_s:
            raise ValueError("DS needs 0 < ds_release_m_s < ds_threshold_m_s")
        if self.ds_mode not in ("floor", "add"):
            raise ValueError(f"ds_mode must be floor or add, got {self.ds_mode!r}")
        if self.ds_gain <= 0.0 or self.ds_add_cap_fraction <= 0.0:
            raise ValueError("DSb needs ds_gain > 0 and ds_add_cap_fraction > 0")
        if min(self.ds_confirm_s, self.ds_release_s, self.ds_max_s, self.ds_push_fraction) <= 0:
            raise ValueError("DS times and ds_push_fraction must be > 0")
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
        self._check_p36()
        self.floor_twist_settings()  # P37t / R4c value checks
        self.integral_clamp_settings()

    def floor_twist_settings(self) -> p37_floor_twist.FloorTwistSettings:
        """The P-S8-37 layer settings of these fields."""
        settle_rad = None if self.p37_settle_att_rad < 0.0 else self.p37_settle_att_rad
        return p37_floor_twist.FloorTwistSettings(
            enable=self.p37, min_twist_m=self.p37_min_twist_m,
            max_offset_m=self.p37_max_offset_m, settle_attitude_rad=settle_rad,
            flat_soil_margin_m=self.r4_margin_m)

    def integral_clamp_settings(self) -> p38_integral_clamp.IntegralClampSettings:
        """The P-S8-38 layer settings of these fields."""
        return p38_integral_clamp.IntegralClampSettings(enable=self.p38,
                                                        cap_fraction=self.p38_cap_fraction,
                                                        window=self.p38_window)

    def _check_p36(self) -> None:
        if self.p36_compensation not in (P36_COMPENSATED, P36_UNCOMPENSATED):
            raise ValueError(f"p36_compensation must be {P36_COMPENSATED} or "
                             f"{P36_UNCOMPENSATED}, got {self.p36_compensation!r}")
        if not 0.0 < self.p36_delta < 1.0:
            raise ValueError(f"p36_delta must be in (0, 1), got {self.p36_delta}")
        if self.p36_mean_s <= 0.0 or self.p36_probe_settle_s < 0.0:
            raise ValueError("p36_mean_s must be > 0 and p36_probe_settle_s >= 0")
        if self.p36_confirm_periods < 1 or self.p36_max_relifts < 0:
            raise ValueError("p36_confirm_periods must be >= 1 and p36_max_relifts >= 0")

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
               "S5": "s5_push_extend", "S6": "s6_saturation_loc", "D1r": "d1r_predicted_hold",
               "P36s": "p36s", "P37t": "p37"}
TOKEN_PRESETS = {
    "P36sa": {"p36s": True, "p36s_all_loc": True},
    "E3w": {"e3": True, "e3_require_soil_use": False},
    "E3c7": {"e3": True, "e3_require_soil_use": False, "e3_min_clearance_at_P_m": 0.007},
    "E3c10": {"e3": True, "e3_require_soil_use": False, "e3_min_clearance_at_P_m": 0.010},
    "D1p": {"d1_fall_hold": True, "d1p_over_p30fz": True},
    "D1p0": {"d1_fall_hold": True, "d1p_over_p30fz": True, "d1p_needs_running_p30fz": False},
    "L1g": {"l1_revoke": True, "l1_soil_gate": True},
    "L1gs": {"l1_revoke": True, "l1_soil_gate": True, "l1_stroke_guard": True},
    "L2g": {"l2_confirm_window": True, "l2_soil_gate": True},
    "DS": {"ds_enable": True},
    "DS50": {"ds_enable": True, "ds_push_fraction": 0.5},
    "DSb": {"ds_enable": True, "ds_mode": "add", "ds_gain": 1.5, "ds_add_cap_fraction": 0.5,
            "ds_release_on_reverse": True},
    "DSb75": {"ds_enable": True, "ds_mode": "add", "ds_gain": 1.5, "ds_add_cap_fraction": 0.75,
              "ds_release_on_reverse": True, "ds_gate_max_settle_tilt_rad": math.radians(1.0)},
    "DSb10": {"ds_enable": True, "ds_mode": "add", "ds_gain": 1.0, "ds_add_cap_fraction": 0.25,
              "ds_release_on_reverse": True},
    "D1q": {"d1q_hold": True, "d1q_gate_a": True, "d1q_gate_b": True},
    "D1qa": {"d1q_hold": True, "d1q_gate_a": True, "d1q_gate_b": False},
    "D1qb": {"d1q_hold": True, "d1q_gate_a": False, "d1q_gate_b": True},
    "D2q": {"d1q_hold": True, "d1q_gate_a": True, "d1q_gate_b": True, "d1q_slow": True},
}
"""Composite variants. E3 (spec 417, 2026-10-29): E3w = E3wide (the adopted candidate of 404.1),
E3c7 / E3c10 = E3wide only with the soil sign c_min(t_P) above 7 / 10 mm. D1p (spec 424.9):
D1 that also stops over a P30fz slowdown. The preset values win over ``--param`` overrides of
the same field."""
TOKEN_DEFAULT_PRESETS = {
    "P36c5": ({"p36": True}, {"p36_delta": 0.05, "p36_compensation": P36_COMPENSATED}),
    "P36c8": ({"p36": True}, {"p36_delta": 0.08, "p36_compensation": P36_COMPENSATED}),
    "P36u8": ({"p36": True}, {"p36_delta": 0.08, "p36_compensation": P36_UNCOMPENSATED}),
    "R4c20": ({}, {"r4_margin_m": 0.020}),
    "R4c30": ({}, {"r4_margin_m": 0.030}),
    "P38z": ({"p38": True}, {"p38_cap_fraction": 0.5}),
    "P38z25": ({"p38": True}, {"p38_cap_fraction": 0.25}),
    "P38z1": ({"p38": True, "p38_window": p38_integral_clamp.WINDOW_FIRST_DONE},
              {"p38_cap_fraction": 0.5}),
}
"""Spec 427.5 / 428.5.2 / 429.5 tokens: (fixed fields, token values). Unlike ``TOKEN_PRESETS``
the token values give way to overrides (``P36c5+p36_delta=0.06``, ``P38z+p38_cap_fraction=0.4``,
``--param ...``)."""
ALTERNATIVE_TOKEN_GROUPS = (
    (("P36c5", "P36c8", "P36u8"), "427.5"),
    (("P36s", "P36sa"), "427.12.2"),
    (("R4c20", "R4c30"), "428.5.2"),
    (("P38z", "P38z25", "P38z1"), "429.5 / 429.7"),
)
"""Tokens of one group set the same fields: at most one per candidate (spec section)."""


def parse_candidate(name: str, overrides: dict | None = None) -> CandidateSettings:
    """Settings of a candidate name ("current" or tokens joined by "+") with parameter overrides.

    A ``name=value`` token is an override carried in the name (e.g. ``D1q+d1q_twist_m=0.010``);
    it wins over ``overrides``, the token flags and presets win over both. The token values of
    ``TOKEN_DEFAULT_PRESETS`` (spec 427 ``p36_delta`` ...) give way to both kinds of override.

    Raises:
        ValueError: unknown token or override name, two spec 424.9.3 variants or two spec 427
            tokens in one name.
    """
    flags: dict = {}
    token_values: dict = {}
    overrides = dict(overrides or {})
    if name != BASELINE:
        quick_tokens = [token for token in name.split("+") if token in QUICK_HOLD_TOKENS]
        if len(quick_tokens) > 1:
            raise ValueError(f"{quick_tokens} are alternatives (424.9.3), not a combination")
        for group, section in ALTERNATIVE_TOKEN_GROUPS:
            chosen = [token for token in name.split("+") if token in group]
            if len(chosen) > 1:
                raise ValueError(f"{chosen} are alternatives ({section}), not a combination")
        for token in name.split("+"):
            if "=" in token:
                overrides.update(parse_param_overrides([token]))
                continue
            if token in TOKEN_PRESETS:
                flags.update(TOKEN_PRESETS[token])
                continue
            if token in TOKEN_DEFAULT_PRESETS:
                fixed, values = TOKEN_DEFAULT_PRESETS[token]
                flags.update(fixed)
                token_values.update(values)
                continue
            if token not in TOKEN_FLAGS:
                raise ValueError(f"unknown candidate token {token!r}, expected {CANDIDATE_TOKENS}")
            flags[TOKEN_FLAGS[token]] = True
    known = {f.name for f in fields(CandidateSettings)}
    unknown = sorted(set(overrides or {}) - known)
    if unknown:
        raise ValueError(f"unknown parameters {unknown}")
    return CandidateSettings(**{**token_values, **(overrides or {}), **flags})


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


def seal_friction_estimates_N(free_air_N, rod_weight_N, cap_excess_N) -> np.ndarray:
    """Spec 427.2 F_s,i: TOUCH free-air reading minus the rod weight, negative and unknown (NaN)
    legs read 0, cut at the P-S8-26 cap ``cap_excess_N`` (8 / 6.67 kN)."""
    free_air = np.asarray(free_air_N, float)
    friction = np.nan_to_num(free_air - np.asarray(rod_weight_N, float), nan=0.0)
    return np.clip(friction, 0.0, np.asarray(cap_excess_N, float))


def friction_signs(output_in_force_m_s, remembered_signs) -> np.ndarray:
    """Spec 427.2 sigma_i: sign of the output in force; a standing leg keeps the sign of its
    last moving direction (``remembered_signs``, +1 at the run start)."""
    output = np.asarray(output_in_force_m_s, float)
    return np.where(output != 0.0, np.sign(output), np.asarray(remembered_signs, float))


def load_sum_ratios(forces_N, signs, friction_N, weight_estimate_N: float
                    ) -> tuple[float | None, float]:
    """Spec 427.2 (rho_c, rho_u): ``sum(F - sigma F_s) / (W_hat - sum F_s)`` and
    ``sum F / W_hat``; rho_c None when the friction leaves no weight."""
    forces = np.asarray(forces_N, float)
    friction = np.asarray(friction_N, float)
    plain = float(np.sum(forces)) / weight_estimate_N
    corrected_weight_N = weight_estimate_N - float(np.sum(friction))
    if corrected_weight_N <= 0.0:
        return None, plain
    corrected = float(np.sum(forces - np.asarray(signs, float) * friction)) / corrected_weight_N
    return corrected, plain


class LoadRatioWindow:
    """Moving mean of (rho_c, rho_u) over ``mean_s`` (spec 427.2: left-out periods are never
    added; a mean needs ``min_periods`` samples)."""

    def __init__(self, mean_s: float, min_periods: int = P36_MIN_VALID_PERIODS) -> None:
        self.mean_s = mean_s
        self.min_periods = min_periods
        self._samples: deque = deque()

    def clear(self) -> None:
        self._samples.clear()

    def add(self, t_s: float, corrected: float | None, plain: float) -> None:
        self._samples.append((float(t_s), corrected, plain))
        while self._samples and self._samples[0][0] <= t_s - self.mean_s + TIME_MATCH_S:
            self._samples.popleft()

    def means(self) -> tuple[float | None, float | None]:
        """(mean rho_c, mean rho_u); None where fewer than ``min_periods`` samples."""
        if len(self._samples) < self.min_periods:
            return None, None
        corrected = [c for _, c, _ in self._samples if c is not None]
        plain_mean = float(np.mean([u for _, _, u in self._samples]))
        if len(corrected) < self.min_periods:
            return None, plain_mean
        return float(np.mean(corrected)), plain_mean


def plant_truth_row(t_s: float, plant) -> tuple:
    """HB-1 row: (t s, true deck roll deg, pad sinkage mm per leg) of the harness plant; roll /
    sinkage ``None`` where the plant has no attitude / no soil (``h6_trace.py`` quantities)."""
    if plant is None or not hasattr(plant, "attitude"):
        return float(t_s), None, None
    roll_deg = math.degrees(plant.attitude()[0])
    soil = getattr(plant, "soil", None)
    sink = getattr(soil, "z", None)
    sink_mm = None if sink is None else [float(z) * 1e3 for z in np.asarray(sink, float)]
    return float(t_s), roll_deg, sink_mm


def first_done_after_s(phase_log, t_from_s: float) -> float | None:
    """Time of the first DONE period at or after ``t_from_s`` (``_FixState.log`` rows)."""
    for t_s, phase, *_ in phase_log:
        if t_s >= t_from_s - TIME_MATCH_S and phase == "done":
            return t_s
    return None


def hb1_metrics(fix, events, crawler_series, period_s: float) -> dict:
    """HB-1 (spec 424.11, record only): roll / side sinkage from the final LOC to the first
    DONE after it (run end without one), the DS record, and the crawler maximum after the
    final LOC."""
    t_loc_s = late_loc_rule.loc_timeline(events)["t_loc_final_s"]
    out = {"roll_abs_max_after_loc_deg": None, "side_sink_after_loc_mm": None,
           "ds_events": list(fix.ds_events), "ds_active_s": round(fix.ds_active_periods
                                                                   * period_s, 2),
           "recontact_after_final_loc_N_max": None}
    if t_loc_s is None:
        return out
    t_end_s = first_done_after_s(fix.log, t_loc_s)
    rows = [row for row in fix.truth_log if row[0] >= t_loc_s - TIME_MATCH_S
            and (t_end_s is None or row[0] <= t_end_s + TIME_MATCH_S)]
    rolls = [abs(roll) for _, roll, _ in rows if roll is not None]
    if rolls:
        out["roll_abs_max_after_loc_deg"] = round(max(rolls), 4)
    sinks = [sink for _, _, sink in rows if sink is not None]
    if len(sinks) >= 2:
        change_mm = np.asarray(sinks[-1]) - np.asarray(sinks[0])
        out["side_sink_after_loc_mm"] = [round(float(change_mm[list(LEFT_LEGS)].mean()), 2),
                                         round(float(change_mm[list(RIGHT_LEGS)].mean()), 2)]
    after = [force for t, force in crawler_series if t > t_loc_s]
    if after:
        out["recontact_after_final_loc_N_max"] = round(max(after), 1)
    return out


RUT_LOG_SUITES = ("slope", "h6", "x426b", "h9")
"""Suites run by ``s9_soil_slope``, whose per-period log carries ``rut_clear_mm``."""
RUT_AFTER_READY_S = 10.0
"""Spec 424.11.2 (1): the clearance window ends 10 s after READY."""


def _slope_harness_log() -> dict | None:
    """Per-period log of the last ``s9_soil_slope`` run in this worker (None if not loaded)."""
    slope = sys.modules.get("s9_soil_slope")
    return None if slope is None else slope._CAP.get("log")


def rut_clear_min_after_final_loc_mm(log, events, t_ready_s: float | None) -> float | None:
    """HB-1 (spec 424.11.2 (1), record only): least ``rut_clear_mm`` (crawler floor clearance,
    ``crawler_floor_clearance_mm``) from the final LOC to READY + 10 s (run end without READY)."""
    t_loc_s = late_loc_rule.loc_timeline(events)["t_loc_final_s"]
    if log is None or t_loc_s is None:
        return None
    t_end_s = None if t_ready_s is None else t_ready_s + RUT_AFTER_READY_S
    values = [clear_mm for t_s, clear_mm in zip(log["t_s"], log["rut_clear_mm"], strict=True)
              if clear_mm is not None and t_s >= t_loc_s - TIME_MATCH_S
              and (t_end_s is None or t_s <= t_end_s + TIME_MATCH_S)]
    return round(min(values), 2) if values else None


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
    # spec 424.11 P-S8-35 DS (differential sinking after the LOC)
    ds_strokes: deque = field(default_factory=lambda: deque(maxlen=DS_SIGNAL_PERIODS))
    """(t_s, motor strokes m) of the last 1 s of LEVEL periods."""
    ds_gyro_roll: deque = field(default_factory=deque)
    """Gyro roll rate samples [rad/s] of the last 1 s (maxlen set at the first update)."""
    ds_first_loc_s: float | None = None
    ds_gate_open: bool = False
    """The L1-g soil sign at the first LOC (the DS gate)."""
    ds_watch_over: bool = False
    """The first DONE ended the DS watch."""
    ds_above_periods: int = 0
    ds_below_periods: int = 0
    ds_active: dict | None = None
    """{t_start_s, axis, sinking legs, periods} of the running hold."""
    ds_active_periods: int = 0
    ds_events: list = field(default_factory=list)
    """Holds {t_s, axis, legs, r_mm_s} and releases {t_s, reason} (record)."""
    truth_log: list = field(default_factory=list)
    """HB-1 (every candidate, record): (t_s, true roll deg, pad sinkage mm per leg or None)."""
    # spec 427 P-S8-36 (the signal and record run for every candidate, only P36 acts)
    p36_armed_t_s: float | None = None
    """Latch ``reload_armed``: the first lift-guard period of the run (kept to the run end)."""
    p36_signs: np.ndarray = field(default_factory=lambda: np.ones(len(LEG_NAMES)))
    """sigma_i memory: sign of each leg's last non-zero output in force (+1 at the start)."""
    p36_window: LoadRatioWindow | None = None
    p36_weight_N: float | None = None
    """W_hat the window was filled with (a new LOC value clears it)."""
    p36_probe_motion_t_s: float | None = None
    """Last PROBE period with an output in force (427.2 left-out periods)."""
    p36_low_count: int = 0
    p36_relifts: int = 0
    p36_pending: dict | None = None
    """{t_s, ratio}: this period's confirmed suspicion, consumed by the phase step."""
    p36_minima: dict = field(default_factory=dict)
    """Phase -> {rho_c, rho_u, mean_c, mean_u} minima after the arming (record)."""
    p36_actions: list = field(default_factory=list)
    """{t_s, ratio, branch, max_stroke_mm} of every WARN_CRAWLER_RELOAD (P36 only)."""
    # spec 427.9 P-S8-36 SGS (the latch and record run for every candidate, only P36s acts)
    p36s_soil_sign: str | None = None
    """Soil-sign latch of the confirmed LOC (``P36S_SIGN_*``); None without a sign or a LOC."""
    p36s_sign_history: list = field(default_factory=list)
    """{t_s, sign} at every LOC and {t_s, sign: None, cleared: True} at every revocation."""
    p36s_guard_t_s: float | None = None
    """First lift stroke guard period with the soil sign on (the stop time P36s would use)."""
    p36s_due: dict | None = None
    """{t_s, legs, mode}: this period's guard period with the sign on (P36s, consumed by
    ``_level`` in the same period)."""
    p36s_stop: dict | None = None
    """{t_s, legs, mode, soil_sign, done_blocked} of the stop (P36s only)."""
    p36s_preempted: str | None = None
    """Phase that a stroke-end FAULT or the guard hold limit set in the stop period (that FAULT
    is kept, no soil stop event)."""


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


def _without_project_ds(config, settings: CandidateSettings):
    """``config`` with the 03_src P-S8-35 (``diff_sink``) off where a DS* token runs (the R8
    preset carries DSb75 since its 03_src form, spec 424.11.2; a token on top would act twice)."""
    if config is None or not settings.ds_enable:
        return config
    if getattr(config, "diff_sink", None) is None:
        return config
    return replace(config, diff_sink=replace(config.diff_sink, enable=False))



def make_candidate_class(c2, base_class, settings: CandidateSettings):
    """Subclass of the project C2 (``base_class``, the module's original class) with the passive
    record and the fixes of ``settings``; with every fix off the commands are the project's."""

    class CandidateC2(base_class):
        candidate = settings

        def __init__(self, geometry, config=None) -> None:
            super().__init__(geometry,
                             _without_project_ds(_without_project_l1(config, settings), settings))
            self._base_config = self.config
            self._new_fix_state()
            _RUNNING["controller"] = self

        def _new_fix_state(self) -> None:
            self.fix = _FixState()
            self.fix.p36_window = LoadRatioWindow(settings.p36_mean_s)
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
            if settings.ds_enable:
                self._ds_feed_gyro(measurements)
            command = super().update(measurements)
            self._record_period(measurements.t_s)
            self._p36s_clear_soil_sign_without_loc(measurements.t_s)
            if settings.l1_revoke:
                self._l1_watch_step()
            if settings.ds_enable:
                self._ds_after_update(measurements.t_s)
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
            self.fix.truth_log.append(plant_truth_row(t_s, _TRUTH.get("plant")))

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
            self._p36s_latch_soil_sign(t_s)
            if settings.e3:
                self._apply_e3_margin(t_s)
            if settings.l1_revoke:
                self._start_l1_watch(t_s)
            if settings.ds_enable:
                self._ds_note_loc(t_s)

        # ------------------------------------------------------------ 424.11 DS
        def _ds_note_loc(self, t_s: float) -> None:
            """The first LOC of the run opens the DS watch; its soil sign is the gate."""
            if self.fix.ds_first_loc_s is not None or not self._soil_state().is_liftoff_confirmed:
                return
            self.fix.ds_first_loc_s = float(t_s)
            self.fix.ds_gate_open = self._has_l1_soil_sign() and self._is_ds_settle_level()

        def _is_ds_settle_level(self) -> bool:
            """DSb75 gate part: settle tilt at most ``ds_gate_max_settle_tilt_rad`` (slopes are
            left to P-S8-31; DSb acted falsely there, spec 424.11.2)."""
            max_tilt_rad = settings.ds_gate_max_settle_tilt_rad
            if max_tilt_rad is None:
                return True
            settle = self._settle_attitude_rad()
            if settle is None:
                return False
            return max(abs(settle[0]), abs(settle[1])) <= max_tilt_rad

        def _ds_feed_gyro(self, measurements) -> None:
            samples = getattr(measurements, "imu_angular_rate_samples_rad_s", None)
            if samples is not None and len(samples):
                rolls = np.asarray(samples, float)[:, 0]
                sample_s = self._imu_sample_s
            else:
                rolls = np.asarray(measurements.angular_rate_rad_s, float)[:1]
                sample_s = self.config.period_s
            gyro = self.fix.ds_gyro_roll
            if gyro.maxlen is None:  # the first period fixes the 1 s length
                gyro = self.fix.ds_gyro_roll = deque(
                    maxlen=round(DS_SIGNAL_WINDOW_S / sample_s))
            gyro.extend(float(roll) for roll in rolls)

        def _ds_rates_m_s(self) -> np.ndarray | None:
            """``r_a`` (front, rear) [m/s]: 1 s least-squares stroke slope difference minus
            the roll the legs would cause, ``w_a`` times the 1 s mean gyro roll rate."""
            history = self.fix.ds_strokes
            if len(history) < DS_SIGNAL_PERIODS or not self.fix.ds_gyro_roll:
                return None
            times_s = np.array([t for t, _ in history])
            strokes_m = np.array([strokes for _, strokes in history])
            centred_t = times_s - times_s.mean()
            slopes_m_s = centred_t @ (strokes_m - strokes_m.mean(axis=0)) / (centred_t @ centred_t)
            roll_rate = float(np.mean(self.fix.ds_gyro_roll))
            front_w_m, rear_w_m = settings.ds_track_w_m
            return np.array([slopes_m_s[0] - slopes_m_s[1] - front_w_m * roll_rate,
                             slopes_m_s[2] - slopes_m_s[3] - rear_w_m * roll_rate])

        def _ds_stroke_limit_m(self) -> float:
            return self._lift_guard_stroke_m() - settings.l1_stroke_margin_m

        def _ds_update(self, reading) -> None:
            """One LEVEL period of the DS watch (before the command of the period)."""
            fix = self.fix
            fix.ds_strokes.append((float(reading.t_s), np.array(reading.motor_stroke_m, float)))
            if fix.ds_watch_over or fix.ds_first_loc_s is None or not fix.ds_gate_open:
                return
            rates = self._ds_rates_m_s()
            if rates is None:
                return
            magnitudes = np.abs(rates)
            is_stroke_limited = float(np.max(reading.motor_stroke_m)) >= self._ds_stroke_limit_m()
            if fix.ds_active is not None:
                self._ds_check_release(reading.t_s, rates, is_stroke_limited)
                return
            if is_stroke_limited:
                fix.ds_above_periods = 0
                return
            is_above = float(magnitudes.max()) > settings.ds_threshold_m_s
            fix.ds_above_periods = fix.ds_above_periods + 1 if is_above else 0
            if fix.ds_above_periods >= round(settings.ds_confirm_s / self.config.period_s):
                self._ds_hold(reading.t_s, rates)

        def _ds_hold(self, t_s: float, rates: np.ndarray) -> None:
            axis = int(np.argmax(np.abs(rates)))
            legs = LEFT_LEGS if rates[axis] > 0.0 else RIGHT_LEGS  # r > 0: the left side sinks
            r_mm_s = abs(float(rates[axis])) * 1e3
            names = ",".join(LEG_NAMES[leg] for leg in legs)
            self.fix.ds_active = {"t_start_s": float(t_s), "axis": axis, "legs": legs,
                                  "periods": 0, "sign": 1.0 if rates[axis] > 0 else -1.0}
            self.fix.ds_above_periods = 0
            self.fix.ds_below_periods = 0
            self.fix.ds_events.append({"t_s": round(float(t_s), 2), "axis": axis,
                                       "legs": names, "r_mm_s": round(r_mm_s, 2)})
            self._add_event(t_s, f"{DS_HOLD_EVENT}:{names}:{r_mm_s:.1f}")

        def _ds_check_release(self, t_s: float, rates: np.ndarray,
                              is_stroke_limited: bool) -> None:
            fix = self.fix
            active = fix.ds_active
            if settings.ds_release_on_reverse and self._is_ds_reversed(rates, active):
                self._ds_release(t_s, "reversed")  # DSb: checked before every other rule
                return
            magnitudes = np.abs(rates)
            fix.ds_active["periods"] += 1
            is_settled = bool(np.all(magnitudes < settings.ds_release_m_s))
            fix.ds_below_periods = fix.ds_below_periods + 1 if is_settled else 0
            period_s = self.config.period_s
            if fix.ds_below_periods >= round(settings.ds_release_s / period_s):
                self._ds_release(t_s, "settled")
            elif fix.ds_active["periods"] >= round(settings.ds_max_s / period_s):
                self._ds_release(t_s, "time")
            elif is_stroke_limited:
                self._ds_release(t_s, "stroke")

        def _ds_release(self, t_s: float, reason: str) -> None:
            self.fix.ds_active = None
            self.fix.ds_below_periods = 0
            self.fix.ds_events.append({"t_s": round(float(t_s), 2), "release": reason})
            self._add_event(t_s, f"{DS_RELEASE_EVENT}:{reason}")

        def _ds_after_update(self, t_s: float) -> None:
            """A hold ends when the phase leaves LEVEL; the first DONE ends the watch."""
            if self.fix.ds_active is not None:
                self.fix.ds_active_periods += 1
                if self._state.phase is not c2.C2Phase.LEVEL:
                    self._ds_release(t_s, "done")
            if self._state.phase is c2.C2Phase.DONE:
                self.fix.ds_watch_over = True

        def _is_ds_reversed(self, rates: np.ndarray, active: dict) -> bool:
            """DSb: the holding axis now sinks the other way by more than the release level."""
            return float(rates[active["axis"]]) * active["sign"] < -settings.ds_release_m_s

        def _ds_added_speeds(self, leg_speeds, active: dict) -> np.ndarray:
            """DSb: each axis sinking the way of the hold adds ``min(k |r_a|, c v_max)`` to its
            sinking leg; every other leg and the controller command stay as they are."""
            speeds = np.array(leg_speeds, float)
            rates = self._ds_rates_m_s()
            if rates is None:
                return speeds
            cap_m_s = settings.ds_add_cap_fraction * self.geometry.max_speed_m_s
            for axis, (left, right) in enumerate(zip(LEFT_LEGS, RIGHT_LEGS, strict=True)):
                rate = float(rates[axis])
                if rate * active["sign"] <= 0.0:
                    continue
                leg = left if rate > 0 else right
                speeds[leg] += min(settings.ds_gain * abs(rate), cap_m_s)
            return speeds

        def _apply_lift_stroke_guard(self, reading, leg_speeds):
            """DS changes the LEVEL command before the P-S8-28 guard (which keeps priority)."""
            active = self.fix.ds_active if settings.ds_enable else None
            if active is not None and settings.ds_mode == "add":
                leg_speeds = self._ds_added_speeds(leg_speeds, active)
            elif active is not None:
                leg_speeds = np.array(leg_speeds, float)
                sinking = list(active["legs"])
                other = [leg for leg in range(len(LEG_NAMES)) if leg not in sinking]
                push_m_s = settings.ds_push_fraction * self.geometry.max_speed_m_s
                leg_speeds[other] = np.minimum(leg_speeds[other], 0.0)
                leg_speeds[sinking] = np.maximum(leg_speeds[sinking], push_m_s)
            return super()._apply_lift_stroke_guard(reading, leg_speeds)

        def _update_completion(self, reading, filtered_clearance_m):
            is_complete = super()._update_completion(reading, filtered_clearance_m)
            if settings.ds_enable and self.fix.ds_active is not None:
                self._state.complete_since_s = None  # no DONE while DS holds
                return False
            return is_complete

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
            if settings.ds_enable and self._state.phase is c2.C2Phase.LEVEL:
                self._ds_update(reading)
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

        # ------------------------------------------------------------ 427 P-S8-36
        # One period: ``_phase_command`` observes the ratio first (every candidate, record);
        # a confirmed suspicion of P36 is acted on by ``_hold_probe_or_relevel`` (DONE /
        # PROBE / READY) or ``_level`` (LEVEL) in the same period.
        def _record_lift_guard_period(self, t_s, guarded, mode) -> None:
            super()._record_lift_guard_period(t_s, guarded, mode)
            if self.fix.p36_armed_t_s is None:
                self.fix.p36_armed_t_s = float(t_s)
            self._p36s_note_guard_period(t_s, guarded, mode)

        def _phase_command(self, reading):
            self._p36_observe(reading)
            try:
                return super()._phase_command(reading)
            finally:
                self.fix.p36_pending = None  # e.g. DONE started a REANCHOR instead
                self.fix.p36s_due = None

        def _level(self, reading):
            if self.fix.p36_pending is not None:
                fault_speeds = self._p36_act(reading)
                if fault_speeds is not None:
                    return fault_speeds
            state = self._state
            integrals_at_start = (state.roll_integral, state.pitch_integral)
            leg_speeds = super()._level(reading)
            if self.fix.p36s_due is None:
                return leg_speeds
            return self._p36s_stop(integrals_at_start, leg_speeds)

        # ------------------------------------------------------------ 427.9 P36s (SGS)
        def _p36s_soil_sign(self) -> str | None:
            """The soil sign at the LOC and its reason: the L1gs sign; under P36sa every LOC
            of a soil-response run (``any_loc`` where the L1gs sign does not hold)."""
            reason = self._p36s_l1gs_sign()
            if reason is None and settings.p36s_all_loc and self.config.soil.enable:
                return P36S_SIGN_ANY_LOC
            return reason

        def _p36s_l1gs_sign(self) -> str | None:
            """The L1gs soil sign at the LOC (424.10.2, the 03_src gate constants) and its
            reason; agrees with ``_has_loc_soil_sign``."""
            soil = self._soil_state()
            if soil.soil_mode_start_s is not None:
                return P36S_SIGN_SOIL_MODE
            c_min_at_P_m = soil.clearance_at_plateau_start_m
            settle_rad = self._settle_attitude_rad()
            if c_min_at_P_m is None or settle_rad is None:
                return None
            gate = getattr(self.config, "loc_revoke", None)
            min_clearance_m = (settings.l1_gate_min_clearance_at_P_m if gate is None
                               else gate.gate_min_clearance_at_P_m)
            min_tilt_rad = settings.l1_gate_tilt_min_rad if gate is None else gate.gate_tilt_min_rad
            is_tilted = max(abs(settle_rad[0]), abs(settle_rad[1])) > min_tilt_rad
            if c_min_at_P_m > min_clearance_m and is_tilted:
                return P36S_SIGN_CLEARANCE_TILT
            return None

        def _p36s_latch_soil_sign(self, t_s: float) -> None:
            """427.9: judged again at every confirmed LOC (a vetoed window leaves it alone)."""
            if not self._soil_state().is_liftoff_confirmed:
                return
            fix = self.fix
            fix.p36s_soil_sign = self._p36s_soil_sign()
            fix.p36s_sign_history.append({"t_s": round(float(t_s), 2),
                                          "sign": fix.p36s_soil_sign})

        def _p36s_clear_soil_sign_without_loc(self, t_s: float) -> None:
            """427.9: a LOC revocation clears the latch (the next LOC judges again). Checked
            after every update, so the 03_src P-S8-33 revocation, the L1* tokens and the E2 /
            P36 re-lifts are all covered without overriding a project method."""
            fix = self.fix
            if fix.p36s_soil_sign is None or self._soil_state().is_liftoff_confirmed:
                return
            fix.p36s_soil_sign = None
            fix.p36s_sign_history.append({"t_s": round(float(t_s), 2), "sign": None,
                                          "cleared": True})

        def _p36s_note_guard_period(self, t_s: float, guarded, mode) -> None:
            """A guard period with the soil sign: record its first time; under P36s the stop is
            due in this period (``_level`` acts after the period's LEVEL step)."""
            fix = self.fix
            if fix.p36s_soil_sign is None or fix.p36s_stop is not None:
                return
            if fix.p36s_guard_t_s is None:
                fix.p36s_guard_t_s = float(t_s)
            if settings.p36s and fix.p36s_due is None:
                legs = tuple(int(leg) for leg in np.flatnonzero(guarded))
                fix.p36s_due = {"t_s": float(t_s), "legs": legs, "mode": str(mode.name).lower()}

        def _p36s_stop(self, integrals_at_start: tuple, leg_speeds: np.ndarray) -> np.ndarray:
            """427.9: the guard FAULT handling in the first guard period; a stroke-end FAULT or
            the hold limit that the LEVEL step already raised in this period is kept."""
            fix, state = self.fix, self._state
            due, fix.p36s_due = fix.p36s_due, None
            if state.phase in (c2.C2Phase.FAULT, c2.C2Phase.FAULT_REGROUND):
                fix.p36s_preempted = str(state.phase.name).lower()
                return leg_speeds
            t_s = due["t_s"]
            legs = c2._leg_names(due["legs"])
            fix.p36s_stop = {"t_s": round(t_s, 2), "legs": legs, "mode": due["mode"],
                             "soil_sign": fix.p36s_soil_sign,
                             "done_blocked": state.phase is c2.C2Phase.DONE}
            state.roll_integral, state.pitch_integral = integrals_at_start
            state.complete_since_s = None
            self._add_event(t_s, f"{P36S_STOP_EVENT}:{legs}", is_warning=True)
            state.phase = c2.C2Phase.FAULT
            if self._starts_stroke_end_reground(t_s):  # as the guard FAULT (U-S8-79, R30)
                state.phase = c2.C2Phase.FAULT_REGROUND
            return self._zero_speeds()

        def _p36_watched_phase(self) -> str | None:
            """427.1: LEVEL after the LOC, DONE, PROBE, READY; None elsewhere."""
            phase = self._state.phase
            if phase is c2.C2Phase.LEVEL:
                return "level" if self._soil_state().is_liftoff_confirmed else None
            if phase in (c2.C2Phase.DONE, c2.C2Phase.PROBE, c2.C2Phase.READY):
                return str(phase.name).lower()
            return None

        def _p36_seal_friction_N(self) -> np.ndarray:
            cap_N = (self.config.r8.touch_free_air_cap_excess_N
                     or c2.R8_D1_TOUCH_FREE_AIR_CAP_EXCESS_N)
            free_air_N = self._state.free_air_force_N
            if free_air_N is None:
                return np.zeros(len(LEG_NAMES))
            return seal_friction_estimates_N(free_air_N, self._touch_rod_weight_N(), cap_N)

        def _p36_is_left_out(self, t_s: float, output_in_force) -> bool:
            """427.2: a PROBE period with any output in force and ``p36_probe_settle_s``
            after it."""
            fix = self.fix
            if self._state.phase is c2.C2Phase.PROBE and np.any(output_in_force != 0.0):
                fix.p36_probe_motion_t_s = float(t_s)
            last_motion_s = fix.p36_probe_motion_t_s
            return (last_motion_s is not None
                    and t_s - last_motion_s <= settings.p36_probe_settle_s + TIME_MATCH_S)

        def _p36_observe(self, reading) -> None:
            """The 427.2 signal of this period (before its command); sets ``p36_pending``."""
            fix = self.fix
            output_in_force = np.asarray(self._state.applied_output_m_s, float)
            signs = friction_signs(output_in_force, fix.p36_signs)
            fix.p36_signs = signs
            is_left_out = self._p36_is_left_out(reading.t_s, output_in_force)
            phase = self._p36_watched_phase()
            weight_N = self._soil_state().weight_estimate_N
            if fix.p36_armed_t_s is None or phase is None or not weight_N or is_left_out:
                fix.p36_low_count = 0
                return
            if weight_N != fix.p36_weight_N:
                fix.p36_window.clear()
                fix.p36_weight_N = weight_N
            corrected, plain = load_sum_ratios(reading.cylinder_force_N, signs,
                                               self._p36_seal_friction_N(), weight_N)
            fix.p36_window.add(reading.t_s, corrected, plain)
            mean_corrected, mean_plain = fix.p36_window.means()
            self._p36_note_minima(phase, (corrected, plain, mean_corrected, mean_plain))
            judged = mean_corrected if settings.p36_compensation == P36_COMPENSATED else mean_plain
            if not settings.p36 or judged is None:
                fix.p36_low_count = 0
                return
            fix.p36_low_count = fix.p36_low_count + 1 if judged < 1.0 - settings.p36_delta else 0
            if fix.p36_low_count >= settings.p36_confirm_periods:
                fix.p36_pending = {"t_s": float(reading.t_s), "ratio": judged}

        def _p36_note_minima(self, phase: str, values: tuple) -> None:
            minima = self.fix.p36_minima.setdefault(
                phase, {"rho_c": None, "rho_u": None, "mean_c": None, "mean_u": None})
            for key, value in zip(minima, values, strict=True):
                if value is not None and (minima[key] is None or value < minima[key]):
                    minima[key] = float(value)

        def _p36_act(self, reading) -> np.ndarray | None:
            """427.3: re-lift (LOC undone, back to LEVEL; returns None) or the FAULT (returns
            the zero command)."""
            fix = self.fix
            pending, fix.p36_pending = fix.p36_pending, None
            t_s, ratio = pending["t_s"], pending["ratio"]
            max_stroke_m = float(np.max(reading.motor_stroke_m))
            relift_limit_m = self._lift_guard_stroke_m() - settings.p36_relift_margin_m
            can_relift = (max_stroke_m <= relift_limit_m
                          and fix.p36_relifts < settings.p36_max_relifts)
            branch = P36_BRANCH_RELIFT if can_relift else P36_BRANCH_FAULT
            if len(fix.p36_actions) < P36_RELOAD_ACTIONS_MAX:
                fix.p36_actions.append({"t_s": round(t_s, 2), "ratio": round(ratio, 4),
                                        "branch": branch,
                                        "max_stroke_mm": round(max_stroke_m * 1e3, 1)})
            self._add_event(t_s, f"{P36_RELOAD_WARNING_EVENT}:{ratio:.3f}", is_warning=True)
            fix.p36_low_count = 0
            fix.p36_window.clear()
            if can_relift:
                fix.p36_relifts += 1
                self._clear_liftoff_confirmation()
                self._start_relevel()
                self._add_event(t_s, f"{P36_RELIFT_EVENT}:{ratio:.3f}", is_warning=True)
                return None
            self._add_event(t_s, P36_FAULT_EVENT, is_warning=True)
            state = self._state
            state.phase = c2.C2Phase.FAULT
            if self._starts_stroke_end_reground(t_s):  # as the guard FAULT (U-S8-79)
                state.phase = c2.C2Phase.FAULT_REGROUND
            return self._zero_speeds()

        # ------------------------------------------------------------ E2
        def _hold_probe_or_relevel(self, reading):
            if self.fix.p36_pending is not None:
                fault_speeds = self._p36_act(reading)
                return fault_speeds  # None after a re-lift: the LEVEL step of this period
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
            """E2 re-lift: the LOC undone (:meth:`_clear_liftoff_confirmation`), E2 counted."""
            self._clear_liftoff_confirmation()
            self.fix.e2_low_count = 0
            self.fix.e2_relifts += 1

        def _clear_liftoff_confirmation(self) -> None:
            """Back to "lift-off not confirmed": soil mode starts again at the next LEVEL period
            and DONE waits for a new S-1 window (the bias stays until the new LOC)."""
            soil = self._soil_state()
            soil.is_liftoff_confirmed = False
            soil.is_soil_mode = False
            soil.soil_mode_start_stroke_m = None
            soil.window.clear()

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
    # spec 428.5.2 / 429.3 layers on top; each factory returns its base when its tokens are off
    layered = p37_floor_twist.make_floor_twist_class(c2, CandidateC2,
                                                     settings.floor_twist_settings())
    return p38_integral_clamp.make_integral_clamp_class(c2, layered,
                                                        settings.integral_clamp_settings())


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
        _TRUTH["plant"] = plant  # HB-1 reads its attitude / soil at each control period
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
    _TRUTH.update(crawler_max_N=0.0, weight_N=None, crawler_series=[], plant=None)
    _RUNNING.pop("controller", None)
    return c2, settings


def install_screen_candidate(candidate: str | None):
    """Candidate class for a screen outside this wrapper (study A ``R426A_CANDIDATE``, r67
    ``R67_CANDIDATE``, as r79 ``R79_CANDIDATE``): swaps ``c2.C2Controller`` and returns a
    function that puts the original back. None / "" / "current": nothing is installed (the
    screen's stored path, bit for bit).

    Raises:
        ValueError: unknown token or parameter in ``candidate``.
    """
    if not candidate or candidate == BASELINE:
        return lambda: None
    c2, _ = _install_candidate(candidate, {})
    original = _RUNNING["original_class"]

    def restore() -> None:
        c2.C2Controller = original

    return restore


def screen_candidate_record(controller) -> dict | None:
    """Candidate record a screen stores per run: the spec 427.11 / 429.5 parts (P36s stop,
    P37t / R4c, P38z) of ``controller``; None for a project controller."""
    fix = getattr(controller, "fix", None)
    if fix is None:
        return None
    metrics = {"p36s": p36s_record(fix),
               "p37": p37_floor_twist.floor_twist_record(controller),
               "p38": p38_integral_clamp.integral_clamp_record(controller)}
    record = {"metrics": metrics}
    return {**metrics, "acted": has_candidate_acted(record), "acted_parts": acted_parts(record)}


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


def _x426b_cases() -> list[dict]:
    """Spec 426.4 study B (84): the 21 points of ``X426B_POINTS`` x ``X426B_VARIANTS``.

    Only the existing SlopeCase fields ``fs_kN`` / ``level`` / ``mass_scale`` are replaced (no
    dependence on the spec 426 extension of ``s9_soil_slope``); the settle table is attached
    after the replacement because its rows are keyed per level.

    Raises:
        ValueError: a point of ``X426B_POINTS`` is not among the study-1 cases.
    """
    import s9_soil_slope as slope

    points = [case for case in slope.build_cases(("H1", "H3")) if case.case_id in X426B_POINTS]
    if len(points) != len(X426B_POINTS):
        missing = sorted(set(X426B_POINTS) - {case.case_id for case in points})
        raise ValueError(f"x426b points not in study 1: {missing}")
    table = json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))[SETTLE_TABLE_KEY]
    variants = [replace(case, fs_kN=fs_kN, level=level, mass_scale=mass_scale)
                for fs_kN, level, mass_scale in X426B_VARIANTS for case in points]
    return [case.to_dict() for case in slope.attach_settle_table(variants, table)]


def _h9_cases() -> list[dict]:
    """Spec 430.2 H9 (36: J1 B / A, J2 B x roll_pos / roll_neg x 6 k), settle table hook_harness
    attached as in study 1 (missing rows run uncorrected, ``no_table_row``)."""
    import s9_soil_slope as slope

    table = json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))[SETTLE_TABLE_KEY]
    cases = slope.attach_settle_table(slope.build_cases((slope.H9_GROUP,)), table)
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
    if suite == "x426b":
        return [(case["id"], case) for case in _x426b_cases()]
    if suite == "h9":
        return [(case["id"], case) for case in _h9_cases()]
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
        "late_loc_reapproach": rows["P3-2"].get("late_loc_reapproach"),
        "soil_stop": rows["SL-1"].get("soil_stop"),  # spec 427.9 (None without the stop)
        "lifted_legs": list(rows["SL-1"]["lifted_legs"])}  # classify's SL-1 lift test (rejudge)


def _g6_record(key: str) -> dict:
    with _argv_as_root():
        import r72_g6_screen as g6
    rec = g6.job(key)
    if "error" in rec:
        return {"error": rec["error"], "tb": rec.get("tb")}
    # spec 427.9: r72 gives a soil-guard stop its own verdict (stroke_limited_stop or fail)
    verdict = rec.get("verdict") or ("pass" if rec["pass"] else "fail")
    record = {"verdict": verdict, "passed": rec["pass"], "soil_stop": rec.get("soil_stop"),
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
                 "h6": _slope_record, "v3s": _p3b_record, "x426b": _slope_record,
                 "h9": _slope_record}


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


def p36_record(fix: _FixState) -> dict:
    """Spec 427.6 record (every candidate): arming time, per-phase ratio minima after it and the
    P36 actions (time, 1 s mean ratio, branch)."""
    minima = {phase: {key: None if value is None else round(value, 4)
                      for key, value in values.items()}
              for phase, values in fix.p36_minima.items()}
    return {"armed_t_s": None if fix.p36_armed_t_s is None else round(fix.p36_armed_t_s, 2),
            "minima": minima, "relifts": fix.p36_relifts, "actions": list(fix.p36_actions)}


def p36s_record(fix: _FixState) -> dict:
    """Spec 427.10 record (every candidate): the soil-sign latch at the run end with its history,
    the first guard period with the sign on and, under P36s, the stop (time, legs, guard mode)."""
    return {"soil_sign": fix.p36s_soil_sign, "sign_history": list(fix.p36s_sign_history[:10]),
            "guard_t_s": None if fix.p36s_guard_t_s is None else round(fix.p36s_guard_t_s, 2),
            "stop": None if fix.p36s_stop is None else dict(fix.p36s_stop),
            "preempted": fix.p36s_preempted}


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
                             or n.startswith(PROJECT_L1_EVENTS) or n.startswith(P36_EVENTS)
                             or n.startswith(P36S_STOP_EVENT) or n.startswith("reanchor_")][:30]
    metrics["p36"] = p36_record(controller.fix)
    metrics["p36s"] = p36s_record(controller.fix)
    metrics["p37"] = p37_floor_twist.floor_twist_record(controller)  # None without P37t / R4c
    metrics["p38"] = p38_integral_clamp.integral_clamp_record(controller)  # None without P38z
    metrics["t_first_done_s"] = first_done_after_s(controller.fix.log, 0.0)  # spec 429.2 trend
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
    metrics.update(hb1_metrics(controller.fix, events, _TRUTH["crawler_series"],
                               controller.config.period_s))
    project_sink = getattr(controller._state, "diff_sink", None)  # 03_src P-S8-35 (one is idle)
    if project_sink is not None:
        metrics["ds_events"] += [dict(event) for event in project_sink.events]
        metrics["ds_active_s"] = round(metrics["ds_active_s"] + project_sink.hold_periods
                                       * controller.config.period_s, 2)
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
            if job["suite"] in RUT_LOG_SUITES:
                record["metrics"]["rut_clear_min_after_final_loc_mm"] = (
                    rut_clear_min_after_final_loc_mm(
                        _slope_harness_log(),
                        [(float(e.t_s), e.name) for e in controller.events],
                        record.get("t_ready_s")))
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
    """A fix of the candidate fired in the run: a ``FIX_*`` / S4 stroke event, the E3 target,
    a spec 427 P36 action, the spec 427.9 P36s stop, a P37t ledger offset or R4 margin
    (428.5.2) or a P38z integral cut (429.3).

    RA (REANCHOR skip) raises no fix event; its runs count as idle, so they meet the stricter
    hash rule.
    """
    metrics = record.get("metrics") or {}
    if metrics.get("e3_applied") or (metrics.get("p36") or {}).get("actions"):
        return True
    if (metrics.get("p36s") or {}).get("stop"):
        return True
    if p37_floor_twist.has_floor_twist_acted(metrics.get("p37")):
        return True
    if p38_integral_clamp.has_integral_clamp_acted(metrics.get("p38")):
        return True
    return any(name.startswith((FIX_EVENT_PREFIX, S4_STROKE_EVENT))
               and name.split(":", 1)[0] not in RECORD_ONLY_FIX_EVENTS
               for _, name in metrics.get("fix_events") or [])


def acted_parts(record: dict) -> list[str]:
    """Which of the spec 427.11 / 429.5 combination parts acted: "P36s" (stop), "P37t" (ledger
    offset), "R4c" (flat margin), "P38z" (integral cut); the stage 2 split reads it."""
    metrics = record.get("metrics") or {}
    p37 = metrics.get("p37") or {}
    parts = []
    if (metrics.get("p36s") or {}).get("stop"):
        parts.append("P36s")
    if p37.get("applied"):
        parts.append("P37t")
    if p37.get("flat_margins"):
        parts.append("R4c")
    if p38_integral_clamp.has_integral_clamp_acted(metrics.get("p38")):
        parts.append("P38z")
    return parts


def _failed_rows(record: dict) -> list[str]:
    rows = record.get("failed_rows") or []
    return rows.split(",") if isinstance(rows, str) else list(rows)


def is_safe_stop(record: dict) -> bool:
    """Spec 427.9 class ``stroke_limited_stop``: safe stop, target not reached (neither pass nor
    fail)."""
    return record.get("verdict") == VERDICT_STROKE_LIMITED_STOP


def _soft_ground_regressions(before: dict, after: dict) -> list[str]:
    """A-3 relaxation on J1 / J2 / S1 for a run the candidate acted in."""
    reasons = []
    if before.get("passed") and not after.get("passed"):
        reasons.append(f"pass -> {VERDICT_STROKE_LIMITED_STOP}" if is_safe_stop(after)
                       else "pass -> fail")
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
        "acted_parts": "+".join(acted_parts(after)),
        "safe_stop_after": is_safe_stop(after),
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
                                         "a3_fail": 0, "safe_stop": 0, "pass_to_safe_stop": 0})
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
    # spec 427.9: a safe stop is counted apart, neither pass nor fail
    was_passed, is_stopped = bool(before.get("passed")), is_safe_stop(after)
    entry["pass_to_fail"] += bool(was_passed and not after.get("passed") and not is_stopped)
    entry["safe_stop"] += is_stopped
    entry["pass_to_safe_stop"] += bool(was_passed and is_stopped)
    entry["fail_to_pass"] += bool(not before.get("passed") and after.get("passed"))
    entry["hash_same"] += row["hash_same"]
    entry["false_loc_after"] += bool(row["false_loc_after"])
    entry["ready_recontacts_after"] += bool(row["ready_recontacts_after"])
    entry["acted"] += row["acted"]
    for part in filter(None, row["acted_parts"].split("+")):  # spec 427.11 stage 2 split
        entry[f"acted_{part}"] = entry.get(f"acted_{part}", 0) + 1
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
        command.add_argument("--ids", default="",
                             help="semicolon list of exact case ids (with --filter: both apply)")
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


def _filtered(cases, text: str, exact_ids: str = ""):
    """Cases whose id contains one of the comma-separated ``text`` substrings and, when
    ``exact_ids`` is given, equals one of its semicolon-separated ids (some ids contain a comma,
    and a substring also matches the longer ids that start with it)."""
    needles = [n for n in text.split(",") if n]
    wanted = _exact_ids(exact_ids)
    return [c for c in cases if (not needles or any(n in c[0] for n in needles))
            and (not wanted or c[0] in wanted)]


def _exact_ids(exact_ids: str) -> set[str]:
    return {i.strip() for i in exact_ids.split(";") if i.strip()}


def _check_ids(suites: str, exact_ids: str) -> None:
    """Raise when an id of ``--ids`` is in none of the suites (a typo would drop it silently).

    Raises:
        ValueError: unknown case ids.
    """
    known = {case_id for suite in suites.split(",") for case_id, _ in suite_cases(suite)}
    unknown = sorted(_exact_ids(exact_ids) - known)
    if unknown:
        raise ValueError(f"unknown case ids {unknown}")


def harness_sha256() -> dict[str, str | None]:
    """Spec 427.6 meta: SHA-256 of this script and of the harnesses in ``HARNESS_HASH_FILES``
    (LF line ends, so a CRLF checkout gives the same digest; None for a missing file)."""
    paths = (Path(__file__).resolve().relative_to(ROOT), *HARNESS_HASH_FILES)
    digests = {}
    for relative in paths:
        path = ROOT / relative
        digests[relative.as_posix()] = (
            hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if path.is_file() else None)
    return digests


def _run(args) -> None:
    import s9_soil_slope as slope

    os.environ[SETTLE_HOOK_ENV] = args.settle_hook  # g6 / p3b plants read it (pool inherits)
    overrides = parse_param_overrides(args.param)
    candidates = [c for c in args.candidates.split(",") if c]
    for candidate in candidates:
        parse_candidate(candidate, overrides)  # fail before any run
    _check_ids(args.suite, args.ids)
    placement = slope.set_parent_affinity(slope.parse_affinity(args.affinity))
    records, t0 = [], time.perf_counter()
    for suite in args.suite.split(","):
        cases = _filtered(suite_cases(suite), args.filter, args.ids)
        jobs = [{"suite": suite, "id": case_id, "payload": payload, "candidate": candidate,
                 "params": overrides} for case_id, payload in cases for candidate in candidates]
        with Pool(max(1, min(args.workers, len(jobs)))) as pool:
            records += pool.map(run_job, jobs, chunksize=1)
    meta = {"script": "04_scripts/03_control/s9/s9_slope_fix_candidates.py",
            "suites": args.suite, "candidates": candidates, "params": overrides,
            "defaults": asdict(CandidateSettings()), "filter": args.filter, "ids": args.ids,
            "settle_hook": args.settle_hook, "workers": args.workers, "placement": placement,
            "wall_s": round(time.perf_counter() - t0, 1), "n_records": len(records),
            "harness_sha256": harness_sha256()}
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
        _check_ids(args.suite, args.ids)
        for suite in args.suite.split(","):
            cases = _filtered(suite_cases(suite), args.filter, args.ids)
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
