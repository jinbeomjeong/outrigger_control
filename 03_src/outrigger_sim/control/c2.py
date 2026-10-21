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

The per-period order of operations reproduces the discrete control law of the reduced
model (``04_scripts/03_control/run_c2_revision.py`` class ``C2R``, gain set ``R:BS_hold``, on
top of ``run_c2_timedomain.py`` ``C2D`` and ``04_scripts/01_dynamics/run_control_comparison.py``),
which the design verified; ``05_tests/unit/test_c2.py`` replays recorded traces of that model.

Units SI (m, rad, N, s). Per-leg arrays follow ``LEG_ORDER`` (FL, FR, RL, RR).
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.sensors.attitude import (
    ATTITUDE_FILTER_STAGE_COUNT,
    ATTITUDE_FILTER_TIME_CONSTANT_S,
    AttitudeEstimator,
    CascadedLowPass,
)
from outrigger_sim.sensors.hydraulic import head_area_from_params
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S, LEG_COUNT, Command, Measurements

logger = logging.getLogger(__name__)

C2_CONTROLLER_NAME = "C2"
C2_REVISION = "R2"
DESIGN_SOURCE = (
    "00_docs/04_control/c2_design.md section 14, revision R1 section 16, revision R2 section 17 "
    "(user decisions 2026-10-21)"
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


# --- configuration -------------------------------------------------------------------------


class C2Phase(StrEnum):
    """Controller phase (design 14.2)."""

    TOUCH = "touch"
    LEVEL = "level"
    DONE = "done"
    REANCHOR = "reanchor"
    """Pad re-anchoring after the first DONE (revision R2, design 17)."""
    PROBE = "probe"
    READY = "ready"
    FAULT = "fault"


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
    integrator_limit_rad_s: float = 0.02
    twist_deadband_N: float = 2000.0
    guard_margin_N: float = 5000.0
    """The guard acts below ``F_min + guard_margin_N``."""
    done_attitude_rad: float = math.radians(0.03)
    done_clearance_tolerance_m: float = 2e-3
    done_twist_N: float = 3000.0
    done_hold_s: float = 1.0
    relevel_attitude_rad: float = math.radians(0.07)
    relevel_load_margin_N: float = 3000.0
    """READY re-levels when the lowest load estimate drops below ``F_min + margin``."""
    stroke_end_fault_margin_m: float = 1e-3
    stroke_end_fault_speed_m_s: float = 1e-5
    """A leg counts as 'still asked to extend' above this command."""
    stroke_end_fault_time_s: float = 2.0
    stroke_end_clip_margin_m: float = 1e-4


@dataclass(frozen=True)
class ProbeSettings:
    """Probe of the combined contact judge (design 14.6, reduced model values)."""

    speed_fraction: float = 0.25
    """Probe speed as a fraction of the maximum leg speed."""
    depth_m: float = 2e-3
    hold_s: float = 0.4
    min_travel_m: float = 2e-4
    """Below this extension travel the incremental stiffness is not evaluated."""
    grounded_stiffness_ratio: float = 0.3
    """Grounded when the incremental stiffness exceeds this fraction of ``S_ii``."""
    max_rounds: int = 3
    """Probe rounds per run that may still re-ground a leg."""
    reground_load_margin_N: float = 15e3
    """A re-grounded leg is extended to ``F_min + margin``."""
    reground_min_load_step_N: float = 5e3
    seal_band_margin_N: float = 1e3
    """``F_band <- max(F_band, F_s estimate + margin)`` (decision D5)."""


@dataclass(frozen=True)
class ReanchorSettings:
    """Pad re-anchoring after the first levelling (design 17, revision R2, option set H4).

    The fields are the settings of design 17.7 Q2 without their ``reanchor_`` prefix.
    """

    enable: bool = True
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
    floor_margin_N: float = 10e3
    """Stop floor ``F_min + F_band + margin``: 5 kN criterion + 4.6 kN hold-phase drop +
    pressure noise (design 17.3)."""
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

    def __post_init__(self) -> None:
        if not 0.0 < self.speed_fraction <= 1.0:
            raise ValueError(f"speed_fraction must be in (0, 1], got {self.speed_fraction!r}")
        if not self.stair_N:
            raise ValueError("stair_N needs at least one step")
        unknown = [leg for leg in self.targets if leg not in LEG_ORDER]
        if not self.targets or unknown:
            raise ValueError(f"targets must be leg names of {LEG_ORDER}, got {self.targets!r}")
        object.__setattr__(self, "stair_N", tuple(self.stair_N))
        object.__setattr__(self, "targets", tuple(self.targets))


@dataclass(frozen=True)
class C2Config:
    """Complete C2 setting; the defaults are the decided design values."""

    gains: C2Gains = field(default_factory=C2Gains)
    filters: C2Filters = field(default_factory=C2Filters)
    thresholds: C2Thresholds = field(default_factory=C2Thresholds)
    probe: ProbeSettings = field(default_factory=ProbeSettings)
    reanchor: ReanchorSettings = field(default_factory=ReanchorSettings)
    contact: ContactJudge = ContactJudge.COMBINED
    """Combined by default: the probe after levelling is part of the base procedure (D4)."""
    initial_seal_band_N: float = 13e3
    """``F_band`` at the start of a run (decision D5: design limit 12 kN + 3 sigma)."""
    output_ramp_time_s: float | None = 0.1
    """Output ramp ``|du| <= v_max T / ramp`` (design 14.7); ``None`` turns it off (L2 valve).

    :meth:`C2Controller.from_params` without a config takes YAML ``actuator.command_ramp_s``
    instead, so the controller ramp matches the actuator command limit."""
    period_s: float = DEFAULT_CONTROL_PERIOD_S

    def __post_init__(self) -> None:
        if not self.period_s > 0.0:
            raise ValueError(f"period_s must be > 0, got {self.period_s!r}")
        if self.output_ramp_time_s is not None and not self.output_ramp_time_s > 0.0:
            raise ValueError(
                f"output_ramp_time_s must be > 0 or None, got {self.output_ramp_time_s!r}"
            )
        object.__setattr__(self, "contact", ContactJudge(self.contact))


# --- geometry ------------------------------------------------------------------------------


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
        head_area_m2: Cylinder head area (pressure -> force).
        oil_bulk_modulus_Pa: Effective bulk modulus for ``k_oil(e)``.
        oil_dead_length_m: Dead oil column length for ``k_oil(e)``.
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
    head_area_m2: float
    oil_bulk_modulus_Pa: float
    oil_dead_length_m: float
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
            head_area_m2=head_area_from_params(params),
            oil_bulk_modulus_Pa=float(params.get(OIL_BULK_MODULUS_KEY)),
            oil_dead_length_m=float(params.get(OIL_DEAD_LENGTH_KEY)),
        )

    def __post_init__(self) -> None:
        plane_basis = np.column_stack([np.ones(LEG_COUNT), self.pad_xy_m])
        object.__setattr__(self, "_plane_fit", np.linalg.pinv(plane_basis))
        object.__setattr__(self, "_support_pinv", np.linalg.pinv(self.support_matrix))

    def clearance_estimate_m(self, rod_stroke_m: ArrayLike) -> float:
        """Smallest crawler-corner clearance of the pad plane fitted to the strokes.

        Least-squares plane ``z = c0 + c1 x + c2 y`` through the pad bottoms ``z_retracted - x``
        (rigid body, floor at the crawler bottom), evaluated at the four crawler corners.
        """
        pad_z = self.pad_bottom_z_retracted_m - np.asarray(rod_stroke_m, dtype=float)
        plane = self._plane_fit @ pad_z
        corner_z = plane[0] + self.crawler_corners_xy_m @ plane[1:]
        return float(np.min(self.crawler_bottom_z_m - corner_z))

    def oil_stiffness_N_m(self, stroke_m: ArrayLike) -> NDArray[np.float64]:
        """Locked oil column stiffness ``k_oil(e) = beta A / (dead + e)`` per leg."""
        extension = np.asarray(stroke_m, dtype=float)
        return self.oil_bulk_modulus_Pa * self.head_area_m2 / (self.oil_dead_length_m + extension)

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


