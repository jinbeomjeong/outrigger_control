"""Rod-side (annulus) pressure synthesis for the L1 engine and the two-pressure force helper.

Engine independent part of C2 R6-P (``00_docs/04_control/s6_control_spec.md`` 53.4 P-14,
interface of ``00_docs/02_hydraulic/rod_side_pressure.md`` 7.1 / 7.4). L1 lumps the oil into
the pad contact stiffness and has no rod chamber, so the rod-side pressure is an observation
state built from the true cylinder force ``F_cyl``, the applied leg speed and the true stroke;
the head pressure follows from the force identity

    p_h = (F_cyl + p_r A_ann) / A_p   =>   p_h A_p - p_r A_ann = F_cyl  (to rounding).

Synthesis rules (7.4 table, per leg, every control instant):

* mode: ``u > +eps`` extend, ``u < -eps`` retract, otherwise locked;
* extend target (flow dependent, rod_side_pressure.md 14.7):
  ``p_r* = max(p_T0 + (p_bB - p_T0) (u / v_max)^2, -F / A_ann)``; retract target (meter-in,
  the POC-A pilot threshold) ``p_h* = max(p_bA, (F / A_ann + p_cr + p_bA (1 - 1/psi)) /
  (phi - 1/psi))``, ``p_r* = min((p_h* A_p - F) / A_ann, p_relief)``; while moving ``p_r``
  relaxes to ``p_r*`` with the exact first-order step ``exp(-T / tau_v)``;
* lock entry (also a law-C saturation stop) takes the ``u = 0`` value of the last move's target
  (after an extension ``max(p_T0, -F / A_ann)``, after a retraction the pilot threshold), not
  the lagged pressure: the RULE ``p_r0`` of the L1-R machine. It fixes the rod oil mass
  ``m_r = V_r exp(p_r / beta)`` (no free air) at ``x_lock``; locked
  ``V_r = A_ann (L_r - k_h / (k_h + k_r) (x - x_lock))``, ``p_r = beta ln(m_r / V_r)``
  (gauge), floor 0.1 bar abs;
* the head pressure is clipped at the same floor and ``p_r`` re-solved from the identity.

Free air (``air_fraction_at_1bar`` > 0) and the thermal option are not implemented
(``ValueError``); they belong to the L2 state equation (L2 spec 3.1). Pressures are gauge (Pa).
Per-leg arrays follow ``LEG_ORDER``.

L1-R (user decision 2026-10-22, rod_side_pressure.md 14): the rod chamber becomes a one-sided
nonlinear spring of the L1 plant with the states EXT / RET / LOCK / FLOOR / LIFT. The virtual
sensor must then read that machine's state, not a separate synthesis. Both sources share the
:class:`RodPressureSource` protocol. The machine is
``outrigger_sim.hydraulics.rod_chamber`` (``RodChamberLegParams`` per leg,
``RodChamberStateMachine.step(time_s=, step_s=, applied_speed_m_s=, pad_deflection_m=,
pad_deflection_rate_m_s=, motor_position_m=, cylinder_force_N=, ...) -> RodChamberStep``,
``state_arrays`` / ``restore_state`` with the ``l1r_*`` keys, ``meta``);
:class:`RodChamberSensorSource` wraps it so that the sensor reads the pressures of the
machine's last engine step instead of a second synthesis.

Three pressure paths (rod_side_pressure.md 7.4 table, :data:`PRESSURE_MODELS`) for the engine,
built with :func:`build_rod_pressure_source`:

* ``net_equivalent`` (legacy): no source, ``p_h = F_cyl / A_p``, no rod-side pressure;
* ``two_chamber_synth``: :class:`RodSideSynth` (7.4 rules, control instants);
* ``l1r_state_machine``: :class:`RodChamberSensorSource` over the engine's L1-R machine.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum
from typing import Any, Protocol

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import Params
from outrigger_sim.signals import LEG_COUNT

ATMOSPHERE_PA = 1.01325e5
MODE_EPSILON_M_S = 1e-6
"""7.4 step 0: a leg moves when ``|u_applied|`` exceeds this."""


class RetractRegime(StrEnum):
    """Rod-side pressure while retracting (rod_side_pressure.md 2, Q-R3)."""

    METER_IN = "meter_in"
    """At the POC-A pilot threshold (lower bound, default)."""
    METER_OUT = "meter_out"
    """At a fixed meter-out pressure ``p_rod_meter_out_Pa`` (sensitivity)."""


class LegMode(IntEnum):
    LOCKED = 0
    EXTEND = 1
    RETRACT = 2


@dataclass(frozen=True)
class RodSideParams:
    """Rod-side model parameters (rod_side_pressure.md 7.3, all ASSUMPTION)."""

    rod_dead_length_m: float = 0.05
    p_rod_tank_Pa: float = 2e5
    """``p_T0``: rod side of a leg standing after an extension (14.7: 2 bar, sensitivity
    0.5-3 bar); the extend target at ``u = 0``."""
    max_speed_m_s: float = 0.0226666667
    """``v_max`` of the flow-dependent extend target; this default is the 0.68 m YAML value
    for runs without a YAML, :meth:`from_params` takes ``actuator.max_speed_m_s``."""
    p_rod_back_extend_Pa: float = 5e5
    """``p_bB``: the extend target at ``v_max``."""
    p_head_back_retract_Pa: float = 5e5
    poc_pilot_ratio: float = 3.5
    poc_cracking_Pa: float = 3e5
    retract_regime: RetractRegime = RetractRegime.METER_IN
    p_rod_meter_out_Pa: float = 100e5
    rod_pressure_lag_s: float = 0.05
    p_rod_locked_initial_Pa: float = 2e5
    air_fraction_at_1bar: float = 0.0
    cavitation_floor_abs_Pa: float = 0.1e5
    relief_Pa: float = 210e5
    oil_bulk_modulus_Pa: float = 1.0e9

    def __post_init__(self) -> None:
        object.__setattr__(self, "retract_regime", RetractRegime(self.retract_regime))
        if self.air_fraction_at_1bar != 0.0:
            raise ValueError("air_fraction_at_1bar > 0 is not implemented (L2 spec 3.1)")
        if not (self.poc_pilot_ratio > 0.0 and self.rod_pressure_lag_s > 0.0):
            raise ValueError("poc_pilot_ratio and rod_pressure_lag_s must be > 0")

    @property
    def floor_gauge_Pa(self) -> float:
        return self.cavitation_floor_abs_Pa - ATMOSPHERE_PA

    @classmethod
    def from_params(cls, params: Params, **overrides: Any) -> RodSideParams:
        """Defaults with the YAML ``actuator.max_speed_m_s`` and
        ``actuator.oil_bulk_modulus_eff_Pa`` (the field defaults are the 0.68 m YAML values,
        for runs without a YAML); ``overrides`` replace single fields."""
        fields: dict[str, Any] = {
            "max_speed_m_s": float(params.actuator.max_speed_m_s),
            "oil_bulk_modulus_Pa": float(params.get("actuator.oil_bulk_modulus_eff_Pa")),
        }
        fields.update(overrides)
        return cls(**fields)


class RodPressureSource(Protocol):
    """Where the virtual two-pressure sensor takes its true pressures from (per control step)."""

    def update(
        self, cylinder_force_N: ArrayLike, applied_speed_m_s: ArrayLike, stroke_true_m: ArrayLike
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """(head pressure, rod-side pressure) per leg, gauge Pa, with ``p_h A_p - p_r A_ann``
        equal to ``F_cyl``."""
        ...

    def state_arrays(self) -> dict[str, NDArray[np.float64]]: ...

    def restore_state(self, arrays: dict[str, ArrayLike]) -> None: ...

    def meta(self) -> dict[str, Any]: ...


class RodSideSynth:
    """Rod-side and head pressures of the four L1 legs (rod_side_pressure.md 7.4).

    Args:
        params: Model parameters.
        head_area_m2: ``A_p`` per leg (4,) or one value.
        annulus_area_m2: ``A_ann`` per leg (4,) or one value.
        stroke_max_m: Stroke (rod chamber length ``L_r = s_max - e + L_0r``).
        head_dead_length_m: ``L_0`` of the head column (``k_h = beta A_p / (L_0 + e)``).
        period_s: Update period (the control period).
    """

    def __init__(
        self,
        params: RodSideParams,
        head_area_m2: ArrayLike,
        annulus_area_m2: ArrayLike,
        stroke_max_m: float,
        head_dead_length_m: float,
        period_s: float,
    ) -> None:
        self.params = params
        self.head_area_m2 = np.broadcast_to(np.asarray(head_area_m2, float), LEG_COUNT).copy()
        self.annulus_area_m2 = np.broadcast_to(
            np.asarray(annulus_area_m2, float), LEG_COUNT
        ).copy()
        self.stroke_max_m = float(stroke_max_m)
        self.head_dead_length_m = float(head_dead_length_m)
        self.period_s = float(period_s)
        self.reset()

    def reset(self) -> None:
        """Start state 'locked after an extension' (7.4 step 6)."""
        self.mode = np.full(LEG_COUNT, LegMode.LOCKED, dtype=int)
        self.rod_pressure_Pa = np.full(LEG_COUNT, self.params.p_rod_locked_initial_Pa)
        self.rod_oil_mass = np.full(LEG_COUNT, math.nan)
        """``m_r`` as the rod volume at 0 bar g (m^3); NaN = not locked yet."""
        self.lock_stroke_m = np.full(LEG_COUNT, math.nan)
        self._last_force_N = np.full(LEG_COUNT, math.nan)

    @property
    def lock_pressure_Pa(self) -> NDArray[np.float64]:
        """``p_r`` a lock would take now: the ``u = 0`` target of the moving legs, the locked
        pressure of the others (the TRACKED hand-over to the L1-R machine)."""
        moving = self.mode != LegMode.LOCKED
        target = self.moving_target_Pa(self._last_force_N, self.mode)
        return np.where(moving, target, self.rod_pressure_Pa)

    # --- pieces ---

    def rod_chamber_length_m(self, stroke_m: NDArray[np.float64]) -> NDArray[np.float64]:
        return self.stroke_max_m - stroke_m + self.params.rod_dead_length_m

    def _rod_share_of_motion(self, stroke_m: NDArray[np.float64]) -> NDArray[np.float64]:
        """``k_h / (k_h + k_r)``: share of the L1 stroke change that the two chambers see."""
        beta = self.params.oil_bulk_modulus_Pa
        k_head = beta * self.head_area_m2 / (self.head_dead_length_m + stroke_m)
        k_rod = beta * self.annulus_area_m2 / self.rod_chamber_length_m(stroke_m)
        return k_head / (k_head + k_rod)

    def moving_target_Pa(
        self, force_N: NDArray[np.float64], mode: NDArray, speed_m_s: ArrayLike = 0.0
    ) -> NDArray:
        """``p_r*`` of the moving legs (7.4 steps 1-2, 14.7); locked legs get NaN.

        ``speed_m_s`` = 0 gives the lock value of each mode (the RULE ``p_r0``).
        """
        p = self.params
        flow_share = (np.asarray(speed_m_s, dtype=float) / p.max_speed_m_s) ** 2
        back_pressure = p.p_rod_tank_Pa + (p.p_rod_back_extend_Pa - p.p_rod_tank_Pa) * flow_share
        extend = np.maximum(back_pressure, -force_N / self.annulus_area_m2)
        if p.retract_regime is RetractRegime.METER_OUT:
            retract = np.full(LEG_COUNT, p.p_rod_meter_out_Pa)
        else:
            ratio = self.head_area_m2 / self.annulus_area_m2
            inverse_pilot = 1.0 / p.poc_pilot_ratio
            head = np.maximum(
                p.p_head_back_retract_Pa,
                (force_N / self.annulus_area_m2 + p.poc_cracking_Pa
                 + p.p_head_back_retract_Pa * (1.0 - inverse_pilot)) / (ratio - inverse_pilot),
            )
            retract = np.minimum((head * self.head_area_m2 - force_N) / self.annulus_area_m2,
                                 p.relief_Pa)
        return np.where(mode == LegMode.EXTEND, extend,
                        np.where(mode == LegMode.RETRACT, retract, math.nan))

    def _lock(self, legs: NDArray[np.bool_], stroke_m: NDArray[np.float64]) -> None:
        volume = self.annulus_area_m2 * self.rod_chamber_length_m(stroke_m)
        mass = volume * np.exp(self.rod_pressure_Pa / self.params.oil_bulk_modulus_Pa)
        self.rod_oil_mass = np.where(legs, mass, self.rod_oil_mass)
        self.lock_stroke_m = np.where(legs, stroke_m, self.lock_stroke_m)

    # --- update ---

    def update(
        self, cylinder_force_N: ArrayLike, applied_speed_m_s: ArrayLike, stroke_true_m: ArrayLike
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """One control instant: (head pressure, rod-side pressure) per leg, gauge Pa."""
        force = np.asarray(cylinder_force_N, dtype=float)
        speed = np.asarray(applied_speed_m_s, dtype=float)
        stroke = np.asarray(stroke_true_m, dtype=float)
        mode = np.where(speed > MODE_EPSILON_M_S, LegMode.EXTEND,
                        np.where(speed < -MODE_EPSILON_M_S, LegMode.RETRACT, LegMode.LOCKED))
        moving = mode != LegMode.LOCKED
        target = self.moving_target_Pa(force, mode, speed)
        decay = math.exp(-self.period_s / self.params.rod_pressure_lag_s)
        relaxed = target + (self.rod_pressure_Pa - target) * decay
        self.rod_pressure_Pa = np.where(moving, relaxed, self.rod_pressure_Pa)
        was_moving = self.mode != LegMode.LOCKED
        entering_lock = ~moving & (was_moving | np.isnan(self.rod_oil_mass))
        # 14.7: the lock takes the u = 0 value of the last move's target, not the lag.
        lock_value = self.moving_target_Pa(force, self.mode)
        self.rod_pressure_Pa = np.where(~moving & was_moving, lock_value, self.rod_pressure_Pa)
        self._lock(entering_lock, stroke)
        self._last_force_N = force.copy()
        self.mode = mode
        locked = ~moving
        travel = self._rod_share_of_motion(self.lock_stroke_m) * (stroke - self.lock_stroke_m)
        volume = self.annulus_area_m2 * (self.rod_chamber_length_m(self.lock_stroke_m) - travel)
        with np.errstate(invalid="ignore", divide="ignore"):
            locked_pressure = self.params.oil_bulk_modulus_Pa * np.log(self.rod_oil_mass / volume)
        floor = self.params.floor_gauge_Pa
        self.rod_pressure_Pa = np.where(
            locked, np.maximum(locked_pressure, floor), self.rod_pressure_Pa
        )
        return self._head_from_identity(force)

    def _head_from_identity(
        self, force_N: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """7.4 step 7: ``p_h`` from the force identity, clipped at the floor."""
        floor = self.params.floor_gauge_Pa
        head = (force_N + self.rod_pressure_Pa * self.annulus_area_m2) / self.head_area_m2
        clipped = head < floor
        head = np.where(clipped, floor, head)
        rod = np.where(
            clipped, (head * self.head_area_m2 - force_N) / self.annulus_area_m2,
            self.rod_pressure_Pa,
        )
        self.rod_pressure_Pa = rod
        return head, rod.copy()

    # --- snapshot (R16) and meta ---

    def state_arrays(self) -> dict[str, NDArray[np.float64]]:
        return {"mode": self.mode.astype(float), "rod_pressure_Pa": self.rod_pressure_Pa.copy(),
                "rod_oil_mass_m3": self.rod_oil_mass.copy(),
                "lock_stroke_m": self.lock_stroke_m.copy()}

    def restore_state(self, arrays: dict[str, ArrayLike]) -> None:
        self.mode = np.asarray(arrays["mode"], dtype=int).copy()
        self.rod_pressure_Pa = np.asarray(arrays["rod_pressure_Pa"], dtype=float).copy()
        self.rod_oil_mass = np.asarray(arrays["rod_oil_mass_m3"], dtype=float).copy()
        self.lock_stroke_m = np.asarray(arrays["lock_stroke_m"], dtype=float).copy()

    def meta(self) -> dict[str, Any]:
        params = asdict(self.params)
        params["retract_regime"] = str(self.params.retract_regime)
        return {"model": "rod_side_pressure.md 7.4 synthesis", "params": params,
                "head_area_m2": self.head_area_m2.tolist(),
                "annulus_area_m2": self.annulus_area_m2.tolist(),
                "stroke_max_m": self.stroke_max_m,
                "head_dead_length_m": self.head_dead_length_m}


class ForceEstimate(StrEnum):
    """How a cylinder force is read from the pressures (P-2, U43)."""

    TWO_SENSOR = "two_sensor"
    """``p_h A_p - p_r A_ann`` (R6 default)."""
    HEAD_ONLY = "head_only"
    """``p_h A_p`` (R5)."""


def cylinder_force_from_pressures(
    head_pressure_Pa: ArrayLike,
    rod_pressure_Pa: ArrayLike | None,
    head_area_m2: ArrayLike,
    annulus_area_m2: ArrayLike,
    mode: ForceEstimate | str = ForceEstimate.TWO_SENSOR,
) -> tuple[NDArray[np.float64], ForceEstimate]:
    """Cylinder force per leg and the estimate actually used.

    Without a rod-side pressure the two-sensor request falls back to ``head_only``; the
    returned mode says so (for the meta). The head-only force is ``p_h * A_p`` exactly as R5.
    """
    head_force = np.asarray(head_pressure_Pa, dtype=float) * np.asarray(head_area_m2, float)
    if ForceEstimate(mode) is ForceEstimate.HEAD_ONLY or rod_pressure_Pa is None:
        return head_force, ForceEstimate.HEAD_ONLY
    rod_force = np.asarray(rod_pressure_Pa, dtype=float) * np.asarray(annulus_area_m2, float)
    return head_force - rod_force, ForceEstimate.TWO_SENSOR


class RodChamberSensorSource:
    """The virtual two-pressure sensor of an L1-R plant: the pressures of the machine's state.

    The engine advances the machine every engine step through :meth:`step` (a pass-through of
    ``RodChamberStateMachine.step`` that keeps the result); at a control instant
    :meth:`update` returns the head and rod-side pressures of that latest step and computes
    nothing, so the sensor and the plant force come from one state.

    TRACKED ``p_r0``: with ``lock_pressure_synth`` the 7.4 synthesis runs at the control
    instants (in :meth:`update`) and its u = 0 lock value (14.7) is handed to the machine as
    ``rod_pressure_at_lock_Pa`` on the following engine steps (only when the machine's
    ``lock_pressure_source`` is ``tracked``; the default value of ``p_r0`` stays a setting of
    hydraulics / dynamics).

    Args:
        machine: The engine's ``RodChamberStateMachine``.
        lock_pressure_synth: Optional :class:`RodSideSynth` for the TRACKED ``p_r0``.
    """

    def __init__(self, machine, lock_pressure_synth: RodSideSynth | None = None) -> None:
        self.machine = machine
        self.lock_pressure_synth = lock_pressure_synth
        self.last_step = None
        """``RodChamberStep`` of the latest engine step (``None`` before the first)."""

    def _passes_synth_pressure(self) -> bool:
        from outrigger_sim.hydraulics.rod_chamber import LockPressureSource

        is_tracked = self.machine.options.lock_pressure_source is LockPressureSource.TRACKED
        return is_tracked and self.lock_pressure_synth is not None

    def step(self, **engine_signals: Any):
        """One engine step of the machine (keyword arguments of its ``step``); kept."""
        if self._passes_synth_pressure() and "rod_pressure_at_lock_Pa" not in engine_signals:
            engine_signals["rod_pressure_at_lock_Pa"] = self.lock_pressure_synth.lock_pressure_Pa
        self.last_step = self.machine.step(**engine_signals)
        return self.last_step

    def update(
        self, cylinder_force_N: ArrayLike, applied_speed_m_s: ArrayLike, stroke_true_m: ArrayLike
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """(head, rod-side) pressures of the latest machine step (gauge Pa)."""
        if self.last_step is None:
            raise RuntimeError("RodChamberSensorSource.update before the first machine step")
        if self.lock_pressure_synth is not None:
            self.lock_pressure_synth.update(cylinder_force_N, applied_speed_m_s, stroke_true_m)
        step = self.last_step
        return np.array(step.head_pressure_Pa, dtype=float), np.array(
            step.rod_pressure_Pa, dtype=float
        )

    def state_arrays(self) -> dict[str, NDArray[np.float64]]:
        """The machine's ``l1r_*`` state (R16)."""
        return self.machine.state_arrays()

    def restore_state(self, arrays: dict[str, ArrayLike]) -> None:
        self.machine.restore_state(arrays)
        self.last_step = None

    def meta(self) -> dict[str, Any]:
        meta = dict(self.machine.meta())
        meta["sensor_source"] = "l1r_state_machine (last engine step)"
        meta["lock_pressure_from_synth"] = self._passes_synth_pressure()
        return meta


