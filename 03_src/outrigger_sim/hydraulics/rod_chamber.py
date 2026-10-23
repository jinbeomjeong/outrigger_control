"""L1-R rod-side chamber: one-sided nonlinear parallel spring of a locked leg (engine independent).

Definitions: ``00_docs/01_dynamics/dynamics_model.md`` 5.12.4 / 5.12.8 (revision 30, L1-R
confirmed: implementation (i) with predictor) and ``00_docs/02_hydraulic/rod_side_pressure.md``
14 (hydraulic specification, numbers ``06_analysis/03_hydraulic/l1r_rod_spring_spec.json``).

L1 keeps the head-only pad contact stiffness ``k_n`` (= ``k_2``) in the engine. This module
returns the extra pad force ``F_x`` (= ``Delta F_R``) that the engine applies along the floor
normal, so that the total normal force follows the locked law::

    N = max(0, Phi(delta)),   F_x = N - k_n max(delta, 0)
    Phi = F_lock + k_n' (delta - delta_lock)              below the knee
    Phi = F_lock + dF_knee + k_n (delta - delta_knee)     at / above the knee (rod side at floor)
    dF_knee = (p_r0 - p_floor) A_ann / r,   r = k_r / (k_h + k_r),   delta_knee = dF_knee / k_n'

which equals ``max(0, k_n delta + (k_n' - k_n) min(Delta delta, Delta delta_knee))`` (5.12.4).

States per leg (rod_side_pressure.md 14.1), from the applied leg speed ``u_applied``:

* ``EXT`` / ``RET``: ``u > +eps`` / ``u < -eps``; no rod spring.
* ``LOCK``: both pilot-operated checks closed, rod side above the floor (``dN/ddelta = k_n'``).
* ``FLOOR``: locked, rod side at the floor 0.1 bar abs (``dN/ddelta = k_n``).
* ``LIFT``: locked, ``N = 0``; the oil is frozen at its zero-pad-force state.

The anchor ``(F_lock, delta_lock, p_r0)`` is taken only when the valve locks (``|u| <= eps``
held for the closing delay ``t_c``), at the total normal force of that instant, so ``F_x`` does
not step; re-contact does not move it. Release (locked -> moving) decays the last ``F_x`` as
``exp(-(t - t_rel) / tau_v)``; a lock during that decay absorbs the residual into the new
anchor. State changes are decided at the current ``delta``; only the returned ``F_x`` may be
evaluated at the predicted ``delta + ddelta/dt * dt`` (predictor on, 5.12.8 Q-D1).

Sensor truth from the same state and the same call:

* rod-side pressure: locked ``p_r = max(p_floor, p_r0 - r q / A_ann)`` with ``q`` the oil force
  change since the lock (``N - F_lock``, frozen at ``-F_lock`` in LIFT); moving: the 7.4 rules
  1-3 (target ``max(p_bB, -F_cyl / A_ann)`` / retract pilot threshold, exact first-order lag);
* head pressure ``p_h = (F_cyl + p_r A_ann) / A_p`` with the floor clip of 7.4 rule 7;
* ``stroke_true``: moving ``s_motor - F_cyl / k_h`` (the L1 formula); locked
  ``s_motor - F_lock,cyl / k_h + x_travel`` with ``x_travel = -q / (k_h + k_r)`` below the knee
  and the part above the knee over ``k_h`` (5.12.8 Q-D4).

``mechanics = off`` returns ``F_x = 0``, ``p_h = F_cyl / A_p``, ``p_r = 0`` and
``stroke_true = s_motor - F_cyl / k_h``: the present L1 truth, bit for bit.

``F_cyl`` is the engine's net cylinder force (motor reaction); it is passed through. Pressures
are gauge [Pa]; only the floor is given absolute. Not implemented: gas separation after FLOOR
(14.3 optional, H6). Damping is not part of this module: the engine keeps one ``c_n`` (LOCK
based, 5.12.8 Q-D3) in all states.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

ATMOSPHERE_PA = 1.01325e5
DEFAULT_MODE_EPSILON_M_S = 1.0e-6
"""14.1 / 5.12.8 Q-D5: a leg moves when ``|u_applied|`` exceeds this."""

STATE_KEYS = (
    "l1r_state",
    "l1r_delta_lock_m",
    "l1r_F_lock_N",
    "l1r_p_r0_Pa",
    "l1r_Fx_prev_N",
    "l1r_release_Fx0_N",
    "l1r_release_t_s",
    "l1r_F_cyl_lock_N",
    "l1r_T_lock_K",
    "l1r_last_direction",
    "l1r_lock_pending_since_s",
    "l1r_p_r_tracked_Pa",
    "l1r_t_s",
    "l1r_delta_m",
    "l1r_temperature_K",
)
"""Snapshot keys (R16): the seven of dynamics 5.12.4 first, then the rest this module needs."""


class RodChamberMode(IntEnum):
    """Rod-chamber state of one leg (14.1)."""

    EXT = 1
    RET = 2
    LOCK = 3
    FLOOR = 4
    LIFT = 5


LOCKED_MODES = (RodChamberMode.LOCK, RodChamberMode.FLOOR, RodChamberMode.LIFT)


class RodSideMechanics(StrEnum):
    """YAML ``actuator.rod_side.mechanics`` (5.12.7 order 2 item 5)."""

    OFF = "off"
    """Present L1: no rod spring, net-force-equivalent head pressure (regression)."""
    ONE_SIDED_PARALLEL = "one_sided_parallel"
    """L1-R."""


class LockPressureSource(StrEnum):
    """Where ``p_r0`` comes from when a leg locks (see the report: to be confirmed)."""

    RULE = "rule"
    """14.3 table: ``p_rod_locked_after_extend_Pa`` after EXT, pilot threshold after RET."""
    TRACKED = "tracked"
    """The moving-state rod pressure (7.4 lag) at the lock instant (5.12.4 ``p_r0`` row)."""


@dataclass(frozen=True)
class CylinderOilColumns:
    """Geometry of the two oil columns of a cylinder (14.3 ``k_h``, ``k_r``).

    Attributes:
        bore_m: Piston (bore) diameter.
        rod_m: Rod diameter.
        extension_m: Extension ``e`` at which the stiffness is frozen (``e_op``, Q-D7).
        stroke_max_m: Mechanical stroke ``s_max``.
        head_dead_length_m: ``L_0h`` (head dead volume as a length).
        rod_dead_length_m: ``L_0r`` (rod-side dead volume as a length).
        bulk_modulus_Pa: Effective oil bulk modulus ``beta``.
    """

    bore_m: float
    rod_m: float
    extension_m: float
    stroke_max_m: float
    head_dead_length_m: float
    rod_dead_length_m: float
    bulk_modulus_Pa: float

    @property
    def head_area_m2(self) -> float:
        return math.pi / 4.0 * self.bore_m**2

    @property
    def annulus_area_m2(self) -> float:
        return math.pi / 4.0 * (self.bore_m**2 - self.rod_m**2)

    @property
    def head_stiffness_N_m(self) -> float:
        """``k_h = beta A_p / (L_0h + e)``."""
        length_m = self.head_dead_length_m + self.extension_m
        return self.bulk_modulus_Pa * self.head_area_m2 / length_m

    @property
    def rod_stiffness_N_m(self) -> float:
        """``k_r = beta A_ann / (s_max - e + L_0r)``."""
        length_m = self.stroke_max_m - self.extension_m + self.rod_dead_length_m
        return self.bulk_modulus_Pa * self.annulus_area_m2 / length_m


@dataclass(frozen=True)
class RodChamberLegParams:
    """Parameters of one leg (14.3, 7.3, 12.2; the defaults are the specs' ASSUMPTION values).

    The engine's head-only pad contact stiffness must equal :attr:`pad_stiffness_head_only_N_m`
    (``k_h`` in series with ``k_out``); :meth:`from_pad_stiffness` builds the parameters from
    that stiffness so the two agree by construction.

    Attributes:
        head_area_m2: ``A_p``.
        annulus_area_m2: ``A_ann``.
        head_stiffness_N_m: ``k_h`` (= L1 ``k_oil(e_op)``, also used by ``stroke_true``).
        rod_stiffness_N_m: ``k_r`` at ``e_op`` (Q-D7).
        outer_stiffness_N_m: ``k_out`` (rod, frame and contact in series with the oil).
        rod_weight_N: ``m_rod g`` of the moving part (reported in the meta only).
        p_rod_locked_after_extend_Pa: ``p_r0`` of a lock after an extension (RULE).
        p_rod_back_extend_Pa: ``p_bB``, moving extend target floor (7.4 rule 1).
        poc_pilot_ratio: ``psi`` of the retract pilot threshold.
        poc_cracking_Pa: ``p_cr`` of the retract pilot threshold.
        p_head_back_retract_Pa: ``p_bA`` of the retract pilot threshold.
        relief_Pa: Upper clip of the moving retract target (7.4 rule 2).
        cavitation_floor_abs_Pa: Rod-side floor, absolute.
        thermal_rod_pressure_Pa_per_K: ``dp_r/dT`` while locked; 0 switches the option off.
    """

    head_area_m2: float
    annulus_area_m2: float
    head_stiffness_N_m: float
    rod_stiffness_N_m: float
    outer_stiffness_N_m: float
    rod_weight_N: float
    p_rod_locked_after_extend_Pa: float = 2.0e5
    p_rod_back_extend_Pa: float = 5.0e5
    poc_pilot_ratio: float = 3.5
    poc_cracking_Pa: float = 3.0e5
    p_head_back_retract_Pa: float = 5.0e5
    relief_Pa: float = 210.0e5
    cavitation_floor_abs_Pa: float = 0.1e5
    thermal_rod_pressure_Pa_per_K: float = 0.0

    def __post_init__(self) -> None:
        positive = (
            self.annulus_area_m2,
            self.head_stiffness_N_m,
            self.rod_stiffness_N_m,
            self.outer_stiffness_N_m,
            self.poc_pilot_ratio,
        )
        if min(positive) <= 0.0:
            raise ValueError("areas, stiffnesses and poc_pilot_ratio must be > 0")
        if self.head_area_m2 <= self.annulus_area_m2:
            raise ValueError("head_area_m2 must exceed annulus_area_m2")

    @classmethod
    def from_oil_columns(
        cls,
        columns: CylinderOilColumns,
        outer_stiffness_N_m: float,
        rod_weight_N: float,
        **options: float,
    ) -> RodChamberLegParams:
        """Parameters with areas and oil stiffnesses computed from the cylinder geometry."""
        return cls(
            head_area_m2=columns.head_area_m2,
            annulus_area_m2=columns.annulus_area_m2,
            head_stiffness_N_m=columns.head_stiffness_N_m,
            rod_stiffness_N_m=columns.rod_stiffness_N_m,
            outer_stiffness_N_m=outer_stiffness_N_m,
            rod_weight_N=rod_weight_N,
            **options,
        )

    @classmethod
    def from_pad_stiffness(
        cls,
        columns: CylinderOilColumns,
        pad_stiffness_head_only_N_m: float,
        rod_weight_N: float,
        **options: float,
    ) -> RodChamberLegParams:
        """Parameters whose ``k_n`` is the engine's pad stiffness (``k_out`` solved from it)."""
        head_N_m = columns.head_stiffness_N_m
        if pad_stiffness_head_only_N_m >= head_N_m:
            raise ValueError("pad stiffness must be below the head oil stiffness k_h")
        outer_N_m = 1.0 / (1.0 / pad_stiffness_head_only_N_m - 1.0 / head_N_m)
        return cls.from_oil_columns(columns, outer_N_m, rod_weight_N, **options)

    @property
    def rod_share(self) -> float:
        """``r = k_r / (k_h + k_r)``: share of a force change carried by the rod side."""
        return self.rod_stiffness_N_m / (self.head_stiffness_N_m + self.rod_stiffness_N_m)

    @property
    def pad_stiffness_head_only_N_m(self) -> float:
        """``k_n = k_h (+) k_out``: moving and FLOOR stiffness (the engine's contact)."""
        return _series(self.head_stiffness_N_m, self.outer_stiffness_N_m)

    @property
    def pad_stiffness_locked_N_m(self) -> float:
        """``k_n' = (k_h + k_r) (+) k_out``: LOCK stiffness."""
        oil_N_m = self.head_stiffness_N_m + self.rod_stiffness_N_m
        return _series(oil_N_m, self.outer_stiffness_N_m)

    @property
    def floor_gauge_Pa(self) -> float:
        return self.cavitation_floor_abs_Pa - ATMOSPHERE_PA

    def knee_force_increment_N(self, rod_pressure_at_lock_Pa: float) -> float:
        """``dF_knee``: load increase from the lock until the rod side reaches the floor."""
        margin_Pa = max(rod_pressure_at_lock_Pa - self.floor_gauge_Pa, 0.0)
        return margin_Pa * self.annulus_area_m2 / self.rod_share

    def retract_threshold_rod_pressure_Pa(self, cylinder_force_N: float) -> float:
        """Rod pressure at the head POC pilot threshold (14.3 lock after RET, 7.4 rule 2)."""
        area_ratio = self.head_area_m2 / self.annulus_area_m2
        inverse_pilot = 1.0 / self.poc_pilot_ratio
        threshold_head_Pa = (
            cylinder_force_N / self.annulus_area_m2
            + self.poc_cracking_Pa
            + self.p_head_back_retract_Pa * (1.0 - inverse_pilot)
        ) / (area_ratio - inverse_pilot)
        head_Pa = max(self.p_head_back_retract_Pa, threshold_head_Pa)
        return (head_Pa * self.head_area_m2 - cylinder_force_N) / self.annulus_area_m2

    def moving_target_rod_pressure_Pa(
        self, direction: RodChamberMode, cylinder_force_N: float
    ) -> float:
        """``p_r*`` of a moving leg (7.4 rules 1-2, meter-in retract)."""
        if direction is RodChamberMode.EXT:
            return max(self.p_rod_back_extend_Pa, -cylinder_force_N / self.annulus_area_m2)
        return min(self.retract_threshold_rod_pressure_Pa(cylinder_force_N), self.relief_Pa)


@dataclass(frozen=True)
class RodChamberOptions:
    """Options shared by all legs (YAML ``actuator.rod_side.*`` proposal, 5.12.7).

    Attributes:
        mechanics: ``off`` reproduces the present L1 bit for bit.
        predictor: Evaluate the returned ``F_x`` at ``delta + ddelta/dt * dt`` (5.12.8 Q-D1).
        lock_pressure_source: Origin of ``p_r0``.
        mode_epsilon_m_s: ``eps`` of the speed sign test.
        poc_close_delay_s: ``t_c`` between ``|u| <= eps`` and the lock (default off, Q-D9).
        rod_pressure_lag_s: ``tau_v`` of the release decay and the moving pressure lag. 0 cuts
            ``F_x`` in one step: the wrong-implementation contrast of 14.5, not a model choice.
    """

    mechanics: RodSideMechanics = RodSideMechanics.ONE_SIDED_PARALLEL
    predictor: bool = True
    lock_pressure_source: LockPressureSource = LockPressureSource.RULE
    mode_epsilon_m_s: float = DEFAULT_MODE_EPSILON_M_S
    poc_close_delay_s: float = 0.0
    rod_pressure_lag_s: float = 0.05

    def __post_init__(self) -> None:
        object.__setattr__(self, "mechanics", RodSideMechanics(self.mechanics))
        source = LockPressureSource(self.lock_pressure_source)
        object.__setattr__(self, "lock_pressure_source", source)
        if min(self.mode_epsilon_m_s, self.poc_close_delay_s, self.rod_pressure_lag_s) < 0.0:
            raise ValueError("mode_epsilon_m_s, poc_close_delay_s, rod_pressure_lag_s >= 0")


@dataclass(frozen=True)
class RodChamberLegInput:
    """Engine signals of one leg at one step.

    Attributes:
        time_s: Simulation time (non-decreasing).
        step_s: Engine step ``dt`` (predictor horizon, moving pressure lag).
        applied_speed_m_s: ``u_applied`` (after the command ramp, as the actuator applies it).
        pad_deflection_m: Pad normal penetration ``delta`` (+ = into the floor).
        pad_deflection_rate_m_s: ``d delta / dt``.
        motor_position_m: ``s_motor``.
        cylinder_force_N: Net cylinder force ``F_cyl`` (motor reaction, + = pushing down).
        oil_temperature_K: For the thermal option; NaN = off.
        rod_pressure_at_lock_Pa: Overrides ``p_r0`` if the leg locks now; NaN = no override.
    """

    time_s: float
    step_s: float
    applied_speed_m_s: float
    pad_deflection_m: float
    pad_deflection_rate_m_s: float
    motor_position_m: float
    cylinder_force_N: float
    oil_temperature_K: float = math.nan
    rod_pressure_at_lock_Pa: float = math.nan


@dataclass(frozen=True)
class RodChamberLegOutput:
    """Outputs of one leg at one step, all from the same state.

    Attributes:
        mode: State at the current deflection.
        extra_force_N: ``F_x`` for the engine (predicted when the predictor is on).
        normal_force_N: Total normal force ``N`` at the current deflection (lift / bushing).
        pad_stiffness_N_m: ``dN/ddelta`` at the current deflection.
        head_pressure_Pa: ``p_h`` (gauge).
        rod_pressure_Pa: ``p_r`` (gauge).
        stroke_true_m: Piston-to-head stroke truth.
        cylinder_force_N: ``F_cyl`` (passed through).
        piston_travel_m: Piston extension change since the lock; NaN while moving.
    """

    mode: RodChamberMode
    extra_force_N: float
    normal_force_N: float
    pad_stiffness_N_m: float
    head_pressure_Pa: float
    rod_pressure_Pa: float
    stroke_true_m: float
    cylinder_force_N: float
    piston_travel_m: float


@dataclass(frozen=True)
class RodChamberStep:
    """:class:`RodChamberLegOutput` fields stacked over the legs (shape ``(n_legs,)``)."""

    mode: NDArray[np.int64]
    extra_force_N: NDArray[np.float64]
    normal_force_N: NDArray[np.float64]
    pad_stiffness_N_m: NDArray[np.float64]
    head_pressure_Pa: NDArray[np.float64]
    rod_pressure_Pa: NDArray[np.float64]
    stroke_true_m: NDArray[np.float64]
    cylinder_force_N: NDArray[np.float64]
    piston_travel_m: NDArray[np.float64]


@dataclass(frozen=True)
class _LockAnchor:
    pad_force_N: float
    deflection_m: float
    rod_pressure_Pa: float
    cylinder_force_N: float
    temperature_K: float


def _series(*stiffnesses_N_m: float) -> float:
    return 1.0 / sum(1.0 / k for k in stiffnesses_N_m)


class RodChamberLeg:
    """State machine, locked law and sensor truth of one leg.

    A fresh leg locks on its first standstill step without the closing delay: "locked after an
    extension at the current force and deflection" (Q-D6, 7.4 step 6).
    """

    def __init__(self, params: RodChamberLegParams, options: RodChamberOptions) -> None:
        self.params = params
        self.options = options
        self.reset()

    def reset(self) -> None:
        """Fresh state (also used when a snapshot has no rod-chamber keys)."""
        self.moving_mode = RodChamberMode.EXT
        self.last_direction = RodChamberMode.EXT
        self.lock_pending_since_s = -math.inf
        self.anchor: _LockAnchor | None = None
        self.release_force_N = 0.0
        self.release_time_s = math.nan
        self.last_extra_force_N = 0.0
        self.tracked_rod_pressure_Pa = self.params.p_rod_locked_after_extend_Pa
        self.time_s = math.nan
        self.deflection_m = 0.0
        self.temperature_K = math.nan

    @property
    def is_locked(self) -> bool:
        return self.anchor is not None

    # --- one step ---

    def step(self, signals: RodChamberLegInput) -> RodChamberLegOutput:
        """Advance to ``signals.time_s`` and return the outputs of the new state."""
        self.time_s = signals.time_s
        self.deflection_m = signals.pad_deflection_m
        self.temperature_K = signals.oil_temperature_K
        self._update_valve_state(signals)
        if not self.is_locked:
            self._relax_tracked_pressure(signals)
        if self.options.mechanics is RodSideMechanics.OFF:
            return self._legacy_output(signals)
        output = self._l1r_output(signals)
        self.last_extra_force_N = output.extra_force_N
        return output

    def _update_valve_state(self, signals: RodChamberLegInput) -> None:
        direction = self._direction_of(signals.applied_speed_m_s)
        if self.is_locked:
            if direction is not None:
                self._release(direction)
            return
        if direction is not None:
            self.moving_mode = direction
            self.last_direction = direction
            self.lock_pending_since_s = math.nan
            return
        if math.isnan(self.lock_pending_since_s):
            self.lock_pending_since_s = signals.time_s
        if signals.time_s - self.lock_pending_since_s >= self.options.poc_close_delay_s:
            self._lock(signals)

    def _direction_of(self, applied_speed_m_s: float) -> RodChamberMode | None:
        epsilon = self.options.mode_epsilon_m_s
        if applied_speed_m_s > epsilon:
            return RodChamberMode.EXT
        if applied_speed_m_s < -epsilon:
            return RodChamberMode.RET
        return None

    def _lock(self, signals: RodChamberLegInput) -> None:
        """Anchor the locked law at the current total normal force (``F_x`` does not step)."""
        deflection_m = self.deflection_m
        extra_force_N = self.extra_force_at(deflection_m)
        pad_force_N = self._head_only_force_N(deflection_m) + extra_force_N
        if pad_force_N <= 0.0:
            # Locked without load: the law starts where head-only force + residual F_x is zero.
            zero_force_m = -extra_force_N / self.params.pad_stiffness_head_only_N_m
            deflection_m = max(deflection_m, zero_force_m, 0.0)
            pad_force_N = 0.0
        self.anchor = _LockAnchor(
            pad_force_N=pad_force_N,
            deflection_m=deflection_m,
            rod_pressure_Pa=self._lock_rod_pressure_Pa(signals),
            cylinder_force_N=signals.cylinder_force_N,
            temperature_K=signals.oil_temperature_K,
        )
        self.release_force_N = 0.0
        self.release_time_s = math.nan
        self.lock_pending_since_s = math.nan

    def _lock_rod_pressure_Pa(self, signals: RodChamberLegInput) -> float:
        params = self.params
        if math.isfinite(signals.rod_pressure_at_lock_Pa):
            pressure_Pa = signals.rod_pressure_at_lock_Pa
        elif self.options.lock_pressure_source is LockPressureSource.TRACKED:
            pressure_Pa = self.tracked_rod_pressure_Pa
        elif self.last_direction is RodChamberMode.RET:
            pressure_Pa = params.retract_threshold_rod_pressure_Pa(signals.cylinder_force_N)
        else:
            pressure_Pa = params.p_rod_locked_after_extend_Pa
        return max(pressure_Pa, params.floor_gauge_Pa)

    def _release(self, direction: RodChamberMode) -> None:
        self.release_force_N = self.extra_force_at(self.deflection_m)
        self.release_time_s = self.time_s
        self.anchor = None
        self.moving_mode = direction
        self.last_direction = direction
        self.lock_pending_since_s = math.nan

    def _relax_tracked_pressure(self, signals: RodChamberLegInput) -> None:
        """7.4 rule 3: exact first-order step towards the moving target."""
        target_Pa = self.params.moving_target_rod_pressure_Pa(
            self.moving_mode, signals.cylinder_force_N
        )
        lag_s = self.options.rod_pressure_lag_s
        keep = math.exp(-signals.step_s / lag_s) if lag_s > 0.0 else 0.0
        self.tracked_rod_pressure_Pa = target_Pa + (self.tracked_rod_pressure_Pa - target_Pa) * keep

    # --- outputs ---

    def _legacy_output(self, signals: RodChamberLegInput) -> RodChamberLegOutput:
        """Present L1 truth (``mechanics = off``): the same expressions as ``chrono/truth.py``."""
        params = self.params
        force_N = signals.cylinder_force_N
        deflection_m = self.deflection_m
        moving = not self.is_locked
        return RodChamberLegOutput(
            mode=self.moving_mode if moving else RodChamberMode.LOCK,
            extra_force_N=0.0,
            normal_force_N=self._head_only_force_N(deflection_m),
            pad_stiffness_N_m=params.pad_stiffness_head_only_N_m if deflection_m > 0.0 else 0.0,
            head_pressure_Pa=force_N / params.head_area_m2,
            rod_pressure_Pa=0.0,
            stroke_true_m=signals.motor_position_m - force_N / params.head_stiffness_N_m,
            cylinder_force_N=force_N,
            piston_travel_m=math.nan,
        )

    def _l1r_output(self, signals: RodChamberLegInput) -> RodChamberLegOutput:
        deflection_m = self.deflection_m
        evaluated_m = deflection_m
        if self.options.predictor:
            evaluated_m = deflection_m + signals.pad_deflection_rate_m_s * signals.step_s
        rod_pressure_Pa = self._rod_pressure_Pa()
        head_pressure_Pa, rod_pressure_Pa = self._pressures_from_identity(
            signals.cylinder_force_N, rod_pressure_Pa
        )
        return RodChamberLegOutput(
            mode=self.mode_at(deflection_m),
            extra_force_N=self.extra_force_at(evaluated_m),
            normal_force_N=self.normal_force_at(deflection_m),
            pad_stiffness_N_m=self.pad_stiffness_at(deflection_m),
            head_pressure_Pa=head_pressure_Pa,
            rod_pressure_Pa=rod_pressure_Pa,
            stroke_true_m=self._stroke_true_m(signals),
            cylinder_force_N=signals.cylinder_force_N,
            piston_travel_m=self._piston_travel_m(),
        )

    def _rod_pressure_Pa(self) -> float:
        anchor = self.anchor
        if anchor is None:
            return self.tracked_rod_pressure_Pa
        params = self.params
        change_Pa = params.rod_share * self._oil_force_change_N(anchor) / params.annulus_area_m2
        pressure_Pa = max(self._anchor_pressure_Pa(anchor) - change_Pa, params.floor_gauge_Pa)
        self.tracked_rod_pressure_Pa = pressure_Pa
        return pressure_Pa

    def _pressures_from_identity(
        self, cylinder_force_N: float, rod_pressure_Pa: float
    ) -> tuple[float, float]:
        """7.4 rule 7: ``p_h`` from the force identity, clipped at the floor."""
        params = self.params
        floor_Pa = params.floor_gauge_Pa
        rod_force_N = rod_pressure_Pa * params.annulus_area_m2
        head_Pa = (cylinder_force_N + rod_force_N) / params.head_area_m2
        if head_Pa >= floor_Pa:
            return head_Pa, rod_pressure_Pa
        rod_Pa = (floor_Pa * params.head_area_m2 - cylinder_force_N) / params.annulus_area_m2
        return floor_Pa, rod_Pa

    def _stroke_true_m(self, signals: RodChamberLegInput) -> float:
        head_N_m = self.params.head_stiffness_N_m
        anchor = self.anchor
        if anchor is None:
            return signals.motor_position_m - signals.cylinder_force_N / head_N_m
        lock_stroke_m = signals.motor_position_m - anchor.cylinder_force_N / head_N_m
        return lock_stroke_m + self._piston_travel_m()

    def _piston_travel_m(self) -> float:
        anchor = self.anchor
        if anchor is None:
            return math.nan
        params = self.params
        both_chambers_N_m = params.head_stiffness_N_m + params.rod_stiffness_N_m
        oil_change_N = self._oil_force_change_N(anchor)
        knee_N = self._knee_force_increment_N(anchor)
        if oil_change_N <= knee_N:
            return -oil_change_N / both_chambers_N_m
        above_knee_N = oil_change_N - knee_N
        return -knee_N / both_chambers_N_m - above_knee_N / params.head_stiffness_N_m

    # --- locked law (pure functions of the deflection) ---

    def _head_only_force_N(self, deflection_m: float) -> float:
        return self.params.pad_stiffness_head_only_N_m * max(deflection_m, 0.0)

    def _anchor_pressure_Pa(self, anchor: _LockAnchor) -> float:
        """``p_r0`` including the optional thermal shift since the lock."""
        warming_K = self.temperature_K - anchor.temperature_K
        if self.params.thermal_rod_pressure_Pa_per_K == 0.0 or not math.isfinite(warming_K):
            return anchor.rod_pressure_Pa
        return anchor.rod_pressure_Pa + self.params.thermal_rod_pressure_Pa_per_K * warming_K

    def _knee_force_increment_N(self, anchor: _LockAnchor) -> float:
        return self.params.knee_force_increment_N(self._anchor_pressure_Pa(anchor))

    def _knee_deflection_m(self, anchor: _LockAnchor) -> float:
        knee_N = self._knee_force_increment_N(anchor)
        return anchor.deflection_m + knee_N / self.params.pad_stiffness_locked_N_m

    def _locked_force_N(self, anchor: _LockAnchor, deflection_m: float) -> float:
        """``Phi(delta)`` (negative: the pad has lifted)."""
        knee_m = self._knee_deflection_m(anchor)
        if deflection_m < knee_m:
            locked_N_m = self.params.pad_stiffness_locked_N_m
            return anchor.pad_force_N + locked_N_m * (deflection_m - anchor.deflection_m)
        knee_force_N = anchor.pad_force_N + self._knee_force_increment_N(anchor)
        head_only_N_m = self.params.pad_stiffness_head_only_N_m
        return knee_force_N + head_only_N_m * (deflection_m - knee_m)

    def _oil_force_change_N(self, anchor: _LockAnchor) -> float:
        """``q``: oil force change since the lock; frozen at ``-F_lock`` once lifted."""
        pad_force_N = max(self._locked_force_N(anchor, self.deflection_m), 0.0)
        return pad_force_N - anchor.pad_force_N

    def _release_decay(self) -> float:
        elapsed_s = self.time_s - self.release_time_s
        lag_s = self.options.rod_pressure_lag_s
        if not math.isfinite(elapsed_s) or lag_s == 0.0:
            return 0.0
        return math.exp(-max(elapsed_s, 0.0) / lag_s)

    def extra_force_at(self, deflection_m: float) -> float:
        """``F_x`` at a deflection with the current anchor / release state (state unchanged)."""
        if self.options.mechanics is RodSideMechanics.OFF:
            return 0.0
        head_only_N = self._head_only_force_N(deflection_m)
        if self.anchor is not None:
            return max(self._locked_force_N(self.anchor, deflection_m), 0.0) - head_only_N
        if deflection_m <= 0.0:
            # No contact: a release residual cannot act on the floor (see the report).
            return 0.0
        return max(self.release_force_N * self._release_decay(), -head_only_N)

    def normal_force_at(self, deflection_m: float) -> float:
        """Total normal force ``N = k_n max(delta, 0) + F_x`` (state unchanged)."""
        return self._head_only_force_N(deflection_m) + self.extra_force_at(deflection_m)

    def mode_at(self, deflection_m: float) -> RodChamberMode:
        anchor = self.anchor
        if anchor is None:
            return self.moving_mode
        if self.options.mechanics is RodSideMechanics.OFF:
            return RodChamberMode.LOCK
        if self._locked_force_N(anchor, deflection_m) <= 0.0:
            return RodChamberMode.LIFT
        if deflection_m >= self._knee_deflection_m(anchor):
            return RodChamberMode.FLOOR
        return RodChamberMode.LOCK

    def pad_stiffness_at(self, deflection_m: float) -> float:
        """``dN/ddelta`` (state unchanged)."""
        mode = self.mode_at(deflection_m)
        if mode is RodChamberMode.LIFT:
            return 0.0
        if mode is RodChamberMode.LOCK and self.options.mechanics is not RodSideMechanics.OFF:
            return self.params.pad_stiffness_locked_N_m
        if mode is RodChamberMode.FLOOR or deflection_m > 0.0:
            return self.params.pad_stiffness_head_only_N_m
        return 0.0

    # --- snapshot ---

    def state_values(self) -> dict[str, float]:
        anchor = self.anchor or _LockAnchor(math.nan, math.nan, math.nan, math.nan, math.nan)
        reported = self.mode_at(self.deflection_m)
        return {
            "l1r_state": float(reported),
            "l1r_delta_lock_m": anchor.deflection_m,
            "l1r_F_lock_N": anchor.pad_force_N,
            "l1r_p_r0_Pa": anchor.rod_pressure_Pa,
            "l1r_Fx_prev_N": self.last_extra_force_N,
            "l1r_release_Fx0_N": self.release_force_N,
            "l1r_release_t_s": self.release_time_s,
            "l1r_F_cyl_lock_N": anchor.cylinder_force_N,
            "l1r_T_lock_K": anchor.temperature_K,
            "l1r_last_direction": float(self.last_direction),
            "l1r_lock_pending_since_s": self.lock_pending_since_s,
            "l1r_p_r_tracked_Pa": self.tracked_rod_pressure_Pa,
            "l1r_t_s": self.time_s,
            "l1r_delta_m": self.deflection_m,
            "l1r_temperature_K": self.temperature_K,
        }

    def restore_values(self, values: Mapping[str, float]) -> None:
        state = RodChamberMode(int(values["l1r_state"]))
        self.anchor = None
        if state in LOCKED_MODES:
            self.anchor = _LockAnchor(
                pad_force_N=values["l1r_F_lock_N"],
                deflection_m=values["l1r_delta_lock_m"],
                rod_pressure_Pa=values["l1r_p_r0_Pa"],
                cylinder_force_N=values["l1r_F_cyl_lock_N"],
                temperature_K=values["l1r_T_lock_K"],
            )
        else:
            self.moving_mode = state
        self.last_direction = RodChamberMode(int(values["l1r_last_direction"]))
        self.lock_pending_since_s = values["l1r_lock_pending_since_s"]
        self.last_extra_force_N = values["l1r_Fx_prev_N"]
        self.release_force_N = values["l1r_release_Fx0_N"]
        self.release_time_s = values["l1r_release_t_s"]
        self.tracked_rod_pressure_Pa = values["l1r_p_r_tracked_Pa"]
        self.time_s = values["l1r_t_s"]
        self.deflection_m = values["l1r_delta_m"]
        self.temperature_K = values["l1r_temperature_K"]


def _per_leg(values: ArrayLike | None, leg_count: int, fill: float) -> NDArray[np.float64]:
    if values is None:
        return np.full(leg_count, fill)
    array = np.asarray(values, dtype=float)
    if array.shape not in ((), (leg_count,)):
        raise ValueError(f"expected shape ({leg_count},) or a scalar, got {array.shape}")
    return np.broadcast_to(array, (leg_count,)).copy()


class RodChamberStateMachine:
    """The independent :class:`RodChamberLeg` objects of all legs, vector interface.

    Call :meth:`step` once per engine step with the leg signals (shape ``(n_legs,)``, scalars
    broadcast), then apply ``extra_force_N`` along the floor normal at each pad.

    Args:
        leg_params: One :class:`RodChamberLegParams` per leg (``LEG_ORDER`` for four legs).
        options: Shared options.
    """

    def __init__(
        self, leg_params: Sequence[RodChamberLegParams], options: RodChamberOptions
    ) -> None:
        if not leg_params:
            raise ValueError("leg_params is empty")
        self.options = options
        self.legs = tuple(RodChamberLeg(params, options) for params in leg_params)
        self.state_defaulted = False
        """True after :meth:`restore_state` without rod-chamber keys (meta, Q-D6)."""

    @property
    def leg_count(self) -> int:
        return len(self.legs)

    def step(
        self,
        *,
        time_s: float,
        step_s: float,
        applied_speed_m_s: ArrayLike,
        pad_deflection_m: ArrayLike,
        pad_deflection_rate_m_s: ArrayLike,
        motor_position_m: ArrayLike,
        cylinder_force_N: ArrayLike,
        oil_temperature_K: ArrayLike | None = None,
        rod_pressure_at_lock_Pa: ArrayLike | None = None,
    ) -> RodChamberStep:
        """Advance every leg one step; the fields follow :class:`RodChamberLegInput`."""
        count = self.leg_count
        columns = {
            "applied_speed_m_s": _per_leg(applied_speed_m_s, count, math.nan),
            "pad_deflection_m": _per_leg(pad_deflection_m, count, math.nan),
            "pad_deflection_rate_m_s": _per_leg(pad_deflection_rate_m_s, count, math.nan),
            "motor_position_m": _per_leg(motor_position_m, count, math.nan),
            "cylinder_force_N": _per_leg(cylinder_force_N, count, math.nan),
            "oil_temperature_K": _per_leg(oil_temperature_K, count, math.nan),
            "rod_pressure_at_lock_Pa": _per_leg(rod_pressure_at_lock_Pa, count, math.nan),
        }
        outputs = []
        for index, leg in enumerate(self.legs):
            leg_values = {name: float(values[index]) for name, values in columns.items()}
            signals = RodChamberLegInput(time_s=time_s, step_s=step_s, **leg_values)
            outputs.append(leg.step(signals))
        return _stack(outputs)

    # --- snapshot (R16, Q-D6) and meta ---

    def state_arrays(self) -> dict[str, NDArray[np.float64]]:
        """State per :data:`STATE_KEYS`, one value per leg (``SnapshotPart`` protocol)."""
        per_leg = [leg.state_values() for leg in self.legs]
        return {key: np.array([values[key] for values in per_leg]) for key in STATE_KEYS}

    def restore_state(self, arrays: Mapping[str, ArrayLike]) -> None:
        """Restore :meth:`state_arrays` output.

        Without any rod-chamber key (an older snapshot) every leg is reset: it locks "after an
        extension, at the current force and deflection" on its next standstill step, and
        :attr:`state_defaulted` is set for the meta (Q-D6). A partial key set is an error.
        """
        present = [key for key in STATE_KEYS if key in arrays]
        if not present:
            for leg in self.legs:
                leg.reset()
            self.state_defaulted = True
            return
        missing = sorted(set(STATE_KEYS) - set(present))
        if missing:
            raise KeyError(f"rod chamber state lacks {missing}")
        columns = {key: _per_leg(arrays[key], self.leg_count, math.nan) for key in STATE_KEYS}
        for index, leg in enumerate(self.legs):
            leg.restore_values({key: float(values[index]) for key, values in columns.items()})
        self.state_defaulted = False

    def to_state(self) -> dict[str, NDArray[np.float64]]:
        """Alias of :meth:`state_arrays`."""
        return self.state_arrays()

    def from_state(self, state: Mapping[str, ArrayLike]) -> None:
        """Alias of :meth:`restore_state`."""
        self.restore_state(state)

    def meta(self) -> dict[str, Any]:
        """Model description with the derived per-leg values (5.12.7 item 6)."""
        options = asdict(self.options)
        for name in ("mechanics", "lock_pressure_source"):
            options[name] = str(options[name])
        legs = []
        for leg in self.legs:
            params = leg.params
            entry: dict[str, Any] = asdict(params)
            entry["rod_share"] = params.rod_share
            entry["pad_stiffness_head_only_N_m"] = params.pad_stiffness_head_only_N_m
            entry["pad_stiffness_locked_N_m"] = params.pad_stiffness_locked_N_m
            entry["knee_after_extend_N"] = params.knee_force_increment_N(
                params.p_rod_locked_after_extend_Pa
            )
            legs.append(entry)
        return {
            "model": "L1-R (dynamics_model.md 5.12.4, rod_side_pressure.md 14), form (i)",
            "l1_rod_chamber_mechanics": str(self.options.mechanics),
            "l1r_state_defaulted": self.state_defaulted,
            "gas_separation": "not_implemented",
            "options": options,
            "legs": legs,
        }


def _stack(outputs: Sequence[RodChamberLegOutput]) -> RodChamberStep:
    def column(name: str) -> NDArray[np.float64]:
        return np.array([getattr(output, name) for output in outputs], dtype=float)

    return RodChamberStep(
        mode=np.array([int(output.mode) for output in outputs], dtype=np.int64),
        extra_force_N=column("extra_force_N"),
        normal_force_N=column("normal_force_N"),
        pad_stiffness_N_m=column("pad_stiffness_N_m"),
        head_pressure_Pa=column("head_pressure_Pa"),
        rod_pressure_Pa=column("rod_pressure_Pa"),
        stroke_true_m=column("stroke_true_m"),
        cylinder_force_N=column("cylinder_force_N"),
        piston_travel_m=column("piston_travel_m"),
    )
