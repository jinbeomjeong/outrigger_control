"""C2 levelling controller: kinematic decomposition + pressure twist loop + F_min guard.

Implementation of ``00_docs/04_control/c2_design.md`` section 14 (design by control-expert,
gains and details decided by the user on 2026-10-21, CLAUDE.md '제어 구조'). Engine
independent: the controller sees only :class:`~outrigger_sim.signals.Measurements` and follows
the :class:`~outrigger_sim.control.protocol.Controller` contract.

Leg speeds are composed from four decoupled channels (design section 1):

    u = A [z_dot, phi_dot, theta_dot]^T + n tau_dot

* attitude: PI on the 2nd-order filtered accelerometer tilt with conditional integration,
* heave: P on the low-passed crawler clearance estimated from the strokes (target 50 mm),
* twist: drive ``n^T P -> 0`` (decision D6) with a dead band, plus the F_min guard with
  priority (proposal N3): while the guard is active, the twist term that would unload the
  guarded leg is dropped.

Phases (design 14.2): TOUCH (extend until every pad bears load) -> LEVEL -> DONE ->
PROBE (combined contact judge only) -> READY (legs locked, monitoring). FAULT holds all legs.
The probe runs once after every completed levelling and again only after a re-level trigger
(decision D4); its seal-friction estimate may only widen the friction band ``F_band``
(decision D5, starts at 13 kN).

Revision R1 (design section 16, adopted by the user on 2026-10-21, decision G7):

* touch confirmation: a leg latches only after its load held for ``touch_hold_s``, and a leg
  that has seen the load approaches slowly (the rocking on the crawler used to latch legs at
  a peak and leave pads in the air at LEVEL entry),
* crawler-zone rule: a latch with hysteresis on a slow clearance estimate from ``stroke_m``
  and the low-passed cylinder force (the rod-stroke rule had become a 3 Hz relay),
* stroke ends: judged on ``stroke_m``, the coordinate the stroke limit acts on (L1 motor
  position, L2 / machine piston position), not on the rod position ``stroke_corrected_m``.

The rod position (``stroke_corrected_m``) still drives the ``lifted`` latch, the heave loop and
the probe.

Revision R2 (design section 17, final option set H4, adopted by the user on 2026-10-21, decision
G9): pad re-anchoring (REANCHOR) once per lifting cycle between the first DONE and PROBE / READY.
On a fore-aft slope (pitch on the crawler >= 2.5 deg) the light rear legs are unloaded one after
the other along the twist mode ``n`` until their pressure reading reaches a stop threshold, so
that each pad slips under mu N and re-anchors; this releases the internal pad tangential force
(rod lateral load) built up while lifting on the slope. The sequence is an open-loop command
(twist mode, no attitude change); the attitude, heave and twist loops are suspended and the
attitude monitor and load / stroke checks abort it. Afterwards LEVEL trims and completes again.

Revision R3 (roll / pitch target, ``00_docs/04_control/s6_control_spec.md`` section 2, user
decisions U1-U4 of 2026-10-21; acceptance rules in ``control/target.py``):

* T1-T4: the attitude error is ``phi_r - phi_f`` (``phi_r`` = ramped reference); completion,
  the READY re-level trigger and the REANCHOR attitude abort compare with the final target;
  completion only once the reference has reached it.
* C1-C3: a run starts in CHECK (``check_time_s`` with ``u = 0``, the mean filtered attitude of
  the last ``check_average_s`` is ``(phi_c, theta_c)``, the mean gyro rate of the whole CHECK
  is the gyro bias removed from the probe attitude cue, spec 10.3 P3; no bias removal with
  ``check_time_s = 0``), then A0-A4 accept the target -> TOUCH,
  or reject it -> IDLE (legs held, code kept, warning event; not a FAULT). A new request in
  IDLE restarts CHECK. A target change is accepted only in READY (A0-A5); in TOUCH ... PROBE it
  is ``REJ_BUSY``. ``theta_crawler`` (TOUCH end, REANCHOR) stays apart from ``(phi_c, theta_c)``.
* R1-R2: an accepted READY change ramps the reference (0.4 / 0.25 deg/s diamond); the first
  levelling has no ramp.
* H1-H3: REANCHOR applies when ``|theta_t - theta_anchor| >= 2.5 deg``, ``theta_anchor`` =
  ``theta_crawler`` or the target pitch of the last completed REANCHOR; once per lifting cycle,
  re-armed by an accepted target change (U3).
* Z1: ``clearance_target_m`` above 92.4 mm (spec P5 with the 65.3 end 0.6948 m, not rounded)
  is a configuration error (the stroke of the worst accepted target would leave less than
  10 mm).
* P1: the probe uses the combined verdict by default; it re-grounds the ungrounded leg with the
  smallest reading and reports ``probe_unresolved`` (READY, no re-grounding) when all four are
  judged ungrounded.

Revision R4 (``s6_control_spec.md`` 16-20, user decisions U16, U17, U21, U23 of 2026-10-21):

* P1: probe moves are trapezoids (plateau 0.56 s, ramps 0.36 s) that leave about 1/10 of the
  rocking of the rectangular move (``ProbeSettings.profile``),
* P2: the conditional integration uses the larger of the two axis errors for its upper bound
  (``C2Thresholds.integrator_band_mode``),
* P5: READY re-levels below ``F_min + 7 kN`` (checked: at least the guard margin + 2 kN),
* P6: a leg too close to its stroke end is probed retract first or skipped
  (``probe_skipped:stroke_margin``) and never re-grounded.

Revision R4.1 (``s6_control_spec.md`` 21.3 and 29):

* Q1: an attitude cue whose 0.3 s windows ripple (peak to peak after detrending > 0.15 of the
  expected response) or drift (> 0.25) abstains; the leg is then judged on band and stiffness,
* Q2: after a probe round the leg to re-ground is the lightest leg below ``F_min`` + guard
  margin, before any verdict (``ProbeSettings.reground_rule``, load first),
* K1: the stiffness cue is taken on the second half of the first move
  (``ProbeSettings.stiffness_window``),
* GE1: :class:`SupportGeometryShadow` records the pad heights against the stored floor normal
  (G1') and the four-pad non-planarity (G2) every period, with the U28 conditions as
  ``shadow_*`` events; meta ``support_geometry``. Shadow only: no command depends on it.

Revision R5 (``s6_control_spec.md`` revision 7 section 42.1 with 22.4, 32-39; user decisions
H5a, U30-a, U31-a, U33-a .. U37-a):

* H5a: after the first DONE the order is PROBE -> REANCHOR (when it applies) -> LEVEL trim ->
  READY (``ReanchorSettings.after_probe``); the first probe round sets ``F_band`` to its measured
  value (at least 1 kN, ``ProbeSettings.seal_band_rule``), so the REANCHOR stop floor
  ``F_min + F_band + 10 kN`` drops to F_min + 11 kN without seal friction. A completed REANCHOR goes
  to READY without a second probe; an aborted one or a re-level probes again first.
* B1': the CHECK gyro bias is the mean of the last ``T_b`` (grade dependent, 2 / 2.5 / 10 s)
  and is taken only when that window is quiet (noise-corrected RMS); CHECK waits up to
  ``check_max_s`` (10 s) for it, otherwise the bias is not removed (``WARN_GYRO_BIAS_SKIPPED``);
  an implausible estimate (> 60 deg/h) is dropped (``WARN_GYRO_BIAS_IMPLAUSIBLE``)
  (``control/standstill.py``).
* GE1': the shadow stores ``(n_0, h(t_ref), r(t_ref))`` and judges the changes ``d_i^Delta``
  (G1') and ``Delta r`` (G2, 1.4 mm), with ``r`` the RR residual of the four-pad plane (fixed
  sign). It evaluates only while the standstill gate ``is_geometry_valid`` is open; the
  reference is refreshed in DONE / READY only after a probe round with four grounded legs and
  no re-grounding target, and only with the gate open. Still shadow only (GE2 is R6, U33-a).
* The rod stroke derived when ``stroke_corrected_m`` is missing uses the oil column at the
  operating extension (L1 lumped split, dynamics-expert) unless
  ``C2Config.rod_stroke_fallback`` asks for ``k_oil(e)`` (L2 / L2b).

Revision R6 (``s6_control_spec.md`` 51.1, 53.3-53.4, 57, 61.3, 63-64; user decisions U43-U65):

* R6-P: the load reading is the net force ``p_h A_p - p_r A_ann`` when a rod-side pressure is
  measured (``control/two_pressure.py``: diagnosis D1-D6, per-leg fallback with a model upper
  bound, rod-side 350 / 300 bar and predicted lift-off watch, the ``Delta F1`` and retraction
  lift-off shadows); per-leg cylinder areas (P-15); the 350 bar check on the raw head pressure.
* R-H4' (U62, shape U66 / U67 of spec 65.1): just before READY all four legs extend together
  1.5 mm at 0.25 v_max and settle 0.2 s (``ready_heave``), so READY locks after an extension
  with no load or attitude change; skipped (``WARN_TAIL_SKIPPED:stroke_margin``) when a leg
  would pass the end-margin stroke. Short locks (probe holds, REANCHOR, DONE) get no tail and
  the probe keeps +d -> E -> -d -> R. U63: the probe corrections use the C1 ``S_ii`` or the
  measured secant; U65: a fallback leg keeps a band >= 13 kN, its head-only probe estimates
  are not used and a rear fallback skips REANCHOR. U68 / U69: READY re-levels below F_min +
  7.5 kN, the REANCHOR floor margin is 11.5 kN. Spec 65.3: the stroke limits count from the
  measured soft end 0.6948 m (``STROKE_SOFT_MAX_M``) when the plant stroke is longer.
* R6-G (J-7, U61): GE2 acts in READY with the combined judge: G1-L (any time) and, after the
  first reference refresh of the READY stay, G1-S / G2 re-level and probe again (the probe
  verdict stays first); the same trigger key again within 30 s raises
  ``WARN_SUPPORT_CHANGE_REPEAT`` and is latched. :meth:`C2Config.with_r5_behaviour` turns R6
  off and reproduces the R5 commands, phases and events except ``shadow_*``.
* Revision 14 (spec 71-76, U70-U73): CHECK runs the airborne round-trip zero calibration of
  the force readings in parallel with B1' (``control/zero_calibration.py``; CHECK ends when
  both are done; ``check_time_s = 0`` means no CHECK and so no calibration). A leg whose
  calibration fails keeps ``c_i = 0`` and gets the lower-bound allowance (E-6) for the run.
  The locked-pressure warning is raised at 345 bar with a 300 bar pre-warning (E-4); the
  monitor watches the READY load-sum drift and the oil temperature since the calibration
  (E-5). :meth:`C2Config.with_r5_behaviour` turns all of it off.

R7 (``s6_control_spec.md`` revision 18 section 82.5 and revision 20 section 86, user decision C):
REANCHOR applies by default only on a relative nose-down slope ``theta_anchor - theta_t >= 2.5
deg`` (``ReanchorSettings.direction``; a nose-up slope is ``reanchor_skipped:nose_up``); the
meta records the direction as ``reanchor_direction``. ``TargetSettings``
``relative_pitch_span_nose_up_rad`` (default ``None``, symmetric) sets the nose-up half-span of
the D8 / relative diamonds; :meth:`C2Config.with_interim_b` is the provisional 3.1 deg operating
preset. :meth:`C2Config.with_r6_behaviour` (and so every older preset) restores both REANCHOR
directions and the symmetric diamonds.

R8-D1 (``s6_control_spec.md`` revision 26 101 (3)-(9), revision 30 136 / 139; user decisions
U-R8-6 = C2, U-R8-7, U-R8-8, U-R8-10 of 2026-10-24): :meth:`C2Config.with_10hz_d1` runs at
10 Hz with the output one period late (``R8Settings.output_delay_periods``, buffer inside the
controller), the attitude filter at 100 Hz on the IMU samples, the C2 gains, the twist loop on
a low-passed ``n^T P``, gains divided by the probe-measured stiffness (revision 31 149), the
increment limit (a FAULT stop skips it), R-1 / R-2, sample confirmation, R-3 and the stroke-end
slowdown. Revision 32 163.1 (U-R8-13, U-R8-14): the CHECK attitude is the mean raw 10 ms tilt
from ``check_quiet_after_motion_s`` after the last leg command (P-R8-9), R-5 is on with a
4-period horizon (P-R8-10), and in PROBE a low load on a leg not being probed stops the probe
and re-levels (P-R8-11, event ``probe_aborted_low_load:<leg>``). Revision 34 174.4 (U-R8-21,
replacing P-R8-12 of revision 33): a grounded leg that lifts again is re-approached with the
twist mode toward it (fastest leg 0.25 ``v_max``, one leg at a time) instead of the twist and
guard terms, until it reads ``F_min + 5 kN`` on three samples (P-R8-13, events
``leg_reapproach_start:<leg>``, ``leg_reapproach_contact:<leg>``,
``WARN_LEG_REAPPROACH_NO_CONTACT:<leg>``); P-R8-12 stays as
:meth:`LiftedReapproachSettings.leg_mode`. Revision 52 228.3 (P-S8-16, U-S8-49): a
re-approach within 2 s of the last one's end runs at 0.6 of the speed, and one on the other
diagonal within 0.8 s waits for two samples below 0 N (event
``leg_reapproach_deferred:<leg>``). :attr:`C2Controller.command_components_m_s` gives
the attitude / heave / twist / guard / re-approach parts of each LEVEL command (P-R8-14) and
the phase command of the other periods; :attr:`C2Controller.raw_output_m_s` and
:attr:`C2Controller.output_limit_flags` give the command before the limits and which limit
changed which leg (P-R8-15, revision 35 188.2). The probe stiffness warning range is
(0.8, 2.3) (P-R8-16).
Revision 57 285 (P-S9-1 .. P-S9-10, user decisions U-S9-C1 .. C6 of 2026-10-26): the soil
response :class:`SoilResponseSettings` (``C2Config.soil``, :meth:`C2Config.with_soil_response`)
confirms the crawler lift-off from a flat load sum while every leg extends (S-1), holds the
crawler zone and pushes every leg up until then (S-2, soil mode), corrects the corner clearance
by the pad sinkage seen at the lift-off (S-3), stops after 150 mm of unconfirmed push (S-4) and
records the weight estimate (S-5); ``LiftedReapproachSettings.max_duration_s`` ends a
re-approach that runs too long (P-S9-10). ``C2Config()`` keeps both off; since U-S9-C1 /
U-S9-C4 :meth:`C2Config.with_10hz_d1` turns both on (10 s limit); ``replace(config,
soil=SoilResponseSettings())`` turns the soil response off again (revision-56 commands unless a
re-approach lasts 10 s).
Only the start-IMU form exists
(the late IMU read C1 is not implemented). ``C2Config()`` keeps every R8 setting off, so the
R7 commands stay bit for bit.

With a level target, ``check_time_s = 0``, the rectangular probe without stroke guard, the
per-axis band, the 3 kN re-level margin (``allow_legacy_relevel_margin``) and the R4 probe
judge (verdict re-ground rule, no attitude quality gate, full stiffness window) the run is the
revision R2 run bit for bit (the reduced-model traces have no CHECK); with CHECK the same run
starts ``check_time_s`` later. The R4 and R4.1 defaults have their own regression traces
(``04_scripts/03_control/export_c2_r4_traces.py``); :meth:`C2Config.with_r41_behaviour` turns
the R5 changes off and reproduces the R4.1 commands and phases bit for bit. The GE1 shadow adds
``shadow_*`` and ``INFO_FLOOR_NONPLANAR`` events only (:func:`is_shadow_event`).

Combined contact judge (``control/ground_contact.py``): the probe of PROBE is a
:class:`~outrigger_sim.control.ground_contact.ProbeRound`; besides the decided stiffness verdict
it records the attitude response against the kinematic ``J`` and keeps each probe within the
attitude limit of decision D4. READY also reports a locked pressure above 350 bar
(``actuator.locked_pressure_limit_Pa``, CLAUDE.md '압력 센서') as a warning event, once per leg.

The per-period order of operations reproduces the discrete control law of the reduced
model (``04_scripts/03_control/run_c2_revision.py`` class ``C2R``, gain set ``R:BS_hold``, on
top of ``run_c2_timedomain.py`` ``C2D`` and ``04_scripts/01_dynamics/run_control_comparison.py``),
which the design verified; ``05_tests/unit/test_c2.py`` replays recorded traces of that model.

Units SI (m, rad, N, s). Per-leg arrays follow ``LEG_ORDER`` (FL, FR, RL, RR).
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import asdict, dataclass, field, replace
from enum import Enum, StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.control.ground_contact import (
    LoadBand,
    ProbeReading,
    ProbeResult,
    ProbeRound,
    ProbeSensitivity,
    ProbeSequence,
    ProbeSettings,
    RegroundRule,
    SealBandRule,
    attitude_sensitivity_rad_m,
    classify_load,
)
from outrigger_sim.control.standstill import (
    GyroBiasEstimate,
    GyroBiasOutcome,
    StandstillGate,
    StandstillGateSettings,
    StandstillGateState,
    deg_per_hour,
    gyro_bias_motion_limit_rad_s,
    gyro_bias_window_s,
    window_statistics,
)
from outrigger_sim.control.target import (
    INTERIM_B_NOSE_UP_PITCH_SPAN_RAD,
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
    TargetAcceptance,
    TargetCheck,
    TargetCode,
    TargetLimits,
    check_target,
    floor_usage,
    ramp_reference,
)
from outrigger_sim.control.two_pressure import (
    BODY_MASS_WITHOUT_YAML_KG,
    LoadEstimate,
    PressureForces,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.control.zero_calibration import (
    LegCalibration,
    SkipReason,
    ZeroCalibration,
    ZeroCalibrationMode,
    ZeroCalibrationSettings,
)
from outrigger_sim.params import LEG_ORDER, Params, ParamsError
from outrigger_sim.sensors.attitude import (
    ATTITUDE_FILTER_STAGE_COUNT,
    ATTITUDE_FILTER_TIME_CONSTANT_S,
    AttitudeEstimate,
    AttitudeEstimator,
    CascadedLowPass,
)
from outrigger_sim.sensors.hydraulic import (
    leg_annulus_areas_from_params,
    leg_head_areas_from_params,
)
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M, STANDARD_GRAVITY_M_S2
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S, LEG_COUNT, Command, Measurements

logger = logging.getLogger(__name__)

C2_CONTROLLER_NAME = "C2"
C2_REVISION = "R7"
R8_REVISION = "R8-D1 (C2)"
"""Meta revision of a config with R8 settings (:meth:`C2Config.with_10hz_d1`)."""
DESIGN_SOURCE = (
    "00_docs/04_control/c2_design.md section 14, revision R1 section 16, revision R2 section 17; "
    "revision R3 00_docs/04_control/s6_control_spec.md section 2 (user decisions 2026-10-21); "
    "revision R5 s6_control_spec.md revision 7 section 42.1 (user decisions 2026-10-22); "
    "revision R6 s6_control_spec.md 51.1, 53.3-53.4, 57, 59.1 J-7, 61.3, 63-64 (U43-U65); "
    "revision R7 s6_control_spec.md 82.5, 86.1-86.3 (user decisions C and provisional B); "
    "R8-D1 preset s6_control_spec.md rev. 26 101, rev. 30 136 / 139 (C2, 2026-10-24)"
)

# Crawler footprint box in body xy (m): parts_classified.csv row 'COMPOUND' bbox, CAD (X, Z)
# -> body (y, x). Not in the YAML; same value as 04_scripts/01_dynamics/dyn_model.py
# geometry_from_params (used by the reduced model the design was verified on).
CRAWLER_XY_BOX_M = ((-1.840, 1.844), (-1.366, 1.366))
CRAWLER_CORNER_NAMES = ("RR", "RL", "FR", "FL")
"""Corners of ``C2Geometry.crawler_corners_xy_m`` in its order (x_min / x_max = rear / front,
y_min / y_max = right / left)."""

# Float sample times (k * T) may miss the touch hold time by rounding; this slack keeps the
# latch on the intended period (same value as the reduced model, design 14.4).
TOUCH_HOLD_SLACK_S = 1e-9

# REANCHOR comparison slacks, the values of the reduced model the design verified (design 17.7
# Q5): float sample times may miss a hold time by rounding, the slope threshold is compared in
# radians converted from degrees, and the return ends once the commanded travel is this small.
REANCHOR_HOLD_SLACK_S = 1e-9
REANCHOR_THETA_SLACK_RAD = 1e-12
REANCHOR_RETURN_DONE_M = 1e-10

OIL_BULK_MODULUS_KEY = "actuator.oil_bulk_modulus_eff_Pa"
OIL_DEAD_LENGTH_KEY = "actuator.oil_dead_length_m"
LOCKED_PRESSURE_LIMIT_KEY = "actuator.locked_pressure_limit_Pa"
RETRACT_LOCK_ROD_PRESSURE_KEY = "actuator.rod_side.p_r0_after_retract_Pa"
CB_LAG_TAU_KEY = "actuator.rod_side.release_tau_s"

# Spec 2.3 A5: stroke window of a READY target change, 10 mm stroke margin + 3 mm for the
# predictor error (-2.39 ... +2.35 mm against the envelope map).
TARGET_STROKE_MARGIN_M = 0.013

# Spec 2.6 Z1: worst stroke of an accepted target at the 50 mm clearance target and its slope
# with the clearance target (s6_control_spec.json envelope_rule_A.worst_accepted,
# heave_target_rule); the stroke must stay 10 mm inside s_max (c* <= 92 mm, spec 65.3).
WORST_ACCEPTED_STROKE_M = 0.6422
WORST_STROKE_PER_CLEARANCE = 1.005
REFERENCE_CLEARANCE_M = 0.05
CLEARANCE_RULE_STROKE_MARGIN_M = 0.010
ENVELOPE_STROKE_MAX_M = 0.6948
"""Stroke end the envelope behind rule A was computed for (spec 65.3: the measured soft end;
642.2 mm worst static stroke, so ``c* <= 92 mm``)."""
STROKE_SOFT_MAX_M = 0.6948
"""Spec 65.3 (user decision): software stroke end = the stroke sensor's measured range; the
FAULT threshold (1 mm before), the A5 window (13 mm) and the 10 mm end margins count from
``min(s_max, STROKE_SOFT_MAX_M)``, so a plant with the 0.68 m YAML stroke keeps its limits."""
STROKE_END_MARGIN_M = 0.010
"""Spec 65.1 / 65.3: end margin of the READY heave tail guard (0.6848 m for a 0.70 m plant)."""

# Spec 20.2 P5: the READY re-level threshold must lie this far above the LEVEL guard threshold.
RELEVEL_ABOVE_GUARD_N = 2500.0
"""Spec 65.2 (U68): READY re-level threshold >= guard margin + 2.5 kN (was 2 kN)."""

# CHECK end and comparisons of float sample times (same convention as the touch hold).
CHECK_TIME_SLACK_S = 1e-9


# --- configuration -------------------------------------------------------------------------


class C2Phase(StrEnum):
    """Controller phase (design 14.2)."""

    CHECK = "check"
    """Standstill on the crawler, measures ``(phi_c, theta_c)``, then A0-A4 (spec C1)."""
    IDLE = "idle"
    """Target rejected at CHECK: legs held, code kept, warning event; not a fault (C2)."""
    TOUCH = "touch"
    LEVEL = "level"
    DONE = "done"
    REANCHOR = "reanchor"
    """Pad re-anchoring after the first DONE (revision R2, design 17)."""
    PROBE = "probe"
    READY = "ready"
    FAULT = "fault"


GEOMETRY_GATE_PHASES = frozenset({C2Phase.DONE, C2Phase.PROBE, C2Phase.READY})
"""GE1'-c (spec 32.1): phases in which the standstill gate may open (the probe moves are kept
out by the command-free time)."""
CRAWLER_LIFTED_PHASES = frozenset(
    {C2Phase.LEVEL, C2Phase.DONE, C2Phase.REANCHOR, C2Phase.PROBE, C2Phase.READY}
)
"""D1'' (spec rev. 48 218.4, P-S8-14): phases after the crawler left the ground, in which a
head step is judged by the IMU residual (the crawler load of CHECK / TOUCH is not in the leg
sum). FAULT keeps the D1' sum rule."""
REFERENCE_UPDATE_PHASES = frozenset({C2Phase.DONE, C2Phase.READY})
"""GE1'-b: phases whose entry arms a refresh of the shadow reference."""
REAPPROACH_PHASES = frozenset({C2Phase.LEVEL, C2Phase.DONE, C2Phase.PROBE, C2Phase.READY})
"""P-R8-12 / P-R8-13: phases in which a lifted leg is watched and re-approaches (spec 172.1;
DONE is the one-period hand-over to PROBE / READY)."""
NO_REAPPROACH_STRONG_COUNTS = (0,) * LEG_COUNT
"""P-S8-16 RT 1: the other-diagonal confirmation counts of a run with nothing counted yet."""
REAPPROACH_DEFERRED_EVENT = "leg_reapproach_deferred"
"""P-S8-16 RT 1: event prefix of a deferred other-diagonal start (``:<leg>``, not a warning)."""
COMMAND_COMPONENT_NAMES = ("attitude", "heave", "twist", "guard", "reapproach", "phase_path")
"""P-R8-14 (spec rev. 34 179.1) / P-R8-15 (rev. 35 188.2): keys of
:attr:`C2Controller.command_components_m_s`, read by the runner's ``r8_series.cmp_<name>_u``
columns. ``phase_path`` is the command of a period that ran no LEVEL step."""


class OutputLimit(StrEnum):
    """P-R8-15 (spec rev. 35 188.2): the stages between the raw command and the computed
    output, keys of :attr:`C2Controller.output_limit_flags`."""

    SPEED_SCALE = "speed_scale"
    """LEVEL: the whole vector scaled to ``v_max`` (design 6.1)."""
    CRAWLER_RULE = "crawler_rule"
    """LEVEL: the crawler-zone heave so that no leg retracts (R1)."""
    STROKE_END = "stroke_end"
    """Stroke-end clipping (LEVEL, REANCHOR), the stroke-end FAULT stop and the spec 99.3 end
    slowdown."""
    INCREMENT = "increment"
    """The R8 increment limit, or the R7 output ramp."""


class ContactJudge(StrEnum):
    """How leg loads are judged (design 14.1 ``contact``)."""

    PRESSURE = "pressure"
    """Raw pressure reading only."""
    COMBINED = "combined"
    """Lower bound ``P - F_band``, free-air offset at touchdown, probe after levelling."""


@dataclass(frozen=True)
class C2Gains:
    """Loop gains (design section 9, user decision 2026-10-21)."""

    attitude_kp_1_s: float = 0.4
    """Roll / pitch proportional gain (rad/s per rad)."""
    attitude_ki_1_s2: float = 0.02
    """Roll / pitch integral gain (rad/s per rad s)."""
    heave_kz_1_s: float = 0.5
    """Heave gain on the clearance error (m/s per m)."""
    twist_ktw_1_s: float = 1.0
    """Twist loop gain on ``n^T P / k_nom`` (proposal N2: 0.5 -> 1.0)."""
    guard_kg_1_s: float = 1.0
    """F_min guard gain on the load deficit / ``k_nom`` (proposal N3: 0.5 -> 1.0)."""


@dataclass(frozen=True)
class C2Filters:
    """Signal filters; every stage is the forward-Euler stage of ``sensors.attitude``."""

    attitude_time_constant_s: float = ATTITUDE_FILTER_TIME_CONSTANT_S
    """Per-stage tau of the attitude low-pass (user decision 2026-10-20)."""
    attitude_stage_count: int = ATTITUDE_FILTER_STAGE_COUNT
    completion_time_constant_s: float = 1.0
    """Extra stage on the filtered attitude for completion and re-level checks (design 14.2)."""
    clearance_time_constant_s: float = 0.2
    """Low-pass on the stroke-based crawler clearance for the heave loop (proposal N1)."""
    crawler_rule_pressure_time_constant_s: float = 0.2
    """Low-pass on the cylinder force for the crawler-zone clearance estimate (R1, 16.2)."""
    twist_load_time_constant_s: float | None = None
    """R8 C2 (spec 136, 139 P-4): one stage on ``n^T P`` of the twist loop only; the F_min
    guard keeps the raw per-leg reading. ``None`` = no filter (R7)."""


class IntegratorBandMode(StrEnum):
    """Upper bound of the conditional integration (spec 16.2 P2)."""

    AXIS = "axis"
    """Each axis integrates while its own error is inside the band (R2 / R3)."""
    JOINT = "joint"
    """Both axes integrate only while ``max(|e_phi|, |e_theta|)`` is below the upper bound;
    the 0.01 deg lower bound stays per axis (R4 default)."""


@dataclass(frozen=True)
class C2Thresholds:
    """Phase, guard and completion thresholds (design 14.4-14.6, reduced model values)."""

    touch_load_factor: float = 1.5
    """Touchdown when the leg load reaches this multiple of F_min (pad preload)."""
    touch_hold_s: float = 0.5
    """R1 (16.3): the touchdown load must hold without a break this long before a leg latches
    (2/3 of the 0.75 s period of the rocking on the crawler)."""
    touch_approach_speed_fraction: float = 0.25
    """R1 (16.3): extension speed / ``v_max`` of a leg that has seen the touchdown load once."""
    free_air_window_s: float = 5.0
    """Combined judge: free-air reading = median of the readings of the first 5 s."""
    rod_weight_N: float = 1047.2
    """Rod + pad weight seen by the free-air reading (reduced model ``rod_weight_N``)."""
    clearance_target_m: float = 0.05
    """Crawler clearance after levelling (YAML ``simulation.crawler_clearance_m``)."""
    lifted_clearance_m: float = 0.01
    """``lifted`` latches once the clearance estimate exceeds this."""
    crawler_zone_release_m: float = 0.02
    """R1 (16.2): the crawler zone (add pure heave instead of retracting) ends once the slow
    clearance estimate reaches this."""
    crawler_zone_rearm_m: float = 0.01
    """R1 (16.2): the crawler zone starts again only below this; the 10 mm hysteresis keeps the
    3 Hz rocking from toggling the rule."""
    integrator_band_rad: tuple[float, float] = (math.radians(0.01), math.radians(0.2))
    """Conditional integration: integrate only while ``low < |error| < high``."""
    integrator_band_mode: IntegratorBandMode = IntegratorBandMode.JOINT
    """Spec 16.2 P2 (U17): ``joint`` (default) applies the upper bound to the larger of the two
    axis errors, so a moving axis does not charge the other axis's integrator; ``axis`` is the
    per-axis band of R2 / R3 (their regression traces)."""
    integrator_limit_rad_s: float = 0.02
    twist_deadband_N: float = 2000.0
    guard_margin_N: float = 5000.0
    """The guard acts below ``F_min + guard_margin_N``."""
    done_attitude_rad: float = math.radians(0.03)
    done_clearance_tolerance_m: float = 2e-3
    done_twist_N: float = 3000.0
    done_hold_s: float = 1.0
    relevel_attitude_rad: float = math.radians(0.07)
    relevel_load_margin_N: float = 7500.0
    """READY re-levels when the lowest load estimate drops below ``F_min + margin``. U68 (spec
    65.2): guard 5 + overshoot 1.2 + 3 sigma 1.24 kN -> 7.5 kN (ASSUMPTION, L1-R; R4-R5: 7 kN,
    R2 / R3: 3 kN, which left READY idle 2 kN below the guard threshold)."""
    stroke_end_fault_margin_m: float = 1e-3
    stroke_end_fault_speed_m_s: float = 1e-5
    """A leg counts as 'still asked to extend' above this command."""
    stroke_end_fault_time_s: float = 2.0
    stroke_end_clip_margin_m: float = 1e-4
    locked_pressure_warning_margin_Pa: float = 5e5
    """E-4 (U72): READY warns above the locked limit minus this (345 bar for 350 bar); the
    sensor error near 350 bar is about 3 bar after the calibration. R5: 0."""
    locked_pressure_prewarning_Pa: float | None = 300e5
    """E-4: head-side pre-warning (``locked_pressure_prewarning:<leg>``); ``None`` = off."""
    allow_legacy_relevel_margin: bool = False
    """Skip the P5 check ``relevel_load_margin_N >= guard_margin_N + 2 kN``; only for replaying
    the R2 / R3 regression traces (3 kN)."""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "integrator_band_mode", IntegratorBandMode(self.integrator_band_mode)
        )
        required_N = self.guard_margin_N + RELEVEL_ABOVE_GUARD_N
        if not self.allow_legacy_relevel_margin and self.relevel_load_margin_N < required_N:
            raise ValueError(
                f"relevel_load_margin_N {self.relevel_load_margin_N:.0f} N < guard_margin_N + "
                f"{RELEVEL_ABOVE_GUARD_N:.0f} N = {required_N:.0f} N (spec 20.2 P5): READY "
                "would wait below the LEVEL guard threshold"
            )


class ReanchorDirection(StrEnum):
    """Pitch directions in which REANCHOR applies (spec 82.5, R7 candidate)."""

    BOTH = "both"
    """``|theta_t - theta_anchor| >= theta_min`` (H2, R2-R6)."""
    NOSE_DOWN_ONLY = "nose_down_only"
    """Option C: only ``theta_anchor - theta_t >= theta_min`` (relative nose-down, theta > 0 =
    nose down); a relative nose-up slope is skipped as ``reanchor_skipped:nose_up``."""
    OFF = "off"
    """Never (``reanchor_skipped:direction_off``)."""


class StopPredictor(StrEnum):
    """How the REANCHOR MOVE judges the stop reading (R8 R-1, spec 99.3, 139 P-6)."""

    OFF = "off"
    """The reading itself (R2-R7)."""
    READING_RATE = "reading_rate"
    """``P_hat = P - r_hat (1 + d)`` with ``r_hat`` the mean unloading per period over the
    last ``stop_predictor_intervals`` periods of the step and ``d`` the output delay: the
    reading is one period old and the stop acts ``d`` periods late."""


@dataclass(frozen=True)
class ReanchorSettings:
    """Pad re-anchoring after the first levelling (design 17, revision R2, option set H4).

    The fields are the settings of design 17.7 Q2 without their ``reanchor_`` prefix.
    """

    enable: bool = True
    direction: ReanchorDirection = ReanchorDirection.NOSE_DOWN_ONLY
    """Spec 82.5: user decision C (no H4 on a nose-up slope) first. Whether the nose-down side
    also goes ``off`` is still open; that decision changes only this default.
    :meth:`C2Config.with_r6_behaviour` restores ``both``."""
    theta_min_rad: float = math.radians(2.5)
    """Applied only when the filtered pitch on the crawler (at TOUCH -> LEVEL) is at least
    this large; the tangential force grows with the slope squared (design 17.2.2)."""
    wait_s: float = 2.0
    """Standstill between the first DONE and the first move."""
    speed_fraction: float = 0.1
    """Speed of the fastest leg / ``v_max`` (0.25 broke the F_min + 5 kN criterion)."""
    stair_N: tuple[float, ...] = (45e3, 30e3, 20e3, 20e3)
    """Stop reading of the target leg per step, before the floor; one step per entry."""
    floor_abs_N: float = 20e3
    floor_margin_N: float = 11.5e3
    """Stop floor ``F_min + F_band + margin``: 5 kN criterion + hold-phase drop + pressure noise
    (design 17.3); U69 (spec 65.2): 5 + 5.2 + 1.24 kN -> 11.5 kN (R2-R5: 10 kN)."""
    targets: tuple[str, ...] = ("RR", "RL")
    """Target legs, cycled over the steps: the lighter axle (case C mass: the rear)."""
    hold_s: float = 1.0
    """Standstill after the stop, before the commanded travel is returned."""
    hold2_s: float = 1.0
    """Standstill after the return, before the next step."""
    other_margin_N: float = 5e3
    """MOVE aborts when a non-target load estimate drops below ``F_min + margin``."""
    hold_guard_margin_N: float = 0.0
    """HOLD aborts when any load estimate drops below ``F_min + margin``."""
    max_step_stroke_m: float = 8e-3
    """MOVE aborts at this commanded travel (about 3 x the expected 1.2-2.9 mm)."""
    attitude_abort_rad: float = math.radians(0.07)
    """Aborts when the completion-filtered roll or pitch exceeds this (re-level trigger)."""
    stroke_end_margin_m: float = 0.01
    """Applied only when every motor stroke is this far from both stroke ends."""
    after_probe: bool = True
    """H5a (spec 22.4, ``reanchor_after_probe``): with the combined judge the first DONE probes
    first and REANCHOR follows the probe, so its stop floor uses the measured ``F_band``;
    ``False`` = R2-R4.1 order (REANCHOR at the first DONE, probe after the trim)."""
    stop_predictor: StopPredictor = StopPredictor.OFF
    """R8 R-1: stop on the predicted reading (``reading_rate``) instead of the reading."""
    stop_predictor_intervals: int = 3
    """R-1: ``r_hat`` from up to this many period-to-period changes (4 readings)."""

    def __post_init__(self) -> None:
        if not 0.0 < self.speed_fraction <= 1.0:
            raise ValueError(f"speed_fraction must be in (0, 1], got {self.speed_fraction!r}")
        if self.stop_predictor_intervals < 1:
            raise ValueError("stop_predictor_intervals must be >= 1")
        object.__setattr__(self, "stop_predictor", StopPredictor(self.stop_predictor))
        if not self.stair_N:
            raise ValueError("stair_N needs at least one step")
        unknown = [leg for leg in self.targets if leg not in LEG_ORDER]
        if not self.targets or unknown:
            raise ValueError(f"targets must be leg names of {LEG_ORDER}, got {self.targets!r}")
        object.__setattr__(self, "direction", ReanchorDirection(self.direction))
        object.__setattr__(self, "stair_N", tuple(self.stair_N))
        object.__setattr__(self, "targets", tuple(self.targets))


