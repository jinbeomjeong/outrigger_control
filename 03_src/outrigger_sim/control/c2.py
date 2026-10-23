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
    AttitudeEstimator,
    CascadedLowPass,
)
from outrigger_sim.sensors.hydraulic import (
    leg_annulus_areas_from_params,
    leg_head_areas_from_params,
)
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S, LEG_COUNT, Command, Measurements

logger = logging.getLogger(__name__)

C2_CONTROLLER_NAME = "C2"
C2_REVISION = "R7"
DESIGN_SOURCE = (
    "00_docs/04_control/c2_design.md section 14, revision R1 section 16, revision R2 section 17; "
    "revision R3 00_docs/04_control/s6_control_spec.md section 2 (user decisions 2026-10-21); "
    "revision R5 s6_control_spec.md revision 7 section 42.1 (user decisions 2026-10-22); "
    "revision R6 s6_control_spec.md 51.1, 53.3-53.4, 57, 59.1 J-7, 61.3, 63-64 (U43-U65); "
    "revision R7 s6_control_spec.md 82.5, 86.1-86.3 (user decisions C and provisional B)"
)

# Crawler footprint box in body xy (m): parts_classified.csv row 'COMPOUND' bbox, CAD (X, Z)
# -> body (y, x). Not in the YAML; same value as 04_scripts/01_dynamics/dyn_model.py
# geometry_from_params (used by the reduced model the design was verified on).
CRAWLER_XY_BOX_M = ((-1.840, 1.844), (-1.366, 1.366))

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
REFERENCE_UPDATE_PHASES = frozenset({C2Phase.DONE, C2Phase.READY})
"""GE1'-b: phases whose entry arms a refresh of the shadow reference."""


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

    def __post_init__(self) -> None:
        if not 0.0 < self.speed_fraction <= 1.0:
            raise ValueError(f"speed_fraction must be in (0, 1], got {self.speed_fraction!r}")
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
    """C1: ``(phi_c, theta_c)`` = mean filtered attitude over this window (ASSUMPTION)."""
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

    def __post_init__(self) -> None:
        if not self.period_s > 0.0:
            raise ValueError(f"period_s must be > 0, got {self.period_s!r}")
        if self.output_ramp_time_s is not None and not self.output_ramp_time_s > 0.0:
            raise ValueError(
                f"output_ramp_time_s must be > 0 or None, got {self.output_ramp_time_s!r}"
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
        30 s). The R8 period, filters and limits are not in the code yet; set ``period_s``
        and the rest with them.
        """
        return replace(self, two_pressure=self.two_pressure.with_r8_period())

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


def _optional_float(params: Params, key: str, default: float) -> float:
    try:
        return float(params.get(key))
    except ParamsError:
        return default


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
    ) -> NDArray[np.float64]:
        """Strokes after tilting by ``(d_phi, d_theta)`` at the clearance target (spec 2.3 A5).

        ``dz = c* - min_k(c_k + y_k d_phi - x_k d_theta)``, ``s_i + dz + y_i d_phi - x_i d_theta``
        (rigid body, small angles, linear in the extensions).
        """
        roll_change, pitch_change = attitude_change_rad
        corners_xy = self.crawler_corners_xy_m
        corner_rise = corners_xy[:, 1] * roll_change - corners_xy[:, 0] * pitch_change
        heave = clearance_target_m - float(
            np.min(self.clearance_corners_m(rod_stroke_m) + corner_rise)
        )
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
    twist = geometry.twist_vector
    k_nom = geometry.nominal_pad_stiffness_N_m
    twist_load = float(twist @ np.asarray(cylinder_force_N, dtype=float))
    deadband = thresholds.twist_deadband_N
    twist_error = (
        0.0 if abs(twist_load) < deadband else twist_load - math.copysign(deadband, twist_load)
    )
    rate = -gains.twist_ktw_1_s * twist_error / k_nom

    loads = np.asarray(load_estimate_N, dtype=float)
    guard_level = geometry.F_min_N + thresholds.guard_margin_N
    lowest_leg = int(np.argmin(loads))
    if loads[lowest_leg] >= guard_level:
        return rate, False
    direction = math.copysign(1.0, twist[lowest_leg])
    if rate * direction < 0:
        rate = 0.0
    rate += direction * gains.guard_kg_1_s * (guard_level - loads[lowest_leg]) / k_nom
    return rate, True


# --- run state -----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Reground:
    leg: int
    target_stroke_m: float


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
            ``INFO_FLOOR_NONPLANAR`` (:func:`is_shadow_event`).
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
    is_band_exceeded: bool = False


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

    def __init__(self, geometry: C2Geometry, config: C2Config | None = None) -> None:
        self.geometry = geometry
        self.config = config if config is not None else C2Config()
        filters = self.config.filters
        period_s = self.config.period_s
        self._attitude = AttitudeEstimator(
            CascadedLowPass(
                filters.attitude_time_constant_s, filters.attitude_stage_count, period_s
            )
        )
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
        return _RunState(
            seal_band_N=self.config.initial_seal_band_N,
            phase=C2Phase.CHECK,
            rate_attitude_recent=deque(maxlen=self._rate_attitude_window_size),
            check_attitudes=deque(maxlen=self._check_window_size),
            requested_target=self.config.target.target,
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
        self._floor_estimator.reset()
        self._support_shadow.reset()
        self._standstill_gate.reset()
        self._pressures.reset()
        self._pressures.set_offset_allowance_N(self.config.pressure_offset_allowance_N)
        self._state = self._new_run_state()

    def update(self, measurements: Measurements) -> Command:
        """Leg speed command for the next period (design 14.3 order: read, filter, phase, ramp)."""
        reading = self._read(measurements)
        self._update_attitude_filters(measurements)
        self._watch_oil_temperature(measurements)
        self._state.last_reading = reading
        phase_before = self._state.phase
        reanchor_stage_before = None if self._state.reanchor is None else self._state.reanchor.stage
        leg_speeds = self._phase_command(reading)
        self._request_lock_tails(reading, phase_before, reanchor_stage_before)
        self._update_support_shadow(reading, phase_before)
        self._state.rate_attitude_recent.append(self._state.rate_attitude_rad)
        self._state.sample_count += 1
        output = self._apply_output_ramp(leg_speeds)
        if np.any(output != 0.0):
            self._state.last_nonzero_command_t_s = measurements.t_s
        moving = output != 0.0
        self._state.last_nonzero_output_m_s = np.where(
            moving, output, self._state.last_nonzero_output_m_s
        )
        return Command(t_s=measurements.t_s, leg_speed_m_s=output)

    def meta(self) -> dict[str, Any]:
        """Name, settings and current friction band (JSON-serialisable, new dict per call)."""
        geometry = self.geometry
        return {
            "controller": C2_CONTROLLER_NAME,
            "design": DESIGN_SOURCE,
            "revision": C2_REVISION,
            "period_s": self.config.period_s,
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
        }

    # --- diagnostics ---

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
        """Friction-band verdict of the last readings (``None`` before the first update)."""
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

    # --- input and filters ---

    def _read(self, measurements: Measurements) -> _Reading:
        state = self._state
        forces = self._pressures.read(
            measurements.t_s,
            np.asarray(measurements.head_pressure_Pa),
            measurements.rod_pressure_Pa,
            state.previous_output_m_s,
            state.phase is C2Phase.READY,
            self._leg_seal_bands_N(),
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

    def _update_attitude_filters(self, measurements: Measurements) -> None:
        estimate = self._attitude.update(measurements.t_s, measurements.specific_force_m_s2)
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
            return self._clip_at_stroke_ends(reading, self._reanchor_step(reading))
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
        state.touch_seen |= bears_touch_load
        max_speed = self.geometry.max_speed_m_s
        approach_speed = np.where(
            state.touch_seen, thresholds.touch_approach_speed_fraction * max_speed, max_speed
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

    def _touchdown_load_N(self, reading: _Reading) -> NDArray[np.float64]:
        if self.config.contact is ContactJudge.PRESSURE:
            return reading.cylinder_force_N
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
        if state.phase is not C2Phase.READY or not state.is_lifted:
            return False
        lowest_load = float(self._load_estimate_N(reading.cylinder_force_lower_N).min())
        return lowest_load < self.geometry.F_min_N + thresholds.relevel_load_margin_N

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
        settings = self.config.target
        if reading.t_s - state.check_start_s < settings.check_time_s - CHECK_TIME_SLACK_S:
            return False
        if self._is_zero_calibration_running():
            return False  # E-3: CHECK ends once the round trip is done as well
        estimate = self._estimate_gyro_bias(reading.t_s)
        if estimate is None:
            return False  # B1': CHECK goes on (window shorter than T_b or still moving)
        self._accept_gyro_bias_estimate(estimate, reading.t_s)
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
        return True

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
        geometry = self.geometry
        thresholds = self.config.thresholds
        clearance = geometry.clearance_estimate_m(reading.rod_stroke_m)
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
        load_estimate = self._load_estimate_N(reading.cylinder_force_lower_N)
        twist_rate, _ = twist_rate_command(
            reading.cylinder_force_N, load_estimate, geometry, self.config.gains, thresholds
        )
        leg_speeds = geometry.leg_speeds(heave_rate, roll_rate, pitch_rate, twist_rate)
        leg_speeds = scale_to_speed_limit(leg_speeds, geometry.max_speed_m_s)
        is_complete = self._update_completion(reading, filtered_clearance)
        if self._update_crawler_zone(reading):
            leg_speeds = self._lift_without_retracting(leg_speeds)
        if self._update_stroke_end_fault(reading, leg_speeds):
            self._state.phase = C2Phase.FAULT
            return self._zero_speeds()
        leg_speeds = self._clip_at_stroke_ends(reading, leg_speeds)
        if is_complete:
            self._state.phase = C2Phase.DONE
        return leg_speeds

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
        slow_clearance = self.geometry.clearance_estimate_m(motor_stroke - compression)
        if state.in_crawler_zone and slow_clearance >= thresholds.crawler_zone_release_m:
            state.in_crawler_zone = False
        elif not state.in_crawler_zone and slow_clearance < thresholds.crawler_zone_rearm_m:
            state.in_crawler_zone = True
        return state.in_crawler_zone

    def _lift_without_retracting(self, leg_speeds: NDArray[np.float64]) -> NDArray[np.float64]:
        """Crawler zone (14.5 step 8): add pure heave so that no leg retracts, then rescale."""
        lifted = leg_speeds + max(0.0, -float(leg_speeds.min()))
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
        """Completion conditions held for ``done_hold_s`` (14.5 step 11)."""
        state = self._state
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
        if target_reading <= run.stop_force_N[run.step]:
            run.stop_readings_N.append((LEG_ORDER[target], target_reading))
            self._enter_reanchor_stage(run, _ReanchorStage.HOLD, reading.t_s)
            return self._zero_speeds()
        leg_speeds = self.reanchor_direction(target) * self._reanchor_speed_m_s()
        run.commanded_m = run.commanded_m + leg_speeds * self.config.period_s
        return leg_speeds

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
        periods = max(1, math.ceil(settings.tail_m / (speed * self.config.period_s) - 1e-9))
        return [settings.tail_m / (periods * self.config.period_s)] * periods

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

    def _apply_output_ramp(self, leg_speeds: NDArray[np.float64]) -> NDArray[np.float64]:
        """``u_out = u_prev + clip(u - u_prev, +-v_max T / ramp)`` (design 14.7)."""
        state = self._state
        ramp_time_s = self.config.output_ramp_time_s
        if ramp_time_s is None:
            output = leg_speeds.copy()
        else:
            max_step = self.geometry.max_speed_m_s * self.config.period_s / ramp_time_s
            step = np.clip(leg_speeds - state.previous_output_m_s, -max_step, max_step)
            output = state.previous_output_m_s + step
        state.previous_output_m_s = output
        return output
