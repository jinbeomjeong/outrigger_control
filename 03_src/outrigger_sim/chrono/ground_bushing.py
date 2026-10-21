"""L1 ground tangential model: ground-fixed spherical bushing + circular Coulomb return mapping.

``00_docs/03_chrono/chrono_build_plan.md`` S0, R7, R8, R9, R15; ``dynamics_model.md`` 4.1;
YAML ``contact.rigid_floor.L1.tangential_model``. Ported from the block test ``hook()`` of
``04_scripts/02_chrono/test_stick_friction.py`` (regression baseline, left unchanged) and
generalised to four legs.

Why: Chrono 10 SMC contact has no stick (``00_docs/03_chrono/chrono_stick_friction_test.md``),
so the SMC materials carry the normal force only (``kt = gt = mu = 0``, R8) and the tangential
force comes from one ``ChLoadBodyBodyBushingSpherical`` per pad:

* body A = leg moving part (the body that carries the pad sphere), body B = fixed floor;
* frame B (floor anchor) at the projection of the pad sphere (ball) centre onto the floor
  surface when the bushing is created, axes = floor tangent plane (x, y) + floor normal (z);
  stiffness ``(kt, kt, 0)``, damping input ``(ct/2, ct/2, 0)`` because Chrono's bushing
  damping acts at twice the input (R7, YAML ``bushing_damping_input_per_pad_N_s_m`` already
  holds ``ct/2``);
* frame A (where the bushing force acts on body A, "force point"): by default the **ball
  centre** (:data:`FORCE_POINT_BALL_CENTRE`, user decision 2026-10-20, ``dynamics_model.md``
  5.3 ruling 4, option A). A swivel pad cannot carry a moment, so the floor reaction passes
  through the ball centre; the SMC normal force of the pad sphere already does, and with the
  tangential force at the centre the resultant does too. The normal offset ``r`` between
  frame A and frame B is not loaded (normal stiffness and damping 0), so the bushing reacts
  to the in-plane motion of the ball centre only, and a rotation of the leg body about the
  ball centre does not deform it. The former behaviour (frame A at the sphere contact point,
  ``r`` below the centre, fixed in body A at creation, :data:`FORCE_POINT_CONTACT`) adds a
  moment ``r n x T`` per leg (about 0.8-1.0 kN m in total on a 2 deg slope, up to 0.23 kN of
  vertical load shift per leg); it is kept as an option for comparison;
* after every step (:meth:`GroundBushingCoulomb.after_step`): normal force
  ``N = max(F_contact . n, 0)`` from the moving part's contact force; if ``kt |d| > mu N`` the
  floor anchor (frame B) is moved along the tangential displacement ``d`` so that the spring
  force equals ``mu N`` (``SetApplicationFrameB``), and the viscous term is switched off while
  sliding; it is switched on again once the tangential speed is below
  ``slip_damping_reenable_speed_m_s``. With ``N = 0`` the anchor follows the pad (no force).
  The built-in ``ChLoadBodyBodyBushingPlastic`` is not used (wrong while yielding).

R15 events (hysteresis): a bushing exists only while the pad is in contact.

* lift-off: ``N_raw <= 0`` on consecutive steps for ``t_lift`` (1 ms) of simulation time,
  i.e. on ``n_lift = ceil(t_lift / dt)`` consecutive steps (time based, so the rule does not
  change with dt; :func:`lift_step_count`) -> the bushing is removed;
* re-touch: ``N_raw > N_th`` (100 N) -> a new bushing is created at the current contact
  point with zero tangential force.

``t_lift`` and ``N_th`` are ASSUMPTIONS of the plan (section 7, to be tuned by the S2b event
test); the YAML has no key for them, so they are module constants here and can be passed to
the constructor. Every event is logged with time, leg and kind (1 create, 2 remove), the
``bushing_events`` table of the Record.

Each bushing lives in its own ``ChLoadContainer`` (Chrono has no way to remove a single load
from a container) that is added to / removed from the system with ``Add`` /
``RemoveOtherPhysicsItem``. Chrono re-analyses the sparsity pattern by itself after such
changes even when the pattern is locked (``chrono/system.py`` docstring), so no
:func:`~outrigger_sim.chrono.system.force_sparsity_pattern_update` call is needed here.
Changing the damping or the anchor frame of an existing bushing is not a structural change.

One-step lag (kept on purpose): Chrono computes the bushing force in the system Update at the
end of a step, so the anchor move and the damping switch made by :meth:`after_step` act from
the step after next (immediately after a bushing was created or removed, because Chrono then
runs a full Update at the start of the next step). The block-test baseline has the same lag;
its sliding friction excess (30 deg: mu_eff 0.505 for mu 0.5) comes from it. Forcing an
immediate update (``ChSystem.Update()`` after the hook) gave mu_eff 0.496 and 12 % more slip
on the 30 deg case (2026-10-20), i.e. it would break the S0 regression; switching is a model
decision, not done here. Snapshots carry the loaded (pre-hook) values so that a restore
reproduces the lag exactly (``chrono/snapshot.py``).

Initial attach (analytic start ``ON_PADS``, plan section 2 rule 1): :meth:`attach` creates the
bushings at t = 0 with zero tangential force; it is an initial condition, not an R15 event,
and is not logged as one.

Initial hold (opt-in, ``attach(hold_until_loaded=True)``; S2a V12 gravity ramp, plan S2a and
``dynamics_model.md`` 5.2 ruling 2): when the pads start with zero normal force and gravity is
ramped from 0, the SMC contact reports ``N = 0`` for the first tens of milliseconds (the
penetration is below Bullet's single-precision resolution, about 1e-7 m; measured
2026-10-20: 30 ms with a 3 s half-cosine ramp). The plain rules would then let the anchor
follow the pad (``mu N = 0``, counted as yield steps), remove every bushing after ``t_lift``
and re-create it at ``N > N_th`` about 74 ms later, so the zero-deformation start of the
linear reference (``dyn_model.static_slope_10dof``: tangential spring engaged from the first
load) would be lost. With the hold, a leg keeps its t = 0 bushing (no return mapping, no
lift-off count) until its normal force first exceeds ``N_th``; from then on the normal rules
apply. The release time per leg is kept (:attr:`GroundBushingCoulomb.hold_release_t_s`). The
tangential force reached while held is tiny (pad drop of a few um times the slope); default
off (S0 / S1 behaviour unchanged).

Hold safety (``dynamics_model.md`` 5.3 ruling 1, conditions 2-3): a leg that is still held
when the gravity ramp has ended carries a tangential restraint without a Coulomb limit;
:meth:`GroundBushingCoulomb.assert_hold_released` raises :class:`HoldNotReleasedError` then
(``chrono/runs.run_gravity_ramp(hold_deadline_s=...)`` calls it at the ramp end). The largest
tangential bushing force while held is kept per leg
(:attr:`GroundBushingCoulomb.hold_max_tangential_N`, judged ``<= mu N_th`` in
``verify/s2a.hold_checks``).

Snapshots: the force point is stored (``force_point_code``, index into
:data:`FORCE_POINTS`). A snapshot without it was written before the option existed, i.e.
with the contact point. Restoring a snapshot into an instance with a different force point
raises :class:`ForcePointMismatchError` (no silent conversion: moving frame A changes the
bushing deformation and force of the saved state); re-create the state with the current
model, or build the model with the snapshot's force point.

Energy diagnostics (S4 V8(b), added 2026-10-21): the return mapping also sums, per leg,
``1/2 kt (|d_trial|^2 - |d|^2)`` and ``mu N |delta anchor|`` (:attr:`GroundBushingCoulomb.
slip_dissipation_J`, :attr:`~GroundBushingCoulomb.slip_coulomb_work_J`), and
:meth:`~GroundBushingCoulomb.anchor_bookkeeping` exposes the anchors before / after the last
hook. These are read-only additions: no value used by the dynamics changes (trajectories
bit-identical, checked 2026-10-21), and they are not stored in snapshots.

Frames: all world quantities are SI, Z-up (R3). Every Chrono vector read here is copied at
once (R9). The floor surface is a plane given in floor-body coordinates (point + normal), so
a tilted floor body works as well as a level one.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER, Params

# --- R15 constants (ASSUMPTION, plan section 7; not in the YAML) --------------------------

LIFT_TIME_S = 1.0e-3
"""t_lift: N <= 0 must last this long (consecutive steps) before the bushing is removed."""
TOUCH_THRESHOLD_N = 100.0
"""N_th: a removed bushing is re-created when the normal force exceeds this value."""

# Relative guard for ceil(t_lift / dt): 1e-3 / 1e-4 = 10.000000000000002 in binary floating
# point and must give 10 steps, not 11.
_STEP_COUNT_REL_GUARD = 1.0e-9

EVENT_CREATE = 1
"""``bushing_events`` kind: bushing created (re-touch)."""
EVENT_REMOVE = 2
"""``bushing_events`` kind: bushing removed (lift-off)."""

STATE_KEYS = (
    "in_contact",
    "sliding",
    "zero_time_s",
    "anchor_floor_local_m",
    "frame_a_pos_body_local_m",
    "frame_a_quat_body_local_wxyz",
    "slip_total_m",
    "yield_steps",
    "event_t_s",
    "event_leg",
    "event_kind",
    "loaded_anchor_floor_local_m",
    "loaded_sliding",
    "normal_force_raw_N",
    "structure_changed",
)
OPTIONAL_STATE_KEYS = ("hold", "hold_release_t_s", "hold_max_tangential_N")
"""Hold state keys added after the first S1 snapshots were written; missing = no hold."""

FORCE_POINT_CONTACT = "contact_point"
"""Frame A at the sphere contact point (``r`` below the ball centre), fixed in body A at
creation; behaviour before 2026-10-20 (comparison option)."""
FORCE_POINT_BALL_CENTRE = "ball_centre"
"""Frame A at the pad sphere (ball) centre: the reaction passes through the swivel centre."""
FORCE_POINTS = (FORCE_POINT_CONTACT, FORCE_POINT_BALL_CENTRE)
"""Allowed force points; the index is the snapshot code (``force_point_code``)."""
DEFAULT_FORCE_POINT = FORCE_POINT_BALL_CENTRE
"""User decision 2026-10-20 (``dynamics_model.md`` 5.3 ruling 4, option A)."""
FORCE_POINT_STATE_KEY = "force_point_code"
"""Snapshot key of the force point; missing = :data:`FORCE_POINT_CONTACT` (older files)."""


class HoldNotReleasedError(RuntimeError):
    """A leg is still in the initial hold after the deadline (end of the gravity ramp)."""


class ForcePointMismatchError(ValueError):
    """A snapshot was written with another bushing force point than the restoring model."""


def lift_step_count(lift_time_s: float, dt_s: float) -> int:
    """``n_lift = ceil(t_lift / dt)`` with a floating-point guard (1e-3 / 1e-4 -> 10, not 11)."""
    if not (lift_time_s > 0.0 and dt_s > 0.0):
        raise ValueError(f"lift time and dt must be positive: {lift_time_s!r}, {dt_s!r}")
    return max(1, math.ceil(lift_time_s / dt_s * (1.0 - _STEP_COUNT_REL_GUARD)))


# --- small vector helpers (copies only, R9) -----------------------------------------------


def _vec(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


def _chvec(a: ArrayLike) -> ch.ChVector3d:
    x, y, z = (float(c) for c in np.asarray(a, dtype=float))
    return ch.ChVector3d(x, y, z)


def _quat(q: Any) -> NDArray[np.float64]:
    return np.array([q.e0, q.e1, q.e2, q.e3], dtype=float)


def _chquat(a: ArrayLike) -> ch.ChQuaterniond:
    w, x, y, z = (float(c) for c in np.asarray(a, dtype=float))
    return ch.ChQuaterniond(w, x, y, z)


def _quat_multiply(p: NDArray[np.float64], q: NDArray[np.float64]) -> NDArray[np.float64]:
    """Hamilton product p q of wxyz quaternions (rotation q first, then p)."""
    pw, px, py, pz = p
    qw, qx, qy, qz = q
    return np.array(
        [
            pw * qw - px * qx - py * qy - pz * qz,
            pw * qx + px * qw + py * qz - pz * qy,
            pw * qy - px * qz + py * qw + pz * qx,
            pw * qz + px * qy - py * qx + pz * qw,
        ]
    )


def _unit(a: ArrayLike, name: str) -> NDArray[np.float64]:
    v = np.asarray(a, dtype=float).reshape(3)
    norm = float(np.linalg.norm(v))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError(f"{name}: expected a non-zero finite 3-vector, got {a!r}")
    return v / norm


def surface_rotation_wxyz(normal: ArrayLike) -> NDArray[np.float64]:
    """Unit quaternion (wxyz) of a frame whose z axis is ``normal``.

    x axis = projection of the parent x axis onto the plane (parent y if x is parallel to the
    normal), y = z cross x. For ``normal = (sin a, 0, cos a)`` this is the rotation by ``a``
    about +y, the slope frame of the block test.
    """
    z = _unit(normal, "normal")
    x = np.array([1.0, 0.0, 0.0])
    x = x - (x @ z) * z
    if np.linalg.norm(x) < 1.0e-9:
        x = np.array([0.0, 1.0, 0.0]) - z[1] * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.column_stack((x, y, z))
    # Shepperd's method
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0.0:
        s = 2.0 * math.sqrt(1.0 + trace)
        q = (0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s)
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        q = ((m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s)
    elif m[1, 1] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        q = ((m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        q = ((m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s)
    quat = np.array(q, dtype=float)
    return quat / np.linalg.norm(quat)


# --- configuration -----------------------------------------------------------------------


@dataclass(frozen=True)
class PadBushingSpec:
    """One leg's pad contact as seen by the ground bushing.

    Attributes:
        name: Leg name (``FL`` ... ``RR``) or any label in tests.
        body: Body A, the leg moving part carrying the pad sphere.
        sphere_centre_body_local_m: Pad sphere centre in body-A coordinates [m].
        sphere_radius_m: Pad sphere radius [m]
            (``legs.<leg>.pad.swivel_center_above_pad_bottom_m``).
        stiffness_N_m: Tangential bushing stiffness ``kt`` [N/m]
            (``contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m``).
        damping_input_N_s_m: Chrono damping input ``ct / 2`` [N s/m] (R7;
            ``contact.rigid_floor.L1.bushing_damping_input_per_pad_N_s_m``). Acts as ``ct``.
    """

    name: str
    body: ch.ChBody
    sphere_centre_body_local_m: tuple[float, float, float]
    sphere_radius_m: float
    stiffness_N_m: float
    damping_input_N_s_m: float


@dataclass(frozen=True)
class BushingEvent:
    """One R15 event: ``kind`` 1 = created (re-touch), 2 = removed (lift-off)."""

    t_s: float
    leg: int
    kind: int


class _LegState:
    """Mutable per-leg state (Python side) and the Chrono objects of the current bushing.

    Arrays held here are never changed in place (always replaced), so they can be shared by
    reference (``loaded_anchor_floor_local``). Setting :attr:`anchor_floor_local` drops the
    cached world anchor; setting :attr:`frame_a_pos_local` rebuilds the cached Chrono vector.
    """

    def __init__(self) -> None:
        self.container: ch.ChLoadContainer | None = None
        self.bushing: ch.ChLoadBodyBodyBushingSpherical | None = None
        self._anchor_floor_local: NDArray[np.float64] = np.full(3, np.nan)
        # world anchor (x, y, z) computed by Chrono from the local anchor for the cached floor
        # frame; None = recompute (anchor or floor frame changed)
        self.anchor_world: tuple[float, float, float] | None = None
        self._frame_a_pos_local: NDArray[np.float64] = np.full(3, np.nan)
        self.frame_a_pos_local_ch: ch.ChVector3d | None = None
        self.frame_a_quat_local = np.full(4, np.nan)
        self.sliding = False
        # damping flag currently set in the Chrono bushing (SetDamping only when it changes)
        self.damping_on = False
        self.zero_time_s = 0.0
        self.slip_total = np.zeros(3)
        self.yield_steps = 0
        self.normal_force_raw_N = 0.0
        # Anchor and sliding flag as they were when Chrono last evaluated the bushing force
        # (the system Update at the end of the last step, i.e. before the last hook call).
        self.loaded_anchor_floor_local = np.full(3, np.nan)
        self.loaded_sliding = False
        # initial hold (attach(hold_until_loaded=True)): no return mapping / lift-off count
        # until the normal force first exceeds N_th
        self.hold = False
        self.hold_release_t_s = math.nan
        # largest |bushing force| seen while held [N] (0 when never held)
        self.hold_max_tangential_N = 0.0
        # S4 energy diagnostics (read only by chrono/energy; never used by the dynamics):
        # sum over return mappings of 1/2 kt (|d_trial|^2 - |d|^2) and of mu N |delta anchor|
        self.slip_dissipation_J = 0.0
        self.slip_coulomb_work_J = 0.0

    @property
    def anchor_floor_local(self) -> NDArray[np.float64]:
        return self._anchor_floor_local

    @anchor_floor_local.setter
    def anchor_floor_local(self, value: NDArray[np.float64]) -> None:
        self._anchor_floor_local = value
        self.anchor_world = None

    @property
    def frame_a_pos_local(self) -> NDArray[np.float64]:
        return self._frame_a_pos_local

    @frame_a_pos_local.setter
    def frame_a_pos_local(self, value: NDArray[np.float64]) -> None:
        self._frame_a_pos_local = value
        self.frame_a_pos_local_ch = _chvec(value) if np.all(np.isfinite(value)) else None

    @property
    def in_contact(self) -> bool:
        return self.bushing is not None


class GroundBushingCoulomb:
    """L1 ground tangential contact for N pads (four legs in LEG_ORDER for the machine).

    Call :meth:`after_step` once after every ``DoStepDynamics`` (plan 3.1 ``chrono/model``
    hook order: ground bushing R15 first). Read results through the copy-returning properties.

    Args:
        system: The Chrono system (``ChSystemSMC``; the bushing adds stiffness/damping matrices,
            so it needs a direct solver).
        floor: Fixed floor body (body B).
        pads: One :class:`PadBushingSpec` per leg.
        friction: Coulomb coefficient ``mu`` of the return mapping
            (``contact.rigid_floor.friction``; ASSUMPTION 0.5 in the YAML).
        slip_damping_reenable_speed_m_s: Damping is switched back on below this tangential
            speed (``contact.rigid_floor.L1.slip_damping_reenable_speed_m_s``; ASSUMPTION).
        dt_s: Time step used by :meth:`after_step` when none is passed [s].
        surface_point_floor_local_m: A point of the floor surface plane, floor-body coordinates.
        surface_normal_floor_local: Outward floor normal, floor-body coordinates.
        lift_time_s: ``t_lift`` (R15), default :data:`LIFT_TIME_S`.
        touch_threshold_N: ``N_th`` (R15), default :data:`TOUCH_THRESHOLD_N`.
        force_point: Where the bushing force acts on body A, one of :data:`FORCE_POINTS`;
            default :data:`DEFAULT_FORCE_POINT` (ball centre, module docstring).
    """

    def __init__(
        self,
        system: ch.ChSystem,
        floor: ch.ChBody,
        pads: Sequence[PadBushingSpec],
        *,
        friction: float,
        slip_damping_reenable_speed_m_s: float,
        dt_s: float,
        surface_point_floor_local_m: ArrayLike = (0.0, 0.0, 0.0),
        surface_normal_floor_local: ArrayLike = (0.0, 0.0, 1.0),
        lift_time_s: float = LIFT_TIME_S,
        touch_threshold_N: float = TOUCH_THRESHOLD_N,
        force_point: str = DEFAULT_FORCE_POINT,
    ) -> None:
        if not pads:
            raise ValueError("at least one pad is needed")
        if friction < 0.0 or not math.isfinite(friction):
            raise ValueError(f"friction must be a finite non-negative number: {friction!r}")
        for pad in pads:
            if pad.stiffness_N_m <= 0.0 or pad.damping_input_N_s_m < 0.0:
                raise ValueError(f"pad {pad.name}: stiffness must be > 0 and damping >= 0")
            if pad.sphere_radius_m <= 0.0:
                raise ValueError(f"pad {pad.name}: sphere radius must be > 0")
        if touch_threshold_N < 0.0:
            raise ValueError(f"touch threshold must be >= 0: {touch_threshold_N!r}")
        if force_point not in FORCE_POINTS:
            raise ValueError(f"force_point must be one of {FORCE_POINTS}, got {force_point!r}")
        lift_step_count(lift_time_s, dt_s)  # validates both
        self._force_point = force_point
        self._system = system
        self._floor = floor
        self._pads = tuple(pads)
        self._mu = float(friction)
        self._v_stick = float(slip_damping_reenable_speed_m_s)
        self._dt_s = float(dt_s)
        self._lift_time_s = float(lift_time_s)
        self._touch_threshold_N = float(touch_threshold_N)
        self._surface_point_local = np.asarray(surface_point_floor_local_m, dtype=float).reshape(3)
        self._normal_local = _unit(surface_normal_floor_local, "surface_normal_floor_local")
        self._surface_quat_local = surface_rotation_wxyz(self._normal_local)
        self._surface_quat_local_ch = _chquat(self._surface_quat_local)
        self._normal_local_ch = _chvec(self._normal_local)
        # floor frame cache (refreshed by _refresh_floor): key = floor position and quaternion
        # as read from Chrono, normal = floor normal in world coordinates computed by Chrono
        self._floor_key: tuple[float, ...] | None = None
        self._n_world: tuple[float, float, float] = (math.nan, math.nan, math.nan)
        self._legs = [_LegState() for _ in self._pads]
        self._events: list[BushingEvent] = []
        # True when a bushing was created or removed since the last system Update; Chrono then
        # runs a full Update at the start of the next step (see the module docstring).
        self._structure_changed = False
        self._pending_post_hook = False  # set by restore_state, cleared by finish_restore

    # --- construction from the YAML --------------------------------------------------

    @classmethod
    def from_params(
        cls,
        params: Params,
        system: ch.ChSystem,
        floor: ch.ChBody,
        moving_parts: Sequence[ch.ChBody],
        sphere_centres_body_local_m: Sequence[ArrayLike],
        *,
        dt_s: float,
        surface_point_floor_local_m: ArrayLike | None = None,
        surface_normal_floor_local: ArrayLike = (0.0, 0.0, 1.0),
        lift_time_s: float = LIFT_TIME_S,
        touch_threshold_N: float = TOUCH_THRESHOLD_N,
        force_point: str = DEFAULT_FORCE_POINT,
    ) -> GroundBushingCoulomb:
        """Four legs in LEG_ORDER with the L1 values of ``02_params/rexome33.yaml``.

        Keys: ``contact.rigid_floor.friction``, ``contact.rigid_floor.L1.
        bushing_stiffness_per_pad_N_m``, ``.bushing_damping_input_per_pad_N_s_m`` (= ct/2),
        ``.slip_damping_reenable_speed_m_s``, ``legs.<leg>.pad.swivel_center_above_pad_bottom_m``
        (sphere radius). The floor surface defaults to the level plane
        ``z = ground.crawler_bottom_z_m`` of the floor body built by ``make_system``.
        """
        if len(moving_parts) != len(LEG_ORDER) or len(sphere_centres_body_local_m) != len(
            LEG_ORDER
        ):
            raise ValueError(f"need one moving part and one sphere centre per leg {LEG_ORDER}")
        l1 = params.contact.rigid_floor.L1
        pads = [
            PadBushingSpec(
                name=leg.name,
                body=moving_parts[i],
                sphere_centre_body_local_m=tuple(
                    float(c) for c in np.asarray(sphere_centres_body_local_m[i], dtype=float)
                ),  # type: ignore[arg-type]
                sphere_radius_m=leg.pad.swivel_center_above_pad_bottom_m,
                stiffness_N_m=l1.bushing_stiffness_per_pad_N_m[i],
                damping_input_N_s_m=l1.bushing_damping_input_per_pad_N_s_m[i],
            )
            for i, leg in enumerate(params.legs)
        ]
        if surface_point_floor_local_m is None:
            surface_point_floor_local_m = (0.0, 0.0, params.ground.crawler_bottom_z_m)
        return cls(
            system,
            floor,
            pads,
            friction=params.contact.rigid_floor.friction,
            slip_damping_reenable_speed_m_s=l1.slip_damping_reenable_speed_m_s,
            dt_s=dt_s,
            surface_point_floor_local_m=surface_point_floor_local_m,
            surface_normal_floor_local=surface_normal_floor_local,
            lift_time_s=lift_time_s,
            touch_threshold_N=touch_threshold_N,
            force_point=force_point,
        )

    # --- read-only views ---------------------------------------------------------------

    @property
    def leg_names(self) -> tuple[str, ...]:
        return tuple(pad.name for pad in self._pads)

    @property
    def dt_s(self) -> float:
        return self._dt_s

    @dt_s.setter
    def dt_s(self, value: float) -> None:
        """Change the default step (transition windows); the lift rule stays time based."""
        lift_step_count(self._lift_time_s, value)
        self._dt_s = float(value)

    @property
    def force_point(self) -> str:
        """Where the bushing force acts on body A (:data:`FORCE_POINTS`)."""
        return self._force_point

    @property
    def lift_time_s(self) -> float:
        return self._lift_time_s

    @property
    def touch_threshold_N(self) -> float:
        return self._touch_threshold_N

    @property
    def n_lift(self) -> int:
        """Consecutive ``N <= 0`` steps that remove a bushing at the current :attr:`dt_s`."""
        return lift_step_count(self._lift_time_s, self._dt_s)

    @property
    def in_contact(self) -> NDArray[np.bool_]:
        return np.array([leg.in_contact for leg in self._legs], dtype=bool)

    @property
    def sliding(self) -> NDArray[np.bool_]:
        return np.array([leg.sliding for leg in self._legs], dtype=bool)

    @property
    def normal_force_N(self) -> NDArray[np.float64]:
        """``max(N_raw, 0)`` of the last :meth:`after_step` per leg [N]."""
        return np.array([max(leg.normal_force_raw_N, 0.0) for leg in self._legs])

    @property
    def normal_force_raw_N(self) -> NDArray[np.float64]:
        """Signed contact force along the floor normal of the last :meth:`after_step` [N]."""
        return np.array([leg.normal_force_raw_N for leg in self._legs])

    @property
    def slip_total_m(self) -> NDArray[np.float64]:
        """Accumulated anchor movement (true slip) per leg, world frame [m], shape (n, 3)."""
        return np.array([leg.slip_total for leg in self._legs])

    @property
    def yield_steps(self) -> NDArray[np.int64]:
        return np.array([leg.yield_steps for leg in self._legs], dtype=np.int64)

    @property
    def hold(self) -> NDArray[np.bool_]:
        """Legs still in the initial hold (``attach(hold_until_loaded=True)``)."""
        return np.array([leg.hold for leg in self._legs], dtype=bool)

    @property
    def hold_release_t_s(self) -> NDArray[np.float64]:
        """Simulation time at which each leg left the initial hold (NaN: never held / held)."""
        return np.array([leg.hold_release_t_s for leg in self._legs], dtype=float)

    @property
    def hold_max_tangential_N(self) -> NDArray[np.float64]:
        """Largest bushing force magnitude per leg while it was held [N] (0: never held).

        Read from ``GetForce()`` in each hook call during the hold, including the call that
        releases it (the force Chrono evaluated at the end of that step).
        """
        return np.array([leg.hold_max_tangential_N for leg in self._legs], dtype=float)

    # --- S4 energy bookkeeping views (read only; ``chrono/energy``) -----------------------

    @property
    def slip_dissipation_J(self) -> NDArray[np.float64]:
        """Per leg ``sum 1/2 kt (|d_trial|^2 - |d|^2)`` over every yielding return mapping
        since construction [J] (``dynamics_model.md`` 5 V8(b) ``D_slip``; a lifted pad maps
        ``d`` to 0 with ``mu N = 0``, so the spring energy it held is counted here). Not part
        of snapshots: a restored instance counts from 0."""
        return np.array([leg.slip_dissipation_J for leg in self._legs], dtype=float)

    @property
    def slip_coulomb_work_J(self) -> NDArray[np.float64]:
        """Per leg ``sum mu N |delta anchor|`` over the same return mappings [J]."""
        return np.array([leg.slip_coulomb_work_J for leg in self._legs], dtype=float)

    @property
    def structure_changed(self) -> bool:
        """True when the last :meth:`after_step` created or removed a bushing."""
        return self._structure_changed

    def anchor_bookkeeping(
        self,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.bool_], NDArray[np.bool_]]:
        """``(anchor, loaded_anchor, sliding, loaded_sliding)`` per leg (copies).

        Anchors are floor-body coordinates [m], NaN rows without a bushing. ``loaded_*`` are
        the values before the last :meth:`after_step` (what Chrono's end-of-step Update
        read); the damping is on exactly when ``sliding`` is false. Read between steps.
        """
        anchor = np.array([leg.anchor_floor_local for leg in self._legs], dtype=float)
        loaded = np.array([leg.loaded_anchor_floor_local for leg in self._legs], dtype=float)
        sliding = np.array([leg.sliding for leg in self._legs], dtype=bool)
        loaded_sliding = np.array([leg.loaded_sliding for leg in self._legs], dtype=bool)
        return anchor, loaded, sliding, loaded_sliding

    def assert_hold_released(self, context: str = "") -> None:
        """Raise :class:`HoldNotReleasedError` if any leg is still in the initial hold.

        ``dynamics_model.md`` 5.3 ruling 1 condition 2: a hold that outlives the gravity ramp
        is a tangential restraint without a Coulomb limit, so the run is invalid.
        """
        held = [name for name, h in zip(self.leg_names, self.hold, strict=True) if h]
        if held:
            raise HoldNotReleasedError(
                f"initial hold not released{' ' + context if context else ''}: legs {held} "
                f"(normal force never exceeded N_th = {self._touch_threshold_N} N; "
                f"t = {float(self._system.GetChTime())} s)"
            )

    def tangential_displacement_m(self) -> NDArray[np.float64]:
        """In-plane bushing deformation ``d`` (frame A point - anchor, normal part removed) per
        leg, world frame [m], shape (n, 3); NaN rows without a bushing. Frame A is the force
        point (:attr:`force_point`). Uses the current body state and the anchors set for the
        next step."""
        self._refresh_floor()
        n = np.array(self._n_world)
        out = np.full((len(self._legs), 3), np.nan)
        for i, (pad, leg) in enumerate(zip(self._pads, self._legs, strict=True)):
            if leg.bushing is None:
                continue
            p = _vec(pad.body.TransformPointLocalToParent(leg.frame_a_pos_local_ch))
            d = p - np.array(self._anchor_world(leg))
            out[i] = d - (d @ n) * n
        return out

    @property
    def events(self) -> tuple[BushingEvent, ...]:
        """R15 events since construction / :meth:`clear_events` (attach is not an event)."""
        return tuple(self._events)

    def event_table(self) -> dict[str, NDArray[Any]]:
        """``bushing_events`` columns: ``t`` [s], ``leg`` (index), ``kind`` (1 create, 2 remove)."""
        return {
            "t": np.array([e.t_s for e in self._events], dtype=float),
            "leg": np.array([e.leg for e in self._events], dtype=np.int64),
            "kind": np.array([e.kind for e in self._events], dtype=np.int64),
        }

    def clear_events(self) -> None:
        self._events.clear()

    def _refresh_floor(self) -> None:
        """Re-read the floor frame; recompute the cached normal and anchors if it moved.

        The floor is normally fixed, so the Chrono transforms of the normal and of every
        anchor are done once and reused (values identical to a per-step transform, because
        they come from the same Chrono call on the same frame). A floor rotated or moved
        between steps (slope set-up) is detected here by comparing its pose.
        """
        floor = self._floor
        p = floor.GetPos()
        q = floor.GetRot()
        key = (p.x, p.y, p.z, q.e0, q.e1, q.e2, q.e3)
        if key != self._floor_key:
            self._floor_key = key
            n = floor.TransformDirectionLocalToParent(self._normal_local_ch)
            self._n_world = (n.x, n.y, n.z)
            for leg in self._legs:
                leg.anchor_world = None

    def _anchor_world(self, leg: _LegState) -> tuple[float, float, float]:
        """World anchor of a leg in contact (cached; call after :meth:`_refresh_floor`)."""
        anchor = leg.anchor_world
        if anchor is None:
            a = self._floor.TransformPointLocalToParent(_chvec(leg.anchor_floor_local))
            anchor = (a.x, a.y, a.z)
            leg.anchor_world = anchor
        return anchor

    def normal_world(self) -> NDArray[np.float64]:
        """Floor normal in world coordinates."""
        self._refresh_floor()
        return np.array(self._n_world, dtype=float)

    def anchors_world_m(self) -> NDArray[np.float64]:
        """Floor anchor (frame B origin) per leg in world coordinates, NaN when lifted [m]."""
        self._refresh_floor()
        out = np.full((len(self._legs), 3), np.nan)
        for i, leg in enumerate(self._legs):
            if leg.in_contact:
                out[i] = self._anchor_world(leg)
        return out

    def tangential_force_world_N(self) -> NDArray[np.float64]:
        """Bushing force on each moving part, world frame [N], shape (n, 3); 0 when lifted.

        ``ChLoadBodyBodyBushingSpherical.GetForce()`` is ``k d + c v`` in frame-B axes (the
        force on body B); the force on body A is its negative (probe 2026-10-20). Reflects
        the state at the last load evaluation (start of the last step).
        """
        out = np.zeros((len(self._legs), 3))
        for i, leg in enumerate(self._legs):
            if leg.bushing is None:
                continue
            force_b = _vec(leg.bushing.GetForce())
            frame_b = leg.bushing.GetAbsoluteFrameB()
            out[i] = -_vec(frame_b.TransformDirectionLocalToParent(_chvec(force_b)))
        return out

    # --- bushing creation / removal ---------------------------------------------------

    def _contact_point_world(self, index: int) -> NDArray[np.float64]:
        pad = self._pads[index]
        centre = _vec(pad.body.TransformPointLocalToParent(_chvec(pad.sphere_centre_body_local_m)))
        n = self.normal_world()
        p0 = _vec(self._floor.TransformPointLocalToParent(_chvec(self._surface_point_local)))
        return centre - ((centre - p0) @ n) * n

    def _damping_vector(self, index: int, on: bool) -> ch.ChVector3d:
        c = self._pads[index].damping_input_N_s_m if on else 0.0
        return ch.ChVector3d(c, c, 0.0)

    def _set_damping(self, index: int, leg: _LegState, on: bool) -> None:
        """``SetDamping`` on the bushing only when the on/off state changes."""
        if on != leg.damping_on:
            assert leg.bushing is not None
            leg.bushing.SetDamping(self._damping_vector(index, on))
            leg.damping_on = on

    def _create(self, index: int, point_world: NDArray[np.float64] | None) -> None:
        """Create the bushing of leg ``index``.

        ``point_world``: the contact point (ball centre projected onto the floor surface);
        frame B is put there, frame A at the force point (:attr:`force_point`). None: frames
        A and B are taken from the leg state (restore).
        """
        pad = self._pads[index]
        leg = self._legs[index]
        surface_rot_world = _quat_multiply(_quat(self._floor.GetRot()), self._surface_quat_local)
        if point_world is None:
            frame_abs = ch.ChFramed(ch.ChVector3d(0.0, 0.0, 0.0), _chquat(surface_rot_world))
        else:
            frame_abs = ch.ChFramed(_chvec(point_world), _chquat(surface_rot_world))
        k = pad.stiffness_N_m
        bushing = ch.ChLoadBodyBodyBushingSpherical(
            pad.body,
            self._floor,
            frame_abs,
            ch.ChVector3d(k, k, 0.0),
            self._damping_vector(index, not leg.sliding),
        )
        leg.damping_on = not leg.sliding
        if point_world is None:
            bushing.SetApplicationFrameA(
                ch.ChFramed(_chvec(leg.frame_a_pos_local), _chquat(leg.frame_a_quat_local))
            )
            bushing.SetApplicationFrameB(
                ch.ChFramed(_chvec(leg.anchor_floor_local), _chquat(self._surface_quat_local))
            )
        else:
            frame_a = bushing.GetApplicationFrameA()
            leg.frame_a_quat_local = _quat(frame_a.GetRot())
            if self._force_point == FORCE_POINT_BALL_CENTRE:
                # same axes, origin moved up the normal by the ball height (not loaded:
                # normal stiffness and damping are 0), zero in-plane deformation
                leg.frame_a_pos_local = np.asarray(pad.sphere_centre_body_local_m, dtype=float)
                bushing.SetApplicationFrameA(
                    ch.ChFramed(_chvec(leg.frame_a_pos_local), _chquat(leg.frame_a_quat_local))
                )
            else:
                leg.frame_a_pos_local = _vec(frame_a.GetPos())
            leg.anchor_floor_local = _vec(bushing.GetApplicationFrameB().GetPos())
        container = ch.ChLoadContainer()
        self._system.Add(container)  # structural change seen by the system -> re-analysis
        container.Add(bushing)
        leg.container = container
        leg.bushing = bushing
        self._structure_changed = True

    def _remove(self, index: int) -> None:
        leg = self._legs[index]
        if leg.container is not None:
            self._system.RemoveOtherPhysicsItem(leg.container)
            self._structure_changed = True
        leg.container = None
        leg.bushing = None
        leg.anchor_floor_local = np.full(3, np.nan)
        leg.frame_a_pos_local = np.full(3, np.nan)
        leg.frame_a_quat_local = np.full(4, np.nan)
        leg.sliding = False
        leg.damping_on = False
        leg.zero_time_s = 0.0
        leg.hold = False

    def attach(self, legs: Sequence[int] | None = None, *, hold_until_loaded: bool = False) -> None:
        """Create bushings now with zero tangential force (initial condition, not an event).

        Args:
            legs: Leg indices; None = every leg without a bushing.
            hold_until_loaded: Keep each new bushing fixed (no return mapping, no lift-off
                count) until its normal force first exceeds ``N_th`` (module docstring,
                "Initial hold"; gravity-ramp starts).
        """
        indices = range(len(self._legs)) if legs is None else legs
        for i in indices:
            if not self._legs[i].in_contact:
                self._legs[i].sliding = False
                self._create(i, self._contact_point_world(i))
                self._legs[i].hold = hold_until_loaded
                self._legs[i].hold_release_t_s = math.nan
                self._legs[i].hold_max_tangential_N = 0.0

    def detach_all(self) -> None:
        """Remove every bushing without logging events (used by restore)."""
        for i in range(len(self._legs)):
            self._remove(i)

    # --- per-step hook ----------------------------------------------------------------

    def after_step(self, dt_s: float | None = None) -> list[BushingEvent]:
        """Return mapping and R15 events after one ``DoStepDynamics`` of length ``dt_s``.

        Returns:
            Events of this step (also appended to :attr:`events`).
        """
        dt = self._dt_s if dt_s is None else float(dt_s)
        t_now = float(self._system.GetChTime())
        self._refresh_floor()
        nx, ny, nz = self._n_world
        new_events: list[BushingEvent] = []
        self._structure_changed = False  # the step just taken ran a system Update at its end
        for leg in self._legs:
            # arrays are replaced, never changed in place (_LegState), so no copy is needed
            leg.loaded_anchor_floor_local = leg.anchor_floor_local
            leg.loaded_sliding = leg.sliding
        for i, (pad, leg) in enumerate(zip(self._pads, self._legs, strict=True)):
            f = pad.body.GetContactForce()
            # plain float dot product: bit-identical to numpy's 3-vector dot (checked
            # 2026-10-20 on 3e5 random pairs, OpenBLAS ddot uses no FMA on this path)
            n_raw = f.x * nx + f.y * ny + f.z * nz
            leg.normal_force_raw_N = n_raw
            if leg.bushing is None:
                if n_raw > self._touch_threshold_N:
                    leg.sliding = False
                    leg.zero_time_s = 0.0
                    self._create(i, self._contact_point_world(i))
                    new_events.append(BushingEvent(t_now, i, EVENT_CREATE))
                continue
            if leg.hold:
                fb = leg.bushing.GetForce()  # k d + c v, frame-B axes (normal part 0)
                t_mag = math.sqrt(fb.x * fb.x + fb.y * fb.y + fb.z * fb.z)
                if t_mag > leg.hold_max_tangential_N:
                    leg.hold_max_tangential_N = t_mag
                if n_raw > self._touch_threshold_N:
                    leg.hold = False
                    leg.hold_release_t_s = t_now
                else:
                    continue
            self._return_mapping(i, leg, max(n_raw, 0.0), nx, ny, nz)
            if n_raw <= 0.0:
                leg.zero_time_s += dt
                if leg.zero_time_s >= self._lift_time_s * (1.0 - _STEP_COUNT_REL_GUARD):
                    self._remove(i)
                    new_events.append(BushingEvent(t_now, i, EVENT_REMOVE))
            else:
                leg.zero_time_s = 0.0
        if new_events:
            self._events.extend(new_events)
        return new_events

    def _return_mapping(
        self, index: int, leg: _LegState, normal_force_N: float, nx: float, ny: float, nz: float
    ) -> None:
        """Circular Coulomb return mapping of the block test ``hook()`` (one leg).

        Scalar float arithmetic in the same operation order as the former numpy version
        (``d -= (d @ n) * n``, ``norm = sqrt(d @ d)``), so the results are bit-identical.
        The slip speed is only evaluated when it is used (leg sliding and not yielding).
        """
        pad = self._pads[index]
        bushing = leg.bushing
        assert bushing is not None
        body = pad.body
        local_a = leg.frame_a_pos_local_ch
        p = body.TransformPointLocalToParent(local_a)
        ax, ay, az = self._anchor_world(leg)
        dx = p.x - ax
        dy = p.y - ay
        dz = p.z - az
        dd = dx * nx + dy * ny + dz * nz
        dx = dx - dd * nx
        dy = dy - dd * ny
        dz = dz - dd * nz
        dn = math.sqrt(dx * dx + dy * dy + dz * dz)
        k = pad.stiffness_N_m
        limit = self._mu * normal_force_N
        if k * dn > limit:
            # Simple return mapping (spring = mu N now); the implicit step then overshoots by
            # about kt |v| dt while sliding (block test; a velocity predictor chattered).
            s = 1.0 - limit / (k * dn)
            mx, my, mz = dx * s, dy * s, dz * s
            # energy diagnostics only (S4 V8(b)); |d| after the mapping = dn (1 - s) = limit / k
            leg.slip_dissipation_J += 0.5 * k * dn * dn * s * (2.0 - s)
            leg.slip_coulomb_work_J += limit * dn * s
            anchor = ch.ChVector3d(ax + mx, ay + my, az + mz)
            leg.slip_total = leg.slip_total + np.array([mx, my, mz])
            leg.yield_steps += 1
            leg.anchor_floor_local = _vec(self._floor.TransformPointParentToLocal(anchor))
            bushing.SetApplicationFrameB(
                ch.ChFramed(_chvec(leg.anchor_floor_local), self._surface_quat_local_ch)
            )
            self._set_damping(index, leg, False)  # no viscous term while sliding
            leg.sliding = True
            return
        if leg.sliding:
            v = body.PointSpeedLocalToParent(local_a)
            vx, vy, vz = v.x, v.y, v.z
            vn = vx * nx + vy * ny + vz * nz
            wx = vx - vn * nx
            wy = vy - vn * ny
            wz = vz - vn * nz
            if math.sqrt(wx * wx + wy * wy + wz * wz) > self._v_stick:
                return  # keep damping off until the slip velocity has died out
        leg.sliding = False
        self._set_damping(index, leg, True)

    # --- snapshot support (R16) -------------------------------------------------------

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        """Python-side state for a snapshot (copies; bool / int / float arrays only)."""
        events = self.event_table()
        return {
            "in_contact": self.in_contact,
            "sliding": self.sliding,
            "zero_time_s": np.array([leg.zero_time_s for leg in self._legs]),
            "anchor_floor_local_m": np.array([leg.anchor_floor_local for leg in self._legs]),
            "frame_a_pos_body_local_m": np.array([leg.frame_a_pos_local for leg in self._legs]),
            "frame_a_quat_body_local_wxyz": np.array(
                [leg.frame_a_quat_local for leg in self._legs]
            ),
            "slip_total_m": self.slip_total_m,
            "yield_steps": self.yield_steps,
            "event_t_s": events["t"],
            "event_leg": events["leg"],
            "event_kind": events["kind"],
            "loaded_anchor_floor_local_m": np.array(
                [leg.loaded_anchor_floor_local for leg in self._legs]
            ),
            "loaded_sliding": np.array([leg.loaded_sliding for leg in self._legs], dtype=bool),
            "normal_force_raw_N": self.normal_force_raw_N,
            "structure_changed": np.array([self._structure_changed], dtype=bool),
            "hold": self.hold,
            "hold_release_t_s": self.hold_release_t_s,
            "hold_max_tangential_N": self.hold_max_tangential_N,
            FORCE_POINT_STATE_KEY: np.array(
                [FORCE_POINTS.index(self._force_point)], dtype=np.int64
            ),
        }

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """Rebuild bushings and Python state from :meth:`state_arrays` output.

        Existing bushings are removed first (through the system, so the sparsity pattern is
        re-analysed); bushings are re-created with the stored local frames A and B, so the
        tangential spring force continues exactly. The bushings are built with the anchor and
        damping that Chrono had loaded when the snapshot was taken (before the last hook call,
        unless a bushing was created or removed in that call); :meth:`finish_restore` then sets
        the post-hook values after the caller has updated the system. This reproduces the
        one-step lag of the uninterrupted run (module docstring); the sequence is driven by
        :func:`outrigger_sim.chrono.snapshot.restore_snapshot`.

        Raises:
            ValueError: Missing keys or a leg count that differs from this instance.
            ForcePointMismatchError: The snapshot's force point (missing key = contact
                point, files written before 2026-10-20) differs from :attr:`force_point`.
                Checked before anything is changed.
        """
        missing = [key for key in STATE_KEYS if key not in arrays]
        if missing:
            raise ValueError(f"ground bushing state lacks {missing}")
        if FORCE_POINT_STATE_KEY in arrays:
            code = int(np.asarray(arrays[FORCE_POINT_STATE_KEY]).reshape(-1)[0])
            if not 0 <= code < len(FORCE_POINTS):
                raise ValueError(f"unknown ground bushing force point code {code}")
            saved = FORCE_POINTS[code]
        else:
            saved = FORCE_POINT_CONTACT
        if saved != self._force_point:
            raise ForcePointMismatchError(
                f"snapshot ground bushing force point is {saved!r} "
                f"({'stored' if FORCE_POINT_STATE_KEY in arrays else 'no key: older file'}), "
                f"this model uses {self._force_point!r}; re-create the state with this model "
                f"or build it with force_point={saved!r}"
            )
        count = len(self._legs)
        in_contact = np.asarray(arrays["in_contact"], dtype=bool)
        if in_contact.shape != (count,):
            raise ValueError(f"ground bushing state has {in_contact.shape} legs, expected {count}")
        structure_changed = bool(np.asarray(arrays["structure_changed"]).reshape(-1)[0])
        self.detach_all()
        for i, leg in enumerate(self._legs):
            leg.zero_time_s = float(arrays["zero_time_s"][i])
            leg.slip_total = np.array(arrays["slip_total_m"][i], dtype=float)
            leg.yield_steps = int(arrays["yield_steps"][i])
            leg.normal_force_raw_N = float(arrays["normal_force_raw_N"][i])
            leg.loaded_anchor_floor_local = np.array(
                arrays["loaded_anchor_floor_local_m"][i], dtype=float
            )
            leg.loaded_sliding = bool(arrays["loaded_sliding"][i])
            leg.sliding = bool(arrays["sliding"][i])
            leg.anchor_floor_local = np.array(arrays["anchor_floor_local_m"][i], dtype=float)
            if in_contact[i]:
                leg.frame_a_pos_local = np.array(arrays["frame_a_pos_body_local_m"][i], dtype=float)
                leg.frame_a_quat_local = np.array(
                    arrays["frame_a_quat_body_local_wxyz"][i], dtype=float
                )
                if structure_changed:
                    self._create(i, None)
                else:
                    # build with what Chrono had loaded (before the last hook call)
                    post_anchor, post_sliding = leg.anchor_floor_local, leg.sliding
                    leg.anchor_floor_local = leg.loaded_anchor_floor_local
                    leg.sliding = leg.loaded_sliding
                    self._create(i, None)
                    leg.anchor_floor_local, leg.sliding = post_anchor, post_sliding
        for i, leg in enumerate(self._legs):  # optional keys (absent in S1 snapshots)
            leg.hold = bool(arrays["hold"][i]) if "hold" in arrays else False
            leg.hold_release_t_s = (
                float(arrays["hold_release_t_s"][i]) if "hold_release_t_s" in arrays else math.nan
            )
            leg.hold_max_tangential_N = (
                float(arrays["hold_max_tangential_N"][i])
                if "hold_max_tangential_N" in arrays
                else 0.0
            )
        self._structure_changed = structure_changed
        self._pending_post_hook = not structure_changed
        self._events = [
            BushingEvent(float(t), int(leg_index), int(kind))
            for t, leg_index, kind in zip(
                arrays["event_t_s"], arrays["event_leg"], arrays["event_kind"], strict=True
            )
        ]

    def finish_restore(self) -> None:
        """Set the post-hook anchor and damping (after the system Update of the restore)."""
        if not self._pending_post_hook:
            return
        for i, leg in enumerate(self._legs):
            if leg.bushing is not None:
                leg.bushing.SetApplicationFrameB(
                    ch.ChFramed(_chvec(leg.anchor_floor_local), _chquat(self._surface_quat_local))
                )
                leg.bushing.SetDamping(self._damping_vector(i, not leg.sliding))
                leg.damping_on = not leg.sliding
        self._pending_post_hook = False