@dataclass(frozen=True)
class TargetSettings:
    """Roll / pitch target, its acceptance and ramp (revision R3, spec 2.2-2.4)."""

    target: AttitudeTarget = field(default_factory=AttitudeTarget)
    """Target requested at the start of a run (judged at the end of CHECK; default level)."""
    slope_limit_mode: SlopeLimitMode = SlopeLimitMode.OPERATING
    """``verification`` (5.5 / 3.5 deg D8 / relative diamond) for the simulation checks only."""
    acceptance: TargetAcceptance = TargetAcceptance.REJECT
    """U1: reject; ``project`` is an option, ``off`` only for trace replays beyond the limits."""
    check_time_s: float = 2.0
    """C1 standstill (ASSUMPTION); 0 skips it (TOUCH runs in the first period, as in R2)."""
    check_average_s: float = 1.0
    """C1: ``(phi_c, theta_c)`` = mean filtered attitude over this window (ASSUMPTION); with
    ``r8.check_attitude_from_raw_tilt`` the mean raw IMU-rate tilt."""
    check_quiet_after_motion_s: float = 0.5
    """P-R8-9 ``T_q`` (ASSUMPTION, spec 158.1: valve lag tail and the first half period of the
    rocking): the raw-tilt CHECK window starts this long after the last nonzero leg command
    (the zero-calibration round trip included). Unused on the filtered-attitude path."""
    roll_ramp_rate_rad_s: float = math.radians(0.4)
    """R1 (U4): reference ramp of a READY change (ASSUMPTION)."""
    pitch_ramp_rate_rad_s: float = math.radians(0.25)
    crawler_settle_map: CrawlerSettleMap | None = None
    """X5: floor estimate of A1 / A4 in the verification mode
    (:meth:`CrawlerSettleMap.for_level`); ``None`` = identity. Operating mode: identity only."""
    check_max_s: float = 10.0
    """B1' (U31-a): CHECK is extended up to this long while the bias window is not quiet or
    shorter than ``T_b``; ``check_max_s = check_time_s`` never extends (R4.1)."""
    gyro_noise_std_rad_s: float = 0.0
    """B1' / GE1' gate: per-sample gyro white noise ``sigma_g`` of the grade (from the IMU
    setting, ``ImuErrorConfig.gyro_noise_std_rad_s``; ASSUMPTION in simulation)."""
    gyro_bias_target_std_rad_s: float = deg_per_hour(4.0)
    """B1' (spec 39): ``T_b = clamp(T (sigma_g / target)^2, check_time_s, check_max_s)``
    (ASSUMPTION 4 deg/h: ideal 2 s, good 2.5 s, normal 10 s)."""
    gyro_bias_max_rate_rms_rad_s: float | None = math.radians(0.01)
    """B1' (spec 32.2, 39, 44.2): noise-corrected RMS about the window mean, per axis, above
    which a ``gyro_bias_max_rate_rms_window_s`` window is moving (ASSUMPTION); the limit of a
    ``T_b`` window is :meth:`gyro_bias_motion_limit_rad_s`. ``None`` = no motion condition
    (R4.1)."""
    gyro_bias_max_rate_rms_window_s: float = 2.0
    """R5-B (U41-a): window length the base limit belongs to."""
    gyro_bias_max_rate_rms_cap_rad_s: float = math.radians(0.02)
    """R5-B (U41-a): the scaled limit never exceeds this (reached at a 10 s window)."""
    gyro_bias_plausible_rad_s: float | None = deg_per_hour(60.0)
    """B1' (spec 32.2): an estimate above 3 x the normal grade bias is discarded; ``None`` =
    no check (R4.1)."""
    relative_pitch_span_nose_up_rad: float | None = None
    """R7 (spec 86.3): nose-up half-span of the D8 / relative diamonds on top of the mode's
    limits (:attr:`TargetLimits.relative_pitch_span_nose_up_rad`); ``None`` = symmetric. The
    provisional B operating value is :meth:`C2Config.with_interim_b`. Operating mode only: the
    verification mode keeps its symmetric 5.5 / 3.5 deg check range (spec revision 22 90.2)."""

    def __post_init__(self) -> None:
        if self.check_time_s < 0.0 or self.check_average_s <= 0.0:
            raise ValueError("check_time_s must be >= 0 and check_average_s > 0")
        if self.check_quiet_after_motion_s < 0.0:
            raise ValueError("check_quiet_after_motion_s must be >= 0")
        if self.check_max_s < self.check_time_s:
            raise ValueError("check_max_s must be >= check_time_s")
        if self.gyro_noise_std_rad_s < 0.0 or not self.gyro_bias_target_std_rad_s > 0.0:
            raise ValueError("gyro_noise_std_rad_s must be >= 0, the target std > 0")
        if not (self.roll_ramp_rate_rad_s > 0.0 and self.pitch_ramp_rate_rad_s > 0.0):
            raise ValueError("ramp rates must be > 0")
        object.__setattr__(self, "slope_limit_mode", SlopeLimitMode(self.slope_limit_mode))
        object.__setattr__(self, "acceptance", TargetAcceptance(self.acceptance))
        is_operating = self.slope_limit_mode is SlopeLimitMode.OPERATING
        if is_operating and not self.settle_map.is_identity:
            raise ValueError(
                "crawler_settle_map: the operating mode judges the measured attitude (user "
                "decision U12); a settle map is for the verification mode only"
            )
        if not is_operating and self.relative_pitch_span_nose_up_rad is not None:
            raise ValueError(
                "relative_pitch_span_nose_up_rad: the provisional B nose-up limit "
                "(C2Config.with_interim_b) is an operating limit; the verification mode keeps "
                "its symmetric check range (spec revision 22 90.2)"
            )

    @property
    def limits(self) -> TargetLimits:
        limits = TargetLimits.for_mode(self.slope_limit_mode)
        if self.relative_pitch_span_nose_up_rad is None:
            return limits
        return replace(limits, relative_pitch_span_nose_up_rad=self.relative_pitch_span_nose_up_rad)

    @property
    def settle_map(self) -> CrawlerSettleMap:
        return self.crawler_settle_map or CrawlerSettleMap.identity()

    def gyro_bias_window_s(self, period_s: float) -> float:
        """B1' averaging length ``T_b`` for gyro samples of ``period_s`` (spec 39)."""
        return gyro_bias_window_s(
            self.gyro_noise_std_rad_s,
            self.gyro_bias_target_std_rad_s,
            period_s,
            self.check_time_s,
            self.check_max_s,
        )

    def gyro_bias_motion_limit_rad_s(self, window_s: float) -> float | None:
        """B1' motion limit ``omega_th(T_b) = min(base sqrt(T_b / 2 s), cap)`` (spec 44.2)."""
        if self.gyro_bias_max_rate_rms_rad_s is None:
            return None
        return gyro_bias_motion_limit_rad_s(
            window_s,
            self.gyro_bias_max_rate_rms_rad_s,
            self.gyro_bias_max_rate_rms_window_s,
            self.gyro_bias_max_rate_rms_cap_rad_s,
        )


class RodStrokeFallback(StrEnum):
    """Rod stroke derived when a reading has no ``stroke_corrected_m``."""

    OPERATING_OIL_COLUMN = "operating_oil_column"
    """``s - F / k_oil(e_op)`` with the oil column at the operating extension: the L1 lumped
    split ``1 / k_oil + 1 / k_s = 1 / k_n`` (dynamics-expert, R5 default)."""
    STROKE_OIL_COLUMN = "stroke_oil_column"
    """``s - F / k_oil(s)`` with the extension-dependent column (R4.1; L2 / L2b plants)."""
    REQUIRED = "required"
    """No fallback: a reading without ``stroke_corrected_m`` is an error."""


class GeometryJudge(StrEnum):
    """R6-G (J-7): whether the GE2 geometry cues act (spec 57, U59, U61)."""

    SHADOW = "shadow"
    """Recorded only (R5)."""
    ACTIVE = "active"
    """READY re-level + probe on G1-L / G1-S / G2 (combined judge only; the pressure judge is
    always shadow, U59)."""


@dataclass(frozen=True)
class GeometryJudgeSettings:
    """R6-G settings (spec 37.3, 49.4, 57; ASSUMPTION values)."""

    mode: GeometryJudge = GeometryJudge.ACTIVE
    repeat_window_s: float = 30.0
    """37.3: the same trigger key again within this time -> ``WARN_SUPPORT_CHANGE_REPEAT``."""
    mismatch_load_change_N: float = 3000.0
    """K-6 / D7: a G1-S leg whose net force changed less than this since the reference ->
    ``WARN_GEOMETRY_PRESSURE_MISMATCH``."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", GeometryJudge(self.mode))


class RetractTailMode(StrEnum):
    """Shape of the R-H4' extension tail (spec 65.1, U66 / U67)."""

    READY_HEAVE = "ready_heave"
    """Just before READY: all four legs extend ``tail_m`` together (pure heave: no load or
    attitude change), settle, lock. Once per READY entry after a retraction."""
    PER_TRANSITION = "per_transition"
    """Spec rev. 11 (legacy option): each grounded leg whose last move was a retraction, at
    DONE / READY entry and the REANCHOR stop."""


@dataclass(frozen=True)
class LockTailSettings:
    """U62 / U66 / U67 (R-H4', spec 63.3, 65.1): extension tail before READY locks."""

    enable: bool = True
    mode: RetractTailMode = RetractTailMode.READY_HEAVE
    tail_m: float = 1.5e-3
    """``retract_tail_m`` (U66: 1.5 mm; 2.0 mm covers the adverse case, ASSUMPTION)."""
    speed_fraction: float = 0.25
    """``retract_tail_speed_fraction`` of ``v_max``."""
    settle_s: float = 0.2
    """``tail_settle_s``: standstill after the tail before READY acts."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", RetractTailMode(self.mode))
        if self.tail_m < 0.0 or not 0.0 < self.speed_fraction <= 1.0:
            raise ValueError("tail_m must be >= 0 and speed_fraction in (0, 1]")


class TwistGainReference(StrEnum):
    """Stiffness the twist and guard gains are divided by (R8, spec 135, 139 P-5, U-R8-8)."""

    NOMINAL = "k_nom"
    """``k_nom`` (R7)."""
    MEASURED_SII = "measured_Sii"
    """``k_nom`` times the median ratio of the probe-measured ``S_ii`` to the head-only nominal
    ``S_ii`` (``C2Geometry.load_sensitivity_diag_N_m``) over the legs of the last probe round
    the stiffness cue calls grounded (spec 144); ``pre_probe_stiffness_scale`` before a probe."""


@dataclass(frozen=True)
class IncrementLimit:
    """Output change per leg and period, replacing the soft ramp at 10 Hz (spec 99.3, 99.4).

    Symmetric 0.25 is fixed by Chrono bundle C (U-R8-27, 2026-10-24); a fraction of 0.1 or
    less is not allowed.
    """

    fraction_per_period: float = 0.25
    """``|u_k - u_(k-1)| <= fraction v_max`` per leg (R8 C2 default 0.25, spec 134)."""
    guard_fraction_per_period: float = 0.25
    """Limit of a leg whose change has the sign of the F_min guard term this period."""

    def __post_init__(self) -> None:
        for name in ("fraction_per_period", "guard_fraction_per_period"):
            if not 0.0 < getattr(self, name) <= 2.0:
                raise ValueError(f"{name} must be in (0, 2], got {getattr(self, name)!r}")


@dataclass(frozen=True)
class SampleConfirmation:
    """Consecutive samples a load verdict needs at 10 Hz (spec 99.3 '표본 확인 규칙')."""

    above_samples: int = 1
    """(a) friction band ABOVE (grounded); a single sample after a fast lift-off can read
    +23 kN on a leg in the air (hydraulics 18)."""
    below_samples: int = 1
    """(b) friction band BELOW (lifted)."""
    relevel_samples: int = 1
    """(c) READY P5 low-load re-level (and the PROBE abort of P-R8-11). The guard and the
    REANCHOR holds stay at 1 (d)."""

    def __post_init__(self) -> None:
        if min(self.above_samples, self.below_samples, self.relevel_samples) < 1:
            raise ValueError("sample counts must be >= 1")

    @property
    def is_active(self) -> bool:
        return max(self.above_samples, self.below_samples) > 1


@dataclass(frozen=True)
class FastRelevelSettings:
    """R-5 (spec 134, 139 P-9; on in the R8-D1 preset, U-R8-13): P5 on the predicted reading.

    In READY (spec 147 / P-R8-8: the P5 re-level runs in READY, not DONE) and, with
    ``R8Settings.probe_abort_on_low_load``, in PROBE on the legs not being probed (P-R8-11), a
    leg whose lower load estimate falls faster than ``rate_threshold_N_s`` (mean over the last
    ``rate_intervals`` periods, the latest period falling as well) and whose predicted estimate
    ``L - r_hat h T`` is below the P5 threshold re-levels on that one sample. Only the falling
    direction counts, so a single upward 102 Hz sample does not.
    """

    rate_threshold_N_s: float = 20e3
    """ASSUMPTION (spec 139 P-9)."""
    rate_intervals: int = 3
    horizon_periods: int | None = None
    """Prediction horizon ``h`` in periods (P-R8-10, spec 157.2); ``None`` = ``1 + d`` (the
    revision-31 behaviour)."""

    def __post_init__(self) -> None:
        if not self.rate_threshold_N_s > 0.0 or self.rate_intervals < 1:
            raise ValueError("rate_threshold_N_s must be > 0 and rate_intervals >= 1")
        horizon = self.horizon_periods
        if horizon is not None and (isinstance(horizon, bool) or not isinstance(horizon, int)
                                    or horizon < 1):
            raise ValueError(f"horizon_periods must be an int >= 1 or None, got {horizon!r}")


class ReapproachMode(StrEnum):
    """How a lifted leg is driven back to the floor (:class:`LiftedReapproachSettings`)."""

    LEG = "leg"
    """P-R8-12 (spec rev. 33 172.1): the lifted leg alone at ``speed_fraction v_max``, the
    twist and guard terms held at zero."""
    TWIST = "twist"
    """P-R8-13 (spec rev. 34 174.4): the twist and guard terms replaced by the twist mode toward
    the lifted leg, the fastest leg at ``twist_speed_fraction v_max``."""


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


REAPPROACH_WINDOW_TOLERANCE_S = 1e-9
"""Sample times are sums of 0.1 s steps; a start exactly one window after the end is outside
(the rule RT harness ``r51_reapp_closed_loop.py`` compares the same way)."""


def _is_inside_reapproach_window(
    t_s: float, last_end_s: float | None, window_s: float | None
) -> bool:
    if window_s is None or last_end_s is None:
        return False
    return t_s - last_end_s < window_s - REAPPROACH_WINDOW_TOLERANCE_S


@dataclass(frozen=True)
class LiftedReapproachSettings:
    """Re-approach of a low-load or lifted leg (P-R8-13, spec rev. 34 174.4 / 179.1, U-R8-21;
    start level P-S8-5, spec rev. 42 212.10, U-S8-9).

    Once the machine is lifted, a touched leg that is low-load (lower load estimate below
    ``load_fraction_of_F_min F_min``, 1.4 ``F_min`` in the R8 preset) or lifted for
    ``samples`` periods in a row (LEVEL, DONE, PROBE or
    READY; never the leg being probed or re-grounded) starts a re-approach (event
    ``leg_reapproach_start:<leg>``). READY, DONE and PROBE go back to LEVEL as the P5 re-level
    does, and no DONE is declared while it is active. ``single_leg``: while one leg
    re-approaches, no other leg starts (the diagonal leg lifting by the rocking would).

    * ``mode`` ``twist`` (P-R8-13, the default): the twist and guard terms are replaced by
      ``tau_dot = sign(n_j) twist_speed_fraction v_max / max|n|`` (``j`` = the lifted leg), so
      the fastest leg moves at ``twist_speed_fraction v_max`` and the lifted corner closes about
      3.8 times faster than by its own leg (spec 173.2); the attitude and heave terms stay. A
      period in which a grounded leg this twist retracts (FR, RL for RR) reads below ``F_min +
      protect_margin_N`` (lower estimate) has ``tau_dot = 0``.
    * ``mode`` ``leg`` (P-R8-12, :meth:`leg_mode`): the lifted leg alone at
      ``speed_fraction v_max`` with the twist and guard terms held at zero.

    It ends after ``exit_samples`` samples in a row at or above ``F_min + exit_margin_N``
    (``leg_reapproach_contact:<leg>``), or after ``max_travel_m`` of motor stroke or (P-S9-10,
    spec rev. 57 285, U-S9-C4) ``max_duration_s`` of time
    (``WARN_LEG_REAPPROACH_NO_CONTACT:<leg>``; the leg then stays on the guard path until it
    reads ``F_min`` again).

    Re-trigger rule RT (P-S8-16, spec rev. 52 228.3, U-S8-49), measured from the end of the
    previous re-approach (any outcome) and its leg's twist sign:

    * ``opposite_window_s``: a start on the other diagonal (twist sign differs) inside this
      window also needs the lower load estimate below ``opposite_strong_level_N`` on
      ``opposite_strong_samples`` samples in a row; otherwise it is deferred (event
      ``leg_reapproach_deferred:<leg>`` once per deferred stretch) and the guard path acts.
    * ``retrigger_window_s``: a re-approach started inside this window is a re-trigger and
      runs at ``retrigger_speed_factor`` times the speed (twist and leg mode).

    The class defaults turn both off (the P-R8-13 behaviour, bit-identical); every new key has
    a class-level default so controllers unpickled from older code read "off".
    """

    enable: bool = False
    mode: ReapproachMode = ReapproachMode.TWIST
    load_fraction_of_F_min: float = 0.5
    """Start level as a fraction of ``F_min``, in (0, 2]. Default ASSUMPTION (spec 172.5):
    4.7 kN, below the 10.75 kN G4 minimum. The R8 preset uses 1.4 (13.2 kN, U-S8-9, spec
    rev. 43 213.3.2): with seal friction the low-load leg must start moving before its lower
    bound falls under ``F_min / 2``, or the G4 minimum drops below ``F_min``."""
    samples: int | None = 1
    """Consecutive low samples to start (spec 174.4: 1); ``None`` =
    ``SampleConfirmation.relevel_samples`` (P-R8-12: 2)."""
    single_leg: bool = True
    exit_margin_N: float = 5000.0
    """ASSUMPTION (spec 179.4): the exit level is ``F_min`` plus this (the guard margin)."""
    exit_samples: int = 3
    """ASSUMPTION (spec 179.4): consecutive samples at the exit level, so a contact in one
    rocking half-period does not end it (P-R8-12 chattered on 1 sample, spec 173.1)."""
    twist_speed_fraction: float = 0.25
    """ASSUMPTION (spec 179.4): fastest leg of the twist re-approach; 0.3 leaves RL 15.5 kN,
    0.35 lifts RL (spec 174.2)."""
    protect_margin_N: float = 5000.0
    """ASSUMPTION (spec 179.4): twist mode holds ``tau_dot`` at zero while a grounded leg it
    retracts reads below ``F_min`` plus this. The protected legs are only those the twist
    retracts, ``sign(n_i) != sign(n_j)`` (FR and RL when RR lifted; spec rev. 35 183 #1,
    U-R8-25, the revised 174.4 wording): the diagonal leg is extended and gains load."""
    speed_fraction: float = 0.25
    """Leg mode: ASSUMPTION (spec 172.5), the R1 re-approach speed of TOUCH (5.23 mm/s)."""
    max_travel_m: float = 0.04
    """ASSUMPTION (spec 172.5): the R-2 touch window."""
    retrigger_window_s: float | None = None
    """RT 2: a start within this time after the previous end is a re-trigger; ``None`` = off."""
    retrigger_speed_factor: float = 1.0
    """RT 2: speed factor of a re-trigger, in (0, 1]."""
    opposite_window_s: float | None = None
    """RT 1: window of the other-diagonal confirmation; ``None`` = off."""
    opposite_strong_level_N: float = 0.0
    """RT 1: the lower load estimate must be below this (0 N: lifted beyond the seal band)."""
    opposite_strong_samples: int = 2
    """RT 1: consecutive samples below ``opposite_strong_level_N``."""
    max_duration_s: float | None = None
    """P-S9-10 (spec rev. 57 283.3 / 285, U-S9-C4): a re-approach still active this long after
    its start ends as ``no_contact`` (the twist protection can hold ``tau_dot`` at zero for good
    when two legs lift together, so ``max_travel_m`` is never reached); ``None`` = off."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ReapproachMode(self.mode))
        if not 0.0 < self.load_fraction_of_F_min <= 2.0:
            raise ValueError("load_fraction_of_F_min must be in (0, 2]")
        if self.samples is not None and not _is_positive_int(self.samples):
            raise ValueError(f"samples must be an int >= 1 or None, got {self.samples!r}")
        if not _is_positive_int(self.exit_samples):
            raise ValueError(f"exit_samples must be an int >= 1, got {self.exit_samples!r}")
        if not self.exit_margin_N >= 0.0 or not self.protect_margin_N >= 0.0:
            raise ValueError("exit_margin_N and protect_margin_N must be >= 0")
        if not 0.0 < self.speed_fraction <= 1.0:
            raise ValueError("speed_fraction must be in (0, 1]")
        if not 0.0 < self.twist_speed_fraction <= 1.0:
            raise ValueError("twist_speed_fraction must be in (0, 1]")
        if not self.max_travel_m > 0.0:
            raise ValueError("max_travel_m must be > 0")
        for name in ("retrigger_window_s", "opposite_window_s", "max_duration_s"):
            window_s = getattr(self, name)
            if window_s is not None and not window_s > 0.0:
                raise ValueError(f"{name} must be > 0 or None, got {window_s!r}")
        if not 0.0 < self.retrigger_speed_factor <= 1.0:
            raise ValueError("retrigger_speed_factor must be in (0, 1]")
        if not _is_positive_int(self.opposite_strong_samples):
            raise ValueError(
                "opposite_strong_samples must be an int >= 1, "
                f"got {self.opposite_strong_samples!r}"
            )

    def has_run_too_long(self, t_s: float, start_s: float) -> bool:
        """P-S9-10: a run started at ``start_s`` has reached ``max_duration_s`` at ``t_s``."""
        if self.max_duration_s is None:
            return False
        return t_s - start_s >= self.max_duration_s - REAPPROACH_WINDOW_TOLERANCE_S

    def is_retrigger(self, t_s: float, last_end_s: float | None) -> bool:
        """RT 2: a start at ``t_s`` falls inside the re-trigger window of the last end."""
        return _is_inside_reapproach_window(t_s, last_end_s, self.retrigger_window_s)

    def needs_strong_confirmation(
        self, t_s: float, last_end_s: float | None, last_sign: float, leg_sign: float
    ) -> bool:
        """RT 1: a start at ``t_s`` on a leg of twist sign ``leg_sign`` is on the other
        diagonal of the last re-approach (``last_sign``) inside the opposite window."""
        is_inside = _is_inside_reapproach_window(t_s, last_end_s, self.opposite_window_s)
        return is_inside and leg_sign != last_sign

    @classmethod
    def leg_mode(cls) -> LiftedReapproachSettings:
        """P-R8-12 as revision 33 ran it (on): the lifted leg alone at 0.25 ``v_max``, start on
        the P5 sample count, end on one sample at ``F_min``, several legs at once."""
        return cls(
            enable=True,
            mode=ReapproachMode.LEG,
            samples=None,
            single_leg=False,
            exit_margin_N=0.0,
            exit_samples=1,
        )


@dataclass(frozen=True)
class R8Settings:
    """10 Hz / output delay changes of spec rev. 26 101 (3)-(9) and rev. 30 139 (C2 R8-D1).

    Every default is the R7 behaviour, so ``R8Settings()`` changes nothing;
    :meth:`C2Config.with_10hz_d1` sets the decided values. Only the start-IMU form (C2,
    U-R8-6) exists: the attitude loop reads the IMU filter at ``t_k`` like everything else.
    """

    output_delay_periods: int = 0
    """``d``: the command computed from the samples of ``t_k`` is output at ``t_(k+d)``
    (output buffer of ``d``; U-R8-2 = 1). Run the runner with ``command_delay_periods = 0``
    then, or the delay counts twice."""
    imu_sample_period_s: float | None = None
    """The attitude low-pass runs on ``Measurements.imu_specific_force_samples_m_s2`` at this
    period (P-3: 0.01 s); ``None`` = once per control period on the period mean (R7)."""
    increment_limit: IncrementLimit | None = None
    """Replaces ``output_ramp_time_s`` (which must then be ``None``)."""
    touch_window_m: float | None = None
    """R-2: before a leg has seen its touch load, it extends at ``touch_window_speed_fraction``
    once its motor stroke is within this distance of the level-floor touch extension."""
    touch_window_speed_fraction: float = 0.5
    touch_free_air_min_travel_m: float | None = None
    """P-S8-6 (spec rev. 43 213.3.1 / 213.8, U-S8-11), combined judge only: the free-air
    reference of a leg takes only the TOUCH samples whose motor stroke has advanced at least
    this far since TOUCH entry (seal friction reversed to the extending side), for
    ``thresholds.free_air_window_s`` from its first such sample, and the leg rod weight is
    ``C2Geometry.rod_weight_N``. ``None`` = the R7 rule (every sample from TOUCH entry, the
    scalar ``thresholds.rod_weight_N``)."""
    touch_free_air_min_samples: int = 1
    """P-S8-6: a leg is judged for touchdown only once its free-air reference holds this many
    samples (before that its touchdown load is ``-inf``)."""
    touch_seen_samples: int = 1
    """P-S8-6, combined judge only: ``touch_seen`` (the slow approach) latches after this many
    touchdown-load samples in a row; 1 = the R7 latch on one sample."""
    confirmation: SampleConfirmation = field(default_factory=SampleConfirmation)
    end_slowdown_window_m: float | None = None
    """Spec 99.3: within this distance below ``soft end - 10 mm`` the leg speeds are scaled so
    that no extending leg there exceeds ``end_slowdown_speed_fraction`` of ``v_max``."""
    end_slowdown_speed_fraction: float = 0.25
    twist_gain_reference: TwistGainReference = TwistGainReference.NOMINAL
    pre_probe_stiffness_scale: float = 1.0
    """Stiffness scale before the first probe (the R8-D1 preset: 1.2, spec 143 / 149 P-R8-1:
    a locked leg is about 20 % stiffer than ``k_nom`` through its rod-side chamber)."""
    measured_stiffness_scale_min: float | None = 1.0
    """Lower bound of the measured scale (ASSUMPTION, spec 144.3): the gains never rise above
    the ``k_nom`` design, the only stiffness the linear checks covered from below.
    ``None`` = no bound."""
    measured_stiffness_scale_max: float | None = 1.5
    """Upper bound of the measured scale (ASSUMPTION, spec 144.3, U-R8-11): above 1.5 the
    attitude channel limits the margin anyway and lower gains only slow the READY recovery.
    ``None`` = no bound."""
    stiffness_warning_range: tuple[float, float] = (0.8, 2.3)
    """A raw median ratio outside this range gives ``WARN_PROBE_STIFFNESS_OUT_OF_RANGE``
    (spec 144.3: stiffness outside the verified range). Upper 2.3: ASSUMPTION (spec rev. 35
    188.2 P-R8-16), beta 1.6 GPa with L1-R reads 2.17; 1.5 before. Independent of the scale
    bound ``measured_stiffness_scale_max`` (still 1.5)."""
    fast_relevel: FastRelevelSettings | None = None
    is_instant_sampling: bool = False
    """Pressures are 10 Hz instantaneous samples: the meta marks the 345 bar warning as a
    quasi-static watch (spec 99.3, 101 (9))."""
    check_attitude_from_raw_tilt: bool = False
    """P-R8-9 (spec 158.1): ``(phi_c, theta_c)`` = mean of the IMU-rate raw tilt over the last
    ``target.check_average_s``, starting no earlier than ``target.check_quiet_after_motion_s``
    after the last nonzero leg command; CHECK is extended until that window is full
    (``target.check_max_s`` at most). ``False`` = mean of the filtered attitude (R7, rev. 31).
    Acts only with ``imu_sample_period_s`` (no IMU-rate samples = the R7 path, spec 158.1)."""
    probe_abort_on_low_load: bool = False
    """P-R8-11 (spec 159.2, U-R8-14): in PROBE the READY P5 rule (and R-5 when on) watches the
    legs not being probed; a hit stops the probe and re-levels (``probe_aborted_low_load``)."""
    lifted_reapproach: LiftedReapproachSettings = field(
        default_factory=LiftedReapproachSettings
    )
    """P-R8-13 (spec rev. 34 174.4, U-R8-21; P-R8-12 = :meth:`LiftedReapproachSettings.
    leg_mode`); off by default."""

    def __post_init__(self) -> None:
        delay = self.output_delay_periods
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
            raise ValueError(f"output_delay_periods must be an int >= 0, got {delay!r}")
        if self.imu_sample_period_s is not None and not self.imu_sample_period_s > 0.0:
            raise ValueError("imu_sample_period_s must be > 0 or None")
        if not 0.0 < self.touch_window_speed_fraction <= 1.0:
            raise ValueError("touch_window_speed_fraction must be in (0, 1]")
        min_travel = self.touch_free_air_min_travel_m
        if min_travel is not None and not min_travel > 0.0:
            raise ValueError("touch_free_air_min_travel_m must be > 0 or None")
        for name in ("touch_free_air_min_samples", "touch_seen_samples"):
            value = getattr(self, name)
            if not _is_positive_int(value):
                raise ValueError(f"{name} must be an int >= 1, got {value!r}")
        if not 0.0 < self.end_slowdown_speed_fraction <= 1.0:
            raise ValueError("end_slowdown_speed_fraction must be in (0, 1]")
        if not self.pre_probe_stiffness_scale > 0.0:
            raise ValueError("pre_probe_stiffness_scale must be > 0")
        scale_min = self.measured_stiffness_scale_min
        if scale_min is not None and not scale_min > 0.0:
            raise ValueError("measured_stiffness_scale_min must be > 0 or None")
        scale_max = self.measured_stiffness_scale_max
        if scale_max is not None:
            if not scale_max > 0.0:
                raise ValueError("measured_stiffness_scale_max must be > 0 or None")
            if scale_min is not None and scale_max < scale_min:
                raise ValueError("measured_stiffness_scale_max must be >= the minimum")
        warning_low, warning_high = self.stiffness_warning_range
        if not 0.0 < warning_low <= warning_high:
            raise ValueError("stiffness_warning_range must be (low, high) with 0 < low <= high")
        object.__setattr__(
            self, "twist_gain_reference", TwistGainReference(self.twist_gain_reference)
        )

    @property
    def is_active(self) -> bool:
        """Anything differs from R7."""
        return self != R8Settings()

    @property
    def uses_raw_check_attitude(self) -> bool:
        """P-R8-9 is in force: switched on and IMU-rate samples to average."""
        return self.check_attitude_from_raw_tilt and self.imu_sample_period_s is not None

    def to_meta(self) -> dict[str, Any]:
        meta = asdict(self)
        meta["twist_gain_reference"] = str(self.twist_gain_reference)
        return meta


R8_PERIOD_S = 0.1
"""Pressure, stroke and valve output period (user decision 2026-10-22, U-R8-10)."""
R8_IMU_SAMPLE_PERIOD_S = 0.01
"""IMU 100 Hz, its own path (Q-R4)."""
R8_D1_C2_GAINS = {
    "attitude_kp_1_s": 0.2,
    "attitude_ki_1_s2": 0.01,
    "twist_ktw_1_s": 0.5,
    "guard_kg_1_s": 0.15,
}
"""Spec 136 C2 column (U-R8-7: guard 0.15)."""
R8_D1_ATTITUDE_TIME_CONSTANT_S = 0.8
R8_D1_TWIST_LOAD_TIME_CONSTANT_S = 0.2
R8_ZERO_HOLD_S = 1.0
"""R-3: 10 samples at 10 Hz."""
R8_ZERO_HOLD_STD_N = (730.0, 730.0, 530.0, 530.0)
"""R-3: ``1.76 sigma_0`` front / rear (spec 99.3)."""
R8_D1_PRE_PROBE_STIFFNESS_SCALE = 1.2
"""Spec 143 / 149 P-R8-1: the twist and guard gains before the first probe are 1 / 1.2."""
R8_D1_MEASURED_STIFFNESS_SCALE_MAX = 1.5
"""Spec 144.3 / 149 P-R8-3 (ASSUMPTION, U-R8-11 accepted 2026-10-24)."""
R8_D1_STIFFNESS_WARNING_RANGE = (0.8, 2.3)
"""Spec rev. 35 188.2 P-R8-16 (ASSUMPTION): raw probe ratio range without a warning; the
upper end holds beta 1.6 GPa (raw 2.17) plus a margin. Was (0.8, 1.5)."""
MIN_STIFFNESS_SCALE_LEGS = 3
"""Spec 144.3: a probe round updates the measured scale only with at least this many legs the
stiffness cue calls grounded (3 legs of the 4-point support are representative)."""
STIFFNESS_SCALE_DENOMINATOR = "load_sensitivity_diag_N_m (head-only k_nom)"
"""Meta: the nominal ``S_ii`` the probe-measured ``S_ii`` is divided by (spec 144.2)."""
R8_D1_FAST_RELEVEL_HORIZON_PERIODS = 4
"""P-R8-10 (ASSUMPTION, spec 157.2 / 163.4): ``1 + d + ceil(tau_v / T)`` plus one period of
sample phase; to be confirmed by the harness (3 against 4) and the Chrono re-run."""
R8_D1_TOUCH_FREE_AIR_MIN_TRAVEL_M = 0.5e-3
"""P-S8-6 (ASSUMPTION, spec rev. 43 213.9): travel that reverses the seal friction, stick band
/ oil stiffness ~ 16 kN / 3e7 N/m."""
R8_D1_TOUCH_FREE_AIR_MIN_SAMPLES = 3
"""P-S8-6 (ASSUMPTION, spec 213.9): a stable median."""
R8_D1_TOUCH_SEEN_SAMPLES = 2
"""P-S8-6 (ASSUMPTION, spec 213.9): the R8 sample-confirmation rule."""
R8_D1_REAPPROACH_LOAD_FRACTION_OF_F_MIN = 1.4
"""P-S8-5 (U-S8-9, spec rev. 42 212.4 / rev. 43 213.3.2): re-approach start level."""
R8_D1_REAPPROACH_RETRIGGER_WINDOW_S = 2.0
"""P-S8-16 rule RT (spec rev. 52 228.3, U-S8-45 / U-S8-49, ASSUMPTION): covers the same-diagonal
closing runs after an event (0.4..1.6 s); 1.5..3.0 s gave the same reduced result."""
R8_D1_REAPPROACH_RETRIGGER_SPEED_FACTOR = 0.6
"""P-S8-16 (spec rev. 52 228.3, ASSUMPTION): between 0.5 (pair time up) and 0.7 (adjacent
gap up) on the reduced closed loop."""
R8_D1_REAPPROACH_OPPOSITE_WINDOW_S = 0.8
"""P-S8-16 (spec rev. 52 228.3, U-S8-45 candidate T_3, ASSUMPTION): 0.5..1.2 s gave the same
reduced result."""
R8_D1_REAPPROACH_OPPOSITE_STRONG_LEVEL_N = 0.0
"""P-S8-16 (spec rev. 52 228.3, U-S8-45): lower bound below zero = surely lifted."""
R8_D1_REAPPROACH_OPPOSITE_STRONG_SAMPLES = 2
"""P-S8-16 (spec rev. 52 228.3): 2 and 3 gave the same result, 1 failed 3 of 28."""
R8_D1_REAPPROACH_MAX_DURATION_S = 10.0
"""P-S9-10 (spec rev. 57 283.3 / 285, U-S9-C4 2026-10-26): the longest re-approach of the S8
records (1,068 runs of ``07_results/S8``, c37 bundle E and ML 768 included) lasted 1.8 s."""
R8_D1_SETTINGS = R8Settings(
    output_delay_periods=1,
    imu_sample_period_s=R8_IMU_SAMPLE_PERIOD_S,
    increment_limit=IncrementLimit(),
    touch_window_m=0.04,
    touch_window_speed_fraction=0.5,
    touch_free_air_min_travel_m=R8_D1_TOUCH_FREE_AIR_MIN_TRAVEL_M,
    touch_free_air_min_samples=R8_D1_TOUCH_FREE_AIR_MIN_SAMPLES,
    touch_seen_samples=R8_D1_TOUCH_SEEN_SAMPLES,
    confirmation=SampleConfirmation(above_samples=3, below_samples=2, relevel_samples=2),
    end_slowdown_window_m=0.015,
    end_slowdown_speed_fraction=0.25,
    twist_gain_reference=TwistGainReference.MEASURED_SII,
    pre_probe_stiffness_scale=R8_D1_PRE_PROBE_STIFFNESS_SCALE,
    measured_stiffness_scale_min=1.0,
    measured_stiffness_scale_max=R8_D1_MEASURED_STIFFNESS_SCALE_MAX,
    stiffness_warning_range=R8_D1_STIFFNESS_WARNING_RANGE,
    fast_relevel=FastRelevelSettings(horizon_periods=R8_D1_FAST_RELEVEL_HORIZON_PERIODS),
    is_instant_sampling=True,
    check_attitude_from_raw_tilt=True,
    probe_abort_on_low_load=True,
    lifted_reapproach=LiftedReapproachSettings(
        enable=True,
        load_fraction_of_F_min=R8_D1_REAPPROACH_LOAD_FRACTION_OF_F_MIN,
        retrigger_window_s=R8_D1_REAPPROACH_RETRIGGER_WINDOW_S,
        retrigger_speed_factor=R8_D1_REAPPROACH_RETRIGGER_SPEED_FACTOR,
        opposite_window_s=R8_D1_REAPPROACH_OPPOSITE_WINDOW_S,
        opposite_strong_level_N=R8_D1_REAPPROACH_OPPOSITE_STRONG_LEVEL_N,
        opposite_strong_samples=R8_D1_REAPPROACH_OPPOSITE_STRONG_SAMPLES,
        max_duration_s=R8_D1_REAPPROACH_MAX_DURATION_S,
    ),
)
"""The R8 part of :meth:`C2Config.with_10hz_d1` (spec 99.3, 136, 139, rev. 31 149, rev. 32
163.1: P-R8-9 raw-tilt CHECK attitude, P-R8-10 R-5 on with horizon 4, P-R8-11 PROBE abort;
rev. 34 174.4: P-R8-13 lifted-leg re-approach in the twist mode, replacing P-R8-12; rev. 43
213.8: P-S8-5 re-approach start at 1.4 ``F_min``, P-S8-6 TOUCH free air from moving samples;
rev. 52 228.3: P-S8-16 re-trigger rule RT; rev. 57 285: P-S9-10 re-approach time limit 10 s)."""
QUASI_STATIC_PRESSURE_NOTE = (
    "10 Hz instantaneous samples: the 345 bar warning sees about 43 % of a heave transient "
    "and hardly any 102 Hz ringing; it is a quasi-static watch, not an overpressure "
    "protection (spec 99.3, U-R8-4)"
)