class _ProbeStage(Enum):
    EXTEND = "extend"
    RETRACT = "retract"


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of probing one leg (+depth, hold, -depth, hold).

    Attributes:
        leg_index: Leg (LEG_ORDER index).
        load_estimate_N: Extend/retract midpoint corrected by ``S_ii dx / 2``.
        seal_friction_estimate_N: Half the extend/retract reading gap after the stiffness part.
        incremental_stiffness_N_m: ``dP / dx`` of the extension (NaN if the leg barely moved).
        is_grounded: Incremental stiffness above the grounded fraction of ``S_ii``.
    """

    leg_index: int
    load_estimate_N: float
    seal_friction_estimate_N: float
    incremental_stiffness_N_m: float
    is_grounded: bool


@dataclass
class _ProbeRound:
    start_stroke_m: NDArray[np.float64]
    start_force_N: NDArray[np.float64]
    stage_start_s: float
    leg: int = 0
    stage: _ProbeStage = _ProbeStage.EXTEND
    extended_force_N: float = math.nan
    extended_stroke_m: float = math.nan
    results: list[ProbeResult] = field(default_factory=list)


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
            ``reanchor_completed`` or ``reanchor_band_exceeded``.
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
    completion_roll_rad: float = 0.0
    completion_pitch_rad: float = 0.0
    roll_integral: float = 0.0
    pitch_integral: float = 0.0
    is_lifted: bool = False
    complete_since_s: float | None = None
    stroke_end_steps: int = 0
    probe_round: _ProbeRound | None = None
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
        self._state = _RunState(seal_band_N=self.config.initial_seal_band_N)

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
        """Clear filters, integrators, phase and probe bookkeeping."""
        self._attitude.reset()
        self._completion_filter.reset()
        self._clearance_filter.reset()
        self._crawler_rule_force_filter.reset()
        self._state = _RunState(seal_band_N=self.config.initial_seal_band_N)

    def update(self, measurements: Measurements) -> Command:
        """Leg speed command for the next period (design 14.3 order: read, filter, phase, ramp)."""
        reading = self._read(measurements)
        self._update_attitude_filters(measurements)
        leg_speeds = self._phase_command(reading)
        self._state.sample_count += 1
        output = self._apply_output_ramp(leg_speeds)
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
            "probe": asdict(self.config.probe),
            "reanchor": self._reanchor_meta(),
            "geometry": {
                "twist_vector": geometry.twist_vector.tolist(),
                "nominal_pad_stiffness_N_m": geometry.nominal_pad_stiffness_N_m,
                "F_min_N": geometry.F_min_N,
                "max_speed_m_s": geometry.max_speed_m_s,
                "stroke_max_m": geometry.stroke_max_m,
                "head_area_m2": geometry.head_area_m2,
                "crawler_xy_box_m": [list(bounds) for bounds in CRAWLER_XY_BOX_M],
            },
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
            "theta_crawler_rad": state.theta_crawler_rad,
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
    def probe_history(self) -> tuple[tuple[ProbeResult, ...], ...]:
        """Results of every completed probe round, oldest first."""
        return tuple(self._state.probe_history)

    # --- input and filters ---

    def _read(self, measurements: Measurements) -> _Reading:
        force = measurements.head_pressure_Pa * self.geometry.head_area_m2
        motor_stroke = np.array(measurements.stroke_m)
        if measurements.stroke_corrected_m is not None:
            rod_stroke = np.array(measurements.stroke_corrected_m)
        else:
            rod_stroke = motor_stroke - force / self.geometry.oil_stiffness_N_m(motor_stroke)
        # R1 (14.3): P_bar runs in every phase so that it is settled when LEVEL starts.
        force_lowpass = self._crawler_rule_force_filter.update(force)
        return _Reading(measurements.t_s, force, rod_stroke, motor_stroke, force_lowpass)

    def _update_attitude_filters(self, measurements: Measurements) -> None:
        estimate = self._attitude.update(measurements.t_s, measurements.specific_force_m_s2)
        completion = self._completion_filter.update([estimate.roll_rad, estimate.pitch_rad])
        state = self._state
        state.roll_rad, state.pitch_rad = estimate.roll_rad, estimate.pitch_rad
        state.completion_roll_rad, state.completion_pitch_rad = map(float, completion)

    def _load_estimate_N(self, cylinder_force_N: NDArray[np.float64]) -> NDArray[np.float64]:
        if self.config.contact is ContactJudge.PRESSURE:
            return cylinder_force_N
        return cylinder_force_N - self._state.seal_band_N

    def _zero_speeds(self) -> NDArray[np.float64]:
        return np.zeros(LEG_COUNT)

    # --- phases ---

    def _phase_command(self, reading: _Reading) -> NDArray[np.float64]:
        phase = self._state.phase
        if phase is C2Phase.TOUCH:
            return self._touch(reading)
        if phase is C2Phase.FAULT:
            return self._zero_speeds()
        if phase is C2Phase.REANCHOR:
            return self._clip_at_stroke_ends(reading, self._reanchor_step(reading))
        if phase is C2Phase.DONE and not self._is_reanchor_decided():
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
        is_waiting = self._update_touch_latches(bears_touch_load, reading.t_s)
        state.touch_seen |= bears_touch_load
        max_speed = self.geometry.max_speed_m_s
        approach_speed = np.where(
            state.touch_seen, thresholds.touch_approach_speed_fraction * max_speed, max_speed
        )
        leg_speeds = np.where(state.touched | is_waiting, 0.0, approach_speed)
        if state.touched.all():
            state.phase = C2Phase.LEVEL
            state.theta_crawler_rad = state.pitch_rad
            state.roll_integral = 0.0
            state.pitch_integral = 0.0
        return leg_speeds

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
        # The first sample closes the first control period, so sample k ends at (k + 1) T.
        sample_end_s = (state.sample_count + 1) * self.config.period_s
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
            if self.config.contact is ContactJudge.PRESSURE:
                state.phase = C2Phase.READY
                return self._zero_speeds()
            state.phase = C2Phase.PROBE
        if state.phase is C2Phase.PROBE:
            return self._probe_step(reading)
        return self._zero_speeds()

    def _needs_relevel(self, reading: _Reading) -> bool:
        state = self._state
        thresholds = self.config.thresholds
        tilt = max(abs(state.completion_roll_rad), abs(state.completion_pitch_rad))
        if tilt > thresholds.relevel_attitude_rad:
            return True
        if state.phase is not C2Phase.READY or not state.is_lifted:
            return False
        lowest_load = float(self._load_estimate_N(reading.cylinder_force_N).min())
        return lowest_load < self.geometry.F_min_N + thresholds.relevel_load_margin_N

    def _start_relevel(self) -> None:
        """Back to LEVEL keeping the integrators; probe bookkeeping restarts."""
        state = self._state
        state.phase = C2Phase.LEVEL
        state.complete_since_s = None
        state.probe_round = None
        state.reground = None

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
        load_estimate = self._load_estimate_N(reading.cylinder_force_N)
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
        roll_rate, state.roll_integral = self._attitude_pi(-state.roll_rad, state.roll_integral)
        pitch_rate, state.pitch_integral = self._attitude_pi(-state.pitch_rad, state.pitch_integral)
        return roll_rate, pitch_rate

    def _attitude_pi(self, error_rad: float, integral: float) -> tuple[float, float]:
        """PI with conditional integration (anti-windup, design 6.2): rate and new integral."""
        thresholds = self.config.thresholds
        band_low, band_high = thresholds.integrator_band_rad
        if band_low < abs(error_rad) < band_high:
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
        at_end = reading.motor_stroke_m >= self.geometry.stroke_max_m - (
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
        clipped[(stroke >= self.geometry.stroke_max_m - margin) & (clipped > 0)] = 0.0
        clipped[(stroke <= margin) & (clipped < 0)] = 0.0
        return clipped

    def _update_completion(self, reading: _Reading, filtered_clearance_m: float) -> bool:
        """Completion conditions held for ``done_hold_s`` (14.5 step 11)."""
        state = self._state
        thresholds = self.config.thresholds
        twist_load = float(self.geometry.twist_vector @ reading.cylinder_force_N)
        is_level = (
            abs(state.completion_roll_rad) < thresholds.done_attitude_rad
            and abs(state.completion_pitch_rad) < thresholds.done_attitude_rad
        )
        is_complete_now = (
            is_level
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
        theta_crawler = state.theta_crawler_rad
        theta_min = settings.theta_min_rad - REANCHOR_THETA_SLACK_RAD
        if theta_crawler is None or abs(theta_crawler) < theta_min:
            return "theta_below_min"
        if not state.is_lifted:
            return "not_lifted"
        if state.in_crawler_zone:
            return "crawler_zone"
        margin = settings.stroke_end_margin_m
        stroke = reading.motor_stroke_m
        if margin > 0.0 and (
            (stroke < margin).any() or (stroke > self.geometry.stroke_max_m - margin).any()
        ):
            return "stroke_margin"
        return None

    def _skip_reanchor(self, t_s: float, reason: str) -> None:
        self._state.reanchor_outcome = f"skipped:{reason}"
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
        state = self._state
        seal_band = state.seal_band_N
        state.reanchor = _ReanchorRun(
            stop_force_N=self.reanchor_stop_forces_N(seal_band),
            seal_band_used_N=seal_band,
            stage_start_s=reading.t_s,
        )
        state.phase = C2Phase.REANCHOR
        self._add_event(reading.t_s, "reanchor_started")
        return self._reanchor_step(reading)

    def _reanchor_speed_m_s(self) -> float:
        return self.config.reanchor.speed_fraction * self.geometry.max_speed_m_s

    def _reanchor_target(self, step: int) -> int:
        targets = self.config.reanchor.targets
        return LEG_ORDER.index(targets[step % len(targets)])

    def _reanchor_attitude_is_bad(self) -> bool:
        state = self._state
        tilt = max(abs(state.completion_roll_rad), abs(state.completion_pitch_rad))
        return tilt > self.config.reanchor.attitude_abort_rad

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
        load_estimate = self._load_estimate_N(reading.cylinder_force_N)
        lowest_other_load = float(np.delete(load_estimate, target).min())
        if lowest_other_load < self.geometry.F_min_N + settings.other_margin_N:
            return self._abort_reanchor(run, reading.t_s, "other_low")
        if np.max(np.abs(run.commanded_m)) >= settings.max_step_stroke_m:
            return self._abort_reanchor(run, reading.t_s, "stroke_cap")
        target_reading = float(reading.cylinder_force_N[target])
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
        lowest_load = float(self._load_estimate_N(reading.cylinder_force_N).min())
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
        state.phase = C2Phase.LEVEL
        state.complete_since_s = None
        state.probe_round = None
        state.reground = None
        if outcome == "completed":
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

    def _probe_step(self, reading: _Reading) -> NDArray[np.float64]:
        """One period of the probe: each leg +depth, hold, -depth, hold, in leg order."""
        state = self._state
        if state.reground is not None:
            return self._reground_step(state.reground, reading)
        if state.probe_round is None:
            state.probe_round = _ProbeRound(
                start_stroke_m=reading.rod_stroke_m.copy(),
                start_force_N=reading.cylinder_force_N.copy(),
                stage_start_s=reading.t_s,
            )
            state.probe_round_count += 1
        probe_round = state.probe_round
        settings = self.config.probe
        speed = self._probe_speed_m_s()
        move_time_s = settings.depth_m / speed
        elapsed_s = reading.t_s - probe_round.stage_start_s
        leg_speeds = self._zero_speeds()
        if elapsed_s < move_time_s:
            is_extending = probe_round.stage is _ProbeStage.EXTEND
            leg_speeds[probe_round.leg] = speed if is_extending else -speed
            return leg_speeds
        if elapsed_s < move_time_s + settings.hold_s:
            return leg_speeds
        leg = probe_round.leg
        if probe_round.stage is _ProbeStage.EXTEND:
            probe_round.extended_force_N = float(reading.cylinder_force_N[leg])
            probe_round.extended_stroke_m = float(reading.rod_stroke_m[leg])
            probe_round.stage = _ProbeStage.RETRACT
            probe_round.stage_start_s = reading.t_s
            return leg_speeds
        probe_round.results.append(self._probe_result(probe_round, reading))
        probe_round.leg += 1
        probe_round.stage = _ProbeStage.EXTEND
        probe_round.stage_start_s = reading.t_s
        if probe_round.leg == LEG_COUNT:
            self._finish_probe_round(probe_round, reading)
        return leg_speeds

    def _probe_result(self, probe_round: _ProbeRound, reading: _Reading) -> ProbeResult:
        settings = self.config.probe
        leg = probe_round.leg
        sensitivity = float(self.geometry.load_sensitivity_diag_N_m[leg])
        extended_force = probe_round.extended_force_N
        extended_stroke = probe_round.extended_stroke_m
        retracted_force = float(reading.cylinder_force_N[leg])
        retracted_stroke = float(reading.rod_stroke_m[leg])
        travel = extended_stroke - float(probe_round.start_stroke_m[leg])
        has_moved = travel > settings.min_travel_m
        force_rise = extended_force - float(probe_round.start_force_N[leg])
        stiffness = force_rise / travel if has_moved else math.nan
        stroke_gap = extended_stroke - retracted_stroke
        load = 0.5 * (extended_force + retracted_force) - 0.5 * sensitivity * stroke_gap
        seal_friction = 0.5 * (extended_force - retracted_force - sensitivity * stroke_gap)
        is_grounded = has_moved and stiffness > settings.grounded_stiffness_ratio * sensitivity
        return ProbeResult(leg, load, seal_friction, stiffness, bool(is_grounded))

    def _finish_probe_round(self, probe_round: _ProbeRound, reading: _Reading) -> None:
        """Widen F_band, then re-ground a weak leg or declare READY."""
        state = self._state
        settings = self.config.probe
        results = tuple(probe_round.results)
        state.probe_history.append(results)
        state.probe_round = None
        largest_friction = max(result.seal_friction_estimate_N for result in results)
        state.seal_band_N = max(state.seal_band_N, largest_friction + settings.seal_band_margin_N)
        self._note_band_beyond_reanchor(reading.t_s)

        guard_level = self.geometry.F_min_N + self.config.thresholds.guard_margin_N
        weak = [r for r in results if not r.is_grounded or r.load_estimate_N < guard_level]
        if not weak or state.probe_round_count >= settings.max_rounds:
            state.phase = C2Phase.READY
            return
        leg = weak[0].leg_index
        missing_load = self.geometry.F_min_N + settings.reground_load_margin_N
        missing_load -= weak[0].load_estimate_N
        load_step = max(missing_load, settings.reground_min_load_step_N)
        target = float(reading.rod_stroke_m[leg]) + load_step / float(
            self.geometry.load_sensitivity_diag_N_m[leg]
        )
        state.reground = _Reground(leg, target)

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
