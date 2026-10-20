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

The per-period order of operations reproduces the discrete control law of the reduced
model (``04_scripts/03_control/run_c2_timedomain.py`` class ``C2D`` on top of
``04_scripts/01_dynamics/run_control_comparison.py`` ``Controller``/``C2``), which the design
verified; ``05_tests/unit/test_c2.py`` replays recorded traces of that model.

Units SI (m, rad, N, s). Per-leg arrays follow ``LEG_ORDER`` (FL, FR, RL, RR).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import Params
from outrigger_sim.sensors.attitude import (
    ATTITUDE_FILTER_STAGE_COUNT,
    ATTITUDE_FILTER_TIME_CONSTANT_S,
    AttitudeEstimator,
    CascadedLowPass,
)
from outrigger_sim.sensors.hydraulic import head_area_from_params
from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S, LEG_COUNT, Command, Measurements

C2_CONTROLLER_NAME = "C2"
DESIGN_SOURCE = "00_docs/04_control/c2_design.md section 14 (user decision 2026-10-21)"

# Crawler footprint box in body xy (m): parts_classified.csv row 'COMPOUND' bbox, CAD (X, Z)
# -> body (y, x). Not in the YAML; same value as 04_scripts/01_dynamics/dyn_model.py
# geometry_from_params (used by the reduced model the design was verified on).
CRAWLER_XY_BOX_M = ((-1.840, 1.844), (-1.366, 1.366))

OIL_BULK_MODULUS_KEY = "actuator.oil_bulk_modulus_eff_Pa"
OIL_DEAD_LENGTH_KEY = "actuator.oil_dead_length_m"


# --- configuration -------------------------------------------------------------------------


class C2Phase(StrEnum):
    """Controller phase (design 14.2)."""

    TOUCH = "touch"
    LEVEL = "level"
    DONE = "done"
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


@dataclass(frozen=True)
class C2Thresholds:
    """Phase, guard and completion thresholds (design 14.4-14.6, reduced model values)."""

    touch_load_factor: float = 1.5
    """Touchdown when the leg load reaches this multiple of F_min (pad preload)."""
    free_air_window_s: float = 5.0
    """Combined judge: free-air reading = median of the readings of the first 5 s."""
    rod_weight_N: float = 1047.2
    """Rod + pad weight seen by the free-air reading (reduced model ``rod_weight_N``)."""
    clearance_target_m: float = 0.05
    """Crawler clearance after levelling (YAML ``simulation.crawler_clearance_m``)."""
    lifted_clearance_m: float = 0.01
    """``lifted`` latches once the clearance estimate exceeds this."""
    crawler_zone_clearance_m: float = 0.02
    """Below this clearance the crawler may bear load: add pure heave instead of retracting."""
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
class C2Config:
    """Complete C2 setting; the defaults are the decided design values."""

    gains: C2Gains = field(default_factory=C2Gains)
    filters: C2Filters = field(default_factory=C2Filters)
    thresholds: C2Thresholds = field(default_factory=C2Thresholds)
    probe: ProbeSettings = field(default_factory=ProbeSettings)
    contact: ContactJudge = ContactJudge.COMBINED
    """Combined by default: the probe after levelling is part of the base procedure (D4)."""
    initial_seal_band_N: float = 13e3
    """``F_band`` at the start of a run (decision D5: design limit 12 kN + 3 sigma)."""
    output_ramp_time_s: float | None = 0.1
    """Output ramp ``|du| <= v_max T / ramp`` (design 14.7); ``None`` turns it off (L2 valve)."""
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


@dataclass
class _RunState:
    seal_band_N: float
    phase: C2Phase = C2Phase.TOUCH
    sample_count: int = 0
    touched: NDArray[np.bool_] = field(default_factory=lambda: np.zeros(LEG_COUNT, dtype=bool))
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


@dataclass(frozen=True)
class _Reading:
    t_s: float
    cylinder_force_N: NDArray[np.float64]
    rod_stroke_m: NDArray[np.float64]
    """Rod position (oil compression removed): clearance, lift latch, probe."""
    motor_stroke_m: NDArray[np.float64]
    """Measured stroke (L1 motor position): stroke-end fault and clipping."""


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
        self._state = _RunState(seal_band_N=self.config.initial_seal_band_N)

    @classmethod
    def from_params(cls, params: Params, config: C2Config | None = None) -> C2Controller:
        """Controller for the machine described by ``params``."""
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
        return _Reading(measurements.t_s, force, rod_stroke, motor_stroke)

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
        if phase is not C2Phase.LEVEL:
            held = self._hold_probe_or_relevel(reading)
            if held is not None:
                return held
        return self._level(reading)

    def _touch(self, reading: _Reading) -> NDArray[np.float64]:
        """Extend every leg at full speed until its load passes the touchdown level (14.4)."""
        state = self._state
        touch_load = self._touchdown_load_N(reading)
        touch_level = self.config.thresholds.touch_load_factor * self.geometry.F_min_N
        state.touched |= touch_load >= touch_level
        leg_speeds = np.where(state.touched, 0.0, self.geometry.max_speed_m_s)
        if state.touched.all():
            state.phase = C2Phase.LEVEL
            state.roll_integral = 0.0
            state.pitch_integral = 0.0
        return leg_speeds

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
        if clearance < thresholds.crawler_zone_clearance_m:
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