R5_RELEVEL_LOAD_MARGIN_N = 7000.0
R5_REANCHOR_FLOOR_MARGIN_N = 10e3
PROBE_CORRECTION_SENSITIVITY_N_M = (5.83e6, 5.83e6, 6.98e6, 6.98e6)
"""U63 (spec 63.2): C1 ``S_ii`` (other legs locked after an extension), REXOME35 stiffness."""
SUPPORT_PAD_STIFFNESS_R6_N_M = (2.166e8, 2.166e8, 2.051e8, 2.051e8)
"""Spec 64.2: GE1' series stiffness ``k_s`` per leg (dynamics 5.11)."""


def _r6_probe_settings() -> ProbeSettings:
    """R6 probe: the original +d -> E -> -d -> R order (spec 65.1) with the U63 corrections."""
    return ProbeSettings(
        sequence=ProbeSequence.EXTEND_RETRACT,
        sensitivity=ProbeSensitivity.MEASURED_IF_GROUNDED,
    )


SOIL_PLATEAU_WINDOW_MAX_SAMPLES = 200
"""Memory bound of the S-1 window (as the reference rules ``04_scripts/03_control/s9/
s9_soil_rules.py``). Every window sample has a mean leg speed of at least 0.15 ``v_max``, so
200 samples span >= 63 mm of mean stroke and the 10 mm tail never reaches the bound."""
SOIL_EVENT_MODE_START = "soil_mode_start"
SOIL_EVENT_LIFTOFF_CONFIRMED = "crawler_liftoff_confirmed"
SOIL_EVENT_CLEARANCE_BIAS = "INFO_CLEARANCE_BIAS"
SOIL_EVENT_LIFTOFF_UNCONFIRMED = "WARN_CRAWLER_LIFTOFF_UNCONFIRMED"
SOIL_EVENT_WEIGHT_MISMATCH = "WARN_WEIGHT_MISMATCH"


@dataclass(frozen=True)
class SoilResponseSettings:
    """C2 soil response S-1 .. S-5 (spec rev. 57 282.4 / 285 P-S9-1, U-S9-C1 / C2 / C6).

    On soft soil the pads sink while the crawler still carries weight, so the stroke-based
    crawler clearance (rigid floor) overstates the real one: the crawler-zone latch would
    release and the attitude loop could retract legs with the crawler still loaded.

    * S-1 lift-off confirmation (LOC): in LEVEL before the LOC, a window of consecutive
      periods whose previous applied output retracted no leg and averaged at least
      ``plateau_mean_speed_fraction v_max``; once its mean motor stroke has advanced
      ``plateau_window_m``, the load sum ``sum F_i`` regressed on the mean stroke over the
      shortest such tail rises by at most ``plateau_rise_max_N`` per ``plateau_window_m`` and
      averages at least ``plausibility_fraction W_ref`` -> ``crawler_liftoff_confirmed``.
    * S-2 soil mode: a crawler-zone release without the LOC keeps the zone latched instead
      (``soil_mode_start``); every leg then extends at least ``push_speed_fraction v_max``
      (pure heave added, rescaled to ``v_max``) and DONE waits for the LOC.
    * S-3 corner bias: at the LOC ``b_k = c_k(t_P) - (rho_k - min rho)``, ``rho_k = y_k d_phi
      - x_k d_theta`` (raw-tilt attitude change since the crawler settle), clipped at zero and
      dropped while the smallest unbiased corner clearance ``c_min(t_P)`` is within
      ``corner_bias_deadzone_m`` (user decision 2026-10-26: no IMU); every control use of the
      crawler-corner clearance reads ``c_k - b_k`` afterwards.
    * S-4 limit: ``max_push_m`` of mean motor stroke in soil mode without the LOC ->
      ``WARN_CRAWLER_LIFTOFF_UNCONFIRMED`` and FAULT.
    * S-5 record: ``W_hat / W_ref`` outside ``weight_record_range`` -> ``WARN_WEIGHT_MISMATCH``
      (no command effect).

    Every key has a class-level default (``enable`` False), so configs unpickled from older
    code read "off" and run revision 56 bit for bit.
    """

    enable: bool = False
    plateau_window_m: float = 0.010
    """S-1 mean motor-stroke progress of the plateau window."""
    plateau_mean_speed_fraction: float = 0.15
    """S-1 minimum mean leg speed of a window period, fraction of ``v_max``."""
    plateau_rise_max_N: float = 2000.0
    """S-1 largest load-sum rise over ``plateau_window_m`` on the plateau (U-S9-C2)."""
    plausibility_fraction: float = 0.85
    """S-1 window-mean load sum at least this fraction of ``W_ref``."""
    push_speed_fraction: float = 0.25
    """S-2 smallest leg speed in soil mode, fraction of ``v_max``."""
    corner_bias_deadzone_m: float = 0.020
    """S-3 no bias while the smallest unbiased corner clearance at ``t_P`` is at most this."""
    max_push_m: float = 0.15
    """S-4 mean motor-stroke increase in soil mode without the LOC (observed <= 93.7 mm)."""
    weight_record_range: tuple[float, float] = (0.9, 1.15)
    """S-5 ``W_hat / W_ref`` range without a warning (ASSUMPTION, U-S9-C6: record only)."""
    settle_tilt_samples: int = 10
    """S-3 without CHECK: periods of raw tilt at the TOUCH start that give the settle attitude."""

    def __post_init__(self) -> None:
        for name in ("plateau_window_m", "max_push_m"):
            if not getattr(self, name) > 0.0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)!r}")
        for name in ("plateau_mean_speed_fraction", "push_speed_fraction"):
            if not 0.0 < getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in (0, 1], got {getattr(self, name)!r}")
        if not self.plateau_rise_max_N >= 0.0 or not self.corner_bias_deadzone_m >= 0.0:
            raise ValueError("plateau_rise_max_N and corner_bias_deadzone_m must be >= 0")
        if not self.plausibility_fraction > 0.0:
            raise ValueError("plausibility_fraction must be > 0")
        low, high = self.weight_record_range
        if not 0.0 < low <= high:
            raise ValueError("weight_record_range must be (low, high) with 0 < low <= high")
        object.__setattr__(self, "weight_record_range", (float(low), float(high)))
        if not _is_positive_int(self.settle_tilt_samples):
            raise ValueError(
                f"settle_tilt_samples must be an int >= 1, got {self.settle_tilt_samples!r}"
            )

    def to_meta(self) -> dict[str, Any]:
        meta = asdict(self)
        meta["weight_record_range"] = list(self.weight_record_range)
        return meta


@dataclass(frozen=True)
class C2Config:
    """Complete C2 setting; the defaults are the decided design values."""

    gains: C2Gains = field(default_factory=C2Gains)
    filters: C2Filters = field(default_factory=C2Filters)
    thresholds: C2Thresholds = field(default_factory=C2Thresholds)
    probe: ProbeSettings = field(default_factory=_r6_probe_settings)
    """Probe of the combined judge (``control/ground_contact.py``); R6: the U63 corrections."""
    reanchor: ReanchorSettings = field(default_factory=ReanchorSettings)
    target: TargetSettings = field(default_factory=TargetSettings)
    contact: ContactJudge = ContactJudge.COMBINED
    """Combined by default: the probe after levelling is part of the base procedure (D4)."""
    initial_seal_band_N: float = 13e3
    """``F_band`` at the start of a run (decision D5: design limit 12 kN + 3 sigma)."""
    output_ramp_time_s: float | None = 0.1
    """Output ramp ``|du| <= v_max T / ramp`` (design 14.7); ``None`` turns it off (L2 valve).

    :meth:`C2Controller.from_params` without a config takes YAML ``actuator.command_ramp_s``
    instead, so the controller ramp matches the actuator command limit."""
    period_s: float = DEFAULT_CONTROL_PERIOD_S
    standstill_gate: StandstillGateSettings = field(default_factory=StandstillGateSettings)
    """GE1' standstill gate (spec 38, U35-a); its ``sigma_g`` is ``target.gyro_noise_std_rad_s``."""
    rod_stroke_fallback: RodStrokeFallback = RodStrokeFallback.OPERATING_OIL_COLUMN
    """Rod stroke when ``stroke_corrected_m`` is missing (R5: L1 operating oil column)."""
    load_estimate: LoadEstimate = LoadEstimate.NET
    """R6-P (P-2, U43): ``net`` uses the rod-side pressure when measured; ``head_only`` = R5."""
    two_pressure: TwoPressureSettings = field(default_factory=TwoPressureSettings)
    """R6-P diagnosis, fallback and rod-side watch thresholds (spec 64.2)."""
    geometry_judge: GeometryJudgeSettings = field(default_factory=GeometryJudgeSettings)
    lock_tail: LockTailSettings = field(default_factory=LockTailSettings)
    probe_correction_sensitivity_N_m: tuple[float, ...] | None = PROBE_CORRECTION_SENSITIVITY_N_M
    """U63: ``S_ii`` of the probe corrections; ``None`` = the nominal load sensitivity."""
    support_pad_stiffness_N_m: tuple[float, ...] = SUPPORT_PAD_STIFFNESS_R6_N_M
    """GE1' deflection term ``F / k_s`` per leg (R5: 2.17e8 N/m on every leg)."""
    zero_calibration: ZeroCalibrationSettings = field(default_factory=ZeroCalibrationSettings)
    """E-3 (U71): CHECK airborne round-trip zero calibration (default on; R5 presets off)."""
    pressure_offset_allowance_N: tuple[float, ...] = (0.0,) * LEG_COUNT
    """E-6: lower-bound deduction per leg (guard, P5, Q2, REANCHOR stop, ABOVE); default 0.
    A leg whose calibration fails takes the larger of this and the failure allowance."""
    r8: R8Settings = field(default_factory=R8Settings)
    """10 Hz / output-delay behaviour (default R7; :meth:`with_10hz_d1`)."""
    soil: SoilResponseSettings = SoilResponseSettings()
    """Soil response S-1 .. S-5 (spec rev. 57 285); off by default. A plain class-level default,
    so configs unpickled from older code read "off"."""

    def __post_init__(self) -> None:
        if not self.period_s > 0.0:
            raise ValueError(f"period_s must be > 0, got {self.period_s!r}")
        if self.output_ramp_time_s is not None and not self.output_ramp_time_s > 0.0:
            raise ValueError(
                f"output_ramp_time_s must be > 0 or None, got {self.output_ramp_time_s!r}"
            )
        if self.r8.increment_limit is not None and self.output_ramp_time_s is not None:
            raise ValueError(
                "r8.increment_limit replaces the soft ramp: set output_ramp_time_s to None"
            )
        object.__setattr__(self, "contact", ContactJudge(self.contact))
        object.__setattr__(self, "rod_stroke_fallback", RodStrokeFallback(self.rod_stroke_fallback))
        object.__setattr__(self, "load_estimate", LoadEstimate(self.load_estimate))
        allowance = tuple(float(value) for value in self.pressure_offset_allowance_N)
        if len(allowance) != LEG_COUNT or min(allowance) < 0.0:
            raise ValueError(
                f"pressure_offset_allowance_N: expected {LEG_COUNT} values >= 0, "
                f"got {self.pressure_offset_allowance_N!r}"
            )
        object.__setattr__(self, "pressure_offset_allowance_N", allowance)

    def with_r6_behaviour(self) -> C2Config:
        """Copy with every R7 change turned off (R6 replays).

        REANCHOR applies on both pitch directions again (``ReanchorDirection.BOTH``, spec 82.5)
        and the D8 / relative diamonds are symmetric (``relative_pitch_span_nose_up_rad``
        ``None``, spec 86.3). Only those two fields are touched.
        """
        reanchor = replace(self.reanchor, direction=ReanchorDirection.BOTH)
        target = replace(self.target, relative_pitch_span_nose_up_rad=None)
        return replace(self, reanchor=reanchor, target=target)

    def with_r8_diagnostics(self) -> C2Config:
        """Copy with the 10 Hz (R8) pressure-diagnosis constants (spec rev. 29 126 #3).

        Only ``two_pressure`` is touched (:meth:`TwoPressureSettings.with_r8_period`: load
        baseline settle 0.5 s / mean 1.5 s, D4 2 samples = 0.2 s, D5 hold 0.5 s, E-5 hold
        30 s). The whole R8-D1 setting (period, gains, filters, limits) is
        :meth:`with_10hz_d1`, which includes this.
        """
        return replace(self, two_pressure=self.two_pressure.with_r8_period())

    def with_lock_valve(self, lock_valve: str, counterbalance: Any | None = None) -> C2Config:
        """Copy whose R6-P diagnosis knows the lock valve of the run (P-S8-11, U-S8-23).

        Only ``two_pressure`` is touched (:meth:`TwoPressureSettings.with_lock_valve`): with
        ``counterbalance`` the D2 extend upper bound and the fallback estimate ``p_r_hat``
        follow the CB rod-side law (spec rev. 46 216.10); ``pilot_check`` is the default.

        Args:
            lock_valve: YAML ``actuator.lock_valve``.
            counterbalance: YAML ``actuator.counterbalance`` (``params.l2b.counterbalance`` of
                the plant parameters), needed for ``counterbalance``.
        """
        two_pressure = self.two_pressure.with_lock_valve(lock_valve, counterbalance)
        return replace(self, two_pressure=two_pressure)

    def with_10hz_d1(self) -> C2Config:
        """Copy with the R8-D1 design C2 (spec rev. 30 136 / 139, user decisions 2026-10-24).

        10 Hz pressures, strokes and valve output, output one period late (``d = 1``), the IMU
        filter at 100 Hz on the IMU samples, A8 attitude gains (Kp 0.2, Ki 0.01, two stages of
        0.8 s), twist gain 0.5 on ``n^T P`` low-passed 0.2 s (the guard keeps the raw reading),
        guard gain 0.15, both divided by the probe-measured stiffness (1.2 ``k_nom`` before
        the first probe, then the median measured / head-only nominal ``S_ii`` bounded to
        [1.0, 1.5], rev. 31 149), and spec 101 (3)-(9):
        increment limit 0.25 ``v_max`` per period instead of the soft ramp (a FAULT stop
        skips it, rev. 31 P-R8-5), R-1 predicted
        REANCHOR stop (horizon ``1 + d``), R-2 touch window 40 mm at 0.5 ``v_max``, sample
        confirmation (ABOVE 3, BELOW 2, P5 2), R-3 zero-calibration hold 1.0 s with the
        chi-square scatter limits, the stroke-end slowdown and the quasi-static 345 bar note;
        the 10 Hz diagnosis constants of :meth:`with_r8_diagnostics`. Spec rev. 32 163.1:
        the CHECK attitude is the mean raw 10 ms tilt after the quiet time (P-R8-9), R-5 is on
        with a 4-period horizon (P-R8-10, U-R8-13) and a low load on a leg not being probed
        stops the probe (P-R8-11, U-R8-14). Spec rev. 34 174.4 (U-R8-21, replacing P-R8-12 of
        rev. 33): a leg that lifts again is re-approached in the twist mode, fastest leg 0.25
        ``v_max``, one leg at a time, started on one low sample and ended on three samples at
        ``F_min + 5 kN`` (P-R8-13, :class:`LiftedReapproachSettings`). Spec rev. 43 213.8:
        the re-approach starts below 1.4 ``F_min`` (P-S8-5, U-S8-9), and the TOUCH free-air
        reference takes only samples after 0.5 mm of travel, judges with 3 of them and
        latches the slow approach on 2 samples in a row (P-S8-6, U-S8-11). Spec rev. 57 285
        (U-S9-C1 / U-S9-C4, 2026-10-26, after the P-S9-9 regression): the soil response
        S-1 .. S-5 is on (:class:`SoilResponseSettings`, the other soil keys of this config
        stay) and a re-approach ends after 10 s (P-S9-10). The start-IMU form only: the late
        IMU read (C1) is not implemented (U-R8-6 = C2).
        """
        config = self.with_r8_diagnostics()
        return replace(
            config,
            soil=replace(config.soil, enable=True),
            period_s=R8_PERIOD_S,
            output_ramp_time_s=None,
            gains=replace(config.gains, **R8_D1_C2_GAINS),
            filters=replace(
                config.filters,
                attitude_time_constant_s=R8_D1_ATTITUDE_TIME_CONSTANT_S,
                twist_load_time_constant_s=R8_D1_TWIST_LOAD_TIME_CONSTANT_S,
            ),
            reanchor=replace(config.reanchor, stop_predictor=StopPredictor.READING_RATE),
            zero_calibration=replace(
                config.zero_calibration,
                hold_s=R8_ZERO_HOLD_S,
                max_hold_std_per_leg_N=R8_ZERO_HOLD_STD_N,
                hold_std_ddof=1,
            ),
            r8=R8_D1_SETTINGS,
        )

    def with_soil_response(self) -> C2Config:
        """Copy of :meth:`with_10hz_d1` with the soil response S-1 .. S-5 on (P-S9-8, spec
        rev. 57 285); the other :class:`SoilResponseSettings` keys of this config stay. Since
        U-S9-C1 the R8 preset has it on as well, so this is :meth:`with_10hz_d1`; it stays as
        the explicit S9 name."""
        return replace(self.with_10hz_d1(), soil=replace(self.soil, enable=True))

    def with_interim_b(self) -> C2Config:
        """Copy with the provisional nose-up limit B: 3.1 deg on the relative nose-up side.

        Provisional B (user decision 2026-10-22, "C first, provisional B"; spec 86.3): the
        relative nose-up half-span of the D8 start check (A1) and the relative diamond (A4) is
        3.1 deg, the nose-down side and the absolute diamond keep 3.2 deg. The return to
        3.2 deg follows ``dynamics_model.md`` 5.13.5 supplements 4 and 5. While B holds, the
        operating mode uses this preset, not the default (``None`` = 3.2 deg). Only
        ``target.relative_pitch_span_nose_up_rad`` is touched; in the verification mode it
        raises ``ValueError`` (spec 90.2).
        """
        target = replace(
            self.target, relative_pitch_span_nose_up_rad=INTERIM_B_NOSE_UP_PITCH_SPAN_RAD
        )
        return replace(self, target=target)

    def with_r5_behaviour(self) -> C2Config:
        """Copy with every R6 change turned off (R5 legacy replays).

        Head-only load reading (the rod-side pressure is ignored, so no diagnosis, fallback or
        rod-side watch), GE2 shadow, no lock tails, the R5 probe sequence and corrections, the
        R5 GE1' stiffness and the R5 margins (re-level 7 kN, REANCHOR floor 10 kN), no zero
        calibration and the 350 bar warning without pre-warning, on top of
        :meth:`with_r6_behaviour`. Only R6 / R7 fields are touched.
        The spec 65.3 stroke constants act through ``min(s_max, 0.6948 m)`` and leave a
        0.68 m plant unchanged.
        """
        r6 = self.with_r6_behaviour()
        thresholds = r6.thresholds
        if thresholds.relevel_load_margin_N == C2Thresholds.relevel_load_margin_N:
            # only the R6 default goes back; an explicit (e.g. R2 / R3 replay) value stays
            thresholds = replace(
                thresholds,
                relevel_load_margin_N=R5_RELEVEL_LOAD_MARGIN_N,
                allow_legacy_relevel_margin=True,
            )
        thresholds = replace(
            thresholds, locked_pressure_warning_margin_Pa=0.0, locked_pressure_prewarning_Pa=None
        )
        reanchor = r6.reanchor
        if reanchor.floor_margin_N == ReanchorSettings.floor_margin_N:
            reanchor = replace(reanchor, floor_margin_N=R5_REANCHOR_FLOOR_MARGIN_N)
        return replace(
            r6,
            thresholds=thresholds,
            reanchor=reanchor,
            probe=replace(
                self.probe,
                sequence=ProbeSequence.EXTEND_RETRACT,
                sensitivity=ProbeSensitivity.NOMINAL,
            ),
            load_estimate=LoadEstimate.HEAD_ONLY,
            two_pressure=replace(self.two_pressure, diagnostics=False),
            geometry_judge=replace(self.geometry_judge, mode=GeometryJudge.SHADOW),
            lock_tail=replace(self.lock_tail, enable=False),
            probe_correction_sensitivity_N_m=None,
            support_pad_stiffness_N_m=(SHADOW_PAD_STIFFNESS_N_M,) * LEG_COUNT,
            zero_calibration=replace(self.zero_calibration, mode=ZeroCalibrationMode.OFF),
        )

    def with_r41_behaviour(self) -> C2Config:
        """Copy with every R5 change of the commands and phases turned off (legacy replays).

        H5a order and band rule, the B1' CHECK extension and checks, and the R4.1 rod-stroke
        fallback, on top of :meth:`with_r5_behaviour`. The GE1' shadow (events only) stays R5.
        Only R5 / R6 fields are touched, so the other settings of this config are kept.
        """
        legacy = self.with_r5_behaviour()
        target = replace(
            legacy.target,
            check_max_s=self.target.check_time_s,  # T_b = check_time_s, no extension
            gyro_bias_max_rate_rms_rad_s=None,
            gyro_bias_plausible_rad_s=None,
        )
        return replace(
            legacy,
            reanchor=replace(legacy.reanchor, after_probe=False),
            probe=replace(legacy.probe, seal_band_rule=SealBandRule.WIDEN_ONLY),
            target=target,
            rod_stroke_fallback=RodStrokeFallback.STROKE_OIL_COLUMN,
        )


# --- geometry ------------------------------------------------------------------------------


STROKE_MEASURABLE_MAX_KEY = "sensors.stroke.measurable_max_m"
LEG_LOCKED_FORCE_LIMIT_KEY = "legs.{leg}.cylinder.locked_force_limit_N"


def _bounded(value: float, lower: float | None, upper: float | None) -> float:
    """``value`` clipped to the bounds that are given (``None`` = no bound on that side)."""
    if lower is not None:
        value = max(value, lower)
    if upper is not None:
        value = min(value, upper)
    return value


def _optional_float(params: Params, key: str, default: float) -> float:
    try:
        return float(params.get(key))
    except ParamsError:
        return default


def _optional_float_or_none(params: Params, key: str) -> float | None:
    try:
        return float(params.get(key))
    except ParamsError:
        return None


def _optional_per_leg(params: Params, key: str) -> NDArray[np.float64] | None:
    """A YAML mapping ``{FL: .., FR: .., RL: .., RR: ..}`` in LEG_ORDER, ``None`` if absent."""
    try:
        by_leg = params.get(key)
    except ParamsError:
        return None
    return np.array([float(by_leg[leg]) for leg in LEG_ORDER])


def _leg_locked_force_limits_N(params: Params, head_area_m2: NDArray[np.float64]) -> NDArray:
    """350 bar head force per leg: ``legs.<leg>.cylinder.locked_force_limit_N`` when the YAML
    has it, else ``actuator.locked_pressure_limit_Pa`` x head area (P-15)."""
    limit_Pa = float(params.get(LOCKED_PRESSURE_LIMIT_KEY))
    limits = []
    for leg, area in zip(LEG_ORDER, head_area_m2, strict=True):
        key = LEG_LOCKED_FORCE_LIMIT_KEY.format(leg=leg)
        limits.append(_optional_float(params, key, limit_Pa * float(area)))
    return np.array(limits)


def _support_matrix(pad_xy_m: NDArray[np.float64]) -> NDArray[np.float64]:
    """``A`` (4x3): pad vertical displacement = A [z, phi, theta] (design section 1)."""
    return np.column_stack([np.ones(len(pad_xy_m)), pad_xy_m[:, 1], -pad_xy_m[:, 0]])


def _twist_vector(support_matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Unit ``n`` with ``A^T n = 0``, sign chosen so that ``n[FL] > 0``."""
    _, _, right_singular = np.linalg.svd(support_matrix.T)
    twist = right_singular[-1]
    return twist / np.linalg.norm(twist) * np.sign(twist[0])


def _load_sensitivity(
    pad_stiffness_N_m: NDArray[np.float64], support_matrix: NDArray[np.float64]
) -> NDArray[np.float64]:
    """dF / d(extension) (4x4) with every leg in contact: ``K - K A (A^T K A)^-1 A^T K``."""
    stiffness = np.diag(pad_stiffness_N_m)
    weighted = support_matrix.T @ stiffness
    return stiffness - weighted.T @ np.linalg.solve(weighted @ support_matrix, weighted)


@dataclass(frozen=True, eq=False)
class C2Geometry:
    """Machine quantities the controller needs, derived from the parameters.

    Attributes:
        pad_xy_m: Pad bottom centres in body xy (4, 2).
        pad_bottom_z_retracted_m: Pad bottom heights, legs retracted (4,).
        support_matrix: ``A`` (4, 3), columns heave, roll, pitch.
        twist_vector: ``n`` (4,), unit, ``A^T n = 0``.
        nominal_pad_stiffness_N_m: ``k_nom``, mean L1 pad stiffness (beta 1.0 GPa).
        load_sensitivity_diag_N_m: ``S_ii`` of the load sensitivity with ``k_nom`` (4,).
        F_min_N: Minimum cylinder force (YAML ``control.F_min_cylinder_N``).
        max_speed_m_s: ``v_max``.
        stroke_max_m: ``s_max``.
        crawler_corners_xy_m: Crawler box corners in body xy (4, 2).
        crawler_bottom_z_m: Crawler bottom height in the CAD pose.
        head_area_m2: Cylinder head area per leg (4,) (pressure -> force; one value is
            broadcast to the four legs, P-15).
        oil_bulk_modulus_Pa: Effective bulk modulus for ``k_oil(e)``.
        oil_dead_length_m: Dead oil column length for ``k_oil(e)``.
        locked_force_limit_N: Head-only force at the locked pressure limit per leg (350 bar x
            head area); READY reports raw head readings above it (P-3).
        annulus_area_m2: Rod-side area per leg (4,) for the net force (0 = no rod side known).
        attitude_sensitivity_rad_m: ``J`` (4, 2), body (roll, pitch) per metre of a single
            leg's extension with ``k_nom`` on every pad (derived).
    """

    pad_xy_m: NDArray[np.float64]
    pad_bottom_z_retracted_m: NDArray[np.float64]
    support_matrix: NDArray[np.float64]
    twist_vector: NDArray[np.float64]
    nominal_pad_stiffness_N_m: float
    load_sensitivity_diag_N_m: NDArray[np.float64]
    F_min_N: float
    max_speed_m_s: float
    stroke_max_m: float
    crawler_corners_xy_m: NDArray[np.float64]
    crawler_bottom_z_m: float
    head_area_m2: NDArray[np.float64]
    oil_bulk_modulus_Pa: float
    oil_dead_length_m: float
    locked_force_limit_N: NDArray[np.float64] = math.inf  # type: ignore[assignment]
    annulus_area_m2: NDArray[np.float64] = 0.0  # type: ignore[assignment]
    stroke_measurable_max_m: float = STROKE_SOFT_MAX_M
    """Stroke sensor end (YAML ``sensors.stroke.measurable_max_m``, spec 65.3)."""
    rod_weight_N: NDArray[np.float64] | None = None
    """``m_rod g`` per leg from YAML ``legs.<leg>.moving_part.mass_kg`` (spec 76.4 (2)):
    zero calibration and the two-pressure monitor; ``None`` = their constants (tests)."""
    rod_lock_pressure_after_retract_Pa: NDArray[np.float64] | None = None
    """YAML ``actuator.rod_side.p_r0_after_retract_Pa`` per leg: the lower end of the fallback
    start after a retraction (P-S8-13); ``None`` = the monitor's constants (tests, old
    pickles)."""
    counterbalance_lag_tau_s: float | None = None
    """YAML ``actuator.rod_side.release_tau_s``: the CB rod-side lag bound of the fallback
    estimate (P-S8-15); ``None`` = the monitor's constant."""
    superstructure_mass_kg: float | None = None
    """YAML superstructure mass of the run's auger level: the D1'' ``nominal`` ``M_eff``
    option (dynamics rev. 41 R41-1); ``None`` = the monitor's constant."""
    imu_lever_arm_m: NDArray[np.float64] | None = None
    """IMU mount C1 minus the superstructure centre of mass of the auger level (body axes):
    the D1'' lever term (P-S8-14 ⑤); ``None`` = the monitor's constant (top level)."""
    attitude_sensitivity_rad_m: NDArray[np.float64] = field(init=False, repr=False)
    _plane_fit: NDArray[np.float64] = field(init=False, repr=False)
    """Pseudo-inverse of ``[1, x, y]`` at the pads (least-squares pad plane)."""
    _support_pinv: NDArray[np.float64] = field(init=False, repr=False)

    @classmethod
    def from_params(cls, params: Params) -> C2Geometry:
        """Derive the controller geometry from the loaded YAML parameters."""
        pad_centres = np.array([leg.pad_bottom_center_retracted_m for leg in params.legs])
        pad_xy = pad_centres[:, :2]
        support_matrix = _support_matrix(pad_xy)
        k_nom = float(np.mean(params.contact.rigid_floor.L1.kn_per_pad_N_m))
        sensitivity = _load_sensitivity(np.full(LEG_COUNT, k_nom), support_matrix)
        (x_min, x_max), (y_min, y_max) = CRAWLER_XY_BOX_M
        corners = np.array([[x_min, y_min], [x_min, y_max], [x_max, y_min], [x_max, y_max]])
        head_area = leg_head_areas_from_params(params)
        return cls(
            pad_xy_m=pad_xy,
            pad_bottom_z_retracted_m=pad_centres[:, 2],
            support_matrix=support_matrix,
            twist_vector=_twist_vector(support_matrix),
            nominal_pad_stiffness_N_m=k_nom,
            load_sensitivity_diag_N_m=np.diag(sensitivity).copy(),
            F_min_N=params.control.F_min_cylinder_N,
            max_speed_m_s=params.actuator.max_speed_m_s,
            stroke_max_m=params.actuator.stroke_m,
            crawler_corners_xy_m=corners,
            crawler_bottom_z_m=params.ground.crawler_bottom_z_m,
            head_area_m2=head_area,
            oil_bulk_modulus_Pa=float(params.get(OIL_BULK_MODULUS_KEY)),
            oil_dead_length_m=float(params.get(OIL_DEAD_LENGTH_KEY)),
            locked_force_limit_N=_leg_locked_force_limits_N(params, head_area),
            annulus_area_m2=leg_annulus_areas_from_params(params),
            stroke_measurable_max_m=_optional_float(
                params, STROKE_MEASURABLE_MAX_KEY, STROKE_SOFT_MAX_M
            ),
            rod_weight_N=np.array(
                [leg.moving_part.mass_kg * params.meta.gravity_m_s2 for leg in params.legs]
            ),
            rod_lock_pressure_after_retract_Pa=_optional_per_leg(
                params, RETRACT_LOCK_ROD_PRESSURE_KEY
            ),
            counterbalance_lag_tau_s=_optional_float_or_none(params, CB_LAG_TAU_KEY),
            superstructure_mass_kg=params.superstructure.mass_properties.mass_kg,
            imu_lever_arm_m=(np.array(IMU_MOUNT_C1_BODY_M)
                             - np.array(params.superstructure.mass_properties.com_m)),
        )

    def __post_init__(self) -> None:
        for name in ("head_area_m2", "locked_force_limit_N", "annulus_area_m2"):
            per_leg = np.broadcast_to(np.asarray(getattr(self, name), dtype=float), LEG_COUNT)
            object.__setattr__(self, name, per_leg.copy())
        nominal_stiffness = np.full(LEG_COUNT, self.nominal_pad_stiffness_N_m)
        sensitivity = attitude_sensitivity_rad_m(self.support_matrix, nominal_stiffness)
        object.__setattr__(self, "attitude_sensitivity_rad_m", sensitivity)
        plane_basis = np.column_stack([np.ones(LEG_COUNT), self.pad_xy_m])
        object.__setattr__(self, "_plane_fit", np.linalg.pinv(plane_basis))
        object.__setattr__(self, "_support_pinv", np.linalg.pinv(self.support_matrix))

    @property
    def stroke_soft_max_m(self) -> float:
        """Software stroke end ``min(s_max, measurable end)`` (spec 65.3, 0.6948 m)."""
        return min(self.stroke_max_m, self.stroke_measurable_max_m)

    def clearance_estimate_m(self, rod_stroke_m: ArrayLike) -> float:
        """Smallest crawler-corner clearance of the pad plane fitted to the strokes.

        Least-squares plane ``z = c0 + c1 x + c2 y`` through the pad bottoms ``z_retracted - x``
        (rigid body, floor at the crawler bottom), evaluated at the four crawler corners.
        """
        return float(np.min(self.clearance_corners_m(rod_stroke_m)))

    def clearance_corners_m(self, rod_stroke_m: ArrayLike) -> NDArray[np.float64]:
        """Clearance ``c_k`` of each crawler box corner (4,) from the fitted pad plane."""
        pad_z = self.pad_bottom_z_retracted_m - np.asarray(rod_stroke_m, dtype=float)
        plane = self._plane_fit @ pad_z
        corner_z = plane[0] + self.crawler_corners_xy_m @ plane[1:]
        return self.crawler_bottom_z_m - corner_z

    def predicted_strokes_m(
        self,
        motor_stroke_m: ArrayLike,
        rod_stroke_m: ArrayLike,
        attitude_change_rad: tuple[float, float],
        clearance_target_m: float,
        corner_bias_m: ArrayLike | None = None,
    ) -> NDArray[np.float64]:
        """Strokes after tilting by ``(d_phi, d_theta)`` at the clearance target (spec 2.3 A5).

        ``dz = c* - min_k(c_k + y_k d_phi - x_k d_theta)``, ``s_i + dz + y_i d_phi - x_i d_theta``
        (rigid body, small angles, linear in the extensions). ``corner_bias_m``: the S-3
        soil bias ``b_k`` subtracted from ``c_k`` (spec rev. 57 282.4); ``None`` = none.
        """
        roll_change, pitch_change = attitude_change_rad
        corners_xy = self.crawler_corners_xy_m
        corner_rise = corners_xy[:, 1] * roll_change - corners_xy[:, 0] * pitch_change
        corner_clearance = self.clearance_corners_m(rod_stroke_m)
        if corner_bias_m is not None:
            corner_clearance = corner_clearance - np.asarray(corner_bias_m, dtype=float)
        heave = clearance_target_m - float(np.min(corner_clearance + corner_rise))
        pad_rise = self.pad_xy_m[:, 1] * roll_change - self.pad_xy_m[:, 0] * pitch_change
        return np.asarray(motor_stroke_m, dtype=float) + heave + pad_rise

    def oil_stiffness_N_m(self, stroke_m: ArrayLike) -> NDArray[np.float64]:
        """Locked oil column stiffness ``k_oil(e) = beta A / (dead + e)`` per leg."""
        extension = np.asarray(stroke_m, dtype=float)
        return self.oil_bulk_modulus_Pa * self.head_area_m2 / (self.oil_dead_length_m + extension)

    def operating_extension_m(self, clearance_m: float) -> NDArray[np.float64]:
        """``e_op``: extensions with every pad on a level floor and the crawler ``clearance_m``
        above it (the extension the L1 lumped pad stiffness was split at)."""
        return self.pad_bottom_z_retracted_m - self.crawler_bottom_z_m + clearance_m

    def leg_speeds(
        self, heave_m_s: float, roll_rad_s: float, pitch_rad_s: float, twist_m_s: float
    ) -> NDArray[np.float64]:
        """Compose leg speeds ``u = A [z, phi, theta] + n tau`` (design section 1)."""
        rates = np.array([heave_m_s, roll_rad_s, pitch_rad_s])
        return self.support_matrix @ rates + self.twist_vector * twist_m_s

    def decompose(self, leg_speeds_m_s: ArrayLike) -> NDArray[np.float64]:
        """Inverse of :meth:`leg_speeds`: ``[A^+ u, n^T u]`` = (heave, roll, pitch, twist)."""
        speeds = np.asarray(leg_speeds_m_s, dtype=float)
        attitude_part = self._support_pinv @ speeds
        return np.append(attitude_part, self.twist_vector @ speeds)


