"""L1 ground tangential model: ground-fixed spherical bushing + circular Coulomb return mapping.

``00_docs/03_chrono/chrono_build_plan.md`` S0, R7, R8, R9, R15; ``dynamics_model.md`` 4.1;
YAML ``contact.rigid_floor.L1.tangential_model``. Ported from the block test ``hook()`` of
``04_scripts/02_chrono/test_stick_friction.py`` (regression baseline, left unchanged) and
generalised to four legs.

Why: Chrono 10 SMC contact has no stick (``00_docs/03_chrono/chrono_stick_friction_test.md``),
so the SMC materials carry the normal force only (``kt = gt = mu = 0``, R8) and the tangential
force comes from one ``ChLoadBodyBodyBushingSpherical`` per pad:

* body A = leg moving part (the body that carries the pad sphere), body B = fixed floor;
* frame at the sphere contact point on the floor surface when the bushing is created, axes =
  floor tangent plane (x, y) + floor normal (z); stiffness ``(kt, kt, 0)``, damping input
  ``(ct/2, ct/2, 0)`` because Chrono's bushing damping acts at twice the input (R7, YAML
  ``bushing_damping_input_per_pad_N_s_m`` already holds ``ct/2``);
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
    """Mutable per-leg state (Python side) and the Chrono objects of the current bushing."""

    def __init__(self) -> None:
        self.container: ch.ChLoadContainer | None = None
        self.bushing: ch.ChLoadBodyBodyBushingSpherical | None = None
        self.anchor_floor_local = np.full(3, np.nan)
        self.frame_a_pos_local = np.full(3, np.nan)
        self.frame_a_quat_local = np.full(4, np.nan)
        self.sliding = False
        self.zero_time_s = 0.0
        self.slip_total = np.zeros(3)
        self.yield_steps = 0
        self.normal_force_raw_N = 0.0
        # Anchor and sliding flag as they were when Chrono last evaluated the bushing force
        # (the system Update at the end of the last step, i.e. before the last hook call).
        self.loaded_anchor_floor_local = np.full(3, np.nan)
        self.loaded_sliding = False

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
        lift_step_count(lift_time_s, dt_s)  # validates both
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

    def normal_world(self) -> NDArray[np.float64]:
        """Floor normal in world coordinates."""
        return _vec(self._floor.TransformDirectionLocalToParent(_chvec(self._normal_local)))

    def anchors_world_m(self) -> NDArray[np.float64]:
        """Floor anchor (frame B origin) per leg in world coordinates, NaN when lifted [m]."""
        out = np.full((len(self._legs), 3), np.nan)
        for i, leg in enumerate(self._legs):
            if leg.in_contact:
                out[i] = _vec(
                    self._floor.TransformPointLocalToParent(_chvec(leg.anchor_floor_local))
                )
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

    def _create(self, index: int, point_world: NDArray[np.float64] | None) -> None:
        """Create the bushing of leg ``index``.

        ``point_world`` None: frames A and B are taken from the leg state (restore).
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
        if point_world is None:
            bushing.SetApplicationFrameA(
                ch.ChFramed(_chvec(leg.frame_a_pos_local), _chquat(leg.frame_a_quat_local))
            )
            bushing.SetApplicationFrameB(
                ch.ChFramed(_chvec(leg.anchor_floor_local), _chquat(self._surface_quat_local))
            )
        else:
            frame_a = bushing.GetApplicationFrameA()
            leg.frame_a_pos_local = _vec(frame_a.GetPos())
            leg.frame_a_quat_local = _quat(frame_a.GetRot())
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
        leg.zero_time_s = 0.0

    def attach(self, legs: Sequence[int] | None = None) -> None:
        """Create bushings now with zero tangential force (initial condition, not an event).

        Args:
            legs: Leg indices; None = every leg without a bushing.
        """
        indices = range(len(self._legs)) if legs is None else legs
        for i in indices:
            if not self._legs[i].in_contact:
                self._legs[i].sliding = False
                self._create(i, self._contact_point_world(i))

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
        n = self.normal_world()
        new_events: list[BushingEvent] = []
        self._structure_changed = False  # the step just taken ran a system Update at its end
        for leg in self._legs:
            leg.loaded_anchor_floor_local = leg.anchor_floor_local.copy()
            leg.loaded_sliding = leg.sliding
        for i, (pad, leg) in enumerate(zip(self._pads, self._legs, strict=True)):
            n_raw = float(_vec(pad.body.GetContactForce()) @ n)
            leg.normal_force_raw_N = n_raw
            if leg.bushing is None:
                if n_raw > self._touch_threshold_N:
                    leg.sliding = False
                    leg.zero_time_s = 0.0
                    self._create(i, self._contact_point_world(i))
                    new_events.append(BushingEvent(t_now, i, EVENT_CREATE))
                continue
            self._return_mapping(i, max(n_raw, 0.0))
            if n_raw <= 0.0:
                leg.zero_time_s += dt
                if leg.zero_time_s >= self._lift_time_s * (1.0 - _STEP_COUNT_REL_GUARD):
                    self._remove(i)
                    new_events.append(BushingEvent(t_now, i, EVENT_REMOVE))
            else:
                leg.zero_time_s = 0.0
        self._events.extend(new_events)
        return new_events

    def _return_mapping(self, index: int, normal_force_N: float) -> None:
        """Circular Coulomb return mapping of the block test ``hook()`` (one leg)."""
        pad = self._pads[index]
        leg = self._legs[index]
        bushing = leg.bushing
        assert bushing is not None
        n = self.normal_world()
        local_a = _chvec(leg.frame_a_pos_local)
        p_a = _vec(pad.body.TransformPointLocalToParent(local_a))
        anchor = _vec(self._floor.TransformPointLocalToParent(_chvec(leg.anchor_floor_local)))
        d = p_a - anchor
        d -= (d @ n) * n
        dn = float(np.linalg.norm(d))
        v = _vec(pad.body.PointSpeedLocalToParent(local_a))
        vt = float(np.linalg.norm(v - (v @ n) * n))
        k = pad.stiffness_N_m
        limit = self._mu * normal_force_N
        if k * dn > limit:
            # Simple return mapping (spring = mu N now); the implicit step then overshoots by
            # about kt |v| dt while sliding (block test; a velocity predictor chattered).
            move = d * (1.0 - limit / (k * dn))
            anchor = anchor + move
            leg.slip_total = leg.slip_total + move
            leg.yield_steps += 1
            leg.anchor_floor_local = _vec(self._floor.TransformPointParentToLocal(_chvec(anchor)))
            bushing.SetApplicationFrameB(
                ch.ChFramed(_chvec(leg.anchor_floor_local), _chquat(self._surface_quat_local))
            )
            bushing.SetDamping(self._damping_vector(index, False))  # no viscous term sliding
            leg.sliding = True
        elif leg.sliding and vt > self._v_stick:
            pass  # keep damping off until the slip velocity has died out
        else:
            leg.sliding = False
            bushing.SetDamping(self._damping_vector(index, True))

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
        """
        missing = [key for key in STATE_KEYS if key not in arrays]
        if missing:
            raise ValueError(f"ground bushing state lacks {missing}")
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
        self._pending_post_hook = False
