"""Signal types at the engine / controller boundary and the Record schema (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` 3.2-3.3:

* :class:`Command` - controller -> engine: four leg speeds (m/s). Saturation, stroke ends
  and the 210 bar cut-off are the actuator model's job, so any finite value is accepted.
* :class:`Measurements` - engine -> controller, every control period (20 ms, assumed):
  IMU specific force and angular rate in sensor axes, cylinder head pressures, strokes.
  Error models (noise, bias, delay) belong to ``sensors``; this type only carries values.
* :class:`TruthState` - the true simulation state for recording and verification. The
  controller must never read it (the runner enforces this); it deliberately shares no base
  class and no field names with :class:`Measurements` so the two cannot be swapped silently.
* :data:`RECORD_FIELDS` - the fixed-name arrays of a Record (plan 3.2), with per-sample
  shape and unit. Saving to npz is the ``record`` module's job.

Per-leg arrays follow :data:`outrigger_sim.params.LEG_ORDER` (FL, FR, RL, RR = 0-3).

Immutability: the dataclasses are frozen, and every array field is copied on construction
into a float64 (or bool) array whose ``writeable`` flag is cleared. Mutating the caller's
original array afterwards does not change the instance, and ``instance.field[0] = x``
raises ``ValueError``. Instances compare by identity (``eq=False``) because ``==`` on numpy
arrays is element-wise.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER

LEG_COUNT = len(LEG_ORDER)

# Control period (s): the controller runs and the sensors are sampled every 20 ms (CLAUDE.md
# '미정 사항': control period 20 ms assumed). Shared by ``sensors`` and ``control``.
DEFAULT_CONTROL_PERIOD_S = 0.02

# Record names of the energy terms share this prefix (plan 3.2 'energy.*').
ENERGY_FIELD_PREFIX = "energy."


class InvalidSignalError(ValueError):
    """A signal field has the wrong shape, dtype or a non-finite value."""

    def __init__(self, field_name: str, problem: str) -> None:
        super().__init__(f"{field_name}: {problem}")
        self.field_name = field_name


# --- array helpers -----------------------------------------------------------------------


def _frozen_array(
    value: ArrayLike,
    shape: tuple[int, ...],
    field_name: str,
    *,
    allow_nan: bool = False,
) -> NDArray[np.float64]:
    """Copy ``value`` into a read-only float64 array of exactly ``shape``."""
    try:
        array = np.array(value, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as error:
        raise InvalidSignalError(field_name, f"not numeric: {error}") from None
    if array.shape != shape:
        raise InvalidSignalError(field_name, f"expected shape {shape}, got {array.shape}")
    if np.any(np.isinf(array)) or (not allow_nan and np.any(np.isnan(array))):
        raise InvalidSignalError(field_name, "contains NaN or infinity")
    array.setflags(write=False)
    return array


def _frozen_flags(value: ArrayLike, shape: tuple[int, ...], field_name: str) -> NDArray[np.bool_]:
    array = np.array(value, copy=True)
    if array.dtype != np.bool_:
        raise InvalidSignalError(field_name, f"expected bool values, got dtype {array.dtype}")
    if array.shape != shape:
        raise InvalidSignalError(field_name, f"expected shape {shape}, got {array.shape}")
    array.setflags(write=False)
    return array


def _finite_time(value: float, field_name: str = "t_s") -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | np.floating):
        raise InvalidSignalError(field_name, f"expected a number, got {value!r}")
    time_s = float(value)
    if not math.isfinite(time_s):
        raise InvalidSignalError(field_name, f"not finite: {value!r}")
    return time_s


def _freeze_fields(instance: object, shapes: Mapping[str, tuple[int, ...]]) -> None:
    """Validate ``t_s`` and replace each float array field listed in ``shapes``."""
    object.__setattr__(instance, "t_s", _finite_time(instance.t_s))  # type: ignore[attr-defined]
    for name, shape in shapes.items():
        frozen = _frozen_array(getattr(instance, name), shape, name)
        object.__setattr__(instance, name, frozen)


# --- boundary types ----------------------------------------------------------------------


@dataclass(frozen=True, eq=False)
class Command:
    """Controller -> engine command, held constant until the next one (zero-order hold).

    Attributes:
        t_s: Simulation time at which the controller issued the command (s).
        leg_speed_m_s: Commanded extension speed per leg (m/s), shape (4,), LEG_ORDER.
            Positive extends the leg (pushes the pad down, body -z).
    """

    t_s: float
    leg_speed_m_s: NDArray[np.float64]

    def __post_init__(self) -> None:
        _freeze_fields(self, {"leg_speed_m_s": (LEG_COUNT,)})

    @classmethod
    def stopped(cls, t_s: float) -> Command:
        """Zero speed on every leg (legs held by the lock valves), issued at ``t_s``."""
        return cls(t_s=t_s, leg_speed_m_s=np.zeros(LEG_COUNT))


@dataclass(frozen=True, eq=False)
class Measurements:
    """Engine -> controller sensor values at one control step (after the sensor models).

    Attributes:
        t_s: Simulation time of the sample (s).
        specific_force_m_s2: IMU specific force ``R^T (a - g)`` in sensor axes (m/s^2),
            shape (3,); about ``(0, 0, +9.81)`` for a level body at rest.
        angular_rate_rad_s: IMU angular rate in sensor axes (rad/s), shape (3,).
        head_pressure_Pa: Cylinder head-side pressure per leg (Pa), shape (4,). The sensor
            sits in the lock valve block and keeps reading the trapped pressure while locked.
        stroke_m: Measured leg extension per leg (m), shape (4,); 0 = fully retracted.
            In L1 this is the motor position (plan 3.3).
        stroke_corrected_m: Stroke corrected for the oil-column compression,
            ``motor position - F_cyl / k_oil(e)`` (m), shape (4,), or ``None`` if the engine
            does not provide it. L1 gives both strokes because they differ by about 5 mm
            (plan S6 risk 3). Optional so that engines written before this field keep working.
        rod_pressure_Pa: Rod-side (annulus) pressure per leg (Pa), shape (4,), or ``None``
            without a rod-side sensor (C2 R6-P, spec 51.1 P-1). The sensor sits on the chamber
            side of the pilot check (U52). NaN marks a dropped-out reading (the controller's
            D1 diagnosis sees it); infinity is rejected. With ``None`` the head reading of the
            legacy engine is the net-force equivalent ``F_cyl / A_p`` (spec 47.1).
        oil_temperature_C: Hydraulic oil temperature (deg C) when the machine has an oil
            temperature signal (U73, manufacturer to confirm), else ``None``. Used only by
            the C2 re-calibration warning (E-5).
        imu_specific_force_samples_m_s2: IMU-rate specific force samples of the control
            period, shape (n, 3), oldest first, the last one ending at ``t_s``; each is the
            mean over one IMU sample interval (10 ms at 100 Hz). ``None`` when the engine
            delivers only the period mean ``specific_force_m_s2``. The C2 R8 preset filters
            the attitude at the IMU rate on these samples (``s6_control_spec.md`` 139 P-3).
    """

    t_s: float
    specific_force_m_s2: NDArray[np.float64]
    angular_rate_rad_s: NDArray[np.float64]
    head_pressure_Pa: NDArray[np.float64]
    stroke_m: NDArray[np.float64]
    stroke_corrected_m: NDArray[np.float64] | None = None
    rod_pressure_Pa: NDArray[np.float64] | None = None
    oil_temperature_C: float | None = None
    imu_specific_force_samples_m_s2: NDArray[np.float64] | None = None

    def __post_init__(self) -> None:
        _freeze_fields(
            self,
            {
                "specific_force_m_s2": (3,),
                "angular_rate_rad_s": (3,),
                "head_pressure_Pa": (LEG_COUNT,),
                "stroke_m": (LEG_COUNT,),
            },
        )
        if self.stroke_corrected_m is not None:
            corrected = _frozen_array(self.stroke_corrected_m, (LEG_COUNT,), "stroke_corrected_m")
            object.__setattr__(self, "stroke_corrected_m", corrected)
        if self.rod_pressure_Pa is not None:
            rod = _frozen_array(
                self.rod_pressure_Pa, (LEG_COUNT,), "rod_pressure_Pa", allow_nan=True
            )
            object.__setattr__(self, "rod_pressure_Pa", rod)
        if self.imu_specific_force_samples_m_s2 is not None:
            self._freeze_imu_samples()

    def _freeze_imu_samples(self) -> None:
        name = "imu_specific_force_samples_m_s2"
        sample_count = np.shape(self.imu_specific_force_samples_m_s2)[0]
        if sample_count < 1:
            raise InvalidSignalError(name, "needs at least one sample")
        samples = _frozen_array(self.imu_specific_force_samples_m_s2, (sample_count, 3), name)
        object.__setattr__(self, name, samples)


@dataclass(frozen=True, eq=False)
class TruthState:
    """True simulation state at one instant; for recording and verification only.

    Positions and velocities are in the world frame (equal to the body axes when the body
    is level). The body reference point is the body-frame origin
    (:data:`outrigger_sim.frames.BODY_ORIGIN_IN_CAD_MM`).

    Attributes:
        t_s: Simulation time (s).
        body_pos_m: Body-frame origin in world coordinates (m), shape (3,).
        body_quat_wxyz: Body orientation, world <- body, wxyz, shape (4,).
        body_vel_m_s: Velocity of the body-frame origin, world frame (m/s), shape (3,).
        body_omega_rad_s: Body angular velocity, world frame (rad/s), shape (3,).
        s_motor_m: Leg motor position = extension (m), shape (4,).
        s_ref_m: Actuator reference extension (m), shape (4,); the integrated command
            (L2b force law), equal to ``s_motor_m`` for the L1 position motor.
        u_applied_m_s: Leg speed actually applied after saturation (m/s), shape (4,).
        F_cyl_N: Cylinder force = head pressure x head area (N), shape (4,); positive
            pushes the pad down. The F_min rule uses this value.
        F_contact_n_N: Ground normal force on each pad (N), shape (4,); up positive.
        F_contact_t_N: Ground tangential force on each pad, world x and y (N), shape (4, 2).
        is_pad_in_contact: Whether each pad touches the ground, shape (4,), bool.
        F_crawler_N: Total ground force on the crawler, world frame (N), shape (3,).
        bushing_anchor_m: Ground anchor of each pad's ground bushing, world frame (m),
            shape (4, 3); NaN rows for legs without an active bushing (lifted, or a model
            without ground bushings).
        stroke_true_m: Actual stroke = rod displacement relative to the cylinder (m),
            shape (4,), or ``None`` if the engine does not provide it. Kept apart from
            ``s_motor_m`` because the two differ (about 5 mm in L1, where the oil and
            contact compliance sit outside the motor; user decision 2026-10-20). Optional
            only so that engines written before this field keep working.
    """

    t_s: float
    body_pos_m: NDArray[np.float64]
    body_quat_wxyz: NDArray[np.float64]
    body_vel_m_s: NDArray[np.float64]
    body_omega_rad_s: NDArray[np.float64]
    s_motor_m: NDArray[np.float64]
    s_ref_m: NDArray[np.float64]
    u_applied_m_s: NDArray[np.float64]
    F_cyl_N: NDArray[np.float64]
    F_contact_n_N: NDArray[np.float64]
    F_contact_t_N: NDArray[np.float64]
    is_pad_in_contact: NDArray[np.bool_]
    F_crawler_N: NDArray[np.float64]
    bushing_anchor_m: NDArray[np.float64]
    stroke_true_m: NDArray[np.float64] | None = None

    def __post_init__(self) -> None:
        _freeze_fields(
            self,
            {
                "body_pos_m": (3,),
                "body_quat_wxyz": (4,),
                "body_vel_m_s": (3,),
                "body_omega_rad_s": (3,),
                "s_motor_m": (LEG_COUNT,),
                "s_ref_m": (LEG_COUNT,),
                "u_applied_m_s": (LEG_COUNT,),
                "F_cyl_N": (LEG_COUNT,),
                "F_contact_n_N": (LEG_COUNT,),
                "F_contact_t_N": (LEG_COUNT, 2),
                "F_crawler_N": (3,),
            },
        )
        contact_flags = _frozen_flags(self.is_pad_in_contact, (LEG_COUNT,), "is_pad_in_contact")
        object.__setattr__(self, "is_pad_in_contact", contact_flags)
        anchors = _frozen_array(
            self.bushing_anchor_m, (LEG_COUNT, 3), "bushing_anchor_m", allow_nan=True
        )
        object.__setattr__(self, "bushing_anchor_m", anchors)
        if self.stroke_true_m is not None:
            stroke_true = _frozen_array(self.stroke_true_m, (LEG_COUNT,), "stroke_true_m")
            object.__setattr__(self, "stroke_true_m", stroke_true)
        if np.linalg.norm(self.body_quat_wxyz) == 0.0:
            raise InvalidSignalError("body_quat_wxyz", "zero quaternion")


# --- Record schema -----------------------------------------------------------------------


@dataclass(frozen=True)
class RecordField:
    """One fixed-name Record array: ``n_samples`` rows of ``sample_shape``.

    Attributes:
        name: Array name in the Record (plan 3.2), for example ``"F_contact_t"``.
        sample_shape: Shape of one sample; the stored array is ``(n, *sample_shape)``.
        unit: SI unit, ``"1"`` for dimensionless, ``"bool"`` for flags.
        source: Where the runner takes it from, ``"<TypeName>.<attribute>"``.
        is_optional: Absent from Records of models or stages that do not produce it.
    """

    name: str
    sample_shape: tuple[int, ...]
    unit: str
    source: str
    is_optional: bool = False

    @property
    def dtype(self) -> type[np.generic]:
        return np.bool_ if self.unit == "bool" else np.float64


_LEGS = (LEG_COUNT,)

# Energy balance terms of plan S4: kinetic, gravity, contact and bushing springs, viscous
# and slip dissipation, motor work.
ENERGY_TERMS: tuple[str, ...] = (
    "kinetic",
    "gravity",
    "contact_spring",
    "bushing_spring",
    "dissipated_viscous",
    "dissipated_slip",
    "motor_work",
)


def _energy_field(term: str) -> RecordField:
    name = f"{ENERGY_FIELD_PREFIX}{term}"
    return RecordField(name, (), "J", "engine energy bookkeeping", is_optional=True)


RECORD_FIELDS: tuple[RecordField, ...] = (
    RecordField("t", (), "s", "TruthState.t_s"),
    RecordField("body_pos", (3,), "m", "TruthState.body_pos_m"),
    RecordField("body_quat_wxyz", (4,), "1", "TruthState.body_quat_wxyz"),
    RecordField("body_vel", (3,), "m/s", "TruthState.body_vel_m_s"),
    RecordField("body_omega", (3,), "rad/s", "TruthState.body_omega_rad_s"),
    RecordField("F_cyl", _LEGS, "N", "TruthState.F_cyl_N"),
    RecordField("F_contact_n", _LEGS, "N", "TruthState.F_contact_n_N"),
    RecordField("F_contact_t", (LEG_COUNT, 2), "N", "TruthState.F_contact_t_N"),
    RecordField("s_motor", _LEGS, "m", "TruthState.s_motor_m"),
    RecordField("s_ref", _LEGS, "m", "TruthState.s_ref_m"),
    RecordField("u_cmd", _LEGS, "m/s", "Command.leg_speed_m_s"),
    RecordField("u_applied", _LEGS, "m/s", "TruthState.u_applied_m_s"),
    RecordField("bushing_anchor", (LEG_COUNT, 3), "m", "TruthState.bushing_anchor_m"),
    # Not in the plan list (signals task, 2026-10-20): contact flags and crawler load.
    RecordField("pad_in_contact", _LEGS, "bool", "TruthState.is_pad_in_contact"),
    RecordField("F_crawler", (3,), "N", "TruthState.F_crawler_N"),
    # plan 3.2 'energy.*' with the terms of plan S4; produced from S4 on.
    *(_energy_field(term) for term in ENERGY_TERMS),
)
"""Per-sample Record arrays. ``bushing_events`` is an event table, see
:data:`BUSHING_EVENT_FIELDS`."""

RECORD_FIELDS_BY_NAME: Mapping[str, RecordField] = {field.name: field for field in RECORD_FIELDS}


class BushingEventKind(IntEnum):
    """Ground bushing event (plan R15): created on touchdown, removed on lift-off."""

    CREATED = 1
    REMOVED = 2


BUSHING_EVENTS_NAME = "bushing_events"

BUSHING_EVENT_FIELDS: tuple[RecordField, ...] = (
    RecordField("t", (), "s", "ground bushing hook"),
    RecordField("leg", (), "1", "ground bushing hook (LEG_ORDER index)"),
    RecordField("kind", (), "1", "ground bushing hook (BushingEventKind)"),
)
"""Columns of the ``bushing_events`` table: one row per event, any number of rows."""


def record_row(truth: TruthState, command: Command) -> dict[str, NDArray]:
    """One Record sample (required fields) from the truth state and the held command.

    Returns:
        Record name -> array of the field's ``sample_shape``, for every non-optional field
        of :data:`RECORD_FIELDS`.
    """
    sources = {"TruthState": truth, "Command": command}
    row: dict[str, NDArray] = {}
    for field in RECORD_FIELDS:
        if field.is_optional:
            continue
        type_name, attribute = field.source.split(".")
        row[field.name] = np.asarray(getattr(sources[type_name], attribute), dtype=field.dtype)
    return row


def validate_record_arrays(arrays: Mapping[str, ArrayLike]) -> int:
    """Check a set of Record arrays against :data:`RECORD_FIELDS`.

    Args:
        arrays: Record name -> stacked array of shape ``(n, *sample_shape)``.

    Returns:
        The common number of samples ``n``.

    Raises:
        InvalidSignalError: An unknown name, a missing required field, a wrong shape or
            dtype kind, or sample counts that differ between fields.
    """
    unknown = sorted(set(arrays) - set(RECORD_FIELDS_BY_NAME))
    if unknown:
        raise InvalidSignalError(unknown[0], f"not a Record field (unknown: {unknown})")
    missing = [field.name for field in RECORD_FIELDS if not field.is_optional]
    missing = [name for name in missing if name not in arrays]
    if missing:
        raise InvalidSignalError(missing[0], f"required Record field missing ({missing})")

    sample_count: int | None = None
    for name, value in arrays.items():
        field = RECORD_FIELDS_BY_NAME[name]
        array = np.asarray(value)
        if array.ndim == 0 or array.shape[1:] != field.sample_shape:
            expected = ("n", *field.sample_shape)
            raise InvalidSignalError(name, f"expected shape {expected}, got {array.shape}")
        is_flag_field = field.dtype is np.bool_
        if is_flag_field != (array.dtype == np.bool_):
            raise InvalidSignalError(name, f"expected dtype {field.dtype.__name__}")
        if sample_count is None:
            sample_count = array.shape[0]
        elif array.shape[0] != sample_count:
            raise InvalidSignalError(
                name, f"{array.shape[0]} samples, other fields have {sample_count}"
            )
    return sample_count or 0