# --- shadow floor estimate (spec 14.6 X9) --------------------------------------------------


def _level_from_body(roll_rad: float, pitch_rad: float) -> NDArray[np.float64]:
    """Rotation level frame <- body, ``R_y(theta) R_x(phi)`` (yaw left out)."""
    cos_roll, sin_roll = math.cos(roll_rad), math.sin(roll_rad)
    cos_pitch, sin_pitch = math.cos(pitch_rad), math.sin(pitch_rad)
    about_x = np.array([[1.0, 0.0, 0.0], [0.0, cos_roll, -sin_roll], [0.0, sin_roll, cos_roll]])
    about_y = np.array([[cos_pitch, 0.0, sin_pitch], [0.0, 1.0, 0.0], [-sin_pitch, 0.0, cos_pitch]])
    return about_y @ about_x


@dataclass(frozen=True)
class FloorPlaneEstimate:
    """Floor attitude from the pad bottoms at their touch latches (method (B), shadow only).

    Attributes:
        floor_rad: ``(phi_g, theta_g)`` of the least-squares plane through the four pads.
        residual_m: Largest pad distance from that plane (non-planarity of the four points).
        floor_usage: A1 usage of ``floor_rad`` with the run's limits.
        latch_times_s: Latch time of each leg.
    """

    floor_rad: tuple[float, float]
    residual_m: float
    floor_usage: float
    latch_times_s: tuple[float, ...]

    def to_meta(self) -> dict[str, Any]:
        return {
            "floor_rad": list(self.floor_rad),
            "residual_m": self.residual_m,
            "floor_usage": self.floor_usage,
            "latch_times_s": list(self.latch_times_s),
        }


class FloorPlaneEstimator:
    """Shadow floor estimate (B) of ``s6_control_spec.md`` 14 and dynamics 3.13.6 (X9).

    Best variant of dynamics 3.13.6: each leg's pad bottom is taken at its own touch latch from
    the piston stroke ``stroke_corrected_m`` and rotated into the level frame with the filtered
    attitude of that moment (the body turns by up to 0.1 deg while the crawler hands over load
    between latches). Body translation between latches is not seen (ASSUMPTION, part of the
    0.004 deg 90th percentile of dynamics 3.13.6). The estimate is recorded only; it decides
    nothing and changes no command.

    Args:
        geometry: Pad positions and retracted pad bottom heights.
    """

    def __init__(self, geometry: C2Geometry) -> None:
        self._geometry = geometry
        self.reset()

    def reset(self) -> None:
        self._points_m: list[NDArray[np.float64] | None] = [None] * LEG_COUNT
        self._latch_times_s: list[float | None] = [None] * LEG_COUNT

    def record_latch(
        self, leg: int, t_s: float, rod_stroke_m: float, attitude_rad: tuple[float, float]
    ) -> None:
        """Pad bottom of ``leg`` (level frame, about the body origin) at its touch latch."""
        geometry = self._geometry
        pad_x, pad_y = geometry.pad_xy_m[leg]
        pad_body = np.array([pad_x, pad_y, geometry.pad_bottom_z_retracted_m[leg] - rod_stroke_m])
        self._points_m[leg] = _level_from_body(*attitude_rad) @ pad_body
        self._latch_times_s[leg] = float(t_s)

    def estimate(self, limits: TargetLimits) -> FloorPlaneEstimate | None:
        """Plane through the four latched pads; ``None`` until every leg has latched."""
        if any(point is None for point in self._points_m):
            return None
        points = np.array(self._points_m)
        basis = np.column_stack([np.ones(LEG_COUNT), points[:, 0], points[:, 1]])
        coefficients, *_ = np.linalg.lstsq(basis, points[:, 2], rcond=None)
        residual_m = float(np.max(np.abs(points[:, 2] - basis @ coefficients)))
        _, slope_x, slope_y = coefficients
        normal = np.array([-slope_x, -slope_y, 1.0])
        normal /= np.linalg.norm(normal)
        floor_rad = (float(math.asin(-normal[1])), float(math.atan2(normal[0], normal[2])))
        latch_times = tuple(float(time_s) for time_s in self._latch_times_s)  # type: ignore[arg-type]
        return FloorPlaneEstimate(
            floor_rad, residual_m, floor_usage(floor_rad, limits), latch_times
        )


# --- support geometry shadow (spec 26, 29 GE1; R5 GE1' spec 37.3, 38) ----------------------

SHADOW_PAD_STIFFNESS_N_M = 2.17e8
"""Series stiffness below the piston (rod, pad, frame, concrete) for the deflection term
``+F / k_s`` of GE1 (spec 26.1, sign 32.5; ASSUMPTION)."""
SHADOW_LIFT_THRESHOLD_M = 5e-3
"""U28 G1-L: a pad risen more than this against the other three (ASSUMPTION)."""
SHADOW_SINK_THRESHOLD_M = -5e-3
"""U28 G1-S: a pad sunk more than this against the other three (ASSUMPTION)."""
SHADOW_NONPLANARITY_THRESHOLD_M = 1.4e-3
"""U28 G2 on ``|Delta r|`` (spec 32.4: 0.273 x 5 mm, rounded; was 1.5 mm in R4.1); also the
``INFO_FLOOR_NONPLANAR`` level of the absolute ``|r|`` (spec 37.3)."""
SHADOW_HOLD_S = 0.5
"""U28: a condition is flagged once it has held this long without a break, with the standstill
gate open all the time (ASSUMPTION)."""
SHADOW_HOLD_SLACK_S = 1e-9
RESIDUAL_SIGN_LEG = LEG_ORDER.index("RR")
"""``r = [(I - P) h]_RR``: the RR component fixes the sign of the four-pad residual (37.3)."""

SHADOW_EVENT_PREFIX = "shadow_"
FLOOR_NONPLANAR_CONDITION = "FLOOR_NONPLANAR"
FLOOR_NONPLANAR_EVENT = "INFO_FLOOR_NONPLANAR"
"""Absolute non-planarity of the floor (information, not a support change; spec 37.3)."""


def is_shadow_event(name: str) -> bool:
    """Whether an event comes from the GE1 shadow (no command depends on it)."""
    return name.startswith(SHADOW_EVENT_PREFIX) or name == FLOOR_NONPLANAR_EVENT


def _shadow_event_name(condition: str) -> str:
    if condition == FLOOR_NONPLANAR_CONDITION:
        return FLOOR_NONPLANAR_EVENT
    return f"{SHADOW_EVENT_PREFIX}{condition}"


def floor_normal(floor_rad: tuple[float, float]) -> NDArray[np.float64]:
    """Unit floor normal (level frame) of the X9 angles ``(phi_g, theta_g)``.

    Inverse of :meth:`FloorPlaneEstimator.estimate`: ``(cos phi sin theta, -sin phi,
    cos phi cos theta)``.
    """
    roll, pitch = floor_rad
    return np.array(
        [math.cos(roll) * math.sin(pitch), -math.sin(roll), math.cos(roll) * math.cos(pitch)]
    )


def _heights_above_others(heights_m: NDArray[np.float64]) -> NDArray[np.float64]:
    """Each value minus the median of the other three (G1', spec 26.1)."""
    return np.array(
        [heights_m[leg] - np.median(np.delete(heights_m, leg)) for leg in range(LEG_COUNT)]
    )


@dataclass(frozen=True)
class SupportGeometry:
    """One GE1' sample (every period once a reference is stored; cad records it with asdict).

    Attributes:
        t_s: Sample time.
        heights_delta_above_others_m: ``d_i^Delta = Delta h_i - median_{j != i} Delta h_j``
            (G1', + = risen against the other three since the reference), per leg.
        nonplanarity_delta_m: ``Delta r = r - r(t_ref)`` (G2).
        nonplanarity_m: ``r = [(I - P) h]_RR``, the absolute four-pad plane residual with the
            RR sign (floor non-planarity, information).
        heights_above_others_m: Absolute ``h_i - median_{j != i} h_j`` (the R4.1 G1' value;
            information only, it keeps the floor non-planarity).
        reference_t_s: When the reference was stored.
        is_geometry_valid: Standstill gate open: only then are the flags evaluated.
    """

    t_s: float
    heights_delta_above_others_m: tuple[float, ...]
    nonplanarity_delta_m: float
    nonplanarity_m: float
    heights_above_others_m: tuple[float, ...]
    reference_t_s: float
    is_geometry_valid: bool


@dataclass(frozen=True)
class SupportReference:
    """Stored GE1' reference ``(n_0, h(t_ref), r(t_ref))`` (spec 37.3)."""

    normal: NDArray[np.float64]
    heights_m: NDArray[np.float64]
    nonplanarity_m: float
    t_s: float
    source: str
    max_abs_height_change_m: float | None
    """``max_i |Delta h_i|`` against the previous reference when this one replaced it (soft
    ground: a refresh may hide accumulated sinking, spec 26.4 (3)); ``None`` for the first."""

    def to_meta(self) -> dict[str, Any]:
        return {
            "normal": self.normal.tolist(),
            "heights_m": self.heights_m.tolist(),
            "nonplanarity_m": self.nonplanarity_m,
            "t_s": self.t_s,
            "source": self.source,
            "max_abs_height_change_m": self.max_abs_height_change_m,
        }