class PressureModel(StrEnum):
    """Engine pressure model of the virtual sensors (``pressure_model`` setting, 7.4)."""

    NET_EQUIVALENT = "net_equivalent"
    TWO_CHAMBER_SYNTH = "two_chamber_synth"
    L1R_STATE_MACHINE = "l1r_state_machine"


PRESSURE_MODELS = tuple(str(model) for model in PressureModel)


def build_rod_pressure_source(
    pressure_model: PressureModel | str,
    *,
    head_area_m2: ArrayLike,
    annulus_area_m2: ArrayLike,
    stroke_max_m: float,
    head_dead_length_m: float,
    period_s: float,
    synth_params: RodSideParams | None = None,
    machine=None,
    lock_pressure_from_synth: bool = False,
) -> RodPressureSource | None:
    """Engine-independent entry point of the three pressure paths.

    Args:
        pressure_model: ``net_equivalent`` (returns ``None``: keep ``p_h = F / A_p``, no rod
            side), ``two_chamber_synth`` or ``l1r_state_machine``.
        head_area_m2, annulus_area_m2: Per-leg areas (or one value).
        stroke_max_m, head_dead_length_m, period_s: Synthesis geometry and control period.
        synth_params: 7.4 parameters (default :class:`RodSideParams`).
        machine: The engine's ``RodChamberStateMachine`` (required for ``l1r_state_machine``).
        lock_pressure_from_synth: ``l1r_state_machine`` with a TRACKED ``p_r0``: also run the
            synthesis and pass its pressure at the lock.
    """
    model = PressureModel(pressure_model)
    if model is PressureModel.NET_EQUIVALENT:
        return None

    def synth() -> RodSideSynth:
        return RodSideSynth(synth_params or RodSideParams(), head_area_m2, annulus_area_m2,
                            stroke_max_m, head_dead_length_m, period_s)

    if model is PressureModel.TWO_CHAMBER_SYNTH:
        return synth()
    if machine is None:
        raise ValueError("l1r_state_machine needs the engine's RodChamberStateMachine")
    return RodChamberSensorSource(machine, synth() if lock_pressure_from_synth else None)