class SupportGeometryShadow:
    """GE1' shadow of spec 37.3 (R5): stroke-geometry cues G1' and G2, recorded only.

    Every period the pad bottoms ``[x_i, y_i, z_i - e_i + F_i / k_s]`` (body axes; ``e`` = rod
    stroke with the oil compression removed, ``+F / k_s`` the deflection below the piston, so a
    loaded pad bottom sits that much higher than the stroke alone says) are turned into the
    level frame with the filtered attitude and projected on the stored normal: ``h_i``. The
    reference keeps ``n_0``, ``h(t_ref)`` and ``r(t_ref)``; the cues are the changes against
    it, so a non-planar floor accepted as the reference reads zero (spec 37.2). The U28
    conditions (``d^Delta`` > +5 mm, < -5 mm, ``|Delta r|`` > 1.4 mm) and the absolute
    ``|r|`` > 1.4 mm are evaluated only on samples with the standstill gate open and flagged
    once per reference after 0.5 s without a break; nothing acts on them.

    Args:
        geometry: Pad positions and retracted pad bottom heights.
    """

    def __init__(
        self, geometry: C2Geometry, pad_stiffness_N_m: ArrayLike = SHADOW_PAD_STIFFNESS_N_M
    ) -> None:
        self._geometry = geometry
        self.pad_stiffness_N_m = np.broadcast_to(
            np.asarray(pad_stiffness_N_m, dtype=float), LEG_COUNT
        ).copy()
        plane_basis = np.column_stack([np.ones(LEG_COUNT), geometry.pad_xy_m])
        plane_projection = plane_basis @ np.linalg.pinv(plane_basis)
        self._residual_row = (np.eye(LEG_COUNT) - plane_projection)[RESIDUAL_SIGN_LEG]
        self.reset()

    def reset(self) -> None:
        self.reference: SupportReference | None = None
        self.reference_history: list[SupportReference] = []
        self.latest: SupportGeometry | None = None
        self.max_abs_heights_delta_m = np.zeros(LEG_COUNT)
        """Largest ``|d^Delta|`` per leg over the gate-open samples."""
        self.max_abs_nonplanarity_delta_m = 0.0
        self.max_abs_nonplanarity_m = 0.0
        self.flags_t_s: dict[str, float] = {}
        """Condition -> time it was first held 0.5 s, since the last stored reference."""
        self._condition_since_s: dict[str, float] = {}

    def pad_bottoms_body_m(
        self, rod_stroke_m: NDArray[np.float64], cylinder_force_N: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Pad bottom centres (4, 3) in body axes with the deflection added back."""
        geometry = self._geometry
        deflection_m = cylinder_force_N / self.pad_stiffness_N_m
        heights_m = geometry.pad_bottom_z_retracted_m - rod_stroke_m + deflection_m
        return np.column_stack([geometry.pad_xy_m, heights_m])

    def heights_m(
        self,
        normal: NDArray[np.float64],
        attitude_rad: tuple[float, float],
        rod_stroke_m: NDArray[np.float64],
        cylinder_force_N: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """``h_i = n . p_i``: pad bottoms in the level frame along ``normal``."""
        body_points = self.pad_bottoms_body_m(rod_stroke_m, cylinder_force_N)
        return body_points @ _level_from_body(*attitude_rad).T @ normal

    def nonplanarity_m(self, heights_m: NDArray[np.float64]) -> float:
        """``r = [(I - P) h]_RR`` (linear in ``h``, sign fixed by the RR row)."""
        return float(self._residual_row @ heights_m)

    def pad_plane_normal(
        self,
        attitude_rad: tuple[float, float],
        rod_stroke_m: NDArray[np.float64],
        cylinder_force_N: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Unit normal (level frame) of the least-squares plane through the current pads."""
        body_points = self.pad_bottoms_body_m(rod_stroke_m, cylinder_force_N)
        level_points = body_points @ _level_from_body(*attitude_rad).T
        basis = np.column_stack([np.ones(LEG_COUNT), level_points[:, :2]])
        coefficients, *_ = np.linalg.lstsq(basis, level_points[:, 2], rcond=None)
        _, slope_x, slope_y = coefficients
        normal = np.array([-slope_x, -slope_y, 1.0])
        return normal / np.linalg.norm(normal)

    def store_reference(
        self,
        t_s: float,
        attitude_rad: tuple[float, float],
        rod_stroke_m: NDArray[np.float64],
        cylinder_force_N: NDArray[np.float64],
        source: str,
        normal: NDArray[np.float64] | None = None,
    ) -> SupportReference:
        """Accept the current support geometry as normal; starts a new flag episode.

        Args:
            t_s: Reference time.
            attitude_rad: Filtered (roll, pitch).
            rod_stroke_m: Rod strokes.
            cylinder_force_N: Pressure readings as cylinder forces.
            source: ``touch``, ``done`` or ``ready`` (meta).
            normal: Floor normal to keep (TOUCH end: the X9 estimate); ``None`` = the plane of
                the current pads.
        """
        if normal is None:
            normal = self.pad_plane_normal(attitude_rad, rod_stroke_m, cylinder_force_N)
        unit_normal = normal / np.linalg.norm(normal)
        previous = self.reference
        max_change_m = None
        if previous is not None:
            heights_on_previous = self.heights_m(
                previous.normal, attitude_rad, rod_stroke_m, cylinder_force_N
            )
            max_change_m = float(np.max(np.abs(heights_on_previous - previous.heights_m)))
        heights = self.heights_m(unit_normal, attitude_rad, rod_stroke_m, cylinder_force_N)
        self.reference = SupportReference(
            unit_normal, heights, self.nonplanarity_m(heights), float(t_s), source, max_change_m
        )
        self.reference_history.append(self.reference)
        self.flags_t_s = {}
        self._condition_since_s = {}
        return self.reference

    def update(
        self,
        t_s: float,
        attitude_rad: tuple[float, float],
        rod_stroke_m: NDArray[np.float64],
        cylinder_force_N: NDArray[np.float64],
        is_geometry_valid: bool = True,
    ) -> list[str]:
        """One period; returns the conditions that have just held for 0.5 s (gate open)."""
        reference = self.reference
        if reference is None:
            return []
        heights = self.heights_m(reference.normal, attitude_rad, rod_stroke_m, cylinder_force_N)
        height_changes = _heights_above_others(heights - reference.heights_m)
        nonplanarity = self.nonplanarity_m(heights)
        nonplanarity_change = nonplanarity - reference.nonplanarity_m
        self.latest = SupportGeometry(
            t_s=float(t_s),
            heights_delta_above_others_m=tuple(map(float, height_changes)),
            nonplanarity_delta_m=nonplanarity_change,
            nonplanarity_m=nonplanarity,
            heights_above_others_m=tuple(map(float, _heights_above_others(heights))),
            reference_t_s=reference.t_s,
            is_geometry_valid=bool(is_geometry_valid),
        )
        if not is_geometry_valid:
            self._condition_since_s = {}  # the 0.5 s must run with the gate open
            return []
        self.max_abs_heights_delta_m = np.maximum(
            self.max_abs_heights_delta_m, np.abs(height_changes)
        )
        self.max_abs_nonplanarity_delta_m = max(
            self.max_abs_nonplanarity_delta_m, abs(nonplanarity_change)
        )
        self.max_abs_nonplanarity_m = max(self.max_abs_nonplanarity_m, abs(nonplanarity))
        conditions = self._conditions(height_changes, nonplanarity_change, nonplanarity)
        return self._update_holds(t_s, conditions)

    def _conditions(
        self,
        height_changes_m: NDArray[np.float64],
        nonplanarity_delta_m: float,
        nonplanarity_m: float,
    ) -> dict[str, bool]:
        conditions = {}
        for leg, name in enumerate(LEG_ORDER):
            conditions[f"G1L:{name}"] = bool(height_changes_m[leg] > SHADOW_LIFT_THRESHOLD_M)
            conditions[f"G1S:{name}"] = bool(height_changes_m[leg] < SHADOW_SINK_THRESHOLD_M)
        threshold_m = SHADOW_NONPLANARITY_THRESHOLD_M
        conditions["G2"] = abs(nonplanarity_delta_m) > threshold_m
        conditions[FLOOR_NONPLANAR_CONDITION] = abs(nonplanarity_m) > threshold_m
        return conditions

    def _update_holds(self, t_s: float, conditions: dict[str, bool]) -> list[str]:
        newly_held = []
        for name, is_met in conditions.items():
            if not is_met:
                self._condition_since_s.pop(name, None)
                continue
            since_s = self._condition_since_s.setdefault(name, t_s)
            has_held = t_s - since_s >= SHADOW_HOLD_S - SHADOW_HOLD_SLACK_S
            if has_held and name not in self.flags_t_s:
                self.flags_t_s[name] = float(t_s)
                newly_held.append(name)
        return newly_held

    def to_meta(self) -> dict[str, Any]:
        latest = self.latest
        reference = self.reference
        return {
            "reference": None if reference is None else reference.to_meta(),
            "reference_updates": [entry.to_meta() for entry in self.reference_history],
            "last": None if latest is None else asdict(latest),
            "max_abs_heights_delta_above_others_m": self.max_abs_heights_delta_m.tolist(),
            "max_abs_nonplanarity_delta_m": self.max_abs_nonplanarity_delta_m,
            "max_abs_nonplanarity_m": self.max_abs_nonplanarity_m,
            "flags_t_s": dict(self.flags_t_s),
            "settings": {
                "pad_stiffness_N_m": self.pad_stiffness_N_m.tolist(),
                "lift_threshold_m": SHADOW_LIFT_THRESHOLD_M,
                "sink_threshold_m": SHADOW_SINK_THRESHOLD_M,
                "nonplanarity_threshold_m": SHADOW_NONPLANARITY_THRESHOLD_M,
                "hold_s": SHADOW_HOLD_S,
                "residual_sign_leg": LEG_ORDER[RESIDUAL_SIGN_LEG],
            },
        }


# --- control law pieces --------------------------------------------------------------------


def scale_to_speed_limit(leg_speeds_m_s: ArrayLike, max_speed_m_s: float) -> NDArray[np.float64]:
    """Scale the whole vector so that no leg exceeds ``max_speed_m_s`` (direction kept).

    Clipping legs one by one would change the decomposition (design 6.1).
    """
    speeds = np.asarray(leg_speeds_m_s, dtype=float)
    largest = np.max(np.abs(speeds))
    if largest > max_speed_m_s:
        return speeds * (max_speed_m_s / largest)
    return speeds.copy()


@dataclass(frozen=True)
class TwistRates:
    """Twist channel of one LEVEL period (design 14.5 steps 4-5).

    Attributes:
        twist_m_s: Twist-loop term after the guard priority (the opposing part dropped).
        guard_m_s: F_min guard term (0 when the guard does not act).
        is_guard_active: The lowest load estimate is below ``F_min + margin``.
    """

    twist_m_s: float
    guard_m_s: float
    is_guard_active: bool

    @property
    def total_m_s(self) -> float:
        """``tau_dot`` = twist + guard (the twist term alone when the guard is idle)."""
        if not self.is_guard_active:
            return self.twist_m_s
        return self.twist_m_s + self.guard_m_s


def twist_rates(
    twist_load_N: float,
    load_estimate_N: ArrayLike,
    geometry: C2Geometry,
    gains: C2Gains,
    thresholds: C2Thresholds,
    stiffness_N_m: float | None = None,
) -> TwistRates:
    """Twist loop and F_min guard terms of ``tau_dot`` (m/s), see :func:`twist_rate_command`.

    Args:
        twist_load_N: ``n^T P`` the twist loop acts on (raw or low-passed, R8 C2).
        load_estimate_N: Lower load estimate per leg (the guard always uses this raw value).
        geometry: Twist vector, ``k_nom``, F_min.
        gains: ``K_tw``, ``K_g``.
        thresholds: Dead band and guard margin.
        stiffness_N_m: Stiffness the gains are divided by; ``None`` = ``k_nom`` (R8 P-5).
    """
    twist = geometry.twist_vector
    stiffness = geometry.nominal_pad_stiffness_N_m if stiffness_N_m is None else stiffness_N_m
    deadband = thresholds.twist_deadband_N
    if abs(twist_load_N) < deadband:
        twist_error = 0.0
    else:
        twist_error = twist_load_N - math.copysign(deadband, twist_load_N)
    rate = -gains.twist_ktw_1_s * twist_error / stiffness

    loads = np.asarray(load_estimate_N, dtype=float)
    guard_level = geometry.F_min_N + thresholds.guard_margin_N
    lowest_leg = int(np.argmin(loads))
    if loads[lowest_leg] >= guard_level:
        return TwistRates(rate, 0.0, False)
    direction = math.copysign(1.0, twist[lowest_leg])
    if rate * direction < 0:
        rate = 0.0
    guard = direction * gains.guard_kg_1_s * (guard_level - loads[lowest_leg]) / stiffness
    return TwistRates(rate, guard, True)


def twist_rate_command(
    cylinder_force_N: ArrayLike,
    load_estimate_N: ArrayLike,
    geometry: C2Geometry,
    gains: C2Gains,
    thresholds: C2Thresholds,
) -> tuple[float, bool]:
    """Twist channel speed ``tau_dot`` (m/s) and whether the F_min guard acted (design 14.5 4-5).

    Twist loop: ``tau_dot = -K_tw db(n^T P) / k_nom`` (decision D6). Guard: if the lowest load
    estimate ``L_i`` is below ``F_min + margin``, a twist term that would unload leg ``i`` is
    dropped (priority, N3) and ``sgn(n_i) K_g (F_min + margin - L_i) / k_nom`` is added.
    """
    twist_load = float(geometry.twist_vector @ np.asarray(cylinder_force_N, dtype=float))
    rates = twist_rates(twist_load, load_estimate_N, geometry, gains, thresholds)
    return rates.total_m_s, rates.is_guard_active


# --- run state -----------------------------------------------------------------------------


def _no_output_limits() -> dict[str, NDArray[np.bool_]]:
    return {limit.value: np.zeros(LEG_COUNT, dtype=bool) for limit in OutputLimit}


def _corner_values_mm(values_m: NDArray[np.float64]) -> str:
    """``FL=..,FR=..,RL=..,RR=..`` in mm of a per-crawler-corner array (event text)."""
    by_name = dict(zip(CRAWLER_CORNER_NAMES, values_m, strict=True))
    return ",".join(f"{name}={by_name[name] * 1e3:.1f}" for name in LEG_ORDER)


def _last_imu_specific_force_z_m_s2(measurements: Measurements) -> float | None:
    """Body-z specific force of the last IMU sample of the period (the 10 ms partial mean
    ending at ``t_s``, D1'' 218.4); ``None`` when only the period mean is delivered (the
    monitor then keeps the D1' sum rule)."""
    samples = measurements.imu_specific_force_samples_m_s2
    if samples is None:
        return None
    return float(samples[-1][2])



@dataclass(frozen=True)
class _Reground:
    leg: int
    target_stroke_m: float


@dataclass(frozen=True)
class _RawTilt:
    """Unfiltered accelerometer tilt of one IMU-rate sample (P-R8-9)."""

    t_s: float
    roll_rad: float
    pitch_rad: float


@dataclass(frozen=True)
class C2Event:
    """Something the run should report (revision R2 re-anchoring events).

    Attributes:
        t_s: Measurement time of the period that raised it (s).
        name: ``reanchor_started``, ``reanchor_skipped:<reason>``, ``reanchor_aborted:<reason>``,
            ``reanchor_completed`` or ``reanchor_band_exceeded``; target events: a rejection
            code of :class:`~outrigger_sim.control.target.TargetCode` (``REJ_*``),
            ``WARN_TARGET_PROJECTED``, ``target_changed``; ``locked_pressure_over_limit:<leg>``;
            B1' ``WARN_GYRO_BIAS_SKIPPED``, ``WARN_GYRO_BIAS_IMPLAUSIBLE``; GE1' shadow flags
            ``shadow_G1L:<leg>``, ``shadow_G1S:<leg>``, ``shadow_G2`` and
            ``INFO_FLOOR_NONPLANAR`` (:func:`is_shadow_event`); R-5 ``relevel_predicted:<leg>``;
            P-R8-11 ``probe_aborted_low_load:<leg>``; P-R8-12 / P-R8-13
            ``leg_reapproach_start:<leg>``,
            ``leg_reapproach_contact:<leg>`` and ``WARN_LEG_REAPPROACH_NO_CONTACT:<leg>``;
            soil response (spec rev. 57 285 P-S9-7) ``soil_mode_start``,
            ``crawler_liftoff_confirmed``, ``INFO_CLEARANCE_BIAS:FL=..,FR=..,RL=..,RR=..``
            (crawler-corner bias in mm), ``WARN_CRAWLER_LIFTOFF_UNCONFIRMED`` and
            ``WARN_WEIGHT_MISMATCH:<W_hat / W_ref>``.
    """

    t_s: float
    name: str


class _ReanchorStage(Enum):
    """Sub-state of REANCHOR (design 17.2.3)."""

    WAIT = "wait"
    MOVE = "move"
    HOLD = "hold"
    RETURN = "return"
    HOLD2 = "hold2"
    ABORT_RETURN = "abort_return"


@dataclass
class _ReanchorRun:
    stop_force_N: tuple[float, ...]
    """``P_stop,k`` per step, fixed at the start with the ``F_band`` of that moment."""
    seal_band_used_N: float
    stage_start_s: float
    stage: _ReanchorStage = _ReanchorStage.WAIT
    step: int = 0
    commanded_m: NDArray[np.float64] = field(default_factory=lambda: np.zeros(LEG_COUNT))
    """``c_k``: commanded displacement of the current step, returned to zero afterwards."""
    abort_outcome: str | None = None
    stop_readings_N: list[tuple[str, float]] = field(default_factory=list)
    """(target leg, its reading) at every MOVE -> HOLD."""
    stop_predicted_readings_N: list[tuple[str, float]] = field(default_factory=list)
    """R-1: (target leg, the predicted reading the stop was judged on) at every MOVE -> HOLD."""
    stop_history_N: list[float] = field(default_factory=list)
    """R-1: target readings of the current MOVE step, oldest first."""
    is_band_exceeded: bool = False


@dataclass
class _Reapproach:
    """P-R8-12 / P-R8-13: one re-approach of a lifted leg (meta interval)."""

    leg: int
    start_s: float
    start_motor_stroke_m: float
    mode: ReapproachMode
    end_s: float | None = None
    travel_m: float = 0.0
    outcome: str | None = None
    """``contact``, ``no_contact`` or ``phase:<phase>`` (left the watched phases)."""
    exit_samples_seen: int = 0
    """Consecutive samples at the exit level (at the end: the count it ended with)."""
    protected_periods: int = 0
    """Twist mode: periods with ``tau_dot`` held at zero to protect another grounded leg."""
    is_retrigger: bool = False
    """P-S8-16 RT 2: started inside the re-trigger window (runs at the reduced speed)."""

    def to_meta(self) -> dict[str, Any]:
        return {
            "leg": LEG_ORDER[self.leg],
            "mode": str(self.mode),
            "start_s": self.start_s,
            "end_s": self.end_s,
            "travel_m": self.travel_m,
            "outcome": self.outcome,
            "exit_samples_seen": self.exit_samples_seen,
            "protected_periods": self.protected_periods,
            "is_retrigger": self.is_retrigger,
        }


@dataclass(frozen=True)
class _PlateauSample:
    """One period of the S-1 lift-off window (spec rev. 57 285 P-S9-2)."""

    t_s: float
    mean_motor_stroke_m: float
    load_sum_N: float
    corner_clearance_m: NDArray[np.float64]
    """Stroke-based crawler-corner clearance ``c_k`` (rigid floor, no bias)."""
    raw_attitude_rad: tuple[float, float]
    """Mean raw tilt (roll, pitch) of the period (without IMU-rate samples: the raw tilt of the
    period-mean specific force)."""


@dataclass
class _SoilState:
    """Soil response S-1 .. S-5 of one lifting cycle (cleared at TOUCH entry, P-S9-6)."""

    is_liftoff_confirmed: bool = False
    is_soil_mode: bool = False
    window: deque[_PlateauSample] = field(
        default_factory=lambda: deque(maxlen=SOIL_PLATEAU_WINDOW_MAX_SAMPLES)
    )
    settle_tilts: list[tuple[float, float]] = field(default_factory=list)
    """Raw tilts of the first TOUCH periods (settle attitude without CHECK)."""
    settle_attitude_rad: tuple[float, float] | None = None
    """Crawler settle attitude the S-3 corner rise is measured from."""
    corner_bias_m: NDArray[np.float64] = field(default_factory=lambda: np.zeros(LEG_COUNT))
    """S-3 bias ``b_k`` per crawler corner (order of ``C2Geometry.crawler_corners_xy_m``)."""
    corner_bias_raw_m: NDArray[np.float64] | None = None
    """``b_k`` before the clip at zero and the dead zone."""
    plateau_start_s: float | None = None
    """``t_P``: first sample of the confirming window (lift-off estimate)."""
    liftoff_s: float | None = None
    """``t_L``: LOC time."""
    weight_estimate_N: float | None = None
    """``W_hat``: window-mean load sum at the LOC."""
    weight_ratio: float | None = None
    clearance_at_plateau_start_m: float | None = None
    clearance_at_liftoff_m: float | None = None
    """Smallest unbiased corner clearance at ``t_P`` / ``t_L`` (rigid-floor check, spec 285:
    the LOC must come before the 20 mm crawler-zone release)."""
    soil_mode_start_s: float | None = None
    soil_mode_start_stroke_m: float | None = None
    push_m: float | None = None
    """Mean motor-stroke increase since the soil-mode start, updated every soil-mode period
    (so it ends at the LOC or the S-4 FAULT)."""

    @property
    def has_corner_bias(self) -> bool:
        return bool(np.any(self.corner_bias_m != 0.0))


@dataclass
class _RunState:
    seal_band_N: float
    phase: C2Phase = C2Phase.TOUCH
    sample_count: int = 0
    touched: NDArray[np.bool_] = field(default_factory=lambda: np.zeros(LEG_COUNT, dtype=bool))
    touch_candidate_since_s: list[float | None] = field(default_factory=lambda: [None] * LEG_COUNT)
    """Start of the unbroken run of touchdown-load samples per leg (R1)."""
    touch_seen: NDArray[np.bool_] = field(default_factory=lambda: np.zeros(LEG_COUNT, dtype=bool))
    """The leg has reached the touchdown load at least once (approach speed, R1)."""
    in_crawler_zone: bool = True
    """Crawler-zone latch (R1); on at LEVEL entry and kept through re-levelling."""
    free_air_readings: list[NDArray[np.float64]] = field(default_factory=list)
    free_air_force_N: NDArray[np.float64] | None = None
    touch_load_counts: NDArray[np.int_] = field(
        default_factory=lambda: np.zeros(LEG_COUNT, dtype=int)
    )
    """Consecutive TOUCH samples at the touchdown load per leg (P-S8-6 ``touch_seen``)."""
    touch_entry_motor_stroke_m: NDArray[np.float64] | None = None
    """Motor strokes of the first TOUCH sample (P-S8-6 travel reference)."""
    free_air_first_moving_sample: list[int | None] = field(
        default_factory=lambda: [None] * LEG_COUNT
    )
    """P-S8-6: TOUCH sample index of each leg's first moving sample (its window start)."""
    free_air_moving_readings_N: list[list[float]] = field(
        default_factory=lambda: [[] for _ in range(LEG_COUNT)]
    )
    """P-S8-6: per-leg readings of the moving samples inside the free-air window."""
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    rate_attitude_rad: tuple[float, float] = (0.0, 0.0)
    """Gyro roll / pitch rate integrated since the run start (rad); only its changes are
    used (probe attitude cue)."""
    rate_attitude_recent: deque[tuple[float, float]] = field(default_factory=deque)
    """``rate_attitude_rad`` of the previous samples (probe attitude baseline); the controller
    sets the length."""
    completion_roll_rad: float = 0.0
    completion_pitch_rad: float = 0.0
    roll_integral: float = 0.0
    pitch_integral: float = 0.0
    is_lifted: bool = False
    complete_since_s: float | None = None
    stroke_end_steps: int = 0
    probe_round: ProbeRound | None = None
    reground: _Reground | None = None
    probe_round_count: int = 0
    probe_history: list[tuple[ProbeResult, ...]] = field(default_factory=list)
    previous_output_m_s: NDArray[np.float64] = field(default_factory=lambda: np.zeros(LEG_COUNT))
    theta_crawler_rad: float | None = None
    """Filtered pitch at TOUCH -> LEVEL, the floor slope seen on the crawler (R2)."""
    reanchor: _ReanchorRun | None = None
    reanchor_outcome: str | None = None
    """``completed``, ``aborted:<reason>`` or ``skipped:<reason>``; latched once per run."""
    events: list[C2Event] = field(default_factory=list)
    check_start_s: float | None = None
    check_attitudes: deque[tuple[float, float]] = field(default_factory=deque)
    """Filtered (roll, pitch) of the last CHECK samples; the controller sets the length."""
    period_raw_tilts: list[_RawTilt] = field(default_factory=list)
    """IMU-rate raw tilts of the current period (P-R8-9; empty on the R7 path)."""
    period_mean_raw_tilt_rad: tuple[float, float] = (0.0, 0.0)
    """R7 path (no IMU-rate samples): raw (roll, pitch) of the period-mean specific force,
    the S-3 raw tilt there (user decision 2026-10-26 (n-2))."""
    check_raw_tilts: list[_RawTilt] = field(default_factory=list)
    """Raw tilts of every CHECK period (P-R8-9 window)."""
    check_window: dict[str, Any] | None = None
    """P-R8-9 meta: the raw-tilt window ``(phi_c, theta_c)`` was averaged over."""
    gyro_rate_rad_s: tuple[float, float] = (0.0, 0.0)
    """Gyro roll / pitch rate of the current sample (before the bias removal)."""
    check_gyro_rates: list[tuple[float, float]] = field(default_factory=list)
    """Gyro roll / pitch rates of every CHECK sample (bias estimate, spec P3, B1')."""
    check_gyro_times_s: list[float] = field(default_factory=list)
    """Sample times of ``check_gyro_rates`` (the B1' window is the last ``T_b``)."""
    gyro_bias_rad_s: tuple[float, float] | None = None
    """Gyro roll / pitch bias removed from the rate attitude; ``None`` = not removed."""
    gyro_bias_estimate: GyroBiasEstimate | None = None
    """B1' result at the end of CHECK (meta)."""
    is_seal_band_measured: bool = False
    """H5a / D5: the first probe round has set ``F_band``."""
    skips_probe_after_reanchor: bool = False
    """H5a: the trim after a completed REANCHOR goes from DONE to READY without a probe."""
    is_reference_update_pending: bool = False
    """GE1'-b: a DONE / READY entry waits for the gate to refresh the shadow reference."""
    does_last_probe_accept_support: bool = False
    """GE1'-b: the last probe round found four grounded legs and nothing to re-ground."""
    support_reference_loads_N: NDArray[np.float64] | None = None
    """Cylinder forces at the last GE1' reference (D7 load change, K-3 / K-6)."""
    is_load_reference_pending: bool = False
    """Spec 110.1: a DONE / READY entry waits for the gate and 0.5 s without commands to store
    the load baseline of the P-4 D5 sum check and the E-5 drift (no probe condition)."""
    last_nonzero_command_t_s: float | None = None
    """Time of the last period whose output command was not all zero (standstill gate)."""
    is_geometry_valid: bool = False
    """GE1'-c standstill gate of the last period."""
    crawler_attitude_rad: tuple[float, float] | None = None
    """``(phi_c, theta_c)``: mean filtered attitude at the end of CHECK (A1, A4)."""
    requested_target: AttitudeTarget | None = None
    """Target judged at the end of CHECK."""
    active_target: AttitudeTarget | None = None
    """Accepted final target ``(phi_t, theta_t)``; ``None`` before acceptance or in IDLE."""
    reference: AttitudeTarget | None = None
    """Ramped reference ``(phi_r, theta_r)`` of the attitude loop (R1)."""
    target_code: TargetCode | None = None
    """Code of the last target decision."""
    target_checks: list[TargetCheck] = field(default_factory=list)
    touch_start_sample: int = 0
    """Sample count at TOUCH entry (the free-air window counts from there)."""
    reanchor_anchor_pitch_rad: float | None = None
    """H2: pitch the pads were last anchored at (``theta_crawler`` or the target pitch of the
    last completed REANCHOR)."""
    reanchor_outcomes: list[str] = field(default_factory=list)
    """Outcome of every REANCHOR decision of the run (U3 may re-arm it)."""
    last_reading: _Reading | None = None
    floor_estimate_touch: FloorPlaneEstimate | None = None
    """X9 shadow floor estimate (B) at the end of TOUCH."""
    locked_pressure_reported: set[int] = field(default_factory=set)
    """Legs whose READY reading went above the locked pressure limit (reported once)."""
    last_cylinder_force_N: NDArray[np.float64] | None = None
    last_forces: PressureForces | None = None
    """R6-P: the force readings of the last period (bands use lower / upper)."""
    last_nonzero_output_m_s: NDArray[np.float64] = field(
        default_factory=lambda: np.zeros(LEG_COUNT)
    )
    """U62: last nonzero command per leg (a retraction asks for a lock tail)."""
    lock_tail_speeds: dict[int, list[float]] = field(default_factory=dict)
    """U62: remaining tail speeds per leg."""
    lock_tail_settle_until_s: float | None = None
    lock_tail_count: int = 0
    is_ready_reference_refreshed: bool = False
    """J-7 (b): the GE1' reference was refreshed since the READY entry."""
    last_support_trigger: tuple[float, str] | None = None
    support_repeat_latched: set[str] = field(default_factory=set)
    support_triggers: list[dict[str, Any]] = field(default_factory=list)
    """J-7: every acted GE2 trigger (time, condition, key, lift vote)."""
    zero_calibration: ZeroCalibration | None = None
    """E-3: the round trip of the current CHECK."""
    previous_zero_calibration: ZeroCalibration | None = None
    """The round trip of the CHECK before an IDLE -> CHECK restart (76.4 (3) b)."""
    calibration_oil_temperature_C: float | None = None
    """E-5: oil temperature when the calibration ended (``None`` = no signal)."""
    oil_temperature_C: float | None = None
    applied_output_m_s: NDArray[np.float64] = field(default_factory=lambda: np.zeros(LEG_COUNT))
    """R8: the command output last period (acting now); ``previous_output_m_s`` with d = 0."""
    output_queue: deque[NDArray[np.float64]] = field(default_factory=deque)
    """R8: computed commands waiting for their output period (``d`` entries)."""
    guard_m_s: NDArray[np.float64] | None = None
    """R8: the F_min guard's share of the leg speeds this period (increment-limit direction)."""
    twist_stiffness_scale: float | None = None
    """R8 P-5: bounded median probe-measured / nominal ``S_ii``; ``None`` before an update."""
    twist_stiffness_raw_ratio: float | None = None
    """P-R8-7: unbounded median ratio of the last probe round (``None``: under 3 legs)."""
    twist_stiffness_leg_count: int | None = None
    """P-R8-7: legs with a stiffness ratio in the last probe round (``None`` before a round)."""
    above_counts: NDArray[np.int64] = field(
        default_factory=lambda: np.zeros(LEG_COUNT, dtype=np.int64)
    )
    below_counts: NDArray[np.int64] = field(
        default_factory=lambda: np.zeros(LEG_COUNT, dtype=np.int64)
    )
    """R8 sample confirmation: consecutive raw ABOVE / BELOW samples per leg."""
    relevel_low_count: int = 0
    """R8 (c): consecutive READY samples below the P5 threshold."""
    load_estimate_history: deque[NDArray[np.float64]] = field(default_factory=deque)
    """R-5: lower load estimates of the last periods (the controller sets the length)."""
    reapproach_low_counts: NDArray[np.int64] = field(
        default_factory=lambda: np.zeros(LEG_COUNT, dtype=np.int64)
    )
    """P-R8-12: consecutive samples below the lift-off level per leg."""
    is_reapproach_armed: NDArray[np.bool_] = field(
        default_factory=lambda: np.ones(LEG_COUNT, dtype=bool)
    )
    """P-R8-12: off after a re-approach without contact, until the leg reads ``F_min``."""
    active_reapproaches: dict[int, _Reapproach] = field(default_factory=dict)
    reapproach_history: list[_Reapproach] = field(default_factory=list)
    """Every re-approach of the run, the active ones included (meta)."""
    reapproach_last_end_s: float | None = None
    """P-S8-16: end time of the last re-approach (any outcome); ``None`` before the first."""
    reapproach_last_sign: float = 0.0
    """P-S8-16: ``sign(n_j)`` of the leg of the last re-approach (its diagonal)."""
    reapproach_strong_counts: tuple[int, ...] = NO_REAPPROACH_STRONG_COUNTS
    """P-S8-16 RT 1: consecutive watched low samples below ``opposite_strong_level_N`` per
    leg. A tuple, not an array, so that the class-level default also serves run states
    unpickled from older code."""
    command_components: dict[str, NDArray[np.float64]] | None = None
    """P-R8-14 / P-R8-15: parts of this period's command; ``None`` before the first period."""
    raw_output_m_s: NDArray[np.float64] = field(default_factory=lambda: np.zeros(LEG_COUNT))
    """P-R8-15: this period's command before the :class:`OutputLimit` stages."""
    output_limit_flags: dict[str, NDArray[np.bool_]] = field(
        default_factory=lambda: _no_output_limits()
    )
    """P-R8-15: per :class:`OutputLimit`, the legs whose speed that stage changed."""
    soil: _SoilState | None = None
    """Soil response state (spec rev. 57 285); ``None`` in run states unpickled from older
    code, which only run with the soil response off."""


@dataclass(frozen=True)
class _Reading:
    t_s: float
    cylinder_force_N: NDArray[np.float64]
    rod_stroke_m: NDArray[np.float64]
    """Rod position (oil compression removed): clearance, lift latch, probe."""
    motor_stroke_m: NDArray[np.float64]
    """``stroke_m``, the coordinate the stroke limit acts on (L1 motor position, L2 / machine
    piston position): stroke-end fault and clipping, crawler-zone estimate (R1)."""
    cylinder_force_lowpass_N: NDArray[np.float64]
    """``P_bar``: cylinder force through the crawler-rule low-pass, updated every period."""
    cylinder_force_lower_N: NDArray[np.float64]
    """R6-P lower-bound reading (fallback legs: head minus the rod-side model bound)."""
    cylinder_force_upper_N: NDArray[np.float64]
    head_only_force_N: NDArray[np.float64]
    """``p_h A_p``: the 350 bar check (P-3)."""


# --- controller ----------------------------------------------------------------------------


class C2Controller:
    """C2 levelling controller (design section 14); see the module docstring.

    Args:
        geometry: Machine quantities, usually :meth:`C2Geometry.from_params`.
        config: Gains, filters, thresholds and options; ``None`` = decided design values.
    """

    _fallback_guard_log: list[dict[str, Any]] | None = None
    """Spec 218.10 record (P-S8-13 complement): stretches of periods in which the F_min guard
    acts on a rod-side fallback leg. Class default for controllers pickled before it."""

    def __init__(self, geometry: C2Geometry, config: C2Config | None = None) -> None:
        self.geometry = geometry
        self.config = config if config is not None else C2Config()
        filters = self.config.filters
        period_s = self.config.period_s
        attitude_period_s = self.config.r8.imu_sample_period_s or period_s
        self._attitude = AttitudeEstimator(
            CascadedLowPass(
                filters.attitude_time_constant_s, filters.attitude_stage_count, attitude_period_s
            )
        )
        self._twist_load_filter: CascadedLowPass | None = None
        if filters.twist_load_time_constant_s is not None:
            self._twist_load_filter = CascadedLowPass(
                filters.twist_load_time_constant_s, 1, period_s
            )
        # R-2: extension at which a pad meets a level floor at the crawler bottom.
        self._touch_extension_m = geometry.operating_extension_m(0.0)
        self._completion_filter = CascadedLowPass(filters.completion_time_constant_s, 1, period_s)
        self._clearance_filter = CascadedLowPass(filters.clearance_time_constant_s, 1, period_s)
        self._crawler_rule_force_filter = CascadedLowPass(
            filters.crawler_rule_pressure_time_constant_s, 1, period_s
        )
        self._rate_attitude_window_size = max(
            1, round(self.config.probe.attitude_window_s / period_s)
        )
        self._check_window_size = max(1, round(self.config.target.check_average_s / period_s))
        self._check_clearance_target()
        self._floor_estimator = FloorPlaneEstimator(geometry)
        self._support_shadow = SupportGeometryShadow(
            geometry, self.config.support_pad_stiffness_N_m
        )
        self._pressures = TwoPressureMonitor(
            geometry.head_area_m2,
            geometry.annulus_area_m2,
            geometry.max_speed_m_s,
            geometry.F_min_N,
            period_s,
            self.config.load_estimate,
            self.config.two_pressure,
            geometry.rod_weight_N,
            stroke_max_m=geometry.stroke_max_m,
            retract_lock_rod_pressure_Pa=geometry.rod_lock_pressure_after_retract_Pa,
            counterbalance_lag_tau_s=geometry.counterbalance_lag_tau_s,
            body_mass_kg=geometry.superstructure_mass_kg,
            imu_lever_arm_m=geometry.imu_lever_arm_m,
        )
        self._pressures.set_offset_allowance_N(self.config.pressure_offset_allowance_N)
        self._standstill_gate = StandstillGate(
            self.config.standstill_gate, self.config.target.gyro_noise_std_rad_s, period_s
        )
        self._gyro_bias_window_s = self.config.target.gyro_bias_window_s(period_s)
        self._state = self._new_run_state()

    def _check_clearance_target(self) -> None:
        """Z1 (spec 2.6): the worst accepted target must keep 10 mm of stroke."""
        clearance_target = self.config.thresholds.clearance_target_m
        worst_stroke = WORST_ACCEPTED_STROKE_M + WORST_STROKE_PER_CLEARANCE * (
            clearance_target - REFERENCE_CLEARANCE_M
        )
        stroke_limit = ENVELOPE_STROKE_MAX_M - CLEARANCE_RULE_STROKE_MARGIN_M
        # P5 / 65.3: c*_max = 50 + (684.8 - 642.2) / 1.005 mm = 92.39 mm, not rounded.
        max_clearance = (
            REFERENCE_CLEARANCE_M
            + (stroke_limit - WORST_ACCEPTED_STROKE_M) / WORST_STROKE_PER_CLEARANCE
        )
        if worst_stroke > stroke_limit:
            raise ValueError(
                f"clearance_target_m {clearance_target:.4f} m above {max_clearance * 1e3:.2f} mm: "
                f"worst accepted stroke {worst_stroke:.4f} m > {stroke_limit:.4f} m; rule A was "
                "derived for the 50 mm target, re-run the envelope (dynamics-expert "
                "run_target_envelope.py)"
            )

    def _new_run_state(self) -> _RunState:
        r8 = self.config.r8
        delay = r8.output_delay_periods
        history_length = 1 if r8.fast_relevel is None else r8.fast_relevel.rate_intervals + 1
        return _RunState(
            seal_band_N=self.config.initial_seal_band_N,
            phase=C2Phase.CHECK,
            rate_attitude_recent=deque(maxlen=self._rate_attitude_window_size),
            check_attitudes=deque(maxlen=self._check_window_size),
            requested_target=self.config.target.target,
            output_queue=deque(np.zeros(LEG_COUNT) for _ in range(delay)),
            load_estimate_history=deque(maxlen=history_length),
            soil=_SoilState(),
        )

    @classmethod
    def from_params(cls, params: Params, config: C2Config | None = None) -> C2Controller:
        """Controller for the machine described by ``params``.

        Args:
            params: Simulation parameters (YAML).
            config: Explicit setting, used unchanged; ``None`` = decided design values with
                ``output_ramp_time_s`` = YAML ``actuator.command_ramp_s`` (0 there means no
                actuator limit, so the controller ramp is turned off as well).
        """
        if config is None:
            command_ramp_s = params.actuator.command_ramp_s
            config = C2Config(output_ramp_time_s=command_ramp_s if command_ramp_s > 0.0 else None)
        return cls(C2Geometry.from_params(params), config)

    # --- Controller protocol ---

    @property
    def period_s(self) -> float:
        """Control period the gains and filters were discretised for (s)."""
        return self.config.period_s

    def reset(self) -> None:
        """Clear filters, integrators, phase and probe bookkeeping; request ``config.target``."""
        self._attitude.reset()
        self._completion_filter.reset()
        self._clearance_filter.reset()
        self._crawler_rule_force_filter.reset()
        if self._twist_load_filter is not None:
            self._twist_load_filter.reset()
        self._floor_estimator.reset()
        self._support_shadow.reset()
        self._standstill_gate.reset()
        self._pressures.reset()
        self._pressures.set_offset_allowance_N(self.config.pressure_offset_allowance_N)
        self._state = self._new_run_state()
        self._fallback_guard_log = None

    def update(self, measurements: Measurements) -> Command:
        """Leg speed command for the next period (design 14.3 order: read, filter, phase, ramp)."""
        state = self._state
        reading = self._read(measurements)
        self._update_attitude_filters(measurements)
        self._watch_oil_temperature(measurements)
        state.last_reading = reading
        state.guard_m_s = None
        state.command_components = None
        state.output_limit_flags = _no_output_limits()
        phase_before = state.phase
        reanchor_stage_before = None if state.reanchor is None else state.reanchor.stage
        self._update_lifted_reapproach(reading)
        leg_speeds = self._phase_command(reading)
        if state.command_components is None:
            self._record_phase_path_command(leg_speeds)
        self._request_lock_tails(reading, phase_before, reanchor_stage_before)
        self._update_support_shadow(reading, phase_before)
        state.rate_attitude_recent.append(state.rate_attitude_rad)
        state.sample_count += 1
        slowed_speeds = self._slow_near_stroke_end(reading, leg_speeds)
        self._note_output_limit(OutputLimit.STROKE_END, leg_speeds, slowed_speeds)
        output = self._apply_output_ramp(slowed_speeds)
        moving = output != 0.0
        state.last_nonzero_output_m_s = np.where(moving, output, state.last_nonzero_output_m_s)
        applied = self._delay_output(output)
        if np.any(applied != 0.0):
            state.last_nonzero_command_t_s = measurements.t_s
        state.applied_output_m_s = applied
        return Command(t_s=measurements.t_s, leg_speed_m_s=applied)

    def _delay_output(self, output: NDArray[np.float64]) -> NDArray[np.float64]:
        """R8 output buffer: the command of ``d`` periods ago (zero speed before that)."""
        if self.config.r8.output_delay_periods == 0:
            return output
        queue = self._state.output_queue
        queue.append(output.copy())
        return queue.popleft()

    def meta(self) -> dict[str, Any]:
        """Name, settings and current friction band (JSON-serialisable, new dict per call)."""
        geometry = self.geometry
        r8 = self.config.r8
        return {
            "controller": C2_CONTROLLER_NAME,
            "design": DESIGN_SOURCE,
            "revision": R8_REVISION if r8.is_active else C2_REVISION,
            "period_s": self.config.period_s,
            # P-8: output delay, attitude read time (start IMU only), gain normalisation.
            "timing": {
                "d": r8.output_delay_periods,
                "late_imu": False,
                "delta_s": None,
                "imu_sample_period_s": r8.imu_sample_period_s,
            },
            "r8": r8.to_meta(),
            "twist_gain_stiffness": self._twist_gain_stiffness_meta(),
            "lifted_reapproach": [run.to_meta() for run in self._state.reapproach_history],
            "soil": self._soil_meta(),
            "locked_pressure_warning_note": (
                QUASI_STATIC_PRESSURE_NOTE if r8.is_instant_sampling else None
            ),
            "contact": str(self.config.contact),
            "initial_seal_band_N": self.config.initial_seal_band_N,
            "seal_band_N": self._state.seal_band_N,
            "output_ramp_time_s": self.config.output_ramp_time_s,
            "gains": asdict(self.config.gains),
            "filters": asdict(self.config.filters),
            "thresholds": {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in asdict(self.config.thresholds).items()
            },
            "probe": {key: str(value) if isinstance(value, StrEnum) else value
                      for key, value in asdict(self.config.probe).items()},
            # Spec 86.1 / 86.6 (return condition 1): the H4 direction next to the revision.
            "reanchor_direction": str(self.config.reanchor.direction),
            "reanchor": self._reanchor_meta(),
            "target": self._target_meta(),
            "floor_estimate_touch": (
                None
                if self._state.floor_estimate_touch is None
                else self._state.floor_estimate_touch.to_meta()
            ),
            "support_geometry": self._support_geometry_meta(),
            "is_geometry_valid": self._state.is_geometry_valid,
            "stationary_gate": self._standstill_gate.to_meta(),
            "rod_stroke_fallback": str(self.config.rod_stroke_fallback),
            "load_estimate": str(self.config.load_estimate),
            "two_pressure": self._pressures.meta(),
            "fallback_guard": [dict(stretch) for stretch in self._fallback_guard_log or []],
            "geometry_judge": {
                "settings": {**asdict(self.config.geometry_judge),
                             "mode": str(self.config.geometry_judge.mode)},
                "is_active": self._is_geometry_judge_active(),
                "triggers": list(self._state.support_triggers),
                "repeat_latched": sorted(self._state.support_repeat_latched),
            },
            "lock_tail": {**asdict(self.config.lock_tail),
                          "mode": str(self.config.lock_tail.mode),
                          "count": self._state.lock_tail_count},
            "probe_correction_sensitivity_N_m": (
                None
                if self.config.probe_correction_sensitivity_N_m is None
                else list(self.config.probe_correction_sensitivity_N_m)
            ),
            "zero_calibration": self._zero_calibration_meta(),
            "geometry": {
                "twist_vector": geometry.twist_vector.tolist(),
                "nominal_pad_stiffness_N_m": geometry.nominal_pad_stiffness_N_m,
                "F_min_N": geometry.F_min_N,
                "max_speed_m_s": geometry.max_speed_m_s,
                "stroke_max_m": geometry.stroke_max_m,
                "head_area_m2": geometry.head_area_m2.tolist(),
                "annulus_area_m2": geometry.annulus_area_m2.tolist(),
                "locked_force_limit_N": geometry.locked_force_limit_N.tolist(),
                "crawler_xy_box_m": [list(bounds) for bounds in CRAWLER_XY_BOX_M],
            },
        }

    def _twist_gain_stiffness_meta(self) -> dict[str, Any]:
        """P-8 / P-R8-7: gain reference, raw and used scale, denominator, leg count."""
        state = self._state
        scale = self._twist_gain_scale()
        stiffness = self._twist_gain_stiffness_N_m()
        return {
            "reference": str(self.config.r8.twist_gain_reference),
            "measured_scale": state.twist_stiffness_scale,
            "raw_ratio": state.twist_stiffness_raw_ratio,
            "scale_in_use": 1.0 if scale is None else scale,
            "grounded_leg_count": state.twist_stiffness_leg_count,
            "denominator": STIFFNESS_SCALE_DENOMINATOR,
            "denominator_N_m": self.geometry.load_sensitivity_diag_N_m.tolist(),
            "stiffness_N_m": self.geometry.nominal_pad_stiffness_N_m
            if stiffness is None
            else stiffness,
        }

    def _zero_calibration_meta(self) -> dict[str, Any]:
        """E-3 / E-6: settings, the round-trip result, offsets and allowances in use."""
        calibration = self._state.zero_calibration
        return {
            "settings": self.config.zero_calibration.to_meta(),
            "is_active": self.config.zero_calibration.is_enabled,
            "result": None if calibration is None else calibration.to_meta(),
            "offsets_N": self._pressures.zero_offsets_N.tolist(),
            "pressure_offset_allowance_N": self._pressures.offset_allowance_N.tolist(),
            "calibration_oil_temperature_C": self._state.calibration_oil_temperature_C,
        }

    def _target_meta(self) -> dict[str, Any]:
        """T4: target, reference, code, ``(phi_c, theta_c)``, settings and every decision."""
        state = self._state
        settings = self.config.target

        def as_list(target: AttitudeTarget | None) -> list[float] | None:
            return None if target is None else [target.roll_rad, target.pitch_rad]

        crawler = state.crawler_attitude_rad
        return {
            "requested_at_start_rad": as_list(settings.target),
            "slope_limit_mode": str(settings.slope_limit_mode),
            "limits_rad": asdict(settings.limits),
            "acceptance": str(settings.acceptance),
            "check_time_s": settings.check_time_s,
            "check_average_s": settings.check_average_s,
            "check_quiet_after_motion_s": settings.check_quiet_after_motion_s,
            "check_attitude_source": (
                "raw_tilt" if self.config.r8.uses_raw_check_attitude else "filtered"
            ),
            "check_window": None if state.check_window is None else dict(state.check_window),
            "ramp_rad_s": [settings.roll_ramp_rate_rad_s, settings.pitch_ramp_rate_rad_s],
            "crawler_attitude_rad": None if crawler is None else list(crawler),
            "crawler_settle_map": settings.settle_map.to_meta(),
            "floor_estimate_rad": self._last_floor_estimate(),
            "gyro_bias_rad_s": None
            if state.gyro_bias_rad_s is None
            else list(state.gyro_bias_rad_s),
            "gyro_bias": self._gyro_bias_meta(),
            "target_rad": as_list(state.active_target),
            "reference_rad": as_list(state.reference),
            "code": None if state.target_code is None else str(state.target_code),
            "checks": [check.to_meta() for check in state.target_checks],
        }

    def _support_geometry_meta(self) -> dict[str, Any]:
        """GE1' shadow meta plus ``reference_source``.

        ``touch_only`` with the pressure judge (spec 44.4, R5-M): without a probe the refresh
        condition 'last probe four legs grounded' never holds, so the TOUCH-end reference stays
        for the whole run; otherwise the source of the current reference (``None`` before one).
        """
        meta = self._support_shadow.to_meta()
        reference = self._support_shadow.reference
        if self.config.contact is ContactJudge.PRESSURE:
            meta["reference_source"] = "touch_only"
        else:
            meta["reference_source"] = None if reference is None else reference.source
        return meta

    def _gyro_bias_meta(self) -> dict[str, Any]:
        """B1': settings, planned window ``T_b`` and the CHECK result (length, value, accepted)."""
        settings = self.config.target
        estimate = self._state.gyro_bias_estimate
        return {
            "settings": {
                "check_max_s": settings.check_max_s,
                "gyro_noise_std_rad_s": settings.gyro_noise_std_rad_s,
                "gyro_bias_target_std_rad_s": settings.gyro_bias_target_std_rad_s,
                "gyro_bias_max_rate_rms_rad_s": settings.gyro_bias_max_rate_rms_rad_s,
                "gyro_bias_max_rate_rms_window_s": settings.gyro_bias_max_rate_rms_window_s,
                "gyro_bias_max_rate_rms_cap_rad_s": settings.gyro_bias_max_rate_rms_cap_rad_s,
                "gyro_bias_plausible_rad_s": settings.gyro_bias_plausible_rad_s,
            },
            "window_s": self._gyro_bias_window_s,
            "motion_limit_rad_s": settings.gyro_bias_motion_limit_rad_s(self._gyro_bias_window_s),
            "result": None if estimate is None else estimate.to_meta(),
        }

    def _reanchor_meta(self) -> dict[str, Any]:
        """Re-anchoring settings and result (design 17.7 Q9)."""
        state = self._state
        run = state.reanchor
        return {
            "settings": {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in asdict(self.config.reanchor).items()
            },
            "outcome": state.reanchor_outcome,
            "outcomes": list(state.reanchor_outcomes),
            "theta_crawler_rad": state.theta_crawler_rad,
            "anchor_pitch_rad": state.reanchor_anchor_pitch_rad,
            "stop_force_N": None if run is None else list(run.stop_force_N),
            "seal_band_used_N": None if run is None else run.seal_band_used_N,
            "stop_readings_N": (
                None
                if run is None
                else [{"leg": leg, "reading_N": force} for leg, force in run.stop_readings_N]
            ),
            "stop_predicted_readings_N": (
                None
                if run is None
                else [
                    {"leg": leg, "reading_N": force}
                    for leg, force in run.stop_predicted_readings_N
                ]
            ),
        }

    # --- diagnostics ---

    @property
    def computed_output_m_s(self) -> NDArray[np.float64]:
        """Leg speeds computed in the last period, before the output delay (P-R8-6, a copy).

        With ``d = 0`` this is the returned command; with ``d = 1`` it is output next period.
        """
        return self._state.previous_output_m_s.copy()

    @property
    def command_components_m_s(self) -> dict[str, NDArray[np.float64]]:
        """Parts of the command computed in the last period (P-R8-14, P-R8-15; copies).

        Names :data:`COMMAND_COMPONENT_NAMES` -> 4 leg speeds (m/s): ``attitude`` ``A [0, phi,
        theta]``, ``heave`` ``A [z, 0, 0]``, ``twist`` and ``guard`` (the twist-loop and F_min
        guard shares of ``n tau_dot``), ``reapproach`` (twist mode: ``n tau_dot_lift``; leg
        mode: the override minus the other parts on the lifted leg) and ``phase_path``. In a
        LEVEL period ``phase_path`` is zero; in any other period (CHECK zero calibration, TOUCH,
        PROBE, READY, REANCHOR, a lock tail, FAULT, ...) it holds that phase's command and the
        other parts are zero. Their sum is :attr:`raw_output_m_s` (to rounding). Empty before
        the first period.
        """
        components = self._state.command_components
        if components is None:
            return {}
        return {name: speeds.copy() for name, speeds in components.items()}

    @property
    def raw_output_m_s(self) -> NDArray[np.float64]:
        """Leg speeds of the last period before the :class:`OutputLimit` stages (P-R8-15, a copy).

        LEVEL: the unscaled command (leg-mode re-approach: the lifted leg at its override
        speed); other phases: the phase command before the REANCHOR stroke-end clip, the end
        slowdown and the increment limit or ramp. Where no stage acted
        (:attr:`output_limit_flags` all false) it equals :attr:`computed_output_m_s` to the
        rounding of ``u_prev + (u - u_prev)`` (last bit; exact without limit or ramp).
        """
        return self._state.raw_output_m_s.copy()

    @property
    def output_limit_flags(self) -> dict[str, NDArray[np.bool_]]:
        """Per :class:`OutputLimit` value, the legs that stage changed in the last period
        (P-R8-15, copies; all false before the first period). The output delay is not a
        stage: it is the gap between :attr:`computed_output_m_s` and the issued command."""
        return {name: legs.copy() for name, legs in self._state.output_limit_flags.items()}

    @property
    def phase(self) -> C2Phase:
        """Current phase."""
        return self._state.phase

    @property
    def seal_band_N(self) -> float:
        """Current seal-friction band ``F_band`` of the combined judge (N)."""
        return self._state.seal_band_N

    @property
    def filtered_attitude_rad(self) -> tuple[float, float]:
        """Roll and pitch after the 2nd-order attitude low-pass (rad)."""
        return self._state.roll_rad, self._state.pitch_rad

    @property
    def is_in_crawler_zone(self) -> bool:
        """Crawler-zone latch of LEVEL step 8 (R1): legs may not retract while it is on."""
        return self._state.in_crawler_zone

    @property
    def reanchor_outcome(self) -> str | None:
        """``None`` until decided or while running, then ``completed`` / ``aborted:*`` /
        ``skipped:*``."""
        return self._state.reanchor_outcome

    @property
    def events(self) -> tuple[C2Event, ...]:
        """Events of the run, oldest first."""
        return tuple(self._state.events)

    @property
    def reground_leg(self) -> int | None:
        """Leg (LEG_ORDER index) being re-grounded after a probe round, ``None`` otherwise."""
        reground = self._state.reground
        return None if reground is None else reground.leg

    @property
    def rate_attitude_rad(self) -> tuple[float, float]:
        """Bias-corrected gyro roll / pitch rate integrated since the run start (rad)."""
        return self._state.rate_attitude_rad

    @property
    def support_geometry(self) -> SupportGeometry | None:
        """Last GE1 shadow sample (``None`` before the floor normal is stored)."""
        return self._support_shadow.latest

    @property
    def is_geometry_valid(self) -> bool:
        """GE1'-c standstill gate of the last period (the shadow flags count only then)."""
        return self._state.is_geometry_valid

    @property
    def stationary_gate(self) -> StandstillGateState:
        """GE1'-c gate values of the last period (open flag, command-free time, rates)."""
        return self._standstill_gate.state()

    @property
    def gyro_bias_rad_s(self) -> tuple[float, float] | None:
        """Gyro roll / pitch bias removed since CHECK (``None`` = not removed)."""
        return self._state.gyro_bias_rad_s

    @property
    def gyro_bias_estimate(self) -> GyroBiasEstimate | None:
        """B1' result of CHECK: window, CHECK length, estimate and whether it was accepted."""
        return self._state.gyro_bias_estimate

    @property
    def probe_history(self) -> tuple[tuple[ProbeResult, ...], ...]:
        """Results of every completed probe round, oldest first."""
        return tuple(self._state.probe_history)

    @property
    def target(self) -> AttitudeTarget | None:
        """Accepted final target ``(phi_t, theta_t)``; ``None`` before acceptance or in IDLE."""
        return self._state.active_target

    @property
    def reference(self) -> AttitudeTarget | None:
        """Ramped reference ``(phi_r, theta_r)`` the attitude loop follows."""
        return self._state.reference

    @property
    def target_code(self) -> TargetCode | None:
        """Code of the last target decision."""
        return self._state.target_code

    @property
    def crawler_attitude_rad(self) -> tuple[float, float] | None:
        """``(phi_c, theta_c)`` measured in CHECK."""
        return self._state.crawler_attitude_rad

    @property
    def target_checks(self) -> tuple[TargetCheck, ...]:
        """Every target decision of the run, oldest first."""
        return tuple(self._state.target_checks)

    @property
    def load_bands(self) -> list[LoadBand] | None:
        """Friction-band verdict of the last readings (``None`` before the first update).

        With the R8 sample confirmation a leg is ABOVE / BELOW only after that many
        consecutive raw verdicts, AMBIGUOUS until then.
        """
        raw_bands = self._raw_load_bands()
        confirmation = self.config.r8.confirmation
        if raw_bands is None or not confirmation.is_active:
            return raw_bands
        state = self._state
        confirmed = []
        for band, above, below in zip(
            raw_bands, state.above_counts, state.below_counts, strict=True
        ):
            if band is LoadBand.ABOVE and above < confirmation.above_samples:
                band = LoadBand.AMBIGUOUS
            elif band is LoadBand.BELOW and below < confirmation.below_samples:
                band = LoadBand.AMBIGUOUS
            confirmed.append(band)
        return confirmed

    def _count_band_samples(self) -> None:
        """R8: consecutive raw ABOVE / BELOW verdicts per leg, updated every period."""
        raw_bands = self._raw_load_bands()
        if raw_bands is None or not self.config.r8.confirmation.is_active:
            return
        state = self._state
        is_above = np.array([band is LoadBand.ABOVE for band in raw_bands])
        is_below = np.array([band is LoadBand.BELOW for band in raw_bands])
        state.above_counts = np.where(is_above, state.above_counts + 1, 0)
        state.below_counts = np.where(is_below, state.below_counts + 1, 0)

    def _raw_load_bands(self) -> list[LoadBand] | None:
        """Friction-band verdict of the last reading alone."""
        forces = self._state.last_forces
        if forces is None:
            return None
        bands = self._leg_seal_bands_N()
        lower_bands = classify_load(forces.lower, bands, self.geometry.F_min_N)
        if forces.upper is forces.lower:
            return lower_bands
        # R6-P fallback: ABOVE from the lower bound, BELOW only from the upper bound.
        upper_bands = classify_load(forces.upper, bands, self.geometry.F_min_N)
        return [
            LoadBand.AMBIGUOUS
            if low is LoadBand.BELOW and high is not LoadBand.BELOW
            else low
            for low, high in zip(lower_bands, upper_bands, strict=True)
        ]

    # --- operator input ---

    def request_target(self, target: AttitudeTarget) -> TargetCheck:
        """Ask for a new roll / pitch target (operator setting, not a sensor input).

        READY: judged now with A0-A5 against the last readings; accepted -> the reference
        ramps to it and the run re-levels (REANCHOR re-armed, U3); rejected -> READY and the
        target stay, warning event. IDLE: CHECK restarts and judges it (``PENDING_CHECK``).
        Any other phase: ``REJ_BUSY``, nothing changes.
        """
        state = self._state
        if state.phase is C2Phase.IDLE:
            self._restart_check(target)
            return self._record_check(TargetCheck(target, None, TargetCode.PENDING_CHECK))
        if state.phase is not C2Phase.READY or state.last_reading is None:
            check = self._record_check(TargetCheck(target, None, TargetCode.REJ_BUSY))
            self._add_event(self._last_time_s(), str(TargetCode.REJ_BUSY), is_warning=True)
            return check
        return self._change_target_in_ready(target, state.last_reading)

    def request_probe(self) -> bool:
        """Ask for one more probe round from READY (test-bench / operator entry point).

        Spec rev. 39 205.3 "탐침 반복" episodes (P-S8-2). The controller never calls it, so a
        run without it is unchanged bit for bit. Accepted only in READY with the combined judge
        (the pressure judge has no probe) and no U67 lock tail pending: the next update runs a
        probe round as DONE -> PROBE does (P-R8-11 low-load abort, D5 band widen-only, P-5
        stiffness scale, then READY; a weak leg is re-grounded while the run's round count is
        below ``max_rounds``). Events ``probe_requested`` / ``probe_request_rejected:<phase>``.

        Returns:
            Whether the request was accepted.
        """
        state = self._state
        is_accepted = (
            state.phase is C2Phase.READY
            and self.config.contact is ContactJudge.COMBINED
            and not state.lock_tail_speeds
        )
        if not is_accepted:
            reason = state.phase.value if state.phase is not C2Phase.READY else "busy"
            self._add_event(self._last_time_s(), f"probe_request_rejected:{reason}",
                            is_warning=True)
            return False
        self._add_event(self._last_time_s(), "probe_requested")
        state.phase = C2Phase.PROBE
        state.probe_round = None
        state.reground = None
        return True

    # --- input and filters ---

    def _read(self, measurements: Measurements) -> _Reading:
        state = self._state
        forces = self._pressures.read(
            measurements.t_s,
            np.asarray(measurements.head_pressure_Pa),
            measurements.rod_pressure_Pa,
            state.applied_output_m_s,  # what the legs do now (d = 0: the last output)
            state.phase is C2Phase.READY,
            self._leg_seal_bands_N(),
            stroke_m=measurements.stroke_m,  # P-S8-11 ③ stroke check only (off by default)
            imu_specific_force_z_m_s2=_last_imu_specific_force_z_m_s2(measurements),
            is_crawler_lifted=state.phase in CRAWLER_LIFTED_PHASES,
            imu_gyro_rad_s=measurements.imu_angular_rate_samples_rad_s,  # lever term
        )
        self._take_pressure_events(measurements.t_s)
        force = forces.nominal
        motor_stroke = np.array(measurements.stroke_m)
        if measurements.stroke_corrected_m is not None:
            rod_stroke = np.array(measurements.stroke_corrected_m)
        else:
            rod_stroke = self._rod_stroke_without_sensor(motor_stroke, force)
        # R1 (14.3): P_bar runs in every phase so that it is settled when LEVEL starts.
        force_lowpass = self._crawler_rule_force_filter.update(force)
        state.last_cylinder_force_N = force
        state.last_forces = forces
        self._count_band_samples()
        if self.config.r8.fast_relevel is not None:
            state.load_estimate_history.append(self._load_estimate_N(forces.lower))
        return _Reading(
            measurements.t_s,
            force,
            rod_stroke,
            motor_stroke,
            force_lowpass,
            forces.lower,
            forces.upper,
            forces.head_only,
        )

    def _take_pressure_events(self, t_s: float) -> None:
        """R6-P monitor events; a head-side fault stops the run (FAULT, U45)."""
        for name, is_warning in self._pressures.pop_events():
            self._add_event(t_s, name, is_warning=is_warning)
        if self._pressures.head_fault_legs and self._state.phase is not C2Phase.FAULT:
            self._state.phase = C2Phase.FAULT

    def _leg_seal_bands_N(self) -> NDArray[np.float64]:
        """``F_band`` per leg (U65: at least 13 kN on a rod-side fallback leg)."""
        return self._pressures.leg_seal_bands_N(self._state.seal_band_N)

    def _rod_stroke_without_sensor(
        self, motor_stroke_m: NDArray[np.float64], cylinder_force_N: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Rod stroke ``s - F / k_oil`` for a reading without ``stroke_corrected_m``.

        L1 lumps the oil column and the series parts below the piston into one pad stiffness
        split at ``e_op`` (``1 / k_oil(e_op) + 1 / k_s = 1 / k_n``); ``k_oil(e)`` at another
        extension breaks that split by more than 0.5 mm per 50 kN beyond about 0.10 m from
        ``e_op`` (dynamics-expert), so the L1 default keeps ``k_oil(e_op)``.
        """
        fallback = self.config.rod_stroke_fallback
        geometry = self.geometry
        if fallback is RodStrokeFallback.REQUIRED:
            raise ValueError(
                "Measurements.stroke_corrected_m is missing and rod_stroke_fallback is 'required'"
            )
        if fallback is RodStrokeFallback.STROKE_OIL_COLUMN:
            oil_stiffness = geometry.oil_stiffness_N_m(motor_stroke_m)
        else:
            clearance_m = self.config.thresholds.clearance_target_m
            oil_stiffness = geometry.oil_stiffness_N_m(geometry.operating_extension_m(clearance_m))
        return motor_stroke_m - cylinder_force_N / oil_stiffness

    def _filtered_attitude(self, measurements: Measurements) -> AttitudeEstimate:
        """Attitude low-pass on the period mean, or (R8 P-3) on every IMU-rate sample."""
        if self.config.r8.imu_sample_period_s is None:
            estimate = self._attitude.update(measurements.t_s, measurements.specific_force_m_s2)
            self._state.period_mean_raw_tilt_rad = (estimate.roll_raw_rad, estimate.pitch_raw_rad)
            return estimate
        samples = measurements.imu_specific_force_samples_m_s2
        if samples is None:
            raise ValueError(
                "r8.imu_sample_period_s is set: Measurements.imu_specific_force_samples_m_s2 "
                "must carry the IMU-rate samples of the period (spec 139 P-3)"
            )
        sample_period_s = self.config.r8.imu_sample_period_s
        raw_tilts = self._state.period_raw_tilts
        raw_tilts.clear()
        last_index = len(samples) - 1
        for index, sample in enumerate(samples):
            # The last sample of the period closes at t_s (runner box averages, P-3).
            sample_t_s = measurements.t_s - (last_index - index) * sample_period_s
            estimate = self._attitude.update(sample_t_s, sample)
            raw_tilts.append(_RawTilt(sample_t_s, estimate.roll_raw_rad, estimate.pitch_raw_rad))
        return estimate

    def _update_attitude_filters(self, measurements: Measurements) -> None:
        estimate = self._filtered_attitude(measurements)
        completion = self._completion_filter.update([estimate.roll_rad, estimate.pitch_rad])
        state = self._state
        state.roll_rad, state.pitch_rad = estimate.roll_rad, estimate.pitch_rad
        state.completion_roll_rad, state.completion_pitch_rad = map(float, completion)
        # The accelerometer tilt carries the apparent tilt of the rocking (0.3-0.5 deg at C1
        # during a probe in the reduced model, against a 0.024 deg probe response); the gyro
        # does not see it. Sensor axes = body axes, small angles: roll / pitch rate = omega_x, y.
        # Spec P3: the gyro bias (and in the field the earth rate) measured in CHECK is removed.
        roll_rate, pitch_rate = (float(rate) for rate in measurements.angular_rate_rad_s[:2])
        state.gyro_rate_rad_s = (roll_rate, pitch_rate)
        roll_bias, pitch_bias = state.gyro_bias_rad_s or (0.0, 0.0)
        previous_roll, previous_pitch = state.rate_attitude_rad
        period_s = self.config.period_s
        state.rate_attitude_rad = (
            previous_roll + (roll_rate - roll_bias) * period_s,
            previous_pitch + (pitch_rate - pitch_bias) * period_s,
        )
        if self.config.soil.enable:
            self._record_settle_tilt()

    def _target_rad(self) -> tuple[float, float]:
        """Final target ``(phi_t, theta_t)``; level while none is accepted."""
        target = self._state.active_target
        if target is None:
            return 0.0, 0.0
        return target.roll_rad, target.pitch_rad

    def _reference_rad(self) -> tuple[float, float]:
        """Ramped reference ``(phi_r, theta_r)`` (T1); level while none is accepted."""
        reference = self._state.reference
        if reference is None:
            return 0.0, 0.0
        return reference.roll_rad, reference.pitch_rad

    def _completion_deviation_rad(self) -> float:
        """Largest completion-filtered roll / pitch deviation from the active target."""
        state = self._state
        target_roll, target_pitch = self._target_rad()
        return max(
            abs(state.completion_roll_rad - target_roll),
            abs(state.completion_pitch_rad - target_pitch),
        )

    def _load_estimate_N(self, cylinder_force_N: NDArray[np.float64]) -> NDArray[np.float64]:
        """Lower load estimate of the readings (pass ``cylinder_force_lower_N``)."""
        if self.config.contact is ContactJudge.PRESSURE:
            return cylinder_force_N
        return cylinder_force_N - self._leg_seal_bands_N()

    def _zero_speeds(self) -> NDArray[np.float64]:
        return np.zeros(LEG_COUNT)

    # --- phases ---

    def _phase_command(self, reading: _Reading) -> NDArray[np.float64]:
        if self._state.phase is C2Phase.CHECK:
            calibration_speeds = self._zero_calibration_step(reading)
            if not self._check_step(reading):
                return calibration_speeds
        phase = self._state.phase
        if phase is C2Phase.TOUCH:
            return self._touch(reading)
        if phase in (C2Phase.FAULT, C2Phase.IDLE):
            return self._zero_speeds()
        tail_speeds = self._lock_tail_step(reading.t_s)
        if tail_speeds is not None:
            return tail_speeds  # U62: the phase waits for the tail and its settle
        self._advance_reference()
        if phase is C2Phase.REANCHOR:
            reanchor_speeds = self._reanchor_step(reading)
            self._record_phase_path_command(reanchor_speeds)
            clipped_speeds = self._clip_at_stroke_ends(reading, reanchor_speeds)
            self._note_output_limit(OutputLimit.STROKE_END, reanchor_speeds, clipped_speeds)
            return clipped_speeds
        is_reanchor_at_done = not self._is_reanchor_after_probe()
        if phase is C2Phase.DONE and is_reanchor_at_done and not self._is_reanchor_decided():
            # Decided before the re-level check, as the reduced model the design verified.
            skip_reason = self._reanchor_skip_reason(reading)
            if skip_reason is None:
                return self._start_reanchor(reading)
            self._skip_reanchor(reading.t_s, skip_reason)
        if phase is not C2Phase.LEVEL:
            held = self._hold_probe_or_relevel(reading)
            if held is not None:
                return held
        return self._level(reading)

    def _touch(self, reading: _Reading) -> NDArray[np.float64]:
        """Extend each leg until its load holds above the touchdown level (14.4, R1).

        A leg latches as touched once the load condition has held without a break for
        ``touch_hold_s``; a break drops the candidate. Touched and candidate legs stop, a leg
        that has seen the load once approaches at ``touch_approach_speed_fraction`` of ``v_max``
        and the others extend at ``v_max``. All legs touched -> LEVEL.
        """
        state = self._state
        thresholds = self.config.thresholds
        touch_level = thresholds.touch_load_factor * self.geometry.F_min_N
        bears_touch_load = self._touchdown_load_N(reading) >= touch_level
        was_touched = state.touched.copy()
        is_waiting = self._update_touch_latches(bears_touch_load, reading.t_s)
        for leg in np.flatnonzero(state.touched & ~was_touched):
            self._floor_estimator.record_latch(
                int(leg),
                reading.t_s,
                float(reading.rod_stroke_m[leg]),
                (state.roll_rad, state.pitch_rad),
            )
        self._update_touch_seen(bears_touch_load)
        max_speed = self.geometry.max_speed_m_s
        approach_speed = np.where(
            state.touch_seen,
            thresholds.touch_approach_speed_fraction * max_speed,
            self._free_extension_speeds(reading),
        )
        leg_speeds = np.where(state.touched | is_waiting, 0.0, approach_speed)
        if state.touched.all():
            state.phase = C2Phase.LEVEL
            state.theta_crawler_rad = state.pitch_rad
            state.reanchor_anchor_pitch_rad = state.pitch_rad
            state.roll_integral = 0.0
            state.pitch_integral = 0.0
            self._record_floor_estimate(reading.t_s)
        return leg_speeds

    def _free_extension_speeds(self, reading: _Reading) -> NDArray[np.float64] | float:
        """Speed of a leg that has not seen its touch load: ``v_max``, or (R-2) the touch-window
        speed once its motor stroke is within the window of the level-floor touch extension."""
        r8 = self.config.r8
        max_speed = self.geometry.max_speed_m_s
        if r8.touch_window_m is None:
            return max_speed
        window_start_m = self._touch_extension_m - r8.touch_window_m
        is_in_window = reading.motor_stroke_m >= window_start_m
        return np.where(is_in_window, r8.touch_window_speed_fraction * max_speed, max_speed)

    def _record_floor_estimate(self, t_s: float) -> None:
        """X9: shadow floor estimate (B) at the end of TOUCH; meta and an event only."""
        estimate = self._floor_estimator.estimate(self.config.target.limits)
        self._state.floor_estimate_touch = estimate
        if estimate is not None:
            self._add_event(t_s, "floor_estimate_touch")

    def _update_support_shadow(self, reading: _Reading, phase_before: C2Phase) -> None:
        """GE1' (spec 37.3, 38): reference at TOUCH end, gate, conditional refresh, sample.

        The pads are rotated with the filtered attitude, whose lag reads as false pad heights
        while the body turns (spec 32.1); the standstill gate keeps those samples out of the
        flags. Shadow only: nothing here feeds back into a phase or a command.
        """
        state = self._state
        is_touch_end = phase_before is C2Phase.TOUCH and state.phase is not C2Phase.TOUCH
        if is_touch_end:
            estimate = state.floor_estimate_touch
            normal = None if estimate is None else floor_normal(estimate.floor_rad)
            self._store_support_reference(reading, "touch", normal)
        is_geometry_valid = self._update_standstill_gate(reading.t_s)
        self._refresh_support_reference(reading, phase_before, is_geometry_valid)
        self._refresh_load_reference(reading, phase_before, is_geometry_valid)
        newly_held = self._support_shadow.update(
            reading.t_s,
            (state.roll_rad, state.pitch_rad),
            reading.rod_stroke_m,
            reading.cylinder_force_N,
            is_geometry_valid,
        )
        for condition in newly_held:
            self._add_event(reading.t_s, _shadow_event_name(condition))
        self._act_on_support_change(reading, newly_held)

    def _store_support_reference(
        self, reading: _Reading, source: str, normal: NDArray[np.float64] | None = None
    ) -> None:
        state = self._state
        state.support_reference_loads_N = np.array(reading.cylinder_force_N, dtype=float)
        if source == str(C2Phase.READY):
            state.is_ready_reference_refreshed = True
        self._support_shadow.store_reference(
            reading.t_s,
            (state.roll_rad, state.pitch_rad),
            reading.rod_stroke_m,
            reading.cylinder_force_N,
            source,
            normal,
        )

    def _update_standstill_gate(self, t_s: float) -> bool:
        """GE1'-c: bias-removed gyro rates, command-free time and phase -> ``is_geometry_valid``.

        The command of period ``k`` acts until ``t_k + T``, so the command-free time at ``t`` is
        ``t - t_last_nonzero - T``.
        """
        state = self._state
        roll_bias, pitch_bias = state.gyro_bias_rad_s or (0.0, 0.0)
        roll_rate, pitch_rate = state.gyro_rate_rad_s
        last_command_s = state.last_nonzero_command_t_s
        zero_command_s = (
            math.inf if last_command_s is None else t_s - last_command_s - self.config.period_s
        )
        state.is_geometry_valid = self._standstill_gate.update(
            t_s,
            (roll_rate - roll_bias, pitch_rate - pitch_bias),
            zero_command_s,
            state.phase in GEOMETRY_GATE_PHASES,
        )
        return state.is_geometry_valid

    def _refresh_support_reference(
        self, reading: _Reading, phase_before: C2Phase, is_geometry_valid: bool
    ) -> None:
        """GE1'-b: a DONE / READY stay refreshes the reference once, on the first period with
        the gate open, and only after a probe round with four grounded legs and nothing to
        re-ground; otherwise the previous reference stays."""
        state = self._state
        if state.phase not in REFERENCE_UPDATE_PHASES:
            state.is_reference_update_pending = False
            return
        if state.phase is not phase_before:
            state.is_reference_update_pending = True
            if state.phase is C2Phase.READY:
                state.is_ready_reference_refreshed = False
        can_refresh = is_geometry_valid and state.does_last_probe_accept_support
        if state.is_reference_update_pending and can_refresh:
            self._store_support_reference(reading, str(state.phase))
            state.is_reference_update_pending = False

    def _refresh_load_reference(
        self, reading: _Reading, phase_before: C2Phase, is_geometry_valid: bool
    ) -> None:
        """Spec 110.1: the load baseline of P-4 D5 and E-5, apart from the GE1' reference.

        Every DONE / READY entry suspends the old baseline; the first period of the stay with
        the GE1'-c gate open and every leg command zero for ``load_reference_settle_s`` stores
        a new one. No probe condition (a run without probes stores it too), never at the
        TOUCH end, and not while a U67 lock tail is pending (it would move the legs next).
        The monitor stores the mean over ``load_reference_mean_s`` (spec 120); the store time
        does not depend on it.
        """
        state = self._state
        if state.phase not in REFERENCE_UPDATE_PHASES:
            state.is_load_reference_pending = False
            return
        if state.phase is not phase_before:
            state.is_load_reference_pending = True
            self._pressures.suspend_load_reference()
        settle_s = self.config.two_pressure.load_reference_settle_s
        is_command_free = self._pressures.command_free_s >= settle_s - 1e-9
        is_settled = is_command_free and not state.lock_tail_speeds
        if state.is_load_reference_pending and is_geometry_valid and is_settled:
            self._pressures.store_load_reference(
                reading.t_s, reading.cylinder_force_N, str(state.phase)
            )
            state.is_load_reference_pending = False

    def _last_floor_estimate(self) -> list[float] | None:
        checks = self._state.target_checks
        floors = [check.floor_estimate_rad for check in checks if check.floor_estimate_rad]
        return list(floors[-1]) if floors else None

    def _update_touch_latches(
        self, bears_touch_load: NDArray[np.bool_], t_s: float
    ) -> NDArray[np.bool_]:
        """Latch legs whose touchdown load held ``touch_hold_s``; return the waiting candidates."""
        state = self._state
        hold_s = self.config.thresholds.touch_hold_s
        is_waiting = np.zeros(LEG_COUNT, dtype=bool)
        for leg in range(LEG_COUNT):
            if state.touched[leg]:
                continue
            if not bears_touch_load[leg]:
                state.touch_candidate_since_s[leg] = None
                continue
            since_s = state.touch_candidate_since_s[leg]
            if since_s is None:
                since_s = state.touch_candidate_since_s[leg] = t_s
            if t_s - since_s >= hold_s - TOUCH_HOLD_SLACK_S:
                state.touched[leg] = True
            else:
                is_waiting[leg] = True
        return is_waiting

    def _update_touch_seen(self, bears_touch_load: NDArray[np.bool_]) -> None:
        """Latch ``touch_seen`` after ``touch_seen_samples`` touchdown-load samples in a row
        (combined judge; the pressure judge keeps the one-sample latch)."""
        state = self._state
        state.touch_load_counts = np.where(bears_touch_load, state.touch_load_counts + 1, 0)
        required_samples = 1
        if self.config.contact is not ContactJudge.PRESSURE:
            required_samples = self.config.r8.touch_seen_samples
        state.touch_seen |= state.touch_load_counts >= required_samples

    def _touchdown_load_N(self, reading: _Reading) -> NDArray[np.float64]:
        if self.config.contact is ContactJudge.PRESSURE:
            return reading.cylinder_force_N
        if self.config.r8.touch_free_air_min_travel_m is None:
            return self._touchdown_load_from_touch_entry_N(reading)
        return self._touchdown_load_from_moving_samples_N(reading)

    def _touchdown_load_from_moving_samples_N(self, reading: _Reading) -> NDArray[np.float64]:
        """P-S8-6 (spec rev. 43 213.3.1, U-S8-11): free-air reference from moving samples.

        With ``d = 1`` the first TOUCH samples still hold the CHECK end, where the seal
        friction acts in the retracting direction (-F_s - m g). A median over them makes the
        friction reversal of the first moving sample (2 F_s) look like touchdown load, which
        latched front legs in the air at F_s 8 kN. Only samples whose motor stroke has
        advanced ``touch_free_air_min_travel_m`` since TOUCH entry enter the reference, for
        ``free_air_window_s`` from the leg's first such sample; a leg with fewer than
        ``touch_free_air_min_samples`` of them is not judged (``-inf``).
        """
        state = self._state
        r8 = self.config.r8
        if state.touch_entry_motor_stroke_m is None:
            state.touch_entry_motor_stroke_m = reading.motor_stroke_m.copy()
        travel_m = reading.motor_stroke_m - state.touch_entry_motor_stroke_m
        has_moved = travel_m >= r8.touch_free_air_min_travel_m
        touch_sample = state.sample_count - state.touch_start_sample
        window_s = self.config.thresholds.free_air_window_s
        rod_weight = self._touch_rod_weight_N()
        free_air = np.full(LEG_COUNT, np.nan)
        touchdown_load = np.full(LEG_COUNT, -np.inf)
        for leg in range(LEG_COUNT):
            readings = state.free_air_moving_readings_N[leg]
            if has_moved[leg]:
                first_sample = state.free_air_first_moving_sample[leg]
                if first_sample is None:
                    first_sample = state.free_air_first_moving_sample[leg] = touch_sample
                # As the R7 window: moving sample m closes at (m + 1) T.
                if (touch_sample - first_sample + 1) * self.config.period_s < window_s:
                    readings.append(float(reading.cylinder_force_N[leg]))
            if len(readings) < r8.touch_free_air_min_samples:
                continue
            free_air[leg] = np.median(readings)
            touchdown_load[leg] = reading.cylinder_force_N[leg] - free_air[leg] - rod_weight[leg]
        state.free_air_force_N = free_air
        return touchdown_load

    def _touch_rod_weight_N(self) -> NDArray[np.float64]:
        """Per-leg ``m_rod g`` from the YAML (front 1047 N, rear 718 N); the scalar threshold
        when the geometry has none (tests)."""
        if self.geometry.rod_weight_N is None:
            return np.full(LEG_COUNT, self.config.thresholds.rod_weight_N)
        return np.asarray(self.geometry.rod_weight_N, dtype=float)

    def _touchdown_load_from_touch_entry_N(self, reading: _Reading) -> NDArray[np.float64]:
        """R7 rule: free-air reference = running median of every TOUCH sample of the window."""
        state = self._state
        # The first sample closes the first control period, so sample k ends at (k + 1) T;
        # counted from TOUCH entry (after CHECK).
        touch_sample = state.sample_count - state.touch_start_sample
        sample_end_s = (touch_sample + 1) * self.config.period_s
        if sample_end_s < self.config.thresholds.free_air_window_s:
            state.free_air_readings.append(reading.cylinder_force_N.copy())
            state.free_air_force_N = np.median(np.array(state.free_air_readings), axis=0)
        # The free-air reading holds the seal-friction offset of the extending leg.
        rod_weight = self.config.thresholds.rod_weight_N
        return reading.cylinder_force_N - state.free_air_force_N - rod_weight

    def _hold_probe_or_relevel(self, reading: _Reading) -> NDArray[np.float64] | None:
        """DONE / PROBE / READY (14.6); ``None`` when a trigger sends the run back to LEVEL."""
        state = self._state
        if self._needs_relevel(reading):
            self._start_relevel()
            return None
        if state.phase is C2Phase.DONE:
            # H5a: the trim after a completed REANCHOR needs no second probe (spec 22.2).
            if self.config.contact is ContactJudge.PRESSURE or state.skips_probe_after_reanchor:
                state.skips_probe_after_reanchor = False
                state.phase = C2Phase.READY
                return self._zero_speeds()
            state.phase = C2Phase.PROBE
        if state.phase is C2Phase.PROBE:
            return self._probe_step(reading)
        self._report_locked_pressure(reading)
        return self._zero_speeds()

    def _report_locked_pressure(self, reading: _Reading) -> None:
        """READY (legs locked): warn once per leg above the locked limit less the sensor margin
        (E-4: 345 bar for 350 bar) and, when set, above the 300 bar pre-warning."""
        state = self._state
        thresholds = self.config.thresholds
        head_area = self.geometry.head_area_m2
        limit_N = self.geometry.locked_force_limit_N
        if thresholds.locked_pressure_warning_margin_Pa:
            limit_N = limit_N - thresholds.locked_pressure_warning_margin_Pa * head_area
        over_limit = reading.head_only_force_N > limit_N
        for leg in np.flatnonzero(over_limit):
            if leg in state.locked_pressure_reported:
                continue
            state.locked_pressure_reported.add(int(leg))
            self._add_event(
                reading.t_s, f"locked_pressure_over_limit:{LEG_ORDER[leg]}", is_warning=True
            )
        prewarning_Pa = thresholds.locked_pressure_prewarning_Pa
        if prewarning_Pa is None:
            return
        for leg in np.flatnonzero(reading.head_only_force_N > prewarning_Pa * head_area):
            name = f"locked_pressure_prewarning:{LEG_ORDER[leg]}"
            if not any(event.name == name for event in state.events):
                self._add_event(reading.t_s, name, is_warning=True)

    def _needs_relevel(self, reading: _Reading) -> bool:
        state = self._state
        thresholds = self.config.thresholds
        if self._completion_deviation_rad() > thresholds.relevel_attitude_rad:
            return True
        if not self._is_low_load_watched():
            state.relevel_low_count = 0
            return self._relevels_for_reapproach(reading.t_s)
        relevel_level_N = self.geometry.F_min_N + thresholds.relevel_load_margin_N
        probed_leg = self._probed_leg()
        predicted_leg = self._leg_falling_below(relevel_level_N, reading.t_s, probed_leg)
        if predicted_leg is not None:
            self._note_probe_abort(reading.t_s, predicted_leg)
            return True
        loads = self._load_estimate_N(reading.cylinder_force_lower_N)
        if probed_leg is not None:
            loads = loads.copy()  # the pressure judge returns the reading itself
            loads[probed_leg] = math.inf  # the probe unloads its own leg on purpose
        lowest_leg = int(np.argmin(loads))
        is_low = float(loads[lowest_leg]) < relevel_level_N
        state.relevel_low_count = state.relevel_low_count + 1 if is_low else 0
        if state.relevel_low_count < self.config.r8.confirmation.relevel_samples:
            return self._relevels_for_reapproach(reading.t_s)
        self._note_probe_abort(reading.t_s, lowest_leg)
        return True

    def _is_low_load_watched(self) -> bool:
        """P5 / R-5 watch: READY, and PROBE with P-R8-11, once the machine is lifted."""
        state = self._state
        if not state.is_lifted:
            return False
        if state.phase is C2Phase.READY:
            return True
        return state.phase is C2Phase.PROBE and self.config.r8.probe_abort_on_low_load

    def _probed_leg(self) -> int | None:
        """P-R8-11: the leg the probe (or its re-ground step) moves now; ``None`` outside PROBE
        or before the round has started."""
        state = self._state
        if state.phase is not C2Phase.PROBE:
            return None
        if state.reground is not None:
            return state.reground.leg
        probe_round = state.probe_round
        if probe_round is None or probe_round.is_finished:
            return None
        return probe_round.leg

    def _note_probe_abort(self, t_s: float, leg: int) -> None:
        """P-R8-11 event when the low-load re-level stops a probe (spec 163.1)."""
        if self._state.phase is C2Phase.PROBE:
            self._add_event(t_s, f"probe_aborted_low_load:{LEG_ORDER[leg]}", is_warning=True)

    def _leg_falling_below(
        self, relevel_level_N: float, t_s: float, excluded_leg: int | None
    ) -> int | None:
        """R-5: the leg falling fast whose predicted estimate is lowest below P5, or ``None``.

        The prediction horizon is ``fast_relevel.horizon_periods`` (``None`` = ``1 + d``).
        ``excluded_leg`` (the probed leg) is not watched.
        """
        settings = self.config.r8.fast_relevel
        history = self._state.load_estimate_history
        if settings is None or len(history) < settings.rate_intervals + 1:
            return None
        oldest, previous, latest = history[0], history[-2], history[-1]
        drop_per_period = (oldest - latest) / settings.rate_intervals
        horizon_periods = settings.horizon_periods
        if horizon_periods is None:
            horizon_periods = 1 + self.config.r8.output_delay_periods
        predicted = latest - drop_per_period * horizon_periods
        is_fast = drop_per_period / self.config.period_s > settings.rate_threshold_N_s
        is_falling_now = previous > latest
        triggered = is_fast & is_falling_now & (predicted < relevel_level_N)
        if excluded_leg is not None:
            triggered[excluded_leg] = False
        if not triggered.any():
            return None
        leg = int(np.argmin(np.where(triggered, predicted, np.inf)))
        self._add_event(t_s, f"relevel_predicted:{LEG_ORDER[leg]}", is_warning=True)
        return leg

    def _start_relevel(self) -> None:
        """Back to LEVEL keeping the integrators; probe bookkeeping restarts.

        H5a: a re-level probes again before READY, even right after a REANCHOR trim.
        """
        state = self._state
        state.phase = C2Phase.LEVEL
        state.complete_since_s = None
        state.probe_round = None
        state.reground = None
        state.skips_probe_after_reanchor = False
        state.relevel_low_count = 0

    # --- lifted-leg re-approach (P-R8-12 leg mode, P-R8-13 twist mode) ---

    def _update_lifted_reapproach(self, reading: _Reading) -> None:
        """Re-approach bookkeeping of one period, before the phase command (spec 172.1, 174.4).

        Ends the re-approaches that held the exit level long enough or reached their travel
        limit, then starts one on a touched leg whose lower load estimate has stayed below the
        lift-off level for the confirmation samples (with ``single_leg`` only while none is
        active). Off, or outside the watched phases, nothing starts.
        """
        settings = self.config.r8.lifted_reapproach
        if not settings.enable:
            return
        state = self._state
        if state.phase not in REAPPROACH_PHASES or not state.is_lifted:
            for leg in list(state.active_reapproaches):
                self._end_reapproach(leg, reading, f"phase:{state.phase}")
            state.reapproach_low_counts[:] = 0
            state.reapproach_strong_counts = NO_REAPPROACH_STRONG_COUNTS
            return
        loads = self._load_estimate_N(reading.cylinder_force_lower_N)
        self._end_finished_reapproaches(reading, loads, settings)
        self._start_reapproaches(reading, loads, settings)

    def _end_finished_reapproaches(
        self,
        reading: _Reading,
        loads_N: NDArray[np.float64],
        settings: LiftedReapproachSettings,
    ) -> None:
        state = self._state
        min_load_N = self.geometry.F_min_N
        exit_level_N = min_load_N + settings.exit_margin_N
        for leg, run in list(state.active_reapproaches.items()):
            travel = float(reading.motor_stroke_m[leg]) - run.start_motor_stroke_m
            if loads_N[leg] >= exit_level_N:
                run.exit_samples_seen += 1
            else:
                run.exit_samples_seen = 0
            if run.exit_samples_seen >= settings.exit_samples:
                self._end_reapproach(leg, reading, "contact")
                self._add_event(reading.t_s, f"leg_reapproach_contact:{LEG_ORDER[leg]}")
            elif travel > settings.max_travel_m or settings.has_run_too_long(
                reading.t_s, run.start_s
            ):
                self._end_reapproach(leg, reading, "no_contact")
                state.is_reapproach_armed[leg] = False
                self._add_event(
                    reading.t_s,
                    f"WARN_LEG_REAPPROACH_NO_CONTACT:{LEG_ORDER[leg]}",
                    is_warning=True,
                )
        # A leg left on the guard path after a failed re-approach is watched again once it
        # bears F_min, so a deep sink does not restart the same 40 mm search every period.
        state.is_reapproach_armed |= loads_N >= min_load_N

    def _start_reapproaches(
        self,
        reading: _Reading,
        loads_N: NDArray[np.float64],
        settings: LiftedReapproachSettings,
    ) -> None:
        state = self._state
        lift_off_level_N = settings.load_fraction_of_F_min * self.geometry.F_min_N
        required_samples = settings.samples or self.config.r8.confirmation.relevel_samples
        probed_leg = self._probed_leg()  # the probe unloads its own leg on purpose
        strong_counts = list(state.reapproach_strong_counts)
        for leg in range(LEG_COUNT):
            is_another_leg_active = settings.single_leg and bool(state.active_reapproaches)
            is_watched = (
                state.touched[leg]
                and state.is_reapproach_armed[leg]
                and leg not in state.active_reapproaches
                and leg != probed_leg
                and not is_another_leg_active
            )
            if not is_watched or loads_N[leg] >= lift_off_level_N:
                state.reapproach_low_counts[leg] = 0
                strong_counts[leg] = 0
                continue
            state.reapproach_low_counts[leg] += 1
            is_strong = loads_N[leg] < settings.opposite_strong_level_N
            strong_counts[leg] = strong_counts[leg] + 1 if is_strong else 0
            if state.reapproach_low_counts[leg] < required_samples:
                continue
            if self._defers_reapproach(leg, reading.t_s, strong_counts[leg], settings):
                # The low count keeps rising while a start is deferred, so it equals the
                # requirement only on the first sample of a deferred stretch.
                if state.reapproach_low_counts[leg] == required_samples:
                    self._add_event(
                        reading.t_s, f"{REAPPROACH_DEFERRED_EVENT}:{LEG_ORDER[leg]}"
                    )
                continue
            state.reapproach_low_counts[leg] = 0
            strong_counts[leg] = 0
            self._begin_reapproach(leg, reading, settings)
        state.reapproach_strong_counts = tuple(strong_counts)

    def _defers_reapproach(
        self, leg: int, t_s: float, strong_count: int, settings: LiftedReapproachSettings
    ) -> bool:
        """P-S8-16 RT 1 (spec rev. 52 228.3): an other-diagonal start inside the opposite
        window waits for ``opposite_strong_samples`` samples below the strong level."""
        state = self._state
        leg_sign = float(np.sign(self.geometry.twist_vector[leg]))
        needs_confirmation = settings.needs_strong_confirmation(
            t_s, state.reapproach_last_end_s, state.reapproach_last_sign, leg_sign
        )
        return needs_confirmation and strong_count < settings.opposite_strong_samples

    def _begin_reapproach(
        self, leg: int, reading: _Reading, settings: LiftedReapproachSettings
    ) -> None:
        state = self._state
        run = _Reapproach(
            leg,
            reading.t_s,
            float(reading.motor_stroke_m[leg]),
            settings.mode,
            is_retrigger=settings.is_retrigger(reading.t_s, state.reapproach_last_end_s),
        )
        state.active_reapproaches[leg] = run
        state.reapproach_history.append(run)
        self._add_event(reading.t_s, f"leg_reapproach_start:{LEG_ORDER[leg]}", is_warning=True)

    def _end_reapproach(self, leg: int, reading: _Reading, outcome: str) -> None:
        state = self._state
        run = state.active_reapproaches.pop(leg)
        run.end_s = reading.t_s
        run.travel_m = float(reading.motor_stroke_m[leg]) - run.start_motor_stroke_m
        run.outcome = outcome
        # P-S8-16: the re-trigger and other-diagonal windows count from here.
        state.reapproach_last_end_s = reading.t_s
        state.reapproach_last_sign = float(np.sign(self.geometry.twist_vector[leg]))

    def _reapproach_speed_factor(self, leg: int) -> float:
        """P-S8-16 RT 2: ``retrigger_speed_factor`` for a re-trigger run, else 1."""
        if not self._state.active_reapproaches[leg].is_retrigger:
            return 1.0
        return self.config.r8.lifted_reapproach.retrigger_speed_factor

    def _reapproaching_legs(self) -> NDArray[np.bool_]:
        legs = np.zeros(LEG_COUNT, dtype=bool)
        legs[list(self._state.active_reapproaches)] = True
        return legs

    def _relevels_for_reapproach(self, t_s: float) -> bool:
        """DONE / PROBE / READY with an active re-approach go back to LEVEL (spec 172.1: the
        transition of P5 and R-5); a probe stop is reported as P-R8-11 does."""
        active_legs = sorted(self._state.active_reapproaches)
        if not active_legs:
            return False
        self._note_probe_abort(t_s, active_legs[0])
        return True

    def _apply_reapproach_speeds(
        self, leg_speeds: NDArray[np.float64], reapproaching: NDArray[np.bool_]
    ) -> NDArray[np.float64]:
        """Leg mode: the re-approaching legs extend at ``speed_fraction v_max``; the others keep
        theirs. Twist mode: unchanged (the re-approach is in ``tau_dot``)."""
        settings = self.config.r8.lifted_reapproach
        if not reapproaching.any() or settings.mode is ReapproachMode.TWIST:
            return leg_speeds
        speeds = leg_speeds.copy()
        speeds[reapproaching] = self._leg_mode_reapproach_speeds()
        # The override is part of the raw command (P-R8-15): the stages it replaces on the
        # lifted legs did not limit them.
        flags = self._state.output_limit_flags
        for limit in (OutputLimit.SPEED_SCALE, OutputLimit.CRAWLER_RULE):
            flags[limit.value] = flags[limit.value] & ~reapproaching
        return speeds

    def _leg_mode_reapproach_speeds(self) -> NDArray[np.float64]:
        """Leg mode: the speed of each re-approaching leg in leg order, ``speed_fraction
        v_max`` times the P-S8-16 factor on a re-trigger run."""
        speed_fraction = self.config.r8.lifted_reapproach.speed_fraction
        legs = sorted(self._state.active_reapproaches)
        fractions = [speed_fraction * self._reapproach_speed_factor(leg) for leg in legs]
        return np.array(fractions) * self.geometry.max_speed_m_s

    def _reapproach_twist_rate(self, reading: _Reading) -> float:
        """Twist mode ``tau_dot_lift = sign(n_j) f v_max / max|n|`` toward the lifted leg ``j``
        (spec 174.4), or zero while a grounded leg this twist retracts reads below ``F_min +
        protect_margin_N`` (lower estimate). A re-trigger run (P-S8-16 RT 2) is slowed by
        ``retrigger_speed_factor``.

        Only the retracted legs (``sign(n_i) != sign(n_j)``, FR and RL for RR) are protected:
        the twist unloads them. The diagonal leg is extended, so its load rises; its rocking
        lift-off (spec 173.1) zeroing ``tau_dot`` would delay the re-contact (reduced plant:
        RR first contact 1.01 -> 1.72 s).
        """
        settings = self.config.r8.lifted_reapproach
        state = self._state
        lifted_leg = min(state.active_reapproaches)  # single_leg: the only one
        twist = self.geometry.twist_vector
        loads = self._load_estimate_N(reading.cylinder_force_lower_N)
        is_protected = state.touched & (np.sign(twist) != np.sign(twist[lifted_leg]))
        protect_level_N = self.geometry.F_min_N + settings.protect_margin_N
        if np.any(loads[is_protected] < protect_level_N):
            state.active_reapproaches[lifted_leg].protected_periods += 1
            return 0.0
        fastest_leg_speed = settings.twist_speed_fraction * self.geometry.max_speed_m_s
        twist_rate = math.copysign(1.0, twist[lifted_leg]) * fastest_leg_speed / float(
            np.max(np.abs(twist))
        )
        # P-S8-16 RT 2: after the protection test; 1.0 (exact) on a first run.
        return twist_rate * self._reapproach_speed_factor(lifted_leg)

    # --- zero calibration (E-3, E-5, E-6) ---

    def _has_check(self) -> bool:
        return self.config.target.check_time_s > 0.0

    def _is_zero_calibration_running(self) -> bool:
        calibration = self._state.zero_calibration
        return calibration is not None and not calibration.is_finished

    def _zero_calibration_step(self, reading: _Reading) -> NDArray[np.float64]:
        """Round-trip speeds of this CHECK period (zero when off or done)."""
        if not self.config.zero_calibration.is_enabled:
            return self._zero_speeds()
        state = self._state
        calibration = state.zero_calibration
        if calibration is None and not self._has_check():
            self._skip_zero_calibration(reading.t_s)
            return self._zero_speeds()
        if calibration is None:
            calibration = self._start_zero_calibration(reading)
            if calibration.is_finished:
                self._apply_zero_calibration(calibration, reading.t_s)
            return self._zero_speeds()
        if calibration.is_finished:
            return self._zero_speeds()
        speeds = calibration.step(reading.t_s, reading.motor_stroke_m, reading.cylinder_force_N)
        if calibration.is_finished:
            self._apply_zero_calibration(calibration, reading.t_s)
        return speeds

    def _new_zero_calibration(self) -> ZeroCalibration:
        return ZeroCalibration(
            self.config.zero_calibration,
            self.geometry.max_speed_m_s,
            self._pressures.rod_weight_N,
            self.geometry.stroke_soft_max_m - self.config.thresholds.stroke_end_clip_margin_m,
        )

    def _skip_zero_calibration(self, t_s: float) -> None:
        """76.4 (3) a: calibration on but no CHECK length -> all legs failed (allowance)."""
        calibration = self._new_zero_calibration()
        calibration.skip_all(t_s, SkipReason.NO_CHECK)
        self._state.zero_calibration = calibration
        self._apply_zero_calibration(calibration, t_s)

    def _reusable_calibrations(self) -> dict[int, LegCalibration]:
        """76.4 (3) b: legs calibrated by an earlier CHECK of this run keep their result."""
        previous = self._state.previous_zero_calibration
        if previous is None or previous.results is None:
            return {}
        return {leg: result for leg, result in enumerate(previous.results)
                if result.is_calibrated}

    def _start_zero_calibration(self, reading: _Reading) -> ZeroCalibration:
        """76.2: a leg already grounded (band ABOVE or ``F_hat > F_min / 2``) is skipped."""
        calibration = self._new_zero_calibration()
        bands = self.load_bands or []
        is_grounded = [
            band is LoadBand.ABOVE or force > 0.5 * self.geometry.F_min_N
            for band, force in zip(bands, reading.cylinder_force_N, strict=True)
        ]
        calibration.start(
            reading.t_s, reading.motor_stroke_m, is_grounded, self._reusable_calibrations()
        )
        self._state.zero_calibration = calibration
        return calibration

    def _apply_zero_calibration(self, calibration: ZeroCalibration, t_s: float) -> None:
        """Offsets from now on; failed legs latch their allowance for the run (76.2)."""
        self._pressures.set_zero_offsets_N(calibration.offsets_N)
        allowance = np.maximum(self.config.pressure_offset_allowance_N, calibration.allowance_N)
        self._pressures.set_offset_allowance_N(allowance)
        reported = {event.name for event in self._state.events}
        for name, is_warning in calibration.events():
            if name not in reported:  # a restarted CHECK does not repeat a run-level warning
                self._add_event(t_s, name, is_warning=is_warning)
        self._state.calibration_oil_temperature_C = self._state.oil_temperature_C

    def _watch_oil_temperature(self, measurements: Measurements) -> None:
        """E-5 (72.1 (5)): ``WARN_PRESSURE_RECAL_DUE`` once when the oil temperature moved
        more than the setting since the calibration (only with a temperature signal)."""
        state = self._state
        state.oil_temperature_C = measurements.oil_temperature_C
        reference = state.calibration_oil_temperature_C
        if reference is None or measurements.oil_temperature_C is None:
            return
        limit_K = self.config.zero_calibration.recalibration_temperature_change_K
        if abs(measurements.oil_temperature_C - reference) <= limit_K:
            return
        if not any(event.name == "WARN_PRESSURE_RECAL_DUE" for event in state.events):
            self._add_event(measurements.t_s, "WARN_PRESSURE_RECAL_DUE", is_warning=True)

    # --- target (revision R3, control/target.py) ---

    def _record_check(self, check: TargetCheck) -> TargetCheck:
        self._state.target_checks.append(check)
        self._state.target_code = check.code
        return check

    def _last_time_s(self) -> float:
        reading = self._state.last_reading
        return 0.0 if reading is None else reading.t_s

    def _restart_check(self, target: AttitudeTarget) -> None:
        """IDLE -> CHECK: measure ``(phi_c, theta_c)`` again and judge ``target`` (spec 2.2)."""
        state = self._state
        state.phase = C2Phase.CHECK
        if state.zero_calibration is not None:
            # 76.4 (3) b: calibrated legs are reused, failed and skipped legs try again; the
            # offsets and allowances stay in force until the new round trip ends.
            state.previous_zero_calibration = state.zero_calibration
            state.zero_calibration = None
        state.check_start_s = None
        state.check_attitudes.clear()
        state.check_raw_tilts.clear()
        state.check_window = None
        state.check_gyro_rates.clear()
        state.check_gyro_times_s.clear()
        state.crawler_attitude_rad = None
        state.requested_target = target
        state.active_target = None
        state.reference = None

    def _check_step(self, reading: _Reading) -> bool:
        """One CHECK period (C1); True when CHECK ended with an accepted target (-> TOUCH)."""
        state = self._state
        if state.check_start_s is None:
            state.check_start_s = reading.t_s
        state.check_attitudes.append((state.roll_rad, state.pitch_rad))
        state.check_gyro_rates.append(state.gyro_rate_rad_s)
        state.check_gyro_times_s.append(reading.t_s)
        uses_raw_tilt = self.config.r8.uses_raw_check_attitude
        if uses_raw_tilt:
            state.check_raw_tilts.extend(state.period_raw_tilts)
        settings = self.config.target
        if reading.t_s - state.check_start_s < settings.check_time_s - CHECK_TIME_SLACK_S:
            return False
        if self._is_zero_calibration_running():
            return False  # E-3: CHECK ends once the round trip is done as well
        if uses_raw_tilt and not self._is_raw_check_window_ready(reading.t_s):
            return False  # P-R8-9: CHECK goes on until the quiet window is full
        estimate = self._estimate_gyro_bias(reading.t_s)
        if estimate is None:
            return False  # B1': CHECK goes on (window shorter than T_b or still moving)
        self._accept_gyro_bias_estimate(estimate, reading.t_s)
        if uses_raw_tilt:
            state.crawler_attitude_rad = self._raw_check_attitude_rad(reading.t_s)
        else:
            # A1-A4 on the last check_average_s of the CHECK, extended or not (spec 34 B1).
            roll, pitch = np.mean(np.array(state.check_attitudes), axis=0)
            state.crawler_attitude_rad = (float(roll), float(pitch))
        requested = state.requested_target or AttitudeTarget()
        check = self._record_check(
            check_target(
                requested,
                state.crawler_attitude_rad,
                settings.limits,
                settings.acceptance,
                settle_map=settings.settle_map,
            )
        )
        if check.accepted is None:
            state.phase = C2Phase.IDLE
            self._add_event(reading.t_s, str(check.code), is_warning=True)
            return False
        if check.is_projected:
            self._add_event(reading.t_s, "WARN_TARGET_PROJECTED", is_warning=True)
        state.active_target = state.reference = check.accepted  # R2: no ramp the first time
        state.phase = C2Phase.TOUCH
        state.touch_start_sample = state.sample_count
        state.soil = _SoilState()  # P-S9-6: a new lifting cycle
        return True

    def _check_quiet_start_s(self) -> float | None:
        """P-R8-9: last nonzero leg command + ``T_q``; ``-inf`` when no leg has moved, ``None``
        while a nonzero command is still to be output (just computed or in the output buffer)."""
        state = self._state
        is_command_pending = bool(np.any(state.previous_output_m_s != 0.0)) or any(
            np.any(queued != 0.0) for queued in state.output_queue
        )
        if is_command_pending:
            return None
        if state.last_nonzero_command_t_s is None:
            return -math.inf
        return state.last_nonzero_command_t_s + self.config.target.check_quiet_after_motion_s

    def _raw_check_window_size(self) -> int:
        sample_period_s = self.config.r8.imu_sample_period_s or self.config.period_s
        return max(1, round(self.config.target.check_average_s / sample_period_s))

    def _last_raw_check_tilts(self) -> list[_RawTilt]:
        """The last ``check_average_s`` of CHECK raw tilts (fewer early in CHECK)."""
        return self._state.check_raw_tilts[-self._raw_check_window_size() :]

    def _quiet_raw_check_tilts(self, window: list[_RawTilt]) -> list[_RawTilt]:
        quiet_start_s = self._check_quiet_start_s()
        if quiet_start_s is None:
            return []
        return [tilt for tilt in window if tilt.t_s >= quiet_start_s - CHECK_TIME_SLACK_S]

    def _is_raw_check_window_ready(self, t_s: float) -> bool:
        """P-R8-9: a full ``check_average_s`` of raw tilts after the quiet start, or CHECK has
        reached ``check_max_s`` (no further extension)."""
        state = self._state
        check_duration_s = t_s - (state.check_start_s or t_s)
        if check_duration_s >= self.config.target.check_max_s - CHECK_TIME_SLACK_S:
            return True
        window = self._last_raw_check_tilts()
        is_window_long_enough = len(window) == self._raw_check_window_size()
        return is_window_long_enough and len(self._quiet_raw_check_tilts(window)) == len(window)

    def _raw_check_attitude_rad(self, t_s: float) -> tuple[float, float]:
        """P-R8-9 ``(phi_c, theta_c)``: mean raw tilt of the quiet window.

        At ``check_max_s`` without a full quiet window it averages the quiet part of the last
        ``check_average_s``, or that whole window when none of it is quiet; the meta records
        which (``check_window``).
        """
        state = self._state
        window = self._last_raw_check_tilts()
        quiet = self._quiet_raw_check_tilts(window)
        averaged = quiet or window
        roll = float(np.mean([tilt.roll_rad for tilt in averaged]))
        pitch = float(np.mean([tilt.pitch_rad for tilt in averaged]))
        quiet_start_s = self._check_quiet_start_s()
        state.check_window = {
            "t_judged_s": t_s,
            "t_first_sample_s": averaged[0].t_s,
            "t_last_sample_s": averaged[-1].t_s,
            "sample_count": len(averaged),
            "quiet_start_s": (
                quiet_start_s if quiet_start_s is not None and math.isfinite(quiet_start_s)
                else None
            ),
            "last_nonzero_command_t_s": state.last_nonzero_command_t_s,
            "is_quiet_window_full": len(quiet) == len(window),
        }
        return roll, pitch

    def _estimate_gyro_bias(self, t_s: float) -> GyroBiasEstimate | None:
        """B1' (spec 39): the CHECK bias decision, ``None`` while CHECK has to go on.

        The estimate is the mean of the last ``T_b``; it is taken once that window is quiet
        (noise-corrected RMS about its mean <= ``omega_th(T_b)``, per axis), at ``check_max_s``
        at the latest. With ``check_time_s = 0`` the one sample of CHECK is no standstill
        average, so the bias stays unremoved, as in the reduced-model regression runs. With the R4.1
        settings (``check_max_s = check_time_s``, no limits) the window holds every CHECK
        sample, so the bias is the R4.1 CHECK mean bit for bit.
        """
        state = self._state
        settings = self.config.target
        check_duration_s = t_s - (state.check_start_s or t_s)
        window_s = self._gyro_bias_window_s
        if settings.check_time_s <= 0.0:
            return GyroBiasEstimate(GyroBiasOutcome.NO_CHECK, window_s, check_duration_s)
        if check_duration_s < window_s - CHECK_TIME_SLACK_S:
            return None
        statistics = window_statistics(
            state.check_gyro_times_s,
            state.check_gyro_rates,
            t_s,
            window_s,
            settings.gyro_noise_std_rad_s,
        )
        motion_limit = settings.gyro_bias_motion_limit_rad_s(window_s)
        is_quiet = motion_limit is None or max(statistics.motion_rms_rad_s) <= motion_limit
        if not is_quiet and check_duration_s < settings.check_max_s - CHECK_TIME_SLACK_S:
            return None
        plausible_limit = settings.gyro_bias_plausible_rad_s
        is_plausible = plausible_limit is None or (
            max(abs(rate) for rate in statistics.mean_rad_s) <= plausible_limit
        )
        if not is_quiet:
            outcome = GyroBiasOutcome.SKIPPED_MOTION
        elif not is_plausible:
            outcome = GyroBiasOutcome.REJECTED_IMPLAUSIBLE
        else:
            outcome = GyroBiasOutcome.ACCEPTED
        return GyroBiasEstimate(
            outcome,
            window_s,
            check_duration_s,
            statistics.mean_rad_s,
            statistics.motion_rms_rad_s,
            motion_limit,
        )

    def _accept_gyro_bias_estimate(self, estimate: GyroBiasEstimate, t_s: float) -> None:
        """Remove the bias from now on, or warn that it is not removed (U36-a)."""
        state = self._state
        state.gyro_bias_estimate = estimate
        state.gyro_bias_rad_s = estimate.bias_rad_s
        if estimate.outcome is GyroBiasOutcome.SKIPPED_MOTION:
            self._add_event(t_s, "WARN_GYRO_BIAS_SKIPPED", is_warning=True)
        elif estimate.outcome is GyroBiasOutcome.REJECTED_IMPLAUSIBLE:
            self._add_event(t_s, "WARN_GYRO_BIAS_IMPLAUSIBLE", is_warning=True)

    def _change_target_in_ready(self, target: AttitudeTarget, reading: _Reading) -> TargetCheck:
        """READY change (A0-A5); an accepted one ramps the reference and re-levels (U3, U4)."""
        state = self._state
        settings = self.config.target
        crawler = state.crawler_attitude_rad
        assert crawler is not None
        check = check_target(
            target,
            crawler,
            settings.limits,
            settings.acceptance,
            current=state.active_target,
            settle_map=settings.settle_map,
        )
        if check.accepted is not None and not self._is_stroke_feasible(check.accepted, reading):
            check = replace(check, accepted=None, code=TargetCode.REJ_TARGET_STROKE)
        self._record_check(check)
        if check.accepted is None:
            self._add_event(reading.t_s, str(check.code), is_warning=True)
            return check
        if check.is_projected:
            self._add_event(reading.t_s, "WARN_TARGET_PROJECTED", is_warning=True)
        if check.accepted == state.active_target:
            return check
        state.active_target = check.accepted
        self._add_event(reading.t_s, "target_changed")
        self._start_relevel()
        state.reanchor = None  # U3: may re-anchor after the change (H2)
        state.reanchor_outcome = None
        return check

    def _is_stroke_feasible(self, target: AttitudeTarget, reading: _Reading) -> bool:
        """A5: predicted strokes within ``[13 mm, s_max - 13 mm]`` (skipped with ``OFF``)."""
        if self.config.target.acceptance is TargetAcceptance.OFF:
            return True
        state = self._state
        attitude_change = (target.roll_rad - state.roll_rad, target.pitch_rad - state.pitch_rad)
        strokes = self.geometry.predicted_strokes_m(
            reading.motor_stroke_m,
            reading.rod_stroke_m,
            attitude_change,
            self.config.thresholds.clearance_target_m,
            corner_bias_m=self._active_corner_bias_m(),
        )
        upper = self.geometry.stroke_soft_max_m - TARGET_STROKE_MARGIN_M
        return bool(strokes.min() >= TARGET_STROKE_MARGIN_M and strokes.max() <= upper)

    def _advance_reference(self) -> None:
        """R1: move the reference toward the target by one ramp period."""
        state = self._state
        if state.reference is None or state.active_target is None:
            return
        if state.reference == state.active_target:
            return
        settings = self.config.target
        state.reference = ramp_reference(
            state.reference,
            state.active_target,
            self.config.period_s,
            settings.roll_ramp_rate_rad_s,
            settings.pitch_ramp_rate_rad_s,
        )

    def _is_reference_on_target(self) -> bool:
        return self._state.reference == self._state.active_target

    # --- LEVEL ---

    def _level(self, reading: _Reading) -> NDArray[np.float64]:
        """One LEVEL period in the fixed order of design 14.5."""
        if self.config.soil.enable and self._state.phase is C2Phase.LEVEL:
            # S-1 first: a confirmation this period already corrects the clearance below.
            self._update_liftoff_window(reading)
        geometry = self.geometry
        thresholds = self.config.thresholds
        clearance = self._clearance_estimate_m(reading.rod_stroke_m)
        if clearance > thresholds.lifted_clearance_m:
            self._state.is_lifted = True
        roll_rate, pitch_rate = self._attitude_rates()
        filtered_clearance = float(self._clearance_filter.update(clearance))
        heave_error = thresholds.clearance_target_m - filtered_clearance
        heave_rate = float(
            np.clip(
                self.config.gains.heave_kz_1_s * heave_error,
                -geometry.max_speed_m_s,
                geometry.max_speed_m_s,
            )
        )
        reapproaching = self._reapproaching_legs()
        twist_rate = self._twist_channel_rate(reading, is_held=bool(reapproaching.any()))
        unscaled_speeds = geometry.leg_speeds(heave_rate, roll_rate, pitch_rate, twist_rate)
        leg_speeds = scale_to_speed_limit(unscaled_speeds, geometry.max_speed_m_s)
        self._note_output_limit(OutputLimit.SPEED_SCALE, unscaled_speeds, leg_speeds)
        is_complete = self._update_completion(reading, filtered_clearance)
        if reapproaching.any():
            # P-R8-12 / P-R8-13: no DONE while a leg is still in the air.
            self._state.complete_since_s = None
            is_complete = False
        if self._update_crawler_zone(reading):
            lifted_speeds = self._lift_without_retracting(leg_speeds)
            self._note_output_limit(OutputLimit.CRAWLER_RULE, leg_speeds, lifted_speeds)
            leg_speeds = lifted_speeds
        leg_speeds = self._apply_reapproach_speeds(leg_speeds, reapproaching)
        self._record_command_components(
            (heave_rate, roll_rate, pitch_rate, twist_rate), unscaled_speeds, reapproaching
        )
        if self._update_stroke_end_fault(reading, leg_speeds):
            self._state.phase = C2Phase.FAULT
            stopped_speeds = self._zero_speeds()
            self._note_output_limit(OutputLimit.STROKE_END, leg_speeds, stopped_speeds)
            return stopped_speeds
        clipped_speeds = self._clip_at_stroke_ends(reading, leg_speeds)
        self._note_output_limit(OutputLimit.STROKE_END, leg_speeds, clipped_speeds)
        leg_speeds = clipped_speeds
        if is_complete:
            self._state.phase = C2Phase.DONE
        return leg_speeds

    def _record_command_components(
        self,
        rates: tuple[float, float, float, float],
        unscaled_speeds: NDArray[np.float64],
        reapproaching: NDArray[np.bool_],
    ) -> None:
        """P-R8-14: split this period's unscaled LEVEL command into its named parts.

        ``rates`` = (heave, roll, pitch, ``tau_dot``) as passed to :meth:`C2Geometry.leg_speeds`.
        While a leg re-approaches the whole ``tau_dot`` is the re-approach part (twist mode:
        ``tau_dot_lift``; leg mode: zero); otherwise the guard part is ``_state.guard_m_s``.
        P-R8-15: ``phase_path`` is zero, and the raw command is ``unscaled_speeds`` with the
        leg-mode override on the lifted legs.
        """
        geometry = self.geometry
        heave_rate, roll_rate, pitch_rate, twist_rate = rates
        twist_mode_speeds = geometry.twist_vector * twist_rate
        zeros = self._zero_speeds()
        components = {
            "attitude": geometry.leg_speeds(0.0, roll_rate, pitch_rate, 0.0),
            "heave": geometry.leg_speeds(heave_rate, 0.0, 0.0, 0.0),
            "twist": twist_mode_speeds,
            "guard": zeros.copy(),
            "reapproach": zeros.copy(),
            "phase_path": zeros.copy(),
        }
        raw_speeds = unscaled_speeds.copy()
        if reapproaching.any():
            components["twist"] = zeros.copy()
            settings = self.config.r8.lifted_reapproach
            if settings.mode is ReapproachMode.TWIST:
                components["reapproach"] = twist_mode_speeds
            else:
                override_speed = self._leg_mode_reapproach_speeds()
                components["reapproach"][reapproaching] = (
                    override_speed - unscaled_speeds[reapproaching]
                )
                raw_speeds[reapproaching] = override_speed
        elif self._state.guard_m_s is not None:
            components["guard"] = self._state.guard_m_s.copy()
            components["twist"] = twist_mode_speeds - components["guard"]
        self._state.command_components = components
        self._state.raw_output_m_s = raw_speeds

    def _record_phase_path_command(self, leg_speeds: NDArray[np.float64]) -> None:
        """P-R8-15: a period without a LEVEL step; its whole command is ``phase_path`` (TOUCH,
        the CHECK zero calibration, PROBE, REANCHOR, a lock tail; zero in READY, FAULT, IDLE)
        and the LEVEL parts are zero."""
        components = {name: self._zero_speeds() for name in COMMAND_COMPONENT_NAMES}
        components["phase_path"] = np.array(leg_speeds, dtype=float)
        self._state.command_components = components
        self._state.raw_output_m_s = np.array(leg_speeds, dtype=float)

    def _note_output_limit(
        self,
        limit: OutputLimit,
        before_m_s: NDArray[np.float64],
        after_m_s: NDArray[np.float64],
    ) -> None:
        """P-R8-15: mark the legs whose speed the ``limit`` stage changed this period."""
        flags = self._state.output_limit_flags
        flags[limit.value] = flags[limit.value] | (after_m_s != before_m_s)

    def _twist_channel_rate(self, reading: _Reading, *, is_held: bool) -> float:
        """``tau_dot`` of this period (twist loop + F_min guard, design 14.5 steps 4-5).

        ``is_held`` (a re-approach is active): the twist and guard terms are dropped. Twist
        mode (P-R8-13, spec 174.4): ``tau_dot_lift`` toward the lifted leg instead. Leg mode
        (P-R8-12): zero, the lifted leg moving alone. The twist low-pass still takes this
        period's reading.
        """
        geometry = self.geometry
        load_estimates_N = self._load_estimate_N(reading.cylinder_force_lower_N)
        rates = twist_rates(
            self._twist_loop_load_N(reading),
            load_estimates_N,
            geometry,
            self.config.gains,
            self.config.thresholds,
            self._twist_gain_stiffness_N_m(),
        )
        if is_held:
            if self.config.r8.lifted_reapproach.mode is ReapproachMode.TWIST:
                return self._reapproach_twist_rate(reading)
            return 0.0
        if rates.is_guard_active:
            self._state.guard_m_s = geometry.twist_vector * rates.guard_m_s
            self._log_fallback_guard(reading, load_estimates_N)
        return rates.total_m_s

    def _log_fallback_guard(
        self, reading: _Reading, load_estimates_N: NDArray[np.float64]
    ) -> None:
        """Spec 218.10 record: the guard acts on the lowest load estimate (:func:`twist_rates`);
        when that leg is a rod-side fallback leg, extend its current stretch (consecutive
        periods) or open a new one. ``head_end_Pa`` is the head reading of the stretch's last
        guarded period, where the guard stopped (compare with ``h*`` of 218.10)."""
        guarded_leg = int(np.argmin(np.asarray(load_estimates_N, dtype=float)))
        if guarded_leg not in self._pressures.fallback_legs:
            return
        if self._fallback_guard_log is None:
            self._fallback_guard_log = []
        period_s = self.config.period_s
        t_s = float(reading.t_s)
        head_force_N = reading.head_only_force_N[guarded_leg]
        head_Pa = float(head_force_N / self.geometry.head_area_m2[guarded_leg])
        stretch = self._last_fallback_guard_stretch(guarded_leg)
        is_continued = stretch is not None and abs(t_s - stretch["t_end_s"] - period_s) < 1e-6
        if not is_continued:
            stretch = {"leg": LEG_ORDER[guarded_leg], "t_start_s": t_s, "periods": 0}
            self._fallback_guard_log.append(stretch)
        stretch["t_end_s"] = t_s
        stretch["periods"] += 1
        stretch["duration_s"] = stretch["periods"] * period_s
        stretch["head_end_Pa"] = head_Pa
        stretch["load_estimate_end_N"] = float(load_estimates_N[guarded_leg])

    def _last_fallback_guard_stretch(self, leg: int) -> dict[str, Any] | None:
        for stretch in reversed(self._fallback_guard_log or []):
            if stretch["leg"] == LEG_ORDER[leg]:
                return stretch
        return None

    def _twist_loop_load_N(self, reading: _Reading) -> float:
        """``n^T P`` of the twist loop: raw, or (R8 C2) through its own low-pass."""
        twist_load = float(self.geometry.twist_vector @ reading.cylinder_force_N)
        if self._twist_load_filter is None:
            return twist_load
        return float(self._twist_load_filter.update(twist_load))

    def _twist_gain_scale(self) -> float | None:
        """Stiffness scale the twist / guard gains are divided by; ``None`` = ``k_nom`` (R7)."""
        r8 = self.config.r8
        if r8.twist_gain_reference is TwistGainReference.NOMINAL:
            return None
        scale = self._state.twist_stiffness_scale
        return r8.pre_probe_stiffness_scale if scale is None else scale

    def _twist_gain_stiffness_N_m(self) -> float | None:
        """Stiffness of the twist / guard gains (P-5); ``None`` = ``k_nom`` unchanged."""
        scale = self._twist_gain_scale()
        if scale is None:
            return None
        return self.geometry.nominal_pad_stiffness_N_m * scale

    def _attitude_rates(self) -> tuple[float, float]:
        state = self._state
        reference_roll, reference_pitch = self._reference_rad()
        roll_error = reference_roll - state.roll_rad
        pitch_error = reference_pitch - state.pitch_rad
        # P2: in the joint mode the upper bound applies to the larger error of both axes.
        joint_error = None
        if self.config.thresholds.integrator_band_mode is IntegratorBandMode.JOINT:
            joint_error = max(abs(roll_error), abs(pitch_error))
        roll_rate, state.roll_integral = self._attitude_pi(
            roll_error, state.roll_integral, joint_error
        )
        pitch_rate, state.pitch_integral = self._attitude_pi(
            pitch_error, state.pitch_integral, joint_error
        )
        return roll_rate, pitch_rate

    def _attitude_pi(
        self, error_rad: float, integral: float, joint_error_rad: float | None = None
    ) -> tuple[float, float]:
        """PI with conditional integration (anti-windup, design 6.2): rate and new integral.

        ``joint_error_rad`` (P2 joint mode) replaces the axis error in the upper-bound test.
        """
        thresholds = self.config.thresholds
        band_low, band_high = thresholds.integrator_band_rad
        upper_test = abs(error_rad) if joint_error_rad is None else joint_error_rad
        if band_low < abs(error_rad) and upper_test < band_high:
            limit = thresholds.integrator_limit_rad_s
            integral = float(np.clip(integral + error_rad * self.config.period_s, -limit, limit))
        gains = self.config.gains
        return gains.attitude_kp_1_s * error_rad + gains.attitude_ki_1_s2 * integral, integral

    def _update_crawler_zone(self, reading: _Reading) -> bool:
        """Crawler-zone latch with hysteresis (14.5 step 8, R1); returns whether it is on.

        The estimate ``c_lr(s - P_bar / k_oil(s))`` low-passes only the oil compression term,
        so the 3 Hz rocking carried by the rod stroke cannot turn the rule into a relay
        (design 16.2), while commanded motion passes without delay.
        """
        state = self._state
        thresholds = self.config.thresholds
        motor_stroke = reading.motor_stroke_m
        compression = reading.cylinder_force_lowpass_N / self.geometry.oil_stiffness_N_m(
            motor_stroke
        )
        slow_clearance = self._clearance_estimate_m(motor_stroke - compression)
        if state.in_crawler_zone and slow_clearance >= thresholds.crawler_zone_release_m:
            state.in_crawler_zone = False
        elif not state.in_crawler_zone and slow_clearance < thresholds.crawler_zone_rearm_m:
            state.in_crawler_zone = True
        if self.config.soil.enable:
            self._hold_crawler_zone_until_liftoff(reading)
        return state.in_crawler_zone

    def _lift_without_retracting(self, leg_speeds: NDArray[np.float64]) -> NDArray[np.float64]:
        """Crawler zone (14.5 step 8): add pure heave so that no leg retracts, then rescale.

        Soil mode (S-2) raises the floor from zero to ``push_speed_fraction v_max``.
        """
        floor_m_s = 0.0
        if self._is_in_soil_mode():
            floor_m_s = self.config.soil.push_speed_fraction * self.geometry.max_speed_m_s
        lifted = leg_speeds + max(0.0, floor_m_s - float(leg_speeds.min()))
        return scale_to_speed_limit(lifted, self.geometry.max_speed_m_s)

    def _update_stroke_end_fault(self, reading: _Reading, leg_speeds: NDArray[np.float64]) -> bool:
        """True once a leg at its stroke end has been asked to extend for the fault time."""
        thresholds = self.config.thresholds
        at_end = reading.motor_stroke_m >= self.geometry.stroke_soft_max_m - (
            thresholds.stroke_end_fault_margin_m
        )
        pushing_at_end = at_end & (leg_speeds > thresholds.stroke_end_fault_speed_m_s)
        state = self._state
        state.stroke_end_steps = state.stroke_end_steps + 1 if pushing_at_end.any() else 0
        return state.stroke_end_steps * self.config.period_s > thresholds.stroke_end_fault_time_s

    def _clip_at_stroke_ends(
        self, reading: _Reading, leg_speeds: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        margin = self.config.thresholds.stroke_end_clip_margin_m
        stroke = reading.motor_stroke_m
        clipped = leg_speeds.copy()
        clipped[(stroke >= self.geometry.stroke_soft_max_m - margin) & (clipped > 0)] = 0.0
        clipped[(stroke <= margin) & (clipped < 0)] = 0.0
        return clipped

    def _update_completion(self, reading: _Reading, filtered_clearance_m: float) -> bool:
        """Completion conditions held for ``done_hold_s`` (14.5 step 11); with the soil response
        never before the lift-off confirmation (S-2)."""
        state = self._state
        if self.config.soil.enable and not self._is_liftoff_confirmed():
            state.complete_since_s = None
            return False
        thresholds = self.config.thresholds
        twist_load = float(self.geometry.twist_vector @ reading.cylinder_force_N)
        # T2: only once the ramped reference has reached the final target.
        is_on_target = (
            self._is_reference_on_target()
            and self._completion_deviation_rad() < thresholds.done_attitude_rad
        )
        is_complete_now = (
            is_on_target
            and abs(filtered_clearance_m - thresholds.clearance_target_m)
            < thresholds.done_clearance_tolerance_m
            and abs(twist_load) < thresholds.done_twist_N
        )
        if not is_complete_now:
            state.complete_since_s = None
            return False
        if state.complete_since_s is None:
            state.complete_since_s = reading.t_s
            return False
        return reading.t_s - state.complete_since_s >= thresholds.done_hold_s

    # --- soil response S-1 .. S-5 (spec rev. 57 282.4 / 285) ---

    def _soil_state(self) -> _SoilState:
        state = self._state
        if state.soil is None:
            state.soil = _SoilState()
        return state.soil

    def _is_liftoff_confirmed(self) -> bool:
        return self._soil_state().is_liftoff_confirmed

    def _is_in_soil_mode(self) -> bool:
        """S-2 is acting: soil mode started and no lift-off confirmed yet."""
        if not self.config.soil.enable:
            return False
        soil = self._soil_state()
        return soil.is_soil_mode and not soil.is_liftoff_confirmed

    def _active_corner_bias_m(self) -> NDArray[np.float64] | None:
        """S-3 bias ``b_k`` in force, ``None`` when off or zero (commands stay bit for bit)."""
        if not self.config.soil.enable:
            return None
        soil = self._soil_state()
        return soil.corner_bias_m if soil.has_corner_bias else None

    def _clearance_corners_m(self, rod_stroke_m: ArrayLike) -> NDArray[np.float64]:
        """Crawler-corner clearance of the control paths: ``c_k``, or ``c_k - b_k`` (S-3)."""
        corners = self.geometry.clearance_corners_m(rod_stroke_m)
        bias = self._active_corner_bias_m()
        return corners if bias is None else corners - bias

    def _clearance_estimate_m(self, rod_stroke_m: ArrayLike) -> float:
        return float(np.min(self._clearance_corners_m(rod_stroke_m)))

    def _reference_weight_N(self) -> float:
        """``W_ref``: YAML superstructure mass times g (S-1 plausibility, S-5 record)."""
        mass_kg = self.geometry.superstructure_mass_kg
        if mass_kg is None:
            mass_kg = BODY_MASS_WITHOUT_YAML_KG
        return mass_kg * STANDARD_GRAVITY_M_S2

    def _period_raw_attitude_rad(self) -> tuple[float, float]:
        """Mean raw tilt of this period; without IMU-rate samples the raw tilt of the
        period-mean specific force (P-S9-4 asks for a raw tilt, not the filtered attitude)."""
        state = self._state
        tilts = state.period_raw_tilts
        if not tilts:
            return state.period_mean_raw_tilt_rad
        roll = float(np.mean([tilt.roll_rad for tilt in tilts]))
        pitch = float(np.mean([tilt.pitch_rad for tilt in tilts]))
        return roll, pitch

    def _record_settle_tilt(self) -> None:
        """P-S9-4 without CHECK: the settle attitude is the mean raw tilt of the first
        ``settle_tilt_samples`` TOUCH periods (with CHECK it is the CHECK attitude)."""
        soil = self._soil_state()
        if self._has_check() or soil.settle_attitude_rad is not None:
            return
        if self._state.phase is not C2Phase.TOUCH:
            return
        soil.settle_tilts.append(self._period_raw_attitude_rad())
        if len(soil.settle_tilts) >= self.config.soil.settle_tilt_samples:
            roll, pitch = np.mean(soil.settle_tilts, axis=0)
            soil.settle_attitude_rad = (float(roll), float(pitch))

    def _settle_attitude_rad(self) -> tuple[float, float] | None:
        if self._has_check():
            return self._state.crawler_attitude_rad
        return self._soil_state().settle_attitude_rad

    def _is_plateau_period(self) -> bool:
        """S-1 window condition on the output applied during the period before this sample:
        no leg retracting and the mean speed at least the window fraction of ``v_max``."""
        applied = np.asarray(self._state.applied_output_m_s, dtype=float)
        min_mean_m_s = self.config.soil.plateau_mean_speed_fraction * self.geometry.max_speed_m_s
        return bool(np.all(applied >= 0.0) and float(np.mean(applied)) >= min_mean_m_s)

    def _plateau_tail(self) -> list[_PlateauSample] | None:
        """Shortest tail of the window spanning ``plateau_window_m`` of mean motor stroke."""
        window = self._soil_state().window
        span_m = self.config.soil.plateau_window_m
        last_stroke_m = window[-1].mean_motor_stroke_m
        if last_stroke_m - window[0].mean_motor_stroke_m < span_m:
            return None
        start = len(window) - 1
        while start > 0 and last_stroke_m - window[start].mean_motor_stroke_m < span_m:
            start -= 1
        return list(window)[start:]

    def _plateau_rise_N(self, tail: list[_PlateauSample]) -> float:
        """Load-sum rise over ``plateau_window_m`` of a first-order fit on the mean stroke
        (end-point difference below three samples)."""
        strokes_m = np.array([sample.mean_motor_stroke_m for sample in tail])
        loads_N = np.array([sample.load_sum_N for sample in tail])
        if len(tail) >= 3:
            slope_N_m = float(np.polyfit(strokes_m - strokes_m.mean(), loads_N, 1)[0])
        else:
            slope_N_m = (loads_N[-1] - loads_N[0]) / max(strokes_m[-1] - strokes_m[0], 1e-9)
        return slope_N_m * self.config.soil.plateau_window_m

    def _update_liftoff_window(self, reading: _Reading) -> None:
        """S-1 (P-S9-2): one LEVEL period of the load-sum plateau window before the LOC."""
        soil = self._soil_state()
        if soil.is_liftoff_confirmed:
            return
        if not self._is_plateau_period():
            soil.window.clear()
            return
        soil.window.append(
            _PlateauSample(
                t_s=float(reading.t_s),
                mean_motor_stroke_m=float(np.mean(reading.motor_stroke_m)),
                load_sum_N=float(np.sum(reading.cylinder_force_N)),
                corner_clearance_m=self.geometry.clearance_corners_m(reading.rod_stroke_m),
                raw_attitude_rad=self._period_raw_attitude_rad(),
            )
        )
        tail = self._plateau_tail()
        if tail is None:
            return
        settings = self.config.soil
        rise_N = self._plateau_rise_N(tail)
        mean_load_N = float(np.array([sample.load_sum_N for sample in tail]).mean())
        is_flat = rise_N <= settings.plateau_rise_max_N
        if is_flat and mean_load_N >= settings.plausibility_fraction * self._reference_weight_N():
            self._confirm_liftoff(reading.t_s, tail, mean_load_N)

    def _corner_bias_m(self, sample: _PlateauSample) -> NDArray[np.float64]:
        """S-3 raw ``b_k = c_k(t_P) - (rho_k - min rho)``: at ``t_P`` the last corner has just
        left the rut, and the body attitude change since the settle lifted corner ``k`` by
        ``rho_k = y_k d_phi - x_k d_theta``."""
        settle_rad = self._settle_attitude_rad()
        if settle_rad is None:
            settle_rad = sample.raw_attitude_rad
        roll_change = sample.raw_attitude_rad[0] - settle_rad[0]
        pitch_change = sample.raw_attitude_rad[1] - settle_rad[1]
        corners_xy = self.geometry.crawler_corners_xy_m
        corner_rise = corners_xy[:, 1] * roll_change - corners_xy[:, 0] * pitch_change
        return sample.corner_clearance_m - (corner_rise - corner_rise.min())

    def _confirm_liftoff(
        self, t_s: float, tail: list[_PlateauSample], mean_load_N: float
    ) -> None:
        """LOC: store ``t_P``, ``W_hat`` and the S-3 bias, end soil mode, report (S-5)."""
        soil = self._soil_state()
        settings = self.config.soil
        plateau_start = tail[0]
        soil.is_liftoff_confirmed = True
        soil.is_soil_mode = False
        soil.liftoff_s = float(t_s)
        soil.plateau_start_s = plateau_start.t_s
        soil.weight_estimate_N = mean_load_N
        soil.weight_ratio = mean_load_N / self._reference_weight_N()
        soil.clearance_at_plateau_start_m = float(plateau_start.corner_clearance_m.min())
        soil.clearance_at_liftoff_m = float(tail[-1].corner_clearance_m.min())
        raw_bias_m = self._corner_bias_m(plateau_start)
        soil.corner_bias_raw_m = raw_bias_m
        bias_m = np.maximum(raw_bias_m, 0.0)  # never raise a corner's clearance estimate
        # User decision 2026-10-26 (n-1): whether the bias applies is judged on the
        # stroke-based c_min(t_P), not on max b_k. b_k carries the IMU attitude change, and an
        # attitude error alone (filter lag 0.4 deg x 2.7 m crawler width = 19 mm) must not
        # switch the bias on. c_min(t_P) > dead zone implies max b_k > dead zone (b_k = c_k at
        # the lowest-rise corner), so this only drops biases the old rule would have applied.
        if soil.clearance_at_plateau_start_m <= settings.corner_bias_deadzone_m:
            bias_m = np.zeros(LEG_COUNT)
        soil.corner_bias_m = bias_m
        self._add_event(t_s, SOIL_EVENT_LIFTOFF_CONFIRMED)
        if soil.has_corner_bias:
            self._add_event(t_s, f"{SOIL_EVENT_CLEARANCE_BIAS}:{_corner_values_mm(bias_m)}")
        low, high = settings.weight_record_range
        if not low <= soil.weight_ratio <= high:
            self._add_event(
                t_s, f"{SOIL_EVENT_WEIGHT_MISMATCH}:{soil.weight_ratio:.3f}", is_warning=True
            )

    def _hold_crawler_zone_until_liftoff(self, reading: _Reading) -> None:
        """S-2 / S-4: before the LOC a released crawler-zone latch is held on (soil mode);
        ``max_push_m`` of mean motor stroke in soil mode raises the S-4 FAULT."""
        soil = self._soil_state()
        if soil.is_liftoff_confirmed:
            return
        state = self._state
        mean_stroke_m = float(np.mean(reading.motor_stroke_m))
        if not state.in_crawler_zone:
            if not soil.is_soil_mode:
                soil.is_soil_mode = True
                soil.soil_mode_start_s = float(reading.t_s)
                soil.soil_mode_start_stroke_m = mean_stroke_m
                self._add_event(reading.t_s, SOIL_EVENT_MODE_START)
            state.in_crawler_zone = True
        if not soil.is_soil_mode or soil.soil_mode_start_stroke_m is None:
            return
        soil.push_m = mean_stroke_m - soil.soil_mode_start_stroke_m
        if soil.push_m > self.config.soil.max_push_m:
            # As the reference rules: this period's command still goes out, FAULT holds next.
            self._add_event(reading.t_s, SOIL_EVENT_LIFTOFF_UNCONFIRMED, is_warning=True)
            state.phase = C2Phase.FAULT

    def _soil_meta(self) -> dict[str, Any]:
        """P-S9-7 meta ``soil`` (JSON-serialisable)."""
        settings = self.config.soil
        meta: dict[str, Any] = {"settings": settings.to_meta()}
        if not settings.enable:
            return meta
        soil = self._soil_state()
        raw_bias = soil.corner_bias_raw_m
        settle = self._settle_attitude_rad()
        meta.update(
            {
                "loc": soil.is_liftoff_confirmed,
                "soil_mode": soil.is_soil_mode,
                "t_P_s": soil.plateau_start_s,
                "t_loc_s": soil.liftoff_s,
                "W_hat_N": soil.weight_estimate_N,
                "W_ratio": soil.weight_ratio,
                "W_ref_N": self._reference_weight_N(),
                "corner_order": list(CRAWLER_CORNER_NAMES),
                "bias_corner_m": soil.corner_bias_m.tolist(),
                "bias_corner_raw_m": None if raw_bias is None else raw_bias.tolist(),
                "clearance_at_P_m": soil.clearance_at_plateau_start_m,
                "clearance_at_loc_m": soil.clearance_at_liftoff_m,
                "settle_attitude_rad": None if settle is None else [float(a) for a in settle],
                "soil_mode_t_s": soil.soil_mode_start_s,
                "push_m": soil.push_m,
            }
        )
        return meta

    # --- REANCHOR (revision R2, design 17) ---

    def _is_reanchor_decided(self) -> bool:
        state = self._state
        return state.reanchor is not None or state.reanchor_outcome is not None

    def _add_event(self, t_s: float, name: str, *, is_warning: bool = False) -> None:
        self._state.events.append(C2Event(t_s, name))
        if is_warning:
            logger.warning("C2 t=%.2f s: %s", t_s, name)

    def _reanchor_skip_reason(self, reading: _Reading) -> str | None:
        """Why the first DONE does not re-anchor (design 17.2.2), ``None`` when it does."""
        state = self._state
        settings = self.config.reanchor
        if not settings.enable:
            return "disabled"
        if settings.direction is ReanchorDirection.OFF:
            return "direction_off"
        # H1 / H2: relative pitch between the target and the pitch the pads are anchored at
        # (theta_crawler at first; equal to the former |theta_crawler| rule for a level target).
        anchor_pitch = state.reanchor_anchor_pitch_rad
        _, target_pitch = self._target_rad()
        theta_min = settings.theta_min_rad - REANCHOR_THETA_SLACK_RAD
        if anchor_pitch is None or abs(target_pitch - anchor_pitch) < theta_min:
            return "theta_below_min"
        # Spec 82.5 (C): theta > 0 = nose down, so anchor - target < 0 is a relative nose-up
        # slope, where H4 raises the rod lateral load transient instead of relieving it.
        is_relative_nose_up = anchor_pitch - target_pitch < 0.0
        if settings.direction is ReanchorDirection.NOSE_DOWN_ONLY and is_relative_nose_up:
            return "nose_up"
        if not state.is_lifted:
            return "not_lifted"
        rear_legs = (LEG_ORDER.index("RL"), LEG_ORDER.index("RR"))
        if any(leg in rear_legs for leg in self._pressures.fallback_legs):
            return "rod_sensor_fallback"  # U65: no trustworthy rear stop reading
        if state.in_crawler_zone:
            return "crawler_zone"
        margin = settings.stroke_end_margin_m
        stroke = reading.motor_stroke_m
        if margin > 0.0 and (
            (stroke < margin).any() or (stroke > self.geometry.stroke_soft_max_m - margin).any()
        ):
            return "stroke_margin"
        return None

    def _skip_reanchor(self, t_s: float, reason: str) -> None:
        self._state.reanchor_outcome = f"skipped:{reason}"
        self._state.reanchor_outcomes.append(self._state.reanchor_outcome)
        self._add_event(t_s, f"reanchor_skipped:{reason}")

    def reanchor_stop_forces_N(self, seal_band_N: float) -> tuple[float, ...]:
        """``P_stop,k = max(S_k, floor_abs, F_min + F_band + margin)`` per step (design 17.2.3).

        Args:
            seal_band_N: ``F_band`` at the start of the sequence.

        Returns:
            Stop readings of the target leg, one per step of ``stair_N``.
        """
        settings = self.config.reanchor
        floor_N = self.geometry.F_min_N + seal_band_N + settings.floor_margin_N
        return tuple(max(stair, settings.floor_abs_N, floor_N) for stair in settings.stair_N)

    def reanchor_direction(self, target_leg: int) -> NDArray[np.float64]:
        """Twist-mode direction ``-sgn(n_j) n / max|n|`` that unloads leg ``target_leg``.

        ``A^T n = 0``, so the rigid-body attitude does not change; the fastest leg moves at 1.
        """
        twist = self.geometry.twist_vector
        return -math.copysign(1.0, twist[target_leg]) * twist / np.max(np.abs(twist))

    def _start_reanchor(self, reading: _Reading) -> NDArray[np.float64]:
        """Fix the stop thresholds, enter REANCHOR / WAIT and run its first period."""
        self._enter_reanchor(reading)
        return self._reanchor_step(reading)

    def _enter_reanchor(self, reading: _Reading) -> None:
        """Fix the stop thresholds with the ``F_band`` of now and enter REANCHOR / WAIT."""
        state = self._state
        seal_band = state.seal_band_N
        state.reanchor = _ReanchorRun(
            stop_force_N=self.reanchor_stop_forces_N(seal_band),
            seal_band_used_N=seal_band,
            stage_start_s=reading.t_s,
        )
        state.phase = C2Phase.REANCHOR
        self._add_event(reading.t_s, "reanchor_started")

    def _reanchor_speed_m_s(self) -> float:
        return self.config.reanchor.speed_fraction * self.geometry.max_speed_m_s

    def _reanchor_target(self, step: int) -> int:
        targets = self.config.reanchor.targets
        return LEG_ORDER.index(targets[step % len(targets)])

    def _reanchor_attitude_is_bad(self) -> bool:
        return self._completion_deviation_rad() > self.config.reanchor.attitude_abort_rad

    def _reanchor_step(self, reading: _Reading) -> NDArray[np.float64]:
        """One REANCHOR period (design 17.2.3, checks in the order of 17.7 Q5)."""
        run = self._state.reanchor
        assert run is not None
        t_s = reading.t_s
        if run.stage is _ReanchorStage.WAIT:
            if self._reanchor_attitude_is_bad():
                return self._finish_reanchor(t_s, "aborted:attitude_wait")
            if t_s < run.stage_start_s + self.config.reanchor.wait_s:
                return self._zero_speeds()
            run.stage = _ReanchorStage.MOVE  # the first move starts in this period
        if run.stage is _ReanchorStage.ABORT_RETURN:
            assert run.abort_outcome is not None
            return self._return_or_finish(run, t_s, run.abort_outcome)
        if run.step >= len(run.stop_force_N):
            return self._finish_reanchor(t_s, "completed")
        if self._reanchor_attitude_is_bad():
            return self._abort_reanchor(run, t_s, "attitude")
        if run.stage is _ReanchorStage.MOVE:
            return self._reanchor_move(run, reading)
        if run.stage is _ReanchorStage.HOLD:
            return self._reanchor_hold(run, reading)
        if run.stage is _ReanchorStage.RETURN:
            leg_speeds = self._return_speeds(run)
            if leg_speeds is not None:
                return leg_speeds
            self._enter_reanchor_stage(run, _ReanchorStage.HOLD2, t_s)
            return self._zero_speeds()
        return self._reanchor_hold2(run, t_s)

    def _enter_reanchor_stage(self, run: _ReanchorRun, stage: _ReanchorStage, t_s: float) -> None:
        run.stage = stage
        run.stage_start_s = t_s
        if stage is _ReanchorStage.MOVE:
            run.stop_history_N.clear()  # R-1: the unloading rate of the new step only

    def _reanchor_move(self, run: _ReanchorRun, reading: _Reading) -> NDArray[np.float64]:
        """Unload the target leg along the twist mode until its reading reaches ``P_stop,k``."""
        settings = self.config.reanchor
        target = self._reanchor_target(run.step)
        load_estimate = self._load_estimate_N(reading.cylinder_force_lower_N)
        lowest_other_load = float(np.delete(load_estimate, target).min())
        if lowest_other_load < self.geometry.F_min_N + settings.other_margin_N:
            return self._abort_reanchor(run, reading.t_s, "other_low")
        if np.max(np.abs(run.commanded_m)) >= settings.max_step_stroke_m:
            return self._abort_reanchor(run, reading.t_s, "stroke_cap")
        # E-6: the stop is a lower-bound judgement (the allowance is 0 unless set or failed).
        target_reading = float(
            reading.cylinder_force_N[target] - self._pressures.offset_allowance_N[target]
        )
        judged_reading = self._predicted_stop_reading(run, target_reading)
        if judged_reading <= run.stop_force_N[run.step]:
            run.stop_readings_N.append((LEG_ORDER[target], target_reading))
            run.stop_predicted_readings_N.append((LEG_ORDER[target], judged_reading))
            self._enter_reanchor_stage(run, _ReanchorStage.HOLD, reading.t_s)
            return self._zero_speeds()
        leg_speeds = self.reanchor_direction(target) * self._reanchor_speed_m_s()
        run.commanded_m = run.commanded_m + leg_speeds * self.config.period_s
        return leg_speeds

    def _predicted_stop_reading(self, run: _ReanchorRun, target_reading_N: float) -> float:
        """R-1: ``P - r_hat (1 + d)``, ``r_hat`` = mean unloading per period of this step.

        Never above the reading (``r_hat`` is clipped at 0), so the reading's own stop stays
        in force when the prediction fails (spec 99.3). The reading itself with R-1 off.
        """
        settings = self.config.reanchor
        if settings.stop_predictor is StopPredictor.OFF:
            return target_reading_N
        history = run.stop_history_N
        history.append(target_reading_N)
        del history[: -(settings.stop_predictor_intervals + 1)]
        if len(history) < 2:
            return target_reading_N
        drop_per_period = (history[0] - history[-1]) / (len(history) - 1)
        horizon_periods = 1 + self.config.r8.output_delay_periods
        return target_reading_N - max(drop_per_period, 0.0) * horizon_periods

    def _reanchor_hold(self, run: _ReanchorRun, reading: _Reading) -> NDArray[np.float64]:
        """Keep the target unloaded; any leg below the guard aborts (17.2.5)."""
        settings = self.config.reanchor
        lowest_load = float(self._load_estimate_N(reading.cylinder_force_lower_N).min())
        if lowest_load < self.geometry.F_min_N + settings.hold_guard_margin_N:
            return self._abort_reanchor(run, reading.t_s, "hold_low")
        if reading.t_s - run.stage_start_s >= settings.hold_s - REANCHOR_HOLD_SLACK_S:
            # RETURN ends on the commanded travel, not on time, so its start time is not kept.
            run.stage = _ReanchorStage.RETURN
        return self._zero_speeds()

    def _reanchor_hold2(self, run: _ReanchorRun, t_s: float) -> NDArray[np.float64]:
        """After the return: wait, then start the next step (the last one ends a period later)."""
        if t_s - run.stage_start_s >= self.config.reanchor.hold2_s - REANCHOR_HOLD_SLACK_S:
            run.step += 1
            run.commanded_m = np.zeros(LEG_COUNT)
            self._enter_reanchor_stage(run, _ReanchorStage.MOVE, t_s)
        return self._zero_speeds()

    def _return_speeds(self, run: _ReanchorRun) -> NDArray[np.float64] | None:
        """Drive ``c_k`` back to zero at the re-anchoring speed; ``None`` once it is there.

        The last period scales the speed by ``lambda = |c_k|_inf / (v_r T) < 1`` so that the
        commanded travel ends exactly at zero.
        """
        largest = float(np.max(np.abs(run.commanded_m)))
        if largest < REANCHOR_RETURN_DONE_M:
            return None
        speed = self._reanchor_speed_m_s()
        period_s = self.config.period_s
        last_period_scale = min(1.0, largest / (speed * period_s))
        leg_speeds = -run.commanded_m / largest * speed * last_period_scale
        run.commanded_m = run.commanded_m + leg_speeds * period_s
        return leg_speeds

    def _return_or_finish(self, run: _ReanchorRun, t_s: float, outcome: str) -> NDArray[np.float64]:
        leg_speeds = self._return_speeds(run)
        if leg_speeds is None:
            return self._finish_reanchor(t_s, outcome)
        return leg_speeds

    def _abort_reanchor(self, run: _ReanchorRun, t_s: float, reason: str) -> NDArray[np.float64]:
        """Hard abort (17.2.5): start returning the commanded travel in this period, then trim."""
        outcome = f"aborted:{reason}"
        run.abort_outcome = outcome
        run.stage = _ReanchorStage.ABORT_RETURN
        self._add_event(t_s, f"reanchor_{outcome}", is_warning=True)
        return self._return_or_finish(run, t_s, outcome)

    def _finish_reanchor(self, t_s: float, outcome: str) -> NDArray[np.float64]:
        """Latch the outcome and go back to LEVEL to trim (design 17.7 Q7)."""
        state = self._state
        state.reanchor_outcome = outcome
        state.reanchor_outcomes.append(outcome)
        state.phase = C2Phase.LEVEL
        state.complete_since_s = None
        state.probe_round = None
        state.reground = None
        if outcome == "completed":
            _, state.reanchor_anchor_pitch_rad = self._target_rad()  # H2: anchored here now
            # H5a: the probe ran before REANCHOR; the trim goes to READY without another one.
            state.skips_probe_after_reanchor = self._is_reanchor_after_probe()
            self._add_event(t_s, "reanchor_completed")
        elif outcome == "aborted:attitude_wait":  # the other aborts were reported when raised
            self._add_event(t_s, f"reanchor_{outcome}", is_warning=True)
        return self._zero_speeds()

    def _note_band_beyond_reanchor(self, t_s: float) -> None:
        """Event when a probe widened ``F_band`` past the band the stops used (17.7 Q8)."""
        run = self._state.reanchor
        if run is None or run.is_band_exceeded:
            return
        if self._state.seal_band_N > run.seal_band_used_N:
            run.is_band_exceeded = True
            self._add_event(t_s, "reanchor_band_exceeded", is_warning=True)

    # --- PROBE ---

    def _probe_speed_m_s(self) -> float:
        return self.config.probe.speed_fraction * self.geometry.max_speed_m_s

    def _probe_reading(self, reading: _Reading) -> ProbeReading:
        state = self._state
        return ProbeReading(
            t_s=reading.t_s,
            cylinder_force_N=reading.cylinder_force_lower_N,
            rod_stroke_m=reading.rod_stroke_m,
            motor_stroke_m=reading.motor_stroke_m,
            rate_attitude_rad=state.rate_attitude_rad,
            filtered_attitude_rad=(state.roll_rad, state.pitch_rad),
        )

    def _probe_step(self, reading: _Reading) -> NDArray[np.float64]:
        """One period of the probe (``ground_contact.ProbeRound``): legs in LEG_ORDER."""
        state = self._state
        if state.reground is not None:
            return self._reground_step(state.reground, reading)
        probe_reading = self._probe_reading(reading)
        if state.probe_round is None:
            geometry = self.geometry
            state.probe_round = ProbeRound(
                start=probe_reading,
                settings=self.config.probe,
                max_speed_m_s=geometry.max_speed_m_s,
                period_s=self.config.period_s,
                load_sensitivity_diag_N_m=geometry.load_sensitivity_diag_N_m,
                attitude_sensitivity_rad_m=geometry.attitude_sensitivity_rad_m,
                recent_rate_attitude_rad=state.rate_attitude_recent,
                load_band_limits_N=(self._leg_seal_bands_N(), geometry.F_min_N),
                stroke_max_m=geometry.stroke_soft_max_m,
                previous_results=state.probe_history[-1] if state.probe_history else (),
                retract_first_legs=self._pressures.fallback_legs,
                correction_sensitivity_N_m=self.config.probe_correction_sensitivity_N_m,
                start_load_bands=(
                    self.load_bands if self.config.r8.confirmation.is_active else None
                ),
            )
            state.probe_round_count += 1
        probe_round = state.probe_round
        skipped_before = len(probe_round.skipped_legs)
        leg_speeds = probe_round.step(probe_reading)
        if len(probe_round.skipped_legs) > skipped_before:
            self._add_event(reading.t_s, "probe_skipped:stroke_margin", is_warning=True)
        if probe_round.is_finished:
            self._finish_probe_round(probe_round, reading)
        return leg_speeds

    def _finish_probe_round(self, probe_round: ProbeRound, reading: _Reading) -> None:
        """Set F_band, then re-ground a weak leg or go on (READY, or REANCHOR first: H5a)."""
        state = self._state
        settings = self.config.probe
        self._pressures.probe_round_finished(probe_round.results)
        results = self._fallback_probe_results(tuple(probe_round.results), reading)
        state.probe_history.append(results)
        state.probe_round = None
        self._update_seal_band(results)
        self._update_twist_stiffness_scale(results, reading.t_s)
        self._note_band_beyond_reanchor(reading.t_s)

        weakest = self._leg_to_reground(results, reading)
        is_every_leg_grounded = all(result.is_grounded for result in results)
        state.does_last_probe_accept_support = weakest is None and is_every_leg_grounded
        if weakest is None or state.probe_round_count >= settings.max_rounds:
            self._leave_probe(reading)
            return
        leg = weakest.leg_index
        missing_load = self.geometry.F_min_N + settings.reground_load_margin_N
        missing_load -= weakest.load_estimate_N
        load_step = max(missing_load, settings.reground_min_load_step_N)
        target = float(reading.rod_stroke_m[leg]) + load_step / float(
            self.geometry.load_sensitivity_diag_N_m[leg]
        )
        state.reground = _Reground(leg, target)

    def _fallback_probe_results(
        self, results: tuple[ProbeResult, ...], reading: _Reading
    ) -> tuple[ProbeResult, ...]:
        """U65: a rod-side fallback leg's head-only midpoint and seal-friction estimate are not
        used; its load is the lower-bound reading (model bound removed), no friction share."""
        fallback = set(self._pressures.fallback_legs)
        if not fallback:
            return results
        return tuple(
            replace(
                result,
                load_estimate_N=float(reading.cylinder_force_lower_N[result.leg_index]),
                seal_friction_estimate_N=0.0,
            )
            if result.leg_index in fallback
            else result
            for result in results
        )

    def _update_seal_band(self, results: tuple[ProbeResult, ...]) -> None:
        """D5: ``F_band`` from the round's largest seal-friction estimate + margin.

        ``measured_first`` (R5, spec 22.4): the first round of the run replaces the start value
        (at least ``seal_band_min_N``), later rounds only widen it; ``widen_only`` (R4.1):
        every round only widens it.
        """
        state = self._state
        settings = self.config.probe
        largest_friction = max(result.seal_friction_estimate_N for result in results)
        measured_band = largest_friction + settings.seal_band_margin_N
        is_first_measurement = not state.is_seal_band_measured
        if settings.seal_band_rule is SealBandRule.MEASURED_FIRST and is_first_measurement:
            state.seal_band_N = max(settings.seal_band_min_N, measured_band)
        else:
            state.seal_band_N = max(state.seal_band_N, measured_band)
        state.is_seal_band_measured = True

    def _update_twist_stiffness_scale(
        self, results: tuple[ProbeResult, ...], t_s: float
    ) -> None:
        """P-5 / rev. 31 149 P-R8-2, P-R8-3: median measured / head-only nominal ``S_ii``.

        The denominator is ``C2Geometry.load_sensitivity_diag_N_m`` (``k_nom``, the reference
        of ``pre_probe_stiffness_scale``); the U63 C1 values stay for the probe midpoint and
        friction corrections only. Under ``MIN_STIFFNESS_SCALE_LEGS`` legs the stiffness cue
        calls grounded keep the previous scale. Every round replaces the scale (no filter).
        """
        r8 = self.config.r8
        if r8.twist_gain_reference is not TwistGainReference.MEASURED_SII:
            return
        nominal = self.geometry.load_sensitivity_diag_N_m
        ratios = [
            result.incremental_stiffness_N_m / nominal[result.leg_index]
            for result in results
            if result.is_grounded_by_stiffness
            and not result.is_skipped
            and math.isfinite(result.incremental_stiffness_N_m)
        ]
        state = self._state
        state.twist_stiffness_leg_count = len(ratios)
        if len(ratios) < MIN_STIFFNESS_SCALE_LEGS:
            state.twist_stiffness_raw_ratio = None
            return
        raw_ratio = float(np.median(ratios))
        state.twist_stiffness_raw_ratio = raw_ratio
        warning_low, warning_high = r8.stiffness_warning_range
        if not warning_low <= raw_ratio <= warning_high:
            self._add_event(
                t_s, f"WARN_PROBE_STIFFNESS_OUT_OF_RANGE:{raw_ratio:.3f}", is_warning=True
            )
        state.twist_stiffness_scale = _bounded(
            raw_ratio, r8.measured_stiffness_scale_min, r8.measured_stiffness_scale_max
        )

    def _is_reanchor_after_probe(self) -> bool:
        """H5a: REANCHOR is decided after the probe (combined judge only; the pressure judge has
        no probe and decides at the first DONE as before)."""
        return self.config.reanchor.after_probe and self.config.contact is ContactJudge.COMBINED

    def _leave_probe(self, reading: _Reading) -> None:
        """End of the probe: READY, or (H5a, first time) the REANCHOR decision."""
        state = self._state
        if not self._is_reanchor_after_probe() or self._is_reanchor_decided():
            state.phase = C2Phase.READY
            return
        skip_reason = self._reanchor_skip_reason(reading)
        if skip_reason is not None:
            self._skip_reanchor(reading.t_s, skip_reason)
            state.phase = C2Phase.READY
            return
        self._enter_reanchor(reading)

    def _leg_to_reground(
        self, results: tuple[ProbeResult, ...], reading: _Reading
    ) -> ProbeResult | None:
        """Leg the probe round re-grounds, ``None`` for READY (design 14.6, spec P1).

        Weak = judged ungrounded or below ``F_min + 5 kN`` (skipped legs never). R4.1 default
        (``RegroundRule.LOAD_FIRST``, spec 21.2 Q2): a leg whose midpoint load estimate is
        below ``F_min + 5 kN`` first, the lowest estimate, whatever the verdict. Otherwise:
        stiffness-only verdict (design) the first weak leg in LEG_ORDER; combined verdict
        (spec 10.1) the ungrounded leg with the smallest reading (else the lightest weak leg);
        when all four are judged ungrounded (and none is light) nothing is re-grounded and
        ``probe_unresolved`` is reported.
        """
        guard_level = self.geometry.F_min_N + self.config.thresholds.guard_margin_N
        # A leg skipped by the stroke guard (P6) is near its stroke end: never re-ground it.
        weak = [
            r
            for r in results
            if not r.is_skipped and (not r.is_grounded or r.load_estimate_N < guard_level)
        ]
        if not weak:
            return None
        if self.config.probe.reground_rule is RegroundRule.LOAD_FIRST:
            # Q2 (spec 21.2): the midpoint load estimate cancels the seal friction, so a lifted
            # leg reads about -W_rod whatever the other cues say; it goes first.
            light = [r for r in weak if r.load_estimate_N < guard_level]
            if light:
                return min(light, key=lambda result: result.load_estimate_N)
        if not self.config.probe.use_combined_verdict:
            return weak[0]
        ungrounded = [result for result in results if not result.is_grounded]
        if len(ungrounded) == LEG_COUNT:
            self._add_event(reading.t_s, "probe_unresolved", is_warning=True)
            return None
        candidates = [result for result in weak if not result.is_grounded] or weak
        return min(candidates, key=lambda result: reading.cylinder_force_N[result.leg_index])

    def _reground_step(self, reground: _Reground, reading: _Reading) -> NDArray[np.float64]:
        """Extend the weak leg to its target stroke, then re-level (and probe again)."""
        state = self._state
        leg_speeds = self._zero_speeds()
        if reading.rod_stroke_m[reground.leg] < reground.target_stroke_m:
            leg_speeds[reground.leg] = self._probe_speed_m_s()
            return leg_speeds
        state.reground = None
        state.phase = C2Phase.LEVEL
        state.complete_since_s = None
        return leg_speeds

    # --- lock tails (U62, R-H4') ---

    def _request_lock_tails(
        self,
        reading: _Reading,
        phase_before: C2Phase,
        reanchor_stage_before: _ReanchorStage | None,
    ) -> None:
        """Ask for a tail on the grounded legs whose last move was a retraction when a long lock
        starts: DONE or READY entry, REANCHOR stop (HOLD entry). Brief zeros inside LEVEL and
        lifted legs ask for none (spec 63.3)."""
        settings = self.config.lock_tail
        state = self._state
        if not settings.enable or state.lock_tail_speeds:
            return
        if settings.mode is RetractTailMode.READY_HEAVE:
            self._request_ready_heave(reading, phase_before)
            return
        phase = state.phase
        enters_lock = phase is not phase_before and phase in (C2Phase.DONE, C2Phase.READY)
        run = state.reanchor
        enters_hold = (
            run is not None
            and run.stage is _ReanchorStage.HOLD
            and reanchor_stage_before is not _ReanchorStage.HOLD
        )
        if not (enters_lock or enters_hold):
            return
        grounded = (
            reading.cylinder_force_lower_N - self._leg_seal_bands_N() >= self.geometry.F_min_N
        )
        room = reading.motor_stroke_m + settings.tail_m <= self.geometry.stroke_max_m - (
            self.config.thresholds.stroke_end_clip_margin_m
        )
        retracted_last = state.last_nonzero_output_m_s < 0.0
        legs = np.flatnonzero(grounded & room & retracted_last)
        if legs.size == 0:
            return
        speeds = self._tail_speeds()
        state.lock_tail_speeds = {int(leg): list(speeds) for leg in legs}
        state.lock_tail_settle_until_s = None
        state.lock_tail_count += 1
        self._add_event(reading.t_s, "lock_tail:" + ",".join(LEG_ORDER[leg] for leg in legs))

    def _request_ready_heave(self, reading: _Reading, phase_before: C2Phase) -> None:
        """U67: on READY entry after a retraction, all four legs extend ``tail_m`` together."""
        state = self._state
        if state.phase is not C2Phase.READY or phase_before is C2Phase.READY:
            return
        if not np.any(state.last_nonzero_output_m_s < 0.0):
            return  # already locked after an extension
        tail_m = self.config.lock_tail.tail_m
        guard_m = self.geometry.stroke_soft_max_m - STROKE_END_MARGIN_M
        if np.any(reading.motor_stroke_m + tail_m > guard_m):
            self._add_event(reading.t_s, "WARN_TAIL_SKIPPED:stroke_margin", is_warning=True)
            return
        speeds = self._tail_speeds()
        state.lock_tail_speeds = {leg: list(speeds) for leg in range(LEG_COUNT)}
        state.lock_tail_settle_until_s = None
        state.lock_tail_count += 1
        self._add_event(reading.t_s, "ready_heave_tail")

    def _tail_speeds(self) -> list[float]:
        settings = self.config.lock_tail
        speed = settings.speed_fraction * self.geometry.max_speed_m_s
        if self.config.r8.increment_limit is not None:
            return self._tail_speeds_within_increment_limit(speed)
        periods = max(1, math.ceil(settings.tail_m / (speed * self.config.period_s) - 1e-9))
        return [settings.tail_m / (periods * self.config.period_s)] * periods

    def _tail_speeds_within_increment_limit(self, speed_m_s: float) -> list[float]:
        """Spec 99.3 ``ready_heave``: rise by the increment limit to ``speed_m_s`` (e.g. 0.1 ->
        0.2 -> 0.25 ``v_max`` with 0.1 per period), the last period closing ``tail_m``."""
        limit = self.config.r8.increment_limit
        assert limit is not None
        tail_m = self.config.lock_tail.tail_m
        period_s = self.config.period_s
        step_m_s = limit.fraction_per_period * self.geometry.max_speed_m_s
        speeds: list[float] = []
        travel_m = 0.0
        while travel_m < tail_m * (1.0 - 1e-9):
            ramp_speed = step_m_s * (len(speeds) + 1)
            speed = min(speed_m_s, ramp_speed, (tail_m - travel_m) / period_s)
            speeds.append(speed)
            travel_m += speed * period_s
        return speeds

    def _lock_tail_step(self, t_s: float) -> NDArray[np.float64] | None:
        """Tail speeds of this period, zero while settling, ``None`` once done (or none)."""
        state = self._state
        if not state.lock_tail_speeds:
            return None
        leg_speeds = self._zero_speeds()
        moving = False
        for leg, remaining in state.lock_tail_speeds.items():
            if remaining:
                leg_speeds[leg] = remaining.pop(0)
                moving = True
        if moving:
            return leg_speeds
        if state.lock_tail_settle_until_s is None:
            state.lock_tail_settle_until_s = t_s + self.config.lock_tail.settle_s
        if t_s < state.lock_tail_settle_until_s - CHECK_TIME_SLACK_S:
            return leg_speeds
        state.lock_tail_speeds = {}
        state.lock_tail_settle_until_s = None
        return None

    # --- GE2 (R6-G, J-7) ---

    def _is_geometry_judge_active(self) -> bool:
        """U59: GE2 acts only with the combined judge; the pressure judge stays shadow."""
        is_active = self.config.geometry_judge.mode is GeometryJudge.ACTIVE
        return is_active and self.config.contact is ContactJudge.COMBINED

    def _support_trigger_key(self, condition: str) -> str:
        """Same leg and sign: ``G1L:<leg>`` / ``G1S:<leg>``, ``G2+`` / ``G2-`` (37.3)."""
        if condition != "G2":
            return condition
        latest = self._support_shadow.latest
        is_positive = latest is not None and latest.nonplanarity_delta_m > 0.0
        return "G2+" if is_positive else "G2-"

    def _act_on_support_change(self, reading: _Reading, conditions: list[str]) -> None:
        """J-7: READY re-level + probe on a held GE2 cue (the probe verdict stays first).

        (b) G1-S / G2 only after the first reference refresh of the READY stay (G1-L lift
        votes any time); (c) the same key again within ``repeat_window_s`` raises
        ``WARN_SUPPORT_CHANGE_REPEAT`` and latches the key (operator to confirm); (d) the
        conditions come from gate-open samples only (shadow rule). D7: ``WARN_CONTACT_CONFLICT``
        (G1-L on a leg the band calls ABOVE) and ``WARN_GEOMETRY_PRESSURE_MISMATCH`` (G1-S
        without a matching load change).
        """
        state = self._state
        if not conditions or state.phase is not C2Phase.READY:
            return
        if not self._is_geometry_judge_active():
            return
        for condition in conditions:
            kind, _, leg_name = condition.partition(":")
            if kind not in ("G1L", "G1S", "G2"):
                continue  # FLOOR_NONPLANAR is information
            if kind != "G1L" and not state.is_ready_reference_refreshed:
                self._add_event(reading.t_s, f"INFO_SUPPORT_TRIGGER_BEFORE_REFRESH:{condition}")
                continue
            key = self._support_trigger_key(condition)
            if key in state.support_repeat_latched:
                continue
            last = state.last_support_trigger
            window_s = self.config.geometry_judge.repeat_window_s
            if last is not None and last[1] == key and reading.t_s - last[0] <= window_s:
                state.support_repeat_latched.add(key)
                self._add_event(reading.t_s, f"WARN_SUPPORT_CHANGE_REPEAT:{key}", is_warning=True)
                continue
            self._support_conflicts(reading, kind, leg_name)
            state.last_support_trigger = (reading.t_s, key)
            state.support_triggers.append(
                {"t_s": reading.t_s, "condition": condition, "key": key,
                 "is_lift_vote": kind == "G1L"}
            )
            self._add_event(reading.t_s, f"WARN_SUPPORT_CHANGED:{condition}", is_warning=True)
            self._start_relevel()
            return

    def _support_conflicts(self, reading: _Reading, kind: str, leg_name: str) -> None:
        """D7 (K-3, K-6, spec 49.4): geometry / pressure disagreements, warnings only."""
        if not leg_name:
            return
        leg = LEG_ORDER.index(leg_name)
        bands = self._leg_seal_bands_N()
        if kind == "G1L":
            lower = reading.cylinder_force_lower_N[leg] - bands[leg]
            if lower >= self.geometry.F_min_N:
                self._add_event(reading.t_s, f"WARN_CONTACT_CONFLICT:{leg_name}", is_warning=True)
            return
        reference_loads = self._state.support_reference_loads_N
        if reference_loads is None:
            return
        change = np.asarray(reading.cylinder_force_N, dtype=float) - reference_loads
        limit = self.config.geometry_judge.mismatch_load_change_N
        if abs(float(change[leg])) < limit:
            self._add_event(
                reading.t_s, f"WARN_GEOMETRY_PRESSURE_MISMATCH:{leg_name}", is_warning=True
            )

    # --- output ---

    def _slow_near_stroke_end(
        self, reading: _Reading, leg_speeds: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Spec 99.3 end approach: an extending leg within the window below the end-margin
        stroke (``soft end - 10 mm``) moves at most ``end_slowdown_speed_fraction v_max``; the
        whole vector is scaled, so the decomposition stays (design 6.1)."""
        r8 = self.config.r8
        if r8.end_slowdown_window_m is None:
            return leg_speeds
        window_start_m = (
            self.geometry.stroke_soft_max_m - STROKE_END_MARGIN_M - r8.end_slowdown_window_m
        )
        speed_limit = r8.end_slowdown_speed_fraction * self.geometry.max_speed_m_s
        is_too_fast = (reading.motor_stroke_m >= window_start_m) & (leg_speeds > speed_limit)
        if not is_too_fast.any():
            return leg_speeds
        return leg_speeds * (speed_limit / float(leg_speeds[is_too_fast].max()))

    def _apply_output_ramp(self, leg_speeds: NDArray[np.float64]) -> NDArray[np.float64]:
        """``u_out = u_prev + clip(u - u_prev, +-v_max T / ramp)`` (design 14.7), or the R8
        increment limit (skipped by a FAULT stop).

        P-R8-15: a leg whose change the clip cut is flagged :attr:`OutputLimit.INCREMENT`.
        An unclipped leg is not flagged even where ``u_prev + (u - u_prev)`` rounds to the
        last bit of ``u``.
        """
        state = self._state
        ramp_time_s = self.config.output_ramp_time_s
        requested_change = leg_speeds - state.previous_output_m_s
        if self.config.r8.increment_limit is not None and state.phase is C2Phase.FAULT:
            # Rev. 31 P-R8-5: a FAULT (head-side fault or stroke-end fault) stops in one
            # period instead of 4 increments (0.4 s); the amplifier ramp and the valve lag
            # smooth the step. The output delay d still applies.
            output = self._zero_speeds()
        elif self.config.r8.increment_limit is not None:
            limited_change = self._limited_increment(leg_speeds)
            self._note_output_limit(OutputLimit.INCREMENT, requested_change, limited_change)
            output = state.previous_output_m_s + limited_change
        elif ramp_time_s is None:
            output = leg_speeds.copy()
        else:
            max_step = self.geometry.max_speed_m_s * self.config.period_s / ramp_time_s
            step = np.clip(requested_change, -max_step, max_step)
            self._note_output_limit(OutputLimit.INCREMENT, requested_change, step)
            output = state.previous_output_m_s + step
        state.previous_output_m_s = output
        return output

    def _limited_increment(self, leg_speeds: NDArray[np.float64]) -> NDArray[np.float64]:
        """R8 (spec 99.3 / 99.4): ``|du| <= f v_max`` per leg and period; a leg whose change has
        the sign of this period's F_min guard term takes the guard fraction."""
        limit = self.config.r8.increment_limit
        assert limit is not None
        max_speed = self.geometry.max_speed_m_s
        change = leg_speeds - self._state.previous_output_m_s
        max_change = np.full(LEG_COUNT, limit.fraction_per_period * max_speed)
        guard = self._state.guard_m_s
        if guard is not None:
            is_guard_direction = np.sign(change) == np.sign(guard)
            is_guard_direction &= guard != 0.0
            max_change[is_guard_direction] = limit.guard_fraction_per_period * max_speed
        return np.clip(change, -max_change, max_change)
